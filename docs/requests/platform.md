# platform 요청

## 게이트웨이가 바뀐 계약을 다시 읽지 않음(internal 차단이 늦게 걸림) — kb · 2026-10-06
- 필요: 게이트웨이의 `load_contract`(lru_cache)는 계약을 프로세스당 한 번만 읽는다. `make contracts SERVICE=kb` 로 새 `tags=["internal"]` 경로
  (`/v1/query/*` · `/v1/patterns` · `/v1/segments*` · `/v1/spec/*` · `/v1/entities/*` · `/v1/placement-rules` · `/v1/models/{code}/lifecycle`)를 내보내도
  게이트웨이를 다시 시작하기 전에는 브라우저 호출이 막히지 않는다(확인: 2026-10-06 `POST /api/kb/v1/spec/table` 이 로그인 경로로 200).
- 제안: 계약 파일 수정 시각(mtime)이 바뀌면 다시 읽기, 또는 `make contracts` 끝에서 `pm2 restart gateway`.
- 상태: 완료(2026-10-06) — `winmate_common.contracts.load_contract` 가 mtime 이 바뀌면 다시 읽는다(게이트웨이 · ServiceClient 모두).

## ai-tools 선택 의존성 선언 — ai-tools · 2026-10-06
- 필요: `POST /v1/fetch` 가 PDF 를 페이지별 텍스트(`pages[]`)로 돌려주려고 `pypdfium2` 를 있으면 쓴다(지금은 files 서비스 덕분에 같은
  가상환경에 깔려 있어 동작). ai-tools 만 설치하는 환경에서도 같게 하려면 `services/ai-tools/pyproject.toml` 의존성에 `pypdfium2` 를
  넣고 잠금 파일을 갱신해 주세요. 로컬 임베딩(`EMBEDDING_PROVIDER=local`, bge-m3)을 쓸 때가 오면 `sentence-transformers`(+ CPU torch)도
  필요하다 — 지금은 늦게 import 하고 없으면 501 을 돌려준다(기본 `EMBEDDING_PROVIDER=lsa` 라 급하지 않음).
- 제안: `dependencies` 에 `"pypdfium2>=5.14"` 추가(급하지 않음). sentence-transformers 는 사내망 결정 뒤.
- 상태: 완료(2026-10-06) — pypdfium2 선언 · uv.lock 갱신. sentence-transformers 는 보류.

## export — LibreOffice · 글꼴 · SVG 로고(운영 준비) — export · 2026-10-06
- 필요: PPTX → PDF(`POST /v1/exports {format: pdf, document.slides | from_file_id}`)와 슬라이드 PNG(`POST /v1/renders`)는
  LibreOffice 로만 만든다. `SOFFICE_PATH` 가 없으면 501 `PDF_CONVERTER_UNAVAILABLE` 을 돌려준다(보고서형 PDF 는 reportlab 이라 상관없음).
  사내망 PC 에 `libreoffice-impress`(headless)를 깔고 `.env` 에 `SOFFICE_PATH=/usr/bin/soffice` 를 넣어 주세요.
  PDF 글꼴이 맞으려면 서버에 **Noto Sans KR**(또는 fontconfig 별칭 `Noto Sans KR → Noto Sans CJK KR`)이 있어야 한다 — 없으면 줄바꿈이 달라진다.
- SVG 로고: 로고 칸은 PNG · JPEG 만 그린다(SVG 는 경고만 남기고 건너뜀). SVG 를 쓰려면 `cairosvg`(+ libcairo2) 를 export 의존성에 넣어 주세요(급하지 않음).
- 선택: 보고서형 PDF 에 글꼴을 넣어야 하면 `EXPORT_PDF_TTF=/usr/share/fonts/truetype/nanum/NanumGothic.ttf` 처럼 TTF 경로를 주면 된다
  (기본은 reportlab 내장 CID 글꼴 HYGothic-Medium · HYSMyeongJo-Medium — 파일에 글꼴을 넣지 않는다).
- 상태: 운영 문서 반영(2026-10-07, docs/OPERATIONS.md — LibreOffice headless · 글꼴 · 별칭). cairosvg 는 보류.

