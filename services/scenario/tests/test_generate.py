"""SC3 · SC3R(AC28–32) · SC4G 생성(AC33–39) · 경쟁사 치환(AC54)."""
from __future__ import annotations

from typing import Any

from sc_flow import (
    KM24C,
    QM55C,
    board,
    by_no,
    create,
    drain,
    generate,
    get,
    ops,
    parse,
    pick,
    scenes,
    timeline,
)


async def _ready(client: Any, *, type_: str = "with", solutions: list[str] | None = None, customer: str | None = None) -> str:
    sc = await create(client, type=type_)
    if customer:
        from winmate_scenario import repo

        def fn(d: dict[str, Any]) -> dict[str, Any]:
            d["customer_name"] = customer
            return d
        await repo.update(sc["id"], fn)
    await parse(client, sc["id"])
    await pick(client, sc["id"], solutions if type_ == "with" else None)
    return sc["id"]


# ── SC3 · SC3R ────────────────────────────────────────────

async def test_ac28_related_products_after_solution(client: Any, world: Any) -> None:
    sc = await create(client)
    await parse(client, sc["id"])
    t = await timeline(client, sc["id"])
    jang = next(r_ for r_ in t["roles"] if r_["name"] == "점장")
    lunch = next(s for s in t["slots"] if s["label"] == "점심 피크")
    # 시나리오 문장 속 「태블릿」(A1) → 갤럭시 탭 액티브
    await ops(client, sc["id"], {"op": "add_beat", "slot_id": lunch["id"], "role_id": jang["id"], "text": "태블릿으로 재고 확인", "new_scene": False})
    await pick(client, sc["id"], None, [QM55C, KM24C])
    r = await client.put(f"/v1/scenarios/{sc['id']}/solutions", json={"items": [{"solution_id": "magicinfo"}]})
    data = r.json()
    assert data["related_for"] == "MagicINFO"
    labels = [x["short"] for x in data["related_products"]]
    assert labels == ["Outdoor OH55C", "Galaxy Tab Active5"], labels
    # 추천 칩을 누르면 제품 칩으로(추천 목록에서 빠진다)
    rel = data["related_products"][0]
    r = await client.put(f"/v1/scenarios/{sc['id']}/products", json={"items": [QM55C, KM24C, {**rel, "source": "recommended"}]})
    assert [p["short"] for p in r.json()["product_picks"]][-1] == "Outdoor OH55C"
    assert "Outdoor OH55C" not in [x["short"] for x in r.json()["related_products"]]


async def test_product_ref_only_resolves_label(client: Any, world: Any) -> None:
    from sc_world import PRODUCTS
    sc = await create(client)
    world.kb.before = None

    async def model_detail(path: str, body: Any) -> dict[str, Any] | None:
        if path.startswith("/v1/models/"):
            return {"status": 404, "body": {"error": {"code": "NOT_FOUND", "message": "없음"}}}
        return None
    world.kb.before = model_detail
    r = await client.put(f"/v1/scenarios/{sc['id']}/products", json={"items": [{"ref": "kb:model:mdl_LH55QMCEBGCXKR"}]})
    assert r.status_code == 200, r.text
    assert r.json()["product_picks"][0]["label"] == "mdl_LH55QMCEBGCXKR"  # KB 를 못 읽으면 참조 id 그대로(지어내지 않음)
    assert PRODUCTS  # 픽스처 확인


