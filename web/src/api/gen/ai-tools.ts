// 자동 생성 — 직접 고치지 말 것. 원본: contracts/ai-tools.json (make contracts)
export interface paths {
    "/v1/calls": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 모델 호출 로그(최신순) */
        get: operations["list_calls"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/calls/{call_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 호출 로그 하나 */
        get: operations["get_call"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/capabilities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 지금 제공자 · 모델 · 지원 기능 · 한도 · 오늘 사용량 */
        get: operations["get_capabilities"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/embed": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 임베딩 */
        post: operations["embed_texts"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/fetch": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 웹 페이지 수집(robots · 속도 제한 · 캐시) */
        post: operations["fetch_page"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/i2t/analyze": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 이미지 분석(글 · JSON · 박스) */
        post: operations["i2t_analyze"];
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
    "/v1/llm/chat": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** LLM 대화(JSON 스키마 · 도구 호출 · 기밀 정책 · 대체 경로) */
        post: operations["llm_chat"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/llm/stream": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * LLM 스트리밍(SSE)
         * @description SSE 이벤트: `delta` {text} 여러 번 → `done` {content, usage, call_id, …}. 오류는 `error` {code, message}. 스트리밍을 지원하지 않는 설정이거나 json_schema · tools 가 있으면 delta 한 번.
         */
        post: operations["llm_stream"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 검색 API(원문 URL 목록) */
        post: operations["search_api"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/t2i/edit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 이미지 편집(마스크 · 바깥 채우기 · 참조, 대체 경로 포함) */
        post: operations["t2i_edit"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/t2i/generate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 이미지 생성(files 서비스에 저장) */
        post: operations["t2i_generate"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/usage": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 오늘 사용량 대 한도 */
        get: operations["get_usage"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/websearch": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 요약형 웹 검색 */
        post: operations["websearch_summary"];
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
        /** Box */
        Box: {
            /**
             * Box
             * @description [x0, y0, x1, y1] 0..1 정규화
             */
            box: number[];
            /**
             * Image Index
             * @description 몇 번째 입력 이미지의 박스인지(0부터)
             * @default 0
             */
            image_index: number;
            /** Label */
            label: string;
            /** Score */
            score?: number | null;
        };
        /** CallList */
        CallList: {
            /** Items */
            items: components["schemas"]["CallRecord"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** CallRecord */
        CallRecord: {
            /**
             * Attempts
             * @default 0
             */
            attempts: number;
            /**
             * Caller
             * @description 호출한 서비스(X-Caller-Service)
             */
            caller?: string | null;
            /** Capability */
            capability: string;
            /**
             * Cassette
             * @description replay_hit · replay_miss · recorded
             */
            cassette?: string | null;
            /**
             * Confidential
             * @default false
             */
            confidential: boolean;
            /** Error */
            error?: {
                [key: string]: unknown;
            } | null;
            /** Fallback */
            fallback?: string | null;
            /** Id */
            id: string;
            /**
             * Latency Ms
             * @default 0
             */
            latency_ms: number;
            /** Mode */
            mode: string;
            /** Model */
            model?: string | null;
            /** Provider */
            provider?: string | null;
            /** Request */
            request?: unknown;
            /** Request Id */
            request_id?: string | null;
            /** Response */
            response?: unknown;
            /**
             * Status
             * @enum {string}
             */
            status: "ok" | "error" | "canceled";
            /** Task */
            task?: string | null;
            /** Ts */
            ts: string;
            usage?: components["schemas"]["Usage"];
            /** User Id */
            user_id?: string | null;
        };
        /** Capabilities */
        Capabilities: {
            embedding: components["schemas"]["EmbeddingCaps"];
            fetch: components["schemas"]["FetchCaps"];
            i2t: components["schemas"]["I2TCaps"];
            limits: components["schemas"]["Limits"];
            llm: components["schemas"]["LLMCaps"];
            /** Mode */
            mode: string;
            search_api: components["schemas"]["SearchApiCaps"];
            t2i: components["schemas"]["T2ICaps"];
            usage_today: components["schemas"]["UsageToday"];
            websearch: components["schemas"]["WebSearchCaps"];
        };
        /** CapLimits */
        CapLimits: {
            /**
             * Daily
             * @description 하루 한도(0 = 제한 없음). t2i 는 이미지 장수 기준
             */
            daily: number;
            /** Max Concurrency */
            max_concurrency: number;
            /**
             * Rpm
             * @description 분당 호출 수(0 = 제한 없음)
             */
            rpm: number;
            /** Timeout S */
            timeout_s: number;
        };
        /** CapUsage */
        CapUsage: {
            /** Daily Limit */
            daily_limit: number;
            /**
             * Remaining
             * @description daily_limit 이 0(무제한)이면 null
             */
            remaining: number | null;
            /** Rpm */
            rpm: number;
            /** This Minute */
            this_minute: number;
            /** Today */
            today: number;
        };
        /** ChatMessage */
        ChatMessage: {
            /**
             * Content
             * @default
             */
            content: string | (components["schemas"]["TextPart"] | components["schemas"]["ImagePart"])[];
            /**
             * Name
             * @description tool 메시지: 호출된 도구 이름
             */
            name?: string | null;
            /**
             * Role
             * @enum {string}
             */
            role: "system" | "user" | "assistant" | "tool";
            /**
             * Tool Call Id
             * @description tool 메시지: 어떤 tool_call 에 대한 결과인지
             */
            tool_call_id?: string | null;
            /**
             * Tool Calls
             * @description assistant 메시지: 앞서 받은 tool_calls 를 그대로
             */
            tool_calls?: components["schemas"]["ToolCall"][] | null;
        };
        /** ChatRequest */
        ChatRequest: {
            /**
             * Confidential
             * @default false
             */
            confidential: boolean;
            /**
             * Json Schema
             * @description 이 JSON 스키마에 맞는 결과를 json 으로 받는다
             */
            json_schema?: {
                [key: string]: unknown;
            } | null;
            /** Max Tokens */
            max_tokens?: number | null;
            /** Messages */
            messages: components["schemas"]["ChatMessage"][];
            /** Schema Name */
            schema_name?: string | null;
            /**
             * Task
             * @description <기능 코드 소문자>.<동작> (예: rq.extract_form)
             */
            task: string;
            /** Temperature */
            temperature?: number | null;
            /**
             * Tool Choice
             * @description auto | none | required | <도구 이름>
             */
            tool_choice?: string | null;
            /** Tools */
            tools?: components["schemas"]["ToolSpec"][] | null;
        };
        /** ChatResponse */
        ChatResponse: {
            /** Call Id */
            call_id: string;
            /**
             * Content
             * @default
             */
            content: string;
            /**
             * Fallback
             * @default none
             * @enum {string}
             */
            fallback: "none" | "json_parse" | "json_repair" | "react";
            /**
             * Finish Reason
             * @default stop
             */
            finish_reason: string;
            /**
             * Json
             * @description json_schema 를 줬을 때 스키마에 맞는 값
             */
            json?: unknown;
            /**
             * Latency Ms
             * @default 0
             */
            latency_ms: number;
            /** Model */
            model: string;
            /** Provider */
            provider: string;
            /** Tool Calls */
            tool_calls?: components["schemas"]["ToolCall"][];
            usage?: components["schemas"]["Usage"];
        };
        /** EmbeddingCaps */
        EmbeddingCaps: {
            /** Available */
            available: boolean;
            /** Dim */
            dim?: number | null;
            /** Model */
            model: string;
            /** Provider */
            provider: string;
        };
        /** EmbedRequest */
        EmbedRequest: {
            /**
             * Kind
             * @default passage
             * @enum {string}
             */
            kind: "query" | "passage";
            /** Texts */
            texts: string[];
        };
        /** EmbedResponse */
        EmbedResponse: {
            /** Dim */
            dim: number;
            /** Model */
            model: string;
            /** Provider */
            provider: string;
            /** Vectors */
            vectors: number[][];
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
        /** FetchCaps */
        FetchCaps: {
            /** Enabled */
            enabled: boolean;
        };
        /** FetchRequest */
        FetchRequest: {
            /**
             * Max Chars
             * @default 20000
             */
            max_chars: number;
            /** Url */
            url: string;
        };
        /** FetchResponse */
        FetchResponse: {
            /**
             * Allowed
             * @default true
             */
            allowed: boolean;
            /**
             * Content Hash
             * @description 본문 텍스트 sha256
             */
            content_hash?: string | null;
            /** Content Type */
            content_type?: string | null;
            /** Fetched At */
            fetched_at: string;
            /** Final Url */
            final_url?: string | null;
            /**
             * From Cache
             * @default false
             */
            from_cache: boolean;
            /**
             * Pages
             * @description PDF 면 페이지별 텍스트
             */
            pages?: string[] | null;
            /** Published At */
            published_at?: string | null;
            /**
             * Reason
             * @description disabled · invalid_url · domain_not_allowed · robots_disallow · http_error · unsupported_content_type …
             */
            reason?: string | null;
            /**
             * Status
             * @default 0
             */
            status: number;
            /**
             * Text
             * @default
             */
            text: string;
            /**
             * Title
             * @default
             */
            title: string;
            /**
             * Truncated
             * @default false
             */
            truncated: boolean;
            /** Url */
            url: string;
        };
        /** GeneratedImage */
        GeneratedImage: {
            /** File Id */
            file_id: string;
            /** Height */
            height: number;
            /** Mime */
            mime: string;
            /** Width */
            width: number;
        };
        /** I2TCaps */
        I2TCaps: {
            /** Allow Confidential */
            allow_confidential: boolean;
            /**
             * Available
             * @default true
             */
            available: boolean;
            /** Max Image Side Px */
            max_image_side_px: number;
            /** Max Images Per Call */
            max_images_per_call: number;
            /** Model */
            model: string;
            /** Provider */
            provider: string;
            supports: components["schemas"]["I2TSupports"];
        };
        /** I2TRequest */
        I2TRequest: {
            /**
             * Confidential
             * @default false
             */
            confidential: boolean;
            /** Images */
            images: components["schemas"]["ImageRef"][];
            /** Json Schema */
            json_schema?: {
                [key: string]: unknown;
            } | null;
            /** Max Tokens */
            max_tokens?: number | null;
            /** Prompt */
            prompt: string;
            /** Task */
            task: string;
            /**
             * Want Bbox
             * @default false
             */
            want_bbox: boolean;
        };
        /** I2TResponse */
        I2TResponse: {
            /** Boxes */
            boxes?: components["schemas"]["Box"][];
            /** Call Id */
            call_id: string;
            /**
             * Content
             * @default
             */
            content: string;
            /**
             * Fallback
             * @default none
             * @enum {string}
             */
            fallback: "none" | "json_parse" | "json_repair" | "react";
            /** Json */
            json?: unknown;
            /**
             * Latency Ms
             * @default 0
             */
            latency_ms: number;
            /** Model */
            model: string;
            /** Provider */
            provider: string;
            usage?: components["schemas"]["Usage"];
            /** Warnings */
            warnings?: string[];
        };
        /** I2TSupports */
        I2TSupports: {
            /** Bbox */
            bbox: boolean;
            /** Json Schema */
            json_schema: boolean;
        };
        /** ImagePart */
        ImagePart: {
            /** Data B64 */
            data_b64?: string | null;
            /** File Id */
            file_id?: string | null;
            /** Mime */
            mime?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "image";
            /** Url */
            url?: string | null;
        };
        /**
         * ImageRef
         * @description 이미지 하나: file_id(files 서비스) · url(http(s) 또는 data:) · data_b64(+mime) 중 하나.
         */
        ImageRef: {
            /** Data B64 */
            data_b64?: string | null;
            /** File Id */
            file_id?: string | null;
            /** Mime */
            mime?: string | null;
            /** Url */
            url?: string | null;
        };
        /** Limits */
        Limits: {
            /**
             * Enforced
             * @description live · record 모드에서만 한도를 적용한다
             */
            enforced: boolean;
            i2t: components["schemas"]["CapLimits"];
            llm: components["schemas"]["CapLimits"];
            t2i: components["schemas"]["CapLimits"];
            websearch: components["schemas"]["CapLimits"];
        };
        /** LLMCaps */
        LLMCaps: {
            /** Allow Confidential */
            allow_confidential: boolean;
            /**
             * Available
             * @default true
             */
            available: boolean;
            /** Max Input Tokens */
            max_input_tokens: number;
            /** Max Output Tokens */
            max_output_tokens: number;
            /** Model */
            model: string;
            /** Provider */
            provider: string;
            supports: components["schemas"]["LLMSupports"];
        };
        /** LLMSupports */
        LLMSupports: {
            /** Json Schema */
            json_schema: boolean;
            /** Streaming */
            streaming: boolean;
            /** Tools */
            tools: boolean;
        };
        /**
         * MaskRef
         * @description 수정할 영역: 마스크 이미지(file_id · data_b64 · url; 흰색=수정, 알파가 있으면 투명=수정) 또는 box(0..1 정규화).
         */
        MaskRef: {
            /**
             * Box
             * @description [x0, y0, x1, y1] 0..1
             */
            box?: number[] | null;
            /** Data B64 */
            data_b64?: string | null;
            /** File Id */
            file_id?: string | null;
            /** Mime */
            mime?: string | null;
            /** Url */
            url?: string | null;
        };
        /** ReferenceImage */
        ReferenceImage: {
            /** Data B64 */
            data_b64?: string | null;
            /** File Id */
            file_id?: string | null;
            /** Mime */
            mime?: string | null;
            /**
             * Role
             * @default subject
             * @enum {string}
             */
            role: "product" | "style" | "composition" | "subject" | "base";
            /**
             * Strength
             * @default mid
             * @enum {string}
             */
            strength: "low" | "mid" | "high";
            /** Url */
            url?: string | null;
        };
        /** SearchApiCaps */
        SearchApiCaps: {
            /** Available */
            available: boolean;
            /** Provider */
            provider: string;
        };
        /** SearchRequest */
        SearchRequest: {
            /**
             * Limit
             * @default 10
             */
            limit: number;
            /**
             * Locale
             * @default ko-KR
             */
            locale: string;
            /** Query */
            query: string;
        };
        /** SearchResponse */
        SearchResponse: {
            /** Available */
            available: boolean;
            /** Provider */
            provider: string;
            /** Results */
            results?: components["schemas"]["SearchResult"][];
        };
        /** SearchResult */
        SearchResult: {
            /** Published At */
            published_at?: string | null;
            /**
             * Snippet
             * @default
             */
            snippet: string;
            /**
             * Title
             * @default
             */
            title: string;
            /** Url */
            url: string;
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
        /** Source */
        Source: {
            /** Snippet */
            snippet?: string | null;
            /**
             * Title
             * @default
             */
            title: string;
            /** Url */
            url: string;
        };
        /** T2ICaps */
        T2ICaps: {
            /** Allow Confidential */
            allow_confidential: boolean;
            /**
             * Available
             * @default true
             */
            available: boolean;
            /** Default Aspect */
            default_aspect: string;
            /** Images Per Call */
            images_per_call: number;
            /** Max Reference Images */
            max_reference_images: number;
            /** Max Side Px */
            max_side_px: number;
            /** Model */
            model: string;
            /** Provider */
            provider: string;
            supports: components["schemas"]["T2ISupports"];
        };
        /** T2IEditRequest */
        T2IEditRequest: {
            /**
             * Aspect
             * @description 원본과 다르면 캔버스를 넓혀 바깥을 채운다(outpaint)
             */
            aspect?: string | null;
            /**
             * Confidential
             * @default false
             */
            confidential: boolean;
            image: components["schemas"]["ImageRef"];
            mask?: components["schemas"]["MaskRef"] | null;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /**
             * N
             * @default 1
             */
            n: number;
            /** Prompt */
            prompt: string;
            /** Reference Images */
            reference_images?: components["schemas"]["ReferenceImage"][] | null;
            /** Task */
            task: string;
        };
        /** T2IGenerateRequest */
        T2IGenerateRequest: {
            /**
             * Aspect
             * @description 예: "16:9" "4:3" "1:1" "9:16" "21:9" (기본 T2I_DEFAULT_ASPECT)
             */
            aspect?: string | null;
            /**
             * Confidential
             * @default false
             */
            confidential: boolean;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /**
             * N
             * @default 1
             */
            n: number;
            /** Negative Prompt */
            negative_prompt?: string | null;
            /** Prompt */
            prompt: string;
            /** Reference Images */
            reference_images?: components["schemas"]["ReferenceImage"][] | null;
            /** Seed */
            seed?: number | null;
            /** Style */
            style?: string | null;
            /** Task */
            task: string;
        };
        /** T2IResponse */
        T2IResponse: {
            /** Call Id */
            call_id: string;
            /**
             * Fallbacks
             * @description references_dropped · mask_crop_paste · outpaint_extend · edit_as_generate · aspect_cropped
             */
            fallbacks?: string[];
            /** Images */
            images?: components["schemas"]["GeneratedImage"][];
            /**
             * Latency Ms
             * @default 0
             */
            latency_ms: number;
            /** Model */
            model: string;
            /** Provider */
            provider: string;
            /** Warnings */
            warnings?: string[];
        };
        /** T2ISupports */
        T2ISupports: {
            /** Edit */
            edit: boolean;
            /** Mask */
            mask: boolean;
            /** Reference Images */
            reference_images: boolean;
        };
        /** TextPart */
        TextPart: {
            /** Text */
            text: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "text";
        };
        /** ToolCall */
        ToolCall: {
            /** Arguments */
            arguments?: {
                [key: string]: unknown;
            };
            /** Id */
            id: string;
            /** Name */
            name: string;
        };
        /** ToolSpec */
        ToolSpec: {
            /**
             * Description
             * @default
             */
            description: string;
            /** Name */
            name: string;
            /** Parameters */
            parameters?: {
                [key: string]: unknown;
            };
        };
        /** Usage */
        Usage: {
            /**
             * Input Tokens
             * @default 0
             */
            input_tokens: number;
            /**
             * Output Tokens
             * @default 0
             */
            output_tokens: number;
        };
        /** UsageResponse */
        UsageResponse: {
            /** Date */
            date: string;
            /** Enforced */
            enforced: boolean;
            /** Mode */
            mode: string;
            /** Usage */
            usage: {
                [key: string]: components["schemas"]["CapUsage"];
            };
        };
        /** UsageToday */
        UsageToday: {
            /**
             * I2T
             * @default 0
             */
            i2t: number;
            /**
             * Llm
             * @default 0
             */
            llm: number;
            /**
             * T2I
             * @default 0
             */
            t2i: number;
            /**
             * Websearch
             * @default 0
             */
            websearch: number;
        };
        /** WebSearchCaps */
        WebSearchCaps: {
            /** Allow Confidential */
            allow_confidential: boolean;
            /**
             * Available
             * @default true
             */
            available: boolean;
            /** Model */
            model: string;
            /** Provider */
            provider: string;
            /** Return Sources */
            return_sources: boolean;
        };
        /** WebSearchRequest */
        WebSearchRequest: {
            /**
             * Confidential
             * @default false
             */
            confidential: boolean;
            /**
             * Locale
             * @default ko-KR
             */
            locale: string;
            /**
             * Max Sources
             * @default 8
             */
            max_sources: number;
            /** Query */
            query: string;
            /** Task */
            task: string;
        };
        /** WebSearchResponse */
        WebSearchResponse: {
            /** Call Id */
            call_id: string;
            /**
             * Latency Ms
             * @default 0
             */
            latency_ms: number;
            /** Model */
            model: string;
            /** Provider */
            provider: string;
            /** Queries */
            queries?: string[];
            /**
             * Returned Sources
             * @default false
             */
            returned_sources: boolean;
            /** Sources */
            sources?: components["schemas"]["Source"][];
            /**
             * Summary
             * @default
             */
            summary: string;
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
    list_calls: {
        parameters: {
            query?: {
                capability?: string | null;
                cursor?: string | null;
                limit?: number;
                task?: string | null;
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
                    "application/json": components["schemas"]["CallList"];
                };
            };
        };
    };
    get_call: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                call_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 요청 오류 */
            "4XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 서버 오류 */
            "5XX": {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CallRecord"];
                };
            };
        };
    };
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
    embed_texts: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EmbedRequest"];
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
                    "application/json": components["schemas"]["EmbedResponse"];
                };
            };
        };
    };
    fetch_page: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FetchRequest"];
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
                    "application/json": components["schemas"]["FetchResponse"];
                };
            };
        };
    };
    i2t_analyze: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["I2TRequest"];
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
                    "application/json": components["schemas"]["I2TResponse"];
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
    llm_chat: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChatRequest"];
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
                    "application/json": components["schemas"]["ChatResponse"];
                };
            };
        };
    };
    llm_stream: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChatRequest"];
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
            /** @description text/event-stream */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "text/event-stream": string;
                };
            };
        };
    };
    search_api: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SearchRequest"];
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
                    "application/json": components["schemas"]["SearchResponse"];
                };
            };
        };
    };
    t2i_edit: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["T2IEditRequest"];
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
                    "application/json": components["schemas"]["T2IResponse"];
                };
            };
        };
    };
    t2i_generate: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["T2IGenerateRequest"];
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
                    "application/json": components["schemas"]["T2IResponse"];
                };
            };
        };
    };
    get_usage: {
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
                    "application/json": components["schemas"]["UsageResponse"];
                };
            };
        };
    };
    websearch_summary: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WebSearchRequest"];
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
                    "application/json": components["schemas"]["WebSearchResponse"];
                };
            };
        };
    };
}
