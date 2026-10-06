# 07. 이미지 생성 (image · IMG) — 화면 수용 기준

- 범위 보드(12): `UC_IMG` `IMG0` `IMG1` `IMG2` `IMG2R` `IMG2P` `IMG3G` `IMG3` `IMG3X` `IMG3E` `IMG3V` `IMG4`
- 원천: `docs/screens/webapp2/<보드>.dc.html`, `docs/screens/_text/webapp2/<보드>.txt`, `docs/ARCHITECTURE.md`, `config/services.yaml`, `winmate-kb/docs/*`
- 표기: 「…」 = 보드 문구 그대로(공백·가운뎃점 포함). **(신규)** = 보드에 없는 상태에 쓰는 제안 문구(디자인 확인 전까지 이 문구 사용). `{변수}` = 템플릿 자리.
- 이 문서는 birdseye(08)·scenario(09)가 쓰는 **생성 이미지 공통 기능**(렌더 API·편집·업스케일·품질 확인·AI 표기·출처 메타데이터)의 원천이기도 하다.

---

## 1. 목적과 진입점

**목적.** 제안서에 넣을 공간·배경·시나리오 이미지를 만들고(T2I), 참조 이미지·현장 사진 합성·부분 수정·변형·비율/해상도·내보내기까지 한 흐름에서 처리한다. 모든 생성 이미지는 생성 조건·참조 출처·모델·업스케일 경로를 메타데이터로 남긴다(“이미지는 출처·메타데이터가 매우 중요”). 생성 이미지는 이 서비스 한 곳에서만 만든다 — birdseye·scenario 는 T2I 를 직접 부르지 않고 이 서비스의 렌더 API(§6.9)를 쓴다.

| 항목 | 값 |
|---|---|
| 서비스 | `image` · 포트 **5107** · `worker: true` · 큐 `wm:q:image` |
| 게이트웨이 경로 | `/api/image/v1/...` (내부 `/v1/...`), `GET /healthz` |
| 소유 경로 | `services/image/**`, `web/src/features/image/**` |
| consumes | `ai-tools, kb, files, jobs, workspace, export` (그 밖 서비스는 서버에서 호출 금지 — 제안서 연동은 §8 참고) |
| 데이터 | `${DATA_DIR}/image/image.sqlite` + LangGraph 체크포인트 `${DATA_DIR}/image/checkpoints.sqlite` |
| 웹 모듈 | `web/src/features/image/` — `index.ts` 에 라우트·사이드바 그룹(`image`, 이름 「이미지 생성」, 목록 `/image`, 새 작업 `/image/new`) 선언 |
| 스텝바 | `steps = ['이미지 유형', '상세 조건', '생성 결과']` · IMG1=1, IMG2/IMG2R/IMG2P=2, IMG3G/IMG3/IMG3X/IMG3E/IMG3V=3, IMG4=3 + `complete` |
| 상단바 | `section="이미지 생성"`, `title` = 작업 제목(새 작업이면 「새 작업」, 목록이면 「작업 목록 · 갤러리」) |

**진입점**

1. 홈 '이미지 생성' 카드 → IMG1(새 작업).
2. 사이드바 그룹 「이미지 생성」 → IMG0, 그룹 항목(최근 작업) → 그 작업의 현재 화면(`work.route`, §5).
3. 상단 '이미지 검색' 팝오버(셸 소유) — 작업 중이면 「현재 작업에 추가」로 IMG1/IMG2 참조에 들어가고, 홈(작업 없음)에서는 「대화에 첨부」로 새 작업을 만들고 IMG2R 로 간다.
4. 다른 기능의 이미지 요청(공간 시나리오 장면, 제안서 표지 배경 등) → IMG0 「다른 기능에서 요청한 이미지」 → 「만들기」 → IMG1(미리 채움).
5. SC4E 「이미지 생성에서 다시 만들기」 → IMG2(장면 설명·제품·비율 미리 채움).
6. 서비스 간: birdseye·scenario 가 `POST /v1/renders`(렌더 API)로 생성·편집을 요청(화면 없음).

**화면 원칙(전 화면 공통).** 한 화면에는 W 말풍선 1개 + 사용자 입력 메아리(있으면) + 하단 작업 카드 1장만 둔다. 보드에 없는 패널을 늘리지 않고, 추가 정보는 팝오버·접힘으로 숨긴다. W 말풍선 문구는 LLM 이 쓰지 않고 상태 값으로 채우는 템플릿이다(§4 각 화면). 템플릿의 조사(을/를 · 이/가 · 은/는 · 으로/로)는 앞말 발음으로 고른다 — 한글은 받침, 숫자는 읽는 소리(1·3·6·7·8·0 → 을/이/은, 2·4·5·9 → 를/가/는), 영문은 마지막 글자 발음 표(예: 「시안 1을」, 「시안 2가」, 「The Wall을」). 문서의 템플릿은 대표형 하나로 적었다.

---

## 2. 화면 목록

| 보드 | 제목 | 라우트 / 상태 제안 | 주요 요소 |
|---|---|---|---|
| `UC_IMG` | 이미지 생성 · 유스케이스 맵 | 런타임 화면 아님(흐름 원천). 개발용 `/_dev/uc/image` 선택 | 레인 5, 노드 18, 대표 흐름 3, 노트 2 |
| `IMG0` | 이미지 생성 · 작업 목록 · 갤러리 | `/image` | 시작 버튼 3, 작업 목록, 다른 기능 요청, 갤러리(탭·필터·선택 바) |
| `IMG1` | 이미지 생성 1/3 · 이미지 유형 | `/image/new` (`?request=irq_…`, `?work=imw_…`) | 유형 카드 3, 장면 설명, 참조 첨부 |
| `IMG2` | 이미지 생성 2/3 · 상세 조건 | `/image/w/:workId/conditions` | 등장 제품, 스타일, 비율·장수, 참조 이미지 |
| `IMG2R` | 이미지 생성 · 참조 이미지 고르기 | `/image/w/:workId/references` (새로 시작 `/image/new/references`) | 탭 4, 검색·필터, 결과 8, 고른 참조별 따를 요소·강도 |
| `IMG2P` | 이미지 생성 · 현장 사진 제품 합성 | `/image/w/:workId/composite` (새로 시작 `/image/new/composite`) | 사진 탭, 벽면 인식, 제품 배치 캔버스, 배열·설치·기준 치수·토글 |
| `IMG3G` | 이미지 생성 · 생성 중 | `/image/w/:workId/run/:runId` — run 상태 `queued`·`running` | 단계 4, 시안별 진행, 내 대기열, 취소, 완료 알림 |
| `IMG3` | 이미지 생성 3/3 · 생성 결과 | `/image/w/:workId/result` (`?image=img_…`) | 시안 4, 선택, 빠른 수정 칩, 수정 요청, 저장, 제안서에 넣기 |
| `IMG3X` | 이미지 생성 · 생성 실패 · 제한 안내 | `/image/w/:workId/run/:runId` — run 상태 `awaiting_input` | 완성 n장 + 보류 n장, 보류 사유 카드, 대안 선택 |
| `IMG3E` | 이미지 생성 · 부분 수정 | `/image/w/:workId/edit/:imageId` | 영역 도구 4, 크기, 전/후 비교, 수정 기록, 영역 목록, 제품 외형 고정 |
| `IMG3V` | 이미지 생성 · 변형 · 비율 · 해상도 | `/image/w/:workId/variants/:imageId` | 변형 4장, 비율 4종, 맞추는 방법 3, 업스케일 3 |
| `IMG4` | 이미지 생성 · 내보내기 · 제안서에 넣기 | `/image/w/:workId/export/:imageId` (`?version=imv_…`) | 파일 형식 4, 해상도, AI 표기, 넣을 제안서·시트, 다른 작업에 쓰기 |

---

## 3. 사용자 흐름

### 3.1 기본 흐름(기존 IMG1 · IMG2 · IMG3)
`IMG1`(유형·장면 설명) → `IMG2`(상세 조건) → 「이미지 4장 생성」 → `IMG3G` → (완료) `IMG3` → 「제안서에 넣기」 → `IMG4` → 제안서 `PRS4` 시트.

### 3.2 대표 흐름(UC_IMG 「대표 흐름」)
| 이름 | 화면 순서 |
|---|---|
| 「현장 사진 합성」 | `IMG0` › `IMG2P` › `IMG3G` › `IMG3E` › `IMG4` |
| 「참조 스타일로」 | `HomeImage` › `IMG2R` › `IMG3G` › `IMG3V` |
| 「실패 후 대안」 | `IMG3G` › `IMG3X` › `IMG2` › `IMG3G` › `IMG3` |

### 3.3 갈래
- **참조**: IMG1 첨부 아이콘(「참조 이미지 첨부」) 또는 IMG2 「+」 → IMG2R → 「참조 2장 적용」 → IMG2 / 「적용하고 바로 4장 생성」 → IMG3G / 「취소」 → IMG2.
- **현장 사진**: IMG0 「현장 사진에 제품 합성」 → IMG2P(업로드 → 벽면 인식 → 배치) → 「합성 이미지 4장 생성」 → IMG3G.
- **떠나도 이어서 생성**(UC 노트): IMG3G 를 떠나도 작업은 계속된다. IMG0 작업 목록·갤러리에 진행률이 보이고, 끝나면 완료 알림이 온다.
- **시안은 버전으로 쌓임**(UC 노트): 부분 수정·변형·보정·비율 버전마다 버전이 추가되고, 이전 버전으로 언제든 돌아간다(삭제 없음).
- **결과 활용**: IMG4 → 제안서 시트(`PRS4` 등) / 「공간 시나리오 장면으로」(`SC4`) / 「조감도 참조로」(`BE1`) / 「팀에 공유」 / IMG0.

### 3.4 라우팅 규칙(에이전트가 자동으로 정하는 것 · 사용자가 정할 것)
| # | 시점 | 에이전트가 자동으로 | 사용자에게 묻는 것 |
|---|---|---|---|
| R1 | IMG1 → IMG2 | 장면 설명에서 제품·수량 추출(KB A1 + LLM, “3연”→×3), 작업 제목 생성, 참조 검색어·업종 추정 | 없음(결과는 IMG2 칩으로 보여 주고 고칠 수 있음) |
| R2 | 요청에서 시작 | 요청의 유형·설명·제품·비율을 IMG1/IMG2 에 채움 | 유형·설명 확인만 |
| R3 | 생성 버튼(「이미지 {count}장 생성」 등)을 누를 때 | 정책 사전 검사(§7.3). 안전한 기본 대안으로 만들 수 있는 시안은 바로 만들고, 사용자 선택이 필요한 문제가 있으면 `floor(N/2)`장을 보류 | 보류된 시안의 대안만(IMG3X) |
| R4 | 참조 예산 초과 | 참조 이미지 배정 규칙(§10.3)으로 보낼 이미지와 글로 바꿀 이미지를 결정 | 없음 |
| R5 | 품질 확인 실패 | 1회 자동 재생성(QC_MAX_RETRY=1), 그래도 실패면 시안에 확인 필요 표시 | 없음 |
| R6 | 자유 입력(수정 요청·변형 요청·내보내기 요청·다른 대안) | LLM 이 화면별 구조화 동작으로 바꿈(§4 각 화면) | 해석이 모호할 때만 W 가 한 번 되묻기 |
| R7 | IMG4 | 넣을 시트 추천(제안서 서비스가 계산, §8) | 넣을 제안서·시트 확정 |
| R8 | 모델 능력 부족 | §7.2 표대로 대체 경로 자동 선택, 결과 메타데이터에 경로 기록 | 없음(대체 경로로 품질이 떨어지면 안내 문구만) |

### 3.5 작업 상태 전이
`draft` → (`queued` → `running`) → `awaiting_input`(보류 있음) → `running` → `done` / `failed` / `canceled`. 편집·변형·비율 run 은 같은 작업 아래 새 run 으로 쌓이고, 작업 상태는 가장 최근 run 의 상태를 따른다(진행 중인 run 이 하나라도 있으면 `running`).

---

## 4. 화면별 상세

### 4.0 UC_IMG · 유스케이스 맵
런타임 화면이 아니라 흐름의 원천이다. 구현은 아래 연결이 모두 동작하는지로 검증한다.
- 머리: 「USE CASE MAP · IMG」, 「이미지 생성 — 유스케이스 맵」, 「기본 흐름 3화면에 새 화면 8개를 더해 들어오는 길부터 결과 활용까지 정리했습니다. 칸을 누르면 그 화면으로 이동합니다.」 통계 「3 기존 화면」 「8 추가 화면」 「6 연결된 화면」.
- 레인: 「01 들어오는 길 · 어디서 이미지 생성을 시작하나」, 「02 입력 방식 · 설명 · 조건 · 참조 이미지 · 현장 사진」, 「03 진행 · 확인 상태 · 생성 대기 · 결과 확인 · 실패와 제한」, 「04 편집 · 버전 · 한 장을 골라 고치고 변형하기」, 「05 결과 활용 · 내보내기 · 제안서 · 다른 기능」.
- 노드와 다음 화면(구현 대상 연결):

| 코드 | 이름 | 설명(보드) | 다음 |
|---|---|---|---|
| Main | 홈 · 이미지 생성 카드 | 홈 메인 카드에서 새 이미지 작업을 바로 시작합니다. | IMG1 |
| IMG0 | 작업 목록 · 갤러리 | 내 생성 이미지 · 사내 자산 탭과 필터, 생성 중 · 실패 작업 이어가기 | IMG1 · IMG2R · IMG2P · IMG3G |
| HomeImage | 상단 이미지 검색 | 사내 자산 · 내 이미지를 골라 참조로 첨부하고 시작합니다. | IMG2R · IMG2 |
| SC4E | 시나리오 장면에서 | 공간 시나리오 장면의 설명 · 제품을 넘겨 장면 컷을 만듭니다. | IMG2 · IMG0 |
| IMG1 | 이미지 유형 · 장면 설명 | 공간 · 배경 · 시나리오 중 고르고 장면을 한두 문장으로 설명 | IMG2 · IMG2R · IMG2P |
| IMG2 | 상세 조건 | 등장 제품 · 스타일 · 비율 · 장수, 이미지 검색에서 고른 참조 | IMG3G · IMG3 · IMG2R |
| IMG2R | 참조 이미지 · 사내 자산 스타일 | 사내 자산에서 고르고 색감 · 구도 · 소재 중 따를 요소와 강도 지정 | IMG2 · IMG3G |
| IMG2P | 현장 사진에 제품 합성 | 고객 매장 사진 → 벽면 인식, 제품 위치 · 크기 · 기준 치수 지정 | IMG3G · IMG1 |
| IMG3G | 생성 중 | 4장 진행률과 단계, 내 대기열, 장별 · 전체 취소, 완료 알림 | IMG3 · IMG3X · IMG2 · IMG0 |
| IMG3 | 생성 결과 | 4장 중 고르기, 빠른 수정 칩, 내 이미지에 저장, 제안서에 넣기 | IMG3E · IMG3V · IMG4 · PRS4 |
| IMG3X | 생성 실패 · 제한 안내 | 제품 인식 실패, 경쟁사 로고 · 실존 인물 제한 → 대안 제시 | IMG2 · IMG3G · IMG3 |
| IMG3E | 부분 수정 | 영역을 고르고 지시문으로 고치기, 수정 전 / 후 비교 | IMG3 · IMG4 |
| IMG3V | 변형 · 비율 · 해상도 | 16:9 · 4:3 · 세로 비율, 업스케일, 한 장 기준 변형 4장 | IMG3G · IMG3E · IMG4 |
| IMG4 | 내보내기 · 제안서에 넣기 | 다운로드 형식, 넣을 제안서와 시트 고르기, 다른 기능으로 보내기 | PRS4 · SC4 · BE1 · PR1 · IMG0 |
| PRS4 | 제안서 섹션에 바로 넣기 | 생성 결과의 '제안서에 넣기' — 섹션 작성 화면에 이미지 배치 | PR5 · PR6 |
| PRS2 | 슬라이드에 끌어 넣기 | 이미지 검색에서 끌어 스토리라인 슬라이드 위에 놓기 | PR6 |
| SC4 | 시나리오 장면에 반영 | 만든 이미지를 공간 시나리오의 장면 컷으로 사용 | SC5 |

