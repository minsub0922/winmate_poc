// 자동 생성 — 직접 고치지 말 것. 원본: contracts/scenario.json (make contracts)
export interface paths {
    "/v1/birdseye-options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Birdseye Options
         * @description SC1 「조감도 작업 {n}개에서 고르기」 · SC1B 「조감도 작업」 목록(조감도 서비스 목록을 칩 표시용으로).
         */
        get: operations["birdseye_options"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/birdseye-options/{be_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Birdseye Preview
         * @description SC1B: 존 행(제품 · 가구만 · 없음 → 기본 포함/제외) · 평면 미리보기 · 시나리오 축 3(LLM, 첫째 기본) · 동선 순서.
         */
        get: operations["birdseye_preview"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/image-returns": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Image Return
         * @description IMG4 「공간 시나리오 장면으로」 → `/scenario?image_version=imv_…&request=irq_…`: 그 요청을 낸 장면을 찾아 붙이고 SC4E 경로를 준다.
         */
        post: operations["image_return"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/industries": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Industries */
        get: operations["industries"];
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
    "/v1/product-search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Product Search */
        get: operations["product_search"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Scenarios */
        get: operations["list_scenarios"];
        put?: never;
        /** Create Scenario */
        post: operations["create_scenario"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios:from-birdseye": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** From Birdseye */
        post: operations["from_birdseye"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios:from-template": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** From Template */
        post: operations["from_template"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Scenario */
        get: operations["get_scenario"];
        put?: never;
        post?: never;
        /** Delete Scenario */
        delete: operations["delete_scenario"];
        options?: never;
        head?: never;
        /** Patch Scenario */
        patch: operations["patch_scenario"];
        trace?: never;
    };
    "/v1/scenarios/{sc_id}:clone": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Clone Scenario */
        post: operations["clone_scenario"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}:edit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Edit Request
         * @description SC4 「수정 요청」 → LLM 시나리오 연산 → 영향 장면만 다시 쓰기(화면 이동 없음).
         */
        post: operations["edit_request"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}:route-generate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Route Generate
         * @description SC3 「시나리오 생성」: WITHOUT 인데 솔루션이 필요한 장면이 있거나 WITH 인데 솔루션 0개 → SC3R, 그 밖 → SC4G.
         *     조감도 추가 「새로 만들기」면 이때 조감도 초안을 만든다(공간 · 제품이 정해진 뒤, 한 번만).
         */
        post: operations["route_generate"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}:save": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Save Scenario */
        post: operations["save_scenario"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}:shorten": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Shorten */
        post: operations["shorten"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/alerts:dismiss": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Dismiss Alert
         * @description SC0 조감도 변경 알림 닫기 — 같은 변경(조감도 · 버전)은 다시 보이지 않는다(연결된 시나리오 모두).
         */
        post: operations["dismiss_alert"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/birdseye:resync": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Birdseye Resync */
        post: operations["birdseye_resync"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/characters:extract": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Extract Characters
         * @description 입력이 멈추고 1초 뒤(웹) — LLM 이 문장에서 역할을 뽑는다(제한 5초, 실패하면 등장인물 사전). 사용자가 지운 역할은 빼고 준다.
         */
        post: operations["extract_characters"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/exports": {
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
    "/v1/scenarios/{sc_id}/exports/{export_id}": {
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
    "/v1/scenarios/{sc_id}/generate": {
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
    "/v1/scenarios/{sc_id}/generate:cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Generate Cancel
         * @description 「중지 · 입력 고치기」: 잡 취소 → 끝난 장면은 done 으로 남기고 SC3 으로(status draft, step 3).
         */
        post: operations["generate_cancel"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/generate:resume": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Generate Resume
         * @description 실패한 생성 다시 시도 — 같은 thread(job_id)로 재개, 끝난 장면은 다시 쓰지 않는다.
         */
        post: operations["generate_resume"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/generation": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Generation View */
        get: operations["generation_view"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/handoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Handoff
         * @description 제안서용 묶음(§8) — version 을 주면 그 저장 버전, 없으면 최신(저장 안 한 변경이 있으면 작업본).
         */
        get: operations["handoff"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/images:generate-missing": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Images Generate Missing
         * @description 「장면별 이미지 모두 생성」: 이미지 없는 장면마다 렌더 API 로 1장씩(동시 1, 16:9 · fhd), 끝날 때마다 붙임.
         */
        post: operations["images_generate_missing"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/images:sync": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Images Sync
         * @description SC4 · SC4E 를 열 때: 장면마다 image 요청이 충족(fulfilled)됐고 아직 안 붙었으면 붙인다.
         */
        post: operations["images_sync"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/imports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Import Work
         * @description 사이드바 작업 항목 끌어오기: 조감도 → handoff 공간 · 제품 「[공간] …」 줄 + birdseye_link(연결 유지 끔), Storyboard → 고객 · 공간 줄.
         */
        post: operations["import_work"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/input:parse": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Parse Input */
        post: operations["parse_input"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/products": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Products */
        put: operations["put_products"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/proposal-handoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Proposal Handoff
         * @description 10-proposal §8.0 ProposalHandoff v1(N1) — 공간별 장면(시간 · 문장 · 이미지) · 장면별 솔루션 · 제품 · 공간 × 솔루션 표.
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
    "/v1/scenarios/{sc_id}/recommendations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Recommendations */
        get: operations["get_recommendations"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/recommendations:apply-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Apply All */
        post: operations["apply_all"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/recommendations:commit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Commit Recommendations
         * @description apply: 켠 추천 → 솔루션 칸 · 장면별 동작(끈 장면은 제품만), 적용 ≥ 1 이면 유형 with. products_only: 유형 WITHOUT · 솔루션 없음.
         */
        post: operations["commit_recommendations"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/recommendations:compute": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Compute Recommendations */
        post: operations["compute_recommendations"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/recommendations/{scene_id}": {
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
        /** Patch Recommendation */
        patch: operations["patch_recommendation"];
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/roles/{role_id}": {
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
         * Patch Role
         * @description 페르소나 저장 — 소개 · 원하는 것 · 불편한 점이 바뀌면 그 레인 비트 문장 재작성 잡(응답 job_id).
         */
        patch: operations["patch_role"];
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/scenes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Scenes */
        get: operations["list_scenes"];
        put?: never;
        /**
         * Add Scene
         * @description SC4E 「장면 추가」: 현재 장면 다음 시간대에 빈 장면(다음 시간대가 없으면 새 시간대).
         */
        post: operations["add_scene"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/share": {
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
         * @description 「팀에 공유」 — workspace 보기 링크.
         */
        post: operations["share"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/sheet-plan": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Sheet Plan
         * @description §7.9 시트 구성(결정적) — 장면을 공간 기준으로 묶어 맵 시트 + 공간 시트.
         */
        get: operations["sheet_plan"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/solutions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Put Solutions */
        put: operations["put_solutions"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/timeline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Timeline */
        get: operations["get_timeline"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/timeline:nl-edit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Timeline Nl Edit */
        post: operations["timeline_nl_edit"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/timeline:text": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Timeline Text */
        get: operations["timeline_text"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/timeline/ops": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Timeline Ops
         * @description 편집 즉시 저장(되돌리기 50단계). undo · redo 는 ops 없이.
         */
        post: operations["timeline_ops"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/usages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Usage
         * @description 제안서가 묶음을 읽어 넣은 뒤 등록 → SC0 「제안서에 사용 중」.
         */
        post: operations["add_usage"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenarios/{sc_id}/usages/{service_name}/{ref}": {
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
    "/v1/scenarios/{sc_id}/versions": {
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
    "/v1/scenarios/{sc_id}/versions/{n}/restore": {
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
    "/v1/scenes/{scene_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Scene */
        get: operations["get_scene"];
        put?: never;
        post?: never;
        /**
         * Delete Scene
         * @description 장면 삭제 — 번호가 다시 매겨지고 시트 계획이 다시 계산된다(시트 계획은 읽을 때 계산).
         */
        delete: operations["delete_scene"];
        options?: never;
        head?: never;
        /**
         * Patch Scene
         * @description 「변경 저장」: 직접 고친 필드가 있으면 locked=true · 새 버전(「직접 수정」).
         */
        patch: operations["patch_scene"];
        trace?: never;
    };
    "/v1/scenes/{scene_id}:rewrite": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Rewrite Scene
         * @description 「이 장면만 다시 쓰기」 — 다른 장면은 그대로, 새 버전(v+1).
         */
        post: operations["rewrite_scene"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenes/{scene_id}/image-prefill": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Image Prefill */
        get: operations["image_prefill"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenes/{scene_id}/image-request": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Image Request
         * @description 「이미지 생성」: image 요청 + :start(대리) → 웹이 IMG2(미리 채움)로 이동. 충족되면 SC4 · SC4E 를 열 때 붙는다.
         */
        post: operations["image_request"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenes/{scene_id}/image:attach": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Image Attach
         * @description 고르기 모드(사내 자산 · 내 이미지) · 요청 충족 결과를 장면에 붙인다(조건 스냅숏 저장 → stale 판정).
         */
        post: operations["image_attach"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenes/{scene_id}/versions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Scene Versions */
        get: operations["scene_versions"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/scenes/{scene_id}/versions/{n}/restore": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Restore Scene Version
         * @description 「v{k-1}로 되돌리기」: v{n} 내용으로 새 버전(지난 버전은 남는다).
         */
        post: operations["restore_scene_version"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/skeletons": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Skeletons */
        get: operations["skeletons"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/solution-actions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Solution Actions */
        get: operations["solution_actions"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/solution-search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Solution Search
         * @description 「솔루션 입력」 자동완성: KB 솔루션 카탈로그(Winmate 솔루션 11개) + 동작 사전 솔루션.
         */
        get: operations["solution_search"];
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
        /** ActionItem */
        ActionItem: {
            /** Action Code */
            action_code: string;
            /** Benefit */
            benefit: string;
            /** Label */
            label: string;
            /** Solution Id */
            solution_id: string;
            /** Solution Name */
            solution_name: string;
        };
        /** ActionList */
        ActionList: {
            /** Items */
            items: components["schemas"]["ActionItem"][];
        };
        /** ActiveJob */
        ActiveJob: {
            /** Job Id */
            job_id: string;
            /** Kind */
            kind: string;
            /** Scene Id */
            scene_id?: string | null;
        };
        /** AddSceneRequest */
        AddSceneRequest: {
            /** After Scene Id */
            after_scene_id?: string | null;
            /** Title */
            title?: string | null;
        };
        /** Aerial */
        Aerial: {
            /** Birdseye Id */
            birdseye_id?: string | null;
            /**
             * Created
             * @default false
             */
            created: boolean;
            /**
             * Enabled
             * @default false
             */
            enabled: boolean;
            /**
             * Source
             * @default new
             * @enum {string}
             */
            source: "new" | "existing";
            /** Title */
            title?: string | null;
        };
        /** AttachImage */
        AttachImage: {
            /**
             * Image Ref
             * @description 셸 이미지 참조 — img:image:<id>(내 이미지 · 현재 버전) · kb:image:<id>(사내 자산)
             */
            image_ref?: string | null;
            /**
             * Image Version Id
             * @description image 서비스 버전(imv_…) — 없으면 image_ref 로
             */
            image_version_id?: string | null;
            /** Request Id */
            request_id?: string | null;
            /**
             * Source
             * @default picked
             * @enum {string}
             */
            source: "image_render" | "image_flow" | "picked";
        };
        /** Beat */
        Beat: {
            /** Id */
            id: string;
            /**
             * Label
             * @description 「장면 {n}」 · 「장면 {n} · {역할} 시점」 · 「새 장면」
             * @default
             */
            label: string;
            /**
             * Place
             * @default
             */
            place: string;
            /**
             * Primary
             * @default false
             */
            primary: boolean;
            /** Role Id */
            role_id?: string | null;
            /** Text */
            text: string;
        };
        /** BirdseyeAlert */
        BirdseyeAlert: {
            /** Birdseye Id */
            birdseye_id: string;
            /** Changed At */
            changed_at: string;
            /**
             * Changed Label
             * @description 「9월 30일」
             */
            changed_label: string;
            /** Scenario Ids */
            scenario_ids: string[];
            /** Title */
            title: string;
            /** Version */
            version?: number | null;
        };
        /** BirdseyeLink */
        BirdseyeLink: {
            /** Axis */
            axis?: string | null;
            /** Birdseye Id */
            birdseye_id: string;
            /**
             * Changed
             * @description {at, version} — 연결 유지한 조감도가 바뀌었을 때
             */
            changed?: {
                [key: string]: unknown;
            } | null;
            /**
             * Keep Link
             * @default false
             */
            keep_link: boolean;
            /** Layout Version */
            layout_version?: number | null;
            /** Linked Version */
            linked_version?: number | null;
            /** Order */
            order?: string[];
            /**
             * Title
             * @default
             */
            title: string;
            /** Zone Ids */
            zone_ids?: string[];
            /** Zones Hash */
            zones_hash?: string | null;
        };
        /** BirdseyeOption */
        BirdseyeOption: {
            /** Id */
            id: string;
            /**
             * Label
             * @description 「{제목} · 존 {k}」
             */
            label: string;
            /** Title */
            title: string;
            /**
             * Zone Count
             * @default 0
             */
            zone_count: number;
        };
        /** BirdseyeOptions */
        BirdseyeOptions: {
            /**
             * Available
             * @default true
             */
            available: boolean;
            /**
             * Count
             * @default 0
             */
            count: number;
            /** Items */
            items: components["schemas"]["BirdseyeOption"][];
        };
        /** BirdseyePreview */
        BirdseyePreview: {
            /** Axes */
            axes: string[];
            /** Birdseye Id */
            birdseye_id: string;
            /** Order */
            order?: string[];
            /**
             * Plan
             * @description plan_preview — 존 포인트 n · 평 · 층고 · 창 라벨 · 존 위치
             */
            plan?: {
                [key: string]: unknown;
            };
            resync?: components["schemas"]["ResyncResult"] | null;
            /** Title */
            title: string;
            /** Version */
            version?: number | null;
            /** Zones */
            zones: components["schemas"]["ZoneRow"][];
        };
        /** Characters */
        Characters: {
            /** Characters */
            characters: string[];
            /**
             * Source
             * @default llm
             * @enum {string}
             */
            source: "llm" | "dictionary";
        };
        /** CloneResult */
        CloneResult: {
            /** Id */
            id: string;
            /** Route */
            route: string;
        };
        /** CommitRecommendations */
        CommitRecommendations: {
            /**
             * Mode
             * @enum {string}
             */
            mode: "apply" | "products_only";
        };
        /** ConfirmToken */
        ConfirmToken: {
            /**
             * Kind
             * @default number
             */
            kind: string;
            /**
             * Near
             * @default
             */
            near: string;
            /**
             * Text
             * @default [00]
             */
            text: string;
        };
        /** CreateScenario */
        CreateScenario: {
            aerial?: components["schemas"]["Aerial"] | null;
            /**
             * Customer Name
             * @description 다른 기능(MI4 `?mi=` · VP4 `?from=vp:`)에서 넘어온 고객사 — 프로젝트 · Storyboard 고객이 없을 때만 쓴다
             */
            customer_name?: string | null;
            /** Project Id */
            project_id?: string | null;
            /**
             * Storyboard Id
             * @description SB4 「공간 시나리오」 카드에서 넘어온 Storyboard(?sb=) — 공간 · 고객을 미리 채운다
             */
            storyboard_id?: string | null;
            /** Title */
            title?: string | null;
            /**
             * Type
             * @default with
             * @enum {string}
             */
            type: "with" | "without";
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
            /** Case Count */
            case_count?: number | null;
            /**
             * Case Text
             * @description 「· 카페 사례 [00]건」
             */
            case_text?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "input_quote" | "kb_message" | "kb_case" | "product_only";
            /** Ref */
            ref?: string | null;
            /** Source Url */
            source_url?: string | null;
            /**
             * Text
             * @default
             */
            text: string;
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
             */
            status: string;
        };
        /** ExportOut */
        ExportOut: {
            /** Created At */
            created_at: string;
            /** Error */
            error?: string | null;
            /** File Id */
            file_id?: string | null;
            /** File Name */
            file_name?: string | null;
            /** Id */
            id: string;
            /** Job Id */
            job_id?: string | null;
            /** Kind */
            kind: string;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "done" | "failed";
            /** Url */
            url?: string | null;
        };
        /** ExportRequest */
        ExportRequest: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "pptx" | "pdf" | "docx" | "zip";
        };
        /** ExtractRequest */
        ExtractRequest: {
            /**
             * Exclude
             * @description 사용자가 지운 역할(다시 넣지 않음)
             */
            exclude?: string[];
            /** Raw Text */
            raw_text: string;
        };
        /** FromBirdseye */
        FromBirdseye: {
            /** Axis */
            axis: string;
            /** Birdseye Id */
            birdseye_id: string;
            /**
             * Keep Link
             * @default true
             */
            keep_link: boolean;
            /** Order */
            order?: string[];
            /** Project Id */
            project_id?: string | null;
            /**
             * Type
             * @default with
             * @enum {string}
             */
            type: "with" | "without";
            /** Zone Ids */
            zone_ids: string[];
        };
        /** FromTemplate */
        FromTemplate: {
            /** Industry */
            industry: string;
            /**
             * Preset Index
             * @description 1부터
             * @default 1
             */
            preset_index: number;
            /** Project Id */
            project_id?: string | null;
            /**
             * Type
             * @default with
             * @enum {string}
             */
            type: "with" | "without";
        };
        /** GenerateRequest */
        GenerateRequest: {
            /** Scene Ids */
            scene_ids?: string[] | null;
            /**
             * Scope
             * @default all
             * @enum {string}
             */
            scope: "all" | "unlocked";
        };
        /** Generation */
        Generation: {
            /**
             * Done
             * @default 0
             */
            done: number;
            /** Failed Reason */
            failed_reason?: string | null;
            /** Job Id */
            job_id?: string | null;
            /**
             * Scope
             * @default all
             */
            scope: string;
            /**
             * Status
             * @default idle
             */
            status: string;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** GenerationView */
        GenerationView: {
            /**
             * Done
             * @default 0
             */
            done: number;
            /** Eta S */
            eta_s?: number | null;
            /**
             * Eta Text
             * @default
             */
            eta_text: string;
            /** Failed Reason */
            failed_reason?: string | null;
            /** Job Id */
            job_id?: string | null;
            /** Memos */
            memos?: string[];
            /**
             * Pct
             * @default 0
             */
            pct: number;
            /** Scenes */
            scenes: components["schemas"]["PreviewScene"][];
            /** Stages */
            stages: components["schemas"]["Stage"][];
            /** Status */
            status: string;
            /**
             * Streaming
             * @default true
             */
            streaming: boolean;
            /**
             * Summary
             * @description 「with 솔루션 · MagicINFO · SmartThings Pro · QM55C ×3 · KM24C」
             */
            summary: string;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** Handoff */
        Handoff: {
            /** Birdseye Link */
            birdseye_link?: {
                [key: string]: unknown;
            } | null;
            /** Confirm Items */
            confirm_items: {
                [key: string]: unknown;
            }[];
            /** Customer */
            customer?: string | null;
            /** Products */
            products: {
                [key: string]: unknown;
            }[];
            /** Roles */
            roles: {
                [key: string]: unknown;
            }[];
            /** Scenario Id */
            scenario_id: string;
            /** Scenes */
            scenes: {
                [key: string]: unknown;
            }[];
            /** Sheet Plan */
            sheet_plan: {
                [key: string]: unknown;
            }[];
            /** Slots */
            slots: {
                [key: string]: unknown;
            }[];
            /** Solutions */
            solutions: {
                [key: string]: unknown;
            }[];
            /** Title */
            title: string;
            /**
             * Type
             * @enum {string}
             */
            type: "with" | "without";
            /** Version */
            version: number;
        };
        /** ImageJob */
        ImageJob: {
            /** Error */
            error?: string | null;
            /** Render Id */
            render_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "failed" | "done";
        };
        /** ImagePrefill */
        ImagePrefill: {
            /**
             * Aspect
             * @default 16:9
             */
            aspect: string;
            /**
             * Aspect Label
             * @default 16:9 · 제안서 시트용
             */
            aspect_label: string;
            /**
             * Kind
             * @default scenario
             */
            kind: string;
            /** Product Line */
            product_line: string;
            /** Products */
            products: string[];
            /** Scene */
            scene: string;
            /** Space */
            space: string;
        };
        /** ImageRequestOut */
        ImageRequestOut: {
            /** Image Route */
            image_route: string;
            /** Request Id */
            request_id: string;
            /** Work Id */
            work_id?: string | null;
        };
        /** ImageReturn */
        ImageReturn: {
            /** Image Version Id */
            image_version_id: string;
            /** Request Id */
            request_id: string;
        };
        /** ImageReturnOut */
        ImageReturnOut: {
            /** Route */
            route: string;
            /** Scenario Id */
            scenario_id: string;
            /** Scene Id */
            scene_id: string;
        };
        /** ImagesSync */
        ImagesSync: {
            /** Attached */
            attached?: string[];
        };
        /** ImportRequest */
        ImportRequest: {
            /**
             * Feature
             * @enum {string}
             */
            feature: "birdseye" | "storyboard" | "BE" | "SB";
            /** Ref */
            ref: string;
        };
        /** ImportResult */
        ImportResult: {
            /** Append Text */
            append_text: string;
            birdseye_link?: components["schemas"]["BirdseyeLink"] | null;
            /** Customer Name */
            customer_name?: string | null;
        };
        /** Industry */
        Industry: {
            /**
             * Case Label
             * @default
             */
            case_label: string;
            /** Code */
            code: string;
            /** Name */
            name: string;
            /** Short */
            short: string;
        };
        /** IndustryList */
        IndustryList: {
            /**
             * Default Code
             * @default FB
             */
            default_code: string;
            /** Items */
            items: components["schemas"]["IndustryTemplate"][];
        };
        /** IndustryTemplate */
        IndustryTemplate: {
            /** Code */
            code: string;
            /** Name */
            name: string;
            /** Needs */
            needs: string[];
            /** Preset Line */
            preset_line: string;
            /** Presets */
            presets: components["schemas"]["Preset"][];
            /** Short */
            short: string;
            /** Space Line */
            space_line: string;
            /** Spaces */
            spaces: string[];
            /** Used */
            used: string[];
            /** Used Line */
            used_line: string;
        };
        /** Info */
        Info: {
            /** Service */
            service: string;
            /** Title */
            title: string;
            /** Version */
            version: string;
        };
        /** JobAccepted */
        JobAccepted: {
            /** Job Id */
            job_id: string;
            /**
             * Status
             * @default queued
             */
            status: string;
        };
        /** JobAcceptedWithScenario */
        JobAcceptedWithScenario: {
            /** Job Id */
            job_id: string;
            /** Scenario Id */
            scenario_id: string;
            /**
             * Status
             * @default queued
             */
            status: string;
        };
        /** ListCounts */
        ListCounts: {
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
             * Failed
             * @default 0
             */
            failed: number;
            /**
             * Generating
             * @default 0
             */
            generating: number;
        };
        /** Notices */
        Notices: {
            /**
             * Real Names
             * @default false
             */
            real_names: boolean;
            /** Too Many */
            too_many?: number | null;
        };
        /** ParseRequest */
        ParseRequest: {
            /** Characters */
            characters?: string[];
            /** Raw Text */
            raw_text: string;
        };
        /** ParseResult */
        ParseResult: {
            /**
             * Next
             * @enum {string}
             */
            next: "SC3" | "SC2E";
            /** Reason */
            reason?: string | null;
            /**
             * Scene Count
             * @default 0
             */
            scene_count: number;
        };
        /** PatchRecommendation */
        PatchRecommendation: {
            /** Applied */
            applied: boolean;
        };
        /** PatchRole */
        PatchRole: {
            /** Intro */
            intro?: string | null;
            /** Name */
            name?: string | null;
            /** Pains */
            pains?: string[] | null;
            /** Wants */
            wants?: string[] | null;
        };
        /** PatchScenario */
        PatchScenario: {
            aerial?: components["schemas"]["Aerial"] | null;
            /** Characters */
            characters?: string[] | null;
            /**
             * If Rev
             * @description 작업본 수정 번호 — 다르면 409 VERSION_CONFLICT
             */
            if_rev?: number | null;
            /** Raw Text */
            raw_text?: string | null;
            /** Removed Characters */
            removed_characters?: string[] | null;
            /** Step */
            step?: number | null;
            /** Title */
            title?: string | null;
            /** Type */
            type?: ("with" | "without") | null;
        };
        /** PatchScene */
        PatchScene: {
            /**
             * Characters
             * @description 역할 id 목록
             */
            characters?: string[] | null;
            /** If Version */
            if_version?: number | null;
            /** Products */
            products?: components["schemas"]["SceneProduct"][] | null;
            /** Solutions */
            solutions?: components["schemas"]["SceneSolution"][] | null;
            /** Story */
            story?: string | null;
            /** Title */
            title?: string | null;
        };
        /** Preset */
        Preset: {
            /** F */
            f: string;
            /** Flow */
            flow: string[];
            /**
             * N
             * @default 장면 4
             */
            n: string;
            /** R */
            r: string;
            /** Roles */
            roles: string[];
            /** T */
            t: string;
        };
        /** PreviewScene */
        PreviewScene: {
            /**
             * Beat Text
             * @default
             */
            beat_text: string;
            /** Chips */
            chips?: string[];
            /** Id */
            id: string;
            /** Label */
            label: string;
            /** No */
            no: number;
            /** Partial Story */
            partial_story?: string | null;
            /** Product Chips */
            product_chips?: string[];
            /**
             * Status
             * @enum {string}
             */
            status: "waiting" | "writing" | "done" | "failed";
            /** Time */
            time?: string | null;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** ProductItem */
        ProductItem: {
            /** Family Id */
            family_id?: string | null;
            /**
             * Label
             * @description 없으면 셸 참조(kb:model:… · kb:family:…)로 KB 에서 이름을 찾는다(팝오버 「현재 작업에 추가」)
             */
            label?: string | null;
            /** Model Code */
            model_code?: string | null;
            /** Qty */
            qty?: number | null;
            /** Ref */
            ref?: string | null;
            /** Short */
            short?: string | null;
            /**
             * Source
             * @default user
             * @enum {string}
             */
            source: "user" | "template" | "birdseye" | "recommended";
        };
        /** ProductPick */
        ProductPick: {
            /** Family Id */
            family_id?: string | null;
            /**
             * Label
             * @description 표시명(Smart Signage QM55C)
             */
            label: string;
            /** Model Code */
            model_code?: string | null;
            /**
             * Ord
             * @default 0
             */
            ord: number;
            /** Qty */
            qty?: number | null;
            /**
             * Ref
             * @description 셸 참조(kb:model:mdl_… · kb:family:fam_… · custom:글)
             */
            ref?: string | null;
            /**
             * Short
             * @description 칩 약칭(QM55C)
             */
            short: string;
            /**
             * Source
             * @default user
             * @enum {string}
             */
            source: "user" | "template" | "birdseye" | "recommended";
        };
        /** ProductsResult */
        ProductsResult: {
            /** Product Picks */
            product_picks: components["schemas"]["ProductPick"][];
            /** Related Products */
            related_products: components["schemas"]["RelatedProduct"][];
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
            /** Source */
            source: {
                [key: string]: unknown;
            };
            /** Target */
            target: {
                [key: string]: unknown;
            };
        };
        /** PutProducts */
        PutProducts: {
            /** Items */
            items: components["schemas"]["ProductItem"][];
        };
        /** PutSolutions */
        PutSolutions: {
            /** Items */
            items: components["schemas"]["SolutionItem"][];
        };
        /** Recommendation */
        Recommendation: {
            /** Action Code */
            action_code: string;
            /** Applied */
            applied: boolean;
            /** Benefit */
            benefit: string;
            /** Evidence */
            evidence: components["schemas"]["Evidence"][];
            /** Label */
            label: string;
            /** No */
            no: number;
            /** Product Only Text */
            product_only_text: string;
            /** Scene Id */
            scene_id: string;
            /** Solution Id */
            solution_id: string;
            /**
             * Solution Label
             * @description 「MagicINFO · 전원 스케줄」
             */
            solution_label: string;
            /**
             * Tag
             * @enum {string}
             */
            tag: "required" | "recommended" | "optional";
            /** Tag Label */
            tag_label: string;
            /** Time */
            time?: string | null;
            /**
             * Title
             * @description 「{라벨} — {한 줄}」
             */
            title: string;
        };
        /** Recommendations */
        Recommendations: {
            /**
             * Applied Count
             * @default 0
             */
            applied_count: number;
            /** Applied Solutions */
            applied_solutions?: string[];
            /** Entered With Type */
            entered_with_type?: ("with" | "without") | null;
            /** Industry Name */
            industry_name?: string | null;
            /** Items */
            items?: components["schemas"]["Recommendation"][];
            /** Job Id */
            job_id?: string | null;
            /** Off Nos */
            off_nos?: number[];
            /**
             * Product Only Count
             * @default 0
             */
            product_only_count: number;
            /** Required Nos */
            required_nos?: number[];
            /**
             * Status
             * @default none
             * @enum {string}
             */
            status: "none" | "computing" | "ready" | "failed";
        };
        /** RelatedProduct */
        RelatedProduct: {
            /** Family Id */
            family_id?: string | null;
            /** Label */
            label: string;
            /** Model Code */
            model_code?: string | null;
            /** Ref */
            ref?: string | null;
            /** Short */
            short: string;
            /**
             * Why
             * @description 추천 근거(D5 공존 · C2 공간 후보 · 문장 언급)
             * @default
             */
            why: string;
        };
        /** ResumeRequest */
        ResumeRequest: {
            /** Job Id */
            job_id: string;
        };
        /** ResyncRequest */
        ResyncRequest: {
            /**
             * Apply
             * @default false
             */
            apply: boolean;
        };
        /** ResyncResult */
        ResyncResult: {
            /**
             * Applied
             * @default false
             */
            applied: boolean;
            /**
             * Diff
             * @description {zones_changed, products_changed}
             */
            diff: {
                [key: string]: unknown;
            };
            /**
             * Summary
             * @description 「존 {a}개 바뀜 · 제품 {b}개 바뀜」
             * @default
             */
            summary: string;
            /** Updated Scene Ids */
            updated_scene_ids?: string[];
            /** Zones */
            zones?: components["schemas"]["ZoneDiff"][];
        };
        /** RewriteRequest */
        RewriteRequest: {
            /** Instruction */
            instruction?: string | null;
            /** Pov Role Id */
            pov_role_id?: string | null;
            /** Preset */
            preset?: ("shorter" | "pov" | "solution_detail") | null;
        };
        /** Role */
        Role: {
            /** Id */
            id: string;
            /** Initial */
            initial: string;
            /**
             * Intro
             * @default
             */
            intro: string;
            /** Name */
            name: string;
            /** Ord */
            ord: number;
            /** Pains */
            pains?: string[];
            /**
             * Rewriting
             * @default false
             */
            rewriting: boolean;
            /**
             * Scene Count
             * @default 0
             */
            scene_count: number;
            /** Scene Refs */
            scene_refs?: components["schemas"]["SceneRef"][];
            /**
             * Source
             * @default parsed
             */
            source: string;
            /**
             * Suggested
             * @default false
             */
            suggested: boolean;
            /** Wants */
            wants?: string[];
        };
        /** RouteResult */
        RouteResult: {
            /** Aerial Birdseye Id */
            aerial_birdseye_id?: string | null;
            /**
             * Next
             * @enum {string}
             */
            next: "SC3R" | "SC4G";
            /** Reason */
            reason?: string | null;
        };
        /** SavedVersion */
        SavedVersion: {
            /** Author */
            author?: string | null;
            /** Created At */
            created_at: string;
            /** N */
            n: number;
            /**
             * Note
             * @default
             */
            note: string;
        };
        /** SaveResult */
        SaveResult: {
            /**
             * Created
             * @default true
             */
            created: boolean;
            /** Version */
            version: number;
        };
        /** Scenario */
        Scenario: {
            active_job?: components["schemas"]["ActiveJob"] | null;
            aerial: components["schemas"]["Aerial"];
            /**
             * Anonymized
             * @description 기밀 차단으로 익명화 대체 경로를 탔다(고객사 → 「고객사」로 보내고 결과에서 되돌림)
             * @default false
             */
            anonymized: boolean;
            birdseye_link?: components["schemas"]["BirdseyeLink"] | null;
            /** Characters */
            characters?: string[];
            /** Created At */
            created_at: string;
            /** Customer Name */
            customer_name?: string | null;
            /**
             * Dirty
             * @default false
             */
            dirty: boolean;
            generation?: components["schemas"]["Generation"] | null;
            /** Id */
            id: string;
            /** Images Job */
            images_job?: {
                [key: string]: unknown;
            } | null;
            /**
             * In Proposal
             * @default false
             */
            in_proposal: boolean;
            industry?: components["schemas"]["Industry"] | null;
            /** Last Saved At */
            last_saved_at?: string | null;
            /** Needs */
            needs?: string[];
            notices?: components["schemas"]["Notices"];
            parse?: components["schemas"]["ParseResult"] | null;
            /** Product Picks */
            product_picks?: components["schemas"]["ProductPick"][];
            /** Project Id */
            project_id?: string | null;
            /**
             * Raw Text
             * @default
             */
            raw_text: string;
            /**
             * Related For
             * @description 추천 근거 솔루션 이름(「· MagicINFO 연관 제품 추천됨」)
             */
            related_for?: string | null;
            /** Related Products */
            related_products?: components["schemas"]["RelatedProduct"][];
            /** Removed Characters */
            removed_characters?: string[];
            /**
             * Rev
             * @description 작업본 수정 번호(PATCH if_rev 로 겹침 확인)
             */
            rev: number;
            /**
             * Role Count
             * @default 0
             */
            role_count: number;
            /** Route */
            route: string;
            /**
             * Scene Count
             * @default 0
             */
            scene_count: number;
            /**
             * Slot Count
             * @default 0
             */
            slot_count: number;
            /** Solution Picks */
            solution_picks?: components["schemas"]["SolutionPick"][];
            /**
             * Space Label
             * @default
             */
            space_label: string;
            /**
             * Start Mode
             * @enum {string}
             */
            start_mode: "blank" | "template" | "birdseye";
            /**
             * Status
             * @enum {string}
             */
            status: "draft" | "generating" | "done" | "failed";
            /** Step */
            step: number;
            /** Template */
            template?: {
                [key: string]: unknown;
            } | null;
            /** Title */
            title: string;
            /**
             * Type
             * @enum {string}
             */
            type: "with" | "without";
            /**
             * Type Label
             * @description 「with 솔루션」 · 「without 솔루션」
             */
            type_label: string;
            /**
             * Type Sub
             * @description 「솔루션 + 연관 제품 활용」 · 「제품 활용만」
             */
            type_sub: string;
            /** Updated At */
            updated_at: string;
            /** Usages */
            usages?: components["schemas"]["UsageRec"][];
            /**
             * Version
             * @description 저장 버전(v{n}) — :save · 생성 완료 때 오른다
             * @default 0
             */
            version: number;
            /** Vertical Code */
            vertical_code?: string | null;
            /**
             * Via Timeline
             * @default false
             */
            via_timeline: boolean;
        };
        /** ScenarioList */
        ScenarioList: {
            alert?: components["schemas"]["BirdseyeAlert"] | null;
            counts: components["schemas"]["ListCounts"];
            /** Items */
            items: components["schemas"]["ScenarioRow"][];
            /** Next Cursor */
            next_cursor?: string | null;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** ScenarioRow */
        ScenarioRow: {
            /**
             * Birdseye Changed
             * @default false
             */
            birdseye_changed: boolean;
            /**
             * Customer Line
             * @description 「{고객} · {공간}」
             */
            customer_line: string;
            /** Id */
            id: string;
            /**
             * In Proposal
             * @default false
             */
            in_proposal: boolean;
            /** Route */
            route: string;
            /** Scene Count */
            scene_count: number;
            /**
             * Start Label
             * @description 「직접 입력」 · 「업종 템플릿 · 의료」 · 「조감도 · {조감도 제목}」
             */
            start_label: string;
            /**
             * Start Mode
             * @enum {string}
             */
            start_mode: "blank" | "template" | "birdseye";
            /**
             * Status
             * @enum {string}
             */
            status: "draft" | "generating" | "done" | "failed";
            /**
             * Status Action
             * @description 실패 행 「다시 시도」
             */
            status_action?: string | null;
            /** Status Label */
            status_label: string;
            /** Status Sub */
            status_sub: string;
            /** Title */
            title: string;
            /**
             * Type
             * @enum {string}
             */
            type: "with" | "without";
            /**
             * Type Label
             * @description 「with 솔루션」 · 「without」
             */
            type_label: string;
            /** Updated At */
            updated_at: string;
        };
        /** SceneCharacter */
        SceneCharacter: {
            /**
             * Is New
             * @default false
             */
            is_new: boolean;
            /**
             * Name
             * @default
             */
            name: string;
            /** Role Id */
            role_id: string;
        };
        /** SceneImage */
        SceneImage: {
            /**
             * Aspect
             * @default 16:9
             */
            aspect: string;
            /** Created At */
            created_at?: string | null;
            /** File Id */
            file_id?: string | null;
            /** Image Id */
            image_id?: string | null;
            /**
             * Label
             * @description 「v1 · 이미지 생성 · 어제」
             * @default
             */
            label: string;
            /**
             * N
             * @description 이미지 버전 번호(v1)
             */
            n?: number | null;
            /** Snapshot */
            snapshot?: {
                [key: string]: unknown;
            };
            /**
             * Source
             * @default image_flow
             * @enum {string}
             */
            source: "image_render" | "image_flow" | "picked";
            /** Thumb Url */
            thumb_url?: string | null;
            /** Url */
            url?: string | null;
            /** Version Id */
            version_id: string;
        };
        /** SceneList */
        SceneList: {
            /** Items */
            items: components["schemas"]["SceneOut"][];
            /** Locked Nos */
            locked_nos?: number[];
        };
        /** SceneOut */
        SceneOut: {
            /** Beats */
            beats?: components["schemas"]["Beat"][];
            /**
             * Changed Sentences
             * @description 직전 버전 대비 새 문장(「바뀐 곳 {k}」)
             */
            changed_sentences?: string[];
            /** Characters */
            characters?: components["schemas"]["SceneCharacter"][];
            /** Confirm Tokens */
            confirm_tokens?: components["schemas"]["ConfirmToken"][];
            /** Evidence */
            evidence?: components["schemas"]["Evidence"][];
            /** Id */
            id: string;
            image?: components["schemas"]["SceneImage"] | null;
            image_job?: components["schemas"]["ImageJob"] | null;
            /** Image Request Id */
            image_request_id?: string | null;
            /**
             * Image Stale
             * @description {missing:['태블릿']} — 이미지 뒤 이야기가 바뀜
             */
            image_stale?: {
                [key: string]: unknown;
            } | null;
            /**
             * Is New
             * @default false
             */
            is_new: boolean;
            /** Label */
            label: string;
            /**
             * Locked
             * @default false
             */
            locked: boolean;
            /** No */
            no: number;
            /** Partial Story */
            partial_story?: string | null;
            /**
             * Place
             * @default
             */
            place: string;
            /**
             * Pov Role Ids
             * @description 「{역할} 시점으로」 후보(주 시점 아닌 역할)
             */
            pov_role_ids?: string[];
            /** Products */
            products?: components["schemas"]["SceneProduct"][];
            /**
             * Reason
             * @default
             */
            reason: string;
            /**
             * Rewriting
             * @default false
             */
            rewriting: boolean;
            /**
             * Short Title
             * @default
             */
            short_title: string;
            /** Slot Id */
            slot_id: string;
            /** Solution Chips */
            solution_chips?: string[];
            /** Solutions */
            solutions?: components["schemas"]["SceneSolution"][];
            /** Space Key */
            space_key?: string | null;
            /**
             * Status
             * @default waiting
             * @enum {string}
             */
            status: "waiting" | "writing" | "done" | "failed";
            /**
             * Story
             * @default
             */
            story: string;
            /**
             * Story Check
             * @default false
             */
            story_check: boolean;
            /** Time */
            time?: string | null;
            /**
             * Title
             * @default
             */
            title: string;
            /**
             * Version
             * @default 0
             */
            version: number;
            /** Zone Ref */
            zone_ref?: {
                [key: string]: unknown;
            } | null;
        };
        /** SceneProduct */
        SceneProduct: {
            /** Family Id */
            family_id?: string | null;
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
            /** Model Code */
            model_code?: string | null;
            /** Qty */
            qty?: number | null;
            /** Ref */
            ref?: string | null;
            /** Short */
            short: string;
        };
        /** SceneRef */
        SceneRef: {
            /**
             * Is New
             * @default false
             */
            is_new: boolean;
            /** No */
            no: number;
        };
        /** SceneSolution */
        SceneSolution: {
            /** Action Code */
            action_code: string;
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
            /** Solution Id */
            solution_id: string;
        };
        /** SceneVersion */
        SceneVersion: {
            /** Created At */
            created_at: string;
            /** N */
            n: number;
            /**
             * Reason
             * @default
             */
            reason: string;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** SceneVersionList */
        SceneVersionList: {
            /** Items */
            items: components["schemas"]["SceneVersion"][];
        };
        /** SearchHit */
        SearchHit: {
            /** Family Id */
            family_id?: string | null;
            /** Id */
            id: string;
            /**
             * Kind
             * @default solution
             */
            kind: string;
            /** Label */
            label: string;
            /** Model Code */
            model_code?: string | null;
            /** Ref */
            ref: string;
            /** Short */
            short: string;
            /**
             * Sub
             * @default
             */
            sub: string;
        };
        /** SearchResult */
        SearchResult: {
            /** Items */
            items: components["schemas"]["SearchHit"][];
        };
        /** ShareOut */
        ShareOut: {
            /** Token */
            token?: string | null;
            /** Url */
            url: string;
        };
        /** Sheet */
        Sheet: {
            /**
             * Code
             * @enum {string}
             */
            code: "VM-A" | "VM-B" | "VM-C" | "VM-D" | "SS-A" | "SS-B" | "SS-C";
            /**
             * Confirm Count
             * @default 0
             */
            confirm_count: number;
            /**
             * Detail
             * @description 미리보기 칩 · 격자(맵 시트 rows × cols)
             */
            detail?: {
                [key: string]: unknown;
            };
            /**
             * Images
             * @description {have, total}
             */
            images: {
                [key: string]: number;
            };
            /**
             * Kind
             * @enum {string}
             */
            kind: "map" | "space";
            /** N */
            n: number;
            /** Scene Ids */
            scene_ids: string[];
            /** Scene Nos */
            scene_nos: number[];
            /** Space Key */
            space_key?: string | null;
            /**
             * Summary
             * @default
             */
            summary: string;
            /** Title */
            title: string;
        };
        /** SheetPlan */
        SheetPlan: {
            /**
             * Carry
             * @description {scenes, solutions, products, images, confirm}
             */
            carry: {
                [key: string]: number;
            };
            /** First Missing Scene Id */
            first_missing_scene_id?: string | null;
            /** Images Missing */
            images_missing: number;
            /** Last Saved At */
            last_saved_at?: string | null;
            /** Sheets */
            sheets: components["schemas"]["Sheet"][];
            /** Spaces */
            spaces?: string[];
            /**
             * Version
             * @default 0
             */
            version: number;
        };
        /** Skeleton */
        Skeleton: {
            /** Text */
            text: string;
            /** Title */
            title: string;
        };
        /** SkeletonList */
        SkeletonList: {
            /** Items */
            items: components["schemas"]["Skeleton"][];
        };
        /** Slot */
        Slot: {
            /** Id */
            id: string;
            /**
             * Is New
             * @default false
             */
            is_new: boolean;
            /** Label */
            label: string;
            /** Ord */
            ord: number;
            /** Time */
            time?: string | null;
        };
        /** SolutionItem */
        SolutionItem: {
            /** Name */
            name?: string | null;
            /** Solution Id */
            solution_id: string;
        };
        /** SolutionPick */
        SolutionPick: {
            /** Name */
            name: string;
            /**
             * Ord
             * @default 0
             */
            ord: number;
            /** Solution Id */
            solution_id: string;
            /**
             * Source
             * @default user
             * @enum {string}
             */
            source: "user" | "template" | "recommended";
        };
        /** SolutionsResult */
        SolutionsResult: {
            /** Related For */
            related_for?: string | null;
            /** Related Products */
            related_products: components["schemas"]["RelatedProduct"][];
            /** Solution Picks */
            solution_picks: components["schemas"]["SolutionPick"][];
        };
        /** Stage */
        Stage: {
            /**
             * Key
             * @enum {string}
             */
            key: "split" | "write" | "link" | "confirm";
            /** Name */
            name: string;
            /**
             * Note
             * @default
             */
            note: string;
            /**
             * State
             * @enum {string}
             */
            state: "done" | "run" | "wait";
        };
        /** SuggestedScene */
        SuggestedScene: {
            /**
             * Place
             * @default
             */
            place: string;
            /** Role Id */
            role_id?: string | null;
            /** Slot Id */
            slot_id: string;
            /** Text */
            text: string;
        };
        /** Suggestions */
        Suggestions: {
            /** Roles */
            roles?: string[];
            scene?: components["schemas"]["SuggestedScene"] | null;
        };
        /** TextRequest */
        TextRequest: {
            /** Text */
            text: string;
        };
        /** Timeline */
        Timeline: {
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
            /**
             * Job Id
             * @description 레인 문장 재작성 · 편집 요청 잡
             */
            job_id?: string | null;
            /** Rewriting Role Ids */
            rewriting_role_ids?: string[];
            /** Roles */
            roles: components["schemas"]["Role"][];
            /** Scenes */
            scenes: components["schemas"]["TimelineScene"][];
            /** Slots */
            slots: components["schemas"]["Slot"][];
            suggestions: components["schemas"]["Suggestions"];
        };
        /** TimelineOp */
        TimelineOp: {
            /** After Slot Id */
            after_slot_id?: string | null;
            /** Beat Id */
            beat_id?: string | null;
            /** Intro */
            intro?: string | null;
            /** Label */
            label?: string | null;
            /** Name */
            name?: string | null;
            /** New Scene */
            new_scene?: boolean | null;
            /**
             * Op
             * @enum {string}
             */
            op: "add_slot" | "set_slot" | "remove_slot" | "move_beat" | "add_beat" | "set_beat" | "remove_beat" | "add_role" | "set_role" | "remove_role" | "reorder_roles" | "split_scene" | "merge_same_time" | "prune_empty_slots" | "accept_suggestion" | "dismiss_suggestion";
            /** Pains */
            pains?: string[] | null;
            /** Place */
            place?: string | null;
            /** Role Id */
            role_id?: string | null;
            /** Role Ids */
            role_ids?: string[] | null;
            /** Scene Id */
            scene_id?: string | null;
            /** Slot Id */
            slot_id?: string | null;
            /** Suggested */
            suggested?: boolean | null;
            /** Text */
            text?: string | null;
            /** Time */
            time?: string | null;
            /** To Role Id */
            to_role_id?: string | null;
            /** To Slot Id */
            to_slot_id?: string | null;
            /** Wants */
            wants?: string[] | null;
        };
        /** TimelineOpsRequest */
        TimelineOpsRequest: {
            /** Ops */
            ops?: components["schemas"]["TimelineOp"][];
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
        /** TimelineScene */
        TimelineScene: {
            /** Beats */
            beats: components["schemas"]["Beat"][];
            /** Id */
            id: string;
            /**
             * Is New
             * @default false
             */
            is_new: boolean;
            /** No */
            no: number;
            /**
             * Ord In Slot
             * @default 0
             */
            ord_in_slot: number;
            /**
             * Place
             * @default
             */
            place: string;
            /** Slot Id */
            slot_id: string;
            /**
             * Status
             * @default waiting
             */
            status: string;
            /**
             * Title
             * @default
             */
            title: string;
        };
        /** TimelineText */
        TimelineText: {
            /** Raw Text */
            raw_text: string;
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
             * @default proposal
             * @constant
             */
            service: "proposal";
            /** Version */
            version?: number | null;
        };
        /** UsageRec */
        UsageRec: {
            /** Created At */
            created_at?: string | null;
            /**
             * Label
             * @default
             */
            label: string;
            /** Ref */
            ref: string;
            /** Service */
            service: string;
            /** Version */
            version?: number | null;
        };
        /** VersionList */
        VersionList: {
            /** Items */
            items: components["schemas"]["SavedVersion"][];
        };
        /** ZoneDiff */
        ZoneDiff: {
            /**
             * Change
             * @enum {string}
             */
            change: "new" | "changed" | "removed" | "same";
            /** N */
            n?: number | null;
            /**
             * Name
             * @default
             */
            name: string;
            /**
             * Products Changed
             * @default false
             */
            products_changed: boolean;
            /** Zone Id */
            zone_id: string;
        };
        /** ZoneRow */
        ZoneRow: {
            /** Change */
            change?: ("new" | "changed" | "removed" | "same") | null;
            /** Id */
            id: string;
            /** Included */
            included: boolean;
            /** N */
            n: number;
            /** Name */
            name: string;
            /** Products */
            products?: {
                [key: string]: unknown;
            }[];
            /** Short Name */
            short_name: string;
            /**
             * State
             * @enum {string}
             */
            state: "products" | "furniture" | "empty";
            /** Sub */
            sub: string;
            /** U */
            u?: number | null;
            /** V */
            v?: number | null;
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
    birdseye_options: {
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
                    "application/json": components["schemas"]["BirdseyeOptions"];
                };
            };
        };
    };
    birdseye_preview: {
        parameters: {
            query?: {
                scenario_id?: string | null;
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
                    "application/json": components["schemas"]["BirdseyePreview"];
                };
            };
        };
    };
    image_return: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ImageReturn"];
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
                    "application/json": components["schemas"]["ImageReturnOut"];
                };
            };
        };
    };
    industries: {
        parameters: {
            query?: {
                project_id?: string | null;
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
                    "application/json": components["schemas"]["IndustryList"];
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
                    "application/json": components["schemas"]["Info"];
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
                    "application/json": components["schemas"]["SearchResult"];
                };
            };
        };
    };
    list_scenarios: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
                q?: string | null;
                sort?: "updated" | "created" | "title";
                start_mode?: "all" | "blank" | "template" | "birdseye";
                status?: "all" | "draft" | "generating" | "done" | "failed";
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
                    "application/json": components["schemas"]["ScenarioList"];
                };
            };
        };
    };
    create_scenario: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateScenario"];
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
                    "application/json": components["schemas"]["Scenario"];
                };
            };
        };
    };
    from_birdseye: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FromBirdseye"];
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
                    "application/json": components["schemas"]["JobAcceptedWithScenario"];
                };
            };
        };
    };
    from_template: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FromTemplate"];
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
                    "application/json": components["schemas"]["JobAcceptedWithScenario"];
                };
            };
        };
    };
    get_scenario: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Scenario"];
                };
            };
        };
    };
    delete_scenario: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
    patch_scenario: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchScenario"];
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
                    "application/json": components["schemas"]["Scenario"];
                };
            };
        };
    };
    clone_scenario: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
                    "application/json": components["schemas"]["CloneResult"];
                };
            };
        };
    };
    edit_request: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
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
    route_generate: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RouteResult"];
                };
            };
        };
    };
    save_scenario: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
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
    shorten: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
    dismiss_alert: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
    birdseye_resync: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResyncRequest"];
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
                    "application/json": components["schemas"]["ResyncResult"];
                };
            };
        };
    };
    extract_characters: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ExtractRequest"];
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
                    "application/json": components["schemas"]["Characters"];
                };
            };
        };
    };
    create_export: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
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
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
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
    generate: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GenerateRequest"];
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
    generate_cancel: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Scenario"];
                };
            };
        };
    };
    generate_resume: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ResumeRequest"];
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
    generation_view: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GenerationView"];
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
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
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
    images_generate_missing: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
    images_sync: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImagesSync"];
                };
            };
        };
    };
    import_work: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
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
        };
    };
    parse_input: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ParseRequest"];
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
    put_products: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PutProducts"];
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
                    "application/json": components["schemas"]["ProductsResult"];
                };
            };
        };
    };
    proposal_handoff: {
        parameters: {
            query?: {
                section?: "spaceScenario" | "space_scenario" | "solution" | "sxs";
                type?: "standard" | "quickwin" | "solution";
                version?: number | null;
            };
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
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
    get_recommendations: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Recommendations"];
                };
            };
        };
    };
    apply_all: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Recommendations"];
                };
            };
        };
    };
    commit_recommendations: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CommitRecommendations"];
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
                    "application/json": components["schemas"]["Scenario"];
                };
            };
        };
    };
    compute_recommendations: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
    patch_recommendation: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
                scene_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchRecommendation"];
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
                    "application/json": components["schemas"]["Recommendations"];
                };
            };
        };
    };
    patch_role: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                role_id: string;
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchRole"];
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
                    "application/json": components["schemas"]["Timeline"];
                };
            };
        };
    };
    list_scenes: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SceneList"];
                };
            };
        };
    };
    add_scene: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AddSceneRequest"];
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
                    "application/json": components["schemas"]["SceneOut"];
                };
            };
        };
    };
    share: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShareOut"];
                };
            };
        };
    };
    sheet_plan: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SheetPlan"];
                };
            };
        };
    };
    put_solutions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PutSolutions"];
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
                    "application/json": components["schemas"]["SolutionsResult"];
                };
            };
        };
    };
    get_timeline: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Timeline"];
                };
            };
        };
    };
    timeline_nl_edit: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
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
    timeline_text: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TimelineText"];
                };
            };
        };
    };
    timeline_ops: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TimelineOpsRequest"];
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
                    "application/json": components["schemas"]["Timeline"];
                };
            };
        };
    };
    add_usage: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
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
                    "application/json": components["schemas"]["UsageRec"];
                };
            };
        };
    };
    delete_usage: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                ref: string;
                sc_id: string;
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
    list_versions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
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
                sc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Scenario"];
                };
            };
        };
    };
    get_scene: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                scene_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SceneOut"];
                };
            };
        };
    };
    delete_scene: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                scene_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
    patch_scene: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                scene_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PatchScene"];
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
                    "application/json": components["schemas"]["SceneOut"];
                };
            };
        };
    };
    rewrite_scene: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                scene_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RewriteRequest"];
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
    image_prefill: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                scene_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImagePrefill"];
                };
            };
        };
    };
    image_request: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                scene_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
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
                    "application/json": components["schemas"]["ImageRequestOut"];
                };
            };
        };
    };
    image_attach: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                scene_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AttachImage"];
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
                    "application/json": components["schemas"]["SceneOut"];
                };
            };
        };
    };
    scene_versions: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                scene_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SceneVersionList"];
                };
            };
        };
    };
    restore_scene_version: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                n: number;
                scene_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SceneOut"];
                };
            };
        };
    };
    skeletons: {
        parameters: {
            query?: {
                industry?: string | null;
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
                    "application/json": components["schemas"]["SkeletonList"];
                };
            };
        };
    };
    solution_actions: {
        parameters: {
            query?: {
                solution_ids?: string | null;
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
                    "application/json": components["schemas"]["ActionList"];
                };
            };
        };
    };
    solution_search: {
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
                    "application/json": components["schemas"]["SearchResult"];
                };
            };
        };
    };
}
