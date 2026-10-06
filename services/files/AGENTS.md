# files 서비스 — 개발 세션 규칙

파일 — 업로드 · 저장 · 문서 파싱(PPTX·PDF·DOCX·XLSX·TXT·메일·HEIC) · 미리보기

- 포트: **5030** · 게이트웨이 경로: `/api/files/v1/...` · 파이썬 모듈: `winmate_files`
- 고칠 수 있는 경로(owns): `services/files/**`
- 호출할 수 있는 서비스(consumes): 없음

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=files          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=files         # 이 서비스 테스트
make contracts SERVICE=files    # contracts/files.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("files", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("files")`(data/files/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=files` 를 돌리고 `contracts/files.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태 (2026-10-06)

### API (`/api/files/v1/...`, 계약 `contracts/files.json`)
| 메서드 · 경로 | 내용 |
|---|---|
| `POST /v1/files` | multipart `file` + `confidential` · `project_id` · `purpose` · `source`(기본 upload) · `parent_id` · `folder` → 201 FileMeta. 올리자마자 백그라운드 파싱(`parse_status` pending → parsing → done/failed) |
| `POST /v1/files/bytes` | **internal**. JSON `{name, mime, data_b64, source, confidential, project_id?, meta?, parent_id?, purpose?, folder?}` → 201. `parent_id` 를 주면 confidential(OR) · project_id 를 이어받는다. 파싱은 요청할 때 |
| `GET /v1/files` | `owner=me\|all\|<id>` · `project_id` · `source` · `kind`(쉼표 여러 개) · `q`(이름) · `parent_id` · `purpose` · `folder` · `include_children` · `limit≤200` · `cursor`, 최신순. 기본은 원본만(자식 제외). 남의 기밀 파일은 `project_id` 로 거를 때만 보인다 |
| `GET /v1/files/{id}` | FileMeta. pending/parsing 인데 이 프로세스에서 돌지 않으면(재시작) 다시 시작 |
| `PATCH /v1/files/{id}` | `name · confidential · project_id · meta(얕은 병합, null=키 삭제) · purpose · folder`. 올린 사람만(403). confidential 은 자식(derived)에 전파 |
| `DELETE /v1/files/{id}` | 204 소프트 삭제(데이터 `deleted` 표시 → DocStore 삭제). 같은 sha256 을 쓰는 레코드가 없으면 blob · 캐시 삭제. 자식은 지우지 않는다(제안서 등이 쓰고 있을 수 있음) |
| `GET …/content?download=1` | Range · ETag(sha256) · `filename*=UTF-8''…`(RFC 5987) + ASCII 대체 이름. HTML/XML 은 attachment + CSP sandbox, SVG 는 CSP |
| `GET …/thumbnail?w=320&format=webp\|png` | 이미지 축소 · PDF/PPTX/DOCX/XLSX 첫 쪽(LibreOffice) · PPTX 자리표시 카드 · 형식 아이콘(PNG). 디스크 캐시 |
| `GET …/parsed` | ParsedDocument. 처음이면 끝날 때까지 기다린다. 415 `UNSUPPORTED_MEDIA_TYPE` · 422 `PARSE_FAILED` · `FILE_ENCRYPTED` · `FILE_TOO_COMPLEX` · `CONVERSION_FAILED` |
| `POST …/parse?force=` | 202 `{file_id, parse_status, parser_version}` (proposal F3) |
| `GET …/pages/{n}/image?w=1280&format=png` | PDF · PPTX/DOCX/XLSX/옛 형식(LibreOffice → PDF 캐시) · 이미지(n=1, 다중 프레임은 n). 렌더러 없으면 501 `PREVIEW_UNAVAILABLE`, 범위 밖 404 `PAGE_NOT_FOUND` |
| `GET …/pages/{n}/thumbnail?w=320` | 쪽 썸네일(proposal F4). 렌더러가 없으면 PPTX 는 그 슬라이드 자리표시 카드, 그 밖은 아이콘 |
| `POST …/copy` | `{folder?, project_id?, name?}` → 201 사본(같은 blob, `meta.copied_from`) — PR7X 팀 공유 폴더(F6) |