- 노트: 「떠나도 이어서 생성 — 생성 중 화면을 벗어나도 IMG0 작업 목록에 진행률이 보이고, 끝나면 알림이 옵니다.」, 「시안은 버전으로 쌓임 — 부분 수정 · 변형마다 시안이 추가되고, 이전 시안으로 언제든 돌아갈 수 있어요.」
- 범례: 「기본 흐름 (기존 IMG1 · IMG2 · IMG3)」 「추가 화면」 「다른 기능 화면」 「기존 연결」 「새 화면으로 생기는 연결」, 버튼 「이미지 작업 목록 열기」 → IMG0.

### 4.1 IMG0 · 작업 목록 · 갤러리
**머리.** 「이미지 생성」, 「내 작업 {works_total} 개 · 생성 이미지 {images_total} 장 · 결과를 다시 고치거나 제안서에 바로 넣을 수 있어요」. 버튼: 「현장 사진에 제품 합성」(→ 새 composite 작업, IMG2P), 「참조 이미지로 시작」(→ 새 작업, IMG2R), 「새 이미지 만들기」(주 버튼, → IMG1).

**작업 목록(왼쪽)** — 머리 「작업 목록」 `{n}`, 정렬 「최근 수정순」, 검색(라벨 「작업 검색」, placeholder 「작업 · 고객사 검색」).

| 필드 | 타입 | 출처 |
|---|---|---|
| 썸네일 | 320px 이미지 · 없으면 빈 칸 | 작업의 대표 시안 최신 버전 `thumb` |
| 제목 | string(≤ 24자) | `work.title` (R1 에서 LLM 생성, 유형별 접미사: 공간 「… 시안」, 배경 「… 배경 이미지」, 시나리오 「… 시나리오 컷」, 합성 「… 벽면 합성」) |
| 메타 | `{고객사} · {유형} · {장수}` | `work.customer_name`, 유형 라벨, 최근 run(예 「A 커피 프랜차이즈 · 공간 · 4장」, 「B 병원 · 배경 · 변형 4장」, 「A 커피 프랜차이즈 · 현장 사진 합성」) |
| 시각 | 상대 시각 | `updated_at` → 「방금」/「N분 전」/「N시간 전」/「어제」/「N일 전」(2~6)/「지난주」(7~13)/「M월 D일」 |
| 상태 배지 | 라벨·색·아이콘 | 아래 표 |
| 링크 | route | `work.route` |

상태 배지(우선순위 위→아래, 하나만 표시):

| 조건 | 라벨 | 색 / 아이콘 |
|---|---|---|
| 진행 중 run | 「생성 중 {done} / {total}」 | 파랑 / 시계 |
| `awaiting_input` | 「{held}장 생성 불가 · 대안 보기」 | 잉크 / 정보 |
| composite 작업이 배치 편집 중(run 없음) | 「제품 위치 지정 중」 | 회색 / 연필 |
| 제안서에 쓰인 버전 있음 | 「제안서 사용 중」 | 파랑 / 체크 |
| 마지막 동작이 내보내기 | 「{FORMAT}로 내보냄」(예 「PPTX로 내보냄」) | 회색 / 다운로드 |
| 완료 | 「완료」 | 회색 / 체크 |
| 실패 | **(신규)** 「생성 실패 · 다시 시도」 | 잉크 / 정보 |

**다른 기능에서 요청한 이미지** — 머리 「다른 기능에서 요청한 이미지」 `{n}`. 행: 제목(예 「장면 2 · 점심 피크 주문」), 출처(예 「공간 시나리오 · A 커피 매장 하루」, 「B2B 제안서 · B 병원 안내 시스템 제안」), 버튼 「만들기」 → `POST /v1/requests/{id}:start` → IMG1(미리 채움). `status=open|in_progress` 인 요청만 보인다. 0건이면 섹션 숨김.

**갤러리(오른쪽)** — 탭 「내 생성 이미지 {n}」(활성), 「사내 자산 {n}」(→ IMG2R, 사내 자산 탭). 검색(라벨 「이미지 검색」, placeholder 「이미지 · 고객사 검색」). 유형 칩 「전체」 「공간」 「배경」 「시나리오」 「제품 합성」(단일 선택, 기본 「전체」). 드롭다운 「고객사 전체」 「비율」 「제안서 사용」. 정렬 「최근 생성순」.

| 타일 필드 | 타입 | 출처 |
|---|---|---|
| 이미지 | thumb | 시안의 현재 버전 |
| 제목 | string | `image.label` 또는 작업 제목 기반(예 「메뉴보드 시안 1」, 「로비 배경 v1」) |
| 메타 | `{고객사 약칭} · {유형} · {비율}` | 예 「A 커피 · 공간 · 16:9」; 생성 중이면 `{고객사 약칭} · {유형} · 생성 중` |
| 생성 중 오버레이 | 「생성 중」 「{done} / {total}」 「진행 보기」 | 진행 중 run(→ IMG3G) |
| 배지 | 「제안서 사용 중」 | `image.used_in.length > 0` |
| 체크박스 | 다중 선택 | 생성 중 타일은 선택 불가 |
| 호버 동작 | 「부분 수정」(→IMG3E) 「변형」(→IMG3V) 「내보내기」(→IMG4) | — |

- 기본 목록은 `origin ∈ {image, scenario}` 인 시안만(조감도 렌더는 BE 에서 본다). 숨김·취소된 시안 제외.
- 고객사 약칭: workspace 프로젝트의 `customer_short`, 없으면 고객사명 앞 두 어절.
- 선택 바(1장 이상 선택 시): 「{n}장 선택됨」, 「선택 해제」, 「다운로드」(export ZIP, 202), 「변형 만들기」(선택 시안마다 변형 run 생성 후 첫 시안의 IMG3V 로), 「제안서에 넣기」(→ IMG4, 다중 넣기 모드).
- 상태: 로딩(스켈레톤 9칸), 빈 상태 **(신규)** 「아직 만든 이미지가 없어요」 + 시작 버튼 3개, 오류 **(신규)** 「목록을 불러오지 못했어요 · 다시 시도」.
- 진행 갱신: 진행 중 run 마다 jobs SSE 구독, 끊기면 15초 폴링.

### 4.2 IMG1 · 이미지 유형 (1/3)
- W: 「어떤 이미지를 만들까요? 제안서에서 쓰일 자리에 따라 유형을 고르고, 원하는 장면을 한두 문장으로 설명해 주세요. 유형에 따라 다음 단계에서 묻는 조건이 달라집니다.」
- 작업 카드 머리: 「이미지 유형 · 하나 선택 · 1 / 3」

| 유형 카드 | 설명(보드) | `kind` |
|---|---|---|
| 「공간」(기본 선택) | 「매장·로비·회의실 등 제품이 설치된 공간 장면」 | `space` |
| 「배경」 | 「표지·섹션 슬라이드용 분위기 배경, 텍스트 영역 확보」 | `background` |
| 「시나리오」 | 「사람이 제품을 사용하는 순간을 담은 컷」 | `scenario` |

- 장면 설명: 라벨 「장면 설명」, textarea placeholder 「예) 카페 카운터 위에 3연 메뉴보드가 걸린 장면, 낮 시간, 손님 2~3명」, 최대 500자. 오른쪽 아이콘 링크(aria 「참조 이미지 첨부」) → IMG2R. 도움말 「참조 이미지는 상단 '이미지 검색'에서도 가져올 수 있어요」.
- 주 버튼 「상세 조건 입력」: 설명이 2자 미만이면 비활성. 누르면 작업 생성/갱신(`POST /v1/works` 또는 `PATCH`) 후 `POST /v1/works/{id}:prefill`(동기, 제한 10초) → IMG2.
- 상단바 이미지 검색 드롭 영역: `accepts=['image']` — 끌어 놓거나 「현재 작업에 추가」한 이미지는 참조로 붙는다.
- 요청에서 시작: 요청의 `prefill.kind`·`description` 을 채우고 유형 카드도 그에 맞춘다.
- 유형별로 IMG2 에서 달라지는 것(보드는 '공간'만 그림 — 아래는 구현 규칙):
  - `space`: 등장 제품 기본 펼침.
  - `background`: 등장 제품을 접고 **(신규)** 「제품 없이」를 기본값으로, 프롬프트에 텍스트 여백(기본: 왼쪽 40% 단순 배경)을 자동 확보. 요청이 제안서 슬롯에서 왔으면 슬롯의 텍스트 영역 위치를 따른다. 사용자에게 따로 묻지 않는다.
  - `scenario`: 사람은 항상 “실존하지 않는 가상 인물”로 생성(정책). 등장 제품 펼침.

### 4.3 IMG2 · 상세 조건 (2/3)
- 메아리: 「{유형 라벨}」 + 「· {장면 설명}」 (예 「공간 · 카페 카운터 위에 3연 메뉴보드가 걸린 장면, 낮 시간, 손님 2~3명」).
- W: 「좋습니다. 장면에 등장할 삼성 제품과 표현 스타일을 정해 주세요. 제품을 지정하면 실제 제품 외형과 비율을 반영해 생성합니다.」
- 작업 카드 머리: 「상세 조건 · 2 / 3」

| 영역 | 표시·컨트롤 | 출처·동작 |
|---|---|---|
| 「등장 제품」 | 칩 `{제품 표시명}{ ×qty}` + 제거 버튼(aria 「제거」). 예 「Smart Signage QM55C ×3」, 「Kiosk KM24C」 | prefill(R1): KB A1 엔티티 링킹 + LLM 수량. 표시명 = KB 제품군 표시명(카테고리 짧은 이름 + 모델) |
| 제품 입력 | 라벨 「제품명 입력」, placeholder 「제품명을 입력해 추가…」, 자동완성 5건, Enter = 첫 후보 추가 | KB 제품 검색(A1/엔티티) |
| 「스타일」 | 세그먼트 「실사 렌더」(기본) 「미니멀 3D」 「일러스트」 | `style = photo \| minimal_3d \| illustration` |
| 「비율 · 장수」 | 비율 「16:9」(기본) 「4:3」 「1:1」, 장수 「2장」 「4장」(기본) | `aspect`, `count` |
| 「참조 이미지」 | 썸네일 + 「×」(aria 「참조 이미지 제거」), 「+」(→ IMG2R) | `work.references` |
| 참조 안내 | 「{출처}에서 선택한 {n}장이 참조로 들어갔습니다」 (예 「이미지 검색에서 선택한 2장이 참조로 들어갔습니다」) | 참조가 상단 이미지 검색에서 왔을 때만 |

- 버튼: 「이전」(→ IMG1), 주 버튼 「이미지 {count}장 생성」(→ `POST /v1/works/{id}/runs {kind:'initial'}` → IMG3G).
- 제품 수량 상한 9(칩 안에서 `×` 숫자 클릭으로 1~9 조정, **(신규)** 툴팁 「수량 바꾸기」). 제품 0개도 허용(배경 등).
- 드롭 영역: 제품 칩 영역 `accepts=['product']`, 참조 영역 `accepts=['image']`.
- 상태: prefill 실패/시간 초과 → 칩 없이 열고 **(신규)** 「제품을 찾지 못했어요. 제품명을 입력해 주세요」를 입력칸 아래 표시. 참조 3장 초과 시 「+」 비활성.

### 4.4 IMG2R · 참조 이미지 고르기
- 메아리: IMG2 와 같음. W: 「참조할 이미지를 골라 주세요. 사내 자산은 브랜드 검수를 마친 이미지라 색감과 구도를 그대로 따라도 됩니다. 고른 이미지마다 무엇을 따를지 정할 수 있어요.」
- 탭: 「사내 자산」(기본) 「내 생성 이미지」 「유관 사례」 「내 파일 올리기」(업로드 아이콘).

| 탭 | 결과 출처 | 타일 출처 표기(`source`) |
|---|---|---|
| 사내 자산 | KB `image_search(q)` + 업종 필터(KR 업종 맥락) + `G1(space, category)`(장면 설명에서 공간·카테고리가 잡히면 앞에 둠). `rights ∈ {official, customer_case}` 만 — 셸(00) 의 「사내 자산」 출처가 정해지기 전까지의 임시 정의(셸 기준으로는 「제품 이미지」 + 「유관 사례 이미지」, 00-shell 갭 G-IMG-5) | 「사내 자산 · 도입사례 사진」 / **(신규)** 「사내 자산 · 삼성 공식 이미지」 |
| 내 생성 이미지 | `GET /v1/images?mine=true` | **(신규)** 「내 생성 이미지 · AI 생성」 |
| 유관 사례 | KB `D1(vertical, spaces, targets, text)` 상위 사례 → `G5(deployment)` 사진 | **(신규)** 「유관 사례 · 도입사례 사진」 |
| 내 파일 올리기 | files 업로드(JPG·PNG·HEIC, 20MB 이하) | **(신규)** 「내 파일 · 업로드」 |

- 검색: 라벨 「참조 이미지 검색」, 입력값 기본 = R1 이 뽑은 검색어(예 「카페 메뉴보드」).
- 필터: 「업종」 칩 4개(예 「외식 · 카페」 「리테일」 「호텔」 「오피스」 — 프로젝트 업종을 첫 칸·선택 상태로, 나머지는 Winmate 16 업종 중 결과가 많은 순), 「스타일」 「전체」(기본) 「실사」 「일러스트」. 스타일은 이미지 메타의 `visual_style`(i2t 분석 캐시) → 없으면 alt 규칙(“일러스트·아이소메트릭·그래픽” 포함 → 일러스트, 그 외 실사).
- 결과 머리: 「{n} 개 · 검수 완료」. “검수 완료” = 출처 URL·권리(`official`/`customer_case`)가 확인된 KB 자산(삼성 공식 게시 = 브랜드 검수 완료로 본다). 업로드·내 생성 이미지 탭에서는 이 문구 대신 **(신규)** 「{n} 개」.
- 결과 타일: 이미지, 라벨, 선택되면 번호와 역할 배지(예 「1」 「구도」, 「2」 「색감 · 조명」 — 역할 = 고른 따를 요소를 「 · 」로 연결). aria = 라벨.
- 오른쪽 패널 머리: 「참조 이미지 {n}장 · 무엇을 따를지」 「· 2 / 3」, 경고 「참조 속 사람 얼굴 · 타사 로고는 따라 그리지 않아요」.
- 고른 참조 카드: 번호, 라벨, 출처(`source`), 따를 요소 칩(다중) 「색감 · 조명」 「구도」 「제품 배치」 「소재」, 「강도」 세그먼트 「약」 「중」(기본) 「강」, 빼기(aria 「참조 빼기」). 새로 고를 때 기본 요소: 사내 자산=「구도」, 그 외=「색감 · 조명」.
- 하단: 「적용하면 상세 조건의 참조 이미지로 들어갑니다」, 「취소」(→ IMG2, 변경 버림), 「적용하고 바로 4장 생성」(적용 후 `count` 만큼 run 시작 → IMG3G; 문구의 4는 `count`), 주 버튼 「참조 {n}장 적용」(→ IMG2).
- 규칙: 참조는 최대 3장(4번째 선택 시 **(신규)** 「참조는 3장까지 고를 수 있어요」). 업로드 참조는 강도 「강」을 고를 수 없다(권리 미확인, **(신규)** 툴팁 「올린 사진은 ‘중’까지 따를 수 있어요」).
- 장면 설명이 비어 있는 상태(「참조 이미지로 시작」)에서 적용·생성하면 참조의 i2t 캡션으로 장면 설명을 자동 작성해 메아리에 보여 준다.

