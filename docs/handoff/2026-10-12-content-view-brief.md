# 2026-10-12 — 완료 화면 없애고 콘텐츠 보기로 (웹앱 ① 보드 v60) · 기능 세션 공통 지시

> **대체됨(같은 날)**: 이 지시(보기 + `?edit=1` 편집)는 v62(최종본 + 단계 팝업)를 거쳐 **v63 「최종본에서 바로 고치기」**(`docs/handoff/2026-10-12-content-detail-v63.md` · `docs/scenarios/11-content-flow.md` §7)로 바뀌었다. 기록으로만 남긴다.

요청(사람이 직접 한 말): **"각 컨텐츠의 완성 화면은 그 컨텐츠여야 해. 완성됐습니다 이런 거 필요 없어. 히스토리로 다시 접근해도 마찬가지야."**

UI 는 보드를 철저히 따른다 — 폭 · 고정/가변 칸 · 여백 · 글자 크기 · 문구. 보드가 디자인 정본이다.

## 무엇이 바뀌나

- 콘텐츠를 **저장하면** 「○○를 저장했어요」 완료 화면(`FlowDoneView` · 요약본 추가분 · 접힌 JSON) 대신 **그 콘텐츠 보기**가 뜬다.
- **목록 줄 · 사이드바 작업 내역 · 허브 cells[].route** 로 저장한 콘텐츠를 열어도 같은 보기다(경로는 지금 그대로 — 예: `/dss/:id`).
- 저장 전 초안(한 번도 저장 안 함)은 그 경로에서 그대로 편집 화면이다(보여 줄 완성본이 없다).
- 편집 화면은 `?edit=1`. 보기의 「편집」이 그리로 가고, 편집 화면에서 저장하면 `?edit` 를 떼고 보기로 돌아온다(완료 안내 · 토스트 없음).
- 보기에는 「저장했어요 · 완성됐어요」 같은 문구가 **어디에도 없다**. 저장 직후와 나중에 다시 열었을 때가 **똑같다**.

## 보드(정본)

- 공통 틀 + 콘텐츠별 본문: `docs/screens/webapp1/View.dc.html`(content = rq · dss · mi · ca · vp · sp · sc). 인라인 px 를 그대로 옮긴다.
- 그린 화면: `docs/screens/_rendered/webapp1/<X>_View.jpg`(Read 로 본다) + `.txt`(글 순서). `DS_ViewJson.jpg` = flow.json 팝업.
  RQ_View · DS_View · MI_View · CA_View · VP_View · SP_View · SC_View.
- 보드의 예시 데이터는 보기 모양을 보여 주려는 것 — 화면 값은 **그 기능의 문서(편집 화면이 쓰는 데이터)** 에서 그린다. 없는 값은 지어내지 않는다(`[확인 필요]` · `—`).

## 이미 된 것(플랫폼 · 고치지 말고 쓴다)

- `web/src/shell/flow/parts.tsx` — **`FlowContentView`**: SB 바 · 머리(아이콘 · 이름 · 참조 v · 메타 한 줄 · actions · flow.json · 편집) · 본문(children) · 후속 작업.
  ```tsx
  <FlowContentView stageKey="dss" sbIds={[doc.sb_id]} title={doc.title} refVer={`${doc.code} v${doc.ver}`}
    meta={[doc.saved_at && `${whenText(doc.saved_at)} 저장`, `공간 ${n}`, …]}   // falsy 는 빠진다 · ' · ' 로 잇는다
    follow={[{ key: 'sc', desc: '공간 7개에서 사용자가 겪는 장면을 만들어요' }, …]}   // 후속이 있는 콘텐츠만(rq → dss, dss → sc · sp)
    actions={<button className="fl-view__btn">…</button>}                         // flow.json 앞(Spec 의 XLSX 내려받기)
    editTo={…}>                                                                   // 기본: 지금 경로 + ?edit=1
    {본문}
  </FlowContentView>
  ```
  후속 작업 칸은 허브에서 그 Storyboard 에 이미 있는지 보고 「참조 · 열기」 / 「만들기」(`/<base>/new?sb=&auto=1`)를 스스로 고른다.
  flow.json 버튼은 허브 flow.json 전체에서 `stages.<key>` 를 강조하는 팝업(「이 콘텐츠가 담긴 줄」 · 「이 콘텐츠만」).
