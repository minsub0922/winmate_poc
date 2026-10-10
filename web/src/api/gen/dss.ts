// 자동 생성 — 직접 고치지 말 것. 원본: contracts/dss.json (make contracts)
export interface paths {
    "/v1/dss": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Dss
         * @description DSS 목록(최근 수정 순) — 보드 List 의 초안 줄.
         */
        get: operations["list_dss"];
        put?: never;
        /**
         * Create Dss
         * @description 새 DSS — 고른 Storyboard 의 고객 요구사항(rq)을 문맥으로 가져온다. Storyboard 없으면 404, rq 없으면 422 PREREQUISITE_MISSING.
         *     같은 Storyboard 의 저장 전 초안이 있으면 그것을 200 으로 돌려준다(Gate 를 다시 거쳐도 초안이 늘지 않음).
         */
        post: operations["create_dss"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/dss/{dss_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Dss
         * @description DSS 한 건. 허브에만 있는 DSS(id = DSS-nn)는 그 stages.dss 값으로 편집본을 만들어 돌려준다.
         */
        get: operations["get_dss"];
        put?: never;
        post?: never;
        /**
         * Delete Dss
         * @description 저장 전 초안 지우기(목록 줄 ×, 소프트 삭제 · 작업물 색인도 지움) — 한 번도 저장하지 않은 것만.
         *     저장한 DSS 는 Storyboard 에 연결돼 있어 409 SAVED_CONTENT, 없으면 404 NOT_FOUND.
         */
        delete: operations["delete_dss"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/dss/{dss_id}:accept-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Accept All
         * @description 공간별 제품 AI 추천 모두 수락.
         */
        post: operations["accept_all"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/dss/{dss_id}:finish": {
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
         * @description 저장 → Storyboard flow.json stages.dss · 요약본 · 팝업 카드(허브 push_stage). 공간 · 제품이 없으면 422.
         */
        post: operations["finish"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/dss/{dss_id}:suggest": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Suggest
         * @description AI 추가기능(점선 → 수락) — industry: 업종 추론 · spaces: 공간 추천 · products: 공간별 제품 자동 매칭(`ds.industry_spaces.v1`) ·
         *     solutions: 솔루션 추천(`ds.solutions.v1`). 모델이 없으면 KB 로 결정적 추천(mode=kb_only).
         */
        post: operations["suggest"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/dss/{dss_id}/industry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Set Industry
         * @description 업종 고르기(value) · AI 업종 추론 적용(accept_ai).
         */
        put: operations["set_industry"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/dss/{dss_id}/products/{product_id}": {
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
         * Delete Product
         * @description 제품 빼기 — AI 추천 거절도 이것.
         */
        delete: operations["delete_product"];
        options?: never;
        head?: never;
        /**
         * Patch Product
         * @description 수량 고치기(빈 문자열이면 [확인 필요]) · AI 추천 수락(accept).
         */
        patch: operations["patch_product"];
        trace?: never;
    };
    "/v1/dss/{dss_id}/solution-options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Solution Options
         * @description 솔루션 고르기 카드 — 카탈로그 전체(관련 높은 순) · 함께 쓰는 제품 · 고름 · AI 추천 · 겹침 안내.
         */
        get: operations["solution_options"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/dss/{dss_id}/solutions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Set Solutions
         * @description 고른 솔루션(0개 이상, 카탈로그 id). AI 추천이던 것은 ai-accepted. 함께 쓰는 제품은 서비스가 다시 계산한다.
         */
        put: operations["set_solutions"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/dss/{dss_id}/spaces": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Space
         * @description 공간 추가 — AI 공간 추천에 있던 이름이면 ai-accepted(근거 유지). 같은 이름이 있으면 409 SPACE_EXISTS.
         */
        post: operations["add_space"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/dss/{dss_id}/spaces/{space_key}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Space */
        delete: operations["delete_space"];
        options?: never;
        head?: never;
        /** Rename Space */
        patch: operations["rename_space"];
        trace?: never;
    };
    "/v1/dss/{dss_id}/spaces/{space_key}/candidates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Space Candidates
         * @description 이 공간의 KB 후보 제품군(S1, 그 공간 관련 요구 문장으로) — 제품 고르기 팝업의 'KB 추천' 묶음.
         */
        get: operations["space_candidates"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/dss/{dss_id}/spaces/{space_key}/products": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Product
         * @description 공간에 제품 넣기(직접). 이미 있는 제품이면 그대로(AI 추천이었으면 수락).
         */
        post: operations["add_product"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/dss/{dss_id}/stage": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Stage
         * @description 지금 값으로 만든 stages.dss · 요약 줄(저장하지 않음).
         */
        get: operations["get_stage"];
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
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** DSAddProduct */
        DSAddProduct: {
            /** Category */
            category?: string | null;
            /**
             * Expected Version
             * @description 주면 지금 판과 다를 때 409 VERSION_CONFLICT
             */
            expected_version?: number | null;
            /** Family Id */
            family_id?: string | null;
            /** Model Code */
            model_code?: string | null;
            /** Name */
            name: string;
            /** Qty */
            qty?: string | null;
            /** Ref */
            ref?: string | null;
            /** Why */
            why?: string | null;
        };
        /** DSAddSpace */
        DSAddSpace: {
            /**
             * Expected Version
             * @description 주면 지금 판과 다를 때 409 VERSION_CONFLICT
             */
            expected_version?: number | null;
            /** Name */
            name: string;
        };
        /** DSCandidate */
        DSCandidate: {
            /** Category */
            category?: string | null;
            /** Family Id */
            family_id?: string | null;
            /**
             * Kind
             * @default product
             * @constant
             */
            kind: "product";
            /** Model Code */
            model_code?: string | null;
            /** Name */
            name: string;
            /** Ref */
            ref?: string | null;
            /** Why */
            why?: string | null;
        };
        /** DSCandidates */
        DSCandidates: {
            /** Items */
            items: components["schemas"]["DSCandidate"][];
            /** Space */
            space: string;
        };
        /** DSCounts */
        DSCounts: {
            /** Pending */
            pending: number;
            /** Products */
            products: number;
            /** Solutions */
            solutions: number;
            /** Spaces */
            spaces: number;
        };
        /** DSCreate */
        DSCreate: {
            /**
             * Sb Id
             * @description 사전 작업(고객 요구사항)이 된 Storyboard
             */
            sb_id: string;
            /** Title */
            title?: string | null;
        };
        /** DSDoc */
        DSDoc: {
            /**
             * Code
             * @description 화면 · flow.json 에 쓰는 짧은 번호(DSS-01 …)
             */
            code?: string | null;
            counts: components["schemas"]["DSCounts"];
            /** Created At */
            created_at: string;
            /** Customer */
            customer?: string | null;
            /** Id */
            id: string;
            industry?: components["schemas"]["DSIndustry"] | null;
            /** @description AI 업종 추론(점선) — 적용해야 들어간다 */
            industry_ai?: components["schemas"]["DSIndustrySuggestion"] | null;
            /** Industry Options */
            industry_options?: string[];
            /**
             * Reqs
             * @description 요구 문장(근거 번호)
             */
            reqs?: components["schemas"]["DSReq"][];
            /**
             * Rq Ref
             * @description 사전 작업 고객 요구사항 ref(근거 표시 RQ-05 1)
             */
            rq_ref?: string | null;
            /** Sb Id */
            sb_id?: string | null;
            /**
             * Solution Recs
             * @description AI 솔루션 추천(점선) — 골라야 들어간다
             */
            solution_recs?: components["schemas"]["DSSolutionRec"][];
            /**
             * Solutions
             * @description 고른 솔루션(0개 이상)
             */
            solutions?: components["schemas"]["DSSolution"][];
            /**
             * Space Recs
             * @description AI 공간 추천(점선) — 추가해야 들어간다
             */
            space_recs?: components["schemas"]["DSSpaceRec"][];
            /** Spaces */
            spaces?: components["schemas"]["DSSpace"][];
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
             * @description 저장(완료) 판 — flow.json stages.dss.ver
             */
            ver?: number | null;
            /** Version */
            version: number;
        };
        /** DSFlowSync */
        DSFlowSync: {
            /** Md Added */
            md_added: string;
            /** Synced */
            synced?: string[];
        };
        /** DSIndustry */
        DSIndustry: {
            /**
             * Basis
             * @description 근거(예: RQ-05 ‘입주사 공용 회의실 예약’)
             */
            basis?: string | null;
            /**
             * By
             * @default manual
             * @enum {string}
             */
            by: "manual" | "ai-pending" | "ai-accepted";
            /** Value */
            value: string;
        };
        /** DSIndustrySuggestion */
        DSIndustrySuggestion: {
            /**
             * Alt
             * @description 애매할 때 다른 후보 업종
             */
            alt?: string | null;
            /** Basis */
            basis?: string | null;
            /** Value */
            value: string;
        };
        /** DSList */
        DSList: {
            /** Items */
            items: components["schemas"]["DSListItem"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** DSListItem */
        DSListItem: {
            /** Code */
            code?: string | null;
            counts: components["schemas"]["DSCounts"];
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
        /** DSPatchProduct */
        DSPatchProduct: {
            /**
             * Accept
             * @description AI 추천 수락(ai-pending → ai-accepted)
             */
            accept?: boolean | null;
            /**
             * Expected Version
             * @description 주면 지금 판과 다를 때 409 VERSION_CONFLICT
             */
            expected_version?: number | null;
            /**
             * Qty
             * @description 빈 문자열이면 수량을 지운다([확인 필요])
             */
            qty?: string | null;
        };
        /** DSPatchSpace */
        DSPatchSpace: {
            /**
             * Expected Version
             * @description 주면 지금 판과 다를 때 409 VERSION_CONFLICT
             */
            expected_version?: number | null;
            /** Name */
            name: string;
        };
        /** DSProduct */
        DSProduct: {
            /**
             * By
             * @default manual
             * @enum {string}
             */
            by: "manual" | "ai-pending" | "ai-accepted";
            /** Category */
            category?: string | null;
            /** Family Id */
            family_id?: string | null;
            /** Id */
            id: string;
            /**
             * Kind
             * @default product
             * @constant
             */
            kind: "product";
            /**
             * Model Code
             * @description 대표 모델코드(상세 시트)
             */
            model_code?: string | null;
            /**
             * Name
             * @description 제품 이름(KB 제품군 · 모델 이름 그대로, 직접 넣은 것은 입력 그대로)
             */
            name: string;
            /**
             * Qty
             * @description 수량(예: 2대) — 모르면 null(화면은 [확인 필요])
             */
            qty?: string | null;
            /**
             * Ref
             * @description KB 참조 — kb:family:fam_… · kb:model:mdl_… (없으면 KB 에 없는 직접 입력)
             */
            ref?: string | null;
            /**
             * Why
             * @description 용도 · 근거 한 줄
             */
            why?: string | null;
        };
        /** DSReq */
        DSReq: {
            /** N */
            n: number;
            /** Text */
            text: string;
        };
        /** DSSetIndustry */
        DSSetIndustry: {
            /**
             * Accept Ai
             * @description AI 업종 추론 적용(value 무시)
             * @default false
             */
            accept_ai: boolean;
            /**
             * Expected Version
             * @description 주면 지금 판과 다를 때 409 VERSION_CONFLICT
             */
            expected_version?: number | null;
            /**
             * Value
             * @description 업종(선택지 또는 직접). null 이면 비움
             */
            value?: string | null;
        };
        /** DSSetSolutions */
        DSSetSolutions: {
            /**
             * Expected Version
             * @description 주면 지금 판과 다를 때 409 VERSION_CONFLICT
             */
            expected_version?: number | null;
            /**
             * Ids
             * @description 고를 솔루션 카탈로그 id(0개 이상, 순서대로)
             */
            ids: string[];
        };
        /** DSSolution */
        DSSolution: {
            /**
             * By
             * @default manual
             * @enum {string}
             */
            by: "manual" | "ai-pending" | "ai-accepted";
            /**
             * Id
             * @description 솔루션 카탈로그 id(magicinfo …)
             */
            id: string;
            /**
             * Links
             * @description 함께 쓰는 제품(공간 · 제품)
             */
            links?: string[];
            /** Name */
            name: string;
            /**
             * Ref
             * @description kb:solution:sol_…
             */
            ref?: string | null;
            /** Why */
            why?: string | null;
        };
        /** DSSolutionOption */
        DSSolutionOption: {
            /** Desc */
            desc: string;
            /** Id */
            id: string;
            /** Links */
            links?: string[];
            /** Name */
            name: string;
            /**
             * On
             * @default false
             */
            on: boolean;
            /**
             * Rec
             * @default false
             */
            rec: boolean;
            /** Ref */
            ref?: string | null;
            /**
             * Relevant
             * @description 함께 쓰는 제품 · 요구 · 업종 중 하나라도 맞음(기본으로 보이는 것)
             * @default false
             */
            relevant: boolean;
            /** Why */
            why?: string | null;
        };
        /** DSSolutionOptions */
        DSSolutionOptions: {
            /** Items */
            items: components["schemas"]["DSSolutionOption"][];
            /**
             * Overlap
             * @description 고른 솔루션끼리 겹칠 때 안내(예: 둘 다 사이니지 CMS)
             */
            overlap?: string | null;
        };
        /** DSSolutionRec */
        DSSolutionRec: {
            /** Id */
            id: string;
            /** Why */
            why: string;
        };
        /** DSSpace */
        DSSpace: {
            /**
             * Basis
             * @description 근거(예: RQ-05 1 · 입주사 안내)
             */
            basis?: string | null;
            /**
             * By
             * @default manual
             * @enum {string}
             */
            by: "manual" | "ai-pending" | "ai-accepted";
            /** Key */
            key: string;
            /** Name */
            name: string;
            /** Products */
            products?: components["schemas"]["DSProduct"][];
        };
        /** DSSpaceRec */
        DSSpaceRec: {
            /** Basis */
            basis?: string | null;
            /**
             * Ext
             * @description 요구에는 없는 확장 공간
             * @default false
             */
            ext: boolean;
            /** Name */
            name: string;
            /** Why */
            why: string;
        };
        /** DSStageOut */
        DSStageOut: {
            flow_sync?: components["schemas"]["DSFlowSync"] | null;
            /**
             * Stage
             * @description Storyboard flow.json 의 stages.dss
             */
            stage: {
                [key: string]: unknown;
            };
            /** Summary Md */
            summary_md: string;
        };
        /** DSSuggestBody */
        DSSuggestBody: {
            /**
             * Scope
             * @enum {string}
             */
            scope: "industry" | "spaces" | "products" | "solutions";
        };
        /** DSSuggestResult */
        DSSuggestResult: {
            /** Added */
            added: number;
            doc: components["schemas"]["DSDoc"];
            /** Message */
            message?: string | null;
            /**
             * Mode
             * @description llm = 모델 결과(검증 후) · kb_only = 모델 없이 KB 로 결정적 추천
             * @enum {string}
             */
            mode: "llm" | "kb_only";
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
        /** ServiceInfo */
        ServiceInfo: {
            /** Service */
            service: string;
            /** Title */
            title: string;
            /** Version */
            version: string;
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
    list_dss: {
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
                    "application/json": components["schemas"]["DSList"];
                };
            };
        };
    };
    create_dss: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DSCreate"];
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
            /** @description 이 Storyboard 의 저장 전 초안이 이미 있음 — 그 초안(새로 만들지 않음) */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DSDoc"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DSDoc"];
                };
            };
        };
    };
    get_dss: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                dss_id: string;
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
                    "application/json": components["schemas"]["DSDoc"];
                };
            };
        };
    };
    delete_dss: {
        parameters: {
            query?: {
                /** @description 주면 지금 판과 다를 때 409 VERSION_CONFLICT */
                expected_version?: number | null;
            };
            header?: never;
            path: {
                dss_id: string;
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
    accept_all: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                dss_id: string;
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
                    "application/json": components["schemas"]["DSDoc"];
                };
            };
        };
    };
    finish: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                dss_id: string;
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
                    "application/json": components["schemas"]["DSStageOut"];
                };
            };
        };
    };
    suggest: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                dss_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DSSuggestBody"];
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
                    "application/json": components["schemas"]["DSSuggestResult"];
                };
            };
        };
    };
    set_industry: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                dss_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DSSetIndustry"];
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
                    "application/json": components["schemas"]["DSDoc"];
                };
            };
        };
    };
    delete_product: {
        parameters: {
            query?: {
                expected_version?: number | null;
            };
            header?: never;
            path: {
                dss_id: string;
                product_id: string;
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
                    "application/json": components["schemas"]["DSDoc"];
                };
            };
        };
    };
    patch_product: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                dss_id: string;
                product_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DSPatchProduct"];
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
                    "application/json": components["schemas"]["DSDoc"];
                };
            };
        };
    };
    solution_options: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                dss_id: string;
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
                    "application/json": components["schemas"]["DSSolutionOptions"];
                };
            };
        };
    };
    set_solutions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                dss_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DSSetSolutions"];
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
                    "application/json": components["schemas"]["DSDoc"];
                };
            };
        };
    };
    add_space: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                dss_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DSAddSpace"];
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
                    "application/json": components["schemas"]["DSDoc"];
                };
            };
        };
    };
    delete_space: {
        parameters: {
            query?: {
                expected_version?: number | null;
            };
            header?: never;
            path: {
                dss_id: string;
                space_key: string;
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
                    "application/json": components["schemas"]["DSDoc"];
                };
            };
        };
    };
    rename_space: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                dss_id: string;
                space_key: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DSPatchSpace"];
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
                    "application/json": components["schemas"]["DSDoc"];
                };
            };
        };
    };
    space_candidates: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                dss_id: string;
                space_key: string;
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
                    "application/json": components["schemas"]["DSCandidates"];
                };
            };
        };
    };
    add_product: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                dss_id: string;
                space_key: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DSAddProduct"];
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
                    "application/json": components["schemas"]["DSDoc"];
                };
            };
        };
    };
    get_stage: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                dss_id: string;
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
                    "application/json": components["schemas"]["DSStageOut"];
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
}
