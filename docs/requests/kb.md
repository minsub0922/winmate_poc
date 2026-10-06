
## Spec 시트가 쓰는 kb 값 보강 4건 — spec · 2026-10-06
- 필요 1(보증 연수): 기본 7항목인 `보증` 행이 kb 에 원천이 없어 늘 `[확정 필요]` + 값 확인으로 남는다(06-spec §4.15.8). spec 은 지어내지 않는다.
  제안: 모델 · 제품군 상세(`GET /v1/models/{code}` · 제품군)에 `warranty: {years, scope?, source_ref, as_of}`.
- 필요 2(생애주기 · 후속, C5): 단종 경고(§4.17.2)와 proposal P3 `lifecycle:check` 가 후속 모델을 kb 에서 받지 못해 spec `config/lifecycle.yaml`(지금 비어 있음)에 기댄다.
  제안: `GET /v1/models/{code}/lifecycle` 에 `successors: [{model_code, relation: 'successor'|'similar', reason}]`(또는 질의 C5).
  아울러 모델 상세 `sale_status_code` 값의 뜻(판매 중 · 단종 · 단종 예정) 표를 계약 설명에 적어 주세요 — 지금 spec 은 해석하지 않고 `unknown` 으로 둔다.
- 필요 3(A3 단위): `POST /v1/query/A3` 가 `55인치 이상` 을 `screen_size_cm` · 55 로 돌려준다. spec 은 문장에 `인치` · `inch` · `"` 가 있으면 `screen_size_inch` 로 고쳐 쓴다(§9.4-30).
  제안: 인치 표현이면 `screen_size_inch` 로, 아니면 cm 값으로 바꿔(×2.54) 돌려주기.
- 필요 4(소비전력 Typical · Max): kb 사이니지 모델은 `On Mode` · `Sleep Mode` 만 있어 `소비전력 (일반 · 최대)` 이 늘 값 확인으로 남는다(On Mode 는 `다른 측정값` 칩으로만 제안).
  원천에 Typical · Max 가 있으면 속성으로 노출해 주세요.
- 상태: 요청

## 업종 인사이트 요구 태그 이름표 · 6업종 대응 — mi · 2026-10-06
- 필요(03-mi §4.8 MI1I · §5.7 · §11 Q2): `GET /v1/segments/{code}/insights` 의 `req_types[]` 에 `label` 이 없어(R01~R24 한국어 이름표 없음)
  mi 는 그 태그 사례 문장 중 안 쓴 첫 문장을 이름으로 쓴다(`label_basis: "example"`). 같은 문장이 여러 태그 예시에 겹쳐 이름이 태그 뜻과 어긋날 수 있다.
  제안: `req_types[]: {code, label, n, examples[]}` 의 `label` 을 R01~R24 고정 이름표로 채우기(예 R08 `인건비 절감`, R03 `본사 일괄 콘텐츠 제어`).
- 필요: `GET /v1/segments` 에서 SV · TP · VN · AD · ID · OE 6업종이 `mapping: false`(KR 업종 대응 `<<FILL>>`)다. mi 는 이 업종도 사례 수를 그대로 보이지만
  업종 판별 `사례비율` · MI1I 집계의 근거가 약하다. 제안: 사례 → 16업종 분류표(사례 1건 = 업종 1개)로 6업종 대응을 채우고 `mapping: true` 로.
- 상태: 요청(급하지 않음 — 지금도 화면은 돈다)

## 요구 유형 R01~R24 이름표 — competitor · 2026-10-07 (mi 요청과 같음)
- 필요: 04-competitor §7.5 비교 기준 `업종 사례 {n}건` 이름도 `GET /v1/segments/{code}/insights` 의 `req_types[].label` 이 비어 있어,
  competitor 는 LLM(`ca.make_criteria`)이 지은 10자 이름 → 실패하면 예시 문장을 줄여 쓴다. 고정 이름표(R08 `인건비 절감` …)가 있으면 그걸 먼저 쓴다(코드는 이미 `label` 을 먼저 읽음).
- 상태: 요청(위 mi 요청에 +1)

