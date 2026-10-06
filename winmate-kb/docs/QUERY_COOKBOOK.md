# 질의 예시 모음 (Query Cookbook)

모든 예시는 `kb/winmate_kb.sqlite` 에 실제로 실행한 결과를 줄여 옮긴 것이다(`python tests/make_cookbook.py` 로 다시 생성).
질의는 LLM 없이 결정적으로 동작한다. 결과는 공통 봉투(`pattern, result, evidence_paths, tier_min, candidates, decision_hint,
decision_reasons, needs_confirmation, fallback_level, modes_used, timings_ms`)로 나온다.

```python
import sys; sys.path.insert(0, 'build')
from query import KB
kb = KB()          # kb/winmate_kb.sqlite
```

| 코드 | 이름 | 메서드 |
|---|---|---|
| search | 하이브리드 검색(키워드 + 벡터, 원문 청크·엔티티) | `kb.search(text)` |
| A1 | 엔티티 링킹(모델코드·제품·카테고리·솔루션·업종·공간·역량) | `kb.A1(text)` |
| A2 | 업종 판별(top-2, 애매하면 ask) | `kb.A2(text)` |
| A3 | 요구 스펙 항목 → 정규 키 | `kb.A3([{name_raw, value_raw}])` |
| B1 | 업종 프리셋(공간 시퀀스·장면·추천 솔루션·사례) | `kb.B1(vertical_id)` |
| B2 | 요구사항 결핍 → 확인 질문 | `kb.B2(text)` |
| C1 | 공간·요구 → 역량(hard/soft) | `kb.C1(spaces, text)` |
| C2 | 후보 제품군(역량 충족 + 사이트 추천 + 선례 + 문장 유사도) | `kb.C2(caps, category, space, vertical, soft, text)` |
| C3 | 제품 → 적합 업종·공간·사례(역방향) | `kb.C3(family_id)` |
| C4 | 제외 사유 | `kb.C4(family_id, caps, category)` |
| C6 | 요구 스펙 충족 판정(pass/fail/unknown) | `kb.C6(ref, requirements)` |
| D1 | 유사 사례(업종·공간·제품·문장 분해 점수) | `kb.D1(vertical, spaces, targets, text)` |
| D2 | 사례 통계 | `kb.D2(vertical=…)` / `kb.D2(space=…)` |
| D3 | 성과 KPI | `kb.D3(deployment_ids, target)` |
| D5 | 공존 패턴(함께 쓰인 제품·솔루션) | `kb.D5(targets)` |
| E1 | 메시지 계층(tagline → key message → proof point) | `kb.E1(about, vertical, space, locale)` |
| E2 | 테마로 메시지 찾기 | `kb.E2(theme)` |
| E3 | 요구사항 컨텍스트(업종·공간·제품·타겟고객·요구사항, 모두 선택) → 메시지 묶음 | `kb.E3(vertical, spaces, products, customer, text)` |
| G1 | 공간 × 카테고리 배치 이미지(폴백 포함) | `kb.G1(space, category, vertical)` |
| G2 | 제품·카테고리가 나오는 이미지(사례 사진 우선) | `kb.G2(kind, id)` |
| G4 | 제품 단독컷 | `kb.G4(family_id)` |
| G5 | 사례 사진 | `kb.G5(deployment_id)` |
| images | 이미지 검색(alt·캡션·맥락) | `kb.image_search(text)` |
| entity | 엔티티 통합 보기(흩어진 정보 모음) | `kb.entity(kind, id)` |
| S1 | 요구사항 → 공간별 추천(체인: A1·A2 → 절 단위 묶기 → C1 → C2 → D1) | `kb.S1(text)` |
| S2 | 업종 → 장면 구성(체인: B1 → E1 → G1 → D1) | `kb.S2(vertical, space)` |

## S1 · 요구사항 → 공간별 제품 추천

요구 문장을 절 단위로 나눠 공간·카테고리·역량을 묶고, 공간마다 후보를 낸다. hard 역량을 못 채우면 후보에서 빠진다(실외·직사광은 완화 없음).

```bash
python build/query.py S1 "호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어"
```

```python
kb.S1("호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어")
```

결과 요약(판단 `check` ['LOW_TIER'], 1818 ms):

