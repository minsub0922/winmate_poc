# kb 서비스 — 개발 세션 규칙

지식 DB — 제품 · 솔루션 · 업종 · 공간 · 사례 · 메시지 · 이미지 질의 (winmate-kb)

- 포트: **5020** · 게이트웨이 경로: `/api/kb/v1/...` · 파이썬 모듈: `winmate_kb`
- 고칠 수 있는 경로(owns): `services/kb/**`
- 호출할 수 있는 서비스(consumes): 없음

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=kb          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=kb         # 이 서비스 테스트
make contracts SERVICE=kb    # contracts/kb.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("kb", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("kb")`(data/kb/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=kb` 를 돌리고 `contracts/kb.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태 (2026-10-07)

### 2026-10-07 반영 (docs/requests/kb.md 요청 4묶음 — 모두 더한 필드 · 계약 경로는 그대로)
- **/ 가 든 모델코드(58개 — The Wall `LH012IWCMWS/XU` · 프린터 `SL-C2410ND/KRM` …)**: `/v1/models/{model_code}` · `/images` · `/cases` · `/lifecycle` 이
  경로 변환기 `{model_code:path}` 로 받는다. 하위 자원 경로를 상세보다 먼저 등록해야 한다(path 는 끝까지 삼킴). 서비스 클라이언트는 `%2F` 로 부른다
  (계약 검증 `[^/]+` 통과). 끝 슬래시 · 퍼센트 인코딩도 `resolve_model` 이 받는다. 모델 목록 `q` · 제품 검색도 / 를 뺀 코드로 맞춘다.
- **LED 크기 버그 고침**: LED 모델코드 숫자(LH012)는 픽셀 피치 코드(1.26 mm)라 `index.inch` 가 인치로 읽지 않는다(`CODE_INCH_L2`). LED `values.size` 는 `—`,
  `pixel_pitch` · `brightness` 열은 영문 스펙 행(Pixel Pitch · Brightness)이나 모델 옵션(픽셀 피치)에서 채운다.
- **모델 상세 추가 필드**: `warranty` · `dims_mm` · `dims_all` · `led` · `release_ym`.
- **스펙 표 derived 추가**: `dims_mm` · `power{typical, max, values[]}` · `warranty`. 예전 `dimensions_mm` 은 그대로 둔다(축 순서를 안 봄).
- **생애주기 추가**: `successors[]`(relation=similar, `newer`) · `release_ym` · `warranty`. `successor` 는 여전히 null(DR10).
- **A3 보강**: 입력 순서로 짝짓기, `55형이상 · 55” · 55'' · 55 inch` 인식, 이름이 인치인데 값이 cm 면 cm 로, 이름을 몰라도 크기 낱말 · 빈 이름 + 인치 값이면 inch,
  `unit_basis`(value · name · default) · `value_cm` · `value_inch` · `mapped_by`.
- **업종**: `/v1/segments` 항목에 `mapping` · `mapping_basis` · `kr_vertical_ids_observed` · `observed_kr_verticals` · `case_basis`.
  `/v1/segments/{code}/insights` 의 `req_types[]` 에 `examples_specific` · `hint_terms`(계산값).
- **요구 태그 코드표**: `req_types[].label` · `description` · `label_source=codebook` 을 `curation/req_tags.yaml` 에서 채운다.
  원문은 `winmate-kb/raw/prior_case_studies.json` meta.taxonomy(R01~R24 · P01~P22, T5)이고 `scripts/make_req_tags.py` 가 만든다(`--check` 로 원문과 대조).
  코드표 전체는 `GET /v1/req-tags`(internal).
- **배치 규칙**: `param_status`(unfilled · draft · approved) · `param_values`(빈칸 null) · `missing_params` · `param_notes` · `explanation_ko` · `category_ids` · `source_tier`.
  `category=` 에 KB 분류 id · 시드 하위 코드도 받는다.
- **계약 설명**: `sale_status_code`(ModelDetail · FamilyItem · Lifecycle)에 관측값 표(17 · 15, 뜻 미확인)를 적었다.

