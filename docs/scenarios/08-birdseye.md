# 08. 공간 조감도 (birdseye · BE) — 화면 수용 기준

- 범위 보드(14): `UC_BE` `BE0` `BE1` `BE1D` `BE1P` `BE2` `BE3` `BE4` `BE4E` `BE5G` `BE5` `BE5V` `BE5Z` `BE6`
- 원천: `docs/screens/webapp2/<보드>.dc.html`, `docs/screens/_text/webapp2/<보드>.txt`, `docs/ARCHITECTURE.md`, `config/services.yaml`, `winmate-kb/seed/ontology/{placement_rules,space_types,visual_vocab}.yaml`, `winmate-kb/docs/*`
- 표기: 「…」 = 보드 문구 그대로. **(신규)** = 보드에 없는 상태용 제안 문구. `{변수}` = 템플릿 자리.
- 생성 이미지(렌더·편집·업스케일·품질 확인·AI 표기·출처 메타)는 **image 서비스 렌더 API**(07 §6.9)로만 만든다. 이 서비스는 T2I 를 직접 부르지 않는다.

---

## 1. 목적과 진입점

**목적.** 고객 공간(설명 · 도면 · 현장 사진)을 미터 단위 공간 모델로 만들고, 삼성 제품과 가구를 **결정적 배치 엔진**으로 배치 · 검증(시야각 · 동선 · 전원)한 뒤, 3D 조감도(생성 이미지)와 시점·조명 컷, 존 포인트, 제품 수량표를 만들어 제안서(BV · ZP · SM 시트) · 공간 시나리오 · Spec 시트로 넘긴다. 공간·배치는 모델이 아니라 엔진이 정하고, 모델은 (1) 입력 해석 (2) 사실적 렌더 (3) 문구 작성에만 쓴다.

| 항목 | 값 |
|---|---|
| 서비스 | `birdseye` · 포트 **5108** · `worker: true` · 큐 `wm:q:birdseye` |
| 게이트웨이 | `/api/birdseye/v1/...` (내부 `/v1/...`), `GET /healthz` |
| 소유 경로 | `services/birdseye/**`, `web/src/features/birdseye/**` |
| consumes | `ai-tools, kb, files, jobs, workspace, export, image` |
| 데이터 | `${DATA_DIR}/birdseye/birdseye.sqlite` + 체크포인트 `${DATA_DIR}/birdseye/checkpoints.sqlite` |
| 설정 | `services/birdseye/config/rules.yaml`(배치·검증 파라미터, §10.3), `config/furniture_catalog.yaml`(가구 카탈로그, §10.4) |
| 웹 모듈 | `web/src/features/birdseye/` — 사이드바 그룹 `birdseye`, 이름 「공간 조감도 생성」, 목록 `/birdseye`, 새 작업 `/birdseye/new` |
| 스텝바 | `steps = ['공간 입력', '배치될 제품', '가구 추천', '배치 · 인테리어 컨펌', '3D 조감도 생성']` — BE1/BE1D/BE1P=1, BE2=2, BE3=3, BE4/BE4E=4, BE5G/BE5/BE5V/BE5Z=5, BE6=5 + `complete` |
| 상단바 | `section="공간 조감도 생성"`, `title` = 작업 제목(새 작업 「새 작업」, 목록 「작업 목록」) |

**진입점**
1. 홈의 '공간 조감도 생성' 카드, 사이드바 「새 작업」 → BE1. 사이드바 그룹 → BE0, 그룹 항목 → 그 작업의 현재 화면(`route`).
2. 제안서 '조감도' 섹션(PRS3)에 넣을 조감도가 없을 때 「조감도 새로 만들기」 → BE1(`?return_to=` 제안서 경로).
3. 공간 시나리오 SC1 「조감도 추가 · 새로 만들기」 → BE1(시나리오 공간·제품 미리 채움, `origin.service='scenario'`). 시나리오는 조감도 없이 만드는 것이 기본이고 조감도는 선택 옵션이다.
4. 이미지 생성 IMG4 「조감도 참조로」 → BE1(이미지 버전을 참조로 붙임 — 렌더 프롬프트의 분위기 참조).
5. BE0 「팀에서 공유한 조감도」 「복제해서 시작」 → BE4.

**화면 원칙.** W 말풍선 1개 + 사용자 입력 메아리 + 하단 작업 카드 1장. 보드에 없는 패널은 만들지 않는다. W 문구는 상태값 템플릿(LLM 이 쓰지 않음). 템플릿의 조사(을/를 · 이/가 · 은/는 · 으로/로)는 앞말 발음으로 고른다(07 §1 규칙과 같음, 예 「The Wall을」). 방향어는 고정 표: 위 → 「위로」, 아래 → 「아래로」, 왼쪽 → 「왼쪽으로」, 오른쪽 → 「오른쪽으로」.

---

## 2. 화면 목록

| 보드 | 제목 | 라우트 / 상태 제안 | 주요 요소 |
|---|---|---|---|
| `UC_BE` | 조감도 · 유스케이스 맵 | 런타임 화면 아님(흐름 원천) · 개발용 `/_dev/uc/birdseye` 선택 | 기본 흐름 8칸, 레인 5, 확인 필요 박스, 통계 |
| `BE0` | 조감도 · 작업 목록 | `/birdseye` | 시작 카드 3, 상태 필터, 작업 표, 행 메뉴, 팀 공유 조감도 |
| `BE1` | 조감도 1/5 · 공간 입력 | `/birdseye/new` · `/birdseye/:id/space` | 공간 유형 칩 6, 공간 설명, 면적(평)·층고(m), 파일 첨부 |
| `BE1D` | 조감도 · 도면 인식 확인 | `/birdseye/:id/space/plan` (새로 `/birdseye/new/plan`) | 인식 결과 캔버스, 인식 요소 5종, 되묻기, 치수 보정, 말로 고치기 |
| `BE1P` | 조감도 · 현장 사진으로 입력 | `/birdseye/:id/space/photos` (새로 `/birdseye/new/photos`) · 모바일 `/m/upload/:token` | 촬영 가이드, 찍은 방향, QR, 사진별 인식 상태, 천장 사진, 추정 요약 |
| `BE2` | 조감도 2/5 · 배치될 제품 | `/birdseye/:id/products` | 공간 요약 칩, 제품 검색·추가, 제품 탐색 |
| `BE3` | 조감도 3/5 · 가구 추천 | `/birdseye/:id/furniture` | 추천 가구 카드 4, 선택 칩, 다른 추천, 가구 없이 진행, 직접 입력 |
| `BE4` | 조감도 4/5 · 배치·인테리어 컨펌 | `/birdseye/:id/layout` | 2D 배치안, 인테리어 톤 3, 시점 2, 배치 수정 요청 |
| `BE4E` | 조감도 · 배치 직접 수정 | `/birdseye/:id/layout/edit` | 편집 도구 3, 표시 4, 변경 수, 경고 카드·자동 조정, 말로 수정 |
| `BE5G` | 조감도 · 생성 중 | `/birdseye/:id/render/:jobId` — job `queued`·`running` | 단계 5, 진행률, 초안 미리보기, 컷 대기열, 확인 필요, 진행 중 요청, 중지 |
| `BE5` | 조감도 5/5 · 3D 조감도 생성 | `/birdseye/:id/result` (`?cut=bec_…`) | 완성 조감도, 컷 썸네일, 제품 칩, 수정 요청, 저장, 제안서에 넣기 |
| `BE5V` | 조감도 · 시점 · 조명 바꾸기 | `/birdseye/:id/views` | 전/후 비교 보기 3, 만든 컷 목록, 시점 4·조명 3·도입 전 컷, 시점 설명 |
| `BE5Z` | 조감도 · 존 포인트 지정 | `/birdseye/:id/zones` (`?scenario=sc_…` 장면 연결 모드) | 번호 포인트 편집, 존 이름·문구·연결, W 제안, 시트 레이아웃 3 |
| `BE6` | 조감도 · 내보내기 · 보내기 | `/birdseye/:id/export` | 이미지 선택·형식·크기, 제품 수량표, 제안서 매핑, 시나리오·Spec·보기 링크, ZIP |

---

## 3. 사용자 흐름

### 3.1 기본 흐름(UC_BE 「기본 흐름」)
「BE1 공간 입력」 → 「BE2 배치될 제품」 → 「BE3 가구 추천」 → 「BE4 배치 컨펌」 → 「BE5G 생성 중」 → 「BE5 3D 조감도」 → 「BE6 내보내기」 → 「PRS3 제안서에 넣기」.

### 3.2 레인(UC_BE)
| 레인 | 화면 |
|---|---|
| 「01 들어오는 길」 3 | Main(「홈의 '공간 조감도 생성' 카드, 사이드바 '새 작업' · 작업 내역에서 시작」 → BE1 · BE0), BE0(「이어서 하기 · 상태 필터 · 검색, 도면 · 사진으로 시작, 팀 공유 조감도 복제」 → BE1 · BE1D · BE1P · BE4 · BE5), PRS3(「넣을 조감도가 없으면 '조감도 새로 만들기'로 이 기능에 들어옴」 → BE1 · BE0) |
| 「02 입력 방식」 5 | BE1(「공간 유형 칩 · 설명 · 면적 · 층고, 도면이나 사진 첨부」), BE1D(「벽 · 창 · 문 · 기둥 인식 결과 확인, 모호한 문 되묻기, 치수 보정」), BE1P(「촬영 가이드 · 사진별 인식 상태, 다시 찍기, 휴대폰 QR 업로드」), BE2(「제품명 검색 · 제품 탐색에서 고르기, 수량은 컨펌 단계에서」), BE3(「공간 특징에 맞춘 가구 추천 · 직접 추가 · 가구 없이 진행」) |
| 「03 진행 · 확인 상태」 4 | BE4(「2D 배치안 확인, 인테리어 톤 · 시점 선택, 말로 배치 수정 요청」), BE5G(「생성 진행 상태 · 중지, 기다리는 동안 다른 작업 가능」), BE5(「완성 조감도 · 시점 썸네일, 수정 요청 · 저장 · 제안서에 넣기」), 확인이 필요할 때 |
| 「04 편집 · 버전」 4 | BE4E(「끌어서 옮기기, 시야각 · 동선 · 전원 위치 경고와 자동 조정」), BE5V(「주간 / 야간, 다른 각도, 도입 전 / 후 비교 버전」), BE5Z(「조감도 위 번호 콜아웃 → 제안서 '존별 포인트'로」), BE0 복제(「완성된 조감도를 복제해 다른 배치 · 톤의 비교 시안 만들기」) |
| 「05 결과 활용」 5 | BE6(「이미지 · 제품 수량표 내보내기, 제안서 · 시나리오 · Spec 시트로 보내기」), PRS3(「공간 전경 · 존별 포인트 시트에 조감도 연결」), PRS4(「배치안의 공간 · 제품 · 수량을 공간 맵 · 구성 시트로」), SC1B(「조감도 존을 공간으로 가져와 공간 시나리오 시작」), PR1L(「새 제안서에 조감도 작업을 연결해 시작」) |

「확인이 필요할 때 · W가 되묻거나 경고를 띄우는 화면」: 「BE1D 도면 인식 확인 필요 · 치수 보정」, 「BE1P 사진 다시 찍기 · 천장 사진 없음」, 「BE4E 시야각 · 동선 · 전원 위치 경고」, 「BE0 목록의 '확인 필요' 필터」.
통계: 「이 기능의 화면 13 전체 화면 5 기본 흐름 8 새 화면 5 연결된 다른 기능」, 「새 화면 8개가 도면 · 사진 입력, 확인 · 경고, 시점 버전, 내보내기 · 보내기를 채웁니다.」

### 3.3 라우팅 규칙
| # | 시점 | 에이전트가 자동으로 | 사용자에게 묻는 것 |
|---|---|---|---|
| R1 | BE1 파일 첨부 | 파일 종류 분류: PDF·DWG 내보내기 PDF → 도면, 이미지 → i2t “평면도인가?”(예 → 도면, 아니오 → 현장 사진). 도면과 사진이 섞이면 BE1D 먼저, 끝나면 BE1P | 없음 |
| R2 | BE1 → BE2 | 공간 설명 해석(LLM JSON + 정규식 대체) → 공간 모델. 도면·사진이 없으면 직사각형 모델(면적·가로세로비 1.5:1 가정, `estimated`) | 없음 |
| R3 | BE1D | 확실한 요소는 확정. 문 종류가 불확실(신뢰도 < 0.6)하거나 치수 불일치(> 1%)일 때만 되묻기 | 되묻기 항목만. 답하지 않고 계속하면 안전 기본값(§10.3)을 쓰고 가정으로 기록 |
| R4 | BE2 | 공간 특징 → 역량(KB C1)으로 W 권장 문구(예 「고휘도 권장」). 크기 옵션이 여러 개인 제품은 엔진이 벽 폭·시청 거리로 크기 선택 | 제품 선택만 |
| R5 | BE3 | 가구 추천 4개 중 상위 3개 미리 선택 | 넣을지 말지 |
| R6 | BE3 → BE4 | 배치 의도(LLM, 닫힌 어휘) → 엔진 배치 → 자동 조정 가능한 경고는 바로 조정, 전원 경고는 메모 | 없음(남은 경고는 BE4 에 링크) |
| R7 | BE4 → BE5G | 렌더 시작과 함께 추가 컷 자동 예약(§7.8: 야간·도입 전) | 대기열에서 뺄지 |
| R8 | BE5 수정 요청 | LLM 분류: 렌더 수정 → 컷 편집, 배치 수정 → 엔진 → 재렌더, 시점 요청 → 컷 추가 | 모호할 때만 W 가 한 번 되묻기 |
| R9 | BE5Z | 배치 군집 → 존 포인트 자동, 덮지 못한 군집은 W 제안 | 제안 수락 여부 |
| R10 | BE6 | 제안서 시트 매핑(BV-A·BV-B·ZP-x·SM-B) 자동 | 보낼 제안서 |

### 3.4 작업 단계·상태
`step`: 1 공간 입력 → 2 제품 → 3 가구 → 4 배치 → 5 조감도. `status`: `in_progress`(진행 중) · `needs_check`(확인 필요: 다시 찍을 사진, 미해결 되묻기, 품질 확인 실패 컷) · `done`(주 컷 완료) · `failed`. 레이아웃이 바뀌면 이전 레이아웃으로 만든 컷은 `stale`(**(신규)** 배지 「배치 변경 전」)이 된다.

---

## 4. 화면별 상세

### 4.0 UC_BE
§3.1·3.2 의 노드·연결을 모두 구현 대상 연결로 본다. 머리 「WINMATE · USE CASE MAP」, 「공간 조감도 생성 — 유스케이스 맵」, 「들어오는 길부터 결과 활용까지 화면 13개를 한 장에 모았습니다. 화면 코드를 누르면 그 화면으로 이동합니다.」, 범례 「기본 흐름 (기존 화면)」 「새 화면」 「다른 기능 화면」.