```
업종: [('kr_hotel', 1.0), ('kr_home', 0.088)]
[객실] 절=['호텔 객실 TV를 통합 관리'] 카테고리=None hard=['cap_hospitality_tv_mgmt']
  호텔 TV CU700 시리즈 (HG43CU700NFXKR) 0.856 — 충족 객실 TV 통합 관리: 스펙 '삼성 LYNK™ Cloud' = 있음 / 사이트 추천: 호텔TV (space)
  호텔 TV HU7000F 시리즈 (HG43U700FNFXKR) 0.856 — 충족 객실 TV 통합 관리: 스펙 '삼성 LYNK™ Cloud' = 있음 / 사이트 추천: 호텔TV (space)
  호텔 TV HU8000F 시리즈 (HG43U800FNFXKR) 0.856 — 충족 객실 TV 통합 관리: 스펙 '삼성 LYNK™ Cloud' = 있음 / 사이트 추천: 호텔TV (space)
  솔루션: ['스마트싱스 프로페셔널 솔루션', '링크 클라우드 솔루션', 'b.IoT 솔루션']
[로비] 절=['로비에 대형 비디오월을 설치'] 카테고리=스마트 LCD 사이니지 > 비디오월 hard=['cap_bezel_less_tiling']
  비디오월  Razor 베젤 0.88mm 시리즈 (LH55VHCRBGBXKR) 1.0 — 충족 이음매 최소 타일링: 사이트 목록 필터 'videowall' / 충족(soft) 원격 콘텐츠 관리
  비디오월 Extreme 베젤 1.74mm 시리즈 (LH55VMCEBGBXKR) 1.0 — 충족 이음매 최소 타일링: 사이트 목록 필터 'videowall' / 사이트 추천: 스마트 LCD 사이니지 (space)
  비디오월 Extreme 베젤 1.74mm 시리즈 (LH55VHCEBGBXKR) 1.0 — 충족 이음매 최소 타일링: 사이트 목록 필터 'videowall' / 사이트 추천: 스마트 LCD 사이니지 (space)
  솔루션: ['스마트싱스 프로페셔널 솔루션', '링크 클라우드 솔루션', 'b.IoT 솔루션']
유사 사례: ['IBC 호텔 – 삼성 TV (더 프레임) / 삼성 호텔', '울산 인투모텔 – 삼성 TV/시스템에어컨', '여수 산무인호텔 – 삼성 스마트 LED 사이니지, 삼성']
```

## A1 · 엔티티 링킹

문장 안의 모델코드·제품·카테고리·솔루션·업종 표현과 공간·요구 키워드를 찾는다.

```bash
python build/query.py A1 "병원 로비 대기실에 MagicINFO로 관리하는 24시간 사이니지"
```

```python
kb.A1("병원 로비 대기실에 MagicINFO로 관리하는 24시간 사이니지")
```

결과 요약(판단 `auto` [], 1 ms):

```
병원 → vertical:kr_hospital (병원) conf=0.9 [alias]
MagicINFO → solution:sol_magicinfo (사이니지 콘텐츠관리 Magic INFO) conf=0.6 [alias]
사이니지 → category:top_display (사이니지) conf=0.9 [alias]
대기실 → space_type:waiting_area (대기 공간) conf=0.8 [space_keyword]
로비 → space_type:lobby (로비) conf=0.8 [space_keyword]
24시간 → capability:cap_continuous_operation (상시 구동) conf=0.7 [need_keyword]
```

## A2 · 업종 판별

업종명·공간·제품 신호와 문장 유사도로 KR 업종 top-2 를 낸다. 1·2위 차가 작으면 `ask`.

```bash
python build/query.py A2 "공장 생산 라인 작업자용 산업용 태블릿"
```

```python
kb.A2("공장 생산 라인 작업자용 산업용 태블릿")
```

결과 요약(판단 `auto` [], 3 ms):

```
kr_manufacturing 1.0 ["공간 '생산 현장'", "제품·솔루션 '갤럭시 탭'", '유사도 0.43']
kr_transport 0.229 ["제품·솔루션 '갤럭시 탭'", '유사도 0.39']
kr_hospital 0.187 ["제품·솔루션 '갤럭시 탭'", '유사도 0.31']
kr_medical 0.187 []
```

## B1 · 업종 프리셋

업종 페이지 장면 순서를 공간 시퀀스로 쓰고, 장면별 추천 항목(링크로 해소된 제품·솔루션), 히어로 문구, 추천 솔루션, 대표 사례를 낸다.

