"""새 MI 흐름(웹앱 ① v58, 2026-10-08 — 보드 webapp1 MI2_Loading · MI2 · MI3 · MI_Done · MI_DoneJson).

Storyboard(최소 DSS 까지)를 고르면 AI 가 먼저 Storyboard 를 읽고(CF-08 예외 — MI 만 분석 로딩이 먼저 나온다)
고객사 · 업종 · 공간 · 요구를 뽑아 시장 · 고객사 · 사용자 검색어를 만든다 → 사람이 검색어 · 조건을 고친다 →
웹 검색 → 찾은 정보를 담기/빼기 · 문장 고치기(정제) → 저장하면 Storyboard flow.json `stages.mi` 에 들어간다.

- 단계(phase): analyzing(잡 mi.flow_analyze) → search → searching(잡 mi.flow_search) → refine → done.
- 분석: `mi.flow_analyze.v1`(요구 · DSS 원문이 들어가므로 confidential=True). 모델이 없거나 답이 비면 Storyboard 값으로 만든 결정적 검색어(`mode=rule`).
- 검색: 기존 MI 와 같은 ai-tools 웹 검색(`aix.websearch`, confidential=False) · 검색어 보호(`aix.query_guard` — 요구 원문 20자 · 계획 수치 차단).
  찾은 정보(items)는 검색 도구가 돌려준 글에서만 만든다 — 출처 이름 · 날짜 · URL 은 그 글에 있는 문자열만 쓰고(없으면 '웹 검색 요약' · null),
  수치가 들어간 문장은 모두 `numberCheck`(원문에서 확인)로 표시한다. 지어내지 않는다.
- 저장: `push_stage(sb, "mi", value=§6 mi 모양)`, 코드 MI-01 …, ver = 저장 횟수, 고쳐 저장하면 prevVer.
- 같은 Storyboard 로 다시 만들면(「‹ Storyboard」 → Gate → 다시 시작) 그 Storyboard 의 저장 전 초안을 돌려준다(200 · 분석을 다시 돌리지 않음).
  복제본(분기)은 Storyboard 가 새로 생기므로 새 MI 가 된다.
- 지우기는 한 번도 저장하지 않은 초안만(status draft · ver 없음) — 돌고 있는 분석 · 검색 잡은 취소한다. 저장한 MI 는 409 SAVED_CONTENT.

저장소: DocStore("mi") 컬렉션 `mi_flows`(mif_ …). 쓰기는 낙관적 잠금 + 재시도.
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
from winmate_common.platform import register_item, unregister_item
from winmate_common.store import VersionConflict

from . import rules
from . import store as R

log = logging.getLogger("winmate.mi.flow")

COLL = "mi_flows"
GROUPS: list[tuple[str, str]] = [("market", "시장"), ("customer", "고객사"), ("user", "사용자")]
GROUP_LABEL = dict(GROUPS)
LABEL_GROUP = {v: k for k, v in GROUPS}
PERIODS = ["최근 1년", "최근 3년", "전체"]
PERIOD_MONTHS = {"최근 1년": 12, "최근 3년": 36, "전체": None}
SOURCE_TYPES = ["뉴스", "공시 · IR", "리포트", "정부 통계"]
SUMMARY_TYPE = "웹 검색 요약"
MAX_QUERIES_PER_GROUP = 6
MAX_ITEMS_PER_QUERY = 4
MAX_ITEMS_PER_GROUP = 10

Phase = Literal["analyzing", "search", "searching", "refine", "done"]
QBy = Literal["ai", "rule", "manual", "prev"]


# ── 모델(API) ───────────────────────────────────────────

class MFQuery(BaseModel):
    text: str
    on: bool = Field(True, description="false = 뺀 검색어(점선 · 취소선, 다시 넣을 수 있음)")
    by: QBy = Field("ai", description="ai = AI 분석 · rule = 규칙(모델 없이) · manual = 직접 · prev = 이전 판에서")


class MFQueries(BaseModel):
    market: list[MFQuery] = Field(default_factory=list)
    customer: list[MFQuery] = Field(default_factory=list)
    user: list[MFQuery] = Field(default_factory=list)


class MFFilters(BaseModel):
    period: Literal["최근 1년", "최근 3년", "전체"] = "최근 1년"
    sourceTypes: list[str] = Field(default_factory=lambda: ["뉴스", "공시 · IR", "리포트"], description="뉴스 · 공시 · IR · 리포트 · 정부 통계")


class MFBasis(BaseModel):
    k: str = Field(description="고객사 · 업종 · 공간 · 요구")
    v: str


class MFStep(BaseModel):
    key: str
    label: str
    state: Literal["wait", "run", "done", "error"] = "wait"
    note: str = ""


class MFProgress(BaseModel):
    kind: Literal["analyze", "search"]
    job_id: str | None = None
    steps: list[MFStep] = Field(default_factory=list)
    done: int = 0
    total: int = 0
    error: str | None = None


class MFSource(BaseModel):
    type: str = Field(description="뉴스 · 공시 · IR · 리포트 · 정부 통계 · 웹 검색 요약(출처를 글에서 못 읽음)")
    name: str = Field(description="출처 이름 — 검색 결과 글에 있는 문자열만(없으면 '웹 검색 요약')")
    date: str | None = Field(None, description="YYYY-MM(글에 있을 때만)")
    url: str | None = Field(None, description="검색 도구가 돌려준 URL 만(요약형 검색이면 null)")


class MFNumberCheck(BaseModel):
    values: list[str] = Field(default_factory=list, description="원문에서 확인해야 하는 수치 표현")
    note: str = "수치는 원문에서 확인해야 해요"


class MFItem(BaseModel):
    id: str
    group: Literal["시장", "고객사", "사용자"]
    summary: str = Field(description="원문을 줄여 쓴 한 문장(사람이 고칠 수 있음)")
    summary_orig: str = Field(description="검색 결과에서 뽑은 그대로의 문장")
    source: MFSource
    kept: bool = True
    addedIn: str = Field(description="처음 찾은 판(v1 · v2 …)")
    numberCheck: MFNumberCheck | None = None
    result_id: str | None = Field(None, description="이 문장을 뽑은 검색 결과(results[].id) — '원문' 보기")
    query: str | None = None
    edited: bool = False


class MFResultSource(BaseModel):
    url: str
    title: str = ""
    snippet: str | None = None


class MFResult(BaseModel):
    id: str
    group: str
    query: str = Field(description="실제로 보낸 검색어(검색어 보호를 거친 것)")
    summary: str = ""
    sources: list[MFResultSource] = Field(default_factory=list)
    mode: Literal["sources", "summary_only"] = "summary_only"
    error: str | None = None
    found: int = 0


class MFCounts(BaseModel):
    found: int
    kept: int
    numberCheck: int
    queries: int
    by_group: dict[str, list[int]] = Field(default_factory=dict, description="{시장: [담음, 찾음]} …")


class MFDoc(BaseModel):
    id: str
    code: str | None = Field(None, description="화면 · flow.json 에 쓰는 짧은 번호(MI-01 …)")
    title: str
    sb_id: str
    status: Literal["draft", "done"] = "draft"
    phase: Phase = "analyzing"
    ver: int | None = Field(None, description="저장(완료) 판 — flow.json stages.mi.ver")
    editing: bool = Field(False, description="저장한 MI 를 고치는 중(저장하면 ver+1 · prevVer)")
    keep_previous: bool = Field(True, description="고칠 때: 담은 정보 유지 · 새로 찾은 것만 더하기(false = 처음부터 다시)")
    saved_kept: int = Field(0, description="마지막 저장 때 담은 정보 수")
    analysis_mode: Literal["llm", "rule"] | None = None
    basis: list[MFBasis] = Field(default_factory=list, description="Storyboard 에서 읽은 것(고객사 · 업종 · 공간 · 요구)")
    queries: MFQueries = Field(default_factory=MFQueries)
    filters: MFFilters = Field(default_factory=MFFilters)
    results: list[MFResult] = Field(default_factory=list)
    items: list[MFItem] = Field(default_factory=list)
    counts: MFCounts
    progress: MFProgress | None = None
    warnings: list[str] = Field(default_factory=list)
    version: int
    created_at: str
    updated_at: str


class MFListItem(BaseModel):
    id: str
    code: str | None = None
    title: str
    sb_id: str
    status: str
    phase: str
    ver: int | None = None
    counts: MFCounts
    updated_at: str


class MFList(BaseModel):
    items: list[MFListItem]
    next_cursor: str | None = None


class MFCreate(BaseModel):
    sb_id: str = Field(min_length=1, description="사전 작업 Storyboard(최소 DSS 까지)")
    title: str | None = Field(None, max_length=120)


class MFPatch(BaseModel):
    title: str | None = Field(None, max_length=120)
    queries: MFQueries | None = None
    filters: MFFilters | None = None
    keep_previous: bool | None = None
    phase: Literal["search", "refine"] | None = Field(None, description="검색어 고치기(refine → search) · 정제로 돌아가기")
    expected_version: int | None = Field(None, description="다르면 409 CONFLICT")


class MFItemPatch(BaseModel):
    kept: bool | None = None
    summary: str | None = Field(None, max_length=200, description="문장 고치기(빈 문자열이면 원래 문장으로)")
    expected_version: int | None = None


class MFFlowSync(BaseModel):
    md_added: str = Field(description="Storyboard 요약본에 더해진 부분")
    synced: list[str] = Field(default_factory=list, description="같은 MI 가 연결돼 함께 바뀐 다른 Storyboard")


class MFStageOut(BaseModel):
    stage: dict[str, Any] = Field(description="Storyboard flow.json 의 stages.mi")
    summary_md: str
    flow_sync: MFFlowSync | None = Field(None, description="Storyboard 허브에 반영된 결과(허브가 안 되면 null)")


# ── 저장소 ──────────────────────────────────────────────

def _st():
    return R.store()


def _get(fid: str) -> dict[str, Any]:
    d = _st().get(COLL, fid)
    if not d:
        raise not_found("MI", fid)
    return d


async def load(fid: str) -> dict[str, Any]:
    return await asyncio.to_thread(_get, fid)


async def update(fid: str, fn: Callable[[dict[str, Any]], None], note: str | None = None, expected: int | None = None) -> dict[str, Any]:
    def _do() -> dict[str, Any]:
        for _ in range(6):
            cur = _get(fid)
            if expected is not None and cur["version"] != expected:
                raise ApiError(409, "CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러온 뒤 다시 해 주세요.", {"version": cur["version"]})
            work = copy.deepcopy(cur)
            fn(work)
            try:
                return _st().put(COLL, fid, work, expected_version=cur["version"], note=note, keep_history=False)
            except VersionConflict:
                if expected is not None:
                    raise ApiError(409, "CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러온 뒤 다시 해 주세요.") from None
                continue
        raise ApiError(409, "CONFLICT", "다른 곳에서 동시에 고쳐 저장하지 못했어요. 다시 시도해 주세요.")
    return await asyncio.to_thread(_do)


def target_ver(d: dict[str, Any]) -> int:
    """이번에 저장하면 될 판."""
    return int(d.get("ver") or 0) + 1


def active_queries(d: dict[str, Any]) -> dict[str, list[str]]:
    q = d.get("queries") or {}
    return {g: [x["text"] for x in q.get(g) or [] if x.get("on", True) and (x.get("text") or "").strip()] for g, _ in GROUPS}


def counts(d: dict[str, Any]) -> dict[str, Any]:
    items = d.get("items") or []
    kept = [x for x in items if x.get("kept")]
    by = {label: [sum(1 for x in kept if x["group"] == label), sum(1 for x in items if x["group"] == label)] for _, label in GROUPS}
    return {"found": len(items), "kept": len(kept), "numberCheck": sum(1 for x in kept if x.get("numberCheck")),
            "queries": sum(len(v) for v in active_queries(d).values()), "by_group": by}


def to_api(d: dict[str, Any]) -> dict[str, Any]:
    return {**d, "counts": counts(d)}


# ── 텍스트 도우미(검색 결과 → 찾은 정보) ───────────────────

URL_RE = re.compile(r"https?://[^\s\)\]\}\"'<>，。、]+")
_DATE_RE = re.compile(r"(20\d{2})\s*(?:년\s*(\d{1,2})\s*월|[.\-/](\d{1,2})(?!\d))")
# '부동산 리서치 2026-08 리포트에 따르면 …' · '경제지 보도에 따르면 …' — 글에 있는 출처 이름만 읽는다
_ATTR_RE = re.compile(
    r"^(?P<name>[^,.;:()\[\]]{2,24}?)\s*(?:의\s*)?(?:\(?(?P<date>20\d{2}\s*(?:년\s*\d{1,2}\s*월|[.\-/]\d{1,2}))\)?\s*)?"
    r"(?P<kind>리포트|보고서|자료|보도|발표|조사|공시|통계|분석|기사)?\s*에\s*따르면[,\s]*")
_NUM_RE = re.compile(r"\[00\]|\d[\d,]*(?:\.\d+)?\s*(?:%|퍼센트|%p|배|조|억|만|천|원|명|곳|개|건|년|개월|㎡|평|층|대|실|위|가구|호|분|시간)?")
_YEAR_RE = re.compile(r"^(?:19|20)\d{2}\s*년?$")
TYPE_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("공시 · IR", ("공시", "IR", "사업보고서", "지속가능경영", "ESG 보고서", "감사보고서", "dart", "investor", "/ir")),
    ("정부 통계", ("통계", "국토교통", "정부", "부처", "산업통상", "환경부", "통계청", ".go.kr", "공공기관", "지자체", "시청")),
    ("뉴스", ("보도", "기사", "경제지", "일보", "신문", "매체", "뉴스", "news", "article", "press", "방송")),
    ("리포트", ("리포트", "보고서", "리서치", "컨설팅", "조사", "분석", "연구", "report", ".pdf")),
]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def norm_key(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "", (text or "").lower())


def ym(text: str | None) -> str | None:
    """글 속 연월 → YYYY-MM(가장 앞의 것)."""
    m = _DATE_RE.search(text or "")
    if not m:
        return None
    y, mo = int(m.group(1)), int(m.group(2) or m.group(3) or 0)
    return f"{y:04d}-{mo:02d}" if 1 <= mo <= 12 else None


def classify(*texts: str | None) -> str | None:
    blob = " ".join(t for t in texts if t)
    low = blob.lower()
    for label, keys in TYPE_RULES:
        if any((k.lower() in low) if k.isascii() else (k in blob) for k in keys):
            return label
    return None


def numbers_in(text: str, *, skip: str | None = None) -> list[str]:
    out: list[str] = []
    for m in _NUM_RE.finditer(text or ""):
        tok = m.group(0).strip()
        if not tok or (skip and tok in skip):
            continue
        if tok != "[00]":
            if _YEAR_RE.match(tok):
                continue
            if re.fullmatch(r"\d", tok):        # 숫자 한 자리(단위 없음)는 수치로 보지 않는다(예: 'AI 2.0' 아님)
                continue
            if re.fullmatch(r"\d+", tok) and len(tok) < 2:
                continue
        if tok not in out:
            out.append(tok)
    return out


def _date_spans(text: str) -> str:
    return " ".join(m.group(0) for m in _DATE_RE.finditer(text or ""))


def number_check(text: str) -> dict[str, Any] | None:
    vals = [v for v in numbers_in(text) if v not in _date_spans(text) and not re.fullmatch(r"\d{1,2}", v)]
    return {"values": vals[:6], "note": "수치는 원문에서 확인해야 해요"} if vals else None


def split_sentences(summary: str) -> list[str]:
    text = URL_RE.sub("", summary or "")
    parts: list[str] = []
    for line in re.split(r"\n+", text):
        line = re.sub(r"^\s*(?:[-*•·]|\d+[.)])\s*", "", line).strip()
        if not line:
            continue
        parts += [p.strip() for p in re.split(r"(?<=[.!?。])\s+", line) if p.strip()]
    return [p for p in parts if len(p) >= 12]


def item_from_sentence(sentence: str, *, group: str, query: str, result_id: str, ver: int, urls: list[str] | None = None) -> dict[str, Any]:
    s = _clean(sentence)
    name, date, typ, body = SUMMARY_TYPE, None, SUMMARY_TYPE, s
    m = _ATTR_RE.match(s)
    if m and len(s) - m.end() >= 8:
        cand = m.group("name").strip()
        if not re.search(r"\d", cand) or classify(cand):
            name = cand
            date = ym(m.group("date") or "")
            typ = classify(cand, m.group("kind")) or SUMMARY_TYPE
            body = s[m.end():].strip()
    if date is None:
        date = ym(s)
    body = body[:1].upper() + body[1:] if body else s
    url = (urls or [None])[0] if urls else None
    return {"id": new_id("mfi"), "group": GROUP_LABEL.get(group, group), "summary": body, "summary_orig": body,
            "source": {"type": typ, "name": name, "date": date, "url": url}, "kept": True, "addedIn": f"v{ver}",
            "numberCheck": number_check(body), "result_id": result_id, "query": query, "edited": False}


def host_of(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url or "")
    return (m.group(1) if m else "").removeprefix("www.")


def items_from_result(res: dict[str, Any], *, group: str, ver: int) -> list[dict[str, Any]]:
    """검색 결과 하나 → 찾은 정보. 출처 목록이 있으면 출처마다, 없으면(요약형) 요약 문장마다."""
    out: list[dict[str, Any]] = []
    if res.get("error"):
        return out
    srcs = [s for s in res.get("sources") or [] if s.get("url")]
    if res.get("mode") == "sources" and srcs:
        for s in srcs[:MAX_ITEMS_PER_QUERY]:
            text = _clean((s.get("snippet") or "").split("\n")[0]) or _clean(s.get("title") or "")
            if len(text) < 8:
                continue
            first = split_sentences(text)[:1] or [text]
            body = first[0][:160]
            host = host_of(s["url"])
            out.append({"id": new_id("mfi"), "group": GROUP_LABEL.get(group, group), "summary": body, "summary_orig": body,
                        "source": {"type": classify(s.get("title"), s["url"], host) or SUMMARY_TYPE, "name": host or SUMMARY_TYPE,
                                   "date": ym(s.get("title")) or ym(s.get("snippet")), "url": s["url"]},
                        "kept": True, "addedIn": f"v{ver}", "numberCheck": number_check(body), "result_id": res["id"], "query": res["query"], "edited": False})
        if out:
            return out
    for sent in split_sentences(res.get("summary") or "")[:MAX_ITEMS_PER_QUERY]:
        urls = URL_RE.findall(sent)
        out.append(item_from_sentence(sent, group=group, query=res["query"], result_id=res["id"], ver=ver, urls=urls))
    return out


def passes_filters(item: dict[str, Any], filters: dict[str, Any]) -> bool:
    typ = (item.get("source") or {}).get("type")
    if typ in SOURCE_TYPES and typ not in (filters.get("sourceTypes") or SOURCE_TYPES):
        return False
    months = PERIOD_MONTHS.get(filters.get("period") or "전체")
    date = (item.get("source") or {}).get("date")
    if months and date:
        m = rules.months_between(f"{date}-01")
        if m is not None and m > months:
            return False
    return True


# ── Storyboard 읽기 · 분석 ──────────────────────────────

def flow_snapshot(flow: dict[str, Any]) -> dict[str, Any]:
    st = flow.get("stages") or {}
    rq, dss = st.get("rq") or {}, st.get("dss") or {}
    return {"id": flow.get("id"), "name": flow.get("name"), "customer": rq.get("customer") or flow.get("customer"),
            "rq": {"title": rq.get("title"), "target": rq.get("target"), "goals": rq.get("goals") or [],
                   "requirements": [r.get("text") for r in rq.get("requirements") or [] if isinstance(r, dict) and r.get("text")][:30]},
            "dss": {"industry": (dss.get("industry") or {}).get("value") if isinstance(dss.get("industry"), dict) else dss.get("industry"),
                    "spaces": [{"name": s.get("name"), "products": [p.get("name") if isinstance(p, dict) else p for p in s.get("products") or []]}
                               for s in dss.get("spaces") or [] if isinstance(s, dict) and s.get("name")],
                    "solutions": [s.get("name") if isinstance(s, dict) else s for s in dss.get("solutions") or []]},
            "summary_md": (flow.get("summary_md") or "")[:3000], "key_message": ((flow.get("key_message") or {}) or {}).get("text")}


def sensitive_texts(snap: dict[str, Any]) -> list[str]:
    """검색어 보호 — 요구 원문 · 요약본(고객 문장 20자 · 계획 수치는 웹으로 나가지 않는다)."""
    rq = snap.get("rq") or {}
    return [t for t in [*(rq.get("requirements") or []), *(rq.get("goals") or []), rq.get("target") or "", snap.get("summary_md") or ""] if t]


def industry_short(industry: str | None) -> str:
    s = (industry or "").split("·")[0].strip()
    return s or "B2B"


def need_labels(snap: dict[str, Any], n: int = 2) -> list[str]:
    rq = snap.get("rq") or {}
    out = [g.strip() for g in rq.get("goals") or [] if isinstance(g, str) and 2 <= len(g.strip()) <= 16][:n]
    return out


_PLAN_NUM_RE = re.compile(r"\s*\d[\d,.]*\s*(?:%p|%|퍼센트|배|억|만|원|명|대|개|곳)?")


def need_query(ind: str, need: str) -> str | None:
    """요구 이름 → 시장 검색어 틀. 고객 계획 수치(예: 20%)는 빼고(검색어 보호와 같은 원칙), 업종 낱말이 겹치면 한 번만."""
    n = re.sub(r"\s+", " ", _PLAN_NUM_RE.sub(" ", need or "")).strip()
    if len(n) < 2:
        return None
    if ind and ind != "B2B":
        n = re.sub(rf"\s*{re.escape(ind)}\s*$", "", n).strip() or n
    return n if ind in n else f"{ind} {n}"


def rule_analysis(snap: dict[str, Any]) -> dict[str, Any]:
    """모델 없이 — Storyboard 값으로만 고객사 · 업종 · 공간 · 요구와 검색어를 만든다(지어내는 사실 없음 · 검색어는 틀)."""
    cust = (snap.get("customer") or "").strip() or None
    ind_full = (snap.get("dss") or {}).get("industry") or None
    ind = industry_short(ind_full)
    spaces = [s["name"] for s in (snap.get("dss") or {}).get("spaces") or []]
    needs = need_labels(snap)
    market = [f"{ind} 시장 동향", f"{ind} 디지털 전환 사례"] + [q for q in (need_query(ind, n) for n in needs[:2]) if q]
    customer = [f"{cust} 사업 현황", f"{cust} 투자 계획", f"{cust} ESG"] if cust else []
    user = [f"{ind} {sp} 이용자 경험" for sp in spaces[:3]] or [f"{ind} 이용자 불편"]
    return {"customer": cust, "industry": ind_full, "spaces": spaces, "needs": needs,
            "queries": {"market": market, "customer": customer, "user": user}, "mode": "rule"}


def _in_text(v: str, blob: str) -> bool:
    return bool(v) and norm_key(v) in norm_key(blob)


def validate_analysis(out: dict[str, Any] | None, snap: dict[str, Any]) -> dict[str, Any] | None:
    """모델 답 검사 — 고객사 · 업종 · 공간은 Storyboard 에 있는 값만, 검색어는 짧은 글만. 쓸 게 없으면 None(규칙으로)."""
    if not out:
        return None
    blob = " ".join([snap.get("customer") or "", snap.get("name") or "", (snap.get("dss") or {}).get("industry") or "", snap.get("summary_md") or "",
                     " ".join((snap.get("rq") or {}).get("requirements") or []), " ".join((snap.get("rq") or {}).get("goals") or [])])
    base = rule_analysis(snap)
    mock = lambda s: not s or "[mock" in s  # noqa: E731
    qs: dict[str, list[str]] = {}
    for g, _ in GROUPS:
        vals = []
        for q in (out.get("queries") or {}).get(g) or []:
            q = _clean(str(q))
            if q and not mock(q) and len(q) <= 40 and q not in vals:
                vals.append(q)
        qs[g] = vals[:MAX_QUERIES_PER_GROUP]
    if sum(len(v) for v in qs.values()) == 0:
        return None
    cust = out.get("customer") if isinstance(out.get("customer"), str) and _in_text(out["customer"], blob) else base["customer"]
    ind = out.get("industry") if isinstance(out.get("industry"), str) and _in_text(out["industry"], blob) else base["industry"]
    dss_spaces = base["spaces"]
    spaces = [s for s in out.get("spaces") or [] if isinstance(s, str) and s in dss_spaces] or dss_spaces
    needs = [n for n in out.get("needs") or [] if isinstance(n, str) and not mock(n) and 2 <= len(n) <= 20][:3] or base["needs"]
    return {"customer": cust, "industry": ind, "spaces": spaces, "needs": needs, "queries": qs, "mode": "llm"}


def basis_of(an: dict[str, Any]) -> list[dict[str, str]]:
    sp = an.get("spaces") or []
    return [{"k": "고객사", "v": an.get("customer") or "[확인 필요]"}, {"k": "업종", "v": an.get("industry") or "[확인 필요]"},
            {"k": "공간", "v": (f"{sp[0]} 외 {len(sp) - 1}" if len(sp) > 1 else (sp[0] if sp else "[확인 필요]"))},
            {"k": "요구", "v": " · ".join(an.get("needs") or []) or "[확인 필요]"}]


def merge_queries(new: dict[str, list[str]], prev: dict[str, Any] | None, by: str) -> dict[str, list[dict[str, Any]]]:
    """고칠 때는 이전 판 검색어(켠 것 · 끈 것 그대로)를 먼저 두고, 새 검색어 중 없는 것만 뒤에."""
    out: dict[str, list[dict[str, Any]]] = {}
    for g, _ in GROUPS:
        rows = [dict(x, by=x.get("by") or "prev") for x in ((prev or {}).get(g) or [])]
        have = {norm_key(x["text"]) for x in rows}
        for q in new.get(g) or []:
            if norm_key(q) not in have and len(rows) < MAX_QUERIES_PER_GROUP:
                rows.append({"text": q, "on": True, "by": by})
                have.add(norm_key(q))
        out[g] = rows
    return out


# ── 작업 ────────────────────────────────────────────────

ANALYZE_STEPS = [("read", "Storyboard {sb} 읽기"), ("extract", "고객사 · 업종 · 공간 · 요구 뽑기"), ("queries", "시장 · 고객사 · 사용자 검색어 만들기")]


def analyze_progress(sb: str, job_id: str | None) -> dict[str, Any]:
    return {"kind": "analyze", "job_id": job_id, "steps": [{"key": k, "label": t.format(sb=sb), "state": "run" if i == 0 else "wait", "note": ""}
                                                         for i, (k, t) in enumerate(ANALYZE_STEPS)], "done": 0, "total": len(ANALYZE_STEPS), "error": None}


async def _enqueue(kind: str, d: dict[str, Any]) -> str:
    from winmate_common.jobs import jobs

    job = await jobs().enqueue("mi", kind, {"flow_id": d["id"]}, title=d.get("title") or "Market Intelligence", ref=d["id"])
    return job.id


async def _job_active(job_id: str | None) -> bool:
    if not job_id:
        return False
    from winmate_common.jobs import TERMINAL, jobs

    j = await jobs().get(job_id)
    return bool(j and j.status not in TERMINAL)


def is_saved(d: dict[str, Any]) -> bool:
    """한 번이라도 저장(:finish)했는지 — 저장하면 Storyboard 에 연결된다(고치는 중이어도 저장한 것)."""
    return d.get("status") == "done" or d.get("ver") is not None or bool(d.get("saved_at"))


def _draft_for(sb_id: str) -> dict[str, Any] | None:
    """이 Storyboard 의 저장 전 초안(가장 최근에 고친 것)."""
    items, _ = _st().list(COLL, where={"sb_id": sb_id, "status": "draft"}, limit=20)
    return next((d for d in items if not is_saved(d)), None)


_creating: dict[tuple[int, str], asyncio.Lock] = {}


def _sb_lock(sb_id: str) -> asyncio.Lock:
    """같은 Storyboard 로 동시에 만들기(두 번 누름 · 탭 두 개)가 초안을 둘 만들지 않게."""
    return _creating.setdefault((id(asyncio.get_running_loop()), sb_id), asyncio.Lock())


async def _next_code() -> str:
    """MI-NN — 이 서비스 번호 · 허브 ref 중 가장 큰 것 다음(초안을 지워도 번호가 겹치지 않게. 같은 ref = 같은 콘텐츠로 동기화된다)."""
    top = 0
    items, _ = await asyncio.to_thread(_st().list, COLL, limit=1000)
    refs = [x.get("code") or "" for x in items]
    try:
        hub = await ServiceClient("storyboard", timeout=10).get("/v1/flows/contents/mi")
        refs += [x.get("ref") or "" for x in (hub or {}).get("items") or []]
    except Exception as exc:  # noqa: BLE001
        log.info("허브 MI 목록을 읽지 못함(번호는 로컬만): %s", exc)
    for r in refs:
        m = re.fullmatch(r"MI-(\d+)", r)
        if m:
            top = max(top, int(m.group(1)))
    return f"MI-{top + 1:02d}"


async def create(body: MFCreate) -> tuple[dict[str, Any], bool]:
    """(문서, 새로 만들었는지). 이 Storyboard 에 저장 전 초안이 있으면 그것을 돌려준다(분석을 다시 돌리지 않는다)."""
    async with _sb_lock(body.sb_id):
        draft = await asyncio.to_thread(_draft_for, body.sb_id)
        if draft:
            return to_api(draft), False
        flow = await get_flow(body.sb_id)
        if flow is None:
            raise ApiError(404, "STORYBOARD_NOT_FOUND", f"Storyboard를 찾을 수 없어요: {body.sb_id}")
        if not (flow.get("stages") or {}).get("dss"):
            raise ApiError(422, "PREREQUISITE_MISSING", "DSS까지 된 Storyboard에서 시작할 수 있어요.", {"need": "dss"})
        snap = flow_snapshot(flow)
        title = (body.title or "").strip() or f"{flow.get('name') or body.sb_id} 시장 분석"
        fid = new_id("mif")
        doc = {"code": await _next_code(), "title": title, "sb_id": body.sb_id, "status": "draft", "phase": "analyzing", "ver": None, "editing": False,
               "keep_previous": True, "saved_kept": 0, "analysis_mode": None, "basis": [], "queries": {"market": [], "customer": [], "user": []},
               "filters": MFFilters().model_dump(), "results": [], "items": [], "saved_items": [], "saved_queries": None, "snapshot": snap,
               "progress": analyze_progress(body.sb_id, None), "warnings": []}
        await asyncio.to_thread(_st().put, COLL, fid, doc, note="만듦", keep_history=False)
    job_id = await _enqueue("mi.flow_analyze", {"id": fid, "title": title})

    def fn(d: dict[str, Any]) -> None:
        d["progress"]["job_id"] = job_id
    saved = await update(fid, fn)
    await register_item(feature="MI", item_id=fid, title=title, status="draft", route=f"/mi/flow/{fid}", summary="Storyboard 분석 · 시장 · 고객사 · 사용자 검색")
    return to_api(saved), True


SAVED_MSG = "저장한 콘텐츠는 Storyboard에 연결돼 있어 지울 수 없어요"


def _delete_sync(fid: str, expected: int | None) -> dict[str, Any]:
    cur = _get(fid)
    if expected is not None and cur["version"] != expected:
        raise ApiError(409, "CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러온 뒤 다시 해 주세요.", {"version": cur["version"]})
    if is_saved(cur):
        raise ApiError(409, "SAVED_CONTENT", SAVED_MSG, {"code": cur.get("code"), "ver": cur.get("ver"), "sb_id": cur.get("sb_id")})
    try:   # 확인 → 지우기 사이에 저장이 끼면 지우지 않는다(DocStore 판 확인, 같은 트랜잭션)
        _st().delete(COLL, fid, expected_version=cur["version"])
    except VersionConflict as exc:
        raise ApiError(409, "VERSION_CONFLICT", "방금 다른 곳에서 저장했어요. 새로 불러와 주세요.", {}) from exc
    return cur


async def delete(fid: str, expected: int | None = None) -> None:
    """저장 전 초안 지우기(소프트 삭제 + 작업물 색인 지우기). 돌고 있는 분석 · 검색 잡은 취소. 저장한 MI 는 409 SAVED_CONTENT, 없으면 404."""
    cur = await asyncio.to_thread(_delete_sync, fid, expected)
    job_id = (cur.get("progress") or {}).get("job_id")
    if cur.get("phase") in ("analyzing", "searching") and job_id:
        from winmate_common.jobs import jobs

        try:
            if await _job_active(job_id):
                await jobs().cancel(job_id)
        except Exception as exc:  # noqa: BLE001 — 잡 취소 실패가 지우기를 막지 않는다
            log.info("MI 흐름 잡 취소 실패 %s: %s", job_id, exc)
    await unregister_item(fid)


def gone(fid: str) -> bool:
    """지운(또는 없는) 초안인지 — 잡이 도는 사이 지워졌으면 되살리지 않고 끝낸다."""
    return _st().get(COLL, fid) is None


async def list_flows(limit: int, cursor: str | None) -> dict[str, Any]:
    items, nxt = await asyncio.to_thread(_st().list, COLL, limit=limit, cursor=cursor)
    return {"items": [{"id": d["id"], "code": d.get("code"), "title": d.get("title") or "", "sb_id": d.get("sb_id") or "", "status": d.get("status", "draft"),
                       "phase": d.get("phase", "analyzing"), "ver": d.get("ver"), "counts": counts(d), "updated_at": d["updated_at"]} for d in items],
            "next_cursor": nxt}


async def analyze(fid: str) -> dict[str, Any]:
    """Storyboard 분석을 (다시) 시작한다 — 저장한 MI 를 고칠 때(Gate 「수정」) · 분석이 실패했을 때."""
    d = await load(fid)
    if d.get("phase") in ("analyzing", "searching") and await _job_active((d.get("progress") or {}).get("job_id")):
        return to_api(d)
    flow = await get_flow(d["sb_id"])
    if flow is not None and not (flow.get("stages") or {}).get("dss"):
        raise ApiError(422, "PREREQUISITE_MISSING", "DSS까지 된 Storyboard에서 시작할 수 있어요.", {"need": "dss"})

    def fn(doc: dict[str, Any]) -> None:
        if flow is not None:
            doc["snapshot"] = flow_snapshot(flow)
        if doc.get("status") == "done":
            doc["editing"] = True
        doc["phase"] = "analyzing"
        doc["progress"] = analyze_progress(doc["sb_id"], None)
    await update(fid, fn, "분석 시작")
    job_id = await _enqueue("mi.flow_analyze", d)

    def fn2(doc: dict[str, Any]) -> None:
        doc["progress"]["job_id"] = job_id
    return to_api(await update(fid, fn2))


async def patch(fid: str, body: MFPatch) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        if d.get("phase") in ("analyzing", "searching") and body.phase is None and (body.queries or body.filters):
            raise ApiError(409, "BUSY", "AI가 아직 일하고 있어요. 끝나면 고칠 수 있어요.")
        if body.title is not None and body.title.strip():
            d["title"] = body.title.strip()
        if body.queries is not None:
            qs = body.queries.model_dump()
            for g, label in GROUPS:
                rows, seen = [], set()
                for x in qs[g]:
                    t = _clean(x["text"])[:40]
                    if t and norm_key(t) not in seen:
                        seen.add(norm_key(t))
                        rows.append({"text": t, "on": bool(x.get("on", True)), "by": x.get("by") or "manual"})
                if len(rows) > MAX_QUERIES_PER_GROUP + 4:
                    raise ApiError(422, "TOO_MANY_QUERIES", f"{label} 검색어는 {MAX_QUERIES_PER_GROUP + 4}개까지예요.")
                qs[g] = rows
            d["queries"] = qs
        if body.filters is not None:
            f = body.filters.model_dump()
            f["sourceTypes"] = [t for t in SOURCE_TYPES if t in f.get("sourceTypes") or []]
            d["filters"] = f
        if body.keep_previous is not None:
            d["keep_previous"] = bool(body.keep_previous)
        if body.phase == "search" and d.get("phase") in ("refine", "search", "done"):
            d["phase"] = "search"
        if body.phase == "refine" and d.get("items"):
            d["phase"] = "refine"
    return to_api(await update(fid, fn, "고침", expected=body.expected_version))


async def start_search(fid: str) -> dict[str, Any]:
    d = await load(fid)
    if d.get("phase") == "searching" and await _job_active((d.get("progress") or {}).get("job_id")):
        return to_api(d)
    if d.get("phase") == "analyzing":
        raise ApiError(409, "BUSY", "Storyboard 분석이 끝나야 검색할 수 있어요.")
    aq = active_queries(d)
    if not sum(len(v) for v in aq.values()):
        raise ApiError(422, "NO_QUERIES", "검색어를 하나 이상 넣어 주세요.")
    steps = [{"key": g, "label": f"{label} 검색어 {len(aq[g])}개", "state": "wait", "note": ""} for g, label in GROUPS if aq[g]]
    steps.append({"key": "organize", "label": "찾은 정보 정리", "state": "wait", "note": ""})
    if steps:
        steps[0]["state"] = "run"

    def fn(doc: dict[str, Any]) -> None:
        doc["phase"] = "searching"
        doc["progress"] = {"kind": "search", "job_id": None, "steps": steps, "done": 0, "total": len(steps), "error": None}
    await update(fid, fn, "검색 시작")
    job_id = await _enqueue("mi.flow_search", d)

    def fn2(doc: dict[str, Any]) -> None:
        doc["progress"]["job_id"] = job_id
    return to_api(await update(fid, fn2))


async def patch_item(fid: str, item_id: str, body: MFItemPatch) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        it = next((x for x in d.get("items") or [] if x["id"] == item_id), None)
        if it is None:
            raise not_found("찾은 정보", item_id)
        if body.kept is not None:
            it["kept"] = bool(body.kept)
        if body.summary is not None:
            s = _clean(body.summary)
            it["summary"] = s or it["summary_orig"]
            it["edited"] = bool(s) and s != it["summary_orig"]
            it["numberCheck"] = number_check(it["summary"]) or (it.get("numberCheck") if not it["edited"] else None)
    return to_api(await update(fid, fn, "정제", expected=body.expected_version))


# ── 저장 · flow.json ────────────────────────────────────

def stage(d: dict[str, Any], prev_ver: int | None) -> dict[str, Any]:
    """flow.json stages.mi(§6) — 담은 것만 items 에(점선 · 뺀 것은 안 들어감)."""
    kept = [x for x in d.get("items") or [] if x.get("kept")]
    c = counts(d)
    return {"prevVer": prev_ver, "queries": active_queries(d),
            "filters": {"period": (d.get("filters") or {}).get("period") or "최근 1년", "sourceTypes": list((d.get("filters") or {}).get("sourceTypes") or [])},
            "counts": {"found": c["found"], "kept": c["kept"], "numberCheck": c["numberCheck"]},
            "items": [{"id": x["id"], "group": x["group"], "summary": x["summary"],
                       "source": {"type": x["source"].get("type"), "name": x["source"].get("name"), "date": x["source"].get("date"), "url": x["source"].get("url")},
                       "kept": True, "addedIn": x.get("addedIn"), "numberCheck": x.get("numberCheck")} for x in kept]}


def summary_md(d: dict[str, Any], ver: int, prev_kept: int | None) -> str:
    c = counts(d)
    g = c["by_group"]
    parts = " · ".join(f"{label} {g[label][0]}" for _, label in GROUPS)
    delta = c["kept"] - prev_kept if prev_kept is not None else None
    lines = [f"## Market Intelligence · {d.get('code') or d['id']} v{ver}",
             f"- {parts}" + (f" ({'+' if delta >= 0 else ''}{delta})" if delta else ""),
             f"- 출처 {c['kept']} · 확인 필요 수치 {c['numberCheck']}"]
    return "\n".join(lines)     # 보드 MI_Done: 머리 + 그룹 수 줄 + 출처 · 확인 필요 수치 줄


def card(d: dict[str, Any], ver: int) -> dict[str, Any]:
    c = counts(d)
    kept = [x for x in d.get("items") or [] if x.get("kept")]
    groups = []
    for _, label in GROUPS:
        rows = [x for x in kept if x["group"] == label]
        if not rows:
            continue
        groups.append({"h": label, "sub": f"{len(rows)}개",
                       "lines": [{"t": x["summary"], "note": "확인 필요" if x.get("numberCheck") else x["source"].get("type")} for x in rows[:3]]})
    parts = " · ".join(f"{label} {c['by_group'][label][0]}" for _, label in GROUPS)
    return {"title": d.get("title") or "MI", "facts": [["담은 정보", str(c["kept"])], ["검색어", str(c["queries"])], ["확인 필요 수치", str(c["numberCheck"])]],
            "groups": groups, "foot": "문장은 원문을 줄여 쓴 것이고, 수치는 원문에서 확인해야 해요",
            "line": f"{d.get('code')} v{ver} · {parts} · 확인 필요 수치 {c['numberCheck']}"}


async def finish(fid: str) -> dict[str, Any]:
    d = await load(fid)
    if d.get("phase") in ("analyzing", "searching"):
        raise ApiError(409, "BUSY", "AI가 아직 일하고 있어요. 끝나면 저장할 수 있어요.")
    c = counts(d)
    if c["kept"] == 0:
        raise ApiError(422, "NO_ITEMS", "담은 정보가 하나 이상 있어야 저장할 수 있어요.")
    prev_ver = d.get("ver")
    prev_kept = d.get("saved_kept") if prev_ver else None
    ver = target_ver(d)

    def fn(doc: dict[str, Any]) -> None:
        doc["ver"] = ver
        doc["prev_ver"] = prev_ver
        doc["status"] = "done"
        doc["phase"] = "done"
        doc["editing"] = False
        doc["saved_at"] = now_iso()
        doc["saved_kept"] = c["kept"]
        doc["saved_items"] = [x for x in doc.get("items") or [] if x.get("kept")]
        doc["saved_queries"] = copy.deepcopy(doc.get("queries"))
        doc["progress"] = None
    saved = await update(fid, fn, f"저장 v{ver}")
    st, md = stage(saved, prev_ver), summary_md(saved, ver, prev_kept)
    await register_item(feature="MI", item_id=fid, title=saved.get("title") or "MI", status="done", route=f"/mi/flow/{fid}",
                        summary=f"{saved.get('code')} v{ver} · 담은 정보 {c['kept']} · 확인 필요 수치 {c['numberCheck']}")
    sync = await push_stage(saved["sb_id"], "mi", ref=saved.get("code") or fid, ver=ver, res_id=fid, title=saved.get("title"),
                            value=st, md=md, card=card(saved, ver))
    return {"stage": {"ref": saved.get("code") or fid, "ver": ver, **st}, "summary_md": md,
            "flow_sync": {"md_added": sync["md_added"], "synced": sync.get("synced") or []} if sync else None}


async def get_stage(fid: str) -> dict[str, Any]:
    d = await load(fid)
    ver = int(d.get("ver") or 0) or 1
    return {"stage": {"ref": d.get("code") or fid, "ver": ver, **stage(d, d.get("prev_ver"))}, "summary_md": summary_md(d, ver, None), "flow_sync": None}
