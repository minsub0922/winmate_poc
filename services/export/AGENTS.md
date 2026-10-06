# export 서비스 — 개발 세션 규칙

내보내기 — PPTX · XLSX · DOCX · PDF · ZIP 생성, 시트 템플릿 카탈로그

- 포트: **5060** · 게이트웨이 경로: `/api/export/v1/...` · 파이썬 모듈: `winmate_export`
- 고칠 수 있는 경로(owns): `services/export/**`
- 호출할 수 있는 서비스(consumes): `files`, `kb`

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=export          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=export         # 이 서비스 테스트
make contracts SERVICE=export    # contracts/export.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("export", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("export")`(data/export/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=export` 를 돌리고 `contracts/export.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태 (2026-10-07)

### 구조
```
src/winmate_export/
  api.py            # /v1 라우트(계약 원천)          service.py   # 요청 검증 · 미리 받기 · 만들기 · files 저장 · 기록(DocStore)
  worker.py         # 잡 export · render(+ noop)
  templates/        # 카탈로그: catalog.json(생성물) · build.py(원본 → json · CATALOG.md) · archetypes.py(레이아웃 190종 매개변수)
                    #   geometry.py(1280×720 좌표 · 머리/바닥 틀) · registry_data.py(코드 → 원형 · 업종 · 솔루션) · samples.py(칸 값 예시)
  render/           # pptx_render.py(DeckRenderer) · pptx_draw.py(도형 · 글 · 표 · 차트) · textfit.py(맞춤) · values.py(언어 · 표시)
                    #   theme.py(색 · 마스터 프리셋) · thumbs.py(썸네일) · xlsx_render(우리 디자인 표 · render_sheet) · docx_render
                    #   pdf_render(reportlab) · zip_build · soffice(변환 · 상태 status() · 글꼴 font_status())
                    #   xlsx_form.py(고객사 XLSX 양식 채우기 — 맞추기 · 쓰기 규칙은 이 파일 머리 문서가 원본)
```
- 카탈로그 원본: `docs/templates/source/{common,mi,vp,ss,pi}/`(claude.ai Design 캔버스 5개 사본, `SOURCE.json` 에 버전) → `python -m winmate_export.templates.build`
  (`--check` 는 테스트가 돌린다). 사람이 읽는 목록은 `docs/templates/CATALOG.md`.
- 레이아웃은 보드 HTML 을 그대로 옮기지 않고 **원형(archetype) + 매개변수**로 다시 그렸다(좌표는 보드에서 잰 값). 업종판(MI-FB-A 등)은 같은 원형을 쓴다.

### API (`/api/export/v1/...`)
| 메서드 · 경로 | 설명 |
|---|---|
| `GET /templates?role=&section=&industry=&proposal_type=&q=&solution=&kind=&status=&codes=&include_slots=&limit=&cursor=` | `{items: TemplateSummary[], next_cursor, total}` — 업종을 주면 그 업종판 + 범용(업종판이 앞). `codes` 는 표시 코드(VP-F·3) · 별칭(VP-F) 도 된다. `slot_schema: {slots: [{id, type, box, capacity}]}` 기본 포함 |
| `GET /templates/stats` | `{total, ready, industry, dedicated, by_role, by_section, by_kind, by_status, catalog_version}` |
| `GET /templates/{code}?n=` | 칸(slots) · 상자(boxes, 0..1) · 원본 보드 · `example_slots`(칸 값 모양 예시). 별칭은 `n`(항목 수)으로 고른다. `slots[].default` 는 글 · 목록(표 머리 등 count 칸) · 숫자, 보드 없는(제작 중) 템플릿은 `source.board` 없음 + `note` |
| `GET /templates/{code}/thumbnail.png?w=&brand=` | Pillow 와이어프레임, 기본 120×68(`w` 60–1280, 16:9). ETag · 메모리 캐시 |
| `POST /exports` | 빠르면 **201** `{export_id, status:"done", file:{id,name,mime,size,url}, files[], template_codes, slide_count, warnings}` · 느리면 **202** `{export_id, job_id, status:"queued"}`(잡 `export`, 결과 `{export_id, file_id, files}`) |
| `GET /exports?project_id=&source_ref=` · `GET /exports/{export_id}` | 기록(queued · running · done · failed, 파일 · 경고 · 오류) |
| `POST /renders` | 202 `{render_id, job_id}` — 슬라이드 PNG(잡 `render`). 원본 `file_id`(PDF 는 바로, PPTX 는 LibreOffice) 또는 덱 `document`. `sheet_ids` 로 골라 받기 |
| `GET /renders/{render_id}` | `{status, pages: [{index, sheet_id, file_id, png_file_id, url}]}` |
| `GET /masters` · `POST /masters {file_id, name?}` | 기본 3(samsung_b2b · retail_fnb · simple_white) + 올린 .potx/.pptx(`mst_…`, 레이아웃 · 비율 검사) |
| `GET /info` | `pdf_converter` · `pdf_converter_reason`(env · off · missing · unset) · `pdf_converter_detected`(이 서버의 soffice) · `pdf_font`({family, resolved, ok}) · `features`(["form_fill"]) |

