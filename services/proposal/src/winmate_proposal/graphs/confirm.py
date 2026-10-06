"""confirm_research(§7.9) — 열린 수치 항목마다 후보 값 + 출처를 찾는다(확정하지 않는다).

(1) 연결된 MI 작업의 저장된 주장(facts:lookup) (2) 웹 검색(ai-tools) — 질의에는 고객사명 · 내부 수치 · RFP 문장을 넣지 않는다(§10.13).
"""
from __future__ import annotations

import logging
import re
from typing import Any

from winmate_common.ai import ai
from winmate_common.errors import ApiError
from winmate_common.jobs import JobContext

from .. import clients, core, defs, prompts, repo
from . import common as G

log = logging.getLogger("winmate.proposal.confirm")

PICK = {"type": "object", "properties": {"value": {"type": "string"}, "source_url": {"type": "string"}, "note": {"type": "string"}}}


def customer_tokens(p: dict[str, Any]) -> list[str]:
    name = (p.get("customer") or {}).get("name") or ""
    toks = [name] + [w for w in re.split(r"\s+", name) if len(w) >= 2 and w not in ("프랜차이즈", "주식회사", "그룹")]
    return [t for t in toks if t]


def safe_query(q: str, p: dict[str, Any]) -> str | None:
    """결정적 검사 — 고객명 · 고객 alias · 숫자(내부 수치)가 있으면 거부."""
    if any(t and t in q for t in customer_tokens(p)):
        return None
    if re.search(r"\d{2,}", q):
        return None
    return q.strip() or None


async def research_item(p: dict[str, Any], it: dict[str, Any], f: dict[str, Any] | None, mi_links: list[dict[str, Any]],
                        instruction: str | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    label = (f or {}).get("label") or (it.get("text") or {}).get("pre") or "수치"
    unit = (f or {}).get("unit")
    for ln in mi_links:
        res = await clients.call("mi", "POST", f"/v1/analyses/{ln['ref_id']}/facts:lookup",
                                 json={"questions": [{"key": (f or {}).get("key") or it["id"], "label": label, "unit": unit}]}, quiet=True)
        for row in (res or {}).get("items") or []:
            for c in row.get("candidates") or []:
                if c.get("value"):
                    out.append({"value": f"{c['value']}{c.get('unit') or ''}", "source": {"kind": "work", "feature": "mi", "ref_id": ln["ref_id"],
                                                                                      "label": (c.get("source") or {}).get("label") or "MI 작업",
                                                                                      "status": c.get("status")}})
    # 웹 — 질의는 일반화(고객 정보 없음)
    ind = defs.INDUSTRIES.get((p.get("customer") or {}).get("industry_code") or "", {}).get("name", "")
    qres = await G.llm_json("pr.research_query", system="웹 검색 질의 하나. 고객사명 · 내부 수치 · RFP 문장은 넣지 않는다.",
                            user=f"찾을 값: {label}" + (f" · 단위 {unit}" if unit else "") + (f"\n업종: {ind}" if ind else "") +
                                 (f"\n방향: {instruction}" if instruction else ""),
                            schema=prompts.RESEARCH_QUERY, confidential=False)
    q = safe_query((qres or {}).get("query") or "", p) or safe_query(f"{ind} {label}".strip(), p) or safe_query(label, p)
    if not q:
        return out
    try:
        web = await ai().websearch("pr.research", q, max_sources=5, confidential=False)
    except ApiError as exc:
        if exc.status in (429, 502, 503, 504):
            return out
        raise
    summary = (web or {}).get("summary") or ""
    sources = (web or {}).get("sources") or []
    if summary:
        pick = await G.llm_json("pr.research_pick", system="요약에 그대로 있는 값만 고른다. 없으면 value 를 비운다.",
                                user=f"찾을 값: {label}\n요약:\n{summary[:3000]}\n출처: " + " · ".join(s.get("url") or "" for s in sources[:5]),
                                schema=PICK, confidential=False)
        val = ((pick or {}).get("value") or "").strip()
        if val and (re.sub(r"[^\d.]", "", val) == "" or re.sub(r"[^\d.]", "", val) in re.sub(r"[^\d.]", "", summary.replace(",", ""))):
            url = (pick or {}).get("source_url") or (sources[0].get("url") if sources else None)
            out.append({"value": val, "source": {"kind": "url", "url": url, "label": next((s.get("title") for s in sources if s.get("url") == url), "") or "웹 검색",
                                                 "query": q, "note": (pick or {}).get("note")}})
    return out


async def handle_research(ctx: JobContext) -> dict[str, Any]:
    pl = ctx.payload
    pid = pl["proposal_id"]

    async def node(s: dict[str, Any]) -> dict[str, Any]:
        p = await core.load(pid)
        mi_links = [ln for ln in await repo.alist("links", {"proposal_id": pid}) if ln.get("feature") == "mi" and (ln.get("status") or "linked") == "linked"]
        found = 0
        ids = pl.get("ids") or []
        for i, iid in enumerate(ids):
            await G.check_cancel()
            it = await repo.aget("confirm_items", iid)
            if not it or it.get("status") != "open":
                continue
            f = await repo.aget("facts", it["fact_id"]) if it.get("fact_id") else None
            cands = await research_item(p, it, f, mi_links, pl.get("instruction"))
            await repo.amutate("confirm_items", iid, lambda x, c=cands: x.update({"candidates": c, "researched": True}))
            found += 1 if cands else 0
            await G.progress(int((i + 1) * 100 / max(1, len(ids))), f"{i + 1} / {len(ids)}")
            await G.partial({"item_id": iid, "candidates": len(cands)})
        return {"result": {"proposal_id": pid, "items": len(ids), "with_candidates": found}}
    final = await G.run(ctx, G.single("research", node), {}, labels={"research": "남은 수치 다시 찾기"})
    return (final or {}).get("result") or {}
