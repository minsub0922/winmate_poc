#!/usr/bin/env bash
# 대시보드 재생성: KB → 데이터 추출 → Python 기준 출력 → 브라우저 엔진 일치 검사 → 페이지 조립 → 스모크 테스트
set -euo pipefail
cd "$(dirname "$0")/.."
python3 dashboard/export_data.py
python3 dashboard/golden.py
node dashboard/parity.js
python3 dashboard/build_site.py "$@"
python3 dashboard/smoke.py