### 4.5 IMG2P · 현장 사진 제품 합성
- 상단바 제목 예: 「A 커피 카운터 벽면 합성」. 업로드 전에는 드롭 영역 **(신규)** 「현장 사진을 끌어 놓거나 올려 주세요 · JPG · PNG · HEIC」.
- W(인식 후): 「{면 라벨}을 설치 가능한 면으로 인식하고 {제품 약칭} {qty}대를 올려두었습니다. 끌어서 위치를, 모서리로 크기를 맞춰 주세요. 실제 치수를 하나 알려주시면 비율을 정확히 맞춥니다.」 (예: 「카운터 위 흰 벽면을 … QM55C 3대를 …」). 면을 못 찾으면 **(신규)** 「설치할 면을 찾지 못했어요. 제품을 끌어 원하는 위치에 놓아 주세요.」

**사진 탭** — 사진마다 탭: 썸네일, 라벨(i2t 가 붙인 위치명, 예 「카운터 벽면」, 「매장 안쪽」), 상태:

| 상태 | 문구 | 판정 |
|---|---|---|
| 인식 완료 | 「벽면 인식 완료」 (체크 아이콘) | 설치 가능 면 1개 이상 |
| 어두움 | 「어두워 인식 어려움 · 다시 촬영 권장」 (정보 아이콘) | 평균 휘도 < 0.22 또는 i2t 가 면을 못 찾음 + 휘도 < 0.30 |
| 인식 중 | **(신규)** 「인식 중」 | job 진행 |
| 실패 | **(신규)** 「인식하지 못했어요 · 다시 인식」 | i2t 오류·면 없음 |

버튼 「사진 추가」, 「촬영 가이드 · 다시 인식」(가이드 팝오버 + 현재 사진 재인식).

**배치 캔버스**
- 사진 위 오버레이: 인식된 면 영역 + 라벨 「인식된 벽면 · 설치 가능」, 배치 그룹 라벨 「{제품 약칭} ×{qty} · {배열}」(예 「QM55C ×3 · 가로 3연」), 그룹 둘레 손잡이 8개(모서리·변 중앙), 치수 라벨 「가로 약 {W} mm · 바닥에서 {H} mm」 — 추정 불가 값은 「[00]」 그대로 표시(보드 상태).
- 떠 있는 도구: 「복제」 「원근 맞춤」(모서리 4점 원근 편집, 인식된 면의 원근에 맞춰 스냅) 「삭제」.
- 보기 전환: 「배치 편집」(기본) / 「원본 사진」. 도움말 「끌어서 이동 · 모서리로 크기 조절」. 확대/축소 「−」 「100%」 「+」(25~400%).

**작업 카드** — 머리 「제품 배치 · 현장 사진 합성 · 2 / 3」.

| 컨트롤 | 값 | 동작 |
|---|---|---|
| 「제품 추가」 | 제품 검색 팝오버(상단바 제품 탐색과 같은 드롭 `accepts=['product']`) | 새 배치 그룹 |
| 제품 줄 | 「Smart Signage QM55C ×3」 | 작업 조건의 제품 |
| 「배열」 | 「가로 3연」(qty=3 기본) 「세로 3연」 「따로 배치」 | 그룹 배열(간격 10 mm) |
| 「설치」 | 「벽 부착」(기본) 「천장 매달기」 | 천장 매달기면 상단에 브래킷 표현 |
| 「기준 치수」 | 「카운터 폭」 `[00]` mm, 「설치 높이」 `[00]` mm (placeholder 「[00]」) | 하나만 넣어도 축척 계산 |
| 토글 | 「원근 · 조명 맞춤」(켜짐), 「화면에 메뉴 넣기」(켜짐) | 생성 단계 옵션 |
| 안내 | 「치수를 모르면 비워 두세요. 사진 속 비율로 추정합니다」 | — |
| 버튼 | 「이전」(→ IMG1), 주 버튼 「합성 이미지 4장 생성」(→ IMG3G) | run `kind='composite'`, 4장 고정 |

- 축척 계산(결정적): 기준 치수가 있으면 `mm_per_px = 입력 mm ÷ i2t 가 찾은 해당 물체(카운터·바닥선) 픽셀 길이(면 평면 원근 보정 후)`. 없으면 i2t 크기 힌트(문 높이 2,100 mm, 카운터 높이 1,050 mm 등 표준값, §10.4)로 추정하고 라벨에 「약」을 붙인다. 둘 다 없으면 「[00]」.
- 제품 실물 크기: KB 스펙 `dimensions`(가로×세로) → 없으면 `screen_size_inch` 와 16:9 + 베젤 비율로 계산하고 `estimated=true`.
- 배치 변경은 `PUT /v1/works/{id}/placements` 로 300ms 디바운스 저장(응답에 계산된 W·H 포함).
- 상태: 사진 0장이면 주 버튼 비활성. 어두운 사진만 있어도 생성은 허용하되 W 아래 **(신규)** 「사진이 어두워 합성 결과가 고르지 않을 수 있어요」.

### 4.6 IMG3G · 생성 중
- W: 「{N}장을 만들고 있어요. 제품 외형과 비율을 먼저 맞춘 뒤 장면을 그립니다. 완료되면 알려드릴 테니 다른 작업을 하셔도 됩니다.」 (변형·비율 run 이면 「{N}장」 대신 **(신규)** 「변형 {N}장」/「{k}개 비율」).
- 단계 표시(가로 4단계): 「제품 외형 맞춤」 → 「장면 구성」 → 「렌더링 {k} / {N}」 → 「품질 확인」. 각 단계 상태 `done | now | todo`(체크 / 시계 / 빈 원).
- 요약 줄: 「{제품 요약} · 참조 {r}장 반영」 (예 「QM55C ×3 · KM24C · 참조 2장 반영」; 참조 0이면 뒷부분 생략).

| 시안 카드 상태 | 표시 |
|---|---|
| 완료 | 이미지 + 「시안 {i} · 완료」 + 크게 보기 링크(aria 「크게 보기」 → IMG3) |
| 렌더링 중 | 미리보기(있을 때만, 흐림) + 「렌더링 중」 「{p}%」 + 「시안 {i}」 + 「이 장 취소」(호버) |
| 장면 구성 중 | 「장면 구성 중」 「{p}%」 + 「시안 {i}」 + 「이 장 취소」 |
| 대기 | 「대기 중」 「시안 {j}가 끝나면 시작해요」(j = 진행 중 시안 중 가장 먼저 시작한 것) + 「시안 {i}」 + 「이 장 취소」(호버) |
| 취소됨 | **(신규)** 「취소됨」 |
| 보류 | **(신규)** 「보류 · 대안 필요」(→ IMG3X) |

- 미리보기: composite run 은 결정적 합성 초안을 흐리게 보여 준다. 일반 생성은 제공자가 부분 이미지를 주지 않으면 미리보기 없이 스켈레톤(가짜 이미지 금지).
- 진행률: 시안별 `progress = min(0.95, 경과 ÷ 최근 지연 EMA)`(제공자·모델·종류별 EMA, 결과 도착 시 100). 이것은 추정치다.
- 머리: 「생성 중 · {done} / {N} 완료 · 3 / 3」, 토글 「완료되면 알림」(기본 켜짐 → `PATCH /v1/runs/{id} {notify}`), 「약 {m}분 남음」(60초 미만이면 「약 {s}초 남음」, 10초 단위).
- 「내 대기열 {q} 건」 「이 작업이 끝나면 순서대로 이어서 생성돼요」 — 내 대기 중 run 목록(번호, 제목, 메타 예 「B 병원 · 변형 4장」, 사전 검사 안내 링크 예 「1장은 생성 불가 · 안내 보기」 → 그 run 의 IMG3X, 순서 「다음 차례」/「{k}번째」, 「취소」). 0건이면 패널 숨김.
- 버튼: 「전체 취소 · 조건 수정」(run 취소 → IMG2, 조건 유지, 끝난 시안은 갤러리에 남김), 「목록에서 기다리기」(→ IMG0), 주 버튼 「완료된 {done}장 먼저 보기」(done ≥ 1 일 때만 활성 → IMG3, 나머지는 계속 진행).
- run 이 `queued`(내 다른 run 이 진행 중): 카드 전체 「대기 중」, 머리 **(신규)** 「대기 중 · 앞에 {k}건」.
- 실패(run 전체): **(신규)** W 「이미지를 만들지 못했어요. {사유}」 + 「다시 시도」(같은 조건 새 run) + 「조건 수정」(→ IMG2). 사유 예: 한도 초과 **(신규)** 「오늘 쓸 수 있는 이미지 생성 횟수를 다 썼어요」, 모델 오류 **(신규)** 「이미지 모델이 응답하지 않아요」.
- 완료되면: `notify=true` 면 jobs 완료 알림(**(신규)** 「{작업 제목} · {done}장 생성 완료」, 링크 = IMG3). 화면이 열려 있으면 IMG3 으로 자동 이동하지 않고 주 버튼을 **(신규)** 「결과 보기」로 바꾼다.

### 4.7 IMG3 · 생성 결과 (3/3)
- W: 「{n}장을 생성했습니다. 마음에 드는 이미지를 선택해 저장하거나, 한 장을 기준으로 변형을 더 만들 수 있습니다.」
- 2×2 시안 그리드: 선택된 시안에 「선택됨」 배지 + 굵은 테두리, 각 시안에 「확대」 「다운로드」(현재 버전 fhd PNG) 버튼, 라벨: 선택 시안 「시안 {i} · {비율} · {스타일 약칭}」(예 「시안 1 · 16:9 · 실사」; 약칭 실사/3D/일러스트), 그 외 「시안 {i}」. 품질 확인 실패 시안에 **(신규)** 「확인 필요」 배지(툴팁 = QC 사유).
- 기본 선택 = 시안 1(또는 `?image=`). 선택은 `work.selected_image_id` 에 저장.
- 작업 카드 머리 「시안 {i} 선택됨 · 3 / 3」.
- 칩: 「이 시안으로 변형 4장」(→ 변형 run 시작 + IMG3V), 「밝기 올리기」(동기 보정 → 새 버전, §7.6), 「사람 제거」(→ IMG3E, 사람 영역 자동 생성).
- 입력: 라벨 「수정 요청」, placeholder 「수정 요청 (예: 메뉴보드 화면에 실제 메뉴 이미지 넣어줘)」, 보내기(aria 「보내기」) → LLM 분류: 영역 지정형이면 IMG3E 로 영역을 만들어 이동, 전체 수정형이면 전체 편집 run(새 버전), 변형형이면 변형 run.
- 버튼: 「내 이미지에 저장」(→ `POST /v1/images/{id}:save`, 저장 후 IMG0), 주 버튼 「제안서에 넣기」(→ IMG4).
- 일부 시안 진행 중(「완료된 1장 먼저 보기」로 온 경우): 미완료 칸은 IMG3G 카드 상태를 그대로 보여 준다.

### 4.8 IMG3X · 생성 실패 · 제한 안내
- 메아리 예: 「공간 · 경쟁사 A 메뉴보드 옆에 QM55C, 배우 ○○○가 주문하는 장면 + 참조 사진」.
- W: 「{N}장 중 {g}장을 만들고 {h}장은 보류했어요. 요청에 그대로 만들 수 없는 부분이 {k}가지 있습니다. 항목마다 대안을 고르면 보류한 {h}장을 이어서 만듭니다.」
- 시안 줄: 완성 시안(「시안 1」…) + 보류 칸(「시안 {i} · 보류」). 요약 카드 「완성 {g}장」 「경쟁사 · 인물 요소 없이 만들었어요」(실제로 기본 대안으로 바꾼 요소만 나열), 링크 「완성본 보기」(→ IMG3).
- 머리 「보류 사유 {k}」 「· 대안 {a}개 선택됨」, 버튼 「생성 이미지 사용 기준」(팝오버, §10.6 내용).

| 사유 종류 | 제목(보드) | 상태 | 설명(보드) | 대안 칩(보드) | 기본/추천 |
|---|---|---|---|---|---|
| `product_unrecognized` | 「참조 사진 속 디스플레이를 알아보지 못했어요」 | 「대안 선택됨」 | 「사진 속 화면이 작고 멀어 베젤 · 두께를 알 수 없어요. 모델을 고르면 실제 외형으로 그립니다.」 + 「올린 참조 사진」 썸네일(인식 못 한 영역에 「?」) | `{후보1} · 가장 비슷`, `{후보2}`, `{후보3}`, 「제품 탐색에서 고르기」, 「외형만 참고」 (예: 「QM55C · 가장 비슷」 「QB55C」 「QH55C」) | 추천=후보1 |
| `competitor_brand` | 「{경쟁사명} 로고 · 제품은 이미지에 넣지 않아요」 (예 「경쟁사 A 로고 · 제품은 이미지에 넣지 않아요」) | 「대안 선택됨」 | 「다른 회사의 로고 · 상표 · 고유 디자인은 그리지 않아요. 비교가 목적이면 비교표 시트가 더 정확해요.」 + 링크 「Why Samsung 비교표로 보내기」 | 「로고 없는 일반 화면으로」, 「'{경쟁사명}' 글자 라벨만」 | 추천=첫째 |
| `real_person` | 「실존 인물({이름})은 그리지 않아요」 (예 「실존 인물(배우 ○○○)은 그리지 않아요」) | 「선택 필요」 | 「초상권 때문에 실제 인물의 얼굴 · 이름을 쓴 이미지는 만들지 않아요. 고르지 않으면 '인물 없이'로 만듭니다.」 | 「가상 인물로」 「뒷모습 · 손만」 「인물 없이 · 기본값」 | 기본=인물 없이 |