### 4.1 BE0 · 작업 목록
- 머리: 「조감도 작업」 `{n}`, 「진행 중인 작업을 이어서 하거나, 공간 설명 · 도면 · 현장 사진으로 새 조감도를 시작하세요.」, 주 버튼 「새 조감도 만들기」(→ BE1).
- 시작 카드: 「공간 설명으로 시작」 「용도 · 면적 · 층고를 적으면 바로 시작」(→ BE1), 「도면 올려서 시작」 「PDF · 이미지 도면에서 벽 · 창 · 문 인식」(→ 업로드 → BE1D), 「현장 사진으로 시작」 「여러 장을 올리면 사진마다 구조를 인식」(→ BE1P).
- 필터: 「전체」 「진행 중」 「확인 필요」 「완료」(각 개수), 토글 「제안서에 쓰인 것만」, 검색(라벨 「작업 검색」, placeholder 「작업 · 고객사 · 공간 검색」), 정렬 「최근 수정순」.
- 표 머리: 「작업」 「입력」 「진행 상태」 「쓰인 곳」 「수정」.

| 열 | 표시 | 출처 |
|---|---|---|
| 작업 | 썸네일(주 컷 thumb, 없으면 첫 현장 사진, 없으면 빈 칸), 제목(링크 = route), 「{고객사} · {공간 라벨}」 (예 「A 커피 프랜차이즈 · 매장 로비」) | `birdseye`, 프로젝트 |
| 입력 | 칩: 「설명」 「도면」 「사진 {n}장」 | 입력 종류 |
| 진행 상태 | 완료: 「완료」 + 「시점 {v} · 존 포인트 {z}」(존 0 이면 뒷부분 생략) + 진행 중 컷이 있으면 링크 「{컷 이름} 추가 생성 중」(예 「야간 시점 추가 생성 중」 → BE5G). 진행 중: 「{step}/5」 + 단계 이름(예 「4/5」 「배치 · 인테리어 컨펌」). 확인 필요: 「확인 필요」 + 사유 줄(예 「사진 1장 다시 찍기 · 1/5 공간 입력」) | `step`, `status`, 컷 |
| 쓰인 곳 | 링크 「제안서 · {제목}」, 「시나리오 · {제목}」 또는 「아직 없음」 | `usage`(제안서·시나리오가 등록) |
| 수정 | 「오늘 HH:mm」/「어제 HH:mm」/「M월 D일」 | `updated_at` |
| 동작 | 완료 「열기」(→ BE5), 진행 중 「이어서」(→ route), 확인 필요 「확인」(→ 확인할 화면) + 작업 메뉴(aria 「작업 메뉴」) | — |

- 작업 메뉴(role menu): 「열기」(BE5) 「배치 직접 수정」(BE4E) 「시점 · 조명 바꾸기」(BE5V) 「존 포인트 지정」(BE5Z) 「복제해서 새 시안」(복제 → BE4) 「내보내기 · 제안서로 보내기」(BE6) 「시나리오로 이어 만들기」(SC1B `?birdseye=`) 「삭제」(**(신규)** 확인 대화 「이 조감도를 삭제할까요? 제안서 · 시나리오에 이미 넣은 이미지는 그대로 남아요.」). 완료 전 작업은 BE5 계열 항목을 비활성.
- 「팀에서 공유한 조감도」 「복제하면 배치안부터 내 작업으로 이어집니다」, 「전체 보기」(공유 목록 전체 팝오버). 카드: 주 컷, 제목, 「{팀} 공유 · 시점 {v} · 존 포인트 {z}」, 「{제품 요약} · 가구 {k}종」(예 「QM55C 메뉴보드 3면 · 가구 6종」), 「복제해서 시작」(→ 복제 → BE4), 「미리보기」(주 컷 + 2D 배치안 라이트박스).
- 복제 규칙: 공간 모델·제품·가구·레이아웃·톤·시점을 복사하고 컷·존 포인트·사용 이력은 복사하지 않는다. 제목 **(신규)** 「{원 제목} 복제」, `cloned_from` 기록.
- 상태: 빈 목록 **(신규)** 「아직 조감도 작업이 없어요」 + 시작 카드 3. 공유 0건이면 공유 섹션 숨김.

### 4.2 BE1 · 공간 입력 (1/5)
- W: 「조감도를 만들 공간을 알려주세요. 용도, 대략의 면적과 층고, 창·기둥 같은 특징이 있으면 함께 적어주세요. 도면이나 현장 사진을 첨부하면 구조를 더 정확히 반영합니다.」 + 보조 「여러 공간을 한 조감도에 담으려면 공간을 줄 단위로 나눠 적어주세요.」
- 작업 카드 머리: 「공간 입력 · 1 / 5」.

| 컨트롤 | 값 | 동작 |
|---|---|---|
| 「공간 유형」 칩(단일) | 「매장 · 로비」(기본) 「회의실 · 오피스」 「강의실」 「병원 대기실」 「호텔 객실」 「관제실」 | KB 공간 코드 대응: 매장·로비 → `sales_floor`,`lobby` / 회의실·오피스 → `meeting_room`,`open_office` / 강의실 → `classroom` / 병원 대기실 → `waiting_area` / 호텔 객실 → `guest_room` / 관제실 → `control_room` |
| 「공간 설명」 textarea | placeholder 「예) 강남 플래그십 스토어 1층 로비. 약 120평, 층고 4.5m, 정면이 전면 유리창이라 낮에는 밝고 저녁엔 외부에서 내부가 잘 보임. 중앙에 기둥 2개.」 (≤ 1,000자) | 줄 단위 = 공간 단위 |
| 「면적」 | placeholder `120`, 단위 「평」(0.1 단위) | 1평 = 400/121 ㎡ |
| 「층고」 | placeholder `4.5`, 단위 「m」 | 1.8~20 m 허용 |
| 「도면 · 사진」 「파일 첨부」 | PDF·PNG·JPG·HEIC, 여러 개 | R1 로 BE1D / BE1P |
| 주 버튼 「배치될 제품 입력」 | — | 설명·파일 중 하나 이상 있어야 활성 → `space:analyze` job → BE2 |

- 면적·층고 칸이 비어 있으면 설명에서 읽고, 설명에도 없으면 공간 유형 기본값(§10.3)을 `estimated` 로 쓴다. 칸 값이 설명과 다르면 칸 값이 우선.
- 여러 줄 = 여러 공간: 도면이 없으면 줄 순서대로 공간 사각형을 가로로 붙여 하나의 평면으로 만든다(공간 사이 벽 0.2 m, 연결 문 1개 가정).
- 시나리오에서 왔으면 설명·공간 유형을 시나리오 공간으로 채운다. 이미지에서 왔으면 참조 이미지 칩을 파일 첨부 옆에 보인다.

### 4.3 BE1D · 도면 인식 확인
- 파일 칩: 「{파일명}」 「{쪽}쪽 · {크기}」 (예 「lobby_plan_1F.pdf」 「1쪽 · 2.4 MB」). 여러 쪽이면 첫 쪽을 쓰고 **(신규)** 쪽 선택 드롭다운.
- W: 「도면에서 공간 구조를 읽었습니다. 벽 · 창 · 문 · 기둥이 표시한 대로 맞는지 보시고, 확인이 필요한 {k}곳({항목 이름 나열})을 정해 주세요.」 (예 「… 확인이 필요한 두 곳(정면 폭 치수, 뒤쪽 문)을 정해 주세요.」; k=0 이면 **(신규)** 「… 맞는지 보시고 계속해 주세요.」). 인식 중 **(신규)** 「도면을 읽고 있어요」.
- 캔버스: 「인식 결과」 「축척 1:{s} 감지 · 면적 {㎡} ㎡ (약 {평}평)」 (예 「축척 1:100 감지 · 면적 396 ㎡ (약 120평)」), 스위치 「원본 겹쳐 보기」(켜짐 = 원본 도면 위에 인식 벡터), 확대/축소(「100%」). 요소를 누르면 캔버스에서 강조.
- 「인식한 요소」 「{종류 수}종 · 확인 {k}」:

| 요소 | 요약 문구 규칙(보드 예) | 확인 항목 |
|---|---|---|
| 「벽」 | 「외벽 {n}면」 (+ 내벽 있으면 「 · 내벽 {m}」) | — |
| 「창」 | 「{위치 라벨} {n}구간」 (「전면 유리창 2구간」) | — |
| 「문」 | 「주출입구 {a} · {위치}쪽 문 {b}」 (「주출입구 1 · 뒤쪽 문 1」) | 종류 불확실 문마다 질문 「{위치}쪽 문은 어떤 문인가요?」 + 「비상구」 「백오피스 출입」 「벽으로 처리」 |
| 「기둥」 | 「{n}개 · {w} × {d} mm」 (「2개 · 600 × 600 mm」, 크기가 다르면 「{n}개 · 크기 다름」) | — |
| 「코어」 | 「EV · 계단 · 배치 제외」 (있는 것만 나열) | — |
| 치수 | 「치수 보정 · {라벨}」 「도면 표기 {a} m · 축척 1:{s} 환산 {b} m」 | 「표기값 {a} m」(기본 선택) 「환산값 {b} m」 「직접 입력」(m 입력칸) |

- 확인 항목 배지는 번호(치수 보정 → 1, 문 → 2 …: 치수 먼저). 질문에 답하면 배지가 체크로.
- 작업 카드 머리 「공간 인식 확인」 「· 확인 필요 {k} · 1 / 5」. 버튼 「다시 인식」(같은 파일 재처리), 「다른 도면 올리기」, 「현장 사진 더하기」(→ BE1P, 같은 작업).
- 입력: 라벨 「말로 고치기」, placeholder 「말로 고치기 (예: 오른쪽 기둥은 철거됐어, 창은 끝까지 유리야)」 → LLM 이 공간 모델 연산(요소 삭제·추가·종류 변경·치수 지정)으로 바꿔 적용 → 목록·캔버스 갱신.
- 버튼: 「이전」(→ BE1), 주 버튼 「이 구조로 계속」(→ BE2). 미해결 항목이 있어도 계속 가능 — 안전 기본값 적용 후 가정 목록에 기록(BE5G 「확인 필요」에 다시 보임).
- 치수 선택 효과: 「표기값」 = 전체 좌표에 `a ÷ b` 배율, 「환산값」 = 그대로, 「직접 입력」 = `입력 ÷ b` 배율. 면적·요약 문구가 즉시 다시 계산된다.
- 상태: 기밀 차단(ai-tools `POLICY_CONFIDENTIAL`) → 벡터/영상 처리 결과만 보이고 **(신규)** 「고객 도면이라 외부 모델 없이 기본 인식만 했어요」. bbox 미지원 래스터 → 외곽을 사각형으로 단순화하고 **(신규)** 「도면 모양을 사각형으로 단순화했어요 · 말로 고쳐 주세요」.

### 4.4 BE1P · 현장 사진으로 입력
- 메아리: BE1 설명(예 「관제실 리뉴얼이에요. 정면 상황판 교체가 핵심이고 운영석은 2열입니다.」).
- W: 「사진 {n}장에서 {공간 이름} 구조를 읽고 있습니다.」 + 상황 문장(보드 예: 「창 쪽 사진은 역광으로 창 위치가 흐리니 다시 찍어 주시고, 천장 사진을 더하면 층고를 더 정확히 잡을 수 있습니다.」). 상황 문장은 문제 사진·천장 없음 여부로 고르는 템플릿 조합.
- 촬영 가이드 카드: 「촬영 가이드」, 「위에서 본 모습」(방향 도식), 「· 모서리에 서서 맞은편 벽까지 담기」 「· 가로로, 사람이 적을 때 찍기」 「· 창이 있는 벽은 역광 피하기」 「· 바닥에 A4 용지를 두면 치수 보정」. 「찍은 방향」 「{k} / 4」 「· 천장 없음」(천장 사진이 있으면 뒷부분 생략). QR + 「휴대폰으로 QR을 찍으면」 「이 작업에 바로 올라가요」.
- 사진 목록 머리 「사진 {n}장」 「인식 완료 {a} · 확인 필요 {b} · 인식 중 {c}」, 버튼 「사진 추가」.

| 사진 카드 상태 | 문구 | 판정 |
|---|---|---|
| 인식 완료 | 「인식 완료 · {찾은 요소}」 (「인식 완료 · 벽 · 상황판」, 「인식 완료 · 출입문 1」) | i2t 결과 정상 |
| 역광 | 「역광 · 창 위치가 흐려요」 + 「다시 찍기」 「그대로 사용」 | 밝은 영역(휘도 > 0.85) 비율 > 25% 이고 그 밖 평균 < 0.30 |
| 어두움 | **(신규)** 「어두워요 · 다시 찍기 권장」 + 같은 두 버튼 | 휘도 평균 < 0.22 |
| 흐림 | **(신규)** 「흔들렸어요 · 다시 찍기 권장」 + 같은 두 버튼 | 라플라시안 분산 < 50 |
| 인식 중 | 「인식 중 · {단계}」 (「인식 중 · 벽 경계 찾는 중」) | job 진행 |
| 실패 | **(신규)** 「인식하지 못했어요 · 다시 인식」 | i2t 오류 |

- 카드 제목 = i2t 가 붙인 벽 이름(「상황판 벽」 「왼쪽 벽」 「창 쪽 벽」 「출입구 쪽」), 번호 = 올린 순서. 「다시 찍기」 = 그 칸 교체 업로드, 「그대로 사용」 = 낮은 신뢰도로 포함.
- 천장 카드: 「천장 사진」 「없음 · 층고는 추정값」 「+ 추가하기」 (있으면 **(신규)** 「있음 · 층고 {h} m」).
- 드롭 영역: 「사진 끌어 놓기」 「JPG · PNG · HEIC」 (20MB/장, 최대 12장; 다른 형식은 **(신규)** 「JPG · PNG · HEIC만 올릴 수 있어요」).
- 요약: 「지금까지 파악한 공간」 「· 사진 {k}장 기준」(k = 인식 완료 + 그대로 사용), 칩: 「약 {평}평 추정」, 「층고 {h} m 추정」, 사실 칩(LLM 이 사진·설명에서 뽑은 것, 예 「상황판 벽 폭 약 9 m」 「운영석 2열」).
- 작업 카드 머리 「현장 사진」 「· {n}장 · 1 / 5」, 버튼 「휴대폰으로 올리기」(QR 팝오버), 「도면도 있어요」(→ BE1D).
- 입력: 라벨 「사진에 없는 정보」, placeholder 「사진에 없는 정보 (예: 상황판 벽 폭 9m, 운영석 2열 12석)」 → 사실 칩·공간 모델 반영(사용자 값은 추정값보다 우선).
- 버튼: 「이전」(→ BE1), 주 버튼 「이 사진으로 계속」(인식 완료 또는 그대로 사용 사진 ≥ 1 일 때 활성 → BE2).
- **QR 업로드**: `POST /v1/birdseyes/{id}/upload-tokens` → 30분 유효 토큰 URL `{PUBLIC_BASE_URL}/m/upload/{token}`(QR). 모바일 페이지 `/m/upload/:token`(웹 경량 페이지): 카메라/앨범 선택 → files 업로드(토큰 인증) → `POST /v1/upload-tokens/{token}/photos {file_id}` → 인식 job → BE1P 에 SSE 로 카드 추가. 휴대폰이 사내망(PC 와 같은 망)에 있어야 한다(§11).

