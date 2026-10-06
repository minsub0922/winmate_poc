# 데이터 사전 (kb/winmate_kb.sqlite)

SQLite 한 파일에 원문 근거, 온톨로지, 제품, 선례, 메시지, 이미지, 그래프, 검색 인덱스가 같이 들어 있다.
스키마 원본은 `build/schema.sql`이다. 이 문서는 표마다 무엇이 들어 있고 어디서 왔는지 설명한다.

## 0. 공통 규칙

### 출처 컬럼

사실을 담은 행에는 아래 컬럼이 붙는다.

| 컬럼 | 뜻 |
|---|---|
| `source_occurrence_id` | `occurrence.id`. 원문 블록(`document_block`)으로 이어지고, 거기서 문서 URL과 섹션 경로로 이어진다 |
| `source_tier` | 근거 등급(아래 표) |
| `method` | 값을 만든 방법(아래 표). 사람이 검수할 때 무엇을 믿고 무엇을 다시 봐야 하는지 알려 준다 |
| `confidence` | 0~1. 링크·별칭 해소처럼 추론이 들어간 행에만 있다 |

### 근거 등급(source_tier)

| 등급 | 뜻 | 이 빌드의 예 |
|---|---|---|
| `T2_official` | 삼성 공식 사이트에 그대로 있는 값 | 상품 API, 스펙 API, PDP 문구, 업종 페이지 섹션, 사이트 필터 |
| `T3_case` | 도입사례 페이지(고객 사례) | 사례 제목·사진·업종 필터 |
| `T5_llm_extracted` | 이전 세션에서 LLM이 사례 본문을 구조화한 값(사람 검토 전) | 사례의 공간·사용 제품·KPI 문장 |
| `T5_rule_draft` | 이 빌드의 presence 규칙이 붙인 값(전문가 승인 전) | `provides` |
| `T5_seed_draft` | 시드 YAML 초안(전문가 승인 전) | `requires`, Winmate 세그먼트 대응 |

T1(제조사 스펙시트·카탈로그 PDF), T4(전문가 승인), T6(생성물)은 이번 빌드에 없다.

### 주요 method 값

| method | 뜻 |
|---|---|
| `site_api_verbatim`, `spec_api_parse`, `spec_api_regex` | 사이트 API 응답을 그대로 또는 정규식으로 옮김 |
| `pdp_html_verbatim`, `page_heading_verbatim`, `page_text_verbatim` | 페이지 HTML의 문장을 그대로 옮김 |
| `industry_parser_v2`, `industry_heading_verbatim`, `industry_text_verbatim`, `industry_hero_verbatim`, `industry_item_tagline_verbatim` | 업종 페이지 결정적 파서 |
| `site_list_filter` | 카테고리 목록 필터에 상품이 속함(사이트의 공식 분류) |
| `link_pdp`, `link_solution_page`, `link_case_page`, `link_category_list(+filter/+subcat)`, `link_category_landing`, `link_model_code` | '자세히 보기' 같은 링크의 대상 URL로 해소 |
| `name_alias`, `name_alias_substring`, `alias_substring` | 이름·별칭 사전으로 해소(링크가 없을 때). 신뢰도가 더 낮다 |
| `rule_presence_v1` | `build/curation.py`의 `AUTO_RULES`(필터·스펙·문구에 '있다'만 보는 규칙) |
| `prior_llm_extract`, `prior_llm+alias` | 이전 세션 LLM 구조화 결과 + 별칭 해소 |
| `case_related_link` | 도입사례 페이지 하단 '관련 제품' 링크(사이트가 직접 밝힌 사용 제품) |
| `curated_dict`, `curated_keyword` | `curation.py` 사전으로 공간 라벨을 공간 유형에 대응 |

### ID 규칙

