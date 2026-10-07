# Winmate · 공간 조감도 PoC

웹앱 시나리오 ②(이미지 · 조감도)의 **공간 조감도** 부분만 떼어 실험하는 PoC입니다.
작업 목록(BE0)부터 2D 경로(BP1–BP5)와 3D 경로(BR1–BR4)까지 시나리오 화면 순서대로 동작합니다.

| | 2D 조감도 | 3D 조감도 |
|---|---|---|
| 목적 | 정확한 수치 · 동선 · 제품 개수 | '이런 느낌으로 쓰이겠다'는 개략 |
| 누가 정하나 | **사용자**가 배치 · 수량 확정 (AI는 추천 · 경고) | **AI**가 요구사항 분석 → Blender로 인테리어 · 가구 선정 · 배치 · 렌더 |
| 결과 | 치수 도면(SVG/PDF 인쇄) · 수량표(xlsx/csv) · DXF · 존 · 동선 | 렌더 PNG/JPG(항상 'AI 생성 · 개략') · 출처 메타데이터 |

## 실행

```bash
cd winmate/poc/birdseye
python3 run.py --open          # http://127.0.0.1:8710
```

- **Python 3.9+, 표준 라이브러리만** 씁니다. `pip install` 이 필요 없고 Docker 도 쓰지 않습니다.
- 처음 켜면 샘플 작업 4개(2D 로비 · 2D 병원 · 3D 로비 · 3D 관제실)를 만듭니다. 처음 상태로 되돌리려면 `python3 run.py --reset-samples` 또는 작업 목록의 '샘플 다시 만들기'.
- 환경만 점검: `python3 run.py --check` (키 값은 출력하지 않고 '있음/없음'만 보여줘요)
- 다른 PC에서 보려면 `--host 0.0.0.0`, 포트는 `--port` 또는 `.env` 의 `BIRDSEYE_PORT`(기본 8710 — winmate 앱 8700과 겹치지 않게).

### 3D 렌더에 필요한 것: Blender

- Blender 4.2 이상(5.x 확인)을 설치하면 `/Applications/Blender.app` 을 자동으로 찾습니다.
- 다른 위치면 `.env` 에 `BLENDER_PATH=/경로/Blender` (앱 실행 파일) 또는 `BPY_PYTHON=/경로/python` (`pip install bpy` 한 파이썬).
- Mac(Apple Silicon)은 Metal GPU 를 자동으로 씁니다. 사이드바 아래 '실행 환경'에서 버전 · 장치를 확인할 수 있어요.
- 품질: 빠른 미리보기 960×540 · 기본 1600×900 · 고해상도 3840×2160. CPU 2코어 기준 기본 품질이 컷당 약 4분이었어요(GPU 는 훨씬 빠름).

## 설정 (`.env`)

winmate 루트의 `.env` 를 **그대로** 읽습니다(PoC 폴더에서 위로 올라가며 찾음, 환경 변수가 우선). 이미 있는 키를 씁니다:

| 키 | 쓰는 곳 |
|---|---|
| `GEMINI_API_KEY` · `LLM_*` · `I2T_*` · `GEMINI_THINKING_LEVEL` | 3D 요구사항 분석 · 말로 수정 · 존 문구(LLM), 도면 인식 · 현장 사진(I2T) |
| `LLM_PROVIDER=gemini \| openai_compat \| internal` + `LLM_BASE_URL` | 사내 모델로 바꿀 때 (OpenAI 호환 `/v1/chat/completions`) |
| `*_ALLOW_CONFIDENTIAL` · `UPLOAD_DEFAULT_CONFIDENTIAL` | 기밀 작업 · 업로드는 허용된 경우에만 외부 모델로 보냄 |
| `MODEL_MODE=live \| record \| replay \| mock` · `MODEL_CASSETTE_DIR` | 모델 응답 녹화/재생(`<cassette>/birdseye/`) |
| `MODEL_CALL_LOG` | 호출 기록 `data/birdseye/model_calls.jsonl` (`full` 이면 프롬프트 · 응답 포함) |
| `DATA_DIR` · `WKB_KB` · `UPLOAD_MAX_MB` | 작업 저장 위치(`DATA_DIR/birdseye`), winmate-kb 위치, 업로드 한도 |

조감도 PoC가 새로 쓰는 키(없으면 기본값):