async def test_ac29_ac30_ac31_without_routes_to_recommend(client: Any, world: Any) -> None:
    sid = await _ready(client, type_="without")
    r = await client.post(f"/v1/scenarios/{sid}:route-generate")
    assert r.json()["next"] == "SC3R"
    r = await client.post(f"/v1/scenarios/{sid}/recommendations:compute")
    assert r.status_code == 202
    await drain()
    recs = (await client.get(f"/v1/scenarios/{sid}/recommendations")).json()
    assert recs["status"] == "ready"
    assert (recs["applied_count"], recs["product_only_count"]) == (3, 1)
    items = {x["no"]: x for x in recs["items"]}
    assert items[2]["applied"] is False and items[2]["tag_label"] == "선택" and items[2]["solution_label"] == "MagicINFO · 시간대 레이아웃"
    assert items[3]["tag_label"] == "꼭 필요"
    assert items[1]["title"] == "오픈 — 메뉴보드가 아침 메뉴로 켜진다"
    ev1 = items[1]["evidence"][0]
    assert (ev1["kind"], ev1["text"]) == ("input_quote", "메뉴보드가 아침 메뉴로 켜져 있어야 한다")
    doc = await get(client, sid)
    assert ev1["text"] in doc["raw_text"]
    ev3 = items[3]["evidence"][0]
    assert ev3["case_text"] == "· 카페 사례 [00]건"
    assert recs["required_nos"] == [3, 4] and recs["industry_name"] == "외식 · 카페"
    # 토글 · 모두 적용
    r = await client.patch(f"/v1/scenarios/{sid}/recommendations/{items[1]['scene_id']}", json={"applied": False})
    assert r.json()["applied_count"] == 2
    r = await client.patch(f"/v1/scenarios/{sid}/recommendations/{items[1]['scene_id']}", json={"applied": True})
    assert r.json()["applied_solutions"] == ["MagicINFO", "SmartThings Pro"] and r.json()["off_nos"] == [2]
    # AC31: 적용 → with · 솔루션 2 · 장면 2 는 제품만
    r = await client.post(f"/v1/scenarios/{sid}/recommendations:commit", json={"mode": "apply"})
    doc = r.json()
    assert doc["type"] == "with" and [p["name"] for p in doc["solution_picks"]] == ["MagicINFO", "SmartThings Pro"]
    await generate(client, sid)
    items2 = await scenes(client, sid)
    assert by_no(items2, 2)["solutions"] == []
    assert by_no(items2, 1)["solution_chips"] == ["MagicINFO · 전원 스케줄"]


async def test_ac31_products_only(client: Any, world: Any) -> None:
    sid = await _ready(client, type_="without")
    await client.post(f"/v1/scenarios/{sid}:route-generate")
    await client.post(f"/v1/scenarios/{sid}/recommendations:compute")
    await drain()
    r = await client.post(f"/v1/scenarios/{sid}/recommendations:commit", json={"mode": "products_only"})
    assert r.json()["type"] == "without" and r.json()["solution_picks"] == []
    await generate(client, sid)
    assert all(s["solutions"] == [] for s in await scenes(client, sid))


async def test_ac32_with_but_no_solution_goes_to_recommend(client: Any, world: Any) -> None:
    sid = await _ready(client, type_="with", solutions=[])
    r = await client.post(f"/v1/scenarios/{sid}:route-generate")
    assert r.json() == {**r.json(), "next": "SC3R", "reason": "no_solution"}
    r = await client.post(f"/v1/scenarios/{sid}:route-generate")
    assert r.status_code == 200
    # 솔루션 · 제품이 모두 없으면 400
    sc = await create(client)
    await parse(client, sc["id"])
    r = await client.post(f"/v1/scenarios/{sc['id']}:route-generate")
    assert r.status_code == 400 and r.json()["error"]["code"] == "NOTHING_SELECTED"


# ── SC4G ────────────────────────────────────────────────

async def _events(job_id: str) -> list[dict[str, Any]]:
    from winmate_common.jobs import jobs
    out = []
    for _id, ev in await jobs().events(job_id, count=1000):
        out.append(ev)
    return out


async def test_ac33_stage_events_and_preview(client: Any, world: Any) -> None:
    sid = await _ready(client, solutions=["magicinfo", "smartthings_pro"])
    await client.post(f"/v1/scenarios/{sid}:route-generate")
    job_id = await generate(client, sid)
    evs = await _events(job_id)
    steps = [(e["data"]["stage"], e["data"]["status"], e["data"].get("note")) for e in evs if e["type"] == "step" and "stage" in e["data"]]
    order = []
    for st, _status, _note in steps:
        if not order or order[-1] != st:
            order.append(st)
    assert order == ["split", "write", "link", "confirm"], order
    write_notes = [n for st, status, n in steps if st == "write" and status == "run"]
    assert write_notes[0] == "장면 1 · 오픈 작성 중 (0 / 4 완료)"
    assert "장면 3 · 본사 배포 작성 중 (2 / 4 완료)" in write_notes
    split_note = next(n for st, _s, n in steps if st == "split")
    assert split_note == "오픈 · 점심 피크 · 본사 배포 · 마감"
    link_note = next(n for st, s, n in steps if st == "link" and s == "done")
    assert link_note == "MagicINFO 3장면 · SmartThings Pro 1장면"
    v = (await client.get(f"/v1/scenarios/{sid}/generation")).json()
    assert v["status"] == "done" and v["pct"] == 100 and v["done"] == 4
    assert [s["status"] for s in v["scenes"]] == ["done"] * 4
    assert v["summary"] == "with 솔루션 · MagicINFO · SmartThings Pro · QM55C ×3 · KM24C"


