// 자동 생성 — 직접 고치지 말 것. 원본: contracts/mi.json (make contracts)
export interface paths {
    "/v1/analyses": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Analyses
         * @description MI0 — 내 작업(상태 · 업종 · 검색 · 정렬) + 머리 집계 · 상태 필터 개수 · 업데이트 배너.
         */
        get: operations["list_analyses"];
        put?: never;
        /** Create Analysis */
        post: operations["create_analysis"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Analysis */
        get: operations["get_analysis"];
        put?: never;
        post?: never;
        /** Delete Analysis */
        delete: operations["delete_analysis"];
        options?: never;
        head?: never;
        /** Patch Analysis */
        patch: operations["patch_analysis"];
        trace?: never;
    };
    "/v1/analyses/{aid}/additions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add From Topbar
         * @description TopBar `현재 작업에 추가`(셸 onAdd) — 제품 · 솔루션은 비교표 `삼성` 쪽, 사례는 사내 사례 DB 출처 후보(§6.13).
         */
        post: operations["add_from_topbar"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/bundle": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Bundle
         * @description 읽기 전용 묶음(vp · 웹). 대상에 맞게 익명 처리를 마친 상태로 나간다. target=competitor 만 실명(작업 소유자만).
         */
        get: operations["get_bundle"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/changes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Changes */
        get: operations["get_changes"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/claims": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Claims */
        get: operations["list_claims"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/claims/{clm}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Claim */
        get: operations["get_claim"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/claims/{clm}/sources/{src}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /**
         * Remove Claim Source
         * @description 이 출처 빼기 → 주장 상태 다시 계산. 마지막 출처를 빼면 missing + 확정 필요 항목(AC-MI-40).
         */
        delete: operations["remove_claim_source"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/competitors": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Competitors */
        get: operations["list_competitors"];
        put?: never;
        /**
         * Add Competitor
         * @description 직접 추가 — 행을 바로 넣고(`직접 추가`, 고정) 짧은 잡이 이름 정규화 · 유형 · 한 줄 설명을 찾는다.
         */
        post: operations["add_competitor"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/competitors/{cmp}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Competitor */
        patch: operations["patch_competitor"];
        trace?: never;
    };
    "/v1/analyses/{aid}/criteria": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Criteria */
        get: operations["get_criteria"];
        /**
         * Put Criteria
         * @description 비교 기준 · 가중치(1~5) · 순서 · 켜기. 비율은 서버가 다시 계산(합계 100%).
         */
        put: operations["put_criteria"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/design": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Design */
        get: operations["get_design"];
        put?: never;
        /**
         * Run Design
         * @description `다음 · 분석 설계` — 잡 mi.design. 이미 돌고 있으면 취소 후 새로.
         */
        post: operations["run_design"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/design/memo": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Design Memo
         * @description 설계에 덧붙일 말 · MI1Q `판단에 도움이 될 말` — 업종 두 갈래로 기다리는 중이면 같은 잡에 힌트로 넣어 업종 판별만 다시.
         */
        post: operations["design_memo"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/duplicate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Duplicate Analysis
         * @description `복제해서 새 분석` — 범위 · 업종 · 경쟁사 · 기준이 같은 새 draft(결과 없음, AC-MI-81).
         */
        post: operations["duplicate_analysis"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/evidence": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Evidence
         * @description Storyboard Key Message 근거 스냅숏(MI4 `Key Message에 근거로 붙이기`) — storyboard 묶음과 같은 익명 · 대외비 규칙.
         *     mi 는 storyboard 를 부르지 않는다: 웹이 이 값을 `POST /api/storyboard/v1/storyboards/{sb}/key-messages/{kmsg}/evidence` 로 올린다.
         */
        get: operations["evidence"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/export-view": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Export View
         * @description MI4 화면 데이터(제안) — 보낼 제안서 · 시트 매핑 · 옵션 · 파일 · 다른 기능.
         */
        get: operations["export_view"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/exports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Create Export
         * @description PDF 리포트 · PPTX 한 장 요약 · Excel 표(잡 mi.export → export 서비스) — 완료 이벤트의 file_id 로 내려받기.
         */
        post: operations["create_export"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/facts:lookup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Facts Lookup
         * @description 제안서 PR7Q `MI에서 확인` — 저장된 주장 중 지표 · 이름 · 단위가 맞는 것을 결정적으로(새 검색 없음, AC-MI-94).
         */
        post: operations["facts_lookup"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/fix-items": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Fix Items */
        get: operations["list_fix_items"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/fix-items/{fix}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Patch Fix Item
         * @description 값 입력 → 숫자 · 비율 검증 → ok · 출처 user(AC-MI-45 · 46).
         */
        patch: operations["patch_fix_item"];
        trace?: never;
    };
    "/v1/analyses/{aid}/fix-items/{fix}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Cancel Fix Scan
         * @description 파일 읽는 중 `취소` — 잡 취소 + 항목은 이전 상태(AC-MI-48).
         */
        post: operations["cancel_fix_scan"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/fix-items/{fix}/question": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Customer Question
         * @description `고객 질문 복사` — 고객에게 물을 문장(LLM, 실패하면 템플릿).
         */
        post: operations["customer_question"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/fix-items/{fix}/revert": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Revert Fix Item */
        post: operations["revert_fix_item"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/fix-items/apply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Apply Fix Items
         * @description 확정값을 주장 문장 · 표 칸 · 시트에 반영하고 출처를 그 자료로 바꾼 새 버전(kind=fix, AC-MI-45 · 50).
         */
        post: operations["apply_fix_items"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/fix-items/parse": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Parse Fix Text
         * @description `값 알려주기` — 말에서 항목 · 값 · 근거를 짝지어 제안(자동 확정하지 않음, AC-MI-49).
         */
        post: operations["parse_fix_text"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/fix-items/scan": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Scan Fix Items
         * @description 사내 자료 올리기 → 열린 항목 값 찾기(잡 mi.fixscan). 해당 행은 wait · `올린 … 에서 값을 찾는 중`.
         */
        post: operations["scan_fix_items"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/followups": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Followup
         * @description 후속 질문 → 의도 판별(§7.9). question 이면 저장된 출처로 답, revision 이면 재분석 안을 만들고 MI3R 로.
         */
        post: operations["followup"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/handoffs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Create Handoff
         * @description 넘기기 준비 — 묻기 2~4 가 남으면 409 ASK_REQUIRED, 연결된 제안서가 없으면 422 NO_TARGET(§6.9).
         */
        post: operations["create_handoff"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/handoffs/{hof}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Handoff */
        patch: operations["patch_handoff"];
        trace?: never;
    };
    "/v1/analyses/{aid}/imports/requirements": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Import Requirements */
        post: operations["import_requirements"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/imports/storyboard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Storyboard
         * @description 웹이 Storyboard 계약으로 읽어 올린 요구사항 · Key Message · 고객 정보(mi 는 storyboard 를 부를 수 없음, §8).
         */
        post: operations["import_storyboard"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/onepager": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Onepager */
        get: operations["get_onepager"];
        put?: never;
        /**
         * Make Onepager
         * @description `한 장 요약` — IM-B 형식(4분면 + 결론) 요약. 새 검색 없음(잡 mi.onepager).
         */
        post: operations["make_onepager"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/progress": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Progress
         * @description MI3G 첫 그림 · 다시 들어올 때(제안) — 마지막 step/progress 스냅숏. 실시간은 jobs SSE.
         */
        get: operations["get_progress"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/proposal-handoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Proposal Handoff
         * @description ProposalHandoff v1(§6.14) — MI4 매핑과 같은 데이터. named=true 는 실명 확인 기록이 있을 때만(아니면 409 ASK_REQUIRED).
         */
        get: operations["proposal_handoff"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/questions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Ask Question */
        post: operations["ask_question"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/recheck": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Recheck */
        post: operations["recheck"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/result": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Result
         * @description MI3 — 분석한 영역 탭 · 블록 · 비교표 · 강점 · 출처 요약 · 확인 권장 칩. preview=true 면 실행 중 정리된 영역만(MI3G 미리 보기).
         */
        get: operations["get_result"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/revisions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Post Revision
         * @description 영역 · 행 · 강점 · 주장만 다시 분석하는 변경 안(잡 mi.revise) — 바로 반영하지 않는다.
         */
        post: operations["post_revision"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/revisions/{rev}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Revision */
        get: operations["get_revision"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/revisions/{rev}/apply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Apply Revision
         * @description 되돌리지 않은 변경만 반영한 새 버전(kind=revision). 기준 버전이 그새 바뀌었으면 409 VERSION_CONFLICT(AC-MI-57).
         */
        post: operations["apply_revision"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/revisions/{rev}/changes/{chg}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Change */
        patch: operations["patch_change"];
        trace?: never;
    };
    "/v1/analyses/{aid}/revisions/{rev}/discard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Discard Revision */
        post: operations["discard_revision"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/revisions/{rev}/revert-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Revert All */
        post: operations["revert_all"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/revisions/{rev}/rounds": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Round
         * @description 수정 요청 · 빠른 요청 — 같은 안에 라운드를 더한다(변경 목록은 늘 기준 버전 대비 누적 차이).
         */
        post: operations["add_round"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Run Analysis
         * @description 잡 mi.analyze. mode: full(전부 다시) · changed_only(바뀐 영역 + areas) · resume(정리 못 한 영역) · 생략 = 의존 해시로 바뀐 것만.
         */
        post: operations["run_analysis"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/share": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Share
         * @description 링크 공유 — workspace 공유 링크(보기 · 코멘트). 공유 화면은 익명 표기.
         */
        post: operations["share"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/shared-view": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Shared View
         * @description 링크 공유 화면(`/mi/:id/shared`) 데이터 — MI3 결과와 같은 모양, 경쟁사는 내보내기 표기(실명 · 별칭 없음, AC-MI-67).
         */
        get: operations["shared_view"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/slides": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Slides */
        get: operations["get_slides"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/slides/{sht}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Patch Slide
         * @description 포함 체크 → included · 고정. 대안 코드 → 그 템플릿으로 바꾸고 고정.
         */
        patch: operations["patch_slide"];
        trace?: never;
    };
    "/v1/analyses/{aid}/slides/{sht}/candidates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Slide Candidates
         * @description MI3L — 요청 해석 · 선택지 A/B/C · 고를 수 있는 레이아웃 · 적합도(§7.8).
         */
        get: operations["slide_candidates"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/slides/{sht}/layout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Choose Layout */
        post: operations["choose_layout"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/slides/requests": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Slide Request
         * @description 구성 요청 · 보내기 전 요청 → 레이아웃 요청이면 MI3L(그 시트), 포함 · 제외 요청이면 바로 반영.
         */
        post: operations["slide_request"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/sources": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Sources
         * @description 출처 목록. tab 을 주면 그 탭 번호 · 카드(종류 필터: public · kb_case · needs_check · …).
         */
        get: operations["list_sources"];
        put?: never;
        /**
         * Add Source
         * @description 출처 직접 추가 — URL 수집 또는 파일 추출 → §7.6 대조 → 그 주장 인용(잡 mi.source_add).
         */
        post: operations["add_source"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/sources/{src}/snapshot": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Snapshot */
        get: operations["get_snapshot"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/table-text": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Table Text
         * @description MI3 `표 복사` — 비교표를 탭으로 나눈 글(고객용이면 익명 표기).
         */
        get: operations["table_text"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/versions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Versions */
        get: operations["list_versions"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/versions/{n}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Restore Version
         * @description 되돌리기 = 내용이 v{n} 과 같은 새 버전(kind=restore, AC-MI-80).
         */
        post: operations["restore_version"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/capabilities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Capabilities */
        get: operations["capabilities"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/imports/competitor": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Competitor
         * @description CA5 `Market Intelligence 작업에 합치기` — 경쟁 영역에 내용이 있으면 재분석 안(MI3R), 없으면 바로 새 버전(kind=import).
         */
        post: operations["import_competitor"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/info": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Info */
        get: operations["info"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/mi-flows": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Mi Flows */
        get: operations["list_mi_flows"];
        put?: never;
        /**
         * Create Mi Flow
         * @description Gate 에서 고른 Storyboard 로 MI 를 만들고 Storyboard 분석을 시작한다(CF-08 예외 — MI 는 분석 로딩이 먼저).
         */
        post: operations["create_mi_flow"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/mi-flows/{flow_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Mi Flow */
        get: operations["get_mi_flow"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Mi Flow */
        patch: operations["patch_mi_flow"];
        trace?: never;
    };
    "/v1/mi-flows/{flow_id}:analyze": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Analyze Mi Flow */
        post: operations["analyze_mi_flow"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/mi-flows/{flow_id}:finish": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Finish Mi Flow */
        post: operations["finish_mi_flow"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/mi-flows/{flow_id}:search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Search Mi Flow */
        post: operations["search_mi_flow"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/mi-flows/{flow_id}/items/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Mi Flow Item */
        patch: operations["patch_mi_flow_item"];
        trace?: never;
    };
    "/v1/mi-flows/{flow_id}/stage": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Mi Flow Stage */
        get: operations["get_mi_flow_stage"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/routing-rules": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Routing Rules
         * @description MIR 시트 — 서비스 설정(services/mi/config/routing.yaml)을 그대로 그린다. 서버 판단 코드도 같은 설정을 읽는다.
         */
        get: operations["routing_rules"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/segments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Segments
         * @description 16업종 · 사례 수(kb 프록시) + MI0 업종 칩(내 작업 업종 먼저, 남는 자리는 MI_HOME_SEGMENTS 순서).
         */
        get: operations["list_segments"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/segments/{code}/insights": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Segment Insights */
        get: operations["segment_insights"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/segments/detect": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Detect Segment
         * @description MI1I `업종 감지` — 빠른 경로: kb 근거만(LLM 없음) `0.6 × kb + 0.4 × 단서`.
         */
        post: operations["detect_segment"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AdditionsIn */
        AdditionsIn: {
            /** Ids */
            ids: string[];
            /**
             * Kind
             * @enum {string}
             */
            kind: "product" | "solution" | "case" | "image";
        };
        /** AdditionsOut */
        AdditionsOut: {
            /** Added */
            added: string[];
        };
        /** Alternative */
        Alternative: {
            /** Code */
            code: string;
            /** Fit */
            fit: number;
        };
        /** Analysis */
        Analysis: {
            /** Analyzed At */
            analyzed_at?: string | null;
            /**
             * Anonymize
             * @default true
             */
            anonymize: boolean;
            /**
             * Competitors
             * @default []
             */
            competitors: components["schemas"]["Competitor"][];
            /**
             * Created At
             * @default
             */
            created_at: string;
            /**
             * Criteria
             * @default []
             */
            criteria: components["schemas"]["Criterion"][];
            /** Current Job Id */
            current_job_id?: string | null;
            /** Customer Name */
            customer_name?: string | null;
            /**
             * @default {
             *       "target_sources": 30,
             *       "eta_s": 180
             *     }
             */
            depth: components["schemas"]["Depth"];
            /** Design Job Id */
            design_job_id?: string | null;
            /**
             * Design Status
             * @default none
             * @enum {string}
             */
            design_status: "none" | "running" | "ask" | "done" | "failed";
            /**
             * Edited After Analysis
             * @default false
             */
            edited_after_analysis: boolean;
            /**
             * Eta S
             * @default 180
             */
            eta_s: number;
            /**
             * Files
             * @default []
             */
            files: components["schemas"]["AnalysisFile"][];
            /** Id */
            id: string;
            /**
             * Input Kind
             * @description MI1Q `{입력 종류}` — 회의록 · RFP · 요구사항 · 메모
             * @default
             */
            input_kind: string;
            /**
             * @default {
             *       "kb_case_count": 0,
             *       "included_file_ids": [],
             *       "excluded_file_ids": [],
             *       "summary": ""
             *     }
             */
            internal: components["schemas"]["InternalDecision"];
            /** Last Screen */
            last_screen?: string | null;
            /** @default {} */
            links: components["schemas"]["Links"];
            /**
             * Memos
             * @default []
             */
            memos: components["schemas"]["MemoItem"][];
            /**
             * Naming Mode
             * @default letter
             * @enum {string}
             */
            naming_mode: "letter" | "type";
            /** Next Recheck At */
            next_recheck_at?: string | null;
            /**
             * One Line Memo
             * @default false
             */
            one_line_memo: boolean;
            /** Owner Id */
            owner_id: string;
            /**
             * Owner Name
             * @default
             */
            owner_name: string;
            preset?: components["schemas"]["Preset"] | null;
            /** Project Id */
            project_id?: string | null;
            /**
             * Req Summary
             * @default
             */
            req_summary: string;
            /**
             * Requirements
             * @default []
             */
            requirements: components["schemas"]["Requirement"][];
            /**
             * Requirements Text
             * @default
             */
            requirements_text: string;
            result?: components["schemas"]["ResultView"] | null;
            /**
             * Route
             * @default
             */
            route: string;
            /**
             * Run Label
             * @description `분석 시작 (약 {m}분)`
             * @default
             */
            run_label: string;
            /**
             * Samsung Products
             * @default []
             */
            samsung_products: components["schemas"]["SamsungProduct"][];
            /**
             * @default {
             *       "areas": [],
             *       "reasons": {},
             *       "reduced": []
             *     }
             */
            scope: components["schemas"]["ScopeDecision"];
            /**
             * Scope Desc
             * @default {}
             */
            scope_desc: {
                [key: string]: string;
            };
            /**
             * @default {
             *       "candidates": [],
             *       "clues": [],
             *       "llm_failed": false
             *     }
             */
            segment: components["schemas"]["SegmentDecision"];
            /**
             * Status
             * @default draft
             * @enum {string}
             */
            status: "draft" | "designing" | "ask" | "designed" | "queued" | "running" | "stopped" | "done" | "upd" | "failed";
            /**
             * Status Label
             * @default
             */
            status_label: string;
            /**
             * Title
             * @default
             */
            title: string;
            /**
             * Topic
             * @default
             */
            topic: string;
            /**
             * Updated At
             * @default
             */
            updated_at: string;
            /**
             * @default {
             *       "reason": ""
             *     }
             */
            usage: components["schemas"]["UsageDecision"];
            /**
             * Version
             * @description 마지막으로 완료된 결과 버전(0 = 결과 없음)
             * @default 0
             */
            version: number;
        };
        /** AnalysisAction */
        AnalysisAction: {
            /**
             * Kind
             * @default open
             * @enum {string}
             */
            kind: "fix" | "rerun" | "progress" | "continue" | "open" | "retry";
            /** Label */
            label: string;
            /** Route */
            route: string;
        };
        /** AnalysisFile */
        AnalysisFile: {
            /**
             * Classification
             * @default internal
             * @enum {string}
             */
            classification: "public" | "internal" | "confidential";
            /**
             * Doc Kind
             * @default other
             * @enum {string}
             */
            doc_kind: "rfp" | "minutes" | "ir" | "internal_research" | "deployment_report" | "price_list" | "spec_sheet" | "customer_material" | "other";
            /** File Id */
            file_id: string;
            /**
             * Include
             * @default true
             */
            include: boolean;
            /**
             * Name
             * @default
             */
            name: string;
        };
        /** AnalysisList */
        AnalysisList: {
            banner?: components["schemas"]["UpdBanner"] | null;
            counts: components["schemas"]["ListCounts"];
            /**
             * Fix Open Works
             * @default 0
             */
            fix_open_works: number;
            /**
             * Header
             * @default
             */
            header: string;
            /** Items */
            items: components["schemas"]["AnalysisListItem"][];
            /** Next Cursor */
            next_cursor?: string | null;
            /**
             * Upd Changes
             * @default {}
             */
            upd_changes: {
                [key: string]: unknown;
            };
        };
        /** AnalysisListItem */
        AnalysisListItem: {
            action: components["schemas"]["AnalysisAction"];
            /**
             * Changes Head
             * @description upd 행 메뉴 머리 상자 `{title, summary}`
             */
            changes_head?: {
                [key: string]: unknown;
            } | null;
            /** Current Job Id */
            current_job_id?: string | null;
            /**
             * Fix Open
             * @default 0
             */
            fix_open: number;
            /**
             * Has Competitors
             * @default false
             */
            has_competitors: boolean;
            /** Id */
            id: string;
            /**
             * Menu
             * @default []
             */
            menu: components["schemas"]["MenuItem"][];
            /**
             * Note
             * @default
             */
            note: string;
            /**
             * Owner Name
             * @default
             */
            owner_name: string;
            /** Proposal Title */
            proposal_title?: string | null;
            /** Route */
            route: string;
            /**
             * Scope Label
             * @default
             */
            scope_label: string;
            /**
             * Scope Selected
             * @default false
             */
            scope_selected: boolean;
            /** Segment */
            segment?: string | null;
            /**
             * Segment Label
             * @default —
             */
            segment_label: string;
            /**
             * Status
             * @enum {string}
             */
            status: "draft" | "designing" | "ask" | "designed" | "queued" | "running" | "stopped" | "done" | "upd" | "failed";
            /** Status Label */
            status_label: string;
            /**
             * Status Tone
             * @default draft
             * @enum {string}
             */
            status_tone: "done" | "upd" | "run" | "draft";
            /**
             * Sub
             * @default
             */
            sub: string;
            /**
             * Time Label
             * @default
             */
            time_label: string;
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
            /**
             * Version
             * @default 0
             */
            version: number;
        };
        /** AnalysisPatch */
        AnalysisPatch: {
            /** Anonymize */
            anonymize?: boolean | null;
            /** Customer Name */
            customer_name?: string | null;
            /** File Ids */
            file_ids?: string[] | null;
            /** Files */
            files?: components["schemas"]["FileIn"][] | null;
            internal?: components["schemas"]["InternalPatch"] | null;
            /** Last Screen */
            last_screen?: string | null;
            links?: components["schemas"]["Links"] | null;
            /** Naming Mode */
            naming_mode?: ("letter" | "type") | null;
            preset?: components["schemas"]["Preset"] | null;
            /** Requirements */
            requirements?: components["schemas"]["RequirementIn"][] | null;
            /** Requirements Text */
            requirements_text?: string | null;
            scope?: components["schemas"]["ScopePatch"] | null;
            segment?: components["schemas"]["SegmentPatch"] | null;
            /** Title */
            title?: string | null;
            usage?: components["schemas"]["UsagePatch"] | null;
        };
        /** AnswerCitation */
        AnswerCitation: {
            /** N */
            n: number;
            /** Source Id */
            source_id: string;
        };
        /** AnswerOut */
        AnswerOut: {
            /** Answer Md */
            answer_md: string;
            /**
             * Answerable
             * @default true
             */
            answerable: boolean;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["AnswerCitation"][];
        };
        /** AreaProgress */
        AreaProgress: {
            /**
             * Area
             * @enum {string}
             */
            area: "market" | "customer" | "user" | "competitor";
            /** Name */
            name: string;
            /**
             * Note
             * @default
             */
            note: string;
            /**
             * Status
             * @enum {string}
             */
            status: "wait" | "run" | "done" | "failed";
        };
        /** AutoRunAccepted */
        AutoRunAccepted: {
            /** Analysis Id */
            analysis_id: string;
            /** Job Id */
            job_id: string;
            /**
             * Status
             * @default queued
             * @constant
             */
            status: "queued";
        };
        /** Bundle */
        Bundle: {
            /** Analysis Id */
            analysis_id: string;
            /**
             * Anonymization
             * @default {}
             */
            anonymization: {
                [key: string]: unknown;
            };
            /** Competitors */
            competitors?: {
                [key: string]: unknown;
            }[] | null;
            /** Criteria */
            criteria?: {
                [key: string]: unknown;
            }[] | null;
            /**
             * Customer
             * @default {}
             */
            customer: {
                [key: string]: unknown;
            };
            /** Handoff Id */
            handoff_id?: string | null;
            /**
             * @default {
             *       "cite_sources": true,
             *       "fix_notes": true,
             *       "link_why": true
             *     }
             */
            options: components["schemas"]["HandoffOptions"];
            /** Requirements */
            requirements?: {
                [key: string]: unknown;
            }[] | null;
            /** Segment */
            segment?: string | null;
            /**
             * Sheets
             * @default []
             */
            sheets: components["schemas"]["BundleSheet"][];
            /** Target */
            target: string;
            /** Usage */
            usage?: string | null;
            /** Version */
            version: number;
            /** Vp Materials */
            vp_materials?: {
                [key: string]: unknown;
            } | null;
            /** Why Samsung */
            why_samsung?: {
                [key: string]: unknown;
            } | null;
        };
        /** BundleSheet */
        BundleSheet: {
            /**
             * Content
             * @default {}
             */
            content: {
                [key: string]: unknown;
            };
            /**
             * Fact Check
             * @default []
             */
            fact_check: {
                [key: string]: unknown;
            }[];
            /**
             * Footnotes
             * @default []
             */
            footnotes: {
                [key: string]: unknown;
            }[];
            /** Id */
            id: string;
            /** Sheet Name */
            sheet_name: string;
            /** Sheet Type */
            sheet_type: string;
            /** Template Code */
            template_code: string;
            /**
             * Why
             * @default
             */
            why: string;
        };
        /** Cagr */
        Cagr: {
            claim?: components["schemas"]["ClaimRef"] | null;
            /**
             * Period
             * @default
             */
            period: string;
            /** Value */
            value?: number | null;
        };
        /** CaImportAccepted */
        CaImportAccepted: {
            /** Analysis Id */
            analysis_id: string;
            /** Job Id */
            job_id: string;
            /** Revision Id */
            revision_id?: string | null;
            /**
             * Status
             * @default queued
             * @constant
             */
            status: "queued";
        };
        /** CaImportIn */
        CaImportIn: {
            /** Analysis Id */
            analysis_id?: string | null;
            /** Ca Bundle */
            ca_bundle: {
                [key: string]: unknown;
            };
            /** Customer Name */
            customer_name?: string | null;
        };
        /** CandidatesView */
        CandidatesView: {
            /**
             * Explanation
             * @default
             */
            explanation: string;
            /**
             * Head
             * @default
             */
            head: string;
            /**
             * Options
             * @default []
             */
            options: components["schemas"]["LayoutOption"][];
            /**
             * Others
             * @default []
             */
            others: {
                [key: string]: unknown;
            }[];
            /**
             * Request Text
             * @default
             */
            request_text: string;
            /** Requested */
            requested?: string | null;
            sheet: components["schemas"]["SlidePlan"];
            /**
             * Templates
             * @default []
             */
            templates: components["schemas"]["TemplateCandidate"][];
        };
        /** Capabilities */
        Capabilities: {
            /** Fetch */
            fetch: boolean;
            /** I2T */
            i2t: boolean;
            /**
             * Mode
             * @default
             */
            mode: string;
            /** Search Api */
            search_api: {
                [key: string]: unknown;
            };
            /** Websearch */
            websearch: {
                [key: string]: unknown;
            };
        };
        /** Change */
        Change: {
            /** After */
            after?: unknown;
            /** Before */
            before?: unknown;
            /**
             * Claim Ids
             * @default []
             */
            claim_ids: string[];
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "row_add" | "row_remove" | "value_edit" | "strength_edit" | "text_edit" | "source_add";
            /**
             * Label
             * @default
             */
            label: string;
            /**
             * Reverted
             * @default false
             */
            reverted: boolean;
            /** Revision Id */
            revision_id: string;
            /** Target */
            target: {
                [key: string]: unknown;
            };
        };
        /** ChangePatch */
        ChangePatch: {
            /** Reverted */
            reverted: boolean;
        };
        /** ChangesView */
        ChangesView: {
            /**
             * Affected Areas
             * @default []
             */
            affected_areas: ("market" | "customer" | "user" | "competitor")[];
            /**
             * Eta Label
             * @default
             */
            eta_label: string;
            /**
             * Head
             * @default
             */
            head: string;
            /** Items */
            items: components["schemas"]["RecheckChange"][];
            /**
             * Summary
             * @default
             */
            summary: string;
        };
        /** CheckChip */
        CheckChip: {
            /** Count */
            count?: number | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "segment" | "competitors" | "conflict" | "inferred";
            /** Label */
            label: string;
            /** Mode */
            mode?: ("auto" | "check" | "ask" | "pin") | null;
            /** Target */
            target?: string | null;
        };
        /** CitationOut */
        CitationOut: {
            /** N */
            n: number;
            /** Source Id */
            source_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "matched" | "needs_check" | "unverifiable" | "stale";
        };
        /** ClaimDetail */
        ClaimDetail: {
            /** Cards */
            cards: components["schemas"]["SourceCard"][];
            claim: components["schemas"]["ClaimItem"];
            /** Conflict */
            conflict?: {
                [key: string]: unknown;
            } | null;
            /** Counts */
            counts: {
                [key: string]: number;
            };
            /** Fix Id */
            fix_id?: string | null;
            /**
             * Tab
             * @enum {string}
             */
            tab: "market" | "customer" | "user" | "competitor";
            /** Tab Label */
            tab_label: string;
        };
        /** ClaimItem */
        ClaimItem: {
            /**
             * Area
             * @enum {string}
             */
            area: "market" | "customer" | "user" | "competitor";
            /**
             * Block Path
             * @default
             */
            block_path: string;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["CitationOut"][];
            /** Id */
            id: string;
            /**
             * Inferred
             * @default false
             */
            inferred: boolean;
            /** Label */
            label: string;
            /**
             * Status
             * @enum {string}
             */
            status: "matched" | "needs_check" | "conflict" | "stale" | "confirmed" | "checking" | "missing";
            /** Text */
            text: string;
        };
        /** ClaimList */
        ClaimList: {
            /**
             * Badges
             * @default {}
             */
            badges: {
                [key: string]: number;
            };
            /** Items */
            items: components["schemas"]["ClaimItem"][];
            /**
             * Needs Check Total
             * @default 0
             */
            needs_check_total: number;
            /**
             * Summary Text
             * @default
             */
            summary_text: string;
            /**
             * Tab Sources
             * @default {}
             */
            tab_sources: {
                [key: string]: number;
            };
        };
        /**
         * ClaimRef
         * @description 블록 안 문장 — 화면 문장 + 탭 안 출처 번호.
         */
        ClaimRef: {
            /** Id */
            id: string;
            /**
             * Inferred
             * @default false
             */
            inferred: boolean;
            /** Label */
            label: string;
            /**
             * Ns
             * @default []
             */
            ns: number[];
            /**
             * Status
             * @enum {string}
             */
            status: "matched" | "needs_check" | "conflict" | "stale" | "confirmed" | "checking" | "missing";
            /** Text */
            text: string;
            /**
             * Unverified Numbers
             * @default false
             */
            unverified_numbers: boolean;
        };
        /** Clue */
        Clue: {
            /** Code */
            code: string;
            /** Text */
            text: string;
            /**
             * Weight
             * @default 0
             */
            weight: number;
        };
        /** CompareTable */
        CompareTable: {
            /** Columns */
            columns: components["schemas"]["TableColumn"][];
            /** Rows */
            rows: components["schemas"]["TableRow"][];
        };
        /** Competitor */
        Competitor: {
            /**
             * Aliases
             * @default []
             */
            aliases: string[];
            /** Confidence */
            confidence?: number | null;
            /**
             * Desc
             * @default
             */
            desc: string;
            /**
             * Display
             * @description 작업 화면 표기(`경쟁사 {글자}`)
             * @default
             */
            display: string;
            /**
             * Evidence Source Ids
             * @default []
             */
            evidence_source_ids: string[];
            /**
             * Export Display
             * @description 내보내기 표기 미리보기(익명 방식 · 켜짐 여부에 따라)
             * @default
             */
            export_display: string;
            /** Id */
            id: string;
            /**
             * Kind Label
             * @default
             */
            kind_label: string;
            /** Letter */
            letter: string;
            /**
             * Lookup
             * @default done
             * @enum {string}
             */
            lookup: "done" | "pending" | "failed";
            /**
             * Order
             * @default 0
             */
            order: number;
            /**
             * Origin
             * @default auto
             * @enum {string}
             */
            origin: "auto" | "user" | "ca_import" | "mi_rfp";
            /**
             * Pinned
             * @default false
             */
            pinned: boolean;
            /** Real Name */
            real_name: string;
            /**
             * Removed
             * @default false
             */
            removed: boolean;
            /**
             * Tag
             * @description `자동 추천` · `직접 추가` · `경쟁사 분석에서`
             * @default
             */
            tag: string;
        };
        /** CompetitorAccepted */
        CompetitorAccepted: {
            /** Competitor Id */
            competitor_id: string;
            /** Job Id */
            job_id: string;
            /**
             * Status
             * @default queued
             * @constant
             */
            status: "queued";
        };
        /** CompetitorAddIn */
        CompetitorAddIn: {
            /** Name */
            name: string;
        };
        /** CompetitorBlock */
        CompetitorBlock: {
            /**
             * Samsung Products
             * @default []
             */
            samsung_products: components["schemas"]["SamsungProduct"][];
            /**
             * Strengths
             * @default []
             */
            strengths: components["schemas"]["Strength"][];
            table?: components["schemas"]["CompareTable"] | null;
        };
        /** CompetitorList */
        CompetitorList: {
            /** Counts */
            counts: {
                [key: string]: number;
            };
            /** Items */
            items: components["schemas"]["Competitor"][];
            /**
             * Removed
             * @default []
             */
            removed: components["schemas"]["Competitor"][];
        };
        /** CompetitorPatch */
        CompetitorPatch: {
            /** Order */
            order?: number | null;
            /** Removed */
            removed?: boolean | null;
        };
        /** CompositionItem */
        CompositionItem: {
            claim?: components["schemas"]["ClaimRef"] | null;
            /** Label */
            label: string;
            /**
             * Unit
             * @default %
             */
            unit: string;
            /** Value */
            value?: number | null;
        };
        /** CreateAnalysisIn */
        CreateAnalysisIn: {
            /**
             * Auto Run
             * @default false
             */
            auto_run: boolean;
            /**
             * Customer
             * @description 제안서 M2 별칭 `{name}`
             */
            customer?: {
                [key: string]: unknown;
            } | null;
            /** Customer Name */
            customer_name?: string | null;
            /**
             * File Ids
             * @default []
             */
            file_ids: string[];
            links?: components["schemas"]["Links"] | null;
            preset?: components["schemas"]["Preset"] | null;
            /** Project Id */
            project_id?: string | null;
            /** Proposal Type */
            proposal_type?: ("standard" | "quickwin" | "solution") | null;
            /** Purpose */
            purpose?: ("proposal" | "user") | null;
            /** Requirements Text */
            requirements_text?: string | null;
            /**
             * Rq Ref
             * @description `{rq_id, version}` (제안서 M2)
             */
            rq_ref?: {
                [key: string]: unknown;
            } | null;
            /**
             * Scope
             * @description 고정할 범위(market · customer · user(users) · competitor)
             */
            scope?: string[] | null;
            /** Segment Pin */
            segment_pin?: string | null;
        };
        /** CriteriaList */
        CriteriaList: {
            /** Items */
            items: components["schemas"]["Criterion"][];
            /**
             * Suggestion Head
             * @default
             */
            suggestion_head: string;
            /**
             * Suggestions
             * @default []
             */
            suggestions: components["schemas"]["NamedCount"][];
        };
        /** CriteriaPut */
        CriteriaPut: {
            /** Items */
            items: components["schemas"]["CriterionIn"][];
        };
        /** Criterion */
        Criterion: {
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /** Id */
            id: string;
            /** Name */
            name: string;
            /**
             * Order
             * @default 0
             */
            order: number;
            /**
             * Pct
             * @default 0
             */
            pct: number;
            /**
             * Pinned
             * @default false
             */
            pinned: boolean;
            /** Requirement Id */
            requirement_id?: string | null;
            /**
             * Source
             * @default requirements
             * @enum {string}
             */
            source: "requirements" | "industry_cases" | "user" | "preset";
            /** Source Count */
            source_count?: number | null;
            /**
             * Source Label
             * @description `요구사항` · `업종 사례 {n}건` · `직접 추가`
             * @default
             */
            source_label: string;
            /**
             * Weight
             * @default 3
             */
            weight: number;
        };
        /** CriterionIn */
        CriterionIn: {
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /** Id */
            id?: string | null;
            /** Name */
            name: string;
            /** Order */
            order?: number | null;
            /**
             * Source
             * @default user
             * @enum {string}
             */
            source: "requirements" | "industry_cases" | "user" | "preset";
            /** Source Count */
            source_count?: number | null;
            /**
             * Weight
             * @default 3
             */
            weight: number;
        };
        /** CustomerBlock */
        CustomerBlock: {
            /**
             * Expansion
             * @default []
             */
            expansion: components["schemas"]["ClaimRef"][];
            /**
             * Ops Challenges
             * @default []
             */
            ops_challenges: components["schemas"]["OpsChallenge"][];
            /**
             * Reduced
             * @default false
             */
            reduced: boolean;
            /**
             * Strategy
             * @default []
             */
            strategy: components["schemas"]["ClaimRef"][];
            /**
             * Structure
             * @default []
             */
            structure: components["schemas"]["StructureItem"][];
            summary?: components["schemas"]["ClaimRef"] | null;
        };
        /** CustomerQuestionOut */
        CustomerQuestionOut: {
            /** Question */
            question: string;
        };
        /** Decision */
        Decision: {
            /**
             * Change Route
             * @default
             */
            change_route: string;
            /**
             * Depends On
             * @default []
             */
            depends_on: string[];
            /** Display Value */
            display_value: string;
            /**
             * Input Hash
             * @default
             */
            input_hash: string;
            /**
             * Key
             * @enum {string}
             */
            key: "segment" | "usage" | "scope" | "competitors" | "naming" | "internal" | "depth";
            /** Label */
            label: string;
            /**
             * Mode
             * @enum {string}
             */
            mode: "auto" | "check" | "ask" | "pin";
            /** Reason */
            reason: string;
            /**
             * Updated At
             * @default
             */
            updated_at: string;
        };
        /** Depth */
        Depth: {
            /**
             * Eta S
             * @default 180
             */
            eta_s: number;
            /**
             * Target Sources
             * @default 30
             */
            target_sources: number;
        };
        /** DesignView */
        DesignView: {
            /**
             * Ask
             * @description awaiting_input 데이터(업종 두 갈래)
             */
            ask?: {
                [key: string]: unknown;
            } | null;
            /**
             * Decisions
             * @default []
             */
            decisions: components["schemas"]["Decision"][];
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            /** Job Id */
            job_id?: string | null;
            /**
             * Run Label
             * @default
             */
            run_label: string;
            /**
             * Sheets Head
             * @default
             */
            sheets_head: string;
            /**
             * Sheets Preview
             * @default []
             */
            sheets_preview: components["schemas"]["SheetPreview"][];
            /**
             * Status
             * @enum {string}
             */
            status: "none" | "running" | "ask" | "done" | "failed";
            /**
             * Tally
             * @default {}
             */
            tally: {
                [key: string]: number;
            };
            /**
             * Usage Label
             * @default
             */
            usage_label: string;
        };
        /** DetectIn */
        DetectIn: {
            /** Analysis Id */
            analysis_id?: string | null;
            /**
             * Text
             * @default
             */
            text: string;
        };
        /** DetectOut */
        DetectOut: {
            /**
             * Basis
             * @description `Storyboard '{SB 제목}' 기준` · `입력한 요구사항 기준` · `정의서 기준`
             * @default
             */
            basis: string;
            /** Candidates */
            candidates: components["schemas"]["SegmentCandidate"][];
            /**
             * Clues
             * @default []
             */
            clues: components["schemas"]["Clue"][];
            /** Customer Name */
            customer_name?: string | null;
            /** Top */
            top?: string | null;
        };
        /** DuplicateIn */
        DuplicateIn: {
            /**
             * Keep Scope
             * @default true
             */
            keep_scope: boolean;
        };
        /** ErrorDetail */
        ErrorDetail: {
            /**
             * Code
             * @description UPPER_SNAKE 오류 코드
             */
            code: string;
            /** Details */
            details?: {
                [key: string]: unknown;
            };
            /**
             * Message
             * @description 사람이 읽는 한국어 메시지
             */
            message: string;
        };
        /** ErrorResponse */
        ErrorResponse: {
            error: components["schemas"]["ErrorDetail"];
        };
        /** EvidenceCitation */
        EvidenceCitation: {
            /** Title */
            title: string;
            /** Url */
            url?: string | null;
        };
        /** EvidenceItem */
        EvidenceItem: {
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["EvidenceCitation"][];
            /**
             * Default On
             * @default false
             */
            default_on: boolean;
            /**
             * Key
             * @description `strength:{i}` · `number:{i}` · `challenge:{i}`
             */
            key: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "strength" | "number" | "challenge";
            /** Kind Label */
            kind_label: string;
            /**
             * Status
             * @description 수치만 — `원문 일치` · `확인 필요`
             * @default
             */
            status: string;
            /** Text */
            text: string;
        };
        /**
         * EvidenceSnapshot
         * @description Storyboard Key Message 근거 스냅숏(02-storyboard §8.3) — 웹이 storyboard `key-messages/{kmsg}/evidence` 로 올린다. 익명 처리를 마친 값.
         */
        EvidenceSnapshot: {
            /** Analysis Id */
            analysis_id: string;
            /**
             * Items
             * @default []
             */
            items: components["schemas"]["EvidenceItem"][];
            /**
             * Source
             * @description `{service:'mi', ref_id, title, route}` — PostEvidence.source 그대로
             */
            source?: {
                [key: string]: unknown;
            };
            /** Storyboard Id */
            storyboard_id?: string | null;
            /** Storyboard Title */
            storyboard_title?: string | null;
            /** Version */
            version: number;
        };
        /** ExportIn */
        ExportIn: {
            /**
             * Audience
             * @default customer
             * @enum {string}
             */
            audience: "customer" | "internal";
            /**
             * Format
             * @enum {string}
             */
            format: "pdf_report" | "pptx_onepager" | "xlsx_table";
        };
        /**
         * ExportView
         * @description MI4 화면 데이터(제안 — 문서 §4.14 표시 데이터를 한 번에).
         */
        ExportView: {
            /**
             * Files
             * @default []
             */
            files: {
                [key: string]: string;
            }[];
            /**
             * Footer
             * @default
             */
            footer: string;
            /**
             * Mapping Head
             * @default
             */
            mapping_head: string;
            /**
             * Next Features
             * @default []
             */
            next_features: {
                [key: string]: unknown;
            }[];
            /**
             * Options
             * @default {}
             */
            options: {
                [key: string]: unknown;
            };
            /**
             * Proposals
             * @default []
             */
            proposals: {
                [key: string]: unknown;
            }[];
            /**
             * Rows
             * @default []
             */
            rows: components["schemas"]["SlidePlan"][];
            /**
             * Show Link Why
             * @default false
             */
            show_link_why: boolean;
            /**
             * Strengths Count
             * @default 0
             */
            strengths_count: number;
            /** Target */
            target?: {
                [key: string]: unknown;
            } | null;
            /** Usage */
            usage?: ("standard" | "solution" | "quickwin" | "exec_onepager" | "none") | null;
            /**
             * Usage Label
             * @default
             */
            usage_label: string;
            /** Vp Card */
            vp_card?: {
                [key: string]: unknown;
            } | null;
        };
        /** FactCandidate */
        FactCandidate: {
            /** Claim Id */
            claim_id: string;
            /** Source */
            source?: {
                [key: string]: unknown;
            } | null;
            /**
             * Status
             * @enum {string}
             */
            status: "matched" | "needs_check" | "conflict" | "stale" | "confirmed" | "checking" | "missing";
            /** Unit */
            unit?: string | null;
            /** Value */
            value: string;
        };
        /** FactQuestion */
        FactQuestion: {
            /** Context */
            context?: string | null;
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Unit */
            unit?: string | null;
        };
        /** FactsLookupIn */
        FactsLookupIn: {
            /** Questions */
            questions: components["schemas"]["FactQuestion"][];
            /**
             * Research
             * @default false
             */
            research: boolean;
        };
        /** FactsLookupItem */
        FactsLookupItem: {
            /** Candidates */
            candidates: components["schemas"]["FactCandidate"][];
            /** Key */
            key: string;
        };
        /** FactsLookupOut */
        FactsLookupOut: {
            /** Items */
            items: components["schemas"]["FactsLookupItem"][];
        };
        /** FileIn */
        FileIn: {
            /** Classification */
            classification?: ("public" | "internal" | "confidential") | null;
            /** Doc Kind */
            doc_kind?: string | null;
            /** File Id */
            file_id: string;
            /** Include */
            include?: boolean | null;
            /** Name */
            name?: string | null;
        };
        /** FixApplyIn */
        FixApplyIn: {
            /**
             * Carry Remaining
             * @default true
             */
            carry_remaining: boolean;
        };
        /** FixHistory */
        FixHistory: {
            /** At */
            at: string;
            /**
             * By
             * @default
             */
            by: string;
            /**
             * Status
             * @enum {string}
             */
            status: "warn" | "ok" | "wait";
            /**
             * Sub Text
             * @default
             */
            sub_text: string;
            /** Value */
            value?: string | null;
            /** Value Source */
            value_source?: string | null;
        };
        /** FixItem */
        FixItem: {
            /**
             * Actions
             * @default []
             */
            actions: string[];
            /**
             * Carry
             * @default true
             */
            carry: boolean;
            /** Cell Ref */
            cell_ref?: string | null;
            /** Claim Id */
            claim_id?: string | null;
            /**
             * Competitor
             * @default false
             */
            competitor: boolean;
            /** Confirmed At */
            confirmed_at?: string | null;
            /** Confirmed By */
            confirmed_by?: string | null;
            /** File Id */
            file_id?: string | null;
            /** File Name */
            file_name?: string | null;
            /**
             * History
             * @default []
             */
            history: components["schemas"]["FixHistory"][];
            /** Id */
            id: string;
            /**
             * Input Kind
             * @default number
             * @enum {string}
             */
            input_kind: "number" | "ratio" | "text" | "file_only";
            /** Job Id */
            job_id?: string | null;
            /** Metric Key */
            metric_key?: string | null;
            /** Note */
            note?: string | null;
            /** Page */
            page?: number | null;
            /**
             * Placeholder
             * @default 값 입력
             */
            placeholder: string;
            /** Reason Code */
            reason_code: string;
            /** Samsung Model */
            samsung_model?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "warn" | "ok" | "wait";
            /** Sub Text */
            sub_text: string;
            /** Suggestion */
            suggestion?: {
                [key: string]: unknown;
            } | null;
            /**
             * Tab
             * @enum {string}
             */
            tab: "market" | "customer" | "user" | "competitor";
            /** Tab Label */
            tab_label: string;
            /** Title */
            title: string;
            /** Unit */
            unit?: string | null;
            /** Value */
            value?: string | null;
            /** Value Source */
            value_source?: ("user" | "file" | "kb") | null;
        };
        /** FixList */
        FixList: {
            /** Counts */
            counts: {
                [key: string]: number;
            };
            /** Items */
            items: components["schemas"]["FixItem"][];
            /**
             * Version
             * @default 0
             */
            version: number;
        };
        /** FixParseIn */
        FixParseIn: {
            /** Text */
            text: string;
        };
        /** FixParseOut */
        FixParseOut: {
            /** Suggestions */
            suggestions: components["schemas"]["FixSuggestion"][];
        };
        /** FixPatch */
        FixPatch: {
            /** Note */
            note?: string | null;
            /** Unit */
            unit?: string | null;
            /** Value */
            value: string;
        };
        /** FixScanIn */
        FixScanIn: {
            /**
             * Classification
             * @default internal
             * @enum {string}
             */
            classification: "internal" | "confidential" | "customer" | "public";
            /** File Id */
            file_id: string;
            /** Fix Ids */
            fix_ids?: string[] | null;
        };
        /** FixSuggestion */
        FixSuggestion: {
            /**
             * Basis
             * @default
             */
            basis: string;
            /** Fix Id */
            fix_id: string;
            /** Unit */
            unit?: string | null;
            /** Value */
            value: string;
        };
        /** FollowupIn */
        FollowupIn: {
            /** Tab */
            tab?: ("market" | "customer" | "user" | "competitor") | null;
            /** Text */
            text: string;
        };
        /** FollowupOut */
        FollowupOut: {
            /** Answer Md */
            answer_md?: string | null;
            /**
             * Citations
             * @default []
             */
            citations: components["schemas"]["AnswerCitation"][];
            /** Instruction */
            instruction?: string | null;
            /**
             * Intent
             * @enum {string}
             */
            intent: "question" | "revision";
            /** Job Id */
            job_id?: string | null;
            /** Revision Id */
            revision_id?: string | null;
            /** Scope */
            scope?: {
                [key: string]: unknown;
            } | null;
        };
        /** Handoff */
        Handoff: {
            /** Analysis Id */
            analysis_id: string;
            /**
             * Anonymization Map
             * @default {}
             */
            anonymization_map: {
                [key: string]: string;
            };
            /** @default {} */
            confirmations: components["schemas"]["HandoffConfirm"];
            /**
             * Created At
             * @default
             */
            created_at: string;
            /** Id */
            id: string;
            /**
             * @default {
             *       "cite_sources": true,
             *       "fix_notes": true,
             *       "link_why": true
             *     }
             */
            options: components["schemas"]["HandoffOptions"];
            /**
             * Served Named At
             * @default []
             */
            served_named_at: string[];
            /**
             * Sheets
             * @default []
             */
            sheets: string[];
            /**
             * Status
             * @enum {string}
             */
            status: "prepared" | "delivered" | "failed";
            /** Target */
            target: string;
            /** Target Id */
            target_id?: string | null;
            /** Target Title */
            target_title?: string | null;
            /**
             * Updated At
             * @default
             */
            updated_at: string;
            /** Version */
            version: number;
        };
        /** HandoffConfirm */
        HandoffConfirm: {
            /** Confidential */
            confidential?: ("exclude" | "include") | null;
            /** Overwrite Pinned */
            overwrite_pinned?: boolean | null;
            /** Real Names */
            real_names?: boolean | null;
        };
        /** HandoffIn */
        HandoffIn: {
            confirm?: components["schemas"]["HandoffConfirm"] | null;
            /**
             * Dry Run
             * @default false
             */
            dry_run: boolean;
            options?: components["schemas"]["HandoffOptions"] | null;
            /** Sheets */
            sheets?: string[] | null;
            /**
             * Target
             * @enum {string}
             */
            target: "proposal_mi" | "proposal_why" | "vp" | "storyboard" | "scenario";
            /** Target Id */
            target_id?: string | null;
            /**
             * Target Pinned Sheets
             * @description 제안서에서 고정한 시트(시트 유형 · 템플릿 코드) — 웹이 알면 넘긴다
             */
            target_pinned_sheets?: string[] | null;
            /** Target Title */
            target_title?: string | null;
        };
        /** HandoffOptions */
        HandoffOptions: {
            /**
             * Cite Sources
             * @default true
             */
            cite_sources: boolean;
            /**
             * Fix Notes
             * @default true
             */
            fix_notes: boolean;
            /**
             * Link Why
             * @default true
             */
            link_why: boolean;
        };
        /** HandoffOut */
        HandoffOut: {
            /**
             * Bundle Url
             * @default
             */
            bundle_url: string;
            /** Handoff Id */
            handoff_id?: string | null;
            /**
             * Section Key
             * @default mi
             */
            section_key: string;
            /**
             * Sheets
             * @default []
             */
            sheets: string[];
            /**
             * Status
             * @default prepared
             * @enum {string}
             */
            status: "ready" | "prepared";
            /** Target Id */
            target_id?: string | null;
        };
        /** HandoffPatch */
        HandoffPatch: {
            /**
             * Status
             * @enum {string}
             */
            status: "delivered" | "failed";
            /** Target Id */
            target_id?: string | null;
            /** Target Title */
            target_title?: string | null;
        };
        /** InternalDecision */
        InternalDecision: {
            /**
             * Excluded File Ids
             * @default []
             */
            excluded_file_ids: string[];
            /**
             * Included File Ids
             * @default []
             */
            included_file_ids: string[];
            /**
             * Kb Case Count
             * @default 0
             */
            kb_case_count: number;
            /** Mode */
            mode?: ("auto" | "check" | "ask" | "pin") | null;
            /**
             * Summary
             * @default
             */
            summary: string;
        };
        /** InternalPatch */
        InternalPatch: {
            /** Excluded File Ids */
            excluded_file_ids?: string[] | null;
            /** Included File Ids */
            included_file_ids?: string[] | null;
        };
        /** JobAccepted */
        JobAccepted: {
            /** Job Id */
            job_id: string;
            /**
             * Status
             * @default queued
             * @constant
             */
            status: "queued";
        };
        /** JourneyStep */
        JourneyStep: {
            /**
             * Claims
             * @default []
             */
            claims: components["schemas"]["ClaimRef"][];
            /**
             * Opportunity
             * @default
             */
            opportunity: string;
            /**
             * Pain
             * @default
             */
            pain: string;
            /** Stage */
            stage: string;
            /**
             * Touchpoint
             * @default
             */
            touchpoint: string;
        };
        /** LayoutIn */
        LayoutIn: {
            /** Axes */
            axes?: {
                [key: string]: string;
            } | null;
            /**
             * Option
             * @enum {string}
             */
            option: "A" | "B" | "C";
            /** Pin */
            pin?: boolean | null;
            /** Template */
            template: string;
        };
        /** LayoutOption */
        LayoutOption: {
            /** Desc */
            desc: string;
            /** Eta S */
            eta_s?: number | null;
            /**
             * Key
             * @enum {string}
             */
            key: "A" | "B" | "C";
            /**
             * Predicted Fit
             * @default 0
             */
            predicted_fit: number;
            /**
             * Recommended
             * @default false
             */
            recommended: boolean;
            /**
             * Template
             * @default
             */
            template: string;
            /** Title */
            title: string;
        };
        /** Links */
        Links: {
            /** Competitor Analysis Id */
            competitor_analysis_id?: string | null;
            /** Proposal Id */
            proposal_id?: string | null;
            /** Proposal Title */
            proposal_title?: string | null;
            /** Proposal Type */
            proposal_type?: ("standard" | "quickwin" | "solution") | null;
            /** Requirements Id */
            requirements_id?: string | null;
            /** Rq Version */
            rq_version?: number | null;
            /** Storyboard Id */
            storyboard_id?: string | null;
            /** Storyboard Title */
            storyboard_title?: string | null;
        };
        /** ListCounts */
        ListCounts: {
            /**
             * All
             * @default 0
             */
            all: number;
            /**
             * Done
             * @default 0
             */
            done: number;
            /**
             * Draft
             * @default 0
             */
            draft: number;
            /**
             * Run
             * @default 0
             */
            run: number;
            /**
             * Upd
             * @default 0
             */
            upd: number;
        };
        /** MarketBlock */
        MarketBlock: {
            cagr?: components["schemas"]["Cagr"] | null;
            /** @description 사내 사례 DB 도입 경향(D2) */
            kb_trend?: components["schemas"]["ClaimRef"] | null;
            /**
             * Regulations
             * @default []
             */
            regulations: components["schemas"]["Regulation"][];
            /**
             * Size Label
             * @default
             */
            size_label: string;
            /**
             * Size Series
             * @default []
             */
            size_series: components["schemas"]["SizePoint"][];
            /**
             * Size Unit
             * @default
             */
            size_unit: string;
            /**
             * Trends
             * @default []
             */
            trends: components["schemas"]["Trend"][];
        };
        /** MemoIn */
        MemoIn: {
            /** Text */
            text: string;
        };
        /** MemoItem */
        MemoItem: {
            /** At */
            at: string;
            /** Text */
            text: string;
            /**
             * Where
             * @default design
             * @enum {string}
             */
            where: "design" | "run" | "recheck";
        };
        /** MenuItem */
        MenuItem: {
            /**
             * Highlight
             * @default false
             */
            highlight: boolean;
            /**
             * Hint
             * @default
             */
            hint: string;
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Route */
            route?: string | null;
        };
        /** MFBasis */
        MFBasis: {
            /**
             * K
             * @description 고객사 · 업종 · 공간 · 요구
             */
            k: string;
            /** V */
            v: string;
        };
        /** MFCounts */
        MFCounts: {
            /**
             * By Group
             * @description {시장: [담음, 찾음]} …
             */
            by_group?: {
                [key: string]: number[];
            };
            /** Found */
            found: number;
            /** Kept */
            kept: number;
            /** Numbercheck */
            numberCheck: number;
            /** Queries */
            queries: number;
        };
        /** MFCreate */
        MFCreate: {
            /**
             * Sb Id
             * @description 사전 작업 Storyboard(최소 DSS 까지)
             */
            sb_id: string;
            /** Title */
            title?: string | null;
        };
        /** MFDoc */
        MFDoc: {
            /** Analysis Mode */
            analysis_mode?: ("llm" | "rule") | null;
            /**
             * Basis
             * @description Storyboard 에서 읽은 것(고객사 · 업종 · 공간 · 요구)
             */
            basis?: components["schemas"]["MFBasis"][];
            /**
             * Code
             * @description 화면 · flow.json 에 쓰는 짧은 번호(MI-01 …)
             */
            code?: string | null;
            counts: components["schemas"]["MFCounts"];
            /** Created At */
            created_at: string;
            /**
             * Editing
             * @description 저장한 MI 를 고치는 중(저장하면 ver+1 · prevVer)
             * @default false
             */
            editing: boolean;
            filters?: components["schemas"]["MFFilters"];
            /** Id */
            id: string;
            /** Items */
            items?: components["schemas"]["MFItem"][];
            /**
             * Keep Previous
             * @description 고칠 때: 담은 정보 유지 · 새로 찾은 것만 더하기(false = 처음부터 다시)
             * @default true
             */
            keep_previous: boolean;
            /**
             * Phase
             * @default analyzing
             * @enum {string}
             */
            phase: "analyzing" | "search" | "searching" | "refine" | "done";
            progress?: components["schemas"]["MFProgress"] | null;
            queries?: components["schemas"]["MFQueries"];
            /** Results */
            results?: components["schemas"]["MFResult"][];
            /**
             * Saved Kept
             * @description 마지막 저장 때 담은 정보 수
             * @default 0
             */
            saved_kept: number;
            /** Sb Id */
            sb_id: string;
            /**
             * Status
             * @default draft
             * @enum {string}
             */
            status: "draft" | "done";
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
            /**
             * Ver
             * @description 저장(완료) 판 — flow.json stages.mi.ver
             */
            ver?: number | null;
            /** Version */
            version: number;
            /** Warnings */
            warnings?: string[];
        };
        /** MFFilters */
        MFFilters: {
            /**
             * Period
             * @default 최근 1년
             * @enum {string}
             */
            period: "최근 1년" | "최근 3년" | "전체";
            /**
             * Sourcetypes
             * @description 뉴스 · 공시 · IR · 리포트 · 정부 통계
             */
            sourceTypes?: string[];
        };
        /** MFFlowSync */
        MFFlowSync: {
            /**
             * Md Added
             * @description Storyboard 요약본에 더해진 부분
             */
            md_added: string;
            /**
             * Synced
             * @description 같은 MI 가 연결돼 함께 바뀐 다른 Storyboard
             */
            synced?: string[];
        };
        /** MFItem */
        MFItem: {
            /**
             * Addedin
             * @description 처음 찾은 판(v1 · v2 …)
             */
            addedIn: string;
            /**
             * Edited
             * @default false
             */
            edited: boolean;
            /**
             * Group
             * @enum {string}
             */
            group: "시장" | "고객사" | "사용자";
            /** Id */
            id: string;
            /**
             * Kept
             * @default true
             */
            kept: boolean;
            numberCheck?: components["schemas"]["MFNumberCheck"] | null;
            /** Query */
            query?: string | null;
            /**
             * Result Id
             * @description 이 문장을 뽑은 검색 결과(results[].id) — '원문' 보기
             */
            result_id?: string | null;
            source: components["schemas"]["MFSource"];
            /**
             * Summary
             * @description 원문을 줄여 쓴 한 문장(사람이 고칠 수 있음)
             */
            summary: string;
            /**
             * Summary Orig
             * @description 검색 결과에서 뽑은 그대로의 문장
             */
            summary_orig: string;
        };
        /** MFItemPatch */
        MFItemPatch: {
            /** Expected Version */
            expected_version?: number | null;
            /** Kept */
            kept?: boolean | null;
            /**
             * Summary
             * @description 문장 고치기(빈 문자열이면 원래 문장으로)
             */
            summary?: string | null;
        };
        /** MFList */
        MFList: {
            /** Items */
            items: components["schemas"]["MFListItem"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** MFListItem */
        MFListItem: {
            /** Code */
            code?: string | null;
            counts: components["schemas"]["MFCounts"];
            /** Id */
            id: string;
            /** Phase */
            phase: string;
            /** Sb Id */
            sb_id: string;
            /** Status */
            status: string;
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
            /** Ver */
            ver?: number | null;
        };
        /** MFNumberCheck */
        MFNumberCheck: {
            /**
             * Note
             * @default 수치는 원문에서 확인해야 해요
             */
            note: string;
            /**
             * Values
             * @description 원문에서 확인해야 하는 수치 표현
             */
            values?: string[];
        };
        /** MFPatch */
        MFPatch: {
            /**
             * Expected Version
             * @description 다르면 409 CONFLICT
             */
            expected_version?: number | null;
            filters?: components["schemas"]["MFFilters"] | null;
            /** Keep Previous */
            keep_previous?: boolean | null;
            /**
             * Phase
             * @description 검색어 고치기(refine → search) · 정제로 돌아가기
             */
            phase?: ("search" | "refine") | null;
            queries?: components["schemas"]["MFQueries"] | null;
            /** Title */
            title?: string | null;
        };
        /** MFProgress */
        MFProgress: {
            /**
             * Done
             * @default 0
             */
            done: number;
            /** Error */
            error?: string | null;
            /** Job Id */
            job_id?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "analyze" | "search";
            /** Steps */
            steps?: components["schemas"]["MFStep"][];
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** MFQueries */
        MFQueries: {
            /** Customer */
            customer?: components["schemas"]["MFQuery"][];
            /** Market */
            market?: components["schemas"]["MFQuery"][];
            /** User */
            user?: components["schemas"]["MFQuery"][];
        };
        /** MFQuery */
        MFQuery: {
            /**
             * By
             * @description ai = AI 분석 · rule = 규칙(모델 없이) · manual = 직접 · prev = 이전 판에서
             * @default ai
             * @enum {string}
             */
            by: "ai" | "rule" | "manual" | "prev";
            /**
             * On
             * @description false = 뺀 검색어(점선 · 취소선, 다시 넣을 수 있음)
             * @default true
             */
            on: boolean;
            /** Text */
            text: string;
        };
        /** MFResult */
        MFResult: {
            /** Error */
            error?: string | null;
            /**
             * Found
             * @default 0
             */
            found: number;
            /** Group */
            group: string;
            /** Id */
            id: string;
            /**
             * Mode
             * @default summary_only
             * @enum {string}
             */
            mode: "sources" | "summary_only";
            /**
             * Query
             * @description 실제로 보낸 검색어(검색어 보호를 거친 것)
             */
            query: string;
            /** Sources */
            sources?: components["schemas"]["MFResultSource"][];
            /**
             * Summary
             * @default
             */
            summary: string;
        };
        /** MFResultSource */
        MFResultSource: {
            /** Snippet */
            snippet?: string | null;
            /**
             * Title
             * @default
             */
            title: string;
            /** Url */
            url: string;
        };
        /** MFSource */
        MFSource: {
            /**
             * Date
             * @description YYYY-MM(글에 있을 때만)
             */
            date?: string | null;
            /**
             * Name
             * @description 출처 이름 — 검색 결과 글에 있는 문자열만(없으면 '웹 검색 요약')
             */
            name: string;
            /**
             * Type
             * @description 뉴스 · 공시 · IR · 리포트 · 정부 통계 · 웹 검색 요약(출처를 글에서 못 읽음)
             */
            type: string;
            /**
             * Url
             * @description 검색 도구가 돌려준 URL 만(요약형 검색이면 null)
             */
            url?: string | null;
        };
        /** MFStageOut */
        MFStageOut: {
            /** @description Storyboard 허브에 반영된 결과(허브가 안 되면 null) */
            flow_sync?: components["schemas"]["MFFlowSync"] | null;
            /**
             * Stage
             * @description Storyboard flow.json 의 stages.mi
             */
            stage: {
                [key: string]: unknown;
            };
            /** Summary Md */
            summary_md: string;
        };
        /** MFStep */
        MFStep: {
            /** Key */
            key: string;
            /** Label */
            label: string;
            /**
             * Note
             * @default
             */
            note: string;
            /**
             * State
             * @default wait
             * @enum {string}
             */
            state: "wait" | "run" | "done" | "error";
        };
        /** NamedCount */
        NamedCount: {
            /** Id */
            id?: string | null;
            /** Kind */
            kind?: string | null;
            /** N */
            n: number;
            /** Name */
            name: string;
        };
        /** NeedReport */
        NeedReport: {
            /**
             * Detail
             * @default
             */
            detail: string;
            /** Need */
            need: string;
            /** Ok */
            ok: boolean;
        };
        /** OnepagerOut */
        OnepagerOut: {
            /**
             * Claims
             * @default []
             */
            claims: string[];
            /**
             * Conclusion
             * @default
             */
            conclusion: string;
            /** Job Id */
            job_id?: string | null;
            /**
             * Quadrants
             * @default {}
             */
            quadrants: {
                [key: string]: string;
            };
            /**
             * Status
             * @enum {string}
             */
            status: "none" | "running" | "done" | "failed";
            /** Version */
            version?: number | null;
        };
        /** OpsChallenge */
        OpsChallenge: {
            claim?: components["schemas"]["ClaimRef"] | null;
            /** Stage */
            stage: string;
        };
        /** Persona */
        Persona: {
            /**
             * Claims
             * @default []
             */
            claims: components["schemas"]["ClaimRef"][];
            /**
             * Context
             * @default
             */
            context: string;
            /**
             * Goal
             * @default
             */
            goal: string;
            /**
             * Pain
             * @default
             */
            pain: string;
            /** Role */
            role: string;
        };
        /** Preset */
        Preset: {
            /**
             * Req Items
             * @default []
             */
            req_items: string[];
            /** Segment */
            segment: string;
        };
        /** ProposalFact */
        ProposalFact: {
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Placeholder */
            placeholder?: string | null;
            /** Source */
            source?: {
                [key: string]: unknown;
            } | null;
            /**
             * Status
             * @enum {string}
             */
            status: "confirmed" | "unconfirmed" | "placeholder";
            /** Unit */
            unit?: string | null;
            /** Value */
            value?: string | null;
        };
        /** ProposalHandoff */
        ProposalHandoff: {
            /**
             * Assets
             * @default []
             */
            assets: {
                [key: string]: unknown;
            }[];
            /** Customer */
            customer?: {
                [key: string]: unknown;
            } | null;
            /**
             * Facts
             * @default []
             */
            facts: components["schemas"]["ProposalFact"][];
            /** Items */
            items: components["schemas"]["ProposalHandoffItem"][];
            /** Rq Ref */
            rq_ref?: {
                [key: string]: unknown;
            } | null;
            source: components["schemas"]["ProposalHandoffSource"];
            /** Target */
            target: {
                [key: string]: string;
            };
        };
        /** ProposalHandoffItem */
        ProposalHandoffItem: {
            /**
             * Content
             * @default {}
             */
            content: {
                [key: string]: unknown;
            };
            /** From Label */
            from_label?: string | null;
            /** Include Default */
            include_default: boolean;
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Sheet Role */
            sheet_role: string;
            /** Sheet Title */
            sheet_title?: string | null;
            /**
             * Sources
             * @default []
             */
            sources: {
                [key: string]: unknown;
            }[];
            /**
             * Status
             * @enum {string}
             */
            status: "ok" | "warn" | "add";
            /** Status Label */
            status_label: string;
            /** Template Hint */
            template_hint?: {
                [key: string]: string;
            } | null;
        };
        /** ProposalHandoffSource */
        ProposalHandoffSource: {
            /**
             * Feature
             * @default MI
             */
            feature: string;
            /** Ref Id */
            ref_id: string;
            /** Route */
            route: string;
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
            /** Version */
            version: number;
        };
        /** QuestionIn */
        QuestionIn: {
            /** Claim Id */
            claim_id?: string | null;
            /** Tab */
            tab?: ("market" | "customer" | "user" | "competitor") | null;
            /** Text */
            text: string;
        };
        /** RecentSource */
        RecentSource: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "사내" | "공개";
            /** Name */
            name: string;
            /** State */
            state: string;
        };
        /** RecheckChange */
        RecheckChange: {
            /**
             * Affected Areas
             * @default []
             */
            affected_areas: ("market" | "customer" | "user" | "competitor")[];
            /**
             * Detected At
             * @default
             */
            detected_at: string;
            /** Evidence Source Id */
            evidence_source_id?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "competitor_new_product" | "report_revised" | "source_changed" | "kb_updated";
            /**
             * Summary
             * @default
             */
            summary: string;
            /** Title */
            title: string;
            /**
             * Verification
             * @default needs_check
             * @enum {string}
             */
            verification: "matched" | "needs_check";
        };
        /** Regulation */
        Regulation: {
            claim?: components["schemas"]["ClaimRef"] | null;
            /** Title */
            title: string;
        };
        /** ReqTypeOut */
        ReqTypeOut: {
            /** Code */
            code: string;
            /**
             * Examples
             * @default []
             */
            examples: string[];
            /** Label */
            label: string;
            /**
             * Label Basis
             * @default kb
             * @enum {string}
             */
            label_basis: "kb" | "example";
            /** N */
            n: number;
        };
        /** Requirement */
        Requirement: {
            /**
             * Basis
             * @description 추론 근거(예 '외식 · 카페 사례 19건')
             */
            basis?: string | null;
            /**
             * Code
             * @description 정의서 항목 코드(RQ-01) · 프리셋 요구 태그(R08)
             */
            code?: string | null;
            /** Id */
            id: string;
            /**
             * Inferred
             * @description 한 줄 메모라 사례 DB 로 채운 요구(빈칸 추론)
             * @default false
             */
            inferred: boolean;
            /** Label */
            label?: string | null;
            /**
             * Origin
             * @default input
             * @enum {string}
             */
            origin: "input" | "definition" | "storyboard" | "preset" | "rfp" | "inferred" | "extracted" | "user";
            /** Text */
            text: string;
            /**
             * Weight
             * @description 키맨 가중치 등(정의서) — 없으면 null
             */
            weight?: number | null;
        };
        /** RequirementIn */
        RequirementIn: {
            /** Id */
            id?: string | null;
            /** Label */
            label?: string | null;
            /**
             * Origin
             * @default input
             * @enum {string}
             */
            origin: "input" | "definition" | "storyboard" | "preset" | "rfp" | "inferred";
            /** Text */
            text: string;
            /** Weight */
            weight?: number | null;
        };
        /** RequirementsImportIn */
        RequirementsImportIn: {
            /** Requirements Id */
            requirements_id: string;
            /** Rq Version */
            rq_version?: number | null;
        };
        /** ResultView */
        ResultView: {
            /**
             * Agent Text
             * @default
             */
            agent_text: string;
            /** Analysis Id */
            analysis_id: string;
            /**
             * Analysis Status
             * @default done
             * @enum {string}
             */
            analysis_status: "draft" | "designing" | "ask" | "designed" | "queued" | "running" | "stopped" | "done" | "upd" | "failed";
            /**
             * Check Chips
             * @default []
             */
            check_chips: components["schemas"]["CheckChip"][];
            competitor?: components["schemas"]["CompetitorBlock"] | null;
            /**
             * Created At
             * @default
             */
            created_at: string;
            customer?: components["schemas"]["CustomerBlock"] | null;
            /**
             * Failed Areas
             * @default []
             */
            failed_areas: ("market" | "customer" | "user" | "competitor")[];
            /**
             * Footers
             * @default {}
             */
            footers: {
                [key: string]: components["schemas"]["TabFooter"];
            };
            /** Implications */
            implications?: {
                [key: string]: unknown;
            } | null;
            /**
             * Is Latest
             * @default true
             */
            is_latest: boolean;
            /**
             * Kind
             * @default
             */
            kind: string;
            market?: components["schemas"]["MarketBlock"] | null;
            /**
             * Needs Check Total
             * @default 0
             */
            needs_check_total: number;
            /**
             * Preview
             * @default false
             */
            preview: boolean;
            /**
             * Stopped
             * @default false
             */
            stopped: boolean;
            /**
             * Tabs
             * @default []
             */
            tabs: components["schemas"]["TabInfo"][];
            /** Upd */
            upd?: {
                [key: string]: unknown;
            } | null;
            user?: components["schemas"]["UserBlock"] | null;
            /** Version */
            version: number;
            /**
             * Web Unavailable
             * @default false
             */
            web_unavailable: boolean;
        };
        /** Revision */
        Revision: {
            /** Analysis Id */
            analysis_id: string;
            /** Applied Version */
            applied_version?: number | null;
            /** Base Version */
            base_version: number;
            /**
             * Created At
             * @default
             */
            created_at: string;
            /**
             * Duration S
             * @default 0
             */
            duration_s: number;
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            /** Id */
            id: string;
            /** Job Id */
            job_id?: string | null;
            /**
             * Origin
             * @default user
             * @enum {string}
             */
            origin: "user" | "followup" | "segment_change" | "ca_import" | "claim_research";
            /**
             * Rounds
             * @default []
             */
            rounds: {
                [key: string]: unknown;
            }[];
            scope: components["schemas"]["RevisionScope"];
            /**
             * Sources Added
             * @default 0
             */
            sources_added: number;
            /**
             * Status
             * @enum {string}
             */
            status: "running" | "proposed" | "applied" | "discarded" | "failed";
        };
        /** RevisionAccepted */
        RevisionAccepted: {
            /** Job Id */
            job_id: string;
            /** Revision Id */
            revision_id: string;
            /**
             * Status
             * @default queued
             * @constant
             */
            status: "queued";
        };
        /** RevisionIn */
        RevisionIn: {
            /**
             * Instruction
             * @default
             */
            instruction: string;
            scope: components["schemas"]["RevisionScope"];
        };
        /** RevisionScope */
        RevisionScope: {
            /** Area */
            area?: ("market" | "customer" | "user" | "competitor") | null;
            /** Ids */
            ids?: string[] | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "area" | "rows" | "strengths" | "claims";
        };
        /** RevisionView */
        RevisionView: {
            /**
             * Agent Text
             * @default
             */
            agent_text: string;
            /** Changed Count */
            changed_count: number;
            /** Changes */
            changes: components["schemas"]["Change"][];
            /** Chips */
            chips: {
                [key: string]: number;
            };
            /** Duration S */
            duration_s: number;
            /**
             * Eta S
             * @default 20
             */
            eta_s: number;
            /**
             * Footer
             * @default
             */
            footer: string;
            /** @description 변경 안을 적용한 모습(되돌린 변경 제외) */
            preview?: components["schemas"]["ResultView"] | null;
            /** Quick Suggestions */
            quick_suggestions: string[];
            revision: components["schemas"]["Revision"];
            /**
             * Scope Label
             * @default
             */
            scope_label: string;
            /** Sources Added */
            sources_added: number;
        };
        /** RoundIn */
        RoundIn: {
            /** Instruction */
            instruction: string;
            scope?: components["schemas"]["RevisionScope"] | null;
        };
        /** RoutingRules */
        RoutingRules: {
            /** Asks */
            asks: {
                [key: string]: unknown;
            };
            gaps: components["schemas"]["RuleStage"];
            /** Header */
            header: {
                [key: string]: string;
            };
            /** Layout */
            layout: {
                [key: string]: unknown;
            };
            /** Modes */
            modes: {
                [key: string]: string;
            }[];
            /** Stages */
            stages: components["schemas"]["RuleStage"][];
            /** Thresholds */
            thresholds: {
                [key: string]: unknown;
            };
        };
        /** RuleRow */
        RuleRow: {
            /** C */
            c: string;
            /**
             * Mode
             * @enum {string}
             */
            mode: "auto" | "check" | "ask" | "pin";
            /** Mode Label */
            mode_label: string;
            /** O */
            o: string;
        };
        /** RuleStage */
        RuleStage: {
            /** No */
            no: string;
            /** Rules */
            rules: components["schemas"]["RuleRow"][];
            /** Sub */
            sub: string;
            /** Title */
            title: string;
        };
        /** RunIn */
        RunIn: {
            /** Areas */
            areas?: ("market" | "customer" | "user" | "competitor")[] | null;
            /**
             * Mode
             * @description auto(기본) = 의존 해시가 바뀐 영역만 · full = 전부 다시 · changed_only = 바뀐 영역 + areas · resume = 정리 못 한 영역
             * @default auto
             * @enum {string}
             */
            mode: "auto" | "full" | "changed_only" | "resume";
        };
        /** RunProgress */
        RunProgress: {
            /**
             * Areas
             * @default []
             */
            areas: components["schemas"]["AreaProgress"][];
            /**
             * Card Sub
             * @default
             */
            card_sub: string;
            /**
             * Card Title
             * @default
             */
            card_title: string;
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            /** Eta S */
            eta_s?: number | null;
            /** Job Id */
            job_id?: string | null;
            /**
             * Memos
             * @default []
             */
            memos: components["schemas"]["MemoItem"][];
            /**
             * Pct
             * @default 0
             */
            pct: number;
            /**
             * Previewable
             * @default []
             */
            previewable: string[];
            /**
             * Recent Sources
             * @default []
             */
            recent_sources: components["schemas"]["RecentSource"][];
            /**
             * Sources
             * @default {}
             */
            sources: {
                [key: string]: number;
            };
            /** Stage */
            stage?: string | null;
            /**
             * Stages
             * @default []
             */
            stages: components["schemas"]["StageState"][];
            /**
             * Status
             * @default none
             */
            status: string;
            /**
             * Summary Chip
             * @default
             */
            summary_chip: string;
        };
        /** SamsungProduct */
        SamsungProduct: {
            /** Family Id */
            family_id?: string | null;
            /**
             * Kind
             * @default model
             * @enum {string}
             */
            kind: "model" | "family" | "solution";
            /** Model Code */
            model_code?: string | null;
            /** Name */
            name: string;
            /**
             * Origin
             * @default s1
             * @enum {string}
             */
            origin: "topbar" | "requirement" | "s1" | "user";
            /**
             * Ref
             * @description 셸 참조(kb:model:mdl_… · kb:family:fam_… · kb:solution:…)
             */
            ref?: string | null;
        };
        /** ScopeDecision */
        ScopeDecision: {
            /**
             * Areas
             * @default []
             */
            areas: ("market" | "customer" | "user" | "competitor")[];
            /** Mode */
            mode?: ("auto" | "check" | "ask" | "pin") | null;
            /**
             * Reasons
             * @default {}
             */
            reasons: {
                [key: string]: string;
            };
            /**
             * Reduced
             * @description 축소한 영역(고객 공개 자료 3건 미만 → customer)
             * @default []
             */
            reduced: ("market" | "customer" | "user" | "competitor")[];
        };
        /** ScopePatch */
        ScopePatch: {
            /** Areas */
            areas: ("market" | "customer" | "user" | "competitor")[];
            /**
             * Mode
             * @default pin
             * @constant
             */
            mode: "pin";
        };
        /** SegmentCandidate */
        SegmentCandidate: {
            /** Clue */
            clue?: number | null;
            /** Code */
            code: string;
            /** Confidence */
            confidence: number;
            /** Kb */
            kb?: number | null;
            /** Llm */
            llm?: number | null;
        };
        /** SegmentDecision */
        SegmentDecision: {
            /**
             * Candidates
             * @default []
             */
            candidates: components["schemas"]["SegmentCandidate"][];
            /**
             * Clues
             * @default []
             */
            clues: components["schemas"]["Clue"][];
            /** Code */
            code?: string | null;
            /** Confidence */
            confidence?: number | null;
            /**
             * Inherited From
             * @description 상속했으면 원천(storyboard · requirements · proposal · mi)
             */
            inherited_from?: string | null;
            /**
             * Llm Failed
             * @default false
             */
            llm_failed: boolean;
            mix?: components["schemas"]["SegmentMix"] | null;
            /** Mode */
            mode?: ("auto" | "check" | "ask" | "pin") | null;
        };
        /** SegmentInsights */
        SegmentInsights: {
            /** Cases */
            cases: number;
            /** Code */
            code: string;
            /** Full */
            full: string;
            /**
             * Gaps
             * @default []
             */
            gaps: string[];
            /** Layouts */
            layouts: string[];
            /** Products */
            products: components["schemas"]["NamedCount"][];
            /** Req Types */
            req_types: components["schemas"]["ReqTypeOut"][];
            /** Short */
            short: string;
            /** Solutions */
            solutions: components["schemas"]["NamedCount"][];
        };
        /** SegmentItem */
        SegmentItem: {
            /**
             * Aliases
             * @default []
             */
            aliases: string[];
            /**
             * Case Count
             * @default 0
             */
            case_count: number;
            /** Code */
            code: string;
            /** Full */
            full: string;
            /**
             * Has Layouts
             * @default true
             */
            has_layouts: boolean;
            /** Kb Id */
            kb_id?: string | null;
            /**
             * Mapping
             * @default true
             */
            mapping: boolean;
            /** Short */
            short: string;
        };
        /** SegmentList */
        SegmentList: {
            /**
             * Case Total
             * @default 0
             */
            case_total: number;
            /**
             * Home
             * @description MI0 업종 칩(최대 6) `{code, short, n}`
             * @default []
             */
            home: {
                [key: string]: unknown;
            }[];
            /** Items */
            items: components["schemas"]["SegmentItem"][];
            /**
             * Method
             * @default
             */
            method: string;
            /**
             * Needs Confirmation
             * @default []
             */
            needs_confirmation: string[];
        };
        /** SegmentMix */
        SegmentMix: {
            /** A */
            a: string;
            /** B */
            b: string;
            /** C */
            c: string;
        };
        /** SegmentPatch */
        SegmentPatch: {
            /** Code */
            code: string;
            mix?: components["schemas"]["SegmentMix"] | null;
            /**
             * Mode
             * @default pin
             * @constant
             */
            mode: "pin";
        };
        /** ServiceInfo */
        ServiceInfo: {
            /** Service */
            service: string;
            /** Title */
            title: string;
            /** Version */
            version: string;
        };
        /** ShareOut */
        ShareOut: {
            /** Share Url */
            share_url: string;
            /** Token */
            token?: string | null;
        };
        /** SheetPreview */
        SheetPreview: {
            /** Code */
            code: string;
            /**
             * Industry
             * @default false
             */
            industry: boolean;
            /** Note */
            note: string;
            /** Sheet */
            sheet: string;
            /** Thumb */
            thumb: string;
        };
        /** SizePoint */
        SizePoint: {
            claim?: components["schemas"]["ClaimRef"] | null;
            /**
             * Unit
             * @default
             */
            unit: string;
            /** Value */
            value?: number | null;
            /** Year */
            year: number;
        };
        /** SlidePatch */
        SlidePatch: {
            /** Included */
            included?: boolean | null;
            /** Pinned */
            pinned?: boolean | null;
            /** Template Code */
            template_code?: string | null;
        };
        /** SlidePlan */
        SlidePlan: {
            /**
             * Alternatives
             * @default []
             */
            alternatives: components["schemas"]["Alternative"][];
            /** Analysis Id */
            analysis_id: string;
            /** Area */
            area?: ("market" | "customer" | "user" | "competitor") | null;
            /** Fit */
            fit: number;
            /**
             * Fix Open
             * @default 0
             */
            fix_open: number;
            /** Id */
            id: string;
            /**
             * In Section
             * @default true
             */
            in_section: boolean;
            /**
             * Include Mode
             * @enum {string}
             */
            include_mode: "auto" | "check" | "ask" | "pin";
            /** Included */
            included: boolean;
            /** Industry Layout */
            industry_layout: boolean;
            /**
             * Item Label
             * @default
             */
            item_label: string;
            /**
             * Needs Report
             * @default []
             */
            needs_report: components["schemas"]["NeedReport"][];
            /**
             * Options
             * @default {}
             */
            options: {
                [key: string]: unknown;
            };
            /**
             * Order
             * @default 0
             */
            order: number;
            /**
             * Pinned
             * @default false
             */
            pinned: boolean;
            /** Sheet Name */
            sheet_name: string;
            /** Sheet Type */
            sheet_type: string;
            /** Source Label */
            source_label: string;
            /**
             * Status
             * @description MI4 매핑 상태(내보내기 화면만) — 그대로 들어가요 · [확정 필요] n건 · 섹션에 없는 시트
             */
            status?: ("ok" | "warn" | "add") | null;
            /**
             * Status Label
             * @default
             */
            status_label: string;
            /** Template Code */
            template_code: string;
            /** Template Name */
            template_name: string;
            /** Thumb Kind */
            thumb_kind: string;
            /** Version */
            version: number;
            /** Why */
            why: string;
        };
        /** SlideRequestIn */
        SlideRequestIn: {
            /** Text */
            text: string;
        };
        /** SlideRequestOut */
        SlideRequestOut: {
            /**
             * Changed
             * @default []
             */
            changed: string[];
            /**
             * Kind
             * @enum {string}
             */
            kind: "layout" | "include" | "none";
            /**
             * Message
             * @default
             */
            message: string;
            /** Requested */
            requested?: string | null;
            /** Sheet Id */
            sheet_id?: string | null;
        };
        /** SlidesView */
        SlidesView: {
            /**
             * Footer
             * @default
             */
            footer: string;
            /** Header */
            header: {
                [key: string]: unknown;
            };
            /** Order */
            order: string[];
            /** Rows */
            rows: components["schemas"]["SlidePlan"][];
            /** Usage */
            usage: ("standard" | "solution" | "quickwin" | "exec_onepager" | "none") | null;
            /** Usage Label */
            usage_label: string;
        };
        /** SnapshotOut */
        SnapshotOut: {
            /** Pages */
            pages?: string[] | null;
            /** Text */
            text: string;
        };
        /** SourceAccepted */
        SourceAccepted: {
            /** Job Id */
            job_id: string;
            /** Source Id */
            source_id: string;
            /**
             * Status
             * @default queued
             * @constant
             */
            status: "queued";
        };
        /** SourceAddIn */
        SourceAddIn: {
            /** Claim Id */
            claim_id?: string | null;
            /** Classification */
            classification?: ("internal" | "confidential" | "customer" | "public") | null;
            /** File Id */
            file_id?: string | null;
            /** Url */
            url?: string | null;
        };
        /** SourceCard */
        SourceCard: {
            /**
             * Actions
             * @default []
             */
            actions: string[];
            /** File Id */
            file_id?: string | null;
            /**
             * Flag
             * @default
             */
            flag: string;
            /**
             * Footnote
             * @default
             */
            footnote: string;
            /**
             * Has Snapshot
             * @default false
             */
            has_snapshot: boolean;
            /**
             * Kind
             * @enum {string}
             */
            kind: "web" | "websearch_summary" | "kb_case" | "kb_official" | "file" | "user" | "ca_import";
            /** Kind Label */
            kind_label: string;
            /**
             * Meta
             * @default
             */
            meta: string;
            /** N */
            n: number;
            /** Page */
            page?: number | null;
            /**
             * Quote
             * @default
             */
            quote: string;
            /**
             * Quote After
             * @default
             */
            quote_after: string;
            /**
             * Quote Before
             * @default
             */
            quote_before: string;
            /**
             * Quote Highlight
             * @default
             */
            quote_highlight: string;
            /**
             * Quote Style
             * @default normal
             * @enum {string}
             */
            quote_style: "normal" | "model" | "snippet" | "summary" | "value";
            /**
             * Reason
             * @default
             */
            reason: string;
            /** Reason Code */
            reason_code?: string | null;
            /** Source Id */
            source_id: string;
            /** Status */
            status: ("matched" | "needs_check" | "unverifiable" | "stale") | "confirmed";
            /** Status Label */
            status_label: string;
            /** Title */
            title: string;
            /** Url */
            url?: string | null;
        };
        /** SourceList */
        SourceList: {
            /**
             * Counts
             * @default {}
             */
            counts: {
                [key: string]: number;
            };
            /** Items */
            items: components["schemas"]["SourceOut"][];
        };
        /** SourceOut */
        SourceOut: {
            /**
             * Areas
             * @default []
             */
            areas: string[];
            /**
             * Authority
             * @default 5
             */
            authority: number;
            card?: components["schemas"]["SourceCard"] | null;
            /**
             * Classification
             * @default public
             */
            classification: string;
            /** Competitor Id */
            competitor_id?: string | null;
            /** Excluded Reason */
            excluded_reason?: string | null;
            /** File Id */
            file_id?: string | null;
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "web" | "websearch_summary" | "kb_case" | "kb_official" | "file" | "user" | "ca_import";
            /**
             * Mode
             * @default summary_only
             */
            mode: string;
            /** N */
            n?: number | null;
            /** Published At */
            published_at?: string | null;
            /**
             * Published Basis
             * @default unknown
             */
            published_basis: string;
            /**
             * Publisher
             * @default
             */
            publisher: string;
            /** Query */
            query?: string | null;
            /**
             * Retrieved At
             * @default
             */
            retrieved_at: string;
            /**
             * State
             * @default used
             * @enum {string}
             */
            state: "used" | "checking" | "excluded";
            /**
             * Subtype
             * @default
             */
            subtype: string;
            /**
             * Title
             * @default
             */
            title: string;
            /** Url */
            url?: string | null;
        };
        /** StageState */
        StageState: {
            /** Name */
            name: string;
            /**
             * Note
             * @default
             */
            note: string;
            /**
             * Stage
             * @enum {string}
             */
            stage: "search" | "organize" | "write";
            /**
             * Status
             * @enum {string}
             */
            status: "wait" | "run" | "done";
        };
        /** StoryboardImportIn */
        StoryboardImportIn: {
            /** Customer Name */
            customer_name?: string | null;
            /**
             * Key Messages
             * @default []
             */
            key_messages: string[];
            /**
             * Requirements
             * @default []
             */
            requirements: components["schemas"]["RequirementIn"][];
            /**
             * Research Topics
             * @default []
             */
            research_topics: string[];
            /** Segment */
            segment?: string | null;
            /** Storyboard Id */
            storyboard_id: string;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** Strength */
        Strength: {
            /**
             * Claims
             * @default []
             */
            claims: components["schemas"]["ClaimRef"][];
            /**
             * Criterion Ids
             * @default []
             */
            criterion_ids: string[];
            /** Id */
            id: string;
            /** Note */
            note: string;
            /** Title */
            title: string;
        };
        /** StructureItem */
        StructureItem: {
            claim?: components["schemas"]["ClaimRef"] | null;
            /** Label */
            label: string;
            /**
             * Value
             * @default
             */
            value: string;
        };
        /** TabFooter */
        TabFooter: {
            /**
             * By Kind
             * @default {}
             */
            by_kind: {
                [key: string]: number;
            };
            /**
             * Sources
             * @default 0
             */
            sources: number;
            /**
             * Text
             * @default
             */
            text: string;
            /**
             * Unverified
             * @default false
             */
            unverified: boolean;
        };
        /** TabInfo */
        TabInfo: {
            /**
             * Area
             * @enum {string}
             */
            area: "market" | "customer" | "user" | "competitor";
            /** Label */
            label: string;
            /**
             * Needs Check
             * @default 0
             */
            needs_check: number;
            /**
             * Status
             * @enum {string}
             */
            status: "done" | "running" | "wait" | "failed" | "reused" | "preview";
        };
        /** TableCell */
        TableCell: {
            /**
             * Claim Ids
             * @default []
             */
            claim_ids: string[];
            /**
             * Ns
             * @default []
             */
            ns: number[];
            /**
             * Placeholder
             * @default false
             */
            placeholder: boolean;
            /** Status */
            status?: ("matched" | "needs_check" | "conflict" | "stale" | "confirmed" | "checking" | "missing") | null;
            /** Text */
            text: string;
            /** Verdict */
            verdict?: ("samsung_better" | "similar" | "samsung_worse" | "unknown") | null;
        };
        /** TableColumn */
        TableColumn: {
            /**
             * Key
             * @description cmp_… 또는 samsung
             */
            key: string;
            /** Label */
            label: string;
            /**
             * Samsung
             * @default false
             */
            samsung: boolean;
            /**
             * Sub
             * @description 작업 화면 보조 글자(실명)
             * @default
             */
            sub: string;
        };
        /** TableRow */
        TableRow: {
            /** Cells */
            cells: {
                [key: string]: components["schemas"]["TableCell"];
            };
            /** Criterion Id */
            criterion_id: string;
            /** Name */
            name: string;
            /**
             * Weight
             * @default 3
             */
            weight: number;
        };
        /**
         * TableText
         * @description `표 복사` — 탭으로 나눈 비교표 글.
         */
        TableText: {
            /**
             * Columns
             * @default []
             */
            columns: string[];
            /**
             * Rows
             * @default 0
             */
            rows: number;
            /** Text */
            text: string;
        };
        /** TemplateCandidate */
        TemplateCandidate: {
            /** Code */
            code: string;
            /** Fit */
            fit: number;
            /**
             * Fit Label
             * @default
             */
            fit_label: string;
            /** Name */
            name: string;
            /**
             * Needs
             * @default []
             */
            needs: components["schemas"]["NeedReport"][];
            /**
             * Tag
             * @default
             * @enum {string}
             */
            tag: "사용 중" | "요청" | "고를 수 없음" | "";
            /** Thumb Kind */
            thumb_kind: string;
        };
        /** Trend */
        Trend: {
            claim?: components["schemas"]["ClaimRef"] | null;
            /**
             * Implication
             * @default
             */
            implication: string;
            /** Title */
            title: string;
            /** When */
            when?: string | null;
        };
        /** UpdBanner */
        UpdBanner: {
            /**
             * Kinds
             * @default []
             */
            kinds: string[];
            /** N */
            n: number;
            /**
             * Target Ids
             * @default []
             */
            target_ids: string[];
            /** Text */
            text: string;
            /** Title */
            title: string;
        };
        /** UsageDecision */
        UsageDecision: {
            /** Mode */
            mode?: ("auto" | "check" | "ask" | "pin") | null;
            /**
             * Reason
             * @default
             */
            reason: string;
            /** Value */
            value?: ("standard" | "solution" | "quickwin" | "exec_onepager" | "none") | null;
        };
        /** UsagePatch */
        UsagePatch: {
            /**
             * Mode
             * @default pin
             * @constant
             */
            mode: "pin";
            /** Proposal Id */
            proposal_id?: string | null;
            /** Proposal Title */
            proposal_title?: string | null;
            /**
             * Value
             * @enum {string}
             */
            value: "standard" | "solution" | "quickwin" | "exec_onepager" | "none";
        };
        /** UserBlock */
        UserBlock: {
            /**
             * Composition
             * @default []
             */
            composition: components["schemas"]["CompositionItem"][];
            /**
             * Journey
             * @default []
             */
            journey: components["schemas"]["JourneyStep"][];
            /**
             * Personas
             * @default []
             */
            personas: components["schemas"]["Persona"][];
        };
        /** VersionList */
        VersionList: {
            /** Items */
            items: components["schemas"]["VersionSummary"][];
        };
        /** VersionOut */
        VersionOut: {
            /** Version */
            version: number;
        };
        /** VersionSummary */
        VersionSummary: {
            /** Created At */
            created_at: string;
            /**
             * Created By
             * @default
             */
            created_by: string;
            /**
             * Current
             * @default false
             */
            current: boolean;
            /** Kind */
            kind: string;
            /** N */
            n: number;
            /**
             * Stopped
             * @default false
             */
            stopped: boolean;
            /**
             * Summary
             * @default
             */
            summary: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    list_analyses: {
        parameters: {
            query?: {
                cursor?: string | null;
                has_competitors?: boolean | null;
                limit?: number;
                q?: string | null;
                segment?: string | null;
                sort?: string;
                status?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnalysisList"];
                };
            };
        };
    };
    create_analysis: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateAnalysisIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Analysis"];
                };
            };
            /** @description auto_run — 설계 → 분석 잡 사슬 */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AutoRunAccepted"];
                };
            };
        };
    };
    get_analysis: {
        parameters: {
            query?: {
                version?: number | null;
            };
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Analysis"];
                };
            };
        };
    };
    delete_analysis: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    patch_analysis: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AnalysisPatch"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Analysis"];
                };
            };
        };
    };
    add_from_topbar: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AdditionsIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdditionsOut"];
                };
            };
        };
    };
    get_bundle: {
        parameters: {
            query?: {
                handoff_id?: string | null;
                target?: string;
            };
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Bundle"];
                };
            };
        };
    };
    get_changes: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ChangesView"];
                };
            };
        };
    };
    list_claims: {
        parameters: {
            query?: {
                status?: string | null;
                tab?: string;
                version?: number | null;
            };
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ClaimList"];
                };
            };
        };
    };
    get_claim: {
        parameters: {
            query?: {
                version?: number | null;
            };
            header?: never;
            path: {
                aid: string;
                clm: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ClaimDetail"];
                };
            };
        };
    };
    remove_claim_source: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                clm: string;
                src: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ClaimDetail"];
                };
            };
        };
    };
    list_competitors: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompetitorList"];
                };
            };
        };
    };
    add_competitor: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CompetitorAddIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompetitorAccepted"];
                };
            };
        };
    };
    patch_competitor: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                cmp: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CompetitorPatch"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Competitor"];
                };
            };
        };
    };
    get_criteria: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CriteriaList"];
                };
            };
        };
    };
    put_criteria: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CriteriaPut"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CriteriaList"];
                };
            };
        };
    };
    get_design: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DesignView"];
                };
            };
        };
    };
    run_design: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
        };
    };
    design_memo: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MemoIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
        };
    };
    duplicate_analysis: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DuplicateIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Analysis"];
                };
            };
        };
    };
    evidence: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EvidenceSnapshot"];
                };
            };
        };
    };
    export_view: {
        parameters: {
            query?: {
                target_id?: string | null;
            };
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExportView"];
                };
            };
        };
    };
    create_export: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ExportIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
        };
    };
    facts_lookup: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FactsLookupIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FactsLookupOut"];
                };
            };
            /** @description research=true — 다른 출처 찾기와 같은 검색(결과는 후보로만) */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
        };
    };
    list_fix_items: {
        parameters: {
            query?: {
                status?: string;
            };
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FixList"];
                };
            };
        };
    };
    patch_fix_item: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                fix: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FixPatch"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FixItem"];
                };
            };
        };
    };
    cancel_fix_scan: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                fix: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FixItem"];
                };
            };
        };
    };
    customer_question: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                fix: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomerQuestionOut"];
                };
            };
        };
    };
    revert_fix_item: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                fix: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FixItem"];
                };
            };
        };
    };
    apply_fix_items: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FixApplyIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VersionOut"];
                };
            };
        };
    };
    parse_fix_text: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FixParseIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FixParseOut"];
                };
            };
        };
    };
    scan_fix_items: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FixScanIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
        };
    };
    followup: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FollowupIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FollowupOut"];
                };
            };
        };
    };
    create_handoff: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["HandoffIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HandoffOut"];
                };
            };
        };
    };
    patch_handoff: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                hof: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["HandoffPatch"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Handoff"];
                };
            };
        };
    };
    import_requirements: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RequirementsImportIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Analysis"];
                };
            };
        };
    };
    import_storyboard: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StoryboardImportIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Analysis"];
                };
            };
        };
    };
    get_onepager: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OnepagerOut"];
                };
            };
        };
    };
    make_onepager: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
        };
    };
    get_progress: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunProgress"];
                };
            };
        };
    };
    proposal_handoff: {
        parameters: {
            query?: {
                handoff_id?: string | null;
                named?: boolean;
                section?: string;
                type?: string | null;
            };
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProposalHandoff"];
                };
            };
        };
    };
    ask_question: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["QuestionIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnswerOut"];
                };
            };
        };
    };
    recheck: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
        };
    };
    get_result: {
        parameters: {
            query?: {
                preview?: boolean;
                tab?: string | null;
                version?: number | null;
            };
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResultView"];
                };
            };
        };
    };
    post_revision: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RevisionIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RevisionAccepted"];
                };
            };
        };
    };
    get_revision: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                rev: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RevisionView"];
                };
            };
        };
    };
    apply_revision: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                rev: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VersionOut"];
                };
            };
        };
    };
    patch_change: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                chg: string;
                rev: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChangePatch"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Change"];
                };
            };
        };
    };
    discard_revision: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                rev: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    revert_all: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                rev: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RevisionView"];
                };
            };
        };
    };
    add_round: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                rev: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RoundIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
        };
    };
    run_analysis: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["RunIn"] | null;
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
        };
    };
    share: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShareOut"];
                };
            };
        };
    };
    shared_view: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResultView"];
                };
            };
        };
    };
    get_slides: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SlidesView"];
                };
            };
        };
    };
    patch_slide: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                sht: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SlidePatch"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SlidePlan"];
                };
            };
        };
    };
    slide_candidates: {
        parameters: {
            query?: {
                requested?: string | null;
                text?: string | null;
            };
            header?: never;
            path: {
                aid: string;
                sht: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CandidatesView"];
                };
            };
        };
    };
    choose_layout: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                sht: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LayoutIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SlidePlan"];
                };
            };
            /** @description 선택지 A — 모자란 데이터 추가 수집(mi.layout) */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
        };
    };
    slide_request: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SlideRequestIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SlideRequestOut"];
                };
            };
        };
    };
    list_sources: {
        parameters: {
            query?: {
                kind?: string | null;
                state?: string | null;
                tab?: string | null;
                version?: number | null;
            };
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceList"];
                };
            };
        };
    };
    add_source: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SourceAddIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SourceAccepted"];
                };
            };
        };
    };
    get_snapshot: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                src: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SnapshotOut"];
                };
            };
        };
    };
    table_text: {
        parameters: {
            query?: {
                audience?: string;
            };
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TableText"];
                };
            };
        };
    };
    list_versions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VersionList"];
                };
            };
        };
    };
    restore_version: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                aid: string;
                n: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Analysis"];
                };
            };
        };
    };
    capabilities: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Capabilities"];
                };
            };
        };
    };
    import_competitor: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CaImportIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CaImportAccepted"];
                };
            };
        };
    };
    info: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ServiceInfo"];
                };
            };
        };
    };
    list_mi_flows: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MFList"];
                };
            };
        };
    };
    create_mi_flow: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MFCreate"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MFDoc"];
                };
            };
        };
    };
    get_mi_flow: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                flow_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MFDoc"];
                };
            };
        };
    };
    patch_mi_flow: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                flow_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MFPatch"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MFDoc"];
                };
            };
        };
    };
    analyze_mi_flow: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                flow_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MFDoc"];
                };
            };
        };
    };
    finish_mi_flow: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                flow_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MFStageOut"];
                };
            };
        };
    };
    search_mi_flow: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                flow_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MFDoc"];
                };
            };
        };
    };
    patch_mi_flow_item: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                flow_id: string;
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MFItemPatch"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MFDoc"];
                };
            };
        };
    };
    get_mi_flow_stage: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                flow_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MFStageOut"];
                };
            };
        };
    };
    routing_rules: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RoutingRules"];
                };
            };
        };
    };
    list_segments: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SegmentList"];
                };
            };
        };
    };
    segment_insights: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                code: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SegmentInsights"];
                };
            };
        };
    };
    detect_segment: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DetectIn"];
            };
        };
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DetectOut"];
                };
            };
        };
    };
}