| 접두 | 대상 | 예 |
|---|---|---|
| `doc_pdp_<goodsId>`, `doc_spec_<goodsId>`, `doc_pg_<hash>` | 문서(PDP, 스펙 API 응답, 웹 페이지) | `doc_pdp_G000183916` |
| `<doc_id>:<seq>` | 문서 블록 | `doc_pg_1a2b…:42` |
| `occ_<block_id>` | 출처(occurrence) | `occ_doc_pg_1a2b…:42` |
| `top_*` | 최상위 카테고리(큐레이션) | `top_display` |
| `cat_<목록 slug>` | 사이트 카테고리 목록 | `cat_smart-signage` |
| `cat_<목록 slug>__<하위 slug>` | 사이트 하위 분류 | `cat_smart-signage__videowall` |
| `fam_<goodsId>` | 상품 카드(제품군·시리즈) | `fam_G000181210` |
| `mdl_<모델코드>` | 모델(옵션·사이즈 단위) | `mdl_AM052BN4DBH1` |
| `sol_<code>`, `svc_<code>` | 솔루션, 서비스 | `sol_lynk_cloud` |
| `kr_*`, `us_*`, `wm_*` | 업종(KR 사이트, US 사이트, Winmate 16 세그먼트) | `kr_hotel` |
| 공간 코드 | 공간 유형(시드 + 큐레이션) | `guest_room` |
| `cap_<code>` | 역량(Capability) | `cap_weatherproof` |
| `dep_<사전 id>`, `dep_pg_<hash>` | 도입사례(사전 추출에 있는 것 / 페이지만 있는 것) | `dep_17` |
| `sec_*`, `si_*` | 업종 페이지 섹션, 섹션 항목 | |
| `img_<hash>`, `io_<hash>` | 이미지 자산(PC/MO 묶음), 이미지 등장 | |
| `vp_*`, `ft_*`, `sv_*`, `attr_*`, `kpi_*`, `men_*`, `ch_*` | 메시지, 특장점 블록, 스펙 값, 스펙 속성, KPI, 언급, 청크 | |

## 1. 원문 근거

| 표 | 내용 |
|---|---|
| `source` | 소스 3개: KR 사이트, US 사이트, 이전 세션의 도입사례 구조화 결과 |
| `source_document` | 문서 1건 = 웹 페이지, PDP, 스펙 API 응답 1개. `page_type`: industry · solution · service · landing · case_study · case_list · pdp · spec · us_vertical · us_solution · us_landing. `meta_json`에 goodsId·경로 |
| `document_block` | 페이지를 순서대로 편 블록. `block_type`: h · p · a · img · usp · feature · spec. `section_path`는 가장 가까운 h2 > h3 > h4. `is_duplicate=1`이면 PC/모바일 중복 섹션(검색·청크에서 제외) |
| `occurrence` | 블록 1개에 대한 출처 핸들. 모든 사실 행이 이것을 가리킨다 |

## 2. 고객 쪽 온톨로지

| 표 | 내용 |
|---|---|
| `vertical` | 업종. `scheme`: kr_site(사이트 업종별 제안 10개와 하위 17개) · us_site(13개) · winmate16 |
| `segment_mapping` | Winmate 16 세그먼트 ↔ KR·US 업종 대응(시드 초안, 빈칸 `<<FILL>>` 포함) |
| `space_type` | 공간 유형. 시드 54개 + 업종 페이지·사례에서 관측되어 추가한 16개(`origin=kb_build_curated`) |
| `space_label` | 업종 페이지에 실제로 쓰인 공간 라벨(예: '객실 내부', '호텔 리셉션')과 대응한 공간 유형, 등장 횟수. 대응 못 한 라벨은 `method=unmapped`로 남는다 |
| `industry_section` | 업종 페이지 섹션 = 장면. `kind`: hero(상단 캐치프레이즈) · scene(공간 장면) · recommend(추천 솔루션/서비스) · cases(고객 도입사례). `labels_json`은 사이트 라벨 원문, `space_types_json`은 대응한 공간 유형 전부, `space_method`는 label_dict 또는 title_keyword(제목의 공간 표현), `chips_json`은 공간이 아닌 짧은 문구(기능 칩·수식어) |
| `industry_section_item` | 장면 안의 항목. `item_kind`: link_item('자세히 보기' 링크가 있는 항목) · listed_item(링크 없이 나열된 제품, 예: 객실 내부 기기 목록) · recommended · case_link. `target_kind/target_id`는 해소된 대상(family·category·solution·service·deployment·model), `item_space_label`은 모바일 분할 섹션 등에서 항목 단위로 확인된 공간 라벨, `image_ids_json`은 항목에 붙은 이미지 |