### 00-shell §7.2 와 다른 점 (먼저 볼 것)
§7.2.2~§7.2.16 의 경로 · 파라미터 · 필드 이름 · 타입은 그대로다. 아래는 더하거나 다르게 정한 것이다.
계약은 `contracts/kb.json`, 웹 타입은 `web/src/api/gen/kb.ts` 에 있다.

- **더한 필드가 많다.** 스키마 description 이 `추가 —` 로 시작하는 필드다. 화면은 무시해도 된다.
- **`ImageMeta.stored` 는 null 일 수 있다.** `ImageDims.format` · `bytes` 도 모르면 null 이다.
- **`stored` 는 실제로 주는 사본의 메타다(G-IMG-2).**
  - 스크립트를 돌리기 전: 썸네일(WebP, 긴 변 160~176px).
  - 돌린 뒤: 로컬 사본(WebP, 긴 변 ≤1600px).
  - 그래서 보드 I-10 의 `저장본 1100 × 673 · JPG` 와 다르다. 근거는 `basis`(`local_file` · `thumbnail`)에 있다.
- **`original` 은 다음 순서로 근거를 찾는다(G-IMG-1).**
  1. 내려받기 사이드카(`download`)
  2. 보드 표본 21장(`board_sample`)
  3. 썸네일을 만들 때 잰 원본 크기(`browser_probe`, `bytes`=null)
- **`usage_note` 는 시트 문구다.** 팝오버 문구는 `usage_note_short`(추가), 캡션 규칙은 `caption_rule`(추가)에 있다.
- **`supported_solutions[].name` 은 PDP 원문 이름이다**(예 `VXT`). 카탈로그 이름은 `catalog_name`(추가)에 있다.
- **표시명은 코드 규칙(display.yaml)이 맞으면 규칙을 쓴다**(예 `LH55QMCEBGCXKR` → `QM55C`). 맞지 않으면 모델코드를 쓴다. 근거는 `display_name_basis`(`code_rule` · `model_code`)에 있다.
- **밝기는 `밝기 (Typ)` 원문의 첫 수(Typ)다.** KB 의 `value_num` 은 Peak 일 수 있어서 쓰지 않았다.
- **`GET /v1/models` 는 필터가 하나는 있어야 한다.** `family_id` · `category_id` · `q` 가 모두 없으면 400 `INVALID_ARGUMENT` 를 준다.
- **id 형식을 더 받는다.**
  - `/v1/models/{code}`: 모델코드 외에 `mdl_…` · `fam_…`(대표 모델)
  - `/v1/solutions/{id}`: `magicinfo` 외에 `sol_magicinfo`
- **`/v1/models/{code}/cases` 에서 `match` 를 생략할 때**
  - 모델 → 시리즈 → 용도 순으로 처음 1건 이상인 종류의 items 를 준다. 어느 종류인지는 `default_match` 에 있다.
  - 용도 이름(G-CASE-5)은 사전으로 정한다(QMC = `매장 사이니지`).
- **`/v1/cases/search`**
  - 본문이 있는 사례 198건만 찾는다. PDF · 영상 20건은 빠진다.
  - `total` 과 `applied.vertical.from`(`vertical_from=user|task`)을 더했다.
  - `infer_vertical=true` 면 A2 가 `auto` 일 때만 업종을 적용한다.
  - `target` 은 `model:…` 도 받는다.
  - `region` 에 값이 있으면 400 `UNSUPPORTED_FILTER`(`details.filters=["region"]`)를 준다(G-CASE-4).
- **`/v1/images/search`**
  - 기본으로 등급 D(도식)와 E(아이콘)를 뺀다. 넣으려면 `grades=A,A?C,C,D,E` 를 준다.
  - `q` 가 비면 둘러보기 묶음을 준다: 최신 사례 대표 사진과 제품군 갤러리 첫 장.
- **`/v1/verticals?scheme=` 는 `us_site` · `winmate16` 도 받는다.**
- **L2 분류는 id 순이다.** 사이트의 순서 데이터가 없다.
- **솔루션 `official` 이미지는 KB 의 견적 PDP 이미지다**(MagicINFO 는 1장). 소개 페이지 이미지는 없다(G-SOL-3).
- **내부 전용(`internal`) 경로는 아직 브라우저에서 막히지 않는다.**
  - 게이트웨이가 계약을 프로세스 캐시에 들고 있어서, 게이트웨이를 다시 시작해야 403 이 걸린다.
  - `docs/requests/platform.md` 에 요청해 두었다.

