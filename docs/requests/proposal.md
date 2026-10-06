# proposal 요청

## requirements 연동(10-proposal.md §R1~R4) 경로 안내 — requirements · 2026-10-06
- 필요: 10-proposal.md 의 R1~R4 는 requirements 계약(`contracts/requirements.json`)에서 아래 경로로 이미 된다. 새 경로를 만들지 않았다.
- R1 목록: `GET /v1/requirements?customer=&q=&has_version=true&limit=&cursor=` → `{items: RequirementListItem[], next_cursor}`
  (`customer` 는 고객사 부분 일치, `q` 는 제목 · 고객사 · 프로젝트명).
- R2 정의서 내용: `GET /v1/requirements/{rq_id}?version=` 은 없다 — 저장 버전 스냅숏 `GET /v1/requirements/{rq_id}/versions/{n|latest}` 를 쓴다.
  `snapshot.items_flat[]` = `{id, code("RQ-01"), text, short, keyman_id, keyman_name, keyman_weight, needs_confirmation, evidence[], entities[],
  source{kind, file_id, file_name, locator("슬라이드 3" · "p.5"), quote}}`, 고객사 · 프로젝트명은 `customer_name` · `project_name`(또는 `snapshot.form`).
  화면 칩 이름 "R1" 은 `code` 를 쓰면 된다. `snapshot.form.author_note` 는 **internal**(고객 문서 · 제안서 본문에 넣지 않음).
- R3 파일로 만들기: `POST /v1/requirements/from-files {file_ids, customer_hint?}` → `202 {job_id, ref: {kind: "requirement", id: rq_…}}`
  (잡은 `rq.fill`, 끝나면 정의서 작업본에 항목 · 근거 인용). 버전 스냅숏이 필요하면 이어서 `POST /v1/requirements/{id}/save {}`.
- R4 고객 질문: `POST /v1/requirements/{rq_id}/customer-questions {text, keyman_id?, target?, origin: {kind: "proposal", feature: "PR", ref_id, confirm_item_id?}}`
  — `origin.feature: "PR"` 만 보내도 kind=proposal 로 받는다. 같은 `ref_id` + `text` 는 멱등(두 번째는 200 + 기존 질문).
- 쓰는 곳 링크: 제안서가 정의서를 쓰면 `PUT /v1/requirements/{rq_id}/links/proposal/{pr_id} {title, route, rq_version, depends_on[]}`(internal).
- 상태: 완료(안내 — requirements 계약에 있음)

## Storyboard → 제안서 넘기기 경로 안내 — storyboard · 2026-10-06
- 필요: 10-proposal §8.0 S1 · PR1 `최근 Storyboard` 카드 · SB4 `B2B 제안서` 카드가 쓰는 storyboard 경로(계약 `contracts/storyboard.json`).
- 목록: `GET /v1/storyboards?customer=&q=&tab=all|in_progress|done&updated_after=&limit=&cursor=` → `{items: StoryboardListItem[], next_cursor}`
  (시작 전 초안 `started=false` 는 안 나온다, `requirement_id` 포함).
- 넘김 묶음: `GET /v1/storyboards/{sb_id}/proposal-handoff?type=standard|quickwin|solution&section=vp|mi|why|space_scenario…`
  → `ProposalHandoff v1 {source, target, rq_ref, customer, key_messages[], strategy, items[], facts[], assets[], live_link}`.
  `facts` 의 확인 안 된 수치는 `status=placeholder` · `placeholder="[00]"`(추정하지 않음). 제작자 의견 · 옮긴 영업목표(internal)는 넣지 않는다.
- SB4 카드는 `/proposal/new?sb={sb_id}&rq={rq_id}` 로 보낸다(`POST /v1/storyboards/{sb_id}/handoffs/proposal` 로 넘김 기록 → 응답 `route`).
- 상태: 완료(안내 — storyboard 계약에 있음)

## Spec 시트 넘김 · 연결 경로 안내 + 제안서 목록 · 섹션 시트 읽기 — spec · 2026-10-06
- 안내(계약 `contracts/spec.json`, 06-spec §6.10 · 10-proposal §8.10):
  - P1 `GET /v1/sheets/{id}/proposal-handoff` → ProposalHandoff v1(items = 묶음 시트마다, [확정 필요] 칸은 facts `status=placeholder`, live_link).
  - P2 `POST /v1/sheets {start: 'link', models, purpose: 'proposal', target_proposal?, project_id?}` → `201 SheetDoc`(+ `active_job`, 생성 잡이 `auto_answer` 로 바로 돈다).
    끝은 jobs SSE 또는 `GET /v1/sheets/{id}` 의 `ui_status`.
  - P3 `POST /v1/lifecycle:check {model_codes, locale}` → `{items: [{model_code, status, successors[], evidence}]}`(배열을 items 로 감쌈).
  - SP4 `제안서에 넣기` → `POST /v1/sheets/{id}/handoffs` → `201 {id: 'sho_…', open_route: '/proposal/{pid}/sections/spec?handoff=sho_…' | '/proposal/new?handoff=sho_…', package}`.
    제안서 화면은 `GET /v1/handoffs/{sho}` 로 묶음을 당겨 넣은 뒤 `POST /v1/handoffs/{sho}:ack`(internal)
    `{result: 'applied'|'failed', proposal_id, proposal_title, section_no, section_name, proposal_sheet_ids[]}` 를 보내 주세요.
    applied 면 연결(slk_)이 생기고, 이후 값이 바뀌면 `GET /v1/links?proposal_id=` 가 `sheet_changed` + `diff_cells` + `route` 를 준다.
- 필요(웹이 proposal 계약으로 직접 읽음, 06-spec §4.13.2): SP4 대상 `바꾸기` 는 `GET /api/proposal/v1/proposals?limit=50`
  → `{items: [{id, title, type: 'standard'|'quickwin'|'solution', customer_name?, subtitle?}]}`, `이 섹션에 '스펙 비교' 시트가 이미 있어요` 알림은
  `GET /api/proposal/v1/proposals/{id}/sections/spec` → `{section_no, status_label, owner_name, sheets: [{id, template, title, from: {service, sheet_id}}]}` 를 기대한다.
  지금 proposal 계약에 없어서 웹은 목록을 못 읽으면 `새 제안서로 시작` 만 안내하고, 기존 시트 알림은 이 시트의 연결(links)로만 판단한다.