- 대안 칩은 `aria-pressed`. 고른 칩에 체크 아이콘. 사유 상태: 대안이 정해지면(자동 추천 포함) 「대안 선택됨」, 사용자가 꼭 골라야 하는 항목(가상 인물 등 창작 선택)은 「선택 필요」.
- 후보 모델: i2t 가 본 형태(visual_vocab 카테고리·크기 힌트) → KB `C2(category, text)` 상위 3. 「제품 탐색에서 고르기」 → 상단바 제품 탐색(고른 제품이 후보1 자리로). 「외형만 참고」 → 모델을 정하지 않고 사진 속 외형 묘사만 쓰며 결과 메타에 `product_identity='generic'`.
- 하단 머리 「대안 선택 · {k}개 중 {a}개 선택됨」. 칩 「모두 추천 대안으로」(모든 사유 = 추천/기본 대안), 「보류 {h}장 건너뛰기」(보류 시안 취소, run 완료).
- 입력: 라벨 「다른 대안 입력」, placeholder 「다른 방법 (예: 경쟁사 화면은 회색 박스로)」 → LLM 이 어느 사유에 대한 대안인지 판정해 그 사유의 `custom` 대안으로 저장(정책 재검사 통과 시에만).
- 버튼: 「조건 다시 입력」(→ IMG2, 보류 시안 취소), 주 버튼 「대안으로 {h}장 이어서 생성」(→ jobs 입력 → IMG3G).
- 「Why Samsung 비교표로 보내기」: 웹 이동만(제안서 Why Samsung CM 시트, `?focus=CM&competitor={경쟁사명}`). 서버 간 호출 없음.
- IMG3X 는 run 이 `awaiting_input` 일 때의 같은 라우트 상태다. 사전 검사에서 문제가 있었지만 모든 시안을 만든 경우(보류 0)는 IMG3 에 **(신규)** 안내 띠 「요청 중 {k}가지를 바꿔서 만들었어요 · 자세히」만 보인다.

### 4.9 IMG3E · 부분 수정
- 메아리 예: 「부분 수정 · 시안 1에서 가운데 메뉴보드 화면만 바꾸고 싶어요」 (진입 원인: 사용자의 수정 요청 문장, 없으면 **(신규)** 「부분 수정 · 시안 {i}」).
- W: 「바꿀 곳을 사각형이나 브러시로 지정하고 영역마다 지시문을 적어 주세요. 선택한 영역 밖은 그대로 둡니다.」 + (적용된 영역이 있으면) 「영역 {k}을 먼저 고쳤으니 가운데 손잡이를 끌어 전/후를 비교해 보세요.」

**도구 막대** (role group 「영역 선택 도구」)

| 도구 | 동작 | 모델 능력 |
|---|---|---|
| 「사각형」(기본) | 끌어서 사각 영역 | 항상 |
| 「브러시」 | 칠해서 자유 영역(마스크) | 항상 |
| 「객체 선택」 | 클릭한 물체의 bbox 를 영역으로(감지 결과 위에 호버 강조) | `I2T_SUPPORTS_BBOX=true` 일 때만. 아니면 비활성 + **(신규)** 툴팁 「지금 모델은 객체 인식을 지원하지 않아요」 |
| 「지우개」 | 선택 영역의 브러시 마스크를 지움 | 항상 |

- 「크기」: 「작게」 「보통」(기본) 「크게」 = 브러시 지름 12 / 24 / 48 px(화면 기준). 「실행 취소」 「다시 실행」 = 마스크 그리기 기록(클라이언트).
- 보기(role group 「보기」): 「편집」 / 「전/후 비교」. 비교: 손잡이(aria 「전/후 비교 손잡이」), 라벨 「전 · {이전 버전 라벨}」 「후 · {현재 버전 라벨}」(예 「전 · 원본」 「후 · 수정 1」).
- 「수정 기록」: 버전 썸네일 목록 — 「원본」, 「수정 {n} · 영역 {k}」 … 선택하면 그 버전을 미리 보고, 「되돌리기」로 그 버전을 현재로 만든다(버전은 지우지 않음).
- 도움말 「영역 밖 픽셀은 원본 유지」.
- 「수정 영역 · {n}」, 「모두 지우기」(적용 전 영역만 지움). 영역 카드:

| 필드 | 예(보드) |
|---|---|
| 번호 | 1 |
| 영역 이름 | 「가운데 메뉴보드 화면」 (i2t 가 영역 크롭을 보고 “위치어 + 명사” 12자 이내로 이름, 실패 시 「영역 {n}」) |
| 지시문 | 「계절 음료 사진 3장으로 바꾸고 글자는 빼줘」 |
| 상태·동작 | 「적용됨 · 비교 중」 + 「되돌리기」 / 「대기 · 적용 전」 + 「적용」 / **(신규)** 「적용 중」 / **(신규)** 「실패 · 다시 적용」 |

- 「영역 추가」(새 빈 영역, 도구는 사각형).
- 「제품 외형 고정」 스위치(기본 켜짐) + 「{제품 약칭} 외형 · 비율은 바뀌지 않아요」 (예 「QM55C 외형 · 비율은 바뀌지 않아요」). 제품이 없는 시안이면 숨김.
- 하단 머리 「영역 {k} 지시문 · 부분 수정」. 칩 「글자 지우기」 「사람 지우기」 「제품 화면에 콘텐츠 넣기」 「주변과 밝기 맞추기」.

| 칩 | 동작 |
|---|---|
| 글자 지우기 | i2t bbox(`text`) → 영역 자동 생성 + 지시문 **(신규)** 「글자를 지우고 주변과 자연스럽게 채워줘」. bbox 미지원이면 전체 편집 지시로 바꾸고 **(신규)** 「자동 영역 인식이 없어 전체 이미지에 적용해요」 |
| 사람 지우기 | i2t bbox(`person`) → 영역 + 지시문 **(신규)** 「사람을 지우고 배경을 자연스럽게 채워줘」(미지원 시 위와 같음) |
| 제품 화면에 콘텐츠 넣기 | i2t bbox(`screen`) 또는 생성 메타의 제품 박스 → 화면 영역 + LLM 이 장면에 맞는 콘텐츠 문장 제안 |
| 주변과 밝기 맞추기 | 선택 영역 결과에 결정적 보정(링 영역 평균·표준편차 맞춤). 모델 호출 없음 |

- 입력: 라벨 「선택한 영역 수정 지시」, placeholder 「영역을 어떻게 바꿀까요? (예: 시즌 메뉴 사진 넣기)」, 보내기 = 선택 영역의 지시문 저장 + 「적용」.
- 버튼: 「결과로 돌아가기」(→ IMG3), 주 버튼 「저장하고 내보내기」(현재 버전 저장 → IMG4).
- 적용은 영역마다 run(`kind='edit'`) — 화면에 머무르며 영역 카드에 진행 표시. 여러 영역을 한 번에 「적용」하면 번호 순서로 순차 적용하고 영역마다 새 버전.

### 4.10 IMG3V · 변형 · 비율 · 해상도
- 메아리 예: 「변형 · 시안 1로 변형을 더 보고, 세로형 사이니지용 버전도 필요해요」.
- W: 「시안 {i}을 기준으로 변형 {n}장을 만들었습니다. 제품 배치는 그대로 두고 시간대 · 조명 · 시점을 조금씩 달리했어요. 고른 변형은 원하는 비율과 해상도로 다시 만들 수 있습니다.」 (변형 생성 중이면 **(신규)** 「시안 {i}을 기준으로 변형 {n}장을 만들고 있어요.」)
- 변형 영역 머리 「변형 {n}장」 「· 기준 시안 {i} · 제품 배치 유지」, 링크 「부분 수정」(→ IMG3E, 선택 변형), 「이 변형 바로 내보내기」(→ IMG4).
- 변형 카드 4장: 라벨 「{A~D} · {변형 이름}」(LLM 이 정한 8자 이내 이름, 예 「A · 오후 자연광」 「B · 저녁 조명」 「C · 측면 시점」 「D · 메뉴보드 근접」), 선택은 단일(aria 「변형 {X} 선택됨」/「변형 {X}」). 생성 중 카드는 IMG3G 카드 상태 표시.
- 「비율 · 해상도」 「· 여러 비율을 한 번에 만들 수 있어요」, 머리 오른쪽 「변형 {X} 기준 · {k}개 선택」.

| 비율 카드(다중 선택) | 해상도(업스케일별, §10.2) | 용도(보드) |
|---|---|---|
| 16:9 (+기준 비율이면 「원본 비율」 배지) | 원본 1920×1080 · ×2 3840×2160 · ×4 7680×4320 | 「슬라이드 · 표지」 |
| 4:3 | 1440×1080 · 2880×2160 · 5760×4320 | 「4:3 제안서 템플릿」 |
| 1:1 | 1080×1080 · 2160×2160 · 4320×4320 | 「SNS · 썸네일」 |
| 9:16 | 1080×1920 · 2160×3840 · 4320×7680 | 「세로형 사이니지 · 모바일」 |

- 기준과 다른 비율 카드에는 새로 그릴 쪽 안내 「{위쪽|아래쪽|양옆|위아래}은 새로 채움」(예 「위쪽은 새로 채움」) — 「잘라내기」를 고르면 안내 대신 **(신규)** 「일부를 잘라요」.
- 「비율 맞추는 방법」(role group): 「다시 구성」(기본) 「잘라내기」 「바깥 채우기」. 「업스케일」: 「원본」 「×2」(기본) 「×4」. 고정 표시 「제품 외형은 고정」.
- 능력에 따른 비활성(툴팁 **(신규)**): 「다시 구성」 — 참조·편집 모두 미지원 시 「지금 모델로는 다시 구성할 수 없어요」; 「바깥 채우기」 — 편집 미지원 시 「지금 모델로는 바깥 채우기를 할 수 없어요」; 「×4」 — 업스케일 모델 미설치 시 「×4는 업스케일 모델이 있어야 해요」.
- 하단 머리 「변형 {X} 선택됨」 「· {비율 목록 ' + '} · {업스케일} 업스케일」 (예 「· 16:9 + 9:16 · ×2 업스케일」; 원본이면 **(신규)** 「· 업스케일 없음」).
- 칩: 「변형 4장 더」(같은 기준으로 변형 run, 새 변형은 E~H), 「조명만 바꾸기」(조명 축만 바꾼 변형 4장), 「손님 넣기」(사람 추가 변형 — 정책상 가상 인물).
- 입력: 라벨 「변형 요청」, placeholder 「요청 (예: 세로 버전은 메뉴보드를 위쪽에)」 → LLM: 비율별 구도 지시(예 9:16 제품 위치=위)로 저장하거나 새 변형 지시로 사용.
- 버튼: 「결과로 돌아가기」(→ IMG3), 주 버튼 「{k}개 비율로 만들기」(→ `POST /v1/images/{id}/renditions` → IMG3G). k=0 이면 비활성.

### 4.11 IMG4 · 내보내기 · 제안서에 넣기
- W: 「{시안 라벨} {수정본|''}을 내보냅니다. 파일로 받거나, 진행 중인 제안서의 이미지 자리에 바로 넣을 수 있어요. 넣을 시트는 장면에 맞춰 추천해 두었습니다.」 (예 「시안 1 수정본을 내보냅니다. …」)
- 미리보기 카드: 제목 「{시안 라벨} · {버전 라벨}」(예 「시안 1 · 부분 수정본 v2」; 버전 라벨 규칙 §5.3), 메타 「{비율} · {해상도}」 「· {스타일 이름} · {저장 시각}」(예 「16:9 · 3840×2160 · 실사 렌더 · 방금 저장」). 링크 「다른 시안 고르기」(→ IMG3), 「비율 · 해상도 바꾸기」(→ IMG3V).

**파일로 받기**
| 컨트롤 | 값 |
|---|---|
| 형식(radiogroup 「파일 형식」) | 「PNG」 「원본 화질」(기본), 「JPG」 「용량 작게」, 「PDF」 「인쇄 · 검토용」, 「PPTX」 「슬라이드 1장」 |
| 「해상도」(group) | 「1920×1080」 / 「3840×2160」(기본; 비율이 다르면 그 비율의 fhd / uhd 크기) |
| 체크 | 「AI 생성 이미지 표기 넣기」(기본 체크), 「수정 전 원본도 함께」(기본 해제) |
| 「파일명」 | 기본 `{고객사 약칭 공백 제거}_{subject_short}_{시안 라벨 공백 제거}_v{n}.{ext}` (예 「A커피_메뉴보드_시안1_v2.png」) — 형식을 바꾸면 확장자만 바뀜 |
| 버튼 | 「{FORMAT} 다운로드」 (예 「PNG 다운로드」) |

- PNG·JPG: 이미지 서비스가 바로 만든다(필요한 해상도 렌디션이 없으면 만들고 내려줌). 「수정 전 원본도 함께」면 ZIP(export). PDF·PPTX: export 서비스 job(202) → 완료 후 다운로드.
- AI 표기: 이미지 오른쪽 아래(가장자리 여백 = 짧은 변의 2%)에 「AI 생성 이미지」 글자(높이 = 짧은 변의 1.6%, 흰 글자 + 50% 검정 그림자)를 굽고, 체크와 무관하게 메타데이터(§7.7)는 항상 넣는다.

**제안서에 넣기**
- 링크 「새 제안서로 시작」(→ 제안서 PR1, 이 이미지 버전을 시작 자료로 전달).
- 「넣을 제안서」(radiogroup): 진행 중 제안서 목록 — 제목 + 메타(예 「A 커피 프랜차이즈 메뉴보드 제안」 「표준 제안서 · 작성 중」, 「B 병원 안내 시스템 제안」 「표준 제안서 · 검토 중」). 기본 선택 = 같은 프로젝트의 가장 최근 제안서.
- 「넣을 시트」 「· 이미지를 받는 시트만 보여요」(radiogroup): 시트 이름 + 섹션(예 「카운터 · 메뉴보드」 「공간별 제품 · 같은 공간 장면」 + 「추천」 배지, 「가치 제안」 「Value Props」, 「공간 전경」 「조감도」, 「사례 · 커피 프랜차이즈」 「유관 사례」). 선택 시트 미리보기: 시트 썸네일, 「{시트 이름}」, 「이미지 자리 {n}곳 · 교체 미리보기」.
- 「넣는 방식」(group): 「이미지 자리 교체」(기본) / 「새 시트로 추가」, 안내 「위치 · 크기는 나중에 조정」.
- 시트 목록·추천은 제안서 서비스가 준다(§8). 이미지 서비스는 제안서를 호출하지 않는다 — 웹 모듈이 제안서 계약으로 직접 부른다.

**다른 작업에 쓰기** — 「공간 시나리오 장면으로」(→ SC4; 요청에서 온 작업이면 요청을 이 버전으로 충족), 「조감도 참조로」(→ BE1, 버전 id 전달), 「팀에 공유」(workspace 공유 링크). 상태 줄 「내 이미지에 저장됨」 + 「갤러리 보기」(→ IMG0). IMG4 에 들어오면 현재 버전을 자동으로 내 이미지에 저장한다.

- 하단 머리 「내보내기」 「· {제안서 짧은 이름} › {시트 이름}」 (예 「· A 커피 제안서 › 카운터 · 메뉴보드」). 칩 「다른 시안도 함께 넣기」(같은 작업의 다른 시안을 다중 선택해 같은 시트/새 시트로), 「캡션 자동 작성」(LLM 캡션 → 넣을 때 함께 전달, 생성 이미지 표기 포함), 「영문 파일명」(파일명 LLM 영문화, 예 `ACoffee_MenuBoard_Draft1_v2.png`).
- 입력: 라벨 「내보내기 요청」, placeholder 「요청 (예: 넣을 때 아래에 캡션도 달아줘)」 → 위 옵션들로 구조화.
- 버튼: 「결과로 돌아가기」(→ IMG3), 주 버튼 「제안서에 넣기」 → 제안서 가져오기 호출 → 성공 시 **(신규)** 토스트 「{제안서} › {시트}에 넣었어요 · 열기」.
- 상태: 진행 중 제안서 0건이면 목록 대신 **(신규)** 「진행 중인 제안서가 없어요」 + 「새 제안서로 시작」. 제안서 호출 실패 **(신규)** 「제안서에 넣지 못했어요 · 다시 시도」.