```ini
BIRDSEYE_PORT=8710
BIRDSEYE_MODEL_MODE=          # 비우면 MODEL_MODE 를 따름 (조감도만 mock/replay 로 돌릴 때)
BIRDSEYE_DATA_DIR=            # 비우면 DATA_DIR/birdseye
BIRDSEYE_RENDER_WORKERS=1     # 동시에 돌릴 렌더 수(1–2)
BLENDER_PATH=                 # 비우면 /Applications/Blender.app 자동 탐색
BPY_PYTHON=                   # bpy 모듈 파이썬(앱 대신)
RENDER_ENGINE=cycles          # cycles | eevee
RENDER_DEVICE=auto            # auto(GPU 있으면 GPU) | cpu
RENDER_THREADS=0              # 0 = 자동
RENDER_TIMEOUT_S=1800
```

모델이 없거나(키 없음 · 기밀 차단 · 호출 실패) 응답이 이상하면 **지어내지 않고** 규칙 기반으로 진행합니다.
화면에는 'AI 결정' 대신 '규칙 결정', 도면 · 사진은 '읽지 못했어요 — 이유'로 표시돼요.

## 화면 ↔ 코드

| 화면 | 파일 | 서버 API |
|---|---|---|
| BE0 작업 목록 | `web/js/screens/list.js` | `GET /api/projects` |
| BP1 공간 · 치수 | `bp1_space.js` | `PUT /api/projects/<id>` |
| BP1D 도면 인식 | `bp1d_plan.js` | `POST /api/2d/plan` (I2T) |
| BP2 제품 · 수량 | `bp2_products.js` | `POST /api/2d/recommend`, `/api/2d/suggest`, `GET /api/catalog` |
| BP3 배치 · 동선 | `bp3_layout.js` + `plan.js` | `POST /api/2d/layout · validate · fix · autofix · fixtures · nl` |
| BP3Z 존 구획 | `bp3z_zones.js` | `POST /api/2d/zones · zone_points` |
| BP4 완성 | `bp4_done.js` | `GET .../drawing.svg · qty.json`, `POST .../to3d` |
| BP5 내보내기 | `bp5_export.js` | `POST .../export.zip`, `GET .../payload.json` |
| BR1 요구사항 | `br1_brief.js` | `POST .../patch`, `POST .../render` |
| BR1P 현장 사진 | `br1p_photos.js` | `POST /api/3d/photos` (I2T) |
| BR2 AI 구성 · 렌더링 | `br2_build.js` | `GET /api/jobs/<jid>` (1초마다) |
| BR3 결과 · 다른 안 | `br3_result.js` | `POST .../alternatives`, `.../alternatives/<alt>/pick` |
| BR3V 시점 · 조명 컷 | `br3v_cuts.js` | `POST .../render {mode: cuts}` |
| BR4 내보내기 | `br4_export.js` | 브라우저에서 ZIP(`zip.js`) + `provenance.json` |
| 유스케이스 맵 | `usecase.js` | — |

## 구조

```
run.py                     실행 · 샘플 설치 · 환경 점검
birdseye/
  config.py                .env 읽기(winmate 루트) · 서비스별 모델 설정
  catalog.py               제품 카탈로그 — seed/products.json + winmate-kb(읽기 전용 SQL)
  rules.py  seed/placement_rules.json   배치 룰 18개(PlacementRule 형식, status=draft)
  space.py geometry.py     좌표계 · 벽 · 개구부 · 다각형(SAT)
  layout2d.py              F2 배치 전략(창면 · 기둥 · 미디어월 · 스탠드 · 비디오월 · LED · 벽부 · 리듬 · 길 안내 · 냉난방)
  furnish.py               집기 배치(2D 동선 검토 블록 = 3D 가구 위치)
  zones.py                 존 제안 · 동선 순서 · A* 동선 · 통로 폭
  validate.py              F4 검증(겹침 · 높이 · 설치 · 전원 · 시야각 · 크기 · 문 앞 · 통로) + 자동 조정 + 화면용 geom
  drawing.py exporters.py  도면 SVG(A3/A4 · 표제란) · xlsx · csv · DXF · 제안서 데이터 · ZIP
  llm.py vision.py         모델 클라이언트(단계적 요청 낮추기 · 녹화/재생) · 도면/사진 읽기 · 말로 수정 · 존 문구
  analyze3d.py scene3d.py  3D 요구사항 분석(브리프) · 씬 명세
  blender/                 Blender 안에서 도는 스크립트(방 · 가구 · 재질 · 조명 · 카메라 · 품질 확인 · 'AI 생성 · 개략' 표시)
  pipeline3d.py jobs.py    BR2 6단계 작업 · 진행률
  kbref.py                 참고 사례(winmate-kb 공간 배치 이미지, 원문 링크 · 캡션 규칙)
  server.py                HTTP API + 정적 웹
web/                       화면(프레임워크 · CDN 없음)
samples/                   3D 샘플 렌더(이 파이프라인 결과)
tests/                     python3 -m unittest discover -s tests
tools/make_seed.py         winmate-kb 에서 제품 시드 다시 뽑기(--kb)
```

