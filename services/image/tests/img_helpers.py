"""image 테스트 도우미(이름이 겹치지 않게 img_ 접두)."""
from __future__ import annotations

import asyncio
import base64
import io
import json
from collections.abc import Callable
from typing import Any

from PIL import Image, ImageDraw

from winmate_common import testing

DESC = "카페 카운터 위에 3연 메뉴보드가 걸린 장면, 낮 시간, 손님 2~3명"
KB_CASE_IMAGES = ["img_5581f01513fedc17", "img_743ba382df12fffd", "img_c7f91ec940eda835"]
KB_PRODUCT_IMAGE = "img_9ec6148d2e4d9c18"


async def new_work(client, desc: str = DESC, kind: str = "space", **kw: Any) -> dict:
    r = await client.post("/v1/works", json={"kind": kind, "description": desc, **kw})
    assert r.status_code == 201, r.text
    return r.json()


async def prefilled(client, desc: str = DESC, kind: str = "space") -> dict:
    w = await new_work(client, desc, kind)
    r = await client.post(f"/v1/works/{w['id']}:prefill")
    assert r.status_code == 200, r.text
    return r.json()["work"]


async def start_run(client, work_id: str, **body: Any) -> dict:
    r = await client.post(f"/v1/works/{work_id}/runs", json={"kind": "initial", **body})
    assert r.status_code == 202, r.text
    return r.json()


async def done_run(env, client, desc: str = DESC, count: int = 4) -> tuple[dict, dict]:
    w = await prefilled(client, desc)
    acc = await start_run(client, w["id"], count=count)
    await env.drain()
    run = (await client.get(f"/v1/runs/{acc['run_id']}")).json()
    assert run["status"] == "succeeded", run
    return w, run


async def wait_for(pred, timeout: float = 20.0, interval: float = 0.05):
    t = 0.0
    while t < timeout:
        v = await pred()
        if v:
            return v
        await asyncio.sleep(interval)
        t += interval
    raise AssertionError("기다리던 상태가 오지 않았습니다")


async def file_image(file_id: str) -> Image.Image:
    from winmate_common.platform import file_bytes

    data, _ = await file_bytes(file_id)
    return Image.open(io.BytesIO(data)).convert("RGB")


def b64_image(data_b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(data_b64))).convert("RGB")


async def patch_conditions(client, work: dict, **changes: Any) -> dict:
    cond = {**work["conditions"], **changes}
    r = await client.patch(f"/v1/works/{work['id']}", json={"conditions": cond})
    assert r.status_code == 200, r.text
    return r.json()


USER = "u_test"


class AiTap:
    """ai-tools ASGI 앞단 — 기록 · task 별 응답 바꾸기 · 지연 · T2I 동시 실행 수 측정."""

    def __init__(self, app: Any):
        self.app = app
        self.calls: list[dict[str, Any]] = []
        self.overrides: dict[str, Callable[[dict[str, Any], int], tuple[int, dict[str, Any]] | None]] = {}
        self.delays: dict[str, float] = {}
        self.active = 0
        self.max_active = 0
        self.counts: dict[str, int] = {}

    def by(self, path: str | None = None, task: str | None = None) -> list[dict[str, Any]]:
        return [c for c in self.calls if (path is None or c["path"] == path) and (task is None or c["task"] == task)]

    def override(self, task: str, fn: Callable[[dict[str, Any], int], tuple[int, dict[str, Any]] | None]) -> None:
        self.overrides[task] = fn

    def sequence(self, task: str, items: list[tuple[int, dict[str, Any]] | None]) -> None:
        """task 의 n 번째 호출 → items[n](None 이면 진짜 ai-tools 로). 끝나면 마지막 것을 반복."""
        def fn(_body: dict[str, Any], n: int) -> tuple[int, dict[str, Any]] | None:
            return items[min(n, len(items) - 1)]

        self.overrides[task] = fn

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        chunks = []
        more = True
        while more:
            msg = await receive()
            chunks.append(msg.get("body", b""))
            more = msg.get("more_body", False)
        raw = b"".join(chunks)
        try:
            body = json.loads(raw) if raw else None
        except ValueError:
            body = None
        path = scope["path"]
        task = (body or {}).get("task") if isinstance(body, dict) else None
        self.calls.append({"path": path, "task": task, "body": body})
        n = self.counts.get(task or path, 0)
        self.counts[task or path] = n + 1
        is_t2i = path.startswith("/v1/t2i/")
        if is_t2i:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            d = self.delays.get(task or "") or (self.delays.get("t2i") if is_t2i else 0)
            if d:
                await asyncio.sleep(d)
            fn = self.overrides.get(task or "")
            res = fn(body or {}, n) if fn else None
            if res is not None:
                status, payload = res
                data = json.dumps(payload, ensure_ascii=False).encode()
                await send({"type": "http.response.start", "status": status,
                            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(data)).encode())]})
                await send({"type": "http.response.body", "body": data})
                return
            sent = False

            async def replay() -> dict[str, Any]:
                nonlocal sent
                if sent:
                    return {"type": "http.disconnect"}
                sent = True
                return {"type": "http.request", "body": raw, "more_body": False}

            await self.app(scope, replay, send)
        finally:
            if is_t2i:
                self.active -= 1


def llm_json(obj: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    return 200, {"call_id": "call_test", "provider": "mock", "model": "mock", "content": json.dumps(obj, ensure_ascii=False), "json": obj}


def i2t_json(obj: dict[str, Any], boxes: list[dict[str, Any]] | None = None) -> tuple[int, dict[str, Any]]:
    return 200, {"call_id": "call_test", "provider": "mock", "model": "mock", "content": json.dumps(obj, ensure_ascii=False), "json": obj,
                 "boxes": boxes or []}


def api_error(status: int, code: str, message: str = "오류") -> tuple[int, dict[str, Any]]:
    return status, {"error": {"code": code, "message": message, "details": {}}}


def png(w: int = 320, h: int = 200, color: tuple[int, int, int] = (90, 120, 160), face: tuple[int, int, int, int] | None = None) -> bytes:
    im = Image.new("RGB", (w, h), color)
    d = ImageDraw.Draw(im)
    d.rectangle([w // 3, h // 4, 2 * w // 3, 3 * h // 4], fill=(230, 210, 120))
    if face:
        # 분산이 큰 체커 무늬(흐림 검증용)
        x0, y0, x1, y1 = face
        for yy in range(y0, y1, 4):
            for xx in range(x0, x1, 4):
                c = 255 if ((xx // 4) + (yy // 4)) % 2 else 0
                d.rectangle([xx, yy, xx + 3, yy + 3], fill=(c, c, c))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


class Env:
    def __init__(self, tap: AiTap, apps: dict[str, Any]):
        self.tap = tap
        self.apps = apps

    async def drain(self, max_jobs: int = 60) -> int:
        from winmate_image.worker import HANDLERS

        return await testing.drain_jobs("image", HANDLERS, max_jobs=max_jobs)

    async def upload(self, data: bytes, name: str = "photo.png", *, confidential: bool = True) -> str:
        import base64

        from winmate_common.client import ServiceClient

        res = await ServiceClient("files").post("/v1/files/bytes", json={
            "name": name, "mime": "image/png", "data_b64": base64.b64encode(data).decode(), "source": "upload",
            "confidential": confidential})
        return res["id"]