---

## 5. 데이터 모델 (`${DATA_DIR}/image/image.sqlite`)

### 5.1 표
```text
work            id TEXT PK 'imw_<ULID>' · owner TEXT · project_id TEXT? · customer_name TEXT? · customer_short TEXT?
                title TEXT · subject_short TEXT(≤ 6자, 파일명용 예 '메뉴보드') · kind TEXT(space|background|scenario|composite) · description TEXT(≤500)
                conditions JSON {products:[{family_id, model_code?, name, short, qty(1..9), source(prefill|user)}],
                                 style(photo|minimal_3d|illustration), aspect('16:9'|'4:3'|'1:1'), count(2|4)}
                composite JSON? {active_photo_id, groups:[PlacementGroup], ref_dims:{counter_width_mm?, install_height_mm?},
                                 options:{perspective_light_match:bool(true), screen_menu:bool(true)}}
                origin JSON? {service:'image'|'scenario'|'proposal'|'shell', ref?, request_id?}
                status TEXT(draft|queued|running|awaiting_input|done|failed|canceled) · route TEXT · selected_image_id TEXT?
                last_export JSON? {format, at} · version INTEGER · created_at · updated_at · deleted_at?
reference       id 'imr_' · work_id · order INT · source_kind(kb_asset|my_image|case_photo|upload|topbar)
                source_ref TEXT (kb asset id | imv_ | dep_… | file_id) · file_id · label · source_label · source_url?
                rights(official|customer_case|generated|unknown) · aspects JSON ['color_light'|'composition'|'placement'|'material']
                strength(low|mid|high) · analysis JSON? {faces:[bbox], logos:[bbox], style, palette:[hex×5], caption}
                sanitized_file_id? · send_mode(image|text_fallback)
site_photo      id 'imp_' · work_id · file_id · label · status(recognizing|recognized|low_light|failed)
                quality JSON {luma_mean, laplacian_var, clipped_ratio} · surfaces JSON [{label, kind(wall|counter|ceiling),
                quad:[[x,y]×4] (0..1), installable:bool}] · scale JSON {mm_per_px?, method(ref_dim|std_object|none)} · job_id
run             id 'ign_' · work_id · job_id · kind(initial|composite|alternatives|variants|edit|adjust|renditions|render_api)
                params JSON · status(queued|running|awaiting_input|succeeded|failed|canceled) · notify BOOL(true)
                stages JSON [{key, label, state}] · eta_s INT? · precheck JSON {issues:[PolicyIssue]} · error JSON?
                created_at · started_at? · finished_at?
image           id 'img_' · work_id · run_id · label ('시안 1' | 'A · 오후 자연광') · aspect · status(waiting|composing|
                rendering|qc|done|held|canceled|failed) · stage_label · progress REAL · base_image_id? · origin
                current_version_id · saved BOOL · hidden BOOL · created_at
image_version   id 'imv_' · image_id · n INT(1..) · parent_version_id? · op(generate|composite|edit_region|edit_global|
                adjust|variant|aspect|upscale) · op_params JSON · master_file_id (fhd) · native JSON {w,h,file_id}
                renditions JSON [{kind(native|fhd|uhd|uhd8k|thumb), w, h, file_id, method}]
                generation JSON (§5.2) · qc JSON {status(ok|check|skipped), checks:[…], products:[{bbox, kind}]}
                created_at
edit_region     id 'ire_' · image_id · base_version_id · n INT · shape(rect|brush|object) · rect JSON? (0..1)
                mask_file_id? · label · instruction · status(pending|applying|applied|reverted|failed)
                result_version_id? · protect_products BOOL
usage           image_id · version_id · service('proposal'|'scenario'|'birdseye') · ref · label · created_at
request         id 'irq_' · from_service · from_ref · from_label · title · prefill JSON {kind, description, products,
                aspect, style, space_label} · status(open|in_progress|fulfilled|dismissed) · work_id? · result_version_id?
                created_by · created_at
export          id 'ixp_' · version_id · format(png|jpg|pdf|pptx|zip) · resolution(fhd|uhd) · ai_label BOOL
                include_original BOOL · filename · file_id? · job_id? · created_at
```
`PlacementGroup = {id, family_id, qty, arrangement(row3|col3|separate|single), mount(wall|ceiling), quad:[[x,y]×4] (사진 좌표 0..1), gap_mm(10)}`

### 5.2 생성 메타데이터(`image_version.generation`) — 출처의 원천
```json
{ "is_generated": true, "rights": "generated", "caption_rule": "생성 이미지",
  "provider": "gemini", "model": "gemini-3.1-flash-lite-image", "call": "t2i.generate|t2i.edit|local",
  "prompt_ko": "…", "prompt_en": "…", "seed": null,
  "references": [{"reference_id": "imr_…", "source_kind": "kb_asset", "source_url": "https://…", "rights": "customer_case",
                  "send_mode": "image|text_fallback", "aspects": ["composition"], "strength": "mid"}],
  "products": [{"family_id": "fam_…", "name": "Smart Signage QM55C", "qty": 3, "ref_asset": "img_…", "identity": "model|generic"}],
  "policy": {"issues": ["competitor_brand"], "applied_options": {"competitor_brand": "로고 없는 일반 화면으로"}},
  "fallbacks": ["reference:text_fallback", "mask:crop_paste"],
  "upscale": {"from": [1024, 576], "to": [3840, 2160], "method": "lanczos3+unsharp | realesrgan_x4v3+lanczos3"},
  "confidential": false, "origin": {"service": "image", "work_id": "imw_…"}, "created_at": "…" }
```
상단바 이미지 정보(셸)용 `GET /v1/images/{id}/info` 는 이 값으로 행을 만든다: 「출처 페이지」=Winmate 작업 링크, 「원본」=`{native w×h} · PNG · {model} · 생성 {날짜}`, 「저장본」=`{렌디션 w×h} · 업스케일({method})`, 「수집」→ **(신규)** 「생성」, 「사용 조건」=**(신규)** 「“AI 생성 이미지” 표기 권장 · 대외 사용 범위 확인 필요」, 「사용 이력」=「Winmate 제안서 {n}건」. 참조 출처 URL 은 그대로 링크한다.

### 5.3 버전 라벨 규칙
- IMG3E 기록: n=1 「원본」, 이후 `op=edit_region` 「수정 {n-1} · 영역 {k}」, `edit_global` **(신규)** 「수정 {n-1} · 전체」, `adjust` **(신규)** 「보정 {n-1}」.
- IMG4 제목: n=1 이면 시안 라벨만, 그 외 `{시안 라벨} · {부분 수정본|수정본|보정본|{비율} 버전} v{n}` (예 「시안 1 · 부분 수정본 v2」).
- 비율 run 결과는 같은 시안의 새 버전이 아니라 **새 시안**(라벨 `{원 라벨} · {비율}`, `base_image_id` 연결)으로 만든다 — 비율이 다른 이미지가 한 시안의 버전으로 섞이지 않게.

### 5.4 작업 색인(workspace)
작업 생성·상태 변경 때마다 `PUT /api/workspace/v1/items/{work_id}` `{feature:'image', title, status:{code,label}, summary:'{메타}', route, project_id}`. `route` 규칙: draft(유형 단계) `/image/new?work=`, 조건 `/image/w/{id}/conditions`, composite 편집 `/image/w/{id}/composite`, run 진행/보류 `/image/w/{id}/run/{runId}`, 완료 `/image/w/{id}/result`, 마지막 동작이 내보내기 `/image/w/{id}/export/{imageId}`.

---

## 6. API 스케치 (`/v1`, 게이트웨이 `/api/image/v1`)
공통: 오류 `{"error":{"code","message","details"}}`, 목록 `?limit=&cursor=` → `{items,next_cursor}`, 시간 ISO 8601 UTC, 오래 걸리는 작업 `202 {"job_id","status":"queued","run_id"}`.

### 6.1 능력
| 메서드 · 경로 | 응답 |
|---|---|
| `GET /v1/capabilities` | `{t2i:{supports_reference_images, supports_edit, supports_mask, max_side_px, images_per_call, max_reference_images}, i2t:{supports_json, supports_bbox}, upscaler:'none'\|'realesrgan_x4v3', features:{object_select, mask_native, outpaint, recompose, upscale_4x, region_edit}}` — ai-tools `/v1/capabilities` 를 60초 캐시해 기능 플래그로 바꿔 준다. 웹은 이 값으로 컨트롤을 켜고 끈다. |

### 6.2 작업
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `GET /v1/works` | `q, sort(updated_desc), limit, cursor` | `{items:[{id,title,meta,time,status:{code,label,tone,icon},thumb_url,route}], next_cursor, totals:{works, images}}` |
| `POST /v1/works` | `{kind?, description?, project_id?, request_id?, start:'type'\|'references'\|'composite', reference_items?:[{source_kind, source_ref}]}` | 201 `Work` |
| `GET /v1/works/{id}` | — | `Work`(조건·참조·composite·최근 run 요약 포함) |
| `PATCH /v1/works/{id}` | `{kind?, description?, title?, conditions?, if_version}` | `Work` · 409 `VERSION_CONFLICT` |
| `POST /v1/works/{id}:prefill` | — (동기, 제한 10초) | `{title, subject_short, products:[…], search_query, industry_chips:[…], kind_suggestion?}` — 시간 초과면 A1 결과만 |
| `DELETE /v1/works/{id}` | — | 204 (소프트 삭제, 제안서에 쓰인 버전 파일은 유지) |

### 6.3 참조
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `GET /v1/reference-search` | `tab(kb\|mine\|cases), q, industry?, style(all\|photo\|illustration), work_id?, limit(8), cursor` | `{items:[{source_kind, source_ref, thumb_url, label, alt, source_label, source_url, rights, verified:bool}], total}` |
| `POST /v1/works/{id}/references` | `{source_kind, source_ref? , file_id?, aspects?, strength?}` | 201 `Reference` (분석은 비동기로 채움) · 422 `REFERENCE_LIMIT` |
| `PATCH /v1/works/{id}/references/{rid}` | `{aspects?, strength?, order?}` | `Reference` · 422 `STRENGTH_NOT_ALLOWED`(업로드 + 강) |
| `DELETE /v1/works/{id}/references/{rid}` | — | 204 |

### 6.4 현장 사진 합성
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `POST /v1/works/{id}/site-photos` | `{file_id}` | 202 `{job_id, photo_id}` (인식 job) |
| `GET /v1/works/{id}/site-photos` | — | `[SitePhoto]` |
| `POST /v1/works/{id}/site-photos/{pid}:recognize` | — | 202 |
| `PUT /v1/works/{id}/placements` | `{photo_id, groups:[PlacementGroup], ref_dims, options}` | 200 `{groups:[{id, width_mm?, bottom_mm?, estimated:bool}], scale}` |

### 6.5 생성 run · 대기열
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `POST /v1/works/{id}/runs` | `{kind:'initial'\|'composite'\|'alternatives', count?}` | 202 `{job_id, run_id, status:'queued', precheck:{issues}}` · 409 `RUN_IN_PROGRESS`(같은 작업의 initial·composite run 이 이미 진행·대기 중 — 편집·변형·비율 run 은 막지 않고 대기열에 넣음) |
| `GET /v1/runs/{run_id}` | — | `{status, stages, shots:[{image_id,label,state,stage_label,progress,eta_s,preview_url?}], done, total, eta_s, notify, issues?}` |
| `PATCH /v1/runs/{run_id}` | `{notify}` | 200 |
| `POST /v1/runs/{run_id}:cancel` | — | 202 (jobs 취소로 전달) |
| `POST /v1/runs/{run_id}/shots/{image_id}:cancel` | — | 200 (대기 시안은 즉시 취소, 진행 시안은 결과 폐기) |
| `POST /v1/runs/{run_id}/answers` | `{answers:[{issue_id, option?:string, custom_text?:string}], skip_held?:bool, all_recommended?:bool}` | 202 (jobs 입력으로 전달, 같은 thread 재개) |
| `GET /v1/queue` | `mine=true` | `{items:[{run_id, work_id, title, meta, position, state_label('다음 차례'\|'{k}번째'), note?, note_route?}]}` — jobs 목록(owner·service=image·queued) 기반 |

### 6.6 시안·버전·편집
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `GET /v1/images` | `owner=me`(= `mine=true`), `origin(image,scenario 기본)`, `kind?`, `customer?`, `aspect?`, `in_proposal?`, `q?`, `sort(created_desc)`, `limit`, `cursor` | `{items:[ImageTile], total, next_cursor}` — `ImageTile = {id, title, width, height, format, bytes, created_at, file_id, thumb_url, kind, aspect, customer_short, status, used_in_count, origin}`(셸 00 의 `내 생성 이미지` 탭 요청 필드 포함) |
| `GET /v1/images/{id}` | — | `Image` + `versions` 요약 |
| `GET /v1/images/{id}/info` | — | 상단바 정보 행(§5.2) |
| `POST /v1/images/{id}:save` | — | 200 |
| `GET /v1/images/{id}/versions` · `POST /v1/images/{id}/versions/{n}/restore` | — | 버전 목록 / 새 현재 버전 |
| `POST /v1/images/{id}/detections` | `{kinds:['object','text','person','screen']}` | 200(캐시) 또는 202 · 422 `CAPABILITY_UNSUPPORTED`(bbox 미지원) |
| `POST /v1/images/{id}/regions` · `PATCH …/regions/{rid}` · `DELETE …` | `{shape, rect?\|mask_file_id?\|detection_id?, instruction?}` | `EditRegion` |
| `POST /v1/images/{id}/edits` | `{base_version_id, region_ids?:[…], mode:'region'\|'global', instruction?, protect_products:bool}` | 202 `{job_id, run_id}` |
| `POST /v1/images/{id}/regions/{rid}:revert` | — | 200 `{current_version_id}` |
| `POST /v1/images/{id}/adjust` | `{base_version_id, brightness?:-0.3..0.3, harmonize_region_id?}` | 200 새 버전(동기, 로컬) |
| `POST /v1/images/{id}/variants` | `{count:4, axis?:'any'\|'lighting'\|'people', instruction?}` | 202 |
| `POST /v1/images/{id}/renditions` | `{aspects:['16:9','9:16'], fit:'recompose'\|'crop'\|'outpaint', upscale:'1x'\|'2x'\|'4x', instructions?:{'9:16':'…'}}` | 202 · 422 `CAPABILITY_UNSUPPORTED` |
| `POST /v1/images/{id}/usages` · `DELETE …/usages/{service}/{ref}` | `{version_id, service, ref, label}` | 201 / 204 — 제안서·시나리오·조감도가 호출 |

### 6.7 내보내기
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `POST /v1/images/{id}/exports` | `{version_id, format:'png'\|'jpg'\|'pdf'\|'pptx', resolution:'fhd'\|'uhd', ai_label:bool, include_original:bool, filename}` | png/jpg 단일: 200 `{file_id, download_url}` · 그 외: 202 `{job_id, export_id}` |
| `POST /v1/images:bulk-export` | `{version_ids:[…], format:'png', ai_label}` | 202 (ZIP) |
| `GET /v1/exports/{id}` | — | `{status, file_id?, download_url?}` |

