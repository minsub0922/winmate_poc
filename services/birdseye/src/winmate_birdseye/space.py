"""공간 입력 → 공간 모델(08-birdseye §4.2 · §7.3).

- 설명 해석: LLM JSON(be.space_parse, 기밀) → 막히거나 실패하면 정규식(space:regex). 줄 = 공간.
- 도면 · 사진이 없으면 직사각형(면적 · 가로세로 1.5:1 가정, estimated). 여러 줄은 가로로 붙이고 사이 벽 0.2 m · 연결 문 1개.
- 병합: 도면 모델 > 사진 모델 > 설명, 사용자 칸 값(면적 · 층고) 우선. 빈 값은 공간 유형 기본값(§10.3, estimated).
- 역량 힌트: KB C1(공간 · 문장 → 역량) → W 특징 문장 · 요약 칩(「전면 유리창 (고휘도 권장)」).
"""
from __future__ import annotations

import copy
import math
import re
from typing import Any

from pydantic import BaseModel, Field

from . import config
from . import text as T

KO_NUM = {"한": 1, "하나": 1, "두": 2, "둘": 2, "세": 3, "셋": 3, "네": 4, "넷": 4, "다섯": 5, "여섯": 6, "일곱": 7, "여덟": 8}
SPACE_WORDS = ["로비", "라운지", "매장", "쇼룸", "카페", "회의실", "강의실", "대기실", "객실", "관제실", "상황실", "사무실", "오피스",
               "홀", "전시장", "강당", "식당", "병실", "접수처", "스튜디오"]
CHIP_NAME = {"store_lobby": "매장", "meeting_office": "회의실", "classroom": "강의실", "hospital_waiting": "대기실",
             "hotel_room": "객실", "control_room": "관제실"}
CAP_HINT = {"cap_sunlight_readable": "고휘도 권장", "cap_weatherproof": "방수·방진 권장"}


# ── LLM 스키마 ───────────────────────────────────────────

class ParsedFeature(BaseModel):
    kind: str = Field(description="storefront_window · window · columns · glass_wall · stage · counter · night_visibility · entrance")
    count: int | None = None
    label: str = ""


class ParsedRoom(BaseModel):
    label: str = ""
    space_types: list[str] = Field(default_factory=list)
    area_pyeong: float | None = None
    ceiling_m: float | None = None
    features: list[ParsedFeature] = Field(default_factory=list)


class ParsedSpace(BaseModel):
    rooms: list[ParsedRoom] = Field(default_factory=list)


PARSE_SYSTEM = (
    "너는 매장 · 오피스 공간 설명을 구조화한다. 줄 하나 = 공간 하나. 숫자는 글에 있는 것만 쓰고 없으면 null. "
    "features.kind 는 storefront_window(정면 전면 유리창) · window · columns(기둥, count) · glass_wall · stage · counter · "
    "night_visibility(저녁 · 야간에 외부에서 보임) · entrance 중에서만 고른다."
)


# ── 정규식 대체 ───────────────────────────────────────────

_PY = re.compile(r"(?:약\s*)?(\d+(?:\.\d+)?)\s*평")
_M2 = re.compile(r"(\d+(?:\.\d+)?)\s*(?:㎡|m2|m²|제곱미터|평방미터)")
_CEIL = re.compile(r"(?:층고|천장\s*높이|천장고)\s*(?:는|은|가|이|약)?\s*(\d+(?:\.\d+)?)\s*m")
_COL = re.compile(r"기둥\s*(?:이|은|는)?\s*(\d+|한|하나|두|둘|세|셋|네|넷|다섯|여섯)\s*(?:개|본)")
_COL2 = re.compile(r"(\d+|두|세|네)\s*개의?\s*기둥")
_FLOOR = re.compile(r"(\d+)\s*층")


