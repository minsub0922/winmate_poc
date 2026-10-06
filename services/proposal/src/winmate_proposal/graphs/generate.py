"""generate · render(§7.8) — 빈 섹션 추론 → 조립 → 넘침 맞춤 → PPTX(export) → 새 버전 → 색인.

render(proposal.render)는 시트 PNG 만(export `POST /renders`) — LibreOffice 가 없으면 export 가 501 이고, 그때는 템플릿 썸네일을 쓴다.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.jobs import JobContext

from .. import clients, config, content as C, core, defs, facts as F, prompts, render_doc as R, repo, versions as VER
from . import common as G
from . import section_fill as SF

log = logging.getLogger("winmate.proposal.generate")

LABELS = {"ensure_filled": "빈 섹션 채우기", "assemble": "조립", "fit": "넘침 맞춤", "render": "PPTX 렌더", "store": "버전 저장"}
PROGRESS = {"ensure_filled": 35, "assemble": 50, "fit": 60, "render": 90, "store": 100}


async def empty_sections(pid: str) -> list[str]:
    p = await core.load(pid)
    keys = core.type_sections(p.get("type"))
    secs = {s["key"]: s for s in await core.sections_of(pid)}
    out = []
    for k in keys:
        s = secs.get(k)
        if not s or not s.get("enabled", True):
            continue
        shs = await core.sheets_of(pid, section_key=k)
        if shs and not any(x.get("draft") for x in shs):
            out.append(k)
    return out


async def review_item(pid: str, key: str, text: str, *, origin: str) -> None:
    shs = await core.sheets_of(pid, section_key=key)
    await F.add_item(pid, sheet=shs[0] if shs else None, tag="검토 필요", category="review", origin=origin,
                     text={"pre": defs.SECTIONS[key]["name"], "mark": "", "post": ""}, sub=text,
                     action={"kind": "button", "label": "섹션 열기", "target": {"route": core.section_route(pid, key)}})


async def fill_empty(pid: str, *, origin: str, memos: list[str], job: str | None) -> list[str]:
    done = []
    for key in await empty_sections(pid):
        await G.check_cancel()
        try:
            await SF.fill(pid, key, mode="infer", origin=origin, job=job, memos=memos)
            await review_item(pid, key, "자료 없이 추론으로 채웠어요 — 내용과 수치를 확인해 주세요", origin=origin)
            done.append(key)
        except ApiError as exc:
            if exc.code == "POLICY_CONFIDENTIAL":
                raise
            log.warning("빈 섹션 %s 추론 실패: %s", key, exc)
            await review_item(pid, key, "이 섹션은 자동으로 채우지 못했어요", origin=origin)
    return done


async def fit_overflow(pid: str, *, job: str | None) -> int:
    """칸 용량(max_chars)을 1.3배 넘는 글만 LLM 으로 줄인다(값 토큰 · 숫자 보존, AC-136). → 줄인 칸 수."""
    p = await core.load(pid)
    todo: list[dict[str, Any]] = []
    for s in await core.sheets_of(pid):
        code = (s.get("template") or {}).get("code")
        if not code or not s.get("content"):
            continue
        detail = await clients.export_template_detail(code, (s.get("template") or {}).get("product_count"))
        caps = {x["id"]: (x.get("capacity") or {}).get("max_chars") for x in ((detail or {}).get("slot_schema") or {}).get("slots") or []}
        c = s["content"]
        for k in ("title", "subtitle"):
            mx = caps.get(k)
            if mx and isinstance(c.get(k), str) and len(C.resolve_text(c[k], {})) > mx * 1.3:
                todo.append({"id": f"{s['id']}|{k}", "text": c[k], "max": mx})
    if not todo:
        return 0
    res = await G.llm_json("pr.shorten", system=prompts.RULES, user=prompts.shorten(items=todo[:20]), schema=prompts.SHORTEN,
                           confidential=G.customer_conf())
    n = 0
    want = {x["id"]: x for x in todo}
    for it in (res or {}).get("items") or []:
        src = want.get(str(it.get("id")))
        new = it.get("text") or ""
        if not src or not new:
            continue
        if sorted(C.tokens_in(src["text"])) != sorted(C.tokens_in(new)) or C.numbers_of(new) - C.numbers_of(src["text"]):
            continue   # 값 토큰 · 숫자가 바뀌면 쓰지 않는다
        sid, key = src["id"].split("|", 1)
        await repo.amutate("sheets", sid, lambda x, key=key, new=new: x.update({"content": {**(x.get("content") or {}), key: new},
                                                                                  "content_rev": int(x.get("content_rev") or 0) + 1}))
        n += 1
    return n


def result_message(p: dict[str, Any], *, sections: int, slides: int, notes_count: int) -> str:
    tname = core.type_name(p.get("type")) or "제안서"
    msg = (f"{tname} {sections}개 섹션, 표지·목차를 포함해 {slides}장으로 완성되었습니다. 섹션마다 구분 슬라이드가 들어가고, "
           f"섹션 단위로 다시 생성할 수 있습니다.")
    if notes_count:
        msg += " [수치 확정 필요]로 표시된 곳은 노트에 남겨두었습니다."
    return msg


async def gen_ensure(pid: str, *, scope: str, skey: str | None, infer_empty: bool, origin: str, job: str | None,
                     memos: list[str]) -> list[str]:
    filled: list[str] = []
    if scope == "section" and skey:
        await SF.fill(pid, skey, mode="draft", origin=origin, job=job, memos=memos)
        if skey in await empty_sections(pid) and infer_empty:
            filled = await fill_empty(pid, origin=origin, memos=memos, job=job)
    elif infer_empty:
        filled = await fill_empty(pid, origin=origin, memos=memos, job=job)
    return filled


async def gen_render(pid: str) -> dict[str, Any]:
    await F.sync_items(pid)
    built = await R.build(pid)
    p = await core.load(pid)
    n = int(p.get("saved_version") or 0) + 1
    res = await R.export_pptx(pid, built, filename=R.file_base(p, n))
    f = res.get("file") or {}
    return {"export": {"file_id": f.get("id"), "name": f.get("name"), "export_id": res.get("export_id"),
                       "slide_count": res.get("slide_count") or built["slides_total"], "warnings": res.get("warnings") or []},
            "built": {"slide_map": built["slide_map"], "notes_count": built["notes_count"], "sheet_count": built["sheet_count"],
                      "slides_total": built["slides_total"]}}


async def gen_store(pid: str, *, ex: dict[str, Any], built: dict[str, Any], scope: str, skey: str | None, origin: str, job: str | None,
                    desc: str | None = None) -> dict[str, Any]:
    p = await core.load(pid)
    n_sheets = built.get("sheet_count") or 0
    first = int(p.get("saved_version") or 0) == 0
    tname = core.type_name(p.get("type")) or "제안서"
    if first:
        d = f"{tname} {n_sheets}시트 처음 생성" + (" · 딸깍" if origin == "one_click" else "")
    elif scope == "section" and skey:
        d = f"{defs.SECTIONS.get(skey, {}).get('name', skey)} 섹션 재생성"
    else:
        d = desc or "PPTX 다시 생성"
    author: Any = "W" if (first or origin == "one_click") else core.actor()
    df = p.get("derived_from") or {}
    kind = "generated"
    if first and df.get("reuse_id"):
        # 기존 제안서에서 파생한 제안서의 첫 버전 — 버전 이력에 「… v4에서 파생」(PRU5 흔적)
        kind = "reuse_derived"
        d = f"{d} · {df.get('label') or '원본에서 파생'}"
    v = await VER.create(pid, kind=kind, desc=d, author=author, pptx_file_id=ex.get("file_id"),
                         derived_from=df if (first and df.get("reuse_id")) else None,
                         extra={"slide_map": built.get("slide_map"), "slides": ex.get("slide_count"), "notes_count": built.get("notes_count"),
                                "file_name": ex.get("name"), "export_id": ex.get("export_id")})
    secs_used = len({m.get("section_key") for m in built.get("slide_map") or [] if m.get("kind") == "sheet"})

    def fn(x: dict[str, Any]) -> None:
        x["generate"] = {"status": "done", "job_id": job, "version": v["n"], "slides": ex.get("slide_count"),
                         "slides_total": built.get("slides_total"), "notes_count": built.get("notes_count"), "file_name": ex.get("name"),
                         "pptx_file_id": ex.get("file_id"), "slide_map": built.get("slide_map"), "sections": secs_used,
                         "created_iso": config.now_iso(), "warnings": ex.get("warnings"), "scope": scope, "section_key": skey}
        core.advance_stage(x, "result")
        x["stage"] = "result"
        core.set_job(x, "generate", None)
    await core.mutate(pid, fn)
    await core.index(pid, force=True)
    p2 = await core.load(pid)
    return {"proposal_id": pid, "version": v["n"], "pptx_file_id": ex.get("file_id"), "slides": ex.get("slide_count"),
            "notes_count": built.get("notes_count"),
            "message": result_message(p2, sections=secs_used, slides=ex.get("slide_count") or 0, notes_count=built.get("notes_count") or 0)}


async def handle_generate(ctx: JobContext) -> dict[str, Any]:
    pl = ctx.payload
    pid = pl["proposal_id"]
    scope = pl.get("scope") or "all"
    skey = pl.get("section_key")
    origin = pl.get("origin") or "generate"

    async def ensure_filled(s: dict[str, Any]) -> dict[str, Any]:
        return {"inferred_sections": await gen_ensure(pid, scope=scope, skey=skey, infer_empty=pl.get("infer_empty", True), origin=origin,
                                                      job=ctx.job.id, memos=s.get("memos") or [])}

    async def assemble(_s: dict[str, Any]) -> dict[str, Any]:
        await F.sync_items(pid)
        return {}

    async def fit(_s: dict[str, Any]) -> dict[str, Any]:
        try:
            n = await fit_overflow(pid, job=ctx.job.id)
        except ApiError as exc:
            if exc.code == "POLICY_CONFIDENTIAL":
                raise
            n = 0
        return {"fitted": n}

    async def render(_s: dict[str, Any]) -> dict[str, Any]:
        return await gen_render(pid)

    async def store(s: dict[str, Any]) -> dict[str, Any]:
        return {"result": await gen_store(pid, ex=s.get("export") or {}, built=s.get("built") or {}, scope=scope, skey=skey, origin=origin,
                                          job=ctx.job.id, desc=pl.get("desc"))}

    try:
        final = await G.run(ctx, G.chain([("ensure_filled", ensure_filled), ("assemble", assemble), ("fit", fit), ("render", render),
                                          ("store", store)]), {"memos": []}, labels=LABELS, progress_map=PROGRESS)
    except BaseException as exc:
        err = {"code": getattr(exc, "code", None) or type(exc).__name__, "message": getattr(exc, "message", None) or str(exc)}

        def fail(x: dict[str, Any]) -> None:
            g = dict(x.get("generate") or {})
            if g.get("job_id") == ctx.job.id:
                g["status"] = "canceled" if type(exc).__name__ == "JobCanceled" else "failed"
                g["error"] = err
                x["generate"] = g
            core.set_job(x, "generate", None)
        try:
            await core.mutate(pid, fail, bump=False)
        except Exception:  # noqa: BLE001
            pass
        raise
    return (final or {}).get("result") or {}


# ── 시트 PNG 렌더(미리보기 캐시) ────────────────────────────
async def render_pngs(pid: str, sheet_ids: list[str] | None = None) -> dict[str, Any]:
    built = await R.build(pid, sheet_ids=sheet_ids, include_cover=False, include_toc=False, dividers=False)
    if not built["document"]["slides"]:
        return {"rendered": 0}
    p = await core.load(pid)
    res = await clients.call("export", "POST", "/v1/renders", json={"document": built["document"], "design": built["design"],
                                                                  "project_id": p.get("project_id"),
                                                                  "confidential": config.customer_text_confidential()}, quiet=True)
    if not res or not res.get("render_id"):
        return {"rendered": 0, "unavailable": True}
    rid = res["render_id"]
    waited = 0.0
    rec = None
    while waited < config.export_wait_s():
        await asyncio.sleep(0.5)
        waited += 0.5
        rec = await clients.call("export", "GET", f"/v1/renders/{rid}", quiet=True)
        if rec and rec.get("status") in ("done", "failed"):
            break
    if not rec or rec.get("status") != "done":
        return {"rendered": 0, "unavailable": True}
    n = 0
    for page in rec.get("pages") or []:
        sid = page.get("sheet_id")
        if not sid:
            continue
        await repo.amutate("sheets", sid, lambda x, page=page: x.update({"render": {"png_file_id": page.get("png_file_id"), "rev": x.get("content_rev"),
                                                                                    "status": "done"}}))
        n += 1
    return {"rendered": n}


async def handle_render(ctx: JobContext) -> dict[str, Any]:
    pl = ctx.payload

    async def node(_s: dict[str, Any]) -> dict[str, Any]:
        return {"result": {"proposal_id": pl["proposal_id"], **(await render_pngs(pl["proposal_id"], pl.get("sheet_ids")))}}
    final = await G.run(ctx, G.single("render", node), {}, labels={"render": "시트 렌더"}, progress_map={"render": 100})
    return (final or {}).get("result") or {}