- 상태: 요청

## IMG4 「제안서에 넣기」 — 진행 중 제안서 · 이미지 자리 · 가져오기 + 사용 등록 — image · 2026-10-06
- 필요: 07-image §4.11 · §8 · AC53. 이미지 서비스는 제안서를 부르지 않고(consumes 아님) **웹 모듈이 제안서 계약으로 직접** 부른다.
  지금 proposal 계약에 경로가 없어 웹은 `404` 면 「진행 중인 제안서가 없어요 + 새 제안서로 시작」, 그 밖 오류면 「다시 시도」를 보인다.
- 제안 API(웹 → proposal):
  - `GET /v1/proposals?tab=draft,review&limit=20` → `{items: [{id, title, short_title?, meta?("표준 제안서 · 작성 중"), project_id?, updated_at}]}`
    — 기본 선택 = 같은 프로젝트의 가장 최근 제안서(웹이 `project_id` 로 고른다).
  - `GET /v1/proposals/{id}/image-slots?image_version=imv_…` → `{sheets: [{sheet_id, name("카운터 · 메뉴보드"), section("공간별 제품 · 같은 공간 장면"),
    recommended: bool, slots: n, preview_url?}]}` — 이미지를 받는 시트만, 장면에 맞는 시트에 `recommended`(R7).
  - `POST /v1/proposals/{id}/imports {source: {service: 'image', version_id, image_id}, target: {sheet_id | null, mode: 'replace_slot' | 'new_sheet'}, caption?}` → 201.
- 제안서가 할 일(서버 → image, internal): 넣은 뒤 `POST /api/image/v1/images/{image_id}/usages {version_id, service: 'proposal', ref: <제안서 id 또는 시트 ref>, label: "A 커피 제안서 › 카운터 · 메뉴보드"}`,
  빼면 `DELETE /v1/images/{image_id}/usages/proposal/{ref}` — IMG0 배지 「제안서 사용 중」 · 셸 정보 「사용 이력」이 이것으로 바뀐다.
  버전 내용(렌디션 fhd · uhd · 생성 메타 · `caption_rule` 「생성 이미지」 · `rights: generated`)은 `GET /v1/versions/{version_id}` · `GET /v1/images/{id}`.
  표지 배경처럼 제안서가 이미지를 요청하려면 `POST /v1/requests {from_service: 'proposal', from_ref, from_label, title, prefill: {kind: 'background', description, aspect}}`(internal).
- 웹 이동: 「새 제안서로 시작」 → `/proposal/new?image_version=imv_…`, IMG3X 「Why Samsung 비교표로 보내기」 → `/proposal?focus=CM&competitor={경쟁사명}`,
  넣은 뒤 토스트 「열기」 → `/proposal/{id}`. proposal 서버가 image 를 부르려면 `config/services.yaml` consumes 에 `image` 가 필요하다.
- 상태: 요청

## MI 넘김 가져오기 · 섹션 경로 · PR 항목 유형 — mi · 2026-10-06
- 필요(03-mi §4.7 · §4.14 · AC-MI-65, 10-proposal §6.6 · §8.7): MI3 `제안서 MI 섹션으로` · MI4 `제안서에 {n}시트 보내기` 는 mi 넘김(`POST /api/mi/v1/analyses/{id}/handoffs`)
  다음에 **웹이** `POST /api/proposal/v1/proposals/{proposal_id}/imports` 를 부른다. 지금 proposal 계약에 경로가 없어 e2e 는 이 호출을 흉내 낸다.
- 보내는 본문: `{section_key: "mi" | "bigMi", via: "handoff", source: {feature: "MI", ref_id: "mi_…", version, handoff_id: "hof_…"}, include_keys: ["sht_…"]}`
  — 10-proposal §6.6 표에 `source.handoff_id` 만 더한 모양. 성공(200/202)이면 웹이 `PATCH /api/mi/v1/analyses/{id}/handoffs/{hof} {status: "delivered", target_title}`, 실패면 `failed`.
  proposal 은 `GET /api/mi/v1/analyses/{id}/proposal-handoff?type=&section=&handoff_id=` 로 시트 내용(익명 처리 끝)을 읽는다(M1).
- 이동: 성공하면 `/proposal/{id}/sections/mi`(Solution형은 `/sections/bigMi`), MI4 `새 제안서로 시작` 은 `/proposal/new?link=mi_…`(셸 기능 키 `proposal` 기준 —
  10-proposal §3 표의 `/proposals/…` 와 다르면 알려 주세요).
- 필요: MI4 `보낼 제안서` 고르기는 workspace `feature=PR` 항목을 쓴다. 매핑을 그 제안서 유형으로 다시 계산하려면 항목 `meta.proposal_type`(standard · quickwin · solution)이 필요하다.
- 상태: 요청

## [backend] 계약 1차 공개 — proposal-backend · 2026-10-07
- `contracts/proposal.json`(85 경로 · 98 작업) · `web/src/api/gen/proposal.ts` 생성 완료. §6.2–§6.13 전 경로가 들어 있다.
  지금은 많은 처리기가 `501 NOT_IMPLEMENTED`(details.op) 를 돌려준다 — 구현되는 대로 이 파일에 `[backend]` 줄로 알린다. 모양(모델)은 바꾸지 않을 생각이다.
- 라우트(서버가 주는 `route` 값)는 웹 기능 키 기준 **`/proposal/...`** 이다(시나리오 §2 의 `/proposals/...` 와 같은 화면).
  예 `/proposal/{id}/customer` · `/proposal/{id}/rfp` · `/proposal/{id}/works` · `/proposal/{id}/reuse` · `/proposal/{id}/type` · `/proposal/{id}/compose` ·
  `/proposal/{id}/industry` · `/proposal/{id}/sections/{key}` · `/proposal/{id}/sections/{key}/sheets/{sheetId}/template` · `/proposal/{id}/design` ·
  `/proposal/{id}/result` · `/proposal/{id}/preview/{sheetNo}` · `/proposal/{id}/confirm` · `/proposal/{id}/review` · `/proposal/{id}/versions` ·
  `/proposal/{id}/one-click/{jobId}` · `/proposal/{id}/reuse/analysis` · `/proposal/{id}/reuse/plan?mode=improve|borrow` · `/proposal/{id}/reuse/summary`.
  다른 기능이 이미 보내는 `/proposal/new?link=mi_…` · `?sb=` · `?rq=` · `?handoff=sho_…` · `?image_version=imv_…` 는 웹이 `POST /v1/proposals {start_mode: handoff, links|rq_ref|image_version}` 로 바꿔 부르면 된다.
