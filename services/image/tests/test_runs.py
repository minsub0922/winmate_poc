"""IMG3G · 대기열 · 취소 · 알림 · 정책(IMG3X) · 품질 확인(AC 13–28)."""
from __future__ import annotations

import asyncio
import re

import pytest
from img_helpers import (DESC, USER, api_error, done_run, i2t_json, llm_json, new_work, png, prefilled, start_run,
                         wait_for)

from winmate_common.jobs import Worker, jobs

COMPETITOR_DESC = "경쟁사 A 메뉴보드 옆에 QM55C, 배우 ○○○가 주문하는 장면"
QC_OK = {"product_count": 3, "products": [{"box": [0.19, 0.12, 0.39, 0.32], "kind": "display"},
                                          {"box": [0.40, 0.12, 0.60, 0.32], "kind": "display"},
                                          {"box": [0.61, 0.12, 0.81, 0.32], "kind": "display"}],
         "logo_visible": False, "brand_text": False, "identifiable_faces": 0, "gibberish_text": False}
QC_LOGO = {**QC_OK, "logo_visible": True}


async def get_run(client, run_id: str) -> dict:
    return (await client.get(f"/v1/runs/{run_id}")).json()


# ── 진행 · 동시성 · 취소 ────────────────────────────────

async def test_shot_concurrency_and_wait_label_ac13(env, client):
    env.tap.delays["t2i"] = 0.4
    w = await prefilled(client)
    acc = await start_run(client, w["id"], count=4)
    task = asyncio.create_task(env.drain())

    async def mid():
        run = await get_run(client, acc["run_id"])
        st = [s["state"] for s in run["shots"]]
        return run if ("rendering" in st and "waiting" in st) else None

    run = await wait_for(mid)
    waiting = [s for s in run["shots"] if s["state"] == "waiting"]
    assert re.fullmatch(r"시안 [12](이|가) 끝나면 시작해요", waiting[0]["wait_for"] or ""), waiting[0]
    assert run["head"].startswith("생성 중 · ") and [s["key"] for s in run["stages"]] == ["product_fit", "compose", "render", "qc"]
    assert run["stages"][0]["state"] == "done" and run["stages"][2]["label"].startswith("렌더링 ")
    # IMG0(AC18) — 떠나도 목록 · 갤러리에 진행률
    works = (await client.get("/v1/works")).json()
    assert works["items"][0]["status"]["label"].startswith("생성 중 ") and works["items"][0]["status"]["label"].endswith(" / 4")
    gal = (await client.get("/v1/images")).json()
    tile = gal["items"][0]
    assert tile["status"] in ("waiting", "composing", "rendering", "qc") and tile["progress_total"] == 4
    assert tile["run_route"] == f"/image/w/{w['id']}/run/{acc['run_id']}" and tile["meta"].endswith("생성 중")
    assert len([t for t in gal["items"] if t["run_id"] == acc["run_id"]]) == 1
    await task
    assert env.tap.max_active <= 2
    assert (await get_run(client, acc["run_id"]))["status"] == "succeeded"


async def test_cancel_one_shot_ac14(env, client):
    env.tap.delays["t2i"] = 0.5
    w = await prefilled(client)
    acc = await start_run(client, w["id"], count=4)
    task = asyncio.create_task(env.drain())

    async def third_started():
        run = await get_run(client, acc["run_id"])
        s3 = run["shots"][2]
        return s3 if s3["state"] in ("composing", "rendering") else None

    s3 = await wait_for(third_started)
    r = await client.post(f"/v1/runs/{acc['run_id']}/shots/{s3['image_id']}:cancel")
    assert r.status_code == 200 and r.json()["status"] == "canceled"
    await task
    run = await get_run(client, acc["run_id"])
    assert run["status"] == "succeeded" and run["done"] == 3 and run["total"] == 4
    assert run["shots"][2]["state"] == "canceled" and run["shots"][2]["stage_label"] == "취소됨"
    img = (await client.get(f"/v1/images/{s3['image_id']}")).json()
    assert img["current_version_id"] is None and img["versions"] == []


