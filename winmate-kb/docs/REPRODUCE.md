# winmate-kb 재현 가이드

이 문서는 코드 에이전트용이다. 다음 세 가지를 이 문서만 보고 할 수 있게 쓴다.

1. `kb/winmate_kb.sqlite` 를 **같은 바이트로** 다시 만든다.
2. 각 단계가 어느 경로에서 무엇을 읽어 어떻게 정제하고 어느 표에 쓰는지 안다.
3. 스키마와 ID 규칙을 알고 고친다.

표 · 컬럼 하나하나의 뜻은 [DATA_DICTIONARY.md](DATA_DICTIONARY.md)에 있다. 원본 스키마는 [`build/schema.sql`](../build/schema.sql)이다. 이 문서는 그 위의 **파이프라인**을 설명한다.

---

## 0. 요약

```
samsung.com/business ──(브라우저 콘솔 collect/*.js)──▶ raw/*.json (6개, 26 MB, git 에 있음)
raw/ + seed/*.yaml + build/curation.py
   └─ build/build_kb.py ─▶ kb/winmate_kb.sqlite (사실 · 출처 · 온톨로지 · 그래프 · 청크)
   └─ build/index_kb.py ─▶ 같은 DB 의 검색 표(entity/image FTS, vec_index) + kb/models/lsa_char24_v2.joblib
   └─ build/qa.py       ─▶ 같은 DB 의 dr_metric · scenario_status · kb_meta(qa.*) + docs/BUILD_REPORT.md
   └─ tests/*.py        ─▶ docs/SCENARIO_TEST_REPORT.md · docs/QUERY_COOKBOOK.md (DB 는 바꾸지 않음)
```

- **재현의 출발점은 `raw/` 다.** 사이트는 계속 바뀐다. 그래서 수집을 다시 하면 같은 raw 가 나오지 않는다. 같은 DB 를 원하면 git 의 `raw/` 로 빌드한다.
- **빌드는 결정적이다.** LLM · 네트워크 · 난수를 쓰지 않는다. ID 는 내용 해시(SHA-1 16자)이고, SVD 는 `random_state=0` 이다.
- **2026-10-07 에 직접 확인한 결과**

  | 빌드 환경 | 결과 |
  |---|---|
  | Python 3.13.16 · scikit-learn 1.9.1 · numpy 2.5.3 · PyYAML 6.0.3 · joblib 1.6.0 · SQLite 3.45.1 | `run_all.sh` 의 build → index → qa 결과가 원본 DB 와 **SHA-256 까지 같다** |
  | 같은 환경, `PYTHONHASHSEED` 를 바꿈 | 모든 표의 내용과 행 순서가 같다 |
  | 저장소 `.venv`(Python 3.12.13 · SQLite 3.53.1) | 모든 표의 내용과 행 순서가 같다 |

  build + index 는 약 70초 걸린다.

| 산출물 | SHA-256 | 크기 |
|---|---|---|
| `kb/winmate_kb.sqlite` | `9ff585782fc80f042d60fbd049410134d1b0aa2c5a16b2e1f626f234ee6c5216` | 190,980,096 B |
| `kb/models/lsa_char24_v2.joblib` | `b17266cc8c7defd7fb16efe4ad00d607efaac6a71acb5bf594497ca23d4d9ba8` | 27,730,547 B |

---

## 1. 다시 만들기

```bash
# Winmate 저장소 루트에서. 의존성(pyyaml · numpy · scikit-learn · joblib)은 저장소 .venv 에 이미 있다
source .venv/bin/activate              # 또는: cd winmate-kb && pip install -r requirements.txt
cd winmate-kb

sha256sum raw/*.json                   # §2.1 표와 같은지 먼저 본다
bash build/run_all.sh                  # build → index → qa → 시나리오 테스트(41) → 질의 예시 문서

sha256sum kb/winmate_kb.sqlite kb/models/lsa_char24_v2.joblib    # §0 표와 비교
python build/compare_db.py <기준 DB> kb/winmate_kb.sqlite          # 해시가 다르면 어느 표가 다른지 본다(표마다 내용 · 순서)

python dashboard/thumb_select.py       # kb 서비스 · kb_fetch_images.py 가 쓰는 dashboard/thumb_select.json(DB 에서 다시 뽑는다)
```

- **경로를 바꿀 때 쓰는 환경 변수**
  - `WKB_RAW=<raw 폴더>`: build_kb 가 읽는 raw 폴더
  - `WKB_KB=<kb 폴더>`: build_kb · index_kb · qa · query 가 쓰고 읽는 DB · 모델 폴더
  - 운영 DB 를 건드리지 않고 시험 빌드하려면 `WKB_KB=/tmp/kbtest bash build/run_all.sh` 처럼 한다.
- **운영 중인 kb 서비스와 함께 쓸 때**
  - `build_kb.py` 는 시작할 때 기존 DB 파일을 지우고 새로 만든다.
  - 그래서 Winmate kb 서비스가 떠 있으면 빌드가 끝난 뒤 `pm2 restart kb` 를 한다. 옛 파일 핸들을 계속 들고 있기 때문이다.
- **해시가 다를 때**
  - `compare_db.py` 로 `DIFF` 표를 찾는다.
  - qa.py 를 아직 안 돌렸다면 `--skip-qa` 를 붙인다.
  - `ORDER` 는 내용은 같고 행 순서만 다르다는 뜻이다. 질의 결과에는 영향이 없다.