- 응답 모델 메모: 화면 문구(…_label · intro · header_label · toast)는 서버가 원문으로 계산해 준다. 시트 `content` 는 템플릿 칸(slots) 키, 값 토큰 `{{fact:id}}` 가 든 원본이고,
  `display` 는 토큰을 표시 문자열로 바꾼 것이다. 동시성: 제안서 · 시트 응답 `rev`(ETag) → PATCH 때 `If-Match` 로(선택, 다르면 409 REV_CONFLICT).

## 공간 시나리오 → 제안서 반입 경로 안내 · SC5 「제안서에 넣기」 — scenario · 2026-10-07
- 안내(계약 `contracts/scenario.json`, 09-scenario §6.6 · §8 · 10-proposal §8.15 N1):
  - N1 `GET /v1/scenarios/{sc_id}/proposal-handoff?type=standard|quickwin|solution&section=spaceScenario|solution&version=`(internal) → ProposalHandoff v1
    `{source: {feature: 'scenario', ref_id, version, title, updated_at, route}, target, customer: {name, industry_code}, items[], facts[], assets[], live_link}`.
    `section=spaceScenario` → 시트마다 항목 1개(`key` = `{코드}:{n}` 예 `VM-A:1` · `SS-A:2` · `SS-B:3`, `template_hint.code` = VM-A · VM-B · VM-C · VM-D · SS-A · SS-B · SS-C,
    공간 시트는 `repeat_key {kind: 'space', ref, label}`, `content = {sheet, scenes[]}`), `section=solution` → 솔루션마다 SXS(`template_hint.code` = `MGI-S` · `STP-S` …).
    근거 없는 수치는 `facts[] status=placeholder · placeholder='[00]'`, 장면 이미지는 `assets[] {kind:'image', file_id, rights:'generated', caption_rule:'생성 이미지'}`.
  - §8 묶음 그대로가 필요하면 `GET /v1/scenarios/{sc_id}/handoff?version=`(internal) — `{scenario_id, version, title, customer, type, solutions, products, roles, slots,
    scenes[{no, time, label, title, story, beats, place, space_key, solutions, products, image?, confirm_tokens, evidence}], sheet_plan, birdseye_link?, confirm_items}`.
    `version` = 시나리오 저장 버전(생성 완료 · 「저장」 때 오른다, 반입 때 쓴 번호를 그대로 다시 읽을 수 있다).
  - 넣은 뒤 `POST /v1/scenarios/{sc_id}/usages {service: 'proposal', ref: <제안서 id>, label, version}`(internal) → SC0 「제안서에 사용 중」, 빼면 `DELETE …/usages/proposal/{ref}`.
- SC5 웹이 부르는 제안서 경로(계약에 있는 것 그대로): `GET /api/proposal/v1/proposals?tab=all&limit=20`(기본 = 같은 프로젝트 · 진행 중 최근) ·
  `POST /api/proposal/v1/proposals/{id}/imports {section_key: 'spaceScenario', via: 'handoff', source: {feature: 'scenario', ref_id: sc_…, version, title}, include_keys: ['VM-A:1', …]}`.
  성공(200/202)하면 토스트 「{제안서}에 시트 {k}장을 넣었어요 · 열기」(응답 `route`), 「새 제안서로 시작」 → `/proposal/new?link=sc_…`(PR1L).
- 상태: 완료(안내 — scenario 계약에 있음)

## [backend] 2차 — 섹션 작성 · 템플릿 · 시트 편집 · 값 · PR6 · PR7(PPTX) 구현 — proposal-backend · 2026-10-07
- 이제 동작(501 아님): `GET /proposals/{id}/sections/{key}`(SectionView — 레일 · 안내 · 받는 자료 칩 · 드롭 문구 · 빠른 요청 · 이전/다음 · `needs_fill`) ·
  `POST …/sections/{key}:fill {reason, quick_action?}`(202 `proposal.section_fill`, 진행 중이면 같은 job_id) · `POST …/sections/{key}/requests {text}` ·
  `POST …/sections/{key}:confirm` · `POST …/sections/{key}/templates:auto` · `GET|PATCH …/sheets/{sheetId}`(ETag = `rev`, PATCH `If-Match` 다르면 409 REV_CONFLICT) ·
  `GET …/sheets/{id}/template-options?product_count=` · `PUT …/sheets/{id}/template {mode, code?, product_count?}` · `POST …/sheets/{id}:rewrite` ·
  `GET …/sheets/{id}/messages` · `GET …/messages?scope=&scope_ref=` · `GET …/facts` · `PUT …/facts/{id}` · `POST …/requests {text}` · `POST …/notes:generate` ·
  `GET|PUT …/design` · `POST …/design/logo` · `POST …:generate {scope, section_key?, infer_empty}` · `GET …/result` · `GET …/slides?filter=` · `POST …/renders`.
- 진입 규칙: 섹션 화면은 `GET …/sections/{key}` 의 `needs_fill=true` 일 때만 `:fill` 을 부르세요(연결 자료가 없는 MI 등은 false — 잡 없음, AC-061).
  `status=filling` 이면 `fill_job_id` 로 `useJob` 을 붙이고 끝나면 다시 GET. 빠른 요청 칩 중 잡이 없는 것(「템플릿 바꾸기」 「출처 보기」 「수량 조정」 「시점 추가」 「조감도 새로 만들기」)은
  `:fill` 에 보내면 422 `QUICK_ACTION_NO_JOB`(details.panel · navigate · prefill)이니 화면에서 처리하세요.
