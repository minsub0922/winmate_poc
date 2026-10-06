"""LLM 출력 스키마 · 프롬프트(§7.9). 모든 호출은 스키마 모드, 고객 자료(요구 · 정의서 · RFP)가 들어가면 confidential=True.

스키마는 화면 id(ULID) 대신 프롬프트에 보인 안정 키(기준 이름 · 근거 번호 E1 · 후보 이름)를 쓰게 한다 — mock 고정 응답과
재생(replay) 카세트가 실행마다 바뀌는 id 에 묶이지 않게.
"""
from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── ca.extract_slots(§7.2) ───────────────────────────────
class SlotValue(BaseModel):
    value: str | None = None
    confidence: float = 0.0


class PlaceValue(BaseModel):
    value: str | None = None
    kind: Literal["region", "site", "scale"] | None = None
    region: str | None = Field(None, description="지역만(예: 수도권)")
    confidence: float = 0.0


class ProductValue(BaseModel):
    value: str | None = Field(None, description='제품 요약(예: 55" 사이니지 + 배포 솔루션)')
    categories: list[str] = Field(default_factory=list)
    specific: bool = Field(False, description="크기 · 모델 · 용도까지 읽혔으면 true, 제품군만이면 false")
    confidence: float = 0.0


class ExtractSlotsOut(BaseModel):
    customer: SlotValue = Field(default_factory=SlotValue)
    place: PlaceValue = Field(default_factory=PlaceValue)
    product: ProductValue = Field(default_factory=ProductValue)
    industry_hint: str | None = None
    competitor_mentions: list[str] = Field(default_factory=list)
    eval_criteria: list[str] = Field(default_factory=list)


def extract_slots(text: str, *, rfp_text: str = "", only: list[str] | None = None) -> str:
    want = only or ["customer", "place", "product"]
    return (
        "아래 고객 · 사업 설명에서 경쟁사 분석에 쓸 네 칸을 읽어라. 글에 없는 값은 null 로 둔다(추정 금지).\n"
        f"읽을 칸: {', '.join(want)}\n"
        "- customer: 고객사 이름 그대로(예: A 커피 프랜차이즈)\n"
        "- place: 지역 · 장소 요약(예: 수도권 직영점). kind = region(지역) · site(장소) · scale(규모). region 에는 지역만\n"
        "- product: 제품 요약(예: 55\" 사이니지 + 배포 솔루션). 제품군만 있으면 specific=false\n"
        "- industry_hint: 업종을 한 단어로(예: 카페 프랜차이즈)\n"
        "- competitor_mentions: 글에 이름이 나온 경쟁 회사(없으면 빈 목록) · eval_criteria: 평가 기준 문장(RFP)\n"
        "- confidence: 0~1\n\n"
        f"[고객 · 사업 설명]\n{text[:4000]}\n" + (f"\n[첨부 RFP · 회의록 앞부분]\n{rfp_text[:4000]}\n" if rfp_text else "")
    )


# ── ca.classify_segment(03-mi.md §7.3) ───────────────────
class SegmentP(BaseModel):
    code: str
    p: float = Field(0.0, ge=0, le=1)
    clues: list[str] = Field(default_factory=list)


class ClassifySegmentOut(BaseModel):
    segments: list[SegmentP] = Field(default_factory=list)
    out_of_scope: bool = False
    reason: str = ""


def classify_segment(text: str, seg_lines: list[str]) -> str:
    return (
        "아래 글이 다음 업종 각각에 해당할 그럴듯함 p(0~1)를 업종마다 독립적으로 매겨라(합이 1일 필요 없음). "
        "글에서 근거가 된 단서 낱말을 clues 에 넣어라. 16개 업종 어디에도 맞지 않으면 out_of_scope=true.\n\n"
        "[업종]\n" + "\n".join(seg_lines) + f"\n\n[글]\n{text[:4000]}"
    )


# ── ca.include_exclude(§4.10 덧붙일 내용) ─────────────────
class IncludeExcludeOut(BaseModel):
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    notes: str = ""


def include_exclude(extra: str) -> str:
    return (
        "아래 덧붙일 내용에서 경쟁사로 꼭 넣을 회사(include)와 뺄 회사(exclude)를 회사 이름 그대로 뽑아라. "
        "그 밖의 문장은 notes 에 그대로 둔다. 이름이 없으면 빈 목록.\n\n"
        f"[덧붙일 내용]\n{extra[:1500]}"
    )


