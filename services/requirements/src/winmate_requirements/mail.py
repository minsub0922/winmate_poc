"""메일 문구(§7.6 rq_mail_draft, 동기) — 체크한 질문만, 키맨별 묶음 · 번호 · 존댓말, 내부 정보 금지.

LLM(`rq.mail_draft`) 출력은 검사한다: 체크한 질문 문장이 모두 있고, 체크하지 않은 질문 · 제작자 의견(5자 이상 겹침) ·
가중치 숫자가 없어야 한다. 아니면(또는 15초 넘거나 실패하면) 템플릿.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from winmate_common.errors import ApiError

from . import domain, llm, repo

log = logging.getLogger("winmate.requirements.mail")
MAIL_TIMEOUT = 15.0


def _norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _grouped(doc: dict[str, Any], qs: list[dict[str, Any]]) -> list[tuple[str | None, list[dict[str, Any]]]]:
    order = {k["id"]: i for i, k in enumerate(domain.keymen(doc))}
    names = {k["id"]: k.get("name") or "" for k in domain.keymen(doc)}
    groups: dict[str | None, list[dict[str, Any]]] = {}
    for q in sorted(qs, key=lambda q: (order.get(q.get("keyman_id") or "", 999), q["created_at"])):
        kid = q.get("keyman_id") if q.get("keyman_id") in names else None
        groups.setdefault(kid, []).append(q)
    return [(names.get(k) if k else None, v) for k, v in groups.items()]


def template(doc: dict[str, Any], qs: list[dict[str, Any]]) -> dict[str, str]:
    cust = domain.field_value(doc, "customer_name")
    proj = domain.field_value(doc, "project_name")
    subject = f"[{cust or '고객사'}] {proj or '제안'} 관련 확인 요청"
    lines = [f"안녕하세요, {cust + ' ' if cust else ''}담당자님.", "", "제안 준비를 위해 몇 가지 여쭙니다.", ""]
    n = 0
    groups = _grouped(doc, qs)
    for name, items in groups:
        if name and len(groups) > 1:
            lines.append(f"[{name}]")
        for q in items:
            n += 1
            lines.append(f"{n}. {q['text']}")
        if len(groups) > 1:
            lines.append("")
    if lines[-1] != "":
        lines.append("")
    lines.append("감사합니다.")
    return {"subject": subject, "body": "\n".join(lines)}


def leaks_internal(doc: dict[str, Any], body: str) -> bool:
    """제작자 의견과 5자 이상 겹치면 누출 — 단 고객에게 보여도 되는 글(프로젝트명 · 고객사 · 질문 · 키맨 · 항목)에도 있는 조각은 뺀다."""
    note = re.sub(r"\s+", "", domain.field_value(doc, "author_note") or "")
    flat = re.sub(r"\s+", "", body)
    public = [domain.field_value(doc, f) or "" for f in ("project_name", "customer_name", "final_audience")]
    public += [q["text"] for q in doc.get("questions") or []] + [k.get("name") or "" for k in domain.keymen(doc)]
    public += [it.get("text") or "" for _, it in domain.all_items(doc)]
    allowed = re.sub(r"\s+", "", " ".join(public))
    for i in range(max(0, len(note) - 4)):
        frag = note[i:i + 5]
        if len(frag) == 5 and frag in flat and frag not in allowed:
            return True
    if "가중치" in body:
        return True
    ks = domain.keymen(doc)
    return len(ks) > 1 and any(re.search(rf"(?<!\d){k.get('weight')}\s*%", body) for k in ks if k.get("weight") is not None)


_NUMBERED = re.compile(r"^\s*\d+\s*[.)]\s*(.+)$")


def valid(doc: dict[str, Any], body: str, chosen: list[dict[str, Any]], others: list[dict[str, Any]]) -> bool:
    """체크한 질문이 모두 있고, 번호 줄이 정확히 그 질문들이며, 다른 질문 · 내부 정보가 없어야 한다."""
    nb = _norm(body)
    if not all(_norm(q["text"]) in nb for q in chosen):
        return False
    if any(_norm(q["text"]) in nb for q in others):
        return False
    numbered = [m.group(1) for line in body.splitlines() if (m := _NUMBERED.match(line))]
    if len(numbered) != len(chosen):
        return False
    texts = [_norm(q["text"]) for q in chosen]
    if not all(any(t in _norm(n) for t in texts) for n in numbered):
        return False
    return not leaks_internal(doc, body)


async def draft(rq_id: str, question_ids: list[str]) -> dict[str, Any]:
    doc = await repo.require_doc(rq_id)
    open_qs = domain.open_questions(doc)
    want = set(question_ids)
    chosen = [q for q in open_qs if q["id"] in want]
    if not chosen:
        raise ApiError(422, "NOTHING_SELECTED", "메일에 넣을 질문을 하나 이상 골라 주세요")
    others = [q for q in open_qs if q["id"] not in want]
    groups = _grouped(doc, chosen)
    lines = []
    n = 0
    for name, items in groups:
        lines.append(f"[{name or '담당자'}]")
        for q in items:
            n += 1
            lines.append(f"{n}. {q['text']}")
    prompt = ("고객 담당자에게 보낼 확인 요청 메일을 정중한 존댓말로 써 주세요. 아래 질문 문장을 그대로 번호와 함께 넣고, 키맨별로 묶으세요. "
              "다른 질문 · 내부 전략 · 가중치 · 제작자 의견은 절대 넣지 마세요.\n"
              f"고객사: {domain.field_value(doc, 'customer_name') or '—'}\n프로젝트: {domain.field_value(doc, 'project_name') or '—'}\n\n"
              + "\n".join(lines))
    try:
        res = await llm.call_json("rq.mail_draft", prompt, llm.RqMailDraft, timeout=MAIL_TIMEOUT)
        subject, body = (res.get("subject") or "").strip(), (res.get("body") or "").strip()
        if subject and body and valid(doc, body, chosen, others) and not leaks_internal(doc, subject):
            return {"subject": subject[:200], "body": body, "generated_by": "llm"}
        log.info("메일 초안 검사 실패 → 템플릿")
    except ApiError as exc:
        log.info("메일 초안 LLM 실패(%s) → 템플릿", exc.code)
    return {**template(doc, chosen), "generated_by": "template"}
