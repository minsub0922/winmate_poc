# 11 · 콘텐츠 흐름(Storyboard 중심) — 수용 기준 (2026-10-08)

디자인 원본: `docs/screens/webapp1/*.dc.html`(캔버스 v62 — 상세 = 최종본 한 장 + 단계 팝업) · 그린 화면 `docs/screens/_rendered/webapp1/<보드>.jpg · .txt`.
이전 보드(v52)는 `docs/screens/_archive/webapp1-v52/` 에 있다. 2026-10-10 에 웹앱 ① 의 모든 콘텐츠를 새 흐름으로 옮겼다(§5). 이전 흐름 화면은 `/<base>/legacy` 아래에 남아 있고,
그 화면의 수용 기준은 기존 문서(01~09)다.

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
| CF-09 | 완료 화면은 없다(2026-10-12 · 보드 v60~). 저장 · 목록 · 작업 내역 모두 그 콘텐츠의 **최종본**(보드 View · `*_View`)으로 열린다 — 머리(이름 · `REF vN` · 저장 시각 · 수) · 콘텐츠 그 자체 · flow.json 팝업(이 콘텐츠 줄 강조) · 후속 작업(있는 콘텐츠만, 이미 있으면 ref + 「열기」). 고치기는 별도 편집 화면(`?edit=1`)이 아니라 머리의 단계 칩 → 단계 팝업(CF-12). |
| CF-10 | 출처 표시 `by`: `manual`(직접) · `ai-accepted`(AI 추천 · 수락) · `ai-pending`(점선) · `ai-candidate-A`(AI 3안 수락) · `ai-web`. |
| CF-11 | 근거 없는 사실 · 수치는 만들지 않는다 — `[확인 필요]` · `[위키 값]` · `[견적 확인]` · `[00]`. |
| CF-12 | **상세에는 페이지 이동이 없다(보드 v62).** 상세는 늘 최종본 한 장이고, 단계 화면(① Gate · 입력 · 공간 · 제품 · 솔루션 · 검색 · 정제 · 리스트업 · 가치 · 시트 · 시나리오)은 그 위 **단계 팝업**(1180×800 · 머리 StepHead: 이름 · 새로 만들기 / `REF vN 고치기` · 연결 Storyboard 칩 · 안내 · 단계 n/N · 단계 칩 · ×)이다. 주소는 `?step=<키>` 만 바뀐다. 새로 만들기 = 빈 최종본(칸마다 자리표시) + 1단계 팝업 → 「다음」은 팝업 안에서 → 마지막 저장이면 팝업이 닫히고 최종본이 채워진다. 중간에 닫으면 작성 중(채운 칸 + 다음 칸 「이어서 · 단계」) · 고르기 전에 닫으면 목록. 작성 중을 열면 이어서 할 단계 팝업이 열린 채로(처음 한 번). 저장된 것은 머리의 단계 칩(「단계별 고치기」)으로 그 단계 팝업만 연다(「저장 · vN+1」 · 이전 단계 링크 없음 · 고친 뒤 닫으면 「계속 고치기 · 저장하지 않고 닫기 · 저장 · vN+1」). 사전 작업(Storyboard)은 만든 뒤 바꾸지 않는다(칩 = 요약 팝업). 팝업 안 상세 시트 · 제품 고르기 · 확인창은 그 위에 겹치고, Esc 는 맨 위 것만 닫는다. |

## 2. Value Proposition — 보드 VP2 · VP2_AI · VP2_Pick · VP2_Detail · VP_View · VpDetail · ProdPicker

API `contracts/vp.json` `/v1/value-maps*` · 화면 `web/src/features/vp/values/` · 라우트 `/vp/values/new` · `/vp/values/:id`.

