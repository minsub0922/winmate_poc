"""시작 방식 그래프 — rfp_extract(§7.2) · links_apply(§7.3)."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from winmate_common.jobs import JobContext

from .. import clients, config, core, defs, handoff, hub, industry, links as L, plan, prompts, repo
from . import common as G

log = logging.getLogger("winmate.proposal.start")

RFP_FIELDS = [(1, "customer", "고객사"), (2, "title", "프로젝트명"), (3, "industry", "업종"), (4, "scale", "규모"), (5, "requirements", "요구사항"),
              (6, "submit_due", "제안 제출일"), (7, "presentation", "제안 설명회"), (8, "budget", "예산 범위"), (9, "decision_makers", "의사결정자")]
STATE_LABEL = {"found": "찾음", "guess": "추정", "empty": "비어 있음"}
PHASES = [("read", "읽기"), ("locate", "항목 찾기"), ("fill", "채우기")]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


async def parsed_pages(file_id: str, *, wait_s: float = 60.0) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """files 파싱 결과(쪽 텍스트). 아직이면 파싱을 요청하고 기다린다."""
    meta = await clients.file_meta(file_id)
    doc = await clients.call("files", "GET", f"/v1/files/{file_id}/parsed", quiet=True)
    if not doc:
        await clients.call("files", "POST", f"/v1/files/{file_id}/parse", quiet=True)
        waited = 0.0
        while waited < wait_s:
            await asyncio.sleep(0.5)
            waited += 0.5
            await G.check_cancel()
            m = await clients.file_meta(file_id)
            st = (m or {}).get("parse_status")
            if st in ("done", "failed", "unsupported"):
                break
        doc = await clients.call("files", "GET", f"/v1/files/{file_id}/parsed", quiet=True)
    if not doc:
        return meta, []
    pages = [{"file_id": file_id, "no": int(pg.get("no") or i + 1), "title": pg.get("title") or "", "text": pg.get("text") or ""}
             for i, pg in enumerate(doc.get("pages") or [])]
    if not pages and doc.get("text"):
        pages = [{"file_id": file_id, "no": 1, "title": doc.get("title") or "", "text": doc["text"]}]
    return meta, pages


def page_label(pg: dict[str, Any]) -> str:
    t = (pg.get("title") or "").strip()
    return f"p.{pg['no']}" + (f" · {t[:16]}" if t else "")


def excerpt_parts(text: str, hits: list[tuple[str, int]]) -> list[dict[str, Any]]:
    """쪽 글에서 찾은 구절 앞뒤 문맥 + 하이라이트(번호)."""
    hits = sorted([(text.find(q), q, no) for q, no in hits if q and text.find(q) >= 0])
    parts: list[dict[str, Any]] = []
    cur = None
    for start, q, no in hits:
        end = start + len(q)
        lo = max(0, start - 40)
        if cur is None or lo > cur:
            if parts:
                parts.append({"text": " … "})
            parts.append({"text": text[lo:start]})
        elif start > cur:
            parts.append({"text": text[cur:start]})
        parts.append({"text": q, "field_no": no})
        cur = end
    if cur is not None:
        parts.append({"text": text[cur:cur + 40]})
    return [p for p in parts if p.get("text")]


async def handle_rfp(ctx: JobContext) -> dict[str, Any]:
    pl = ctx.payload
    pid = pl["proposal_id"]
    file_ids: list[str] = pl.get("file_ids") or []
    extra: list[str] = pl.get("extra_file_ids") or []

    async def set_phase(done_upto: int) -> None:
        def fn(x: dict[str, Any]) -> None:
            r = dict(x.get("rfp") or {})
            r["phases"] = [{"key": k, "label": lb, "status": "done" if i < done_upto else ("busy" if i == done_upto else "todo")}
                           for i, (k, lb) in enumerate(PHASES)]
            x["rfp"] = r
        await core.mutate(pid, fn, bump=False)

    async def read(_s: dict[str, Any]) -> dict[str, Any]:
        await set_phase(0)
        pages: list[dict[str, Any]] = []
        files: list[dict[str, Any]] = []
        for fid in [*file_ids, *extra]:
            meta, pgs = await parsed_pages(fid)
            if not pgs and fid in file_ids:
                from winmate_common.errors import ApiError
                raise ApiError(422, "FILE_UNREADABLE", "파일을 읽지 못했어요. 다른 파일을 올려 주세요.", {"file_id": fid})
            pages += pgs
            files.append({"file_id": fid, "name": (meta or {}).get("name") or fid, "pages": (meta or {}).get("pages") or len(pgs),
                          "kind": (meta or {}).get("kind") or "", "extra": fid in extra})
        return {"pages": pages, "files": files}

    async def locate(s: dict[str, Any]) -> dict[str, Any]:
        await set_phase(1)
        pages = s.get("pages") or []
        body = "\n\n".join(f"[p.{pg['no']}] {pg['title']}\n{pg['text'][:1500]}" for pg in pages[:40])[:24000]
        user = ("RFP · 회의록에서 9항목(고객사 · 프로젝트명 · 업종 · 규모 · 요구사항 · 제안 제출일 · 제안 설명회 · 예산 범위 · 의사결정자)을 찾아라. "
                "값마다 쪽 번호(page)와 원문 그대로의 인용(quote)을 붙이고, 원문에 없으면 값을 비워라. 요구사항은 items 에 문장 목록으로.\n"
                f"{body}")
        res = await G.llm_json("pr.rfp_fields", system=prompts.RULES, user=user, schema=prompts.RFP_FIELDS, confidential=True,
                               allow_fallback=False)
        return {"llm": res or {"fields": []}}

    async def fill(s: dict[str, Any]) -> dict[str, Any]:
        await set_phase(2)
        pages = s.get("pages") or []
        by_page = {(pg["file_id"], pg["no"]): pg for pg in pages}
        llm = {f.get("key"): f for f in (s.get("llm") or {}).get("fields") or [] if isinstance(f, dict)}
        fields = []
        det: dict[str, Any] | None = None
        hits_by_page: dict[tuple[str, int], list[tuple[str, int]]] = {}
        for no, key, label in RFP_FIELDS:
            f = llm.get(key) or {}
            value = _norm(str(f.get("value") or ""))
            quote = _norm(str(f.get("quote") or ""))
            page = f.get("page")
            items = [x for x in f.get("items") or [] if isinstance(x, str) and x.strip()]
            if key == "requirements" and items and not value:
                value = f"{len(items)}건 · {items[0]}" + (f" 외 {len(items) - 1}" if len(items) > 1 else "")
            state = "empty"
            src = None
            if value and quote:
                hit = None
                for pg in pages:
                    if quote in _norm(pg["text"]):
                        hit = pg
                        break
                if hit is not None:
                    state = "found"
                    src = {"file_id": hit["file_id"], "page": hit["no"], "page_label": page_label(hit), "quote": quote}
                    hits_by_page.setdefault((hit["file_id"], hit["no"]), []).append((quote, no))
                else:
                    state = "guess"
                    src = {"file_id": None, "page": int(page) if isinstance(page, int) else None, "page_label": f"p.{page}" if page else None, "quote": None}
            elif value:
                state = "guess"
            if key == "industry":
                # 업종은 원문 단서 해석(「추정」) — kb 업종 판별로 16업종 이름에 맞춘다
                p = await core.load(pid)
                probe = {**p, "customer": {**(p.get("customer") or {}), "name": llm.get("customer", {}).get("value") or (p.get("customer") or {}).get("name")},
                         "title": llm.get("title", {}).get("value") or p.get("title")}
                det = await industry.detect(probe, {"rq": {"items": [{"text": t} for t in (llm.get("requirements") or {}).get("items") or []]}})
                if det and det.get("code"):
                    value = defs.INDUSTRIES[det["code"]].get("full") or defs.INDUSTRIES[det["code"]]["name"]
                # 업종은 원문 단서를 해석한 값 — 값 자체가 원문에 그대로 있을 때만 「찾음」
                if value and not any(value in _norm(pg["text"]) for pg in pages):
                    state = "guess"
                    if state == "guess" and quote:
                        src = src or {"file_id": None, "page": None, "page_label": None, "quote": quote}
            if state == "empty":
                value = "원문에 없음"
            fields.append({"no": no, "key": key, "label": label, "value": value, "source": src, "state": state, "edited": False,
                           "items": items if key == "requirements" else None, "code": (det or {}).get("code") if key == "industry" and value != "원문에 없음" else None})
        excerpts = []
        for (fid, n), hits in sorted(hits_by_page.items(), key=lambda kv: kv[0][1]):
            pg = by_page.get((fid, n))
            if not pg:
                continue
            excerpts.append({"page": n, "page_label": page_label(pg), "parts": excerpt_parts(_norm(pg["text"]), hits)})
        # 요구사항 정의서(requirements 원천, §7.0-1)
        cust_name = next((f["value"] for f in fields if f["key"] == "customer" and f["state"] != "empty"), None)
        rq_job = None
        rq_id = None
        res = await clients.call("requirements", "POST", "/v1/requirements/from-files",
                                 json={"file_ids": file_ids + extra, **({"customer_hint": cust_name} if cust_name else {})}, quiet=True)
        if res:
            rq_job = res.get("job_id")
            rq_id = ((res.get("ref") or {}).get("id")) or res.get("rq_id")

        def fn(x: dict[str, Any]) -> None:
            r = dict(x.get("rfp") or {})
            r.update({"status": "done", "files": s.get("files") or [], "fields": fields, "excerpts": excerpts,
                      "phases": [{"key": k, "label": lb, "status": "done"} for k, lb in PHASES], "rq_job_id": rq_job, "rq_id": rq_id,
                      "error": None, "done_iso": config.now_iso()})
            x["rfp"] = r
            core.set_job(x, "rfp", None)
        await core.mutate(pid, fn)
        tally = {k: sum(1 for f in fields if f["state"] == k) for k in ("found", "guess", "empty")}
        return {"result": {"proposal_id": pid, "tally": tally, "rq_id": rq_id}, "pages": None}

    try:
        final = await G.run(ctx, G.chain([("read", read), ("locate", locate), ("fill", fill)]), {},
                            labels=dict(PHASES), progress_map={"read": 30, "locate": 75, "fill": 100})
    except BaseException as exc:
        err = {"code": getattr(exc, "code", None) or type(exc).__name__, "message": getattr(exc, "message", None) or str(exc)}

        def fail(x: dict[str, Any]) -> None:
            r = dict(x.get("rfp") or {})
            if r.get("job_id") == ctx.job.id:
                r["status"] = "failed"
                r["error"] = err
                x["rfp"] = r
            core.set_job(x, "rfp", None)
        try:
            await core.mutate(pid, fail, bump=False)
        except Exception:  # noqa: BLE001
            pass
        raise
    return (final or {}).get("result") or {}


# ── links_apply ────────────────────────────────────────────
async def apply_links(pid: str, *, job: str | None = None) -> dict[str, Any]:
    """후보 연결 → 반입 스냅숏 · 사용 등록 · 고객 정보 채움(Storyboard → requirements) · 추천 유형(§7.3). 섹션 초안은 만들지 않는다."""
    p = await core.load(pid)
    cands = [ln for ln in await repo.alist("links", {"proposal_id": pid}) if (ln.get("status") or "linked") in ("candidate", "linked")]
    linked = []
    for ln in cands:
        await G.check_cancel()
        saved = await L.add_link(pid, feature=ln["feature"], ref_id=ln["ref_id"], section_key=ln.get("section_key"), via=ln.get("via") or "start",
                                 handoff_id=ln.get("handoff_id"), title=ln.get("title"), status="linked",
                                 fetch=ln.get("status") == "candidate" or not ln.get("handoff"))
        linked.append(saved)
        await handoff.register_usage(saved["feature"], saved["ref_id"], proposal=p, label=core.title_display(p),
                                     version=saved.get("version_at_link"))
    # 고객 정보: Storyboard → 없으면 requirements
    order = sorted(linked, key=lambda x: {"storyboard": 0, "requirements": 1}.get(x.get("feature") or "", 2))
    for ln in order:
        await L.apply_customer(pid, ln.get("handoff"))
    for ln in linked:
        await hub.on_linked(pid, ln)      # 허브 Storyboard — 제안서에 Key message · 허브 ppt 칸 기록
    ctx = await plan.refresh_context(pid)
    from ..ops.proposals import redetect_industry
    await redetect_industry(pid)
    p = await core.load(pid)
    rec = await industry.recommend_type(p, ctx)

    def fn(x: dict[str, Any]) -> None:
        x["recommended_type"] = rec
        core.advance_stage(x, "type")
        core.set_job(x, "links_apply", None)
    await core.mutate(pid, fn)
    if p.get("type"):
        await plan.sync_sheets(pid)
    await core.index(pid, force=True)
    return {"proposal_id": pid, "linked": [x["id"] for x in linked], "recommended_type": rec}


async def handle_links_apply(ctx: JobContext) -> dict[str, Any]:
    pid = ctx.payload["proposal_id"]

    async def node(_s: dict[str, Any]) -> dict[str, Any]:
        return {"result": await apply_links(pid, job=ctx.job.id)}
    final = await G.run(ctx, G.single("apply", node), {}, labels={"apply": "연결 · 고객 정보 채우기"}, progress_map={"apply": 100})
    return (final or {}).get("result") or {}
