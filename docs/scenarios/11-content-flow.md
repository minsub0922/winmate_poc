# 11 · 콘텐츠 흐름(Storyboard 중심) — 수용 기준 (2026-10-08)

디자인 원본: `docs/screens/webapp1/*.dc.html`(캔버스 v58) · 그린 화면 `docs/screens/_rendered/webapp1/<보드>.jpg · .txt`.
이전 보드(v52)는 `docs/screens/_archive/webapp1-v52/` 에 있다. 아직 새 흐름으로 다시 만들지 않은 화면(MI · CA · SP · RQ · DSS · Storyboard)은
기존 수용 기준(01~09)과 이전 보드를 그대로 따르고, 아래 "단계" 순서대로 옮긴다.

## 1. 규칙(모든 콘텐츠 공통)

| 코드 | 규칙 |
|---|---|
| CF-01 | Storyboard 는 제안 흐름 전체의 context 다. 고객 요구사항을 저장하면 자동으로 생긴다. |
| CF-02 | 흐름 전체는 JSON 하나(`flow.json`)로 들고, `stages.<콘텐츠>` 에 참조뿐 아니라 그 콘텐츠의 **실제 값 전부**를 담는다. |
| CF-03 | 요약본(`summary.md`)은 연결 콘텐츠가 저장될 때마다 다시 쓴다. 사람이 고친 요약 문장은 표시해서 유지한다. |
| CF-04 | 모든 콘텐츠 화면 위에 연결된 Storyboard 바(SBBar: 이름 칩 + 진행 칸 RQ → DSS → MI · CA · VP · SP · SC)를 둔다. 칩을 누르면 요약본 팝업. |
| CF-05 | Storyboard 하나에는 콘텐츠 종류별로 하나만 연결된다. 콘텐츠 하나는 여러 Storyboard 에 연결될 수 있다. |
| CF-06 | 사전 작업은 필수다. 콘텐츠 목록 → 새로 만들기는 사전 작업 고르기(Gate)에서 Storyboard 를 고른다. 같은 종류가 이미 있으면 **수정**(연결된 모든 Storyboard 반영) 또는 **복제본 만들기**(Storyboard 분기). |
| CF-07 | Storyboard 화면에서 "만들기" 하면 Gate 를 건너뛰고 현재 Storyboard 를 가져가 새로 만들기 화면으로 간다. |
| CF-08 | AI 가 먼저 묻는 화면은 없다. AI 는 "AI 추가기능" 버튼(파란 테두리 + ✦)으로만 돌고, 결과는 **점선**으로 보이며 **수락해야** 들어간다. 예외: MI 는 Storyboard 분석 로딩이 먼저 나온다. |
| CF-09 | 저장하면 완료 화면(Done): 요약본에 더해진 부분 + `flow.json` 에 더해진 블록(`stages.<콘텐츠>`, 접힌 JSON: 긴 배열은 첫 항목 + "… n개 더") + "전체 JSON 보기"(추가 · 바뀐 줄 강조) + 후속 작업. |
| CF-10 | 출처 표시 `by`: `manual`(직접) · `ai-accepted`(AI 추천 · 수락) · `ai-pending`(점선) · `ai-candidate-A`(AI 3안 수락) · `ai-web`. |
| CF-11 | 근거 없는 사실 · 수치는 만들지 않는다 — `[확인 필요]` · `[위키 값]` · `[견적 확인]` · `[00]`. |

## 2. Value Proposition — 보드 VP2 · VP2_AI · VP2_Pick · VP2_Detail · VP_Done · VP_DoneJson · VpDetail · ProdPicker

API `contracts/vp.json` `/v1/value-maps*` · 화면 `web/src/features/vp/values/` · 라우트 `/vp/values/new` · `/vp/values/:id`.

| 코드 | 기준 |
|---|---|
| VP-N-01 | 왼쪽 280px 패널: 고른 제품 · 솔루션(종류 태그 · `가치 n · 니즈 m/n` · 가치 없음은 주황). 오른쪽 1fr: 고른 항목의 가치 카드 여러 개. |
| VP-N-02 | 가치 카드 = 공간 칩 · 출처 태그 · 연결 요구(파란 칩) · 가치 메시지 · 고객의 니즈 줄. 니즈는 고객이 할 말처럼("여름에도 쾌적한 교실 환경이 필요해요"). |
| VP-N-03 | 니즈가 비면 입력칸 + "AI 니즈 추론"(`vp.need_infer.v1`). 결과는 점선 · "수락/빼기". 모델이 못 쓰면 빈 값(지어내지 않음). |
| VP-N-04 | "AI 가치 매칭 추천"(`vp.values_suggest.v1`): 빈 곳에 가치 후보(니즈 포함)를 점선으로. 모델이 없으면 KB E1 원문 메시지를 니즈 없는 후보로(`mode=kb_only`). "모두 수락" 가능. |
| VP-N-05 | "제품 · 솔루션 고르기 · n"(ProdPicker 760×640): DSS 제품 · 솔루션 + KB 카탈로그 검색 + "직접 추가 · KB 에 없음 · 확인 필요". |
| VP-N-06 | "연결된 가치 전체 보기"(VpDetail 900×720): 이 제안 · 같은 제품을 쓴 다른 제안(가져오기 → 복사) · 삼성 공식 메시지(KB 원문, 출처 링크). 공간 칩으로 거른다. |
| VP-N-07 | 저장 → Done: `stages.vp = {ref, ver, from, selection{fromDss, excluded, addedOutsideDss}, items[{name, kind, spaces, values[{id, space, message, need{text,by}|null, req, by}]}], importedFrom, counts}`. 점선(대기) 값은 저장에 안 들어간다. |

