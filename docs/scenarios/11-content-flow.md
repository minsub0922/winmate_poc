# 11 · 콘텐츠 흐름(Storyboard 중심) — 수용 기준 (2026-10-08)

디자인 원본: `docs/screens/webapp1/*.dc.html`(캔버스 v63 — 상세 한 장은 §7) · 그린 화면 `docs/screens/_rendered/webapp1/<보드>.jpg · .txt`.
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
| CF-06 | 사전 작업은 필수다. 콘텐츠 목록 → 새로 만들기를 누르면 **목록 위에 Storyboard 고르기 팝업(Gate 880×780)** 이 바로 뜨고, 고르면 그 콘텐츠 상세로 넘어간다(v63). 같은 종류가 이미 있으면 **수정**(연결된 모든 Storyboard 반영) 또는 **복제본 만들기**(Storyboard 분기). 사전 작업이 없는 고객 요구사항은 팝업 없이 바로 빈 최종본. |
| CF-07 | Storyboard 화면 · 상세의 후속 작업에서 "만들기" 하면 Gate 를 건너뛰고(`/<base>/new?sb=<id>&auto=1`) 현재 Storyboard 를 가져가 새로 만들기 상세로 간다. |
| CF-08 | AI 가 먼저 묻는 화면은 없다. AI 는 "AI 추가기능" 버튼(파란 테두리 + ✦)으로만 돌고, 결과는 **점선**으로 보이며 **수락해야** 들어간다. 예외: MI 는 Storyboard 분석 로딩이 먼저 나온다. |
| CF-09 | 상세는 **최종본 한 장**이다(v63 · §7). 단계 팝업 · 완료 화면 없이 그 자리에서 입력 · 수정 · 저장하고, 저장하면 같은 화면이 「저장됨」으로 바뀐다(토스트 · `flow.json` 버튼 = 전체 JSON 팝업, 이 콘텐츠 줄 강조 · 후속 작업 카드). 저장한 것을 고치면 「고친 곳 n · 되돌리기 · 저장 · vN+1」. |
| CF-10 | 출처 표시 `by`: `manual`(직접) · `ai-accepted`(AI 추천 · 수락) · `ai-pending`(점선) · `ai-candidate-A`(AI 3안 수락) · `ai-web`. |
| CF-11 | 근거 없는 사실 · 수치는 만들지 않는다 — `[확인 필요]` · `[위키 값]` · `[견적 확인]` · `[00]`. |
| CF-12 | 상세 안에서는 페이지가 바뀌지 않는다. 콘텐츠마다 주소 하나(`/<base>/…/:id`)이고 `?step=` · `?edit=` 는 쓰지 않는다(예전 주소로 와도 같은 상세). 2026-10-12 하루 동안 v60(보기 + `?edit=1` 편집 화면) → v62(최종본 + 단계 팝업 `StepModal`) → **v63(최종본에서 바로 고치기 · 단계 팝업 없음)** 으로 바뀌었다 — 앞의 둘은 코드에서 지웠다. 팝업 위에 겹친 시트 · 확인창은 Esc 가 맨 위 것만 닫는다. |

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

## 5. 구현 현황 (2026-10-12 — 웹앱 ① v63 전부)

모든 콘텐츠가 허브(§6)에 붙었다. 화면은 보드 인라인 px 그대로이고, e2e 가 고정 칸 폭을 숫자로 잰다(`web/e2e/<기능>/<기능>-flow.spec.ts`, 캡처 `__screens__/<보드>.png`).
2026-10-12 v63 으로 상세를 최종본 한 장으로 바꿨다 — 보드 이름 · 팝업 · 새 API 는 §7.

