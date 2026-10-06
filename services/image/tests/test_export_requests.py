"""IMG4 · 내보내기 · 제안서 사용 · 다른 기능의 요청 · 렌더 API · workspace 색인(AC 49–56)."""
from __future__ import annotations

import io
import zipfile

import numpy as np
from img_helpers import done_run, file_image, png

from winmate_common import testing
from winmate_common.client import ServiceClient
from winmate_common.platform import file_bytes
from winmate_image import imaging


async def edited_v2(env, client) -> tuple[dict, dict]:
    w, run = await done_run(env, client, count=2)
    await client.patch(f"/v1/works/{w['id']}", json={"customer_name": "A 커피 프랜차이즈"})
    iid = run["shots"][0]["image_id"]
    r = await client.post(f"/v1/images/{iid}/regions", json={"shape": "rect", "rect": [0.1, 0.5, 0.4, 0.8], "instruction": "화분 넣기"})
    await client.post(f"/v1/images/{iid}/edits", json={"region_ids": [r.json()["region"]["id"]]})
    await env.drain()
    return w, (await client.get(f"/v1/images/{iid}")).json()


async def drain_export() -> int:
    return await testing.drain_jobs("export", testing.load_service_worker("export"))


async def test_export_title_filename_ac49(env, client):
    w, img = await edited_v2(env, client)
    assert img["customer_short"] == "A 커피"
    assert img["current"]["title"] == "시안 1 · 부분 수정본 v2"
    r = await client.post(f"/v1/images/{img['id']}/filename", json={"lang": "ko", "ext": "png"})
    assert r.json()["filename"] == "A커피_메뉴보드_시안1_v2.png"
    r = await client.post(f"/v1/images/{img['id']}/filename", json={"lang": "en", "ext": "png"})
    assert r.json()["filename"] == "ACoffee_MenuBoard_Draft1_v2.png"


async def test_png_ai_label_and_xmp_ac50(env, client):
    w, run = await done_run(env, client, count=2)
    iid = run["shots"][0]["image_id"]
    r = await client.post(f"/v1/images/{iid}/exports", json={"format": "png", "resolution": "uhd", "ai_label": True})
    assert r.status_code == 200, r.text
    on = r.json()
    assert on["status"] == "done" and on["download_url"].endswith("?download=1") and on["filename"].endswith(".png")
    r = await client.post(f"/v1/images/{iid}/exports", json={"format": "png", "resolution": "uhd", "ai_label": False})
    off = r.json()
    img = (await client.get(f"/v1/images/{iid}")).json()
    uhd = next(x for x in img["current"]["renditions"] if x["kind"] == "uhd")
    rend, a, b = await file_image(uhd["file_id"]), await file_image(on["file_id"]), await file_image(off["file_id"])
    assert a.size == (3840, 2160)
    box = imaging.ai_label_box(a.size)
    ra, rr, rb = (np.asarray(x.crop(box), np.int16) for x in (a, rend, b))
    assert np.abs(ra - rr).sum() > 0 and np.array_equal(rb, rr)
    for fid in (on["file_id"], off["file_id"]):
        data, _ = await file_bytes(fid)
        text = imaging.read_png_text(data)
        assert imaging.TRAINED_MEDIA in text["XML:com.adobe.xmp"] and text["winmate:generated"] == "true"
    work = (await client.get(f"/v1/works/{w['id']}")).json()
    assert work["badge"]["label"] == "PNG로 내보냄" and work["route"] == f"/image/w/{w['id']}/export/{iid}"


async def test_with_original_zip_ac51(env, client):
    w, img = await edited_v2(env, client)
    r = await client.post(f"/v1/images/{img['id']}/exports", json={"format": "png", "include_original": True, "resolution": "fhd"})
    assert r.status_code == 202, r.text
    out = r.json()
    assert out["job_id"] and out["status"] == "queued"
    await drain_export()
    got = (await client.get(f"/v1/exports/{out['export_id']}")).json()
    assert got["status"] == "done" and got["file_id"]
    data, _ = await file_bytes(got["file_id"])
    names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    assert sum(1 for n in names if n.endswith(".png")) == 2 and "sources.json" in names


