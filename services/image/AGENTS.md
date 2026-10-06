# image 서비스 — 개발 세션 규칙

이미지 생성 — 유형 · 상세 조건 · 참조 이미지 · 현장 합성 · 부분 수정 · 변형 · 업스케일

- 포트: **5107** · 게이트웨이 경로: `/api/image/v1/...` · 파이썬 모듈: `winmate_image`
- 고칠 수 있는 경로(owns): `services/image/**`, `web/src/features/image/**`
- 호출할 수 있는 서비스(consumes): `ai-tools`, `kb`, `files`, `jobs`, `workspace`, `export`
- 화면 수용 기준: `docs/scenarios/07-image.md` · 원본 보드: `docs/screens/` (INDEX.md)

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=image          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=image         # 이 서비스 테스트
make contracts SERVICE=image    # contracts/image.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("image", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("image")`(data/image/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=image` 를 돌리고 `contracts/image.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태 (2026-10-06)
07-image 의 12개 보드(UC_IMG 는 런타임 화면 아님) · 수용 기준 57개를 구현했다. 백엔드 테스트 74개 · e2e 20개 통과(MODEL_MODE=mock).

### 코드 지도 (`src/winmate_image/`)
| 파일 | 하는 일 |
|---|---|
| `api.py` · `models.py` | `/v1` 라우트 51개 · 모든 요청/응답 Pydantic 모델(= `contracts/image.json`) |
| `service.py` | 작업 만들기/고치기(409 VERSION_CONFLICT) · prefill(R1, 10초 · LLM 8초) · 배지 · 경로 · workspace 색인(`feature='IMG'`) · 셸 참조로 제품 더하기 · 참조 캡션으로 장면 설명 채우기 |
| `refs.py` · `analysis.py` | 참조 해석(kb_asset · case_photo · my_image · upload · topbar) · 탭 검색 · 예산 배정(§10.3) · 얼굴/로고 흐림 · 팔레트 |
| `photos.py` · `graphs/recognize.py` | 현장 사진 인식(면 · 물체 · 바닥선) · 어두움 판정 · 축척(기준 치수 → 표준 크기 → [00]) · 기본 배치 |
| `runs.py` · `scheduler.py` · `shots.py` · `notify.py` | run 만들기(동기 사전 검사) · 사용자별 대기열(FIFO, 진행 1) · 시안 동시 2 · EMA 진행률 · 장별/전체 취소 · 완료 알림 1회 |
| `policy.py` · `data/content_policy.yaml` | 경쟁사 사전(초안) + 정규식 + LLM 판정 · 보류 floor(N/2) · 대안 적용 · 프롬프트에서 이름 빼기 |
| `graphs/generate.py` · `graphs/common.py` | initial · composite · alternatives(interrupt → answers 로 재개) · QC 1회 재생성 · 합성 결정적 초안 → t2i.edit → 가장자리 IoU 확인 |
| `graphs/edit.py` · `variants.py` · `renditions.py` · `render.py` | 부분/전체 수정(마스크 · 제품 보호 · 영역 밖 바이트 동일) · 변형 A~ · 비율(다시 구성 · 잘라내기 · 바깥 채우기 + 업스케일) · 렌더 API |
| `images.py` · `imaging.py` · `exports.py` | 버전 · 렌디션 사다리 · 감지 · 영역 · 보정 · 메타데이터(iTXt + XMP trainedAlgorithmicMedia) · AI 표기 · 내보내기(PNG/JPG 바로, ZIP/PDF/PPTX 는 export 잡) |
| `requests_.py` · `renders.py` | 다른 기능의 요청(start · fulfill · dismiss) · birdseye/scenario 렌더 API(숨은 internal 작업) |
| `llm.py` · `prompts.py` · `texts.py` | `ai()` 호출(재시도 2회 2초/6초 · 503/504 · POLICY_CONFIDENTIAL → 로컬 경로 · QUOTA) · 프롬프트 · 조사/시간/파일명 규칙 |

