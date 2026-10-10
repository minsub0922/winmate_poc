# vp 요청

## Storyboard Key Message 읽기 · 다듬은 문장 되돌려 쓰기 경로 안내 — storyboard · 2026-10-06
- 필요: 05-vp E3 `Storyboard에서`(Key Message 를 가치 기둥으로) · VP 가 다듬은 문장을 Storyboard 에 되돌려 쓰기(02-storyboard §1.3).
- 읽기: `GET /v1/storyboards/{sb_id}/key-messages` → `{items: [{id: kmsg_…, place_label, axis_label, audience, text, flags[], evidence[]}]}`
  (vp 는 consumes 에 storyboard 가 있다 — `ServiceClient("storyboard")`).
- 되돌려 쓰기: `PATCH /v1/storyboards/{sb_id}/key-messages/{kmsg_id} {text, source: {service: "vp", ref_id: <vp_id>}}` → `KeyMessage`
  (표현 검사를 다시 하고 변경 기록 원인 `VP 문장 반영`).
- 상태: 완료(안내 — storyboard 계약에 있음)
- vp 처리: 반영함 — 읽기는 `sources.py`(Storyboard 연결 → Key Message 를 가치 축 재료로), 되돌려 쓰기는 VP4 넘김 옵션 `다듬은 Key Message를 Storyboard에도 반영`(넘길 때 `PATCH …/key-messages/{kmsg_id}`). 상태: 완료 · vp · 2026-10-07

## `GET /v1/templates/{code}` 500 고침(`VP-FB-*` 등) — export · 2026-10-07
- 필요: 업종 VP(`VP-<업종>-A..C`)는 캔버스 보드가 없어(제작 중) 원본 `board` 가 null 이라 상세가 500 이었다 — 고침. 지금은 200 이고 `source.board` 가 빠진 채
  `source.note`(「캔버스 보드 없음(제작 중) — 같은 역할 바탕 레이아웃 사용」)가 온다. 목록 기본값(`slots[].default` 가 목록 · 숫자일 수 있음)도 함께 고침.
- 제안 API: 그대로 `GET /api/export/v1/templates/{code}`(pm2 의 export 를 다시 띄운 뒤). 우회 코드가 있으면 걷어 내도 된다.
- 상태: 요청(export → vp 안내)

## 통합 세션 처리 — integration · 2026-10-07
- 제안서를 지워도 VP0 「연결된 제안서」가 지운 제안서를 가리키던 것: 완료 — 새 internal `POST /v1/vps/{vp_id}:release-proposal {proposal_id}`
  → `{vp_id, proposal_id, released, linked_proposal}`(그 제안서면 비우고, 다른 제안서로 넘긴 기록이 있으면 가장 최근 것으로 · 보낼 제안서 `target_proposal` 도 비움 · 넘김 기록에 `released_at`).
  proposal 이 제안서를 지울 때 VP 연결마다 부른다. 테스트 `test_api.py::test_export_and_handoff_contract`(pytest 30), 계약 갱신.
- VP4 넘김: include_keys 없이 보내도 EF(기대 효과)가 들어가고, 제안서 쪽 연결 제목 = VP 제목, ack 에 `proposal_id` · `proposal_title`(proposal 쪽에서 고침).
- VP4 「공간 시나리오」(`/scenario/new?from=vp:{id}`): scenario SC1 이 이해관계자별 가치 · 과제 · 제품을 입력 줄로 받는다(scenario 쪽에서 고침).
- 템플릿 상세 500 고침 안내(위, export): VP 웹 · 서버에 목록 우회 코드 없음 — 할 일 없음(pm2 export 재시작 뒤 그대로).
- 보충(integration): `exporting._template_ready` 가 export 상세 호출 실패(500)까지 「준비 안 됨」으로 프로세스 내내 기억하던 것 → 실패는 기억하지 않게(export 재시작 뒤 vp 재시작 없이 바로 반영).
- 보충(integration): 제안서에서 VP 반입을 실행 취소해 그 VP 연결이 하나도 안 남으면 proposal 이 `:release-proposal` 을 부른다.

## 허브 완료 화면 머리 = 보드 Done(짧은 이름) — storyboard · 2026-10-10
- 바뀐 것(허브 `/v1/flows*`, 응답 모양 그대로): `PUT /v1/flows/{id}/stages/{key}` 의 `md_added`(→ `push_stage` · 각 서비스 `flow_sync.md_added`) 첫 줄을
  보드 Done 머리(짧은 이름 · 번호 없음)로 바꿨다 — `## 요구사항 · RQ-06 v1` · `## DSS · …` · `## MI · MI-01 v2` · `## 경쟁사 · CA-01 v1` · `## VP · …` · `## Spec · …` · `## 시나리오 · …`.
  요약본 전체(`summary_md`)는 그대로 보드 SB1 형식(`## 1. 고객 요구사항 · RQ-01 v2` · `## 3. Market Intelligence · MI-01 v1`), 「남은 것」 줄의 시나리오는 `공간 시나리오`.
  함께: flow.json `progress` 는 보드 값 `rq` · `dss+n/5`(화면 문구 `FlowDoc.progress` 는 그대로), `keyPillars` 는 받쳐 줄 메시지가 있을 때만, 분기(`:branch`)는 Key message 를 복사하지 않는다(보드 SB0 · SBPopup).
- 맞출 곳: `services/vp/tests/test_value_maps.py:101` `md_added.startswith("## Value Proposition · VP-")` → `"## VP · VP-"`.
- 상태: 완료(2026-10-10 플랫폼 통합 때 테스트 기대 문자열을 고침)
