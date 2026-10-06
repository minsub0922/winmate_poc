"""현장 사진(08-birdseye §4.4 · §7.5) — 로컬 품질 검사 + i2t(벽 이름 · 요소 · 크기 힌트) + 종합(LLM) → 직사각형 공간 모델.

품질(§10.3): 휘도 평균 < 0.22 어두움 · 밝은 영역(> 0.85) > 25% 이고 그 밖 평균 < 0.30 역광 · 라플라시안 분산 < 50 흐림.
i2t 불가(기밀 차단) → 품질 검사만 + 설명 기반 사각형 모델(photo:quality_only).
"""
from __future__ import annotations

import io
import re
from typing import Any

from pydantic import BaseModel, Field

from . import config
from . import text as T

STATUS_LABEL = {
    "backlit": "역광 · 창 위치가 흐려요",
    "dark": "어두워요 · 다시 찍기 권장",
    "blurry": "흔들렸어요 · 다시 찍기 권장",
    "failed": "인식하지 못했어요 · 다시 인식",
}
REASON_CLAUSE = {
    "backlit": "역광으로 창 위치가 흐리니",
    "dark": "어두워 벽 경계가 잘 안 보이니",
    "blurry": "흔들려 형태가 흐리니",
}
STAGES = ["사진 밝기 확인 중", "벽 경계 찾는 중", "요소 찾는 중"]


class PhotoFeature(BaseModel):
    kind: str = Field(description="wall · window · door · display · board · column · desk · ceiling …")
    label: str = ""
    count: int | None = None


class SizeHint(BaseModel):
    object: str = Field(description="A4 · door · person")
    bbox: list[float] | None = None


class PhotoEst(BaseModel):
    wall_width_m: float | None = None
    ceiling_h_m: float | None = None


class PhotoI2T(BaseModel):
    wall_label: str = Field("", description="「상황판 벽」 「왼쪽 벽」 「창 쪽 벽」 「출입구 쪽」")
    dir_slot: int | None = Field(None, description="1 정면 · 2 왼쪽 · 3 창 쪽(오른쪽) · 4 출입구 쪽(뒤)")
    is_ceiling: bool = False
    features: list[PhotoFeature] = Field(default_factory=list)
    size_hints: list[SizeHint] = Field(default_factory=list)
    est: PhotoEst = Field(default_factory=PhotoEst)


class AggWall(BaseModel):
    dir: int = 1
    label: str = ""
    width_m_est: float | None = None


class PhotoAggregate(BaseModel):
    area_m2_est: float | None = None
    ceiling_h_m_est: float | None = None
    walls: list[AggWall] = Field(default_factory=list)
    facts_ko: list[str] = Field(default_factory=list)


class FactUpdate(BaseModel):
    wall_label: str | None = None
    wall_width_m: float | None = None
    ceiling_h_m: float | None = None
    area_m2: float | None = None


class PhotoFacts(BaseModel):
    facts_ko: list[str] = Field(default_factory=list)
    updates: FactUpdate = Field(default_factory=FactUpdate)


def quality(img_bytes: bytes) -> dict[str, float]:
    import numpy as np
    from PIL import Image, ImageOps

    im = Image.open(io.BytesIO(img_bytes))
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((640, 640))
    a = np.asarray(im, dtype=np.float32) / 255.0
    y = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    q = config.rules()["photo_quality"]
    bright = y > float(q["bright_thr"])
    ratio = float(bright.mean())
    rest = y[~bright]
    rest_mean = float(rest.mean()) if rest.size else 0.0
    g = y * 255.0
    lap = (-4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:])
    return {"mean": round(float(y.mean()), 4), "bright_ratio": round(ratio, 4), "rest_mean": round(rest_mean, 4),
            "lap_var": round(float(lap.var()), 2)}


def judge(q: dict[str, float]) -> str | None:
    """품질 판정 — None 이면 정상."""
    c = config.rules()["photo_quality"]
    if q["bright_ratio"] > float(c["bright_ratio"]) and q["rest_mean"] < float(c["backlit_rest_mean"]):
        return "backlit"
    if q["mean"] < float(c["dark_mean"]):
        return "dark"
    if q["lap_var"] < float(c["blur_var"]):
        return "blurry"
    return None


def found_label(i2t: dict[str, Any] | None) -> list[str]:
    """「인식 완료 · 벽 · 상황판」 · 「인식 완료 · 출입문 1」 의 찾은 요소."""
    if not i2t:
        return []
    out = []
    names = {"wall": "벽", "window": "창", "door": "출입문", "display": "상황판", "board": "상황판", "column": "기둥", "desk": "운영석"}
    for f in i2t.get("features") or []:
        nm = f.get("label") or names.get(f.get("kind", ""), f.get("kind", ""))
        if not nm:
            continue
        if f.get("count") and f.get("kind") in ("door", "window", "column"):
            nm = f"{nm} {f['count']}"
        if nm not in out:
            out.append(nm)
    return out[:3]