```bash
python build/query.py B1 kr_hospital
```

```python
kb.B1("kr_hospital")
```

결과 요약(판단 `auto` [], 1 ms):

```
공간 시퀀스: ['로비', '병원 접수·수납', '대기 공간', '병실', '탕비실·라운지', '진료실', '수술실', '간호사 스테이션', '회의실']
- 환자를 위한 의료 공간 혁신 [로비] → ['시스템에어컨·공조', 'LED 조명', '스마트 LED 사이니지', '스마트 LCD 사이니지']
- 환자의 편의를 돕는 모바일 전자 서명 [병원 접수·수납] → ['갤럭시 탭']
- 대기 중인 고객을 위한 진료 대기실 [대기 공간] → ['스마트 LCD 사이니지']
- 환자를 위한 세심함이 느껴지는 입원실 [병실] → ['환기 솔루션', '시스템에어컨 실내기', 'LED 조명', 'TV']
- 병상 태블릿 하나로 환자와의 소통 해결 [병실] → ['갤럭시 탭']
- 보호자를 위한 간이 조리실 [탕비실·라운지] → ['세탁기', '냉장고 > Bespoke 냉장고']
추천: ['b.IoT 솔루션', 'b.IoT 솔루션', 'b.IoT 솔루션', '시스템에어컨 제어 솔루션 DMS 2.5', '시스템에어컨 제어 솔루션 DMS 2.5', '시스템에어컨 제어 솔루션 DMS 2.5', '사이니지 콘텐츠관리 Magic INFO', '사이니지 콘텐츠관리 Magic INFO', '사이니지 콘텐츠관리 Magic INFO']
```

## C2 · 공간 × 역량 후보

역량(presence 규칙)과 사이트 추천을 함께 본다. 예: 교실에서 터치가 되는 제품.

```bash
python build/query.py C2 --caps touch_interactive --space classroom --vertical kr_school
```

```python
kb.C2(["touch_interactive"], space="classroom", vertical="kr_school")
```

결과 요약(판단 `check` ['LOW_MARGIN', 'LOW_TIER'], 38 ms):

```
Flip Pro 전자칠판 0.8 — 충족 터치 상호작용: 사이트 목록 필터 'electronic-board' / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space)
Flip Pro 전자칠판 0.8 — 충족 터치 상호작용: 사이트 목록 필터 'electronic-board' / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space)
안드로이드 전자칠판 WAF 0.8 — 충족 터치 상호작용: 사이트 목록 필터 'electronic-board' / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space)
안드로이드 전자칠판 WAF + 안드로이드 전자칠판 이동식 스탠드 0.8 — 충족 터치 상호작용: 사이트 목록 필터 'electronic-board' / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space)
전자칠판 Flip Pro(138.7cm)+Flip pro 전자칠판 트레이+Flip pro 55인치 이동식 스탠드 0.8 — 충족 터치 상호작용: 사이트 목록 필터 'electronic-board' / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space) / 사이트 추천: 스마트 LCD 사이니지 > 전자칠판 (space)
```

## C3 · 제품 → 적합 업종·공간(역방향)

업종 페이지 추천과 도입사례로 이 제품(또는 소속 카테고리)이 쓰이는 곳을 찾는다.

```bash
python build/query.py C3 fam_G000183751
```

```python
kb.C3("fam_G000183751")
```

결과 요약(판단 `auto` [], 0 ms):

```
병원 / 병실 via category:갤럭시 탭 (3개 장면)
제조 / 생산 현장 via category:갤럭시 탭 > 갤럭시 탭 액티브 (2개 장면)
학교 / 교실·강의실 via category:갤럭시 탭 (2개 장면)
학교 / 교무실 via category:갤럭시 탭 (2개 장면)
유통 / 매장 플로어 via category:갤럭시 탭 (2개 장면)
운송 / 차량 내부 via category:갤럭시 탭 (2개 장면)
사례 55건: ['르노삼성자동차 – 갤럭시 탭 액티브,', 'CJ푸드빌 ‘제일제면소’– 갤럭시 탭', '서울드래곤시티 – 하만 프로 오디오']
```

## C6 · 요구 스펙 충족 판정

정규 스펙 키로 pass/fail 을 판정하고, 스펙이 없으면 추정하지 않고 unknown.

```bash

```

