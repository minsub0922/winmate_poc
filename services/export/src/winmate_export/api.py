"""export API (/v1). 이 파일의 엔드포인트가 contracts/export.json 이 된다(make contracts).

- 템플릿 카탈로그: GET /v1/templates · /v1/templates/stats · /v1/templates/{code} · /v1/templates/{code}/thumbnail.png
- 내보내기: POST /v1/exports(빠르면 201 + 파일, 느리면 202 + 잡) · GET /v1/exports · GET /v1/exports/{export_id}
  - xlsx + base_file_id: 고객사 양식 사본에 값만 써 넣기(render/xlsx_form.py — 맞추기 규칙 · 쓰기 규칙 문서)
- 슬라이드 그림: POST /v1/renders(202, LibreOffice 필요 — 없으면 501) · GET /v1/renders/{render_id}
- 마스터: GET /v1/masters · POST /v1/masters {file_id}(.potx · .pptx)
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
from typing import Any, Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from winmate_common.errors import ApiError
from winmate_common.jobs import jobs

from . import service
from .render import soffice
from .render.theme import FONT
from .render.thumbs import DEFAULT_W, MAX_W, MIN_W, cached_thumbnail
from .templates.catalog import CATALOG_PATH, catalog, normalize_code
from .templates.samples import sample_slots

router = APIRouter(prefix="/v1")


class ServiceInfo(BaseModel):
    service: str
    title: str
    version: str
    catalog_version: str = ""
    templates: int = 0
    pdf_converter: bool = False
    pdf_converter_reason: str | None = Field(None, description="env(SOFFICE_PATH 사용) · off · missing(경로 없음) · unset(비어 있음 — 끔)")
    pdf_converter_detected: str | None = Field(None, description="이 서버에서 찾은 soffice 경로(쓰지 않을 때도 — SOFFICE_PATH 에 넣으면 켜진다)")
    features: list[str] = Field(default_factory=list, description="예 form_fill(xlsx 고객사 양식 채우기)")
    pdf_font: dict[str, Any] | None = Field(None, description="{family, resolved, ok} — fontconfig 가 덱 글꼴(Noto Sans KR)을 무엇으로 고르는지(ok=false 면 PDF 줄바꿈이 달라짐)")


def catalog_hash() -> str:
    return _catalog_hash(CATALOG_PATH.stat().st_mtime_ns)


_HASHES: dict[int, str] = {}


def _catalog_hash(mtime: int) -> str:
    if mtime not in _HASHES:
        _HASHES[mtime] = hashlib.sha1(CATALOG_PATH.read_bytes()).hexdigest()[:10]
    return _HASHES[mtime]


@router.get("/info", response_model=ServiceInfo, tags=["meta"])
async def info() -> ServiceInfo:
    st = soffice.status()
    return ServiceInfo(service="export", title="내보내기 — PPTX · XLSX · DOCX · PDF · ZIP 생성, 시트 템플릿 카탈로그", version="0.3.0",
                       catalog_version=catalog_hash(), templates=len(catalog().templates), pdf_converter=st.path is not None,
                       pdf_converter_reason=st.reason, pdf_converter_detected=st.detected, features=["form_fill"],
                       pdf_font=await asyncio.to_thread(soffice.font_status, FONT))


# ── 모델: 템플릿 ─────────────────────────────────────────────

class SlotField(BaseModel):
    key: str
    type: str
    label: str = ""
    max_chars: int | None = None
    image_grade: str | None = None


# 칸 기본값 — 글 칸은 문자열, 목록 칸(count, 예: 표 머리 headers · 축 axes · 행 이름 row_labels)은 항목마다 하나씩 든 목록,
# 숫자 칸(예: GN-*.recommended)은 숫자. 카탈로그(templates/build.py)가 내는 모양 그대로 돌려준다.
SlotDefault = str | int | float | list[str] | None


class Slot(BaseModel):
    key: str = Field(description="칸 이름 — 문서 slides[].slots 의 키")
    type: Literal["text", "bullets", "number", "kpi", "image", "table", "chart", "logo", "caption", "source", "card"]
    label: str = ""
    required: bool = False
    max_chars: int | None = Field(None, description="한국어 기준 글자 수(영어는 1.8배까지)")
    count: int | None = Field(None, description="목록 칸이면 항목 수(카드 · 수치 · 이미지 n개)")
    image_grade: str | None = Field(None, description="A 공간+제품 · B 솔루션 화면 · C 제품 컷 · D 도식 · E 아이콘/로고")
    fields: list[SlotField] | None = Field(None, description="card 칸의 항목 필드")
    default: SlotDefault = Field(None, description="기본값 — 글 칸은 문자열, 목록 칸(count)은 항목별 목록(예 표 머리), 숫자 칸은 숫자")
    default_en: SlotDefault = Field(None, description="영문 기본값(모양은 default 와 같다)")
    hint: str | None = None


class Box(BaseModel):
    model_config = ConfigDict(extra="allow")
    slot: str | None = Field(None, description="칸 이름(null 이면 장식)")
    x: float = Field(description="16:9 슬라이드 기준 0..1")
    y: float
    w: float
    h: float
    style: str
    index: int | None = Field(None, description="목록 칸의 몇 번째 항목인지")
    part: str | None = Field(None, description="카드 항목의 필드 하나만 그리는 상자")


class SlotSchemaItem(BaseModel):
    id: str
    type: str
    label: str = ""
    required: bool = False
    box: dict[str, float] | None = Field(None, description="첫 상자(0..1)")
    boxes: int = 0
    capacity: dict[str, int] = Field(default_factory=dict, description="{max_chars?, count?}")
    fields: list[SlotField] | None = None


class SlotSchema(BaseModel):
    slots: list[SlotSchemaItem]


class TemplateSummary(BaseModel):
    model_config = ConfigDict(extra="allow")
    code: str = Field(description="저장 코드(예 VP-F3) — 표시 코드는 display_code(VP-F·3)")
    display_code: str
    name: str
    sheet_role: str
    role_name: str = ""
    section: str
    section_name: str = ""
    kind: Literal["common", "generic", "industry", "product", "dedicated", "industry_solution"]
    family: str | None = None
    industry: str | None = None
    industry_code: str | None = None
    industry_name: str | None = None
    industry_scheme: str | None = None
    solution: str | None = None
    solution_code: str | None = None
    solution_name: str | None = None
    variant: str | None = None
    product_count: int | None = None
    proposal_types: list[str] = Field(default_factory=list)
    description: str = ""
    when: str = ""
    status: Literal["ready", "in_production", "internal"]
    base: str | None = None
    archetype: str
    thumb_kind: str | None = None
    thumb_n: int | None = None
    thumb_url: str
    slot_count: int
    data_shape: dict[str, Any] = Field(default_factory=dict)
    slot_schema: SlotSchema | None = None


class TemplateList(BaseModel):
    items: list[TemplateSummary]
    next_cursor: str | None = None
    total: int


class TemplateSource(BaseModel):
    model_config = ConfigDict(extra="allow")
    canvas: str
    board: str | None = Field(None, description="캔버스 보드 파일 — 보드가 없는(제작 중) 템플릿은 비우고 note 에 사유")
    title: str = ""
    artifact: str = ""
    version: str = ""
    path: str = ""


class TemplateDetail(TemplateSummary):
    params: dict[str, Any] = Field(default_factory=dict)
    sample_title: str | None = None
    slots: list[Slot]
    boxes: list[Box]
    source: TemplateSource | None = None
    example_slots: dict[str, Any] = Field(default_factory=dict, description="칸 값 모양 예시(자리표시 문구 — 사실 아님)")


class TemplateStats(BaseModel):
    model_config = ConfigDict(extra="allow")
    total: int
    ready: int
    industry: int
    dedicated: int
    by_role: dict[str, int]
    by_section: dict[str, int]
    by_kind: dict[str, int]
    by_status: dict[str, int]
    catalog_version: str = ""


def _slot_schema(t: dict[str, Any]) -> dict[str, Any]:
    items = []
    for s in t["slots"]:
        boxes = [b for b in t["boxes"] if b.get("slot") == s["key"]]
        first = boxes[0] if boxes else None
        cap = {k: s[k] for k in ("max_chars", "count") if s.get(k)}
        items.append({"id": s["key"], "type": s["type"], "label": s.get("label", ""), "required": bool(s.get("required")),
                      "box": {k: first[k] for k in ("x", "y", "w", "h")} if first else None, "boxes": len(boxes),
                      "capacity": cap, "fields": s.get("fields")})
    return {"slots": items}


def _summary(t: dict[str, Any], include_slots: bool) -> dict[str, Any]:
    d = catalog().summary(t)
    d["industry_code"] = t.get("industry")
    d["solution_code"] = t.get("solution")
    d["proposal_types"] = d.get("proposal_types") or []
    d["data_shape"] = d.get("data_shape") or {}
    d["description"] = d.get("description") or ""
    d["when"] = d.get("when") or ""
    if include_slots:
        d["slot_schema"] = _slot_schema(t)
    return d


# ── 템플릿 API ───────────────────────────────────────────────

@router.get("/templates", response_model=TemplateList, tags=["templates"], response_model_exclude_none=True)
async def list_templates(
    role: str | None = Query(None, description="시트 역할(쉼표로 여럿) — 예 MS,TR"),
    section: str | None = Query(None, description="섹션(쉼표로 여럿) — common · mi · vp · birdseye · space_products · solution · space_scenario · cases · why · spec · appendix"),
    industry: str | None = Query(None, description="업종 코드(FB · RT · …) — 그 업종판 + 범용, 업종판이 앞"),
    proposal_type: str | None = Query(None, description="standard · quickwin · solution"),
    q: str | None = Query(None, description="코드 · 이름 · 쓰는 때 검색"),
    solution: str | None = Query(None, description="솔루션 코드(MGI · VXT …)"),
    kind: str | None = Query(None, description="common · generic · industry · product · dedicated · industry_solution(쉼표로 여럿)"),
    status: str | None = Query(None, description="ready · in_production · internal"),
    codes: str | None = Query(None, description="코드 목록(쉼표) — 표시 코드(VP-F·3)도 된다"),
    include_slots: bool = Query(True, description="slot_schema 포함"),
    limit: int = Query(500, ge=1, le=1000),
    cursor: str | None = None,
) -> dict[str, Any]:
    code_list = [c for c in (codes or "").split(",") if c.strip()] or None
    found = catalog().search(role=role, section=section, industry=industry, proposal_type=proposal_type, q=q,
                             solution=solution, kind=kind, status=status, codes=code_list)
    if code_list:
        # 별칭(VP-F → VP-F3 등)도 풀어 준다
        have = {normalize_code(t["code"]) for t in found}
        for c in code_list:
            t = catalog().get(c)
            if t is not None and normalize_code(t["code"]) not in have:
                found.append(t)
                have.add(normalize_code(t["code"]))
    try:
        offset = int(base64.urlsafe_b64decode((cursor or "").encode()).decode() or 0) if cursor else 0
    except Exception:  # noqa: BLE001
        offset = 0
    page = found[offset: offset + limit]
    nxt = base64.urlsafe_b64encode(str(offset + limit).encode()).decode() if offset + limit < len(found) else None
    return {"items": [_summary(t, include_slots) for t in page], "next_cursor": nxt, "total": len(found)}


@router.get("/templates/stats", response_model=TemplateStats, tags=["templates"])
async def template_stats() -> dict[str, Any]:
    return {**catalog().stats(), "catalog_version": catalog_hash()}


@router.get("/templates/{code}", response_model=TemplateDetail, tags=["templates"], response_model_exclude_none=True)
async def get_template(code: str, n: int | None = Query(None, ge=1, le=12, description="별칭 코드(VP-F 등)를 항목 수로 고를 때")) -> dict[str, Any]:
    cat = catalog()
    t = cat.get(code)
    alias = cat.aliases.get(normalize_code(code))
    if alias and n and alias.get("options"):
        t = cat.get(alias["options"].get(str(n), alias.get("default", ""))) or t
    if t is None:
        raise ApiError(404, "TEMPLATE_NOT_FOUND", f"템플릿을 찾을 수 없습니다: {code}", {"code": code})
    d = _summary(t, True)
    # 보드 없는(제작 중) 템플릿은 원본의 board · title · path 가 null — 빈 값으로 둔다(board 는 빠지고 title · path 는 "")
    source = {k: v for k, v in (t.get("source") or {}).items() if v is not None} or None
    d.update({"params": t.get("params") or {}, "sample_title": t.get("sample_title"), "slots": t["slots"], "boxes": t["boxes"],
              "source": source, "example_slots": sample_slots(t)})
    return d


@router.get("/templates/{code}/thumbnail.png", tags=["templates"], response_class=Response,
            responses={200: {"content": {"image/png": {"schema": {"type": "string", "format": "binary"}}},
                             "description": "썸네일 PNG(w × w·9/16)"}})
async def template_thumbnail(
    code: str, request: Request,
    w: int = Query(DEFAULT_W, ge=MIN_W, le=MAX_W, description="가로 px(세로는 16:9)"),
    brand: str | None = Query(None, pattern=r"^#?[0-9a-fA-F]{6}$", description="포인트 색(기본 #1428a0)"),
) -> Response:
    t = catalog().get(code)
    if t is None:
        raise ApiError(404, "TEMPLATE_NOT_FOUND", f"템플릿을 찾을 수 없습니다: {code}", {"code": code})
    version = catalog_hash()
    b = ("#" + brand.lstrip("#").lower()) if brand else ""
    etag = f'"{version}-{t["code"]}-{w}{b}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    png = await asyncio.to_thread(cached_thumbnail, t["code"], w, version, b)
    return Response(content=png, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400", "ETag": etag})


# ── 모델: 내보내기 ───────────────────────────────────────────

class FormFill(BaseModel):
    """고객사 양식의 한 칸 — 칸 주소(cell) 또는 행(row) · 열(column)로 찾는다."""
    model_config = ConfigDict(extra="ignore")
    sheet: str | int | None = Field(None, description="양식 시트 이름 또는 번호(0부터). 비우면 form.sheet · 첫 보이는 시트")
    cell: str | None = Field(None, description="칸 주소(D7 · $D$7 · 'Sheet'!D7) — 주면 row · column 은 보지 않고, 값이 있어도 덮는다")
    row: int | str | None = Field(None, description="행 번호(1부터) 또는 행 이름(양식 라벨 글로 찾는다 — 단위 괄호 · 번호 매김 무시)")
    column: int | str | None = Field(None, description=(
        "열 번호(1부터) · 머리 글(행 위쪽에서 찾는다) · 열 글자(D). 비우면 행 이름 칸 바로 오른쪽. 행 번호 + 열 번호/글자면 값이 있어도 덮는다"))
    value: Any = Field(None, description="쓸 값 — 글 · 숫자 · {ko, en} · {value, note?}. null · 빈 글이면 쓰지 않는다")
    note: str | None = Field(None, description="셀 메모로 남길 글(예 변환 전 원래 값 · 직접 입력 표시)")


class FormOptions(BaseModel):
    """고객사 양식 맞추기 힌트 · 규칙(모두 선택). document.sheets[i].form 으로 시트마다 덮을 수 있다."""
    model_config = ConfigDict(extra="ignore")
    sheet: str | int | None = Field(None, description="첫 문서 시트 · fills 기본 시트를 쓸 양식 시트(이름 · 0부터 번호). 비우면 이름이 같은 시트 → 첫 보이는 시트")
    header_row: int | None = Field(None, ge=1, description="머리 행 번호(1부터) — 비우면 문서 열 이름이 가장 많이 맞는 행(위 60행)")
    label_column: str | int | None = Field(None, description="행 이름 열(B · 2) — 비우면 이름이 가장 많이 맞는 열")
    label_key: str | None = Field(None, description="문서의 행 이름 열 key — 비우면 글이 든 첫 열")
    column_map: dict[str, str | int] | None = Field(None, description="문서 열 key → 양식 열(글자 D · 번호 4 · 머리 글)")
    row_map: dict[str, str | int] | None = Field(None, description="문서 행 이름(또는 행의 _key · row_key) → 양식 행 번호 · 양식 행 이름")
    orientation: Literal["auto", "rows", "columns"] | None = Field(
        None, description="auto(기본: 문서 그대로와 돌린 것 중 칸이 많이 맞는 쪽) · rows(문서 행 = 양식 행) · columns(문서 행 = 양식 열)")
    overwrite: Literal["empty", "always"] | None = Field(
        None, description="이름으로 맞춘 칸에 값이 이미 있으면: empty(기본 — 비었거나 자리표시일 때만) · always(덮기). 수식 칸은 늘 건너뛴다")
    overwrite_formulas: bool | None = Field(None, description="true 면 수식 칸도 덮는다(기본 false)")
    fuzzy: bool | None = Field(None, description="오타 수준 비슷한 이름도 맞춘다(기본 true — 0.88 이상이고 유일할 때, 보고서 match=fuzzy)")
    unmatched_rows: Literal["report", "append"] | None = Field(
        None, description="못 맞춘 문서 행: report(기본 — 보고만) · append(양식 맨 아래 「추가 항목」에 같은 서식으로 덧붙임)")
    extra_sheets: Literal["drop", "append"] | None = Field(
        None, description="양식과 짝이 없는 문서 시트: drop(기본 — 보고만) · append(우리 디자인 시트로 뒤에 덧붙임, 예 메모 · 출처)")
    highlight_marks: bool | None = Field(None, description="[확인 필요] 같은 자리표시가 든 칸을 노랗게(기본 true)")


class FormFillColumn(BaseModel):
    model_config = ConfigDict(extra="allow")
    key: str
    label: str = ""
    column: str | None = Field(None, description="양식 열 글자(못 맞추면 null)")
    match: str | None = None


class FormFillSheet(BaseModel):
    model_config = ConfigDict(extra="allow")
    sheet: str
    source: str = Field(description="문서 시트(sheets[0])")
    orientation: Literal["rows", "columns"]
    header_row: int | None = None
    label_column: str | None = None
    columns: list[FormFillColumn] = Field(default_factory=list)
    rows_total: int = 0
    rows_matched: int = 0
    cells: int = 0


class FormFillCell(BaseModel):
    model_config = ConfigDict(extra="allow")
    sheet: str
    cell: str
    match: str = Field(description="exact · normalized · base · fuzzy · hint · inferred · cell · number · letter · next_to_label · appended")
    source: str = Field(description="sheets[0].rows[3] · fills[2]")
    row_label: str | None = None
    column_label: str | None = None
    row_match: str | None = None
    column_match: str | None = None
    redirected_from: str | None = Field(None, description="병합 칸 안쪽 주소였으면 원래 주소(머리칸에 썼다)")
    replaced: str | None = Field(None, description="덮어쓴 원래 값")
    warning: str | None = Field(None, description="예: 목록(드롭다운)에 없는 값")
    outside: bool | None = Field(None, description="양식 범위 밖 칸")


class FormFillMiss(BaseModel):
    model_config = ConfigDict(extra="allow")
    sheet: str | None = None
    label: str
    source: str
    key: str | None = None
    candidates: list[str] | None = Field(None, description="값 열 후보(열 글자 + 머리) — form.column_map 으로 고르기")


class FormFillSkip(BaseModel):
    model_config = ConfigDict(extra="allow")
    sheet: str | None = None
    cell: str | None = None
    reason: str = Field(description="formula · merged · locked · not_empty · duplicate · out_of_bounds · invalid_cell · sheet_not_found · column_required")
    source: str
    current: str | None = Field(None, description="not_empty 일 때 칸의 지금 값")


class FormFillRow(BaseModel):
    model_config = ConfigDict(extra="allow")
    sheet: str
    row: int
    label: str
    source: str | None = None


class FormFillLoss(BaseModel):
    part: str = Field(description="shapes · form_controls · header_footer_images · ext_validations · sparklines · …")
    name: str
    base: int
    output: int


class FormFillReport(BaseModel):
    """고객사 양식 채우기 결과 — 쓴 칸 · 못 맞춘 행/열/시트 · 건너뛴 칸 · 양식에만 있는 행 · 유지 못 한 양식 요소."""
    model_config = ConfigDict(extra="allow")
    base_file_id: str
    base_name: str | None = None
    converted_from: str | None = Field(None, description="xls · ods · xlsb 를 LibreOffice 로 .xlsx 로 바꿨으면 그 형식")
    filled: int = Field(description="값을 쓴 칸 수")
    sheets: list[FormFillSheet] = Field(default_factory=list)
    cells: list[FormFillCell] = Field(default_factory=list, description="쓴 칸(최대 300)")
    unmatched_rows: list[FormFillMiss] = Field(default_factory=list)
    unmatched_columns: list[FormFillMiss] = Field(default_factory=list)
    unmatched_sheets: list[str] = Field(default_factory=list)
    skipped: list[FormFillSkip] = Field(default_factory=list)
    form_only_rows: list[FormFillRow] = Field(default_factory=list, description="양식에만 있고 값이 빈 행")
    appended_rows: list[FormFillRow] = Field(default_factory=list)
    appended_sheets: list[str] = Field(default_factory=list)
    lost: list[FormFillLoss] = Field(default_factory=list, description="openpyxl 이 다시 쓰지 못한 양식 요소(저장 전후 개수)")


class ExportRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    format: Literal["pptx", "xlsx", "docx", "pdf", "zip"]
    filename: str | None = Field(None, description="확장자 없이(붙어 있어도 된다). 비우면 문서 제목")
    document: dict[str, Any] | None = Field(None, description=(
        "pptx(·pdf 덱): {title?, cover?:{title,subtitle,customer,date,presenter,image}, footer?, design?, lang?, tbd_label?, "
        "slides:[{template_code, kind?, slots|content, notes?, sources|footnotes?:[{label,url?}], confirm?:[str], sheet_id?}]} · "
        "xlsx: {sheets:[{name, columns:[{key,label,width?,format?}], rows, freeze?, merges?, notes?, header_style?, sources?}]} · "
        "docx · pdf 보고서: {title, subtitle?, meta?, sections:[{heading, level?, paragraphs?, bullets?, numbered?, table?, "
        "images?, captions?, sources?}], page_size?: A4|Letter, orientation?} (pdf 는 {report: …} 로 감싸도 된다) · "
        "zip: {entries:[{file_id, path} | {path, text|json} | {path, format, document}]}"))
    document_file_id: str | None = Field(None, description="문서 JSON 을 files 에 올렸으면 그 id(ProposalRenderDoc 등)")
    from_file_id: str | None = Field(None, description="pdf: 이 파일(PPTX · DOCX · XLSX)을 PDF 로 바꾼다 — LibreOffice 필요")
    design: dict[str, Any] | None = Field(None, description=(
        "{brand_hex?, master_id?(samsung_b2b · retail_fnb · simple_white · mst_…), master_file_id?(.potx/.pptx), "
        "logo_file_id?, cover_image_file_id?, cover_template?, page_numbers?}"))
    master_id: str | None = None
    language: Literal["ko", "en", "both", "ko_en"] | None = Field(None, description="both = 한국어 + 영문")
    lang: Literal["ko", "en", "both", "ko_en"] | None = Field(None, description="language 와 같다(ProposalRenderDoc)")
    bilingual: Literal["files", "slides", "inline"] | None = Field(
        None, description="language=both 일 때: files(기본, _KO · _EN 두 파일) · slides(한 덱에 KO/EN 번갈아) · inline(한 칸에 두 줄)")
    tbd_mode: Literal["keep_marks", "move_to_notes", "keep", "notes"] | None = Field(
        None, description="keep_marks(기본) · move_to_notes(칸은 「—」, 문장은 발표자 노트)")
    tbd_label: str | None = Field(None, description="영문 확인 필요 표시(기본 [TBD])")
    confidential: bool = False
    project_id: str | None = None
    source_ref: str | None = Field(None, description="만든 곳(예 proposal:prp_…) — 파일 메타에 남긴다")
    async_: bool | None = Field(None, alias="async", description="true 면 늘 잡(202)으로")
    base_file_id: str | None = Field(None, description=(
        "xlsx: 고객사 양식(.xlsx · .xlsm · .xltx · .xls · .ods — 옛 형식은 LibreOffice 필요) — 이 파일 사본의 칸에 값만 써 넣는다"
        "(서식 · 병합 · 수식 · 열 너비 유지). document.sheets(행 이름 × 열 머리로 맞춤) · fills(칸 하나씩) 중 하나 이상. "
        "기밀 · project_id 는 원본을 이어받는다. 결과는 form_fill 보고"))
    customer_template_file_id: str | None = Field(None, description="base_file_id 와 같다")
    fills: list[FormFill] | None = Field(None, description="base_file_id 양식에 칸 하나씩 쓰기(document 다음에 적용)")
    form: FormOptions | None = Field(None, description="base_file_id 양식 맞추기 힌트 · 규칙")


class ExportFile(BaseModel):
    id: str
    name: str
    mime: str
    size: int
    url: str
    lang: str | None = None


class ExportError(BaseModel):
    code: str
    message: str


class ExportResult(BaseModel):
    export_id: str
    status: Literal["done"]
    file: ExportFile
    files: list[ExportFile]
    template_codes: list[str] = Field(default_factory=list)
    slide_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    form_fill: FormFillReport | None = Field(None, description="base_file_id(고객사 양식)로 만들었을 때만")


class ExportAccepted(BaseModel):
    export_id: str
    job_id: str
    status: Literal["queued"]


class ExportRecord(BaseModel):
    export_id: str
    status: Literal["queued", "running", "done", "failed"]
    format: str
    mode: str | None = None
    language: str | None = None
    bilingual: str | None = None
    filename: str | None = None
    file: ExportFile | None = None
    files: list[ExportFile] = Field(default_factory=list)
    job_id: str | None = None
    project_id: str | None = None
    source_ref: str | None = None
    template_codes: list[str] = Field(default_factory=list)
    slide_count: int | None = None
    warnings: list[str] = Field(default_factory=list)
    error: ExportError | None = None
    owner: str | None = None
    confidential: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None
    form_fill: FormFillReport | None = None


class ExportList(BaseModel):
    items: list[ExportRecord]
    next_cursor: str | None = None


# ── 내보내기 API ─────────────────────────────────────────────

@router.post("/exports", response_model=ExportResult, status_code=201, tags=["exports"],
             responses={202: {"model": ExportAccepted, "description": "느린 내보내기(LibreOffice PDF · 큰 덱) — 잡으로 처리"},
                        501: {"description": "PDF_CONVERTER_UNAVAILABLE — LibreOffice(SOFFICE_PATH) 없음"}})
async def create_export(body: ExportRequest) -> Any:
    raw = body.model_dump(by_alias=True, exclude_none=True)
    plan = await service.prepare(raw)
    st = service.store()
    if service.is_slow(plan):
        rec = await asyncio.to_thread(st.put, "exports", plan.export_id, service.plan_record(plan, "queued"))
        job = await jobs().enqueue("export", "export", {"export_id": plan.export_id}, title=f"내보내기 · {plan.filename}.{plan.format}",
                                   ref=plan.export_id, project_id=plan.project_id)
        await asyncio.to_thread(st.patch, "exports", rec["id"], {"job_id": job.id})
        return JSONResponse({"export_id": plan.export_id, "job_id": job.id, "status": "queued"}, status_code=202)
    await asyncio.to_thread(st.put, "exports", plan.export_id, service.plan_record(plan, "running"))
    try:
        result = await service.execute(plan)
    except Exception as exc:  # noqa: BLE001
        err = service.to_api_error(exc)
        await asyncio.to_thread(st.patch, "exports", plan.export_id, {"status": "failed", "error": {"code": err.code, "message": err.message}})
        raise err from exc
    await asyncio.to_thread(st.patch, "exports", plan.export_id, {"status": "done", **result})
    return {"export_id": plan.export_id, "status": "done", **result}


@router.get("/exports", response_model=ExportList, tags=["exports"])
async def list_exports(project_id: str | None = None, source_ref: str | None = None, limit: int = Query(50, ge=1, le=200),
                       cursor: str | None = None) -> dict[str, Any]:
    where = {k: v for k, v in {"project_id": project_id, "source_ref": source_ref}.items() if v}
    items, nxt = await asyncio.to_thread(service.store().list, "exports", where=where or None, limit=limit, cursor=cursor)
    return {"items": [service.public_record(r) for r in items], "next_cursor": nxt}


@router.get("/exports/{export_id}", response_model=ExportRecord, tags=["exports"])
async def get_export(export_id: str) -> dict[str, Any]:
    rec = await asyncio.to_thread(service.store().get, "exports", export_id)
    if rec is None:
        raise ApiError(404, "NOT_FOUND", f"내보내기를 찾을 수 없습니다: {export_id}", {"export_id": export_id})
    return service.public_record(rec)


# ── 모델 · API: 렌더 ─────────────────────────────────────────

class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    file_id: str | None = Field(None, description="PPTX(LibreOffice 필요) · PDF(바로) 파일")
    document: dict[str, Any] | None = Field(None, description="덱 문서(POST /exports 의 pptx 문서와 같다)")
    document_file_id: str | None = None
    design: dict[str, Any] | None = None
    master_id: str | None = None
    language: Literal["ko", "en", "both", "ko_en"] | None = None
    max_slides: int | None = Field(None, ge=1, le=500)
    sheet_ids: list[str] | None = Field(None, description="이 시트(slides[].sheet_id)만")
    width: int | None = Field(None, ge=320, le=2560, description="PNG 가로 px(기본 1280)")
    project_id: str | None = None
    confidential: bool = False


class RenderPage(BaseModel):
    index: int
    sheet_id: str | None = None
    file_id: str
    png_file_id: str
    url: str


class RenderAccepted(BaseModel):
    render_id: str
    job_id: str
    status: Literal["queued"]


class RenderRecord(BaseModel):
    render_id: str
    status: Literal["queued", "running", "done", "failed"]
    job_id: str | None = None
    pages: list[RenderPage] = Field(default_factory=list)
    source_file_id: str | None = None
    error: ExportError | None = None
    warnings: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


@router.post("/renders", response_model=RenderAccepted, status_code=202, tags=["renders"],
             responses={501: {"description": "PDF_CONVERTER_UNAVAILABLE — LibreOffice(SOFFICE_PATH) 없음"}})
async def create_render(body: RenderRequest) -> dict[str, Any]:
    from winmate_common.ids import new_id

    rec = await service.prepare_render(body.model_dump(exclude_none=True))
    rid = new_id("rnd")
    st = service.store()
    await asyncio.to_thread(st.put, "renders", rid, rec)
    job = await jobs().enqueue("export", "render", {"render_id": rid}, title="슬라이드 그림 만들기", ref=rid,
                               project_id=rec.get("project_id"))
    await asyncio.to_thread(st.patch, "renders", rid, {"job_id": job.id})
    return {"render_id": rid, "job_id": job.id, "status": "queued"}


@router.get("/renders/{render_id}", response_model=RenderRecord, tags=["renders"])
async def get_render(render_id: str) -> dict[str, Any]:
    rec = await asyncio.to_thread(service.store().get, "renders", render_id)
    if rec is None:
        raise ApiError(404, "NOT_FOUND", f"렌더를 찾을 수 없습니다: {render_id}", {"render_id": render_id})
    return service.public_render(rec)


# ── 모델 · API: 마스터 ───────────────────────────────────────

class Master(BaseModel):
    master_id: str
    name: str
    description: str = ""
    builtin: bool
    file_id: str | None = None
    cover_template: str = "C01"
    layouts: list[str] = Field(default_factory=list)
    aspect: str = ""
    project_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    created_at: str | None = None


class MasterList(BaseModel):
    items: list[Master]


class MasterCreate(BaseModel):
    file_id: str = Field(description=".potx · .pptx 파일 id(files)")
    name: str | None = None
    project_id: str | None = None


@router.get("/masters", response_model=MasterList, tags=["masters"])
async def list_masters(project_id: str | None = None) -> dict[str, Any]:
    return {"items": await service.list_masters(project_id)}


@router.post("/masters", response_model=Master, status_code=201, tags=["masters"])
async def create_master(body: MasterCreate) -> dict[str, Any]:
    return await service.register_master(body.file_id, body.name, body.project_id)
