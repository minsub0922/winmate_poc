"""내보내기 실행 — 요청 검증 → 자원(문서 · 이미지 · 로고 · 마스터) 미리 받기 → 만들기 → files 저장 → 기록.

빠른 것(슬라이드 EXPORT_SYNC_MAX_SLIDES 장 이하, LibreOffice 없이 되는 것)은 API 가 바로 만들어 201,
느린 것(LibreOffice PDF · 큰 덱 · 큰 ZIP · async=true)은 잡으로 넘겨 202 → worker.py 가 같은 execute() 를 부른다.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from winmate_common import platform
from winmate_common.context import current_user
from winmate_common.env import get, get_int, settings
from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso
from winmate_common.store import DocStore

from .render import soffice
from .render.docx_render import DocxError, build_docx
from .render.pdf_render import PdfError, build_pdf
from .render.pptx_render import (
    Asset,
    DeckRenderer,
    DictAssets,
    RenderError,
    open_master,
)
from .render.theme import FONT, MASTERS, Theme
from .render.values import collect_file_ids, to_text
from .render.xlsx_form import FormError, Opts, fill_form, validate_fills
from .render.xlsx_render import XlsxError, build_xlsx
from .render.zip_build import ZipError, build_zip
from .templates.catalog import catalog

log = logging.getLogger("winmate.export")

MIME = {
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "zip": "application/zip",
    "png": "image/png",
    "xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
}
# 고객사 양식(base_file_id): 바로 여는 형식 · LibreOffice 로 .xlsx 로 바꿔 여는 형식
FORM_EXTS = {"xlsx", "xlsm", "xltx", "xltm"}
CONVERT_EXTS = {"xls", "ods", "xlsb"}
SHEET_MIMES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel.sheet.macroEnabled.12": "xlsm",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.template": "xltx",
    "application/vnd.ms-excel.template.macroEnabled.12": "xltm",
    "application/vnd.ms-excel": "xls",
    "application/vnd.oasis.opendocument.spreadsheet": "ods",
    "application/vnd.ms-excel.sheet.binary.macroEnabled.12": "xlsb",
}
FILE_ID_RE = re.compile(r"^file_[0-9A-Za-z]{26}$")
KIND_DEFAULTS = {"cover", "toc", "divider", "closing", "appendix"}
LANG_ALIASES = {"ko": "ko", "kr": "ko", "en": "en", "both": "both", "ko_en": "both", "ko+en": "both", "ko-en": "both", "bilingual": "both"}
BAD_NAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


# ── 저장소 ────────────────────────────────────────────────

@lru_cache(maxsize=8)
def _store(path: str) -> DocStore:
    return DocStore(Path(path))


def store() -> DocStore:
    return _store(str(settings().service_data_dir("export") / "export.sqlite"))


def sync_max_slides() -> int:
    return get_int("EXPORT_SYNC_MAX_SLIDES", 40)


def sync_max_zip_entries() -> int:
    return get_int("EXPORT_SYNC_MAX_ZIP", 40)


# ── 오류 ─────────────────────────────────────────────────

def bad(code: str, message: str, **details: Any) -> ApiError:
    return ApiError(400, code, message, details)


def converter_unavailable(what: str) -> ApiError:
    """501 — 왜 없는지(off · 경로 없음 · 비어 있음)와 고칠 방법(이 서버에서 찾은 soffice 경로 · 설치 명령)을 함께."""
    message, details = soffice.unavailable_message(what)
    return ApiError(501, "PDF_CONVERTER_UNAVAILABLE", message, details)


def to_api_error(exc: Exception) -> ApiError:
    if isinstance(exc, ApiError):
        return exc
    if isinstance(exc, (RenderError, FormError)):
        return ApiError(400, exc.code, exc.message, exc.details)
    if isinstance(exc, (XlsxError, DocxError, PdfError, ZipError)):
        return ApiError(400, "VALIDATION_FAILED", str(exc))
    if isinstance(exc, soffice.ConverterUnavailable):
        return converter_unavailable("변환")
    if isinstance(exc, soffice.ConversionFailed):
        return ApiError(502, "CONVERSION_FAILED", str(exc))
    return ApiError(500, "EXPORT_FAILED", f"파일을 만들지 못했습니다: {type(exc).__name__}: {exc}")


# ── 계획 ─────────────────────────────────────────────────

@dataclass
class Plan:
    export_id: str
    format: str                       # pptx | xlsx | docx | pdf | zip
    mode: str                         # deck | sheets | docx | report | zip | convert
    filename: str                     # 확장자 없는 이름
    document: dict[str, Any] | None
    design: dict[str, Any]
    language: str                     # ko | en | both
    bilingual: str                    # files | slides | inline
    confidential: bool = False
    project_id: str | None = None
    source_ref: str | None = None
    from_file_id: str | None = None
    tbd_mode: str = "keep"
    tbd_label: str | None = None
    owner: str | None = None
    slide_count: int = 0
    needs_soffice: bool = False
    force_async: bool = False
    base_file_id: str | None = None            # mode=form: 고객사 양식 XLSX
    base_name: str | None = None
    base_ext: str | None = None                # xlsx · xlsm · xltx · xltm · (xls · ods · xlsb → LibreOffice 로 바꿈)
    fills: list[Any] | None = None
    form: dict[str, Any] | None = None

    def langs(self) -> list[str]:
        if self.language == "both" and self.bilingual == "files" and self.format != "zip":
            return ["ko", "en"]
        return [self.language]


def norm_lang(v: Any) -> str:
    key = str(v or "ko").strip().lower()
    if key not in LANG_ALIASES:
        raise bad("VALIDATION_FAILED", f"지원하지 않는 언어입니다: {v}", allowed=["ko", "en", "both"])
    return LANG_ALIASES[key]


def safe_filename(name: Any, fallback: str = "winmate_export") -> str:
    s = unicodedata.normalize("NFC", str(name or "")).strip()
    s = re.sub(r"\.(pptx|xlsx|docx|pdf|zip|potx)$", "", s, flags=re.I)
    s = BAD_NAME.sub("_", s).strip(" ._")
    return (s or fallback)[:120]


async def load_json_file(file_id: str) -> dict[str, Any]:
    try:
        data, _mime = await platform.file_bytes(file_id)
    except ApiError as exc:
        if exc.status == 404:
            raise ApiError(404, "FILE_NOT_FOUND", f"문서 파일을 찾을 수 없습니다: {file_id}", {"file_id": file_id}) from exc
        raise
    try:
        doc = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise bad("INVALID_DOCUMENT", "문서 파일이 JSON 이 아닙니다", file_id=file_id) from exc
    if not isinstance(doc, dict):
        raise bad("INVALID_DOCUMENT", "문서 JSON 은 객체여야 합니다", file_id=file_id)
    return doc


def _check_deck(doc: dict[str, Any]) -> int:
    slides = doc.get("slides")
    if not isinstance(slides, list) or not slides:
        raise bad("VALIDATION_FAILED", "document.slides 가 비어 있습니다")
    cat = catalog()
    unknown, need_code = [], []
    for i, s in enumerate(slides):
        if not isinstance(s, dict):
            raise bad("VALIDATION_FAILED", f"slides[{i}] 형식이 잘못되었습니다")
        code = s.get("template_code")
        if code:
            if cat.get(str(code), s.get("slots") if isinstance(s.get("slots"), dict) else s.get("content")) is None:
                unknown.append(str(code))
        elif (s.get("kind") or "sheet").lower() not in KIND_DEFAULTS:
            need_code.append(i)
    if unknown:
        raise bad("TEMPLATE_NOT_FOUND", f"카탈로그에 없는 템플릿 코드: {', '.join(sorted(set(unknown))[:10])}",
                  codes=sorted(set(unknown)))
    if need_code:
        raise bad("TEMPLATE_REQUIRED", "template_code 가 없는 슬라이드가 있습니다", slides=need_code[:20])
    return len(slides) + (1 if doc.get("cover") else 0)


async def prepare(body: dict[str, Any]) -> Plan:
    """요청(본문 dict) → 실행 계획. 형식 오류는 여기서 4xx 로 끝낸다."""
    fmt = str(body.get("format") or "").lower()
    if fmt not in ("pptx", "xlsx", "docx", "pdf", "zip"):
        raise bad("VALIDATION_FAILED", f"지원하지 않는 형식입니다: {fmt}", allowed=["pptx", "xlsx", "docx", "pdf", "zip"])
    doc = body.get("document")
    if doc is None and body.get("document_file_id"):
        doc = await load_json_file(str(body["document_file_id"]))
    from_file_id = body.get("from_file_id") or ((doc or {}).get("from_file_id") if isinstance(doc, dict) else None)
    base_id = body.get("base_file_id") or body.get("customer_template_file_id")
    form_mode = bool(base_id) or body.get("fills") is not None or body.get("form") is not None
    if form_mode:
        if fmt != "xlsx":
            raise bad("VALIDATION_FAILED", "고객사 양식 채우기(base_file_id · fills · form)는 format=xlsx 에서만 됩니다")
        if not base_id:
            raise bad("VALIDATION_FAILED", "fills · form 은 base_file_id(고객사 양식 XLSX)와 함께 씁니다")
    if doc is None and not from_file_id and not form_mode:
        raise bad("VALIDATION_FAILED", "document · document_file_id · from_file_id 중 하나가 필요합니다")
    if doc is not None and not isinstance(doc, dict):
        raise bad("VALIDATION_FAILED", "document 는 객체여야 합니다")
    doc = doc or {}
    language = norm_lang(body.get("language") or body.get("lang") or doc.get("lang") or doc.get("language") or "ko")
    bilingual = str(body.get("bilingual") or doc.get("bilingual") or "files").lower()
    if bilingual not in ("files", "slides", "inline"):
        raise bad("VALIDATION_FAILED", f"bilingual 은 files · slides · inline 중 하나입니다: {bilingual}")
    design = {**(doc.get("design") or {}), **(body.get("design") or {})}
    if body.get("master_id"):
        design["master_id"] = body["master_id"]
    mode, needs = "", False
    slide_count = 0
    if fmt == "pptx":
        mode, slide_count = "deck", _check_deck(doc)
    elif fmt == "pdf":
        if from_file_id:
            mode, needs = "convert", True
        elif isinstance(doc.get("slides"), list):
            mode, needs, slide_count = "deck", True, _check_deck(doc)
        elif isinstance(doc.get("report"), dict) or isinstance(doc.get("sections"), list):
            mode = "report"
        else:
            raise bad("VALIDATION_FAILED", "PDF 는 report(보고서) · slides(덱) · from_file_id 중 하나가 필요합니다")
    elif fmt == "xlsx" and form_mode:
        fills = body.get("fills")
        try:
            validate_fills(fills)
            Opts.parse(body.get("form"))
        except FormError as exc:
            raise ApiError(400, exc.code, exc.message, exc.details) from exc
        if doc.get("sheets") is not None and not isinstance(doc.get("sheets"), list):
            raise bad("VALIDATION_FAILED", "document.sheets 는 목록이어야 합니다")
        if not doc.get("sheets") and not fills:
            raise bad("VALIDATION_FAILED", "고객사 양식에 쓸 document.sheets 또는 fills 가 필요합니다")
        base = await base_file(str(base_id))
        mode, needs = "form", base["_ext"] in CONVERT_EXTS
        if needs and not soffice.available():
            raise converter_unavailable(f"옛 형식(.{base['_ext']}) 고객사 양식 읽기")
    elif fmt == "xlsx":
        if not isinstance(doc.get("sheets"), list) or not doc["sheets"]:
            raise bad("VALIDATION_FAILED", "document.sheets 가 비어 있습니다")
        mode = "sheets"
    elif fmt == "docx":
        if not isinstance(doc.get("sections"), list):
            raise bad("VALIDATION_FAILED", "document.sections 가 필요합니다")
        mode = "docx"
    elif fmt == "zip":
        if not isinstance(doc.get("entries"), list) or not doc["entries"]:
            raise bad("VALIDATION_FAILED", "document.entries 가 비어 있습니다")
        mode = "zip"
    if needs and not soffice.available():
        raise converter_unavailable("PPTX → PDF 변환" if mode == "deck" else "파일 → PDF 변환")
    if language == "both" and bilingual == "slides":
        slide_count *= 2
    title = to_text((doc.get("cover") or {}).get("title") or doc.get("title") or (doc.get("report") or {}).get("title"), "ko")
    tbd_mode = str(body.get("tbd_mode") or doc.get("tbd_mode") or "keep").lower()
    if tbd_mode in ("move_to_notes", "notes"):
        tbd_mode = "notes"
    elif tbd_mode in ("keep", "keep_marks"):
        tbd_mode = "keep"
    else:
        raise bad("VALIDATION_FAILED", f"tbd_mode 는 keep_marks · move_to_notes 중 하나입니다: {tbd_mode}")
    confidential, project_id = bool(body.get("confidential", False)), body.get("project_id")
    form_fields: dict[str, Any] = {}
    if mode == "form":
        # 고객 자료 — 원본 양식의 기밀 · 프로젝트를 이어받는다(요청이 더 엄하면 요청대로)
        confidential = confidential or bool(base.get("confidential"))
        project_id = project_id or base.get("project_id")
        stem = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", str(base.get("name") or "")).strip()
        title = f"{stem}_{'filled' if language == 'en' else '작성'}" if stem else title
        form_fields = {"base_file_id": str(base_id), "base_name": base.get("name"), "base_ext": base["_ext"],
                       "fills": body.get("fills"), "form": body.get("form")}
    return Plan(
        export_id=new_id("exp"), format=fmt, mode=mode,
        filename=safe_filename(body.get("filename") or body.get("file_name") or doc.get("filename") or title),
        document=doc if mode != "convert" else None, design=design, language=language, bilingual=bilingual,
        confidential=confidential, project_id=project_id, source_ref=body.get("source_ref"),
        from_file_id=from_file_id, tbd_mode=tbd_mode, tbd_label=body.get("tbd_label") or doc.get("tbd_label"),
        owner=current_user().id, slide_count=slide_count, needs_soffice=needs, force_async=bool(body.get("async")),
        **form_fields,
    )


async def base_file(file_id: str) -> dict[str, Any]:
    """고객사 양식 파일 메타 + 형식(_ext). 없으면 404, 엑셀이 아니면 400 INVALID_BASE_FILE."""
    try:
        meta = await platform.file_meta(file_id)
    except ApiError as exc:
        if exc.status == 404:
            raise ApiError(404, "FILE_NOT_FOUND", f"고객사 양식 파일을 찾을 수 없습니다: {file_id}", {"file_id": file_id}) from exc
        raise
    name = str(meta.get("name") or "")
    m = re.search(r"\.([A-Za-z0-9]{2,5})$", name)
    ext = m.group(1).lower() if m else ""
    if ext not in FORM_EXTS | CONVERT_EXTS:
        ext = SHEET_MIMES.get(str(meta.get("mime") or "").split(";")[0].strip(), ext)
    if ext not in FORM_EXTS | CONVERT_EXTS:
        raise bad("INVALID_BASE_FILE", "고객사 양식은 엑셀 파일이어야 합니다(.xlsx · .xlsm · .xls · .ods)",
                  file_id=file_id, name=name, mime=meta.get("mime"))
    return {**meta, "_ext": ext}


def is_slow(plan: Plan) -> bool:
    if plan.force_async or plan.needs_soffice:
        return True
    if plan.mode == "deck" and plan.slide_count * len(plan.langs()) > sync_max_slides():
        return True
    if plan.mode == "zip" and len((plan.document or {}).get("entries") or []) > sync_max_zip_entries():
        return True
    return False


# ── 자원 미리 받기 ───────────────────────────────────────────

def _string_ids(obj: Any, out: set[str]) -> None:
    if isinstance(obj, str):
        if FILE_ID_RE.match(obj):
            out.add(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _string_ids(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _string_ids(v, out)


def referenced_files(plan: Plan) -> set[str]:
    ids: set[str] = set()
    if plan.document:
        collect_file_ids(plan.document, ids)
        _string_ids(plan.document, ids)
    for k in ("logo_file_id", "cover_image_file_id", "master_file_id"):
        v = plan.design.get(k)
        if isinstance(v, str) and v:
            ids.add(v)
    if plan.from_file_id:
        ids.add(plan.from_file_id)
    if plan.base_file_id:
        ids.add(plan.base_file_id)
    return ids


async def fetch_assets(ids: set[str], *, strict: set[str] | None = None, concurrency: int = 6) -> tuple[dict[str, Asset], list[str]]:
    """file_id → Asset(바이트 + FileMeta). strict 에 든 것은 없으면 오류, 나머지는 경고."""
    sem = asyncio.Semaphore(concurrency)
    assets: dict[str, Asset] = {}
    warnings: list[str] = []
    strict = strict or set()

    async def one(fid: str) -> None:
        async with sem:
            try:
                data, mime = await platform.file_bytes(fid)
                try:
                    meta = await platform.file_meta(fid)
                except ApiError:
                    meta = {}
                assets[fid] = Asset(data=data, mime=(meta.get("mime") or mime or ""), meta=meta)
            except ApiError as exc:
                if fid in strict:
                    raise ApiError(404 if exc.status == 404 else 502, "FILE_NOT_FOUND" if exc.status == 404 else "UPSTREAM_FAILED",
                                   f"파일을 가져오지 못했습니다: {fid}", {"file_id": fid, "upstream": exc.code}) from exc
                warnings.append(f"file {fid}: {exc.code}")

    await asyncio.gather(*(one(f) for f in sorted(ids)))
    return assets, warnings


async def resolve_master(plan: Plan, assets: dict[str, Asset]) -> None:
    """design.master_id(mst_…) · master_file_id → design['_master_bytes']."""
    mid = plan.design.get("master_id")
    fid = plan.design.get("master_file_id")
    if isinstance(mid, str) and mid and mid not in MASTERS:
        rec = await asyncio.to_thread(store().get, "masters", mid)
        if rec is None:
            raise ApiError(404, "MASTER_NOT_FOUND", f"마스터를 찾을 수 없습니다: {mid}", {"master_id": mid})
        fid = rec["file_id"]
    if fid:
        if fid not in assets:
            got, _ = await fetch_assets({fid}, strict={fid})
            assets.update(got)
        plan.design["_master_bytes"] = assets[fid].data


# ── 만들기 ───────────────────────────────────────────────

@dataclass
class Output:
    name: str
    data: bytes
    mime: str
    lang: str | None = None


@dataclass
class BuildResult:
    outputs: list[Output] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    template_codes: list[str] = field(default_factory=list)
    slide_count: int = 0
    form_fill: dict[str, Any] | None = None


def _ext_of(name: str, mime: str) -> str:
    m = re.search(r"\.([A-Za-z0-9]{2,5})$", name or "")
    if m:
        return m.group(1).lower()
    for ext, mm in MIME.items():
        if mm == mime:
            return ext
    return "bin"


def _deck(plan: Plan, lang: str, assets: dict[str, Asset], res: BuildResult) -> bytes:
    design = dict(plan.design)
    r = DeckRenderer(theme=Theme.from_design(design), lang=lang, assets=DictAssets(assets), design=design,
                     confidential=plan.confidential, bilingual=plan.bilingual, tbd_mode=plan.tbd_mode, tbd_label=plan.tbd_label)
    data = r.render(plan.document or {})
    res.warnings.extend(r.warnings)
    if not res.template_codes:
        res.template_codes = list(dict.fromkeys(r.template_codes))
    res.slide_count = max(res.slide_count, r.slide_count)
    return data


def build_nested(fmt: str, doc: dict[str, Any], plan: Plan, assets: dict[str, Asset], res: BuildResult) -> bytes:
    """ZIP 안에 함께 만드는 문서."""
    lang = plan.language if plan.language != "both" else "ko"
    if fmt == "xlsx":
        return build_xlsx(doc, design=plan.design, lang=lang, confidential=plan.confidential)
    if fmt == "docx":
        data, w = build_docx(doc, design=plan.design, lang=lang, assets=DictAssets(assets), confidential=plan.confidential)
        res.warnings.extend(w)
        return data
    if fmt == "pdf":
        data, w = build_pdf(doc, design=plan.design, lang=lang, assets=DictAssets(assets), confidential=plan.confidential,
                            ttf_path=get("EXPORT_PDF_TTF"))
        res.warnings.extend(w)
        return data
    if fmt == "pptx":
        sub = Plan(**{**asdict(plan), "document": doc, "format": "pptx", "mode": "deck"})
        _check_deck(doc)
        return _deck(sub, lang, assets, res)
    raise ZipError(f"ZIP 안에서 만들 수 없는 형식입니다: {fmt}")


def form_base(plan: Plan, assets: dict[str, Asset]) -> tuple[bytes, str | None]:
    """고객사 양식 바이트(.xls · .ods · .xlsb 는 LibreOffice 로 .xlsx 로 바꾼다) → (바이트, 바꾼 원래 형식)."""
    src = assets[plan.base_file_id or ""]
    if plan.base_ext in CONVERT_EXTS:
        return soffice.convert(src.data, plan.base_ext or "xls", "xlsx"), plan.base_ext
    return src.data, None


def build_form(plan: Plan, data: bytes, converted: str | None, lang: str) -> tuple[bytes, dict[str, Any], list[str]]:
    out, report, warns = fill_form(data, document=plan.document or None, fills=plan.fills, options=plan.form, lang=lang,
                                   design=plan.design, confidential=plan.confidential, macro=plan.base_ext in ("xlsm", "xltm"))
    report = {"base_file_id": plan.base_file_id, "base_name": plan.base_name, **({"converted_from": converted} if converted else {}),
              **report}
    if converted:
        warns = [f"옛 형식(.{converted}) 양식을 LibreOffice 로 .xlsx 로 바꿔 채웠습니다 — 서식이 조금 달라질 수 있어요", *warns]
    return out, report, warns


def output_type(plan: Plan) -> tuple[str, str]:
    """(확장자, MIME) — 매크로 양식(.xlsm · .xltm)을 채우면 .xlsm 으로 낸다."""
    if plan.mode == "form" and plan.base_ext in ("xlsm", "xltm"):
        return "xlsm", MIME["xlsm"]
    return plan.format, MIME[plan.format]


def _font_note(warnings: list[str]) -> None:
    """우리 덱을 LibreOffice 로 PDF · 그림으로 만들 때 — 서버에서 글꼴이 바뀌면 알린다."""
    w = soffice.font_warning(FONT)
    if w and w not in warnings:
        warnings.append(w)


def build(plan: Plan, assets: dict[str, Asset]) -> BuildResult:
    """CPU 일(스레드에서 부른다)."""
    res = BuildResult()
    ext, mime = output_type(plan)
    langs = plan.langs()
    base: tuple[bytes, str | None] | None = form_base(plan, assets) if plan.mode == "form" else None
    for lang in langs:
        suffix = f"_{lang.upper()}" if len(langs) > 1 else ""
        name = f"{plan.filename}{suffix}.{ext}"
        if plan.mode == "form" and base is not None:
            data, report, warns = build_form(plan, base[0], base[1], lang)
            res.warnings.extend(x for x in warns if x not in res.warnings)
            if res.form_fill is None:
                res.form_fill = report
        elif plan.mode == "deck":
            data = _deck(plan, lang, assets, res)
            if plan.format == "pdf":
                data = soffice.convert(data, "pptx", "pdf")
                _font_note(res.warnings)
        elif plan.mode == "sheets":
            data = build_xlsx(plan.document or {}, design=plan.design, lang=lang, confidential=plan.confidential)
        elif plan.mode == "docx":
            data, w = build_docx(plan.document or {}, design=plan.design, lang=lang, assets=DictAssets(assets),
                                 confidential=plan.confidential)
            res.warnings.extend(w)
        elif plan.mode == "report":
            data, w = build_pdf(plan.document or {}, design=plan.design, lang=lang, assets=DictAssets(assets),
                                confidential=plan.confidential, ttf_path=get("EXPORT_PDF_TTF"))
            res.warnings.extend(w)
        elif plan.mode == "convert":
            src = assets[plan.from_file_id or ""]
            data = soffice.convert(src.data, _ext_of(str(src.meta.get("name") or ""), src.mime), "pdf")
        elif plan.mode == "zip":
            files = {fid: a.data for fid, a in assets.items()}
            names = {fid: str(a.meta.get("name") or fid) for fid, a in assets.items()}
            data = build_zip(plan.document or {}, files=files, names=names,
                             nested=lambda f, d: build_nested(f, d, plan, assets, res))
        else:  # pragma: no cover
            raise RuntimeError(plan.mode)
        res.outputs.append(Output(name=name, data=data, mime=mime, lang=lang))
    return res


async def execute(plan: Plan, progress: Any = None) -> dict[str, Any]:
    """미리 받기 → 만들기 → 저장. 기록에 넣을 결과 dict 를 돌려준다."""
    async def step(pct: int, msg: str) -> None:
        if progress is not None:
            await progress(pct, msg)

    await step(5, "자료 받는 중")
    ids = referenced_files(plan)
    strict: set[str] = set()
    if plan.mode == "zip":
        strict = {e["file_id"] for e in (plan.document or {}).get("entries") or [] if isinstance(e, dict) and e.get("file_id")}
    if plan.from_file_id:
        strict.add(plan.from_file_id)
    if plan.base_file_id:
        strict.add(plan.base_file_id)
    if plan.design.get("master_file_id"):
        strict.add(plan.design["master_file_id"])
    assets, warnings = await fetch_assets(ids, strict=strict)
    await resolve_master(plan, assets)
    await step(30, "파일 만드는 중")
    res = await asyncio.to_thread(build, plan, assets)
    res.warnings = warnings + res.warnings
    await step(85, "저장하는 중")
    files = []
    for out in res.outputs:
        meta = {"export_id": plan.export_id, "format": plan.format, "language": out.lang or plan.language,
                "template_codes": res.template_codes, "source_ref": plan.source_ref, "base_file_id": plan.base_file_id}
        fm = await platform.save_file(out.name, out.data, out.mime, source="export", confidential=plan.confidential,
                                      project_id=plan.project_id, meta={k: v for k, v in meta.items() if v not in (None, [], "")})
        files.append({"id": fm["id"], "name": fm.get("name") or out.name, "mime": fm.get("mime") or out.mime,
                      "size": int(fm.get("size") or len(out.data)), "url": fm.get("url") or f"/api/files/v1/files/{fm['id']}/content",
                      "lang": out.lang if len(res.outputs) > 1 else None})
    await step(100, "완료")
    return {"files": files, "file": files[0] if files else None, "template_codes": res.template_codes,
            "slide_count": res.slide_count, "warnings": res.warnings[:100], "form_fill": res.form_fill}


# ── 기록 ─────────────────────────────────────────────────

PUBLIC_KEYS = ("status", "format", "mode", "language", "bilingual", "filename", "file", "files", "job_id", "project_id",
               "source_ref", "template_codes", "slide_count", "warnings", "error", "owner", "confidential", "form_fill")


def public_record(rec: dict[str, Any]) -> dict[str, Any]:
    out = {"export_id": rec["id"], **{k: rec.get(k) for k in PUBLIC_KEYS}}
    out["created_at"], out["updated_at"] = rec.get("created_at"), rec.get("updated_at")
    out["files"] = out.get("files") or []
    out["template_codes"] = out.get("template_codes") or []
    out["warnings"] = out.get("warnings") or []
    return out


def plan_record(plan: Plan, status: str, **extra: Any) -> dict[str, Any]:
    d = asdict(plan)
    d["design"] = {k: v for k, v in plan.design.items() if not k.startswith("_")}
    return {"status": status, "format": plan.format, "mode": plan.mode, "language": plan.language, "bilingual": plan.bilingual,
            "filename": plan.filename, "project_id": plan.project_id, "source_ref": plan.source_ref, "owner": plan.owner,
            "confidential": plan.confidential, "slide_count": plan.slide_count, "plan": d, **extra}


def plan_from_record(rec: dict[str, Any]) -> Plan:
    return Plan(**rec["plan"])


# ── 마스터 ───────────────────────────────────────────────

def builtin_masters() -> list[dict[str, Any]]:
    return [{"master_id": k, "name": v["name"], "description": v["desc"], "builtin": True, "file_id": None,
             "cover_template": v.get("cover", "C01"), "layouts": [], "aspect": "16:9", "created_at": None}
            for k, v in MASTERS.items()]


def public_master(rec: dict[str, Any]) -> dict[str, Any]:
    return {"master_id": rec["id"], "name": rec.get("name") or rec["id"], "description": rec.get("description") or "",
            "builtin": False, "file_id": rec.get("file_id"), "cover_template": rec.get("cover_template") or "C01",
            "layouts": rec.get("layouts") or [], "aspect": rec.get("aspect") or "", "created_at": rec.get("created_at"),
            "project_id": rec.get("project_id"), "warnings": rec.get("warnings") or []}


async def list_masters(project_id: str | None = None) -> list[dict[str, Any]]:
    where = {"project_id": project_id} if project_id else None
    items, _ = await asyncio.to_thread(store().list, "masters", where=where, limit=200)
    return builtin_masters() + [public_master(r) for r in items]


def _inspect_master(data: bytes) -> dict[str, Any]:
    prs = open_master(data)
    w, h = int(prs.slide_width), int(prs.slide_height)
    ratio = w / h if h else 0
    aspect = "16:9" if abs(ratio - 16 / 9) < 0.02 else ("4:3" if abs(ratio - 4 / 3) < 0.02 else f"{ratio:.2f}:1")
    warnings = [] if aspect == "16:9" else [f"16:9 가 아닌 마스터({aspect}) — 템플릿 좌표가 늘어나 보일 수 있어요"]
    return {"layouts": [lay.name for lay in prs.slide_layouts], "aspect": aspect, "slide_size": {"w_emu": w, "h_emu": h},
            "warnings": warnings}


async def register_master(file_id: str, name: str | None = None, project_id: str | None = None) -> dict[str, Any]:
    assets, _ = await fetch_assets({file_id}, strict={file_id})
    a = assets[file_id]
    try:
        info = await asyncio.to_thread(_inspect_master, a.data)
    except RenderError as exc:
        raise ApiError(400, "INVALID_MASTER", exc.message, {"file_id": file_id}) from exc
    except Exception as exc:  # noqa: BLE001
        raise ApiError(400, "INVALID_MASTER", "마스터 파일을 열 수 없습니다(.potx · .pptx)", {"file_id": file_id}) from exc
    base = re.sub(r"\.(potx|pptx)$", "", str(a.meta.get("name") or ""), flags=re.I)
    rec = await asyncio.to_thread(store().put, "masters", new_id("mst"), {
        "name": name or base or "고객사 템플릿", "description": "올린 마스터", "file_id": file_id, "project_id": project_id,
        "owner": current_user().id, **info})
    return public_master(rec)


# ── 렌더(슬라이드 PNG) ─────────────────────────────────────

def public_render(rec: dict[str, Any]) -> dict[str, Any]:
    return {"render_id": rec["id"], "status": rec.get("status"), "job_id": rec.get("job_id"), "pages": rec.get("pages") or [],
            "source_file_id": rec.get("source_file_id"), "error": rec.get("error"), "warnings": rec.get("warnings") or [],
            "created_at": rec.get("created_at"), "updated_at": rec.get("updated_at")}


async def prepare_render(body: dict[str, Any]) -> dict[str, Any]:
    """렌더 요청 검증 → 기록에 넣을 dict. PDF 는 바로 그림으로, PPTX · 문서는 LibreOffice 가 필요."""
    fid = body.get("file_id")
    doc_plan: dict[str, Any] | None = None
    source_kind = "file"
    if fid:
        try:
            meta = await platform.file_meta(fid)
        except ApiError as exc:
            if exc.status == 404:
                raise ApiError(404, "FILE_NOT_FOUND", f"파일을 찾을 수 없습니다: {fid}", {"file_id": fid}) from exc
            raise
        is_pdf = (meta.get("mime") == "application/pdf") or str(meta.get("name") or "").lower().endswith(".pdf")
        if not is_pdf and not soffice.available():
            raise converter_unavailable("슬라이드 그림 만들기")
        source_kind = "pdf" if is_pdf else "office"
    elif body.get("document") is not None or body.get("document_file_id"):
        if not soffice.available():
            raise converter_unavailable("슬라이드 그림 만들기")
        plan = await prepare({**body, "format": "pptx"})
        doc_plan = asdict(plan)
        source_kind = "document"
    else:
        raise bad("VALIDATION_FAILED", "file_id · document · document_file_id 중 하나가 필요합니다")
    width = max(320, min(2560, int(body.get("width") or 1280)))
    max_slides = body.get("max_slides")
    return {"status": "queued", "source_kind": source_kind, "source_file_id": fid, "plan": doc_plan, "width": width,
            "max_slides": int(max_slides) if max_slides else None, "sheet_ids": list(body.get("sheet_ids") or []),
            "project_id": body.get("project_id"), "confidential": bool(body.get("confidential", False)), "owner": current_user().id}


async def execute_render(render_id: str, rec: dict[str, Any], progress: Any = None) -> dict[str, Any]:
    async def step(pct: int, msg: str) -> None:
        if progress is not None:
            await progress(pct, msg)

    warnings: list[str] = []
    sheet_ids: list[str] = []
    width = int(rec.get("width") or 1280)
    max_slides = rec.get("max_slides")
    await step(5, "자료 받는 중")
    if rec.get("source_kind") in ("pdf", "office"):
        fid = rec["source_file_id"]
        assets, _ = await fetch_assets({fid}, strict={fid})
        a = assets[fid]
        if rec["source_kind"] == "pdf":
            pngs = await asyncio.to_thread(soffice.pdf_to_pngs, a.data, max_pages=max_slides, width=width)
        else:
            ext = _ext_of(str(a.meta.get("name") or ""), a.mime)
            pdf = await asyncio.to_thread(soffice.convert, a.data, ext, "pdf")
            pngs = await asyncio.to_thread(soffice.pdf_to_pngs, pdf, max_pages=max_slides, width=width)
    else:
        plan = Plan(**rec["plan"])
        sheet_ids = [str((s or {}).get("sheet_id") or (s or {}).get("id") or "") for s in (plan.document or {}).get("slides") or []]
        if (plan.document or {}).get("cover"):
            sheet_ids = ["cover"] + sheet_ids
        assets, warnings = await fetch_assets(referenced_files(plan))
        await resolve_master(plan, assets)
        await step(30, "슬라이드 만드는 중")
        lang = plan.language if plan.language != "both" else "ko"
        res = BuildResult()
        pptx = await asyncio.to_thread(_deck, plan, lang, assets, res)
        warnings += res.warnings
        await step(55, "그림으로 바꾸는 중")
        pdf = await asyncio.to_thread(soffice.convert, pptx, "pptx", "pdf")
        _font_note(warnings)
        pngs = await asyncio.to_thread(soffice.pdf_to_pngs, pdf, max_pages=max_slides, width=width)
    wanted = list(rec.get("sheet_ids") or [])
    await step(85, "저장하는 중")
    pages = []
    for i, png in enumerate(pngs):
        sid = sheet_ids[i] if i < len(sheet_ids) and sheet_ids[i] else None
        if wanted and sid not in wanted:
            continue
        fm = await platform.save_file(f"slide_{i + 1:03d}.png", png, "image/png", source="export",
                                      confidential=bool(rec.get("confidential")), project_id=rec.get("project_id"),
                                      meta={"render_id": render_id, "index": i, **({"sheet_id": sid} if sid else {})})
        pages.append({"index": i, "sheet_id": sid, "file_id": fm["id"], "png_file_id": fm["id"],
                      "url": fm.get("url") or f"/api/files/v1/files/{fm['id']}/content"})
    await step(100, "완료")
    return {"pages": pages, "warnings": warnings[:100]}


__all__ = ["Plan", "prepare", "is_slow", "execute", "store", "public_record", "plan_record", "plan_from_record",
           "to_api_error", "converter_unavailable", "now_iso", "fetch_assets", "MIME", "safe_filename"]