### API — 다른 기능이 쓰는 것
- **셸(workspace)**: `GET /v1/images?owner=me&q=&limit=&cursor=`(저장한 시안만, 낱말 검색) · `GET /v1/images/{id}/info` · `POST /v1/works/{id}/products`(「현재 작업에 추가」 제품 참조) · 참조 `img:image:<id>`.
- **proposal**(internal): `GET /v1/images/{id}`(I1) · `GET /v1/versions/{id}` · `POST /v1/images/{id}/usages` · `DELETE /v1/images/{id}/usages/{service}/{ref}` · `POST /v1/requests`(표지 배경 등).
- **scenario**(internal): `POST /v1/requests` · `GET /v1/requests?from_service=&from_ref=` · `GET /v1/versions/{id}` · `POST /v1/renders` · usages.
- **birdseye**(internal): `POST /v1/renders`(structure_ref 1순위, 참조 없으면 t2i.edit) · `GET /v1/renders/{id}` · `POST /v1/renders/{id}:cancel` · `GET /v1/versions/{id}` · usages.
- 화면용: works CRUD · `:prefill` · reference-search · references(GET/POST/PUT/PATCH/DELETE) · site-photos(POST 202 · GET · `:recognize` · DELETE) · placements(PUT) ·
  runs(POST 202/409 · GET · PATCH notify · `:cancel` · shots `:cancel` · answers · alternatives) · queue · images · `images:bulk-export` · `:save` · versions · restore ·
  detections · regions(CRUD · `:revert`) · edits · adjust · variants · renditions · `:interpret` · caption · filename · exports(POST · GET) · requests(GET · `:start` · `:fulfill` · `:dismiss`) · capabilities.

### 워커 · 모델 호출
- 잡 kind: `run`(generate · edit · variants · renditions · render 그래프) · `recognize_photo` · `analyze_reference` · `noop`. `IMAGE_WORKER_TASKS=12`(대기 task), 실제 동시는 scheduler(heavy 2).
- ai task: `img.prefill` · `img.policy` · `img.compose` · `img.render` · `img.qc` · `img.ref_analyze` · `img.recognize_photo` · `img.composite` · `img.detect` ·
  `img.region_name` · `img.edit` · `img.variant_plan` · `img.variant` · `img.rendition` · `img.edit_intent` · `img.variant_request` · `img.export_request` · `img.caption` ·
  `img.filename_en` · `img.screen_content` · `img.alt_custom`. 고객 자료(현장 사진 · 업로드 참조)는 `confidential=True`, 막히면 §7.2 로컬 경로(`composite:local_only` 등).
- 목 픽스처 `mocks/ai-tools/img.*.json` 16개(prefill = QM55C ×3 · 「카페 매장 메뉴보드 시안」 등 고정).

### 웹 (`web/src/features/image/`)
| 라우트 | 보드 |
|---|---|
| `/image` | IMG0 작업 목록 · 갤러리(진행 SSE + 15초 폴링 · 다중 선택 ZIP · 변형 · 제안서) |
| `/image/new` (`?work=` · `?request=`) | IMG1 · `/image/new/references` · `/image/new/composite` 는 작업을 만들고 IMG2R · IMG2P 로 |
| `/image/w/:workId/conditions` · `references` · `composite` | IMG2 · IMG2R · IMG2P(캔버스: 끌기 · 손잡이 8 · 원근 4점 스냅 · 보기 · 확대) |
| `/image/w/:workId/run/:runId` | IMG3G(queued · running) · IMG3X(awaiting_input) |
| `/image/w/:workId/result` (`?image=` · `?run=`) | IMG3 |
| `/image/w/:workId/edit/:imageId` (`?preset=`) · `variants/:imageId` · `export/:imageId` (`?version=` · `?also=`) | IMG3E · IMG3V · IMG4 |
- 셸: `accepts`/`onAdd` — IMG1 · IMG2R 이미지, IMG2 제품 · 이미지, IMG2P 제품, IMG3X 제품(「제품 탐색에서 고르기」). IMG0 `onAttach` → 참조로 새 작업.
- 지역 부품(키트 요청 중): `ProductChips`(수량 칩) · `Echo` · `WSay` · `Seg` · `ShotCard` · `ZoomView`(components.tsx).
- e2e: `web/e2e/image/*.spec.ts`(20개) · 화면 캡처 `__screens__/`. 진행 화면을 보려면 `IMAGE_DEV_SHOT_DELAY_S=2.5 make dev-bg SERVICE=image` 로 띄운 뒤 `make e2e-feature SERVICE=image`.