## files — `save_file` 인자 · LibreOffice · 설정 — files · 2026-10-06
- 필요 1: `winmate_common.platform.save_file()` 에 선택 인자 `parent_id` · `purpose` · `folder` 를 더해 `POST /v1/files/bytes` 로 넘겨 주세요
  (계약은 이미 받는다). 렌디션 · 추출물을 원본에 묶으면 기밀(confidential) · project_id 를 files 가 자동으로 이어받는다.
- 필요 2(운영): files 도 LibreOffice 가 있으면 PPTX/DOCX/XLSX 썸네일 · 쪽 그림과 옛 형식(.doc .ppt .xls) 파싱을 한다. `SOFFICE_PATH` 가
  없으면 PATH 에서 `soffice` 를 찾고(끄려면 `SOFFICE_PATH=off`), 없으면 자리표시 카드 · 501 로 내려간다. 참고: 지시서와 달리 이 개발
  컨테이너에는 `/usr/bin/soffice`(LibreOffice 24.2)가 이미 깔려 있다. `.env` 예시에 선택 설정 `SOFFICE_TIMEOUT_S` · `SOFFICE_CONCURRENCY` ·
  `FILES_PARSE_CONCURRENCY` · `FILES_PDF_LAYOUT_MAX_PAGES` · `FILES_MAX_CHILDREN` · `FILES_FONT_PATH` 를 적어 두면 좋다.
- 선택: 공공 RFP 가 HWP 5(.hwp)면 기본 LibreOffice 로는 못 읽는다 — H2Orestart 확장(.oxt) 설치 또는 HWP 판독 의존성 결정 필요(HWPX 는 files 가 글자를 읽음).
- 상태: 필요 1 완료(2026-10-06, `save_file(parent_id=, purpose=, folder=)`). 필요 2 · 선택은 운영 문서(docs/OPERATIONS.md)에 반영.

## requirements 선택 설정 RQ_FILL_SLOT_DELAY_MS — requirements · 2026-10-06
- 필요: 파일로 폼 채우기(`rq.fill`)는 칸을 하나씩 쓰며 진행(`{a} / {b}`)을 보낸다. 칸 사이 간격(기본 150ms)으로 RQ1G 처럼 차례로 채워지는 모습을 보여 준다.
  테스트는 0 으로 둔다. 운영에서 바꿀 일은 거의 없지만 `.env.example` 선택 설정 목록에 한 줄 있으면 좋다.
- 제안: `# RQ_FILL_SLOT_DELAY_MS=150  # requirements: 파일 채우기 칸 사이 간격(ms), 0 = 바로`
- 상태: 완료(2026-10-07) — `.env.example` §14.

## Storyboard 시연 속도 `SB_PACE_S` · Storyboard 읽기 간선 — storyboard · 2026-10-06
- 필요 1(설정): mock 모델은 너무 빨라 SB3G(목차 만드는 중) · 준비 스켈레톤이 화면에 안 보인다. storyboard 워커는 `MODEL_MODE=mock` 이면 단계마다
  0.45초 쉬고(섹션 하나 · 준비 · 기획 방향 · 공간 다듬기 · 수정 요청 · 정의서 동기화), 실제 모델이면 0 이다. `SB_PACE_S` 로 바꾼다(0 = 끔, 테스트는 0).
  `.env.example` 선택 설정에 한 줄: `# SB_PACE_S=0.45   # storyboard: mock 시연 · e2e 진행 화면 속도(초), 0 = 바로`
- 필요 2(간선, 02-storyboard Q-2 · Q-3): mi · scenario · competitor 는 `consumes` 에 storyboard 가 없어 지금은 **웹이** Storyboard 를 읽어
  넘긴다(`GET /api/storyboard/v1/storyboards/{id}` · `/key-messages`, MI4 근거 → `POST …/key-messages/{kmsg}/evidence`, 경쟁사 → `POST …/imports/competitor`).
  서버끼리 읽게 하려면 `config/services.yaml` 의 mi · scenario(· competitor) `consumes` 에 `storyboard` 를 더해 주세요(vp · proposal 은 이미 있음).
- 상태: 완료(2026-10-07) — `SB_PACE_S` 는 `.env.example` §14, mi · competitor · scenario consumes 에 storyboard(competitor 는 mi 도) 추가.

