# Winmate 운영 가이드

맥 개발 환경 만들기, 사내망 우분투 PC(인터넷 없음 · Docker 없음)에 설치 · 운영하기, 서비스 지도.
구조는 [ARCHITECTURE.md](ARCHITECTURE.md), 사내 모델 API 로 바꾸는 법은 [MIGRATION.md](MIGRATION.md),
환경 변수 하나하나의 뜻은 [`.env.example`](../.env.example) 에 있다.

- [0. 한눈에](#0-한눈에)
- [1. 맥 개발 환경](#1-맥-개발-환경)
- [2. 사내망 우분투 설치 · 운영](#2-사내망-우분투-설치--운영)
- [3. 서비스 지도](#3-서비스-지도)
- [4. 남은 일(코드에 없는 운영 항목)](#4-남은-일코드에-없는-운영-항목)

---

## 0. 한눈에

- **프로세스**: pm2 하나가 Redis(5379) + API 17개 + 워커 11개를 띄운다. 정의는 `ops/pm2/ecosystem.config.cjs` 가
  `config/services.yaml`(포트 · 워커 여부의 단일 원천)을 읽어 만든다. 바깥에 여는 것은 게이트웨이(5000) 하나뿐이고 나머지는 `127.0.0.1` 에서만 듣는다.
- **설정**: `.env` — 서비스 프로세스가 시작할 때 한 번 읽는다(고치면 `make restart`). 이미 있는 셸 환경 변수가 `.env` 보다 우선한다.
- **데이터**: `data/` — 서비스별 SQLite(`data/<서비스>/`) · 업로드/생성 파일(`data/files/blobs/`) · 카세트 · 로그(`data/logs/`) · Redis(`data/redis/`).
  지식 DB 는 `winmate-kb/`(읽기 전용).
- **모델**: 외부 모델은 ai-tools(5010)만 부른다. 제공자는 `.env` 로 바꾼다(맥 = Gemini, 사내망 = 사내 API).

`make up` 을 실행하는 **셸의** 환경 변수(`.env` 가 아님 — pm2 설정 파일이 직접 읽는다):

| 변수 | 뜻 | 예 |
|---|---|---|
| `WINMATE_ONLY` | 일부만 띄움(쉼표, `<서비스>` 를 쓰면 그 워커도, Redis 가 필요하면 `redis` 도). `make restart` · `make up` 때도 같은 값을 준다 — 없으면 나머지가 모두 다시 뜬다 | `WINMATE_ONLY=redis,gateway,kb,ai-tools make up` |
| `REDIS_SERVER_BIN` | `redis-server` 대신 쓸 실행 파일 | `REDIS_SERVER_BIN=valkey-server make up` |
| `REDIS_MANAGED=0` | Redis 를 pm2 가 띄우지 않음(시스템 서비스로 따로 운영할 때 — 그때는 `.env` `REDIS_URL`) | |
| `WINMATE_WEB_DEV=1` | Vite 개발 서버(5001)도 pm2 로 | |
| `WINMATE_VENV_BIN` | 파이썬 가상환경 bin(기본 `<저장소>/.venv/bin`) | |

`.env` 에서는 `APP_HOST`(게이트웨이 듣는 주소)와 `JOB_WORKERS`(워커 동시 잡 수)만 pm2 설정이 읽는다 — 바꾸면 `make down && make up`.

| 명령 | 하는 일 |
|---|---|
| `make setup` | (맥 · 인터넷) `uv sync --all-packages` · `ops`/`web` `npm install` · 계약 내보내기 · API 타입 · 웹 빌드 |
| `make up` · `make down` · `make restart` | pm2 전체 시작 · 삭제(데이터는 그대로) · 다시 읽기(`pm2 reload --update-env`) |
| `make status` · `make health` · `make logs SERVICE=x` | pm2 목록 · 전체 상태 JSON(`/api/_health`) · 로그 |
| `make dev SERVICE=x` · `make dev-worker SERVICE=x` · `make dev-bg SERVICE=x` · `make dev-stop SERVICE=x` | 서비스 하나만 개발 모드로 |
| `make test [SERVICE=x]` · `make typecheck SERVICE=x` | 테스트(네트워크 없이) · 웹 타입 검사 |
| `make contracts [SERVICE=x]` · `make contracts-check` | 계약 갱신(+ 웹 API 타입) · 코드 ↔ 계약 일치 검사 |
| `make web-dev` · `make web-build` · `make e2e` · `make e2e-feature SERVICE=x` | Vite(5001) · `web/dist` 빌드 · e2e |

pm2 를 직접 쓸 때는 저장소의 것을 쓴다: `ops/node_modules/.bin/pm2 …` (편하게 `alias pm2="$PWD/ops/node_modules/.bin/pm2"`).

---

## 1. 맥 개발 환경

### 1.1 준비물

| 도구 | 설치 | 비고 |
|---|---|---|
| Xcode 명령줄 도구 | `xcode-select --install` | git · make |
| uv | `brew install uv` | 파이썬 3.12 는 `uv sync` 가 알아서 받는다(`.python-version`) |
| Node.js 24 LTS | `brew install node@24` | keg-only 라 PATH 에 넣는다 |
| Redis | `brew install redis` | 실행 파일만 쓴다. `brew services` 로 띄우지 않는다 — pm2 가 `ops/redis/redis.conf` 로 5379 에 띄운다. Valkey 도 된다(`brew install valkey` 후 `REDIS_SERVER_BIN=valkey-server make up`) |
| LibreOffice(선택) | `brew install --cask libreoffice` | PPTX → PDF · 슬라이드 PNG(export), 문서 썸네일(files). `.env` `SOFFICE_PATH=/Applications/LibreOffice.app/Contents/MacOS/soffice` |

```bash
xcode-select --install                       # 이미 있으면 건너뜀
brew install uv node@24 redis
echo "export PATH=\"$(brew --prefix node@24)/bin:\$PATH\"" >> ~/.zshrc && exec zsh
uv --version && node --version && redis-server --version
```

### 1.2 처음 설치

```bash
git clone <저장소 주소> winmate && cd winmate
cp .env.example .env               # GEMINI_API_KEY 를 채운다(이미지 생성은 결제를 켠 프로젝트의 키)
make setup                         # uv sync · npm install(ops · web) · 계약 · API 타입 · 웹 빌드
make up                            # pm2: Redis 5379 + API 17 + 워커 11
make status                        # 모두 online
make health                        # "ok": true — kb 는 처음 5~11초 데운다
open http://localhost:5000         # 게이트웨이가 web/dist 를 서빙
```

- 첫 실행 때 `data/.internal_token`(서비스 간 토큰) · `data/.secret_key`(세션 쿠키)가 생긴다.
- 지식 DB 데이터(`winmate-kb/kb/winmate_kb.sqlite` · `winmate-kb/kb/models/` · `winmate-kb/dashboard/build/`)는 git 에 없다 — 새로 받았으면 가지고 있는 winmate-kb 폴더에서 같은 자리로 복사한다.
- 계약 문서 UI: http://localhost:5000/api/_docs

### 1.3 매일 쓰는 명령

| 하는 일 | 명령 |
|---|---|
| 켜기 · 끄기 · `.env` 다시 읽기 | `make up` · `make down` · `make restart` |
| 상태 · 로그 | `make status` · `make health` · `make logs SERVICE=ai-tools` · `tail -f data/logs/ai-tools.log` |
| 웹 개발(HMR) | `make web-dev` → http://localhost:5001 (`/api` 는 5000 으로 넘김) |
| 플랫폼만 띄우기 | `make down && WINMATE_ONLY=redis,gateway,ai-tools,kb,files,jobs,workspace,export make up` |
| 모델 사용량 | `curl -s localhost:5000/api/ai-tools/v1/usage \| .venv/bin/python -m json.tool` (`AUTH_MODE=none` 일 때) |

### 1.4 서비스 하나 고치기

| 방식 | 시작 | pm2 로 되돌리기 |
|---|---|---|
| API 포그라운드(리로드) | `make dev SERVICE=kb` | Ctrl-C → `ops/node_modules/.bin/pm2 restart kb` |
| 워커 포그라운드 | `make dev-worker SERVICE=mi` | Ctrl-C → `ops/node_modules/.bin/pm2 restart mi-worker` |
| API(리로드) + 워커 백그라운드 | `make dev-bg SERVICE=mi` (로그 `data/logs/dev-mi.log` · `dev-mi-worker.log`) | `make dev-stop SERVICE=mi` → `ops/node_modules/.bin/pm2 restart mi mi-worker` |

- 그 서비스의 pm2 프로세스를 멈추고 같은 포트로 띄우므로 게이트웨이 경로(`/api/<서비스>/…`)는 그대로다.
- 워커는 코드가 바뀌어도 저절로 다시 뜨지 않는다 → `make dev-bg SERVICE=x` 를 다시 실행.

### 1.5 테스트 · 계약 · e2e

```bash
make test SERVICE=kb               # 네트워크 없이(MODEL_MODE=mock · 임시 DATA_DIR · fakeredis · 계약 strict)
make test                          # libs/common + 전 서비스
make typecheck SERVICE=mi          # 웹 타입 검사(그 기능 폴더 오류만 실패)
make contracts SERVICE=kb          # contracts/kb.json 갱신 + 깨지는 변경 경고 + web/src/api/gen/kb.ts
make contracts-check               # 코드 ↔ 계약 일치 — 배포 번들을 만들기 전에 반드시
```

e2e(Playwright):

```bash
(cd web && npx playwright install chromium)          # 처음 한 번
make web-build && make up && make e2e                 # 게이트웨이(5000)의 web/dist 로 전체 e2e

# 기능 e2e — Vite 개발 서버(서비스 포트 + 100)로, 브라우저는 /opt/pw-browsers 에서 찾는다(Makefile 고정 경로)
sudo mkdir -p /opt/pw-browsers && sudo chown "$USER" /opt/pw-browsers
(cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers npx playwright install chromium)
make e2e-feature SERVICE=requirements
```

### 1.6 실제 Gemini 점검 · mock

```bash
MODEL_MODE=live uv run python services/ai-tools/scripts/live_check.py                    # 7개 점검 표, 실패가 있으면 종료 코드 1
MODEL_MODE=live uv run python services/ai-tools/scripts/live_check.py --only llm_json,i2t
LIVE_CHECK_TRACE=1 MODEL_MODE=live uv run python services/ai-tools/scripts/live_check.py # 실패 원인(트레이스백)
```

- 점검: `llm_text` · `llm_json` · `llm_tools`(도구 2턴, thought signature 왕복) · `i2t`(JSON + 박스) · `t2i` · `t2i_edit`(마스크 잘라 붙이기) · `websearch`.
- 게이트웨이를 거치지 않고 ai-tools 함수를 직접 부른다. Redis 가 없으면 메모리로 한도를 센다. t2i 결과는 files 서비스에, 없으면 `data/ai-tools/live_check/` 에.
- 개발용 Gemini 로는 기밀(`confidential: true`) 호출이 403 `POLICY_CONFIDENTIAL` 로 막힌다 — 공개 시험 자료로 개발한다.
- 네트워크 없이 개발: `.env` `MODEL_MODE=mock` → `make restart`. 고정 응답은 `mocks/ai-tools/<task>.json`([형식](../mocks/ai-tools/README.md)).
  기밀 차단 경로를 mock 으로 시험하려면 `MOCK_ENFORCE_CONFIDENTIAL=true`.
- `GEMINI_THINKING_LEVEL` 을 받지 않는 모델이면 400 → 값을 비운다.

---

## 2. 사내망 우분투 설치 · 운영

전제: x86_64 우분투(22.04 · 24.04, 아래 패키지 이름은 24.04 기준), RAM 16 GB, 인터넷 없음, Docker 없음, 사내 LLM · I2T · T2I · 웹 검색 API 는 네트워크로 닿음.
사내 apt · PyPI · npm 미러가 있으면 2.1 의 번들 대신 미러에서 바로 설치해도 된다(경로 · 이후 절차는 같다).

### 2.0 배치

| 경로 | 내용 |
|---|---|
| `/opt/winmate/bin` | uv · uvx |
| `/opt/winmate/node` | Node.js 24 LTS(pm2 실행용) |
| `/opt/winmate/uv-python` | uv 관리 CPython 3.12 |
| `/opt/winmate/uv-cache` | 파이썬 휠 캐시(오프라인 설치 원본) |
| `/opt/winmate/bundle` | 받은 번들: `.deb` 로컬 저장소 · 소스 · 빌드 산출물 · KB 데이터 · pm2-logrotate |
| `/opt/winmate/app` | 저장소(코드 · `.venv` · `ops/node_modules` · `web/dist` · `winmate-kb/` · `data/` · `.env`) |
| `/opt/winmate/backups` | 백업 |
| `/opt/winmate/env.sh` | PATH · uv 오프라인 설정 |

- 빌드 머신과 사내망 PC 에서 **같은 경로(`/opt/winmate`)** 를 쓴다 — uv 가 만드는 파이썬 버전 링크가 절대 경로다.
- 서비스는 일반 계정 하나(예: `winmate`)로 돌린다. root 로 돌리지 않는다.

### 2.1 오프라인 번들 만들기(인터넷이 되는 곳)

**① 맥에서**(저장소 루트, 커밋된 것만 들어간다):

```bash
git archive --format=tar.gz -o winmate-src.tar.gz HEAD
export COPYFILE_DISABLE=1                     # macOS tar 가 ._ 파일을 넣지 않게
tar -czf winmate-kb-data.tar.gz winmate-kb/kb/winmate_kb.sqlite winmate-kb/kb/models winmate-kb/dashboard/build
tar -czf kb-images.tar.gz data/kb/images      # 선택: kb_fetch_images.py 로 받은 이미지 사본(사내망은 samsung.com 에 못 붙는다)
tar -czf cassettes.tar.gz data/cassettes      # 선택: MODEL_MODE=record 로 쌓은 카세트(MIGRATION.md §7)
uv --version                                  # 빌드 머신에서 같은 판의 uv 를 받는다
```

이 파일들을 빌드 머신의 `/opt/winmate/bundle/` 로 옮긴다(아래 컨테이너를 쓰면 맥의 `out/` 에 두고 컨테이너 안에서
`mkdir -p /opt/winmate/bundle && cp /out/*.tar.gz /opt/winmate/bundle/`).

**② 빌드 머신** — 인터넷이 되는 x86_64 우분투, **사내망 PC 와 같은 버전**. 새 VM 이나 맥의 컨테이너
`docker run --rm -it --platform linux/amd64 -v "$PWD/out:/out" ubuntu:24.04 bash` 도 된다(Docker 는 번들을 만들 때만 —
사내망 PC 에는 필요 없다). 아래는 root 셸 기준이다(VM 이면 `sudo -i`).

```bash
# 공통 변수 — 사내망과 같은 경로
export W=/opt/winmate UV_VERSION=0.11.32                 # ← 맥의 uv 판
export UV_PYTHON_INSTALL_DIR=$W/uv-python UV_CACHE_DIR=$W/uv-cache UV_MANAGED_PYTHON=1
export PATH=$W/bin:$W/node/bin:$PATH
mkdir -p $W/bin $W/node $W/app $W/bundle/debs
apt-get update && apt-get install -y --no-install-recommends ca-certificates curl xz-utils apt-utils
```

```bash
# 시스템 패키지 — 의존성까지 전부 .deb 로 받고 로컬 저장소 색인(Packages)을 만든다
PKGS="make curl rsync fontconfig fonts-noto-cjk fonts-nanum redis-server \
  libreoffice-writer-nogui libreoffice-calc-nogui libreoffice-impress-nogui libreoffice-draw-nogui"
cd $W/bundle/debs
apt-get download $(apt-cache depends --recurse --no-recommends --no-suggests --no-conflicts \
  --no-breaks --no-replaces --no-enhances $PKGS | grep '^\w' | sort -u)
apt-ftparchive packages . > Packages && apt-ftparchive release . > /tmp/Release && mv /tmp/Release Release
cd $W
```

- `make` · `curl` · `rsync` 는 우분투 데스크톱에 없을 수 있어 넣는다(`make` 명령 · `make health` · 업그레이드에 쓴다).
- 사내망 PC 에 데스크톱 LibreOffice 가 이미 있으면(`which soffice`) `libreoffice-*-nogui` 는 빼도 된다.
- Valkey 를 쓰려면 `redis-server` 대신 `valkey-server`(24.04 universe), 실행은 `REDIS_SERVER_BIN=valkey-server make up`.

```bash
# Node.js 24 LTS — 공식 tarball, 체크섬 확인
NODE_DIST=https://nodejs.org/dist/latest-v24.x
NODE_TAR=$(curl -fsSL $NODE_DIST/SHASUMS256.txt | awk '/linux-x64\.tar\.xz$/{print $2}')
curl -fsSL -o bundle/$NODE_TAR $NODE_DIST/$NODE_TAR
curl -fsSL $NODE_DIST/SHASUMS256.txt | grep " $NODE_TAR\$" | (cd bundle && sha256sum -c -)
tar -xJf bundle/$NODE_TAR -C node --strip-components=1 && node --version

# uv — 단일 실행 파일
curl -fsSL -o bundle/uv.tar.gz \
  https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-unknown-linux-gnu.tar.gz
tar -xzf bundle/uv.tar.gz -C bin --strip-components=1 && uv --version
```

```bash
# 소스 · CPython 3.12 · 휠 캐시 — 마지막 줄이 "네트워크 없이 새 가상환경이 만들어지는가"를 확인한다
tar -xzf bundle/winmate-src.tar.gz -C app
uv python install 3.12
(cd app && uv sync --frozen --all-packages)
rm -rf app/.venv && (cd app && UV_OFFLINE=1 uv sync --frozen --all-packages) \
  && app/.venv/bin/python -c "import fastapi, langgraph, google.genai, openai, pptx, pdfplumber, sklearn; print('offline ok')"
```

```bash
# pm2 · 계약 문서 UI(ops/node_modules) + 운영 웹 빌드(web/dist, 개발 화면 /_dev 제외)
(cd app/ops && npm ci --no-audit --no-fund)
(cd app/web && npm ci --no-audit --no-fund && VITE_WM_DEVTOOLS=0 npm run build)
tar -czf bundle/app-build.tar.gz -C app ops/node_modules web/dist
```

```bash
# pm2-logrotate — pm2 의 TAR 모듈(맨 위 폴더 이름이 module). 의존성을 넣고 기본 설정을 박아 둔다
mkdir -p /tmp/lr && cd /tmp/lr && npm pack pm2-logrotate@3.0.0 && tar -xzf pm2-logrotate-3.0.0.tgz
(cd package && npm install --omit=dev --no-audit --no-fund)
node -e 'const f="./package/package.json",p=require(f);Object.assign(p.config,{max_size:"20M",retain:"14",compress:true});require("fs").writeFileSync(f,JSON.stringify(p,null,2))'
mv package module && tar -czf $W/bundle/pm2-logrotate-3.0.0.tar.gz module && cd $W
```

```bash
# 하나로 묶기(빌드용 app/ 은 넣지 않는다)
mkdir -p /out && cd /opt
tar -cf /out/winmate-offline-$(date +%Y%m%d).tar \
  winmate/bin winmate/node winmate/uv-python winmate/uv-cache winmate/bundle
cd /out && sha256sum winmate-offline-*.tar > SHA256SUMS && ls -lh
```

번들 안 `bundle/`: `debs/`(+`Packages`) · `winmate-src.tar.gz` · `app-build.tar.gz` · `winmate-kb-data.tar.gz` · (선택) `kb-images.tar.gz` · `cassettes.tar.gz` ·
`pm2-logrotate-3.0.0.tar.gz` · Node · uv 원본. 크기는 대략 2~3 GB.
로컬 모델 가중치는 지금 옮길 것이 없다 — 로컬 임베딩 · 업스케일러는 의존성이 없어 꺼져 있다(§4).

### 2.2 옮겨서 설치(사내망 PC)

서비스를 돌릴 일반 계정으로 한다. `sudo` 는 표시한 줄만.

```bash
sudo mkdir -p /opt/winmate && sudo chown "$USER": /opt/winmate
sha256sum -c SHA256SUMS && tar -C /opt -xf winmate-offline-*.tar
cat > /opt/winmate/env.sh <<'EOF'
export PATH=/opt/winmate/bin:/opt/winmate/node/bin:$PATH
export UV_PYTHON_INSTALL_DIR=/opt/winmate/uv-python UV_CACHE_DIR=/opt/winmate/uv-cache UV_MANAGED_PYTHON=1
export UV_OFFLINE=1 UV_FROZEN=1 UV_PYTHON_DOWNLOADS=never
EOF
echo 'source /opt/winmate/env.sh' >> ~/.bashrc && source /opt/winmate/env.sh
```

시스템 패키지(번들의 로컬 apt 저장소 — 이미 깔린 것보다 새 판이 필요할 때만 올린다):

```bash
chmod -R a+rX /opt/winmate/bundle/debs
echo "deb [trusted=yes] file:/opt/winmate/bundle/debs ./" | sudo tee /etc/apt/sources.list.d/winmate-local.list
sudo apt-get update -o Dir::Etc::sourcelist=sources.list.d/winmate-local.list \
  -o Dir::Etc::sourceparts=- -o APT::Get::List-Cleanup=0
sudo apt-get install -y --no-install-recommends make curl rsync fontconfig fonts-noto-cjk fonts-nanum redis-server \
  libreoffice-writer-nogui libreoffice-calc-nogui libreoffice-impress-nogui libreoffice-draw-nogui
sudo systemctl disable --now redis-server      # 패키지가 켠 6379 인스턴스는 쓰지 않는다(pm2 가 5379 로 띄움)
soffice --headless --version && redis-server --version
```

글꼴 — export 의 PPTX 는 'Noto Sans KR' 을 쓴다. 서버에는 Noto Sans CJK KR 이 있으니 이름을 잇는다(PDF 줄바꿈이 맥과 같아진다):

```bash
sudo tee /etc/fonts/local.conf >/dev/null <<'EOF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <alias binding="same"><family>Noto Sans KR</family><prefer><family>Noto Sans CJK KR</family></prefer></alias>
</fontconfig>
EOF
sudo fc-cache -f && fc-match "Noto Sans KR"       # → NotoSansCJK-…: "Noto Sans CJK KR"
```

(`/etc/fonts/local.conf` 가 이미 있으면 `<alias>` 줄만 더한다.)

코드 · 빌드 산출물 · 지식 DB · 가상환경:

```bash
mkdir -p /opt/winmate/app && cd /opt/winmate/app
tar -xzf ../bundle/winmate-src.tar.gz
tar -xzf ../bundle/app-build.tar.gz             # ops/node_modules · web/dist
tar -xzf ../bundle/winmate-kb-data.tar.gz       # winmate-kb/kb/winmate_kb.sqlite · models · dashboard/build
tar -xzf ../bundle/kb-images.tar.gz             # 선택 → data/kb/images
tar -xzf ../bundle/cassettes.tar.gz             # 선택 → data/cassettes
uv sync --offline --frozen --all-packages       # .venv — 네트워크 없이 캐시에서
make contracts-check                            # 코드 ↔ 계약 일치
```

### 2.3 `.env` · 첫 실행

```bash
cp .env.example .env && chmod 600 .env && nano .env
```

| 키 | 사내망 값 |
|---|---|
| `WINMATE_ENV` | `intranet`(서비스 간 계약 검증이 warn — 로그만) |
| `MODEL_MODE` | `live`(이전 검증 중에는 `replay` · `record` — MIGRATION.md §7) |
| `LLM_*` · `I2T_*` · `T2I_*` · `WEBSEARCH_*` · `*_ALLOW_CONFIDENTIAL` | 사내 API — [MIGRATION.md](MIGRATION.md) |
| `GEMINI_API_KEY` | 비움 |
| `APP_HOST` | 다른 PC 에서 접속하면 `0.0.0.0`(2.5) |
| `AUTH_MODE` · `ADMIN_PASSWORD` | 로그인을 쓰면 `local` + 관리자 비밀번호(2.5) — 쓸 수 있는 관리자가 없으면 시작할 때 만든다 |
| `SOFFICE_PATH` | `/usr/bin/soffice` |
| `EXPORT_PDF_TTF` | (선택) `/usr/share/fonts/truetype/nanum/NanumGothic.ttf` |
| `WEB_FETCH_ENABLED` · `SEARCH_API_PROVIDER` | 외부 웹이 막혀 있으면 `false` · `none` |
| `HTTP(S)_PROXY` · `NO_PROXY` · `SSL_CERT_FILE` | 사내 API 가 프록시 · 사설 인증서 뒤에 있을 때만(MIGRATION.md §6) |

시간대는 한국으로(하루 호출 한도가 로컬 날짜 기준): `sudo timedatectl set-timezone Asia/Seoul`.

```bash
make up && make status && make health
curl -s -H "X-Internal-Token: $(cat data/.internal_token)" \
  http://127.0.0.1:5000/api/ai-tools/v1/capabilities | .venv/bin/python -m json.tool    # 제공자 · 모델 · available
```

### 2.4 부팅 때 자동 시작(pm2 startup · save)

```bash
cd /opt/winmate/app
ops/node_modules/.bin/pm2 startup systemd     # 출력되는 sudo 명령을 그대로 실행한다. 예:
# sudo env PATH=$PATH:/opt/winmate/node/bin /opt/winmate/app/ops/node_modules/pm2/bin/pm2 startup systemd -u winmate --hp /home/winmate
make up                                       # 이미 떠 있으면 생략
ops/node_modules/.bin/pm2 save                # 지금 목록을 ~/.pm2/dump.pm2 에 → 부팅 때 pm2-<계정>.service 가 resurrect
systemctl status "pm2-$USER" --no-pager
sudo reboot                                   # 확인: 다시 로그인해 make health
```

- 프로세스 구성을 바꾼 뒤(`make down/up`, `WINMATE_ONLY`, `REDIS_SERVER_BIN` …)에는 `pm2 save` 를 다시 한다.
- Node 를 바꾸면 `ops/node_modules/.bin/pm2 unstartup systemd` 로 지우고 다시 `startup` → `save`.

### 2.5 게이트웨이만 열기 · 방화벽 · 계정

- `.env` `APP_HOST=0.0.0.0` → `make down && make up && ops/node_modules/.bin/pm2 save`. 접속 주소는 `http://<PC IP>:5000`.
- 확인: `ss -ltn | grep -E ':5[0-9]{3}\b'` → 바깥 주소는 `0.0.0.0:5000` 하나, 나머지(5010–5110 · 5379)는 `127.0.0.1`(Redis 는 `[::1]` 도).
- 방화벽(ufw) — 5000 만, 가능하면 사내 대역만:

  ```bash
  sudo ufw allow OpenSSH                                       # 원격 접속을 쓰면 먼저
  sudo ufw allow from 10.0.0.0/8 to any port 5000 proto tcp    # 예: 사내 대역
  sudo ufw enable && sudo ufw status
  ```

- `AUTH_MODE=none` 이면 접속하는 모든 사람이 같은 사용자(`DEV_USER_ID`)다 — 방화벽으로 접속 대역을 좁힌다.
- `AUTH_MODE=local`(사내망 권장): `.env` 에 `AUTH_MODE=local` · `ADMIN_PASSWORD=<…>`(필요하면 `ADMIN_USERNAME`) → `ops/node_modules/.bin/pm2 restart gateway workspace`
  (둘 다 `AUTH_MODE` 를 읽는다). 쓸 수 있는 관리자(관리자 역할 · 비밀번호 있음 · 사용 중)가 없으면 workspace 가 시작할 때 그 계정을 만든다
  (같은 아이디가 있으면 관리자로 올리고 비밀번호를 정함). 브라우저에서 `/login` → 관리자로 로그인 → 오른쪽 위 사용자 메뉴 「사용자 관리」(`/admin/users`)에서
  계정 만들기 · 역할 · 비밀번호 재설정 · 사용 중지. 사용자는 사용자 메뉴에서 비밀번호를 바꾼다.
- 세션: 쿠키 14일, 게이트웨이가 60초마다 workspace 로 다시 확인해 사용 중지 · 비밀번호 재설정된 계정의 기존 세션을 끊는다.
  같은 IP · 아이디로 로그인 5번 연속 실패(10분) 또는 한 IP 에서 20번 실패면 잠시 429(「로그인 시도가 너무 많아요」).
- 휴대폰 QR 사진 올리기(조감도 BE1P)는 로그인 없이 업로드 토큰(30분)으로만 통과한다. QR 주소가 휴대폰에서 열리려면 `.env` `PUBLIC_BASE_URL=http://<PC IP>:5000`.
- 화면 대신 API 로 사용자를 만들 수도 있다:

  ```bash
  curl -s -c /tmp/wm.cookie -H 'Content-Type: application/json' \
    -d '{"username":"admin","password":"<ADMIN_PASSWORD>"}' http://127.0.0.1:5000/api/_auth/login
  curl -s -b /tmp/wm.cookie -H 'Content-Type: application/json' \
    -d '{"username":"kim","name":"김영업","org":"B2B영업","password":"<6자 이상>"}' \
    http://127.0.0.1:5000/api/workspace/v1/users
  ```

### 2.6 메모리 예산(RAM 16 GB)

`ops/pm2/ecosystem.config.cjs` 의 `max_memory_restart` — 넘으면 그 프로세스를 다시 띄우는 기준일 뿐 메모리를 예약하지 않는다.

| 프로세스 | 한도 | 측정(개발 컨테이너, 유휴) |
|---|---|---|
| ai-tools | 2G | 83 MB |
| kb | 1500M | 350 MB(데운 뒤) |
| files · export · image · birdseye · proposal | 1G | files 65 MB · export 115 MB |
| export · image · birdseye · proposal 워커 | 1G | export 워커 95 MB |
| 그 밖 API(gateway · jobs · workspace · 기능 7개) | 600M | gateway 68 MB · jobs · workspace 58 MB |
| 그 밖 워커(기능 7개) | 800M | (export 워커와 비슷하게 ≈ 100 MB 로 본다) |
| Redis | `maxmemory 512mb`(noeviction — 차면 쓰기 오류) | 수 MB |
| pm2 데몬 | — | 50 MB |

- 한도를 모두 더하면 약 24 GB 라 16 GB 보다 크다 → 한도가 아니라 실제 사용량으로 본다. 유휴 합계는 약 3 GB(추정).
- 일할 때 늘어나는 것: LibreOffice 변환(한 번에 수백 MB — files 는 `SOFFICE_CONCURRENCY`, export 는 워커의 `JOB_WORKERS` 만큼 동시에),
  PDF 파싱(pdfplumber), 큰 이미지 편집(Pillow), kb 검색 캐시.
- 권장: `JOB_WORKERS=1~2` · `SOFFICE_CONCURRENCY=1` · `FILES_PARSE_CONCURRENCY=2`, 쓰지 않는 기능은 빼고 띄운다
  (`make down && WINMATE_ONLY=redis,gateway,…,<쓰는 기능> make up` → `pm2 save`. 이후 `make restart` 에도 같은 `WINMATE_ONLY`),
  스왑 4~8 GB. 지금 코드는 GPU 를 쓰지 않는다.
- 보기: `ops/node_modules/.bin/pm2 monit` · `ops/node_modules/.bin/pm2 ls`(mem 열) · `free -h`. 한도를 바꾸려면 ecosystem 의 `MEMORY`(플랫폼 담당) → `make down && make up`.

### 2.7 로그 회전

로그는 `data/logs/<프로세스>.log`(stdout + stderr, 시각 포함), pm2 자체 로그는 `~/.pm2/pm2.log`. 둘 중 **하나만** 쓴다.

**pm2-logrotate**(번들의 TAR 모듈 — 20 MB 넘거나 매일 0시에 회전, 14개 보관, gzip):

```bash
cd /opt/winmate/app
ops/node_modules/.bin/pm2 install /opt/winmate/bundle/pm2-logrotate-3.0.0.tar.gz
ops/node_modules/.bin/pm2 ls                   # Module 표에 pm2-logrotate
```

설정을 바꾸려면 2.1 의 `node -e …` 줄을 고쳐 TAR 를 다시 만들고 `pm2 uninstall pm2-logrotate` → `pm2 install …`.

**시스템 logrotate**(우분투 기본, 매일 한 번):

```bash
sudo tee /etc/logrotate.d/winmate >/dev/null <<EOF
/opt/winmate/app/data/logs/*.log {
  daily
  rotate 14
  maxsize 20M
  missingok
  notifempty
  compress
  delaycompress
  copytruncate
  su $(id -un) $(id -gn)
}
EOF
sudo logrotate -d /etc/logrotate.d/winmate     # 시험(아무것도 바꾸지 않음)
```

### 2.8 백업 · 복구

| 대상 | 경로 | 방법 |
|---|---|---|
| 서비스 DB(WAL) | `data/**/*.sqlite` | SQLite 백업 API(실행 중에도 일관된 사본) |
| 업로드 · 생성 파일 | `data/files/blobs/` | 한 폴더로 rsync(내용 해시 이름이라 바뀌지 않고 늘기만 한다) |
| Redis(잡 · 이벤트 · 예약 · 한도) | `data/redis/appendonlydir` | AOF 다시 쓰기를 잠시 멈추고 복사(redis.io persistence 문서 절차) |
| 설정 · 비밀 · 그 밖 데이터 | `.env` · `data/.secret_key` · `data/.internal_token` · 서비스 폴더의 나머지 파일 | tar |
| 백업 불필요 | `data/files/cache` · `data/cache` · `data/logs` · `winmate-kb/` · `data/kb/images` · 카세트(번들에 있음) | — |

`/opt/winmate/backup.sh`:

```bash
mkdir -p /opt/winmate/backups
cat > /opt/winmate/backup.sh <<'SH'
#!/usr/bin/env bash
# Winmate 백업 — 서비스가 돌고 있어도 일관된 사본을 만든다.
set -euo pipefail
APP=/opt/winmate/app
BK=/opt/winmate/backups
DEST=$BK/$(date +%Y%m%d-%H%M)
mkdir -p "$DEST" && cd "$APP"
.venv/bin/python - "$DEST" <<'PY'
import pathlib, shutil, sqlite3, sys, time
import redis
dest = pathlib.Path(sys.argv[1])
for src in sorted(pathlib.Path("data").rglob("*.sqlite")):           # 1) SQLite
    out = dest / "sqlite" / src.relative_to("data")
    out.parent.mkdir(parents=True, exist_ok=True)
    s, d = sqlite3.connect(src, timeout=60), sqlite3.connect(out)
    s.backup(d); d.close(); s.close()
r = redis.Redis(host="127.0.0.1", port=5379, decode_responses=True)   # 2) Redis AOF
prev = r.config_get("auto-aof-rewrite-percentage")["auto-aof-rewrite-percentage"]
r.config_set("auto-aof-rewrite-percentage", 0)
try:
    while int(r.info("persistence")["aof_rewrite_in_progress"]):
        time.sleep(1)
    shutil.copytree("data/redis/appendonlydir", dest / "redis-appendonlydir")
finally:
    r.config_set("auto-aof-rewrite-percentage", prev)
PY
rsync -a data/files/blobs/ "$BK/blobs/"                                 # 3) 파일 원본(덧붙이기만)
tar -czf "$DEST/data-rest.tgz" --exclude='*.sqlite' --exclude='*.sqlite-wal' --exclude='*.sqlite-shm' \
  --exclude=data/files/blobs --exclude=data/files/cache --exclude=data/cache --exclude=data/logs \
  --exclude=data/redis --exclude=data/run --exclude=data/kb/images --exclude='data/cassettes*' \
  .env data                                                             # 4) 설정 · 그 밖 데이터
find "$BK" -mindepth 1 -maxdepth 1 -type d -name '20*' -mtime +14 -exec rm -rf {} +
echo "백업 완료: $DEST"
SH
chmod +x /opt/winmate/backup.sh && /opt/winmate/backup.sh
( crontab -l 2>/dev/null; echo '30 3 * * * /opt/winmate/backup.sh >> /opt/winmate/backups/backup.log 2>&1' ) | crontab -
```

백업은 같은 디스크에만 두지 않는다 — 주기적으로 외장 디스크 · NAS 로 복사한다.

복구:

```bash
B=/opt/winmate/backups/<날짜-시각>
cd /opt/winmate/app && make down
find data \( -name '*.sqlite-wal' -o -name '*.sqlite-shm' \) -delete
tar -xzf "$B/data-rest.tgz"                                # .env · 비밀 · 그 밖 데이터
cp -a "$B/sqlite/." data/                                  # 서비스 DB
rsync -a /opt/winmate/backups/blobs/ data/files/blobs/     # 파일 원본
rm -rf data/redis/appendonlydir && cp -a "$B/redis-appendonlydir" data/redis/appendonlydir
make up && make health
```

### 2.9 업그레이드

맥에서 2.1 ① 로 새 `winmate-src.tar.gz` 를 만들고, 빌드 머신에서 `rm -rf $W/app && mkdir $W/app` 뒤 소스 · 휠 캐시 · 웹 빌드 단계를 다시 해
`app-build.tar.gz` 를 만든다. `uv.lock` 이 바뀌었으면 `uv-cache/` 도, 시스템 패키지가 늘었으면 `debs/` 도, KB 를 다시 수집했으면
`winmate-kb-data.tar.gz` 도 함께 옮긴다(`uv-cache` 는 통째로 덮어써도 된다 — 캐시는 추가만 한다). 사내망 PC 에서:

```bash
/opt/winmate/backup.sh                                    # 먼저 백업
# 새 bundle/* · (바뀌었으면) uv-cache/ 를 /opt/winmate 아래에 덮어쓴 뒤
rm -rf /tmp/wm-new && mkdir /tmp/wm-new && tar -xzf /opt/winmate/bundle/winmate-src.tar.gz -C /tmp/wm-new
rsync -a --delete \
  --exclude=/.env --exclude=/.venv/ --exclude=/data/ --exclude=/models/ \
  --exclude=/ops/node_modules/ --exclude=/web/node_modules/ --exclude=/web/dist/ \
  --exclude=/winmate-kb/kb/ --exclude=/winmate-kb/dashboard/build/ \
  /tmp/wm-new/ /opt/winmate/app/                          # 코드만 바꾼다(지운 파일도 지움, 런타임 경로는 그대로)
cd /opt/winmate/app
rm -rf ops/node_modules web/dist && tar -xzf ../bundle/app-build.tar.gz
uv sync --offline --frozen --all-packages
make contracts-check
diff <(grep -oE '^[A-Z][A-Z0-9_]*=' .env.example | sort) <(grep -oE '^[A-Z][A-Z0-9_]*=' .env | sort)   # 새 키가 있나
make restart                                               # pm2 reload(.env 다시 읽음, 새로 생긴 프로세스는 시작)
ops/node_modules/.bin/pm2 save && make health
```

- pm2 판이 바뀌었으면(`ops/package-lock.json`) `ops/node_modules/.bin/pm2 update`.
- 포트 · 메모리 한도 · 워커 여부(`config/services.yaml` · ecosystem)나 `APP_HOST` · `JOB_WORKERS` 가 바뀌었으면 `make restart` 대신 `make down && make up` → `pm2 save`.
- KB 데이터가 바뀌었으면 `tar -xzf ../bundle/winmate-kb-data.tar.gz` → `ops/node_modules/.bin/pm2 restart kb`.
- 되돌리기: 이전 `winmate-src.tar.gz` · `app-build.tar.gz` 로 같은 절차, 데이터가 문제면 2.8 복구.

### 2.10 문제 해결

| 증상 | 확인 | 조치 |
|---|---|---|
| `make health` 에서 서비스가 `down` · `degraded` | `make logs SERVICE=x` · `tail -n 200 data/logs/x.log` · `curl -s 127.0.0.1:<포트>/healthz`(토큰 없이 열림, `checks` 에 세부) | 오류를 고친 뒤 `ops/node_modules/.bin/pm2 restart x`. kb 는 처음 5~11초 `warm=false` |
| `Address already in use` · 포트 충돌 | `ss -ltnp \| grep -E ':(5000\|50[1-6]0\|510[0-9]\|511[01]\|5379)\b'` | 남은 개발 프로세스는 `make dev-stop SERVICE=x`. 포트를 바꾸려면 `config/services.yaml`(플랫폼 담당) → `make down && make up` |
| 서비스 포트에 직접 붙으면 401 `UNAUTHENTICATED`("게이트웨이를 거친 요청만") | — | 정상. `http://127.0.0.1:5000/api/<서비스>/…` 로, 스크립트는 `-H "X-Internal-Token: $(cat data/.internal_token)"` |
| 브라우저가 계속 `/login` 으로 감 | `.env` `AUTH_MODE` · `curl -s localhost:5000/api/_auth/me` | `local` 이면 정상(로그인 필요). 로그인이 429 면 10분 뒤 · 401 이면 아이디 · 비밀번호 · 사용 중지 여부(관리자 「사용자 관리」) |
| 403 `INTERNAL_ONLY` · `DEPENDENCY_NOT_ALLOWED` | 응답 `error.message` | 브라우저가 서비스 전용 API 를 부름 · `consumes` 밖 호출 — 코드 문제(해당 서비스 담당) |
| `make contracts-check` 실패 · 로그의 `ContractViolation` | 어느 계약 · 경로인지 | 코드와 `contracts/*.json` 이 다르다 → 맥에서 `make contracts SERVICE=x` 후 커밋 → 번들을 다시. 사내망에서 `make contracts` 로 덮어쓰지 않는다 |
| 잡이 `queued` 에서 안 움직임 · `health` 의 `redis.ok=false` | `make logs SERVICE=redis` · `ls -ld data/redis` | (`ops/redis/redis.conf` 는 `bind 127.0.0.1 -::1` — IPv6 가 꺼져 있어도 뜬다) 5379 를 다른 프로세스가 쓰는지, `data/redis` 권한. AOF 손상은 백업 후 `redis-check-aof`. (ai-tools 는 Redis 가 없으면 한도 검사 없이 통과하고 경고만 남긴다) |
| PPTX → PDF 501 `PDF_CONVERTER_UNAVAILABLE` · 미리보기 501 `PREVIEW_UNAVAILABLE` · PPTX 썸네일이 자리표시 카드 | `which soffice` · `soffice --headless --version` · `.env` `SOFFICE_PATH` | LibreOffice 설치, `SOFFICE_PATH=/usr/bin/soffice` → `make restart`. 변환 실패(`CONVERSION_FAILED`)는 1시간 캐시된다(`data/files/cache/soffice/*.fail` 을 지우고 다시) |
| PDF 줄바꿈 · 글꼴이 맥과 다름 | `fc-match "Noto Sans KR"` | 2.2 의 글꼴 별칭 · `fc-cache -f` |
| 모델 호출 오류(아래 코드) | `capabilities`(2.3) · 호출 로그 `curl -s -H "X-Internal-Token: $(cat data/.internal_token)" "http://127.0.0.1:5000/api/ai-tools/v1/calls?limit=20"` · `data/logs/ai-tools.log` | [MIGRATION.md §9](MIGRATION.md#9-자주-나는-오류) |
| `.env` 를 고쳤는데 그대로 | `env \| grep -E '^(MODEL_MODE\|LLM_\|AUTH_)'` | `make restart`. 같은 이름의 셸 변수가 이긴다. 값 뒤에 `#` 주석을 달지 않는다 |
| `AUTH_MODE=local` 인데 관리자로 로그인이 안 됨 | `.env` `ADMIN_PASSWORD` · `make logs SERVICE=workspace` | `ADMIN_PASSWORD` 를 넣고 `pm2 restart workspace`(쓸 수 있는 관리자가 없으면 만든다). 이미 관리자가 있으면 그 계정으로 — 잊었으면 `ADMIN_USERNAME` 을 새 아이디로 바꿔 다시 시작 |
| `uv sync --offline` 실패(캐시에 없음 · 인터프리터 없음) | `echo $UV_CACHE_DIR $UV_PYTHON_INSTALL_DIR` · `uv python list` | 번들의 `uv-cache` 가 `uv.lock` 보다 오래됨 → 빌드 머신에서 다시. 경로가 빌드 때(`/opt/winmate`)와 같아야 한다 |
| 재부팅 뒤 아무것도 안 뜸 | `systemctl status pm2-$USER` · `ls ~/.pm2/dump.pm2` | `pm2 save` 를 했는지 · `ops/node_modules/.bin/pm2 resurrect` |
| 디스크가 찬다 | `du -sh data/* \| sort -h` | 파일 원본(`files/blobs`), 호출 로그(`ai-tools/calls.sqlite`, `MODEL_CALL_LOG` · `MODEL_CALL_LOG_RETENTION_DAYS`), 카세트, 로그 회전 |

---

## 3. 서비스 지도

`config/services.yaml` 에서 만든 표다(바뀌면 그 파일이 원본 — 실행 중에는 `curl -s localhost:5000/api/_services`).
API 는 모두 `http://<게이트웨이>:5000/api/<서비스>/v1/…`, 상태는 각 포트의 `/healthz`. 워커가 있는 서비스는 pm2 이름 `<서비스>-worker`.

| 포트 | 서비스 | 역할 | 워커 | 호출하는 서비스(consumes) |
|---|---|---|---|---|
| 5000 | `gateway` | 라우팅 · 인증 · 계약 문서(`/api/_docs`) · 전체 상태(`/api/_health`) · 웹 정적 파일 | | workspace |
| 5010 | `ai-tools` | LLM · I2T · T2I · 요약형 웹 검색 · 검색 API · 웹 수집 · 임베딩 — 외부 모델 호출의 유일한 통로 | | files |
| 5020 | `kb` | 지식 DB 질의(제품 · 솔루션 · 업종 · 공간 · 사례 · 메시지 · 이미지) | | — |
| 5030 | `files` | 업로드 · 저장 · 문서 파싱 · 미리보기 · 썸네일 | | — |
| 5040 | `jobs` | 잡 상태 · 진행 이벤트(SSE) · 취소 · 사람 입력 · 예약 실행 · 완료 알림 | | — |
| 5050 | `workspace` | 사용자 · 프로젝트 · 작업물 색인 · 코멘트 · 검토/승인 · 공유 링크 | | — |
| 5060 | `export` | PPTX · XLSX · DOCX · PDF · ZIP 생성, 시트 템플릿 카탈로그 | ✓ | files, kb |
| 5101 | `requirements`(RQ) | 고객 요구사항 | ✓ | ai-tools, kb, files, jobs, workspace, export, storyboard |
| 5102 | `storyboard`(SB) | 전략 수립 Storyboard · 콘텐츠 흐름 허브(`/v1/flows*` · flow.json · summary.md) | ✓ | ai-tools, kb, files, jobs, workspace, export, requirements |
| 5111 | `dss`(DS) | 공간별 제품 매칭 DSS(새 콘텐츠 흐름, 2026-10-10) | | ai-tools, kb, workspace, storyboard |
| 5103 | `mi`(MI) | Market Intelligence | ✓ | ai-tools, kb, files, jobs, workspace, export, requirements, storyboard |
| 5104 | `competitor`(CA) | 경쟁사 분석 | ✓ | ai-tools, kb, files, jobs, workspace, export, requirements, storyboard, mi |
| 5105 | `vp`(VP) | Value Proposition | ✓ | ai-tools, kb, files, jobs, workspace, export, requirements, storyboard, mi |
| 5106 | `spec`(SP) | Spec 시트 | ✓ | ai-tools, kb, files, jobs, workspace, export, requirements, storyboard |
| 5107 | `image`(IMG) | 이미지 생성 · 합성 · 부분 수정 · 업스케일 | ✓ | ai-tools, kb, files, jobs, workspace, export |
| 5108 | `birdseye`(BE) | 공간 조감도 | ✓ | ai-tools, kb, files, jobs, workspace, export, image |
| 5109 | `scenario`(SC) | 공간 시나리오 | ✓ | ai-tools, kb, files, jobs, workspace, export, image, birdseye, storyboard |
| 5110 | `proposal`(PR) | B2B 제안서 · 기존 제안서 활용 · 딸깍 | ✓ | ai-tools, kb, files, jobs, workspace, export, requirements, storyboard, mi, competitor, vp, spec, image, birdseye, scenario |
| 5001 | web(개발) | Vite 개발 서버 — `make web-dev`(운영은 게이트웨이가 `web/dist` 서빙) | | — |
| 5379 | redis | 잡 큐(Stream) · 이벤트 · 호출 한도 카운터(`ops/redis/redis.conf`, AOF) | | — |

---

## 4. 남은 일(코드에 없는 운영 항목)

| 항목 | 지금 | 영향 · 임시 방법 |
|---|---|---|
| 공유 링크 절대 주소 | 공유 링크는 상대 경로, 휴대폰 QR 만 `PUBLIC_BASE_URL` 을 쓴다 | 메일 등에 붙일 절대 링크가 필요하면 같은 키를 쓰도록 기능 쪽 작업이 필요 |
| pm2 설정이 `.env` 를 따로 읽음 | `APP_HOST` · `JOB_WORKERS` 만(따옴표 · 값 뒤 ` #` 주석 · `export` 처리) | `REDIS_SERVER_BIN` · `WINMATE_ONLY` 는 `.env` 가 아니라 `make up` 을 실행하는 셸의 환경 변수 |
| JSON 수리 재시도와 호출 제한 시간 | 기능 → ai-tools 호출 제한이 300초(`winmate_common.ai`), JSON 수리는 모델을 최대 3번 부른다 | 느린 사내 모델은 `LLM_TIMEOUT_S` 를 100초 안쪽으로. 더 길게 하려면 클라이언트 제한도 함께 늘려야 한다 |
| HWP 5(.hwp) | 기본 LibreOffice 로는 못 읽는다(HWPX 는 글자만) | 24.04 에 `libreoffice-h2orestart`(universe)가 있지만 GUI LibreOffice(`libreoffice-core`) · Java(`default-jre`)를 끌어온다 — 채택 여부 결정 필요 |
| SVG 로고 | export 는 PNG · JPEG 만 그린다(SVG 는 경고 후 건너뜀) | `cairosvg`(+ `libcairo2`) 의존성 추가 여부 결정 필요 |
| 로컬 모델(선택) | 로컬 임베딩(`EMBEDDING_PROVIDER=local`)은 sentence-transformers, image 의 업스케일러(`UPSCALER=realesrgan_x4v3`)는 onnxruntime 이 필요한데 둘 다 의존성에 없다 | 지금은 옮길 가중치가 없다. 쓰기로 하면 의존성 추가 + 가중치 폴더(`models/`)를 번들에 넣고 `HF_HUB_OFFLINE=1` |
| HTTPS · 접근 기록 | 게이트웨이는 HTTP 만, 접근 기록 없음(`--no-access-log`) | 사내 정책상 HTTPS · 접근 기록이 필요하면 앞단 리버스 프록시(nginx 등) 또는 uvicorn TLS · 로그 설정이 필요 |
