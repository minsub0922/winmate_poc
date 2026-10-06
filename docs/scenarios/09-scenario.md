# 09. 공간 시나리오 (scenario · SC) — 화면 수용 기준

- 범위 보드(13): `UC_SC` `SC0` `SC1` `SC1T` `SC1B` `SC2` `SC2E` `SC3` `SC3R` `SC4G` `SC4` `SC4E` `SC5`
- 원천: `docs/screens/webapp2/<보드>.dc.html`, `docs/screens/_text/webapp2/<보드>.txt`(특히 `SC1T` 의 업종 16개 데이터), `docs/ARCHITECTURE.md`, `config/services.yaml`, `winmate-kb/docs/*`, `winmate-kb/seed/ontology/verticals.yaml`·`solutions_services.yaml`, `winmate-kb/seed/sheet_roles.yaml`
- 표기: 「…」 = 보드 문구 그대로. **(신규)** = 보드에 없는 상태용 제안 문구. `{변수}` = 템플릿 자리.
- 장면 이미지는 image 서비스(07)로, 조감도는 birdseye 서비스(08)로 만든다. 이 서비스는 T2I 를 직접 부르지 않는다.

---

## 1. 목적과 진입점

**목적.** 고객 공간에서 하루 또는 특정 상황이 흘러가는 모습을 시간대 × 역할의 장면으로 나누고, 장면마다 삼성 솔루션 동작과 제품 활용을 근거와 함께 넣는다. 결과는 제안서 「공간별 가치 제공 시나리오」 섹션(VM · SS 시트)으로 넘기거나 PPTX · PDF · DOCX · ZIP 으로 내보낸다. **조감도는 기본 꺼짐** — 설정으로 켜는 선택 옵션이다.

| 항목 | 값 |
|---|---|
| 서비스 | `scenario` · 포트 **5109** · `worker: true` · 큐 `wm:q:scenario` |
| 게이트웨이 | `/api/scenario/v1/...` (내부 `/v1/...`), `GET /healthz` |
| 소유 경로 | `services/scenario/**`, `web/src/features/scenario/**` |
| consumes | `ai-tools, kb, files, jobs, workspace, export, image, birdseye` |
| 데이터 | `${DATA_DIR}/scenario/scenario.sqlite` + 체크포인트 `${DATA_DIR}/scenario/checkpoints.sqlite` |
| 시드 | `services/scenario/seed/industry_templates.yaml`(업종 16, §10.4), `solution_actions.yaml`(솔루션 동작 사전, §10.5), `skeletons.yaml`(예시 골격, §10.6) |
| 웹 모듈 | `web/src/features/scenario/` — 사이드바 그룹 `scenario`, 이름 「공간 시나리오 생성」, 목록 `/scenario`, 새 작업 `/scenario/new` |
| 스텝바 | `steps = ['시나리오 유형', '공간 시나리오 입력', '솔루션 · 제품 입력', '시나리오 생성']` — SC1·SC1T=1, SC1B·SC2·SC2E=2, SC3·SC3R=3, SC4G·SC4·SC4E=4, SC5=4 + `complete` |
| 상단바 | `section="공간 시나리오 생성"`, `title` = 시나리오 제목(새 작업 「새 작업」, 목록 「작업 목록」) |

**진입점**
1. 홈 '공간 시나리오 생성' 기능 버튼 → SC1. 사이드바 그룹 → SC0, 그룹 항목 → 그 시나리오의 현재 화면(`route`).
2. 조감도 BE6 「공간 시나리오로 이어 만들기 · 시작」, BE0 메뉴 「시나리오로 이어 만들기」 → SC1B(`?birdseye=be_…`).
3. 제안서 시작 PR1L 에서 이 시나리오를 기존 작업으로 고르면 제안서가 `handoff` 를 읽는다(화면 진입 없음).

**화면 원칙.** W 말풍선 1개 + 사용자 입력 메아리 + 하단 작업 카드 1장. 보드에 없는 패널은 만들지 않는다. W 문구는 상태값 템플릿. 템플릿의 조사(을/를 · 이/가 · 은/는)는 앞말 발음으로 고른다(07 §1 규칙과 같음, 예 「장면 2는」, 「장면 1을」).

---

## 2. 화면 목록

| 보드 | 제목 | 라우트 / 상태 제안 | 주요 요소 |
|---|---|---|---|
| `UC_SC` | 시나리오 · 유스케이스 맵 | 런타임 화면 아님 · 개발용 `/_dev/uc/scenario` 선택 | 레인 5, 카드 17, 화면 안 상태 4, 받아오는 것·넘겨주는 것 |
| `SC0` | 시나리오 · 작업 목록 | `/scenario` | 시작 카드 3, 조감도 변경 알림, 상태 필터, 시작 방식 필터, 목록, 보내기 아이콘 |
| `SC1` | 시나리오 1/4 · 유형 선택 (with/without 솔루션) | `/scenario/new` · `/scenario/:id/type` | 유형 카드 2, 조감도 추가 토글(기본 꺼짐) + 새로/기존 |
| `SC1T` | 시나리오 · 업종 템플릿에서 시작 | `/scenario/new/template` (`?industry=FB&preset=1`) | 업종 16 타일·검색, 유형, 장면 프리셋 3, 대표 공간, 요구, 자주 쓰인 것 |
| `SC1B` | 시나리오 · 조감도에서 이어 만들기 | `/scenario/new/birdseye?birdseye=` · 변경 반영 `/scenario/:id/birdseye` | 조감도 고르기, 존 평면, 가져올 존, 시나리오 축, 동선 순서, 연결 유지 |
| `SC2` | 시나리오 2/4 · 공간 시나리오 입력 | `/scenario/:id/input` | 예시 골격 3, 시나리오 텍스트, 등장인물 |
| `SC2E` | 시나리오 · 타임라인 · 페르소나 편집 | `/scenario/:id/timeline` | 시간대 × 역할 격자, 장면 카드 끌기, W 추천 장면, 역할 추가, 페르소나 패널 |
| `SC3` | 시나리오 3/4 · 솔루션·제품 입력 | `/scenario/:id/solutions` | 장면 칩, 솔루션 칩·탐색·입력, 제품 칩·추천·입력 |
| `SC3R` | 시나리오 · 장면별 솔루션 추천 | `/scenario/:id/solutions/recommend` | 장면별 제품만 상황·근거·추천 솔루션·적용 토글, 유형 전환 안내 |
| `SC4G` | 시나리오 · 생성 중 | `/scenario/:id/generate/:jobId` | 단계 4, 진행률, 끝난 장면 미리보기, 진행 방향 메모, 중지 |
| `SC4` | 시나리오 4/4 · 시나리오 생성 | `/scenario/:id/result` | 장면 카드(이야기·솔루션·제품·이미지), 장면 추가·더 짧게·이미지 모두 생성·조감도 추가, 수정 요청 |
| `SC4E` | 시나리오 · 장면 편집 | `/scenario/:id/scenes/:sceneId` | 장면 목록, 장면 버전·되돌리기, 제목·이야기·인물·솔루션·제품, 장면 이미지·넘어가는 조건, 이 장면만 다시 쓰기 |
| `SC5` | 시나리오 · 제안서로 보내기 · 내보내기 | `/scenario/:id/send` | 보낼 곳, 시트 3장 미리보기, 함께 넘어가는 것, 파일로 받기 4, 다른 기능으로 2 |

---

## 3. 사용자 흐름

### 3.1 기본 흐름
`SC1`(유형) → `SC2`(공간 시나리오 입력) → `SC3`(솔루션 · 제품) → `SC4G`(생성 중) → `SC4`(결과) → `SC5`(보내기) → 제안서 `PRX3`.

### 3.2 레인(UC_SC)
머리 「WINMATE · USE-CASE MAP」 「공간 시나리오 생성 — 유스케이스 맵」 「들어오는 길부터 결과 활용까지, 시나리오 기능의 화면 12개와 이어지는 다른 기능. 카드를 누르면 그 화면으로 이동합니다.」, 범례 「기본 흐름」 「다른 길」 「기본 흐름 화면」 「추가 화면」 「다른 기능」, 꼬리 「기본 흐름 4 · 추가 화면 8 · 다른 기능 5」.

| 레인 | 카드(설명 · 다음) |
|---|---|
| 「01 들어오는 길 · 화면 5 · 어디서 시나리오를 시작하나」 | HOME 「홈 · 공간 시나리오 생성」 「홈 화면 기능 버튼으로 바로 시작」 → SC1 · SC0 「시나리오 작업 목록」 「최근 작업 · 상태 · 검색 · 이어서 작성」 → SC1 · SC1T · SC1B · SC4 · SC1T 「업종 템플릿에서 시작」 「16개 업종 · 대표 공간 · 장면 프리셋」 → SC2E · SC1B 「조감도에서 이어 만들기」 「조감도 존 · 배치 제품을 공간으로」 → SC2E · BE6 「조감도 결과에서 보내기」 「공간 조감도 → 시나리오로 보내기」 → SC1B |
| 「02 입력 방식 · 화면 4 · 무엇을 어떻게 넣나」 | SC1 「시나리오 유형」 「with / without · 조감도 추가(선택)」 → SC2 · SC2 「공간 시나리오 입력」 「텍스트 · 예시 골격 · 등장인물」 → SC3 · SC2E · SC3 「솔루션 · 제품 입력」 「솔루션을 고르면 연관 제품 추천」 → SC4G · SC3R · SC3R 「장면별 솔루션 추천」 「without → with 전환 · 추천 근거」 → SC4G |
| 「03 진행 · 확인 상태 · 화면 2 · 생성 · 대기 · 결과 확인」 | SC4G 「시나리오 생성 중」 「장면 단위 진행 · 중지 · 미리보기」 → SC4 · SC4 「시나리오 생성 결과」 「장면별 이야기 · 솔루션 · 제품」 → PRX3 · SC4E · SC5 |
| 「04 편집 · 버전 · 화면 2 · 구조와 장면 고치기」 | SC2E 「타임라인 · 페르소나 편집」 「시간대 · 역할 레인 · 장면 이동」 → SC3 · SC4E 「장면 편집 · 재생성」 「장면 고치기 · 장면 이미지 만들기」 → SC4 · IMG2 |
| 「05 결과 활용 · 화면 4 · 제안서 · 이미지 · 내보내기」 | SC5 「제안서로 보내기 · 내보내기」 「공간별 가치 제공 시나리오 · PDF」 → PRX3 · PR1L · PRX3 「제안서 · 공간별 가치 제공 시나리오」 「B2B 제안서 섹션에 장면이 들어감」 → PRX4 · IMG2 「이미지 생성 · 장면 이미지」 「장면 설명으로 이미지 조건 채움」 → IMG3 · PR1L 「제안서 시작 · 기존 작업 연결」 「제안서 생성에서 이 시나리오 선택」 → PR2 |

연결선 라벨: 「제안서에 넣기」 「구조로 편집」 「보내기 · 내보내기」. 「카드 아래 '다음'은 그 화면에서 이어지는 곳입니다. SC1T · SC1B는 타임라인 편집(SC2E)으로 바로 이어집니다.」

**화면 안에서 생기는 상태**(UC_SC): 「생성이 멈추면 → SC4G 다시 시도」, 「장면이 너무 많으면 → SC2E 합치기」, 「조감도가 바뀌면 → SC0 알림 → SC1B」, 「솔루션을 못 고르면 → SC3R 추천」.
**받아오는 것**: 「조감도 존 · 배치 제품 ← 공간 조감도」, 「고객 · 공간 정보 ← Storyboard · 사이드바에서 끌어오기」, 「업종별 공간 · 장면 프리셋 ← 도입사례 기준 템플릿」.
**넘겨주는 것**: 「장면 · 솔루션 · 제품 → 제안서 '공간별 가치 제공 시나리오'」, 「장면 설명 · 등장 제품 → 이미지 생성 조건」, 「시나리오 보드 → PDF · 이미지 내보내기」.

### 3.3 라우팅 규칙
| # | 시점 | 에이전트가 자동으로 | 사용자에게 묻는 것 |
|---|---|---|---|
| R1 | SC1 | 유형 기본값 「WITH 솔루션」(보드). 요청·프로젝트 맥락에 솔루션이 없으면 그대로 두고 SC3 에서 정리 | 유형 |
| R2 | SC2 → 다음 | 텍스트 → 타임라인(시간 정규식 + LLM JSON). **장면 ≤ 6 이고 같은 시간 충돌·역할 미배정이 없으면 SC3, 아니면 SC2E**(장면 > 6 이면 W 가 「같은 시간 장면 합치기」 권유) | 없음 |
| R3 | SC1T · SC1B → | 골격 생성 후 항상 SC2E | 없음 |
| R4 | SC3 「시나리오 생성」 | WITHOUT 인데 솔루션이 「꼭 필요」·「추천」인 장면이 있거나, WITH 인데 솔루션을 하나도 고르지 않았으면 → SC3R. 그 밖은 SC4G | SC3R 에서 적용 여부 |
| R5 | SC3 솔루션 선택 | 연관 제품 추천(KB D5 공존 + C2 공간 후보 + 시나리오 문장 언급) | 추천 칩 추가 여부 |
| R6 | 생성 | 근거 없는 수치는 「[00]」, 실존 인물 이름은 역할명으로, 경쟁사명은 일반명(**(신규)** 「기존 시스템」)으로 | 없음 |
| R7 | SC4 「장면별 이미지 모두 생성」 | 이미지 없는 장면마다 image 렌더 API 로 1장씩 만들어 붙임(화면 이동 없음) | 없음 |
| R8 | 재생성 | 사용자가 직접 고친 장면(`locked`)은 「나머지 장면 다시 생성」에서 제외 | 없음 |
| R9 | SC5 | 장면을 공간 기준으로 묶어 시트 구성(VM·SS 템플릿) 자동 결정(§7.9) | 보낼 제안서 |
| R10 | 조감도 변경 | 연결 유지한 조감도의 버전이 바뀌면 SC0 알림·행 상태 | 반영 여부 |

### 3.4 상태
`status`: `draft`(작성 중, `step` 1~4) · `generating`(생성 중) · `done`(완료) · `failed`(생성 멈춤). 장면 `status`: `waiting` · `writing` · `done` · `failed`. 장면 `locked`: 사용자가 SC4E 에서 직접 고치면 true.

