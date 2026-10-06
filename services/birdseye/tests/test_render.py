"""BE5G · BE5 · BE5V · BE5Z · BE6 · BE0 — 렌더(image 렌더 API in-process) · 수정 요청 · 존 포인트 · 내보내기 · 목록(AC 1–5 · 40–61)."""
from __future__ import annotations

import io
import json
import zipfile

import pytest
from be_kit import create, drain, seed_golden

from winmate_common.jobs import jobs

DESC = "강남 플래그십 스토어 1층 로비. 약 120평, 층고 4.5m, 정면이 전면 유리창이라 낮에는 밝고 저녁엔 외부에서 내부가 잘 보임. 중앙에 기둥 2개."


@pytest.fixture
def renders(monkeypatch):
    """image POST /v1/renders 인자 기록(그대로 보낸다)."""
    from winmate_common.client import ServiceClient

    from winmate_birdseye import edits, render

    calls: list[dict] = []

    class Spy(ServiceClient):
        async def post(self, path, *args, **kw):  # type: ignore[override]
            if self.target == "image":
                calls.append({"path": path, "json": kw.get("json")})
            return await super().post(path, *args, **kw)

    monkeypatch.setattr(render, "ServiceClient", Spy)
    monkeypatch.setattr(edits, "ServiceClient", Spy)
    return calls


async def _ready(client, *, proposal: bool = False) -> str:
    b = await create(client, description=DESC, title="강남 플래그십 1층 로비")
    await seed_golden(b["id"], layout=True)
    if proposal:
        r = await client.post(f"/v1/birdseyes/{b['id']}/usages", json={"service": "proposal", "ref": "prp_1", "label": "A 커피 메뉴보드 제안", "version": 1})
        assert r.status_code == 201
    return b["id"]


async def _events(job_id: str) -> list[tuple[str, dict]]:
    evs = await jobs().events(job_id, "0", count=500)
    return [(e.get("type") or e.get("event") or "", e) for _id, e in evs]


async def test_ac40_ac41_ac45_render(client, renders, monkeypatch):
    monkeypatch.setenv("BE_RENDER_TARGET", "uhd")
    be_id = await _ready(client, proposal=True)
    r = await client.post(f"/v1/birdseyes/{be_id}/cuts", json={"views": [{"preset": "aerial45"}], "lights": ["day"], "primary": True,
                                                              "auto_extra": True, "tone": "warm_wood"})
    assert r.status_code == 202, r.text
    acc = r.json()
    assert len(acc["cut_ids"]) == 3 and acc["route"] == f"/birdseye/{be_id}/render/{acc['job_id']}"
    cuts = (await client.get(f"/v1/birdseyes/{be_id}/cuts")).json()
    queue = [c for c in cuts if c["status"] == "queued" and c["auto_queued"]]
    assert [c["label"] for c in queue] == ["조감 45° · 야간", "도입 전 · 조감 45° (비교용)"]
    assert [c["queue_pos"] for c in queue] == [1, 2] or [c["queue_pos"] for c in queue] == [2, 3]
    await drain()
    cuts = {c["id"]: c for c in (await client.get(f"/v1/birdseyes/{be_id}/cuts")).json()}
    main = cuts[acc["cut_ids"][0]]
    assert main["status"] in ("done", "check"), main["qc"]          # mock 검출은 상자 수가 고정이라 check 가 될 수 있다
    assert main["qc"]
    assert main["is_primary"] and main["resolution"] == "3840×2160"
    assert main["label"] == "조감 45° · 주간" and main["tone"] == "warm_wood"
    assert [s["state"] for s in main["steps"]] == ["done"] * 5
    # 단계 이벤트 순서 · 미리보기
    evs = await _events(acc["job_id"])
    order = []
    for _t, e in evs:
        data = e.get("data") if isinstance(e.get("data"), dict) else e
        st = (data or {}).get("stage")
        if st and (data or {}).get("state") == "run" and st not in order:
            order.append(st)
    assert order == ["structure", "products", "furniture", "render", "qc"]
    raw = json.dumps([e for _t, e in evs], ensure_ascii=False)
    assert '"preview"' in raw and "초안 · 조감 45°" in raw
    # image 렌더 인자
    body = next(c["json"] for c in renders if c["path"] == "/v1/renders" and c["json"]["origin"]["ref"] == main["id"])
    assert body["structure_ref_file_id"] == main["draft_v1_file_id"]
    assert len(body["product_refs"]) == 3 and body["target"] == "uhd" and body["aspect"] == "16:9"
    assert sorted(body["forbid"]) == ["competitor_logo", "gibberish_text", "real_person_face"]
    assert body["confidential"] is True and body["kind"] == "birdseye"
    before = next(c for c in cuts.values() if c["before"])
    bbody = next(c["json"] for c in renders if c["path"] == "/v1/renders" and c["json"]["origin"]["ref"] == before["id"])
    assert bbody["product_refs"] == [] and "expect" not in bbody
    b = (await client.get(f"/v1/birdseyes/{be_id}")).json()
    assert b["status"] == "done" and b["primary_cut_id"] == main["id"]   # 주 컷이 done · check 면 작업은 완료
    # BE0 행(AC 1 일부)
    rows = (await client.get("/v1/birdseyes", params={"filter": "done"})).json()["items"]
    row = next(x for x in rows if x["id"] == be_id)
    assert row["status_title"] == "완료" and row["status_line"].startswith("시점 3") and row["action"]["label"] == "열기"
    assert row["usages"][0]["service"] == "proposal"


