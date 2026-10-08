// 자동 생성 — 직접 고치지 말 것. 원본: contracts/export.json (make contracts)
export interface paths {
    "/v1/exports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Exports */
        get: operations["list_exports"];
        put?: never;
        /** Create Export */
        post: operations["create_export"];
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
    "/v1/masters": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Masters */
        get: operations["list_masters"];
        put?: never;
        /** Create Master */
        post: operations["create_master"];
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
        /** Create Render */
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
    "/v1/templates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Templates */
        get: operations["list_templates"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/templates/{code}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Template */
        get: operations["get_template"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/templates/{code}/board.jpg": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Template Board
         * @description 레이아웃 브라우저용 — 원본 보드 그림. 보드가 없거나(제작 중) 아직 그리지 않았으면 404 `BOARD_NOT_RENDERED`.
         */
        get: operations["template_board"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/templates/{code}/thumbnail.png": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Template Thumbnail */
        get: operations["template_thumbnail"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/templates/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Template Stats */
        get: operations["template_stats"];
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
        /** Box */
        Box: {
            /** H */
            h: number;
            /**
             * Index
             * @description 목록 칸의 몇 번째 항목인지
             */
            index?: number | null;
            /**
             * Part
             * @description 카드 항목의 필드 하나만 그리는 상자
             */
            part?: string | null;
            /**
             * Slot
             * @description 칸 이름(null 이면 장식)
             */
            slot?: string | null;
            /** Style */
            style: string;
            /** W */
            w: number;
            /**
             * X
             * @description 16:9 슬라이드 기준 0..1
             */
            x: number;
            /** Y */
            y: number;
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
        /** ExportAccepted */
        ExportAccepted: {
            /** Export Id */
            export_id: string;
            /** Job Id */
            job_id: string;
            /**
             * Status
             * @constant
             */
            status: "queued";
        };
        /** ExportError */
        ExportError: {
            /** Code */
            code: string;
            /** Message */
            message: string;
        };
        /** ExportFile */
        ExportFile: {
            /** Id */
            id: string;
            /** Lang */
            lang?: string | null;
            /** Mime */
            mime: string;
            /** Name */
            name: string;
            /** Size */
            size: number;
            /** Url */
            url: string;
        };
        /** ExportList */
        ExportList: {
            /** Items */
            items: components["schemas"]["ExportRecord"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** ExportRecord */
        ExportRecord: {
            /** Bilingual */
            bilingual?: string | null;
            /** Confidential */
            confidential?: boolean | null;
            /** Created At */
            created_at?: string | null;
            error?: components["schemas"]["ExportError"] | null;
            /** Export Id */
            export_id: string;
            file?: components["schemas"]["ExportFile"] | null;
            /** Filename */
            filename?: string | null;
            /** Files */
            files?: components["schemas"]["ExportFile"][];
            form_fill?: components["schemas"]["FormFillReport"] | null;
            /** Format */
            format: string;
            /** Job Id */
            job_id?: string | null;
            /** Language */
            language?: string | null;
            /** Mode */
            mode?: string | null;
            /** Owner */
            owner?: string | null;
            /** Project Id */
            project_id?: string | null;
            /** Slide Count */
            slide_count?: number | null;
            /** Source Ref */
            source_ref?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "done" | "failed";
            /** Template Codes */
            template_codes?: string[];
            /** Updated At */
            updated_at?: string | null;
            /** Warnings */
            warnings?: string[];
        };
        /** ExportRequest */
        ExportRequest: {
            /**
             * Async
             * @description true 면 늘 잡(202)으로
             */
            async?: boolean | null;
            /**
             * Base File Id
             * @description xlsx: 고객사 양식(.xlsx · .xlsm · .xltx · .xls · .ods — 옛 형식은 LibreOffice 필요) — 이 파일 사본의 칸에 값만 써 넣는다(서식 · 병합 · 수식 · 열 너비 유지). document.sheets(행 이름 × 열 머리로 맞춤) · fills(칸 하나씩) 중 하나 이상. 기밀 · project_id 는 원본을 이어받는다. 결과는 form_fill 보고
             */
            base_file_id?: string | null;
            /**
             * Bilingual
             * @description language=both 일 때: files(기본, _KO · _EN 두 파일) · slides(한 덱에 KO/EN 번갈아) · inline(한 칸에 두 줄)
             */
            bilingual?: ("files" | "slides" | "inline") | null;
            /**
             * Confidential
             * @default false
             */
            confidential: boolean;
            /**
             * Customer Template File Id
             * @description base_file_id 와 같다
             */
            customer_template_file_id?: string | null;
            /**
             * Design
             * @description {brand_hex?, master_id?(samsung_b2b · retail_fnb · simple_white · mst_…), master_file_id?(.potx/.pptx), logo_file_id?, cover_image_file_id?, cover_template?, page_numbers?}
             */
            design?: {
                [key: string]: unknown;
            } | null;
            /**
             * Document
             * @description pptx(·pdf 덱): {title?, cover?:{title,subtitle,customer,date,presenter,image}, footer?, design?, lang?, tbd_label?, slides:[{template_code, kind?, slots|content, notes?, sources|footnotes?:[{label,url?}], confirm?:[str], sheet_id?}]} · xlsx: {sheets:[{name, columns:[{key,label,width?,format?}], rows, freeze?, merges?, notes?, header_style?, sources?}]} · docx · pdf 보고서: {title, subtitle?, meta?, sections:[{heading, level?, paragraphs?, bullets?, numbered?, table?, images?, captions?, sources?}], page_size?: A4|Letter, orientation?} (pdf 는 {report: …} 로 감싸도 된다) · zip: {entries:[{file_id, path} | {path, text|json} | {path, format, document}]}
             */
            document?: {
                [key: string]: unknown;
            } | null;
            /**
             * Document File Id
             * @description 문서 JSON 을 files 에 올렸으면 그 id(ProposalRenderDoc 등)
             */
            document_file_id?: string | null;
            /**
             * Filename
             * @description 확장자 없이(붙어 있어도 된다). 비우면 문서 제목
             */
            filename?: string | null;
            /**
             * Fills
             * @description base_file_id 양식에 칸 하나씩 쓰기(document 다음에 적용)
             */
            fills?: components["schemas"]["FormFill"][] | null;
            /** @description base_file_id 양식 맞추기 힌트 · 규칙 */
            form?: components["schemas"]["FormOptions"] | null;
            /**
             * Format
             * @enum {string}
             */
            format: "pptx" | "xlsx" | "docx" | "pdf" | "zip";
            /**
             * From File Id
             * @description pdf: 이 파일(PPTX · DOCX · XLSX)을 PDF 로 바꾼다 — LibreOffice 필요
             */
            from_file_id?: string | null;
            /**
             * Lang
             * @description language 와 같다(ProposalRenderDoc)
             */
            lang?: ("ko" | "en" | "both" | "ko_en") | null;
            /**
             * Language
             * @description both = 한국어 + 영문
             */
            language?: ("ko" | "en" | "both" | "ko_en") | null;
            /** Master Id */
            master_id?: string | null;
            /** Project Id */
            project_id?: string | null;
            /**
             * Source Ref
             * @description 만든 곳(예 proposal:prp_…) — 파일 메타에 남긴다
             */
            source_ref?: string | null;
            /**
             * Tbd Label
             * @description 영문 확인 필요 표시(기본 [TBD])
             */
            tbd_label?: string | null;
            /**
             * Tbd Mode
             * @description keep_marks(기본) · move_to_notes(칸은 「—」, 문장은 발표자 노트)
             */
            tbd_mode?: ("keep_marks" | "move_to_notes" | "keep" | "notes") | null;
        };
        /** ExportResult */
        ExportResult: {
            /** Export Id */
            export_id: string;
            file: components["schemas"]["ExportFile"];
            /** Files */
            files: components["schemas"]["ExportFile"][];
            /** @description base_file_id(고객사 양식)로 만들었을 때만 */
            form_fill?: components["schemas"]["FormFillReport"] | null;
            /**
             * Slide Count
             * @default 0
             */
            slide_count: number;
            /**
             * Status
             * @constant
             */
            status: "done";
            /** Template Codes */
            template_codes?: string[];
            /** Warnings */
            warnings?: string[];
        };
        /**
         * FormFill
         * @description 고객사 양식의 한 칸 — 칸 주소(cell) 또는 행(row) · 열(column)로 찾는다.
         */
        FormFill: {
            /**
             * Cell
             * @description 칸 주소(D7 · $D$7 · 'Sheet'!D7) — 주면 row · column 은 보지 않고, 값이 있어도 덮는다
             */
            cell?: string | null;
            /**
             * Column
             * @description 열 번호(1부터) · 머리 글(행 위쪽에서 찾는다) · 열 글자(D). 비우면 행 이름 칸 바로 오른쪽. 행 번호 + 열 번호/글자면 값이 있어도 덮는다
             */
            column?: number | string | null;
            /**
             * Note
             * @description 셀 메모로 남길 글(예 변환 전 원래 값 · 직접 입력 표시)
             */
            note?: string | null;
            /**
             * Row
             * @description 행 번호(1부터) 또는 행 이름(양식 라벨 글로 찾는다 — 단위 괄호 · 번호 매김 무시)
             */
            row?: number | string | null;
            /**
             * Sheet
             * @description 양식 시트 이름 또는 번호(0부터). 비우면 form.sheet · 첫 보이는 시트
             */
            sheet?: string | number | null;
            /**
             * Value
             * @description 쓸 값 — 글 · 숫자 · {ko, en} · {value, note?}. null · 빈 글이면 쓰지 않는다
             */
            value?: unknown;
        };
        /** FormFillCell */
        FormFillCell: {
            /** Cell */
            cell: string;
            /** Column Label */
            column_label?: string | null;
            /** Column Match */
            column_match?: string | null;
            /**
             * Match
             * @description exact · normalized · base · fuzzy · hint · inferred · cell · number · letter · next_to_label · appended
             */
            match: string;
            /**
             * Outside
             * @description 양식 범위 밖 칸
             */
            outside?: boolean | null;
            /**
             * Redirected From
             * @description 병합 칸 안쪽 주소였으면 원래 주소(머리칸에 썼다)
             */
            redirected_from?: string | null;
            /**
             * Replaced
             * @description 덮어쓴 원래 값
             */
            replaced?: string | null;
            /** Row Label */
            row_label?: string | null;
            /** Row Match */
            row_match?: string | null;
            /** Sheet */
            sheet: string;
            /**
             * Source
             * @description sheets[0].rows[3] · fills[2]
             */
            source: string;
            /**
             * Warning
             * @description 예: 목록(드롭다운)에 없는 값
             */
            warning?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** FormFillColumn */
        FormFillColumn: {
            /**
             * Column
             * @description 양식 열 글자(못 맞추면 null)
             */
            column?: string | null;
            /** Key */
            key: string;
            /**
             * Label
             * @default
             */
            label: string;
            /** Match */
            match?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** FormFillLoss */
        FormFillLoss: {
            /** Base */
            base: number;
            /** Name */
            name: string;
            /** Output */
            output: number;
            /**
             * Part
             * @description shapes · form_controls · header_footer_images · ext_validations · sparklines · …
             */
            part: string;
        };
        /** FormFillMiss */
        FormFillMiss: {
            /**
             * Candidates
             * @description 값 열 후보(열 글자 + 머리) — form.column_map 으로 고르기
             */
            candidates?: string[] | null;
            /** Key */
            key?: string | null;
            /** Label */
            label: string;
            /** Sheet */
            sheet?: string | null;
            /** Source */
            source: string;
        } & {
            [key: string]: unknown;
        };
        /**
         * FormFillReport
         * @description 고객사 양식 채우기 결과 — 쓴 칸 · 못 맞춘 행/열/시트 · 건너뛴 칸 · 양식에만 있는 행 · 유지 못 한 양식 요소.
         */
        FormFillReport: {
            /** Appended Rows */
            appended_rows?: components["schemas"]["FormFillRow"][];
            /** Appended Sheets */
            appended_sheets?: string[];
            /** Base File Id */
            base_file_id: string;
            /** Base Name */
            base_name?: string | null;
            /**
             * Cells
             * @description 쓴 칸(최대 300)
             */
            cells?: components["schemas"]["FormFillCell"][];
            /**
             * Converted From
             * @description xls · ods · xlsb 를 LibreOffice 로 .xlsx 로 바꿨으면 그 형식
             */
            converted_from?: string | null;
            /**
             * Filled
             * @description 값을 쓴 칸 수
             */
            filled: number;
            /**
             * Form Only Rows
             * @description 양식에만 있고 값이 빈 행
             */
            form_only_rows?: components["schemas"]["FormFillRow"][];
            /**
             * Lost
             * @description openpyxl 이 다시 쓰지 못한 양식 요소(저장 전후 개수)
             */
            lost?: components["schemas"]["FormFillLoss"][];
            /** Sheets */
            sheets?: components["schemas"]["FormFillSheet"][];
            /** Skipped */
            skipped?: components["schemas"]["FormFillSkip"][];
            /** Unmatched Columns */
            unmatched_columns?: components["schemas"]["FormFillMiss"][];
            /** Unmatched Rows */
            unmatched_rows?: components["schemas"]["FormFillMiss"][];
            /** Unmatched Sheets */
            unmatched_sheets?: string[];
        } & {
            [key: string]: unknown;
        };
        /** FormFillRow */
        FormFillRow: {
            /** Label */
            label: string;
            /** Row */
            row: number;
            /** Sheet */
            sheet: string;
            /** Source */
            source?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** FormFillSheet */
        FormFillSheet: {
            /**
             * Cells
             * @default 0
             */
            cells: number;
            /** Columns */
            columns?: components["schemas"]["FormFillColumn"][];
            /** Header Row */
            header_row?: number | null;
            /** Label Column */
            label_column?: string | null;
            /**
             * Orientation
             * @enum {string}
             */
            orientation: "rows" | "columns";
            /**
             * Rows Matched
             * @default 0
             */
            rows_matched: number;
            /**
             * Rows Total
             * @default 0
             */
            rows_total: number;
            /** Sheet */
            sheet: string;
            /**
             * Source
             * @description 문서 시트(sheets[0])
             */
            source: string;
        } & {
            [key: string]: unknown;
        };
        /** FormFillSkip */
        FormFillSkip: {
            /** Cell */
            cell?: string | null;
            /**
             * Current
             * @description not_empty 일 때 칸의 지금 값
             */
            current?: string | null;
            /**
             * Reason
             * @description formula · merged · locked · not_empty · duplicate · out_of_bounds · invalid_cell · sheet_not_found · column_required
             */
            reason: string;
            /** Sheet */
            sheet?: string | null;
            /** Source */
            source: string;
        } & {
            [key: string]: unknown;
        };
        /**
         * FormOptions
         * @description 고객사 양식 맞추기 힌트 · 규칙(모두 선택). document.sheets[i].form 으로 시트마다 덮을 수 있다.
         */
        FormOptions: {
            /**
             * Column Map
             * @description 문서 열 key → 양식 열(글자 D · 번호 4 · 머리 글)
             */
            column_map?: {
                [key: string]: string | number;
            } | null;
            /**
             * Extra Sheets
             * @description 양식과 짝이 없는 문서 시트: drop(기본 — 보고만) · append(우리 디자인 시트로 뒤에 덧붙임, 예 메모 · 출처)
             */
            extra_sheets?: ("drop" | "append") | null;
            /**
             * Fuzzy
             * @description 오타 수준 비슷한 이름도 맞춘다(기본 true — 0.88 이상이고 유일할 때, 보고서 match=fuzzy)
             */
            fuzzy?: boolean | null;
            /**
             * Header Row
             * @description 머리 행 번호(1부터) — 비우면 문서 열 이름이 가장 많이 맞는 행(위 60행)
             */
            header_row?: number | null;
            /**
             * Highlight Marks
             * @description [확인 필요] 같은 자리표시가 든 칸을 노랗게(기본 true)
             */
            highlight_marks?: boolean | null;
            /**
             * Label Column
             * @description 행 이름 열(B · 2) — 비우면 이름이 가장 많이 맞는 열
             */
            label_column?: string | number | null;
            /**
             * Label Key
             * @description 문서의 행 이름 열 key — 비우면 글이 든 첫 열
             */
            label_key?: string | null;
            /**
             * Orientation
             * @description auto(기본: 문서 그대로와 돌린 것 중 칸이 많이 맞는 쪽) · rows(문서 행 = 양식 행) · columns(문서 행 = 양식 열)
             */
            orientation?: ("auto" | "rows" | "columns") | null;
            /**
             * Overwrite
             * @description 이름으로 맞춘 칸에 값이 이미 있으면: empty(기본 — 비었거나 자리표시일 때만) · always(덮기). 수식 칸은 늘 건너뛴다
             */
            overwrite?: ("empty" | "always") | null;
            /**
             * Overwrite Formulas
             * @description true 면 수식 칸도 덮는다(기본 false)
             */
            overwrite_formulas?: boolean | null;
            /**
             * Row Map
             * @description 문서 행 이름(또는 행의 _key · row_key) → 양식 행 번호 · 양식 행 이름
             */
            row_map?: {
                [key: string]: string | number;
            } | null;
            /**
             * Sheet
             * @description 첫 문서 시트 · fills 기본 시트를 쓸 양식 시트(이름 · 0부터 번호). 비우면 이름이 같은 시트 → 첫 보이는 시트
             */
            sheet?: string | number | null;
            /**
             * Unmatched Rows
             * @description 못 맞춘 문서 행: report(기본 — 보고만) · append(양식 맨 아래 「추가 항목」에 같은 서식으로 덧붙임)
             */
            unmatched_rows?: ("report" | "append") | null;
        };
        /** Master */
        Master: {
            /**
             * Aspect
             * @default
             */
            aspect: string;
            /** Builtin */
            builtin: boolean;
            /**
             * Cover Template
             * @default C01
             */
            cover_template: string;
            /** Created At */
            created_at?: string | null;
            /**
             * Description
             * @default
             */
            description: string;
            /** File Id */
            file_id?: string | null;
            /** Layouts */
            layouts?: string[];
            /** Master Id */
            master_id: string;
            /** Name */
            name: string;
            /** Project Id */
            project_id?: string | null;
            /** Warnings */
            warnings?: string[];
        };
        /** MasterCreate */
        MasterCreate: {
            /**
             * File Id
             * @description .potx · .pptx 파일 id(files)
             */
            file_id: string;
            /** Name */
            name?: string | null;
            /** Project Id */
            project_id?: string | null;
        };
        /** MasterList */
        MasterList: {
            /** Items */
            items: components["schemas"]["Master"][];
        };
        /** RenderAccepted */
        RenderAccepted: {
            /** Job Id */
            job_id: string;
            /** Render Id */
            render_id: string;
            /**
             * Status
             * @constant
             */
            status: "queued";
        };
        /** RenderPage */
        RenderPage: {
            /** File Id */
            file_id: string;
            /** Index */
            index: number;
            /** Png File Id */
            png_file_id: string;
            /** Sheet Id */
            sheet_id?: string | null;
            /** Url */
            url: string;
        };
        /** RenderRecord */
        RenderRecord: {
            /** Created At */
            created_at?: string | null;
            error?: components["schemas"]["ExportError"] | null;
            /** Job Id */
            job_id?: string | null;
            /** Pages */
            pages?: components["schemas"]["RenderPage"][];
            /** Render Id */
            render_id: string;
            /** Source File Id */
            source_file_id?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "done" | "failed";
            /** Updated At */
            updated_at?: string | null;
            /** Warnings */
            warnings?: string[];
        };
        /** RenderRequest */
        RenderRequest: {
            /**
             * Confidential
             * @default false
             */
            confidential: boolean;
            /** Design */
            design?: {
                [key: string]: unknown;
            } | null;
            /**
             * Document
             * @description 덱 문서(POST /exports 의 pptx 문서와 같다)
             */
            document?: {
                [key: string]: unknown;
            } | null;
            /** Document File Id */
            document_file_id?: string | null;
            /**
             * File Id
             * @description PPTX(LibreOffice 필요) · PDF(바로) 파일
             */
            file_id?: string | null;
            /** Language */
            language?: ("ko" | "en" | "both" | "ko_en") | null;
            /** Master Id */
            master_id?: string | null;
            /** Max Slides */
            max_slides?: number | null;
            /** Project Id */
            project_id?: string | null;
            /**
             * Sheet Ids
             * @description 이 시트(slides[].sheet_id)만
             */
            sheet_ids?: string[] | null;
            /**
             * Width
             * @description PNG 가로 px(기본 1280)
             */
            width?: number | null;
        };
        /** ServiceInfo */
        ServiceInfo: {
            /**
             * Catalog Version
             * @default
             */
            catalog_version: string;
            /**
             * Features
             * @description 예 form_fill(xlsx 고객사 양식 채우기)
             */
            features?: string[];
            /**
             * Pdf Converter
             * @default false
             */
            pdf_converter: boolean;
            /**
             * Pdf Converter Detected
             * @description 이 서버에서 찾은 soffice 경로(쓰지 않을 때도 — SOFFICE_PATH 에 넣으면 켜진다)
             */
            pdf_converter_detected?: string | null;
            /**
             * Pdf Converter Reason
             * @description env(SOFFICE_PATH 사용) · off · missing(경로 없음) · unset(비어 있음 — 끔)
             */
            pdf_converter_reason?: string | null;
            /**
             * Pdf Font
             * @description {family, resolved, ok} — fontconfig 가 덱 글꼴(Noto Sans KR)을 무엇으로 고르는지(ok=false 면 PDF 줄바꿈이 달라짐)
             */
            pdf_font?: {
                [key: string]: unknown;
            } | null;
            /** Service */
            service: string;
            /**
             * Templates
             * @default 0
             */
            templates: number;
            /** Title */
            title: string;
            /** Version */
            version: string;
        };
        /** Slot */
        Slot: {
            /**
             * Count
             * @description 목록 칸이면 항목 수(카드 · 수치 · 이미지 n개)
             */
            count?: number | null;
            /**
             * Default
             * @description 기본값 — 글 칸은 문자열, 목록 칸(count)은 항목별 목록(예 표 머리), 숫자 칸은 숫자
             */
            default?: string | number | string[] | null;
            /**
             * Default En
             * @description 영문 기본값(모양은 default 와 같다)
             */
            default_en?: string | number | string[] | null;
            /**
             * Fields
             * @description card 칸의 항목 필드
             */
            fields?: components["schemas"]["SlotField"][] | null;
            /** Hint */
            hint?: string | null;
            /**
             * Image Grade
             * @description A 공간+제품 · B 솔루션 화면 · C 제품 컷 · D 도식 · E 아이콘/로고
             */
            image_grade?: string | null;
            /**
             * Key
             * @description 칸 이름 — 문서 slides[].slots 의 키
             */
            key: string;
            /**
             * Label
             * @default
             */
            label: string;
            /**
             * Max Chars
             * @description 한국어 기준 글자 수(영어는 1.8배까지)
             */
            max_chars?: number | null;
            /**
             * Required
             * @default false
             */
            required: boolean;
            /**
             * Type
             * @enum {string}
             */
            type: "text" | "bullets" | "number" | "kpi" | "image" | "table" | "chart" | "logo" | "caption" | "source" | "card";
        };
        /** SlotField */
        SlotField: {
            /** Image Grade */
            image_grade?: string | null;
            /** Key */
            key: string;
            /**
             * Label
             * @default
             */
            label: string;
            /** Max Chars */
            max_chars?: number | null;
            /** Type */
            type: string;
        };
        /** SlotSchema */
        SlotSchema: {
            /** Slots */
            slots: components["schemas"]["SlotSchemaItem"][];
        };
        /** SlotSchemaItem */
        SlotSchemaItem: {
            /**
             * Box
             * @description 첫 상자(0..1)
             */
            box?: {
                [key: string]: number;
            } | null;
            /**
             * Boxes
             * @default 0
             */
            boxes: number;
            /**
             * Capacity
             * @description {max_chars?, count?}
             */
            capacity?: {
                [key: string]: number;
            };
            /** Fields */
            fields?: components["schemas"]["SlotField"][] | null;
            /** Id */
            id: string;
            /**
             * Label
             * @default
             */
            label: string;
            /**
             * Required
             * @default false
             */
            required: boolean;
            /** Type */
            type: string;
        };
        /** TemplateDetail */
        TemplateDetail: {
            /** Archetype */
            archetype: string;
            /** Base */
            base?: string | null;
            /** Boxes */
            boxes: components["schemas"]["Box"][];
            /**
             * Code
             * @description 저장 코드(예 VP-F3) — 표시 코드는 display_code(VP-F·3)
             */
            code: string;
            /** Data Shape */
            data_shape?: {
                [key: string]: unknown;
            };
            /**
             * Description
             * @default
             */
            description: string;
            /** Display Code */
            display_code: string;
            /**
             * Example Slots
             * @description 칸 값 모양 예시(자리표시 문구 — 사실 아님)
             */
            example_slots?: {
                [key: string]: unknown;
            };
            /** Family */
            family?: string | null;
            /** Industry */
            industry?: string | null;
            /** Industry Code */
            industry_code?: string | null;
            /** Industry Name */
            industry_name?: string | null;
            /** Industry Scheme */
            industry_scheme?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "common" | "generic" | "industry" | "product" | "dedicated" | "industry_solution";
            /** Name */
            name: string;
            /** Params */
            params?: {
                [key: string]: unknown;
            };
            /** Product Count */
            product_count?: number | null;
            /** Proposal Types */
            proposal_types?: string[];
            /**
             * Role Name
             * @default
             */
            role_name: string;
            /** Sample Title */
            sample_title?: string | null;
            /** Section */
            section: string;
            /**
             * Section Name
             * @default
             */
            section_name: string;
            /** Sheet Role */
            sheet_role: string;
            /** Slot Count */
            slot_count: number;
            slot_schema?: components["schemas"]["SlotSchema"] | null;
            /** Slots */
            slots: components["schemas"]["Slot"][];
            /** Solution */
            solution?: string | null;
            /** Solution Code */
            solution_code?: string | null;
            /** Solution Name */
            solution_name?: string | null;
            source?: components["schemas"]["TemplateSource"] | null;
            /**
             * Status
             * @enum {string}
             */
            status: "ready" | "in_production" | "internal";
            /** Thumb Kind */
            thumb_kind?: string | null;
            /** Thumb N */
            thumb_n?: number | null;
            /** Thumb Url */
            thumb_url: string;
            /** Variant */
            variant?: string | null;
            /**
             * When
             * @default
             */
            when: string;
        } & {
            [key: string]: unknown;
        };
        /** TemplateList */
        TemplateList: {
            /** Items */
            items: components["schemas"]["TemplateSummary"][];
            /** Next Cursor */
            next_cursor?: string | null;
            /** Total */
            total: number;
        };
        /** TemplateSource */
        TemplateSource: {
            /**
             * Artifact
             * @default
             */
            artifact: string;
            /**
             * Board
             * @description 캔버스 보드 파일 — 보드가 없는(제작 중) 템플릿은 비우고 note 에 사유
             */
            board?: string | null;
            /** Canvas */
            canvas: string;
            /**
             * Path
             * @default
             */
            path: string;
            /**
             * Title
             * @default
             */
            title: string;
            /**
             * Version
             * @default
             */
            version: string;
        } & {
            [key: string]: unknown;
        };
        /** TemplateStats */
        TemplateStats: {
            /** By Kind */
            by_kind: {
                [key: string]: number;
            };
            /** By Role */
            by_role: {
                [key: string]: number;
            };
            /** By Section */
            by_section: {
                [key: string]: number;
            };
            /** By Status */
            by_status: {
                [key: string]: number;
            };
            /**
             * Catalog Version
             * @default
             */
            catalog_version: string;
            /** Dedicated */
            dedicated: number;
            /** Industry */
            industry: number;
            /** Ready */
            ready: number;
            /** Total */
            total: number;
        } & {
            [key: string]: unknown;
        };
        /** TemplateSummary */
        TemplateSummary: {
            /** Archetype */
            archetype: string;
            /** Base */
            base?: string | null;
            /**
             * Code
             * @description 저장 코드(예 VP-F3) — 표시 코드는 display_code(VP-F·3)
             */
            code: string;
            /** Data Shape */
            data_shape?: {
                [key: string]: unknown;
            };
            /**
             * Description
             * @default
             */
            description: string;
            /** Display Code */
            display_code: string;
            /** Family */
            family?: string | null;
            /** Industry */
            industry?: string | null;
            /** Industry Code */
            industry_code?: string | null;
            /** Industry Name */
            industry_name?: string | null;
            /** Industry Scheme */
            industry_scheme?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "common" | "generic" | "industry" | "product" | "dedicated" | "industry_solution";
            /** Name */
            name: string;
            /** Product Count */
            product_count?: number | null;
            /** Proposal Types */
            proposal_types?: string[];
            /**
             * Role Name
             * @default
             */
            role_name: string;
            /** Section */
            section: string;
            /**
             * Section Name
             * @default
             */
            section_name: string;
            /** Sheet Role */
            sheet_role: string;
            /** Slot Count */
            slot_count: number;
            slot_schema?: components["schemas"]["SlotSchema"] | null;
            /** Solution */
            solution?: string | null;
            /** Solution Code */
            solution_code?: string | null;
            /** Solution Name */
            solution_name?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "ready" | "in_production" | "internal";
            /** Thumb Kind */
            thumb_kind?: string | null;
            /** Thumb N */
            thumb_n?: number | null;
            /** Thumb Url */
            thumb_url: string;
            /** Variant */
            variant?: string | null;
            /**
             * When
             * @default
             */
            when: string;
        } & {
            [key: string]: unknown;
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
    list_exports: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
                project_id?: string | null;
                source_ref?: string | null;
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
                    "application/json": components["schemas"]["ExportList"];
                };
            };
        };
    };
    create_export: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
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
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExportResult"];
                };
            };
            /** @description 느린 내보내기(LibreOffice PDF · 큰 덱) — 잡으로 처리 */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExportAccepted"];
                };
            };
            /** @description PDF_CONVERTER_UNAVAILABLE — LibreOffice(SOFFICE_PATH) 없음 */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
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
    list_masters: {
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
                    "application/json": components["schemas"]["MasterList"];
                };
            };
        };
    };
    create_master: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MasterCreate"];
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
                    "application/json": components["schemas"]["Master"];
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
                "application/json": components["schemas"]["RenderRequest"];
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
            /** @description PDF_CONVERTER_UNAVAILABLE — LibreOffice(SOFFICE_PATH) 없음 */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
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
                    "application/json": components["schemas"]["RenderRecord"];
                };
            };
        };
    };
    list_templates: {
        parameters: {
            query?: {
                /** @description 코드 목록(쉼표) — 표시 코드(VP-F·3)도 된다 */
                codes?: string | null;
                cursor?: string | null;
                /** @description slot_schema 포함 */
                include_slots?: boolean;
                /** @description 업종 코드(FB · RT · …) — 그 업종판 + 범용, 업종판이 앞 */
                industry?: string | null;
                /** @description common · generic · industry · product · dedicated · industry_solution(쉼표로 여럿) */
                kind?: string | null;
                limit?: number;
                /** @description standard · quickwin · solution */
                proposal_type?: string | null;
                /** @description 코드 · 이름 · 쓰는 때 검색 */
                q?: string | null;
                /** @description 시트 역할(쉼표로 여럿) — 예 MS,TR */
                role?: string | null;
                /** @description 섹션(쉼표로 여럿) — common · mi · vp · birdseye · space_products · solution · space_scenario · cases · why · spec · appendix */
                section?: string | null;
                /** @description 솔루션 코드(MGI · VXT …) */
                solution?: string | null;
                /** @description ready · in_production · internal */
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
                    "application/json": components["schemas"]["TemplateList"];
                };
            };
        };
    };
    get_template: {
        parameters: {
            query?: {
                /** @description 별칭 코드(VP-F 등)를 항목 수로 고를 때 */
                n?: number | null;
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
                    "application/json": components["schemas"]["TemplateDetail"];
                };
            };
        };
    };
    template_board: {
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
            /** @description 원본 디자인 보드를 그린 그림(1280×720, docs/templates/_rendered) */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "image/jpeg": string;
                };
            };
        };
    };
    template_thumbnail: {
        parameters: {
            query?: {
                /** @description 포인트 색(기본 #1428a0) */
                brand?: string | null;
                /** @description 가로 px(세로는 16:9) */
                w?: number;
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
            /** @description 썸네일 PNG(w × w·9/16) */
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
    template_stats: {
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
                    "application/json": components["schemas"]["TemplateStats"];
                };
            };
        };
    };
}
