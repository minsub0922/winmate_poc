"""목록(MI0) · 30일 재확인 — AC-MI-75 · 77 · 78."""
from __future__ import annotations

from mi_scenario import full_fb, run

from winmate_common.ids import now_iso
from winmate_common.jobs import jobs
from winmate_mi import service
from winmate_mi import store as R


def _doc(**kw):
    from winmate_common.context import set_user

    set_user("u_test", "테스터")
    d = service.new_doc(customer_name=kw.pop("customer", "고객"))
    d.update(owner_id="u_test", owner_name="테스터", title=kw.pop("title", "작업"), scope={"areas": ["market", "competitor"], "mode": "auto", "reasons": {},
                                                                                     "reduced": []},
             segment={"code": "FB", "mode": "auto"}, **kw)
    return d


async def test_ac75_list_header_filters_banner_actions(env):
    docs = [
        _doc(title="완료 작업", status="done", result_version=1, analyzed_at=now_iso(), run={"fix_open": 2, "sources_used": 18}),
        _doc(title="업데이트 1", status="upd", result_version=2, analyzed_at=now_iso(),
             upd_changes=[{"kind": "competitor_new_product", "title": "경쟁사 B 신제품 발표", "affected_areas": ["competitor"]}]),
        _doc(title="업데이트 2", status="upd", result_version=1, analyzed_at=now_iso(),
             upd_changes=[{"kind": "report_revised", "title": "시장 리포트 개정", "affected_areas": ["market"]}]),
        _doc(title="진행 작업", status="running", run={"stage": "organize", "sources_total": 12, "started_at": now_iso()}),
        _doc(title="작성 작업", status="draft", last_screen="scope"),
    ]
    for d in docs:
        await R.call(R.put_analysis, d)
    out = (await env.c.get("/v1/analyses")).json()
    assert out["header"] == "분석 5건 · 업데이트 필요 2건 · 확정 필요 수치가 남은 작업 1건"
    assert out["counts"] == {"all": 5, "run": 1, "done": 1, "upd": 2, "draft": 1}
    assert out["banner"]["title"] == "2건은 다시 분석을 권해요."
    assert out["banner"]["text"] == "분석한 지 30일이 지났고, 그사이 경쟁사 신제품 발표와 시장 리포트 개정이 확인됐어요."
    acts = {i["title"]: i["action"]["label"] for i in out["items"]}
    assert acts == {"완료 작업": "수치 확정", "업데이트 1": "다시 분석", "업데이트 2": "다시 분석", "진행 작업": "진행 보기", "작성 작업": "이어서"}
    notes = {i["title"]: i["note"] for i in out["items"]}
    assert notes["완료 작업"] == "출처 18곳 · 확정 필요 수치 2" and notes["진행 작업"] == "정리 중 · 출처 12곳 확인" and notes["작성 작업"] == "분석 범위까지 입력"
    assert notes["업데이트 1"] == "경쟁사 신제품 감지 1건"
    run_only = (await env.c.get("/v1/analyses?status=run")).json()["items"]
    assert [i["title"] for i in run_only] == ["진행 작업"]
    upd = next(i for i in out["items"] if i["title"] == "업데이트 1")
    assert [m["label"] for m in upd["menu"]] == ["바뀐 부분만 다시 분석", "전체 다시 분석", "지난 결과 열기", "제안서 MI 섹션으로 보내기", "복제해서 새 분석"]
    assert upd["menu"][0]["hint"] == "경쟁 · 약 40초"


async def test_ac77_recheck_new_product_then_changed_only(env):
    aid = await full_fb(env)
    env.ai.web["mi.web_recheck"] = lambda body: ({"summary": "가나 디스플레이가 2026년 11월 새 메뉴보드 GX-55를 출시했다."}
                                                 if "가나 디스플레이" in body["query"] else {"summary": ""})
    env.ai.llm["mi.recheck_news"] = lambda body: ({"items": [{"product": "GX-55", "date": "2026-11-02", "summary": "새 메뉴보드 출시"}]}
                                                  if "가나 디스플레이" in body["messages"][-1]["content"] else {"items": []})
    r = await env.c.post(f"/v1/analyses/{aid}/recheck")
    assert r.status_code == 202
    await env.drain()
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "upd"
    ch = (await env.c.get(f"/v1/analyses/{aid}/changes")).json()
    assert ch["head"] == "바뀐 자료 1건" and ch["items"][0]["kind"] == "competitor_new_product" and ch["affected_areas"] == ["competitor"]
    assert ch["items"][0]["title"] == "경쟁사 A 신제품 발표 · GX-55" and "가나" not in ch["summary"]
    lst = (await env.c.get("/v1/analyses")).json()
    row = next(i for i in lst["items"] if i["id"] == aid)
    assert row["note"] == "경쟁사 신제품 감지 1건" and lst["banner"]["n"] == 1
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    assert res["upd"]["text"] == "분석한 지 30일이 지났어요 · 바뀐 자료 1건"
    env.ai.reset_calls()
    await run(env, aid, mode="changed_only", areas=ch["affected_areas"])
    assert {c["task"] for c in env.ai.web_calls()} == {"mi.web_competitor"}
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "done" and a["version"] == 2


async def test_ac78_recheck_no_changes(env):
    aid = await full_fb(env)
    before = (await jobs().schedules(service="mi", ref=aid))[0]["run_at"]
    await env.c.post(f"/v1/analyses/{aid}/recheck")
    await env.drain()
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "done"
    s = await jobs().schedules(service="mi", ref=aid)
    assert len(s) == 1 and s[0]["run_at"] >= before
    assert any(m["text"] == "30일 재확인 · 바뀐 자료 없음" for m in (await R.call(R.get_analysis, aid))["memos"])