| 코드 | 기준 |
|---|---|
| VP-N-01 | 왼쪽 280px 패널: 고른 제품 · 솔루션(종류 태그 · `가치 n · 니즈 m/n` · 가치 없음은 주황). 오른쪽 1fr: 고른 항목의 가치 카드 여러 개. |
| VP-N-02 | 가치 카드 = 공간 칩 · 출처 태그 · 연결 요구(파란 칩) · 가치 메시지 · 고객의 니즈 줄. 니즈는 고객이 할 말처럼("여름에도 쾌적한 교실 환경이 필요해요"). |
| VP-N-03 | 니즈가 비면 입력칸 + "AI 니즈 추론"(`vp.need_infer.v1`). 결과는 점선 · "수락/빼기". 모델이 못 쓰면 빈 값(지어내지 않음). |
| VP-N-04 | "AI 가치 매칭 추천"(`vp.values_suggest.v1`): 빈 곳에 가치 후보(니즈 포함)를 점선으로. 모델이 없으면 KB E1 원문 메시지를 니즈 없는 후보로(`mode=kb_only`). "모두 수락" 가능. |
| VP-N-05 | "제품 · 솔루션 고르기 · n"(ProdPicker 760×640): DSS 제품 · 솔루션 + KB 카탈로그 검색 + "직접 추가 · KB 에 없음 · 확인 필요". |
| VP-N-06 | "연결된 가치 전체 보기"(VpDetail 900×720): 이 제안 · 같은 제품을 쓴 다른 제안(가져오기 → 복사) · 삼성 공식 메시지(KB 원문, 출처 링크). 공간 칩으로 거른다. |
| VP-N-07 | 저장 → 보기(VP_View): `stages.vp = {ref, ver, from, selection{fromDss, excluded, addedOutsideDss}, items[{name, kind, spaces, values[{id, space, message, need{text,by}|null, req, by}]}], importedFrom, counts}`. 점선(대기) 값은 저장에 안 들어간다. |

## 3. 공간 시나리오 — 보드 SC2 · SC2_AI · SC2_Pick · SC2_Empty · SC_View

API `contracts/scenario.json` `/v1/space-sets*` · 화면 `web/src/features/scenario/spaces/` · 라우트 `/scenario/spaces/new` · `/scenario/spaces/:id`.

| 코드 | 기준 |
|---|---|
| SC-N-01 | 3단: 공간 `196px` → 나머지 `1fr` 안에 시나리오 목록 `236px` + 편집 `1fr`. 공간 위에 공간 제품 칩 줄 + "+ 추가 · 변경"(ProdPicker). |
| SC-N-02 | 공간마다 제품 · 솔루션이 1개 이상. 없으면 공간 목록에 주황 표시 + SC2_Empty 안내, 저장 422 `SPACE_WITHOUT_PRODUCT`. |
| SC-N-03 | 시나리오는 공간마다 여러 개. 이름 · 사용자 · 이 시나리오의 제품(공간 제품 중 1개 이상, 없으면 422 `SCENARIO_WITHOUT_PRODUCT`) · 장면 흐름. |
| SC-N-04 | 입력 폼은 고정하지 않는다: 단계 수 자유, 단계마다 "쓰인 제품" 선택, 항목(시간대 · 기대 효과 · 연결 요구 · 페인 포인트 · 직접 이름 짓기)은 필요할 때만 더한다. |
| SC-N-05 | "AI 시나리오 3안"(`sc.space_candidates.v1` + KB D1 사례): 목록에 점선 후보 A/B/C. 수락 전에도 고칠 수 있고, 수락해야 시나리오가 된다. 모델이 없으면 KB 사례 틀 + `[확인 필요]`(`mode=kb_only`). |
| SC-N-06 | 자동 저장(600ms, `expected_version` 409). 저장 → 보기(SC_View): `stages.sc = {ref, ver, from, spaces[{name, products, scenarios[{id, title, user, products, steps[{text, product}], fields[{k,v}], by}]}], rules{minProductsPerSpace:1, minProductsPerScenario:1}, counts}`. |

## 4. 화면 폭 · 동적 폭 (모든 화면)

