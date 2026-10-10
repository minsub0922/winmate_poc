"""공간별 제품 매칭 DSS(새 콘텐츠 흐름, 2026-10-08 — 보드 webapp1 DS0 · DS1 · DS2 · DS2_AI · DS4 · DS4_AI · DS_Done).

Storyboard(고객 요구사항까지)에서 시작해 업종 → 공간 → 공간별 제품 → 솔루션(0개 이상)을 정하고, 저장하면 flow.json `stages.dss` 에 넣는다.
- 만들기: `get_flow(sb)` 로 rq 값(요구 문장 · 요약본)을 읽어 문맥으로 둔다. rq 가 없으면 422 PREREQUISITE_MISSING.
- AI 는 버튼으로만(CF-08): 업종 추론 · 공간 추천 · 공간별 제품 자동 매칭(`ds.industry_spaces.v1`) · 솔루션 추천(`ds.solutions.v1`).
  결과는 점선(ai-pending)이고 수락해야 들어간다. 모델이 없거나(mock · 장애) 답이 비면 KB 로 결정적으로 대신한다(`mode=kb_only`):
  업종 = A2, 공간 = S1 공간 + 업종 기본 공간(space-types), 제품 = 공간마다 S1 후보 제품군, 솔루션 = 지원 기기 제품군 · 요구 낱말 · 업종.
- 사실을 지어내지 않는다: 제품은 KB 후보 키로만, 솔루션은 카탈로그 id 로만, 수량은 요구 문장에 있는 수치일 때만(없으면 null → `[확인 필요]`).

저장소: DocStore("dss") 컬렉션 `dss`(dss_ …). 쓰기는 낙관적 잠금 + 재시도, `expected_version` 을 주면 맞지 않을 때 409.
"""
from __future__ import annotations

import asyncio
import copy
import logging
import re
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, Field
from winmate_common.env import settings
from winmate_common.errors import ApiError, not_found
from winmate_common.flow import get_flow, push_stage
from winmate_common.ids import new_id, now_iso
from winmate_common.client import ServiceClient
from winmate_common.platform import register_item
from winmate_common.store import DocStore, VersionConflict

from . import kbx, llm

log = logging.getLogger("winmate.dss")

COLL = "dss"
MAX_SPACES = 20
MAX_PRODUCTS_PER_SPACE = 20

By = Literal["manual", "ai-pending", "ai-accepted"]

# 보드 DS2 업종 목록(순서 그대로) · KB A2(KR 업종) 대응 · 동점일 때만 쓰는 요구 낱말 · 솔루션 카탈로그 industries 키
INDUSTRIES = ["오피스 · 업무시설", "리테일", "외식 · 카페", "호텔 · 숙박", "병원 · 헬스케어", "교육", "공공 · 관공서", "주거 · 복합단지"]
_KR = {
    "오피스 · 업무시설": ["kr_office", "kr_small_office"],
    "리테일": ["kr_retail", "kr_retail_fnb"],
    "외식 · 카페": ["kr_fnb"],
    "호텔 · 숙박": ["kr_hotel"],
    "병원 · 헬스케어": ["kr_hospital", "kr_medical", "kr_clinic"],
    "교육": ["kr_school", "kr_education", "kr_academy"],
    "공공 · 관공서": ["kr_public_agency", "kr_public", "kr_military"],
    "주거 · 복합단지": ["kr_home", "kr_construction", "kr_officetel"],
}
_KR_TO_LABEL = {kr: label for label, krs in _KR.items() for kr in krs}
_WORDS = {
    "오피스 · 업무시설": ["오피스", "사무", "업무", "입주사", "회의실"],
    "리테일": ["매장", "리테일", "쇼핑", "판매", "플래그십"],
    "외식 · 카페": ["카페", "커피", "메뉴", "식당", "외식"],
    "호텔 · 숙박": ["호텔", "객실", "투숙", "리조트"],
    "병원 · 헬스케어": ["병원", "환자", "진료", "의원", "병동"],
    "교육": ["학교", "교실", "강의", "학원", "캠퍼스"],
    "공공 · 관공서": ["공공", "관공서", "민원", "청사"],
    "주거 · 복합단지": ["주거", "아파트", "단지", "복합", "분양"],
}
_SOL_IND = {"오피스 · 업무시설": "office", "리테일": "retail", "외식 · 카페": "retail", "호텔 · 숙박": "hospitality",
            "병원 · 헬스케어": "healthcare", "교육": "education"}


# ── 모델(API) ───────────────────────────────────────────

class DSIndustry(BaseModel):
    value: str
    by: By = "manual"
    basis: str | None = Field(None, description="근거(예: RQ-05 ‘입주사 공용 회의실 예약’)")


class DSIndustrySuggestion(BaseModel):
    value: str
    basis: str | None = None
    alt: str | None = Field(None, description="애매할 때 다른 후보 업종")


class DSProduct(BaseModel):
    id: str
    name: str = Field(description="제품 이름(KB 제품군 · 모델 이름 그대로, 직접 넣은 것은 입력 그대로)")
    kind: Literal["product"] = "product"
    ref: str | None = Field(None, description="KB 참조 — kb:family:fam_… · kb:model:mdl_… (없으면 KB 에 없는 직접 입력)")
    model_code: str | None = Field(None, description="대표 모델코드(상세 시트)")
    family_id: str | None = None
    category: str | None = None
    qty: str | None = Field(None, description="수량(예: 2대) — 모르면 null(화면은 [확인 필요])")
    why: str | None = Field(None, description="용도 · 근거 한 줄")
    by: By = "manual"


class DSSpace(BaseModel):
    key: str
    name: str
    by: By = "manual"
    basis: str | None = Field(None, description="근거(예: RQ-05 1 · 입주사 안내)")
    products: list[DSProduct] = Field(default_factory=list)


class DSSpaceRec(BaseModel):
    name: str
    why: str
    basis: str | None = None
    ext: bool = Field(False, description="요구에는 없는 확장 공간")


class DSSolution(BaseModel):
    id: str = Field(description="솔루션 카탈로그 id(magicinfo …)")
    name: str
    ref: str | None = Field(None, description="kb:solution:sol_…")
    by: By = "manual"
    links: list[str] = Field(default_factory=list, description="함께 쓰는 제품(공간 · 제품)")
    why: str | None = None


class DSSolutionRec(BaseModel):
    id: str
    why: str


class DSReq(BaseModel):
    n: int
    text: str


class DSCounts(BaseModel):
    spaces: int
    products: int
    solutions: int
    pending: int