```python
kb.C6("fam_G000181132", [{"key": "brightness_nit", "op": ">=", "value": 2500}, {"key": "operation_hours", "op": ">=", "value": 24}, {"key": "weight_kg", "op": "<=", "value": 20}, {"key": "capacity_l", "op": ">=", "value": 100}])
```

결과 요약(판단 `auto` [], 0 ms):

```
brightness_nit >= 2500 · 실제 4,000 nit → pass
operation_hours >= 24 · 실제 24/7 → pass
weight_kg <= 20 · 실제 18.2 kg → pass
capacity_l >= 100 · 실제 None → unknown
```

## D1 · 유사 사례

업종·공간·제품 겹침과 문장 유사도를 분해해서 보여 준다.

```bash
python build/query.py D1 --vertical kr_education --space classroom "전자칠판 수업"
```

```python
kb.D1(vertical="kr_education", spaces=["classroom"], targets=[("category", "cat_smart-signage__flip")], text="전자칠판 수업")
```

결과 요약(판단 `check` ['LOW_MARGIN', 'LOW_TIER'], 11 ms):

```
국민대학교 - 스마트 LED 사이니지&Flip Pro 전자칠판&시스템에어 0.936 {'vertical': 1.0, 'space': 1.0, 'product': 1.0, 'text': 0.57} KPI=1 사진=True
서울교육대학교 AI 미래교실 - 삼성 스마트싱스 프로 + 갤럭시 탭&무빙 0.863 {'vertical': 1.0, 'space': 1.0, 'product': 1.0, 'text': 0.09} KPI=0 사진=True
삼성전자 모듈러 교육시설 - 스마트싱스 프로 구축 0.608 {'vertical': 0.0, 'space': 1.0, 'product': 1.0, 'text': 0.39} KPI=2 사진=True
서울 문정초등학교 디지털 교과서 – 갤럭시 탭 + 삼성 무선 네트워크 A 0.563 {'vertical': 1.0, 'space': 1.0, 'product': 0.0, 'text': 0.09} KPI=2 사진=True
삼성전자 CSR 프로그램 – 삼성 스마트스쿨 0.562 {'vertical': 0.0, 'space': 1.0, 'product': 1.0, 'text': 0.08} KPI=1 사진=True
```

## D5 · 공존 패턴

사례에서 대상과 함께 쓰인 제품·솔루션(support·confidence·lift).

```bash

```

```python
kb.D5([("category", "cat_hotel-tvs")])
```

결과 요약(판단 `check` ['LOW_TIER'], 2 ms):

```
기준 사례 7
스마트 LCD 사이니지 support=3 conf=0.429 lift=1.84
시스템에어컨·공조 support=3 conf=0.429 lift=1.57
갤럭시 탭 support=2 conf=0.286 lift=2.18
스마트 LED 사이니지 support=2 conf=0.286 lift=1.15
```

## E1 · 메시지 계층

업종·공간·제품별 원문 메시지를 tagline → key message → proof point 로 묶는다.

```bash
python build/query.py E1 --vertical kr_hotel
```

```python
kb.E1(vertical="kr_hotel")
```

결과 요약(판단 `auto` [], 3 ms):

```
tagline: 고객 유치 경쟁력을 갖춘 미래형 호텔을 완성하다
- 새로운 경험 SMART 객실 솔루션 (sec_cc1068a90702792c) → ['IoT 기반의 기기 연동을 통해 경험하지 못했던 보다 편리한 객실 자동화']
- SmartThings 앱 하나로 객실 기기 제어는 물론 다양한 객실 자동화 서비스 제공 (스마트싱스 프로페셔널 솔루션) → []
- 투숙객 맞춤 콘텐츠 제공 (sec_eff3e1ccba5fbb7b) → ['LYNK Cloud 솔루션을 통해 투숙객 정보에 따라 맞춤형 콘텐츠 및 ']
- 호텔 운영에 최적화된 링크 클라우드 솔루션 (링크 클라우드 솔루션) → []
- 집에서 보던 OTT 콘텐츠를 객실 TV로 (sec_f24f7dfef3946cc3) → ['밀레니얼 세대들이 즐겨보는 OTT 콘텐츠를 객실에서도 자유롭게 감상하실 ']
- 강력한 몰입감과 편리함을 선사하는 호텔 맞춤형 TV (호텔TV) → []
```

