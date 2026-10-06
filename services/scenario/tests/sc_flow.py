"""시험 흐름 도우미 — 보드 예(A 커피 매장 하루) 입력 → 타임라인 → 솔루션 · 제품 → 생성."""
from __future__ import annotations

from typing import Any

from winmate_common import testing

RAW = ("07:00 점장이 매장을 오픈한다. 메뉴보드가 아침 메뉴로 켜져 있어야 한다.\n"
       "11:30 점심 피크. 주문 줄이 길어지고 프로모션 음료가 잘 팔린다.\n"
       "14:00 본사 마케팅팀이 전국 320개 매장에 오후 프로모션을 배포한다.\n"
       "21:00 마감. 메뉴보드가 자동으로 꺼지고 전력 사용량이 집계된다.")
CHARS = ["점장", "손님", "본사 마케팅 담당자"]
QM55C = {"ref": "kb:model:mdl_LH55QMCEBGCXKR", "family_id": "fam_G000182628", "model_code": "LH55QMCEBGCXKR", "label": "Smart Signage QM55C",
         "short": "QM55C", "qty": 3}
KM24C = {"ref": "custom:Kiosk KM24C", "label": "Kiosk KM24C", "short": "KM24C"}


async def drain(max_jobs: int = 50) -> int:
    from winmate_scenario.worker import HANDLERS
    return await testing.drain_jobs("scenario", HANDLERS, max_jobs=max_jobs)


async def create(c: Any, **body: Any) -> dict[str, Any]:
    r = await c.post("/v1/scenarios", json={"type": "with", **body})
    assert r.status_code == 201, r.text
    return r.json()


async def get(c: Any, sid: str) -> dict[str, Any]:
    r = await c.get(f"/v1/scenarios/{sid}")
    assert r.status_code == 200, r.text
    return r.json()


async def parse(c: Any, sid: str, raw: str = RAW, characters: list[str] | None = None) -> dict[str, Any]:
    r = await c.post(f"/v1/scenarios/{sid}/input:parse", json={"raw_text": raw, "characters": CHARS if characters is None else characters})
    assert r.status_code == 202, r.text
    await drain()
    return await get(c, sid)


async def timeline(c: Any, sid: str) -> dict[str, Any]:
    r = await c.get(f"/v1/scenarios/{sid}/timeline")
    assert r.status_code == 200, r.text
    return r.json()


async def ops(c: Any, sid: str, *ops_: dict[str, Any], undo: bool = False, redo: bool = False) -> dict[str, Any]:
    r = await c.post(f"/v1/scenarios/{sid}/timeline/ops", json={"ops": list(ops_), "undo": undo, "redo": redo})
    assert r.status_code == 200, r.text
    return r.json()


async def pick(c: Any, sid: str, solutions: list[str] | None = None, products: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if solutions is not None:
        r = await c.put(f"/v1/scenarios/{sid}/solutions", json={"items": [{"solution_id": s} for s in solutions]})
        assert r.status_code == 200, r.text
    r = await c.put(f"/v1/scenarios/{sid}/products", json={"items": products if products is not None else [QM55C, KM24C]})
    assert r.status_code == 200, r.text
    return r.json()


async def generate(c: Any, sid: str, scope: str = "all") -> str:
    r = await c.post(f"/v1/scenarios/{sid}/generate", json={"scope": scope})
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    await drain()
    return job_id


async def board(c: Any, *, type_: str = "with", customer: str | None = None) -> dict[str, Any]:
    """보드 예 시나리오를 생성 완료까지: WITH MagicINFO · SmartThings Pro, QM55C ×3 · KM24C."""
    sc = await create(c, type=type_)
    sid = sc["id"]
    if customer:
        from winmate_scenario import repo

        def fn(d: dict[str, Any]) -> dict[str, Any]:
            d["customer_name"] = customer
            return d
        await repo.update(sid, fn)
    await parse(c, sid)
    await pick(c, sid, ["magicinfo", "smartthings_pro"] if type_ == "with" else None)
    r = await c.post(f"/v1/scenarios/{sid}:route-generate")
    assert r.status_code == 200, r.text
    await generate(c, sid)
    return await get(c, sid)


async def scenes(c: Any, sid: str) -> list[dict[str, Any]]:
    r = await c.get(f"/v1/scenarios/{sid}/scenes")
    assert r.status_code == 200, r.text
    return r.json()["items"]


def by_no(items: list[dict[str, Any]], no: int) -> dict[str, Any]:
    return next(s for s in items if s["no"] == no)