### 결정 · 문서와 다른 점
- workspace 색인 `feature='IMG'`(workspace 계약 enum), 상태는 문자열 + 배지 meta.
- 대기열 · 순번은 jobs 목록이 아니라 image DB 의 run 으로 계산(잡 레코드는 대기 중에도 running).
- 갤러리 「내 이미지」 = 저장 · IMG4 자동 저장 · 취소 때 남긴 시안 + 진행 중 run 마다 타일 1. 셸 `owner=me` 는 저장한 것만.
- 감지(detections)는 동기 200(202 아님). 작은 영역 인페인트는 OpenCV 대신 Pillow 확산(`edit:local_inpaint`).
- 문서에 없는 경로를 더함: PUT references(IMG2R 묶음 적용) · GET works/{id}/references · GET works/{id}/runs · GET /v1/versions/{id} · `:interpret` · caption · filename ·
  run alternatives · DELETE site-photo · POST works/{id}/products. `:start` 응답에 `route`(IMG1) · `conditions_route`(IMG2).
- KB 사례 이미지(customer_case)는 기밀 아님으로 다룬다. prefill 은 A1 과 함께 모델코드 정규식 검색도 한다(A1 이 QM55C 같은 표시명을 못 이음).
- 409 RUN_IN_PROGRESS 는 `details.run_id` 를 준다(웹이 그 run 으로 이동). 영문 파일명은 원문에 없는 고객사 · 주제를 넣지 않는다.
- (신규) 문구: 생성 끝 W 「{N}장을 모두 만들었어요…」, 업로드 전 IMG2P W, 촬영 가이드 3줄, 대기열 · 인식 중 상태 문구 등은 디자인 확인 전 임시.

### 남은 것 · 통합 담당
- 제안서 계약에 `GET /proposals?tab=` · `image-slots` · `imports` 가 없다(`docs/requests/proposal.md`) — 지금 IMG4 는 404 면 「진행 중인 제안서가 없어요」, 503 이면 「다시 시도」.
- proposal · scenario · birdseye 의 `consumes` 에 `image` 추가 필요(안내: `docs/requests/{scenario,birdseye,proposal}.md`).
- `config/content_policy.yaml` 소유 · 법무 승인, ×4 업스케일 모델 · OpenCV(선택) — `docs/requests/platform.md`. 키트 부품 — `docs/requests/workspace.md`.
- UC_IMG 개발 화면(`/_dev/uc/image`)은 만들지 않았다(선택 항목).
- e2e 중 다른 세션이 기능 파일을 저장하면 셸 순환 import(HMR)로 화면이 빌 수 있다 — 그 테스트만 다시 돌린다(`docs/requests/platform.md` 요청).

### 통합(integration · 2026-10-07)
- mock 렌더 QC 는 요청 수량 · 배치 상자를 맞은 것으로(`qc.mock_matched`) — 조감도 컷이 늘 「제품 수 다름」이던 것. 렌더 API 의 숨은 작업(`internal`)은 workspace 색인에 안 올림.
- 이미지 정보 「사용 이력」 = `Winmate 제안서 n건 · 조감도 k건 · 시나리오 k건`. 제안서를 지우면 proposal 이 사용 등록을 푼다.
