"""§6.8 디자인 템플릿(PR6) · PPTX 생성(PR7) · 미리보기 레일(PR7P) · 렌더."""
from __future__ import annotations

import io
import re
from typing import Any

from winmate_common.platform import file_bytes

from .. import clients, config, core, defs, repo
from .. import models as M
from ..errors import not_found, unprocessable
from ..graphs import common as G
from ..graphs.generate import empty_sections, result_message

HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
INTRO = ("디자인 템플릿을 골라주세요. 사내 표준 템플릿은 업종별 변형이 있고, 고객사 로고와 컬러를 넣으면 표지·섹션 슬라이드에 자동 반영됩니다. "
         "템플릿은 PPTX 마스터 슬라이드로 적용되어 생성 후에도 PowerPoint에서 편집할 수 있습니다.")
RETAIL_INDUSTRIES = ("FB", "RT", "CV", "FS", "HM", "BT")


async def _masters(p: dict[str, Any]) -> list[dict[str, Any]]:
    items = await clients.export_masters(p.get("project_id"))
    if not items:
        items = [{"master_id": m["id"], "name": m["name"], "description": m["desc"], "builtin": True} for m in defs.MASTERS]
    return items


async def design_view(pid: str) -> M.DesignView:
    p = await core.load(pid)
    d = {**core.default_design(), **(p.get("design") or {})}
    ind = (p.get("customer") or {}).get("industry_code") or ((p.get("industry_layout") or {}).get("industry_code"))
    masters = []
    for m in await _masters(p):
        mid = m.get("master_id") or m.get("id")
        masters.append(M.MasterOut(id=mid, name=m.get("name") or mid, desc=m.get("description") or m.get("desc") or "",
                                   preview_url=f"/api/export/v1/templates/{m.get('cover_template') or 'C01'}/thumbnail.png",
                                   recommended=(mid == "retail_fnb" and ind in RETAIL_INDUSTRIES), builtin=bool(m.get("builtin", True)),
                                   selected=(mid == d.get("master_id"))))
    stats = await clients.export_stats()
    shs = await core.sheets_of(pid)
    keys = core.type_sections(p.get("type"))
    secs = {s["key"]: s for s in await core.sections_of(pid)}
    shs = [s for s in shs if s["section_key"] in keys and secs.get(s["section_key"], {}).get("enabled", True)]
    pinned = [M.PinnedSheet(sheet_no=int(s.get("sheet_no") or 0), code=(s.get("template") or {}).get("code") or "")
              for s in shs if (s.get("template") or {}).get("mode") == "pinned" and (s.get("template") or {}).get("code")]
    total = int(stats.get("ready") or stats.get("total") or 0)
    ind_n = int(stats.get("industry") or 0)
    ded_n = int(stats.get("dedicated") or 0)
    label = f"미리 만든 템플릿 {total}종 (업종별 {ind_n} · 솔루션 전용 {ded_n}) · 시트 {len(shs)}장 중 직접 고른 {len(pinned)}장"
    if pinned:
        label += f" ({' · '.join(x.code for x in pinned)})"
    label += " · 나머지 자동 추천"
    empties = await empty_sections(pid)
    empty_sheets = sum(1 for s in shs if not s.get("draft"))
    pre = M.PreGenerate(empty_sections=[M.RouteRef(label=defs.SECTIONS[k]["name"], route=core.section_route(pid, k)) for k in empties],
                        empty_sheet_count=empty_sheets,
                        notice=f"자료 없는 시트 {empty_sheets}장 · 딸깍으로 채우기" if empty_sheets else None)
    gen = p.get("generate") or {}
    gj = gen.get("job_id") if gen.get("status") in ("running", "queued") else None
    return M.DesignView(intro=INTRO, masters=masters, design=M.Design(**d), sheet_templates=M.SheetTemplatesSummary(
        catalog_total=total, industry=ind_n, dedicated=ded_n, sheets_total=len(shs), pinned=pinned, label=label), pre_generate=pre,
        generate_job_id=gj)


