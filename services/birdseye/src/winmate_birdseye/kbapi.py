"""kb 호출(계약 contracts/kb.json) — 제품 검색 · 제품 치수/크기 · 배치 규칙 · C1(공간 → 역량) · E3(존 문구 근거).

치수는 지어내지 않는다: KB 스펙 「제품 크기」(가로 x 높이 x 깊이 mm) → 없으면 대각 inch 로 16:9 · 베젤 3% · 깊이 0.08 m 계산
(dims_source=computed) → 그것도 없으면 estimated(화면에 「[확인 필요]」).
"""
from __future__ import annotations

import logging
import re
from typing import Any

from winmate_common.client import ServiceClient

from .engine import computed_dims, size_inch

log = logging.getLogger("winmate.birdseye.kb")

_SIZE_RE = re.compile(r'(\d{2,3}(?:\.\d)?)\s*(?:"|형|인치|inch)')
_DIM_RE = re.compile(r"([\d,.]+)\s*[xX×]\s*([\d,.]+)\s*[xX×]\s*([\d,.]+)\s*mm")
_NIT_RE = re.compile(r"([\d,]+)\s*(?:\(|nit|cd)")
_GENERIC_PREFIX = ("Smart Signage ", "Outdoor Signage ", "Indoor Signage ", "Signage ", "Smart LED Signage ", "실내용 ", "실외용 ")
_DROP_TOKENS = {"All-in-One", "Series", "시리즈", "for", "Business", "전자칠판"}


def kb() -> ServiceClient:
    return ServiceClient("kb", timeout=30)


def short_name(name: str, model_display: str | None = None) -> str:
    """표시명 → 약칭: 「Outdoor Signage OH55C」 → 「OH55C」, 「The Wall All-in-One IAB」 → 「The Wall IAB」."""
    n = (name or "").strip()
    for pre in _GENERIC_PREFIX:
        if n.startswith(pre):
            n = n[len(pre):].strip()
            break
    toks = [t for t in n.split() if t not in _DROP_TOKENS]
    out = " ".join(toks).strip()
    if not out:
        out = model_display or name
    if len(out) > 28 and model_display:
        out = model_display
    return out


def size_options_from(meta_line: str | None) -> list[str]:
    out: list[str] = []
    for m in _SIZE_RE.finditer(meta_line or ""):
        v = m.group(1)
        v = v[:-2] if v.endswith(".0") else v
        s = f'{v}"'
        if s not in out:
            out.append(s)
    return out


def role_for(name: str, category_path: list[str], brightness: float | None = None) -> tuple[str, str]:
    """(role, mount_default)."""
    hay = " ".join([name or ""] + list(category_path or []))
    low = hay.lower()
    if "실외" in hay or "outdoor" in low or "윈도우" in hay or "window" in low or (brightness or 0) >= 2500:
        return "window_signage", "window_facing"
    if "키오스크" in hay or "kiosk" in low:
        return "kiosk", "floor"
    if "the wall" in low or "더월" in hay or "led" in low:
        return "led_wall", "wall"
    if "flip" in low or "전자칠판" in hay or "인터랙티브" in hay:
        return "interactive", "wall"
    if any(k in hay for k in ("사이니지", "디스플레이", "모니터", "TV", "비디오월")):
        return "display", "wall"
    return "other", "floor"


async def search(q: str, limit: int = 5) -> list[dict[str, Any]]:
    res = await kb().get("/v1/products/search", params={"q": q, "limit": max(1, min(limit, 20))})
    out = []
    for it in res.get("items", []):
        disp = it.get("display_name") or ""
        name = it.get("label") or disp
        hl = it.get("highlight") or []
        match = None
        if hl:
            off = name.find(disp) if disp and disp in name else 0
            s, e = hl[0][0] + max(0, off), hl[0][1] + max(0, off)
            match = [s, e]
        else:
            i = name.lower().find(q.lower().strip())
            if i >= 0:
                match = [i, i + len(q.strip())]
        thumb = (it.get("thumb") or {}).get("thumb_url") if it.get("thumb") else None
        ref = f"kb:model:{it['id']}" if it.get("kind") == "model" else f"kb:family:{it['family_id']}"
        out.append({
            "family_id": it.get("family_id"), "model_code": it.get("model_code"), "ref": ref, "kind": it.get("kind", "family"),
            "name": name, "name_match": match, "subline": it.get("meta_line") or " · ".join(it.get("category_path") or []),
            "size_options": size_options_from(it.get("meta_line")), "thumb_url": thumb,
        })
    return out