- **보고서 문서는 매번 조금 다를 수 있다.**
  - `docs/SCENARIO_TEST_REPORT.md` · `QUERY_COOKBOOK.md` 의 출력 예시 문장은 바뀔 수 있다. `build/query.py` 가 동점 후보를 set 순서로 내기 때문이고, 이 순서는 `PYTHONHASHSEED` 에 따라 달라진다.
  - DB 는 그렇지 않다. 판정(41/41 통과)도 같다.

---

## 2. 입력

### 2.1 `raw/` — 수집 원본(git 에 있음)

수집 시각은 2026-10-04 15:51–17:20 KST 다(`wkb_products.json` 의 `fetchedAt` 2026-10-04T06:51:11Z). 사례 구조화는 2026-10-01 이다.

| 파일 | SHA-256 | 크기 | 만든 것 | 구조 | 쓰는 단계 |
|---|---|---|---|---|---|
| `wkb_products.json` | `c9bda4e5…6a5`(아래 전체) | 1.4 MB | collect 01 · 02 · 05 | 아래 표 참고 | 1 상품 |
| `wkb_filter_meta.json` | `817c158c…2fbc` | 0.1 MB | collect 06 | `{meta:{dispClsfNo:{filter:{group,label,min,max}}}, tabs:{dispClsfNo:[[path,query,label]]}, members:{dispClsfNo:[goodsId]}}` | 1 상품(필터 라벨 · 복수 소속 · 대표 목록) |
| `wkb_specs.json` | `5fb1a63f…a6e5` | 2.9 MB | collect 02 · 05 | `{goodsId: [[그룹, 항목, 값], …]}` 응답 1,123개 | 1 상품(스펙) |
| `wkb_features.json` | `393868d3…1f` | 18.5 MB | collect 07(`parser:'pdp_v2'`) | 아래 표 참고 | 1 상품(PDP 특장점 · 이미지) |
| `wkb_pages_v2.json` | `8f813b41…3416` | 3.0 MB | collect 03 · 04 | 아래 표 참고 | 3 페이지 · 4 업종 · 5 사례 |
| `prior_case_studies.json` | `778e77a2…986` | 0.3 MB | 이전 세션의 LLM 구조화(방법 기록 없음, T5) | 아래 표 참고 | 0 시드(사례 id) · 5 사례 |

`wkb_products.json` 의 구조

| 키 | 내용 |
|---|---|
| `cats` | 목록 50개. 원소는 `{p:'dvms/all-dvms', no:dispClsfNo, title, count, filters, allFilters, listCount}` |
| `products` | 상품 카드 605개. 형태는 `{goodsId: {catPath, catNo, catTitle, goodsId, goodsNm, mdlCode, mdlNm, grpPath, goodsDetailUrl, dispClsfNo, dlgtDispClsfEnNm, compDispClsfEnNm, compDispClsfNo, uspDescList, goodsOptStr, saleStatCd, sysRegDtm, goodsTpCd, …, images:[{src, alt}]}}` |
| `cardOrder` | 사이트 목록 순서 |
| `variants` | 옵션 모델 955개. 형태는 `{goodsId: {goodsId, mdlCode, parentGoodsId, optName, optValue, optValue2, soldOut}}`. `goodsOptStr` 를 `|` 로 쪼갠 것이다 |
| `filters` | 형태는 `{dispClsfNo: {filter: [goodsId]}}`. 필터값마다 목록 API 를 다시 불러 얻은 소속이다 |
| `fetchedAt`, `finishedAt` | 수집 시작 · 끝 시각 |

`wkb_features.json` 의 구조

```
{goodsId: {title, desc, ogImage, ctg1, ctg2, parser:'pdp_v2',
           feats: [{type, h, h_all, sub, desc, disc, text, imgs, videos, items}]}}
```

- `imgs` 는 `[{src, mo_src, alt}]` 다. PC/MO 를 한 항목으로 묶었다.
- `items` 는 캐러셀 하위 항목이다. 원소 모양은 `{h, desc, imgs}` 다.

`wkb_pages_v2.json` 의 구조

```
{items: {경로: {kind, url, status, title, desc, ogImage, ogTitle, pubDate, fetchedAt, rootId, blocks}}, fetchedAt}
```

- 페이지는 261개다(`kind` 별 수: `case_kr` 198 · `us_page` 20 · `industry_kr` 17 · `solution_service_kr` 17 · `landing_kr` 9).
- `blocks` 는 본문을 순서대로 편 블록 목록이다. 블록 모양은 네 가지다.

  | 모양 | 뜻 |
  |---|---|
  | `{t:'h', l, x}` | 제목(레벨 · 글) |
  | `{t:'p', x}` | 문단 |
  | `{t:'a', href, x}` | 링크 |
  | `{t:'img', src, alt}` | 이미지 |

- 빌드는 `raw/wkb_pages*.json` 을 이름 순서로 읽는다. 나중 파일이 같은 경로를 덮는다. v1 파일은 저장소에 없다.

`prior_case_studies.json` 의 구조

- 형태는 `{meta: {source, collected, count:218, with_text:198, note, taxonomy:{req_tags:[24], proposal_content}}, cases: [...]}` 다.
- `cases` 원소의 키: `id, title, date, url, format, industry, product, solution, customer_type, scale, space, needs, req_tags, new_req, offer, proof, constraints, decision_factors, proposal_content, quote`.

