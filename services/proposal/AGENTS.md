# proposal 서비스 — 개발 세션 규칙

B2B 제안서 — 시작 방식 · 섹션 작성 · 템플릿 · 딸깍 · 검토/승인 · 버전 · 기존 제안서 활용

- 포트: **5110** · 게이트웨이 경로: `/api/proposal/v1/...` · 파이썬 모듈: `winmate_proposal`
- 고칠 수 있는 경로(owns): `services/proposal/**`, `web/src/features/proposal/**`
- 호출할 수 있는 서비스(consumes): `ai-tools`, `kb`, `files`, `jobs`, `workspace`, `export`, `requirements`, `storyboard`, `mi`, `competitor`, `vp`, `spec`, `image`, `birdseye`, `scenario`
- 화면 수용 기준: `docs/scenarios/10-proposal.md` · 원본 보드: `docs/screens/` (INDEX.md)

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=proposal          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=proposal         # 이 서비스 테스트
make contracts SERVICE=proposal    # contracts/proposal.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("proposal", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("proposal")`(data/proposal/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=proposal` 를 돌리고 `contracts/proposal.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태
백엔드는 시나리오 §5–§8 전부 구현(85 경로 · 99 작업, 501 없음). 웹 화면 메모는 `web/src/features/proposal/README.md`, 요청 · 답은 `docs/requests/proposal.md`.

**API(영역 → 모듈 `ops/*`)**
- 제안서(§6.2 `proposals`): 목록 PR0(탭 · 검색 · 마감순 · 행 버튼 · 집계) · 만들기(시작 방식 5, 넘김 links · rq_ref · image_version · 복제 source_proposal_id) · 읽기 · 고치기(If-Match) · 제출 · 지우기.
- 시작(§6.3 `start`): RFP 읽기(PR1F 잡 · 항목 고치기 · 확정) · 기존 작업(PR1L 관련 작업 · 미리보기 · 연결 · 해제 · 되살리기 · 새로고침).
- 유형 · 구성 · 업종(§6.4 `compose`): 추천 유형 · 구성(넣음/추천/뺌 · 시트 수) · 섹션 시작 · 업종 레이아웃(감지 · 통계 · 적용).
- 섹션 · 시트(§6.5 `sections`): SectionView · `:fill`(잡) · 요청 · 확정 · 템플릿(옵션 · 고르기 · 자동) · 시트 PATCH(JSON 포인터 · 변경 기록) · 다시 쓰기 · 메시지 · 값(fact) · 노트.
- 반입(§6.6 `imports`): 사이드바 추출 → 적용(키 골라) · 넘김 include_keys 바로 적용 · 항목 드롭(제품 · 사례 · 솔루션 · 이미지) · IMG4 image-slots · 실행 취소(+ 사용 등록 해제).
- 딸깍(§6.7 `oneclick`) · 확인 항목(§6.8 `confirm`: 목록 · 확정(값 전파) · 노트로 · 익명 · 질문 · 근거 · 조사 잡) · 디자인 · 생성 · 결과 · 슬라이드 · 렌더(§6.9–6.10 `design`).
- 검토(§6.11 `review`, workspace 파사드: 리뷰 · 결정 · 시트 확인 · 코멘트 수정안 · 반영 버전 · 공유 링크) · 버전(§6.10 `versions`: 저장 · 비교(+ display) · 바뀐 곳 되돌리기 · 버전 되돌리기).
- 내보내기(§6.12 `exports`: 옵션 · 형식 × 언어 · 범위 · 팀 폴더 · 고객사 마스터) · 기존 제안서 활용(§6.13 `reuse`: 추천 · 분석 · 기준 · 역할 · 재분석 · 확인 · 방식 · 판정 · 확정 · 원본 대조/흐름 가이드 · 줄 끌어오기 · PRU5 요약 · 지우기).

