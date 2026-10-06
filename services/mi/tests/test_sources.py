"""출처 · 검증(두 모드) — AC-MI-28 · 29 · 30 · 31 · 32 · 33 · 34 · 35 · 36 · 38 · 39 · 40 · 41 · 42 · 43 · 44 · 89."""
from __future__ import annotations

import json
import re
from typing import Any

from mi_scenario import MARKET_PAGE, MARKET_URL, add_qm55c, compare_cells, create, design, full_fb, market_claims, run, setup_fb

URL2 = "https://news.example.com/menuboard-2026"
PAGE2 = "업계 기사. 디지털 메뉴보드 도입 매장이 꾸준히 늘고 있다. 키오스크와 메뉴보드 연동이 확산되고 있다."


async def _market_claim(env: Any, aid: str, frag: str) -> dict[str, Any]:
    res = (await env.c.get(f"/v1/analyses/{aid}/claims?tab=market")).json()
    return next(c for c in res["items"] if frag in c["text"])


def _claims(*claims: dict[str, Any], blocks: dict[str, Any] | None = None) -> Any:
    def fn(_body: dict[str, Any]) -> dict[str, Any]:
        b = blocks or {"size_label": "시장", "size_unit": "억 원", "size_series": [], "trends": [], "regulations": []}
        return {"blocks": b, "claims": list(claims)}

    return fn


def _urls(obj: Any) -> set[str]:
    return set(re.findall(r"https?://[^\s\"'<>)\]]+", json.dumps(obj, ensure_ascii=False)))


async def _go(env: Any, *, sources_mode: bool = False) -> str:
    aid = (await create(env))["id"]
    await add_qm55c(env, aid)
    await design(env, aid)
    await run(env, aid)
    return aid


async def test_ac28_ac29_ac40_sources_mode(env):
    setup_fb(env, sources_mode=True)
    env.ai.web["mi.web_market"] = {"summary": "요약", "sources": [{"url": MARKET_URL, "title": "동향"}, {"url": URL2, "title": "기사"}]}
    env.ai.pages[URL2] = {"title": "업계 기사", "text": PAGE2, "published_at": "2026-02-01"}
    env.ai.llm["mi.extract_claims_market"] = _claims(
        {"local_id": "a", "text": "디지털 메뉴보드를 쓰는 매장이 최근 3년간 42% 늘었습니다.", "metric_key": "growth",
         "citations": [{"evidence_id": "E1", "quote": "디지털 메뉴보드를 쓰는 매장이 3년간 42% 증가했다"}]},
        {"local_id": "b", "text": "메뉴보드를 쓰는 매장이 3년간 42% 늘었어요.", "metric_key": "growth_b", "metric_label": "메뉴보드 매장 증가율",
         "citations": [{"evidence_id": "E1", "quote": "디지털 메뉴보드를 쓰는 매장이 3년간 42% 증가했다"},
                       {"evidence_id": "E2", "quote": "디지털 메뉴보드 도입 매장이 꾸준히 늘고 있다"}]},
        blocks={"size_label": "시장", "size_unit": "억 원", "size_series": [], "trends": [{"title": "확산", "claim": "a"}, {"title": "확산 2", "claim": "b"}],
                "regulations": []})
    aid = await _go(env, sources_mode=True)
    a = await _market_claim(env, aid, "최근 3년간 42%")
    assert a["status"] == "matched" and a["label"] == "원문 일치"
    det = (await env.c.get(f"/v1/analyses/{aid}/claims/{a['id']}")).json()
    card = det["cards"][0]
    assert card["kind"] == "web" and card["status_label"] == "원문 일치"
    assert "원문 열기" in card["actions"] and "각주로 복사" in card["actions"] and "42% 증가" in card["quote_highlight"]
    b = await _market_claim(env, aid, "메뉴보드를 쓰는 매장이 3년간")
    assert b["status"] == "needs_check" and b["label"] == "확인 필요 1"
    det = (await env.c.get(f"/v1/analyses/{aid}/claims/{b['id']}")).json()
    bad = next(c for c in det["cards"] if c["status"] != "matched")
    assert bad["reason"] == "수치 없이 흐름만 말해 42%를 뒷받침하지 못해요."
    fx = (await env.c.get(f"/v1/analyses/{aid}/fix-items")).json()["items"]
    assert next(f for f in fx if f["claim_id"] == b["id"])["sub_text"] == "출처 2건 중 1건만 수치가 있음"
    # AC-MI-40 — needs_check 인용을 빼면 원문 일치, 마지막까지 빼면 missing + 확정 필요 항목
    r = await env.c.delete(f"/v1/analyses/{aid}/claims/{b['id']}/sources/{bad['source_id']}")
    assert r.status_code == 200 and r.json()["claim"]["status"] == "matched"
    good = next(c for c in det["cards"] if c["status"] == "matched")
    r = await env.c.delete(f"/v1/analyses/{aid}/claims/{b['id']}/sources/{good['source_id']}")
    assert r.json()["claim"]["status"] == "missing" and r.json()["fix_id"]
    # AC-MI-89 — sources 모드 웹 출처 카드에는 원문 열기
    caps = (await env.c.get("/v1/capabilities")).json()
    assert caps["websearch"]["returns_sources"] is True


