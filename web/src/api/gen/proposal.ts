// 자동 생성 — 직접 고치지 말 것. 원본: contracts/proposal.json (make contracts)
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
    "/v1/proposals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Proposals */
        get: operations["list_proposals"];
        put?: never;
        /** Create Proposal */
        post: operations["create_proposal"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Proposal */
        get: operations["get_proposal"];
        put?: never;
        post?: never;
        /** Delete Proposal */
        delete: operations["delete_proposal"];
        options?: never;
        head?: never;
        /** Patch Proposal */
        patch: operations["patch_proposal"];
        trace?: never;
    };
    "/v1/proposals/{proposal_id}:generate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Generate */
        post: operations["generate"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}:mark-submitted": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Mark Submitted */
        post: operations["mark_submitted"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/changes/{change_id}:revert": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Revert Change */
        post: operations["revert_change"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/comments/{comment_id}:apply-suggestion": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Apply Suggestion */
        post: operations["apply_suggestion"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/comments/{comment_id}:suggest": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Suggest */
        post: operations["suggest"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/comments/{comment_id}/suggestion": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Suggestion */
        get: operations["get_suggestion"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/composition": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Composition */
        get: operations["get_composition"];
        /** Put Composition */
        put: operations["put_composition"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/composition:start": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start Sections
         * @description 「섹션 작성 시작」 — 업종 레이아웃 미결정 + 업종 감지 + MI/VP/SS 계열 시트가 있으면 PR3I, 아니면 첫 섹션.
         */
        post: operations["start_sections"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/confirm-items": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Items */
        get: operations["list_items"];
        put?: never;
        /** Create Item */
        post: operations["create_item"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/confirm-items:move-to-note": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Move All To Note */
        post: operations["move_all_to_note"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/confirm-items:research": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Research */
        post: operations["research"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/confirm-items/{item_id}:anonymize": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Anonymize */
        post: operations["anonymize"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/confirm-items/{item_id}:evidence": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Attach Evidence */
        post: operations["attach_evidence"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/confirm-items/{item_id}:move-to-note": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Move To Note */
        post: operations["move_to_note"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/confirm-items/{item_id}:question": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Question */
        post: operations["question"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/confirm-items/{item_id}:resolve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Resolve Item */
        post: operations["resolve_item"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/design": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Design */
        get: operations["get_design"];
        /** Put Design */
        put: operations["put_design"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/design/logo": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Put Logo */
        post: operations["put_logo"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/export-options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Options */
        get: operations["export_options"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/exports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Export */
        post: operations["create_export"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/exports/{export_id}": {
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
    "/v1/proposals/{proposal_id}/facts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Facts */
        get: operations["list_facts"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/facts/{fact_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Fact */
        put: operations["put_fact"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/image-slots": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Image Slots */
        get: operations["image_slots"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/imports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Create Import
         * @description 팝업 항목(제품 · 솔루션 · 이미지 · 사례)은 **200** 바로 추가, 사이드바 작업 · 보내기(handoff)는 **202** 잡.
         */
        post: operations["create_import"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/imports/{import_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Import */
        get: operations["get_import"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/imports/{import_id}:apply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Apply Import */
        post: operations["apply_import"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/imports/{import_id}:undo": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Undo Import */
        post: operations["undo_import"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/industry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Industry */
        get: operations["get_industry"];
        /** Put Industry */
        put: operations["put_industry"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/links": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Links */
        get: operations["list_links"];
        /** Put Links */
        put: operations["put_links"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/links:apply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Apply Links */
        post: operations["apply_links"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/links/{link_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Link */
        delete: operations["delete_link"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/links/{link_id}:refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Refresh Link */
        post: operations["refresh_link"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/links/{link_id}:restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Restore Link */
        post: operations["restore_link"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/masters": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Upload Master */
        post: operations["upload_master"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Proposal Messages */
        get: operations["proposal_messages"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/notes:generate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Notes Generate */
        post: operations["notes_generate"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/one-click": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Start One Click */
        post: operations["start_one_click"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/one-click/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get One Click */
        get: operations["get_one_click"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/one-click/plan": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** One Click Plan */
        get: operations["one_click_plan"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/related-works": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Related Works */
        get: operations["related_works"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/renders": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Render */
        post: operations["create_render"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/requests": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Proposal Request */
        post: operations["proposal_request"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/result": {
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
    "/v1/proposals/{proposal_id}/reuse": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Reuse */
        get: operations["get_reuse"];
        put?: never;
        /** Start Reuse */
        post: operations["start_reuse"];
        /** Delete Reuse */
        delete: operations["delete_reuse"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/reuse:confirm-analysis": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Confirm Analysis */
        post: operations["confirm_analysis"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/reuse:reanalyze": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reanalyze */
        post: operations["reanalyze"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/reuse/candidates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Candidates */
        get: operations["candidates"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/reuse/criteria/{no}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Criterion */
        get: operations["get_criterion"];
        /** Put Criterion */
        put: operations["put_criterion"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/reuse/mode": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Mode */
        put: operations["put_mode"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/reuse/pages/{no}/role": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Page Role */
        put: operations["put_page_role"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/reuse/plan:confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Confirm Plan */
        post: operations["confirm_plan"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/reuse/plan/rows/{row_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Verdict */
        put: operations["put_verdict"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/reuse/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Reuse Summary */
        get: operations["reuse_summary"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/review": {
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
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/review-requests": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Request Review */
        post: operations["request_review"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/review-requests/{review_id}:resubmit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Resubmit */
        post: operations["resubmit"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/review:apply-comments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Apply Comments */
        post: operations["apply_comments"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/review/checks/{sheet_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Check */
        put: operations["put_check"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/review/decision": {
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
    "/v1/proposals/{proposal_id}/rfp": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Rfp */
        get: operations["get_rfp"];
        put?: never;
        /** Start Rfp */
        post: operations["start_rfp"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/rfp:confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Confirm Rfp */
        post: operations["confirm_rfp"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/rfp/fields/{key}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Rfp Field */
        put: operations["put_rfp_field"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/sections/{key}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Section */
        get: operations["get_section"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/sections/{key}:confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Confirm Section */
        post: operations["confirm_section"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/sections/{key}:fill": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Fill Section */
        post: operations["fill_section"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/sections/{key}/requests": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Section Request */
        post: operations["section_request"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/sections/{key}/reuse-view": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Reuse Section View */
        get: operations["reuse_section_view"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/sections/{key}/templates:auto": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Section Templates Auto */
        post: operations["section_templates_auto"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/share-link": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Share Link */
        post: operations["share_link"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/sheets/{sheet_id}": {
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
        /** Patch Sheet */
        patch: operations["patch_sheet"];
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/sheets/{sheet_id}:rewrite": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Rewrite Sheet */
        post: operations["rewrite_sheet"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/sheets/{sheet_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Sheet Messages */
        get: operations["sheet_messages"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/sheets/{sheet_id}/reuse:pull-lines": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Pull Lines */
        post: operations["pull_lines"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/sheets/{sheet_id}/template": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Template */
        put: operations["put_template"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/sheets/{sheet_id}/template-options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Template Options */
        get: operations["template_options"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/slides": {
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
    "/v1/proposals/{proposal_id}/type": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Type */
        put: operations["put_type"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/type-options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Type Options */
        get: operations["type_options"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/versions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Versions */
        get: operations["list_versions"];
        put?: never;
        /** Save Version */
        post: operations["save_version"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/versions/{n}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Restore */
        post: operations["restore"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/proposals/{proposal_id}/versions/compare": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Compare */
        get: operations["compare"];
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
        /** Accepts */
        Accepts: {
            /** Items */
            items: ("product" | "solution" | "image" | "case")[];
            /**
             * Sidebar
             * @description 받는 사이드바 기능(서비스 이름)
             */
            sidebar: string[];
        };
        /** ApplyCommentsIn */
        ApplyCommentsIn: {
            /** Comment Ids */
            comment_ids?: string[] | null;
        };
        /** ApplySuggestionResult */
        ApplySuggestionResult: {
            /** Change Ids */
            change_ids?: string[];
            /** Comment Id */
            comment_id: string;
            sheet?: components["schemas"]["Sheet"] | null;
        };
        /** Approvals */
        Approvals: {
            /** Done */
            done: number;
            /** Label */
            label: string;
            /** Total */
            total: number;
        };
        /** BorrowRow */
        BorrowRow: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "flow" | "new" | "drop";
            /** New Count */
            new_count: number;
            /** New Label */
            new_label: string;
            /** Note */
            note: string;
            /** Rq Ids */
            rq_ids?: string[];
            /** Src Count */
            src_count: number;
            /**
             * Src Range
             * @default
             */
            src_range: string;
            /** Src Step */
            src_step: string;
        };
        /** BulkIds */
        BulkIds: {
            /** Ids */
            ids?: string[] | null;
        };
        /** Candidate */
        Candidate: {
            /** Source */
            source?: {
                [key: string]: unknown;
            };
            /** Value */
            value: string;
        };
        /** CheckCell */
        CheckCell: {
            /** Sheet Id */
            sheet_id: string;
            /** Sheet No */
            sheet_no: number;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "open" | "todo";
            /** Title */
            title: string;
        };
        /** CheckPut */
        CheckPut: {
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "todo";
        };
        /** CommentSheet */
        CommentSheet: {
            /**
             * Label
             * @default
             */
            label: string;
            /** Name */
            name: string;
            /** Open */
            open: number;
            /** Resolved */
            resolved: number;
            /** Sheet Id */
            sheet_id: string;
            /** Sheet No */
            sheet_no: number;
        };
        /** CompareSheet */
        CompareSheet: {
            /** Count */
            count: number;
            /** Name */
            name: string;
            /** Sheet Id */
            sheet_id: string;
            /** Sheet No */
            sheet_no: number;
        };
        /** CompareSide */
        CompareSide: {
            /**
             * Display
             * @description 그 버전의 그 시트 display(§5.3.1) — PNG 가 없을 때 웹이 슬라이드를 직접 그린다
             */
            display?: {
                [key: string]: unknown;
            } | null;
            /** Label */
            label: string;
            /**
             * Meta
             * @default
             */
            meta: string;
            /** N */
            n: number;
            /** Png Url */
            png_url?: string | null;
            /** Sheet Id */
            sheet_id?: string | null;
        };
        /** CompareView */
        CompareView: {
            a: components["schemas"]["CompareSide"];
            b: components["schemas"]["CompareSide"];
            /** Changed Sheets */
            changed_sheets: components["schemas"]["CompareSheet"][];
            /** Diffs */
            diffs: components["schemas"]["DiffItem"][];
            /**
             * Footer Note
             * @default
             */
            footer_note: string;
            /**
             * Header Label
             * @description 「바뀐 시트 4 · 바뀐 곳 6」
             */
            header_label: string;
            /** Sheet Id */
            sheet_id?: string | null;
        };
        /** CompChip */
        CompChip: {
            /** Code */
            code: string;
            /** Name */
            name: string;
            /**
             * Repeat
             * @default 1
             */
            repeat: number;
        };
        /** Composition */
        Composition: {
            /**
             * Footer Note
             * @default 시트 수는 따로 정하지 않아요. 공간 · 사례처럼 반복되는 시트는 연결된 항목 수만큼 생깁니다.
             */
            footer_note: string;
            /**
             * Header Label
             * @description 「시트 구성 · 표준 제안서 · 섹션 8 · 시트 24 · 3 / 6」
             */
            header_label: string;
            /** Intro */
            intro: string;
            next: components["schemas"]["NextStep"];
            /** Open Key */
            open_key?: string | null;
            /** Section Count */
            section_count: number;
            /** Sections */
            sections: components["schemas"]["CompSection"][];
            /** Sheet Total */
            sheet_total: number;
            /**
             * Type
             * @enum {string}
             */
            type: "standard" | "quickwin" | "solution";
            /** Type Name */
            type_name: string;
        };
        /** CompositionPut */
        CompositionPut: {
            /** Sections */
            sections: components["schemas"]["CompSectionPut"][];
        };
        /** CompSection */
        CompSection: {
            /** Chips */
            chips: components["schemas"]["CompChip"][];
            /** Enabled */
            enabled: boolean;
            /** Key */
            key: string;
            /** More */
            more: number;
            /**
             * More Label
             * @default
             */
            more_label: string;
            /** Name */
            name: string;
            /** No */
            no: number;
            /** No Label */
            no_label: string;
            /**
             * Open
             * @default false
             */
            open: boolean;
            /** Optional */
            optional: boolean;
            /** Sheet Count */
            sheet_count: number;
            /**
             * Switch Label
             * @description 선택 섹션 스위치 aria 「{{섹션}} 섹션 사용」
             */
            switch_label?: string | null;
            /**
             * Tag
             * @description 「필수」 · 「선택」
             */
            tag: string;
            /** Types */
            types: components["schemas"]["CompType"][];
        };
        /** CompSectionPut */
        CompSectionPut: {
            /** Enabled */
            enabled?: boolean | null;
            /** Key */
            key: string;
            /** Types */
            types?: components["schemas"]["CompTypeToggle"][];
        };
        /** CompType */
        CompType: {
            /** Code */
            code: string;
            /**
             * Dedicated
             * @default false
             */
            dedicated: boolean;
            /** Meta */
            meta: string;
            /** Msg */
            msg: string;
            /** Name */
            name: string;
            /**
             * Repeat
             * @default 1
             */
            repeat: number;
            /** Src Label */
            src_label: string;
            /**
             * State
             * @enum {string}
             */
            state: "on" | "rec" | "off";
            /** Template Count */
            template_count?: number | null;
            /**
             * User Set
             * @default false
             */
            user_set: boolean;
        };
        /** CompTypeToggle */
        CompTypeToggle: {
            /** Code */
            code: string;
            /** On */
            on: boolean;
        };
        /** ConfirmAction */
        ConfirmAction: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "link" | "button";
            /** Label */
            label: string;
            target: components["schemas"]["ConfirmActionTarget"];
        };
        /** ConfirmActionTarget */
        ConfirmActionTarget: {
            /** Feature */
            feature?: string | null;
            /** Op */
            op?: string | null;
            /** Ref Id */
            ref_id?: string | null;
            /** Route */
            route?: string | null;
        };
        /** ConfirmBrief */
        ConfirmBrief: {
            /** Id */
            id: string;
            /** Status */
            status: string;
            /** Tag */
            tag: string;
            /** Text */
            text: string;
        };
        /** ConfirmCounts */
        ConfirmCounts: {
            /**
             * Confirmed
             * @default 0
             */
            confirmed: number;
            /**
             * Open
             * @default 0
             */
            open: number;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** ConfirmCreate */
        ConfirmCreate: {
            /** From Comment Id */
            from_comment_id?: string | null;
            /** Sheet Id */
            sheet_id: string;
            /** Tag */
            tag?: string | null;
            /** Text */
            text: string;
        };
        /** ConfirmFix */
        ConfirmFix: {
            /** Formula */
            formula?: string | null;
            /** Linked Sheets */
            linked_sheets?: components["schemas"]["FixSheet"][];
            /** Sentence */
            sentence: components["schemas"]["FixPart"][];
        };
        /** ConfirmItem */
        ConfirmItem: {
            action?: components["schemas"]["ConfirmAction"] | null;
            /** Candidates */
            candidates?: components["schemas"]["Candidate"][];
            /**
             * Candidates Label
             * @description 「후보 2」
             */
            candidates_label?: string | null;
            /**
             * Category
             * @enum {string}
             */
            category: "fact" | "review";
            /** Created At */
            created_at: string;
            evidence?: components["schemas"]["FactEvidence"] | null;
            /** Fact Id */
            fact_id?: string | null;
            fix?: components["schemas"]["ConfirmFix"] | null;
            /** Id */
            id: string;
            /** Linked Sheet Ids */
            linked_sheet_ids?: string[];
            /** Origin */
            origin: string;
            /** Proposal Id */
            proposal_id: string;
            /** Resolution */
            resolution?: {
                [key: string]: unknown;
            } | null;
            /**
             * Route
             * @description 「섹션 열기」 · 「바로 고치기」 이동
             */
            route: string;
            /** Section Key */
            section_key?: string | null;
            /** Sheet Id */
            sheet_id?: string | null;
            /** Sheet No */
            sheet_no?: number | null;
            /**
             * Sheet No Label
             * @default
             */
            sheet_no_label: string;
            /**
             * Status
             * @enum {string}
             */
            status: "open" | "confirmed" | "moved_to_note" | "dismissed";
            /** Status Label */
            status_label: string;
            /**
             * Sub
             * @default
             */
            sub: string;
            /** Tag */
            tag: string;
            text: components["schemas"]["ConfirmText"];
            /** Where */
            where?: string | null;
            /** Why */
            why?: string | null;
        };
        /** ConfirmList */
        ConfirmList: {
            /**
             * Confirmed Summary
             * @default
             */
            confirmed_summary: string;
            counts: components["schemas"]["ConfirmCounts"];
            /**
             * Footer Label
             * @default
             */
            footer_label: string;
            /**
             * Header Label
             * @description 「확정 필요 7곳」
             */
            header_label: string;
            /** Intro */
            intro: string;
            /** Items */
            items: components["schemas"]["ConfirmItem"][];
            /**
             * Progress Label
             * @description 「2곳 확정 · 5곳 남음」
             */
            progress_label: string;
            /**
             * Sheets Total
             * @default 0
             */
            sheets_total: number;
        };
        /** ConfirmResolve */
        ConfirmResolve: {
            evidence?: components["schemas"]["FactEvidence"] | null;
            /** Value */
            value?: string | null;
            /**
             * Values
             * @description fact key → 값
             */
            values?: {
                [key: string]: string;
            };
        };
        /** ConfirmResolveResult */
        ConfirmResolveResult: {
            /** Change Ids */
            change_ids?: string[];
            /** Changed Sheet Ids */
            changed_sheet_ids?: string[];
            /** Facts */
            facts?: components["schemas"]["Fact"][];
            item: components["schemas"]["ConfirmItem"];
        };
        /** ConfirmText */
        ConfirmText: {
            /** Mark */
            mark: string;
            /**
             * Post
             * @default
             */
            post: string;
            /**
             * Pre
             * @default
             */
            pre: string;
        };
        /** Cover */
        Cover: {
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            image_ref?: components["schemas"]["CoverImageRef"] | null;
        };
        /** Coverage */
        Coverage: {
            /** Code */
            code: string;
            /** Name */
            name: string;
            /** Rq Id */
            rq_id: string;
            /**
             * State
             * @enum {string}
             */
            state: "has" | "part" | "none";
            /** State Label */
            state_label: string;
            /** Where */
            where: string;
        };
        /** CoverImageRef */
        CoverImageRef: {
            /** File Id */
            file_id?: string | null;
            /** Id */
            id: string;
            /**
             * Kind
             * @description file · kb_image · image_job
             */
            kind: string;
            /** Label */
            label?: string | null;
        };
        /** CoverIn */
        CoverIn: {
            /** Enabled */
            enabled?: boolean | null;
            image_ref?: components["schemas"]["CoverImageRef"] | null;
        };
        /** CriterionDetail */
        CriterionDetail: {
            /**
             * Chips
             * @description 기준 전환 칩 1–9
             */
            chips?: {
                [key: string]: unknown;
            }[];
            /** Confidence */
            confidence: number;
            /** Detail */
            detail?: {
                [key: string]: unknown;
            };
            flow?: components["schemas"]["ReuseFlow"] | null;
            /**
             * Footer Label
             * @default
             */
            footer_label: string;
            /**
             * Header Label
             * @default
             */
            header_label: string;
            /**
             * Intro
             * @default
             */
            intro: string;
            /** Key */
            key: string;
            /** Must */
            must: boolean;
            /** Name */
            name: string;
            /** No */
            no: number;
            /** Pages */
            pages?: components["schemas"]["ReusePage"][];
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "need" | "edited";
            /** State Label */
            state_label: string;
            /** Summary */
            summary: string;
        };
        /** CriterionPut */
        CriterionPut: {
            /** Edits */
            edits?: {
                [key: string]: unknown;
            } | null;
            /** State */
            state?: ("ok" | "need") | null;
        };
        /** Customer */
        Customer: {
            /**
             * Decision Makers
             * @description 「고객 측 의사결정자 · 청중」
             */
            decision_makers?: string | null;
            /**
             * Industry Code
             * @description 16업종 코드(부록 C, 예 FB)
             */
            industry_code?: string | null;
            /** Industry Label */
            industry_label?: string | null;
            /**
             * Industry User Set
             * @description 사용자가 업종 칩을 직접 고름(고정)
             * @default false
             */
            industry_user_set: boolean;
            /** Kr Vertical Id */
            kr_vertical_id?: string | null;
            /**
             * Name
             * @default
             */
            name: string;
            /** Scale Text */
            scale_text?: string | null;
        };
        /** CustomerFrom */
        CustomerFrom: {
            /** Feature */
            feature: string;
            /** Label */
            label: string;
        };
        /** CustomerIn */
        CustomerIn: {
            /** Decision Makers */
            decision_makers?: string | null;
            /**
             * Industry Chip
             * @description PR1 업종 칩(「리테일 · F&B」 등). 주면 묶음 안 1위 업종으로
             */
            industry_chip?: string | null;
            /** Industry Code */
            industry_code?: string | null;
            /** Industry Label */
            industry_label?: string | null;
            /** Name */
            name?: string | null;
            /** Scale Text */
            scale_text?: string | null;
        };
        /** DecisionIn */
        DecisionIn: {
            /** Comment */
            comment?: string | null;
            /**
             * Decision
             * @enum {string}
             */
            decision: "approve" | "request_changes";
        };
        /** DerivedFrom */
        DerivedFrom: {
            /** File Ids */
            file_ids?: string[];
            /**
             * Kind
             * @enum {string}
             */
            kind: "proposal" | "file";
            /**
             * Label
             * @description 「2025 제안서 v4에서 파생」
             */
            label?: string | null;
            /** Proposal Id */
            proposal_id?: string | null;
            /** Reuse Id */
            reuse_id?: string | null;
            /** Version */
            version?: number | null;
        };
        /** Design */
        Design: {
            /**
             * Appendix
             * @default false
             */
            appendix: boolean;
            /** Brand Hex */
            brand_hex?: string | null;
            /**
             * Chosen
             * @description 사용자가 PR6 에서 고른 적 있음(딸깍 「디자인 템플릿」 행)
             * @default false
             */
            chosen: boolean;
            /** Color Candidates */
            color_candidates?: string[];
            cover?: components["schemas"]["Cover"];
            /**
             * Layout Mode
             * @default auto
             * @enum {string}
             */
            layout_mode: "auto" | "manual";
            /** Logo File Id */
            logo_file_id?: string | null;
            /**
             * Master Id
             * @default samsung_b2b
             */
            master_id: string;
            /**
             * Master Name
             * @default 삼성 B2B 표준
             */
            master_name: string;
            /**
             * Page Numbers
             * @default true
             */
            page_numbers: boolean;
            /**
             * Section Dividers
             * @default true
             */
            section_dividers: boolean;
        };
        /** DesignPatch */
        DesignPatch: {
            /** Appendix */
            appendix?: boolean | null;
            /** Brand Hex */
            brand_hex?: string | null;
            cover?: components["schemas"]["CoverIn"] | null;
            /** Layout Mode */
            layout_mode?: ("auto" | "manual") | null;
            /** Logo File Id */
            logo_file_id?: string | null;
            /** Master Id */
            master_id?: string | null;
            /** Page Numbers */
            page_numbers?: boolean | null;
            /** Section Dividers */
            section_dividers?: boolean | null;
        };
        /** DesignView */
        DesignView: {
            design: components["schemas"]["Design"];
            /** Generate Job Id */
            generate_job_id?: string | null;
            /**
             * Header Label
             * @default 디자인 템플릿 · 하나 선택 · 5 / 6
             */
            header_label: string;
            /** Intro */
            intro: string;
            /** Masters */
            masters: components["schemas"]["MasterOut"][];
            pre_generate: components["schemas"]["PreGenerate"];
            sheet_templates: components["schemas"]["SheetTemplatesSummary"];
        };
        /** DiffItem */
        DiffItem: {
            /** Bbox */
            bbox?: {
                [key: string]: number;
            } | null;
            /** Change Id */
            change_id?: string | null;
            /** From */
            from?: unknown;
            /** From Swatch */
            from_swatch?: string | null;
            /** Kind */
            kind: string;
            /** N */
            n: number;
            /**
             * Revertable
             * @default true
             */
            revertable: boolean;
            /** Sheet Id */
            sheet_id: string;
            /** Sheet No */
            sheet_no?: number | null;
            /** To */
            to?: unknown;
            /** To Swatch */
            to_swatch?: string | null;
            /** Where */
            where: string;
            /**
             * Why
             * @default
             */
            why: string;
        };
        /** DropHint */
        DropHint: {
            /**
             * Idle
             * @default 여기에 끌어 놓기
             */
            idle: string;
            /**
             * Item
             * @description 팝업 항목 드래그 중 두 줄(「{{항목}}」 자리 표시)
             */
            item?: string[];
            /**
             * Sidebar
             * @description 사이드바 작업 드래그 중 두 줄
             */
            sidebar?: string[];
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
        /** EvidenceIn */
        EvidenceIn: {
            evidence: components["schemas"]["FactEvidence"];
        };
        /** ExportFileOut */
        ExportFileOut: {
            /** File Id */
            file_id: string;
            /** Format */
            format: string;
            /** Lang */
            lang: string;
            /** Name */
            name: string;
            /** Size */
            size?: number | null;
            /** Url */
            url: string;
        };
        /** ExportInclude */
        ExportInclude: {
            /**
             * Appendix
             * @default false
             */
            appendix: boolean;
            /**
             * Footnotes
             * @default true
             */
            footnotes: boolean;
            /**
             * Speaker Notes
             * @default true
             */
            speaker_notes: boolean;
        };
        /** ExportOptions */
        ExportOptions: {
            defaults: components["schemas"]["ExportRequest"];
            /** Eta Label */
            eta_label: string;
            /** Filename Tokens */
            filename_tokens?: string[];
            /** Header Label */
            header_label: string;
            /**
             * Include Note
             * @default 검토 코멘트와 '추론' 표시는 파일에 넣지 않아요.
             */
            include_note: string;
            /** Intro */
            intro: string;
            /** Masters */
            masters: components["schemas"]["MasterOut"][];
            /** Open Confirm */
            open_confirm: number;
            /**
             * Open Confirm Label
             * @default
             */
            open_confirm_label: string;
            /** Preview Files */
            preview_files: string[];
            /** Sections */
            sections?: components["schemas"]["RouteRef"][];
            /** Sheets Total */
            sheets_total: number;
            /**
             * Tbd Note
             * @default 영문은 번역 후 넘치는 문장을 줄이고, [확정 필요] 표시는 [TBD]로 바꿔요.
             */
            tbd_note: string;
            /** Team Folder Path */
            team_folder_path: string;
            /** Version */
            version: number;
            /** Version Label */
            version_label: string;
        };
        /** ExportRecord */
        ExportRecord: {
            /** Created At */
            created_at: string;
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            /** Filename Base */
            filename_base: string;
            /** Files */
            files?: components["schemas"]["ExportFileOut"][];
            /** Formats */
            formats: string[];
            /** Id */
            id: string;
            include: components["schemas"]["ExportInclude"];
            /** Job Id */
            job_id?: string | null;
            /** Lang */
            lang: string;
            /** Master Id */
            master_id?: string | null;
            /** Proposal Id */
            proposal_id: string;
            scope: components["schemas"]["ExportScope"];
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "done" | "failed";
            /** Tbd Mode */
            tbd_mode: string;
            team_folder: components["schemas"]["TeamFolder"];
            /** Team Folder Files */
            team_folder_files?: string[];
            /** Version */
            version?: number | null;
            /** Warnings */
            warnings?: string[];
        };
        /** ExportRequest */
        ExportRequest: {
            /** Filename Base */
            filename_base?: string | null;
            /** Formats */
            formats?: ("pptx" | "pdf")[];
            include?: components["schemas"]["ExportInclude"];
            /**
             * Lang
             * @default ko
             * @enum {string}
             */
            lang: "ko" | "en" | "ko_en";
            /** Master Id */
            master_id?: string | null;
            scope?: components["schemas"]["ExportScope"];
            /**
             * Tbd Mode
             * @default keep_marks
             * @enum {string}
             */
            tbd_mode: "keep_marks" | "move_to_notes";
            team_folder?: components["schemas"]["TeamFolder"];
            /**
             * Version
             * @description 없으면 현재 상태
             */
            version?: number | null;
        };
        /** ExportScope */
        ExportScope: {
            /**
             * Kind
             * @default all
             * @enum {string}
             */
            kind: "all" | "sections" | "sheets";
            /**
             * Range
             * @description 「01–07, 21」
             */
            range?: string | null;
            /** Section Keys */
            section_keys?: string[] | null;
        };
        /** Fact */
        Fact: {
            /** Display */
            display: string;
            evidence?: components["schemas"]["FactEvidence"] | null;
            /** Formula */
            formula?: string | null;
            /**
             * Formula Label
             * @description 「합계 = 매장 수 × 3대」
             */
            formula_label?: string | null;
            /** History */
            history?: {
                [key: string]: unknown;
            }[];
            /** Id */
            id: string;
            /** Key */
            key: string;
            /**
             * Kind
             * @default input
             * @enum {string}
             */
            kind: "input" | "derived";
            /** Label */
            label: string;
            /** Origin */
            origin?: {
                [key: string]: unknown;
            };
            /** Placeholder */
            placeholder: string;
            /**
             * Status
             * @enum {string}
             */
            status: "placeholder" | "unconfirmed" | "confirmed";
            /** Unit */
            unit?: string | null;
            /** Used In */
            used_in?: components["schemas"]["FactUse"][];
            /** Value */
            value?: string | null;
        };
        /** FactBrief */
        FactBrief: {
            /** Display */
            display: string;
            /** Id */
            id: string;
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Status */
            status: string;
        };
        /** FactEvidence */
        FactEvidence: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "url" | "file" | "work" | "internal_doc" | "customer" | "user";
            /** Note */
            note?: string | null;
            /** Ref */
            ref?: string | null;
        };
        /** FactList */
        FactList: {
            /** Items */
            items: components["schemas"]["Fact"][];
        };
        /** FactPut */
        FactPut: {
            evidence?: components["schemas"]["FactEvidence"] | null;
            /** Unit */
            unit?: string | null;
            /** Value */
            value?: string | null;
        };
        /** FactUpdateResult */
        FactUpdateResult: {
            /** Change Ids */
            change_ids: string[];
            /** Changed Sheet Ids */
            changed_sheet_ids: string[];
            fact: components["schemas"]["Fact"];
        };
        /** FactUse */
        FactUse: {
            /** Path */
            path: string;
            /** Sheet Id */
            sheet_id: string;
            /** Sheet No */
            sheet_no?: number | null;
        };
        /** FamilyCard */
        FamilyCard: {
            /**
             * Available
             * @default true
             */
            available: boolean;
            /** Code */
            code: string;
            /**
             * Desc
             * @default
             */
            desc: string;
            /** Name */
            name: string;
            /**
             * State
             * @enum {string}
             */
            state: "applied" | "alt" | "add";
            /** State Label */
            state_label: string;
            /** Thumb Url */
            thumb_url: string;
            /** Variant */
            variant: string;
        };
        /** FamilyMap */
        FamilyMap: {
            /**
             * Strong
             * @default false
             */
            strong: boolean;
            /** Text */
            text: string;
        };
        /** Files */
        Files: {
            /** Pdf File Id */
            pdf_file_id?: string | null;
            /** Pptx File Id */
            pptx_file_id?: string | null;
        };
        /** FillCounts */
        FillCounts: {
            /**
             * Full
             * @default 0
             */
            full: number;
            /**
             * New
             * @default 0
             */
            new: number;
            /**
             * Partial
             * @default 0
             */
            partial: number;
        };
        /** FillPreview */
        FillPreview: {
            counts: components["schemas"]["FillCounts"];
            /**
             * Counts Label
             * @description 「채움 3 · 일부 3 · 새로 작성 2」
             * @default
             */
            counts_label: string;
            customer_from?: components["schemas"]["CustomerFrom"] | null;
            /**
             * Customer Summary
             * @default
             */
            customer_summary: string;
            recommended_type: components["schemas"]["RecommendedType"];
            /** Sections */
            sections: components["schemas"]["FillPreviewSection"][];
        };
        /** FillPreviewSection */
        FillPreviewSection: {
            /** Key */
            key: string;
            /** Name */
            name: string;
            /** Source Label */
            source_label: string;
            /**
             * State
             * @enum {string}
             */
            state: "full" | "partial" | "new";
            /** State Label */
            state_label: string;
        };
        /** FixPart */
        FixPart: {
            /**
             * Input
             * @description fact key
             */
            input?: string | null;
            /** Label */
            label?: string | null;
            /** Text */
            text?: string | null;
            /** Value */
            value?: string | null;
        };
        /** FixSheet */
        FixSheet: {
            /** Name */
            name: string;
            /** Sheet Id */
            sheet_id: string;
            /** Sheet No */
            sheet_no: number;
        };
        /** FlowMemo */
        FlowMemo: {
            /** Action */
            action: string;
            /** No */
            no: number;
            /** Tag */
            tag: string;
            /** Text */
            text: string;
        };
        /** FlowStep */
        FlowStep: {
            /** Count */
            count: number;
            /**
             * Dashed
             * @default false
             */
            dashed: boolean;
            /**
             * Excluded
             * @default false
             */
            excluded: boolean;
            /** Name */
            name: string;
            /**
             * Note
             * @default
             */
            note: string;
            /**
             * Range
             * @default
             */
            range: string;
        };
        /** GenerateIn */
        GenerateIn: {
            /**
             * Infer Empty
             * @description 자료 없는 섹션을 추론으로 채우고 검토 필요로(AC-134)
             * @default true
             */
            infer_empty: boolean;
            /**
             * Scope
             * @default all
             * @enum {string}
             */
            scope: "all" | "section";
            /** Section Key */
            section_key?: string | null;
        };
        /** GuideStep */
        GuideStep: {
            /** Chips */
            chips?: string[];
            /** From Source */
            from_source: string;
            /** No */
            no: number;
            /** Role */
            role: string;
            /**
             * Status
             * @enum {string}
             */
            status: "writing" | "waiting";
            /** Status Label */
            status_label: string;
            /** This Time */
            this_time: string;
            /** Title */
            title: string;
        };
        /** ImageSlot */
        ImageSlot: {
            /** Name */
            name: string;
            /** Preview Url */
            preview_url?: string | null;
            /** Recommended */
            recommended: boolean;
            /** Section */
            section: string;
            /** Section Key */
            section_key: string;
            /** Section Name */
            section_name: string;
            /** Sheet Id */
            sheet_id: string;
            /** Sheet No */
            sheet_no: number;
            /** Sheet Title */
            sheet_title: string;
            /** Slot */
            slot: string;
            /** Slots */
            slots: number;
        };
        /** ImageSlots */
        ImageSlots: {
            /** Image Ref */
            image_ref?: string | null;
            /** Proposal Id */
            proposal_id: string;
            /** Proposal Title */
            proposal_title: string;
            /** Sheets */
            sheets: components["schemas"]["ImageSlot"][];
            /** Slots */
            slots: components["schemas"]["ImageSlot"][];
        };
        /** Import */
        Import: {
            /** Affected Sheet Ids */
            affected_sheet_ids?: string[];
            /**
             * Can Undo
             * @default false
             */
            can_undo: boolean;
            /** Change Ids */
            change_ids?: string[];
            /** Created At */
            created_at: string;
            /** Created By */
            created_by?: string | null;
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            /**
             * Ex Count
             * @default 0
             */
            ex_count: number;
            /** Id */
            id: string;
            /**
             * Intro
             * @default MI 작업에서 이 섹션에 쓸 내용을 뽑았습니다. 어느 시트에, 어떤 템플릿으로 들어갈지 함께 표시했어요.
             */
            intro: string;
            /** Items */
            items?: components["schemas"]["ImportItem"][];
            /** Job Id */
            job_id?: string | null;
            /**
             * Label
             * @default
             */
            label: string;
            /** Link Id */
            link_id?: string | null;
            /** New Sheet Ids */
            new_sheet_ids?: string[];
            /**
             * Note
             * @default
             */
            note: string;
            /**
             * Panel Title
             * @default
             */
            panel_title: string;
            /** Proposal Id */
            proposal_id: string;
            /**
             * Question
             * @default 이 섹션의 시트에 이렇게 넣을까요? 필요한 것만 남겨 주세요.
             */
            question: string;
            /** Section Key */
            section_key: string;
            /** Source */
            source: {
                [key: string]: unknown;
            };
            /**
             * Source Route
             * @description 「원본 채팅 보기」 원 작업 화면
             */
            source_route?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "extracting" | "pending_confirm" | "applying" | "applied" | "undone" | "failed";
            /**
             * Toast
             * @default
             */
            toast: string;
            /** Via */
            via: string;
        };
        /** ImportApply */
        ImportApply: {
            /** Keys */
            keys: string[];
        };
        /** ImportItem */
        ImportItem: {
            /** Checked */
            checked: boolean;
            /** From Label */
            from_label?: string | null;
            /** In Section */
            in_section: boolean;
            /** Key */
            key: string;
            /**
             * Line Label
             * @description 「→ 시장 규모 · 성장 · 성장 추이 템플릿」 / 「이 섹션엔 없는 시트 · 사용자 분석 시트로 추가 가능」
             */
            line_label: string;
            /**
             * Role Name
             * @default
             */
            role_name: string;
            /**
             * Section Key
             * @description 이 항목이 들어갈 섹션(보내기에서 역할이 다른 섹션에 있으면 그 섹션, 없으면 반입 섹션)
             */
            section_key?: string | null;
            /** Sheet Role */
            sheet_role: string;
            /** Status */
            status?: string | null;
            /** Status Label */
            status_label?: string | null;
            /** Target Sheet Id */
            target_sheet_id?: string | null;
            /** Template Code */
            template_code?: string | null;
            /** Template Name */
            template_name?: string | null;
            /** What */
            what: string;
        };
        /** ImportRequest */
        ImportRequest: {
            /** Caption */
            caption?: string | null;
            /**
             * Include Keys
             * @description 보내기 화면에서 고른 항목 키(handoff)
             */
            include_keys?: string[] | null;
            /**
             * Section Key
             * @description 없으면 유형별 기본 섹션(§10.7)
             */
            section_key?: string | null;
            /** Slot */
            slot?: string | null;
            source: components["schemas"]["ImportSource"];
            target?: components["schemas"]["ImportTarget"] | null;
            /** Target Sheet Id */
            target_sheet_id?: string | null;
            /**
             * Via
             * @default drag_item
             * @enum {string}
             */
            via: "drag_sidebar" | "drag_item" | "button" | "handoff";
        };
        /** ImportResult */
        ImportResult: {
            /** Affected Sheet Ids */
            affected_sheet_ids?: string[];
            /** Confirm Item Ids */
            confirm_item_ids?: string[];
            /** Import Id */
            import_id: string;
            /**
             * Job Id
             * @description 관련 시트 내용 갱신 잡(카드 「업데이트됨」 → 끝나면 내용 반영)
             */
            job_id?: string | null;
            /** Label */
            label: string;
            /** New Sheet Ids */
            new_sheet_ids?: string[];
            /** Note */
            note: string;
            /** Route */
            route: string;
            /** Section Key */
            section_key: string;
            source_chip?: components["schemas"]["SourceChipOut"] | null;
            /** Status */
            status: string;
            /**
             * Toast
             * @description 「「QM65C」 추가됨 · "카운터 · 메뉴보드" 시트에 배치됨 · 수량 320」
             */
            toast: string;
        };
        /** ImportSource */
        ImportSource: {
            /**
             * Feature
             * @description 사이드바 작업 · 보내기: 기능(mi · storyboard … 또는 MI · SB …)
             */
            feature?: string | null;
            /** Handoff Id */
            handoff_id?: string | null;
            /** Image Id */
            image_id?: string | null;
            /**
             * Kind
             * @description 팝업 항목 종류
             */
            kind?: ("product" | "solution" | "image" | "case") | null;
            /** Label */
            label?: string | null;
            /**
             * Ref
             * @description {kb_kind, id} · {file_id} · {image_job_id} 또는 id 문자열
             */
            ref?: {
                [key: string]: unknown;
            } | string | null;
            /** Ref Id */
            ref_id?: string | null;
            /**
             * Service
             * @description IMG4: 'image'
             */
            service?: string | null;
            /** Sub */
            sub?: string | null;
            /** Title */
            title?: string | null;
            /** Version */
            version?: number | null;
            /** Version Id */
            version_id?: string | null;
        };
        /** ImportTarget */
        ImportTarget: {
            /** Mode */
            mode?: ("replace_slot" | "new_sheet") | null;
            /** Sheet Id */
            sheet_id?: string | null;
        };
        /** IndustryDetected */
        IndustryDetected: {
            /** Code */
            code: string;
            /** Evidence */
            evidence?: string[];
            /** Label */
            label: string;
            /**
             * Mode
             * @default auto
             * @enum {string}
             */
            mode: "auto" | "check" | "ask" | "pinned";
            /** Score */
            score?: number | null;
        };
        /** IndustryDetectedView */
        IndustryDetectedView: {
            /** Code */
            code?: string | null;
            /** Evidence */
            evidence?: string[];
            /**
             * Evidence Label
             * @default
             */
            evidence_label: string;
            /**
             * Label
             * @default
             */
            label: string;
            /**
             * Mode
             * @default auto
             * @enum {string}
             */
            mode: "auto" | "check" | "ask" | "pinned";
            /**
             * Mode Label
             * @default
             */
            mode_label: string;
            /** Score */
            score?: number | null;
        };
        /** IndustryFamily */
        IndustryFamily: {
            /**
             * Available
             * @default true
             */
            available: boolean;
            /** Cards */
            cards: components["schemas"]["FamilyCard"][];
            /** Maps */
            maps: components["schemas"]["FamilyMap"][];
            /** Name */
            name: string;
            /** On */
            on: boolean;
            /**
             * Pick Route
             * @description 「시트별로 바꾸기」 → 대표 시트 템플릿 고르기
             */
            pick_route?: string | null;
            /**
             * Role
             * @enum {string}
             */
            role: "MI" | "VP" | "SS";
            /** Switch Label */
            switch_label: string;
        };
        /** IndustryLayout */
        IndustryLayout: {
            /** Applied Codes */
            applied_codes?: string[];
            /**
             * Cards
             * @description 카드 코드 → applied|alt
             */
            cards?: {
                [key: string]: string;
            };
            /**
             * Decided
             * @default false
             */
            decided: boolean;
            detected?: components["schemas"]["IndustryDetected"] | null;
            /** Families */
            families?: {
                [key: string]: "on" | "off";
            };
            /** Industry Code */
            industry_code?: string | null;
        };
        /** IndustryOption */
        IndustryOption: {
            /** Code */
            code: string;
            /** Label */
            label: string;
        };
        /** IndustryPut */
        IndustryPut: {
            /** Cards */
            cards?: {
                [key: string]: "applied" | "alt";
            };
            /** Code */
            code?: string | null;
            /**
             * Decided
             * @default true
             */
            decided: boolean;
            /**
             * Families
             * @description {MI, VP, SS}: 켬/끔
             */
            families?: {
                [key: string]: boolean;
            };
            /**
             * Keep Default
             * @description 「기본 템플릿 유지」 — 세 계열 끔 · 결정함 · PR3
             * @default false
             */
            keep_default: boolean;
        };
        /** IndustryStats */
        IndustryStats: {
            /**
             * Cases
             * @default 0
             */
            cases: number;
            /**
             * Labels
             * @description 3열 머리 「고객이 요구한 것 · 사례 23건 중」 …
             */
            labels?: string[];
            /** Needs */
            needs?: components["schemas"]["StatRow"][];
            /** Products */
            products?: components["schemas"]["StatRow"][];
            /** Solutions */
            solutions?: components["schemas"]["StatRow"][];
        };
        /** IndustryView */
        IndustryView: {
            /** Applied Count */
            applied_count: number;
            /**
             * Ask
             * @description 선택 필요 — 업종 바꾸기 목록을 연 채로 시작
             * @default false
             */
            ask: boolean;
            /**
             * Can Apply
             * @default true
             */
            can_apply: boolean;
            /**
             * Decided
             * @default false
             */
            decided: boolean;
            detected: components["schemas"]["IndustryDetectedView"];
            /** Families */
            families: components["schemas"]["IndustryFamily"][];
            /**
             * Footer Note
             * @default 업종 레이아웃은 섹션 작성의 템플릿 고르기 맨 앞에도 나와요.
             */
            footer_note: string;
            /** Header Label */
            header_label: string;
            /** Intro */
            intro: string;
            next?: components["schemas"]["NextStep"] | null;
            /** Options */
            options: components["schemas"]["IndustryOption"][];
            stats: components["schemas"]["IndustryStats"];
        };
        /** JobAccepted */
        JobAccepted: {
            /** Export Id */
            export_id?: string | null;
            /** Import Id */
            import_id?: string | null;
            /** Job Id */
            job_id: string;
            /**
             * Kind
             * @description 잡 종류(proposal.section_fill 등)
             */
            kind: string;
            /** Proposal Id */
            proposal_id?: string | null;
            /** Reuse Id */
            reuse_id?: string | null;
            /** Section Key */
            section_key?: string | null;
            /** Sheet Id */
            sheet_id?: string | null;
            /**
             * Status
             * @default queued
             */
            status: string;
        };
        /** LinkedSource */
        LinkedSource: {
            /** Created At */
            created_at: string;
            /** Feature */
            feature: string;
            /** Feature Label */
            feature_label: string;
            /** Id */
            id: string;
            /**
             * Label
             * @description 칩 이름(「MI · A 커피 시장·경쟁사 분석」)
             */
            label: string;
            /** Latest Version */
            latest_version?: number | null;
            /** Ref Id */
            ref_id: string;
            /** Route */
            route?: string | null;
            /** Section Key */
            section_key?: string | null;
            /**
             * Stale
             * @default false
             */
            stale: boolean;
            /**
             * Status
             * @default linked
             * @enum {string}
             */
            status: "candidate" | "linked" | "removed";
            /** Title */
            title: string;
            /** Version At Link */
            version_at_link?: number | null;
            /** Via */
            via: string;
        };
        /** LinkIn */
        LinkIn: {
            /**
             * Feature
             * @description 기능(서비스 이름 mi · storyboard … 또는 코드 MI · SB …, kb_product · kb_solution · kb_case · kb_image · file)
             */
            feature: string;
            /**
             * Handoff Id
             * @description 넘김 기록 id(mi hof_ · spec sho_)
             */
            handoff_id?: string | null;
            /** Ref Id */
            ref_id: string;
            /** Section Key */
            section_key?: string | null;
            /** Title */
            title?: string | null;
            /** Version */
            version?: number | null;
        };
        /** LinkRemoved */
        LinkRemoved: {
            /** Link Id */
            link_id: string;
            /** Section Key */
            section_key?: string | null;
            /**
             * Toast
             * @default 연결 해제됨
             */
            toast: string;
        };
        /** LinksOut */
        LinksOut: {
            /** Links */
            links: components["schemas"]["LinkedSource"][];
            /**
             * On Count
             * @default 0
             */
            on_count: number;
            preview?: components["schemas"]["FillPreview"] | null;
        };
        /** LinksPut */
        LinksPut: {
            /** Links */
            links: components["schemas"]["LinkToggle"][];
        };
        /** LinkToggle */
        LinkToggle: {
            /** Feature */
            feature: string;
            /** On */
            on: boolean;
            /** Ref Id */
            ref_id: string;
            /** Section Key */
            section_key?: string | null;
        };
        /** LogoIn */
        LogoIn: {
            /** File Id */
            file_id: string;
        };
        /** MarkSubmitted */
        MarkSubmitted: {
            /** Submitted At */
            submitted_at?: string | null;
        };
        /** MasterCreated */
        MasterCreated: {
            /** Master Id */
            master_id: string;
            /** Name */
            name: string;
        };
        /** MasterOut */
        MasterOut: {
            /**
             * Builtin
             * @default true
             */
            builtin: boolean;
            /**
             * Desc
             * @default
             */
            desc: string;
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Preview Url */
            preview_url?: string | null;
            /**
             * Recommended
             * @default false
             */
            recommended: boolean;
            /**
             * Selected
             * @default false
             */
            selected: boolean;
        };
        /** MasterUpload */
        MasterUpload: {
            /** File Id */
            file_id: string;
            /** Name */
            name?: string | null;
        };
        /** Message */
        Message: {
            /** Change Ids */
            change_ids?: string[];
            /** Created At */
            created_at: string;
            /** Id */
            id: string;
            /** Job Id */
            job_id?: string | null;
            /**
             * Role
             * @enum {string}
             */
            role: "user" | "w";
            /**
             * Scope
             * @enum {string}
             */
            scope: "proposal" | "section" | "sheet" | "comment";
            /** Scope Ref */
            scope_ref?: string | null;
            /** Text */
            text: string;
        };
        /** MessageList */
        MessageList: {
            /** Items */
            items: components["schemas"]["Message"][];
        };
        /** ModePut */
        ModePut: {
            /**
             * Mode
             * @description PRU3 활용 방식 전환(계획을 그 방식으로)
             */
            mode?: ("improve" | "borrow") | null;
            /**
             * Mode Pref
             * @description PR1C 라디오 — 저장만(분석은 그대로)
             */
            mode_pref?: ("improve" | "borrow" | "auto") | null;
        };
        /** NextStep */
        NextStep: {
            /**
             * Label
             * @default
             */
            label: string;
            /** Route */
            route: string;
            /**
             * Target
             * @enum {string}
             */
            target: "industry" | "sections" | "compose" | "type" | "design" | "result";
        };
        /** NotesGenerate */
        NotesGenerate: {
            /**
             * Only Empty
             * @default true
             */
            only_empty: boolean;
        };
        /** Ok */
        Ok: {
            /**
             * Ok
             * @default true
             */
            ok: boolean;
        };
        /** OneClickBrief */
        OneClickBrief: {
            /**
             * Auto From Step
             * @default 4
             */
            auto_from_step: number;
            /** Job Id */
            job_id: string;
            /**
             * Pct
             * @default 0
             */
            pct: number;
            /** Route */
            route: string;
            /** Status */
            status: string;
        };
        /** OneClickFile */
        OneClickFile: {
            /** Meta */
            meta: string;
            /** Name */
            name: string;
            /** Pdf File Id */
            pdf_file_id?: string | null;
            /** Pptx File Id */
            pptx_file_id?: string | null;
            /** Pptx Url */
            pptx_url?: string | null;
        };
        /** OneClickMemo */
        OneClickMemo: {
            /** Applied At */
            applied_at?: string | null;
            /** At */
            at: string;
            /**
             * Status Label
             * @default
             */
            status_label: string;
            /** Text */
            text: string;
        };
        /** OneClickOptions */
        OneClickOptions: {
            /**
             * Collect Reviews
             * @default true
             */
            collect_reviews: boolean;
            /**
             * Mark Inferred
             * @default true
             */
            mark_inferred: boolean;
        };
        /** OneClickPlan */
        OneClickPlan: {
            /** Confirmed */
            confirmed: string[];
            /**
             * Desc
             * @default 지금까지 확정한 내용은 그대로 두고, 남은 단계는 AI가 추론해 채운 뒤 최종 PPTX까지 만듭니다.
             */
            desc: string;
            /**
             * Eta Label
             * @default 약 1–2분
             */
            eta_label: string;
            /**
             * Footer Label
             * @default 약 1–2분 · 진행 중에도 다른 작업 가능
             */
            footer_label: string;
            /** From Section Key */
            from_section_key?: string | null;
            /** From Stage */
            from_stage: string;
            options?: components["schemas"]["OneClickOptions"];
            /** Rows */
            rows: components["schemas"]["PlanRow"][];
            /** Running Job Id */
            running_job_id?: string | null;
            /**
             * Summary
             * @description 「섹션 6 · 시트 19」 / 「남은 5단계 · 약 24시트」
             */
            summary: string;
            /**
             * Title
             * @default 딸깍으로 나머지를 완성할까요?
             */
            title: string;
        };
        /** OneClickStart */
        OneClickStart: {
            /** From Section Key */
            from_section_key?: string | null;
            /** From Stage */
            from_stage?: string | null;
            options?: components["schemas"]["OneClickOptions"];
        };
        /** OneClickStep */
        OneClickStep: {
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Note */
            note: string;
            /**
             * Status
             * @enum {string}
             */
            status: "confirmed" | "inferred_done" | "running" | "waiting" | "skipped" | "canceled";
            /** Status Label */
            status_label: string;
        };
        /** OneClickView */
        OneClickView: {
            /** Auto From Step */
            auto_from_step: number;
            /**
             * Counts
             * @description {confirmed, inferred, review}
             */
            counts?: {
                [key: string]: number;
            };
            /**
             * Counts Label
             * @description 「확정 5」 「추론 16」 「검토 필요 3」
             */
            counts_label?: string[];
            /** Done Intro */
            done_intro?: string | null;
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            /**
             * Eta Label
             * @default
             */
            eta_label: string;
            file?: components["schemas"]["OneClickFile"] | null;
            /** From Section Key */
            from_section_key?: string | null;
            /** From Stage */
            from_stage: string;
            /**
             * Header
             * @description 「· 조감도부터 나머지 자동 완성」
             */
            header: string;
            /** Intro */
            intro: string;
            /** Job Id */
            job_id: string;
            /** Memos */
            memos?: components["schemas"]["OneClickMemo"][];
            /**
             * Next Route
             * @description 완료 → OneClickDone 또는 PR7(검토 모아 보기 끔), 중지 → 누른 단계 화면
             */
            next_route?: string | null;
            options: components["schemas"]["OneClickOptions"];
            /**
             * Pct
             * @default 0
             */
            pct: number;
            plan?: components["schemas"]["OneClickPlan"] | null;
            /**
             * Progress Label
             * @description 「45% · 약 1분 남음」
             * @default
             */
            progress_label: string;
            /**
             * Rest Label
             * @default
             */
            rest_label: string;
            /**
             * Review Header
             * @default
             */
            review_header: string;
            /** Review Items */
            review_items?: components["schemas"]["ConfirmItem"][];
            /**
             * Slides Label
             * @description 「표준 제안서 · 21장」
             * @default
             */
            slides_label: string;
            /**
             * Status
             * @enum {string}
             */
            status: "running" | "succeeded" | "canceled" | "failed" | "queued";
            /** Steps */
            steps: components["schemas"]["OneClickStep"][];
            /** Thumbs */
            thumbs?: components["schemas"]["SlideThumb"][];
            /**
             * Type Label
             * @default
             */
            type_label: string;
        };
        /** OnlyInSource */
        OnlyInSource: {
            /** Label */
            label: string;
            /**
             * Tag
             * @enum {string}
             */
            tag: "제외 제안" | "비복제";
        };
        /** Owner */
        Owner: {
            /**
             * Initial
             * @default
             */
            initial: string;
            /** Name */
            name: string;
            /** User Id */
            user_id: string;
        };
        /** Phase */
        Phase: {
            /** Key */
            key: string;
            /** Label */
            label: string;
            /**
             * Status
             * @enum {string}
             */
            status: "done" | "busy" | "todo";
        };
        /** PinnedSheet */
        PinnedSheet: {
            /** Code */
            code: string;
            /** Sheet No */
            sheet_no: number;
        };
        /** PlanBorrow */
        PlanBorrow: {
            /** Counts */
            counts: {
                [key: string]: number;
            };
            /**
             * Footer Label
             * @default
             */
            footer_label: string;
            /** Not Take */
            not_take: components["schemas"]["TakeItem"][];
            /** Rows */
            rows: components["schemas"]["BorrowRow"][];
            /** Sections */
            sections: number;
            /** Sheets */
            sheets: number;
            /** Take */
            take: components["schemas"]["TakeItem"][];
        };
        /** PlanConfirm */
        PlanConfirm: {
            /**
             * Then
             * @default sections
             * @enum {string}
             */
            then: "sections" | "compose";
        };
        /** PlanImprove */
        PlanImprove: {
            /**
             * Footer Label
             * @default
             */
            footer_label: string;
            /** Groups */
            groups: components["schemas"]["ReusePlanGroup"][];
            /** New Total */
            new_total: number;
            /** Only In Source */
            only_in_source: components["schemas"]["OnlyInSource"][];
            /** Requirement Coverage */
            requirement_coverage: components["schemas"]["Coverage"][];
            /**
             * Shown Label
             * @description 「12 / 21장 표시 · 나머지 9장 보기」
             * @default
             */
            shown_label: string;
            /** Source Total */
            source_total: number;
            /**
             * Summary Note
             * @default
             */
            summary_note: string;
            /** Totals */
            totals: {
                [key: string]: number;
            };
        };
        /** PlanRow */
        PlanRow: {
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Note */
            note: string;
        };
        /** PreGenerate */
        PreGenerate: {
            /** Empty Sections */
            empty_sections?: components["schemas"]["RouteRef"][];
            /**
             * Empty Sheet Count
             * @default 0
             */
            empty_sheet_count: number;
            /**
             * Notice
             * @description 「자료 없는 시트 {{n}}장 · 딸깍으로 채우기」
             */
            notice?: string | null;
        };
        /** Presentation */
        Presentation: {
            /** Date */
            date?: string | null;
            /** Duration Min */
            duration_min?: number | null;
            /**
             * Label
             * @description 「2026-10-22 · 발표 20분」
             */
            label?: string | null;
        };
        /** Proposal */
        Proposal: {
            /** Budget Text */
            budget_text?: string | null;
            /** Created At */
            created_at: string;
            /** Current Section Key */
            current_section_key?: string | null;
            customer: components["schemas"]["Customer"];
            derived_from?: components["schemas"]["DerivedFrom"] | null;
            design: components["schemas"]["Design"];
            /**
             * Edits Since Version
             * @default 0
             */
            edits_since_version: number;
            files?: components["schemas"]["Files"];
            /** Id */
            id: string;
            industry_layout: components["schemas"]["IndustryLayout"];
            /**
             * Language
             * @default ko
             * @enum {string}
             */
            language: "ko" | "en";
            /**
             * Link Count
             * @default 0
             */
            link_count: number;
            one_click?: components["schemas"]["OneClickBrief"] | null;
            /**
             * Open Confirm Count
             * @default 0
             */
            open_confirm_count: number;
            owner: components["schemas"]["Owner"];
            /** Progress Label */
            progress_label: string;
            /** Project Id */
            project_id?: string | null;
            reuse?: components["schemas"]["ReuseRef"] | null;
            /**
             * Rev
             * @description 자동 저장 리비전 — If-Match 로 보낸다
             */
            rev: number;
            review?: components["schemas"]["ReviewBrief"] | null;
            /**
             * Route
             * @description 지금 단계 화면(「이어서 작성」)
             */
            route: string;
            rq_ref?: components["schemas"]["RqRef"] | null;
            schedule: components["schemas"]["Schedule"];
            /** Sections */
            sections?: components["schemas"]["SectionSummary"][];
            /**
             * Sheet Total
             * @default 0
             */
            sheet_total: number;
            /** Sheets */
            sheets?: components["schemas"]["SheetSummary"][];
            /**
             * Slides Total
             * @default 0
             */
            slides_total: number;
            /** Stage */
            stage: string;
            /** Stage No */
            stage_no: number;
            /** Start Files */
            start_files?: string[];
            /** Start Mode */
            start_mode: string;
            /**
             * Status
             * @enum {string}
             */
            status: "draft" | "review" | "done";
            /** Status Label */
            status_label: string;
            stepper: components["schemas"]["Stepper"];
            /** Steps Done */
            steps_done: number;
            /** Submitted At */
            submitted_at?: string | null;
            /** Title */
            title: string;
            /**
             * Title Display
             * @description 빈 제목이면 「새 제안서」
             */
            title_display: string;
            /** Type */
            type?: ("standard" | "quickwin" | "solution") | null;
            /** Type Label */
            type_label?: string | null;
            /** Type Name */
            type_name?: string | null;
            /** Type Source */
            type_source?: string | null;
            /** Updated At */
            updated_at: string;
            /**
             * Version
             * @description 저장된 최신 버전 번호(첫 PPTX 생성 전 0)
             * @default 0
             */
            version: number;
        };
        /** ProposalAction */
        ProposalAction: {
            /**
             * Label
             * @description 검토 보기 · 버전 보기 · 확인할 곳 · 이어서 작성 · 복제해서 시작
             */
            label: string;
            /** Route */
            route: string;
        };
        /** ProposalCounts */
        ProposalCounts: {
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
             * Review
             * @default 0
             */
            review: number;
        };
        /** ProposalCreate */
        ProposalCreate: {
            customer?: components["schemas"]["CustomerIn"] | null;
            /**
             * Image Version
             * @description IMG4 「새 제안서로 시작」 이미지 버전(imv_…)
             */
            image_version?: string | null;
            /** Language */
            language?: ("ko" | "en") | null;
            /** Links */
            links?: components["schemas"]["LinkIn"][];
            /** Project Id */
            project_id?: string | null;
            rq_ref?: components["schemas"]["RqRef"] | null;
            schedule?: components["schemas"]["Schedule"] | null;
            /**
             * Source Proposal Id
             * @description 복제해서 시작(PR1C 원본)
             */
            source_proposal_id?: string | null;
            /**
             * Start Mode
             * @default blank
             * @enum {string}
             */
            start_mode: "blank" | "rfp" | "works" | "reuse" | "handoff";
            /** Title */
            title?: string | null;
        };
        /** ProposalList */
        ProposalList: {
            counts: components["schemas"]["ProposalCounts"];
            /** Due Within 14D */
            due_within_14d: number;
            /** Items */
            items: components["schemas"]["ProposalRow"][];
            /** My Review Turn */
            my_review_turn: number;
            /** Next Cursor */
            next_cursor?: string | null;
            /**
             * Range Label
             * @description 「1–6 / 6」
             * @default
             */
            range_label: string;
            /**
             * Summary Label
             * @description 「전체 6건 · 2주 안에 마감 3건 · 내 검토 차례 1건」
             */
            summary_label: string;
            /** Total */
            total: number;
        };
        /** ProposalPatch */
        ProposalPatch: {
            /** Budget Text */
            budget_text?: string | null;
            /** Current Section Key */
            current_section_key?: string | null;
            customer?: components["schemas"]["CustomerIn"] | null;
            /** Language */
            language?: ("ko" | "en") | null;
            /** Project Id */
            project_id?: string | null;
            rq_ref?: components["schemas"]["RqRef"] | null;
            schedule?: components["schemas"]["Schedule"] | null;
            /** Stage */
            stage?: ("customer" | "type" | "compose" | "industry" | "sections" | "design" | "result") | null;
            /** Title */
            title?: string | null;
        };
        /** ProposalRow */
        ProposalRow: {
            action: components["schemas"]["ProposalAction"];
            badge?: components["schemas"]["RowBadge"] | null;
            /** Current Step */
            current_step: number;
            /**
             * Customer Name
             * @default
             */
            customer_name: string;
            /**
             * D Day Label
             * @default
             */
            d_day_label: string;
            /** Due Date */
            due_date?: string | null;
            /**
             * Due Label
             * @default
             */
            due_label: string;
            /** Id */
            id: string;
            /**
             * Industry Label
             * @default
             */
            industry_label: string;
            /**
             * Meta
             * @description 「표준 제안서 · 작성 중」(IMG4 보낼 제안서)
             * @default
             */
            meta: string;
            /**
             * One Click Running
             * @default false
             */
            one_click_running: boolean;
            owner: components["schemas"]["Owner"];
            /** Progress Label */
            progress_label: string;
            /** Project Id */
            project_id?: string | null;
            /** Route */
            route: string;
            /** Short Title */
            short_title?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "draft" | "review" | "done";
            /** Status Label */
            status_label: string;
            /** Steps Done */
            steps_done: number;
            /**
             * Sub Label
             * @description 「의료 · 요양 · PPTX v2」
             * @default
             */
            sub_label: string;
            /**
             * Subtitle
             * @description sub_label 과 같다(Spec SP4 · 이미지 IMG4 목록용)
             * @default
             */
            subtitle: string;
            /** Title */
            title: string;
            /** Type */
            type?: ("standard" | "quickwin" | "solution") | null;
            /** Type Label */
            type_label?: string | null;
            /** Updated At */
            updated_at: string;
            /**
             * Urgent
             * @default false
             */
            urgent: boolean;
            /**
             * Version
             * @default 0
             */
            version: number;
        };
        /** PullLines */
        PullLines: {
            /**
             * All
             * @default false
             */
            all: boolean;
            /** Line Ids */
            line_ids?: string[] | null;
        };
        /** QuestionIn */
        QuestionIn: {
            /**
             * Push To Rq
             * @default true
             */
            push_to_rq: boolean;
        };
        /** QuestionOut */
        QuestionOut: {
            /**
             * Pushed
             * @default false
             */
            pushed: boolean;
            /** Question Id */
            question_id?: string | null;
            /** Text */
            text: string;
        };
        /** RailItem */
        RailItem: {
            /** Count */
            count: number;
            /** Current */
            current: boolean;
            /** Done */
            done: boolean;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** Optional */
            optional: boolean;
            /** Route */
            route: string;
            /**
             * Title
             * @description 선택 섹션 title 「{{이름}} (선택 섹션)」
             */
            title?: string | null;
        };
        /** RailSection */
        RailSection: {
            /** Key */
            key: string;
            /**
             * Label
             * @description 「06 유관 사례」
             */
            label: string;
            /** Name */
            name: string;
            /** No */
            no: number;
            /** Sheets */
            sheets: components["schemas"]["RailSheet"][];
        };
        /** RailSheet */
        RailSheet: {
            /**
             * Aria Label
             * @default
             */
            aria_label: string;
            /**
             * Confirm
             * @default false
             */
            confirm: boolean;
            /**
             * Edited
             * @default false
             */
            edited: boolean;
            /**
             * Inferred
             * @default false
             */
            inferred: boolean;
            /** Sheet Id */
            sheet_id: string;
            /** Sheet No */
            sheet_no: number;
            /** Thumb Url */
            thumb_url?: string | null;
            /** Title */
            title: string;
        };
        /** RecommendedType */
        RecommendedType: {
            /** Name */
            name: string;
            /** Reason */
            reason: string;
            /**
             * Type
             * @enum {string}
             */
            type: "standard" | "quickwin" | "solution";
        };
        /** RelatedWork */
        RelatedWork: {
            /**
             * Customer Match
             * @default true
             */
            customer_match: boolean;
            /**
             * Default On
             * @default false
             */
            default_on: boolean;
            /** Feature */
            feature: string;
            /**
             * Meta
             * @default
             */
            meta: string;
            /**
             * On
             * @default false
             */
            on: boolean;
            /** Ref Id */
            ref_id: string;
            /** Route */
            route?: string | null;
            /**
             * Target Label
             * @default
             */
            target_label: string;
            /** Target Sections */
            target_sections?: string[];
            /** Title */
            title: string;
            /** Tool Label */
            tool_label: string;
            /** Updated At */
            updated_at?: string | null;
            /** Version */
            version?: number | null;
        };
        /** RelatedWorks */
        RelatedWorks: {
            /**
             * Customer Name
             * @default
             */
            customer_name: string;
            /**
             * Footer Label
             * @default
             */
            footer_label: string;
            /**
             * Header Label
             * @description 「연결할 작업 4 / 6」
             * @default
             */
            header_label: string;
            /**
             * Intro
             * @default
             */
            intro: string;
            /** On Count */
            on_count: number;
            preview: components["schemas"]["FillPreview"];
            /**
             * Scope
             * @enum {string}
             */
            scope: "customer" | "all";
            /** Work Count */
            work_count: number;
            /** Works */
            works: components["schemas"]["RelatedWork"][];
        };
        /** RenderIn */
        RenderIn: {
            /** Sheet Ids */
            sheet_ids?: string[] | null;
        };
        /** ResearchIn */
        ResearchIn: {
            /** Ids */
            ids?: string[] | null;
            /** Instruction */
            instruction?: string | null;
        };
        /** RestoreIn */
        RestoreIn: {
            /**
             * Scope
             * @default all
             * @enum {string}
             */
            scope: "all" | "sheet";
            /** Sheet Id */
            sheet_id?: string | null;
        };
        /** RestoreResult */
        RestoreResult: {
            /** Change Ids */
            change_ids?: string[];
            /** New Version */
            new_version?: number | null;
            /** Scope */
            scope: string;
        };
        /** ResubmitIn */
        ResubmitIn: {
            /** Message */
            message?: string | null;
        };
        /** ResultFile */
        ResultFile: {
            /** Created At */
            created_at?: string | null;
            /**
             * Created Label
             * @default 방금 생성
             */
            created_label: string;
            /**
             * Meta
             * @description 「24 슬라이드 · 표준 제안서 8섹션 · 방금 생성 · 노트 3건」
             * @default
             */
            meta: string;
            /** Name */
            name: string;
            /** Notes Count */
            notes_count: number;
            /** Pdf File Id */
            pdf_file_id?: string | null;
            /** Pdf Url */
            pdf_url?: string | null;
            /** Pptx File Id */
            pptx_file_id?: string | null;
            /** Pptx Url */
            pptx_url?: string | null;
            /** Sections */
            sections: number;
            /** Sheets */
            sheets: number;
            /** Slides */
            slides: number;
            /** Type Label */
            type_label: string;
            /** Version */
            version: number;
        };
        /** ResultView */
        ResultView: {
            /**
             * Derived
             * @description 파생 제안서(PRU5 자리)
             * @default false
             */
            derived: boolean;
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            file?: components["schemas"]["ResultFile"] | null;
            /**
             * Footer Label
             * @default PPTX 생성 · 6 / 6 · 완료
             */
            footer_label: string;
            /** Job Id */
            job_id?: string | null;
            /**
             * Message
             * @default
             */
            message: string;
            /** Ranges */
            ranges?: components["schemas"]["SlideRange"][];
            /**
             * Ranges Label
             * @default
             */
            ranges_label: string;
            /** @description 「{{섹션}} 섹션만 재생성」 칩(label · section_key 는 route 마지막) */
            regen_section?: components["schemas"]["RouteRef"] | null;
            /** Regen Section Key */
            regen_section_key?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "none" | "running" | "done" | "failed";
            /** Summary Route */
            summary_route?: string | null;
            /** Thumbs */
            thumbs?: components["schemas"]["SlideThumb"][];
        };
        /** ReuseCandidate */
        ReuseCandidate: {
            /** Name */
            name: string;
            /** Proposal Id */
            proposal_id: string;
            /** Version */
            version?: number | null;
            /**
             * Why
             * @enum {string}
             */
            why: "같은 고객" | "같은 솔루션";
        };
        /** ReuseCandidates */
        ReuseCandidates: {
            /** Items */
            items: components["schemas"]["ReuseCandidate"][];
            /**
             * Label
             * @description 「내 제안서 목록에서는 2개 추천」
             * @default
             */
            label: string;
        };
        /** ReuseConfirmOut */
        ReuseConfirmOut: {
            /** Job Id */
            job_id?: string | null;
            /** Route */
            route?: string | null;
            /** Status */
            status: string;
        };
        /** ReuseCriterion */
        ReuseCriterion: {
            /** Confidence */
            confidence: number;
            /** Key */
            key: string;
            /** Must */
            must: boolean;
            /** Name */
            name: string;
            /** No */
            no: number;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "need" | "edited";
            /** State Label */
            state_label: string;
            /** Summary */
            summary: string;
            /** Warn */
            warn: boolean;
        };
        /** ReuseFlow */
        ReuseFlow: {
            /** Broken */
            broken?: string[];
            /** Claims */
            claims?: {
                [key: string]: number;
            };
            /** Memos */
            memos?: components["schemas"]["FlowMemo"][];
            /** Pattern */
            pattern?: {
                [key: string]: string;
            };
            /** Steps */
            steps: components["schemas"]["FlowStep"][];
        };
        /** ReuseLine */
        ReuseLine: {
            /** Line Id */
            line_id: string;
            /**
             * Mark
             * @enum {string}
             */
            mark: "keep" | "update" | "new" | "drop";
            /** Source Line Id */
            source_line_id?: string | null;
        };
        /** ReuseLineView */
        ReuseLineView: {
            /** Badge */
            badge?: string | null;
            /** Draft Text */
            draft_text?: string | null;
            /**
             * Edited
             * @default false
             */
            edited: boolean;
            /** Id */
            id: string;
            /**
             * Mark
             * @enum {string}
             */
            mark: "keep" | "update" | "new" | "drop";
            /** Source Line Id */
            source_line_id?: string | null;
            /** Text */
            text: string;
        };
        /** ReusePage */
        ReusePage: {
            /**
             * Evidence
             * @default
             */
            evidence: string;
            /**
             * Evidence Warn
             * @default false
             */
            evidence_warn: boolean;
            /** Exclude Reason */
            exclude_reason?: string | null;
            /**
             * Excluded
             * @default false
             */
            excluded: boolean;
            /** File Page */
            file_page?: number | null;
            /** Flow Role */
            flow_role?: string | null;
            /**
             * Locked
             * @default false
             */
            locked: boolean;
            /** No */
            no: number;
            /** Role Candidates */
            role_candidates?: string[];
            /**
             * Role State
             * @default auto
             * @enum {string}
             */
            role_state: "auto" | "ok" | "edited" | "need";
            /**
             * Role State Label
             * @default
             */
            role_state_label: string;
            /**
             * Section Color
             * @default
             */
            section_color: string;
            /**
             * Section Name
             * @default
             */
            section_name: string;
            /**
             * Source Idx
             * @default 0
             */
            source_idx: number;
            /**
             * Text Excerpt
             * @default
             */
            text_excerpt: string;
            /** Thumb Url */
            thumb_url?: string | null;
            /** Title */
            title: string;
        };
        /** ReusePlanGroup */
        ReusePlanGroup: {
            /** Count */
            count: number;
            /**
             * Is New
             * @default false
             */
            is_new: boolean;
            /**
             * Label
             * @default
             */
            label: string;
            /** Name */
            name: string;
            /**
             * Range
             * @default
             */
            range: string;
            /** Rows */
            rows: components["schemas"]["ReusePlanRow"][];
        };
        /** ReusePlanRow */
        ReusePlanRow: {
            /** Group */
            group: string;
            /**
             * Locked
             * @default false
             */
            locked: boolean;
            /**
             * Noncopy
             * @default false
             */
            noncopy: boolean;
            /** Note */
            note: string;
            /** Page */
            page?: number | null;
            /**
             * Page Label
             * @default
             */
            page_label: string;
            /** Row Id */
            row_id: string;
            /** Rq Ids */
            rq_ids?: string[];
            /** Sheet Name */
            sheet_name: string;
            /** Thumb Kind */
            thumb_kind?: string | null;
            /**
             * Verdict
             * @enum {string}
             */
            verdict: "keep" | "update" | "rewrite" | "new" | "drop";
            /** Verdict Label */
            verdict_label: string;
        };
        /** ReuseRecommendation */
        ReuseRecommendation: {
            /** Badge */
            badge: string;
            /**
             * Mode
             * @enum {string}
             */
            mode: "improve" | "borrow";
            /** Reason */
            reason: string;
        };
        /** ReuseRef */
        ReuseRef: {
            /** Mode */
            mode?: ("improve" | "borrow") | null;
            /** Reuse Id */
            reuse_id: string;
        };
        /** ReuseSection */
        ReuseSection: {
            /** Color */
            color: string;
            /** Count */
            count: number;
            /**
             * Excluded
             * @default false
             */
            excluded: boolean;
            /** Name */
            name: string;
        };
        /** ReuseSectionView */
        ReuseSectionView: {
            /** Compare Disabled Reason */
            compare_disabled_reason?: string | null;
            /**
             * Footer Label
             * @default
             */
            footer_label: string;
            /** Guide */
            guide?: components["schemas"]["GuideStep"][];
            /**
             * Guide Label
             * @default
             */
            guide_label: string;
            /** Header Label */
            header_label: string;
            /**
             * Mode
             * @enum {string}
             */
            mode: "improve" | "borrow";
            new_sheet: components["schemas"]["ReuseSheetSide"];
            /** Placeholders */
            placeholders?: {
                [key: string]: unknown;
            }[];
            /** Section Key */
            section_key: string;
            /** Section Sheets */
            section_sheets?: {
                [key: string]: unknown;
            }[];
            /** Sheet Id */
            sheet_id?: string | null;
            /**
             * Source Label
             * @default
             */
            source_label: string;
            source_sheet?: components["schemas"]["ReuseSheetSide"] | null;
            /** Tally */
            tally?: {
                [key: string]: number;
            };
            /**
             * View
             * @enum {string}
             */
            view: "compare" | "guide" | "new_only";
        };
        /** ReuseSheetSide */
        ReuseSheetSide: {
            /**
             * Images Note
             * @default
             */
            images_note: string;
            /**
             * Kind Label
             * @default
             */
            kind_label: string;
            /** Lines */
            lines?: components["schemas"]["ReuseLineView"][];
            /**
             * Note
             * @default
             */
            note: string;
            /** Page */
            page?: number | null;
            /**
             * Page Label
             * @default
             */
            page_label: string;
            /**
             * Rq Label
             * @default
             */
            rq_label: string;
            /** Sheet Id */
            sheet_id?: string | null;
            /** Thumb Url */
            thumb_url?: string | null;
            /**
             * Title
             * @default
             */
            title: string;
            /**
             * Title Label
             * @default
             */
            title_label: string;
        };
        /** ReuseSourceIn */
        ReuseSourceIn: {
            /** File Id */
            file_id?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "proposal" | "file";
            /** Proposal Id */
            proposal_id?: string | null;
            /** Version */
            version?: number | null;
        };
        /** ReuseSourceOut */
        ReuseSourceOut: {
            /** Author */
            author?: string | null;
            /** Customer */
            customer?: string | null;
            /** Doc Date */
            doc_date?: string | null;
            /** File Id */
            file_id?: string | null;
            /** Format */
            format: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "proposal" | "file";
            /**
             * Meta Label
             * @description 「PPTX · 24장 · 2024.09 · 김하늘(동료)」
             * @default
             */
            meta_label: string;
            /** Name */
            name: string;
            /**
             * Pages
             * @default 0
             */
            pages: number;
            /** Phases */
            phases?: components["schemas"]["Phase"][];
            /** Proposal Id */
            proposal_id?: string | null;
            /** Version */
            version?: number | null;
        };
        /** ReuseStart */
        ReuseStart: {
            /**
             * Mode Pref
             * @default auto
             * @enum {string}
             */
            mode_pref: "improve" | "borrow" | "auto";
            /** New Title */
            new_title?: string | null;
            /**
             * Replace
             * @description false = 분석 중인 원본에 더함(파일 더 놓기), true = 이 목록으로 바꿈(원본 빼기)
             * @default false
             */
            replace: boolean;
            /** Sources */
            sources: components["schemas"]["ReuseSourceIn"][];
        };
        /** ReuseSummary */
        ReuseSummary: {
            /** Changed Count */
            changed_count: number;
            /** Counts */
            counts: components["schemas"]["SummaryCount"][];
            /**
             * File Label
             * @default
             */
            file_label: string;
            /** Footer Label */
            footer_label: string;
            /** Intro */
            intro: string;
            /** Mapping */
            mapping: components["schemas"]["SummaryMapRow"][];
            /** Mapping Label */
            mapping_label: string;
            /** Review Items */
            review_items: components["schemas"]["ConfirmItem"][];
            /**
             * Review More Label
             * @default
             */
            review_more_label: string;
            /** Review Total */
            review_total: number;
            /** Traces */
            traces: components["schemas"]["TraceRow"][];
        };
        /** ReuseView */
        ReuseView: {
            /**
             * Band Label
             * @description 「원본 24장 · 외부 파일 · 섹션 8개」
             * @default
             */
            band_label: string;
            /**
             * Can Confirm
             * @default false
             */
            can_confirm: boolean;
            /**
             * Confirmed Count
             * @default 0
             */
            confirmed_count: number;
            /** Context */
            context?: {
                [key: string]: unknown;
            };
            /** Criteria */
            criteria?: components["schemas"]["ReuseCriterion"][];
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            /**
             * Excluded Page Count
             * @default 0
             */
            excluded_page_count: number;
            flow?: components["schemas"]["ReuseFlow"] | null;
            /**
             * Footer Label
             * @default
             */
            footer_label: string;
            /** Id */
            id: string;
            /**
             * Intro
             * @default
             */
            intro: string;
            /** Job Id */
            job_id?: string | null;
            /** Job Status */
            job_status?: string | null;
            /** Mode */
            mode?: ("improve" | "borrow") | null;
            /**
             * Mode Pref
             * @enum {string}
             */
            mode_pref: "improve" | "borrow" | "auto";
            /**
             * Must Done
             * @default 0
             */
            must_done: number;
            /**
             * Must Total
             * @default 3
             */
            must_total: number;
            /** Pages */
            pages?: components["schemas"]["ReusePage"][];
            /** Phases */
            phases: components["schemas"]["Phase"][];
            plan_borrow?: components["schemas"]["PlanBorrow"] | null;
            plan_improve?: components["schemas"]["PlanImprove"] | null;
            /** Proposal Id */
            proposal_id: string;
            recommendation?: components["schemas"]["ReuseRecommendation"] | null;
            /** Source Sections */
            source_sections?: components["schemas"]["ReuseSection"][];
            /** Sources */
            sources: components["schemas"]["ReuseSourceOut"][];
            /**
             * Status
             * @enum {string}
             */
            status: "analyzing" | "awaiting_confirm" | "planning" | "awaiting_plan_confirm" | "applied" | "failed";
            /** Status Label */
            status_label: string;
        };
        /** RevertResult */
        RevertResult: {
            /**
             * Change Id
             * @description 새로 기록한 반대 변경
             */
            change_id: string;
            /** Reverted Change Id */
            reverted_change_id: string;
            /** Sheet Id */
            sheet_id?: string | null;
        };
        /** ReviewBrief */
        ReviewBrief: {
            /**
             * Approvals
             * @default 0
             */
            approvals: number;
            /**
             * Changes Requested
             * @default 0
             */
            changes_requested: number;
            /** Due Date */
            due_date?: string | null;
            /** My Turn User Ids */
            my_turn_user_ids?: string[];
            /** Requested At */
            requested_at?: string | null;
            /** Review Id */
            review_id: string;
            /**
             * Reviewers Total
             * @default 0
             */
            reviewers_total: number;
            /**
             * Status
             * @default pending
             */
            status: string;
            /** Version */
            version: number;
        };
        /** Reviewer */
        Reviewer: {
            /** Initial */
            initial: string;
            /**
             * Me
             * @default false
             */
            me: boolean;
            /** Name */
            name: string;
            /**
             * Role
             * @default
             */
            role: string;
            /**
             * Status
             * @enum {string}
             */
            status: "approved" | "changes_requested" | "pending";
            /** Status Label */
            status_label: string;
            /** User Id */
            user_id: string;
        };
        /** ReviewInfo */
        ReviewInfo: {
            /** Due Date */
            due_date?: string | null;
            /** Id */
            id: string;
            /** Message */
            message?: string | null;
            /** Requested At */
            requested_at?: string | null;
            /**
             * Requester Name
             * @default
             */
            requester_name: string;
            /**
             * Sent Label
             * @description 「오늘 11:00 보냄 · 마감 10월 8일 (수)」
             * @default
             */
            sent_label: string;
            /** Status */
            status: string;
            /** Status Label */
            status_label: string;
            /** Version */
            version: number;
        };
        /** ReviewRequestIn */
        ReviewRequestIn: {
            /** Due Date */
            due_date?: string | null;
            /** Message */
            message?: string | null;
            /** Reviewer Ids */
            reviewer_ids: string[];
        };
        /** ReviewView */
        ReviewView: {
            approvals: components["schemas"]["Approvals"];
            /**
             * Can Decide
             * @default false
             */
            can_decide: boolean;
            /** Check Grid */
            check_grid?: components["schemas"]["CheckCell"][];
            /**
             * Check Label
             * @default
             */
            check_label: string;
            /** Comment Sheets */
            comment_sheets?: components["schemas"]["CommentSheet"][];
            /**
             * Comment Target
             * @description workspace 코멘트 target 접두(proposal:pr_…)
             */
            comment_target: string;
            /**
             * Comments Open
             * @default 0
             */
            comments_open: number;
            /**
             * Comments Resolved
             * @default 0
             */
            comments_resolved: number;
            /**
             * My Turn
             * @default false
             */
            my_turn: boolean;
            review?: components["schemas"]["ReviewInfo"] | null;
            /** Reviewers */
            reviewers?: components["schemas"]["Reviewer"][];
            /**
             * Share Permission Label
             * @default 팀 내부 · 코멘트 가능
             */
            share_permission_label: string;
            /**
             * Suggest Text
             * @description 「열린 코멘트 {{n}}건을 반영한 수정안을 만들 수 있어요. …」
             */
            suggest_text?: string | null;
            /**
             * Version Label
             * @default
             */
            version_label: string;
        };
        /** RewriteOptions */
        RewriteOptions: {
            /**
             * Concise
             * @default false
             */
            concise: boolean;
            /**
             * Emphasize Numbers
             * @default false
             */
            emphasize_numbers: boolean;
            /**
             * Same Template
             * @default true
             */
            same_template: boolean;
        };
        /** RfpExcerpt */
        RfpExcerpt: {
            /** Page */
            page?: number | null;
            /** Page Label */
            page_label: string;
            /** Parts */
            parts: components["schemas"]["RfpExcerptPart"][];
        };
        /** RfpExcerptPart */
        RfpExcerptPart: {
            /** Field No */
            field_no?: number | null;
            /** Text */
            text: string;
        };
        /** RfpField */
        RfpField: {
            /**
             * Edited
             * @default false
             */
            edited: boolean;
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** No */
            no: number;
            source?: components["schemas"]["RfpSource"] | null;
            /**
             * Source Label
             * @description 「p.11」, 없으면 「—」
             * @default —
             */
            source_label: string;
            /**
             * State
             * @enum {string}
             */
            state: "found" | "guess" | "empty";
            /** State Label */
            state_label: string;
            /**
             * Value
             * @default
             */
            value: string;
        };
        /** RfpFieldPut */
        RfpFieldPut: {
            /** Value */
            value: string;
        };
        /** RfpFile */
        RfpFile: {
            /** File Id */
            file_id: string;
            /**
             * Kind Label
             * @description 「PDF · 24쪽 · 방금 올림」
             * @default
             */
            kind_label: string;
            /** Name */
            name: string;
            /** Pages */
            pages?: number | null;
        };
        /** RfpSource */
        RfpSource: {
            /** File Id */
            file_id?: string | null;
            /** Page */
            page?: number | null;
            /** Page Label */
            page_label?: string | null;
            /** Quote */
            quote?: string | null;
        };
        /** RfpStart */
        RfpStart: {
            /**
             * Extra File Ids
             * @description 회의록
             */
            extra_file_ids?: string[];
            /** File Ids */
            file_ids: string[];
        };
        /** RfpTally */
        RfpTally: {
            /**
             * Empty
             * @default 0
             */
            empty: number;
            /**
             * Found
             * @default 0
             */
            found: number;
            /**
             * Guess
             * @default 0
             */
            guess: number;
        };
        /** RfpView */
        RfpView: {
            /**
             * Confirmed
             * @default false
             */
            confirmed: boolean;
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            /** Excerpts */
            excerpts?: components["schemas"]["RfpExcerpt"][];
            /** Extra Files */
            extra_files?: components["schemas"]["RfpFile"][];
            /** Fields */
            fields?: components["schemas"]["RfpField"][];
            /** Files */
            files?: components["schemas"]["RfpFile"][];
            /**
             * Found Count
             * @default 0
             */
            found_count: number;
            /**
             * Intro
             * @default
             */
            intro: string;
            /** Job Id */
            job_id?: string | null;
            /** Phases */
            phases?: components["schemas"]["Phase"][];
            /**
             * Rq Count
             * @default 0
             */
            rq_count: number;
            /**
             * Rq Label
             * @default
             */
            rq_label: string;
            rq_ref?: components["schemas"]["RqRef"] | null;
            /**
             * Status
             * @enum {string}
             */
            status: "none" | "running" | "done" | "failed";
            tally?: components["schemas"]["RfpTally"];
        };
        /** RolePut */
        RolePut: {
            /** Role */
            role: string;
        };
        /** RouteRef */
        RouteRef: {
            /** Label */
            label: string;
            /** Route */
            route: string;
        };
        /** RowBadge */
        RowBadge: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "comments" | "source_updated" | "confirm_needed";
            /** Label */
            label: string;
            /**
             * N
             * @default 0
             */
            n: number;
        };
        /** RqRef */
        RqRef: {
            /** Rq Id */
            rq_id: string;
            /** Version */
            version?: number | null;
        };
        /** Schedule */
        Schedule: {
            presentation?: components["schemas"]["Presentation"] | null;
            /**
             * Submit Due
             * @description 제안 제출일 YYYY-MM-DD(PR0 마감)
             */
            submit_due?: string | null;
        };
        /** SectionConfirmResult */
        SectionConfirmResult: {
            next: components["schemas"]["RouteRef"];
            proposal: components["schemas"]["Proposal"];
        };
        /** SectionFill */
        SectionFill: {
            /** Quick Action */
            quick_action?: string | null;
            /**
             * Reason
             * @default enter
             * @enum {string}
             */
            reason: "enter" | "sources_changed" | "regen";
        };
        /** SectionSheet */
        SectionSheet: {
            /**
             * Edited Since Version
             * @default false
             */
            edited_since_version: boolean;
            /** Evidence Note */
            evidence_note?: string | null;
            from?: components["schemas"]["SheetFrom"] | null;
            /**
             * Group Label
             * @description 솔루션 그룹(「MagicINFO」 · 「통합」)
             */
            group_label?: string | null;
            /** Id */
            id: string;
            /**
             * Inferred
             * @default false
             */
            inferred: boolean;
            /**
             * Open Confirm
             * @default 0
             */
            open_confirm: number;
            /** Role */
            role: string;
            /** Role Name */
            role_name: string;
            /** Sheet No */
            sheet_no: number;
            /** Solution Code */
            solution_code?: string | null;
            /** Status */
            status: string;
            /** Status Label */
            status_label: string;
            /** Tag */
            tag: string;
            /**
             * Template
             * @description 템플릿 코드(SP4 알림용)
             */
            template?: string | null;
            template_info: components["schemas"]["TemplateState"];
            /** Thumb Url */
            thumb_url?: string | null;
            /** Title */
            title: string;
        };
        /** SectionSummary */
        SectionSummary: {
            /** Confirmed */
            confirmed: boolean;
            /** Enabled */
            enabled: boolean;
            /**
             * Hidden
             * @default false
             */
            hidden: boolean;
            /** Id */
            id: string;
            /** Inferred */
            inferred: boolean;
            /** Key */
            key: string;
            /** Name */
            name: string;
            /** No */
            no: number;
            /** Optional */
            optional: boolean;
            /** Route */
            route: string;
            /** Sheet Count */
            sheet_count: number;
            /** Short */
            short: string;
            /** Status */
            status: string;
            /** Status Label */
            status_label: string;
        };
        /** SectionView */
        SectionView: {
            /** Accept Chips */
            accept_chips: string[];
            accepts: components["schemas"]["Accepts"];
            /**
             * Confirmed
             * @default false
             */
            confirmed: boolean;
            drop_hint: components["schemas"]["DropHint"];
            /**
             * Empty Sources Label
             * @default 아직 연결된 자료가 없어요 — 아래 영역에 끌어다 놓으세요
             */
            empty_sources_label: string;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /** Fill Job Id */
            fill_job_id?: string | null;
            /**
             * Header Label
             * @description 「Market Intelligence · 섹션 1 / 8 · 시트 3」
             */
            header_label: string;
            /**
             * Inferred
             * @default false
             */
            inferred: boolean;
            /** Intro */
            intro: string;
            /** Key */
            key: string;
            /** Name */
            name: string;
            /**
             * Needs Fill
             * @description 진입 시 :fill 을 불러야 함(연결 자료가 있고 초안이 없거나 stale)
             * @default false
             */
            needs_fill: boolean;
            next: components["schemas"]["RouteRef"];
            /** No */
            no: number;
            /**
             * Optional
             * @default false
             */
            optional: boolean;
            /**
             * Owner Name
             * @default
             */
            owner_name: string;
            /** Placeholder */
            placeholder: string;
            prev: components["schemas"]["RouteRef"];
            /** Proposal Id */
            proposal_id: string;
            /** Quick Actions */
            quick_actions: string[];
            /** Rail */
            rail: components["schemas"]["RailItem"][];
            /**
             * Request Label
             * @default 섹션 수정 요청
             */
            request_label: string;
            /** Reuse View */
            reuse_view?: ("compare" | "guide") | null;
            /** Section No */
            section_no: number;
            /** Sheet Label */
            sheet_label: string;
            /** Sheets */
            sheets: components["schemas"]["SectionSheet"][];
            /** Short */
            short: string;
            /** Sources */
            sources: components["schemas"]["SourceChip"][];
            /**
             * Status
             * @enum {string}
             */
            status: "empty" | "filling" | "ready" | "stale";
            /** Status Label */
            status_label: string;
            /** Total */
            total: number;
            /** Total Sheets */
            total_sheets: number;
            /**
             * Type
             * @enum {string}
             */
            type: "standard" | "quickwin" | "solution";
            /** Type Name */
            type_name: string;
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
        /** ShareLinkIn */
        ShareLinkIn: {
            /**
             * Permission
             * @default team_comment
             * @enum {string}
             */
            permission: "team_comment" | "team_view";
        };
        /** ShareLinkOut */
        ShareLinkOut: {
            /** Permission */
            permission: string;
            /** Permission Label */
            permission_label: string;
            /** Token */
            token?: string | null;
            /** Url */
            url: string;
        };
        /** Sheet */
        Sheet: {
            /** Confirm Items */
            confirm_items?: components["schemas"]["ConfirmBrief"][];
            /**
             * Confirm Label
             * @description 「이 시트에 확정 필요 1곳 · …」
             * @default
             */
            confirm_label: string;
            /**
             * Content
             * @description SheetContent(§5.3.1) — eyebrow · title · subtitle · slots · notes · footnotes. 값 토큰 {{fact:id}} 포함
             */
            content: {
                [key: string]: unknown;
            };
            /**
             * Display
             * @description 값 토큰을 표시 문자열로 바꾼 content(미리보기 · 편집 표시용)
             */
            display?: {
                [key: string]: unknown;
            };
            /**
             * Edited Since Version
             * @default false
             */
            edited_since_version: boolean;
            /** Evidence Note */
            evidence_note?: string | null;
            /** Facts */
            facts?: components["schemas"]["FactBrief"][];
            /** Id */
            id: string;
            /**
             * Inferred
             * @default false
             */
            inferred: boolean;
            /**
             * Msg
             * @default
             */
            msg: string;
            /** Order */
            order: number;
            /**
             * Origin
             * @default user
             */
            origin: string;
            /** Proposal Id */
            proposal_id: string;
            render?: components["schemas"]["SheetRender"] | null;
            /** Repeat Key */
            repeat_key?: {
                [key: string]: unknown;
            } | null;
            reuse?: components["schemas"]["SheetReuse"] | null;
            /** Rev */
            rev: number;
            /** Role */
            role: string;
            /** Role Name */
            role_name: string;
            /** Section Key */
            section_key: string;
            /** Section Name */
            section_name: string;
            /** Sheet No */
            sheet_no: number;
            /**
             * Slot Schema
             * @description export 템플릿 칸 정의(slots[] — id · type · box · capacity · fields)
             */
            slot_schema?: {
                [key: string]: unknown;
            } | null;
            /** Solution Code */
            solution_code?: string | null;
            /** Sources */
            sources?: components["schemas"]["SheetSourceRef"][];
            /** Split Of */
            split_of?: string | null;
            /** Status */
            status: string;
            /** Status Label */
            status_label: string;
            template: components["schemas"]["TemplateState"];
            /** Thumb Url */
            thumb_url?: string | null;
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
        };
        /** SheetFrom */
        SheetFrom: {
            /** Ref Id */
            ref_id?: string | null;
            /** Service */
            service: string;
            /** Sheet Id */
            sheet_id?: string | null;
        };
        /** SheetOp */
        SheetOp: {
            /**
             * From
             * @description move 의 출발 경로
             */
            from?: string | null;
            /**
             * Op
             * @enum {string}
             */
            op: "set" | "insert" | "delete" | "move";
            /**
             * Path
             * @description content 안 JSON pointer(예 /slots/table/rows/5/cells/1/text, /title)
             */
            path: string;
            /** Value */
            value?: unknown;
        };
        /** SheetPatch */
        SheetPatch: {
            /** Ops */
            ops: components["schemas"]["SheetOp"][];
            /** Reason */
            reason?: string | null;
        };
        /** SheetPatchResult */
        SheetPatchResult: {
            /** Change Ids */
            change_ids: string[];
            /**
             * Edits Since Version
             * @default 0
             */
            edits_since_version: number;
            /** Resolved Item Ids */
            resolved_item_ids?: string[];
            /** Rev */
            rev: number;
            sheet: components["schemas"]["Sheet"];
        };
        /** SheetRender */
        SheetRender: {
            /** Png File Id */
            png_file_id?: string | null;
            /** Rev */
            rev?: number | null;
            /** Status */
            status?: string | null;
            /** Url */
            url?: string | null;
        };
        /** SheetReuse */
        SheetReuse: {
            /** Flow Role */
            flow_role?: string | null;
            /** Lines */
            lines?: components["schemas"]["ReuseLine"][];
            /**
             * Note
             * @default
             */
            note: string;
            /** Source Page */
            source_page?: number | null;
            /**
             * Verdict
             * @enum {string}
             */
            verdict: "keep" | "update" | "rewrite" | "new" | "drop" | "auto";
        };
        /** SheetRewrite */
        SheetRewrite: {
            /** Instruction */
            instruction?: string | null;
            options?: components["schemas"]["RewriteOptions"];
            /** Target Path */
            target_path?: string | null;
        };
        /** SheetSourceRef */
        SheetSourceRef: {
            /** Kind */
            kind: string;
            /** Label */
            label: string;
            /** Page */
            page?: number | null;
            /** Ref */
            ref?: string | null;
            /** Tier */
            tier?: string | null;
            /** Url */
            url?: string | null;
        };
        /** SheetSummary */
        SheetSummary: {
            /**
             * Edited Since Version
             * @default false
             */
            edited_since_version: boolean;
            /** Id */
            id: string;
            /**
             * Inferred
             * @default false
             */
            inferred: boolean;
            /**
             * Open Confirm
             * @default 0
             */
            open_confirm: number;
            /** Role */
            role: string;
            /** Role Name */
            role_name: string;
            /** Section Key */
            section_key: string;
            /** Sheet No */
            sheet_no: number;
            /** Status */
            status: string;
            /** Status Label */
            status_label: string;
            /**
             * Tag
             * @description 「자동 · MS-B」 또는 「MS-C · 직접」
             */
            tag: string;
            /** Template Code */
            template_code?: string | null;
            /**
             * Template Mode
             * @default auto
             */
            template_mode: string;
            /** Thumb Url */
            thumb_url?: string | null;
            /** Title */
            title: string;
        };
        /** SheetTemplatesSummary */
        SheetTemplatesSummary: {
            /** Catalog Total */
            catalog_total: number;
            /** Dedicated */
            dedicated: number;
            /** Industry */
            industry: number;
            /**
             * Label
             * @description 「미리 만든 템플릿 234종 (업종별 75 · 솔루션 전용 54) · 시트 24장 중 직접 고른 2장 (P3-C · CM-B) · 나머지 자동 추천」
             */
            label: string;
            /** Pinned */
            pinned: components["schemas"]["PinnedSheet"][];
            /** Sheets Total */
            sheets_total: number;
        };
        /** SlideRange */
        SlideRange: {
            /** Flag */
            flag?: string | null;
            /** From */
            from: number;
            /** Label */
            label: string;
            /** To */
            to: number;
        };
        /** SlidesView */
        SlidesView: {
            /** Edits Since Version */
            edits_since_version: number;
            /**
             * File Name
             * @default
             */
            file_name: string;
            /** Filter */
            filter?: string | null;
            /**
             * Open Confirm
             * @default 0
             */
            open_confirm: number;
            /**
             * Rail Label
             * @description 「표지 · 목차 포함 26장」
             * @default
             */
            rail_label: string;
            /**
             * Rev
             * @default 0
             */
            rev: number;
            /** Sections */
            sections: components["schemas"]["RailSection"][];
            /** Sheets Total */
            sheets_total: number;
            /** Slides Total */
            slides_total: number;
            /**
             * Toolbar Label
             * @description 「시트 24 + 표지 · 목차 · 자동 저장됨」
             * @default
             */
            toolbar_label: string;
            /** Version */
            version: number;
            /**
             * Version Label
             * @description 「v1 · 수정 2」
             */
            version_label: string;
        };
        /** SlideThumb */
        SlideThumb: {
            /**
             * Inferred
             * @default false
             */
            inferred: boolean;
            /**
             * Kind
             * @default sheet
             */
            kind: string;
            /** Label */
            label: string;
            /** Sheet Id */
            sheet_id?: string | null;
            /** Slide No */
            slide_no: number;
            /** Thumb Url */
            thumb_url?: string | null;
        };
        /** SourceChip */
        SourceChip: {
            /** Feature */
            feature: string;
            /** Feature Label */
            feature_label: string;
            /** Id */
            id: string;
            /** Label */
            label: string;
            /**
             * Ref
             * @description 셸 참조(「kb:model:mdl_…」 · 「kb:case:…」 · 「img:image:img_…」 · 「ws:item:<id>」) — 팝오버 「✓ 추가됨」 표시용
             */
            ref?: string | null;
            /** Route */
            route?: string | null;
            /**
             * Stale
             * @default false
             */
            stale: boolean;
        };
        /** SourceChipOut */
        SourceChipOut: {
            /** Feature */
            feature: string;
            /** Id */
            id: string;
            /** Label */
            label: string;
        };
        /**
         * StartSections
         * @description 「섹션 작성 시작」 결과
         */
        StartSections: {
            next: components["schemas"]["NextStep"];
            proposal: components["schemas"]["Proposal"];
        };
        /** StatRow */
        StatRow: {
            /** Label */
            label: string;
            /** N */
            n: number;
            /** Of */
            of: number;
        };
        /** Stepper */
        Stepper: {
            /**
             * Auto From
             * @description 딸깍이 채운 첫 단계(검은 번개 아이콘), 0 = 없음
             * @default 0
             */
            auto_from: number;
            /**
             * Complete
             * @default false
             */
            complete: boolean;
            /**
             * Current
             * @description 1–6
             */
            current: number;
            /** Done Steps */
            done_steps?: number[];
            /**
             * One Click
             * @description 딸깍 버튼 표시(1–5단계 · 딸깍 실행 중 아님)
             */
            one_click: boolean;
            /** Steps */
            steps: string[];
        };
        /** Suggestion */
        Suggestion: {
            /** Comment Id */
            comment_id: string;
            /** Job Id */
            job_id?: string | null;
            /** Patch */
            patch?: {
                [key: string]: unknown;
            }[];
            /** Sheet Id */
            sheet_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "none" | "running" | "done" | "failed" | "not_applicable";
            /** Suggestion Text */
            suggestion_text?: string | null;
        };
        /** SummaryCount */
        SummaryCount: {
            /** Desc */
            desc: string;
            /** Label */
            label: string;
            /** N */
            n: number;
            /** Verdict */
            verdict: string;
        };
        /** SummaryMapRow */
        SummaryMapRow: {
            /** Chips */
            chips: string[];
            /** New Count */
            new_count: number;
            /**
             * New Label
             * @default
             */
            new_label: string;
            /** Section */
            section: string;
            /** Src Count */
            src_count: number;
            /**
             * Src Label
             * @default
             */
            src_label: string;
        };
        /** TakeItem */
        TakeItem: {
            /** Label */
            label: string;
            /** Sub */
            sub: string;
        };
        /** TeamFolder */
        TeamFolder: {
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /** Path */
            path?: string | null;
        };
        /** TemplateApplyResult */
        TemplateApplyResult: {
            /** Sheets */
            sheets: components["schemas"]["Sheet"][];
            /**
             * Split
             * @default false
             */
            split: boolean;
        };
        /** TemplateOptions */
        TemplateOptions: {
            /**
             * Auto All Confirm
             * @description 「직접 고른 {{n}}장도 자동으로 바꿔요」
             */
            auto_all_confirm?: string | null;
            /** Current Code */
            current_code?: string | null;
            /**
             * Header Label
             * @description 「시장 규모 · 성장 · “이 시장은 크고, 커지고 있다”를 보여줄 템플릿 5종」
             */
            header_label: string;
            /**
             * Mode
             * @enum {string}
             */
            mode: "auto" | "pinned";
            /**
             * Pinned In Section
             * @default 0
             */
            pinned_in_section: number;
            /** Product Count */
            product_count?: number | null;
            /** Products */
            products?: string[];
            /**
             * Products Label
             * @default
             */
            products_label: string;
            /**
             * Reason Line
             * @description 「MS-B 추천 · …」
             */
            reason_line: string;
            /** Recommended */
            recommended: {
                [key: string]: string | null;
            };
            sheet: components["schemas"]["TemplateSheetInfo"];
            /**
             * Sheet Label
             * @description 「시트 2」 또는 「MagicINFO 시트 3 · 섹션 전체 7」
             * @default
             */
            sheet_label: string;
            /** Split Note */
            split_note?: string | null;
            /** Variants */
            variants: components["schemas"]["TemplateVariant"][];
        };
        /** TemplatePut */
        TemplatePut: {
            /** Code */
            code?: string | null;
            /**
             * Mode
             * @enum {string}
             */
            mode: "auto" | "pinned";
            /**
             * Product Count
             * @description 공간 제품 소개 시트만 1–5
             */
            product_count?: number | null;
        };
        /** TemplatesAuto */
        TemplatesAuto: {
            /**
             * Include Pinned
             * @default true
             */
            include_pinned: boolean;
        };
        /** TemplateSheetInfo */
        TemplateSheetInfo: {
            /** Id */
            id: string;
            /** Msg */
            msg: string;
            /** Role */
            role: string;
            /** Role Name */
            role_name: string;
            /** Title */
            title: string;
        };
        /** TemplateState */
        TemplateState: {
            /** Code */
            code?: string | null;
            /**
             * Locked Manual
             * @description PR6 「시트마다 직접」 — 자동 재추천 끔
             * @default false
             */
            locked_manual: boolean;
            /**
             * Mode
             * @default auto
             * @enum {string}
             */
            mode: "auto" | "pinned";
            /** Name */
            name?: string | null;
            /** Product Count */
            product_count?: number | null;
            /** Reason */
            reason?: string | null;
            /** Recommended Code */
            recommended_code?: string | null;
            /**
             * Source
             * @description industry · dedicated · data_shape · message · user · import
             */
            source?: string | null;
            /**
             * Tag
             * @default
             */
            tag: string;
        };
        /** TemplateVariant */
        TemplateVariant: {
            /**
             * Available
             * @default true
             */
            available: boolean;
            /** Code */
            code: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "industry" | "dedicated" | "industry_solution" | "generic" | "product";
            /** Name */
            name: string;
            /**
             * Selected
             * @default false
             */
            selected: boolean;
            /**
             * Tag
             * @description 「자동」 · 「추천」 · 「직접」
             */
            tag?: string | null;
            /** Thumb Url */
            thumb_url: string;
            /** When */
            when: string;
        };
        /** TextRequest */
        TextRequest: {
            /** Text */
            text: string;
        };
        /** TraceRow */
        TraceRow: {
            /** Sub */
            sub: string;
            /** Title */
            title: string;
        };
        /** TypeOption */
        TypeOption: {
            /** Desc */
            desc: string;
            /**
             * Footnote
             * @description 「섹션 8 · 넣을 시트는 다음 단계에서 골라요」
             */
            footnote: string;
            /** Name */
            name: string;
            /** Rec */
            rec: boolean;
            /** Route */
            route: string;
            /** Section Count */
            section_count: number;
            /** Sections */
            sections: components["schemas"]["TypeSectionChip"][];
            /**
             * Selected
             * @default false
             */
            selected: boolean;
            /**
             * Type
             * @enum {string}
             */
            type: "standard" | "quickwin" | "solution";
        };
        /** TypeOptions */
        TypeOptions: {
            /**
             * Customer Line
             * @description 「A 커피 프랜차이즈 · 전국 매장 디지털 메뉴보드 전환 · 리테일/F&B · 320개 매장」
             */
            customer_line: string;
            /**
             * Footer Note
             * @default 유형은 섹션 작성 중에도 바꿀 수 있고, 이미 작성한 섹션은 유지됩니다.
             */
            footer_note: string;
            /**
             * Header Label
             * @default 제안서 유형 · 하나 선택 · 2 / 6
             */
            header_label: string;
            /** Intro */
            intro: string;
            recommended: components["schemas"]["RecommendedType"];
            /** Selected */
            selected?: ("standard" | "quickwin" | "solution") | null;
            /** Types */
            types: components["schemas"]["TypeOption"][];
        };
        /** TypePut */
        TypePut: {
            /**
             * Type
             * @enum {string}
             */
            type: "standard" | "quickwin" | "solution";
        };
        /** TypeSectionChip */
        TypeSectionChip: {
            /** Key */
            key: string;
            /** Label */
            label: string;
            /** No */
            no: number;
            /** Optional */
            optional: boolean;
        };
        /** UndoResult */
        UndoResult: {
            /** Import Id */
            import_id: string;
            /** Removed Link Ids */
            removed_link_ids?: string[];
            /** Removed Sheet Ids */
            removed_sheet_ids?: string[];
            /** Restored Sheet Ids */
            restored_sheet_ids?: string[];
            /** Status */
            status: string;
        };
        /** VerdictPut */
        VerdictPut: {
            /**
             * Verdict
             * @enum {string}
             */
            verdict: "keep" | "update" | "rewrite" | "new" | "drop";
        };
        /** VersionChange */
        VersionChange: {
            /** Change Id */
            change_id: string;
            /** T */
            t: string;
            /** Text */
            text: string;
        };
        /** VersionCreate */
        VersionCreate: {
            /** Desc */
            desc?: string | null;
        };
        /** VersionCreated */
        VersionCreated: {
            /** N */
            n: number;
        };
        /** VersionEvent */
        VersionEvent: {
            /** At */
            at: string;
            /**
             * Kind
             * @default review_request
             */
            kind: string;
            /** Text */
            text: string;
        };
        /** VersionItem */
        VersionItem: {
            /** Author Label */
            author_label: string;
            /** Changes */
            changes?: components["schemas"]["VersionChange"][];
            /** Created At */
            created_at: string;
            /**
             * Current
             * @default false
             */
            current: boolean;
            /** Derived Label */
            derived_label?: string | null;
            /** Desc */
            desc: string;
            /** Kind */
            kind: string;
            /**
             * Label
             * @description 「v3」
             */
            label: string;
            /** N */
            n: number;
            /**
             * Time Label
             * @description 「오늘 14:20 · 최민섭」
             * @default
             */
            time_label: string;
        };
        /** VersionsView */
        VersionsView: {
            /** Change Count */
            change_count: number;
            /** Current */
            current: number;
            /**
             * Current Label
             * @default
             */
            current_label: string;
            /** Events */
            events: components["schemas"]["VersionEvent"][];
            /**
             * Header Label
             * @description 「버전 3 · 변경 기록 12」
             */
            header_label: string;
            /**
             * Next Save Label
             * @description 「지금 상태를 v4로 저장」
             */
            next_save_label: string;
            /**
             * Pending Changes
             * @description 마지막 버전 이후 변경
             */
            pending_changes?: components["schemas"]["VersionChange"][];
            /**
             * Retention Note
             * @default 자동 저장 기록은 30일 동안 남아요
             */
            retention_note: string;
            /** Versions */
            versions: components["schemas"]["VersionItem"][];
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
    list_proposals: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
                /** @description me | all | <user id> */
                owner?: string;
                project_id?: string | null;
                /** @description 제안서 · 고객사 검색 */
                q?: string | null;
                sort?: "due_asc" | "updated_desc";
                /** @description all | draft | review | done (쉼표로 여러 개: draft,review) */
                tab?: string;
                /** @description standard · quickwin · solution */
                type?: string | null;
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
                    "application/json": components["schemas"]["ProposalList"];
                };
            };
        };
    };
    create_proposal: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProposalCreate"];
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
                    "application/json": components["schemas"]["Proposal"];
                };
            };
        };
    };
    get_proposal: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["Proposal"];
                };
            };
        };
    };
    delete_proposal: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
    patch_proposal: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProposalPatch"];
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
                    "application/json": components["schemas"]["Proposal"];
                };
            };
        };
    };
    generate: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["GenerateIn"] | null;
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
    mark_submitted: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["MarkSubmitted"] | null;
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
                    "application/json": components["schemas"]["Proposal"];
                };
            };
        };
    };
    revert_change: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                change_id: string;
                proposal_id: string;
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
                    "application/json": components["schemas"]["RevertResult"];
                };
            };
        };
    };
    apply_suggestion: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                comment_id: string;
                proposal_id: string;
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
                    "application/json": components["schemas"]["ApplySuggestionResult"];
                };
            };
        };
    };
    suggest: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                comment_id: string;
                proposal_id: string;
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
    get_suggestion: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                comment_id: string;
                proposal_id: string;
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
                    "application/json": components["schemas"]["Suggestion"];
                };
            };
        };
    };
    get_composition: {
        parameters: {
            query?: {
                open?: string | null;
            };
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["Composition"];
                };
            };
        };
    };
    put_composition: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CompositionPut"];
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
                    "application/json": components["schemas"]["Composition"];
                };
            };
        };
    };
    start_sections: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["StartSections"];
                };
            };
        };
    };
    list_items: {
        parameters: {
            query?: {
                category?: ("fact" | "review") | null;
                sheet_id?: string | null;
                status?: "open" | "confirmed" | "all";
            };
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["ConfirmList"];
                };
            };
        };
    };
    create_item: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConfirmCreate"];
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
                    "application/json": components["schemas"]["ConfirmItem"];
                };
            };
        };
    };
    move_all_to_note: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["BulkIds"] | null;
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
                    "application/json": components["schemas"]["ConfirmList"];
                };
            };
        };
    };
    research: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["ResearchIn"] | null;
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
    anonymize: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
                proposal_id: string;
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
                    "application/json": components["schemas"]["ConfirmResolveResult"];
                };
            };
        };
    };
    attach_evidence: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EvidenceIn"];
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
                    "application/json": components["schemas"]["ConfirmItem"];
                };
            };
        };
    };
    move_to_note: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
                proposal_id: string;
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
                    "application/json": components["schemas"]["ConfirmItem"];
                };
            };
        };
    };
    question: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["QuestionIn"] | null;
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
                    "application/json": components["schemas"]["QuestionOut"];
                };
            };
        };
    };
    resolve_item: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_id: string;
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["ConfirmResolve"] | null;
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
                    "application/json": components["schemas"]["ConfirmResolveResult"];
                };
            };
        };
    };
    get_design: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
    put_design: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DesignPatch"];
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
                    "application/json": components["schemas"]["DesignView"];
                };
            };
        };
    };
    put_logo: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LogoIn"];
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
                    "application/json": components["schemas"]["DesignView"];
                };
            };
        };
    };
    export_options: {
        parameters: {
            query?: {
                lang?: string | null;
                version?: number | null;
            };
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["ExportOptions"];
                };
            };
        };
    };
    create_export: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
    get_export: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                export_id: string;
                proposal_id: string;
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
    list_facts: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["FactList"];
                };
            };
        };
    };
    put_fact: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                fact_id: string;
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FactPut"];
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
                    "application/json": components["schemas"]["FactUpdateResult"];
                };
            };
        };
    };
    image_slots: {
        parameters: {
            query?: {
                image_id?: string | null;
                image_ref?: string | null;
                image_version?: string | null;
            };
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["ImageSlots"];
                };
            };
        };
    };
    create_import: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ImportRequest"];
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
                    "application/json": components["schemas"]["ImportResult"];
                };
            };
            /** @description 사이드바 작업 · 보내기 — 추출/적용 잡 */
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
    get_import: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                import_id: string;
                proposal_id: string;
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
                    "application/json": components["schemas"]["Import"];
                };
            };
        };
    };
    apply_import: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                import_id: string;
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ImportApply"];
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
    undo_import: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                import_id: string;
                proposal_id: string;
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
                    "application/json": components["schemas"]["UndoResult"];
                };
            };
        };
    };
    get_industry: {
        parameters: {
            query?: {
                code?: string | null;
            };
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["IndustryView"];
                };
            };
        };
    };
    put_industry: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["IndustryPut"];
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
                    "application/json": components["schemas"]["IndustryView"];
                };
            };
        };
    };
    list_links: {
        parameters: {
            query?: {
                section_key?: string | null;
            };
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["LinksOut"];
                };
            };
        };
    };
    put_links: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LinksPut"];
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
                    "application/json": components["schemas"]["LinksOut"];
                };
            };
        };
    };
    apply_links: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
    delete_link: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                link_id: string;
                proposal_id: string;
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
                    "application/json": components["schemas"]["LinkRemoved"];
                };
            };
        };
    };
    refresh_link: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                link_id: string;
                proposal_id: string;
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
    restore_link: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                link_id: string;
                proposal_id: string;
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
                    "application/json": components["schemas"]["LinkedSource"];
                };
            };
        };
    };
    upload_master: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MasterUpload"];
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
                    "application/json": components["schemas"]["MasterCreated"];
                };
            };
        };
    };
    proposal_messages: {
        parameters: {
            query?: {
                scope?: string | null;
                scope_ref?: string | null;
            };
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["MessageList"];
                };
            };
        };
    };
    notes_generate: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["NotesGenerate"] | null;
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
    start_one_click: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["OneClickStart"] | null;
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
    get_one_click: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
                proposal_id: string;
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
                    "application/json": components["schemas"]["OneClickView"];
                };
            };
        };
    };
    one_click_plan: {
        parameters: {
            query?: {
                /** @description 누른 단계(stage) */
                from?: string | null;
                section?: string | null;
            };
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["OneClickPlan"];
                };
            };
        };
    };
    related_works: {
        parameters: {
            query?: {
                q?: string | null;
                scope?: "customer" | "all";
            };
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["RelatedWorks"];
                };
            };
        };
    };
    create_render: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["RenderIn"] | null;
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
    proposal_request: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TextRequest"];
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
    get_result: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
    get_reuse: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["ReuseView"];
                };
            };
        };
    };
    start_reuse: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReuseStart"];
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
    delete_reuse: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
    confirm_analysis: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["ReuseConfirmOut"];
                };
            };
        };
    };
    reanalyze: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["ReuseConfirmOut"];
                };
            };
        };
    };
    candidates: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["ReuseCandidates"];
                };
            };
        };
    };
    get_criterion: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                no: number;
                proposal_id: string;
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
                    "application/json": components["schemas"]["CriterionDetail"];
                };
            };
        };
    };
    put_criterion: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                no: number;
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CriterionPut"];
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
                    "application/json": components["schemas"]["ReuseView"];
                };
            };
        };
    };
    put_mode: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ModePut"];
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
                    "application/json": components["schemas"]["ReuseView"];
                };
            };
        };
    };
    put_page_role: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                no: number;
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RolePut"];
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
                    "application/json": components["schemas"]["ReuseView"];
                };
            };
        };
    };
    confirm_plan: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PlanConfirm"] | null;
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
                    "application/json": components["schemas"]["ReuseConfirmOut"];
                };
            };
        };
    };
    put_verdict: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
                row_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VerdictPut"];
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
                    "application/json": components["schemas"]["ReuseView"];
                };
            };
        };
    };
    reuse_summary: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["ReuseSummary"];
                };
            };
        };
    };
    get_review: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["ReviewView"];
                };
            };
        };
    };
    request_review: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewRequestIn"];
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
                    "application/json": components["schemas"]["ReviewView"];
                };
            };
        };
    };
    resubmit: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
                review_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["ResubmitIn"] | null;
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
                    "application/json": components["schemas"]["ReviewView"];
                };
            };
        };
    };
    apply_comments: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["ApplyCommentsIn"] | null;
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
    put_check: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CheckPut"];
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
                    "application/json": components["schemas"]["ReviewView"];
                };
            };
        };
    };
    decide: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DecisionIn"];
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
                    "application/json": components["schemas"]["ReviewView"];
                };
            };
        };
    };
    get_rfp: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["RfpView"];
                };
            };
        };
    };
    start_rfp: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RfpStart"];
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
    confirm_rfp: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["Proposal"];
                };
            };
        };
    };
    put_rfp_field: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                key: string;
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RfpFieldPut"];
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
                    "application/json": components["schemas"]["RfpView"];
                };
            };
        };
    };
    get_section: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                key: string;
                proposal_id: string;
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
                    "application/json": components["schemas"]["SectionView"];
                };
            };
        };
    };
    confirm_section: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                key: string;
                proposal_id: string;
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
                    "application/json": components["schemas"]["SectionConfirmResult"];
                };
            };
        };
    };
    fill_section: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                key: string;
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["SectionFill"] | null;
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
    section_request: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                key: string;
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TextRequest"];
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
    reuse_section_view: {
        parameters: {
            query?: {
                sheet_id?: string | null;
                view?: ("compare" | "guide" | "new_only") | null;
            };
            header?: never;
            path: {
                key: string;
                proposal_id: string;
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
                    "application/json": components["schemas"]["ReuseSectionView"];
                };
            };
        };
    };
    section_templates_auto: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                key: string;
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["TemplatesAuto"] | null;
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
                    "application/json": components["schemas"]["SectionView"];
                };
            };
        };
    };
    share_link: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["ShareLinkIn"] | null;
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
                    "application/json": components["schemas"]["ShareLinkOut"];
                };
            };
        };
    };
    get_sheet: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["Sheet"];
                };
            };
        };
    };
    patch_sheet: {
        parameters: {
            query?: never;
            header?: {
                "If-Match"?: string | null;
            };
            path: {
                proposal_id: string;
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SheetPatch"];
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
                    "application/json": components["schemas"]["SheetPatchResult"];
                };
            };
        };
    };
    rewrite_sheet: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["SheetRewrite"] | null;
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
    sheet_messages: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["MessageList"];
                };
            };
        };
    };
    pull_lines: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PullLines"] | null;
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
                    "application/json": components["schemas"]["Sheet"];
                };
            };
        };
    };
    put_template: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
                sheet_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TemplatePut"];
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
                    "application/json": components["schemas"]["TemplateApplyResult"];
                };
            };
        };
    };
    template_options: {
        parameters: {
            query?: {
                product_count?: number | null;
            };
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["TemplateOptions"];
                };
            };
        };
    };
    get_slides: {
        parameters: {
            query?: {
                filter?: string | null;
            };
            header?: never;
            path: {
                proposal_id: string;
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
    put_type: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TypePut"];
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
                    "application/json": components["schemas"]["Proposal"];
                };
            };
        };
    };
    type_options: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["TypeOptions"];
                };
            };
        };
    };
    list_versions: {
        parameters: {
            query?: {
                include?: string;
            };
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["VersionsView"];
                };
            };
        };
    };
    save_version: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["VersionCreate"] | null;
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
                    "application/json": components["schemas"]["VersionCreated"];
                };
            };
        };
    };
    restore: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                n: number;
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["RestoreIn"] | null;
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
                    "application/json": components["schemas"]["RestoreResult"];
                };
            };
        };
    };
    compare: {
        parameters: {
            query?: {
                a?: number | null;
                b?: number | null;
                mode?: "side" | "changes";
                sheet?: string | null;
            };
            header?: never;
            path: {
                proposal_id: string;
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
                    "application/json": components["schemas"]["CompareView"];
                };
            };
        };
    };
}