class DSDoc(BaseModel):
    id: str
    code: str | None = Field(None, description="화면 · flow.json 에 쓰는 짧은 번호(DSS-01 …)")
    title: str
    sb_id: str | None = None
    rq_ref: str | None = Field(None, description="사전 작업 고객 요구사항 ref(근거 표시 RQ-05 1)")
    customer: str | None = None
    reqs: list[DSReq] = Field(default_factory=list, description="요구 문장(근거 번호)")
    industry_options: list[str] = Field(default_factory=lambda: list(INDUSTRIES))
    industry: DSIndustry | None = None
    industry_ai: DSIndustrySuggestion | None = Field(None, description="AI 업종 추론(점선) — 적용해야 들어간다")
    spaces: list[DSSpace] = Field(default_factory=list)
    space_recs: list[DSSpaceRec] = Field(default_factory=list, description="AI 공간 추천(점선) — 추가해야 들어간다")
    solutions: list[DSSolution] = Field(default_factory=list, description="고른 솔루션(0개 이상)")
    solution_recs: list[DSSolutionRec] = Field(default_factory=list, description="AI 솔루션 추천(점선) — 골라야 들어간다")
    status: Literal["draft", "done"] = "draft"
    ver: int | None = Field(None, description="저장(완료) 판 — flow.json stages.dss.ver")
    counts: DSCounts
    version: int
    created_at: str
    updated_at: str


class DSListItem(BaseModel):
    id: str
    code: str | None = None
    title: str
    sb_id: str | None = None
    status: str
    counts: DSCounts
    updated_at: str


class DSList(BaseModel):
    items: list[DSListItem]
    next_cursor: str | None = None


class DSCreate(BaseModel):
    sb_id: str = Field(description="사전 작업(고객 요구사항)이 된 Storyboard")
    title: str | None = None


class DSVersioned(BaseModel):
    expected_version: int | None = Field(None, description="주면 지금 판과 다를 때 409 VERSION_CONFLICT")


class DSSetIndustry(DSVersioned):
    value: str | None = Field(None, max_length=40, description="업종(선택지 또는 직접). null 이면 비움")
    accept_ai: bool = Field(False, description="AI 업종 추론 적용(value 무시)")


class DSAddSpace(DSVersioned):
    name: str = Field(min_length=1, max_length=40)


class DSPatchSpace(DSVersioned):
    name: str = Field(min_length=1, max_length=40)


class DSAddProduct(DSVersioned):
    name: str = Field(min_length=1, max_length=120)
    ref: str | None = None
    model_code: str | None = None
    family_id: str | None = None
    category: str | None = None
    qty: str | None = Field(None, max_length=30)
    why: str | None = Field(None, max_length=120)


class DSPatchProduct(DSVersioned):
    qty: str | None = Field(None, max_length=30, description="빈 문자열이면 수량을 지운다([확인 필요])")
    accept: bool | None = Field(None, description="AI 추천 수락(ai-pending → ai-accepted)")


class DSSetSolutions(DSVersioned):
    ids: list[str] = Field(description="고를 솔루션 카탈로그 id(0개 이상, 순서대로)")


class DSSuggestBody(BaseModel):
    scope: Literal["industry", "spaces", "products", "solutions"]


class DSSuggestResult(BaseModel):
    doc: DSDoc
    added: int
    mode: Literal["llm", "kb_only"] = Field(description="llm = 모델 결과(검증 후) · kb_only = 모델 없이 KB 로 결정적 추천")
    message: str | None = None


class DSCandidate(BaseModel):
    name: str
    kind: Literal["product"] = "product"
    ref: str | None = None
    model_code: str | None = None
    family_id: str | None = None
    category: str | None = None
    why: str | None = None


class DSCandidates(BaseModel):
    space: str
    items: list[DSCandidate]


class DSSolutionOption(BaseModel):
    id: str
    name: str
    desc: str
    ref: str | None = None
    links: list[str] = Field(default_factory=list)
    on: bool = False
    rec: bool = False
    why: str | None = None
    relevant: bool = Field(False, description="함께 쓰는 제품 · 요구 · 업종 중 하나라도 맞음(기본으로 보이는 것)")


class DSSolutionOptions(BaseModel):
    items: list[DSSolutionOption]
    overlap: str | None = Field(None, description="고른 솔루션끼리 겹칠 때 안내(예: 둘 다 사이니지 CMS)")


class DSFlowSync(BaseModel):
    md_added: str
    synced: list[str] = Field(default_factory=list)


class DSStageOut(BaseModel):
    stage: dict[str, Any] = Field(description="Storyboard flow.json 의 stages.dss")
    summary_md: str
    flow_sync: DSFlowSync | None = None


# ── 저장소 ──────────────────────────────────────────────

_stores: dict[str, DocStore] = {}


def _store() -> DocStore:
    path = settings().service_data_dir("dss") / "dss.sqlite"
    st = _stores.get(str(path))
    if st is None:
        st = DocStore(path)
        st.index(COLL, "code")
        st.index(COLL, "sb_id")
        _stores[str(path)] = st
    return st


def slug(name: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z가-힣]+", "-", (name or "").strip().lower()).strip("-")
    return s or "space"


def _norm(s: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "", (s or "").lower())


def _short(text: str, n: int = 18) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def _get(doc_id: str) -> dict[str, Any] | None:
    return _store().get(COLL, doc_id)


async def load(doc_id: str) -> dict[str, Any]:
    d = await asyncio.to_thread(_get, doc_id)
    if d:
        return d
    if re.fullmatch(r"DSS-[0-9A-Za-z]+", doc_id):  # 허브에만 있는 DSS(예시 데이터 · 다른 곳에서 저장) → 편집본으로 가져온다
        adopted = await _adopt(doc_id)
        if adopted:
            return adopted
    raise not_found("DSS", doc_id)


async def update(doc_id: str, fn: Callable[[dict[str, Any]], None], note: str, expected_version: int | None = None) -> dict[str, Any]:
    await load(doc_id)

    def _do() -> dict[str, Any]:
        for _ in range(8):
            cur = _get(doc_id)
            if cur is None:
                raise not_found("DSS", doc_id)
            if expected_version is not None and cur["version"] != expected_version:
                raise ApiError(409, "VERSION_CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러온 뒤 다시 해 주세요.", {"current": cur["version"]})
            work = copy.deepcopy(cur)
            fn(work)
            try:
                return _store().put(COLL, doc_id, work, expected_version=cur["version"], note=note)
            except VersionConflict:
                continue
        raise ApiError(409, "VERSION_CONFLICT", "다른 곳에서 동시에 고쳐 저장하지 못했어요. 다시 시도해 주세요.")
    return await asyncio.to_thread(_do)


