# requirements 요청

## 허브 완료 화면 머리 = 보드 Done(짧은 이름) — storyboard · 2026-10-10
- 바뀐 것(허브 `/v1/flows*`, 응답 모양 그대로): `PUT /v1/flows/{id}/stages/{key}` 의 `md_added`(→ `push_stage` · 각 서비스 `flow_sync.md_added`) 첫 줄을
  보드 Done 머리(짧은 이름 · 번호 없음)로 바꿨다 — `## 요구사항 · RQ-06 v1` · `## DSS · …` · `## MI · MI-01 v2` · `## 경쟁사 · CA-01 v1` · `## VP · …` · `## Spec · …` · `## 시나리오 · …`.
  요약본 전체(`summary_md`)는 그대로 보드 SB1 형식(`## 1. 고객 요구사항 · RQ-01 v2` · `## 3. Market Intelligence · MI-01 v1`), 「남은 것」 줄의 시나리오는 `공간 시나리오`.
  함께: flow.json `progress` 는 보드 값 `rq` · `dss+n/5`(화면 문구 `FlowDoc.progress` 는 그대로), `keyPillars` 는 받쳐 줄 메시지가 있을 때만, 분기(`:branch`)는 Key message 를 복사하지 않는다(보드 SB0 · SBPopup).
- 맞출 곳: `services/requirements/tests/test_requirements_flow.py:192` · `:213` `md_added.startswith(f"## 고객 요구사항 · {d['code']} v…")` → `## 요구사항 · {code} v…`.
  `rqflow.py:947` 의 허브 없을 때 대체 머리(`## 고객 요구사항 · …`)도 보드 RQ_Done(`## 요구사항 · RQ-06 v1`)에 맞추면 같다.
- 상태: 완료(2026-10-10 플랫폼 통합 때 테스트 기대 문자열을 고침)
