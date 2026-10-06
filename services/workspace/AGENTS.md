# workspace 서비스 — 개발 세션 규칙

워크스페이스 — 사용자 · 프로젝트 · 작업물 색인(최근 작업·사이드바 이력) · 코멘트 · 검토/승인 · 공유 링크

- 포트: **5050** · 게이트웨이 경로: `/api/workspace/v1/...` · 파이썬 모듈: `winmate_workspace`
- 고칠 수 있는 경로(owns): `services/workspace/**`, `web/src/shell/**`, `web/src/ui/**`, `web/src/App.tsx`, `web/src/main.tsx`, `web/e2e/shell/**`, `web/playwright.config.ts`
- 호출할 수 있는 서비스(consumes): 없음

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=workspace          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=workspace         # 이 서비스 테스트
make contracts SERVICE=workspace    # contracts/workspace.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("workspace", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("workspace")`(data/workspace/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=workspace` 를 돌리고 `contracts/workspace.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태
### 서비스(services/workspace) — 2026-10-07
- 모듈: `db.py`(저장소 · 상수) · `users.py`(사용자 · 로그인 확인 · 관리자) · `api.py`(프로젝트 · 작업물 색인 · 코멘트 · 공유 링크 · 자산 사용 이력) · `reviews.py`(검토/승인) · `notify.py`(작업물 알림).
- 사용자: `GET/PATCH /v1/me`(username · has_password 포함) · `POST /v1/me/password`(지금 비밀번호 확인) · `GET/POST /v1/users` · `PATCH /v1/users/{id}`(이름 · 소속 · 역할 · 비밀번호 재설정 · `disabled`).
  AUTH_MODE=local 이면 사용자 관리는 관리자만(마지막 관리자 강등 · 중지는 409 `LAST_ADMIN`), none 이면 누구나(개발). 비밀번호는 scrypt, 사용자 문서는 이력(doc_versions)을 남기지 않는다.
- 로그인 확인 `POST /v1/auth/verify`(internal, 게이트웨이 `/api/_auth/login` 이 부름): 사용 중지 계정 거절 · 아이디 대소문자만 다르면 같은 계정 · `last_login_at` 기록.
- 관리자 준비 `bootstrap_admin()`(시작할 때 · 로그인 확인 때): AUTH_MODE=local 이고 **쓸 수 있는 관리자(role=admin · 비밀번호 · 사용 중)가 없으면** `.env` ADMIN_USERNAME/ADMIN_PASSWORD 로 만든다(같은 아이디가 있으면 관리자로 올리고 비밀번호를 정함). none 으로 먼저 띄워 개발 사용자가 있어도 된다.
- 작업물 색인 · 코멘트 · 공유 링크 · 자산 사용 이력: 예전 그대로(`PUT /v1/items/{id}` internal · `GET /v1/items` · `/items/counts` …).
- 검토: `POST /v1/reviews`(+ `due_date` · `item_id` · `version_label`) · `decision` · `PUT|DELETE /v1/reviews/{id}/checks/{target_ref}`(검토자별 대상 확인 ok|need) ·
  `POST /v1/reviews/{id}/resubmit`(라운드 +1 · 결정 · 확인 초기화 · 지난 라운드는 `rounds[]`) · `PATCH /v1/reviews/{id}`(마감일) · `GET /v1/reviews?item_id=` · `cancel`.
- 알림: `POST /v1/notifications`(internal — `{item_id, title, route?, type?, …}` → 항목 주인 + recipients, 사용자마다 저장 + jobs 알림 흐름) · `GET /v1/notifications`(내 것, `unread_only` · `item_id`) ·
  `GET /v1/notifications/counts`(읽지 않은 수 — 전체 · 항목별) · `POST /v1/notifications/read {ids? | item_id?}`(없으면 전부). 검토 요청 · 결정 · 다시 요청 때 `review_requested` · `review_decided` · `review_resubmitted`.
- 시험: `make test SERVICE=workspace` — 12개(test_basics · test_auth · test_notify_reviews). 계약 `contracts/workspace.json`(25 경로).

