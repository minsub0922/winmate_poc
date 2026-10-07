# PPT 레이아웃 구현 지시서 — 디자인 보드와 똑같이 나오게

이 문서는 **코드 에이전트에게 그대로 주는 작업 지시서**다. 사내망(인터넷 · claude.ai 없음)에서 진행할 수 있다.
먼저 저장소 루트 `AGENTS.md` · `BOOTSTRAP.md` 의 1~3단계(환경 · 스택 · 시험)가 끝나 있어야 한다.

## 0. 목표와 원칙

- 목표: export 서비스가 만드는 PPTX 슬라이드가 **디자인 보드(원본 캔버스)와 같은 레이아웃 · 같은 시각 요소**로 나온다.
  1. 이미 등록된 출시(ready) 템플릿 381종의 모양을 보드와 맞춘다(Phase A).
  2. 「05 시나리오 커버리지 · 보강 레이아웃」 캔버스의 62장을 템플릿으로 추가한다(Phase B).
  3. 제안서가 새 섹션(00 제안 개요 · 09 실행 계획 · 10 비용)과 새 시트 유형을 쓰게 한다(Phase C).
- **claude.ai 아티팩트 링크는 열지 않는다**(사내망에서 인증서 오류). 디자인 원본은 모두 저장소에 있다(아래 §1).
- 보드 HTML 을 PPTX 에 그대로 옮길 수는 없다. export 는 **원형(archetype) + 매개변수**로 다시 그린다(`services/export/src/winmate_export/templates/archetypes.py`).
  보드에서 좌표 · 색 · 글자 크기를 재서 원형을 고치거나 새 원형을 만든다.
- 서비스 경계: 템플릿 · 그리기는 **export**(`services/export/**`), 제안서 섹션 · 시트 유형 선택은 **proposal**(`services/proposal/**`).
  서로의 코드는 고치지 않고 계약(`contracts/*.json`)과 `docs/requests/*.md` 로 주고받는다.
- 사실을 지어내지 않는다. 보드의 예시 값(고객명 · 수치)은 시험용 예시로만 쓴다.

## 1. 디자인 원본(저장소 안)

| 무엇 | 경로 |
|---|---|
| 캔버스 6개 원본(템플릿 · 예시 데이터 · 인라인 스타일) | `docs/templates/source/{common,mi,vp,ss,pi,cov}/*.dc.html` · `SOURCE.json` · `canvas.json` |
| 그린 그림 · 글자(값이 채워진 상태, 1280×720) | `docs/templates/_rendered/<캔버스>/<보드>.jpg` · `.txt` |
| 살아 있는 보드 보기 | `python3 -m http.server 5099 --directory docs` → `http://localhost:5099/templates/source/cov/L_CO_B.dc.html` |
| 다시 그리기 | `node docs/screens/_runtime/render.mjs templates` |
| 템플릿 카탈로그(기계용 · 사람용) | `services/export/src/winmate_export/templates/catalog.json` · `docs/templates/CATALOG.md` |
| 05 캔버스의 상황 132개 점검표 · 섹션 배치 | `docs/templates/_rendered/cov/Main.txt` · `SCN_*.txt`(서비스별) · `SCN_MAP.txt`(섹션 구조 · 넣는 신호 — ● ○ 표시는 그림이라 글자에 없다 → 아래 §5 표) |

보드 하나를 볼 때는 `.jpg`(모양) → `.txt`(글 · 예시 값) → `.dc.html`(정확한 px · 색 · `renderVals` 예시 데이터) 순서로 본다.

## 2. 비교 도구

```bash
make up                                     # 스택(export · files · gateway)
export SOFFICE_PATH=$(command -v soffice)   # LibreOffice 필요(PPTX → PDF → PNG)
uv run python services/export/scripts/compare_boards.py MS-B CM-A OP-B       # 몇 개
uv run python services/export/scripts/compare_boards.py --section why        # 섹션 하나
uv run python services/export/scripts/compare_boards.py --all                # ready 전부
# → data/ppt-compare/<시각>/<코드>.png(왼쪽 보드 | 오른쪽 export) · index.html · report.json
```

- 채울 값: `services/export/src/winmate_export/templates/board_slots/<코드>.json` 이 있으면 그것, 없으면 `example_slots`(모양만 맞춘 채움 글).
  **보드와 같은 내용으로 비교해야 차이를 판단할 수 있다** — 그래서 Phase A 는 board_slots 부터 만든다.
- 비교 그림은 이미지로 직접 열어 본다(코드 에이전트의 이미지 읽기). 사람에게 보여 줄 때는 `index.html`.

## 3. Phase A — 출시 템플릿 381종을 보드와 맞추기

섹션 하나씩(common → mi → vp → birdseye → space_products → solution → space_scenario → cases → why → spec → appendix) 진행한다.

1. 그 섹션의 코드 목록: `GET /api/export/v1/templates?section=<섹션>&status=ready&limit=100`.
2. 코드마다 `board_slots/<코드>.json` 을 만든다 — 보드 `.dc.html` 의 `renderVals()` 예시 데이터를 템플릿 슬롯 모양(`GET /templates/<코드>` 의 `slots` · `fields`)으로 옮긴다.
   이미지 칸은 비워 두거나(자리표시) 시험용 이미지 file_id. 업종판(예 MI-FB-A)은 같은 원형이면 대표 하나만 만들어도 된다.
