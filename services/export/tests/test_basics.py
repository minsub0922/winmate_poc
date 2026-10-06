from __future__ import annotations

import pytest
from winmate_common import testing


@pytest.fixture
def env(tmp_path):
    with testing.environment(tmp_path, service="export"):
        yield


async def test_info(env):
    from winmate_export.main import app

    async with testing.api_client(app) as c:
        r = await c.get("/v1/info")
        assert r.status_code == 200
        assert r.json()["service"] == "export"


async def test_requires_internal_token(env):
    import httpx
    from winmate_export.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/v1/info")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHENTICATED"


def _exe(path, body: str):
    path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_soffice_status_reasons_and_fix_message(tmp_path, monkeypatch):
    """SOFFICE_PATH: 경로 · off · 없는 경로 · 비어 있음(끔 — 이 서버에서 찾은 soffice 를 안내)."""
    from winmate_export.render import soffice

    fake = _exe(tmp_path / "soffice", "exit 0")
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setenv("SOFFICE_PATH", "")
    st = soffice.status()
    assert (st.path, st.reason, st.detected) == (None, "unset", str(fake)) and not soffice.available()
    msg, details = soffice.unavailable_message("PPTX → PDF 변환")
    assert f"SOFFICE_PATH={fake}" in msg and details["detected"] == str(fake) and details["reason"] == "unset"
    monkeypatch.setenv("SOFFICE_PATH", str(tmp_path / "nope"))
    assert soffice.status().reason == "missing" and "nope" in soffice.unavailable_message("x")[0]
    monkeypatch.setenv("SOFFICE_PATH", str(fake))
    assert soffice.status() == soffice.Status(str(fake), "env", str(fake), str(fake)) and soffice.available()
    monkeypatch.setenv("SOFFICE_PATH", "soffice")                          # PATH 의 이름도 된다
    assert soffice.status().path == str(fake)
    monkeypatch.setenv("SOFFICE_PATH", "off")
    assert soffice.status().reason == "off" and not soffice.available()
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.setenv("SOFFICE_PATH", "")
    msg, details = soffice.unavailable_message("슬라이드 그림 만들기")
    assert "detected" not in details and "apt-get" in msg


def test_pdf_font_status_with_fake_fc_match(tmp_path, monkeypatch):
    from winmate_export.render import soffice

    fc = _exe(tmp_path / "fc-match", "echo 'Noto Sans CJK KR,Noto Sans CJK KR Regular'")
    monkeypatch.setenv("PATH", str(tmp_path))
    soffice.font_status.cache_clear()
    try:
        assert soffice.font_status("Noto Sans KR") == {"family": "Noto Sans KR", "resolved": "Noto Sans CJK KR", "ok": True}
        assert soffice.font_warning("Noto Sans KR") is None
        _exe(fc, "echo 'Inter'")
        soffice.font_status.cache_clear()
        assert soffice.font_status("Noto Sans KR")["ok"] is False and "Inter" in soffice.font_warning("Noto Sans KR")
        monkeypatch.setenv("PATH", str(tmp_path / "empty"))
        soffice.font_status.cache_clear()
        assert soffice.font_status("Noto Sans KR")["ok"] is None and soffice.font_warning("Noto Sans KR") is None
    finally:
        soffice.font_status.cache_clear()


async def test_info_reports_converter_and_features(env, monkeypatch):
    from winmate_export.main import app

    monkeypatch.setenv("SOFFICE_PATH", "off")
    async with testing.api_client(app) as c:
        info = (await c.get("/v1/info")).json()
    assert info["pdf_converter"] is False and info["pdf_converter_reason"] == "off" and info["features"] == ["form_fill"]
    assert info["pdf_font"]["family"] == "Noto Sans KR" and "ok" in info["pdf_font"]
