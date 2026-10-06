# Build report

- 빌드 DB: `winmate_kb.sqlite` · 상품 수집 시각 2026-10-04T06:51:11.726Z
- 외래키 위반: {}
- 인덱스: lsa_char24_v2 dim=192

## 적재 건수

| 항목 | 건수 |
|---|---|
| blocks | 91212 |
| case_related_links | 304 |
| chunks | 24346 |
| deployments | 218 |
| documents | 1795 |
| families | 605 |
| image_assets | 10251 |
| image_occurrences | 15065 |
| industry_items | 555 |
| industry_sections | 469 |
| kg_edges | 36014 |
| kpi_claims | 294 |
| mentions | 32598 |
| models | 1067 |
| product_tags | 1215 |
| provides | 206 |
| spec_values | 47490 |
| value_props | 14699 |

## 데이터 요소(DR) 커버리지

| DR | 요소 | 지표 | 값 | 상태 | 메모 |
|---|---|---|---|---|---|
| DR01 | 업종·세그먼트 대응표 | FILL 없는 Winmate 세그먼트 / 전체 | 9/16 | partial | 모두 draft. 빈칸은 사람이 채워야 함 |
| DR02 | 업종별 공간 시퀀스 | 공간이 있는 장면을 가진 KR 업종 페이지 | 17/17 | ready | 업종 페이지 장면 순서 = 공간 시퀀스 |
| DR03 | 공간 속성 | 속성 있는 공간 유형 | 2/70 | blocked_by_source | 사이트에 공간 속성(시청거리·직사광 등) 구조 데이터 없음 |
| DR04 | UseCase·Need·Persona | 업종 페이지 장면(UseCase 대용) 수 | 428 | partial | 장면 제목·설명을 UseCase 로 사용. 페르소나는 소스에 없음 |
| DR05 | 공간 → 역량(requires) | requires 엣지(모두 draft) | 14 | partial | 시드 초안. 전문가 승인 필요 |
| DR06 | 역량 룰 | presence 자동 규칙 / 전체 규칙, provides 행 | 13/21, provides=206 | partial | 임계값 규칙(휘도·IP·온도)은 파라미터 빈칸으로 비활성 |
| DR07 | 제품 마스터 | 카테고리 / 제품군(카드) / 모델코드 | 200 / 605 / 1067 | ready |  |
| DR08 | 정규화 스펙 | 스펙 있는 모델 / 제품군, 정규 키 비율 | 929/1067 모델, 563/605 제품군, 정규화 18.8% | ready | 솔루션·서비스 상품 일부는 사이트에 스펙 없음 |
| DR09 | 판매 상태 | 사이트 목록 노출 = 판매 중으로 간주 | 605 제품군 | partial | 목록에서 빠진 단종 모델 정보는 사이트에 없음 |
| DR10 | 세대·후속 모델 | succession 엣지 | 0 | blocked_by_source | e-카탈로그·내부 자료 필요 |
| DR11 | 솔루션 | 솔루션 / 상품코드 연결 / 상세 페이지 연결 | 14 / 11 / 12 | partial | 호환 기기 목록(compat)은 소스에 구조화되어 있지 않음 |
| DR12 | 서비스 상품 | 서비스 수 | 5 | partial |  |
| DR13 | 구축사례 | 사례 수, 사용 항목 해소율, 사이트 '관련 제품' 링크 수 | 218, 71.0%, 304 | ready | 수량은 소스에 거의 없음. 대부분 카테고리 단위 해소 |
| DR14 | 성과 KPI | KPI 있는 사례 비율 | 64.2% | partial | 이전 세션 LLM 추출(T5), 원문 대조 필요 |
| DR15 | Value Prop 계층 | 레벨별 문구 수 | {"key_message": 6776, "proof_point": 6177, "tagline": 17, "usp": 1729} | ready | 전부 원문 그대로(verbatim) |
| DR16 | 강점·비교 축 | strength_point | 0 | blocked_by_source | 경쟁 비교 자료 필요 |
| DR17 | A등급 공간 배치 이미지 | A 힌트(공간 맥락 있음) / A 전체 / A?C 미판정 | 278 / 2140 / 3699 | partial | VLM 판정 전. 등급은 페이지 유형·파일명·alt 문장 규칙 |
| DR18 | C등급 단독컷 | 단독컷 있는 제품군 | 595/605 (98.3%) | ready |  |
| DR19 | UI·구성도 이미지 | D 힌트 이미지 | 631 | partial |  |
| DR20 | 사례 사진 | 사진 있는 사례 비율 | 90.8% | ready |  |
| DR21 | 배치 룰(active) | active placement_rule | 0 | blocked_by_source | 수량·크기 기준은 영업·기술 기준 필요 |
| DR22 | 공식 권장(사이트) | 공간 추천 / 업종 추천 엣지 | 252 / 365 | ready | e-카탈로그 권장은 별도 소스(이번 빌드 범위 밖) |
| DR23 | 과거 제안서 구조 | proposal_doc | 0 | blocked_by_source | 제안서 파일 필요 |
| DR24 | Winmate 템플릿 메타 | sheet_role 수 | 26 | partial | data_shape 빈칸 |
| DR25 | 근거 원문 인덱스 | 청크 / 엔티티 연결 비율 / 벡터 | 24346 / 40.4% / 35775 | ready | 벡터는 LSA(문자 n-gram) — 신경망 임베딩은 모델 다운로드 차단으로 보류 |
| DR26 | 언급 해소 | 언급 수 / 저신뢰 비율 / 업종 항목 미해소 | 32598 / 13.4% / 122/555 | partial |  |