3. `compare_boards.py --section <섹션>` → 그림을 보고 코드마다 판정해 `docs/templates/FIDELITY.md` 표에 적는다:
   `코드 · 원형 · 판정(같음 | 근사 | 다름) · 다른 점(빠진 요소 · 위치 · 색 · 글자) · 고칠 곳`.
   - 같음: 요소 · 배치 · 강조 색이 같고 위치 차이가 슬라이드 폭의 2% 안쪽.
   - 근사: 요소는 다 있으나 크기 · 간격 · 글자 크기 차이.
   - 다름: 보드의 고유 요소가 없다(예: 강조 열, 제품 사진 머리, 스윔레인 화살표, ROI 곡선 · 교차점, 단계 화살표, 아이콘).
4. 「다름」부터 고친다: `archetypes.py`(매개변수) · `render/pptx_draw.py`(도형 · 표 · 차트) · 필요하면 새 원형. 같은 원형을 쓰는 다른 코드도 다시 비교한다.
5. 섹션이 끝나면: `make test SERVICE=export`(+ `--check` 로 카탈로그 재생성 확인 `uv run python -m winmate_export.templates.build --check`) →
   커밋(`export: <섹션> 템플릿 보드 일치 — 같음 n · 근사 n · 다름 n`).
6. 시험을 더한다: `tests/test_board_fidelity.py` — board_slots 가 있는 코드마다 PPTX 를 만들고 **도형 수 · 주요 도형 위치(±2%) · 표/차트 종류**가
   기대값과 같은지(기대값은 고친 뒤의 결과로 고정, 보드에서 잰 값과 함께 주석).

## 4. Phase B — 05 캔버스 62장 추가

원본 `docs/templates/source/cov/L_*.dc.html`(62장) · 상황표 `SCN_*` · 배치 `SCN_MAP`.

1. 카탈로그에 캔버스를 등록한다: `templates/registry_data.py` 의 `CANVASES` 에 `cov`(제목 「Winmate PPT · 05 시나리오 커버리지 · 보강 레이아웃」).
2. 코드 · 역할 · 섹션 · 원형을 `registry_data.py` 에 등록한다.
   - 새 시트 역할 14: ES 제안 요약 · OV 사업 이해 · 범위 · 전제 · RM 요구 이해 · 대응 · RV 분양 · 입주민 가치 · OG 추진 체계 · IP 설치 · 시공 · IG 시스템 연동 ·
     PL 파일럿 · 확산 · CU 맞춤 개발 · SE 보안 · 인증 · 개인정보 · TO 교육 · 운영 이관 · MT 유지보수 · CO 비용 · 구매 방식 · QA 예상 질문.
   - 기존 역할 보강 31: C13 · MS-F · TR-D · CB-E · CB-F · CB-G · US-D · CH-D · VP-V · EF-F · EF-G · EF-H · EF-I · BV-E · BV-F · BV-G · SS-D · SS-E · SS-F ·
     CM-D · CM-E · ST-E · SD-D · SD-E · SD-F · SD-G · SC-D · SC-E · SC-F · AX-C · AX-D.
   - 「넣는 신호」(언제 이 장을 쓰나)는 `SCN_MAP.txt` · 각 `SCN_*.txt` 의 표에서 `when` · `description` 으로 옮긴다.
3. 원형: 기존 원형으로 그릴 수 있으면 매개변수만, 아니면 새 원형(예: 누적 막대 + 연도 표 + KPI 띠의 CO-B, RACI 표의 IP-B, 질문 카드 2×3 의 QA-A).
4. `board_slots/<코드>.json` 을 보드 예시 값으로 만들고 `compare_boards.py` 로 「같음」이 될 때까지 고친다(Phase A 기준).
5. 섹션 · 역할 이름표: 새 섹션 `overview`(00 제안 개요) · `execution`(09 실행 계획) · `cost`(10 비용)를 `templates/build.py` 의 `SECTION_ORDER` 에 넣는다
   (순서: 00 개요 → 01 MI → 02 VP → 03 조감도 · 시나리오 → 04 공간별 제품 → 05 솔루션 → 06 사례 → 07 Why Samsung → 08 스펙 → 09 실행 → 10 비용 → 부록 → 마무리 C13).
6. `uv run python -m winmate_export.templates.build` → `catalog.json` · `docs/templates/CATALOG.md` 갱신 → `make test SERVICE=export` →
   `make contracts SERVICE=export`(계약이 바뀌면) → 커밋.
7. proposal 에 알린다: `docs/requests/proposal.md` 에 「export 새 시트 유형 14 · 새 섹션 3 · 템플릿 62 — 코드 목록 · 넣는 신호 · 기본 넣음 규칙(SCN_MAP 표)」.

## 5. Phase C — 제안서가 새 섹션 · 시트를 쓰게(proposal 세션)

