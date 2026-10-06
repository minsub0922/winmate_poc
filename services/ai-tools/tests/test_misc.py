"""임베딩 · 호출 로그(줄이기 · 보관 기간 · 모드) · PDF 수집."""
from __future__ import annotations

import io
import json
import sqlite3

import numpy as np
import pytest
import respx


# ── 임베딩 ─────────────────────────────────────────────────

async def test_embed_disabled_lsa(client):
    r = await client.post("/v1/embed", json={"texts": ["가"], "kind": "query"})
    assert r.status_code == 501 and r.json()["error"]["code"] == "EMBEDDING_DISABLED"


async def test_embed_local_not_installed(client, monkeypatch):
    monkeypatch.setenv("MODEL_MODE", "live")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    r = await client.post("/v1/embed", json={"texts": ["가"], "kind": "passage"})
    assert r.status_code == 501
    err = r.json()["error"]
    assert err["code"] == "NOT_CONFIGURED" and "sentence-transformers" in err["message"]
    caps = (await client.get("/v1/capabilities")).json()
    assert caps["embedding"]["available"] is False


async def test_embed_mock_vectors(client, monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    texts = ["호텔 로비 디지털 사이니지", "호텔 로비의 디지털 사이니지 설치", "냉장고 에너지 효율"]
    body = (await client.post("/v1/embed", json={"texts": texts})).json()
    assert body["provider"] == "mock" and body["model"] == "BAAI/bge-m3" and body["dim"] == 1024
    v = np.array(body["vectors"])
    assert v.shape == (3, 1024) and np.allclose(np.linalg.norm(v, axis=1), 1.0, atol=1e-4)
    assert v[0] @ v[1] > v[0] @ v[2]     # 비슷한 글은 더 가깝다
    again = (await client.post("/v1/embed", json={"texts": texts[:1]})).json()
    assert again["vectors"][0] == body["vectors"][0]
    caps = (await client.get("/v1/capabilities")).json()
    assert caps["embedding"] == {"provider": "local", "model": "BAAI/bge-m3", "available": True, "dim": 1024}


# ── 호출 로그 ───────────────────────────────────────────────

async def test_call_log_scrubs_base64_and_paginates(client, h):
    big = h.b64(h.noise_png((64, 64)))
    for i in range(3):
        msg = {"role": "user", "content": [{"type": "text", "text": f"n{i}"}, {"type": "image", "data_b64": big, "mime": "image/png"}]}
        assert (await client.post("/v1/llm/chat", json={"task": "rq.page", "messages": [msg]})).status_code == 200
    page1 = (await client.get("/v1/calls", params={"task": "rq.page", "limit": 2})).json()
    assert len(page1["items"]) == 2 and page1["next_cursor"]
    page2 = (await client.get("/v1/calls", params={"task": "rq.page", "limit": 2, "cursor": page1["next_cursor"]})).json()
    assert len(page2["items"]) == 1 and page2["next_cursor"] is None
    ids = [x["id"] for x in page1["items"] + page2["items"]]
    assert len(set(ids)) == 3
    logged = page1["items"][0]["request"]["messages"][0]["content"][1]["data_b64"]
    assert logged.startswith("<base64 ") and big not in json.dumps(page1)


async def test_call_log_modes(client, monkeypatch):
    monkeypatch.setenv("MODEL_CALL_LOG", "meta")
    await client.post("/v1/llm/chat", json={"task": "rq.meta", "messages": [{"role": "user", "content": "비밀 아님"}]})
    rec = (await client.get("/v1/calls", params={"task": "rq.meta"})).json()["items"][0]
    assert rec["request"] is None and rec["response"] is None and rec["usage"]["input_tokens"] > 0
    monkeypatch.setenv("MODEL_CALL_LOG", "off")
    await client.post("/v1/llm/chat", json={"task": "rq.off", "messages": [{"role": "user", "content": "x"}]})
    assert (await client.get("/v1/calls", params={"task": "rq.off"})).json()["items"] == []


async def test_call_log_retention_prune(env):
    from winmate_ai_tools import calllog

    store = calllog.store()
    store.put({"id": "call_old", "ts": "2020-01-01T00:00:00.000Z", "capability": "llm", "task": "t", "status": "ok"})
    store.put({"id": "call_new", "ts": "2999-01-01T00:00:00.000Z", "capability": "llm", "task": "t", "status": "ok"})
    assert store.prune(30) == 1
    assert store.get("call_old") is None and store.get("call_new") is not None
    conn = sqlite3.connect(store.path)
    assert conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0] == 1


async def test_lifespan_prunes(env):
    from winmate_ai_tools import calllog
    from winmate_ai_tools.main import app, lifespan

    calllog.store().put({"id": "call_old", "ts": "2020-01-01T00:00:00.000Z", "capability": "llm", "task": "t", "status": "ok"})
    async with lifespan(app):
        pass
    assert calllog.store().get("call_old") is None


def test_scrub():
    from winmate_ai_tools.calllog import scrub

    s = scrub({"data_b64": "abc", "url": "data:image/png;base64,AAAA", "text": "가" * 30000, "vec": list(range(500)), "b": b"xy"})
    assert s["data_b64"].startswith("<base64") and s["url"].startswith("<base64") and s["b"].startswith("<bytes 2")
    assert len(s["text"]) < 21000 and s["vec"][-1] == "…(+400 items)"


# ── PDF 수집 ────────────────────────────────────────────────

async def test_fetch_pdf_pages(client, monkeypatch):
    pytest.importorskip("pypdfium2")
    canvas = pytest.importorskip("reportlab.pdfgen.canvas")
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, "Page one about signage")
    c.showPage()
    c.drawString(72, 720, "Page two about kiosks")
    c.save()
    monkeypatch.setenv("WEB_FETCH_RESPECT_ROBOTS", "false")
    monkeypatch.setenv("WEB_FETCH_RATE_LIMIT_RPS", "0")
    with respx.mock() as router:
        router.get("https://docs.example.com/r.pdf").respond(200, content=buf.getvalue(), headers={"content-type": "application/pdf"})
        body = (await client.post("/v1/fetch", json={"url": "https://docs.example.com/r.pdf"})).json()
    assert body["content_type"] == "application/pdf" and len(body["pages"]) == 2
    assert "signage" in body["pages"][0] and "kiosks" in body["pages"][1] and "signage" in body["text"]
