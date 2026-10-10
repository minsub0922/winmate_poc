# spec 서비스 — 개발 세션 규칙

Spec 시트 — 조건으로 모델 찾기 · 고객 스펙 대응표 · 단종·불일치 경고 · 단위 변환

- 포트: **5106** · 게이트웨이 경로: `/api/spec/v1/...` · 파이썬 모듈: `winmate_spec`
- 고칠 수 있는 경로(owns): `services/spec/**`, `web/src/features/spec/**`
- 호출할 수 있는 서비스(consumes): `ai-tools`, `kb`, `files`, `jobs`, `workspace`, `export`, `requirements`
- 화면 수용 기준: `docs/scenarios/06-spec.md` · 원본 보드: `docs/screens/` (INDEX.md)

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=spec          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=spec         # 이 서비스 테스트
make contracts SERVICE=spec    # contracts/spec.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("spec", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("spec")`(data/spec/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=spec` 를 돌리고 `contracts/spec.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태

### 새 흐름(2026-10-08 · 보드 webapp1 SP0 · SP1 · SP2 · SP_Done · docs/scenarios/11-content-flow.md §6 `sp`)
- API `/v1/spec-flows*`(스키마 접두어 `SF*`, 본체 `spec_flow.py` · `routes/flows.py`, 저장 컬렉션 `spec_flows` sfl_ …):
  만들기 `POST {sb_id}`(get_flow → stages.dss 제품 = 행, 솔루션은 행 아님 · 없으면 404 / DSS 없으면 422 `PREREQUISITE_MISSING`) · 고치기 PATCH(형식 · 항목 8칩 · 표기, expected_version 409) ·
  행 PATCH(넣기/빼기 · 수량 · 모델 바꾸기 — 카탈로그에 없으면 422 `MODEL_NOT_IN_CATALOG` · 모델 비우기) · 행 모델 후보 GET(같은 제품군 / q 검색) · `:finish` · `/stage`.
- 모델 맞춤은 결정적(DSS ref → 이름 속 모델명 → 없음). 칸 값은 KB 원문에서만, 없으면 `[확인 필요]`(영문 `[To be confirmed]`). 경고: 카탈로그에 없음 · 단종(예정) · 품절 · DSS 이름과 불일치 · 제품군 대표 모델.
- 수량은 DSS 원문(`2대` · `1식` · `실당 1대` · null)에서 개수가 분명한 것만 더하고, 하나라도 모르면 null(= [확인 필요]) — 원문은 `qty_note`.
- `:finish` → XLSX(export `POST /v1/exports` xlsx · `SP-01_v1.xlsx`, 못 만들면 null — 저장은 된다) → `push_stage(sp)` 값 = §6 `{from, models[{space, name, model_code, ref, qty, specs, by}], columns, warnings[{model, kind, text}], counts}`
  + 보드 Done 키 `format · lang · unit · valuesFrom · catalogVersion · file · fileId`. 응답 `{stage, summary_md, flow_sync, file{id, name, url}}`. register_item(feature=SP, route=`/spec/flow/{id}`).
- 화면 `web/src/features/spec/flow/`: `/spec`(SP0 = ContentListScreen) · `/spec/new`(SP1 = GateScreen · `?sb=&auto=1`) · `/spec/flow/:id`(SheetPage: SP2 → SP_Done = FlowDoneView) ·
  ModelDialog(보드에 없음 — ProdPicker 760×640 모양: 같은 제품군 · 카탈로그 검색 · 수량 · 모델 비우기). CSS `sheet.css`(접두어 sf-).
  이전 흐름 목록 · 새로 만들기는 `/spec/legacy` · `/spec/legacy/new(/find · /requirements)`, `/spec/new?models=|from=|pop=` 와 옛 `/spec/new/find|requirements` 도 그리로. `/spec/:id/*` 는 그대로.
- 보드와 다름: 제품 줄 오른쪽 모델 칩 · 공간 줄 뒤 경고 이름(주황) · 아래 줄 「확인 필요 값 n · 경고 m」 · 미리보기 제품 4개부터 3칸 폭 유지 + 가로 스크롤 · 「제품별 1장」 미리보기 ·
  Done 설명의 「XLSX로 내보낼 수 있어요」는 내려받기 링크 · 요약 줄에 「확인 필요 값 · 경고」 한 줄 더.