## 모델 코드에 / 가 든 모델 상세 · LED 크기 · 배치 규칙 파라미터 — birdseye · 2026-10-07
- 필요 1: `GET /v1/models/{model_code}` 가 `LH012IWCMWS/XU` 같은 / 든 코드(실내용 The Wall IWC 등)를 못 찾는다(`%2F` 도 404 — 경로 매개변수가 / 를 못 받음).
  birdseye 는 `GET /v1/models?q=<코드>` 목록 행으로 대신 읽어(스펙 표 없음) 치수를 `[확인 필요]`(estimated)로 둔다.
  제안: `{model_code:path}` 로 받거나 `GET /v1/models/by-code?code=` 추가.
- 필요 2: The Wall(IWC · IWA …) 제품군 크기 칸이 `12"` · `16"` 이다 — 화면 대각이 아니라 모듈(캐비닛) 크기로 보인다. 조감도는 LED 의 30" 미만 값을 화면 크기로 쓰지 않고
  치수를 `[확인 필요]` 로 둔다. 화면 구성 옵션(예 146" · 110" 등, 가로×세로 mm)이 있으면 `values.size` 와 별도로(`screen_options[]`) 주세요.
- 필요 3(08 §10.3): `GET /v1/placement-rules` 를 엔진 파라미터 기본값 위에 덮어 쓴다(`rule_id` 같으면 `params` 교체 · `param_status` 그대로 표시).
  지금 응답이 비어 있어 `services/birdseye/config/rules.yaml`(draft) 값만 쓴다. 사람 승인 값이 생기면 `param_status: 'approved'` 로 주세요.
- 필요 4: 모델 상세 스펙의 「제품 크기」(가로×높이×깊이 mm) 행이 모델마다 이름 · 단위가 달라 정규식으로 읽는다. `dims_mm: {w, h, d}` 정규화 칸이 있으면 좋겠다.
- 상태: 요청

## kb 답변 — 위 요청 4묶음 · 2026-10-07 (계약 `contracts/kb.json` 갱신, 더한 필드만 · 경로 그대로 · 반영은 `pm2 restart kb` 뒤)
- 상태(kb · 2026-10-07) ↑「Spec 시트가 쓰는 kb 값 보강 4건 — spec」 필요 1(보증): 완료 + 데이터 공백 — `GET /v1/models/{code}` · `POST /v1/spec/table` 의 `derived[code]` · `/lifecycle` 에
  `warranty {status, years, months, parts_years, text, attr, source_ref, source_url, as_of, claims[]}`(스펙 API `품질보증기준` · `품질 보증 기간` 행 원문, 없으면 null).
  사이니지 · TV · 모니터(LCD 65 · LED 10 모델 등)는 원문이 `소비자분쟁해결기준에 따라 보상 가능` 문구뿐이라 `status=statement_only` · `years=null` — 연수는 KB 에 없다(지어내지 않음, `[확정 필요]` 유지).
  연수가 있는 것: 프린터 1년 · LED 조명 2년(부품보유 3년) · 에어컨 청소 3개월. PDP 의 `10년 무상보증`(모터 · 컴프레서) 같은 문구는 `claims` 로만 준다(제품 연수 아님).
- 상태(kb · 2026-10-07) ↑ spec 필요 2(후속 · sale_status_code): 부분 완료 — `/v1/models/{code}/lifecycle` 에 `successors[{model_code, id, display_name, relation, reason, newer, release_ym, basis}]` · `release_ym`.
  공식 후속(DR10)은 KB 에 없어 `successor=null` 그대로, relation 은 `similar` 만 준다: 사이니지 코드 규칙으로 같은 계열 · 같은 크기(LED 는 같은 피치 코드)의 다른 세대 KB 모델 +
  스펙 `동일모델의 출시년월`로 `newer`(예 WM55B → WM55F 2026-03 newer=true · KB 에 없는 QM55R → QM55C · IWA → IWC). 원본보다 오래된 후보는 빼고 최근 출시 먼저, 사이니지 밖 모델은 [].
  `sale_status_code` 뜻: 데이터 공백(코드표 없음). 관측값은 '17'(589 제품군) · '15'(16 제품군) 둘뿐이고 둘 다 수집 시점 사이트 목록 노출 상품 = 판매 중(DR09). 단종 · 단종 예정 코드는 수집본에 없다
  (목록에서 빠진 모델은 KB 에 없음 → `status=not_in_catalog`). 이 표를 계약 설명(ModelDetail · FamilyItem · Lifecycle `sale_status_code`)에 적었다 — spec 은 계속 해석하지 않는 편이 맞다.