def status_label(photo: dict[str, Any]) -> str:
    st = photo["status"]
    if st == "recognizing":
        return f"인식 중 · {photo.get('stage_label') or STAGES[1]}"
    if st in ("recognized", "accepted"):
        found = photo.get("found") or []
        base = "인식 완료" if st == "recognized" else "그대로 사용"
        return f"{base} · {' · '.join(found)}" if found else base
    return STATUS_LABEL.get(st, st)


def summarize(photos: list[dict[str, Any]], *, space_name: str, description: str, facts: list[str],
              model: dict[str, Any] | None) -> dict[str, Any]:
    """BE1P 머리 · 찍은 방향 · 천장 · 요약 칩 · W 문장."""
    items = [p for p in photos if not p.get("is_ceiling")]
    ceil = [p for p in photos if p.get("is_ceiling")]
    rec = sum(1 for p in items if p["status"] in ("recognized", "accepted"))
    chk = sum(1 for p in items if p["status"] in ("backlit", "dark", "blurry"))
    ing = sum(1 for p in items if p["status"] == "recognizing")
    fail = sum(1 for p in items if p["status"] == "failed")
    n = len(items)
    head = f"인식 완료 {rec} · 확인 필요 {chk} · 인식 중 {ing}" + (f" · 실패 {fail}" if fail else "")
    slots = sorted({str(p.get("dir_slot")) for p in items if p.get("dir_slot") and str(p.get("dir_slot")).isdigit()})
    dir_count = min(4, len(slots) if slots else min(4, n))
    has_ceiling = any(p["status"] in ("recognized", "accepted") for p in ceil)
    ceil_h = None
    for p in ceil:
        if p.get("ceiling_h_m"):
            ceil_h = p["ceiling_h_m"]
    ceiling_label = f"있음 · 층고 {T.num(ceil_h)} m" if has_ceiling and ceil_h else ("있음" if has_ceiling else "없음 · 층고는 추정값")
    basis = rec
    chips: list[dict[str, Any]] = []
    if model and basis:
        chips.append({"label": f"약 {T.pyeong_label(model.get('area_m2')).replace('평', '')}평 추정", "kind": "estimate", "estimated": True})
        ch = model.get("ceiling_h") or {}
        chips.append({"label": f"층고 {T.num(ch.get('value'))} m" + (" 추정" if ch.get("estimated") else ""), "kind": "estimate",
                      "estimated": bool(ch.get("estimated"))})
    for f in facts:
        chips.append({"label": f, "kind": "fact", "estimated": False})
    # W
    verb = "읽고 있습니다" if ing or not basis else "읽었습니다"
    w = f"사진 {n}장에서 {space_name} 구조를 {verb}."
    bad = [p for p in items if p["status"] in ("backlit", "dark", "blurry")]
    clauses = []
    if bad:
        p = bad[0]
        lab = _short_wall(p.get("wall_label") or f"{p['n']}번")
        clauses.append(f"{lab} 사진은 {REASON_CLAUSE[p['status']]} 다시 찍어 주시")
    if not has_ceiling and n:
        clauses.append("천장 사진을 더하면 층고를 더 정확히 잡을 수 있습니다.")
    if clauses:
        if len(clauses) == 2:
            w += f" {clauses[0]}고, {clauses[1]}"
        elif clauses[0].endswith("주시"):
            w += f" {clauses[0]}어요."
        else:
            w += f" {clauses[0]}"
    return {"head": head, "dir_count": dir_count, "dir_label": f"{dir_count} / 4", "has_ceiling": has_ceiling,
            "ceiling_label": ceiling_label, "basis_count": basis, "summary_chips": chips, "w_message": w,
            "counts": {"total": n, "recognized": rec, "check": chk, "recognizing": ing, "failed": fail},
            "can_continue": basis >= 1}


def _short_wall(label: str) -> str:
    """「창 쪽 벽」 → 「창 쪽」."""
    lab = label.strip()
    return lab[:-2] if lab.endswith(" 벽") and len(lab) > 3 else lab


_WALL_W = re.compile(r"([가-힣A-Za-z ]{1,10}?벽)\s*(?:의\s*)?폭\s*(?:은|는|이|가|약)?\s*(\d+(?:\.\d+)?)\s*m")
_CEIL_F = re.compile(r"층고\s*(?:는|은|약)?\s*(\d+(?:\.\d+)?)\s*m")
_ROWS = re.compile(r"(\S+)\s*(\d+)\s*열(?:\s*(\d+)\s*석)?")


def regex_facts(text: str) -> dict[str, Any]:
    facts: list[str] = []
    upd: dict[str, Any] = {}
    m = _WALL_W.search(text)
    if m:
        wl = m.group(1).strip()
        upd["wall_label"] = wl
        upd["wall_width_m"] = float(m.group(2))
        facts.append(f"{wl} 폭 {T.num(float(m.group(2)))} m")
    m = _CEIL_F.search(text)
    if m:
        upd["ceiling_h_m"] = float(m.group(1))
        facts.append(f"층고 {T.num(float(m.group(1)))} m")
    for m in _ROWS.finditer(text):
        lab = m.group(1).strip(", ")
        tail = f" {m.group(3)}석" if m.group(3) else ""
        facts.append(f"{lab} {m.group(2)}열{tail}")
    return {"facts_ko": facts, "updates": upd}