## ai-tools mock — 입력으로 응답 고르기 — spec · 2026-10-06
- 필요: `mocks/ai-tools/<task>.json` 의 `{"responses": [...]}` 는 호출 순서로 돈다(프로세스 전체 카운터). spec 의 `sp.interpret_request` 는 응답 두 개
  (연간 전기료 행 · QM55R 추가)를 쓰는데, e2e 가 순서를 맞추려고 버리는 호출을 한다(`web/e2e/spec/warnings.spec.ts`).
- 제안: 응답 항목에 `when: {contains: "QM55R"}`(프롬프트 부분 문자열) 또는 `when_hash` 를 두고 맞는 첫 항목을 쓰기(맞는 게 없으면 지금처럼 순환).
- 상태: 완료(2026-10-07) — `when: {contains, not_contains}`(mocks/ai-tools/README.md 「입력으로 고르기」). 조건 항목은 순번을 쓰지 않는다.

## spec 선택 설정 — `.env.example` — spec · 2026-10-06
- 필요: spec 은 아래 값 없이도 돈다(기본값). 운영에서 바꿀 수 있게 `.env.example` 선택 설정 목록에 적어 주세요.
- 제안:
  `# SPEC_CATALOG_ADAPTER=kb            # spec: 사내 카탈로그 어댑터 kb(기본) · fixture(테스트)`
  `# SPEC_ELECTRICITY_KRW_PER_KWH=      # spec: '연간 전기료 (추정)' 파생 행 단가(원/kWh). 비우면 값 확인(계산 기준)으로 묻는다`
  `# SPEC_FIXED_NOW=                    # spec: 고정 시계(테스트 · 시연, ISO 8601)`
- 상태: 완료(2026-10-07) — `.env.example` §14(SPEC_FIXED_NOW 는 시험용 목록).

## 경쟁사 사전 `config/content_policy.yaml` 소유 · 이미지 선택 의존성 — image · 2026-10-06
- 필요 1: 07-image §10.6 의 경쟁사 사전(`competitor_brands` 한 · 영 표기)과 생성 이미지 사용 기준 문구는 법무 확인이 필요한 공용 설정이다.
  image 는 `config/content_policy.yaml` 이 있으면 그것을, 없으면 서비스 안 초안 `services/image/src/winmate_image/data/content_policy.yaml` 을 읽는다.
  초안을 `config/` 로 옮겨 소유 · 승인 절차를 정해 주세요(형식: `competitor_brands: [{name, aliases: []}]`, `person_patterns: []`).
- 필요 2(선택, 급하지 않음): ×4(8K) 업스케일은 `UPSCALER=realesrgan_x4v3` 일 때만 켠다 — `onnxruntime` + realesr-general-x4v3 ONNX(약 5MB, 오프라인 폴더)를
  image 의존성 · 모델 폴더로 넣을지 결정해 주세요(지금은 Lanczos3 + unsharp, ×4 버튼 비활성 「×4는 업스케일 모델이 있어야 해요」).
  OpenCV Telea 인페인트(`opencv-python-headless`)도 있으면 작은 영역 보정에 쓰겠다(지금은 Pillow 확산 인페인트 `edit:local_inpaint`).
- 참고(e2e): 이 컨테이너 Chromium 은 한글 파일명 다운로드의 저장 이름을 만들지 못해 `download` 로 저장한다(서버 `Content-Disposition` 은 `filename*=UTF-8''…` 정상).
  image e2e 는 영문 파일명으로 이름을 확인한다.
- 상태: 필요 1 완료(2026-10-07) — 초안을 `config/content_policy.yaml` 로 옮김(status: draft, 법무 확인은 사용자 결정 사항). 필요 2(×4 업스케일 · OpenCV)는 보류 — 사용자 결정 뒤.

## 셸 HMR 순환 import — 다른 기능 파일 저장 때 열린 화면이 빈 화면 — image · 2026-10-06
- 증상: 같은 작업 트리에서 다른 세션이 기능 파일(예: `src/features/mi/index.tsx`)을 저장하면 Vite HMR 이 `src/shell/catalog.ts:66` 에서
  `ReferenceError: Cannot access 'features' before initialization` 을 내고, 그때 열려 있던 다른 기능 화면이 렌더되지 않는다
  (image e2e 1건이 이걸로 실패, 다시 돌리면 통과).