async def test_ac43_memo_before_render(client, renders):
    be_id = await _ready(client)
    acc = (await client.post(f"/v1/birdseyes/{be_id}/cuts", json={"views": [{"preset": "aerial45"}], "lights": ["day"], "primary": True})).json()
    await jobs().add_memo(acc["job_id"], "로비에 사람 실루엣 몇 명 넣어줘")
    await drain()
    body = next(c["json"] for c in renders if c["path"] == "/v1/renders")
    assert body["allow_people"] == "silhouette"
    assert "로비에 사람 실루엣 몇 명 넣어줘" in body["prompt"]["details_ko"]


async def test_ac44_capability_paths(client, renders, monkeypatch):
    from winmate_birdseye import llm

    be_id = await _ready(client)

    async def caps_ref_off():
        return {"t2i": {"available": True, "supports": {"reference_images": False, "edit": True, "mask": False}}, "i2t": {"supports": {"bbox": True}}}

    monkeypatch.setattr(llm, "caps", caps_ref_off)
    acc = (await client.post(f"/v1/birdseyes/{be_id}/cuts", json={"views": [{"preset": "aerial45"}], "lights": ["day"], "primary": True})).json()
    await drain()
    c = (await client.get(f"/v1/cuts/{acc['cut_ids'][0]}")).json()
    body = renders[-1]["json"]
    assert body["edit_of"]["file_id"] == c["draft_v1_file_id"] and "structure_ref_file_id" not in body
    assert c["render_path"] == "render:edit"

    async def caps_none():
        return {"t2i": {"available": True, "supports": {"reference_images": False, "edit": False, "mask": False}}, "i2t": {"supports": {"bbox": True}}}

    monkeypatch.setattr(llm, "caps", caps_none)
    acc = (await client.post(f"/v1/birdseyes/{be_id}/cuts", json={"views": [{"preset": "entrance"}], "lights": ["day"]})).json()
    await drain()
    c = (await client.get(f"/v1/cuts/{acc['cut_ids'][0]}")).json()
    assert c["render_path"] == "render:text" and c["status"] == "check"

    async def caps_down():
        return {"t2i": {"available": False, "supports": {"reference_images": False, "edit": False, "mask": False}}, "i2t": {"supports": {"bbox": True}}}

    monkeypatch.setattr(llm, "caps", caps_down)
    acc = (await client.post(f"/v1/birdseyes/{be_id}/cuts", json={"views": [{"preset": "top"}], "lights": ["day"]})).json()
    await drain()
    c = (await client.get(f"/v1/cuts/{acc['cut_ids'][0]}")).json()
    assert c["render_path"] == "render:draft_only" and c["badge"] == "초안 렌더" and c["status"] == "done"


