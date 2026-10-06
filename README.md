# Winmate

삼성 B2B 제안서 제작 어시스턴트(한국어 웹앱). 고객 요구사항 정리부터 전략 Storyboard · 시장/경쟁 분석 · Value Proposition ·
Spec 시트 · 이미지 · 공간 조감도 · 공간 시나리오를 거쳐 B2B 제안서(PPTX · PDF)까지, 지식 DB(winmate-kb)와 모델 API 를 근거로 만든다.
근거가 없는 사실은 지어내지 않고 `[확인 필요]` 로 남긴다.

## 구조

FastAPI 서비스 17개(플랫폼 7 + 기능 10)와 기능별 워커(LangGraph, Redis Stream 잡 큐), React · Vite 웹으로 이루어진다.
브라우저와 서비스 간 호출은 모두 게이트웨이(5000)를 거치고 OpenAPI 계약(`contracts/`)으로 검증한다. 외부 모델(LLM · I2T · T2I · 웹 검색)은
ai-tools 서비스만 부르며, `.env` 로 Gemini(맥 개발) ↔ 사내 API(사내망 운영)를 바꾼다. 저장은 서비스별 SQLite + 로컬 파일, 프로세스는
pm2(Docker 없음), 포트는 5000번대만 쓴다. 포트 · 역할 · 의존 관계는 [서비스 지도](docs/OPERATIONS.md#3-서비스-지도),
원본은 [`config/services.yaml`](config/services.yaml).

## 맥에서 시작하기

```bash
brew install uv node@24 redis          # node@24 는 PATH 에 추가 — docs/OPERATIONS.md 1.1
cp .env.example .env                   # GEMINI_API_KEY 채우기
make setup                             # 파이썬 · npm 의존성, 계약 · API 타입, 웹 빌드
make up && make health                 # pm2: Redis + 서비스 + 워커
open http://localhost:5000             # 웹 개발(HMR)은 make web-dev → http://localhost:5001
```

자주 쓰는 명령은 `make help`, 서비스 하나 개발 · 테스트 · 계약은 [AGENTS.md](AGENTS.md) §3.

## 문서

| 문서 | 내용 |
|---|---|
| [AGENTS.md](AGENTS.md) | 코드 에이전트 공통 규칙 · 통신 규칙 · 명령 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 원칙 · 서비스와 포트 · API 규약 · 잡(Redis) · 저장 · 웹 |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | 맥 개발 환경 · 사내망 오프라인 설치 · 백업 · 업그레이드 · 문제 해결 · 서비스 지도 |
| [docs/MIGRATION.md](docs/MIGRATION.md) | Gemini → 사내 LLM · I2T · T2I · 웹 검색 이전 · 검증 절차 |
| [docs/scenarios/](docs/scenarios/) | 기능별 화면 시나리오 · 수용 기준(00 셸 ~ 10 제안서) |
| [docs/screens/INDEX.md](docs/screens/INDEX.md) | 화면 디자인 원본 보드 색인 |
| [docs/templates/CATALOG.md](docs/templates/CATALOG.md) | 시트 템플릿 카탈로그 |
| [.env.example](.env.example) | 환경 변수 전체와 기본값 |
| `services/<서비스>/AGENTS.md` | 서비스별 규칙 · 현재 상태 · API |
| [docs/requests/](docs/requests/) | 서비스 간 · 플랫폼 요청 |
