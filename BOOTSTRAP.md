# BOOTSTRAP — Winmate 한 번에 이어받기

이 문서는 **코드 에이전트에게 그대로 주는 작업 지시서**다. 위에서부터 순서대로 진행한다.

1. 개발 환경을 갖춘다.
2. 지식 DB(winmate-kb)를 재현하고 검증한다.
3. 전체 시험을 통과시킨다.
4. 남은 앱 개발을 이어서 한다.

각 단계 끝의 **관문(✅)**을 통과해야 다음 단계로 간다. 관문을 못 넘으면 원인을 고치고 다시 확인한다. 고칠 수 없는 이유(권한 · 네트워크 · 사람의 결정)가 있을 때만 멈추고 보고한다.

---

## 0. 먼저 읽고 지킬 것

### 읽을 문서(이 순서로)

1. `AGENTS.md` — 저장소 공통 규칙. 세션 = 서비스 하나, 통신 규칙, 명령, 완료의 정의.
2. `docs/ARCHITECTURE.md` — API 규약(경로 `/v1`, 오류 형식, 목록, 202 잡, 내부 전용 API).
3. `docs/OPERATIONS.md` §1 — 맥 개발 환경. 사내망 우분투는 §2.
4. `docs/INTEGRATION.md` — 기능 간 여정 · 넘김 규약 · 알려진 틈.
5. `winmate-kb/docs/REPRODUCE.md` — 지식 DB 재현.
6. 서비스를 고칠 때마다: `services/<서비스>/AGENTS.md` 의 「현재 상태」와, 그 서비스가 부르는 서비스의 `contracts/<서비스>.json`.

### 절대 규칙

- **비밀**
  - `.env` 는 git 에 넣지 않는다.
  - `GEMINI_API_KEY` 등 키 값을 출력 · 로그 · 커밋 · URL 에 남기지 않는다. 키는 헤더로만 보낸다.
- **기밀**
  - 기밀 데이터가 든 모델 호출은 `confidential=True` 로 표시한다.
  - 개발용 Gemini 로 기밀을 보내지 않는다(`*_ALLOW_CONFIDENTIAL=false` 유지).
- **사실을 지어내지 않는다.**
  - 스펙 · 수치 · 모델명 · 고객명 · 문구는 KB · 파일 · 검색 근거가 있을 때만 쓴다.
  - 근거가 없으면 `[확인 필요]` 로 남긴다.
  - KB 의 데이터 공백(아래 §4.3)을 그럴듯한 값으로 채우지 않는다.
- **MSA 경계**
  - 서비스 코드는 자기 `owns` 경로(`config/services.yaml`)만 고친다.
  - 다른 서비스는 계약(OpenAPI)과 `ServiceClient` 로만 부른다.
  - 외부 모델은 ai-tools(`winmate_common.ai.ai()`)로만 부른다.
  - 공용 경로(`libs/common` · `config/` · `ops/` · `scripts/` · `web/src/ui` · `web/src/shell` · `web/src/api/client.ts`)는 "플랫폼 작업"으로 따로 다룬다.
- **포트는 5000번대만** 쓴다. Redis 는 5379.
- **삭제 · 되돌릴 수 없는 일은 하지 않는다.**
  - 대상: `rm -rf`, `git push --force`, `git reset --hard`, 원격 저장소 설정 변경, 사용자 데이터(`data/`) 삭제.
  - 필요하면 멈추고 사람에게 묻는다.
- **git**
  - 작업 단위마다 커밋한다. 메시지는 한국어 한 줄 요약 + 무엇을 · 왜.
  - `git push` 는 사람이 지시했을 때만 한다(원격: `origin` = github.com/minsub0922/winmate_poc, 브랜치 `main`).
- **메모리 예산**
  - 운영 대상은 RAM 16GB · GPU 2GB 우분투다.
  - 새 상주 프로세스나 큰 모델 의존성을 넣지 않는다. 필요하면 근거를 들어 사람에게 제안한다.

