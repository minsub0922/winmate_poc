"""테스트 시나리오 — MIC 1번 `A 커피 프랜차이즈 메뉴보드`(외식 · 카페 0.94 · 표준 · 4개 영역) 를 가짜 ai-tools 로 꾸민다.

경쟁사 이름은 지어낸 이름(가나 디스플레이 · 다라 사이니지 · 마바 미디어)이고, 칸 · 판정 · 강점 응답은 프롬프트 속 id 를 읽어 만든다.
"""
from __future__ import annotations

import json
import re
from typing import Any

A_REQ = "A 커피 프랜차이즈 전국 매장 메뉴보드 디지털 전환 · 경쟁사 대비 본사 원격 통합 관리 · 피크타임 주문 대기 · 저전력 운영"
MARKET_URL = "https://research.example.org/fnb-signage-2026"
MARKET_PAGE = ("F&B 디지털 사이니지 동향 2026. 디지털 메뉴보드를 쓰는 매장이 3년간 42% 증가했다. "
               "국내 F&B 디지털 사이니지 시장 규모는 2025년 6,700억 원으로 추정된다. 키오스크와 메뉴보드 연동이 확산되고 있다.")
MARKET_SUMMARY = ("국내 F&B 디지털 사이니지 시장 규모는 2025년 6,700억 원 수준이다. 연도별로는 2023년 5,000억 원, 2024년 5,800억 원이었다. "
                  "디지털 메뉴보드를 쓰는 매장이 최근 3년간 42% 증가했다. 2026년 3월 업계 자료에 따르면 키오스크와 메뉴보드 연동이 확산되고 있다.")
CUSTOMER_SUMMARY = ("A 커피는 2026년 3월 보도자료에서 직영점과 가맹점을 함께 늘리는 매장 확장 계획을 밝혔다. "
                    "A 커피는 피크타임 메뉴 교체를 본사에서 일괄 관리하는 운영 방식을 검토하고 있다.")
USER_SUMMARY = ("2026년 2월 조사에 따르면 카페 손님은 피크타임 주문 대기에서 메뉴를 찾는 데 시간을 가장 많이 쓴다. "
                "점장은 시간대별 메뉴 교체 작업을 부담으로 꼽았다.")
NEW_COMPS = ("사바 비전", "아자 테크", "차카 시스템")
COMP = {
    **{n: f"{n}는 자체 CMS를 제공한다. {n}는 콘텐츠를 수동으로 배포한다." for n in NEW_COMPS},
    "가나 디스플레이": "가나 디스플레이는 자체 CMS를 제공하며 매장 500곳 이상이면 별도 서버를 추가해야 한다. 2026년 1월 기준 가나 디스플레이 메뉴보드는 배포 후 매장 수동 승인이 필요하다. 가나 디스플레이 55형 메뉴보드 소비전력은 180 W이다.",
    "다라 사이니지": "다라 사이니지는 3rd-party CMS 연동 방식이며 2025년 11월부터 지역 단위로 콘텐츠를 배포한다.",
    "마바 미디어": "마바 미디어는 2026년 2월 클라우드 CMS를 내세웠고 메뉴보드 원격 관리를 지원한다.",
}


def _ids(prompt: str, label: str) -> list[dict[str, Any]]:
    m = re.search(label + r": (\[.*?\])(?:\n|$)", prompt)
    return json.loads(m.group(1)) if m else []


def compare_cells(body: dict[str, Any]) -> dict[str, Any]:
    prompt = body["messages"][-1]["content"]
    crits = _ids(prompt, "기준")
    comps = _ids(prompt, "경쟁사")
    cells = []
    for crt in crits:
        for c in comps:
            name = c["name"]
            text, quote = "[확인 필요]", None
            if "원격" in crt["name"]:
                if name == "가나 디스플레이":
                    text, quote = "자체 CMS, 매장 500곳 이상 시 서버 추가", "자체 CMS를 제공하며 매장 500곳 이상이면 별도 서버를 추가해야 한다"
                elif name == "다라 사이니지":
                    text, quote = "3rd-party CMS 연동", "3rd-party CMS 연동 방식이며"
                elif name == "마바 미디어":
                    text, quote = "클라우드 CMS · 원격 관리 지원", "메뉴보드 원격 관리를 지원한다"
            elif "전력" in crt["name"]:
                if name == "가나 디스플레이":
                    text, quote = "55형 소비전력 180 W", "55형 메뉴보드 소비전력은 180 W이다"
            elif "피크" in crt["name"] or "메뉴" in crt["name"]:
                if name == "가나 디스플레이":
                    text, quote = "배포 후 매장 수동 승인", "배포 후 매장 수동 승인이 필요하다"
                elif name == "다라 사이니지":
                    text, quote = "지역 단위 배포", "지역 단위로 콘텐츠를 배포한다"
                elif name == "마바 미디어":
                    text, quote = "클라우드 CMS 배포", "클라우드 CMS를 내세웠고"
            if name in NEW_COMPS and ("원격" in crt["name"] or "피크" in crt["name"]):
                text, quote = ("자체 CMS", f"{name}는 자체 CMS를 제공한다") if "원격" in crt["name"] else ("수동 배포", f"{name}는 콘텐츠를 수동으로 배포한다")
            cells.append({"criterion_id": crt["id"], "competitor_id": c["id"], "text": text,
                          "citations": [{"evidence_id": "E1", "quote": quote}] if quote else []})
    return {"cells": cells}


