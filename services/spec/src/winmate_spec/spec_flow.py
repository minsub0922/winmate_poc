"""Spec 시트 새 흐름(2026-10-08 — 보드 webapp1 SP0 · SP1 · SP2 · SP_Done, docs/scenarios/11-content-flow.md §6 `sp`).

- 시작: Gate 에서 고른 Storyboard(`get_flow`) 의 stages.dss 제품 → 시트 행(제품 하나 = 행 하나, 공간은 모아서 · 수량은 더해서).
- 행마다 KB 모델을 결정적으로 맞춘다: DSS ref(kb:model · kb:family) → 이름 속 모델명(QM55C …, kb `/v1/spec/table` · `/v1/products/search`) → 못 찾으면 비워 둔다.
  사람이 행마다 다른 모델을 고를 수 있다(제품군 모델 · 카탈로그 검색).
- 칸 값은 kb `POST /v1/spec/table`(+ `/v1/models/{code}`) 원문에서만(rules/values.catalog_candidate). 없는 값은 `[확인 필요]` — 지어내지 않는다.
- 경고: 카탈로그에 없음(not_in_catalog) · 단종(spec 생애주기 표) · 품절 · DSS 이름과 고른 모델 불일치 · 제품군 대표 모델로 채움.
- 수량: DSS 원문(`2대` · `1식` · `실당 1대` · null)에서 개수가 분명한 것만 더한다. 하나라도 개수가 아니거나 비면 `None`(= [확인 필요]) — 원문은 `qty_note` 로 남긴다.
- 저장(`:finish`) → XLSX(export 서비스 · 보드 Done `file: "SP-01_v1.xlsx"`, 못 만들면 null) → Storyboard flow.json `stages.sp`(§6 모양) · 요약 줄 · 팝업 카드(push_stage)
  · workspace 색인(feature=SP, route=/spec/flow/{id}).

저장소: DocStore("spec") 컬렉션 `spec_flows`(sfl_ …). 쓰기는 낙관적 잠금 + 재시도, PATCH 는 expected_version(409).
"""
from __future__ import annotations

import asyncio
import copy
import logging
import re
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, Field
from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError, not_found
from winmate_common.flow import get_flow, push_stage
from winmate_common.ids import new_id, now_iso
from winmate_common.platform import register_item
from winmate_common.store import VersionConflict

from . import ops, repo
from .catalog import catalog, strip_ref
from .rules.fmt import fmt_num
from .rules.values import Fmt, attr, catalog_candidate, is_none_value, render_text

log = logging.getLogger("winmate.spec.flow")

COLL = "spec_flows"
PENDING = "[확인 필요]"
PENDING_EN = "[To be confirmed]"

# 보드 SP2 항목 칩 8개(순서 · 이름 그대로) — key · 한국어 · 영문 · 값 원천(rules/values row_key)
ITEMS: list[dict[str, Any]] = [
    {"key": "size_resolution", "label": "화면 크기 · 해상도", "en": "Screen Size · Resolution", "rows": ["size_resolution"]},
    {"key": "brightness_contrast", "label": "밝기 · 명암비", "en": "Brightness · Contrast", "rows": ["brightness_contrast"]},
    {"key": "io_ports", "label": "입출력 단자", "en": "I/O Ports", "rows": ["io_ports"]},
    {"key": "power", "label": "소비전력", "en": "Power Consumption", "rows": ["power"]},
    {"key": "size_weight", "label": "크기 · 무게", "en": "Dimensions · Weight", "rows": ["dimensions", "weight"]},
    {"key": "install", "label": "설치 방식", "en": "Installation", "rows": ["install"]},
    {"key": "operation_hours", "label": "운영 시간", "en": "Operation Hours", "rows": ["operation_hours"]},
    {"key": "warranty", "label": "보증", "en": "Warranty", "rows": ["warranty"]},
]
ITEM_KEYS = [it["key"] for it in ITEMS]
DEFAULT_ITEMS = ITEM_KEYS[:6]           # 보드: 앞 6개 기본 선택
FORMAT_LABEL = {"compare": "비교표", "per_product": "제품별 1장"}
NOTATION = {"ko_mm": ("ko", "mm", "한국어 · mm"), "en_inch": ("en", "inch", "영문 · inch")}
_CODE = re.compile(r"\b([A-Z]{2,3}\d{2,3}[A-Z]{0,2})\b")
# DSS 수량 원문 중 「개수」로 읽을 수 있는 것(2 · 2대 · 1식 · 3 EA). `실당 1대` · `층당 1대` 같은 단위당 수는 개수가 아니다.
_QTY = re.compile(r"^\s*(\d{1,4})\s*(대|식|개|세트|set|sets|ea|pcs|unit|units)?\s*$", re.IGNORECASE)