- 테스트 pytest 60(새 흐름 4: 허브 연동 · 저장 조건 · 수량 원문 · XLSX) · e2e `web/e2e/spec/sp-flow.spec.ts` 2(캡처 `__screens__/SP0 · SP1 · SP2 · SP2_Model · SP2_PerProduct · SP_Done · SP_DoneJson · SP2-1920-new.png`).
- **DSS 다시 가져오기 · 초안 지우기 · 초안 이어 쓰기(2026-10-10 · 보드에 없음)**:
  - 시트는 만든(다시 가져온) DSS 의 `dss_ref` · `dss_ver` 를 남긴다. `GET /v1/spec-flows/{id}` 는 허브(`get_flow`)의 지금 stages.dss 와 행을 견줘
    `dss_changed{from: "DSS-01 v1", to: "DSS-01 v2", ref_changed, added, removed, changed, added_names, removed_names}`(바뀐 것 없으면 null — 판만 올랐으면 null,
    DSS ref 가 바뀌면(분기 등) 내용이 같아도 알림). 다른 고침 응답의 `dss_changed` 는 계산하지 않아 늘 null(웹은 앞의 값을 잇는다).
  - `POST …/{id}:resync-dss`: 새 DSS 제품 → 행 추가(모델 맞춤 · 카탈로그 값 · `by: dss` · `dss_status: added`), DSS 에서 빠진 제품 → 행은 남기고 `dss_status: removed`
    + 경고 kind `dss_removed` 「DSS에서 빠짐」(첫 경고), 남은 제품 → 공간 · 수량 원문은 DSS 값, 수량은 사람이 고치지 않은 행만(`qty_edited` — 행 PATCH qty 때 true),
    DSS ref 가 바뀌었고 모델을 사람이 고르지 않았으면 모델을 다시 맞춤. 결과 `last_resync{from, to, added, removed, updated, kept_qty}`. 빠졌던 제품이 돌아오면 added.
    `DELETE …/{id}/rows/{key}` 는 빠진 행만(아니면 422 `ROW_IN_DSS`).
  - `DELETE /v1/spec-flows/{id}` 204 — 한 번도 저장하지 않은 것만(`ver` · `saved_at` · done 이면 409 `SAVED_CONTENT` 「저장한 콘텐츠는 Storyboard에 연결돼 있어 지울 수 없어요」),
    workspace 색인 `unregister_item`. `POST /v1/spec-flows {sb_id}` 는 같은 Storyboard 의 저장 전 초안이 있으면 그것을 200 으로(새로 만들면 201). 코드 SP-NN 은 남은 코드 최댓값 + 1.
  - 화면: SP2 머리 아래 안내 줄(`@/ui` AiBar · 「Storyboard의 DSS가 바뀌었어요 · DSS-01 v1 → v2 · 제품 1 추가 · 1 빠짐」 · 「다시 가져오기」) — 줄(38 + 12)만큼 그리드만 준다.
    다시 가져오면 토스트, 새 행 공간 줄 「DSS에서 새로」, 빠진 행 「DSS에서 빠짐」 + ×(지우기). SP0 저장 전 초안 줄은 `DraftRow.onDelete`(셸 × · 확인).
  - 테스트 pytest 63(+3: 다시 가져오기 합치기 · 사람 수량 유지 · ref 바뀜 · 돌아온 제품 / 404 / 지우기 · 이어 쓰기 · 분기) ·
    e2e `web/e2e/spec/sp-resync.spec.ts` 1(캡처 `__screens__/SP2-resync-new.png` · `SP2-resynced-new.png`).

(2026-10-06 · 06-spec 전 화면 · API · 워크플로 구현, 테스트 55 · e2e 7 통과)

### 구조
- API(71 작업, `contracts/spec.json`): `routes/` — sheets(목록 · 작업 · 제품 · 항목 · 형식 · 양식 · 기본값) · find(SP1C) · compliance(SP1R) ·
  generate(생성 · 값 확인 · 데이터시트 · 셀 · 말로 수정 · 내보내기 · 공유) · edit(편집 세션) · warnings(경고 · 재확인 · 카탈로그 · 생애주기) ·
  handoff(넘김 · ack · 연결 · 묶음 · proposal P1/P2/P3).
- 잡(`worker.py`): spec_generate · spec_find · spec_compliance · spec_datasheet · spec_revise · spec_template · spec_recheck · spec_export.
  LangGraph(`graphs/`)는 단계 노드마다 `step` 이벤트(`{step, status, note, label}` — 06 문서의 `stage` 대신 공용 `step` 키).
- 결정적 규칙(`rules/`): values(값 해석 · 표시 · 단위 · 충돌 · 우위) · items(12항목) · finder · compliance · warnings · edit · package · fmt · text(화면 문장).
- 저장: `DocStore.for_service("spec")` 컬렉션 sheets · exports · handoffs · links · edit_sessions · snapshots · prefs. 상태가 바뀌면 `ops.publish` → `register_item`.
- 화면(`web/src/features/spec/`): ListPage(SP0) · ProductsPage(SP1 · SP1Product) · FindPage(SP1C) · RequirementsPage(SP1R) · ItemsPage(SP2) ·
  FormatPage(SP2L) · GeneratingPage(SP3G) · ResultPage(SP3) · WarningsPage(SP3W) · EditPage(SP3E) · ExportPage(SP4). 공용: api.ts · ui.tsx · parts.tsx · revise.ts · spec.css(토큰만).
  `index.tsx` 의 `Keyed` 는 `/spec/new…` → `/spec/:id/…` 로 넘어갈 때 화면을 이어 가고(잡 · 입력 유지), 다른 작업으로 옮기면 새로 마운트.