| 코드 | 기준 |
|---|---|
| UI-W-01 | 본문 열은 `--wm-main-w`(1180px) 가운데 정렬. 셸 규칙 `:where(.sh-content) > :where(*)` 이 처리한다 — 화면에서 따로 max-width 를 주지 않는다. |
| UI-W-02 | 보드의 고정 칸(280 · 196 · 236 · 900×720 팝업 등)은 px 그대로, 나머지는 `1fr` · `minmax(0,1fr)`. 보드 `.txt` 의 px 를 숫자로 옮긴다(반올림 · 임의 rem 금지). |
| UI-W-03 | 작업 화면(VP2 · SC2)은 높이를 채운다: 헤더 · 바 · 푸터를 뺀 높이를 그리드가 갖고, 패널 안에서만 스크롤. |
| UI-W-04 | 1440 · 1920 폭에서 e2e 가 폭을 잰다(`values.spec.ts`: 왼쪽 280 · 본문 1180). 새 화면도 같은 방식으로 재고 `__screens__/` 캡처를 `_rendered` 와 나란히 본다. |

## 5-0. 상세 = 최종본 + 단계 팝업(2026-10-12 · 보드 v62)

| 콘텐츠 | 새로 만들기 | 최종본 · 팝업 단계(`?step=`) | 최종본 본문 | e2e |
|---|---|---|---|---|
| 고객 요구사항 | `/requirements/new`(첫 입력에 문서가 생기면 `/requirements/flow/:id?step=input` 로 바꿔치기) | `/requirements/flow/:id` · `input` | `RqView.tsx` | `requirements/rq-flow` · `rq-draft` |
| DSS | `/dss/new` | `/dss/:id` · `space` · `solution` | `DsView.tsx` | `dss/dss-flow` · `dss-draft` |
| MI | `/mi/new` | `/mi/flow/:id` · `search`(분석 로딩 → 검색어) · `refine` | `MiView.tsx` | `mi/mi-flow` · `mi-draft` |
| 경쟁사 분석 | `/competitor/new` | `/competitor/flow/:id` · `list`(`&tab=info\|pc`) | `CaView.tsx` | `competitor/ca-flow` · `ca-draft` |
| VP | `/vp/new` | `/vp/values/:id` · `values` | `VpView.tsx` | `vp/values` · `vp-resync` |
| Spec 시트 | `/spec/new` | `/spec/flow/:id` · `sheet`(최종본 머리 「XLSX 내려받기」) | `SpView.tsx` | `spec/sp-flow` · `sp-resync` |
| 공간 시나리오 | `/scenario/new` | `/scenario/spaces/:id` · `spaces` | `ScView.tsx` | `scenario/sc-flow` · `sc-resync` · `spaces` |

- 공용(`@/shell` flow/detail.tsx): `ContentDetail`(최종본 틀 · 머리 단계 칩 · flow.json · 후속 작업) · `StepModal`(팝업 · 안의 FlowScreen 은 SB 바 없음 · useShellPage 는 작업 추가 맥락만 얹음) · `StepSlot` · `DetailFollow` · `useStepParam` · `useEditGuard` · `useCloseAsk`. `GateScreen` 은 팝업 안이면 「목록」 링크를 숨기고 `openStep` 으로 「수정」 · 초안을 그 단계 팝업으로 연다.
- 저장 여부: 콘텐츠마다 `status === 'done'` 또는 `ver` 있음. 저장 시각은 허브 기록 · `saved_at` 을 먼저 본다(편집 중 자동 저장이 `updated_at` 을 바꾼다).
- 아래 §5 표의 `*_Done` 보드 · FlowDoneView 는 새 흐름에서 쓰지 않는다(이전 기록).

## 5. 구현 현황 (2026-10-10 — 웹앱 ① v58 전부)

모든 콘텐츠가 허브(§6)에 붙었다. 화면은 보드 인라인 px 그대로이고, e2e 가 고정 칸 폭을 숫자로 잰다(`web/e2e/<기능>/<기능>-flow.spec.ts`, 캡처 `__screens__/<보드>-new.png`).