async def test_ac30_ac89_summary_only_no_foreign_urls(env):
    aid = await full_fb(env)
    c = await _market_claim(env, aid, "6,700억 원")
    assert c["status"] == "needs_check"
    det = (await env.c.get(f"/v1/analyses/{aid}/claims/{c['id']}")).json()
    card = det["cards"][0]
    assert card["kind"] == "websearch_summary" and card["status"] == "unverifiable" and card["status_label"] == "확인 필요"
    assert "원문 열기" not in card["actions"] and "URL 붙여 확인" in card["actions"] and card["url"] is None
    srcs = (await env.c.get(f"/v1/analyses/{aid}/sources")).json()["items"]
    allowed = {s["url"] for s in srcs if s.get("url") and s["kind"] in ("web", "kb_case", "kb_official")}
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    bundle = (await env.c.get(f"/v1/analyses/{aid}/bundle?target=vp")).json()
    for obj in (res, srcs, bundle):
        for u in _urls(obj):
            assert u in allowed or u.startswith("https://www.samsung.com"), u
    caps = (await env.c.get("/v1/capabilities")).json()
    assert caps["websearch"]["returns_sources"] is False and caps["search_api"]["provider"] == "none"


async def test_ac31_ac39_summary_url_fetched(env):
    setup_fb(env)
    url = "https://example.org/report.pdf"
    env.ai.web["mi.web_market"] = {"summary": f"디지털 메뉴보드를 쓰는 매장이 3년간 42% 증가했다는 보고서가 있다({url})."}
    env.ai.pages[url] = {"title": "보고서", "text": MARKET_PAGE, "published_at": "2026-03-10"}
    env.ai.llm["mi.extract_claims_market"] = _claims(
        {"local_id": "a", "text": "디지털 메뉴보드를 쓰는 매장이 3년간 42% 늘었어요.", "metric_key": "growth",
         "citations": [{"evidence_id": "E1", "quote": "디지털 메뉴보드를 쓰는 매장이 3년간 42% 증가했다."},
                       {"evidence_id": "E2", "quote": "디지털 메뉴보드를 쓰는 매장이 3년간 42% 증가했다는 보고서가 있다"}]},
        blocks={"size_label": "", "size_unit": "", "size_series": [], "trends": [{"title": "확산", "claim": "a"}], "regulations": []})
    aid = await _go(env)
    assert any(f["url"] == url for f in env.ai.fetch_calls())
    c = await _market_claim(env, aid, "42%")
    assert c["status"] == "matched"                      # 같은 수치의 요약 인용은 떼어짐(AC-MI-39)
    srcs = (await env.c.get(f"/v1/analyses/{aid}/sources?tab=market")).json()["items"]
    web = next(s for s in srcs if s["kind"] == "web")
    assert web["mode"] == "summary_only" and web["url"] == url
    summ = (await env.c.get(f"/v1/analyses/{aid}/sources")).json()["items"]
    assert any(s["kind"] == "websearch_summary" and s["state"] == "excluded" and s.get("excluded_reason") == "superseded" for s in summ)