**워크플로(`graphs/*`, 잡 `proposal.*`, LangGraph run_graph · 노드 경계 취소 · 메모)**: section_fill · edit(rewrite · request · notes) · generate · render · start(rfp_extract · links_apply) ·
imports(extract · apply) · one_click · confirm(research) · review(suggest · apply) · export · reuse(ingest → analyze → **interrupt** 분석 확인 → plan → **interrupt** 계획 확정 → apply,
큰 데이터는 `reuse` 문서 pru_). 모델 호출은 전부 `pr.*`, 과거 제안서 · RFP 는 confidential=true 고정, 403 이면 잡 실패(문구 고정, 모델 안 바꿈). 저장 전 결정적 검사 V1 · V3 · V4 · V5 · V8 · V9 · V10 + 흐름 차용 누출 검사.

**반입 · 넘김(기능별)**: mi(넘김 v1 · 사이드바 추출 · facts:lookup) · storyboard · competitor(익명, why) · vp(vho_ ack) · spec(sho_ ack · lifecycle) · birdseye · scenario(v1 섹션별 + 사용 등록/해제) ·
image(버전 · 사용 등록) · requirements(rq_ref · 링크 · 고객 질문) · kb(제품 · 사례 · 솔루션 · 이미지 · E3 메시지/사례). handoff_id 만 와도 spec · vp 는 원본 id 를 찾는다(mi · competitor 는 ref_id 필요).

**테스트**: `tests/` 26개(시작 · 구성 · 섹션 · 생성 PPTX(export in-process) · RFP · 기존 작업 · 반입 · 딸깍 · 확인 · 검토 · 버전 · 내보내기 · 기존 제안서 활용 5) — `make test SERVICE=proposal` 통과.
가짜 서비스는 `tests/pr_stubs.py`(계약 검증 통과 모양, ai-tools 기록 프록시 · task 별 오류 흉내). mock 고정 응답: `mocks/ai-tools/pr.*.json` 19개(섹션 초안 · 다듬기 · 요청 라우팅 · 노트 · 줄이기 ·
RFP · 익명 · 고객 질문 · 조사 3 · 코멘트 수정안 · 영문 · reuse 6).

**제안 · 차이(시나리오와 다른 곳)**
- 업종 감지는 kb 분류 · 세그먼트 규칙, VP 업종 가족은 아직 제작 중이라 숨김. workspace 에 없는 리뷰 마감 · 시트 확인 · 다시 요청은 제안서 문서에 둔다(요청 filed).
- export 템플릿 상세 일부가 500 이라 목록(include_slots)으로 대신 읽는다(요청 filed). PDF · PNG 는 LibreOffice 가 없으면 export 501 → 경고 · 템플릿 썸네일.
- 기존 제안서 분석은 규칙 먼저(구조 · 비복제 · 제품 · 수치 · 이미지 · 매핑 · 대조), LLM 은 비복제 확정 · 흐름 메모 · KM · 원본 고객만. 이미지 분류는 kb 재식별 없이 종류 · 권리로,
  계획(개선/차용)은 결정적 규칙(LLM `plan_improve` 안 씀). 활용 방식 바꾸기는 잡 입력 대신 계획을 바로 다시 계산한다(잡은 계획 확정만 기다림).
- 영문 내보내기는 `pr.translate_en`(mock 은 비어 한국어 유지 + 경고).

**통합(integration · 2026-10-07)** — 기능 사이 여정 e2e `web/e2e/integration/`(정리: `docs/INTEGRATION.md`)에서 고친 것
- 넘김 반입: 항목을 역할로 섹션에 나눔(`ImportItem.section_key`, BE SM → spaceProducts · SC SXS → solution), 유형에 없는 섹션이면 기능 기본 섹션(`defs.WORK_TARGETS`)으로 대체 + `requested_section`,
  include_keys 없는 넘김은 `include_default`. `hof_` 겹침은 작업 id 접두사로(`defs.feature_for_ref` — 반입 · 링크).
- 만들기: 넘긴 작업(rq_ref · links · 이미지 작업)의 workspace 항목에서 `project_id` 이어받기, `rq_ref` 면 정의서 고객 · 제목. 지우기: birdseye · scenario · image 사용 등록과 requirements 링크를 푼다.
- VP: 링크 제목 = VP 제목, ack 에 `proposal_id` · `proposal_title`. 기존 제안서 활용 `plan:confirm` 은 유형 · 섹션(filling)을 먼저 적용하고 잡에 신호.
- 웹: `lib/routes.handoffFeature`(넘김 id → 기능), `/birdseye/new?return_to=`.
