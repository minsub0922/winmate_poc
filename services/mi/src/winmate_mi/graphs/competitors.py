"""경쟁사 후보 찾기 · 행 추가(설계 decide_competitors · 분석 · mi.layout · mi.competitor_add 공용, 04-competitor.md §7.3 의 가벼운 판)."""
from __future__ import annotations

import logging
import re
from typing import Any

from winmate_common.errors import ApiError

from .. import aix, config, prompts, rules, verify
from ..store import nid
from .common import Budget, sensitive_texts

log = logging.getLogger("winmate.mi.competitors")

TRANSIENT = (429, 502, 503, 504)


def norm_name(name: str) -> str:
    n = re.sub(r"\(주\)|㈜|주식회사|\s*inc\.?$|\s*co\.,?\s*ltd\.?$", "", (name or "").strip(), flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", n).strip()


def is_samsung(name: str) -> bool:
    low = (name or "").lower()
    return "삼성" in low or "samsung" in low


def same_company(a: str, c: dict[str, Any]) -> bool:
    na = verify.N(norm_name(a))
    if not na:
        return False
    if na == verify.N(norm_name(c.get("real_name") or "")):
        return True
    return any(na == verify.N(norm_name(x)) for x in c.get("aliases") or [])


def add_competitor(doc: dict[str, Any], name: str, *, origin: str, aliases: list[str] | None = None, kind_label: str = "",
                   desc: str = "", confidence: float | None = None, pinned: bool = False, lookup: str = "done") -> dict[str, Any]:
    comps = doc.setdefault("competitors", [])
    used = {c.get("letter") for c in comps}
    letter = next(x for x in rules.letters(len(comps) + 27) if x not in used)
    c = {"id": nid("cmp"), "letter": letter, "real_name": norm_name(name), "aliases": list(dict.fromkeys(aliases or [])), "kind_label": kind_label,
         "desc": desc, "origin": origin, "confidence": confidence, "pinned": pinned, "removed": False, "evidence_source_ids": [],
         "order": len(comps), "lookup": lookup}
    comps.append(c)
    return c


async def _summary(task: str, query: str, budget: Budget) -> str:
    if budget.web_unavailable or not budget.take("websearch"):
        return ""
    try:
        res = await aix.websearch(task, query)
    except ApiError as exc:
        if exc.status in TRANSIENT or exc.code in ("UPSTREAM_UNAVAILABLE", "TIMEOUT", "RATE_LIMITED", "DAILY_LIMIT_EXCEEDED", "NOT_CONFIGURED"):
            budget.web_unavailable = True
            return ""
        raise
    return res.get("summary") or ""


async def find_candidates(doc: dict[str, Any], budget: Budget, *, want: int = 3, exclude: list[dict[str, Any]] | None = None,
                          task: str = "mi.web_candidates", query: str | None = None) -> tuple[list[prompts.Candidate], str]:
    """업종 · 제품군 검색 1회 → 요약에서 후보 추출(LLM) → 요약에 이름이 있는 것 · 신뢰 ≥ 0.50 · 삼성 제외 → 상위 want."""
    seg_code = ((doc.get("segment") or {}).get("mix") or {}).get("a") or (doc.get("segment") or {}).get("code") or "GEN"
    seg = config.segment(seg_code)
    region = ((doc.get("extracted") or {}).get("region") or "").strip()
    q = query or " ".join(x for x in [region, seg["market"] if seg_code != "GEN" else "", seg["product"], "공급 업체 경쟁사"] if x)
    q = aix.query_guard(q, sensitive_texts(doc))
    if not q:
        return [], ""
    summary = await _summary(task, q, budget)
    if not summary.strip():
        return [], ""
    if not budget.take("llm"):
        return [], summary
    try:
        out = await aix.llm("mi.competitor_candidates", prompts.competitor_candidates(seg_code, seg["product"], summary), prompts.Candidates,
                            confidential=False)
    except (aix.LLMFailed, ApiError) as exc:
        log.info("후보 추출 실패: %s", exc)
        return [], summary
    hay = verify.N(summary)
    min_conf = float(config.th("competitor_min_conf", 0.5))
    picked: list[prompts.Candidate] = []
    for c in out.items:
        name = norm_name(c.name)
        if not name or verify.N(name) not in hay or is_samsung(name):
            continue
        if any(same_company(name, e) for e in exclude or []) or any(verify.N(name) == verify.N(p.name) for p in picked):
            continue
        conf = rules.round2(c.confidence) or 0.0
        if rules.to100(conf) < rules.to100(min_conf):
            continue
        aliases = [a for a in c.aliases if a and verify.N(a) in hay and verify.N(a) != verify.N(name)]
        picked.append(prompts.Candidate(name=name, aliases=aliases, kind_label=c.kind_label or "", desc=c.desc or "", confidence=conf, quote=c.quote))
    picked.sort(key=lambda c: (-c.confidence, c.name))
    return picked[:want], summary


async def profile(doc: dict[str, Any], cmp: dict[str, Any], budget: Budget) -> dict[str, Any]:
    """직접 추가한 경쟁사 — 1회 검색으로 유형 · 한 줄 설명 · 별칭(요약에 있는 것만)."""
    seg = config.segment((doc.get("segment") or {}).get("code") or "GEN")
    q = aix.query_guard(f"{cmp['real_name']} {seg['product']} 회사", sensitive_texts(doc), allow_numbers=None)
    if not q:
        return {}
    summary = await _summary("mi.web_competitor_add", q, budget)
    if not summary.strip():
        return {"kind_label": "[확인 필요]", "desc": "[확인 필요]"}
    try:
        out = await aix.llm("mi.competitor_profile", prompts.competitor_profile(cmp["real_name"], summary), prompts.Candidate, confidential=False)
    except (aix.LLMFailed, ApiError):
        return {"kind_label": "[확인 필요]", "desc": "[확인 필요]"}
    hay = verify.N(summary)
    aliases = [a for a in out.aliases if a and verify.N(a) in hay and verify.N(a) != verify.N(cmp["real_name"])]
    return {"kind_label": out.kind_label or "[확인 필요]", "desc": out.desc or "[확인 필요]", "aliases": aliases}
