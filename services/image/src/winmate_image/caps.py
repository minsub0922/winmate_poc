"""모델 능력 → 기능 플래그(07-image §6.1). ai-tools `/v1/capabilities` 를 60초 캐시한다."""
from __future__ import annotations

import logging
import time
from typing import Any

from winmate_common.ai import ai

from . import config

log = logging.getLogger("winmate.image.caps")

_cache: tuple[float, dict[str, Any]] | None = None
TTL_S = 60.0

_DEFAULT = {
    "mode": "unknown",
    "t2i": {"supports": {"reference_images": False, "edit": False, "mask": False}, "max_side_px": 1024,
            "images_per_call": 1, "max_reference_images": 3, "available": False, "provider": "unknown", "model": "unknown"},
    "i2t": {"supports": {"json_schema": False, "bbox": False}, "available": False, "provider": "unknown", "model": "unknown"},
    "llm": {"available": False, "provider": "unknown", "model": "unknown"},
}


def reset() -> None:
    global _cache
    _cache = None


async def raw() -> dict[str, Any]:
    global _cache
    if _cache and time.time() - _cache[0] < TTL_S:
        return _cache[1]
    try:
        caps = await ai().capabilities(max_age_s=0)
    except Exception as exc:  # noqa: BLE001
        log.warning("ai-tools 능력을 읽지 못했습니다: %s", exc)
        return _DEFAULT
    _cache = (time.time(), caps)
    return caps


class Flags:
    """워크플로가 쓰는 판단 묶음."""

    def __init__(self, caps: dict[str, Any]):
        t2i = caps.get("t2i") or {}
        i2t = caps.get("i2t") or {}
        ts = t2i.get("supports") or {}
        its = i2t.get("supports") or {}
        self.mode = caps.get("mode") or "unknown"
        self.t2i_available = bool(t2i.get("available", True))
        self.ref_images = bool(ts.get("reference_images")) and self.t2i_available
        self.edit = bool(ts.get("edit")) and self.t2i_available
        self.mask = bool(ts.get("mask")) and self.edit
        self.max_refs = int(t2i.get("max_reference_images") or 3)
        self.max_side = int(t2i.get("max_side_px") or 1024)
        self.images_per_call = int(t2i.get("images_per_call") or 1)
        self.t2i_provider = str(t2i.get("provider") or "unknown")
        self.t2i_model = str(t2i.get("model") or "unknown")
        self.i2t_available = bool(i2t.get("available", True))
        self.bbox = bool(its.get("bbox")) and self.i2t_available
        self.i2t_json = bool(its.get("json_schema")) and self.i2t_available
        self.upscaler = config.upscaler()

    def features(self) -> dict[str, bool]:
        return {
            "object_select": self.bbox,
            "mask_native": self.mask,
            "outpaint": self.edit,
            "recompose": self.ref_images or self.edit,
            "upscale_4x": self.upscaler != "none",
            "region_edit": self.edit,
            "reference_images": self.ref_images,
        }


async def flags() -> Flags:
    return Flags(await raw())


async def capabilities() -> dict[str, Any]:
    caps = await raw()
    f = Flags(caps)
    return {
        "mode": f.mode,
        "t2i": {"supports_reference_images": f.ref_images, "supports_edit": f.edit, "supports_mask": f.mask,
                "max_side_px": f.max_side, "images_per_call": f.images_per_call, "max_reference_images": f.max_refs,
                "available": f.t2i_available},
        "i2t": {"supports_json": f.i2t_json, "supports_bbox": f.bbox, "available": f.i2t_available},
        "upscaler": f.upscaler,
        "features": f.features(),
        "available": caps is not _DEFAULT,
    }
