"""mi 서비스 설정 — services/mi/config/*.yaml (MIR 시트와 서버 판단이 같은 값을 읽는다).

`MI_CONFIG_DIR` 로 다른 폴더를 줄 수 있다(테스트: 임계값을 바꿔 AC-MI-01 확인). 파일 수정 시각이 바뀌면 다시 읽는다.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

import yaml

from winmate_common import env

_lock = threading.Lock()
_cache: dict[str, tuple[float, Any]] = {}


def config_dir() -> Path:
    custom = env.get("MI_CONFIG_DIR")
    if custom:
        return Path(custom)
    return Path(__file__).resolve().parents[2] / "config"


def _load(name: str) -> Any:
    path = config_dir() / name
    mtime = path.stat().st_mtime
    key = str(path)
    hit = _cache.get(key)
    if hit and hit[0] == mtime:
        return hit[1]
    with _lock:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        _cache[key] = (mtime, data)
        return data


def routing() -> dict[str, Any]:
    return _load("routing.yaml")


def thresholds() -> dict[str, Any]:
    return routing().get("thresholds", {})


def th(key: str, default: float | int | None = None) -> Any:
    return thresholds().get(key, default)


def segments_cfg() -> dict[str, Any]:
    return _load("segments.yaml")


def templates_cfg() -> dict[str, Any]:
    return _load("templates.yaml")


def segment_list() -> list[dict[str, Any]]:
    return list(segments_cfg().get("segments", []))


def segment(code: str | None) -> dict[str, Any]:
    for s in segment_list():
        if s["code"] == code:
            return s
    return next(s for s in segment_list() if s["code"] == "GEN")


SEGMENT_CODES = ("FB", "RT", "SV", "HT", "TP", "VN", "AD", "OF", "RS", "ID", "ED", "PB", "MD", "MF", "FN", "OE")


def home_segments() -> list[str]:
    raw = env.get("MI_HOME_SEGMENTS")
    if raw:
        return [x.strip().upper() for x in raw.split(",") if x.strip()]
    return list(segments_cfg().get("home_segments_default") or ["FB", "MD", "ED", "MF", "HT", "OF"])


def organize_concurrency() -> int:
    return max(1, env.get_int("MI_ORGANIZE_CONCURRENCY", 2))


def snapshots_dir() -> Path:
    from winmate_common.env import settings

    d = settings().service_data_dir("mi") / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def clock_today() -> str | None:
    """테스트용 고정 시계(MI_TODAY=2026-10-06). 없으면 None(실제 날짜)."""
    return os.environ.get("MI_TODAY") or None