async def test_ac42_cancel_keeps_draft(client, renders, monkeypatch):
    from winmate_birdseye import render

    be_id = await _ready(client)
    acc = (await client.post(f"/v1/birdseyes/{be_id}/cuts", json={"views": [{"preset": "aerial45"}], "lights": ["day"], "primary": True})).json()
    cut_id = acc["cut_ids"][0]
    orig = render._follow

    async def follow_then_cancel(cid, rid):
        await client.post(f"/v1/cuts/{cid}:cancel")       # 진행 중 중지 → 잡 취소 플래그
        return await orig(cid, rid)

    monkeypatch.setattr(render, "_follow", follow_then_cancel)
    await drain()
    c = (await client.get(f"/v1/cuts/{cut_id}")).json()
    assert c["status"] == "draft" and c["draft_v1_file_id"] and c["image_url"]
    assert any(x["path"].endswith(":cancel") for x in renders)
    j = await jobs().get(acc["job_id"])
    assert j is not None and j.status == "canceled"


async def test_ac46_ac48_ac50_edit_and_views(client, renders):
    be_id = await _ready(client)
    acc = (await client.post(f"/v1/birdseyes/{be_id}/cuts", json={"views": [{"preset": "aerial45"}], "lights": ["day"], "primary": True})).json()
    await drain()
    main_id = acc["cut_ids"][0]
    # 렌더 수정 → 같은 컷의 새 버전
    r = await client.post(f"/v1/birdseyes/{be_id}/result:edit", json={"text": "조명을 더 따뜻하게", "cut_id": main_id})
    assert r.status_code == 202, r.text
    assert r.json()["route_hint"] == "render" and r.json()["cut_id"] == main_id
    v0 = (await client.get(f"/v1/cuts/{main_id}")).json()["version_id"]
    await drain()
    c = (await client.get(f"/v1/cuts/{main_id}")).json()
    assert c["version_id"] != v0 and c["status"] in ("done", "check")
    edit_body = renders[-1]["json"]
    assert edit_body["edit_of"]["instruction"] == "조명을 더 따뜻한 색온도로"
    # BE5V — 새로 만들 컷 2(입구 + The Wall 정면, 야간) · 같은 컷은 빼고
    r = await client.post(f"/v1/birdseyes/{be_id}/cuts", json={"views": [{"preset": "entrance"}, {"preset": "product_front"}], "lights": ["night"]})
    assert len(r.json()["cut_ids"]) == 2
    labels = sorted(c["label"] for c in (await client.get(f"/v1/birdseyes/{be_id}/cuts")).json() if c["light"] == "night")
    assert labels == ["The Wall 정면 · 야간", "입구 시점 · 야간"]
    r = await client.post(f"/v1/birdseyes/{be_id}/cuts", json={"views": [{"preset": "entrance"}, {"preset": "product_front"}], "lights": ["night"],
                                                              "before": True})
    assert len(r.json()["cut_ids"]) == 2 and r.json()["skipped"] == 2
    # 시점 설명 → 카메라 높이 제한(층고 − 0.2)
    r = await client.post(f"/v1/birdseyes/{be_id}/cuts", json={"views": [{"custom_text": "2층 난간에서 내려다본 시점"}], "lights": ["day"]})
    custom_id = r.json()["cut_ids"][0]
    await drain()
    cc = (await client.get(f"/v1/cuts/{custom_id}")).json()
    assert cc["view"]["camera"]["pos"][2] == 4.3 and cc["view"]["meta_path"] == "camera:llm"
    # 배치 수정 → 레이아웃 +1 · 기존 컷 stale · 주 컷 재렌더(BE5G)
    r = await client.post(f"/v1/birdseyes/{be_id}/result:edit", json={"text": "벤치를 2열로", "cut_id": main_id})
    out = r.json()
    assert out["route_hint"] == "layout" and out["route"] == f"/birdseye/{be_id}/render/{out['job_id']}"
    lay = (await client.get(f"/v1/birdseyes/{be_id}/layout")).json()["layout"]
    assert lay["version"] == 2
    old = (await client.get(f"/v1/cuts/{main_id}")).json()
    assert old["stale"] is True
    await drain()
    new = (await client.get(f"/v1/cuts/{out['cut_id']}")).json()
    assert new["status"] in ("done", "check") and new["is_primary"] and new["layout_version"] == 2


