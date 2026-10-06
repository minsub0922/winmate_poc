# 큐레이션 가이드: 사람이 고치는 곳

빌드는 결정적이다. 같은 `raw/` 입력과 같은 사전이면 같은 DB가 나온다. 사실(제품명·수치·문구)은 원문에서만 오고,
사람이 고치는 것은 "원문을 어떤 구조로 읽을지"를 정하는 사전과 규칙이다. 고친 뒤에는 다시 빌드한다.

```bash
bash build/run_all.sh        # 빌드 → 인덱스 → QA 프로브 → 시나리오 테스트 → 질의 예시 갱신
```

## 1. 무엇을 어디서 고치나

| 대상 | 파일 | 확인 방법 |
|---|---|---|
| 공간 라벨 → 공간 유형 | `build/curation.py` `LABEL_KO`(정확 일치), `KW_KO`(부분 일치) | `docs/BUILD_REPORT.md` "미매핑 공간 라벨", `SELECT * FROM space_label WHERE space_type_id IS NULL` |
| 새 공간 유형 | `seed/ontology/space_types.yaml` 또는 `curation.py` `EXTRA_SPACE_TYPES` | `space_type.origin` |
| 통칭 → 사이트 분류 별칭 | `curation.py` `CURATED_ALIASES` | BUILD_REPORT "미해소 업종 페이지 항목", `SELECT * FROM industry_section_item WHERE target_id IS NULL` |
| 하위 분류 표시명 | `curation.py` `SUBCAT_LABEL`(사이트 필터 라벨이 없을 때만 씀) | `SELECT * FROM category WHERE origin='site_api'` |
| 자동 역량 규칙 | `curation.py` `AUTO_RULES` | `SELECT capability_id, count(*) FROM provides GROUP BY 1`, `provides.evidence` |
| 임계값 규칙(휘도·IP·온도 등) | `seed/ontology/capability_rules.yaml` `rules[].params` | 아직 실행되지 않음(빈칸) |
| 공간 → 역량(hard/soft) | `seed/ontology/capability_rules.yaml` `requires` | `kg_edge` REQUIRES_* |
| Winmate 16 세그먼트 대응 | `seed/ontology/verticals.yaml` `winmate_segments` | `segment_mapping`, DR01 |
| 이미지 1차 등급 | `curation.py` `grade_hint_for`, `grade_from_alt` | `SELECT grade_hint, count(*) FROM image_asset GROUP BY 1` |
| 업종 페이지 파서 | `curation.py` `parse_industry_blocks` | `python build/query.py B1 kr_hotel` |
| 옛 경로·US 경로 대응 | `curation.py` `LEGACY_PATH_MAP`, `US_PATH_MAP` | `SELECT resolve_method, count(*) FROM industry_section_item GROUP BY 1` |
| 사례 사진 캡션 제외 문구 | `curation.py` `CAPTION_STOP` | `SELECT caption, count(*) FROM image_occurrence WHERE page_type='case_study' GROUP BY 1 ORDER BY 2 DESC` |
| 요구 문장 키워드(정규식) | `curation.py` `REQ_CAP_KEYWORDS` — '운영하는'의 '영하', '실외기'의 '실외' 같은 함정은 정규식으로 막는다 | `python build/query.py A1 "<문장>"` |

## 2. 검수 우선순위

1. `provides`(자동 역량) — 추천 결과를 직접 바꾼다. 근거 문장(`evidence`)을 보고 틀린 규칙은 `AUTO_RULES`에서 고친다. 승인한 규칙은 운영 DB에서 `status`를 바꾸는 대신 시드 규칙으로 옮겨 T4로 관리한다.
2. `requires` — 공간이 요구하는 역량. 지금은 시드 초안 14개뿐이라 S1 추천의 hard 조건 대부분은 요구 문장 키워드에서 온다.
3. 공간 라벨 사전 — 업종 페이지 장면의 공간 대응. 장면 제목에서 공간을 더 찾을 때(`space_method`에 title_keyword)는 오탐이 있을 수 있다.
4. `CURATED_ALIASES` — 업종 페이지의 링크 없는 항목(예: 객실 내부 기기 나열)과 사례 '사용 제품' 문자열 해소.
5. 이미지 등급 — A?C(미판정)가 가장 많다. VLM 파이프라인(05_IMAGE_PIPELINE)이 붙기 전까지는 alt 문장 규칙이 유일한 자동 판정이다.

## 3. 원칙

- 사실을 사전에 쓰지 않는다. 사전에는 "이 라벨은 이 공간 유형이다", "이 통칭은 이 사이트 분류다" 같은 대응만 쓴다.
- 대응이 애매하면 넣지 않는다. 미해소로 남는 편이 잘못된 연결보다 낫다(질의 결과에 `unresolved`·`확인 필요`로 드러난다).
- 사람이 승인한 결과는 시드 YAML로 옮겨 버전 관리한다. DB를 직접 고치면 다음 빌드에서 사라진다.
