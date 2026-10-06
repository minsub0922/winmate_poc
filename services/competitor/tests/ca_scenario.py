"""테스트 공용 시나리오 — A 커피 메뉴보드(AC-CA-01 글) · FakeAI 응답 묶음.

`use_a_coffee(env)` 는 FakeAI 에 찾기 · 분석 응답을 넣는다. 기본은 `sources` 모드(수집한 페이지가 근거 → 요약 상한 없음)로
보드 예시 신뢰 `0.91 · 0.86 · 0.78 · 0.74 · 0.52 · 0.31` 을 그대로 낸다.
"""
from __future__ import annotations

import re
from typing import Any

A_TEXT = ("A 커피 프랜차이즈가 전국 320개 매장의 메뉴보드를 디지털로 바꾸려고 해요. 수도권 직영점부터 시작하고, "
          "55인치 사이니지와 본사에서 콘텐츠를 일괄 배포하는 솔루션이 필요해요.")
NAMES = ["ZZ 사이니지", "WW 디스플레이", "VV 클라우드", "UU 키오스크", "TT 디스플레이", "SS 미디어"]
KINDS = ["국내 대형 가전 · 사이니지", "글로벌 사이니지 전문", "클라우드 CMS 소프트웨어", "키오스크 · 메뉴보드 통합 벤더", "저가형 상업용 디스플레이 수입사", "오프라인 광고 매체사"]
# 신호(업종 · 제품 · 장소 · 고객사) → 신뢰 0.91 · 0.86 · 0.78 · 0.74 · 0.52 · 0.31 (가중치 .30 · .40 · .15 · .15, 네 칸 모두 있음)
SIGNALS = [
    (1.0, 1.0, 0.95, 0.45, False),   # 0.3+0.4+0.1425+0.0675 = 0.91
    (0.95, 0.9, 1.0, 0.4, False),    # 0.285+0.36+0.15+0.06 = 0.855 → 0.86
    (1.0, 0.9, 1.0, 0.6, True),      # 제품 일부 겹침 → 0.6 · 0.3+0.24+0.15+0.09 = 0.78
    (0.9, 0.75, 0.7, 0.4, False),    # 0.27+0.30+0.105+0.06 = 0.735 → 0.74
    (0.4, 0.7, 0.6, 0.2, False),     # 0.12+0.28+0.09+0.03 = 0.52
    (0.6, 0.2, 0.2, 0.1, False),     # 0.18+0.08+0.03+0.015 = 0.305 → 0.31
]
CONF = [0.91, 0.86, 0.78, 0.74, 0.52, 0.31]


def page(url: str, text: str, title: str = "", published_at: str = "2026-05-01") -> dict[str, Any]:
    return {"text": text, "title": title or url, "published_at": published_at}


def slots_json(customer: str | None = "A 커피 프랜차이즈", place: str | None = "수도권 직영점", region: str | None = "수도권",
               product: str | None = '55" 사이니지 + 배포 솔루션', specific: bool = True) -> dict[str, Any]:
    return {"customer": {"value": customer, "confidence": 0.95 if customer else 0},
            "place": {"value": place, "kind": "site" if place else None, "region": region, "confidence": 0.9 if place else 0},
            "product": {"value": product, "categories": ["스마트 사이니지"], "specific": specific, "confidence": 0.9 if product else 0},
            "industry_hint": "카페 프랜차이즈", "competitor_mentions": [], "eval_criteria": []}


def use_a_coffee(env: Any, *, names: list[str] | None = None, signals: list[tuple] | None = None, sources_mode: bool = True,
                 slots: dict[str, Any] | None = None, segment: dict[str, float] | None = None) -> None:
    names = names or NAMES
    signals = signals or SIGNALS
    kinds = [KINDS[i % len(KINDS)] for i in range(len(names))]
    ai = env.ai
    ai.return_sources = sources_mode
    env.kb.set_conf(segment or {"FB": 0.94, "RT": 0.40})
    ai.llm["ca.extract_slots"] = slots or slots_json()
    ai.llm["ca.classify_segment"] = {"segments": [{"code": c, "p": p, "clues": []} for c, p in (segment or {"FB": 0.94, "RT": 0.40}).items()]}
    summary = "메뉴보드 사이니지 공급 업체: " + ", ".join(names) + "."
    url = "https://example.com/news/menuboard-vendors"
    ai.pages[url] = page(url, summary + " 업체별 설명은 기사 본문을 참고.", "메뉴보드 공급 업체 기사")
    ai.web["ca.web_candidates"] = {"summary": summary, "sources": [{"url": url, "title": "메뉴보드 공급 업체 기사"}]}
    ai.llm["ca.candidates_from_text"] = {"candidates": [{"name": n, "kind_label": k, "evidence_id": "E1", "evidence_quote": n} for n, k in zip(names, kinds)]}
    ai.llm["ca.resolve_entities"] = {"groups": [{"canonical": n, "aliases": []} for n in names]}
    ev = "E1" if sources_mode else "E1"
    ai.llm["ca.score_signals"] = {"candidates": [
        {"name": n, "kind_label": k, "why": f"{n} 근거 한 줄",
         "signals": {"industry": {"s": s[0], "source_ids": [ev]}, "product": {"s": s[1], "partial": s[4], "source_ids": [ev]},
                     "place": {"s": s[2], "source_ids": [ev]}, "customer": {"s": s[3], "source_ids": [ev]}}}
        for n, k, s in zip(names, kinds, signals)]}
    ai.llm["ca.make_criteria"] = {"criteria": [{"name": "본사 일괄 배포", "source": "free"}, {"name": "매장별 가격 차등", "source": "free"},
                                               {"name": "전기료", "source": "free"}],
                                  "industry": [{"code": "R08", "name": "인건비 절감"}, {"code": "R03", "name": "원격 콘텐츠"},
                                               {"code": "R07", "name": "설치 속도"}, {"code": "R16", "name": "시간대 프로모션"}]}
    ai.llm["ca.title"] = {"title": "A 커피 메뉴보드 경쟁사 분석"}