### 웹 셸 · UI 키트 (web/src/shell · web/src/ui) — 2026-10-07
- 틀: 1440×900(최소 1280) 레이아웃 · 사이드바(기능 10 그룹 · 작업 5개 · 사용자 카드, workspace `/me` · `/items` · `/items/counts`) · 상단바(브레드크럼 + 팝오버 4) · 스텝바(딸깍 팝오버) · 홈(§5.1, 문구는 `shell/catalog.ts`) · `WorkListPage`(작업 목록 기본형).
- 팝오버 4종(제품 트리 L1›L2›시리즈 · 솔루션 11 · 이미지 탭/출처 토글/정보 패널/대화에 첨부 · 유관 사례 필터 업종/제품/지역/기간) — 실제 kb §7.2. 「내 생성 이미지」 = image `GET /v1/images?owner=me&q=` · 정보 행 `GET /v1/images/{id}/info` · 참조 `img:image:<id>`.
- 상세 시트 2종(제품 `spec · images · cases`, 솔루션 `overview · images · cases`) — URL `detail=` · `tab` · `img`. 끌어서 추가: `application/x-winmate` · `DropZone`/`useDropTarget`.
- 기능 등록 · 격리: `registry.ts` 가 기능 index 를 따로 불러온다(non-eager glob + `Promise.allSettled`, main.tsx 가 처음 그리기 전에 기다림). import 오류면 그 경로만 `FeatureLoadFailed`,
  그리다 오류면 기능 경로마다 `errorElement`(`FeatureError`) — 셸 · 다른 기능은 그대로(`shell/errors.tsx`). `FeatureModule.publicRoutes` = 셸 밖 · 로그인 확인 없는 최상위 경로(birdseye `/m/upload/:token`).
- 로그인(AUTH_MODE=local): `/login?next=`(`shell/LoginPage.tsx`) · `AuthGate`(`shell/auth.tsx` — `/api/_auth/me` 401 → 로그인, API 401 → `/login?next=<지금 화면>`) · 401 알림은 `@/api/client`
  (openapi 미들웨어 · `uploadFile` · 전역 fetch 감시 `installAuthGuard()`) · `@/api/jobs`(잡 fetch · SSE 끊김 → `probeAuth()`). 사용자 메뉴(설정 버튼, `shell/UserMenu.tsx`): 알림 · 로그인한 사용자 · 사용자 관리 · 비밀번호 바꾸기 · 로그아웃(local 만).
  `/admin/users`(`shell/admin/UsersPage.tsx`): 사용자 만들기 · 고치기(역할 · 비밀번호 재설정 · 사용 중지) — 관리자 · AUTH_MODE=none.
- 작업물 알림: 사이드바 항목 읽지 않은 수 · 그룹 점 · 설정 버튼 점 · 사용자 메뉴 알림 목록(최근 8 · 모두 읽음) · 그 작업물 화면을 열면 읽음.
- 키트 더하기(기능 요청): 키맨 색 토큰 · `WeightBar` · `WeightStepper` · `KeymanAvatar/Dot` · `Segmented` tone/h/variant · `Toggle size="lg"` · `ChoiceCard` · `ChoiceCustomInput` · `QBadge` ·
  `ProductInput qty/headText/rowCta` · `EchoBubble` · `ChatLine body` · `ModeChip` · `SourceCard` · `EvidencePanel` · `Modal variant="side"`/`SideSheet` · `WorkPickerDialog`. 목록 · 예는 `web/src/ui/README.md`(§12~15 · 셸 API).
  기능 폴더의 지역 부품은 그대로 두었다(기능 세션이 바꿀 때 키트로).
- 개발 화면 `/_dev/shell`(작업 맥락 흉내 · 호출 로그) · `/_dev/kit`(부품 견본 + 더한 부품), 운영 빌드에서 빼려면 `VITE_WM_DEVTOOLS=0`.
- 시험: `cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers WM_E2E_SUITE=shell WM_E2E_DEV=1 WM_E2E_PORT=5197 npx playwright test e2e/shell --workers=1` — §8 수용 기준 + auth · isolation(개발 서버만) · kit-more · notify · image-mine, 화면 캡처 `web/e2e/shell/__screens__/`.
- 남은 것(kb 갭): 사례 요약 없음(G-CASE-1 → 원문 인용 `quote` 로 대신) · 지역 필터 400(G-CASE-4) · 공식 자료 없음(G-PRD-3) · 이미지 저장본이 썸네일(160px, G-IMG-2) · 솔루션 공식 이미지 일부(G-SOL-3).
  게이트웨이 세션 보강(사용 중지 · 비밀번호 재설정 즉시 반영 · 로그인 시도 제한)과 운영 문서 갱신은 `docs/requests/platform.md` 에 요청.