| 콘텐츠 | 보드 | 목록 · 새로 · 상세 | 백엔드(새 자원) | e2e |
|---|---|---|---|---|
| 홈 | HomeGrid | `/` — 시작 · 흐름 3 · Storyboard로 만드는 콘텐츠 5 · 비주얼 2 · 최근 작업 2 | — | `shell/layout.spec.ts` H-* |
| 고객 요구사항 | RQ0 · RQ1 · RQ_Draft · RQ_View · RQ1_Edit · RQBody | `/requirements` · `/requirements/new`(바로 빈 최종본 — 첫 칸을 쓰고 떠나면 초안이 생기고 주소가 `/requirements/flow/:id` 로) · `/requirements/flow/:id` | requirements `/v1/rq-flows*` — 첫 저장에 Storyboard 자동 생성 | `requirements/rq-flow.spec.ts` |
| Storyboard | SB0 · SB1 · SB1_Json · SB1_View · SB1_Strat · SB1_StratAI | `/storyboard` · `/storyboard/flow/:id` | storyboard `/v1/flows*`(허브) | `storyboard/sb-flow.spec.ts` |
| DSS | DS0 · DS1 · DS2 · DS2_AI · DS4 · DS4_AI · DS_Draft · DS_View · DS_ViewJson · DS2_Edit · DSBody · SolPicker | `/dss` · `/dss/new`(목록 위 Gate 팝업) · `/dss/:id` | dss(신규 서비스, 5111) `/v1/dss*` | `dss/dss-flow.spec.ts` |
| MI | MI0 · MI1 · MI1_Branch · MI2_Loading · MI2 · MI2_Run · MI3 · MI_Draft · MI_View · MI3_Edit · MI_Search · MIBody · MISearch | `/mi` · `/mi/new`(Gate 팝업) · `/mi/flow/:id`(새로 만들면 검색 팝업 MISearch 가 바로 열림) | mi `/v1/mi-flows*` | `mi/mi-flow.spec.ts` |
| 경쟁사 분석 | CA0 · CA1 · CA2 · CA2_Info · CA2_Pc · CA2_AI · CA_Draft · CA_View · CA2_Edit · CA_Table · CABody | `/competitor` · `/competitor/new`(Gate 팝업) · `/competitor/flow/:id`(탭 · 경쟁사별/비교표는 화면 상태) | competitor `/v1/ca-flows*` | `competitor/ca-flow.spec.ts` |
| VP | VP0 · VP1 · VP2 · VP2_AI · VP2_Pick · VP2_Detail · VP_Draft · VP_View · VP2_Edit · VPBody | `/vp` · `/vp/new`(Gate 팝업) · `/vp/values/:id` | vp `/v1/value-maps*` | `vp/values.spec.ts` |
| Spec 시트 | SP0 · SP1 · SP2 · SP2_Pick · SP_Draft · SP_View · SP2_Edit · SPBody | `/spec` · `/spec/new`(Gate 팝업) · `/spec/flow/:id` | spec `/v1/spec-flows*`(저장 때 XLSX 도 만든다) | `spec/sp-flow.spec.ts` |
| 공간 시나리오 | SC0 · SC1 · SC2 · SC2_AI · SC2_Pick · SC2_Empty · SC_Draft · SC_View · SC2_Edit · SCBody | `/scenario` · `/scenario/new`(Gate 팝업) · `/scenario/spaces/:id` | scenario `/v1/space-sets*`(DSS 공간 · 제품으로 미리 채움) | `scenario/sc-flow.spec.ts` |

- **고객 요구사항의 AI 심층 질의(폼 개선 과정 · 보드 RQ1_AI)는 2026-10-12 에 뺐다**(아티팩트 v59 · `deep-questions` API · `rq.deep_questions.v1` 도 없음) — RQ1 은 폼 입력 · 파일로 채우기 · 저장만. 확인 필요 표시는 사람이 요구 줄의 「확인 필요」로 단다.
- **목록 v61(2026-10-12 · 보드 List · SB0)**: 7개 콘텐츠 목록과 Storyboard 목록은 같은 틀이다.
  머리(이름 · 설명 · 사전 / 후속) 아래 22 에 **본문 폭 전체 · 가운데 「새 ○○ 만들기」**(1100×156 · 브랜드 바탕 · 아래 줄에 그 콘텐츠의 단계 흐름 ① → ② → ③ · 「모두 N단계」),
  그 아래 44 에 「작업 내역 n」, 16 아래 **그리드 카드 260 × 4(간격 20)**. 카드 = 썸네일 258×148(회색 바탕 위 흰 문서 — 허브가 가진 그 콘텐츠의 보기 팝업 카드
  `card{facts, groups}` 를 472 폭으로 그려 반으로 줄인 것 · 오른쪽 아래 「완성」/「작성 중」) · 제목(2줄) · 코드 · 수정 시각 · **n/N 단계**(막대 N칸: 지난 · 지금 · 남은)
  · 연결된 Storyboard 첫 칩 + 「+n」. 저장한 것은 N/N 「완성」, 저장 전 초안은 지금 단계 — 사전 작업이 있는 콘텐츠는 2(Storyboard 를 골랐으니), DSS 는 솔루션을 골랐으면 3,
  MI 는 정제(`phase=refine`) 중이면 3, 요구사항 초안은 1(`DraftRow.step`). 카드가 없는 저장분 · 초안은 빈 틀 썸네일. 최근 수정 순, 빈 목록은 점선 안내(범례 없음).
  Storyboard 목록(SB0)은 「새 고객 요구사항으로 시작」 · 카드 썸네일 = 진행 8칸 + 요약본 앞 줄(`FlowListItem.summary_head`) · **n/8 단계**(입력된 칸 수 · 막대 8칸) · Key message.
  공용 부품 `@/shell` `ListHero` · `HistoryHead` · `SegLegend` · `StepMeter` · `ThumbFrame` · `CardMini`(`web/src/shell/flow/list.tsx`), e2e `shell/content-list.spec.ts`.