---

## 4. 화면별 상세

### 4.0 UC_SC
§3.2 의 카드·다음 연결을 모두 구현 대상 연결로 본다.

### 4.1 SC0 · 작업 목록
- 머리: 「공간 시나리오」, 「고객 공간의 하루 · 동선을 장면으로 풀고, 장면마다 삼성 제품 · 솔루션 활용을 넣습니다.」, 주 버튼 「새 시나리오」(→ SC1).
- 시작 카드: 「빈 시나리오로 시작」 「유형 → 공간 시나리오 → 솔루션 · 제품 → 생성」(→ SC1), 「업종 템플릿으로 시작」 「16개 업종 · 대표 공간 · 장면 프리셋」(→ SC1T), 「조감도에서 이어 만들기」 「조감도 존과 배치 제품을 공간으로 가져오기」(→ SC1B).
- 조감도 변경 알림(연결 유지한 조감도가 바뀐 시나리오가 있을 때만): 「{조감도 제목}」 「조감도가 {M월 D일}에 바뀌었어요.」 「연결된 시나리오 {n}개의 공간 · 제품을 다시 맞출까요?」 + 「변경 반영하기」(→ SC1B 변경 반영 모드) + 닫기(aria 「닫기」, 같은 변경은 다시 보이지 않음). 여러 조감도가 바뀌었으면 가장 최근 1건만 보이고 나머지는 행 상태로.
- 필터: 「전체」 「작성 중」 「생성 중」 「완료」(각 개수), 검색(라벨 「시나리오 검색」, placeholder 「시나리오 · 고객 · 공간 검색」), 드롭다운 「시작 방식 · 전체」(전체/직접 입력/업종 템플릿/조감도), 정렬 「최근 수정순」.
- 표 머리: 「시나리오 · 고객」 「시작 방식」 「유형」 「장면」 「상태」 「수정」.

| 열 | 표시 | 규칙 |
|---|---|---|
| 시나리오 · 고객 | 제목(링크 = route) + 「{고객} · {공간}」 (「A 커피 프랜차이즈 · 매장」) | 프로젝트 고객, 대표 공간 |
| 시작 방식 | 「직접 입력」 / 「업종 템플릿 · {업종 약칭}」(「업종 템플릿 · 의료」, 「업종 템플릿 · 교육 · 캠퍼스」) / 「조감도 · {조감도 제목}」 | `start_mode` |
| 유형 | 「with 솔루션」 / 「without」 | `type` |
| 장면 | 장면 수 | — |
| 상태 | 완료: 「완료」 + 「제안서에 사용 중」 또는 「제안서에 아직 안 넣음」 · 작성 중: 「작성 중」 + 「{step} / 4 · {단계 이름}」(「3 / 4 · 솔루션 · 제품 입력」) 또는 「조감도가 바뀌었어요」 · 생성 중: 「생성 중」 + 「장면 {k} / {n} 작성 중」 · 실패 **(신규)** 「생성 멈춤」 + 「다시 시도」 | `status`, `step`, 조감도 변경, 사용 등록 |
| 수정 | 「방금」/「오늘 HH:mm」/「어제 HH:mm」/「M월 D일」 | `updated_at` |
| 동작 | 완료 행만 보내기 아이콘(aria 「제안서로 보내기」, title 「제안서로 보내기 · 내보내기」 → SC5) + 「더 보기」(aria, **(신규)** 메뉴: 열기 · 복제 · 삭제) | — |

- 꼬리: 「{total}개 중 {a}–{b}」, 「완료된 시나리오는 보내기 아이콘으로 제안서 · PDF로 바로 넘길 수 있어요」.
- route 규칙: 완료 → SC4, 생성 중 → SC4G, 작성 중 → 현재 단계 화면(1 SC1, 2 SC2 또는 SC2E(타임라인 편집을 거쳤으면), 3 SC3), 실패 → SC4G(다시 시도 상태).
- 빈 목록 **(신규)** 「아직 시나리오가 없어요」 + 시작 카드 3.

### 4.2 SC1 · 유형 선택 (1/4)
- W: 「공간 시나리오는 고객의 공간에서 하루 또는 특정 상황이 어떻게 흘러가는지를 이야기로 풀고, 그 안에 삼성 제품의 활용 장면을 넣습니다. 솔루션을 함께 엮을지 먼저 정해주세요.」
- 작업 카드 머리: 「시나리오 유형 · 하나 선택 · 1 / 4」.

| 카드 | 제목 · 부제 | 설명(보드) | 예시 태그 |
|---|---|---|---|
| WITH(기본 선택) | 「WITH 솔루션」 「솔루션 + 연관 제품 활용」 | 「시나리오 속에 MagicINFO·SmartThings Pro 같은 솔루션이 동작하는 장면과, 그 솔루션에 연결된 제품 활용을 함께 넣습니다. 운영·관리 효과를 보여줄 때 적합.」 | 「본사 원격 배포 장면」 「에너지 자동 제어」 (카드 그림 라벨 「솔루션」 「매장」 「본사」) |
| WITHOUT | 「WITHOUT 솔루션」 「제품 활용만」 | 「고객의 공간 시나리오에 제품이 쓰이는 장면만 넣습니다. 하드웨어 중심 제안이나 솔루션 도입 전 단계에 적합.」 | 「메뉴보드 시청 장면」 「키오스크 주문」 (그림 라벨 「매장」) |

- 「조감도 추가」 카드: 태그 「선택 · 기본 꺼짐」(꺼짐) / 「켜짐」(켜짐), 설명 「장면이 일어나는 위치를 공간 조감도 위에 번호로 표시해 시나리오와 함께 넣습니다.」, 토글(aria 「조감도 추가」, `aria-pressed`). **기본 꺼짐.**
- 켜짐일 때만 선택지(단일, 기본 「새로 만들기」): 「새로 만들기」 「시나리오 공간으로 조감도 생성」 / 「기존 조감도 연결」 「조감도 작업 {n}개에서 고르기」(n = 내 조감도 수, 고르면 조감도 선택 팝오버 — 「{제목} · 존 {k}」 목록).
- 주 버튼 「공간 시나리오 입력」(→ 시나리오 생성/갱신 → SC2).
- 「새로 만들기」의 효과: SC3 제출 시점(공간·제품이 정해진 뒤) birdseye 에 조감도 초안을 만든다 — `POST /api/birdseye/v1/birdseyes {title:'{시나리오 제목} 조감도', description:{시나리오 공간 문장}, prefill:{products}, origin:{service:'scenario', ref}}`. 조감도는 사용자가 이어서 완성한다(배치는 사용자가 확인해야 하므로 자동 3D 생성은 하지 않음). 「기존 조감도 연결」은 `birdseye_link` 만 저장.

### 4.3 SC1T · 업종 템플릿에서 시작
- W: 「업종을 고르면 그 업종 도입사례에 자주 나온 공간과 장면으로 시나리오 골격을 미리 채워 드립니다.」
- 머리: 「업종 16개」 「· 삼성 B2B 도입사례로 나눔 · 공간 · 장면 프리셋 포함」, 검색(라벨·placeholder 「업종 · 공간 검색」 — 업종명·대표 공간 부분 일치로 타일 거르기).
- 타일 16개(§10.4 시드 순서): 이름, `spaceLine`(대표 공간 「 · 」 연결), `presetLine`(프리셋 제목 「 · 」 연결), 선택 표시. 기본 선택 = 프로젝트 업종에 대응하는 코드(없으면 `FB`).
- 패널 머리: 「{업종 이름}」 「· 장면 프리셋 하나 선택 · 1 / 4」, 「유형」 세그먼트 「WITH 솔루션」(기본) / 「WITHOUT」.
- 프리셋 카드 3장(단일 선택, 기본 1번): 제목 `t`, 배지 「장면 4」, 흐름 `f`(「오픈 → 점심 피크 → 본사 배포 → 마감」), 역할 `r`(「점장 · 손님 · 본사 담당자」).
- 「대표 공간」 칩(그 업종 `spaces`), 「장면에 담을 요구」 칩(`needs`), 「솔루션 · 제품 단계에 미리 채움」 「· 이 업종에서 자주 쓰인 순」 + `usedLine`(`used` 「 · 」 연결).
- 버튼: 「빈 시나리오로」(→ SC1), 주 버튼 「이 골격으로 시작」(→ 골격 job → SC2E).
- 골격 규칙: 시간대 = 흐름 단계 4개(라벨 = 단계 이름, 시각 = 프리셋 제목에 「하루」가 들어가면 LLM 이 대표 시각 제안, 아니면 비움), 역할 = `r` 를 「 · 」로 나눈 것, 장면 = 시간대마다 1개(역할별 한 줄 비트는 LLM 초안), 공간 후보 = `spaces`, 요구 = `needs`(장면 작성 근거), 솔루션·제품 미리 채움 = `used` 를 KB `A1` 로 해소(솔루션 → 솔루션 칩, 제품 카테고리 → SC3 추천 칩). WITHOUT 이면 솔루션 미리 채움을 버린다. 업종 `used` 순위는 시드 순서를 쓰고, 대응 KR 업종이 있으면 KB `D2`(사례 통계)로 다시 정렬할 수 있다.

### 4.4 SC1B · 조감도에서 이어 만들기
- 메아리: 「조감도에서 이어 만들기」 「· {유형}」(기본 「with 솔루션」).
- W: 「조감도의 존을 시나리오 공간으로 가져옵니다. 존에 배치된 제품도 함께 넘어와 장면에 바로 들어갑니다.」
- 「조감도 작업」 목록(단일): 「{제목}」 「· 존 {n}」(존 포인트가 있는 내 조감도·팀 공유 조감도, `?birdseye=` 가 있으면 그것을 선택). 링크 「조감도 열기」(→ BE5).
- 평면 미리보기(birdseye `handoff.plan_preview`): 「존 포인트 {n}」 「{평}평 · 층고 {h}m」 「{창 라벨}」, 존 번호 원, 범례 「삼성 제품」 「가구」.
- 「가져올 존」 「· {k} / {n} 선택」, 「모두 선택」. 존 행: 체크, 번호, 이름, 부제, 장면 배지:

