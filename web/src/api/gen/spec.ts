// 자동 생성 — 직접 고치지 말 것. 원본: contracts/spec.json (make contracts)
export interface paths {
    "/v1/catalog:recheck-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Recheck All
         * @description 전체 재확인(매일 06:00 KST 예약과 같은 일). 카탈로그 버전이 바뀌었으면 SP0 배너 · 알림.
         */
        post: operations["recheck_all"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/catalog/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Catalog Status */
        get: operations["catalog_status"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/combos": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Combos
         * @description 자주 비교하는 조합 — 모든 모델이 지금 카탈로그에서 해소될 때만(최대 3).
         */
        get: operations["list_combos"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/handoffs/{handoff_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Handoff
         * @description proposal 이 넘김 묶음을 당겨 간다.
         */
        get: operations["get_handoff"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/handoffs/{handoff_id}:ack": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Ack Handoff
         * @description proposal 이 반영 결과를 알림 — applied 면 연결(slk_) 생성 · 갱신(보낸 스냅숏), 그 연결의 `제안서와 다름` 경고 해결.
         */
        post: operations["ack_handoff"];
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
    "/v1/item-catalog": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Item Catalog */
        get: operations["item_catalog"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/lifecycle": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Lifecycle
         * @description 생애주기 표(관리) — 단종 · 후속 모델(사내 카탈로그에 생애주기가 없을 때의 원천, §4.17.2).
         */
        get: operations["list_lifecycle"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/lifecycle:check": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Lifecycle Check
         * @description P3 — 모델마다 판매 상태 · 후속 후보 · 근거(사내 카탈로그 생애주기 → 생애주기 표 → KB 존재 여부, §4.17.2).
         */
        post: operations["lifecycle_check"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/lifecycle/{model_key}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Lifecycle */
        put: operations["put_lifecycle"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/links": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Links
         * @description 제안서 PR7Q `값 불일치` · `Spec 시트에서 보기` — 연결마다 보낸 값과 지금 값의 차이.
         */
        get: operations["list_links"];
        put?: never;
        post?: never;
        /**
         * Release Links
         * @description proposal → spec: 제안서를 지웠다(또는 그 시트 반입을 실행 취소했다 — `sheet_id`) — 그 제안서와의 연결(slk_)을 지우고,
         *     그 연결의 `제안서와 다름` 경고를 닫고, 시트의 `보낼 제안서`(target_proposal)가 그 제안서면 비운다. 지운 제안서로 알림이 가지 않게(통합).
         */
        delete: operations["release_links"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/preferences": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Preferences */
        get: operations["get_preferences"];
        /**
         * Put Preferences
         * @description 내 기본값으로 저장 — 새 작업의 SP2 · SP2L 기본값.
         */
        put: operations["put_preferences"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Sheets
         * @description 작업 목록. 탭 숫자는 검색 · 거르기 전 기준. 기본 기간 최근 30일(검색하면 기간 무시).
         */
        get: operations["list_sheets"];
        put?: never;
        /**
         * Create Sheet
         * @description 새 작업. `purpose: proposal`(제안서 딸깍 P2)이면 기본 항목으로 바로 생성(auto_answer)까지 시작한다.
         */
        post: operations["create_sheet"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Sheet */
        get: operations["get_sheet"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Patch Sheet
         * @description 제목 · 고객사 · 단계(1 · 2) · 대상 제안서. step 2 로 넘어가면 제목을 확정한다(SP1 큰 버튼).
         */
        patch: operations["patch_sheet"];
        trace?: never;
    };
    "/v1/sheets/{sheet_id}:archive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Archive Sheet */
        post: operations["archive_sheet"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}:clone": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Clone Sheet
         * @description 복제해서 새 버전 — 제품 · 항목 · 형식 · 행 편집(순서 · 강조 · 숨김 · 각주 메모)만. 고객사 · 연결 · 경고 · 값 확인 · 내부 메모는 비움.
         */
        post: operations["clone_sheet"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}:save": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Save Sheet
         * @description 저장 — version +1 · saved_at · 상태 다시 계산 · workspace.
         */
        post: operations["save_sheet"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}:unarchive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Unarchive Sheet */
        post: operations["unarchive_sheet"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/cells/{row_id}/{product_id}": {
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
         * Patch Cell
         * @description 셀 직접 고치기 → `edited`(출처 직접 입력, 고정) · 우위 다시 계산. 숫자 · 단위가 틀리면 422 INVALID_VALUE.
         */
        patch: operations["patch_cell"];
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/cells/{row_id}/{product_id}/sources": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Cell Sources
         * @description `출처 보기` — 칸의 출처(출처끼리 다른 칸이면 후보 출처 전부).
         */
        get: operations["cell_sources"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/checks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Checks */
        get: operations["list_checks"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/checks:apply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Apply Checks
         * @description `답 반영하고 완성` — 답은 반영, 답 없는 확인은 [확정 필요](눌린 칩이 있으면 그 값). 잡이 아직이면 저장해 두고 끝날 때 반영.
         */
        post: operations["apply_checks"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/checks:defer-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Defer All Checks
         * @description `모두 [확정 필요]로 두기` — 열린 확인 전부 deferred(셀 [확정 필요]). 생성 중이면 이후 생기는 확인도 미룬다.
         */
        post: operations["defer_all_checks"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/checks/{check_id}:answer": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Answer Check
         * @description 답(칩 · 입력 · 다른 측정값)을 미리 저장 — 적용은 `답 반영하고 완성`(checks:apply). 숫자 · 단위가 틀리면 422 INVALID_VALUE.
         */
        post: operations["answer_check"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/compliance": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Compliance */
        get: operations["get_compliance"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Patch Compliance
         * @description 대응 모델 · 시트에 넣기 칩. 대응 모델이 바뀌면 다시 판정(202, spec_compliance reevaluate).
         */
        patch: operations["patch_compliance"];
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/compliance:to-items": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Compliance To Items
         * @description `대응표로 시트 만들기` — 제목 확정 · 제품(대응 모델 + 켰으면 대안) · 요구 관련 항목 미리 체크 · step 2.
         */
        post: operations["compliance_to_items"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/compliance/ask-draft": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Ask Draft
         * @description `확인 필요 {n}건 담당자에게 묻기` 초안(복사 · mailto).
         */
        get: operations["ask_draft"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/compliance/rows/{row_id}": {
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
         * Patch Compliance Row
         * @description 판정 고치기(사람이 확인한 결과) · 메모.
         */
        patch: operations["patch_compliance_row"];
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/datasheets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Datasheet
         * @description 제품 데이터시트(사용자 자료 — confidential) → 빈 칸 채우기 · 다른 값은 확인/경고.
         */
        post: operations["add_datasheet"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/diff-items": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Diff Items */
        get: operations["diff_items"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/edit-sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Session */
        post: operations["create_session"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/edit-sessions/{session_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Session */
        get: operations["get_session"];
        put?: never;
        post?: never;
        /**
         * Discard
         * @description `취소` — 세션 버림(시트 그대로).
         */
        delete: operations["discard"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/edit-sessions/{session_id}:commit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Commit
         * @description `편집 완료` — 한 번에 반영(version +1). 그사이 시트가 바뀌었으면 409 VERSION_CONFLICT(rebase=true 면 최신 시트에 다시 얹음).
         */
        post: operations["commit"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/edit-sessions/{session_id}:redo": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Redo */
        post: operations["redo"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/edit-sessions/{session_id}:reset": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Reset
         * @description `모두 되돌리기` — 세션 조작 비움.
         */
        post: operations["reset"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/edit-sessions/{session_id}:undo": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Undo */
        post: operations["undo"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/edit-sessions/{session_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Edit Message
         * @description `말로 고치기` — LLM 조작을 세션에 더함(바로 커밋하지 않음, spec_revise context=edit).
         */
        post: operations["edit_message"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/edit-sessions/{session_id}/ops": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Ops
         * @description 조작 더하기(행 이동 · 숨김 · 강조 · 메모 · 항목 추가 · 행 삭제 · 열 이동). 추가 행 값은 카탈로그에서 바로(결정적).
         */
        post: operations["add_ops"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/exports": {
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
         * @description XLSX · PDF · PPT(export 서비스가 만듦). overrides 는 이 내보내기에만.
         */
        post: operations["create_export"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/exports/{export_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Export */
        get: operations["get_export"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/finder": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Put Finder
         * @description 칩 · 필수 · 추가 조건 · 숨기기 · 보기 · 선택 → 후보 다시 계산(결정적). preset 은 다른 화면에서 올 때 조건을 미리 채운다.
         */
        put: operations["put_finder"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/finder:commit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Commit Finder
         * @description 고른 후보 → 제품. `items` 면 제목 확정 · step 2(SP2), `products` 면 SP1 에 머문다(모델명으로 직접 입력).
         */
        post: operations["commit_finder"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/finder:parse": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Parse Finder
         * @description 문장 → 칩 · 추가 조건 · 후보(spec_find, 고객사 이름이 있을 수 있어 confidential).
         */
        post: operations["parse_finder"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/format": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Format */
        put: operations["put_format"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/format:preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Format Preview
         * @description SP2L 미리보기(결정적 · 동기): 격자 · 바뀐 셀 · 안내 줄 · 시트 탭 · 파일명 기본값.
         */
        post: operations["format_preview"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/generate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Generate Sheet
         * @description 시트 생성(5단계 잡). rerender = 형식만 바뀜(kb 다시 읽지 않음) · columns = 바뀐 열만.
         */
        post: operations["generate_sheet"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/handoffs": {
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
         * @description `제안서에 넣기`(SP4) · `새 제안서로 시작`(proposal_id null). Solution형은 422 NO_SPEC_SECTION.
         */
        post: operations["create_handoff"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/items": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Items */
        put: operations["put_items"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Post Message
         * @description 말로 수정(spec_revise). 생성 중이면 조종 메모(`시트 구성` 전에 반영, 200). 결과는 잡 result 의 applied_ops · reply · navigate.
         */
        post: operations["post_message"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/package": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Package
         * @description 넘김 없이 묶음 미리보기(SP4 슬라이드 미리보기 · 제안서 딸깍).
         */
        get: operations["get_package"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/products": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Products
         * @description 다른 기능으로 넘길 모델 ref(§3.7).
         */
        get: operations["list_products"];
        put?: never;
        /**
         * Add Products
         * @description 제품 추가(제품 입력창 · 제품 탐색 팝오버 onAdd · 조합 칩). 같은 모델은 넣지 않는다. 8개 넘으면 422 PRODUCT_LIMIT.
         */
        post: operations["add_products"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/products/{product_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Remove Product */
        delete: operations["remove_product"];
        options?: never;
        head?: never;
        /**
         * Patch Product
         * @description 역할 · 열 이름 · 순서 · 모델 바꾸기(대체 모델로 바꾸기 → 그 열만 다시 채움, 202 잡은 active_job 으로).
         */
        patch: operations["patch_product"];
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/proposal-handoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Proposal Handoff
         * @description ProposalHandoff v1(10-proposal §8.0 · P1) — 보이는 행 · 강조 · 각주 · [확정 필요] 칸 · 모델 목록 · live_link.
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
    "/v1/sheets/{sheet_id}/recheck": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Recheck
         * @description 시트 하나 재확인(카탈로그 · 생애주기 · 연결 · 요구) — 값은 바꾸지 않고 경고만.
         */
        post: operations["recheck"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/requirement-docs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Requirement Doc
         * @description 규격서 올리기(PDF · DOCX · XLSX · 이미지) → spec_compliance. 다른 규격서를 더 올리면 행이 합쳐진다.
         */
        post: operations["add_requirement_doc"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/requirement-docs/{doc_id}/pages/{n}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Requirement Page
         * @description 원문 쪽(이미지는 files 쪽 렌더) + 그 쪽의 인용들.
         */
        get: operations["requirement_page"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/share": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Share Sheet
         * @description `링크로 공유` — workspace 공유 링크(보기 전용).
         */
        post: operations["share_sheet"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/templates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Template
         * @description 고객사 양식 올리기(XLSX 권장 · PDF · DOCX · 이미지) → spec_template(confidential).
         */
        post: operations["add_template"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/templates/{template_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Remove Template */
        delete: operations["remove_template"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/versions": {
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
    "/v1/sheets/{sheet_id}/versions/{n}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Restore Version */
        post: operations["restore_version"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/warnings": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Warnings
         * @description SP3W — 카드(번호 = 종류 → 행 → 열) · 필터 수 · 결정 수 · 에이전트 문장 · 표 제목 · 바닥.
         */
        get: operations["list_warnings"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/warnings:apply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Apply Warnings
         * @description `선택한 대로 반영` — 결정이 있는 카드만 반영(한 번의 version +1). 대체 모델로 바꾸면 그 열만 다시 채움(202).
         */
        post: operations["apply_warnings"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/sheets/{sheet_id}/warnings/{warning_id}": {
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
         * Decide Warning
         * @description 카드의 선택(라디오 · 칩 · 버튼)을 저장 — 반영은 `선택한 대로 반영`(warnings:apply). 이동만 하는 버튼은 저장하지 않는다.
         */
        patch: operations["decide_warning"];
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** ActiveJob */
        ActiveJob: {
            /** Id */
            id: string;
            /** Kind */
            kind: string;
            /**
             * Progress
             * @default 0
             */
            progress: number;
            /** Status */
            status: string;
        };
        /** AddableRow */
        AddableRow: {
            /** Item Key */
            item_key: string;
            /** Label */
            label: string;
            /** Row Key */
            row_key: string;
        };
        /** AddProducts */
        AddProducts: {
            /** Refs */
            refs: string[];
            /** Role */
            role?: ("proposed" | "existing" | "alternative") | null;
            /** Source */
            source?: ("input" | "explorer" | "link" | "request" | "find" | "requirements") | null;
        };
        /** AddProductsResult */
        AddProductsResult: {
            /** Added */
            added: string[];
            sheet: components["schemas"]["SheetDoc"];
            /** Skipped */
            skipped?: components["schemas"]["SkippedRef"][];
        };
        /** Alternative */
        Alternative: {
            /** Label */
            label: string;
            /** Model Code */
            model_code?: string | null;
            /** Product Ref */
            product_ref: string;
        };
        /** AltMeasure */
        AltMeasure: {
            /** Footnote */
            footnote: string;
            /** Label */
            label: string;
            /** Value Text */
            value_text: string;
        };
        /** ApplyAnswer */
        ApplyAnswer: {
            /** Alt Measure */
            alt_measure?: string | null;
            /** Check Id */
            check_id: string;
            /** Option Key */
            option_key?: string | null;
            /** Value Text */
            value_text?: string | null;
        };
        /** AskDraft */
        AskDraft: {
            /**
             * Count
             * @default 0
             */
            count: number;
            /** Mailto */
            mailto: string;
            /** Text */
            text: string;
        };
        /** Banner */
        Banner: {
            /** Date */
            date: string;
            /** Route */
            route?: string | null;
            /** Sheets */
            sheets: number;
            /** Text */
            text: string;
        };
        /** Carry */
        Carry: {
            /**
             * Footnote Memos
             * @default 0
             */
            footnote_memos: number;
            /**
             * Hidden Rows Dropped
             * @default 0
             */
            hidden_rows_dropped: number;
            /**
             * Pending Cells
             * @default 0
             */
            pending_cells: number;
            /**
             * Visible Rows
             * @default 0
             */
            visible_rows: number;
            /**
             * Win Cells
             * @default 0
             */
            win_cells: number;
        };
        /** CatalogItem */
        CatalogItem: {
            /** Default Checked */
            default_checked: boolean;
            /** Group */
            group: string;
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Label En Lines */
            label_en_lines: string[];
            /** Rows */
            rows?: {
                [key: string]: unknown;
            }[];
        };
        /** CatalogLabel */
        CatalogLabel: {
            /**
             * Label
             * @default 사내 카탈로그
             */
            label: string;
            /**
             * Source Label
             * @default 사내 제품 카탈로그
             */
            source_label: string;
            /**
             * Version
             * @default
             */
            version: string;
        };
        /** CatalogStatus */
        CatalogStatus: {
            /** Adapter */
            adapter: string;
            /**
             * Changed Sheets
             * @default 0
             */
            changed_sheets: number;
            /** Detected At */
            detected_at?: string | null;
            /** Label */
            label: string;
            /** Previous Version */
            previous_version?: string | null;
            /** Source Label */
            source_label: string;
            /** Version */
            version: string;
        };
        /** Cell */
        Cell: {
            /** Check N */
            check_n?: number | null;
            /**
             * Converted
             * @default false
             */
            converted: boolean;
            /**
             * Flag Text
             * @description SP3G 미리보기 flag 칸 글(`값 없음` · `출처 {n}곳 다름`)
             */
            flag_text?: string | null;
            /** Original Text */
            original_text?: string | null;
            /** Product Id */
            product_id: string;
            /** Sources */
            sources?: components["schemas"]["Source"][];
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "checking" | "flag" | "pending" | "sync_pending" | "edited" | "derived";
            /** Text */
            text: string;
            /** Text En */
            text_en?: string | null;
            value?: components["schemas"]["CellValue"] | null;
            /** Warning Ns */
            warning_ns?: number[];
            /**
             * Win
             * @default false
             */
            win: boolean;
        };
        /** CellPart */
        CellPart: {
            /** Label */
            label: string;
            /** Num */
            num?: number | null;
            /** Text */
            text?: string | null;
            /** Unit */
            unit?: string | null;
        };
        /** CellPatch */
        CellPatch: {
            /** Value Text */
            value_text: string;
        };
        /** CellPatchResult */
        CellPatchResult: {
            cell: components["schemas"]["Cell"];
            /** Win Rows */
            win_rows: number;
        };
        /** CellValue */
        CellValue: {
            /** Num */
            num?: number | null;
            /** Num2 */
            num2?: number | null;
            /** Parts */
            parts?: components["schemas"]["CellPart"][] | null;
            /** Unit */
            unit?: string | null;
        };
        /** CheckAnswer */
        CheckAnswer: {
            /** Alt Measure */
            alt_measure?: string | null;
            /** Datasheet Id */
            datasheet_id?: string | null;
            /** Option Key */
            option_key?: string | null;
            /** Value Text */
            value_text?: string | null;
        };
        /** CheckAnswerBody */
        CheckAnswerBody: {
            /** Alt Measure */
            alt_measure?: string | null;
            /** Option Key */
            option_key?: string | null;
            /** Value Text */
            value_text?: string | null;
        };
        /** CheckList */
        CheckList: {
            /** Items */
            items: components["schemas"]["ValueCheck"][];
            /** Open */
            open: number;
        };
        /** CheckOption */
        CheckOption: {
            /** Key */
            key: string;
            /** Label */
            label: string;
            /**
             * Preselected
             * @default false
             */
            preselected: boolean;
            /**
             * Source Ref
             * @default
             */
            source_ref: string;
            /**
             * Tier
             * @default
             */
            tier: string;
            /** Value Text */
            value_text: string;
        };
        /** Checks */
        Checks: {
            /** Items */
            items?: components["schemas"]["ValueCheck"][];
            /**
             * Open
             * @default 0
             */
            open: number;
        };
        /** ChecksApply */
        ChecksApply: {
            /** Answers */
            answers?: components["schemas"]["ApplyAnswer"][];
        };
        /** ChecksApplyResult */
        ChecksApplyResult: {
            /** Next Route */
            next_route: string;
            /**
             * Pending Until Job Done
             * @default false
             */
            pending_until_job_done: boolean;
            sheet: components["schemas"]["SheetDoc"];
        };
        /** CloneBody */
        CloneBody: {
            /** Customer Name */
            customer_name?: string | null;
        };
        /** Combo */
        Combo: {
            /** Label */
            label: string;
            /** Model Codes */
            model_codes: string[];
            /** Refs */
            refs?: string[];
        };
        /** ComboList */
        ComboList: {
            /** Items */
            items: components["schemas"]["Combo"][];
        };
        /** CommitBody */
        CommitBody: {
            /**
             * Rebase
             * @default false
             */
            rebase: boolean;
        };
        /** Compliance */
        Compliance: {
            /** Agent Text */
            agent_text?: string | null;
            /** Alternative Label */
            alternative_label?: string | null;
            counts?: components["schemas"]["ComplianceCounts"];
            /** Customer */
            customer?: string | null;
            /** Docs */
            docs?: components["schemas"]["ComplianceDoc"][];
            /** Error */
            error?: string | null;
            /**
             * Folded Line
             * @description 처음 8행 밖 요약 `4개 더 · 충족 3 · 확인 필요 1`
             */
            folded_line?: string | null;
            include?: components["schemas"]["ComplianceInclude"];
            /** Note */
            note?: string | null;
            /**
             * Picked By Finder
             * @default false
             */
            picked_by_finder: boolean;
            /** Place */
            place?: string | null;
            /** Rows */
            rows?: components["schemas"]["ComplianceRow"][];
            /**
             * Status
             * @default empty
             * @enum {string}
             */
            status: "empty" | "running" | "done" | "failed";
            /** Target Label */
            target_label?: string | null;
            /** Target Product Id */
            target_product_id?: string | null;
        };
        /** ComplianceCounts */
        ComplianceCounts: {
            /**
             * Fail
             * @default 0
             */
            fail: number;
            /**
             * Pass
             * @default 0
             */
            pass: number;
            /**
             * Unknown
             * @default 0
             */
            unknown: number;
        };
        /** ComplianceDoc */
        ComplianceDoc: {
            /** File Id */
            file_id?: string | null;
            /** Format */
            format: string;
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Note */
            note?: string | null;
            /**
             * Pages
             * @default 0
             */
            pages: number;
            /**
             * Recognized
             * @default 0
             */
            recognized: number;
            /**
             * Status
             * @default done
             */
            status: string;
        };
        /** ComplianceInclude */
        ComplianceInclude: {
            /**
             * Alternative
             * @default false
             */
            alternative: boolean;
            /**
             * Page Refs
             * @default true
             */
            page_refs: boolean;
            /**
             * Spec
             * @default true
             */
            spec: boolean;
            /**
             * Table
             * @default true
             */
            table: boolean;
        };
        /** CompliancePatch */
        CompliancePatch: {
            /** Include */
            include?: {
                [key: string]: boolean;
            } | null;
            /** Target Product Id */
            target_product_id?: string | null;
            /**
             * Target Ref
             * @description 시트에 없는 모델을 대응 모델로(제품으로 추가)
             */
            target_ref?: string | null;
        };
        /** ComplianceRow */
        ComplianceRow: {
            alternative?: components["schemas"]["Alternative"] | null;
            /** Doc Id */
            doc_id?: string | null;
            /** Id */
            id: string;
            /** Item */
            item: string;
            /**
             * Kind
             * @default text
             */
            kind: string;
            /** Note */
            note?: string | null;
            /**
             * Overridden
             * @default false
             */
            overridden: boolean;
            /** Page */
            page?: number | null;
            /**
             * Quote
             * @default
             */
            quote: string;
            /** Requirement */
            requirement: string;
            /** Value Text */
            value_text: string;
            /**
             * Verdict
             * @enum {string}
             */
            verdict: "pass" | "fail" | "unknown";
        };
        /** ComplianceRowPatch */
        ComplianceRowPatch: {
            /** Note */
            note?: string | null;
            /** Verdict Override */
            verdict_override?: ("pass" | "fail" | "unknown") | null;
        };
        /** CreateSheet */
        CreateSheet: {
            /** Customer Name */
            customer_name?: string | null;
            /**
             * Models
             * @description products 와 같음(proposal P2 호환)
             */
            models?: string[] | null;
            origin?: components["schemas"]["Origin"] | null;
            /**
             * Products
             * @description ref · 모델코드 · mdl_ · fam_
             */
            products?: string[] | null;
            /** Project Id */
            project_id?: string | null;
            /**
             * Purpose
             * @description proposal 딸깍: 기본 항목 + 생성(auto_answer)까지 바로 시작
             */
            purpose?: "proposal" | null;
            /** Query Text */
            query_text?: string | null;
            /** Role */
            role?: ("proposed" | "existing" | "alternative") | null;
            /**
             * Rq Ref
             * @description {rq_id, version} — 요구사항 정의서 연결(선택)
             */
            rq_ref?: {
                [key: string]: unknown;
            } | null;
            /**
             * Start
             * @default model
             * @enum {string}
             */
            start: "model" | "explorer" | "find" | "requirements" | "clone" | "link";
            target_proposal?: components["schemas"]["TargetProposal"] | null;
        };
        /** DatasheetBody */
        DatasheetBody: {
            /** File Id */
            file_id: string;
            /** Product Id */
            product_id: string;
        };
        /** DatasheetInfo */
        DatasheetInfo: {
            /** File Id */
            file_id: string;
            /** Id */
            id: string;
            /** Name */
            name: string;
            /**
             * Pages
             * @default 0
             */
            pages: number;
            /** Product Id */
            product_id: string;
            /**
             * Status
             * @default queued
             */
            status: string;
        };
        /** DiffCell */
        DiffCell: {
            /** Current Text */
            current_text: string;
            /** Product Label */
            product_label: string;
            /** Row Label */
            row_label: string;
            /** Sent Text */
            sent_text: string;
        };
        /** DiffItems */
        DiffItems: {
            /** Different */
            different: string[];
        };
        /** EditColumn */
        EditColumn: {
            /** Label */
            label: string;
            /** Product Id */
            product_id: string;
            /**
             * Role
             * @enum {string}
             */
            role: "proposed" | "existing" | "alternative";
        };
        /** EditMessage */
        EditMessage: {
            /** Text */
            text: string;
        };
        /** EditOp */
        EditOp: {
            /** Item Key */
            item_key?: string | null;
            /** Mode */
            mode?: ("footnote" | "internal") | null;
            /**
             * Op
             * @enum {string}
             */
            op: "move_row" | "hide_row" | "show_row" | "highlight_row" | "unhighlight_row" | "set_memo" | "delete_memo" | "add_rows" | "remove_row" | "move_column";
            /** Product Id */
            product_id?: string | null;
            /** Row Id */
            row_id?: string | null;
            /** Row Keys */
            row_keys?: string[] | null;
            /** Text */
            text?: string | null;
            /** To Index */
            to_index?: number | null;
        };
        /** EditOps */
        EditOps: {
            /** Ops */
            ops: components["schemas"]["EditOp"][];
        };
        /** EditRow */
        EditRow: {
            /**
             * Added By
             * @default items
             * @enum {string}
             */
            added_by: "items" | "edit" | "request" | "template";
            /** Cells */
            cells?: components["schemas"]["Cell"][];
            /** Footnote Mark */
            footnote_mark?: string | null;
            /**
             * Hidden
             * @default false
             */
            hidden: boolean;
            /**
             * Highlighted
             * @default false
             */
            highlighted: boolean;
            /** Id */
            id: string;
            /** Item Key */
            item_key?: string | null;
            /** Label */
            label: string;
            /** Label En */
            label_en?: string | null;
            /** Lines */
            lines?: components["schemas"]["RowLine"][];
            memo?: components["schemas"]["Memo"] | null;
            /**
             * Moved
             * @default 0
             */
            moved: number;
            /** Ord */
            ord: number;
            /** Row Key */
            row_key: string;
            /** Tags */
            tags?: string[];
            /**
             * Win
             * @default false
             */
            win: boolean;
        };
        /** EditSessionCreated */
        EditSessionCreated: {
            /** Base Version */
            base_version: number;
            /** Id */
            id: string;
            view: components["schemas"]["EditView"];
        };
        /** EditSummary */
        EditSummary: {
            /**
             * Add
             * @default 0
             */
            add: number;
            /**
             * Column
             * @default 0
             */
            column: number;
            /**
             * Hide
             * @default 0
             */
            hide: number;
            /**
             * Highlight
             * @default 0
             */
            highlight: number;
            /**
             * Memo
             * @default 0
             */
            memo: number;
            /**
             * Move
             * @default 0
             */
            move: number;
            /**
             * Remove
             * @default 0
             */
            remove: number;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** EditView */
        EditView: {
            /** Addable Rows */
            addable_rows: components["schemas"]["AddableRow"][];
            /** Base Version */
            base_version: number;
            /** Can Redo */
            can_redo: boolean;
            /** Can Undo */
            can_undo: boolean;
            /** Columns */
            columns: components["schemas"]["EditColumn"][];
            /** Current Version */
            current_version: number;
            /** Hidden Count */
            hidden_count: number;
            /** History */
            history: components["schemas"]["HistoryItem"][];
            /** Missing Items */
            missing_items: components["schemas"]["MissingItem"][];
            /** Rows */
            rows: components["schemas"]["EditRow"][];
            /** Session Id */
            session_id: string;
            /**
             * Stale
             * @default false
             */
            stale: boolean;
            /**
             * Status
             * @default open
             * @enum {string}
             */
            status: "open" | "committed" | "discarded";
            summary: components["schemas"]["EditSummary"];
            /** Summary Text */
            summary_text: string;
            /** Title */
            title: string;
            /** Total */
            total: number;
            /** Visible */
            visible: number;
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
        /** ExportAccepted */
        ExportAccepted: {
            /** Export Id */
            export_id: string;
            /** Job Id */
            job_id: string;
            /**
             * Status
             * @default queued
             * @constant
             */
            status: "queued";
        };
        /** ExportBody */
        ExportBody: {
            /** Filename */
            filename?: string | null;
            /**
             * Format
             * @enum {string}
             */
            format: "xlsx" | "pdf" | "pptx";
            options?: components["schemas"]["ExportOptions"] | null;
            overrides?: components["schemas"]["FormatSettingsPatch"] | null;
        };
        /** ExportOptions */
        ExportOptions: {
            /**
             * Drop Hidden
             * @default true
             */
            drop_hidden: boolean;
            /**
             * Keep Pending Marks
             * @default true
             */
            keep_pending_marks: boolean;
            /**
             * Memo Footnotes
             * @default true
             */
            memo_footnotes: boolean;
        };
        /** ExportRecord */
        ExportRecord: {
            /** Download Url */
            download_url?: string | null;
            /** Error */
            error?: string | null;
            /** File Id */
            file_id?: string | null;
            /** Filename */
            filename: string;
            /**
             * Format
             * @enum {string}
             */
            format: "xlsx" | "pdf" | "pptx";
            /** Id */
            id: string;
            /** Job Id */
            job_id?: string | null;
            /** Slide Count */
            slide_count?: number | null;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "done" | "failed";
            /** Warnings */
            warnings?: string[];
        };
        /** FactCheck */
        FactCheck: {
            /**
             * Placeholder
             * @default [확정 필요]
             * @constant
             */
            placeholder: "[확정 필요]";
            /** Reason */
            reason: string;
            /** Sheet Index */
            sheet_index: number;
            /** Text */
            text: string;
        };
        /** FinderCandidate */
        FinderCandidate: {
            /** Brightness Nit */
            brightness_nit?: number | null;
            /**
             * C2 Score
             * @default 0
             */
            c2_score: number;
            /** Display Name */
            display_name: string;
            /** Model Code */
            model_code: string;
            /**
             * Ok
             * @default 0
             */
            ok: number;
            /** Operation */
            operation?: string | null;
            /**
             * Out
             * @default false
             */
            out: boolean;
            /** Out Reason */
            out_reason?: string | null;
            /** Power Text */
            power_text?: string | null;
            /** Ref */
            ref: string;
            /** Rows */
            rows?: components["schemas"]["FinderCondRow"][];
            /**
             * Selected
             * @default false
             */
            selected: boolean;
            /** Series Label */
            series_label: string;
            /** Size Inch */
            size_inch?: number | null;
            /**
             * Total
             * @default 0
             */
            total: number;
            /** Weight Text */
            weight_text?: string | null;
        };
        /** FinderCommit */
        FinderCommit: {
            /** Selected */
            selected: string[];
            /**
             * To
             * @default items
             * @enum {string}
             */
            to: "items" | "products";
        };
        /** FinderConditions */
        FinderConditions: {
            /**
             * Brightness
             * @default any
             * @enum {string}
             */
            brightness: "any" | "desc" | "outdoor";
            /** Install */
            install?: ("wall" | "stand" | "ceiling" | "portrait")[];
            /**
             * Off
             * @description 사용자가 끈 칩(문장 해석이 다시 켜지 않음) — 'size:55' · 'usage:monitoring' …
             */
            off?: string[];
            /**
             * Required
             * @description continuous_operation · wall · magicinfo · size · stand · …
             */
            required?: string[];
            /** Sizes */
            sizes?: ("43" | "50" | "55" | "65" | "75+")[];
            /** Usage */
            usage?: ("menu_board" | "wayfinding" | "monitoring" | "meeting")[];
        };
        /** FinderCondRow */
        FinderCondRow: {
            /** Key */
            key: string;
            /** Label */
            label: string;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "check" | "no";
            /** Value Text */
            value_text: string;
        };
        /** FinderExtra */
        FinderExtra: {
            /** Capability Id */
            capability_id?: string | null;
            /** Id */
            id: string;
            /** Key */
            key?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "filter" | "sort";
            /** Label */
            label: string;
            /** Op */
            op?: string | null;
            /** Value */
            value?: number | string | null;
        };
        /** FinderParse */
        FinderParse: {
            /** Text */
            text: string;
        };
        /** FinderPut */
        FinderPut: {
            conditions?: components["schemas"]["FinderConditions"] | null;
            /** Extra */
            extra?: components["schemas"]["FinderExtra"][] | null;
            /** Hide Out */
            hide_out?: boolean | null;
            /**
             * Preset
             * @description 다른 화면에서 올 때 조건 미리 채우기: 'row:{srq}'(대안 보기) · 'alternatives'(대안 모델 찾기) · 'warning:{swn}'(다른 후보 찾기)
             */
            preset?: string | null;
            /** Selected */
            selected?: string[] | null;
            /** View */
            view?: ("cards" | "table") | null;
        };
        /** FinderState */
        FinderState: {
            /** Agent Text */
            agent_text?: string | null;
            /** Candidates */
            candidates?: components["schemas"]["FinderCandidate"][];
            /**
             * Catalog Version
             * @default
             */
            catalog_version: string;
            conditions?: components["schemas"]["FinderConditions"];
            /** Customer */
            customer?: string | null;
            /** Error */
            error?: string | null;
            /** Extra */
            extra?: components["schemas"]["FinderExtra"][];
            /**
             * Hide Out
             * @default false
             */
            hide_out: boolean;
            /** Place */
            place?: string | null;
            /** Query Text */
            query_text?: string | null;
            /**
             * Selected
             * @description 고른 후보 ref(카드에서 사라져도 유지)
             */
            selected?: string[];
            /** Sort Label */
            sort_label?: string | null;
            /**
             * Status
             * @default idle
             * @enum {string}
             */
            status: "idle" | "running" | "done" | "failed";
            /**
             * Total Candidates
             * @default 0
             */
            total_candidates: number;
            /**
             * View
             * @default cards
             * @enum {string}
             */
            view: "cards" | "table";
        };
        /** Footnote */
        Footnote: {
            /** Mark */
            mark: string;
            /** Text */
            text: string;
        };
        /** FormatPreview */
        FormatPreview: {
            /** Chip Label */
            chip_label: string;
            /** Converted Cells */
            converted_cells: number;
            /** Ext Line */
            ext_line: string;
            /** Filename Default */
            filename_default: string;
            /** Footnotes */
            footnotes?: components["schemas"]["Footnote"][];
            grid: components["schemas"]["Grid"];
            /** Note Line */
            note_line?: string | null;
            /** Sheet Tabs */
            sheet_tabs: string[];
            /**
             * Source Line
             * @default
             */
            source_line: string;
            /** Tab Labels */
            tab_labels: {
                [key: string]: string;
            };
            /** Title */
            title: string;
        };
        /** FormatPreviewBody */
        FormatPreviewBody: {
            /**
             * Filename Base
             * @description null = 규칙 기본값(§4.16.6)
             */
            filename_base?: string | null;
            /**
             * Formats
             * @description 최소 1
             */
            formats?: ("xlsx" | "pdf" | "pptx")[];
            /**
             * Language
             * @default ko
             * @enum {string}
             */
            language: "ko" | "en" | "ko_en";
            /**
             * Length Unit
             * @default mm
             * @enum {string}
             */
            length_unit: "mm" | "inch" | "both";
            /**
             * Number Format
             * @default 1,234.5
             * @enum {string}
             */
            number_format: "1,234.5" | "1.234,5";
            /**
             * Paper
             * @default a4_landscape
             * @enum {string}
             */
            paper: "a4_landscape" | "a4_portrait" | "letter";
            /**
             * Tab
             * @default xlsx
             * @enum {string}
             */
            tab: "xlsx" | "pdf" | "pptx";
            /**
             * Weight Unit
             * @default kg
             * @enum {string}
             */
            weight_unit: "kg" | "lb" | "both";
        };
        /** FormatSettings */
        FormatSettings: {
            /**
             * Filename Base
             * @description null = 규칙 기본값(§4.16.6)
             */
            filename_base?: string | null;
            /**
             * Formats
             * @description 최소 1
             */
            formats?: ("xlsx" | "pdf" | "pptx")[];
            /**
             * Language
             * @default ko
             * @enum {string}
             */
            language: "ko" | "en" | "ko_en";
            /**
             * Length Unit
             * @default mm
             * @enum {string}
             */
            length_unit: "mm" | "inch" | "both";
            /**
             * Number Format
             * @default 1,234.5
             * @enum {string}
             */
            number_format: "1,234.5" | "1.234,5";
            /**
             * Paper
             * @default a4_landscape
             * @enum {string}
             */
            paper: "a4_landscape" | "a4_portrait" | "letter";
            /**
             * Weight Unit
             * @default kg
             * @enum {string}
             */
            weight_unit: "kg" | "lb" | "both";
        };
        /** FormatSettingsPatch */
        FormatSettingsPatch: {
            /** Filename Base */
            filename_base?: string | null;
            /** Formats */
            formats?: ("xlsx" | "pdf" | "pptx")[] | null;
            /** Language */
            language?: ("ko" | "en" | "ko_en") | null;
            /** Length Unit */
            length_unit?: ("mm" | "inch" | "both") | null;
            /** Number Format */
            number_format?: ("1,234.5" | "1.234,5") | null;
            /** Paper */
            paper?: ("a4_landscape" | "a4_portrait" | "letter") | null;
            /** Weight Unit */
            weight_unit?: ("kg" | "lb" | "both") | null;
        };
        /** GenerateBody */
        GenerateBody: {
            /**
             * Auto Answer
             * @default false
             */
            auto_answer: boolean;
            /**
             * Mode
             * @default full
             * @enum {string}
             */
            mode: "full" | "rerender" | "columns";
            /** Product Ids */
            product_ids?: string[] | null;
        };
        /** Grid */
        Grid: {
            /** Cols */
            cols: string[];
            /** Rows */
            rows: components["schemas"]["GridRow"][];
        };
        /** GridCell */
        GridCell: {
            /**
             * Converted
             * @default false
             */
            converted: boolean;
            /**
             * Kind
             * @default cell
             * @enum {string}
             */
            kind: "title" | "head" | "cell" | "label";
            /**
             * Pending
             * @default false
             */
            pending: boolean;
            /** Text */
            text: string;
            /**
             * Win
             * @default false
             */
            win: boolean;
        };
        /** GridRow */
        GridRow: {
            /** Cells */
            cells: components["schemas"]["GridCell"][];
            /** N */
            n: number;
        };
        /** Handoff */
        Handoff: {
            /** Ack */
            ack?: {
                [key: string]: unknown;
            } | null;
            /** Created At */
            created_at: string;
            /** Id */
            id: string;
            /** Mode */
            mode: string;
            package: components["schemas"]["Package"];
            /** Proposal Id */
            proposal_id?: string | null;
            /** Proposal Type */
            proposal_type?: string | null;
            /** Sheet Id */
            sheet_id: string;
            /** Sheet Version */
            sheet_version: number;
            /**
             * Status
             * @enum {string}
             */
            status: "ready" | "acked" | "failed";
            /** Templates */
            templates: string[];
        };
        /** HandoffAck */
        HandoffAck: {
            /** Proposal Id */
            proposal_id?: string | null;
            /** Proposal Sheet Ids */
            proposal_sheet_ids?: string[];
            /** Proposal Title */
            proposal_title?: string | null;
            /**
             * Result
             * @enum {string}
             */
            result: "applied" | "failed";
            /** Section Name */
            section_name?: string | null;
            /** Section No */
            section_no?: string | null;
        };
        /** HandoffBody */
        HandoffBody: {
            /**
             * Mode
             * @default replace
             * @enum {string}
             */
            mode: "replace" | "add";
            options?: components["schemas"]["ExportOptions"] | null;
            overrides?: components["schemas"]["FormatSettingsPatch"] | null;
            /** Proposal Id */
            proposal_id?: string | null;
            /** Proposal Title */
            proposal_title?: string | null;
            /**
             * Proposal Type
             * @default standard
             * @enum {string}
             */
            proposal_type: "standard" | "quickwin" | "solution";
            /** Replace Proposal Sheet Ids */
            replace_proposal_sheet_ids?: string[] | null;
            /** Section No */
            section_no?: string | null;
            /** Templates */
            templates?: ("SC-A" | "SC-B" | "SD-A")[];
        };
        /** HandoffCreated */
        HandoffCreated: {
            /** Id */
            id: string;
            /** Open Route */
            open_route: string;
            package: components["schemas"]["Package"];
            /**
             * Status
             * @enum {string}
             */
            status: "ready" | "acked" | "failed";
        };
        /** HistoryItem */
        HistoryItem: {
            /** N */
            n: number;
            /** Text */
            text: string;
        };
        /** ItemCatalog */
        ItemCatalog: {
            /** Category */
            category: string;
            /** Items */
            items: components["schemas"]["CatalogItem"][];
        };
        /** ItemsPut */
        ItemsPut: {
            /** Highlight Wins */
            highlight_wins?: boolean | null;
            /**
             * Items
             * @description [{key, checked}]
             */
            items?: {
                [key: string]: unknown;
            }[] | null;
            /** Language */
            language?: ("ko" | "en" | "ko_en") | null;
            /** Layout */
            layout?: ("compare" | "per_product") | null;
        };
        /** JobAccepted */
        JobAccepted: {
            /** Job Id */
            job_id: string;
            /** Sheet Id */
            sheet_id?: string | null;
            /**
             * Status
             * @default queued
             * @constant
             */
            status: "queued";
        };
        /** Lifecycle */
        Lifecycle: {
            /** As Of */
            as_of?: string | null;
            /**
             * Sold Out
             * @default false
             */
            sold_out: boolean;
            /**
             * Source
             * @default
             */
            source: string;
            /**
             * Status
             * @default unknown
             * @enum {string}
             */
            status: "on_sale" | "discontinued" | "eol_planned" | "unknown";
            successor?: components["schemas"]["Successor"] | null;
        };
        /** LifecycleCheckBody */
        LifecycleCheckBody: {
            /**
             * Locale
             * @default ko
             * @enum {string}
             */
            locale: "ko" | "en" | "ko_en";
            /** Model Codes */
            model_codes: string[];
        };
        /** LifecycleCheckItem */
        LifecycleCheckItem: {
            /** Display Name */
            display_name?: string | null;
            /** Evidence */
            evidence: string;
            /** Model Code */
            model_code: string;
            /**
             * Status
             * @enum {string}
             */
            status: "on_sale" | "discontinued" | "unknown";
            /** Successors */
            successors?: components["schemas"]["LifecycleSuccessor"][];
        };
        /** LifecycleCheckResult */
        LifecycleCheckResult: {
            /** Items */
            items: components["schemas"]["LifecycleCheckItem"][];
        };
        /** LifecycleEntry */
        LifecycleEntry: {
            /** As Of */
            as_of?: string | null;
            /** Model Key */
            model_key: string;
            /** Note */
            note?: string | null;
            /**
             * Source Label
             * @default 사내 제품 카탈로그
             */
            source_label: string;
            /**
             * Status
             * @enum {string}
             */
            status: "on_sale" | "discontinued" | "eol_planned" | "unknown";
            /** Successor Model Code */
            successor_model_code?: string | null;
        };
        /** LifecycleList */
        LifecycleList: {
            /** Items */
            items: components["schemas"]["LifecycleEntry"][];
        };
        /** LifecycleSuccessor */
        LifecycleSuccessor: {
            /** Display Name */
            display_name?: string | null;
            /** Model Code */
            model_code: string;
            /** Reason */
            reason: string;
            /** Spec Diff Summary */
            spec_diff_summary?: string | null;
        };
        /** LinkInfo */
        LinkInfo: {
            /** Id */
            id: string;
            /** Proposal Id */
            proposal_id: string;
            /** Proposal Title */
            proposal_title: string;
            /** Section Name */
            section_name: string;
            /** Section No */
            section_no: string;
            /** Sent Version */
            sent_version: number;
            /**
             * Status
             * @enum {string}
             */
            status: "in_sync" | "sheet_changed";
        };
        /** LinkItem */
        LinkItem: {
            /** Current Version */
            current_version: number;
            /** Diff Cells */
            diff_cells: components["schemas"]["DiffCell"][];
            /** Link Id */
            link_id: string;
            /** Proposal Id */
            proposal_id: string;
            /** Route */
            route: string;
            /** Sent Version */
            sent_version: number;
            /** Sheet Id */
            sheet_id: string;
            /** Sheet Title */
            sheet_title: string;
            /**
             * Status
             * @enum {string}
             */
            status: "in_sync" | "sheet_changed";
        };
        /** LinkList */
        LinkList: {
            /** Items */
            items: components["schemas"]["LinkItem"][];
        };
        /**
         * LinksReleased
         * @description `DELETE /v1/links?proposal_id=`(internal) — 제안서를 지웠을 때 그 제안서와의 연결을 거둔 결과.
         */
        LinksReleased: {
            /** Deleted */
            deleted: number;
            /** Proposal Id */
            proposal_id: string;
            /** Sheet Ids */
            sheet_ids?: string[];
        };
        /** Memo */
        Memo: {
            /**
             * Mode
             * @default footnote
             * @enum {string}
             */
            mode: "footnote" | "internal";
            /** Text */
            text: string;
        };
        /** MessageBody */
        MessageBody: {
            /**
             * Context
             * @default result
             * @enum {string}
             */
            context: "generating" | "result" | "warnings" | "export" | "find" | "requirements";
            /** Text */
            text: string;
        };
        /** MessageQueued */
        MessageQueued: {
            /** Job Id */
            job_id?: string | null;
            /**
             * Memo
             * @description true = 생성 중이라 조종 메모로 들어감(job_id = 생성 잡)
             * @default false
             */
            memo: boolean;
            /**
             * Queued
             * @default true
             */
            queued: boolean;
        };
        /** MissingItem */
        MissingItem: {
            /** Key */
            key: string;
            /** Label */
            label: string;
        };
        /** Options */
        Options: {
            /**
             * Highlight Wins
             * @default true
             */
            highlight_wins: boolean;
        };
        /** Origin */
        Origin: {
            /** From */
            from?: ("home" | "mi" | "vp" | "birdseye" | "product_detail" | "proposal" | "clone") | null;
            /** Ref */
            ref?: string | null;
        };
        /** Package */
        Package: {
            carry: components["schemas"]["Carry"];
            /** Catalog */
            catalog: {
                [key: string]: string;
            };
            /** Customer Name */
            customer_name?: string | null;
            /** Fact Check */
            fact_check: components["schemas"]["FactCheck"][];
            /**
             * Lines
             * @description SP4 넘어가는 것 4줄
             */
            lines?: string[];
            /** Link Back */
            link_back: {
                [key: string]: string;
            };
            /**
             * Locale
             * @enum {string}
             */
            locale: "ko" | "en" | "ko_en";
            /**
             * Mode
             * @default replace
             * @enum {string}
             */
            mode: "replace" | "add";
            /** Replace Proposal Sheet Ids */
            replace_proposal_sheet_ids?: string[] | null;
            /** Sheet Id */
            sheet_id: string;
            /** Sheet Version */
            sheet_version: number;
            /** Sheets */
            sheets: components["schemas"]["PackageSheet"][];
            /** Title */
            title: string;
        };
        /** PackageSheet */
        PackageSheet: {
            /** Data */
            data: {
                [key: string]: unknown;
            };
            /**
             * Template
             * @enum {string}
             */
            template: "SC-A" | "SC-B" | "SD-A" | "SD-B";
        };
        /** PageQuote */
        PageQuote: {
            /** Bbox */
            bbox?: number[] | null;
            /** Row Id */
            row_id: string;
            /** Text */
            text: string;
        };
        /** PageView */
        PageView: {
            /** Image File Id */
            image_file_id?: string | null;
            /** Image Url */
            image_url?: string | null;
            /** Page */
            page: number;
            /** Quotes */
            quotes?: components["schemas"]["PageQuote"][];
            /**
             * Text
             * @default
             */
            text: string;
        };
        /** PatchProduct */
        PatchProduct: {
            /** Column Label */
            column_label?: string | null;
            /** Model Ref */
            model_ref?: string | null;
            /** Ord */
            ord?: number | null;
            /** Role */
            role?: ("proposed" | "existing" | "alternative") | null;
        };
        /** PatchSheet */
        PatchSheet: {
            /**
             * Clear Target Proposal
             * @default false
             */
            clear_target_proposal: boolean;
            /**
             * Confirm Title
             * @default false
             */
            confirm_title: boolean;
            /** Customer Name */
            customer_name?: string | null;
            /** Step */
            step?: (1 | 2) | null;
            target_proposal?: components["schemas"]["TargetProposal"] | null;
            /** Title */
            title?: string | null;
        };
        /** PHFact */
        PHFact: {
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
        /** PHItem */
        PHItem: {
            /** Content */
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
            /** Repeat Key */
            repeat_key?: {
                [key: string]: string;
            } | null;
            /** Sheet Role */
            sheet_role: string;
            /** Sheet Title */
            sheet_title?: string | null;
            /** Sources */
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
        /** PHSource */
        PHSource: {
            /** Feature */
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
        /** PHTarget */
        PHTarget: {
            /** Proposal Type */
            proposal_type: string;
            /** Section Key */
            section_key: string;
        };
        /** Preferences */
        Preferences: {
            format: components["schemas"]["FormatSettings"];
            /**
             * Highlight Wins
             * @default true
             */
            highlight_wins: boolean;
            /**
             * Is Custom
             * @default false
             */
            is_custom: boolean;
        };
        /** Product */
        Product: {
            /**
             * Bubble Label
             * @description 'Smart Signage QM55C' — 계열명이 없으면 표시명
             */
            bubble_label: string;
            /** Column Label */
            column_label?: string | null;
            /**
             * Custom
             * @default false
             */
            custom: boolean;
            /** Display Name */
            display_name: string;
            /** Family Id */
            family_id?: string | null;
            /** Family Label En */
            family_label_en?: string | null;
            /** Id */
            id: string;
            /** Kb Model Id */
            kb_model_id?: string | null;
            lifecycle?: components["schemas"]["Lifecycle"];
            /** Model Code */
            model_code?: string | null;
            /** Ref */
            ref: string;
            /**
             * Role
             * @default proposed
             * @enum {string}
             */
            role: "proposed" | "existing" | "alternative";
            /** Series Code */
            series_code?: string | null;
            /** Size Inch */
            size_inch?: number | null;
            /**
             * Source
             * @default input
             */
            source: string;
            /**
             * Warning Ns
             * @description 열 머리 경고 번호(단종 · 카탈로그 없음)
             */
            warning_ns?: number[];
        };
        /** ProductRefItem */
        ProductRefItem: {
            /** Display Name */
            display_name: string;
            /** Family Id */
            family_id?: string | null;
            /** Kb Model Id */
            kb_model_id?: string | null;
            /** Model Code */
            model_code?: string | null;
            /** Ref */
            ref: string;
            /**
             * Role
             * @enum {string}
             */
            role: "proposed" | "existing" | "alternative";
        };
        /** ProductRefList */
        ProductRefList: {
            /** Items */
            items: components["schemas"]["ProductRefItem"][];
        };
        /** ProposalHandoff */
        ProposalHandoff: {
            /** Customer */
            customer?: {
                [key: string]: unknown;
            } | null;
            /** Facts */
            facts?: components["schemas"]["PHFact"][];
            /** Items */
            items: components["schemas"]["PHItem"][];
            /**
             * Live Link
             * @default true
             */
            live_link: boolean;
            /** Rq Ref */
            rq_ref?: {
                [key: string]: unknown;
            } | null;
            source: components["schemas"]["PHSource"];
            target: components["schemas"]["PHTarget"];
        };
        /** Replacement */
        Replacement: {
            /**
             * Already In Sheet
             * @default false
             */
            already_in_sheet: boolean;
            /** Label */
            label: string;
            /** Model Code */
            model_code?: string | null;
            /** Relation Text */
            relation_text: string;
        };
        /** RequirementDocBody */
        RequirementDocBody: {
            /** File Id */
            file_id: string;
            /** Note */
            note?: string | null;
        };
        /** Row */
        Row: {
            /**
             * Added By
             * @default items
             * @enum {string}
             */
            added_by: "items" | "edit" | "request" | "template";
            /** Cells */
            cells?: components["schemas"]["Cell"][];
            /** Footnote Mark */
            footnote_mark?: string | null;
            /**
             * Hidden
             * @default false
             */
            hidden: boolean;
            /**
             * Highlighted
             * @default false
             */
            highlighted: boolean;
            /** Id */
            id: string;
            /** Item Key */
            item_key?: string | null;
            /** Label */
            label: string;
            /** Label En */
            label_en?: string | null;
            /** Lines */
            lines?: components["schemas"]["RowLine"][];
            memo?: components["schemas"]["Memo"] | null;
            /** Ord */
            ord: number;
            /** Row Key */
            row_key: string;
            /**
             * Win
             * @default false
             */
            win: boolean;
        };
        /**
         * RowLine
         * @description 시트 언어로 그린 줄(영문 · 한/영에서 `화면 크기 · 해상도` · `밝기 · 명암비` 는 두 줄).
         */
        RowLine: {
            /** Converted */
            converted?: boolean[];
            /** Label */
            label: string;
            /** Pending */
            pending?: boolean[];
            /** Texts */
            texts: string[];
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
        /** ShareResult */
        ShareResult: {
            /** Share Url */
            share_url: string;
        };
        /** SheetDoc */
        SheetDoc: {
            active_job?: components["schemas"]["ActiveJob"] | null;
            /**
             * Agent
             * @description 화면 에이전트 문장(sp2 · sp3 · sp3g · from_note …)
             */
            agent?: {
                [key: string]: string | null;
            };
            /** Archived At */
            archived_at?: string | null;
            catalog: components["schemas"]["CatalogLabel"];
            checks: components["schemas"]["Checks"];
            compliance?: components["schemas"]["Compliance"] | null;
            /** Created At */
            created_at?: string | null;
            /** Customer Name */
            customer_name?: string | null;
            /** Datasheets */
            datasheets?: components["schemas"]["DatasheetInfo"][];
            finder?: components["schemas"]["FinderState"] | null;
            format: components["schemas"]["FormatSettings"];
            /** Format Confirmed */
            format_confirmed: boolean;
            /** @description 말로 요청한 형식(SP2L 이 미리 고른 값, 저장 전) */
            format_draft?: components["schemas"]["FormatSettingsPatch"] | null;
            /** Generated At */
            generated_at?: string | null;
            /** Id */
            id: string;
            /** Items */
            items: components["schemas"]["SheetItem"][];
            /**
             * Kind
             * @enum {string}
             */
            kind: "single" | "compare" | "req";
            /**
             * Last Error
             * @description 마지막 생성 잡 실패 원인(SP3G `시트를 만들지 못했어요. {원인}`)
             */
            last_error?: string | null;
            /** Last Job Id */
            last_job_id?: string | null;
            /**
             * Layout
             * @default compare
             * @enum {string}
             */
            layout: "compare" | "per_product";
            /** Links */
            links?: components["schemas"]["LinkInfo"][];
            options: components["schemas"]["Options"];
            origin?: components["schemas"]["Origin"] | null;
            /** Owner Name */
            owner_name?: string | null;
            /**
             * Product Limit
             * @default 8
             */
            product_limit: number;
            /** Products */
            products: components["schemas"]["Product"][];
            /** Project Id */
            project_id?: string | null;
            /** Resume Route */
            resume_route: string;
            /** Saved At */
            saved_at?: string | null;
            /**
             * Start
             * @enum {string}
             */
            start: "model" | "explorer" | "find" | "requirements" | "clone" | "link";
            /** Status Text */
            status_text: string;
            /**
             * Step
             * @enum {integer}
             */
            step: 1 | 2 | 3;
            /** Suggested Title */
            suggested_title: string;
            table?: components["schemas"]["SheetTable"] | null;
            target_proposal?: components["schemas"]["TargetProposal"] | null;
            template?: components["schemas"]["TemplateInfo"] | null;
            /** Title */
            title: string;
            /** Title Confirmed */
            title_confirmed: boolean;
            /**
             * Ui Status
             * @enum {string}
             */
            ui_status: "draft" | "run" | "check" | "warn" | "done";
            /** Updated At */
            updated_at: string;
            /** Version */
            version: number;
            warnings: components["schemas"]["Warnings"];
        };
        /** SheetItem */
        SheetItem: {
            /** Checked */
            checked: boolean;
            /** Key */
            key: string;
            /** Label */
            label: string;
            /**
             * Prechecked By
             * @default default
             * @enum {string}
             */
            prechecked_by: "default" | "requirement" | "user";
        };
        /** SheetList */
        SheetList: {
            /**
             * Archived Count
             * @default 0
             */
            archived_count: number;
            banner?: components["schemas"]["Banner"] | null;
            counts: components["schemas"]["TabCounts"];
            /** Items */
            items: components["schemas"]["SheetListItem"][];
            /** Next Cursor */
            next_cursor?: string | null;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** SheetListItem */
        SheetListItem: {
            /** Id */
            id: string;
            /** Model Chips */
            model_chips: string[];
            /**
             * More Models
             * @default 0
             */
            more_models: number;
            /** Output Label */
            output_label: string;
            /** Proposal Label */
            proposal_label: string;
            /** Resume Route */
            resume_route: string;
            /** Status Text */
            status_text: string;
            /** Sub Line */
            sub_line: string;
            /** Title */
            title: string;
            /**
             * Type Icon
             * @enum {string}
             */
            type_icon: "compare" | "single" | "req" | "find";
            /**
             * Ui Status
             * @enum {string}
             */
            ui_status: "draft" | "run" | "check" | "warn" | "done";
            /** Updated At */
            updated_at: string;
            /** When Label */
            when_label: string;
        };
        /** SheetTable */
        SheetTable: {
            /** Footnotes */
            footnotes?: components["schemas"]["Footnote"][];
            /**
             * Hidden Rows
             * @default 0
             */
            hidden_rows: number;
            /** Rows */
            rows: components["schemas"]["Row"][];
            /** Source Line */
            source_line: string;
            /** Title */
            title: string;
            /** Title En */
            title_en: string;
            /**
             * Total Rows
             * @default 0
             */
            total_rows: number;
            /**
             * Visible Rows
             * @default 0
             */
            visible_rows: number;
            /**
             * Win Rows
             * @default 0
             */
            win_rows: number;
        };
        /** SkippedRef */
        SkippedRef: {
            /**
             * Reason
             * @enum {string}
             */
            reason: "duplicate" | "limit" | "unresolved";
            /** Ref */
            ref: string;
        };
        /** Source */
        Source: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "catalog" | "datasheet" | "policy_doc" | "user" | "derived";
            /** Label */
            label: string;
            /** Page */
            page?: number | null;
            /** Quote */
            quote?: string | null;
            /**
             * Ref
             * @default
             */
            ref: string;
            /**
             * Tier
             * @default
             */
            tier: string;
            /**
             * Version Or Date
             * @default
             */
            version_or_date: string;
        };
        /** SourceList */
        SourceList: {
            /** Sources */
            sources: components["schemas"]["Source"][];
        };
        /** Successor */
        Successor: {
            /** Display Name */
            display_name: string;
            /** Model Code */
            model_code: string;
            /** Relation */
            relation: string;
        };
        /** TabCounts */
        TabCounts: {
            /**
             * All
             * @default 0
             */
            all: number;
            /**
             * Check
             * @default 0
             */
            check: number;
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
        };
        /** TargetProposal */
        TargetProposal: {
            /** Id */
            id: string;
            /**
             * Section No
             * @default 08
             */
            section_no: string;
            /** Subtitle */
            subtitle?: string | null;
            /** Title */
            title: string;
            /**
             * Type
             * @default standard
             * @enum {string}
             */
            type: "standard" | "quickwin" | "solution";
        };
        /** TemplateBody */
        TemplateBody: {
            /** File Id */
            file_id: string;
        };
        /** TemplateInfo */
        TemplateInfo: {
            /** File Id */
            file_id?: string | null;
            /** Format */
            format?: string | null;
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Status */
            status: string;
        };
        /** ValueCheck */
        ValueCheck: {
            /** Alt Measures */
            alt_measures?: components["schemas"]["AltMeasure"][];
            answer?: components["schemas"]["CheckAnswer"] | null;
            /** Body */
            body: string;
            /** Id */
            id: string;
            /** Input Label */
            input_label?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "missing" | "conflict" | "missing_product";
            /** N */
            n: number;
            /** Options */
            options?: components["schemas"]["CheckOption"][];
            /** Placeholder */
            placeholder?: string | null;
            /** Product Id */
            product_id: string;
            /** Row Id */
            row_id?: string | null;
            /**
             * Status
             * @default open
             * @enum {string}
             */
            status: "open" | "answered" | "deferred";
            /** Title */
            title: string;
            /** Unit */
            unit?: string | null;
        };
        /** VersionItem */
        VersionItem: {
            /** Created At */
            created_at: string;
            /** Reason */
            reason: string;
            /** Version */
            version: number;
        };
        /** VersionList */
        VersionList: {
            /** Items */
            items: components["schemas"]["VersionItem"][];
        };
        /** Warning */
        Warning: {
            /** Body */
            body: string;
            decision?: components["schemas"]["WarningDecision"] | null;
            /** Default Option */
            default_option?: string | null;
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "discontinued" | "not_in_catalog" | "value_mismatch_source" | "value_mismatch_proposal" | "requirement_unmet" | "catalog_changed";
            /** Link Id */
            link_id?: string | null;
            /** N */
            n: number;
            /** Options */
            options?: components["schemas"]["WarningOption"][];
            /** Product Id */
            product_id?: string | null;
            replacement?: components["schemas"]["Replacement"] | null;
            /** Row Id */
            row_id?: string | null;
            /**
             * Status
             * @default open
             * @enum {string}
             */
            status: "open" | "decided" | "applied" | "dismissed";
            /** Tag */
            tag: string;
            /** Title */
            title: string;
        };
        /** WarningCounts */
        WarningCounts: {
            /**
             * All
             * @default 0
             */
            all: number;
            /**
             * Discontinued
             * @default 0
             */
            discontinued: number;
            /**
             * Mismatch
             * @default 0
             */
            mismatch: number;
            /**
             * Unmet
             * @default 0
             */
            unmet: number;
        };
        /** WarningDecision */
        WarningDecision: {
            /** At */
            at: string;
            /** Option Key */
            option_key: string;
        };
        /** WarningOption */
        WarningOption: {
            /** Key */
            key: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "radio" | "chip" | "button";
            /** Label */
            label: string;
            /** Navigates To */
            navigates_to?: ("SP1C" | "SP4" | "SP1R") | null;
        };
        /** WarningPatch */
        WarningPatch: {
            /** Option Key */
            option_key: string;
        };
        /** Warnings */
        Warnings: {
            counts?: components["schemas"]["WarningCounts"];
            /** Items */
            items?: components["schemas"]["Warning"][];
            /**
             * Open
             * @default 0
             */
            open: number;
        };
        /** WarningsView */
        WarningsView: {
            /** Agent Text */
            agent_text: string;
            counts: components["schemas"]["WarningCounts"];
            /** Decided */
            decided: number;
            /** Footer */
            footer: string;
            /** Items */
            items: components["schemas"]["Warning"][];
            /** Table Title */
            table_title: string;
            /** Total */
            total: number;
            /** User Text */
            user_text?: string | null;
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
    recheck_all: {
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
    catalog_status: {
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
                    "application/json": components["schemas"]["CatalogStatus"];
                };
            };
        };
    };
    list_combos: {
        parameters: {
            query?: {
                category?: string;
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
                    "application/json": components["schemas"]["ComboList"];
                };
            };
        };
    };
    get_handoff: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                handoff_id: string;
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
                    "application/json": components["schemas"]["Handoff"];
                };
            };
        };
    };
    ack_handoff: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                handoff_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["HandoffAck"];
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
    item_catalog: {
        parameters: {
            query?: {
                category?: string;
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
                    "application/json": components["schemas"]["ItemCatalog"];
                };
            };
        };
    };
    list_lifecycle: {
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
                    "application/json": components["schemas"]["LifecycleList"];
                };
            };
        };
    };
    lifecycle_check: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LifecycleCheckBody"];
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
                    "application/json": components["schemas"]["LifecycleCheckResult"];
                };
            };
        };
    };
    put_lifecycle: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                model_key: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LifecycleEntry"];
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
                    "application/json": components["schemas"]["LifecycleEntry"];
                };
            };
        };
    };
    list_links: {
        parameters: {
            query?: {
                proposal_id?: string | null;
                sheet_id?: string | null;
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
                    "application/json": components["schemas"]["LinkList"];
                };
            };
        };
    };
    release_links: {
        parameters: {
            query: {
                proposal_id: string;
                sheet_id?: string | null;
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
                    "application/json": components["schemas"]["LinksReleased"];
                };
            };
        };
    };
    get_preferences: {
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
                    "application/json": components["schemas"]["Preferences"];
                };
            };
        };
    };
    put_preferences: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FormatSettingsPatch"];
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
                    "application/json": components["schemas"]["Preferences"];
                };
            };
        };
    };
    list_sheets: {
        parameters: {
            query?: {
                archived?: boolean;
                cursor?: string | null;
                limit?: number;
                linked?: boolean;
                q?: string | null;
                since_days?: number;
                sort?: "updated_desc" | "title" | "status";
                tab?: "all" | "draft" | "check" | "done";
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
                    "application/json": components["schemas"]["SheetList"];
                };
            };
        };
    };
    create_sheet: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateSheet"];
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
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
        };
    };
    get_sheet: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
        };
    };
    patch_sheet: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchSheet"];
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
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
        };
    };
    archive_sheet: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
    clone_sheet: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["CloneBody"] | null;
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
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
        };
    };
    save_sheet: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
        };
    };
    unarchive_sheet: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
    patch_cell: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_id: string;
                row_id: string;
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CellPatch"];
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
                    "application/json": components["schemas"]["CellPatchResult"];
                };
            };
        };
    };
    cell_sources: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_id: string;
                row_id: string;
                sheet_id: string;
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
    list_checks: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
                    "application/json": components["schemas"]["CheckList"];
                };
            };
        };
    };
    apply_checks: {
        parameters: {
            query?: never;
            header?: {
                "if-match"?: string | null;
            };
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChecksApply"];
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
                    "application/json": components["schemas"]["ChecksApplyResult"];
                };
            };
        };
    };
    defer_all_checks: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
                    "application/json": components["schemas"]["ChecksApplyResult"];
                };
            };
        };
    };
    answer_check: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                check_id: string;
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CheckAnswerBody"];
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
                    "application/json": components["schemas"]["ValueCheck"];
                };
            };
        };
    };
    get_compliance: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
                    "application/json": components["schemas"]["Compliance"];
                };
            };
        };
    };
    patch_compliance: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CompliancePatch"];
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
                    "application/json": components["schemas"]["Compliance"];
                };
            };
            /** @description 대응 모델이 바뀌어 다시 판정 중 */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Compliance"];
                };
            };
        };
    };
    compliance_to_items: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
        };
    };
    ask_draft: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
                    "application/json": components["schemas"]["AskDraft"];
                };
            };
        };
    };
    patch_compliance_row: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                row_id: string;
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ComplianceRowPatch"];
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
                    "application/json": components["schemas"]["ComplianceRow"];
                };
            };
        };
    };
    add_datasheet: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DatasheetBody"];
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
    diff_items: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
                    "application/json": components["schemas"]["DiffItems"];
                };
            };
        };
    };
    create_session: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EditSessionCreated"];
                };
            };
        };
    };
    get_session: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
                sheet_id: string;
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
                    "application/json": components["schemas"]["EditView"];
                };
            };
        };
    };
    discard: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
                sheet_id: string;
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
    commit: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["CommitBody"] | null;
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
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
        };
    };
    redo: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
                sheet_id: string;
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
                    "application/json": components["schemas"]["EditView"];
                };
            };
        };
    };
    reset: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
                sheet_id: string;
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
                    "application/json": components["schemas"]["EditView"];
                };
            };
        };
    };
    undo: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
                sheet_id: string;
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
                    "application/json": components["schemas"]["EditView"];
                };
            };
        };
    };
    edit_message: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EditMessage"];
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
    add_ops: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EditOps"];
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
                    "application/json": components["schemas"]["EditView"];
                };
            };
        };
    };
    create_export: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ExportBody"];
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
                    "application/json": components["schemas"]["ExportAccepted"];
                };
            };
        };
    };
    get_export: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                export_id: string;
                sheet_id: string;
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
                    "application/json": components["schemas"]["ExportRecord"];
                };
            };
        };
    };
    put_finder: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FinderPut"];
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
                    "application/json": components["schemas"]["FinderState"];
                };
            };
        };
    };
    commit_finder: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FinderCommit"];
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
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
        };
    };
    parse_finder: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FinderParse"];
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
    put_format: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FormatSettings"];
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
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
        };
    };
    format_preview: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FormatPreviewBody"];
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
                    "application/json": components["schemas"]["FormatPreview"];
                };
            };
        };
    };
    generate_sheet: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["GenerateBody"] | null;
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
    create_handoff: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["HandoffBody"];
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
                    "application/json": components["schemas"]["HandoffCreated"];
                };
            };
        };
    };
    put_items: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ItemsPut"];
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
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
        };
    };
    post_message: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MessageBody"];
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
            /** @description 생성 중 — 조종 메모로 들어감 */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MessageQueued"];
                };
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MessageQueued"];
                };
            };
        };
    };
    get_package: {
        parameters: {
            query?: {
                locale?: string | null;
                /** @description 쉼표로 — SC-A,SD-B */
                templates?: string | null;
            };
            header?: never;
            path: {
                sheet_id: string;
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
                    "application/json": components["schemas"]["Package"];
                };
            };
        };
    };
    list_products: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
                    "application/json": components["schemas"]["ProductRefList"];
                };
            };
        };
    };
    add_products: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AddProducts"];
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
                    "application/json": components["schemas"]["AddProductsResult"];
                };
            };
        };
    };
    remove_product: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_id: string;
                sheet_id: string;
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
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
        };
    };
    patch_product: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_id: string;
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchProduct"];
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
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
        };
    };
    proposal_handoff: {
        parameters: {
            query?: {
                section?: string;
                type?: string;
            };
            header?: never;
            path: {
                sheet_id: string;
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
    recheck: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
    add_requirement_doc: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RequirementDocBody"];
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
    requirement_page: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                doc_id: string;
                n: number;
                sheet_id: string;
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
                    "application/json": components["schemas"]["PageView"];
                };
            };
        };
    };
    share_sheet: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
                    "application/json": components["schemas"]["ShareResult"];
                };
            };
        };
    };
    add_template: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TemplateBody"];
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
    remove_template: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
                template_id: string;
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
    list_versions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
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
                n: number;
                sheet_id: string;
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
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
        };
    };
    list_warnings: {
        parameters: {
            query?: {
                /** @description open = 열린(결정 포함) 경고 */
                status?: string;
            };
            header?: never;
            path: {
                sheet_id: string;
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
                    "application/json": components["schemas"]["WarningsView"];
                };
            };
        };
    };
    apply_warnings: {
        parameters: {
            query?: never;
            header?: {
                "if-match"?: string | null;
            };
            path: {
                sheet_id: string;
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
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
            /** @description 대체 모델로 바꾼 열을 다시 채우는 중(active_job) */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SheetDoc"];
                };
            };
        };
    };
    decide_warning: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sheet_id: string;
                warning_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WarningPatch"];
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
                    "application/json": components["schemas"]["Warning"];
                };
            };
        };
    };
}
