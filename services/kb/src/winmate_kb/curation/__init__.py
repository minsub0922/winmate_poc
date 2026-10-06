"""큐레이션 사전(사람이 검수하는 영역). 사실(이름·수치·문구)은 KB 원문 또는 보드 원문에서만 온다.

파일
- solutions.yaml       Winmate 솔루션 카탈로그 11개(G-SOL-1) + MagicINFO 프로필(G-SOL-2, 보드 원문)
- columns.yaml         분류별 모델 목록 열(G-PRD-4, 00-shell §9.4)
- spec_profiles.yaml   사이니지 핵심 스펙 프로필(G-PRD-2, 00-shell 부록 B)
- display.yaml         L1 순서, 모델 표시명 규칙(G-PRD-1), 영문 계열명, 해상도 라벨, 솔루션 종류 이름, 공간 짧은 말(G-CASE-2), 용도 이름(G-CASE-5)
- segments.yaml        Winmate 16업종 코드표(03-mi §5.7 · 10-proposal 부록 C) + 업종 단서 사전(초안)
- image_samples.yaml   보드 이미지 표본 26장 중 KB 자산 21장의 제목·원본 메타(G-IMG-3 · G-IMG-1)
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent


@lru_cache(maxsize=None)
def load(name: str) -> dict[str, Any]:
    return yaml.safe_load((HERE / f"{name}.yaml").read_text(encoding="utf-8")) or {}