def _kept(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [p for p in products if p.get("by") != "ai-pending"]


def counts(d: dict[str, Any]) -> dict[str, int]:
    prods = [p for sp in d.get("spaces") or [] for p in sp.get("products") or []]
    kept = _kept(prods)
    pending = (len(prods) - len(kept)) + len(d.get("space_recs") or []) + (1 if d.get("industry_ai") else 0) \
        + len([r for r in d.get("solution_recs") or [] if r["id"] not in {s["id"] for s in d.get("solutions") or []}])
    return {"spaces": len(d.get("spaces") or []), "products": len(kept), "solutions": len(d.get("solutions") or []), "pending": pending}


def to_api(d: dict[str, Any]) -> dict[str, Any]:
    return {**d, "industry_options": list(INDUSTRIES), "counts": counts(d)}


# ── 문맥(사전 작업) ─────────────────────────────────────

def _reqs_from_flow(flow: dict[str, Any]) -> list[dict[str, Any]]:
    rq = (flow.get("stages") or {}).get("rq") or {}
    out: list[dict[str, Any]] = []
    for r in rq.get("requirements") or []:
        t = (r.get("text") if isinstance(r, dict) else str(r)) or ""
        if t.strip():
            out.append({"n": len(out) + 1, "text": t.strip()})
    if not out:
        for g in rq.get("goals") or []:
            if isinstance(g, str) and g.strip():
                out.append({"n": len(out) + 1, "text": g.strip()})
    return out


def context_text(d: dict[str, Any]) -> str:
    parts = [d.get("title") or "", d.get("customer") or ""] + [r["text"] for r in d.get("reqs") or []]
    return " \n".join(p for p in parts if p) + ("\n" + d["summary_md"][:1500] if d.get("summary_md") else "")


def _tokens(s: str) -> list[str]:
    return [t for t in re.split(r"[^0-9a-zA-Z가-힣]+", s or "") if len(t) >= 2]


def _reqs_for(d: dict[str, Any], words: list[str]) -> list[dict[str, Any]]:
    ws = [w for w in words if w]
    return [r for r in d.get("reqs") or [] if any(w in r["text"] for w in ws)]


def _basis(d: dict[str, Any], ns: list[int]) -> str:
    ref = d.get("rq_ref") or "요구"
    ns = sorted(set(ns))
    return f"{ref} {' · '.join(str(n) for n in ns)}" if ns else ref


def _ns(d: dict[str, Any], keys: list[str]) -> list[int]:
    """모델이 준 요구 키(R1 …) → 실제 있는 번호만."""
    have = {r["n"] for r in d.get("reqs") or []}
    out = []
    for k in keys or []:
        m = re.fullmatch(r"R?(\d+)", str(k).strip())
        if m and int(m.group(1)) in have:
            out.append(int(m.group(1)))
    return out


def _manual_basis(d: dict[str, Any], name: str) -> str | None:
    """직접 넣은 공간의 근거 — 공간 이름 낱말이 모두 나오는 첫 요구 문장(번호 · 그 낱말부터 짧게). 없으면 None(지어내지 않는다)."""
    toks = _tokens(name)
    if not toks:
        return None
    r = next((r for r in d.get("reqs") or [] if all(t in r["text"] for t in toks)), None)
    if r is None:
        return None
    at = min(r["text"].find(t) for t in toks)
    return f"{_basis(d, [r['n']])} · {_short(r['text'][at:], 16)}"


def _covered(d: dict[str, Any], name: str) -> bool:
    n = _norm(name)
    for sp in d.get("spaces") or []:
        m = _norm(sp["name"])
        if n and m and (n in m or m in n):
            return True
    return False


# ── 만들기 · 목록 · 가져오기 ─────────────────────────────

async def _next_code() -> str:
    used: set[int] = set()
    items, _ = await asyncio.to_thread(_store().list, COLL, limit=1000)
    for x in items:
        m = re.fullmatch(r"DSS-(\d+)", x.get("code") or "")
        if m:
            used.add(int(m.group(1)))
    try:                                            # 허브에 이미 쓰인 ref 와 겹치지 않게(같은 ref = 같은 콘텐츠로 동기화된다)
        hub = await ServiceClient("storyboard").get("/v1/flows/contents/dss")
        for x in (hub or {}).get("items") or []:
            m = re.fullmatch(r"DSS-(\d+)", x.get("ref") or "")
            if m:
                used.add(int(m.group(1)))
    except Exception as exc:  # noqa: BLE001
        log.warning("허브 DSS 목록을 읽지 못함: %s", exc)
    n = 1
    while n in used:
        n += 1
    return f"DSS-{n:02d}"


async def create(body: DSCreate) -> dict[str, Any]:
    flow = await get_flow(body.sb_id)
    if flow is None:
        raise ApiError(404, "STORYBOARD_NOT_FOUND", f"Storyboard를 찾을 수 없어요: {body.sb_id}")
    if not (flow.get("stages") or {}).get("rq"):
        raise ApiError(422, "PREREQUISITE_MISSING", "고객 요구사항이 연결된 Storyboard에서 시작할 수 있어요.", {"need": "rq"})
    rq = flow["stages"]["rq"]
    doc = {"code": await _next_code(), "title": body.title or flow.get("name") or "새 DSS", "sb_id": body.sb_id,
           "rq_ref": rq.get("ref"), "customer": rq.get("customer") or flow.get("customer"), "reqs": _reqs_from_flow(flow),
           "summary_md": (flow.get("summary_md") or "")[:3000],
           "industry": None, "industry_ai": None, "spaces": [], "space_recs": [], "solutions": [], "solution_recs": [], "status": "draft"}
    doc_id = new_id("dss")
    saved = await asyncio.to_thread(_store().put, COLL, doc_id, doc, note="만듦")
    await register_item(feature="DS", item_id=doc_id, title=saved["title"], status="draft", route=f"/dss/{doc_id}", summary="업종 · 공간 · 공간별 제품 · 솔루션")
    return to_api(saved)


async def _adopt(code: str) -> dict[str, Any] | None:
    """허브에만 있는 DSS(res_id = ref) → 그 stages.dss 값으로 편집본을 만든다(같은 ref 로 저장하면 연결된 Storyboard 가 함께 바뀐다)."""
    try:
        hub = await ServiceClient("storyboard").get("/v1/flows/contents/dss")
    except Exception:  # noqa: BLE001
        return None
    it = next((x for x in (hub or {}).get("items") or [] if x.get("ref") == code), None)
    if not it or not it.get("storyboards"):
        return None
    sb = it["storyboards"][0]["id"]
    flow = await get_flow(sb)
    st = ((flow or {}).get("stages") or {}).get("dss")
    if not flow or not st:
        return None
    rq = (flow.get("stages") or {}).get("rq") or {}
    spaces = []
    for sp in st.get("spaces") or []:
        prods = []
        for p in sp.get("products") or []:
            q = p.get("qty")
            prods.append({"id": new_id("prd"), "name": p.get("name") or p.get("model") or "", "kind": "product", "ref": p.get("ref"),
                          "model_code": p.get("model_code"), "family_id": None, "category": None,
                          "qty": (f"{q}대" if isinstance(q, int) else q) or None, "why": p.get("why"), "by": p.get("by") or "manual"})
        spaces.append({"key": slug(sp.get("name") or ""), "name": sp.get("name") or "", "by": sp.get("by") or "manual", "basis": sp.get("basis"), "products": prods})
    cat = {s.get("kb_id"): s for s in await kbx.solutions() if s.get("kb_id")}
    sols = []
    for so in st.get("solutions") or []:
        kb_id = (so.get("ref") or "").split(":")[-1] if so.get("ref") else None
        c = cat.get(kb_id) if kb_id else None
        sols.append({"id": (c or {}).get("id") or slug(so.get("name") or ""), "name": so.get("name") or "", "ref": so.get("ref"),
                     "by": so.get("by") or "manual", "links": so.get("links") or [], "why": so.get("why")})
    ind = st.get("industry")
    doc = {"code": code, "title": it.get("title") or flow.get("name") or code, "sb_id": sb, "rq_ref": rq.get("ref"),
           "customer": rq.get("customer") or flow.get("customer"), "reqs": _reqs_from_flow(flow), "summary_md": (flow.get("summary_md") or "")[:3000],
           "industry": {"value": ind.get("value"), "by": ind.get("by") or "manual", "basis": ind.get("basis")} if isinstance(ind, dict) and ind.get("value") else None,
           "industry_ai": None, "spaces": spaces, "space_recs": [], "solutions": sols, "solution_recs": [],
           "status": "done", "ver": int(st.get("ver") or it.get("ver") or 1), "saved_at": it.get("updated_at")}
    saved = await asyncio.to_thread(_store().put, COLL, code, doc, note="허브에서 가져옴")
    await register_item(feature="DS", item_id=code, title=saved["title"], status="done", route=f"/dss/{code}", summary=_summary_line(saved))
    return saved


async def list_docs(limit: int, cursor: str | None) -> dict[str, Any]:
    items, nxt = await asyncio.to_thread(_store().list, COLL, limit=limit, cursor=cursor)
    return {"items": [{"id": d["id"], "code": d.get("code"), "title": d.get("title") or "", "sb_id": d.get("sb_id"), "status": d.get("status", "draft"),
                       "counts": counts(d), "updated_at": d["updated_at"]} for d in items], "next_cursor": nxt}


# ── 고치기 ──────────────────────────────────────────────

def _space(d: dict[str, Any], key: str) -> dict[str, Any]:
    sp = next((s for s in d.get("spaces") or [] if s["key"] == key), None)
    if sp is None:
        raise not_found("공간", key)
    return sp


def _product(d: dict[str, Any], pid: str) -> tuple[dict[str, Any], dict[str, Any]]:
    for sp in d.get("spaces") or []:
        for p in sp.get("products") or []:
            if p["id"] == pid:
                return sp, p
    raise not_found("제품", pid)


async def set_industry(doc_id: str, body: DSSetIndustry) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        if body.accept_ai:
            ai = d.get("industry_ai")
            if not ai:
                raise ApiError(422, "NO_SUGGESTION", "적용할 AI 업종 추론이 없어요.")
            d["industry"] = {"value": ai["value"], "by": "ai-accepted", "basis": ai.get("basis")}
        else:
            v = (body.value or "").strip()
            d["industry"] = {"value": v, "by": "manual", "basis": None} if v else None
        d["industry_ai"] = None
    return to_api(await update(doc_id, fn, "업종", body.expected_version))


async def add_space(doc_id: str, body: DSAddSpace) -> dict[str, Any]:
    name = body.name.strip()

    def fn(d: dict[str, Any]) -> None:
        if len(d.get("spaces") or []) >= MAX_SPACES:
            raise ApiError(422, "TOO_MANY_SPACES", f"공간은 {MAX_SPACES}개까지예요.")
        if any(_norm(s["name"]) == _norm(name) for s in d.get("spaces") or []):
            raise ApiError(409, "SPACE_EXISTS", f"‘{name}’ 공간이 이미 있어요.")
        rec = next((r for r in d.get("space_recs") or [] if _norm(r["name"]) == _norm(name)), None)
        key = slug(name)
        keys = {s["key"] for s in d.get("spaces") or []}
        i = 2
        while key in keys:
            key = f"{slug(name)}-{i}"
            i += 1
        d.setdefault("spaces", []).append({"key": key, "name": name, "by": "ai-accepted" if rec else "manual",
                                           "basis": (rec.get("basis") or rec.get("why")) if rec else _manual_basis(d, name), "products": []})
        d["space_recs"] = [r for r in d.get("space_recs") or [] if _norm(r["name"]) != _norm(name)]
    return to_api(await update(doc_id, fn, "공간 추가", body.expected_version))


async def rename_space(doc_id: str, key: str, body: DSPatchSpace) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        sp = _space(d, key)
        sp["name"] = body.name.strip()
        if sp.get("by") == "manual":                 # 직접 넣은 공간은 새 이름으로 근거를 다시 찾는다
            sp["basis"] = _manual_basis(d, sp["name"])
    return to_api(await update(doc_id, fn, "공간 이름", body.expected_version))


async def delete_space(doc_id: str, key: str, expected_version: int | None = None) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        _space(d, key)
        d["spaces"] = [s for s in d["spaces"] if s["key"] != key]
    return to_api(await update(doc_id, fn, "공간 지움", expected_version))


async def add_product(doc_id: str, key: str, body: DSAddProduct) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        sp = _space(d, key)
        if len(sp.get("products") or []) >= MAX_PRODUCTS_PER_SPACE:
            raise ApiError(422, "TOO_MANY_PRODUCTS", f"제품은 공간마다 {MAX_PRODUCTS_PER_SPACE}개까지예요.")
        name = body.name.strip()
        dup = next((p for p in sp.get("products") or [] if (body.ref and p.get("ref") == body.ref) or _norm(p["name"]) == _norm(name)), None)
        if dup:
            if dup.get("by") == "ai-pending":
                dup["by"] = "ai-accepted"
            return
        fam = body.family_id or (body.ref.split(":")[-1] if body.ref and body.ref.startswith("kb:family:") else None)
        sp.setdefault("products", []).append({
            "id": new_id("prd"), "name": name, "kind": "product", "ref": body.ref, "model_code": body.model_code, "family_id": fam,
            "category": body.category, "qty": (body.qty or "").strip() or None,
            "why": body.why or ("직접 추가" if body.ref else "직접 추가 · KB 에 없음 · 확인 필요"), "by": "manual"})
    return to_api(await update(doc_id, fn, "제품 추가", body.expected_version))


async def patch_product(doc_id: str, pid: str, body: DSPatchProduct) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        _, p = _product(d, pid)
        if body.qty is not None:
            p["qty"] = body.qty.strip() or None
        if body.accept and p.get("by") == "ai-pending":
            p["by"] = "ai-accepted"
    return to_api(await update(doc_id, fn, "제품 고침", body.expected_version))


async def delete_product(doc_id: str, pid: str, expected_version: int | None = None) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        sp, _ = _product(d, pid)
        sp["products"] = [x for x in sp["products"] if x["id"] != pid]
    return to_api(await update(doc_id, fn, "제품 지움", expected_version))


async def accept_all(doc_id: str) -> dict[str, Any]:
    """공간별 제품 AI 추천 모두 수락(보드 DS2_AI '추천 모두 수락 n')."""
    def fn(d: dict[str, Any]) -> None:
        for sp in d.get("spaces") or []:
            for p in sp.get("products") or []:
                if p.get("by") == "ai-pending":
                    p["by"] = "ai-accepted"
    return to_api(await update(doc_id, fn, "AI 추천 모두 수락"))


async def set_solutions(doc_id: str, body: DSSetSolutions) -> dict[str, Any]:
    cat = {s["id"]: s for s in await kbx.solutions()}

    def fn(d: dict[str, Any]) -> None:
        old = {s["id"]: s for s in d.get("solutions") or []}
        recs = {r["id"]: r for r in d.get("solution_recs") or []}
        out = []
        for sid in dict.fromkeys(body.ids):
            if sid in old:
                out.append(old[sid])
                continue
            c = cat.get(sid)
            if c is None:
                raise ApiError(422, "UNKNOWN_SOLUTION", f"카탈로그에 없는 솔루션이에요: {sid}")
            rec = recs.get(sid)
            out.append({"id": sid, "name": c.get("name") or sid, "ref": f"kb:solution:{c['kb_id']}" if c.get("kb_id") else None,
                        "by": "ai-accepted" if rec else "manual", "links": [], "why": rec["why"] if rec else None})
        d["solutions"] = out
    saved = await update(doc_id, fn, "솔루션", body.expected_version)
    return to_api(await _refresh_links(doc_id, saved))


# ── 솔루션 · 함께 쓰는 제품 ──────────────────────────────

def _product_fams(d: dict[str, Any]) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    out = []
    for sp in d.get("spaces") or []:
        for p in _kept(sp.get("products") or []):
            out.append((p.get("family_id") or (p["ref"].split(":")[-1] if (p.get("ref") or "").startswith("kb:family:") else ""), sp, p))
    return out


def _links_for(detail: dict[str, Any] | None, d: dict[str, Any]) -> list[str]:
    """함께 쓰는 제품 — 이 DSS 제품 중 솔루션 지원 기기 제품군에 든 것(공간 · 제품). 제품군을 모르는 직접 입력은 지원 기기 이름 낱말로."""
    sup = (detail or {}).get("supported_devices") or {}
    fams = set(sup.get("family_ids") or [])
    word = (sup.get("label") or "").split()[-1] if sup.get("label") else ""
    by_name: dict[str, list[str]] = {}
    for fam, sp, p in _product_fams(d):
        hit = (fam and fam in fams) or (not fam and word and len(word) >= 2 and word in (p["name"] + (p.get("category") or "")))
        if hit:
            by_name.setdefault(p["name"], [])
            if sp["name"] not in by_name[p["name"]]:
                by_name[p["name"]].append(sp["name"])
    return [f"{' · '.join(spaces)} {name}" for name, spaces in by_name.items()]


async def _details(ids: list[str]) -> dict[str, dict[str, Any] | None]:
    res = await asyncio.gather(*(kbx.solution_detail(i) for i in ids))
    return dict(zip(ids, res))


async def _refresh_links(doc_id: str, d: dict[str, Any]) -> dict[str, Any]:
    if not d.get("solutions"):
        return d
    det = await _details([s["id"] for s in d["solutions"]])
    links = {s["id"]: _links_for(det.get(s["id"]), d) for s in d["solutions"]}
    if all(links[s["id"]] == (s.get("links") or []) for s in d["solutions"]):
        return d

    def fn(doc: dict[str, Any]) -> None:
        for s in doc.get("solutions") or []:
            if s["id"] in links:
                s["links"] = links[s["id"]]
    return await update(doc_id, fn, "함께 쓰는 제품")


def _josa_wa(word: str) -> str:
    ch = (word or " ")[-1]
    if "가" <= ch <= "힣":
        return "과" if (ord(ch) - 0xAC00) % 28 else "와"
    return "와"


def _overlap(selected: list[dict[str, Any]], det: dict[str, dict[str, Any] | None]) -> str | None:
    cats = [(s, ((det.get(s["id"]) or {}).get("category_path") or [""])[-1]) for s in selected]
    for i, (a, ca) in enumerate(cats):
        for b, cb in cats[i + 1:]:
            if ca and cb and (ca in cb or cb in ca):
                cat = ca if len(ca) <= len(cb) else cb
                where = "사이니지" if "사이니지" in cat else "공간"
                return f"{a['name']}{_josa_wa(a['name'])} {b['name']}는 둘 다 {cat}예요. 같은 {where}에 함께 쓰는 경우는 드물어요."
    return None


def _industry_label(d: dict[str, Any]) -> str | None:
    return (d.get("industry") or {}).get("value") or (d.get("industry_ai") or {}).get("value")


def _sol_score(c: dict[str, Any], det: dict[str, Any] | None, d: dict[str, Any]) -> tuple[float, list[int], list[str]]:
    links = _links_for(det, d)
    words = [w for w in _tokens(c.get("desc") or "") if w not in ("디스플레이", "솔루션", "관리", "중심", "모바일", "공간")]
    reqs = _reqs_for(d, words)
    ind = _SOL_IND.get(_industry_label(d) or "")
    score = 2.0 * min(len(links), 2) + 1.0 * min(len(reqs), 2) + (0.5 if ind and ind in (c.get("industries") or []) else 0.0)
    return score, [r["n"] for r in reqs], links


async def solution_options(doc_id: str) -> dict[str, Any]:
    d = await load(doc_id)
    cat = await kbx.solutions()
    det = await _details([c["id"] for c in cat])
    on = {s["id"] for s in d.get("solutions") or []}
    recs = {r["id"]: r["why"] for r in d.get("solution_recs") or []}
    rows = []
    for i, c in enumerate(cat):
        score, _, links = _sol_score(c, det.get(c["id"]), d)
        rows.append((-(score + (100 if c["id"] in recs else 0) + (50 if c["id"] in on else 0)), i, {
            "id": c["id"], "name": c.get("name") or c["id"], "desc": (det.get(c["id"]) or {}).get("subtitle") or c.get("desc") or "",
            "ref": f"kb:solution:{c['kb_id']}" if c.get("kb_id") else None, "links": links, "on": c["id"] in on,
            "rec": c["id"] in recs and c["id"] not in on, "why": recs.get(c["id"]), "relevant": score > 0 or c["id"] in on or c["id"] in recs}))
    rows.sort(key=lambda x: (x[0], x[1]))
    sel = [s for s in d.get("solutions") or []]
    return {"items": [r[2] for r in rows], "overlap": _overlap(sel, det)}


# ── AI 추가기능(점선 → 수락) ────────────────────────────

def _pick_industry(d: dict[str, Any], env: dict[str, Any]) -> dict[str, Any] | None:
    """A2 후보(정규화 점수) + 요구 낱말(동점 가르기) → 보드 업종 하나 · 근거 · 다른 후보."""
    res = env.get("result") if isinstance(env.get("result"), dict) else {}
    cands = list(env.get("candidates") or []) or [{"id": x.get("id"), "score": x.get("score"), "reasons": x.get("signals")} for x in res.get("top2") or []]
    text = context_text(d)
    scores: dict[str, float] = {}
    signals: dict[str, list[str]] = {}
    for c in cands[:8]:
        label = _KR_TO_LABEL.get(c.get("id") or "")
        if not label:
            continue
        s = float(c.get("score") or 0)
        if s > scores.get(label, -1):
            scores[label] = s
            signals[label] = list(c.get("reasons") or [])
    if not scores:
        return None
    hits = {label: [w for w in _WORDS[label] if w in text] for label in scores}
    ranked = sorted(scores, key=lambda lb: (-(scores[lb] + 0.15 * len(hits[lb])), INDUSTRIES.index(lb)))
    best = ranked[0]
    alt = ranked[1] if len(ranked) > 1 and (scores[best] + 0.15 * len(hits[best])) - (scores[ranked[1]] + 0.15 * len(hits[ranked[1]])) < 0.4 else None
    sig_words = [m.group(1) for s in signals.get(best, []) for m in [re.search(r"'([^']+)'", s)] if m]
    reqs = _reqs_for(d, hits[best] + sig_words)[:2]
    quote = " · ".join(f"‘{_short(r['text'], 16)}’" for r in reqs)
    basis = f"{d.get('rq_ref') or '요구'} {quote}".strip() if quote else f"KB 업종 판별 · {' · '.join(sig_words[:2]) or best}"
    if alt:
        basis += f" — {alt.split(' · ')[-1]}일 수도 있어요"
    return {"value": best, "basis": basis, "alt": alt}


async def _kb_space_recs(d: dict[str, Any]) -> list[dict[str, Any]]:
    s1 = await kbx.spaces_products(context_text(d), limit=4)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sp in s1.get("by_space") or []:
        name = sp.get("space_name") or ""
        if not name or _covered(d, name) or _norm(name) in seen:
            continue
        seen.add(_norm(name))
        clause = (sp.get("clauses") or [""])[0]
        ns = [r["n"] for r in d.get("reqs") or [] if clause and (clause in r["text"] or r["text"] in clause)]
        why = f"{_basis(d, ns)} {_short(clause, 20)}".strip() if clause else "KB 요구 분석"
        out.append({"name": name, "why": why, "basis": f"{_basis(d, ns)} · {_short(clause, 16)}" if clause else None, "ext": False})
    label = _industry_label(d) or (_pick_industry(d, await kbx.industry(context_text(d))) or {}).get("value")
    if label:
        n_ext = 0
        for kr in _KR.get(label, []):
            for st in await kbx.space_types(kr):
                name = st.get("name") or ""
                if n_ext >= 3 or not name or _covered(d, name) or _norm(name) in seen:
                    continue
                seen.add(_norm(name))
                n_ext += 1
                out.append({"name": name, "why": f"요구에는 없음 · {label.split(' · ')[0]} 기본 공간", "basis": None, "ext": True})
            if n_ext:
                break
    return out[:6]


async def _space_candidates(d: dict[str, Any], sp: dict[str, Any], limit: int = 4) -> list[dict[str, Any]]:
    """공간 하나 → KB S1 후보 제품군(그 공간 관련 요구 문장 + 공간 이름으로)."""
    reqs = _reqs_for(d, _tokens(sp["name"]))
    label = _industry_label(d) or ""
    text = f"{sp['name']} " + (" ".join(r["text"] for r in reqs) if reqs else f"{label} {sp['name']}")
    s1 = await kbx.spaces_products(text, limit=limit + 2)
    by = s1.get("by_space") or []
    ent = next((b for b in by if b.get("space_name") and (_norm(b["space_name"]) in _norm(sp["name"]) or _norm(sp["name"]) in _norm(b["space_name"]))), None) or (by[0] if by else None)
    if not ent:
        return []
    have = {p.get("family_id") for p in sp.get("products") or []} | {_norm(p["name"]) for p in sp.get("products") or []}
    out, seen = [], set()
    basis = _basis(d, [r["n"] for r in reqs]) if reqs else None
    for f in ent.get("families") or []:
        name = (f.get("name") or "").strip()
        if not name or f.get("id") in have or _norm(name) in have or _norm(name) in seen:
            continue
        seen.add(_norm(name))
        cat = f.get("category") or ent.get("category_name")
        out.append({"name": re.sub(r"\s+", " ", name), "kind": "product", "ref": f"kb:family:{f['id']}" if f.get("id") else None, "model_code": f.get("model"),
                    "family_id": f.get("id"), "category": cat, "why": " · ".join(x for x in [cat, basis] if x) or "KB 공간 추천"})
        if len(out) >= limit:
            break
    return out


async def space_candidates(doc_id: str, key: str) -> dict[str, Any]:
    d = await load(doc_id)
    sp = _space(d, key)
    return {"space": sp["name"], "items": await _space_candidates(d, sp, limit=6)}


def _qty_ok(d: dict[str, Any], qty: Any) -> str | None:
    if not isinstance(qty, str) or llm.mockish(qty):
        return None
    nums = re.findall(r"\d+", qty)
    if not nums:
        return None
    text = " ".join(r["text"] for r in d.get("reqs") or [])
    return qty.strip() if all(n in text for n in nums) else None


async def _llm_industry_spaces(d: dict[str, Any], scope: str, cands: list[dict[str, Any]]) -> dict[str, Any] | None:
    text = context_text(d)
    a2 = await kbx.industry(text) if scope == "industry" else {}
    s1 = await kbx.spaces_products(text, limit=3) if scope == "spaces" else {}
    ask = {"industry": "업종을 하나 고르고 근거 요구 키와 구절을 단다(애매하면 alt).",
           "spaces": "지금 공간에 없는 공간을 최대 6개 추천한다. 요구에서 나온 공간은 basis 에 요구 키, 요구에 없는 업종 기본 공간은 ext=true.",
           "products": "공간마다 후보 제품(P 키) 중 맞는 것을 최대 2개 고르고 용도 한 줄을 단다. 후보에 없는 제품은 쓰지 않는다."}[scope]
    prompt = llm.dump({
        "요청": ask, "범위": scope,
        "요구": [{"키": f"R{r['n']}", "문장": r["text"]} for r in d.get("reqs") or []],
        "Storyboard 요약": (d.get("summary_md") or "")[:1500],
        "업종 선택지": INDUSTRIES, "지금 업종": _industry_label(d),
        "KB 업종 후보": [{"id": x.get("id"), "이름": x.get("name"), "신호": x.get("signals")} for x in ((a2.get("result") or {}).get("top2") or [])],
        "KB 공간 후보": [{"공간": b.get("space_name"), "구절": b.get("clauses")} for b in s1.get("by_space") or []],
        "지금 공간": [sp["name"] for sp in d.get("spaces") or []],
        "후보 제품": [{"키": c["key"], "공간": c["space"], "이름": c["name"], "분류": c.get("category")} for c in cands],
    })
    return await llm.try_call("ds.industry_spaces.v1", prompt, llm.IndustrySpacesOut)


async def suggest(doc_id: str, body: DSSuggestBody) -> dict[str, Any]:
    if body.scope == "solutions":
        return await suggest_solutions(doc_id)
    d = await load(doc_id)
    scope = body.scope
    cands: list[dict[str, Any]] = []
    if scope == "products":
        if not d.get("spaces"):
            raise ApiError(422, "NO_SPACES", "공간을 먼저 하나 이상 넣어 주세요.")
        per = await asyncio.gather(*(_space_candidates(d, sp) for sp in d["spaces"]))
        for sp, items in zip(d["spaces"], per):
            for c in items:
                cands.append({**c, "key": f"P{len(cands) + 1}", "space": sp["name"], "space_key": sp["key"]})
    out = await _llm_industry_spaces(d, scope, cands)
    mode = "llm"
    ind_sug: dict[str, Any] | None = None
    space_recs: list[dict[str, Any]] = []
    prod_sug: list[dict[str, Any]] = []
    text = context_text(d)
    if out and scope == "industry" and out.get("industry"):
        io = out["industry"]
        if io.get("value") in INDUSTRIES:
            quotes = [q for q in io.get("quote") or [] if isinstance(q, str) and q.strip() and q.strip() in text][:2]
            ns = _ns(d, io.get("basis") or [])
            basis = f"{d.get('rq_ref') or '요구'} " + (" · ".join(f"‘{q.strip()}’" for q in quotes) if quotes else " · ".join(str(n) for n in ns))
            alt = io.get("alt") if io.get("alt") in INDUSTRIES and io.get("alt") != io["value"] else None
            if alt:
                basis += f" — {alt.split(' · ')[-1]}일 수도 있어요"
            ind_sug = {"value": io["value"], "basis": basis.strip(), "alt": alt}
    if out and scope == "spaces":
        seen: set[str] = set()
        for so in out.get("spaces") or []:
            name = (so.get("name") or "").strip()
            if llm.mockish(name) or llm.mockish(so.get("why")) or _covered(d, name) or _norm(name) in seen or len(name) > 40:
                continue
            seen.add(_norm(name))
            ns = _ns(d, so.get("basis") or [])
            why = so["why"].strip()
            space_recs.append({"name": name, "why": f"{d.get('rq_ref')} {why}" if ns and d.get("rq_ref") else why,
                               "basis": f"{_basis(d, ns)} · {why}" if ns else None, "ext": bool(so.get("ext")) and not ns})
    if out and scope == "products":
        by_key = {c["key"]: c for c in cands}
        for po in out.get("products") or []:
            c = by_key.get(po.get("cand"))
            if not c or llm.mockish(po.get("why")):
                continue
            ns = _ns(d, po.get("basis") or [])
            prod_sug.append({**c, "why": f"{po['why'].strip()} · {_basis(d, ns)}" if ns else po["why"].strip(), "qty": _qty_ok(d, po.get("qty"))})
    # 모델 결과가 없으면 KB 로 결정적 추천
    if scope == "industry" and not ind_sug:
        mode = "kb_only"
        ind_sug = _pick_industry(d, await kbx.industry(text))
    if scope == "spaces" and not space_recs:
        mode = "kb_only"
        space_recs = await _kb_space_recs(d)
    if scope == "products" and not prod_sug:
        mode = "kb_only"
        per_space: dict[str, int] = {}
        for c in cands:
            if per_space.get(c["space_key"], 0) < 2:
                per_space[c["space_key"]] = per_space.get(c["space_key"], 0) + 1
                prod_sug.append({**c, "qty": None})
    added = 0

    def fn(doc: dict[str, Any]) -> None:
        nonlocal added
        if scope == "industry":
            doc["industry_ai"] = ind_sug
            added = 1 if ind_sug else 0
        elif scope == "spaces":
            doc["space_recs"] = [r for r in space_recs if not _covered(doc, r["name"])]
            added = len(doc["space_recs"])
        else:
            by_name = {sp["name"]: sp for sp in doc.get("spaces") or []}
            by_key = {sp["key"]: sp for sp in doc.get("spaces") or []}
            for c in prod_sug:
                sp = by_key.get(c.get("space_key")) or by_name.get(c.get("space"))
                if sp is None or len(sp.get("products") or []) >= MAX_PRODUCTS_PER_SPACE:
                    continue
                if any((c.get("family_id") and p.get("family_id") == c["family_id"]) or _norm(p["name"]) == _norm(c["name"]) for p in sp.get("products") or []):
                    continue
                sp.setdefault("products", []).append({"id": new_id("prd"), "name": c["name"], "kind": "product", "ref": c.get("ref"), "model_code": c.get("model_code"),
                                                      "family_id": c.get("family_id"), "category": c.get("category"), "qty": c.get("qty"),
                                                      "why": c.get("why"), "by": "ai-pending"})
                added += 1
    saved = await update(doc_id, fn, {"industry": "AI 업종 추론", "spaces": "AI 공간 추천", "products": "AI 공간별 제품 자동 매칭"}[scope])
    msg = None if added else {"industry": "KB 에서 업종을 판별하지 못했어요. 직접 골라 주세요.", "spaces": "더 추천할 공간이 없어요.",
                              "products": "더할 제품 추천이 없어요. 공간 이름을 구체적으로 바꾸거나 직접 찾아 넣어 주세요."}[scope]
    return {"doc": to_api(saved), "added": added, "mode": mode, "message": msg}


async def suggest_solutions(doc_id: str) -> dict[str, Any]:
    d = await load(doc_id)
    cat = await kbx.solutions()
    det = await _details([c["id"] for c in cat])
    scored = {c["id"]: _sol_score(c, det.get(c["id"]), d) for c in cat}
    prods = [f"{sp['name']} · {p['name']}" for sp in d.get("spaces") or [] for p in _kept(sp.get("products") or [])]
    prompt = llm.dump({
        "요청": "이 DSS 에 맞는 솔루션을 최대 3개 고르고 이유 한 줄과 근거 요구 키를 단다. 같은 역할(예: 사이니지 CMS 둘)은 하나만. 카탈로그 id 로만 가리킨다.",
        "요구": [{"키": f"R{r['n']}", "문장": r["text"]} for r in d.get("reqs") or []],
        "업종": _industry_label(d), "공간 · 제품": prods[:40],
        "솔루션 카탈로그": [{"id": c["id"], "이름": c.get("name"), "설명": c.get("desc"), "지원 기기": ((det.get(c["id"]) or {}).get("supported_devices") or {}).get("label"),
                       "함께 쓰는 제품": scored[c["id"]][2]} for c in cat],
    })
    out = await llm.try_call("ds.solutions.v1", prompt, llm.SolutionsOut)
    mode = "llm"
    recs: list[dict[str, Any]] = []
    ids = {c["id"] for c in cat}
    for it in (out or {}).get("items") or []:
        if it.get("id") in ids and not llm.mockish(it.get("why")) and it["id"] not in {r["id"] for r in recs}:
            ns = _ns(d, it.get("basis") or [])
            recs.append({"id": it["id"], "why": f"{_basis(d, ns)} {it['why'].strip()}" if ns else it["why"].strip()})
    if not recs:
        mode = "kb_only"
        cats_used: list[str] = []
        for c in sorted(cat, key=lambda c: -scored[c["id"]][0]):
            score, ns, links = scored[c["id"]]
            if score < 2 or len(recs) >= 3:
                continue
            cp = ((det.get(c["id"]) or {}).get("category_path") or [""])[-1]
            if cp and any(cp in u or u in cp for u in cats_used):        # 같은 역할(둘 다 사이니지 CMS)은 하나만
                continue
            cats_used.append(cp)
            parts = []
            if ns:
                parts.append(f"{_basis(d, ns[:1])} {_short(next(r['text'] for r in d['reqs'] if r['n'] == ns[0]), 16)}")
            if links:
                parts.append(f"함께 쓰는 제품 {len(links)}")
            recs.append({"id": c["id"], "why": " · ".join(parts) or "업종 · KB 추천"})
    on = {s["id"] for s in d.get("solutions") or []}

    def fn(doc: dict[str, Any]) -> None:
        doc["solution_recs"] = recs
    saved = await update(doc_id, fn, "AI 솔루션 추천")
    added = len([r for r in recs if r["id"] not in on])
    return {"doc": to_api(saved), "added": added, "mode": mode, "message": None if added else "더 추천할 솔루션이 없어요. 솔루션 없이 저장해도 돼요."}


# ── 저장 · flow.json ────────────────────────────────────

def _qty_view(q: str | None) -> str:
    return q if q else "[확인 필요]"


def stage(d: dict[str, Any]) -> dict[str, Any]:
    spaces = []
    for sp in d.get("spaces") or []:
        prods = []
        for p in _kept(sp.get("products") or []):
            row: dict[str, Any] = {"name": p["name"], "kind": "product", "ref": p.get("ref"), "model_code": p.get("model_code"), "qty": p.get("qty"), "by": p["by"]}
            if not p.get("qty") or "[" in (p.get("qty") or ""):
                row["qtyStatus"] = "확인 필요"
            prods.append(row)
        spaces.append({"name": sp["name"], "by": sp.get("by") or "manual", "basis": sp.get("basis"), "products": prods})
    ind = d.get("industry")
    c = counts(d)
    return {"id": d["id"], "from": d.get("sb_id"),
            "industry": {"value": ind["value"], "by": ind.get("by") or "manual", "basis": ind.get("basis")} if ind else None,
            "spaces": spaces,
            "solutions": [{"name": s["name"], "ref": s.get("ref"), "by": s.get("by") or "manual", "links": s.get("links") or [], "why": s.get("why")}
                          for s in d.get("solutions") or []],
            "counts": {"spaces": c["spaces"], "products": c["products"], "solutions": c["solutions"]}}


def _prod_line(p: dict[str, Any]) -> str:
    m = re.fullmatch(r"\s*(\d+)\s*대?\s*", p.get("qty") or "")
    return f"{p['name']} ×{m.group(1)}" if m and m.group(1) != "1" else p["name"]


def _summary_line(d: dict[str, Any]) -> str:
    c = counts(d)
    return f"공간 {c['spaces']} · 제품 {c['products']} · 솔루션 {c['solutions']}"


def summary_md(d: dict[str, Any]) -> str:
    c = counts(d)
    ind = (d.get("industry") or {}).get("value") or "[확인 필요]"
    lines = [f"## DSS · {d.get('code') or d['id']} v{d.get('ver') or 1}", f"- 업종: {ind} · 공간 {c['spaces']}"]
    spaces = d.get("spaces") or []
    for sp in spaces[:4]:
        prods = _kept(sp.get("products") or [])
        lines.append(f"- {sp['name']}: " + (" · ".join(_prod_line(p) for p in prods[:4]) + (f" 외 {len(prods) - 4}" if len(prods) > 4 else "") if prods else "제품 없음"))
    if len(spaces) > 4:
        lines.append(f"- 그 밖의 공간 {len(spaces) - 4}: " + " · ".join(sp["name"] for sp in spaces[4:]))
    if d.get("solutions"):
        lines.append("- 솔루션: " + " · ".join(s["name"] for s in d["solutions"]))
    return "\n".join(lines)


def card(d: dict[str, Any]) -> dict[str, Any]:
    c = counts(d)
    groups = []
    for sp in (d.get("spaces") or [])[:3]:
        prods = _kept(sp.get("products") or [])
        groups.append({"h": sp["name"], "sub": f"제품 {len(prods)}",
                       "lines": [{"t": f"{p['name']} · {_qty_view(p.get('qty'))}", "note": "확인 필요" if not p.get("qty") else None} for p in prods[:3]]})
    ind = (d.get("industry") or {}).get("value") or "[확인 필요]"
    return {"title": d.get("title") or "DSS", "facts": [["업종", ind], ["공간", str(c["spaces"])], ["제품 · 솔루션", f"{c['products']} · {c['solutions']}"]],
            "groups": groups, "foot": "수량이 빈 제품은 [확인 필요]로 표시돼요",
            "line": f"{d.get('code')} v{d.get('ver') or 1} · 업종 {ind} · 공간 {c['spaces']} · 제품 {c['products']} · 솔루션 {c['solutions']}"}


async def finish(doc_id: str) -> dict[str, Any]:
    d = await load(doc_id)
    c = counts(d)
    if c["spaces"] == 0:
        raise ApiError(422, "NO_SPACES", "공간을 하나 이상 넣어 주세요.")
    if c["products"] == 0:
        raise ApiError(422, "NO_PRODUCTS", "공간에 제품을 하나 이상 넣어 주세요. 수락하지 않은 추천은 저장되지 않아요.")
    d = await _refresh_links(doc_id, d)

    def fn(doc: dict[str, Any]) -> None:
        doc["ver"] = int(doc.get("ver") or 0) + 1 if (doc.get("status") == "done" or doc.get("saved_at")) else 1
        doc["status"] = "done"
        doc["saved_at"] = now_iso()
    saved = await update(doc_id, fn, "저장")
    await register_item(feature="DS", item_id=doc_id, title=saved.get("title") or "DSS", status="done", route=f"/dss/{doc_id}", summary=_summary_line(saved))
    st, md = stage(saved), summary_md(saved)
    sync = None
    if saved.get("sb_id"):
        sync = await push_stage(saved["sb_id"], "dss", ref=saved.get("code") or doc_id, ver=int(saved.get("ver") or 1), res_id=doc_id,
                                title=saved.get("title"), value=st, md=md, card=card(saved))
    return {"stage": st, "summary_md": md, "flow_sync": {"md_added": sync["md_added"], "synced": sync.get("synced") or []} if sync else None}


async def get_stage(doc_id: str) -> dict[str, Any]:
    d = await load(doc_id)
    return {"stage": stage(d), "summary_md": summary_md(d), "flow_sync": None}