Format = Literal["compare", "per_product"]
Notation = Literal["ko_mm", "en_inch"]
Match = Literal["ref", "code", "family", "manual", "none"]


# ── 모델(API) ───────────────────────────────────────────

class SFWarning(BaseModel):
    kind: Literal["not_in_catalog", "discontinued", "sold_out", "mismatch", "family_default"]
    text: str


class SFRow(BaseModel):
    key: str = Field(description="시트 안에서 행을 가리키는 키(DSS 제품 이름에서 만든 slug)")
    name: str = Field(description="DSS 제품 이름(보드 제품 줄 제목)")
    spaces: list[str] = Field(default_factory=list, description="이 제품이 놓인 DSS 공간들")
    qty: int | None = Field(None, ge=0, description="수량(DSS 공간별 개수의 합, 사람이 고칠 수 있음) — 개수를 알 수 없으면 null(= [확인 필요])")
    qty_note: str | None = Field(None, description="DSS 수량 원문(공간별, 예: 로비 2대 · 라운지 [확인 필요])")
    on: bool = Field(True, description="시트에 넣는다(보드 체크박스)")
    dss_ref: str | None = Field(None, description="DSS 제품 참조(kb:model:… · kb:family:…)")
    model_code: str | None = Field(None, description="맞춘 KB 모델코드 — 없으면 카탈로그에서 찾지 못함")
    display_name: str | None = Field(None, description="KB 모델 표시명(QM55C …)")
    family_id: str | None = None
    family_name: str | None = None
    source_url: str | None = Field(None, description="값 출처(공식 카탈로그 페이지)")
    match: Match = Field("none", description="모델을 맞춘 방법: ref · code(이름 속 모델명) · family(제품군 대표 모델) · manual(사람이 고름) · none")
    by: str = Field("manual", description="출처 표시(CF-10) — DSS 제품의 by, 사람이 모델을 바꾸면 manual")
    cells: dict[str, str] = Field(default_factory=dict, description="항목 key → 표시 글(현재 표기 기준, 없는 값은 [확인 필요])")
    pending: list[str] = Field(default_factory=list, description="값을 다 채우지 못한 항목 key")
    warnings: list[SFWarning] = Field(default_factory=list)


class SFColumn(BaseModel):
    key: str
    label: str
    on: bool


class SFCounts(BaseModel):
    models: int = Field(description="시트에 넣은 행")
    total: int = Field(description="전체 행(DSS 제품)")
    columns: int
    pending_cells: int
    warnings: int


class SFDoc(BaseModel):
    id: str
    code: str | None = Field(None, description="화면 · flow.json 짧은 번호(SP-01 …)")
    title: str
    sb_id: str | None = None
    dss_ref: str | None = Field(None, description="가져온 DSS 참조(DSS-01 …)")
    format: Format = "compare"
    notation: Notation = "ko_mm"
    items: list[str] = Field(default_factory=list, description="고른 항목 key(보드 순서)")
    columns: list[SFColumn] = Field(default_factory=list, description="항목 칩 전체(이름은 현재 표기 언어)")
    rows: list[SFRow] = Field(default_factory=list)
    catalog_version: str | None = None
    status: Literal["draft", "done"] = "draft"
    ver: int | None = Field(None, description="저장(완료) 판 — flow.json stages.sp.ver")
    counts: SFCounts
    version: int
    created_at: str
    updated_at: str


class SFListItem(BaseModel):
    id: str
    code: str | None = None
    title: str
    sb_id: str | None = None
    status: str
    counts: SFCounts
    updated_at: str


class SFList(BaseModel):
    items: list[SFListItem]
    next_cursor: str | None = None


class SFCreate(BaseModel):
    sb_id: str = Field(min_length=1, description="사전 작업 Storyboard(DSS 까지 된 것)")
    title: str | None = Field(None, max_length=120)


class SFPatch(BaseModel):
    title: str | None = Field(None, max_length=120)
    format: Format | None = None
    notation: Notation | None = None
    items: list[str] | None = Field(None, description="고를 항목 key(순서는 보드 순서로 맞춘다)")
    expected_version: int | None = Field(None, description="다르면 409")


class SFRowPatch(BaseModel):
    on: bool | None = None
    qty: int | None = Field(None, ge=0, le=9999)
    model_code: str | None = Field(None, description="이 모델로 바꾼다(KB 모델코드 · 표시명)")
    clear_model: bool | None = Field(None, description="모델을 비운다(카탈로그 밖 제품)")
    expected_version: int | None = None


class SFModelOption(BaseModel):
    model_code: str
    display_name: str
    family_name: str | None = None
    size_inch: float | None = None
    current: bool = False


