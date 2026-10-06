"""설정 — `services/competitor/config/*.yaml`(CAR 규칙 · 임계값 · 16업종) + 환경 변수 덮어쓰기.

- `CA_ASK_SLOTS_REQUIRE_AMBIGUOUS_INDUSTRY` (기본 true, §11 Q1): false 면 고객사 · 장소가 둘 다 비면 업종과 관계없이 묻는다.
- `CA_TODAY` (YYYY-MM-DD): 테스트 고정 시계(실행일 D). 없으면 오늘(Asia/Seoul).
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from winmate_common import env

SERVICE = "competitor"
KST = timezone(timedelta(hours=9))
_DIR = Path(__file__).resolve().parents[2] / "config"


@lru_cache(maxsize=4)
def _load(name: str) -> dict[str, Any]:
    return yaml.safe_load((_DIR / f"{name}.yaml").read_text(encoding="utf-8")) or {}


def routing() -> dict[str, Any]:
    return _load("routing")


def th(key: str, default: float | None = None) -> float:
    v = (routing().get("thresholds") or {}).get(key, default)
    return float(v if v is not None else 0.0)


def weights() -> dict[str, float]:
    return {k: float(v) for k, v in (routing().get("weights") or {}).items()}


def caps() -> dict[str, int]:
    return {k: int(v) for k, v in (routing().get("caps") or {}).items()}


def page_size() -> int:
    return int(routing().get("page_size") or 6)


def drop_extra() -> int:
    return int(routing().get("drop_extra") or 3)


def criteria_rules() -> dict[str, Any]:
    return dict(routing().get("criteria") or {})


def budgets(kind: str) -> dict[str, int]:
    return {k: int(v) for k, v in ((routing().get("budgets") or {}).get(kind) or {}).items()}


def concurrency() -> int:
    v = os.environ.get("CA_ANALYZE_CONCURRENCY")
    return int(v) if v and v.isdigit() else int(routing().get("concurrency") or 2)


def eta() -> dict[str, int]:
    return {k: int(v) for k, v in (routing().get("eta") or {}).items()}


def recheck_days() -> int:
    return int(routing().get("recheck_days") or 30)


def fact_order() -> list[str]:
    return list((routing().get("facts") or {}).get("order") or ["lineup", "solution", "references", "price", "recent"])


def fact_label(key: str) -> str:
    return ((routing().get("facts") or {}).get("labels") or {}).get(key, key)


def fact_progress_label(key: str) -> str:
    return ((routing().get("facts") or {}).get("progress") or {}).get(key, key)


def self_entities() -> list[str]:
    return [str(x) for x in routing().get("self_entities") or []]


def ask_requires_ambiguous() -> bool:
    raw = env.get("CA_ASK_SLOTS_REQUIRE_AMBIGUOUS_INDUSTRY")
    if raw is None:
        return bool(routing().get("ask_slots_require_ambiguous_industry", True))
    return raw.strip().lower() in {"1", "true", "yes", "on", "y"}


# ── 업종 ─────────────────────────────────────────────────
def segments() -> list[dict[str, Any]]:
    return list(_load("segments").get("segments") or [])


def general() -> dict[str, Any]:
    return dict(_load("segments").get("general") or {"code": "GEN", "full": "범용", "short": "범용"})


def segment(code: str | None) -> dict[str, Any]:
    for s in segments():
        if s["code"] == code:
            return s
    return general()


SEGMENT_CODES = tuple(s["code"] for s in segments())


def segment_for_kr(kr_id: str | None) -> list[str]:
    """KB A2 의 KR 업종 → 대응하는 Winmate 업종 코드들."""
    if not kr_id:
        return []
    return [s["code"] for s in segments() if kr_id in (s.get("kr") or [])]


# ── 시계 ─────────────────────────────────────────────────
def today() -> date:
    raw = os.environ.get("CA_TODAY")
    if raw:
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            pass
    return datetime.now(KST).date()


def now() -> datetime:
    """실행 시각(UTC). CA_TODAY 가 있으면 그 날 정오(KST) 기준으로 고정한다(재현 가능한 날짜 비교)."""
    raw = os.environ.get("CA_TODAY")
    if raw:
        d = today()
        return datetime(d.year, d.month, d.day, 12, 0, tzinfo=KST).astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def snapshots_dir() -> Path:
    d = env.settings().service_data_dir(SERVICE) / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def reload() -> None:
    _load.cache_clear()
