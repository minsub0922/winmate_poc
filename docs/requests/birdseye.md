# birdseye 요청

## 이미지 렌더 API 경로 안내 — image · 2026-10-06
- 안내(계약 `contracts/image.json`, 07-image §6.9 · §7.9 — birdseye 가 image 를 consumes 해야 한다. 조감도는 T2I 를 직접 부르지 않는다):
  `POST /v1/renders {origin: {service: 'birdseye', ref: <조감도 id>}, kind: 'birdseye', prompt: {subject_ko, details_ko[]}, aspect: '16:9', target: 'uhd',
  structure_ref_file_id: <배치 도면 · 결정적 합성 초안 file id>, product_refs: [{model_code, qty}], expect?, forbid[], allow_people, confidential}`(internal)
  → `202 {job_id, render_id}` → `GET /v1/renders/{id}`(uhd = 3840×2160 렌디션 · `generation.origin.service='birdseye'`).
  structure_ref 는 참조 1순위(「이 구도 · 배치를 정확히 따름」), 모델이 참조를 못 받고 편집만 되면 `t2i.edit(edit_of=structure_ref)` 로 바꿔 부른다(메타에 경로 기록).
- IMG4 「조감도 참조로」는 웹 이동만 한다: `/birdseye/new?ref_version=imv_…` — 버전 내용은 `GET /v1/versions/{id}`(렌디션 file id · 생성 메타).
  조감도에 쓰면 `POST /v1/images/{image_id}/usages {version_id, service: 'birdseye', ref, label}`(internal).
- 상태: 완료(안내 — image 계약에 있음)

## SC1B · SC0 · SC1 이 읽는 조감도 경로 · handoff 필드 — scenario · 2026-10-07
- 필요(09-scenario §4.1 · §4.2 · §4.4 · §8, AC 3 · 7 · 11–14): scenario 가 서버에서 부른다(consumes 에 birdseye 있음). 지금 `contracts/birdseye.json` 에 경로가 없어
  scenario 는 08 문서 모양의 가짜로 시험하고, 계약에 경로가 생기면 자동으로 엄격 검증으로 바꿔 부른다(그 전에는 검증 없이 호출, 실패하면 빈 값).
- 쓰는 경로(08 §6.1 · §6.7 그대로): `GET /v1/birdseyes?limit=50`(내 조감도 · 팀 공유) · `GET /v1/birdseyes/{id}/version` → `{version, layout_version, updated_at, zones_hash}` ·
  `GET /v1/birdseyes/{id}/handoff` · `POST /v1/birdseyes {title, description, prefill: {products: [family_id]}, origin: {service: 'scenario', ref: sc_…}, project_id?}` → 201 `{id, title}` ·
  `POST /v1/birdseyes/{id}/usages {service: 'scenario', ref: sc_…, label, version}` → 201.
- 목록 행에 꼭 필요한 것: `id` · `title` · `zone_count`(존 포인트 수 — SC1 「조감도 작업 {n}개」 · SC1B 「{제목} · 존 {n}」) · `version`.
- handoff 에 더해 주세요(08 §8 묶음에 없는 것):
  - `zones.points[]` 마다 `id`(bez_…) · `short_name`(동선 칩 「쇼윈도」 「미디어월」) · `path_order`(동선 순서) · `u` · `v`(0..1, 주 컷 위 위치 — VM-C 핀) ·
    `products: [{family_id, model_code?, label('Outdoor Signage OH55C'), short('OH55C'), qty}]`(그 존에 배치된 제품 묶음) · `furniture: [{name, qty}]`(가구만 있는 존 판정).
    `text`(존 의미 한 줄, 「거리에서 보이는 첫인상」)는 SC1B 부제 「{제품 라벨} · {존 의미 한 줄}」에 그대로 쓴다.
  - `plan_preview: {zone_count, area_pyeong, ceiling_h_m, window_label('전면 유리창 (도로측)'), zones: [{id, n, x, y}], items?: [{kind: 'product'|'furniture', x, y, w, d}], file_id?}` —
    SC1B 평면 미리보기(「존 포인트 5」 「120평 · 층고 4.5m」 「전면 유리창 (도로측)」, 존 번호 원, 범례 「삼성 제품」 「가구」). 없으면 scenario 는 `space` 와 존 u · v 로 대신 그린다.
  - `customer`(문자열 또는 `{name, industry?}`) — 시나리오 고객 · 업종(시나리오 축 제안)에 쓴다.
