"""spec 설정 · 설정 파일(YAML) · 시계.

환경 변수(모두 선택)
- SPEC_CATALOG_ADAPTER   kb(기본) · fixture — 사내 카탈로그 어댑터(06-spec §4.15.1)
- SPEC_CATALOG_FIXTURE   fixture 어댑터 JSON 경로(테스트 CAT_FIX)
- SPEC_ELECTRICITY_KRW_PER_KWH  파생 행 `연간 전기료 (추정)` 단가(원/kWh). 없으면 값 확인(`계산 기준`)
- SPEC_FIXED_NOW         고정 시계(ISO 8601, 테스트) — 예 2026-10-06T01:00:00Z
- SPEC_CONFIG_DIR        설정 폴더(기본 services/spec/config)
- SPEC_WARRANTY_FILE · SPEC_LIFECYCLE_FILE · SPEC_COMBOS_FILE  개별 파일 바꾸기(테스트)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from winmate_common import env

SERVICE = "spec"
FEATURE = "SP"
KST = timezone(timedelta(hours=9))
PRODUCT_LIMIT = 8


def config_dir() -> Path:
    p = env.get("SPEC_CONFIG_DIR")
    return Path(p) if p else Path(__file__).resolve().parents[2] / "config"


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}


@lru_cache(maxsize=8)
def _yaml_cached(path: str, mtime: float) -> dict[str, Any]:
    return _load_yaml(Path(path))


def load_config(name: str, override_env: str | None = None) -> dict[str, Any]:
    """config/<name> 를 읽는다(파일 수정 시각이 바뀌면 다시 읽음)."""
    p = Path(env.get(override_env) or "") if override_env and env.get(override_env) else config_dir() / name
    try:
        mtime = p.stat().st_mtime
    except FileNotFoundError:
        return {}
    return _yaml_cached(str(p), mtime)


def items_config(category: str = "signage") -> dict[str, Any]:
    cfg = load_config(f"items/{category}.yaml")
    return cfg or load_config("items/signage.yaml")


def combos_config() -> dict[str, Any]:
    return load_config("combos.yaml", "SPEC_COMBOS_FILE")


def warranty_config() -> dict[str, Any]:
    return load_config("warranty.yaml", "SPEC_WARRANTY_FILE")


def lifecycle_seed() -> list[dict[str, Any]]:
    return list(load_config("lifecycle.yaml", "SPEC_LIFECYCLE_FILE").get("entries") or [])


def catalog_adapter_name() -> str:
    return (env.get("SPEC_CATALOG_ADAPTER", "kb") or "kb").lower()


def catalog_fixture_path() -> str | None:
    return env.get("SPEC_CATALOG_FIXTURE")


def electricity_price() -> float | None:
    v = env.get("SPEC_ELECTRICITY_KRW_PER_KWH")
    try:
        return float(v) if v else None
    except ValueError:
        return None


# ── 시계 ───────────────────────────────────────────────

def now() -> datetime:
    fixed = env.get("SPEC_FIXED_NOW")
    if fixed:
        return datetime.fromisoformat(fixed.replace("Z", "+00:00")).astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now().isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