## 3. 제품 쪽

| 표 | 내용 |
|---|---|
| `category` | 3단계. level 1 `top_*`(큐레이션), level 2 사이트 카테고리 목록(`site_disp_clsf_no`=사이트 분류 번호, `site_filters_json`=목록 필터 값), level 3 사이트 하위 분류(이름은 목록 필터 패널의 공식 라벨). `origin=site_api_comp`는 사이트 비교 분류(예: `dvms-indoor` 시스템에어컨 실내기) |
| `product_family` | 사이트 상품 카드 = 제품군(시리즈). 이름, 대표 모델코드, 마케팅 모델명, 상세 URL, USP(카드 문구), PDP 제목·설명, 판매상태코드(사이트 원값), 등록일 |
| `product_model` | 모델코드(사이즈·용량 옵션 단위). `option_name/value`(예: 용량 5.2 kW), `is_family_default` |
| `family_category` | 상품이 노출되는 모든 목록(`role=list`)과 사이트 비교 분류(`role=comp`). 한 상품이 여러 목록에 나오는 경우를 모두 담는다 |
| `product_tag` | 목록 필터 소속 = 공식 세그먼트 라벨. `site_group`(예: 유형 · 사이즈 · 밝기)과 `site_label`(예: 비디오월 · 3000nits 이상)은 사이트 필터 패널 원문, `tag_kind`는 정규화한 종류 |
| `spec_attr_def` | 카테고리별 스펙 속성 정의(그룹·항목명), 정규 키, 단위, 값 개수 |
| `spec_value` | 모델별 스펙 원값(`value_raw`) + 정규 키(`norm_key`)·수치(`value_num`, 범위면 `value_num2`)·단위. IP 등급은 `norm_key=ip_rating`, `value_unit=IP55` 형태로 별도 행 |
| `feature_block` | PDP 특장점 컴포넌트 원문. `component_type`(feature-benefit · feature-full-bleed · textbox-simple · carousel-container · item 등), `headline`, `sub`, `body`, 면책 문구(`disclaimer`), 이미지 수. 캐러셀 하위 항목은 `parent_seq`로 부모 컴포넌트에 연결 |
| `solution`, `service_product` | 솔루션 14개·서비스 5개(시드). `document_id`는 수집한 상세 페이지 |

정규 스펙 키(`norm_key`): screen_size_cm · screen_size_inch · brightness_nit · resolution(단위 px 또는 dpi, value_num×value_num2) · pixel_pitch_mm(㎛ 표기는 mm로 환산) · operation_hours(h/7d, 24면 상시) · operating_temp_c · outdoor_temp_cool_c · outdoor_temp_heat_c(실외기 사용 온도 범위) · cooling_capacity_kw · heating_capacity_kw(정격, '최소/정격/최대'면 정격값과 최대값) · cooling/heating_capacity_min_kw · _max_kw · power_consumption(단위 W 또는 kW) · energy_grade · capacity_l · dimensions · weight_kg(g 표기는 kg로 환산) · release_ym · ip_rating_field · ip_rating(`value_unit`=IP54 형태). 문자 속성(touch · panel_type · refrigerant · smartthings · wifi · os · cpu)은 수치를 뽑지 않는다.

## 4. 연결 계층(Capability)