### 구성
- **KB 파일**
  - `winmate-kb/kb/winmate_kb.sqlite` 를 읽기 전용(`immutable=1`)으로 열고 `models/*.joblib` 을 함께 쓴다.
  - 질의 패턴은 `winmate-kb/build/query.py` 를 importlib 로 불러 그대로 쓴다(`engine.py`). winmate-kb 는 고치지 않는다.
- **스레드 안전(`ThreadKB`)**
  - sqlite 연결은 스레드마다 하나다.
  - LSA · 벡터 · 별칭 캐시는 모든 스레드가 공유하고 RLock 으로 보호한다.
  - 엔드포인트는 모두 동기 함수라 스레드 풀에서 돈다.
  - query.py 와 다른 점은 두 가지다. A2 는 `raw_score` 를 더한다(순위는 같다). E2 는 메시지 임베딩을 캐시한다.
- **시작과 상태**
  - 시작하면 백그라운드에서 데운다. 5~11초 걸리고(머신 부하에 따라), RSS 는 약 380MB 다.
  - `/healthz` 의 `checks.kb` 는 `{ok, db, warm, warm_seconds, warm_error}` 다.
- **목록**: `?limit=&cursor=` 로 받는다. 기본 20, 최대 100 이다. `cursor` 에는 이전 응답의 `next_cursor` 를 넣는다.
- **이미지 주소는 게이트웨이 경로만 준다.**
  - `thumb_url` = `/api/kb/v1/images/{id}/thumb`
  - `stored_url` = `/api/kb/v1/images/{id}/file`
  - 외부 URL 은 출처 표기용 `original_url` · `source_page.url` 에만 둔다.
- **환경 변수(모두 선택)**
  - `WKB_ROOT`: 기본 `winmate-kb`
  - `WKB_KB`: 기본 `<WKB_ROOT>/kb`
  - `WKB_THUMBS_DIR`: `thumbs_pack*.bin` 폴더. 기본 `<WKB_ROOT>/dashboard/build`
  - `WKB_IMAGE_DIR`: 로컬 사본 폴더. 기본 `<DATA_DIR>/kb/images`
  - `KB_WARMUP`: `0` 이면 미리 데우지 않는다.
- **코드**
  - `api.py`: REST
  - `patterns.py`: 질의 패턴
  - `engine.py`: query.py 를 불러 스레드 안전하게 감싼다.
  - `index.py`: 메모리 색인 · 표시명 · 인치 규칙
  - `catalog.py` · `cases.py` · `solutions.py` · `segments.py` · `specs.py`: 영역별 응답
    - `specs.py`: 스펙 표 · 생애주기(같은 계열 다른 세대) · 보증 · 소비전력 모드 · LED 정보 · 배치 규칙(시드 categories.yaml 로 분류 id 잇기)
    - `segments.py`: 16업종 · 관측 대응 · 요구 태그 lift(`examples_specific` · `hint_terms`)
  - `dims.py`: 치수 정규화(속성 이름의 축 순서 · 단위 → mm, 종류 body · without_stand · package …)
  - `images.py`: 썸네일 묶음 · 로컬 사본
  - `imagecards.py` · `schemas.py`: 이미지 카드 · 응답 스키마

### 엔드포인트 (게이트웨이 접두 `/api/kb`, operationId = 함수 이름)
셸용(§7.2, 브라우저에서 부른다)
- `GET /v1/info` — 서비스 정보.
- `GET /v1/meta` — §7.2.2 kb_version · 수집 시각 · `counts`.
  - 값: families 605 · models 1067 · image_assets 10251 · case_pages 198 · thumbnails 10219 · local_images.