async def get_design(pid: str) -> M.DesignView:
    p = await core.load(pid)
    if core.STAGE_RANK.get(p.get("stage") or "customer", 0) < core.STAGE_RANK["design"] and p.get("type"):
        await core.mutate(pid, lambda x: core.advance_stage(x, "design"), bump=False)
        await core.index(pid)
    return await design_view(pid)


async def put_design(pid: str, body: M.DesignPatch) -> M.DesignView:
    p = await core.load(pid)
    patch = body.model_dump(exclude_unset=True)
    if "brand_hex" in patch and patch["brand_hex"] not in (None, "") and not HEX_RE.match(patch["brand_hex"]):
        raise unprocessable("INVALID_HEX", "#RRGGBB 형식으로 넣어 주세요", brand_hex=patch["brand_hex"])
    masters = {m.get("master_id") or m.get("id"): m for m in await _masters(p)}
    if patch.get("master_id") and patch["master_id"] not in masters:
        raise not_found("디자인 템플릿", patch["master_id"], "MASTER_NOT_FOUND")
    if patch.get("logo_file_id"):
        await _check_logo(patch["logo_file_id"])
    manual_changed = "layout_mode" in patch and patch["layout_mode"] != ((p.get("design") or {}).get("layout_mode") or "auto")

    def fn(x: dict[str, Any]) -> None:
        d = {**core.default_design(), **(x.get("design") or {})}
        for k, v in patch.items():
            if k == "cover" and isinstance(v, dict):
                cov = dict(d.get("cover") or {})
                cov.update({kk: vv for kk, vv in v.items() if vv is not None or kk == "image_ref"})
                d["cover"] = cov
            elif k == "master_id" and v:
                d["master_id"] = v
                d["master_name"] = masters[v].get("name") or v
                if masters[v].get("file_id"):
                    d["master_file_id"] = masters[v]["file_id"]
                else:
                    d.pop("master_file_id", None)
            elif v is not None or k in ("brand_hex", "logo_file_id"):
                d[k] = v
        d["chosen"] = True
        x["design"] = d
        core.advance_stage(x, "design")
    await core.mutate(pid, fn)
    if manual_changed:
        locked = patch["layout_mode"] == "manual"
        for s in await core.sheets_of(pid):
            await repo.amutate("sheets", s["id"], lambda y, locked=locked: y.update({"template": {**(y.get("template") or {}), "locked_manual": locked}}))
    if patch.get("logo_file_id"):
        await _apply_logo_colors(pid, patch["logo_file_id"])
    await core.index(pid)
    return await design_view(pid)


async def _check_logo(file_id: str) -> dict[str, Any]:
    meta = await clients.file_meta(file_id)
    if not meta:
        raise not_found("파일", file_id, "FILE_NOT_FOUND")
    mime = (meta.get("mime") or "").lower()
    name = (meta.get("name") or "").lower()
    if not (mime in ("image/png", "image/svg+xml") or name.endswith((".png", ".svg"))):
        raise unprocessable("UNSUPPORTED_FILE_TYPE", "로고는 PNG · SVG만 올릴 수 있어요")
    if int(meta.get("size") or 0) > 10 * 1024 * 1024:
        raise unprocessable("FILE_TOO_LARGE", "로고는 10MB까지 올릴 수 있어요")
    return meta


