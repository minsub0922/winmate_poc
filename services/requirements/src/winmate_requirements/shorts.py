"""항목 short(≤ 24자) · 정의서 short_title(≤ 30자) — LLM `rq.short`(§7.1 rq_short_texts).

- 저장 때 `ensure_shorts()` 로 빠진 것만 동기로 채운다(실패해도 저장은 계속).
- 작업본에서 항목 문장이 바뀌면 `maybe_enqueue()` 가 `rq.short` 잡을 30초에 한 번 넣는다.
- LLM 결과는 항목 문장과 맞춰(비슷도) 붙인다 — 엉뚱한 항목에 짧은 이름이 붙지 않게.
"""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.jobs import JobContext, jobs

from . import domain, llm, repo
from .textutil import best_match, clip, relevance

log = logging.getLogger("winmate.requirements.shorts")


def needs(doc: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    items = [it for _, it in domain.all_items(doc) if (it.get("text") or "").strip() and not domain.short_is_current(it)]
    basis = [domain.field_value(doc, "customer_name"), domain.field_value(doc, "project_name")]
    need_title = bool(basis[0] and basis[1]) and (not doc.get("short_title") or doc.get("short_title_basis") != basis)
    return items, need_title


async def compute(doc: dict[str, Any], *, timeout: float = 60.0) -> tuple[dict[str, tuple[str, str]], str | None, list[Any]]:
    """→ ({item_id: (short, 원문)}, short_title, basis). 실패는 ApiError."""
    items, need_title = needs(doc)
    basis = [domain.field_value(doc, "customer_name"), domain.field_value(doc, "project_name")]
    if not items and not need_title:
        return {}, None, basis
    lines = [f"{i + 1}. [{it['code']}] {it['text']}" for i, it in enumerate(items)]
    prompt = (
        "요구사항 항목마다 24자 이내의 짧은 이름(short)을 만들어 주세요. 원문 낱말을 살리고 새 사실 · 숫자를 넣지 마세요.\n"
        + ("정의서 제목(short_title)도 30자 이내로 '고객사 + 사업 약칭' 꼴로 만들어 주세요.\n" if need_title else "short_title 은 비워 두세요.\n")
        + f"고객사: {basis[0] or '—'}\n프로젝트명: {basis[1] or '—'}\n\n항목:\n" + ("\n".join(lines) if lines else "(없음)")
        + "\n\n각 항목은 code 와 text(원문 그대로)를 함께 돌려주세요."
    )
    res = await llm.call_json("rq.short", prompt, llm.RqShort, timeout=timeout)
    cands = [(it["id"], it["text"]) for it in items]
    by_code = {it["code"]: it for it in items}
    out: dict[str, tuple[str, str]] = {}
    for row in res.get("items") or []:
        iid = best_match(row.get("text"), cands)
        if iid is None and row.get("code") in by_code and relevance(row.get("short"), by_code[row["code"]]["text"]) >= 0.5:
            iid = by_code[row["code"]]["id"]
        if iid is None:
            continue
        src = next(it for it in items if it["id"] == iid)
        short = clip(row.get("short"), 24)
        if short and relevance(short, src["text"]) >= 0.4:
            out[iid] = (short, src["text"])
    title = None
    if need_title and res.get("short_title"):
        cand = clip(res["short_title"], 30)
        if relevance(cand, basis[0], basis[1], *[it["text"] for it in items]) >= 0.6:
            title = cand
    return out, title, basis


async def apply(rq_id: str, shorts: dict[str, tuple[str, str]], title: str | None, basis: list[Any]) -> dict[str, Any]:
    def fn(d: dict[str, Any], rev: int) -> None:
        for _, it in domain.all_items(d):
            if it["id"] in shorts and (it.get("text") or "").strip() == shorts[it["id"]][1].strip():
                it["short"] = shorts[it["id"]][0]
                it["short_for"] = domain._short_key(it["text"])
        cur_basis = [domain.field_value(d, "customer_name"), domain.field_value(d, "project_name")]
        if title and cur_basis == basis:
            d["short_title"] = title
            d["short_title_basis"] = basis

    doc, _ = await repo.mutate(rq_id, fn)
    return doc


async def ensure_shorts(rq_id: str, *, timeout: float = 8.0) -> None:
    doc = await repo.require_doc(rq_id)
    items, need_title = needs(doc)
    if not items and not need_title:
        return
    try:
        shorts, title, basis = await compute(doc, timeout=timeout)
    except ApiError as exc:
        log.info("짧은 이름 건너뜀(%s): %s", rq_id, exc.code)
        return
    if shorts or title:
        await apply(rq_id, shorts, title, basis)


async def maybe_enqueue(doc: dict[str, Any]) -> None:
    items, need_title = needs(doc)
    if not items and not need_title:
        return
    try:
        ok = await jobs().r.set(f"wm:rq:short:{doc['id']}", "1", nx=True, ex=30)
        if ok:
            await jobs().enqueue("requirements", "rq.short", {"requirement_id": doc["id"]}, title="짧은 이름 만들기",
                                 ref=doc["id"], project_id=doc.get("project_id"))
    except Exception as exc:  # noqa: BLE001 — 부가 작업
        log.debug("rq.short 넣기 건너뜀: %s", exc)


async def handle_short_job(ctx: JobContext) -> dict[str, Any]:
    rq_id = ctx.payload["requirement_id"]
    doc = await repo.get_doc(rq_id)
    if doc is None:
        return {"requirement_id": rq_id, "updated": 0}
    try:
        shorts, title, basis = await compute(doc, timeout=60)
    except ApiError as exc:
        await ctx.log(f"짧은 이름을 만들지 못했어요: {exc.message}")
        return {"requirement_id": rq_id, "updated": 0}
    if shorts or title:
        await apply(rq_id, shorts, title, basis)
    await ctx.progress(100, "완료")
    return {"requirement_id": rq_id, "updated": len(shorts), "short_title": title}
