# birdseye 서비스 — 개발 세션 규칙

공간 조감도 — 공간 입력 · 도면 인식 · 제품 배치 · 가구 추천 · 배치 검증 · 3D 조감도

- 포트: **5108** · 게이트웨이 경로: `/api/birdseye/v1/...` · 파이썬 모듈: `winmate_birdseye`
- 고칠 수 있는 경로(owns): `services/birdseye/**`, `web/src/features/birdseye/**`
- 호출할 수 있는 서비스(consumes): `ai-tools`, `kb`, `files`, `jobs`, `workspace`, `export`, `image`
- 화면 수용 기준: `docs/scenarios/08-birdseye.md` · 원본 보드: `docs/screens/` (INDEX.md)

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=birdseye          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=birdseye         # 이 서비스 테스트
make contracts SERVICE=birdseye    # contracts/birdseye.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("birdseye", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("birdseye")`(data/birdseye/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=birdseye` 를 돌리고 `contracts/birdseye.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태(2026-10-07)
08-birdseye 화면 · 흐름 · 수용 기준을 끝까지 구현했다. 테스트: pytest 42(`make test SERVICE=birdseye`) · e2e 6(`make e2e-feature SERVICE=birdseye`, 화면 캡처 `web/e2e/birdseye/__screens__/`).

**화면(web/src/features/birdseye)** — BE0 `/birdseye` · BE1 `/birdseye/new`(+`?ref_version=` · `?return_to=`) · BE1D `/new/plan` · `/:id/space/plan` ·
BE1P `/new/photos` · `/:id/space/photos` · 휴대폰 `/birdseye/m/:token` · BE2 `/:id/products` · BE3 `/:id/furniture` · BE4 `/:id/layout` · BE4E `/:id/layout/edit`(`?move=item:dx:dy`) ·
BE5G `/:id/render/:jobId` · BE5 `/:id/result?cut=` · BE5V `/:id/views`(`?mode=tone`) · BE5Z `/:id/zones`(`?scenario=sc_…` 장면 연결) · BE6 `/:id/export`(`?map=BV-B|ZP`) · UC `/birdseye/uc`.

**다른 기능이 쓰는 API**(계약 `contracts/birdseye.json`)
- scenario: `GET /v1/birdseyes?limit=`(행 `id · title · zone_count · version · layout_version`) · `GET /v1/birdseyes/{id}/version` · `GET /v1/birdseyes/{id}/handoff`
  (`zones.points[]` id · short_name · path_order · u · v · products · furniture · text, `plan_preview`, `customer`) · `POST /v1/birdseyes {prefill, origin}` · `POST /v1/birdseyes/{id}/usages`(internal).
- proposal: `GET /v1/birdseyes/{id}/proposal-handoff?type=&section=`(ProposalHandoff v1 — `BV-A` · `BV-B` · `ZP-A|B|C` · `SM-B` · `VM-C`) · 별칭 `GET /v1/layouts/{id}/proposal-handoff` ·
  `GET /v1/birdseyes/{id}/handoff` · `POST|DELETE /v1/birdseyes/{id}/usages…`(internal). 웹 진입: `/birdseye/new?return_to=` · BE6 「제안서에 넣기」 → proposal imports.
- image: IMG4 「조감도 참조로」 → `/birdseye/new?ref_version=imv_…`.

**잡(워커 `worker.py`, LangGraph)** — `space_analyze`(load_inputs → parse_description → merge → capability_hints → save) · `plan_recognize`(fetch → i2t → geometry → model) ·
`photo_recognize`(quality → i2t → save) · `space_nl_edit` · `furniture_recommend` · `layout_generate` · `layout_nl_edit` · `render_cut`(structure → products → furniture → render(image `POST /v1/renders`) → qc) ·
`result_edit` · `zones_auto` · `zones_rewrite` · `export` · `noop`. 모델 task: `be.classify_image · plan_analyze · photo_analyze · photo_aggregate · photo_facts · space_parse · space_ops ·
furniture_recommend · furniture_match · layout_intent · layout_ops · camera · result_classify · zone_texts · zone_rewrite`(고정 응답 `mocks/ai-tools/be.*.json`). 고객 도면 · 사진은 `confidential=True`,
403 `POLICY_CONFIDENTIAL` 이면 벡터(PDF) · 로컬 품질 검사만으로 진행하고 화면에 알린다.

