# 시나리오 테스트 결과

- 테스트 41건 · 통과 41 · 실패 0
- 실행: `python tests/test_scenarios.py` (LLM 없이 결정적 질의 패턴만 사용)

| 시나리오 | 테스트 | 결과 | 상세 | 판단 |
|---|---|---|---|---|
| S1 | 요구사항: 호텔 객실 TV를 통합 관리하고 싶어 | pass | 후보 3, 상위: 호텔 TV CU700 시리즈 | check ['LOW_TIER'] |
| S1 | 요구사항: 매장 입구 쇼윈도에 햇빛에서도 잘 보이는 사이니지 | pass | 후보 1, 상위: 실외용 스마트 사이니지 | check ['LOW_MARGIN', 'LOW_TIER'] |
| S1 | 요구사항: 주차장 입구 옥외에 설치할 실외 사이니지 | pass | 후보 1, 상위: 실외용 스마트 사이니지 | ask ['AMBIGUOUS_INDUSTRY', 'LOW_MARGIN', 'LOW_TIER'] |
| S1 | 요구사항: 학교 교실에 판서가 되는 전자칠판 | pass | 후보 8, 상위: Flip Pro 전자칠판 | check ['LOW_MARGIN', 'LOW_TIER'] |
| S1 | 요구사항: 물류센터 현장 작업자가 쓸 내구성 좋은 태블릿 | pass | 후보 2, 상위: 갤럭시 탭 액티브5 프로 5G | check ['LOW_TIER'] |
| S1 | 요구사항: 사무실 회의실에 직바람 없는 무풍 냉방 | pass | 후보 8, 상위: 무풍 1Way  | check ['LOW_MARGIN', 'LOW_TIER'] |
| S1 | 요구사항: 병원 입원실 환자용 태블릿 | pass | 후보 8, 상위: 갤럭시 탭 액티브5 프로 5G | check ['LOW_MARGIN', 'LOW_TIER'] |
| S1 | 요구사항: 호텔 로비에 대형 비디오월 | pass | 후보 5, 상위: 비디오월  Razor 베젤 0.88mm 시리즈 | check ['LOW_TIER'] |
| S2 | 업종 장면: kr_hotel | pass | 장면 14, 공간 ['banquet_hall', 'fitness', 'front_desk', 'guest_room', 'lobby', 'lounge'], 누락 [], 빈 장면 [], 메시지 없는 장면 [] | check ['LOW_TIER'] |
| S2 | 업종 장면: kr_hospital | pass | 장면 15, 공간 ['exam_room', 'hospital_reception', 'lobby', 'meeting_room', 'nurse_station', 'operating_room', 'pantry_lounge', 'patient_room', 'waiting_area'], 누락 [], 빈 장면 [], 메시지 없는 장면 [] | check ['LOW_TIER'] |
| S2 | 업종 장면: kr_school | pass | 장면 12, 공간 ['cafeteria', 'classroom', 'fitness', 'teachers_office'], 누락 [], 빈 장면 [], 메시지 없는 장면 [] | check ['LOW_TIER'] |
| S2 | 업종 장면: kr_manufacturing | pass | 장면 16, 공간 ['factory_floor', 'research_lab', 'sales_floor', 'warehouse'], 누락 [], 빈 장면 [], 메시지 없는 장면 [] | check ['LOW_TIER'] |
| S2 | 업종 장면: kr_fnb | pass | 장면 4, 공간 ['back_of_house', 'dining_hall', 'entrance', 'order_counter', 'sales_floor'], 누락 [], 빈 장면 [], 메시지 없는 장면 [] | check ['LOW_TIER'] |
| S3 | 공간별 제품: guest_room @ kr_hotel | pass | 제품군 40, 솔루션 ['스마트싱스 프로페셔널 솔루션', '링크 클라우드 솔루션', 'b.IoT 솔루션'], 누락 카테고리 [] | check ['LOW_MARGIN'] |
| S3 | 공간별 제품: classroom @ kr_school | pass | 제품군 40, 솔루션 ['에어컨 세척서비스', '사이니지 콘텐츠관리 Magic INFO'], 누락 카테고리 [] | check ['LOW_MARGIN'] |
| S3 | 공간별 제품: meeting_room @ kr_office | pass | 제품군 40, 솔루션 ['b.IoT 솔루션', '에어컨 세척서비스'], 누락 카테고리 [] | check ['LOW_MARGIN'] |
| S4 | 제품 메시지 계층(Flip Pro) | pass | key 11, usp 3, 원문 불일치 [] | auto  |
| S4 | 업종 메시지 계층(호텔) | pass | tagline 1, key 25 | auto  |
| S4 | 테마 검색: 에너지 절감 | pass | 상위 10 중 '에너지' 포함 10 | auto  |
| S4 | 컨텍스트→메시지: 호텔·객실·비즈니스호텔 체인·요구사항(모두 입력) | pass | 헤드라인 1, 핵심 12, 제품 상위3 호텔 TV True, 고객 일치 사례 True, 원문 불일치 [] | check ['LOW_TIER'] |
| S4 | 컨텍스트→메시지: 요구사항 문장만(업종·공간·제품 추론) | pass | 업종 {'id': 'kr_hotel', 'name': '호텔', 'from': 'inferred'}, 공간 ['guest_room', 'lobby'], 제품 ['cat_tvs', 'cat_smart-signage__videowall'] | check ['LOW_TIER'] |
| S4 | 컨텍스트→메시지: 제품만(비디오월 분류 + 로비) | pass | 제품 상위 ['비디오월  Razor 베젤 0.88mm 시리즈', '비디오월 Extreme 베젤 1.74mm 시리즈', '비디오월 Ultra 베젤 3.5 mm 시리즈'] | check ['LOW_TIER'] |
| S4 | 컨텍스트→메시지: 빈 컨텍스트 → 질문 | pass | hint ask | ask ['ASK'] |
| S5 | 공간×카테고리 배치 이미지: 객실 × 호텔TV | pass | 4장, 수준 space+category | auto  |
| S5 | 공간 이미지: 회의실 | pass | 20장, 등급 ['A', 'A?C', 'D'], 폴백 None | auto  |
| S5 | 공간 이미지 폴백: 수술실 × 공기청정기 | pass | 수준 category_context, 폴백 category_context | auto ['FALLBACK_USED'] |
| S5 | 제품 설치 사진: 호텔TV | pass | 113장, 사례 경유 7 | check ['LOW_TIER'] |
| S5 | 이미지 검색: 카페 천장 시스템에어컨 | pass | 상위 5 중 관련 alt 3 이상 | auto  |
| S6 | 솔루션 통합 보기: 링크 클라우드 | pass | out ['DESCRIBED_BY', 'SOLD_AS'], in ['ABOUT', 'DEPICTS_PROBABLE', 'FEATURED_BY_SITE', 'MENTIONS', 'RECOMMENDED_BY_SITE', 'USES'], 언급 문서 10 | auto  |
| S6 | 제품군 통합 보기: 호텔TV | pass | 모델 5, 핵심 스펙 12, 메시지 29, 역량 ['cap_hospitality_tv_mgmt'] | auto  |
| S7 | 요구 스펙 대응표(고휘도 사이니지) | pass | [["brightness_nit", "4,000 nit", "pass"], ["operation_hours", "24/7", "pass"], ["pixel_pitch_mm", "0.53 x 0.53 mm", "pass"], ["capacity_l", null, "unknown"]] | auto  |
| S8 | 유사 사례: 호텔 객실 TV | pass | 상위 ['롯데 시그니엘 서울 - 삼성 호텔 T', '부티크 호텔 XYM - 삼성 호텔 T', '크라운 파크 호텔 서울 - 삼성 호텔'] | check ['LOW_MARGIN', 'LOW_TIER'] |
| S8 | 성과 KPI: 호텔TV 사용 사례 | pass | KPI 6 | check ['LOW_TIER'] |
| S8 | 사례 통계: 교육 | pass | 사례 16 | check ['LOW_TIER'] |
| S9 | 업종 판별 정확도(10문장) | pass | top-2 정답 10/10 |   |
| S10 | 업종 추천 솔루션: 호텔 | pass | 추천 ['링크 클라우드 솔루션', 'b.IoT 솔루션'] | auto  |
| S13 | 하이브리드 검색: 객실 TV 원격 관리 | pass | 상위 3에 '객실' · 상위 5 포괄도 [1.0, 1.0, 1.0, 1.0, 1.0] | auto  |
| S13 | 하이브리드 검색: 전자칠판 필기 공유 | pass | 상위 3에 '필기' · 상위 5 포괄도 [1.0, 1.0, 1.0, 0.67, 0.67] | auto  |
| S13 | 하이브리드 검색: 무풍 냉방 직바람 | pass | 상위 3에 '무풍' · 상위 5 포괄도 [1.0, 1.0, 1.0, 1.0, 1.0] | auto  |
| S13 | 하이브리드 검색: 실외 사이니지 밝기 | pass | 상위 3에 '밝기' · 상위 5 포괄도 [1.0, 1.0, 1.0, 1.0, 1.0] | auto  |
| S13 | 하이브리드 검색: 급식실 영양 정보 사이니지 | pass | 상위 3에 '급식' · 상위 5 포괄도 [0.75, 0.5, 0.25, 0.5, 0.5] | auto  |