## 실험 포인트

- **룰 계수**: `birdseye/seed/placement_rules.json` 의 `params` 를 바꾸면 권장 수량 · 경고가 바로 바뀝니다. 근거 팝오버(BP2 ⓘ)에 룰 ID · 식 · 값이 그대로 보여요.
- **2D 편집**: 끌기(스냅) · R 회전 · 방향키 · ⌘Z, 경고마다 '고치는 방법' 버튼과 '경고 모두 자동 조정'. 벽 · 창 제품은 벽을 따라서만(Alt 로 자유 이동).
- **2D → 3D**: BP4/BP5 '이 배치로 3D 조감도 만들기' — 제품 위치 · 대수는 2D 그대로, 가구 · 마감 · 조명만 AI가. 2D 존 번호가 렌더 위에 Blender 카메라 투영으로 표시돼요.
- **모델 비교**: `BIRDSEYE_MODEL_MODE=mock` 으로 규칙 기반, `live` 로 Gemini — 같은 요구사항의 브리프(BR2 'W가 정한 구성')를 비교. `record` 로 녹화하면 `replay` 로 같은 응답을 다시 쓸 수 있어요.
- **3D 편집은 최소**: 시점 · 조명 프리셋, 도입 전 컷, 한 줄 요청(예: "더 밝고 미니멀하게, 플랜터는 빼고"), 다른 안 2개.

## 데이터 · 출처

- 제품 22종: winmate-kb 추출(2026-10-04) — 치수 · 전력은 samsung.com/sec/business 원문 값 그대로, 짧은 이름 · 설치 방식만 PoC 큐레이션. KB가 연결되면(`WKB_KB`) 검색에서 KB 제품도 나와요.
- 3D 제품 외형은 KB 스펙 치수로 만들고 품질 확인에서 오차를 잽니다. 화면 콘텐츠는 일반 패턴(상표 · 로고 없음).
- 가구 · 마감 라이브러리(`seed/furniture.json` · `materials.json`)와 룰 계수는 **PoC 임시값**입니다.
- 렌더 표시 글꼴: Noto Sans CJK KR 일부 글자(OFL, `birdseye/fonts/OFL.txt`).

## 한계 · 확인 못 한 것

- **Gemini 실호출은 이 PoC 개발 환경에서 막혀 있어 확인하지 못했어요.** 요청 형식은 문서 기준이고, 거절되면 단계적으로 낮춥니다(responseJsonSchema+thinking → schema → JSON만). 가짜 전송으로는 테스트했어요.
- 공간은 직사각형만(도면 인식도 가장 큰 직사각형으로 단순화).
- PDF 는 브라우저 인쇄로(도면 SVG는 종이 mm 단위라 100% 인쇄 시 축척이 맞아요). 서버에 래스터 도구가 없어 PNG 는 브라우저에서 그립니다.
- 렌더 진행률: Blender 앱은 샘플 수로, bpy 모듈은 시간으로 어림합니다.
- 제안서 · 시나리오 · Spec 시트 · 이미지 생성 화면은 범위 밖 — 넘길 데이터(`proposal_payload.json`, `proposal_images.json`)만 만듭니다.
- 작업 저장은 JSON 파일(`DATA_DIR/birdseye/projects/<id>/`), 렌더 작업 상태는 메모리 — 서버를 다시 켜면 진행 중이던 렌더는 사라져요.

## 사내망 이전 메모

외부 CDN · 웹 폰트 없음, 서버는 표준 라이브러리 HTTP 서버, 모델은 `LLM_PROVIDER=openai_compat` + `LLM_BASE_URL` 로 사내 모델에 붙일 수 있어요. 기밀 플래그가 켜진 작업 · 업로드는 `*_ALLOW_CONFIDENTIAL=true` 일 때만 모델로 보냅니다.

## 테스트

```bash
python3 -m unittest discover -s tests                     # 36개(룰 · 배치 · 검증 · 동선 · 내보내기 · 모델 · 3D 씬 · API)
BIRDSEYE_TEST_BLENDER=1 python3 -m unittest tests.test_scene3d   # + 실제 Blender 작은 렌더
```