- 느린 것 = LibreOffice 가 필요한 것 · 슬라이드 `EXPORT_SYNC_MAX_SLIDES`(기본 40) 초과 · ZIP 항목 `EXPORT_SYNC_MAX_ZIP`(40) 초과 · `async: true`.
- LibreOffice 는 `SOFFICE_PATH`(경로 · PATH 의 이름 · `off`)가 있을 때만 쓴다 — **비우면 끔**(files 와 달리 PATH 에서 스스로 찾지 않는다:
  무거운 변환을 설정 없이 켜지 않고, 다른 서비스 테스트가 이 501 을 기대). 없으면 PPTX → PDF · `from_file_id` PDF · PPTX 렌더 · 옛 형식(.xls) 양식이
  **501 `PDF_CONVERTER_UNAVAILABLE`** — 메시지 · `details{reason, fix, detected?, value?}` 가 왜(off · 경로 없음 · 비어 있음)와 고칠 방법(이 서버에서 찾은
  soffice 경로 · 설치 명령)을 알려 준다. 우리 덱을 PDF · 그림으로 만들 때 fontconfig 가 Noto Sans KR 을 다른 글꼴로 고르면 경고(`soffice.font_warning`).
- 오류: `TEMPLATE_NOT_FOUND`(details.codes) · `TEMPLATE_REQUIRED` · `VALIDATION_FAILED` · `INVALID_DOCUMENT` · `FILE_NOT_FOUND` · `MASTER_NOT_FOUND` ·
  `INVALID_MASTER` · `INVALID_BASE_FILE`(양식이 엑셀이 아님 · 깨짐 · 암호) · `CONVERSION_FAILED`(502) · `EXPORT_FAILED`(500).
- 출력은 `platform.save_file(…, source="export", confidential, project_id, meta={export_id, format, language, template_codes, source_ref})`.

### 요청 · 문서 모양 (`POST /v1/exports`)
요청: `{format: pptx|xlsx|docx|pdf|zip, filename?, document? | document_file_id?(files 의 JSON) | from_file_id?(pdf 변환), design?, master_id?,
language|lang?: ko|en|both|ko_en, bilingual?: files|slides|inline, tbd_mode?: keep_marks|move_to_notes, tbd_label?, confidential=false, project_id?, source_ref?, async?}`
- **pptx(· pdf 덱)**: `{title?, footer?, cover?: {title, subtitle, customer, date, presenter, image}, design?, lang?, tbd_label?,
  slides: [{template_code?, kind?: cover|toc|divider|sheet|closing|appendix, slots | content, notes?, sources | footnotes?: [{label, url?}], confirm?: [str], sheet_id?}]}`
  — `ProposalRenderDoc v1` 을 그대로 받는다. `kind` 만 있으면 기본 템플릿(C01 · C04 · C05 · C07 · AX-B). `cover` 가 있고 표지 슬라이드가 없으면 표지를 앞에 넣는다
  (그림 있으면 C01, retail_fnb 는 C02, 없으면 C03).
  - 칸 값: text 는 문자열 또는 `{ko, en}` · bullets 는 목록 · kpi 는 `{value, unit, label, sub?, delta?, pre?, bar?}` · image 는 `file_id` 또는
    `{file_id, fit?: cover|contain, focus?: [x, y], credit?, ai_generated?}` · table 은 `{columns, rows, col_widths?, highlight_col?, highlight_rows?}` ·
    chart 는 `{type: bar|hbar|line|stacked|stacked100|pie|doughnut|radar|area|scatter|bubble, categories, series: [{name, values}], unit?, title?}` ·
    card 는 필드 dict 목록(템플릿 `fields`). 템플릿에 없는 칸 · 빈 필수 칸은 `warnings` 로 알린다.
  - design: `{brand_hex?(기본 #1428a0), master_id?, master_file_id?(.potx/.pptx — 빈 · 첫 레이아웃 위에 그림), logo_file_id?, cover_image_file_id?, cover_template?, page_numbers?}`
- **xlsx**: `{sheets: [{name, title?, subtitle?, columns: [{key, label, width?, format?: text|int|number|percent|currency|date|엑셀 서식, align?, wrap?}],
  rows: [{key: 값|{value, bold?, fill?, color?, comment?, format?, link?}} | [값…]], freeze?(기본 머리 행 아래), merges?, notes?, header_style?, sources?, highlight_rows?, group_rows?, autofilter?, orientation?}]}`