def regex_parse(description: str) -> list[dict[str, Any]]:
    rooms = []
    for line in [ln.strip() for ln in (description or "").splitlines() if ln.strip()]:
        r: dict[str, Any] = {"label": "", "space_types": [], "area_pyeong": None, "ceiling_m": None, "features": [], "text": line}
        m = _PY.search(line)
        if m:
            r["area_pyeong"] = float(m.group(1))
        else:
            m = _M2.search(line)
            if m:
                r["area_pyeong"] = round(float(m.group(1)) / T.PYEONG_M2, 2)
        m = _CEIL.search(line)
        if m:
            r["ceiling_m"] = float(m.group(1))
        m = _COL.search(line) or _COL2.search(line)
        if m:
            v = m.group(1)
            n = int(v) if v.isdigit() else KO_NUM.get(v, 0)
            if n:
                r["features"].append({"kind": "columns", "count": n, "label": "중앙 기둥" if "중앙" in line else "기둥"})
        if re.search(r"전면\s*(?:이\s*)?(?:유리|통유리)|정면이\s*전면\s*유리|쇼윈도|통유리", line):
            r["features"].append({"kind": "storefront_window", "count": None, "label": "전면 유리창"})
        elif re.search(r"유리창|창문|창가|창이", line):
            r["features"].append({"kind": "window", "count": None, "label": "창"})
        if re.search(r"저녁|야간|밤에|외부에서\s*(?:내부가)?\s*(?:잘\s*)?보", line):
            r["features"].append({"kind": "night_visibility", "count": None, "label": "외부 노출"})
        r["label"] = room_label(line)
        rooms.append(r)
    return rooms


def room_label(line: str) -> str:
    """「강남 플래그십 스토어 1층 로비. …」 → 「1층 로비」."""
    head = re.split(r"[.,\n]", line, maxsplit=1)[0]
    for w in SPACE_WORDS:
        if w in head:
            m = _FLOOR.search(head)
            return f"{m.group(1)}층 {w}" if m else w
    return head.strip()[:20]


def space_name(birdseye: dict[str, Any], model: dict[str, Any] | None = None) -> str:
    """W 문장의 공간 이름(「로비」 「관제실」)."""
    texts = [birdseye.get("description") or ""]
    if model:
        texts += [r.get("label", "") for r in model.get("rooms", [])]
    for t in texts:
        for w in SPACE_WORDS:
            if w in t:
                return w
    return CHIP_NAME.get(birdseye.get("space_chip") or "store_lobby", "공간")


# ── 직사각형 모델 ─────────────────────────────────────────

def _wall(wid: str, a: list[float], b: list[float], label: str, kind: str = "exterior", dim_known: bool = False,
          room_id: str | None = None) -> dict[str, Any]:
    return {"id": wid, "a": [round(a[0], 2), round(a[1], 2)], "b": [round(b[0], 2), round(b[1], 2)], "thickness": 0.2,
            "kind": kind, "label": label, "dim_known": dim_known, "room_id": room_id}