- 시트 `content` = 템플릿 칸(`slot_schema.slots[].id`) 키의 값 + 값 토큰 `{{fact:fct_…}}`, `display` = 토큰을 푼 표시용. 편집은 `content` 경로로 PATCH(`/title`, `/slots/table/rows/5/cells/1/text` …).
- PR7: `:generate` 202 → 잡 끝나면 `GET …/result`(status running|done|failed, 파일 카드 · 썸네일 10 · 범위 줄 · 「{{섹션}} 섹션만 재생성」). PPTX 는 export 로 실제 생성(mock 에서도).
  시트 PNG 렌더는 LibreOffice 가 없으면 export 가 501 이라 썸네일은 템플릿 썸네일(`/api/export/v1/templates/{code}/thumbnail.png`)로 옵니다.
- mock: `mocks/ai-tools/pr.section_draft.json`(섹션별 · 작성 방식별) · `pr.sheet_rewrite.json` · `pr.request_route.json` · `pr.notes.json` · `pr.shorten.json`.
- 상태: 진행 중 — 다음은 시작 방식(RFP · 기존 작업) · 반입(DnD · 보내기) · 딸깍 · 확인 항목 · 검토 · 버전 · 내보내기 · 기존 제안서 활용.

## 조감도 → 제안서 반입 경로 안내 · BE6 「제안서에 넣기」 — birdseye · 2026-10-07
- 안내(계약 `contracts/birdseye.json`, 08-birdseye §6.7 · §8 · 10-proposal §8.14 B1):
  - B1 `GET /v1/birdseyes/{id}/proposal-handoff?type=standard|quickwin|solution&section=birdseye|spaceProducts|spaceScenario` → ProposalHandoff v1
    `{source: {feature: 'birdseye', ref_id, version, title, updated_at, route}, target, customer, items[], facts[], assets[], live_link}`.
    10-proposal §8.14 의 `GET /v1/layouts/{id}/proposal-handoff` 도 같은 응답(별칭)이라 어느 쪽을 불러도 된다.
  - 항목 `key` / `template_hint.code`: `BV-A`(주 컷 · 공간 전경) · `BV-B`(도입 전/후 쌍, 없으면 주간/야간 쌍, 둘 다 없으면 없음) · `ZP-A|ZP-B|ZP-C`(존 포인트 —
    BE5Z 레이아웃, `content.points[{n, name, text, u, v}]`) · `SM-B`(공간별 제품 · 수량표 — `content.rows[{name, model_code, at, qty, qty_source, confirm}]`,
    추정 수량은 `status='warn'` · 「확인 필요」). 이미지는 `assets[] {kind:'image', file_id, image_version_id, rights:'generated', caption_rule:'생성 이미지'}`.
  - §8 묶음 그대로: `GET /v1/birdseyes/{id}/handoff?version=` · 변경 감지 `GET /v1/birdseyes/{id}/version`.
  - 넣은 뒤 `POST /v1/birdseyes/{id}/usages {service: 'proposal', ref: <제안서 id>, label, version}`(internal) → BE0 「쓰인 곳」, 빼면 `DELETE …/usages/proposal/{ref}`.
- BE6 웹은 제안서 계약 그대로 `GET /api/proposal/v1/proposals?tab=all&limit=20` · `POST /api/proposal/v1/proposals/{id}/imports {section_key: 'birdseye',
  via: 'handoff', source: {feature: 'birdseye', ref_id: be_…, version, title}, include_keys: ['BV-A', 'ZP-A', 'SM-B', …]}` 를 부른다.
- 상태: 완료(안내 — birdseye 계약에 있음)

## [proposal-web] 웹 화면에서 필요한 것 — proposal-web · 2026-10-07
웹 화면(web/src/features/proposal)은 계약 그대로 붙였고, 아래가 빠지거나 모양이 정해지지 않아 어댑터로 비켜 두었다. 받는 대로 어댑터를 지운다.
1. **SectionView.sources[] 에 셸 참조 `ref` 추가**(AC-091) — `SourceChip.ref: string|null` = 반입 때 받은 셸 참조(`kb:model:mdl_…` · `kb:solution:magicinfo` ·
   `kb:case:dep_…` · `kb:image:img_…` · `img:image:img_…` · `ws:item:<item_id>`). 웹은 이 값을 상단바 `added` 로 넘겨 팝오버 항목을 「✓ 추가됨」으로 보인다(새로고침 뒤에도).
   지금은 드롭한 그 화면에서만 표시된다.
2. **반입 `source.feature` 는 서비스 키**로 보낸다(`mi` · `storyboard` · `birdseye` · `scenario` · `spec` · `image` · `vp` · `competitor` · `requirements`).
   사이드바 드래그 데이터는 기능 코드(`MI` · `SB` …)라 웹이 바꿔서 보낸다 — 서버도 코드가 오면 받아 주면 좋겠다(둘 다 허용). `SectionView.accepts.sidebar` 는 지금처럼 서비스 키면 된다.
3. **넘김(handoff) 반입** — 웹은 `/proposal/{id}/sections/{key}?handoff=sho_…`(SP4) · `?handoff=hof_…`(MI4)로 열리면
   `POST …/imports {section_key, via: 'handoff', source: {feature: 'spec'|'mi', handoff_id}}` 를 한 번 부르고(응답 `label` · `import_id` · `job_id` 로 띠 + 실행 취소),
   `/proposal/new?handoff=…` 면 `POST /proposals {start_mode: 'handoff', links: [{feature, ref_id: '', handoff_id}]}` 로 만든다.
   서버가 handoff_id 로 그 기능의 ProposalHandoff 를 읽고 ack 하는지(ref_id 빈 문자열 허용 포함) 확인 부탁.
4. **PR1C 활용 방식 선호 저장** — 분석을 시작한 뒤 PR1C 라디오를 바꾸면 「저장만」(§4.10) 해야 하는데 `PUT …/reuse/mode` 는 `improve|borrow` 만 받는다(= PRU3 방식 전환).
   `mode_pref`(`improve|borrow|auto`)만 바꾸는 길이 필요하다: 예 `PUT …/reuse/mode {mode_pref}`(mode 없이) 또는 `PUT …/reuse/mode-pref {mode_pref}` → ReuseView.
   지금은 웹이 그 창(sessionStorage)에 기억했다가 PRU2 → PRU3 를 그 방식(`?mode=`)으로 연다.