---

## 1. 환경 준비

### 1.1 저장소

- **이미 있는 폴더**(맥 `~/Dev/projects/sr_tasks/winmate`)에서 시작하면 `git status` 가 깨끗한지 보고 이어간다.
- **새로 받는다면** `git clone https://github.com/minsub0922/winmate_poc winmate && cd winmate`.
  - 이 경우 `.env` 가 없다. `cp .env.example .env` 하고, 사람에게 `GEMINI_API_KEY` 를 채워 달라고 요청한다.
  - 키가 없어도 4단계 전까지는 `MODEL_MODE=mock` 으로 모두 진행할 수 있다.
- **`poc/birdseye`** 는 별도 Blender PoC 다(포트 8710, 자체 `.gitignore`). 지시 없이는 고치지 않는다.

### 1.2 도구(맥)

```bash
xcode-select --install                       # 이미 있으면 건너뜀
brew install uv node@24 redis
export PATH="$(brew --prefix node@24)/bin:$PATH"
uv --version && node --version && redis-server --version
```

- Redis 는 `brew services` 로 띄우지 않는다. pm2 가 `ops/redis/redis.conf` 로 5379 에 띄운다.
- (선택) LibreOffice: `brew install --cask libreoffice`. 설치했으면 `.env` 에 `SOFFICE_PATH=/Applications/LibreOffice.app/Contents/MacOS/soffice` 를 넣는다. 이게 있으면 export 의 PDF · 슬라이드 PNG 와 LibreOffice 시험 3개가 돈다.

### 1.3 설치

```bash
make setup          # uv sync · npm install(ops · web) · 계약 · API 타입 · 웹 빌드
(cd web && npx playwright install chromium)
source .venv/bin/activate
```

✅ **관문 1**
- `make setup` 이 오류 없이 끝난다.
- `.venv/bin/python -c "import fastapi, langgraph, sklearn, yaml, joblib"` 가 성공한다.

---

## 2. 지식 DB 재현 · 검증

자세한 설명은 `winmate-kb/docs/REPRODUCE.md` 에 있다. 여기서는 **운영 DB 를 덮어쓰지 않고** 임시 폴더에 다시 빌드해 비교한다.

맥에는 `sha256sum` 이 없다. 아래 명령은 `shasum -a 256` 을 쓴다.

```bash
cd winmate-kb

# 2.1 원본 확인 — 6개 해시가 REPRODUCE.md §2.1 표와 같아야 한다
shasum -a 256 raw/*.json

# 2.2 임시 폴더에 빌드(운영 DB 는 그대로). 보고서 문서는 임시 경로로 빼서 git 을 더럽히지 않는다
export WKB_KB=$PWD/../data/wkb-rebuild
python build/build_kb.py && python build/index_kb.py && python build/qa.py
WKB_TEST_REPORT=$WKB_KB/SCENARIO_TEST_REPORT.md python tests/test_scenarios.py     # 41/41 통과여야 한다

# 2.3 비교
shasum -a 256 $WKB_KB/winmate_kb.sqlite $WKB_KB/models/lsa_char24_v2.joblib
#   기대값: sqlite 9ff585782fc80f042d60fbd049410134d1b0aa2c5a16b2e1f626f234ee6c5216
#           joblib b17266cc8c7defd7fb16efe4ad00d607efaac6a71acb5bf594497ca23d4d9ba8
#   운영 DB(kb/winmate_kb.sqlite)가 있으면 표 단위로도 비교한다:
[ -f kb/winmate_kb.sqlite ] && python build/compare_db.py kb/winmate_kb.sqlite $WKB_KB/winmate_kb.sqlite
unset WKB_KB
```

**운영 DB 가 없을 때**(새로 clone 한 경우)는 기본 위치에 만든다.

```bash
bash build/run_all.sh
python dashboard/thumb_select.py
git checkout -- docs/       # 보고서 문장 순서만 바뀐 노이즈를 되돌린다 — REPRODUCE.md §1 참고
```

