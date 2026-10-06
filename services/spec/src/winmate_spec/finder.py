"""조건으로 모델 찾기(SP1C, 06-spec §4.5 · §7.1). 칩 변경은 동기 · 결정적(LLM 없음), 문장 해석만 잡(spec_find)."""
from __future__ import annotations

import json
import logging
from typing import Any

from winmate_common.ai import ai
from winmate_common.ids import new_id

from .catalog import catalog
from .rules import finder as F
from .rules.fmt import fmt_num

log = logging.getLogger("winmate.spec.finder")

DEFAULT_CONDITIONS = {"sizes": [], "brightness": "desc", "usage": [], "install": [], "required": [], "off": []}


def empty_state(text: str | None = None) -> dict[str, Any]:
    return {"query_text": text, "conditions": dict(DEFAULT_CONDITIONS), "extra": [], "candidates": [], "hide_out": False, "view": "cards",
            "catalog_version": "", "total_candidates": 0, "agent_text": None, "sort_label": None, "customer": None, "place": None,
            "status": "idle", "error": None, "selected": [], "extra_caps": []}


async def compute(state: dict[str, Any]) -> dict[str, Any]:
    """pool(C2 상위 제품군 15) → 제품군의 모델 전부 → 판정 → 정렬 → 보일 카드."""
    cat = catalog()
    cond = {**DEFAULT_CONDITIONS, **(state.get("conditions") or {})}
    extra = state.get("extra") or []
    params = F.c2_params(cond, state.get("query_text"), state.get("extra_caps"))
    try:
        env = await cat.c2(**params)
    except Exception as exc:  # noqa: BLE001
        log.warning("C2 실패: %s", exc)
        env = {"result": {"families": []}}
    fams = ((env.get("result") or {}).get("families") or [])[:15]
    scores = {f["id"]: float(f.get("score") or 0) for f in fams}
    codes: list[str] = []
    fam_of: dict[str, str] = {}
    for f in fams:
        fe = await cat.family(f["id"])
        for m in fe.get("models") or []:
            if m.get("model_code") and m["model_code"] not in fam_of:
                codes.append(m["model_code"])
                fam_of[m["model_code"]] = f["id"]
    specs = await cat.specs(codes) if codes else {}
    selected = list(state.get("selected") or [])
    cands = []
    for code in codes:
        sp = specs.get(code)
        if not sp:
            continue
        ev = F.evaluate(sp, cond, extra)
        ref = f"kb:model:{sp['kb_model_id']}" if sp.get("kb_model_id") else code
        d = sp.get("derived") or {}
        power = next((a for k, a in (sp.get("attrs") or {}).items() if k.startswith("전원 › 소비전력") and "On Mode" in k), None)
        cands.append({
            "ref": ref, "model_code": code, "display_name": sp.get("display_name") or code, "series_label": F.series_label_of(sp),
            "size_inch": sp.get("size_inch"), "out": ev["out"], "ok": ev["ok"], "total": ev["total"], "no": ev["no"], "req_ok": ev["req_ok"],
            "rows": [{k: r[k] for k in ("key", "label", "value_text", "state")} for r in ev["rows"]], "c2_score": scores.get(fam_of[code], 0.0),
            "selected": ref in selected or code in selected, "nit": ev["nit"], "brightness_nit": ev["nit"],
            "operation": ((sp.get("attrs") or {}).get("디스플레이 › 제품 사용 시간") or {}).get("raw"),
            "power_text": (power or {}).get("raw"), "weight_text": f"{fmt_num(d['weight_kg_set'])} kg" if d.get("weight_kg_set") is not None else None,
            "out_reason": "; ".join(f"{r['label']} {r['value_text']}" for r in ev["rows"] if r["state"] == "no") or None,
            "extra_values": {e.get("key"): F._extra_value(sp, e.get("key") or "") for e in extra if e.get("key")},
        })
    ranked = F.rank(cands, cond, extra)
    shown = F.visible(ranked, bool(state.get("hide_out")))
    # 선택한 후보는 보이는 목록에 없어도 남긴다
    for c in ranked:
        if c["selected"] and c not in shown:
            shown.append(c)
    text, sort = F.agent_text(len([c for c in shown]), cond)
    out = {**state, "conditions": cond, "candidates": [{k: v for k, v in c.items() if k not in ("nit", "req_ok", "no", "extra_values")}
                                                        for c in shown],
           "total_candidates": len(ranked), "catalog_version": await cat.version(), "agent_text": text, "sort_label": sort,
           "status": "done", "error": None}
    return out