async def test_cancel_all_keeps_done_ac15(env, client):
    env.tap.delays["t2i"] = 0.5
    w = await prefilled(client)
    acc = await start_run(client, w["id"], count=4)
    task = asyncio.create_task(env.drain())

    async def one_done():
        run = await get_run(client, acc["run_id"])
        return run if run["done"] >= 1 else None

    await wait_for(one_done)
    r = await client.post(f"/v1/runs/{acc['run_id']}:cancel")
    assert r.status_code == 202 and r.json()["status"] == "canceled"
    await task
    job = await jobs().get(acc["job_id"])
    assert job.status == "canceled"
    run = await get_run(client, acc["run_id"])
    assert run["status"] == "canceled"
    done = [s for s in run["shots"] if s["state"] == "done"]
    assert done and all(s["state"] in ("done", "canceled") for s in run["shots"])
    work = (await client.get(f"/v1/works/{w['id']}")).json()
    assert work["conditions"]["products"][0]["qty"] == 3 and work["conditions"]["count"] == 4
    assert work["route"] == f"/image/w/{w['id']}/conditions"
    gal = (await client.get("/v1/images", params={"owner": "me"})).json()
    assert {s["image_id"] for s in done} <= {i["id"] for i in gal["items"]}


async def test_queue_order_ac16(env, client):
    env.tap.delays["t2i"] = 0.3
    accs = []
    for i in range(3):
        w = await prefilled(client)
        accs.append(await start_run(client, w["id"], count=2))
    q = (await client.get("/v1/queue")).json()
    assert [(x["run_id"], x["state_label"]) for x in q["items"]] == [(accs[0]["run_id"], "다음 차례"), (accs[1]["run_id"], "2번째"),
                                                                       (accs[2]["run_id"], "3번째")]
    from winmate_image.worker import HANDLERS

    worker = Worker("image", HANDLERS, concurrency=3)
    await worker._ensure_group()
    res = await worker.jobs.r.xreadgroup(worker.group, worker.consumer, {worker.stream: ">"}, count=3)
    tasks = [asyncio.create_task(worker.process(eid, f)) for _s, entries in res for eid, f in entries]
    assert len(tasks) == 3

    async def r1_running():
        q = (await client.get("/v1/queue")).json()
        return q if q["running"] and q["running"]["id"] == accs[0]["run_id"] else None

    q = await wait_for(r1_running)
    assert [(x["run_id"], x["state_label"]) for x in q["items"]] == [(accs[1]["run_id"], "다음 차례"), (accs[2]["run_id"], "2번째")]
    r2 = await get_run(client, accs[1]["run_id"])
    assert r2["status"] == "queued" and r2["head"].startswith("대기 중 · 앞에 ")
    await asyncio.gather(*tasks)
    for a in accs:
        assert (await get_run(client, a["run_id"]))["status"] == "succeeded"


@pytest.mark.parametrize("notify", [True, False])
async def test_notify_once_ac17(env, client, notify):
    w = await prefilled(client)
    acc = await start_run(client, w["id"], count=2, notify=notify)
    await env.drain()
    rows = [d for _id, d in await jobs().notifications(USER) if d.get("type") == "image_run_done"]
    if notify:
        assert len(rows) == 1 and rows[0]["route"] == f"/image/w/{w['id']}/result"
        assert rows[0]["title"] == "카페 매장 메뉴보드 시안 · 2장 생성 완료"
    else:
        assert rows == []
    r = await client.patch(f"/v1/runs/{acc['run_id']}", json={"notify": not notify})
    assert r.status_code == 200 and r.json()["notify"] is (not notify)


async def test_quota_exceeded_ac19(env, client, monkeypatch):
    monkeypatch.setenv("IMAGE_SHOT_CONCURRENCY", "1")
    env.tap.sequence("img.generate", [None, api_error(429, "DAILY_LIMIT_EXCEEDED", "하루 한도")])
    w = await prefilled(client)
    acc = await start_run(client, w["id"], count=4)
    await env.drain()
    run = await get_run(client, acc["run_id"])
    assert run["status"] == "failed" and run["error"]["code"] == "QUOTA_EXCEEDED"
    assert run["error"]["message"] == "오늘 쓸 수 있는 이미지 생성 횟수를 다 썼어요"
    assert len(env.tap.by("/v1/t2i/generate")) == 2      # 재시도 없음 · 남은 시안은 부르지 않음
    assert run["shots"][0]["state"] == "done" and run["done"] == 1
    job = await jobs().get(acc["job_id"])
    assert job.status == "failed"
    work = (await client.get(f"/v1/works/{w['id']}")).json()
    assert work["badge"]["label"] == "생성 실패 · 다시 시도"


async def test_transient_retry(env, client, monkeypatch):
    env.tap.sequence("img.generate", [api_error(503, "UPSTREAM_UNAVAILABLE"), None])
    w = await prefilled(client)
    acc = await start_run(client, w["id"], count=2)
    await env.drain()
    assert (await get_run(client, acc["run_id"]))["status"] == "succeeded"
    assert len(env.tap.by("/v1/t2i/generate")) == 3