## E2 · 테마로 메시지 찾기

문장과 비슷한 원문 메시지와 그 대상(제품·솔루션)을 찾는다.

```bash
python build/query.py E2 "에너지 절감과 원격 제어"
```

```python
kb.E2("에너지 절감과 원격 제어")
```

결과 요약(판단 `auto` [], 1380 ms):

```
[usp] 에너지 절감 제어 — 링크 제어기
[usp] 에너지 절감 제어 — 링크 제어기
[key_message] 에너지 절감 제어 — b.IoT 솔루션
[key_message] 공간별 쾌적 제어로 에너지 절감 실현 — sec_1ca552f35c2c1a4b
[proof_point] 실내 온도에 따라 냉방을 자동 조정하여 전기료 절감과 에너지 소비를 최소화하였으며 냉풍방지 제어를 통해 난방 — 중대형에어컨 냉난방 Bespoke
[proof_point] 실내 온도에 따라 냉방을 자동 조정하여 전기료 절감과 에너지 소비를 최소화하였으며 냉풍방지 제어를 통해 난방 — 비스포크 상업용 에어컨
```

## E3 · 컨텍스트 → 메시지 묶음

업종·공간·제품·타겟고객·요구사항(모두 선택)으로 원문 메시지를 헤드라인 → 핵심 메시지(+근거 문장) → 제품 메시지(제품군별) → 근거 사례(인용·KPI)로 뽑는다. 비워 둔 업종·공간·제품은 타겟고객·요구사항 문장에서 추론한다(A2·공간 키워드·A1, 가중치 0.5배). 점수 = Σ(가중치 × 일치도) ÷ Σ(쓴 항목 가중치), 가중치는 제품 0.35 · 업종 0.25 · 공간 0.2 · 타겟고객 0.15 · 문장 유사도 0.35(0.6×LSA + 0.4×토큰 포괄도). 같은 문장(여러 제품군 공통 문구)은 하나로 묶고 `dup` 에 개수를 남긴다. 결과 문장은 모두 원문 그대로다.

```bash
python build/query.py E3 --vertical kr_hotel --space guest_room --customer "비즈니스호텔 체인" --text "객실 TV를 통합 관리하고 투숙객 만족도를 높이고 싶어"
```

```python
kb.E3(vertical="kr_hotel", spaces=["guest_room"], customer="비즈니스호텔 체인",
      text="객실 TV를 통합 관리하고 투숙객 만족도를 높이고 싶어")
```

결과 요약(판단 `check` ['LOW_TIER'], 1503 ms):

```
가중치 {'product': 0.175, 'vertical': 0.25, 'space': 0.2, 'customer': 0.15, 'text': 0.35} · 빠진 항목 []
헤드라인: 고객 유치 경쟁력을 갖춘 미래형 호텔을 완성하다
핵심 0.536: 넷플릭스 시청 가능한 호텔 TV (호텔 · 넷플릭스 시청 가능한 호텔 TV) ← 업종 '호텔' 페이지 장면 / 같은 공간 장면 / 요구사항 유사 0.44
핵심 0.533: 강력한 몰입감과 편리함을 선사하는 호텔 맞춤형 TV (호텔TV) ← 업종 '호텔' 페이지 문구 / 공간 '객실' 장면 문구 / 요구사항 유사 0.43
핵심 0.519: 집에서 보던 OTT 콘텐츠를 객실 TV로 (호텔 · 집에서 보던 OTT 콘텐츠를 객실 ) ← 업종 '호텔' 페이지 장면 / 같은 공간 장면 / 요구사항 유사 0.38
핵심 0.498: 투숙객 맞춤 콘텐츠 제공 (호텔 · 투숙객 맞춤 콘텐츠 제공) ← 업종 '호텔' 페이지 장면 / 같은 공간 장면 / 요구사항 유사 0.31
핵심 0.494: 호텔 운영에 최적화된 링크 클라우드 솔루션 (링크 클라우드 솔루션) ← 업종 '호텔' 페이지 문구 / 공간 '객실' 장면 문구 / 요구사항 유사 0.30
제품 0.45: 호텔 TV CU700 시리즈 — 체계적인 호텔 관리를 위한 통합 클라우드 플랫폼
제품 0.406: 호텔 TV HU7000F 시리즈 — 투숙객은 객실 내 TV에서 영화, TV 프로그램, 사진 등 좋아하는 콘텐
제품 0.347: 호텔 TV HU8000F 시리즈 — 전 객실 모든 투숙객들에게 몰입감 넘치는 시청각 경험을 선사하세요. 10
사례 0.817: IBC 호텔 – 삼성 TV (더 프레임) / 삼성 호텔 TV / 삼성 시 ← 선택 제품을 쓴 사례 / 업종 사례 / 같은 공간 사례
사례 0.692: 신라스테이 서초 – 호텔 TV, 시스템에어컨, 터보 냉동기 ← 업종 사례 / 같은 공간 사례 / 고객 유형 '프리미엄 비즈니스 호텔(체인)'
사례 0.682: 크라운 파크 호텔 서울 - 삼성 호텔 TV ← 업종 사례 / 같은 공간 사례 / 고객 유형 '비즈니스호텔'
```