### 6.8 다른 기능의 요청
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `POST /v1/requests` (서비스 간) | `{from_service, from_ref, from_label, title, prefill}` | 201 `Request` |
| `GET /v1/requests` | `status=open,in_progress` 또는 `from_service&from_ref` | `{items}` |
| `POST /v1/requests/{id}:start` | — | `{work_id, route}` |
| `POST /v1/requests/{id}:fulfill` | `{version_id}` | 200 — 요청자는 `GET /v1/requests/{id}` 로 결과를 읽는다(이미지 서비스는 요청자를 호출하지 않음) |
| `POST /v1/requests/{id}:dismiss` | — | 200 |

### 6.9 렌더 API (birdseye·scenario 전용, 화면 없음)
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `POST /v1/renders` | `{origin:{service, ref}, project_id?, kind:'birdseye'\|'scene'\|…, prompt:{subject_ko, details_ko[], negatives[]}, aspect, target:'fhd'\|'uhd', structure_ref_file_id?, edit_of?:{file_id, instruction}, reference_file_ids?:[], product_refs?:[{family_id, qty}], expect?:{products:[{family_id, qty, bbox_hint?}]}, forbid?:['competitor_logo','real_person_face','gibberish_text'], allow_people:'none'\|'silhouette'\|'generic', confidential:bool, label?}` | 202 `{job_id, render_id}` |
| `GET /v1/renders/{id}` | — | `{status, image_id?, version_id?, renditions, generation, qc, error?}` |
| `POST /v1/renders/{id}:cancel` | — | 202 |

렌더 결과는 `image`·`image_version` 으로 저장되고 `origin.service` 가 요청 서비스다(IMG0 기본 갤러리에는 `birdseye` 출처가 보이지 않음).

### 6.10 SSE 이벤트(jobs)
`GET /api/jobs/v1/jobs/{job_id}/events` 의 `data` 형태:
- `step`: `{stage:'product_fit'|'compose'|'render'|'qc'|'postprocess', label:'렌더링 2 / 4', shot:{image_id, state, progress, eta_s, preview_file_id?}}`
- `progress`: `{pct, done, total, eta_s}` · `awaiting_input`: `{issues:[PolicyIssue], held:[image_id]}` · `result`: `{run_id, image_ids:[…]}` · `error`: `{code, message}`

---

## 7. 워크플로 (LangGraph · 워커 `wm:q:image`)

### 7.1 공통
- 체크포인터: SQLite(`checkpoints.sqlite`), `thread_id = job_id`. 노드 경계마다 `wm:job:<id>:cancel` 확인, 시안 단위 취소는 `image.status='canceled'` 확인(시안 시작 전·결과 저장 전).
- 동시성: 워커 전체 `IMAGE_WORKER_CONCURRENCY=2` job, 사용자당 진행 run `IMAGE_MAX_RUNNING_PER_USER=1`(나머지는 queued — “내 대기열”), run 안 시안 동시 `IMAGE_SHOT_CONCURRENCY=2`. `T2I_IMAGES_PER_CALL=1` 이라 시안 1장 = 호출 1회.
- 모든 ai-tools 호출: 고객 자료(업로드 사진·현장 사진·고객 사례 사진을 보낼 때, 프로젝트 고객 정보가 들어간 프롬프트)는 `confidential:true`. ai-tools 가 `POLICY_CONFIDENTIAL` 로 막으면 §7.2 의 로컬 대체 경로로 내려간다.
- 일시 오류 재시도 2회(2초, 6초). `QUOTA_EXCEEDED` 는 재시도하지 않고 run 을 `failed`(사유 표시)로 끝낸다(끝난 시안은 보존).

### 7.2 모델 능력별 경로(네이티브 vs 대체)
| 기능 | 네이티브(조건) | 대체 경로 | 결과 메타 `fallbacks` |
|---|---|---|---|
| 기본 생성 4장 | `t2i.generate` × N(참조 지원 시 제품 단독컷·참조 이미지 첨부) | 참조 미지원: 제품 외형(스펙 비율·베젤·색) + 참조의 요소별 i2t 묘사 + 로컬 팔레트(k-means 5색 hex)를 프롬프트 글로 | `reference:text_fallback` |
| 참조 강도 약/중/강 | 참조 이미지 + 역할 지시문(약 “loosely inspired by”, 중 “follow”, 강 “closely match”) + 따를 요소만 명시 | 위 텍스트 대체(강도는 형용 강도로) | 〃 |
| 참조 속 얼굴·로고 | bbox 지원: 해당 영역 가우시안 블러(σ=짧은 변 3%) 후 전송 | bbox 미지원: 그 참조는 이미지로 보내지 않고 텍스트 대체 | `reference:sanitize_text` |
| 현장 사진 합성 | 결정적 합성(원근 워프) → `t2i.edit`(원근·조명 맞춤, 기하 유지 지시) | 편집 미지원·기밀 차단: 로컬 조화(색 전달 + 접촉 그림자 + 화면 반사 그라데이션)만 | `composite:local_only` |
| 화면에 메뉴 넣기 | edit 지시에 메뉴 콘텐츠 포함 | 번들 메뉴 템플릿 이미지(로고 없음)를 화면 쿼드에 워프 | `screen:template` |
| 부분 수정(영역) | `T2I_SUPPORTS_MASK=true`: `t2i.edit(전체, mask)` | **현재 기본**: crop → `t2i.edit` → 원래 크기로 → 페더 마스크로 붙이기 | `mask:crop_paste` |
| 영역 수정, 편집 미지원 | — | 글자·사람 지우기 등 작은 영역(면적 ≤ 2%): OpenCV Telea 인페인트. 그 외 영역 수정 비활성 | `edit:opencv_inpaint` |
| 객체 선택 | `I2T_SUPPORTS_BBOX=true`: i2t bbox(객체·글자·사람·화면) | 도구 비활성, 칩은 전체 편집 지시로 | — |
| 제품 외형 고정 | 제품 bbox(생성 QC 또는 i2t) 기준으로 마스크에서 제품 테두리 띠 제외 | bbox 없음: 지시문만 + 결과 메타에 `product_lock:'instruction_only'` | `lock:instruction_only` |
| 변형 4장 | `t2i.edit(기준, 변형 지시)` | 편집 미지원+참조 지원: `t2i.generate(ref=기준)` / 둘 다 미지원: 원래 프롬프트 + 변형 지시(배치 유지 보장 안 됨 → **(신규)** 카드 표시 「배치가 조금 달라질 수 있어요」) | `variant:ref\|text` |
| 비율 · 잘라내기 | 로컬(제품 bbox 를 최대한 담는 창) | — | — |
| 비율 · 바깥 채우기 | 캔버스 확장(빈 곳 = 가장자리 미러 + 블러 힌트) → `t2i.edit("빈 곳만 자연스럽게 확장")` → 원래 영역은 원본 픽셀로 다시 덮기 | 편집 미지원: 비활성 | — |
| 비율 · 다시 구성 | `t2i.generate(ref=기준, 목표 비율)` + 제품 외형 고정 지시 | 참조 미지원+편집 지원: 바깥 채우기 경로 / 둘 다 미지원: 비활성 | `recompose:outpaint` |
| 업스케일 ×2/×4 | `UPSCALER=realesrgan_x4v3`(ONNX, CPU 또는 2GB GPU 타일 256) → 목표 크기로 Lanczos | 업스케일 모델 없음: Lanczos3 + 약한 언샤프(×4 비활성) | `upscale:lanczos` |
| 품질 확인 | i2t JSON(+bbox): 제품 수·비율, 로고·상표 글자, 식별 가능한 얼굴, 깨진 글자 | i2t JSON 실패: QC `skipped` + 시안에 「확인 필요」 | `qc:skipped` |
| 정책 사전 검사 | LLM JSON 분류 + 경쟁사 사전(`config/content_policy.yaml`) + i2t 참조 분석 | LLM 실패: 사전·정규식만(사람 이름 판정 없음 → 시나리오·공간 유형은 인물 기본값 '가상 인물'로 강제) | `policy:rules_only` |

### 7.3 그래프 `image.generate` (run kind: initial · composite · alternatives)
```text
START → load_context → policy_check ─┬─ "선택 필요" 이슈 없음 ─────────┐
                                     └─ "선택 필요" 이슈 있음 → split_shots ─┤ (지금 만들 시안 = N − floor(N/2), 나머지 held)
                                                                    ↓
        product_fit("제품 외형 맞춤") → compose("장면 구성") → render("렌더링 k / N", 시안 fan-out ≤2)
        → quality_check("품질 확인") ─(실패 & 재시도 < 1)→ render(그 시안만)
        → postprocess → held 있음? ─ 예 → await_alternatives [interrupt: awaiting_input] → apply_answers → product_fit(held 시안)
                                    └ 아니오 → finalize → END
```
| 노드 | 하는 일 | 호출 |
|---|---|---|
| `load_context` | 작업·조건·참조·composite 로드, 능력 플래그, 제품 사실(스펙 치수·카테고리·형태 어휘), 프로젝트 고객·업종 | kb `entity(family)`(스펙 `dimensions`·`screen_size_inch`), workspace 프로젝트 |
| `policy_check` | (1) 설명·지시문 분류 `{competitors[], real_persons[], unsafe[]}` (2) 참조 분석 `{faces[], logos[], displays[{bbox?, visual_category, size_hint}], style, caption}` → 블러/텍스트 대체 (3) 참조 속 디스플레이 제품 매칭(top1 신뢰도 < 0.6 → `product_unrecognized`, 후보 3) (4) 이슈별 추천/기본 대안과 상태 — 자동 해결(「대안 선택됨」): `competitor_brand`, `product_unrecognized`(후보1 점수 ≥ 0.4) / 선택 필요(「선택 필요」): `real_person`, `product_unrecognized`(후보 없음·점수 < 0.4) | ai-tools `llm.json`, `i2t.analyze(json, bbox?)`, kb `C2` |
| `split_shots` | held = 끝 번호부터 `floor(N/2)`장. 지금 만들 시안은 모든 이슈에 추천/기본 대안 적용 | — |
| `product_fit` | 제품별 참조 단독컷 선택(kb `G4`, 정면 C등급 우선), 예상 화면비(가로/세로), 외형 문장. 참조 예산 배정(§10.3) | kb `G4` |
| `compose` | LLM 이 시안별 구도 지시 N개를 겹치지 않게 작성(카메라 높이·각도·시간대 차이), 최종 프롬프트(영문)와 한국어 요약. composite: 시안별 결정적 합성 초안 생성 | ai-tools `llm.json` |
| `render` | 시안별 `t2i.generate`/`t2i.edit` 1회. 진행 이벤트, 제공자 거절은 그 시안 `failed`(사유 `provider_refused`) | ai-tools `t2i.*` |
| `quality_check` | 시안별 i2t JSON: 제품 개수(기대 qty), 제품 박스 비율(기대 ±15%), 경쟁사 로고·상표 글자, 식별 가능 얼굴(시나리오의 가상 인물은 허용, 실존 인물 사유가 있었다면 불허), 깨진 글자. 실패 1회 → 교정 지시 붙여 재생성 | ai-tools `i2t.analyze` |
| `postprocess` | 비율 정규화(±2% 이내면 중앙 크롭), fhd 마스터 + thumb(320) 렌디션, 메타데이터 삽입(§7.7), 버전 1 「원본」 저장, 작업 색인 갱신 | files 업로드 |
| `await_alternatives` | `awaiting_input {issues, held}` 이벤트 후 정지. 입력: `answers`, `skip_held`, `all_recommended` | jobs interrupt |
| `apply_answers` | 대안 반영(정책 재검사 통과 시) → held 시안을 waiting 으로 | `llm.json`(custom 대안 판정) |
| `finalize` | run 상태, 작업 상태, `notify` 면 jobs 완료 알림 요청, 요청 기반 작업이면 요청 `in_progress` 유지 | jobs, workspace |

진행 단계 가중치(머리 `{pct}`): 제품 외형 맞춤 10 · 장면 구성 10 · 렌더링 65 · 품질 확인 10 · 후처리 5.

### 7.4 그래프 `image.edit` (부분·전체 수정)
```text
load → (region 마다 번호 순) build_mask → protect_products → (native mask? → t2i.edit(full, mask))
                                                          | (crop_paste: crop_expand → t2i.edit(crop) → resize_back)
     → paste_feather → seam_harmonize → verify_outside → save_version → renditions → END
```
- `build_mask`: 사각형 = 사각 마스크, 브러시 = 업로드된 마스크 PNG, 객체 = 감지 bbox.
- `protect_products`(스위치 켜짐): 제품 박스 중 디스플레이는 “바깥 박스 − 화면 박스(안쪽으로 3% 들인 박스)” 테두리 띠를 마스크에서 뺀다. 지시가 화면 콘텐츠를 겨냥하면 화면 박스만 허용. 그 밖의 제품은 박스 전체를 뺀다.
- `crop_expand`: 마스크 bbox 를 `max(64px, bbox 짧은 변의 25%)` 만큼 넓히고, T2I 가 받는 비율(1:1, 4:3, 3:4, 16:9, 9:16, 3:2, 2:3) 중 가장 가까운 비율로 넓혀(줄이지 않음) 이미지 안으로 맞춘다. 크롭 긴 변이 1024 를 넘으면 1024 로 줄여 보내고, 512 미만이면 512 로 키워 보낸다.
- 지시문(영문 변환): `"{instruction}. Change only the {region_label}. Keep camera, lighting, and everything else identical."`
- `paste_feather`: 알파 = 마스크를 `FEATHER_PX=8`(fhd 기준) 가우시안 페더. `seam_harmonize`: 마스크 바깥 16px 링과 안쪽 16px 링의 평균·표준편차를 맞추는 보정(안쪽만 바꿈).
- `verify_outside`: (마스크 ⊕ 8px) 바깥 픽셀이 기준 버전과 **바이트 단위로 같아야** 한다. 다르면 오류(버그)로 간주하고 run 실패.
- 전체 수정(`mode=global`): `t2i.edit(전체, 지시)`(편집 미지원이면 비활성). 제품 외형 고정이 켜져 있으면 결과의 제품 박스 IoU(기준 대비) ≥ 0.8 확인, 미달이면 1회 재시도 후 「확인 필요」.

### 7.5 그래프 `image.variants` · `image.renditions`
- `variants`: `load_base → plan_axes(llm.json: 4개 {label≤8자, instruction}, 축 = 시간대·조명·시점·근접 중 겹치지 않게; '조명만 바꾸기'면 조명 축만, '손님 넣기'면 가상 인물 추가) → render(edit|ref|text) ×4 → qc(제품 박스 IoU vs 기준 ≥ 0.5 → '제품 배치 유지') → postprocess`.
- `renditions`: 비율마다 `fit` 경로(§7.2) → `qc(제품 비율 ±15%, 바깥 채우기면 원래 영역 일치)` → `upscale(목표 렌디션)` → 새 시안 저장. 기준과 같은 비율은 업스케일만.

### 7.6 동기 로컬 보정 `adjust`
「밝기 올리기」 = 감마 0.9 + 노출 +8%(하이라이트 보호: 상위 1% 휘도는 압축) → 새 버전(`op=adjust`). 「주변과 밝기 맞추기」 = §7.4 seam_harmonize 와 같은 계산을 선택 영역 결과에만. 모델 호출 없음, 200 응답.

