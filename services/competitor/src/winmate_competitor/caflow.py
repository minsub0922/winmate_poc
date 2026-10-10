"""경쟁사 리스트업(새 CA 흐름, 2026-10-08 — 보드 webapp1 CA2 · CA2_Info · CA2_Pc · CA2_AI · CA_Done · CA_DoneJson).

Storyboard(사전 작업 DSS)의 제품 · 공간을 기준으로 경쟁사를 리스트업하고, 우리 제안과 5축으로 비교한다.
- 만들기: `get_flow(sb)` → DSS 공간 · 제품 · 솔루션 → 비교 기준(basis.categories: 제품군 규칙 분류 · 개수).
- 경쟁사 = 직접(manual) · AI 웹 탐색 후보(ai-pending, 점선 → 수락하면 ai-web).
  직접 추가는 웹 검색 요약에서 기본 정보(위키)를 읽고(`ca.flow_wiki.v1`), 요약 원문에 근거 구절이 없는 값은 `[위키 값]` · `[확인 필요]`.
- 비교 쌍(matches) = DSS 공간 · 제품(우리) ↔ 경쟁 제품, 5축(스펙 · 가격 · 유관 사례 · ESG · 브랜드 평판) 판정 우위/비슷/열위/자료 없음 + 한 줄 메모.
  직접 추가는 겹치는 제품군의 DSS 제품으로 쌍을 만들고 판정은 `자료 없음` 으로 둔다(사람이 고친다).
- AI 경쟁사 후보군 웹 탐색(`ca.flow_candidates_web.v1` 웹 검색 → `ca.flow_candidates.v1` 정리): 요약에 이름 · 근거 구절이 실제로 있는 후보만.
  모델 · 웹이 안 되면 후보 0(지어내지 않는다) — `mode=none` · reason.
- 저장(:finish) → Storyboard flow.json `stages.ca`(docs/scenarios/11-content-flow.md §6 `ca`) · 요약 md · 팝업 카드.

저장소: competitor DocStore 컬렉션 `ca_flows`(cflow_ …, 코드 CA-NN). 쓰기는 낙관적 잠금 + 재시도, expected_version 을 주면 다르면 409.
"""
from __future__ import annotations

import asyncio
import copy
import logging
import re
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, Field
from winmate_common.errors import ApiError, not_found
from winmate_common.flow import get_flow, push_stage
from winmate_common.ids import new_id, now_iso
from winmate_common.platform import register_item
from winmate_common.store import VersionConflict

from . import aix
from .store import store

log = logging.getLogger("winmate.competitor.caflow")

COLL = "ca_flows"
MAX_COMPETITORS = 12
MAX_CANDIDATES = 3
MAX_DERIVED_MATCHES = 4

DIMS: list[tuple[str, str]] = [("spec", "스펙"), ("price", "가격"), ("cases", "유관 사례"), ("esg", "ESG"), ("brand", "브랜드 평판")]
DIM_KEYS = [k for k, _ in DIMS]
VERDICTS = ("ours-better", "similar", "ours-worse", "no-data")
WIKI_KEYS = ["hq", "size", "revenue", "employees", "industry", "mainBusiness", "b2bOffice"]
WIKI_LABEL = {"hq": "본사", "size": "규모", "revenue": "매출", "employees": "임직원", "industry": "업종", "mainBusiness": "주력 사업", "b2bOffice": "B2B 오피스"}
NUM_PLACEHOLDER = {"revenue", "employees"}          # 숫자 값 — 근거 없으면 [위키 값]

# 제품군 규칙(이름 → 비교 기준 제품군). 순서 = 화면 칩 순서
CATEGORY_ORDER = ["사이니지", "LED", "협업 디스플레이", "비디오월", "키오스크", "기타 디스플레이", "IoT · 솔루션"]
_CAT_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("LED", re.compile(r"the\s*wall|\bled\b|\biab\b|\bifr\b|\bia\d", re.I)),
    ("협업 디스플레이", re.compile(r"flip|\bwa\d|\bwm\d|인터랙티브|전자\s*칠판|interactive", re.I)),
    ("비디오월", re.compile(r"비디오\s*월|video\s*wall|\bvm\d|\bvh\d|\bvmb", re.I)),
    ("키오스크", re.compile(r"kiosk|키오스크|\bkm\d", re.I)),
    ("사이니지", re.compile(r"signage|사이니지|\bq[mbhe]\d|\bom\d|\bqmc|\bqbc", re.I)),
]

By = Literal["manual", "ai-pending", "ai-web"]
Verdict = Literal["ours-better", "similar", "ours-worse", "no-data"]


# ── 모델(API) ───────────────────────────────────────────

class CFSource(BaseModel):
    type: str = Field(description="Wikipedia · 웹 검색 요약 · 직접 입력 …")
    url: str | None = None
    title: str | None = None


class CFWiki(BaseModel):
    hq: str = "[확인 필요]"
    size: str = "[확인 필요]"
    revenue: str = "[위키 값]"
    employees: str = "[위키 값]"
    industry: str = "[확인 필요]"
    mainBusiness: str = "[확인 필요]"
    b2bOffice: str = "[확인 필요]"
    source: CFSource


class CFCriterion(BaseModel):
    k: str
    v: str
    status: Literal["ok", "check"] = "ok"


class CFDim(BaseModel):
    verdict: Verdict = "no-data"
    note: str = "자료 없음"


class CFDims(BaseModel):
    spec: CFDim = Field(default_factory=CFDim)
    price: CFDim = Field(default_factory=CFDim)
    cases: CFDim = Field(default_factory=CFDim)
    esg: CFDim = Field(default_factory=CFDim)
    brand: CFDim = Field(default_factory=CFDim)


class CFMatch(BaseModel):
    id: str
    space: str = Field(description="DSS 공간(또는 쓰임 — 로비 미디어월)")
    ours: str = Field(description="우리 제품 · 솔루션(DSS)")
    ours_ref: str | None = None
    theirs: str = Field(description="경쟁 제품 한 줄")
    dims: CFDims