5. **PR1C 「올린 파일 지우기」** — 원본을 빼면 웹이 남은 원본으로 `POST …/reuse {sources}` 를 다시 부른다. 마지막 하나를 빼는 길이 없다:
   `POST …/reuse {sources: []}` 를 「원본 없음(분석 초기화)」으로 받거나 `DELETE …/reuse` 가 있으면 좋겠다.
6. **PR7V 나란히 비교의 A 쪽 그림** — LibreOffice 가 없으면 `CompareView.a.png_url` 이 비어 A 슬라이드를 못 그린다.
   `CompareSide.display`(그 버전의 그 시트 display, §5.3.1 모양)를 같이 주면 웹이 슬라이드를 직접 그린다(B 가 현재 버전이면 지금도 시트 display 로 그림).
7. **모양이 열린(object) 필드의 키 확정** — 웹은 아래 키로 읽는다. 다르면 알려 주세요.
   - `ReuseSectionView.section_sheets[]`: `{sheet_id, sheet_no, page_label, name, role, verdict, verdict_label, status, status_label, thumb_url, template_code}`
   - `ReuseSectionView.placeholders[]`: `{token: '[0]일', label: '교체 소요 · 현재', confirm_item_id}`
   - `ReuseView.flow.pattern`: `{name: '문제 해결형', en: 'Problem → Solution'}` · `flow.claims`: `{linked, total}`
   - `CriterionDetail.chips[]`: `{no, name, state}` · `CriterionDetail.detail`: 기준별 표(배열이면 웹이 표로 그림)
   - `ReuseSectionView.tally`: 원본 대조 = `{update, keep, new, drop}`(줄 수), 흐름 가이드 = `{writing, waiting, confirm}`
   - `OneClickView.counts`: `{confirmed, inferred, review}`
8. **시트 content/display 의 칸에 `type`** — 지금 칸에 `type` 이 없어(`{columns, rows}`) 웹이 모양으로 판단한다(rows → 표, items(before/after) → 수치, items → 목록, asset → 이미지, text → 문단).
   §5.3.1 처럼 `type` 을 넣어 주면 더 정확하다(선택).
9. **잡 결과 키** — PR7C 「수정안 만들기」(`review:apply-comments`) 잡이 끝나면 새 버전 번호를 `result.version` 으로 주세요(웹이 PR7V `?a=요청 버전&b=새 버전` 으로 연다).
   `exports` 잡은 `result.export_id`(응답 202 에 export_id 가 없을 때).
- 상태: 요청

## 경쟁사 분석 → Why Samsung 넘김(CA5) 연결 확인 — competitor · 2026-10-07
- 웹(CA5 `제안서 Why Samsung · 경쟁 비교 시트로`)이 하는 일:
  1. `POST /api/competitor/v1/analyses/{ca}/handoffs {target:"proposal_why", target_id: <proposal_id>, confirm?: {real_names}}` → `handoff_id`(`hof_…`)
  2. `POST /api/proposal/v1/proposals/{proposal_id}/imports {section_key:"why", via:"handoff", source:{feature:"competitor", ref_id: ca_…, version, handoff_id, title}}`
     (`feature` 는 서비스 키 — 위 proposal-web 요청 2. 코드 `CA` 로 받아도 같은 뜻)
  3. 받으면 `PATCH …/handoffs/{hof} {status:"delivered"}` 후 `/proposal/{id}/sections/why` 로 이동. 「새 제안서로 시작」은 `POST /proposals {start_mode:"handoff", title, customer:{name}}` 뒤 같은 순서.
- proposal 이 읽을 것: `GET /api/competitor/v1/analyses/{ca}/proposal-handoff?type=&section=why&handoff_id=` → ProposalHandoff v1(`items` = `CM`(경쟁 비교) · `ST`(삼성 강점),
  `facts[]`, 기본 익명 `경쟁사 A · B …`). `named=true` 는 그 넘김 기록에 실명 확인이 있을 때만(없으면 `409 ASK_REQUIRED{kind:"real_names"}`), 실명 응답마다 `served_named_at` 기록.
  `handoff_id` 없이 부르면 익명(안전 기본값). 이 경로는 서비스 간 호출도 받는다(proposal consumes competitor).
- 상태: 안내(경쟁사 쪽 완료 — 반입 잡이 위 응답을 읽어 CM · ST 시트로 넣는지 확인 부탁)

## 공간 시나리오 반입 뒤 사용 등록(usages) — scenario · 2026-10-07
- 필요(09-scenario AC51 · §8): SC5 「제안서에 넣기」 → `POST /v1/proposals/{id}/imports {via:'handoff', source:{feature:'scenario', ref_id, version}}` 는 잘 들어간다
  (`proposal.import_extract` 잡 → 항목 3 · applied 확인). 그런데 넣은 뒤 scenario 에 사용 등록이 오지 않아 SC0 행이 「제안서에 아직 안 넣음」으로 남는다.
- 원하는 것: 반입을 적용(applied)하면 `POST /api/scenario/v1/scenarios/{ref_id}/usages {service: 'proposal', ref: <제안서 id>, label: <제안서 제목>, version: <넣은 시나리오 버전>}`
  (internal, proposal consumes 에 scenario 있음) → 201. 되돌리기(`:undo`) · 제안서 삭제 · 시트 모두 뺌이면 `DELETE /api/scenario/v1/scenarios/{ref_id}/usages/proposal/{제안서 id}` → 204.
  같은 제안서로 다시 넣으면 같은 (service, ref) 기록을 덮어쓴다(중복 없음).
- 참고: 유형을 안 고른 제안서에 넣으면 `TYPE_REQUIRED`(「제안서 유형을 먼저 골라 주세요」)가 오고, SC5 는 그 메시지를 그대로 보여 준다.
- 상태: 요청

## 조감도 반입 뒤 사용 등록(usages) — birdseye · 2026-10-07 (scenario 요청과 같은 모양)
- 필요(08-birdseye AC3 · AC59): BE6 「제안서에 넣기」 → `POST /v1/proposals/{id}/imports {section_key:'birdseye', via:'handoff', source:{feature:'birdseye', ref_id, version, title}, include_keys}` 뒤
  반입을 적용(applied)하면 `POST /api/birdseye/v1/birdseyes/{ref_id}/usages {service:'proposal', ref:<제안서 id>, label:<제안서 제목>, version}`(internal) 를 불러 주세요.
  BE0 「쓰인 곳」 · 「제안서에 쓰인 것만」 필터가 이것으로 채워진다. 반입을 지우면 `DELETE /api/birdseye/v1/birdseyes/{ref_id}/usages/proposal/{제안서 id}`.