## 시나리오 상태

| 시나리오 | 이름 | 상태 | 사유 |
|---|---|---|---|
| S1 | 고객 요구사항 → 필요 제품 추론 | partial | DR05:partial; DR06:partial; DR26:partial; probes 4/4 pass |
| S2 | 업종·공간 → 솔루션 시나리오·제품 배치 | partial | DR17:partial; probes 3/3 pass |
| S3 | 업종·공간 → 제품 리스트 | partial | DR21:blocked_by_source; probes 3/3 pass |
| S4 | Value Prop 추출 | ready | probes 2/2 pass |
| S5 | 관련 이미지 활용 | partial | DR17:partial; DR19:partial; probes 3/3 pass |
| S6 | 제품·솔루션 상세(흩어진 정보 통합) | partial | DR11:partial; DR26:partial; probes 2/2 pass |
| S7 | 스펙 비교·요구 스펙 대응표 | partial | DR10:blocked_by_source; probes 1/1 pass |
| S8 | 유사 사례·성과 수치 | partial | DR14:partial; probes 1/1 pass |
| S9 | 업종 판별·인사이트 | partial | DR01:partial; probes 3/3 pass |
| S10 | 솔루션 구성·BOM | blocked_by_source | DR11:partial; DR12:partial |
| S11 | 공간 배치·수량 산정 | blocked_by_source | DR03:blocked_by_source; DR21:blocked_by_source |
| S12 | 기존 제안서 활용 | blocked_by_source | DR23:blocked_by_source; DR24:partial |
| S13 | 자유 질문 RAG | ready | probes 1/1 pass; LLM RAG 는 이번 범위 밖(검색·근거 레이어만 구축) |
| S14 | 변경 영향 | blocked_by_source | DR10:blocked_by_source; DR23:blocked_by_source |
| S15 | 화면별 자동 판단 | partial | DR05:partial; DR06:partial |

## 시나리오 프로브