async def test_ac32_failed_url_never_shows(env):
    setup_fb(env)
    bad = "https://competitor.example/cms"
    env.ai.web["mi.web_market"] = {"summary": f"국내 F&B 디지털 사이니지 시장 규모는 2025년 6,700억 원 수준이다. 자세한 내용은 {bad} 참고."}
    env.ai.llm["mi.extract_claims_market"] = _claims(
        {"local_id": "a", "text": f"시장 규모는 2025년 6,700억 원이에요. 자세한 내용은 {bad}", "metric_key": "size",
         "citations": [{"evidence_id": "E1", "quote": "국내 F&B 디지털 사이니지 시장 규모는 2025년 6,700억 원 수준이다"}]},
        blocks={"size_label": "시장", "size_unit": "억 원", "size_series": [{"year": 2025, "claim": "a"}], "trends": [], "regulations": []})
    aid = await _go(env)
    assert any(f["url"] == bad for f in env.ai.fetch_calls())
    everything = [(await env.c.get(f"/v1/analyses/{aid}/result")).json(), (await env.c.get(f"/v1/analyses/{aid}/sources")).json(),
                  (await env.c.get(f"/v1/analyses/{aid}/bundle?target=proposal_mi")).json(),
                  (await env.c.get(f"/v1/analyses/{aid}/claims?tab=market")).json()]
    from winmate_mi import bundle as B
    from winmate_mi import store as R

    doc = await R.call(R.get_analysis, aid)
    v = await R.call(R.get_version, aid, 1)
    everything.append(B.export_document(doc, v, "pdf_report", "internal"))
    assert bad not in json.dumps(everything, ensure_ascii=False)


async def test_ac33_unsupported_number(env):
    setup_fb(env)
    env.ai.llm["mi.extract_claims_market"] = _claims(
        {"local_id": "a", "text": "시장 규모는 5,000억 원이에요.", "metric_key": "market_size", "metric_label": "시장 규모",
         "citations": [{"evidence_id": "E1", "quote": "국내 F&B 디지털 사이니지 시장 규모는 2025년 6,700억 원 수준이다"}]},
        blocks={"size_label": "시장", "size_unit": "억 원", "size_series": [{"year": 2025, "claim": "a"}], "trends": [], "regulations": []})
    aid = await _go(env)
    c = await _market_claim(env, aid, "시장 규모는")
    assert c["text"] == "시장 규모는 [00]억 원이에요."
    fx = [f for f in (await env.c.get(f"/v1/analyses/{aid}/fix-items")).json()["items"] if f["claim_id"] == c["id"]]
    assert len(fx) == 1 and fx[0]["reason_code"] == "NUMBER_UNSUPPORTED" and fx[0]["unit"] == "억 원"


async def test_ac34_conflict_two_sources(env):
    setup_fb(env, sources_mode=True)
    u1, u2 = "https://a.example.com/r1", "https://b.example.com/r2"
    env.ai.web["mi.web_market"] = {"summary": "요약", "sources": [{"url": u1, "title": "보고서 1"}, {"url": u2, "title": "보고서 2"}]}
    env.ai.pages[u1] = {"title": "시장 보고서 2026", "text": "국내 시장 규모는 5,000억 원이다.", "published_at": "2026-03-01"}
    env.ai.pages[u2] = {"title": "시장 보고서 2025", "text": "국내 시장 규모는 6,700억 원이다.", "published_at": "2025-06-01"}
    env.ai.llm["mi.extract_claims_market"] = _claims(
        {"local_id": "a", "text": "국내 시장 규모는 5,000억 원이에요.", "metric_key": "size",
         "citations": [{"evidence_id": "E1", "quote": "국내 시장 규모는 5,000억 원이다"}, {"evidence_id": "E2", "quote": "국내 시장 규모는 6,700억 원이다"}]},
        blocks={"size_label": "시장", "size_unit": "억 원", "size_series": [{"year": 2025, "claim": "a"}], "trends": [], "regulations": []})
    aid = await _go(env, sources_mode=True)
    c = await _market_claim(env, aid, "국내 시장 규모는")
    assert c["status"] == "conflict" and c["label"] == "출처 간 값 다름"
    assert "5,000억 원" in c["text"] and "6,700억 원" in c["text"]
    det = (await env.c.get(f"/v1/analyses/{aid}/claims/{c['id']}")).json()
    assert det["conflict"]["diff_ratio"] == 0.34
    prim = det["conflict"]["primary_source_id"]
    assert next(x for x in det["cards"] if x["source_id"] == prim)["title"] == "시장 보고서 2026"
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    assert any(ch["kind"] == "conflict" for ch in res["check_chips"])


