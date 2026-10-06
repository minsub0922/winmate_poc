## kb 새 필드 쓰기(보증 · 후속 후보 · 소비전력 모드 · A3 단위) — kb · 2026-10-07
- 필요: docs/requests/kb.md spec 요청 4건의 답(맨 아래 `kb 답변`). `pm2 restart kb` 뒤 쓸 수 있다.
  - 보증 행: 모델 상세 · `POST /v1/spec/table` `derived[code].warranty`(`status=stated` 면 `years`, `statement_only` 면 원문 `text` + `[확정 필요]` 유지 — 사이니지는 연수 원천 없음).
  - 단종 경고 · P3 `lifecycle:check`: `/lifecycle` 의 `successors[]`(relation=similar, `newer`, `reason`)를 후속 후보로 보여 주고 확정은 사람이 — `successor` 는 계속 null. `config/lifecycle.yaml` 은 그대로 우선해도 된다.
  - `소비전력 (일반 · 최대)`: `derived[code].power.typical` · `.max`(LED Max 는 `per_m2=true`, 단위 `W/㎡` 그대로 표기). On Mode 는 `power.values` 의 `mode=on`.
  - A3: 크기 항목의 `unit_basis` · `value_cm` · `value_inch` 를 쓰면 spec 쪽 인치 보정(§9.4-30)을 줄일 수 있다(`unit_basis=default` 는 단위 없음 → 확인 필요).
  - 치수: `derived[code].dims_mm`(축 순서 정규화, 예전 `dimensions_mm` 은 그대로).
- 상태: 요청(kb → spec 안내)

## XLSX 내보내기를 고객사 양식 파일 그대로 — export 새 옵션 쓰기 — export · 2026-10-07
- 필요: §4.18 「XLSX 내보내기는 고객사 파일을 바탕으로 같은 칸에 값을 써 넣는다(서식 유지)」 — export 가 지원한다(docs/requests/export.md 답).
  `spec_export` 에서 양식이 있으면 지금 보내는 xlsx 요청에 `base_file_id: <양식 file_id>` 만 더하면 된다(document.sheets 그대로 — 행 이름 × 열 머리로 맞춤).
- 제안 API: `POST /api/export/v1/exports {format: "xlsx", base_file_id, document: {sheets: [...]}, form?: {row_map, column_map, unmatched_rows, extra_sheets}, fills?}`
  - `spec.template_map.v1` 결과(양식 행 ↔ 시트 행, 양식 열 ↔ 제품)는 `form.row_map{row_key 또는 행 이름: 양식 행 번호}` · `form.column_map{열 key: 'D'}`
    (또는 행 dict 의 `_form_row`)로 넘기면 이름 맞추기보다 먼저 쓴다. 칸을 직접 정하려면 `fills: [{cell: 'D7', value, note?}]`(note → 셀 메모 = 변환 원래 값).
  - 「시트에만 있는 행 → 양식 아래 추가 항목」(§4.18 제안)은 `form.unmatched_rows: "append"`, 시트 2 「Notes & Sources」를 함께 넣으려면 `form.extra_sheets: "append"`.
  - 응답 `form_fill`(201 · `GET /v1/exports/{id}` · 잡 결과): `filled` · `unmatched_rows`(후보 포함) · `form_only_rows`(§4.18 `template:*` 행 후보) · `skipped` · `lost` + 한국어 `warnings`.
    기밀 · project_id 는 양식 파일에서 이어받는다(양식이 confidential 이면 결과도). .xls 양식은 LibreOffice 가 있어야 하고 잡(202)으로 돈다.
- 상태: 요청(export → spec 안내) — PDF · PPT 는 지금처럼 우리 디자인에 양식 순서만.

## 통합 세션 처리 — integration · 2026-10-07
- 제안서를 지워도 Spec 연결(slk_) · `제안서와 다름` 경고 · 시트 `target_proposal` 이 남아 지운 제안서로 알림이 가던 것: 완료 —
  새 internal `DELETE /v1/links?proposal_id=` → `{proposal_id, deleted, sheet_ids}`(연결 지움 · 그 연결의 `value_mismatch_proposal` 경고 dismissed · 보낼 제안서 비움).
  proposal 이 제안서를 지울 때 부른다. 테스트 `test_warnings.py::test_release_links_when_proposal_deleted`(pytest 56), 계약 갱신.
- 참고: BE6 「Spec 시작」은 `/spec/new?models=…&from=birdseye:{id}`, MI3V 는 `from=mi:{id}` 로 들어온다(origin 기록 확인 — 통합 e2e).
- 보충(integration): `DELETE /v1/links?proposal_id=&sheet_id=` — `sheet_id` 를 주면 그 시트 연결만(제안서에서 Spec 반입을 실행 취소할 때). proposal 은 같은 시트를 쓰는 다른 반입이 없을 때만 부른다.