- `GET /v1/categories?parent_id=` — §7.2.3 하위 분류와 제품군 수. `parent_id` 가 없으면 L1 9개.
- `GET /v1/families?category_id=` — §7.2.4 제품군 목록. 시리즈 라벨 · 모델 수 · 대표 이미지를 준다.
- `GET /v1/models?family_id=|category_id=&q=` — §7.2.4 모델 행. §9.4 열 프로필의 값과 하이라이트를 준다.
- `GET /v1/products/search?q=&limit=5&kinds=model,family` — §7.2.5 제품 검색. 코드 · 표시명 · 별칭으로 찾고, 없으면 LSA 로 찾는다.
- `GET /v1/models/{model_code}` — §7.2.6 제품 시트.
  - 표시명 · 분류 경로 · 핵심 칩 · 사실 줄 · 스펙 블록(부록 B) · 지원 솔루션을 준다.
  - 공식 자료는 데이터가 없어 `documents=null` 이다.
  - 추가: `warranty`(스펙 보증 행 원문) · `dims_mm` · `dims_all`(치수 정규화) · `led`(LED 만) · `release_ym`. 코드에 / 가 있어도 된다(%2F 권장).
- `GET /v1/models/{model_code}/images` — §7.2.7 PDP 갤러리 중 confirmed 이미지를 원래 순서로 준다.
- `GET /v1/models/{model_code}/cases?match=model|series|usage` — §7.2.8 이 모델이 쓰인 사례와 종류별 건수 3개.
- `GET /v1/solutions?q=&industry=` — §7.2.9 솔루션 목록(카탈로그 11 + KB 전용 5)과 업종 칩.
- `GET /v1/solutions/{id}` — §7.2.10 솔루션 시트. 지원 기기 · 프로필(MagicINFO 만) · `gaps` 를 준다.
- `GET /v1/solutions/{id}/images` — §7.2.11 공식 이미지와 사례 사진(사례마다 1장, 최대 4장).
- `GET /v1/solutions/{id}/cases` — §7.2.12 이 솔루션을 쓴 사례(최신순).
- `GET /v1/images/search?q=&source=&verified_only=&grades=&limit=24&cursor=` — §7.2.13 이미지 검색. ImageCard 목록을 준다.
- `GET /v1/images/{id}` — §7.2.14 ImageMeta. 출처 · 원본 · 저장본 · 게시일 · 사용 범위 · 묘사 대상을 준다.
- `GET /v1/images/{id}/thumb` — WTHB 묶음의 썸네일(WebP). 없으면 404.
- `GET /v1/images/{id}/file` — 이미지 파일.
  - `WKB_IMAGE_DIR` 의 로컬 사본을 주고, 없으면 썸네일을 준다. 둘 다 없으면 404.
  - 응답 헤더 `X-KB-Image-Source: local|thumbnail` 로 무엇을 줬는지 알린다.
- `GET /v1/cases/search?q=&vertical_id=&target=&period=&limit=10&cursor=` — §7.2.15 사례 검색. D1 점수 · 일치어(최대 2) · 태그 세부를 준다.
- `GET /v1/cases/{id}` — §7.2.16 사례 시트. 인용 · 제품 · 사진 · 원문 링크를 준다.
- `GET /v1/cases/{id}/similar?limit=5` — (추가) D1 로 찾은 비슷한 사례.
- `GET /v1/verticals?scheme=kr_site|us_site|winmate16` — §7.2.16 업종 목록과 업종별 사례 수.
- `GET /v1/space-types?vertical_id=` — (추가) 공간 유형. `vertical_id` 를 주면 그 업종 페이지에 나온 것만 준다.

서비스끼리만 부른다(`tags=["internal"]`)
- `GET /v1/models/{model_code}/lifecycle` — 06-spec 판매 상태.
  - `status` 는 `on_sale` 또는 `not_in_catalog`. `sale_status_code` 도 준다(뜻 미확인 — 계약 설명에 관측값 표).
  - `successor` 는 항상 null 이다(KB 에 후속 모델 데이터가 없다, DR10).
  - `successors[]`: 사이니지 표시명 규칙(display.yaml signage_lh)으로 같은 계열 · 같은 크기(LED 는 피치 코드)의 다른 세대 KB 모델.
    relation 은 `similar` 만, `newer` 는 스펙 '동일모델의 출시년월'(세대마다 가장 이른 값)로 본다. 더 오래된 후보는 뺀다. KB 에 없는 입력(QM55R)도 찾는다.
  - `release_ym` · `warranty` 도 준다.
