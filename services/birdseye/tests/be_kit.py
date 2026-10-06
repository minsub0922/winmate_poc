"""birdseye 시험 도우미(이름이 겹치지 않게 conftest 밖으로 — 여러 서비스 시험을 한 번에 돌릴 때 `conftest` 모듈 이름이 겹친다)."""
from __future__ import annotations

import asyncio
import io
from typing import Any

from winmate_common import testing


def handlers() -> dict[str, Any]:
    from winmate_birdseye.worker import HANDLERS

    return HANDLERS


async def drain(max_rounds: int = 30) -> int:
    """birdseye 잡을 다 처리한다. 렌더는 image 잡을 함께 돌려야 끝나므로 image 큐도 옆에서 비운다."""
    img = testing.load_service_worker("image")
    stop = asyncio.Event()

    async def image_pump() -> None:
        while not stop.is_set():
            try:
                await testing.drain_jobs("image", img, max_jobs=5)
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(0.02)

    task = asyncio.create_task(image_pump())
    total = 0
    try:
        for _ in range(max_rounds):
            n = await testing.drain_jobs("birdseye", handlers(), max_jobs=20)
            total += n
            if n == 0:
                break
    finally:
        stop.set()
        await task
    return total


async def upload(name: str, data: bytes, mime: str) -> str:
    from winmate_common.platform import save_file

    meta = await save_file(name, data, mime, source="upload", confidential=True)
    return meta["id"]


def png(w: int = 320, h: int = 240, color: tuple[int, int, int] = (128, 128, 128), *, pattern: str = "noise") -> bytes:
    """작은 시험 그림. pattern: noise(선명 · 보통 밝기) · backlit(밝은 창 30% + 어두운 나머지) · dark · flat(흐림)."""
    import numpy as np
    from PIL import Image

    rng = np.random.default_rng(7)
    if pattern == "backlit":
        a = np.full((h, w, 3), 50, dtype=np.uint8)
        a += rng.integers(0, 30, size=(h, w, 3), dtype=np.uint8)
        a[:, : int(w * 0.32)] = 250
    elif pattern == "dark":
        a = rng.integers(0, 60, size=(h, w, 3), dtype=np.uint8)
    elif pattern == "flat":
        a = np.full((h, w, 3), 140, dtype=np.uint8)
    else:
        a = rng.integers(40, 220, size=(h, w, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(a).save(buf, "PNG")
    return buf.getvalue()


def raster_plan(w: int = 1200, h: int = 900) -> bytes:
    """래스터 평면도: 흰 바탕 + 굵은 외곽(0.1~0.9) — be.plan_analyze 목 박스와 맞춘 그림."""
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = int(w * 0.1), int(h * 0.1), int(w * 0.9), int(h * 0.9)
    d.rectangle([x0, y0, x1, y1], outline="black", width=10)
    d.rectangle([int(w * 0.337), int(h * 0.475), int(w * 0.355), int(h * 0.5)], fill="black")
    d.rectangle([int(w * 0.565), int(h * 0.475), int(w * 0.583), int(h * 0.5)], fill="black")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


async def create(client: Any, **body: Any) -> dict[str, Any]:
    r = await client.post("/v1/birdseyes", json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def seed_golden(be_id: str, *, layout: bool = False, furniture: bool = True) -> None:
    """골든 공간 · 제품 · 가구를 저장소에 바로 넣는다(kb 픽스처 대신 — 실제 KB 에 OH55C · WA75D · IAB 가 없다)."""
    import golden

    from winmate_birdseye.inputs import save_space
    from winmate_birdseye.repo import repo

    await save_space(be_id, {**golden.space(), "features": [{"kind": "storefront_window", "label": "전면 유리창", "hint_cap": "cap_sunlight_readable",
                                                            "cap_label": "고휘도 권장"},
                                                           {"kind": "columns", "label": "중앙 기둥", "count": 2},
                                                           {"kind": "night_visibility", "label": "외부 노출"}]})
    for p in golden.products():
        await repo().put("products", p["id"], {**p, "birdseye_id": be_id})
    if furniture:
        for f in golden.furniture():
            await repo().put("furniture", f["id"], {**f, "birdseye_id": be_id})
        await repo().patch("birdseyes", be_id, {"step": 3, "recommendations": {"shown": ["lounge_sofa_set", "column_wrap_frame",
                                                                                         "viewing_bench", "info_desk"]}})
    else:
        await repo().patch("birdseyes", be_id, {"step": 2})
    if layout:
        from winmate_birdseye.engine import generate
        from winmate_birdseye.layouts import params, save_layout

        lay = generate(golden.space(), golden.products(), [f for f in golden.furniture() if f.get("selected")], intents=golden.intents(),
                       params=await params(), version=0)
        await save_layout(be_id, lay, created_by="engine", note="intent:llm")