## 결과 예시

### S1 · 요구사항: 호텔 객실 TV를 통합 관리하고 싶어 — pass

업종 판별: [('kr_hotel', 1.0), ('kr_hospital', 0.086)] · 판단 check ['LOW_TIER']
공간 객실(guest_room) · 카테고리 None · hard ['cap_hospitality_tv_mgmt'] · soft []
  - 호텔 TV CU700 시리즈 [HG43CU700NFXKR] 0.856 · 충족 객실 TV 통합 관리: 스펙 '삼성 LYNK™ Cloud' = 있음 / 사이트 추천: 호텔TV (space) / 사이트 추천: 호텔TV (space)
  - 호텔 TV HU7000F 시리즈 [HG43U700FNFXKR] 0.856 · 충족 객실 TV 통합 관리: 스펙 '삼성 LYNK™ Cloud' = 있음 / 사이트 추천: 호텔TV (space) / 사이트 추천: 호텔TV (space)
  - 호텔 TV HU8000F 시리즈 [HG43U800FNFXKR] 0.856 · 충족 객실 TV 통합 관리: 스펙 '삼성 LYNK™ Cloud' = 있음 / 사이트 추천: 호텔TV (space) / 사이트 추천: 호텔TV (space)
  솔루션: 스마트싱스 프로페셔널 솔루션(space), 링크 클라우드 솔루션(space), b.IoT 솔루션(vertical)

### S1 · 요구사항: 매장 입구 쇼윈도에 햇빛에서도 잘 보이는 사이니지 — pass

업종 판별: [('kr_fnb', 1.0), ('kr_retail_fnb', 1.0)] · 판단 check ['LOW_MARGIN', 'LOW_TIER']
공간 쇼윈도·창가(storefront_window) · 카테고리 사이니지 · hard ['cap_sunlight_readable'] · soft []
  - 실외용 스마트 사이니지 [LH75OHAEBGBXKR] 1.0 · 충족 직사광 가독성: 사이트 목록 필터 '3000nits-over' / 사이트 추천: 스마트 LCD 사이니지 > 실외용 (space) / 사이트 추천: 스마트 LCD 사이니지 > 실외용 (space)
  솔루션: 스마트싱스 프로페셔널 솔루션(vertical), 사이니지 콘텐츠관리 Magic INFO(vertical), 에어컨 세척서비스(vertical)
공간 매장 플로어(sales_floor) · 카테고리 사이니지 · hard ['cap_sunlight_readable'] · soft []
  - 실외용 스마트 사이니지 [LH75OHAEBGBXKR] 1.0 · 충족 직사광 가독성: 사이트 목록 필터 '3000nits-over' / 사이트 추천: 스마트 LCD 사이니지 (space) / 사이트 추천: 사이니지 (space)
  - 창문형(단면형) 스마트 사이니지 [LH46OMBEBGBXKR] 0.917 · 충족 직사광 가독성: 사이트 목록 필터 '3000nits-over' / 사이트 추천: 스마트 LCD 사이니지 (space) / 사이트 추천: 사이니지 (space)
  - 창문형(양면형) 스마트 사이니지 [LH55OMNDSGBXKR] 0.917 · 충족 직사광 가독성: 사이트 목록 필터 '3000nits-over' / 사이트 추천: 스마트 LCD 사이니지 (space) / 사이트 추천: 사이니지 (space)
  솔루션: 스마트싱스 프로페셔널 솔루션(space), 사이니지 콘텐츠관리 Magic INFO(vertical), 에어컨 세척서비스(vertical)
공간 입구(entrance) · 카테고리 사이니지 · hard ['cap_sunlight_readable'] · soft []
  - 실외용 스마트 사이니지 [LH75OHAEBGBXKR] 1.0 · 충족 직사광 가독성: 사이트 목록 필터 '3000nits-over' / 사이트 추천: 스마트 LCD 사이니지 > 실외용 (space) / 사이트 추천: 스마트 LCD 사이니지 > 실외용 (space)
  솔루션: 스마트싱스 프로페셔널 솔루션(vertical), 사이니지 콘텐츠관리 Magic INFO(vertical), 에어컨 세척서비스(vertical)

### S1 · 요구사항: 주차장 입구 옥외에 설치할 실외 사이니지 — pass

업종 판별: [('kr_academy', 1.0), ('kr_fnb', 1.0)] · 판단 ask ['AMBIGUOUS_INDUSTRY', 'LOW_MARGIN', 'LOW_TIER']
공간 주차장(parking) · 카테고리 None · hard ['cap_weatherproof'] · soft []
  - 실외용 스마트 사이니지 [LH75OHAEBGBXKR] 0.6 · 충족 방수·방진: 사이트 목록 필터 'outdoor' / 선례 점수 16.8 / 요구 문장 유사도 0.52
  - 창문형(단면형) 스마트 사이니지 [LH46OMBEBGBXKR] 0.6 · 충족 방수·방진: 사이트 목록 필터 'outdoor-dual' / 선례 점수 12.4 / 요구 문장 유사도 0.62
  - 창문형(양면형) 스마트 사이니지 [LH55OMNDSGBXKR] 0.6 · 충족 방수·방진: 사이트 목록 필터 'outdoor-dual' / 선례 점수 12.4 / 요구 문장 유사도 0.59
  솔루션: 사이니지 콘텐츠관리 Magic INFO(vertical), 에어컨 세척서비스(vertical)
공간 외벽·옥외(outdoor_facade) · 카테고리 사이니지 · hard ['cap_weatherproof', 'cap_sunlight_readable'] · soft ['cap_wide_temp_operation']
  - 실외용 스마트 사이니지 [LH75OHAEBGBXKR] 1.0 · 충족 방수·방진: 사이트 목록 필터 'outdoor' / 충족 직사광 가독성: 사이트 목록 필터 '3000nits-over' / 사이트 추천: 스마트 LCD 사이니지 > 실외용 (space)
  솔루션: 사이니지 콘텐츠관리 Magic INFO(vertical), 에어컨 세척서비스(vertical)
공간 입구(entrance) · 카테고리 사이니지 · hard ['cap_weatherproof'] · soft []
  - 실외용 스마트 사이니지 [LH75OHAEBGBXKR] 1.0 · 충족 방수·방진: 사이트 목록 필터 'outdoor' / 사이트 추천: 스마트 LCD 사이니지 > 실외용 (space) / 사이트 추천: 스마트 LCD 사이니지 > 실외용 (space)
  솔루션: 사이니지 콘텐츠관리 Magic INFO(vertical), 에어컨 세척서비스(vertical)