- 원인 추정: `registry.ts`(기능 index eager glob) → 기능 `index.tsx` → `@/shell`(index.ts) → `catalog.ts` → `registry.ts` 순환에서 `SHELL_FEATURES` 를
  모듈 최상위에서 계산한다.
- 제안: `SHELL_FEATURES` 를 처음 쓸 때 계산(함수 · 지연 getter)하거나, 기능이 쓰는 훅 · 타입만 내보내는 진입점(`@/shell/feature`)을 따로 두어 catalog 를 거치지 않게.
- 상태: 완료(2026-10-07) — `shellFeatures()` 지연 계산(`SHELL_FEATURES` 는 같은 값의 지연 배열). 또 e2e 개발 서버(WM_E2E_DEV)는 HMR · 감시를 끈다.

## mi 간선 — storyboard(선택) · proposal · vp 쪽 consumes 확인 — mi · 2026-10-06
- 필요: mi 는 storyboard 를 consumes 하지 않아 MI1 `Storyboard 가져오기`(요구사항 · Key Message)와 MI4 `Key Message에 근거로 붙이기` 를 **웹이** 한다
  (`GET /api/storyboard/v1/storyboards/{id}` · `/key-messages` 읽기, `POST …/key-messages/{kmsg}/evidence` 쓰기 — 근거 문장은 mi `GET /v1/analyses/{id}/evidence` 의 익명 처리 끝 값).
  storyboard 요청(위 「Storyboard 시연 속도 · 읽기 간선」 필요 2)과 같은 내용 — mi 도 서버끼리 읽게 바꿀 생각은 없고, 간선을 더하면 그때 옮기겠다.
- 확인: proposal · vp 가 mi 를 부른다(`proposal-handoff` · `auto_run` · `facts:lookup` · `bundle?target=vp`) — `config/services.yaml` 의 proposal · vp `consumes` 에 `mi` 가 있어야 한다.
  경쟁사 분석 반입(`POST /api/mi/v1/imports/competitor`, `bundle?target=competitor`)을 서버가 부른다면 competitor `consumes` 에도 `mi`.
- 상태: 요청(확인)
- 상태 갱신(플랫폼, 2026-10-07): mi · competitor · scenario consumes 에 storyboard, competitor 에 mi 추가.
- 상태 갱신(mi): `config/services.yaml` 을 다시 보니 proposal · vp `consumes` 에 `mi` 는 이미 있다 — 남은 것은 storyboard 간선(선택)과, 경쟁사 서버가 mi 를 직접 부를 때의 competitor `consumes` 뿐.

## competitor 설정 키 `.env.example` 등록 — competitor · 2026-10-07
- 필요: 경쟁사 분석이 읽는 환경 변수(없으면 아래 기본값으로 동작)를 `.env.example` 에 적어 주세요.
  - `CA_ASK_SLOTS_REQUIRE_AMBIGUOUS_INDUSTRY=true` — 묻기 1(CA2Q) 조건(04-competitor §3.3 · §10.3). `false` 면 고객사 · 장소가 둘 다 없을 때 업종이 분명해도 묻는다.
  - `CA_ANALYZE_CONCURRENCY=2` — 동시에 분석하는 경쟁사 수(§10.5).
  - `CA_PARSE_TIMEOUT_S=8` — `POST /v1/parse` 의 LLM 읽기 제한 시간(넘으면 KB 만으로 읽고 `degraded=true`).
  - `CA_TODAY=` — 시험 · 시연 전용 고정 날짜(YYYY-MM-DD, 30일 재확인 · 날짜 비교 재현용). 운영에서는 비워 둔다.
- 참고: `consumes` 에 storyboard · mi 를 더해 주셔서 고맙습니다. 지금은 명세(§4.9 · §11 Q5)대로 **웹이** MI · Storyboard 로 묶음을 옮기고, 서버는 부르지 않는다.
- 상태: 완료(2026-10-07) — `.env.example` §14(CA_TODAY 는 시험용 목록).

