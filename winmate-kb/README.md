# Winmate KB — samsung.com/business 지식 DB (v1)

Winmate(삼성 B2B 제안서 어시스턴트)가 업종·공간·요구사항으로부터 제품·솔루션·메시지·이미지·사례를 **근거와 함께** 꺼내 쓰도록
samsung.com/business(KR, 일부 US)를 수집해 만든 SQLite 지식 DB 다. DB·KB·문서와 검증용 대시보드(`dashboard/`)까지 들어 있고,
LLM API 를 쓰는 RAG 는 다음 단계다. 모든 질의는 LLM 없이 결정적으로 동작한다.

- 수집 시각: 2026-10-04 (KST 15:51~17:20)
- DB: `kb/winmate_kb.sqlite`(191 MB), 벡터 모델: `kb/models/lsa_char24_v2.joblib`(28 MB)
- 시나리오 테스트 41/41 통과, 품질 프로브 23/23 통과(`docs/SCENARIO_TEST_REPORT.md`, `docs/BUILD_REPORT.md`)

## 무엇이 들어 있나

| 영역 | 내용 |
|---|---|
| 제품 | 카테고리 3단계(최상위 9 · 사이트 목록 53 · 하위 분류 138), 상품 카드(제품군) 605, 모델코드 1,067, 목록 필터 태그 1,215(공식 그룹·라벨) |
| 스펙 | 모델 929개의 스펙 원값 47,490행 + 정규 키(크기·밝기·해상도·사용 시간·냉난방 능력·IP 등급 등) |
| 특장점 | PDP 특장점 컴포넌트 9,676(헤드라인·본문·면책 문구 분리) |
| 업종 | KR 업종 22(상위 10·하위 17), US 13, Winmate 16 세그먼트 대응(초안) |
| 업종 장면 | KR 업종 페이지 17개의 히어로 17 · 장면 155 · 장면 항목 287(링크로 제품·솔루션 해소) · 추천 솔루션 39 · 사례 링크 68, US 섹션 273 |
| 공간 | 공간 유형 70(시드 54 + 관측 16), 사이트 공간 라벨 → 공간 유형 대응 |
| 역량 | 역량 15, 자동 presence 규칙 13 → 제품군 역량 206건(근거 문장 포함) |
| 사례 | 도입사례 218(페이지 198), 사이트 '관련 제품' 링크 304, 공간·요구·KPI(이전 세션 추출) |
| 메시지 | 원문 그대로의 tagline 17 · key message 6,776 · proof point 6,177 · USP 1,729 |
| 이미지 | 이미지 자산 10,251(PC/MO 묶음) · 등장 15,065 · 1차 등급 힌트(A 2,140 · A?C 3,699 · C · D · E) |
| 해소·그래프 | 별칭 3,314, 언급 32,598(모델코드 정확 일치 1,107 포함), 그래프 엣지 36,014 |
| 검색 | 원문 청크 24,346(FTS5 trigram) + 엔티티·이미지 검색 문서 + LSA 벡터 35,775 |

모든 사실 행에 출처(`source_occurrence_id` → 원문 블록 → URL·섹션), 근거 등급(`source_tier`), 방법(`method`)이 붙는다.

## 폴더