### S1 · 요구사항: 학교 교실에 판서가 되는 전자칠판 — pass

업종 판별: [('kr_school', 1.0), ('kr_education', 1.0)] · 판단 check ['LOW_MARGIN', 'LOW_TIER']
공간 교실·강의실(classroom) · 카테고리 스마트 LCD 사이니지 > 전자칠판 · hard ['cap_touch_interactive'] · soft []
  - Flip Pro 전자칠판 [LH85WMBWLGCXKR] 1.0 · 충족 터치 상호작용: 사이트 목록 필터 'electronic-board' / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space)
  - Flip Pro 전자칠판 [LH55WMFWBGCXKR] 1.0 · 충족 터치 상호작용: 사이트 목록 필터 'electronic-board' / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space)
  - 안드로이드 전자칠판 WAF [LH65WAFWLGCXKR] 1.0 · 충족 터치 상호작용: 사이트 목록 필터 'electronic-board' / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space)
  솔루션: 에어컨 세척서비스(vertical), 사이니지 콘텐츠관리 Magic INFO(vertical)

### S1 · 요구사항: 물류센터 현장 작업자가 쓸 내구성 좋은 태블릿 — pass

업종 판별: [('kr_manufacturing', 1.0), ('kr_transport', 0.426)] · 판단 check ['LOW_TIER']
공간 물류 창고(warehouse) · 카테고리 갤럭시 탭 · hard ['cap_rugged_mobile'] · soft []
  - 갤럭시 탭 액티브5 프로 5G [SM-X356NZGAKOO] 0.968 · 충족 현장용 내구 모바일: 사이트 분류 '갤럭시 탭 액티브' / 사이트 추천: 갤럭시 탭 (vertical) / 사이트 추천: 갤럭시 탭 > 갤럭시 탭 액티브 (space)
  - 갤럭시 탭 액티브5 (5G) [SM-X306NZGAKOO] 0.967 · 충족 현장용 내구 모바일: 사이트 분류 '갤럭시 탭 액티브' / 사이트 추천: 갤럭시 탭 (vertical) / 사이트 추천: 갤럭시 탭 > 갤럭시 탭 액티브 (space)
  솔루션: b.IoT 솔루션(vertical), 에어컨 세척서비스(vertical)

### S1 · 요구사항: 사무실 회의실에 직바람 없는 무풍 냉방 — pass

업종 판별: [('kr_office', 1.0), ('kr_construction', 1.0)] · 판단 check ['LOW_MARGIN', 'LOW_TIER']
공간 회의실(meeting_room) · 카테고리 None · hard ['cap_draft_free_cooling'] · soft ['cap_touch_interactive']
  - 무풍 1Way  [AG026RN1DBH1] 0.9 · 충족 직바람 없는 냉방: 문구 '…무풍 1Way 실내 공간을 더욱 넓게 사용 스탠드형…' / 사이트 추천: 중앙공조 (vertical) / 사이트 추천: 중앙공조 (vertical)
  - 무풍 1Way (Wi-Fi 내장형) [AG026BN1DBH1] 0.9 · 충족 직바람 없는 냉방: 문구 '…무풍 1Way (Wi-Fi 내장형) 실내 공간을 더욱…' / 사이트 추천: 중앙공조 (vertical) / 사이트 추천: 중앙공조 (vertical)
  - 무풍 4Way [AG060AN4DBH1] 0.9 · 충족 직바람 없는 냉방: 문구 '…무풍 4Way 직바람 없이 시원하게 무풍냉방 쾌속냉방…' / 사이트 추천: 중앙공조 (vertical) / 사이트 추천: 중앙공조 (vertical)
  솔루션: b.IoT 솔루션(vertical), 에어컨 세척서비스(vertical)
공간 오픈 오피스(open_office) · 카테고리 None · hard ['cap_draft_free_cooling'] · soft []
  - 무풍 1Way  [AG026RN1DBH1] 0.9 · 충족 직바람 없는 냉방: 문구 '…무풍 1Way 실내 공간을 더욱 넓게 사용 스탠드형…' / 사이트 추천: 중앙공조 (vertical) / 사이트 추천: 중앙공조 (vertical)
  - 무풍 1Way (Wi-Fi 내장형) [AG026BN1DBH1] 0.9 · 충족 직바람 없는 냉방: 문구 '…무풍 1Way (Wi-Fi 내장형) 실내 공간을 더욱…' / 사이트 추천: 중앙공조 (vertical) / 사이트 추천: 중앙공조 (vertical)
  - 무풍 4Way [AG060AN4DBH1] 0.9 · 충족 직바람 없는 냉방: 문구 '…무풍 4Way 직바람 없이 시원하게 무풍냉방 쾌속냉방…' / 사이트 추천: 중앙공조 (vertical) / 사이트 추천: 중앙공조 (vertical)
  솔루션: b.IoT 솔루션(vertical), 에어컨 세척서비스(vertical)

### S1 · 요구사항: 병원 입원실 환자용 태블릿 — pass

업종 판별: [('kr_hospital', 1.0), ('kr_medical', 1.0)] · 판단 check ['LOW_MARGIN', 'LOW_TIER']
공간 병실(patient_room) · 카테고리 갤럭시 탭 · hard [] · soft []
  - 갤럭시 탭 액티브5 프로 5G [SM-X356NZGAKOO] 0.749 · 사이트 추천: 갤럭시 탭 (space) / 사이트 추천: 갤럭시 탭 (space) / 선례 점수 8.2
  - 갤럭시 탭 액티브5 (5G) [SM-X306NZGAKOO] 0.742 · 사이트 추천: 갤럭시 탭 (space) / 사이트 추천: 갤럭시 탭 (space) / 선례 점수 8.2
  - 갤럭시 탭 S10+ 5G [SM-X826NZSAKOO] 0.718 · 사이트 추천: 갤럭시 탭 (space) / 사이트 추천: 갤럭시 탭 (space) / 선례 점수 8.2
  솔루션: b.IoT 솔루션(vertical), 시스템에어컨 제어 솔루션 DMS 2.5(vertical), 사이니지 콘텐츠관리 Magic INFO(vertical), 에어컨 세척서비스(vertical)

### S1 · 요구사항: 호텔 로비에 대형 비디오월 — pass

업종 판별: [('kr_hotel', 1.0), ('kr_home', 0.142)] · 판단 check ['LOW_TIER']
공간 로비(lobby) · 카테고리 스마트 LCD 사이니지 > 비디오월 · hard ['cap_bezel_less_tiling'] · soft ['cap_remote_content_mgmt']
  - 비디오월  Razor 베젤 0.88mm 시리즈 [LH55VHCRBGBXKR] 1.0 · 충족 이음매 최소 타일링: 사이트 목록 필터 'videowall' / 충족(soft) 원격 콘텐츠 관리 / 사이트 추천: 스마트 LCD 사이니지 > 비디오월 (space)
  - 비디오월 Extreme 베젤 1.74mm 시리즈 [LH55VHCEBGBXKR] 1.0 · 충족 이음매 최소 타일링: 사이트 목록 필터 'videowall' / 사이트 추천: 스마트 LCD 사이니지 > 비디오월 (space) / 사이트 추천: 스마트 LCD 사이니지 > 비디오월 (space)
  - 비디오월 Extreme 베젤 1.74mm 시리즈 [LH55VMCEBGBXKR] 1.0 · 충족 이음매 최소 타일링: 사이트 목록 필터 'videowall' / 사이트 추천: 스마트 LCD 사이니지 > 비디오월 (space) / 사이트 추천: 스마트 LCD 사이니지 > 비디오월 (space)
  솔루션: 스마트싱스 프로페셔널 솔루션(vertical), 링크 클라우드 솔루션(vertical), b.IoT 솔루션(vertical)

