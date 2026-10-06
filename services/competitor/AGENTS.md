# competitor 서비스 — 개발 세션 규칙

경쟁사 분석 — 경쟁사 찾기 · 6개 비교 기준 · 신뢰도 · 익명화 · 30일 재확인

- 포트: **5104** · 게이트웨이 경로: `/api/competitor/v1/...` · 파이썬 모듈: `winmate_competitor`
- 고칠 수 있는 경로(owns): `services/competitor/**`, `web/src/features/competitor/**`
- 호출할 수 있는 서비스(consumes): `ai-tools`, `kb`, `files`, `jobs`, `workspace`, `export`, `requirements`
- 화면 수용 기준: `docs/scenarios/04-competitor.md` · 원본 보드: `docs/screens/` (INDEX.md)

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=competitor          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=competitor         # 이 서비스 테스트
make contracts SERVICE=competitor    # contracts/competitor.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("competitor", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("competitor")`(data/competitor/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=competitor` 를 돌리고 `contracts/competitor.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태
- 04-competitor.md 화면 · 흐름 · 수용 기준 AC-CA-01~55 구현(백엔드 · LangGraph · 웹 · 시험). 계약 `contracts/competitor.json`(30 경로).
- **코드 지도**(`src/winmate_competitor/`)
  - `api.py`(넣기 · 작업 · 찾기 · 후보 · 기준 · 실행 · 셸 추가) · `api_results.py`(결과 · 상세 · 근거 · 넘김 · 묶음 · ProposalHandoff · 내보내기 · 재확인)
  - `graphs/find.py`(ca.find: 칸 읽기 → 묻기 1 interrupt → 빈 칸 → 후보 → 개체 합치기 → 신뢰 → 고르기 → 기준 → 제목) · `graphs/analyze.py`(ca.analyze: 동시 2곳 ·
    사실 5 · 판정 · 강점 · 중지 저장 · 30일 예약) · `graphs/misc.py`(research · candidate_add · recheck · export · source_add)
  - 규칙 `rules.py`(신뢰 Σw·s/Σw · 배지 · 상한 · 글자 · 묻기 · 기준 6) · `verify.py`(인용 대조 · `[00]` 지우기 · 실명 새기 검사) · `reading.py`(네 칸)
  - `evidence.py` · `judging.py` · `results.py` · `bundle.py`(익명 묶음 · 리포트) · `store.py`(DocStore + 낙관적 잠금) · 설정 `config/routing.yaml` · `config/segments.yaml`
- **웹** `web/src/features/competitor/`: CA0 목록 · CA1/CA1R 넣기 · CA1G · CA2Q · CA2 · CA3 · CA3C · CA4(한눈에 · 비교표 · 삼성 강점) · CA4D(+근거 패널) · CA5.
- **mock 데모**: `mocks/ai-tools/ca.*.json` 은 `scripts/gen_mocks.py` 로 만든다(인용 구절이 요약 안에 있는지 검사). A 커피 글 → 후보 6(추천 4) → 결과 4곳.
  `매장 메뉴보드 사이니지` → 묻기 1(업종 두 갈래), `카페 메뉴보드 사이니지` → `업종 기준`. 개발 스택은 수집(fetch)이 꺼져 있어 경쟁사 사실은 `확인 필요`(요약뿐)로 나온다.
- **시험**: `make test SERVICE=competitor`(pytest 95 — AC 별 파일 test_parse/find/candidates/criteria/analyze/handoff/list_recheck + mock 데모 + requirements · mi 실제 통합),
  `make e2e-feature SERVICE=competitor`(Playwright 14, 화면 `web/e2e/competitor/__screens__/`). 다른 기능 폴더의 없는 import 로 개발 서버가 깨질 때는
  `web/e2e/competitor/vite.e2e.config.ts` 로 5204 를 먼저 띄우면 e2e 가 그 서버를 쓴다. 공유 머신이 바쁘면 첫 요청만으로 수십 초가 걸려
  준비 시간은 파일 머리 `describe.configure({ timeout: SETUP_MS })`, 본문은 `budget(ms)`(그 위에 더하기)로 잡고, 게이트웨이 일시 500(RemoteProtocolError)은 GET 만 다시 묻는다.
- **결정 · 명세와 다른 점**
  - 잡 입력은 jobs 계약대로 `{answer}` — 서버는 `{value:{…}}` 로 와도 푼다. 문서 쓰기는 API · 워커 두 프로세스가 같은 문서를 고치므로 `version` 비교 쓰기(재시도), 잡 id 는 먼저 문서에 적고 넣는다.
  - MI · Storyboard · 제안서로 보내기는 명세대로 **웹이** 묶음을 옮긴다(consumes 에 mi · storyboard 가 생겼어도 서버는 부르지 않음). 제안서 반입 `source.feature` 는 서비스 키 `competitor`.
  - 업종이 두 갈래면 업종 칩에 `일부`(§7.2 문구 규칙 — 보드 CA1 예시와 다름). 제작자 의견(정의서 author_note)은 칸 읽기 LLM 문맥에서도 뺀다.
  - 다시 찾기에서 지운 자동 후보의 글자는 다시 쓸 수 있다(고정 · 직접 추가 글자는 그대로). 후보 0곳이면 찾기 실패(`failed`), 직접 추가하면 `confirming`.
  - 분석 중 기준 바꾸기(PUT criteria)는 지금 잡을 끝내고(supersede) 모은 사실로 판정부터 다시(`rejudge`). 셸 추가 뒤에는 결과 화면 `다시 판정` 띠.
  - 후보 상한의 `업종만` 단: 업종 사례로 채운 제품(origin=inferred)은 입력 신호로 세지 않는다. 기본 기준과 이름이 같은 요구 기준은 기본 하나로.
  - 업데이트 배너 `분석 {d}일 경과` 는 실제 경과일(같은 날 손으로 재확인하면 `오늘 분석`). 상세 항목 순서는 화면 순서(라인업 · 가격대 · 솔루션 · 레퍼런스 · 최근 동향).
  - 명세 밖 추가 API: `GET /progress` · `GET /capabilities` · `GET /handoffs` · `GET /changes`. `proposal-handoff` 는 브라우저도 읽을 수 있다(tags handoffs — MI 와 같음).
  - KB 요구 유형 R01~R24 이름표가 비어 있어 업종 사례 기준 이름은 LLM(실패하면 예시 문장 줄임) — kb 요청.
- **요청한 것**: platform(`.env.example` CA_* 키 · 게이트웨이 keep-alive 500) · kb(R 이름표) · proposal(Why Samsung 넘김 연결 확인) · workspace(36×22 스위치, 선택).
- **통합(integration · 2026-10-07)**: CA5 「새 제안서로 시작」 = 넘김(`target_id: null`) 만들고 delivered → `/proposal/new?handoff=hof_…&link=ca_…&feature=competitor`(유형 고르면 why 섹션 반입).
  `hof_` 는 MI 와 겹쳐 proposal 이 분석 id(`ca_`)로 기능을 정한다.