class SFModelOptions(BaseModel):
    items: list[SFModelOption]
    basis: str = Field(description="family = 같은 제품군 모델 · search = 카탈로그 검색")


class SFFlowSync(BaseModel):
    md_added: str = Field(description="Storyboard 요약본에 더해진 부분")
    synced: list[str] = Field(default_factory=list, description="같은 Spec 시트가 연결돼 함께 바뀐 다른 Storyboard")


class SFFile(BaseModel):
    id: str
    name: str = Field(description="SP-01_v1.xlsx")
    url: str = Field(description="내려받기 경로(files 서비스)")


class SFStageOut(BaseModel):
    stage: dict[str, Any] = Field(description="Storyboard flow.json 의 stages.sp")
    summary_md: str
    flow_sync: SFFlowSync | None = Field(None, description="허브에 반영된 결과(허브가 안 되면 null)")
    file: SFFile | None = Field(None, description="저장 때 만든 XLSX(보드 Done 「XLSX로 내보낼 수 있어요」) — 못 만들었으면 null")


# ── 저장소 ──────────────────────────────────────────────

def _store():
    return repo.store()


def slug(name: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z가-힣]+", "-", (name or "").strip().lower()).strip("-")
    return s or "item"


def _get(fid: str) -> dict[str, Any]:
    d = _store().get(COLL, fid)
    if not d:
        raise not_found("Spec 시트", fid)
    return d


async def load(fid: str) -> dict[str, Any]:
    return await asyncio.to_thread(_get, fid)


async def update(fid: str, fn: Callable[[dict[str, Any]], None], note: str | None = None, expected: int | None = None) -> dict[str, Any]:
    def _do() -> dict[str, Any]:
        for _ in range(5):
            cur = _get(fid)
            if expected is not None and cur["version"] != expected:
                raise ApiError(409, "CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러온 뒤 다시 고쳐 주세요.",
                               {"current_version": cur["version"]})
            work = copy.deepcopy(cur)
            fn(work)
            try:
                return _store().put(COLL, fid, work, expected_version=cur["version"], note=note)
            except VersionConflict:
                if expected is not None:
                    raise ApiError(409, "CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러온 뒤 다시 고쳐 주세요.") from None
                continue
        raise ApiError(409, "CONFLICT", "다른 곳에서 동시에 고쳐 저장하지 못했어요. 다시 시도해 주세요.")
    return await asyncio.to_thread(_do)


# ── 값 · 표시 ────────────────────────────────────────────

def _install_value(spec: dict[str, Any]) -> dict[str, Any] | None:
    """설치 방식 — VESA 마운트(기구사양) + 추가 기능 마운트 · 스탠드(KB 원문 그대로)."""
    vesa = attr(spec, "기구사양", "VESA 마운트")
    acc = catalog_candidate("accessories", spec, "").value or {}
    v = {"vesa": vesa["raw"].strip() if vesa and not is_none_value(vesa["raw"]) else None,
         "mount": acc.get("mount"), "stand": acc.get("stand")}
    return v if any(v.values()) else None


def values_of(spec: dict[str, Any], version: str) -> dict[str, Any]:
    """KB 모델 스펙 → 항목 원천 row_key 별 정규 값(표기와 무관). 값이 없으면 None. 전력은 조건 붙은 값(On Mode 등)도 같이 둔다."""
    out: dict[str, Any] = {}
    for rk in ("size_resolution", "brightness_contrast", "io_ports", "power", "dimensions", "weight", "operation_hours", "warranty"):
        c = catalog_candidate(rk, spec, version)
        out[rk] = c.value
        if rk == "power" and c.value is None and c.alt_measures:
            out["power_alt"] = [{"label": a["label"], "num": a.get("num")} for a in c.alt_measures if a.get("num") is not None][:1]
        if rk == "warranty" and c.value is None:
            pol = catalog().warranty_policy(spec)
            if pol and pol.get("years") is not None:
                out[rk] = {"years": pol["years"]}
    out["install"] = _install_value(spec)
    return out


def _fix_pending(text: str, lang: str) -> str:
    return text.replace("[확정 필요]", PENDING if lang == "ko" else PENDING_EN).replace("[To be confirmed]", PENDING if lang == "ko" else PENDING_EN)


