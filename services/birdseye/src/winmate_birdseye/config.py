"""설정 — services/birdseye/config/{rules,furniture_catalog}.yaml + .env 스위치(08-birdseye §10.3 · §10.4)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from winmate_common import env

SERVICE = "birdseye"
FEATURE = "BE"            # workspace feature 코드(계약 enum)
SECTION = "공간 조감도 생성"
STEPS = ["공간 입력", "배치될 제품", "가구 추천", "배치 · 인테리어 컨펌", "3D 조감도 생성"]


def config_dir() -> Path:
    return env.repo_root() / "services" / "birdseye" / "config"


@lru_cache(maxsize=1)
def rules() -> dict[str, Any]:
    with open(config_dir() / "rules.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def catalog() -> dict[str, Any]:
    with open(config_dir() / "furniture_catalog.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def catalog_item(code: str | None) -> dict[str, Any] | None:
    if not code:
        return None
    for it in catalog()["items"]:
        if it["code"] == code:
            return it
    return None


def chip_info(chip: str | None) -> dict[str, Any]:
    chips = rules()["space_chips"]
    return chips.get(chip or "store_lobby") or chips["store_lobby"]


def tone_info(tone: str | None) -> dict[str, Any]:
    tones = rules()["tones"]
    return tones.get(tone or "warm_wood") or tones["warm_wood"]


def light_info(light: str | None) -> dict[str, Any]:
    lights = rules()["lights"]
    return lights.get(light or "day") or lights["day"]


def auto_extra_cuts() -> bool:
    v = env.get("AUTO_EXTRA_CUTS")
    if v is None:
        return bool(rules()["auto_extra_cuts"].get("enabled", True))
    return v.lower() in {"1", "true", "yes", "on"}


def public_base_url() -> str:
    """QR 업로드 주소의 앞부분(휴대폰이 닿는 PC 주소). 없으면 상대 경로."""
    return (env.get("PUBLIC_BASE_URL") or "").rstrip("/")


def render_target() -> str:
    """image 렌더 목표 해상도 — 기본 rules.yaml(uhd = 3840×2160). `BE_RENDER_TARGET=fhd` 는 메모리가 빠듯한 장비 · 시험용."""
    v = (env.get("BE_RENDER_TARGET") or "").strip().lower()
    return v if v in ("fhd", "uhd") else str(rules()["render"]["target"])


def render_poll_s() -> float:
    return env.get_float("BE_RENDER_POLL_S", 0.5)


def render_timeout_s() -> float:
    return env.get_float("BE_RENDER_TIMEOUT_S", 900.0)


def retry_delays() -> list[float]:
    raw = env.get("BE_RETRY_DELAYS", "2,6") or ""
    out: list[float] = []
    for part in raw.split(","):
        try:
            out.append(float(part))
        except ValueError:
            continue
    return out


def llm_timeout_s() -> float:
    return env.get_float("BE_LLM_TIMEOUT_S", 60.0)
