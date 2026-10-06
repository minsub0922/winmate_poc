from __future__ import annotations

import pytest
from winmate_common import testing


@pytest.fixture
def env(tmp_path):
    with testing.environment(tmp_path, service="requirements"):
        yield


async def test_info(env):
    from winmate_requirements.main import app

    async with testing.api_client(app) as c:
        r = await c.get("/v1/info")
        assert r.status_code == 200
        assert r.json()["service"] == "requirements"


async def test_requires_internal_token(env):
    import httpx
    from winmate_requirements.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/v1/info")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHENTICATED"


def test_customer_question_templates():
    """'모름' 고객 질문 템플릿(LLM 실패 · 엉뚱한 출력 때) — 정중한 한 문장, 내부 말 없음."""
    from winmate_requirements.deep import template_customer_question as t

    assert t({"kind": "too_few_items", "target": {"kind": "keyman"}}, "개발사업팀장", {"name": "개발사업팀장"}) == (
        "개발사업팀장님께서 이번 사업에 더 바라시는 점이 있을까요?", "개발사업팀장 요구사항")
    assert t({"kind": "empty_field", "target": {"kind": "field", "field": "final_audience"}}, "최종 제안대상", None)[0] == \
        "최종 제안은 어느 분께 드리면 될까요?"
    assert t({"kind": "empty_field", "target": {"kind": "field", "field": "customer_name"}}, "고객사", None)[0] == "고객사를 알려 주실 수 있을까요?"
    assert t({"kind": "vague_scope", "target": {"kind": "item"}}, "업무환경 플랫폼", None)[0] == "'업무환경 플랫폼'에 어떤 내용이 들어가나요?"
    assert "가중치" not in t({"kind": "default_weights", "target": {"kind": "weights"}}, "가중치", None)[0]