def cell_text(item_key: str, values: dict[str, Any] | None, notation: str) -> tuple[str, bool]:
    """항목 하나의 표시 글 · 덜 채워짐 여부. values 가 None(카탈로그에 없음)이면 [확인 필요]."""
    lang, unit, _ = NOTATION.get(notation, NOTATION["ko_mm"])
    P = PENDING if lang == "ko" else PENDING_EN
    if values is None:
        return P, True
    f = Fmt(language=lang, length_unit=unit, weight_unit="lb" if unit == "inch" else "kg")
    if item_key == "size_weight":
        dims, wt = values.get("dimensions"), values.get("weight")
        if dims is None and wt is None:
            return P, True
        t1 = _fix_pending(render_text("dimensions", dims, f, lang)[0], lang) if dims is not None else P
        w = (wt or {}).get("set")
        if w is None:
            t2 = P
        elif unit == "inch":
            t2 = _fix_pending(render_text("weight", {"set": w, "pkg": None}, f, lang)[0].split(" / ")[0], lang)
        else:
            t2 = f"{fmt_num(w)} kg"
        return f"{t1} · {t2}", (dims is None or w is None)
    if item_key == "install":
        v = values.get("install")
        if not v:
            return P, True
        parts = []
        if v.get("vesa"):
            parts.append(f"VESA {v['vesa']}")
        if v.get("mount"):
            parts.append(("마운트 " if lang == "ko" else "Mount ") + v["mount"])
        if v.get("stand"):
            parts.append(("스탠드 " if lang == "ko" else "Stand ") + v["stand"])
        return " · ".join(parts), False
    if item_key == "power":
        v = values.get("power")
        if v is None:
            alt = values.get("power_alt") or []
            if alt:
                a = alt[0]
                return (f"{fmt_num(a['num'])} W ({a['label']} 기준)" if lang == "ko" else f"{fmt_num(a['num'])} W ({a['label']})"), False
            return P, True
    rk = next(it["rows"][0] for it in ITEMS if it["key"] == item_key)
    v = values.get(rk)
    if v is None:
        return P, True
    text = _fix_pending(render_text(rk, v, f, lang)[0], lang)
    return text, (P in text)


def item_label(key: str, notation: str) -> str:
    it = next((x for x in ITEMS if x["key"] == key), None)
    if not it:
        return key
    return it["en"] if NOTATION.get(notation, NOTATION["ko_mm"])[0] == "en" else it["label"]


def _codes_in(name: str) -> list[str]:
    return list(dict.fromkeys(m.group(1) for m in _CODE.finditer((name or "").upper())))