async def test_ac52_to_ac55_zones(client, renders):
    from winmate_birdseye import draft

    be_id = await _ready(client)
    acc = (await client.post(f"/v1/birdseyes/{be_id}/cuts", json={"views": [{"preset": "aerial45"}], "lights": ["day"], "primary": True})).json()
    await drain()
    cut = (await client.get(f"/v1/cuts/{acc['cut_ids'][0]}")).json()
    r = await client.post(f"/v1/birdseyes/{be_id}/zones:auto", json={"cut_id": cut["id"]})
    assert r.status_code == 202
    await drain()
    zv = (await client.get(f"/v1/birdseyes/{be_id}/zones", params={"cut_id": cut["id"]})).json()
    assert len(zv["points"]) == 4 and len(zv["suggestions"]) == 1
    assert zv["suggestions"][0]["question"] == "기둥 2개를 5번 포인트로 넣을까요?"
    assert zv["suggestions"][0]["title"] == "W 제안 · 기둥 랩핑 길 안내" and zv["suggestions"][0]["add_label"] == "5번으로 추가"
    assert sorted(p["name"] for p in zv["points"]) == sorted(["쇼윈도 · 외부 노출", "라운지 · 체류", "미디어 월 · 관람", "상담 · 시연"])
    assert zv["points"][0]["name"] == "쇼윈도 · 외부 노출"           # 주출입구에서 가장 가까운 군집
    assert zv["preview"]["line"] == "ZP-A 번호 콜아웃 · 포인트 4곳"
    from winmate_birdseye.repo import repo

    craw = await repo().get("cuts", cut["id"])
    for p in zv["points"]:
        u, v = draft.project_norm(craw["camera"], *p["anchor_m"])
        assert abs(u - p["u"]) * 1024 <= 1 and abs(v - p["v"]) * 576 <= 1
        assert len(p["name"]) <= 14 and len(p["text"]) <= 60
    # 동선 순서로 번호
    from winmate_birdseye.layouts import get_layout
    from winmate_birdseye.service import space_model
    from winmate_birdseye.zones import path_order

    await client.patch(f"/v1/zones/{zv['points'][3]['id']}", json={"u": 0.5, "v": 0.5, "cut_id": cut["id"]})
    zv2 = (await client.post(f"/v1/birdseyes/{be_id}/zones:renumber-by-path", params={"cut_id": cut["id"]})).json()
    assert [p["n"] for p in zv2["points"]] == [1, 2, 3, 4]
    lay = await get_layout(be_id)
    items = {it["id"]: it for it in lay["items"]}
    d = path_order(await space_model(be_id), lay, [(p["id"], p["anchor_m"][0], p["anchor_m"][1]) for p in zv2["points"]],
                   {p["id"]: [items[i] for i in p["cluster_item_ids"]] for p in zv2["points"]})
    seq = [d[p["id"]] for p in zv2["points"]]
    assert seq == sorted(seq)
    # 빈 곳 클릭(안내 데스크 근처 바닥)
    u, v = draft.project_norm(craw["camera"], 9.4, 3.2, 0.0)
    r = await client.post(f"/v1/birdseyes/{be_id}/zones", json={"cut_id": cut["id"], "u": u, "v": v})
    assert r.status_code == 201, r.text
    z = r.json()
    assert z["n"] == 5 and z["name"]
    # 사용자가 고친 문구는 그대로(근거가 사용자)
    r = await client.patch(f"/v1/zones/{z['id']}", json={"text": "방문객을 맞이하는 안내 자리", "cut_id": cut["id"]})
    assert r.json()["text"] == "방문객을 맞이하는 안내 자리"
    # 시트 레이아웃 바꾸기 → 미리보기 코드
    await client.patch(f"/v1/birdseyes/{be_id}", json={"zone_layout": "ZP-B"})
    zv3 = (await client.get(f"/v1/birdseyes/{be_id}/zones", params={"cut_id": cut["id"]})).json()
    assert zv3["preview"]["code"] == "ZP-B" and zv3["preview"]["layout_label"] == "존 확대 컷"
    # 제안 수락
    r = await client.post(f"/v1/birdseyes/{be_id}/zones", json={"cut_id": cut["id"], "from_suggestion": zv["suggestions"][0]["id"]})
    assert r.status_code == 201
    # 문구 다듬기
    r = await client.post(f"/v1/birdseyes/{be_id}/zones:rewrite", json={"text": "4곳 모두 고객 관점의 한 문장으로"})
    assert r.status_code == 202
    await drain()
    zv4 = (await client.get(f"/v1/birdseyes/{be_id}/zones")).json()
    assert zv4["points"][0]["name"] == "쇼윈도 · 첫인상"
    # LLM 이 숫자를 내면 [00] · 길이 제한
    from winmate_birdseye import llm, zones as Z

    async def fake(task, prompt, schema, **kw):
        return {"zones": [{"cluster": "1", "name": "쇼윈도 3곳 · 하루 유동 인구 많은 곳", "text": "하루 3000명이 지나는 창면에서 " + "가" * 80, "needs": []}]}

    import pytest as _pt

    mp = _pt.MonkeyPatch()
    mp.setattr(llm, "json_task", fake)
    try:
        await Z.rewrite(be_id, "숫자 넣어서", None)
    finally:
        mp.undo()
    p1 = (await client.get(f"/v1/birdseyes/{be_id}/zones")).json()["points"][0]
    assert "[00]" in p1["name"] and "3" not in p1["name"] and len(p1["name"]) <= 14
    assert "3000" not in p1["text"] and "[00]" in p1["text"] and len(p1["text"]) <= 60
    # handoff(시나리오 · 제안서)
    h = (await client.get(f"/v1/birdseyes/{be_id}/handoff")).json()
    p0 = h["zones"]["points"][0]
    assert p0["id"].startswith("bez_") and p0["short_name"] and p0["path_order"] == 1 and 0 <= p0["u"] <= 1
    assert p0["products"] and p0["products"][0]["short"] == "OH55C" and p0["subtitle"].startswith("OH55C ×3 · ")
    assert h["plan_preview"]["zone_count"] == len(h["zones"]["points"]) and h["plan_preview"]["area_pyeong"] == 120
    ver = (await client.get(f"/v1/birdseyes/{be_id}/version")).json()
    assert set(ver) >= {"version", "layout_version", "updated_at", "zones_hash"}


