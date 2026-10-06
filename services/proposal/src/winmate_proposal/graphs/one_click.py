"""one_click — 딸깍(§7.7). 사람 확인 없음(선택 필요 → 추천값 + 검토 필요).

prepare(유형 · 구성 · 업종 추론) → sections(남은 섹션마다 infer) → design(기본 마스터) → generate(PPTX v1) → finalize(검토 항목 · 수치).
중지: 노드 · 섹션 경계에서 멈추고, 끝난 섹션은 「추론 완료」로 두고 누른 단계로 돌아간다(⚠Q7).
"""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.jobs import JobContext, jobs

from .. import config, core, defs, facts as F, industry, plan, repo
from . import common as G
from . import generate as GEN
from . import section_fill as SF

log = logging.getLogger("winmate.proposal.one_click")

LABELS = {"prepare": "유형 · 구성 · 업종", "sections": "섹션 추론", "design": "디자인 템플릿", "generate": "PPTX 조립", "finalize": "마무리"}


async def _set(pid: str, fn: Any) -> None:
    def wrap(x: dict[str, Any]) -> None:
        oc = dict(x.get("one_click") or {})
        fn(oc)
        x["one_click"] = oc
    await core.mutate(pid, wrap, bump=False)


async def _step(pid: str, key: str, status: str, *, note: str | None = None) -> None:
    def fn(oc: dict[str, Any]) -> None:
        for st in oc.get("steps") or []:
            if st["key"] == key:
                st["status"] = status
                if note:
                    st["note"] = note
    await _set(pid, fn)
    await G.step(key, status, label=key)


async def _pct(pid: str, pct: int, msg: str) -> None:
    await _set(pid, lambda oc: oc.update({"pct": int(pct)}))
    await G.progress(pct, msg)
    await core.index(pid)


async def review(pid: str, *, sheet: dict[str, Any] | None, tag: str, where: str, why: str, mark: str = "") -> str:
    it = await F.add_item(pid, sheet=sheet, tag=tag, category="review", origin="one_click", text={"pre": where, "mark": mark, "post": ""},
                          sub=why, where=where, why=why,
                          action={"kind": "button", "label": "섹션 열기",
                                  "target": {"route": core.section_route(pid, (sheet or {}).get("section_key") or "")}} if sheet else None)
    return it["id"]


async def collect_reviews(pid: str) -> list[str]:
    """보드 검토 항목 3종(제안): 공간당 수량 가정 · 경쟁사 수치 없음 · 사례 공개 여부."""
    out: list[str] = []
    shs = await core.sheets_of(pid)
    by_sheet = await core.open_confirm_by_sheet(pid)
    pis = [s for s in shs if s.get("role") == "PI" and s.get("inferred")]
    if pis:
        s = pis[-1]
        out.append(await review(pid, sheet=s, tag="수량 가정", where=f"공간별 제품 · {s.get('title')}",
                                why="매장당 1대로 수량을 가정했어요 — 실제 매장 도면과 맞는지 확인"))
    cm = next((s for s in shs if s.get("role") == "CM"), None)
    if cm and by_sheet.get(cm["id"]):
        out.append(await review(pid, sheet=cm, tag="수치", where="Why Samsung · 경쟁사 비교", why="경쟁사 수치를 찾지 못해 [확정 필요]로 두었어요"))
    cds = [s for s in shs if s.get("role") == "CD"]
    if cds:
        out.append(await review(pid, sheet=cds[0], tag="공개 여부", where=f"유관 사례 · 사례 {len(cds)}건",
                                why="유사도 순으로 자동 선택 — 고객사에 공개 가능한 사례인지 확인"))
    return out