- **xlsx + 고객사 양식**(`base_file_id` · 다른 이름 `customer_template_file_id` — .xlsx · .xlsm · .xltx · .xltm, .xls · .ods · .xlsb 는 LibreOffice 로 .xlsx 로 바꿔
  잡 202): 고객 파일 **사본의 칸에 값만** 쓴다(서식 · 병합 · 수식 · 열 너비 · 인쇄 · 유효성 · 그림 · 차트 유지, 열 때 재계산). 입력은 둘 중 하나 이상:
  - `document.sheets[]`(위 xlsx 표 문서 그대로) — 행 이름(글이 든 첫 열 · `form.label_key`) × 열 머리(`columns[].label`, {ko, en} 둘 다)로 칸을 찾는다.
    시트 짝: `sheets[i].form.sheet` → 이름이 같은 양식 시트 → 첫 문서 시트는 첫 보이는 시트. 행 dict 의 `_form_row`(번호) · `_form_label`, 열의 `form_column` 힌트.
  - `fills: [{sheet?, cell? | row?, column?, value, note?}]` — `cell`(D7 · 'Sheet'!D7) · `row`(번호 | 이름) · `column`(번호 | 머리 글 | 열 글자), column 없으면 이름 칸 오른쪽.
  - `form`: `sheet · header_row · label_column · label_key · column_map{열 key: 'D'|4|'머리 글'} · row_map{행 이름 · _key: 7|'양식 이름'} ·
    orientation(auto|rows|columns) · overwrite(empty|always) · overwrite_formulas · fuzzy · unmatched_rows(report|append) · extra_sheets(drop|append) · highlight_marks`.
  - 맞추기(결정적, 모델 호출 없음): exact → normalized(번호 매김 · 기호 · 공백) → base(괄호 · 대괄호 단위) → fuzzy(0.88 · 유일할 때). 통째 exact 가 아닌 단계에서
    서로 다른 양식 이름 여럿이 맞으면 고르지 않고 후보로 보고. 머리 행 = 열 이름이 가장 많이 맞는 행(여러 줄 머리 근처 포함), 같은 이름이 여럿이면 문서 순서대로,
    값 열이 하나뿐이면 빈 열 추론(「제안 · 회신」 우선 · 「비고」 제외), 방향 auto(제품이 행인 견적서면 돌려 맞춤). 수식 칸 이름은 저장된 계산값으로.
  - 쓰기: 같은 행 병합은 머리칸으로(다른 행 병합 · 수식 · 보호 잠김 칸은 건너뜀), 이름으로 맞춘 칸은 비었거나 자리표시일 때만(fills 의 주소 · 번호는 덮음),
    숫자 모양 글은 숫자로(텍스트 서식 · 0 시작 제외), '=' 글은 글로, 새 칸은 행 · 열 서식 상속, [확인 필요] 노란 칠, note → 셀 메모, 목록 유효성 밖 값은 알림.
  - 결과(201 · 레코드 · 잡 결과)에 `form_fill`: `{base_file_id, base_name, converted_from?, filled, sheets[{sheet, orientation, header_row, label_column,
    columns[{key, label, column, match}], rows_matched, cells}], cells[{cell, match, row_label, column_label, redirected_from?, replaced?, warning?, outside?}],
    unmatched_rows · unmatched_columns(candidates?) · unmatched_sheets · skipped[{cell, reason, current?}] · form_only_rows · appended_rows · appended_sheets ·
    lost[{part, name, base, output}]}` + 한국어 `warnings`. 기밀 · project_id 는 원본 양식에서 이어받고, 파일 이름 기본은 `{양식 이름}_작성`(en `_filled`),
    매크로 양식은 `.xlsm` 으로 낸다. 파일 메타에 `base_file_id`.
- **docx · pdf 보고서**: `{title, subtitle?, meta?, sections: [{heading, level?, paragraphs?, bullets?, numbered?, table?, images?: [file_id | {file_id, caption?, width_cm?}],
  captions?, sources?, page_break?}], page_size?: A4|Letter, orientation?}` — pdf 는 `{report: …}` 로 감싸도 된다(reportlab CID 글꼴 HYGothic-Medium · HYSMyeongJo-Medium, `EXPORT_PDF_TTF` 로 TTF 넣기).
