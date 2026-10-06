# image 요청

## 셸 「내 생성 이미지」 탭 · 이미지 정보 — workspace(00-shell §7.4 · Q 표 1395행) · 2026-10-06
- 필요: 상단 이미지 검색 팝오버 「내 생성 이미지」 탭 = `GET /api/image/v1/images?owner=me&q=&limit=&cursor=` → `{id, title, width, height, format, bytes,
  created_at, file_id, thumb_url}`, 이미지 정보(셸 정보 패널 · 시트) = `GET /v1/images/{id}/info`.
- 상태: 완료(2026-10-06, contracts/image.json) — `owner=me` 는 저장한 시안만(생성 중 · 숨김 · 렌더 API 결과 제외), `q` 는 제목 · 고객사 약칭,
  응답에 `total` · `next_cursor` 와 `kind` · `aspect` · `customer_short` · `used_in_count` · `meta` · `route`(IMG3) 도 있다. 참조 문자열은 `img:image:<id>`.
- 보충(2026-10-06): `q` 는 띄어쓰기로 나눈 낱말이 모두 들어 있는 것만 — 제목 · 고객사 약칭 · 작업 제목 · 장면 설명 · 고객사 이름에서 찾는다.
  셸 「현재 작업에 추가」 제품 참조는 `POST /v1/works/{id}/products {refs, qty}`(IMG2 · IMG2P 화면이 onAdd 로 부른다).

## 렌더 mock 품질 확인(QC)이 늘 「제품 수 다름」 — birdseye · 2026-10-07
- 관찰: `MODEL_MODE=mock` 에서 `POST /v1/renders`(kind 'birdseye') 결과 `qc` 가 제품 수 불일치로 표시돼 조감도 컷이 늘 「확인 필요」(`check`)로 끝난다
  (BE5 W 끝에 「일부 제품 위치가 배치안과 다를 수 있어요.」, BE0 「확인 필요」 필터). 데모에서는 `done` 이 보이면 좋겠다.
- 제안: mock 렌더는 `product_refs` 수량을 그대로 맞은 것으로 보거나, mock 고정 응답으로 QC 결과를 고를 수 있게(예 `mocks/ai-tools/img.render_qc.json`). 실제 모델 경로는 지금 그대로.
- 상태: 요청(급하지 않음 — 조감도는 `check` 도 정상 흐름으로 다룬다)
- 셸 사용 확인(workspace · 2026-10-07): 이미지 검색 팝오버 「내 생성 이미지」 탭이 `GET /api/image/v1/images?owner=me&q=&limit=24` 를 쓰고(검색어가 있을 때), 정보 패널은 `GET /api/image/v1/images/{id}/info` 의 `rows` 를 그대로 보인다(못 받으면 셸이 아는 값).
  고르기 · 끌기 참조는 `img:image:<id>`(e2e `web/e2e/shell/image-mine.spec.ts`).
- 상태(integration · 2026-10-07): 완료 — mock 공급자일 때 렌더 QC 가 요청 수량(`product_refs` qty 합) · 배치 상자(`expect`)를 그대로 맞은 것으로 본다(`qc.mock_matched=true`, 비율 검사 건너뜀 → 조감도 컷 `done`). 실제 모델 경로는 그대로(`shots.quality_check`).
  함께 고침: 렌더 API 가 만든 숨은 작업(`internal` — 조감도 컷 · 시나리오 장면)은 workspace 색인에 올리지 않는다(IMG 사이드바 오염 — 이미 올라간 옛 항목은 남아 있음).
  이미지 정보 「사용 이력」 줄 = `Winmate 제안서 {n}건 · 조감도 {k}건 · 시나리오 {k}건`(usages 서비스별). `make test SERVICE=image` 74 통과.
