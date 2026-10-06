-- Winmate KB schema (SQLite). docs/02_DATA_MODEL.md 의 부분 구현.
-- 사실 행 공통 출처 컬럼: source_occurrence_id, source_tier, confidence, method
PRAGMA foreign_keys = ON;   -- 빌드 중에는 끄고, 끝에서 foreign_key_check 결과를 kb_meta 에 기록한다

-- ── 소스 ─────────────────────────────────────────────
CREATE TABLE source (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL, location TEXT, notes TEXT
);
CREATE TABLE source_document (
  id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES source(id),
  kind TEXT NOT NULL,            -- web_page | product_api | spec_api | pdp_page | prior_extraction
  page_type TEXT,                -- industry | solution | service | landing | case_study | pdp | category_list | us_vertical | ...
  url TEXT, title TEXT, description TEXT, og_image TEXT, locale TEXT,
  fetched_at TEXT, published_at TEXT, content_hash TEXT, status TEXT, meta_json TEXT
);
CREATE TABLE document_block (
  id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES source_document(id),
  seq INTEGER NOT NULL, block_type TEXT NOT NULL,   -- h | p | img | a | spec | feature | usp
  level INTEGER, text TEXT, href TEXT, img_src TEXT, img_alt TEXT,
  section_path TEXT,             -- 가장 가까운 h2 > h3 > h4 경로
  is_duplicate INTEGER DEFAULT 0 -- PC/MO 중복 등
);
CREATE INDEX ix_block_doc ON document_block(document_id, seq);
CREATE TABLE occurrence (
  id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES source_document(id),
  block_id TEXT REFERENCES document_block(id), kind TEXT NOT NULL, locator_json TEXT
);

-- ── 고객 측 온톨로지 ─────────────────────────────────
CREATE TABLE vertical (
  id TEXT PRIMARY KEY, code TEXT UNIQUE, name_ko TEXT, name_en TEXT, parent_id TEXT, scheme TEXT, url TEXT, status TEXT
);
CREATE TABLE segment_mapping (
  winmate_segment TEXT, name_ko TEXT, kr_vertical_codes TEXT, us_vertical_codes TEXT, catalog_chapter TEXT, status TEXT
);
CREATE TABLE space_type (
  id TEXT PRIMARY KEY, code TEXT UNIQUE, name_ko TEXT, default_attrs_json TEXT, origin TEXT, status TEXT
);
CREATE TABLE space_label (            -- 소스에 실제로 쓰인 공간 표현 → 공간 유형
  label TEXT, locale TEXT, space_type_id TEXT REFERENCES space_type(id), method TEXT, status TEXT, occurrences INTEGER,
  PRIMARY KEY(label, locale)
);
CREATE TABLE industry_section (       -- 업종 페이지의 섹션(장면) = 공간 + 제품·솔루션 묶음
  id TEXT PRIMARY KEY, vertical_id TEXT REFERENCES vertical(id), document_id TEXT REFERENCES source_document(id),
  seq INTEGER, kind TEXT,               -- hero | scene | recommend | cases
  title TEXT, description TEXT, tagline TEXT,
  space_label TEXT,                     -- 사이트 라벨 원문(여러 개면 ' · ')
  space_type_id TEXT,                   -- 첫 번째 공간 유형
  space_types_json TEXT,                -- 라벨 전체 → 공간 유형 목록
  space_method TEXT,                    -- label_dict | title_keyword | none
  labels_json TEXT, chips_json TEXT,    -- 공간 라벨 / 공간이 아닌 짧은 문구(기능 칩·태그라인)
  block_from INTEGER, block_to INTEGER,
  source_occurrence_id TEXT, source_tier TEXT, method TEXT
);
CREATE TABLE industry_section_item (
  id TEXT PRIMARY KEY, section_id TEXT REFERENCES industry_section(id), seq INTEGER,
  item_kind TEXT,                       -- link_item | listed_item | recommended | case_link
  item_name TEXT, item_tagline TEXT, link_url TEXT, link_path TEXT, link_filter TEXT,
  item_space_label TEXT, item_space_type_id TEXT,   -- 모바일 분할 섹션 등에서 항목 단위로 확인된 공간
  target_kind TEXT, target_id TEXT, resolve_method TEXT, confidence REAL,
  image_ids_json TEXT,
  source_occurrence_id TEXT, source_tier TEXT
);