### 7.7 메타데이터·AI 표기 삽입(모든 렌디션·내보내기)
- PNG: iTXt `winmate:generated=true`, `winmate:version_id`, `winmate:model`, `winmate:sources`(참조 URL 목록 JSON). JPEG/PNG 공통 XMP `Iptc4xmpExt:DigitalSourceType = http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia`, `dc:source`=작업 경로.
- 「AI 생성 이미지 표기 넣기」가 켜진 내보내기만 픽셀에 글자를 굽는다(§4.11). PDF·PPTX 는 이미지 아래 캡션 「AI 생성 이미지」를 export 템플릿이 넣는다.

### 7.8 그래프 `image.recognize_photo` (현장 사진)
`quality(휘도 평균, 라플라시안 분산, 포화 비율) → i2t.analyze(confidential:true, json+bbox?: surfaces[{label, kind, quad|bbox}], objects[{label('counter'|'door'|…), bbox}], floor_line?) → status → default_placement(조건의 제품, 배열 기본: qty=3 → 가로 3연, 면 중앙, 바닥에서 표준 설치 높이)`. bbox 미지원: 면은 '사진 전체 중앙 60%'로 두고 상태는 「벽면 인식 완료」 대신 **(신규)** 「면을 직접 맞춰 주세요」.

### 7.9 렌더 API 그래프 `image.render`
`load → policy_check(텍스트만) → product_fit → render(structure_ref 가 있으면 참조 1순위로 '이 구도·배치를 정확히 따름' 지시; 참조 미지원이면 edit_of=structure_ref 로 t2i.edit; 둘 다 없으면 텍스트) → quality_check(expect·forbid) → postprocess(target 렌디션까지) → END`. 호출 서비스의 job 은 이 job 의 SSE 를 따라가며 자기 단계로 보여 준다.

---

## 8. 다른 서비스 의존

| 서비스 | 쓰는 것 | 비고 |
|---|---|---|
| ai-tools | `llm.json`(분류·프롬프트·라벨·캡션), `i2t.analyze`(json, bbox), `t2i.generate`, `t2i.edit`, `GET /v1/capabilities` | 계약에 capabilities 가 없으면 `docs/requests/ai-tools.md` 로 요청(플래그: §7.2) |
| kb | `A1`(설명 → 제품·공간·카테고리), `entity`·스펙(`dimensions`, `screen_size_inch`), `G4`(제품 단독컷), `G1`/`G2`/`image_search`(사내 자산), `D1`+`G5`(유관 사례 사진), `C2`(인식 못 한 디스플레이 후보) | 경로는 `contracts/kb.json` 을 따른다. 결과의 `source_url`·`rights`·`caption_rule` 을 참조 메타에 그대로 저장 |
| files | 업로드(JPG·PNG·HEIC 변환), 렌디션·마스크·초안 저장, 썸네일 | 바이너리는 files 만 저장 |
| jobs | 잡 생성·SSE·취소·입력(interrupt)·완료 알림·owner/service/status 목록과 대기 순번 | 목록 순번(`position`)이 없으면 `docs/requests/jobs.md` 로 요청 |
| workspace | 작업 색인(§5.4), 프로젝트 고객·업종, 「팀에 공유」 링크 | — |
| export | PDF·PPTX(이미지 1장 템플릿)·ZIP(메타데이터 `sources.json` 포함) | — |
| proposal(웹에서만) | 웹 모듈이 제안서 계약으로 직접 호출: 진행 중 제안서 목록, `GET /proposals/{id}/image-slots?image_version=` (시트·추천·미리보기), `POST /proposals/{id}/imports {source:{service:'image', version_id}, target:{sheet_id, mode:'replace_slot'\|'new_sheet'}, caption?}` | 제안서가 이미지 서비스를 consume 하므로 제안서가 버전을 읽고 `POST /v1/images/{id}/usages` 로 사용을 등록. 슬롯·가져오기 API 가 없으면 `docs/requests/proposal.md` |
| scenario·birdseye(호출자) | 렌더 API(§6.9), 요청(§6.8), 사용 등록 | 이미지 서비스는 그들을 호출하지 않는다 |
| 셸(workspace 소유) | 상단 이미지 검색의 「내 생성 이미지」 탭 = `GET /v1/images?owner=me`(00-shell 이 `docs/requests/image.md` 로 요청한 형태), 정보 = `/info`, 셸 맥락 `accepts`(`product`·`image`)·드래그 데이터 `{type, ref, label, sub}`(00-shell §5.7) | — |

---

## 9. 수용 기준
모델 호출은 모두 결정적 목(mock)으로 대체한다: `llm.json` 은 고정 JSON, `i2t.analyze` 는 픽스처 JSON(필요 시 bbox), `t2i.*` 는 입력 크기에 맞춘 단색·패턴 PNG(호출 인자 기록), `kb` 는 픽스처 응답. 시간은 고정 시계.

**IMG1 · IMG2**
1. Given 새 작업, When IMG1 을 열면, Then 「공간」 카드가 선택돼 있고 textarea placeholder 가 「예) 카페 카운터 위에 3연 메뉴보드가 걸린 장면, 낮 시간, 손님 2~3명」이며, 설명이 비어 있는 동안 「상세 조건 입력」은 비활성이다.
2. Given 설명 「카페 카운터 위에 3연 메뉴보드가 걸린 장면, 낮 시간, 손님 2~3명」과 A1 픽스처(QM55C)·LLM 픽스처(qty 3), When 「상세 조건 입력」, Then IMG2 에 칩 「Smart Signage QM55C ×3」, 스타일 「실사 렌더」·비율 「16:9」·장수 「4장」이 선택돼 있고 주 버튼은 「이미지 4장 생성」이다.
3. Given IMG2 에서 「2장」 선택, When 주 버튼, Then 버튼 문구가 「이미지 2장 생성」이고 생성된 run 의 시안이 2개다.
4. Given IMG2 이고 상단 이미지 검색에서 2장을 「현재 작업에 추가」, Then 참조 썸네일 2개와 「이미지 검색에서 선택한 2장이 참조로 들어갔습니다」가 보인다.
5. Given prefill 이 10초를 넘기는 LLM 목, When 「상세 조건 입력」, Then 10초 안에 IMG2 가 열리고 A1 결과만 칩으로 채워진다.

**IMG2R**
6. Given 사내 자산 탭, When 화면을 열면, Then 검색 입력값이 prefill 검색어(「카페 메뉴보드」)이고 결과 머리가 「{n} 개 · 검수 완료」이며 모든 결과의 `rights ∈ {official, customer_case}` 이다.
7. Given 결과 2장을 고르고 첫째에 「구도」「제품 배치」·강도 「중」, 둘째에 「색감 · 조명」「소재」·강도 「강」, When 「참조 2장 적용」, Then IMG2 로 돌아가고 `work.references` 2건에 요소·강도가 그대로 저장된다.
8. Given 업로드 참조, When 강도 「강」을 누르면, Then 바뀌지 않고 422 `STRENGTH_NOT_ALLOWED`(웹은 비활성 표시)다.
9. Given 참조 3장 선택 상태, When 넷째를 고르면, Then 선택되지 않고 「참조는 3장까지 고를 수 있어요」가 보인다.
10. Given 참조에 얼굴 bbox 가 있는 i2t 픽스처와 `I2T_SUPPORTS_BBOX=true`, When 생성, Then T2I 로 보낸 참조 이미지의 해당 bbox 영역 픽셀 분산이 원본의 10% 이하(블러)이고 원본 파일은 보내지 않는다. Given 같은 참조와 `I2T_SUPPORTS_BBOX=false`, Then 그 참조는 이미지로 보내지 않고 `send_mode='text_fallback'` 이다.

**참조 예산 · 능력 대체**
11. Given `T2I_MAX_REFERENCE_IMAGES=3`, 제품 2종(QM55C ×3, KM24C ×1)과 사용자 참조 2장(강·중), When 시안 렌더, Then `t2i.generate` 인자의 이미지는 [QM55C 단독컷, KM24C 단독컷, 강도 「강」 참조] 순서 3장이고 「중」 참조는 프롬프트 텍스트(팔레트 hex 5개 포함)로 들어간다.
12. Given `T2I_SUPPORTS_REFERENCE_IMAGES=false`, When 생성, Then `t2i.generate` 에 이미지 인자가 없고 프롬프트에 제품 화면비(예 “16:9 landscape panel, thin black bezel”)와 참조 묘사가 있으며 `generation.fallbacks` 에 `reference:text_fallback` 이 있다.

**IMG3G · 대기열 · 취소 · 알림**
13. Given 4장 run 과 지연 목, When 진행, Then 동시에 `render` 중인 시안은 최대 2개이고, 대기 시안 카드 문구는 「시안 {j}가 끝나면 시작해요」(j = 진행 중 가장 먼저 시작한 시안 번호)다.
14. Given 진행 중 시안 3, When 「이 장 취소」, Then 그 시안 결과는 저장되지 않고 카드가 「취소됨」, run 은 나머지로 끝나 `done=3, total=4` 이다.
15. Given 시안 1 완료 후, When 「전체 취소 · 조건 수정」, Then jobs 취소가 요청되고 IMG2 로 이동하며 조건이 그대로이고 시안 1 은 갤러리에 남는다.
16. Given 사용자 진행 run R1, 대기 run R2·R3, When `GET /v1/queue`, Then R2 `state_label='다음 차례'`, R3 `'2번째'` 이고 R1 이 끝나기 전 R2 는 `running` 이 되지 않는다.
17. Given `notify=true`, When run 완료, Then jobs 완료 알림이 정확히 1번 요청되고 링크가 IMG3 경로다. `notify=false` 면 요청하지 않는다.
18. Given IMG3G 를 떠난 상태, When IMG0 를 열면, Then 그 작업 행 배지가 「생성 중 {done} / 4」이고 갤러리에 「생성 중」 「{done} / 4」 「진행 보기」 타일이 있다.
19. Given ai-tools 가 `QUOTA_EXCEEDED`, When 렌더, Then 재시도 없이 run `failed`, 끝난 시안은 보존, W 에 「오늘 쓸 수 있는 이미지 생성 횟수를 다 썼어요」.

**정책 · IMG3X**
20. Given 설명 「경쟁사 A 메뉴보드 옆에 QM55C, 배우 ○○○가 주문하는 장면」과 디스플레이를 못 알아보는 참조 사진(i2t 매칭 top1 0.5 < 0.6, C2 후보 QM55C·QB55C·QH55C), N=4, When 생성, Then 2장 생성·2장 보류, run `awaiting_input`, 사유 3개의 상태가 각각 「대안 선택됨」(「QM55C · 가장 비슷」) / 「대안 선택됨」(「로고 없는 일반 화면으로」) / 「선택 필요」이고 머리는 「보류 사유 3 · 대안 2개 선택됨」, 하단은 「대안 선택 · 3개 중 2개 선택됨」이다.
21. Given 20 의 상태에서 인물 대안을 고르지 않고 「대안으로 2장 이어서 생성」, Then 보류 2장이 「인물 없이 · 기본값」으로 만들어지고 라벨이 「시안 3」 「시안 4」이며 프롬프트에 경쟁사명·인물 이름이 없다.
22. Given 20, When 「보류 2장 건너뛰기」, Then run `succeeded`, 보류 시안 `canceled`, IMG3 에 2장.
23. Given N=2 이고 실존 인물 사유만 있음, When 생성, Then 1장 생성·1장 보류다(`floor(2/2)=1`).
24. Given 「다른 대안 입력」에 「경쟁사 화면은 회색 박스로」, When 보내기, Then 경쟁사 사유의 대안이 custom 으로 저장되고 정책 재검사(목)가 통과해야만 반영된다.
25. Given 사전 검사에서 이슈가 있지만 모든 이슈가 자동 해결(선택 필요 없음)인 run, When 생성, Then 보류 없이 N장을 만들고 IMG3 에 「요청 중 {k}가지를 바꿔서 만들었어요 · 자세히」 띠가 보인다.

**품질 확인**
26. Given 시안 2 의 첫 QC 목이 `logo_visible=true`, 둘째가 정상, When 생성, Then 시안 2 는 1번 재생성되고 최종 버전은 둘째 결과, `qc.status='ok'`.
27. Given 두 번 모두 QC 실패, Then 시안은 보존되고 `qc.status='check'`, IMG3 타일에 「확인 필요」 배지.
28. Given `i2t.analyze` 가 JSON 을 못 돌려주는 목, Then `qc.status='skipped'`, `fallbacks` 에 `qc:skipped`, 시안에 「확인 필요」.

**IMG3**
29. Given 4장 완료, When IMG3 을 열면, Then 시안 1 이 「선택됨」, 라벨 「시안 1 · 16:9 · 실사」, 카드 머리 「시안 1 선택됨 · 3 / 3」이다.
30. When 「밝기 올리기」, Then 200 으로 새 버전(`op=adjust`, n=2)이 생기고 평균 휘도가 기준보다 높으며 모델 호출이 0회다.
31. When 「내 이미지에 저장」, Then `image.saved=true` 이고 IMG0 「내 생성 이미지」 개수가 1 늘어난다.

**IMG3E**
32. Given `T2I_SUPPORTS_MASK=false`, fhd 기준 버전, 사각 영역 R, 단색 크롭을 돌려주는 `t2i.edit` 목, When 「적용」, Then (R ⊕ 8px) 바깥 픽셀이 기준과 바이트 단위로 같고 R 안쪽이 바뀌며, 새 버전 라벨 「수정 1 · 영역 1」, 영역 상태 「적용됨 · 비교 중」, 비교 라벨 「전 · 원본」 「후 · 수정 1」이다.
33. Given `T2I_SUPPORTS_MASK=true`, When 같은 적용, Then `t2i.edit` 가 전체 이미지 + 마스크로 1번 호출되고 32 의 바깥 픽셀 조건도 만족한다.
34. Given `I2T_SUPPORTS_BBOX=false`, Then 「객체 선택」이 비활성(툴팁 「지금 모델은 객체 인식을 지원하지 않아요」)이고 「글자 지우기」는 전체 편집 지시로 바뀌며 안내 「자동 영역 인식이 없어 전체 이미지에 적용해요」가 보인다.
35. Given 「제품 외형 고정」 켜짐, 제품 박스가 R 과 겹침, When 적용, Then 제품 테두리 띠(바깥 박스 − 3% 안쪽 박스) 픽셀이 기준과 같다.
36. Given 영역 1 적용 후, When 「되돌리기」, Then 현재 버전이 「원본」이 되고 「수정 1 · 영역 1」 버전은 수정 기록에 남으며 영역 상태가 `reverted` 다.
37. Given 영역 2개 대기, When 둘 다 「적용」, Then 번호 순으로 순차 적용되어 버전이 2개(n=2, n=3) 생긴다.

