"""2026-10-08 — 이미지 · 사례 검색이 안 되던 원인(벡터 모델 못 읽음) · 솔루션 매칭 공백 보완."""
from __future__ import annotations

import pytest



async def test_unmapped_solution_gets_text_matches(client, ok):
    """KB 에 솔루션 id 가 없는 카탈로그 솔루션(G-SOL-1)도 이름 글자 일치로 메시지 · 이미지 · 사례를 준다."""
    kc = ok(await client.get("/v1/solutions/knox_capture"))
    assert kc["kb_id"] is None and "G-SOL-1" in kc["gaps"]
    assert kc["messages"] and all(m["basis"] == "text_match" for m in kc["messages"])
    dex = ok(await client.get("/v1/solutions/dex/images"))
    ctx = [g for g in dex["groups"] if g["key"] == "context"]
    assert ctx and ctx[0]["items"] and "확인 필요" in ctx[0]["source_label"]
    hv = ok(await client.get("/v1/solutions/hvac_integrated/cases"))
    assert hv["total"] >= 1


async def test_pattern_targets_accept_catalog_ids(client, ok):
    """G2 · E1 이 카탈로그 id(magicinfo) · 이름(MagicINFO) 으로도 KB id(sol_magicinfo) 와 같은 결과를 준다."""
    a = ok(await client.post("/v1/query/G2", json={"kind": "solution", "ident": "sol_magicinfo", "limit": 5}), "POST")
    b = ok(await client.post("/v1/query/G2", json={"kind": "solution", "ident": "magicinfo", "limit": 5}), "POST")
    c = ok(await client.post("/v1/query/G2", json={"kind": "solution", "ident": "MagicINFO", "limit": 5}), "POST")
    assert a["result"]["n_total"] > 0 and a["result"]["n_total"] == b["result"]["n_total"] == c["result"]["n_total"]
    e = ok(await client.post("/v1/query/E1", json={"about": [{"kind": "solution", "id": "magicinfo"}]}), "POST")
    assert e["result"]["n"] > 0


async def test_lobby_image_search_prefers_space_scenes(client, ok):
    """'로비' 는 로비 맥락의 장면 사진이 먼저 온다(업종 페이지 화면 예시 그림이 아니라)."""
    body = ok(await client.get("/v1/images/search", params={"q": "로비", "limit": 6}))
    assert body["items"]
    kinds = [i["kind"] for i in body["items"][:6]]
    assert sum(1 for k in kinds if k in ("case", "industry", "product")) == len(kinds)
    metas = [ok(await client.get(f"/v1/images/{i['id']}")) for i in body["items"][:4]]
    assert sum(1 for m in metas if (m.get("context") or {}).get("space_type_id") == "lobby") >= 3


def test_vector_model_failure_degrades_to_keyword(env, tmp_path, monkeypatch):
    """벡터 모델 파일을 못 읽어도(판 차이 · 깨진 복사) 이미지 · 사례 · 메시지 검색이 예외 없이 키워드로 돈다."""
    import shutil

    from winmate_kb import config, engine as E

    src = config.db_path()
    kb_dir = tmp_path / "kb"
    (kb_dir / "models").mkdir(parents=True)
    shutil.copy(src, kb_dir / src.name)
    (kb_dir / "models" / "lsa_char24_v2.joblib").write_bytes(b"not a joblib")
    monkeypatch.setenv("WKB_KB", str(kb_dir))
    eng = E.Engine()
    k = eng.kb()
    assert k.image_search("로비", limit=5)["result"]["images"]
    assert k.D1(text="호텔 로비 사이니지", limit=5)["result"]["deployments"]
    assert k.E2("원격 콘텐츠 관리")["result"]["messages"]
    assert eng.shared.vector_failed and eng.shared.vector_error