`python dashboard/thumb_select.py` 는 kb 서비스와 이미지 받기 스크립트가 쓰는 우선 목록을 만든다.

```bash
cd ..
make test SERVICE=kb        # 90개, 실제 KB 파일로
```

✅ **관문 2**
- 원본 해시 6개가 일치한다.
- 시나리오 41/41, 품질 프로브 23/23 이 통과한다.
- 새 DB 가 기대 해시와 같다. 해시가 다르면(SQLite · scikit-learn 버전 차이 등) `compare_db.py` 결과의 「다른 표」가 0 이어야 한다.
  - `vec_index` 만 다르다면 scikit-learn 버전 차이일 수 있다. 버전을 기록하고, 검색 시나리오가 통과하면 넘어간다.
- `make test SERVICE=kb` 가 통과한다.
- 끝나면 `data/wkb-rebuild/` 를 지워도 된다(`data/` 는 git 밖).

---

## 3. 전체 스택 · 전체 시험

### 3.1 mock 모드로 띄우기

시험은 외부 네트워크 없이 돈다. `.env` 의 `MODEL_MODE` 가 `live` 면 시험 동안만 `mock` 으로 바꾸고, 끝나면 원래 값으로 되돌린다.

```bash
make up && sleep 20 && make status && make health      # 29개 online, "ok": true (kb 는 첫 5~11초 데운다)
```

### 3.2 정적 검사 · 백엔드

```bash
make contracts-check          # 17개 서비스 ✓
make typecheck                # 웹 타입 오류 0
make web-build
make test                     # libs/common + 전 서비스(약 9분) — 977 통과 · 3 건너뜀(LibreOffice 없을 때)
```

### 3.3 e2e(Playwright, 브라우저 1개 워커)

```bash
# 셸
(cd web && WM_E2E_SUITE=shell WM_E2E_DEV=1 WM_E2E_PORT=5197 npx playwright test e2e/shell --workers=1)        # 138

# 기능 10개
for s in requirements storyboard mi competitor vp spec image birdseye scenario proposal; do make e2e-feature SERVICE=$s; done
#   RQ 11 · SB 14 · MI 10 · CA 14 · VP 4 · SP 8 · IMG 20 · BE 6 · SC 9 · PR 25

# 기능 간 여정
(cd web && WM_E2E_SUITE=integration WM_E2E_DEV=1 WM_E2E_PORT=5299 npx playwright test e2e/integration --workers=1)   # 25
```

진행 화면을 보는 e2e 2개는 mock 이 너무 빨라서 속도를 늦춰야 한다.

| 시험 | 필요한 설정 |
|---|---|
| image `run.spec.ts` | `IMAGE_DEV_SHOT_DELAY_S=2.5` |
| scenario `result.spec.ts:33` | `SC_PACE_S=1.5` |

1. 두 워커를 그 환경 변수로 다시 띄운다. `pm2 restart --update-env` 는 셸에서 뺀 변수를 지우지 못하므로 delete 후 start 한다.

   ```bash
   ops/node_modules/.bin/pm2 delete image-worker scenario-worker
   IMAGE_DEV_SHOT_DELAY_S=2.5 SC_PACE_S=1.5 WINMATE_ONLY=image-worker,scenario-worker ops/node_modules/.bin/pm2 start ops/pm2/ecosystem.config.cjs
   ```

2. 시험이 끝나면 같은 방법(delete 후 start)으로 변수 없이 다시 띄운다.

알려진 가끔 실패: 셸 T-12, birdseye `inputs.spec.ts:41` 은 부하가 크면 가끔 실패한다. 한 번 다시 돌려 통과하면 넘어간다. 두 번 연속 실패하면 버그로 다룬다.

### 3.4 실제 모델 점검(키가 있을 때만)

```bash
MODEL_MODE=live uv run python services/ai-tools/scripts/live_check.py     # 7개 점검 표, 실패가 있으면 종료 코드 1
```