- `GET /v1/segments` — 03-mi · 04-competitor Winmate 16업종과 업종별 사례 수. 규칙 초안(`rule_segment_v1`)으로 나눈다.
  - `mapping_basis=observed_cases`: 시드 대응이 빈 업종(SV · TP · VN · ID · OE)은 분류된 사례의 사이트 업종 필터(2건 이상 · 절반 이상)를 관측 대응으로 준다.
    AD 는 2건이 갈려 대응 없음. 관측 대응은 사례 분류 prior · classify 에 되먹이지 않는다(분류 · 사례 수 그대로).
- `GET /v1/segments/{code}/insights?top_req=6&top_items=4` — 03-mi 업종 인사이트. 요구 유형 상위(R코드 · 코드표 `label` · `description`) · 제품 · 솔루션.
  - `examples_specific`: 요구 문장 낱말의 태그 lift 합 순 상위 3(같은 응답의 앞 태그가 쓴 문장은 뺌). `hint_terms`: 태그 lift 낱말(3건 이상) 최대 5.
- `GET /v1/req-tags` — 요구 태그 R01~R24(`label` · `description`) · 제안 콘텐츠 P01~P22 코드표(T5, `curation/req_tags.yaml`).
- `POST /v1/segments/classify {text}` — 03-mi §7.3 업종 판별 근거. 16업종마다 `kb_score` · `clue_score` · `clues` · `similar_case_ids` 를 준다.
- `GET /v1/entities/{kind}/{id}` — 엔티티 통합 보기. 봉투로 주고, 없으면 404.
- `GET /v1/spec/attributes?category_id=&q=` — 06-spec 스펙 속성 사전. 그룹 · 이름 · 정규 키 · 단위를 준다.
- `POST /v1/spec/table {models, keys?, groups?}` — 06-spec 여러 모델의 스펙을 나란히 놓은 표.
  - 파생값도 준다: 인치 · 치수(mm) · 밝기(Typ) · 무게 · 해상도.
  - 추가: `dims_mm`(정규화) · `power{typical, max, values}`(소비전력 모드, LED Max 는 W/㎡ · `per_m2`) · `warranty`.
- `GET /v1/placement-rules?category=&space=` — 08-birdseye 배치 규칙. 모두 초안이라 `active=false` · `param_status=unfilled` 다.
  - `category` 는 시드 코드(signage) · KB 분류 id(cat_smart-signage · top_display · L3) · 시드 하위 코드(signage_lcd)를 받는다.
  - `param_values`(빈칸 null) · `missing_params` · `param_notes` · `explanation_ko`(시드 YAML) · `category_ids`. id 는 birdseye `rule_id` 와 같다.
- `GET /v1/patterns` — 질의 패턴 26개의 이름 · 설명 · 요청 JSON 스키마와 봉투 필드.
- `POST /v1/query/{code}` — 패턴마다 경로 하나다(아래 표 28줄).
  - operationId 는 `query_{code}` 이고, 요청 모델은 패턴마다 다르다.
  - 응답은 query.py 와 같은 공통 봉투다: `{pattern, result, evidence_paths, tier_min, candidates, decision_hint, decision_reasons, needs_confirmation, fallback_level, modes_used, timings_ms, kb_version}`.
  - 이미지 행에는 `thumb_url` · `stored_url` · `has_local` 을 더한다.