- 새로 만들기 `/<base>/new?sb=<id>&auto=1` 은 Gate 를 건너뛴다(Storyboard 「만들기」 · 상세의 후속 작업 카드).
- **이전 흐름**은 `/<base>/legacy` · `/<base>/legacy/new` 로 옮겼다. 이전 흐름의 다른 경로(`/<base>/:id/...`)는 그대로다(제안서 handoff 가 읽는다).
  예전 들어오기 주소(`/vp/new?sb=sb_…` · `?mi=` · `?rq=`, `/mi/new?rq=`, `/competitor/new?input=…`, `/spec/new?models=|from=|pop=`, `/scenario/new?from=|mi=|sb=sb_…`)는 이전 흐름 화면으로 넘긴다.
- 공용 화면(`@/shell` flow): `ContentListScreen`(목록 v61 — 위 · 초안 카드의 Storyboard 칩도 이름 · 초안 ×) · `GateScreen`(v63: 목록 위 팝업 `GateDialog` · 줄 목록 안에서만 스크롤, 조사 자동 · 초안 이어 쓰기) · `ContentDetail`(v63 상세 틀 · §7) · `FlowBar` · `SBPopup` · `ContentPopup`(머리 · 바닥 보드 값). `FlowDoneView` 는 이전 흐름 화면만 쓴다.
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
(consumes 에 storyboard 필요). 웹은 `@/shell` 의 `useFlow` · `FlowBar` · `GateScreen` · `ContentListScreen` · `ContentDetail` · `ContentPopup` · `SBPopup`.

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

상세 경로(허브 `cells[].route`): rq `/requirements/flow/{id}` · dss `/dss/{id}` · mi `/mi/flow/{id}` · ca `/competitor/flow/{id}` · vp `/vp/values/{id}` ·
sp `/spec/flow/{id}` · sc `/scenario/spaces/{id}`. 목록은 `/<base>`(보드 List), 새로 만들기는 `/<base>/new`(보드 Gate — 목록 위 팝업, rq 만 바로 빈 최종본).
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

## 7. 최종본에서 바로 고치기 (2026-10-12 · 웹앱 ① v63)

보드 `View`(틀: 머리 · 저장 · 본문 · 후속 작업 · 팝업) + 콘텐츠마다 본문 `RQBody` · `DSBody` · `MIBody` · `CABody` · `VPBody` · `SPBody` · `SCBody`.
코드는 셸 `ContentDetail`(`web/src/shell/flow/detail.tsx`) + 기능 본문(`RqBody` · `DsBody` · `MiBody` · `CABody` · `ValuesPage` · `SheetPage` · `SpacesPage`).