## 3. 공간 시나리오 — 보드 SC2 · SC2_AI · SC2_Pick · SC2_Empty · SC_Done · SC_DoneJson

API `contracts/scenario.json` `/v1/space-sets*` · 화면 `web/src/features/scenario/spaces/` · 라우트 `/scenario/spaces/new` · `/scenario/spaces/:id`.

| 코드 | 기준 |
|---|---|
| SC-N-01 | 3단: 공간 `196px` → 나머지 `1fr` 안에 시나리오 목록 `236px` + 편집 `1fr`. 공간 위에 공간 제품 칩 줄 + "+ 추가 · 변경"(ProdPicker). |
| SC-N-02 | 공간마다 제품 · 솔루션이 1개 이상. 없으면 공간 목록에 주황 표시 + SC2_Empty 안내, 저장 422 `SPACE_WITHOUT_PRODUCT`. |
| SC-N-03 | 시나리오는 공간마다 여러 개. 이름 · 사용자 · 이 시나리오의 제품(공간 제품 중 1개 이상, 없으면 422 `SCENARIO_WITHOUT_PRODUCT`) · 장면 흐름. |
| SC-N-04 | 입력 폼은 고정하지 않는다: 단계 수 자유, 단계마다 "쓰인 제품" 선택, 항목(시간대 · 기대 효과 · 연결 요구 · 페인 포인트 · 직접 이름 짓기)은 필요할 때만 더한다. |
| SC-N-05 | "AI 시나리오 3안"(`sc.space_candidates.v1` + KB D1 사례): 목록에 점선 후보 A/B/C. 수락 전에도 고칠 수 있고, 수락해야 시나리오가 된다. 모델이 없으면 KB 사례 틀 + `[확인 필요]`(`mode=kb_only`). |
| SC-N-06 | 자동 저장(600ms, `expected_version` 409). 저장 → Done: `stages.sc = {ref, ver, from, spaces[{name, products, scenarios[{id, title, user, products, steps[{text, product}], fields[{k,v}], by}]}], rules{minProductsPerSpace:1, minProductsPerScenario:1}, counts}`. |

## 4. 화면 폭 · 동적 폭 (모든 화면)

| 코드 | 기준 |
|---|---|
| UI-W-01 | 본문 열은 `--wm-main-w`(1180px) 가운데 정렬. 셸 규칙 `:where(.sh-content) > :where(*)` 이 처리한다 — 화면에서 따로 max-width 를 주지 않는다. |
| UI-W-02 | 보드의 고정 칸(280 · 196 · 236 · 900×720 팝업 등)은 px 그대로, 나머지는 `1fr` · `minmax(0,1fr)`. 보드 `.txt` 의 px 를 숫자로 옮긴다(반올림 · 임의 rem 금지). |
| UI-W-03 | 작업 화면(VP2 · SC2)은 높이를 채운다: 헤더 · 바 · 푸터를 뺀 높이를 그리드가 갖고, 패널 안에서만 스크롤. |
| UI-W-04 | 1440 · 1920 폭에서 e2e 가 폭을 잰다(`values.spec.ts`: 왼쪽 280 · 본문 1180). 새 화면도 같은 방식으로 재고 `__screens__/` 캡처를 `_rendered` 와 나란히 본다. |

## 5. 단계(남은 이전 작업)

| 단계 | 할 일 | 서비스 |
|---|---|---|
| 1 | Storyboard `flow.json` · `summary.md` 저장소 + `stages.*` 반영 API(VP · SC 의 `:finish` 결과 `stage` 를 받아 씀) + SBBar 칩의 실제 진행 칸 | storyboard |
| 2 | Gate(사전 작업 고르기) · 수정/복제본 분기 · Storyboard 에서 바로 만들기 | storyboard + 각 기능 |
| 3 | 완료 화면 공통(Done · JsonPopup) — `@/ui` `FlowDone` 을 각 기능이 쓴다 | 각 기능 |
| 4 | DSS(업종 · 공간 · 공간별 제품 → 솔루션) 새 화면 DS0~DS4 | dss(신규) 또는 requirements |
| 5 | MI(분석 로딩 → 검색 → 정제) · CA(개요 · 비교 · 장단점 탭) · SP · RQ 새 화면 | mi · competitor · spec · requirements |