# ── ca.candidates_from_text(§7.3 summary_only) ───────────
class CandidateMention(BaseModel):
    name: str
    kind_label: str = Field("", description="유형(예: 글로벌 사이니지 전문)")
    evidence_id: str = Field("", description="근거 번호(예: E1)")
    evidence_quote: str = Field("", description="근거 글에서 그대로 옮긴 구절")
    url_guess: str | None = Field(None, description="공식 사이트 URL 짐작(수집에 성공해야만 출처가 된다)")


class CandidatesOut(BaseModel):
    candidates: list[CandidateMention] = Field(default_factory=list)


def candidates_from_text(evidence: list[dict[str, Any]], *, industry: str, product: str) -> str:
    return (
        f"아래 근거 글에 이름이 나온 회사 중 '{industry}' 업종 고객에게 '{product}'(또는 같은 제품군)를 공급하거나 대체할 수 있는 회사만 뽑아라. "
        "근거 글에 없는 회사는 절대 넣지 않는다. 삼성 · 고객사 자신은 빼라. evidence_quote 는 근거 글에서 그대로 옮긴다.\n\n"
        + _evidence_block(evidence)
    )


# ── ca.resolve_entities ──────────────────────────────────
class EntityGroup(BaseModel):
    canonical: str
    aliases: list[str] = Field(default_factory=list)


class ResolveOut(BaseModel):
    groups: list[EntityGroup] = Field(default_factory=list)


def resolve_entities(names: list[str]) -> str:
    return ("아래 회사 이름 중 같은 회사(한글 · 영문 표기, 약칭)를 묶어라. 묶음마다 대표 이름(canonical) 하나와 나머지 이름(aliases). "
            "같은 회사가 아니면 따로 둔다.\n\n" + "\n".join(f"- {n}" for n in names))


# ── ca.score_signals(§7.4) ───────────────────────────────
class SignalScore(BaseModel):
    s: float = Field(0.0, ge=0, le=1)
    partial: bool = False
    source_ids: list[str] = Field(default_factory=list, description="근거 번호(E1 · K1 …)")


class SignalSet(BaseModel):
    industry: SignalScore = Field(default_factory=SignalScore)
    product: SignalScore = Field(default_factory=SignalScore)
    place: SignalScore = Field(default_factory=SignalScore)
    customer: SignalScore = Field(default_factory=SignalScore)


class ScoredCandidate(BaseModel):
    name: str
    kind_label: str = ""
    signals: SignalSet = Field(default_factory=SignalSet)
    why: str = Field("", description="근거 한 줄 ≤ 40자, 근거에 없는 수치 금지")


class ScoreOut(BaseModel):
    candidates: list[ScoredCandidate] = Field(default_factory=list)


def score_signals(names: list[str], evidence: list[dict[str, Any]], slots: dict[str, str]) -> str:
    return (
        "후보 회사마다 네 신호의 강도 s(0~1)와 근거 번호를 매겨라. 근거가 없으면 s=0, source_ids=[].\n"
        "- industry: 이 업종 고객 · 사례와 겹치는 정도 · product: 요구 제품군과 겹치는 정도(하드웨어 없이 소프트웨어만 등 일부만 겹치면 partial=true)\n"
        "- place: 그 지역 설치 · 레퍼런스 · customer: 그 고객사와 거래 · 입찰 이력\n"
        "why 는 근거 한 줄(40자 이내, 근거에 없는 수치 금지), kind_label 은 유형(예: 국내 대형 가전 · 사이니지).\n\n"
        f"[입력] 고객사: {slots.get('customer') or '[없음]'} · 업종: {slots.get('industry') or '[없음]'} · 장소: {slots.get('place') or '[없음]'} · 제품: {slots.get('product') or '[없음]'}\n"
        "[후보]\n" + "\n".join(f"- {n}" for n in names) + "\n\n" + _evidence_block(evidence)
    )


# ── ca.candidate_profile(§7.8 candidate_add) ─────────────
class CandidateProfileOut(BaseModel):
    kind_label: str = ""
    why: str = ""
    evidence_id: str = ""
    evidence_quote: str = ""
    url_guess: str | None = None
    aliases: list[str] = Field(default_factory=list, description="근거 글에 나온 같은 회사의 다른 표기(영문 이름 등). 없으면 빈 목록")