def verdicts(body: dict[str, Any]) -> dict[str, Any]:
    prompt = body["messages"][-1]["content"]
    rows = []
    for line in prompt.splitlines():
        m = re.match(r"\[(crt_[A-Z0-9]+)\] (.*?) — (.*)", line)
        if not m:
            continue
        crt, name, rest = m.groups()
        vs = []
        for cm in re.finditer(r"\((cmp_[A-Z0-9]+)\): ([^|]*)", rest):
            cid, txt = cm.groups()
            better = "[확인 필요]" not in txt and ("원격" in name or "피크" in name or "메뉴" in name or "전력" in name)
            vs.append({"competitor_id": cid, "verdict": "samsung_better" if better else "unknown"})
        rows.append({"criterion_id": crt, "verdicts": vs, "rationale": ""})
    return {"rows": rows}


def strengths(body: dict[str, Any]) -> dict[str, Any]:
    prompt = body["messages"][-1]["content"]
    m = re.search(r"고른 기준: (\[.*?\])\n", prompt)
    picked = json.loads(m.group(1)) if m else []
    out = []
    for p in picked:
        if "전력" in p["name"]:
            out.append({"criterion_id": p["criterion_id"], "title": "에너지 절감", "note": "QM55C 소비전력 154 W로 전기료 부담이 적어요",
                        "citations": [{"evidence_id": "E1", "quote": "소비전력 (On Mode): 154 W"}]})
        else:
            out.append({"criterion_id": p["criterion_id"], "title": p.get("title") or p["name"][:12],
                        "note": (p.get("samsung") or p.get("note") or "")[:40] or "[확인 필요]", "citations": []})
    return {"strengths": out}


def market_claims(_body: dict[str, Any]) -> dict[str, Any]:
    return {
        "blocks": {"size_label": "국내 F&B 디지털 사이니지 시장", "size_unit": "억 원",
                   "size_series": [{"year": 2023, "claim": "c5"}, {"year": 2024, "claim": "c6"}, {"year": 2025, "claim": "c1"}], "cagr": None,
                   "trends": [{"title": "디지털 메뉴보드 확산", "when": "2023~2025", "claim": "c2", "implication": "그래서 A 커피는 전 매장 동시 전환이 유리해요"},
                              {"title": "키오스크 · 메뉴보드 연동", "when": "2026", "claim": "c4", "implication": "주문 대기 줄이기에 맞아요"}],
                   "regulations": [], "kb_trend": "c3"},
        "claims": [
            {"local_id": "c1", "block_path": "size_series.0", "text": "국내 F&B 디지털 사이니지 시장 규모는 2025년 6,700억 원이에요.",
             "metric_key": "market_size_2025", "metric_label": "F&B 사이니지 시장 규모(2025)",
             "citations": [{"evidence_id": "E9", "quote": "국내 F&B 디지털 사이니지 시장 규모는 2025년 6,700억 원"}]},
            {"local_id": "c5", "block_path": "size_series.0", "text": "2023년 시장 규모는 5,000억 원이었어요.", "metric_key": "market_size_2023",
             "metric_label": "F&B 사이니지 시장 규모(2023)", "citations": [{"evidence_id": "E9", "quote": "2023년 5,000억 원"}]},
            {"local_id": "c6", "block_path": "size_series.1", "text": "2024년 시장 규모는 5,800억 원이었어요.", "metric_key": "market_size_2024",
             "metric_label": "F&B 사이니지 시장 규모(2024)", "citations": [{"evidence_id": "E9", "quote": "2024년 5,800억 원"}]},
            {"local_id": "c2", "block_path": "trends.0", "text": "디지털 메뉴보드를 쓰는 매장이 최근 3년간 42% 늘었습니다.",
             "metric_key": "menuboard_store_growth", "metric_label": "디지털 메뉴보드 도입 매장 증가율",
             "citations": [{"evidence_id": "E9", "quote": "디지털 메뉴보드를 쓰는 매장이 3년간 42% 증가했다"},
                           {"evidence_id": "E9", "quote": "디지털 메뉴보드를 쓰는 매장이 최근 3년간 42% 증가했다"}]},
            {"local_id": "c3", "block_path": "kb_trend", "text": "외식 · 카페 사례 DB에서는 스마트 LCD 사이니지 도입이 가장 많아요.",
             "citations": [{"evidence_id": "E1", "quote": "많이 쓰인 제품: 스마트 LCD 사이니지"}]},
            {"local_id": "c4", "block_path": "trends.1", "text": "키오스크와 메뉴보드 연동이 확산되고 있어요.",
             "citations": [{"evidence_id": "E9", "quote": "키오스크와 메뉴보드 연동이 확산되고 있다"}]},
        ],
    }


