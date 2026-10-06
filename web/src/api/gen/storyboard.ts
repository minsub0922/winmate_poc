// 자동 생성 — 직접 고치지 말 것. 원본: contracts/storyboard.json (make contracts)
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
    "/v1/storyboards": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Storyboards
         * @description 작업 목록(SB0) — 시작된 내 스토리보드만, 수정 시각 내림차순.
         */
        get: operations["list_storyboards"];
        put?: never;
        /**
         * Create Storyboard
         * @description SB1 진입 — 정의서로 스토리보드를 만들고 `sb.prepare` 를 시작한다(`prepare_job_id`). 시작 전 초안이 있으면 재사용(200).
         */
        post: operations["create_storyboard"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Storyboard
         * @description 작업본 전체. 정의서 링크가 `pending` 이면 이때 `sb.rq_sync` 를 시작하고 `active_job` 으로 알린다.
         */
        get: operations["get_storyboard"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Storyboard */
        patch: operations["patch_storyboard"];
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/changes/{chg}/revert": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Revert Change
         * @description 행별 `되돌리기` — 되돌릴 수 없으면 409 NOT_REVERTIBLE.
         */
        post: operations["revert_change"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/compare": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Compare
         * @description SB3V — 기본 from = 최신 저장 버전, to = 작업본. `count` = 변경 + 추가 + 삭제(유지 제외, Q-1).
         */
        get: operations["compare"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/direction": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Direction */
        get: operations["get_direction"];
        put?: never;
        /**
         * Start Direction
         * @description `sb.direction` — `started=true`, step 2. `skip_planning` 이면 모든 질의 `unknown`.
         */
        post: operations["start_direction"];
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Patch Direction
         * @description 기획 방향 선택 · 방향 덧붙이기. 선택이 바뀌면 `sb.messages` 잡(`messages_job_id`).
         */
        patch: operations["patch_direction"];
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/discussions/agenda": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Discussions Agenda
         * @description `회의 안건에 넣기` — 추가 논의를 안건 글로(웹이 클립보드에 복사, Q-8).
         */
        post: operations["discussions_agenda"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/exports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start Export
         * @description SB4E — 작업본 ≠ 최신 버전이면 먼저 저장 → `sb.export` 잡(결과 `{file_id, name, url}`). 표시 유지는 항상 켬.
         */
        post: operations["start_export"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/handoffs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Handoffs
         * @description SB4 `다음에 할 일` 3 — 제안서 · MI · 공간 시나리오.
         */
        get: operations["list_handoffs"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/handoffs/{target}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Record Handoff
         * @description 넘김 기록(→ `status=shared`, SB0 `… 넘겼어요`) — 응답 `route` 로 이동.
         */
        post: operations["record_handoff"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/imports/competitor": {
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
         * @description 경쟁사 분석 CA5 `Storyboard 비교 기준으로`(익명 묶음) → SB1Q3 `비교 기준` 질의의 `경쟁사 제안` 선택지 근거(Q-3).
         */
        post: operations["import_competitor"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/key-messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Key Messages
         * @description 핵심 메시지(Key Message) — VP · 제안서 · MI 가 읽는다.
         */
        get: operations["list_key_messages"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/key-messages/{kmsg}": {
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
         * Patch Key Message
         * @description 문장 고치기 — 표현 검사 다시 · 변경 기록. VP 가 다듬은 문장은 `source: {service: 'vp', ref_id}`.
         */
        patch: operations["patch_key_message"];
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/key-messages/{kmsg}/evidence": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Evidence
         * @description MI4 `Key Message에 근거로 붙이기` — 웹이 근거 스냅숏을 올린다(SB 가 MI 를 부르지 않음, Q-2).
         */
        post: operations["add_evidence"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/key-messages/{kmsg}/flags/{flg}/apply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Apply Flag
         * @description `바꾸기`(검증 안 된 주장 → 대체안) · `빼기`(되돌렸던 내부 목표를 다시 뺀다).
         */
        post: operations["apply_flag"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/key-messages/{kmsg}/flags/{flg}/revert": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Revert Flag
         * @description `되돌리기` — 바꾸기 · 자동으로 뺀 내부 목표를 원래대로.
         */
        post: operations["revert_flag"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/outline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Outline
         * @description 목차(잡 중이면 지금까지 쓴 것 + `writing`).
         */
        get: operations["get_outline"];
        put?: never;
        /**
         * Start Outline
         * @description `sb.outline`(step 3). 실행 중이면 409 JOB_RUNNING.
         */
        post: operations["start_outline"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/planning": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Planning */
        get: operations["get_planning"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/planning/{qid}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Answer Planning
         * @description 답 저장(클릭마다). 순서 있는 복수 선택은 고른 순서대로. 비면 422 NOTHING_SELECTED.
         */
        put: operations["answer_planning"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/prepare": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Prepare
         * @description 정의서 다시 읽기(설정 · 기획 질의).
         */
        post: operations["prepare"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/proposal-handoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Proposal Handoff
         * @description ProposalHandoff v1(10-proposal.md §8.0 S1) — 고객 · Key Message · 제안 전략 · 목차 · 공간 · 자리표시 수치.
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
    "/v1/storyboards/{sb_id}/requirement": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Put Requirement
         * @description SB1 다른 정의서 고르기 — `sb.prepare` 다시. step ≥ 2 면 409 STAGE_LOCKED.
         */
        put: operations["put_requirement"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/requirement-sync": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Requirement Sync
         * @description 정의서 새 버전 반영(`sb.rq_sync`). `dry_run` 이면 미리 보기(`ref.kind=sync_preview`) — 작업본 · 링크 불변. RQ7B 웹이 부른다.
         */
        post: operations["requirement_sync"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/review-requests": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Review Request
         * @description SB4 `내부 검토 요청` — workspace 검토 요청 · `status=shared`.
         */
        post: operations["review_request"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/revisions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Revision */
        post: operations["create_revision"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/revisions/{rev}": {
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
    "/v1/storyboards/{sb_id}/revisions/{rev}/apply": {
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
         * @description `적용` — 작업본 반영 · 변경 기록(cause=revision) · 추적 다시 계산(백그라운드). 그 사이 대상이 바뀌었으면 409 REVISION_STALE.
         */
        post: operations["apply_revision"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/revisions/{rev}/discard": {
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
    "/v1/storyboards/{sb_id}/save": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Save
         * @description SB5 `저장하고 공유` — 버전 저장 · `status=done` · step 5.
         */
        post: operations["save"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/schedule": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Schedule
         * @description SB5 — 6단계 · 담당 · D-범위 · 현재 단계.
         */
        get: operations["get_schedule"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/settings": {
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
         * Patch Settings
         * @description SB1S — 바꾼 값은 `source=user`. 목차가 있으면 이후 생성부터 적용(Q-6).
         */
        patch: operations["patch_settings"];
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/share": {
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
         * @description SB3D `공유` — 내부 공유 링크(workspace).
         */
        post: operations["share"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/spaces/{spc}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Space */
        get: operations["get_space"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/spaces/{spc}/compose": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Compose Space
         * @description `sb.space.compose` — 답을 칸 문장으로 다듬기(AI 보탠 구간 표시 · `[00]` · 고객 질문 · 제품 후보).
         */
        post: operations["compose_space"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/spaces/{spc}/questions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Space Questions
         * @description 빈 칸 질문 — 이미 있으면 200 `{questions}`, 없으면 202 `sb.space.questions`.
         */
        post: operations["space_questions"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/spaces/{spc}/slots/{slot}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Put Slot
         * @description 칸 답. `unknown` 이면 `[확인 필요]` + 정의서 고객 질문 추가(`customer_question_id`, 멱등).
         */
        put: operations["put_slot"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/sync-previews/{syp}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Sync Preview */
        get: operations["get_sync_preview"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/trace": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Trace
         * @description 요구 추적(`to_resolve` 는 `priority` 순으로 정리).
         */
        get: operations["get_trace"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/trace/extensions/acknowledge": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Acknowledge Extensions
         * @description SB4X `확인했어요` — 확장은 고객 요구(정의서)로 쓰지 않는다.
         */
        post: operations["acknowledge_extensions"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/trace/items/{rq_item_id}/resolution": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Put Resolution
         * @description SB4U — 놓기(`sb.trace.apply` 잡) · 확인 필요로 유지 · 본제안으로 미루기 · 제외(사유 필수) · 고객에게 묻기. 버리는 요구는 없다.
         */
        put: operations["put_resolution"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/versions": {
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
    "/v1/storyboards/{sb_id}/versions/{n}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Version */
        get: operations["get_version"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/{sb_id}/versions/{n}/restore": {
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
         * @description 옛 버전을 **새 버전**으로 되살린다(역사는 다시 쓰지 않음).
         */
        post: operations["restore_version"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/storyboards/counts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Storyboard Counts
         * @description SB0 탭 숫자(`완료` = done + shared).
         */
        get: operations["storyboard_counts"];
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
        /** ActiveJob */
        ActiveJob: {
            /** Job Id */
            job_id: string;
            /** Kind */
            kind: string;
        };
        /** AddedQuestion */
        AddedQuestion: {
            /** Id */
            id: string;
            /** Short Label */
            short_label: string;
        };
        /** AgendaText */
        AgendaText: {
            /** Text */
            text: string;
        };
        /** Badge */
        Badge: {
            /** Label */
            label: string;
            /**
             * Style
             * @enum {string}
             */
            style: "fill" | "soft" | "line" | "dashed" | "draft" | "muted" | "tbd" | "ext";
        };
        /** ChangeCause */
        ChangeCause: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "rq_sync" | "revision" | "space_questions" | "trace" | "vp" | "user" | "restore";
            /**
             * Label
             * @default
             */
            label: string;
            /** Ref */
            ref?: string | null;
        };
        /** ChangeEntry */
        ChangeEntry: {
            /**
             * After Summary
             * @default
             */
            after_summary: string;
            /** Aspect */
            aspect?: string | null;
            /** At */
            at?: string | null;
            /**
             * Before Summary
             * @default
             */
            before_summary: string;
            cause: components["schemas"]["ChangeCause"];
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "changed" | "added" | "removed" | "kept";
            /** Place Label */
            place_label: string;
            /**
             * Revertible
             * @default true
             */
            revertible: boolean;
            /** Tags */
            tags?: ("extension" | "author_supplemented")[];
        };
        /** Citation */
        Citation: {
            /** Title */
            title: string;
            /** Url */
            url?: string | null;
        };
        /** Compare */
        Compare: {
            /** Causes */
            causes?: string[];
            /**
             * Count
             * @description 바뀐 곳 수 = 변경 + 추가 + 삭제(유지 제외)
             * @default 0
             */
            count: number;
            from: components["schemas"]["CompareFrom"];
            /**
             * Revertible
             * @description to 가 작업본이라 행별 되돌리기가 된다
             * @default false
             */
            revertible: boolean;
            /** Rows */
            rows?: components["schemas"]["ChangeEntry"][];
            to: components["schemas"]["CompareTo"];
        };
        /** CompareFrom */
        CompareFrom: {
            /** Date */
            date?: string | null;
            /** Note */
            note?: string | null;
            /** Version */
            version: number;
        };
        /** CompareTo */
        CompareTo: {
            /** Date */
            date?: string | null;
            /**
             * Is Draft
             * @default false
             */
            is_draft: boolean;
            /** Version */
            version: number;
            /** Version Label */
            version_label: string;
        };
        /** CompetitorCriterion */
        CompetitorCriterion: {
            /** Importance */
            importance?: string | null;
            /** Name */
            name: string;
            /** Source */
            source?: string | null;
        };
        /**
         * CompetitorImport
         * @description 경쟁사 분석 CA5 `Storyboard 비교 기준으로` — 웹이 묶음(bundle?target=storyboard)을 옮겨 올린다(익명).
         */
        CompetitorImport: {
            /** Analysis Id */
            analysis_id?: string | null;
            /** Competitors */
            competitors?: string[];
            /** Criteria */
            criteria?: components["schemas"]["CompetitorCriterion"][];
            /** Note */
            note?: string | null;
            /** Title */
            title?: string | null;
        };
        /** CompetitorImportResult */
        CompetitorImportResult: {
            question?: components["schemas"]["PlanningQuestion"] | null;
            /**
             * Stored
             * @default true
             */
            stored: boolean;
        };
        /** Coverage */
        Coverage: {
            /** Codes */
            codes?: string[];
            /**
             * Count
             * @default 0
             */
            count: number;
            /** Item Ids */
            item_ids?: string[];
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** CreateStoryboard */
        CreateStoryboard: {
            /** Requirement Id */
            requirement_id?: string | null;
            /** Requirement Version */
            requirement_version?: number | null;
        };
        /** Direction */
        Direction: {
            /** Extra Direction */
            extra_direction?: string | null;
            /**
             * Internal Goal Count
             * @default 0
             */
            internal_goal_count: number;
            /** Internal Memos */
            internal_memos?: components["schemas"]["InternalMemo"][];
            /** Key Messages */
            key_messages?: components["schemas"]["KeyMessage"][];
            /** Options */
            options?: components["schemas"]["DirectionOption"][];
            /**
             * Ready
             * @default false
             */
            ready: boolean;
            /** Recommended Option Id */
            recommended_option_id?: string | null;
            /** Selected Option Id */
            selected_option_id?: string | null;
            /**
             * Total
             * @description 정의서 항목 수 N
             * @default 0
             */
            total: number;
        };
        /** DirectionOption */
        DirectionOption: {
            coverage?: components["schemas"]["Coverage"];
            /** Id */
            id: string;
            /** Key */
            key?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "combo" | "axis";
            /** Mapping */
            mapping?: components["schemas"]["MappingRow"][];
            /**
             * One Liner
             * @default
             */
            one_liner: string;
            /** Title */
            title: string;
        };
        /** Discussion */
        Discussion: {
            /** Id */
            id: string;
            /** Label */
            label: string;
            /** N */
            n: number;
            /** Section Ids */
            section_ids?: string[];
            /**
             * Short
             * @default
             */
            short: string;
            /**
             * State
             * @default open
             * @enum {string}
             */
            state: "open" | "resolved";
            /** Trace Item Ids */
            trace_item_ids?: string[];
        };
        /** DocTypeSetting */
        DocTypeSetting: {
            /** Evidence */
            evidence?: string | null;
            /**
             * Source
             * @default default
             * @enum {string}
             */
            source: "rq" | "user" | "default";
            /**
             * Value
             * @default custom
             * @enum {string}
             */
            value: "common_pitch" | "custom";
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
        /** Evidence */
        Evidence: {
            /** Added At */
            added_at?: string | null;
            /** Citations */
            citations?: components["schemas"]["Citation"][];
            /** Id */
            id?: string | null;
            source: components["schemas"]["EvidenceSource"];
            /** Text */
            text: string;
        };
        /** EvidenceSource */
        EvidenceSource: {
            /** Ref Id */
            ref_id: string;
            /** Route */
            route?: string | null;
            /** Service */
            service: string;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** ExportOptions */
        ExportOptions: {
            /**
             * Discussions
             * @default true
             */
            discussions: boolean;
            /**
             * Internal Memo
             * @default false
             */
            internal_memo: boolean;
            /**
             * Trace Appendix
             * @default true
             */
            trace_appendix: boolean;
        };
        /** ExportRequest */
        ExportRequest: {
            /**
             * Format
             * @default pptx
             * @enum {string}
             */
            format: "pptx" | "pdf";
            options?: components["schemas"]["ExportOptions"];
        };
        /** Extension */
        Extension: {
            /**
             * Acknowledged
             * @default false
             */
            acknowledged: boolean;
            /** Derived From Codes */
            derived_from_codes?: string[];
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Places */
            places?: components["schemas"]["Place"][];
            /**
             * Short
             * @default
             */
            short: string;
            /**
             * Status
             * @default extension
             * @enum {string}
             */
            status: "extension" | "reviewing";
            /**
             * Where Label
             * @default
             */
            where_label: string;
        };
        /** Flag */
        Flag: {
            /**
             * Auto Applied
             * @default false
             */
            auto_applied: boolean;
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "unverified_claim" | "internal_goal";
            /** Note */
            note: string;
            /** Original Text */
            original_text?: string | null;
            /**
             * Span
             * @description [start, end] — 지금 문장 기준(빠진 구간이면 빈 배열)
             */
            span?: number[];
            /** Span Text */
            span_text: string;
            /**
             * State
             * @default open
             * @enum {string}
             */
            state: "open" | "applied" | "reverted";
            /** Suggestion */
            suggestion?: string | null;
        };
        /** FollowUp */
        FollowUp: {
            /**
             * Label
             * @default 이어서 하나만
             */
            label: string;
            /** Options */
            options: components["schemas"]["FollowUpOption"][];
            /** Text */
            text: string;
        };
        /** FollowUpOption */
        FollowUpOption: {
            /**
             * Effect
             * @enum {string}
             */
            effect: "use_public" | "internal_only" | "placeholder";
            /** Id */
            id: string;
            /** Label */
            label: string;
        };
        /** Group */
        Group: {
            /** Badges */
            badges?: components["schemas"]["Badge"][];
            /**
             * Key
             * @enum {string}
             */
            key: "start" | "part1" | "part2" | "part3" | "end";
            /**
             * Meta
             * @default
             */
            meta: string;
            /** Name */
            name: string;
            /** Order */
            order: number;
            /** Section Ids */
            section_ids?: string[];
            /**
             * Summary
             * @default
             */
            summary: string;
        };
        /** Handoff */
        Handoff: {
            /** At */
            at: string;
            /** Target */
            target: string;
        };
        /** HandoffCard */
        HandoffCard: {
            /** Description */
            description: string;
            /**
             * Done
             * @default false
             */
            done: boolean;
            /**
             * Emphasized
             * @default false
             */
            emphasized: boolean;
            /** Route */
            route: string;
            /**
             * Target
             * @enum {string}
             */
            target: "proposal" | "mi" | "scenario";
            /** Title */
            title: string;
        };
        /** HandoffCustomer */
        HandoffCustomer: {
            /** Decision Makers */
            decision_makers?: string | null;
            /** Industry Code */
            industry_code?: string | null;
            /** Name */
            name?: string | null;
            /** Scale Text */
            scale_text?: string | null;
        };
        /** HandoffFact */
        HandoffFact: {
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
             * @default placeholder
             * @enum {string}
             */
            status: "confirmed" | "unconfirmed" | "placeholder";
            /** Unit */
            unit?: string | null;
            /** Value */
            value?: string | null;
        };
        /** HandoffItem */
        HandoffItem: {
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
            /** Repeat Key */
            repeat_key?: {
                [key: string]: string;
            } | null;
            /** Sheet Role */
            sheet_role: string;
            /** Sheet Title */
            sheet_title?: string | null;
            /** Sources */
            sources?: {
                [key: string]: unknown;
            }[];
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
        /** HandoffList */
        HandoffList: {
            /** Items */
            items: components["schemas"]["HandoffCard"][];
        };
        /** HandoffResult */
        HandoffResult: {
            /** Route */
            route: string;
        };
        /** HandoffRqRef */
        HandoffRqRef: {
            /** Rq Id */
            rq_id: string;
            /** Version */
            version: number;
        };
        /** HandoffSource */
        HandoffSource: {
            /**
             * Feature
             * @default storyboard
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
        /** HandoffTargetRef */
        HandoffTargetRef: {
            /** Proposal Type */
            proposal_type: string;
            /** Section Key */
            section_key: string;
        };
        /** InternalMemo */
        InternalMemo: {
            /** Flag Id */
            flag_id?: string | null;
            /**
             * From
             * @default flag
             * @enum {string}
             */
            from: "flag" | "rq_author_note";
            /** Text */
            text: string;
        };
        /**
         * JobAccepted
         * @description 202 — 잡을 큐에 넣었다. 진행은 jobs SSE, 결과는 자원을 다시 읽는다.
         */
        JobAccepted: {
            /** Job Id */
            job_id: string;
            /**
             * Ref
             * @description 만들어진 자원 {kind, id}
             */
            ref?: {
                [key: string]: string;
            } | null;
            /**
             * Status
             * @default queued
             * @constant
             */
            status: "queued";
        };
        /** KbRef */
        KbRef: {
            /** Id */
            id: string;
            /** Kind */
            kind: string;
        };
        /** KeyMessage */
        KeyMessage: {
            /**
             * Audience
             * @default
             */
            audience: string;
            /** Axis Key */
            axis_key?: string | null;
            /**
             * Axis Label
             * @default
             */
            axis_label: string;
            /** Evidence */
            evidence?: components["schemas"]["Evidence"][];
            /** Flags */
            flags?: components["schemas"]["Flag"][];
            /** Id */
            id: string;
            /** Kb Refs */
            kb_refs?: string[];
            /** Place Label */
            place_label: string;
            /** Text */
            text: string;
            /**
             * Updated By
             * @default llm
             * @enum {string}
             */
            updated_by: "llm" | "user" | "vp";
        };
        /** KeyMessageList */
        KeyMessageList: {
            /** Items */
            items: components["schemas"]["KeyMessage"][];
        };
        /** LanguageSetting */
        LanguageSetting: {
            /** Evidence */
            evidence?: string | null;
            /**
             * Source
             * @default default
             * @enum {string}
             */
            source: "rq" | "user" | "default";
            /**
             * Value
             * @default ko
             * @enum {string}
             */
            value: "ko" | "en" | "ko_en";
        };
        /** Line */
        Line: {
            /**
             * Claim
             * @description 출처 없는 주장 표현(최초 · 1위 …) — 섹션 확인 필요
             * @default false
             */
            claim: boolean;
            /** Id */
            id: string;
            /**
             * Reviewing
             * @default false
             */
            reviewing: boolean;
            /** Text */
            text: string;
            /** Tokens */
            tokens?: string[];
        };
        /** MappingRow */
        MappingRow: {
            /** Axis Key */
            axis_key: string;
            /**
             * Axis Label
             * @default
             */
            axis_label: string;
            /** Place Label */
            place_label: string;
        };
        /** Ok */
        Ok: {
            /**
             * Ok
             * @default true
             */
            ok: boolean;
        };
        /** Outline */
        Outline: {
            /** Discussions */
            discussions?: components["schemas"]["Discussion"][];
            /** Groups */
            groups?: components["schemas"]["Group"][];
            /**
             * Ready
             * @default false
             */
            ready: boolean;
            /** Sections */
            sections?: components["schemas"]["Section"][];
            /** Spaces */
            spaces?: components["schemas"]["Space"][];
            writing?: components["schemas"]["Writing"] | null;
        };
        /** Owner */
        Owner: {
            /** Id */
            id: string;
            /**
             * Name
             * @default
             */
            name: string;
        };
        /** PatchDirection */
        PatchDirection: {
            /** Extra Direction */
            extra_direction?: string | null;
            /** Selected Option Id */
            selected_option_id?: string | null;
        };
        /** PatchDirectionResult */
        PatchDirectionResult: {
            direction: components["schemas"]["Direction"];
            /** Messages Job Id */
            messages_job_id?: string | null;
        };
        /** PatchKeyMessage */
        PatchKeyMessage: {
            /**
             * Source
             * @description {service: 'vp', ref_id} — VP 가 다듬은 문장을 되돌려 쓸 때
             */
            source?: {
                [key: string]: string;
            } | null;
            /** Text */
            text: string;
        };
        /** PatchStoryboardBody */
        PatchStoryboardBody: {
            /** Name */
            name?: string | null;
            /**
             * Step
             * @description (제안) 사람이 다음 단계로 넘어갈 때 — `요구 추적 확인` → 4, `일정 · 분담으로` → 5
             */
            step?: number | null;
        };
        /** Place */
        Place: {
            /** Id */
            id?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "section" | "space" | "customer_question" | "owner_check";
            /** Label */
            label: string;
        };
        /** PlaceTarget */
        PlaceTarget: {
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "section" | "space";
            /**
             * Label
             * @default
             */
            label: string;
        };
        /** Planning */
        Planning: {
            /** Answers */
            answers?: components["schemas"]["PlanningAnswer"][];
            /** Questions */
            questions?: components["schemas"]["PlanningQuestion"][];
        };
        /** PlanningAnswer */
        PlanningAnswer: {
            /** Answered At */
            answered_at?: string | null;
            /** Custom Text */
            custom_text?: string | null;
            /** Follow Up Option Id */
            follow_up_option_id?: string | null;
            /** Question Id */
            question_id: string;
            /**
             * Roles
             * @description 고른 선택지 → 순서 역할(`Overview 목적` · `Outro 다음 단계`)
             */
            roles?: {
                [key: string]: string;
            };
            /**
             * Selected Option Ids
             * @description 고른 순서
             */
            selected_option_ids?: string[];
            /**
             * Unknown
             * @default false
             */
            unknown: boolean;
        };
        /** PlanningOption */
        PlanningOption: {
            /** Badge */
            badge?: string | null;
            /**
             * Custom
             * @description 직접 입력으로 더한 선택지
             * @default false
             */
            custom: boolean;
            /**
             * Evidence
             * @description 다른 기능에서 받은 근거(예 경쟁사 비교 기준)
             */
            evidence?: string | null;
            follow_up?: components["schemas"]["FollowUp"] | null;
            /** Hint */
            hint?: string | null;
            /** Id */
            id: string;
            /** Label */
            label: string;
            /**
             * Recommended
             * @default false
             */
            recommended: boolean;
        };
        /** PlanningQuestion */
        PlanningQuestion: {
            /** Affects */
            affects?: string[];
            /**
             * Allow Custom
             * @default true
             */
            allow_custom: boolean;
            /** Id */
            id: string;
            /** Info */
            info: string;
            /** Options */
            options: components["schemas"]["PlanningOption"][];
            /** Order */
            order: number;
            /** Order Roles */
            order_roles?: string[];
            /**
             * Select
             * @enum {string}
             */
            select: "multi_ordered" | "single";
            /** Text */
            text: string;
            /**
             * Topic
             * @description decision | audience | comparison | budget_scope | timeline
             */
            topic: string;
            /** Topic Label */
            topic_label: string;
        };
        /** PostDirection */
        PostDirection: {
            /**
             * Skip Planning
             * @default false
             */
            skip_planning: boolean;
        };
        /** PostEvidence */
        PostEvidence: {
            /** Citations */
            citations?: components["schemas"]["Citation"][];
            source: components["schemas"]["EvidenceSource"];
            /** Text */
            text: string;
        };
        /** PostOutlineBody */
        PostOutlineBody: {
            /** Extra Direction */
            extra_direction?: string | null;
            /**
             * Retry
             * @description 실패한 목차 잡 다시 시도 — 이미 쓴 섹션은 건너뛴다
             * @default false
             */
            retry: boolean;
        };
        /** PostRevision */
        PostRevision: {
            /** Chips */
            chips?: string[];
            /**
             * Instruction
             * @default
             */
            instruction: string;
            /**
             * Scope
             * @default target
             * @enum {string}
             */
            scope: "target" | "group";
            target: components["schemas"]["RevisionTarget"];
        };
        /** ProductRef */
        ProductRef: {
            /**
             * Is Extension
             * @default false
             */
            is_extension: boolean;
            kb_ref?: components["schemas"]["KbRef"] | null;
            /** Name */
            name: string;
        };
        /** ProposalHandoff */
        ProposalHandoff: {
            /** Assets */
            assets?: {
                [key: string]: unknown;
            }[];
            customer?: components["schemas"]["HandoffCustomer"] | null;
            /** Facts */
            facts?: components["schemas"]["HandoffFact"][];
            /** Items */
            items?: components["schemas"]["HandoffItem"][];
            /**
             * Key Messages
             * @description Key Message 목록(text · place_label · audience)
             */
            key_messages?: {
                [key: string]: unknown;
            }[];
            /**
             * Live Link
             * @default false
             */
            live_link: boolean;
            rq_ref?: components["schemas"]["HandoffRqRef"] | null;
            source: components["schemas"]["HandoffSource"];
            /**
             * Strategy
             * @description 제안 전략(방향 제목 · 한 줄 · 청중)
             */
            strategy?: {
                [key: string]: unknown;
            } | null;
            target: components["schemas"]["HandoffTargetRef"];
        };
        /** PutPlanningAnswer */
        PutPlanningAnswer: {
            /**
             * Custom Text
             * @description 직접 입력 — 선택지로 더해지고 마지막 순서로 고른다(빈 글이면 뺀다)
             */
            custom_text?: string | null;
            /** Follow Up Option Id */
            follow_up_option_id?: string | null;
            /** Selected Option Ids */
            selected_option_ids?: string[] | null;
            /** Unknown */
            unknown?: boolean | null;
        };
        /** PutRequirement */
        PutRequirement: {
            /** Requirement Id */
            requirement_id: string;
            /** Version */
            version?: number | null;
        };
        /** PutResolution */
        PutResolution: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "place" | "keep_unconfirmed" | "defer_main" | "exclude" | "ask_customer";
            /** Option Id */
            option_id?: string | null;
            /** Reason */
            reason?: string | null;
        };
        /** PutSlot */
        PutSlot: {
            /** Custom Text */
            custom_text?: string | null;
            /** Selected Option Ids */
            selected_option_ids?: string[] | null;
            /** Unknown */
            unknown?: boolean | null;
        };
        /** RequirementRef */
        RequirementRef: {
            /** Customer Name */
            customer_name?: string | null;
            /**
             * Item Count
             * @default 0
             */
            item_count: number;
            /**
             * Latest Version
             * @description 정의서의 최신 저장 버전(새 버전 띠 판단)
             * @default 0
             */
            latest_version: number;
            /**
             * Open Question Count
             * @default 0
             */
            open_question_count: number;
            /** Project Id */
            project_id?: string | null;
            /** Requirement Id */
            requirement_id: string;
            /** Saved At */
            saved_at?: string | null;
            /**
             * Title
             * @default
             */
            title: string;
            /**
             * Version
             * @description 이 스토리보드가 근거로 쓰는 정의서 버전
             */
            version: number;
            /** Version Note */
            version_note?: string | null;
        };
        /** RequirementSyncRequest */
        RequirementSyncRequest: {
            /**
             * Dry Run
             * @default false
             */
            dry_run: boolean;
            /** Reply Id */
            reply_id?: string | null;
            /** Requirement Id */
            requirement_id: string;
            /** To Version */
            to_version?: number | null;
        };
        /** Resolution */
        Resolution: {
            /** At */
            at?: string | null;
            /**
             * Badge
             * @default
             */
            badge: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "place" | "keep_unconfirmed" | "defer_main" | "exclude" | "ask_customer";
            /** Option Id */
            option_id?: string | null;
            /** Reason */
            reason?: string | null;
            /** Result Label */
            result_label: string;
        };
        /** ResolutionResult */
        ResolutionResult: {
            /** Apply Job Id */
            apply_job_id?: string | null;
            item: components["schemas"]["TraceItem"];
        };
        /** RestoreResult */
        RestoreResult: {
            /** Version */
            version: number;
        };
        /** ReviewBody */
        ReviewBody: {
            /** Note */
            note?: string | null;
            /**
             * Reviewers
             * @description 검토자 user id(없으면 workspace 사용자 중 한 명)
             */
            reviewers?: string[] | null;
        };
        /** ReviewRequestResult */
        ReviewRequestResult: {
            /** Review Id */
            review_id?: string | null;
            /**
             * Status
             * @default requested
             */
            status: string;
        };
        /** Revision */
        Revision: {
            /**
             * Base Hash
             * @default
             */
            base_hash: string;
            /**
             * Changed Count
             * @default 0
             */
            changed_count: number;
            /** Chips */
            chips?: string[];
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            /** Id */
            id: string;
            /**
             * Instruction
             * @default
             */
            instruction: string;
            /** Job Id */
            job_id?: string | null;
            /** Rows */
            rows?: components["schemas"]["RevisionRow"][];
            /**
             * Scope
             * @default target
             * @enum {string}
             */
            scope: "target" | "group";
            /**
             * Scope Label
             * @default
             */
            scope_label: string;
            /**
             * Status
             * @default running
             * @enum {string}
             */
            status: "running" | "ready" | "applied" | "discarded" | "failed";
            target: components["schemas"]["RevisionTarget"];
        };
        /** RevisionRow */
        RevisionRow: {
            /** After */
            after?: string | null;
            /** Before */
            before?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "changed" | "added" | "removed" | "kept";
            /** Line Id */
            line_id?: string | null;
            /** Reason */
            reason?: string | null;
            /** Section Label */
            section_label?: string | null;
        };
        /** RevisionTarget */
        RevisionTarget: {
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "section" | "space";
            /**
             * Label
             * @default
             */
            label: string;
        };
        /** RqUpdate */
        RqUpdate: {
            /** Note */
            note?: string | null;
            /** Version */
            version: number;
        };
        /** SaveRequest */
        SaveRequest: {
            /** Note */
            note?: string | null;
        };
        /** SaveResult */
        SaveResult: {
            /** Created */
            created: boolean;
            /** Version */
            version: number;
        };
        /** Schedule */
        Schedule: {
            /**
             * Open Question Count
             * @default 0
             */
            open_question_count: number;
            /** Phases */
            phases?: components["schemas"]["SchedulePhase"][];
            /**
             * Start D
             * @default 21
             */
            start_d: number;
        };
        /** SchedulePhase */
        SchedulePhase: {
            /** Badges */
            badges?: string[];
            /**
             * Current
             * @default false
             */
            current: boolean;
            /** D From */
            d_from: number;
            /** D To */
            d_to: number;
            /** Id */
            id: string;
            /** N */
            n: number;
            /** Name */
            name: string;
            /** Owner */
            owner: string;
            /** Short */
            short: string;
        };
        /** Section */
        Section: {
            /** Code */
            code?: string | null;
            /**
             * Direction
             * @default
             */
            direction: string;
            /** Discussion Ids */
            discussion_ids?: string[];
            /**
             * Group Key
             * @enum {string}
             */
            group_key: "start" | "part1" | "part2" | "part3" | "end";
            /** Id */
            id: string;
            /** Internal Memo */
            internal_memo?: string | null;
            /**
             * Key
             * @description 자리 키(overview · key_considerations · intro · p1_1 … · part2 · p3_1 … · outro · timeline)
             */
            key: string;
            /** Lines */
            lines?: components["schemas"]["Line"][];
            /** Name */
            name: string;
            /** Order */
            order: number;
            /** Products */
            products?: components["schemas"]["ProductRef"][];
            /**
             * Status
             * @default writing
             * @enum {string}
             */
            status: "confirmed" | "reviewing" | "needs_confirmation" | "writing" | "tbd";
            /** Tbd Reason */
            tbd_reason?: string | null;
            /**
             * Written
             * @default true
             */
            written: boolean;
        };
        /** Segment */
        Segment: {
            /**
             * Ai Added
             * @default false
             */
            ai_added: boolean;
            /** Placeholder */
            placeholder?: ("[00]" | "[확인 필요]") | null;
            /** Text */
            text: string;
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
        /** Settings */
        Settings: {
            /**
             * All From Rq
             * @description 4값이 모두 정의서에서 왔다 → `정의서에서 읽었어요`
             * @default false
             */
            all_from_rq: boolean;
            doc_type?: components["schemas"]["DocTypeSetting"];
            language?: components["schemas"]["LanguageSetting"];
            /**
             * Ready
             * @description prepare 가 끝나 값이 채워졌다
             * @default false
             */
            ready: boolean;
            stage?: components["schemas"]["StageSetting"];
            /**
             * Summary
             * @description SB1 설정 줄 — 4값을 ` · ` 로
             * @default
             */
            summary: string;
            volume?: components["schemas"]["VolumeSetting"];
        };
        /** SettingsPatch */
        SettingsPatch: {
            /** Doc Type */
            doc_type?: ("common_pitch" | "custom") | null;
            /** Language */
            language?: ("ko" | "en" | "ko_en") | null;
            /** Stage */
            stage?: ("concept" | "main") | null;
            /** Volume */
            volume?: (12 | 20 | 30) | null;
        };
        /** SettingsResult */
        SettingsResult: {
            settings: components["schemas"]["Settings"];
        };
        /** ShareResult */
        ShareResult: {
            /** Url */
            url: string;
        };
        /** Slot */
        Slot: {
            answer?: components["schemas"]["SlotAnswer"] | null;
            /** Customer Question Id */
            customer_question_id?: string | null;
            /** Segments */
            segments?: components["schemas"]["Segment"][];
            /** Source */
            source?: ("outline" | "answer" | "compose" | "revision" | "rq_sync" | "trace") | null;
            /**
             * State
             * @default empty
             * @enum {string}
             */
            state: "empty" | "filled" | "unknown";
        };
        /** SlotAnswer */
        SlotAnswer: {
            /** Custom Text */
            custom_text?: string | null;
            /** Labels */
            labels?: string[];
            /** Selected Option Ids */
            selected_option_ids?: string[];
        };
        /** SlotQuestion */
        SlotQuestion: {
            /**
             * Allow Custom
             * @default true
             */
            allow_custom: boolean;
            /** Info */
            info: string;
            /** Options */
            options: components["schemas"]["SlotQuestionOption"][];
            /**
             * Select
             * @default multi_ordered
             * @constant
             */
            select: "multi_ordered";
            /**
             * Slot
             * @enum {string}
             */
            slot: "action" | "trigger" | "response" | "exception" | "metric";
            /** Text */
            text: string;
        };
        /** SlotQuestionOption */
        SlotQuestionOption: {
            /** Id */
            id: string;
            /** Label */
            label: string;
        };
        /** Space */
        Space: {
            /**
             * Added Questions
             * @description 이번 질의 · 다듬기로 정의서에 더한 고객 질문
             */
            added_questions?: components["schemas"]["AddedQuestion"][];
            /**
             * Composing
             * @default false
             */
            composing: boolean;
            /** Customer Question Ids */
            customer_question_ids?: string[];
            /**
             * Filled Count
             * @default 0
             */
            filled_count: number;
            /** Id */
            id: string;
            /**
             * Is Extension
             * @default false
             */
            is_extension: boolean;
            /**
             * Key
             * @description 공간 유형(kb space_type 또는 슬러그)
             * @default
             */
            key: string;
            /** Name */
            name: string;
            /** Order */
            order: number;
            /** Products */
            products?: components["schemas"]["ProductRef"][];
            /**
             * Purpose
             * @default
             */
            purpose: string;
            /** Questions */
            questions?: components["schemas"]["SlotQuestion"][];
            /**
             * Slots
             * @description action · trigger · response · exception · metric
             */
            slots?: {
                [key: string]: components["schemas"]["Slot"];
            };
            /**
             * Status
             * @default draft
             * @enum {string}
             */
            status: "empty" | "draft" | "supplemented";
        };
        /** SpaceQuestions */
        SpaceQuestions: {
            /** Questions */
            questions: components["schemas"]["SlotQuestion"][];
        };
        /** SpaceSlotResult */
        SpaceSlotResult: {
            /**
             * Added Questions
             * @description 이번 질의 · 다듬기로 정의서에 더한 고객 질문
             */
            added_questions?: components["schemas"]["AddedQuestion"][];
            /**
             * Composing
             * @default false
             */
            composing: boolean;
            /**
             * Customer Question Id
             * @description `unknown` 이면 정의서에 더한 고객 질문 id
             */
            customer_question_id?: string | null;
            /** Customer Question Ids */
            customer_question_ids?: string[];
            /**
             * Filled Count
             * @default 0
             */
            filled_count: number;
            /** Id */
            id: string;
            /**
             * Is Extension
             * @default false
             */
            is_extension: boolean;
            /**
             * Key
             * @description 공간 유형(kb space_type 또는 슬러그)
             * @default
             */
            key: string;
            /** Name */
            name: string;
            /** Order */
            order: number;
            /** Products */
            products?: components["schemas"]["ProductRef"][];
            /**
             * Purpose
             * @default
             */
            purpose: string;
            /** Questions */
            questions?: components["schemas"]["SlotQuestion"][];
            /**
             * Slots
             * @description action · trigger · response · exception · metric
             */
            slots?: {
                [key: string]: components["schemas"]["Slot"];
            };
            /**
             * Status
             * @default draft
             * @enum {string}
             */
            status: "empty" | "draft" | "supplemented";
        };
        /** StageSetting */
        StageSetting: {
            /** Evidence */
            evidence?: string | null;
            /**
             * Source
             * @default default
             * @enum {string}
             */
            source: "rq" | "user" | "default";
            /**
             * Value
             * @default concept
             * @enum {string}
             */
            value: "concept" | "main";
        };
        /** Storyboard */
        Storyboard: {
            active_job?: components["schemas"]["ActiveJob"] | null;
            /**
             * Changes
             * @description 최신 저장 버전 이후 변경
             */
            changes?: components["schemas"]["ChangeEntry"][];
            /**
             * Counts
             * @description needs_confirmation · tbd · sections · spaces_empty · unknown_answers
             */
            counts?: {
                [key: string]: number;
            };
            /** Created At */
            created_at: string;
            /** Customer Name */
            customer_name?: string | null;
            direction?: components["schemas"]["Direction"] | null;
            /**
             * Draft Label
             * @default
             */
            draft_label: string;
            /**
             * Exported
             * @default false
             */
            exported: boolean;
            /** Handoffs */
            handoffs?: components["schemas"]["Handoff"][];
            /**
             * Has Unsaved Changes
             * @default true
             */
            has_unsaved_changes: boolean;
            /** Id */
            id: string;
            /** Name */
            name: string;
            outline?: components["schemas"]["Outline"] | null;
            owner: components["schemas"]["Owner"];
            planning?: components["schemas"]["Planning"];
            /** Prepare Job Id */
            prepare_job_id?: string | null;
            /** Project Id */
            project_id?: string | null;
            requirement_ref?: components["schemas"]["RequirementRef"] | null;
            /**
             * Review Requested
             * @default false
             */
            review_requested: boolean;
            /**
             * Revision
             * @description 작업본 내용이 바뀔 때마다 +1
             * @default 0
             */
            revision: number;
            /**
             * Route
             * @default
             */
            route: string;
            /** @description 반영 요청 없이 저장된 정의서 새 버전(SB3 띠) */
            rq_update?: components["schemas"]["RqUpdate"] | null;
            schedule?: components["schemas"]["Schedule"];
            settings?: components["schemas"]["Settings"];
            /**
             * Started
             * @default false
             */
            started: boolean;
            /**
             * Status
             * @default in_progress
             * @enum {string}
             */
            status: "in_progress" | "done" | "shared";
            /**
             * Step
             * @default 1
             */
            step: number;
            /**
             * Step Label
             * @default
             */
            step_label: string;
            /**
             * Sub Line
             * @default
             */
            sub_line: string;
            /** Title */
            title: string;
            trace?: components["schemas"]["Trace"] | null;
            /** Updated At */
            updated_at: string;
            /**
             * Version
             * @description 저장한 스토리보드 버전(0 = 아직 없음)
             * @default 0
             */
            version: number;
        };
        /** StoryboardCounts */
        StoryboardCounts: {
            /** All */
            all: number;
            /** Done */
            done: number;
            /** In Progress */
            in_progress: number;
        };
        /** StoryboardList */
        StoryboardList: {
            /** Items */
            items: components["schemas"]["StoryboardListItem"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** StoryboardListItem */
        StoryboardListItem: {
            active_job?: components["schemas"]["ActiveJob"] | null;
            /**
             * Cta
             * @enum {string}
             */
            cta: "continue" | "view" | "open";
            /** Customer Name */
            customer_name?: string | null;
            /** Id */
            id: string;
            /** Requirement Id */
            requirement_id?: string | null;
            /** Route */
            route: string;
            /**
             * Status
             * @enum {string}
             */
            status: "in_progress" | "done" | "shared";
            /** Status Label */
            status_label: string;
            /** Step */
            step: number;
            /** Step Label */
            step_label: string;
            /** Sub Line */
            sub_line: string;
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
        };
        /** StoryboardVersion */
        StoryboardVersion: {
            /** Causes */
            causes?: string[];
            /** Created At */
            created_at: string;
            /** Created By */
            created_by?: string | null;
            /** Note */
            note?: string | null;
            /**
             * Reason
             * @default save
             * @enum {string}
             */
            reason: "save" | "restore";
            /** Snapshot */
            snapshot: {
                [key: string]: unknown;
            };
            /** Version */
            version: number;
        };
        /** SyncPreview */
        SyncPreview: {
            /** Causes */
            causes?: string[];
            /**
             * Count
             * @default 0
             */
            count: number;
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            /** From Rq Version */
            from_rq_version: number;
            /**
             * From Version
             * @description 미리 보기의 기준 스토리보드 버전(v{a})
             * @default 0
             */
            from_version: number;
            /** Id */
            id: string;
            /** Reply Id */
            reply_id?: string | null;
            /** Requirement Id */
            requirement_id: string;
            /** Rows */
            rows?: components["schemas"]["ChangeEntry"][];
            /**
             * Status
             * @default running
             * @enum {string}
             */
            status: "running" | "ready" | "failed";
            /** To Rq Version */
            to_rq_version?: number | null;
        };
        /** Trace */
        Trace: {
            /** Computed At */
            computed_at?: string | null;
            /** Extensions */
            extensions?: components["schemas"]["Extension"][];
            /**
             * Extensions Acknowledged
             * @default false
             */
            extensions_acknowledged: boolean;
            /** Items */
            items?: components["schemas"]["TraceItem"][];
            /**
             * Ok Count
             * @default 0
             */
            ok_count: number;
            /**
             * Stale
             * @default false
             */
            stale: boolean;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** TraceItem */
        TraceItem: {
            /** Code */
            code: string;
            /** Link Types */
            link_types?: ("direct" | "interpreted" | "extension" | "reviewing" | "unconfirmed" | "deferred" | "excluded")[];
            /**
             * Needs Confirmation
             * @default false
             */
            needs_confirmation: boolean;
            /** Owner Note */
            owner_note?: string | null;
            /** Places */
            places?: components["schemas"]["Place"][];
            /** Places Label */
            places_label?: string | null;
            /**
             * Priority
             * @default 0
             */
            priority: number;
            /** Problem */
            problem?: ("no_place" | "empty_content") | null;
            question?: components["schemas"]["TraceQuestion"] | null;
            resolution?: components["schemas"]["Resolution"] | null;
            /** Rq Item Id */
            rq_item_id: string;
            /**
             * Short
             * @default
             */
            short: string;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "to_resolve" | "owner_check" | "resolved";
            /**
             * Text
             * @default
             */
            text: string;
        };
        /** TraceOption */
        TraceOption: {
            /**
             * Hint
             * @default
             */
            hint: string;
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "place" | "keep_unconfirmed" | "defer_main" | "exclude";
            /** Label */
            label: string;
            target?: components["schemas"]["PlaceTarget"] | null;
        };
        /** TraceQuestion */
        TraceQuestion: {
            /**
             * Info
             * @default
             */
            info: string;
            /** Options */
            options: components["schemas"]["TraceOption"][];
            /** Recommended Option Id */
            recommended_option_id?: string | null;
            /** Text */
            text: string;
        };
        /** VersionList */
        VersionList: {
            /** Items */
            items: components["schemas"]["VersionSummary"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** VersionSummary */
        VersionSummary: {
            /** Causes */
            causes?: string[];
            /** Created At */
            created_at: string;
            /** Created By */
            created_by?: string | null;
            /** Note */
            note?: string | null;
            /**
             * Reason
             * @default save
             * @enum {string}
             */
            reason: "save" | "restore";
            /** Version */
            version: number;
        };
        /** VolumeSetting */
        VolumeSetting: {
            /**
             * Evidence
             * @description 분량 힌트(공간 수 규칙) — 예 `7개 공간을 담으려면 20장 이상`
             */
            evidence?: string | null;
            /**
             * Source
             * @default default
             * @enum {string}
             */
            source: "rq" | "user" | "default";
            /**
             * Value
             * @default 20
             * @enum {integer}
             */
            value: 12 | 20 | 30;
        };
        /** Writing */
        Writing: {
            /**
             * Done
             * @default 0
             */
            done: number;
            /** Stage */
            stage?: string | null;
            /**
             * Total
             * @default 0
             */
            total: number;
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
    list_storyboards: {
        parameters: {
            query?: {
                cursor?: string | null;
                /** @description 고객사 부분 일치(제안서 PR1 `최근 Storyboard` 카드) */
                customer?: string | null;
                limit?: number;
                q?: string | null;
                tab?: "all" | "in_progress" | "done";
                /** @description ISO 시각 이후 수정된 것만 */
                updated_after?: string | null;
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
                    "application/json": components["schemas"]["StoryboardList"];
                };
            };
        };
    };
    create_storyboard: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateStoryboard"];
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
            /** @description 내 시작 전 초안을 다시 씀 */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Storyboard"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Storyboard"];
                };
            };
        };
    };
    get_storyboard: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["Storyboard"];
                };
            };
        };
    };
    patch_storyboard: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchStoryboardBody"];
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
                    "application/json": components["schemas"]["Storyboard"];
                };
            };
        };
    };
    revert_change: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                chg: string;
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["Storyboard"];
                };
            };
        };
    };
    compare: {
        parameters: {
            query?: {
                from?: number | null;
                /** @description 버전 번호 또는 draft(작업본) */
                to?: string | null;
            };
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["Compare"];
                };
            };
        };
    };
    get_direction: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["Direction"];
                };
            };
        };
    };
    start_direction: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PostDirection"] | null;
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
    patch_direction: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchDirection"];
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
                    "application/json": components["schemas"]["PatchDirectionResult"];
                };
            };
        };
    };
    discussions_agenda: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["AgendaText"];
                };
            };
        };
    };
    start_export: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ExportRequest"];
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
    list_handoffs: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
    record_handoff: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
                target: "proposal" | "mi" | "scenario";
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
                    "application/json": components["schemas"]["HandoffResult"];
                };
            };
        };
    };
    import_competitor: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CompetitorImport"];
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
                    "application/json": components["schemas"]["CompetitorImportResult"];
                };
            };
        };
    };
    list_key_messages: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["KeyMessageList"];
                };
            };
        };
    };
    patch_key_message: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kmsg: string;
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchKeyMessage"];
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
                    "application/json": components["schemas"]["KeyMessage"];
                };
            };
        };
    };
    add_evidence: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                kmsg: string;
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PostEvidence"];
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
                    "application/json": components["schemas"]["KeyMessage"];
                };
            };
        };
    };
    apply_flag: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                flg: string;
                kmsg: string;
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["KeyMessage"];
                };
            };
        };
    };
    revert_flag: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                flg: string;
                kmsg: string;
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["KeyMessage"];
                };
            };
        };
    };
    get_outline: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["Outline"];
                };
            };
        };
    };
    start_outline: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PostOutlineBody"] | null;
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
    get_planning: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["Planning"];
                };
            };
        };
    };
    answer_planning: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                qid: string;
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PutPlanningAnswer"];
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
                    "application/json": components["schemas"]["PlanningAnswer"];
                };
            };
        };
    };
    prepare: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
    proposal_handoff: {
        parameters: {
            query?: {
                /** @description vp · mi · why · space_scenario …(없으면 전부) */
                section?: string | null;
                /** @description standard · quickwin · solution */
                type?: string;
            };
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
    put_requirement: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PutRequirement"];
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
    requirement_sync: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RequirementSyncRequest"];
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
    review_request: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["ReviewBody"] | null;
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
                    "application/json": components["schemas"]["ReviewRequestResult"];
                };
            };
        };
    };
    create_revision: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PostRevision"];
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
    get_revision: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                rev: string;
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["Revision"];
                };
            };
        };
    };
    apply_revision: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                rev: string;
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["Storyboard"];
                };
            };
        };
    };
    discard_revision: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                rev: string;
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["Revision"];
                };
            };
        };
    };
    save: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
            /** @description 바뀐 것이 없어 버전 그대로(created=false) */
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
    get_schedule: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["Schedule"];
                };
            };
        };
    };
    patch_settings: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SettingsPatch"];
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
                    "application/json": components["schemas"]["SettingsResult"];
                };
            };
        };
    };
    share: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
    get_space: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
                spc: string;
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
                    "application/json": components["schemas"]["Space"];
                };
            };
        };
    };
    compose_space: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
                spc: string;
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
    space_questions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
                spc: string;
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
                    "application/json": components["schemas"]["SpaceQuestions"];
                };
            };
            /** @description 잡을 큐에 넣었다 — 진행은 jobs SSE */
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
    put_slot: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
                /** @description action · trigger · response · exception · metric */
                slot: string;
                spc: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PutSlot"];
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
                    "application/json": components["schemas"]["SpaceSlotResult"];
                };
            };
        };
    };
    get_sync_preview: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
                syp: string;
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
                    "application/json": components["schemas"]["SyncPreview"];
                };
            };
        };
    };
    get_trace: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["Trace"];
                };
            };
        };
    };
    acknowledge_extensions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["Ok"];
                };
            };
        };
    };
    put_resolution: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                rq_item_id: string;
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PutResolution"];
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
                    "application/json": components["schemas"]["ResolutionResult"];
                };
            };
        };
    };
    list_versions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                n: number;
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
                    "application/json": components["schemas"]["StoryboardVersion"];
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
                /** @description 스토리보드 id(sb_…) */
                sb_id: string;
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
    storyboard_counts: {
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
                    "application/json": components["schemas"]["StoryboardCounts"];
                };
            };
        };
    };
}
