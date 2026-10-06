"""GET /v1/capabilities · GET /v1/usage — 지금 설정(제공자 · 모델 · 지원 기능 · 한도)과 오늘 사용량."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from winmate_common.errors import ApiError

from . import config, embed, limits, providers, search


def _available(mode: str, cfg: config.CapConfig) -> bool:
    if mode in ("mock", "replay"):
        return True
    try:
        return providers.get(cfg.provider_key).available(cfg)
    except ApiError:
        return False


async def _counts(mode: str) -> dict[str, tuple[int, int]]:
    if mode == "mock":   # mock 은 Redis 를 건드리지 않는다
        return {c: (0, 0) for c in config.CAPS}
    values = await asyncio.gather(*(limits.counts(c) for c in config.CAPS))
    return dict(zip(config.CAPS, values))


async def capabilities() -> dict[str, Any]:
    mode = config.model_mode()
    c = {cap: config.load(cap) for cap in config.CAPS}
    llm, i2t, t2i, ws = c["llm"], c["i2t"], c["t2i"], c["websearch"]

    def prov(cfg: config.CapConfig) -> str:
        return "mock" if mode == "mock" else cfg.provider

    counts = await _counts(mode)
    sc = config.search_config()
    ec = config.embed_config()
    emb_ok = embed.available(ec)
    return {
        "mode": mode,
        "llm": {"provider": prov(llm), "model": llm.model, "max_input_tokens": llm.max_input_tokens,
                "max_output_tokens": llm.max_output_tokens,
                "supports": {"json_schema": llm.supports_json_schema, "tools": llm.supports_tools, "streaming": llm.supports_streaming},
                "allow_confidential": llm.allow_confidential, "available": _available(mode, llm)},
        "i2t": {"provider": prov(i2t), "model": i2t.model, "max_images_per_call": i2t.max_images_per_call,
                "max_image_side_px": i2t.max_image_side_px,
                "supports": {"json_schema": i2t.supports_json_schema, "bbox": i2t.supports_bbox},
                "allow_confidential": i2t.allow_confidential, "available": _available(mode, i2t)},
        "t2i": {"provider": prov(t2i), "model": t2i.model, "max_side_px": t2i.max_side_px, "default_aspect": t2i.default_aspect,
                "max_reference_images": t2i.max_reference_images,
                "images_per_call": t2i.images_per_call,
                "supports": {"reference_images": t2i.supports_reference_images, "edit": t2i.supports_edit, "mask": t2i.supports_mask},
                "allow_confidential": t2i.allow_confidential, "available": _available(mode, t2i)},
        "websearch": {"provider": prov(ws), "model": ws.model, "return_sources": ws.return_sources,
                      "allow_confidential": ws.allow_confidential, "available": _available(mode, ws)},
        "search_api": {"provider": sc.provider, "available": search.available(sc)},
        "fetch": {"enabled": config.fetch_config().enabled},
        "embedding": {"provider": ec.provider, "model": ec.model, "available": emb_ok,
                      "dim": (ec.dim or (384 if (mode == "mock" or ec.provider == "mock") else None)) if emb_ok else None},
        "usage_today": {cap: counts[cap][0] for cap in config.CAPS},
        "limits": {"enforced": mode in ("live", "record"),
                   **{cap: {"rpm": cfg.rpm, "daily": cfg.daily_limit, "max_concurrency": cfg.max_concurrency,
                            "timeout_s": cfg.timeout_s} for cap, cfg in c.items()}},
    }


async def usage() -> dict[str, Any]:
    mode = config.model_mode()
    counts = await _counts(mode)
    out: dict[str, Any] = {}
    for cap in config.CAPS:
        cfg = config.load(cap)
        today, minute = counts[cap]
        out[cap] = {"today": today, "daily_limit": cfg.daily_limit,
                    "remaining": max(0, cfg.daily_limit - today) if cfg.daily_limit > 0 else None,
                    "this_minute": minute, "rpm": cfg.rpm}
    return {"date": time.strftime("%Y-%m-%d"), "mode": mode, "enforced": mode in ("live", "record"), "usage": out}