**참고 — 요구 태그 코드표.** 요구 태그 R01–R24 의 이름과 제안 콘텐츠 코드 P01–P22 의 이름은 `meta.taxonomy` 에 들어 있다. 하지만 빌드는 이 코드표를 DB 에 싣지 않는다. DB 의 `deployment_need(kind='req_tags')` 에는 코드만 들어간다.
Winmate kb 서비스는 이 코드표를 `services/kb/src/winmate_kb/curation/req_tags.yaml` 로 옮겨(`services/kb/scripts/make_req_tags.py`) 이름표로 쓴다. raw 를 새로 수집해 코드표가 바뀌면 그 스크립트를 다시 돌린다.

원본 SHA-256 전체

```
c9bda4e57379a6c57e9d237f83d8c5a8981a363b3ab45539756e6ecd283a4c8f  wkb_products.json
5fb1a63faa21b55144d1475f5fb6639650fb5946a96ecdff55829ea2fcf6e6a5  wkb_specs.json
393868d32a5aa08acbc26b8948923552f2ec767efcb2f4ed72d892c7a0835a1f  wkb_features.json
817c158cbf58f8cd82bae14249179769d12271a832a722b7b0f8f1f8251e2fbc  wkb_filter_meta.json
8f813b413ef0409c1b84f7ab122568aa6fc1f2e30422f8631dbabafb8ed03416  wkb_pages_v2.json
778e77a23f4d56ae657690629995efba51496a905803346ae7438c968cf20986  prior_case_studies.json
```

### 2.2 `seed/` — 사람이 정한 온톨로지(YAML, 초안)

| 파일 | 내용(개수) | 빌드가 쓰는 표 | 그 밖에 읽는 곳 |
|---|---|---|---|
| `ontology/verticals.yaml` | KR 업종 10(하위 포함), US 13, Winmate 16 세그먼트(`<<FILL>>` 빈칸 포함) | `vertical` · `segment_mapping` · 업종 별칭 | — |
| `ontology/space_types.yaml` | 공간 유형 54, 속성 정의 11 | `space_type` | `curation.py` |
| `ontology/solutions_services.yaml` | 솔루션 14, 서비스 5 | `solution` · `service_product` · 별칭 · `SOLD_AS` | — |
| `ontology/capability_rules.yaml` | 역량 15, 임계값 규칙 8(params 빈칸이라 실행 안 함), 공간 → 역량 14 | `capability` · `capability_rule` · `requires` | — |
| `ontology/placement_rules.yaml` | 배치 · 수량 규칙 6(계수 `<<FILL>>`) | `placement_rule` | kb 서비스 `specs.py` |
| `ontology/categories.yaml` | 카테고리 시드 7, US 대응 6 | (빌드는 안 씀) | kb 서비스 `api.py` · `specs.py` |
| `ontology/visual_vocab.yaml` | 이미지 시각 어휘 37, 설치 방식 11 | (안 씀, 참고용) | — |
| `sheet_roles.yaml` | 시트 역할 26, 제안 유형 3, 템플릿 23 | `sheet_role` | export 서비스 템플릿 |

### 2.3 `build/curation.py` — 원문을 "어떻게 읽을지" 정하는 사전과 규칙

사실은 넣지 않고 대응만 넣는다. 고치는 순서와 확인 방법은 [CURATION_GUIDE.md](CURATION_GUIDE.md)에 있다. 주요 이름은 다음과 같다.

| 이름 | 쓰임 |
|---|---|
| `LABEL_KO` · `MULTI_LABEL_KO` · `KW_KO` · `KW_EN` · `SPACE_SUFFIX` | 공간 라벨 → 공간 유형. 정확 일치 → 부분 일치 순서로 본다. 업종마다 주방 · 주거를 구분한다 |
| `EXTRA_SPACE_TYPES` | 관측에서 더한 공간 유형 16 |
| `CATEGORY_TOP` · `_TOP_OF` · `SUBCAT_LABEL` · `FILTER_GROUP_KIND` · `classify_filter` | 카테고리 3단계, 필터 종류 |
| `page_type_of` | `kind` 와 경로로 페이지 유형을 정한다 |
| `img_base` · `img_key` · `is_mobile_img` | 이미지 URL 정규화. PC/MO 를 한 자산으로 묶는다 |
| `grade_hint_for` · `GRADE_PRIORITY` · `CAPTION_STOP` | 이미지 1차 등급(A · A?C · C · D · E), 사례 사진 캡션 |
| `parse_industry_blocks` 와 그 하위(`_hero` · `_items_kr` · `_parse_us`) | 업종 페이지 → 섹션(hero · scene · recommend · cases)과 항목 |
| `CURATED_ALIASES` · `LEGACY_PATH_MAP` · `US_PATH_MAP` · `KR_CASE_INDUSTRY` · `US_VERTICAL_SLUGS` | 통칭 · 옛 경로 · US 경로 · 사례 업종 필터 → 대상 id |
| `AUTO_RULES` | 자동 역량 규칙 13개(presence 규칙). 필터 · 스펙 · 문구에 무엇이 "있다"만 본다 |
| `REQ_CAP_KEYWORDS` | 요구 문장 → 역량(`query.py` 가 씀) |
| `KIND_PRIORITY` · `LEVEL_OF` · `NAV_KO` · `SKIP_LINK` | 해소 우선순위, 탐색 문구 걸러내기 |