| 코드 | 기준 |
|---|---|
| CD-01 | 상세는 한 장이다. 단계 스텝바 · 하단 푸터 · 완료 화면이 없고, 예전 `?step=` 주소로 와도 같은 상세가 뜬다. 팝업은 고르기(ProdPicker 760×640 · SolPicker 820×700) · MI 검색(MISearch 1040×740) · 보기(JsonPopup 900×780 · VpDetail 900×720)에만 쓴다. |
| CD-02 | 상태 4개(보드 View `status`): **새로 만들기**(저장 전 · 빈) · **작성 중**(저장 전 · 쓴 것 있음 — 쓰는 대로 자동 저장) · **저장됨**(머리 「눌러서 바로 고쳐요」 · `flow.json` 버튼 · 후속 작업) · **고치는 중**(저장한 뒤 고침 — 「고친 곳 n」 · 되돌리기 · 「저장 · vN+1」). |
| CD-03 | 글 칸은 칸을 떠날 때(또는 Enter) 한 번 저장한다(`InlineInput` — Esc 는 고치기 전 값으로). 토글 · 고르기는 누르는 즉시. 저장한 뒤 이 화면에서 고친 칸은 `cd-in--chg`(파란 1.5px), 더한 줄은 `cd-chgrow` — 저장 · 되돌리기 하면 지운다. |
| CD-04 | 저장(`:finish`)하면 그 자리에서 저장됨으로 바뀌고 토스트(「<ref> vN 저장 · SB-nn에 반영했어요」). 저장할 수 없으면 버튼은 그대로 두고 누를 때 이유를 토스트로(`canSave` 이유 문구 또는 서버 422). |
| CD-05 | 고친 곳 수는 서버가 센다: `:finish` 가 사람이 고치는 값(`EDIT_KEYS`)을 `saved_snapshot` 으로 남기고, 응답 `changes` = 지금과 판의 다른 곳 수(`winmate_common.edits.changes_of` — 목록은 id · 이름으로 맞춰 앞에 하나 끼워도 1, 점선 AI 후보 · 파생 값은 세지 않음). 판 없이 저장된 예전 문서는 처음 읽을 때 지금 값을 판으로 남긴다. |
| CD-06 | `POST …/{id}:revert` 는 저장한 판으로 되돌린다(changes 0, ver 그대로). 저장한 적 없으면 409 `NOT_SAVED`(「아직 저장하지 않아 되돌릴 판이 없어요」). |
| CD-07 | 고치는 중에 다른 화면으로 가면 묻는다: 계속 고치기 · 고친 채로 두고 나가기(다음에 열면 고치는 중으로 이어짐) · 저장하고 나가기. 새로 고침 · 창 닫기는 브라우저 확인. |
| CD-08 | AI 는 「✦ AI …」 버튼으로만 돌고 결과는 점선(`cd-pend`) — 하나씩 수락 · × 또는 PendingBar 「모두 수락 · 모두 지우기」. 점선은 저장 · 고친 곳 수에 들어가지 않는다. |
| CD-09 | 후속 작업 카드(rq → DSS, dss → 공간 시나리오 · Spec 시트): 그 Storyboard 에 이미 있으면 「참조 vN · 열기」, 없으면 `/<base>/new?sb=<id>&auto=1`. |

콘텐츠별 API(2026-10-12 더함 — 계약 `contracts/<서비스>.json`):

| 콘텐츠 | 저장 판(`EDIT_KEYS`) | 새 · 바뀐 API |
|---|---|---|
| rq | title · customer · target · note · keymen · *_by | `RFDoc.changes` · `:revert`(409 `NOT_SAVED` · `FILLING`) |
| dss | industry · spaces · solutions | `DSDoc.changes · saved_at` · `DSSpace.ext` · `:revert` · `:dismiss {kind: industry\|space\|all, name}` · `:accept-all {scope: products\|all}` · `GET …/solution-options?selected=` |
| mi | items · queries · filters · results | `MFDoc.changes · saved_at` · `:revert`(409 `BUSY`) · 저장한 MI 에서 바로 `:search` 하면 지금 화면을 두고 새로 찾은 것만 더함(`addedIn` = 다음 판) |
| ca | title · competitors | `CFDoc.changes · saved_at` · `:revert`(지금 점선 후보는 남김) |
| vp | items | `VMDoc.changes · saved_at` · `:revert` · `:clear-pending` · mock `vp.values_suggest.v1.json` |
| sp | title · format · notation · items · rows · dss_ref · dss_ver · last_resync | `SFDoc.changes · saved_at · file` · 행 `manual · editable · qty_text · source · kind · catalog_ref` · `PATCH …/rows/{row_key} {cells}`(`[확인 필요]` 칸에만, 아니면 422 `CELL_FROM_CATALOG`) · `POST …/rows {name, ref, kind}`(DSS 밖 제품) |
| sc | spaces · dss_ref · dss_ver · dss_spaces · dss_items | `SSDoc.changes · saved_at` · `:revert` |

보드와 다른 곳(보드에 없는 편집 수단 — 모두 손을 올렸을 때만 보이고 자리를 차지하지 않음): 줄 · 카드 · 후보 빼기 ×, 「확인 필요로 표시」, 쓰인 제품 비우기,
SP 모델 · 수량 팝업(ModelDialog) · 항목 체크 목록, DSS 카드 안 찾기 결과 줄 · 솔루션 「더 보기」, VP 칩 목록(ChipSelect). DSS 다시 가져오기 안내 줄(10-10 기능)은 본문 맨 위.