### 4.5 BE2 · 배치될 제품 (2/5)
- 메아리: 공간 설명 + 첨부 파일 칩(예 「lobby_plan_1F.pdf」).
- W: 「{공간 이름} 공간을 파악했습니다. {특징 문장들}. 이 공간에 배치할 삼성 제품을 입력해 주세요.」 — 특징 문장은 공간 특징 → KB `C1`(공간·요구 → 역량) 결과로 고르는 템플릿(보드 예: 「전면 유리창은 외부 노출이 큰 만큼 고휘도 사이니지가 어울리고, 기둥 2개는 랩핑형 디스플레이 포인트로 쓸 수 있습니다.」). 분석 중 **(신규)** 「공간을 파악하고 있어요」.
- 요약 칩: 「{평}평 · 층고 {h}m」, 「{특징} ({역량 권장})」(「전면 유리창 (고휘도 권장)」), 「중앙 기둥 {n}개」. 추정값이면 칩 끝에 **(신규)** 「· 추정」.
- 작업 카드 머리 「배치될 제품」 「· {n}개 추가됨 · 2 / 5」. 버튼 「제품 탐색에서 고르기」(상단바 제품 탐색, 드롭 `accepts=['product']`).
- 검색: 라벨 「제품명 입력」, 입력 중 결과 머리 「"{q}" 검색 결과 · Enter로 추가」, 최대 5행: 제품군 이름(입력과 일치하는 부분 굵게), 줄 「{카테고리} · {크기 옵션 ' / '} · {핵심 특징}」(예 「LED 사이니지 · 110" / 146" · Micro LED」), 포커스 행에 「추가 ↵」. Enter = 포커스 행 추가.
- 추가된 칩: 「{표시명}」 + 제거(aria 「제거」) (예 「Outdoor Signage OH55C」, 「Flip Pro WA75D」).
- 안내 「수량과 위치 메모는 4단계 배치 컨펌에서 조정합니다」.
- 버튼: 「이전」(→ BE1), 주 버튼 「가구 추천 받기」(제품 ≥ 1 일 때 활성 → 가구 추천 job → BE3).
- 크기 옵션이 있는 제품(예 The Wall IAB 110"/146")은 여기서 묻지 않는다 — 엔진이 정하고(§7.6) BE4 라벨에 크기를 쓴다.

### 4.6 BE3 · 가구 추천 (3/5)
- 메아리: 「제품 {n}개 · {표시명 ' / '}」 (예 「제품 3개 · Outdoor Signage OH55C / Flip Pro WA75D / The Wall All-in-One IAB」).
- W: 「공간 특징과 제품 배치를 살리는 가구를 추천합니다. {핵심 가구 요약}이 핵심입니다. 넣을 가구를 고르거나 직접 추가하세요.」 (보드 예: 「유리창 앞 라운지, 기둥 랩핑 프레임, The Wall 앞 관람 벤치」).
- 추천 카드 4개(다중 선택, 상위 3개 기본 선택): 이름 + 이유 줄 「{앵커 위치} · {목적}」 — 보드 예: 「라운지 소파 세트」 「유리창 앞 · 외부 시선 유도」, 「기둥 랩핑 프레임」 「기둥 2개 · 사이니지 매립」, 「관람 벤치 (3열)」 「The Wall 정면 · 시청 거리 6m」, 「체험 카운터」 「Flip Pro 앞 · 상담·시연」. 시청 거리 같은 수치는 엔진이 계산(§7.6)해 넣는다.
- 작업 카드 머리 「선택된 가구」 「· {n}개 · 3 / 5」. 버튼 「다른 가구 추천」(보인 것 제외 다음 4개), 「가구 없이 진행」(가구 0 으로 배치 job → BE4).
- 선택 칩: 「{이름}{ ×qty}」 + 「×」 (예 「라운지 소파 세트 ×」, 「기둥 랩핑 프레임 ×2 ×」, 「관람 벤치 (3열) ×」). 기둥 랩핑 수량 = 기둥 수.
- 입력: 라벨 「가구 직접 입력」, placeholder 「가구를 직접 입력해 추가 (예: 화분, 안내 데스크)」 → 카탈로그 일치(별칭·LLM) → 없으면 사용자 가구(기본 1.0×0.6×0.8 m, **(신규)** 칩 꼬리 「· 치수 추정」).
- 버튼: 「이전」(→ BE2), 주 버튼 「배치안 보기」(→ 배치 job → BE4).