-- ── 제품 측 ─────────────────────────────────────────
CREATE TABLE category (
  id TEXT PRIMARY KEY, code TEXT UNIQUE, parent_id TEXT, name_ko TEXT, level INTEGER,
  list_url TEXT, site_disp_clsf_no TEXT, site_filters_json TEXT, origin TEXT
);
CREATE TABLE product_family (          -- 사이트 상품 카드(사이즈·용량 옵션을 묶은 단위) = Series
  id TEXT PRIMARY KEY, goods_id TEXT UNIQUE, category_id TEXT REFERENCES category(id), subcategory_slug TEXT,
  name_ko TEXT, default_model_code TEXT, marketing_model TEXT, grp_path TEXT, detail_url TEXT,
  usp_json TEXT, sale_status_code TEXT, registered_at TEXT, goods_type_code TEXT,
  pdp_title TEXT, pdp_description TEXT, ctg1 TEXT, ctg2 TEXT,
  source_occurrence_id TEXT, source_tier TEXT
);
CREATE TABLE product_model (           -- 개별 모델코드(사이즈·용량 옵션) = Model/SKU
  id TEXT PRIMARY KEY, model_code TEXT UNIQUE, goods_id TEXT, family_id TEXT REFERENCES product_family(id),
  option_name TEXT, option_value TEXT, is_family_default INTEGER, sold_out_flag TEXT,
  source_occurrence_id TEXT, source_tier TEXT
);
CREATE TABLE product_tag (             -- 사이트 목록 필터 = 공식 세그먼트 레이블
  family_id TEXT REFERENCES product_family(id), tag_kind TEXT, tag_value TEXT, site_filter TEXT, category_id TEXT,
  site_group TEXT, site_label TEXT,     -- 사이트 필터 패널의 공식 그룹명·라벨(예: 유형 / 비디오월)
  source_tier TEXT, method TEXT, PRIMARY KEY(family_id, site_filter, category_id)
);
CREATE TABLE family_category (          -- 상품 카드가 노출되는 모든 목록(복수 소속) + 사이트 비교 분류
  family_id TEXT REFERENCES product_family(id), category_id TEXT REFERENCES category(id), role TEXT, -- list | comp
  PRIMARY KEY(family_id, category_id)
);
CREATE TABLE spec_attr_def (
  id TEXT PRIMARY KEY, category_root TEXT, group_name TEXT, attr_name TEXT, norm_key TEXT, unit TEXT, n_values INTEGER
);
CREATE TABLE spec_value (
  id TEXT PRIMARY KEY, model_id TEXT REFERENCES product_model(id), family_id TEXT, attr_id TEXT REFERENCES spec_attr_def(id),
  group_name TEXT, attr_name TEXT, value_raw TEXT, norm_key TEXT, value_num REAL, value_num2 REAL, value_unit TEXT,
  source_occurrence_id TEXT, source_tier TEXT, method TEXT
);
CREATE INDEX ix_spec_model ON spec_value(model_id);
CREATE INDEX ix_spec_norm ON spec_value(norm_key, value_num);
CREATE TABLE solution (
  id TEXT PRIMARY KEY, code TEXT UNIQUE, name_ko TEXT, aliases_json TEXT, kind TEXT, site_code TEXT, url TEXT, document_id TEXT, origin TEXT
);
CREATE TABLE service_product (
  id TEXT PRIMARY KEY, code TEXT UNIQUE, name_ko TEXT, aliases_json TEXT, target_category TEXT, url TEXT, document_id TEXT
);
CREATE TABLE feature_block (           -- PDP 특장점 블록(원문)
  id TEXT PRIMARY KEY, family_id TEXT REFERENCES product_family(id), seq INTEGER, parent_seq INTEGER,
  component_type TEXT,                  -- feature-benefit | feature-full-bleed | carousel-container | textbox-simple ...
  headline TEXT, sub TEXT, body TEXT, disclaimer TEXT, n_images INTEGER,
  source_occurrence_id TEXT, source_tier TEXT
);

-- ── 다리 계층 ───────────────────────────────────────
CREATE TABLE capability (id TEXT PRIMARY KEY, code TEXT UNIQUE, name_ko TEXT, description TEXT);
CREATE TABLE capability_rule (
  id TEXT PRIMARY KEY, capability_id TEXT, category TEXT, expression TEXT, params_json TEXT, explanation_ko TEXT, status TEXT, origin TEXT
);
CREATE TABLE provides (
  family_id TEXT, model_id TEXT, capability_id TEXT, rule_id TEXT, evidence TEXT, source_tier TEXT, method TEXT,
  PRIMARY KEY(family_id, capability_id, rule_id)
);
CREATE TABLE requires (space_type_id TEXT, capability_id TEXT, strength TEXT, status TEXT, origin TEXT);
CREATE TABLE placement_rule (id TEXT PRIMARY KEY, kind TEXT, space TEXT, category TEXT, expression TEXT, params_json TEXT, status TEXT);