class CFClaim(BaseModel):
    axis: str = Field(description="주장 축(통합 · 사례 · 가격 · ESG · 브랜드 …)")
    text: str
    supports: str | None = Field(None, description="연결 요구(예: RQ-01)")


class CFEvidence(BaseModel):
    source: str = Field(description="근거 출처 이름(업계 뉴스 · 회사 소개 페이지 · 조달 공고 …)")
    date: str | None = None
    quote: str = Field(description="웹 검색 요약 원문 구절")
    url: str | None = None


class CFCompetitor(BaseModel):
    id: str = Field(description="목록 글자(A · B · C …)")
    name: str
    by: By
    industry: str = Field("[확인 필요]", description="목록 한 줄 — 업종")
    size: str = Field("[확인 필요]", description="목록 한 줄 — 규모")
    categories: list[str] = Field(default_factory=list, description="겹치는 비교 기준 제품군")
    spaces: list[str] = Field(default_factory=list, description="겹치는 DSS 공간")
    why: str = Field("", description="목록 둘째 줄 — 겹침 · 공간")
    wiki: CFWiki
    criteria: list[CFCriterion] = Field(default_factory=list)
    matches: list[CFMatch] = Field(default_factory=list)
    pros: list[str] = Field(default_factory=list, description="경쟁사 장점 · 삼성 대비")
    cons: list[str] = Field(default_factory=list, description="경쟁사 단점 · 삼성 대비")
    claims: list[CFClaim] = Field(default_factory=list, description="그래서 우리가 주장할 것")
    candidateEvidence: CFEvidence | None = None


class CFDssItem(BaseModel):
    name: str
    kind: Literal["product", "solution"]
    ref: str | None = None
    spaces: list[str] = Field(default_factory=list)
    category: str


class CFBasis(BaseModel):
    from_: str | None = Field(None, alias="from", description="DSS 참조(DSS-01)")
    categories: list[str]
    counts: dict[str, int] = Field(default_factory=dict, description="제품군마다 DSS 제품 · 솔루션 수")

    model_config = {"populate_by_name": True}


class CFVerdictCounts(BaseModel):
    oursBetter: int
    similar: int
    oursWorse: int
    noData: int


class CFCounts(BaseModel):
    competitors: int
    candidates: int
    matches: int
    verdicts: CFVerdictCounts


class CFDoc(BaseModel):
    id: str
    code: str | None = Field(None, description="CA-01 …")
    title: str
    sb_id: str | None = None
    customer: str | None = None
    basis: CFBasis
    dss_items: list[CFDssItem] = Field(default_factory=list, description="비교 쌍에 고를 수 있는 DSS 제품 · 솔루션")
    competitors: list[CFCompetitor] = Field(default_factory=list)
    status: Literal["draft", "done"] = "draft"
    ver: int | None = Field(None, description="저장(완료) 판 — flow.json stages.ca.ver")
    counts: CFCounts
    version: int
    created_at: str
    updated_at: str


class CFListItem(BaseModel):
    id: str
    code: str | None = None
    title: str
    sb_id: str | None = None
    status: str
    counts: CFCounts
    updated_at: str


class CFList(BaseModel):
    items: list[CFListItem]
    next_cursor: str | None = None


class CFCreate(BaseModel):
    sb_id: str = Field(description="사전 작업 DSS 가 된 Storyboard")
    title: str | None = Field(None, max_length=120)


class CFPatch(BaseModel):
    title: str | None = Field(None, max_length=120)
    expected_version: int | None = None