- 상태: 요청

## [proposal-web] 실제 백엔드로 e2e 돌리다 본 잡 실패 3건(알림) — proposal-web · 2026-10-07
- 웹 e2e(web/e2e/proposal/backend.spec.ts)를 실제 서비스에 붙여 돌렸더니 아래 잡이 시작 직후 `failed` 로 끝난다. API 응답 모양은 계약대로라 웹은 실패 화면까지만 확인하고 건너뛴다.
  - `proposal.one_click`(POST …/one-click {from_stage:'type'}) → `error {code:'AttributeError', message:"module 'winmate_proposal.graphs.generate' has no attribute 'gen_ensure'"}` (90%에서 멈춤)
  - `proposal.export`(POST …/exports {formats:['pptx'], lang:'ko'}) → `error {code:'TypeError', message:"build() got an unexpected keyword argument 'snapshot'"}`
  - `proposal.reuse`(POST …/reuse {sources:[{kind:'proposal', proposal_id}], mode_pref:'auto'}) → `error {code:'AttributeError', message:"module 'winmate_proposal.content' has no attribute 'content_lines'"}`
- 관찰: `python -m winmate_proposal.worker` 프로세스가 01:34(KST)부터 그대로 떠 있다 — API(리로드)와 워커 코드가 어긋난 것처럼 보인다. 워커를 새 코드로 다시 띄우면 풀리는지 확인 부탁(웹 세션은 dev-bg/pm2 를 건드리지 않는다).
- 화면 쪽: 딸깍 진행 화면은 `OneClickView.status='failed'` 면 오류 띠 + 「딸깍 다시 시도」(같은 from_stage 로 다시 POST) · 「돌아가기」(`next_route`), PR7X 는 오류 띠, PR1C/PRU2 는 `status_label` · `intro` 를 그대로 보여 준다.
- 상태: 알림

## [backend] 3차 — 남은 영역 전부 구현 + 위 요청 처리 — proposal-backend · 2026-10-07
- 이제 501 인 경로가 없다(85 경로 · 99 작업). 2차 뒤에 붙은 것: 시작(RFP 읽기 PR1F · 기존 작업 PR1L 미리보기 · 연결/해제/되살리기) · 반입(사이드바 추출 → 적용 ·
  넘김 include_keys 바로 적용 · 항목 드롭 제품/사례/솔루션/이미지 · 실행 취소) · 딸깍(계획 · 실행 · 메모 · 중지 · 완료 요약) · 확인 항목(확정 · 값 전파 · 노트로 · 질문 · 조사 후보) ·
  검토(workspace 파사드 · 결정 · 시트 확인 · 코멘트 수정안 · 반영 버전 · 공유 링크) · 버전(저장 · 비교 · 바뀐 곳 되돌리기 · 버전으로 되돌리기) · 내보내기(옵션 · 형식 × 언어 · 팀 폴더) ·
  **기존 제안서 활용**(PR1C → PRU2 → PRU2F → PRU3A|B → PRU4|PRU4B → PRU5, 잡 `proposal.reuse` 의 사람 확인 2곳 = `awaiting_input {kind: reuse_confirm_analysis|reuse_confirm_plan, ref: pru_…}`).
- 기존 제안서 활용 메모(웹):
  - `POST …/reuse` 202 뒤 `GET …/reuse` 를 잡 이벤트마다 다시 읽으면 된다(`status` analyzing → awaiting_confirm → planning → awaiting_plan_confirm → applied | failed, `can_confirm`).
    `confirm-analysis` 는 계획을 바로 계산해 두므로 응답 `route`(…/reuse/plan?mode=)로 곧장 가도 `plan_improve|plan_borrow` 가 있다. `plan:confirm` 응답 `route` = 첫 섹션 `?view=compare|guide`
    (또는 then=compose → PR3). 적용(섹션 초안 작성)은 잡이 이어서 하고, 그동안 섹션은 `status=filling` · `fill_job_id` = 그 잡.
  - 요청 4: `PUT …/reuse/mode {mode_pref}`(mode 없이) = PR1C 라디오 「저장만」 → ReuseView. `{mode}` = PRU3 방식 전환(계획을 그 방식으로 바로 다시 계산).
  - 요청 5: `POST …/reuse {sources, replace: true}` = 원본 목록을 그대로 바꿈(빼기), `replace` 없이(false) = 더하기. 마지막 원본까지 빼면 `DELETE …/reuse` → `{ok}`(분석 지움).
  - 요청 7 키: `section_sheets[]` = `{sheet_id, sheet_no, name, title, page, page_label, role, role_name, flow_role, verdict, verdict_label, status(writing|waiting),
    status_label, thumb_url, template_code, selected}` · `placeholders[]` = `{token, label, confirm_item_id, tag}` · `tally` = 원본 대조 `{update, keep, new, drop}` / 흐름 가이드 `{writing, waiting, confirm}` ·
    `flow.pattern {name, en}` · `flow.claims {linked, total}` · `chips[] {no, name, label, state, must}` · `detail` = 기준별 dict(안의 표는 배열: 1 sections · 4 coverage · 5 products/sol_diff ·
    6 numbers · 7 images · 8 mapping · 9 pages/lines(비복제 줄은 글 없이 쪽 · id 만)) · `OneClickView.counts {confirmed, inferred, review}` — 모두 그대로.
  - PRU4 줄 `id` = 시트 content 의 JSON 포인터(`/subtitle` · `/slots/points/0/body` …) → 줄 고치기는 그 경로로 시트 PATCH, 「되돌리기」는 `draft_text` 로 PATCH.
    흐름 차용에서 `view=compare` · `reuse:pull-lines` 는 403 `BORROW_MODE_CONTENT_HIDDEN`. 비복제 줄 id 로 끌어오기는 422 `LINE_NOT_AVAILABLE`.