- 상태(kb · 2026-10-07) ↑ spec 필요 3(A3 단위): 완료 — `화면 크기` + `55인치 이상` 은 10-06 부터 `screen_size_inch`(+`value_cm` 139.7)였다(지금 pm2 kb 에서도 확인). 못 잡던 꼴을 보강:
  `55형이상` · `55”` · `55''` · `55 inch`, 같은 이름 항목 여럿(입력 순서로 짝짓기), 이름이 인치인데 값이 cm(→ `screen_size_cm` + `value_inch`), 이름이 `크기` · 빈칸이어도 값이 인치 표현이면 inch(`mapped_by: inch_expression`).
  크기 항목마다 `unit_basis`(value · name · default) — 단위 없는 값은 KB 기본 cm 로 읽고 `needs_confirmation` 에 `단위가 없어 cm 로 읽음` 을 단다. spec 쪽 인치 보정은 `unit_basis` 로 대신할 수 있다.
- 상태(kb · 2026-10-07) ↑ spec 필요 4(소비전력): 완료 + 데이터 공백 — `POST /v1/spec/table` `derived[code].power {typical, max, values[{mode, value, unit, per_m2, raw, attr, spec_value_id}]}`.
  원천: LCD 사이니지 `소비전력 (Typical)` 은 14개 모델(BEH · BEF · BED · WMF)에만 있고, QMC 등은 On Mode · Sleep 뿐(→ `typical=null`, On Mode 는 typical 로 보지 않음).
  `(Max)` 는 LCD 사이니지에 없다. LED 는 Max 가 ㎡당 값(`410 W/㎡`, 9개 모델 → `unit='W/㎡'` · `per_m2=true`). 모니터 · 호텔 TV 는 Typical · Max 둘 다 있다.
- 상태(kb · 2026-10-07) ↑「업종 인사이트 요구 태그 이름표 · 6업종 대응 — mi」+「요구 유형 R01~R24 이름표 — competitor」 이름표: 데이터 공백 — R01~R24 코드표가 winmate-kb 어디에도 없다
  (KB 에는 코드만, 이전 세션 LLM 추출 원본 `raw/prior_case_studies.json` 도 없음) → `label` 은 계속 null. 대신 `req_types[]` 에 `examples_specific`(이 태그에 두드러진 요구 문장 상위 3,
  같은 응답에서 앞 태그가 쓴 문장은 빼서 태그끼리 안 겹침) · `hint_terms`(태그 lift 낱말 ≤5)를 더했다 — 이름표 아님(계산값). 참고로 낱말 통계상 R03 은 인테리어 · 디자인, R08 은 주문 · 결제 · 대기 문장과
  더 엮인다 — 요청에 든 예시 이름(R08 `인건비 절감`, R03 `본사 일괄 콘텐츠 제어`)과 다를 수 있으니 고정 이름표는 코드표 원본으로 확인해야 한다. 코드표 파일을 주면 `curation/req_tags.yaml` 로 `label` 을 채운다.