class CFCompetitorAdd(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    lookup: bool = Field(True, description="웹 검색으로 기본 정보(위키)를 불러온다")
    expected_version: int | None = None


class CFWikiPatch(BaseModel):
    hq: str | None = None
    size: str | None = None
    revenue: str | None = None
    employees: str | None = None
    industry: str | None = None
    mainBusiness: str | None = None
    b2bOffice: str | None = None
    source_url: str | None = None


class CFCompetitorPatch(BaseModel):
    name: str | None = Field(None, max_length=80)
    accept: bool | None = Field(None, description="AI 후보를 목록에 추가(ai-pending → ai-web)")
    wiki: CFWikiPatch | None = None
    criteria: list[CFCriterion] | None = None
    pros: list[str] | None = None
    cons: list[str] | None = None
    claims: list[CFClaim] | None = None
    expected_version: int | None = None


class CFMatchAdd(BaseModel):
    ours: str = Field(min_length=1, max_length=120, description="우리 제품 · 솔루션(DSS 이름)")
    space: str | None = Field(None, max_length=60)
    theirs: str = Field("[확인 필요]", max_length=120)
    expected_version: int | None = None


class CFDimPatch(BaseModel):
    verdict: Verdict | None = None
    note: str | None = Field(None, max_length=120)


class CFMatchPatch(BaseModel):
    space: str | None = Field(None, max_length=60)
    theirs: str | None = Field(None, max_length=120)
    dims: dict[Literal["spec", "price", "cases", "esg", "brand"], CFDimPatch] | None = None
    expected_version: int | None = None


class CFCandidatesResult(BaseModel):
    flow: CFDoc
    added: int
    mode: Literal["web", "none"] = Field(description="web = 웹 검색 요약에서 후보를 찾음 · none = 웹 · 모델이 안 돼 찾지 못함")
    reason: str | None = None


class CFFlowSync(BaseModel):
    md_added: str
    synced: list[str] = Field(default_factory=list)


class CFStageOut(BaseModel):
    stage: dict[str, Any] = Field(description="Storyboard flow.json 의 stages.ca")
    summary_md: str
    flow_sync: CFFlowSync | None = None


# ── 저장소 ──────────────────────────────────────────────

def _get(fid: str) -> dict[str, Any]:
    d = store().get(COLL, fid)
    if not d:
        raise not_found("경쟁사 분석", fid)
    return d


async def load(fid: str) -> dict[str, Any]:
    return await asyncio.to_thread(_get, fid)


async def update(fid: str, fn: Callable[[dict[str, Any]], None], note: str | None = None, expected: int | None = None) -> dict[str, Any]:
    def _do() -> dict[str, Any]:
        for _ in range(6):
            cur = _get(fid)
            if expected is not None and cur["version"] != expected:
                raise ApiError(409, "CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러온 뒤 다시 고쳐 주세요.",
                               {"current_version": cur["version"]})
            work = copy.deepcopy(cur)
            fn(work)
            try:
                return store().put(COLL, fid, work, expected_version=cur["version"], note=note)
            except VersionConflict:
                if expected is not None:
                    raise ApiError(409, "CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러온 뒤 다시 고쳐 주세요.") from None
                continue
        raise ApiError(409, "CONFLICT", "다른 곳에서 동시에 고쳐 저장하지 못했어요. 다시 시도해 주세요.")
    return await asyncio.to_thread(_do)


def _in_list(c: dict[str, Any]) -> bool:
    return c.get("by") != "ai-pending"


def verdict_counts(comps: list[dict[str, Any]]) -> dict[str, int]:
    out = {"oursBetter": 0, "similar": 0, "oursWorse": 0, "noData": 0}
    key = {"ours-better": "oursBetter", "similar": "similar", "ours-worse": "oursWorse", "no-data": "noData"}
    for c in comps:
        for m in c.get("matches") or []:
            for k in DIM_KEYS:
                out[key[((m.get("dims") or {}).get(k) or {}).get("verdict") or "no-data"]] += 1
    return out


def counts(d: dict[str, Any]) -> dict[str, Any]:
    comps = [c for c in d.get("competitors") or [] if _in_list(c)]
    return {"competitors": len(comps), "candidates": sum(1 for c in d.get("competitors") or [] if not _in_list(c)),
            "matches": sum(len(c.get("matches") or []) for c in comps), "verdicts": verdict_counts(comps)}


def to_api(d: dict[str, Any]) -> dict[str, Any]:
    return {**d, "counts": counts(d)}


# ── DSS → 비교 기준 ─────────────────────────────────────

def category_of(name: str, kind: str) -> str:
    if kind == "solution":
        return "IoT · 솔루션"
    for cat, rx in _CAT_RULES:
        if rx.search(name or ""):
            return cat
    return "기타 디스플레이"


def dss_items(flow: dict[str, Any]) -> list[dict[str, Any]]:
    """flow.json stages.dss → 제품 · 솔루션(공간 · 제품군 붙여서)."""
    dss = (flow.get("stages") or {}).get("dss") or {}
    out: dict[str, dict[str, Any]] = {}
    for sp in dss.get("spaces") or []:
        for p in sp.get("products") or []:
            name = (p.get("name") if isinstance(p, dict) else p) or ""
            if not name.strip():
                continue
            kind = "solution" if isinstance(p, dict) and p.get("kind") == "solution" else "product"
            it = out.setdefault(name, {"name": name, "kind": kind, "ref": p.get("ref") if isinstance(p, dict) else None, "spaces": [],
                                       "category": category_of(name, kind)})
            if sp.get("name") and sp["name"] not in it["spaces"]:
                it["spaces"].append(sp["name"])
    for so in dss.get("solutions") or []:
        name = (so.get("name") if isinstance(so, dict) else so) or ""
        if name.strip() and name not in out:
            spaces = []
            for ln in (so.get("links") or []) if isinstance(so, dict) else []:
                s = ln.get("space") if isinstance(ln, dict) else None
                if s and s not in spaces:
                    spaces.append(s)
            out[name] = {"name": name, "kind": "solution", "ref": so.get("ref") if isinstance(so, dict) else None, "spaces": spaces,
                         "category": "IoT · 솔루션"}
    return list(out.values())


def basis_of(flow: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    cnt: dict[str, int] = {}
    for it in items:
        cnt[it["category"]] = cnt.get(it["category"], 0) + 1
    cats = [c for c in CATEGORY_ORDER if c in cnt]
    dss = (flow.get("stages") or {}).get("dss") or {}
    return {"from": dss.get("ref"), "categories": cats, "counts": {c: cnt[c] for c in cats}}


async def create(body: CFCreate) -> dict[str, Any]:
    flow = await get_flow(body.sb_id)
    if flow is None:
        raise ApiError(404, "STORYBOARD_NOT_FOUND", f"Storyboard를 찾을 수 없어요: {body.sb_id}")
    if not (flow.get("stages") or {}).get("dss"):
        raise ApiError(422, "PREREQUISITE_MISSING", "DSS까지 된 Storyboard에서 시작할 수 있어요.", {"need": "dss"})
    items = dss_items(flow)
    rq = (flow.get("stages") or {}).get("rq") or {}
    n = await asyncio.to_thread(store().count, COLL)
    doc = {"code": f"CA-{n + 1:02d}", "title": (body.title or "").strip() or f"{flow.get('name') or body.sb_id} 경쟁사",
           "sb_id": body.sb_id, "customer": flow.get("customer") or rq.get("customer"),
           "industry": (((flow.get("stages") or {}).get("dss") or {}).get("industry") or {}).get("value"),
           "context_text": (flow.get("summary_md") or "")[:4000],
           "basis": basis_of(flow, items), "dss_items": items, "competitors": [], "status": "draft"}
    fid = new_id("cflow")
    saved = await asyncio.to_thread(store().put, COLL, fid, doc, note="만듦")
    await register_item(feature="CA", item_id=fid, title=saved["title"], status="draft", route=f"/competitor/flow/{fid}",
                        summary="경쟁사 리스트업 · 제안 기준 비교")
    return to_api(saved)


async def list_flows(limit: int, cursor: str | None) -> dict[str, Any]:
    items, nxt = await asyncio.to_thread(store().list, COLL, limit=limit, cursor=cursor)
    return {"items": [{"id": d["id"], "code": d.get("code"), "title": d.get("title") or "", "sb_id": d.get("sb_id"),
                       "status": d.get("status", "draft"), "counts": counts(d), "updated_at": d["updated_at"]} for d in items],
            "next_cursor": nxt}


async def patch(fid: str, body: CFPatch) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        if body.title is not None and body.title.strip():
            d["title"] = body.title.strip()
    return to_api(await update(fid, fn, "제목", body.expected_version))


# ── 경쟁사 ──────────────────────────────────────────────

def _letter(d: dict[str, Any]) -> str:
    used = {c["id"] for c in d.get("competitors") or []}
    for i in range(26 * 2):
        s = chr(65 + i % 26) + ("" if i < 26 else str(i // 26 + 1))
        if s not in used:
            return s
    return new_id("c")[-4:]


def _find(d: dict[str, Any], cid: str) -> dict[str, Any]:
    c = next((x for x in d.get("competitors") or [] if x["id"] == cid), None)
    if c is None:
        raise not_found("경쟁사", cid)
    return c


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


_NUM = re.compile(r"\d[\d,\.]*")


def guard_numbers(text: str, evidence: str) -> str:
    """근거 요약에 없는 숫자는 [00] 으로(수치를 지어내지 않는다)."""
    ev = evidence or ""
    return _NUM.sub(lambda m: m.group(0) if m.group(0) in ev else "[00]", text or "")


def _items_in(d: dict[str, Any], cats: list[str]) -> list[dict[str, Any]]:
    return [it for it in d.get("dss_items") or [] if it["category"] in cats]


def _spaces_of(items: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for it in items:
        for s in it.get("spaces") or []:
            if s not in out:
                out.append(s)
    return out


def _why(cats: list[str], spaces: list[str]) -> str:
    if not cats:
        return "겹치는 제품군 [확인 필요]"
    return " · ".join(cats) + " 겹침" + (" · " + " · ".join(spaces[:3]) if spaces else "")


def _blank_dims() -> dict[str, Any]:
    return {k: {"verdict": "no-data", "note": "자료 없음"} for k in DIM_KEYS}


def _derived_matches(d: dict[str, Any], cats: list[str]) -> list[dict[str, Any]]:
    """겹치는 제품군마다 대표 DSS 제품 하나(DSS 순서) → 비교 쌍(경쟁 제품 · 판정은 사람이 채운다)."""
    out = []
    seen: set[str] = set()
    reps = []
    for it in _items_in(d, cats):
        if it["category"] not in seen:
            seen.add(it["category"])
            reps.append(it)
    for it in reps[:MAX_DERIVED_MATCHES]:
        out.append({"id": new_id("cm"), "space": (it.get("spaces") or ["전체"])[0], "ours": it["name"], "ours_ref": it.get("ref"),
                    "theirs": "[확인 필요]", "dims": _blank_dims()})
    return out


def _criteria(d: dict[str, Any], cats: list[str], spaces: list[str], evidence: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ref = (d.get("basis") or {}).get("from") or "DSS"
    where = " ".join(x for x in (ref, " · ".join(spaces[:3])) if x)
    crit = [{"k": "제품군", "v": f"{' · '.join(cats)} — {where} 제품과 겹침" if cats else "[확인 필요]",
             "status": "ok" if cats else "check"},
            {"k": "공간", "v": " · ".join(spaces) if spaces else "[확인 필요]", "status": "ok" if spaces else "check"}]
    if evidence:
        crit.append({"k": "근거", "v": " · ".join(x for x in (evidence.get("source"), evidence.get("date")) if x) or "웹 검색 요약", "status": "ok"})
    elif d.get("customer"):
        crit.append({"k": "고객 접점", "v": f"{d['customer']} 거래 이력", "status": "check"})
    return crit


class _WikiField(BaseModel):
    value: str | None = Field(None, description="요약에 있는 값만(없으면 null)")
    quote: str | None = Field(None, description="값의 근거 — 요약 원문 구절 그대로")


class _WikiOut(BaseModel):
    hq: _WikiField = Field(default_factory=_WikiField, description="본사(국내 · 해외 · 도시)")
    size: _WikiField = Field(default_factory=_WikiField, description="규모(대기업 · 중견 · 중소)")
    revenue: _WikiField = Field(default_factory=_WikiField, description="매출")
    employees: _WikiField = Field(default_factory=_WikiField, description="임직원 수")
    industry: _WikiField = Field(default_factory=_WikiField, description="업종")
    main_business: _WikiField = Field(default_factory=_WikiField, description="주력 사업")
    b2b_office: _WikiField = Field(default_factory=_WikiField, description="B2B 오피스 납품")
    categories: list[str] = Field(default_factory=list, description="이 회사 제품이 겹치는 비교 기준 제품군(입력 목록에서만)")


def _grounded(f: dict[str, Any] | None, summary: str) -> str | None:
    if not f or not (f.get("value") or "").strip() or not (f.get("quote") or "").strip():
        return None
    q, s = _norm(f["quote"]), _norm(summary)
    if q not in s:
        return None
    v = _norm(f["value"])
    if any(m.group(0) not in q for m in _NUM.finditer(v)):     # 값의 숫자는 근거 구절에 있어야
        return None
    return v


def _placeholder(k: str) -> str:
    return "[위키 값]" if k in NUM_PLACEHOLDER else "[확인 필요]"


def _source_of(res: dict[str, Any] | None, filled: bool) -> dict[str, Any]:
    srcs = (res or {}).get("sources") or []
    if srcs:
        url = srcs[0].get("url")
        return {"type": "Wikipedia" if url and "wikipedia" in url else "웹 검색", "url": url, "title": srcs[0].get("title")}
    return {"type": "웹 검색 요약" if filled else "Wikipedia", "url": None, "title": None}


async def wiki_lookup(name: str, basis_cats: list[str]) -> tuple[dict[str, Any], list[str]]:
    """회사 이름 → 기본 정보(위키) · 겹치는 제품군. 근거 구절이 요약에 없으면 자리표시."""
    wiki = {k: _placeholder(k) for k in WIKI_KEYS}
    res: dict[str, Any] | None = None
    summary = ""
    q = aix.query_guard(f"{name} 회사 개요 본사 규모 매출 임직원 주력 사업", [])
    if q:
        try:
            res = await aix.websearch("ca.flow_wiki_web.v1", q, max_sources=4)
            summary = res.get("summary") or ""
        except ApiError as exc:
            log.info("위키 웹 검색 실패 %s: %s", name, exc.code)
    cats: list[str] = []
    filled = False
    if summary.strip() and not summary.startswith("[mock"):
        prompt = aix_dump({"요청": "웹 검색 요약에서 이 회사의 기본 정보를 뽑는다. 요약에 없는 값은 null. 값마다 근거 구절(요약 원문 그대로)을 붙인다. "
                                   "categories 는 아래 '비교 기준 제품군' 중 이 회사 제품이 겹치는 것만.",
                           "회사": name, "비교 기준 제품군": basis_cats, "웹 검색 요약": summary[:4000]})
        try:
            out = (await aix.llm("ca.flow_wiki.v1", prompt, _WikiOut, confidential=True)).model_dump()
        except aix.LLMFailed as exc:
            log.info("위키 정리 실패 %s: %s", name, exc.code)
            out = {}
        for k, src in (("hq", "hq"), ("size", "size"), ("revenue", "revenue"), ("employees", "employees"), ("industry", "industry"),
                       ("mainBusiness", "main_business"), ("b2bOffice", "b2b_office")):
            v = _grounded(out.get(src), summary)
            if v:
                wiki[k] = v
                filled = True
        cats = [c for c in out.get("categories") or [] if c in basis_cats]
    wiki["source"] = _source_of(res, filled)
    return wiki, cats


def aix_dump(obj: Any) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, indent=1)


async def add_competitor(fid: str, body: CFCompetitorAdd) -> dict[str, Any]:
    d0 = await load(fid)
    name = _norm(body.name)
    if any(_norm(c["name"]).lower() == name.lower() for c in d0.get("competitors") or []):
        raise ApiError(409, "DUPLICATE_COMPETITOR", f"‘{name}’은 이미 목록에 있어요.")
    if sum(1 for c in d0.get("competitors") or [] if _in_list(c)) >= MAX_COMPETITORS:
        raise ApiError(422, "TOO_MANY_COMPETITORS", f"경쟁사는 {MAX_COMPETITORS}곳까지예요.")
    cats0 = (d0.get("basis") or {}).get("categories") or []
    if body.lookup:
        wiki, cats = await wiki_lookup(name, cats0)
    else:
        wiki, cats = {**{k: _placeholder(k) for k in WIKI_KEYS}, "source": {"type": "직접 입력", "url": None, "title": None}}, []

    def fn(d: dict[str, Any]) -> None:
        spaces = _spaces_of(_items_in(d, cats))
        size = wiki["size"]
        d.setdefault("competitors", []).append({
            "id": _letter(d), "name": name, "by": "manual", "industry": wiki["industry"], "size": size.split(" · ")[0],
            "categories": cats, "spaces": spaces, "why": _why(cats, spaces), "wiki": wiki,
            "criteria": _criteria(d, cats, spaces), "matches": _derived_matches(d, cats), "pros": [], "cons": [], "claims": [],
            "candidateEvidence": None})
    saved = await update(fid, fn, f"경쟁사 추가 {name}", body.expected_version)
    return to_api(saved)


async def patch_competitor(fid: str, cid: str, body: CFCompetitorPatch) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        c = _find(d, cid)
        if body.name is not None and _norm(body.name):
            c["name"] = _norm(body.name)
        if body.accept and c.get("by") == "ai-pending":
            c["by"] = "ai-web"
        if body.wiki is not None:
            w = body.wiki.model_dump(exclude_none=True)
            src_url = w.pop("source_url", None)
            for k, v in w.items():
                c["wiki"][k] = _norm(v) or _placeholder(k)
            if src_url is not None:
                c["wiki"]["source"] = {"type": c["wiki"].get("source", {}).get("type") or "직접 입력", "url": src_url or None,
                                       "title": c["wiki"].get("source", {}).get("title")}
            if "industry" in w:
                c["industry"] = c["wiki"]["industry"]
            if "size" in w:
                c["size"] = c["wiki"]["size"].split(" · ")[0]
        if body.criteria is not None:
            c["criteria"] = [x.model_dump() for x in body.criteria if _norm(x.k)]
        if body.pros is not None:
            c["pros"] = [_norm(x) for x in body.pros if _norm(x)]
        if body.cons is not None:
            c["cons"] = [_norm(x) for x in body.cons if _norm(x)]
        if body.claims is not None:
            c["claims"] = [{"axis": _norm(x.axis) or "주장", "text": _norm(x.text), "supports": _norm(x.supports or "") or None}
                           for x in body.claims if _norm(x.text)]
    return to_api(await update(fid, fn, "경쟁사 고침", body.expected_version))


async def delete_competitor(fid: str, cid: str, expected: int | None = None) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        _find(d, cid)
        d["competitors"] = [x for x in d["competitors"] if x["id"] != cid]
    return to_api(await update(fid, fn, "경쟁사 뺌", expected))


# ── 비교 쌍 ─────────────────────────────────────────────

def _dss_match(d: dict[str, Any], ours: str) -> dict[str, Any] | None:
    """우리 제품 이름 → DSS 항목(정확히 · 부분). 'QM55C + MagicINFO' 처럼 묶인 이름은 첫 조각으로."""
    items = d.get("dss_items") or []
    o = _norm(ours).lower()
    for it in items:
        if it["name"].lower() == o:
            return it
    parts = [p.strip() for p in re.split(r"\s[+·]\s", o) if len(p.strip()) >= 3]
    if parts and all(any(p in it["name"].lower() for it in items) for p in parts):
        return next(it for it in items if parts[0] in it["name"].lower())
    return None


def _find_match(c: dict[str, Any], mid: str) -> dict[str, Any]:
    m = next((x for x in c.get("matches") or [] if x["id"] == mid), None)
    if m is None:
        raise not_found("비교 쌍", mid)
    return m


async def add_match(fid: str, cid: str, body: CFMatchAdd) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        c = _find(d, cid)
        it = _dss_match(d, body.ours)
        if it is None:
            raise ApiError(422, "NOT_IN_DSS", "비교 쌍의 우리 제품은 DSS 제품 · 솔루션에서 골라 주세요.", {"ours": body.ours})
        c.setdefault("matches", []).append({"id": new_id("cm"), "space": _norm(body.space or "") or (it.get("spaces") or ["전체"])[0],
                                            "ours": it["name"], "ours_ref": it.get("ref"), "theirs": _norm(body.theirs) or "[확인 필요]",
                                            "dims": _blank_dims()})
    return to_api(await update(fid, fn, "비교 쌍 추가", body.expected_version))


async def patch_match(fid: str, cid: str, mid: str, body: CFMatchPatch) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        m = _find_match(_find(d, cid), mid)
        if body.space is not None:
            m["space"] = _norm(body.space) or m["space"]
        if body.theirs is not None:
            m["theirs"] = _norm(body.theirs) or "[확인 필요]"
        for k, p in (body.dims or {}).items():
            cur = m["dims"].setdefault(k, {"verdict": "no-data", "note": "자료 없음"})
            if p.verdict is not None:
                cur["verdict"] = p.verdict
            if p.note is not None:
                cur["note"] = _norm(p.note) or ("자료 없음" if cur["verdict"] == "no-data" else "")
    return to_api(await update(fid, fn, "비교 쌍 고침", body.expected_version))


async def delete_match(fid: str, cid: str, mid: str, expected: int | None = None) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        c = _find(d, cid)
        _find_match(c, mid)
        c["matches"] = [x for x in c["matches"] if x["id"] != mid]
    return to_api(await update(fid, fn, "비교 쌍 뺌", expected))


# ── AI 경쟁사 후보군 웹 탐색 ─────────────────────────────

class _CDim(BaseModel):
    verdict: Verdict = "no-data"
    note: str = ""


class _CMatch(BaseModel):
    space: str | None = None
    ours: str = Field(description="입력 'DSS 제품 · 솔루션' 이름 그대로")
    theirs: str
    spec: _CDim = Field(default_factory=_CDim)
    price: _CDim = Field(default_factory=_CDim)
    cases: _CDim = Field(default_factory=_CDim)
    esg: _CDim = Field(default_factory=_CDim)
    brand: _CDim = Field(default_factory=_CDim)


class _CClaim(BaseModel):
    axis: str
    text: str
    supports: str | None = None


class _Cand(BaseModel):
    name: str = Field(description="요약에 나온 회사 이름 그대로")
    industry: str = Field(description="업종(짧게)")
    size: str | None = Field(None, description="규모(대기업 · 중견 · 중소) — 요약에 없으면 null")
    hq: str | None = None
    main_business: str | None = None
    b2b_office: str | None = None
    categories: list[str] = Field(default_factory=list, description="겹치는 비교 기준 제품군(입력 목록에서만)")
    spaces: list[str] = Field(default_factory=list, description="겹치는 DSS 공간(입력 목록에서만)")
    evidence_quote: str = Field(description="후보 근거 — 요약 원문 구절 그대로")
    source_name: str | None = Field(None, description="근거 출처 종류(업계 뉴스 · 회사 소개 페이지 · 조달 공고 …)")
    source_date: str | None = None
    matches: list[_CMatch] = Field(default_factory=list)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    claims: list[_CClaim] = Field(default_factory=list)


class _CandOut(BaseModel):
    candidates: list[_Cand] = Field(default_factory=list)


def _mockish(s: str | None) -> bool:
    return not s or "[mock" in s


async def suggest_candidates(fid: str) -> dict[str, Any]:
    d = await load(fid)
    basis = d.get("basis") or {}
    cats = basis.get("categories") or []
    have = {_norm(c["name"]).lower() for c in d.get("competitors") or []}
    industry = d.get("industry") or ""
    q = aix.query_guard(f"{industry} {' · '.join(cats)} B2B 공급 업체 경쟁사".strip(), [d.get("context_text") or ""])
    if not q:
        return {"flow": to_api(d), "added": 0, "mode": "none", "reason": "검색어를 만들지 못했어요 · 경쟁사를 직접 추가해 주세요."}
    try:
        res = await aix.websearch("ca.flow_candidates_web.v1", q, max_sources=6)
    except ApiError as exc:
        log.info("후보 웹 검색 실패: %s", exc.code)
        return {"flow": to_api(d), "added": 0, "mode": "none", "reason": "지금은 AI 웹 탐색을 쓸 수 없어요 · 경쟁사를 직접 추가해 주세요."}
    summary = res.get("summary") or ""
    if _mockish(summary) or not summary.strip():
        return {"flow": to_api(d), "added": 0, "mode": "none", "reason": "웹에서 경쟁사 후보를 찾지 못했어요 · 경쟁사를 직접 추가해 주세요."}
    srcs = res.get("sources") or []
    items = d.get("dss_items") or []
    prompt = aix_dump({
        "요청": "웹 검색 요약에서 우리 제안(DSS)과 제품군이 겹치는 B2B 경쟁사 후보를 최대 3곳 고른다. 요약에 이름이 나온 회사만, 이미 있는 경쟁사는 빼고. "
                "후보마다 근거 구절(요약 원문 그대로) · 겹치는 제품군과 공간 · DSS 제품과 맞서는 경쟁 제품 쌍(우리 제품 이름은 입력 그대로) · "
                "5축 판정(ours-better · similar · ours-worse · no-data, 근거 없으면 no-data)과 한 줄 메모 · 삼성 대비 장단점 · 우리가 주장할 것(축 · 문장 · 연결 요구)을 쓴다. "
                "요약에 없는 수치 · 가격은 쓰지 않는다(가격은 [견적 확인]).",
        "비교 기준 제품군": cats, "업종": industry,
        "DSS 제품 · 솔루션": [{"이름": it["name"], "제품군": it["category"], "공간": it.get("spaces") or []} for it in items],
        "이미 있는 경쟁사": sorted(have), "요구 · Storyboard": (d.get("context_text") or "")[:2000], "웹 검색 요약": summary[:5000],
    })
    try:
        out = (await aix.llm("ca.flow_candidates.v1", prompt, _CandOut, confidential=True)).model_dump()
    except aix.LLMFailed as exc:
        log.info("후보 정리 실패: %s", exc.code)
        return {"flow": to_api(d), "added": 0, "mode": "none", "reason": "지금은 AI로 후보를 정리하지 못했어요 · 경쟁사를 직접 추가해 주세요."}
    s_norm = _norm(summary)
    space_names = {s for it in items for s in it.get("spaces") or []}
    picked: list[dict[str, Any]] = []
    for cand in out.get("candidates") or []:
        name = _norm(cand.get("name") or "")
        quote = _norm(cand.get("evidence_quote") or "")
        if not name or _mockish(name) or name.lower() in have or name not in s_norm or not quote or quote not in s_norm:
            continue        # 요약에 없는 회사 · 근거 구절 = 지어낸 것
        have.add(name.lower())
        ccats = [c for c in cand.get("categories") or [] if c in cats]
        cspaces = [s for s in cand.get("spaces") or [] if s in space_names] or _spaces_of(_items_in(d, ccats))
        matches = []
        for cm in cand.get("matches") or []:
            it = _dss_match(d, cm.get("ours") or "")
            if it is None:
                continue
            dims = {}
            for k in DIM_KEYS:
                x = cm.get(k) or {}
                v = x.get("verdict") if x.get("verdict") in VERDICTS else "no-data"
                note = guard_numbers(_norm(x.get("note") or ""), summary) or ("자료 없음" if v == "no-data" else "")
                dims[k] = {"verdict": v, "note": note}
            matches.append({"id": new_id("cm"), "space": _norm(cm.get("space") or "") or (it.get("spaces") or ["전체"])[0],
                            "ours": _norm(cm.get("ours")) if _norm(cm.get("ours")).lower() != it["name"].lower() else it["name"],
                            "ours_ref": it.get("ref"), "theirs": guard_numbers(_norm(cm.get("theirs") or ""), summary) or "[확인 필요]", "dims": dims})
        if not matches:
            matches = _derived_matches(d, ccats)
        url = srcs[0].get("url") if srcs else None
        ev = {"source": _norm(cand.get("source_name") or "") or "웹 검색 요약", "date": _norm(cand.get("source_date") or "") or None,
              "quote": quote, "url": url}
        size = _norm(cand.get("size") or "") or "[확인 필요]"
        wiki = {"hq": _norm(cand.get("hq") or "") or "[확인 필요]", "size": size,
                "revenue": "[위키 값]", "employees": "[위키 값]", "industry": _norm(cand.get("industry") or "") or "[확인 필요]",
                "mainBusiness": _norm(cand.get("main_business") or "") or "[확인 필요]", "b2bOffice": _norm(cand.get("b2b_office") or "") or "[확인 필요]",
                "source": {"type": "웹 검색 요약", "url": url, "title": srcs[0].get("title") if srcs else None}}
        for k in ("hq", "industry", "mainBusiness", "b2bOffice"):
            wiki[k] = guard_numbers(wiki[k], summary)
        picked.append({"name": name, "by": "ai-pending", "industry": wiki["industry"], "size": size, "categories": ccats, "spaces": cspaces,
                       "why": _why(ccats, cspaces), "wiki": wiki, "evidence": ev, "matches": matches,
                       "pros": [guard_numbers(_norm(x), summary) for x in cand.get("pros") or [] if _norm(x)][:4],
                       "cons": [guard_numbers(_norm(x), summary) for x in cand.get("cons") or [] if _norm(x)][:4],
                       "claims": [{"axis": _norm(x.get("axis") or "") or "주장", "text": guard_numbers(_norm(x.get("text") or ""), summary),
                                   "supports": _norm(x.get("supports") or "") or None} for x in cand.get("claims") or [] if _norm(x.get("text") or "")][:4]})
        if len(picked) >= MAX_CANDIDATES:
            break
    if not picked:
        return {"flow": to_api(d), "added": 0, "mode": "web", "reason": "근거가 확인되는 새 후보가 없어요 · 경쟁사를 직접 추가해 주세요."}
    added = 0

    def fn(doc: dict[str, Any]) -> None:
        nonlocal added
        names = {_norm(c["name"]).lower() for c in doc.get("competitors") or []}
        for p in picked:
            if p["name"].lower() in names:
                continue
            ev = p.pop("evidence")
            doc.setdefault("competitors", []).append({**p, "id": _letter(doc), "criteria": _criteria(doc, p["categories"], p["spaces"], ev),
                                                      "candidateEvidence": ev})
            added += 1
    saved = await update(fid, fn, "AI 경쟁사 후보군 웹 탐색")
    return {"flow": to_api(saved), "added": added, "mode": "web", "reason": None}


# ── 저장 · flow.json ────────────────────────────────────

def stage(d: dict[str, Any]) -> dict[str, Any]:
    comps = [c for c in d.get("competitors") or [] if _in_list(c)]
    basis = d.get("basis") or {}
    out = []
    for c in comps:
        out.append({
            "id": c["id"], "name": c["name"], "by": c["by"],
            "wiki": {**{k: c["wiki"].get(k) for k in WIKI_KEYS}, "source": {"type": (c["wiki"].get("source") or {}).get("type"),
                                                                           "url": (c["wiki"].get("source") or {}).get("url")}},
            "criteria": [{"k": x["k"], "v": x["v"], "status": x.get("status", "ok")} for x in c.get("criteria") or []],
            "matches": [{"space": m["space"], "ours": m["ours"], "theirs": m["theirs"],
                         "dims": {k: {"verdict": m["dims"][k]["verdict"], "note": m["dims"][k]["note"]} for k in DIM_KEYS}}
                        for m in c.get("matches") or []],
            "pros": list(c.get("pros") or []), "cons": list(c.get("cons") or []),
            "claims": [{"axis": x["axis"], "text": x["text"], "supports": x.get("supports")} for x in c.get("claims") or []],
            "candidateEvidence": c.get("candidateEvidence"),
        })
    cnt = counts(d)
    return {"basis": {"from": basis.get("from"), "categories": basis.get("categories") or []}, "dimensions": [lab for _, lab in DIMS],
            "competitors": out, "counts": {"competitors": cnt["competitors"], "matches": cnt["matches"], "verdicts": cnt["verdicts"]}}


def _axis_rank(comps: list[dict[str, Any]], verdict: str) -> list[tuple[str, int]]:
    tally = {k: 0 for k in DIM_KEYS}
    for c in comps:
        for m in c.get("matches") or []:
            for k in DIM_KEYS:
                if m["dims"][k]["verdict"] == verdict:
                    tally[k] += 1
    lab = dict(DIMS)
    return [(lab[k], n) for k, n in sorted(tally.items(), key=lambda kv: -kv[1]) if n]


def _short(text: str, n: int) -> str:
    """요약 줄용 — n 자를 넘으면 낱말 경계에서 자르고 …(낱말 중간에서 끊지 않는다)."""
    t = _norm(text)
    if len(t) <= n:
        return t
    cut = t[:n]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp >= n // 2 else cut).rstrip(" ·—,") + "…"


def md_lines(d: dict[str, Any]) -> list[str]:
    comps = [c for c in d.get("competitors") or [] if _in_list(c)]
    cnt = counts(d)
    direct = sum(1 for c in comps if c["by"] == "manual")
    ai_n = len(comps) - direct
    lines = [f"- 경쟁사 {cnt['competitors']} (직접 {direct} · AI 웹 탐색 {ai_n}) · 비교 쌍 {cnt['matches']}"]
    better, worse = _axis_rank(comps, "ours-better"), _axis_rank(comps, "ours-worse")
    if better:
        lines.append("- 우위: " + " · ".join(f"{a} {n}" for a, n in better[:3]))
    if worse:
        lines.append("- 열위: " + " · ".join(f"{a} {n}" for a, n in worse[:3]))
    claims = [x for c in comps for x in c.get("claims") or []][:2]
    if claims:
        lines.append("- 주장: " + " · ".join(f"{x['axis']} — {_short(x['text'], 32)}" for x in claims))
    nd = cnt["verdicts"]["noData"]
    if nd:
        lines.append(f"- 자료 없음 {nd}칸 · 수치와 견적은 원문 · 사내 자료로 확인")
    return lines


def summary_md(d: dict[str, Any]) -> str:
    return "\n".join([f"## 경쟁사 · {d.get('code') or d['id']} v{d.get('ver') or 1}", *md_lines(d)])


def card(d: dict[str, Any], st: dict[str, Any]) -> dict[str, Any]:
    cnt = counts(d)
    v = cnt["verdicts"]
    groups = []
    for c in st["competitors"][:3]:
        lines = [{"t": f"{x['axis']} · {x['text']}", "note": None} for x in c["claims"][:2]]
        lines += [{"t": f"{m['ours']} ↔ {m['theirs']}", "note": "확인 필요" if "[확인 필요]" in m["theirs"] else None} for m in c["matches"][:3 - len(lines)]]
        groups.append({"h": c["name"], "sub": {"manual": "직접", "ai-web": "AI 웹 탐색"}.get(c["by"], c["by"]) + f" · 비교 쌍 {len(c['matches'])}", "lines": lines})
    return {"title": d.get("title") or "경쟁사 분석",
            "facts": [["경쟁사", str(cnt["competitors"])], ["비교 쌍", str(cnt["matches"])], ["우위 · 열위", f"{v['oursBetter']} · {v['oursWorse']}"]],
            "groups": groups, "foot": "판정은 우리 제품 기준 · 수치와 견적은 원문 · 사내 자료로 확인",
            "line": f"{d.get('code')} v{d.get('ver') or 1} · 경쟁사 {cnt['competitors']} · 비교 쌍 {cnt['matches']} · 우위 {v['oursBetter']} · 열위 {v['oursWorse']}"}


async def finish(fid: str) -> dict[str, Any]:
    d = await load(fid)
    if counts(d)["competitors"] == 0:
        raise ApiError(422, "NO_COMPETITORS", "경쟁사를 하나 이상 목록에 넣어 주세요.")

    def fn(doc: dict[str, Any]) -> None:
        doc["ver"] = int(doc.get("ver") or 0) + 1 if doc.get("saved_at") else 1
        doc["status"] = "done"
        doc["saved_at"] = now_iso()
    saved = await update(fid, fn, "저장")
    cnt = counts(saved)
    await register_item(feature="CA", item_id=fid, title=saved.get("title") or "경쟁사 분석", status="done", route=f"/competitor/flow/{fid}",
                        summary=f"경쟁사 {cnt['competitors']} · 비교 쌍 {cnt['matches']}")
    st = stage(saved)
    sync = None
    if saved.get("sb_id"):
        sync = await push_stage(saved["sb_id"], "ca", ref=saved.get("code") or fid, ver=int(saved.get("ver") or 1), res_id=fid,
                                title=saved.get("title"), value=st, md="\n".join(md_lines(saved)), card=card(saved, st))
    return {"stage": {"ref": saved.get("code") or fid, "ver": int(saved.get("ver") or 1), **st}, "summary_md": summary_md(saved),
            "flow_sync": {"md_added": sync["md_added"], "synced": sync["synced"]} if sync else None}


async def get_stage(fid: str) -> dict[str, Any]:
    d = await load(fid)
    return {"stage": {"ref": d.get("code") or fid, "ver": int(d.get("ver") or 1), **stage(d)}, "summary_md": summary_md(d), "flow_sync": None}