async def test_ac34_streaming_partials(client: Any, world: Any) -> None:
    from winmate_scenario import llm
    sid = await _ready(client, solutions=["magicinfo"])
    await client.post(f"/v1/scenarios/{sid}:route-generate")
    job_id = await generate(client, sid)
    logs = [e for e in await _events(job_id) if e["type"] == "log" and e["data"].get("partial_story")]
    if await llm.streaming_supported():
        assert logs, "스트리밍이 되면 부분 문장 log 이벤트가 있어야 한다"
        assert any(len(e["data"]["partial_story"]) > 5 for e in logs)
    else:
        assert logs == []


async def test_ac35_memo_applies_to_next_scene_only(client: Any, world: Any) -> None:
    from winmate_common.jobs import jobs
    sid = await _ready(client, solutions=["magicinfo", "smartthings_pro"])
    await client.post(f"/v1/scenarios/{sid}:route-generate")
    r = await client.post(f"/v1/scenarios/{sid}/generate", json={"scope": "all"})
    job_id = r.json()["job_id"]
    added = [False]

    async def before(path: str, body: Any) -> dict[str, Any] | None:
        prompt = "\n".join(m.get("content") or "" for m in (body or {}).get("messages") or [])
        if body and body.get("task") == "sc.write_scene" and "장면 라벨: 점심 피크" in prompt and not added[0]:
            added[0] = True
            await jobs().add_memo(job_id, "장면 3은 본사 담당자 시점으로")
        return None
    world.ai.before = before
    await drain()
    world.ai.before = None
    prompts = world.ai.prompts("sc.write_scene")
    p3 = [p for p in prompts if "장면 라벨: 본사 배포" in p]
    p1 = [p for p in prompts if "장면 라벨: 오픈" in p]
    assert p3 and "장면 3은 본사 담당자 시점으로" in p3[-1]
    assert all("장면 3은 본사 담당자 시점으로" not in p for p in p1)
    assert len(p1) == 1  # 장면 1 · 2 는 다시 쓰지 않는다
    v = (await client.get(f"/v1/scenarios/{sid}/generation")).json()
    assert v["memos"] == ["장면 3은 본사 담당자 시점으로"]


async def test_ac36_cancel_keeps_done_scenes(client: Any, world: Any) -> None:
    sid = await _ready(client, solutions=["magicinfo"])
    await client.post(f"/v1/scenarios/{sid}:route-generate")
    r = await client.post(f"/v1/scenarios/{sid}/generate", json={"scope": "all"})
    job_id = r.json()["job_id"]
    calls = [0]

    async def before(path: str, body: Any) -> dict[str, Any] | None:
        if body and body.get("task") == "sc.write_scene":
            calls[0] += 1
            if calls[0] == 3:  # 장면 3 쓰기 직전 「중지 · 입력 고치기」
                r2 = await client.post(f"/v1/scenarios/{sid}/generate:cancel")
                assert r2.status_code == 200
        return None
    world.ai.before = before
    await drain()
    world.ai.before = None
    doc = await get(client, sid)
    assert doc["status"] == "draft" and doc["step"] == 3 and doc["route"].endswith("/solutions")
    items = await scenes(client, sid)
    assert [s["status"] for s in items][:2] == ["done", "done"]
    assert by_no(items, 4)["status"] == "waiting"
    from winmate_common.jobs import jobs
    assert (await jobs().get(job_id)).status == "canceled"


