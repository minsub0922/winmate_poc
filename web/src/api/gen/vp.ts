// 자동 생성 — 직접 고치지 말 것. 원본: contracts/vp.json (make contracts)
export interface paths {
    "/v1/handoffs/{vho}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Vp Handoff
         * @description proposal 이 당겨 간다(웹 VP4 도 읽는다).
         */
        get: operations["get_vp_handoff"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/handoffs/{vho}:ack": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Ack Vp Handoff
         * @description proposal → vp: 받아 넣은 결과. needs_confirmation 이면 VP 작업에 확인할 것(요청)을 남긴다.
         */
        post: operations["ack_vp_handoff"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/industry-packs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Industry Packs */
        get: operations["list_industry_packs"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/industry-packs/{code}:release": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Release Industry Pack */
        post: operations["release_industry_pack"];
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
    "/v1/layouts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Layouts */
        get: operations["list_layouts"];
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
        /** Get Routing Rules */
        get: operations["get_routing_rules"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/routing-rules/scenarios": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Routing Scenarios */
        get: operations["get_routing_scenarios"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/value-maps": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Value Maps */
        get: operations["list_value_maps"];
        put?: never;
        /**
         * Create Value Map
         * @description 새 가치 맵. sb_id 만 주면 Storyboard 의 DSS 제품 · 솔루션으로(같은 Storyboard 의 저장 전 초안이 있으면 그것을 200 으로),
         *     candidates(DSS 제품 · 솔루션)를 주거나, context_text(요구 문장)로 KB 에서 공간별 후보를 찾는다.
         */
        post: operations["create_value_map"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/value-maps/{map_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Value Map
         * @description 맵 하나 + `dss_changed`(Storyboard 로 만든 맵의 DSS 가 바뀌었으면 그 차이, 아니면 null).
         */
        get: operations["get_value_map"];
        put?: never;
        post?: never;
        /**
         * Delete Value Map
         * @description 저장 전 초안 지우기(workspace 색인도 지운다). 한 번이라도 저장한 맵은 Storyboard 에 연결돼 있어 409 `SAVED_CONTENT`.
         */
        delete: operations["delete_value_map"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/value-maps/{map_id}:accept-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Accept All */
        post: operations["accept_all"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/value-maps/{map_id}:finish": {
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
         * @description 저장 — status=done, Storyboard flow.json 의 stages.vp 와 요약 md 를 돌려준다.
         */
        post: operations["finish"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/value-maps/{map_id}:resync-dss": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Resync Value Map Dss
         * @description DSS 다시 가져오기 — 새 DSS 제품 · 솔루션은 고를 수 있는 후보로만(자동으로 고르지 않음), 골라 둔 것이 DSS 에서 빠지면 남기고 「DSS에서 빠짐」.
         *     결과는 `last_resync`. Storyboard 로 만든 맵이 아니면 422 `NO_STORYBOARD` · Storyboard 없음 404 · DSS 없음 422.
         */
        post: operations["resync_value_map_dss"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/value-maps/{map_id}:suggest": {
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
         * @description AI 가치 매칭 추천 — KB 원문 메시지 + 요구 → 가치 후보(니즈 포함, 제품마다 최대 2) · 빈 니즈 추론. 모두 ai-pending.
         */
        post: operations["suggest"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/value-maps/{map_id}/items": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Set Value Map Items
         * @description VP 에 넣을 제품 · 솔루션 고르기(제품 · 솔루션 고르기 팝업). 하나 이상.
         */
        put: operations["set_value_map_items"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/value-maps/{map_id}/items/{item_key}/linked": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Linked Values
         * @description 연결된 가치 전체 — 이 제안 · 같은 제품을 쓴 다른 제안 · KB 공식 메시지.
         */
        get: operations["linked_values"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/value-maps/{map_id}/items/{item_key}/values": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Add Value */
        post: operations["add_value"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/value-maps/{map_id}/items/{item_key}/values:import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Value
         * @description 다른 제안의 가치를 이 제안에 가져오기(복사).
         */
        post: operations["import_value"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/value-maps/{map_id}/stage": {
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
    "/v1/value-maps/{map_id}/values/{value_id}": {
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
         * Delete Value
         * @description 가치 지우기 — AI 후보 '빼기'도 이것.
         */
        delete: operations["delete_value"];
        options?: never;
        head?: never;
        /**
         * Patch Value
         * @description 가치 고치기 · 니즈 쓰기(빈 문자열이면 지움) · AI 후보 수락(accept) · AI 니즈 수락(accept_need).
         */
        patch: operations["patch_value"];
        trace?: never;
    };
    "/v1/value-maps/{map_id}/values/{value_id}:infer-need": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Infer Need
         * @description AI 니즈 추론(가치 하나). 모델이 없으면 need=null · reason.
         */
        post: operations["infer_need"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/value-props:draft": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Draft Value Prop
         * @description 10-proposal §8.9 V2 — VP 작업 없이 Value Props 초안(재료 → 생성까지 기본값으로).
         */
        post: operations["draft_value_prop"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/value-props/{vp_id}/proposal-handoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Value Prop Proposal Handoff
         * @description `/v1/vps/{id}/proposal-handoff` 와 같다(10-proposal §8.9 의 경로 이름).
         */
        get: operations["get_value_prop_proposal_handoff"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Vps */
        get: operations["list_vps"];
        put?: never;
        /** Create Vp */
        post: operations["create_vp"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Vp */
        get: operations["get_vp"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Vp */
        patch: operations["patch_vp"];
        trace?: never;
    };
    "/v1/vps/{vp_id}:archive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Archive Vp */
        post: operations["archive_vp"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}:clone": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Clone Vp */
        post: operations["clone_vp"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}:release-proposal": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Release Vp Proposal
         * @description proposal → vp: 제안서를 지웠다 — 「연결된 제안서」 · 보낼 제안서를 거둔다(통합).
         */
        post: operations["release_vp_proposal"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/attachments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Add Vp Attachment */
        post: operations["add_vp_attachment"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/attachments/{att_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Vp Attachment */
        delete: operations["delete_vp_attachment"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/copy-text": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Copy Text */
        get: operations["get_copy_text"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/data-request-draft": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Data Request Draft */
        get: operations["get_data_request_draft"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/exports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Vp Export */
        post: operations["create_vp_export"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/exports/{vex}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Vp Export */
        get: operations["get_vp_export"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/fixes/{fx}:decide": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Decide Fix */
        post: operations["decide_fix"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/generate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Generate Vp */
        post: operations["generate_vp"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/handoffs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Vp Handoff */
        post: operations["create_vp_handoff"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/image-slots": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Image Slots */
        get: operations["list_image_slots"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/image-slots/{vis}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Image Slot */
        put: operations["put_image_slot"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/image-slots/{vis}/candidates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Slot Candidates */
        get: operations["list_slot_candidates"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/images:restyle": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Restyle Images */
        post: operations["restyle_images"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/layout-requests/{vlr}:cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Layout Request */
        post: operations["cancel_layout_request"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/materials:collect": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Collect Materials */
        post: operations["collect_materials"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Vp Message */
        post: operations["post_vp_message"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/metrics/{vmt}": {
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
        /** Patch Vp Metric */
        patch: operations["patch_vp_metric"];
        trace?: never;
    };
    "/v1/vps/{vp_id}/pack-offers/{vpo}:decide": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Decide Pack Offer */
        post: operations["decide_pack_offer"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/package": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Vp Package */
        get: operations["get_vp_package"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/packages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Vp Packages
         * @description VP4 — 세 유형을 한 번에(유형 열 · 독 문구).
         */
        get: operations["get_vp_packages"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/plan": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Vp Plan */
        get: operations["get_vp_plan"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Vp Plan */
        patch: operations["patch_vp_plan"];
        trace?: never;
    };
    "/v1/vps/{vp_id}/plan:refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Refresh Plan */
        post: operations["refresh_plan"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/proposal-handoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Proposal Handoff
         * @description 10-proposal §8.9 V1 — ProposalHandoff v1(유형별 시트 · 수치 사실 · 이미지 자산).
         */
        get: operations["get_proposal_handoff"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/questions:answer": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Answer Questions */
        post: operations["answer_questions"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/sheets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Add Vp Sheet */
        post: operations["add_vp_sheet"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/sheets/{sh}": {
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
        /** Patch Vp Sheet */
        patch: operations["patch_vp_sheet"];
        trace?: never;
    };
    "/v1/vps/{vp_id}/sheets/{sh}/layout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Choose Sheet Layout */
        post: operations["choose_sheet_layout"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/sheets/{sh}/layout-options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Layout Options */
        get: operations["get_layout_options"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/sheets/{sh}/metrics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Sheet Metrics */
        get: operations["get_sheet_metrics"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/sheets/{sh}/metrics:apply": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Apply Sheet Metrics */
        post: operations["apply_sheet_metrics"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/source-candidates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Source Candidates */
        get: operations["list_source_candidates"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/sources": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Vp Sources */
        put: operations["put_vp_sources"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/versions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Vp Versions */
        get: operations["list_vp_versions"];
        put?: never;
        /**
         * Save Vp Version
         * @description 저장 지점(version +1) — VP3 `저장 · 내보내기`.
         */
        post: operations["save_vp_version"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/vps/{vp_id}/versions/{n}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Restore Vp Version */
        post: operations["restore_vp_version"];
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
            /** Graph */
            graph: string;
            /** Job Id */
            job_id: string;
            /**
             * Kind
             * @description vp.materials · vp.generate · vp.revise · vp.images
             * @default
             */
            kind: string;
            /**
             * Progress
             * @default 0
             */
            progress: number;
            /** Started At */
            started_at?: string | null;
            /**
             * Status
             * @default queued
             */
            status: string;
        };
        /** AddAttachment */
        AddAttachment: {
            /** File Id */
            file_id: string;
            /** Kind */
            kind?: ("rfp" | "quote" | "meeting_notes" | "customer_photo" | "other") | null;
        };
        /** AddSheet */
        AddSheet: {
            /** Deployment Id */
            deployment_id?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "one_liner" | "reference";
            /** Layout Code */
            layout_code?: string | null;
        };
        /** AnswerItem */
        AnswerItem: {
            /** Keys */
            keys?: string[] | null;
            /** Question Id */
            question_id: string;
            /** Text */
            text?: string | null;
        };
        /** AnswerQuestions */
        AnswerQuestions: {
            /** Answers */
            answers?: components["schemas"]["AnswerItem"][];
            /**
             * Proceed
             * @default true
             */
            proceed: boolean;
        };
        /**
         * AnswerResult
         * @description `VPDoc` + 재개한 잡 · 다음 화면.
         */
        AnswerResult: {
            /**
             * Action Label
             * @default 이어서
             */
            action_label: string;
            active_job?: components["schemas"]["ActiveJob"] | null;
            /** Attachments */
            attachments?: components["schemas"]["Attachment"][];
            /**
             * Auto Answer
             * @default false
             */
            auto_answer: boolean;
            /**
             * Auto Chips
             * @description VP1Q `자동으로 정한 것`
             */
            auto_chips?: string[];
            /** Checks */
            checks?: components["schemas"]["CheckItem"][];
            /** Coverage */
            coverage?: components["schemas"]["CoverageAxis"][];
            /** Created At */
            created_at: string;
            /** Customer Name */
            customer_name?: string | null;
            /** Decisions */
            decisions?: components["schemas"]["Decision"][];
            /** Fixes */
            fixes?: components["schemas"]["Fix"][];
            /**
             * Generated
             * @default false
             */
            generated: boolean;
            /** Id */
            id: string;
            /** Image Slots */
            image_slots?: components["schemas"]["ImageSlot"][];
            industry?: components["schemas"]["Industry"] | null;
            /**
             * Intros
             * @description 에이전트 문장(materials_review · questions · questions_default · result · structure)
             */
            intros?: {
                [key: string]: string;
            };
            /**
             * Labels
             * @description 말풍선 · 요약(connect · questions · materials_footer · generate · head_codes)
             */
            labels?: {
                [key: string]: string;
            };
            /** Last Error */
            last_error?: {
                [key: string]: unknown;
            } | null;
            last_job?: components["schemas"]["ActiveJob"] | null;
            /** Layout Requests */
            layout_requests?: components["schemas"]["LayoutRequest"][];
            /**
             * Legend
             * @description VP1A 출처 범례(쓰인 출처만)
             */
            legend?: {
                [key: string]: string;
            }[];
            /** Linked Proposal */
            linked_proposal?: {
                [key: string]: unknown;
            } | null;
            /** Materials */
            materials?: components["schemas"]["MaterialItem"][];
            /**
             * Materials Ready
             * @default false
             */
            materials_ready: boolean;
            /**
             * Next Route
             * @default
             */
            next_route: string;
            /**
             * Note
             * @default
             */
            note: string;
            owner: components["schemas"]["Owner"];
            /** Pack Offers */
            pack_offers?: components["schemas"]["PackOffer"][];
            plan?: components["schemas"]["Plan"] | null;
            /** Project Id */
            project_id?: string | null;
            /** Questions */
            questions?: components["schemas"]["Question"][];
            /**
             * Resume Route
             * @default
             */
            resume_route: string;
            /** Resumed Job Id */
            resumed_job_id?: string | null;
            /** Sheets */
            sheets?: components["schemas"]["Sheet"][];
            /** Sources */
            sources?: components["schemas"]["Source"][];
            /**
             * Start
             * @default direct
             * @enum {string}
             */
            start: "direct" | "storyboard" | "mi" | "clone" | "proposal";
            /**
             * Status
             * @default draft
             * @enum {string}
             */
            status: "draft" | "collecting" | "ask" | "planned" | "generating" | "check" | "done" | "stopped" | "failed";
            /**
             * Status Text
             * @default
             */
            status_text: string;
            /**
             * Step
             * @default 1
             */
            step: number;
            target_proposal?: components["schemas"]["TargetProposal"] | null;
            /** Title */
            title: string;
            /**
             * Ui Status
             * @default draft
             * @enum {string}
             */
            ui_status: "draft" | "ask" | "check" | "run" | "done";
            /** Updated At */
            updated_at: string;
            /** Variants */
            variants?: components["schemas"]["Sheet"][];
            /**
             * Version
             * @description 저장 지점 수(재료 완료 · 플랜 변경 · 생성 완료 · 레이아웃 적용 · 수치 반영 · 이미지 변경 · 넘김)
             */
            version: number;
        };
        /** AssetRef */
        AssetRef: {
            /** Asset Id */
            asset_id?: string | null;
            /** File Id */
            file_id?: string | null;
            /**
             * Source
             * @enum {string}
             */
            source: "kb" | "file" | "generated";
            /**
             * Std Url
             * @default
             */
            std_url: string;
            /**
             * Thumb Url
             * @default
             */
            thumb_url: string;
        };
        /** Attachment */
        Attachment: {
            /**
             * Confidential
             * @default true
             */
            confidential: boolean;
            /** Detected Kind */
            detected_kind?: string | null;
            /** File Id */
            file_id: string;
            /**
             * Filename
             * @default
             */
            filename: string;
            /** Id */
            id: string;
            /**
             * Kind
             * @default other
             * @enum {string}
             */
            kind: "rfp" | "quote" | "meeting_notes" | "customer_photo" | "other";
            /**
             * Status
             * @default pending
             * @enum {string}
             */
            status: "pending" | "read" | "failed";
            /**
             * Summary
             * @default
             */
            summary: string;
        };
        /** BandRow */
        BandRow: {
            /** Code */
            code: string;
            /** Ind */
            ind: string;
            /** Name */
            name: string;
            /** Rules */
            rules: components["schemas"]["BandRule"][];
        };
        /** BandRule */
        BandRule: {
            /** C */
            c: string;
            /** T */
            t: string;
        };
        /** ChallengeItem */
        ChallengeItem: {
            /**
             * Body
             * @default
             */
            body: string;
            /** Id */
            id: string;
            impact?: components["schemas"]["NumberValue"] | null;
            /** Source Ids */
            source_ids?: string[];
            /** Title */
            title: string;
        };
        /** CheckItem */
        CheckItem: {
            /** Action Label */
            action_label: string;
            /** Action Route */
            action_route: string;
            /** Id */
            id: string;
            /**
             * Resolved
             * @default false
             */
            resolved: boolean;
            /**
             * Strong
             * @default false
             */
            strong: boolean;
            /**
             * Tag
             * @enum {string}
             */
            tag: "추정" | "이미지" | "알림" | "요청" | "업종판";
            /** Text */
            text: string;
        };
        /** ChooseLayout */
        ChooseLayout: {
            /** Layout Code */
            layout_code?: string | null;
            /** Note */
            note?: string | null;
            /** Option Key */
            option_key?: ("A" | "B" | "C") | null;
            /** Pillars */
            pillars?: number | null;
            /**
             * Pin
             * @default false
             */
            pin: boolean;
            /** Request Id */
            request_id?: string | null;
        };
        /** CloneVP */
        CloneVP: {
            /** Customer Name */
            customer_name: string;
            industry?: components["schemas"]["IndustryCode"] | null;
            /**
             * Keep Pinned
             * @default true
             */
            keep_pinned: boolean;
        };
        /** CollectBody */
        CollectBody: {
            /** Note */
            note?: string | null;
        };
        /** CopyText */
        CopyText: {
            /** Text */
            text: string;
        };
        /** CoverageAxis */
        CoverageAxis: {
            /**
             * Axis
             * @enum {string}
             */
            axis: "challenge" | "value" | "evidence" | "stakeholder";
            /** Label */
            label: string;
            /**
             * Level
             * @enum {string}
             */
            level: "충분" | "보통" | "부족";
            /** Percent */
            percent: number;
            /** Summary */
            summary: string;
            /** Todo */
            todo: string;
        };
        /** CreateVP */
        CreateVP: {
            /**
             * Auto Answer
             * @default false
             */
            auto_answer: boolean;
            /** Customer Name */
            customer_name?: string | null;
            /** Note */
            note?: string | null;
            /** Project Id */
            project_id?: string | null;
            /** Source Refs */
            source_refs?: components["schemas"]["SourceRef"][] | null;
            /**
             * Start
             * @default direct
             * @enum {string}
             */
            start: "direct" | "storyboard" | "mi" | "clone" | "proposal";
            target_proposal?: components["schemas"]["TargetProposal"] | null;
            /** Title */
            title?: string | null;
        };
        /** DataRequestDraft */
        DataRequestDraft: {
            /** Mailto */
            mailto: string;
            /** Targets */
            targets?: string[];
            /** Text */
            text: string;
            /** To Hint */
            to_hint: string;
        };
        /** Decision */
        Decision: {
            /** Id */
            id: string;
            /** Job Id */
            job_id?: string | null;
            /**
             * Key
             * @default
             */
            key: string;
            /**
             * Mode
             * @default auto
             * @enum {string}
             */
            mode: "auto" | "check" | "ask" | "pin";
            /** Stage */
            stage: number;
            /**
             * T
             * @description HH:MM:SS
             */
            t: string;
            /** Text */
            text: string;
            /**
             * Value
             * @default
             */
            value: string;
            /**
             * Why
             * @default
             */
            why: string;
        };
        /** DraftAccepted */
        DraftAccepted: {
            /** Job Id */
            job_id: string;
            /**
             * Status
             * @default queued
             */
            status: string;
            /** Value Prop Id */
            value_prop_id: string;
        };
        /** DraftBody */
        DraftBody: {
            /** Customer Name */
            customer_name?: string | null;
            /** Industry Code */
            industry_code?: string | null;
            /** Products */
            products?: string[] | null;
            /** Project Id */
            project_id?: string | null;
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
            rq_ref?: components["schemas"]["DraftRqRef"] | null;
            /** Sheet Roles */
            sheet_roles?: ("CH" | "VP" | "EF")[] | null;
            /** Sources */
            sources?: components["schemas"]["DraftSource"][];
        };
        /** DraftRqRef */
        DraftRqRef: {
            /** Rq Id */
            rq_id: string;
            /** Version */
            version?: number | null;
        };
        /** DraftSource */
        DraftSource: {
            /** Feature */
            feature: string;
            /** Ref Id */
            ref_id: string;
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
        /** ExportBody */
        ExportBody: {
            /**
             * Format
             * @enum {string}
             */
            format: "pptx" | "pdf_summary";
            /**
             * Include Notes
             * @default true
             */
            include_notes: boolean;
            /** Proposal Type */
            proposal_type?: ("standard" | "quickwin" | "solution") | null;
        };
        /** ExportRecord */
        ExportRecord: {
            /** File Id */
            file_id?: string | null;
            /** Filename */
            filename?: string | null;
            /** Format */
            format: string;
            /** Id */
            id: string;
            /** Job Id */
            job_id?: string | null;
            /** Status */
            status: string;
        };
        /** Fix */
        Fix: {
            /** Decided By */
            decided_by?: ("user" | "default") | null;
            /**
             * Decision
             * @default pending
             * @enum {string}
             */
            decision: "pending" | "accepted" | "reverted";
            /** From Text */
            from_text: string;
            /** Id */
            id: string;
            /** Item Ids */
            item_ids?: string[];
            /**
             * Kind
             * @enum {string}
             */
            kind: "merge" | "rewrite" | "refetch";
            /** Kind Label */
            kind_label: string;
            /**
             * Mode
             * @enum {string}
             */
            mode: "auto" | "check";
            /** To Text */
            to_text: string;
        };
        /** FixDecision */
        FixDecision: {
            /**
             * Decision
             * @enum {string}
             */
            decision: "accept" | "revert";
        };
        /** GenerateBody */
        GenerateBody: {
            /**
             * Retry
             * @default false
             */
            retry: boolean;
            /** Sheet Roles */
            sheet_roles?: ("CH" | "VP" | "EF")[] | null;
        };
        /** Handoff */
        Handoff: {
            /** Acked At */
            acked_at?: string | null;
            /**
             * Created At
             * @default
             */
            created_at: string;
            /** Id */
            id: string;
            /**
             * Open Route
             * @default
             */
            open_route: string;
            options: components["schemas"]["HandoffOptions"];
            package: components["schemas"]["Package"];
            /** Proposal Id */
            proposal_id?: string | null;
            /**
             * Proposal Type
             * @enum {string}
             */
            proposal_type: "standard" | "quickwin" | "solution";
            /** Status */
            status: string;
            /** Vp Id */
            vp_id: string;
            /** Vp Version */
            vp_version: number;
        };
        /** HandoffAck */
        HandoffAck: {
            /** Applied Sheet Ids */
            applied_sheet_ids?: string[];
            /** Pinned Conflicts */
            pinned_conflicts?: {
                [key: string]: string;
            }[] | null;
            /** Proposal Id */
            proposal_id?: string | null;
            /** Proposal Title */
            proposal_title?: string | null;
            /**
             * Result
             * @enum {string}
             */
            result: "applied" | "needs_confirmation" | "failed";
        };
        /** HandoffBody */
        HandoffBody: {
            /** Interview Numbers Confirmed */
            interview_numbers_confirmed?: boolean | null;
            /** Note */
            note?: string | null;
            options?: components["schemas"]["HandoffOptions"];
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
             * @default ready
             */
            status: string;
            /**
             * Storyboard Synced
             * @default 0
             */
            storyboard_synced: number;
        };
        /** HandoffOptions */
        HandoffOptions: {
            /**
             * Ask Before Overwrite Pinned
             * @default true
             */
            ask_before_overwrite_pinned: boolean;
            /**
             * Estimates As Notes
             * @default true
             */
            estimates_as_notes: boolean;
            /**
             * Sync Storyboard
             * @default true
             */
            sync_storyboard: boolean;
        };
        /** ImageDims */
        ImageDims: {
            /** Bytes */
            bytes?: number | null;
            /**
             * Format
             * @default
             */
            format: string;
            /**
             * H
             * @default 0
             */
            h: number;
            /**
             * W
             * @default 0
             */
            w: number;
        };
        /** ImageMeta */
        ImageMeta: {
            /** Alt On Source */
            alt_on_source?: string | null;
            /**
             * Caption Rule
             * @default
             */
            caption_rule: string;
            /**
             * Collected At
             * @default
             */
            collected_at: string;
            /** Grade Hint */
            grade_hint?: string | null;
            /**
             * Kind
             * @default 제품
             * @enum {string}
             */
            kind: "제품" | "도입사례" | "솔루션" | "고객 사진" | "생성";
            /**
             * Method
             * @default
             */
            method: string;
            original?: components["schemas"]["ImageDims"] | null;
            /** Original File Url */
            original_file_url?: string | null;
            /** Posted At */
            posted_at?: string | null;
            /**
             * Rights
             * @default
             */
            rights: string;
            source_page?: components["schemas"]["PageRef"] | null;
            stored?: components["schemas"]["ImageDims"];
            /**
             * Tier Source
             * @default T2_official
             * @enum {string}
             */
            tier_source: "T2_official" | "T3_case" | "T6_generated" | "customer";
            /**
             * Title
             * @default
             */
            title: string;
            usage_history?: components["schemas"]["UsageHistory"];
        };
        /** ImageSlot */
        ImageSlot: {
            asset?: components["schemas"]["AssetRef"] | null;
            /**
             * Code
             * @description 'VP-F·3 · 기둥 1'
             */
            code: string;
            /**
             * Extra
             * @description 추가 제안 칸(VP-Q · 보낼 때 기본 미포함)
             * @default false
             */
            extra: boolean;
            /**
             * Fit
             * @default cover
             * @enum {string}
             */
            fit: "cover" | "contain";
            flags?: components["schemas"]["SlotFlags"];
            /** Focal */
            focal?: string | null;
            /** Id */
            id: string;
            /** Label */
            label: string;
            meta?: components["schemas"]["ImageMeta"] | null;
            /**
             * Mode
             * @default auto
             * @enum {string}
             */
            mode: "auto" | "check";
            /** Request Draft */
            request_draft?: string | null;
            /** Sheet Id */
            sheet_id: string;
            subject: components["schemas"]["SlotSubject"];
            /**
             * Tier
             * @enum {string}
             */
            tier: "customer" | "cut" | "case" | "ui" | "illust";
            /** Tier Label */
            tier_label: string;
            /**
             * Why
             * @default
             */
            why: string;
        };
        /** ImageSlotCounts */
        ImageSlotCounts: {
            /** Checks */
            checks: number;
            /** Illust */
            illust: number;
            /** Official */
            official: number;
            /** Slots */
            slots: number;
        };
        /** ImageSlotsView */
        ImageSlotsView: {
            /** Actions */
            actions?: components["schemas"]["PlanAlternative"][];
            counts: components["schemas"]["ImageSlotCounts"];
            /** Intro */
            intro: string;
            /** Items */
            items: components["schemas"]["ImageSlot"][];
        };
        /** Industry */
        Industry: {
            /**
             * Caption
             * @default
             */
            caption: string;
            /**
             * Cell
             * @default
             */
            cell: string;
            /**
             * Code
             * @description 16 업종 코드 · GEN(범용)
             */
            code: string;
            /** Confidence */
            confidence?: number | null;
            /** Inherited From */
            inherited_from?: string | null;
            /** Kr Vertical Id */
            kr_vertical_id?: string | null;
            /**
             * Mode
             * @default auto
             * @enum {string}
             */
            mode: "auto" | "check" | "ask" | "pin";
            /**
             * Name
             * @description `외식 · 카페`
             */
            name: string;
            pack?: components["schemas"]["IndustryPack"];
            /**
             * Source
             * @default classified
             * @enum {string}
             */
            source: "mi" | "storyboard" | "proposal" | "requirements" | "classified" | "user" | "vp";
            /** Top2 */
            top2?: components["schemas"]["IndustryScore"][] | null;
        };
        /** IndustryCode */
        IndustryCode: {
            /** Code */
            code: string;
        };
        /** IndustryPack */
        IndustryPack: {
            /**
             * Label
             * @default 업종판 제작 중 → 범용
             */
            label: string;
            /**
             * Status
             * @default in_production
             * @enum {string}
             */
            status: "in_production" | "ready";
        };
        /** IndustryPackItem */
        IndustryPackItem: {
            /** Cell */
            cell: string;
            /** Code */
            code: string;
            /** Name */
            name: string;
            /** Released At */
            released_at?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "in_production" | "ready";
        };
        /** IndustryPacks */
        IndustryPacks: {
            /** Banner */
            banner?: string | null;
            /** Banner Sub */
            banner_sub?: string | null;
            /** Items */
            items: components["schemas"]["IndustryPackItem"][];
            /** Ready */
            ready: number;
            /**
             * Total
             * @default 16
             */
            total: number;
        };
        /** IndustryScore */
        IndustryScore: {
            /** Code */
            code: string;
            /** Score */
            score: number;
        };
        /** JobAccepted */
        JobAccepted: {
            /** Job Id */
            job_id: string;
            /**
             * Ref
             * @description 만들어진 · 바뀌는 자원(편의)
             */
            ref?: {
                [key: string]: unknown;
            } | null;
            /**
             * Status
             * @default queued
             */
            status: string;
        };
        /** KBRef */
        KBRef: {
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "family" | "model" | "solution" | "category" | "deployment";
            /** Name */
            name: string;
        };
        /** LayoutCandidate */
        LayoutCandidate: {
            /** Code */
            code: string;
            /** Display */
            display: string;
            /**
             * Family
             * @default
             */
            family: string;
            /**
             * Fit
             * @description 0~100, 업종판 제작 중이면 −1
             */
            fit: number;
            /**
             * State
             * @enum {string}
             */
            state: "cur" | "req" | "normal" | "no";
            thumb: components["schemas"]["Thumb"];
            /** Why */
            why: string;
        };
        /** LayoutCatalog */
        LayoutCatalog: {
            /** Counts */
            counts: {
                [key: string]: number;
            };
            /** Items */
            items: components["schemas"]["LayoutCatalogEntry"][];
        };
        /** LayoutCatalogEntry */
        LayoutCatalogEntry: {
            /** Board */
            board: string;
            /** Code */
            code: string;
            /** Display */
            display: string;
            /** Family */
            family: string;
            /**
             * Has Images
             * @default false
             */
            has_images: boolean;
            /** Industry Code */
            industry_code?: string | null;
            /** Name */
            name: string;
            /** Pack Role */
            pack_role?: string | null;
            /** Role */
            role: string;
            /**
             * Shape
             * @default
             */
            shape: string;
            /**
             * Status
             * @default ready
             * @enum {string}
             */
            status: "ready" | "in_production";
            thumb: components["schemas"]["Thumb"];
            /**
             * When
             * @default
             */
            when: string;
        };
        /** LayoutChip */
        LayoutChip: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "code" | "pinned" | "text" | "pack";
            /** T */
            t: string;
        };
        /** LayoutChoice */
        LayoutChoice: {
            /** Key */
            key?: string | null;
            /** Layout Code */
            layout_code?: string | null;
            /**
             * Pinned
             * @default false
             */
            pinned: boolean;
        };
        /** LayoutHeader */
        LayoutHeader: {
            /** Image */
            image: number;
            /** Industry */
            industry: number;
            /** No Image */
            no_image: number;
        };
        /** LayoutOption */
        LayoutOption: {
            /** Desc */
            desc: string;
            effect?: components["schemas"]["LayoutOptionEffect"];
            /** Fit */
            fit: number;
            /**
             * Key
             * @enum {string}
             */
            key: "A" | "B" | "C";
            /**
             * Recommended
             * @default false
             */
            recommended: boolean;
            /** Title */
            title: string;
        };
        /** LayoutOptionEffect */
        LayoutOptionEffect: {
            /** Add Sheet */
            add_sheet?: string | null;
            /** Keep */
            keep?: boolean | null;
            /** Move To Notes */
            move_to_notes?: string | null;
            /** Replace Layout */
            replace_layout?: string | null;
        };
        /** LayoutOptions */
        LayoutOptions: {
            /** Candidates */
            candidates: components["schemas"]["LayoutCandidate"][];
            header: components["schemas"]["LayoutHeader"];
            /** Intro */
            intro: string;
            /** Options */
            options?: components["schemas"]["LayoutOption"][] | null;
            /** Other Sheets Label */
            other_sheets_label: string;
            /** Pillars */
            pillars: number;
            /**
             * Pinned
             * @default false
             */
            pinned: boolean;
            /** Request Id */
            request_id?: string | null;
            /** Sheet Id */
            sheet_id: string;
            /** Sheet Label */
            sheet_label: string;
        };
        /** LayoutPick */
        LayoutPick: {
            /**
             * Chosen By
             * @default agent
             * @enum {string}
             */
            chosen_by: "agent" | "user";
            /**
             * Code
             * @description 정본 코드(VP-F3)
             */
            code: string;
            /**
             * Display
             * @description 화면 코드(VP-F·3)
             */
            display: string;
            /** Family */
            family: string;
            /** Fit */
            fit?: number | null;
            /** Industry Code */
            industry_code?: string | null;
            /** Name */
            name: string;
            /**
             * Pinned
             * @default false
             */
            pinned: boolean;
            thumb: components["schemas"]["Thumb"];
            /**
             * Why
             * @default
             */
            why: string;
        };
        /** LayoutRequest */
        LayoutRequest: {
            choice?: components["schemas"]["LayoutChoice"] | null;
            /** Id */
            id: string;
            /**
             * Intro
             * @default
             */
            intro: string;
            /** Options */
            options?: components["schemas"]["LayoutOption"][];
            /**
             * Request Text
             * @default
             */
            request_text: string;
            /** Requested Code */
            requested_code?: string | null;
            /** Sheet Id */
            sheet_id: string;
            /**
             * Status
             * @default open
             * @enum {string}
             */
            status: "open" | "applied" | "canceled";
        };
        /** LegendRow */
        LegendRow: {
            /** Desc */
            desc: string;
            /** Label */
            label: string;
            /**
             * Mode
             * @enum {string}
             */
            mode: "auto" | "check" | "ask" | "pin";
        };
        /** MaterialItem */
        MaterialItem: {
            /**
             * Approver
             * @default false
             */
            approver: boolean;
            /**
             * Axis
             * @enum {string}
             */
            axis: "challenge" | "value" | "evidence" | "stakeholder" | "product";
            /**
             * Cost
             * @default false
             */
            cost: boolean;
            /**
             * Excluded
             * @default false
             */
            excluded: boolean;
            /** Flags */
            flags?: string[];
            /** Group */
            group?: string | null;
            /** Id */
            id: string;
            metric?: components["schemas"]["MaterialMetric"] | null;
            number?: components["schemas"]["NumberValue"] | null;
            /** Product Refs */
            product_refs?: components["schemas"]["KBRef"][];
            /** Sources */
            sources?: components["schemas"]["SourceTag"][];
            /**
             * State
             * @default new
             * @enum {string}
             */
            state: "new" | "merged" | "rewritten" | "refetched" | "inferred";
            /** Text */
            text: string;
        };
        /** MaterialMetric */
        MaterialMetric: {
            after: components["schemas"]["NumberValue"];
            before: components["schemas"]["NumberValue"];
            /** Label */
            label: string;
        };
        /** MessageBody */
        MessageBody: {
            /**
             * Context
             * @enum {string}
             */
            context: "materials" | "questions" | "structure" | "result" | "layout" | "numbers" | "images" | "export";
            /** Sheet Id */
            sheet_id?: string | null;
            /** Text */
            text: string;
        };
        /** Metric */
        Metric: {
            after: components["schemas"]["NumberValue"];
            before: components["schemas"]["NumberValue"];
            /** Handling */
            handling?: ("request" | "industry_avg" | "exclude" | "direct") | null;
            /**
             * How
             * @default
             */
            how: string;
            /** Id */
            id: string;
            /**
             * Industry Avg Available
             * @default false
             */
            industry_avg_available: boolean;
            /** Label */
            label: string;
            /** Options */
            options?: string[];
            /**
             * Source Label
             * @default
             */
            source_label: string;
            /**
             * Status
             * @default ask
             * @enum {string}
             */
            status: "secured" | "estimated" | "ask" | "requested" | "excluded";
            /**
             * Status Label
             * @default
             */
            status_label: string;
        };
        /** MetricCounts */
        MetricCounts: {
            /** Estimated */
            estimated: number;
            /** Missing */
            missing: number;
            /** Secured */
            secured: number;
            /** Total */
            total: number;
        };
        /** MetricRule */
        MetricRule: {
            /** Current */
            current: string;
            /** Estimated */
            estimated: number;
            /** Secured */
            secured: number;
            /** Tail */
            tail?: string | null;
            /** Text */
            text: string;
            /** Usable */
            usable: number;
            /** Would Switch To */
            would_switch_to?: string | null;
        };
        /** MetricsView */
        MetricsView: {
            /** Code */
            code: string;
            counts: components["schemas"]["MetricCounts"];
            /** Intro */
            intro: string;
            /** Metrics */
            metrics: components["schemas"]["Metric"][];
            /**
             * Pending Ask
             * @default 0
             */
            pending_ask: number;
            /**
             * Pending Check
             * @default 0
             */
            pending_check: number;
            rule: components["schemas"]["MetricRule"];
            /** Sheet Id */
            sheet_id: string;
        };
        /** NumberSource */
        NumberSource: {
            /** As Of */
            as_of?: string | null;
            /**
             * Kind
             * @default customer
             * @enum {string}
             */
            kind: "customer" | "rfp" | "requirements" | "interview" | "case" | "industry_avg" | "mi" | "web" | "user" | "quote" | "kb" | "storyboard";
            /**
             * Label
             * @default
             */
            label: string;
            /** Refs */
            refs?: string[];
            /** Tier */
            tier?: string | null;
        };
        /** NumberValue */
        NumberValue: {
            /**
             * Display
             * @description '12초' | '3~5초' | '[00]시간'
             */
            display: string;
            /** Estimate Basis */
            estimate_basis?: string | null;
            source?: components["schemas"]["NumberSource"] | null;
            /**
             * Status
             * @default missing
             * @enum {string}
             */
            status: "secured" | "estimated" | "missing" | "requested" | "excluded";
            /** Unit */
            unit?: string | null;
            /** Value */
            value?: number | null;
            /** Value2 */
            value2?: number | null;
        };
        /** OneLinerContent */
        OneLinerContent: {
            /** Evidence */
            evidence?: string[];
            /** Image Slot Id */
            image_slot_id?: string | null;
            /** Statement */
            statement: string;
        };
        /** Owner */
        Owner: {
            /** Name */
            name: string;
            /** User Id */
            user_id: string;
        };
        /** Package */
        Package: {
            counts: components["schemas"]["PackageCounts"];
            /** Interview Numbers */
            interview_numbers?: string[];
            /**
             * Needs Variant
             * @description 퀵윈인데 VP-G 변형이 아직 없음(넘길 때 만든다)
             * @default false
             */
            needs_variant: boolean;
            /** Path Label */
            path_label: string;
            /**
             * Proposal Type
             * @enum {string}
             */
            proposal_type: "standard" | "quickwin" | "solution";
            /** Rows */
            rows: components["schemas"]["PackageRow"][];
            /** Sheets */
            sheets: components["schemas"]["PackageSheet"][];
            /** Sources Footer */
            sources_footer?: string[];
            /** Type Label */
            type_label: string;
        };
        /** PackageCounts */
        PackageCounts: {
            /** Added Not In Section */
            added_not_in_section: number;
            /** Estimates As Notes */
            estimates_as_notes: number;
            /** Send */
            send: number;
        };
        /** PackageRow */
        PackageRow: {
            /** Code */
            code: string;
            /** Sheet Label */
            sheet_label: string;
            /** Treatment */
            treatment: string;
        };
        /** PackageSet */
        PackageSet: {
            /** Dock */
            dock: string;
            /** Estimates Note */
            estimates_note?: string | null;
            /**
             * Selected
             * @enum {string}
             */
            selected: "standard" | "quickwin" | "solution";
            /** Types */
            types: components["schemas"]["Package"][];
        };
        /** PackageSheet */
        PackageSheet: {
            content: components["schemas"]["SheetContent"];
            /** Image Slots */
            image_slots?: components["schemas"]["ImageSlot"][];
            layout: components["schemas"]["LayoutPick"];
            /**
             * Pinned
             * @default false
             */
            pinned: boolean;
            /**
             * Points
             * @default
             */
            points: string;
            /**
             * Role
             * @enum {string}
             */
            role: "CH" | "VP" | "EF" | "REF";
            /** Sheet Id */
            sheet_id?: string | null;
            /**
             * Speaker Notes
             * @default
             */
            speaker_notes: string;
            /** Title */
            title: string;
        };
        /** PackChange */
        PackChange: {
            /** From Code */
            from_code: string;
            /** Sheet Id */
            sheet_id: string;
            /** To Code */
            to_code: string;
        };
        /** PackDecide */
        PackDecide: {
            /**
             * Decision
             * @enum {string}
             */
            decision: "apply" | "dismiss";
        };
        /** PackOffer */
        PackOffer: {
            /** Changes */
            changes?: components["schemas"]["PackChange"][];
            /** Id */
            id: string;
            /** Industry Code */
            industry_code: string;
            /**
             * Status
             * @default open
             * @enum {string}
             */
            status: "open" | "applied" | "dismissed";
        };
        /** PageRef */
        PageRef: {
            /**
             * Title
             * @default
             */
            title: string;
            /**
             * Url
             * @default
             */
            url: string;
        };
        /** PairItem */
        PairItem: {
            /** Challenge */
            challenge: string;
            /** Image Slot Id */
            image_slot_id?: string | null;
            product?: components["schemas"]["KBRef"] | null;
            /**
             * Value
             * @default
             */
            value: string;
        };
        /** PatchMetric */
        PatchMetric: {
            after?: components["schemas"]["NumberValue"] | null;
            before?: components["schemas"]["NumberValue"] | null;
            /**
             * Handling
             * @enum {string}
             */
            handling: "request" | "industry_avg" | "exclude" | "direct";
        };
        /** PatchPlan */
        PatchPlan: {
            override: components["schemas"]["PlanOverride"];
        };
        /** PatchSheet */
        PatchSheet: {
            /** @description 보낸 필드만 바꾼다(예: pillars 만) */
            content?: components["schemas"]["SheetContent"] | null;
            /** Pinned */
            pinned?: boolean | null;
            /** Points */
            points?: string | null;
            /** Speaker Notes */
            speaker_notes?: string | null;
            /** Title */
            title?: string | null;
        };
        /** PatchVP */
        PatchVP: {
            /** Auto Answer */
            auto_answer?: boolean | null;
            /**
             * Clear Industry
             * @description 업종 고정 풀기(다시 판별)
             * @default false
             */
            clear_industry: boolean;
            /** Customer Name */
            customer_name?: string | null;
            industry?: components["schemas"]["IndustryCode"] | null;
            /** Note */
            note?: string | null;
            target_proposal?: components["schemas"]["TargetProposal"] | null;
            /** Title */
            title?: string | null;
        };
        /** PillarItem */
        PillarItem: {
            /**
             * Body
             * @default
             */
            body: string;
            /** Id */
            id: string;
            /** Image Slot Id */
            image_slot_id?: string | null;
            /** Km Ref */
            km_ref?: string | null;
            /** Product Refs */
            product_refs?: components["schemas"]["KBRef"][];
            /** Proof Ids */
            proof_ids?: string[];
            /** Title */
            title: string;
        };
        /** Plan */
        Plan: {
            /** Alternatives */
            alternatives?: components["schemas"]["PlanAlternative"][];
            /** Chips */
            chips?: components["schemas"]["LayoutChip"][];
            /** Cta Label */
            cta_label: string;
            /**
             * Decisions
             * @description VP2 `그 밖에 정한 것` 7행(고정 순서)
             */
            decisions?: components["schemas"]["PlanDecisionRow"][];
            /** Flow */
            flow: string;
            /** Flow Label */
            flow_label: string;
            /**
             * Intro
             * @default
             */
            intro: string;
            /** Omitted */
            omitted?: components["schemas"]["PlanOmitted"][];
            /** Overrides */
            overrides?: {
                [key: string]: string;
            };
            /** Reason */
            reason: string;
            /** Sheets */
            sheets: components["schemas"]["PlanSheet"][];
        };
        /** PlanAlternative */
        PlanAlternative: {
            /** Code */
            code: string;
            /** Display */
            display: string;
            /** Label */
            label: string;
            /** Prerequisite */
            prerequisite?: ("quote" | "stakeholders") | null;
            /**
             * Role
             * @default VP
             * @enum {string}
             */
            role: "CH" | "VP" | "EF";
            /** Tip */
            tip: string;
        };
        /** PlanDecisionRow */
        PlanDecisionRow: {
            /** Key */
            key: string;
            /**
             * Mode
             * @default auto
             * @enum {string}
             */
            mode: "auto" | "check" | "ask" | "pin";
            /** Value */
            value: string;
            /** Why */
            why: string;
        };
        /** PlanOmitted */
        PlanOmitted: {
            /** Label */
            label: string;
            /**
             * Role
             * @enum {string}
             */
            role: "CH" | "VP" | "EF";
            /**
             * Why
             * @default
             */
            why: string;
        };
        /** PlanOverride */
        PlanOverride: {
            /** Ch */
            CH?: string | null;
            /**
             * Clear
             * @description 대안 선택을 모두 풀기
             * @default false
             */
            clear: boolean;
            /** Ef */
            EF?: string | null;
            /** Vp */
            VP?: string | null;
        };
        /** PlanSheet */
        PlanSheet: {
            /**
             * Chip
             * @default
             */
            chip: string;
            /**
             * Content Preview
             * @default
             */
            content_preview: string;
            layout: components["schemas"]["LayoutPick"];
            /**
             * Mode
             * @default auto
             * @enum {string}
             */
            mode: "auto" | "check" | "ask" | "pin";
            /**
             * Role
             * @enum {string}
             */
            role: "CH" | "VP" | "EF";
            /** Step Label */
            step_label: string;
        };
        /**
         * ProposalHandoff
         * @description 10-proposal.md §8.0 ProposalHandoff v1.
         */
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
            facts?: {
                [key: string]: unknown;
            }[];
            /** Items */
            items: {
                [key: string]: unknown;
            }[];
            /**
             * Live Link
             * @default false
             */
            live_link: boolean;
            /** Rq Ref */
            rq_ref?: {
                [key: string]: unknown;
            } | null;
            /** Source */
            source: {
                [key: string]: unknown;
            };
            /** Target */
            target: {
                [key: string]: unknown;
            };
        };
        /** ProposalRelease */
        ProposalRelease: {
            /** Linked Proposal */
            linked_proposal?: {
                [key: string]: unknown;
            } | null;
            /** Proposal Id */
            proposal_id: string;
            /** Released */
            released: boolean;
            /** Vp Id */
            vp_id: string;
        };
        /**
         * ProposalReleaseIn
         * @description `POST /v1/vps/{vp_id}:release-proposal`(internal) — proposal 이 제안서를 지웠을 때.
         */
        ProposalReleaseIn: {
            /** Proposal Id */
            proposal_id: string;
        };
        /** PutImageSlot */
        PutImageSlot: {
            asset: components["schemas"]["AssetRef"];
        };
        /** PutSources */
        PutSources: {
            /** Sources */
            sources: components["schemas"]["SourceToggle"][];
        };
        /** Question */
        Question: {
            answer?: components["schemas"]["QuestionAnswer"] | null;
            /**
             * Aside
             * @default
             */
            aside: string;
            /** Context Text */
            context_text?: string | null;
            /** Default Keys */
            default_keys?: string[];
            /** Hint */
            hint?: string | null;
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "direction" | "approver" | "industry" | "sb_mi_conflict" | "investment" | "interview_numbers";
            /**
             * Mode
             * @enum {string}
             */
            mode: "ask" | "check";
            /**
             * Multi
             * @default false
             */
            multi: boolean;
            /** No */
            no: number;
            /** Options */
            options?: components["schemas"]["QuestionOption"][];
            /**
             * Selected Keys
             * @description 화면이 보여 줄 현재 선택(직접 답하기 해석 결과 포함)
             */
            selected_keys?: string[];
            /**
             * Status
             * @default open
             * @enum {string}
             */
            status: "open" | "answered" | "defaulted";
            /** Title */
            title: string;
        };
        /** QuestionAnswer */
        QuestionAnswer: {
            /**
             * By
             * @default user
             * @enum {string}
             */
            by: "user" | "default";
            /** Keys */
            keys?: string[];
            /** Text */
            text?: string | null;
        };
        /** QuestionOption */
        QuestionOption: {
            /** Desc */
            desc?: string | null;
            /** Key */
            key: string;
            /** Label */
            label: string;
            preview?: components["schemas"]["QuestionPreview"] | null;
            /**
             * Recommended
             * @default false
             */
            recommended: boolean;
        };
        /** QuestionPreview */
        QuestionPreview: {
            /** Code */
            code: string;
            /** Display */
            display: string;
            /** Effect */
            effect: string;
            thumb: components["schemas"]["Thumb"];
        };
        /** ReferenceContent */
        ReferenceContent: {
            /** Deployment Id */
            deployment_id: string;
            /**
             * Summary
             * @default
             */
            summary: string;
            /** Title */
            title: string;
            /**
             * Url
             * @default
             */
            url: string;
        };
        /** Restyle */
        Restyle: {
            /**
             * Style
             * @default illustration
             * @constant
             */
            style: "illustration";
        };
        /** Roi */
        Roi: {
            investment: components["schemas"]["NumberValue"];
            /** Payback Months */
            payback_months?: number[];
            /** Quote File Id */
            quote_file_id?: string | null;
            /** Savings */
            savings?: components["schemas"]["NumberValue"][];
            /** Scenario Labels */
            scenario_labels?: string[];
        };
        /** RoutingRules */
        RoutingRules: {
            /** Asks */
            asks: {
                [key: string]: unknown;
            }[];
            /** Asks Title */
            asks_title: string;
            /** Band */
            band: components["schemas"]["BandRow"][];
            /** Band Head */
            band_head: string[];
            /** Band Sub */
            band_sub: string;
            /** Band Title */
            band_title: string;
            /**
             * Eyebrow
             * @default ROUTING · VALUE PROPOSITION
             */
            eyebrow: string;
            /** Gaps */
            gaps: components["schemas"]["RuleRow"][];
            /** Gaps Sub */
            gaps_sub: string;
            /** Gaps Title */
            gaps_title: string;
            /** Legend */
            legend: components["schemas"]["LegendRow"][];
            /** Packs */
            packs: {
                [key: string]: unknown;
            };
            /** Stages */
            stages: components["schemas"]["RuleStage"][];
            /** Thresholds */
            thresholds: {
                [key: string]: unknown;
            };
            /** Title */
            title: string;
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
            /** O */
            o: string;
        };
        /** RuleStage */
        RuleStage: {
            /** No */
            no: number;
            /** Rules */
            rules: components["schemas"]["RuleRow"][];
            /** Sub */
            sub: string;
            /** Title */
            title: string;
        };
        /** SavePoint */
        SavePoint: {
            /**
             * Reason
             * @default 저장
             */
            reason: string;
        };
        /** ScenarioRow */
        ScenarioRow: {
            /** Asked */
            asked: string;
            /** Chips */
            chips: components["schemas"]["LayoutChip"][];
            /** Flow Label */
            flow_label: string;
            /** Industry */
            industry: string;
            /** Input */
            input: string;
            /**
             * Mode
             * @default
             */
            mode: string;
            /** Name */
            name: string;
            /** No */
            no: number;
            /** Pack */
            pack: string;
            /**
             * Scene
             * @default
             */
            scene: string;
        };
        /** Scenarios */
        Scenarios: {
            /** Rows */
            rows: components["schemas"]["ScenarioRow"][];
            /** Stats */
            stats: {
                [key: string]: string;
            }[];
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
        /** Sheet */
        Sheet: {
            content?: components["schemas"]["SheetContent"];
            /** Id */
            id: string;
            /**
             * Include Default
             * @default true
             */
            include_default: boolean;
            /**
             * Kind
             * @default main
             * @enum {string}
             */
            kind: "main" | "one_liner" | "reference" | "summary";
            layout: components["schemas"]["LayoutPick"];
            /**
             * Meta Label
             * @default
             */
            meta_label: string;
            /**
             * Mode
             * @default auto
             * @enum {string}
             */
            mode: "auto" | "check" | "ask" | "pin";
            /** Order */
            order: number;
            /**
             * Pinned
             * @default false
             */
            pinned: boolean;
            /**
             * Points
             * @default
             */
            points: string;
            /**
             * Role
             * @enum {string}
             */
            role: "CH" | "VP" | "EF" | "REF";
            /**
             * Speaker Notes
             * @default
             */
            speaker_notes: string;
            /**
             * Status
             * @default waiting
             * @enum {string}
             */
            status: "waiting" | "writing" | "done";
            /** Step Label */
            step_label: string;
            /**
             * Title
             * @default
             */
            title: string;
            /** Variant Of */
            variant_of?: string | null;
        };
        /** SheetContent */
        SheetContent: {
            /** Challenges */
            challenges?: components["schemas"]["ChallengeItem"][] | null;
            /** Metrics */
            metrics?: components["schemas"]["Metric"][] | null;
            one_liner?: components["schemas"]["OneLinerContent"] | null;
            /** Pairs */
            pairs?: components["schemas"]["PairItem"][] | null;
            /** Pillars */
            pillars?: components["schemas"]["PillarItem"][] | null;
            /** Qualitative */
            qualitative?: string[] | null;
            reference?: components["schemas"]["ReferenceContent"] | null;
            roi?: components["schemas"]["Roi"] | null;
            /** Stakeholders */
            stakeholders?: components["schemas"]["StakeholderItem"][] | null;
        };
        /** SlotCandidate */
        SlotCandidate: {
            asset?: components["schemas"]["AssetRef"] | null;
            /**
             * Current
             * @default false
             */
            current: boolean;
            meta?: components["schemas"]["ImageMeta"] | null;
            /**
             * Mode
             * @default auto
             * @enum {string}
             */
            mode: "auto" | "check";
            /** Name */
            name: string;
            /**
             * Tier
             * @enum {string}
             */
            tier: "customer" | "cut" | "case" | "ui" | "illust";
            /** Tier Label */
            tier_label: string;
        };
        /** SlotCandidates */
        SlotCandidates: {
            /** Header */
            header: string;
            /** Items */
            items: components["schemas"]["SlotCandidate"][];
            /**
             * Right
             * @default
             */
            right: string;
            /** Slot Id */
            slot_id: string;
        };
        /** SlotFlags */
        SlotFlags: {
            /** Case Caption Required */
            case_caption_required?: boolean | null;
            /** Customer Unconfirmed */
            customer_unconfirmed?: boolean | null;
            /** Fallback Level */
            fallback_level?: string | null;
            /** Generated */
            generated?: boolean | null;
            /** Not Real Data */
            not_real_data?: boolean | null;
            /** Other Brand Visible */
            other_brand_visible?: boolean | null;
            /** Similar Model */
            similar_model?: boolean | null;
        };
        /** SlotSubject */
        SlotSubject: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "product" | "solution" | "space" | "case" | "customer";
            /**
             * Label
             * @default
             */
            label: string;
            /** Refs */
            refs?: components["schemas"]["KBRef"][];
            /** Space Type Id */
            space_type_id?: string | null;
        };
        /** Source */
        Source: {
            /**
             * Connected
             * @default true
             */
            connected: boolean;
            /** Fetched At */
            fetched_at?: string | null;
            /** Fetched Version */
            fetched_version?: number | null;
            gives?: components["schemas"]["SourceGives"];
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "storyboard" | "mi" | "requirements" | "case" | "vp";
            /**
             * Kind Label
             * @default
             */
            kind_label: string;
            /** Ref Id */
            ref_id: string;
            /**
             * Status
             * @default connected
             * @enum {string}
             */
            status: "connected" | "recommended";
            /** Title */
            title: string;
        };
        /** SourceCandidate */
        SourceCandidate: {
            /**
             * Connected
             * @default true
             */
            connected: boolean;
            /** Fetched At */
            fetched_at?: string | null;
            /** Fetched Version */
            fetched_version?: number | null;
            gives?: components["schemas"]["SourceGives"];
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "storyboard" | "mi" | "requirements" | "case" | "vp";
            /**
             * Kind Label
             * @default
             */
            kind_label: string;
            /**
             * Recommended
             * @default false
             */
            recommended: boolean;
            /** Ref Id */
            ref_id: string;
            /**
             * Status
             * @default connected
             * @enum {string}
             */
            status: "connected" | "recommended";
            /** Title */
            title: string;
        };
        /** SourceCandidates */
        SourceCandidates: {
            /** Found Label */
            found_label: string;
            /** Items */
            items: components["schemas"]["SourceCandidate"][];
        };
        /** SourceGives */
        SourceGives: {
            /** Axes */
            axes?: string[];
            /** Counts */
            counts?: {
                [key: string]: number;
            };
            /**
             * Summary
             * @default
             */
            summary: string;
        };
        /** SourceRef */
        SourceRef: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "storyboard" | "mi" | "requirements" | "case" | "vp";
            /** Ref Id */
            ref_id: string;
        };
        /** SourceTag */
        SourceTag: {
            /** As Of */
            as_of?: string | null;
            /** Locator */
            locator?: string | null;
            /**
             * Ref Id
             * @default
             */
            ref_id: string;
            /**
             * Tag
             * @enum {string}
             */
            tag: "SB" | "MI" | "RFP" | "CS" | "RQ" | "QT" | "USER" | "KB" | "VP";
        };
        /** SourceToggle */
        SourceToggle: {
            /** Connected */
            connected: boolean;
            /**
             * Kind
             * @enum {string}
             */
            kind: "storyboard" | "mi" | "requirements" | "case" | "vp";
            /** Ref Id */
            ref_id: string;
            /** Title */
            title?: string | null;
        };
        /** StakeholderItem */
        StakeholderItem: {
            /** Id */
            id: string;
            /** Image Slot Id */
            image_slot_id?: string | null;
            /**
             * Kpi
             * @default
             */
            kpi: string;
            /** Product Refs */
            product_refs?: components["schemas"]["KBRef"][];
            /** Role */
            role: string;
            /**
             * Value
             * @default
             */
            value: string;
        };
        /** TargetProposal */
        TargetProposal: {
            /** Proposal Id */
            proposal_id?: string | null;
            /**
             * Section Label
             * @default Value Props
             */
            section_label: string;
            /**
             * Title
             * @default
             */
            title: string;
            /**
             * Type
             * @default standard
             * @enum {string}
             */
            type: "standard" | "quickwin" | "solution";
        };
        /** Thumb */
        Thumb: {
            /** Kind */
            kind: string;
            /**
             * N
             * @default 3
             */
            n: number;
        };
        /** UsageHistory */
        UsageHistory: {
            /**
             * Count
             * @default 0
             */
            count: number;
            /**
             * Label
             * @default Winmate 제안서 0건
             */
            label: string;
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
        /** VMAddValue */
        VMAddValue: {
            /** Message */
            message: string;
            /** Need */
            need?: string | null;
            /** Req */
            req?: string | null;
            /**
             * Space
             * @default 전체
             */
            space: string;
        };
        /** VMCandidate */
        VMCandidate: {
            /**
             * Dss Status
             * @description added = DSS 다시 가져오기로 새로 들어온 후보(고르지 않은 채로)
             */
            dss_status?: "added" | null;
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
        /** VMCounts */
        VMCounts: {
            /** Items */
            items: number;
            /** Needs */
            needs: number;
            /** Needs Missing */
            needs_missing: number;
            /** Pending */
            pending: number;
            /** Values */
            values: number;
        };
        /** VMCreate */
        VMCreate: {
            /**
             * Candidates
             * @description DSS 제품 · 솔루션. 없으면 context_text 로 KB S1 에서 공간별 후보를 찾는다
             */
            candidates?: components["schemas"]["VMCandidate"][] | null;
            /** Context Text */
            context_text?: string | null;
            /** Sb Id */
            sb_id?: string | null;
            /**
             * Select All
             * @description 후보를 처음부터 모두 고른다
             * @default true
             */
            select_all: boolean;
            /** Title */
            title?: string | null;
        };
        /** VMDoc */
        VMDoc: {
            /**
             * Candidates
             * @description DSS 에서 온 고를 수 있는 제품 · 솔루션
             */
            candidates?: components["schemas"]["VMCandidate"][];
            /**
             * Code
             * @description 화면 · flow.json 에 쓰는 짧은 번호(VP-01 …)
             */
            code?: string | null;
            /**
             * Context Text
             * @description 요구 · Storyboard 요약(AI 추천 문맥)
             */
            context_text?: string | null;
            counts: components["schemas"]["VMCounts"];
            /** Created At */
            created_at: string;
            /** @description 허브의 DSS 가 바뀌었으면 그 차이(GET · :resync-dss 응답에서만 계산 — 다른 고침 응답은 null) */
            dss_changed?: components["schemas"]["VMDssChange"] | null;
            /**
             * Dss Ref
             * @description Storyboard(Gate)로 만들 때 가져온 DSS 코드(DSS-01 …) — 없으면 DSS 다시 가져오기 대상이 아님
             */
            dss_ref?: string | null;
            /**
             * Dss Ver
             * @description 가져온 DSS 판(허브 stages.dss.ver)
             */
            dss_ver?: number | null;
            /** Id */
            id: string;
            /**
             * Items
             * @description 고른 제품 · 솔루션(이 순서로 보인다)
             */
            items?: components["schemas"]["VMItem"][];
            last_resync?: components["schemas"]["VMResync"] | null;
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
             * @description 저장(완료) 판 — flow.json stages.vp.ver
             */
            ver?: number | null;
            /** Version */
            version: number;
        };
        /**
         * VMDssChange
         * @description Storyboard 의 DSS 가 맵을 만든(다시 가져온) 뒤 바뀌었다 — 편집 화면 위 안내 줄.
         */
        VMDssChange: {
            /**
             * Added
             * @description 새로 들어온 DSS 제품 · 솔루션
             */
            added: number;
            /** Added Names */
            added_names?: string[];
            /**
             * Changed
             * @description 놓인 공간이 바뀐 제품
             * @default 0
             */
            changed: number;
            /**
             * From
             * @description 맵이 가져온 DSS(DSS-01 v1)
             */
            from: string;
            /**
             * Ref Changed
             * @description DSS 자체가 바뀜(분기 등으로 다른 DSS)
             * @default false
             */
            ref_changed: boolean;
            /**
             * Removed
             * @description DSS 에서 빠진 제품 · 솔루션
             */
            removed: number;
            /** Removed Names */
            removed_names?: string[];
            /**
             * To
             * @description 허브의 지금 DSS(DSS-01 v2 · 분기로 바뀌면 DSS-02 v1)
             */
            to: string;
        };
        /** VMFlowSync */
        VMFlowSync: {
            /**
             * Md Added
             * @description Storyboard 요약본에 더해진 부분
             */
            md_added: string;
            /**
             * Synced
             * @description 같은 VP 가 연결돼 함께 바뀐 다른 Storyboard
             */
            synced?: string[];
        };
        /** VMImportValue */
        VMImportValue: {
            /** From Map */
            from_map: string;
            /** Value Id */
            value_id: string;
        };
        /** VMInferNeedResult */
        VMInferNeedResult: {
            map: components["schemas"]["VMDoc"];
            need: components["schemas"]["VMNeed"] | null;
            /** Reason */
            reason?: string | null;
        };
        /** VMItem */
        VMItem: {
            /**
             * Dss Status
             * @description removed = 골라 둔 것이 Storyboard 의 DSS 에서 빠짐(가치와 함께 남겨 둠)
             */
            dss_status?: "removed" | null;
            /**
             * From Dss
             * @default true
             */
            from_dss: boolean;
            /**
             * Key
             * @description 맵 안에서 제품 · 솔루션을 가리키는 키(이름에서 만든 slug)
             */
            key: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "product" | "solution";
            /** Name */
            name: string;
            /**
             * Ref
             * @description KB 참조 — kb:family:fam_… · kb:solution:sol_… · kb:model:…
             */
            ref?: string | null;
            /** Spaces */
            spaces?: string[];
            /** Values */
            values?: components["schemas"]["VMValue"][];
        };
        /** VMLinked */
        VMLinked: {
            /** Here */
            here: components["schemas"]["VMLinkedValue"][];
            item: components["schemas"]["VMItem"];
            /**
             * Official
             * @description KB 원문 메시지(삼성 공식 · 원문 그대로)
             */
            official: components["schemas"]["VMOfficialMessage"][];
            /** Other */
            other: components["schemas"]["VMLinkedValue"][];
        };
        /** VMLinkedValue */
        VMLinkedValue: {
            /** By */
            by: string;
            /** Map Id */
            map_id: string;
            /** Map Title */
            map_title: string;
            /** Message */
            message: string;
            /** Need */
            need?: string | null;
            /** Req */
            req?: string | null;
            /** Sb Id */
            sb_id?: string | null;
            /** Space */
            space: string;
            /** Value Id */
            value_id: string;
        };
        /** VMList */
        VMList: {
            /** Items */
            items: components["schemas"]["VMListItem"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** VMListItem */
        VMListItem: {
            /** Code */
            code?: string | null;
            counts: components["schemas"]["VMCounts"];
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
        /** VMNeed */
        VMNeed: {
            /**
             * By
             * @default manual
             * @enum {string}
             */
            by: "manual" | "ai-pending" | "ai-accepted";
            /** Text */
            text: string;
        };
        /** VMOfficialMessage */
        VMOfficialMessage: {
            /**
             * Claim Flag
             * @default false
             */
            claim_flag: boolean;
            /** Level */
            level: string;
            /** Source Url */
            source_url?: string | null;
            /** Text */
            text: string;
        };
        /** VMPatchValue */
        VMPatchValue: {
            /**
             * Accept
             * @description AI 가치 후보 수락(ai-pending → ai-accepted)
             */
            accept?: boolean | null;
            /**
             * Accept Need
             * @description AI 니즈 추론 수락
             */
            accept_need?: boolean | null;
            /** Message */
            message?: string | null;
            /**
             * Need
             * @description 빈 문자열이면 니즈를 지운다
             */
            need?: string | null;
            /** Req */
            req?: string | null;
            /** Space */
            space?: string | null;
        };
        /**
         * VMResync
         * @description 마지막 DSS 다시 가져오기 결과(토스트 · 표시).
         */
        VMResync: {
            /**
             * Added
             * @description 새 후보(고르기 대화상자에 「새로」) — 자동으로 고르지 않음
             */
            added?: string[];
            /** At */
            at: string;
            /** From */
            from: string;
            /**
             * Kept
             * @description 골라 둔 것이 DSS 에서 빠져 남기고 「DSS에서 빠짐」 표시한 것
             */
            kept?: string[];
            /**
             * Removed
             * @description 고르지 않은 채 DSS 에서 빠져 후보에서 뺀 것
             */
            removed?: string[];
            /** To */
            to: string;
            /**
             * Updated
             * @description DSS 공간이 바뀐 고른 것
             */
            updated?: string[];
        };
        /** VMSetItems */
        VMSetItems: {
            /**
             * Items
             * @description 고를 제품 · 솔루션(순서대로). 빠진 것의 가치는 지운다
             */
            items: components["schemas"]["VMCandidate"][];
        };
        /** VMStageOut */
        VMStageOut: {
            /** @description Storyboard 허브에 반영된 결과(sb_id 가 없거나 허브가 안 되면 null) */
            flow_sync?: components["schemas"]["VMFlowSync"] | null;
            /**
             * Stage
             * @description Storyboard flow.json 의 stages.vp
             */
            stage: {
                [key: string]: unknown;
            };
            /** Summary Md */
            summary_md: string;
        };
        /** VMSuggestBody */
        VMSuggestBody: {
            /**
             * Item Keys
             * @description 이 제품 · 솔루션만(없으면 고른 것 모두)
             */
            item_keys?: string[] | null;
        };
        /** VMSuggestResult */
        VMSuggestResult: {
            /** Added Needs */
            added_needs: number;
            /** Added Values */
            added_values: number;
            map: components["schemas"]["VMDoc"];
            /**
             * Mode
             * @description llm = 모델이 다듬음 · kb_only = 모델 없이 KB 원문 메시지만(니즈는 비움)
             * @enum {string}
             */
            mode: "llm" | "kb_only";
        };
        /** VMValue */
        VMValue: {
            /**
             * Basis
             * @description AI 후보의 근거(KB 메시지 원문 출처 · 요구)
             */
            basis?: string | null;
            /**
             * By
             * @default manual
             * @enum {string}
             */
            by: "manual" | "ai-pending" | "ai-accepted";
            /** Id */
            id: string;
            /**
             * Message
             * @description 고객에게 주는 가치 한 문장
             */
            message: string;
            /** @description 고객의 니즈 — 고객이 할 말처럼 쓴 한 문장(예: 여름에도 쾌적한 교실 환경이 필요해요) */
            need?: components["schemas"]["VMNeed"] | null;
            /**
             * Req
             * @description 연결 요구(예: RQ-01 에너지 20% 절감)
             */
            req?: string | null;
            /**
             * Space
             * @description 공간(로비 · 회의실 …) 또는 '전체'
             */
            space: string;
        };
        /** VPCounts */
        VPCounts: {
            /**
             * All
             * @default 0
             */
            all: number;
            /**
             * Ask
             * @default 0
             */
            ask: number;
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
            /**
             * Run
             * @default 0
             */
            run: number;
        };
        /** VPDoc */
        VPDoc: {
            /**
             * Action Label
             * @default 이어서
             */
            action_label: string;
            active_job?: components["schemas"]["ActiveJob"] | null;
            /** Attachments */
            attachments?: components["schemas"]["Attachment"][];
            /**
             * Auto Answer
             * @default false
             */
            auto_answer: boolean;
            /**
             * Auto Chips
             * @description VP1Q `자동으로 정한 것`
             */
            auto_chips?: string[];
            /** Checks */
            checks?: components["schemas"]["CheckItem"][];
            /** Coverage */
            coverage?: components["schemas"]["CoverageAxis"][];
            /** Created At */
            created_at: string;
            /** Customer Name */
            customer_name?: string | null;
            /** Decisions */
            decisions?: components["schemas"]["Decision"][];
            /** Fixes */
            fixes?: components["schemas"]["Fix"][];
            /**
             * Generated
             * @default false
             */
            generated: boolean;
            /** Id */
            id: string;
            /** Image Slots */
            image_slots?: components["schemas"]["ImageSlot"][];
            industry?: components["schemas"]["Industry"] | null;
            /**
             * Intros
             * @description 에이전트 문장(materials_review · questions · questions_default · result · structure)
             */
            intros?: {
                [key: string]: string;
            };
            /**
             * Labels
             * @description 말풍선 · 요약(connect · questions · materials_footer · generate · head_codes)
             */
            labels?: {
                [key: string]: string;
            };
            /** Last Error */
            last_error?: {
                [key: string]: unknown;
            } | null;
            last_job?: components["schemas"]["ActiveJob"] | null;
            /** Layout Requests */
            layout_requests?: components["schemas"]["LayoutRequest"][];
            /**
             * Legend
             * @description VP1A 출처 범례(쓰인 출처만)
             */
            legend?: {
                [key: string]: string;
            }[];
            /** Linked Proposal */
            linked_proposal?: {
                [key: string]: unknown;
            } | null;
            /** Materials */
            materials?: components["schemas"]["MaterialItem"][];
            /**
             * Materials Ready
             * @default false
             */
            materials_ready: boolean;
            /**
             * Note
             * @default
             */
            note: string;
            owner: components["schemas"]["Owner"];
            /** Pack Offers */
            pack_offers?: components["schemas"]["PackOffer"][];
            plan?: components["schemas"]["Plan"] | null;
            /** Project Id */
            project_id?: string | null;
            /** Questions */
            questions?: components["schemas"]["Question"][];
            /**
             * Resume Route
             * @default
             */
            resume_route: string;
            /** Sheets */
            sheets?: components["schemas"]["Sheet"][];
            /** Sources */
            sources?: components["schemas"]["Source"][];
            /**
             * Start
             * @default direct
             * @enum {string}
             */
            start: "direct" | "storyboard" | "mi" | "clone" | "proposal";
            /**
             * Status
             * @default draft
             * @enum {string}
             */
            status: "draft" | "collecting" | "ask" | "planned" | "generating" | "check" | "done" | "stopped" | "failed";
            /**
             * Status Text
             * @default
             */
            status_text: string;
            /**
             * Step
             * @default 1
             */
            step: number;
            target_proposal?: components["schemas"]["TargetProposal"] | null;
            /** Title */
            title: string;
            /**
             * Ui Status
             * @default draft
             * @enum {string}
             */
            ui_status: "draft" | "ask" | "check" | "run" | "done";
            /** Updated At */
            updated_at: string;
            /** Variants */
            variants?: components["schemas"]["Sheet"][];
            /**
             * Version
             * @description 저장 지점 수(재료 완료 · 플랜 변경 · 생성 완료 · 레이아웃 적용 · 수치 반영 · 이미지 변경 · 넘김)
             */
            version: number;
        };
        /** VPList */
        VPList: {
            counts: components["schemas"]["VPCounts"];
            /** Items */
            items: components["schemas"]["VPListItem"][];
            /** Next Cursor */
            next_cursor?: string | null;
            /**
             * Total Label
             * @default
             */
            total_label: string;
        };
        /** VPListItem */
        VPListItem: {
            /** Action Label */
            action_label: string;
            /** Id */
            id: string;
            /** Industry */
            industry?: {
                [key: string]: string;
            } | null;
            /** Layout Chips */
            layout_chips?: components["schemas"]["LayoutChip"][];
            /** Linked Proposal */
            linked_proposal?: {
                [key: string]: unknown;
            } | null;
            /** Owner Name */
            owner_name: string;
            /** Resume Route */
            resume_route: string;
            /** Status Text */
            status_text: string;
            /** Title */
            title: string;
            /**
             * Ui Status
             * @enum {string}
             */
            ui_status: "draft" | "ask" | "check" | "run" | "done";
            /** Updated At */
            updated_at: string;
            /** When Label */
            when_label: string;
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
    get_vp_handoff: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vho: string;
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
    ack_vp_handoff: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vho: string;
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
    list_industry_packs: {
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
                    "application/json": components["schemas"]["IndustryPacks"];
                };
            };
        };
    };
    release_industry_pack: {
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
    list_layouts: {
        parameters: {
            query?: {
                family?: string | null;
                industry?: string | null;
                role?: string | null;
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
                    "application/json": components["schemas"]["LayoutCatalog"];
                };
            };
        };
    };
    get_routing_rules: {
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
    get_routing_scenarios: {
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
                    "application/json": components["schemas"]["Scenarios"];
                };
            };
        };
    };
    list_value_maps: {
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
                    "application/json": components["schemas"]["VMList"];
                };
            };
        };
    };
    create_value_map: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VMCreate"];
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
            /** @description Storyboard(Gate)로 시작했는데 같은 Storyboard 의 저장 전 초안이 이미 있으면 그 초안 */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VMDoc"];
                };
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VMDoc"];
                };
            };
        };
    };
    get_value_map: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                map_id: string;
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
                    "application/json": components["schemas"]["VMDoc"];
                };
            };
        };
    };
    delete_value_map: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                map_id: string;
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
                map_id: string;
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
                    "application/json": components["schemas"]["VMDoc"];
                };
            };
        };
    };
    finish: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                map_id: string;
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
                    "application/json": components["schemas"]["VMStageOut"];
                };
            };
        };
    };
    resync_value_map_dss: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                map_id: string;
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
                    "application/json": components["schemas"]["VMDoc"];
                };
            };
        };
    };
    suggest: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                map_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["VMSuggestBody"] | null;
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
                    "application/json": components["schemas"]["VMSuggestResult"];
                };
            };
        };
    };
    set_value_map_items: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                map_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VMSetItems"];
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
                    "application/json": components["schemas"]["VMDoc"];
                };
            };
        };
    };
    linked_values: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_key: string;
                map_id: string;
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
                    "application/json": components["schemas"]["VMLinked"];
                };
            };
        };
    };
    add_value: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_key: string;
                map_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VMAddValue"];
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
                    "application/json": components["schemas"]["VMDoc"];
                };
            };
        };
    };
    import_value: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                item_key: string;
                map_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VMImportValue"];
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
                    "application/json": components["schemas"]["VMDoc"];
                };
            };
        };
    };
    get_stage: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                map_id: string;
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
                    "application/json": components["schemas"]["VMStageOut"];
                };
            };
        };
    };
    delete_value: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                map_id: string;
                value_id: string;
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
                    "application/json": components["schemas"]["VMDoc"];
                };
            };
        };
    };
    patch_value: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                map_id: string;
                value_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VMPatchValue"];
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
                    "application/json": components["schemas"]["VMDoc"];
                };
            };
        };
    };
    infer_need: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                map_id: string;
                value_id: string;
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
                    "application/json": components["schemas"]["VMInferNeedResult"];
                };
            };
        };
    };
    draft_value_prop: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DraftBody"];
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
                    "application/json": components["schemas"]["DraftAccepted"];
                };
            };
        };
    };
    get_value_prop_proposal_handoff: {
        parameters: {
            query?: {
                section?: string | null;
                type?: ("standard" | "quickwin" | "solution") | null;
            };
            header?: never;
            path: {
                vp_id: string;
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
    list_vps: {
        parameters: {
            query?: {
                archived?: boolean;
                cursor?: string | null;
                /** @description 업종 코드(쉼표) · GEN */
                industry?: string | null;
                limit?: number;
                /** @description 고객사 · 작업명 · 레이아웃 코드 */
                q?: string | null;
                since_days?: number | null;
                /** @description draft,ask,check,run,done (쉼표) */
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
                    "application/json": components["schemas"]["VPList"];
                };
            };
        };
    };
    create_vp: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateVP"];
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
                    "application/json": components["schemas"]["VPDoc"];
                };
            };
        };
    };
    get_vp: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
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
                    "application/json": components["schemas"]["VPDoc"];
                };
            };
        };
    };
    patch_vp: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchVP"];
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
                    "application/json": components["schemas"]["VPDoc"];
                };
            };
        };
    };
    archive_vp: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
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
    clone_vp: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CloneVP"];
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
                    "application/json": components["schemas"]["VPDoc"];
                };
            };
        };
    };
    release_vp_proposal: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProposalReleaseIn"];
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
                    "application/json": components["schemas"]["ProposalRelease"];
                };
            };
        };
    };
    add_vp_attachment: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AddAttachment"];
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
                    "application/json": components["schemas"]["Attachment"];
                };
            };
            /** @description 고객 사진 — 이미지 칸 다시 맞추기 잡 */
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
    delete_vp_attachment: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                att_id: string;
                vp_id: string;
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
    get_copy_text: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
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
                    "application/json": components["schemas"]["CopyText"];
                };
            };
        };
    };
    get_data_request_draft: {
        parameters: {
            query?: {
                sheet?: string | null;
            };
            header?: never;
            path: {
                vp_id: string;
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
                    "application/json": components["schemas"]["DataRequestDraft"];
                };
            };
        };
    };
    create_vp_export: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
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
                    "application/json": components["schemas"]["JobAccepted"];
                };
            };
        };
    };
    get_vp_export: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vex: string;
                vp_id: string;
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
    decide_fix: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                fx: string;
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FixDecision"];
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
                    "application/json": components["schemas"]["VPDoc"];
                };
            };
        };
    };
    generate_vp: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
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
    create_vp_handoff: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
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
            /** @description 퀵윈 VP-G 변형을 만든 뒤 넘김 */
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
    list_image_slots: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
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
                    "application/json": components["schemas"]["ImageSlotsView"];
                };
            };
        };
    };
    put_image_slot: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vis: string;
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PutImageSlot"];
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
                    "application/json": components["schemas"]["ImageSlot"];
                };
            };
        };
    };
    list_slot_candidates: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vis: string;
                vp_id: string;
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
                    "application/json": components["schemas"]["SlotCandidates"];
                };
            };
        };
    };
    restyle_images: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["Restyle"] | null;
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
    cancel_layout_request: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vlr: string;
                vp_id: string;
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
    collect_materials: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["CollectBody"] | null;
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
    post_vp_message: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
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
    patch_vp_metric: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vmt: string;
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchMetric"];
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
                    "application/json": components["schemas"]["MetricsView"];
                };
            };
        };
    };
    decide_pack_offer: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
                vpo: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PackDecide"];
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
                    "application/json": components["schemas"]["VPDoc"];
                };
            };
            /** @description 잡 시작(jobs SSE 로 진행) */
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
    get_vp_package: {
        parameters: {
            query?: {
                proposal_type?: ("standard" | "quickwin" | "solution") | null;
            };
            header?: never;
            path: {
                vp_id: string;
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
    get_vp_packages: {
        parameters: {
            query?: {
                estimates_as_notes?: boolean;
                selected?: ("standard" | "quickwin" | "solution") | null;
            };
            header?: never;
            path: {
                vp_id: string;
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
                    "application/json": components["schemas"]["PackageSet"];
                };
            };
        };
    };
    get_vp_plan: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
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
                    "application/json": components["schemas"]["Plan"];
                };
            };
        };
    };
    patch_vp_plan: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchPlan"];
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
                    "application/json": components["schemas"]["Plan"];
                };
            };
        };
    };
    refresh_plan: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
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
                    "application/json": components["schemas"]["Plan"];
                };
            };
        };
    };
    get_proposal_handoff: {
        parameters: {
            query?: {
                section?: string | null;
                type?: ("standard" | "quickwin" | "solution") | null;
            };
            header?: never;
            path: {
                vp_id: string;
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
    answer_questions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AnswerQuestions"];
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
    add_vp_sheet: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AddSheet"];
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
    patch_vp_sheet: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sh: string;
                vp_id: string;
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
                    "application/json": components["schemas"]["Sheet"];
                };
            };
        };
    };
    choose_sheet_layout: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sh: string;
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChooseLayout"];
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
            /** @description 잡 시작(jobs SSE 로 진행) */
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
    get_layout_options: {
        parameters: {
            query?: {
                pillars?: number | null;
                request_id?: string | null;
            };
            header?: never;
            path: {
                sh: string;
                vp_id: string;
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
                    "application/json": components["schemas"]["LayoutOptions"];
                };
            };
        };
    };
    get_sheet_metrics: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sh: string;
                vp_id: string;
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
                    "application/json": components["schemas"]["MetricsView"];
                };
            };
        };
    };
    apply_sheet_metrics: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sh: string;
                vp_id: string;
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
                    "application/json": components["schemas"]["VPDoc"];
                };
            };
            /** @description 잡 시작(jobs SSE 로 진행) */
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
    list_source_candidates: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
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
                    "application/json": components["schemas"]["SourceCandidates"];
                };
            };
        };
    };
    put_vp_sources: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PutSources"];
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
                    "application/json": components["schemas"]["VPDoc"];
                };
            };
        };
    };
    list_vp_versions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
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
    save_vp_version: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vp_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["SavePoint"] | null;
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
                    "application/json": components["schemas"]["VPDoc"];
                };
            };
        };
    };
    restore_vp_version: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                n: number;
                vp_id: string;
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
                    "application/json": components["schemas"]["VPDoc"];
                };
            };
        };
    };
}