- **zip**: `{entries: [{file_id, path} | {path, text} | {path, json} | {path, format: xlsx|docx|pdf|pptx, document}]}` — 상대 경로만, 겹치면 ` (2)`.
- 언어: `en` 은 `[확인 필요]` · `[확정 필요]` → `[TBD]`(tbd_label), `[추정]` → `[Est.]`, 칸 글자 수 1.8배까지. `both` 기본은 파일 두 개(`_KO` · `_EN`, 10-proposal §7.12).
- XLSX 칸 · 메모 · 시트 이름의 제어 문자(모델 · PDF 추출 글)는 빼고 넣는다(`values.excel_text`, 칸 한도 32,767자) — 전에는 openpyxl 오류로 500.
- 표시: `[확인 필요]` · `[00]` 같은 대괄호 자리표시는 노란 형광 + 굵게(PPTX · DOCX · XLSX · PDF). `tbd_mode=move_to_notes` 면 칸은 「—」, 문장은 발표자 노트.
- 이미지: 상자에 맞춰 잘라(cover) 넣고(C · E 등급은 contain), 2400px 넘으면 줄인다. 파일 메타가 생성 이미지(`is_generated` · `ai_generated` · `rights: generated`)면
  오른쪽 아래에 「AI 생성 이미지」 칩. 슬라이드마다 출처 줄(출처 상자가 없는 표지 · 간지는 노트로). 글은 크기 단계(1.0 → 0.66) 후 말줄임.

### 템플릿 카탈로그 요약 — 430종(ready 381 · 제작 중 48 · 내부 1), 원본 캔버스 5개
- Market Intelligence: MS 21 · TR 3 · CB 20 · US 19 · CP 3 · IM 2
- Value Props: CH 19 · VP 46 · EF 21 (업종 VP 묶음 48장은 보드가 없어 `in_production`)
- 조감도: BV 4 · ZP 4 · IS 2 · GN 4 · MB 2 / 공간별 제품: SM 5 · PI 36 · BM 5
- 솔루션 제안: SA 4 · OP 19 · SF 5 · SXI 11 · SXD 11 · SXS 32 / 공간 시나리오: VM 20 · SS 71 · UX 3
- 사례 CD 4 · CL 4 / Why Samsung CM 3 · ST 4 · SV 3 / 스펙 SC 3 · SD 3 / 공통 COVER 5 · TOC 2 · DIVIDER 3 · CLOSING 2 / 부록 AX 2
- 종류: common 12 · generic 165 · industry 179 · product 20 · dedicated 33 · industry_solution 21. 업종 16(winmate16) + 솔루션 업종판.

### 알려진 빈 곳
- 업종판은 범용과 같은 원형을 쓴다(업종별 고유 기하는 아님). 보드 JS 계산 레이아웃 일부는 근사.
- 글꼴: 'Noto Sans KR'(숫자 글꼴 Manrope 대신 같은 글꼴). 보는 PC 에 없으면 PowerPoint 가 맑은 고딕 등으로 바꿔 줄바꿈이 조금 달라질 수 있다(폭 6% 여유).
- LibreOffice 가 없으면 덱 PDF · 렌더 불가(501). SVG 로고는 그리지 않는다(경고) — `docs/requests/platform.md`.
- 16:9 가 아닌 마스터는 좌표가 늘어난다(등록 시 경고). 차트는 python-pptx 기본 차트(막대 · 선 · 원 등)만.
- workspace 색인(register_item)은 하지 않는다 — 내보내기는 다른 기능 자원의 파생물(파일은 files 에 남는다).
- 고객사 양식: openpyxl 이 다시 쓰지 못하는 요소(도형 · 글상자 · 양식 컨트롤 · 머리글/바닥글 그림 · x14 확장 유효성/조건부 서식 · 스파크라인 · 슬라이서 ·
  스레드 댓글 · 셀 안 그림)는 잃는다 — 저장 전후 부품 수를 비교해 `form_fill.lost` · 경고로 알린다(몰래 잃지 않음). 더 엄격히 지켜야 하면 시트 XML 직접 수정 방식으로.
  이름 맞추기는 결정적 규칙뿐 — 의미가 같은 다른 말(「휘도」 ↔ 「밝기」)은 부르는 쪽(spec 의 `spec.template_map.v1`)이 `row_map` · `column_map` · `_form_row` 로 준다.
  이름을 찾는 범위는 시트 앞 5000행 · 200열. 행을 양식 중간에 끼워 넣지 않는다(append 는 맨 아래).
- 테스트: `make test SERVICE=export` — 75개(+ LibreOffice 경로 3개는 `SOFFICE_PATH` 있을 때만: 덱 PDF · 덱 렌더 · 옛 형식 .xls 양식).
  `test_api.py::test_get_template_every_catalog_code` 가 카탈로그 전 코드(표시 코드 · 별칭 n 포함)를 상세 API 로 돌린다(응답 모델 ↔ 카탈로그 데이터 회귀 방지).
  `test_xlsx_form.py` 25개(맞추기 · 쓰기 · 보존 · API).