async def test_ac56_to_ac59_export(client, renders):
    be_id = await _ready(client, proposal=True)
    acc = (await client.post(f"/v1/birdseyes/{be_id}/cuts", json={"views": [{"preset": "aerial45"}], "lights": ["day"], "primary": True,
                                                                 "auto_extra": True})).json()
    await client.post(f"/v1/birdseyes/{be_id}/cuts", json={"views": [{"preset": "entrance"}], "lights": ["day"]})
    await drain()
    main_id = acc["cut_ids"][0]
    await client.post(f"/v1/birdseyes/{be_id}/zones:auto", json={"cut_id": main_id})
    await drain()
    opts = (await client.get(f"/v1/birdseyes/{be_id}/export-options")).json()
    names = [(i["name"], i["selected"]) for i in opts["images"]]
    assert names == [("조감 45° · 주간", True), ("조감 45° · 야간", True), ("도입 전 / 후 비교", True), ("존 포인트 콜아웃", True),
                     ("입구 시점 · 주간", False)]
    assert opts["images"][0]["sub"] == "원본 · 1920×1080"          # 시험 환경 렌더는 fhd(메모리) — uhd 는 test_ac40
    assert opts["filename_default"] == "강남플래그십1층로비_조감도_v1" or opts["filename_default"].endswith("_조감도_v1")
    maps = [(m["from"], m["to"], m["code"]) for m in opts["mapping"]]
    assert maps == [("조감 45° · 주간", "조감도 · 공간 전경", "BV-A"), ("도입 전 / 후", "공간 전경 · 두 시점 비교", "BV-B"),
                    ("존 포인트 4곳", "조감도 · 존별 포인트", "ZP-A"), ("제품 수량표", "공간별 제품 · 수량표", "SM-B")]
    q = (await client.get(f"/v1/birdseyes/{be_id}/quantities")).json()
    assert [(r["name"], r["at"], r["qty"]) for r in q["rows"]] == [("Outdoor Signage OH55C", "쇼윈도 창면", 3),
                                                                   ('The Wall All-in-One IAB 146"', "후면 벽", 1),
                                                                   ("Flip Pro WA75D", "측벽 · 상담", 1)]
    assert q["furniture_row"] == {"label": "가구 4종 (참고)", "at": "라운지 · 관람 · 안내", "qty": 7}
    r = await client.post(f"/v1/birdseyes/{be_id}/exports", json={"format": "png", "size": "fhd", "include_furniture": True,
                                                                 "filename": opts["filename_default"]})
    assert r.status_code == 202, r.text
    xid = r.json()["export_id"]
    await drain()
    x = (await client.get(f"/v1/exports/{xid}")).json()
    assert x["status"] == "done", x
    from winmate_common.platform import file_bytes

    data, _ = await file_bytes(x["file_id"])
    zf = zipfile.ZipFile(io.BytesIO(data))
    names = zf.namelist()
    pngs = [n for n in names if n.endswith(".png")]
    assert len(pngs) == 4 and "수량표.xlsx" in names and "sources.json" in names
    from PIL import Image

    assert Image.open(io.BytesIO(zf.read(pngs[0]))).size == (1920, 1080)
    src = json.loads(zf.read("sources.json"))
    assert src["birdseye_id"] == be_id and src["cuts"]
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(zf.read("수량표.xlsx")))
    header = [c.value for c in next(wb.worksheets[0].iter_rows(max_row=1))]
    assert "수량 근거" in header and not any("가격" in str(h) or "단가" in str(h) for h in header)
    # 제안서 넘기기(B1)
    ph = (await client.get(f"/v1/birdseyes/{be_id}/proposal-handoff", params={"type": "standard", "section": "birdseye"})).json()
    assert [i["key"] for i in ph["items"]][:3] == ["BV-A", "BV-B", "ZP-A"]
    alias = (await client.get(f"/v1/layouts/{be_id}/proposal-handoff", params={"section": "spaceProducts"})).json()
    assert [i["key"] for i in alias["items"]] == ["SM-B"]