def rect_model(rooms_in: list[dict[str, Any]], *, chip: str, area_field_pyeong: float | None, ceiling_field_m: float | None,
               front_width_m: float | None = None, source: str = "description") -> dict[str, Any]:
    """설명(또는 사진 종합) → 직사각형 공간 모델. rooms_in: [{label, area_pyeong?, ceiling_m?, features[]}]."""
    rules = config.rules()
    info = config.chip_info(chip)
    assumptions: list[dict[str, Any]] = []
    if not rooms_in:
        rooms_in = [{"label": info["space_label"], "area_pyeong": None, "ceiling_m": None, "features": []}]
    n = len(rooms_in)
    # 면적: 칸 값(전체) > 줄마다 값 > 공간 유형 기본값(estimated)
    areas: list[float] = []
    estimated = False
    if area_field_pyeong:
        given = [r.get("area_pyeong") for r in rooms_in]
        if n > 1 and all(given) and abs(sum(given) - area_field_pyeong) > 0.5:
            areas = [float(g) for g in given]  # type: ignore[arg-type]
        elif n > 1 and all(given):
            areas = [float(g) for g in given]  # type: ignore[arg-type]
        else:
            areas = [area_field_pyeong / n] * n
    else:
        for r in rooms_in:
            if r.get("area_pyeong"):
                areas.append(float(r["area_pyeong"]))
            else:
                areas.append(float(info["area_pyeong"]))
                estimated = True
        if estimated:
            assumptions.append({"kind": "area_estimate", "ref": None, "action": "BE1",
                                "text_ko": f"면적을 알 수 없어 {info['label']} 기본값 {info['area_pyeong']}평으로 잡았어요."})
    # 층고
    ceil_est = False
    if ceiling_field_m:
        ceiling = float(ceiling_field_m)
    else:
        cs = [r.get("ceiling_m") for r in rooms_in if r.get("ceiling_m")]
        if cs:
            ceiling = float(cs[0])
        else:
            ceiling = float(info["ceiling_m"])
            ceil_est = True
            assumptions.append({"kind": "ceiling_estimate", "ref": None, "action": "BE1",
                                "text_ko": f"층고를 알 수 없어 {T.num(ceiling)} m로 잡았어요."})
    lo, hi = rules["ceiling_range_m"]
    ceiling = min(max(ceiling, lo), hi)
    aspect = float(rules["rect_aspect"])
    gap = float(rules["multi_room_wall_m"])
    model: dict[str, Any] = {
        "rooms": [], "walls": [], "openings": [], "columns": [], "cores": [], "power_points": [],
        "ceiling_h": {"value": round(ceiling, 2), "estimated": ceil_est},
        "scale": {"ratio": None, "source": "description" if source == "description" else "photo_estimate", "correction": 1.0},
        "dims": [], "area_m2": 0.0, "features": [], "assumptions": assumptions, "questions": [], "facts": [],
        "estimated": True, "source": source, "meta_paths": [],
    }
    x0 = 0.0
    total = 0.0
    feats_all: list[dict[str, Any]] = []
    room_boxes = []
    for i, (r, apy) in enumerate(zip(rooms_in, areas), start=1):
        a_m2 = T.pyeong_to_m2(apy)
        if front_width_m and i == 1:
            wdt = float(front_width_m)
            dep = a_m2 / wdt
        else:
            wdt = math.sqrt(a_m2 * aspect)
            dep = a_m2 / wdt
        wdt, dep = round(wdt, 2), round(dep, 2)
        rid = f"r{i}"
        label = r.get("label") or info["space_label"]
        types = r.get("space_types") or list(info["space_types"])
        model["rooms"].append({"id": rid, "label": label, "space_types": types,
                               "outline": [[round(x0, 2), 0.0], [round(x0 + wdt, 2), 0.0], [round(x0 + wdt, 2), dep], [round(x0, 2), dep]]})
        room_boxes.append((rid, x0, wdt, dep, r))
        total += a_m2
        x0 += wdt + gap
    model["area_m2"] = round(total, 2)
    # 벽 · 개구부 · 기둥
    wn = 0
    on = 0
    cn = 0
    for idx, (rid, rx, wdt, dep, r) in enumerate(room_boxes):
        feats = r.get("features") or []
        labels = ("정면", "오른쪽", "후면", "왼쪽") if n == 1 else (f"{r.get('label') or rid} 정면", f"{r.get('label') or rid} 오른쪽",
                                                                   f"{r.get('label') or rid} 후면", f"{r.get('label') or rid} 왼쪽")
        pts = [(rx, 0.0), (rx + wdt, 0.0), (rx + wdt, dep), (rx, dep)]
        ids = []
        for k in range(4):
            a, b = pts[k], pts[(k + 1) % 4]
            if n > 1 and ((k == 1 and idx < n - 1) or (k == 3 and idx > 0)):
                # 공간 사이 벽: 오른쪽 방의 왼쪽 벽은 두지 않고(왼쪽 방 오른쪽 벽 + gap) 하나로
                if k == 3:
                    ids.append(None)
                    continue
                wn += 1
                mid_x = round(rx + wdt + gap / 2, 2)
                model["walls"].append(_wall(f"w{wn}", [mid_x, 0.0], [mid_x, dep], f"{r.get('label') or rid} · 사이 벽", "interior",
                                            False, rid))
                ids.append(f"w{wn}")
                continue
            wn += 1
            model["walls"].append(_wall(f"w{wn}", list(a), list(b), labels[k], "exterior", bool(front_width_m and idx == 0 and k == 0), rid))
            ids.append(f"w{wn}")
        front_id = ids[0]
        has_store = any(f.get("kind") == "storefront_window" for f in feats)
        has_win = has_store or any(f.get("kind") in ("window", "glass_wall") for f in feats)
        door_w = 2.0 if has_store else 1.8
        if idx == 0:
            # 주출입구: 정면 벽 가운데
            d_off = round(wdt / 2 - door_w / 2, 2)
            on += 1
            model["openings"].append({"id": f"o{on}", "kind": "door", "wall_id": front_id, "offset": d_off, "width": door_w,
                                      "label": "주출입구", "door_type": "main", "is_main": True, "confidence": 0.7,
                                      "faces_outdoor": False, "assumed": False})
            if has_win:
                seg_l = round(d_off - 1.0, 2)
                if seg_l > 1.0:
                    on += 1
                    model["openings"].append({"id": f"o{on}", "kind": "window", "wall_id": front_id, "offset": 1.0, "width": round(seg_l - 0.0, 2) - 0.0,
                                              "label": "전면 유리창" if has_store else "창", "faces_outdoor": True})
                    on += 1
                    model["openings"].append({"id": f"o{on}", "kind": "window", "wall_id": front_id,
                                              "offset": round(d_off + door_w + 0.0, 2) + 0.0, "width": round(wdt - (d_off + door_w) - 1.0, 2),
                                              "label": "전면 유리창" if has_store else "창", "faces_outdoor": True})
        elif has_win:
            on += 1
            model["openings"].append({"id": f"o{on}", "kind": "window", "wall_id": front_id, "offset": 1.0, "width": round(max(1.0, wdt - 2.0), 2),
                                      "label": "창", "faces_outdoor": True})
        if idx > 0:
            # 연결 문 1개: 사이 벽 가운데
            between = next((w for w in model["walls"] if w["kind"] == "interior" and w["room_id"] == room_boxes[idx - 1][0]), None)
            if between:
                on += 1
                model["openings"].append({"id": f"o{on}", "kind": "door", "wall_id": between["id"], "offset": round(dep / 2 - 0.5, 2),
                                          "width": 1.0, "label": "연결 문", "door_type": "normal", "confidence": 0.9, "faces_outdoor": False})
        for f in feats:
            if f.get("kind") == "columns" and f.get("count"):
                k = int(f["count"])
                for j in range(k):
                    cn += 1
                    cx = round(rx + wdt * (j + 1) / (k + 1), 2)
                    model["columns"].append({"id": f"c{cn}", "center": [cx, round(dep / 2, 2)], "w": 0.6, "d": 0.6, "label": ""})
        feats_all += feats
    model["features"] = _features(feats_all, model)
    model["assumptions"].append({"kind": "shape_estimate", "ref": None, "action": "BE1D",
                                 "text_ko": f"도면이 없어 가로세로 {T.num(aspect)} : 1 직사각형으로 잡았어요."})
    return model