- 비용이 드는 호출이니 이 한 번만 돌린다.
- 실패하면 `LIVE_CHECK_TRACE=1` 로 원인을 본다.
- 모델 이름 · 요청 모양이 바뀌었다면 `services/ai-tools/tests/test_gemini_live_fixtures.py` 를 함께 갱신한다.

✅ **관문 3**
- 위 숫자가 모두 맞는다(시험을 더했으면 그만큼 늘어난다). 실패 0.
- 실패가 있으면 2단계 원인 분석(어느 서비스 · 계약 · 데이터) → 고침 → 그 서비스 시험 + 관련 e2e 를 다시 돌린다.
- 이 단계 결과를 `docs/INTEGRATION.md` §1.1 표에 날짜와 함께 갱신하고 커밋한다.

---

## 4. 앱 개발 이어가기

### 4.1 작업 목록(backlog) 만들기 — 먼저 목록부터, 코드는 그다음

다음 출처를 모두 읽고 `docs/BACKLOG.md` 를 만든다. 표 열은 `번호 · 서비스 · 할 일 · 출처 · 종류 · 상태` 다.

1. **`docs/requests/*.md`**
   - 섹션마다 첫 `상태: 요청` 줄만 보지 말고, 그 아래 이어 붙은 `상태(<서비스> · <날짜>) ↑ …` 답변 줄까지 읽는다. 이미 「완료」인 것은 뺀다.
   - 특히 「상태: 요청(kb → mi 안내)」처럼 **kb · export 가 새 필드를 만들어 두고 기능 쪽에 쓰라고 안내한 것**이 남아 있다. 대상은 mi · competitor · birdseye · spec · vp · proposal 이다.
2. **`docs/INTEGRATION.md`** §5 「남은 틈」 · §6 「통합 담당 할 일」.
   - 예: requirements · storyboard 에 지우기(보관) API 를 만들고 e2e `helpers.cleanup` 에 반영한다.
3. **`services/*/AGENTS.md`** 「현재 상태」의 「알려진 한계 · 공백」 중 코드로 풀 수 있는 것.
4. **`docs/scenarios/*.md`** 수용 기준 중 e2e 로 확인되지 않은 것. 각 기능 e2e 와 시나리오 문서를 대조해서 찾는다.

종류는 셋으로 나눈다.

| 종류 | 뜻 |
|---|---|
| `code` | 지금 바로 구현할 수 있다 |
| `decision` | 사람이 정해야 한다 |
| `data` | 사람이 자료를 줘야 한다 |

`decision` · `data` 는 구현하지 않고 목록에만 둔다.

### 4.2 진행 순서(우선순위)

1. **깨진 것.** 3단계에서 드러난 실패 · 계약 불일치.
2. **이미 만든 필드를 기능이 쓰게 하기.** `docs/requests` 의 안내 항목들. 예:
   - spec: XLSX 고객 양식 `base_file_id`
   - birdseye: kb `dims_mm` · `led` · 배치 규칙 `param_status`
   - mi · competitor: 요구 태그 이름표 `label` · `description`(이미 동작 — 화면 표시만 확인)
3. **requirements · storyboard 지우기(보관) API** + 통합 e2e 정리 도우미.
4. **남은 `code` 항목.** 서비스별로 묶어서 진행한다.
5. (사람이 지시하면) birdseye 3D 조감도와 `poc/birdseye`(Blender) 연결.
   - 먼저 설계 문서(`docs/requests/birdseye.md` 에 제안)를 쓴다. 사람의 확인을 받은 뒤 구현한다.

### 4.3 손대지 말 것(사람의 결정 · 자료 필요) — 목록에 `decision` · `data` 로만 둔다