def candidate_profile(name: str, evidence: list[dict[str, Any]], product: str) -> str:
    return (f"'{name}' 이 어떤 회사인지 근거 글로만 정리하라. kind_label = 유형(예: 글로벌 사이니지 전문), why = '{product}' 과의 관계 한 줄(40자 이내, 근거에 없는 수치 금지). "
            "aliases = 근거 글에 나온 같은 회사의 다른 표기만. 근거가 없으면 빈 문자열.\n\n" + _evidence_block(evidence))


# ── ca.make_criteria(§7.5) ───────────────────────────────
class CriterionName(BaseModel):
    name: str = Field(description="비교 기준 이름 10자 이내(예: 본사 일괄 배포)")
    source: Literal["rfp", "requirements", "free"] = "requirements"
    requirement_ref: str | None = None


class MakeCriteriaOut(BaseModel):
    criteria: list[CriterionName] = Field(default_factory=list)


def make_criteria(reqs: list[dict[str, Any]]) -> str:
    lines = [f"- [{r.get('ref') or ''}] ({r['source']}) {r['text']}" for r in reqs]
    return ("아래 요구를 경쟁사 비교 기준 이름(10자 이내, 예: 본사 일괄 배포 · 매장별 가격 차등 · 전기료)으로 바꿔라. "
            "RFP 평가 기준 → 정의서 요구 → 자유 양식 요구 순으로 최대 3개, 같은 뜻은 하나로. requirement_ref 는 [ ] 안 값.\n\n" + "\n".join(lines))


# ── ca.title ─────────────────────────────────────────────
class TitleOut(BaseModel):
    title: str = Field(description="24자 이내 `{고객사} {제품 요약} 경쟁사 분석`")


def title(customer: str | None, industry: str, product: str) -> str:
    return (f"경쟁사 분석 작업 제목을 24자 이내로 지어라. 꼴: '{{고객사}} {{제품 요약}} 경쟁사 분석'(고객사가 없으면 '{{업종}} {{제품}} 경쟁사 분석'). "
            f"고객사: {customer or '[없음]'} · 업종: {industry} · 제품: {product}")


# ── ca.extract_facts(§7.6) ───────────────────────────────
class Citation(BaseModel):
    evidence_id: str
    quote: str


class FactClaim(BaseModel):
    text: str
    citations: list[Citation] = Field(default_factory=list)


class FactItem(BaseModel):
    text: str = Field("", description="짧은 사실(모르면 [확인 필요])")
    claims: list[FactClaim] = Field(default_factory=list)


class FactSet(BaseModel):
    lineup: FactItem = Field(default_factory=FactItem)
    price: FactItem = Field(default_factory=FactItem)
    solution: FactItem = Field(default_factory=FactItem)
    references: FactItem = Field(default_factory=FactItem)
    recent: FactItem = Field(default_factory=FactItem)


class ExtractFactsOut(BaseModel):
    facts: FactSet = Field(default_factory=FactSet)


def extract_facts(name: str, evidence: list[dict[str, Any]], *, recent_months: int) -> str:
    return (
        f"경쟁사 '{name}' 에 대해 아래 근거 글로만 다섯 항목을 짧게 써라. 항목마다 주장(claims)과 인용(근거 번호 · 그대로 옮긴 구절)을 붙인다.\n"
        "- lineup 제품 라인업 · price 가격대 · solution 솔루션(CMS 등) · references 레퍼런스(공개 사례) · "
        f"recent 최근 동향(최근 {recent_months}개월)\n"
        "- 근거가 없는 항목은 text 를 '[확인 필요]' 로, claims 는 빈 목록으로 둔다. 가격 · 수치는 근거 구절에 있을 때만 쓴다(추정 금지).\n\n"
        + _evidence_block(evidence)
    )


# ── ca.verdicts(§7.6 judge) ──────────────────────────────
class VerdictRow(BaseModel):
    criterion: str = Field(description="기준 이름 그대로")
    verdict: Literal["samsung_better", "similar", "samsung_worse", "unknown"] = "unknown"
    rationale: str = ""