| 존 상태 | 부제 규칙(보드 예) | 기본 | 배지 |
|---|---|---|---|
| 제품 있음 | 「{제품 라벨} · {존 의미 한 줄}」 (「OH55C ×3 · 거리에서 보이는 첫인상」, 「The Wall IAB 146" · 입장 후 시선이 닿는 곳」, 「Flip Pro WA75D · 직원이 설명하는 자리」) | 포함 | 「장면 {k}」 |
| 가구만 | 「가구만 배치 · 제품은 다음 단계에서 추천」 | 포함 | 「장면 {k}」 |
| 아무것도 없음(랩핑 포인트 등) | 「배치 제품 없음 · 랩핑 포인트만 지정」 | 제외(점선 행) | 「제외」 |

- 작업 카드 머리 「가져오기 설정」 「· 존 {k}개 → 장면 {k}개 · 2 / 4」, 링크 「존 포인트 다시 지정」(→ BE5Z).
- 「시나리오 축」(단일, LLM 이 공간 유형·업종으로 3개 제안, 첫째 기본): 예 「방문객 동선」 「매장 하루」 「런칭 이벤트 당일」.
- 「동선 순서」: 칩 「{순번} {존 짧은 이름}」(「1 쇼윈도」 「2 미디어월」 「3 체험 · 시연 존」 「4 라운지 · 상담」), 「끌어서 순서 바꾸기」. 기본 순서 = 조감도의 동선 순서 번호.
- 체크 「조감도와 연결 유지」 「· 배치가 바뀌면 알려드려요」(기본 켬).
- 버튼: 「이전」(→ SC0), 주 버튼 「존으로 장면 만들기」(→ 가져오기 job → SC2E). 가져오면 birdseye `usages` 에 이 시나리오를 등록한다.
- 축별 골격: 「방문객 동선」 = 시간대 대신 순서 단계(라벨 = 존 짧은 이름, 시각 없음), 역할 = 방문객 + 직원; 「매장 하루」·「…당일」 = 시각 있는 시간대(LLM 제안), 장소 = 존. 장면 k 의 장소·제품 = 존 k 의 것.
- **변경 반영 모드**(SC0 「변경 반영하기」): 같은 화면에 **(신규)** 변경 요약 줄 「존 {a}개 바뀜 · 제품 {b}개 바뀜」과 존 행의 변경 배지(「새로」/「바뀜」/「없어짐」), 주 버튼 **(신규)** 「바뀐 곳 반영하기」 — 장면의 장소·제품만 갱신하고 문장은 그대로 두며, 제품이 바뀐 장면에 「이야기 확인」 표시와 이미지 `stale` 를 건다.

### 4.5 SC2 · 공간 시나리오 입력 (2/4)
- 메아리: 「{유형 소문자}」 「· {유형 부제}」 (「with 솔루션」 「· 솔루션 + 연관 제품 활용」).
- W: 「고객 공간에서 벌어지는 시나리오를 적어주세요. 하루의 흐름(오픈 → 피크 → 마감)이나 특정 상황(신메뉴 출시일)처럼 시간 축이 있으면 장면을 나누기 좋습니다. 등장인물(점장, 손님, 본사 담당자)도 함께 적어주세요.」 + 「Tip」 「Storyboard나 조감도 작업이 있다면 사이드바에서 끌어와 공간·고객 정보를 재사용할 수 있습니다.」
- 작업 카드 머리 「공간 시나리오 · 2 / 4」.
- 「예시 골격」 칩 3개: 업종을 알면 그 업종 프리셋 제목 앞 2개 + 「장애 발생 상황」, 모르면 「매장 하루」 「신메뉴 출시일」 「장애 발생 상황」(보드). 누르면 골격 문장(§10.6)을 입력칸 끝에 덧붙인다(지우지 않음).
- 입력: 라벨 「공간 시나리오 입력」, textarea(≤ 3,000자). 보드 예 값:
  ```
  07:00 점장이 매장을 오픈한다. 메뉴보드가 아침 메뉴로 켜져 있어야 한다.
  11:30 점심 피크. 주문 줄이 길어지고 프로모션 음료가 잘 팔린다.
  14:00 본사 마케팅팀이 전국 320개 매장에 오후 프로모션을 배포한다.
  21:00 마감. 메뉴보드가 자동으로 꺼지고 전력 사용량이 집계된다.
  ```
- 「등장인물」 칩(「점장 ×」 「손님 ×」 「본사 마케팅 담당자 ×」): 입력이 멈추고 1초 뒤 LLM 이 문장에서 역할을 뽑아 채운다(사용자가 지운 역할은 다시 넣지 않음). 라벨 「등장인물 추가」, placeholder 「추가…」.
- 드롭 영역(사이드바 작업 항목 — 셸 드래그 데이터 `type:'work_item'`, `feature ∈ {birdseye, storyboard}`, 00-shell §5.7; 받는 유형 칩 「{기능} 작업 (사이드바)」): 조감도 항목 → `handoff` 의 공간·제품을 문장 끝에 「[공간] …」 줄로 덧붙이고 `birdseye_link`(연결 유지 끔) 저장. Storyboard 항목 → workspace 항목 요약(고객·공간 줄)만 덧붙인다(§11).
- 버튼: 「이전」(→ SC1), 주 버튼 「솔루션 · 제품 입력」(→ 파싱 job → R2: SC3 또는 SC2E). 입력이 10자 미만이면 비활성.
- 실존 인물 이름이 입력에 있으면 파싱 때 역할명으로 바꾸고 **(신규)** 안내 「실제 인물 이름은 역할로 바꿔 썼어요」.

### 4.6 SC2E · 타임라인 · 페르소나 편집
- W: 「입력하신 하루를 시간대 × 역할로 나눴어요. 장면을 끌어 옮기거나 빈 칸에 추가하고, 오른쪽에서 인물을 다듬어 주세요.」 (장면 > 6 으로 들어왔으면 **(신규)** 「장면이 {n}개로 많아요. 같은 시간 장면을 합쳐 보세요.」를 덧붙임)
- 머리: 「타임라인」 「· 시간대 {s} · 역할 {r} · 장면 {n}」, 되돌리기(aria 「되돌리기」)/다시 실행(aria 「다시 실행」), 추가 버튼 「시간대」 「역할」.
- 격자: 왼쪽 위 「역할 \ 시간」. 열 = 시간대(「07:00」 「오픈」, 「11:30」 「점심 피크」, 「14:00」 「본사 배포」, 「18:00」 「새 시간대」 배지 「저녁 퇴근길」, 「21:00」 「마감」). 행(레인) = 역할(머리글자 원 「점」 + 이름 「점장」 + 그 역할이 나오는 장면 수 「장면 {k}」).
- 장면 카드(비트): 「장면 {n}」(그 장면의 첫 역할) 또는 「장면 {n} · {역할} 시점」(같은 장면의 다른 역할), 한 줄 내용(「아침 메뉴로 켜진 메뉴보드 확인」), 장소 칩(「카운터」). 끌어서 다른 칸으로 옮기면 놓는 칸에 「여기에 놓기」, 원래 칸에 「원래 위치」, 끌리는 카드 「새 장면 · 이동 중」(새로 만든 비트일 때). 빈 칸 「+」(aria 「장면 추가」) 「장면」.
- W 추천 장면 카드(빈 시간대·역할 칸에, 최대 1개): 「W」 「추천 장면」 「{내용}」(「퇴근길 모바일 주문 픽업」) + 「추가」 「닫기」.
- 「역할 추가」, 「추천 역할」 「+ {역할}」(「+ 바리스타」 「+ 배달 라이더」 — 업종 프리셋 역할 + LLM), 「· 레인을 끌어 순서를 바꿀 수 있어요」.
- 오른쪽 「인물 · 페르소나」 「· {r}명」 + 「추가」. 인물 목록(머리글자 · 이름 · 「장면 {목록 ' · '}」 — 「장면 1 · 4 · 새 장면」). 선택 인물 상세: 「역할 이름」(값 「점장」), 「한 줄 소개」(값 「매장 운영 책임자 · 오픈과 마감 담당」), 「원하는 것」 칩(「바쁜 시간 손 덜기」 「표기 실수 없애기」) + 추가(aria 「추가」), 「불편한 점」 칩(「메뉴판 수작업 교체」 「공지 늦게 받음」) + 추가, 안내 「인물을 바꾸면 그 레인의 장면 문장에 반영돼요」. 페르소나는 첫 파싱 때 LLM 이 초안을 쓴다.
- 하단 머리 「타임라인 편집」 「· 2 / 4」, 상태 「변경 {n}건 · 자동 저장됨」. 버튼 「장면 나누기」(선택 장면의 비트를 두 장면으로), 「같은 시간 장면 합치기」(시간대마다 장면 하나로), 「빈 시간대 정리」(비트 없는 시간대 삭제), 링크 「텍스트로 보기」(→ SC2, 타임라인을 시각 줄 텍스트로 직렬화; 텍스트를 고쳐 다시 넘기면 다시 파싱하며 **(신규)** 확인 「텍스트를 고치면 타임라인을 다시 나눠요」).
- 입력: 라벨 「편집 요청」, placeholder 「요청 (예: 손님 레인 18:00에 퇴근길 픽업 장면 추가, 점장 장면은 한 문장으로 짧게)」 → LLM 타임라인 연산(job, 짧음) → 적용 → 변경 수 증가.
- 버튼: 「이전」(→ SC2), 주 버튼 「솔루션 · 제품 입력」(→ SC3).
- 장면 번호 = 시간대 순서 → 같은 시간대 안에서는 만든 순서. 비트를 다른 시간대로 옮기면 그 시간대 첫 장면에 들어가고 번호가 다시 매겨진다. 모든 편집은 즉시 저장(연산 로그, 되돌리기 50단계).
- 페르소나 저장 시 그 레인 비트 문장 재작성 job → 끝나면 비트 갱신(진행 중 레인 위 **(신규)** 「문장 다듬는 중」).

### 4.7 SC3 · 솔루션 · 제품 입력 (3/4)
- 메아리: 「{시각} {라벨} → … · {역할 ' / '}」 (「07:00 오픈 → 11:30 점심 피크 → 14:00 본사 프로모션 배포 → 21:00 마감 · 점장 / 손님 / 본사 마케팅 담당자」).
- W: 「{n}개 장면으로 나눌 수 있겠네요. 시나리오에 넣을 솔루션과 제품을 입력해 주세요. 솔루션을 고르면 연관 제품을 추천해 드립니다.」 (WITHOUT 이면 **(신규)** 「{n}개 장면으로 나눌 수 있겠네요. 시나리오에 넣을 제품을 입력해 주세요.」)
- 장면 칩: 「장면 {n} · {라벨}」(「장면 1 · 오픈」 …).
- 작업 카드 머리 「솔루션 · 제품 · 3 / 4」.
- 「솔루션」(WITH 만): 「솔루션 탐색에서 고르기」(상단바 솔루션 탐색, 드롭 `accepts=['solution']`), 칩 「MagicINFO」 「SmartThings Pro」 + 제거(aria 「제거」), 라벨 「솔루션 입력」 placeholder 「솔루션명 입력…」(자동완성: KB 솔루션 + Winmate 솔루션 11개).
- 「제품」 + 추천이 있으면 「· {솔루션} 연관 제품 추천됨」(「· MagicINFO 연관 제품 추천됨」): 「제품 탐색에서 고르기」(드롭 `accepts=['product']`), 칩 「Smart Signage QM55C」 「Kiosk KM24C」 + 제거, 추천 칩(점선) 「추천: {약칭 또는 표시명}」(「추천: Outdoor OH55C」 「추천: Galaxy Tab Active5」) — 누르면 제품 칩으로, 라벨 「제품 입력」 placeholder 「제품명 입력…」.
- 버튼: 「이전」(→ SC2 또는 SC2E — 들어온 곳), 주 버튼 「시나리오 생성」(→ R4: SC3R 또는 SC4G).
- 솔루션·제품 0개면 주 버튼 비활성(WITHOUT 은 제품 ≥ 1 필요).
- 추천 계산: KB `D5`(사례에서 그 솔루션과 함께 쓰인 제품 카테고리, lift 순) ∩ KB `C2`(장면 공간 × 역량 후보) + 시나리오 문장의 제품·카테고리 언급(A1: 「태블릿으로 재고 확인」 → 갤럭시 탭 액티브) → 최대 3개, 이미 고른 것 제외.

### 4.8 SC3R · 장면별 솔루션 추천
- 메아리: 「{유형}」 「· 제품만 · {제품 라벨 ' · '}」 (「without 솔루션」 「· 제품만 · Smart Signage QM55C ×3 · Kiosk KM24C」).
- W: 「제품만으로도 {n}개 장면을 만들 수 있지만, 장면 {목록}는 솔루션이 있어야 이야기가 완성돼요. 입력하신 시나리오 문장과 {업종 이름} 도입사례를 근거로 장면별 솔루션을 추천합니다.」 (보드 예: 「장면 3 · 4는」, 「외식 · 카페 도입사례」). WITH 인데 솔루션 0개로 들어온 경우 **(신규)** 「솔루션을 고르지 않아 장면별로 어울리는 솔루션을 추천합니다.」
- 머리 「장면별 솔루션 추천」 「· 적용 {a} · 제품만 {b}」, 근거 줄 「근거 · 입력한 시나리오 문장 · {업종 이름} 도입사례」, 버튼 「모두 적용」.
- 장면 행: 「{시각}」 「장면 {n}」, 제목 「{라벨} — {한 줄}」(「오픈 — 메뉴보드가 아침 메뉴로 켜진다」), 제품만 줄 「제품만 · {제품만일 때 모습}」(「제품만 · 점장이 출근해 메뉴보드 3대를 직접 켠다」), 근거 줄 「근거」 + 아래 중 하나:
  - 입력 인용: 「입력」 「‘{입력 문장 일부}’」 (+ 사례 수가 있으면 「· {업종 약칭} 사례 {n}건」 — KB 에서 못 세면 「[00]」, 보드 예 「· 카페 사례 [00]건」)
  - 「제품만으로 장면이 완성돼요」
- 추천 솔루션: 「{솔루션} · {동작}」(「MagicINFO · 전원 스케줄」), 태그 「추천」/「선택」/「꼭 필요」, 효과 한 줄(「시간 맞춰 자동 점등」). 「선택」 태그의 솔루션 이름 앞에 「+」(「+ MagicINFO · 시간대 레이아웃」)와 효과 자리에 「제품만으로 충분해요」.
- 적용 토글(aria 「장면 {n} 추천 적용」, `aria-pressed`): 기본 = 「추천」·「꼭 필요」 켬, 「선택」 끔.
- 오른쪽 「솔루션 · 제품 · 3 / 4」, 「시나리오 유형」 「WITHOUT」 → 「WITH 솔루션」, 안내 「적용하면 시나리오 유형이 with 솔루션 으로 바뀌고 {적용 솔루션 ' · '}가 솔루션 칸에 들어가요.」, 「장면 {끈 장면}는 제품만 유지 · 솔루션 장면은 결과에서 이야기 · 솔루션 동작 · 제품 활용으로 나뉩니다.」(끈 장면이 없으면 앞 구절 생략). 적용 0 이면 안내 대신 **(신규)** 「제품만으로 만들어요」.
- 링크 「솔루션 직접 고르기」(→ SC3). 버튼: 「이전」(→ SC2), 「제품만으로 생성」(유형 WITHOUT 유지, 솔루션 없이 → SC4G), 주 버튼 「추천 적용 · 시나리오 생성」(켠 추천 적용 → 유형 with(적용 ≥ 1) → SC4G).
- 태그 판정(§7.5): 「꼭 필요」 = 장면 문장이 솔루션만 할 수 있는 동작을 요구(예 다수 매장 일괄 배포), 「추천」 = 문장 속 수작업을 솔루션이 자동화, 「선택」 = 제품만으로 장면이 완성.

### 4.9 SC4G · 생성 중
- W: 「{n}개 장면으로 시나리오를 쓰고 있어요. 끝난 장면부터 아래에 미리 보여드릴게요.」
- 진행 카드(완료 후 누르면 SC4): 「시나리오 생성 중」, 「{유형 소문자} · {솔루션 ' · '} · {제품 라벨 ' · '}」(「with 솔루션 · MagicINFO · SmartThings Pro · QM55C ×3 · KM24C」), 「{pct}% · 약 {t} 남음」(「50% · 약 20초 남음」; 07 §10.5 규칙).

| 단계 | 메모 템플릿(보드 예) |
|---|---|
| 「장면 나누기」 | 장면 라벨 나열(「오픈 · 점심 피크 · 본사 배포 · 마감」) |
| 「장면별 이야기 쓰기」 | 「장면 {k} · {라벨} 작성 중 ({done} / {n} 완료)」 (「장면 3 · 본사 배포 작성 중 (2 / 4 완료)」) |
| 「솔루션 동작 · 제품 연결」 | 솔루션별 장면 수(「MagicINFO 3장면 · SmartThings Pro 1장면」) |
| 「확인 필요 표시」 | 「근거 없는 수치는 [00]으로 두고 표시」 |
상태 문구 「완료」 「진행 중」 「대기」.

- 「미리보기」 「· 끝난 장면부터」 「{done} / {n}」: 장면 카드 — 완성: 시각·번호·제목·솔루션/제품 칩 + 「완성」; 작성 중: 시각·번호·제목·부분 이야기(스트리밍) + 「작성 중」; 대기: 시각 + 「장면 {n} · {라벨}」 + 「대기」.
- 하단 머리 「시나리오 생성 중」 「· 4 / 4 · 다른 작업을 해도 돼요, 끝나면 알려드릴게요」.
- 버튼 「작업 목록에서 기다리기」(→ SC0). 입력: 라벨 「진행 방향 메모」, placeholder 「진행 중에도 방향을 알려주세요 (예: 장면 3은 본사 담당자 시점으로)」 → jobs 조종 메모(다음 장면 작성부터 반영, 이미 쓴 장면은 그대로 — **(신규)** 안내 「이미 쓴 장면은 결과에서 고칠 수 있어요」). 링크 「중지 · 입력 고치기」(job 취소 → 끝난 장면 보존 → SC3).
- 실패(「생성이 멈추면 → SC4G 다시 시도」): **(신규)** W 「시나리오를 쓰다가 멈췄어요. {사유}」 + 「다시 시도」(같은 thread 에서 마지막으로 끝난 노드 다음부터 재개 — 끝난 장면은 다시 쓰지 않음) + 「입력 고치기」(→ SC3).
- 완료: 알림 **(신규)** 「{제목} · 시나리오 완성」(링크 SC4). 화면이 열려 있으면 SC4 로 자동 이동.

### 4.10 SC4 · 시나리오 생성 (4/4)
- W: 「{n}개 장면으로 시나리오를 구성했습니다. 각 장면은 이야기 · 솔루션 동작 · 제품 활용으로 나뉘며, 장면별 이미지는 '이미지 생성'으로 바로 만들 수 있습니다.」 (WITHOUT 이면 **(신규)** 「각 장면은 이야기 · 제품 활용으로 나뉘며, …」)
- 장면 카드(누르면 SC4E): 「{시각}」 「장면 {n}」, 제목 「{라벨} — {한 줄}」(「오픈 — 메뉴보드가 아침 메뉴로 스스로 켜진다」), 이야기(1~2문장, 「점장이 도착하기 전, 전날 본사가 예약한 스케줄에 따라 QM55C 3대가 자동 점등되고 아침 메뉴 레이아웃이 표시된다.」), 칩: 솔루션 동작(파랑, 「MagicINFO · 전원 스케줄」) + 제품(회색, 「QM55C ×3」 「KM24C」 「QM55C」). 오른쪽: 장면 이미지가 있으면 썸네일(92×62), 없으면 버튼 「이미지 생성」. `[00]` 토큰은 강조 표시.
- 「이미지 생성」(장면 하나): image 요청 생성(`POST /api/image/v1/requests` + `:start`, §7.8) → IMG2(미리 채움)로 이동. 돌아와서 결과가 충족되면 자동으로 장면에 붙는다.
- 작업 카드 머리 「시나리오」 「· 4 / 4 · 완료」(스텝 4/4 — 장면 수가 아님). 링크 「장면 추가」(→ SC2E), 버튼 「더 짧게」(모든 장면 이야기 줄이기 job, 장면별 새 버전), 「장면별 이미지 모두 생성」(이미지 없는 장면 일괄 렌더, 카드에 **(신규)** 「이미지 만드는 중」), 링크 「조감도 추가」(조감도 연결이 있으면 BE5Z 장면 연결 모드, 없으면 **(신규)** 팝오버 「조감도 연결」 — SC1 의 「새로 만들기」/「기존 조감도 연결」 선택지 재사용).
- 입력: 라벨 「수정 요청」, placeholder 「수정 요청 (예: 장면 2에 점장이 태블릿으로 재고 확인하는 장면 추가)」 → LLM 시나리오 연산(비트 추가·제품 추가·장면 추가·문장 수정) → 영향 장면만 다시 쓰기 job(카드 위 **(신규)** 「장면 {n} 다시 쓰는 중」), 화면 이동 없음.
- 버튼: 「저장」(버전 스냅샷 → **(신규)** 토스트 「저장했어요 · v{n}」), 주 버튼 「제안서에 넣기」(→ SC5).

### 4.11 SC4E · 장면 편집
- 왼쪽: 「장면」 「{n}」 + 링크 「타임라인 편집」(→ SC2E). 장면 목록 행: 「{시각}」 「장면 {n}」 상태(「편집 중」(현재) / 「이미지 없음」 / **(신규)** 「이미지 확인」(stale) / 없음), 제목 짧은 형(「점심 피크 — 키오스크로 주문 분산」), 대표 솔루션 동작(「MagicINFO · 시간대 레이아웃」). 「장면 추가」(현재 장면 다음 시간대에 빈 장면 → 편집), 링크 「나머지 장면 다시 생성」(→ SC4G, `locked` 아닌 장면만) + 「직접 고친 장면 {목록}는 그대로 둡니다」(「직접 고친 장면 2는 그대로 둡니다」; locked 0 이면 숨김).
- 편집기 머리: 「{시각}」 「장면 {n}」 「{라벨}」, 버전 「v{k}」 「· {변경 이유}」(「v2」 「· 방금 수정 요청 반영」), 「v{k-1}로 되돌리기」(k ≥ 2), 삭제(aria 「장면 삭제」, **(신규)** 확인 「장면 {n}을 지울까요? 번호가 다시 매겨져요.」).
- 필드: 「장면 제목」 입력(값 예 「점심 피크 — 줄이 길어지자 키오스크로 주문이 분산된다」), 「이야기」 + 「바뀐 곳 {k}」(직전 버전 대비 추가 문장 강조 — 「점장은 Galaxy Tab Active5로 재고를 확인하고, 품절 메뉴를 메뉴보드에서 바로 내린다.」), 「등장인물」 칩(「손님 ×」 「점장 ×」 + 새로 붙은 것 「새로」 배지) + 「+ 추가」, 「솔루션 동작」 칩(「MagicINFO · 시간대 레이아웃 ×」 「MagicINFO · 즉시 변경 ×」 「새로」) + 「+ 솔루션」(시나리오 솔루션의 동작 사전 목록에서), 「제품 활용」 칩(「KM24C ×」 「QM55C ×」 「Galaxy Tab Active5 ×」 「새로」) + 「+ 제품」. 「새로」 = 직전 버전에 없던 항목. WITHOUT 이면 솔루션 동작 영역 숨김.
- 「장면 이미지」: 「v{k} · {출처} · {상대 시각}」(「v1 · 이미지 생성 · 어제」), 이미지 + 비율 배지 「16:9」, stale 경고 「이야기가 바뀌어 이미지와 다를 수 있어요 ({빠진 요소})」(「(태블릿 장면 없음)」), 버튼 「이미지 생성에서 다시 만들기」(→ IMG2 미리 채움), 「이미지 생성으로 넘어가는 것」 표: 「공간」 「{장소}」(「카페 카운터 · 주문 구역」), 「장면」 「{요약}」(「점심 피크, 키오스크 주문 + 재고 확인」), 「제품」 「{약칭 ' · '}」(「KM24C · QM55C · Tab Active5」), 「비율」 「16:9 · 제안서 시트용」. 링크 「사내 자산 · 내 이미지에서 고르기」(→ IMG0 고르기 모드 — 고른 버전이 이 장면에 붙음). 이미지가 없으면 이미지 자리에 **(신규)** 「아직 이미지가 없어요」 + 같은 두 버튼.
- 「이 장면만 다시 쓰기」 「· 다른 장면은 그대로」: 칩 「더 짧게」, 「{다른 역할} 시점으로」(장면에 나오는 역할 중 현재 주 시점이 아닌 것, 보드 예 「점장 시점으로」), 「솔루션 동작 더 구체적으로」(WITH 만). 입력: 라벨 「이 장면 수정 지시」, placeholder 「지시문 (예: 키오스크 대기 줄이 줄어드는 순간을 강조)」, 보내기(aria 「이 장면 다시 쓰기」) → 장면 다시 쓰기 job → 새 버전(v+1).
- 버튼: 「취소」(편집 버림 → SC4), 주 버튼 「변경 저장」(직접 고친 필드가 있으면 `locked=true`, 새 버전 → SC4).
- stale 판정(결정적): 이미지 생성 시점의 조건 스냅샷(제품·인물·솔루션)과 현재 장면 비교 → 새로 생긴 제품의 KB 카테고리 일반명(갤럭시 탭 → 「태블릿」) 또는 새 인물 → 「({요소} 장면 없음)」, 여러 개면 「 · 」로.

### 4.12 SC5 · 제안서로 보내기 · 내보내기
- 메아리: 「제안서에 넣기」.
- W: 「시나리오를 제안서 '공간별 가치 제공 시나리오' 섹션에 넣을게요. 장면 {n}개를 공간 기준으로 묶어 시트 {k}장으로 나눴어요. 넣기 전에 어떻게 들어가는지 확인하세요.」
- 「보낼 곳」: 버튼(누르면 제안서 선택 팝오버) 「{제안서 제목}」 「· 공간별 가치 제공 시나리오」 + 상태 「작성 중」(「A 커피 프랜차이즈 메뉴보드 제안」), 링크 「새 제안서로 시작」(→ PR1L, 이 시나리오 연결). 기본 = 같은 프로젝트의 진행 중 제안서 중 최근 것.
- 시트 미리보기(§7.9 계획 그대로):

| 시트 | 머리(보드 예) | 내용 |
|---|---|---|
| 시트 1 | 「시트 1 · 공간 × 솔루션 맵」 「VM-A」 「장면 1–4 요약」 「공간 2 × 솔루션 2 격자」 「칸마다 장면 한 줄 요약」 | 행 = 공간(「매장 카운터」 「본사 운영실」), 열 = 솔루션(「MagicINFO」 「SmartThings Pro」), 칸 = 장면 시각(+ 이미지가 있으면 썸네일) |
| 시트 2 | 「시트 2 · 매장 카운터」 「SS-A」 「장면 1」 「장면 2」 「장면 4」 「시간대 장면 3개 · 이미지 1 / 3」 「이야기 · 솔루션 동작 · 제품」 | 칩 「MagicINFO」 「QM55C」 「가치」 「[00]」 |
| 시트 3 | 「시트 3 · 본사 운영실」 「SS-B」 「장면 3」 「확정 필요 1」 「MagicINFO → QM55C → 배포 시간」 「가치 수치는 [확정 필요]로 표시」 | 솔루션 → 제품 → 가치 사슬 |

- 「함께 넘어가는 것」 「장면 텍스트 {n} · 솔루션 {s} · 제품 {p} · 이미지 {i} · 확정 필요 {c}」(보드 예 「장면 텍스트 4 · 솔루션 2 · 제품 2 · 이미지 1 · 확정 필요 1」). 링크 「시트 구성 바꾸기」(→ 제안서 PRX3 레이아웃 고르기, 웹 이동). 이미지 없는 장면이 있으면 「이미지가 없는 장면 {m}개는 시트에 이미지 자리만 남겨요.」 + 링크 「장면 이미지 먼저 만들기」(→ SC4E, 이미지 없는 첫 장면).
- 오른쪽 머리 「보내기 · 내보내기」 「· 시나리오 완료 · 장면 {n}」, 「마지막 저장 {상대 시각}」(「마지막 저장 방금」).
- 「파일로 받기」: 「PPTX · 시트 {k}장」, 「PDF」, 「장면 스크립트 DOCX」, 「장면 이미지 ZIP」(이미지 0장이면 비활성) — 각각 export job(202) → 완료 시 다운로드(**(신규)** 진행 표시 「만드는 중」).
- 「다른 기능으로」: 「장면 이미지 만들기」(→ IMG2, 이미지 없는 첫 장면 미리 채움), 「조감도 존에 장면 연결」(→ BE5Z 장면 연결 모드; 조감도 연결이 없으면 SC4 의 「조감도 연결」 팝오버).
- 버튼: 「이전」(→ SC4), 「팀에 공유」(workspace 공유 링크), 주 버튼 「제안서에 넣기 · 시트 {k}장」(웹 → 제안서 가져오기, §8) → 성공 **(신규)** 토스트 「{제안서}에 시트 {k}장을 넣었어요 · 열기」, SC0 상태 「제안서에 사용 중」.

---

## 5. 데이터 모델 (`${DATA_DIR}/scenario/scenario.sqlite`)

### 5.1 표
```text
scenario        id 'sc_<ULID>' · owner · project_id? · customer_name? · title · space_label · vertical_code?(FB…)
                type(with|without) · start_mode(blank|template|birdseye) · template JSON? {industry, preset_index}
                birdseye_link JSON? {birdseye_id, linked_version, layout_version, zones_hash, keep_link:bool,
                                     changed:{at, version}?, axis, zone_ids:[…]}
                aerial JSON {enabled:false, source:'new'|'existing', birdseye_id?}
                raw_text TEXT · needs JSON [] · status(draft|generating|done|failed) · step INT(1..4)
                version INT · route · created_at · updated_at · deleted_at?
time_slot       id 'sct_' · scenario_id · ord INT · time TEXT? ('07:00') · label ('오픈') · is_new BOOL
role            id 'scr_' · scenario_id · ord · name · initial ('점') · intro · wants JSON [] · pains JSON []
                suggested BOOL · source(parsed|template|birdseye|user)
scene           id 'scs_' · scenario_id · slot_id · ord_in_slot · no INT · title · place · space_key · story
                beats JSON [{id, role_id, text, place, primary:bool}] · solutions JSON [{solution_id, action_code,
                label('MagicINFO · 전원 스케줄'), is_new}] · products JSON [{family_id, short, label, qty?, is_new}]
                characters JSON [{role_id, is_new}] · confirm_tokens JSON [{text:'[00]', near, kind:'number'}]
                evidence JSON [{kind:'input_quote'|'kb_message'|'kb_case', ref, text, source_url?}]
                image JSON? {image_id, version_id, aspect, created_at, source:'image_render'|'image_flow'|'picked',
                            snapshot:{products, characters, solutions}} · image_request_id?
                image_stale JSON? {missing:['태블릿']} · locked BOOL · status(waiting|writing|done|failed)
                version INT · zone_ref JSON? {birdseye_id, zone_id}
scene_version   scene_id · n · json(장면 스냅샷) · reason ('방금 수정 요청 반영') · created_at
solution_pick   scenario_id · solution_id · name · source(user|template|recommended) · ord
product_pick    scenario_id · family_id · label · short · qty? · source(user|template|birdseye|recommended) · ord
recommendation  scenario_id · scene_id · product_only_text · evidence JSON · solution_id · action_code
                benefit · tag(required|recommended|optional) · applied BOOL
op_log          id · scenario_id · target(timeline|persona|scene) · op JSON · inverse JSON · created_at · undone BOOL
sheet_plan      scenario_id · version · json [{n, code:'VM-A'|'VM-C'|'VM-D'|'SS-A'|'SS-B'|'SS-C', title, space_key?,
                scene_ids, images:{have, total}, confirm_count}]
usage           scenario_id · service('proposal') · ref · label · version · created_at
export          id 'sce_' · scenario_id · kind(pptx|pdf|docx|zip) · job_id · file_id? · created_at
```

### 5.2 장면 규칙
- 장면은 시간대에 속하고, 시간대마다 기본 1장면(「장면 나누기」로 여러 장면 가능). 비트 = 역할별 관점. 장면 번호 = (시간대 순서, 시간대 안 순서)로 1부터.
- 제목 형식 「{라벨} — {한 줄}」, 이야기 1~2문장 ≤ 120자, 비트 ≤ 40자, 장소 ≤ 16자.
- `space_key` = 장소를 시나리오 공간 목록으로 정규화한 키(시트 묶음 기준, §7.9). 예: 「카운터」「주문 대기 줄」「카운터 앞」「매장 전체」→ `매장 카운터`, 「본사 사무실」→ `본사 운영실`.

### 5.3 작업 색인(workspace)
`PUT /api/workspace/v1/items/{sc_id}` `{feature:'scenario', title, status:{code,label}, summary:'{고객} · {공간} · 장면 {n}', route, project_id}` — 생성·단계 이동·생성 완료·보내기 때.

---

## 6. API 스케치 (`/v1`, 게이트웨이 `/api/scenario/v1`)

### 6.1 시나리오
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `GET /v1/scenarios` | `status(all\|draft\|generating\|done)`, `start_mode?`, `q`, `sort`, `limit`, `cursor` | `{items:[Row], counts, alert?:{birdseye_id, title, changed_at, scenario_ids}, next_cursor}` — 응답 전에 연결 유지 조감도의 `GET /api/birdseye/v1/birdseyes/{id}/version` 을 확인(60초 캐시) |
| `POST /v1/scenarios` | `{type, aerial?:{enabled, source, birdseye_id?}, project_id?}` | 201 `Scenario` |
| `POST /v1/scenarios:from-template` | `{industry, preset_index, type}` | 202 `{job_id, scenario_id}` (골격) |
| `POST /v1/scenarios:from-birdseye` | `{birdseye_id, zone_ids, axis, order:[zone_id], keep_link, type}` | 202 `{job_id, scenario_id}` |
| `GET /v1/scenarios/{id}` · `PATCH` | `PATCH {type?, aerial?, title?, raw_text?, if_version}` | `Scenario` · 409 |
| `POST /v1/scenarios/{id}/birdseye:resync` | `{apply:bool}` | `{diff:{zones_changed, products_changed}}` / 적용 결과 |
| `POST /v1/scenarios/{id}:save` · `GET …/versions` · `POST …/versions/{n}/restore` | | |
| `DELETE /v1/scenarios/{id}` · `POST /v1/scenarios/{id}:clone` | | |

### 6.2 입력·타임라인
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `POST /v1/scenarios/{id}/input:parse` | `{raw_text, characters:[…]}` | 202 → 결과 `{next:'SC3'\|'SC2E', reason?}` |
| `POST /v1/scenarios/{id}/characters:extract` | `{raw_text}` (동기, 제한 5초) | `{characters:[…]}` |
| `GET /v1/scenarios/{id}/timeline` | — | `{slots, roles, scenes(비트 포함), suggestions:{scene?, roles:[…]}, changes_count}` |
| `POST /v1/scenarios/{id}/timeline/ops` | `{ops:[{op:'add_slot'\|'set_slot'\|'remove_slot'\|'move_beat'\|'add_beat'\|'set_beat'\|'remove_beat'\|'add_role'\|'set_role'\|'reorder_roles'\|'split_scene'\|'merge_same_time'\|'prune_empty_slots'\|'accept_suggestion'\|'dismiss_suggestion', …}]}` 또는 `{undo:true}`·`{redo:true}` | 200 timeline (자동 저장) |
| `POST /v1/scenarios/{id}/timeline:nl-edit` | `{text}` | 202 |
| `PATCH /v1/scenarios/{id}/roles/{rid}` | `{name?, intro?, wants?, pains?}` | 200 + 202 `{job_id}`(레인 문장 재작성) |
| `GET /v1/scenarios/{id}/timeline:text` | — | `{raw_text}` (텍스트로 보기) |

### 6.3 솔루션·제품·추천
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `PUT /v1/scenarios/{id}/solutions` | `{items:[{solution_id}]}` | 200 + `related_products:[…]` |
| `PUT /v1/scenarios/{id}/products` | `{items:[{family_id, qty?}]}` | 200 |
| `GET /v1/solution-search` · `GET /v1/product-search` | `q` | kb 결과를 칩 표시용으로 |
| `POST /v1/scenarios/{id}:route-generate` | — | `{next:'SC3R'\|'SC4G'}` (R4) |
| `POST /v1/scenarios/{id}/recommendations:compute` | — | 202 → `GET /v1/scenarios/{id}/recommendations` |
| `PATCH /v1/scenarios/{id}/recommendations/{scene_id}` | `{applied}` · `POST …/recommendations:apply-all` | 200 |
| `POST /v1/scenarios/{id}/recommendations:commit` | `{mode:'apply'\|'products_only'}` | 200 (유형·솔루션 반영) |

### 6.4 생성·장면
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `POST /v1/scenarios/{id}/generate` | `{scope:'all'\|'unlocked', scene_ids?}` | 202 `{job_id}` · 409 `GENERATION_IN_PROGRESS` |
| `POST /v1/scenarios/{id}/generate:resume` | `{job_id}` | 202 (실패 thread 재개) |
| 취소·메모 | jobs API(`POST /api/jobs/v1/jobs/{id}:cancel`, 메모) | |
| `GET /v1/scenarios/{id}/scenes` · `GET /v1/scenes/{sid}` | — | 장면(버전·stale 포함) |
| `PATCH /v1/scenes/{sid}` | `{title?, story?, characters?, solutions?, products?, if_version}` | 200 (`locked=true`, 새 버전) |
| `POST /v1/scenes/{sid}:rewrite` | `{preset?:'shorter'\|'pov'\|'solution_detail', pov_role_id?, instruction?}` | 202 |
| `POST /v1/scenes/{sid}/versions/{n}/restore` · `DELETE /v1/scenes/{sid}` · `POST /v1/scenarios/{id}/scenes` | | |
| `POST /v1/scenarios/{id}:edit` | `{text}` (수정 요청) | 202 |
| `POST /v1/scenarios/{id}:shorten` | — | 202 |

### 6.5 장면 이미지
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `POST /v1/scenes/{sid}/image-request` | — | 201 `{request_id, image_route}` (image `POST /v1/requests` + `:start` 대리) |
| `POST /v1/scenes/{sid}/image:attach` | `{image_version_id}` | 200 (고르기 모드·요청 충족 결과) |
| `POST /v1/scenarios/{id}/images:generate-missing` | — | 202 (일괄 렌더) |
| `GET /v1/scenes/{sid}/image-prefill` | — | `{space, scene, products, aspect:'16:9', kind:'scenario'}` |

### 6.6 보내기·내보내기
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `GET /v1/scenarios/{id}/sheet-plan` | — | `{sheets:[…], carry:{scenes, solutions, products, images, confirm}, images_missing}` |
| `GET /v1/scenarios/{id}/handoff` | `version?` | 제안서용 묶음(§8) |
| `POST /v1/scenarios/{id}/exports` | `{kind:'pptx'\|'pdf'\|'docx'\|'zip'}` | 202 `{job_id, export_id}` |
| `POST /v1/scenarios/{id}/usages` · `DELETE …` | `{service, ref, label, version}` | 201 / 204 |

SSE `data`: `step {stage:'split'|'write'|'link'|'confirm', note, done, total}`, `log {scene_id, partial_story}`(스트리밍), `progress {pct, eta_s}`, `result {scene_ids}`, `error`.

---

## 7. 워크플로 (LangGraph · 워커 `wm:q:scenario`)

### 7.1 공통
- 체크포인터 SQLite, `thread_id=job_id`. 노드 경계 취소 확인. 조종 메모는 `write_scene` 노드 시작마다 읽는다.
- 고객 정보가 들어간 LLM 호출은 `confidential:true`. 차단되면 **익명화 대체**: 고객사명·지점명 → 「고객사」, 사람 이름 → 역할명으로 바꿔 `confidential:false` 로 보내고, 결과에서 로컬로 되돌린다(`anonymized=true` 기록).
- 문장 규칙(프롬프트·후처리 공통): 고른 솔루션·제품만 등장, 솔루션 동작은 동작 사전(§10.5) 어휘에서, 수치는 근거(입력 인용·KB 메시지/사례 KPI)가 있을 때만 — 없으면 「[00]」, 실존 인물 이름 금지(역할명), 경쟁사명 금지(「기존 시스템」·「타사 제품」), 최상급·인증 주장 금지.

### 7.2 모델 능력별 경로(네이티브 vs 대체)
| 기능 | 네이티브 | 대체 |
|---|---|---|
| 텍스트 → 타임라인 | 시간 정규식(`^\s*(\d{1,2}):(\d{2})`)으로 줄 나눔 + LLM JSON(시간대·라벨·역할·비트·장소) | LLM 실패: 정규식 줄 = 시간대, 문장 주어 = 역할(등장인물 칩과 일치), 비트 = 줄 전체 |
| 등장인물 추출 | LLM JSON | 등장인물 사전(점장·손님·직원·담당자 등) 일치 |
| 골격(템플릿·조감도) | LLM 비트 초안 | 템플릿 문장 「{역할}이 {장소}에서 {단계}」 |
| 솔루션 추천 | LLM(닫힌 동작 사전) + KB 근거 | 키워드 규칙(동작 사전 `keywords`) |
| 연관 제품 | KB `D5`·`C2`·`A1` (결정적) | — |
| 장면 쓰기 | LLM(스트리밍 지원 시 부분 문장 SSE) | 스트리밍 미지원: 장면이 끝날 때마다 통째로 표시, 작성 중 카드는 비트 문장 + 입력 중 표시 / LLM 없음: job 실패(다시 시도) |
| 수치 표시 | 결정적 후처리(숫자 토큰 ↔ 근거 대조) | — |
| 장면 이미지 | image 렌더 API(07 §6.9, 그쪽 대체 경로 사용) | — |

### 7.3 그래프 `sc.parse_input`
`regex_split → llm.json({slots[{time?, label}], roles[{name}], beats[{slot, role, text, place}], personas[…]}) → validate(시각 HH:MM 정렬, 역할 이름 정규화, 실존 인물 → 역할) → build_timeline(시간대마다 장면 1, 첫 비트 primary) → route(장면 ≤ 6 · 충돌 없음 → SC3 else SC2E) → save → END`.

### 7.4 그래프 `sc.skeleton` (템플릿·조감도)
- 템플릿: `load_preset(시드) → slots(흐름 단계) → roles(r) → llm.json(시간대×역할 비트 초안, 업종 요구 반영; '하루'면 대표 시각) → prefill(used → A1 → 솔루션/추천) → save`.
- 조감도: `fetch_handoff(birdseye) → zones(선택·순서) → axis → slots(방문객 동선 = 존 순서 단계 / 하루·당일 = LLM 시각) → scenes(장면 k = 존 k: 장소 = 존 이름, 제품 = 존 제품, zone_ref) → roles(축 기본 역할 + LLM) → beats(llm) → register_usage(birdseye) → save`.

### 7.5 그래프 `sc.recommend`
`entities(A1 on 장면 문장) → match(llm.json: 장면별 {product_only_text, action_code(동작 사전), tag, benefit, evidence_quote}) → evidence(입력 인용 검증: 인용이 원문 부분 문자열이어야 함; 사례 수 = KB D1(vertical, targets=[('solution', id)]) 결과 수, 업종 대응 없으면 「[00]」) → related_products(D5 ∩ C2 ∪ A1 언급) → save`. 태그 규칙: 다수 사업장 일괄·원격 동작(“전국 N개 매장에 배포”) → 꼭 필요, 시간·상태에 따른 자동화(“켜져 있어야”, “집계된다”) → 추천, 제품 화면만으로 성립 → 선택.

### 7.6 그래프 `sc.generate` (SC4G)
```text
load → split_scenes("장면 나누기": 장면 목록 확정, 잠긴 장면은 건너뜀 표시)
     → for 장면 in 순서: apply_memos → write_scene("장면별 이야기 쓰기": llm(스트리밍) → 제목·이야기·비트 정리) → emit preview
     → link("솔루션 동작 · 제품 연결": 장면별 솔루션 동작·제품 칩 확정, 동작 사전 밖 표현 정규화)
     → mark_confirm("확인 필요 표시": 숫자 토큰마다 근거 대조 → 없으면 '[00]'로 바꾸고 confirm_tokens 기록)
     → finalize(status done, 버전, 알림, 작업 색인) → END
```
- `write_scene` 입력: 장면 비트·장소·시간대, 페르소나(원하는 것·불편한 점), 고른 솔루션·제품, 동작 사전 설명, KB 근거(업종 B1 장면 문구·E1 솔루션 메시지·D1 유사 사례 요약), 업종 요구(needs), 메모.
- 진행률: 나누기 10 · 장면 쓰기 70(장면 수로 등분) · 연결 10 · 확인 10.
- 중지: 끝난 장면은 `done` 으로 남고 나머지는 `waiting`; 시나리오 `status=draft, step=3`.
- 실패: `failed` + 체크포인트 유지 → `generate:resume` 이 같은 thread 로 재개.

### 7.7 다시 쓰기·수정 요청·줄이기
- `sc.rewrite_scene`: 한 장면만(이 장면만 다시 쓰기), 다른 장면은 읽기 전용 맥락. 결과 = 새 버전, 이유 문구(「방금 수정 요청 반영」 등).
- `sc.edit`(SC4 수정 요청): `llm.json → ops([{op:'add_beat', scene, role, text}, {op:'add_product', scene, family}, {op:'add_scene', after, …}, {op:'rewrite', scene, instruction}])` → 적용 → 영향 장면만 `rewrite_scene` 순차. 새 제품·인물은 「새로」 표시.
- `sc.shorten`: 모든 장면 이야기를 ≤ 70자로(새 버전).

### 7.8 장면 이미지
- 하나(SC4 「이미지 생성」, SC4E 「이미지 생성에서 다시 만들기」): `image POST /v1/requests {from_service:'scenario', from_ref:scene_id, from_label:'공간 시나리오 · {제목}', title:'장면 {n} · {라벨} {요약}', prefill:{kind:'scenario', description, products, aspect:'16:9', space_label}}` → `:start` → 웹이 IMG2 로 이동. SC4·SC4E 를 열 때 `GET /api/image/v1/requests?from_service=scenario&from_ref=` 로 충족 여부를 확인해 붙인다(`image:attach`).
- 일괄(「장면별 이미지 모두 생성」): 이미지 없는 장면마다 `image POST /v1/renders {origin:{service:'scenario', ref:scene_id}, kind:'scene', prompt:{subject_ko:장면 요약, details_ko:[장소, 비트, 제품 활용]}, product_refs, aspect:'16:9', target:'fhd', allow_people:'generic', forbid:[…]}` 순차(동시 1) → 완료마다 붙임. 실패 장면은 카드에 **(신규)** 「이미지를 만들지 못했어요 · 다시」.
- 붙일 때 조건 스냅샷(제품·인물·솔루션)을 저장 → stale 판정(§4.11).

### 7.9 시트 구성 `sheet_plan` (결정적)
1. 장면을 `space_key` 로 묶는다(LLM 이 장소를 시나리오 공간 목록에 정규화, 결과는 저장해 재사용).
2. 공간 ≥ 2 이면 맵 시트 1장: 조감도 연결 + 존 위치가 있으면 `VM-C`(조감도 위 솔루션 핀), WITH 이면 `VM-A`(공간 × 솔루션 매트릭스), WITHOUT 이고 시각 있는 시간대면 `VM-D`(하루 타임라인 × 공간), 그 밖은 `VM-B`(공간 3개 한 장, 공간 ≤ 3 일 때만 — 4개 이상이면 맵 시트 생략).
3. 공간마다: 장면 ≥ 2 → `SS-A`(한 공간의 장면 3, 3장면씩 나눠 여러 장), 장면 1 & 솔루션 있음 → `SS-B`(솔루션 → 제품 → 가치), 장면 1 & 전후 이미지(조감도 도입 전·후) 있음 → `SS-C`, 그 밖 장면 1 → `SS-A`.
4. 시트 번호는 맵 → 공간(첫 장면 시각 순). 시트별 `images {have, total}`, `confirm_count`(그 시트 장면의 `[00]` 수).
보드 예(장면 4, 공간 2, 솔루션 2) → `VM-A` + `SS-A`(매장 카운터: 장면 1·2·4) + `SS-B`(본사 운영실: 장면 3) = 3장.

### 7.10 내보내기 `sc.export`
- PPTX: export 서비스 템플릿 카탈로그의 VM-*/SS-* 템플릿에 시트 계획을 채움(이미지 없는 칸 = 이미지 자리, `[00]`·「[확정 필요]」 그대로).
- PDF: 같은 시트를 PDF 로.
- 장면 스크립트 DOCX: 장면마다 시각·제목·이야기·역할별 비트·솔루션 동작·제품·근거(인용·출처 URL)·확정 필요 목록, 끝에 페르소나 표.
- 장면 이미지 ZIP: `장면{n}_{라벨}.png` + `sources.json`(이미지 생성 메타).
- 시나리오 변경 감지 예약: jobs `wm:sched` 로 6시간마다 연결 유지 조감도 버전 확인(선택), SC0 조회 때도 확인.

---

## 8. 다른 서비스 의존

| 서비스 | 쓰는 것 |
|---|---|
| ai-tools | `llm.json`(파싱·페르소나·추천·문장), `llm.stream`(있으면 장면 스트리밍), capabilities |
| kb | `A1`(문장 → 제품·솔루션·공간), `A2`(업종 판별, 프로젝트 업종 없을 때), `B1`/`S2`(업종 장면·공간 시퀀스 근거), `C1`/`C2`(공간 → 역량 → 제품), `D1`/`D2`(유사 사례·사례 수), `D5`(솔루션 공존 제품), `E1`/`E3`(솔루션·제품 메시지 근거, claim 표시) — 경로는 `contracts/kb.json` |
| image | 요청(07 §6.8)·렌더 API(§6.9)·요청 결과 조회·사용 등록 |
| birdseye | `GET /birdseyes`(목록), `GET /birdseyes/{id}/handoff`(존·배치 제품·평면 미리보기), `GET /birdseyes/{id}/version`(변경 감지), `POST /birdseyes`(조감도 추가 「새로 만들기」), `POST /birdseyes/{id}/usages` |
| files | 내보내기 결과, 평면 미리보기 파일 읽기 |
| jobs | job·SSE·취소·메모·완료 알림·예약 확인 |
| workspace | 작업 색인, 프로젝트 고객·업종, 사이드바 항목 요약(Storyboard 끌어오기), 「팀에 공유」 |
| export | PPTX(VM·SS 템플릿)·PDF·DOCX·ZIP |
| proposal(웹에서만) | 웹이 제안서 계약으로: 진행 중 제안서 목록, `POST /proposals/{id}/imports {source:{service:'scenario', id, version}, section:'space_scenario', sheet_plan}`, 「시트 구성 바꾸기」 이동. 제안서가 `GET /v1/scenarios/{id}/handoff` 를 읽고 `usages` 등록 |

**handoff 묶음**: `{scenario_id, version, title, customer, type, solutions:[{id, name}], products:[{family_id, label}], roles:[{name, intro, wants, pains}], slots:[…], scenes:[{no, time, label, title, story, beats, place, space_key, solutions:[{id, action, label}], products, image:{version_id, renditions, generation}?, confirm_tokens, evidence}], sheet_plan, birdseye_link?, confirm_items:[{scene_no, token, near_text}]}`.

---

## 9. 수용 기준
LLM·i2t·KB·image·birdseye 는 결정적 목(mock)·픽스처로 대체, 시계 고정.

**SC0**
1. Given 시나리오 5건(보드 예 데이터), When SC0, Then 필터 개수 「전체」 5 「작성 중」 2 「생성 중」 1 「완료」 2, 행 상태가 「완료」+「제안서에 사용 중」, 「작성 중」+「3 / 4 · 솔루션 · 제품 입력」, 「생성 중」+「장면 2 / 4 작성 중」, 「작성 중」+「조감도가 바뀌었어요」, 「완료」+「제안서에 아직 안 넣음」, 꼬리 「5개 중 1–5」.
2. Then 보내기 아이콘(aria 「제안서로 보내기」)은 완료 행에만 있다.
3. Given 연결 유지한 조감도의 `version` 목이 연결 시점보다 큼(9월 30일), When SC0, Then 알림 「C 물류센터 관제실」 「조감도가 9월 30일에 바뀌었어요.」 「연결된 시나리오 1개의 공간 · 제품을 다시 맞출까요?」가 보이고 「변경 반영하기」는 SC1B 변경 반영 모드로 간다. 닫으면 같은 변경으로는 다시 보이지 않는다. `keep_link=false` 면 알림이 없다.
4. Then 시작 방식 칸이 「직접 입력」 / 「업종 템플릿 · 의료」 / 「조감도 · 강남 플래그십 1층 로비」 형식이다.

**SC1**
5. Given 새 시나리오, Then 「WITH 솔루션」 선택, 「조감도 추가」 토글이 꺼져 있고 태그 「선택 · 기본 꺼짐」, 선택지(새로 만들기/기존 조감도 연결)가 보이지 않는다.
6. When 토글을 켜면, Then 태그 「켜짐」, 「새로 만들기」가 선택된 상태로 두 선택지가 보이고 「기존 조감도 연결」 부제가 「조감도 작업 {내 조감도 수}개에서 고르기」다.
7. Given 조감도 추가 켜짐·새로 만들기, When SC3 에서 「시나리오 생성」, Then birdseye `POST /birdseyes` 가 `origin.service='scenario'`·시나리오 제품으로 1번 호출되고 `aerial.birdseye_id` 가 저장된다. 꺼져 있으면 호출이 없다.

**SC1T**
8. When SC1T, Then 타일이 16개(시드 순서)이고 기본 선택 「외식 · 카페 프랜차이즈」, 프리셋 1 「매장 하루」(배지 「장면 4」, 흐름 「오픈 → 점심 피크 → 본사 배포 → 마감」, 역할 「점장 · 손님 · 본사 담당자」), 대표 공간 5칩, 요구 4칩, 줄 「시스템에어컨 · LCD 사이니지 · 갤럭시 탭 · 파트너 앱 · 주문 결제 · MagicINFO」.
9. When 검색 「병실」, Then 「의료 · 요양 · 케어」 타일만 남는다.
10. When 「이 골격으로 시작」(FB, 프리셋 1, WITH), Then SC2E 가 열리고 시간대 4(오픈·점심 피크·본사 배포·마감), 역할 3(점장·손님·본사 담당자), 장면 4, SC3 솔루션 칩에 「MagicINFO」가 미리 들어가 있다. WITHOUT 이면 솔루션 칩이 없다.

**SC1B**
11. Given 조감도(존 5: 제품 3 · 가구만 1 · 빈 1), When SC1B, Then 「가져올 존」 「· 4 / 5 선택」, 5번 행이 「배치 제품 없음 · 랩핑 포인트만 지정」 「제외」, 머리 「· 존 4개 → 장면 4개 · 2 / 4」, 「조감도와 연결 유지」 켜짐, 시나리오 축 첫째 선택.
12. When 「존으로 장면 만들기」(축 「방문객 동선」), Then 장면 4개가 동선 순서대로 생기고 장면 k 의 장소·제품이 존 k 의 것이며 시간대에 시각이 없다. birdseye `usages` 등록이 1번 호출된다.
13. When 동선 순서 칩 2와 3을 바꾸고 만들면, Then 장면 2·3 의 장소가 바뀐 순서를 따른다.
14. Given 변경 반영 모드에서 존 1의 제품이 바뀐 diff 목, When 「바뀐 곳 반영하기」, Then 장면 1 의 제품만 갱신되고 이야기는 그대로이며 이미지가 `stale` 이다.

**SC2 · 라우팅**
15. When 「예시 골격」 「신메뉴 출시일」을 누르면, Then 골격 문장이 입력칸 끝에 붙고 기존 문장은 지워지지 않는다.
16. Given 보드 예 4줄 입력, When 1초 멈춤, Then 등장인물 칩이 「점장」 「손님」 「본사 마케팅 담당자」다. 사용자가 지운 칩은 다시 생기지 않는다.
17. Given 보드 예 4줄, When 「솔루션 · 제품 입력」, Then 파싱 결과 장면 4·충돌 없음 → SC3 로 간다. Given 시각이 있는 8줄(장면 8), Then SC2E 로 가고 W 에 「장면이 8개로 많아요. 같은 시간 장면을 합쳐 보세요.」.
18. Given LLM 파싱 실패 목, Then 정규식 경로로 시간대 4·비트 4 의 타임라인이 만들어진다.
19. Given 입력에 「배우 ○○○가 방문」, Then 타임라인 비트에 그 이름이 없고 역할명이 쓰이며 「실제 인물 이름은 역할로 바꿔 썼어요」 안내가 보인다.

**SC2E**
20. Given 파싱 결과(시간대 5 · 역할 3 · 장면 5), Then 머리 「· 시간대 5 · 역할 3 · 장면 5」, 레인 머리글자 「점」 「손」 「본」, 18:00 열에 「새 시간대」 배지.
21. When 점장 레인 비트 「태블릿으로 재고 확인」을 11:30 칸으로 옮기면, Then 그 비트가 장면 2 에 들어가고(「장면 2 · 점장 시점」) 장면 번호가 다시 매겨지며 「변경 {n}건 · 자동 저장됨」의 n 이 1 늘어난다. 되돌리기로 원래 상태가 된다.
22. When 「같은 시간 장면 합치기」, Then 시간대마다 장면이 하나다. 「빈 시간대 정리」, Then 비트 없는 시간대가 사라진다. 「장면 나누기」, Then 선택 장면이 같은 시간대의 두 장면이 된다.
23. When W 추천 장면 「추가」, Then 손님 레인 18:00 에 비트 「퇴근길 모바일 주문 픽업」이 생긴다. 「닫기」면 추천이 사라지고 같은 추천이 다시 나오지 않는다.
24. When 「+ 바리스타」, Then 레인이 하나 늘고 페르소나 목록이 「· 4명」.
25. When 점장의 「불편한 점」에 칩을 추가하고 저장, Then 레인 문장 재작성 job 이 1번 생기고 끝나면 점장 레인 비트만 바뀐다.
26. When 「편집 요청」 「손님 레인 18:00에 퇴근길 픽업 장면 추가」(LLM 목 ops), Then 해당 비트가 추가된다.
27. When 「텍스트로 보기」, Then SC2 입력칸에 「07:00 …」 형식 줄 텍스트가 채워진다.

**SC3 · SC3R**
28. When 솔루션 「MagicINFO」 선택(D5·C2·A1 픽스처), Then 제품 머리에 「· MagicINFO 연관 제품 추천됨」, 추천 칩 「추천: Outdoor OH55C」 「추천: Galaxy Tab Active5」가 생기고 누르면 제품 칩으로 바뀐다.
29. Given WITHOUT, 제품 QM55C ×3·KM24C, 추천 목(장면 3 꼭 필요, 1·4 추천, 2 선택), When 「시나리오 생성」, Then SC3R 로 가고 머리 「· 적용 3 · 제품만 1」, 장면 2 토글 꺼짐(「+ MagicINFO · 시간대 레이아웃」 「선택」 「제품만으로 충분해요」), 장면 3 태그 「꼭 필요」.
30. Then 장면 1 근거가 「입력」 「‘메뉴보드가 아침 메뉴로 켜져 있어야 한다’」이고 이 인용은 입력 원문의 부분 문자열이다(아니면 근거에서 뺀다). 장면 3 사례 수를 KB 가 셀 수 없으면 「· 카페 사례 [00]건」.
31. When 「추천 적용 · 시나리오 생성」, Then 유형이 with, 솔루션 칸에 MagicINFO · SmartThings Pro, 장면 2 는 제품만, SC4G 로 간다. 「제품만으로 생성」이면 유형 WITHOUT·솔루션 없음으로 SC4G.
32. Given WITH 이고 솔루션 0개, When 「시나리오 생성」, Then SC3R 로 간다(「솔루션을 못 고르면 → SC3R 추천」).

**SC4G**
33. When 생성, Then 단계 이벤트가 「장면 나누기」 → 「장면별 이야기 쓰기」(장면마다 「장면 {k} · {라벨} 작성 중 ({done} / 4 완료)」) → 「솔루션 동작 · 제품 연결」 → 「확인 필요 표시」 순이고 미리보기에 끝난 장면이 「완성」, 쓰는 장면이 「작성 중」, 나머지가 「대기」로 보인다.
34. Given `llm.stream` 지원 목, Then 작성 중 카드에 부분 문장이 `log` 이벤트로 갱신된다. 미지원이면 작성 중 카드는 비트 문장과 입력 중 표시만 보인다.
35. Given 장면 2 작성 중 메모 「장면 3은 본사 담당자 시점으로」, Then 장면 3 프롬프트에 메모가 들어가고 장면 1·2 는 다시 쓰지 않는다.
36. When 「중지 · 입력 고치기」, Then job 취소, 끝난 장면은 `done` 으로 남고 SC3 로 간다.
37. Given 장면 3 작성 중 LLM 오류(재시도 소진), Then 「시나리오를 쓰다가 멈췄어요」와 「다시 시도」, 「다시 시도」는 같은 thread 로 재개되어 장면 1·2 의 LLM 호출이 다시 일어나지 않는다.
38. Given LLM 목이 장면 3 에 「10분 만에」(근거 없음)와 「320개 매장」(입력 근거)을 씀, Then 결과 이야기에서 「10분」은 「[00]」 이 되고 「320개」는 남으며 `confirm_tokens` 가 1개다.
39. Given 고객 정보가 든 호출에 `POLICY_CONFIDENTIAL`, Then 고객사명이 「고객사」로 바뀐 요청이 `confidential:false` 로 다시 가고, 결과에는 원래 고객사명이 복원되며 `anonymized=true` 다.

**SC4 · SC4E**
40. Then 장면 카드에 제목 「{라벨} — …」, 이야기, 솔루션 칩(파랑)·제품 칩(회색), 이미지가 있는 장면은 썸네일·없는 장면은 「이미지 생성」 버튼이 있다.
41. When 장면 1 「이미지 생성」, Then image `POST /v1/requests`(prefill: kind 'scenario', aspect '16:9', 제품 「QM55C」, 공간) + `:start` 가 호출되고 IMG2 로 이동한다. image 목이 요청을 `fulfilled`(버전 v) 로 바꾼 뒤 SC4 를 열면 장면 1 에 v 가 붙는다.
42. When 「장면별 이미지 모두 생성」(이미지 없는 장면 3개), Then image `POST /v1/renders` 가 장면마다 1번씩 순차 호출되고(동시 1), 끝날 때마다 해당 카드에 썸네일이 붙는다.
43. When 수정 요청 「장면 2에 점장이 태블릿으로 재고 확인하는 장면 추가」(LLM 목: add_beat 점장 + add_product Tab Active5), Then 장면 2 만 다시 쓰여 v2(「· 방금 수정 요청 반영」)가 되고 SC4E 에서 「점장」·「Galaxy Tab Active5」·「MagicINFO · 즉시 변경」 칩에 「새로」, 「바뀐 곳 1」이 보인다.
44. Given 장면 2 이미지 스냅샷 제품 {KM24C, QM55C}, 현재 제품에 Galaxy Tab Active5 추가, Then 경고 「이야기가 바뀌어 이미지와 다를 수 있어요 (태블릿 장면 없음)」와 「이미지 생성으로 넘어가는 것」 표의 제품 「KM24C · QM55C · Tab Active5」, 비율 「16:9 · 제안서 시트용」.
45. When 「v1로 되돌리기」, Then 장면이 v1 내용의 새 버전(v3)이 되고 v2 는 남는다.
46. When 장면 2 제목을 직접 고치고 「변경 저장」, Then `locked=true`, 장면 목록 링크 아래 「직접 고친 장면 2는 그대로 둡니다」. 「나머지 장면 다시 생성」 job 은 장면 2 를 호출하지 않는다.
47. When 「점장 시점으로」 칩, Then `rewrite` 가 `pov_role_id=점장` 으로 호출되고 다른 장면은 바뀌지 않는다.
48. When 장면 3 삭제, Then 장면 4 가 장면 3 으로 번호가 바뀌고 시트 계획이 다시 계산된다.

**SC5 · 내보내기 · 제안서**
49. Given 장면 4(장소: 1·2·4 = 매장 카운터, 3 = 본사 운영실), 솔루션 2, 제품 2, 이미지 1(장면 2), `[00]` 1(장면 3), Then 시트 계획이 VM-A · SS-A(장면 1·2·4, 「이미지 1 / 3」) · SS-B(장면 3, 「확정 필요 1」) 3장, W 「… 장면 4개를 공간 기준으로 묶어 시트 3장으로 나눴어요. …」, 「함께 넘어가는 것」 「장면 텍스트 4 · 솔루션 2 · 제품 2 · 이미지 1 · 확정 필요 1」, 「이미지가 없는 장면 3개는 시트에 이미지 자리만 남겨요.」, 주 버튼 「제안서에 넣기 · 시트 3장」, 파일 버튼 「PPTX · 시트 3장」.
50. Given WITHOUT, 공간 2, 시각 있는 시간대, Then 맵 시트가 VM-D 다. 공간 1 이면 맵 시트가 없다. 조감도 연결과 존 위치가 있으면 VM-C 다.
51. When 「제안서에 넣기 · 시트 3장」, Then 웹이 제안서 `imports` 에 `{source:{service:'scenario', id, version}, section:'space_scenario', sheet_plan}` 를 보내고, 제안서 목이 `handoff` 를 읽은 뒤 `usages` 를 등록하면 SC0 상태가 「제안서에 사용 중」이다.
52. When 「장면 스크립트 DOCX」, Then export job 이 생기고 문서에 장면 4개(시각·제목·이야기·역할별 비트·솔루션 동작·제품·근거·확정 필요)와 페르소나 표가 있다. 「장면 이미지 ZIP」은 이미지 0장이면 비활성.
53. Given 시나리오 생성·완료·보내기, Then workspace `PUT items/{id}` 가 `feature='scenario'`, 올바른 `route` 로 호출된다.
54. Then 어떤 생성 결과에도 경쟁사 사전(`config/content_policy.yaml`) 의 이름이 없다(LLM 목이 넣으면 「기존 시스템」으로 치환).

---

## 10. 규칙 · 임계값

### 10.1 보드의 수치(그대로)
- 단계 4, 유형 2(WITH 솔루션 · WITHOUT 솔루션), 조감도 추가 기본 꺼짐, 업종 16, 업종별 프리셋 3 · 프리셋당 「장면 4」, 예시 골격 3, SC1B 시나리오 축 3.
- 보드 예: 「07:00」 「11:30」 「14:00」 「18:00」 「21:00」, 「320개 매장」, 「시간대 5 · 역할 3 · 장면 5」, 「변경 3건」, 「적용 3 · 제품만 1」, 「50% · 약 20초 남음」, 「2 / 4」, 「존 4개 → 장면 4개」, 「4 / 5 선택」, 「시트 3장」, 「장면 텍스트 4 · 솔루션 2 · 제품 2 · 이미지 1 · 확정 필요 1」, 「이미지 1 / 3」, 「공간 2 × 솔루션 2」, 「16:9 · 제안서 시트용」, 「5개 중 1–5」.
- 확인 표시: 근거 없는 수치 「[00]」, 시트 가치 수치 「[확정 필요]」.
- 시트 코드: VM-A(공간 × 솔루션 매트릭스) · VM-B(공간 3개 한 장) · VM-C(조감도 위 솔루션 핀) · VM-D(하루 타임라인 × 공간) · SS-A(한 공간의 장면 3) · SS-B(솔루션 → 제품 → 가치) · SS-C(이 공간 전 → 후).

### 10.2 시스템 기본값(제안)
| 키 | 기본 | 뜻 |
|---|---|---|
| `SC_MAX_SCENES_AUTO` | 6 | 넘으면 SC2E 로 보내고 합치기 권유 |
| `SC_MAX_SCENES` | 12 | 장면 상한 |
| 이야기 / 줄이기 / 비트 / 장소 | ≤ 120 / ≤ 70 / ≤ 40 / ≤ 16자 | 문장 길이 |
| SS-A 장면 수 | 3/시트 | 넘으면 시트 추가 |
| 등장인물 추출 | 입력 멈춘 뒤 1초, 제한 5초 | SC2 |
| 되돌리기 | 50단계 | 타임라인 연산 로그 |
| 추천 제품 | 최대 3 | SC3 |
| 장면 이미지 일괄 | 장면당 1장, 동시 1, 16:9, fhd | SC4 |
| 조감도 변경 확인 | SC0 조회 시(60초 캐시) + 6시간 예약 | R10 |
| 입력 길이 | 시나리오 텍스트 ≤ 3,000자, 최소 10자 | SC2 |

### 10.3 업종 → KB 대응(`verticals.yaml` winmate_segments, draft)
FB → `kr_fnb` · RT → `kr_retail` · SV → (FILL) · HT → `kr_hotel` · TP → (FILL) · VN → (FILL) · AD → (FILL) · OF → `kr_office`,`kr_small_office` · RS → `kr_home`,`kr_officetel` · ID → (FILL) · ED → `kr_school`,`kr_academy` · PB → `kr_public_agency`,`kr_military` · MD → `kr_hospital`,`kr_clinic` · MF → `kr_manufacturing`,`kr_transport` · FN → `kr_finance` · OE → (FILL). 대응이 없는 업종은 KB 업종 질의(B1·D1·D2)를 건너뛰고 사례 수는 「[00]」.

### 10.4 업종 템플릿 시드(`seed/industry_templates.yaml` — SC1T 데이터 그대로, `short` 는 목록 표기용 추가)
| code | 이름 / short | 대표 공간 | 장면 프리셋(제목: 흐름 / 역할) | 장면에 담을 요구 | 자주 쓰인 것 |
|---|---|---|---|---|---|
| FB | 외식 · 카페 프랜차이즈 / 외식 · 카페 | 주문 카운터 · 홀 테이블 · 주방 · 드라이브스루 · 테라스 | 매장 하루: 오픈 → 점심 피크 → 본사 배포 → 마감 / 점장 · 손님 · 본사 담당자 · 신메뉴 출시일: 전날 예약 → 오픈 교체 → 피크 주문 → 반응 집계 / 본사 마케팅 · 점장 · 손님 · 드라이브스루 피크: 진입 → 메뉴 확인 → 주문 결제 → 픽업 / 운전자 손님 · 크루 | 디자인 조화 · 고객 경험 · 쾌적 · 공기질 · 업무 효율 | 시스템에어컨 · LCD 사이니지 · 갤럭시 탭 · 파트너 앱 · 주문 결제 · MagicINFO |
| RT | 리테일 · 브랜드 플래그십 / 리테일 | 쇼윈도 · 매장 벽면 · 체험존 · VIP 라운지 · 건물 외벽 | 방문객 동선: 거리에서 발견 → 입장 → 체험존 → 상담 · 구매 / 방문객 · 매장 스태프 · 신제품 런칭: 티저 송출 → 런칭 당일 → 체험 이벤트 → 재방문 / 방문객 · 본사 VMD · 스태프 · 매장 하루: 오픈 → 피크 → VMD 교체 → 마감 / 매장 스태프 · 본사 VMD | 브랜드 · 공간 임팩트 · 디자인 조화 · 고객 경험 · 설치 · 시공 | LCD 사이니지 · LED 사이니지 · 시스템에어컨 · MagicINFO · 케어 · 유지관리 서비스 |
| SV | 생활 편의 · 무인 매장 / 생활 편의 | 무인 출력 코너 · 셀프 세탁 존 · PC 좌석 · 스터디 룸 | 무인 24시간: 심야 이용 → 셀프 결제 → 원격 점검 → 아침 보충 / 손님 · 점주 · 원격 관리자 · 첫 방문 손님: 입장 → 기기 사용 → 결제 → 문의 대응 / 손님 · 점주 · 기기 장애 대응: 오류 발생 → 원격 알림 → 조치 → 정상화 / 점주 · 원격 관리자 · 손님 | 고객 경험 · 업무 효율 · 확장성 · 유지보수 · AS | TV · 모니터 · 디지털 복합기 · PC · 노트북 · 무인 과금 · 파트너 앱 · 주문 결제 |
| HT | 호텔 · 리조트 / 호텔 · 리조트 | 로비 프런트 · 객실 · 연회장 · 레스토랑 주방 · 코인 세탁실 | 투숙객 여정: 체크인 → 객실 입실 → 부대시설 → 체크아웃 / 투숙객 · 프런트 · 객실팀 · 연회 · 행사: 셋업 → 행사 진행 → 식사 → 철수 / 주최 측 · 연회팀 · 참석자 · 객실 운영 하루: 객실 점검 → 입실 준비 → 야간 → 에너지 정리 / 객실팀 · 시설팀 | 고객 경험 · 디자인 조화 · 브랜드 · 공간 임팩트 · 쾌적 · 공기질 | 호텔 TV · 시스템에어컨 · TV · 모니터 · 케어 · 유지관리 서비스 · LYNK Cloud |
| TP | 테마파크 · 관광 · 전시 / 테마파크 | 입장 대기 공간 · 전시 공간 · 어트랙션 · 야외 무대 | 관람객 하루: 입장 대기 → 어트랙션 → 공연 → 퇴장 / 관람객 · 운영팀 · 시즌 이벤트: 사전 홍보 → 개막 → 야간 공연 → 종료 / 관람객 · 콘텐츠 담당 · 운영팀 · 외국인 관광객: 입구 안내 → 다국어 전시 → 기념품 → 귀가 / 외국인 관광객 · 안내 직원 | 브랜드 · 공간 임팩트 · 고객 경험 · 디자인 조화 · 설치 · 시공 | LCD 사이니지 · LED 사이니지 · TV · 모니터 · MagicINFO · 전용 에디션 · 커스터마이징 |
| VN | 공연장 · 경기장 · 영화관 / 공연장 · 경기장 | 입구 · 상영관 객석 · 클럽하우스 라운지 · 라커룸 · 중계실 | 경기일 하루: 입장 → 경기 → 하프타임 → 퇴장 / 관중 · 운영팀 · 선수단 · 관객 여정: 예매 → 입장 → 상영 · 공연 → 식음 · 굿즈 / 관객 · 매점 직원 · 선수 · 운영 동선: 준비 → 라커룸 → 중계 → 정리 / 선수단 · 중계팀 | 고객 경험 · 브랜드 · 공간 임팩트 · 설치 · 시공 · 업무 효율 | 하만 프로 오디오 · LED 사이니지 · 시스템에어컨 · 케어 · 유지관리 서비스 · VXT |
| AD | 옥외 · 미디어 광고 / 옥외 광고 | 건물 외벽 · 미디어폴 · 환승통로 · 공항 출입구 | 매체 하루 송출: 출근 시간 → 낮 → 퇴근 피크 → 야간 / 시민 · 매체사 · 캠페인 집행: 계약 → 콘텐츠 등록 → 송출 → 결과 보고 / 광고주 · 매체사 · 시민 동선: 접근 → 시선 → 참여 → 이동 / 시민 · 매체사 | 브랜드 · 공간 임팩트 · 현장 내구성 · 설치 · 시공 · 규제 · 인증 | LED 사이니지 · LCD 사이니지 · 케어 · 유지관리 서비스 · 콘텐츠 제작 지원 |
| OF | 오피스 · 업무 빌딩 / 오피스 | 로비 · 회의실 · 업무 공간 · 라운지 · 타운홀 | 직원의 하루: 출근 → 회의 → 집중 업무 → 퇴근 / 직원 · 시설 관리팀 · 타운홀 · 행사: 준비 → 진행 → 원격 참여 → 정리 / 경영진 · 직원 · 운영팀 · 방문객 동선: 로비 안내 → 회의실 이동 → 미팅 → 배웅 / 방문객 · 안내 직원 · 직원 | 원격 통합 관리 · 브랜드 · 공간 임팩트 · 설치 · 시공 · 쾌적 · 공기질 | 시스템에어컨 · LED 사이니지 · LCD 사이니지 · MagicINFO · SmartThings |
| RS | 주거 분양 · 주택 / 주거 분양 | 주방 · 거실 · 침실 · 세탁 공간 · 견본주택 | 분양부터 입주까지: 견본주택 방문 → 계약 → 입주 → 생활 / 예비 입주민 · 분양 담당 · 시행사 · 입주민의 하루: 아침 → 외출 → 귀가 → 취침 / 입주민 · 관리사무소 · 견본주택 투어: 입장 → 주방 → 거실 → 상담 / 방문객 · 분양 상담사 | 분양 · 자산 가치 · 디자인 조화 · 쾌적 · 공기질 · 에너지 절감 | 시스템에어컨 · 빌트인 주방가전 · 리빙가전 · SmartThings · DMS · 공조 제어 |
| ID | 인테리어 · 빌트인 파트너 / 인테리어 | 키친 전시장 · 거실 쇼룸 · 빌트인 존 · 상담 공간 | 쇼룸 방문: 입장 → 키친 체험 → 거실 연출 → 상담 / 방문 고객 · 디자이너 · 시공부터 입주까지: 설계 → 시공 → 설치 확인 → 입주 / 고객 · 디자이너 · 시공 파트너 · 설치 후 하루: 아침 주방 → 외출 → 귀가 → 휴식 / 고객 가족 | 디자인 조화 · 브랜드 · 공간 임팩트 · 설치 · 시공 · 쾌적 · 공기질 | 빌트인 주방가전 · 리빙가전 · 시스템에어컨 · SmartThings |
| ED | 교육 · 캠퍼스 / 교육 · 캠퍼스 | 강의실 · 도서관 · 기숙사 · 학생회관 | 학생의 하루: 등교 → 강의 → 도서관 → 기숙사 / 학생 · 교수 · 교직원 · 수업 한 시간: 수업 준비 → 강의 → 모둠 활동 → 정리 / 교수 · 학생 · 시험 · 행사 기간: 공지 → 출결 → 시험 → 결과 안내 / 학생 · 교직원 | 교육 · 학습 환경 · 업무 효율 · 협업 · 회의 · 쾌적 · 공기질 | 시스템에어컨 · 갤럭시 탭 · PC · 노트북 · 무인 과금 · 케어 · 유지관리 서비스 |
| PB | 공공 · 교통 인프라 / 공공 · 교통 | 교통 상황실 · 역 대합실 · 승강장 · 탐방센터 | 관제실 24시간: 주간 모니터링 → 사고 발생 → 대응 → 교대 / 관제 요원 · 현장 직원 · 시민 이용 동선: 역 출입구 → 안내 → 승강장 → 하차 / 시민 · 역무원 · 현장 순찰: 출동 준비 → 현장 → 상황 공유 → 복귀 / 현장 직원 · 관제 요원 | 현장 내구성 · 데이터 · 모니터링 · 안전 · 재난 · 시스템 연동 | LED 사이니지 · LCD 사이니지 · 시스템에어컨 · 안전 · 관제 솔루션 · Knox · Knox Configure |
| MD | 의료 · 요양 · 케어 / 의료 | 진료 대기실 · 진료실 · 병실 · 재활치료실 | 외래 환자 동선: 접수 → 대기 → 진료 → 수납 / 환자 · 보호자 · 의료진 · 입원 하루: 회진 → 식사 → 재활 → 야간 / 환자 · 간호사 · 의료진 · 요양 시설 하루: 기상 → 프로그램 → 식사 → 취침 / 어르신 · 요양보호사 · 가족 | 쾌적 · 공기질 · 업무 효율 · 원격 통합 관리 · 고객 경험 | 시스템에어컨 · 리빙가전 · LCD 사이니지 · SmartThings · 파트너 앱 · 주문 결제 |
| MF | 제조 · 물류 · 현장 / 제조 · 물류 | 생산 시설 · 물류 현장 · 재배 하우스 · 사무 공간 | 교대 근무 하루: 출근 점검 → 작업 → 이상 감지 → 교대 / 작업자 · 관리자 · 물류 흐름: 입고 → 분류 → 출고 → 배송 추적 / 작업자 · 관제 담당 · 안전 점검: 작업 전 → 위험 구역 → 경보 → 보고 / 작업자 · 안전 관리자 | 현장 내구성 · 업무 효율 · 원격 통합 관리 · 에너지 절감 | 시스템에어컨 · 갤럭시 탭 · 갤럭시 워치 · 태그 · Knox · Knox Configure · 파트너 앱 · 주문 결제 |
| FN | 금융 / 금융 | 영업점 객장 · 상담 창구 · 본사 로비 · 대강당 | 고객 방문 동선: 입구 → 대기 → 창구 상담 → 배웅 / 고객 · 창구 직원 · 영업점 하루: 오픈 → 피크 → 마감 정산 → 보안 점검 / 창구 직원 · 지점장 · 본사 · 찾아가는 영업: 방문 준비 → 고객 상담 → 전자 서명 → 후속 / 영업 직원 · 고객 | 고객 경험 · 보안 · 기기 통제 · 브랜드 · 공간 임팩트 · 설치 · 시공 | 갤럭시 탭 · LED 사이니지 · LCD 사이니지 · Knox · Knox Configure · 파트너 앱 · 주문 결제 |
| OE | 파트너 전용 단말 · 에디션 / 파트너 단말 | 이동 중 · 업무 현장 · 골프 필드 · 가정 | 사용자의 하루: 아침 → 이동 → 업무 · 레저 → 귀가 / 최종 사용자 · 단말 도입 과정: 기획 → 맞춤 개발 → 배포 → 운영 / 파트너사 · 삼성 · 사용자 · 현장 업무: 출동 → 측정 · 기록 → 공유 → 복귀 / 현장 작업자 · 관리자 | 맞춤 개발 · 시스템 연동 · 보안 · 기기 통제 · 현장 내구성 | 갤럭시 스마트폰 · 갤럭시 탭 · 갤럭시 워치 · 태그 · 파트너 앱 · 주문 결제 · 전용 에디션 · 커스터마이징 |

주: 「요구」·「자주 쓰인 것」 칸은 원본 배열을 「 · 」로 이은 것이라 항목 경계는 원본(`SC1T.txt` 의 `needs`·`used` 배열)을 따른다(예: FB `used` = ["시스템에어컨", "LCD 사이니지", "갤럭시 탭", "파트너 앱 · 주문 결제", "MagicINFO"]).

### 10.5 솔루션 동작 사전(`seed/solution_actions.yaml`, draft — KB 솔루션 페이지 메시지로 검수)
| 솔루션 | 동작(라벨) | 효과 한 줄 | 키워드 |
|---|---|---|---|
| MagicINFO | 전원 스케줄 | 시간 맞춰 자동 점등 | 켜져 있어야, 자동으로 켜, 꺼, 오픈, 마감 |
| MagicINFO | 시간대 레이아웃 | 시간대별 화면 전환 | 피크, 점심, 아침 메뉴, 시간대 |
| MagicINFO | 원격 배포 | 한 번에 배포 · 미수신 알림 | 전국, N개 매장, 배포, 본사 |
| MagicINFO | 장애 알림 | 미수신 · 오류 즉시 알림 | 장애, 오류, 미수신 |
| MagicINFO | 즉시 변경 | 품절 · 변경 즉시 반영 | 품절, 바로 내린다, 즉시 |
| SmartThings Pro | 에너지 리포트 | 매장별 전력 리포트 | 전력, 사용량, 집계 |
| SmartThings Pro | 일괄 OFF | 디스플레이 · 조명 함께 끄기 | 마감, 끄기, 일괄 |
| VXT | 원격 통합 관리 | 클라우드로 가맹점 화면 관리 | 원격, 클라우드, 가맹점 |
| LYNK Cloud | 객실 TV 통합 관리 | 투숙객 맞춤 콘텐츠 | 객실, 투숙객, 체크인 |
| b.IoT · SAC 제어 | 공조 통합 제어 | 공간별 쾌적 · 에너지 절감 | 냉난방, 공조, 온도 |
| Knox Suite | 기기 등록 · 관리 | 업무 단말 일괄 설정 · 보안 | 태블릿 배포, 단말, 보안 |

장면 칩 라벨은 `{솔루션} · {동작}`(예 「MagicINFO · 원격 배포 · 장애 알림」처럼 같은 솔루션의 동작이 둘 이상이면 「 · 」로 이음).

### 10.6 예시 골격(`seed/skeletons.yaml`, **(신규)** 제안 문장 — 업종 프리셋 외 골격)
- 매장 하루: 「07:00 {책임자}가 매장을 오픈한다.\n11:30 점심 피크. 손님이 몰린다.\n14:00 본사가 오후 프로모션을 내린다.\n21:00 마감.」
- 신메뉴 출시일: 「전날 본사가 신메뉴 콘텐츠를 예약한다.\n07:00 오픈과 함께 메뉴가 바뀐다.\n12:00 신메뉴 주문이 몰린다.\n20:00 반응을 집계한다.」
- 장애 발생 상황: 「10:00 매장 화면 하나가 꺼진다.\n10:05 본사가 알림을 받는다.\n10:20 원격으로 조치한다.\n10:30 정상화된다.」
- 업종을 알면 그 업종 프리셋 흐름(§10.4)을 「{단계}. …」 줄로 펼친 골격을 쓴다.

---

## 11. 열린 질문
1. **Storyboard 끌어오기**: scenario 는 storyboard 를 consume 하지 않아 사이드바 Storyboard 항목은 workspace 요약만 쓸 수 있다. 공간·고객 정보를 제대로 재사용하려면 `services.yaml` 의 scenario `consumes` 에 `storyboard`(와 `requirements`)를 추가해야 한다.
2. **조감도 「새로 만들기」 시점**: SC3 제출 때 조감도 초안을 만들고 사용자가 이어서 완성하게 했다(배치 확인 없이 3D 를 자동 생성하지 않음). 시나리오 완료 직후 BE4 까지 자동 진행할지?
3. **「[00]」 과 「[확정 필요]」 의 구분**: 보드에서 시트 2 는 「가치 [00]」, 시트 3 은 「[확정 필요]」. 이 문서는 장면 문장의 근거 없는 수치 = 「[00]」(확정 필요 개수에 포함), 시트 가치 칸 표기는 템플릿이 정한다고 보았다. 제안서 PR7Q(확정 필요 목록)와 용어를 맞출지.
4. **보낼 섹션**: 표준·퀵윈 제안서에는 「공간별 가치 제공 시나리오」 섹션이 없고 솔루션 섹션의 SXS(솔루션 공간 시나리오)가 있다. 그때 어디에 넣을지 제안서 서비스가 정한다고 보았다(`sheet_plan` 은 힌트).
5. **방문객 동선 축의 시간**: 조감도에서 온 「방문객 동선」 시나리오는 시각 없는 순서 단계라 VM-D(하루 타임라인)를 쓸 수 없다. 순서 라벨(「1 쇼윈도」)을 시간대 머리에 써도 되는지.
6. **SC4 「조감도 추가」 링크**가 보드에서 BE5Z 로 간다. 조감도 연결이 없을 때 띄우는 「조감도 연결」 팝오버(SC1 선택지 재사용)는 보드 밖 결정이다.
7. **업종 매핑 빈칸**(SV·TP·VN·AD·ID·OE)이 KB 에서 `<<FILL>>` 이라 사례 수 근거가 「[00]」으로 많이 나온다. 매핑 확정 일정.
8. **솔루션 동작 사전**(§10.5)은 제안 초안이다. 솔루션 담당자 검수와 KB 메시지 id 연결이 필요하다.
9. **장면 일괄 이미지 해상도**: 제안서 시트용으로 fhd 로 정했다. uhd 가 필요하면 IMG3V 로 개별 업스케일.
10. **스트리밍**: ai-tools 계약에 `llm.stream` 이 있는지. 없으면 SC4G 의 「작성 중」 부분 문장은 표시하지 않는다.