```
README.md                  이 문서
requirements.txt           pyyaml, numpy, scikit-learn, joblib
kb/winmate_kb.sqlite       지식 DB
kb/models/                 LSA 벡터 모델(질의 임베딩용)
raw/                       수집 원본(JSON 6개, 26 MB)
seed/                      온톨로지 시드(업종·공간·카테고리·솔루션·역량·배치 규칙·시트 역할)
collect/                   브라우저 수집 스크립트와 실행 순서
build/
  schema.sql               스키마
  build_kb.py              raw + seed → DB (결정적 파서·해소·KG·청크)
  curation.py              사람이 검수하는 사전·규칙(공간 라벨, 별칭, 자동 역량 규칙, 업종 페이지 파서, 이미지 등급 규칙)
  index_kb.py              검색 인덱스(엔티티·이미지 FTS, LSA 벡터)
  query.py                 질의 패턴 라이브러리 + CLI
  qa.py                    DR 커버리지·시나리오 상태·품질 프로브 → docs/BUILD_REPORT.md
  sql.py                   간단한 SQL 실행기
  compare_db.py            두 DB 를 표 단위로 비교(재현 확인)
  run_all.sh               전체 재빌드
dashboard/                 검증 대시보드(정적 페이지 + 브라우저 질의 엔진, dashboard/README.md)
tests/
  test_scenarios.py        시나리오 테스트 → docs/SCENARIO_TEST_REPORT.md
  make_cookbook.py         질의 예시 → docs/QUERY_COOKBOOK.md
  make_fixture.py          스모크 테스트용 합성 픽스처
docs/
  DATA_DICTIONARY.md       표·컬럼·근거 등급·ID 규칙·그래프 관계
  SOURCE_REPORT.md         수집한 것·못 한 것·사이트 특성
  QUERY_COOKBOOK.md        질의 패턴별 실제 실행 예시
  BUILD_REPORT.md          적재 건수·DR 커버리지·시나리오 상태·프로브(자동 생성)
  SCENARIO_TEST_REPORT.md  시나리오 테스트 결과와 출력 예시(자동 생성)
  CURATION_GUIDE.md        사람이 고치는 곳과 검수 우선순위
  REPRODUCE.md             재현 가이드: raw → 단계별 정제 → 표, 같은 바이트로 다시 빌드·확인하는 법(코드 에이전트용)
```

## 바로 써 보기

```bash
pip install -r requirements.txt

python build/query.py S1 "호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어"
python build/query.py B1 kr_hospital                      # 업종 프리셋(공간 시퀀스·장면·추천)
python build/query.py G1 guest_room --category cat_hotel-tvs   # 객실 × 호텔TV 배치 이미지
python build/query.py search "병상 태블릿 환자 소통"
python build/query.py entity solution sol_magicinfo
python build/query.py E3 --vertical kr_hotel --space guest_room --customer "비즈니스호텔 체인" --text "객실 TV 통합 관리"   # 컨텍스트 → 메시지
python build/sql.py "SELECT title, space_label FROM industry_section WHERE vertical_id='kr_hotel'"
```

```python
import sys; sys.path.insert(0, "build")
from query import KB
kb = KB()
r = kb.S1("매장 입구 쇼윈도에 햇빛에서도 잘 보이는 사이니지")
r["result"]["by_space"][0]["families"][0]["reasons"]
```

다시 빌드: `bash build/run_all.sh` (약 2분). 같은 raw/ 로 같은 바이트의 DB 가 나온다 — 확인 방법과 단계별 설명은 [`docs/REPRODUCE.md`](docs/REPRODUCE.md).

- 벡터 모델은 scikit-learn 1.9 로 저장했다. 다른 버전에서도 동작하지만(1.7.2 에서 시나리오 테스트 통과 확인), 버전 경고가 신경 쓰이면 `python build/index_kb.py` 로 다시 만든다.

## 검증 대시보드

`dashboard/`는 이 DB 를 브라우저에서 바로 검증하는 페이지다(claude.ai 아티팩트로 게시).

- 탭: 개요(테스트·프로브·DR) · 질의(요구사항→추천, 원문·이미지 검색, 업종 판별) · 컨텍스트 → 메시지 · 업종 장면 · 제품 · 도입사례 · 이미지 · 메시지 · 검수
- 질의는 `dashboard/src/engine.js`(= `build/query.py` 이식)로 브라우저에서 계산한다. Python 과 같은 입력 73개(문장 57 + 컨텍스트 16)로 맞춰 보면 요구사항 1순위 제품·업종 판별·공간·역량·솔루션, 컨텍스트 해석·메시지 순위가 100% 같다(`dashboard/build/parity.json`).
- 이미지 썸네일(10,219장 · KB 이미지의 99.7%)은 데이터로 함께 싣고 보이는 묶음만 받는다.
- 항목마다 ✓ ✗ ? ✎ 검수 표시를 남기면 페이지를 여는 사람끼리 공유된다(아티팩트 저장소 `reviews`).
- 다시 만들기: `bash dashboard/run.sh --b64` 후 게시.