- 요청 1(SourceChip.ref): `SectionView.sources[].ref` 추가 — 항목 드롭 때 `source.ref` 로 보낸 셸 참조 문자열을 그대로 돌려주고, 없으면 `kb:model:` · `kb:case:` · `kb:solution:` ·
  `kb:image:` · `img:image:` · `ws:item:<ref_id>` 로 만든다. 상태: 완료
- 요청 2(feature 코드): `MI` · `SB` · `CA` … 코드도 받는다(서비스 키로 바꿔 저장). 상태: 완료
- 요청 3(handoff_id 만): spec `sho_` · vp `vho_` 는 `ref_id: ''` 여도 넘김 기록에서 원본 id 를 찾아 반입 · ack 한다(새 제안서 `links[{ref_id: '', handoff_id}]` 도).
  mi · competitor 의 `hof_` 는 그 서비스에 넘김 조회 경로가 없어 **ref_id(분석 id)가 필요**하다 — 없으면 422 `SOURCE_REQUIRED`. MI4 에서 열 때 `?handoff=hof_…&link=mi_…` 처럼 함께 주세요. 상태: 완료(조건부)
- 요청 6(비교 A 쪽 그림): `CompareView.a|b.display`(+ `sheet_id`) — `?sheet=` 가 있으면 그 시트, 없으면 가장 많이 바뀐 시트의 그 버전 display. 상태: 완료
- 요청 8(칸 `type`): 칸 값은 목록 · 문자열 그대로라 값 안에 type 을 넣지 않는다 — 시트 응답 `slot_schema.slots[].type`(export 칸 정의)을 칸 id 로 맞춰 쓰세요. 상태: 안내
- 요청 9: `review:apply-comments` 잡 결과 `result.version`(+ `from_version`) · 내보내기 202 응답과 잡 결과 모두 `export_id`. 상태: 완료(이미 그 모양)
- spec 요청(목록 · 섹션 시트): `GET /v1/proposals?limit=50` → `items[{id, title, type, customer_name, subtitle, meta, …}]` · `GET /v1/proposals/{id}/sections/spec` →
  `{section_no, status_label, owner_name, sheets: [{id, template, title, from: {service, sheet_id}}]}`. ack 의 `section_no` 는 문자열 「08」. 상태: 완료
- IMG4 요청: `GET /v1/proposals?tab=draft,review&limit=20`(쉼표 여러 탭) · `GET /v1/proposals/{id}/image-slots?image_version=` · `POST /v1/proposals/{id}/imports {source: {service: 'image', …}}` 가
  있고 넣으면 image usages 등록 · 빼면 DELETE. 반입 응답은 **200**(201 아님 — 다른 반입과 같은 ImportResult). 상태: 완료
- MI 요청: `POST …/imports {via: 'handoff', source: {feature: 'MI'|'mi', ref_id, version, handoff_id}, include_keys}` → 고른 시트만 바로 적용, workspace 항목 `meta.proposal_type` 있음. 상태: 완료
- competitor(CA5) 확인: `section=why` 넘김(handoff_id 포함)을 읽어 CM · ST 시트로 넣는다(경쟁사는 익명 라벨, 실명은 V5 검사). 상태: 완료
- scenario · birdseye 사용 등록: 반입 적용 때 `POST …/usages`, 반입 실행 취소(같은 작업 연결이 더 없을 때) · 연결 해제 때 `DELETE …/usages/proposal/{제안서 id}`. 상태: 완료
- [backend] 계약 변경(깨지지 않음): `ModePut.mode` 선택 + `mode_pref` · `ReuseStart.replace` · `DELETE /proposals/{id}/reuse` · `SourceChip.ref` · `CompareSide.sheet_id|display`.

## Value Props 넘김 · 초안 경로 안내 — vp · 2026-10-07
- 넘김(VP4 `제안서에 {n}시트 보내기`): vp 가 `POST /api/vp/v1/vps/{vp_id}/handoffs` → `201 {id: 'vho_…', open_route, package}`(퀵윈인데 한 문장 버전이 없으면 202 잡 뒤 같은 모양).
  `open_route` = `/proposal/{pid}/sections/vp?handoff=vho_…` | `/proposal/new?handoff=vho_…`.
- 제안서 화면: `GET /api/vp/v1/handoffs/{vho}` → `{id, vp_id, proposal_type, package{sheets[{sheet_id, role, template_code, title, points, slots, notes}], sources_footer}, status}`
  로 묶음을 당겨 넣고, 서버에서 `POST /v1/handoffs/{vho}:ack`(internal) `{result: applied|needs_confirmation|failed, applied_sheet_ids, pinned_conflicts?, proposal_id, proposal_title}`.
  `needs_confirmation` 이면 VP 작업에 `제안서 확인` 확인할 것을 남기고, `applied` 면 VP0 `연결된 제안서` 가 그 제목이 된다.
- 섹션 읽기: `GET /api/vp/v1/value-props/{vp_id}/proposal-handoff?type=standard|quickwin|solution&section=vp`(= `/v1/vps/{id}/proposal-handoff`) — 10-proposal §6.6 모양.
- V2 초안(작업 없이): `POST /v1/value-props:draft`(internal) `{customer_name, proposal_type, sheet_roles?, industry_code?, products?, rq_ref?, sources[], proposal_id?, proposal_title?, project_id?}`
  → `202 {value_prop_id, job_id}` — 잡이 재료 → 생성까지 기본값으로 끝내면 위 섹션 읽기로 가져가면 된다.
- 상태: 완료(vp 계약)
- 정정(vp): `GET /v1/handoffs/{vho}` 응답 = `Handoff {id, vp_id, vp_version, proposal_id, proposal_type, options, package{…, sheets[{sheet_id, role, layout, title, points, content, image_slots, speaker_notes, pinned}]}, status, open_route, created_at, acked_at}` — 계약 `contracts/vp.json` 이 기준.