async def test_pptx_export_ac52(env, client):
    w, run = await done_run(env, client, count=2)
    iid = run["shots"][0]["image_id"]
    r = await client.post(f"/v1/images/{iid}/exports", json={"format": "pptx", "resolution": "fhd"})
    assert r.status_code == 202, r.text
    out = r.json()
    await drain_export()
    got = (await client.get(f"/v1/exports/{out['export_id']}")).json()
    assert got["status"] == "done" and got["filename"].endswith(".pptx") and got["download_url"]


async def test_usage_badge_ac53(env, client):
    w, run = await done_run(env, client, count=2)
    iid = run["shots"][0]["image_id"]
    img = (await client.get(f"/v1/images/{iid}")).json()
    await client.post(f"/v1/images/{iid}:save")
    r = await client.post(f"/v1/images/{iid}/usages", json={"version_id": img["current_version_id"], "service": "proposal",
                                                              "ref": "prp_1", "label": "A 커피 제안서 › 카운터 · 메뉴보드"})
    assert r.status_code == 201, r.text
    work = (await client.get(f"/v1/works/{w['id']}")).json()
    assert work["badge"]["label"] == "제안서 사용 중"
    tile = (await client.get("/v1/images")).json()["items"][0]
    assert tile["used_in_count"] == 1
    info = (await client.get(f"/v1/images/{iid}/info")).json()
    assert next(r for r in info["rows"] if r["k"] == "사용 이력")["v"] == "Winmate 제안서 1건"
    assert (await client.delete(f"/v1/images/{iid}/usages/proposal/prp_1")).status_code == 204
    assert (await client.get(f"/v1/works/{w['id']}")).json()["badge"]["label"] == "완료"


async def test_scenario_request_ac54(env, client):
    body = {"from_service": "scenario", "from_ref": "scn_1", "from_label": "공간 시나리오 · A 커피 매장 하루",
            "title": "장면 2 · 점심 피크 주문",
            "prefill": {"kind": "scenario", "description": "점심 피크 시간, 카운터 앞에서 손님이 주문하는 장면",
                        "products": ["QM55C"], "aspect": "16:9", "space_label": "카운터"}}
    r = await client.post("/v1/requests", json=body)
    assert r.status_code == 201, r.text
    req = r.json()
    lst = (await client.get("/v1/requests", params={"status": "open,in_progress"})).json()["items"]
    assert lst[0]["id"] == req["id"] and lst[0]["from_label"] == "공간 시나리오 · A 커피 매장 하루"
    st = (await client.post(f"/v1/requests/{req['id']}:start")).json()
    assert st["route"] == f"/image/new?work={st['work_id']}" and st["conditions_route"] == f"/image/w/{st['work_id']}/conditions"
    work = (await client.get(f"/v1/works/{st['work_id']}")).json()
    assert work["kind"] == "scenario" and work["description"].startswith("점심 피크") and work["origin"]["request_id"] == req["id"]
    assert [p["short"] for p in work["conditions"]["products"]] == ["QM55C"] and work["title"] == "장면 2 · 점심 피크 주문"
    by_ref = (await client.get("/v1/requests", params={"from_service": "scenario", "from_ref": "scn_1"})).json()["items"]
    assert by_ref[0]["status"] == "in_progress"
    await client.post(f"/v1/works/{work['id']}/runs", json={"kind": "initial", "count": 2})
    await env.drain()
    run = (await client.get(f"/v1/works/{work['id']}/runs")).json()["items"][0]
    vid = (await client.get(f"/v1/images/{run['shots'][0]['image_id']}")).json()["current_version_id"]
    r = await client.post(f"/v1/requests/{req['id']}:fulfill", json={"version_id": vid})
    assert r.json()["status"] == "fulfilled" and r.json()["result_version_id"] == vid
    v = (await client.get(f"/v1/versions/{vid}")).json()
    assert v["id"] == vid and v["renditions"] and v["generation"]["is_generated"]