| 콘텐츠 | 보드 | 목록 · 새로 · 편집 | 백엔드(새 자원) | e2e |
|---|---|---|---|---|
| 홈 | HomeGrid | `/` — 시작 · 흐름 3 · Storyboard로 만드는 콘텐츠 5 · 비주얼 2 · 최근 작업 2 | — | `shell/layout.spec.ts` H-* |
| 고객 요구사항 | RQ0 · RQ1 · RQ_View | `/requirements` · `/requirements/new`(바로 RQ1) · `/requirements/flow/:id`(최종본 · `?step=input` RQ1 팝업) | requirements `/v1/rq-flows*` — 첫 저장에 Storyboard 자동 생성 | `requirements/rq-flow.spec.ts` |
| Storyboard | SB0 · SB1 · SB1_Json · SB1_View · SB1_Strat · SB1_StratAI | `/storyboard` · `/storyboard/flow/:id` | storyboard `/v1/flows*`(허브) | `storyboard/sb-flow.spec.ts` |
| DSS | DS0 · DS1 · DS2 · DS2_AI · DS4 · DS4_AI · DS_View · DS_ViewJson | `/dss` · `/dss/new` · `/dss/:id`(최종본 · `?step=space` DS2 팝업 · `?step=solution` DS4 팝업) | dss(신규 서비스, 5111) `/v1/dss*` | `dss/dss-flow.spec.ts` |
| MI | MI0 · MI1 · MI1_Branch · MI2_Loading · MI2 · MI3 · MI_View | `/mi` · `/mi/new` · `/mi/flow/:id`(최종본 · `?step=search` MI2 · `?step=refine` MI3 팝업) | mi `/v1/mi-flows*` | `mi/mi-flow.spec.ts` |
| 경쟁사 분석 | CA0 · CA1 · CA2 · CA2_Info · CA2_Pc · CA2_AI · CA_View | `/competitor` · `/competitor/new` · `/competitor/flow/:id`(최종본 · `?step=list` CA2 팝업 · `&tab=info\|pc`) | competitor `/v1/ca-flows*` | `competitor/ca-flow.spec.ts` |
| VP | VP0 · VP1 · VP2 · VP2_AI · VP2_Pick · VP2_Detail · VP_View | `/vp` · `/vp/new` · `/vp/values/:id`(최종본 · `?step=values` VP2 팝업) | vp `/v1/value-maps*` | `vp/values.spec.ts` |
| Spec 시트 | SP0 · SP1 · SP2 · SP_View | `/spec` · `/spec/new` · `/spec/flow/:id`(최종본 · XLSX 내려받기 · `?step=sheet` SP2 팝업) | spec `/v1/spec-flows*`(저장 때 XLSX 도 만든다) | `spec/sp-flow.spec.ts` |
| 공간 시나리오 | SC0 · SC1 · SC2 · SC2_AI · SC2_Pick · SC2_Empty · SC_View | `/scenario` · `/scenario/new` · `/scenario/spaces/:id`(최종본 · `?step=spaces` SC2 팝업) | scenario `/v1/space-sets*`(DSS 공간 · 제품으로 미리 채움) | `scenario/sc-flow.spec.ts` |