- 지시서 FileMeta 에 더한 필드: `updated_at · purpose · folder · doc_props{author,title,subject,created,modified,last_modified_by,producer,company} · parse_status(none\|pending\|parsing\|done\|failed\|unsupported) · parse_error`.
- ParsedDocument 에 더한 필드: page `title · images[{file_id,bbox}] · hidden · section · size[pt]`, block `font_size · line · file_id`, sheet `merged · hidden · row_count · truncated`, email `attachment_list`, meta `outline`(PDF 북마크) · `format` · `parsed_as`. proposal 의 `layout_name` = `layout`, `kind` = block `type`.

### 형식
| kind | 파싱 |
|---|---|
| pdf | pypdfium2(쪽 글자 · 속성 · 목차 · 그림 추출 · 글자 층 없는 쪽 `scanned_page:n`) + pdfplumber(단어 → 줄 → 블록, XY-cut 순서, 글자 크기 → heading level, 선 있는 표). 300쪽 넘는 부분 · 깨진 글꼴 쪽은 pypdfium2 줄 블록(`layout_skipped_after` · `layout_fallback:n`), 객체 2만 넘는 도면 쪽은 `layout_skipped:n:complex` |
| pptx(.potx .ppsx .pptm) | 제목 · 부제 · 본문/목록 · 표 · 차트 데이터(표) · SmartArt 글자 · 그림(자식) · 노트 · 레이아웃 · 숨김 · 구역, 그룹 도형 좌표 변환. EMF/WMF 그림은 건너뜀 |
| docx(.dotx .docm) | 제목 수준(스타일 · 개요 수준) · 목록 · 캡션 · 표(gridSpan/vMerge) · 글상자 · 그림(자식). 쪽 = 명시적 쪽 나눔 + `w:lastRenderedPageBreak` |
| xlsx(.xlsm .xltx) | read_only + data_only, 시트당 2000행 · 256열, A1 위치 유지, 병합 범위, 숨김 시트. 시트 = 쪽 |
| text | txt · md · csv/tsv(→ sheets) · json · xml · yaml · html. 인코딩 utf-8(BOM)/cp949(euc-kr)/utf-16. 블록에 시작 줄 번호. 5만 자마다 쪽 |
| email | .eml(표준 라이브러리) · .msg(Outlook, 자체 OLE 판독기 `cfb.py`). 머리 디코딩, text/plain 우선(없으면 HTML → 글). 첨부 = 자식, cid 그림은 inline. base64 로 감싼 message/rfc822 도 푼다 |
| image | PNG · JPEG · GIF · WEBP · BMP · TIFF · AVIF · **HEIC/HEIF → JPEG 변환**(`meta.original_mime/name/size`). 가로세로 · 썸네일은 EXIF 회전 반영(원본 바이트는 그대로), `meta.exif{orientation,make,model,taken_at}` |
| svg | 크기 · 글자. 썸네일은 LibreOffice 있으면 그림, 없으면 아이콘 |
| other | hwpx(글자), LibreOffice 있으면 .doc/.ppt/.xls/.odt/.odp/.ods/.rtf(→ OOXML 로 바꿔 파싱) · .hwp(→ PDF 시도). 그 밖 `unsupported` |
| zip | 목록만(풀지 않음) |

### 자식 파일(추출 이미지 · 메일 첨부)
- `source=derived` · `parent_id` · confidential/project_id/owner 를 원본에서 이어받음 · `meta.depth=1` · `meta.child_key`(sha256) · `meta.pages`.
- 같은 내용은 한 번만(sha256). 자식은 다시 자식을 만들지 않는다(깊이 1, `children_skipped:depth:n`). 자식 파싱은 요청할 때.
- 파싱은 내용(sha256) 기준 한 번 + 레코드마다 자식 레코드를 만들어 ref → file id (같은 파일을 두 사람이 올려도 자식은 각자).