# ── 문장 해석(spec_find 1~3) ──────────────────────────────

PARSE_SCHEMA = {
    "type": "object",
    "properties": {
        "customer": {"type": "string"}, "place": {"type": "string"},
        "sizes": {"type": "array", "items": {"type": ["integer", "string"]}}, "around": {"type": "boolean"},
        "brightness": {"type": "string", "enum": ["any", "desc", "outdoor"]},
        "usage": {"type": "array", "items": {"type": "string", "enum": ["menu_board", "wayfinding", "monitoring", "meeting"]}},
        "install": {"type": "array", "items": {"type": "string", "enum": ["wall", "stand", "ceiling", "portrait"]}},
        "required": {"type": "array", "items": {"type": "string"}},
        "extra": {"type": "array", "items": {"type": "object", "properties": {
            "label": {"type": "string"}, "kind": {"type": "string", "enum": ["filter", "sort"]},
            "key": {"type": "string", "enum": ["bezel_mm", "weight_kg", "brightness_nit", "power_w"]},
            "op": {"type": "string", "enum": [">=", "<=", "asc", "desc"]}, "value": {"type": "number"}, "capability_id": {"type": "string"}},
            "required": ["label", "kind"]}},
    },
}

VOCAB = {"sizes": [43, 50, 55, 65, "75+"], "brightness": ["any", "desc", "outdoor"], "usage": list(F.USAGE_LABEL),
         "install": list(F.INSTALL_LABEL), "required": ["continuous_operation", "wall", "magicinfo", "stand", "outdoor"]}


async def parse_text(state: dict[str, Any], text: str) -> dict[str, Any]:
    """LLM `sp.parse_conditions`(고객사 이름이 있을 수 있어 confidential) → 칩 · 추가 조건 · 고객사 · 장소. 어휘 밖 값은 버린다."""
    payload = {"text": text, "current": state.get("conditions") or {}, "vocab": VOCAB}
    res = await ai().json("sp.parse_conditions", json.dumps(payload, ensure_ascii=False), PARSE_SCHEMA,
                          system="문장에서 디스플레이 조건을 칩 어휘로만 뽑는다. 어휘 밖 값은 쓰지 않는다. 고객사 · 장소 이름은 문장에 있을 때만.",
                          confidential=True)
    return res or {}


async def link_entities(text: str) -> dict[str, Any]:
    """KB A1 — 역량 · 공간 · 모델 언급(결정적)."""
    try:
        env = await catalog().a1(text)
    except Exception:  # noqa: BLE001
        return {"caps": [], "spaces": []}
    links = (env.get("result") or {}).get("links") or []
    return {"caps": [x["id"] for x in links if x.get("type") == "capability"], "spaces": [x["id"] for x in links if x.get("type") == "space_type"]}


def merge_conditions(state: dict[str, Any], parsed: dict[str, Any], linked: dict[str, Any], text: str) -> dict[str, Any]:
    """해석 결과를 칩에 합친다 — 사용자가 끈 칩은 다시 켜지 않는다. 필수 기본값: '24시간' → 24시간 운영, '벽걸이' → 벽걸이."""
    cond = {**DEFAULT_CONDITIONS, **(state.get("conditions") or {})}
    off = set(cond.get("off") or [])

    def add(lst: list[str], v: str, tag: str) -> None:
        if v not in lst and tag not in off:
            lst.append(v)

    sizes = list(cond.get("sizes") or [])
    for s in parsed.get("sizes") or []:
        try:
            n = int(str(s).rstrip("+").strip())
        except ValueError:
            continue
        v = "75+" if n >= 75 else str(n)
        if v in F.SIZE_CHIPS:
            add(sizes, v, f"size:{v}")
    cond["sizes"] = sizes
    if parsed.get("brightness") in F.BRIGHT_LABEL and "brightness" not in off:
        cond["brightness"] = parsed["brightness"]
    usage = list(cond.get("usage") or [])
    for u in parsed.get("usage") or []:
        if u in F.USAGE_LABEL:
            add(usage, u, f"usage:{u}")
    cond["usage"] = usage
    inst = list(cond.get("install") or [])
    for i in parsed.get("install") or []:
        if i in F.INSTALL_LABEL:
            add(inst, i, f"install:{i}")
    cond["install"] = inst
    req = list(cond.get("required") or [])
    for r in parsed.get("required") or []:
        if r in VOCAB["required"]:
            add(req, r, f"required:{r}")
    if ("24시간" in text or "24/7" in text or "cap_continuous_operation" in linked.get("caps", [])):
        add(req, "continuous_operation", "required:continuous_operation")
    if "벽걸이" in text:
        add(req, "wall", "required:wall")
        add(inst, "wall", "install:wall")
    cond["required"] = req
    extra = list(state.get("extra") or [])
    for e in parsed.get("extra") or []:
        if not e.get("label"):
            continue
        if any(x.get("label") == e["label"] for x in extra):
            continue
        extra.append({"id": new_id("sfx")[-8:], "label": e["label"], "kind": e.get("kind") or "filter", "key": e.get("key"),
                      "op": e.get("op"), "value": e.get("value"), "capability_id": e.get("capability_id")})
    caps = [c for c in linked.get("caps") or [] if c not in ("cap_continuous_operation",)]
    return {**state, "conditions": cond, "extra": extra, "extra_caps": caps, "query_text": text,
            "customer": parsed.get("customer") or state.get("customer"), "place": parsed.get("place") or state.get("place")}