| 시나리오 | 프로브 | 결과 | 상세 |
|---|---|---|---|
| S1 | S1 '호텔 객실에 24시간 운영하는 디스플레이가 필요해' | pass | 후보 8개, hard 미충족 0, 근거 없음 0, 판단 check ['LOW_TIER'] |
| S1 | S1 '호텔 객실 TV를 통합 관리하고 로비에 대형 사이니지를 설치하고 싶어' | pass | 후보 11개, hard 미충족 0, 근거 없음 0, 판단 check ['LOW_TIER'] |
| S1 | S1 '매장 입구 쇼윈도에 햇빛에서도 잘 보이는 사이니지' | pass | 후보 5개, hard 미충족 0, 근거 없음 0, 판단 check ['LOW_MARGIN', 'LOW_TIER'] |
| S1 | 실외 요구 → 실외 대응 없는 모델 제외 | pass | 후보 3: 실외용 스마트 사이니지, 창문형(단면형) 스마트 사이니지, 창문형(양면형) 스마트 사이니지 |
| S2 | S2 kr_public_agency 장면 | pass | 장면 9, 공간 있는 장면 3 |
| S2 | S2 kr_military 장면 | pass | 장면 7, 공간 있는 장면 5 |
| S2 | S2 kr_manufacturing 장면 | pass | 장면 16, 공간 있는 장면 16 |
| S3 | S3 공간 sales_floor 제품 | pass | 제품군 15, 솔루션 1 |
| S3 | S3 공간 teachers_office 제품 | pass | 제품군 15, 솔루션 0 |
| S3 | S3 공간 classroom 제품 | pass | 제품군 15, 솔루션 0 |
| S4 | 메시지 문장 = 출처 블록 원문(200건 표본) | pass | 불일치 0/200 |
| S4 | key_message → proof_point 계층 | pass | 부모-자식 쌍 5993 |
| S5 | G1 공간 residential_living | pass | 20장, 폴백 None |
| S5 | G1 공간 cold_storage | pass | 20장, 폴백 None |
| S5 | G1 공간 open_office | pass | 20장, 폴백 None |
| S6 | 제품군 fam_G000183618 통합 보기 | pass | 언급 페이지 유형 ['case_study', 'industry', 'landing', 'pdp', 'service', 'solution'], 모델 1, 스펙 0 |
| S6 | 솔루션 sol_smartthings_pro 통합 보기 | pass | in ['ABOUT', 'DEPICTS_PROBABLE', 'FEATURED_BY_SITE', 'MENTIONS', 'RECOMMENDED_BY_SITE'], out ['DESCRIBED_BY'] |
| S7 | C6 pass/fail/unknown | pass | [{"attr": "brightness_nit", "required": ">= 500", "actual": "300 cd/㎡", "verdict": "fail", "source": "occ_doc_spec_G000183961:7", "attr_name": "밝기 (Typical)"}, {"attr": "pixel_pitch_mm", "required": " |
| S8 | D1 kr_retail_fnb | pass | 10건, URL 없는 사례 형식 ['pdf'] |
| S9 | A2 '병원 입원실 환자용 태블릿' | pass | top2 ['kr_hospital', 'kr_medical'], ask=False |
| S9 | A2 '학교 교실 전자칠판' | pass | top2 ['kr_school', 'kr_education'], ask=False |
| S9 | A2 '호텔 객실 TV' | pass | top2 ['kr_hotel', 'kr_military'], ask=False |
| S13 | 하이브리드 검색 근거 URL | pass | 10건 |

## 미매핑 공간 라벨(큐레이션 대상)

없음

## 미해소 업종 페이지 항목(상위 40)

how(4), 스캐닝 솔루션(3), interactive displays(3), Police(3), 4K UHD displays(3), Standalone digital signage Standalone digital signage Professional image quality and commercial reliability. Professional image quality and commercial reliability. Learn more(2), Situational Awareness(2), Register now(2), Interactive and touch displays Interactive and touch displays Simple, effective touch interactions for any environment. Simple, effective touch interactions for any environment. Learn more(2), Interactive & touch displays(2), Health and human performance(2), Digital signage accessories Digital signage accessories Mounts, stands, receivers and more. Mounts, stands, receivers and more. Learn more(2), DeX in Vehicle(2), Connected Worker(2), Connected Command Centers(2), Buy now(2), AI 스피커(2), 4K UHD displays 4K UHD displays Head-turning visual impact and fine detail. Head-turning visual impact and fine detail. Learn more(2), 핸드폰을 통해 전기 요금 관리 및 가전 사용 TIP 제공(1), 통합 관리 솔루션(1), 출력 보안 솔루션(1), 제품 자세히 보기(1), 인체 무해한 조명(1), 삼성 녹스 솔루션을 통해 재탄생한 전용폰!항공사 맞춤 전용폰은 이용하는 고객에게 실질적인 편의를 줄 수 있는환경을 제공합니다.(1), 빛 반사 방지 패널로 24시간 선명하게!(1), 블루투스 스피커(1), 국내 최대 PAC 공청 KIT넓은 공간도 빠르게 청정하는 공기질 케어!(1), retail solutions(1), out more(1), digital signage(1), digital displays(1), business offers(1), Why shop Samsung(1), Volume pricing up to 30% off per device Get exclusive volume pricing up to 30% off per device when you buy in bulk with a Samsung Business Account. Plus, get free shipping and limited time instant sav(1), Volume pricing(1), Virtual Care(1), Upscale your display Engage customers and vividly display business messaging. Shop now(1), UHD displays(1), Trusted & secure(1), Terms of Sale(1)

## 빌드 메모

- 무효 필터 제외: cat_smartphones 'wireless-charging' (8개 = 목록 전체)
- 무효 필터 제외: cat_cooling-single '4-way_multi' (23개 = 목록 전체)
- 무효 필터 제외: cat_cooling-single 'general-housing' (23개 = 목록 전체)
- 무효 필터 제외: cat_cooling-for-residential 'dvm-s-eco' (23개 = 목록 전체)
- 무효 필터 제외: cat_ventilations 'erv' (3개 = 목록 전체)
- 무효 필터 제외: cat_smart-signage 'built-in-wifi' (37개 = 목록 전체)
- 무효 필터 제외: cat_smart-signage 'flip' (37개 = 목록 전체)
- 무효 필터 제외: cat_monitors 'over-123cm' (47개 = 목록 전체)
- 무효 필터 제외: cat_washing-machines 'black' (12개 = 목록 전체)
- 무효 필터 제외: cat_washing-machines 'cleansing' (12개 = 목록 전체)
- 무효 필터 제외: cat_washing-machines 'grande' (12개 = 목록 전체)
- 무효 필터 제외: cat_washing-machines '18-20kg' (12개 = 목록 전체)
- 무효 필터 제외: cat_washing-machines 'all-in-one-control' (12개 = 목록 전체)
- 무효 필터 제외: cat_washing-machines '10kg-under' (12개 = 목록 전체)
- 무효 필터 제외: cat_dryers 'door' (10개 = 목록 전체)
- 무효 필터 제외: cat_dryers '23kg-over' (10개 = 목록 전체)
- 무효 필터 제외: cat_dryers '10-15kg' (10개 = 목록 전체)
- 무효 필터 제외: cat_dryers 'black' (10개 = 목록 전체)
- 무효 필터 제외: cat_dryers 'cleansing' (10개 = 목록 전체)
- 무효 필터 제외: cat_dryers 'all-in-one-control' (10개 = 목록 전체)
- 무효 필터 제외: cat_multifunction-printers-supplies 'waste-toner-container-mono' (15개 = 목록 전체)
- 무효 필터 제외: cat_qooker 'premium-housing' (5개 = 목록 전체)
- 무효 필터 제외: cat_qooker 'apartment' (5개 = 목록 전체)
- 무효 필터 제외: cat_kimchi-refrigerators 'apartment' (16개 = 목록 전체)
- 무효 필터 제외: cat_dvms '220v-1-phase' (10개 = 목록 전체)
- 무효 필터 제외: cat_dvms '4-way' (10개 = 목록 전체)
- 무효 필터 제외: cat_dvms 'cassette' (10개 = 목록 전체)
- 무효 필터 제외: cat_electric-range 'apartment' (6개 = 목록 전체)
- 무효 필터 제외: cat_led-lights 'sports' (14개 = 목록 전체)
- 무효 필터 제외: cat_led-lights 'slim-edge' (14개 = 목록 전체)
- 무효 필터 제외: cat_led-lights 'biorhythms' (14개 = 목록 전체)
- 무효 필터 제외: cat_led-lights 'iot' (14개 = 목록 전체)
