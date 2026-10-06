"""LLM 호출 — ai-tools JSON 스키마 응답만, 항상 `confidential=True`(고객 자료가 프롬프트에 들어간다).

task 이름 `sb.<동작>`(자리별로 나눈 것은 `sb.section.<자리 키>` · `sb.slot_questions.<공간 키>` …) — mock 고정 응답
`mocks/ai-tools/<task>.json` 의 키가 된다. 웹 검색은 쓰지 않는다(외부 수치는 MI 로 넘긴다, §7.0).

정의서 항목은 id 대신 코드(`RQ-01`)로, 섹션은 자리 키(`overview` · `p1_2` · `part2` …), 공간은 `space:<키>` 로 주고받는다
(LLM 이 만든 참조를 결정적으로 되짚기 위해 — 02-storyboard.md §7.9 스키마의 `item_id` · `place_id` 자리).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Literal

from pydantic import BaseModel, Field
from winmate_common.ai import ai
from winmate_common.errors import ApiError

log = logging.getLogger("winmate.storyboard.llm")

SYSTEM = (
    "너는 삼성전자 B2B 영업 기획자를 돕는 제안 기획 어시스턴트다. 한국어로 답한다.\n"
    "규칙: (1) 정의서 · 기획 답 · KB 근거에 없는 사실 · 수치 · 고객명 · 제품 사양을 지어내지 않는다. 모르는 수치는 [00], "
    "확인 전 내용은 [확인 필요]로 쓴다. (2) 제작자 의견(내부용)의 영업 목표 · 스펙인 · 수주 같은 삼성 내부 목표는 고객용 문장에 넣지 않는다. "
    "(3) '최초' · '유일' · '1위' 같은 검증 안 된 주장을 만들지 않는다. (4) 짧고 구체적으로, 보고서 문체가 아니라 기획 메모 문체로 쓴다. "
    "(5) 요청한 JSON 스키마만 돌려준다."
)


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, default=str)


def map_error(exc: Exception) -> ApiError:
    if isinstance(exc, ApiError):
        if exc.code == "POLICY_CONFIDENTIAL" or exc.status == 403:
            return ApiError(403, "POLICY_CONFIDENTIAL", "기밀 자료는 지금 설정된 모델로 보낼 수 없어요. 사내 모델 설정을 확인해 주세요.",
                            exc.details)
        if exc.status == 504 or exc.code in ("TIMEOUT", "LLM_TIMEOUT"):
            return ApiError(504, "LLM_TIMEOUT", "AI 응답이 늦어져 멈췄어요. 잠시 후 다시 시도해 주세요.", exc.details)
        if exc.status in (429, 500, 502, 503) or exc.code in ("UPSTREAM_UNAVAILABLE", "RATE_LIMITED", "PROVIDER_ERROR"):
            return ApiError(503, "LLM_UNAVAILABLE", "지금은 AI를 쓸 수 없어요. 잠시 후 다시 시도해 주세요.", {"upstream": exc.code})
        return exc
    return ApiError(503, "LLM_UNAVAILABLE", "지금은 AI를 쓸 수 없어요. 잠시 후 다시 시도해 주세요.", {"error": str(exc)[:200]})


async def call(task: str, prompt: str, schema: type[BaseModel], *, temperature: float | None = 0.3) -> dict[str, Any]:
    """JSON 결과(dict). 모델 · 정책 오류는 이 서비스 오류 코드(403 POLICY_CONFIDENTIAL · 503 LLM_UNAVAILABLE · 504 LLM_TIMEOUT)로."""
    try:
        return await ai().json(task, prompt, schema, system=SYSTEM, confidential=True, temperature=temperature)
    except Exception as exc:  # noqa: BLE001
        err = map_error(exc)
        log.warning("LLM %s 실패: %s %s", task, err.code, err.message)
        raise err from exc


# ── 출력 스키마(§7.9) ───────────────────────────────────────

class SbSettings(BaseModel):
    short_name: str | None = Field(None, description="스토리보드 짧은 이름(장소 · 대상, 12자 안팎) — 뒤에 ' 제안 기획'을 붙인다")
    stage: Literal["concept", "main"] | None = None
    stage_evidence: str | None = Field(None, description="제안 단계를 판단한 정의서 · 원본 문장(그대로 짧게)")
    language: Literal["ko", "en", "ko_en"] | None = None
    language_hint: str | None = None


class SbQuestionCandidate(BaseModel):
    topic: Literal["decision", "audience", "comparison", "budget_scope", "timeline"]
    answerable_from_rq: bool
    impact: int = Field(ge=1, le=3)
    reason: str = ""


class SbQuestionPick(BaseModel):
    candidates: list[SbQuestionCandidate]


class SbFollowUpOption(BaseModel):
    label: str
    effect: Literal["use_public", "internal_only", "placeholder"]


class SbFollowUp(BaseModel):
    text: str
    options: list[SbFollowUpOption] = Field(default_factory=list)


class SbOption(BaseModel):
    label: str
    hint: str | None = None
    badge: str | None = None
    follow_up: SbFollowUp | None = None
    recommended: bool = False


class SbQuestion(BaseModel):
    topic: str
    text: str | None = None
    info: str | None = None
    options: list[SbOption]


class SbPlanningQuestions(BaseModel):
    questions: list[SbQuestion]


class SbItemClass(BaseModel):
    code: str = Field(description="정의서 항목 코드(RQ-01)")
    theme: str
    is_internal_goal: bool = False


class SbItemClasses(BaseModel):
    items: list[SbItemClass]
    internal_goal_phrases: list[str] = Field(default_factory=list, description="제작자 의견에서 뽑은 삼성 내부 목표 구절(그대로)")


class SbAxis(BaseModel):
    key: str
    title: str
    one_liner: str
    codes: list[str] = Field(description="이 축이 담는 정의서 항목 코드")


class SbAxes(BaseModel):
    axes: list[SbAxis]


class SbCombo(BaseModel):
    title: str
    one_liner: str


class SbMessage(BaseModel):
    place_label: str
    axis_key: str
    audience: str = ""
    text: str
    kb_refs: list[str] = Field(default_factory=list)


class SbKeyMessages(BaseModel):
    messages: list[SbMessage]


class SbClaimFix(BaseModel):
    span_text: str | None = Field(None, description="표시할 구간(주장 단어를 포함, 문장의 부분 문자열)")
    suggestion: str = Field(description="span_text 를 바꿀 검증 가능한 표현")
    note: str = ""


class SbGroupNames(BaseModel):
    part1: str = "사업 논리"
    part2: str = "공간 시나리오"
    part3: str = "실행 역량"


class SbGroupSummaries(BaseModel):
    start: str = ""
    part1: str = ""
    part2: str = ""
    part3: str = ""
    end: str = ""


class SbOwners(BaseModel):
    part1: str = "영업 기획"
    part2: str = "솔루션"
    part3: str = "관계사 협업"


class SbSkeletonSection(BaseModel):
    group_key: Literal["part1", "part3"]
    name: str


class SbSkeleton(BaseModel):
    group_names: SbGroupNames = Field(default_factory=SbGroupNames)
    group_summaries: SbGroupSummaries = Field(default_factory=SbGroupSummaries)
    sections: list[SbSkeletonSection] = Field(default_factory=list)
    owners: SbOwners = Field(default_factory=SbOwners)


class SbLine(BaseModel):
    text: str
    reviewing: bool = False


class SbKbRef(BaseModel):
    kind: str
    id: str


class SbProduct(BaseModel):
    name: str
    kb_ref: SbKbRef | None = None


class SbSection(BaseModel):
    direction: str = Field(description="작성 방향 한 줄(60자 이내)")
    lines: list[SbLine] = Field(default_factory=list)
    products: list[SbProduct] = Field(default_factory=list)
    tbd_reason: str | None = None
    discussion_labels: list[str] = Field(default_factory=list)
    internal_memo: str | None = None


class SbSlotText(BaseModel):
    slot: Literal["action", "trigger", "response", "exception", "metric"]
    text: str


class SbSpace(BaseModel):
    key: str = Field(description="공간 유형 키(kb space_type 또는 영문 슬러그)")
    name: str
    purpose: str = ""
    from_rq: bool = Field(True, description="정의서에 근거가 있는 공간인가(없으면 확장)")
    slots: list[SbSlotText] = Field(default_factory=list, description="근거 있는 칸만")
    products: list[SbProduct] = Field(default_factory=list)


class SbSpaces(BaseModel):
    spaces: list[SbSpace]


class SbTraceOption(BaseModel):
    label: str
    hint: str = ""
    target: str | None = Field(None, description="놓을 곳 자리 키(p1_4) 또는 space:<키>")


class SbTraceQuestion(BaseModel):
    text: str
    info: str = ""
    options: list[SbTraceOption] = Field(default_factory=list)


class SbTraceItem(BaseModel):
    code: str
    places: list[str] = Field(default_factory=list, description="자리 키 또는 space:<키>")
    places_label: str | None = None
    link_types: list[Literal["direct", "interpreted", "extension", "reviewing", "unconfirmed"]] = Field(default_factory=list)
    problem: Literal["no_place", "empty_content"] | None = None
    owner_note: str | None = None
    priority: int | None = None
    question: SbTraceQuestion | None = None


class SbExtension(BaseModel):
    name: str
    short: str = ""
    where_label: str = ""
    places: list[str] = Field(default_factory=list)
    derived_from_codes: list[str] = Field(default_factory=list)
    status: Literal["extension", "reviewing"] = "extension"


class SbDiscussion(BaseModel):
    label: str
    short: str = ""
    section_refs: list[str] = Field(default_factory=list)


class SbTrace(BaseModel):
    items: list[SbTraceItem]
    extensions: list[SbExtension] = Field(default_factory=list)
    discussions: list[SbDiscussion] = Field(default_factory=list)


class SbSlotQ(BaseModel):
    slot: Literal["action", "trigger", "response", "exception", "metric"]
    text: str
    info: str | None = None
    options: list[str]


class SbSlotQuestions(BaseModel):
    questions: list[SbSlotQ]


class SbSeg(BaseModel):
    text: str
    ai_added: bool = False


class SbSlotSegments(BaseModel):
    slot: Literal["action", "trigger", "response", "exception", "metric"]
    segments: list[SbSeg]


class SbCustomerQ(BaseModel):
    text: str
    short_label: str


class SbSlotCompose(BaseModel):
    slots: list[SbSlotSegments]
    customer_questions: list[SbCustomerQ] = Field(default_factory=list)
    products: list[SbProduct] = Field(default_factory=list)


class SbRevLine(BaseModel):
    id: str | None = Field(None, description="고친 줄은 원래 id, 새 줄은 비움")
    text: str


class SbKept(BaseModel):
    id: str
    reason: str


class SbRevision(BaseModel):
    lines: list[SbRevLine]
    kept: list[SbKept] = Field(default_factory=list, description="그대로 둔 줄과 이유(`kept_reasons`)")


class SbSyncPlace(BaseModel):
    place_id: str = Field(description="자리 키 또는 space:<키>")
    aspect: str | None = None
    kind: Literal["changed", "added", "removed", "kept"] = "changed"
    lines: list[str] | None = None
    slots: list[SbSlotText] | None = None
    summary_before: str = ""
    summary_after: str = ""


class SbSyncUpdate(BaseModel):
    places: list[SbSyncPlace]


class SbPlaceItem(BaseModel):
    place_id: str | None = None
    lines_add: list[str] = Field(default_factory=list)
    slot_segments: list[SbSlotText] = Field(default_factory=list)
    result_label: str = ""


class SbMiTopic(BaseModel):
    codes: list[str] = Field(description="근거가 필요한 섹션 코드(1-1 · 1-2)")
    find: str = Field(description="MI 가 찾을 것(한 줄)")


# ── 프롬프트 ───────────────────────────────────────────────

def p_settings(rq: dict[str, Any]) -> str:
    return ("요구사항 정의서에서 스토리보드 설정 근거를 뽑아라. 제안 단계(concept=컨셉 제안, main=본제안)는 요청서 · 회의 메모의 단계 문장을 "
            "근거로(짧게 그대로), 언어는 정의서 언어 · 고객 지역으로. 근거가 없으면 null. short_name 은 장소 · 대상을 담은 짧은 이름"
            "(예: '용산 오피스').\n\n정의서:\n" + _dump(rq))


def p_pick(rq: dict[str, Any]) -> str:
    return ("기획 질의 후보(decision=고객이 결정할 것, audience=먼저 설득할 사람, comparison=고객의 비교 기준, budget_scope, timeline)마다 "
            "정의서만으로 답할 수 있는지(answerable_from_rq)와 영향(impact 1–3)을 평가하라. 정의서로 답할 수 있으면 묻지 않는다.\n\n정의서:\n"
            + _dump(rq))


def p_questions(rq: dict[str, Any], topics: list[str]) -> str:
    return ("다음 기획 질의마다 선택지 2–4개를 만들어라(짧은 명사구). audience 는 정의서 키맨 · 부서를 부서 단위로 묶고 hint 에 맡을 부분"
            "(예 'Part 2 공간 경험')을, comparison 은 정의서 · 제작자 의견의 비교 대상 + 일반안. 고객사 기존 자산이 비교 대상이면 그 선택지에 "
            "follow_up(그 자산의 성과 수치를 Part 1-2에 쓸 수 있는지, 선택지 use_public · internal_only · placeholder)을 붙여라. "
            "근거가 있으면 recommended=true.\n질의: " + ", ".join(topics) + "\n\n정의서:\n" + _dump(rq))


def p_classify(rq: dict[str, Any]) -> str:
    return ("정의서 항목을 주제(theme)로 묶고, 제작자 의견에서 나온 삼성 내부 목표(영업 목표 · 스펙인 · 수주 등)를 고객 요구와 분리하라. "
            "internal_goal_phrases 에는 제작자 의견 속 내부 목표 구절을 원문 그대로 넣어라. 항목은 코드로.\n\n정의서:\n" + _dump(rq))


def p_axes(rq: dict[str, Any], classes: dict[str, Any], answers: dict[str, Any]) -> str:
    return ("이 제안의 기획 축 3개(A · B · C)를 만들어라. 축마다 제목(짧게), 한 줄, 담는 항목 코드. 세 축을 합치면 고객 요구 항목이 빠지지 "
            "않게. A 는 사업 서사(Part 1), B 는 이해관계자 가치(Key considerations · 1-3), C 는 공간 경험(Part 2)에 어울리게.\n\n"
            f"정의서:\n{_dump(rq)}\n\n분류:\n{_dump(classes)}\n\n기획 답:\n{_dump(answers)}")


def p_combo(axes: list[dict[str, Any]], rq: dict[str, Any]) -> str:
    return ("세 축을 파트별로 나눠 쓰는 추천 조합의 제목(짧은 컨셉 이름)과 한 줄 설명을 지어라.\n\n축:\n" + _dump(axes)
            + "\n\n정의서 요약:\n" + _dump({"title": rq.get("title"), "customer": rq.get("customer_name")}))


def p_messages(places: list[dict[str, Any]], rq: dict[str, Any], answers: dict[str, Any], kb_msgs: list[str], extra: str | None) -> str:
    return ("자리마다 핵심 메시지(Key Message) 한 문장을 써라. 청중은 기획 질의 2 답 순서(모르면 정의서 최종 제안대상). KB 원문 메시지 문구를 "
            "우선 쓰되 고객 요구에 맞게. 검증 안 된 '최초' 같은 주장 · 삼성 내부 목표는 쓰지 않는다.\n\n"
            f"자리:\n{_dump(places)}\n\n정의서:\n{_dump(rq)}\n\n기획 답:\n{_dump(answers)}\n\nKB 원문 메시지 후보:\n{_dump(kb_msgs)}"
            + (f"\n\n덧붙인 방향: {extra}" if extra else ""))


def p_claim_fix(text: str, claim: str) -> str:
    return (f"다음 문장의 '{claim}'은(는) 출처가 확인되지 않은 주장이다. 고객 문서에 넣을 수 있는 검증 가능한 표현으로 바꿀 구간(span_text, "
            f"문장의 부분 문자열)과 대체안(suggestion), 짧은 이유(note, 예 \"'{claim}'는 아직 검증 전이에요\")를 줘라.\n문장: {text}")


def p_skeleton(volume: int, counts: dict[str, int], direction: dict[str, Any], rq: dict[str, Any], answers: dict[str, Any]) -> str:
    return (f"분량 약 {volume}장 스토리보드의 묶음 이름과 Part 1 · Part 3 섹션 이름을 정하라. Part 1 섹션 {counts['part1']}개, Part 3 섹션 "
            f"{counts['part3']}개(순서대로). 묶음마다 SB3 한 줄 요약(group_summaries)과 Part별 담당(owners)도.\n\n기획 방향:\n{_dump(direction)}"
            f"\n\n정의서:\n{_dump(rq)}\n\n기획 답:\n{_dump(answers)}")


def p_section(section: dict[str, Any], ctx: dict[str, Any]) -> str:
    return ("스토리보드 섹션 하나의 작성 방향(direction, 60자 이내), 본문 줄 2–5개(lines), 제품 · 솔루션 후보(products, KB 후보 안에서), "
            "정하지 못한 이유(tbd_reason — 사람이 고르기 전이면), 추가 논의(discussion_labels)를 써라. 모르는 수치는 [00], 확인 전 내용은 "
            "[확인 필요]. 회의에서 나왔지만 확정 아닌 줄은 reviewing=true.\n\n섹션:\n" + _dump(section) + "\n\n맥락:\n" + _dump(ctx))


def p_spaces(candidates: list[dict[str, Any]], limit: int, ctx: dict[str, Any]) -> str:
    return (f"Part 2 공간 시나리오의 공간 목록(최대 {limit}개)을 정하라. 후보는 정의서 공간 + KB 업종 공간 시퀀스 + 축 C. 정의서에 근거 없는 공간은 "
            "from_rq=false(확장). 칸(action 행위 · trigger 트리거 · response 반응 · exception 예외 · metric 지표)은 근거가 있는 것만 채운다 — "
            "근거가 없으면 비워 둔다(질문으로 채운다).\n\n후보:\n" + _dump(candidates) + "\n\n맥락:\n" + _dump(ctx))


def p_trace(items: list[dict[str, Any]], places: list[dict[str, Any]], ctx: dict[str, Any]) -> str:
    return ("정의서 항목마다 스토리보드에 들어간 곳(places — 자리 키 · space:<키>)과 연결 유형(direct=주제가 보임, interpreted=새 콘셉트로, "
            "extension=요구에 없던 해결안까지, reviewing=논의 중, unconfirmed=담당 항목이 안 보임)을 정하라. 넣을 곳이 없거나 내용이 비면 "
            "problem 과 정리 질문(question — 놓을 곳 후보 최대 2, target 은 자리 키)을, 담당 부서 확인이 필요하면 owner_note 를. "
            "요구에 없던 해결안은 extensions 로, 회의에서 정할 것은 discussions 로. 모든 항목을 정확히 한 번씩.\n\n항목:\n" + _dump(items)
            + "\n\n자리:\n" + _dump(places) + "\n\n맥락:\n" + _dump(ctx))


def p_slot_questions(space: dict[str, Any], empty_slots: list[str], ctx: dict[str, Any]) -> str:
    return ("공간 시나리오의 빈 칸마다 질문 하나(40자 이내)와 선택지 2–4개(짧게, '상황 → 대응' 꼴)를 만들어라. 빈 칸만.\n칸: "
            + ", ".join(empty_slots) + "\n\n공간:\n" + _dump(space) + "\n\n장면 · 제품 맥락:\n" + _dump(ctx))


def p_slot_compose(space: dict[str, Any], answers: dict[str, Any], ctx: dict[str, Any]) -> str:
    return ("공간 시나리오 칸을 답으로 다듬어라. 답에 없던 구간은 ai_added=true 로 따로 나눠라. 모르는 수치는 [00]. 고객에게 받아야 할 것"
            "(운영 데이터 · 혼잡 시간대 등)은 customer_questions(존댓말 질문 · 짧은 이름)로. 제품 후보는 KB 후보 안에서.\n\n공간:\n"
            + _dump(space) + "\n\n칸별 답:\n" + _dump(answers) + "\n\n맥락:\n" + _dump(ctx))


def p_revise(target: dict[str, Any], instruction: str, chips: list[str], settings: dict[str, Any]) -> str:
    return ("스토리보드 섹션을 요청대로 다시 써라. 범위 밖 내용은 건드리지 않는다. reviewing 줄 · [확인 필요] · [00] 은 그대로 두고, 새 수치는 "
            "넣지 않는다. 고친 줄은 원래 id, 새 줄은 id 없이. 그대로 둔 줄은 kept 에 이유와 함께.\n\n요청: " + (instruction or "(없음)")
            + "\n빠른 지시: " + (", ".join(chips) or "(없음)") + "\n설정: " + _dump(settings) + "\n\n섹션:\n" + _dump(target))


def p_sync(changes: list[dict[str, Any]], places: list[dict[str, Any]]) -> str:
    return ("요구사항 정의서가 바뀌었다. 영향받는 자리만 다시 써라(다른 자리는 건드리지 않는다). 자리마다 바뀌기 전 · 후 요약(짧게)과 바뀐 "
            "본문 줄(lines) 또는 공간 칸(slots). [확인 필요] · [00] 은 확인되기 전까지 유지.\n\n정의서 변경:\n" + _dump(changes)
            + "\n\n영향 자리:\n" + _dump(places))


def p_place_item(item: dict[str, Any], target: dict[str, Any]) -> str:
    return ("정의서 항목을 고른 자리에 더하라. 섹션이면 본문 줄(lines_add, 1–2줄), 공간이면 칸 문장(slot_segments). 결과 문구(result_label, "
            "예 \"Part 3에 '설계 반영 체크리스트' 추가\").\n\n항목:\n" + _dump(item) + "\n\n자리:\n" + _dump(target))


def p_mi_topic(sections: list[dict[str, Any]]) -> str:
    return ("확인 필요 수치가 있는 섹션을 보고 Market Intelligence 가 찾을 근거를 한 줄로(예 '성수 성과 수치의 출처 찾기') 정하고, 그 섹션 "
            "코드를 골라라.\n\n섹션:\n" + _dump(sections))