class VerdictsOut(BaseModel):
    rows: list[VerdictRow] = Field(default_factory=list)


def verdicts(name: str, criteria: list[dict[str, Any]], facts: dict[str, str], samsung: dict[str, str]) -> str:
    crit_lines = [f"- {c['name']} (중요도 {c.get('importance', 3)}) · 삼성: {samsung.get(c['id']) or '[확인 필요]'}" for c in criteria]
    fact_lines = [f"- {k}: {v}" for k, v in facts.items()]
    return (
        f"기준마다 경쟁사 '{name}' 와 비교해 삼성이 낫다(samsung_better) · 비슷하다(similar) · 못하다(samsung_worse)를 판정하라. "
        "경쟁사 사실이나 삼성 근거가 [확인 필요] 이면 unknown. rationale 은 한 줄, 받은 사실에 없는 수치는 쓰지 않는다.\n\n"
        "[기준 · 삼성 근거]\n" + "\n".join(crit_lines) + "\n\n[경쟁사 사실]\n" + "\n".join(fact_lines)
    )


# ── ca.positioning ───────────────────────────────────────
class PositioningOut(BaseModel):
    text: str = Field(description="40자 이내 한 줄")


def positioning(name: str, facts: dict[str, str]) -> str:
    return (f"경쟁사 '{name}' 의 포지셔닝을 40자 이내 한 줄로 써라. 아래 사실 안의 표현만 쓰고 사실에 없는 수치는 쓰지 않는다.\n\n"
            + "\n".join(f"- {k}: {v}" for k, v in facts.items()))


# ── ca.strengths(§7.7) ───────────────────────────────────
class StrengthText(BaseModel):
    criterion: str
    title: str = Field(description="12자 이내")
    note: str = Field(description="30자 이내 한 줄")


class CautionText(BaseModel):
    letter: str
    note: str = Field(description="`{그 경쟁사 강점} · {우리에게 미치는 영향}`")


class StrengthsOut(BaseModel):
    strengths: list[StrengthText] = Field(default_factory=list)
    cautions: list[CautionText] = Field(default_factory=list)


def strengths(picks: list[dict[str, Any]], cautions: list[dict[str, Any]]) -> str:
    s_lines = [f"- 기준 '{p['name']}' · 삼성 근거: {p['samsung']} · 이긴 경쟁사 {p['wins']}곳" for p in picks]
    c_lines = [f"- 경쟁사 {c['letter']} · 기준 '{c['name']}' · 그 경쟁사 사실: {c['fact']}" for c in cautions]
    return (
        "삼성 강점(기준마다 제목 12자 이내 · 한 줄 30자 이내)과 주의할 점(경쟁사마다 `{그 경쟁사 강점} · {우리에게 미치는 영향}`)을 써라. "
        "삼성 근거 · 경쟁사 사실에 없는 수치 · 사례 규모는 쓰지 않는다. 경쟁사는 '경쟁사 {글자}' 로만 부른다.\n\n"
        "[강점 기준]\n" + ("\n".join(s_lines) or "- 없음") + "\n\n[주의할 점]\n" + ("\n".join(c_lines) or "- 없음")
    )


# ── ca.recheck_news(§7.8) ────────────────────────────────
class NewsItem(BaseModel):
    product: str
    date: str = Field(description="YYYY-MM-DD 또는 YYYY-MM")
    summary: str = ""
    quote: str = ""


class RecheckNewsOut(BaseModel):
    items: list[NewsItem] = Field(default_factory=list)


def recheck_news(name: str, since: str, evidence: list[dict[str, Any]]) -> str:
    return (f"'{name}' 가 {since} 이후 낸 신제품 · 출시 소식을 근거 글로만 뽑아라(날짜 · 제품 · 한 줄 요약 · 그대로 옮긴 구절). 없으면 빈 목록.\n\n"
            + _evidence_block(evidence))


# ── 공용 ─────────────────────────────────────────────────
def _evidence_block(evidence: list[dict[str, Any]]) -> str:
    lines = ["[근거]"]
    for e in evidence:
        head = f"{e['id']} ({e.get('label') or e.get('kind', '')}) {e.get('title') or ''}".strip()
        lines.append(f"{head}\n{(e.get('text') or '')[:1500]}")
    return "\n\n".join(lines)


def dumps(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False)
