"""LLM 출력 스키마 · 프롬프트(03-mi.md §7.13). 모든 호출은 JSON 스키마 모드, 고객 자료가 들어가면 confidential=True."""
from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from . import config


def _j(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False)


def segments_brief() -> str:
    return "\n".join(f"- {s['code']}: {s['full']} — {s['perspective']}" for s in config.segment_list() if s["code"] != "GEN")


def customer_context(doc: dict[str, Any], *, limit: int = 3000) -> str:
    reqs = [r.get("text", "") for r in doc.get("requirements") or []]
    ext = doc.get("extracted") or {}
    parts = [f"고객사: {doc.get('customer_name') or '[확인 필요]'}", f"요구사항 원문: {(doc.get('requirements_text') or '')[:limit]}"]
    if reqs:
        parts.append("구조화된 요구: " + " / ".join(reqs[:20]))
    if ext.get("key_messages"):
        parts.append("Storyboard Key Message: " + " / ".join(ext["key_messages"][:6]))
    if ext.get("author_note"):
        parts.append("제작자 의견(내부용 · 고객 문서에 쓰지 말 것): " + ext["author_note"][:600])
    if ext.get("file_summaries"):
        parts.append("첨부 요약: " + " / ".join(ext["file_summaries"][:6])[:limit])
    memos = [m["text"] for m in doc.get("memos") or []]
    if memos:
        parts.append("사용자 메모: " + " / ".join(memos[-5:]))
    return "\n".join(parts)


# ── 설계 ─────────────────────────────────────────────────
class FileClass(BaseModel):
    doc_kind: Literal["rfp", "minutes", "ir", "internal_research", "deployment_report", "price_list", "spec_sheet", "customer_material", "other"] = "other"
    classification: Literal["public", "internal", "confidential"] = "internal"
    title: str = ""
    date: str | None = None


def classify_file(name: str, head: str) -> str:
    return (f"첨부 파일의 종류와 기밀 분류를 정해라. 단가표 · 견적 · 원가 · 내부 가격은 confidential, 고객 RFP · 회의록 · 고객 제공 자료는 internal, "
            f"공개 IR · 보도자료는 public.\n파일 이름: {name}\n앞부분:\n{head[:3000]}")


class ExtractReq(BaseModel):
    requirements: list[str] = Field(default_factory=list, description="요구 항목(짧은 명사구)")
    eval_criteria: list[str] = Field(default_factory=list)
    schedule: list[str] = Field(default_factory=list)
    competitor_mentions: list[str] = Field(default_factory=list, description="원문에 나온 경쟁사 · 공급사 이름 그대로")
    keywords: list[str] = Field(default_factory=list)
    region: str | None = Field(None, description="국내 · 수도권 등 시장 지역(없으면 null)")


def extract_requirements(doc: dict[str, Any]) -> str:
    return ("고객 요구사항과 첨부에서 요구 항목 · 평가 기준 · 일정 · 경쟁사 언급 · 범위 키워드를 뽑아라. 원문에 없는 것은 넣지 않는다.\n\n"
            + customer_context(doc, limit=4000))


class SegScore(BaseModel):
    code: str
    p: float = Field(0.0, ge=0, le=1)
    clues: list[str] = Field(default_factory=list)


class SegClass(BaseModel):
    segments: list[SegScore] = Field(default_factory=list)
    out_of_scope: bool = False
    reason: str = ""


def classify_segment(doc: dict[str, Any], hint: str | None = None) -> str:
    h = f"\n판단에 도움이 될 말(사용자): {hint}" if hint else ""
    return ("아래 16개 업종마다 이 고객이 그 업종일 그럴듯함 p(0~1)를 서로 독립적으로 매겨라(합이 1일 필요 없음). "
            "업종마다 근거가 된 단서 낱말(원문 그대로)을 clues 에 넣어라. 어디에도 맞지 않으면 out_of_scope=true.\n"
            f"업종:\n{segments_brief()}\n\n{customer_context(doc)}{h}")


