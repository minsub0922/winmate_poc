// 자동 생성 — 직접 고치지 말 것. 원본: contracts/birdseye.json (make contracts)
export interface paths {
    "/v1/birdseyes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 조감도 작업 목록(BE0 · 시나리오 SC1 · SC1B) */
        get: operations["list_birdseyes"];
        put?: never;
        /** 새 조감도 작업(BE1 · 시나리오 · 이미지 참조) */
        post: operations["create_birdseye"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Birdseye */
        get: operations["get_birdseye"];
        put?: never;
        post?: never;
        /** 지우기(소프트 삭제) */
        delete: operations["delete_birdseye"];
        options?: never;
        head?: never;
        /** 칸 값 · 톤 · 시점 · 존 레이아웃 · 공유(409 if_version) */
        patch: operations["patch_birdseye"];
        trace?: never;
    };
    "/v1/birdseyes/{be_id}:clone": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 복제해서 새 시안(→ BE4) */
        post: operations["clone_birdseye"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}:save": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 버전 저장(「저장했어요 · v{n}」) */
        post: operations["save_birdseye"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/attachments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** BE1 파일 첨부 분류(R1): PDF → 도면, 이미지 → i2t 「평면도인가?」 → 도면/현장 사진 · 415 */
        post: operations["attach"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/cuts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 컷 목록(진행률 · 대기 순번) */
        get: operations["list_cuts"];
        put?: never;
        /** 컷 만들기(컷마다 잡, 작업당 순차 · 같은 컷은 건너뜀) */
        post: operations["create_cuts"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/export-options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** BE6 이미지 목록 · 파일 이름 · 제안서 매핑 */
        get: operations["export_options"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/exports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** ZIP(이미지 + 수량표.xlsx + sources.json) · PDF */
        post: operations["create_export"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/furniture": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Furniture */
        get: operations["get_furniture"];
        /** 선택 · 수량 · 직접 입력(카탈로그 일치 → 없으면 치수 추정) · 가구 없이 */
        put: operations["put_furniture"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/furniture:recommend": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 가구 추천(다음 4개 · 보인 것 제외) */
        post: operations["recommend_furniture"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/handoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 제안서 · 시나리오용 묶음(§8) */
        get: operations["handoff"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/layout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 배치안(레이아웃 + 평면 + 표시 겹) */
        get: operations["get_layout"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/layout-sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** BE4E 편집 세션 */
        post: operations["create_session"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/layout:generate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 배치 의도(LLM) + 엔진 + 자동 조정 → 새 레이아웃(→ BE4) */
        post: operations["generate_layout"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/layout:nl-edit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 배치 수정 요청 · 말로 수정(LLM → 연산 → 엔진) */
        post: operations["nl_edit_layout"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/layout:validate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 동기 검증(저장 안 함, ≤ 200ms) */
        post: operations["validate_layout"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/photos": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Photos */
        get: operations["list_photos"];
        put?: never;
        /** 현장 사진 올리기 · 다시 찍기(replace) · 천장 사진 · 415 FILE_TYPE_UNSUPPORTED */
        post: operations["add_photo"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/photos/{photo_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Photo */
        delete: operations["delete_photo"];
        options?: never;
        head?: never;
        /** 「그대로 사용」 */
        patch: operations["patch_photo"];
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/photos/{photo_id}:recognize": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 「다시 인식」 */
        post: operations["recognize_photo"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/plans": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Plans */
        get: operations["list_plans"];
        put?: never;
        /** 도면 올리기 → 인식 잡 · 415 */
        post: operations["add_plan"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/plans/{plan_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Plan */
        get: operations["get_plan"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/plans/{plan_id}:recognize": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 다시 인식(같은 파일) · 쪽 바꾸기 */
        post: operations["recognize_plan"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/products": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Products */
        get: operations["get_products"];
        /** Put Products */
        put: operations["put_products"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/proposal-handoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** ProposalHandoff v1(10-proposal §8 · B1) — BV-A · BV-B · ZP · SM-B */
        get: operations["proposal_handoff"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/quantities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 제품 수량표(배치안 기준) */
        get: operations["quantities"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/result:edit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** BE5 수정 요청(R8: 렌더 수정 · 배치 수정 → 재렌더 · 시점 컷) */
        post: operations["result_edit"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/space": {
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
    "/v1/birdseyes/{be_id}/space:analyze": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 설명 · 도면 · 사진 → 공간 모델(→ BE2) */
        post: operations["analyze_space"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/space:nl-edit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 말로 고치기(LLM 공간 연산) */
        post: operations["nl_edit_space"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/space/answers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 되묻기 답 · 치수 보정 */
        post: operations["answer_space"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/space/facts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 사진에 없는 정보 → 사실 칩 · 모델 */
        post: operations["add_facts"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/upload-tokens": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 휴대폰 QR 업로드 토큰(30분) */
        post: operations["create_upload_token"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/usages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 쓰인 곳 등록(제안서 · 시나리오) */
        post: operations["add_usage"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/usages/{service_name}/{ref}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Remove Usage */
        delete: operations["remove_usage"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/version": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 변경 감지(시나리오 · 가벼움) */
        get: operations["get_version"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/versions": {
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
    "/v1/birdseyes/{be_id}/versions/{n}/restore": {
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
    "/v1/birdseyes/{be_id}/zones": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Zones */
        get: operations["get_zones"];
        put?: never;
        /** 빈 곳 클릭 · W 제안 수락 */
        post: operations["add_zone"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/zones:auto": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 존 포인트 자동(군집 · 투영 · 문구) */
        post: operations["zones_auto"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/zones:renumber-by-path": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 동선 순서로 번호 */
        post: operations["renumber_zones"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseyes/{be_id}/zones:rewrite": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 포인트 문구 수정 요청(선택 존 또는 전체) */
        post: operations["rewrite_zones"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/catalog": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 가구 카탈로그 · 인테리어 톤 · 조명(화면 칩) */
        get: operations["catalog"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cuts/{cut_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Cut */
        get: operations["get_cut"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** 주 컷 지정 */
        patch: operations["patch_cut"];
        trace?: never;
    };
    "/v1/cuts/{cut_id}:cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 대기 컷은 즉시 빼기, 진행 컷은 초안 저장 후 중지 */
        post: operations["cancel_cut"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/exports/{export_id}": {
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
    "/v1/layout-sessions/{session_id}": {
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
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/layout-sessions/{session_id}:autofix": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 경고 모두 자동 조정 */
        post: operations["session_autofix"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/layout-sessions/{session_id}:commit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 수정 적용 → 새 레이아웃 버전 */
        post: operations["session_commit"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/layout-sessions/{session_id}:discard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 취소(세션 버림) */
        post: operations["session_discard"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/layout-sessions/{session_id}/ops": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 연산 · 되돌리기 · 다시 실행 */
        post: operations["session_ops"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/layout-sessions/{session_id}/warnings/{warning_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 경고 수정안 · 무시 · 메모 · 전원 위치 추가 */
        post: operations["warning_action"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/layouts/{be_id}/proposal-handoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 별칭(10-proposal §8.14 B1 경로) — /v1/birdseyes/{id}/proposal-handoff 와 같음 */
        get: operations["proposal_handoff_alias"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/product-search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 제품 검색(kb 결과를 표시용으로) */
        get: operations["product_search"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/upload-tokens/{token}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 모바일 업로드 페이지 정보 · 404 */
        get: operations["get_upload_token"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/upload-tokens/{token}/photos": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 휴대폰에서 올린 사진(토큰 인증) · 410 TOKEN_EXPIRED */
        post: operations["upload_token_photo"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/upload-tokens/{token}/principal": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 게이트웨이 전용 — 업로드 토큰의 주인(로그인 없는 휴대폰 업로드 통과용) */
        get: operations["get_upload_token_principal"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/zones/{zone_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Zone */
        delete: operations["delete_zone"];
        options?: never;
        head?: never;
        /** Patch Zone */
        patch: operations["patch_zone"];
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** Anchor */
        Anchor: {
            /**
             * Label
             * @default
             */
            label: string;
            /** Target */
            target?: string | null;
            /**
             * Type
             * @description wall · window · column · faces · near · entrance · area · free
             */
            type: string;
        };
        /** AnswerIn */
        AnswerIn: {
            /** Choice */
            choice?: ("annotated" | "computed" | "manual") | null;
            /** Dim Id */
            dim_id?: string | null;
            /** Manual M */
            manual_m?: number | null;
            /** Option */
            option?: ("emergency" | "backoffice" | "wall" | "main" | "normal") | null;
            /** Question Id */
            question_id?: string | null;
        };
        /** Assumption */
        Assumption: {
            /**
             * Action
             * @description 되돌아갈 화면(BE1D · BE1P)
             */
            action?: string | null;
            /**
             * Kind
             * @description dims_missing · door_unknown · dim_default · area_estimate · ceiling_estimate · photo_estimate
             */
            kind: string;
            /** Ref */
            ref?: string | null;
            /** Text Ko */
            text_ko: string;
        };
        /** AttachIn */
        AttachIn: {
            /** File Ids */
            file_ids: string[];
        };
        /** AttachItem */
        AttachItem: {
            /** File Id */
            file_id: string;
            /** Job Id */
            job_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "plan" | "photo";
            /**
             * Name
             * @default
             */
            name: string;
            /** Photo Id */
            photo_id?: string | null;
            /** Plan Id */
            plan_id?: string | null;
        };
        /** AttachOut */
        AttachOut: {
            /** Items */
            items: components["schemas"]["AttachItem"][];
            /**
             * Route
             * @description 도면이 있으면 BE1D(먼저), 사진만 있으면 BE1P
             */
            route: string;
        };
        /** Birdseye */
        Birdseye: {
            /** Analyzing Job Id */
            analyzing_job_id?: string | null;
            /** Area Input Pyeong */
            area_input_pyeong?: number | null;
            /** Ceiling Input M */
            ceiling_input_m?: number | null;
            /** Check Route */
            check_route?: string | null;
            /** Cloned From */
            cloned_from?: string | null;
            /** Created At */
            created_at: string;
            /** Customer Name */
            customer_name?: string | null;
            /**
             * Default View
             * @default aerial45
             * @enum {string}
             */
            default_view: "aerial45" | "entrance";
            /**
             * Description
             * @default
             */
            description: string;
            /** Id */
            id: string;
            inputs?: components["schemas"]["Inputs"];
            /**
             * Layout Version
             * @default 0
             */
            layout_version: number;
            origin?: components["schemas"]["Origin"] | null;
            /** Owner */
            owner: string;
            /**
             * Owner Name
             * @default
             */
            owner_name: string;
            /** Prefill Products */
            prefill_products?: components["schemas"]["PrefillProduct"][];
            /** Primary Cut Id */
            primary_cut_id?: string | null;
            /** Project Id */
            project_id?: string | null;
            reference_image?: components["schemas"]["ReferenceImage"] | null;
            /**
             * Rev
             * @description 문서 수정 번호 — PATCH if_version 비교
             * @default 1
             */
            rev: number;
            /** Route */
            route: string;
            /** Shared Label */
            shared_label?: string | null;
            /**
             * Shared Scope
             * @default private
             * @enum {string}
             */
            shared_scope: "private" | "team";
            /**
             * Space Chip
             * @default store_lobby
             * @enum {string}
             */
            space_chip: "store_lobby" | "meeting_office" | "classroom" | "hospital_waiting" | "hotel_room" | "control_room";
            /**
             * Space Label
             * @default
             */
            space_label: string;
            /** Space Types */
            space_types?: string[];
            /**
             * Status
             * @default in_progress
             * @enum {string}
             */
            status: "in_progress" | "needs_check" | "done" | "failed";
            /**
             * Status Reason
             * @description 확인 필요 사유 줄(「사진 1장 다시 찍기 · 1/5 공간 입력」)
             */
            status_reason?: string | null;
            /**
             * Step
             * @default 1
             */
            step: number;
            /** Title */
            title: string;
            /**
             * Tone
             * @default warm_wood
             * @enum {string}
             */
            tone: "warm_wood" | "modern_white" | "dark_metal";
            /** Updated At */
            updated_at: string;
            /**
             * Version
             * @description 저장 버전(「저장」 v{n} · 내보내기 파일 이름)
             * @default 1
             */
            version: number;
            /**
             * Zone Layout
             * @default ZP-A
             * @enum {string}
             */
            zone_layout: "ZP-A" | "ZP-B" | "ZP-C";
        };
        /** BirdseyeCreate */
        BirdseyeCreate: {
            /** Area Pyeong */
            area_pyeong?: number | null;
            /** Ceiling M */
            ceiling_m?: number | null;
            /** Customer Name */
            customer_name?: string | null;
            /** Description */
            description?: string | null;
            origin?: components["schemas"]["Origin"] | null;
            prefill?: components["schemas"]["Prefill"] | null;
            /** Project Id */
            project_id?: string | null;
            /** Space Chip */
            space_chip?: ("store_lobby" | "meeting_office" | "classroom" | "hospital_waiting" | "hotel_room" | "control_room") | null;
            /** Title */
            title?: string | null;
        };
        /** BirdseyeList */
        BirdseyeList: {
            counts: components["schemas"]["Counts"];
            /** Items */
            items: components["schemas"]["BirdseyeRow"][];
            /** Next Cursor */
            next_cursor?: string | null;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** BirdseyePatch */
        BirdseyePatch: {
            /** Area Pyeong */
            area_pyeong?: number | null;
            /** Ceiling M */
            ceiling_m?: number | null;
            /**
             * Clear Area
             * @description 면적 칸 비우기
             * @default false
             */
            clear_area: boolean;
            /**
             * Clear Ceiling
             * @description 층고 칸 비우기
             * @default false
             */
            clear_ceiling: boolean;
            /** Customer Name */
            customer_name?: string | null;
            /** Default View */
            default_view?: ("aerial45" | "entrance") | null;
            /** Description */
            description?: string | null;
            /**
             * If Version
             * @description rev 와 다르면 409 VERSION_CONFLICT
             */
            if_version?: number | null;
            /** Shared Label */
            shared_label?: string | null;
            /** Shared Scope */
            shared_scope?: ("private" | "team") | null;
            /** Space Chip */
            space_chip?: ("store_lobby" | "meeting_office" | "classroom" | "hospital_waiting" | "hotel_room" | "control_room") | null;
            /** Step */
            step?: number | null;
            /** Title */
            title?: string | null;
            /** Tone */
            tone?: ("warm_wood" | "modern_white" | "dark_metal") | null;
            /** Zone Layout */
            zone_layout?: ("ZP-A" | "ZP-B" | "ZP-C") | null;
        };
        /** BirdseyeRow */
        BirdseyeRow: {
            action: components["schemas"]["RowAction"];
            /** Created At */
            created_at: string;
            /** Customer Name */
            customer_name?: string | null;
            /**
             * Done
             * @default false
             */
            done: boolean;
            /**
             * Furniture Kinds
             * @default 0
             */
            furniture_kinds: number;
            /** Id */
            id: string;
            /**
             * Input Chips
             * @description 「설명」 「도면」 「사진 {n}장」
             */
            input_chips?: string[];
            /**
             * Layout Version
             * @default 0
             */
            layout_version: number;
            /** Owner */
            owner: string;
            /**
             * Owner Name
             * @default
             */
            owner_name: string;
            /** Primary Cut Url */
            primary_cut_url?: string | null;
            /**
             * Products Line
             * @description 「{제품 요약} · 가구 {k}종」
             * @default
             */
            products_line: string;
            /** Route */
            route: string;
            running?: components["schemas"]["RunningCut"] | null;
            /** Shared Label */
            shared_label?: string | null;
            /**
             * Shared Scope
             * @default private
             * @enum {string}
             */
            shared_scope: "private" | "team";
            /**
             * Space Label
             * @default
             */
            space_label: string;
            /**
             * Status
             * @enum {string}
             */
            status: "in_progress" | "needs_check" | "done" | "failed";
            /**
             * Status Line
             * @description 「시점 3 · 존 포인트 4」 · 「배치 · 인테리어 컨펌」 · 사유 줄
             * @default
             */
            status_line: string;
            /**
             * Status Title
             * @description 「완료」 · 「4/5」 · 「확인 필요」 · 「실패」
             */
            status_title: string;
            /** Step */
            step: number;
            /** Step Label */
            step_label: string;
            /**
             * Subtitle
             * @description 「{고객사} · {공간 라벨}」
             */
            subtitle: string;
            /**
             * Team Meta
             * @description 「{팀} 공유 · 시점 {v} · 존 포인트 {z}」
             * @default
             */
            team_meta: string;
            /** Thumb Url */
            thumb_url?: string | null;
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
            /** Usages */
            usages?: components["schemas"]["UsageRef"][];
            /**
             * Version
             * @description 저장 버전
             * @default 1
             */
            version: number;
            /**
             * Views Count
             * @default 0
             */
            views_count: number;
            /**
             * Zone Count
             * @description = zones_count(시나리오 SC1 · SC1B 「존 {n}」)
             * @default 0
             */
            zone_count: number;
            /**
             * Zones Count
             * @default 0
             */
            zones_count: number;
        };
        /** Bottleneck */
        Bottleneck: {
            /** A */
            a: string;
            /** B */
            b: string;
            /** Pos */
            pos: number[];
            /** Width */
            width: number;
        };
        /** Camera */
        Camera: {
            /**
             * Fov Deg
             * @default 40
             */
            fov_deg: number;
            /**
             * Ortho
             * @default false
             */
            ortho: boolean;
            /** Ortho W */
            ortho_w?: number | null;
            /** Pos */
            pos: number[];
            /** Target */
            target: number[];
        };
        /** CatalogOut */
        CatalogOut: {
            /** Furniture */
            furniture: components["schemas"]["FurnitureCatalogItem"][];
            /** Lights */
            lights: {
                [key: string]: unknown;
            }[];
            /** Tones */
            tones: {
                [key: string]: unknown;
            }[];
        };
        /** CeilingH */
        CeilingH: {
            /**
             * Estimated
             * @default true
             */
            estimated: boolean;
            /** Value */
            value: number;
        };
        /** Chip */
        Chip: {
            /**
             * Estimated
             * @default false
             */
            estimated: boolean;
            /**
             * Kind
             * @default feature
             * @enum {string}
             */
            kind: "area" | "feature" | "column" | "fact" | "estimate" | "file";
            /** Label */
            label: string;
        };
        /** CloneIn */
        CloneIn: {
            /** Title */
            title?: string | null;
        };
        /** CloneOut */
        CloneOut: {
            /** Id */
            id: string;
            /** Route */
            route: string;
        };
        /** Column */
        Column: {
            /** Center */
            center: number[];
            /**
             * D
             * @default 0.6
             */
            d: number;
            /** Id */
            id: string;
            /**
             * Label
             * @default
             */
            label: string;
            /**
             * W
             * @default 0.6
             */
            w: number;
        };
        /** CommitOut */
        CommitOut: {
            /**
             * Changes Count
             * @default 0
             */
            changes_count: number;
            /** Layout Version */
            layout_version: number;
        };
        /** Core */
        Core: {
            /** Id */
            id: string;
            /**
             * Kinds
             * @description ev · stairs · toilet · shaft
             */
            kinds?: string[];
            /** Polygon */
            polygon: number[][];
        };
        /** Counts */
        Counts: {
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
             * In Progress
             * @default 0
             */
            in_progress: number;
            /**
             * Needs Check
             * @default 0
             */
            needs_check: number;
        };
        /** Cut */
        Cut: {
            /**
             * Auto Queued
             * @default false
             */
            auto_queued: boolean;
            /**
             * Badge
             * @description 「초안 렌더」
             */
            badge?: string | null;
            /**
             * Before
             * @default false
             */
            before: boolean;
            /** Birdseye Id */
            birdseye_id: string;
            /** Created At */
            created_at: string;
            /**
             * Display Url
             * @description 화면 표시용(FHD 렌디션 — 없으면 image_url). 내려받기는 image_url(원본)
             */
            display_url?: string | null;
            /**
             * Draft File Id
             * @description draft_v0(마감재 적용 전)
             */
            draft_file_id?: string | null;
            /** Draft Url */
            draft_url?: string | null;
            /** Draft V1 File Id */
            draft_v1_file_id?: string | null;
            /**
             * Edit Pending Text
             * @description 진행 중 요청을 편집으로 못 반영했을 때 수정 요청 칸에 채울 글
             */
            edit_pending_text?: string | null;
            /** Error */
            error?: string | null;
            /** Eta S */
            eta_s?: number | null;
            /** Finished At */
            finished_at?: string | null;
            /** Id */
            id: string;
            /** Image Id */
            image_id?: string | null;
            /** Image Url */
            image_url?: string | null;
            /**
             * Is Primary
             * @default false
             */
            is_primary: boolean;
            /** Job Id */
            job_id?: string | null;
            /**
             * Label
             * @description 「조감 45° · 야간」 · 「도입 전 · 조감 45° (비교용)」
             */
            label: string;
            /** Layout Version */
            layout_version: number;
            /**
             * Light
             * @default day
             * @enum {string}
             */
            light: "day" | "evening" | "night";
            /** Notice */
            notice?: string | null;
            /**
             * Progress
             * @default 0
             */
            progress: number;
            /** Qc */
            qc?: {
                [key: string]: unknown;
            };
            /** Queue Pos */
            queue_pos?: number | null;
            /** Render Id */
            render_id?: string | null;
            /**
             * Render Path
             * @description render:ref|edit|text|draft_only
             */
            render_path?: string | null;
            /** Renditions */
            renditions?: {
                [key: string]: unknown;
            }[];
            /**
             * Resolution
             * @default 3840×2160
             */
            resolution: string;
            /** Stage */
            stage?: string | null;
            /**
             * Stale
             * @default false
             */
            stale: boolean;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "draft" | "done" | "check" | "failed" | "canceled";
            /** Steps */
            steps?: components["schemas"]["CutStep"][];
            /**
             * Thumb Label
             * @description 썸네일 라벨(주 시점과 다르면 시점, 조명만 다르면 조명)
             * @default
             */
            thumb_label: string;
            /** Thumb Url */
            thumb_url?: string | null;
            /**
             * Tone
             * @default warm_wood
             * @enum {string}
             */
            tone: "warm_wood" | "modern_white" | "dark_metal";
            /** Version Id */
            version_id?: string | null;
            view: components["schemas"]["CutView"];
        };
        /** CutPatch */
        CutPatch: {
            /**
             * Is Primary
             * @default true
             */
            is_primary: boolean;
        };
        /** CutsAccepted */
        CutsAccepted: {
            /** Cut Ids */
            cut_ids: string[];
            /** Job Id */
            job_id?: string | null;
            /** Job Ids */
            job_ids: string[];
            /** Route */
            route?: string | null;
            /**
             * Skipped
             * @default 0
             */
            skipped: number;
        };
        /** CutsCreate */
        CutsCreate: {
            /**
             * Auto Extra
             * @description 첫 렌더 때 야간 · 도입 전 컷 자동 예약(§7.8)
             * @default false
             */
            auto_extra: boolean;
            /**
             * Before
             * @default false
             */
            before: boolean;
            /** Lights */
            lights?: ("day" | "evening" | "night")[];
            /**
             * Primary
             * @description BE4 「이 배치로 3D 생성」 — 주 컷
             * @default false
             */
            primary: boolean;
            /** Tone */
            tone?: ("warm_wood" | "modern_white" | "dark_metal") | null;
            /** Views */
            views: components["schemas"]["ViewSpec"][];
        };
        /** CutStep */
        CutStep: {
            /** Label */
            label: string;
            /**
             * Note
             * @default
             */
            note: string;
            /**
             * Stage
             * @enum {string}
             */
            stage: "structure" | "products" | "furniture" | "render" | "qc";
            /**
             * State
             * @default wait
             * @enum {string}
             */
            state: "done" | "run" | "wait";
        };
        /** CutView */
        CutView: {
            camera?: components["schemas"]["Camera"] | null;
            /** Custom Text */
            custom_text?: string | null;
            /** Label */
            label: string;
            /**
             * Meta Path
             * @description camera:rules · camera:llm
             */
            meta_path?: string | null;
            /**
             * Preset
             * @enum {string}
             */
            preset: "aerial45" | "entrance" | "product_front" | "top" | "custom";
            /** Target Item Id */
            target_item_id?: string | null;
        };
        /** Dim */
        Dim: {
            /** Annotated M */
            annotated_m?: number | null;
            /**
             * Answered
             * @default false
             */
            answered: boolean;
            /**
             * Asked
             * @description 표기 · 환산 차가 1% 를 넘어 되묻는 항목
             * @default false
             */
            asked: boolean;
            /**
             * Choice
             * @default annotated
             * @enum {string}
             */
            choice: "annotated" | "computed" | "manual";
            /** Computed M */
            computed_m?: number | null;
            /** Id */
            id: string;
            /** Label */
            label: string;
            /** Manual M */
            manual_m?: number | null;
            /** Wall Id */
            wall_id?: string | null;
        };
        /** Dims3 */
        Dims3: {
            /** D */
            d: number;
            /** H */
            h: number;
            /** W */
            w: number;
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
        /** ExportCreate */
        ExportCreate: {
            /** Filename */
            filename?: string | null;
            /**
             * Format
             * @default png
             * @enum {string}
             */
            format: "png" | "jpg" | "pdf";
            /**
             * Include Furniture
             * @default true
             */
            include_furniture: boolean;
            /**
             * Items
             * @description 없으면 기본 선택(BE6), [] 이면 수량표만
             */
            items?: components["schemas"]["ExportItemRef"][] | null;
            /**
             * Size
             * @default original
             * @enum {string}
             */
            size: "original" | "fhd";
        };
        /** ExportImageOption */
        ExportImageOption: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "cut" | "before_after" | "zones_callout";
            /** Name */
            name: string;
            /** Ref */
            ref?: string | null;
            /**
             * Selected
             * @default false
             */
            selected: boolean;
            /** Sub */
            sub: string;
            /** Thumb Url */
            thumb_url?: string | null;
        };
        /** ExportItemRef */
        ExportItemRef: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "cut" | "before_after" | "zones_callout";
            /** Ref */
            ref?: string | null;
        };
        /** ExportOptions */
        ExportOptions: {
            /** Family Ids */
            family_ids?: string[];
            /** Filename Default */
            filename_default: string;
            /** Images */
            images: components["schemas"]["ExportImageOption"][];
            /** Mapping */
            mapping: components["schemas"]["SheetMapRow"][];
            /**
             * Products Count
             * @default 0
             */
            products_count: number;
            /** Spec Products */
            spec_products?: components["schemas"]["ProductPick"][];
            /**
             * Title
             * @default
             */
            title: string;
            /**
             * Version
             * @default 1
             */
            version: number;
            /**
             * Zones Count
             * @default 0
             */
            zones_count: number;
        };
        /** ExportRecord */
        ExportRecord: {
            /** Birdseye Id */
            birdseye_id: string;
            /** Created At */
            created_at: string;
            /** Download Url */
            download_url?: string | null;
            /** Error */
            error?: string | null;
            /** File Id */
            file_id?: string | null;
            /** Filename */
            filename: string;
            /** Format */
            format: string;
            /** Id */
            id: string;
            /**
             * Include Furniture
             * @default true
             */
            include_furniture: boolean;
            /** Items */
            items?: components["schemas"]["ExportItemRef"][];
            /** Job Id */
            job_id?: string | null;
            /** Size */
            size: string;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "done" | "failed";
            /** Url */
            url?: string | null;
        };
        /** FactsOut */
        FactsOut: {
            /** Facts */
            facts: string[];
            model: components["schemas"]["SpaceModel"];
        };
        /** Feature */
        Feature: {
            /**
             * Cap Label
             * @description W 권장 문구(「고휘도 권장」)
             */
            cap_label?: string | null;
            /** Count */
            count?: number | null;
            /**
             * Hint Cap
             * @description KB C1 역량 id(cap_sunlight_readable …)
             */
            hint_cap?: string | null;
            /**
             * Kind
             * @description storefront_window · columns · glass_wall · stage · counter · …
             */
            kind: string;
            /** Label */
            label: string;
        };
        /** FurnitureCard */
        FurnitureCard: {
            /** Code */
            code: string;
            /** Item Id */
            item_id?: string | null;
            /** Name */
            name: string;
            /**
             * Qty
             * @default 1
             */
            qty: number;
            /** Rank */
            rank: number;
            /** Reason */
            reason: string;
            /** Rows */
            rows?: number | null;
            /**
             * Selected
             * @default false
             */
            selected: boolean;
        };
        /** FurnitureCatalogItem */
        FurnitureCatalogItem: {
            /** Aliases */
            aliases?: string[];
            /** Code */
            code: string;
            /** D */
            d: number;
            /** H */
            h: number;
            /** Name */
            name: string;
            /** Short */
            short: string;
            /** W */
            w: number;
        };
        /** FurnitureDetailRow */
        FurnitureDetailRow: {
            /** At */
            at: string;
            /**
             * Dims
             * @default
             */
            dims: string;
            /**
             * Estimated
             * @default false
             */
            estimated: boolean;
            /** Name */
            name: string;
            /** Qty */
            qty: number;
        };
        /** FurnitureItem */
        FurnitureItem: {
            /** Birdseye Id */
            birdseye_id: string;
            /** Catalog Code */
            catalog_code?: string | null;
            /**
             * Chip Label
             * @description 「기둥 랩핑 프레임 ×2」 · 「안내 로봇 · 치수 추정」
             * @default
             */
            chip_label: string;
            /**
             * Dims Estimated
             * @default false
             */
            dims_estimated: boolean;
            dims_m: components["schemas"]["Dims3"];
            /** Id */
            id: string;
            /** Name */
            name: string;
            /**
             * Qty
             * @default 1
             */
            qty: number;
            /**
             * Reason
             * @default
             */
            reason: string;
            /** Rec Rank */
            rec_rank?: number | null;
            /** Rows */
            rows?: number | null;
            /**
             * Selected
             * @default true
             */
            selected: boolean;
            /**
             * Short
             * @default
             */
            short: string;
            /**
             * Source
             * @default recommended
             * @enum {string}
             */
            source: "recommended" | "user" | "custom";
            /**
             * Tiny
             * @default
             */
            tiny: string;
        };
        /** FurniturePick */
        FurniturePick: {
            /** Catalog Code */
            catalog_code?: string | null;
            /** Id */
            id?: string | null;
            /** Name */
            name?: string | null;
            /** Qty */
            qty?: number | null;
            /** Rows */
            rows?: number | null;
            /**
             * Selected
             * @default true
             */
            selected: boolean;
        };
        /** FurniturePut */
        FurniturePut: {
            /** Items */
            items?: components["schemas"]["FurniturePick"][];
            /**
             * None
             * @default false
             */
            none: boolean;
            /**
             * Replace
             * @description true 면 목록을 통째로(빠진 항목은 선택 해제), false 면 더하기
             * @default true
             */
            replace: boolean;
        };
        /** FurnitureRecommendIn */
        FurnitureRecommendIn: {
            /** Exclude */
            exclude?: string[];
        };
        /** FurnitureRow */
        FurnitureRow: {
            /**
             * At
             * @description 「라운지 · 관람 · 안내」
             */
            at: string;
            /**
             * Label
             * @description 「가구 4종 (참고)」
             */
            label: string;
            /** Qty */
            qty: number;
        };
        /** FurnitureView */
        FurnitureView: {
            /** Cards */
            cards?: components["schemas"]["FurnitureCard"][];
            /**
             * Echo
             * @default
             */
            echo: string;
            /** Job Id */
            job_id?: string | null;
            /**
             * More Available
             * @default true
             */
            more_available: boolean;
            /**
             * None
             * @description 가구 없이 진행을 골랐다
             * @default false
             */
            none: boolean;
            /**
             * Running
             * @default false
             */
            running: boolean;
            /** Selected */
            selected?: components["schemas"]["FurnitureItem"][];
            /** Shown Codes */
            shown_codes?: string[];
            /**
             * W Message
             * @default
             */
            w_message: string;
        };
        /** Handoff */
        Handoff: {
            /** Birdseye Id */
            birdseye_id: string;
            /** Comparisons */
            comparisons?: components["schemas"]["HandoffComparison"][];
            /** Customer */
            customer?: string | null;
            /** Cuts */
            cuts?: components["schemas"]["HandoffCut"][];
            /** Furniture */
            furniture?: components["schemas"]["FurnitureDetailRow"][];
            /** Layout Version */
            layout_version: number;
            /** Memos */
            memos?: string[];
            plan_preview?: components["schemas"]["PlanPreview"] | null;
            /** Products */
            products?: components["schemas"]["ZoneProduct"][];
            /** Project Id */
            project_id?: string | null;
            /** Quantities */
            quantities?: components["schemas"]["QuantityRow"][];
            /** Route */
            route: string;
            /** Sheet Map */
            sheet_map?: components["schemas"]["SheetMapRow"][];
            space: components["schemas"]["HandoffSpace"];
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
            /** Version */
            version: number;
            zones?: components["schemas"]["HandoffZones"];
        };
        /** HandoffComparison */
        HandoffComparison: {
            /** Composite File Id */
            composite_file_id?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "before_after" | "day_night";
            /** Left */
            left: string;
            /** Right */
            right: string;
        };
        /** HandoffCut */
        HandoffCut: {
            /**
             * Before
             * @default false
             */
            before: boolean;
            /** Cut Id */
            cut_id: string;
            /**
             * Draft Only
             * @default false
             */
            draft_only: boolean;
            /** File Id */
            file_id?: string | null;
            /** Generation */
            generation?: {
                [key: string]: unknown;
            };
            /** Image Id */
            image_id?: string | null;
            /** Image Version Id */
            image_version_id?: string | null;
            /**
             * Is Primary
             * @default false
             */
            is_primary: boolean;
            /** Label */
            label: string;
            /**
             * Light
             * @enum {string}
             */
            light: "day" | "evening" | "night";
            /** Renditions */
            renditions?: {
                [key: string]: unknown;
            }[];
            /**
             * Stale
             * @default false
             */
            stale: boolean;
            /** Url */
            url?: string | null;
            /** View */
            view: string;
        };
        /** HandoffSpace */
        HandoffSpace: {
            /** Area M2 */
            area_m2?: number | null;
            /** Area Pyeong */
            area_pyeong?: number | null;
            /** Ceiling H M */
            ceiling_h_m?: number | null;
            /**
             * Estimated
             * @default true
             */
            estimated: boolean;
            /** Features */
            features?: components["schemas"]["Feature"][];
            /**
             * Label
             * @default
             */
            label: string;
            /** Space Types */
            space_types?: string[];
            /**
             * Summary
             * @description 「120평 · 층고 4.5m」
             * @default
             */
            summary: string;
        };
        /** HandoffZonePoint */
        HandoffZonePoint: {
            /** Furniture */
            furniture?: components["schemas"]["ZoneFurniture"][];
            /**
             * Id
             * @description bez_…
             */
            id: string;
            /**
             * Kind
             * @default product
             * @enum {string}
             */
            kind: "product" | "furniture" | "empty";
            /** Links */
            links?: components["schemas"]["ZoneLink"][];
            /** N */
            n: number;
            /** Name */
            name: string;
            /** Path Order */
            path_order?: number | null;
            /** Products */
            products?: components["schemas"]["ZoneProduct"][];
            /**
             * Short Name
             * @default
             */
            short_name: string;
            /**
             * Subtitle
             * @description SC1B 부제 「OH55C ×3 · 거리에서 보이는 첫인상」
             * @default
             */
            subtitle: string;
            /** Text */
            text: string;
            /** U */
            u?: number | null;
            /** V */
            v?: number | null;
            /** X */
            x?: number | null;
            /** Y */
            y?: number | null;
            /** Zone Id */
            zone_id: string;
        };
        /** HandoffZones */
        HandoffZones: {
            /** Cut Id */
            cut_id?: string | null;
            /**
             * Layout
             * @default ZP-A
             * @enum {string}
             */
            layout: "ZP-A" | "ZP-B" | "ZP-C";
            /** Points */
            points?: components["schemas"]["HandoffZonePoint"][];
        };
        /** InputFile */
        InputFile: {
            /** File Id */
            file_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "plan" | "photo";
            /** Name */
            name: string;
            /** Route */
            route?: string | null;
        };
        /** Inputs */
        Inputs: {
            /**
             * Description
             * @default false
             */
            description: boolean;
            /**
             * Photo Count
             * @default 0
             */
            photo_count: number;
            /** Plan File Ids */
            plan_file_ids?: string[];
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
        /** Layout */
        Layout: {
            /** Assumptions */
            assumptions?: components["schemas"]["Assumption"][];
            /** Created At */
            created_at?: string | null;
            /**
             * Created By
             * @default engine
             * @enum {string}
             */
            created_by: "engine" | "user" | "nl_edit" | "clone" | "restore";
            /**
             * Engine Version
             * @default be-engine/1
             */
            engine_version: string;
            /** Groups */
            groups?: components["schemas"]["LayoutGroup"][];
            /** Items */
            items?: components["schemas"]["LayoutItem"][];
            /** Memos */
            memos?: string[];
            /** Parent Version */
            parent_version?: number | null;
            /** Power Points */
            power_points?: components["schemas"]["PowerPoint"][];
            /** Version */
            version: number;
            /** Warnings */
            warnings?: components["schemas"]["LayoutWarning"][];
        };
        /** LayoutGenerateIn */
        LayoutGenerateIn: {
            /**
             * None
             * @description 가구 없이 진행
             * @default false
             */
            none: boolean;
        };
        /** LayoutGroup */
        LayoutGroup: {
            /**
             * Anchor Label
             * @default
             */
            anchor_label: string;
            /**
             * At Label
             * @description 수량표 위치(「쇼윈도 창면」)
             * @default
             */
            at_label: string;
            /** Family Id */
            family_id?: string | null;
            /** Id */
            id: string;
            /** Item Ids */
            item_ids?: string[];
            /**
             * Kind
             * @enum {string}
             */
            kind: "product" | "furniture" | "column_wrap";
            /**
             * Label
             * @description 「OH55C ×3」 · 「관람 벤치 3열」 · 「기둥 랩핑 ×2」
             */
            label: string;
            /** Model Code */
            model_code?: string | null;
            /**
             * Plan Label
             * @description 배치안 라벨(「OH55C ×3 (창면)」 「The Wall IAB 146" (후면 벽)」)
             * @default
             */
            plan_label: string;
            /**
             * Qty
             * @default 1
             */
            qty: number;
            /**
             * Qty Source
             * @default default
             * @enum {string}
             */
            qty_source: "rule" | "user" | "suggested" | "default";
            /** Ref */
            ref: string;
            /** Rule Id */
            rule_id?: string | null;
            /**
             * Short
             * @default
             */
            short: string;
            /** Size */
            size?: string | null;
            /**
             * Tiny
             * @default
             */
            tiny: string;
        };
        /** LayoutItem */
        LayoutItem: {
            anchor?: components["schemas"]["Anchor"];
            /** D */
            d: number;
            /** Diag Inch */
            diag_inch?: number | null;
            /** Faces */
            faces?: string | null;
            /** Group Id */
            group_id: string;
            /** H */
            h: number;
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "product" | "furniture" | "column_wrap";
            /** Label */
            label: string;
            /**
             * Locked
             * @default false
             */
            locked: boolean;
            /**
             * Mount
             * @default floor
             * @enum {string}
             */
            mount: "wall" | "floor" | "ceiling" | "column" | "window_facing";
            /** Parts */
            parts?: {
                [key: string]: unknown;
            }[];
            /**
             * Qty In Group
             * @default 1
             */
            qty_in_group: number;
            /**
             * Qty Source
             * @default default
             * @enum {string}
             */
            qty_source: "rule" | "user" | "suggested" | "default";
            /**
             * Ref
             * @description bpi_… · bfi_…
             */
            ref: string;
            /** Role */
            role?: string | null;
            /**
             * Rot Deg
             * @default 0
             */
            rot_deg: number;
            /** Rule Id */
            rule_id?: string | null;
            /** Seat Points */
            seat_points?: number[][];
            /**
             * Seats
             * @default 0
             */
            seats: number;
            /**
             * Short
             * @default
             */
            short: string;
            /**
             * Tiny
             * @default
             */
            tiny: string;
            /**
             * Unplaced
             * @default false
             */
            unplaced: boolean;
            /** W */
            w: number;
            /** X */
            x: number;
            /** Y */
            y: number;
            /**
             * Z
             * @default 0
             */
            z: number;
        };
        /** LayoutNlEditIn */
        LayoutNlEditIn: {
            /** Session Id */
            session_id?: string | null;
            /** Text */
            text: string;
        };
        /** LayoutView */
        LayoutView: {
            /**
             * Default View
             * @default aerial45
             * @enum {string}
             */
            default_view: "aerial45" | "entrance";
            /** Job Id */
            job_id?: string | null;
            layout?: components["schemas"]["Layout"] | null;
            /**
             * Open Warnings
             * @default 0
             */
            open_warnings: number;
            overlays?: components["schemas"]["Overlays"];
            plan?: components["schemas"]["PlanGeometry"] | null;
            /**
             * Running
             * @default false
             */
            running: boolean;
            /**
             * Tone
             * @default warm_wood
             * @enum {string}
             */
            tone: "warm_wood" | "modern_white" | "dark_metal";
            /**
             * W Message
             * @default
             */
            w_message: string;
        };
        /** LayoutWarning */
        LayoutWarning: {
            /**
             * Actions
             * @description fix · ignore · memo · add_power
             */
            actions?: string[];
            /** Expr */
            expr: string;
            /** Fixes */
            fixes?: components["schemas"]["WarningFix"][];
            /** Id */
            id: string;
            /**
             * Key
             * @description 같은 경고를 다시 알아보는 키(종류 + 대상)
             * @default
             */
            key: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "viewing_angle" | "viewing_distance" | "walkway" | "power" | "mount_height" | "unplaced";
            /**
             * Marker
             * @description 배치안 위 번호 표식 위치[x, y]
             */
            marker?: number[] | null;
            /** Message Ko */
            message_ko: string;
            /** N */
            n: number;
            /**
             * Param Status
             * @default draft
             */
            param_status: string;
            /** Params */
            params?: {
                [key: string]: unknown;
            };
            /** Rule Id */
            rule_id: string;
            /**
             * Status
             * @default open
             * @enum {string}
             */
            status: "open" | "fixed" | "ignored" | "memo";
            /** Subjects */
            subjects?: string[];
            /** Title Ko */
            title_ko: string;
            /**
             * Tooltip
             * @description 「pr_warn_power_distance · distance_to_power_m > 3.0 (draft)」
             * @default
             */
            tooltip: string;
            /** Value */
            value?: number | null;
        };
        /** MoveMark */
        MoveMark: {
            /**
             * D
             * @default 0
             */
            d: number;
            /** Dx */
            dx: number;
            /** Dy */
            dy: number;
            /** From X */
            from_x: number;
            /** From Y */
            from_y: number;
            /** Group Id */
            group_id: string;
            /** Item Id */
            item_id: string;
            /** Label Ko */
            label_ko: string;
            /**
             * Rot Deg
             * @default 0
             */
            rot_deg: number;
            /**
             * W
             * @default 0
             */
            w: number;
        };
        /** NlEditAccepted */
        NlEditAccepted: {
            /** Job Id */
            job_id: string;
            /**
             * Status
             * @default queued
             * @constant
             */
            status: "queued";
        };
        /** Op */
        Op: {
            /** Deg */
            deg?: number | null;
            /** Dx */
            dx?: number | null;
            /** Dy */
            dy?: number | null;
            /** Group */
            group?: string | null;
            /** Item */
            item?: string | null;
            /**
             * Op
             * @enum {string}
             */
            op: "move" | "rotate" | "add" | "remove" | "set_qty" | "add_power" | "set_size" | "set_pos";
            /** Pos */
            pos?: number[] | null;
            /** Product */
            product?: string | null;
            /** Qty */
            qty?: number | null;
            /** Size */
            size?: string | null;
            /**
             * Spec
             * @description add — {kind, ref, w, d, h, x, y, rot_deg, label}
             */
            spec?: {
                [key: string]: unknown;
            } | null;
        } & {
            [key: string]: unknown;
        };
        /** Opening */
        Opening: {
            /**
             * Assumed
             * @description 되묻기에 답하지 않아 안전 기본값(출입 가능한 문)으로 처리
             * @default false
             */
            assumed: boolean;
            /** Confidence */
            confidence?: number | null;
            /** Door Type */
            door_type?: ("main" | "emergency" | "backoffice" | "normal" | "unknown") | null;
            /**
             * Faces Outdoor
             * @default false
             */
            faces_outdoor: boolean;
            /** Id */
            id: string;
            /**
             * Is Main
             * @default false
             */
            is_main: boolean;
            /**
             * Kind
             * @enum {string}
             */
            kind: "window" | "door" | "opening";
            /**
             * Label
             * @default
             */
            label: string;
            /**
             * Offset
             * @description 벽 a 점에서 개구부 시작까지(m)
             */
            offset: number;
            /** Wall Id */
            wall_id: string;
            /** Width */
            width: number;
        };
        /** OpsIn */
        OpsIn: {
            /** Ops */
            ops?: components["schemas"]["Op"][];
            /**
             * Redo
             * @default false
             */
            redo: boolean;
            /**
             * Undo
             * @default false
             */
            undo: boolean;
        };
        /** Origin */
        Origin: {
            /** Label */
            label?: string | null;
            /** Ref */
            ref?: string | null;
            /**
             * Return To
             * @description 돌아갈 웹 경로(제안서 PRS3 · 시나리오)
             */
            return_to?: string | null;
            /**
             * Service
             * @default birdseye
             */
            service: string;
        };
        /** Overlays */
        Overlays: {
            /** Bottlenecks */
            bottlenecks?: components["schemas"]["Bottleneck"][];
            /** Entrance */
            entrance?: number[] | null;
            /** Fans */
            fans?: components["schemas"]["ViewFan"][];
            /** Paths */
            paths?: components["schemas"]["WalkPath"][];
            /** Power Links */
            power_links?: components["schemas"]["PowerLink"][];
        };
        /** PHAsset */
        PHAsset: {
            /**
             * Caption Rule
             * @default 생성 이미지
             */
            caption_rule: string;
            /** File Id */
            file_id?: string | null;
            /** Image Version Id */
            image_version_id?: string | null;
            /** Kb Image Id */
            kb_image_id?: string | null;
            /**
             * Kind
             * @default image
             * @constant
             */
            kind: "image";
            /**
             * Rights
             * @default generated
             */
            rights: string;
            /** Source Url */
            source_url?: string | null;
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
             * @default confirmed
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
            repeat_key?: components["schemas"]["PHRepeatKey"] | null;
            /** Sheet Role */
            sheet_role: string;
            /** Sheet Title */
            sheet_title?: string | null;
            /** Solution Code */
            solution_code?: string | null;
            /** Sources */
            sources?: components["schemas"]["PHSourceRef"][];
            /**
             * Status
             * @default ok
             * @enum {string}
             */
            status: "ok" | "warn" | "add";
            /**
             * Status Label
             * @default 그대로 들어가요
             */
            status_label: string;
            template_hint?: components["schemas"]["PHTemplateHint"] | null;
        };
        /** Photo */
        Photo: {
            /** Birdseye Id */
            birdseye_id: string;
            /** Ceiling H M */
            ceiling_h_m?: number | null;
            /** Created At */
            created_at: string;
            /**
             * Dir Slot
             * @description 1..4 · ceiling
             */
            dir_slot?: string | null;
            /** File Id */
            file_id: string;
            /** Found */
            found?: string[];
            /** Id */
            id: string;
            /**
             * Is Ceiling
             * @default false
             */
            is_ceiling: boolean;
            /** Job Id */
            job_id?: string | null;
            /** N */
            n: number;
            /**
             * Needs Check
             * @default false
             */
            needs_check: boolean;
            quality?: components["schemas"]["PhotoQuality"];
            /** Stage Label */
            stage_label?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "recognizing" | "recognized" | "backlit" | "dark" | "blurry" | "failed" | "accepted";
            /**
             * Status Label
             * @description 「인식 완료 · 벽 · 상황판」 · 「역광 · 창 위치가 흐려요」 …
             */
            status_label: string;
            /** Thumb Url */
            thumb_url: string;
            /** Url */
            url: string;
            /** Wall Label */
            wall_label?: string | null;
        };
        /** PhotoAccepted */
        PhotoAccepted: {
            /** Job Id */
            job_id: string;
            /** Photo Id */
            photo_id: string;
            /**
             * Status
             * @default queued
             * @constant
             */
            status: "queued";
        };
        /** PhotoAdd */
        PhotoAdd: {
            /** File Id */
            file_id: string;
            /**
             * Is Ceiling
             * @default false
             */
            is_ceiling: boolean;
            /** Replace Photo Id */
            replace_photo_id?: string | null;
        };
        /** PhotoCounts */
        PhotoCounts: {
            /**
             * Check
             * @default 0
             */
            check: number;
            /**
             * Failed
             * @default 0
             */
            failed: number;
            /**
             * Recognized
             * @default 0
             */
            recognized: number;
            /**
             * Recognizing
             * @default 0
             */
            recognizing: number;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** PhotoPatch */
        PhotoPatch: {
            /**
             * Accept
             * @default true
             */
            accept: boolean;
        };
        /** PhotoQuality */
        PhotoQuality: {
            /**
             * Bright Ratio
             * @default 0
             */
            bright_ratio: number;
            /**
             * Lap Var
             * @default 0
             */
            lap_var: number;
            /**
             * Mean
             * @default 0
             */
            mean: number;
            /**
             * Rest Mean
             * @default 0
             */
            rest_mean: number;
        };
        /** PhotoSet */
        PhotoSet: {
            /**
             * Basis Count
             * @default 0
             */
            basis_count: number;
            /**
             * Can Continue
             * @default false
             */
            can_continue: boolean;
            /**
             * Ceiling Label
             * @description 「없음 · 층고는 추정값」 · 「있음 · 층고 3.2 m」
             * @default
             */
            ceiling_label: string;
            counts: components["schemas"]["PhotoCounts"];
            /**
             * Dir Count
             * @default 0
             */
            dir_count: number;
            /**
             * Dir Label
             * @description 「4 / 4」
             * @default
             */
            dir_label: string;
            /**
             * Echo
             * @default
             */
            echo: string;
            /**
             * Has Ceiling
             * @default false
             */
            has_ceiling: boolean;
            /**
             * Head
             * @description 「인식 완료 2 · 확인 필요 1 · 인식 중 1」
             * @default
             */
            head: string;
            /** Items */
            items: components["schemas"]["Photo"][];
            /**
             * Max Photos
             * @default 12
             */
            max_photos: number;
            /** Summary Chips */
            summary_chips?: components["schemas"]["Chip"][];
            /**
             * W Message
             * @default
             */
            w_message: string;
        };
        /** PHRepeatKey */
        PHRepeatKey: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "space" | "case" | "product" | "solution";
            /** Label */
            label: string;
            /** Ref */
            ref: string;
        };
        /** PHSource */
        PHSource: {
            /**
             * Feature
             * @default birdseye
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
        /** PHSourceRef */
        PHSourceRef: {
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
             * @default birdseye
             */
            section_key: string;
        };
        /** PHTemplateHint */
        PHTemplateHint: {
            /** Code */
            code: string;
            /** Name */
            name: string;
        };
        /** PlanAccepted */
        PlanAccepted: {
            /** Job Id */
            job_id: string;
            /** Plan Id */
            plan_id: string;
            /**
             * Status
             * @default queued
             * @constant
             */
            status: "queued";
        };
        /** PlanAdd */
        PlanAdd: {
            /** File Id */
            file_id: string;
            /**
             * Page
             * @default 1
             */
            page: number;
        };
        /** PlanElement */
        PlanElement: {
            /**
             * Key
             * @enum {string}
             */
            key: "wall" | "window" | "door" | "column" | "core";
            /** Label */
            label: string;
            /** Question N */
            question_n?: number | null;
            /** Summary */
            summary: string;
        };
        /** PlanGeometry */
        PlanGeometry: {
            /**
             * Area Label
             * @description 「120평 · 4.5m」
             * @default
             */
            area_label: string;
            /** Columns */
            columns?: components["schemas"]["Column"][];
            /** Cores */
            cores?: components["schemas"]["Core"][];
            /** Height M */
            height_m: number;
            /** Openings */
            openings?: components["schemas"]["Opening"][];
            /** Power Points */
            power_points?: components["schemas"]["PowerPoint"][];
            /** Rooms */
            rooms?: components["schemas"]["Room"][];
            /** Walls */
            walls?: components["schemas"]["Wall"][];
            /** Width M */
            width_m: number;
            /** Window Label */
            window_label?: string | null;
        };
        /** PlanList */
        PlanList: {
            /** Items */
            items: components["schemas"]["PlanView"][];
        };
        /** PlanPreview */
        PlanPreview: {
            /**
             * Area Label
             * @description 「120평 · 층고 4.5m」
             * @default
             */
            area_label: string;
            /** Area Pyeong */
            area_pyeong?: number | null;
            /** Ceiling H M */
            ceiling_h_m?: number | null;
            /** Columns */
            columns?: components["schemas"]["Column"][];
            /**
             * File Id
             * @description 평면 미리보기 PNG(있으면)
             */
            file_id?: string | null;
            /** Height M */
            height_m: number;
            /** Items */
            items?: components["schemas"]["PlanPreviewItem"][];
            /** Openings */
            openings?: components["schemas"]["Opening"][];
            /** Outline */
            outline?: number[][];
            /** Rooms */
            rooms?: components["schemas"]["Room"][];
            /** Walls */
            walls?: components["schemas"]["Wall"][];
            /** Width M */
            width_m: number;
            /** Window Label */
            window_label?: string | null;
            /**
             * Zone Count
             * @default 0
             */
            zone_count: number;
            /** Zones */
            zones?: components["schemas"]["PlanPreviewZone"][];
        };
        /** PlanPreviewItem */
        PlanPreviewItem: {
            /** D */
            d: number;
            /**
             * Kind
             * @enum {string}
             */
            kind: "product" | "furniture" | "column_wrap";
            /** Label */
            label: string;
            /**
             * Rot Deg
             * @default 0
             */
            rot_deg: number;
            /** W */
            w: number;
            /** X */
            x: number;
            /** Y */
            y: number;
        };
        /** PlanPreviewZone */
        PlanPreviewZone: {
            /** Id */
            id: string;
            /** N */
            n: number;
            /**
             * Name
             * @default
             */
            name: string;
            /** X */
            x: number;
            /** Y */
            y: number;
        };
        /** PlanRecognizeIn */
        PlanRecognizeIn: {
            /**
             * Page
             * @description 쪽 바꾸기(없으면 같은 쪽 다시 인식)
             */
            page?: number | null;
        };
        /** PlanView */
        PlanView: {
            /**
             * Area M2
             * @default 0
             */
            area_m2: number;
            /** Birdseye Id */
            birdseye_id: string;
            /**
             * Check Count
             * @default 0
             */
            check_count: number;
            /** Elements */
            elements?: components["schemas"]["PlanElement"][];
            /** Error */
            error?: string | null;
            /** File Id */
            file_id: string;
            /**
             * File Meta
             * @description 「1쪽 · 2.4 MB」
             * @default
             */
            file_meta: string;
            /**
             * File Name
             * @default
             */
            file_name: string;
            /**
             * Head
             * @description 「5종 · 확인 2」
             * @default
             */
            head: string;
            /** Id */
            id: string;
            /** Job Id */
            job_id?: string | null;
            /** Kind */
            kind?: ("vector_pdf" | "raster") | null;
            /** Meta Paths */
            meta_paths?: string[];
            model?: components["schemas"]["SpaceModel"] | null;
            /** Notices */
            notices?: string[];
            /**
             * Page
             * @default 1
             */
            page: number;
            /**
             * Page Box
             * @description 원본 쪽 그림에서 공간 외곽이 차지하는 범위 [x0, y0, x1, y1] 0..1 (겹쳐 보기)
             */
            page_box?: number[] | null;
            /** Page Image Url */
            page_image_url?: string | null;
            /**
             * Pages
             * @default 1
             */
            pages: number;
            /** Questions */
            questions?: components["schemas"]["Question"][];
            /**
             * Scale Label
             * @description 「축척 1:100 감지 · 면적 396 ㎡ (약 120평)」
             * @default
             */
            scale_label: string;
            /**
             * Stage Label
             * @default
             */
            stage_label: string;
            /**
             * Status
             * @enum {string}
             */
            status: "recognizing" | "recognized" | "failed";
            /**
             * W Message
             * @default
             */
            w_message: string;
        };
        /** PowerLink */
        PowerLink: {
            /** A */
            a: number[];
            /** B */
            b?: number[] | null;
            /** D */
            d?: number | null;
            /** Group Id */
            group_id: string;
        };
        /** PowerPoint */
        PowerPoint: {
            /** Id */
            id: string;
            /** Pos */
            pos: number[];
            /**
             * Source
             * @default user
             * @enum {string}
             */
            source: "plan" | "user" | "default";
        };
        /** Prefill */
        Prefill: {
            /**
             * Products
             * @description family_id 문자열 또는 {family_id, model_code, label, qty}
             */
            products?: (string | components["schemas"]["PrefillProduct"])[];
            /**
             * Reference Image Version
             * @description image 버전 id(imv_…) — 렌더 분위기 참조
             */
            reference_image_version?: string | null;
        };
        /** PrefillProduct */
        PrefillProduct: {
            /** Family Id */
            family_id?: string | null;
            /** Label */
            label?: string | null;
            /** Model Code */
            model_code?: string | null;
            /** Qty */
            qty?: number | null;
        };
        /** ProductItem */
        ProductItem: {
            /** Birdseye Id */
            birdseye_id: string;
            /**
             * Category
             * @default
             */
            category: string;
            /** Chosen Size */
            chosen_size?: string | null;
            /** Diag Inch */
            diag_inch?: number | null;
            /** Dims By Size */
            dims_by_size?: {
                [key: string]: components["schemas"]["Dims3"];
            };
            dims_m?: components["schemas"]["Dims3"] | null;
            /**
             * Dims Source
             * @default estimated
             * @enum {string}
             */
            dims_source: "spec" | "computed" | "estimated";
            /**
             * Display Name
             * @description 정식 표시명(「Outdoor Signage OH55C」)
             */
            display_name: string;
            /** Family Id */
            family_id: string;
            /** Id */
            id: string;
            /** Model Code */
            model_code?: string | null;
            /** Models By Size */
            models_by_size?: {
                [key: string]: string;
            };
            /**
             * Mount Default
             * @default wall
             * @enum {string}
             */
            mount_default: "wall" | "floor" | "ceiling" | "column" | "window_facing";
            /**
             * Order
             * @default 0
             */
            order: number;
            /** Ref */
            ref: string;
            /**
             * Role
             * @default display
             * @enum {string}
             */
            role: "window_signage" | "led_wall" | "display" | "interactive" | "kiosk" | "other";
            /**
             * Short
             * @description 약칭(「OH55C」 · 「The Wall IAB」)
             */
            short: string;
            /** Size Options */
            size_options?: string[];
        };
        /** ProductPick */
        ProductPick: {
            /** Family Id */
            family_id?: string | null;
            /** Label */
            label?: string | null;
            /** Model Code */
            model_code?: string | null;
            /** Ref */
            ref?: string | null;
        };
        /** ProductSearch */
        ProductSearch: {
            /** Items */
            items: components["schemas"]["ProductSearchItem"][];
        };
        /** ProductSearchItem */
        ProductSearchItem: {
            /** Family Id */
            family_id: string;
            /**
             * Kind
             * @default family
             * @enum {string}
             */
            kind: "model" | "family";
            /** Model Code */
            model_code?: string | null;
            /** Name */
            name: string;
            /**
             * Name Match
             * @description name 안에서 검색어와 맞은 [시작, 끝)
             */
            name_match?: number[] | null;
            /**
             * Ref
             * @description kb:family:fam_… · kb:model:mdl_…
             */
            ref: string;
            /** Size Options */
            size_options?: string[];
            /**
             * Subline
             * @description 「{카테고리} · {크기 옵션 ' / '} · {핵심 특징}」
             */
            subline: string;
            /** Thumb Url */
            thumb_url?: string | null;
        };
        /** ProductsPut */
        ProductsPut: {
            /** Items */
            items: components["schemas"]["ProductPick"][];
        };
        /** ProductsView */
        ProductsView: {
            /**
             * Analyzing
             * @default false
             */
            analyzing: boolean;
            /** Chips */
            chips?: components["schemas"]["Chip"][];
            /**
             * Echo
             * @default
             */
            echo: string;
            /** Files */
            files?: components["schemas"]["InputFile"][];
            /** Items */
            items: components["schemas"]["ProductItem"][];
            /**
             * W Message
             * @default
             */
            w_message: string;
        };
        /** ProposalHandoff */
        ProposalHandoff: {
            /** Assets */
            assets?: components["schemas"]["PHAsset"][];
            /** Customer */
            customer?: {
                [key: string]: unknown;
            } | null;
            /** Facts */
            facts?: components["schemas"]["PHFact"][];
            /** Items */
            items?: components["schemas"]["PHItem"][];
            /**
             * Live Link
             * @default false
             */
            live_link: boolean;
            source: components["schemas"]["PHSource"];
            target: components["schemas"]["PHTarget"];
        };
        /** Quantities */
        Quantities: {
            /** Furniture */
            furniture?: components["schemas"]["FurnitureDetailRow"][];
            furniture_row?: components["schemas"]["FurnitureRow"] | null;
            /** Memos */
            memos?: string[];
            /** Rows */
            rows: components["schemas"]["QuantityRow"][];
        };
        /** QuantityRow */
        QuantityRow: {
            /** At */
            at: string;
            /**
             * Confirm
             * @description 수량 근거가 추정(suggested) → 「확인 필요」
             * @default false
             */
            confirm: boolean;
            /** Family Id */
            family_id?: string | null;
            /** Memo */
            memo?: string | null;
            /** Model Code */
            model_code?: string | null;
            /** Name */
            name: string;
            /** Qty */
            qty: number;
            /**
             * Qty Source
             * @default default
             */
            qty_source: string;
            /** Rule Id */
            rule_id?: string | null;
            /** Source Url */
            source_url?: string | null;
        };
        /** Question */
        Question: {
            /** Answer */
            answer?: string | null;
            /**
             * Answered
             * @default false
             */
            answered: boolean;
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "dim" | "door";
            /** Manual M */
            manual_m?: number | null;
            /** N */
            n: number;
            /** Options */
            options?: components["schemas"]["QuestionOption"][];
            /** Ref */
            ref: string;
            /**
             * Sub
             * @description 「도면 표기 24.0 m · 축척 1:100 환산 23.6 m」
             */
            sub?: string | null;
            /**
             * Title
             * @description 「치수 보정 · 정면 폭」 · 「뒤쪽 문은 어떤 문인가요?」
             */
            title: string;
        };
        /** QuestionOption */
        QuestionOption: {
            /** Label */
            label: string;
            /** Value */
            value: string;
        };
        /** ReferenceImage */
        ReferenceImage: {
            /**
             * Label
             * @default 참조 이미지
             */
            label: string;
            /** Thumb Url */
            thumb_url?: string | null;
            /** Url */
            url?: string | null;
            /** Version Id */
            version_id: string;
        };
        /** ResultEditIn */
        ResultEditIn: {
            /** Cut Id */
            cut_id?: string | null;
            /** Text */
            text: string;
        };
        /** ResultEditOut */
        ResultEditOut: {
            /** Cut Id */
            cut_id?: string | null;
            /** Cut Ids */
            cut_ids?: string[];
            /** Job Id */
            job_id?: string | null;
            /** Notice */
            notice?: string | null;
            /**
             * Question
             * @description 모호할 때 W 가 한 번 되묻는 말(route_hint='ask')
             */
            question?: string | null;
            /** Route */
            route?: string | null;
            /**
             * Route Hint
             * @enum {string}
             */
            route_hint: "render" | "layout" | "view" | "mixed" | "ask";
        };
        /** Room */
        Room: {
            /** Id */
            id: string;
            /**
             * Label
             * @default
             */
            label: string;
            /**
             * Outline
             * @description [[x, y], …] 시계 방향(화면 기준)
             */
            outline: number[][];
            /** Space Types */
            space_types?: string[];
        };
        /** RowAction */
        RowAction: {
            /**
             * Label
             * @enum {string}
             */
            label: "열기" | "이어서" | "확인";
            /** Route */
            route: string;
        };
        /** RunningCut */
        RunningCut: {
            /** Cut Id */
            cut_id: string;
            /**
             * Label
             * @description 「야간 시점 추가 생성 중」
             */
            label: string;
            /**
             * Progress
             * @default 0
             */
            progress: number;
            /** Route */
            route: string;
        };
        /** SavedVersion */
        SavedVersion: {
            /** Created At */
            created_at: string;
            /**
             * Layout Version
             * @default 0
             */
            layout_version: number;
            /** Note */
            note?: string | null;
            /** Version */
            version: number;
        };
        /** SavedVersionList */
        SavedVersionList: {
            /** Items */
            items: components["schemas"]["SavedVersion"][];
        };
        /** SaveOut */
        SaveOut: {
            /**
             * Created
             * @default true
             */
            created: boolean;
            /** Version */
            version: number;
        };
        /** Scale */
        Scale: {
            /**
             * Correction
             * @default 1
             */
            correction: number;
            /** Ratio */
            ratio?: number | null;
            /**
             * Source
             * @default default
             * @enum {string}
             */
            source: "pdf_text" | "dimension" | "photo_estimate" | "default" | "description" | "user";
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
        /** SessionCreated */
        SessionCreated: {
            /** Base Version */
            base_version: number;
            /** Session Id */
            session_id: string;
        };
        /** SessionView */
        SessionView: {
            /** Base Version */
            base_version: number;
            /** Birdseye Id */
            birdseye_id: string;
            /**
             * Can Redo
             * @default false
             */
            can_redo: boolean;
            /**
             * Can Undo
             * @default false
             */
            can_undo: boolean;
            /**
             * Changes Count
             * @default 0
             */
            changes_count: number;
            layout: components["schemas"]["Layout"];
            /** Moves */
            moves?: components["schemas"]["MoveMark"][];
            /**
             * Open Warnings
             * @default 0
             */
            open_warnings: number;
            overlays?: components["schemas"]["Overlays"];
            plan?: components["schemas"]["PlanGeometry"] | null;
            /** Session Id */
            session_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "open" | "committed" | "discarded";
            /** Warnings */
            warnings: components["schemas"]["LayoutWarning"][];
        };
        /** SheetMapRow */
        SheetMapRow: {
            /** Code */
            code: string;
            /** From */
            from: string;
            /**
             * Kind
             * @default
             */
            kind: string;
            /** Ref */
            ref?: string | null;
            /** To */
            to: string;
        };
        /** SpaceModel */
        SpaceModel: {
            /**
             * Area M2
             * @default 0
             */
            area_m2: number;
            /** Assumptions */
            assumptions?: components["schemas"]["Assumption"][];
            ceiling_h?: components["schemas"]["CeilingH"];
            /** Columns */
            columns?: components["schemas"]["Column"][];
            /** Cores */
            cores?: components["schemas"]["Core"][];
            /** Dims */
            dims?: components["schemas"]["Dim"][];
            /**
             * Estimated
             * @default true
             */
            estimated: boolean;
            /**
             * Facts
             * @description 사진 · 설명에서 뽑은 사실 칩(「상황판 벽 폭 약 9 m」)
             */
            facts?: string[];
            /** Features */
            features?: components["schemas"]["Feature"][];
            /**
             * Meta Paths
             * @description 쓴 대체 경로(space:regex · plan:vector_only …)
             */
            meta_paths?: string[];
            /** Openings */
            openings?: components["schemas"]["Opening"][];
            /** Power Points */
            power_points?: components["schemas"]["PowerPoint"][];
            /** Questions */
            questions?: components["schemas"]["Question"][];
            /** Rooms */
            rooms?: components["schemas"]["Room"][];
            scale?: components["schemas"]["Scale"];
            /**
             * Source
             * @default description
             * @enum {string}
             */
            source: "description" | "plan" | "photos" | "mixed";
            /** Walls */
            walls?: components["schemas"]["Wall"][];
        };
        /** SpaceView */
        SpaceView: {
            /**
             * Analyzing
             * @default false
             */
            analyzing: boolean;
            /**
             * Echo
             * @default
             */
            echo: string;
            /**
             * Features Text
             * @default
             */
            features_text: string;
            /** Files */
            files?: components["schemas"]["InputFile"][];
            /** Job Id */
            job_id?: string | null;
            model?: components["schemas"]["SpaceModel"] | null;
            /**
             * Space Name
             * @description W 문장의 공간 이름(「로비」 「관제실」)
             * @default
             */
            space_name: string;
            /** Summary Chips */
            summary_chips?: components["schemas"]["Chip"][];
            /**
             * Version
             * @default 0
             */
            version: number;
            /** W Message */
            w_message: string;
        };
        /** TextIn */
        TextIn: {
            /** Text */
            text: string;
        };
        /** TokenPhotoIn */
        TokenPhotoIn: {
            /** File Id */
            file_id: string;
        };
        /** UploadToken */
        UploadToken: {
            /** Expires At */
            expires_at: string;
            /** Path */
            path: string;
            /**
             * Qr
             * @description QR 모듈 행("0101…") — 없으면 주소만
             */
            qr?: string[] | null;
            /** Token */
            token: string;
            /** Url */
            url: string;
        };
        /** UploadTokenInfo */
        UploadTokenInfo: {
            /** Expires At */
            expires_at: string;
            /**
             * Photo Count
             * @default 0
             */
            photo_count: number;
            /**
             * Title
             * @default
             */
            title: string;
            /** Token */
            token: string;
            /** Valid */
            valid: boolean;
        };
        /**
         * UploadTokenPrincipal
         * @description 게이트웨이 전용(internal) — valid=false 면 나머지는 비어 있다.
         */
        UploadTokenPrincipal: {
            /** Birdseye Id */
            birdseye_id?: string | null;
            /** Expires At */
            expires_at?: string | null;
            /** Owner */
            owner?: string | null;
            /** Owner Name */
            owner_name?: string | null;
            /** Valid */
            valid: boolean;
        };
        /** Usage */
        Usage: {
            /** Birdseye Id */
            birdseye_id: string;
            /** Created At */
            created_at: string;
            /**
             * Label
             * @default
             */
            label: string;
            /** Ref */
            ref: string;
            /** Route */
            route?: string | null;
            /**
             * Service
             * @enum {string}
             */
            service: "proposal" | "scenario";
            /** Version */
            version?: number | null;
        };
        /** UsageIn */
        UsageIn: {
            /**
             * Label
             * @default
             */
            label: string;
            /** Ref */
            ref: string;
            /** Route */
            route?: string | null;
            /**
             * Service
             * @enum {string}
             */
            service: "proposal" | "scenario";
            /** Version */
            version?: number | null;
        };
        /** UsageRef */
        UsageRef: {
            /**
             * Label
             * @default
             */
            label: string;
            /** Ref */
            ref: string;
            /** Route */
            route?: string | null;
            /**
             * Service
             * @enum {string}
             */
            service: "proposal" | "scenario";
            /** Version */
            version?: number | null;
        };
        /** ValidateIn */
        ValidateIn: {
            /** Base Version */
            base_version?: number | null;
            /** Ops */
            ops?: components["schemas"]["Op"][];
        };
        /** ValidateOut */
        ValidateOut: {
            /** Assumptions */
            assumptions?: components["schemas"]["Assumption"][];
            /**
             * Elapsed Ms
             * @default 0
             */
            elapsed_ms: number;
            /** Groups */
            groups?: components["schemas"]["LayoutGroup"][];
            /** Items */
            items: components["schemas"]["LayoutItem"][];
            overlays?: components["schemas"]["Overlays"];
            /** Warnings */
            warnings: components["schemas"]["LayoutWarning"][];
        };
        /** VersionInfo */
        VersionInfo: {
            /** Layout Version */
            layout_version: number;
            /**
             * Rev
             * @default 1
             */
            rev: number;
            /** Updated At */
            updated_at: string;
            /** Version */
            version: number;
            /** Zones Hash */
            zones_hash: string;
        };
        /** ViewFan */
        ViewFan: {
            /** Apex */
            apex: number[];
            /** Dir Deg */
            dir_deg: number;
            /** Half Angle Deg */
            half_angle_deg: number;
            /** Item Id */
            item_id: string;
            /** Max D */
            max_d: number;
            /** Min D */
            min_d: number;
        };
        /** ViewSpec */
        ViewSpec: {
            /** Custom Text */
            custom_text?: string | null;
            /** Preset */
            preset?: ("aerial45" | "entrance" | "product_front" | "top" | "custom") | null;
            /** Target Item Id */
            target_item_id?: string | null;
        };
        /** WalkPath */
        WalkPath: {
            /** Points */
            points: number[][];
            /** Target */
            target: string;
        };
        /** Wall */
        Wall: {
            /** A */
            a: number[];
            /** B */
            b: number[];
            /**
             * Dim Known
             * @description 도면 치수 · 사용자 값으로 폭을 안다(모르면 크기 옵션은 가장 큰 것 + 가정)
             * @default false
             */
            dim_known: boolean;
            /** Id */
            id: string;
            /**
             * Kind
             * @default exterior
             * @enum {string}
             */
            kind: "exterior" | "interior";
            /**
             * Label
             * @description 정면 · 후면 · 왼쪽 · 오른쪽 · 상황판 벽 …
             * @default
             */
            label: string;
            /** Room Id */
            room_id?: string | null;
            /**
             * Thickness
             * @default 0.2
             */
            thickness: number;
        };
        /** WarningActionIn */
        WarningActionIn: {
            /**
             * Action
             * @enum {string}
             */
            action: "fix" | "ignore" | "memo" | "add_power";
            /** Fix Id */
            fix_id?: string | null;
            /** Pos */
            pos?: number[] | null;
        };
        /** WarningFix */
        WarningFix: {
            /** Id */
            id: string;
            /** Label Ko */
            label_ko: string;
            /** Ops */
            ops: {
                [key: string]: unknown;
            }[];
        };
        /** ZoneCreate */
        ZoneCreate: {
            /** Cut Id */
            cut_id?: string | null;
            /** From Suggestion */
            from_suggestion?: string | null;
            /** U */
            u?: number | null;
            /** V */
            v?: number | null;
        };
        /** ZoneFurniture */
        ZoneFurniture: {
            /** Name */
            name: string;
            /**
             * Qty
             * @default 1
             */
            qty: number;
        };
        /** ZoneLink */
        ZoneLink: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "product" | "feature" | "need" | "scene";
            /** Label */
            label: string;
            /** Ref */
            ref?: string | null;
        };
        /** ZonePatch */
        ZonePatch: {
            /** Cut Id */
            cut_id?: string | null;
            /** Links */
            links?: components["schemas"]["ZoneLink"][] | null;
            /** Name */
            name?: string | null;
            /** Status */
            status?: ("active" | "suggested" | "dismissed") | null;
            /** Text */
            text?: string | null;
            /** U */
            u?: number | null;
            /** V */
            v?: number | null;
        };
        /** ZonePoint */
        ZonePoint: {
            /** Anchor M */
            anchor_m: number[];
            /** Birdseye Id */
            birdseye_id: string;
            /** Cluster Item Ids */
            cluster_item_ids?: string[];
            /** Id */
            id: string;
            /**
             * Kind
             * @default product
             * @enum {string}
             */
            kind: "product" | "furniture" | "empty";
            /** Links */
            links?: components["schemas"]["ZoneLink"][];
            /** Meta Path */
            meta_path?: string | null;
            /** N */
            n: number;
            /** Name */
            name: string;
            /** Path Order */
            path_order?: number | null;
            /**
             * Positions
             * @description {cut_id: [u, v]} 0..1
             */
            positions?: {
                [key: string]: number[];
            };
            /** Products */
            products?: components["schemas"]["ZoneProduct"][];
            /**
             * Short Name
             * @default
             */
            short_name: string;
            /**
             * Status
             * @default active
             * @enum {string}
             */
            status: "active" | "suggested" | "dismissed";
            /** Text */
            text: string;
            /** U */
            u?: number | null;
            /** V */
            v?: number | null;
        };
        /** ZonePreview */
        ZonePreview: {
            /**
             * Code
             * @enum {string}
             */
            code: "ZP-A" | "ZP-B" | "ZP-C";
            /** Count */
            count: number;
            /**
             * Layout Label
             * @description 「번호 콜아웃」
             */
            layout_label: string;
            /**
             * Line
             * @description 「ZP-A 번호 콜아웃 · 포인트 4곳」
             */
            line: string;
        };
        /** ZoneProduct */
        ZoneProduct: {
            /** Family Id */
            family_id?: string | null;
            /**
             * Group Label
             * @description 배치안 묶음 라벨(「OH55C ×3」)
             * @default
             */
            group_label: string;
            /**
             * Label
             * @description 정식 표시명(「Outdoor Signage OH55C」)
             */
            label: string;
            /** Model Code */
            model_code?: string | null;
            /**
             * Qty
             * @default 1
             */
            qty: number;
            /**
             * Short
             * @description 약칭(「OH55C」)
             * @default
             */
            short: string;
        };
        /** ZonesAutoIn */
        ZonesAutoIn: {
            /** Cut Id */
            cut_id?: string | null;
        };
        /** ZonesRewriteIn */
        ZonesRewriteIn: {
            /** Text */
            text: string;
            /** Zone Ids */
            zone_ids?: string[] | null;
        };
        /** ZoneSuggestion */
        ZoneSuggestion: {
            /**
             * Add Label
             * @description 「5번으로 추가」
             */
            add_label: string;
            /** Id */
            id: string;
            /** N */
            n: number;
            /**
             * Question
             * @description 「기둥 2개를 5번 포인트로 넣을까요?」
             */
            question: string;
            /**
             * Title
             * @description 「W 제안 · 기둥 랩핑 길 안내」
             */
            title: string;
        };
        /** ZonesView */
        ZonesView: {
            /** Cut Id */
            cut_id?: string | null;
            /**
             * Cut Label
             * @default
             */
            cut_label: string;
            /** Cut Url */
            cut_url?: string | null;
            /** Job Id */
            job_id?: string | null;
            /** Points */
            points: components["schemas"]["ZonePoint"][];
            preview: components["schemas"]["ZonePreview"];
            /**
             * Proposal Label
             * @description 연결된 제안서 제목(없으면 「연결된 제안서 없음」)
             */
            proposal_label?: string | null;
            /**
             * Running
             * @default false
             */
            running: boolean;
            /** Suggestions */
            suggestions?: components["schemas"]["ZoneSuggestion"][];
            /**
             * W Message
             * @default
             */
            w_message: string;
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
    list_birdseyes: {
        parameters: {
            query?: {
                cursor?: string | null;
                filter?: "all" | "in_progress" | "needs_check" | "done";
                in_proposal?: boolean;
                limit?: number;
                q?: string | null;
                scope?: "mine" | "team";
                sort?: "updated";
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
                    "application/json": components["schemas"]["BirdseyeList"];
                };
            };
        };
    };
    create_birdseye: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BirdseyeCreate"];
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
                    "application/json": components["schemas"]["Birdseye"];
                };
            };
        };
    };
    get_birdseye: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["Birdseye"];
                };
            };
        };
    };
    delete_birdseye: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
    patch_birdseye: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BirdseyePatch"];
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
                    "application/json": components["schemas"]["Birdseye"];
                };
            };
        };
    };
    clone_birdseye: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["CloneIn"];
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
                    "application/json": components["schemas"]["CloneOut"];
                };
            };
        };
    };
    save_birdseye: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["SaveOut"];
                };
            };
        };
    };
    attach: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AttachIn"];
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
                    "application/json": components["schemas"]["AttachOut"];
                };
            };
        };
    };
    list_cuts: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["Cut"][];
                };
            };
        };
    };
    create_cuts: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CutsCreate"];
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
                    "application/json": components["schemas"]["CutsAccepted"];
                };
            };
        };
    };
    export_options: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ExportCreate"];
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
    get_furniture: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["FurnitureView"];
                };
            };
        };
    };
    put_furniture: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FurniturePut"];
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
                    "application/json": components["schemas"]["FurnitureItem"][];
                };
            };
        };
    };
    recommend_furniture: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["FurnitureRecommendIn"];
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
    handoff: {
        parameters: {
            query?: {
                version?: number | null;
            };
            header?: never;
            path: {
                be_id: string;
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
    get_layout: {
        parameters: {
            query?: {
                version?: number | null;
            };
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["LayoutView"];
                };
            };
        };
    };
    create_session: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["SessionCreated"];
                };
            };
        };
    };
    generate_layout: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["LayoutGenerateIn"];
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
    nl_edit_layout: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LayoutNlEditIn"];
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
                    "application/json": components["schemas"]["NlEditAccepted"];
                };
            };
        };
    };
    validate_layout: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ValidateIn"];
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
                    "application/json": components["schemas"]["ValidateOut"];
                };
            };
        };
    };
    list_photos: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["PhotoSet"];
                };
            };
        };
    };
    add_photo: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PhotoAdd"];
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
                    "application/json": components["schemas"]["PhotoAccepted"];
                };
            };
        };
    };
    delete_photo: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
                photo_id: string;
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
    patch_photo: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
                photo_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PhotoPatch"];
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
                    "application/json": components["schemas"]["Photo"];
                };
            };
        };
    };
    recognize_photo: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
                photo_id: string;
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
                    "application/json": components["schemas"]["PhotoAccepted"];
                };
            };
        };
    };
    list_plans: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["PlanList"];
                };
            };
        };
    };
    add_plan: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlanAdd"];
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
                    "application/json": components["schemas"]["PlanAccepted"];
                };
            };
        };
    };
    get_plan: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
                plan_id: string;
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
                    "application/json": components["schemas"]["PlanView"];
                };
            };
        };
    };
    recognize_plan: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PlanRecognizeIn"];
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
                    "application/json": components["schemas"]["PlanAccepted"];
                };
            };
        };
    };
    get_products: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["ProductsView"];
                };
            };
        };
    };
    put_products: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProductsPut"];
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
                    "application/json": components["schemas"]["ProductItem"][];
                };
            };
        };
    };
    proposal_handoff: {
        parameters: {
            query?: {
                section?: string;
                type?: "standard" | "quickwin" | "solution";
            };
            header?: never;
            path: {
                be_id: string;
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
    quantities: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["Quantities"];
                };
            };
        };
    };
    result_edit: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResultEditIn"];
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
                    "application/json": components["schemas"]["ResultEditOut"];
                };
            };
        };
    };
    get_space: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["SpaceView"];
                };
            };
        };
    };
    analyze_space: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
    nl_edit_space: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TextIn"];
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
                    "application/json": components["schemas"]["NlEditAccepted"];
                };
            };
        };
    };
    answer_space: {
        parameters: {
            query?: {
                plan_id?: string | null;
            };
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AnswerIn"];
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
                    "application/json": components["schemas"]["SpaceModel"];
                };
            };
        };
    };
    add_facts: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TextIn"];
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
                    "application/json": components["schemas"]["FactsOut"];
                };
            };
        };
    };
    create_upload_token: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["UploadToken"];
                };
            };
        };
    };
    add_usage: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UsageIn"];
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
                    "application/json": components["schemas"]["Usage"];
                };
            };
        };
    };
    remove_usage: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
                ref: string;
                service_name: string;
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
    get_version: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["VersionInfo"];
                };
            };
        };
    };
    list_versions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["SavedVersionList"];
                };
            };
        };
    };
    restore_version: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["Birdseye"];
                };
            };
        };
    };
    get_zones: {
        parameters: {
            query?: {
                cut_id?: string | null;
            };
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["ZonesView"];
                };
            };
        };
    };
    add_zone: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ZoneCreate"];
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
                    "application/json": components["schemas"]["ZonePoint"];
                };
            };
        };
    };
    zones_auto: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["ZonesAutoIn"];
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
    renumber_zones: {
        parameters: {
            query?: {
                cut_id?: string | null;
            };
            header?: never;
            path: {
                be_id: string;
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
                    "application/json": components["schemas"]["ZonesView"];
                };
            };
        };
    };
    rewrite_zones: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                be_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ZonesRewriteIn"];
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
                    "application/json": components["schemas"]["NlEditAccepted"];
                };
            };
        };
    };
    catalog: {
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
                    "application/json": components["schemas"]["CatalogOut"];
                };
            };
        };
    };
    get_cut: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                cut_id: string;
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
                    "application/json": components["schemas"]["Cut"];
                };
            };
        };
    };
    patch_cut: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                cut_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CutPatch"];
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
                    "application/json": components["schemas"]["Cut"];
                };
            };
        };
    };
    cancel_cut: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                cut_id: string;
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
                    "application/json": components["schemas"]["Cut"];
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
    get_session: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
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
                    "application/json": components["schemas"]["SessionView"];
                };
            };
        };
    };
    session_autofix: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
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
                    "application/json": components["schemas"]["SessionView"];
                };
            };
        };
    };
    session_commit: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
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
                    "application/json": components["schemas"]["CommitOut"];
                };
            };
        };
    };
    session_discard: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
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
                    "application/json": components["schemas"]["CommitOut"];
                };
            };
        };
    };
    session_ops: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OpsIn"];
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
                    "application/json": components["schemas"]["SessionView"];
                };
            };
        };
    };
    warning_action: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
                warning_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WarningActionIn"];
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
                    "application/json": components["schemas"]["SessionView"];
                };
            };
        };
    };
    proposal_handoff_alias: {
        parameters: {
            query?: {
                section?: string;
                type?: "standard" | "quickwin" | "solution";
            };
            header?: never;
            path: {
                be_id: string;
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
    product_search: {
        parameters: {
            query?: {
                limit?: number;
                q?: string;
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
                    "application/json": components["schemas"]["ProductSearch"];
                };
            };
        };
    };
    get_upload_token: {
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
                    "application/json": components["schemas"]["UploadTokenInfo"];
                };
            };
        };
    };
    upload_token_photo: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                token: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TokenPhotoIn"];
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
                    "application/json": components["schemas"]["PhotoAccepted"];
                };
            };
        };
    };
    get_upload_token_principal: {
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
                    "application/json": components["schemas"]["UploadTokenPrincipal"];
                };
            };
        };
    };
    delete_zone: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                zone_id: string;
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
    patch_zone: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                zone_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ZonePatch"];
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
                    "application/json": components["schemas"]["ZonePoint"];
                };
            };
        };
    };
}
