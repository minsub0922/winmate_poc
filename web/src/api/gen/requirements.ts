// 자동 생성 — 직접 고치지 말 것. 원본: contracts/requirements.json (make contracts)
export interface paths {
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
    "/v1/requirements": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 정의서 목록(RQ0 · Storyboard SB1 has_version=true · 경쟁사 CA1R · 제안서 R1) */
        get: operations["list_requirements"];
        put?: never;
        /** 정의서 만들기(RQ1 첫 입력 · 심층 작성 · 파일 놓기) */
        post: operations["create_requirement"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 정의서(작업본 + 메타) */
        get: operations["get_requirement"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/customer-questions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 고객에게 물을 것 */
        get: operations["list_customer_questions"];
        put?: never;
        /** 고객 질문 추가(Storyboard · 제안서 · 수동) — 같은 origin.ref_id + text 면 200 기존 것 */
        post: operations["create_customer_question"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/customer-questions/{qid}": {
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
        /** 메일에 넣기 체크 · 없애기(dismissed) */
        patch: operations["patch_customer_question"];
        trace?: never;
    };
    "/v1/requirements/{rq_id}/customer-questions/mail-draft": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 메일 문구(체크한 질문만 · 내부 정보 제외, 15초 넘으면 템플릿) */
        post: operations["mail_draft"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/deep-sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 심층 작성 시작 → rq.deep.analyze 잡 · 진행 중 세션이 있으면 409 SESSION_ACTIVE */
        post: operations["create_deep_session"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/deep-sessions/{sid}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 세션(조회 때 규칙형 보강할 곳을 다시 평가) */
        get: operations["get_deep_session"];
        put?: never;
        post?: never;
        /** 세션 취소(canceled — 이미 반영한 값은 남음) */
        delete: operations["cancel_deep_session"];
        options?: never;
        head?: never;
        /** 다룰 곳 선택(ready 일 때만) */
        patch: operations["select_deep_gaps"];
        trace?: never;
    };
    "/v1/requirements/{rq_id}/deep-sessions/{sid}/answers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 답 하나 처리(동기 LangGraph rq_deep_answer, 30초) */
        post: operations["answer_deep"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/deep-sessions/{sid}/finish": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 끝내기 → finished(result · completeness_after) */
        post: operations["finish_deep_session"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/deep-sessions/{sid}/proposals/{pid}/accept": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 반영 제안 반영(고친 문장 · 부수 효과 선택) */
        post: operations["accept_proposal"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/deep-sessions/{sid}/proposals/{pid}/revise": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 반영 제안 다시 쓰기(고칠 지시) */
        post: operations["revise_proposal"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/deep-sessions/{sid}/reanalyze": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 다시 분석(폼이 크게 바뀐 ready 세션 · 실패한 분석) */
        post: operations["reanalyze_deep_session"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/deep-sessions/{sid}/start": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 질의 시작(asking) — 선택 0이면 422 NOTHING_SELECTED */
        post: operations["start_deep_session"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/diff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 두 버전 비교(항목 id 기준) */
        get: operations["diff_versions"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/draft": {
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
        /** 작업본 편집(자동 저장 · 모든 폼 편집) — 409 REVISION_CONFLICT 면 다시 읽고 적용 */
        patch: operations["patch_draft"];
        trace?: never;
    };
    "/v1/requirements/{rq_id}/exports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 정의서 DOCX · PDF(제작자 의견 · 내부 메모 항상 제외) */
        post: operations["create_export"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/exports/{export_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 내보내기 결과 */
        get: operations["get_export"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/files": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 파일 넣기 → rq.fill 잡(채우는 중이면 뒤에 줄 선다) */
        post: operations["add_files"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/files/{file_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** 파일 빼기 — rollback=true 면 그 파일에서 와서 사람이 안 고친 값 · 항목 · 키맨도 지운다 */
        delete: operations["remove_file"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/files/{file_id}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 파일 빼기 되돌리기(재추출 없이 스냅숏 복원) */
        post: operations["restore_file"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/links": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 이 정의서를 쓰는 곳(RQ6 쓰는 곳) */
        get: operations["list_links"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/links/{service_name}/{ref_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** 링크 등록 · 갱신(소비 서비스가 호출, 멱등) */
        put: operations["upsert_link"];
        post?: never;
        /** 링크 지우기 */
        delete: operations["delete_link"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/replies": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 고객 답변 붙여넣기 → rq.reply.analyze 잡 · 둘 다 비면 422 EMPTY_REPLY */
        post: operations["create_reply"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/replies/{rid}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 답변 분석(Storyboard 미리 보기도 읽음) */
        get: operations["get_reply"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** 바뀔 곳 선택(storyboard_impact 다시 계산) */
        patch: operations["patch_reply"];
        trace?: never;
    };
    "/v1/requirements/{rq_id}/replies/{rid}/apply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 선택한 변경 반영 → 새 버전(reason=reply), 링크 sync_state=pending */
        post: operations["apply_reply"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/save": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 버전 저장 — 바뀐 것이 없으면 200 {created:false} */
        post: operations["save_requirement"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/share": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 내부 공유 링크(RQ6 공유) */
        post: operations["share_requirement"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/versions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 버전 목록(최신순) */
        get: operations["list_versions"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/versions/{n}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 저장 스냅숏(불변) — n 은 숫자 또는 latest */
        get: operations["get_version"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/{rq_id}/versions/{n}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 이 버전으로 되돌리기(새 버전 생성) */
        post: operations["restore_version"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/counts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** RQ0 탭 개수 */
        get: operations["requirement_counts"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requirements/from-files": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 파일로 새 정의서 만들기(제안서 PR1F R3) — 새 정의서 + rq.fill 잡 */
        post: operations["create_from_files"];
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
        /** AcceptProposal */
        AcceptProposal: {
            /** Edited Text */
            edited_text?: string | null;
            /** Side Effects */
            side_effects?: components["schemas"]["SideEffectChoice"][] | null;
        };
        /** AcceptResult */
        AcceptResult: {
            /** Created Question Ids */
            created_question_ids: string[];
            log_entry: components["schemas"]["LogEntry"];
            /** Requirement Revision */
            requirement_revision: number;
            session: components["schemas"]["DeepSession"];
        };
        /** ActiveDeep */
        ActiveDeep: {
            /**
             * Current Index
             * @default 1
             */
            current_index: number;
            /** Session Id */
            session_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "analyzing" | "ready" | "asking" | "finished" | "canceled" | "failed";
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** ActiveJob */
        ActiveJob: {
            /** Job Id */
            job_id: string;
            /** Kind */
            kind: string;
        };
        /** AddFiles */
        AddFiles: {
            /** File Ids */
            file_ids: string[];
        };
        /** AddItemOp */
        AddItemOp: {
            /** After Item Id */
            after_item_id?: string | null;
            /**
             * Item Id
             * @description 클라이언트가 만든 ri_<ULID> 허용
             */
            item_id?: string | null;
            /** Keyman Id */
            keyman_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "add_item";
            /**
             * Text
             * @default
             */
            text: string;
        };
        /** AddKeymanOp */
        AddKeymanOp: {
            /** After Keyman Id */
            after_keyman_id?: string | null;
            /**
             * Keyman Id
             * @description 클라이언트가 만든 km_<ULID> 허용
             */
            keyman_id?: string | null;
            /**
             * Name
             * @default
             */
            name: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "add_keyman";
        };
        /** Alternative */
        Alternative: {
            source: components["schemas"]["Source"] | null;
            /** Value */
            value: string;
        };
        /** AnswerRequest */
        AnswerRequest: {
            /** Gap Id */
            gap_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "option" | "text" | "weights" | "unknown" | "skip";
            /** Option Id */
            option_id?: string | null;
            /** Text */
            text?: string | null;
            /** Weights */
            weights?: {
                [key: string]: number;
            } | null;
        };
        /** AnswerResult */
        AnswerResult: {
            customer_question: components["schemas"]["CustomerQuestion"] | null;
            log_entry: components["schemas"]["LogEntry"] | null;
            /**
             * Outcome
             * @enum {string}
             */
            outcome: "applied" | "proposal" | "deferred" | "skipped";
            proposal: components["schemas"]["Proposal"] | null;
            /** Requirement Revision */
            requirement_revision: number;
            session: components["schemas"]["DeepSession"];
        };
        /** ApplyReply */
        ApplyReply: {
            /** Note */
            note?: string | null;
            /** Propagate */
            propagate?: "storyboard"[];
            /** Selected Change Ids */
            selected_change_ids: string[];
        };
        /** ApplyResult */
        ApplyResult: {
            /** Pending Sync Links */
            pending_sync_links: components["schemas"]["SyncLinkRef"][];
            /** Version */
            version: number;
        };
        /** ContextProduct */
        ContextProduct: {
            /** Id */
            id: string;
            /** Item Ids */
            item_ids: string[];
            /** Name */
            name: string;
            /**
             * Type
             * @description category · model · family …
             */
            type: string;
        };
        /** ContextSolution */
        ContextSolution: {
            /** Id */
            id: string;
            /** Item Ids */
            item_ids: string[];
            /** Name */
            name: string;
        };
        /** ContextSpace */
        ContextSpace: {
            /** Id */
            id: string;
            /** Item Ids */
            item_ids: string[];
            /** Name */
            name: string;
        };
        /** Counts */
        Counts: {
            /** All */
            all: number;
            /** In Progress */
            in_progress: number;
            /** Saved */
            saved: number;
        };
        /** CreateCustomerQuestion */
        CreateCustomerQuestion: {
            /** Keyman Id */
            keyman_id?: string | null;
            origin?: components["schemas"]["CustomerQuestionOriginIn"];
            /** Short Label */
            short_label?: string | null;
            target?: components["schemas"]["QuestionTarget"] | null;
            /** Text */
            text: string;
        };
        /** CreateReply */
        CreateReply: {
            /** File Ids */
            file_ids?: string[];
            /**
             * Text
             * @default
             */
            text: string;
        };
        /** CreateRequirement */
        CreateRequirement: {
            form?: components["schemas"]["FormInit"] | null;
            /** Project Id */
            project_id?: string | null;
        };
        /**
         * CustomerQuestion
         * @description §5.6 고객에게 물을 것.
         */
        CustomerQuestion: {
            answer: components["schemas"]["QuestionAnswer"] | null;
            /** Created At */
            created_at: string;
            /**
             * Id
             * @description cq_<ULID>
             */
            id: string;
            /**
             * Include In Mail
             * @default true
             */
            include_in_mail: boolean;
            /** Keyman Id */
            keyman_id: string | null;
            origin: components["schemas"]["CustomerQuestionOrigin"];
            /** Requirement Id */
            requirement_id: string;
            /** Short Label */
            short_label: string | null;
            /**
             * Status
             * @default open
             * @enum {string}
             */
            status: "open" | "answered" | "dismissed";
            target: components["schemas"]["QuestionTarget"] | null;
            /** Text */
            text: string;
            /** Updated At */
            updated_at: string | null;
        };
        /** CustomerQuestionList */
        CustomerQuestionList: {
            /** Items */
            items: components["schemas"]["CustomerQuestion"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** CustomerQuestionOrigin */
        CustomerQuestionOrigin: {
            /** Confirm Item Id */
            confirm_item_id: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "deep_unknown" | "deep_side_effect" | "storyboard" | "manual" | "proposal" | "reply";
            /** Place Label */
            place_label: string | null;
            /** Ref Id */
            ref_id: string | null;
            /** Service */
            service: string | null;
            /** Session Id */
            session_id: string | null;
        };
        /** CustomerQuestionOriginIn */
        CustomerQuestionOriginIn: {
            /** Confirm Item Id */
            confirm_item_id?: string | null;
            /**
             * Feature
             * @description 기능 코드(SB · PR …) — service 대신 써도 된다
             */
            feature?: string | null;
            /**
             * Kind
             * @description 없으면 service/feature 로 정함(SB → storyboard, PR → proposal, 그 밖 → manual)
             */
            kind?: ("storyboard" | "manual" | "proposal") | null;
            /** Place Label */
            place_label?: string | null;
            /** Ref Id */
            ref_id?: string | null;
            /** Service */
            service?: string | null;
        };
        /** DeepSession */
        DeepSession: {
            /**
             * Base Revision
             * @default 0
             */
            base_revision: number;
            /** Completeness */
            completeness: number | null;
            /** Completeness After */
            completeness_after: number | null;
            /** Completeness Before */
            completeness_before: number | null;
            /** Created At */
            created_at: string;
            /** Current Gap Id */
            current_gap_id: string | null;
            /**
             * Current Index
             * @default 0
             */
            current_index: number;
            error: components["schemas"]["ErrorInfo"] | null;
            /** Gaps */
            gaps: components["schemas"]["Gap"][];
            /**
             * Id
             * @description ds_<ULID>
             */
            id: string;
            /** Job Id */
            job_id: string | null;
            /** Log */
            log: components["schemas"]["LogEntry"][];
            pending_proposal: components["schemas"]["Proposal"] | null;
            /** Requirement Id */
            requirement_id: string;
            result: components["schemas"]["SessionResult"] | null;
            /** Selected Gap Ids */
            selected_gap_ids: string[];
            /**
             * Stale
             * @default false
             */
            stale: boolean;
            /**
             * Status
             * @enum {string}
             */
            status: "analyzing" | "ready" | "asking" | "finished" | "canceled" | "failed";
            /**
             * Total
             * @default 0
             */
            total: number;
            /** Updated At */
            updated_at: string;
        };
        /** Diff */
        Diff: {
            /** Changes */
            changes: components["schemas"]["DiffChange"][];
            /** From Version */
            from_version: number;
            /** To Version */
            to_version: number;
        };
        /** DiffChange */
        DiffChange: {
            /** After */
            after: unknown;
            /** Before */
            before: unknown;
            /** Keyman Id */
            keyman_id: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "added" | "removed" | "changed";
            /** Label */
            label: string | null;
            target: components["schemas"]["DiffTarget"];
        };
        /** DiffTarget */
        DiffTarget: {
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "item" | "field" | "keyman" | "weights";
        };
        /** Entity */
        Entity: {
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Surface */
            surface: string | null;
            /**
             * Type
             * @description space_type · category · solution · capability · model · vertical …(kb A1)
             */
            type: string;
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
        /** ErrorInfo */
        ErrorInfo: {
            /** Code */
            code: string;
            /** Message */
            message: string;
        };
        /** ErrorResponse */
        ErrorResponse: {
            error: components["schemas"]["ErrorDetail"];
        };
        /** Evidence */
        Evidence: {
            /** File Id */
            file_id: string;
            /** Name */
            name: string;
            /** Type Label */
            type_label: string | null;
        };
        /** ExportRecord */
        ExportRecord: {
            /** Created At */
            created_at: string;
            error: components["schemas"]["ErrorInfo"] | null;
            /** File Id */
            file_id: string | null;
            /** File Name */
            file_name: string | null;
            /** Format */
            format: string;
            /** Id */
            id: string;
            /** Job Id */
            job_id: string | null;
            /** Requirement Id */
            requirement_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "done" | "failed";
            /** Updated At */
            updated_at: string;
            /** Version */
            version: number;
        };
        /** ExportRequest */
        ExportRequest: {
            /**
             * Format
             * @default docx
             * @enum {string}
             */
            format: "docx" | "pdf";
            /** Version */
            version?: number | null;
        };
        /** FillProgress */
        FillProgress: {
            /**
             * Filled
             * @default 0
             */
            filled: number;
            /** Job Id */
            job_id: string | null;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** FlatItem */
        FlatItem: {
            /** Code */
            code: string;
            /** Entities */
            entities: components["schemas"]["Entity"][];
            /** Evidence */
            evidence: components["schemas"]["Evidence"][];
            /** Id */
            id: string;
            /** Keyman Id */
            keyman_id: string | null;
            /** Keyman Name */
            keyman_name: string | null;
            /** Keyman Weight */
            keyman_weight: number | null;
            /**
             * Needs Confirmation
             * @default false
             */
            needs_confirmation: boolean;
            /** Short */
            short: string | null;
            /** @description 항목이 어디서 왔나(파일이면 file_id · locator(쪽) · quote) */
            source: components["schemas"]["Source"] | null;
            /** Text */
            text: string;
        };
        /** Form */
        Form: {
            /** @description 제작자 의견 — 내부용, 고객 문서 제외 */
            author_note: components["schemas"]["FormField"];
            customer_name: components["schemas"]["FormField"];
            final_audience: components["schemas"]["FormField"];
            /** Keymen */
            keymen: components["schemas"]["Keyman"][];
            project_name: components["schemas"]["FormField"];
            /**
             * Weights Mode
             * @default equal_default
             * @enum {string}
             */
            weights_mode: "equal_default" | "custom";
        };
        /**
         * FormField
         * @description §5.1 Field — 폼 칸 하나.
         */
        FormField: {
            /** Alternatives */
            alternatives: components["schemas"]["Alternative"][];
            derived_from: components["schemas"]["Source"] | null;
            /**
             * Rev
             * @description 이 칸을 마지막으로 쓴 작업본 revision
             * @default 0
             */
            rev: number;
            source: components["schemas"]["Source"] | null;
            /** Updated At */
            updated_at: string | null;
            /** Value */
            value: string | null;
        };
        /** FormInit */
        FormInit: {
            /** Author Note */
            author_note?: string | null;
            /** Customer Name */
            customer_name?: string | null;
            /** Final Audience */
            final_audience?: string | null;
            /** Project Name */
            project_name?: string | null;
        };
        /**
         * FromFiles
         * @description 제안서(PR1F) 등이 파일로 바로 정의서를 만들 때 — 새 정의서 + rq.fill 잡.
         */
        FromFiles: {
            /** Customer Hint */
            customer_hint?: string | null;
            /** File Ids */
            file_ids: string[];
            /** Project Id */
            project_id?: string | null;
        };
        /** Gap */
        Gap: {
            answer: components["schemas"]["GapAnswer"] | null;
            change: components["schemas"]["GapChange"] | null;
            /**
             * Chip Keyman Id
             * @description 키맨 칩이면 색 점(키맨 색)
             */
            chip_keyman_id: string | null;
            /** Chip Label */
            chip_label: string;
            /** Customer Question Ids */
            customer_question_ids: string[];
            /**
             * Id
             * @description gp_<ULID>
             */
            id: string;
            /**
             * Impact
             * @default 1
             */
            impact: number;
            /**
             * Kind
             * @enum {string}
             */
            kind: "empty_field" | "default_weights" | "too_few_items" | "no_keyman" | "unquantified" | "vague_scope" | "ambiguous" | "missing_perspective" | "conflict" | "capability_unclear";
            /**
             * Needs Confirmation
             * @description KB 시드 초안 근거(B2)
             * @default false
             */
            needs_confirmation: boolean;
            /**
             * Origin
             * @enum {string}
             */
            origin: "rule" | "llm" | "kb_b2";
            /** Priority */
            priority: number;
            /**
             * Problem
             * @description ≤ 24자 문제 한 줄
             */
            problem: string;
            question: components["schemas"]["GapQuestion"];
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "proposed" | "applied" | "deferred" | "skipped" | "resolved_by_form" | "deselected";
            target: components["schemas"]["GapTarget"];
        };
        /** GapAnswer */
        GapAnswer: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "option" | "text" | "weights" | "unknown" | "skip";
            /** Option Id */
            option_id: string | null;
            /** Text */
            text: string | null;
            /** Weights */
            weights: {
                [key: string]: number;
            } | null;
        };
        /** GapChange */
        GapChange: {
            /** After Display */
            after_display: string;
            /** After Short */
            after_short: string | null;
            /** Before Display */
            before_display: string | null;
            /**
             * Is Addition
             * @default false
             */
            is_addition: boolean;
            /** Keyman Id */
            keyman_id: string | null;
            /** Label */
            label: string;
        };
        /** GapOption */
        GapOption: {
            /** Id */
            id: string;
            /** Label */
            label: string;
            /** Value */
            value: string | null;
            /** Weights */
            weights: {
                [key: string]: number;
            } | null;
        };
        /** GapQuestion */
        GapQuestion: {
            /**
             * Allow Text
             * @default true
             */
            allow_text: boolean;
            /**
             * Answer Type
             * @enum {string}
             */
            answer_type: "value" | "weights" | "sentence";
            /** Options */
            options: components["schemas"]["GapOption"][];
            /** Text */
            text: string;
        };
        /** GapTarget */
        GapTarget: {
            /** Field */
            field: ("project_name" | "customer_name" | "final_audience" | "author_note") | null;
            /** Item Id */
            item_id: string | null;
            /** Keyman Id */
            keyman_id: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "field" | "weights" | "keyman" | "item" | "keymen";
        };
        /** ImpactLink */
        ImpactLink: {
            /** Places */
            places: components["schemas"]["ImpactPlace"][];
            /** Ref Id */
            ref_id: string;
            /** Route */
            route: string | null;
            /** Title */
            title: string | null;
        };
        /** ImpactPlace */
        ImpactPlace: {
            /** Code */
            code: string | null;
            /** Label */
            label: string;
        };
        /** InternalText */
        InternalText: {
            /**
             * Internal
             * @default true
             */
            internal: boolean;
            /** Value */
            value: string | null;
        };
        /** JobAccepted */
        JobAccepted: {
            /** Job Id */
            job_id: string;
            ref: components["schemas"]["JobRef"];
            /**
             * Status
             * @default queued
             */
            status: string;
        };
        /** JobRef */
        JobRef: {
            /** Id */
            id: string;
            /** Kind */
            kind: string;
        };
        /**
         * Keyman
         * @description §5.2 키맨.
         */
        Keyman: {
            /**
             * Color Index
             * @default 0
             */
            color_index: number;
            /**
             * Id
             * @description km_<ULID>
             */
            id: string;
            /** Items */
            items: components["schemas"]["ReqItem"][];
            /**
             * Name
             * @default
             */
            name: string;
            /**
             * Order
             * @default 0
             */
            order: number;
            /**
             * Rev
             * @default 0
             */
            rev: number;
            source: components["schemas"]["Source"] | null;
            /**
             * Weight
             * @description 키맨 ≥ 2: 합 100 · 각 ≥ 5 / 1명: 100 / 0명: 없음
             */
            weight: number | null;
        };
        /** LinkDependency */
        "LinkDependency-Input": {
            /** Places */
            places?: components["schemas"]["LinkPlace-Input"][];
            target: components["schemas"]["LinkTarget"];
        };
        /** LinkDependency */
        "LinkDependency-Output": {
            /** Places */
            places: components["schemas"]["LinkPlace-Output"][];
            target: components["schemas"]["LinkTarget"];
        };
        /** LinkList */
        LinkList: {
            /** Items */
            items: components["schemas"]["UsageLink"][];
        };
        /** LinkPlace */
        "LinkPlace-Input": {
            /** Code */
            code?: string | null;
            /** Label */
            label: string;
        };
        /** LinkPlace */
        "LinkPlace-Output": {
            /** Code */
            code: string | null;
            /** Label */
            label: string;
        };
        /** LinkTarget */
        LinkTarget: {
            /**
             * Id
             * @description 항목 ri_ · 키맨 km_ · 칸 이름 · weights
             */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "item" | "field" | "keyman" | "weights";
        };
        /** LogEntry */
        LogEntry: {
            /** Gap Id */
            gap_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "applied" | "deferred" | "skipped" | "resolved";
            /** Label */
            label: string;
            /** Value Display */
            value_display: string;
        };
        /** MailDraft */
        MailDraft: {
            /** Body */
            body: string;
            /**
             * Generated By
             * @enum {string}
             */
            generated_by: "llm" | "template";
            /** Subject */
            subject: string;
        };
        /** MailDraftRequest */
        MailDraftRequest: {
            /** Question Ids */
            question_ids: string[];
        };
        /** MoveItemOp */
        MoveItemOp: {
            /** Index */
            index: number;
            /** Item Id */
            item_id: string;
            /** Keyman Id */
            keyman_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "move_item";
        };
        /** PatchCustomerQuestion */
        PatchCustomerQuestion: {
            /** Include In Mail */
            include_in_mail?: boolean | null;
            /** Status */
            status?: ("dismissed" | "open") | null;
        };
        /** PatchDraft */
        PatchDraft: {
            /**
             * Base Revision
             * @description 클라이언트가 마지막으로 본 revision(없으면 충돌 검사 안 함)
             */
            base_revision?: number | null;
            /** Ops */
            ops?: (components["schemas"]["SetFieldOp"] | components["schemas"]["AddKeymanOp"] | components["schemas"]["UpdateKeymanOp"] | components["schemas"]["RemoveKeymanOp"] | components["schemas"]["SetWeightsOp"] | components["schemas"]["ResetWeightsEqualOp"] | components["schemas"]["AddItemOp"] | components["schemas"]["UpdateItemOp"] | components["schemas"]["RemoveItemOp"] | components["schemas"]["MoveItemOp"])[];
        };
        /** PatchReply */
        PatchReply: {
            /** Selected Change Ids */
            selected_change_ids: string[];
        };
        /** Proposal */
        Proposal: {
            /** After Short */
            after_short: string | null;
            /** After Text */
            after_text: string;
            /** Answer Text */
            answer_text: string | null;
            /** Before Text */
            before_text: string | null;
            /** Gap Id */
            gap_id: string;
            /**
             * Id
             * @description pp_<ULID>
             */
            id: string;
            /** Keyman Id */
            keyman_id: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "replace_item" | "add_item" | "set_field";
            /**
             * Revisions
             * @default 0
             */
            revisions: number;
            /** Side Effects */
            side_effects: components["schemas"]["SideEffect"][];
            target: components["schemas"]["GapTarget"];
        };
        /** QuestionAnswer */
        QuestionAnswer: {
            /** Answered At */
            answered_at: string;
            /** Reply Id */
            reply_id: string | null;
            /** Text */
            text: string | null;
        };
        /** QuestionTarget */
        QuestionTarget: {
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "item" | "field" | "keyman";
        };
        /** RemoveItemOp */
        RemoveItemOp: {
            /** Item Id */
            item_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "remove_item";
        };
        /** RemoveKeymanOp */
        RemoveKeymanOp: {
            /** Keyman Id */
            keyman_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "remove_keyman";
        };
        /** ReplyAnalysis */
        ReplyAnalysis: {
            /** Applied Version */
            applied_version: number | null;
            /** Base Version */
            base_version: number;
            /** Changes */
            changes: components["schemas"]["ReplyChange"][];
            /** Created At */
            created_at: string;
            error: components["schemas"]["ErrorInfo"] | null;
            /** File Ids */
            file_ids: string[];
            /** Files */
            files: components["schemas"]["ReplyFile"][];
            /**
             * Id
             * @description rp_<ULID>
             */
            id: string;
            /** Job Id */
            job_id: string | null;
            /** Matches */
            matches: {
                [key: string]: unknown;
            }[];
            /** Requirement Id */
            requirement_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "analyzing" | "ready" | "applied" | "failed";
            storyboard_impact: components["schemas"]["StoryboardImpact"];
            /**
             * Text
             * @default
             */
            text: string;
            /** Updated At */
            updated_at: string;
            /** Version Note */
            version_note: string | null;
        };
        /** ReplyChange */
        ReplyChange: {
            /** After Display */
            after_display: string;
            /** Before Display */
            before_display: string | null;
            /** Evidence File Ids */
            evidence_file_ids: string[];
            /**
             * Id
             * @description ch_<ULID>
             */
            id: string;
            /** Label */
            label: string;
            /** Ops */
            ops: {
                [key: string]: unknown;
            }[];
            /** Resolves Question Ids */
            resolves_question_ids: string[];
            /**
             * Selected
             * @default true
             */
            selected: boolean;
            target: components["schemas"]["ReplyTarget"];
        };
        /** ReplyFile */
        ReplyFile: {
            /** File Id */
            file_id: string;
            /** Name */
            name: string;
            /** Type Label */
            type_label: string | null;
        };
        /** ReplyTarget */
        ReplyTarget: {
            /** Id */
            id: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "item" | "field" | "keyman" | "weights" | "evidence" | "new_item";
        };
        /**
         * ReqItem
         * @description §5.3 요구사항 항목.
         */
        ReqItem: {
            /**
             * Code
             * @description "RQ-01" — 재사용하지 않음
             */
            code: string;
            /** Entities */
            entities: components["schemas"]["Entity"][];
            /** Evidence */
            evidence: components["schemas"]["Evidence"][];
            /**
             * Id
             * @description ri_<ULID> — 버전을 넘어 유지
             */
            id: string;
            /**
             * Needs Confirmation
             * @default false
             */
            needs_confirmation: boolean;
            /**
             * Order
             * @default 0
             */
            order: number;
            /**
             * Rev
             * @default 0
             */
            rev: number;
            /**
             * Short
             * @description ≤ 24자 짧은 이름(LLM)
             */
            short: string | null;
            source: components["schemas"]["Source"] | null;
            /** Text */
            text: string;
            /** Updated At */
            updated_at: string | null;
        };
        /**
         * Requirement
         * @description §5.1 요구사항 정의서(작업본 + 메타).
         */
        Requirement: {
            active_deep: components["schemas"]["ActiveDeep"] | null;
            /** Active Deep Session Id */
            active_deep_session_id: string | null;
            active_job: components["schemas"]["ActiveJob"] | null;
            context: components["schemas"]["RqContext"];
            /** Created At */
            created_at: string;
            /** Files */
            files: components["schemas"]["SourceFile"][];
            fill_progress: components["schemas"]["FillProgress"] | null;
            form: components["schemas"]["Form"];
            /**
             * Has Unsaved Changes
             * @default false
             */
            has_unsaved_changes: boolean;
            /**
             * Id
             * @description rq_<ULID>
             */
            id: string;
            /**
             * Item Count
             * @default 0
             */
            item_count: number;
            /**
             * Keyman Count
             * @default 0
             */
            keyman_count: number;
            /** Last Deep Session Id */
            last_deep_session_id: string | null;
            /**
             * List State
             * @enum {string}
             */
            list_state: "input" | "filling" | "deepening" | "editing" | "saved";
            /**
             * Open Question Count
             * @default 0
             */
            open_question_count: number;
            owner: components["schemas"]["UserRef"];
            /** Project Id */
            project_id: string | null;
            /** Queued Jobs */
            queued_jobs: components["schemas"]["ActiveJob"][];
            /**
             * Revision
             * @description 작업본 쓰기마다 +1
             */
            revision: number;
            /** Route */
            route: string;
            /** Saved At */
            saved_at: string | null;
            /** Short Title */
            short_title: string | null;
            /**
             * Skipped Ops
             * @description PATCH draft 에서 대상이 사라져 무시한 op
             */
            skipped_ops: components["schemas"]["SkippedOp"][] | null;
            /** State Label */
            state_label: string;
            /**
             * Title
             * @description short_title ?? `${고객사} ${프로젝트명}` ?? null
             */
            title: string | null;
            /** Updated At */
            updated_at: string;
            /**
             * Version
             * @description 최신 저장 버전, 0 = 없음
             * @default 0
             */
            version: number;
        };
        /** RequirementList */
        RequirementList: {
            /** Items */
            items: components["schemas"]["RequirementListItem"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** RequirementListItem */
        RequirementListItem: {
            active_deep: components["schemas"]["ActiveDeep"] | null;
            /** Customer Name */
            customer_name: string | null;
            /**
             * Has Unsaved Changes
             * @default false
             */
            has_unsaved_changes: boolean;
            /** Id */
            id: string;
            /**
             * Item Count
             * @default 0
             */
            item_count: number;
            /**
             * Keyman Count
             * @default 0
             */
            keyman_count: number;
            /**
             * List State
             * @enum {string}
             */
            list_state: "input" | "filling" | "deepening" | "editing" | "saved";
            /**
             * Open Question Count
             * @default 0
             */
            open_question_count: number;
            owner: components["schemas"]["UserRef"];
            /** Project Id */
            project_id: string | null;
            /** Project Name */
            project_name: string | null;
            /** Route */
            route: string;
            /** Saved At */
            saved_at: string | null;
            /** State Label */
            state_label: string;
            /** Title */
            title: string | null;
            /** Updated At */
            updated_at: string;
            /**
             * Version
             * @default 0
             */
            version: number;
        };
        /**
         * RequirementVersion
         * @description 불변 저장 스냅숏. 소비자(Storyboard · MI · 경쟁사 · VP · Spec · 제안서)가 읽는 기준.
         */
        RequirementVersion: {
            /**
             * Change Count
             * @default 0
             */
            change_count: number;
            /** Created At */
            created_at: string;
            created_by: components["schemas"]["UserRef"] | null;
            /** Customer Name */
            customer_name: string | null;
            /** Final Audience */
            final_audience: string | null;
            /**
             * Item Count
             * @default 0
             */
            item_count: number;
            /**
             * Keyman Count
             * @default 0
             */
            keyman_count: number;
            /**
             * Latest Version
             * @description 지금 이 정의서의 최신 저장 버전
             * @default 0
             */
            latest_version: number;
            /** Note */
            note: string | null;
            /**
             * Open Question Count
             * @default 0
             */
            open_question_count: number;
            /** Project Id */
            project_id: string | null;
            /** Project Name */
            project_name: string | null;
            /**
             * Reason
             * @enum {string}
             */
            reason: "direct" | "deep" | "edit" | "reply" | "restore";
            /** Requirement Id */
            requirement_id: string;
            snapshot: components["schemas"]["Snapshot"];
            /** Summary */
            summary: string;
            /** Title */
            title: string | null;
            /** Version */
            version: number;
        };
        /** ResetWeightsEqualOp */
        ResetWeightsEqualOp: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "reset_weights_equal";
        };
        /** RestoreResult */
        RestoreResult: {
            /** Version */
            version: number;
        };
        /** ResultQuestion */
        ResultQuestion: {
            /** Id */
            id: string;
            /** Short Label */
            short_label: string | null;
            /** Text */
            text: string;
        };
        /** ReviseProposal */
        ReviseProposal: {
            /** Instruction */
            instruction: string;
        };
        /** ReviseResult */
        ReviseResult: {
            proposal: components["schemas"]["Proposal"];
            session: components["schemas"]["DeepSession"];
        };
        /**
         * RqContext
         * @description 화면에 보이지 않는 파생 정보 — 소비자용(§8.3).
         */
        RqContext: {
            /** Deadline Text */
            deadline_text: string | null;
            /** Language */
            language: string | null;
            /** Products */
            products: components["schemas"]["ContextProduct"][];
            /** Scale Text */
            scale_text: string | null;
            /** Solutions */
            solutions: components["schemas"]["ContextSolution"][];
            /** Spaces */
            spaces: components["schemas"]["ContextSpace"][];
            vertical: components["schemas"]["Vertical"] | null;
        };
        /** SaveRequest */
        SaveRequest: {
            /** Note */
            note?: string | null;
            /** Reason */
            reason?: ("direct" | "deep" | "edit") | null;
        };
        /** SaveResult */
        SaveResult: {
            /** Created */
            created: boolean;
            requirement: components["schemas"]["Requirement"] | null;
            /** Version */
            version: number;
        };
        /** SelectGaps */
        SelectGaps: {
            /** Selected Gap Ids */
            selected_gap_ids: string[];
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
        /** SessionResult */
        SessionResult: {
            /** Changes */
            changes: components["schemas"]["GapChange"][];
            /** Customer Question Ids */
            customer_question_ids: string[];
            /** Customer Questions */
            customer_questions: components["schemas"]["ResultQuestion"][];
            /** Reinforced Count */
            reinforced_count: number;
        };
        /** SetFieldOp */
        SetFieldOp: {
            /**
             * Field
             * @enum {string}
             */
            field: "project_name" | "customer_name" | "final_audience" | "author_note";
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "set_field";
            /** Value */
            value?: string | null;
        };
        /** SetWeightsOp */
        SetWeightsOp: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "set_weights";
            /**
             * Weights
             * @description {km_id: 정수} — 합 100, 각 ≥ 5
             */
            weights: {
                [key: string]: number;
            };
        };
        /** ShareResult */
        ShareResult: {
            /** Token */
            token: string | null;
            /** Url */
            url: string;
        };
        /** SideEffect */
        SideEffect: {
            /**
             * Checked
             * @default true
             */
            checked: boolean;
            /** Id */
            id: string;
            /** Keyman Id */
            keyman_id: string | null;
            /**
             * Kind
             * @default add_customer_question
             * @constant
             */
            kind: "add_customer_question";
            /** Label */
            label: string;
            /** Question Text */
            question_text: string;
        };
        /** SideEffectChoice */
        SideEffectChoice: {
            /** Checked */
            checked: boolean;
            /** Id */
            id: string;
        };
        /** SkippedOp */
        SkippedOp: {
            /** Index */
            index: number;
            /** Op */
            op: string;
            /** Reason */
            reason: string;
        };
        /** Snapshot */
        Snapshot: {
            /** @description 제작자 의견(internal: true) */
            author_note: components["schemas"]["InternalText"];
            context: components["schemas"]["RqContext"];
            /** Customer Questions */
            customer_questions: components["schemas"]["SnapshotQuestion"][];
            form: components["schemas"]["SnapshotForm"];
            /** Items Flat */
            items_flat: components["schemas"]["FlatItem"][];
            /** Keymen */
            keymen: components["schemas"]["SnapshotKeyman"][];
            /** Source Files */
            source_files: components["schemas"]["SnapshotFile"][];
        };
        /** SnapshotFile */
        SnapshotFile: {
            /** File Id */
            file_id: string;
            /** Name */
            name: string;
            /** Type Label */
            type_label: string | null;
        };
        /** SnapshotForm */
        SnapshotForm: {
            /** @description 내부용(internal) — 소비자는 고객용 산출물에 넣지 않는다 */
            author_note: components["schemas"]["FormField"];
            /**
             * Author Note Internal
             * @default true
             */
            author_note_internal: boolean;
            customer_name: components["schemas"]["FormField"];
            final_audience: components["schemas"]["FormField"];
            /** Keymen */
            keymen: components["schemas"]["Keyman"][];
            project_name: components["schemas"]["FormField"];
            /**
             * Weights Mode
             * @default equal_default
             * @enum {string}
             */
            weights_mode: "equal_default" | "custom";
        };
        /** SnapshotKeyman */
        SnapshotKeyman: {
            /**
             * Color Index
             * @default 0
             */
            color_index: number;
            /** Id */
            id: string;
            /** Item Ids */
            item_ids: string[];
            /** Name */
            name: string;
            /**
             * Order
             * @default 0
             */
            order: number;
            /** Weight */
            weight: number | null;
        };
        /** SnapshotQuestion */
        SnapshotQuestion: {
            /** Id */
            id: string;
            /** Keyman Id */
            keyman_id: string | null;
            /** Short Label */
            short_label: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "open" | "answered" | "dismissed";
            target: components["schemas"]["QuestionTarget"] | null;
            /** Text */
            text: string;
        };
        /**
         * Source
         * @description 값이 어디서 왔나(§5.1 Source).
         */
        Source: {
            /** File Id */
            file_id: string | null;
            /**
             * File Label
             * @description 배지 글자: PPTX · PDF · DOCX · TXT · 메일
             */
            file_label: string | null;
            /** File Name */
            file_name: string | null;
            /**
             * Job Id
             * @description 채운 잡(이번 잡에서 막 채운 칸 강조)
             */
            job_id: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "user" | "file" | "deep" | "reply" | "storyboard";
            /**
             * Locator
             * @description "슬라이드 3" · "p.5" · "줄 12"
             */
            locator: string | null;
            /**
             * Quote
             * @description 원문 근거 문장(≤ 200자)
             */
            quote: string | null;
            /** Reply Id */
            reply_id: string | null;
            /** Service */
            service: string | null;
            /** Session Id */
            session_id: string | null;
        };
        /**
         * SourceFile
         * @description §5.4 정의서에 넣은 파일.
         */
        SourceFile: {
            /** Added At */
            added_at: string | null;
            /** Doc Kind */
            doc_kind: ("rfp" | "meeting_memo" | "mail" | "other") | null;
            error: components["schemas"]["ErrorInfo"] | null;
            /** File Id */
            file_id: string;
            /**
             * Filled Count
             * @default 0
             */
            filled_count: number;
            /** Job Id */
            job_id: string | null;
            /** Name */
            name: string;
            /**
             * Status
             * @default reading
             * @enum {string}
             */
            status: "uploading" | "reading" | "done" | "failed";
            /** Type Label */
            type_label: string;
        };
        /** StoryboardImpact */
        StoryboardImpact: {
            /**
             * Count
             * @default 0
             */
            count: number;
            /** Links */
            links: components["schemas"]["ImpactLink"][];
        };
        /** SyncLinkRef */
        SyncLinkRef: {
            /** Ref Id */
            ref_id: string;
            /** Service */
            service: string;
        };
        /** UpdateItemOp */
        UpdateItemOp: {
            /** Item Id */
            item_id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "update_item";
            /** Text */
            text: string;
        };
        /** UpdateKeymanOp */
        UpdateKeymanOp: {
            /** Keyman Id */
            keyman_id: string;
            /** Name */
            name: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            op: "update_keyman";
        };
        /** UpsertLink */
        UpsertLink: {
            /** Depends On */
            depends_on?: components["schemas"]["LinkDependency-Input"][];
            /** Route */
            route?: string | null;
            /** Rq Version */
            rq_version: number;
            /** Title */
            title?: string | null;
        };
        /** UsageLink */
        UsageLink: {
            /** Created At */
            created_at: string;
            /** Depends On */
            depends_on: components["schemas"]["LinkDependency-Output"][];
            /** Pending Version */
            pending_version: number | null;
            /** Ref Id */
            ref_id: string;
            /** Requirement Id */
            requirement_id: string;
            /** Route */
            route: string | null;
            /** Rq Version */
            rq_version: number;
            /**
             * Service
             * @enum {string}
             */
            service: "storyboard" | "mi" | "competitor" | "vp" | "spec" | "proposal";
            /**
             * Sync State
             * @default up_to_date
             * @enum {string}
             */
            sync_state: "up_to_date" | "pending";
            /** Title */
            title: string | null;
            /** Updated At */
            updated_at: string;
        };
        /** UserRef */
        UserRef: {
            /** Id */
            id: string;
            /**
             * Name
             * @default
             */
            name: string;
        };
        /** VersionList */
        VersionList: {
            /** Items */
            items: components["schemas"]["VersionSummary"][];
            /** Next Cursor */
            next_cursor: string | null;
        };
        /** VersionSummary */
        VersionSummary: {
            /**
             * Change Count
             * @default 0
             */
            change_count: number;
            /** Created At */
            created_at: string;
            created_by: components["schemas"]["UserRef"] | null;
            /** Note */
            note: string | null;
            /** Reason */
            reason: string;
            /** Summary */
            summary: string;
            /** Version */
            version: number;
        };
        /** Vertical */
        Vertical: {
            /**
             * Ask
             * @default false
             */
            ask: boolean;
            /** Top2 */
            top2: components["schemas"]["VerticalCandidate"][];
        };
        /** VerticalCandidate */
        VerticalCandidate: {
            /** Id */
            id: string;
            /** Name */
            name: string;
            /**
             * Score
             * @default 0
             */
            score: number;
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
    list_requirements: {
        parameters: {
            query?: {
                cursor?: string | null;
                /** @description 고객사 부분 일치(제안서 R1) */
                customer?: string | null;
                /** @description true 면 저장된 버전(v1 이상)이 있는 것만 */
                has_version?: boolean | null;
                limit?: number;
                /** @description me | all | <user id> */
                owner?: string;
                project_id?: string | null;
                /** @description 제목 · 고객사 · 프로젝트명 · 키맨 이름 부분 일치 */
                q?: string | null;
                /** @description all | in_progress | saved */
                tab?: "all" | "in_progress" | "saved";
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
                    "application/json": components["schemas"]["RequirementList"];
                };
            };
        };
    };
    create_requirement: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["CreateRequirement"] | null;
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
                    "application/json": components["schemas"]["Requirement"];
                };
            };
        };
    };
    get_requirement: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
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
                    "application/json": components["schemas"]["Requirement"];
                };
            };
        };
    };
    list_customer_questions: {
        parameters: {
            query?: {
                status?: "open" | "answered" | "dismissed" | "all";
            };
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
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
                    "application/json": components["schemas"]["CustomerQuestionList"];
                };
            };
        };
    };
    create_customer_question: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateCustomerQuestion"];
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
            /** @description 이미 있는 질문(멱등) */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomerQuestion"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CustomerQuestion"];
                };
            };
        };
    };
    patch_customer_question: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                qid: string;
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchCustomerQuestion"];
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
                    "application/json": components["schemas"]["CustomerQuestion"];
                };
            };
        };
    };
    mail_draft: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MailDraftRequest"];
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
                    "application/json": components["schemas"]["MailDraft"];
                };
            };
        };
    };
    create_deep_session: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
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
    get_deep_session: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
                sid: string;
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
                    "application/json": components["schemas"]["DeepSession"];
                };
            };
        };
    };
    cancel_deep_session: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
                sid: string;
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
                    "application/json": components["schemas"]["DeepSession"];
                };
            };
        };
    };
    select_deep_gaps: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
                sid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SelectGaps"];
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
                    "application/json": components["schemas"]["DeepSession"];
                };
            };
        };
    };
    answer_deep: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
                sid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AnswerRequest"];
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
                    "application/json": components["schemas"]["AnswerResult"];
                };
            };
        };
    };
    finish_deep_session: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
                sid: string;
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
                    "application/json": components["schemas"]["DeepSession"];
                };
            };
        };
    };
    accept_proposal: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                pid: string;
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
                sid: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["AcceptProposal"] | null;
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
                    "application/json": components["schemas"]["AcceptResult"];
                };
            };
        };
    };
    revise_proposal: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                pid: string;
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
                sid: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviseProposal"];
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
                    "application/json": components["schemas"]["ReviseResult"];
                };
            };
        };
    };
    reanalyze_deep_session: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
                sid: string;
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
    start_deep_session: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
                sid: string;
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
                    "application/json": components["schemas"]["DeepSession"];
                };
            };
        };
    };
    diff_versions: {
        parameters: {
            query: {
                from: number;
                to: number;
            };
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
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
                    "application/json": components["schemas"]["Diff"];
                };
            };
        };
    };
    patch_draft: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchDraft"];
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
                    "application/json": components["schemas"]["Requirement"];
                };
            };
        };
    };
    create_export: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["ExportRequest"] | null;
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
    get_export: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                export_id: string;
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
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
    add_files: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AddFiles"];
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
    remove_file: {
        parameters: {
            query?: {
                rollback?: boolean;
            };
            header?: never;
            path: {
                file_id: string;
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
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
                    "application/json": components["schemas"]["Requirement"];
                };
            };
        };
    };
    restore_file: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                file_id: string;
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
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
                    "application/json": components["schemas"]["Requirement"];
                };
            };
        };
    };
    list_links: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
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
                    "application/json": components["schemas"]["LinkList"];
                };
            };
        };
    };
    upsert_link: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 그 서비스의 자원 id(예: sb_<ULID>) */
                ref_id: string;
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
                /** @description 쓰는 서비스(storyboard · mi · competitor · vp · spec · proposal) */
                service_name: "storyboard" | "mi" | "competitor" | "vp" | "spec" | "proposal";
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UpsertLink"];
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
                    "application/json": components["schemas"]["UsageLink"];
                };
            };
        };
    };
    delete_link: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 그 서비스의 자원 id(예: sb_<ULID>) */
                ref_id: string;
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
                /** @description 쓰는 서비스(storyboard · mi · competitor · vp · spec · proposal) */
                service_name: "storyboard" | "mi" | "competitor" | "vp" | "spec" | "proposal";
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
    create_reply: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateReply"];
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
    get_reply: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                rid: string;
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
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
                    "application/json": components["schemas"]["ReplyAnalysis"];
                };
            };
        };
    };
    patch_reply: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                rid: string;
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchReply"];
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
                    "application/json": components["schemas"]["ReplyAnalysis"];
                };
            };
        };
    };
    apply_reply: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                rid: string;
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApplyReply"];
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
                    "application/json": components["schemas"]["ApplyResult"];
                };
            };
        };
    };
    save_requirement: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["SaveRequest"] | null;
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
            /** @description 작업본이 최신 버전과 같아 버전 그대로 */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SaveResult"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SaveResult"];
                };
            };
        };
    };
    share_requirement: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
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
    list_versions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
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
    get_version: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 버전 번호 또는 latest */
                n: string;
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
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
                    "application/json": components["schemas"]["RequirementVersion"];
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
                /** @description 정의서 id(rq_<ULID>) */
                rq_id: string;
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
                    "application/json": components["schemas"]["RestoreResult"];
                };
            };
        };
    };
    requirement_counts: {
        parameters: {
            query?: {
                owner?: string;
                q?: string | null;
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
                    "application/json": components["schemas"]["Counts"];
                };
            };
        };
    };
    create_from_files: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FromFiles"];
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
}