- **고객 요구사항의 AI 심층 질의(폼 개선 과정 · 보드 RQ1_AI)는 2026-10-12 에 뺐다**(아티팩트 v59 · `deep-questions` API · `rq.deep_questions.v1` 도 없음) — RQ1 은 폼 입력 · 파일로 채우기 · 저장만. 확인 필요 표시는 사람이 요구 줄의 「확인 필요」로 단다.
- **목록 v61(2026-10-12 · 보드 List · SB0)**: 7개 콘텐츠 목록과 Storyboard 목록은 같은 틀이다.
  머리(이름 · 설명 · 사전 / 후속) 아래 22 에 **본문 폭 전체 · 가운데 「새 ○○ 만들기」**(1100×156 · 브랜드 바탕 · 아래 줄에 그 콘텐츠의 단계 흐름 ① → ② → ③ · 「모두 N단계」),
  그 아래 44 에 「작업 내역 n」, 16 아래 **그리드 카드 260 × 4(간격 20)**. 카드 = 썸네일 258×148(회색 바탕 위 흰 문서 — 허브가 가진 그 콘텐츠의 보기 팝업 카드
  `card{facts, groups}` 를 472 폭으로 그려 반으로 줄인 것 · 오른쪽 아래 「완성」/「작성 중」) · 제목(2줄) · 코드 · 수정 시각 · **n/N 단계**(막대 N칸: 지난 · 지금 · 남은)
  · 연결된 Storyboard 첫 칩 + 「+n」. 저장한 것은 N/N 「완성」, 저장 전 초안은 지금 단계 — 사전 작업이 있는 콘텐츠는 2(Storyboard 를 골랐으니), DSS 는 솔루션을 골랐으면 3,
  MI 는 정제(`phase=refine`) 중이면 3, 요구사항 초안은 1(`DraftRow.step`). 카드가 없는 저장분 · 초안은 빈 틀 썸네일. 최근 수정 순, 빈 목록은 점선 안내(범례 없음).
  Storyboard 목록(SB0)은 「새 고객 요구사항으로 시작」 · 카드 썸네일 = 진행 8칸 + 요약본 앞 줄(`FlowListItem.summary_head`) · **n/8 단계**(입력된 칸 수 · 막대 8칸) · Key message.
  공용 부품 `@/shell` `ListHero` · `HistoryHead` · `SegLegend` · `StepMeter` · `ThumbFrame` · `CardMini`(`web/src/shell/flow/list.tsx`), e2e `shell/content-list.spec.ts`.
- 새로 만들기 `/<base>/new?sb=<id>&auto=1` 은 Gate 를 건너뛴다(Storyboard 「만들기」 · 보기의 후속 작업 「만들기」).
- **보기 ↔ 편집**: 2026-10-12 오전의 `?edit=1` 편집 화면(`editRoute` · `useEditMode` · `FlowContentView`)은 같은 날 v62 에서 **최종본 + 단계 팝업(CF-12 · §5-0)** 으로 바뀌었다. ContentPopup 「콘텐츠 열기 · 단계별로 고치기」는 최종본을 열고, Gate 「수정하기」는 `openStep` 으로 그 단계 팝업을 연다.
  보기 본문은 각 기능 문서에서 그린다(`<X>View` — RqView · DsView · MiView · CaView · VpView · SpView · ScView). MI 를 고쳐 쓰는 중(저장 안 함)에도 최종본은 허브의 마지막 저장본을 보여 준다.
- **이전 흐름**은 `/<base>/legacy` · `/<base>/legacy/new` 로 옮겼다. 이전 흐름의 다른 경로(`/<base>/:id/...`)는 그대로다(제안서 handoff 가 읽는다).
  예전 들어오기 주소(`/vp/new?sb=sb_…` · `?mi=` · `?rq=`, `/mi/new?rq=`, `/competitor/new?input=…`, `/spec/new?models=|from=|pop=`, `/scenario/new?from=|mi=|sb=sb_…`)는 이전 흐름 화면으로 넘긴다.
