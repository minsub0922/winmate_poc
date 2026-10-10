// 자동 생성 — 직접 고치지 말 것. 원본: contracts/competitor.json (make contracts)
export interface paths {
    "/v1/analyses": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Analyses */
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
         * Add Refs
         * @description TopBar `현재 작업에 추가` — 제품 · 솔루션 = 비교 `삼성` 쪽 제품, 사례 = 사내 사례 DB 근거. 다음 실행에서 판정부터 다시. image 는 받지 않는다.
         */
        post: operations["add_refs"];
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
         * @description 넘김 묶음 — mi 는 실명 포함(MI 가 자기 내보내기에서 익명 처리), proposal_why · storyboard 는 익명(기록에 실명 확인이 있을 때만 실명).
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
    "/v1/analyses/{aid}/candidates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Candidates */
        get: operations["get_candidates"];
        put?: never;
        /**
         * Add Candidate
         * @description 경쟁사 직접 추가 → 켜짐 · 고정 · 다음 글자 · 배지 `직접 추가`. 같은 회사(별칭 포함)면 409 DUPLICATE_COMPETITOR.
         */
        post: operations["add_candidate"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/candidates/{cmp}": {
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
         * Patch Candidate
         * @description 켜기 · 끄기 → pinned=true(다시 찾기 · 다시 분석해도 유지).
         */
        patch: operations["patch_candidate"];
        trace?: never;
    };
    "/v1/analyses/{aid}/changes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Changes */
        get: operations["changes"];
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
         * Remove Source
         * @description 이 출처 빼기 → 주장 상태 다시(마지막 출처를 빼면 그 사실은 `[확인 필요]`).
         */
        delete: operations["remove_source"];
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
        /** Get Competitor */
        get: operations["get_competitor"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/competitors/{cmp}/research": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Research
         * @description 이 경쟁사 더 찾기(ca.research) — 그 경쟁사 사실만 다시 모으고 판정 · 강점 · 주의할 점 다시 → 새 버전.
         */
        post: operations["research"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
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
         * @description 기준 바꾸기(CA3C) — 모두 pinned, 모드 `고정`. 분석 중이면 202(사실 재사용 · 판정부터), 아니면 200(웹이 runs{rejudge}).
         */
        put: operations["put_criteria"];
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
         * @description 리포트 저장(ca.export) — `internal` = 실명 · 표지 `사내용 · 고객 제출 금지`, `customer` = 익명. 끝나면 result.file_id.
         */
        post: operations["create_export"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/analyses/{aid}/find": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start Find
         * @description ca.find — 이미 돌고 있으면 취소 후 새로. 사용자가 켜고 끈 · 추가한 후보는 그대로 두고 나머지만 다시 찾는다.
         */
        post: operations["start_find"];
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
        /** List Handoffs */
        get: operations["list_handoffs"];
        put?: never;
        /**
         * Create Handoff
         * @description 넘김 기록. 고객 제출물(제안서)인데 익명이 꺼져 있고 실명 확인이 없으면 409 ASK_REQUIRED(묻기 2).
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
    "/v1/analyses/{aid}/progress": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Progress
         * @description CA1G · CA3 를 다시 열었을 때 그릴 진행 상태(잡 SSE 와 같은 내용).
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
         * @description ProposalHandoff v1(§6.11 · 10-proposal §8.8 C1) — Why Samsung 경쟁 비교(CM) · 삼성 강점(ST). 기본 익명.
         *     named=true 는 넘김 기록에 실명 확인(CA5 묻기 2 `실명으로 보내기`)이 있을 때만 — 없으면 409 ASK_REQUIRED, 있으면 응답마다 served_named_at 기록.
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
        /** Get Result */
        get: operations["get_result"];
        put?: never;
        post?: never;
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
         * Start Run
         * @description ca.analyze — full · changed_only · rejudge · resume. 실행 중 409 RUN_IN_PROGRESS · 켜진 경쟁사 0 → 422 NO_COMPETITORS.
         */
        post: operations["start_run"];
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
        /** List Sources */
        get: operations["list_sources"];
        put?: never;
        /**
         * Add Source
         * @description 출처 직접 추가 · URL 또는 사내 문서(ca.source_add) → 수집 · 대조 후 카드로 나타난다.
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
        /** Source Snapshot */
        get: operations["source_snapshot"];
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
        /** Restore Version */
        post: operations["restore_version"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/ca-flows": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Ca Flows
         * @description 경쟁사 분석(새 흐름) 목록 — 보드 List 의 작성 중 초안.
         */
        get: operations["list_ca_flows"];
        put?: never;
        /**
         * Create Ca Flow
         * @description 새 경쟁사 분석 — Storyboard 의 DSS 로 비교 기준을 채운다. 없는 Storyboard 404 · DSS 전이면 422 PREREQUISITE_MISSING.
         */
        post: operations["create_ca_flow"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/ca-flows/{flow_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Ca Flow */
        get: operations["get_ca_flow"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Patch Ca Flow
         * @description 제목 고치기(expected_version 이 다르면 409).
         */
        patch: operations["patch_ca_flow"];
        trace?: never;
    };
    "/v1/ca-flows/{flow_id}:candidates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Suggest Candidates
         * @description AI 경쟁사 후보군 웹 탐색 — 웹 검색 요약에 이름 · 근거 구절이 있는 후보만 점선(ai-pending)으로. 웹 · 모델이 안 되면 mode=none · 후보 0.
         */
        post: operations["suggest_candidates"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/ca-flows/{flow_id}:finish": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Finish
         * @description 저장 — status=done, Storyboard flow.json stages.ca · 요약 md · 팝업 카드 반영(push_stage). 경쟁사 0이면 422 NO_COMPETITORS.
         */
        post: operations["finish"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/ca-flows/{flow_id}/competitors": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Competitor
         * @description 경쟁사 직접 추가 — 웹 검색 요약에서 기본 정보(위키)를 불러오고, 겹치는 제품군의 DSS 제품으로 비교 쌍을 만든다. 근거 없는 값은 자리표시.
         */
        post: operations["add_competitor"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/ca-flows/{flow_id}/competitors/{cid}": {
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
         * Delete Competitor
         * @description 경쟁사 빼기(AI 후보 빼기도 이것).
         */
        delete: operations["delete_competitor"];
        options?: never;
        head?: never;
        /**
         * Patch Competitor
         * @description 경쟁사 고치기 — 기본 정보 · 선별 기준 · 장단점 · 주장, AI 후보 목록에 추가(accept).
         */
        patch: operations["patch_competitor"];
        trace?: never;
    };
    "/v1/ca-flows/{flow_id}/competitors/{cid}/matches": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Match
         * @description 비교 쌍 추가 — 우리 제품은 DSS 제품 · 솔루션(아니면 422 NOT_IN_DSS), 판정은 자료 없음으로 시작.
         */
        post: operations["add_match"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/ca-flows/{flow_id}/competitors/{cid}/matches/{mid}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Match */
        delete: operations["delete_match"];
        options?: never;
        head?: never;
        /**
         * Patch Match
         * @description 비교 쌍 고치기 — 공간 · 경쟁 제품 · 축별 판정(ours-better · similar · ours-worse · no-data)과 메모.
         */
        patch: operations["patch_match"];
        trace?: never;
    };
    "/v1/ca-flows/{flow_id}/stage": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Stage */
        get: operations["get_stage"];
        put?: never;
        post?: never;
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
        /**
         * Capabilities
         * @description 웹 검색 모드(sources · summary_only) — 화면이 `원문 열기` 같은 표시를 정할 때.
         */
        get: operations["capabilities"];
        put?: never;
        post?: never;
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
    "/v1/parse": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Parse
         * @description CA1 · CA1R 칩 — 네 칸 읽기(≤ 3초 목표, 넘으면 KB 만으로).
         */
        post: operations["parse"];
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
         * @description CAR 보드 원문 + 규칙 임계값(서버 판단과 같은 설정 파일).
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
        /** Analysis */
        Analysis: {
            /**
             * Added Refs
             * @description 셸 `현재 작업에 추가`로 넣은 참조(kb:model:… · kb:solution:… · kb:case:…) — 셸 `added`
             */
            added_refs?: string[];
            /** Analyzed At */
            analyzed_at?: string | null;
            /**
             * Analyzed Count
             * @default 0
             */
            analyzed_count: number;
            /**
             * Anonymize
             * @default true
             */
            anonymize: boolean;
            ask?: components["schemas"]["AskRequest"] | null;
            /** Chips */
            chips?: components["schemas"]["ChipView"][];
            /**
             * Competitor Count
             * @default 0
             */
            competitor_count: number;
            /**
             * Created At
             * @default
             */
            created_at: string;
            /**
             * Criteria Mode
             * @default auto
             * @enum {string}
             */
            criteria_mode: "auto" | "pin";
            /** Current Job Id */
            current_job_id?: string | null;
            /** Current Job Kind */
            current_job_kind?: string | null;
            /** Customer Name */
            customer_name?: string | null;
            /** Exclude Names */
            exclude_names?: string[];
            /**
             * Extra Text
             * @default
             */
            extra_text: string;
            /** File Ids */
            file_ids?: string[];
            find?: components["schemas"]["FindProgress"];
            /**
             * Found Count
             * @default 0
             */
            found_count: number;
            /** Id */
            id: string;
            /** Include Names */
            include_names?: string[];
            /**
             * Input Label
             * @default
             */
            input_label: string;
            /**
             * Input Mode
             * @default free
             * @enum {string}
             */
            input_mode: "free" | "requirements" | "mi";
            /** Last Screen */
            last_screen?: string | null;
            /**
             * Letters On
             * @description 켜진 경쟁사 글자(CA5 익명 표기 `경쟁사 A · B · C · D`)
             */
            letters_on?: string[];
            mi_ref?: components["schemas"]["MiRef"] | null;
            /**
             * Naming Mode
             * @default letter
             */
            naming_mode: string;
            /**
             * Needs Rejudge
             * @default false
             */
            needs_rejudge: boolean;
            /** Next Recheck At */
            next_recheck_at?: string | null;
            /**
             * On Count
             * @default 0
             */
            on_count: number;
            /**
             * Owner Name
             * @default
             */
            owner_name: string;
            /** Project Id */
            project_id?: string | null;
            /** Purpose */
            purpose?: string | null;
            /** Requirements Id */
            requirements_id?: string | null;
            rfp?: components["schemas"]["RfpView"];
            /**
             * Route
             * @default
             */
            route: string;
            /** Rq Version */
            rq_version?: number | null;
            run?: components["schemas"]["RunProgress"] | null;
            segment?: components["schemas"]["SegmentView"];
            slots: components["schemas"]["SlotsView"];
            /**
             * Status
             * @default draft
             * @enum {string}
             */
            status: "draft" | "finding" | "ask" | "confirming" | "analyzing" | "stopped" | "done" | "upd" | "failed";
            /**
             * Status Label
             * @default
             */
            status_label: string;
            stopped?: components["schemas"]["StoppedInfo"] | null;
            /**
             * Text
             * @default
             */
            text: string;
            /**
             * Title
             * @default
             */
            title: string;
            /**
             * Updated At
             * @default
             */
            updated_at: string;
            /**
             * Version
             * @default 0
             */
            version: number;
        };
        /** AnalysisCreate */
        AnalysisCreate: {
            /**
             * Auto Run
             * @default false
             */
            auto_run: boolean;
            /**
             * Customer
             * @description 제안서 딸깍 호환: 고객사 이름 또는 {name}
             */
            customer?: unknown;
            /** Customer Name */
            customer_name?: string | null;
            /** Extra Text */
            extra_text?: string | null;
            /** File Ids */
            file_ids?: string[];
            /**
             * Input Mode
             * @default free
             * @enum {string}
             */
            input_mode: "free" | "requirements" | "mi";
            /**
             * Mi Bundle
             * @description MI `bundle?target=competitor` 응답(웹이 읽어 넣음)
             */
            mi_bundle?: {
                [key: string]: unknown;
            } | null;
            mi_ref?: components["schemas"]["MiRef"] | null;
            /** Project Id */
            project_id?: string | null;
            /**
             * Purpose
             * @description proposal(제안서 딸깍)
             */
            purpose?: string | null;
            /** Requirements Id */
            requirements_id?: string | null;
            /** @description 제안서 딸깍(10-proposal §8.8 C2) 호환 — requirements_id 와 같음 */
            rq_ref?: components["schemas"]["RqRef"] | null;
            /** Rq Version */
            rq_version?: number | null;
            /** Text */
            text?: string | null;
        };
        /** AnalysisList */
        AnalysisList: {
            banner?: components["schemas"]["ListBanner"] | null;
            counts: components["schemas"]["ListCounts"];
            /**
             * Header
             * @default
             */
            header: string;
            /** Items */
            items: components["schemas"]["ListItem"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** AnalysisPatch */
        AnalysisPatch: {
            /** Anonymize */
            anonymize?: boolean | null;
            /** Extra Text */
            extra_text?: string | null;
            /** File Ids */
            file_ids?: string[] | null;
            /** Input Mode */
            input_mode?: ("free" | "requirements" | "mi") | null;
            /** Last Screen */
            last_screen?: string | null;
            /** Requirements Id */
            requirements_id?: string | null;
            /** Rq Version */
            rq_version?: number | null;
            /** Text */
            text?: string | null;
            /** Title */
            title?: string | null;
        };
        /** AskRead */
        AskRead: {
            /** Key */
            key: string;
            /** Label */
            label: string;
            /**
             * Partial
             * @default false
             */
            partial: boolean;
            /** Value */
            value: string;
        };
        /** AskRequest */
        AskRequest: {
            /** Default */
            default?: {
                [key: string]: unknown;
            };
            /**
             * Desc
             * @default
             */
            desc: string;
            /** Industry */
            industry?: {
                [key: string]: unknown;
            };
            /**
             * Kind
             * @default slots
             */
            kind: string;
            /** Missing */
            missing?: string[];
            /** Read */
            read?: components["schemas"]["AskRead"][];
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** AskRow */
        AskRow: {
            /**
             * Default
             * @default
             */
            default: string;
            /** N */
            n: number;
            /** T */
            t: string;
            /** Where */
            where: string;
        };
        /**
         * Bundle
         * @description 넘김 묶음(§6.10). target 마다 채우는 필드가 다르다 — mi(실명 포함) · proposal_why(익명) · storyboard(익명).
         */
        Bundle: {
            /** Analysis Id */
            analysis_id: string;
            /** Cautions */
            cautions?: {
                [key: string]: unknown;
            }[] | null;
            /** Citations */
            citations?: {
                [key: string]: unknown;
            }[] | null;
            /** Claims */
            claims?: {
                [key: string]: unknown;
            }[] | null;
            /** Comparison */
            comparison?: {
                [key: string]: unknown;
            } | null;
            /** Competitors */
            competitors?: unknown[];
            /** Criteria */
            criteria?: {
                [key: string]: unknown;
            }[];
            /** Customer */
            customer?: {
                [key: string]: unknown;
            } | null;
            /** Fact Check */
            fact_check?: {
                [key: string]: unknown;
            }[] | null;
            /** Facts */
            facts?: {
                [key: string]: unknown;
            } | null;
            /** Footnotes */
            footnotes?: {
                [key: string]: unknown;
            }[] | null;
            /** Handoff Id */
            handoff_id?: string | null;
            /**
             * Named
             * @default false
             */
            named: boolean;
            /** Note */
            note?: string | null;
            /** Positioning */
            positioning?: {
                [key: string]: unknown;
            } | null;
            /** Samsung Cells */
            samsung_cells?: {
                [key: string]: unknown;
            } | null;
            /** Segment */
            segment?: {
                [key: string]: unknown;
            } | null;
            /** Slots */
            slots?: {
                [key: string]: unknown;
            } | null;
            /** Sources */
            sources?: {
                [key: string]: unknown;
            }[] | null;
            /** Strengths */
            strengths?: {
                [key: string]: unknown;
            }[] | null;
            /** Target */
            target: string;
            /**
             * Title
             * @default
             */
            title: string;
            /** Verdicts */
            verdicts?: {
                [key: string]: unknown;
            }[] | null;
            /**
             * Version
             * @default 0
             */
            version: number;
        };
        /** CandidateAdd */
        CandidateAdd: {
            /** Name */
            name: string;
        };
        /** CandidateAddOut */
        CandidateAddOut: {
            /** Competitor Id */
            competitor_id: string;
            /** Job Id */
            job_id: string;
            /**
             * Status
             * @default queued
             */
            status: string;
        };
        /** CandidateCounts */
        CandidateCounts: {
            /**
             * Check
             * @default 0
             */
            check: number;
            /**
             * Drop
             * @default 0
             */
            drop: number;
            /**
             * On
             * @default 0
             */
            on: number;
            /**
             * Rec
             * @default 0
             */
            rec: number;
            /**
             * User
             * @default 0
             */
            user: number;
        };
        /** CandidatePatch */
        CandidatePatch: {
            /** On */
            on: boolean;
        };
        /** CandidatesOut */
        CandidatesOut: {
            /** Chips */
            chips?: components["schemas"]["ChipView"][];
            counts: components["schemas"]["CandidateCounts"];
            /**
             * Finding
             * @default false
             */
            finding: boolean;
            header?: components["schemas"]["HeaderView"];
            /** Items */
            items: components["schemas"]["CompetitorView"][];
            /** Job Id */
            job_id?: string | null;
            /**
             * Page Size
             * @default 6
             */
            page_size: number;
            /**
             * Read Count
             * @default 0
             */
            read_count: number;
            slots?: components["schemas"]["SlotsView"] | null;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** Capabilities */
        Capabilities: {
            /**
             * Fetch
             * @default false
             */
            fetch: boolean;
            /**
             * Mode
             * @default summary_only
             */
            mode: string;
            /**
             * Returns Sources
             * @default false
             */
            returns_sources: boolean;
            /**
             * Search Api
             * @default none
             */
            search_api: string;
            /**
             * Websearch Available
             * @default true
             */
            websearch_available: boolean;
        };
        /** CautionView */
        CautionView: {
            /** Claim Ids */
            claim_ids?: string[];
            /** Competitor Id */
            competitor_id: string;
            /** Criterion Ids */
            criterion_ids?: string[];
            /** Criterion Names */
            criterion_names?: string[];
            /** Display */
            display: string;
            /** Letter */
            letter: string;
            /** Note */
            note: string;
            /**
             * Sources Label
             * @default
             */
            sources_label: string;
        };
        /** CFBasis */
        CFBasis: {
            /** Categories */
            categories: string[];
            /**
             * Counts
             * @description 제품군마다 DSS 제품 · 솔루션 수
             */
            counts?: {
                [key: string]: number;
            };
            /**
             * From
             * @description DSS 참조(DSS-01)
             */
            from?: string | null;
        };
        /** CFCandidatesResult */
        CFCandidatesResult: {
            /** Added */
            added: number;
            flow: components["schemas"]["CFDoc"];
            /**
             * Mode
             * @description web = 웹 검색 요약에서 후보를 찾음 · none = 웹 · 모델이 안 돼 찾지 못함
             * @enum {string}
             */
            mode: "web" | "none";
            /** Reason */
            reason?: string | null;
        };
        /** CFClaim */
        CFClaim: {
            /**
             * Axis
             * @description 주장 축(통합 · 사례 · 가격 · ESG · 브랜드 …)
             */
            axis: string;
            /**
             * Supports
             * @description 연결 요구(예: RQ-01)
             */
            supports?: string | null;
            /** Text */
            text: string;
        };
        /** CFCompetitor */
        CFCompetitor: {
            /**
             * By
             * @enum {string}
             */
            by: "manual" | "ai-pending" | "ai-web";
            candidateEvidence?: components["schemas"]["CFEvidence"] | null;
            /**
             * Categories
             * @description 겹치는 비교 기준 제품군
             */
            categories?: string[];
            /**
             * Claims
             * @description 그래서 우리가 주장할 것
             */
            claims?: components["schemas"]["CFClaim"][];
            /**
             * Cons
             * @description 경쟁사 단점 · 삼성 대비
             */
            cons?: string[];
            /** Criteria */
            criteria?: components["schemas"]["CFCriterion"][];
            /**
             * Id
             * @description 목록 글자(A · B · C …)
             */
            id: string;
            /**
             * Industry
             * @description 목록 한 줄 — 업종
             * @default [확인 필요]
             */
            industry: string;
            /** Matches */
            matches?: components["schemas"]["CFMatch"][];
            /** Name */
            name: string;
            /**
             * Pros
             * @description 경쟁사 장점 · 삼성 대비
             */
            pros?: string[];
            /**
             * Size
             * @description 목록 한 줄 — 규모
             * @default [확인 필요]
             */
            size: string;
            /**
             * Spaces
             * @description 겹치는 DSS 공간
             */
            spaces?: string[];
            /**
             * Why
             * @description 목록 둘째 줄 — 겹침 · 공간
             * @default
             */
            why: string;
            wiki: components["schemas"]["CFWiki"];
        };
        /** CFCompetitorAdd */
        CFCompetitorAdd: {
            /** Expected Version */
            expected_version?: number | null;
            /**
             * Lookup
             * @description 웹 검색으로 기본 정보(위키)를 불러온다
             * @default true
             */
            lookup: boolean;
            /** Name */
            name: string;
        };
        /** CFCompetitorPatch */
        CFCompetitorPatch: {
            /**
             * Accept
             * @description AI 후보를 목록에 추가(ai-pending → ai-web)
             */
            accept?: boolean | null;
            /** Claims */
            claims?: components["schemas"]["CFClaim"][] | null;
            /** Cons */
            cons?: string[] | null;
            /** Criteria */
            criteria?: components["schemas"]["CFCriterion"][] | null;
            /** Expected Version */
            expected_version?: number | null;
            /** Name */
            name?: string | null;
            /** Pros */
            pros?: string[] | null;
            wiki?: components["schemas"]["CFWikiPatch"] | null;
        };
        /** CFCounts */
        CFCounts: {
            /** Candidates */
            candidates: number;
            /** Competitors */
            competitors: number;
            /** Matches */
            matches: number;
            verdicts: components["schemas"]["CFVerdictCounts"];
        };
        /** CFCreate */
        CFCreate: {
            /**
             * Sb Id
             * @description 사전 작업 DSS 가 된 Storyboard
             */
            sb_id: string;
            /** Title */
            title?: string | null;
        };
        /** CFCriterion */
        CFCriterion: {
            /** K */
            k: string;
            /**
             * Status
             * @default ok
             * @enum {string}
             */
            status: "ok" | "check";
            /** V */
            v: string;
        };
        /** CFDim */
        CFDim: {
            /**
             * Note
             * @default 자료 없음
             */
            note: string;
            /**
             * Verdict
             * @default no-data
             * @enum {string}
             */
            verdict: "ours-better" | "similar" | "ours-worse" | "no-data";
        };
        /** CFDimPatch */
        CFDimPatch: {
            /** Note */
            note?: string | null;
            /** Verdict */
            verdict?: ("ours-better" | "similar" | "ours-worse" | "no-data") | null;
        };
        /** CFDims */
        CFDims: {
            brand?: components["schemas"]["CFDim"];
            cases?: components["schemas"]["CFDim"];
            esg?: components["schemas"]["CFDim"];
            price?: components["schemas"]["CFDim"];
            spec?: components["schemas"]["CFDim"];
        };
        /** CFDoc */
        CFDoc: {
            basis: components["schemas"]["CFBasis"];
            /**
             * Code
             * @description CA-01 …
             */
            code?: string | null;
            /** Competitors */
            competitors?: components["schemas"]["CFCompetitor"][];
            counts: components["schemas"]["CFCounts"];
            /** Created At */
            created_at: string;
            /** Customer */
            customer?: string | null;
            /**
             * Dss Items
             * @description 비교 쌍에 고를 수 있는 DSS 제품 · 솔루션
             */
            dss_items?: components["schemas"]["CFDssItem"][];
            /** Id */
            id: string;
            /** Sb Id */
            sb_id?: string | null;
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
             * @description 저장(완료) 판 — flow.json stages.ca.ver
             */
            ver?: number | null;
            /** Version */
            version: number;
        };
        /** CFDssItem */
        CFDssItem: {
            /** Category */
            category: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "product" | "solution";
            /** Name */
            name: string;
            /** Ref */
            ref?: string | null;
            /** Spaces */
            spaces?: string[];
        };
        /** CFEvidence */
        CFEvidence: {
            /** Date */
            date?: string | null;
            /**
             * Quote
             * @description 웹 검색 요약 원문 구절
             */
            quote: string;
            /**
             * Source
             * @description 근거 출처 이름(업계 뉴스 · 회사 소개 페이지 · 조달 공고 …)
             */
            source: string;
            /** Url */
            url?: string | null;
        };
        /** CFFlowSync */
        CFFlowSync: {
            /** Md Added */
            md_added: string;
            /** Synced */
            synced?: string[];
        };
        /** CFList */
        CFList: {
            /** Items */
            items: components["schemas"]["CFListItem"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** CFListItem */
        CFListItem: {
            /** Code */
            code?: string | null;
            counts: components["schemas"]["CFCounts"];
            /** Id */
            id: string;
            /** Sb Id */
            sb_id?: string | null;
            /** Status */
            status: string;
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
        };
        /** CFMatch */
        CFMatch: {
            dims: components["schemas"]["CFDims"];
            /** Id */
            id: string;
            /**
             * Ours
             * @description 우리 제품 · 솔루션(DSS)
             */
            ours: string;
            /** Ours Ref */
            ours_ref?: string | null;
            /**
             * Space
             * @description DSS 공간(또는 쓰임 — 로비 미디어월)
             */
            space: string;
            /**
             * Theirs
             * @description 경쟁 제품 한 줄
             */
            theirs: string;
        };
        /** CFMatchAdd */
        CFMatchAdd: {
            /** Expected Version */
            expected_version?: number | null;
            /**
             * Ours
             * @description 우리 제품 · 솔루션(DSS 이름)
             */
            ours: string;
            /** Space */
            space?: string | null;
            /**
             * Theirs
             * @default [확인 필요]
             */
            theirs: string;
        };
        /** CFMatchPatch */
        CFMatchPatch: {
            /** Dims */
            dims?: {
                [key: string]: components["schemas"]["CFDimPatch"];
            } | null;
            /** Expected Version */
            expected_version?: number | null;
            /** Space */
            space?: string | null;
            /** Theirs */
            theirs?: string | null;
        };
        /** CFPatch */
        CFPatch: {
            /** Expected Version */
            expected_version?: number | null;
            /** Title */
            title?: string | null;
        };
        /** CFSource */
        CFSource: {
            /** Title */
            title?: string | null;
            /**
             * Type
             * @description Wikipedia · 웹 검색 요약 · 직접 입력 …
             */
            type: string;
            /** Url */
            url?: string | null;
        };
        /** CFStageOut */
        CFStageOut: {
            flow_sync?: components["schemas"]["CFFlowSync"] | null;
            /**
             * Stage
             * @description Storyboard flow.json 의 stages.ca
             */
            stage: {
                [key: string]: unknown;
            };
            /** Summary Md */
            summary_md: string;
        };
        /** CFVerdictCounts */
        CFVerdictCounts: {
            /** Nodata */
            noData: number;
            /** Oursbetter */
            oursBetter: number;
            /** Oursworse */
            oursWorse: number;
            /** Similar */
            similar: number;
        };
        /** CFWiki */
        CFWiki: {
            /**
             * B2Boffice
             * @default [확인 필요]
             */
            b2bOffice: string;
            /**
             * Employees
             * @default [위키 값]
             */
            employees: string;
            /**
             * Hq
             * @default [확인 필요]
             */
            hq: string;
            /**
             * Industry
             * @default [확인 필요]
             */
            industry: string;
            /**
             * Mainbusiness
             * @default [확인 필요]
             */
            mainBusiness: string;
            /**
             * Revenue
             * @default [위키 값]
             */
            revenue: string;
            /**
             * Size
             * @default [확인 필요]
             */
            size: string;
            source: components["schemas"]["CFSource"];
        };
        /** CFWikiPatch */
        CFWikiPatch: {
            /** B2Boffice */
            b2bOffice?: string | null;
            /** Employees */
            employees?: string | null;
            /** Hq */
            hq?: string | null;
            /** Industry */
            industry?: string | null;
            /** Mainbusiness */
            mainBusiness?: string | null;
            /** Revenue */
            revenue?: string | null;
            /** Size */
            size?: string | null;
            /** Source Url */
            source_url?: string | null;
        };
        /** ChangesOut */
        ChangesOut: {
            /** Checked At */
            checked_at?: string | null;
            /** Items */
            items: components["schemas"]["ChangeView"][];
            /**
             * Summary
             * @default
             */
            summary: string;
        };
        /** ChangeView */
        ChangeView: {
            /** Competitor Id */
            competitor_id?: string | null;
            /** Date */
            date?: string | null;
            /**
             * Detected At
             * @default
             */
            detected_at: string;
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "competitor_new_product" | "source_changed";
            /** Letter */
            letter?: string | null;
            /** Product */
            product?: string | null;
            /**
             * Summary
             * @default
             */
            summary: string;
            /**
             * Title
             * @description `경쟁사 {글자} 신제품 발표` 처럼(실명 없음)
             */
            title: string;
            /**
             * Verification
             * @default needs_check
             * @enum {string}
             */
            verification: "matched" | "needs_check";
        };
        /** ChipView */
        ChipView: {
            /**
             * Key
             * @description industry_basis · region_missing · industry_inferred · place_inferred · industry_check · auto_confirmed · unknown_cells
             */
            key: string;
            /**
             * Label
             * @description `업종 기준` · `지역 미반영` · `업종 추정` · `장소 추정` · `업종 확인` · `후보 자동 확정` · `확인 필요 {n}`
             */
            label: string;
            /**
             * Mode
             * @default check
             * @enum {string}
             */
            mode: "auto" | "check" | "ask" | "pin";
        };
        /** CitationRef */
        CitationRef: {
            /** N */
            n: number;
            /** Source Id */
            source_id: string;
            /** Status */
            status: string;
        };
        /** ClaimCounts */
        ClaimCounts: {
            /**
             * Kb Case
             * @default 0
             */
            kb_case: number;
            /**
             * Matched
             * @default 0
             */
            matched: number;
            /**
             * Needs Check
             * @default 0
             */
            needs_check: number;
            /**
             * Public
             * @default 0
             */
            public: number;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** ClaimDetail */
        ClaimDetail: {
            /** Cards */
            cards: components["schemas"]["SourceCard"][];
            claim: components["schemas"]["ClaimItem"];
        };
        /** ClaimItem */
        ClaimItem: {
            /**
             * Block
             * @default
             */
            block: string;
            /** Citations */
            citations?: components["schemas"]["CitationRef"][];
            /** Competitor Id */
            competitor_id?: string | null;
            /** Criterion Id */
            criterion_id?: string | null;
            /** Fact Key */
            fact_key?: string | null;
            /** Id */
            id: string;
            /** Label */
            label: string;
            /** Status */
            status: string;
            /** Text */
            text: string;
        };
        /** ClaimList */
        ClaimList: {
            counts?: components["schemas"]["ClaimCounts"];
            /** Items */
            items: components["schemas"]["ClaimItem"][];
        };
        /** CompetitorDetail */
        CompetitorDetail: {
            /** Facts */
            facts: components["schemas"]["FactView"][];
            footer?: components["schemas"]["FooterView"];
            header: components["schemas"]["DetailHeader"];
            /** Others */
            others?: components["schemas"]["OtherCompetitor"][];
            /**
             * Positioning
             * @default
             */
            positioning: string;
            research?: components["schemas"]["ResearchState"];
            /**
             * State
             * @default done
             */
            state: string;
            /**
             * Version
             * @default 0
             */
            version: number;
            /**
             * Vs Labels
             * @description `우위 3 · 통합 관리 · 전력 · 배포` 칩(0 인 칩은 뺌)
             */
            vs_labels?: components["schemas"]["ChipView"][];
            vs_samsung?: components["schemas"]["VsSamsung"];
        };
        /** CompetitorView */
        CompetitorView: {
            /** Add State */
            add_state?: ("pending" | "done" | "failed") | null;
            /** Aliases */
            aliases?: string[];
            /** Chips */
            chips?: string[];
            /** Confidence */
            confidence?: number | null;
            /**
             * Confidence Label
             * @default
             */
            confidence_label: string;
            /**
             * Display
             * @description `경쟁사 {글자}`
             */
            display: string;
            /** Id */
            id: string;
            /**
             * Kind Label
             * @default
             */
            kind_label: string;
            /** Letter */
            letter: string;
            /** On */
            on: boolean;
            /**
             * Origin
             * @default auto
             */
            origin: string;
            /**
             * Pinned
             * @default false
             */
            pinned: boolean;
            /**
             * Rank
             * @default 0
             */
            rank: number;
            /**
             * Real Name
             * @description 실명(작업 화면 안에서만 보조 글자로)
             * @default
             */
            real_name: string;
            /**
             * Removed
             * @default false
             */
            removed: boolean;
            /**
             * Status
             * @enum {string}
             */
            status: "rec" | "check" | "drop" | "user";
            /** Status Label */
            status_label: string;
            /**
             * Switch Label
             * @description `경쟁사 {글자} 빼기` / `경쟁사 {글자} 넣기`
             * @default
             */
            switch_label: string;
            /**
             * Why
             * @default
             */
            why: string;
        };
        /** CriteriaOut */
        CriteriaOut: {
            /** Items */
            items: components["schemas"]["CriterionView"][];
            /**
             * Mode
             * @default auto
             * @enum {string}
             */
            mode: "auto" | "pin";
            /**
             * On
             * @default 0
             */
            on: number;
            /** Suggestions */
            suggestions?: components["schemas"]["Suggestion"][];
            summary: components["schemas"]["CriteriaSummary"];
            /**
             * Summary Text
             * @description `요구사항에서 3 · 업종 사례에서 1 · 기본 2`
             * @default
             */
            summary_text: string;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** CriteriaPut */
        CriteriaPut: {
            /** Items */
            items: components["schemas"]["CriterionIn"][];
        };
        /** CriteriaPutOut */
        CriteriaPutOut: {
            /** Items */
            items: components["schemas"]["CriterionView"][];
            /** Job Id */
            job_id?: string | null;
            /**
             * Mode
             * @default auto
             * @enum {string}
             */
            mode: "auto" | "pin";
            /**
             * On
             * @default 0
             */
            on: number;
            /** Suggestions */
            suggestions?: components["schemas"]["Suggestion"][];
            summary: components["schemas"]["CriteriaSummary"];
            /**
             * Summary Text
             * @description `요구사항에서 3 · 업종 사례에서 1 · 기본 2`
             * @default
             */
            summary_text: string;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** CriteriaSummary */
        CriteriaSummary: {
            /**
             * Default
             * @default 0
             */
            default: number;
            /**
             * Industry Cases
             * @default 0
             */
            industry_cases: number;
            /**
             * Requirements
             * @default 0
             */
            requirements: number;
            /**
             * Total
             * @default 0
             */
            total: number;
            /**
             * User
             * @default 0
             */
            user: number;
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
            /**
             * Importance
             * @default 3
             */
            importance: number;
            /** Name */
            name: string;
            /**
             * Order
             * @default 0
             */
            order: number;
            /**
             * Source
             * @default user
             * @enum {string}
             */
            source: "requirements" | "industry_cases" | "default" | "user";
            /** Source Count */
            source_count?: number | null;
        };
        /** CriterionView */
        CriterionView: {
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /** Id */
            id: string;
            /**
             * Importance
             * @default 3
             */
            importance: number;
            /** Name */
            name: string;
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
            /** Requirement Ref */
            requirement_ref?: string | null;
            /**
             * Source
             * @enum {string}
             */
            source: "requirements" | "industry_cases" | "default" | "user";
            /** Source Count */
            source_count?: number | null;
            /**
             * Source Label
             * @description `요구` · `업종 사례 {n}건` · `기본` · `직접 추가`
             * @default
             */
            source_label: string;
        };
        /** DetailHeader */
        DetailHeader: {
            /** Aliases */
            aliases?: string[];
            /** Display */
            display: string;
            /** Id */
            id: string;
            /**
             * Kind
             * @default
             */
            kind: string;
            /** Letter */
            letter: string;
            /**
             * Real Name
             * @default
             */
            real_name: string;
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
        /** ExportIn */
        ExportIn: {
            /**
             * Audience
             * @default internal
             * @enum {string}
             */
            audience: "internal" | "customer";
            /**
             * Format
             * @default pdf
             * @constant
             */
            format: "pdf";
        };
        /** FactView */
        FactView: {
            /**
             * Check
             * @description 칩 `확인 필요`(모르는 값 · 확인 안 된 값)
             * @default false
             */
            check: boolean;
            /** Claim Ids */
            claim_ids?: string[];
            /**
             * Has Kb
             * @default false
             */
            has_kb: boolean;
            /**
             * Key
             * @enum {string}
             */
            key: "lineup" | "price" | "solution" | "references" | "recent";
            /** Label */
            label: string;
            /**
             * Sources
             * @default 0
             */
            sources: number;
            /**
             * Sources Label
             * @default
             */
            sources_label: string;
            /**
             * Tbd
             * @default false
             */
            tbd: boolean;
            /** Text */
            text: string;
        };
        /** FindLine */
        FindLine: {
            /** N */
            n: number;
            /**
             * State
             * @enum {string}
             */
            state: "done" | "active" | "wait";
            /** Text */
            text: string;
        };
        /** FindProgress */
        FindProgress: {
            /**
             * Candidates So Far
             * @default 0
             */
            candidates_so_far: number;
            /** Error */
            error?: string | null;
            /**
             * Eta Label
             * @default 약 30초
             */
            eta_label: string;
            /** Lines */
            lines?: components["schemas"]["FindLine"][];
        };
        /** FooterView */
        FooterView: {
            /**
             * Kb Case
             * @default 0
             */
            kb_case: number;
            /**
             * Public
             * @default 0
             */
            public: number;
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
        /** HandoffConfirm */
        HandoffConfirm: {
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
            /**
             * Target
             * @enum {string}
             */
            target: "mi" | "proposal_why" | "storyboard" | "report";
            /** Target Id */
            target_id?: string | null;
            /** Target Title */
            target_title?: string | null;
        };
        /** HandoffList */
        HandoffList: {
            /** Items */
            items: components["schemas"]["HandoffView"][];
        };
        /** HandoffOut */
        HandoffOut: {
            /** Anonymization Map */
            anonymization_map?: {
                [key: string]: string;
            };
            /** Handoff Id */
            handoff_id?: string | null;
            /** Letters */
            letters?: string[];
            /**
             * Named
             * @default false
             */
            named: boolean;
            /**
             * Status
             * @default prepared
             */
            status: string;
            /**
             * Target
             * @enum {string}
             */
            target: "mi" | "proposal_why" | "storyboard" | "report";
        };
        /** HandoffPatch */
        HandoffPatch: {
            /**
             * Status
             * @enum {string}
             */
            status: "prepared" | "delivered" | "failed";
            /** Target Id */
            target_id?: string | null;
            /** Target Title */
            target_title?: string | null;
        };
        /** HandoffView */
        HandoffView: {
            /** Analysis Id */
            analysis_id: string;
            /** Anonymization Map */
            anonymization_map?: {
                [key: string]: string;
            };
            /** Confirmations */
            confirmations?: {
                [key: string]: unknown;
            };
            /**
             * Created At
             * @default
             */
            created_at: string;
            /** Id */
            id: string;
            /** Served Named At */
            served_named_at?: string[];
            /** Status */
            status: string;
            /**
             * Target
             * @enum {string}
             */
            target: "mi" | "proposal_why" | "storyboard" | "report";
            /** Target Id */
            target_id?: string | null;
            /** Target Title */
            target_title?: string | null;
            /**
             * Updated At
             * @default
             */
            updated_at: string;
            /**
             * Version
             * @default 0
             */
            version: number;
        };
        /** HeaderView */
        HeaderView: {
            /**
             * Desc
             * @default
             */
            desc: string;
            /**
             * Kicker
             * @default
             */
            kicker: string;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** JobAccepted */
        JobAccepted: {
            /** Analysis Id */
            analysis_id?: string | null;
            /** Job Id */
            job_id: string;
            /**
             * Status
             * @default queued
             */
            status: string;
        };
        /** LadderRow */
        LadderRow: {
            /** Desc */
            desc: string;
            /** How */
            how: string;
            /** N */
            n: string;
            /** O */
            o: string;
            /** Signal */
            signal: string;
            /** Tag */
            tag: string;
            /** Width */
            width: number;
        };
        /** ListAction */
        ListAction: {
            /**
             * Kind
             * @default continue
             * @enum {string}
             */
            kind: "result" | "continue" | "detail";
            /** Label */
            label: string;
            /** Route */
            route: string;
        };
        /** ListBanner */
        ListBanner: {
            /** Competitor Ids */
            competitor_ids?: string[];
            /** N */
            n: number;
            /** Target Id */
            target_id: string;
            /**
             * Text
             * @description `경쟁사 {글자} 가 {YYYY.MM} 신제품을 냈어요 — {작업 제목} · 분석 30일 경과`
             */
            text: string;
            /**
             * Title
             * @description `{n}건은 다시 분석을 권해요.`
             */
            title: string;
        };
        /** ListCounts */
        ListCounts: {
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
             * Upd
             * @default 0
             */
            upd: number;
        };
        /** ListItem */
        ListItem: {
            action: components["schemas"]["ListAction"];
            /** Count */
            count?: number | null;
            /**
             * Count Label
             * @description 숫자 또는 `—`
             * @default —
             */
            count_label: string;
            /**
             * Count Unit
             * @description `곳` · `후보`(회색)
             * @default
             */
            count_unit: string;
            /** Current Job Id */
            current_job_id?: string | null;
            /** Id */
            id: string;
            /**
             * Input Label
             * @default
             */
            input_label: string;
            /**
             * Input Mode
             * @default free
             * @enum {string}
             */
            input_mode: "free" | "requirements" | "mi";
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
            /** Route */
            route: string;
            /**
             * Sent Label
             * @description `MI 작업 · 제안서` 처럼. 없으면 null(`아직 없음`)
             */
            sent_label?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "draft" | "finding" | "ask" | "confirming" | "analyzing" | "stopped" | "done" | "upd" | "failed";
            /**
             * Status Label
             * @description `완료` · `확인 중` · `업데이트 필요`
             */
            status_label: string;
            /**
             * Status Tone
             * @default check
             * @enum {string}
             */
            status_tone: "done" | "check" | "upd";
            /**
             * Sub
             * @description `{소유자} · {시점}`
             */
            sub: string;
            /**
             * Time Label
             * @default
             */
            time_label: string;
            /** Title */
            title: string;
            /**
             * Updated At
             * @default
             */
            updated_at: string;
        };
        /** MiRef */
        MiRef: {
            /** Analysis Id */
            analysis_id: string;
            /** Version */
            version?: number | null;
        };
        /** OtherCompetitor */
        OtherCompetitor: {
            /**
             * Current
             * @default false
             */
            current: boolean;
            /** Id */
            id: string;
            /** Letter */
            letter: string;
        };
        /** ParseIn */
        ParseIn: {
            /** Extra Text */
            extra_text?: string | null;
            /** File Ids */
            file_ids?: string[];
            /** Requirements Id */
            requirements_id?: string | null;
            /** Rq Version */
            rq_version?: number | null;
            /** Text */
            text?: string | null;
        };
        /** ParseOut */
        ParseOut: {
            /**
             * Degraded
             * @description LLM 없이 KB 만으로 읽음(§4.4 2)
             * @default false
             */
            degraded: boolean;
            /** Exclude Names */
            exclude_names?: string[];
            /** Found Count */
            found_count: number;
            /** Include Names */
            include_names?: string[];
            /**
             * Reading Files
             * @default false
             */
            reading_files: boolean;
            rfp?: components["schemas"]["RfpView"];
            segment: components["schemas"]["SegmentView"];
            slots: components["schemas"]["SlotsView"];
        };
        /** PartialInfo */
        PartialInfo: {
            /**
             * Analyzing
             * @default false
             */
            analyzing: boolean;
            /**
             * Done
             * @default 0
             */
            done: number;
            /**
             * Stopped
             * @default false
             */
            stopped: boolean;
            /**
             * Text
             * @default
             */
            text: string;
            /**
             * Total
             * @default 0
             */
            total: number;
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
            content?: {
                [key: string]: unknown;
            };
            /** From Label */
            from_label?: string | null;
            /**
             * Include Default
             * @default true
             */
            include_default: boolean;
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Sheet Role */
            sheet_role: string;
            /** Sheet Title */
            sheet_title?: string | null;
            /** Sources */
            sources?: components["schemas"]["PHItemSource"][];
            /**
             * Status
             * @default ok
             * @enum {string}
             */
            status: "ok" | "warn" | "add";
            /**
             * Status Label
             * @default
             */
            status_label: string;
            /** Template Hint */
            template_hint?: {
                [key: string]: string;
            } | null;
        };
        /** PHItemSource */
        PHItemSource: {
            /** Kind */
            kind: string;
            /** Label */
            label: string;
            /** Ref */
            ref: string;
            /** Tier */
            tier?: string | null;
            /** Url */
            url?: string | null;
        };
        /** PHSource */
        PHSource: {
            /**
             * Feature
             * @default CA
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
        /** PHTarget */
        PHTarget: {
            /**
             * Proposal Type
             * @default standard
             * @enum {string}
             */
            proposal_type: "standard" | "quickwin" | "solution";
            /**
             * Section Key
             * @default why
             */
            section_key: string;
        };
        /** ProgressOut */
        ProgressOut: {
            ask?: components["schemas"]["AskRequest"] | null;
            find?: components["schemas"]["FindProgress"];
            /** Job Id */
            job_id?: string | null;
            /** Job Kind */
            job_kind?: string | null;
            /** Job Status */
            job_status?: string | null;
            run?: components["schemas"]["RunProgress"] | null;
            /**
             * Status
             * @enum {string}
             */
            status: "draft" | "finding" | "ask" | "confirming" | "analyzing" | "stopped" | "done" | "upd" | "failed";
        };
        /** ProposalHandoff */
        ProposalHandoff: {
            /** Assets */
            assets?: {
                [key: string]: unknown;
            }[];
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
             * @default false
             */
            live_link: boolean;
            /**
             * Named
             * @default false
             */
            named: boolean;
            rq_ref?: components["schemas"]["RqRef"] | null;
            source: components["schemas"]["PHSource"];
            target: components["schemas"]["PHTarget"];
        };
        /** ResearchIn */
        ResearchIn: {
            /** Facts */
            facts?: ("lineup" | "price" | "solution" | "references" | "recent")[] | null;
        };
        /** ResearchState */
        ResearchState: {
            /**
             * Eta Label
             * @default
             */
            eta_label: string;
            /** Job Id */
            job_id?: string | null;
            /**
             * Running
             * @default false
             */
            running: boolean;
        };
        /** ResultOut */
        ResultOut: {
            /**
             * Can Send
             * @default false
             */
            can_send: boolean;
            /** Cautions */
            cautions?: components["schemas"]["CautionView"][];
            /** Chips */
            chips?: components["schemas"]["ChipView"][];
            /** Competitors */
            competitors: components["schemas"]["ResultRow"][];
            /**
             * Criteria Count
             * @default 0
             */
            criteria_count: number;
            footer?: components["schemas"]["FooterView"];
            header?: components["schemas"]["HeaderView"];
            partial?: components["schemas"]["PartialInfo"];
            /**
             * Status
             * @enum {string}
             */
            status: "draft" | "finding" | "ask" | "confirming" | "analyzing" | "stopped" | "done" | "upd" | "failed";
            /** Strengths */
            strengths?: components["schemas"]["StrengthView"][];
            table?: components["schemas"]["TableView"] | null;
            /**
             * Version
             * @default 0
             */
            version: number;
            /**
             * View
             * @default overview
             * @enum {string}
             */
            view: "overview" | "table" | "strengths";
        };
        /** ResultRow */
        ResultRow: {
            /** Display */
            display: string;
            /**
             * Dn
             * @default 0
             */
            dn: number;
            /**
             * Eq
             * @default 0
             */
            eq: number;
            /** Id */
            id: string;
            /**
             * Kind
             * @default
             */
            kind: string;
            /** Letter */
            letter: string;
            /**
             * Positioning
             * @default
             */
            positioning: string;
            /**
             * Real Name
             * @default
             */
            real_name: string;
            /**
             * Sources
             * @default 0
             */
            sources: number;
            /**
             * State
             * @default done
             * @enum {string}
             */
            state: "done" | "partial" | "run" | "wait" | "skipped";
            /**
             * State Label
             * @default
             */
            state_label: string;
            /**
             * Unknown
             * @default 0
             */
            unknown: number;
            /**
             * Up
             * @default 0
             */
            up: number;
        };
        /** RfpView */
        RfpView: {
            /** Competitor Mentions */
            competitor_mentions?: string[];
            /** Eval Criteria */
            eval_criteria?: string[];
        };
        /** RoutingRule */
        RoutingRule: {
            /** Decision */
            decision: string;
            /**
             * Mode
             * @enum {string}
             */
            mode: "auto" | "check" | "ask" | "pin";
            /** Mode Label */
            mode_label: string;
            /** Signal */
            signal: string;
        };
        /** RoutingRules */
        RoutingRules: {
            /**
             * Ask Requires Ambiguous Industry
             * @default true
             */
            ask_requires_ambiguous_industry: boolean;
            /** Asks */
            asks: components["schemas"]["AskRow"][];
            /** Asks Footer */
            asks_footer: string;
            /** Asks Title */
            asks_title: string;
            header: components["schemas"]["HeaderView"];
            /** Ladder */
            ladder: components["schemas"]["LadderRow"][];
            /** Ladder Example */
            ladder_example: string;
            /** Ladder Sub */
            ladder_sub: string;
            /** Ladder Title */
            ladder_title: string;
            /** Legend */
            legend: components["schemas"]["ChipView"][];
            /** Stages */
            stages: components["schemas"]["RoutingStage"][];
            /** Thresholds */
            thresholds?: {
                [key: string]: number;
            };
        };
        /** RoutingStage */
        RoutingStage: {
            /** No */
            no: string;
            /** Rules */
            rules: components["schemas"]["RoutingRule"][];
            /** Sub */
            sub: string;
            /** Title */
            title: string;
        };
        /** RqRef */
        RqRef: {
            /** Rq Id */
            rq_id: string;
            /** Version */
            version?: number | null;
        };
        /** RunCompetitor */
        RunCompetitor: {
            /** Current Fact */
            current_fact?: string | null;
            /**
             * Display
             * @default
             */
            display: string;
            /** Done Facts */
            done_facts?: string[];
            /** Id */
            id: string;
            /** Letter */
            letter: string;
            /**
             * State
             * @default wait
             * @enum {string}
             */
            state: "wait" | "run" | "done" | "partial";
            /**
             * Text
             * @description CA3 문장(`경쟁사 A — 제품 · 솔루션 · 레퍼런스 완료, 가격대 찾는 중`)
             * @default
             */
            text: string;
        };
        /** RunIn */
        RunIn: {
            /** Competitor Ids */
            competitor_ids?: string[] | null;
            /**
             * Mode
             * @default full
             * @enum {string}
             */
            mode: "full" | "changed_only" | "rejudge" | "resume";
        };
        /** RunProgress */
        RunProgress: {
            /** Competitors */
            competitors?: components["schemas"]["RunCompetitor"][];
            /** Criteria */
            criteria?: {
                [key: string]: number;
            };
            /**
             * Eta Label
             * @default
             */
            eta_label: string;
            /** Eta S */
            eta_s?: number | null;
            /**
             * Mode
             * @default full
             */
            mode: string;
            /**
             * Pct
             * @default 0
             */
            pct: number;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** SegmentCandidate */
        SegmentCandidate: {
            /** Code */
            code: string;
            /**
             * Confidence
             * @default 0
             */
            confidence: number;
            /**
             * Name
             * @default
             */
            name: string;
        };
        /** SegmentView */
        SegmentView: {
            /**
             * Ambiguous
             * @default false
             */
            ambiguous: boolean;
            /** Candidates */
            candidates?: components["schemas"]["SegmentCandidate"][];
            /**
             * Code
             * @default GEN
             */
            code: string;
            /**
             * Confidence
             * @default 0
             */
            confidence: number;
            /**
             * Full
             * @default
             */
            full: string;
            /** Gap */
            gap?: number | null;
            /**
             * Name
             * @description 업종 short 이름
             * @default 범용
             */
            name: string;
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
        /** SlotsView */
        SlotsView: {
            customer: components["schemas"]["SlotView"];
            industry: components["schemas"]["SlotView"];
            place: components["schemas"]["SlotView"];
            product: components["schemas"]["SlotView"];
        };
        /** SlotView */
        SlotView: {
            /**
             * Chip Text
             * @description `{항목} · {값}` 또는 `{항목} · 비어 있음`
             * @default
             */
            chip_text: string;
            /**
             * Code
             * @description 업종 칸이면 업종 코드(FB …)
             */
            code?: string | null;
            /** Confidence */
            confidence?: number | null;
            /**
             * Found
             * @default empty
             * @enum {string}
             */
            found: "found" | "partial" | "empty";
            /**
             * Key
             * @enum {string}
             */
            key: "customer" | "industry" | "place" | "product";
            /**
             * Label
             * @description 고객사 · 업종 · 장소 · 제품
             */
            label: string;
            /**
             * Origin
             * @description input · definition · answer · inferred · mi · rfp
             */
            origin?: string | null;
            /**
             * Partial
             * @default false
             */
            partial: boolean;
            /** Value */
            value?: string | null;
        };
        /** SnapshotOut */
        SnapshotOut: {
            /** Pages */
            pages?: string[] | null;
            /** Text */
            text: string;
        };
        /** SourceAddIn */
        SourceAddIn: {
            /** Claim Id */
            claim_id?: string | null;
            /** Classification */
            classification?: ("internal" | "confidential" | "customer" | "public") | null;
            /** Competitor Id */
            competitor_id?: string | null;
            /** Fact Key */
            fact_key?: ("lineup" | "price" | "solution" | "references" | "recent") | null;
            /** File Id */
            file_id?: string | null;
            /** Url */
            url?: string | null;
        };
        /** SourceAddOut */
        SourceAddOut: {
            /** Job Id */
            job_id: string;
            /** Source Id */
            source_id?: string | null;
            /**
             * Status
             * @default queued
             */
            status: string;
        };
        /** SourceCard */
        SourceCard: {
            /** Actions */
            actions?: string[];
            /**
             * Footnote
             * @default
             */
            footnote: string;
            /** Highlight */
            highlight?: string | null;
            /** Kind */
            kind: string;
            /** Kind Label */
            kind_label: string;
            /**
             * Meta
             * @default
             */
            meta: string;
            /**
             * N
             * @default 0
             */
            n: number;
            /**
             * Quote
             * @default
             */
            quote: string;
            /**
             * Reason
             * @default
             */
            reason: string;
            /** Source Id */
            source_id: string;
            /** Status */
            status: string;
            /**
             * Status Label
             * @description `원문 일치` 또는 `확인 필요`
             */
            status_label: string;
            /**
             * Title
             * @default
             */
            title: string;
            /** Url */
            url?: string | null;
        };
        /** SourceList */
        SourceList: {
            /** Items */
            items: components["schemas"]["SourceOut"][];
        };
        /** SourceOut */
        SourceOut: {
            /** Competitor Id */
            competitor_id?: string | null;
            /** Fact Key */
            fact_key?: string | null;
            /** Id */
            id: string;
            /** Kind */
            kind: string;
            /** Kind Label */
            kind_label: string;
            /**
             * Mode
             * @default
             */
            mode: string;
            /** Published At */
            published_at?: string | null;
            /**
             * Publisher
             * @default
             */
            publisher: string;
            /** Query */
            query?: string | null;
            /** Retrieved At */
            retrieved_at?: string | null;
            /**
             * State
             * @default used
             */
            state: string;
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
        /** StoppedInfo */
        StoppedInfo: {
            /**
             * Done
             * @default 0
             */
            done: number;
            /**
             * Text
             * @default
             */
            text: string;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** StrengthView */
        StrengthView: {
            /** Claim Ids */
            claim_ids?: string[];
            /** Competitor Ids */
            competitor_ids?: string[];
            /** Competitor Letters */
            competitor_letters?: string[];
            /** Criterion Ids */
            criterion_ids?: string[];
            /** Criterion Names */
            criterion_names?: string[];
            /** Note */
            note: string;
            /**
             * Sources Label
             * @default
             */
            sources_label: string;
            /** Title */
            title: string;
        };
        /** Suggestion */
        Suggestion: {
            /**
             * N
             * @default 0
             */
            n: number;
            /** Name */
            name: string;
        };
        /** TableCell */
        TableCell: {
            /** Claim Ids */
            claim_ids?: string[];
            /** Source Ns */
            source_ns?: number[];
            /**
             * Tbd
             * @default false
             */
            tbd: boolean;
            /** Text */
            text: string;
            /** Verdict */
            verdict?: ("samsung_better" | "similar" | "samsung_worse" | "unknown") | null;
        };
        /** TableColumn */
        TableColumn: {
            /** Id */
            id: string;
            /** Label */
            label: string;
            /** Letter */
            letter?: string | null;
            /** Real Name */
            real_name?: string | null;
            /**
             * Samsung
             * @default false
             */
            samsung: boolean;
        };
        /** TableCriterion */
        TableCriterion: {
            /** Id */
            id: string;
            /**
             * Importance
             * @default 3
             */
            importance: number;
            /** Name */
            name: string;
            /**
             * Source
             * @default
             */
            source: string;
        };
        /** TableView */
        TableView: {
            /** Cells */
            cells: components["schemas"]["TableCell"][][];
            /** Columns */
            columns: components["schemas"]["TableColumn"][];
            /** Criteria */
            criteria: components["schemas"]["TableCriterion"][];
        };
        /** VersionList */
        VersionList: {
            /** Items */
            items: components["schemas"]["VersionSummary"][];
        };
        /** VersionSummary */
        VersionSummary: {
            /**
             * Created At
             * @default
             */
            created_at: string;
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
        /** VsSamsung */
        VsSamsung: {
            /** Better */
            better?: string[];
            /** Similar */
            similar?: string[];
            /** Unknown */
            unknown?: string[];
            /** Worse */
            worse?: string[];
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
                limit?: number;
                q?: string | null;
                /** @description updated_desc(기본)|created_desc|title */
                sort?: string | null;
                /** @description all|done|check */
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
                "application/json": components["schemas"]["AnalysisCreate"];
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
            /** @description auto_run — 찾기 → 분석을 사람 확인 없이 잇는다(§6.11 C2) */
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
    get_analysis: {
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
    add_refs: {
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
            query: {
                handoff_id?: string | null;
                target: string;
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
    get_candidates: {
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
                    "application/json": components["schemas"]["CandidatesOut"];
                };
            };
        };
    };
    add_candidate: {
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
                "application/json": components["schemas"]["CandidateAdd"];
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
                    "application/json": components["schemas"]["CandidateAddOut"];
                };
            };
        };
    };
    patch_candidate: {
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
                "application/json": components["schemas"]["CandidatePatch"];
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
                    "application/json": components["schemas"]["CompetitorView"];
                };
            };
        };
    };
    changes: {
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
                    "application/json": components["schemas"]["ChangesOut"];
                };
            };
        };
    };
    list_claims: {
        parameters: {
            query?: {
                competitor?: string | null;
                fact?: string | null;
                status?: string | null;
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
    remove_source: {
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
                    "application/json": components["schemas"]["ClaimItem"];
                };
            };
        };
    };
    get_competitor: {
        parameters: {
            query?: {
                version?: number | null;
            };
            header?: never;
            path: {
                aid: string;
                cmp: string;
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
                    "application/json": components["schemas"]["CompetitorDetail"];
                };
            };
        };
    };
    research: {
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
                "application/json": components["schemas"]["ResearchIn"];
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
                    "application/json": components["schemas"]["CriteriaOut"];
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
                    "application/json": components["schemas"]["CriteriaPutOut"];
                };
            };
            /** @description 분석 중 — 지금 잡을 끝내고 모은 사실을 재사용해 판정부터 다시 */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CriteriaPutOut"];
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
    start_find: {
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
    list_handoffs: {
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
                    "application/json": components["schemas"]["HandoffList"];
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
                    "application/json": components["schemas"]["HandoffView"];
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
                    "application/json": components["schemas"]["ProgressOut"];
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
                type?: string;
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
                version?: number | null;
                view?: string;
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
                    "application/json": components["schemas"]["ResultOut"];
                };
            };
        };
    };
    start_run: {
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
                "application/json": components["schemas"]["RunIn"];
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
    list_sources: {
        parameters: {
            query?: {
                competitor?: string | null;
                kind?: string | null;
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
                    "application/json": components["schemas"]["SourceAddOut"];
                };
            };
        };
    };
    source_snapshot: {
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
    list_ca_flows: {
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
                    "application/json": components["schemas"]["CFList"];
                };
            };
        };
    };
    create_ca_flow: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CFCreate"];
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
                    "application/json": components["schemas"]["CFDoc"];
                };
            };
        };
    };
    get_ca_flow: {
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
                    "application/json": components["schemas"]["CFDoc"];
                };
            };
        };
    };
    patch_ca_flow: {
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
                "application/json": components["schemas"]["CFPatch"];
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
                    "application/json": components["schemas"]["CFDoc"];
                };
            };
        };
    };
    suggest_candidates: {
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
                    "application/json": components["schemas"]["CFCandidatesResult"];
                };
            };
        };
    };
    finish: {
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
                    "application/json": components["schemas"]["CFStageOut"];
                };
            };
        };
    };
    add_competitor: {
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
                "application/json": components["schemas"]["CFCompetitorAdd"];
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
                    "application/json": components["schemas"]["CFDoc"];
                };
            };
        };
    };
    delete_competitor: {
        parameters: {
            query?: {
                expected_version?: number | null;
            };
            header?: never;
            path: {
                cid: string;
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
                    "application/json": components["schemas"]["CFDoc"];
                };
            };
        };
    };
    patch_competitor: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                cid: string;
                flow_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CFCompetitorPatch"];
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
                    "application/json": components["schemas"]["CFDoc"];
                };
            };
        };
    };
    add_match: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                cid: string;
                flow_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CFMatchAdd"];
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
                    "application/json": components["schemas"]["CFDoc"];
                };
            };
        };
    };
    delete_match: {
        parameters: {
            query?: {
                expected_version?: number | null;
            };
            header?: never;
            path: {
                cid: string;
                flow_id: string;
                mid: string;
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
                    "application/json": components["schemas"]["CFDoc"];
                };
            };
        };
    };
    patch_match: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                cid: string;
                flow_id: string;
                mid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CFMatchPatch"];
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
                    "application/json": components["schemas"]["CFDoc"];
                };
            };
        };
    };
    get_stage: {
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
                    "application/json": components["schemas"]["CFStageOut"];
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
    parse: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ParseIn"];
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
                    "application/json": components["schemas"]["ParseOut"];
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
}
