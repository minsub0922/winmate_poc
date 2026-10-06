"""워크플로 — 되묻기 interrupt/재개 · 자동 답 · 중지/다시 시도 · 조종 메모 · 후속 요청 · 오류(403 기밀 · 503 대체)."""
from __future__ import annotations

from typing import Any

import pytest

from vp_helpers import RFP_TEXT, ready_vp, run_jobs, upload
from winmate_common import testing


async def test_questions_interrupt_resume_two_approvers_make_vp_h(client):
    r = await client.post("/v1/vps", json={"start": "direct", "customer_name": "C 빌딩",
                                           "note": "회의실 디스플레이 교체 문의. 한 줄 메모뿐"})
    vid = r.json()["id"]
    r = await client.post(f"/v1/vps/{vid}/materials:collect", json={})
    job = r.json()["job_id"]
    await run_jobs()
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    # RFP 없음 · 결재자 모름 → 확인 권장 질문 하나로 잡이 멈춘다
    assert doc["active_job"]["job_id"] == job and doc["active_job"]["status"] == "awaiting_input"
    assert doc["ui_status"] == "ask" and doc["resume_route"] == f"/vp/{vid}/questions"
    open_qs = [q for q in doc["questions"] if q["status"] == "open"]
    assert [q["kind"] for q in open_qs] == ["approver"] and open_qs[0]["mode"] == "check"
    assert doc["labels"]["questions"].endswith("RFP 없음")
    assert any(m["state"] == "inferred" for m in doc["materials"]), "메모뿐 → 사례 DB 로 과제 추론"
    q = open_qs[0]
    keys = [o["key"] for o in q["options"]][:2]
    r = await client.post(f"/v1/vps/{vid}/questions:answer", json={"answers": [{"question_id": q["id"], "keys": keys}], "proceed": True})
    assert r.status_code == 200, r.text
    ans = r.json()
    assert ans["resumed_job_id"] == job
    await run_jobs()
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert doc["active_job"] is None and doc["materials_ready"]
    q = next(x for x in doc["questions"] if x["id"] == q["id"])
    assert q["status"] == "answered" and q["answer"]["by"] == "user"
    vp = next(s for s in doc["plan"]["sheets"] if s["role"] == "VP")
    assert vp["layout"]["code"] == "VP-H", doc["plan"]["sheets"]  # 결재자 2명 → 이해관계자형
    ch = next(s for s in doc["plan"]["sheets"] if s["role"] == "CH")
    assert ch["chip"].endswith("추론") and ch["mode"] == "check"


async def test_auto_answer_does_not_pause(client):
    r = await client.post("/v1/vps", json={"start": "direct", "customer_name": "C 빌딩", "note": "회의실 교체", "auto_answer": True})
    vid = r.json()["id"]
    await client.post(f"/v1/vps/{vid}/materials:collect", json={})
    await run_jobs()
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert doc["active_job"] is None and doc["materials_ready"]
    assert all(q["status"] != "open" for q in doc["questions"])
    assert any(q["status"] == "defaulted" for q in doc["questions"])


async def test_note_priority_pins_direction(client):
    r = await client.post("/v1/vps", json={"start": "direct", "customer_name": "N 체인 무인 매장",
                                           "note": "매출도 늘리고 싶지만 인건비 절감이 1순위"})
    vid = r.json()["id"]
    await client.post(f"/v1/vps/{vid}/materials:collect", json={})
    await run_jobs()
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert not [q for q in doc["questions"] if q["kind"] == "direction" and q["status"] == "open"]
    assert any(d["key"] == "direction" and d["mode"] == "pin" for d in doc["decisions"]), doc["decisions"]


async def test_generate_cancel_then_retry_and_steering_memo(client):
    from winmate_common.jobs import jobs

    vid = await ready_vp(client, generate=False)
    r = await client.post(f"/v1/vps/{vid}/generate", json={})
    gen = r.json()["job_id"]
    await jobs().cancel(gen)
    await run_jobs()
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert doc["status"] == "stopped" and doc["active_job"] is None
    assert doc["resume_route"] == f"/vp/{vid}/structure" and doc["step"] == 2  # §AC 33 — 중지 → VP2

    r = await client.post(f"/v1/vps/{vid}/generate", json={"retry": True})
    assert r.status_code == 202
    gen2 = r.json()["job_id"]
    await jobs().add_memo(gen2, "학생 가치는 수업 참여도로")
    await run_jobs()
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert doc["generated"] and doc["status"] in ("done", "check", "ask")
    assert any(d["text"].startswith("메모 반영 — ") and d["job_id"] == gen2 for d in doc["decisions"]), \
        [d["text"] for d in doc["decisions"]]