def rect_from_photos(*, chip: str, description_rooms: list[dict[str, Any]], area_field_pyeong: float | None,
                     ceiling_field_m: float | None, agg: dict[str, Any] | None, photos: list[dict[str, Any]],
                     facts: dict[str, Any] | None) -> dict[str, Any]:
    """사각형 모델(가로 = 정면 벽 폭, 세로 = 면적 ÷ 가로, 없으면 1.5:1), estimated=true. 사용자 값이 추정값보다 우선."""
    from . import space as S

    upd = (facts or {}).get("updates") or {}
    rooms = [dict(r) for r in description_rooms] or [{"label": "", "features": []}]
    rooms = rooms[:1]
    area_py = area_field_pyeong
    if not area_py and (agg or {}).get("area_m2_est"):
        area_py = float(agg["area_m2_est"]) / T.PYEONG_M2
    if not area_py and rooms[0].get("area_pyeong"):
        area_py = float(rooms[0]["area_pyeong"])
    ceiling = ceiling_field_m or upd.get("ceiling_h_m")
    ceil_from_photo = None
    for p in photos:
        if p.get("is_ceiling") and p.get("ceiling_h_m"):
            ceil_from_photo = p["ceiling_h_m"]
    if not ceiling:
        ceiling = ceil_from_photo or (agg or {}).get("ceiling_h_m_est")
    front_w = upd.get("wall_width_m")
    if not front_w:
        for w in (agg or {}).get("walls") or []:
            if int(w.get("dir") or 0) == 1 and w.get("width_m_est"):
                front_w = float(w["width_m_est"])
    model = S.rect_model(rooms, chip=chip, area_field_pyeong=area_py, ceiling_field_m=None, front_width_m=front_w, source="photos")
    if ceiling:
        lo, hi = config.rules()["ceiling_range_m"]
        model["ceiling_h"] = {"value": round(min(max(float(ceiling), lo), hi), 2),
                              "estimated": not (ceiling_field_m or upd.get("ceiling_h_m") or ceil_from_photo)}
        model["assumptions"] = [a for a in model["assumptions"] if a["kind"] != "ceiling_estimate"]
        if model["ceiling_h"]["estimated"]:
            model["assumptions"].append({"kind": "ceiling_estimate", "ref": None, "action": "BE1P",
                                         "text_ko": f"천장 사진이 없어 층고를 {T.num(model['ceiling_h']['value'])} m로 추정했어요."})
    model["assumptions"] = [a for a in model["assumptions"] if a["kind"] != "shape_estimate"]
    model["assumptions"].append({"kind": "photo_estimate", "ref": None, "action": "BE1P",
                                 "text_ko": "현장 사진으로 공간 크기를 추정했어요. 도면이 있으면 더 정확해요."})
    # 벽 이름: 사진 방향 슬롯 → 벽(1 정면 · 2 왼쪽 · 3 오른쪽 · 4 후면)
    slot_wall = {1: "w1", 2: "w4", 3: "w2", 4: "w3"}
    for p in photos:
        if p.get("is_ceiling") or not p.get("wall_label") or not p.get("dir_slot"):
            continue
        try:
            slot = int(p["dir_slot"])
        except (TypeError, ValueError):
            continue
        wid = slot_wall.get(slot)
        for w in model["walls"]:
            if w["id"] == wid:
                w["label"] = p["wall_label"] if slot != 1 else (p["wall_label"] or "정면")
                if slot == 1:
                    w["label_alias"] = "정면"
    if upd.get("wall_width_m"):
        target = upd.get("wall_label") or ""
        for w in model["walls"]:
            if (target and target.replace(" ", "") in (w.get("label") or "").replace(" ", "")) or (not target and w["id"] == "w1"):
                w["dim_known"] = True
        model["dims"].append({"id": "d1", "label": f"{target or '정면 벽'} 폭", "wall_id": "w1", "annotated_m": None,
                              "computed_m": float(upd["wall_width_m"]), "choice": "manual", "manual_m": float(upd["wall_width_m"]),
                              "answered": True, "asked": False})
    model["facts"] = list((facts or {}).get("facts_ko") or []) + [f for f in (agg or {}).get("facts_ko") or []
                                                                   if f not in ((facts or {}).get("facts_ko") or [])]
    return model


def photo_prompt(n: int, description: str) -> str:
    return ("현장 사진 한 장이다. 이 사진이 보여 주는 벽의 이름(예: 상황판 벽 · 왼쪽 벽 · 창 쪽 벽 · 출입구 쪽), 방향 슬롯(1 정면 · 2 왼쪽 · "
            "3 창 쪽 · 4 출입구 쪽), 천장 사진인지, 보이는 요소(벽 · 창 · 문 · 상황판 · 기둥 · 운영석)와 개수, 크기 기준 물체(A4 · 문 · 사람) 상자, "
            f"벽 폭 · 층고 추정(m)을 JSON 으로. 사진 번호 {n}. 공간 설명: {description[:300]}")
