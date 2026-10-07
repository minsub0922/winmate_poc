# board_slots — 보드 예시 값을 슬롯 모양으로 옮긴 것

`<템플릿 코드>.json` = `POST /exports` 의 `slides[].slots` 와 같은 모양. 값은 원본 보드(`docs/templates/source/<캔버스>/<보드>.dc.html`)의
`renderVals()` 예시 데이터에서 옮긴다(사실이 아니라 시험 · 비교용 예시).

- `services/export/scripts/compare_boards.py` 가 있으면 이 값으로, 없으면 `example_slots` 로 슬라이드를 만들어 보드와 나란히 놓는다.
- 작업 순서 · 판정 기준: `docs/templates/PPT_TASK.md`.