## scenario 설정 키 `.env.example` 등록 — scenario · 2026-10-07
- 필요: 공간 시나리오가 읽는 환경 변수(없으면 아래 기본값으로 동작)를 `.env.example` 선택 설정에 적어 주세요.
  - `# SC_PACE_S=0   # scenario: mock 시연 · e2e 진행 화면(SC4G) 속도 — 장면 하나 쓰기 전 쉬는 초, 0 = 바로(테스트는 0)`
  - `# SC_LLM_RETRY_DELAYS=1,3   # scenario: LLM 503 · 504 다시 시도 간격(초, 쉼표) — 시험은 0,0`
- 새 의존성 · consumes 간선 요청은 없다(storyboard 간선 추가 고맙습니다 — SB4 `?sb=` 공간 · 고객 미리 채움을 서버에서 읽는다).
- 상태: 완료(2026-10-07) — `.env.example` §14.

## birdseye 의존성 · 설정 키 — birdseye · 2026-10-07
- 의존성: `services/birdseye/pyproject.toml` 에 지금 `pillow · numpy · shapely · pdfplumber · pypdfium2` 가 있다(잠금 파일에 이미 있음).
  추가로 BE1P QR(휴대폰 업로드)에 `reportlab`(`reportlab.graphics.barcode.qrencoder`)을 **있으면 쓰는 선택 의존성**으로 쓴다 — 지금은 export 쪽 설치분을 빌려 쓴다.
  birdseye 의존성에 `reportlab` 을 넣어 주세요(없으면 QR 대신 주소만 보인다). LangGraph · PyYAML 은 winmate-common 경유로 쓴다.
- `.env.example` 등록 부탁(모두 선택, 기본값 있음):
  `PUBLIC_BASE_URL`(QR 주소 앞부분 — 휴대폰이 닿는 PC 주소, 비우면 상대 경로) · `BE_LLM_TIMEOUT_S`(기본 30) · `BE_RENDER_POLL_S`(기본 1.5) ·
  `BE_RENDER_TIMEOUT_S`(기본 600) · `BE_UPLOAD_TOKEN_MIN`(기본 30).
- 게이트웨이: 휴대폰은 로그인 쿠키가 없을 수 있다. `GET /api/birdseye/v1/upload-tokens/{token}` · `POST /api/birdseye/v1/upload-tokens/{token}/photos` 와
  그 앞의 파일 올리기(`POST /api/files/v1/files`)를 **업로드 토큰으로만** 통과시키는 길이 필요하다(토큰 = 조감도 하나 · 30분 · 사진만).
  제안: 게이트웨이 공개 경로 목록에 위 두 경로를 넣고, files 는 `X-Upload-Token` 헤더가 있으면 birdseye `GET /v1/upload-tokens/{token}`(internal 검증)으로 확인 뒤 받기.
  지금은 개발 사용자 세션으로 돈다(사내망 PC 와 같은 브라우저 세션이 아니면 실패).
- 상태: 완료(2026-10-07) — reportlab 선언 · uv.lock, `.env.example` §14(PUBLIC_BASE_URL · BE_* · AUTO_EXTRA_CUTS), 게이트웨이 업로드 토큰 통과(birdseye `GET /v1/upload-tokens/{token}/principal` internal, gateway consumes birdseye). 웹의 셸 밖 `/m/upload/:token` 경로 · 로그인 예외는 workspace 담당.
- 정정(birdseye · 2026-10-07, 위 설정 키 기본값 — 코드 `services/birdseye/src/winmate_birdseye/config.py` 기준): `BE_LLM_TIMEOUT_S`=60 · `BE_RENDER_POLL_S`=0.5 ·
  `BE_RENDER_TIMEOUT_S`=900 · `BE_RETRY_DELAYS`=`2,6`(503 재시도 간격 초) · `AUTO_EXTRA_CUTS`(비우면 `config/rules.yaml` 값, 기본 켬) · `PUBLIC_BASE_URL`(비우면 상대 경로).
  `BE_UPLOAD_TOKEN_MIN` 은 없다(QR 토큰 30분 고정).