def customer_claims(_body: dict[str, Any]) -> dict[str, Any]:
    return {
        "blocks": {"summary": "k1", "strategy": ["k2"], "expansion": ["k3"], "structure": [{"label": "직영 : 가맹", "value": "[00] : [00]", "claim": "k4"}],
                   "ops_challenges": [{"stage": "메뉴 교체", "claim": "k2"}, {"stage": "프로모션", "claim": "k2"}, {"stage": "매장 확장", "claim": "k3"}]},
        "claims": [
            {"local_id": "k1", "text": "A 커피는 피크타임 메뉴 교체를 본사에서 일괄 관리하는 운영 방식을 검토하고 있어요.",
             "citations": [{"evidence_id": "E1", "quote": "피크타임 메뉴 교체를 본사에서 일괄 관리하는 운영 방식을 검토하고 있다"}]},
            {"local_id": "k2", "text": "본사 일괄 관리로 메뉴 교체 부담을 줄이려 해요.",
             "citations": [{"evidence_id": "E1", "quote": "피크타임 메뉴 교체를 본사에서 일괄 관리하는"}]},
            {"local_id": "k3", "text": "직영점과 가맹점을 함께 늘리는 매장 확장 계획을 밝혔어요.",
             "citations": [{"evidence_id": "E1", "quote": "직영점과 가맹점을 함께 늘리는 매장 확장 계획을 밝혔다"}]},
            {"local_id": "k4", "text": "직영 : 가맹 비율은 [00] : [00]이에요.", "metric_key": "store_mix_ratio", "metric_label": "직영 : 가맹 비율", "citations": []},
        ],
    }


def user_claims(_body: dict[str, Any]) -> dict[str, Any]:
    return {
        "blocks": {"personas": [{"role": "카페 손님", "goal": "빨리 주문", "pain": "메뉴 찾기", "context": "피크타임", "claims": ["u1"]},
                                {"role": "점장", "goal": "메뉴 교체 부담 줄이기", "pain": "시간대별 교체", "context": "매장 운영", "claims": ["u2"]}],
                   "journey": [{"stage": "입장", "touchpoint": "메뉴보드", "pain": "메뉴 찾기", "opportunity": "추천 메뉴", "claims": ["u1"]},
                               {"stage": "주문", "touchpoint": "카운터", "pain": "대기", "opportunity": "메뉴 미리 보기", "claims": ["u1"]},
                               {"stage": "픽업", "touchpoint": "픽업대", "pain": "호출", "opportunity": "번호 안내", "claims": []}],
                   "composition": []},
        "claims": [
            {"local_id": "u1", "text": "카페 손님은 피크타임 주문 대기에서 메뉴를 찾는 데 시간을 가장 많이 써요.",
             "citations": [{"evidence_id": "E1", "quote": "카페 손님은 피크타임 주문 대기에서 메뉴를 찾는 데 시간을 가장 많이 쓴다"}]},
            {"local_id": "u2", "text": "점장은 시간대별 메뉴 교체 작업을 부담으로 꼽았어요.",
             "citations": [{"evidence_id": "E1", "quote": "점장은 시간대별 메뉴 교체 작업을 부담으로 꼽았다"}]},
        ],
    }


def web_competitor(body: dict[str, Any]) -> dict[str, Any]:
    q = body["query"]
    for name, text in COMP.items():
        if name in q:
            return {"summary": text, "sources": []}
    return {"summary": ""}