### S2 · 업종 장면: kr_hotel — pass

히어로: ['미래형 호텔을 완성하다']
- [객실] 새로운 경험 SMART 객실 솔루션 · 객실 자동화 서비스→스마트싱스 프로페셔널 솔루션, 객실 내 공기 질을 자동파악 에어케어 기기를 제어하는 에어모니터 플러스→주거용 실내외기 > 기타 · 이미지 4
- [객실] 투숙객 맞춤 콘텐츠 제공 · 링크 클라우드 솔루션→링크 클라우드 솔루션 · 이미지 4
- [객실] 집에서 보던 OTT 콘텐츠를 객실 TV로 · 호텔 맞춤형 TV→호텔TV · 이미지 4
- [객실] 편안하고 안락한 SMART 객실 공간 · 시스템 청정환기→환기 솔루션, IoT LED 조명→LED 조명, 무풍 시스템에어컨→시스템에어컨 실내기, 호텔 TV→호텔TV · 이미지 4
- [객실] 넷플릭스 시청 가능한 호텔 TV · 호텔 맞춤형 TV→호텔TV · 이미지 4
- [객실] 투숙객 전용 모바일 도우미 · 갤럭시 탭→갤럭시 탭 · 이미지 4
- [객실] 프리미엄 의류 청정 서비스 · BESPOKE 에어드레서→에어드레서 · 이미지 4
- [프런트·리셉션, 라운지, 로비] 투숙 만족도를 높이는 로비 공간 · The Frame→TV, 시스템에어컨 360→시스템에어컨 실내기 · 이미지 3
유사 사례: ['스페이스 엄 ∙ 에버랜드 사파리월드 – 삼성 ', '롯데시네마 광음LED - 삼성 오닉스', '골프존클라우드 – 갤럭시 워치FE 골프 패키지']

### S2 · 업종 장면: kr_hospital — pass

히어로: ['Smart 병원을 완성하다']
- [로비] 환자를 위한 의료 공간 혁신 · 시스템에어컨→시스템에어컨·공조, LED 조명→LED 조명, LED 사이니지→스마트 LED 사이니지, 스마트 사이니지→스마트 LCD 사이니지 · 이미지 4
- [병원 접수·수납] 환자의 편의를 돕는 모바일 전자 서명 · 전자 서명 태블릿→갤럭시 탭 · 이미지 1
- [대기 공간] 대기 중인 고객을 위한 진료 대기실 · 스마트 사이니지→스마트 LCD 사이니지 · 이미지 2
- [병실] 환자를 위한 세심함이 느껴지는 입원실 · 환기시스템→환기 솔루션, 무풍 시스템 에어컨→시스템에어컨 실내기, LED 조명→LED 조명, TV→TV · 이미지 2
- [병실] 병상 태블릿 하나로 환자와의 소통 해결 · 병상용 태블릿→갤럭시 탭 · 이미지 2
- [탕비실·라운지] 보호자를 위한 간이 조리실 · 상업용 세탁기/건조기→세탁기, BESPOKE 냉장고→냉장고 > Bespoke 냉장고 · 이미지 0
- [공간 없음] 의료진을 위한 진료 공간 혁신 ·  · 이미지 0
- [진료실] 정확한 환자 상태 판단을 위한 진료실 · QLED 8K 사이니지→모니터, 태블릿 전자차트→갤럭시 탭 · 이미지 0
유사 사례: ['성심요양병원 – 삼성 시스템에어컨+DMS 솔루', '나클리닉 - 스마트싱스 솔루션', '이리온 동물병원 – 삼성 무풍큐브 펫케어 + ']

### S2 · 업종 장면: kr_school — pass

히어로: ['미래 교육을 시작하다']
- [교실·강의실] 창의적인 학습 솔루션 · 삼성 Crystal UHD TV→TV > UHD, 플립→스마트 LCD 사이니지 > 전자칠판, 갤럭시 탭→갤럭시 탭 · 이미지 4
- [교실·강의실] 교육용 영상을 더욱 선명하게 · Crystal UHD TV→TV · 이미지 4
- [교실·강의실] 효과적인 디지털 멀티미디어 수업 · 갤럭시 탭→갤럭시 탭 · 이미지 4
- [교실·강의실] 함께 소통하는 참여형 수업 · 플립→스마트 LCD 사이니지 > 전자칠판 · 이미지 4
- [교실·강의실] 건강한 학습 공간 · 무풍 시스템에어컨→주거용 실내외기 > 기타 · 이미지 4
- [교무실] 효율적인 수업 준비 지원 · 에어드레서→에어드레서, 비스포크 슬림→청소기 > Bespoke 슬림, 갤럭시 탭→갤럭시 탭, 갤럭시 북→노트북 · 이미지 4
- [교무실] 온라인 강의 영상도 간편하게 제작 · 갤럭시 탭→갤럭시 탭 · 이미지 4
- [교무실] 교사를 위한 의류청정 서비스 · 비스포크 에어드레서→에어드레서 > Bespoke AI 에어드레서 · 이미지 4
유사 사례: ['서울교육대학교 AI 미래교실 - 삼성 스마트싱', '국민대학교 - 스마트 LED 사이니지&Flip', '성균관대학교 글로벌']

### S2 · 업종 장면: kr_manufacturing — pass

히어로: ['제조 프로세스를 혁신하다']
- [연구실] 연구/개발의 창의적인 아이디어 발굴 · 커브드 모니터→모니터, 스마트 사이니지→스마트 LCD 사이니지, 무풍 시스템에어컨→시스템에어컨 실내기, 디지털 복합기→디지털복합기 · 이미지 4
- [연구실] 쾌적한 업무환경을 제공하는 무풍 시스템에어컨 · 무풍 시스템에어컨→시스템에어컨 실내기 · 이미지 4
- [연구실] 업무 효율성을 높이는 커브드 모니터 · 커브드 모니터→모니터 · 이미지 4
- [연구실] 편리한 업무 진행이 가능한 디지털 복합기 · 디지털 복합기→디지털복합기 · 이미지 4
- [생산 현장] 안전한 생산환경 · 산업용 사이니지→스마트 LCD 사이니지, 산업용 LED조명→LED 조명, 산업용 태블릿→갤럭시 탭 · 이미지 4
- [생산 현장] 생산 효율화를 실현하는 산업용 태블릿 · 갤럭시 탭→갤럭시 탭 > 갤럭시 탭 액티브 · 이미지 4
- [생산 현장] 강력한 내구성을 제공하는 산업용 사이니지 · 스마트 사이니지→스마트 LCD 사이니지 > 단독형 · 이미지 4
- [생산 현장] 안정적인 조명품질을 제공하는 산업용 LED조명 · LED 조명→LED 조명 > 산업용 · 이미지 4
유사 사례: ['아이센스 송도2공장 - 삼성 시스템에어컨+바이', '기아 SUV EV9 – 더 프리스타일 EV9 ', '앱노트 핸들리 - 갤럭시 탭/회의실 예약 솔루']

### S2 · 업종 장면: kr_fnb — pass

히어로: ['차별화된 고객 유치 경쟁력을 갖추다']
- [입구] 실시간 맞춤 정보 제공 · 스마트 사이니지 (창문형)→스마트 LCD 사이니지 > 실외용, 스마트 사이니지 (비디오월)→스마트 LCD 사이니지 > 비디오월 · 이미지 4
- [주문·계산 카운터] 간편한 주문 / 결제 시스템 · 드라이브 스루 (Drive Through)→스마트 LCD 사이니지 > 실외용, 매장 결제 시스템→갤럭시 탭 · 이미지 4
- [홀·식사 공간, 매장 플로어] 쾌적한 매장 환경 · 시스템 청정환기→환기 솔루션, 에어모니터 플러스→주거용 실내외기 > 기타 · 이미지 4
- [백오피스·직원 공간, 매장 플로어] 디지털 기반 매장 관리 자동화 · 스마트싱스를 통한 매장 관리 자동화→스마트싱스 프로페셔널 솔루션, 스마트싱스를 통한 매장 관리 자동화→스마트싱스 프로페셔널 솔루션, 스마트싱스를 통한 매장 관리 자동화→스마트싱스 프로페셔널 솔루션, 스마트싱스를 통한 매장 관리 자동화→스마트싱스 프로페셔널 솔루션 · 이미지 3
유사 사례: ['밀키프레소 - 삼성 VXT 솔루션 + 스마트 ', '넥슨 메이플 아지트 - 삼성 스마트 LED 사', '노노샵(NONO SHOP) - 삼성 컬러 이페']