- 공용 화면(`@/shell` flow): `ContentListScreen`(목록 v61 — 위 · 초안 카드의 Storyboard 칩도 이름 · 초안 ×) · `GateScreen`(줄 목록 안에서만 스크롤, 조사 자동 · 초안 이어 쓰기) · `FlowBar` · `SBPopup` · `ContentPopup`(머리 · 바닥 보드 값) · 상세 틀은 `ContentDetail` · `StepModal`(§5-0).
- **저장 전 초안 지우기 · 이어 쓰기(2026-10-10 · 보드에 없음)**: 7개 자원 `DELETE /v1/{rq-flows|dss|mi-flows|ca-flows|value-maps|spec-flows|space-sets}/{id}`
  — 한 번도 저장하지 않은 초안만 204, 저장한 것 409 `SAVED_CONTENT`(「저장한 콘텐츠는 Storyboard에 연결돼 있어 지울 수 없어요」), 확인과 지우기 사이에 저장이 끼면 409 `VERSION_CONFLICT`
  (`DocStore.delete(expected_version=)` 한 트랜잭션). 목록(보드 List)은 초안 카드에 손을 올리면 오른쪽 위 × → 확인 → 지움(`DraftRow.onDelete`). Gate 로 같은 Storyboard 를 다시 시작하면
  새로 만들지 않고 그 초안을 연다(`POST {sb_id}` → 200 기존 초안 · 새로면 201) — Gate 줄에 「작성 중 초안 있음」 · 시작 버튼 「초안 이어 쓰기」(`GateScreen drafts`). 코드 번호는 남은 최댓값 + 1.
- **DSS 다시 가져오기(2026-10-10 · 보드에 없음)**: Spec 시트 · 공간 시나리오 · VP 는 만든 DSS(`dss_ref` · `dss_ver`)를 남기고, 열 때(`GET`) 허브의 지금 `stages.dss` 와 견줘
  `dss_changed{from, to, added, removed, changed, …}` 를 준다. 편집 화면 머리 아래 안내 줄(AiBar 「Storyboard의 DSS가 바뀌었어요 · DSS-01 v1 → v2 · 제품 1 추가 · 1 빠짐」 · 「다시 가져오기」)
  → `POST …/{id}:resync-dss`: 새 제품(공간)은 더하고, 빠진 제품은 사람이 쓴 내용(시트 값 · 시나리오 · 가치)과 함께 남겨 「DSS에서 빠짐」으로 표시(지우기는 사람이), 사람이 고친 수량은 그대로.
  그리드 높이만 안내 줄(38 + 12)만큼 줄고 칸 폭은 보드 그대로.
- **제안서 ← 허브(2026-10-10)**: `/proposal/new?sb=SB-nn` · PR1L 「최근 Storyboard」 줄에서 허브 Storyboard 를 연결하면 `stages.*` 가 섹션 재료가 된다(proposal `hub.py` `STAGE_TARGETS` —
  rq → 고객 정보 · 요구사항, dss → 공간별 제품 · 솔루션, Key message → Value Props · 표지 부제, mi → MI, ca → Why Samsung, vp → Value Props, sp → 제품 스펙, sc → 솔루션 시나리오;
  빈 stage 는 「새로 작성」). 제안서는 허브 「PPT 제작 · B2B 제안서」 칸에 자기를 적고(`stages.ppt`), 지우면 칸을 비운다(`DELETE /v1/flows/{id}/stages/ppt?ref=`).
  「Storyboard 업데이트됨」은 허브 `content_rev`(ppt 칸 기록 제외)로 견준다.
- 남은 것: 웹앱 ② 조감도 2D/3D 재구현(별도).

## 6. Storyboard 허브 · stage 계약 (2026-10-08 구현)

허브: storyboard 서비스 `/v1/flows*`(contracts/storyboard.json, 본체 `services/storyboard/src/winmate_storyboard/flows.py`).
콘텐츠 서비스는 `winmate_common.flow` 의 `get_flow(sb)` · `push_stage(sb, key, ref=, ver=, res_id=, title=, value=, md=, card=)` 만 쓴다
(consumes 에 storyboard 필요). 웹은 `@/shell` 의 `useFlow` · `FlowBar` · `GateScreen` · `ContentListScreen` · `ContentDetail` · `StepModal` · `ContentPopup` · `SBPopup`.