async def handle(ctx: JobContext) -> dict[str, Any]:
    pl = ctx.payload
    pid = pl["proposal_id"]
    opts = pl.get("options") or {}
    job = ctx.job.id

    async def prepare(_s: dict[str, Any]) -> dict[str, Any]:
        p = await core.load(pid)
        if not p.get("type"):
            ctxd = p.get("ctx") or await plan.refresh_context(pid)
            rec = await industry.recommend_type(p, ctxd)
            from ..ops.compose import set_type
            await set_type(pid, rec["type"], source="one_click", advance=True)
            await _step(pid, "type", "inferred_done", note=f"{defs.TYPES[rec['type']]['name']} (요구사항 기반 추천)")
        p = await core.load(pid)
        if not await repo.alist("sections", {"proposal_id": pid}):
            await plan.ensure_sections(pid)
            await plan.sync_sheets(pid)
        if any(st["key"] == "compose" for st in (p.get("one_click") or {}).get("steps") or []):
            await _step(pid, "compose", "inferred_done")
        il = p.get("industry_layout") or {}
        if not il.get("decided"):
            det = il.get("detected") or {}
            from ..ops.compose import apply_industry_templates

            def fn(x: dict[str, Any]) -> None:
                lay = x.setdefault("industry_layout", core.default_industry_layout())
                lay["industry_code"] = lay.get("industry_code") or det.get("code")
                lay["decided"] = bool(lay.get("industry_code"))
            await core.mutate(pid, fn)
            await apply_industry_templates(pid)
            if det.get("mode") == "ask" and det.get("code"):
                await review(pid, sheet=None, tag="정책", where="업종 레이아웃",
                             why=f"업종을 {defs.INDUSTRIES.get(det['code'], {}).get('name', det['code'])}로 정했어요 — 두 갈래였어요")
        await core.mutate(pid, lambda x: core.advance_stage(x, "sections"), bump=False)
        await _pct(pid, 5, "유형 · 구성 확인")
        return {}

    async def sections(s: dict[str, Any]) -> dict[str, Any]:
        p = await core.load(pid)
        keys = core.type_sections(p.get("type"))
        secs = {x["key"]: x for x in await core.sections_of(pid)}
        todo = [k for k in keys if secs.get(k, {}).get("enabled", True) and not secs.get(k, {}).get("confirmed")]
        weights = {k: max(1, len(await core.sheets_of(pid, section_key=k))) for k in todo}
        total_w = sum(weights.values()) or 1
        done_w = 0
        memos: list[str] = list(s.get("memos") or [])
        skipped: list[str] = []
        for k in todo:
            await G.check_cancel()
            new = await G.new_memos()
            if new:
                memos += new
                await _set(pid, lambda oc, n=new, k=k: oc.update({"memos": [*(oc.get("memos") or []),
                                                                            *[{"text": t, "at": config.now_iso(), "applied_at": None} for t in n]]}))
            await _step(pid, k, "running")
            await core.mutate(pid, lambda x, k=k: x.update({"current_section_key": k}), bump=False)
            try:
                await SF.fill(pid, k, mode="infer", origin="one_click", job=job, memos=memos)
                await _step(pid, k, "inferred_done")
                await repo.amutate("sections", secs[k]["id"], lambda x: x.update({"inferred": True}))
            except ApiError as exc:
                if exc.code == "POLICY_CONFIDENTIAL":
                    raise
                log.warning("딸깍 섹션 %s 실패: %s", k, exc)
                skipped.append(k)
                await _step(pid, k, "skipped")
                await review(pid, sheet=(await core.sheets_of(pid, section_key=k) or [None])[0], tag="정책",
                             where=defs.SECTIONS[k]["name"], why="이 섹션은 자동으로 채우지 못했어요")
            # 이 섹션에 메모가 반영됨
            if memos:
                await _set(pid, lambda oc, k=k: oc.update({"memos": [
                    {**m, "applied_at": m.get("applied_at") or config.now_iso(), "applied_section": m.get("applied_section") or k}
                    for m in oc.get("memos") or []]}))
            done_w += weights[k]
            await _pct(pid, 5 + int(85 * done_w / total_w), f"{defs.SECTIONS[k]['short']} 추론 완료")
            await config.pace()
        return {"memos": memos, "skipped": skipped}

    async def design(_s: dict[str, Any]) -> dict[str, Any]:
        await core.mutate(pid, lambda x: core.advance_stage(x, "design"), bump=False)
        await _step(pid, "design", "inferred_done")
        return {}

    async def generate(s: dict[str, Any]) -> dict[str, Any]:
        await _step(pid, "assemble", "running")
        await GEN.gen_ensure(pid, scope="all", skey=None, infer_empty=True, origin="one_click", job=job, memos=s.get("memos") or [])
        out = await GEN.gen_render(pid)
        res = await GEN.gen_store(pid, ex=out["export"], built=out["built"], scope="all", skey=None, origin="one_click", job=job)
        await _step(pid, "assemble", "inferred_done")
        await _pct(pid, 97, "PPTX 조립 완료")
        return {"gen": res, "built": out["built"]}

    async def finalize(s: dict[str, Any]) -> dict[str, Any]:
        rv = await collect_reviews(pid) if opts.get("collect_reviews", True) else []
        p = await core.load(pid)
        oc = p.get("one_click") or {}
        confirmed_keys = set(oc.get("confirmed_sections") or [])
        smap = (s.get("built") or {}).get("slide_map") or []
        conf_slides = sum(1 for m in smap if m.get("kind") == "sheet" and m.get("section_key") in confirmed_keys)
        total = len(smap)
        review_ids = [it["id"] for it in await repo.alist("confirm_items", {"proposal_id": pid})
                      if it.get("origin") == "one_click" and it.get("category") == "review" and it.get("status") == "open"]
        result = {"slides_total": total, "confirmed_slides": conf_slides, "inferred_slides": total - conf_slides, "review_item_ids": review_ids,
                  "version": (s.get("gen") or {}).get("version")}
        await _set(pid, lambda o: o.update({"status": "succeeded", "pct": 100, "result": result, "finished_iso": config.now_iso()}))
        await core.mutate(pid, lambda x: (core.advance_stage(x, "result"), x.update({"stage": "result"})), bump=True)
        await core.index(pid, force=True)
        await G.progress(100, "딸깍 완료")
        return {"result": {"proposal_id": pid, **result, "reviews_added": len(rv)}}

    try:
        final = await G.run(ctx, G.chain([("prepare", prepare), ("sections", sections), ("design", design), ("generate", generate),
                                          ("finalize", finalize)]), {"memos": []}, labels=LABELS)
    except BaseException as exc:
        canceled = type(exc).__name__ == "JobCanceled"
        err = None if canceled else {"code": getattr(exc, "code", None) or type(exc).__name__, "message": getattr(exc, "message", None) or str(exc)}
        try:
            p = await core.load(pid)
            oc = p.get("one_click") or {}

            def back(x: dict[str, Any]) -> None:
                o = dict(x.get("one_click") or {})
                o["status"] = "canceled" if canceled else "failed"
                o["error"] = err
                for st in o.get("steps") or []:
                    if st["status"] == "running":
                        st["status"] = "canceled"
                x["one_click"] = o
                x["stage"] = oc.get("from_stage") or x.get("stage")
                if oc.get("from_section_key"):
                    x["current_section_key"] = oc["from_section_key"]
            await core.mutate(pid, back)
            await core.index(pid, force=True)
        except Exception:  # noqa: BLE001
            log.exception("딸깍 중지 처리 실패")
        raise
    return (final or {}).get("result") or {}


async def memo_list(job_id: str) -> list[dict[str, Any]]:
    try:
        return await jobs().memos(job_id, 0)
    except Exception:  # noqa: BLE001
        return []