## E3 · 컨텍스트 → 메시지 묶음(요구사항 문장만)

업종·공간·제품을 비우면 문장에서 추론한다. 추론한 값은 `context.*.from = inferred` 와 `needs_confirmation` 으로 표시된다.

```bash
python build/query.py E3 --text "호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어"
```

```python
kb.E3(text="호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어")
```

결과 요약(판단 `check` ['LOW_TIER'], 159 ms):

```
업종 {'id': 'kr_hotel', 'name': '호텔', 'from': 'inferred'}
공간 [('guest_room', '객실'), ('lobby', '로비')]
제품 [('TV', 'TV'), ('스마트 LCD 사이니지 > 비디오월', '비디오월')]
확인 ['claim(수치·최상급) 문구는 대외 사용 전 원문 확인', '사례 인용(T5)은 사례 원문에서 확인', '문장에서 추론한 업종·공간·제품이 맞는지 확인']
핵심 0.624: 투숙 만족도를 높이는 로비 공간 ← 장면 항목에 선택 제품 / 업종 '호텔' 페이지 장면 / 같은 공간 장면
핵심 0.52: 넷플릭스 시청 가능한 호텔 TV ← 업종 '호텔' 페이지 장면 / 같은 공간 장면 / 요구사항 유사 0.47
핵심 0.503: 강력한 몰입감과 편리함을 선사하는 호텔 맞춤형 TV ← 업종 '호텔' 페이지 문구 / 공간 '객실' 장면 문구 / 요구사항 유사 0.43
핵심 0.467: 집에서 보던 OTT 콘텐츠를 객실 TV로 ← 업종 '호텔' 페이지 장면 / 같은 공간 장면 / 요구사항 유사 0.36
```

## G1 · 공간 × 카테고리 배치 이미지

공간 맥락이 있는 이미지를 등급(A > A?C > …) 순으로. 없으면 공간만 → 카테고리 맥락 → 제품 컷 순으로 폴백하고 `fallback_level` 을 붙인다.

```bash
python build/query.py G1 guest_room --category cat_hotel-tvs
```

```python
kb.G1("guest_room", category="cat_hotel-tvs")
```

결과 요약(판단 `auto` [], 40 ms):

```
수준 space+category
[A] https://images.samsung.com/kdp/cms_contents/108882/7e4b7164-6e66-4514-aacd-cb4423a1b92f.jpg · 호텔의 객실 침대 정면 벽면에 호텔TV가 설치되어 있고 화면으로 우주비행 · 예시 사진(삼성 공식 이미지) · https://www.samsung.com/sec/business/hotel-tvs/hoteltv-hu700
[A?C] https://images.samsung.com/kdp/cms_contents/108882/6b6bc4f4-6c20-411f-8758-bc8788023f26.jpg · 총 4개의 주요 특장점을 각각의 이미지와 함께 보여줍니다. 링크 클라우드 · 예시 사진(삼성 공식 이미지) · https://www.samsung.com/sec/business/hotel-tvs/hoteltv-hu700
[A?C] https://images.samsung.com/kdp/business/hospitality/ci_slide1_3_obj.png · 호텔 맞춤형 TV 안내 이미지 · 예시 사진(삼성 공식 이미지) · https://www.samsung.com/sec/business/hospitality/
[A?C] https://images.samsung.com/is/image/samsung/p5/sec/business/hospitality_2020/ci_slide2_2_obj.png · 호텔 맞춤형 TV 안내 이미지 · 예시 사진(삼성 공식 이미지) · https://www.samsung.com/sec/business/hospitality/
```