## jobs — 사용자 단위 이벤트 스트림(휴대폰 업로드 → BE1P 실시간 카드) — birdseye · 2026-10-07
- 필요(08-birdseye AC20 「모바일이 토큰으로 사진을 올림 → BE1P 에 카드가 SSE 로 추가」): 휴대폰 업로드는 birdseye 가 `photo_recognize` 잡을 만들지만
  PC 화면은 그 잡 id 를 모른다. jobs 계약에는 잡 하나의 SSE(`/v1/jobs/{id}/events`)만 있어 BE1P 는 4초마다 사진 목록을 다시 읽는다.
- 제안: `GET /v1/events?ref=<자원 id>`(또는 `?service=birdseye&ref=be_…`) — 그 사용자 · 그 ref 로 만든 잡의 생성 · 진행 · 끝 이벤트 SSE. 생기면 폴링을 지운다.
- 상태: 보류(2026-10-07) — 지금은 BE1P 4초 다시 읽기로 충분. 필요해지면 jobs `GET /v1/events?ref=` 로.

## 게이트웨이 — 끊긴 keep-alive 연결로 500(RemoteProtocolError) — competitor · 2026-10-07
- 관찰: e2e 중 `GET /api/competitor/v1/analyses/{id}` 가 가끔 `500 {"error":{"code":"INTERNAL", …, "details":{"type":"RemoteProtocolError"}}}` 로 온다
  (서비스는 정상 · 바로 다시 부르면 200). 업스트림은 `make dev-bg SERVICE=competitor` 의 uvicorn(--reload).
- 짐작: 게이트웨이 httpx 풀이 업스트림이 이미 닫은 keep-alive 연결(uvicorn 기본 `timeout_keep_alive=5s`)을 다시 써서 `Server disconnected without sending a response`.
- 제안: 프록시에서 `httpx.RemoteProtocolError` · `ConnectError` 는 GET/HEAD(멱등)만 한 번 다시 보내기, 또는 풀 `keepalive_expiry` 를 업스트림 keep-alive 보다 짧게(예: 4s).
- 지금은: 경쟁사 e2e 도우미(`web/e2e/competitor/helpers.ts` `api()`)가 GET 만 두 번까지 다시 묻는다.
- 상태: 완료(2026-10-07) — keepalive_expiry 4초 + GET/HEAD 한 번 재시도, 그 밖은 502 UPSTREAM_ERROR(services/gateway/tests).

## vp 시연 속도 `VP_PACE_S` — vp · 2026-10-07
- 필요: VP3G(생성 중 · 결정 기록)를 시연할 때 단계 사이에 쉬는 시간(초). mock 모델은 몇 초 만에 끝나 화면이 바로 VP3 로 넘어간다.
- 설정: 환경 변수 `VP_PACE_S`(기본 0 — `services/vp/config/routing.yaml` `dev.pace_s` 가 대체값). 실제 모델에서는 0 그대로.
- 제안: `.env.example` 에 `VP_PACE_S=0` 한 줄(설명: "vp 생성 단계 사이 쉬는 시간(초) — 시연용"). 새 의존성 · 새 consumes 간선은 없음(vp → image 는 웹 이동만).
- 상태: 완료(2026-10-07) — `.env.example` §14.

## 로그인 화면이 생김 — 문서 · .env 안내 · 게이트웨이 세션 보강 — workspace · 2026-10-07
- 바뀐 것(workspace 셸 · 서비스): 웹에 `/login?next=` 로그인 화면 · 전역 401 처리(→ `/login?next=<지금 화면>`) · 사용자 메뉴(로그인한 사용자 · 로그아웃 · 비밀번호 바꾸기 · `사용자 관리`) · `/admin/users` 사용자 관리 화면이 생겼다.
  workspace 관리자 준비 조건이 "사용자 표가 비었을 때" → **"쓸 수 있는 관리자(role=admin · 비밀번호 있음 · 사용 중)가 없을 때"** 로 바뀌었다 — AUTH_MODE=none 으로 먼저 띄워 `u_dev` 가 생겼어도
  `.env` 의 ADMIN_USERNAME/ADMIN_PASSWORD 로 관리자가 생긴다(같은 아이디가 있으면 관리자로 올리고 비밀번호를 정함). 새 API: `PATCH /v1/users/{id}`(관리자: 이름 · 소속 · 역할 · 비밀번호 재설정 · `disabled`) · `POST /v1/me/password`.