| 경로 | 하는 일 |
|---|---|
| `GET /v1/flows?content=` | SB0 · Gate 목록(진행 칸 `cells` · `progress` · content 를 주면 `eligible` · `need` · `existing`, 안 주면 SB0 썸네일 `summary_head`) |
| `POST /v1/flows` (internal) | 고객 요구사항 저장 → Storyboard 자동 생성(`rq` stage 포함) |
| `GET /v1/flows/{id}` | flow.json 전체(`flow_json`) · `summary_md` · `cards` · `history` |
| `PATCH /v1/flows/{id}` | 이름 · Key message · 요약본 고침(사람 문장 `user_lines` → 다시 써도 `✎` 로 남음) |
| `PUT /v1/flows/{id}/stages/{key}` (internal) | 콘텐츠 저장 → stages.<key> 실제 값 · 요약 줄 · 팝업 카드. 같은 ref 의 다른 Storyboard 도 반영(`synced`). 사전 작업 없으면 422 `PREREQUISITE_MISSING` |
| `POST /v1/flows/{id}:branch {stage}` | 복제본 — 새 Storyboard(parent · `분기 B`), 사전 작업 사슬(dss → rq)만 공유(`sharedWith`) |
| `POST /v1/flows/{id}/key-message:suggest` | 전략 수립 AI 후보 3안(`sb.key_message.v1`, 없으면 규칙 후보) |
| `GET /v1/flows/contents/{key}` | 보드 List — 저장된 콘텐츠마다 연결된 Storyboard 들 · 썸네일 `card`(가장 최근 저장분의 보기 팝업 카드) |

편집 화면 경로(허브 `cells[].route`): rq `/requirements/flow/{id}` · dss `/dss/{id}` · mi `/mi/flow/{id}` · ca `/competitor/flow/{id}` · vp `/vp/values/{id}` ·
sp `/spec/flow/{id}` · sc `/scenario/spaces/{id}`. 목록은 `/<base>`(보드 List), 새로 만들기는 `/<base>/new`(보드 Gate, rq 만 바로 RQ1).
이전 흐름 화면은 `/<base>/legacy` 아래로 옮긴다(제안서 handoff 가 아직 읽는다).

`push_stage` 의 `value`(= flow.json `stages.<key>`, ref · ver 는 허브가 붙인다) — 콘텐츠끼리 서로 읽으므로 이름을 바꾸지 않는다:

```text
rq : {customer, title, target, keymen[{role, weight, needs[]}], goals[], requirements[{id, text, status: ok|check, by}], counts{keymen, reqs, check}}
dss: {industry{value, by, basis}, spaces[{name, by, products[{name, kind: product, ref, qty, by}]}], solutions[{name, ref, by, links[], why}], counts{spaces, products, solutions}}
mi : {prevVer, queries{market[], customer[], user[]}, filters{period, sourceTypes[]}, counts{found, kept, numberCheck}, items[{id, group, summary, source{type, name, date, url}, kept, addedIn, numberCheck}]}
ca : {basis{from, categories[]}, dimensions[], competitors[{id, name, by, wiki{…, source}, criteria[{k, v, status}], matches[{space, ours, theirs, dims{spec|price|cases|esg|brand: {verdict, note}}}], pros[], cons[], claims[{axis, text, supports}], candidateEvidence}], counts{competitors, matches, verdicts{oursBetter, similar, oursWorse, noData}}}
vp : {from, selection{fromDss, excluded, addedOutsideDss}, items[{name, kind, ref, spaces, values[{id, space, message, need{text, by}|null, req, by}]}], importedFrom, counts}
sp : {from, models[{space, name, model_code, ref, qty, specs{<key>: value}, by}], columns[{key, label}], warnings[{model, text}], counts{models, columns}}
sc : {from, spaces[{name, products[], scenarios[{id, title, user, products[], steps[{text, product}], fields[{k, v}], by}]}], rules, counts}
```

`card`(ContentPopup 820×680): `{title, facts[[이름, 값]×3], groups[{h, sub, lines[{t, note}]}], foot, line}` — `line` 은 SB1 연결된 콘텐츠 줄 한 줄 요약.
`md`: 요약본 절의 본문 줄(`- …`), 머리(`## n. 이름 · ref vN`)는 허브가 붙인다. `ver` 는 그 콘텐츠를 저장(완료)한 횟수.