def eid(prompt: str, quote: str, prefer: str, default: str) -> str:
    """사실 뽑기 프롬프트의 근거 블록(`E3 (공개 자료) 제목\n본문`)에서 quote 가 든 블록 번호 — prefer 글자가 함께 든 블록을 먼저."""
    blocks = [b for b in re.split(r"\n\n(?=[EK]\d+ )", prompt) if re.match(r"[EK]\d+ ", b)]
    hits = [b for b in blocks if quote in b]
    best = next((b for b in hits if prefer and prefer in b), hits[0] if hits else None)
    return best.split(" ", 1)[0] if best else default


def use_facts(env: Any, *, price_text: str | None = None, price_quote: str | None = None) -> None:
    """분석 단계 응답 — 경쟁사마다 사실 페이지(수집 성공) · 사실 뽑기 · 판정 · 포지셔닝 · 강점."""
    ai = env.ai
    ai.return_sources = True

    def web(body: dict[str, Any]) -> dict[str, Any]:
        q = body["query"]
        name = next((n for n in NAMES if n in q), "기타")
        key = next((k for k in ("라인업", "CMS", "도입 사례", "가격", "신제품") if k in q), "기타")
        url = f"https://example.com/{abs(hash((name, key))) % 10**8}"
        text = f"{name} {key} 정보: 55인치 메뉴보드 라인업과 자체 CMS를 제공한다. 공개 사례 6건."
        if key == "가격" and price_quote:
            text = f"{name} {price_quote}"
        ai.pages[url] = page(url, text, f"{name} {key}")
        return {"summary": text, "sources": [{"url": url, "title": f"{name} {key}"}]}

    ai.web["ca.web_facts"] = web
    ai.web["ca.web_research"] = web

    def facts(body: dict[str, Any]) -> dict[str, Any]:
        p = body["prompt"]
        q1, q2, q3 = "55인치 메뉴보드 라인업과 자체 CMS를 제공한다", "자체 CMS를 제공한다", "공개 사례 6건"
        claim = {"text": "55인치 메뉴보드 라인업", "citations": [{"evidence_id": eid(p, q1, "라인업 정보", "E1"), "quote": q1}]}
        out = {"lineup": {"text": "55\" 메뉴보드 라인업", "claims": [claim]},
               "solution": {"text": "자체 CMS", "claims": [{"text": "자체 CMS 제공", "citations": [{"evidence_id": eid(p, q2, "CMS 정보", "E2"), "quote": q2}]}]},
               "references": {"text": "공개 사례 6건", "claims": [{"text": "공개 사례 6건", "citations": [{"evidence_id": eid(p, q3, "도입 사례 정보", "E3"),
                                                                                                       "quote": q3}]}]},
               "price": {"text": price_text or "[확인 필요]", "claims": []},
               "recent": {"text": "[확인 필요]", "claims": []}}
        if price_text and price_quote:
            out["price"] = {"text": price_text, "claims": [{"text": price_text, "citations": [{"evidence_id": eid(p, price_quote, "", "E4"),
                                                                                                "quote": price_quote}]}]}
        return {"facts": out}

    ai.llm["ca.extract_facts"] = facts
    crit = ["본사 일괄 배포", "매장별 가격 차등", "전기료", "인건비 절감", "가격대", "레퍼런스 · AS"]

    def verdicts(body: dict[str, Any]) -> dict[str, Any]:
        p = body["prompt"]
        i = next((k for k, n in enumerate(NAMES) if f"'{n}'" in p), 0)
        table = [
            ["samsung_better", "samsung_better", "samsung_better", "similar", "unknown", "similar"],
            ["samsung_better", "similar", "similar", "similar", "unknown", "samsung_worse"],
            ["similar", "samsung_worse", "unknown", "similar", "unknown", "similar"],
            ["samsung_better", "similar", "samsung_better", "similar", "unknown", "samsung_worse"],
            ["samsung_better", "samsung_better", "similar", "samsung_better", "samsung_worse", "samsung_better"],
            ["similar"] * 6,
        ][i]
        return {"rows": [{"criterion": c, "verdict": v, "rationale": f"{c} 판정"} for c, v in zip(crit, table)]}

    ai.llm["ca.verdicts"] = verdicts
    ai.llm["ca.positioning"] = lambda body: {"text": "자체 CMS 기반 라인업"}
    ai.llm["ca.strengths"] = {"strengths": [{"criterion": "본사 일괄 배포", "title": "서버 없는 통합 관리", "note": "MagicINFO · 별도 서버 없이 전 매장 관리"}],
                              "cautions": []}


async def find(env: Any, text: str = A_TEXT, **create: Any) -> str:
    r = await env.c.post("/v1/analyses", json={"input_mode": "free", "text": text, **create})
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    r = await env.c.post(f"/v1/analyses/{aid}/find")
    assert r.status_code == 202, r.text
    await env.drain()
    return aid


async def analyze(env: Any, aid: str, mode: str = "full") -> dict[str, Any]:
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": mode})
    assert r.status_code == 202, r.text
    await env.drain()
    return (await env.c.get(f"/v1/analyses/{aid}")).json()