# ── 정책 · IMG3X ────────────────────────────────────────

async def _policy_run(env, client, monkeypatch, count: int = 4) -> tuple[dict, dict]:
    from winmate_image import analysis

    async def cands(d):
        return [{"family_id": "fam_G000182628", "model_code": "LH55QMCEBGCXKR", "name": "Smart Signage QM55C", "short": "QM55C",
                 "qty": 1, "score": 0.5},
                {"family_id": "fam_G000182632", "model_code": "LH55QBCEBGCXKR", "name": "Smart Signage QB55C", "short": "QB55C",
                 "qty": 1, "score": 0.42},
                {"family_id": "fam_G000182638", "model_code": "LH55QHCEBGCXKR", "name": "Smart Signage QH55C", "short": "QH55C",
                 "qty": 1, "score": 0.4}]

    monkeypatch.setattr(analysis, "display_candidates", cands)
    env.tap.override("img.ref_analyze", lambda b, n: i2t_json({"faces": [], "logos": [], "style": "photo", "caption": "카운터 사진",
                                                                "displays": [{"box": [0.3, 0.2, 0.5, 0.4], "visual_category": "사이니지",
                                                                              "size_hint": "55인치", "confidence": 0.5}]}))
    w = await prefilled(client, COMPETITOR_DESC)
    fid = await env.upload(png(), "ref.png")
    assert (await client.post(f"/v1/works/{w['id']}/references", json={"source_kind": "upload", "file_id": fid})).status_code == 201
    await env.drain()
    acc = await start_run(client, w["id"], count=count)
    assert [i["type"] for i in acc["precheck"]["issues"]] == ["product_unrecognized", "competitor_brand", "real_person"]
    await env.drain()
    return w, await get_run(client, acc["run_id"])


async def test_policy_hold_ac20(env, client, monkeypatch):
    w, run = await _policy_run(env, client, monkeypatch)
    assert run["status"] == "awaiting_input" and run["done"] == 2 and run["held"] == 2
    assert [s["state"] for s in run["shots"]] == ["done", "done", "held", "held"]
    iss = run["issues"]
    assert [(i["type"], i["state_label"]) for i in iss] == [("product_unrecognized", "대안 선택됨"), ("competitor_brand", "대안 선택됨"),
                                                            ("real_person", "선택 필요")]
    assert iss[0]["options"][0]["label"] == "QM55C · 가장 비슷" and iss[0]["selected"] == "cand_1"
    assert [o["label"] for o in iss[0]["options"]] == ["QM55C · 가장 비슷", "QB55C", "QH55C", "제품 탐색에서 고르기", "외형만 참고"]
    assert iss[1]["title"] == "경쟁사 A 로고 · 제품은 이미지에 넣지 않아요" and iss[1]["selected"] == "generic_screen"
    assert iss[2]["title"] == "실존 인물(배우 ○○○)은 그리지 않아요" and iss[2]["selected"] is None
    assert sum(1 for i in iss if i["selected"]) == 2
    assert run["applied_note"] == "경쟁사 · 인물 요소 없이 만들었어요"
    work = (await client.get(f"/v1/works/{w['id']}")).json()
    assert work["status"] == "awaiting_input" and work["badge"]["label"] == "2장 생성 불가 · 대안 보기"
    assert work["route"] == f"/image/w/{w['id']}/run/{run['id']}"
    q = (await client.get("/v1/queue")).json()
    assert q["items"] == []


async def test_policy_continue_defaults_ac21(env, client, monkeypatch):
    w, run = await _policy_run(env, client, monkeypatch)
    before = len(env.tap.by("/v1/t2i/generate"))
    r = await client.post(f"/v1/runs/{run['id']}/answers", json={"answers": []})
    assert r.status_code == 202, r.text
    await env.drain()
    run = await get_run(client, run["id"])
    assert run["status"] == "succeeded" and run["done"] == 4
    assert [s["label"] for s in run["shots"][2:]] == ["시안 3", "시안 4"]
    later = env.tap.by("/v1/t2i/generate")[before:]
    assert len(later) == 2
    for c in env.tap.by("/v1/t2i/generate"):
        p = c["body"]["prompt"]
        assert "경쟁사 A" not in p and "○○○" not in p and "No people in the scene." in p
    issues = run["issues"]
    assert issues[2]["selected"] == "no_people"
    img = (await client.get(f"/v1/images/{run['shots'][3]['image_id']}")).json()
    assert img["current"]["generation"]["policy"]["applied_options"]["real_person"] == "인물 없이 · 기본값"