## 시나리오별 상태

| 시나리오 | 상태 | 이번 버전에서 되는 것 | 막힌 것 |
|---|---|---|---|
| S1 요구사항 → 제품 | 부분 | 절 단위로 공간·카테고리·역량을 묶어 공간별 후보, hard 역량 필터, 근거(규칙·사이트 추천·선례), 유사 사례 | 역량 규칙·공간 요구가 초안, 임계값 규칙 미승인 |
| S2 업종·공간 → 장면 | 부분 | 업종 페이지 장면(공간·항목·메시지·이미지) + 유사 사례 | 이미지 VLM 판정 전 |
| S3 공간 → 제품 리스트 | 부분 | 공간별 사이트 추천 + 역량 + 선례로 순위 | 수량·티어(배치 규칙 없음) |
| S4 메시지 | 준비됨 | 원문 그대로의 계층(tagline → key → proof), 출처, claim 표시, 컨텍스트(업종·공간·제품·타겟고객·요구사항) → 메시지 묶음(E3) | E3 가중치는 휴리스틱(검수로 조정) |
| S5 이미지 | 부분 | 공간 × 카테고리, 제품 설치 사진, 폴백, 이미지 검색 | VLM 판정 전(등급은 규칙 힌트) |
| S6 엔티티 통합 | 부분 | 언급·메시지·스펙·엣지 통합 | 세대·후속 모델 |
| S7 스펙 대응표 | 부분 | pass/fail/unknown 판정 | 단종·후속 |
| S8 유사 사례·KPI | 부분 | 분해 점수 유사 사례, KPI(이전 추출), 통계, 공존 | KPI 원문 대조 |
| S9 업종 판별 | 부분 | top-2 + ask | 세그먼트 대응 빈칸 |
| S10~S12, S14 | 소스 부족 | — | 호환 정보, 배치 기준, 과거 제안서, 카탈로그 |
| S13 RAG | 검색 층 준비 | 하이브리드 검색·근거 URL | LLM 답변 생성은 다음 단계 |

## 원칙과 한계

- 사실(이름·수치·문구)은 사이트 원문에서만 온다. 큐레이션 사전은 "어떻게 읽을지"만 정한다(`docs/CURATION_GUIDE.md`).
- 역량(`provides`)은 사이트 필터·스펙·문구에 무엇이 "있다"만 보는 규칙이라 초안이다. 휘도·IP·온도 같은 임계값 규칙은 파라미터가 비어 있어 실행하지 않는다.
- 이미지 등급은 페이지 유형·파일명·alt 문장 규칙으로 정한 1차 힌트다. alt 문장이 장면을 서술한 상품 상세 이미지는 공간까지 붙었다. VLM 판정은 `vlm_status=pending`.
- 벡터는 문자 n-gram LSA 다(빌드 환경에서 신경망 임베딩 모델을 받을 수 없음). 표와 모델 파일만 바꾸면 사내 임베딩으로 교체된다.
- e-카탈로그(robots 차단), 로그인 뒤 콘텐츠, 과거 제안서는 들어 있지 않다. 파일로 받으면 같은 구조로 붙일 수 있다(`docs/SOURCE_REPORT.md`).

## 다음 단계

1. 사람 검수: `provides` 근거, `requires`, 공간 라벨, 세그먼트 대응(`docs/CURATION_GUIDE.md` 우선순위).
2. e-카탈로그 PDF·과거 제안서를 받아 카탈로그 권장·세대·제안서 구조 추가.
3. LLM_API 연동: 임베딩 교체, 이미지 VLM 판정, RAG 답변(인용 검증) — kickoff 패키지의 M3 이후.
4. 대시보드 검수 결과(`reviews`)를 큐레이션 사전·규칙에 반영 → 재빌드.