- `useEditMode()` → `{ editing, toView(drop?: string[]) }` · `editRoute(route)` — `@/shell` 에서.
- 본문 공용 클래스(`web/src/shell/flow/flow.css`): `.fl-vstrip`(흰 띠 h44 r12) · `.fl-vcard`(흰 판 r14) · `.fl-vtag` + `--ai` `--warn` `--line` `--brand` · `.fl-vnote`.
- ContentPopup 「편집 화면에서 고치기」 · Gate 「수정하기」 는 이미 `editRoute(...)` 로 편집 화면에 간다.
- `FlowDoneView` · `@/ui` 의 `FlowDone` 은 **지웠다**(import 하면 빌드가 깨진다). `FollowCard` 는 `refLabel?` · `cta?` 가 생겼다.

## 참고 구현(같은 모양으로) — 고객 요구사항

- `web/src/features/requirements/flow/RqView.tsx` — 보기 본문(보드 View content=rq).
- `web/src/features/requirements/flow/RqFlowPages.tsx` `Body` — `isSaved(d) && !editing` 이면 보기, 아니면 편집기. 저장 콜백에서
  `qc.setQueryData(<문서 키>, out.doc)` → 목록 · 허브 무효화(`useFlowInvalidate()`) → `toView()`. 보기의 `useShellPage` 는 `{ section, title: 참조, hasTask: false }`(스텝바 없음).
- `web/src/features/requirements/flow/rqflow.css` 의 `RQ_View` 절 — 클래스 접두사는 기능 것(`rqv-`).
- `web/e2e/requirements/rq-flow.spec.ts` 저장 이후 — 보기 검증(완료 문구 없음 · 값 · 폭 · flow.json · 편집 `?edit=1` · 목록 「열기」 · 새로고침도 보기).

## 기능 세션이 할 일

1. 보기 본문 컴포넌트 `<X>View`(기능 폴더) — 보드 View 의 그 content 본문을 px 그대로. 데이터는 그 기능 문서.
2. 편집 페이지: 저장한 문서 + `?edit` 없음 → 보기 / 그 밖 → 지금 편집 화면. `done` 상태 · `FlowDoneView` · 완료 화면 CSS(`*-done` 등) 삭제.
   저장 성공 → 문서 캐시 갱신 · 목록 · 허브 무효화 → `toView([...그 기능의 단계 · 탭 검색 조건])`.
   단계가 여러 개인 편집(DSS `?step=solution`, MI 검색 → 정제 등)은 편집 진입이 첫 단계부터인지 보드 View 의 「편집」 링크(editHref)를 따른다.
3. 기능 e2e(`web/e2e/<기능>/`) — 완료 화면을 기대하던 곳을 보기로 바꾸고, 다음을 검증:
   저장 → 같은 경로의 보기(`?edit` 없음) · 「저장했어요」 등 완료 문구 0개 · 보기의 실제 값 · 보드 고정 칸 폭 · 「편집」 → `?edit=1` 편집 화면 ·
   목록 「열기」 → 보기 · 새로고침해도 보기 · (후속이 있으면) 후속 카드 href. 화면은 `__screens__/<X>_View-new.png` 로 남긴다.
4. `make typecheck SERVICE=<기능>` · `make e2e-feature SERVICE=<기능>` 통과(스택은 이미 pm2 로 떠 있다 · `MODEL_MODE=mock`).
   병렬 부하로 흔들린 테스트는 단독으로 다시 돌려 확인한다. 백엔드 · 계약은 바꾸지 않는다(필요하면 보고만).
5. `services/<기능>/AGENTS.md` 의 화면 · 현재 상태 줄을 「완료 화면」 → 「보기」로 고친다. **커밋하지 않는다.**

## 하지 말 것

- 공용 경로(`web/src/shell`, `web/src/ui`, `libs/common`, `config`, `ops`, `scripts`) 수정 — 필요하면 보고.
- 다른 기능 폴더 · 다른 기능 e2e 수정.
- 보기에 완료 안내 · 요약본 추가분 · 접힌 JSON 칸 다시 넣기.