### S3 · 공간별 제품: guest_room @ kr_hotel — pass

- Infinite AI 무풍 시스템에어컨 판넬 · 주거용 실내외기 · 사이트 추천: 주거용 실내외기 > 기타 (space) / 사이트 추천: 주거용 실내외기 > 기타 (vertical)
- Infinite Line 무풍 시스템에어컨 일반 판넬 · 주거용 실내외기 · 사이트 추천: 주거용 실내외기 > 기타 (space) / 사이트 추천: 주거용 실내외기 > 기타 (vertical)
- 시스템에어컨 인테리어핏 판넬 · 주거용 실내외기 · 사이트 추천: 주거용 실내외기 > 기타 (space) / 사이트 추천: 주거용 실내외기 > 기타 (vertical)
- 에어모니터 플러스 · 주거용 실내외기 · 사이트 추천: 주거용 실내외기 > 기타 (space) / 사이트 추천: 주거용 실내외기 > 기타 (vertical)
- 프리미엄 솔라셀 리모트 · 주거용 실내외기 · 사이트 추천: 주거용 실내외기 > 기타 (space) / 사이트 추천: 주거용 실내외기 > 기타 (vertical)
- 호텔 TV CU700 시리즈 · 호텔TV · 사이트 추천: 호텔TV (space) / 사이트 추천: 호텔TV (space)

### S3 · 공간별 제품: classroom @ kr_school — pass

- Flip Pro 전자칠판 · 스마트 LCD 사이니지 · 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space)
- Flip Pro 전자칠판 · 스마트 LCD 사이니지 · 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space)
- 안드로이드 전자칠판 WAF · 스마트 LCD 사이니지 · 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space)
- 안드로이드 전자칠판 WAF + 안드로이드 전자칠판 이동식 스탠드 · 스마트 LCD 사이니지 · 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space)
- 전자칠판 Flip Pro(138.7cm)+Flip pro 전자칠판 트레이+Flip pro 55인치 이동식 스탠드 · 스마트 LCD 사이니지 · 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space)
- 전자칠판 Flip Pro(138.7cm)+Flip pro 전자칠판 트레이+스위블 벽걸이 · 스마트 LCD 사이니지 · 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space)

### S3 · 공간별 제품: meeting_room @ kr_office — pass

- 2 Way · 중앙공조 · 사이트 추천: 중앙공조 (vertical) / 사이트 추천: 중앙공조 (vertical)
- DVM 칠러 · 중앙공조 · 사이트 추천: 중앙공조 (vertical) / 사이트 추천: 중앙공조 (vertical)
- Flip Pro 전자칠판 · 스마트 LCD 사이니지 · 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 선례 점수 13.0
- Flip Pro 전자칠판 · 스마트 LCD 사이니지 · 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 선례 점수 15.0
- 무풍 1Way  · 중앙공조 · 사이트 추천: 중앙공조 (vertical) / 사이트 추천: 중앙공조 (vertical)
- 무풍 1Way (Wi-Fi 내장형) · 중앙공조 · 사이트 추천: 중앙공조 (vertical) / 사이트 추천: 중앙공조 (vertical)

### S4 · 제품 메시지 계층(Flip Pro) — pass

- 교육의 Pro를 위한 기능, 한계 없는 학습 공간 → ['디지털 교육의 발전에 발맞춰 새로운 양방향 학습 환경을 완성하는 Flip Pro를 소개합니']
- 양방향 학습을 위한 동급 최고수준 속도 멀티 터치 → ['삼성 Flip Pro는 2,048 단계의 압력 센서로 현실적이고 부드러운 드로잉을 할 수 ']
- 손쉽게 쓰고 그리며 완성하는 아이디어 → ['Flip Pro는 펜과 브러시 모드를 통해 실제 필기를 하는 듯한 경험을 할 수 있습니다.']
- 다양한 기기를 연결할 수 있는 편리함 → ['Flip Pro는 USB, HDMI는 물론 DP 등 다양한 연결방식을 제공하며, 모바일, ']
- 하나의 USB-C 포트, 세 가지 기능 → ['각각의 선을 준비해야 하는 번거로움 없이 하나의 포트 연결로 모든 준비를 마칠 수 있습니다']

### S4 · 업종 메시지 계층(호텔) — pass

tagline: 고객 유치 경쟁력을 갖춘 미래형 호텔을 완성하다
- 새로운 경험 SMART 객실 솔루션 (sec_cc1068a90702792c)
- SmartThings 앱 하나로 객실 기기 제어는 물론 다양한 객실 자동화 서비스 제공 (스마트싱스 프로페셔널 솔루션)
- 투숙객 맞춤 콘텐츠 제공 (sec_eff3e1ccba5fbb7b)
- 호텔 운영에 최적화된 링크 클라우드 솔루션 (링크 클라우드 솔루션)
- 집에서 보던 OTT 콘텐츠를 객실 TV로 (sec_f24f7dfef3946cc3)
- 강력한 몰입감과 편리함을 선사하는 호텔 맞춤형 TV (호텔TV)

### S4 · 테마 검색: 에너지 절감 — pass

- [key_message] 경제적인 에너지 절감 (sec_78bfad35bafd2c49)
- [usp] 에너지 절감 제어 (링크 제어기)
- [usp] 에너지 절감 제어 (링크 제어기)
- [key_message] 에너지 절감 제어 (b.IoT 솔루션)
- [key_message] 학습기반 예냉/예열을 통한 지능형 에너지 절감 (sec_3a9f750649c85fe4)
- [usp] 에너지 절감하고 전기료 절약하고 (건조기 9 kg)

### S4 · 컨텍스트→메시지: 호텔·객실·비즈니스호텔 체인·요구사항(모두 입력) — pass

컨텍스트: 업종 kr_hotel(input) · 공간 ['guest_room'] · 제품 ['TV'] · 빠짐 []
헤드라인: 고객 유치 경쟁력을 갖춘 미래형 호텔을 완성하다
- 넷플릭스 시청 가능한 호텔 TV (호텔 · 넷플릭스 시청 가능한 호텔 ) 0.536 · 업종 '호텔' 페이지 장면 / 같은 공간 장면 / 요구사항 유사 0.44
- 강력한 몰입감과 편리함을 선사하는 호텔 맞춤형 TV (호텔TV) 0.533 · 업종 '호텔' 페이지 문구 / 공간 '객실' 장면 문구 / 요구사항 유사 0.43
- 집에서 보던 OTT 콘텐츠를 객실 TV로 (호텔 · 집에서 보던 OTT 콘텐츠를) 0.519 · 업종 '호텔' 페이지 장면 / 같은 공간 장면 / 요구사항 유사 0.38
- 투숙객 맞춤 콘텐츠 제공 (호텔 · 투숙객 맞춤 콘텐츠 제공) 0.498 · 업종 '호텔' 페이지 장면 / 같은 공간 장면 / 요구사항 유사 0.31
- 호텔 운영에 최적화된 링크 클라우드 솔루션 (링크 클라우드 솔루션) 0.494 · 업종 '호텔' 페이지 문구 / 공간 '객실' 장면 문구 / 요구사항 유사 0.30
제품: 호텔 TV CU700 시리즈 0.45 — 체계적인 호텔 관리를 위한 통합 클라우드 플랫폼
제품: 호텔 TV HU7000F 시리즈 0.406 — 투숙객은 객실 내 TV에서 영화, TV 프로그램, 사진 등 좋아하는 콘텐
제품: 호텔 TV HU8000F 시리즈 0.347 — 전 객실 모든 투숙객들에게 몰입감 넘치는 시청각 경험을 선사하세요. 10
사례: IBC 호텔 – 삼성 TV (더 프레임) / 삼성 호텔 TV / 삼성 시 0.817 · 선택 제품을 쓴 사례 / 업종 사례 / 같은 공간 사례
사례: 신라스테이 서초 – 호텔 TV, 시스템에어컨, 터보 냉동기 0.692 · 업종 사례 / 같은 공간 사례 / 고객 유형 '프리미엄 비즈니스 호텔(체인)'
사례: 크라운 파크 호텔 서울 - 삼성 호텔 TV 0.682 · 업종 사례 / 같은 공간 사례 / 고객 유형 '비즈니스호텔'

