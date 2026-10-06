# ai-tools mock 고정 응답

`MODEL_MODE=mock`(또는 `<CAP>_PROVIDER=mock`)일 때 ai-tools 는 `<task>.json` 이 있으면 그 내용을 응답으로 쓴다.
없으면 스키마로 만든 결정적 가짜 값(JSON 스키마가 있을 때) 또는 `"[mock:<task>] <마지막 사용자 메시지 앞부분>"` 텍스트.

- 파일 이름 = task(예: `rq.extract_form.json`). 각 기능 세션은 자기 접두사(rq. sb. mi. ca. vp. sp. img. be. sc. pr.) 파일만 만든다.
- 파일은 호출할 때마다 다시 읽는다(고치면 서비스 재시작 없이 반영).
- 고정 응답은 스키마 검증 · 수리 재시도를 거치지 않는다(맞지 않으면 ai-tools 로그에 경고만). 문맥 길이(413)는 그대로 적용된다.
- 기밀 정책: mock 은 밖으로 나가는 것이 없어 `confidential:true` 도 막지 않는다. 차단 경로(403 `POLICY_CONFIDENTIAL`)를 시험하려면
  `MOCK_ENFORCE_CONFIDENTIAL=true`(그때는 `*_ALLOW_CONFIDENTIAL` 설정대로 막는다).

## 형식

| 기능 | 형식 | 결과 |
|---|---|---|
| LLM(JSON) | `{"json": {...}}` | `json` 에 그대로, `content` 는 그 JSON 글 |
| LLM(텍스트) | `{"content": "..."}` | `content` |
| LLM(도구) | `{"tool_calls": [{"name": "kb_search", "arguments": {"q": "QMC"}}], "content": "선택"}` | 요청에 `tools` 가 있을 때만 `tool_calls`(id 는 자동) |
| I2T | `{"json": {...}, "boxes": [{"label": "screen", "box": [0.1, 0.2, 0.5, 0.6], "score": 0.9, "image_index": 0}]}` 또는 `{"content": "..."}` | `want_bbox` 일 때만 `boxes`(없으면 기본 박스 2개). `box` = [x0, y0, x1, y1] 0..1 |
| 웹 검색 | `{"summary": "...", "sources": [{"url": "...", "title": "..."}], "queries": ["..."]}` | `sources` 는 `WEBSEARCH_RETURN_SOURCES=true` 일 때만 밖으로 나간다 |
| T2I | (고정 응답 없음 — 항상 프롬프트를 그린 PNG) | `{"error": …}` 만 쓴다 |
| 오류 흉내 | `{"error": {"status": 503, "code": "UPSTREAM_UNAVAILABLE", "message": "웹 검색 장애"}}` | 그 상태 · 코드의 오류 응답 |

### 여러 응답을 차례로

```json
{"responses": [
  {"json": {"step": 1}},
  {"tool_calls": [{"name": "lookup", "arguments": {"q": "x"}}]},
  {"error": {"status": 429, "code": "RATE_LIMITED", "message": "한도"}}
]}
```

task 별 호출 횟수로 차례대로 돌려 쓴다(끝나면 처음부터). 호출 횟수는 ai-tools 프로세스 안에서 센다 — 서비스를 재시작하면 처음부터.

### 입력으로 고르기(`when`)

```json
{"responses": [
  {"when": {"contains": "QM55R"}, "json": {"add": "QM55R"}},
  {"when": {"contains": ["연간", "전기료"], "not_contains": "QM55R"}, "json": {"row": "annual_power_cost"}},
  {"json": {"note": "기본"}}
]}
```

- `when.contains`(문자열 또는 목록 — 모두 들어 있어야) · `not_contains`(하나라도 있으면 아님)를 요청 글(LLM: system + 메시지, I2T · T2I: 프롬프트,
  웹 검색: 질의)에서 찾는다. 맞는 첫 항목을 쓰고, 맞는 것이 없으면 `when` 없는 항목들만 차례로 돌린다.
- 조건 항목은 순번을 쓰지 않는다 — 여러 호출이 동시에 와도 입력이 같으면 응답이 같다(e2e · 그래프 병렬 노드에 권장).
같은 task 를 동시에 여러 번 부르는 그래프라면 순서가 흔들릴 수 있으니, 응답마다 task 이름을 나누는 편이 결정적이다.

## 가짜 값 규칙(고정 응답이 없을 때)

- 문자열: `"[mock] <속성 이름의 한국어>"` (예 `customer_name` → `"[mock] 고객사 이름"`, 한국어 title/description 이 있으면 그것), 배열 안에서는 순번
- format: date `2026-10-06` · date-time `2026-10-06T09:00:00Z` · uri `https://example.com/mock/…` · email · uuid …
- 숫자: 범위 · multipleOf 를 지키는 작은 값, enum/const 는 첫 값, 배열은 최소 개수(없으면 2개), pattern 은 정규식에 맞는 문자열
- 같은 스키마 → 항상 같은 값(프롬프트가 바뀌어도 그대로)