async def test_ac37_failure_then_resume_same_thread(client: Any, world: Any) -> None:
    sid = await _ready(client, solutions=["magicinfo", "smartthings_pro"])
    await client.post(f"/v1/scenarios/{sid}:route-generate")
    r = await client.post(f"/v1/scenarios/{sid}/generate", json={"scope": "all"})
    job_id = r.json()["job_id"]
    down = [True]

    async def before(path: str, body: Any) -> dict[str, Any] | None:
        prompt = "\n".join(m.get("content") or "" for m in (body or {}).get("messages") or [])
        if down[0] and body and body.get("task") == "sc.write_scene" and "장면 라벨: 본사 배포" in prompt:
            return {"status": 503, "body": {"error": {"code": "UPSTREAM_UNAVAILABLE", "message": "mock 장애"}}}
        return None
    world.ai.before = before
    await drain()
    doc = await get(client, sid)
    assert doc["status"] == "failed" and doc["route"].endswith(f"/generate/{job_id}")
    v = (await client.get(f"/v1/scenarios/{sid}/generation")).json()
    assert v["status"] == "failed" and v["failed_reason"]
    rows = {x["id"]: x for x in (await client.get("/v1/scenarios")).json()["items"]}
    assert (rows[sid]["status_label"], rows[sid]["status_action"]) == ("생성 멈춤", "다시 시도")
    before_counts = {k: sum(1 for p in world.ai.prompts("sc.write_scene") if f"장면 라벨: {k}" in p) for k in ("오픈", "점심 피크")}
    down[0] = False
    r = await client.post(f"/v1/scenarios/{sid}/generate:resume", json={"job_id": job_id})
    assert r.status_code == 202 and r.json()["job_id"] == job_id
    await drain()
    world.ai.before = None
    after_counts = {k: sum(1 for p in world.ai.prompts("sc.write_scene") if f"장면 라벨: {k}" in p) for k in ("오픈", "점심 피크")}
    assert after_counts == before_counts  # 장면 1 · 2 는 LLM 을 다시 부르지 않는다
    doc = await get(client, sid)
    assert doc["status"] == "done"
    assert [s["status"] for s in await scenes(client, sid)] == ["done"] * 4


async def test_ac38_unsupported_numbers(client: Any, world: Any) -> None:
    sc = await board(client)
    s3 = by_no(await scenes(client, sc["id"]), 3)
    assert "320개" in s3["story"] and "[00]분" in s3["story"] and "10분" not in s3["story"]
    assert len(s3["confirm_tokens"]) == 1 and s3["confirm_tokens"][0]["text"] == "[00]"


async def test_ac39_confidential_anonymized_and_restored(client: Any, world: Any, monkeypatch: Any) -> None:
    monkeypatch.setenv("MOCK_ENFORCE_CONFIDENTIAL", "true")
    monkeypatch.setenv("LLM_ALLOW_CONFIDENTIAL", "false")
    sid = await _ready(client, solutions=["magicinfo", "smartthings_pro"], customer="A 커피")
    await client.post(f"/v1/scenarios/{sid}:route-generate")
    await generate(client, sid)
    calls = world.ai.calls("sc.write_scene")
    opens = [c for c in calls if any("장면 라벨: 오픈" in (m.get("content") or "") for m in c["messages"])]
    assert any(c.get("confidential") for c in opens)  # 먼저 기밀로 보냈다가
    anon = [c for c in opens if not c.get("confidential")]
    assert anon, "차단되면 익명화해 confidential:false 로 다시 보낸다"
    text = "\n".join(m.get("content") or "" for m in anon[-1]["messages"])
    assert "A 커피" not in text and "고객사" in text
    s1 = by_no(await scenes(client, sid), 1)
    assert "A 커피" in s1["story"] and "고객사" not in s1["story"]
    doc = await get(client, sid)
    assert doc["anonymized"] is True and doc["status"] == "done"


async def test_ac54_competitor_names_replaced(client: Any, world: Any) -> None:
    sid = await _ready(client, solutions=["magicinfo", "smartthings_pro"])
    t = await timeline(client, sid)
    beat = next(b for s in t["scenes"] for b in s["beats"] if b["text"] == "화면 자동 종료 확인 후 마감")
    await ops(client, sid, {"op": "set_beat", "beat_id": beat["id"], "text": "화면 자동 종료 확인 후 마감 #mock:competitor"})
    await client.post(f"/v1/scenarios/{sid}:route-generate")
    await generate(client, sid)
    s4 = by_no(await scenes(client, sid), 4)
    from winmate_scenario import policy
    blob = " ".join([s4["title"], s4["story"], *(b["text"] for b in s4["beats"])])
    assert "기존 시스템" in blob
    for name in policy.competitor_names():
        assert name not in blob, name
    assert "경쟁사" not in blob