**데이터(DocStore birdseye)** — birdseyes · space · plans · photos · tokens · products · furniture · layouts · sessions · memos · cuts · zones · exports · usages · snapshots · stats.

**결정 · 문서와 다른 점**
- `GET /layout` 은 Layout 그대로가 아니라 화면용 묶음 `LayoutView{layout, plan, overlays, w_message, open_warnings, running, job_id, tone, default_view}`.
- `POST /birdseyes/{id}/attachments` 추가 — BE1 첨부를 R1 규칙(PDF → 도면, 이미지 → i2t 「평면도인가」)으로 나눠 도면 · 사진 잡을 만들고 갈 화면(`route`)을 준다.
- 배치 의도(LLM)는 닫힌 어휘: 항목 키 `p1 · f1 · <id> · role:<역할>`, 앵커가 틀리면 앵커만 규칙값으로 두고 수량 · 위치 라벨은 받는다.
- `result:edit` — 분류가 배치 · 시점이면 바로 처리(라우트 반환), 렌더 수정만 잡. 애매하면 `route_hint='ask'` + 질문.
- 존 번호 「동선 순서」 = 주출입구에서 각 존 접근점(항목 0.8 m 바깥)까지 실내 경로 거리.
- AC32 보드 수치(벤치 6.0 m · 3.0 m 이동 → 왼쪽 2석)는 기하로 동시에 성립하지 않아 시험은 벤치를 3.1 m 로 당긴 뒤 본다. AC34 수정안 방향은 기하에 따라 「위로 / 아래로」.
- 실제 KB 에 OH55C · WA75D · IAB 가 없어 pytest 는 골든 제품을 저장소에 심고, e2e 는 실제 KB(OH55A · Flip Pro · The Wall IWC)로 돈다.
  kb 코드에 `/` 가 든 모델(The Wall IWC)은 목록 검색으로 대신 읽고, LED 의 30" 미만 크기(모듈)는 화면 크기로 쓰지 않는다(치수 `[확인 필요]`).
- BE5V 조명: 처음 고르는 조명은 기본값(주 컷 조명)을 바꾸고 그다음부터 여러 개(보드 예 「입구 + The Wall 정면, 야간」 = 2컷).
- 화면 표시 이미지는 FHD 렌디션(`Cut.display_url`), 내려받기 · 내보내기는 3840×2160 원본.
- 휴대폰 업로드: QR 주소는 `/m/upload/{token}`(셸 밖 경로는 workspace 요청 중) · 지금은 `/birdseye/m/:token`. PC 화면은 사용자 단위 SSE 가 없어 4초 폴링(platform 요청).
- BE2 제품 입력은 키트 `ProductInput` 머리 문구가 보드와 달라 같은 동작의 로컬 컴포넌트(workspace 요청).
- 삭제는 소프트 삭제(`deleted_at`) — 제안서 · 시나리오에 넣은 이미지는 남는다.

**요청한 것** — workspace(셸 밖 `/m/upload/:token` · ProductInput 머리 문구) · platform(reportlab · 설정 키 · 토큰 업로드 게이트웨이 · jobs 사용자 SSE) ·
kb(`/` 든 모델 코드 · LED 화면 크기 · placement-rules · dims 정규화) · image(mock QC 가 늘 check). proposal(반입 뒤 usages 등록)은 proposal 쪽에서 완료.

**통합(integration · 2026-10-07)** — BE6 제안서 기본 대상(return_to → 같은 프로젝트 → 첫 줄) · 토스트 「열기」는 응답 섹션, 「Spec 시작」 `from=birdseye:{id}`, BE1 `?return_to=`(옛 `?return=`도).
mock QC 는 image 에서 고쳐 컷이 `done`. SM 수량표는 proposal 이 「공간별 제품」 섹션으로 보낸다.