- 요청 1(문서): `.env.example` 의 "웹에는 아직 로그인 화면이 없다" · "사용자가 하나도 없을 때 만드는 관리자" 주석과 `docs/OPERATIONS.md` §2.5 · §2.10 · 문제 해결 표(589 · 590행 근처 "웹 로그인 화면 없음" · "관리자 생성 조건")를 위 내용으로 고쳐 주세요.
  사내망 켜기: `.env` `AUTH_MODE=local` · `ADMIN_PASSWORD=<…>`(필요하면 `ADMIN_USERNAME`) → `pm2 restart gateway workspace`(둘 다 AUTH_MODE 를 읽는다) → 브라우저 `/login` 으로 관리자 로그인 → 사용자 메뉴 `사용자 관리` 에서 계정 만들기.
- 요청 2(게이트웨이, 선택): 세션 쿠키(14일)는 서명만 확인해서 관리자가 사용자를 사용 중지하거나 비밀번호를 재설정해도 이미 받은 세션은 끝까지 쓴다.
  제안: `/api/_auth/me` 와 프록시가 세션 사용자를 가끔(예: 5분 캐시) workspace `GET /v1/users/{id}`(internal 로 하나 더 만들 수 있음) 로 확인해 `disabled` 면 401, 또는 세션에 `password_changed_at` 을 넣어 다르면 401.
- 요청 3(게이트웨이, 선택): `/api/_auth/login` 시도 횟수 제한(같은 IP · 아이디 연속 실패 → 429). 로그인 화면은 429 를 「로그인 시도가 너무 많아요. 잠시 뒤 다시 해 주세요.」로 보인다.
- 상태: 완료(2026-10-07) — 요청 1: `.env.example` · OPERATIONS 2.5 · 문제 해결 표 · §4 갱신. 요청 2: 게이트웨이가 local 세션을 60초마다 workspace `GET /v1/users/{id}/status`(internal)로 확인해 사용 중지 · 비밀번호 재설정 뒤 401. 요청 3: 로그인 연속 실패 429 `TOO_MANY_ATTEMPTS`(같은 IP · 아이디 5번 / IP 20번, 10분). services/gateway/tests.
- 상태(export · 2026-10-07, 위 「export — LibreOffice · 글꼴 · SVG 로고」 코드 쪽): 501 `PDF_CONVERTER_UNAVAILABLE` 이 원인과 고칠 방법을 알려 준다
  (`details{reason: off|missing|unset, fix, detected?}` — 이 서버에서 찾은 soffice 경로 · 설치 명령). `GET /api/export/v1/info` 에 `pdf_converter_reason` ·
  `pdf_converter_detected` · `pdf_font{family, resolved, ok}`. `SOFFICE_PATH` 값 뜻은 files 와 같다(경로 · PATH 이름 · off) — 단 **비우면 export 는 끈다**(그대로:
  다른 서비스 테스트가 이 501 을 기대하고 — 예 storyboard `test_real_export_render[pdf]` 는 501 이면 skip — 무거운 변환을 설정 없이 켜지 않는다).
  이 개발 컨테이너: /usr/bin/soffice 가 있지만 `.env` 에 SOFFICE_PATH 가 없어 export PDF 는 501. 켜려면 `.env` 에 `SOFFICE_PATH=/usr/bin/soffice` 후
  `pm2 restart export export-worker`(그러면 위 테스트들이 실제 변환 잡을 탄다). 글꼴: 이 컨테이너 fontconfig 는 `Noto Sans KR` → `Inter`(Noto Sans CJK KR 은 깔려 있음) —
  OPERATIONS 의 fontconfig 별칭이 필요. export 는 우리 덱을 PDF · 그림으로 만들 때 이 경우 경고를 붙인다. 새로 LibreOffice 를 쓰는 곳: 고객사 .xls · .ods 양식 읽기(잡).
  SVG 로고는 코드 변화 없음(cairosvg 보류 그대로).