| 표 | 내용 |
|---|---|
| `capability` | 역량 15개(시드). 예: weatherproof, sunlight_readable, continuous_operation, touch_interactive, hospitality_tv_mgmt |
| `capability_rule` | 시드 규칙(임계값 빈칸, `status=draft`, 실행 안 함) + 자동 presence 규칙 13개(`status=draft_auto`) |
| `provides` | 제품군 → 역량. `evidence`에 근거(예: "사이트 목록 필터 'outdoor'", "스펙 '제품 사용 시간' = 24/7") |
| `requires` | 공간 → 역량(hard/soft). 시드 초안 |
| `placement_rule` | 배치·수량 규칙. 모두 draft(실행 안 함) |

## 5. 선례(도입사례)

| 표 | 내용 |
|---|---|
| `deployment` | 사례 1건. 제목·날짜·URL·형식, 사이트 업종 필터(`industry_raw_json`)와 대응한 KR 업종(`vertical_ids_json`), 페이지의 '업종 :'·'규모 :' 문장, 이전 세션 LLM 추출의 고객 유형·규모·인용문 |
| `deployment_space` | 사례의 공간(원문 문자열 → 공간 유형) |
| `deployment_item` | 사례가 쓴 제품·솔루션. `source=case_related_link`(사이트 '관련 제품' 링크, T2) 또는 `prior_llm_offer`(T5) |
| `deployment_need` | 요구·제약·결정 요인·요구 태그(R01~R24)·제안 내용 태그(P01~P22) |
| `kpi_claim` | 성과 문장. `has_number`, `claim_flag=1`(대외 사용 전 확인) |

## 6. 메시지

`value_prop` 한 행 = 원문 문구 하나.

| level | 출처 |
|---|---|
| tagline | 업종 페이지 상단 캐치프레이즈(예: "고객 유치 경쟁력을 갖춘 미래형 호텔을 완성하다") |
| key_message | 업종 장면 제목, 업종 항목 수식어+이름, PDP 특장점 헤드라인, 솔루션·랜딩 페이지 헤딩 |
| proof_point | 장면 설명, 특장점 본문, 솔루션 헤딩 아래 설명(`parent_id`로 key_message에 연결), 사례 인용문 |
| usp | 상품 카드 USP |

`about_kind/about_id`가 대상(family · solution · service · category · vertical · industry_section · deployment)이고, 업종·공간 문맥이 있으면 `vertical_id`·`space_type_id`가 채워진다. `claim_flag=1`은 숫자·최고·최초·1위 같은 주장 표현이 있는 문구다.

## 7. 이미지

| 표 | 내용 |
|---|---|
| `image_asset` | 이미지 1개(PC 원본 `url` + 모바일 변형 `url_mobile`을 한 자산으로). `grade_hint`, `grade_hint_reason`, `rights`(official · customer_case), `vlm_status=pending` |
| `image_occurrence` | 이미지가 어느 문서의 어느 블록·섹션에 나왔는지 + 맥락: `alt`, `caption`(사례 사진 아래 문장), `context_space_type_id`, `context_vertical_id`, `context_entities_json`(같은 섹션 항목의 해소 대상) |
| `depicts` | 이미지 → 대상. `level_label`: confirmed(PDP 갤러리, 사례 사진, 업종 페이지 사례 썸네일) · probable(특장점 이미지, 업종 장면 항목 이미지) · context |

등급 힌트(VLM 판정 전):

| 힌트 | 뜻 | 정한 근거 |
|---|---|---|
| A | 공간 + 제품(실제 설치·연출 장면) | 도입사례 사진, alt 문장이 공간 속 설치 장면을 서술 |
| A?C | 공간 연출이거나 제품 컷(미판정) | 업종 장면 항목 이미지, PDP 특장점 이미지 |
| C | 제품 단독 컷 | PDP 갤러리, 사례 '관련 제품' 썸네일 |
| D | 도식·UI | 파일명·alt 문장 패턴 |
| E | 아이콘·로고 | 파일명 패턴 |

