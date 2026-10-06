// 자동 생성 — 직접 고치지 말 것. 원본: contracts/image.json (make contracts)
export interface paths {
    "/v1/capabilities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 모델 능력 → 기능 플래그(60초 캐시) */
        get: operations["get_capabilities"];
        put?: never;
        post?: never;
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
    "/v1/images": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 내 생성 이미지(IMG0 갤러리 · 셸 「내 생성 이미지」 탭 · IMG2R) */
        get: operations["list_images"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images:bulk-export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 선택 시안 ZIP(export 잡) */
        post: operations["bulk_export"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 시안 + 버전(제안서 I1: file_id · rights · caption_rule · scene · prompt) */
        get: operations["get_image"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}:interpret": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** R6 자유 입력(수정 요청 · 변형 요청 · 내보내기 요청) → 구조화 동작 */
        post: operations["interpret"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}:save": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 「내 이미지에 저장」 */
        post: operations["save_image"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/adjust": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 동기 로컬 보정(밝기 올리기 · 주변과 밝기 맞추기) — 모델 호출 없음 */
        post: operations["adjust_image"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/caption": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 「캡션 자동 작성」 */
        post: operations["make_caption"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/detections": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 객체 · 글자 · 사람 · 화면 감지(캐시) — bbox 미지원이면 422 CAPABILITY_UNSUPPORTED */
        post: operations["detect"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/edits": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 부분 · 전체 수정 run(영역마다 번호 순 새 버전) */
        post: operations["start_edit"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/exports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** PNG · JPG 는 바로(200), PDF · PPTX · 원본 함께(ZIP)는 export 잡(202) */
        post: operations["export_image"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/filename": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 「영문 파일명」 */
        post: operations["make_filename"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/info": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 상단바 이미지 정보 행(§5.2) */
        get: operations["get_image_info"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/regions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Regions */
        get: operations["list_regions"];
        put?: never;
        /** 수정 영역(사각형 · 브러시 · 객체) · 칩(글자 지우기 · 사람 지우기 · 제품 화면에 콘텐츠) */
        post: operations["create_region"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/regions/{region_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Region */
        delete: operations["delete_region"];
        options?: never;
        head?: never;
        /** Patch Region */
        patch: operations["patch_region"];
        trace?: never;
    };
    "/v1/images/{image_id}/regions/{region_id}:revert": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 영역 되돌리기 — 현재 버전을 그 영역의 기준 버전으로(버전은 남는다) */
        post: operations["revert_region"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/renditions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 비율 · 해상도 run(새 시안) — 능력 부족이면 422 CAPABILITY_UNSUPPORTED */
        post: operations["start_renditions"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/usages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 사용 등록 — 제안서 · 시나리오 · 조감도가 호출 */
        post: operations["add_usage"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/usages/{service_name}/{ref}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Usage */
        delete: operations["delete_usage"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/variants": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 변형 run(4장 · 조명만 · 손님 넣기) */
        post: operations["start_variants"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/versions": {
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
    "/v1/images/{image_id}/versions/{n}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 그 버전 내용으로 새 현재 버전(이전 버전은 남는다) */
        post: operations["restore_version"];
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
    "/v1/queue": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 내 대기열(다음 차례 · k번째) */
        get: operations["get_queue"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/reference-search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** IMG2R 탭(kb · mine · cases) 검색 */
        get: operations["reference_search"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/renders": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 렌더 API — 생성 · 편집(edit_of) · 구조 참조 · 업스케일 · 품질 확인 · AI 메타 */
        post: operations["create_render"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/renders/{render_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Render */
        get: operations["get_render"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/renders/{render_id}:cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Render */
        post: operations["cancel_render"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requests": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** IMG0 「다른 기능에서 요청한 이미지」(status=open,in_progress) · 요청자 조회(from_service · from_ref) */
        get: operations["list_requests"];
        put?: never;
        /** 다른 기능의 이미지 요청(서비스 간 — scenario · proposal) */
        post: operations["create_request"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requests/{request_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Request */
        get: operations["get_request"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requests/{request_id}:dismiss": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Dismiss Request */
        post: operations["dismiss_request"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requests/{request_id}:fulfill": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 요청을 이 버전으로 충족(IMG4 「공간 시나리오 장면으로」) */
        post: operations["fulfill_request"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/requests/{request_id}:start": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 「만들기」 — 작업을 만들고 경로(IMG1 route · IMG2 conditions_route)를 준다 */
        post: operations["start_request"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs/{run_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Run */
        get: operations["get_run"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** 「완료되면 알림」 */
        patch: operations["patch_run"];
        trace?: never;
    };
    "/v1/runs/{run_id}:cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 전체 취소(끝난 시안은 남긴다) */
        post: operations["cancel_run"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs/{run_id}/alternatives": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 「다른 대안 입력」 — LLM 이 사유를 판정, 정책 재검사 통과 시 custom 대안으로 저장 */
        post: operations["custom_alternative"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs/{run_id}/answers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** IMG3X 대안 → jobs 입력(같은 thread 재개) */
        post: operations["answer_run"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/runs/{run_id}/shots/{image_id}:cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 「이 장 취소」(대기 시안은 바로, 진행 시안은 결과 폐기) */
        post: operations["cancel_shot"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/versions/{version_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 버전 하나(렌디션 · 생성 메타) — 제안서 · 시나리오 · 조감도가 읽는다 */
        get: operations["get_version"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/works": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** IMG0 작업 목록(최근 수정순) */
        get: operations["list_works"];
        put?: never;
        /** 새 작업(IMG1 · 참조로 시작 · 현장 사진 합성) */
        post: operations["create_work"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/works/{work_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Work */
        get: operations["get_work"];
        put?: never;
        post?: never;
        /** Delete Work */
        delete: operations["delete_work"];
        options?: never;
        head?: never;
        /** 유형 · 설명 · 제목 · 조건 · 선택 시안(if_version → 409) */
        patch: operations["patch_work"];
        trace?: never;
    };
    "/v1/works/{work_id}:prefill": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** R1 — 제품 · 수량 · 제목 · 검색어(동기, 10초) */
        post: operations["prefill_work"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/works/{work_id}/placements": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** 배치 저장(300ms 디바운스) → 축척 · 실제 크기(가로 · 바닥에서) 계산 */
        put: operations["put_placements"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/works/{work_id}/products": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 셸 「현재 작업에 추가」 · 끌어 놓기(제품 참조 → KB 제품, 합성이면 배치 그룹) */
        post: operations["add_products"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/works/{work_id}/references": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List References */
        get: operations["list_references"];
        /** IMG2R 「참조 n장 적용」(묶음 교체) */
        put: operations["set_references"];
        /** 참조 추가(최대 3 → 422 REFERENCE_LIMIT) · 분석은 비동기 */
        post: operations["add_reference"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/works/{work_id}/references/{ref_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Reference */
        delete: operations["delete_reference"];
        options?: never;
        head?: never;
        /** 따를 요소 · 강도 · 순서(업로드 + 강 → 422 STRENGTH_NOT_ALLOWED) */
        patch: operations["patch_reference"];
        trace?: never;
    };
    "/v1/works/{work_id}/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 작업의 run(최근 순) */
        get: operations["list_runs"];
        put?: never;
        /** 생성 run(initial · composite · alternatives) — 사전 검사 포함 · 409 RUN_IN_PROGRESS */
        post: operations["create_run"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/works/{work_id}/site-photos": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Site Photos */
        get: operations["list_site_photos"];
        put?: never;
        /** 현장 사진 등록 → 인식 잡(202) */
        post: operations["add_site_photo"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/works/{work_id}/site-photos/{photo_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Site Photo */
        delete: operations["delete_site_photo"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/works/{work_id}/site-photos/{photo_id}:recognize": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 다시 인식 */
        post: operations["recognize_site_photo"];
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
        /** AdjustIn */
        AdjustIn: {
            /** Base Version Id */
            base_version_id?: string | null;
            /** Brightness */
            brightness?: number | null;
            /** Harmonize Region Id */
            harmonize_region_id?: string | null;
            /** Preset */
            preset?: "brighten" | null;
        };
        /** AlternativeIn */
        AlternativeIn: {
            /** Text */
            text: string;
        };
        /** AlternativeResult */
        AlternativeResult: {
            /** Accepted */
            accepted: boolean;
            /** Issue Id */
            issue_id?: string | null;
            /** Message */
            message: string;
            run: components["schemas"]["RunDetail"];
        };
        /** Answer */
        Answer: {
            /** Custom Text */
            custom_text?: string | null;
            /** Issue Id */
            issue_id: string;
            /** Option */
            option?: string | null;
            /**
             * Product
             * @description 「제품 탐색에서 고르기」로 고른 제품 {model_code, family_id, name, short}
             */
            product?: {
                [key: string]: unknown;
            } | null;
        };
        /** AnswersAccepted */
        AnswersAccepted: {
            /** Job Id */
            job_id?: string | null;
            /** Run Id */
            run_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "awaiting_input" | "succeeded" | "failed" | "canceled";
        };
        /** AnswersIn */
        AnswersIn: {
            /**
             * All Recommended
             * @default false
             */
            all_recommended: boolean;
            /** Answers */
            answers?: components["schemas"]["Answer"][];
            /**
             * Skip Held
             * @default false
             */
            skip_held: boolean;
        };
        /** Badge */
        Badge: {
            /**
             * Code
             * @description 상태 코드(running · awaiting_input · placing · in_proposal · exported · done · failed · draft)
             */
            code: string;
            /**
             * Icon
             * @default none
             * @enum {string}
             */
            icon: "clock" | "info" | "edit" | "check" | "download" | "none";
            /**
             * Label
             * @description 배지 문구(예 「생성 중 3 / 4」)
             */
            label: string;
            /**
             * Tone
             * @default gray
             * @enum {string}
             */
            tone: "brand" | "ink" | "gray";
        };
        /** BulkExportIn */
        BulkExportIn: {
            /**
             * Ai Label
             * @default true
             */
            ai_label: boolean;
            /**
             * Format
             * @default png
             * @constant
             */
            format: "png";
            /** Version Ids */
            version_ids: string[];
        };
        /** Capabilities */
        Capabilities: {
            /**
             * Available
             * @default true
             */
            available: boolean;
            features: components["schemas"]["FeatureFlags"];
            i2t: components["schemas"]["I2TCapFlags"];
            /** Mode */
            mode: string;
            t2i: components["schemas"]["T2ICapFlags"];
            /**
             * Upscaler
             * @enum {string}
             */
            upscaler: "none" | "realesrgan_x4v3";
        };
        /** CaptionResult */
        CaptionResult: {
            /** Caption */
            caption: string;
        };
        /** CompositeOptions */
        CompositeOptions: {
            /**
             * Perspective Light Match
             * @default true
             */
            perspective_light_match: boolean;
            /**
             * Screen Menu
             * @default true
             */
            screen_menu: boolean;
        };
        /** CompositeState */
        CompositeState: {
            /** Active Photo Id */
            active_photo_id?: string | null;
            /** Groups */
            groups?: components["schemas"]["PlacementGroup"][];
            /** Measures */
            measures?: components["schemas"]["GroupMeasure"][];
            options?: components["schemas"]["CompositeOptions"];
            ref_dims?: components["schemas"]["RefDims"];
            scale?: components["schemas"]["Scale"];
        };
        /** Conditions */
        Conditions: {
            /**
             * Aspect
             * @default 16:9
             * @enum {string}
             */
            aspect: "16:9" | "4:3" | "1:1";
            /**
             * Count
             * @default 4
             * @enum {integer}
             */
            count: 2 | 4;
            /**
             * No Products
             * @description 배경 유형의 「제품 없이」
             * @default false
             */
            no_products: boolean;
            /** Products */
            products?: components["schemas"]["ProductCond"][];
            /**
             * Style
             * @default photo
             * @enum {string}
             */
            style: "photo" | "minimal_3d" | "illustration";
        };
        /** DetectIn */
        DetectIn: {
            /** Kinds */
            kinds?: ("object" | "text" | "person" | "screen")[];
            /** Version Id */
            version_id?: string | null;
        };
        /** Detection */
        Detection: {
            /** Box */
            box: number[];
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "object" | "text" | "person" | "screen" | "product";
            /** Label */
            label: string;
        };
        /** Detections */
        Detections: {
            /** Boxes */
            boxes: components["schemas"]["Detection"][];
            /** Supported */
            supported: boolean;
            /** Version Id */
            version_id: string;
        };
        /** EditIn */
        EditIn: {
            /** Base Version Id */
            base_version_id?: string | null;
            /** Instruction */
            instruction?: string | null;
            /**
             * Mode
             * @default region
             * @enum {string}
             */
            mode: "region" | "global";
            /**
             * Protect Products
             * @default true
             */
            protect_products: boolean;
            /** Region Ids */
            region_ids?: string[] | null;
        };
        /** EditOf */
        EditOf: {
            /** File Id */
            file_id: string;
            /** Instruction */
            instruction: string;
        };
        /** EditRegion */
        EditRegion: {
            /** Base Version Id */
            base_version_id?: string | null;
            /** Created At */
            created_at: string;
            /** Detection Id */
            detection_id?: string | null;
            /** Error */
            error?: string | null;
            /** Id */
            id: string;
            /** Image Id */
            image_id: string;
            /**
             * Instruction
             * @default
             */
            instruction: string;
            /** Label */
            label: string;
            /** Mask File Id */
            mask_file_id?: string | null;
            /** N */
            n: number;
            /**
             * Protect Products
             * @default true
             */
            protect_products: boolean;
            /**
             * Rect
             * @description [x0,y0,x1,y1] 0..1
             */
            rect?: number[] | null;
            /** Result Version Id */
            result_version_id?: string | null;
            /** Run Id */
            run_id?: string | null;
            /**
             * Shape
             * @enum {string}
             */
            shape: "rect" | "brush" | "object";
            /**
             * Status
             * @enum {string}
             */
            status: "pending" | "applying" | "applied" | "reverted" | "failed";
            /** Status Label */
            status_label: string;
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
        /** ExpectProduct */
        ExpectProduct: {
            /** Bbox Hint */
            bbox_hint?: number[] | null;
            /** Family Id */
            family_id?: string | null;
            /** Model Code */
            model_code?: string | null;
            /**
             * Qty
             * @default 1
             */
            qty: number;
        };
        /** ExportIn */
        ExportIn: {
            /**
             * Ai Label
             * @default true
             */
            ai_label: boolean;
            /** Caption */
            caption?: string | null;
            /** Filename */
            filename?: string | null;
            /**
             * Format
             * @default png
             * @enum {string}
             */
            format: "png" | "jpg" | "pdf" | "pptx";
            /**
             * Include Original
             * @default false
             */
            include_original: boolean;
            /**
             * Resolution
             * @default uhd
             * @enum {string}
             */
            resolution: "fhd" | "uhd";
            /** Version Id */
            version_id?: string | null;
        };
        /** ExportOut */
        ExportOut: {
            /** Download Url */
            download_url?: string | null;
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            /** Export Id */
            export_id: string;
            /** File Id */
            file_id?: string | null;
            /** Filename */
            filename: string;
            /** Format */
            format: string;
            /** Job Id */
            job_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "done" | "failed";
        };
        /** FeatureFlags */
        FeatureFlags: {
            /** Mask Native */
            mask_native: boolean;
            /** Object Select */
            object_select: boolean;
            /** Outpaint */
            outpaint: boolean;
            /** Recompose */
            recompose: boolean;
            /** Reference Images */
            reference_images: boolean;
            /** Region Edit */
            region_edit: boolean;
            /** Upscale 4X */
            upscale_4x: boolean;
        };
        /** FilenameIn */
        FilenameIn: {
            /**
             * Ext
             * @default png
             */
            ext: string;
            /**
             * Lang
             * @default en
             * @enum {string}
             */
            lang: "en" | "ko";
            /** Version Id */
            version_id?: string | null;
        };
        /** FilenameResult */
        FilenameResult: {
            /** Filename */
            filename: string;
        };
        /** FulfillIn */
        FulfillIn: {
            /** Version Id */
            version_id: string;
        };
        /** GroupMeasure */
        GroupMeasure: {
            /** Bottom Mm */
            bottom_mm?: number | null;
            /**
             * Estimated
             * @default false
             */
            estimated: boolean;
            /**
             * Fit Quad
             * @description 축척이 있으면 실제 크기로 맞춘 그룹 쿼드(사진 0..1)
             */
            fit_quad?: number[][] | null;
            /** Height Mm */
            height_mm?: number | null;
            /** Id */
            id: string;
            /**
             * Label Text
             * @description 「가로 약 3,730 mm · 바닥에서 1,800 mm」 — 모르면 [00]
             * @default
             */
            label_text: string;
            /** Width Mm */
            width_mm?: number | null;
        };
        /** I2TCapFlags */
        I2TCapFlags: {
            /**
             * Available
             * @default true
             */
            available: boolean;
            /** Supports Bbox */
            supports_bbox: boolean;
            /** Supports Json */
            supports_json: boolean;
        };
        /** ImageDetail */
        ImageDetail: {
            /** Aspect */
            aspect: string;
            /** Base Image Id */
            base_image_id?: string | null;
            /**
             * Caption Rule
             * @default 생성 이미지
             */
            caption_rule: string;
            /** Created At */
            created_at: string;
            current?: components["schemas"]["Version"] | null;
            /** Current Version Id */
            current_version_id?: string | null;
            /** Customer Short */
            customer_short?: string | null;
            /**
             * File Id
             * @description 현재 버전의 기준 렌디션(fhd) 파일
             */
            file_id?: string | null;
            /** Height */
            height?: number | null;
            /**
             * Hidden
             * @default false
             */
            hidden: boolean;
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "space" | "background" | "scenario" | "composite";
            /** Label */
            label: string;
            /** Layout Note */
            layout_note?: string | null;
            /** Letter */
            letter?: string | null;
            /**
             * Origin
             * @default image
             */
            origin: string;
            /** Products */
            products?: components["schemas"]["ProductCond"][];
            /** Project Id */
            project_id?: string | null;
            /** Prompt */
            prompt?: string | null;
            /**
             * Qc Flag
             * @default false
             */
            qc_flag: boolean;
            /** Qc Reason */
            qc_reason?: string | null;
            /**
             * Rights
             * @default generated
             * @constant
             */
            rights: "generated";
            /** Run Id */
            run_id?: string | null;
            /**
             * Saved
             * @default false
             */
            saved: boolean;
            scene?: components["schemas"]["Scene"];
            /**
             * Status
             * @enum {string}
             */
            status: "waiting" | "composing" | "rendering" | "qc" | "done" | "held" | "canceled" | "failed";
            /**
             * Style
             * @default photo
             * @enum {string}
             */
            style: "photo" | "minimal_3d" | "illustration";
            /** Subject Short */
            subject_short?: string | null;
            /** Thumb Url */
            thumb_url?: string | null;
            /** Title */
            title: string;
            /** Url */
            url?: string | null;
            /** Used In */
            used_in?: components["schemas"]["Usage"][];
            /** Variant Name */
            variant_name?: string | null;
            /** Versions */
            versions?: components["schemas"]["Version"][];
            /** Width */
            width?: number | null;
            /** Work Id */
            work_id: string;
            /**
             * Work Title
             * @default
             */
            work_title: string;
        };
        /** ImageInfo */
        ImageInfo: {
            /** Image Id */
            image_id: string;
            /** Rows */
            rows: components["schemas"]["InfoRow"][];
            /** Title */
            title: string;
            /** Version Id */
            version_id: string;
        };
        /** ImageList */
        ImageList: {
            /** Items */
            items: components["schemas"]["ImageTile"][];
            /** Next Cursor */
            next_cursor?: string | null;
            /** Total */
            total: number;
        };
        /** ImageRequest */
        ImageRequest: {
            /** Created At */
            created_at: string;
            /** Created By */
            created_by: string;
            /** From Label */
            from_label: string;
            /** From Ref */
            from_ref: string;
            /** From Service */
            from_service: string;
            /** Id */
            id: string;
            prefill: components["schemas"]["RequestPrefill"];
            /** Project Id */
            project_id?: string | null;
            /** Result Image Id */
            result_image_id?: string | null;
            /** Result Version Id */
            result_version_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "open" | "in_progress" | "fulfilled" | "dismissed";
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
            /** Work Id */
            work_id?: string | null;
        };
        /** ImageTile */
        ImageTile: {
            /** Aspect */
            aspect: string;
            /** Bytes */
            bytes?: number | null;
            /** Created At */
            created_at: string;
            /** Current Version Id */
            current_version_id?: string | null;
            /** Customer Short */
            customer_short?: string | null;
            /** File Id */
            file_id?: string | null;
            /** Format */
            format?: string | null;
            /** Height */
            height?: number | null;
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "space" | "background" | "scenario" | "composite";
            /** Label */
            label: string;
            /**
             * Meta
             * @description 「A 커피 · 공간 · 16:9」 · 생성 중이면 「… · 생성 중」
             * @default
             */
            meta: string;
            /**
             * Origin
             * @default image
             */
            origin: string;
            /** Progress Done */
            progress_done?: number | null;
            /** Progress Total */
            progress_total?: number | null;
            /**
             * Route
             * @default
             */
            route: string;
            /** Run Id */
            run_id?: string | null;
            /** Run Route */
            run_route?: string | null;
            /**
             * Saved
             * @default false
             */
            saved: boolean;
            /**
             * Status
             * @enum {string}
             */
            status: "waiting" | "composing" | "rendering" | "qc" | "done" | "held" | "canceled" | "failed";
            /** Thumb Url */
            thumb_url?: string | null;
            /** Title */
            title: string;
            /**
             * Used In Count
             * @default 0
             */
            used_in_count: number;
            /** Width */
            width?: number | null;
            /** Work Id */
            work_id: string;
        };
        /** InfoRow */
        InfoRow: {
            /** Href */
            href?: string | null;
            /** K */
            k: string;
            /** V */
            v: string;
        };
        /** InterpretIn */
        InterpretIn: {
            /**
             * Screen
             * @default result
             * @enum {string}
             */
            screen: "result" | "variants" | "export" | "edit";
            /** Text */
            text: string;
        };
        /** InterpretResult */
        InterpretResult: {
            /**
             * Action
             * @enum {string}
             */
            action: "region_edit" | "global_edit" | "variants" | "aspect_instruction" | "export_options" | "ask";
            /** Aspect */
            aspect?: string | null;
            /**
             * Instruction
             * @default
             */
            instruction: string;
            /**
             * Options
             * @description 내보내기 옵션(caption · english_filename · format · include_original …)
             */
            options?: {
                [key: string]: unknown;
            };
            /**
             * Question
             * @description 해석이 모호할 때 W 가 한 번 되묻는 문장
             */
            question?: string | null;
            /**
             * Region
             * @description {rect, label} — region_edit
             */
            region?: {
                [key: string]: unknown;
            } | null;
        };
        /** IssueOption */
        IssueOption: {
            /**
             * Action
             * @default choose
             * @enum {string}
             */
            action: "choose" | "pick_product" | "link";
            /**
             * Default
             * @default false
             */
            default: boolean;
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
        /** JobAccepted */
        JobAccepted: {
            /** Job Id */
            job_id: string;
            /** Run Id */
            run_id: string;
            /**
             * Status
             * @default queued
             * @enum {string}
             */
            status: "queued" | "running" | "awaiting_input" | "succeeded" | "failed" | "canceled";
        };
        /** Origin */
        Origin: {
            /** Label */
            label?: string | null;
            /** Ref */
            ref?: string | null;
            /** Request Id */
            request_id?: string | null;
            /**
             * Service
             * @default image
             */
            service: string;
        };
        /** PhotoQuality */
        PhotoQuality: {
            /** Clipped Ratio */
            clipped_ratio: number;
            /** Laplacian Var */
            laplacian_var: number;
            /** Luma Mean */
            luma_mean: number;
        };
        /** PlacementGroup */
        PlacementGroup: {
            /**
             * Arrangement
             * @default row3
             * @enum {string}
             */
            arrangement: "row3" | "col3" | "separate" | "single";
            /** Family Id */
            family_id?: string | null;
            /**
             * Gap Mm
             * @default 10
             */
            gap_mm: number;
            /** Id */
            id: string;
            /**
             * Label
             * @description 약칭(예 QM55C)
             * @default
             */
            label: string;
            /** Model Code */
            model_code?: string | null;
            /**
             * Mount
             * @default wall
             * @enum {string}
             */
            mount: "wall" | "ceiling";
            /**
             * Name
             * @default
             */
            name: string;
            /**
             * Qty
             * @default 1
             */
            qty: number;
            /**
             * Quad
             * @description 사진 좌표(0..1) [[x,y]×4] 왼쪽 위부터 시계 방향
             */
            quad?: number[][];
        };
        /** PlacementResult */
        PlacementResult: {
            composite: components["schemas"]["CompositeState"];
            /** Groups */
            groups: components["schemas"]["GroupMeasure"][];
            scale: components["schemas"]["Scale"];
        };
        /** PlacementsIn */
        PlacementsIn: {
            /** Groups */
            groups?: components["schemas"]["PlacementGroup"][];
            options?: components["schemas"]["CompositeOptions"];
            /** Photo Id */
            photo_id: string;
            ref_dims?: components["schemas"]["RefDims"];
        };
        /** PolicyIssue */
        PolicyIssue: {
            /** Custom Text */
            custom_text?: string | null;
            /** Data */
            data?: {
                [key: string]: unknown;
            };
            /** Description */
            description: string;
            /** Id */
            id: string;
            /** Options */
            options: components["schemas"]["IssueOption"][];
            /**
             * Selected
             * @description 고른 option id · 'custom'
             */
            selected?: string | null;
            /**
             * State Label
             * @description 「대안 선택됨」 · 「선택 필요」
             */
            state_label: string;
            /**
             * Status
             * @enum {string}
             */
            status: "auto" | "needs_choice";
            /** Title */
            title: string;
            /**
             * Type
             * @enum {string}
             */
            type: "product_unrecognized" | "competitor_brand" | "real_person" | "unsafe";
        };
        /** Precheck */
        Precheck: {
            /**
             * Applied Note
             * @description 「경쟁사 · 인물 요소 없이 만들었어요」
             */
            applied_note?: string | null;
            /** Issues */
            issues?: components["schemas"]["PolicyIssue"][];
            /**
             * Mode
             * @default rules
             * @enum {string}
             */
            mode: "llm" | "rules";
        };
        /** Prefill */
        Prefill: {
            /** Customer Name */
            customer_name?: string | null;
            /** Industry Chips */
            industry_chips?: string[];
            /** Kind Suggestion */
            kind_suggestion?: ("space" | "background" | "scenario" | "composite") | null;
            /** Message */
            message?: string | null;
            /** Products */
            products?: components["schemas"]["PrefillProduct"][];
            /** Search Query */
            search_query?: string | null;
            /** Subject Short */
            subject_short?: string | null;
            /**
             * Timed Out
             * @default false
             */
            timed_out: boolean;
            /** Title */
            title: string;
            work: components["schemas"]["Work"];
        };
        /** PrefillProduct */
        PrefillProduct: {
            /** Family Id */
            family_id?: string | null;
            /** Model Code */
            model_code?: string | null;
            /** Name */
            name: string;
            /**
             * Qty
             * @default 1
             */
            qty: number;
            /** Short */
            short: string;
        };
        /** PrefillState */
        PrefillState: {
            /**
             * Done
             * @default false
             */
            done: boolean;
            /** Industry */
            industry?: string | null;
            /** Industry Chips */
            industry_chips?: string[];
            /** Kind Suggestion */
            kind_suggestion?: ("space" | "background" | "scenario" | "composite") | null;
            /**
             * Message
             * @description prefill 실패 안내(「제품을 찾지 못했어요. 제품명을 입력해 주세요」)
             */
            message?: string | null;
            /** Search Query */
            search_query?: string | null;
            /** Space Label */
            space_label?: string | null;
            /**
             * Timed Out
             * @default false
             */
            timed_out: boolean;
        };
        /** ProductCond */
        ProductCond: {
            /** Family Id */
            family_id?: string | null;
            /** Model Code */
            model_code?: string | null;
            /**
             * Name
             * @description 표시명(예 Smart Signage QM55C)
             */
            name: string;
            /**
             * Qty
             * @default 1
             */
            qty: number;
            /**
             * Short
             * @description 약칭(예 QM55C)
             */
            short: string;
            /**
             * Source
             * @default user
             * @enum {string}
             */
            source: "prefill" | "user" | "request";
        };
        /** ProductRef */
        ProductRef: {
            /** Family Id */
            family_id?: string | null;
            /** Model Code */
            model_code?: string | null;
            /**
             * Qty
             * @default 1
             */
            qty: number;
        };
        /** ProductsAdd */
        ProductsAdd: {
            /**
             * Qty
             * @default 1
             */
            qty: number;
            /**
             * Refs
             * @description 셸 참조 kb:model:mdl_… · kb:family:fam_… · custom:<글>
             */
            refs: string[];
        };
        /** ProductsAdded */
        ProductsAdded: {
            /**
             * Added
             * @description 풀어서 더한 참조(셸 「✓ 추가됨」)
             */
            added: string[];
            work: components["schemas"]["Work"];
        };
        /** QueueItem */
        QueueItem: {
            /** Meta */
            meta: string;
            /** Note */
            note?: string | null;
            /** Note Route */
            note_route?: string | null;
            /** Position */
            position: number;
            /** Run Id */
            run_id: string;
            /** State Label */
            state_label: string;
            /** Title */
            title: string;
            /** Work Id */
            work_id: string;
        };
        /** QueueList */
        QueueList: {
            /** Items */
            items: components["schemas"]["QueueItem"][];
            running?: components["schemas"]["RunBrief"] | null;
        };
        /** RefAnalysis */
        RefAnalysis: {
            /** Caption */
            caption?: string | null;
            /** Displays */
            displays?: {
                [key: string]: unknown;
            }[];
            /**
             * Elements
             * @description 따를 요소별 묘사(color_light · composition · placement · material)
             */
            elements?: {
                [key: string]: string;
            };
            /** Faces */
            faces?: number[][];
            /** Logos */
            logos?: number[][];
            /** Palette */
            palette?: string[];
            /** Style */
            style?: string | null;
        };
        /** RefDims */
        RefDims: {
            /** Counter Width Mm */
            counter_width_mm?: number | null;
            /** Install Height Mm */
            install_height_mm?: number | null;
        };
        /** Reference */
        Reference: {
            analysis?: components["schemas"]["RefAnalysis"] | null;
            /** Aspects */
            aspects: ("color_light" | "composition" | "placement" | "material")[];
            /** Created At */
            created_at: string;
            /** File Id */
            file_id?: string | null;
            /** Id */
            id: string;
            /** Label */
            label: string;
            /** Order */
            order: number;
            /**
             * Origin Kind
             * @default kb_asset
             * @enum {string}
             */
            origin_kind: "kb_asset" | "my_image" | "case_photo" | "upload";
            /**
             * Rights
             * @enum {string}
             */
            rights: "official" | "customer_case" | "generated" | "customer" | "unknown";
            /**
             * Role Label
             * @description 「구도」 · 「색감 · 조명 · 소재」
             * @default
             */
            role_label: string;
            /** Sanitized File Id */
            sanitized_file_id?: string | null;
            /** Send Mode */
            send_mode?: ("image" | "text_fallback") | null;
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "kb_asset" | "my_image" | "case_photo" | "upload" | "topbar";
            /** Source Label */
            source_label: string;
            /** Source Ref */
            source_ref?: string | null;
            /** Source Url */
            source_url?: string | null;
            /**
             * Strength
             * @enum {string}
             */
            strength: "low" | "mid" | "high";
            /**
             * Strong Allowed
             * @default true
             */
            strong_allowed: boolean;
            /** Thumb Url */
            thumb_url?: string | null;
            /**
             * Via
             * @default picker
             * @enum {string}
             */
            via: "picker" | "topbar" | "drop" | "upload";
            /** Work Id */
            work_id: string;
        };
        /** ReferenceIn */
        ReferenceIn: {
            /** Aspects */
            aspects?: ("color_light" | "composition" | "placement" | "material")[] | null;
            /** File Id */
            file_id?: string | null;
            /** Label */
            label?: string | null;
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "kb_asset" | "my_image" | "case_photo" | "upload" | "topbar";
            /**
             * Source Ref
             * @description KB 이미지 id · img_(내 생성) · dep_ 사례 사진 id · 셸 ref(kb:image:… · img:image:…)
             */
            source_ref?: string | null;
            /** Strength */
            strength?: ("low" | "mid" | "high") | null;
            /** Via */
            via?: ("picker" | "topbar" | "drop" | "upload") | null;
        };
        /** ReferenceList */
        ReferenceList: {
            /** Items */
            items: components["schemas"]["Reference"][];
            /** Notice */
            notice?: string | null;
        };
        /** ReferencePatch */
        ReferencePatch: {
            /** Aspects */
            aspects?: ("color_light" | "composition" | "placement" | "material")[] | null;
            /** Order */
            order?: number | null;
            /** Strength */
            strength?: ("low" | "mid" | "high") | null;
        };
        /** ReferenceSet */
        ReferenceSet: {
            /** Items */
            items?: components["schemas"]["ReferenceIn"][];
            /**
             * Via
             * @default picker
             * @enum {string}
             */
            via: "picker" | "topbar" | "drop" | "upload";
        };
        /** RefSearch */
        RefSearch: {
            /**
             * Head
             * @description 「8 개 · 검수 완료」 · 「3 개」
             */
            head: string;
            /** Industry Chips */
            industry_chips?: string[];
            /** Items */
            items: components["schemas"]["RefSearchItem"][];
            /** Next Cursor */
            next_cursor?: string | null;
            /**
             * Query
             * @default
             */
            query: string;
            /** Total */
            total: number;
        };
        /** RefSearchItem */
        RefSearchItem: {
            /** Alt */
            alt?: string | null;
            /** File Id */
            file_id?: string | null;
            /** Label */
            label: string;
            /**
             * Rights
             * @enum {string}
             */
            rights: "official" | "customer_case" | "generated" | "customer" | "unknown";
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "kb_asset" | "my_image" | "case_photo" | "upload" | "topbar";
            /** Source Label */
            source_label: string;
            /** Source Ref */
            source_ref: string;
            /** Source Url */
            source_url?: string | null;
            /** Thumb Url */
            thumb_url?: string | null;
            /**
             * Verified
             * @default false
             */
            verified: boolean;
            /**
             * Visual Style
             * @default photo
             * @enum {string}
             */
            visual_style: "photo" | "illustration";
        };
        /** RegionCreated */
        RegionCreated: {
            /** Global Instruction */
            global_instruction?: string | null;
            /**
             * Note
             * @description 「자동 영역 인식이 없어 전체 이미지에 적용해요」 — 이때 region 은 없고 global_instruction 으로 전체 편집
             */
            note?: string | null;
            /** @description 첫 영역(칩으로 여러 개가 생기면 regions 에 모두) */
            region?: components["schemas"]["EditRegion"] | null;
            /** Regions */
            regions?: components["schemas"]["EditRegion"][];
        };
        /** RegionIn */
        RegionIn: {
            /** Detection Id */
            detection_id?: string | null;
            /** Instruction */
            instruction?: string | null;
            /** Label */
            label?: string | null;
            /** Mask File Id */
            mask_file_id?: string | null;
            /** Preset */
            preset?: ("erase_text" | "erase_people" | "screen_content") | null;
            /** Rect */
            rect?: number[] | null;
            /**
             * Shape
             * @default rect
             * @enum {string}
             */
            shape: "rect" | "brush" | "object";
        };
        /** RegionList */
        RegionList: {
            /** Items */
            items: components["schemas"]["EditRegion"][];
        };
        /** RegionPatch */
        RegionPatch: {
            /** Instruction */
            instruction?: string | null;
            /** Label */
            label?: string | null;
            /** Mask File Id */
            mask_file_id?: string | null;
            /** Protect Products */
            protect_products?: boolean | null;
            /** Rect */
            rect?: number[] | null;
        };
        /** RenderAccepted */
        RenderAccepted: {
            /** Job Id */
            job_id: string;
            /** Render Id */
            render_id: string;
            /**
             * Status
             * @default queued
             * @constant
             */
            status: "queued";
        };
        /** RenderExpect */
        RenderExpect: {
            /** Products */
            products?: components["schemas"]["ExpectProduct"][];
        };
        /** RenderIn */
        RenderIn: {
            /**
             * Allow People
             * @default none
             * @enum {string}
             */
            allow_people: "none" | "silhouette" | "generic";
            /**
             * Aspect
             * @default 16:9
             */
            aspect: string;
            /**
             * Confidential
             * @default false
             */
            confidential: boolean;
            edit_of?: components["schemas"]["EditOf"] | null;
            expect?: components["schemas"]["RenderExpect"] | null;
            /** Forbid */
            forbid?: ("competitor_logo" | "real_person_face" | "gibberish_text")[];
            /**
             * Kind
             * @description birdseye · scene · …
             * @default scene
             */
            kind: string;
            /** Label */
            label?: string | null;
            origin: components["schemas"]["Origin"];
            /** Product Refs */
            product_refs?: components["schemas"]["ProductRef"][];
            /** Project Id */
            project_id?: string | null;
            prompt: components["schemas"]["RenderPrompt"];
            /** Reference File Ids */
            reference_file_ids?: string[];
            /** Structure Ref File Id */
            structure_ref_file_id?: string | null;
            /**
             * Style
             * @default photo
             * @enum {string}
             */
            style: "photo" | "minimal_3d" | "illustration";
            /**
             * Target
             * @default fhd
             * @enum {string}
             */
            target: "fhd" | "uhd";
        };
        /** RenderOut */
        RenderOut: {
            /** Created At */
            created_at: string;
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            /** Generation */
            generation?: {
                [key: string]: unknown;
            };
            /** Id */
            id: string;
            /** Image Id */
            image_id?: string | null;
            /** Job Id */
            job_id?: string | null;
            /** Kind */
            kind: string;
            origin: components["schemas"]["Origin"];
            /** Qc */
            qc?: {
                [key: string]: unknown;
            };
            /** Renditions */
            renditions?: components["schemas"]["Rendition"][];
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "succeeded" | "failed" | "canceled";
            /** Version Id */
            version_id?: string | null;
        };
        /** RenderPrompt */
        RenderPrompt: {
            /** Details Ko */
            details_ko?: string[];
            /** Negatives */
            negatives?: string[];
            /** Subject Ko */
            subject_ko: string;
        };
        /** Rendition */
        Rendition: {
            /** File Id */
            file_id: string;
            /** H */
            h: number;
            /**
             * Kind
             * @enum {string}
             */
            kind: "native" | "fhd" | "uhd" | "uhd8k" | "thumb";
            /**
             * Method
             * @default
             */
            method: string;
            /** Url */
            url: string;
            /** W */
            w: number;
        };
        /** RenditionsIn */
        RenditionsIn: {
            /** Aspects */
            aspects: ("16:9" | "4:3" | "1:1" | "9:16")[];
            /**
             * Fit
             * @default recompose
             * @enum {string}
             */
            fit: "recompose" | "crop" | "outpaint";
            /** Instructions */
            instructions?: {
                [key: string]: string;
            } | null;
            /**
             * Upscale
             * @default 2x
             * @enum {string}
             */
            upscale: "1x" | "2x" | "4x";
        };
        /** RequestIn */
        RequestIn: {
            /** From Label */
            from_label: string;
            /** From Ref */
            from_ref: string;
            /** From Service */
            from_service: string;
            prefill?: components["schemas"]["RequestPrefill"];
            /** Project Id */
            project_id?: string | null;
            /** Title */
            title: string;
        };
        /** RequestList */
        RequestList: {
            /** Items */
            items: components["schemas"]["ImageRequest"][];
        };
        /** RequestPrefill */
        RequestPrefill: {
            /** Aspect */
            aspect?: ("16:9" | "4:3" | "1:1") | null;
            /** Description */
            description?: string | null;
            /** Kind */
            kind?: ("space" | "background" | "scenario" | "composite") | null;
            /**
             * Products
             * @description 모델코드 · 제품 이름 문자열 또는 {model_code, family_id, name, short, qty}
             */
            products?: unknown[];
            /** Space Label */
            space_label?: string | null;
            /** Style */
            style?: ("photo" | "minimal_3d" | "illustration") | null;
        } & {
            [key: string]: unknown;
        };
        /** RequestStarted */
        RequestStarted: {
            /**
             * Conditions Route
             * @description IMG2 경로 /image/w/{id}/conditions(장면 설명 · 제품 · 비율 미리 채움)
             */
            conditions_route: string;
            request: components["schemas"]["ImageRequest"];
            /**
             * Route
             * @description IMG1(미리 채움) 경로 /image/new?work=…
             */
            route: string;
            /** Work Id */
            work_id: string;
        };
        /** RevertResult */
        RevertResult: {
            /** Current Version Id */
            current_version_id: string;
            region: components["schemas"]["EditRegion"];
        };
        /** RunAccepted */
        RunAccepted: {
            /** Job Id */
            job_id: string;
            precheck: components["schemas"]["Precheck"];
            /** Run Id */
            run_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "awaiting_input" | "succeeded" | "failed" | "canceled";
        };
        /** RunBrief */
        RunBrief: {
            /**
             * Done
             * @default 0
             */
            done: number;
            /**
             * Held
             * @default 0
             */
            held: number;
            /** Id */
            id: string;
            /** Job Id */
            job_id?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "initial" | "composite" | "alternatives" | "variants" | "edit" | "adjust" | "renditions" | "render_api";
            /**
             * Route
             * @default
             */
            route: string;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "awaiting_input" | "succeeded" | "failed" | "canceled";
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** RunCancelResult */
        RunCancelResult: {
            /** Run Id */
            run_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "awaiting_input" | "succeeded" | "failed" | "canceled";
        };
        /** RunCreate */
        RunCreate: {
            /** Count */
            count?: (2 | 4) | null;
            /**
             * Kind
             * @default initial
             * @enum {string}
             */
            kind: "initial" | "composite" | "alternatives";
            /**
             * Notify
             * @default true
             */
            notify: boolean;
        };
        /** RunDetail */
        RunDetail: {
            /** Applied Note */
            applied_note?: string | null;
            /** Base Image Id */
            base_image_id?: string | null;
            /**
             * Change Note
             * @description 보류 없이 바꿔 만든 경우 IMG3 띠 「요청 중 {k}가지를 바꿔서 만들었어요」
             */
            change_note?: string | null;
            /** Created At */
            created_at: string;
            /** Done */
            done: number;
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            /**
             * Eta Label
             * @default
             */
            eta_label: string;
            /** Eta S */
            eta_s?: number | null;
            /** Finished At */
            finished_at?: string | null;
            /**
             * Head
             * @description 「생성 중 · 1 / 4 완료」 · 「대기 중 · 앞에 1건」
             * @default
             */
            head: string;
            /**
             * Held
             * @default 0
             */
            held: number;
            /** Id */
            id: string;
            /** Issues */
            issues?: components["schemas"]["PolicyIssue"][];
            /** Job Id */
            job_id?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "initial" | "composite" | "alternatives" | "variants" | "edit" | "adjust" | "renditions" | "render_api";
            /**
             * Notify
             * @default true
             */
            notify: boolean;
            /** Params */
            params?: {
                [key: string]: unknown;
            };
            /** Queue Ahead */
            queue_ahead?: number | null;
            /**
             * Route
             * @default
             */
            route: string;
            /** Shots */
            shots: components["schemas"]["Shot"][];
            /** Stages */
            stages: components["schemas"]["Stage"][];
            /** Started At */
            started_at?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "awaiting_input" | "succeeded" | "failed" | "canceled";
            /**
             * Summary Line
             * @default
             */
            summary_line: string;
            /** Title */
            title: string;
            /** Total */
            total: number;
            /** Work Id */
            work_id: string;
        };
        /** RunList */
        RunList: {
            /** Items */
            items: components["schemas"]["RunDetail"][];
        };
        /** RunPatch */
        RunPatch: {
            /** Notify */
            notify: boolean;
        };
        /** SaveResult */
        SaveResult: {
            /** Image Id */
            image_id: string;
            /** Saved */
            saved: boolean;
        };
        /** Scale */
        Scale: {
            /**
             * Method
             * @default none
             * @enum {string}
             */
            method: "ref_dim" | "std_object" | "none";
            /** Mm Per Px */
            mm_per_px?: number | null;
        };
        /** Scene */
        Scene: {
            /** Products */
            products?: string[];
            /** Space */
            space?: string | null;
        };
        /** SceneObject */
        SceneObject: {
            /** Bbox */
            bbox: number[];
            /** Label */
            label: string;
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
        /** Shot */
        Shot: {
            /** Aspect */
            aspect: string;
            /** Error */
            error?: string | null;
            /** Eta S */
            eta_s?: number | null;
            /** Expected S */
            expected_s?: number | null;
            /** Height */
            height?: number | null;
            /** Image Id */
            image_id: string;
            /** Index */
            index: number;
            /** Label */
            label: string;
            /** Layout Note */
            layout_note?: string | null;
            /** Letter */
            letter?: string | null;
            /** Preview Url */
            preview_url?: string | null;
            /**
             * Progress
             * @description 0..100(추정)
             * @default 0
             */
            progress: number;
            /**
             * Qc Flag
             * @default false
             */
            qc_flag: boolean;
            /** Qc Reason */
            qc_reason?: string | null;
            /**
             * Stage Label
             * @default
             */
            stage_label: string;
            /** Started At */
            started_at?: string | null;
            /**
             * State
             * @enum {string}
             */
            state: "waiting" | "composing" | "rendering" | "qc" | "done" | "held" | "canceled" | "failed";
            /** Thumb Url */
            thumb_url?: string | null;
            /** Url */
            url?: string | null;
            /**
             * Wait For
             * @description 대기 카드 「시안 {j}가 끝나면 시작해요」
             */
            wait_for?: string | null;
            /** Width */
            width?: number | null;
        };
        /** ShotCancelResult */
        ShotCancelResult: {
            /** Image Id */
            image_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "waiting" | "composing" | "rendering" | "qc" | "done" | "held" | "canceled" | "failed";
        };
        /** SitePhoto */
        SitePhoto: {
            /** Created At */
            created_at: string;
            /** File Id */
            file_id: string;
            /** Floor Line */
            floor_line?: number | null;
            /** Height */
            height?: number | null;
            /** Id */
            id: string;
            /** Job Id */
            job_id?: string | null;
            /** Label */
            label: string;
            /**
             * Message
             * @description W 문구(인식 결과)
             */
            message?: string | null;
            /** Objects */
            objects?: components["schemas"]["SceneObject"][];
            quality?: components["schemas"]["PhotoQuality"] | null;
            /**
             * Status
             * @enum {string}
             */
            status: "recognizing" | "recognized" | "low_light" | "failed" | "manual";
            /** Status Label */
            status_label: string;
            /** Surfaces */
            surfaces?: components["schemas"]["Surface"][];
            /** Thumb Url */
            thumb_url: string;
            /** Url */
            url: string;
            /** Width */
            width?: number | null;
            /** Work Id */
            work_id: string;
        };
        /** SitePhotoAccepted */
        SitePhotoAccepted: {
            /** Job Id */
            job_id: string;
            photo: components["schemas"]["SitePhoto"];
            /** Photo Id */
            photo_id: string;
            /**
             * Status
             * @default queued
             * @constant
             */
            status: "queued";
        };
        /** SitePhotoIn */
        SitePhotoIn: {
            /** File Id */
            file_id: string;
        };
        /** SitePhotoList */
        SitePhotoList: {
            /** Items */
            items: components["schemas"]["SitePhoto"][];
        };
        /** Stage */
        Stage: {
            /**
             * Key
             * @enum {string}
             */
            key: "product_fit" | "compose" | "render" | "qc";
            /** Label */
            label: string;
            /**
             * State
             * @enum {string}
             */
            state: "done" | "now" | "todo";
        };
        /** Surface */
        Surface: {
            /**
             * Installable
             * @default true
             */
            installable: boolean;
            /**
             * Kind
             * @default wall
             * @enum {string}
             */
            kind: "wall" | "counter" | "ceiling" | "floor" | "other";
            /** Label */
            label: string;
            /** Quad */
            quad: number[][];
        };
        /** T2ICapFlags */
        T2ICapFlags: {
            /**
             * Available
             * @default true
             */
            available: boolean;
            /** Images Per Call */
            images_per_call: number;
            /** Max Reference Images */
            max_reference_images: number;
            /** Max Side Px */
            max_side_px: number;
            /** Supports Edit */
            supports_edit: boolean;
            /** Supports Mask */
            supports_mask: boolean;
            /** Supports Reference Images */
            supports_reference_images: boolean;
        };
        /** Totals */
        Totals: {
            /** Images */
            images: number;
            /** Works */
            works: number;
        };
        /** Usage */
        Usage: {
            /** Created At */
            created_at: string;
            /** Image Id */
            image_id: string;
            /**
             * Label
             * @default
             */
            label: string;
            /** Ref */
            ref: string;
            /**
             * Service
             * @enum {string}
             */
            service: "proposal" | "scenario" | "birdseye";
            /** Version Id */
            version_id: string;
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
            /**
             * Service
             * @enum {string}
             */
            service: "proposal" | "scenario" | "birdseye";
            /** Version Id */
            version_id: string;
        };
        /** VariantsIn */
        VariantsIn: {
            /**
             * Axis
             * @default any
             * @enum {string}
             */
            axis: "any" | "lighting" | "people";
            /**
             * Count
             * @default 4
             */
            count: number;
            /** Instruction */
            instruction?: string | null;
        };
        /** Version */
        Version: {
            /** Created At */
            created_at: string;
            /** Generation */
            generation?: {
                [key: string]: unknown;
            };
            /** Height */
            height: number;
            /** Id */
            id: string;
            /** Image Id */
            image_id: string;
            /**
             * Is Current
             * @default false
             */
            is_current: boolean;
            /**
             * Label
             * @description 수정 기록 라벨(원본 · 수정 1 · 영역 1 · 보정 1 …)
             */
            label: string;
            /** Master File Id */
            master_file_id: string;
            /** N */
            n: number;
            /** Native */
            native?: {
                [key: string]: unknown;
            };
            /**
             * Op
             * @enum {string}
             */
            op: "generate" | "composite" | "edit_region" | "edit_global" | "adjust" | "variant" | "aspect" | "upscale" | "restore";
            /** Op Params */
            op_params?: {
                [key: string]: unknown;
            };
            /** Parent Version Id */
            parent_version_id?: string | null;
            /** Qc */
            qc?: {
                [key: string]: unknown;
            };
            /** Renditions */
            renditions?: components["schemas"]["Rendition"][];
            /**
             * Short Label
             * @description 전/후 비교 라벨(원본 · 수정 1 · 보정 1)
             * @default
             */
            short_label: string;
            /** Thumb Url */
            thumb_url: string;
            /**
             * Title
             * @description IMG4 제목(시안 1 · 부분 수정본 v2)
             */
            title: string;
            /** Url */
            url: string;
            /** Width */
            width: number;
        };
        /** VersionList */
        VersionList: {
            /** Items */
            items: components["schemas"]["Version"][];
        };
        /** Work */
        Work: {
            /** Active Runs */
            active_runs?: components["schemas"]["RunBrief"][];
            badge: components["schemas"]["Badge"];
            composite?: components["schemas"]["CompositeState"] | null;
            conditions: components["schemas"]["Conditions"];
            /** Created At */
            created_at: string;
            /** Customer Name */
            customer_name?: string | null;
            /** Customer Short */
            customer_short?: string | null;
            /**
             * Description
             * @default
             */
            description: string;
            /**
             * Echo
             * @description 사용자 입력 메아리 「공간 · 카페 카운터 …」
             * @default
             */
            echo: string;
            /** Id */
            id: string;
            /**
             * Image Count
             * @default 0
             */
            image_count: number;
            /**
             * Kind
             * @enum {string}
             */
            kind: "space" | "background" | "scenario" | "composite";
            /** Kind Label */
            kind_label: string;
            /** Last Export */
            last_export?: {
                [key: string]: unknown;
            } | null;
            latest_run?: components["schemas"]["RunBrief"] | null;
            origin?: components["schemas"]["Origin"] | null;
            /** Owner */
            owner: string;
            prefill?: components["schemas"]["PrefillState"] | null;
            /** Project Id */
            project_id?: string | null;
            /**
             * Ref Notice
             * @description 「이미지 검색에서 선택한 2장이 참조로 들어갔습니다」
             */
            ref_notice?: string | null;
            /** References */
            references?: components["schemas"]["Reference"][];
            /** Route */
            route: string;
            /** Selected Image Id */
            selected_image_id?: string | null;
            /**
             * Start
             * @default type
             * @enum {string}
             */
            start: "type" | "references" | "composite";
            /**
             * Status
             * @enum {string}
             */
            status: "draft" | "queued" | "running" | "awaiting_input" | "done" | "failed" | "canceled";
            /** Subject Short */
            subject_short?: string | null;
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
            /**
             * Version
             * @description 사용자 편집 판(PATCH if_version)
             */
            version: number;
        };
        /** WorkCreate */
        WorkCreate: {
            /** Customer Name */
            customer_name?: string | null;
            /** Description */
            description?: string | null;
            /** Kind */
            kind?: ("space" | "background" | "scenario" | "composite") | null;
            /** Project Id */
            project_id?: string | null;
            /** Reference Items */
            reference_items?: components["schemas"]["ReferenceIn"][] | null;
            /** Request Id */
            request_id?: string | null;
            /**
             * Start
             * @default type
             * @enum {string}
             */
            start: "type" | "references" | "composite";
            /** Title */
            title?: string | null;
        };
        /** WorkList */
        WorkList: {
            /** Items */
            items: components["schemas"]["WorkRow"][];
            /** Next Cursor */
            next_cursor?: string | null;
            totals: components["schemas"]["Totals"];
        };
        /** WorkPatch */
        WorkPatch: {
            conditions?: components["schemas"]["Conditions"] | null;
            /** Customer Name */
            customer_name?: string | null;
            /** Description */
            description?: string | null;
            /** If Version */
            if_version?: number | null;
            /** Kind */
            kind?: ("space" | "background" | "scenario" | "composite") | null;
            /** Selected Image Id */
            selected_image_id?: string | null;
            /** Title */
            title?: string | null;
        };
        /** WorkRow */
        WorkRow: {
            /** Customer Short */
            customer_short?: string | null;
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "space" | "background" | "scenario" | "composite";
            /**
             * Meta
             * @description `{고객사} · {유형} · {장수}`
             */
            meta: string;
            /** Route */
            route: string;
            run?: components["schemas"]["RunBrief"] | null;
            status: components["schemas"]["Badge"];
            /** Thumb Url */
            thumb_url?: string | null;
            /**
             * Time
             * @description 상대 시각(방금 · N분 전 …)
             */
            time: string;
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
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
    get_capabilities: {
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
                    "application/json": components["schemas"]["ExportOut"];
                };
            };
        };
    };
    list_images: {
        parameters: {
            query?: {
                aspect?: string | null;
                cursor?: string | null;
                customer?: string | null;
                in_proposal?: boolean | null;
                kind?: string | null;
                limit?: number;
                mine?: boolean;
                origin?: string;
                /** @description me = 내 이미지 */
                owner?: string | null;
                q?: string | null;
                /** @description 생성 중 타일 포함(기본: owner=me 면 제외) */
                running?: boolean | null;
                saved?: boolean | null;
                sort?: "created_desc";
                work_id?: string | null;
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
                    "application/json": components["schemas"]["ImageList"];
                };
            };
        };
    };
    bulk_export: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BulkExportIn"];
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
                    "application/json": components["schemas"]["ExportOut"];
                };
            };
        };
    };
    get_image: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImageDetail"];
                };
            };
        };
    };
    interpret: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InterpretIn"];
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
                    "application/json": components["schemas"]["InterpretResult"];
                };
            };
        };
    };
    save_image: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SaveResult"];
                };
            };
        };
    };
    adjust_image: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AdjustIn"];
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
                    "application/json": components["schemas"]["Version"];
                };
            };
        };
    };
    make_caption: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CaptionResult"];
                };
            };
        };
    };
    detect: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
            };
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
                    "application/json": components["schemas"]["Detections"];
                };
            };
        };
    };
    start_edit: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EditIn"];
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
    export_image: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
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
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExportOut"];
                };
            };
            /** @description export 서비스 잡(PDF · PPTX · ZIP) */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExportOut"];
                };
            };
        };
    };
    make_filename: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FilenameIn"];
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
                    "application/json": components["schemas"]["FilenameResult"];
                };
            };
        };
    };
    get_image_info: {
        parameters: {
            query?: {
                version_id?: string | null;
            };
            header?: never;
            path: {
                image_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImageInfo"];
                };
            };
        };
    };
    list_regions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RegionList"];
                };
            };
        };
    };
    create_region: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RegionIn"];
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
                    "application/json": components["schemas"]["RegionCreated"];
                };
            };
        };
    };
    delete_region: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
                region_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
    patch_region: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
                region_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RegionPatch"];
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
                    "application/json": components["schemas"]["EditRegion"];
                };
            };
        };
    };
    revert_region: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
                region_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
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
    start_renditions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RenditionsIn"];
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
    add_usage: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
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
    delete_usage: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
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
    start_variants: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VariantsIn"];
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
    list_versions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
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
                image_id: string;
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
                    "application/json": components["schemas"]["Version"];
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
    get_queue: {
        parameters: {
            query?: {
                mine?: boolean;
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
                    "application/json": components["schemas"]["QueueList"];
                };
            };
        };
    };
    reference_search: {
        parameters: {
            query?: {
                cursor?: string | null;
                industry?: string | null;
                limit?: number;
                q?: string | null;
                style?: "all" | "photo" | "illustration";
                tab?: "kb" | "mine" | "cases";
                work_id?: string | null;
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
                    "application/json": components["schemas"]["RefSearch"];
                };
            };
        };
    };
    create_render: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RenderIn"];
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
                    "application/json": components["schemas"]["RenderAccepted"];
                };
            };
        };
    };
    get_render: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                render_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RenderOut"];
                };
            };
        };
    };
    cancel_render: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                render_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
                    "application/json": components["schemas"]["RenderOut"];
                };
            };
        };
    };
    list_requests: {
        parameters: {
            query?: {
                from_ref?: string | null;
                from_service?: string | null;
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
                    "application/json": components["schemas"]["RequestList"];
                };
            };
        };
    };
    create_request: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RequestIn"];
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
                    "application/json": components["schemas"]["ImageRequest"];
                };
            };
        };
    };
    get_request: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                request_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImageRequest"];
                };
            };
        };
    };
    dismiss_request: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                request_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImageRequest"];
                };
            };
        };
    };
    fulfill_request: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                request_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FulfillIn"];
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
                    "application/json": components["schemas"]["ImageRequest"];
                };
            };
        };
    };
    start_request: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                request_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RequestStarted"];
                };
            };
        };
    };
    get_run: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunDetail"];
                };
            };
        };
    };
    patch_run: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RunPatch"];
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
                    "application/json": components["schemas"]["RunDetail"];
                };
            };
        };
    };
    cancel_run: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
                    "application/json": components["schemas"]["RunCancelResult"];
                };
            };
        };
    };
    custom_alternative: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AlternativeIn"];
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
                    "application/json": components["schemas"]["AlternativeResult"];
                };
            };
        };
    };
    answer_run: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AnswersIn"];
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
                    "application/json": components["schemas"]["AnswersAccepted"];
                };
            };
        };
    };
    cancel_shot: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                image_id: string;
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShotCancelResult"];
                };
            };
        };
    };
    get_version: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                version_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Version"];
                };
            };
        };
    };
    list_works: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
                q?: string | null;
                sort?: "updated_desc";
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
                    "application/json": components["schemas"]["WorkList"];
                };
            };
        };
    };
    create_work: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WorkCreate"];
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
                    "application/json": components["schemas"]["Work"];
                };
            };
        };
    };
    get_work: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                work_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Work"];
                };
            };
        };
    };
    delete_work: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                work_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
    patch_work: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                work_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WorkPatch"];
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
                    "application/json": components["schemas"]["Work"];
                };
            };
        };
    };
    prefill_work: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                work_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Prefill"];
                };
            };
        };
    };
    put_placements: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                work_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlacementsIn"];
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
                    "application/json": components["schemas"]["PlacementResult"];
                };
            };
        };
    };
    add_products: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                work_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProductsAdd"];
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
                    "application/json": components["schemas"]["ProductsAdded"];
                };
            };
        };
    };
    list_references: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                work_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReferenceList"];
                };
            };
        };
    };
    set_references: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                work_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReferenceSet"];
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
                    "application/json": components["schemas"]["ReferenceList"];
                };
            };
        };
    };
    add_reference: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                work_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReferenceIn"];
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
                    "application/json": components["schemas"]["Reference"];
                };
            };
        };
    };
    delete_reference: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                ref_id: string;
                work_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
    patch_reference: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                ref_id: string;
                work_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReferencePatch"];
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
                    "application/json": components["schemas"]["Reference"];
                };
            };
        };
    };
    list_runs: {
        parameters: {
            query?: {
                active?: boolean;
                kind?: string | null;
            };
            header?: never;
            path: {
                work_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunList"];
                };
            };
        };
    };
    create_run: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                work_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RunCreate"];
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
                    "application/json": components["schemas"]["RunAccepted"];
                };
            };
        };
    };
    list_site_photos: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                work_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SitePhotoList"];
                };
            };
        };
    };
    add_site_photo: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                work_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SitePhotoIn"];
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
                    "application/json": components["schemas"]["SitePhotoAccepted"];
                };
            };
        };
    };
    delete_site_photo: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                photo_id: string;
                work_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
    recognize_site_photo: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                photo_id: string;
                work_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
                    "application/json": components["schemas"]["SitePhotoAccepted"];
                };
            };
        };
    };
}
