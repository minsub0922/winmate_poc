"""기본 흐름(IMG1 → IMG2 → IMG3G → IMG3) — 실제 플랫폼 앱(in-process) · mock 모델."""
from __future__ import annotations

from winmate_common.jobs import jobs

DESC = "카페 카운터 위에 3연 메뉴보드가 걸린 장면, 낮 시간, 손님 2~3명"


async def make_work(client, desc: str = DESC, kind: str = "space") -> dict:
    r = await client.post("/v1/works", json={"kind": kind, "description": desc})
    assert r.status_code == 201, r.text
    return r.json()


async def test_basic_flow(env, client):
    w = await make_work(client)
    assert w["title"] == "새 작업" and w["status"] == "draft" and w["route"] == f"/image/new?work={w['id']}"
    r = await client.post(f"/v1/works/{w['id']}:prefill")
    assert r.status_code == 200, r.text
    pre = r.json()
    assert pre["products"][0]["short"] == "QM55C" and pre["products"][0]["qty"] == 3
    assert pre["work"]["conditions"]["products"][0]["name"] == "Smart Signage QM55C"
    assert pre["work"]["conditions"]["style"] == "photo" and pre["work"]["conditions"]["aspect"] == "16:9"
    assert pre["work"]["conditions"]["count"] == 4
    assert pre["search_query"] == "카페 메뉴보드"
    assert pre["work"]["route"].endswith("/conditions")
    r = await client.post(f"/v1/works/{w['id']}/runs", json={"kind": "initial"})
    assert r.status_code == 202, r.text
    acc = r.json()
    assert acc["status"] == "queued" and acc["precheck"]["issues"] == []
    run = (await client.get(f"/v1/runs/{acc['run_id']}")).json()
    assert run["total"] == 4 and [s["label"] for s in run["shots"]] == ["시안 1", "시안 2", "시안 3", "시안 4"]
    work = (await client.get(f"/v1/works/{w['id']}")).json()
    assert work["badge"]["label"] == "생성 중 0 / 4"
    n = await env.drain()
    assert n >= 1
    run = (await client.get(f"/v1/runs/{acc['run_id']}")).json()
    assert run["status"] == "succeeded", run
    assert run["done"] == 4
    assert all(s["state"] == "done" and s["width"] == 1920 and s["height"] == 1080 for s in run["shots"])
    job = await jobs().get(acc["job_id"])
    assert job.status == "succeeded"
    work = (await client.get(f"/v1/works/{w['id']}")).json()
    assert work["status"] == "done" and work["route"] == f"/image/w/{w['id']}/result"
    img = (await client.get(f"/v1/images/{run['shots'][0]['image_id']}")).json()
    cur = img["current"]
    assert cur["n"] == 1 and cur["label"] == "원본" and cur["op"] == "generate"
    kinds = {r["kind"]: (r["w"], r["h"]) for r in cur["renditions"]}
    assert kinds["native"] == (1024, 576) and kinds["fhd"] == (1920, 1080)
    gen = cur["generation"]
    assert gen["is_generated"] and gen["rights"] == "generated" and gen["call"] == "t2i.generate"
    assert gen["products"][0]["name"] == "Smart Signage QM55C" and gen["upscale"]["to"] == [1920, 1080]
    assert cur["qc"]["status"] == "ok"
    # 갤러리(내 이미지)는 저장한 시안만 — 저장하면 1 늘어난다(AC31)
    lst = (await client.get("/v1/images", params={"owner": "me"})).json()
    assert lst["total"] == 0
    r = await client.post(f"/v1/images/{run['shots'][0]['image_id']}:save")
    assert r.status_code == 200 and r.json()["saved"] is True
    lst = (await client.get("/v1/images", params={"owner": "me"})).json()
    assert lst["total"] == 1 and lst["items"][0]["meta"].endswith("16:9") and lst["items"][0]["title"] == "메뉴보드 시안 1"
    works = (await client.get("/v1/works")).json()
    assert works["totals"]["images"] == 1 and works["items"][0]["status"]["label"] == "완료"