## 8. 해소·그래프·검색

| 표 | 내용 |
|---|---|
| `alias` | 표면형 → 대상(사이트 이름, 마케팅 모델명, 모델코드, 시드 이름, 큐레이션 별칭). `surface_norm`은 공백·기호를 지운 소문자 |
| `mention` | 블록 안에서 찾은 언급(모델코드 정확 일치, 별칭 일치). 같은 제품이 PDP·업종 페이지·솔루션 페이지·사례에 흩어진 것을 이 표로 모은다 |
| `kg_edge` | 그래프 엣지(아래 표). 모든 엣지에 등급·방법·신뢰도·근거 |
| `text_chunk`, `chunk_fts` | 섹션 단위 원문 청크(≤ 900자, 중복 블록 제외)와 FTS5 trigram 인덱스. `entity_refs_json`은 청크 안의 언급 대상 |
| `entity_doc`, `entity_fts` | 엔티티별 검색 문서(이름·별칭·USP·특장점 헤드라인·필터 라벨·핵심 스펙·역량 등) |
| `image_doc`, `image_fts` | 이미지별 검색 문서(alt·캡션·섹션·페이지 제목·공간·업종·맥락 엔티티 이름·등급) |
| `vec_index` | 밀집 벡터(float16 저장, L2 정규화, 192차원). `space`: chunk · entity · image. 모델은 `kb/models/lsa_char24_v2.joblib`(문자 2~4gram TF-IDF 4.5만 특징 → SVD). 신경망 임베딩으로 바꿀 때는 이 표와 모델 파일만 교체 |

그래프 관계:

| rel | 방향 | 근거 |
|---|---|---|
| IN_CATEGORY, LISTED_IN, IN_COMP_CATEGORY, CHILD_OF, VARIANT_OF, HAS_TAG | 제품 구조 | 사이트 API·목록 |
| SOLD_AS | 솔루션 → 상품 카드 | 시드 사이트 코드 = 모델코드 |
| DESCRIBED_BY | 솔루션·서비스 → 상세 페이지 문서 | 시드 URL |
| PROVIDES | 제품군 → 역량 | presence 규칙 |
| REQUIRES_HARD / REQUIRES_SOFT | 공간 → 역량 | 시드 초안 |
| HAS_SPACE | 업종 → 공간 | 업종 페이지 장면 |
| RECOMMENDED_BY_SITE | 공간 → 카테고리·제품군·솔루션 | 업종 페이지 장면 항목(`evidence` = 업종\|섹션) |
| FEATURED_BY_SITE | 업종 → 카테고리·제품군·솔루션 | 업종 페이지 장면·추천 솔루션 |
| FEATURED_CASE | 업종 → 사례 | 업종 페이지 '고객 도입사례' |
| MAPS_TO | Winmate 세그먼트 → KR·US 업종 | 시드 초안 |
| IN_VERTICAL, AT_SPACE, USES, MENTIONS | 사례 → 업종·공간·제품·언급 대상 | 사례 필터, 관련 제품 링크, 이전 추출, 페이지 언급 |
| DEPICTS_CONFIRMED / DEPICTS_PROBABLE / DEPICTS_CONTEXT | 이미지 → 대상 | 페이지 맥락 |
| SHOWN_IN_CONTEXT_OF | 이미지 → 공간 | 업종 장면·alt 문장 |
| ABOUT | 메시지 → 대상 | 원문 위치 |

## 9. 메타·품질

| 표 | 내용 |
|---|---|
| `kb_meta` | 적재 건수(`count.*`), 빌드 메모, 외래키 점검 결과, 인덱스 정보, QA 프로브 결과 |
| `dr_metric` | 데이터 요소(DR01~DR26)별 지표·값·상태 |
| `scenario_status` | 시나리오(S1~S15)별 상태(ready · partial · blocked_by_build · blocked_by_source)와 사유 |
| `sheet_role` | Winmate 시트 역할 시드 |