async def test_ac1_to_ac5_list_and_clone(client):
    # 완료 · 진행 중(4/5) · 확인 필요(역광 사진)
    from be_kit import png, upload

    from winmate_birdseye.repo import repo

    done_id = await _ready(client)
    await repo().put("cuts", "bec_done1", {"birdseye_id": done_id, "layout_version": 1, "view": {"preset": "aerial45", "label": "조감 45°"},
                                           "light": "day", "before": False, "tone": "warm_wood", "status": "done", "stale": False, "is_primary": True,
                                           "image_file_id": None, "job_id": None, "queue_order": 1})
    await repo().put("cuts", "bec_night", {"birdseye_id": done_id, "layout_version": 1, "view": {"preset": "aerial45", "label": "조감 45°"},
                                           "light": "night", "before": False, "tone": "warm_wood", "status": "running", "stale": False,
                                           "job_id": "job_night", "queue_order": 2, "progress": 40})
    await repo().patch("birdseyes", done_id, {"primary_cut_id": "bec_done1", "step": 5})
    prog = await create(client, title="진행 중 작업")
    await repo().patch("birdseyes", prog["id"], {"step": 4})
    chk = await create(client, title="확인 필요 작업", description="관제실")
    fid = await upload("w.jpg", png(pattern="backlit"), "image/png")
    await client.post(f"/v1/birdseyes/{chk['id']}/photos", json={"file_id": fid})
    await drain()
    lst = (await client.get("/v1/birdseyes")).json()
    rows = {r["id"]: r for r in lst["items"]}
    assert lst["counts"] == {"all": 3, "in_progress": 1, "needs_check": 1, "done": 1}
    d, p, c = rows[done_id], rows[prog["id"]], rows[chk["id"]]
    assert (d["status_title"], d["action"]["label"]) == ("완료", "열기")
    assert d["running"]["label"] == "야간 시점 추가 생성 중" and d["running"]["route"].endswith("/render/job_night")
    assert (p["status_title"], p["status_line"], p["action"]["label"]) == ("4/5", "배치 · 인테리어 컨펌", "이어서")
    assert (c["status_title"], c["status_line"], c["action"]["label"]) == ("확인 필요", "사진 1장 다시 찍기 · 1/5 공간 입력", "확인")
    assert c["input_chips"] == ["설명", "사진 1장"]
    # 쓰인 곳 · 제안서에 쓰인 것만
    await client.post(f"/v1/birdseyes/{done_id}/usages", json={"service": "scenario", "ref": "sc_1", "label": "로비 시나리오", "version": 1})
    await client.post(f"/v1/birdseyes/{prog['id']}/usages", json={"service": "proposal", "ref": "prp_9", "label": "A 커피 제안", "version": 1})
    only = (await client.get("/v1/birdseyes", params={"in_proposal": True})).json()["items"]
    assert [r["id"] for r in only] == [prog["id"]]
    # 복제(AC 4)
    r = await client.post(f"/v1/birdseyes/{done_id}:clone", json={})
    assert r.status_code == 201
    nid = r.json()["id"]
    assert r.json()["route"] == f"/birdseye/{nid}/layout"
    nb = (await client.get(f"/v1/birdseyes/{nid}")).json()
    assert nb["cloned_from"] == done_id and nb["title"].endswith("복제") and nb["tone"] == "warm_wood"
    assert (await client.get(f"/v1/birdseyes/{nid}/cuts")).json() == []
    assert (await client.get(f"/v1/birdseyes/{nid}/zones")).json()["points"] == []
    nl = (await client.get(f"/v1/birdseyes/{nid}/layout")).json()["layout"]
    ol = (await client.get(f"/v1/birdseyes/{done_id}/layout")).json()["layout"]
    assert [(i["x"], i["y"]) for i in nl["items"]] == [(i["x"], i["y"]) for i in ol["items"]]
    # 팀 공유(AC 5)
    await client.patch(f"/v1/birdseyes/{done_id}", json={"shared_scope": "team", "shared_label": "외식 영업팀"})
    team = (await client.get("/v1/birdseyes", params={"scope": "team"})).json()["items"]
    assert team[0]["team_meta"].startswith("외식 영업팀 공유 · 시점 1")
    # 지우기(소프트)
    assert (await client.delete(f"/v1/birdseyes/{nid}")).status_code == 204
    assert (await client.get(f"/v1/birdseyes/{nid}")).status_code == 404
    # workspace 색인(AC 61)
    from winmate_common.client import ServiceClient

    item = await ServiceClient("workspace").get(f"/v1/items/{done_id}")
    assert item["route"].startswith(f"/birdseye/{done_id}/")