### S4 · 컨텍스트→메시지: 요구사항 문장만(업종·공간·제품 추론) — pass

컨텍스트: 업종 kr_hotel(inferred) · 공간 ['guest_room', 'lobby'] · 제품 ['TV', '스마트 LCD 사이니지 > 비디오월'] · 빠짐 ['customer']
헤드라인: 고객 유치 경쟁력을 갖춘 미래형 호텔을 완성하다
- 투숙 만족도를 높이는 로비 공간 (호텔 · 투숙 만족도를 높이는 로비 ) 0.624 · 장면 항목에 선택 제품 / 업종 '호텔' 페이지 장면 / 같은 공간 장면
- 넷플릭스 시청 가능한 호텔 TV (호텔 · 넷플릭스 시청 가능한 호텔 ) 0.52 · 업종 '호텔' 페이지 장면 / 같은 공간 장면 / 요구사항 유사 0.47
- 강력한 몰입감과 편리함을 선사하는 호텔 맞춤형 TV (호텔TV) 0.503 · 업종 '호텔' 페이지 문구 / 공간 '객실' 장면 문구 / 요구사항 유사 0.43
- 집에서 보던 OTT 콘텐츠를 객실 TV로 (호텔 · 집에서 보던 OTT 콘텐츠를) 0.467 · 업종 '호텔' 페이지 장면 / 같은 공간 장면 / 요구사항 유사 0.36
- 호텔 운영에 최적화된 링크 클라우드 솔루션 (링크 클라우드 솔루션) 0.456 · 업종 '호텔' 페이지 문구 / 공간 '객실' 장면 문구 / 요구사항 유사 0.34
제품: 호텔 TV CU700 시리즈 0.526 — 체계적인 호텔 관리를 위한 통합 클라우드 플랫폼
제품: 비디오월 Ultra 베젤 3.5 mm 시리즈 0.445 — 비디오월 Ultra 베젤 3.5 mm 시리즈는 언제 어디서나 고객의 시선
제품: 호텔 TV HU7000F 시리즈 0.44 — 멀티 코드 리모컨으로 삼성 호텔 TV는 인접 리모컨이나 디스플레이의 간섭
사례: IBC 호텔 – 삼성 TV (더 프레임) / 삼성 호텔 TV / 삼성 시 0.762 · 선택 제품을 쓴 사례 / 업종 사례 / 같은 공간 사례
사례: 여수 산무인호텔 – 삼성 스마트 LED 사이니지, 삼성 TV 0.704 · 선택 제품을 쓴 사례 / 업종 사례 / 같은 공간 사례
사례: 울산 인투모텔 – 삼성 TV/시스템에어컨 0.645 · 선택 제품을 쓴 사례 / 업종 사례 / 같은 공간 사례

### S4 · 컨텍스트→메시지: 제품만(비디오월 분류 + 로비) — pass

컨텍스트: 업종 None(None) · 공간 ['lobby'] · 제품 ['스마트 LCD 사이니지 > 비디오월'] · 빠짐 ['vertical', 'customer', 'text']
- 효과적인 정보 전달 (중소형 의원 · 효과적인 정보 전달) 0.873 · 장면 항목에 선택 제품 / 같은 공간 장면
- 대화면과 선명한 화질로 신속한 정보 공유 (스마트 LCD 사이니지 > 비디오월) 0.782 · 선택 분류 / 공간 추천 분류
- 압도적 몰입감을 선사하는 초슬림 베젤과 멀티화면 구성으로 최적의 관제실 솔루션 제공 (스마트 LCD 사이니지 > 비디오월) 0.782 · 선택 분류 / 공간 추천 분류
- 실감나는 디스플레이로 차별화된 경험 제공 (스마트 LCD 사이니지 > 비디오월) 0.782 · 선택 분류 / 공간 추천 분류
- 단지 내 공지사항 및 상가 프로모션 정보 등 아파트 관련 정보 적시 제공 (스마트 LCD 사이니지) 0.682 · 선택 분류의 상위 분류 / 공간 '로비' 장면 문구
제품: 비디오월  Razor 베젤 0.88mm 시리즈 0.691 — 종잇장처럼 얇고 매끄러운 비디오월
제품: 비디오월 Extreme 베젤 1.74mm 시리즈 0.691 — 공간의 한계를 뛰어넘는 상시 작동 디스플레이
제품: 비디오월 Ultra 베젤 3.5 mm 시리즈 0.691 — 24시간 고객의 시선을 사로잡는 사이니지
사례: 청주대학교 중앙도서관 – 삼성 스마트 사이니지(공지용) 1.0 · 선택 제품을 쓴 사례 / 같은 공간 사례
사례: 프랑스 퓌티로스코프 테마파크 - 스마트 LED 사이니지(IFR 시리즈)  0.636 · 선택 제품을 쓴 사례
사례: NFT아트갤러리 청담 – 스마트 사이니지 + MagicINFO 솔루션 0.636 · 선택 제품을 쓴 사례

### S4 · 컨텍스트→메시지: 빈 컨텍스트 → 질문 — pass


### S5 · 공간×카테고리 배치 이미지: 객실 × 호텔TV — pass

- [A] https://images.samsung.com/kdp/cms_contents/108882/7e4b7164-6e66-4514-aacd-cb4423a1b92f.jpg · 호텔의 객실 침대 정면 벽면에 호텔TV가 설치되어 있고 화면으로 우주비행사의 모습이 보입니 · 객실 · 예시 사진(삼성 공식 이미지)
- [A?C] https://images.samsung.com/kdp/cms_contents/108882/6b6bc4f4-6c20-411f-8758-bc8788023f26.jpg · 총 4개의 주요 특장점을 각각의 이미지와 함께 보여줍니다. 링크 클라우드 맞춤형 서비스를  · 객실 · 예시 사진(삼성 공식 이미지)
- [A?C] https://images.samsung.com/kdp/business/hospitality/ci_slide1_3_obj.png · 호텔 맞춤형 TV 안내 이미지 · 객실 · 예시 사진(삼성 공식 이미지)
- [A?C] https://images.samsung.com/is/image/samsung/p5/sec/business/hospitality_2020/ci_slide2_2_obj.png · 호텔 맞춤형 TV 안내 이미지 · 객실 · 예시 사진(삼성 공식 이미지)

### S5 · 공간 이미지: 회의실 — pass