### 저장 · 캐시
- blob `data/files/blobs/<sha[:2]>/<sha256>`, 메타 DocStore `files`(keep_history=False, 인덱스 owner · sha256 · parent_id · project_id · kind · folder).
- `data/files/cache/`: `parsed/<sha>.v<PARSER_VERSION>[.nochild].json`(내용) · `parsed/<sha>.v<ver>.<file_id>.json`(레코드) · `thumbs/` · `pages/` · `soffice/`(PDF 변환, 실패는 1시간 `.fail`, `_profiles/`) · `icons/`. `settings.PARSER_VERSION` 을 올리면 다시 읽는다.
- PDFium 은 스레드 안전하지 않아 모든 호출을 `pdfium.LOCK` 안에서(파싱은 쪽마다 잠금).

### 한도 · 설정(환경 변수)
- `UPLOAD_MAX_MB`(공통, 기본 50) → 413 `PAYLOAD_TOO_LARGE`(Content-Length 로 먼저 거르고 본문은 버린다. 게이트웨이도 50MB 한도).
- `FILES_PARSE_CONCURRENCY=2` · `FILES_PDF_LAYOUT_MAX_PAGES=300` · `FILES_MAX_CHILDREN=300` · 압축 해제 합계 400MB(`FILE_TOO_COMPLEX`).
- `SOFFICE_PATH=경로|off`(없으면 PATH · `/Applications/LibreOffice.app` 자동) · `SOFFICE_TIMEOUT_S=180` · `SOFFICE_CONCURRENCY=1` · `FILES_FONT_PATH`(카드 · 아이콘 글꼴, 없으면 Noto CJK · Nanum · `fc-match :lang=ko`).

### LibreOffice
- 있으면: PPTX/DOCX/XLSX 썸네일 · 쪽 그림(PDF 변환 캐시, 숨긴 슬라이드도 내보내 슬라이드 n = 쪽 n), 옛 형식 파싱. 변환 한 번 1.5~2초.
- 없으면: PPTX 썸네일 · 쪽 썸네일은 자리표시 카드(제목 · 본문 몇 줄 · 그림 자리), 쪽 그림 501, DOCX/XLSX 썸네일은 형식 아이콘.
- 이 개발 컨테이너에는 `/usr/bin/soffice`(24.2)가 있어 자동으로 쓴다. 테스트: LibreOffice 테스트(3개)는 없으면 건너뛰고, 나머지는 `SOFFICE_PATH=off`.
- 실행마다 프로필 폴더 분리, 출력은 파일로, 끝나면 프로세스 묶음(oosplash → soffice.bin)을 정리한다.

### 알려진 한계 · 남은 일
- HWP 5(.hwp)는 기본 LibreOffice 로는 대개 못 읽는다(`CONVERSION_FAILED`). HWPX 는 글자만.
- .msg 의 RTF 전용 본문 · 메일 안 .msg 첨부는 건너뜀(warnings). DOCX 머리글 · 바닥글 · 각주는 읽지 않음.
- PDF 읽는 순서는 XY-cut 근사, 표는 선 있는 표만. 스캔 쪽 OCR 은 호출 측(ai-tools i2t + `pages/{n}/image`).
- XLSX 수식 값은 파일에 저장된 계산값(엑셀이 저장하지 않은 파일은 비어 있음).
- 기밀 접근: 목록에서 남의 기밀 숨김 + 수정 · 삭제는 올린 사람만. 프로젝트 구성원 검사(F7)는 workspace 계약이 필요(consumes 없음).
- KB 이미지 저장본(G-IMG-2) · QR 모바일 업로드 토큰 인증은 kb · 게이트웨이 쪽 결정 필요 — files 는 게이트웨이가 넘긴 `X-User-Id` 를 owner 로 쓴다.
- 백그라운드 파싱은 API 프로세스 안(asyncio + 스레드)이라 재시작 시 끊기지만, 조회 · 파싱 요청 때 다시 시작한다.

### 테스트
- `make test SERVICE=files`(47개, 약 12초). 샘플은 `tests/files_samples.py` 가 코드로 만든다(한글 PDF · PPTX · DOCX · XLSX · EML · MSG(OLE 직접 작성) · HEIC · EXIF 회전 JPEG · HWPX · cp949).
- 계약 검증(strict)으로 `winmate_common.platform` 의 save_file · file_meta · file_bytes · parsed_document 를 확인한다.