async def test_ac34_no_conflict_under_20(env):
    setup_fb(env, sources_mode=True)
    u1, u2 = "https://a.example.com/r1", "https://b.example.com/r2"
    env.ai.web["mi.web_market"] = {"summary": "요약", "sources": [{"url": u1, "title": "보고서 1"}, {"url": u2, "title": "보고서 2"}]}
    env.ai.pages[u1] = {"title": "시장 보고서 2026", "text": "국내 시장 규모는 5,000억 원이다.", "published_at": "2026-03-01"}
    env.ai.pages[u2] = {"title": "시장 보고서 2025", "text": "국내 시장 규모는 5,900억 원이다.", "published_at": "2025-06-01"}
    env.ai.llm["mi.extract_claims_market"] = _claims(
        {"local_id": "a", "text": "국내 시장 규모는 5,000억 원이에요.", "metric_key": "size",
         "citations": [{"evidence_id": "E1", "quote": "국내 시장 규모는 5,000억 원이다"}, {"evidence_id": "E2", "quote": "국내 시장 규모는 5,900억 원이다"}]},
        blocks={"size_label": "시장", "size_unit": "억 원", "size_series": [{"year": 2025, "claim": "a"}], "trends": [], "regulations": []})
    aid = await _go(env, sources_mode=True)
    c = await _market_claim(env, aid, "국내 시장 규모는")
    assert c["status"] != "conflict"


async def test_ac35_stale_kept_when_no_replacement(env):
    setup_fb(env, sources_mode=True)
    u = "https://old.example.com/2023"
    env.ai.web["mi.web_market"] = {"summary": "요약", "sources": [{"url": u, "title": "오래된 보고서"}]}
    env.ai.pages[u] = {"title": "시장 보고서 2023", "text": "국내 시장 규모는 4,000억 원이다.", "published_at": "2023-08-01"}
    env.ai.llm["mi.extract_claims_market"] = _claims(
        {"local_id": "a", "text": "국내 시장 규모는 4,000억 원이에요.", "metric_key": "size",
         "citations": [{"evidence_id": "E1", "quote": "국내 시장 규모는 4,000억 원이다"}]},
        blocks={"size_label": "시장", "size_unit": "억 원", "size_series": [{"year": 2023, "claim": "a"}], "trends": [], "regulations": []})
    aid = await _go(env, sources_mode=True)
    qs = [c["query"] for c in env.ai.web_calls("mi.web_market")]
    assert any(q.endswith(" 최근") for q in qs)
    c = await _market_claim(env, aid, "국내 시장 규모는")
    assert c["status"] == "stale" and c["label"] == "자료 연도 오래됨"


async def test_ac35_stale_replaced(env):
    setup_fb(env, sources_mode=True)
    old, new = "https://old.example.com/2023", "https://new.example.com/2026"

    def web(body: dict[str, Any]) -> dict[str, Any]:
        if body["query"].endswith(" 최근"):
            return {"summary": "요약", "sources": [{"url": new, "title": "새 보고서"}]}
        return {"summary": "요약", "sources": [{"url": old, "title": "오래된 보고서"}]}

    env.ai.web["mi.web_market"] = web
    env.ai.pages[old] = {"title": "시장 보고서 2023", "text": "국내 시장 규모는 4,000억 원이다.", "published_at": "2023-08-01"}
    env.ai.pages[new] = {"title": "시장 보고서 2026", "text": "국내 시장 규모는 5,000억 원이다.", "published_at": "2026-04-01"}
    env.ai.llm["mi.extract_claims_market"] = _claims(
        {"local_id": "a", "text": "국내 시장 규모는 5,000억 원이에요.", "metric_key": "size", "citations": [{"evidence_id": "E1", "quote": "국내 시장 규모는 5,000억 원이다"}]},
        blocks={"size_label": "시장", "size_unit": "억 원", "size_series": [{"year": 2026, "claim": "a"}], "trends": [], "regulations": []})
    aid = await _go(env, sources_mode=True)
    c = await _market_claim(env, aid, "국내 시장 규모는")
    assert c["status"] == "matched"
    srcs = (await env.c.get(f"/v1/analyses/{aid}/sources")).json()["items"]
    stale = next(s for s in srcs if s.get("url") == old)
    assert stale["state"] == "excluded" and stale["excluded_reason"] == "stale"