`services/proposal/AGENTS.md` · `docs/scenarios/10-proposal.md` · 보드 `docs/screens/_rendered/webapp3/PR3*.jpg`(시트 구성) 를 먼저 본다.

1. 섹션 정의(유형별 기본 구성)에 00 · 09 · 10 을 더한다. 유형마다 기본값은 아래 표(SCN_MAP 보드의 ● ○ 표시를 옮김 — ● 기본으로 넣음 · ○ 신호가 있으면 넣음 · — 넣지 않음, 사용자가 바꿀 수 있음).

   | 섹션 | 유형 | 템플릿 | 넣는 신호 | 표준 | 퀵윈 | Solution형 | RFP 대응 | 건설 · 주거 |
   |---|---|---|---|---|---|---|---|---|
   | 00 | ES 제안 요약 | ES-A · ES-B | 결정권자가 첫 장만 볼 때 · 경영진 보고 | ● | ○ | ● | ● | ● |
   | 00 | OV 사업 이해 · 범위 · 전제 | OV-A · OV-B · OV-C | RFP 양식 · 범위를 나눌 때 · 가정이 있을 때 | ○ | — | ○ | ● | ○ |
   | 00 | RM 요구 이해 · 요구 대응 | RM-A · RM-B · RM-C | 키맨이 여럿 · 요구 10개 이상 · 평가표 | ○ | — | ● | ● | ○ |
   | 02 | RV 분양 · 입주민 가치 | RV-A · RV-B · RV-C | 건설사 · 모델하우스 · 세대 타입별 옵션 | — | — | — | — | ● |
   | 09 | OG 추진 체계 | OG-A | 여러 회사 · 팀이 함께 수행할 때 | ○ | — | ○ | ● | ● |
   | 09 | IP 설치 · 시공 | IP-A · IP-B · IP-C | 현장 조건 · 공사 분담 · 야간 시공 | ● | ○ | ● | ● | ● |
   | 09 | IG 시스템 연동 | IG-A · IG-B | POS · PMS · BMS 등 고객 시스템과 연결 | ○ | — | ● | ● | ○ |
   | 09 | PL 파일럿 · 확산 | PL-A · PL-B | 시범 지점을 거쳐 전체로 넓힐 때 | ○ | ○ | ● | ○ | — |
   | 09 | CU 맞춤 개발 | CU-A · CU-B | 전용 에디션 · 개발 · 인증 · 출고 일정 | ○ | — | ○ | ○ | — |
   | 08 · 09 | SE 보안 · 인증 · 개인정보 | SE-A · SE-B · SE-C | 금융 · 공공 · 의료 · 화면에 개인정보 | ○ | — | ● | ● | ○ |
   | 09 | TO 교육 · 운영 이관 | TO-A · TO-B | 운영 인력이 따로 있을 때 · 구축 후 이관 | ○ | — | ● | ● | ○ |
   | 09 | MT 유지보수 | MT-A · MT-B | 점검 일정 · 케어 상품을 고를 때 | ● | ○ | ● | ● | ● |
   | 10 | CO 비용 · 구매 방식 | CO-A · CO-B | 구매 · 구독 · 렌탈 비교 · 5년 총비용 | ● | ● | ● | ● | ● |
   | 부록 | QA 예상 질문 | QA-A | 발표 · 평가 질의에 대비할 때 | ○ | — | ○ | ● | ○ |

   지금 제안서 유형은 표준 · 퀵윈 · Solution형 셋이다. 「RFP 대응」 · 「건설 · 주거」는 유형이 아니라 신호(RFP 로 시작 · 업종이 건설/주거)로 다룬다 — 새 유형으로 만들지는 사람에게 묻는다.
2. 「넣는 신호」를 규칙으로: 예) RFP 가 있으면 OV · RM · QA ●, 키맨 3명 이상이면 RM ○→●, 건설 · 주거 업종이면 RV ●, 고객 시스템(POS · PMS · BMS) 언급이면 IG ○.
   근거가 정의서 · RFP · Storyboard 에서 나오도록(지어내지 않음) 하고, 사용자가 시트 구성 화면(PR3)에서 바꿀 수 있게 한다.
3. 섹션 채우기(`section_fill`)에 새 역할의 슬롯 채우는 법(어떤 작업물 · 필드에서 오는지)을 더한다. 근거 없는 값은 `[확인 필요]`.
4. 화면: PR3 시트 구성 · 섹션 작성 · 미리보기에서 새 섹션이 보이게. `make e2e-feature SERVICE=proposal` + 통합 e2e(`e2e/integration`) 통과.
5. `services/proposal/AGENTS.md` 「현재 상태」 · `docs/requests/proposal.md` 상태 줄 갱신 → 커밋.

## 6. 끝낼 때

- `docs/templates/FIDELITY.md`: 코드별 판정 표와 요약(같음 · 근사 · 다름 수, 남은 「다름」 목록과 이유).
- 회귀: `make contracts-check` · `make test` · 제안서 e2e · 통합 e2e.
- 보고: Phase 별 결과(숫자) · 커밋 목록 · 사람이 정해야 할 것(예: 보드끼리 서로 다른 규칙, 그릴 수 없는 요소의 대안).