# ── 다른 화면에서 올 때 미리 채우기(SP1R `대안 보기` · `대안 모델 찾기`, SP3W `다른 후보 찾기`) ──

def _size_chip(n: float | int | None) -> str | None:
    if n is None:
        return None
    n = int(n)
    if n >= 75:
        return "75+"
    return str(n) if str(n) in F.SIZE_CHIPS else None


def _chip_num(chip: str) -> int:
    return 75 if chip == "75+" else int(chip)


def is_empty(state: dict[str, Any]) -> bool:
    """조건 · 문장이 하나도 없으면 후보를 찾지 않는다(SP1C 처음 상태)."""
    c = state.get("conditions") or {}
    return not (c.get("sizes") or c.get("usage") or c.get("install") or c.get("required") or state.get("extra") or state.get("query_text")
                or c.get("brightness") == "outdoor")


def preset_state(sheet: dict[str, Any], preset: str) -> tuple[dict[str, Any], list[str]]:
    """preset → (조건, 미리 선택). `row:{srq}` = 그 미충족 행의 대안 · `alternatives` = 미충족 요구 + 충족한 역량 필수 ·
    `warning:{swn}` = 단종 · 카탈로그 없음 모델의 크기(결정적)."""
    from winmate_common.errors import ApiError

    from .rules.fmt import inch_from_code
    cond: dict[str, Any] = {**DEFAULT_CONDITIONS, "sizes": [], "usage": [], "install": [], "required": [], "off": []}
    selected: list[str] = []
    comp = sheet.get("compliance") or {}
    rows = comp.get("rows") or []
    if preset.startswith("row:"):
        rid = preset.split(":", 1)[1]
        r = next((x for x in rows if x["id"] == rid), None)
        if r is None:
            raise ApiError(404, "NOT_FOUND", "요구 행을 찾을 수 없어요.")
        alt = r.get("alternative") or {}
        chip = _size_chip(inch_from_code(alt.get("model_code"))) if alt else None
        if chip:
            cond["sizes"] = [chip]
        if alt.get("product_ref"):
            selected = [alt["product_ref"]]
    elif preset == "alternatives":
        sizes: list[str] = []
        for r in rows:
            p = r.get("parsed") or {}
            if r.get("verdict") == "fail" and p.get("key") == "screen_size_inch" and p.get("value"):
                v = float(p["value"])
                op = p.get("op") or ">="
                for chip in F.SIZE_CHIPS:
                    n = _chip_num(chip)
                    if (op == ">=" and n >= v) or (op == "<=" and n <= v) or (op == "==" and n == int(v)):
                        if chip not in sizes:
                            sizes.append(chip)
            if r.get("verdict") == "pass" and "cap_continuous_operation" in (p.get("capabilities") or []):
                if "continuous_operation" not in cond["required"]:
                    cond["required"].append("continuous_operation")
        cond["sizes"] = sorted(sizes, key=_chip_num)
    elif preset.startswith("warning:"):
        wid = preset.split(":", 1)[1]
        w = next((x for x in sheet.get("warnings") or [] if x["id"] == wid), None)
        if w is None:
            raise ApiError(404, "NOT_FOUND", "경고를 찾을 수 없어요.")
        p = next((x for x in sheet.get("products") or [] if x["id"] == w.get("product_id")), None) or {}
        chip = _size_chip(p.get("size_inch") or inch_from_code(p.get("model_code")) or inch_from_code(p.get("display_name")))
        if chip:
            cond["sizes"] = [chip]
    else:
        raise ApiError(422, "VALIDATION_FAILED", f"알 수 없는 preset 이에요: {preset}")
    return cond, selected
