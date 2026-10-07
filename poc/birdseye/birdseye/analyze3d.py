"""3D 조감도 ① 요구사항 분석 — AI(LLM)가 콘셉트·마감·조명·가구를 고른다. 모델이 없거나 실패하면 규칙 기반.

AI 는 라이브러리(seed/materials.json · furniture.json)에 있는 키 중에서만 고르고, 고른 이유를 짧게 남긴다.
제품 위치·대수는 2D 조감도가 연결되면 2D 를 따르고(바꾸지 않음), 아니면 F2 권장 수량을 기본으로 AI 가 조정할 수 있다.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from .catalog import CATEGORY_NAMES, Catalog, screen_size
from .llm import ModelClient

SEED = Path(__file__).resolve().parent / "seed"
LIB = json.loads((SEED / "materials.json").read_text(encoding="utf-8"))
FURN = json.loads((SEED / "furniture.json").read_text(encoding="utf-8"))
FURN_TYPES = {f["type"]: f for f in FURN["types"]}
SPACE_TYPES = {s["code"]: s for s in FURN["space_types"]}
DECOR = {"plinth", "planter_large", "planter_small", "rug"}

KEYWORDS = {  # 문장 단서 → 분위기
    "gallery": ["갤러리", "전시", "아트", "작품", "미술"], "warm": ["따뜻", "아늑", "포근", "우드", "원목"],
    "premium": ["프리미엄", "고급", "럭셔리", "하이엔드", "VIP"], "minimal": ["미니멀", "심플", "깔끔", "모던"],
    "vibrant": ["활기", "생동", "역동", "컬러풀", "화려"], "calm": ["차분", "편안", "조용", "휴식"],
    "natural": ["자연", "식물", "그린", "카페", "내추럴"], "tech": ["관제", "상황판", "테크", "미래", "디지털", "운영석"],
    "clean": ["병원", "의료", "청결", "깨끗", "위생"],
}
CONTENT_BY_SPACE = {"lobby": "brand", "sales_floor": "brand", "exhibition_showroom": "art", "meeting_room": "board",
                    "open_office": "info", "classroom": "board", "waiting_area": "info", "hospital_reception": "info",
                    "guest_room": "brand", "control_room": "dashboard", "dining_hall": "menu", "lounge": "art"}


def brief_schema(product_codes: list[str], linked: bool) -> dict:
    furn_types = list(FURN_TYPES)
    s = {
        "type": "object",
        "properties": {
            "understanding": {"type": "string", "description": "요구사항을 한 문장(40자 안팎)으로 이해한 내용"},
            "concept": {"type": "string", "enum": list(LIB["concepts"])},
            "concept_reason": {"type": "string", "description": "40자 이내"},
            "floor": {"type": "string", "enum": list(LIB["floors"])},
            "wall": {"type": "string", "enum": list(LIB["walls"])},
            "accent": {"type": "string", "enum": list(LIB["accents"])},
            "fabric": {"type": "string", "enum": list(LIB["fabrics"])},
            "finish_reason": {"type": "string", "description": "40자 이내"},
            "light_k": {"type": "integer", "enum": [2700, 3000, 3500, 4000, 5000]},
            "lighting": {"type": "string", "enum": list(LIB["lighting"])},
            "lighting_reason": {"type": "string", "description": "40자 이내"},
            "plants": {"type": "string", "enum": list(LIB["plants"])},
            "screen_content": {"type": "string", "enum": list(LIB["screen_contents"])},
            "furniture": {
                "type": "array", "maxItems": 8,
                "items": {"type": "object", "properties": {
                    "type": {"type": "string", "enum": furn_types},
                    "count": {"type": "integer", "minimum": 0, "maximum": 24},
                    "reason": {"type": "string", "description": "30자 이내"}},
                    "required": ["type", "count", "reason"]}},
        },
        "required": ["understanding", "concept", "concept_reason", "floor", "wall", "accent", "fabric", "finish_reason",
                     "light_k", "lighting", "lighting_reason", "plants", "screen_content", "furniture"],
    }
    if not linked and product_codes:
        s["properties"]["product_counts"] = {
            "type": "array",
            "items": {"type": "object", "properties": {
                "code": {"type": "string", "enum": product_codes},
                "count": {"type": "integer", "minimum": 1, "maximum": 40},
                "reason": {"type": "string", "description": "30자 이내"}},
                "required": ["code", "count", "reason"]}}
    return s


SYSTEM = """당신은 삼성 B2B 제안서에 넣을 '3D 조감도'의 공간 구성을 정하는 인테리어 플래너입니다.
- 3D 조감도는 '이 공간에서 이런 느낌으로 쓰이겠다'를 보여주는 개략 이미지입니다. 정확한 수치·수량은 2D 조감도가 맡습니다.
- 반드시 스키마의 enum 값 중에서만 고르세요. 새 이름을 만들지 마세요.
- 이유(reason)는 한국어로 짧게(30~40자), 요구사항·분위기·공간 유형·제품 중 무엇 때문인지 드러나게 쓰세요.
- 가구는 공간 면적에 맞게 절제해서 고르세요(통로·화면 앞을 막지 않게). 제품(삼성 디스플레이 등)은 가구로 넣지 마세요.
- 2D 조감도가 연결된 경우 제품 위치·대수는 바꿀 수 없습니다(product_counts 를 내지 마세요).
- 제품 모델명·수치를 지어내지 마세요."""


def _product_lines(project: dict, catalog: Catalog) -> list[str]:
    out = []
    for code in project["input"].get("products", []):
        p = catalog.get(code)
        if not p:
            continue
        sw, sh = screen_size(p, p["h"] > p["w"])
        out.append(f"- {p['short']} ({code}) · {p['name']} · {CATEGORY_NAMES.get(p['category'], p['category'])} · 외형 {p['w']:,.0f}×{p['h']:,.0f}×{p['d']:,.0f} mm")
    return out


def build_prompt(project: dict, layout_info: dict, catalog: Catalog, mode: str = "initial", prev: dict | None = None,
                 request: str | None = None) -> str:
    inp = project["input"]
    sp = layout_info["space"]
    st = SPACE_TYPES.get(inp.get("space_type") or sp.get("space_type") or "lobby", {})
    moods = ", ".join(LIB["moods"].get(m, m) for m in inp.get("moods", [])) or "(없음)"
    lines = [
        f"[요구사항] {inp.get('text', '').strip() or '(비어 있음)'}",
        f"[공간 유형] {st.get('label', inp.get('space_type'))} ({inp.get('space_type')})",
        f"[분위기] {moods}",
        f"[공간 크기] {sp['width']:,.0f} × {sp['depth']:,.0f} mm, 층고 {sp['height']:,.0f} mm ({layout_info['space_basis']})",
        "[제품]", *(_product_lines(project, catalog) or ["- (없음)"]),
        f"[2D 조감도 연결] {'예 — 제품 위치·대수 고정' if layout_info['linked'] else '아니오'}",
    ]
    if layout_info.get("fixtures_2d"):
        lines.append("[2D 집기 블록] " + ", ".join(f"{k} {v}개" for k, v in layout_info["fixtures_2d"].items()))
    if layout_info.get("rec_counts") and not layout_info["linked"]:
        lines.append("[룰 권장 수량(F2)] " + ", ".join(f"{k} {v}대" for k, v in layout_info["rec_counts"].items()))
    pr = inp.get("photo_read")
    if pr:
        lines.append("[현장 사진에서 읽은 것] " + " · ".join(pr.get("structure", []) + pr.get("mood", [])))
        if pr.get("finishes"):
            lines.append("[사진에서 읽은 마감 후보] " + json.dumps(pr["finishes"], ensure_ascii=False))
    if (inp.get("photo_text") or "").strip():
        lines.append(f"[사진에 없는 정보] {inp['photo_text'].strip()}")
    if mode == "alternative" and prev:
        lines.append(f"[앞 안] 콘셉트 {prev.get('concept')} · 바닥 {prev.get('floor')} · 벽 {prev.get('wall')} · 포인트 {prev.get('accent')}")
        lines.append("[지시] 앞 안과 확실히 다른 콘셉트로 다른 안을 하나 만드세요. 요구사항은 그대로 지킵니다.")
    if mode == "request" and prev:
        lines.append("[현재 안] " + json.dumps({k: prev.get(k) for k in ("concept", "floor", "wall", "accent", "fabric", "light_k",
                                                                       "lighting", "plants", "screen_content", "furniture")}, ensure_ascii=False))
        lines.append(f"[사용자 한 줄 요청] {request}")
        lines.append("[지시] 요청에 해당하는 항목만 바꾸고 나머지는 현재 안을 유지하세요. 바꾼 이유를 reason 에 적으세요.")
    return "\n".join(lines)


# ── 규칙 기반(모델 없이) ──

def _all_text(inp: dict) -> str:
    """요구사항 + '사진에 없는 정보'(BR1P)."""
    return " ".join(t for t in ((inp.get("text") or ""), (inp.get("photo_text") or "")) if t).strip()


def _mood_scores(project: dict) -> dict[str, float]:
    inp = project["input"]
    text = _all_text(inp)
    sc: dict[str, float] = {}
    for m in inp.get("moods", []):
        sc[m] = sc.get(m, 0) + 2.0
    for m, kws in KEYWORDS.items():
        for k in kws:
            if k in text:
                sc[m] = sc.get(m, 0) + 1.0
    return sc


def _rank_concepts(project: dict) -> list[tuple[float, str]]:
    sc = _mood_scores(project)
    st = SPACE_TYPES.get(project["input"].get("space_type") or "lobby", {})
    ranked = []
    for key, c in LIB["concepts"].items():
        s = sum(sc.get(m, 0) for m in c["moods"])
        if key == st.get("concept"):
            s += 1.5
        ranked.append((s, key))
    ranked.sort(key=lambda t: (-t[0], list(LIB["concepts"]).index(t[1])))
    return ranked


def _furniture_rules(project: dict, layout_info: dict, concept: dict, plants: str) -> list[dict]:
    inp = project["input"]
    st = SPACE_TYPES.get(inp.get("space_type") or "lobby", SPACE_TYPES["lobby"])
    sp = layout_info["space"]
    area = sp["width"] * sp["depth"] / 1e6
    f = max(0.5, min(2.0, area / st["area_m2"]))
    reqs: dict[str, dict] = {}
    for t, n in st["furniture"]:
        if t in ("planter_large", "planter_small", "plinth", "rug"):
            continue
        reqs[t] = {"type": t, "count": max(1, round(n * (f if t in ("table_set_2", "table_set_4", "work_desk", "desk_pair_set", "waiting_chairs", "operator_desk", "display_shelf") else 1))),
                   "reason": f"{st['label']}에 맞는 기본 구성"}
    cats = layout_info["categories"]
    if cats & {"led_allinone", "signage_large", "led_cabinet"}:
        reqs["bench"] = {"type": "bench", "count": 3 if area > 150 else 2, "reason": "미디어월을 마주 보는 관람석"}
    if "flip" in cats:
        reqs["exp_counter"] = {"type": "exp_counter", "count": 1, "reason": "전자칠판 곁 체험·상담 카운터"}
    if "videowall" in cats:
        reqs.pop("bench", None)
        reqs["operator_desk"] = {"type": "operator_desk", "count": reqs.get("operator_desk", {}).get("count", 8), "reason": "상황판을 보는 운영석 2열"}
    moods = set(inp.get("moods", [])) | {m for m, v in _mood_scores(project).items() if v >= 1}
    if "gallery" in moods and "plinth" not in reqs:
        reqs["plinth"] = {"type": "plinth", "count": 4 if area > 150 else 2, "reason": "갤러리처럼 작품·제품을 올리는 플린스"}
    n_pl = {"none": 0, "few": 2, "some": 4, "many": 6}[plants]
    if area < 60:
        n_pl = min(n_pl, 2)
    if n_pl:
        reqs["planter_large" if area > 60 else "planter_small"] = {"type": "planter_large" if area > 60 else "planter_small", "count": n_pl,
                                                                     "reason": f"식물 '{LIB['plants'][plants]}' — 모서리·입구 양옆"}
    if "lounge_sofa" in reqs and "coffee_table" not in reqs:
        reqs["coffee_table"] = {"type": "coffee_table", "count": 1, "reason": "소파 앞 테이블"}
    if layout_info.get("fixtures_2d"):
        for t, n in layout_info["fixtures_2d"].items():
            reqs[t] = {"type": t, "count": n, "reason": "2D 집기 블록 위치를 그대로 사용"}
    return list(reqs.values())


def rule_brief(project: dict, layout_info: dict, concept_key: str | None = None) -> dict:
    inp = project["input"]
    ranked = _rank_concepts(project)
    key = concept_key or ranked[0][1]
    c = LIB["concepts"][key]
    text = _all_text(inp)
    lighting = "night" if re.search(r"야간|밤", text) else ("evening" if "저녁" in text else "day")
    plants = c["plants"]
    if any(k in text for k in KEYWORDS["natural"]):
        plants = "many"
    st = SPACE_TYPES.get(inp.get("space_type") or "lobby", SPACE_TYPES["lobby"])
    moods_txt = " · ".join(LIB["moods"].get(m, m) for m in inp.get("moods", []))
    phrase = _understanding(text, st["label"])
    b = {
        "understanding": phrase,
        "concept": key, "concept_reason": f"분위기 '{moods_txt or c['label']}' + {st['label']} 기본 콘셉트",
        "floor": c["floor"], "wall": c["wall"], "accent": c["accent"], "fabric": c["fabric"],
        "finish_reason": f"{LIB['concepts'][key]['label']} 조합 — 화면이 돋보이게 벽은 밝고 채도 낮게" if LIB["walls"][c["wall"]]["base"][0] > 0.5 else f"{LIB['concepts'][key]['label']} 조합",
        "light_k": c["light_k"], "lighting": lighting,
        "lighting_reason": ("창 채광 + " if layout_info["has_windows"] else "") + f"{c['light_k']}K 라인 조명",
        "plants": plants, "screen_content": "art" if "gallery" in inp.get("moods", []) and inp.get("space_type") == "exhibition_showroom" else CONTENT_BY_SPACE.get(inp.get("space_type") or "lobby", "brand"),
        "furniture": _furniture_rules(project, layout_info, c, plants),
    }
    fin = ((inp.get("photo_read") or {}).get("finishes") or {})
    if not concept_key and fin:  # 현장 사진에서 읽은 마감을 그대로 쓴다(다른 안은 콘셉트 마감)
        used = []
        for k, lib_key in (("floor", "floors"), ("wall", "walls"), ("accent", "accents")):
            if fin.get(k) in LIB[lib_key]:
                b[k] = fin[k]
                used.append(LIB[lib_key][fin[k]]["label"])
        if used:
            b["finish_reason"] = "현장 사진에서 읽은 마감 — " + " · ".join(used)
    if not layout_info["linked"] and layout_info.get("rec_counts_by_code"):
        b["product_counts"] = [{"code": code, "count": n, "reason": "공간 치수 기준 권장 수량(룰)"}
                               for code, n in layout_info["rec_counts_by_code"].items()]
    return b


def _understanding(text: str, space_label: str) -> str:
    t = (text or "").strip()
    m = re.search(r"([^\s.!?,]+(?:\s+[^\s.!?,]+){0,5}?)\s*(같은|처럼|느낌의|분위기의)(?:\s|$)", t)
    if m:
        words = m.group(1).split()[-3:]
        kw = "같은" if m.group(2) in ("같은", "처럼") else m.group(2)
        return f"'{' '.join(words)} {kw} {space_label}'"
    first = re.split(r"[.!?\n]", t)[0].strip()
    if first:
        return f"'{first[:40]}'"
    return f"'{space_label}'"


# ── 정리·검증 ──

def normalize(raw: dict | None, fallback: dict, linked: bool, product_codes: list[str]) -> tuple[dict, list[str]]:
    """모델 출력을 라이브러리 키로 맞추고 빠진 값은 규칙 결과로 채운다. 고친 항목 목록도 돌려준다."""
    if not raw:
        return copy.deepcopy(fallback), []
    b = copy.deepcopy(fallback)
    fixed = []
    enums = {"concept": LIB["concepts"], "floor": LIB["floors"], "wall": LIB["walls"], "accent": LIB["accents"],
             "fabric": LIB["fabrics"], "lighting": LIB["lighting"], "plants": LIB["plants"], "screen_content": LIB["screen_contents"]}
    for k, allowed in enums.items():
        v = raw.get(k)
        if v in allowed:
            b[k] = v
        elif v is not None:
            fixed.append(k)
    if raw.get("light_k") in (2700, 3000, 3500, 4000, 5000):
        b["light_k"] = raw["light_k"]
    for k in ("understanding", "concept_reason", "finish_reason", "lighting_reason"):
        if isinstance(raw.get(k), str) and raw[k].strip():
            b[k] = raw[k].strip()[:80]
    furn = []
    for it in raw.get("furniture") or []:
        t = it.get("type")
        if t not in FURN_TYPES:
            fixed.append(f"furniture:{t}")
            continue
        n = int(max(0, min(24, it.get("count") or 0)))
        if n:
            furn.append({"type": t, "count": n, "reason": (it.get("reason") or "")[:60]})
    if furn:
        if linked:  # 2D 집기 블록은 지킨다
            keep = {f["type"]: f for f in fallback["furniture"] if f.get("reason", "").startswith("2D 집기")}
            furn = [f for f in furn if f["type"] not in keep] + list(keep.values())
        b["furniture"] = furn
    if not linked:
        pc = []
        for it in raw.get("product_counts") or []:
            if it.get("code") in product_codes and isinstance(it.get("count"), int) and 0 < it["count"] <= 40:
                pc.append({"code": it["code"], "count": it["count"], "reason": (it.get("reason") or "")[:60]})
        if pc:
            seen = {p["code"] for p in pc}
            pc += [p for p in fallback.get("product_counts", []) if p["code"] not in seen]
            b["product_counts"] = pc
    else:
        b.pop("product_counts", None)
    return b, fixed


def analyze(project: dict, layout_info: dict, catalog: Catalog, client: ModelClient | None, mode: str = "initial",
            prev: dict | None = None, request: str | None = None) -> dict:
    """요구사항 → 브리프(+ 메타). mode: initial | alternative | request."""
    linked = layout_info["linked"]
    codes = list(project["input"].get("products", []))
    if mode == "alternative" and prev:
        ranked = [k for _, k in _rank_concepts(project) if k != prev.get("concept")]
        used = set(layout_info.get("avoid_concepts", []))
        alt_key = next((k for k in ranked if k not in used), ranked[0])
        fallback = rule_brief(project, layout_info, alt_key)
    elif mode == "request" and prev:
        fallback = apply_request_rules(prev, request or "", layout_info)
    else:
        fallback = rule_brief(project, layout_info)
    raw, meta = (None, {"source": "rules", "reason": "모델 클라이언트 없음"})
    if client is not None:
        user = build_prompt(project, layout_info, catalog, mode, prev, request)
        raw, meta = client.generate_json(SYSTEM, user, brief_schema(codes, linked), "birdseye_brief",
                                         confidential=bool(project.get("confidential")))
    brief, fixed = normalize(raw, fallback, linked, codes)
    if mode == "request" and prev:
        brief["changes"] = _diff(prev, brief)
    brief["meta"] = {"source": meta.get("source", "rules"), "reason": meta.get("reason"), "model": meta.get("model"),
                     "fixed": fixed, "mode": mode}
    return brief


def _diff(a: dict, b: dict) -> list[str]:
    out = []
    names = {"concept": "콘셉트", "floor": "바닥", "wall": "벽", "accent": "포인트", "fabric": "패브릭", "light_k": "색온도",
             "lighting": "조명", "plants": "식물", "screen_content": "화면 콘텐츠"}
    lab = {"concept": LIB["concepts"], "floor": LIB["floors"], "wall": LIB["walls"], "accent": LIB["accents"],
           "fabric": LIB["fabrics"], "lighting": LIB["lighting"]}
    for k, n in names.items():
        if a.get(k) != b.get(k):
            def L(v):
                d = lab.get(k, {})
                if isinstance(d.get(v), dict):
                    return d[v]["label"]
                if k == "plants":
                    return LIB["plants"].get(v, v)
                if k == "screen_content":
                    return LIB["screen_contents"].get(v, v)
                return f"{v}K" if k == "light_k" else str(v)
            out.append(f"{n}: {L(a.get(k))} → {L(b.get(k))}")
    fa = {f["type"]: f["count"] for f in a.get("furniture", [])}
    fb = {f["type"]: f["count"] for f in b.get("furniture", [])}
    for t in sorted(set(fa) | set(fb)):
        if fa.get(t, 0) != fb.get(t, 0):
            out.append(f"{FURN_TYPES[t]['label']}: {fa.get(t, 0)} → {fb.get(t, 0)}")
    return out


def apply_request_rules(prev: dict, text: str, layout_info: dict) -> dict:
    """한 줄 요청을 규칙으로 해석(모델이 없을 때)."""
    b = copy.deepcopy(prev)
    b.pop("meta", None)
    b.pop("changes", None)
    t = text or ""
    furn = {f["type"]: f for f in b.get("furniture", [])}

    def setc(key):
        c = LIB["concepts"][key]
        b.update(concept=key, floor=c["floor"], wall=c["wall"], accent=c["accent"], fabric=c["fabric"], light_k=c["light_k"])
        b["concept_reason"] = f"요청 '{t[:20]}' 반영"

    if re.search(r"밝게|환하게|화사", t):
        b["lighting"] = "day"
        if LIB["walls"][b["wall"]]["base"][0] < 0.5:
            b["wall"] = "warm_white"
        b["lighting_reason"] = "요청 반영 — 밝은 주간 조명"
    if re.search(r"어둡게|무드|야간|밤", t):
        b["lighting"] = "night" if re.search(r"야간|밤", t) else "evening"
        b["lighting_reason"] = "요청 반영 — 화면이 돋보이는 어두운 조명"
    if "저녁" in t:
        b["lighting"] = "evening"
    if re.search(r"따뜻|웜", t):
        b["light_k"] = 2700 if b["light_k"] <= 3000 else 3000
        if b["floor"] in ("polished_concrete", "terrazzo", "carpet_gray", "vinyl_light"):
            b["floor"] = "oak_wood"
    if re.search(r"차갑|시원|쿨", t):
        b["light_k"] = 5000 if b["light_k"] >= 4000 else 4000
    if re.search(r"고급|프리미엄|럭셔리", t):
        setc("premium_lounge")
    if re.search(r"미니멀|심플|깔끔|비워", t):
        setc("modern_minimal")
        for f in b["furniture"]:
            if f["type"] in DECOR:
                f["count"] = max(0, f["count"] // 2)
        b["plants"] = "few"
    if re.search(r"갤러리|전시", t):
        setc("gallery_white" if "화이트" in t or "하얀" in t else "gallery_warm")
        furn.setdefault("plinth", {"type": "plinth", "count": 0, "reason": ""})
        furn["plinth"]["count"] = max(furn["plinth"]["count"], 4)
        furn["plinth"]["reason"] = "요청 반영 — 갤러리 플린스"
        if furn["plinth"] not in b["furniture"]:
            b["furniture"].append(furn["plinth"])
    if re.search(r"식물|그린|화분", t):
        b["plants"] = "few" if re.search(r"줄|빼|없", t) else "many"
    m = re.search(r"(소파|벤치|플랜터|화분|플린스|카운터|테이블)[^\d]*(\d+)\s*개", t)
    name_map = {"소파": "lounge_sofa", "벤치": "bench", "플랜터": "planter_large", "화분": "planter_large", "플린스": "plinth",
                "카운터": "exp_counter", "테이블": "coffee_table"}
    if m and name_map.get(m.group(1)) in furn:
        furn[name_map[m.group(1)]]["count"] = int(m.group(2))
    for word, typ in name_map.items():
        if typ in furn and re.search(word + r"[^가-힣]*(빼|없애|제거)", t):
            furn[typ]["count"] = 0
        if typ in furn and re.search(word + r"[^가-힣]*(줄여|적게)", t):
            furn[typ]["count"] = max(0, furn[typ]["count"] - 1)
        if typ in furn and re.search(word + r"[^가-힣]*(늘려|더)", t):
            furn[typ]["count"] += 1
    b["furniture"] = [f for f in b["furniture"] if f["count"] > 0 or f["type"] in furn]
    return b