async def test_ac36_ac51_samsung_spec_from_kb(env):
    aid = await full_fb(env)
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    row = next(r for r in res["competitor"]["table"]["rows"] if r["name"] == "저전력 운영")
    cell = row["cells"]["samsung"]
    assert cell["text"] == "QM55C 소비전력 154 W" and cell["status"] == "matched"
    det = (await env.c.get(f"/v1/analyses/{aid}/claims/{cell['claim_ids'][0]}")).json()
    assert det["cards"][0]["kind"] == "kb_official" and det["cards"][0]["status"] == "matched"
    fx = (await env.c.get(f"/v1/analyses/{aid}/fix-items")).json()["items"]
    assert not any(f.get("cell_ref") == f"{row['criterion_id']}:samsung" for f in fx)
    # KB 에 없는 삼성 값(피크타임 메뉴 전환 → 메시지 없음)은 사내 스펙 값 필요 + Spec 시트에서
    empty = [r for r in res["competitor"]["table"]["rows"] if r["cells"]["samsung"]["placeholder"]]
    if empty:
        it = next(f for f in fx if f.get("cell_ref") == f"{empty[0]['criterion_id']}:samsung")
        assert it["sub_text"] == "사내 스펙 값 필요" and it["actions"] == ["Spec 시트에서"]


async def test_ac38_summary_corroborated(env):
    setup_fb(env)
    env.ai.web["mi.web_market"] = {"summary": "국내 F&B 디지털 사이니지 시장 규모는 2025년 1조 원이다."}
    env.ai.web["mi.web_corroborate"] = {"summary": "업계는 F&B 사이니지 시장 규모를 1.1조 원으로 본다."}
    env.ai.llm["mi.extract_claims_market"] = _claims(
        {"local_id": "a", "text": "국내 F&B 디지털 사이니지 시장 규모는 2025년 1조 원이에요.", "metric_key": "size",
         "citations": [{"evidence_id": "E1", "quote": "국내 F&B 디지털 사이니지 시장 규모는 2025년 1조 원이다"}]},
        blocks={"size_label": "시장", "size_unit": "조 원", "size_series": [{"year": 2025, "claim": "a"}], "trends": [], "regulations": []})
    aid = await _go(env)
    c = await _market_claim(env, aid, "1조 원")
    assert c["status"] == "needs_check"
    det = (await env.c.get(f"/v1/analyses/{aid}/claims/{c['id']}")).json()
    assert any(x["reason_code"] == "SUMMARY_CORROBORATED" for x in det["cards"])
    assert any(x["reason"] == "검색 요약 2건이 같은 값을 말해요 · 원문은 확인 전이에요." for x in det["cards"])


async def test_ac38_summary_conflict(env):
    setup_fb(env)
    env.ai.web["mi.web_market"] = {"summary": "국내 F&B 디지털 사이니지 시장 규모는 2025년 1조 원이다."}
    env.ai.web["mi.web_corroborate"] = {"summary": "다른 조사는 F&B 사이니지 시장 규모를 1.5조 원으로 본다."}
    env.ai.llm["mi.extract_claims_market"] = _claims(
        {"local_id": "a", "text": "국내 F&B 디지털 사이니지 시장 규모는 2025년 1조 원이에요.", "metric_key": "size",
         "citations": [{"evidence_id": "E1", "quote": "국내 F&B 디지털 사이니지 시장 규모는 2025년 1조 원이다"}]},
        blocks={"size_label": "시장", "size_unit": "조 원", "size_series": [{"year": 2025, "claim": "a"}], "trends": [], "regulations": []})
    aid = await _go(env)
    c = await _market_claim(env, aid, "1조 원")
    assert c["status"] == "conflict"