---

## 3. 빌드 단계 — `build/build_kb.py`

`Builder().run()` 은 아래 순서로 돈다. 공통 규칙은 다음과 같다.

- **DB 준비**: 파일을 지우고 `schema.sql` 로 새로 만든다. 그 뒤 `PRAGMA foreign_keys=OFF` 를 건다. 마지막에 `foreign_key_check` 결과를 `kb_meta.foreign_key_violations` 에 남긴다(지금 `{}`).
- **쓰기**: 표마다 5,000행씩 묶어 `INSERT OR IGNORE` 로 쓴다. 그래서 같은 id 는 처음 것만 남는다.
- **ID**: `hid(*parts)` = SHA-1(`'|'.join(parts)`)의 앞 16자다. 접두사 규칙은 DATA_DICTIONARY §0 에 있다.
- **정규화**: `norm(s)` 는 공백 · `·∙-_/()[]` · ™ · ® 를 지우고 소문자로 바꾼다. 별칭 · 메시지 중복 판정에 쓴다.
- **출처 사슬**: 원문 블록이 생길 때마다 `occurrence(occ_<doc>:<seq>)` 를 하나 만든다. 사실 행은 모두 `source_occurrence_id` · `source_tier` · `method` 를 가진다.

| # | 메서드 | 읽는 것 | 하는 일(정제 규칙) | 쓰는 표 |
|---|---|---|---|---|
| 0 | `sources` · `seeds` | seed/*.yaml, `prior_case_studies.json`(id 만) | 소스 3개를 등록한다. 업종 · 공간 · 솔루션 · 서비스 · 역량 · 규칙 · 시트 역할을 적재한다. 사례 URL → `dep_<id>` 를 미리 계산한다 | `source` · `vertical` · `segment_mapping` · `space_type` · `solution` · `service_product` · `capability` · `capability_rule` · `requires` · `placement_rule` · `sheet_role` |
| 1 | `products` | products · filter_meta · specs · features | 아래 「1단계 상품의 세부 규칙」 참고 | `category` · `product_family` · `product_model` · `family_category` · `product_tag` · `spec_value` · `feature_block` · `source_document(pdp/spec)` · `document_block` · `value_prop(usp, key/proof)` · `kg_edge(SOLD_AS)` |
| 2 | `build_aliases` | 앞 단계 별칭 + `CURATED_ALIASES` | 아래 「2단계 별칭의 세부 규칙」 참고 | `alias` |
| 3 | `pages` | `wkb_pages*.json` | 아래 「3단계 페이지의 세부 규칙」 참고 | `source_document(web_page)` · `document_block` · `occurrence` · `value_prop` · `kg_edge(DESCRIBED_BY)` |
| 4 | `industry_sections` | 업종 페이지(KR 17 · US) | 아래 「4단계 업종 섹션의 세부 규칙」 참고 | `industry_section` · `industry_section_item` · `space_label` · `value_prop` · `depicts` |
| 5 | `cases` | `prior_case_studies.json` + 사례 페이지 198 | 아래 「5단계 도입사례의 세부 규칙」 참고 | `deployment` · `deployment_space` · `deployment_item` · `deployment_need` · `kpi_claim` · `value_prop` · `depicts` |
| 6 | `mentions` | 중복 아닌 블록(스펙 제외)의 글 + alt | 모델코드 정확 일치(`code_exact`, 신뢰도 1.0)를 먼저 찾는다. 겹치지 않는 별칭 일치(`alias_exact`)를 더한다. 신뢰도는 제품군 · 솔루션 · 서비스 0.9, 그 밖 0.7 이고 대상이 여럿이면 −0.2 다 | `mention` |
| 7 | `capabilities` | 제품군마다 카테고리 · 하위 분류 · 이름 · 태그 · 정규 스펙 · 특장점 글 | `AUTO_RULES` 의 각 `fn(ctx)` 가 근거 문장을 돌려주면 적재한다(`rule_presence_v1`). 근거는 300자까지 | `provides` |
| 8 | `save_images` | 1–5단계에서 모은 이미지 | 자산(PC `url` + `url_mobile`)과 등장을 저장한다. 모두 `vlm_status='pending'` | `image_asset` · `image_occurrence` |
| 9 | `kg` | 위 표들 | 엣지 25종을 만든다(DATA_DICTIONARY §8 「그래프 관계」). 등급 · 방법 · 신뢰도 · 근거가 붙는다 | `kg_edge` |
| 10 | `chunks` | 중복 아닌 블록(h · p · feature · usp · spec · img alt) | 아래 「10단계 텍스트 청크의 세부 규칙」 참고 | `text_chunk` · `chunk_fts` |
| 11 | `finish` | — | 아래 「11단계 메타의 세부 규칙」 참고 | `spec_attr_def` · `kb_meta` |

### 1단계 상품의 세부 규칙

- **카테고리**
  - level 1 은 큐레이션한 `top_*` 이다.
  - level 2 는 사이트 목록 `cat_<root>` 다. `site_disp_clsf_no` · `site_filters_json` 을 가진다.
  - level 3 는 하위 분류 `cat_<root>__<dlgtDispClsfEnNm>` 다. 이름은 필터 패널 공식 라벨 > `SUBCAT_LABEL` > slug 순서로 정한다.
  - 비교 분류(`compDispClsfEnNm`, 예 `dvms-indoor`)도 level 2 로 만든다(`origin=site_api_comp`).
- **상품 카드** → `fam_<goodsId>`.
  - 대표 목록은 `members` 에서 사이트 목록 순서상 처음 소속된 목록이다.
  - 모든 소속은 `family_category(role=list)` 에, 비교 분류는 `role=comp` 에 쓴다.
- **문서 · 블록**
  - PDP 문서는 `doc_pdp_<goodsId>` 다. 블록 순서는 카드 → USP(`usp` 블록 + `value_prop(usp)`) → 갤러리 이미지(등급 C, `depicts confirmed 0.98`) → 특장점이다.
  - 특장점은 `pdp_features` 가 만든다.
    - 블록: 컴포넌트마다 `feature_block`(headline · sub · body · disclaimer) 하나를 만든다. 캐러셀 항목은 `parent_seq` 로 이어진다.
    - 메시지: 헤드라인 → `key_message`, 본문 → `proof_point` 다.
    - 이미지 등급: alt 문장이 장면을 서술하면 A, 아니면 A?C 다.
- **모델**
  - 카드의 `mdlCode` 와 `variants` 에서 `parentGoodsId` 가 같은 것을 모은다. ID 는 `mdl_<모델코드>` 다.
  - 같은 모델코드는 처음 것만 남긴다.
- **스펙**
  - 모델별 `goodsId` 의 행마다 `spec_value` 를 하나 만든다. 문서는 `doc_spec_<goodsId>` 다.
  - 정규 키는 `normalize_spec` 이 `SPEC_RULES`(정규식 → `norm_key`, 단위)로 정한다. 수치는 `value_num` · `value_num2`(범위 · 해상도), 단위 환산(㎛ → mm, g → kg)을 한다.
  - IP 등급은 `IP_RE` 로 찾아 `norm_key='ip_rating'` 행을 더 만든다.
  - 속성 정의는 `attr_<hid(root, 그룹, 항목)>` 다.
- **필터 → `product_tag`**
  - 필터 패널에 없는 값인데 목록 전체가 그대로 돌아오면 사이트가 무시한 필터로 보고 버린다. 지금 32개다. `kb_meta.notes` 에 남는다.
  - 종류는 `classify_filter` 로 정한다.
- **솔루션 ↔ 상품**: 시드 `site_code` 가 모델코드와 같으면 `SOLD_AS` 엣지를 만든다.

### 2단계 별칭의 세부 규칙

- 별칭 출처는 사이트 이름 · 마케팅 모델명 · grpPath · 모델코드 · 시드 이름 · 하위 분류 라벨 · 큐레이션이다.
- 걸러내는 것
  - `norm` 길이가 2 미만인 것은 버린다.
  - 카테고리 이름과 같은 일반 제품명(예 '냉장고')은 제품군 별칭으로 만들지 않는다.
  - 여러 목록에 같은 하위 분류 라벨이 있으면 단독 별칭을 만들지 않는다.
- 언급 탐지용 정규식을 만든다.
  - 별칭: 3자 이상이고 업종이 아닌 것을 긴 순서로 넣는다.
  - 모델코드: 영숫자 경계로 막는다.

### 3단계 페이지의 세부 규칙

- **문서**
  - 페이지마다 `doc_pg_<hid(경로)>` 를 만든다.
  - 사례 페이지는 `<title>` 이 모두 같아서 h2 를 제목으로 쓴다.
  - `/us/` 경로는 `src_site_us` · `en-US` 로 둔다.
- **선형화(`linearize`)**
  - 섹션 경로는 h2 > h3 > h4 를 이어 만든다.
  - PC/MO 중복은 h2 섹션의 서명((종류, 글 또는 이미지 키) 목록)으로 판정한다. 중복이면 `is_duplicate=1` 로 두고 검색 · 청크 · 언급에서 뺀다.
- **이미지**
  - 등급은 `grade_hint_for` 로 정한다.
  - 사례 사진은 바로 뒤 짧은 문단(4–120자, `CAPTION_STOP` 제외)을 캡션으로 쓴다.
- **연결**: 솔루션 · 서비스 상세 페이지는 시드 URL 로 연결해 `DESCRIBED_BY` 엣지를 만든다.
- **메시지**: 솔루션 · 서비스 · 랜딩 페이지에서 뽑는다.
  - h1–h3 제목(4–90자, 탐색 문구 제외) → `key_message` 다.
  - 바로 뒤 문단(15–400자) → `proof_point` 다.
  - 페이지당 40개까지다.

### 4단계 업종 섹션의 세부 규칙

- **섹션 나누기**: `parse_industry_blocks` 가 섹션을 hero · scene · recommend · cases 로 나눈다.
- **공간 정하기**
  - 라벨은 `spaces_for_label` 로 공간에 대응시킨다(`label_dict`).
  - scene 은 제목의 공간 표현도 더한다(`title_keyword`).
- **항목 해소(`resolve_item`)**
  - 링크가 있으면 다음 순서로 해소한다: 솔루션 URL → PDP → 사례 → 목록(+필터 → 하위 분류) → 카테고리 랜딩 → 모델코드 경로 → 옛 경로 → 경로 루트 → US 경로.
  - 링크가 없는 나열 항목은 별칭(부분 일치)으로 해소한다. 제품 단서가 없는 기능 문구는 버린다.
  - US 이름 대응은 신뢰도를 0.5 로 낮춘다.
- **메시지**
  - hero → `tagline` 이다.
  - scene 제목 → `key_message`, 설명 → `proof_point` 다.
  - 항목 수식어(+이름) → `key_message` 다.
- **기타**
  - 항목 이미지는 `depicts` 에 넣는다. cases 섹션은 confirmed 0.9, 나머지는 probable 0.6 이다.
  - 라벨 등장 수는 `space_label` 에 쌓는다. 대응하지 못한 라벨은 `method=unmapped` 로 남는다.

### 5단계 도입사례의 세부 규칙

- **id**
  - 사전 추출 218건은 `dep_<id>`, 사전에 없는 페이지는 `dep_pg_<hid>` 다.
  - 둘은 URL 경로로 짝짓는다.
- **페이지에서 뽑는 값**
  - 본문의 '업종 :' · '규모 :' 문장 → `site_industry_text` · `site_scale_text` 다.
  - 사이트 업종 필터는 `KR_CASE_INDUSTRY` 로 업종에 대응시킨다.
  - 공간은 `space_for_label` 로 정한다.
- **사용 제품**
  - `offer` 는 별칭 부분 일치로 해소한다(`prior_llm_offer`, T5).
  - 페이지 하단 '관련 제품' 링크는 `resolve_item` 으로 해소한다(`case_related_link`, T2).
- **그 밖**
  - needs · constraints · decision_factors · req_tags · proposal_content · new_req → `deployment_need` 다.
  - proof → `kpi_claim` 이다. 모두 `claim_flag=1` 이다.
  - quote → `proof_point` 다.
  - 사례 사진은 `depicts confirmed 0.95` 다.

### 10단계 텍스트 청크의 세부 규칙

- (문서, 섹션)마다 900자 안쪽으로 묶는다.
- 같은 섹션 안에서 반복되는 문구는 뺀다.
- id 는 `ch_<hid(문서, 섹션, 전체 글)>` 다. 같은 id 는 한 번만 넣는다.
- 청크 안의 언급 대상은 `entity_refs_json` 에 넣는다.
- FTS5 는 trigram 토크나이저를 쓴다.

### 11단계 메타의 세부 규칙

- 스펙 속성 정의에 값 개수(`n_values`)를 단다.
- `kb_meta` 에 `count.*` · `notes`(무효 필터 등) · `products_fetched_at` · `schema_version=kb_v1` 을 쓴다.
- 외래키 점검 결과를 남기고 `ANALYZE` 를 돈다.

빌드 결과 건수(`kb_meta.count.*`)

| 항목 | 건수 | 항목 | 건수 |
|---|---|---|---|
| documents | 1,795 | blocks | 91,212 |
| families | 605 | models | 1,067 |
| spec_values | 47,490 | product_tags | 1,215 |
| value_props | 14,699 | industry_sections | 469 |
| industry_items | 555 | deployments | 218 |
| kpi_claims | 294 | case_related_links | 304 |
| mentions | 32,598 | provides | 206 |
| image_assets | 10,251 | image_occurrences | 15,065 |
| kg_edges | 36,014 | chunks | 24,346 |

`spec_value` 표는 47,500행이다. IP 등급 행이 더해지기 때문이다.

---

## 4. 검색 인덱스 — `build/index_kb.py`

1. 검색 표를 비운다: `entity_doc` · `entity_fts` · `image_doc` · `image_fts` · `vec_index`.
2. **엔티티 문서 1,178개**를 만든다(제품군 · 모델 · 카테고리 · 솔루션 · 서비스 · 업종 · 공간 · 사례 · 역량).
   - 글은 이름 · 별칭 · USP · 특장점 헤드라인 · 필터 라벨 · 핵심 스펙 · 역량 등을 ` | ` 로 이은 것이다.
3. **이미지 문서 10,251개**를 만든다.
   - 글은 alt · 캡션 · 섹션 · 페이지 제목 · 페이지 유형 · 공간 · 업종 · 맥락 엔티티 이름 · depicts 대상 이름 · `grade:<등급>` 을 이은 것이다.
   - 중복은 빼고 3,000자까지 쓴다.
4. **LSA 벡터**를 만든다. 말뭉치는 청크(`섹션 경로 + 글`) + 엔티티(`이름 + 글`) + 이미지 글이다.
   - TF-IDF 설정: `TfidfVectorizer(analyzer='char_wb', ngram_range=(2,4), min_df=2, max_df=0.5, sublinear_tf=True, max_features=45000, dtype=float32)`
   - 차원 축소: `TruncatedSVD(n_components=192, random_state=0)` 뒤 L2 정규화
   - 저장: `vec_index.vec` 에 **float16** 바이트로 저장한다. `ref` 는 청크 id · `entity:<kind>:<id>` · `image:<img_id>` 이고, `space` 는 chunk · entity · image 다.
5. **모델 파일**: `kb/models/lsa_char24_v2.joblib` 에 저장한다.
   - 내용: `{tfidf, svd, name, dim}`(`compress=3`). `stop_words_` 는 지운다.
   - 질의 때 `query.py` 가 이 파일로 질의를 임베딩한다.
6. **메타 · 마무리**: `kb_meta` 에 `index.model` · `index.dim` · `index.n_*` · `index.explained_variance`(0.4556)를 쓰고 `VACUUM` 한다.

신경망 임베딩으로 바꿀 때는 `vec_index`(같은 ref · space)와 모델 로더만 바꾼다. 질의 인터페이스는 그대로다.

## 5. 품질 점검과 시험

| 명령 | 하는 일 |
|---|---|
| `build/qa.py` | `dr_metric`(DR01–DR26), `scenario_status`(S1–S15), 프로브 23개(`kb_meta.qa.probes`) → `docs/BUILD_REPORT.md`. 이 단계에서 DB 가 마지막으로 바뀐다 |
| `tests/test_scenarios.py` | 시나리오 41개 → `docs/SCENARIO_TEST_REPORT.md`. `WKB_TEST_REPORT` · `WKB_TEST_JSON` 로 출력 위치를 바꾼다 |
| `tests/make_cookbook.py` | 질의 패턴 예시 → `docs/QUERY_COOKBOOK.md` |
| `tests/make_fixture.py` | 스모크용 합성 픽스처 |
| `build/query.py` | 질의 라이브러리(`KB`)와 CLI. 패턴은 아래와 같다 |

`build/query.py` 의 질의 패턴

- 문장 분석: `A1`–`A3`
- 업종: `B1` · `B2`
- 제품 추천: `C1` · `C2` · `C3` · `C4` · `C6`
- 사례: `D1` · `D2` · `D3` · `D5`
- 메시지: `E1` · `E2` · `E3`
- 이미지: `G1` · `G2` · `G4` · `G5`
- 시나리오: `S1` · `S2`
- 검색 · 조회: `search` · `entity`

## 6. 스키마 요약

원본은 `build/schema.sql` 이고, 컬럼 뜻은 DATA_DICTIONARY.md 에 있다. 행 수는 이번 빌드 기준이다.

| 묶음 | 표(행 수) |
|---|---|
| 원문 근거 | `source`(3) · `source_document`(1,795) · `document_block`(91,212) · `occurrence`(91,212) |
| 고객 쪽 온톨로지 | `vertical`(51) · `segment_mapping`(16) · `space_type`(70) · `space_label`(58) · `industry_section`(469) · `industry_section_item`(555) |
| 제품 | `category`(200) · `product_family`(605) · `product_model`(1,067) · `product_tag`(1,215) · `family_category`(623) · `spec_attr_def`(2,770) · `spec_value`(47,500) · `solution`(14) · `service_product`(5) · `feature_block`(9,676) |
| 다리(역량) | `capability`(15) · `capability_rule`(21) · `provides`(206) · `requires`(14) · `placement_rule`(6) |
| 선례 | `deployment`(218) · `deployment_space`(481) · `deployment_item`(1,028) · `deployment_need`(4,174) · `kpi_claim`(294) |
| 메시지 | `value_prop`(14,699) |
| 이미지 | `image_asset`(10,251) · `image_occurrence`(15,065) · `depicts`(15,957) |
| 해소 · 그래프 | `alias`(3,314) · `mention`(32,598) · `kg_edge`(36,014) |
| 검색 | `text_chunk` · `chunk_fts`(24,346) · `entity_doc` · `entity_fts`(1,178) · `image_doc` · `image_fts`(10,251) · `vec_index`(35,775) |
| 메타 | `kb_meta`(29) · `dr_metric`(26) · `scenario_status`(15) · `sheet_role`(26) |

- FTS5 표는 모두 `tokenize='trigram'` 이다.
- JSON 컬럼(`*_json`)은 `ensure_ascii=False` 로 직렬화한 문자열이다.
- 근거 등급은 `T2_official` · `T3_case` · `T5_llm_extracted` · `T5_rule_draft` · `T5_seed_draft` 다.

---

## 7. Winmate 가 이 폴더를 쓰는 방법(kb 서비스)

| 설정 | 기본값 | 무엇 |
|---|---|---|
| `WKB_ROOT` | `<저장소>/winmate-kb` | `build/query.py`(질의 엔진으로 import) · `seed/` · `dashboard/` |
| `WKB_KB` | `<WKB_ROOT>/kb` | `winmate_kb.sqlite` · `models/*.joblib`(읽기 전용) |
| `WKB_THUMBS_DIR` | `<WKB_ROOT>/dashboard/build` | 썸네일 묶음 `thumbs_pack*.bin` |
| `WKB_IMAGE_DIR` | `<DATA_DIR>/kb/images` | 원본 이미지 로컬 사본 + `_originals.json` |

- **런타임 큐레이션**
  - `services/kb/src/winmate_kb/curation/*.yaml`(columns · display · image_samples · segments · solutions · spec_profiles)은 kb 서비스가 실행 중에 덧입히는 화면용 사전이다. DB 에는 들어가지 않는다.
  - `seed/ontology/categories.yaml` · `placement_rules.yaml` 도 kb 서비스가 직접 읽는다.
- **썸네일 묶음 형식**: `b'WTHB'` + uint32 머리 길이 + JSON 머리 `[[hash, w, h, w0, h0, len], …]` + webp 바이트를 이어 붙인 것이다.
  - `hash` 는 fnv36(`curation.img_key(asset.url 또는 url_mobile)`)다.
  - 176px(우선 3,384장)과 160px(나머지)로 모두 10,219장이다. image-us.samsung.com 20장은 CORS 때문에 없다.
- **원본 이미지**
  - `services/kb/scripts/kb_fetch_images.py` 가 인터넷이 되는 PC 에서 `thumb_select.json` 순서로 받는다.
  - 저장 형식: 긴 변 1,600px 이하 WebP(품질 82)다.
  - 사내망으로 옮길 때는 그 폴더를 통째로 복사한다.

---

## 8. raw 를 새로 수집할 때(DB 가 바뀐다)

`collect/README.md` 의 순서를 따른다. 브라우저에서 `https://www.samsung.com/sec/business/` 를 연 채 콘솔에서 실행한다. 같은 출처 XHR 을 쓰고, 요청 간격은 150–500 ms 다.

| 순서 | 스크립트 | 결과 변수 | raw 파일로 옮기는 법 |
|---|---|---|---|
| 1 | `01_categories.js` | `window.__cats` | (2번 입력) |
| 2 | `02_products_specs.js` | `window.__wkb` | `{cats, products, cardOrder, variants, filters, fetchedAt:startedAt, finishedAt}` → `wkb_products.json`, `__wkb.specs` → `wkb_specs.json` |
| 3 | `05_extra_categories.js` | `window.__wkb`(목록 8개 추가) | 위와 같음 |
| 4 | `06_filter_meta.js` | `window.__fmeta` | `{meta, tabs, members}` → `wkb_filter_meta.json` |
| 5 | `07_pdp_features_v2.js` | `window.__feat2` | `items` → `wkb_features.json`. 02 의 v1 `features` 는 쓰지 않는다 |
| 6 | `03_page_queue.js` | `window.__pagesQueue` | — |
| 7 | `04_pages_v2.js` | `window.__pages2` | `{items, fetchedAt}` → `wkb_pages_v2.json` |
| 8 | `08_transfer_gzip_b64.js` | — | `WKBGZ1:<길이>:<b64 길이>:<base64>` 로 묶는다 → `python build/recv.py <tool-result.json> raw/<파일>` 로 푼다(길이 · JSON 확인) |

**수집 스크립트에 남지 않은 것** — 다시 수집할 때 직접 채워야 한다.

- **사례 slug 목록**: `03_page_queue.js` 는 `window.__caseSlugs`(사례 slug JSON 배열)를 이미 있다고 보고 쓴다. 이 목록은 사례 목록 페이지(`/sec/business/insights/case-study/`)에서 모아야 하는데, 그 스크립트가 저장되지 않았다.
- **v1 페이지 수집**: `04_pages_v2.js` 는 v1 페이지 수집(`window.__pages`)이 끝나기를 기다린다. v1 스크립트도 저장되지 않았다. 혼자 돌릴 때는 마지막 줄 대신 `window.__runPages2()` 를 바로 부른다.
- **사례 구조화**: `prior_case_studies.json` 을 만든 LLM 추출은 프롬프트 · 모델 기록이 없다.
  - 다시 만들려면 같은 키(§2.1)와 `meta.taxonomy` 코드표로 새로 추출해야 한다.
  - T5 등급이므로 다시 뽑으면 값이 달라진다.
- **썸네일 생성 코드**: 썸네일 묶음을 만든 브라우저 쪽 코드도 저장되지 않았다(`dashboard/README.md` 「썸네일」에 방식만 있음). 그래서 `thumbs_pack*.bin` 은 git 에 그대로 둔다.

새로 수집했다면 다음을 한다.

1. §2.1 SHA-256 표를 갱신한다.
2. `run_all.sh` 를 돌린다.
3. `docs/BUILD_REPORT.md` 에서 건수 · DR · 프로브 변화를 확인한다.
4. Winmate 쪽은 `make test SERVICE=kb` · e2e 를 다시 돌린다. kb 서비스 시험은 이 DB 의 실데이터를 쓴다.

---

## 9. git 에 있는 것과 없는 것

| 경로 | git | 이유 · 다시 만드는 법 |
|---|---|---|
| `raw/*.json` | ✅ | 재현의 출발점이다(다시 수집하면 달라짐) |
| `seed/` · `build/` · `collect/` · `tests/` · `docs/` · `dashboard/*.py` · `dashboard/src/` | ✅ | 코드 · 사전 · 문서 |
| `dashboard/build/thumbs_pack*.bin`(21 MB) | ✅ | 브라우저에서만 만들 수 있다(생성 코드 없음) |
| `kb/winmate_kb.sqlite`(191 MB) | ❌ | `bash build/run_all.sh`(GitHub 100 MB 파일 제한도 넘는다) |
| `kb/models/*.joblib`(28 MB) | ❌ | `build/index_kb.py` |
| `kb/_parts*/` | ❌ | 예전 브라우저 → 빌드 환경 전송 조각 |
| `dashboard/build/` 의 나머지 · `dashboard/site/` | ❌ | `bash dashboard/run.sh`(썸네일 묶음 필요) |
| `dashboard/thumb_select.json` · `thumb_hashes.txt` | ❌ | `python dashboard/thumb_select.py`(DB 에서 같은 파일이 나온다 — 확인함) |
| `<DATA_DIR>/kb/images/` | ❌ | `services/kb/scripts/kb_fetch_images.py`(인터넷 필요) |