- 상태(kb · 2026-10-07) ↑ mi 6업종 대응: 부분 완료 — 시드 대응(`kr_vertical_ids`, `<<FILL>>`)은 사람 결정이라 비워 둔 채, `GET /v1/segments` 항목에 `mapping` · `mapping_basis`(seed · observed_cases · null) ·
  `kr_vertical_ids_observed` · `observed_kr_verticals[{id, name, n}]` · `case_basis{prior, clue_only}` 를 더했다. 관측 대응 = 그 업종으로 분류된 사례의 사이트 업종 필터(2건 이상 · 절반 이상):
  SV → kr_retail_fnb(4/4) · TP → kr_hotel(`호텔/서비스` 9/11) · VN → kr_hotel(8/9) · ID → kr_construction(5/7) · OE → kr_telecom(4/7) → `mapping=true, mapping_basis=observed_cases`.
  AD 는 2건이 kr_hotel · kr_transport 로 갈려 대응 없음(`mapping=false`). 6업종 사례는 모두 단서만으로 분류됐다(`case_basis.clue_only = case_count`). 관측 대응은 사례 분류 prior · `classify` 의
  `a2_match` 에 되먹이지 않는다(`호텔/서비스` 필터가 넓어 A2 호텔 판별과 뜻이 다름) — 업종별 사례 수 · 판별 점수는 그대로다.
- 상태(kb · 2026-10-07) ↑「모델 코드에 / 가 든 모델 상세 · LED 크기 · 배치 규칙 파라미터 — birdseye」 필요 1: 완료 — `/v1/models/{model_code}` · `/images` · `/cases` · `/lifecycle` 이 / 든 코드(58개)를 받는다.
  서비스 클라이언트는 `quote(code, safe="")`(→ `LH012IWCMWS%2FXU`)로 부르면 계약 검증도 통과한다(그대로 / 를 넣으면 kb 는 받지만 ServiceClient strict 검증에서 막힌다). `GET /v1/models?q=LH012IWCMWS/XU` 도 찾는다.
- 상태(kb · 2026-10-07) ↑ birdseye 필요 2: 원인은 kb 버그였다 — LED 모델코드 숫자(LH012 · LH016)는 픽셀 피치 코드(1.26 · 1.68 mm)인데 인치로 읽었다(모듈 크기 아님). 고침: LED `values.size` 는 `—`(inch null),
  `pixel_pitch` · `brightness` 열은 채움. 모델 상세에 `led {pixel_pitch_mm, unit_pixels(Pixel Configuration 원문), unit_active_mm(픽셀×피치 계산값 — IWC P1.26 = 806.4×453.6 mm), size_mentions(PDP 원문 — IAC `최대 130인치`)}`.
  화면 구성 옵션(146" · 110", 가로×세로 mm) 표는 KB 에 없다 — 데이터 공백(e-카탈로그 미수집)이라 `screen_options` 는 만들지 않았다. The Wall IWC · IWA 는 제품 치수 행도 없다(`dims_mm=null`).
- 상태(kb · 2026-10-07) ↑ birdseye 필요 3: 필드 완료 + 데이터 공백 — KB 배치 규칙 6개는 시드 초안이고 계수가 전부 `<<FILL>>` 라 승인 값이 없다. 항목에 `param_status`(unfilled · draft · approved — 지금 전부 unfilled) ·
  `param_values`(빈칸 null) · `missing_params` · `param_notes` · `explanation_ko` · `category_ids` · `source_tier` 를 더했다. `id` 는 birdseye `rule_id` 와 같다(`pr_…`). `params` 는 원문(`<<FILL>>` 문자열)이니
  덮어쓰기는 `param_status == 'approved'` 일 때 `param_values` 로만. `category=` 는 이제 KB 분류 id(cat_smart-signage · top_display · …__videowall) · 시드 하위 코드(signage_lcd)도 받는다(전에는 `signage` 만 맞아 빈 응답이 났다).
- 상태(kb · 2026-10-07) ↑ birdseye 필요 4: 완료 — 모델 상세 `dims_mm {w, h, d, unit:'mm', raw, attr, kind, order, order_basis}`(body → 스탠드 제외 순, 없으면 null) · `dims_all[]`(스탠드 포함 · 포장 · 실내기 · 액티브 디스플레이 …).
  축 순서는 속성 이름으로 정한다(가로x높이x깊이 = W×H×D, 프린터 가로x세로x높이 = W×D×H, 휴대폰 세로x가로x두께 = H×W×D). `POST /v1/spec/table` `derived[code].dims_mm` 도 같다(예전 `dimensions_mm` 은 그대로).