| 경로 `POST /v1/query/…` | 하는 일 |
|---|---|
| `S1` | 요구 문장 → 공간별 후보 제품군 · 솔루션 · 유사 사례(A1 · A2 → C1 → C2 → D1) |
| `S2` | 업종 · 공간 → 장면 구성(B1 → E1 → G1 → D1) |
| `A1` | 엔티티 링킹(모델 · 제품 · 분류 · 솔루션 · 업종 · 공간 · 역량) |
| `A2` | KR 업종 판별 top-2(+`raw_score`) |
| `A3` | 요구 스펙 원문 → 정규 키 · 수치 · 단위(+화면 크기 인치 · cm 보정, `unit_basis`) |
| `B1` | 업종 프리셋(장면 순서 · 추천 항목 · 히어로 문구 · 솔루션 · 사례) |
| `B2` | 결핍 역량 → 확인 질문 |
| `C1` | 공간 · 문장 → hard · soft 역량 |
| `C2` | 역량 · 공간 · 업종 → 후보 제품군 |
| `C3` | 제품군 → 적합 업종 · 공간 · 사례 |
| `C4` | 제외 사유 |
| `C6` | 요구 스펙 충족 판정 pass · fail · unknown(+`attr_name`) |
| `D1` | 유사 사례(분해 점수) |
| `D2` | 업종 · 공간 사례 통계 |
| `D3` | 사례 KPI 문장(claim_flag) |
| `D5` | 함께 쓰인 제품 · 솔루션(lift) |
| `E1` | 메시지 계층(tagline → key message → proof point) |
| `E2` | 테마 문장 → 비슷한 원문 메시지 |
| `E3` | 컨텍스트 → 헤드라인 · 메시지 묶음 · 근거 사례 |
| `G1` | 공간 × 분류 배치 이미지(폴백 단계) |
| `G2` | 제품 · 분류가 나오는 이미지 |
| `G4` | 제품 단독컷(PDP 갤러리) |
| `G5` | 사례 사진 |
| `search` | 하이브리드 검색(BM25 + 부분 일치 + LSA → RRF) |
| `image_search` | 이미지 검색 |
| `images` | `image_search` 별칭 |
| `get_entity` | 엔티티 통합 보기(못 찾으면 `result=null`) |
| `entity` | `get_entity` 별칭 |

### 큐레이션 데이터 (`src/winmate_kb/curation/*.yaml`, 모두 [제안] — 사람이 검수해야 한다)
- `display.yaml`
  - 표시: L1 순서 · 표시명 규칙(G-PRD-1) · 영문 계열 이름 · 해상도 라벨(§9.3)
  - 솔루션 · 페이지: 솔루션 종류 라벨 · 페이지 유형
  - 이미지: 출처 우선순위 · 사용 범위 문구 · 캡션 규칙
  - 사례: 공간 짧은 말(G-CASE-2) · 용도 이름(G-CASE-5)
- `columns.yaml` — 분류별 목록 열 프로필(§9.4, G-PRD-4).
- `spec_profiles.yaml` — 사이니지 핵심 스펙 프로필(부록 B, G-PRD-2) · 핵심 칩 · 사실 줄.
- `solutions.yaml`
  - 솔루션 카탈로그 11개(G-SOL-1): 아이콘 · 설명 · 템플릿 코드 · `kb_ids` · 제목 별칭 · 분류 경로 · 부제
  - 업종 칩
  - 10-proposal 부록 B 템플릿
  - MagicINFO 프로필(G-SOL-2)
- `segments.yaml` — Winmate 16업종 초안.
  - 업종마다 코드 · 이름 · 별칭 · 단서 사전 · KR 업종 대응.
  - 분류 규칙: 사전 가중 0.3, 최소 점수 0.4.
- `image_samples.yaml` — 보드 표본 이미지 21장의 원본 크기 · 형식. G-IMG-1 의 근거로 쓴다.
- `req_tags.yaml` — 요구 태그 R01~R24 · 제안 콘텐츠 P01~P22 코드표. `scripts/make_req_tags.py` 가 raw 원문에서 만든다(손으로 고치지 않는다).