## [proposal-web] 요청 정리 — [backend] 3차 답 반영 — proposal-web · 2026-10-07
- 1 SourceChip.ref → 웹이 `sources[].ref`(kb: · img:)를 상단바 `added` 로 넘긴다(새로고침 뒤에도 「✓ 추가됨」, AC-091). 상태: 완료
- 2 feature 코드 → 웹은 서비스 키로 보낸다(서버가 코드도 받음). 상태: 완료
- 3 넘김 → 웹: `?handoff=hof_…` 면 `?link=`(분석 id)를 `source.ref_id` 로 함께, `/proposal/new?handoff=hof_…&link=…` 는 links 한 항목 `{feature, ref_id, handoff_id}` 로 보낸다. `vho_` → `vp`. 상태: 완료
- 4 mode_pref → PR1C 라디오가 분석이 있으면 `PUT …/reuse/mode {mode_pref}`(저장만), PRU2 → PRU3 는 `ReuseView.mode_pref` 로 연다. 상태: 완료
- 5 원본 빼기 → 웹은 늘 화면의 원본 목록 전체를 `replace: true` 로 보내고, 마지막 원본을 빼면 `DELETE …/reuse`. 상태: 완료
- 6 비교 A 쪽 → `CompareSide.display` 로 A · B 슬라이드를 그린다(PNG 가 있으면 PNG). 상태: 완료
- 7 키 → 그대로 읽는다. 추가로 `section_sheets[].selected` 로 현재 시트 표시, PRU4 줄 `id`(JSON 포인터)를 그대로 시트 PATCH 경로로 쓴다. 상태: 완료
- 8 칸 type → 안내 확인. 웹은 모양으로 판단하는 지금 방식을 유지(`slot_schema.slots[].type · box · label` 활용은 다음 개선). 상태: 닫음
- 9 잡 결과 키 → 확인. 상태: 완료
- 잡 실패 알림(위) → 워커 재시작 뒤 실제 e2e 에서 딸깍 · 내보내기 · 기존 제안서 활용(PR1C → PRU2 → PRU3 → PRU4) 모두 통과. 상태: 닫음
- 새로 본 것(선택): 활용 계획 확정 직후(`plan:confirm` 응답 `status: applying`) 1–2초 동안 `GET …/sections/{key}` 가 422 `SECTION_NOT_IN_TYPE`,
  `…/reuse-view` 가 404 `REUSE_NOT_FOUND` 다. 웹은 그 섹션이 열릴 때까지(최대 30초) 기다렸다가 이동하고 reuse-view 404 는 몇 번 다시 읽어 비켜 두었다.
  plan:confirm 이 응답하기 전에 유형 · 시트 구성을 먼저 적용해 주면 이 기다림이 필요 없다. 상태: 요청(선택)

- 상태(birdseye · 2026-10-07): 「조감도 반입 뒤 사용 등록(usages)」 요청은 proposal-backend 3차 「scenario · birdseye 사용 등록 … 완료」로 해결 — 닫음.

## `GET /v1/templates/{code}` 500 고침 — 목록 우회 없애도 됨 — export · 2026-10-07
- 필요: docs/requests/export.md 「…135종에서 500」 완료. 카탈로그 전 코드(표시 코드 · 별칭 n 포함) 상세가 200 이다(회귀 테스트로 지킴).
  `slots[].default` 는 글 · **목록**(표 머리 같은 count 칸 — 항목별 기본값, 합치지 않음) · **숫자**(예 `GN-*.recommended`) 중 하나, 보드 없는(제작 중) 템플릿은
  `source.board` 가 빠지고 `source.note` 에 사유. 웹 타입: `default?: string | number | string[] | null` · `board?: string | null`.
- 제안 API: 그대로 `GET /api/export/v1/templates/{code}` — 목록 우회(`?codes=…&include_slots=true`)를 걷어 내도 된다(pm2 의 export 를 다시 띄운 뒤).
- 상태: 요청(export → proposal 안내)

## 통합 세션 처리 — integration · 2026-10-07
- 「plan:confirm 이 응답하기 전에 유형 · 시트 구성을 먼저 적용」(위 proposal-web 새로 본 것): 완료 — `ops/reuse.confirm_plan` 이 잡 신호 전에 유형(`set_type`) · 기존 제안서 표시를 먼저 적용하고,
  켜진 섹션을 `status: filling`(`fill_job_id`)으로 둔다. 잡이 취소되면 그 섹션들을 원래 상태로 되돌린다(`graphs/reuse.handle`). 응답 직후 `GET …/sections/{key}` 422 없음.
- `hof_` 겹침(mi · competitor 둘 다 `hof_`): 완료 — 백엔드 `defs.feature_for_ref`(작업 id 접두사 mi_/ca_/vp_/sp_/img_/be_/sc_ 가 가리키는 기능 우선) — 반입 · 링크가 접두사로 기능을 바로잡는다.
  웹 `lib/routes.handoffFeature`(feature → link/ref 접두사 → sho_/vho_ → 섹션 기본) — `/proposal/new?handoff=hof_…&link=ca_…` 가 competitor 로 간다.
- 넘김 섹션 대체: 유형에 없는 섹션으로 넘기면(SC5 → standard 「solution」 없음 등) 422 대신 그 기능의 기본 섹션(`defs.WORK_TARGETS`)으로, 반입 `requested_section` 기록.
  넘김(via=handoff) 항목은 역할로 섹션을 다시 고른다(BE6 SM-B → spaceProducts, SC5 SXS → solution) — `ImportItem.section_key`(추가 필드, 계약 갱신). 다른 섹션으로 옮긴 넘김은 남의 역할을 그 섹션 구성에 더하지 않는다.
- include_keys 없는 넘김(VP4 등): `include_default` 로 체크(EF 누락 고침). VP 링크 제목 = VP 제목(`GET /v1/vps/{id}`), VP ack 에 `proposal_id` · `proposal_title`(VP0 연결된 제안서 id 가 None 이던 것).
- 만들기: `project_id` 를 넘긴 작업(rq_ref · links · image work)의 workspace 항목에서 이어받는다. `rq_ref` 면 정의서 고객 · 제목을 PR1 에 채운다.
- 지우기: birdseye · scenario · image 사용 등록, requirements 링크를 함께 푼다(`_release_usages`). spec 링크 · VP linked_proposal 은 아직 남는다(남은 틈).
- export 템플릿 상세 500 고침 안내(아래): 확인 — `clients.template_detail` 은 상세를 먼저 부르고 실패할 때만 목록(include_slots)이라 그대로 둔다.
