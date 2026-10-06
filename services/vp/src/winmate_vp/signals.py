"""작업 문서 → 플래너 신호(PlannerInput) · VP2 `그 밖에 정한 것` 7행 · 적합도 입력. 결정적.

재료(materials)와 재료 잡이 남긴 사실(facts: KM · RFP 추출 · 견적 · 테마 …)에서 계산한다.
"""
from __future__ import annotations

import re
from typing import Any

from . import catalog, config, coverage, numbers
from .planner import PlannerInput, Theme

REPLACE_WORDS = ("교체", "리뉴얼", "노후", "기존 설비", "바꾸")
JOURNEY_WORDS = ("동선", "관람", "여정", "이동", "투어")
SHORT_WORDS = ("짧게", "한 장", "1장", "한 문장")
TO_BE_WORDS = ("바라는", "원하는", "되도록", "목표", "하고 싶")
QUESTION_RE = re.compile(r"(\?|나요$|까요$|되나$|있나$|할 수 있나)")


def active(doc: dict[str, Any], axis: str | None = None) -> list[dict[str, Any]]:
    return [m for m in doc.get("materials") or [] if not m.get("excluded") and (axis is None or m.get("axis") == axis)]


def facts(doc: dict[str, Any]) -> dict[str, Any]:
    return doc.get("facts") or {}


