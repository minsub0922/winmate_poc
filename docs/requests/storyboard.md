# storyboard 요청

## 허브 「PPT 제작 · B2B 제안서」 칸(stages.ppt) 비우기 — proposal · 2026-10-10
- 필요: proposal 이 허브 Storyboard(SB-nn)에서 시작한 제안서를 `PUT /v1/flows/{id}/stages/ppt`(internal, `push_stage`)로 기록한다
  (`ref` = `PR-nn`, `res_id` = 제안서 id → `cells[ppt].route` = `/proposal/{pr_…}`, `value` = `{proposal_id, title, customer, type, type_name, status, sections, route}`, 카드 · 요약 줄 포함).
  제안서를 지우면 SB1 「PPT 제작 · B2B 제안서」 칸이 지운 제안서를 계속 가리킨다 — 지금 허브에는 stage 를 지우는 경로가 없다.
- 제안 API: `DELETE /v1/flows/{flow_id}/stages/{key}`(internal, 우선 `ppt` 만 허용 · `ref` 를 주면 그 ref 일 때만 지움) → `FlowStageOut`(md_added 빈 문자열).
  같은 ref 를 가진 다른 Storyboard 도 같이 비운다(PUT 과 같은 규칙). 생기면 proposal 이 제안서 지우기(`_release_usages`)에서 부른다.
- 상태: 완료(2026-10-10) — `DELETE /v1/flows/{flow_id}/stages/{key}?ref=`(internal, `ppt` 만 · 다른 키는 422 STAGE_NOT_CLEARABLE · ref 가 다르면 그대로). proposal `hub.clear_ppt` 가 제안서 지우기에서 부른다.

## workspace 색인 meta 에 고객사 · 버전 — proposal · 2026-10-10
- 필요: 허브 Storyboard 의 workspace 항목(`register_item(feature="SB", meta={kind, parent, key_message})`)에 고객사 · 버전이 없어
  ① PR1 「최근 Storyboard … 채울까요?」 카드가 고객사로 거를 때 요약 문자열(`SB-06 · E 자산운용 · …`)에 기대고,
  ② 제안서 목록의 「Storyboard 작업 업데이트됨」(연결 뒤 허브가 바뀜 — `meta.version` 비교)을 허브 연결에는 못 띄운다(시각 비교는 형식이 달라 끔).
- 제안: `meta` 에 `customer`(flow.customer) · `version`(flow 문서 version, stage 를 넣을 때마다 오름)을 더한다. 응답 모양 · 경로는 그대로.
- 상태: 완료(2026-10-10) — `meta.customer` · `meta.version` 추가. 단 `version` 은 문서 판이 아니라 **콘텐츠 판 `content_rev`**(stage — ppt 칸 제외 · Key message · 요약본이 바뀔 때만 오름). 제안서가 ppt 칸에 자기를 적는 것으로 「업데이트됨」이 뜨지 않게. 흐름 응답에도 `content_rev` 가 있다.