async def test_ac41_ac42_numbering_and_badges(env):
    aid = await full_fb(env)
    lst = (await env.c.get(f"/v1/analyses/{aid}/claims?tab=market")).json()
    ns = [x["n"] for it in lst["items"] for x in it["citations"]]
    first = []
    for n in ns:
        if n not in first:
            first.append(n)
    assert first == list(range(1, len(first) + 1))
    ts = lst["tab_sources"]
    assert lst["summary_text"].startswith(f"이 탭 출처 {ts['total']}건 · 공개 자료 {ts['public']} · 사내 사례 DB {ts['kb_case']}")
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    assert lst["badges"] == {t["area"]: t["needs_check"] for t in res["tabs"]}
    assert lst["needs_check_total"] == sum(t["needs_check"] for t in res["tabs"]) == res["needs_check_total"]
    srcs = (await env.c.get(f"/v1/analyses/{aid}/sources?tab=market&kind=kb_case")).json()
    assert srcs["counts"]["total"] == ts["kb_case"]


async def test_ac43_confidential_competitor_number(env):
    setup_fb(env)
    fid = env.files.add("경쟁사 단가표.pdf", ["다라 사이니지 메뉴보드 단가 120만 원"], confidential=True)
    env.ai.llm["mi.classify_file"] = {"doc_kind": "price_list", "classification": "confidential", "title": "단가표"}

    def cells(body: dict[str, Any]) -> dict[str, Any]:
        out = compare_cells(body)
        for c in out["cells"]:
            if "전력" in body["messages"][-1]["content"] and c["text"] == "[확인 필요]":
                pass
        prompt = body["messages"][-1]["content"]
        m = re.search(r'"id": "(cmp_[A-Z0-9]+)", "name": "다라 사이니지"', prompt)
        m2 = re.search(r'"id": "(crt_[A-Z0-9]+)", "name": "저전력 운영"', prompt)
        if m and m2:
            for c in out["cells"]:
                if c["competitor_id"] == m.group(1) and c["criterion_id"] == m2.group(1):
                    c["text"] = "메뉴보드 단가 120만 원"
                    c["citations"] = [{"evidence_id": "E1", "quote": "다라 사이니지 메뉴보드 단가 120만 원"}]
        return out

    env.ai.llm["mi.compare_cells"] = cells
    aid = (await create(env, file_ids=[fid]))["id"]
    await add_qm55c(env, aid)
    await design(env, aid)
    await run(env, aid)
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    row = next(r for r in res["competitor"]["table"]["rows"] if r["name"] == "저전력 운영")
    col = next(c["key"] for c in res["competitor"]["table"]["columns"] if c["sub"] == "다라 사이니지")
    cell = row["cells"][col]
    assert cell["text"] == "메뉴보드 단가 [00]만 원" and cell["placeholder"]
    fx = (await env.c.get(f"/v1/analyses/{aid}/fix-items")).json()["items"]
    assert any(f["claim_id"] in cell["claim_ids"] and f["competitor"] for f in fx)


async def test_ac44_add_source_url(env):
    aid = await full_fb(env)
    c = await _market_claim(env, aid, "6,700억 원")
    url = "https://stats.example.go.kr/fnb"
    env.ai.pages[url] = {"title": "통계", "text": "국내 F&B 디지털 사이니지 시장 규모는 2025년 6,700억 원으로 집계됐다.", "published_at": "2026-01-15"}
    r = await env.c.post(f"/v1/analyses/{aid}/sources", json={"url": url, "claim_id": c["id"]})
    assert r.status_code == 202
    mid = (await env.c.get(f"/v1/analyses/{aid}/claims/{c['id']}")).json()
    assert mid["claim"]["status"] == "checking"
    await env.drain()
    det = (await env.c.get(f"/v1/analyses/{aid}/claims/{c['id']}")).json()
    new = next(x for x in det["cards"] if x["url"] == url)
    assert new["status"] == "matched" and det["claim"]["status"] in ("matched", "needs_check")
