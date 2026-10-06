"""시험 흐름 도우미 — 정의서 → 기획 질의 → 기획 방향 → 목차까지 한 번에."""
from __future__ import annotations

from typing import Any

from winmate_common import testing

from sb_world import RQ


async def drain() -> int:
    from winmate_storyboard.worker import HANDLERS
    return await testing.drain_jobs("storyboard", HANDLERS)


async def create(c: Any, rq_id: str = RQ) -> dict[str, Any]:
    r = await c.post("/v1/storyboards", json={"requirement_id": rq_id})
    assert r.status_code in (200, 201), r.text
    await drain()
    r = await c.get(f"/v1/storyboards/{r.json()['id']}")
    assert r.status_code == 200, r.text
    return r.json()


def q_by_topic(sb: dict[str, Any], topic: str) -> dict[str, Any]:
    return next(q for q in sb["planning"]["questions"] if q["topic"] == topic)


async def answer_all(c: Any, sb: dict[str, Any]) -> None:
    sid = sb["id"]
    for q in sb["planning"]["questions"]:
        opts = q["options"]
        body: dict[str, Any] = {"selected_option_ids": [opts[0]["id"]] if q["select"] == "single" else [o["id"] for o in opts[:2]]}
        fu = opts[0].get("follow_up")
        if q["select"] == "single" and fu:
            body["follow_up_option_id"] = fu["options"][2]["id"]
        r = await c.put(f"/v1/storyboards/{sid}/planning/{q['id']}", json=body)
        assert r.status_code == 200, r.text


async def to_direction(c: Any) -> dict[str, Any]:
    sb = await create(c)
    await answer_all(c, sb)
    r = await c.post(f"/v1/storyboards/{sb['id']}/direction", json={})
    assert r.status_code == 202, r.text
    await drain()
    return (await c.get(f"/v1/storyboards/{sb['id']}")).json()


async def to_outline(c: Any) -> dict[str, Any]:
    sb = await to_direction(c)
    r = await c.post(f"/v1/storyboards/{sb['id']}/outline", json={})
    assert r.status_code == 202, r.text
    await drain()
    sb = (await c.get(f"/v1/storyboards/{sb['id']}")).json()
    assert sb["outline"]["ready"], sb["outline"]
    return sb


def space_named(sb: dict[str, Any], name: str) -> dict[str, Any]:
    return next(s for s in sb["outline"]["spaces"] if s["name"] == name)


def section_key(sb: dict[str, Any], key: str) -> dict[str, Any]:
    return next(s for s in sb["outline"]["sections"] if s["key"] == key)