| 항목 | 종류 |
|---|---|
| Winmate 16업종 중 시드 대응이 없는 6개(SV · TP · VN · AD · ID · OE)의 KR 업종 대응 | data |
| 조감도 배치 · 수량 규칙 계수(`placement_rules.yaml` 의 `<<FILL>>`), 역량 임계값 규칙 | data |
| LED 화면 구성 옵션 · The Wall 치수 · 공식 후속 모델 · 보증 연수 · 매뉴얼 · 솔루션 프로필(MagicINFO 외) | data(e-카탈로그 등) |
| `config/content_policy.yaml` 법무 확인 | decision |
| HWP(h2orestart) · SVG 로고(cairosvg) · 업스케일러 · 로컬 임베딩 의존성 추가 | decision(16GB 예산 · 사내망 설치 영향) |
| HTTPS · 접근 기록(리버스 프록시) | decision |
| 사내 API 어댑터(`services/ai-tools/src/winmate_ai_tools/providers/internal.py`) | data(사내 API 명세가 와야 함 — `docs/MIGRATION.md`) |

### 4.4 작업 하나의 진행 방식(서비스 단위)

서비스 하나를 맡은 세션처럼 일한다. 서브에이전트를 쓸 수 있으면 서비스마다 하나씩 맡겨도 된다. 단, 같은 공용 파일(`uv.lock` · `web/package-lock.json` · `libs/common`)을 동시에 고치지 않는다.

1. `services/<x>/AGENTS.md` 와 소비하는 서비스의 `contracts/*.json` 을 읽는다. 해당 `docs/scenarios/<번호>-<x>.md` · `docs/screens/` 원본도 읽는다.
2. 띄운다: `make dev-bg SERVICE=<x>`(API 리로드 + 워커).
3. 백엔드를 고친다 → `make test SERVICE=<x>`.
4. API 가 바뀌면 `make contracts SERVICE=<x>` 를 돌린다.
   - 깨지는 변경이면 소비 서비스에 `docs/requests/<소비 서비스>.md` 로 알린다.
   - 가능하면 더하는 변경(필드 · 경로 추가)만 한다.
5. 화면(`web/src/features/<x>/`)을 고친다.
   - `@/ui` 키트와 `var(--wm-*)` 토큰만 쓴다.
   - 확인: `make typecheck SERVICE=<x>` → `make e2e-feature SERVICE=<x>`. 수용 기준마다 e2e 를 더한다.
6. 다른 기능과 이어지는 변경이면 통합 e2e(`e2e/integration`)를 돌리고, 새 넘김 · 진입은 `docs/INTEGRATION.md` 표에 한 줄 더한다.
7. 정리한다.
   - `make dev-stop SERVICE=<x>` 를 하고 `ops/node_modules/.bin/pm2 restart <x> <x>-worker` 로 되돌린다.
   - `services/<x>/AGENTS.md` 「현재 상태」를 갱신한다.
   - `docs/requests/*` 의 해당 요청에 `- 상태(<x> · <날짜>) ↑ 완료 — …` 줄을 단다.
   - `docs/BACKLOG.md` 상태를 갱신하고 커밋한다.

**완료의 정의**(`AGENTS.md` §5): 코드 + 테스트 통과 + 계약 갱신 + 화면(시나리오 수용 기준) + AGENTS.md 「현재 상태」 갱신.

### 4.5 일정 간격마다 회귀 확인

서비스 3개를 마칠 때마다, 그리고 마지막에 한 번 3단계의 다음 항목을 다시 돌린다.

- `make contracts-check` · `make typecheck` · `make test`
- 바뀐 기능의 e2e + 통합 e2e

---

## 5. 끝낼 때 보고

마지막 응답에 아래를 짧게 적는다(과정 설명은 생략).

1. 관문 1~3 결과. 숫자를 적고, 다른 점이 있으면 원인도 적는다.
2. 이번에 끝낸 backlog 항목. 서비스 · 한 줄 요약 · 커밋 해시.
3. 남은 `code` 항목과 다음에 할 것.
4. 사람이 정하거나 줘야 하는 `decision` · `data` 목록. `docs/BACKLOG.md` 의 해당 줄을 그대로 옮긴다.
5. push 여부. 하지 않았으면 사람이 돌릴 명령 `git push origin main`.
