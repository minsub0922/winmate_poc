"""렌더 문서(ProposalRenderDoc v1) 조립 — 표지 → 목차 → [섹션 간지] → 시트 → [부록] (§7.8 assemble · §7.12).

- 칸 값은 content.export_slots 로(값 토큰을 풀고, 이미지는 files id 로).
- 열린 확인 항목은 발표자 노트에 「[수치 확정 필요] …」로 남긴다(PR7 「노트 {{k}}건」).
- kb 이미지는 처음 쓸 때 files 에 올리고 그 id 를 assets 컬렉션에 기억한다.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from winmate_common.platform import save_file

from . import clients, config, content as C, core, defs, facts as F, repo
from .graphs import common as G

log = logging.getLogger("winmate.proposal.render_doc")

SUFFIXES = ("프랜차이즈", "주식회사", "(주)", "㈜", "그룹", "코리아")
PROJECT_DROP = ("전국", "매장", "전환", "도입", "구축", "사업", "프로젝트", "제안", "제안서")


def customer_short(p: dict[str, Any]) -> str:
    name = (p.get("customer") or {}).get("name") or ""
    for s in SUFFIXES:
        name = name.replace(s, "")
    return re.sub(r"\s+", "", name).strip() or "고객"


def project_short(p: dict[str, Any]) -> str:
    words = [w for w in re.split(r"\s+", (p.get("title") or "").strip()) if w and w not in PROJECT_DROP]
    return "".join(words)[:20] or "제안"


def file_base(p: dict[str, Any], version: int) -> str:
    return f"{customer_short(p)}_{project_short(p)}_제안서_v{version}"


def export_code(code: str | None, body: dict[str, Any]) -> str | None:
    """VP-B · VP-F 는 카탈로그에 기둥 수별(2 · 3 · 4)로 있다."""
    if code in ("VP-B", "VP-F"):
        n = len(body.get("points") or []) or 3
        return f"{code}{max(2, min(4, n))}"
    return code


async def kb_image_file(image_id: str, *, project_id: str | None, confidential: bool) -> str | None:
    """kb 이미지 → files(한 번만). 실패하면 None(칸은 비우고 경고)."""
    key = f"kbimg:{image_id}"
    a = await repo.aget("assets", key)
    if a and a.get("file_id"):
        return a["file_id"]
    try:
        data, mime = await clients.client("kb", "GET", f"/v1/images/{image_id}/file").get_bytes(f"/v1/images/{image_id}/file")
    except Exception as exc:  # noqa: BLE001
        log.warning("kb 이미지 %s 못 가져옴: %s", image_id, exc)
        return None
    if not data:
        return None
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get((mime or "").split(";")[0], "jpg")
    try:
        meta = await save_file(f"{image_id}.{ext}", data, (mime or "image/jpeg").split(";")[0], source="derived", confidential=False,
                               project_id=project_id, meta={"kb_image_id": image_id, "rights": "official"})
    except Exception as exc:  # noqa: BLE001
        log.warning("kb 이미지 저장 실패 %s: %s", image_id, exc)
        return None
    await repo.aput("assets", key, {"id": key, "kind": "kb_image", "ref": image_id, "file_id": meta["id"], "created_iso": config.now_iso()})
    return meta["id"]


async def image_files_for(contents: list[dict[str, Any]], *, project_id: str | None, confidential: bool,
                          extra: list[dict[str, Any]] | None = None) -> dict[str, str]:
    """칸 안 이미지 참조(id) → files id."""
    out: dict[str, str] = {}
    refs: list[dict[str, Any]] = list(extra or [])

    def walk(v: Any) -> None:
        if isinstance(v, dict):
            if v.get("kind") in ("kb_image", "image_job", "file") or ("rights" in v and v.get("id")):
                refs.append(v)
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    for c in contents:
        walk(c.get("slots") or {})
    for r in refs:
        rid = r.get("id")
        if not rid or rid in out:
            continue
        if r.get("file_id"):
            out[rid] = r["file_id"]
        elif r.get("kind") == "kb_image" or str(rid).startswith("img_"):
            fid = await kb_image_file(rid, project_id=project_id, confidential=confidential)
            if fid:
                out[rid] = fid
        elif r.get("kind") == "image_job":
            fid = await image_job_file(rid)
            if fid:
                out[rid] = fid
    return out


async def image_job_file(version_id: str) -> str | None:
    """이미지 생성 기능의 버전 → 렌디션 file id."""
    res = await clients.call("image", "GET", f"/v1/versions/{version_id}", quiet=True)
    if not res:
        return None
    for key in ("fhd", "uhd", "original"):
        r = next((x for x in res.get("renditions") or [] if x.get("kind") == key or x.get("name") == key), None)
        if r and r.get("file_id"):
            return r["file_id"]
    return res.get("file_id")


def _confirm_lines(items: list[dict[str, Any]]) -> list[str]:
    from .ops.sections import item_text
    out = []
    for it in items:
        tag = it.get("tag") or "수치"
        label = "수치 확정 필요" if tag in ("수치", "값 불일치", "고객 확인", "수량 가정") else "확정 필요"
        out.append(f"[{label}] {item_text(it)}" + (f" — {it.get('sub')}" if it.get("sub") else ""))
    return out


async def build(pid: str, *, sheet_ids: list[str] | None = None, language: str = "ko", tbd_mode: str = "keep_marks",
                include_inferred_marks: bool = True, include_cover: bool = True, include_toc: bool = True,
                dividers: bool | None = None, for_export: bool = False, snapshot: dict[str, Any] | None = None,
                include_notes: bool = True, include_sources: bool = True, master_id: str | None = None) -> dict[str, Any]:
    """→ {document, design, slide_map, notes_count, sheet_count, template_codes}. snapshot 이 있으면 그 버전 내용으로."""
    p = await core.load(pid)
    if snapshot:
        p = {**p, **{k: v for k, v in (snapshot.get("proposal") or {}).items() if v is not None}}
    d = p.get("design") or {}
    keys = core.type_sections(p.get("type"))
    if snapshot:
        secs = {s["key"]: s for s in snapshot.get("sections") or [] if not s.get("hidden")}
        all_sheets = sorted([s for s in snapshot.get("sheets") or [] if s.get("status") != "excluded" and not s.get("hidden")],
                            key=lambda s: (s.get("sheet_no") or 9999, s.get("order") or 0))
        facts_all = {f["id"]: f for f in snapshot.get("facts") or []}
        raw_items = snapshot.get("confirm_items") or []
    else:
        secs = {s["key"]: s for s in await core.sections_of(pid)}
        all_sheets = await core.sheets_of(pid)
        facts_all = await F.facts_of(pid)
        raw_items = await repo.alist("confirm_items", {"proposal_id": pid})
    enabled = [k for k in keys if secs.get(k, {}).get("enabled", True)]
    sheets = [s for s in all_sheets if s["section_key"] in enabled and (not sheet_ids or s["id"] in sheet_ids)]
    items = [it for it in raw_items if it.get("status") in ("open", "moved_to_note") and (it.get("category") or "fact") == "fact"]
    conf = config.customer_text_confidential()
    img_map = await image_files_for([s.get("content") or {} for s in sheets], project_id=p.get("project_id"), confidential=conf)
    cover_file = None
    cov = d.get("cover") or {}
    if cov.get("enabled", True) and cov.get("image_ref"):
        ref = cov["image_ref"]
        cover_file = ref.get("file_id") or (await image_files_for([], project_id=p.get("project_id"), confidential=conf, extra=[ref])).get(ref.get("id"))
    slides: list[dict[str, Any]] = []
    slide_map: list[dict[str, Any]] = []
    n = 0
    if include_cover:
        n += 1
        slide_map.append({"slide_no": n, "kind": "cover", "label": "표지"})
    if include_toc:
        toc_items = []
        for i, k in enumerate(enabled):
            shs = [s for s in sheets if s["section_key"] == k]
            if not shs:
                continue
            toc_items.append({"no": f"{i + 1:02d}", "title": defs.SECTIONS[k]["name"], "body": " · ".join(s.get("title") or "" for s in shs[:4])})
        slides.append({"kind": "toc", "template_code": "C04", "slots": {"title": "목차" if language != "en" else "Contents", "items": toc_items[:8]}})
        n += 1
        slide_map.append({"slide_no": n, "kind": "toc", "label": "목차"})
    use_div = d.get("section_dividers", True) if dividers is None else dividers
    notes_count = 0
    codes: list[str] = []
    for i, k in enumerate(enabled):
        shs = [s for s in sheets if s["section_key"] == k]
        if not shs:
            continue
        if use_div:
            slides.append({"kind": "divider", "template_code": "C05",
                           "slots": {"no": f"{i + 1:02d}", "title": defs.SECTIONS[k]["name"],
                                     "subtitle": f"시트 {len(shs)}장", "sheets": [s.get("title") or "" for s in shs[:6]]}})
            n += 1
            slide_map.append({"slide_no": n, "kind": "divider", "label": defs.SECTIONS[k]["short"], "section_key": k})
        for s in shs:
            content = s.get("content") or {}
            slots, to_notes = C.export_slots(content, facts_all, image_files=img_map, tbd_mode=tbd_mode)
            if not slots.get("title"):
                slots["title"] = s.get("title") or ""
            sitems = [it for it in items if it.get("sheet_id") == s["id"] or s["id"] in (it.get("linked_sheet_ids") or [])]
            note_parts = []
            base_note = C.resolve_text(content.get("notes") or "", facts_all) if include_notes else ""
            if base_note:
                note_parts.append(base_note)
            lines = _confirm_lines(sitems)
            if lines:
                note_parts += lines
                notes_count += len(lines)
            note_parts += to_notes
            if include_inferred_marks and s.get("inferred") and s.get("evidence_note"):
                note_parts.append(f"(W 추론) {s['evidence_note']}")
            sources = [{"label": x.get("label"), **({"url": x["url"]} if x.get("url") else {})} for x in s.get("sources") or []
                       if x.get("label") and x.get("kind") != "link"][:3]
            code = export_code((s.get("template") or {}).get("code"), s.get("draft") or {})
            if code:
                codes.append(code)
            slide = {"kind": "sheet", "template_code": code, "slots": slots, "notes": "\n".join(note_parts), "sheet_id": s["id"]}
            if not include_sources:
                slide["slots"].pop("sources", None)
                sources = []
            if sources:
                slide["sources"] = sources
            slides.append(slide)
            n += 1
            slide_map.append({"slide_no": n, "kind": "sheet", "sheet_id": s["id"], "sheet_no": int(s.get("sheet_no") or 0), "section_key": k,
                              "label": f"{defs.SECTIONS[k]['short']} · {s.get('title') or ''}", "inferred": bool(s.get("inferred"))})
    cust = (p.get("customer") or {}).get("name") or ""
    today = config.today_kst()
    document: dict[str, Any] = {
        "title": core.title_display(p), "footer": " · ".join(x for x in (cust, core.title_display(p)) if x), "lang": language,
        "slides": slides,
    }
    if include_cover:
        # 허브 Storyboard 에서 시작했으면 Key message 가 표지 부제(없으면 유형 이름)
        km = (((p.get("hub") or {}).get("key_message")) or {}).get("text")
        document["cover"] = {"title": core.title_display(p), "subtitle": km or core.type_name(p.get("type")) or "", "customer": cust,
                             "date": f"{today.year}.{today.month:02d}.{today.day:02d}", "presenter": p.get("owner_name") or "",
                             **({"image": cover_file} if cover_file else {})}
    design = {"brand_hex": d.get("brand_hex") or defs.BRAND_BLUE, "master_id": master_id or d.get("master_id") or defs.DEFAULT_MASTER,
              "page_numbers": bool(d.get("page_numbers", True))}
    if d.get("logo_file_id"):
        design["logo_file_id"] = d["logo_file_id"]
    if cover_file:
        design["cover_image_file_id"] = cover_file
    if d.get("master_file_id"):
        design["master_file_id"] = d["master_file_id"]
    return {"document": document, "design": design, "slide_map": slide_map, "notes_count": notes_count, "sheet_count": len(sheets),
            "template_codes": codes, "slides_total": n}


async def export_pptx(pid: str, built: dict[str, Any], *, filename: str, language: str = "ko", tbd_mode: str = "keep_marks",
                      fmt: str = "pptx", bilingual: str | None = None) -> dict[str, Any]:
    """export `POST /v1/exports` → 끝날 때까지(202 면 기다림). → ExportResult/Record dict. 실패는 ApiError."""
    from winmate_common.errors import ApiError
    p = await core.load(pid)
    body: dict[str, Any] = {"format": fmt, "filename": filename, "document": built["document"], "design": built["design"],
                            "language": language, "tbd_mode": tbd_mode, "confidential": config.customer_text_confidential(),
                            "project_id": p.get("project_id"), "source_ref": f"proposal:{pid}"}
    if bilingual:
        body["bilingual"] = bilingual
    res = await clients.call("export", "POST", "/v1/exports", json=body, timeout=180, raise_errors=True)
    if not res:
        raise ApiError(502, "UPSTREAM_UNAVAILABLE", "PPTX를 만들지 못했어요. 잠시 뒤 다시 시도해 주세요", {"service": "export"})
    if res.get("file"):
        return res
    xid = res.get("export_id")
    waited = 0.0
    import asyncio
    while waited < config.export_wait_s():
        await asyncio.sleep(0.5)
        waited += 0.5
        await G.check_cancel()
        rec = await clients.call("export", "GET", f"/v1/exports/{xid}", quiet=True)
        if rec and rec.get("status") == "done":
            return rec
        if rec and rec.get("status") == "failed":
            err = rec.get("error") or {}
            raise ApiError(502, err.get("code") or "EXPORT_FAILED", err.get("message") or "PPTX를 만들지 못했어요")
    raise ApiError(504, "TIMEOUT", "PPTX 만들기가 오래 걸려요. 잠시 뒤 결과를 다시 확인해 주세요", {"export_id": xid})