### 결정 · 원칙
- 셀 값은 카탈로그(kb 어댑터) · 보증 정책 · 데이터시트 · 사용자 입력 · 파생 계산에서만. LLM 은 고객 문서에서 요구 추출 · 말 해석 · 번역만(값 담은 조작은 `needs_clarification`).
  근거 없는 칸은 `[확정 필요]`(영문 `[To be confirmed]`). 고객 문서 · 양식 · 데이터시트 · 고객사 이름이 든 호출은 `confidential=True`.
- ai task 매핑(문서 이름 → task): spec.parse_conditions.v1 → `sp.parse_conditions` · page_ocr → `sp.page_ocr` · extract_requirements → `sp.extract_requirements` ·
  classify_requirement → `sp.classify_requirement` · datasheet_extract → `sp.datasheet_extract` · template_map → `sp.template_map` ·
  interpret_request → `sp.interpret_request`(맥락별 `_memo` · `_warnings` · `_export` · `_edit`) · translate → `sp.translate`. 목: `mocks/ai-tools/sp.*.json`(12개).
- 앱 시계 `touched_at`(SPEC_FIXED_NOW 고정 가능)으로 화면 시각을 그린다. 카탈로그 어댑터 기본 `kb`(테스트 CAT_FIX 는 `fixture`).
- 경고 카드의 기본 선택은 웹이 `선택한 대로 반영` 직전에 결정으로 저장한다(서버 `warnings:apply` 는 결정 있는 카드만 반영). 이동만 하는 버튼(find_other · upload_datasheet · view)은 저장하지 않는다.
- 매일 06:00 KST `spec_recheck(all)` 예약(`ensure_daily_schedule`), `POST /v1/catalog:recheck-all`(system).

### 문서와 다른 점(알려진 차이)
- kb 실데이터: 보증 · 소비전력 Typical/Max 원천이 없어 값 확인으로 남는다(`warranty.yaml` · `lifecycle.yaml` 은 비워 둠 — 지어내지 않음). QHC 는 실데이터에 MagicINFO 가 있어
  테스트는 KB_FIX_55(VXT 만)로 패치, C2 후보 풀도 실데이터와 달라 찾기 테스트는 C2 · 제품군을 패치.
- P2 는 `201 SheetDoc`(+ active_job), P3 는 `{items: [...]}`. XLSX 를 고객사 양식 파일에 그대로 써 넣지는 못함(우리 디자인 + 양식 행 순서 · 이름) → export 요청.
- 대응표 그래프는 노드 하나. 셀 직접 수정은 `value_mismatch_source` 경고를 만들지 않음. SP3E `편집 완료` 는 SP3 로.
- SP4 제안서 목록 · 섹션 시트는 proposal 계약에 아직 없어 웹은 시트의 연결로만 기존 시트 알림을 판단(요청함).

### 요청한 것(docs/requests)
- kb: 보증 연수 · 후속(C5)/sale_status_code 뜻 · A3 인치/cm · 소비전력 Typical/Max. export: XLSX 양식 채우기. proposal: 경로 안내 + 제안서 목록 · 섹션 시트 읽기.
  workspace: 제안서 항목에 붙는 알림. platform: ai-tools 목 입력별 응답.

### 테스트
- `make test SERVICE=spec`(pytest 55, in-process 플랫폼 앱 · kb 실데이터 · 실제 requirements 앱 통합 1). 도우미 `tests/sp_helpers.py`(importlib 모드라 고유 이름),
  픽스처 생성 `python services/spec/tests/sp_samples.py <폴더>`.
- `make e2e-feature SERVICE=spec`(web/e2e/spec 7개, 스크린숏 `web/e2e/spec/__screens__/`). 목 `sp.interpret_request` 는 순환이라 warnings.spec 이 순서를 맞춘다.

### 통합(integration · 2026-10-07)
- 새 internal `DELETE /v1/links?proposal_id=` — proposal 이 제안서를 지울 때 연결(slk_) · `제안서와 다름` 경고(dismissed) · 시트 `target_proposal` 을 거둔다(pytest 56). BE6 · MI3V 진입 `from=birdseye:` · `from=mi:` 는 origin 으로 남는다(통합 e2e 확인).