### 알려진 공백 (요청한 문서)
00-shell
- **G-PRD-1**: 표시명 규칙은 사이니지 모델코드에만 맞는다. 영문 계열 이름도 Smart Signage 만 있다. 나머지는 모델코드로 표시한다.
- **G-PRD-3**: 공식 자료(매뉴얼 · QSG · 펌웨어) 데이터가 없다. `documents=null` 이다.
- **G-SOL-1**: Knox Capture · DeX · 콜드체인 · 통합공조는 KB 에 없다. `kb_ids=[]` 라 이미지 · 사례가 빈 목록이고, `gaps` 에 표시한다.
- **G-SOL-2**: 솔루션 프로필은 MagicINFO 만 있다. 나머지는 `profile=null` 이다.
- **G-SOL-3**: 솔루션 소개 페이지와 공식 소개 이미지를 수집하지 않았다.
- **G-IMG-1 · G-IMG-2**: 원본 메타와 저장본은 `kb_fetch_images.py` 를 돌려야 채워진다. 그전에는 표본 · 썸네일을 근거로 쓴다.
- **G-IMG-3**: 짧은 제목은 alt · 캡션 규칙으로 만든다. 쓸모없는 alt 는 `{사례} 도입사례 사진` 으로 바꾼다. LLM 요약은 없다.
- **G-IMG-4**: `focal=null` 이다. 화면은 가운데를 쓴다.
- **G-IMG-5**: `사내 자산` 출처가 없다. `source` 는 `all` · `official` · `case` 만 받는다.
- **G-CASE-1**: 사례 요약이 없다. `summary=null` 이고 `quote` 만 준다.
- **G-CASE-4**: 지역 필터를 주면 400 이다.
- **G-DATE-1**: 사례 날짜는 KB 값 그대로다. 3건이 보드보다 하루 이르다.
- **G-WS-1**: 사용 이력은 workspace 서비스가 맡는다.

다른 기능 문서
- **06-spec**
  - 공식 후속 모델 데이터가 없다(DR10). `successor=null` 이다. `successors` 는 같은 계열 다른 세대(similar)일 뿐이다.
  - 보증 연수: 사이니지 · TV · 모니터는 스펙에 `소비자분쟁해결기준에 따라 보상` 문구뿐이다 → `warranty.status=statement_only`, `years=null`.
    연수가 있는 것은 프린터(1년) · LED 조명(2년, 부품보유 3년) · 에어컨 청소(3개월)뿐이다.
  - `sale_status_code`(15 · 17)의 뜻을 모른다(코드표 없음). 둘 다 목록 노출 상품이다.
  - `소비전력 (Typical)` 은 LCD 사이니지 14개 모델(BEH · BEF · BED · WMF)에만 있다. `(Max)` 는 LCD 사이니지에 없고 LED 는 ㎡당 값(9개)이다.
    QMC 등은 On Mode · Sleep 뿐이라 `power.typical=null` 이다.
- **03-mi · 04-competitor**
  - 요구 태그 이름표는 이전 세션 사례 구조화 때 쓴 코드표(T5, 사람 검토 전)다. KB DB 에는 코드만 있다.
  - 사례 → 업종 분류는 규칙 초안(T5)이다.
  - 16업종 중 6개(SV · TP · VN · AD · ID · OE)는 시드 KR 업종 대응이 없다. 5개는 관측 대응(`observed_cases`)을 주고, AD 는 그것도 없다.
- **08-birdseye**
  - 배치 · 수량 규칙이 모두 초안이다(계수 빈칸). 그래서 `active=false` · `param_status=unfilled` 다.
  - LED 화면 구성 옵션(대각 · 가로×세로) 표가 없다(e-카탈로그 미수집). The Wall IWC · IWA 는 제품 치수 행도 없다(`dims_mm=null`).
  - 게이트웨이의 internal 차단은 계약 경로 매칭이라, 브라우저가 / 를 그대로 넣은 `/lifecycle` 은 막히지 않을 수 있다(데이터는 판매 상태뿐).
- **10-proposal**
  - K4 `POST /v1/images:match`(기존 제안서 이미지 재식별)를 만들지 않았다. 지각 해시 색인이 없다.
  - K5 의 C5 · E4 · F1 · F3 패턴은 query.py 에 없다.
  - K3: KB 의 `catalog_chapter` 는 모두 `<<FILL>>` 이다. 대신 `segments.yaml` 로 16업종 코드(`FB` …)와 `wm_…` id 를 이었다(`/v1/verticals?scheme=winmate16` 의 `code`, 초안).

공통
- PDF · 영상 사례 20건은 본문이 없다. 그래서 사례 검색과 업종 집계에서 빠진다.

