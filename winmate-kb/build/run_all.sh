#!/usr/bin/env bash
# 전체 재빌드: raw/ + seed/ → kb/winmate_kb.sqlite, 인덱스, 품질 점검, 시나리오 테스트, 질의 예시 문서
set -euo pipefail
cd "$(dirname "$0")/.."
python3 build/build_kb.py
python3 build/index_kb.py
python3 build/qa.py
python3 tests/test_scenarios.py
python3 tests/make_cookbook.py