def dominant_colors(data: bytes, k: int = 2) -> list[str]:
    """PNG 대표색 1–2개(흰 · 검 · 투명 제외, 많이 쓴 순)."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        im.thumbnail((96, 96))
        counts: dict[tuple[int, int, int], int] = {}
        for r, g, b, a in im.getdata():
            if a < 128:
                continue
            if max(r, g, b) > 235 and min(r, g, b) > 220:
                continue
            if max(r, g, b) < 25:
                continue
            key = (r // 16 * 16, g // 16 * 16, b // 16 * 16)
            counts[key] = counts.get(key, 0) + 1
        out = []
        for (r, g, b), _n in sorted(counts.items(), key=lambda kv: -kv[1]):
            hx = f"#{r:02X}{g:02X}{b:02X}"
            if all(abs(int(hx[1:3], 16) - int(o[1:3], 16)) + abs(int(hx[3:5], 16) - int(o[3:5], 16)) + abs(int(hx[5:7], 16) - int(o[5:7], 16)) > 60
                   for o in out):
                out.append(hx)
            if len(out) >= k:
                break
        return out
    except Exception:  # noqa: BLE001
        return []


async def _apply_logo_colors(pid: str, file_id: str) -> None:
    try:
        data, mime = await file_bytes(file_id)
    except Exception:  # noqa: BLE001
        return
    cols = dominant_colors(data) if "svg" not in (mime or "") else []
    cands = [*cols, defs.BRAND_BLUE, defs.BRAND_DARK]
    cands = list(dict.fromkeys(c.upper() for c in cands))[:3]

    def fn(x: dict[str, Any]) -> None:
        d = {**core.default_design(), **(x.get("design") or {})}
        d["color_candidates"] = cands
        if cols and not d.get("brand_hex"):
            d["brand_hex"] = cols[0]
        x["design"] = d
    await core.mutate(pid, fn)


async def put_logo(pid: str, body: M.LogoIn) -> M.DesignView:
    await core.load(pid)
    await _check_logo(body.file_id)
    await core.mutate(pid, lambda x: x.update({"design": {**core.default_design(), **(x.get("design") or {}), "logo_file_id": body.file_id}}))
    await _apply_logo_colors(pid, body.file_id)
    return await design_view(pid)


async def start_generate(pid: str, *, scope: str = "all", section_key: str | None = None, infer_empty: bool = True, origin: str = "generate",
                         desc: str | None = None) -> M.JobAccepted:
    p = await core.load(pid)
    if not p.get("type"):
        from ..errors import type_required
        raise type_required()
    if scope == "section":
        if not section_key or section_key not in core.type_sections(p.get("type")):
            from ..errors import section_not_in_type
            raise section_not_in_type(section_key or "")
    gen = p.get("generate") or {}
    if gen.get("status") in ("running", "queued") and await G.running(gen.get("job_id")):
        return M.JobAccepted(job_id=gen["job_id"], status="running", kind="proposal.generate", proposal_id=pid, section_key=gen.get("section_key"))
    job_id = await G.enqueue("proposal.generate", {"proposal_id": pid, "scope": scope, "section_key": section_key, "infer_empty": infer_empty,
                                                   "origin": origin, "desc": desc},
                             title=("PPTX 생성" if scope == "all" else f"{defs.SECTIONS.get(section_key or '', {}).get('name', '')} 섹션 재생성"),
                             ref=pid, project_id=p.get("project_id"))

    def fn(x: dict[str, Any]) -> None:
        g = dict(x.get("generate") or {})
        g.update({"status": "running", "job_id": job_id, "scope": scope, "section_key": section_key, "error": None, "started_iso": config.now_iso()})
        x["generate"] = g
        core.set_job(x, "generate", job_id)
        core.advance_stage(x, "result")
        x["stage"] = "result" if core.STAGE_RANK.get(x.get("stage") or "customer", 0) >= core.STAGE_RANK["design"] else x.get("stage")
    await core.mutate(pid, fn)
    await core.index(pid)
    return M.JobAccepted(job_id=job_id, kind="proposal.generate", proposal_id=pid, section_key=section_key)


async def generate(pid: str, body: M.GenerateIn) -> M.JobAccepted:
    return await start_generate(pid, scope=body.scope, section_key=body.section_key, infer_empty=body.infer_empty)


def _file_url(fid: str | None, download: bool = False) -> str | None:
    return f"/api/files/v1/files/{fid}/content" + ("?download=true" if download else "") if fid else None


async def get_result(pid: str) -> M.ResultView:
    p = await core.load(pid)
    gen = p.get("generate") or {}
    st = gen.get("status")
    df = p.get("derived_from") or {}
    derived = bool(df.get("reuse_id"))
    if st in ("running", "queued"):
        if not await G.running(gen.get("job_id")):
            st = "failed" if not gen.get("version") else "done"
        else:
            return M.ResultView(status="running", job_id=gen.get("job_id"), message="PPTX 만드는 중", footer_label="PPTX 생성 · 6 / 6 · 진행 중",
                                derived=derived)
    if st in ("failed", "canceled") and not int(p.get("saved_version") or 0):
        return M.ResultView(status="failed", job_id=gen.get("job_id"), error=gen.get("error"), message=(gen.get("error") or {}).get("message") or "PPTX를 만들지 못했어요",
                            footer_label="PPTX 생성 · 6 / 6 · 실패", derived=derived)
    v = int(p.get("saved_version") or 0)
    if not v:
        return M.ResultView(status="none", derived=derived, footer_label="PPTX 생성 · 6 / 6")
    from .. import versions as VER
    ver = await VER.get_version(pid, v) or {}
    gv = gen if gen.get("version") else {}
    smap = ver.get("slide_map") or gv.get("slide_map") or []
    slides = int(ver.get("slides") or gv.get("slides") or len(smap))
    notes_count = int(ver.get("notes_count") or gv.get("notes_count") or 0)
    secs_used = [k for k in core.type_sections(p.get("type")) if any(m.get("section_key") == k and m.get("kind") == "sheet" for m in smap)]
    sheets_n = sum(1 for m in smap if m.get("kind") == "sheet")
    created = ver.get("created_iso")
    open_by = await core.open_confirm_by_sheet(pid)
    shs = {s["id"]: s for s in await core.sheets_of(pid)}
    thumbs = []
    for m in smap[:10]:
        sh = shs.get(m.get("sheet_id") or "")
        if m.get("kind") == "cover":
            url = core.thumb_url("C01" if (p.get("design") or {}).get("cover", {}).get("image_ref") else "C03")
        elif m.get("kind") == "toc":
            url = core.thumb_url("C04")
        elif m.get("kind") == "divider":
            url = core.thumb_url("C05")
        else:
            url = core.sheet_thumb(sh) if sh else None
        label = m.get("label") or ""
        if m.get("kind") == "sheet" and sh:
            label = f"{defs.SECTIONS.get(sh['section_key'], {}).get('short', '')} · {sh.get('title') or ''}"
        thumbs.append(M.SlideThumb(slide_no=int(m["slide_no"]), label=f"{int(m['slide_no']):02d} {label}", thumb_url=url,
                                   inferred=bool(sh.get("inferred")) if sh else False, sheet_id=m.get("sheet_id"), kind=m.get("kind") or "sheet"))
    ranges = []
    last_shown = smap[min(9, len(smap) - 1)]["slide_no"] if smap else 0
    for k in secs_used:
        nums = [int(m["slide_no"]) for m in smap if m.get("section_key") == k]
        if not nums or max(nums) <= last_shown:
            continue
        lo = max(min(nums), last_shown + 1)
        flag = None
        if any(open_by.get(m.get("sheet_id") or "", 0) for m in smap if m.get("section_key") == k):
            flag = "[수치 확정 필요]"
        ranges.append(M.SlideRange(**{"from": lo, "to": max(nums), "label": defs.SECTIONS[k]["name"], "flag": flag}))
    rl = " · ".join(f"{r.from_}–{r.to} {r.label}" + (f" {r.flag}" if r.flag else "") if r.from_ != r.to else f"{r.from_} {r.label}" + (f" {r.flag}" if r.flag else "")
                    for r in ranges)
    # 「{{섹션}} 섹션만 재생성」: 열린 확인 항목이 가장 많은 섹션(동률이면 뒤)
    best, best_n = None, 0
    for k in secs_used:
        n = sum(open_by.get(s["id"], 0) for s in shs.values() if s["section_key"] == k)
        if n >= best_n and n > 0:
            best, best_n = k, n
    if best is None and secs_used:
        best = secs_used[-1]
    regen = M.RouteRef(label=f"{defs.SECTIONS[best]['short']} 섹션만 재생성", route=core.section_route(pid, best)) if best else None
    tl = core.type_name(p.get("type")) or ""
    fname = ver.get("file_name") or gv.get("file_name") or ""
    created_label = config.when_label(created) if created else "방금 생성"
    if created and (config.now() - (config.parse_iso(created) or config.now())).total_seconds() < 600:
        created_label = "방금 생성"
    pptx = ver.get("pptx_file_id") or (p.get("files") or {}).get("pptx_file_id")
    pdf = ver.get("pdf_file_id") or (p.get("files") or {}).get("pdf_file_id")
    file = M.ResultFile(name=fname, slides=slides, sheets=sheets_n, type_label=tl, sections=len(secs_used), notes_count=notes_count,
                        created_at=created, created_label=created_label, version=v, pptx_file_id=pptx, pdf_file_id=pdf,
                        pptx_url=_file_url(pptx, True), pdf_url=_file_url(pdf, True),
                        meta=f"{slides} 슬라이드 · {tl} {len(secs_used)}섹션 · {created_label} · 노트 {notes_count}건")
    return M.ResultView(status="done", job_id=gen.get("job_id"), file=file,
                        message=result_message(p, sections=len(secs_used), slides=slides, notes_count=notes_count), thumbs=thumbs,
                        ranges=ranges, ranges_label=rl, regen_section=regen, regen_section_key=best,
                        footer_label="PPTX 생성 · 6 / 6 · 완료", derived=derived,
                        summary_route=core.route(pid, "reuse", "summary") if derived else None)


async def get_slides(pid: str, filter_: str | None) -> M.SlidesView:
    p = await core.load(pid)
    keys = core.type_sections(p.get("type"))
    secs = {s["key"]: s for s in await core.sections_of(pid)}
    enabled = [k for k in keys if secs.get(k, {}).get("enabled", True)]
    shs = [s for s in await core.sheets_of(pid) if s["section_key"] in enabled]
    open_by = await core.open_confirm_by_sheet(pid)
    out = []
    for i, k in enumerate(enabled):
        rows = []
        for s in [x for x in shs if x["section_key"] == k]:
            edited = bool(s.get("edited_since_version"))
            confirm = open_by.get(s["id"], 0) > 0
            inferred = bool(s.get("inferred"))
            if filter_ == "inferred" and not inferred or filter_ == "edited" and not edited or filter_ == "confirm" and not confirm:
                continue
            flags = [x for x, on in (("수정됨", edited), ("확정 필요", confirm), ("추론", inferred)) if on]
            rows.append(M.RailSheet(sheet_no=int(s.get("sheet_no") or 0), sheet_id=s["id"], title=s.get("title") or "", thumb_url=core.sheet_thumb(s),
                                    edited=edited, confirm=confirm, inferred=inferred,
                                    aria_label=f"시트 {int(s.get('sheet_no') or 0):02d} {s.get('title') or ''}" + (f" · {' · '.join(flags)}" if flags else "")))
        if rows or not filter_:
            first_no = min([r.sheet_no for r in rows] or [0])
            out.append(M.RailSection(no=i + 1, key=k, name=defs.SECTIONS[k]["name"], label=f"{first_no:02d} {defs.SECTIONS[k]['name']}", sheets=rows))
    v = int(p.get("saved_version") or 0)
    e = int(p.get("edits_since_version") or 0)
    from .. import versions as VER
    ver = await VER.get_version(pid, v) if v else None
    n_sh = len(shs)
    total = core.slides_total(p, n_sh, len([k for k in enabled if any(s["section_key"] == k for s in shs)]))
    return M.SlidesView(version=v, edits_since_version=e, version_label=f"v{v} · 수정 {e}" if v else "초안", file_name=(ver or {}).get("file_name") or "",
                        sheets_total=n_sh, slides_total=total, toolbar_label=f"시트 {n_sh} + 표지 · 목차 · 자동 저장됨",
                        rail_label=f"표지 · 목차 포함 {n_sh + 2}장", open_confirm=sum(open_by.values()), sections=out, filter=filter_,
                        rev=int(p.get("rev") or 0))


async def create_render(pid: str, body: M.RenderIn) -> M.JobAccepted:
    p = await core.load(pid)
    if body.sheet_ids:
        for sid in body.sheet_ids:
            await core.sheet_doc(pid, sid)
    job_id = await G.enqueue("proposal.render", {"proposal_id": pid, "sheet_ids": body.sheet_ids}, title="시트 미리보기 렌더", ref=pid,
                             project_id=p.get("project_id"))
    return M.JobAccepted(job_id=job_id, kind="proposal.render", proposal_id=pid)
