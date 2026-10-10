"""Storyboard 흐름(flow.json · summary.md) — 11-content-flow CF-01~CF-09 · 보드 SB0 · SB1 · Gate · Done."""
from __future__ import annotations

RQ = {"ref": "RQ-01", "ver": 2, "res_id": "rqf_1", "value": {"customer": "E 자산운용", "target": "대표이사", "goals": ["AI Ready 오피스의 새로운 모델"]},
      "md": "## 고객 요구사항\n- 대표이사(50%): 사용자를 인식하고 반응하는 오피스",
      "card": {"title": "용산 업무시설 재개발 AI Ready 오피스", "facts": [["고객사", "E 자산운용"]], "groups": [], "line": "RQ-01 v2 · 요구 12"}}
DSS = {"ref": "DSS-01", "ver": 1, "value": {"industry": {"value": "오피스 · 업무시설", "by": "ai-accepted"}, "spaces": [{"name": "로비", "products": ["The Wall IAB 146\""]}]},
       "md": "- 업종: 오피스 · 업무시설 / 공간 7"}


async def _new(client):
    r = await client.post("/v1/flows", json={"name": "용산 AI Ready 오피스", "customer": "E 자산운용", "target": "대표이사", "rq": RQ})
    assert r.status_code == 201, r.text
    return r.json()


async def test_create_from_requirements_and_progress(client):
    d = await _new(client)
    assert d["id"] == "SB-01" and d["progress"] == "요구사항까지"
    assert d["stages"]["rq"]["ref"] == "RQ-01" and d["stages"]["rq"]["customer"] == "E 자산운용"
    assert [c["key"] for c in d["cells"]] == ["rq", "dss", "mi", "ca", "vp", "sp", "sc", "ppt"]
    assert d["cells"][0]["route"] == "/requirements/flow/rqf_1"
    assert "## 1. 고객 요구사항 · RQ-01 v2" in d["summary_md"] and "## 남은 것" in d["summary_md"]
    assert d["flow_json"]["stages"]["rq"]["ver"] == 2


