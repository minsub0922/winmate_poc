"""테스트 공통 — 저장소 루트를 import 경로에 넣고, 내장 제품 시드만 쓰는 카탈로그를 만든다(KB 없이도 같은 결과)."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from birdseye.catalog import Catalog  # noqa: E402
from birdseye.config import Settings  # noqa: E402

_CAT = None


def catalog() -> Catalog:
    global _CAT
    if _CAT is None:
        _CAT = Catalog(None)
    return _CAT


def temp_settings(extra: dict | None = None) -> Settings:
    """임시 데이터 폴더 + 임시 .env 로 Settings 를 만든다(실제 .env · 키를 건드리지 않음)."""
    d = Path(tempfile.mkdtemp(prefix="birdseye-test-"))
    lines = [f"BIRDSEYE_DATA_DIR={d / 'data'}", "MODEL_MODE=live", "LLM_PROVIDER=gemini", "I2T_PROVIDER=gemini"]
    for k, v in (extra or {}).items():
        lines.append(f"{k}={v}")
    env = d / ".env"
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for k in ("BIRDSEYE_DATA_DIR", "MODEL_MODE", "BIRDSEYE_MODEL_MODE", "GEMINI_API_KEY", "LLM_API_KEY", "I2T_API_KEY",
              "LLM_PROVIDER", "I2T_PROVIDER", "LLM_ALLOW_CONFIDENTIAL", "I2T_ALLOW_CONFIDENTIAL"):
        os.environ.pop(k, None)
    return Settings(env)