- [A] https://images.samsung.com/kdp/cms_contents/102774/cac1ebbe-52d8-447f-a6d6-63ae8a6b0b40.jpg · 회의실에서 회의중인 여러 사람들이 있고 그 위로 천장에 무풍 4Way 실내기가 설치되어 있 · 회의실 · 예시 사진(삼성 공식 이미지)
- [A] https://images.samsung.com/is/image/samsung/sec-feature-indoor-floor-103249485 · 외부가 보이는 통창의 넓은 회의실 공간이 있고 좌측에는 긴 회의용 테이블과 데스크체어들이  · 회의실 · 예시 사진(삼성 공식 이미지)
- [A] https://images.samsung.com/kdp/cms_contents/109721/65ed59ce-813f-45f4-939d-e6a9097bdffa.jpg · 대형 회의실 정면 벽에 Flip Pro 전자칠판이 설치되어 있는 모습입니다. Flip Pr · 회의실 · 예시 사진(삼성 공식 이미지)
- [A] https://images.samsung.com/kdp/cms_contents/109721/15c53bf1-039c-4840-ba40-06c77ee17413.jpg · 회의가 진행중인 회의실에서 한 남성이 정면 벽에 설치된 Flip Pro 전자칠판의 화면에  · 회의실 · 예시 사진(삼성 공식 이미지)
- [A] https://images.samsung.com/kdp/cms_contents/109721/4430b71f-a3d8-4f7d-a19a-e579b3939406.jpg · 회의실 벽면에 설치된 Flip Pro 전자칠판 화면으로 정면에 손으로 들고있는 스마트폰의  · 회의실 · 예시 사진(삼성 공식 이미지)

### S5 · 공간 이미지 폴백: 수술실 × 공기청정기 — pass

- [A] https://images.samsung.com/kdp/cms_task/C20260108000109/46918/d85cda5e-22cc-4acb-9d0e-d678b11a426b.jpg · 이미지 왼쪽 부분에 Infinite AI 공기청정기 공간과 조화되는 본연의 깨끗함, 일상  · 주거 거실 · 예시 사진(삼성 공식 이미지)
- [A] https://images.samsung.com/kdp/cms_task/C20260116000119/47108/692c5f62-43d7-4c65-b759-1e06e5212b32.jpg · 왼쪽에는 대리석이 깔린 베이지 톤의 거실을 배경으로 뒤쪽 벽에는 원목 색상의 패널 장식이  · 주거 거실 · 예시 사진(삼성 공식 이미지)
- [A] https://images.samsung.com/kdp/cms_task/C20260116000095/47084/b1d4c209-fab4-49f5-a956-f63d916dcf5d.jpg · 연한 베이지 톤으로 포인트 인테리어가 된 아늑한 분위기의 침실을 배경으로 가운데에는 연한  · 주거 침실 · 예시 사진(삼성 공식 이미지)
- [A] https://images.samsung.com/kdp/cms_task/C20260116000099/47088/bec73ca1-646b-4481-ab3e-5f46e23eb244.jpg · 이미지 중앙에 Infinite AI 공기청정기 우측면 상단 3분의 2 정도가 확대 되어 놓 · 주거 거실 · 예시 사진(삼성 공식 이미지)
- [A] https://images.samsung.com/kdp/cms_task/C20260116000109/47098/984a2fab-2e7f-4977-a1f6-14806e55e83c.jpg · 왼쪽에는 그레이톤 인테리어의 거실을 배경으로 연한 회색의 패브릭 소파 위에는 분홍색 카디건 · 주거 거실 · 예시 사진(삼성 공식 이미지)

### S5 · 제품 설치 사진: 호텔TV — pass

- [A] https://images.samsung.com/kdp/editor/case-study/2405301/pc_case_01.jpg ·  · None · 도입사례 사진
- [A] https://images.samsung.com/kdp/editor/case-study/2405301/pc_case_02.gif ·  · None · 도입사례 사진
- [A] https://images.samsung.com/kdp/editor/case-study/2405301/pc_case_03.jpg ·  · None · 도입사례 사진
- [A] https://images.samsung.com/kdp/editor/case-study/2405301/pc_case_04.jpg ·  · None · 도입사례 사진
- [A] https://images.samsung.com/kdp/editor/case-study/2405301/pc_case_04.gif ·  · None · 도입사례 사진

### S5 · 이미지 검색: 카페 천장 시스템에어컨 — pass

- [A] https://images.samsung.com/is/image/samsung/p5/sec/business/business-insights/gemstone2-1.jpg · 좌)카페 젬스톤 내부에 설치된 삼성 시스템에어컨 360 우) 삼성 시스템에어컨 360 확대 · None · 도입사례 사진
- [A] https://images.samsung.com/is/image/samsung/sec-indoor-ceiling-360-am145kn4pbh1-white-thumb-Front-83627799 · 천장형 실내기_360 화이트 제품 정면(사각형) · None · 도입사례 사진
- [A] https://images.samsung.com/is/image/samsung/p5/sec/business/insights/case-study/2018/08/20180827-4.jpg · 왼쪽) 헤리티지 산후조리원에 설치된 삼성 시스템에어컨 360 디자인판넬의 모습입니다. 오른 · None · 도입사례 사진
- [A] https://images.samsung.com/is/image/samsung/p5/sec/business/business-insights/gemstone1.jpg · 젬스톤 카페 내부에 설치된 삼성 시스템에어컨 360, 삼성 스마트 사이니지 · None · 도입사례 사진
- [A] https://images.samsung.com/is/image/samsung/p5/sec/business/insights/case-study/2018/05/20180516_2.jpg · 좌)레고 코리아 사무실 내부에 설치된 삼성 시스템에어컨 360 우)사무실 내부에 설치된 삼 · None · 도입사례 사진

### S6 · 솔루션 통합 보기: 링크 클라우드 — pass

- us_solution · Samsung Business US | Samsung LYNK Cloud · 18회
- industry · 호텔 | 업종별 제안 | Samsung Business 대한민국 · 17회
- case_study · 인스파이어 엔터테인먼트 리조트 - 사이니지 + 갤럭시 탭 + 호텔 TV/ · 9회
- solution · 링크 클라우드ㅣTV/음향 솔루션ㅣSamsung Business 대한민국 · 8회
- pdp · 링크 클라우드ㅣTV/음향 솔루션ㅣSamsung Business 대한민국 · 7회
- us_landing · Digital Signage Displays | Commercial Di · 5회

### S6 · 제품군 통합 보기: 호텔TV — pass

- 해상도: 4 K (3,840 x 2,160)
- WiFi: 있음 (Wi-Fi 5)
- 에너지효율 등급: 1
- 소비전력 (Max): 110 W
- 소비전력 (Stand-by): 0.5 W
- 소비전력 (Typical): 49.4 W

### S7 · 요구 스펙 대응표(고휘도 사이니지) — pass

- brightness_nit >= 2500 · 실제 4,000 nit → pass
- operation_hours >= 24 · 실제 24/7 → pass
- pixel_pitch_mm <= 1 · 실제 0.53 x 0.53 mm → pass
- capacity_l >= 100 · 실제 None → unknown

### S8 · 유사 사례: 호텔 객실 TV — pass

- 롯데 시그니엘 서울 - 삼성 호텔 TV · 0.976 · {'vertical': 1.0, 'space': 1.0, 'product': 1.0, 'text': 0.84} · KPI 0 · 사진 True
- 부티크 호텔 XYM - 삼성 호텔 TV, 삼성 올인원PC · 0.969 · {'vertical': 1.0, 'space': 1.0, 'product': 1.0, 'text': 0.8} · KPI 1 · 사진 True
- 크라운 파크 호텔 서울 - 삼성 호텔 TV · 0.961 · {'vertical': 1.0, 'space': 1.0, 'product': 1.0, 'text': 0.74} · KPI 3 · 사진 True
- IBC 호텔 – 삼성 TV (더 프레임) / 삼성 호텔 TV / 삼성 시스템에어컨 · 0.955 · {'vertical': 1.0, 'space': 1.0, 'product': 1.0, 'text': 0.7} · KPI 0 · 사진 True
- 신라스테이 서초 – 호텔 TV, 시스템에어컨, 터보 냉동기 · 0.948 · {'vertical': 1.0, 'space': 1.0, 'product': 1.0, 'text': 0.65} · KPI 0 · 사진 True