def _features(feats: list[dict[str, Any]], model: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen = set()
    for f in feats:
        kind = f.get("kind")
        if kind in seen:
            continue
        seen.add(kind)
        if kind == "columns":
            n = len(model.get("columns", []))
            if n:
                out.append({"kind": "columns", "label": f.get("label") or "기둥", "count": n})
        elif kind == "storefront_window":
            out.append({"kind": "storefront_window", "label": "전면 유리창"})
        elif kind in ("window", "glass_wall"):
            out.append({"kind": kind, "label": f.get("label") or "창"})
        elif kind == "night_visibility":
            out.append({"kind": "night_visibility", "label": "외부 노출"})
        elif kind:
            out.append({"kind": kind, "label": f.get("label") or kind})
    return out


def features_from_model(model: dict[str, Any]) -> list[dict[str, Any]]:
    """도면 · 사진 모델에서 특징(창 · 기둥)을 다시 뽑는다."""
    out = []
    wins = [o for o in model.get("openings", []) if o["kind"] == "window"]
    if any(o.get("faces_outdoor") for o in wins):
        out.append({"kind": "storefront_window", "label": "전면 유리창"})
    elif wins:
        out.append({"kind": "window", "label": "창"})
    cols = model.get("columns", [])
    if cols:
        out.append({"kind": "columns", "label": "중앙 기둥" if _central(model, cols) else "기둥", "count": len(cols)})
    return out


def _central(model: dict[str, Any], cols: list[dict[str, Any]]) -> bool:
    xs = [p[0] for r in model.get("rooms", []) for p in r["outline"]]
    ys = [p[1] for r in model.get("rooms", []) for p in r["outline"]]
    if not xs:
        return False
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    for c in cols:
        x, y = c["center"]
        if not (minx + (maxx - minx) * 0.2 <= x <= maxx - (maxx - minx) * 0.2 and miny + (maxy - miny) * 0.2 <= y <= maxy - (maxy - miny) * 0.2):
            return False
    return True


def apply_fields(model: dict[str, Any], *, ceiling_field_m: float | None) -> dict[str, Any]:
    """도면 · 사진 모델에 사용자 칸 값(층고)을 덮는다."""
    m = copy.deepcopy(model)
    if ceiling_field_m:
        lo, hi = config.rules()["ceiling_range_m"]
        m["ceiling_h"] = {"value": round(min(max(float(ceiling_field_m), lo), hi), 2), "estimated": False}
        m["assumptions"] = [a for a in m.get("assumptions", []) if a.get("kind") != "ceiling_estimate"]
    return m


def with_features_from_description(model: dict[str, Any], parsed_rooms: list[dict[str, Any]]) -> dict[str, Any]:
    """도면 모델 + 설명의 특징 중 도면에 없는 것(외부 노출 등)만 더한다."""
    m = copy.deepcopy(model)
    kinds = {f["kind"] for f in m.get("features", [])}
    for r in parsed_rooms:
        for f in r.get("features") or []:
            if f.get("kind") == "night_visibility" and "night_visibility" not in kinds:
                m["features"].append({"kind": "night_visibility", "label": "외부 노출"})
                kinds.add("night_visibility")
    if parsed_rooms and m.get("rooms"):
        lab = parsed_rooms[0].get("label")
        if lab and not m["rooms"][0].get("label"):
            m["rooms"][0]["label"] = lab
    return m


# ── 역량 힌트 · 요약 칩 · W 문장 ─────────────────────────

def apply_caps(model: dict[str, Any], caps: list[dict[str, Any]]) -> dict[str, Any]:
    ids = {c.get("id") for c in caps}
    for f in model.get("features", []):
        if f["kind"] in ("storefront_window", "glass_wall") and "cap_sunlight_readable" in ids:
            f["hint_cap"] = "cap_sunlight_readable"
            f["cap_label"] = CAP_HINT["cap_sunlight_readable"]
        elif f["kind"] in ("storefront_window", "window") and f.get("hint_cap") is None and "cap_weatherproof" in ids:
            f["hint_cap"] = "cap_weatherproof"
            f["cap_label"] = CAP_HINT["cap_weatherproof"]
    return model


def caps_text(model: dict[str, Any], description: str) -> str:
    words = [description or ""]
    for f in model.get("features", []):
        if f["kind"] in ("storefront_window", "glass_wall"):
            words.append("전면 유리창 햇빛 외부 노출 고휘도")
    return " ".join(words)


def summary_chips(model: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not model:
        return []
    est = model.get("estimated", True)
    ch = model.get("ceiling_h") or {}
    area_est = est and any(a.get("kind") in ("area_estimate", "photo_estimate") for a in model.get("assumptions", []))
    chips = [{"label": f"{T.pyeong_label(model.get('area_m2'))} · 층고 {T.num(ch.get('value'))}m" + (" · 추정" if area_est or ch.get("estimated") else ""),
              "kind": "area", "estimated": bool(area_est or ch.get("estimated"))}]
    for f in model.get("features", []):
        if f["kind"] == "columns":
            chips.append({"label": f"{f.get('label') or '기둥'} {f.get('count') or len(model.get('columns', []))}개", "kind": "column",
                          "estimated": False})
        elif f["kind"] == "night_visibility":
            continue
        else:
            lab = f["label"] + (f" ({f['cap_label']})" if f.get("cap_label") else "")
            chips.append({"label": lab, "kind": "feature", "estimated": False})
    return chips


def _feature_clauses(model: dict[str, Any]) -> list[tuple[str, str]]:
    """(연결형, 끝맺음형) 문장 조각."""
    out = []
    for f in model.get("features", []):
        lab = f.get("label") or ""
        if f["kind"] in ("storefront_window", "glass_wall") and f.get("cap_label") == "고휘도 권장":
            out.append((f"{T.jo(lab, '은/는')} 외부 노출이 큰 만큼 고휘도 사이니지가 어울리고",
                        f"{T.jo(lab, '은/는')} 외부 노출이 큰 만큼 고휘도 사이니지가 어울립니다"))
        elif f["kind"] in ("storefront_window", "window", "glass_wall"):
            out.append((f"{T.jo(lab, '은/는')} 낮 시간 밝기를 고려해 화면 위치를 정해야 하고",
                        f"{T.jo(lab, '은/는')} 낮 시간 밝기를 고려해 화면 위치를 정해야 합니다"))
        elif f["kind"] == "columns":
            n = f.get("count") or len(model.get("columns", []))
            out.append((f"기둥 {n}개는 랩핑형 디스플레이 포인트로 쓸 수 있고", f"기둥 {n}개는 랩핑형 디스플레이 포인트로 쓸 수 있습니다"))
    return out


def w_message(name: str, model: dict[str, Any] | None) -> str:
    """BE2 W — 「{공간 이름} 공간을 파악했습니다. {특징 문장들}. 이 공간에 배치할 삼성 제품을 입력해 주세요.」"""
    head = f"{name} 공간을 파악했습니다."
    clauses = _feature_clauses(model or {})
    if not clauses:
        return f"{head} 이 공간에 배치할 삼성 제품을 입력해 주세요."
    body = ", ".join([c[0] for c in clauses[:-1]] + [clauses[-1][1]])
    return f"{head} {body}. 이 공간에 배치할 삼성 제품을 입력해 주세요."


def features_text(model: dict[str, Any] | None) -> str:
    return ", ".join(c[1] for c in _feature_clauses(model or {}))


def stage_note(model: dict[str, Any] | None) -> str:
    """BE5G 「공간 구조」 메모 — 「120평 · 층고 4.5m · 전면 유리창 · 기둥 2개」."""
    if not model:
        return ""
    parts = [T.pyeong_label(model.get("area_m2")), f"층고 {T.num((model.get('ceiling_h') or {}).get('value'))}m"]
    for f in model.get("features", []):
        if f["kind"] == "columns":
            parts.append(f"기둥 {f.get('count') or len(model.get('columns', []))}개")
        elif f["kind"] != "night_visibility":
            parts.append(f["label"])
    return " · ".join(parts)


def area_label_short(model: dict[str, Any] | None) -> str:
    """배치안 오른쪽 위 「120평 · 4.5m」."""
    if not model:
        return ""
    return f"{T.pyeong_label(model.get('area_m2'))} · {T.num((model.get('ceiling_h') or {}).get('value'))}m"


def window_label(model: dict[str, Any] | None) -> str | None:
    for o in (model or {}).get("openings", []):
        if o["kind"] == "window" and o.get("label"):
            return o["label"]
    return None


def bbox_of(model: dict[str, Any]) -> tuple[float, float, float, float]:
    xs = [p[0] for r in model.get("rooms", []) for p in r["outline"]] or [0.0, 10.0]
    ys = [p[1] for r in model.get("rooms", []) for p in r["outline"]] or [0.0, 8.0]
    return min(xs), min(ys), max(xs), max(ys)


def recompute_area(model: dict[str, Any]) -> None:
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    polys = [Polygon(r["outline"]) for r in model.get("rooms", []) if len(r.get("outline", [])) >= 3]
    if polys:
        model["area_m2"] = round(unary_union(polys).area, 2)