### 확인 방법
```bash
UV_SYSTEM_CERTS=1 uv run pytest services/kb -q        # = make test SERVICE=kb, 90개, 실제 KB 파일로
UV_SYSTEM_CERTS=1 uv run python scripts/contracts.py export kb && (cd web && node scripts/gen-api.mjs kb)
WINMATE_ONLY=kb ops/node_modules/.bin/pm2 start ops/pm2/ecosystem.config.cjs   # 처음(또는 make up)
ops/node_modules/.bin/pm2 restart kb                                           # 코드를 바꾼 뒤
curl -s localhost:5000/api/_health                                              # kb: ok · warm=true
curl -s localhost:5000/api/kb/v1/models/LH55QMCEBGCXKR                          # QM55C · 138.7 cm · 500 nit · 3,840 x 2,160
curl -s -o /dev/null -w '%{content_type}\n' localhost:5000/api/kb/v1/images/img_9ec6148d2e4d9c18/thumb   # image/webp
```
테스트 파일
- `test_shell_api.py`
  - §2 KB 확인값: `fam_G000182628` 7행, QM55C 수치, MagicINFO 사례 17 · 3, meta 605 · 1067 · 10251 · 198.
  - §8.14 수용 기준 A-KB-01~17 과 PD · SD · C · I 수치.
- `test_patterns.py`
  - 패턴 26개와 별칭 2개의 봉투.
  - query.py 와 같은 결과(D1 · B1 · C2 · E2 · A1 · A2).
  - A3 인치 보정 · C6 `attr_name` · 이미지 행 주소 · 엔티티 404.
- `test_images_and_features.py`
  - 이미지: WebP 썸네일 · 404 · 로컬 사본과 사이드카.
  - 추가 엔드포인트: 업종 · 스펙 표 · 생애주기 · 배치 규칙.
  - 성능 · 동시성: 데운 뒤 검색 1초 미만, 동시 요청.
- `test_requests_1007.py`(2026-10-07 요청 14개)
  - / 든 모델코드(상세 · 하위 자원 · %2F · 검색), LED 크기 · 피치 · `led`, 치수 정규화(파서 단위 시험 포함).
  - 보증 · 생애주기 successors · sale_status_code 설명 · A3 단위 · 소비전력 모드 · 배치 규칙 파라미터 · 업종 관측 대응 · 요구 태그 lift.
- `test_req_tags.py` — 코드표 엔드포인트 · 인사이트 이름표 · yaml 이 raw 원문과 같은지.
- `test_basics.py`

200 응답은 모두 계약 스키마로 검증한다(`conftest.ok`).

### 이미지 로컬 사본 만들기 (`scripts/kb_fetch_images.py`, 인터넷이 되는 맥에서)
사내망 PC 는 samsung.com 에 붙지 못한다. 맥에서 한 번 받아 폴더째 옮긴다. 스크립트는 표준 라이브러리와 Pillow 만 쓴다.
```bash
uv run python services/kb/scripts/kb_fetch_images.py --dry-run         # 받을 목록만 본다
uv run python services/kb/scripts/kb_fetch_images.py --limit 50        # 시험
uv run python services/kb/scripts/kb_fetch_images.py --only-priority   # 대시보드 우선 목록(thumb_select.json)만
uv run python services/kb/scripts/kb_fetch_images.py                   # 전부: 우선 목록 → 등급 A → A?C → C → D → E
uv run python services/kb/scripts/kb_fetch_images.py --report          # 지금 상태 요약
```
- **출력 폴더**: `$WKB_IMAGE_DIR`, 기본 `data/kb/images`.
  - `<asset_id>.webp`: 긴 변 ≤1600px, 품질 82.
  - `_originals.json`: 원본 가로 · 세로 · 형식 · 용량. kb 가 `ImageMeta.original` 로 쓴다.
  - `_failures.json` · `_report.json`.
- **속도와 이어 받기**
  - 초당 2건(`--rps`)으로 받는다. 429 · 5xx 는 3번까지 다시 시도한다.
  - 이미 받은 파일은 건너뛰므로, 끊기면 다시 돌리면 이어 받는다.
  - 영상 · 벡터 12건은 받지 않는다.
- **다른 옵션**: `--ids` · `--max-side` · `--quality` · `--timeout` · `--skip-failed` · `--out` · `--db`.
- **옮긴 뒤**: kb 를 다시 시작할 필요는 없다. 요청마다 파일과 사이드카의 수정 시각을 본다. `WKB_IMAGE_DIR` 값을 바꿨을 때만 `pm2 restart kb --update-env` 를 한다.