class AreaInclude(BaseModel):
    include: bool = True
    reason: str = ""


class ScopeAreas(BaseModel):
    market: AreaInclude = AreaInclude()
    customer: AreaInclude = AreaInclude()
    user: AreaInclude = AreaInclude()
    competitor: AreaInclude = AreaInclude()


class ScopeOut(BaseModel):
    areas: ScopeAreas = ScopeAreas()


def decide_scope(doc: dict[str, Any], segment: str) -> str:
    return (f"요구사항을 보고 분석 영역(market 시장 · customer 고객사 · user 사용자 · competitor 경쟁사)마다 넣을지와 한 줄 이유를 정해라. "
            f"업종: {config.segment(segment)['full']}\n\n{customer_context(doc)}")


class ScopeDesc(BaseModel):
    market: str = ""
    customer: str = ""
    user: str = ""
    competitor: str = ""


class TitleTopic(BaseModel):
    title: str = Field("", description="'{고객사} {주제} 분석' 꼴, 30자 이내")
    topic: str = Field("", description="예 '시장 · 경쟁사'")
    scope_desc: ScopeDesc = ScopeDesc()
    req_summary: str = Field("", description="요구 요약 60자 이내")


def title_topic(doc: dict[str, Any], segment: str, areas: list[str], competitors: list[str]) -> str:
    return (f"작업 제목 · 주제 · 영역 설명 4개 · 요구 요약을 써라. 영역 설명 예: market '국내 F&B 디지털 사이니지 시장 규모·성장률, 도입 트렌드, 규제'. "
            f"경쟁사 영역 설명에는 받은 표기({' · '.join(competitors) or '경쟁사'})만 쓴다.\n업종: {config.segment(segment)['full']} · 영역: {areas}\n\n"
            + customer_context(doc))