async def test_stage_requires_prerequisite_and_gate_lists(client):
    d = await _new(client)
    r = await client.put(f"/v1/flows/{d['id']}/stages/mi", json={"ref": "MI-01", "value": {}, "md": "- x"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "PREREQUISITE_MISSING"
    g = (await client.get("/v1/flows", params={"content": "mi"})).json()["items"][0]
    assert g["eligible"] is False and g["need"] == "dss"
    r = await client.put(f"/v1/flows/{d['id']}/stages/dss", json=DSS)
    assert r.status_code == 200
    out = r.json()
    assert out["md_added"].startswith("## DSS · DSS-01 v1") and out["flow"]["progress"] == "DSS까지"
    g = (await client.get("/v1/flows", params={"content": "mi"})).json()["items"][0]
    assert g["eligible"] is True and g["existing"] is None
    await client.put(f"/v1/flows/{d['id']}/stages/mi", json={"ref": "MI-01", "value": {"counts": {"kept": 11}}, "md": "- 담은 정보 11"})
    g = (await client.get("/v1/flows", params={"content": "mi"})).json()["items"][0]
    assert g["existing"]["ref"] == "MI-01" and g["progress"] == "DSS + 콘텐츠 1/5"


async def test_branch_shares_prerequisites_and_edit_syncs(client):
    d = await _new(client)
    await client.put(f"/v1/flows/{d['id']}/stages/dss", json=DSS)
    await client.put(f"/v1/flows/{d['id']}/stages/mi", json={"ref": "MI-01", "value": {}, "md": "- a"})
    await client.patch(f"/v1/flows/{d['id']}", json={"key_message": "AI Ready 오피스의 새로운 모델"})
    r = await client.post(f"/v1/flows/{d['id']}:branch", json={"stage": "mi"})
    assert r.status_code == 201
    b = r.json()
    assert b["parent"] == d["id"] and b["name"].endswith("분기 B")
    assert b["key_message"] is None and "## Key message" not in b["summary_md"]   # 보드 SB0: 분기 Key message 「아직 없음」
    assert b["stages"]["dss"]["sharedWith"] == [d["id"]] and b["stages"]["mi"] is None
    main = (await client.get(f"/v1/flows/{d['id']}")).json()
    assert main["branches"] == [b["id"]] and main["stages"]["dss"]["sharedWith"] == [b["id"]]
    # DSS 를 고치면(같은 ref) 분기에도 반영
    out = (await client.put(f"/v1/flows/{d['id']}/stages/dss", json={**DSS, "ver": 2})).json()
    assert out["synced"] == [b["id"]]
    assert (await client.get(f"/v1/flows/{b['id']}")).json()["stages"]["dss"]["ver"] == 2
    # 목록: 메인 바로 아래 분기
    ids = [x["id"] for x in (await client.get("/v1/flows")).json()["items"]]
    assert ids.index(b["id"]) == ids.index(d["id"]) + 1


async def test_key_message_and_user_lines_survive_regeneration(client):
    d = await _new(client)
    k = (await client.post(f"/v1/flows/{d['id']}/key-message:suggest")).json()
    assert k["candidates"] and k["candidates"][0]["text"]
    d = (await client.patch(f"/v1/flows/{d['id']}", json={"key_message": "AI Ready 오피스의 새로운 모델", "key_message_by": "ai-accepted"})).json()
    assert "## Key message\nAI Ready 오피스의 새로운 모델" in d["summary_md"]
    md = d["summary_md"].replace("## 1. 고객 요구사항 · RQ-01 v2\n", "## 1. 고객 요구사항 · RQ-01 v2\n- 회의에서 확인: 임원 보고는 11월\n")
    d = (await client.patch(f"/v1/flows/{d['id']}", json={"summary_md": md, "expected_version": d["version"]})).json()
    assert d["user_lines"] == {"rq": ["- 회의에서 확인: 임원 보고는 11월"]}
    d = (await client.put(f"/v1/flows/{d['id']}/stages/dss", json=DSS)).json()["flow"]
    assert "- 회의에서 확인: 임원 보고는 11월 ✎" in d["summary_md"]
    assert (await client.patch(f"/v1/flows/{d['id']}", json={"name": "x", "expected_version": 1})).status_code == 409


async def test_content_list_groups_storyboards(client):
    d = await _new(client)
    await client.put(f"/v1/flows/{d['id']}/stages/dss", json={**DSS, "title": "용산 오피스 공간별 제품", "res_id": "dss_1"})
    b = (await client.post(f"/v1/flows/{d['id']}:branch", json={"stage": "mi"})).json()
    items = (await client.get("/v1/flows/contents/dss")).json()["items"]
    assert len(items) == 1 and items[0]["title"] == "용산 오피스 공간별 제품" and items[0]["route"] == "/dss/dss_1"
    assert [s["id"] for s in items[0]["storyboards"]] == [d["id"], b["id"]]
    assert (await client.get("/v1/flows/contents/rq")).json()["items"][0]["ref"] == "RQ-01"


async def test_sb1_branch_items_list_key_message_and_pillars(client):
    """SB0 Key message 칸 · 분기 표시 · SB1 「분기 n」 팝오버 · 전략 수립 받쳐 줄 메시지(요약본 Key message 절에 함께)."""
    d = await _new(client)
    await client.put(f"/v1/flows/{d['id']}/stages/dss", json=DSS)
    await client.put(f"/v1/flows/{d['id']}/stages/mi", json={"ref": "MI-01", "value": {}, "md": "- a"})
    b = (await client.post(f"/v1/flows/{d['id']}:branch", json={"stage": "mi"})).json()
    await client.put(f"/v1/flows/{b['id']}/stages/mi", json={"ref": "MI-02", "title": "리테일 테넌트 관점", "value": {}, "md": "- b"})
    main = (await client.get(f"/v1/flows/{d['id']}")).json()
    assert main["branch_items"] == [{"id": b["id"], "name": b["name"], "stage": "mi", "ref": "MI-02", "title": "리테일 테넌트 관점"}]
    d2 = (await client.patch(f"/v1/flows/{d['id']}", json={
        "key_message": "AI Ready 오피스의 새로운 모델", "key_message_by": "ai-accepted",
        "key_pillars": [{"text": "사용자를 먼저 알아보는 공간", "evidence": ["RQ-01 대표이사"]}, {"text": "  ", "evidence": []}]})).json()
    assert d2["key_message"]["by"] == "ai-accepted" and d2["key_message"]["pillars"] == [{"text": "사용자를 먼저 알아보는 공간", "evidence": ["RQ-01 대표이사"]}]
    assert "## Key message\nAI Ready 오피스의 새로운 모델\n- 사용자를 먼저 알아보는 공간\n" in d2["summary_md"]
    assert d2["flow_json"]["keyPillars"] == ["사용자를 먼저 알아보는 공간"] and d2["branch_items"][0]["id"] == b["id"]
    # 받쳐 줄 메시지 줄은 생성 줄 — 요약본을 그대로 보내도 사람 문장으로 남지 않는다
    d3 = (await client.patch(f"/v1/flows/{d['id']}", json={"summary_md": d2["summary_md"]})).json()
    assert d3["user_lines"] == {}
    items = (await client.get("/v1/flows")).json()["items"]
    row = next(x for x in items if x["id"] == d["id"])
    br = next(x for x in items if x["id"] == b["id"])
    assert row["key_message"] == "AI Ready 오피스의 새로운 모델" and row["branch_point"] is None
    assert br["is_branch"] and br["branch_point"]["stage"] == "mi"


async def test_key_message_suggest_llm_pillars_and_rule_fallback(client):
    """AI 후보 3안 — mock(보드 예시) 근거 코드는 이 Storyboard 의 실제 코드로 맞춘다. 모델 후보가 없으면 연결 콘텐츠 문장으로 규칙 후보."""
    rq = {**RQ, "ref": "RQ-7K", "value": {**RQ["value"], "keymen": [{"role": "대표이사", "weight": 50, "needs": ["사용자를 인식하고 반응하는 오피스", "최초 AI Ready로 알리기"]}]}}
    r = await client.post("/v1/flows", json={"name": "용산 AI Ready 오피스", "customer": "E 자산운용", "rq": rq})
    fid = r.json()["id"]
    await client.put(f"/v1/flows/{fid}/stages/dss", json={**DSS, "ref": "DSS-7K"})
    k = (await client.post(f"/v1/flows/{fid}/key-message:suggest")).json()
    assert k["mode"] == "llm" and [c["id"] for c in k["candidates"]] == ["A", "B", "C"]
    a = k["candidates"][0]
    assert a["text"] == "공간이 먼저 알아보는 오피스" and len(a["pillars"]) == 3
    assert a["pillars"][0]["evidence"] == ["RQ-7K 대표이사", "DSS-7K 로비"]
    assert a["pillars"][2]["evidence"] == []   # MI 가 없으니 MI-01 근거는 버린다
    # 다른 이름 → mock 기본(후보 없음) → 규칙 후보(요구 목표 · 키맨 니즈 문장 그대로)
    r = await client.post("/v1/flows", json={"name": "판교 스타트업 단지", "customer": "G 공사", "rq": rq})
    k = (await client.post(f"/v1/flows/{r.json()['id']}/key-message:suggest")).json()
    assert k["mode"] == "rule"
    texts = [c["text"] for c in k["candidates"]]
    assert texts == ["AI Ready 오피스의 새로운 모델", "사용자를 인식하고 반응하는 오피스"]
    assert k["candidates"][0]["pillars"][0] == {"text": "사용자를 인식하고 반응하는 오피스", "evidence": ["RQ-7K 대표이사"]}


SB1_MD = """# 용산 AI Ready 오피스 — Storyboard 요약
고객: E 자산운용 · 최종 제안대상: 대표이사 · main

## Key message
AI Ready 오피스의 새로운 모델

## 1. 고객 요구사항 · RQ-01 v2
- 대표이사(50%): 사용자를 인식하고 반응하는 오피스 · 최초 AI Ready로 알리기
- 공간컨텐츠실장(30%): 업무환경 플랫폼 [확인 필요]
- 개발사업팀장(20%): 설계 단계 AI 인프라 · 유지보수 최소화

## 2. DSS · DSS-01 v1
- 업종: 오피스 · 업무시설 / 공간 7
- 로비: The Wall IAB 146" · QM55C ×2 · 키오스크
- 솔루션: MagicINFO · SmartThings Pro · b.IoT

## 3. Market Intelligence · MI-01 v1
- 담은 정보 11 (시장 4 · 고객사 4 · 사용자 3)

## 남은 것
- 경쟁사 · VP · Spec · 공간 시나리오 → 제안서"""


async def test_summary_and_done_headers_match_boards(client):
    """요약본 전체 = 보드 SB1 그대로(번호 · 긴 이름 · 남은 것 「공간 시나리오」), 완료 화면 더해진 부분 = 보드 Done 머리(짧은 이름 · 번호 없음)."""
    rq = {**RQ, "md": "## 고객 요구사항 · RQ-01 v2\n- 대표이사(50%): 사용자를 인식하고 반응하는 오피스 · 최초 AI Ready로 알리기\n"
                       "- 공간컨텐츠실장(30%): 업무환경 플랫폼 [확인 필요]\n- 개발사업팀장(20%): 설계 단계 AI 인프라 · 유지보수 최소화"}
    r = await client.post("/v1/flows", json={"name": "용산 AI Ready 오피스", "customer": "E 자산운용", "target": "대표이사", "rq": rq})
    fid = r.json()["id"]
    out = (await client.put(f"/v1/flows/{fid}/stages/dss", json={**DSS, "md": "- 업종: 오피스 · 업무시설 / 공간 7\n"
                                                                 "- 로비: The Wall IAB 146\" · QM55C ×2 · 키오스크\n- 솔루션: MagicINFO · SmartThings Pro · b.IoT"})).json()
    assert out["md_added"].startswith("## DSS · DSS-01 v1\n- 업종: 오피스 · 업무시설 / 공간 7")
    # 콘텐츠가 보낸 머리(긴 이름)는 버리고 보드 Done 머리로
    out = (await client.put(f"/v1/flows/{fid}/stages/mi", json={"ref": "MI-01", "ver": 1, "value": {},
                                                                "md": "## Market Intelligence · MI-01 v1\n- 담은 정보 11 (시장 4 · 고객사 4 · 사용자 3)"})).json()
    assert out["md_added"] == "## MI · MI-01 v1\n- 담은 정보 11 (시장 4 · 고객사 4 · 사용자 3)"
    d = (await client.patch(f"/v1/flows/{fid}", json={"key_message": "AI Ready 오피스의 새로운 모델"})).json()
    assert d["summary_md"] == SB1_MD
    # flow.json — 보드 SB1_Json 키 순서 · progress 'dss+1/5' · 받쳐 줄 메시지가 없으면 keyPillars 없음
    fj = d["flow_json"]
    assert list(fj) == ["id", "name", "parent", "branches", "keyMessage", "stages", "progress", "summary", "updatedAt"]
    assert fj["progress"] == "dss+1/5" and list(fj["stages"]) == ["rq", "dss", "mi", "ca", "vp", "sp", "sc", "ppt"]
    assert d["progress"] == "DSS + 콘텐츠 1/5"
    # 나머지 콘텐츠 — 보드 Done 머리
    heads = {"ca": ("CA-01", "## 경쟁사 · CA-01 v1"), "vp": ("VP-01", "## VP · VP-01 v1"), "sp": ("SP-01", "## Spec · SP-01 v1"),
             "sc": ("SC-01", "## 시나리오 · SC-01 v1")}
    for k, (ref, head) in heads.items():
        o = (await client.put(f"/v1/flows/{fid}/stages/{k}", json={"ref": ref, "value": {}, "md": f"## {k}\n- x"})).json()
        assert o["md_added"] == f"{head}\n- x"
    d = (await client.get(f"/v1/flows/{fid}")).json()
    assert "## 4. 경쟁사 분석 · CA-01 v1" in d["summary_md"] and "## 7. 공간 시나리오 · SC-01 v1" in d["summary_md"]
    assert "## 남은 것" not in d["summary_md"] and d["flow_json"]["progress"] == "dss+5/5"
    # 요구사항만 있으면 「남은 것」에 DSS 부터, progress 'rq'
    r = await client.post("/v1/flows", json={"name": "동탄 시니어 복합단지", "customer": "F 시행사", "rq": {**RQ, "ref": "RQ-04"}})
    d2 = r.json()
    assert d2["summary_md"].endswith("## 남은 것\n- DSS · MI · 경쟁사 · VP · Spec · 공간 시나리오 → 제안서")
    assert d2["flow_json"]["progress"] == "rq" and d2["history"][-1]["md"].startswith("## 요구사항 · RQ-04 v2")


async def test_user_lines_under_short_or_numbered_headers(client):
    """요약본 수정 — 번호 붙은 머리든 완료 화면의 짧은 머리든 같은 절로 받아 ✎ 로 남긴다."""
    d = await _new(client)
    await client.put(f"/v1/flows/{d['id']}/stages/dss", json=DSS)
    d = (await client.get(f"/v1/flows/{d['id']}")).json()
    md = d["summary_md"] + "\n\n## DSS · DSS-01 v1\n- 로비 동선은 현장 확인 후 확정"
    md = md.replace("## 2. DSS · DSS-01 v1\n", "## 2. DSS · DSS-01 v1\n- 회의실 수량은 11월 실사 뒤\n")
    d = (await client.patch(f"/v1/flows/{d['id']}", json={"summary_md": md})).json()
    assert d["user_lines"] == {"dss": ["- 회의실 수량은 11월 실사 뒤", "- 로비 동선은 현장 확인 후 확정"]}
    assert "- 회의실 수량은 11월 실사 뒤 ✎\n- 로비 동선은 현장 확인 후 확정 ✎" in d["summary_md"]


async def test_clear_ppt_stage_only_matching_ref(client):
    """제안서를 지우면 proposal 이 「PPT 제작」 칸을 비운다 — ref 가 같을 때만 · 콘텐츠 칸은 비울 수 없다."""
    d = await _new(client)
    sid = d["id"]
    r = await client.put(f"/v1/flows/{sid}/stages/ppt", json={"ref": "PR-03", "res_id": "pr_x", "value": {"title": "제안서"}, "md": "- 표준 제안서"})
    assert r.status_code == 200 and next(c for c in r.json()["flow"]["cells"] if c["key"] == "ppt")["state"] == "done"
    out = (await client.delete(f"/v1/flows/{sid}/stages/ppt", params={"ref": "PR-99"})).json()        # 다른 제안서 → 그대로
    assert next(c for c in out["flow"]["cells"] if c["key"] == "ppt")["ref"] == "PR-03"
    out = (await client.delete(f"/v1/flows/{sid}/stages/ppt", params={"ref": "PR-03"})).json()
    cell = next(c for c in out["flow"]["cells"] if c["key"] == "ppt")
    assert cell["state"] == "none" and out["flow"]["stages"].get("ppt") is None and "ppt" not in out["flow"]["cards"]
    assert out["flow"]["history"][-1]["note"] == "PR-03 연결 끊김"
    r = await client.delete(f"/v1/flows/{sid}/stages/rq")
    assert r.status_code == 422 and r.json()["error"]["code"] == "STAGE_NOT_CLEARABLE"
    assert (await client.delete(f"/v1/flows/{sid}/stages/ppt")).status_code == 200                   # 이미 비었으면 그대로