def _spec_rows(detail: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for g in (detail.get("spec") or {}).get("groups", []):
        rows.extend(g.get("rows", []))
    return rows


def dims_from_detail(detail: dict[str, Any]) -> tuple[dict[str, float] | None, float | None, float | None]:
    """(dims_m, diag_inch, brightness_nit)."""
    dims = None
    inch = None
    nit = None
    for r in _spec_rows(detail):
        label, value = r.get("label", ""), r.get("value", "")
        attrs = " ".join(r.get("attrs") or [])
        if dims is None and ("제품 크기" in label or "제품(가로x높이x깊이)" in attrs):
            m = _DIM_RE.search(value.replace(" ", " "))
            if m:
                w, h, d = (float(x.replace(",", "")) / 1000.0 for x in m.groups())
                if w > 0 and h > 0:
                    dims = {"w": round(w, 3), "h": round(h, 3), "d": round(max(d, 0.02), 3)}
        if inch is None and ("대각" in label or "대각선" in attrs or "화면 크기" in label):
            m = _SIZE_RE.search(value)
            if m:
                inch = float(m.group(1))
        if nit is None and "밝기" in label:
            m = _NIT_RE.search(value)
            if m:
                try:
                    nit = float(m.group(1).replace(",", ""))
                except ValueError:
                    nit = None
    vals = detail.get("values") or {}          # 목록 행 모양(스펙 표 없음) — 크기 · 밝기 칸
    if inch is None and isinstance((vals.get("size") or {}).get("inch"), (int, float)):
        inch = float(vals["size"]["inch"])
    if nit is None and isinstance((vals.get("brightness") or {}).get("nit"), (int, float)):
        nit = float(vals["brightness"]["nit"])
    return dims, inch, nit


async def model_detail(code: str) -> dict[str, Any] | None:
    if "/" in code:
        # 「LH012IWCMWS/XU」처럼 / 가 든 코드는 경로로 못 부른다(kb 요청 남김) → 목록 검색에서 같은 코드 한 행(스펙 표 없음)
        try:   # 검색어에 / 가 들어가면 못 찾는다 → / 앞부분으로 찾고 코드가 같은 행
            res = await kb().get("/v1/models", params={"q": code.split("/", 1)[0], "limit": 20})
        except Exception as exc:  # noqa: BLE001
            log.warning("kb models q=%s: %s", code, exc)
            return None
        return next((m for m in res.get("items", []) if m.get("model_code") == code), None)
    try:
        return await kb().get(f"/v1/models/{code}")
    except Exception as exc:  # noqa: BLE001
        log.warning("kb model %s: %s", code, exc)
        return None


async def family_models(family_id: str) -> list[dict[str, Any]]:
    try:
        res = await kb().get("/v1/models", params={"family_id": family_id, "limit": 50})
        return res.get("items", [])
    except Exception as exc:  # noqa: BLE001
        log.warning("kb models %s: %s", family_id, exc)
        return []


def _size_key(inch: float) -> str:
    return f'{int(inch) if float(inch).is_integer() else inch}"'


async def resolve_product(pick: dict[str, Any], order: int) -> dict[str, Any]:
    """{family_id, model_code?, ref?, label?} → ProductItem 필드(id · birdseye_id 제외).

    모델을 고르면 그 모델 하나(크기 고정), 제품군이면 모델들의 크기가 크기 옵션(엔진이 벽 폭 · 시청 거리로 고른다).
    """
    family_id = pick.get("family_id")
    model_code = pick.get("model_code")
    ref = pick.get("ref") or ""
    if not model_code and ref.startswith("kb:model:"):
        model_code = ref.split(":", 2)[2]
    if model_code and model_code.startswith("mdl_"):
        model_code = model_code[4:]
    if not family_id and ref.startswith("kb:family:"):
        family_id = ref.split(":", 2)[2]
    detail = await model_detail(model_code) if model_code else None
    if detail is None:
        model_code = None
    if detail and not family_id:
        family_id = (detail.get("family") or {}).get("id")
    models = await family_models(family_id) if family_id else []
    models_by_size: dict[str, str] = {}
    for m in models:
        inch = ((m.get("values") or {}).get("size") or {}).get("inch")
        if inch:
            key = _size_key(inch)
            if key not in models_by_size or m.get("is_family_default"):
                models_by_size[key] = m["model_code"]
    rep_detail = detail
    if rep_detail is None and models:
        rep = next((m for m in models if m.get("is_family_default")), models[0])
        rep_detail = await model_detail(rep["model_code"])
    family_name = ((rep_detail or {}).get("family") or {}).get("name") or ((models[0].get("family") or {}).get("name") if models else None)
    cat = [c.get("name", "") for c in (rep_detail or {}).get("category_path", [])]
    dims_by_size: dict[str, dict[str, float]] = {}
    dims_source = "estimated"
    if detail is not None:
        display_name = detail.get("label_en") or detail.get("display_name") or pick.get("label") or "제품"
        model_display = detail.get("display_name")
        dims, inch, nit = dims_from_detail(detail)
        size_options = [_size_key(inch)] if inch else []
        if dims:
            dims_source = "spec"
        elif inch:
            dims = computed_dims(inch)
            dims_source = "computed"
        if dims and size_options:
            dims_by_size[size_options[0]] = dims
    else:
        display_name = pick.get("label") or family_name or family_id or "제품"
        model_display = None
        _d, inch, nit = dims_from_detail(rep_detail) if rep_detail else (None, None, None)
        size_options = sorted(models_by_size, key=lambda s: size_inch(s) or 0)
        dims = None
        for s in size_options[:6]:
            det2 = await model_detail(models_by_size[s])
            d2 = dims_from_detail(det2)[0] if det2 else None
            if d2:
                dims_by_size[s] = d2
                dims_source = "spec" if dims_source in ("estimated", "spec") else dims_source
            else:
                dims_by_size[s] = computed_dims(size_inch(s) or 55)
                dims_source = "computed"
        for s in size_options[6:]:
            dims_by_size[s] = computed_dims(size_inch(s) or 55)
        if len(size_options) == 1:
            dims = dims_by_size[size_options[0]]
            inch = size_inch(size_options[0])
    role, mount = role_for(f"{display_name} {family_name or ''}", cat, nit)
    if role == "led_wall":
        # LED 의 12" · 16" 같은 값은 화면이 아니라 모듈(캐비닛) 크기 — 화면 크기로 쓰지 않는다
        bad = [s for s in size_options if (size_inch(s) or 0) < 30]
        if bad:
            size_options = [s for s in size_options if s not in bad]
            for s in bad:
                dims_by_size.pop(s, None)
        if inch is not None and inch < 30:
            inch = None
            if dims_source == "computed":
                dims, dims_source = None, "estimated"
    if not dims and not dims_by_size:
        dims_source = "estimated"
    short = short_name(display_name, model_display)
    return {
        "family_id": family_id or "", "model_code": model_code,
        "ref": f"kb:model:mdl_{model_code}" if model_code else f"kb:family:{family_id}",
        "display_name": display_name, "short": short, "size_options": size_options, "chosen_size": None,
        "dims_m": dims, "dims_source": dims_source, "diag_inch": inch, "category": " · ".join(cat[-2:]) if cat else "",
        "role": role, "mount_default": mount, "order": order, "models_by_size": models_by_size, "dims_by_size": dims_by_size,
        "brightness_nit": nit,
    }


async def placement_rules() -> list[dict[str, Any]]:
    try:
        res = await kb().get("/v1/placement-rules")
        return res.get("items", [])
    except Exception as exc:  # noqa: BLE001
        log.warning("kb placement-rules: %s", exc)
        return []


async def capabilities_for(spaces: list[str], text: str) -> list[dict[str, Any]]:
    """C1 — 공간 · 문장 → 역량(hard · soft)."""
    try:
        res = await kb().post("/v1/query/C1", json={"spaces": spaces, "text": text})
        return ((res or {}).get("result") or {}).get("capabilities", [])
    except Exception as exc:  # noqa: BLE001
        log.warning("kb C1: %s", exc)
        return []


async def messages_for(spaces: list[str], family_ids: list[str], limit: int = 4) -> list[dict[str, Any]]:
    """E3 — 공간 · 제품 → 메시지(존 문구 근거). [{text, source_url, about_name}]"""
    body: dict[str, Any] = {"spaces": spaces[:3], "limit": limit}
    if family_ids:
        body["products"] = [{"kind": "family", "id": f} for f in family_ids[:3] if f]
    try:
        res = await kb().post("/v1/query/E3", json=body)
    except Exception as exc:  # noqa: BLE001
        log.warning("kb E3: %s", exc)
        return []
    r = (res or {}).get("result") or {}
    out = []
    for m in r.get("ranked", [])[:limit]:
        out.append({"text": m.get("text", ""), "source_url": m.get("source_url"), "about_name": m.get("about_name", "")})
    return out