def products_of(doc: dict[str, Any]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for m in active(doc):
        for r in m.get("product_refs") or []:
            k = f"{r.get('kind')}:{r.get('id')}"
            seen.setdefault(k, r)
    return list(seen.values())


def ef_metrics(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """기대 효과 시트의 지표 — 생성 뒤면 시트 것, 전이면 재료 잡이 만든 후보(facts.metrics)."""
    ef = next((s for s in doc.get("sheets") or [] if s.get("role") == "EF" and s.get("kind", "main") == "main"), None)
    if ef and (ef.get("content") or {}).get("metrics") is not None:
        return ef["content"]["metrics"]
    return list(facts(doc).get("metrics") or [])


def answered_keys(doc: dict[str, Any], kind: str) -> list[str] | None:
    for q in doc.get("questions") or []:
        if q.get("kind") == kind and q.get("status") in ("answered", "defaulted") and q.get("answer"):
            return list(q["answer"].get("keys") or [])
    return None


def open_question(doc: dict[str, Any], kind: str) -> dict[str, Any] | None:
    return next((q for q in doc.get("questions") or [] if q.get("kind") == kind and q.get("status") == "open"), None)


def planner_input(doc: dict[str, Any], *, pack_status: dict[str, str] | None = None) -> PlannerInput:
    f = facts(doc)
    rfp = f.get("rfp") or {}
    quote = f.get("quote") or {}
    ch = active(doc, "challenge")
    va = active(doc, "value")
    sk = active(doc, "stakeholder")
    prods = products_of(doc)
    hard = [p for p in prods if p.get("kind") in ("family", "model", "category")]
    sols = [p for p in prods if p.get("kind") == "solution"]
    top3 = ch[:3]
    tp = (doc.get("target_proposal") or {}).get("type") if doc.get("target_proposal") else None
    pinned = {s["role"]: s["layout"]["code"] for s in doc.get("sheets") or [] if s.get("pinned") and s.get("kind", "main") == "main"}
    pinned.update(doc.get("inherited_pins") or {})
    ind = doc.get("industry") or {}
    code = ind.get("code") if ind.get("code") not in (None, "GEN") else None
    from_customer = [m for m in ch if any(t.get("tag") in ("RFP",) for t in m.get("sources") or []) and m.get("state") != "inferred"]
    meeting = [m for m in ch if any((t.get("locator") or "").startswith("회의록") for t in m.get("sources") or [])]
    note = doc.get("note") or ""
    approvers = [m for m in sk if m.get("approver")]
    dms = list(rfp.get("decision_makers") or [])
    keymen = list(f.get("keymen") or [])
    dm_labels = [d.get("role", "") for d in dms] or [k.get("name", "") for k in keymen]
    kpis = {(d.get("kpi") or "").strip() for d in dms if (d.get("kpi") or "").strip()}
    distinct = len(kpis) >= 2 or (not dms and len(keymen) >= 3 and all(k.get("items") for k in keymen))
    econ_words = config.routing().get("economic_words") or []
    econ = sum(int(c.get("points") or 0) for c in rfp.get("evaluation_criteria") or []
               if any(w in (c.get("name") or "") for w in econ_words))
    econ_label = f"RFP {next((c.get('name') for c in rfp.get('evaluation_criteria') or [] if any(w in (c.get('name') or '') for w in econ_words)), '경제성')} {econ}점" if econ else ""
    metrics = ef_metrics(doc)
    proj = [numbers.projected_usable(m) for m in metrics if numbers.metric_status(m) != "excluded"]
    usable = sum(1 for p in proj if p)
    est = sum(1 for p in proj if p == "estimated")
    per_product = len(hard) >= 2 and bool(f.get("per_product_numbers"))
    real_ch = [m for m in ch if m.get("state") != "inferred"]
    replacement = any(any(w in (m.get("text") or "") for w in REPLACE_WORDS) for m in real_ch) or bool(rfp.get("replacement"))
    spaces = list(f.get("spaces") or [])
    journey = len(spaces) if any(any(w in (m.get("text") or "") for w in JOURNEY_WORDS) for m in active(doc)) or f.get("journey") else 0
    fq = sum(1 for m in ch if QUESTION_RE.search((m.get("text") or "").strip()))
    memo_only = not [s for s in doc.get("sources") or [] if s.get("connected")] and not doc.get("attachments") and bool(note.strip())
    themes = [Theme(**t) for t in f.get("themes") or []]
    dir_ans = answered_keys(doc, "direction")
    appr = answered_keys(doc, "approver")
    main_product = (hard or sols or [{}])[0].get("name", "")
    has_quote = bool(quote.get("total"))
    return PlannerInput(
        target_type=tp,
        pinned=pinned,
        industry_code=code,
        pack_ready=bool(code and (pack_status or {}).get(code) == "ready"),
        has_customer_challenges=bool(from_customer or meeting or (rfp.get("challenges"))),
        challenge_source_label="회의록" if meeting and not from_customer else "RFP",
        challenge_count=len(ch),
        cost_challenges=sum(1 for m in top3 if m.get("cost")),
        to_be_clear=bool(rfp.get("to_be")) or any(any(w in (m.get("text") or "") for w in TO_BE_WORDS) for m in real_ch
                                                  if any(t.get("tag") in ("RQ", "RFP") for t in m.get("sources") or [])),
        repeated_symptom=any(len({t.get("tag") for t in m.get("sources") or []}) >= 2 for m in ch),
        km_count=int(f.get("km_count") or 0),
        approvers_known=len(approvers),
        approvers_confirmed=len(appr) if appr is not None else 0,
        approver_labels=[m.get("text", "") for m in approvers],
        short_requested=any(w in note for w in SHORT_WORDS),
        decision_makers=max(len(dms), len(keymen)),
        decision_maker_labels=[x for x in dm_labels if x][:6],
        distinct_kpi=distinct,
        economic_points=econ,
        economic_label=econ_label,
        investment_available=has_quote,
        investment_source=(quote.get("source") or "attached") if has_quote else None,
        investment_label=quote.get("version_label") or "견적",
        usable_numbers=usable,
        estimated_numbers=est,
        per_product_numbers=per_product,
        product_count=len(hard) + len(sols),
        single_product_feature=len(hard) == 1 and not sols and len(va) >= 3,
        solution_screen_focus=bool(sols) and not hard,
        space_journey_count=journey,
        replacement=replacement,
        field_questions=fq,
        no_image=False,
        memo_only=memo_only,
        clone=doc.get("start") == "clone",
        stakeholder_count=len(sk),
        stakeholder_labels=[m.get("text", "") for m in sk][:4],
        themes=themes,
        direction_open=open_question(doc, "direction") is not None,
        direction_answer=(dir_ans[0] if dir_ans else None),
        overrides=dict(doc.get("plan_overrides") or {}),
        main_product=main_product,
    )


def fit_features(doc: dict[str, Any]) -> dict[str, Any]:
    p = planner_input(doc)
    f = facts(doc)
    slots = doc.get("image_slots") or []
    return {
        "km": p.km_count, "values": len(active(doc, "value")), "challenges": p.challenge_count, "products": p.product_count,
        "stakeholders": max(p.stakeholder_count, p.decision_makers), "stakeholder_kpis": p.distinct_kpi or p.approvers_confirmed >= 2,
        "pairs": p.challenge_count >= 2 and p.challenge_count == p.product_count, "field_questions": p.field_questions,
        "single_product": p.product_count == 1, "solution_screen": p.solution_screen_focus, "spaces": p.space_journey_count,
        "replacement": p.replacement, "numbers": p.usable_numbers, "per_product_numbers": p.per_product_numbers,
        "investment": p.investment_available, "economic": p.economic_points > 0,
        "official_cuts": sum(1 for s in slots if s.get("tier") == "cut"), "same_vertical_case": bool(f.get("same_vertical_case")),
        "customer_photo": any(a.get("kind") == "customer_photo" for a in doc.get("attachments") or []),
        "to_be": p.to_be_clear, "repeated": p.repeated_symptom, "cost_challenges": p.cost_challenges,
        "message_one": p.km_count == 1 or p.target_type == "quickwin", "evidence": len(active(doc, "evidence")),
        "qualitative": True,
    }


def decision_rows(doc: dict[str, Any], plan: dict[str, Any], p: PlannerInput) -> list[dict[str, Any]]:
    """VP2 `그 밖에 정한 것` — 키는 고정 목록(이 순서): 업종 · 업종 레이아웃 · 이해관계자형 · 시트 수 · 추정 값 · 이미지 · 톤."""
    ind = doc.get("industry") or {}
    f = facts(doc)
    rows: list[dict[str, Any]] = []
    name = ind.get("name") or "범용"
    src = ind.get("source")
    if ind.get("mode") == "pin":
        why = "직접 고른 업종"
    elif src in ("mi", "storyboard", "proposal", "requirements", "vp") and ind.get("inherited_from"):
        why = f"연결한 {ind['inherited_from']}에서 상속"
    elif ind.get("code") == "GEN":
        why = "16개 업종 밖 — 범용으로"
    else:
        why = f"자동 판별 · 확신 {float(ind.get('confidence') or 0):.2f}" if ind.get("confidence") is not None else "자동 판별"
    rows.append({"key": "업종", "value": name, "why": why, "mode": ind.get("mode") or "auto"})
    n = len(plan.get("sheets") or [])
    if ind.get("code") and ind.get("code") != "GEN":
        if p.pack_ready:
            rows.append({"key": "업종 레이아웃", "value": f"업종판 (VP-{ind['code']})", "why": "업종판이 준비돼 업종 레이아웃을 먼저 골랐어요", "mode": "auto"})
        else:
            rows.append({"key": "업종 레이아웃", "value": f"범용 (VP-{ind['code']} 제작 중)", "why": f"업종판이 나오면 {n}장을 바꿀지 물어볼게요", "mode": "auto"})
    else:
        rows.append({"key": "업종 레이아웃", "value": "범용", "why": "범용 35종 · 이미지판 기본 · 공식 실사 우선", "mode": "auto"})
    vp_sheet = next((s for s in plan.get("sheets") or [] if s["role"] == "VP"), None)
    uses_h = bool(vp_sheet and vp_sheet["layout"]["code"] in ("VP-H", "VP-D"))
    if uses_h:
        rows.append({"key": "이해관계자형", "value": "씀 — " + catalog.display(vp_sheet["layout"]["code"]),
                     "why": f"의사결정자 {max(p.decision_makers, p.approvers_confirmed)} — " + " · ".join(p.decision_maker_labels[:4] or p.stakeholder_labels[:4]),
                     "mode": "auto"})
    else:
        ap = p.approver_labels[:1]
        src_label = "RFP" if (f.get("rfp") or {}).get("decision_makers") else "자료"
        why = f"결재자 {max(1, p.approvers_known)} — {ap[0]} ({src_label})" if ap else "결재자 1 — 업종 기본값"
        rows.append({"key": "이해관계자형", "value": "쓰지 않음", "why": why, "mode": "auto"})
    tp = p.target_type
    why = {"standard": "표준 제안서 Value Props 기본 구성", "quickwin": "퀵윈 제안서 — 가치 제안 1장",
           "solution": "Solution형 — 고객 과제 생략"}.get(tp or "", "연결 없음 — 3장 기본 · 보낼 때 줄이기")
    rows.append({"key": "시트 수", "value": f"{n}장", "why": why, "mode": "auto"})
    metrics = ef_metrics(doc)
    est = [m for m in metrics if numbers.projected_usable(m) == "estimated"]
    if est:
        basis = next((m.get("estimate_note") for m in est if m.get("estimate_note")), None) or "사례 범위"
        rows.append({"key": "추정 값", "value": f"{len(est)}개 · '{est[0]['label']}'" if len(est) == 1 else f"{len(est)}개",
                     "why": f"{basis}로 넣고 [추정] 표시", "mode": "check"})
    else:
        rows.append({"key": "추정 값", "value": "없음", "why": "추정 없이 확보한 수치만 써요", "mode": "auto"})
    no_img = vp_sheet and not catalog.has_images(vp_sheet["layout"]["code"])
    rows.append({"key": "이미지", "value": "이미지 없이" if no_img else "공식 실사 우선",
                 "why": "제품 이미지 없이 글로만 보여 줘요" if no_img else "기둥마다 그 가치를 만드는 제품 · 솔루션 → 삼성 공식 컷 · 화면 → 없으면 일러스트",
                 "mode": "auto"})
    comp = (f.get("rfp") or {}).get("competitor_mentions") or []
    no_comp_note = "경쟁사" in (doc.get("note") or "") and ("빼" in (doc.get("note") or "") or "없이" in (doc.get("note") or ""))
    if comp and not no_comp_note:
        rows.append({"key": "톤", "value": "고객사명 사용 · 경쟁사 익명", "why": "RFP가 경쟁 비교를 요청해요 — 이름은 익명으로", "mode": "check"})
    else:
        rows.append({"key": "톤", "value": "고객사명 사용 · 경쟁사 언급 없음",
                     "why": "메모에 경쟁사 이야기는 빼 달라고 했어요" if no_comp_note else "RFP에 경쟁 비교 요청이 없어요", "mode": "auto"})
    return rows


def plan_intro(doc: dict[str, Any], plan: dict[str, Any]) -> str:
    n = len(plan.get("sheets") or [])
    tp = (doc.get("target_proposal") or {}).get("type") if doc.get("target_proposal") else None
    label = {"standard": "표준", "quickwin": "퀵윈", "solution": "Solution형"}.get(tp or "")
    head = "재료를 보고 메시지 구조와 시트를 정했어요. "
    if label:
        return head + f"{label} 제안서 Value Props 섹션에 맞춘 {n}장이고, 바꾸고 싶은 것만 고르면 됩니다."
    return head + f"{n}장 기본이고, 바꾸고 싶은 것만 고르면 됩니다."


def coverage_of(doc: dict[str, Any]) -> list[dict[str, Any]]:
    f = facts(doc)
    items = doc.get("materials") or []
    if not items:
        items = f.get("preview_materials") or []
        f = {**f, **(f.get("preview_facts") or {})}
    note = doc.get("note") or ""
    memo_only = not [s for s in doc.get("sources") or [] if s.get("connected")] and not doc.get("attachments") and bool(note.strip())
    return coverage.compute(items, km_count=int(f.get("km_count") or 0), strengths=int(f.get("strengths") or 0),
                            mi_users=list(f.get("mi_users") or []), memo_only=memo_only)
