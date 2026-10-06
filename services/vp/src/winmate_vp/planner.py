"""플래너 — 메시지 구조 · 시트 · 레이아웃을 정하는 결정적 순수 함수(05-vp.md §3.5 · §7.3).

입력 `PlannerInput`(재료에서 뽑은 신호) → `Plan`(flow · 시트 · 대안 · CTA · 결정). LLM 없음.
위에서 첫 번째로 맞는 행을 고른다. 고정한 시트는 건너뛴다(pin). 업종판이 준비된 업종이면 업종판을 먼저 쓴다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import catalog, config

ROLES = ("CH", "VP", "EF")
STEP_LABEL = {"CH": "고객 과제", "VP": "가치 제안", "EF": "기대 효과"}


@dataclass
class Theme:
    key: str
    label: str
    kind: str = "gain"   # gain(매출 · 성장) | cost(비용 · 과제)
    score: float = 0.0


@dataclass
class PlannerInput:
    target_type: str | None = None             # standard | quickwin | solution | None(연결 없음)
    pinned: dict[str, str] = field(default_factory=dict)   # 역할 → 고정한 레이아웃 코드
    industry_code: str | None = None           # 16 업종 코드(없으면 범용)
    pack_ready: bool = False
    has_customer_challenges: bool = False      # RFP · 회의록이 과제를 직접 말함
    challenge_source_label: str = "RFP"        # 이유 문장(RFP · 회의록)
    challenge_count: int = 0
    cost_challenges: int = 0                   # 상위 과제 3개 중 비용 수치가 붙은 수
    to_be_clear: bool = False
    repeated_symptom: bool = False
    km_count: int = 0
    approvers_known: int = 0                   # RFP · 정의서 · Storyboard 에서 아는 결재자 수
    approvers_confirmed: int = 0               # VP1Q 에서 사용자가 확인한 결재자 수
    approver_labels: list[str] = field(default_factory=list)
    short_requested: bool = False              # 메모 `짧게` · `한 장`
    decision_makers: int = 0                   # 추론한 의사결정자 수
    decision_maker_labels: list[str] = field(default_factory=list)
    distinct_kpi: bool = False
    economic_points: int = 0
    economic_label: str = ""                   # `RFP 경제성 20점`
    investment_available: bool = False
    investment_source: str | None = None       # attached(견적 첨부) | linked(연결된 견적) | rfp
    investment_label: str = "견적"
    usable_numbers: int = 0                    # 쓸 수 있는 전 → 후 수치(확보 + 추정)
    estimated_numbers: int = 0
    per_product_numbers: bool = False
    product_count: int = 0
    single_product_feature: bool = False
    solution_screen_focus: bool = False
    space_journey_count: int = 0
    replacement: bool = False
    field_questions: int = 0
    no_image: bool = False
    memo_only: bool = False
    clone: bool = False
    stakeholder_count: int = 0                 # 이해관계자 재료 수(VP-H 전제)
    stakeholder_labels: list[str] = field(default_factory=list)
    themes: list[Theme] = field(default_factory=list)   # 방향 테마(1 · 2위)
    direction_open: bool = False               # 방향 질문이 열려 있음(답 없음)
    direction_answer: str | None = None        # gain(매출 먼저) | cost(비용 먼저) | both(둘 다)
    overrides: dict[str, str] = field(default_factory=dict)   # {VP: 'VP-G', EF: 'EF-B', CH: …}(VP2 대안 · 구조 요청)
    main_product: str = ""                     # 대표 제품 이름(대안 툴팁)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PlannerInput":
        kw = dict(d)
        kw["themes"] = [t if isinstance(t, Theme) else Theme(**t) for t in kw.get("themes") or []]
        allowed = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in kw.items() if k in allowed})


def _decision(stage: int, key: str, value: str, why: str, mode: str, text: str) -> dict[str, Any]:
    return {"stage": stage, "key": key, "value": value, "why": why, "mode": mode, "text": text}


def multi_dm(p: PlannerInput) -> bool:
    """VP-H 조건 — 사용자가 확인한 결재자 2명 이상 또는 추론한 의사결정자 3명 이상 · KPI가 다름(§11 Q3)."""
    return p.approvers_confirmed >= int(config.th("stakeholders_min")) or (
        p.decision_makers >= int(config.th("decision_makers_min")) and p.distinct_kpi)


def pairs_1to1(p: PlannerInput) -> bool:
    return p.challenge_count >= 2 and p.challenge_count == p.product_count


def one_liner(p: PlannerInput) -> bool:
    return p.target_type == "quickwin" or p.km_count == 1 or (p.approvers_known == 1 and p.short_requested)


def flow_of(p: PlannerInput) -> tuple[str, str]:
    """메시지 구조(§3.5 flow 표) — (key, flow_label)."""
    if p.direction_open:
        return "direction", "방향 두 갈래"
    if p.clone and p.pinned:
        return "inherit", "상속 · 고객명만 교체"
    if one_liner(p):
        return "one_liner", "한 문장 + 제품 사진"
    if p.target_type == "solution" and (multi_dm(p) or p.decision_makers >= 2):
        return "stakeholder_roi", "이해관계자 + 투자 회수"
    if multi_dm(p):
        return "stakeholder", "이해관계자형"
    if pairs_1to1(p):
        return "pairs", "과제 ↔ 제품 1:1"
    if p.replacement and p.economic_points > 0:
        return "renewal", "리뉴얼 전 → 후 · 투자 회수"
    if p.single_product_feature:
        return "product", "제품 1대 · 기능 → 가치"
    if p.space_journey_count >= int(config.th("spaces_journey_min")):
        return "journey", "공간 · 관람 동선 → 가치"
    if p.memo_only:
        return "inferred", "과제 추론 → 가치"
    return "standard", "과제 → 가치 → 효과"


def _ch(p: PlannerInput, decisions: list[dict[str, Any]]) -> tuple[str | None, str, str, str]:
    """(코드 | None, 이유, 모드, 칩 꼬리)."""
    if p.target_type == "solution":
        decisions.append(_decision(4, "고객 과제", "생략", "대규모 MI가 이미 말함", "auto",
                                   "Solution형 → 고객 과제 시트 생략 (대규모 MI가 이미 말함)"))
        return None, "대규모 MI가 과제를 말함", "auto", ""
    if p.challenge_count <= 0:
        decisions.append(_decision(4, "고객 과제", "생략", "과제 재료 없음", "auto", "과제 재료 없음 → 고객 과제 시트 생략"))
        return None, "과제 재료 없음", "auto", ""
    if p.direction_answer == "cost":
        return "CH-A", f"{_theme_label(p, 'cost')}을 먼저 말하기로 했어요", "auto", ""
    top = min(3, p.challenge_count)
    if p.cost_challenges >= int(config.th("cost_challenges_min")):
        why = f"과제 {top}개 모두 비용 수치가 있어요" if p.cost_challenges >= top else f"과제 {p.cost_challenges}개에 비용 수치가 있어요"
        return "CH-A", why, "auto", ""
    if p.to_be_clear:
        return "CH-B", "요구사항에 바라는 운영 모습이 적혀 있어요", "auto", ""
    if p.repeated_symptom:
        return "CH-C", "같은 증상이 여러 자료에서 반복돼요", "auto", ""
    if p.memo_only:
        return "CH-A", "메모와 사례 DB로 추론한 과제예요", "check", "추론"
    return "CH-A", f"과제 {top}개 · 영향을 함께 보여 줘요", "auto", ""


def _vp(p: PlannerInput, decisions: list[dict[str, Any]]) -> tuple[str, str, str]:
    """(코드, 이유, 모드)."""
    km_max = int(config.th("km_max"))
    if p.km_count > km_max:
        decisions.append(_decision(3, "Key Message", f"{p.km_count} → {km_max}", "기둥은 4개까지", "check",
                                   f"Key Message {p.km_count} → {km_max}로 묶음"))
    if p.direction_answer == "gain":
        return "VP-F3", f"{_theme_label(p, 'gain')}을 먼저 말하기로 했어요", "auto"
    if p.direction_answer == "cost":
        return "VP-E", "과제마다 제품을 짝지어요", "auto"
    if p.direction_answer == "both":
        return "VP-F2", "두 방향을 나란히 보여 줘요", "auto"
    if one_liner(p):
        if p.target_type == "quickwin":
            return "VP-G", "퀵윈 제안서라 한 문장 + 제품 사진 1장", "auto"
        if p.km_count == 1:
            return "VP-G", "Key Message 1개 → 한 문장 + 제품 사진", "auto"
        return "VP-G", "결재자 1명 · 짧게 → 한 문장 + 제품 사진", "auto"
    if multi_dm(p):
        n = max(p.approvers_confirmed, p.decision_makers)
        names = " · ".join(p.decision_maker_labels[:4])
        decisions.append(_decision(3, "이해관계자형", "VP-H", f"의사결정자 {n}", "auto",
                                   f"의사결정자 {n}{f' ({names})' if names else ''} → VP-H"))
        return "VP-H", f"의사결정자 {n} · KPI가 달라요", "auto"
    if pairs_1to1(p):
        return "VP-E", f"과제 {p.challenge_count} = 제품 {p.product_count} → 1:1로 짝지어요", "auto"
    if p.field_questions >= int(config.th("field_questions_min")):
        return "VP-U", f"고객의 질문 · 요구가 {p.field_questions}개예요", "auto"
    if p.single_product_feature:
        return "VP-I", "제품 1대의 기능이 핵심이에요", "auto"
    if p.solution_screen_focus:
        return "VP-J", "솔루션 화면이 핵심이에요", "auto"
    if p.space_journey_count >= int(config.th("spaces_journey_min")):
        return "VP-K", f"공간 {p.space_journey_count}곳 · 손님 동선", "auto"
    if p.replacement:
        return "VP-L", "기존 설비를 교체해요", "auto"
    if p.product_count >= int(config.th("products_matrix")):
        return "VP-M", f"제안 제품이 {p.product_count}개예요", "auto"
    if 2 <= p.km_count <= km_max:
        return f"VP-F{p.km_count}", f"Key Message {p.km_count} → 기둥 {p.km_count} + 제품", "auto"
    if p.km_count > km_max:
        return f"VP-F{km_max}", f"Key Message {p.km_count} → {km_max}로 묶음", "check"
    return "VP-F3", "가치 기둥 3 + 제품", "auto"


def _ef(p: PlannerInput, decisions: list[dict[str, Any]]) -> tuple[str, str, str, str]:
    """(코드, 이유, 모드, 칩 꼬리)."""
    nmin = int(config.th("numbers_min"))
    wants_roi = p.economic_points > 0 or p.overrides.get("EF") == "EF-B"
    if wants_roi:
        if p.investment_available:
            if p.economic_points > 0:
                label = p.economic_label or f"평가 기준 경제성 {p.economic_points}점"
                decisions.append(_decision(3, "기대 효과", "EF-B", label, "auto", f"{label} → 기대 효과는 투자 회수 EF-B"))
            if p.investment_source == "linked":
                decisions.append(_decision(6, "투자비", p.investment_label, "투자비 없음", "check",
                                           f"투자비 없음 → 연결된 {p.investment_label}로 계산"))
            return "EF-B", "투자비 + 절감액 범위로 회수 기간", "auto", ""
        decisions.append(_decision(6, "투자비", "견적 없음", "투자 회수가 필요한데 투자비가 없음", "check",
                                   "투자비 없음 → 견적 연결 요청 · 없으면 EF-A로"))
    if p.per_product_numbers:
        return "EF-D", "제안 제품마다 전 → 후 수치가 있어요", "auto", ""
    if p.usable_numbers >= nmin:
        return "EF-A", f"전 → 후 수치 {p.usable_numbers}개 확보", "auto", ""
    tail = "추정" if p.memo_only else ""
    if p.usable_numbers >= 1:
        return "EF-C", f"수치 {p.usable_numbers}개 + 체감 효과", "auto", tail
    return "EF-C", "수치 없음 → 업종 평균 범위로 채워요", "auto", tail or "업종 평균"


def _theme_label(p: PlannerInput, kind: str) -> str:
    t = next((t for t in p.themes if t.kind == kind), None)
    return t.label if t else ("매출" if kind == "gain" else "비용")


def direction_previews(p: PlannerInput) -> list[dict[str, Any]]:
    """VP1Q 질문 1 선택지 미리보기 — 플래너를 그 답으로 미리 돌린 결과(결정적)."""
    out = []
    for key in ("gain", "cost", "both"):
        q = PlannerInput(**{**p.__dict__, "direction_open": False, "direction_answer": key})
        plan = plan_of(q)
        vp = next((s for s in plan["sheets"] if s["role"] == "VP"), None)
        ch = next((s for s in plan["sheets"] if s["role"] == "CH"), None)
        vp_code = vp["layout"]["code"] if vp else "VP-F3"
        if key == "gain":
            code = catalog.display(vp_code)
            effect = f"{_theme_label(p, 'gain')} 기둥 2 + 운영 기둥 1"
        elif key == "cost":
            code = f"{catalog.display(ch['layout']['code'])} + {catalog.display(vp_code)}" if ch else catalog.display(vp_code)
            k = max(1, min(3, p.challenge_count or 3, p.product_count or 3))
            effect = f"과제 {k} ↔ 제품 {k}으로 짝지어요"
        else:
            ef = next((s for s in plan["sheets"] if s["role"] == "EF"), None)
            code = catalog.display(vp_code)
            effect = f"기둥 2개 · 기대 효과 {catalog.display(ef['layout']['code'])}" if ef else "기둥 2개"
        out.append({"key": key, "code": code, "display": code, "thumb": catalog.thumb(vp_code), "effect": effect,
                    "layout_code": vp_code})
    return out


def direction_chip(p: PlannerInput) -> str:
    """방향 미해결 칩 — `답에 따라 VP-F·2 또는 ·3`(추천 답의 가치 제안 코드 + 같은 계열의 다른 답)."""
    prev = direction_previews(p)
    rec = next((x for x in prev if x["key"] == "both"), prev[-1])
    head = rec["layout_code"][:4]
    label = "답에 따라 " + catalog.display(rec["layout_code"])
    seen = {rec["layout_code"]}
    for o in prev:
        lc = o["layout_code"]
        if lc in seen or not lc.startswith(head):
            continue
        seen.add(lc)
        d = catalog.display(lc)
        label += f" 또는 ·{d.split('·', 1)[1]}" if "·" in d else f" 또는 {d}"
    return label


def _alternatives(p: PlannerInput, sheets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cur = {s["role"]: s["layout"]["code"] for s in sheets}
    vp_code = cur.get("VP", "VP-F3")
    prod = p.main_product or "제품"
    people = " · ".join(p.stakeholder_labels[:3]) or "결재자 · 운영 · 이용자"
    n = catalog.pillars_of(vp_code) or 3
    no_img = catalog.no_image(vp_code)
    cands = [
        {"code": "VP-G", "label": "한 문장형", "tip": f"경영진 결재용 1장 — {prod} 사진과 근거 3 · 과제 · 효과 시트는 부록으로", "role": "VP"},
        {"code": "VP-H", "label": "이해관계자형", "tip": f"{people}에게 각각 다른 가치 — 각자 쓰는 제품과 함께", "role": "VP",
         "prerequisite": "stakeholders" if p.stakeholder_count < 2 else None},
        {"code": no_img if no_img != vp_code else f"VP-B{n}", "label": "이미지 없이",
         "tip": f"같은 기둥 {n}개 · 제품 이미지만 빼요" if no_img.startswith("VP-B") else "같은 구성 · 제품 이미지만 빼요", "role": "VP"},
        {"code": "EF-B", "label": "투자 회수", "role": "EF",
         "tip": (f"{p.investment_label} 기준으로 투자 회수 기간을 계산해요" if p.investment_available
                 else "견적이 연결돼야 해요 — 연결하면 바로 바뀝니다"),
         "prerequisite": None if p.investment_available else "quote"},
    ]
    out = []
    for c in cands:
        if cur.get(c["role"]) == catalog.norm(c["code"]) or (c["role"] == "VP" and "VP" in p.pinned) or (c["role"] == "EF" and "EF" in p.pinned):
            continue
        if c["role"] == "EF" and "EF" not in cur:
            continue
        out.append({"code": catalog.norm(c["code"]), "display": catalog.display(c["code"]), "label": c["label"], "tip": c["tip"],
                    "role": c["role"], "prerequisite": c.get("prerequisite")})
    return out[:4]


def cta_label(n: int) -> str:
    m = max(1, round(n * int(config.th("seconds_per_sheet")) / 60))
    return f"{n}장 만들기 (약 {m}분)"


def _reason(p: PlannerInput, flow: str, first_role: str | None) -> str:
    first = STEP_LABEL.get(first_role or "VP", "가치 제안")
    if flow == "direction":
        return "방향이 두 갈래라 답을 듣고 정해요"
    if flow == "inherit":
        return "복제한 작업이라 고정한 시트는 그대로 두고 나머지만 다시 골라요"
    if flow == "one_liner":
        if p.target_type == "quickwin":
            return "퀵윈 제안서라서 가치 제안 1장으로 시작해요"
        if p.km_count == 1:
            return "Key Message가 1개라서 한 문장으로 시작해요"
        return "결재자 1명 · 짧게라서 한 문장으로 시작해요"
    if flow == "stakeholder_roi":
        return f"Solution형 · 의사결정자 {max(p.decision_makers, p.approvers_confirmed)}명이라서 {first}부터 시작해요"
    if flow == "stakeholder":
        return f"의사결정자마다 KPI가 달라서 {first}부터 시작해요"
    if flow == "pairs":
        return f"과제와 제품이 1:1로 맞아서 {first}부터 시작해요"
    if flow == "renewal":
        return f"기존 설비 교체 · 경제성 배점이 있어서 {first}부터 시작해요"
    if flow == "product":
        return f"제품 1대의 기능이 핵심이라서 {first}부터 시작해요"
    if flow == "journey":
        return f"공간 {p.space_journey_count}곳의 동선이 있어서 {first}부터 시작해요"
    if flow == "inferred":
        return "한 줄 메모뿐이라서 사례 DB로 추론한 과제부터 시작해요"
    if p.has_customer_challenges and first_role == "CH":
        return f"{p.challenge_source_label}가 과제를 직접 말하고 있어 과제부터 시작해요"
    return "재료에서 찾은 과제부터 시작해요" if first_role == "CH" else f"{first}부터 시작해요"


def plan_of(p: PlannerInput) -> dict[str, Any]:
    """Plan(§5.2) + decisions + chips(VP0 · VPC 칩)."""
    decisions: list[dict[str, Any]] = []
    flow, flow_label = flow_of(p)
    pack_ok = bool(p.pack_ready and p.industry_code and p.industry_code != "GEN")
    roles: list[str]
    if p.target_type == "quickwin":
        roles = ["VP"]
        decisions.append(_decision(4, "시트 수", "1장", "퀵윈 제안서", "auto", "퀵윈 제안서 → 가치 제안 1장 (VP-G)"))
    else:
        roles = ["CH", "VP", "EF"]
    sheets: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    chips: list[dict[str, Any]] = []
    for role in roles:
        tail = ""
        if role in p.pinned:
            code = catalog.norm(p.pinned[role])
            why, mode, chosen = "사람이 정한 레이아웃이에요", "pin", "user"
            chip = {"t": f"{catalog.display(code)} 고정", "kind": "pinned"}
        else:
            if role == "CH":
                code, why, mode, tail = _ch(p, decisions)
                if code is None:
                    omitted.append({"role": "CH", "label": "고객 과제 생략", "why": why})
                    if p.target_type == "solution":
                        chips.append({"t": "고객 과제 생략", "kind": "text"})
                    continue
            elif role == "VP":
                code, why, mode = _vp(p, decisions)
            else:
                code, why, mode, tail = _ef(p, decisions)
            chosen = "agent"
            ov = p.overrides.get(role)
            if ov and not (role == "EF" and catalog.norm(ov) == "EF-B" and not p.investment_available):
                code, why, mode, chosen, tail = catalog.norm(ov), "직접 고른 구조예요", "pin", "user", ""
            elif p.no_image and role == "VP":
                code = catalog.no_image(code)
                why = "이미지 없이 — " + why
            if p.clone and role not in p.pinned and p.pinned:
                tail = "다시 고름"
            if pack_ok and chosen == "agent":
                code = catalog.pack_code(p.industry_code or "", role)
                why = "업종판 준비됨 → 업종 레이아웃을 먼저"
                tail = ""
            chip = {"t": catalog.chip_text(code, tail), "kind": "pack" if catalog.is_pack(code) else "code"}
        pick = catalog.pick(code, why=why, chosen_by=chosen, pinned=role in p.pinned)
        sheets.append({"role": role, "step_label": STEP_LABEL[role], "layout": pick, "content_preview": "", "mode": mode,
                       "chip": chip["t"], "tail": tail})
        chips.append(chip)
    if p.direction_open:
        chips = [{"t": direction_chip(p), "kind": "text"}]
    if pack_ok:
        decisions.insert(0, _decision(2, "업종 레이아웃", f"업종판 VP-{p.industry_code}", "업종판 준비됨", "auto",
                                      f"VP-{p.industry_code} 업종판 준비됨 → 업종 레이아웃으로"))
    first_role = sheets[0]["role"] if sheets else None
    n = len(sheets)
    return {
        "flow": flow, "flow_label": flow_label, "reason": _reason(p, flow, first_role), "sheets": sheets, "omitted": omitted,
        "alternatives": _alternatives(p, sheets), "cta_label": cta_label(max(1, n)), "decisions": decisions, "chips": chips,
    }