**IMG3V**
38. When 「이 시안으로 변형 4장」, Then IMG3V 로 이동하고 변형 run 이 시작되며, 완료 후 카드 라벨이 「A · …」~「D · …」(LLM 목 라벨)이다. `T2I_SUPPORTS_EDIT=true` 면 4번 모두 `t2i.edit(기준)` 이다.
39. Given `T2I_SUPPORTS_EDIT=false, REFERENCE=true`, Then 변형은 `t2i.generate(ref=기준)`; 둘 다 false 면 텍스트 생성이고 카드에 「배치가 조금 달라질 수 있어요」.
40. Given 업스케일 「×2」, Then 카드 해상도가 16:9 「3840×2160」, 4:3 「2880×2160」, 1:1 「2160×2160」, 9:16 「2160×3840」; 「원본」이면 1920×1080·1440×1080·1080×1080·1080×1920; `UPSCALER=none` 이면 「×4」 비활성.
41. Given 16:9 와 9:16 선택, 「다시 구성」, 「×2」, When 「2개 비율로 만들기」, Then IMG3G 로 이동하고 결과로 3840×2160 시안(업스케일만, T2I 호출 0)과 2160×3840 시안(T2I 1회 + 업스케일)이 새 시안(`base_image_id` 연결)으로 생긴다.
42. Given 「잘라내기」 1:1, 제품 박스가 가로 중앙 40% 안, When 실행, Then T2I 호출 0회이고 결과 창이 모든 제품 박스를 포함한다.
43. Given 「바깥 채우기」 9:16, When 실행, Then `t2i.edit` 입력 캔버스가 576×1024 이고, 결과에서 원래 영역(리사이즈 기준)과의 평균 절대 차가 1 미만이다.
44. Given `UPSCALER=none`, When ×2 렌디션, Then `renditions[].method='lanczos3+unsharp'` 이고 `/info` 「저장본」에 업스케일 방식이 보인다.

**IMG2P**
45. Given 휘도 평균 0.15 사진, When 업로드, Then 탭 상태가 「어두워 인식 어려움 · 다시 촬영 권장」이다.
46. Given 카운터 bbox 가로 900px(원근 보정 후)와 「카운터 폭」 3600, QM55C 가로 1,236mm(스펙 픽스처), 「가로 3연」, When 배치 저장, Then 응답 `width_mm=3730`(3×1236+2×10=3728 → 10mm 반올림)이고 라벨이 「가로 약 3,730 mm · 바닥에서 {H} mm」 형식이다. 축척을 못 구하면 「[00]」이 그대로 보인다.
47. Given 「원근 · 조명 맞춤」 켜짐과 편집 목, When 「합성 이미지 4장 생성」, Then 시안마다 결정적 합성 → `t2i.edit` 순으로 호출되고, 결과의 제품 쿼드 가장자리 IoU(합성 대비) < 0.9 인 시안은 결정적 합성 + 로컬 조화 결과로 대체되며 `fallbacks` 에 `composite:local_only` 가 남는다.
48. Given 현장 사진(권리 customer)과 ai-tools 의 `POLICY_CONFIDENTIAL`, When 생성, Then 모든 시안이 로컬 경로로 만들어지고 모든 ai-tools 호출 인자에 `confidential:true` 가 있었다.

**IMG4 · 내보내기 · 제안서 · 요청 · 렌더 API**
49. Given 시안 1 v2(부분 수정), 고객 약칭 「A 커피」, When IMG4 를 열면, Then 제목 「시안 1 · 부분 수정본 v2」, 파일명 기본값 「A커피_메뉴보드_시안1_v2.png」, 버튼 「PNG 다운로드」, 해상도 「3840×2160」 선택이다.
50. Given 「AI 생성 이미지 표기 넣기」 체크, When PNG 다운로드, Then 파일 오른쪽 아래 표기 영역 픽셀이 렌디션과 다르고 XMP `DigitalSourceType` 이 `trainedAlgorithmicMedia` 다. 체크 해제면 픽셀은 렌디션과 같고 XMP 는 그대로 있다.
51. Given 「수정 전 원본도 함께」 체크, When 다운로드, Then export ZIP job(202)이 생기고 ZIP 에 PNG 2개와 `sources.json` 이 있다.
52. Given 형식 「PPTX」, When 다운로드, Then export 에 이미지 1장 템플릿 요청이 가고 job 완료 후 링크가 생긴다.
53. Given 제안서 목록 목(2건)과 시트 목(추천 1), When 「제안서에 넣기」, Then 웹이 `POST /api/proposal/v1/proposals/{id}/imports` 에 `{source:{service:'image', version_id}, target:{sheet_id, mode:'replace_slot'}}` 를 보내고, 이어 제안서 목이 `POST /v1/images/{id}/usages` 를 부르면 IMG0 배지가 「제안서 사용 중」이 된다.
54. Given scenario 가 `POST /v1/requests` 로 「장면 2 · 점심 피크 주문」 요청, When IMG0, Then 요청 행(출처 「공간 시나리오 · A 커피 매장 하루」)이 보이고 「만들기」 → IMG1 이 요청의 유형·설명으로 채워진다. IMG4 「공간 시나리오 장면으로」를 누르면 요청이 `fulfilled`, `result_version_id` 가 그 버전이다.
55. Given birdseye 의 `POST /v1/renders`(structure_ref, aspect 16:9, target uhd), When 완료, Then 결과 렌디션이 3840×2160, `generation.origin.service='birdseye'`, IMG0 기본 갤러리에는 나오지 않는다. `T2I_SUPPORTS_REFERENCE_IMAGES=false, EDIT=true` 면 `t2i.edit(edit_of=structure_ref)` 로 호출된다.
56. Given 작업 생성·run 완료·내보내기, Then 각 시점에 workspace `PUT items/{id}` 가 `feature='image'`, 올바른 `route`(§5.4)로 호출된다.
57. Given 버전 3개, When `POST /v1/images/{id}/versions/1/restore`, Then 현재 버전이 1 의 내용을 가진 새 버전(n=4)이고 이전 버전은 남는다.

---

## 10. 규칙 · 임계값

### 10.1 보드의 수치(그대로)
- 유형 3(공간·배경·시나리오) + 목록 칩 「제품 합성」, 스타일 3(실사 렌더·미니멀 3D·일러스트), 생성 비율 3(16:9·4:3·1:1), 장수 2(2장·4장, 기본 4장), 단계 `1 / 3`·`2 / 3`·`3 / 3`.
- 참조 따를 요소 4(색감 · 조명, 구도, 제품 배치, 소재), 강도 3(약·중·강), IMG2R 결과 8칸, 탭 4.
- 생성 중 단계 4(제품 외형 맞춤 · 장면 구성 · 렌더링 k / N · 품질 확인), 보드 예: 「1 / 4 완료」, 「렌더링 중 80%」, 「장면 구성 중 35%」, 「약 1분 남음」, 「내 대기열 2 건」.
- 보류 예: 「4장 중 2장을 만들고 2장은 보류」, 「보류 사유 3」, 「대안 2개 선택됨」, 대안 칩 5 / 2 / 3개.
- 부분 수정 도구 4, 크기 3, 보드 예 영역 2개.
- 변형 4장(A~D), 비율 4(16:9 3840×2160 · 4:3 2880×2160 · 1:1 2160×2160 · 9:16 2160×3840, ×2 기준), 맞추는 방법 3(다시 구성·잘라내기·바깥 채우기), 업스케일 3(원본·×2·×4).
- 내보내기 형식 4(PNG·JPG·PDF·PPTX), 해상도 2(1920×1080·3840×2160), 체크 2(AI 생성 이미지 표기 넣기 = 기본 켬, 수정 전 원본도 함께 = 기본 끔), 넣는 방식 2.
- IMG2P 배열 3(가로 3연·세로 3연·따로 배치), 설치 2(벽 부착·천장 매달기), 기준 치수 2(카운터 폭·설치 높이, mm), 토글 2(둘 다 기본 켬), 합성 4장.

### 10.2 해상도 사다리(결정)
| 렌디션 | 짧은 변 | 16:9 | 4:3 | 1:1 | 9:16 | 만드는 법 |
|---|---|---|---|---|---|---|
| native | — | 1024×576 | 1024×768 | 1024×1024 | 576×1024 | T2I 출력(`T2I_MAX_SIDE_PX=1024`) |
| fhd = 「원본」 | 1080 | 1920×1080 | 1440×1080 | 1080×1080 | 1080×1920 | native → 업스케일(편집 마스터) |
| uhd = 「×2」 | 2160 | 3840×2160 | 2880×2160 | 2160×2160 | 2160×3840 | 업스케일 |
| uhd8k = 「×4」 | 4320 | 7680×4320 | 5760×4320 | 4320×4320 | 4320×7680 | 업스케일 모델이 있을 때만 |
“원본”은 모델 원출력이 아니라 기준 렌디션(fhd)이다. 정보 패널·메타에는 원출력 크기와 업스케일 방식을 항상 함께 쓴다. 8K 렌디션은 동시 1개(`UPSCALE_8K_CONCURRENCY=1`).

### 10.3 참조 예산 배정(결정적)
`max = T2I_MAX_REFERENCE_IMAGES`(기본 3). 순서: (1) 제품 단독컷 — 서로 다른 제품마다 1장, 수량 큰 순, 최대 `PRODUCT_REF_MAX=2` (2) 사용자 참조 — 강 > 중 > 약, 같으면 고른 순서 (3) 남는 참조는 텍스트 대체. structure_ref(렌더 API)는 항상 1순위.

### 10.4 시스템 기본값(제안 — 운영 중 조정)
| 키 | 기본 | 뜻 |
|---|---|---|
| `IMAGE_WORKER_CONCURRENCY` | 2 | 워커 동시 job |
| `IMAGE_MAX_RUNNING_PER_USER` | 1 | 사용자당 진행 run(나머지 대기열) |
| `IMAGE_SHOT_CONCURRENCY` | 2 | run 안 동시 시안 |
| `QC_MAX_RETRY` | 1 | 품질 확인 실패 재생성 |
| `PRODUCT_MATCH_MIN` | 0.6 | 디스플레이 제품 매칭 최소 신뢰도 |
| `PRODUCT_ASPECT_TOL` | 0.15 | 제품 박스 비율 허용 오차 |
| `VARIANT_LAYOUT_IOU_MIN` | 0.5 | 변형 '제품 배치 유지' |
| `GLOBAL_EDIT_PRODUCT_IOU_MIN` | 0.8 | 전체 수정 시 제품 유지 |
| `COMPOSITE_EDGE_IOU_MIN` | 0.9 | 합성 조화 후 제품 형태 유지 |
| `FEATHER_PX` / 링 | 8 / 16 (fhd) | 붙이기 페더·보정 링 |
| `CROP_PAD` | max(64px, 25%) | 편집 크롭 여백 |
| 어두움 판정 | 휘도 평균 < 0.22 | 「어두워 인식 어려움 · 다시 촬영 권장」 |
| 브러시 지름 | 12 / 24 / 48 px | 작게 / 보통 / 크게 |
| 참조 최대 | 3 | 사용자 참조 장수 |
| 업로드 | JPG·PNG·HEIC, 20MB | 참조·현장 사진 |
| prefill 제한 | 10초 | IMG1 → IMG2 |
| 재시도 | 2회(2초, 6초) | 일시 오류 |
| AI 표기 | 글자 높이 1.6%, 여백 2% (짧은 변) | 내보내기 |
| 표준 크기 힌트 | 문 2,100 mm · 카운터 1,050 mm · A4 297 mm | 사진 축척 추정 |

### 10.5 상태·문구 매핑
- 작업 배지 우선순위와 문구: §4.1 표. 시간 표기: §4.1.
- 대기열 순번: 1 → 「다음 차례」, k ≥ 2 → 「{k}번째」.
- 남은 시간: ≥ 60초 「약 {ceil(s/60)}분 남음」, < 60초 「약 {round10(s)}초 남음」.

### 10.6 콘텐츠 정책(「생성 이미지 사용 기준」 팝오버 내용 — **(신규)**, 법무 확인 필요)
1. 다른 회사의 로고·상표·고유 디자인(제품 외형 포함)은 그리지 않는다. 비교는 Why Samsung 비교표 시트로.
2. 실존 인물(연예인·공인·특정 개인)의 얼굴·이름을 쓴 이미지는 만들지 않는다. 사람은 가상 인물·뒷모습·손만.
3. 참조·현장 사진 속 사람 얼굴과 다른 회사 로고는 흐리게 처리하거나 글로만 참고한다.
4. 고객 현장 사진은 고객 자료로 취급한다(기밀 표시, 대외 사용 전 고객 확인).
5. 생성 이미지는 「AI 생성 이미지」 표기를 권장하고, 제품 수치·인증 마크·가격을 이미지에 그리지 않는다.
- 경쟁사 사전 `config/content_policy.yaml`(`competitor_brands`, 한·영 표기, draft) + LLM 판정. 사전 밖 “경쟁사 A” 같은 일반 표현도 LLM 이 잡는다.

---

## 11. 열린 질문
1. **배경 유형의 조건**: 보드는 IMG2 를 '공간'만 그렸다. 배경의 텍스트 여백 위치(기본 왼쪽 40%)를 사용자에게 묻지 않고 자동으로 둔 결정이 맞는가?
2. **해상도 의미**: IMG3V 「원본」=1920×1080 계열, BE6 「원본」=3840×2160 으로 보드마다 다르다. 이 문서는 IMG 의 「원본」을 fhd 로 정했다. 용어를 「기본(FHD)」로 바꿀지 디자인 확인 필요.
3. **×4(8K)** 를 업스케일 모델이 있을 때만 켜는 결정 — 1024px 원출력에서 7.5배라 품질이 낮다. 보드에서 ×4 를 뺄지?
4. **「사내 자산 48」 숫자 기준·출처**: 프로젝트 업종 맥락의 KB 결과 수로 정했다. 셸 스펙(00-shell 갭 G-IMG-5)은 「사내 자산」 출처를 미정으로 두고 KB 이미지를 「제품 이미지」·「유관 사례 이미지」 탭으로 나눈다 — 두 화면의 「사내 자산」 정의를 하나로 맞춰야 한다. 사내 별도 브랜드 자산 DB 가 생기면 출처를 바꿔야 한다. “검수 완료”를 “삼성 공식 게시 = 브랜드 검수”로 본 해석 확인.
5. **조감도 렌더의 갤러리 노출**: IMG0 기본 목록에서 birdseye 렌더를 숨겼다. 상단 이미지 검색 「내 생성 이미지」에는 출처 라벨과 함께 보이게 할지?
6. **진행률 표시**: 제공자가 진행률을 주지 않아 지연 EMA 추정치를 쓴다. 「렌더링 중 80%」 같은 숫자를 보여도 되는지, 아니면 단계만 보여 줄지?
7. **보류 비율** `floor(N/2)` 은 보드 예(4→2, 2→1)에서 역산한 규칙이다. 정책 이슈가 있으면 전부 보류하는 편이 나은지?
8. **정책 사전 검사 시점**: 대기열에서 「1장은 생성 불가」를 보이려면 run 생성 시 동기 검사가 필요하다(LLM 8초 제한). 지연이 문제면 워커 첫 노드로만 옮기고 대기열 안내를 뺄지?
9. **제안서 API**: 이미지 슬롯 목록·추천·가져오기(imports)·사용 등록은 제안서 서비스 계약에 아직 없다(`docs/requests/proposal.md` 필요).
10. **jobs 목록 순번**과 **완료 알림** 문구·채널(토스트·사이드바 배지)이 jobs/셸 계약에 있는지 확인 필요.
11. **경쟁사 사전·법무 문구**(§10.6)의 소유자와 승인 절차.
12. **i2t bbox 좌표 규약**(0..1 정규화, [x0,y0,x1,y1])과 쿼드(점) 출력 지원 여부 — 현장 사진 원근 맞춤 자동 스냅의 품질이 여기에 달려 있다.
13. **업스케일 모델 배포**: realesr-general-x4v3 ONNX(약 5MB)를 오프라인 폴더로 옮길지, Lanczos 로만 갈지.