def setup_fb(env: Any, *, sources_mode: bool = False) -> None:
    ai = env.ai
    env.kb.set_conf({"FB": 0.94, "RT": 0.40}, clues={"FB": ["메뉴보드"]})
    ai.return_sources = sources_mode
    ai.llm.update({
        "mi.extract_requirements": {"requirements": ["본사 원격 통합 관리", "저전력 운영", "피크타임 메뉴 전환"], "eval_criteria": [], "schedule": [],
                                    "competitor_mentions": [], "keywords": ["메뉴보드"], "region": "국내"},
        "mi.classify_segment": {"segments": [{"code": "FB", "p": 0.94, "clues": ["프랜차이즈", "메뉴보드"]}, {"code": "RT", "p": 0.40, "clues": []}],
                                "out_of_scope": False, "reason": ""},
        "mi.decide_scope": {"areas": {a: {"include": True, "reason": "요구사항 기준"} for a in ("market", "customer", "user", "competitor")}},
        "mi.public_docs": {"documents": ["2025 사업보고서", "2026년 IR 자료", "매장 확장 보도자료"]},
        "mi.competitor_candidates": {"items": [
            {"name": "가나 디스플레이", "aliases": [], "kind_label": "국내 대형 가전 · 사이니지", "desc": "메뉴보드급 사이니지 · 자체 CMS", "confidence": 0.82, "quote": ""},
            {"name": "다라 사이니지", "aliases": [], "kind_label": "글로벌 사이니지 전문", "desc": "대형 프랜차이즈 레퍼런스", "confidence": 0.74, "quote": ""},
            {"name": "마바 미디어", "aliases": [], "kind_label": "국내 CMS · 솔루션", "desc": "클라우드 CMS", "confidence": 0.61, "quote": ""},
            {"name": "지어낸 전자", "aliases": [], "kind_label": "", "desc": "", "confidence": 0.9, "quote": ""}]},
        "mi.title_topic": {"title": "A 커피 메뉴보드 시장 분석", "topic": "시장 · 경쟁사",
                           "scope_desc": {"market": "국내 F&B 디지털 사이니지 시장 규모·성장률, 도입 트렌드, 규제", "customer": "A 커피 매장 전략 · 확장 계획",
                                          "user": "점장 · 본사 운영자 · 손님", "competitor": "경쟁사 A · B · C 비교 → 삼성 강점"},
                           "req_summary": "전국 매장 메뉴보드 디지털 전환"},
        "mi.extract_claims_market": market_claims,
        "mi.extract_claims_customer": customer_claims,
        "mi.extract_claims_user": user_claims,
        "mi.compare_cells": compare_cells,
        "mi.verdicts": verdicts,
        "mi.strengths": strengths,
    })
    ai.web.update({
        "mi.web_scope": {"summary": "A 커피는 2025 사업보고서와 2026년 IR 자료, 매장 확장 보도자료를 공개했다."},
        "mi.web_candidates": {"summary": "외식 매장 디지털 메뉴보드 공급사로는 가나 디스플레이, 다라 사이니지, 마바 미디어가 많이 거론된다."},
        "mi.web_market": {"summary": MARKET_SUMMARY, "sources": [{"url": MARKET_URL, "title": "F&B 디지털 사이니지 동향 2026"}]},
        "mi.web_customer": {"summary": CUSTOMER_SUMMARY},
        "mi.web_user": {"summary": USER_SUMMARY},
        "mi.web_competitor": web_competitor,
    })
    ai.pages[MARKET_URL] = {"title": "F&B 디지털 사이니지 동향 2026", "text": MARKET_PAGE, "published_at": "2026-03-10"}


async def create(env: Any, **body: Any) -> dict[str, Any]:
    payload = {"customer_name": "A 커피", "requirements_text": A_REQ,
               "links": {"proposal_id": "prp_test1", "proposal_title": "A 커피 메뉴보드", "proposal_type": "standard"}, **body}
    r = await env.c.post("/v1/analyses", json=payload)
    assert r.status_code in (201, 202), r.text
    return r.json()


async def design(env: Any, aid: str) -> dict[str, Any]:
    r = await env.c.post(f"/v1/analyses/{aid}/design")
    assert r.status_code == 202, r.text
    await env.drain()
    return (await env.c.get(f"/v1/analyses/{aid}/design")).json()


async def run(env: Any, aid: str, **body: Any) -> str:
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json=body or {"mode": "full"})
    assert r.status_code == 202, r.text
    jid = r.json()["job_id"]
    await env.drain()
    return jid


async def add_qm55c(env: Any, aid: str) -> None:
    r = await env.c.post(f"/v1/analyses/{aid}/additions", json={"kind": "product", "ids": ["kb:model:mdl_LH55QMCEBGCXKR"]})
    assert r.status_code == 200, r.text


async def full_fb(env: Any, *, sources_mode: bool = False) -> str:
    """설계 → (QM55C 추가) → 분석까지 — 작업 id."""
    setup_fb(env, sources_mode=sources_mode)
    a = await create(env)
    aid = a["id"]
    await add_qm55c(env, aid)
    await design(env, aid)
    await run(env, aid)
    return aid