-- ── 선례 ───────────────────────────────────────────
CREATE TABLE deployment (
  id TEXT PRIMARY KEY, prior_id INTEGER, title TEXT, date TEXT, url TEXT, format TEXT, document_id TEXT,
  customer_type TEXT, scale TEXT, quote TEXT, industry_raw_json TEXT, product_group_json TEXT, solution_group_json TEXT,
  vertical_ids_json TEXT, site_industry_text TEXT, site_scale_text TEXT,
  source_tier TEXT, method TEXT
);
CREATE TABLE deployment_space (deployment_id TEXT, space_raw TEXT, space_type_id TEXT, method TEXT);
CREATE TABLE deployment_item (
  deployment_id TEXT, item_raw TEXT, target_level TEXT, target_kind TEXT, target_id TEXT, resolve_method TEXT, confidence REAL,
  source TEXT,                          -- case_related_link(사이트 '관련 제품' 링크, T2) | prior_llm_offer(T5)
  link_url TEXT, source_tier TEXT
);
CREATE TABLE deployment_need (deployment_id TEXT, need_raw TEXT, kind TEXT); -- need | constraint | decision_factor | req_tag | proposal_content
CREATE TABLE kpi_claim (
  id TEXT PRIMARY KEY, deployment_id TEXT, text TEXT, has_number INTEGER, claim_flag INTEGER, source_tier TEXT, method TEXT
);

-- ── 메시지 ─────────────────────────────────────────
CREATE TABLE value_prop (
  id TEXT PRIMARY KEY, level TEXT,       -- tagline | key_message | proof_point | usp
  text TEXT NOT NULL, parent_id TEXT, about_kind TEXT, about_id TEXT, vertical_id TEXT, space_type_id TEXT,
  locale TEXT, claim_flag INTEGER, source_occurrence_id TEXT, source_tier TEXT, method TEXT
);

-- ── 이미지 ─────────────────────────────────────────
CREATE TABLE image_asset (
  id TEXT PRIMARY KEY, url TEXT UNIQUE, url_mobile TEXT, media_type TEXT, grade_hint TEXT, grade_hint_reason TEXT,
  rights TEXT, n_occurrences INTEGER, vlm_status TEXT
);
CREATE TABLE image_occurrence (
  id TEXT PRIMARY KEY, asset_id TEXT REFERENCES image_asset(id), document_id TEXT, block_id TEXT,
  page_type TEXT, alt TEXT, caption TEXT, section_path TEXT, context_space_type_id TEXT, context_vertical_id TEXT,
  context_entities_json TEXT
);
CREATE TABLE depicts (
  asset_id TEXT, target_kind TEXT, target_id TEXT, level_label TEXT, evidence TEXT, confidence REAL
);

-- ── 해소 ───────────────────────────────────────────
CREATE TABLE alias (surface TEXT, surface_norm TEXT, target_kind TEXT, target_id TEXT, kind TEXT, source TEXT);
CREATE INDEX ix_alias_norm ON alias(surface_norm);
CREATE TABLE mention (
  id TEXT PRIMARY KEY, occurrence_id TEXT, document_id TEXT, block_id TEXT, surface TEXT, mention_type TEXT,
  resolved_level TEXT, resolved_kind TEXT, resolved_id TEXT, method TEXT, confidence REAL
);
CREATE INDEX ix_mention_target ON mention(resolved_kind, resolved_id);

-- ── 그래프·검색 ─────────────────────────────────────
CREATE TABLE kg_edge (
  src_kind TEXT, src_id TEXT, rel TEXT, dst_kind TEXT, dst_id TEXT,
  source_tier TEXT, method TEXT, confidence REAL, evidence TEXT
);
CREATE INDEX ix_edge_src ON kg_edge(src_kind, src_id, rel);
CREATE INDEX ix_edge_dst ON kg_edge(dst_kind, dst_id, rel);
CREATE TABLE text_chunk (
  id TEXT PRIMARY KEY, document_id TEXT, page_type TEXT, section_path TEXT, text TEXT, entity_refs_json TEXT, url TEXT
);
CREATE VIRTUAL TABLE chunk_fts USING fts5(text, section_path, chunk_id UNINDEXED, tokenize='trigram');
CREATE TABLE vec_index (                -- 밀집 벡터(float32, L2 정규화). space: chunk | entity | image
  ref TEXT PRIMARY KEY, space TEXT, model TEXT, dim INTEGER, vec BLOB
);
CREATE TABLE entity_doc (               -- 엔티티 단위 검색 문서(이름·별칭·USP·스펙 요약·라벨)
  kind TEXT, id TEXT, name TEXT, text TEXT, PRIMARY KEY(kind, id)
);
CREATE VIRTUAL TABLE entity_fts USING fts5(name, text, kind UNINDEXED, id UNINDEXED, tokenize='trigram');
CREATE TABLE image_doc (                -- 이미지 단위 검색 문서(alt·캡션·섹션·맥락 엔티티·공간·업종 이름)
  asset_id TEXT PRIMARY KEY, text TEXT
);
CREATE VIRTUAL TABLE image_fts USING fts5(text, asset_id UNINDEXED, tokenize='trigram');

-- ── 템플릿·시나리오·메타 ──────────────────────────────
CREATE TABLE sheet_role (code TEXT PRIMARY KEY, name_ko TEXT, says_ko TEXT, section TEXT);
CREATE TABLE kb_meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE dr_metric (dr TEXT PRIMARY KEY, name TEXT, metric TEXT, value TEXT, status TEXT, note TEXT);
CREATE TABLE scenario_status (scenario TEXT PRIMARY KEY, name TEXT, status TEXT, reasons TEXT);