## images · 이미지 검색

alt·캡션·섹션·맥락 엔티티로 만든 이미지 문서를 검색한다.

```bash
python build/query.py images "사무실 천장 무풍 시스템에어컨"
```

```python
kb.image_search("사무실 천장 무풍 시스템에어컨")
```

결과 요약(판단 `auto` [], 71 ms):

```
[A] 2분할의 이미지로 구성되어 있습니다. 좌측 이미지에는 사무실 공간에 두사람이 서서 회의를 하는 모습이며, 그 · 오픈 오피스
[A] 모던한 그레이톤 사무실 공간이 보여지며, 이미지 좌측에는 천장에 설치된 무풍 시스템에어컨 4way의 필터 및 · 오픈 오피스
[A] 모던한 그레이톤 사무실 공간이 보여지며, 이미지 좌측에는 천장에 설치된 무풍 시스템에어컨 4way의 필터 및 · 오픈 오피스
[A] 모던한 그레이톤 사무실 공간이 보여지며, 이미지모던한 그레이톤 사무실 공간이 보여지며, 이미지 좌측에는 천장 · 오픈 오피스
[A] 모던한 그레이톤 사무실 공간이 보여지며, 이미지 좌측에는 천장에 설치된 무풍 시스템에어컨 4way의 필터 및 · 오픈 오피스
```

## search · 하이브리드 검색

trigram BM25 + 2글자 토큰 부분일치 + LSA 벡터를 RRF 로 합치고 토큰 포괄도로 재정렬한다. 결과마다 원문 URL·섹션.

```bash
python build/query.py search "병상 태블릿 환자 소통"
```

```python
kb.search("병상 태블릿 환자 소통")
```

결과 요약(판단 `auto` [], 144 ms):

```
1.0 industry · 병상 태블릿 하나로 환자와의 소통 해결 · 병상 태블릿 하나로 환자와의 소통 해결
환자의 침대에 설치된 개인용 태블릿을 통해 TV시청
1.0 industry · 환자 중심 소통 · 환자 중심 소통
입원실에서도 고해상도 TV 와 병상용 태블릿을 통해 다양한 의료 정보 안내
1.0 industry · 병상 태블릿 하나로 환자와의 소통 해결 > 병상용 태블릿 · 병상용 태블릿
다양한 병원 생활 안내 및 멀티미디어 시청
다양한 병원 생활 안내 및 멀티미
0.5 industry · 정확한 환자 상태 판단을 위한 진료실 > 태블릿 전자차트 · 태블릿 전자차트
자세히 보기
0.5 industry · 정확한 환자 상태 판단을 위한 진료실 > 태블릿 전자차트 · 태블릿 전자차트
모바일 기반 환자상태 보기
정확한 환자 상태 판단을 위한 시각적 편안함과 
엔티티: ['병실', '병원', '태평전통시장 - 삼성 태블릿', '갤럭시 탭', '차량 내부']
```

## entity · 엔티티 통합 보기

흩어진 정보(언급 문서, 메시지, 그래프 엣지)를 한 엔티티에 모은다.

```bash
python build/query.py entity solution sol_magicinfo
```

```python
kb.entity("solution", "sol_magicinfo")
```

결과 요약(판단 `auto` [], 4 ms):

```
out: {k: len(v) for k, v in r['result']['edges_out'].items()} = {'DESCRIBED_BY': 1, 'SOLD_AS': 1}
in: {'ABOUT': 14, 'DEPICTS_PROBABLE': 6, 'FEATURED_BY_SITE': 10, 'MENTIONS': 15, 'USES': 16}
- pdp · MagicINFO™ | 사이니지 솔루션ㅣSamsung Business 대 · 18회
- solution · MagicINFO™ | 사이니지 솔루션ㅣSamsung Business 대 · 15회
- case_study · 쉐라톤 서울 디큐브시티 호텔 – 삼성 스마트 사이니지(홍보용), 매직인포 · 14회
- case_study · NFT아트갤러리 청담 – 스마트 사이니지 + MagicINFO 솔루션 · 8회
- case_study · NH농협은행 - 스마트 LED 사이니지 + MagicINFO솔루션 · 6회
- industry · 건설 | 업종별 제안 | Samsung Business 대한민국 · 6회
```