### 4.7 BE4 · 배치 · 인테리어 컨펌 (4/5)
- W: 「배치안입니다. 평면도 위의 제품·가구는 드래그해서 옮길 수 있고, 인테리어 톤을 고르면 3D 생성 시 마감재와 조명에 반영됩니다.」 배치 생성 중 **(신규)** 「배치안을 만들고 있어요」.
- 2D 배치안(SVG, 엔진 좌표 그대로): 외곽·벽·창(라벨 「{창 라벨}」, 예 「전면 유리창 (도로측)」), 오른쪽 위 「{평}평 · {h}m」, 기둥(회색 사각), 제품(파랑 채움, 라벨 `{약칭}{ ×qty} ({앵커 라벨})` — 「OH55C ×3 (창면)」 「The Wall IAB 146" (후면 벽)」 「Flip Pro WA75D (측벽)」), 가구(점선, 라벨 「라운지 소파 세트」 「관람 벤치 3열」 「안내 데스크」), 기둥 랩핑(파랑 테두리, 라벨 「기둥 랩핑 ×2」). 범례 「삼성 제품」 「가구」 「기둥」.
- 항목을 끌기 시작하면 BE4E(직접 수정 모드)로 전환된다(끌던 항목 유지).
- 남은 경고가 있으면 배치안 아래 **(신규)** 링크 「경고 {n} · 직접 수정에서 보기」(→ BE4E).
- 작업 카드 머리 「배치 · 인테리어 컨펌」 「· 4 / 5」.

| 컨트롤 | 값 |
|---|---|
| 「인테리어 톤」 | 「웜 우드」(기본, 견본색 #d9c3a5) 「모던 화이트」(#eeeeee) 「다크 메탈」(#2b2f36) |
| 「시점」 | 「조감 (45°)」(기본) 「입구 시점」 |
| 「배치 수정 요청」 | placeholder 「배치 수정 요청 (예: 관람 벤치를 2열로 줄이고 The Wall 쪽으로 붙여줘)」 → LLM 레이아웃 연산 → 엔진 적용·검증 → 배치안 갱신(새 레이아웃 버전) |
| 버튼 | 「이전」(→ BE3), 주 버튼 「이 배치로 3D 생성」(→ 렌더 job → BE5G) |

### 4.8 BE4E · 배치 직접 수정
- W: 「직접 수정 모드입니다. 제품과 가구를 끌어서 옮기면 시야각 · 동선 · 전원 위치를 바로 다시 확인하고, 문제가 생긴 곳을 번호로 표시합니다.」
- 도구(role group 「편집 도구」): 「이동」(기본) 「회전」(15° 단위, 벽과 평행에 스냅) 「치수 재기」(두 점 거리 m, 0.1 단위). 「표시」 토글: 「시야각」(켬) 「동선」(켬) 「전원 위치」(켬) 「치수」(끔). 「변경 {n} 건」, 되돌리기(aria 「되돌리기」) / 다시 실행(aria 「다시 실행」).
- 캔버스: BE4 배치안 + 옮긴 항목의 원래 자리 유령(라벨 「원래 위치」)과 이동 라벨 「{방향어} {d} m」(예 「오른쪽으로 3.0 m」; 두 축 모두 0.3 m 이상이면 **(신규)** 「오른쪽 2.0 m · 위 1.0 m」), 경고 번호 표식(①②③). 범례 「삼성 제품」 「가구」 「시야각」 「동선」 「전원」 「경고」. 시야각 = 디스플레이별 허용 부채꼴(±최대 각, 최소~최대 시청 거리), 동선 = 주 동선 경로와 병목, 전원 = 콘센트 점과 연결선.
- 패널 머리 「배치 직접 수정」 「· 경고 {n} · 4 / 5」, 버튼 「경고 모두 자동 조정」.

| 경고 종류 | 제목 | 문구 템플릿(보드 예) | 동작 버튼 |
|---|---|---|---|
| 시야각 `viewing_angle` | 「시야각」 | 이동이 원인: 「{디스플레이}을 {방향어} {d} m 옮겨 {좌석 묶음} {왼쪽\|오른쪽} {k}석이 시야각 밖이에요」 (「The Wall을 오른쪽으로 3.0 m 옮겨 관람 벤치 왼쪽 2석이 시야각 밖이에요」). 그 외 **(신규)** 「{좌석 묶음} {쪽} {k}석이 {디스플레이} 시야각 밖이에요」 / 거리 **(신규)** 「{좌석 묶음}이 {디스플레이}에서 {d} m · 권장 {a}~{b} m」 | 「{좌석 묶음 약칭} 함께 옮기기」(「벤치 함께 옮기기」) · 「무시」 |
| 동선 `walkway` | 「동선」 | 「{A}와 {B} 사이 통로 {w} m · 권장 1.2 m 이상」 (「라운지 소파와 기둥 사이 통로 0.6 m · 권장 1.2 m 이상」) | 「{움직일 항목 약칭} {방향어} {Δ} m」(「소파 위로 0.6 m」) · 「무시」 |
| 전원 `power` | 「전원」 | 「{제품 묶음}에서 가까운 콘센트까지 {d} m · 바닥 배선 필요」 (「OH55C ×3에서 가까운 콘센트까지 6.0 m · 바닥 배선 필요」). 콘센트 정보 없음 **(신규)** 「{제품 묶음} 근처 전원 위치를 몰라요」 | 「전원 위치 추가」(배치안을 눌러 콘센트 추가 → 재검증) · 「메모로 남기기」 |

- 각 경고 카드에 규칙 툴팁(**(신규)**): `{rule_id} · {식} · 파라미터 {값} (draft)`.
- 「경고 모두 자동 조정」: 시야각·동선 경고는 첫 번째 수정안을 순서대로 적용(적용 후 새 경고가 생기는 수정안은 건너뜀), 전원 경고는 「메모로 남기기」로 처리.
- 입력: 라벨 「말로 수정」, placeholder 「말로 수정 (예: The Wall을 다시 가운데로, 벤치는 2열로)」.
- 버튼: 「취소」(편집 세션 버림 → BE4), 주 버튼 「수정 적용」(세션 커밋 → 새 레이아웃 버전 → BE4).
- 편집 세션: 화면 진입 시 레이아웃 작업본 생성, 끌기 끝·회전 끝마다 동기 검증(`layout:validate`, ≤ 200ms). 「변경 {n} 건」 = 세션에서 적용된 연산 수(되돌린 것 제외).

### 4.9 BE5G · 생성 중
- 메아리: 「이 배치로 3D 생성 · {톤} · {시점}」 (예 「이 배치로 3D 생성 · 웜 우드 · 조감 45°」).
- W: 「배치안을 3D로 만들고 있어요. {끝난 단계 요약}까지 끝났고, 지금 {현재 단계 동작} 중입니다. 다른 작업을 해도 계속 진행되고, 끝나면 알려드릴게요.」 (보드 예: 「공간 구조와 제품 배치까지 끝났고, 지금 가구와 마감재를 입히는 중입니다.」).
- 진행 카드(누르면 BE5 — 완료 후만): 「3D 조감도 생성 중」 「{pct}%」 「· 약 {m}분 남음」, 줄 「{시점} · {톤} · {해상도} · 제품 {p}종 · 가구 {f}종」(예 「조감 45° · 웜 우드 · 3840×2160 · 제품 3종 · 가구 4종」).

| 단계 | 메모 템플릿(보드 예) | 상태 문구 |
|---|---|---|
| 「공간 구조」 | 「{평}평 · 층고 {h}m · {특징 ' · '}」 (「120평 · 층고 4.5m · 전면 유리창 · 기둥 2개」) | 「완료」/「진행 중」/「대기」 |
| 「제품 배치」 | 제품 라벨 나열 (「OH55C ×3 · The Wall IAB 146" · Flip Pro WA75D」) | 〃 |
| 「가구 · 마감재」 | 가구 약칭 + 톤 (「라운지 소파 · 기둥 랩핑 · 관람 벤치 · 안내 데스크 · 웜 우드」) | 〃 |
| 「조명 · 렌더링」 | 「{조명 설명} · {해상도}」 (「주간 자연광 · 3840×2160」) | 〃 |
| 「품질 확인」 | 「제품 비율 · 겹침 · 로고 노출 점검」 | 〃 |

- 안내 「중지해도 끝난 단계까지는 초안으로 저장돼요」.
- 「기다리는 동안 미리보기」: 로컬 초안 렌더(§7.7) — 라벨 「마감재 적용 전」 「초안 · {시점}」, 진행 띠 「{현재 단계 동작} 중」(「가구 · 마감재 입히는 중」). 「제품 배치」 단계가 끝나면 나타난다.
- 「끝나면 이어서 만들 컷 · 대기열 {n}」: 번호, 컷 이름(「조감 45° · 야간」, 「도입 전 · 조감 45° (비교용)」), 「대기」, 빼기(aria 「대기열에서 빼기」). 링크 「시점 · 조명 컷 추가」(→ BE5V).
- 확인 필요 상자(가정이 있을 때): 「!」 「확인 필요」 「· {가정 문장}」(보드 예: 「· 도면에 후면 벽 폭이 없어 The Wall 크기는 146" 비율로 맞췄어요.」) + 동작 링크(치수 가정이면 「벽 치수 보정」 → BE1D).
- 하단 머리 「3D 조감도 생성 중」 「· 5 / 5 · 다른 작업을 해도 돼요, 끝나면 알려드릴게요」.
- 입력: 라벨 「진행 중 요청」, placeholder 「진행 중에도 요청을 남겨주세요 (예: 로비에 사람 실루엣 몇 명 넣어줘)」 → jobs 조종 메모(§7.8).
- 버튼: 「작업 목록으로」(→ BE0, 생성 계속), 「중지」(job 취소 → 끝난 단계까지 초안 컷 저장 → BE4).
- 실패 **(신규)**: W 「조감도를 만들지 못했어요. {사유}」 + 「다시 시도」 + 「배치로 돌아가기」(→ BE4). 완료: 완료 알림 **(신규)** 「{작업 제목} · 3D 조감도 완성」(링크 BE5). 화면이 열려 있으면 BE5 로 자동 이동한다.

### 4.10 BE5 · 3D 조감도 (5/5)
- W: 「3D 조감도가 완성되었습니다. {톤} 톤, {시점 구} 시점이며 제품 {p}종과 가구 {f}종이 배치안대로 반영되었습니다.」 (시점 구: 조감 45° → 「45° 조감」, 입구 → 「입구」, 제품 정면 → 「{제품} 정면」, 탑뷰 → 「탑뷰」). 품질 확인이 `check` 면 문장 끝에 **(신규)** 「 일부 제품 위치가 배치안과 다를 수 있어요.」
- 이미지: 주 컷(uhd), 태그 「{시점}」 「{톤}」 「{해상도}」(예 「조감 45°」 「웜 우드」 「3840×2160」), 「확대」 「다운로드」(aria) 버튼. 이미지 영역 대체 텍스트 「3D 조감도 렌더 (생성 이미지 영역)」.
- 컷 썸네일: 완료 컷 목록(라벨 = 주 시점과 다르면 시점, 조명만 다르면 조명: 「조감 45°」 「입구 시점」 「야간」). 누르면 주 이미지 전환(`?cut=`). 진행 중 컷은 진행률 표시. `stale` 컷은 「배치 변경 전」 배지.
- 제품 칩: 「{제품 라벨}」… + 「가구 {f}종」 (「OH55C ×3」 「The Wall IAB 146"」 「Flip Pro WA75D」 「가구 4종」).
- 작업 카드 머리 「3D 조감도」 「· 5 / 5 · 완료」. 링크 「다른 시점 추가」(→ BE5V), 「톤 바꿔 재생성」(→ BE5V 톤 모드, §4.11), 「배치 수정」(→ BE4E).
- 입력: 라벨 「수정 요청」, placeholder 「수정 요청 (예: 조명을 더 따뜻하게, 사람 실루엣 추가)」 → R8 라우팅.
- 버튼: 「저장」(버전 스냅샷 → **(신규)** 토스트 「저장했어요 · v{n}」), 주 버튼 「제안서에 넣기」(→ BE6).

### 4.11 BE5V · 시점 · 조명 바꾸기
- 메아리 예: 「야간 컷이랑 도입 전후 비교도 만들어줘. 입구에서 본 시점도.」(자유 요청으로 들어온 경우).
- W: 「배치는 그대로 두고 카메라와 조명만 바꿨어요. 도입 전 컷은 같은 시점에서 제품과 가구를 뺀 모습이라 지금 {공간 이름}와 나란히 비교할 수 있습니다.」 (요청 없이 들어오면 **(신규)** 「배치는 그대로 두고 카메라와 조명만 바꿔 새 컷을 만들어요.」).
- 비교 영역: 왼쪽 「도입 전 · 현재 {공간 이름}」 「제품 · 가구를 뺀 같은 시점」, 오른쪽 「도입 후 · {시점} {조명}」(예 「도입 후 · 조감 45° 주간」). 보기 전환: 「나란히」(기본) 「겹쳐 밀기」(슬라이더) 「주간 / 야간」(같은 시점의 주간·야간 컷 비교). 비교할 컷이 없으면 해당 보기 비활성.
- 「만든 컷」 「· {n}」, 「테두리 표시된 2컷을 비교 중」. 컷 행: 「원본」 배지(첫 주 컷), 이름(「조감 45° · 주간」), 상태(「비교 중 · 도입 후」 「완료 · 방금」 「비교 중 · 도입 전」 「생성 중」 「{p}%」 「대기열 {k}」 「대기」).
- 작업 카드 머리 「시점 · 조명 바꾸기」 「· 5 / 5 · 새로 만들 컷 {N}」. 링크 「전/후 2컷을 제안서 '두 시점 비교'로」(→ BE6, BV-B 매핑 선택).

| 컨트롤(다중) | 값 |
|---|---|
| 「시점」 | 「조감 45°」 「입구 시점」 「{대표 제품} 정면」(「The Wall 정면」 — 배치에서 가장 큰 디스플레이) 「탑뷰」 |
| 「조명」 | 「주간」 「저녁」 「야간」 |
| 「도입 전 컷도」 | 토글(끔) |
| 「시점 설명」 | placeholder 「원하는 시점을 말로 설명해도 돼요 (예: 2층 난간에서 내려다본 시점)」 → LLM 카메라 JSON(§7.7) → 사용자 시점 1개로 추가 |

- 새로 만들 컷 수 `N = (선택 시점 수 + 시점 설명 1) × 선택 조명 수 × (도입 전 컷도 ? 2 : 1)` — 이미 있는 같은 컷(같은 레이아웃 버전·시점·조명·전후)은 빼고 센다. 보드 예: 입구 시점 + The Wall 정면, 야간 → 「새로 만들 컷 2」.
- 버튼: 「결과로」(→ BE5), 주 버튼 「선택한 {N}컷 생성」(→ 컷 job 들을 대기열에 넣고 BE5G, N=0 이면 비활성).
- **톤 모드**(BE5 「톤 바꿔 재생성」으로 들어올 때): 시점 줄 위에 BE4 와 같은 「인테리어 톤」 칩 줄(「웜 우드」 「모던 화이트」 「다크 메탈」)을 보이고, 고른 톤으로 현재 주 컷과 같은 시점·조명을 다시 만든다(§11 디자인 확인).

### 4.12 BE5Z · 존 포인트 지정
- W: 「조감도 위에 존 포인트 {n}곳을 찍어 두었어요. 번호를 끌어 위치를 옮기고, 빈 곳을 누르면 포인트가 추가됩니다. 여기 적은 문구가 제안서 '존별 포인트' 시트에 그대로 들어가요.」
- 이미지: 기준 컷(기본 주 컷, 라벨 「조감 45° · 주간」) 위 번호 원. 모드 버튼 「포인트」(활성), 도움말 「빈 곳을 눌러 추가 · 번호를 끌어 이동」.
- 제안서 미리보기 카드: 「공간마다 무엇이 달라지나」 「제안서 미리보기」 「조감도 · 존별 포인트 시트」 「{시트 코드}」 「{레이아웃 이름} · 포인트 {n}곳」 「{제안서 제목} · {시트 번호}번」 (보드 예: 「ZP-A」 「번호 콜아웃 · 포인트 4곳」 「A 커피 프랜차이즈 메뉴보드 제안 · 9번」). 연결된 제안서가 없으면 마지막 줄 **(신규)** 「연결된 제안서 없음」. 시트 번호는 웹이 제안서 계약으로 조회한다.
- 「존 포인트」 「· {n}」, 버튼 「동선 순서로 번호」. 존 카드(하나만 펼침): 번호, 「존 이름」 입력(예 「쇼윈도 · 외부 노출」, ≤ 14자), 「포인트 문구」 textarea(예 「도로에서도 보이는 창면 사이니지로 지나가는 고객을 매장 안으로 끌어들입니다」, ≤ 60자), 「연결」 칩(제품 「OH55C ×3」, 공간 특징 「전면 유리창」, 요구 「요구: 외부 유입」). 접힌 카드: 번호 · 이름 · 문구 한 줄(「라운지 · 체류」 「창가 라운지에서 머무는 시간을 늘려 브랜드 경험으로」, 「미디어 월 · 관람」 「The Wall 앞 관람 벤치에서 브랜드 영상에 몰입」, 「상담 · 시연」 「Flip Pro에 상담 내용을 바로 그려 보이는 시연 공간」). 「+」 = 포인트 추가(이미지 중앙에 놓고 끌기).
- W 제안 카드(덮지 못한 배치 군집이 있을 때): 「W 제안 · {제안 이름}」 「{대상}를 {k}번 포인트로 넣을까요?」 (「W 제안 · 기둥 랩핑 길 안내」 「기둥 2개를 5번 포인트로 넣을까요?」) + 「{k}번으로 추가」 「넘기기」.
- 작업 카드 머리 「존 포인트 지정」 「· {n}곳」, 「시트 레이아웃」: 「번호 콜아웃」(기본, ZP-A) 「존 확대 컷」(ZP-B) 「고객 동선 따라가기」(ZP-C).
- 입력: 라벨 「포인트 문구 수정 요청」, placeholder 「문구 다듬기 (예: 4곳 모두 고객 관점의 한 문장으로)」 → LLM 문구 재작성(선택 존 또는 전체).
- 버튼: 「결과로」(→ BE5), 주 버튼 「제안서 '존별 포인트'로」(→ BE6 의 제안서 보내기, ZP 매핑만 선택된 상태로 바로 보내기 확인).
- '요구' 연결 칩은 이 작업의 입력 문장(공간 설명·요청)에서 LLM 이 뽑은 요구 태그다(요구사항 서비스는 호출하지 않음 — §11).
- 장면 연결 모드(`?scenario=sc_…`, 시나리오 SC4 「조감도 추가」·SC5 「조감도 존에 장면 연결」에서 진입): 웹이 시나리오 계약으로 장면 목록을 읽어 존 카드의 「연결」에 **(신규)** 「장면 {n}」 칩을 고를 수 있게 한다. 저장은 존의 `links(kind='scene')`. 「결과로」 대신 **(신규)** 「시나리오로 돌아가기」.

### 4.13 BE6 · 내보내기 · 보내기
- W: 「조감도 결과를 내려받거나 다른 작업으로 보낼 수 있어요. 이미지와 함께 배치안의 제품 수량표가 넘어가고, 수량은 배치안 기준이라 견적 전에 한 번 확인해 주세요.」

**이미지** 「이미지」 「{k}」 「/ {n} 선택」 — 항목(체크박스 + 썸네일 + 이름 + 부제):
| 항목 종류 | 이름 / 부제(보드 예) | 기본 선택 |
|---|---|---|
| 주 컷 | 「조감 45° · 주간」 / 「원본 · 3840×2160」 | 예 |
| 주 시점의 다른 조명 컷 | 「조감 45° · 야간」 / 「3840×2160」 | 예 |
| 전후 비교 합성(도입 전·후 컷이 있을 때) | 「도입 전 / 후 비교」 / 「2컷 · 나란히 한 장」 | 예 |
| 존 포인트 콜아웃 합성(존 ≥ 1) | 「존 포인트 콜아웃」 / 「번호 {n}곳 · 범례 포함」 | 예 |
| 다른 시점 컷 | 「입구 시점 · 주간」 / 「3840×2160」 | 아니오 |

- 「형식」 「PNG」(기본) 「JPG」 「PDF」(선택 이미지를 한 PDF 로), 「크기」 「원본」(3840×2160, 기본) 「FHD」(1920×1080).
- **제품 수량표** 「제품 수량표」 「배치안 기준 · Excel」, 표 「제품」 「위치」 「수량」: 제품 행 = 레이아웃의 제품 묶음(이름 = 제품 정식 표시명, 위치 = 앵커 위치 라벨) — 보드 예 「Outdoor Signage OH55C」 「쇼윈도 창면」 「3」, 「The Wall All-in-One IAB 146"」 「후면 벽」 「1」, 「Flip Pro WA75D」 「측벽 · 상담」 「1」; 가구 묶음 행(흐린 글자) 「가구 {종}종 (참고)」 「{존 약칭 ' · '}」 「{총 개수}」 (「가구 4종 (참고)」 「라운지 · 관람 · 안내」 「7」). 토글 「가구도 함께」(켬 — 엑셀에 가구 시트 포함), 「단가 · 견적은 넣지 않아요」(켬, 비활성 고정 — 가격 정보를 다루지 않음).
- **B2B 제안서로 보내기**: 「B2B 제안서로 보내기」 「{제안서 제목} · {유형}」(예 「A 커피 프랜차이즈 메뉴보드 제안 · 표준」) + 「바꾸기」(제안서 선택 팝오버). 매핑 행 `{from} → {to} {code}`:
  - 「조감 45° · 주간」 → 「조감도 · 공간 전경」 `BV-A` (주 컷)
  - 「도입 전 / 후」 → 「공간 전경 · 두 시점 비교」 `BV-B` (전후 쌍, 없으면 주간/야간 쌍, 둘 다 없으면 행 없음)
  - 「존 포인트 {n}곳」 → 「조감도 · 존별 포인트」 `ZP-A|ZP-B|ZP-C` (BE5Z 레이아웃)
  - 「제품 수량표」 → 「공간별 제품 · 수량표」 `SM-B`
  링크 「새 제안서로 시작」(→ PR1L, 이 조감도 연결), 「제안서에 넣기」(웹 → 제안서 가져오기, §8).
- 「공간 시나리오로 이어 만들기」 「존 {n}곳을 공간으로 가져와 장면을 만들어요」 「시작」(→ SC1B `?birdseye={id}`).
- 「Spec 시트 만들기」 「제품 {p}종으로 스펙 비교표를 만들어요」 「시작」(→ SP1, 제품 목록을 웹이 넘김).
- 「보기 전용 링크」 「팀원이 조감도와 수량표를 볼 수 있어요」 「링크 복사」(workspace 공유 링크 → 클립보드, **(신규)** 토스트 「링크를 복사했어요」).
- 하단 「내려받기」 「· 이미지 {k}장 · 수량표 1개 · ZIP」, 「파일 이름」 입력(기본 `{제목 공백 제거}_조감도_v{version}`, 예 「강남플래그십_1층로비_조감도_v1」) + 「.zip」. 버튼 「이전」(→ BE5), 주 버튼 「ZIP 내려받기」(export job → 완료 시 다운로드).
- 상태: 이미지 0개 선택이면 ZIP 에 수량표만(문구 「· 이미지 0장 · 수량표 1개 · ZIP」). 제안서 0건이면 보내기 카드에 **(신규)** 「진행 중인 제안서가 없어요」 + 「새 제안서로 시작」.

---

## 5. 데이터 모델 (`${DATA_DIR}/birdseye/birdseye.sqlite`)

### 5.1 표
```text
birdseye        id 'be_<ULID>' · owner · project_id? · customer_name? · title · space_label ('매장 로비')
                space_chip TEXT(store_lobby|meeting_office|classroom|hospital_waiting|hotel_room|control_room)
                space_types JSON ['lobby','sales_floor'] · description TEXT · area_input_pyeong REAL? · ceiling_input_m REAL?
                inputs JSON {description:bool, plan_file_ids:[…], photo_count:int}
                step INT(1..5) · status(in_progress|needs_check|done|failed) · tone(warm_wood|modern_white|dark_metal)
                default_view(aerial45|entrance) · version INT · layout_version INT · primary_cut_id?
                shared_scope(private|team) · shared_label? ('외식 영업팀 공유') · cloned_from? · origin JSON?
                zone_layout(ZP-A|ZP-B|ZP-C) · route · created_at · updated_at · deleted_at?
space_model     birdseye_id · version · json SpaceModel (§5.2) · source(description|plan|photos|mixed) · created_at
plan_file       id 'bep_' · birdseye_id · file_id · page INT · kind(vector_pdf|raster) · status(recognizing|recognized|failed)
                result JSON {elements, scale, dims, questions, confidence} · job_id
photo           id 'beh_' · birdseye_id · file_id · n INT · wall_label? · dir_slot(1..4|ceiling)? · status(recognizing|
                recognized|backlit|dark|blurry|failed|accepted) · quality JSON · i2t JSON · job_id
upload_token    token TEXT PK · birdseye_id · owner · expires_at · used_count
product_item    id 'bpi_' · birdseye_id · family_id · model_code? · display_name ('Outdoor Signage OH55C') · short ('OH55C')
                size_options JSON ['110"','146"'] · chosen_size? · dims_m {w,h,d} · dims_source(spec|computed|estimated)
                category · mount_default · order
furniture_item  id 'bfi_' · birdseye_id · catalog_code? · name · qty INT · reason · source(recommended|user|custom)
                dims_m {w,d,h} · dims_estimated BOOL · selected BOOL · rec_rank?
layout          birdseye_id · version INT · json Layout (§5.3) · created_by(engine|user|nl_edit) · parent_version · created_at
layout_session  id 'bes_' · birdseye_id · base_version · ops JSON [] · cursor INT · status(open|committed|discarded)
cut             id 'bec_' · birdseye_id · layout_version · view JSON {preset(aerial45|entrance|product_front|top|custom),
                target_item_id?, camera{pos[x,y,z], target[x,y,z], fov_deg, ortho:bool}, label}
                light(day|evening|night) · before BOOL · tone · status(queued|running|draft|done|check|failed|canceled)
                stale BOOL · progress REAL · stage · job_id · render_id? (image) · image_id? · version_id? (image)
                draft_file_id? · resolution ('3840×2160') · auto_queued BOOL · is_primary BOOL · created_at
zone_point      id 'bez_' · birdseye_id · n INT · name · text · links JSON [{kind(product|feature|need|scene), label, ref?}]
                anchor_m [x,y,z] · cluster_item_ids JSON · positions JSON {cut_id:[u,v]} · status(active|suggested|dismissed)
                path_order INT?
memo            id 'bem_' · birdseye_id · kind(power|layout|render) · text · ref · created_at
usage           birdseye_id · service(proposal|scenario) · ref · label · version · created_at
export          id 'bex_' · birdseye_id · items JSON · format · size · include_furniture BOOL · filename · job_id · file_id?
```

### 5.2 SpaceModel (단위 m, 평면 좌표: x → 오른쪽, y → 아래(화면 기준, 위 = 정면 쪽), 원점 = 외곽 bbox 왼쪽 위)
```json
{ "rooms": [{"id": "r1", "label": "1층 로비", "space_types": ["lobby"], "outline": [[0,0],[24.0,0],[24.0,16.5],[0,16.5]]}],
  "walls": [{"id": "w1", "a": [0,0], "b": [24.0,0], "thickness": 0.2, "kind": "exterior", "label": "정면"}],
  "openings": [{"id": "o1", "kind": "window", "wall_id": "w1", "offset": 1.0, "width": 10.0, "label": "전면 유리창 (도로측)", "faces_outdoor": true},
               {"id": "o3", "kind": "door", "wall_id": "w3", "offset": 2.0, "width": 0.9, "door_type": "unknown", "confidence": 0.4}],
  "columns": [{"id": "c1", "center": [8.2, 8.0], "w": 0.6, "d": 0.6}],
  "cores": [{"id": "k1", "polygon": [[20,12],[24,12],[24,16.5],[20,16.5]], "kinds": ["ev","stairs"]}],
  "power_points": [{"id": "p1", "pos": [0.2, 9.0], "source": "plan|user"}],
  "ceiling_h": {"value": 4.5, "estimated": false},
  "scale": {"ratio": 100, "source": "pdf_text|dimension|photo_estimate|default", "correction": 1.0169},
  "dims": [{"id": "d1", "label": "정면 폭", "annotated_m": 24.0, "computed_m": 23.6, "choice": "annotated|computed|manual", "manual_m": null}],
  "area_m2": 396.0, "features": [{"kind": "storefront_window", "label": "전면 유리창", "hint_cap": "cap_sunlight_readable"}],
  "assumptions": [{"kind": "dims_missing", "ref": "w3", "text_ko": "도면에 후면 벽 폭이 없어 …", "action": "BE1D"}],
  "estimated": false }
```

### 5.3 Layout
```json
{ "version": 3,
  "items": [{"id": "li1", "kind": "product|furniture|column_wrap", "ref": "bpi_…|bfi_…", "group_id": "g1",
             "label": "OH55C ×3 (창면)", "x": 6.0, "y": 0.5, "rot_deg": 180, "w": 1.24, "d": 0.08, "h": 0.72,
             "z": 1.2, "mount": "wall|floor|ceiling|column|window_facing", "anchor": {"type": "window", "target": "o1"},
             "qty_in_group": 3, "qty_source": "rule|user|suggested", "rule_id": "pr_menuboard_qty_by_counter|null",
             "faces": "li4|null", "seats": 0, "locked": false}],
  "groups": [{"id": "g1", "label": "OH55C ×3", "at_label": "쇼윈도 창면", "family_id": "fam_…", "qty": 3}],
  "warnings": [{"id": "wv1", "n": 1, "kind": "viewing_angle|walkway|power", "rule_id": "pr_warn_viewing_angle",
                "expr": "abs(viewer_angle_deg) > 45", "params": {"max_angle_deg": 45}, "param_status": "draft",
                "message_ko": "…", "subjects": ["li5","li7"], "fixes": [{"id": "f1", "label_ko": "벤치 함께 옮기기", "ops": [ … ]}],
                "status": "open|fixed|ignored|memo"}],
  "assumptions": [ … ], "engine_version": "be-engine/1" }
```
레이아웃 연산(`ops`): `{op:'move', item, dx, dy}`, `{op:'rotate', item, deg}`, `{op:'add', item}`, `{op:'remove', item}`, `{op:'set_qty', group, qty}`, `{op:'add_power', pos}`, `{op:'set_size', product, size}`. 연산은 엔진에서 결정적으로 적용·검증한다.

### 5.4 작업 색인(workspace)
`PUT /api/workspace/v1/items/{be_id}` `{feature:'birdseye', title, status:{code,label}, summary:'{고객사} · {공간 라벨} · {진행 상태}', route, project_id}` — 단계 이동·컷 완료·삭제 때마다. `route` = 현재 단계 화면(진행 중 렌더가 있으면 BE5G).

---

## 6. API 스케치 (`/v1`, 게이트웨이 `/api/birdseye/v1`)
공통 규약은 ARCHITECTURE §3(오류 형식, 목록 커서, 202 job, 버전).

### 6.1 작업
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `GET /v1/birdseyes` | `filter(all\|in_progress\|needs_check\|done)`, `in_proposal:bool`, `q`, `scope(mine\|team)`, `sort`, `limit`, `cursor` | `{items:[Row], counts:{all,in_progress,needs_check,done}, next_cursor}` |
| `POST /v1/birdseyes` | `{title?, space_chip?, description?, area_pyeong?, ceiling_m?, project_id?, origin?, prefill?:{products:[family_id], reference_image_version?}}` | 201 `Birdseye` |
| `GET /v1/birdseyes/{id}` · `PATCH` | `PATCH {space_chip?, description?, area_pyeong?, ceiling_m?, tone?, default_view?, zone_layout?, if_version}` | `Birdseye` · 409 |
| `GET /v1/birdseyes/{id}/version` | — | `{version, layout_version, updated_at, zones_hash}` (시나리오 변경 감지용, 가벼움) |
| `POST /v1/birdseyes/{id}:clone` | `{title?}` | 201 `{id, route}` |
| `POST /v1/birdseyes/{id}:save` | — | `{version}` · `GET /v1/birdseyes/{id}/versions` · `POST /v1/birdseyes/{id}/versions/{n}/restore` |
| `DELETE /v1/birdseyes/{id}` | — | 204(소프트 삭제) |

### 6.2 공간 입력
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `POST /v1/birdseyes/{id}/space:analyze` | — | 202 (설명·도면·사진 → 공간 모델, W 특징 문장) |
| `GET /v1/birdseyes/{id}/space` | — | `{model: SpaceModel, summary_chips:[…], w_message}` |
| `POST /v1/birdseyes/{id}/plans` | `{file_id, page?}` | 202 `{job_id, plan_id}` |
| `POST /v1/birdseyes/{id}/plans/{pid}:recognize` | — | 202 |
| `POST /v1/birdseyes/{id}/space/answers` | `{question_id, option:'emergency'\|'backoffice'\|'wall'}` 또는 `{dim_id, choice:'annotated'\|'computed'\|'manual', manual_m?}` | 200 `SpaceModel` |
| `POST /v1/birdseyes/{id}/space:nl-edit` | `{text}` | 202 (LLM 연산) |
| `POST /v1/birdseyes/{id}/photos` | `{file_id, replace_photo_id?, is_ceiling?}` | 202 `{job_id, photo_id}` · 415 `FILE_TYPE_UNSUPPORTED` |
| `PATCH /v1/birdseyes/{id}/photos/{phid}` | `{accept:true}` (그대로 사용) | 200 |
| `POST /v1/birdseyes/{id}/space/facts` | `{text}` (사진에 없는 정보) | 200 `{facts:[…], model}` |
| `POST /v1/birdseyes/{id}/upload-tokens` | — | 201 `{token, url, expires_at}` |
| `POST /v1/upload-tokens/{token}/photos` | `{file_id}` (토큰 인증) | 202 · 410 `TOKEN_EXPIRED` |

### 6.3 제품·가구
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `GET /v1/product-search` | `q`, `limit=5` | `{items:[{family_id, name, name_match:[s,e], subline, size_options}]}` (kb 결과를 표시용으로 가공) |
| `PUT /v1/birdseyes/{id}/products` | `{items:[{family_id, model_code?}]}` | `[ProductItem]` |
| `POST /v1/birdseyes/{id}/furniture:recommend` | `{exclude?:[codes]}` | 202 → 결과 `GET /v1/birdseyes/{id}/furniture` |
| `PUT /v1/birdseyes/{id}/furniture` | `{items:[{catalog_code?\|name, qty?, selected}], none?:bool}` | `[FurnitureItem]` |

### 6.4 레이아웃
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `POST /v1/birdseyes/{id}/layout:generate` | — | 202 (의도 LLM + 엔진 + 자동 조정) |
| `GET /v1/birdseyes/{id}/layout` | `version?` | `Layout` |
| `POST /v1/birdseyes/{id}/layout:validate` | `{base_version, ops}` | 200 `{items, warnings, assumptions}` (동기, ≤ 200ms, 저장 안 함) |
| `POST /v1/birdseyes/{id}/layout-sessions` | — | 201 `{session_id, base_version}` |
| `POST /v1/layout-sessions/{sid}/ops` | `{ops:[…]}` 또는 `{undo:true}`·`{redo:true}` | 200 `{layout, warnings, changes_count}` |
| `POST /v1/layout-sessions/{sid}/warnings/{wid}` | `{action:'fix', fix_id}`·`{action:'ignore'}`·`{action:'memo'}` | 200 |
| `POST /v1/layout-sessions/{sid}:autofix` | — | 200 |
| `POST /v1/layout-sessions/{sid}:commit` · `:discard` | — | 200 `{layout_version}` |
| `POST /v1/birdseyes/{id}/layout:nl-edit` | `{text, session_id?}` | 202 (LLM → ops → 엔진) |

### 6.5 컷(렌더)
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `POST /v1/birdseyes/{id}/cuts` | `{views:[{preset, target_item_id?}\|{custom_text}], lights:['day'\|'evening'\|'night'], before:bool, tone?}` | 202 `{cut_ids:[…], job_ids:[…]}` — 컷마다 job, 작업당 순차 |
| `GET /v1/birdseyes/{id}/cuts` | — | `[Cut]` (진행률·대기 순번 포함) |
| `POST /v1/cuts/{cut_id}:cancel` | — | 202 (대기 컷은 즉시 삭제, 진행 컷은 초안 저장 후 중지) |
| `POST /v1/birdseyes/{id}/result:edit` | `{text, cut_id}` | 202 `{route_hint:'render'\|'layout'\|'view', job_id}` |
| `PATCH /v1/cuts/{cut_id}` | `{is_primary:true}` | 200 |

### 6.6 존 포인트
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `POST /v1/birdseyes/{id}/zones:auto` | `{cut_id}` | 202 (군집·투영·문구) |
| `GET /v1/birdseyes/{id}/zones` | `cut_id` | `{points:[ZonePoint], suggestions:[…], preview:{code, layout_label}}` |
| `POST /v1/birdseyes/{id}/zones` | `{cut_id, u, v}` (빈 곳 클릭) 또는 `{from_suggestion}` | 201 `ZonePoint` |
| `PATCH /v1/zones/{zid}` | `{name?, text?, links?, u?, v?, cut_id}` | 200 |
| `DELETE /v1/zones/{zid}` · `POST /v1/birdseyes/{id}/zones:renumber-by-path` · `POST /v1/birdseyes/{id}/zones:rewrite {text, zone_ids?}`(202) | | |

### 6.7 내보내기·넘기기
| 메서드 · 경로 | 요청 | 응답 |
|---|---|---|
| `POST /v1/birdseyes/{id}/exports` | `{items:[{kind:'cut'\|'before_after'\|'zones_callout', ref}], format:'png'\|'jpg'\|'pdf', size:'original'\|'fhd', include_furniture:bool, filename}` | 202 `{job_id, export_id}` (ZIP: 이미지 + `수량표.xlsx` + `sources.json`) |
| `GET /v1/birdseyes/{id}/quantities` | — | `{rows:[{family_id, model_code?, name, at, qty, qty_source, rule_id?, memo?}], furniture_row:{label, at, qty}}` |
| `GET /v1/birdseyes/{id}/handoff` | `version?` | 제안서·시나리오용 묶음(§8) |
| `POST /v1/birdseyes/{id}/usages` · `DELETE …/usages/{service}/{ref}` | `{service, ref, label, version}` | 201 / 204 |

SSE 이벤트 `data`: `step {stage:'structure'|'products'|'furniture'|'render'|'qc', state, note}`, `progress {pct, eta_s}`, `preview {draft_file_id}`, `result {cut_id, version_id}`, `error`.

---

## 7. 워크플로 (LangGraph · 워커 `wm:q:birdseye`) 와 배치 엔진

### 7.1 공통
- 체크포인터 SQLite, `thread_id=job_id`, 노드 경계 취소 확인, 조종 메모 `wm:job:<id>:memos` 는 다음 노드 시작 때 반영.
- 고객 도면·현장 사진·고객 설명이 들어간 모든 ai-tools 호출은 `confidential:true`. 차단되면 §7.2 의 로컬 경로.
- 모델 호출은 해석(LLM JSON·i2t)과 문구에만 쓴다. 좌표·수량·검증은 엔진(§7.6)만 정한다.
- 동시성: 워커 2 job, 같은 조감도의 컷 job 은 순차(대기열). 렌더는 image 서비스 job 을 자식으로 만들고 그 SSE 를 따라간다(자식 id 를 cut 에 저장, 취소 전파).

### 7.2 모델 능력별 경로(네이티브 vs 대체)
| 기능 | 네이티브 | 대체 | 메타 |
|---|---|---|---|
| 도면 인식(벡터 PDF) | PyMuPDF 벡터·텍스트 추출(결정적) + i2t 로 요소 종류 보강 | i2t 불가: 벡터만(문 종류는 모두 질문) | `plan:vector_only` |
| 도면 인식(래스터) | OpenCV 벽 검출 + i2t JSON + bbox(창·문·기둥·코어·치수 글자) → IoU 병합 | bbox 미지원: i2t 개수·글자만 + 외곽 사각형 단순화 / i2t 불가: OpenCV 벽만 | `plan:raster_nobbox` |
| 현장 사진 인식 | 로컬 품질 검사 + i2t JSON(벽 이름·요소·크기 힌트·기준 물체 bbox) → LLM 종합 | i2t 불가: 품질 검사만 + 설명 기반 사각형 모델 | `photo:quality_only` |
| 공간 설명 해석 | LLM JSON | 정규식(평·㎡·m·기둥 n개·유리창·층) | `space:regex` |
| 가구 추천 | LLM(닫힌 카탈로그, 이유 줄) | 규칙 표(공간 특징·제품 → 가구) | `furniture:rules` |
| 배치·검증 | **엔진(항상 로컬)** | — | — |
| 배치 의도 | LLM JSON(앵커 어휘) | 규칙: 디스플레이 큰 순 → 가장 긴 빈 벽, 창 사이니지 → 창, 랩핑 → 기둥, 좌석 → 가장 큰 디스플레이 정면, 나머지 → 창 쪽 빈 영역 | `intent:rules` |
| 3D 조감도 | 로컬 초안 렌더 → image 렌더 API(초안 = 구조 참조 1순위 + 제품 단독컷) | 참조 미지원 + 편집 지원: `edit_of=초안` / 둘 다 미지원: 텍스트만(배치 일치 낮음 → 컷 `check`) / T2I 없음: 초안을 톤 색으로 칠한 이미지를 컷으로(**(신규)** 배지 「초안 렌더」) | `render:ref\|edit\|text\|draft_only` |
| 품질 확인 | image QC(제품 수·투영 박스 IoU ≥ 0.3·로고·얼굴) | bbox 미지원: 개수·로고만 | `qc:count_only` |
| 시점 설명 → 카메라 | LLM JSON(위치·목표·FOV) + 엔진 범위 제한 | 키워드 규칙(“위에서/내려다” → 높이 ↑, “입구” → entrance) | `camera:rules` |
| 존 포인트 위치 | 엔진 투영(정확) | 편집으로 기하가 바뀐 컷: i2t bbox 로 제품 위치 → 군집 매칭 / bbox 미지원: 수동 | `zones:bbox\|manual` |
| 문구(존·W 특징) | LLM(+ KB 메시지 근거) | 템플릿 | `text:template` |
| 업스케일 | image 서비스(uhd 렌디션) | 〃 | — |

### 7.3 그래프 `be.space_analyze`
`load_inputs → parse_description(llm.json: rooms[{label, space_types, area_pyeong?, ceiling_m?, features[{kind, count, label}]}]) → merge(plan 모델 > 사진 모델 > 설명, 사용자 칸 값 우선) → fill_defaults(§10.3, estimated) → capability_hints(kb C1(spaces, text) → 특징별 역량 → W 특징 문장·요약 칩) → save(space_model v+1) → END`.

### 7.4 그래프 `be.plan_recognize`
```text
fetch(files) → classify(vector_pdf | raster)
 vector: extract_paths(get_drawings) → walls(두꺼운 선·평행 2선 100~300mm) → openings(벽 틈 + 호=문 + 3선=창)
         → columns(채운 사각 ≥ 300mm) → text(축척 "1:100|S=1/100|SCALE", 치수 "24.0 m|24,000") → scale(용지 mm × 축척)
 raster: binarize → morph → hough → walls ; i2t.analyze(confidential, json+bbox?) → merge(IoU ≥ 0.5)
→ outline(가장 큰 닫힌 외곽) → area → dims_check(|표기−환산|/표기 > 1% → dims 질문)
→ door_types(라벨·i2t 신뢰도 < 0.6 → 질문, 위치어 = 주출입구 기준 앞/뒤/왼/오른)
→ summary(요소 문구 §4.3) → save(plan_file.result, space_model) → END
```

### 7.5 그래프 `be.photo_recognize` · `be.photo_aggregate`
- 사진별: `quality(휘도 평균·밝은 영역 비율·라플라시안 분산) → status(§4.4) → i2t.analyze(confidential: wall_label, features[{kind, count, bbox?}], is_ceiling, size_hints[{object:'A4'|'door'|'person', bbox}], est{wall_width_m?, ceiling_h_m?}) → save`.
- 종합(사진 추가·수락·정보 입력 때마다): `llm.json(모든 사진 결과 + 설명 + 사용자 사실) → {dir_slots, area_m2_est, ceiling_h_m_est, walls[{dir, width_m_est, features}], facts_ko[]}` → 사각형 공간 모델(가로 = 정면 벽 폭, 세로 = 면적 ÷ 가로, 없으면 1.5:1) `estimated=true`. 천장 사진이 없으면 층고 = 사진 추정 또는 공간 유형 기본값.

### 7.6 결정적 배치 엔진 `be-engine` (모델 호출 없음, 순수 함수)
**입력**: SpaceModel, ProductItems(치수: KB 스펙 `dimensions` → 없으면 `screen_size_inch` 와 16:9·베젤 3%·깊이 0.08 m로 계산), FurnitureItems(카탈로그 치수), 의도(intents), 규칙 파라미터(§10.3; KB `placement_rule` 이 active 면 그 값 우선), 이전 레이아웃(있으면 고정 항목 유지).
**좌표**: §5.2. 점유 격자 0.1 m. 항목 = 회전된 사각형(w × d), 바닥에서 z, 높이 h.

1. **고정 요소 마스크**: 벽(두께), 기둥, 코어(배치 금지), 문 앞 여유(문 폭 × 1.2 m), 외곽 밖.
2. **크기 선택**(크기 옵션 제품): 앵커 벽의 빈 구간 길이 `L` 에서 양옆 0.5 m 를 뺀 폭에 들어가는 옵션 중 가장 큰 것. 그 크기의 최소 시청 거리(`대각 m × 1.5`)가 정면 깊이 `D` 보다 길면 한 단계 작은 옵션. 거리 규칙(`pr_signage_size_by_distance`)은 좌석 위치와 검증에만 쓴다. 벽 폭을 모르면(치수 없음) 가장 큰 옵션 + 가정 「도면에 {벽 이름} 폭이 없어 {제품} 크기는 {크기} 비율로 맞췄어요.」
3. **수량**: 앵커가 카운터면 `pr_menuboard_qty_by_counter`(`ceil(카운터 폭 ÷ 패널 폭)`), 규칙이 없으면 의도의 qty(없으면 1)를 쓰고 `qty_source='suggested'`(→ BE6·제안서에서 확인 필요). 사용자가 바꾼 수량은 `user`.
4. **배치 순서**: 벽·창 부착 제품(큰 순) → 기둥 랩핑 → 정면 좌석(`faces`) → 근접 가구(`near`) → 자유 가구. 같은 단계 안에서는 항목 id 순.
5. **앵커 해석**(배치안 라벨의 앵커 라벨: 창 → 「창면」, 정면 맞은편 벽 → 「후면 벽」, 좌우 벽 → 「측벽」, 정면 벽 → **(신규)** 「정면 벽」, 기둥 → **(신규)** 「기둥」. 수량표 위치 라벨 `at_label` 은 의도 LLM 이 앵커 + 용도로 10자 이내 작성(「쇼윈도 창면」 「후면 벽」 「측벽 · 상담」), 없으면 앵커 라벨): `wall:<id>` 빈 구간 중앙, 벽면에서 d/2 안쪽, 화면이 방 안을 향함 · `window:<id>` 창 선을 따라 등간격(그룹 간격 = 패널 폭 + 0.1 m), `faces_outdoor` 이면 바깥을 향함 · `column:<id>` 기둥 둘레 +0.1 m · `faces:<item>` 대상 디스플레이 법선 위 시청 거리 `ceil_0.5(대각 m × 1.5)` 지점, 좌석 열 간격 0.9 m · `near:<target>` 대상과 1.0 m 떨어진 가장 가까운 빈 자리 · `entrance` 주출입구에서 2.0 m 안쪽 측면.
6. **충돌 해소**: 목표 자세가 막히면 0.1 m 나선 탐색(최대 3.0 m), 같은 방향 우선, 순위 = (이동 거리, 각도 차, x, y). 실패하면 `unplaced` + **(신규)** 경고 「{항목}을 놓을 자리가 없어요」.
7. **좌석**: 벤치 길이 ÷ 0.6 m = 좌석 수, 좌석 중심 좌표 생성.
8. **검증**(§7.6.1) → 자동 조정 가능한 경고는 초기 생성 때 바로 적용(R6) → 남은 경고 저장.
같은 입력이면 출력 JSON 이 바이트 단위로 같아야 한다(부동소수는 0.01 m 반올림, 각도 0.1°).

#### 7.6.1 검증 규칙
| 종류 | 규칙 id | 식 | 기본 파라미터 |
|---|---|---|---|
| 시야각 | `pr_warn_viewing_angle` | 좌석마다 θ = 디스플레이 법선과 (디스플레이 중심 → 좌석) 수평각, `abs(θ) > max_angle_deg` → 좌석 밖 | `max_angle_deg = 45` (draft) |
| 시청 거리 | `pr_signage_size_by_distance` | 좌석 거리 d, 대각 inch 가 `[d·inch_per_m_min, d·inch_per_m_max]` 밖 | `inch_per_m_min = 15.75`, `inch_per_m_max = 26.25` (draft) |
| 동선 | `be_walkway_min_clear` | 자유 격자 거리변환, 주출입구 → 각 군집 접근점 최단 경로의 병목 폭 `w = 2 × 거리값`, `w < min_m` | `min_m = 1.2` (BE4E 「권장 1.2 m 이상」) |
| 전원 | `pr_warn_power_distance` | 제품 묶음의 전원 입구(뒷면 중앙)에서 가장 가까운 콘센트 직선거리 `d > max_m` | `max_m = 3.0` (draft) |
| 설치 높이 | `pr_warn_mount_height` | 디스플레이 아래 모서리 높이가 `[min_m, max_m]` 밖 | `min_m = 0.8`, `max_m = 2.6` (draft, 화면 표시는 §11) |

**수정안 계산(결정적)**
- 시야각: 원인이 디스플레이 이동이면 좌석 묶음을 같은 변위로 옮기는 안(「{묶음} 함께 옮기기」). 충돌하면 같은 변위 근처 0.1 m 탐색으로 모든 좌석이 다시 범위 안에 드는 가장 가까운 자세. 없으면 수정안 없음.
- 동선: 병목 양쪽 장애물 중 움직일 수 있는 것(가구 > 제품 > 고정 불가) 하나를 병목 법선 방향, 상대 반대쪽으로 `Δ = ceil_0.1(min_m − w)` 이동(「{약칭} {방향어} {Δ} m」, 방향어 = 「위로」 「아래로」 「왼쪽으로」 「오른쪽으로」). 이동 후 새 경고가 생기면 수정안 없음.
- 전원: 자동 수정 없음 — 「전원 위치 추가」(사용자 지정) / 「메모로 남기기」(메모는 BE6 수량표 `memo` 와 제안서 넘기기에 포함, 예 「바닥 배선 필요」).
- 방향어는 화면 기준(위 = −y). 거리 표기는 0.1 m.

### 7.7 로컬 초안 렌더 `be-draft` (결정적, CPU)
- 3D 구성: 바닥 다각형, 벽을 층고까지 돌출(창은 반투명 유리, 문은 틈), 기둥 상자, 제품 = 상자 + 화면 면(진회색 광택), 가구 = 카탈로그 원형(상자 1~3개), 코어 = 회색 덩어리.
- 카메라 프리셋: `aerial45` 목표 = 방 중심 바닥, 수평 방위 = 주출입구 쪽에서 45° 회전, 앙각 45°, 방 bbox 가 8% 여백으로 들어오는 거리, FOV 40° · `entrance` 눈높이 1.6 m, 주출입구 안쪽 0.5 m, 방 중심을 봄, FOV 60° · `product_front` 눈높이 1.6 m, 대상 디스플레이 법선 위 시청 거리, FOV 50° · `top` 직교 투영 · `custom` LLM JSON 을 방 bbox(±2 m)·높이(≤ 층고 − 0.2 m, 바깥은 ≤ 30 m)로 제한.
- 래스터화: numpy 투영 + 깊이 정렬(화가 알고리즘) + 평면 음영(방향광 1개) + 윤곽선, Pillow 1024×576. 톤 색: 웜 우드 #d9c3a5 · 모던 화이트 #eeeeee · 다크 메탈 #2b2f36(바닥·벽 포인트), 조명 틴트(저녁 따뜻한 주황 15%, 야간 어둡게 + 실내 발광).
- 두 장: `draft_v0`(구조 + 제품, 「마감재 적용 전」 미리보기) → `draft_v1`(+ 가구 + 톤, 구조 참조). 도입 전 컷은 제품·가구·랩핑을 뺀 `draft_v1`.
- 투영 행렬을 컷에 저장한다(존 포인트·QC 박스 힌트·클릭 역투영에 사용).

### 7.8 그래프 `be.render_cut`
```text
load(layout v, cut view/light/tone/before) → structure("공간 구조") → products("제품 배치") → draft_v0 → event preview
→ furniture_materials("가구 · 마감재") → draft_v1 → apply_memos(이 시점까지 온 메모 → 프롬프트 추가·allow_people)
→ render("조명 · 렌더링": image POST /renders {structure_ref=draft_v1, product_refs, prompt(공간·톤 재질·조명·시점·
   '참조의 모든 물체 위치를 그대로', 화면은 로고·글자 없는 추상 콘텐츠), aspect 16:9, target uhd,
   expect.products(투영 박스 힌트), forbid[competitor_logo, real_person_face, gibberish_text], allow_people})
   → 자식 job SSE 를 따라 진행 반영
→ qc("품질 확인": 자식 결과 qc + 컷 일치 확인; check 면 컷 status=check) → finalize(컷 done, 주 컷 지정, 작업 status, 알림) → END
```
- 렌더 중 도착한 메모: 끝난 뒤 그 컷에 편집 렌더(`edit_of=컷`)를 자동으로 한 번 더(편집 미지원이면 BE5 수정 요청 칸에 그 메모를 채워 둠, **(신규)** 안내 「진행 중 요청은 완성 후 수정 요청으로 남겼어요」).
- 중지: 자식 job 취소 → 마지막으로 끝난 초안(`draft_v1` 또는 `draft_v0`)을 컷 `status=draft` 로 저장.
- 추가 컷 자동 예약(`AUTO_EXTRA_CUTS=true`, BE4 → 첫 렌더 때만): (a) 공간 특징·설명에 「저녁」「야간」「외부 노출」·외부를 향한 창이 있으면 주 시점 야간 컷, (b) 제안서와 연결돼 있거나 설명·요청에 「전후」「도입 전」이 있으면 주 시점 도입 전 컷. 최대 2개, `auto_queued=true`, 대기열에서 뺄 수 있다.
- 진행률: 단계별 소요 EMA 로 추정(로컬 단계는 짧고 렌더가 대부분). 「약 {m}분 남음」 규칙은 07 §10.5 와 같다.

### 7.9 그래프 `be.result_edit` (BE5 수정 요청)
`classify(llm.json: {kind:'render'|'layout'|'view'|'mixed', render_instruction?, layout_ops?, view?}) →`
- `render`: image 렌더 API `edit_of=현재 컷` + 지시 → 같은 컷의 새 버전(조감도 컷 이력 유지).
- `layout`: 엔진에 ops 적용 → 새 레이아웃 버전 → 기존 컷 `stale` → 주 컷 재렌더 job → BE5G.
- `view`: BE5V 와 같은 컷 생성.
- `mixed`: layout 먼저, 그다음 render 지시를 새 컷 프롬프트에 포함.

### 7.10 그래프 `be.zones_auto`
`cluster(레이아웃 항목, 앵커 같은 것 묶고 2.5 m 이내 근접 병합, 결정적) → classify(제품 있는 군집 = 존, 가구만 = 존, 랩핑만 = 제안) → anchor(군집 중심, z = 평균 높이/2) → project(컷 투영 → u,v) → texts(llm.json: 존 이름 ≤ 14자, 문구 ≤ 60자, 근거 = kb E1/E3 제품·업종 메시지; 수치는 [00]) → order(주출입구에서 경로 거리 순 번호) → save`. 「빈 곳 클릭」은 역투영으로 바닥 평면 점을 구해 근처 항목으로 이름·문구 제안.

### 7.11 그래프 `be.export`
`collect(선택 컷 렌디션: 원본=uhd, FHD=fhd) → compose(전후 비교: 같은 높이로 나란히 + 라벨 「도입 전」「도입 후」 / 존 콜아웃: 번호 원(짧은 변 3%, #1428a0 흰 글자) + 범례 패널) → quantities.xlsx(export 서비스, 열 이름은 **(신규)**: 시트1 제품[공간, 제품명, 모델코드, 위치, 수량, 수량 근거(규칙/사용자/추정 → '확인 필요'), 메모, 출처 URL], 시트2 가구(참고), 가격 열 없음) → zip(export: 이미지 + xlsx + sources.json) → file → END`. 형식 PDF 는 이미지 페이지 + 수량표 페이지.

---

## 8. 다른 서비스 의존

| 서비스 | 쓰는 것 |
|---|---|
| ai-tools | `llm.json`(설명 해석·의도·가구 추천·문구·카메라·분류), `i2t.analyze`(도면·사진, json + bbox), capabilities |
| kb | 제품 검색·엔티티·스펙(`dimensions`, `screen_size_inch`, 크기 옵션), `C1`(공간 특징 → 역량, W 권장 문구), `E1`/`E3`(존 문구 근거), `G4`(제품 단독컷 — 렌더 참조는 image 가 고름), 배치 규칙(`placement_rule`, active·params 가 있으면 우선) — 경로는 `contracts/kb.json`. 배치 규칙 조회 API 가 없으면 `docs/requests/kb.md` |
| image | 렌더 API(07 §6.9: 조감도·도입 전·편집 렌더, uhd 업스케일, 품질 확인, AI 메타), 버전 사용 등록 |
| files | 도면·사진 업로드(HEIC 변환, PDF 쪽 미리보기), 초안·합성·엑셀 저장 |
| jobs | job·SSE·취소·메모·완료 알림, 컷 대기열 |
| workspace | 작업 색인, 프로젝트 고객, 팀 공유 목록(팀 이름), 「보기 전용 링크」 |
| export | XLSX(수량표)·PDF·ZIP |
| gateway·files(요청) | QR 모바일 업로드: `/m/upload/:token` 페이지와 files 업로드·`/v1/upload-tokens/{token}/photos` 를 토큰 인증으로 허용(`docs/requests/gateway.md`, `files.md`) |
| proposal(웹에서만) | 웹이 제안서 계약으로 호출: 제안서 목록, `POST /proposals/{id}/imports {source:{service:'birdseye', id, version}, map:[{from, code}]}`, ZP 시트 번호 조회. 제안서가 `GET /v1/birdseyes/{id}/handoff` 를 읽고 `usages` 를 등록 |
| scenario(호출자) | SC1B 가 `handoff`(존·배치 제품)와 `version`(변경 감지)을 읽고 `usages` 등록. 조감도 → 시나리오 호출은 없음 |
| spec(웹에서만) | 「Spec 시트 만들기」 = SP1 으로 제품 목록(`family_id`, 모델코드)을 라우트 상태로 넘김(spec 은 birdseye 를 consume 하지 않음) |

**handoff 묶음**: `{birdseye_id, version, title, customer, space:{area_m2, area_pyeong, ceiling_h_m, features}, cuts:[{cut_id, label, view, light, before, image_version_id, renditions, generation}], comparisons:[{kind:'before_after'|'day_night', left, right, composite_file_id}], zones:{layout:'ZP-A'|'ZP-B'|'ZP-C', cut_id, points:[{n, name, text, links, u, v}]}, quantities:[…], furniture:[…], memos:[…], sheet_map:[{from, to, code}]}`.

---

## 9. 수용 기준
모델 호출은 결정적 목(mock), KB 는 픽스처, 시계 고정. 엔진·초안 렌더는 실제 코드로 검증(골든 파일).

**BE0**
1. Given 작업 3건(완료 1·진행 중 1·확인 필요 1), When BE0, Then 필터 개수가 「전체」 3 「진행 중」 1 「확인 필요」 1 「완료」 1, 행 동작 버튼이 각각 「열기」 「이어서」 「확인」, 진행 상태 문구가 「완료」+「시점 3 · 존 포인트 4」, 「4/5」+「배치 · 인테리어 컨펌」, 「확인 필요」+「사진 1장 다시 찍기 · 1/5 공간 입력」이다.
2. Given 완료 작업에 야간 컷 job 진행 중, Then 진행 상태 칸에 링크 「야간 시점 추가 생성 중」(→ BE5G)이 있다.
3. Given 제안서·시나리오가 `usages` 를 등록, Then 「쓰인 곳」에 「제안서 · {제목}」 「시나리오 · {제목}」, 없으면 「아직 없음」. 「제안서에 쓰인 것만」을 켜면 제안서 사용 작업만 남는다.
4. When 작업 메뉴 「복제해서 새 시안」, Then 새 작업이 BE4 로 열리고 공간 모델·제품·가구·레이아웃·톤이 같고 컷·존·사용 이력은 비어 있으며 `cloned_from` 이 원본이다.
5. Given 팀 공유 2건, Then 카드 메타가 「외식 영업팀 공유 · 시점 2 · 존 포인트 5」 형식이고 「복제해서 시작」이 4 와 같이 동작한다.

**BE1**
6. Given 새 작업, Then 「매장 · 로비」 칩이 선택, 면적·층고 placeholder 가 `120`·`4.5`, 설명·파일이 없으면 「배치될 제품 입력」 비활성.
7. Given 면적 120평, Then 공간 모델 `area_m2` = 396.69(400/121 × 120, 소수 둘째 자리)다.
8. Given PDF 첨부, Then BE1D 로; JPG 3장(i2t 목: 평면도 아님), Then BE1P 로; PNG 평면도(i2t 목: 평면도), Then BE1D 로 간다.
9. Given 설명 두 줄(“1층 로비 … / 2층 라운지 …”)이고 도면 없음, Then 공간 모델 `rooms` 가 2개, 줄 순서대로 가로로 붙고 사이 벽 0.2 m·연결 문 1개가 있다.

**BE1D**
10. Given 벡터 PDF 픽스처(외벽 4·전면 창 2구간·문 2·기둥 600×600 2·EV/계단 코어·텍스트 「1:100」·치수 「24.0 m」, 환산 23.6 m), When 인식, Then 요약이 「축척 1:100 감지 · 면적 396 ㎡ (약 120평)」, 요소 문구가 「외벽 4면」 「전면 유리창 2구간」 「주출입구 1 · 뒤쪽 문 1」 「2개 · 600 × 600 mm」 「EV · 계단 · 배치 제외」, 머리 「5종 · 확인 2」, 확인 항목 1 = 「치수 보정 · 정면 폭」(「표기값 24.0 m」 선택됨), 2 = 「뒤쪽 문은 어떤 문인가요?」.
11. Given 표기 24.0 m · 환산 23.88 m(0.5% 차), Then 치수 보정 항목이 없다.
12. When 「표기값 24.0 m」 유지 후 계속, Then 모든 좌표에 24.0/23.6 배율이 적용되고 면적이 다시 계산된다. 「환산값」이면 좌표 불변.
13. When 문 질문에 「벽으로 처리」, Then 그 문 개구부가 공간 모델에서 사라지고 문 요약이 「주출입구 1」이 된다.
14. Given 문 질문 미응답, When 「이 구조로 계속」, Then BE2 로 가고 그 문은 출입 가능한 문(앞 1.2 m 비움)으로 처리되며 `assumptions` 에 기록된다.
15. Given ai-tools `POLICY_CONFIDENTIAL`, Then 벡터 결과만으로 BE1D 가 보이고 「고객 도면이라 외부 모델 없이 기본 인식만 했어요」, 모든 i2t 호출 인자에 `confidential:true` 가 있었다.
16. When 「말로 고치기」 「오른쪽 기둥은 철거됐어」(LLM 목: remove c2), Then 기둥 요약이 「1개 · 600 × 600 mm」.

**BE1P**
17. Given 밝은 영역 30%·나머지 평균 0.25 인 사진, Then 상태 「역광 · 창 위치가 흐려요」와 「다시 찍기」 「그대로 사용」. 「그대로 사용」을 누르면 `accepted` 로 요약 사진 수에 포함된다.
18. Given 인식 완료 2·역광 1·인식 중 1, 천장 없음, Then 머리 「사진 4장」 「인식 완료 2 · 확인 필요 1 · 인식 중 1」, 「찍은 방향」 「4 / 4」 「· 천장 없음」, 천장 카드 「없음 · 층고는 추정값」, 요약 「· 사진 2장 기준」.
19. When 「사진에 없는 정보」 「상황판 벽 폭 9m, 운영석 2열 12석」, Then 사실 칩에 반영되고 공간 모델 정면 벽 폭이 9.0 m(사용자 값, `estimated=false`)다.
20. Given 업로드 토큰 발급, When 모바일이 토큰으로 사진을 올림, Then BE1P 에 카드가 SSE 로 추가된다. 30분 지난 토큰은 410 `TOKEN_EXPIRED`.
21. Given GIF 업로드, Then 415 와 「JPG · PNG · HEIC만 올릴 수 있어요」.

**BE2 · BE3**
22. Given 공간 특징(전면 유리창 `faces_outdoor`, 기둥 2)과 C1 픽스처(`cap_sunlight_readable`), Then 요약 칩 「120평 · 층고 4.5m」 「전면 유리창 (고휘도 권장)」 「중앙 기둥 2개」.
23. Given 입력 「the w」와 검색 픽스처 3건, Then 결과 머리 「"the w" 검색 결과 · Enter로 추가」, 첫 행에 「추가 ↵」, Enter 로 첫 행이 칩으로 추가되고 머리 개수가 늘어난다.
24. Given 제품 0개, Then 「가구 추천 받기」 비활성.
25. Given 가구 추천 LLM 목(4개), Then 카드 4장 중 상위 3장이 선택, 칩 「기둥 랩핑 프레임 ×2 ×」(기둥 2), 관람 벤치 이유 줄이 「The Wall 정면 · 시청 거리 6m」(146" 대각 3.708 m × 1.5 = 5.56 → 0.5 m 올림 6.0)이다.
26. When 「가구 없이 진행」, Then 가구 0 으로 배치 job 이 돌고 BE4 배치안에 가구가 없다.
27. When 「가구 직접 입력」 「안내 로봇」(카탈로그 없음), Then 사용자 가구 1.0×0.6×0.8 m 칩에 「· 치수 추정」.

**엔진 · BE4 · BE4E**
28. Given 골든 입력(§5.2 예 공간, 제품 3종, 가구 4종, 의도 픽스처), When `layout:generate` 를 두 번 실행, Then 두 결과 JSON 이 바이트 단위로 같고 골든 파일과 같으며, 라벨 「OH55C ×3 (창면)」 「The Wall IAB 146" (후면 벽)」 「Flip Pro WA75D (측벽)」 「기둥 랩핑 ×2」가 있다.
29. Given 후면 벽 폭 미상, Then The Wall 크기는 146"(가장 큰 옵션)이고 `assumptions` 에 「도면에 후면 벽 폭이 없어 The Wall 크기는 146" 비율로 맞췄어요.」가 있다.
30. Given BE4 기본, Then 톤 「웜 우드」, 시점 「조감 (45°)」 선택.
31. When 「배치 수정 요청」 「관람 벤치를 2열로 줄이고 The Wall 쪽으로 붙여줘」(LLM 목: set_qty 2, move dy), Then 레이아웃 버전 +1, 벤치 2열, 엔진 검증 결과가 저장된다.
32. Given BE4E 세션, When The Wall 을 x +3.0 m 이동, Then 경고 1 = 「시야각」 「The Wall을 오른쪽으로 3.0 m 옮겨 관람 벤치 왼쪽 2석이 시야각 밖이에요」(골든 좌석에서 θ > 45° 인 왼쪽 좌석 2), 수정안 「벤치 함께 옮기기」, 이동 라벨 「오른쪽으로 3.0 m」, 「원래 위치」 유령이 있다.
33. When 「벤치 함께 옮기기」, Then 벤치가 +3.0 m 이동하고 재검증에서 시야각 경고가 없다.
34. Given 소파–기둥 병목 0.6 m, Then 경고 「라운지 소파와 기둥 사이 통로 0.6 m · 권장 1.2 m 이상」, 수정안 「소파 위로 0.6 m」; 적용 후 병목 ≥ 1.2 m.
35. Given OH55C ×3 전원 입구에서 가장 가까운 콘센트 6.0 m, Then 경고 「OH55C ×3에서 가까운 콘센트까지 6.0 m · 바닥 배선 필요」, 버튼 「전원 위치 추가」 「메모로 남기기」. 「전원 위치 추가」로 2.0 m 지점에 콘센트를 넣으면 경고가 사라진다(3.0 이하).
36. When 「경고 모두 자동 조정」(32·34·35 상태), Then 시야각·동선 경고는 `fixed`, 전원은 `memo` 이고 메모 「바닥 배선 필요」가 수량표 `memo` 에 실린다.
37. Then 모든 경고 객체에 `rule_id`·`expr`·`params`·`param_status` 가 있고 툴팁에 보인다(예 `pr_warn_power_distance · distance_to_power_m > 3.0 (draft)`).
38. When 「취소」, Then 세션이 버려지고 레이아웃 버전이 그대로다. 「수정 적용」, Then 새 버전이 생기고 「변경 {n} 건」의 n 이 세션 연산 수와 같다(되돌린 연산 제외).
39. Given 항목 50개 레이아웃, Then `layout:validate` 응답이 200ms 이내(CI 기준 장비).

**BE5G · BE5 · 렌더**
40. When 「이 배치로 3D 생성」, Then 단계 이벤트가 「공간 구조」 → 「제품 배치」 → 「가구 · 마감재」 → 「조명 · 렌더링」 → 「품질 확인」 순으로 오고, 「제품 배치」 완료 뒤 미리보기 「초안 · 조감 45°」(`draft_v0`)가 나타나며, image `POST /v1/renders` 인자에 `structure_ref_file_id=draft_v1`, 제품 3종, `target='uhd'`, `forbid` 3종이 있고, 결과 컷이 3840×2160 이다.
41. Given 설명에 「저녁엔 외부에서 내부가 잘 보임」이고 제안서 연결 있음, Then 첫 렌더와 함께 대기열에 「조감 45° · 야간」 「도입 전 · 조감 45° (비교용)」이 자동으로 들어가고(대기열 2), 「대기열에서 빼기」로 뺄 수 있다.
42. When 「중지」, Then 자식 image job 취소가 요청되고 컷이 `draft`(초안 이미지 보존)로 저장되며 BE4 로 이동한다.
43. Given 「조명 · 렌더링」 전에 메모 「로비에 사람 실루엣 몇 명 넣어줘」, Then 렌더 요청 `allow_people='silhouette'` 이고 프롬프트에 반영. 렌더 중 도착한 메모는 완료 후 `edit_of` 렌더 1회로 반영된다.
44. Given `T2I_SUPPORTS_REFERENCE_IMAGES=false, EDIT=true`, Then image 렌더 요청은 `edit_of=draft_v1`; 둘 다 false 면 텍스트 렌더 + 컷 `check`; image 렌더 API 가 `T2I_UNAVAILABLE` 이면 초안 컷 + 「초안 렌더」 배지.
45. Given 완료(톤 웜 우드, 조감 45°, 제품 3·가구 4), Then BE5 W 가 「3D 조감도가 완성되었습니다. 웜 우드 톤, 45° 조감 시점이며 제품 3종과 가구 4종이 배치안대로 반영되었습니다.」, 태그 「조감 45°」 「웜 우드」 「3840×2160」.
46. When 수정 요청 「조명을 더 따뜻하게」(분류 목 render), Then 같은 컷의 새 버전이 `edit_of` 렌더로 생긴다. 「벤치를 2열로」(분류 목 layout), Then 레이아웃 버전 +1, 기존 컷 `stale`(「배치 변경 전」), 주 컷 재렌더 job 이 생겨 BE5G 로 간다.
47. Given 가정(후면 벽 폭 없음), Then BE5G 에 「확인 필요」 「· 도면에 후면 벽 폭이 없어 The Wall 크기는 146" 비율로 맞췄어요.」와 링크 「벽 치수 보정」(→ BE1D).

**BE5V**
48. Given 시점 「입구 시점」+「The Wall 정면」, 조명 「야간」, 도입 전 꺼짐, Then 「새로 만들 컷 2」 「선택한 2컷 생성」. 「도입 전 컷도」를 켜면 4, 이미 있는 같은 컷은 빼고 센다.
49. Then 도입 전 컷의 초안에는 제품·가구·랩핑 다각형이 없고 구조(벽·기둥·창)는 같다.
50. When 「시점 설명」 「2층 난간에서 내려다본 시점」(LLM 목: 높이 7 m), Then 카메라 높이가 층고 − 0.2 m(4.3 m)로 제한된다.
51. When 「전/후 2컷을 제안서 '두 시점 비교'로」, Then BE6 이 열리고 매핑에 `BV-B` 행이 선택돼 있다.

**BE5Z**
52. Given 골든 레이아웃·컷, When `zones:auto`, Then 존 4개와 제안 1개(기둥 랩핑 군집), W 제안 「기둥 2개를 5번 포인트로 넣을까요?」, 포인트 `u,v` 가 투영 골든 값과 1px 이내다.
53. When 「동선 순서로 번호」, Then 번호가 주출입구 경로 거리 오름차순이 된다.
54. When 이미지 빈 곳 클릭, Then 역투영한 바닥 점에 새 포인트가 생기고 근처 항목 기반 이름 제안이 붙는다.
55. Then 존 이름 ≤ 14자, 문구 ≤ 60자, 수치는 「[00]」 로만 나온다(LLM 목이 숫자를 내면 치환). 시트 레이아웃 칩이 ZP-A/B/C 로 매핑되고 미리보기 코드가 바뀐다.

**BE6**
56. Given 컷 4종(주간·야간·도입 전·입구) + 존 4, Then 이미지 목록이 「조감 45° · 주간」 「조감 45° · 야간」 「도입 전 / 후 비교」 「존 포인트 콜아웃」 「입구 시점 · 주간」 이고 앞 4개 선택(「4」 「/ 5 선택」), 형식 「PNG」, 크기 「원본」.
57. Then 수량표 행이 「Outdoor Signage OH55C」 「쇼윈도 창면」 「3」, 「The Wall All-in-One IAB 146"」 「후면 벽」 「1」, 「Flip Pro WA75D」 「측벽 · 상담」 「1」, 「가구 4종 (참고)」 「라운지 · 관람 · 안내」 「7」 이다.
58. When 「ZIP 내려받기」(파일 이름 기본 「강남플래그십_1층로비_조감도_v1」), Then export job 이 생기고 ZIP 에 PNG 4장(3840×2160), `수량표.xlsx`(가격 열 없음, 「수량 근거」 열에 suggested → 「확인 필요」), `sources.json`(컷별 생성 메타)이 있다.
59. Then 제안서 매핑이 「조감 45° · 주간 → 조감도 · 공간 전경 BV-A」, 「도입 전 / 후 → 공간 전경 · 두 시점 비교 BV-B」, 「존 포인트 4곳 → 조감도 · 존별 포인트 ZP-A」, 「제품 수량표 → 공간별 제품 · 수량표 SM-B」. 「제안서에 넣기」를 누르면 웹이 제안서 가져오기를 호출하고, 제안서 목이 `handoff` 를 읽은 뒤 `usages` 를 등록하면 BE0 「쓰인 곳」이 갱신된다.
60. When 「공간 시나리오로 이어 만들기 · 시작」, Then SC1B 가 `?birdseye={id}` 로 열린다. 「Spec 시트 만들기 · 시작」, Then SP1 라우트 상태에 제품 3종 `family_id` 가 있다. 「링크 복사」, Then workspace 공유 링크 생성 호출 후 클립보드에 URL.
61. Given 작업 단계 이동·컷 완료, Then workspace `PUT items/{id}` 가 `feature='birdseye'` 와 §5.4 규칙의 `route` 로 호출된다.

---

## 10. 규칙 · 임계값

### 10.1 보드의 수치(그대로)
- 단계 5(공간 입력 · 배치될 제품 · 가구 추천 · 배치 · 인테리어 컨펌 · 3D 조감도 생성), 공간 유형 칩 6, 인테리어 톤 3(웜 우드 · 모던 화이트 · 다크 메탈), BE4 시점 2(조감 (45°) · 입구 시점), BE5V 시점 4 · 조명 3 · 도입 전 컷 1, 비교 보기 3(나란히 · 겹쳐 밀기 · 주간 / 야간), 존 시트 레이아웃 3.
- 예시 값: 「120평」 「층고 4.5m」 「396 ㎡ (약 120평)」 「축척 1:100」 「24.0 m」/「23.6 m」 「600 × 600 mm」 「외벽 4면」 「전면 유리창 2구간」 「약 45평 추정」 「층고 3.2 m 추정」 「상황판 벽 폭 약 9 m」 「운영석 2열」 「4 / 4」 「사진 4장」.
- 「시청 거리 6m」, 「오른쪽으로 3.0 m」, 「왼쪽 2석」, 「통로 0.6 m · 권장 1.2 m 이상」, 「소파 위로 0.6 m」, 「콘센트까지 6.0 m」.
- 「60% · 약 1분 남음」 「3840×2160」 「대기열 2」 「생성 중 62%」 「만든 컷 · 5」 「새로 만들 컷 2」 「존 포인트 4곳」 「9번」 「이미지 4 / 5 선택」 「원본 · 3840×2160」 「FHD」 「가구 4종 (참고) … 7」 「이미지 4장 · 수량표 1개 · ZIP」.
- 시트 코드: BV-A(공간 전경), BV-B(두 시점 비교), ZP-A(번호 콜아웃), ZP-B(존 확대 컷), ZP-C(고객 동선 따라가기), SM-B(공간별 제품 · 수량표).
- 톤 견본색: 웜 우드 #d9c3a5, 모던 화이트 #eeeeee, 다크 메탈 #2b2f36.

### 10.2 단위·표기
- 1평 = 400/121 ㎡(3.3058). 평 표기는 정수 반올림 「약 {n}평」, ㎡ 는 정수. 길이 0.1 m, 제품 치수 mm.
- 시각: 「오늘 HH:mm」 / 「어제 HH:mm」 / 「M월 D일」.

### 10.3 엔진·검증 파라미터(`services/birdseye/config/rules.yaml`, draft — 사람 승인 전)
| 키 | 기본 | 근거 |
|---|---|---|
| `be_walkway_min_clear.min_m` | 1.2 | 보드 「권장 1.2 m 이상」 |
| `pr_warn_viewing_angle.max_angle_deg` | 45 | 제안(KB `<<FILL>>`) |
| `pr_signage_size_by_distance.inch_per_m_min / max` | 15.75 / 26.25 | 시청 거리 = 대각의 1.5~2.5배(제안) |
| 좌석 시청 거리 | `ceil_0.5(대각 m × 1.5)` | 146" → 6.0 m(보드 「시청 거리 6m」) |
| `pr_warn_power_distance.max_m` | 3.0 | 제안(보드 6.0 m 가 경고) |
| `pr_warn_mount_height.min_m / max_m` | 0.8 / 2.6 | 제안 |
| `pr_menuboard_qty_by_counter.panel_width_m` | 제품 스펙 가로폭 | KB 스펙 |
| 문 앞 여유 | 문 폭 × 1.2 m | 동선 기준과 같은 값 |
| 좌석 간격 / 열 간격 | 0.6 m / 0.9 m | 제안 |
| 충돌 탐색 | 0.1 m 나선, 최대 3.0 m | 제안 |
| 군집 반경 | 2.5 m | 제안 |
| 치수 불일치 질문 | > 1% | 보드 예 1.7% 질문 |
| 문 종류 질문 | 신뢰도 < 0.6 | 제안 |
| 미응답 기본값 | 문 = 출입 가능한 문, 치수 = 표기값 | 안전 쪽 |
| 공간 유형 기본 층고 | 매장·로비 3.0 · 회의실·오피스 2.7 · 강의실 3.0 · 병원 대기실 2.7 · 호텔 객실 2.6 · 관제실 3.2 m | 제안(estimated) |
| 사진 품질 | 휘도 평균 < 0.22 어두움 · 밝은 영역(> 0.85) > 25% & 나머지 < 0.30 역광 · 라플라시안 분산 < 50 흐림 | 제안 |
| 업로드 | 도면 PDF·PNG·JPG / 사진 JPG·PNG·HEIC, 20MB/장, 사진 최대 12장, QR 토큰 30분 | 제안 |
| 추가 컷 자동 예약 | 최대 2(야간·도입 전) | 제안 |
| 렌더 | 16:9, uhd 3840×2160(T2I 원출력 1024×576 → 업스케일) | 보드 해상도 |
| 존 | 이름 ≤ 14자, 문구 ≤ 60자, 콜아웃 원 지름 짧은 변 3% | 제안 |

### 10.4 가구 카탈로그(`config/furniture_catalog.yaml`, 제안 치수 w×d×h m)
라운지 소파 세트(소파 2.4×0.9×0.8 + 테이블 1.0×0.6×0.4) · 기둥 랩핑 프레임(기둥 +0.1 m 둘레, 높이 = 층고 − 0.3) · 관람 벤치(1열 2.4×0.45×0.45, n열 간격 0.9) · 체험 카운터 1.8×0.7×1.0 · 안내 데스크 2.0×0.8×1.05 · 화분 0.5×0.5×1.2 · 테이블 세트 1.2×1.2×0.75 · 회의 테이블 3.0×1.2×0.75 · 운영석 책상 1.6×0.8×0.75 · 진열대 1.8×0.5×1.5. 별칭(“벤치”, “데스크” 등)과 앵커 기본값(소파 = 창 근처, 벤치 = 가장 큰 디스플레이 정면, 데스크 = 입구)을 함께 둔다.

---

## 11. 열린 질문
1. **BE5 「톤 바꿔 재생성」 → BE5V**: BE5V 보드에 톤 선택이 없다. BE4 의 톤 칩 줄을 BE5V 에 “톤 모드”로 보이게 한 결정(§4.11) 확인.
2. **검증 파라미터 승인**: 시야각 45°, 전원 3.0 m, 설치 높이 0.8~2.6 m, 시청 거리 1.5~2.5배는 제안값이다(KB `placement_rules.yaml` 은 `<<FILL>>`). 누가 승인하고 KB active 규칙으로 옮길지. 설치 높이 경고는 보드에 없어 화면에 보이지 않게 했다 — 보일지?
3. **존 '요구' 연결**: birdseye 는 requirements 를 consume 하지 않아 「요구: 외부 유입」을 입력 문장에서 뽑는다. 요구사항 정의서와 연결하려면 `services.yaml` 에 `requirements` 추가가 필요하다.
4. **팀 공유를 켜는 곳**: BE0 에 팀 공유 목록은 있지만 공유하는 버튼은 어느 보드에도 없다(「보기 전용 링크」와 다름). workspace 공유 기능으로 둘지?
5. **QR 업로드 망**: 사내 PC 한 대에서 도는 구조라 휴대폰이 같은 망에서 PC 주소에 닿아야 한다. 게이트웨이 외부 노출·토큰 인증 경로 허용 여부.
6. **콘센트 위치 출처**: 도면 기호 인식은 신뢰도가 낮다. 전원 경고는 사용자가 넣은 콘센트가 없으면 “전원 위치를 몰라요”가 대부분일 것 — 초기 생성에서 전원 검사를 끄고 BE4E 에서만 켤지?
7. **추가 컷 자동 예약 비용**: 첫 렌더 때 야간·도입 전 컷을 자동으로 예약하면 T2I 호출이 3배가 된다. 기본 켬/끔.
8. **도입 전 컷의 의미**: 생성 이미지라 실제 현재 모습이 아니다. 현장 사진이 있으면 그 사진을 도입 전으로 쓸지(정면 시점이 맞지 않음), 생성 이미지에 「생성 이미지 · 도입 전 가정」 캡션을 강제할지.
9. **여러 공간(줄 단위)**: 도면 없이 여러 공간을 가로로 붙이는 단순 배치가 제안 품질에 충분한지.
10. **BE5Z 장면 연결 모드**: 시나리오 화면이 BE5Z 로 링크하지만 BE5Z 보드에는 장면 연결 UI 가 없다. 「장면 {n}」 연결 칩 추가 확인.
11. **KB 배치 규칙·제품 치수 API**: kb 계약에 `placement_rule` 조회와 스펙 `dimensions` 정규값 제공이 있는지(`docs/requests/kb.md`).
12. **BE0 「삭제」** 시 이미 제안서·시나리오에 넘긴 이미지 처리(남김으로 정함) 확인.