async def test_policy_skip_held_ac22(env, client, monkeypatch):
    w, run = await _policy_run(env, client, monkeypatch)
    r = await client.post(f"/v1/runs/{run['id']}/answers", json={"skip_held": True})
    assert r.status_code == 202
    await env.drain()
    run = await get_run(client, run["id"])
    assert run["status"] == "succeeded" and [s["state"] for s in run["shots"]] == ["done", "done", "canceled", "canceled"]


async def test_hold_rule_two_ac23(env, client):
    w = await prefilled(client, "배우 ○○○가 카페 카운터에서 주문하는 장면")
    acc = await start_run(client, w["id"], count=2)
    assert [i["type"] for i in acc["precheck"]["issues"]] == ["real_person"]
    await env.drain()
    run = await get_run(client, acc["run_id"])
    assert run["status"] == "awaiting_input" and run["done"] == 1 and run["held"] == 1


async def test_custom_alternative_ac24(env, client, monkeypatch):
    w, run = await _policy_run(env, client, monkeypatch)
    r = await client.post(f"/v1/runs/{run['id']}/alternatives", json={"text": "경쟁사 화면은 회색 박스로"})
    body = r.json()
    assert r.status_code == 200 and body["accepted"] is True
    comp = next(i for i in body["run"]["issues"] if i["type"] == "competitor_brand")
    assert comp["selected"] == "custom" and comp["custom_text"] == "경쟁사 화면은 회색 박스로"
    env.tap.override("img.alt_custom", lambda b, n: llm_json({"issue_type": "real_person", "option_text": "배우 ○○○ 얼굴로",
                                                              "safe": False}))
    r = await client.post(f"/v1/runs/{run['id']}/alternatives", json={"text": "그냥 그 배우 얼굴로"})
    assert r.json()["accepted"] is False
    person = next(i for i in r.json()["run"]["issues"] if i["type"] == "real_person")
    assert person["selected"] is None


async def test_auto_resolved_band_ac25(env, client):
    w = await prefilled(client, "경쟁사 A 메뉴보드 옆에 QM55C 3대를 둔 카페 카운터")
    acc = await start_run(client, w["id"], count=4)
    await env.drain()
    run = await get_run(client, acc["run_id"])
    assert run["status"] == "succeeded" and run["done"] == 4 and run["held"] == 0
    assert run["change_note"] == "요청 중 1가지를 바꿔서 만들었어요"


# ── 품질 확인 ───────────────────────────────────────────

async def test_qc_retry_then_ok_ac26(env, client, monkeypatch):
    monkeypatch.setenv("IMAGE_SHOT_CONCURRENCY", "1")
    env.tap.sequence("img.qc", [i2t_json(QC_OK), i2t_json(QC_LOGO), i2t_json(QC_OK)])
    w = await prefilled(client)
    acc = await start_run(client, w["id"], count=2)
    await env.drain()
    gens = env.tap.by("/v1/t2i/generate")
    assert len(gens) == 3 and "Remove any logos" in gens[2]["body"]["prompt"]
    run = await get_run(client, acc["run_id"])
    img = (await client.get(f"/v1/images/{run['shots'][1]['image_id']}")).json()
    assert img["current"]["qc"]["status"] == "ok" and img["current"]["generation"]["qc_attempts"] == 2
    assert not run["shots"][1]["qc_flag"]


async def test_qc_fail_twice_ac27(env, client, monkeypatch):
    monkeypatch.setenv("IMAGE_SHOT_CONCURRENCY", "1")
    env.tap.sequence("img.qc", [i2t_json(QC_OK), i2t_json(QC_LOGO), i2t_json(QC_LOGO)])
    w = await prefilled(client)
    acc = await start_run(client, w["id"], count=2)
    await env.drain()
    run = await get_run(client, acc["run_id"])
    s2 = run["shots"][1]
    assert s2["state"] == "done" and s2["qc_flag"] is True and "로고" in (s2["qc_reason"] or "")
    img = (await client.get(f"/v1/images/{s2['image_id']}")).json()
    assert img["current"]["qc"]["status"] == "check"


async def test_qc_no_json_ac28(env, client):
    env.tap.override("img.qc", lambda b, n: (200, {"call_id": "c", "provider": "mock", "model": "mock", "content": "모르겠어요",
                                                    "json": None, "boxes": []}))
    w, run = await done_run(env, client, count=2)
    img = (await client.get(f"/v1/images/{run['shots'][0]['image_id']}")).json()
    assert img["current"]["qc"]["status"] == "skipped" and "qc:skipped" in img["current"]["generation"]["fallbacks"]
    assert run["shots"][0]["qc_flag"] is True


_ = (DESC, new_work)
