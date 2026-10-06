// 자동 생성 — 직접 고치지 말 것. 원본: contracts/workspace.json (make contracts)
export interface paths {
    "/v1/asset-usage": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Asset Usage */
        get: operations["asset_usage"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/asset-usage/{ref}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Record Asset Use */
        put: operations["record_asset_use"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/auth/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Verify */
        post: operations["verify"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/comments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Comments */
        get: operations["list_comments"];
        put?: never;
        /** Add Comment */
        post: operations["add_comment"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/comments/{comment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Comment */
        delete: operations["delete_comment"];
        options?: never;
        head?: never;
        /** Patch Comment */
        patch: operations["patch_comment"];
        trace?: never;
    };
    "/v1/items": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Items */
        get: operations["list_items"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/items/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Item */
        get: operations["get_item"];
        /** Upsert Item */
        put: operations["upsert_item"];
        post?: never;
        /** Delete Item */
        delete: operations["delete_item"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/items/counts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Item Counts */
        get: operations["item_counts"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Me */
        get: operations["get_me"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Me */
        patch: operations["patch_me"];
        trace?: never;
    };
    "/v1/me/password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Change My Password */
        post: operations["change_my_password"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/notifications": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Notifications */
        get: operations["list_notifications"];
        put?: never;
        /** Create Notification */
        post: operations["create_notification"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/notifications/counts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Notification Counts
         * @description 읽지 않은 알림 수 — 전체 · 작업물별(사이드바 배지).
         */
        get: operations["notification_counts"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/notifications/read": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Mark Read
         * @description 읽음 표시 — ids · item_id 가 없으면 내 알림 전부.
         */
        post: operations["mark_read"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/projects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Projects */
        get: operations["list_projects"];
        put?: never;
        /** Create Project */
        post: operations["create_project"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/projects/{project_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Project */
        get: operations["get_project"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Project */
        patch: operations["patch_project"];
        trace?: never;
    };
    "/v1/reviews": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Reviews */
        get: operations["list_reviews"];
        put?: never;
        /** Request Review */
        post: operations["request_review"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/reviews/{review_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Review */
        get: operations["get_review"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Review */
        patch: operations["patch_review"];
        trace?: never;
    };
    "/v1/reviews/{review_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Review */
        post: operations["cancel_review"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/reviews/{review_id}/checks/{target_ref}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Put Check
         * @description 검토자가 대상(시트 등) 하나를 확인했다(`ok`) · 고칠 게 있다(`need`). 같은 검토자 · 대상이면 바꾼다.
         */
        put: operations["put_check"];
        post?: never;
        /**
         * Delete Check
         * @description 내 확인 지우기.
         */
        delete: operations["delete_check"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/reviews/{review_id}/decision": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Decide */
        post: operations["decide"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/reviews/{review_id}/resubmit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Resubmit
         * @description 다시 요청 — 같은 검토의 라운드 +1, 결정 · 확인 초기화(지난 라운드는 rounds[] 에).
         */
        post: operations["resubmit"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/share-links": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Share */
        post: operations["create_share"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/share-links/{token}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Resolve Share */
        get: operations["resolve_share"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/users": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Users */
        get: operations["list_users"];
        put?: never;
        /** Create User */
        post: operations["create_user"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/users/{user_id}": {
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
        /** Patch User */
        patch: operations["patch_user"];
        trace?: never;
    };
    "/v1/users/{user_id}/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** User Status */
        get: operations["user_status"];
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
        /** AssetUsage */
        AssetUsage: {
            /** Proposals */
            proposals: number;
            /** Ref */
            ref: string;
            /** Uses */
            uses?: components["schemas"]["AssetUseBody"][];
        };
        /** AssetUsageList */
        AssetUsageList: {
            /** Items */
            items: components["schemas"]["AssetUsage"][];
        };
        /** AssetUseBody */
        AssetUseBody: {
            /** Proposal Id */
            proposal_id: string;
            /** Sheet Id */
            sheet_id?: string | null;
        };
        /** Comment */
        Comment: {
            /** Anchor */
            anchor?: {
                [key: string]: unknown;
            } | null;
            /** Author */
            author: string;
            /** Author Name */
            author_name: string;
            /** Body */
            body: string;
            /** Created At */
            created_at: string;
            /** Id */
            id: string;
            /** Parent Id */
            parent_id?: string | null;
            /**
             * Resolved
             * @default false
             */
            resolved: boolean;
            /** Target */
            target: string;
            /** Updated At */
            updated_at: string;
        };
        /** CommentBody */
        CommentBody: {
            /**
             * Anchor
             * @description 화면 위치 등 기능별 앵커
             */
            anchor?: {
                [key: string]: unknown;
            } | null;
            /** Body */
            body: string;
            /** Parent Id */
            parent_id?: string | null;
            /**
             * Target
             * @description 대상 참조(예: proposal:pr_…:sheet:sh_…)
             */
            target: string;
        };
        /** CommentList */
        CommentList: {
            /** Items */
            items: components["schemas"]["Comment"][];
        };
        /** CommentPatch */
        CommentPatch: {
            /** Body */
            body?: string | null;
            /** Resolved */
            resolved?: boolean | null;
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
        /** FeatureCount */
        FeatureCount: {
            /** Count */
            count: number;
            /**
             * Feature
             * @enum {string}
             */
            feature: "RQ" | "SB" | "IMG" | "BE" | "SC" | "MI" | "CA" | "VP" | "SP" | "PR";
        };
        /** Item */
        Item: {
            /** Created At */
            created_at: string;
            /**
             * Feature
             * @enum {string}
             */
            feature: "RQ" | "SB" | "IMG" | "BE" | "SC" | "MI" | "CA" | "VP" | "SP" | "PR";
            /** Item Id */
            item_id: string;
            /** Meta */
            meta?: {
                [key: string]: unknown;
            } | null;
            /** Owner */
            owner: string;
            /**
             * Owner Name
             * @default
             */
            owner_name: string;
            /** Project Id */
            project_id?: string | null;
            /** Route */
            route: string;
            /** Status */
            status: string;
            /** Summary */
            summary?: string | null;
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
        };
        /** ItemBody */
        ItemBody: {
            /**
             * Feature
             * @enum {string}
             */
            feature: "RQ" | "SB" | "IMG" | "BE" | "SC" | "MI" | "CA" | "VP" | "SP" | "PR";
            /** Meta */
            meta?: {
                [key: string]: unknown;
            } | null;
            /** Project Id */
            project_id?: string | null;
            /**
             * Route
             * @description 웹 경로(예: /requirements/rq_…)
             */
            route: string;
            /**
             * Status
             * @description 기능별 상태(draft · generating · done · …)
             */
            status: string;
            /** Summary */
            summary?: string | null;
            /** Title */
            title: string;
        };
        /** ItemCounts */
        ItemCounts: {
            /** Items */
            items: components["schemas"]["FeatureCount"][];
        };
        /** ItemList */
        ItemList: {
            /** Items */
            items: components["schemas"]["Item"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** ItemUnread */
        ItemUnread: {
            /** Feature */
            feature?: ("RQ" | "SB" | "IMG" | "BE" | "SC" | "MI" | "CA" | "VP" | "SP" | "PR") | null;
            /** Item Id */
            item_id: string;
            /** Unread */
            unread: number;
        };
        /** Me */
        Me: {
            /** Given Name */
            given_name: string;
            /**
             * Has Password
             * @description 로그인 비밀번호가 있는 계정
             * @default false
             */
            has_password: boolean;
            /** Initial */
            initial: string;
            /** Name */
            name: string;
            /**
             * Org
             * @default
             */
            org: string;
            /**
             * Role
             * @default member
             */
            role: string;
            /**
             * Timezone
             * @default Asia/Seoul
             */
            timezone: string;
            /** User Id */
            user_id: string;
            /**
             * Username
             * @description 로그인 아이디(AUTH_MODE=local 계정)
             */
            username?: string | null;
        };
        /** MePatch */
        MePatch: {
            /** Name */
            name?: string | null;
            /** Org */
            org?: string | null;
        };
        /** Notification */
        Notification: {
            /** By */
            by?: string | null;
            /** By Name */
            by_name?: string | null;
            /** Created At */
            created_at: string;
            /** Data */
            data?: {
                [key: string]: unknown;
            } | null;
            /** Id */
            id: string;
            item?: components["schemas"]["NotificationItemRef"] | null;
            /** Message */
            message?: string | null;
            /**
             * Read
             * @default false
             */
            read: boolean;
            /** Read At */
            read_at?: string | null;
            /** Recipient */
            recipient: string;
            /** Ref */
            ref?: string | null;
            /** Route */
            route?: string | null;
            /** Service */
            service?: string | null;
            /** Title */
            title: string;
            /** Type */
            type: string;
        };
        /** NotificationBody */
        NotificationBody: {
            /** Data */
            data?: {
                [key: string]: unknown;
            } | null;
            /**
             * Exclude Actor
             * @description 지금 사용자(요청한 사람)는 빼기
             * @default false
             */
            exclude_actor: boolean;
            /**
             * Item Id
             * @description 작업물 색인 id(제안서 id 등) — 그 항목 주인에게 가고 사이드바 그 항목에 배지가 붙는다
             */
            item_id?: string | null;
            /** Message */
            message?: string | null;
            /**
             * Notify Owner
             * @description 항목 주인에게도 보내기
             * @default true
             */
            notify_owner: boolean;
            /**
             * Recipients
             * @description 더 받을 사용자 id
             */
            recipients?: string[];
            /**
             * Ref
             * @description 원인 자원 참조(예: sp_…)
             */
            ref?: string | null;
            /**
             * Route
             * @description 눌렀을 때 갈 웹 경로(없으면 항목 route)
             */
            route?: string | null;
            /**
             * Service
             * @description 보낸 서비스(없으면 호출 서비스)
             */
            service?: string | null;
            /** Title */
            title: string;
            /**
             * Type
             * @description 알림 종류(예: spec_link_changed)
             * @default item_updated
             */
            type: string;
        };
        /** NotificationCounts */
        NotificationCounts: {
            /** Items */
            items: components["schemas"]["ItemUnread"][];
            /** Unread */
            unread: number;
        };
        /** NotificationItemRef */
        NotificationItemRef: {
            /** Feature */
            feature?: ("RQ" | "SB" | "IMG" | "BE" | "SC" | "MI" | "CA" | "VP" | "SP" | "PR") | null;
            /** Id */
            id: string;
        };
        /** NotificationList */
        NotificationList: {
            /** Items */
            items: components["schemas"]["Notification"][];
            /** Next Cursor */
            next_cursor?: string | null;
            /**
             * Unread
             * @default 0
             */
            unread: number;
        };
        /** PasswordBody */
        PasswordBody: {
            /**
             * Current Password
             * @description 지금 비밀번호(비밀번호가 있는 계정이면 필수)
             */
            current_password?: string | null;
            /** New Password */
            new_password: string;
        };
        /** Project */
        Project: {
            /** Created At */
            created_at: string;
            /** Customer */
            customer?: string | null;
            /** Id */
            id: string;
            /** Industry */
            industry?: string | null;
            /** Name */
            name: string;
            /** Note */
            note?: string | null;
            /** Owner */
            owner: string;
            /** Updated At */
            updated_at: string;
        };
        /** ProjectBody */
        ProjectBody: {
            /** Customer */
            customer?: string | null;
            /** Industry */
            industry?: string | null;
            /** Name */
            name: string;
            /** Note */
            note?: string | null;
        };
        /** ProjectList */
        ProjectList: {
            /** Items */
            items: components["schemas"]["Project"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** ReadBody */
        ReadBody: {
            /**
             * Ids
             * @description 이 알림들만
             */
            ids?: string[] | null;
            /**
             * Item Id
             * @description 이 작업물의 알림 전부
             */
            item_id?: string | null;
        };
        /** ReadResult */
        ReadResult: {
            /** Updated */
            updated: number;
        };
        /** ResubmitBody */
        ResubmitBody: {
            /**
             * Due Date
             * @description 새 마감일(없으면 그대로)
             */
            due_date?: string | null;
            /** Message */
            message?: string | null;
            /** Version Label */
            version_label?: string | null;
        };
        /** Review */
        Review: {
            /** Approvals */
            approvals: number;
            /**
             * Checks
             * @description 이번 라운드의 검토자별 대상 확인
             */
            checks?: components["schemas"]["ReviewCheck"][];
            /** Created At */
            created_at: string;
            /** Due Date */
            due_date?: string | null;
            /** Id */
            id: string;
            /** Item Id */
            item_id?: string | null;
            /** Message */
            message?: string | null;
            /**
             * Requested At
             * @description 이번 라운드 요청 시각
             */
            requested_at?: string | null;
            /** Requester */
            requester: string;
            /** Requester Name */
            requester_name: string;
            /** Required Approvals */
            required_approvals: number;
            /** Reviewers */
            reviewers: components["schemas"]["ReviewerState"][];
            /**
             * Round
             * @default 1
             */
            round: number;
            /**
             * Rounds
             * @description 지난 라운드 기록(오래된 것부터)
             */
            rounds?: components["schemas"]["ReviewRound"][];
            /** Route */
            route: string;
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "approved" | "changes_requested" | "canceled";
            /** Target */
            target: string;
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
            /** Version Label */
            version_label?: string | null;
        };
        /** ReviewBody */
        ReviewBody: {
            /**
             * Due Date
             * @description 마감일 YYYY-MM-DD(선택) — 「마감 10월 8일 (목)」 · 알림 D-n
             */
            due_date?: string | null;
            /**
             * Item Id
             * @description 작업물 색인 id(없으면 target 두 번째 조각이 색인에 있으면 그것) — 알림이 붙는 항목
             */
            item_id?: string | null;
            /** Message */
            message?: string | null;
            /**
             * Required Approvals
             * @default 1
             */
            required_approvals: number;
            /**
             * Reviewers
             * @description 검토자 user id
             */
            reviewers: string[];
            /**
             * Route
             * @description 검토 화면 웹 경로
             */
            route: string;
            /**
             * Target
             * @description 검토 대상(예: proposal:pr_…:v3)
             */
            target: string;
            /** Title */
            title: string;
            /**
             * Version Label
             * @description 검토하는 판(예: v3) — 라운드 기록에 남김
             */
            version_label?: string | null;
        };
        /** ReviewCheck */
        ReviewCheck: {
            /** At */
            at: string;
            /** Comment */
            comment?: string | null;
            /**
             * Name
             * @default
             */
            name: string;
            /**
             * Round
             * @default 1
             */
            round: number;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "need";
            /**
             * Target Ref
             * @description 확인한 대상(예: 시트 id)
             */
            target_ref: string;
            /** User Id */
            user_id: string;
        };
        /** ReviewCheckBody */
        ReviewCheckBody: {
            /** Comment */
            comment?: string | null;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "need";
        };
        /** ReviewDecisionBody */
        ReviewDecisionBody: {
            /** Comment */
            comment?: string | null;
            /**
             * Decision
             * @enum {string}
             */
            decision: "approve" | "request_changes";
        };
        /** ReviewerState */
        ReviewerState: {
            /** Comment */
            comment?: string | null;
            /** Decided At */
            decided_at?: string | null;
            /**
             * Decision
             * @default pending
             * @enum {string}
             */
            decision: "pending" | "approve" | "request_changes";
            /**
             * Name
             * @default
             */
            name: string;
            /** User Id */
            user_id: string;
        };
        /** ReviewList */
        ReviewList: {
            /** Items */
            items: components["schemas"]["Review"][];
        };
        /** ReviewPatch */
        ReviewPatch: {
            /**
             * Clear Due Date
             * @description 마감일 지우기
             * @default false
             */
            clear_due_date: boolean;
            /** Due Date */
            due_date?: string | null;
            /** Message */
            message?: string | null;
            /** Title */
            title?: string | null;
        };
        /** ReviewRound */
        ReviewRound: {
            /** Checks */
            checks?: components["schemas"]["ReviewCheck"][];
            /** Message */
            message?: string | null;
            /** Requested At */
            requested_at?: string | null;
            /** Reviewers */
            reviewers?: components["schemas"]["ReviewerState"][];
            /** Round */
            round: number;
            /**
             * Status
             * @description 다시 요청할 때의 상태(changes_requested 등)
             */
            status: string;
            /** Version Label */
            version_label?: string | null;
        };
        /** ShareBody */
        ShareBody: {
            /**
             * Expires Days
             * @default 30
             */
            expires_days: number | null;
            /**
             * Route
             * @description 보기 전용 화면 웹 경로
             */
            route: string;
            /** Target */
            target: string;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** ShareLink */
        ShareLink: {
            /** Created At */
            created_at: string;
            /** Created By */
            created_by: string;
            /** Expires At */
            expires_at?: string | null;
            /** Id */
            id: string;
            /** Route */
            route: string;
            /** Target */
            target: string;
            /**
             * Title
             * @default
             */
            title: string;
            /** Token */
            token: string;
            /**
             * Url
             * @description 게이트웨이 기준 상대 경로(/share/<token>)
             */
            url: string;
        };
        /** UserCreate */
        UserCreate: {
            /** Name */
            name: string;
            /**
             * Org
             * @default
             */
            org: string;
            /** Password */
            password: string;
            /**
             * Role
             * @default member
             * @enum {string}
             */
            role: "admin" | "member";
            /** Username */
            username: string;
        };
        /** UserList */
        UserList: {
            /** Items */
            items: components["schemas"]["UserOut"][];
        };
        /** UserOut */
        UserOut: {
            /** Created At */
            created_at?: string | null;
            /**
             * Disabled
             * @default false
             */
            disabled: boolean;
            /**
             * Has Password
             * @description 로그인 비밀번호가 있는 계정(AUTH_MODE=none 에서 자동으로 생긴 프로필은 없음)
             * @default false
             */
            has_password: boolean;
            /** Id */
            id: string;
            /** Last Login At */
            last_login_at?: string | null;
            /** Name */
            name: string;
            /**
             * Org
             * @default
             */
            org: string;
            /**
             * Role
             * @default member
             */
            role: string;
            /** Username */
            username: string;
        };
        /** UserPatch */
        UserPatch: {
            /**
             * Disabled
             * @description 사용 중지(로그인 불가)
             */
            disabled?: boolean | null;
            /** Name */
            name?: string | null;
            /** Org */
            org?: string | null;
            /**
             * Password
             * @description 비밀번호 재설정(관리자)
             */
            password?: string | null;
            /** Role */
            role?: ("admin" | "member") | null;
        };
        /**
         * UserStatus
         * @description 게이트웨이 전용(internal) — 세션 다시 확인(사용 중지 · 비밀번호 재설정 뒤 기존 세션 끊기).
         */
        UserStatus: {
            /**
             * Disabled
             * @default false
             */
            disabled: boolean;
            /** Exists */
            exists: boolean;
            /** Id */
            id: string;
            /** Password Changed At */
            password_changed_at?: string | null;
        };
        /** VerifiedUser */
        VerifiedUser: {
            /** Id */
            id: string;
            /** Name */
            name: string;
        };
        /** VerifyBody */
        VerifyBody: {
            /** Password */
            password: string;
            /** Username */
            username: string;
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
    asset_usage: {
        parameters: {
            query: {
                /** @description 쉼표로 구분한 참조 목록 */
                refs: string;
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
                    "application/json": components["schemas"]["AssetUsageList"];
                };
            };
        };
    };
    record_asset_use: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                ref: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssetUseBody"];
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
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    verify: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VerifyBody"];
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
                    "application/json": components["schemas"]["VerifiedUser"];
                };
            };
        };
    };
    list_comments: {
        parameters: {
            query: {
                /** @description 대상 참조(접두 일치: target* 는 하위 전부) */
                target: string;
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
                    "application/json": components["schemas"]["CommentList"];
                };
            };
        };
    };
    add_comment: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CommentBody"];
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
                    "application/json": components["schemas"]["Comment"];
                };
            };
        };
    };
    delete_comment: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                comment_id: string;
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
    patch_comment: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                comment_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CommentPatch"];
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
                    "application/json": components["schemas"]["Comment"];
                };
            };
        };
    };
    list_items: {
        parameters: {
            query?: {
                cursor?: string | null;
                feature?: ("RQ" | "SB" | "IMG" | "BE" | "SC" | "MI" | "CA" | "VP" | "SP" | "PR") | null;
                limit?: number;
                /** @description me | all | <user id> */
                owner?: string;
                project_id?: string | null;
                /** @description 제목 포함 검색 */
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
                    "application/json": components["schemas"]["ItemList"];
                };
            };
        };
    };
    get_item: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
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
                    "application/json": components["schemas"]["Item"];
                };
            };
        };
    };
    upsert_item: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ItemBody"];
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
                    "application/json": components["schemas"]["Item"];
                };
            };
        };
    };
    delete_item: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
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
    item_counts: {
        parameters: {
            query?: {
                owner?: string;
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
                    "application/json": components["schemas"]["ItemCounts"];
                };
            };
        };
    };
    get_me: {
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
                    "application/json": components["schemas"]["Me"];
                };
            };
        };
    };
    patch_me: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MePatch"];
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
                    "application/json": components["schemas"]["Me"];
                };
            };
        };
    };
    change_my_password: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordBody"];
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
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    list_notifications: {
        parameters: {
            query?: {
                cursor?: string | null;
                /** @description 이 작업물의 알림만 */
                item_id?: string | null;
                limit?: number;
                /** @description 읽지 않은 것만 */
                unread_only?: boolean;
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
                    "application/json": components["schemas"]["NotificationList"];
                };
            };
        };
    };
    create_notification: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["NotificationBody"];
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
                    "application/json": components["schemas"]["NotificationList"];
                };
            };
        };
    };
    notification_counts: {
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
                    "application/json": components["schemas"]["NotificationCounts"];
                };
            };
        };
    };
    mark_read: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReadBody"];
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
                    "application/json": components["schemas"]["ReadResult"];
                };
            };
        };
    };
    list_projects: {
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
                    "application/json": components["schemas"]["ProjectList"];
                };
            };
        };
    };
    create_project: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectBody"];
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
                    "application/json": components["schemas"]["Project"];
                };
            };
        };
    };
    get_project: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
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
                    "application/json": components["schemas"]["Project"];
                };
            };
        };
    };
    patch_project: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectBody"];
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
                    "application/json": components["schemas"]["Project"];
                };
            };
        };
    };
    list_reviews: {
        parameters: {
            query?: {
                /** @description 이 작업물의 검토만 */
                item_id?: string | null;
                mine?: "to_review" | "requested" | "all";
                status?: string | null;
                target?: string | null;
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
                    "application/json": components["schemas"]["ReviewList"];
                };
            };
        };
    };
    request_review: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewBody"];
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
                    "application/json": components["schemas"]["Review"];
                };
            };
        };
    };
    get_review: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                review_id: string;
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
                    "application/json": components["schemas"]["Review"];
                };
            };
        };
    };
    patch_review: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                review_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewPatch"];
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
                    "application/json": components["schemas"]["Review"];
                };
            };
        };
    };
    cancel_review: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                review_id: string;
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
                    "application/json": components["schemas"]["Review"];
                };
            };
        };
    };
    put_check: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                review_id: string;
                target_ref: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewCheckBody"];
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
                    "application/json": components["schemas"]["Review"];
                };
            };
        };
    };
    delete_check: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                review_id: string;
                target_ref: string;
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
                    "application/json": components["schemas"]["Review"];
                };
            };
        };
    };
    decide: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                review_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewDecisionBody"];
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
                    "application/json": components["schemas"]["Review"];
                };
            };
        };
    };
    resubmit: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                review_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResubmitBody"];
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
                    "application/json": components["schemas"]["Review"];
                };
            };
        };
    };
    create_share: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ShareBody"];
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
                    "application/json": components["schemas"]["ShareLink"];
                };
            };
        };
    };
    resolve_share: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                token: string;
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
                    "application/json": components["schemas"]["ShareLink"];
                };
            };
        };
    };
    list_users: {
        parameters: {
            query?: {
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
                    "application/json": components["schemas"]["UserList"];
                };
            };
        };
    };
    create_user: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserCreate"];
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
                    "application/json": components["schemas"]["UserOut"];
                };
            };
        };
    };
    patch_user: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserPatch"];
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
                    "application/json": components["schemas"]["UserOut"];
                };
            };
        };
    };
    user_status: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
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
                    "application/json": components["schemas"]["UserStatus"];
                };
            };
        };
    };
}
