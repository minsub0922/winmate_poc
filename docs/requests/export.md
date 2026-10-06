
## XLSX 를 고객사 양식 파일 그대로 채우기 — spec · 2026-10-06
- 필요: 06-spec §4.18 — 고객사 양식(XLSX)을 올리면 "XLSX 내보내기는 고객사 파일을 바탕으로 같은 칸에 값을 써 넣는다(서식 유지)".
  지금 export 계약은 우리 디자인 문서(document)만 받아 새 파일을 만들어서, spec 은 양식의 행 순서 · 행 이름만 반영한 우리 디자인 XLSX 를 낸다.
- 제안 API: `POST /v1/exports` 에 `format: 'xlsx'` + `base_file_id`(고객사 XLSX, 기밀 상속) + `fills: [{sheet: string|null, cell: 'B3', value: string, note?: string}]`
  — 서식 · 병합 · 열 너비를 유지하고 지정 칸만 쓴 사본을 files 에 저장. 칸이 시트 범위 밖이거나 병합 칸 안쪽이면 `warnings[]`.
- 상태: 요청

## `GET /v1/templates/{code}` 가 135종에서 500(ResponseValidationError) — proposal · 2026-10-07
- 현상: 카탈로그 429종 중 135종(예 `CB-B` `CB-D` `IM-A` `US-B` `US-C` `CH-B` `CH-C` `EF-A` `EF-C` · 업종판 `MI-FB-A` `MI-FB-C` `VP-FB-A` `VP-FB-C` …)의 상세가
  `500 INTERNAL {details.type: ResponseValidationError}`. 로그: `('response', 'slots', 7, 'default') Input should be a valid string — input: ['운영 영역', '지금', '바라는 모습']`
  → `Slot.default` 가 `str | None` 인데 표 머리글 같은 칸은 목록 기본값을 갖는다.
- 필요: `Slot.default`(· `default_en`) 를 `str | list[str] | None` 으로(또는 목록이면 `" · "` 로 합쳐) — 상세 응답이 모든 코드에서 200.
- 왜: proposal 은 시트 칸 채우기에 상세의 `slot_schema` 를 쓴다(§7.5 · §8.12). 지금은 목록 `GET /v1/templates?codes={code}&include_slots=true` 로 우회 중(그 경로는 정상).
- 상태: 요청
- 상태: 완료(export · 2026-10-07) — 원인: 응답 모델이 카탈로그 데이터보다 좁았다. ① `Slot.default/default_en: str | None` 인데 count 글 칸(표 머리 `headers` ·
  `axes` · `row_labels` · `labels`)은 항목별 **목록**, `GN-*.recommended` 는 **숫자** 기본값(112칸) ② 보드 없는(제작 중) 업종 VP 48종(`VP-<업종>-A..C`)은
  `source.board/title/path` 가 null 인데 `board: str` 필수. 목록 API 는 slots · source 를 싣지 않아 멀쩡했다. 실제로 깨진 것은 128종(표시 코드까지 130건).
  고침: `default · default_en: str | int | float | list[str] | null`(목록은 합치지 않고 그대로), `source.board` 선택(보드 없으면 빠지고 `note` 에 사유,
  title · path 는 ""). 깨지는 변경 없음(응답 타입 넓힘 — 웹 타입은 `board?` 만 바뀜). 테스트 `test_get_template_every_catalog_code` 가 카탈로그 전 코드 ·
  표시 코드 · 별칭(n 마다)을 상세 API 로 돌려 slots · boxes · source 가 카탈로그 그대로인지 본다. 반영: `pm2 restart export` 뒤 목록 우회
  (`GET /v1/templates?codes=…&include_slots=true`)는 없애도 된다.

## ↑ 「XLSX 를 고객사 양식 파일 그대로 채우기 — spec · 2026-10-06」 답 — export · 2026-10-07
- 상태: 완료 — `POST /v1/exports {format: "xlsx", base_file_id(= customer_template_file_id), document?, fills?, form?}` (덧붙인 필드만, 깨지는 변경 없음).
  고객 파일 **사본의 칸에 값만** 쓰고 서식 · 병합 · 수식 · 열 너비 · 인쇄 설정 · 유효성 · 그림 · 차트는 그대로(열 때 재계산). 기밀 · project_id 는 원본 양식에서 이어받는다.
  - 요청하신 `fills: [{sheet?, cell, value, note?}]` 그대로 된다(note → 셀 메모). 더해 `cell` 대신 `row`(행 번호 | 양식 행 이름) · `column`(열 번호 | 머리 글 | 열 글자)로도
    지정, column 이 없으면 이름 칸 바로 오른쪽.
  - 또는 지금 보내는 **우리 표 문서(document.sheets) 그대로** + `base_file_id` — export 가 행 이름 × 열 머리로 양식 칸을 찾는다(단위 괄호 · 번호 매김 · 공백 ·
    「밝기 / Brightness」 두 언어 · 오타 수준까지, 결정적). 제품이 행인 양식은 돌려 맞추고, 값 열이 하나면 빈 「제안 · 회신」 열을 추론.
    `spec.template_map.v1` 결과는 `form.row_map{시트 행 이름 · row_key: 양식 행 번호}` · `form.column_map{열 key: 'D'}` · 행의 `_form_row` 로 넘기면 그대로 쓴다.
  - 경고 대상: 병합 칸 안쪽 주소는 같은 행이면 병합 머리칸에 쓰고 알림(`redirected_from`), 다른 행 병합 · 수식 · 보호 잠김 칸은 건너뛰고 `skipped[]`,
    양식 범위 밖 칸은 쓰고 `outside` + `warnings[]`.
  - 결과 `form_fill`: 쓴 칸 · 못 맞춘 행/열(후보 포함) · 양식에만 있는 행(`form_only_rows` — §4.18 `template:*` 행 후보) · 건너뛴 칸 · openpyxl 이 유지 못 한 요소(`lost`).
    `form.unmatched_rows: "append"` 면 시트에만 있는 행을 양식 아래 「추가 항목」으로(§4.18 제안), `form.extra_sheets: "append"` 면 「Notes & Sources」 같은 시트를 덧붙임.
  - .xls · .ods 양식은 LibreOffice 로 .xlsx 로 바꿔 잡(202)으로, .xlsm 은 매크로 유지 .xlsm 으로 낸다. 자세한 규칙: `services/export/src/winmate_export/render/xlsx_form.py` 머리 문서 ·
    `contracts/export.json`(FormFill · FormOptions · FormFillReport).
