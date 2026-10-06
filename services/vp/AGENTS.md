# vp 서비스 — 개발 세션 규칙

Value Proposition — 재료 수집 · 메시지 · 레이아웃 · 이미지 슬롯 · 수치

- 포트: **5105** · 게이트웨이 경로: `/api/vp/v1/...` · 파이썬 모듈: `winmate_vp`
- 고칠 수 있는 경로(owns): `services/vp/**`, `web/src/features/vp/**`
- 호출할 수 있는 서비스(consumes): `ai-tools`, `kb`, `files`, `jobs`, `workspace`, `export`, `requirements`, `storyboard`, `mi`
- 화면 수용 기준: `docs/scenarios/05-vp.md` · 원본 보드: `docs/screens/` (INDEX.md)

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=vp          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=vp         # 이 서비스 테스트
make contracts SERVICE=vp    # contracts/vp.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("vp", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("vp")`(data/vp/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=vp` 를 돌리고 `contracts/vp.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태
- **완성(1차)** — 05-vp 의 화면 13(VP0 · VPR · VP1 · VP1A · VP1Q · VP2 · VP3G · VP3 · VP3L · VP3N · VPI · VP4 + `/vp/:id` 이어 열기) · API 48 경로 · 잡 6종.
- 코드 지도(`src/winmate_vp/`): `api.py`(라우트 · 202 잡) · `models.py`(요청/응답) · `service.py`(문서 · 파생 값 · 저장 지점 · 플랜) · `ops_work.py`(작업 · 재료 · 되묻기 · 플랜)
  · `ops_result.py`(결과 다듬기 · 수치 · 이미지 · 내보내기 · 넘김 · 업종판) · `workflows.py`(LangGraph: `vp.materials` · `vp.generate` · `vp.revise` · `vp.images` · `vp.export` · `vp.pack_offer`)
  · `collect.py`(첨부 읽기 · 추출 · 합침 · 다시 찾기 · 수치 채우기 · 되물을 것) · `writer.py`(시트 글 — LLM + 결정적 대체) · `guards.py`(근거 없는 숫자 `[00]` · 경쟁사 · 주장)
  · `planner.py` · `decide.py` · `fit.py` · `catalog.py`(레이아웃 83 · 업종판) · `imagesel.py`(KB G1~G5 → 일러스트) · `exporting.py`(export 문서) · `scenarios.py`(VPC 12 골든) · `views.py`(화면 문장).
- 설정: `config/routing.yaml`(VPR 단일 원천 · 임계값 · 방향 낱말 · `dev.pace_s`) · `config/layouts.yaml`. mock 고정 응답: `mocks/ai-tools/vp.*.json`(17 — 비어 있으면 결정적 경로).
- 테스트: `tests/` 30개(API · 워크플로 HITL · 중지/재시도 · 403 기밀 · 503 대체 · 업종판 · VPC 12 + 통계). e2e `web/e2e/vp/`(flow · branches) · 화면 `web/e2e/vp/__screens__/`.

### 정한 것(결정 기록)
- 작업 = JSON 문서 하나(`vp` 컬렉션) + 저장 지점(`versions`) · 넘김(`handoffs`) · 내보내기 기록. API `version` = 문서 판(doc_version).
- 업종 판별은 MI `POST /v1/segments/detect`(같은 판별기), 실패 시 KB 대체. 사용자가 고르면 `pin`, MI/SB 상속은 그대로.
- 모든 LLM 단계는 결정적 대체가 있다(mock 빈 응답 · `[mock` 값 · 503/504 → 대체). `POLICY_CONFIDENTIAL` 만 잡 오류로 올린다.
  task 이름 `vp.<동작>.v1`, T2I `vp.illustration`, 웹 검색 `vp.refetch_source`. 프롬프트에는 재료 이름(handle: `RFP-C1` · `N1`)만 쓴다.
- 재료 잡은 열린 질문(선택 필요 · 확인 권장)이 있으면 `awaiting_input` 으로 멈춘다(`auto_answer` 면 기본값). 결재자 질문은 결재자 재료도 RFP 도 없을 때만.
- 메모의 우선순위 지시(`비용 절감이 1순위`)는 방향을 고정(결정 기록 `고정`), 메모 글은 방향 점수에 USER 0.5 로 들어간다.
- RFP 문장은 칩 길이로 줄여 재료로(원문은 quote), RFP 수치는 근거 재료로, 규모 · 날짜 · 제품 스펙 수치는 기대 효과 지표로 쓰지 않는다.
- RFP `바라는 모습` → 가치 축 · CH-B 오른쪽 칸. 제품이 없으면 KB E3 제안 제품(확인 권장 `제안 제품 확인`).
- 레이아웃 요청: 기둥 수 변경 등으로 내용이 빠지면 선택지 A(요약 시트 추가) · B(바꾸고 노트로) · C(그대로) — 적합도 최고(동점 A>B>C)를 추천.
- 중지 → 끝난 시트 보존 · `stopped` · VP2. 실패 → `failed` · `다시 시도`(끝난 시트 건너뜀).
- 넘김: `GET /v1/handoffs/{vho}`(브라우저도 읽음) · `POST /v1/handoffs/{vho}:ack`(internal) · `proposal-handoff` 두 경로 · `POST /v1/value-props:draft`(internal).
- 웹: 작업 고르기 대화상자 · VPR 시트는 키트에 없어 기능 쪽 구현(docs/requests/workspace.md). `/vp/new?sb=|mi=|rq=|proposal=&type=&title=` 진입.
- `VP_PACE_S`(시연용 단계 쉬는 시간, 기본 0). `layouts` 응답은 `{items, counts}`(스펙은 배열).

### 남은 것 · 알려진 한계
- 보드 예시 수치 그대로 맞추는 픽스처(VP0 6행 · VP3 메타 · VP1A 14재료)는 `when` mock 을 쓰지 않아 결정적 결과와 다를 수 있다.
- 업종판 템플릿(export `VP-FB-*`)이 준비 안 됐으면 범용 코드로 내보낸다. 화면 문구 스냅샷 테스트(AC 72) · 300ms 성능 측정(AC 71)은 없음.

### 통합(integration · 2026-10-07)
- 새 internal `POST /v1/vps/{vp_id}:release-proposal {proposal_id}` — 제안서를 지우면 proposal 이 불러 VP0 「연결된 제안서」 · 보낼 제안서를 거둔다(다른 제안서 넘김이 있으면 가장 최근 것으로). pytest 30.
- `exporting._template_ready` 는 export 호출 실패를 기억하지 않는다(export 상세 500 이 고쳐지면 재시작 없이 반영). VP4 「공간 시나리오」는 scenario SC1 이 가치 · 과제 · 제품을 입력으로 받는다.
