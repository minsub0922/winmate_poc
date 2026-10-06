"""설정 파일(services/vp/config/*.yaml) — 라우팅 규칙 · 임계값 · 업종 · 레이아웃 카탈로그의 단일 원천."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


@lru_cache(maxsize=None)
def _load(name: str) -> dict[str, Any]:
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def routing() -> dict[str, Any]:
    return _load("routing.yaml")


def layouts_raw() -> list[dict[str, Any]]:
    return list(_load("layouts.yaml").get("layouts") or [])


def th(key: str) -> Any:
    """임계값(routing.yaml thresholds)."""
    return routing()["thresholds"][key]


def industries() -> list[dict[str, Any]]:
    return list(routing()["industries"])


def generic_industry() -> dict[str, Any]:
    return dict(routing()["generic"])


def industry(code: str | None) -> dict[str, Any]:
    if not code or code == "GEN":
        return generic_industry()
    for it in industries():
        if it["code"] == code:
            return dict(it)
    return generic_industry()


INDUSTRY_CODES = ("FB", "RT", "SV", "HT", "TP", "VN", "AD", "OF", "RS", "ID", "ED", "PB", "MD", "MF", "FN", "OE")