def row_warnings(r: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not r.get("model_code"):
        out.append({"kind": "not_in_catalog", "text": "공식 카탈로그에서 모델을 찾지 못했어요 · 모델을 골라 주세요(값은 [확인 필요])"})
        return out
    lc = r.get("lifecycle") or {}
    if lc.get("status") in ("discontinued", "eol_planned"):
        succ = (lc.get("successor") or {}).get("display_name")
        word = "단종" if lc["status"] == "discontinued" else "단종 예정"
        out.append({"kind": "discontinued", "text": f"{word} 모델이에요" + (f" · 후속 {succ}" if succ else "") + f" · {lc.get('source') or '생애주기 표'}"})
    if lc.get("sold_out"):
        out.append({"kind": "sold_out", "text": "카탈로그에 품절로 표시돼 있어요"})
    codes = _codes_in(r.get("name") or "")
    dn = (r.get("display_name") or "").upper()
    if codes and dn and dn not in codes:
        out.append({"kind": "mismatch", "text": f"DSS 제품명({', '.join(codes)})과 고른 모델({r.get('display_name')})이 달라요"})
    if r.get("match") == "family":
        out.append({"kind": "family_default", "text": "제품군 대표 모델로 채웠어요 · 모델을 확인해 주세요"})
    return out


def to_row(r: dict[str, Any], notation: str, items: list[str]) -> dict[str, Any]:
    cells: dict[str, str] = {}
    pending: list[str] = []
    vals = r.get("values") if r.get("model_code") else None
    for k in ITEM_KEYS:
        t, p = cell_text(k, vals, notation)
        cells[k] = t
        if p and k in items:
            pending.append(k)
    out = {k: v for k, v in r.items() if k not in ("values", "lifecycle")}
    return {**out, "cells": cells, "pending": pending, "warnings": row_warnings(r)}


def counts(d: dict[str, Any]) -> dict[str, int]:
    items = d.get("items") or []
    rows = [to_row(r, d.get("notation") or "ko_mm", items) for r in d.get("rows") or []]
    on = [r for r in rows if r.get("on")]
    return {"models": len(on), "total": len(rows), "columns": len(items),
            "pending_cells": sum(len(r["pending"]) for r in on), "warnings": sum(len(r["warnings"]) for r in on)}


def to_api(d: dict[str, Any]) -> dict[str, Any]:
    notation = d.get("notation") or "ko_mm"
    items = d.get("items") or []
    return {**d, "rows": [to_row(r, notation, items) for r in d.get("rows") or []],
            "columns": [{"key": k, "label": item_label(k, notation), "on": k in items} for k in ITEM_KEYS], "counts": counts(d)}


# ── 모델 맞추기 ──────────────────────────────────────────

async def _spec_for(code: str) -> dict[str, Any] | None:
    try:
        return await catalog().spec(code)
    except ApiError as exc:
        log.warning("kb spec %s: %s", code, exc.code)
        return None


async def _fill(r: dict[str, Any], code: str | None, match: str) -> None:
    """행에 모델 · 값 · 생애주기를 채운다(code 가 None 이면 비운다)."""
    for k in ("model_code", "display_name", "family_id", "family_name", "source_url", "values", "lifecycle"):
        r[k] = None
    r["match"] = "none"
    if not code:
        return
    spec = await _spec_for(code)
    if not spec:
        return
    ver = await catalog().version()
    r.update({"model_code": spec["model_code"], "display_name": spec.get("display_name") or spec["model_code"], "family_id": spec.get("family_id"),
              "family_name": spec.get("family_name"), "source_url": spec.get("source_url"), "match": match, "values": values_of(spec, ver)})
    try:
        lc = await ops.evaluate_lifecycle({"model_code": spec["model_code"], "display_name": r["display_name"], "in_catalog": spec.get("in_catalog", True)}, spec)
        r["lifecycle"] = {"status": lc.get("status"), "sold_out": bool(lc.get("sold_out")), "source": lc.get("source"), "successor": lc.get("successor")}
    except Exception as exc:  # noqa: BLE001
        log.warning("lifecycle %s: %s", code, exc)


async def match_model(name: str, ref: str | None) -> tuple[str | None, str]:
    """DSS 제품 → (모델코드, 맞춘 방법). 결정적: ref → 이름 속 모델명 → 없음."""
    cat = catalog()
    if ref and ref.startswith("kb:model:"):
        code = await cat.resolve(ref)
        if code:
            return code, "ref"
    if ref and ref.startswith("kb:family:"):
        code = await cat.resolve(strip_ref(ref))
        if code:
            return code, "family"
    for tok in _codes_in(name):
        try:
            code = await cat.resolve(tok)
            if code is None:
                for it in await cat.search(tok, limit=5, kinds="model"):
                    if (it.get("display_name") or "").upper() == tok and it.get("model_code"):
                        code = it["model_code"]
                        break
        except ApiError as exc:
            log.warning("kb resolve %s: %s", tok, exc.code)
            code = None
        if code:
            return code, "code"
    return None, "none"


def parse_qty(v: Any) -> int | None:
    """DSS 수량 하나 → 개수(모르면 None). 2 · '2대' · '1식' → 2 · 1, '실당 1대' · '' · None → None."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, int):
        return v if v >= 0 else None
    if isinstance(v, float):
        return int(v) if v.is_integer() and v >= 0 else None
    if isinstance(v, str):
        m = _QTY.match(v)
        return int(m.group(1)) if m else None
    return None


def dss_rows(flow: dict[str, Any]) -> list[dict[str, Any]]:
    """flow.json stages.dss → 행(제품 하나 = 행 하나, 공간 모으고 수량 더함). 솔루션은 스펙 시트 행이 아니다.
    수량은 공간마다 개수로 읽히는 것만 더하고, 하나라도 모르면 None — 지어내지 않는다(원문은 qty_note)."""
    dss = (flow.get("stages") or {}).get("dss") or {}
    out: dict[str, dict[str, Any]] = {}
    for sp in dss.get("spaces") or []:
        for p in sp.get("products") or []:
            if isinstance(p, str):
                p = {"name": p}
            name = (p.get("name") or p.get("model") or "").strip()
            if not name or (p.get("kind") not in (None, "product")):
                continue
            k = slug(name)
            r = out.setdefault(k, {"key": k, "name": name, "spaces": [], "_qty": [], "on": True, "dss_ref": p.get("ref"), "by": p.get("by") or "manual"})
            if sp.get("name") and sp["name"] not in r["spaces"]:
                r["spaces"].append(sp["name"])
            raw = p.get("qty")
            r["_qty"].append((sp.get("name") or "", parse_qty(raw), str(raw).strip() if raw not in (None, "") else PENDING))
            r["dss_ref"] = r["dss_ref"] or p.get("ref")
    for r in out.values():
        parts = r.pop("_qty")
        nums = [n for _, n, _ in parts]
        r["qty"] = sum(nums) if nums and all(n is not None for n in nums) else None   # type: ignore[arg-type]
        r["qty_note"] = " · ".join(f"{s} {t}".strip() for s, _, t in parts) or None
    return list(out.values())


# ── 작업 ────────────────────────────────────────────────

async def create(body: SFCreate) -> dict[str, Any]:
    flow = await get_flow(body.sb_id)
    if flow is None:
        raise ApiError(404, "STORYBOARD_NOT_FOUND", f"Storyboard를 찾을 수 없어요: {body.sb_id}")
    dss = (flow.get("stages") or {}).get("dss")
    if not dss:
        raise ApiError(422, "PREREQUISITE_MISSING", "DSS까지 된 Storyboard에서 시작할 수 있어요.", {"need": "dss"})
    rows = dss_rows(flow)
    sem = asyncio.Semaphore(4)

    async def one(r: dict[str, Any]) -> None:
        async with sem:
            code, how = await match_model(r["name"], r.get("dss_ref"))
            await _fill(r, code, how)
    await asyncio.gather(*(one(r) for r in rows))
    try:
        cver = await catalog().version()
    except ApiError:
        cver = None
    n = await asyncio.to_thread(_store().count, COLL)
    doc = {"code": f"SP-{n + 1:02d}", "title": body.title or flow.get("name") or "새 Spec 시트", "sb_id": body.sb_id,
           "dss_ref": dss.get("ref"), "format": "compare", "notation": "ko_mm", "items": list(DEFAULT_ITEMS), "rows": rows,
           "catalog_version": cver, "status": "draft"}
    fid = new_id("sfl")
    saved = await asyncio.to_thread(_store().put, COLL, fid, doc, note="만듦")
    await register_item(feature="SP", item_id=fid, title=saved["title"], status="draft", route=f"/spec/flow/{fid}",
                        summary=f"DSS 제품 {len(rows)} · 스펙 시트 작성 중")
    return to_api(saved)


async def list_flows(limit: int, cursor: str | None) -> dict[str, Any]:
    items, nxt = await asyncio.to_thread(_store().list, COLL, limit=limit, cursor=cursor)
    return {"items": [{"id": d["id"], "code": d.get("code"), "title": d.get("title") or "", "sb_id": d.get("sb_id"),
                       "status": d.get("status", "draft"), "counts": counts(d), "updated_at": d["updated_at"]} for d in items], "next_cursor": nxt}


async def patch(fid: str, body: SFPatch) -> dict[str, Any]:
    if body.items is not None:
        bad = [k for k in body.items if k not in ITEM_KEYS]
        if bad:
            raise ApiError(422, "UNKNOWN_ITEM", f"모르는 항목이에요: {', '.join(bad)}", {"items": bad})

    def fn(d: dict[str, Any]) -> None:
        if body.title is not None and body.title.strip():
            d["title"] = body.title.strip()
        if body.format is not None:
            d["format"] = body.format
        if body.notation is not None:
            d["notation"] = body.notation
        if body.items is not None:
            d["items"] = [k for k in ITEM_KEYS if k in set(body.items)]
    return to_api(await update(fid, fn, "형식 · 항목 · 표기", expected=body.expected_version))


async def patch_row(fid: str, key: str, body: SFRowPatch) -> dict[str, Any]:
    d = await load(fid)
    if not any(r["key"] == key for r in d.get("rows") or []):
        raise not_found("제품 행", key)
    filled: dict[str, Any] | None = None
    if body.model_code:
        code = await catalog().resolve(body.model_code)
        if not code:
            raise ApiError(422, "MODEL_NOT_IN_CATALOG", f"공식 카탈로그에 없는 모델이에요: {body.model_code}", {"model": body.model_code})
        filled = {}
        await _fill(filled, code, "manual")

    def fn(doc: dict[str, Any]) -> None:
        r = next(x for x in doc["rows"] if x["key"] == key)
        if body.on is not None:
            r["on"] = body.on
        if body.qty is not None:
            r["qty"] = body.qty
        if filled is not None:
            r.update(filled)
            r["by"] = "manual"
        elif body.clear_model:
            for k in ("model_code", "display_name", "family_id", "family_name", "source_url", "values", "lifecycle"):
                r[k] = None
            r["match"] = "none"
            r["by"] = "manual"
    return to_api(await update(fid, fn, "행 고침", expected=body.expected_version))


async def model_options(fid: str, key: str, q: str | None) -> dict[str, Any]:
    d = await load(fid)
    r = next((x for x in d.get("rows") or [] if x["key"] == key), None)
    if r is None:
        raise not_found("제품 행", key)
    cat = catalog()
    cur = r.get("model_code")
    out: list[dict[str, Any]] = []
    basis = "search"
    if not (q or "").strip() and r.get("family_id"):
        basis = "family"
        for m in await cat.family_models(r["family_id"]):
            out.append({"model_code": m["model_code"], "display_name": m.get("display_name") or m["model_code"], "family_name": r.get("family_name"),
                        "size_inch": m.get("size_inch"), "current": m["model_code"] == cur})
    else:
        term = (q or "").strip() or (_codes_in(r["name"]) or [r["name"]])[0]
        try:
            found = await cat.search(term, limit=12, kinds="model")
        except ApiError:
            found = []
        for it in found:
            if it.get("model_code"):
                out.append({"model_code": it["model_code"], "display_name": it.get("display_name") or it["model_code"],
                            "family_name": it.get("family_name"), "size_inch": it.get("size_inch"), "current": it["model_code"] == cur})
    return {"items": out[:30], "basis": basis}


# ── 저장 · flow.json ────────────────────────────────────

def stage(d: dict[str, Any]) -> dict[str, Any]:
    notation = d.get("notation") or "ko_mm"
    lang, unit, _ = NOTATION[notation]
    items = d.get("items") or []
    rows = [to_row(r, notation, items) for r in d.get("rows") or [] if r.get("on")]
    models = [{"space": " · ".join(r.get("spaces") or []), "name": r["name"], "model_code": r.get("model_code"),
               "ref": f"kb:model:{r['model_code']}" if r.get("model_code") else None, "qty": r.get("qty"),
               "specs": {k: r["cells"][k] for k in items}, "by": r.get("by") or "manual"} for r in rows]
    warnings = [{"model": r.get("display_name") or r["name"], "kind": w["kind"], "text": w["text"]} for r in rows for w in r["warnings"]]
    f = d.get("file") or {}
    return {"ref": d.get("code") or d["id"], "ver": d.get("ver"), "from": d.get("dss_ref") or d.get("sb_id"),
            "format": FORMAT_LABEL[d.get("format") or "compare"], "lang": lang, "unit": unit,
            "models": models, "columns": [{"key": k, "label": item_label(k, notation)} for k in items], "warnings": warnings,
            "valuesFrom": "공식 카탈로그", "catalogVersion": d.get("catalog_version"),
            "file": f.get("name"), "fileId": f.get("id"),
            "counts": {"models": len(models), "columns": len(items), "pendingCells": sum(len(r["pending"]) for r in rows), "warnings": len(warnings)}}


def xlsx_document(d: dict[str, Any]) -> dict[str, Any]:
    """export 서비스 xlsx 문서 — 비교표는 시트 하나(항목 × 제품), 제품별 1장은 제품마다 시트. 칸 글은 화면 미리보기와 같다."""
    notation = d.get("notation") or "ko_mm"
    en = NOTATION[notation][0] == "en"
    P = PENDING_EN if en else PENDING
    items = d.get("items") or []
    rows = [to_row(r, notation, items) for r in d.get("rows") or [] if r.get("on")]
    head = [("model", "Model" if en else "모델"), ("space", "Space" if en else "공간"), ("qty", "Qty" if en else "수량")]

    def meta(r: dict[str, Any], k: str) -> str:
        if k == "model":
            return f"{r['display_name']} ({r['model_code']})" if r.get("model_code") else P
        if k == "space":
            return " · ".join(r.get("spaces") or []) or "—"
        return str(r["qty"]) if r.get("qty") is not None else P

    src = ("Values: official catalog" if en else "값 출처: 공식 카탈로그") + (f" ({d['catalog_version']})" if d.get("catalog_version") else "")
    notes = [src, f"{P} = " + ("no catalog value · please confirm" if en else "카탈로그에 값이 없어 확인이 필요한 칸")]
    notes += [f"⚠ {r.get('display_name') or r['name']}: {w['text']}" for r in rows for w in r["warnings"]]
    label = "Item" if en else "항목"
    if (d.get("format") or "compare") == "compare":
        cols = [{"key": "item", "label": label, "width": 24}] + [{"key": f"m{i}", "label": r["name"], "width": 30} for i, r in enumerate(rows)]
        lines = [{"item": {"value": t, "bold": True}, **{f"m{i}": meta(r, k) for i, r in enumerate(rows)}} for k, t in head]
        lines += [{"item": {"value": item_label(k, notation), "bold": True}, **{f"m{i}": r["cells"][k] for i, r in enumerate(rows)}} for k in items]
        return {"sheets": [{"name": "Comparison" if en else "비교표", "columns": cols, "rows": lines, "notes": notes}]}
    sheets, used = [], set()
    for r in rows:
        base = re.sub(r"[\[\]:*?/\\]", " ", r["name"]).strip()[:28] or "Sheet"
        name, n = base, 2
        while name in used:
            name, n = f"{base[:26]} {n}", n + 1
        used.add(name)
        lines = [{"item": {"value": t, "bold": True}, "value": meta(r, k)} for k, t in head]
        lines += [{"item": {"value": item_label(k, notation), "bold": True}, "value": r["cells"][k]} for k in items]
        sheets.append({"name": name, "columns": [{"key": "item", "label": label, "width": 24}, {"key": "value", "label": r["name"], "width": 48}],
                       "rows": lines, "notes": notes})
    return {"sheets": sheets}


async def make_xlsx(d: dict[str, Any]) -> dict[str, str] | None:
    """저장 판의 XLSX(SP-01_v1.xlsx). export 가 안 되면 None — 저장은 그대로 된다."""
    body = {"format": "xlsx", "filename": f"{d.get('code') or d['id']}_v{d.get('ver') or 1}", "document": xlsx_document(d),
            "confidential": True, "source_ref": f"spec:{d['id']}"}   # 제목(Storyboard 이름)에 고객 · 사업명이 들어갈 수 있다
    try:
        res = await ServiceClient("export", timeout=60).post("/v1/exports", json=body)
    except Exception as exc:  # noqa: BLE001 — 파일은 덤, 저장을 막지 않는다
        log.warning("spec flow xlsx %s: %s", d["id"], exc)
        return None
    f = res.get("file") if res.get("status") == "done" else None
    return {"id": f["id"], "name": f["name"], "url": f["url"]} if f else None


def card(d: dict[str, Any], st: dict[str, Any]) -> dict[str, Any]:
    """연결된 콘텐츠 보기 팝업(ContentPopup) 값 — 공간별 제품 · 모델(경고 · 카탈로그에 없음은 확인 필요)."""
    notation = d.get("notation") or "ko_mm"
    rows = [to_row(r, notation, d.get("items") or []) for r in d.get("rows") or [] if r.get("on")]
    by_space: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_space.setdefault(" · ".join(r.get("spaces") or []) or "공간 없음", []).append(r)
    groups = [{"h": sp, "sub": f"제품 {len(rs)}",
               "lines": [{"t": r["name"] + (f" · {r['display_name']}" if r.get("display_name") else ""),
                          "note": "확인 필요" if (r["warnings"] or r["pending"]) else None} for r in rs[:4]]}
              for sp, rs in list(by_space.items())[:3]]
    c = st["counts"]
    _, _, nlabel = NOTATION[notation]
    return {"title": d.get("title") or "Spec 시트",
            "facts": [["제품", str(c["models"])], ["항목", str(c["columns"])], ["형식", f"{st['format']} · {nlabel}"]],
            "groups": groups, "foot": "값은 공식 카탈로그에서만 채웠어요 · 없는 값은 [확인 필요]",
            "line": f"{d.get('code')} v{d.get('ver') or 1} · 제품 {c['models']} · 항목 {c['columns']} · {st['format']}"}


def summary_md(d: dict[str, Any], st: dict[str, Any] | None = None) -> str:
    st = st or stage(d)
    c = st["counts"]
    _, _, nlabel = NOTATION[d.get("notation") or "ko_mm"]
    lines = [f"- 제품 {c['models']} · 항목 {c['columns']} · {st['format']} · {nlabel}"]
    if c["pendingCells"] or c["warnings"]:
        lines.append(f"- 확인 필요 값 {c['pendingCells']} · 경고 {c['warnings']}")
    return "\n".join(lines)


async def finish(fid: str) -> dict[str, Any]:
    d = await load(fid)
    c = counts(d)
    if c["models"] == 0:
        raise ApiError(422, "NO_MODELS", "시트에 넣을 제품을 하나 이상 골라 주세요.")
    if c["columns"] == 0:
        raise ApiError(422, "NO_COLUMNS", "항목을 하나 이상 골라 주세요.")

    def fn(doc: dict[str, Any]) -> None:
        doc["ver"] = int(doc.get("ver") or 0) + 1
        doc["status"] = "done"
        doc["saved_at"] = now_iso()
        doc["file"] = None
    saved = await update(fid, fn, "저장")
    f = await make_xlsx(saved)
    if f:
        saved = await update(fid, lambda doc: doc.update({"file": f}), "XLSX")
    st = stage(saved)
    md = summary_md(saved, st)
    await register_item(feature="SP", item_id=fid, title=saved.get("title") or "Spec 시트", status="done", route=f"/spec/flow/{fid}",
                        summary=f"제품 {st['counts']['models']} · 항목 {st['counts']['columns']} · {st['format']}")
    sync = None
    if saved.get("sb_id"):
        sync = await push_stage(saved["sb_id"], "sp", ref=saved.get("code") or fid, ver=int(saved.get("ver") or 1), res_id=fid,
                                title=saved.get("title"), value=st, md=md, card=card(saved, st))
    return {"stage": st, "summary_md": md, "flow_sync": {"md_added": sync["md_added"], "synced": sync["synced"]} if sync else None,
            "file": saved.get("file")}


async def get_stage(fid: str) -> dict[str, Any]:
    d = await load(fid)
    st = stage(d)
    return {"stage": st, "summary_md": summary_md(d, st), "flow_sync": None, "file": d.get("file")}