### S8 · 성과 KPI: 호텔TV 사용 사례 — pass

- 길이 150m 공간 벽면·기둥 LED 구성 (인스파이어 엔터테인먼트 리조트 - 사)
- 전 객실 호텔 TV·갤럭시 탭 공급 (인스파이어 엔터테인먼트 리조트 - 사)
- 오픈 4개월 만에 단골 다수 확보 (부티크 호텔 XYM - 삼성 호텔 T)
- 제안 후 6개월 만에 전 객실 도입 (크라운 파크 호텔 서울 - 삼성 호텔)

### S8 · 사례 통계: 교육 — pass

- 갤럭시 탭 4
- Knox 솔루션 4
- 시스템에어컨 실내기 3
- 갤럭시 탭 > 갤럭시 탭 A 3
- 올인원PC/데스크탑 > 올인원 PC 2
- 디지털복합기 2

### S9 · 업종 판별 정확도(10문장) — pass

- 병원 입원실 환자용 태블릿 → ['kr_medical', 'kr_medical'] (정답 kr_medical)
- 학교 교실 전자칠판 → ['kr_education', 'kr_education'] (정답 kr_education)
- 호텔 객실 TV → ['kr_hotel', 'kr_public'] (정답 kr_hotel)
- 공장 물류센터 산업용 태블릿 → ['kr_manufacturing', 'kr_transport'] (정답 kr_manufacturing)
- 은행 지점 VIP 공간 → ['kr_finance', 'kr_construction'] (정답 kr_finance)
- 아파트 커뮤니티 공간과 거실 → ['kr_construction', 'kr_construction'] (정답 kr_construction)
- 매장 주문 공간 키오스크 → ['kr_manufacturing', 'kr_retail_fnb'] (정답 kr_retail_fnb)
- 병영 생활관 무풍 에어컨 → ['kr_public', 'kr_public'] (정답 kr_public)
- 공항 라운지 사이니지 → ['kr_transport', 'kr_hotel'] (정답 kr_transport)
- 민원실 대기 공간 안내 → ['kr_public', 'kr_public'] (정답 kr_public)

### S10 · 업종 추천 솔루션: 호텔 — pass

- 링크 클라우드 솔루션 → 링크 클라우드 솔루션
- b.IoT 솔루션 → b.IoT 솔루션

### S13 · 하이브리드 검색: 객실 TV 원격 관리 — pass

- case_study · 크라운 파크 호텔 서울 - 삼성 호텔 TV · [이미지] 크라운 파크 호텔 객실에 삼성 호텔 TV가 설치된 사진
"호텔TV 관리와 호텔 정보, 콘텐츠 제공
- case_study · 크라운 파크 호텔 서울 - 삼성 호텔 TV · [이미지] 크라운 파크 호텔 내부에 삼성 호텔 TV, 삼성 링크 리치 솔루션 도입된 사진
삼성전자는 2015
- pdp · 특장점 > 호텔 운영에 최적화된 올인원 플랫폼을 소개합니다 · [이미지] 구름 모양의 아이콘 안에 사이니지가 벽면에 설치되어 있습니다.
[이미지] 전세계가 그려진 그래픽 
- pdp · 특장점 > 호텔 운영에 최적화된 올인원 플랫폼을 소개합니다 · 호텔 운영에 최적화된 올인원 플랫폼을 소개합니다
삼성 링크 클라우드는 관리자의 효율적인 운영을 돕고, 고객에

### S13 · 하이브리드 검색: 전자칠판 필기 공유 — pass

- case_study · 국민대학교 - 스마트 LED 사이니지&Flip Pro 전자칠판&시스템에어컨 360 > 국민대학교– 스마트 LED 사이니지+Flip Pro 전자칠판+시스템에어컨 360 > 02 적극적인 의견 교류를 위해 강의자와 학생 간 소통을 지원하는 디바이스가 필요합니다 · 02 적극적인 의견 교류를 위해 강의자와 학생 간 소통을 지원하는 디바이스가 필요합니다
Flip Pro 전자
- case_study · 삼성전자 모듈러 교육시설 - 스마트싱스 프로 구축 > 삼성전자 모듈러 교육시설 – 스마트싱스 프로 구축 > 03 적극적인 토론과 소통을 위한 스마트 디바이스는 필수입니다 · 03 적극적인 토론과 소통을 위한 스마트 디바이스는 필수입니다
Flip Pro 전자칠판은 다양한 디바이스와 
- case_study · 국민대학교 - 스마트 LED 사이니지&Flip Pro 전자칠판&시스템에어컨 360 > [SOLUTION] 삼성 스마트 LED 사이니지 신세계스퀘어 본관* · [SOLUTION] 삼성 스마트 LED 사이니지 신세계스퀘어 본관*
SOLUTION 01. 선명한 화질과 함
- pdp · 특장점 > 주요 기능 개요 · 주요 기능 개요
[이미지] 총 4개의 주요 특장점을 이미지와 함께 보여주고 있습니다. 왼쪽 상단부터 시계 방

### S13 · 하이브리드 검색: 무풍 냉방 직바람 — pass

- pdp · USP · 직바람없이 시원한 무풍냉방
무풍 지능냉방으로 자동 조절
인체감지 지능냉방
- pdp · 특장점 > 직바람 없이 시원하게 무풍냉방 · 직바람 없이 시원하게 무풍냉방
쾌속냉방으로 실내를 빠르게 냉방 시킨 후, 15,700여개의 마이크로 홀이 무
- pdp · 특장점 > 직바람 없이 시원하게 · 직바람 없이 시원하게
쾌속냉방으로 실내를 빠르게 냉방 시킨 후, 15,700여개의 마이크로 홀이 무풍냉방을 
- pdp · USP · 직바람없이 시원한 무풍냉방
지능 냉방으로 자동 조절
최대 50 % 에너지 절감

### S13 · 하이브리드 검색: 실외 사이니지 밝기 — pass

- case_study · 커피빈 학동역 DT점, 서초역 1번출구점 – 삼성 스마트 사이니지 (홍보용) / 삼성 시스템에어컨 360 · 커피빈 학동역 DT점, 서초역 1번출구점 – 삼성 스마트 사이니지 (홍보용) / 삼성 시스템에어컨 360
2
- case_study · 두껍삼 명동직영점 – 갤럭시 탭/테이블 오더 솔루션 + Knox Configure · 또한 본체 대비 와이드한 대화면 * 은 선명한 화질의 이미지로 오더 시스템이 익숙하지 않은 중장년층 고객들도
- case_study · 현대백화점면세점 무역센터점– 삼성 스마트 LED 사이니지 · 현대백화점면세점 무역센터점– 삼성 스마트 LED 사이니지
2019-05-13
[이미지] 현대백화점면세점 무역
- case_study · 광명동굴 – 삼성 스마트 사이니지(홍보용) · 광명동굴 – 삼성 스마트 사이니지(홍보용)
2017-10-17
[이미지] 광명동굴에 설치된 삼성 스마트 사이

### S13 · 하이브리드 검색: 급식실 영양 정보 사이니지 — pass

- industry · 급식 영양 정보를 생생하게 전달 · 급식 영양 정보를 생생하게 전달
스마트 사이니지 메뉴보드로 급식 메뉴와 영양 정보 등 다양한 정보를 생생하게
- industry · 디지털 포스터로 금융 정보 신속 전달 > 양면형 사이니지 · 양면형 사이니지
자세히 보기
“고객들은 정확한 정보를 신속하게 받아들이면서도 관심도가 높아졌고, 직원들은 효
- landing · 사이니지 영상 · 사이니지 영상
- case_study · 코엑스 SM타운/K-POP 광장 – 삼성 스마트 LED 사이니지 · 참고안내 - LED 사이니지(실내용)은 하단 관련제품을 참고하여 주시기 바랍니다. - LED 사이니지(실외용
