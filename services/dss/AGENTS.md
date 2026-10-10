# dss 서비스 — 개발 세션 규칙

공간별 제품 매칭 DSS — 업종 · 공간 · 공간별 제품 · 솔루션(새 콘텐츠 흐름, Storyboard 사전 작업)

- 포트: **5111** · 게이트웨이 경로: `/api/dss/v1/...` · 파이썬 모듈: `winmate_dss`
- 고칠 수 있는 경로(owns): `services/dss/**`, `web/src/features/dss/**`
- 호출할 수 있는 서비스(consumes): `ai-tools`, `kb`, `workspace`, `storyboard`

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=dss          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=dss         # 이 서비스 테스트
make contracts SERVICE=dss    # contracts/dss.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("dss", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("dss")`(data/dss/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=dss` 를 돌리고 `contracts/dss.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태

### 새 흐름(2026-10-08 · 보드 webapp1 v58 DS0 · DS1 · DS2 · DS2_AI · DS4 · DS4_AI · DS_Done)
수용 기준 `docs/scenarios/11-content-flow.md` §1 · §4 · §6. Storyboard(고객 요구사항까지) → 업종 · 공간 · 공간별 제품 → 솔루션(0개 이상) → 저장하면 허브 `stages.dss`.

**API**(`contracts/dss.json` · 본체 `src/winmate_dss/dss.py`, 저장소 DocStore `dss`, 쓰기는 낙관적 잠금 · `expected_version` 이면 409)
| 경로 | 하는 일 |
|---|---|
| `GET/POST /v1/dss` | 목록(보드 List 초안 줄) · 만들기 `{sb_id}` — `get_flow` 로 rq 요구 문장을 문맥으로(없으면 404 · rq 없으면 422 `PREREQUISITE_MISSING`). 번호 `DSS-nn` 은 허브 ref 와 겹치지 않게. **같은 Storyboard 의 저장 전 초안이 있으면 그 초안을 200 으로**(새로 만들면 201 · Gate 를 다시 거쳐도 초안이 늘지 않음 · 같은 Storyboard 동시 만들기는 잠금). 복제본은 분기 Storyboard 라 새 DSS |
| `GET /v1/dss/{id}` | 한 건. 허브에만 있는 DSS(`DSS-<영숫자>` = 허브 ref)는 그 `stages.dss` 로 편집본을 만들어 준다(Gate 「수정」 · 목록 「열기」) |
| `DELETE /v1/dss/{id}` | 저장 전 초안 지우기 204(소프트 삭제 + `unregister_item`) — 저장한 것(status done · ver · 허브에서 가져온 것)은 409 `SAVED_CONTENT` 「저장한 콘텐츠는 Storyboard에 연결돼 있어 지울 수 없어요」 · `?expected_version=` 다르면 409 VERSION_CONFLICT · 없으면 404 |
| `PUT …/industry` | 업종 고르기 `{value}` · AI 추론 적용 `{accept_ai: true}` |
| `POST/PATCH/DELETE …/spaces[/{key}]` | 공간 넣기(추천에 있던 이름이면 ai-accepted · 근거 유지, 직접 넣으면 이름 낱말이 모두 나오는 요구 문장을 근거로 — 없으면 null) · 이름 · 빼기 |
| `GET …/spaces/{key}/candidates` | 이 공간의 KB S1 후보 제품군(제품 고르기 팝업 「KB 추천」) |
| `POST …/spaces/{key}/products` · `PATCH/DELETE …/products/{pid}` | 제품 넣기(KB ref 또는 직접 = 「KB 에 없음 · 확인 필요」) · 수량(빈 값 → `[확인 필요]`) · 수락 · 빼기(추천 거절) |
| `POST …:accept-all` | 공간별 제품 추천 모두 수락 |
| `PUT …/solutions` · `GET …/solution-options` | 고른 솔루션(카탈로그 id) · 카드(관련 높은 순 · 함께 쓰는 제품 · AI 추천 · `relevant` · 겹침 안내 `overlap`) |
| `POST …:suggest {scope}` | AI 추가기능(점선 → 수락): industry · spaces · products(`ds.industry_spaces.v1`) · solutions(`ds.solutions.v1`). 모델이 없거나 빈 답이면 KB 로 결정적(`mode=kb_only`) |
| `POST …:finish` · `GET …/stage` | 저장 → `push_stage(sb, "dss", ref=DSS-nn, ver=저장 횟수, value=§6, md, card)` · `register_item(DS, /dss/{id})`. 공간 · 제품(수락한 것)이 없으면 422 |

**웹**(`web/src/features/dss/`, CSS `dss.css` 접두어 `ds-`, 보드 인라인 px 그대로)
- `/dss` DS0 = 셸 `ContentListScreen`(초안 = `GET /v1/dss` 의 draft, 줄마다 `onDelete` — 손을 올리면 × · 확인 → `useDsDelete` → 목록 · 사이드바 색인 새로) ·
  `/dss/new` DS1 = 셸 `GateScreen`(`?sb=&auto=1` 이면 바로 만든다 · 서버가 기존 초안을 돌려주면(200) 「작성 중이던 DSS-nn 초안을 이어서 열어요」 알림)
- `/dss/:id` DS2(`SpacesStep.tsx`): 머리(업종 220 목록 · AI 업종 추론 → 점선 줄 「적용」) · 공간 270 | 제품 1fr(직접 · AI 추천 점선 → 수락 · 추천 모두 수락 · 수량 눌러 고치기 · 상세 = 셸 제품 시트 · 빼기) ·
  제품 검색 줄(결과는 위로) · 「제품 탐색에서 고르기」= `ProductPickerDialog`(KB 추천 + 카탈로그 + 직접) · 공간 빼기는 손을 올리면 ×
- `?step=solution` DS4(`SolutionsStep.tsx`): 카드 2열(940 · 465) · AI 솔루션 추천(점선 · 근거) · 겹침 안내 · 상세 = 셸 솔루션 시트 · 관련 없는 것은 「솔루션 n개 더 보기」
- 저장 → DS_Done = 셸 `FlowDoneView`(stages.dss 접힘 · 전체 JSON) + 후속 작업 공간 시나리오 · Spec 시트(`/scenario/new?sb=&auto=1` · `/spec/new?sb=&auto=1`)
- 셸 상세 시트 · 팝오버의 「현재 작업에 추가」: 제품 → 지금 고른 공간, 솔루션 → 고른 솔루션(`shellcfg.ts`)

**테스트**: `make test SERVICE=dss` 12개(허브 연동 · AI mock · KB 대체 · 겹침 · 저장 · 허브 가져오기 · 같은 Storyboard 초안 다시 쓰기 · 지우기) · e2e `web/e2e/dss/dss-flow.spec.ts` 2개(`make e2e-feature SERVICE=dss`, 캡처 `web/e2e/dss/__screens__/<보드>-new.png`) ·
`dss-draft.spec.ts` 1개(Gate 다시 시작 = 같은 초안 → 목록 × → 확인 → 빠짐 → 다시 시작 = 새 초안, 캡처 `DS0-draft-delete.png`)