async def test_followup_requests_layout_request_and_numbers(client):
    vid = await ready_vp(client)
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    vp = next(s for s in doc["sheets"] if s["role"] == "VP" and s["kind"] == "main")

    # 기둥 수를 줄이면 내용이 빠진다 → 선택지 A/B/C 를 내고 VP3L 로
    r = await client.post(f"/v1/vps/{vid}/messages", json={"text": "가치 기둥 2개로", "context": "result"})
    assert r.status_code == 202
    await run_jobs()
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    reqs = [x for x in doc["layout_requests"] if x["status"] == "open"]
    if reqs:  # 기둥 3 → 2: 한 기둥이 빠지므로 선택지를 묻는다
        lr = reqs[0]
        lo = (await client.get(f"/v1/vps/{vid}/sheets/{lr['sheet_id']}/layout-options", params={"req": lr["id"]})).json()
        assert [o["key"] for o in lo["options"]] == ["A", "B", "C"]
        assert sum(1 for o in lo["options"] if o["recommended"]) == 1
        r = await client.post(f"/v1/vps/{vid}/sheets/{lr['sheet_id']}/layout",
                              json={"option_key": "B", "request_id": lr["id"], "pin": False})
        assert r.status_code in (200, 202), r.text
        await run_jobs()
        doc = (await client.get(f"/v1/vps/{vid}")).json()
        assert next(x for x in doc["layout_requests"] if x["id"] == lr["id"])["status"] == "applied"
        sheet = next(s for s in doc["sheets"] if s["id"] == lr["sheet_id"])
        assert sheet["layout"]["code"].endswith("2") or sheet["layout"]["code"] in ("VP-F2", "VP-B2")
    else:
        sheet = next(s for s in doc["sheets"] if s["id"] == vp["id"])
        assert sheet["layout"]["code"] in ("VP-F2", "VP-B2"), sheet["layout"]

    # 수치 직접 입력 → 지표 '지금' 값이 확보로
    ef = next(s for s in doc["sheets"] if s["role"] == "EF" and s["kind"] == "main")
    mv = (await client.get(f"/v1/vps/{vid}/sheets/{ef['id']}/metrics")).json()
    if mv["metrics"]:
        label = mv["metrics"][0]["label"]
        r = await client.post(f"/v1/vps/{vid}/messages", json={"text": f"{label} 지금 12%", "context": "numbers", "sheet_id": ef["id"]})
        assert r.status_code == 202
        await run_jobs()
        mv2 = (await client.get(f"/v1/vps/{vid}/sheets/{ef['id']}/metrics")).json()
        m = next(x for x in mv2["metrics"] if x["label"] == label)
        assert m["before"]["status"] == "secured" and "12" in m["before"]["display"], m


@pytest.fixture
def conf_env(tmp_path):
    with testing.environment(tmp_path, service="vp", MOCK_ENFORCE_CONFIDENTIAL="true"):
        testing.use_fake_redis()
        yield


@pytest.fixture
async def conf_client(conf_env):
    from winmate_vp.main import app

    apps: dict[str, Any] = {**testing.platform_apps(), "vp": app}
    for svc in ("requirements", "storyboard", "mi"):
        apps[svc] = testing.load_service_app(svc)
    with testing.inprocess(apps):
        async with testing.api_client(app) as c:
            yield c


async def test_confidential_material_blocked_by_policy(conf_client):
    client = conf_client
    r = await client.post("/v1/vps", json={"start": "direct", "customer_name": "A 커피 프랜차이즈"})
    vid = r.json()["id"]
    fid = await upload("A커피_RFP.txt", RFP_TEXT)
    await client.post(f"/v1/vps/{vid}/attachments", json={"file_id": fid})
    await client.post(f"/v1/vps/{vid}/materials:collect", json={})
    await run_jobs()
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert doc["last_error"] and doc["last_error"]["code"] == "POLICY_CONFIDENTIAL", doc.get("last_error")
    assert not doc["materials_ready"]


async def test_model_unavailable_falls_back_to_deterministic(client, monkeypatch):
    from winmate_common.errors import ApiError
    from winmate_vp import llm

    async def down(*_a, **_k):
        raise ApiError(503, "MODEL_UNAVAILABLE", "모델을 잠시 쓸 수 없어요.")
    monkeypatch.setattr(llm, "call", down)
    vid = await ready_vp(client)
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert doc["generated"] and all(s["title"] for s in doc["sheets"] if s["kind"] == "main")
    assert "[mock" not in str([s["title"] for s in doc["sheets"]])
