// 자동 생성 — 직접 고치지 말 것. 원본: contracts/kb.json (make contracts)
export interface paths {
    "/v1/cases/{case_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Case */
        get: operations["get_case"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cases/{case_id}/similar": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Similar Cases
         * @description 이 사례와 비슷한 사례(D1: 업종 · 공간 · 제품 · 제목 문장).
         */
        get: operations["get_similar_cases"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/cases/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Cases Search */
        get: operations["cases_search"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/categories": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Categories */
        get: operations["list_categories"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/entities/{kind}/{entity_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Entity
         * @description 엔티티 통합 보기(query.py `entity`, 봉투). 없으면 404.
         */
        get: operations["get_entity"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/families": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Families */
        get: operations["list_families"];
        put?: never;
        post?: never;
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
        /** Get Image */
        get: operations["get_image"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/file": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Image File
         * @description 로컬 저장본(WKB_IMAGE_DIR/<id>.webp|jpg|png). 아직 없으면 썸네일. 둘 다 없으면 404.
         */
        get: operations["get_image_file"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/{image_id}/thumb": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Image Thumb
         * @description 썸네일(webp, 긴 변 160~176px). 없으면 404.
         */
        get: operations["get_image_thumb"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/images/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Images Search */
        get: operations["images_search"];
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
    "/v1/meta": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Meta */
        get: operations["meta"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/models": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Models */
        get: operations["list_models"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/models/{model_code}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Model
         * @description 모델코드(LH55QMCEBGCXKR · LH012IWCMWS/XU) · mdl_ · fam_(대표 모델) 모두 받는다.
         */
        get: operations["get_model"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/models/{model_code}/cases": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Model Cases */
        get: operations["get_model_cases"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/models/{model_code}/images": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Model Images */
        get: operations["get_model_images"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/models/{model_code}/lifecycle": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Model Lifecycle
         * @description 생애주기(06-spec §4.17): KB 에 있으면 판매 중(DR09), 없으면 not_in_catalog. 공식 후속 모델은 KB 에 없다(DR10) —
         *     `successors` 에 같은 계열 · 같은 크기 다른 세대 모델(relation=similar, newer)을 준다.
         */
        get: operations["get_model_lifecycle"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/patterns": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Patterns
         * @description KB 질의 패턴 목록(설명 · 요청 JSON 스키마). 실행은 `POST /v1/query/{code}`.
         */
        get: operations["list_patterns"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/placement-rules": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Placement Rules
         * @description 배치 · 수량 규칙(KB placement_rule). 지금은 모두 draft · 계수 빈칸 → active=false · param_status=unfilled(08-birdseye).
         */
        get: operations["list_placement_rules"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/products/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Products Search */
        get: operations["products_search"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/A1": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * A1 · 엔티티 링킹
         * @description 문장 속 모델코드 · 제품 · 분류 · 솔루션 · 업종 별칭과 공간 · 역량 키워드를 찾는다.
         *
         *     query.py: `KB.A1`
         */
        post: operations["query_A1"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/A2": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * A2 · 업종 판별
         * @description KR 업종 top-2(애매하면 ask). 추가: 후보마다 정규화 전 점수 raw_score.
         *
         *     query.py: `KB.A2`
         */
        post: operations["query_A2"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/A3": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * A3 · 요구 스펙 항목 → 정규 키
         * @description 이름 · 값 원문 → 정규 스펙 키 · 수치 · 단위. 추가: 값의 '인치' 를 screen_size_inch 로 보정.
         *
         *     query.py: `KB.A3`
         */
        post: operations["query_A3"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/B1": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * B1 · 업종 프리셋
         * @description 업종 페이지 장면 순서 = 공간 시퀀스, 장면별 추천 항목, 히어로 문구, 추천 솔루션, 대표 사례.
         *
         *     query.py: `KB.B1`
         */
        post: operations["query_B1"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/B2": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * B2 · 요구사항 결핍 → 확인 질문
         * @description 문장에 나온 공간이 요구하는 역량 중 문장에 없는 것을 질문으로.
         *
         *     query.py: `KB.B2`
         */
        post: operations["query_B2"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/C1": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * C1 · 공간 · 요구 → 역량
         * @description 공간(requires 초안)과 문장 키워드로 hard · soft 역량.
         *
         *     query.py: `KB.C1`
         */
        post: operations["query_C1"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/C2": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * C2 · 후보 제품군
         * @description 역량 충족 + 사이트 추천 + 분류 일치 + 선례 + 문장 유사도로 후보 제품군.
         *
         *     query.py: `KB.C2`
         */
        post: operations["query_C2"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/C3": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * C3 · 제품 → 적합 업종 · 공간 · 사례
         * @description 이 제품군(또는 소속 분류)이 추천된 업종 · 공간과 쓰인 도입사례(역방향).
         *
         *     query.py: `KB.C3`
         */
        post: operations["query_C3"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/C4": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * C4 · 제외 사유
         * @description 역량 근거 없음 · 분류 밖 같은 제외 사유.
         *
         *     query.py: `KB.C4`
         */
        post: operations["query_C4"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/C6": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * C6 · 요구 스펙 충족 판정
         * @description 정규 스펙 키로 pass · fail · unknown(스펙 없으면 추정하지 않음). 추가: attr_name 으로 속성 고르기.
         *
         *     query.py: `KB.C6`
         */
        post: operations["query_C6"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/D1": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * D1 · 유사 사례
         * @description 업종 · 공간 · 제품 겹침 + 문장 유사도로 분해 점수.
         *
         *     query.py: `KB.D1`
         */
        post: operations["query_D1"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/D2": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * D2 · 사례 통계
         * @description 업종(또는 공간) 사례 수 · 많이 쓴 제품 · 공간 · 요구 태그.
         *
         *     query.py: `KB.D2`
         */
        post: operations["query_D2"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/D3": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * D3 · 성과 KPI
         * @description 사례 KPI 문장(claim_flag, T5 — 원문 대조 필요).
         *
         *     query.py: `KB.D3`
         */
        post: operations["query_D3"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/D5": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * D5 · 공존 패턴
         * @description 사례에서 함께 쓰인 제품 · 솔루션(support · confidence · lift).
         *
         *     query.py: `KB.D5`
         */
        post: operations["query_D5"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/E1": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * E1 · 메시지 계층
         * @description 대상 · 업종 · 공간별 원문 메시지(tagline → key message → proof point, 출처 · claim).
         *
         *     query.py: `KB.E1`
         */
        post: operations["query_E1"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/E2": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * E2 · 테마로 메시지 찾기
         * @description 문장과 비슷한 원문 메시지와 그 대상(제품 · 솔루션).
         *
         *     query.py: `KB.E2`
         */
        post: operations["query_E2"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/E3": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * E3 · 컨텍스트 → 메시지 묶음
         * @description 업종 · 공간 · 제품 · 타겟고객 · 요구사항(모두 선택) → 헤드라인 · 핵심 메시지 · 제품 메시지 · 근거 사례.
         *
         *     query.py: `KB.E3`
         */
        post: operations["query_E3"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/entity": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * get_entity · 엔티티 통합 보기 (= get_entity)
         * @description 흩어진 정보(언급 문서 · 메시지 · 그래프 엣지 · 스펙 · 태그)를 엔티티 하나에 모은다. 못 찾으면 result=null, decision_reasons=[NOT_FOUND].
         *
         *     query.py: `KB.entity`
         */
        post: operations["query_entity"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/G1": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * G1 · 공간 × 분류 배치 이미지
         * @description 공간 맥락 이미지(등급순), 없으면 폴백(fallback_level).
         *
         *     query.py: `KB.G1`
         */
        post: operations["query_G1"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/G2": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * G2 · 제품 · 분류가 나오는 이미지
         * @description 설치 · 사례 사진 우선.
         *
         *     query.py: `KB.G2`
         */
        post: operations["query_G2"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/G4": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * G4 · 제품 단독컷
         * @description 제품군 PDP 갤러리(confirmed).
         *
         *     query.py: `KB.G4`
         */
        post: operations["query_G4"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/G5": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * G5 · 사례 사진
         * @description 도입사례 페이지 사진.
         *
         *     query.py: `KB.G5`
         */
        post: operations["query_G5"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/get_entity": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * get_entity · 엔티티 통합 보기
         * @description 흩어진 정보(언급 문서 · 메시지 · 그래프 엣지 · 스펙 · 태그)를 엔티티 하나에 모은다. 못 찾으면 result=null, decision_reasons=[NOT_FOUND].
         *
         *     query.py: `KB.entity`
         */
        post: operations["query_get_entity"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/image_search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * image_search · 이미지 검색
         * @description alt · 캡션 · 섹션 · 맥락으로 이미지 검색(등급 힌트 재정렬).
         *
         *     query.py: `KB.image_search`
         */
        post: operations["query_image_search"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/images": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * image_search · 이미지 검색 (= image_search)
         * @description alt · 캡션 · 섹션 · 맥락으로 이미지 검색(등급 힌트 재정렬).
         *
         *     query.py: `KB.image_search`
         */
        post: operations["query_images"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/S1": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * S1 · 요구사항 → 공간별 제품 추천
         * @description 요구 문장을 절 단위로 나눠 공간 · 분류 · 역량을 묶고 공간마다 후보 제품군(C2) · 솔루션 · 유사 사례(D1)를 낸다(체인 A1 · A2 → C1 → C2 → D1).
         *
         *     query.py: `KB.S1`
         */
        post: operations["query_S1"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/S2": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * S2 · 업종 → 장면 구성
         * @description 업종 페이지 장면(공간 · 항목 · 메시지 · 배치 이미지)과 유사 사례(체인 B1 → E1 → G1 → D1).
         *
         *     query.py: `KB.S2`
         */
        post: operations["query_S2"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/query/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * search · 하이브리드 검색
         * @description 원문 청크 · 엔티티(trigram BM25 + 부분 일치 + LSA 벡터 → RRF), 결과마다 원문 URL · 섹션.
         *
         *     query.py: `KB.search`
         */
        post: operations["query_search"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/segments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Segments
         * @description Winmate 16업종 · 업종별 사례 수(03-mi MI1I). 사례 → 업종은 규칙 초안(rule_segment_v1).
         */
        get: operations["list_segments"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/segments/{code}/insights": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Segment Insights
         * @description 업종 인사이트(03-mi MI1I): 요구 유형 상위 · 많이 쓰인 제품 · 솔루션. code = FB … 또는 wm_…
         */
        get: operations["get_segment_insights"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/segments/classify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Classify Segments
         * @description 업종 판별 KB 근거(03-mi §7.3): 16업종마다 kb_score · clue_score · clues · similar_case_ids.
         */
        post: operations["classify_segments"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/solutions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Solutions */
        get: operations["list_solutions"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/solutions/{solution_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Solution
         * @description 카탈로그 id(magicinfo) 또는 KB id(sol_magicinfo).
         */
        get: operations["get_solution"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/solutions/{solution_id}/cases": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Solution Cases */
        get: operations["get_solution_cases"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/solutions/{solution_id}/images": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Solution Images */
        get: operations["get_solution_images"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/space-types": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Space Types */
        get: operations["list_space_types"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/spec/attributes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Spec Attributes
         * @description 스펙 속성 사전(spec_attr_def): 분류별 그룹 · 속성 이름 · 정규 키 · 단위.
         */
        get: operations["list_spec_attributes"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/spec/table": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Spec Table
         * @description 여러 모델의 스펙을 나란히(같은 그룹 › 속성 = 한 행, 값은 원문 + 정규 수치 · 단위 · 출처) + 파생값(인치 · 치수 mm · 밝기 Typ).
         */
        post: operations["spec_table"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/verticals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Verticals
         * @description kr_site = KR 사이트 업종 22(상위 10 · 하위 12) · us_site = 13 · winmate16 = Winmate 16업종(10-proposal 부록 C, K3).
         */
        get: operations["list_verticals"];
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
        /** A1Req */
        A1Req: {
            /**
             * Lang
             * @default ko
             */
            lang: string;
            /** Text */
            text: string;
        };
        /** A3Item */
        A3Item: {
            /**
             * Name Raw
             * @default
             */
            name_raw: string;
            /**
             * Value Raw
             * @default
             */
            value_raw: string;
        };
        /** A3Req */
        A3Req: {
            /** Category Root */
            category_root?: string | null;
            /**
             * Items
             * @description 요구 스펙 항목(이름 · 값 원문)
             */
            items: components["schemas"]["A3Item"][];
        };
        /** Applied */
        Applied: {
            vertical: components["schemas"]["AppliedVertical"] | null;
        };
        /** AppliedVertical */
        AppliedVertical: {
            /**
             * From
             * @enum {string}
             */
            from: "user" | "task" | "inferred";
            /** Id */
            id: string;
            /** Name */
            name: string;
        };
        /** B1Req */
        B1Req: {
            /** Vertical Id */
            vertical_id: string;
        };
        /** BodyMention */
        BodyMention: {
            /** Date */
            date: string | null;
            /** Id */
            id: string;
            /** Title */
            title: string;
            /** Url */
            url: string | null;
        };
        /** C1Req */
        C1Req: {
            /** Spaces */
            spaces?: string[];
            /** Text */
            text?: string | null;
        };
        /** C2Req */
        C2Req: {
            /**
             * Capabilities
             * @description hard 역량(cap_ 접두 없어도 됨)
             */
            capabilities?: string[];
            /** Category */
            category?: string | null;
            /**
             * Limit
             * @default 15
             */
            limit: number;
            /** Soft */
            soft?: string[];
            /** Space */
            space?: string | null;
            /** Text */
            text?: string | null;
            /** Vertical */
            vertical?: string | null;
        };
        /** C3Req */
        C3Req: {
            /** Family Id */
            family_id: string;
        };
        /** C4Req */
        C4Req: {
            /** Capabilities */
            capabilities?: string[];
            /** Category */
            category?: string | null;
            /** Family Id */
            family_id: string;
        };
        /** C6Req */
        C6Req: {
            /**
             * Ref
             * @description mdl_… 또는 fam_…(대표 모델)
             */
            ref: string;
            /** Requirements */
            requirements: components["schemas"]["C6Requirement"][];
        };
        /** C6Requirement */
        C6Requirement: {
            /**
             * Attr Name
             * @description 추가 — 같은 정규 키에 값이 여럿일 때 고를 속성 이름(예 `소비전력 (On Mode)`). 없으면 원본처럼 첫 행(06-spec kb 요청 ①)
             */
            attr_name?: string | null;
            /**
             * Key
             * @description 정규 스펙 키(brightness_nit · operation_hours …)
             */
            key: string;
            /**
             * Op
             * @enum {string}
             */
            op: ">=" | "<=" | "==" | "contains";
            /** Value */
            value: number | string;
        };
        /** CaseBasis */
        CaseBasis: {
            /**
             * Clue Only
             * @description 단서 사전만으로 분류된 사례 수(대응 없는 업종은 전부)
             */
            clue_only: number;
            /**
             * Prior
             * @description KR 업종 대응(prior)과 단서로 분류된 사례 수
             */
            prior: number;
        };
        /** CaseCard */
        CaseCard: {
            /** Date */
            date: string | null;
            /**
             * Format
             * @description 추가 — article · pdf · video
             */
            format?: string | null;
            /** Id */
            id: string;
            match: components["schemas"]["CaseMatch"] | null;
            photos: components["schemas"]["CasePhotos"];
            /** Products */
            products: components["schemas"]["CaseProduct"][];
            /**
             * Quote
             * @description 추가 — 사례 인용문(T5, 이전 세션 추출) — 요약 아님
             */
            quote?: string | null;
            /** Source Tier */
            source_tier: string | null;
            /**
             * Summary
             * @description 갭 G-CASE-1: KB v1 에 요약 없음 → null
             */
            summary: string | null;
            /**
             * Tag Detail
             * @description 갭 G-CASE-2: 공간 유형 → 짧은 말 사전([제안])
             */
            tag_detail: string | null;
            /** Title */
            title: string;
            /** Url */
            url: string | null;
            /** Url Display */
            url_display: string | null;
            vertical: components["schemas"]["IdName"] | null;
        };
        /** CaseDetail */
        CaseDetail: {
            /** Date */
            date: string | null;
            /**
             * Format
             * @description 추가 — article · pdf · video
             */
            format?: string | null;
            /** Id */
            id: string;
            /** Kpis */
            kpis: components["schemas"]["Kpi"][];
            match: components["schemas"]["CaseMatch"] | null;
            /** Needs */
            needs: components["schemas"]["Need"][];
            photos: components["schemas"]["CasePhotos"];
            /** Products */
            products: components["schemas"]["CaseProduct"][];
            /**
             * Quote
             * @description 추가 — 사례 인용문(T5, 이전 세션 추출) — 요약 아님
             */
            quote?: string | null;
            /** Source Tier */
            source_tier: string | null;
            /**
             * Spaces
             * @description 추가 — 사례 공간(deployment_space)
             */
            spaces?: components["schemas"]["IdName"][];
            /**
             * Summary
             * @description 갭 G-CASE-1: KB v1 에 요약 없음 → null
             */
            summary: string | null;
            /**
             * Tag Detail
             * @description 갭 G-CASE-2: 공간 유형 → 짧은 말 사전([제안])
             */
            tag_detail: string | null;
            /** Title */
            title: string;
            /** Url */
            url: string | null;
            /** Url Display */
            url_display: string | null;
            vertical: components["schemas"]["IdName"] | null;
        };
        /** CaseMatch */
        CaseMatch: {
            breakdown: components["schemas"]["MatchBreakdown"];
            /** Score */
            score: number;
            /** Terms */
            terms: string[];
        };
        /** CasePhotos */
        CasePhotos: {
            /** Count */
            count: number;
            /** Items */
            items: components["schemas"]["ImageCard"][];
        };
        /** CaseProduct */
        CaseProduct: {
            /** Label */
            label: string;
            /** Ref */
            ref: string | null;
            /** Tier */
            tier: string | null;
        };
        /** CaseSearchOut */
        CaseSearchOut: {
            applied: components["schemas"]["Applied"];
            corpus: components["schemas"]["Corpus"];
            /** Items */
            items: components["schemas"]["CaseCard"][];
            /** Next Cursor */
            next_cursor?: string | null;
            /**
             * Total
             * @description 추가 — 조건에 맞는 전체 건수
             */
            total: number;
        };
        /** CategoryItem */
        CategoryItem: {
            /** Family Count */
            family_count: number;
            /** Has Children */
            has_children: boolean;
            /** Id */
            id: string;
            /** Level */
            level: number;
            /** Name */
            name: string;
            /** Order */
            order: number;
            /** Parent Id */
            parent_id: string | null;
        };
        /** CategoryList */
        CategoryList: {
            /** Items */
            items: components["schemas"]["CategoryItem"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** ClassifyIn */
        ClassifyIn: {
            /** Text */
            text: string;
        };
        /** ClassifyItem */
        ClassifyItem: {
            /** A2 Match */
            a2_match: number | null;
            /** Case Ratio */
            case_ratio: number;
            /** Clue Score */
            clue_score: number;
            /** Clues */
            clues: components["schemas"]["Clue"][];
            /** Code */
            code: string;
            /** Has Kr Mapping */
            has_kr_mapping: boolean;
            /** Id */
            id: string;
            /** Kb Score */
            kb_score: number;
            /** Name */
            name: string;
            /** Similar Case Ids */
            similar_case_ids: string[];
        };
        /** ClassifyOut */
        ClassifyOut: {
            /** A2 */
            a2: {
                [key: string]: unknown;
            };
            /** Items */
            items: components["schemas"]["ClassifyItem"][];
            /** Method */
            method: string;
            /** Needs Confirmation */
            needs_confirmation: string[];
            /** Similar Case Ids */
            similar_case_ids: string[];
        };
        /** Clue */
        Clue: {
            /** Code */
            code: string;
            /** Text */
            text: string;
            /** Weight */
            weight: number;
        };
        /** Column */
        Column: {
            /** Key */
            key: string;
            /** Label */
            label: string;
        };
        /** Corpus */
        Corpus: {
            /** Checked At */
            checked_at: string | null;
            /** Count */
            count: number;
        };
        /** D1Req */
        D1Req: {
            /**
             * Limit
             * @default 10
             */
            limit: number;
            /** Spaces */
            spaces?: string[];
            /**
             * Targets
             * @description [kind, id] 또는 {kind, id}
             */
            targets?: ([
                string,
                string
            ] | components["schemas"]["KindId"])[];
            /** Text */
            text?: string | null;
            /** Vertical */
            vertical?: string | null;
        };
        /** D2Req */
        D2Req: {
            /** Space */
            space?: string | null;
            /** Vertical */
            vertical?: string | null;
        };
        /** D3Req */
        D3Req: {
            /** Deployment Ids */
            deployment_ids?: string[];
            /** Target */
            target?: [
                string,
                string
            ] | components["schemas"]["KindId"] | null;
        };
        /** D5Req */
        D5Req: {
            /**
             * Min Support
             * @default 2
             */
            min_support: number;
            /** Targets */
            targets: ([
                string,
                string
            ] | components["schemas"]["KindId"])[];
        };
        /** Depict */
        Depict: {
            /** Id */
            id: string;
            /** Kind */
            kind: string;
            /** Level */
            level: string;
            /** Name */
            name: string;
        };
        /** Deploy */
        Deploy: {
            /** Desc */
            desc: string;
            evidence: components["schemas"]["DeployEvidence"] | null;
            /** Name */
            name: string;
        };
        /** DeployEvidence */
        DeployEvidence: {
            /** Date */
            date: string | null;
            /** Deployment Id */
            deployment_id: string;
            /** Title */
            title: string | null;
        };
        /** DetailCounts */
        DetailCounts: {
            /** Cases */
            cases: number;
            /** Images */
            images: number;
        };
        /** DeviceExample */
        DeviceExample: {
            /** Display Name */
            display_name: string;
            /** Family Id */
            family_id: string;
            /** Model Code */
            model_code: string;
            /** Series Label */
            series_label: string;
        };
        /**
         * Dims
         * @description 정규화한 치수(mm). 원문 수치를 속성 이름의 축 순서대로 옮긴 것(계산 없음 · 단위만 mm).
         */
        Dims: {
            /**
             * Attr
             * @description 원문 행 `그룹 › 속성`
             */
            attr: string;
            /**
             * D
             * @description 깊이 · 두께(mm). 원문에 없으면 null
             */
            d?: number | null;
            /**
             * H
             * @description 높이(mm)
             */
            h: number | null;
            /**
             * Kind
             * @description body(제품 · 본체) · without_stand · with_stand · package · active_area(화면 발광부) · indoor_unit · outdoor_unit · panel · other
             * @enum {string}
             */
            kind: "body" | "without_stand" | "with_stand" | "package" | "active_area" | "indoor_unit" | "outdoor_unit" | "panel" | "other";
            /**
             * Order
             * @description 원문의 축 순서(WxHxD · WxDxH · HxWxD · WxH …)
             */
            order: string;
            /**
             * Order Basis
             * @description 축 순서를 정한 근거(속성 이름 · 그룹 이름 · 기본 W×H×D)
             * @enum {string}
             */
            order_basis: "attr" | "group" | "default";
            /**
             * Raw
             * @description KB value_raw 원문
             */
            raw: string;
            /** Spec Value Id */
            spec_value_id?: string | null;
            /**
             * Unit
             * @default mm
             * @constant
             */
            unit: "mm";
            /**
             * W
             * @description 가로(mm)
             */
            w: number | null;
        };
        /** E1Req */
        E1Req: {
            /** About */
            about?: ([
                string,
                string
            ] | components["schemas"]["KindId"])[];
            /** Locale */
            locale?: string | null;
            /** Space */
            space?: string | null;
            /** Vertical */
            vertical?: string | null;
        };
        /** E2Req */
        E2Req: {
            /**
             * Limit
             * @default 15
             */
            limit: number;
            /** Locale */
            locale?: string | null;
            /** Theme */
            theme: string;
        };
        /** E3Req */
        E3Req: {
            /** Customer */
            customer?: string | null;
            /**
             * Limit
             * @default 12
             */
            limit: number;
            /**
             * Locale
             * @default ko-KR
             */
            locale: string | null;
            /** Products */
            products?: ([
                string,
                string
            ] | components["schemas"]["KindId"])[];
            /** Spaces */
            spaces?: string[];
            /** Text */
            text?: string | null;
            /** Vertical */
            vertical?: string | null;
        };
        /** EntityReq */
        EntityReq: {
            /** Ident */
            ident: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "family" | "model" | "category" | "solution" | "service" | "vertical" | "space_type" | "deployment" | "capability";
        };
        /**
         * Envelope
         * @description query.py 공통 봉투.
         */
        Envelope: {
            /** Candidates */
            candidates?: {
                [key: string]: unknown;
            }[];
            /**
             * Decision Hint
             * @enum {string}
             */
            decision_hint: "auto" | "check" | "ask";
            /** Decision Reasons */
            decision_reasons?: string[];
            /** Evidence Paths */
            evidence_paths?: unknown[];
            /** Fallback Level */
            fallback_level?: string | null;
            /**
             * Kb Version
             * @description 추가 — KB 빌드 버전(kb_meta.schema_version)
             */
            kb_version?: string | null;
            /** Modes Used */
            modes_used?: string[];
            /** Needs Confirmation */
            needs_confirmation?: string[];
            /** Pattern */
            pattern: string;
            /**
             * Result
             * @description 패턴 결과(패턴마다 모양이 다르다 — QUERY_COOKBOOK). get_entity 가 못 찾으면 null
             */
            result: {
                [key: string]: unknown;
            } | null;
            /** Tier Min */
            tier_min?: string | null;
            /** Timings Ms */
            timings_ms?: {
                [key: string]: number;
            };
        } & {
            [key: string]: unknown;
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
            /** Source Url */
            source_url: string | null;
            /** Text */
            text: string;
        };
        /** Fact */
        Fact: {
            /** Label */
            label: string;
            /** Value */
            value: string;
        };
        /** FamilyDetailRef */
        FamilyDetailRef: {
            /** Detail Url */
            detail_url: string | null;
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Series Label */
            series_label: string;
        };
        /** FamilyItem */
        FamilyItem: {
            /** Detail Url */
            detail_url: string | null;
            /** Id */
            id: string;
            /** Is Bundle */
            is_bundle: boolean;
            /** Model Count */
            model_count: number;
            /** Name */
            name: string;
            /**
             * Sale Status Code
             * @description 추가 — 사이트 판매상태코드(saleStatCd) 원값. 코드표(뜻)는 KB 에 없다. KB 수집본 값은 '17'(589 제품군) · '15'(16 제품군) 둘뿐이고 둘 다 수집 시점(2026-10-04) 사이트 목록에 노출된 상품이라 DR09 기준 판매 중으로 본다(lifecycle.status=on_sale). 단종 · 단종 예정 코드는 수집본에 없다 — 목록에서 빠진 모델은 KB 에 없고 lifecycle.status=not_in_catalog 다
             */
            sale_status_code?: string | null;
            /**
             * Series Code
             * @description 추가 — marketing_model 이 짧은 코드면 그 코드(QMC)
             */
            series_code?: string | null;
            /** Series Label */
            series_label: string;
            subcategory: components["schemas"]["IdName"] | null;
            thumb: components["schemas"]["ImageCard"] | null;
        };
        /** FamilyList */
        FamilyList: {
            /** Items */
            items: components["schemas"]["FamilyItem"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** FamilyRef */
        FamilyRef: {
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Series Label */
            series_label: string;
        };
        /** Focal */
        Focal: {
            /** X */
            x: number;
            /** Y */
            y: number;
        };
        /** G1Req */
        G1Req: {
            /** Category */
            category?: string | null;
            /**
             * Limit
             * @default 20
             */
            limit: number;
            /** Space */
            space: string;
            /** Vertical */
            vertical?: string | null;
        };
        /** G2Req */
        G2Req: {
            /** Ident */
            ident: string;
            /**
             * Kind
             * @description family · category · solution …
             */
            kind: string;
            /**
             * Limit
             * @default 20
             */
            limit: number;
        };
        /** G4Req */
        G4Req: {
            /** Family Id */
            family_id: string;
            /**
             * Limit
             * @default 10
             */
            limit: number;
        };
        /** G5Req */
        G5Req: {
            /** Deployment Id */
            deployment_id: string;
            /**
             * Limit
             * @default 30
             */
            limit: number;
        };
        /** IdName */
        IdName: {
            /** Id */
            id: string;
            /** Name */
            name: string;
        };
        /** ImageCard */
        ImageCard: {
            /** Alt */
            alt: string;
            /** @description 갭 G-IMG-4: 아직 없음(null) → 화면 기본 50%/50% */
            focal: components["schemas"]["Focal"] | null;
            /**
             * Grade
             * @enum {string}
             */
            grade: "A" | "A?C" | "C" | "D" | "E";
            /**
             * Has Local
             * @description 추가 — 썸네일이나 로컬 사본이 있으면 true(없으면 /thumb · /file 이 404)
             */
            has_local: boolean;
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "product" | "case" | "solution" | "industry";
            original: components["schemas"]["ImageDims"] | null;
            /**
             * Rights
             * @enum {string}
             */
            rights: "official" | "customer_case";
            /** Source Domain */
            source_domain: string;
            /**
             * Stored Url
             * @description 로컬 저장본 주소(게이트웨이). 원본 사본이 없으면 썸네일을 준다
             */
            stored_url: string;
            /** Thumb Url */
            thumb_url: string;
            /**
             * Title
             * @description 갭 G-IMG-3: 큐레이션 제목이 없으면 alt 앞 40자
             */
            title: string;
        };
        /** ImageContext */
        ImageContext: {
            /** Space Type Id */
            space_type_id: string | null;
            /** Vertical Id */
            vertical_id: string | null;
        };
        /** ImageDims */
        ImageDims: {
            /**
             * Basis
             * @description 추가 — 값의 근거: download(내려받은 원본) · board_sample(보드 표본) · browser_probe(썸네일 만들 때 잰 원본 크기, 용량 없음) · local_file · thumbnail
             */
            basis?: string | null;
            /**
             * Bytes
             * @description 파일 크기(바이트). 모르면 null(화면이 KB 로 포맷)
             */
            bytes?: number | null;
            /**
             * Format
             * @description JPG · PNG · WEBP … (모르면 null)
             */
            format?: string | null;
            /** Height */
            height: number;
            /** Width */
            width: number;
        };
        /** ImageGroup */
        ImageGroup: {
            /** Items */
            items: components["schemas"]["ImageMeta"][];
            /**
             * Key
             * @enum {string}
             */
            key: "official" | "case";
            /** Label */
            label: string;
            /** Source Label */
            source_label: string;
        };
        /** ImageList */
        ImageList: {
            /** Items */
            items: components["schemas"]["ImageMeta"][];
            /** Total */
            total: number;
        };
        /** ImageMeta */
        ImageMeta: {
            /** Alt */
            alt: string;
            /**
             * Caption Rule
             * @description 추가 — 제안서 캡션 규칙(`도입사례 사진` · `예시 사진(삼성 공식 이미지)`)
             */
            caption_rule: string;
            /** Collected At */
            collected_at: string | null;
            context: components["schemas"]["ImageContext"];
            /** Depicts */
            depicts: components["schemas"]["Depict"][];
            /** @description 갭 G-IMG-4: 아직 없음(null) → 화면 기본 50%/50% */
            focal: components["schemas"]["Focal"] | null;
            /**
             * Grade
             * @enum {string}
             */
            grade: "A" | "A?C" | "C" | "D" | "E";
            /**
             * Has Local
             * @description 추가 — 썸네일이나 로컬 사본이 있으면 true(없으면 /thumb · /file 이 404)
             */
            has_local: boolean;
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "product" | "case" | "solution" | "industry";
            /** Label */
            label: string;
            original: components["schemas"]["ImageDims"] | null;
            /** Original Url */
            original_url: string;
            /** Page Note */
            page_note: string | null;
            posted: components["schemas"]["Posted"] | null;
            /**
             * Rights
             * @enum {string}
             */
            rights: "official" | "customer_case";
            /** Source Domain */
            source_domain: string;
            source_page: components["schemas"]["SourcePage"];
            /** Source Type Label */
            source_type_label: string;
            /** @description 갭 G-IMG-2: 실제로 주는 로컬 사본(없으면 썸네일)의 메타 */
            stored: components["schemas"]["ImageDims"] | null;
            /**
             * Stored Url
             * @description 로컬 저장본 주소(게이트웨이). 원본 사본이 없으면 썸네일을 준다
             */
            stored_url: string;
            /** Thumb Url */
            thumb_url: string;
            /**
             * Title
             * @description 갭 G-IMG-3: 큐레이션 제목이 없으면 alt 앞 40자
             */
            title: string;
            /**
             * Usage Note
             * @description §9.6-6: 도입사례 `“도입사례 사진” 표기 필수 · 대외 사용 범위 확인 필요` · 공식 `삼성전자 저작물 · 대외 사용 범위 확인 필요`
             */
            usage_note: string;
            /**
             * Usage Note Short
             * @description 추가 — 팝오버 표기(공식 이미지는 `대외 사용 범위 확인 필요`)
             */
            usage_note_short: string;
        };
        /** ImageSearchCounts */
        ImageSearchCounts: {
            /** All */
            all: number;
            /** Case */
            case: number;
            /** Official */
            official: number;
        };
        /** ImageSearchOut */
        ImageSearchOut: {
            counts: components["schemas"]["ImageSearchCounts"];
            /** Items */
            items: components["schemas"]["ImageCard"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** ImageSearchReq */
        ImageSearchReq: {
            /**
             * Grade
             * @description 등급 힌트 필터(A · A?C · C · D · E)
             */
            grade?: string[] | null;
            /**
             * Limit
             * @default 20
             */
            limit: number;
            /** Text */
            text: string;
        };
        /** InsightItem */
        InsightItem: {
            /** Id */
            id: string;
            /** Kind */
            kind: string;
            /** N */
            n: number;
            /** Name */
            name: string;
        };
        /** KindId */
        KindId: {
            /** Id */
            id: string;
            /**
             * Kind
             * @description family · category · solution · service · model · deployment · vertical · industry_section …
             */
            kind: string;
        };
        /** Kpi */
        Kpi: {
            /** Claim Flag */
            claim_flag: boolean;
            /** Has Number */
            has_number: boolean;
            /** Id */
            id: string;
            /** Source Tier */
            source_tier: string | null;
            /** Text */
            text: string;
        };
        /** LedArea */
        LedArea: {
            /** Basis */
            basis: string;
            /** H */
            h: number;
            /** W */
            w: number;
        };
        /**
         * LedInfo
         * @description 스마트 LED 사이니지만(그 밖은 null). 화면 구성 옵션(대각 · 가로×세로) 표는 KB 에 없다.
         */
        LedInfo: {
            /** Note */
            note: string;
            /** Pitch Basis */
            pitch_basis: ("spec" | "option") | null;
            /** Pixel Pitch Mm */
            pixel_pitch_mm: number | null;
            /**
             * Size Mentions
             * @description PDP 원문의 화면 크기 언급(예 IAC `최대 130인치 화면`)
             */
            size_mentions: components["schemas"]["SizeMention"][];
            /** @description unit_pixels × pixel_pitch_mm(계산값, 발광 면적) */
            unit_active_mm: components["schemas"]["LedArea"] | null;
            /** @description 한 단위(캐비닛 또는 올인원 화면)의 픽셀 구성 원문(Pixel Configuration · LED 구성) */
            unit_pixels: components["schemas"]["LedPixels"] | null;
        };
        /** LedPixels */
        LedPixels: {
            /** Attr */
            attr: string;
            /** H */
            h: number;
            /** Raw */
            raw: string;
            /** W */
            w: number;
        };
        /** Lifecycle */
        Lifecycle: {
            /** Basis */
            basis: string;
            /** Gaps */
            gaps: string[];
            /** Id */
            id?: string | null;
            /** Model Code */
            model_code: string | null;
            /** Ref */
            ref: string;
            /**
             * Release Ym
             * @description 추가 — 스펙 '동일모델의 출시년월'(YYYY-MM)
             */
            release_ym?: string | null;
            /**
             * Sale Status Code
             * @description 추가 — 사이트 판매상태코드(saleStatCd) 원값. 코드표(뜻)는 KB 에 없다. KB 수집본 값은 '17'(589 제품군) · '15'(16 제품군) 둘뿐이고 둘 다 수집 시점(2026-10-04) 사이트 목록에 노출된 상품이라 DR09 기준 판매 중으로 본다(lifecycle.status=on_sale). 단종 · 단종 예정 코드는 수집본에 없다 — 목록에서 빠진 모델은 KB 에 없고 lifecycle.status=not_in_catalog 다
             */
            sale_status_code: string | null;
            /** Sold Out Flag */
            sold_out_flag: string | null;
            /**
             * Status
             * @description on_sale = KB(사이트 목록)에 있음(DR09) · not_in_catalog = KB 에 없음(단종이거나 미등록)
             * @enum {string}
             */
            status: "on_sale" | "not_in_catalog";
            /**
             * Successor
             * @description 공식 후속 모델 — KB 에 데이터가 없어 항상 null(DR10)
             */
            successor: {
                [key: string]: unknown;
            } | null;
            /**
             * Successors
             * @description 추가(06-spec 요청 2 · C5 대용) — 같은 계열 · 같은 크기(LED 는 피치 코드)의 다른 세대 KB 모델(사이니지 · LED 만, 표시명 규칙). 원본보다 오래된 것으로 확인된 후보는 뺀다. 최근 출시 먼저. 후속 여부는 사람이 정한다
             */
            successors?: components["schemas"]["Successor"][];
            /** @description 추가(06-spec 요청 1) — 스펙 보증 행 원문(없으면 null) */
            warranty?: components["schemas"]["Warranty"] | null;
        };
        /** MatchBreakdown */
        MatchBreakdown: {
            /** Product */
            product: number;
            /** Space */
            space: number;
            /** Text */
            text: number;
            /** Vertical */
            vertical: number;
        };
        /** MatchCounts */
        MatchCounts: {
            /** Model */
            model: number;
            /** Series */
            series: number;
            /** Usage */
            usage: number;
        };
        /** Message */
        Message: {
            /** Children */
            children: string[];
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
        /** MetaCounts */
        MetaCounts: {
            /** Case Pages */
            case_pages: number;
            /** Deployments */
            deployments: number;
            /** Families */
            families: number;
            /** Image Assets */
            image_assets: number;
            /**
             * Local Images
             * @description 추가 — 로컬 원본 사본 수(WKB_IMAGE_DIR)
             */
            local_images: number;
            /** Models */
            models: number;
            /**
             * Thumbnails
             * @description 추가 — 썸네일이 있는 이미지 수
             */
            thumbnails: number;
        };
        /** MetaOut */
        MetaOut: {
            /**
             * Catalog Version
             * @description 추가 — products_fetched_at 의 YYYY-MM
             */
            catalog_version?: string | null;
            /** Collected At */
            collected_at: string | null;
            counts: components["schemas"]["MetaCounts"];
            /** Kb Version */
            kb_version: string;
            /**
             * Products Fetched At
             * @description 추가 — kb_meta.products_fetched_at(카탈로그 버전 YYYY-MM 의 원천)
             */
            products_fetched_at?: string | null;
            /**
             * Warm
             * @description 추가 — 무거운 캐시(벡터 · 메시지)가 준비됐는지
             */
            warm: boolean;
        };
        /** ModelCaseItem */
        ModelCaseItem: {
            /** Date */
            date: string | null;
            /**
             * Format
             * @description 추가 — article · pdf · video
             */
            format?: string | null;
            /** Id */
            id: string;
            match: components["schemas"]["CaseMatch"] | null;
            /**
             * Match Type
             * @enum {string}
             */
            match_type: "model" | "series" | "usage";
            photos: components["schemas"]["CasePhotos"];
            /** Products */
            products: components["schemas"]["CaseProduct"][];
            /**
             * Quote
             * @description 추가 — 사례 인용문(T5, 이전 세션 추출) — 요약 아님
             */
            quote?: string | null;
            /** Source Tier */
            source_tier: string | null;
            /**
             * Summary
             * @description 갭 G-CASE-1: KB v1 에 요약 없음 → null
             */
            summary: string | null;
            /**
             * Tag Detail
             * @description 갭 G-CASE-2: 공간 유형 → 짧은 말 사전([제안])
             */
            tag_detail: string | null;
            /** Title */
            title: string;
            /** Url */
            url: string | null;
            /** Url Display */
            url_display: string | null;
            /** Used Products Line */
            used_products_line: string;
            vertical: components["schemas"]["IdName"] | null;
        };
        /** ModelCases */
        ModelCases: {
            corpus: components["schemas"]["Corpus"];
            counts: components["schemas"]["MatchCounts"];
            /**
             * Default Match
             * @description 추가 — 기본 켜짐 칩(모델 → 시리즈 → 용도 중 처음 1건 이상)
             */
            default_match?: ("model" | "series" | "usage") | null;
            /** Items */
            items: components["schemas"]["ModelCaseItem"][];
            /** Usage Label */
            usage_label: string | null;
        };
        /** ModelDetail */
        ModelDetail: {
            case_corpus: components["schemas"]["Corpus"];
            /** Category Path */
            category_path: components["schemas"]["IdName"][];
            counts: components["schemas"]["DetailCounts"];
            /**
             * Dims All
             * @description 추가 — 읽힌 치수 행 전부(스탠드 포함 · 포장 · 실내기 · 액티브 디스플레이 …)
             */
            dims_all?: components["schemas"]["Dims"][];
            /** @description 추가(08-birdseye 요청 4) — 대표 본체 치수(mm): body → without_stand 순으로 처음 행. 없으면 null */
            dims_mm?: components["schemas"]["Dims"] | null;
            /** Display Name */
            display_name: string;
            /**
             * Display Name Basis
             * @enum {string}
             */
            display_name_basis: "code_rule" | "model_code";
            /**
             * Documents
             * @description 갭 G-PRD-3: KB v1 에 매뉴얼 자료 없음 → null
             */
            documents: {
                [key: string]: unknown;
            }[] | null;
            /** Facts */
            facts: components["schemas"]["Fact"][];
            family: components["schemas"]["FamilyDetailRef"];
            /** Id */
            id: string;
            /** Key Chips */
            key_chips: string[];
            /**
             * Label En
             * @description 추가 — 영문 계열명 + 표시명(`Smart Signage QM55C`), 없으면 null
             */
            label_en?: string | null;
            /** @description 추가(08-birdseye 요청 2) — 스마트 LED 사이니지의 피치 · 픽셀 구성 · 발광 면적(그 밖은 null) */
            led?: components["schemas"]["LedInfo"] | null;
            /** Model Code */
            model_code: string;
            /**
             * Release Ym
             * @description 추가 — 스펙 '동일모델의 출시년월'(YYYY-MM), 없으면 null
             */
            release_ym?: string | null;
            /**
             * Sale Status Code
             * @description 추가 — 사이트 판매상태코드(saleStatCd) 원값. 코드표(뜻)는 KB 에 없다. KB 수집본 값은 '17'(589 제품군) · '15'(16 제품군) 둘뿐이고 둘 다 수집 시점(2026-10-04) 사이트 목록에 노출된 상품이라 DR09 기준 판매 중으로 본다(lifecycle.status=on_sale). 단종 · 단종 예정 코드는 수집본에 없다 — 목록에서 빠진 모델은 KB 에 없고 lifecycle.status=not_in_catalog 다
             */
            sale_status_code?: string | null;
            /**
             * Sold Out Flag
             * @description 추가 — 사이트 옵션 품절 표시 원값(Y · N · null)
             */
            sold_out_flag?: string | null;
            spec: components["schemas"]["SpecBlock"];
            /** Supported Solutions */
            supported_solutions: components["schemas"]["SupportedSolution"][];
            /** Title Line */
            title_line: string;
            /** Verified At */
            verified_at: string | null;
            /** @description 추가(06-spec 요청 1) — 스펙 보증 행 원문. 행이 없으면 null */
            warranty?: components["schemas"]["Warranty"] | null;
        };
        /** ModelList */
        ModelList: {
            /** Columns */
            columns: components["schemas"]["Column"][];
            /** Items */
            items: components["schemas"]["ModelRow"][];
            /** Next Cursor */
            next_cursor?: string | null;
            /**
             * Profile
             * @description 추가 — 열 프로필 id(00-shell §9.4)
             */
            profile: string;
        };
        /** ModelRow */
        ModelRow: {
            /** Display Name */
            display_name: string;
            /**
             * Display Name Basis
             * @description 추가 — G-PRD-1 표시명 근거
             * @enum {string}
             */
            display_name_basis: "code_rule" | "model_code";
            family: components["schemas"]["FamilyRef"];
            /** Id */
            id: string;
            /** Is Family Default */
            is_family_default: boolean;
            /** Model Code */
            model_code: string;
            thumb: components["schemas"]["ImageCard"] | null;
            /** Values */
            values: {
                [key: string]: components["schemas"]["ModelValue"];
            };
        };
        /** ModelValue */
        ModelValue: {
            /** Cm */
            cm?: number | null;
            /**
             * Display
             * @description 표시 문자열. 값이 없으면 `—`
             */
            display: string;
            /** H */
            h?: number | null;
            /** Inch */
            inch?: number | null;
            /** Nit */
            nit?: number | null;
            /**
             * Raw
             * @description KB value_raw 원문
             */
            raw?: string | null;
            /** Unit */
            unit?: string | null;
            /**
             * Value
             * @description 숫자 값(크기 · 밝기 · 해상도 밖의 열)
             */
            value?: number | null;
            /** W */
            w?: number | null;
        };
        /** Need */
        Need: {
            /** Kind */
            kind: string;
            /** Text */
            text: string;
        };
        /** ObservedVertical */
        ObservedVertical: {
            /** Id */
            id: string;
            /**
             * N
             * @description 이 업종으로 분류된 사례 중 그 KR 업종(사례 페이지의 사이트 업종 필터)인 사례 수
             */
            n: number;
            /** Name */
            name: string | null;
        };
        /** Part */
        Part: {
            /** Does */
            does: string;
            /** Name */
            name: string;
        };
        /** PatternInfo */
        PatternInfo: {
            /** Aliases */
            aliases: string[];
            /** Code */
            code: string;
            /** Description */
            description: string;
            /** Method */
            method: string;
            /** Name */
            name: string;
            /** Request Schema */
            request_schema: {
                [key: string]: unknown;
            };
            /** Route */
            route: string;
        };
        /** PatternList */
        PatternList: {
            /** Envelope Fields */
            envelope_fields: string[];
            /** Items */
            items: components["schemas"]["PatternInfo"][];
        };
        /** Pillar */
        Pillar: {
            /** Items */
            items: string[];
            /** Name */
            name: string;
        };
        /** PlacementRule */
        PlacementRule: {
            /** Active */
            active: boolean;
            /**
             * Category
             * @description 시드 분류 코드(signage · hvac_system_ac · *)
             */
            category: string | null;
            /**
             * Category Ids
             * @description 추가 — 이 규칙 분류의 KB 분류 id(시드 categories.yaml 의 목록 URL 로 이음)
             */
            category_ids?: string[];
            /**
             * Explanation Ko
             * @description 추가 — 시드 설명 문구
             */
            explanation_ko?: string | null;
            /** Expression */
            expression: string | null;
            /**
             * Id
             * @description 규칙 id(= 08-birdseye rule_id, 예 pr_warn_power_distance)
             */
            id: string;
            /** Kind */
            kind: string | null;
            /**
             * Missing Params
             * @description 추가 — 빈칸인 계수 이름
             */
            missing_params?: string[];
            /**
             * Param Notes
             * @description 추가 — 빈칸 안내 문구(`<<FILL: 용도별 단위면적당 부하>>` 의 설명)
             */
            param_notes?: {
                [key: string]: string;
            };
            /**
             * Param Status
             * @description 추가(08-birdseye 요청 3) — unfilled = 계수 빈칸이 있음(KB v1 은 모두) · draft = 다 채웠지만 승인 전 · approved = 사람 승인(status active). approved 일 때만 엔진 기본값을 덮어쓰세요
             * @default unfilled
             * @enum {string}
             */
            param_status: "unfilled" | "draft" | "approved";
            /**
             * Param Values
             * @description 추가 — 계수 값(빈칸은 null)
             */
            param_values?: {
                [key: string]: unknown;
            };
            /**
             * Params
             * @description KB 원문 그대로(빈칸은 `<<FILL…>>` 문자열) — 덮어쓸 때는 param_values 를 쓰세요
             */
            params: {
                [key: string]: unknown;
            };
            /**
             * Source Tier
             * @description 추가 — T5_seed_draft(시드 초안) · T4_expert(승인)
             */
            source_tier?: string | null;
            /** Space */
            space: string | null;
            /** Status */
            status: string | null;
        };
        /** PlacementRuleList */
        PlacementRuleList: {
            /** Items */
            items: components["schemas"]["PlacementRule"][];
            /** Note */
            note: string;
        };
        /** Posted */
        Posted: {
            /**
             * Basis
             * @enum {string}
             */
            basis: "case_page" | "file_path";
            /** Date */
            date: string;
        };
        /** PowerSet */
        PowerSet: {
            /** @description `(Max)` 행. LCD 사이니지에는 없고, LED 는 ㎡당(W/㎡) 값이다 */
            max: components["schemas"]["PowerValue"] | null;
            /** @description `(Typical)` 행. 사이니지는 14개 모델(BEH · BEF · BED · WMF)에만 있다 — On Mode 는 typical 로 보지 않는다 */
            typical: components["schemas"]["PowerValue"] | null;
            /**
             * Values
             * @description 소비전력 행 전부(원래 순서)
             */
            values: components["schemas"]["PowerValue"][];
        };
        /** PowerValue */
        PowerValue: {
            /**
             * Attr
             * @description 원문 행 `그룹 › 속성`
             */
            attr: string;
            /**
             * Mode
             * @description 속성 이름에서 읽은 측정 모드(`소비전력 (Typical)` → typical · `Power Consumption (Max)` → max · `정격소비전력` → rated …)
             * @enum {string}
             */
            mode: "typical" | "max" | "on" | "sleep" | "standby" | "off" | "dpms" | "yearly" | "rated" | "average" | "unspecified";
            /**
             * Per M2
             * @description ㎡당 값(LED 사이니지의 Max)
             */
            per_m2: boolean;
            /** Raw */
            raw: string;
            /** Spec Value Id */
            spec_value_id: string;
            /**
             * Unit
             * @description W · kW · W/㎡ · kWh/year(원문에서)
             */
            unit: string | null;
            /**
             * Value
             * @description 원문의 첫 수(없음 · 문자면 null)
             */
            value: number | null;
        };
        /** ProductSearchItem */
        ProductSearchItem: {
            /** Category Path */
            category_path: string[];
            /** Display Name */
            display_name: string;
            /**
             * Family Id
             * @description 추가
             */
            family_id: string;
            /** Family Name */
            family_name: string;
            /**
             * Highlight
             * @description display_name 안에서 검색어와 맞은 [시작, 끝) 범위
             */
            highlight: number[][];
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "model" | "family";
            /**
             * Label
             * @description 버블 글: `{영문 계열명} {표시명}`(사이니지 모델) · 그 밖은 표시명
             */
            label: string;
            /** Meta Line */
            meta_line: string;
            /** Model Code */
            model_code: string | null;
            /**
             * Score
             * @description 추가 — 정렬 점수
             */
            score: number;
            thumb: components["schemas"]["ImageCard"] | null;
        };
        /** ProductSearchOut */
        ProductSearchOut: {
            /** Items */
            items: components["schemas"]["ProductSearchItem"][];
        };
        /** Purchase */
        Purchase: {
            /** Label */
            label: string;
            /** Site Code */
            site_code: string | null;
        };
        /** ReqType */
        ReqType: {
            /** Code */
            code: string;
            /**
             * Examples
             * @description 이 태그가 붙은 사례들의 요구 문장 상위 3(빈도순, 이름표 아님 · 태그끼리 겹칠 수 있음)
             */
            examples: string[];
            /**
             * Examples Specific
             * @description 추가 — 이 태그에 두드러진 요구 문장 상위 3(문장 낱말의 태그 lift 합 순, 같은 응답의 앞 태그가 쓴 문장은 뺌). 이름표 아님
             */
            examples_specific?: string[];
            /**
             * Hint Terms
             * @description 추가 — 이 태그가 붙은 사례 요구 문장에서 전체 대비 두드러진 낱말(lift, 3건 이상) 최대 5. 이름표 아님
             */
            hint_terms?: string[];
            /**
             * Label
             * @description R01~R24 한국어 이름표 — KB 에 코드표가 없어 항상 null(데이터 공백, 지어내지 않음)
             */
            label: string | null;
            /** N */
            n: number;
        };
        /** S1Req */
        S1Req: {
            /**
             * Limit
             * @default 8
             */
            limit: number;
            /**
             * Text
             * @description 요구사항 문장
             */
            text: string;
        };
        /** S2Req */
        S2Req: {
            /**
             * Space
             * @description 공간 유형 id(guest_room …)
             */
            space?: string | null;
            /**
             * Vertical
             * @description KR 업종 id(kr_hotel …)
             */
            vertical: string;
        };
        /** SearchReq */
        SearchReq: {
            /**
             * K
             * @default 10
             */
            k: number;
            /** Modes */
            modes?: ("kw" | "vec")[];
            /** Text */
            text: string;
        };
        /** SegmentInsights */
        SegmentInsights: {
            /** Case Ids */
            case_ids: string[];
            /** Cases */
            cases: number;
            /** Code */
            code: string;
            /** Full */
            full: string;
            /** Gaps */
            gaps: string[];
            /** Id */
            id: string;
            /** Method */
            method: string;
            /** Name */
            name: string;
            /** Products */
            products: components["schemas"]["InsightItem"][];
            /** Req Types */
            req_types: components["schemas"]["ReqType"][];
            /** Short */
            short: string;
            /** Solutions */
            solutions: components["schemas"]["InsightItem"][];
            /** Tier */
            tier: string;
        };
        /** SegmentItem */
        SegmentItem: {
            /** Aliases */
            aliases: string[];
            /** @description 추가 — 이 업종 사례가 어떻게 분류됐나(prior+단서 · 단서만) */
            case_basis?: components["schemas"]["CaseBasis"] | null;
            /** Case Count */
            case_count: number;
            /** Code */
            code: string;
            /** Full */
            full: string;
            /** Id */
            id: string;
            /** Kb Name */
            kb_name: string | null;
            /**
             * Kr Vertical Ids
             * @description 시드 대응(segment_mapping, 초안). `<<FILL>>` 은 빈 목록 — 사례 분류 prior 는 이것만 쓴다
             */
            kr_vertical_ids: string[];
            /**
             * Kr Vertical Ids Observed
             * @description 추가 — 이 업종으로 분류된 사례의 KR 업종 중 2건 이상 · 절반 이상인 것(관측 대응, 계산값). 시드 대응이 있는 업종도 참고로 준다
             */
            kr_vertical_ids_observed?: string[];
            /**
             * Mapping
             * @description 추가(03-mi 요청) — KR 업종 대응이 있는가(시드 대응 또는 사례 관측 대응)
             * @default false
             */
            mapping: boolean;
            /**
             * Mapping Basis
             * @description 추가 — seed = 시드 대응(kr_vertical_ids) · observed_cases = 시드는 빈칸이고 이 업종으로 분류된 사례의 사이트 업종 필터에서 본 대응(kr_vertical_ids_observed, T5 · 사람 확인 전) · null = 둘 다 없음
             */
            mapping_basis?: ("seed" | "observed_cases") | null;
            /** Mapping Status */
            mapping_status: string | null;
            /** Name */
            name: string;
            /**
             * Observed Kr Verticals
             * @description 추가 — 이 업종 사례의 KR 업종 분포(많은 순)
             */
            observed_kr_verticals?: components["schemas"]["ObservedVertical"][];
            /** Short */
            short: string;
            /** Us Vertical Ids */
            us_vertical_ids: string[];
        };
        /** SegmentList */
        SegmentList: {
            /** Classified Cases */
            classified_cases: number;
            /** Items */
            items: components["schemas"]["SegmentItem"][];
            /** Method */
            method: string;
            /** Needs Confirmation */
            needs_confirmation: string[];
            /** Tier */
            tier: string;
            /** Total Cases */
            total_cases: number;
            /** Unclassified Cases */
            unclassified_cases: number;
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
        /** SimilarCases */
        SimilarCases: {
            /** Items */
            items: components["schemas"]["CaseCard"][];
        };
        /** SizeMention */
        SizeMention: {
            /** Inch */
            inch: number;
            /**
             * Qualifier
             * @description 원문의 `최대` · `최소`(없으면 null)
             */
            qualifier: string | null;
            /** Source Url */
            source_url: string | null;
            /**
             * Text
             * @description PDP 원문 문장
             */
            text: string;
        };
        /** SolutionCases */
        SolutionCases: {
            /** Body Mentions */
            body_mentions: components["schemas"]["BodyMention"][];
            corpus: components["schemas"]["Corpus"];
            /** Title Explicit */
            title_explicit: components["schemas"]["CaseCard"][];
            /** Total */
            total: number;
        };
        /** SolutionDetail */
        SolutionDetail: {
            /** Category Path */
            category_path: string[];
            counts: components["schemas"]["DetailCounts"];
            /**
             * Gaps
             * @description 추가 — 이 솔루션에 비어 있는 데이터(갭 코드)
             */
            gaps?: string[];
            /** Id */
            id: string;
            /** Intro Url */
            intro_url: string | null;
            /** Kb Id */
            kb_id?: string | null;
            /** Kb Ids */
            kb_ids?: string[];
            /** Key Chips */
            key_chips: string[];
            /** Messages */
            messages: components["schemas"]["Message"][];
            /** Name */
            name: string;
            profile: components["schemas"]["SolutionProfile"] | null;
            /**
             * Proposal Templates
             * @description 추가 — 10-proposal 부록 B(전용 템플릿 설명 · 업종 버전)
             */
            proposal_templates?: {
                [key: string]: unknown;
            } | null;
            purchase: components["schemas"]["Purchase"] | null;
            /** Quote Url */
            quote_url: string | null;
            /** Subtitle */
            subtitle: string | null;
            supported_devices: components["schemas"]["SupportedDevices"] | null;
            /** Template Code */
            template_code?: string | null;
            /** Verified At */
            verified_at: string | null;
            /** Version Label */
            version_label: string | null;
        };
        /** SolutionImages */
        SolutionImages: {
            /** Groups */
            groups: components["schemas"]["ImageGroup"][];
            /** Total */
            total: number;
        };
        /** SolutionItem */
        SolutionItem: {
            /** Desc */
            desc: string;
            /** Domain */
            domain: string;
            /** Icon */
            icon: string;
            /** Id */
            id: string;
            /** Industries */
            industries: string[];
            /** Kb Id */
            kb_id: string | null;
            /**
             * Kb Ids
             * @description 추가 — 대응하는 KB 솔루션 전부(SAC 제어 = 3개)
             */
            kb_ids?: string[];
            /**
             * Kb Match
             * @description 추가 — full · partial · none
             */
            kb_match?: string | null;
            /** Name */
            name: string;
            /** Template Code */
            template_code: string | null;
        };
        /** SolutionList */
        SolutionList: {
            /** Items */
            items: components["schemas"]["SolutionItem"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** SolutionProfile */
        SolutionProfile: {
            /** Deploy */
            deploy: components["schemas"]["Deploy"][];
            /** Device Functions */
            device_functions: string[];
            /** Intro */
            intro: string;
            /** Parts */
            parts: components["schemas"]["Part"][];
            /** Pillars */
            pillars: components["schemas"]["Pillar"][];
            /** Source Note */
            source_note: string;
        };
        /** SourcePage */
        SourcePage: {
            /** Label */
            label: string;
            /** Title */
            title: string | null;
            /** Url */
            url: string;
        };
        /** SpaceTypeItem */
        SpaceTypeItem: {
            /** Case Count */
            case_count: number;
            /** Default Attrs */
            default_attrs: {
                [key: string]: unknown;
            } | null;
            /** Id */
            id: string;
            /** Name */
            name: string;
            /** Origin */
            origin: string | null;
            /** Status */
            status: string | null;
            /** Vertical Ids */
            vertical_ids: string[];
        };
        /** SpaceTypeList */
        SpaceTypeList: {
            /** Items */
            items: components["schemas"]["SpaceTypeItem"][];
        };
        /** SpecAttr */
        SpecAttr: {
            /** Category Id */
            category_id: string;
            /** Group */
            group: string | null;
            /** Id */
            id: string;
            /** N Values */
            n_values: number | null;
            /** Name */
            name: string | null;
            /** Norm Key */
            norm_key: string | null;
            /** Unit */
            unit: string | null;
        };
        /** SpecAttrList */
        SpecAttrList: {
            /** Items */
            items: components["schemas"]["SpecAttr"][];
        };
        /** SpecBlock */
        SpecBlock: {
            /** Groups */
            groups: components["schemas"]["SpecGroup"][];
            /**
             * Profile
             * @description 프로필 id(사이니지 = `signage`). 프로필이 맞지 않으면 null → KB 원래 그룹 · 행 전체
             */
            profile: string | null;
            /** Source Url */
            source_url: string | null;
        };
        /** SpecCell */
        SpecCell: {
            /** Num */
            num: number | null;
            /** Num2 */
            num2: number | null;
            /** Raw */
            raw: string | null;
            /** Source */
            source: string | null;
            /** Source Url */
            source_url: string | null;
            /** Spec Value Id */
            spec_value_id: string;
            /** Unit */
            unit: string | null;
        };
        /** SpecDerived */
        SpecDerived: {
            /** Brightness Typ Nit */
            brightness_typ_nit: number | null;
            /** @description 예전 값 — 첫 'AxBxC' 를 가로×높이×깊이로 본다(축 순서를 보지 않음). 새 값은 dims_mm */
            dimensions_mm: components["schemas"]["SpecDims"] | null;
            /** @description 추가 — 속성 이름의 축 순서로 읽은 본체 치수(mm), 모델 상세 dims_mm 과 같다 */
            dims_mm?: components["schemas"]["Dims"] | null;
            option: components["schemas"]["SpecOption"];
            /** @description 추가(06-spec 요청 4) — 소비전력 행을 모드별로. 행이 없으면 null */
            power?: components["schemas"]["PowerSet"] | null;
            resolution: components["schemas"]["SpecResolution"] | null;
            /** Screen Size Cm */
            screen_size_cm: number | null;
            /**
             * Screen Size Inch
             * @description 00-shell §9.2 규칙. 스마트 LED 사이니지는 코드 숫자가 픽셀 피치라 쓰지 않는다(화면 크기 데이터 없음 → null)
             */
            screen_size_inch: number | null;
            /** @description 추가(06-spec 요청 1) — 스펙 보증 행 원문. 행이 없으면 null */
            warranty?: components["schemas"]["Warranty"] | null;
            /** Weight Kg Package */
            weight_kg_package: number | null;
            /** Weight Kg Set */
            weight_kg_set: number | null;
        };
        /** SpecDims */
        SpecDims: {
            /** D */
            d: number | null;
            /** H */
            h: number;
            /** Raw */
            raw: string;
            /** Unit */
            unit: string;
            /** W */
            w: number;
        };
        /** SpecGroup */
        SpecGroup: {
            /**
             * Column
             * @description 추가 — 프로필 2열 배치(없으면 null)
             */
            column?: ("left" | "right") | null;
            /** Name */
            name: string;
            /** Rows */
            rows: components["schemas"]["winmate_kb__schemas__SpecRow"][];
        };
        /** SpecOption */
        SpecOption: {
            /** Name */
            name: string | null;
            /** Value */
            value: string | null;
        };
        /** SpecResolution */
        SpecResolution: {
            /** H */
            h: number;
            /** Label */
            label: string | null;
            /** W */
            w: number;
        };
        /** SpecTableIn */
        SpecTableIn: {
            /**
             * Groups
             * @description 스펙 그룹 이름으로 행 거르기
             */
            groups?: string[] | null;
            /**
             * Keys
             * @description 정규 키로 행 거르기
             */
            keys?: string[] | null;
            /**
             * Models
             * @description 모델코드 · mdl_ · fam_(대표 모델)
             */
            models: string[];
        };
        /** SpecTableModel */
        SpecTableModel: {
            /** Category Id */
            category_id: string | null;
            /** Display Name */
            display_name: string;
            /** Display Name Basis */
            display_name_basis: string;
            /** Family Id */
            family_id: string;
            /** Family Name */
            family_name: string | null;
            /** Has Spec */
            has_spec: boolean;
            /** Id */
            id: string;
            /** Label En */
            label_en: string | null;
            /** Model Code */
            model_code: string;
            /** Ref */
            ref: string;
            /** Series Label */
            series_label: string | null;
            /** Source Url */
            source_url: string | null;
        };
        /** SpecTableOut */
        SpecTableOut: {
            /** Catalog Version */
            catalog_version: string | null;
            /**
             * Derived
             * @description 모델코드 → 파생값
             */
            derived: {
                [key: string]: components["schemas"]["SpecDerived"];
            };
            /** Models */
            models: components["schemas"]["SpecTableModel"][];
            /** Notes */
            notes: string[];
            /** Rows */
            rows: components["schemas"]["winmate_kb__api__SpecRow"][];
            /** Unresolved */
            unresolved: string[];
        };
        /** Successor */
        Successor: {
            /** Basis */
            basis: string;
            /** Display Name */
            display_name: string;
            /** Id */
            id: string;
            /** Model Code */
            model_code: string;
            /**
             * Newer
             * @description 출시년월(스펙 '동일모델의 출시년월', 같은 세대 중 가장 이른 값)로 본 원본보다 최근인지. 모르면 null
             */
            newer: boolean | null;
            /**
             * Reason
             * @description 예 `같은 계열(WM) · 같은 크기(55") · 세대 B → F · 출시 2026-03 (더 최근)`
             */
            reason: string;
            /**
             * Relation
             * @description KB 에 후속 데이터가 없어(DR10) 지금은 similar 만 준다
             * @enum {string}
             */
            relation: "successor" | "similar";
            /** Release Ym */
            release_ym: string | null;
        };
        /** SupportedDevices */
        SupportedDevices: {
            example: components["schemas"]["DeviceExample"] | null;
            /**
             * Family Ids
             * @description 추가 — 이 솔루션을 제품 페이지에서 언급한 제품군 전부
             */
            family_ids?: string[];
            /** Label */
            label: string;
        };
        /** SupportedSolution */
        SupportedSolution: {
            /**
             * Catalog Name
             * @description 추가 — 카탈로그 이름(예 `Samsung VXT`)
             */
            catalog_name?: string | null;
            evidence: components["schemas"]["Evidence"];
            /**
             * Id
             * @description 솔루션 시트 id(카탈로그 id, 카탈로그에 없으면 KB id)
             */
            id: string;
            /** Kb Id */
            kb_id: string;
            /** Kind Label */
            kind_label: string;
            /**
             * Name
             * @description 제품 페이지 원문 표기(예 `VXT`)
             */
            name: string;
        };
        /** TextReq */
        TextReq: {
            /** Text */
            text: string;
        };
        /** VerticalItem */
        VerticalItem: {
            /**
             * Code
             * @description 추가 — winmate16: 16업종 코드(FB …)
             */
            code?: string | null;
            /** Full */
            full?: string | null;
            /** Id */
            id: string;
            /**
             * Kb Name
             * @description 추가 — winmate16: KB 이름(name 은 SectionStep 이름)
             */
            kb_name?: string | null;
            /** Kr Vertical Ids */
            kr_vertical_ids?: string[];
            /** Mapping Status */
            mapping_status?: string | null;
            /** Name */
            name: string;
            /** Parent Id */
            parent_id: string | null;
            /**
             * Scheme
             * @description 추가 — kr_site · us_site · winmate16
             */
            scheme: string;
            /** Short */
            short?: string | null;
            /** Url */
            url?: string | null;
            /** Us Vertical Ids */
            us_vertical_ids?: string[];
        };
        /** VerticalList */
        VerticalList: {
            /** Items */
            items: components["schemas"]["VerticalItem"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /**
         * Warranty
         * @description 스펙 API 의 보증 행 원문(`품질보증기준` · `품질 보증 기간` · `보증기간`). KB 에 행이 없으면 객체 자체가 null.
         */
        Warranty: {
            /**
             * As Of
             * @description 원문 수집 시각
             */
            as_of: string | null;
            /**
             * Attr
             * @description 원문 행 `그룹 › 속성`
             */
            attr: string;
            /**
             * Claims
             * @description PDP 특장점의 보증 문구(최대 3, 예 `모터와 컴프레서 10년 무상보증`)
             */
            claims?: components["schemas"]["WarrantyClaim"][];
            /** Months */
            months: number | null;
            /**
             * Parts Years
             * @description 부품보유년한(원문에 있을 때만)
             */
            parts_years: number | null;
            /**
             * Source Ref
             * @description KB occurrence id
             */
            source_ref: string | null;
            /** Source Url */
            source_url: string | null;
            /**
             * Status
             * @description stated = 원문에 기간 숫자가 있음 · statement_only = '소비자분쟁해결기준에 따라 보상' 같은 문구뿐(연수 없음 → 확인 필요)
             * @enum {string}
             */
            status: "stated" | "statement_only";
            /**
             * Text
             * @description 원문 값 그대로
             */
            text: string;
            /**
             * Years
             * @description 보증 연수(3개월 = 0.25). 원문에 숫자가 없으면 null
             */
            years: number | null;
        };
        /** WarrantyClaim */
        WarrantyClaim: {
            /** Source Url */
            source_url: string | null;
            /**
             * Text
             * @description PDP 특장점 원문 문장(부품 · 혜택 보증일 수 있어 연수로 읽지 않는다)
             */
            text: string;
        };
        /** SpecRow */
        winmate_kb__api__SpecRow: {
            /** Attr Name */
            attr_name: string;
            /** Group */
            group: string;
            /** Norm Key */
            norm_key: string | null;
            /**
             * Values
             * @description 모델코드 → 값
             */
            values: {
                [key: string]: components["schemas"]["SpecCell"];
            };
        };
        /** SpecRow */
        winmate_kb__schemas__SpecRow: {
            /**
             * Attrs
             * @description 이 행을 만든 KB 속성 `그룹 › 속성`
             */
            attrs: string[];
            /** Label */
            label: string;
            /** Value */
            value: string;
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
    get_case: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                case_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CaseDetail"];
                };
            };
        };
    };
    get_similar_cases: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path: {
                case_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SimilarCases"];
                };
            };
        };
    };
    cases_search: {
        parameters: {
            query?: {
                /** @description 이전 응답의 next_cursor */
                cursor?: string | null;
                /** @description 업종이 없을 때 검색어로 판별(A2 decision_hint=auto 일 때만) */
                infer_vertical?: boolean;
                limit?: number;
                period?: "all" | "1y" | "3y" | "5y";
                q?: string | null;
                /** @description 지원 안 함(갭 G-CASE-4) — 값이 있으면 400 UNSUPPORTED_FILTER */
                region?: string | null;
                /** @description family:fam_… · solution:sol_…|magicinfo · category:cat_… · model:… */
                target?: string | null;
                /** @description 추가 — vertical_id 를 누가 정했나(applied.vertical.from) */
                vertical_from?: "user" | "task";
                /** @description kr_* 업종(하위 업종이면 상위 사례 필터로 찾는다) */
                vertical_id?: string | null;
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
                    "application/json": components["schemas"]["CaseSearchOut"];
                };
            };
        };
    };
    list_categories: {
        parameters: {
            query?: {
                /** @description 이전 응답의 next_cursor */
                cursor?: string | null;
                /** @description 기본 20, 최대 100 */
                limit?: number;
                /** @description 없으면 L1(9개) */
                parent_id?: string | null;
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
                    "application/json": components["schemas"]["CategoryList"];
                };
            };
        };
    };
    get_entity: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                entity_id: string;
                kind: "family" | "model" | "category" | "solution" | "service" | "vertical" | "space_type" | "deployment" | "capability";
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    list_families: {
        parameters: {
            query: {
                /** @description L1 · L2 · L3 분류 id */
                category_id: string;
                /** @description 이전 응답의 next_cursor */
                cursor?: string | null;
                /** @description 기본 20, 최대 100 */
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
                    "application/json": components["schemas"]["FamilyList"];
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
                    "application/json": components["schemas"]["ImageMeta"];
                };
            };
        };
    };
    get_image_file: {
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
            /** @description 이미지 바이너리 */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "image/jpeg": unknown;
                    "image/png": unknown;
                    "image/webp": unknown;
                };
            };
        };
    };
    get_image_thumb: {
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
            /** @description 이미지 바이너리 */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "image/jpeg": unknown;
                    "image/png": unknown;
                    "image/webp": unknown;
                };
            };
        };
    };
    images_search: {
        parameters: {
            query?: {
                /** @description 이전 응답의 next_cursor */
                cursor?: string | null;
                /** @description 등급 쉼표 목록. 기본 A,A?C,C(도식 D · 아이콘 E 제외 [제안]) */
                grades?: string | null;
                limit?: number;
                q?: string | null;
                source?: "all" | "official" | "case";
                /** @description 출처 페이지와 원본 URL 이 모두 있는 이미지만(KB 이미지는 모두 해당) */
                verified_only?: boolean;
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
                    "application/json": components["schemas"]["ImageSearchOut"];
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
    meta: {
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
                    "application/json": components["schemas"]["MetaOut"];
                };
            };
        };
    };
    list_models: {
        parameters: {
            query?: {
                category_id?: string | null;
                /** @description 이전 응답의 next_cursor */
                cursor?: string | null;
                family_id?: string | null;
                /** @description 기본 20, 최대 100 */
                limit?: number;
                /** @description 모델코드 일부 · 표시명 · 시리즈 코드 · 제품군 이름 */
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
                    "application/json": components["schemas"]["ModelList"];
                };
            };
        };
    };
    get_model: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 모델코드(LH55QMCEBGCXKR · / 가 든 코드는 %2F 로 · 그대로도 받음) · mdl_… · fam_…(대표 모델) */
                model_code: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelDetail"];
                };
            };
        };
    };
    get_model_cases: {
        parameters: {
            query?: {
                match?: ("model" | "series" | "usage") | null;
            };
            header?: never;
            path: {
                /** @description 모델코드(LH55QMCEBGCXKR · / 가 든 코드는 %2F 로 · 그대로도 받음) · mdl_… · fam_…(대표 모델) */
                model_code: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ModelCases"];
                };
            };
        };
    };
    get_model_images: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 모델코드(LH55QMCEBGCXKR · / 가 든 코드는 %2F 로 · 그대로도 받음) · mdl_… · fam_…(대표 모델) */
                model_code: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
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
    get_model_lifecycle: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 모델코드(LH55QMCEBGCXKR · / 가 든 코드는 %2F 로 · 그대로도 받음) · mdl_… · fam_…(대표 모델) */
                model_code: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Lifecycle"];
                };
            };
        };
    };
    list_patterns: {
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
                    "application/json": components["schemas"]["PatternList"];
                };
            };
        };
    };
    list_placement_rules: {
        parameters: {
            query?: {
                /** @description 시드 코드(signage · hvac_system_ac) 또는 KB 분류 id(cat_smart-signage · top_display · cat_smart-signage__videowall) — 분류를 주면 `*` 규칙도 함께 */
                category?: string | null;
                /** @description 공간 유형 id(그 공간 규칙 + `*`) */
                space?: string | null;
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
                    "application/json": components["schemas"]["PlacementRuleList"];
                };
            };
        };
    };
    products_search: {
        parameters: {
            query: {
                /** @description model · family 쉼표 목록 */
                kinds?: string;
                limit?: number;
                q: string;
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
                    "application/json": components["schemas"]["ProductSearchOut"];
                };
            };
        };
    };
    query_A1: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["A1Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_A2: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TextReq"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_A3: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["A3Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_B1: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["B1Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_B2: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TextReq"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_C1: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["C1Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_C2: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["C2Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_C3: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["C3Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_C4: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["C4Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_C6: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["C6Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_D1: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["D1Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_D2: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["D2Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_D3: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["D3Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_D5: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["D5Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_E1: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["E1Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_E2: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["E2Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_E3: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["E3Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_entity: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EntityReq"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_G1: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["G1Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_G2: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["G2Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_G4: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["G4Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_G5: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["G5Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_get_entity: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EntityReq"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_image_search: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ImageSearchReq"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_images: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ImageSearchReq"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_S1: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["S1Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_S2: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["S2Req"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    query_search: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SearchReq"];
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
                    "application/json": components["schemas"]["Envelope"];
                };
            };
        };
    };
    list_segments: {
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
                    "application/json": components["schemas"]["SegmentList"];
                };
            };
        };
    };
    get_segment_insights: {
        parameters: {
            query?: {
                top_items?: number;
                top_req?: number;
            };
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
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SegmentInsights"];
                };
            };
        };
    };
    classify_segments: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ClassifyIn"];
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
                    "application/json": components["schemas"]["ClassifyOut"];
                };
            };
        };
    };
    list_solutions: {
        parameters: {
            query?: {
                /** @description 이전 응답의 next_cursor */
                cursor?: string | null;
                industry?: ("retail" | "hospitality" | "education" | "healthcare" | "office") | null;
                /** @description 기본 20, 최대 100 */
                limit?: number;
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
                    "application/json": components["schemas"]["SolutionList"];
                };
            };
        };
    };
    get_solution: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                solution_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SolutionDetail"];
                };
            };
        };
    };
    get_solution_cases: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                solution_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SolutionCases"];
                };
            };
        };
    };
    get_solution_images: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                solution_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SolutionImages"];
                };
            };
        };
    };
    list_space_types: {
        parameters: {
            query?: {
                /** @description 그 업종 페이지에 나온 공간만(HAS_SPACE) */
                vertical_id?: string | null;
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
                    "application/json": components["schemas"]["SpaceTypeList"];
                };
            };
        };
    };
    list_spec_attributes: {
        parameters: {
            query?: {
                /** @description L1 · L2 분류(없으면 전체) */
                category_id?: string | null;
                /** @description 속성 · 그룹 이름 일부 또는 정규 키 */
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
                    "application/json": components["schemas"]["SpecAttrList"];
                };
            };
        };
    };
    spec_table: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SpecTableIn"];
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
                    "application/json": components["schemas"]["SpecTableOut"];
                };
            };
        };
    };
    list_verticals: {
        parameters: {
            query?: {
                /** @description 이전 응답의 next_cursor */
                cursor?: string | null;
                limit?: number;
                scheme?: "kr_site" | "us_site" | "winmate16";
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
                    "application/json": components["schemas"]["VerticalList"];
                };
            };
        };
    };
}
