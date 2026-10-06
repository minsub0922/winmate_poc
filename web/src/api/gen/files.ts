// 자동 생성 — 직접 고치지 말 것. 원본: contracts/files.json (make contracts)
export interface paths {
    "/v1/files": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 파일 목록(최신순) */
        get: operations["list_files"];
        put?: never;
        /** 파일 올리기(multipart) */
        post: operations["upload_file"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/files/{file_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 파일 메타 */
        get: operations["get_file"];
        put?: never;
        post?: never;
        /** 지우기(소프트 삭제 — 같은 내용을 쓰는 다른 파일이 있으면 바이너리는 남긴다) */
        delete: operations["delete_file"];
        options?: never;
        head?: never;
        /** 이름 · 기밀 · 프로젝트 · 메타 바꾸기 */
        patch: operations["patch_file"];
        trace?: never;
    };
    "/v1/files/{file_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 내용 내려받기(?download=1 이면 attachment) */
        get: operations["get_content"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/files/{file_id}/copy": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 사본 만들기(같은 바이너리, 다른 폴더 · 프로젝트) */
        post: operations["copy_file"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/files/{file_id}/pages/{n}/image": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** n 쪽 그림(PDF · LibreOffice 있으면 PPTX/DOCX/XLSX · 이미지는 1쪽) */
        get: operations["get_page_image"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/files/{file_id}/pages/{n}/thumbnail": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** n 쪽 썸네일(렌더러가 없으면 PPTX 는 슬라이드 자리표시 카드) */
        get: operations["get_page_thumbnail"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/files/{file_id}/parse": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 파싱 시작(백그라운드). force=true 면 캐시를 버리고 다시 읽는다 */
        post: operations["start_parse"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/files/{file_id}/parsed": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 문서 파싱 결과(쪽 · 블록 · 표 · 시트 · 메일). 처음이면 읽을 때까지 기다린다 */
        get: operations["get_parsed"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/files/{file_id}/thumbnail": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** 썸네일(이미지 축소 · PDF/PPTX 첫 쪽 · 형식 아이콘) */
        get: operations["get_thumbnail"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/files/bytes": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** 바이트 저장(서비스 간) */
        post: operations["save_bytes"];
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
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** Attachment */
        Attachment: {
            /** File Id */
            file_id?: string | null;
            /**
             * Inline
             * @default false
             */
            inline: boolean;
            /** Mime */
            mime: string;
            /** Name */
            name: string;
            /** Size */
            size: number;
        };
        /** Block */
        Block: {
            /**
             * Bbox
             * @description [x0, y0, x1, y1] 쪽 크기 대비 0..1(왼쪽 위 원점)
             */
            bbox?: number[] | null;
            /**
             * File Id
             * @description image 블록의 추출 이미지 file id
             */
            file_id?: string | null;
            /**
             * Font Size
             * @description 글자 크기(pt), 알 때만
             */
            font_size?: number | null;
            /**
             * Level
             * @description 제목 수준(1 = 가장 큼)
             */
            level?: number | null;
            /**
             * Line
             * @description 텍스트 파일의 시작 줄 번호(1부터)
             */
            line?: number | null;
            /**
             * Text
             * @default
             */
            text: string;
            /**
             * Type
             * @enum {string}
             */
            type: "title" | "heading" | "body" | "list" | "table" | "image" | "note" | "caption";
        };
        /** Body_upload_file */
        Body_upload_file: {
            /**
             * Confidential
             * @description 고객 기밀 자료
             * @default false
             */
            confidential: boolean;
            /**
             * File
             * @description 파일 하나(최대 UPLOAD_MAX_MB, 기본 50MB). HEIC/HEIF 는 JPEG 로 바꿔 저장
             */
            file: string;
            /** Folder */
            folder?: string | null;
            /** Parent Id */
            parent_id?: string | null;
            /** Project Id */
            project_id?: string | null;
            /**
             * Purpose
             * @description 용도 태그(예 rq.source · logo · site_photo)
             */
            purpose?: string | null;
            /**
             * Source
             * @default upload
             * @enum {string}
             */
            source: "upload" | "generated" | "derived" | "export";
        };
        /**
         * BytesUpload
         * @description 서비스 간 저장(내부). 바이트는 base64.
         */
        BytesUpload: {
            /**
             * Confidential
             * @default false
             */
            confidential: boolean;
            /** Data B64 */
            data_b64: string;
            /** Folder */
            folder?: string | null;
            /** Meta */
            meta?: {
                [key: string]: unknown;
            } | null;
            /**
             * Mime
             * @description 모르면 비워 두면 내용으로 판별
             * @default application/octet-stream
             */
            mime: string;
            /** Name */
            name: string;
            /**
             * Parent Id
             * @description 원본 file id(주면 confidential · project_id 를 이어받는다)
             */
            parent_id?: string | null;
            /** Project Id */
            project_id?: string | null;
            /** Purpose */
            purpose?: string | null;
            /**
             * Source
             * @default generated
             * @enum {string}
             */
            source: "upload" | "generated" | "derived" | "export";
        };
        /** CopyRequest */
        CopyRequest: {
            /**
             * Folder
             * @description 복사본을 둘 폴더(예 'B2B 제안서/A 커피')
             */
            folder?: string | null;
            /** Name */
            name?: string | null;
            /** Project Id */
            project_id?: string | null;
        };
        /** DocMeta */
        DocMeta: {
            /** Author */
            author?: string | null;
            /** Created */
            created?: string | null;
            /** Modified */
            modified?: string | null;
            /** Producer */
            producer?: string | null;
            slide_size?: components["schemas"]["SlideSize"] | null;
            /** Subject */
            subject?: string | null;
            /** Title */
            title?: string | null;
        } & {
            [key: string]: unknown;
        };
        /**
         * DocProps
         * @description 문서 속성(PDF 정보 사전 · OOXML docProps · 메일 머리 · 사진 EXIF). 없는 값은 null.
         */
        DocProps: {
            /**
             * Author
             * @description 작성자(PDF Author · dc:creator · 메일 보낸 사람 · EXIF Artist)
             */
            author?: string | null;
            /** Company */
            company?: string | null;
            /**
             * Created
             * @description 작성 시각(ISO 8601 UTC). 사진은 촬영 시각
             */
            created?: string | null;
            /** Last Modified By */
            last_modified_by?: string | null;
            /** Modified */
            modified?: string | null;
            /**
             * Producer
             * @description 만든 프로그램(PDF Producer · OOXML Application)
             */
            producer?: string | null;
            /** Subject */
            subject?: string | null;
            /** Title */
            title?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** EmailInfo */
        EmailInfo: {
            /**
             * Attachment List
             * @description 첨부 전체(이름 · 형식 · 크기 · 본문 안 그림 여부)
             */
            attachment_list?: components["schemas"]["Attachment"][];
            /**
             * Attachments
             * @description 첨부(본문 안 그림 제외) file id
             */
            attachments?: string[];
            /**
             * Body
             * @default
             */
            body: string;
            /** Cc */
            cc?: string[];
            /**
             * Date
             * @description ISO 8601 UTC
             */
            date?: string | null;
            /** From */
            from?: string | null;
            /** Subject */
            subject?: string | null;
            /** To */
            to?: string[];
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
        /** FileList */
        FileList: {
            /** Items */
            items: components["schemas"]["FileMeta"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** FileMeta */
        FileMeta: {
            /** Confidential */
            confidential: boolean;
            /** Created At */
            created_at: string;
            doc_props?: components["schemas"]["DocProps"] | null;
            /**
             * Folder
             * @description 공유 폴더 경로(예 'B2B 제안서/A 커피')
             */
            folder?: string | null;
            /** Height */
            height?: number | null;
            /**
             * Id
             * @description file_<ULID>
             */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "pdf" | "pptx" | "docx" | "xlsx" | "image" | "text" | "email" | "svg" | "zip" | "other";
            /**
             * Meta
             * @description 부가 정보(original_mime · exif · encoding · format · depth …)
             */
            meta?: {
                [key: string]: unknown;
            };
            /** Mime */
            mime: string;
            /**
             * Name
             * @description 파일 이름(NFC 정규화, 경로 제거). HEIC 는 변환 뒤 .jpg
             */
            name: string;
            /**
             * Owner
             * @description 올린 사용자 id(X-User-Id)
             */
            owner: string;
            /** Owner Name */
            owner_name: string;
            /**
             * Pages
             * @description 쪽 수(PDF 쪽 · PPTX 슬라이드 · XLSX 시트 · DOCX 추정 쪽)
             */
            pages?: number | null;
            /**
             * Parent Id
             * @description 자식 파일(추출 이미지 · 메일 첨부)이면 원본 file id
             */
            parent_id: string | null;
            parse_error?: components["schemas"]["ErrorInfo"] | null;
            /**
             * Parse Status
             * @description none(요청 전) · pending · parsing · done · failed · unsupported. 업로드(source=upload)는 올리자마자 파싱을 시작한다
             * @default none
             * @enum {string}
             */
            parse_status: "none" | "pending" | "parsing" | "done" | "failed" | "unsupported";
            /** Project Id */
            project_id: string | null;
            /**
             * Purpose
             * @description 용도 태그(예 rq.source · logo · site_photo)
             */
            purpose?: string | null;
            /** Sha256 */
            sha256: string;
            /**
             * Size
             * @description 바이트 수(저장된 바이너리 기준)
             */
            size: number;
            /**
             * Source
             * @enum {string}
             */
            source: "upload" | "generated" | "derived" | "export";
            /**
             * Thumb Url
             * @description /api/files/v1/files/{id}/thumbnail
             */
            thumb_url: string;
            /** Updated At */
            updated_at?: string | null;
            /**
             * Url
             * @description /api/files/v1/files/{id}/content
             */
            url: string;
            /**
             * Width
             * @description 이미지 · SVG 가로(px, EXIF 회전 반영)
             */
            width?: number | null;
        };
        /** FilePatch */
        FilePatch: {
            /** Confidential */
            confidential?: boolean | null;
            /** Folder */
            folder?: string | null;
            /**
             * Meta
             * @description 얕은 병합. 값이 null 인 키는 지운다
             */
            meta?: {
                [key: string]: unknown;
            } | null;
            /** Name */
            name?: string | null;
            /** Project Id */
            project_id?: string | null;
            /** Purpose */
            purpose?: string | null;
        };
        /** Page */
        Page: {
            /** Blocks */
            blocks?: components["schemas"]["Block"][];
            /**
             * Hidden
             * @description 숨긴 슬라이드면 true
             */
            hidden?: boolean | null;
            /** Image File Ids */
            image_file_ids?: string[];
            /**
             * Images
             * @description 쪽 안 이미지 위치(bbox)
             */
            images?: components["schemas"]["PageImage"][];
            /**
             * Layout
             * @description 슬라이드 레이아웃 이름(PPTX)
             */
            layout?: string | null;
            /**
             * No
             * @description 1부터
             */
            no: number;
            /**
             * Notes
             * @description 발표자 노트(PPTX)
             */
            notes?: string | null;
            /**
             * Section
             * @description PowerPoint 구역 이름
             */
            section?: string | null;
            /**
             * Size
             * @description [가로, 세로] pt
             */
            size?: number[] | null;
            /** Tables */
            tables?: string[][][];
            /**
             * Text
             * @default
             */
            text: string;
            /**
             * Title
             * @description 쪽 · 슬라이드 제목(추정)
             */
            title?: string | null;
        };
        /** PageImage */
        PageImage: {
            /** Bbox */
            bbox?: number[] | null;
            /** File Id */
            file_id: string;
        };
        /** ParseAccepted */
        ParseAccepted: {
            /** File Id */
            file_id: string;
            /**
             * Parse Status
             * @enum {string}
             */
            parse_status: "none" | "pending" | "parsing" | "done" | "failed" | "unsupported";
            /** Parser Version */
            parser_version: string;
        };
        /** ParsedDocument */
        ParsedDocument: {
            email?: components["schemas"]["EmailInfo"] | null;
            /** File Id */
            file_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "pdf" | "pptx" | "docx" | "xlsx" | "image" | "text" | "email" | "svg" | "zip" | "other";
            meta?: components["schemas"]["DocMeta"];
            /**
             * Page Count
             * @default 0
             */
            page_count: number;
            /** Pages */
            pages?: components["schemas"]["Page"][];
            /** Parser Version */
            parser_version: string;
            /** Sheets */
            sheets?: components["schemas"]["Sheet"][] | null;
            /**
             * Text
             * @description 쪽 순서 본문(최대 500,000자)
             * @default
             */
            text: string;
            /** Title */
            title?: string | null;
            /**
             * Warnings
             * @description 예 scanned_page:3(글자 층 없는 쪽 → i2t), text_truncated, layout_skipped_after:300, children_skipped:depth
             */
            warnings?: string[];
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
            /**
             * Dims
             * @description 예 A1:F120
             */
            dims?: string | null;
            /**
             * Hidden
             * @default false
             */
            hidden: boolean;
            /**
             * Merged
             * @description 병합 범위(예 A1:C1). 값은 왼쪽 위 칸에만 있다
             */
            merged?: string[];
            /** Name */
            name: string;
            /**
             * Row Count
             * @description 읽은 행 수(잘렸으면 truncated)
             * @default 0
             */
            row_count: number;
            /**
             * Rows
             * @description 값(수식은 마지막 계산값). 시트당 2000행까지
             */
            rows: (string | number | boolean | null)[][];
            /**
             * Truncated
             * @default false
             */
            truncated: boolean;
        };
        /** SlideSize */
        SlideSize: {
            /**
             * Aspect
             * @description 예 16:9 · 4:3
             */
            aspect: string;
            /** Height Emu */
            height_emu: number;
            /** Height Mm */
            height_mm: number;
            /** Width Emu */
            width_emu: number;
            /** Width Mm */
            width_mm: number;
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
    list_files: {
        parameters: {
            query?: {
                cursor?: string | null;
                folder?: string | null;
                /** @description 자식 파일도 함께(기본은 원본만) */
                include_children?: boolean;
                /** @description pdf|pptx|docx|xlsx|image|text|email|svg|zip|other — 쉼표로 여러 개 */
                kind?: string | null;
                limit?: number;
                /** @description me | all | <user id>. 남의 기밀 파일은 project_id 로 거를 때만 보인다 */
                owner?: string;
                /** @description 이 파일의 자식(추출 이미지 · 첨부) */
                parent_id?: string | null;
                project_id?: string | null;
                purpose?: string | null;
                /** @description 이름 포함 검색 */
                q?: string | null;
                source?: ("upload" | "generated" | "derived" | "export") | null;
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
                    "application/json": components["schemas"]["FileList"];
                };
            };
        };
    };
    upload_file: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_upload_file"];
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
                    "application/json": components["schemas"]["FileMeta"];
                };
            };
        };
    };
    get_file: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description file_<ULID> */
                file_id: string;
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
                    "application/json": components["schemas"]["FileMeta"];
                };
            };
        };
    };
    delete_file: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description file_<ULID> */
                file_id: string;
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
    patch_file: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description file_<ULID> */
                file_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FilePatch"];
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
                    "application/json": components["schemas"]["FileMeta"];
                };
            };
        };
    };
    get_content: {
        parameters: {
            query?: {
                download?: boolean;
            };
            header?: never;
            path: {
                /** @description file_<ULID> */
                file_id: string;
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
            /** @description 파일 바이트 */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/octet-stream": string;
                };
            };
        };
    };
    copy_file: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description file_<ULID> */
                file_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CopyRequest"];
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
                    "application/json": components["schemas"]["FileMeta"];
                };
            };
        };
    };
    get_page_image: {
        parameters: {
            query?: {
                format?: "png" | "jpeg" | "webp";
                w?: number;
            };
            header?: never;
            path: {
                /** @description file_<ULID> */
                file_id: string;
                /** @description 1부터 */
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
            /** @description 쪽 그림(PNG 기본) */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "image/png": string;
                };
            };
        };
    };
    get_page_thumbnail: {
        parameters: {
            query?: {
                format?: "webp" | "png";
                w?: number;
            };
            header?: never;
            path: {
                /** @description file_<ULID> */
                file_id: string;
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
            /** @description 쪽 썸네일 */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "image/png": string;
                    "image/webp": string;
                };
            };
        };
    };
    start_parse: {
        parameters: {
            query?: {
                force?: boolean;
            };
            header?: never;
            path: {
                /** @description file_<ULID> */
                file_id: string;
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
                    "application/json": components["schemas"]["ParseAccepted"];
                };
            };
        };
    };
    get_parsed: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description file_<ULID> */
                file_id: string;
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
                    "application/json": components["schemas"]["ParsedDocument"];
                };
            };
        };
    };
    get_thumbnail: {
        parameters: {
            query?: {
                format?: "webp" | "png";
                /** @description 가로 px */
                w?: number;
            };
            header?: never;
            path: {
                /** @description file_<ULID> */
                file_id: string;
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
            /** @description 썸네일 */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "image/png": string;
                    "image/webp": string;
                };
            };
        };
    };
    save_bytes: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BytesUpload"];
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
                    "application/json": components["schemas"]["FileMeta"];
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
}