async def test_birdseye_render_ac55(env, client, monkeypatch):
    fid = await env.upload(png(640, 360), "draft.png", confidential=False)
    body = {"origin": {"service": "birdseye", "ref": "be_1"}, "kind": "birdseye", "prompt": {"subject_ko": "카페 매장 조감도",
                                                                                              "details_ko": ["우드톤", "주간"]},
            "aspect": "16:9", "target": "uhd", "structure_ref_file_id": fid,
            "product_refs": [{"model_code": "LH55QMCEBGCXKR", "qty": 3}],
            "forbid": ["competitor_logo", "real_person_face", "gibberish_text"], "allow_people": "none"}
    r = await client.post("/v1/renders", json=body)
    assert r.status_code == 202, r.text
    rid = r.json()["render_id"]
    await env.drain()
    out = (await client.get(f"/v1/renders/{rid}")).json()
    assert out["status"] == "succeeded", out
    uhd = next(x for x in out["renditions"] if x["kind"] == "uhd")
    assert (uhd["w"], uhd["h"]) == (3840, 2160) and out["generation"]["origin"]["service"] == "birdseye"
    g = env.tap.by("/v1/t2i/generate", "img.render")[0]["body"]
    assert g["reference_images"][0]["file_id"] == fid and g["reference_images"][0]["role"] == "composition"
    await client.post(f"/v1/images/{out['image_id']}:save")
    assert out["image_id"] not in {i["id"] for i in (await client.get("/v1/images")).json()["items"]}
    assert (await client.get("/v1/works")).json()["totals"]["works"] == 0
    # 참조 미지원 + 편집 지원 → t2i.edit(edit_of=structure_ref)
    monkeypatch.setenv("T2I_SUPPORTS_REFERENCE_IMAGES", "false")
    from winmate_image import caps

    caps.reset()
    r = await client.post("/v1/renders", json=body)
    await env.drain()
    e = env.tap.by("/v1/t2i/edit", "img.render")[0]["body"]
    assert e["image"]["file_id"] == fid
    assert (await client.get(f"/v1/renders/{r.json()['render_id']}")).json()["status"] == "succeeded"


async def test_workspace_index_ac56(env, client):
    ws = ServiceClient("workspace")
    r = await client.post("/v1/works", json={"kind": "space", "description": "카페 카운터 위에 3연 메뉴보드"})
    wid = r.json()["id"]
    item = await ws.get(f"/v1/items/{wid}")
    assert item["feature"] == "IMG" and item["route"] == f"/image/new?work={wid}" and item["status"] == "draft"
    await client.post(f"/v1/works/{wid}:prefill")
    acc = (await client.post(f"/v1/works/{wid}/runs", json={"kind": "initial", "count": 2})).json()
    item = await ws.get(f"/v1/items/{wid}")
    assert item["route"] == f"/image/w/{wid}/run/{acc['run_id']}" and item["status"] in ("queued", "running")
    await env.drain()
    item = await ws.get(f"/v1/items/{wid}")
    assert item["route"] == f"/image/w/{wid}/result" and item["status"] == "done" and item["summary"] == "이미지 생성 · 공간 · 2장" or \
        item["summary"].endswith("공간 · 2장")
    run = (await client.get(f"/v1/runs/{acc['run_id']}")).json()
    iid = run["shots"][0]["image_id"]
    await client.post(f"/v1/images/{iid}/exports", json={"format": "jpg", "resolution": "fhd"})
    item = await ws.get(f"/v1/items/{wid}")
    assert item["route"] == f"/image/w/{wid}/export/{iid}"


async def test_english_filename_without_customer(env, client):
    """고객사 · 주제가 없으면 LLM 이 채워도 파일명에 넣지 않는다(지어내지 않기)."""
    w, run = await done_run(env, client, count=2)
    iid = run["shots"][0]["image_id"]
    await client.patch(f"/v1/works/{w['id']}", json={"customer_name": None})
    r = await client.post(f"/v1/images/{iid}/filename", json={"lang": "en", "ext": "jpg"})
    assert r.json()["filename"] == "MenuBoard_Draft1_v1.jpg"


async def test_shell_my_images_search(env, client):
    """셸 「내 생성 이미지」(owner=me) — 저장한 시안만, 검색어 낱말은 제목 · 고객사 · 작업 설명 어디서든."""
    w, run = await done_run(env, client, count=2)
    iid = run["shots"][0]["image_id"]
    assert (await client.get("/v1/images", params={"owner": "me"})).json()["items"] == []
    await client.post(f"/v1/images/{iid}:save")
    items = (await client.get("/v1/images", params={"owner": "me", "q": "카페 메뉴보드"})).json()["items"]
    assert [t["id"] for t in items] == [iid] and items[0]["thumb_url"] and items[0]["width"] == 1920
    assert (await client.get("/v1/images", params={"owner": "me", "q": "병원"})).json()["items"] == []