class Candidate(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    kind_label: str = Field("", description="유형(예 '국내 대형 가전 · 사이니지')")
    desc: str = Field("", description="한 줄 설명(예 '메뉴보드급 사이니지 · 자체 CMS')")
    confidence: float = Field(0.0, ge=0, le=1)
    quote: str = Field("", description="근거 요약 속 구절 그대로")


class Candidates(BaseModel):
    items: list[Candidate] = Field(default_factory=list)


def competitor_candidates(segment: str, product: str, summary: str) -> str:
    return (f"{config.segment(segment)['full']} 업종의 {product} 공급 경쟁사 후보를 검색 요약에서만 뽑아라(삼성 제외). "
            f"요약에 이름이 없는 회사는 넣지 않는다. confidence 는 요약의 근거 강도(0~1).\n\n검색 요약:\n{summary[:4000]}")


def competitor_profile(name: str, summary: str) -> str:
    return (f"'{name}' 의 정식 이름 · 별칭 · 유형 · 한 줄 설명을 검색 요약에서만 써라. 요약에 없으면 kind_label · desc 를 '[확인 필요]'로.\n\n"
            f"검색 요약:\n{summary[:3000]}")


class PublicDocs(BaseModel):
    documents: list[str] = Field(default_factory=list, description="요약에 나온 서로 다른 공개 문서 이름(사업보고서 · IR · 보도자료)")


def public_docs(customer: str, summary: str) -> str:
    return f"'{customer}' 의 공개 문서(사업보고서 · IR · 보도자료) 이름을 요약에서만 뽑아라.\n\n{summary[:3000]}"


# ── 분석 ─────────────────────────────────────────────────
class WebQuery(BaseModel):
    q: str
    purpose: str = ""
    recency_months: int = 24


class AreaPlan(BaseModel):
    area: Literal["market", "customer", "user", "competitor"]
    questions: list[str] = Field(default_factory=list)
    web_queries: list[WebQuery] = Field(default_factory=list)
    file_terms: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    areas: list[AreaPlan] = Field(default_factory=list)


def plan(doc: dict[str, Any], areas: list[str], memos: list[str]) -> str:
    seg = config.segment((doc.get("segment") or {}).get("code"))
    m = f"\n진행 방향 메모(반드시 반영): {' / '.join(memos)}" if memos else ""
    comps = [c.get("real_name") for c in doc.get("competitors") or [] if not c.get("removed")]
    return (f"영역마다 조사 질문 · 웹 검색어(한국어 우선) · 파일에서 찾을 말을 정해라. 검색어에는 고객사 이름 · 업종 · 지역 · 제품군 · 경쟁사 이름 · 공개 보고서 이름만 쓰고, "
            f"요구사항 문장을 그대로 넣지 않는다.\n업종: {seg['full']} · 제품군: {seg['product']} · 영역: {areas} · 경쟁사: {comps}{m}\n\n"
            + customer_context(doc, limit=1500))


class ClaimCitation(BaseModel):
    evidence_id: str = Field(..., description="근거 번호(E1 …)")
    quote: str = Field(..., description="근거 원문에서 그대로 옮긴 구절")
    page: int | None = None


class ExtractedClaim(BaseModel):
    local_id: str
    block_path: str = ""
    text: str
    metric_key: str | None = None
    metric_label: str | None = Field(None, description="확정 필요 항목 이름(예 '디지털 메뉴보드 도입 매장 증가율')")
    citations: list[ClaimCitation] = Field(default_factory=list)


class SizeRef(BaseModel):
    year: int
    claim: str


class CagrRef(BaseModel):
    period: str = ""
    claim: str


class TrendRef(BaseModel):
    title: str
    when: str | None = None
    claim: str
    implication: str = ""


class TitledRef(BaseModel):
    title: str
    claim: str


class MarketBlocks(BaseModel):
    size_label: str = ""
    size_unit: str = ""
    size_series: list[SizeRef] = Field(default_factory=list)
    cagr: CagrRef | None = None
    trends: list[TrendRef] = Field(default_factory=list)
    regulations: list[TitledRef] = Field(default_factory=list)
    kb_trend: str | None = None


class MarketExtract(BaseModel):
    blocks: MarketBlocks = MarketBlocks()
    claims: list[ExtractedClaim] = Field(default_factory=list)


class StructRef(BaseModel):
    label: str
    value: str = ""
    claim: str | None = None


class StageRef(BaseModel):
    stage: str
    claim: str


class CustomerBlocks(BaseModel):
    summary: str | None = None
    strategy: list[str] = Field(default_factory=list)
    expansion: list[str] = Field(default_factory=list)
    structure: list[StructRef] = Field(default_factory=list)
    ops_challenges: list[StageRef] = Field(default_factory=list)


class CustomerExtract(BaseModel):
    blocks: CustomerBlocks = CustomerBlocks()
    claims: list[ExtractedClaim] = Field(default_factory=list)


class PersonaRef(BaseModel):
    role: str
    goal: str = ""
    pain: str = ""
    context: str = ""
    claims: list[str] = Field(default_factory=list)


class JourneyRef(BaseModel):
    stage: str
    touchpoint: str = ""
    pain: str = ""
    opportunity: str = ""
    claims: list[str] = Field(default_factory=list)


class CompRef(BaseModel):
    label: str
    claim: str


class UserBlocks(BaseModel):
    personas: list[PersonaRef] = Field(default_factory=list)
    journey: list[JourneyRef] = Field(default_factory=list)
    composition: list[CompRef] = Field(default_factory=list)


class UserExtract(BaseModel):
    blocks: UserBlocks = UserBlocks()
    claims: list[ExtractedClaim] = Field(default_factory=list)


EXTRACT_MODELS = {"market": MarketExtract, "customer": CustomerExtract, "user": UserExtract}
AREA_GUIDE = {
    "market": "시장 규모(연도별 · 단위) · 성장률 · 도입 트렌드(제목 · 시점 · 설명 · '그래서 {고객사}는' 한 줄) · 규제를 쓴다. kb_trend 는 사내 사례 DB 도입 경향 문장.",
    "customer": "고객사 한 줄 요약 · 전략 · 투자/확장 계획 · 운영 구조(예 직영 : 가맹) · 운영 단계별 과제를 쓴다. 고객만 아는 수치는 [00] 으로 둔다.",
    "user": "페르소나(최대 3: 역할 · 목표 · 불편 · 맥락) · 여정(단계 → 접점 → 불편 → 기회) · 구성 비율(데이터 있을 때만)을 쓴다.",
}


def extract_claims(area: str, doc: dict[str, Any], evidence: list[dict[str, Any]], memos: list[str]) -> str:
    ev = "\n".join(f"[{e['id']}] ({e['kind_label']}) {e['title']}\n{e['text'][:1500]}" for e in evidence)
    m = f"\n진행 방향 메모(반영): {' / '.join(memos)}" if memos else ""
    return (f"영역 '{area}' 결과를 근거 묶음으로만 써라. {AREA_GUIDE[area]}\n"
            "규칙: 주장(claims)마다 text(화면 문장) · 근거 번호와 원문 구절(citations)을 단다. 블록은 주장의 local_id 로 가리킨다. "
            "근거에 없는 수치는 쓰지 말고 [00] 으로 둔다. 수치가 있는 주장에는 metric_key(영문 snake_case)와 metric_label 을 준다."
            f"{m}\n\n{customer_context(doc, limit=1500)}\n\n근거 묶음:\n{ev}")


class CellCitation(BaseModel):
    evidence_id: str
    quote: str


class Cell(BaseModel):
    criterion_id: str
    competitor_id: str
    text: str = Field(..., description="짧은 문장, 모르면 [확인 필요] 또는 [00]{단위}")
    citations: list[CellCitation] = Field(default_factory=list)


class Cells(BaseModel):
    cells: list[Cell] = Field(default_factory=list)


def compare_cells(criteria: list[dict[str, Any]], comps: list[dict[str, Any]], evidence: list[dict[str, Any]], memos: list[str]) -> str:
    ev = "\n".join(f"[{e['id']}] ({e['kind_label']}) {e['title']}\n{e['text'][:1200]}" for e in evidence)
    m = f"\n진행 방향 메모(반영): {' / '.join(memos)}" if memos else ""
    return ("경쟁사 비교표 칸을 채워라. 기준 × 경쟁사마다 짧은 문장 + 근거 구절. 경쟁사 수치는 공개 자료 근거에만 있을 때 쓰고, 없으면 [확인 필요].\n"
            f"기준: {_j([{'id': c['id'], 'name': c['name']} for c in criteria])}\n경쟁사: {_j([{'id': c['id'], 'name': c['real_name']} for c in comps])}{m}\n\n근거:\n{ev}")


class VerdictItem(BaseModel):
    competitor_id: str
    verdict: Literal["samsung_better", "similar", "samsung_worse", "unknown"] = "unknown"


class VerdictRow(BaseModel):
    criterion_id: str
    verdicts: list[VerdictItem] = Field(default_factory=list)
    rationale: str = ""


class Verdicts(BaseModel):
    rows: list[VerdictRow] = Field(default_factory=list)


def verdicts(table_txt: str) -> str:
    return ("비교표의 기준마다 삼성이 각 경쟁사보다 나은지 판정하라. 근거가 [확인 필요] 인 칸은 unknown.\n\n" + table_txt)


class StrengthOut(BaseModel):
    criterion_id: str
    title: str = Field(..., description="12자 이내")
    note: str = Field(..., description="한 줄 근거 40자 이내")
    citations: list[CellCitation] = Field(default_factory=list)


class Strengths(BaseModel):
    strengths: list[StrengthOut] = Field(default_factory=list)


def strengths(picked: list[dict[str, Any]], table_txt: str, evidence: list[dict[str, Any]]) -> str:
    ev = "\n".join(f"[{e['id']}] {e['title']}\n{e['text'][:900]}" for e in evidence)
    return ("고른 기준마다 삼성 강점 제목(12자 이내)과 한 줄 근거(40자 이내)를 써라. 한 줄 근거의 수치는 사례 · KPI 근거 구절에 있어야 한다.\n"
            f"고른 기준: {_j(picked)}\n\n비교표:\n{table_txt}\n\n사례 근거:\n{ev}")


class Implications(BaseModel):
    findings: list[str] = Field(default_factory=list)
    implications: list[str] = Field(default_factory=list)
    direction: str = ""


def implications(summary: str) -> str:
    return "분석 결과로 발견 → 시사점 → 방향을 써라. 새 사실이나 수치를 만들지 않는다.\n\n" + summary


class Onepager(BaseModel):
    market: str = ""
    customer: str = ""
    user: str = ""
    competitor: str = ""
    conclusion: str = ""


def onepager(summary: str) -> str:
    return "IM-B(4분면 요약 + 결론) 한 장 요약을 써라. 분면마다 한두 문장, 결과에 있는 문장 · 수치만 쓴다.\n\n" + summary


class MessageIntent(BaseModel):
    intent: Literal["why", "how_much", "who"] = "why"


# ── 재분석 · 질문 ────────────────────────────────────────
class Operation(BaseModel):
    op: Literal["add_row", "remove_row", "edit_cell", "edit_strength", "research_claim", "shorten", "remove_competitor", "use_internal_spec", "edit_text"]
    target: str = ""
    detail: str = ""


class Interpret(BaseModel):
    operations: list[Operation] = Field(default_factory=list)
    needs_search: bool = False
    quick_suggestion: str | None = None


def revise_interpret(instruction: str, scope: dict[str, Any], table_txt: str) -> str:
    return (f"수정 요청을 작업 목록으로 바꿔라. 범위 밖은 건드리지 않는다. 범위: {_j(scope)}\n요청: {instruction}\n\n지금 결과:\n{table_txt[:3000]}\n"
            "quick_suggestion 에는 다음에 해 볼 만한 짧은 요청 하나(예 '경쟁사 B 빼기')를 쓴다.")


class FollowupIntent(BaseModel):
    intent: Literal["question", "revision"] = "question"
    area: Literal["market", "customer", "user", "competitor"] | None = None
    instruction: str | None = None


def followup_intent(text: str, tab: str | None, doc: dict[str, Any]) -> str:
    return (f"사용자 말이 결과에 대한 질문인지(question), 결과를 고쳐 달라는 요청인지(revision) 정해라. revision 이면 고칠 영역과 지시문을 쓴다.\n"
            f"지금 탭: {tab or '-'}\n말: {text}")


class AnswerOut(BaseModel):
    answer_md: str = ""
    citations: list[int] = Field(default_factory=list, description="쓴 출처 번호")
    answerable: bool = True


def answer(question: str, evidence: list[dict[str, Any]], claim_lines: list[str], doc: dict[str, Any]) -> str:
    ev = "\n".join(f"[{e['n']}] {e['title']}\n{e['text']}" for e in evidence)
    return ("저장된 출처와 결과 문장으로만 답하라(새 검색 없음). 답 속 수치는 출처에 있어야 한다. 답할 수 없으면 answerable=false.\n"
            f"질문: {question}\n\n결과 문장:\n" + "\n".join(claim_lines) + f"\n\n출처:\n{ev}")


class FixMatch(BaseModel):
    fix_id: str
    value: str
    unit: str | None = None
    page: int | None = None
    quote: str = ""


class FixMatches(BaseModel):
    matches: list[FixMatch] = Field(default_factory=list)


def fix_match(items: list[dict[str, Any]], pages: list[dict[str, Any]]) -> str:
    pg = "\n".join(f"[p.{p['no']}] {p['text'][:1800]}" for p in pages)
    its = _j([{"fix_id": i["id"], "title": i.get("title"), "unit": i.get("unit")} for i in items])
    return f"올린 자료의 쪽 텍스트에서 항목 값을 찾아라. quote 는 그 쪽 원문 그대로, value 는 구절 속 숫자.\n항목: {its}\n\n쪽:\n{pg}"


class FixParseItem(BaseModel):
    fix_id: str
    value: str
    unit: str | None = None
    basis: str = ""


class FixParseOut(BaseModel):
    suggestions: list[FixParseItem] = Field(default_factory=list)


def fix_parse(text: str, items: list[dict[str, Any]]) -> str:
    its = _j([{"fix_id": i["id"], "title": i.get("title"), "unit": i.get("unit")} for i in items])
    return f"사용자 말에서 항목 · 값 · 근거를 짝지어라. 말에 없는 값은 만들지 않는다.\n항목: {its}\n말: {text}"


class QuestionOut(BaseModel):
    question: str = ""


def customer_question(item: dict[str, Any], customer: str) -> str:
    return f"고객 담당자에게 '{item.get('title')}' 값을 정중히 묻는 한 문장을 써라. 고객사: {customer}"


class NewsItem(BaseModel):
    product: str
    date: str | None = None
    summary: str = ""
    competitor_id: str | None = None


class News(BaseModel):
    items: list[NewsItem] = Field(default_factory=list)


def recheck_news(name: str, since: str, summary: str) -> str:
    return f"'{name}' 의 {since} 이후 신제품 출시만 검색 요약에서 뽑아라(날짜 YYYY-MM-DD, 모르면 null).\n\n{summary[:3000]}"


class SlideRequest(BaseModel):
    kind: Literal["layout", "include", "none"] = "none"
    sheet_type: Literal["MS", "TR", "MS+TR", "CB", "US", "CP", "IM"] | None = None
    template: str | None = None
    include: list[str] = Field(default_factory=list, description="넣을 시트 유형")
    exclude: list[str] = Field(default_factory=list, description="뺄 시트 유형")
    axes_x: str | None = None
    axes_y: str | None = None


def slide_request(text: str, rows: list[dict[str, Any]]) -> str:
    rs = _j([{"sheet_type": r["sheet_type"], "sheet_name": r["sheet_name"], "template": r["template_code"], "included": r["included"]} for r in rows])
    return ("시트 구성 요청을 해석하라. 레이아웃을 바꾸는 요청이면 kind=layout(시트 유형 · 템플릿 코드 · 축), 시트를 넣고 빼는 요청이면 kind=include. "
            "템플릿 코드는 MS-A~E · TR-A~C · CB-A~D · US-A~C · CP-A~C(포지셔닝 맵 = CP-B) · IM-A~B 중에서.\n"
            f"시트: {rs}\n요청: {text}")


# ── 재분석 보조 ──────────────────────────────────────────
class ClaimRewrite(BaseModel):
    claim_id: str
    text: str


class Rewrites(BaseModel):
    items: list[ClaimRewrite] = Field(default_factory=list)


def revise_apply(instruction: str, claims: list[dict[str, Any]]) -> str:
    cs = _j([{"claim_id": c["id"], "text": c["text"]} for c in claims])
    return ("요청대로 문장을 고쳐라. 수치 · 이름 · 사실은 그대로 두고(새 수치를 만들지 않는다) 표현만 바꾼다. 바꿀 필요가 없는 문장은 빼라.\n"
            f"요청: {instruction}\n문장: {cs}")


class ClaimCites(BaseModel):
    citations: list[ClaimCitation] = Field(default_factory=list)


def research_claim(text: str, evidence: list[dict[str, Any]]) -> str:
    ev = "\n".join(f"[{e['id']}] ({e['kind_label']}) {e['title']}\n{e['text'][:1500]}" for e in evidence)
    return ("주장을 뒷받침하는 구절을 근거 묶음에서만 골라라. 구절은 원문 그대로 옮기고, 뒷받침하는 구절이 없으면 빈 목록.\n"
            f"주장: {text}\n\n근거 묶음:\n{ev}")