- BE5Z 장면 연결 모드(`/birdseye/{id}/zones?scenario=sc_…`): 웹이 `GET /api/scenario/v1/scenarios/{sc}/scenes` 로 장면(번호 · 제목 · 장소)을 읽으면 된다.
- 상태: 요청
- 상태(birdseye · 2026-10-07): 반영 — `contracts/birdseye.json` 에 경로 공개. `GET /v1/birdseyes` 행에 `id · title · zone_count · version · layout_version`,
  `GET /v1/birdseyes/{id}/version` → `{version, layout_version, updated_at, zones_hash, rev}`, `GET /v1/birdseyes/{id}/handoff` 의 `zones.points[]` 에
  `id · zone_id · short_name · path_order · u · v · products[{family_id, model_code, label, short, qty, group_label}] · furniture[{name, qty}] · text · subtitle`,
  `plan_preview{zone_count, area_pyeong, ceiling_h_m, window_label, zones[{id, n, x, y}], items[{kind, x, y, w, d}], file_id?}`, `customer`(문자열).
  `POST /v1/birdseyes {title, description, prefill:{products:[family_id]}, origin:{service:'scenario', ref}}` → 201 Birdseye(`id`, `title` 포함 — 단계는 1 공간 입력에서 시작),
  `POST /v1/birdseyes/{id}/usages {service, ref, label, version}` → 201(internal).

## kb 모델 상세 · 배치 규칙 새 필드 쓰기 — kb · 2026-10-07
- 필요: docs/requests/kb.md birdseye 요청의 답(맨 아래 `kb 답변`). `pm2 restart kb` 뒤.
  - / 든 코드: `GET /v1/models/{quote(code, safe="")}`(%2F) — 목록 행 대신 상세를 읽으세요.
  - 치수: 상세 `dims_mm {w, h, d}`(mm, 없으면 null) — 정규식 대신. `dims_all` 에 스탠드 포함 · 포장 등.
  - LED: `values.size` 의 12" · 16" 은 kb 버그(피치 코드를 인치로 읽음)였고 이제 null 이다. `led.pixel_pitch_mm` · `led.unit_active_mm`(픽셀×피치, 캐비닛/단위 발광 면적) ·
    `led.size_mentions`(IAC `최대 130인치`)를 쓸 수 있고, 화면 구성 옵션 표는 KB 에 없다(그대로 `[확인 필요]`).
  - 배치 규칙: `param_status == 'approved'` 일 때만 `param_values` 로 덮어쓰기(지금 KB 는 전부 `unfilled`) — `params` 원문에는 `<<FILL>>` 문자열이 있다. `category=` 에 KB 분류 id 도 된다.
- 상태: 요청(kb → birdseye 안내)

## 통합 세션 처리 — integration · 2026-10-07
- BE6 「제안서에 넣기」: 기본 대상 = `origin.return_to` 의 제안서 → 같은 프로젝트 제안서 → 첫 줄(`pages/ExportPage.tsx`), 완료 토스트 「열기」는 응답 `section_key` 섹션으로.
  proposal 이 넘김 항목을 역할로 나눈다 — BV · ZP 는 조감도 섹션, 수량표 SM 은 「공간별 제품」 섹션(표준). 퀵윈 · 솔루션처럼 섹션이 없으면 기본 섹션으로 대체.
- BE6 「Spec 시작」 → `/spec/new?models=…&from=birdseye:{id}`(Spec 시트 origin 이 조감도). 제안서 「조감도 새로 만들기」 → `/birdseye/new?return_to=…`(BE1 이 `return_to` 를 읽고 옛 `?return=` 도 받음).
- 렌더 mock QC 「제품 수 다름」(image 요청): image 쪽에서 완료 — mock 이면 조감도 컷이 `done`.
- 제안서를 지우면 조감도 사용 등록(`DELETE …/usages/proposal/{pr}`)이 풀린다.
- 참고: `make e2e-feature SERVICE=birdseye` 의 `inputs.spec.ts:41`(휴대폰 올리기)이 처음 한 번 8초 안에 `be-mobile` 을 못 찾고 실패했다가 다시 돌리면 통과 — 새 브라우저 문맥에서 Vite 첫 변환이 느린 탓으로 보임(코드 문제 아님).
