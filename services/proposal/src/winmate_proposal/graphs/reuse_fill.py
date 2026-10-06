"""섹션 작성 · 기존 제안서 활용 모드(§7.11).

- reuse_improve: 유지 = 원본 줄 복사(비복제 제외) · 갱신 = 복사 후 모델 · 버전 · 오래된 수치 · 매장 수 현행화 · 재작성 = 역할 · 원본 줄을 참고해
  새로 씀(`pr.reuse_rewrite`, 기밀) · 신규 = 일반 작성. 재사용 가능한 이미지만 가져오고, 시트 노트에 「원본 p.N 기반 · {판정}」.
- reuse_borrow: 일반 작성과 같되 흐름 역할 · 「이번엔」만 넣고 원본 글 · 이미지 · 수치는 넣지 않는다. 저장 전 누출 검사(§10.12) —
  걸린 줄은 비우고 다시 쓰고(`pr.reuse_line_rewrite`), 두 번 걸리면 빈 줄 + 확인 항목.
저장은 일반 섹션 작성과 같은 검사 · 값 토큰 · 템플릿 파이프라인(section_fill.persist)을 탄다.
"""
from __future__ import annotations

import copy
import logging
import re
from typing import Any

from .. import clients, config, content as C, core, defs, facts as F, inputs, prompts, repo, reuse_analysis as RA, templates
from . import common as G
from . import section_fill as SF

log = logging.getLogger("winmate.proposal.reuse_fill")

def norm(t: str) -> str:
    return re.sub(r"[\s\W_]+", "", t or "")


content_lines = C.content_lines


def align(new_lines: list[tuple[str, str]], src_lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """새 줄 ↔ 원본 줄 대응 — 같으면 유지, 비슷하면 갱신, 없으면 신규(§4.29 줄 마커)."""
    srcg = [(s, RA.gram3(s["text"])) for s in src_lines]
    used: set[str] = set()
    out = []
    for path, text in new_lines:
        g = RA.gram3(text)
        best, bs = None, 0.0
        for s, sg in srcg:
            if s["id"] in used or not g or not sg:
                continue
            sc = len(g & sg) / max(1, len(g | sg))
            if sc > bs:
                best, bs = s, sc
        same = next((s for s, _g in srcg if norm(s["text"]) == norm(text)), None)
        if best is not None and bs >= 0.3 and not (same and same["id"] in used and norm(best["text"]) != norm(text)):
            used.add(best["id"])
            out.append({"line_id": path, "source_line_id": best["id"], "mark": "keep" if norm(text) == norm(best["text"]) else "update"})
        elif same is not None:
            # 같은 글이 칸 두 곳에 들어간 경우(부제 · 칸 설명 등) — 이미 쓴 원본 줄이어도 유지
            out.append({"line_id": path, "source_line_id": same["id"], "mark": "keep"})
        else:
            out.append({"line_id": path, "source_line_id": None, "mark": "new"})
    return out


def set_path(obj: Any, path: str, value: Any) -> None:
    parts = [p for p in path.split("/") if p != ""]
    cur = obj
    for p in parts[:-1]:
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    last = parts[-1]
    if isinstance(cur, list):
        cur[int(last)] = value
    else:
        cur[last] = value


# ── 원본 본문(개선 · 수정) ─────────────────────────────────
def strip_noncopy(obj: Any, nc: set[str]) -> Any:
    """비복제 줄(V10)을 뺀 사본 — 목록 항목은 통째로, 칸 글은 비운다."""
    def bad(t: Any) -> bool:
        return isinstance(t, str) and bool(t.strip()) and any(n and (n == t.strip() or n in t or t.strip() in n and len(t.strip()) >= 6) for n in nc)

    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if k in ("signals", "images", "series"):
                out[k] = v
            elif isinstance(v, str):
                out[k] = "" if bad(v) else v
            elif isinstance(v, list):
                keep = []
                for x in v:
                    if isinstance(x, str) and bad(x):
                        continue
                    if isinstance(x, dict) and any(bad(y) for y in x.values()):
                        continue
                    keep.append(strip_noncopy(x, nc))
                out[k] = keep
            elif isinstance(v, dict):
                out[k] = strip_noncopy(v, nc)
            else:
                out[k] = v
        return out
    return obj


def image_class(im: dict[str, Any]) -> str:
    k = im.get("kind")
    if k == "kb_image" or im.get("rights") == "official":
        return "official"
    if k == "image_job" or im.get("rights") == "generated":
        return "generated"
    if im.get("rights") in ("customer", "customer_case", "site_photo"):
        return "customer"
    return "unknown"


def apply_changes(body: dict[str, Any], a: dict[str, Any], *, store: str | None, year_now: int, stats: bool = True) -> list[dict[str, Any]]:
    """갱신 판정 — 단종 모델 → 후속, 솔루션 버전, 오래된 수치 → 자리표시, 매장 수 → 이번 값(값 전파). 바꾼 것 목록."""
    applied: list[dict[str, Any]] = []
    disc = {x["model"]: x["successor"] for x in a.get("products") or [] if x.get("successor")}
    sol = {x["name"]: x for x in a.get("sol_diff") or []}

    def fn(t: str, path: str) -> str:
        if path.startswith("/signals") or path.startswith("/images"):
            return t
        new = t
        for old, succ in disc.items():
            if old in new:
                new = re.sub(rf"\b{re.escape(old)}\b", succ, new)
                applied.append({"kind": "model", "from": old, "to": succ})
        for name, x in sol.items():
            pat = re.compile(rf"({re.escape(name)})\s*{re.escape(x['from'])}(?!\d)")
            if pat.search(new):
                new = pat.sub(rf"\g<1> {x['to']}", new)
                applied.append({"kind": "solution", "name": name, "from": x["from"], "to": x["to"]})
        y = RA.YEAR_RE.search(new) if stats else None
        if y and int(y.group(1)) <= year_now - 2:
            year = int(y.group(1))
            stripped = RA.YEAR_RE.sub("", new).strip(" ·,")
            replaced = RA.NUM_UNIT_RE.sub(lambda m: C.placeholder_for(m.group(2)), stripped)
            if replaced != new:
                new = replaced
                applied.append({"kind": "stale", "year": year})
        if store:
            def rep(m: re.Match[str]) -> str:
                if m.group(1) != store:
                    applied.append({"kind": "store", "from": m.group(1), "to": store})
                    return m.group(0).replace(m.group(1), f"{int(store):,}", 1)
                return m.group(0)
            new = RA.STORE_RE.sub(rep, new)
        return new
    out = C.walk_strings({k: v for k, v in body.items() if k not in ("signals", "images", "series")}, fn)
    for k in ("signals", "images", "series"):
        if k in body:
            out[k] = body[k]
    body.clear()
    body.update(out)
    uniq: list[dict[str, Any]] = []
    for x in applied:
        if x not in uniq:
            uniq.append(x)
    return uniq


def _stats(a: dict[str, Any], pg: dict[str, Any]) -> bool:
    """이 쪽의 수치가 기준일이 의미 있는 시장 · 효과 수치인가(사례 도입 연도 같은 역사적 사실은 아님)."""
    fr = next((x.get("flow_role") for x in a.get("pages") or [] if x["no"] == pg.get("no")), None)
    return fr in RA.STAT_ROLES


def source_body(pg: dict[str, Any], *, nc: set[str], same: bool) -> tuple[dict[str, Any], int]:
    """원본 쪽 → 새 시트 기본 본문(비복제 줄 빼고, 재사용 가능한 이미지만)."""
    if pg.get("winmate") and pg.get("body") is not None:
        body = copy.deepcopy(pg["body"])
    else:
        body = {"title": pg.get("title") or "", "bullets": [ln["text"] for ln in pg.get("lines") or []][:8]}
    body = strip_noncopy(body, nc)
    imgs = [im for im in body.get("images") or [] if isinstance(im, dict) and
            (image_class(im) in ("official", "generated") or (image_class(im) == "customer" and same))]
    body["images"] = imgs
    body.pop("notes", None)
    body.pop("footnotes", None)
    return body, len(imgs)


def trace_note(pg: dict[str, Any] | None, verdict: str, img_n: int = 0) -> str:
    if not pg:
        return ""
    no = pg.get("file_page") if not pg.get("winmate") else pg.get("no")
    note = f"원본 p.{no} 기반 · {defs.VERDICT_LABEL.get(verdict, verdict)}"
    if img_n:
        note += f" — 이미지 {img_n}개는 원본에서 그대로 가져옴"
    return note


def _rq_lines(p: dict[str, Any]) -> list[str]:
    return [f"{x.get('code')} {x.get('text')}" for x in (((p.get("ctx") or {}).get("rq") or {}).get("items") or [])][:12]


def _prep(rows: list[dict[str, Any]], bases: dict[str, dict[str, Any]], cur: dict[str, Any]) -> dict[str, Any]:
    return {"rows": rows, "bases": bases, "items": cur["items"], "links": [], "features": []}


async def _finish_meta(pid: str, sids: list[str], *, ru: dict[str, Any], mode: str) -> None:
    """저장 뒤 — 시트 reuse 메타에 줄 대응 · 초안 줄(되돌리기 기준) · 출처 표시."""
    facts = await F.facts_of(pid)
    src = {pg["no"]: pg for pg in ru.get("src_pages") or []}
    nc = {x["line_id"] for x in (ru.get("analysis") or {}).get("noncopy_lines") or []}
    for sid in sids:
        sh = await repo.aget("sheets", sid)
        if not sh:
            continue
        disp = C.display_content(sh.get("content") or {}, facts) if sh.get("content") else {}
        lines = content_lines(disp)
        r = dict(sh.get("reuse") or {})
        pg = src.get(r.get("source_page") or -1)
        if mode == "improve" and pg:
            r["lines"] = align(lines, [x for x in pg.get("lines") or [] if x["id"] not in nc])
        else:
            r["lines"] = [{"line_id": path, "source_line_id": None, "mark": "new"} for path, _t in lines]
        r["draft_lines"] = {path: t for path, t in lines}
        r["draft_title"] = disp.get("title") or ""

        def fn(x: dict[str, Any], r: dict[str, Any] = r) -> None:
            x["reuse"] = r
            x["origin"] = "reuse"
        await repo.amutate("sheets", sid, fn)


def _strip_images(content: dict[str, Any], same: bool) -> int:
    """칸 안 이미지 중 재사용 가능한 것만 남긴다 → 남긴 수."""
    kept = 0
    slots = content.get("slots") or {}
    for k, v in list(slots.items()):
        def ok(x: Any) -> bool:
            return not isinstance(x, dict) or not (x.get("kind") in ("kb_image", "image_job", "file") or x.get("file_id")) or \
                image_class(x) in ("official", "generated") or (image_class(x) == "customer" and same)
        if isinstance(v, list) and any(isinstance(x, dict) and (x.get("kind") in ("kb_image", "image_job", "file") or x.get("file_id")) for x in v):
            keep = [x for x in v if ok(x)]
            kept += sum(1 for x in keep if isinstance(x, dict) and (x.get("kind") or x.get("file_id")))
            if keep:
                slots[k] = keep
            else:
                slots.pop(k)
        elif isinstance(v, dict) and (v.get("kind") in ("kb_image", "image_job", "file") or v.get("file_id")):
            if ok(v):
                kept += 1
            else:
                slots.pop(k)
    return kept


async def persist_copy(pid: str, key: str, sh: dict[str, Any], pg: dict[str, Any], verdict: str, a: dict[str, Any], *, nc: set[str],
                       same: bool, store: str | None, ru_id: str, job: str | None) -> list[dict[str, Any]]:
    """같은 역할의 Winmate 원본 시트 — 사용자가 다듬은 칸 글(content)을 그대로 옮긴다(유지) · 옮기고 현행화(갱신). 템플릿도 원본 것."""
    p = await core.load(pid)
    ctx = p.get("ctx") or {}
    year_now = int(a.get("year_now") or 0) or 2026
    content = strip_noncopy(copy.deepcopy(pg.get("content") or {}), nc)
    body, _n = source_body(pg, nc=nc, same=same)
    img_n = _strip_images(content, same)
    changes: list[dict[str, Any]] = []
    if verdict == "update":
        changes = apply_changes(content, a, store=store, year_now=year_now, stats=_stats(a, pg))
        apply_changes(body, a, store=store, year_now=year_now, stats=_stats(a, pg))
    content["notes"] = trace_note(pg, verdict, img_n)
    content.pop("footnotes", None)
    content = await SF.bind_known_facts(pid, content, ctx)
    new_content, made = await F.tokenize(pid, content, sheet_title=sh.get("title") or "", origin="reuse")
    w = pg.get("winmate") or {}
    src = [{"kind": "reuse", "ref": ru_id, "label": f"원본 p.{pg.get('no')}", "page": pg.get("no")}]
    old_content = sh.get("content") or {}

    def save(x: dict[str, Any]) -> None:
        t = dict(x.get("template") or {})
        t.update({"code": w.get("template") or t.get("code"), "mode": "auto", "source": "reuse",
                  "reason": f"원본 p.{pg.get('no')}과 같은 템플릿"})
        if w.get("product_count"):
            t["product_count"] = w["product_count"]
        x["template"] = t
        x["content"] = new_content
        x["draft"] = body
        x["sources"] = src
        x["status"] = "ready"
        x["content_rev"] = int(x.get("content_rev") or 0) + 1
        x["filled_by"] = "reuse"
        x["filled_at"] = config.now_iso()
        if not x.get("title_user_set") and new_content.get("title"):
            x["title"] = x.get("title") or new_content["title"]
    fresh, _ = await repo.amutate("sheets", sh["id"], save)
    await F.items_for_tokens(pid, fresh, made, origin="reuse", reason="원본에서 확정하지 않은 값이에요")
    if old_content and old_content != new_content:
        await core.record_change(pid, sheet=fresh, where="시트 내용", kind="content", path="/", from_=core.snippet(old_content.get("title")),
                                 to=core.snippet(new_content.get("title")), by_w=True, job_id=job, reason="원본에서 가져옴",
                                 extra={"op": "content", "from_full": old_content, "to_full": new_content},
                                 summary=f"{int(fresh.get('sheet_no') or 0):02d} {fresh.get('title')} · 원본 p.{pg.get('no')} {defs.VERDICT_LABEL.get(verdict)}")
    await G.partial({"sheet_id": sh["id"], "status": "ready", "template": (fresh.get("template") or {}).get("code")})
    return changes


async def section_done(pid: str, key: str, job: str | None) -> None:
    """섹션 상태(초안이 하나라도 있으면 ready) — persist 를 거치지 않은 복사 경로용."""
    from ..ops.sections import fill_signature
    shs = await core.sheets_of(pid, section_key=key)
    any_content = any(x.get("content") for x in shs)
    sec = await core.section_doc(pid, key)
    sig = await fill_signature(pid, key)

    def fn(x: dict[str, Any]) -> None:
        x["fill_sig"] = sig
        x["status"] = "ready" if any_content else "empty"
        x.pop("status_before_fill", None)
        if x.get("fill_job_id") == job:
            x["fill_job_id"] = None
    await repo.amutate("sections", sec["id"], fn)


# ── 개선 · 수정 ────────────────────────────────────────────
async def fill_improve(pid: str, key: str, ru: dict[str, Any], *, job: str | None, memos: list[str]) -> dict[str, Any]:
    shs = await core.sheets_of(pid, section_key=key)
    if not shs:
        return {"section_key": key, "filled": []}
    p = await core.load(pid)
    a = ru["analysis"]
    src = {pg["no"]: pg for pg in ru.get("src_pages") or []}
    nc_texts = {x["text"] for x in a.get("noncopy_lines") or []}
    nc_ids = {x["line_id"] for x in a.get("noncopy_lines") or []}
    same = bool(a["context"].get("same_customer"))
    store = ((p.get("ctx") or {}).get("store_count") or "").replace(",", "") or None
    cur = await inputs.base_bodies(p, key, shs, mode="draft")
    allowed_cur = inputs.allowed_from(p, [b["body"] for b in cur["sheets"].values()], [list((await F.facts_of(pid)).values())])
    cat = await clients.export_catalog()
    copy_direct: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    copy_rows: list[dict[str, Any]] = []
    copy_bases: dict[str, dict[str, Any]] = {}
    llm_rows: list[dict[str, Any]] = []
    llm_bases: dict[str, dict[str, Any]] = {}
    rewrite_in: list[dict[str, Any]] = []
    draft_in: list[dict[str, Any]] = []
    guidance: list[str] = []
    changes: dict[str, list[dict[str, Any]]] = {}
    for sh in shs:
        r = sh.get("reuse") or {}
        v = r.get("verdict") or "auto"
        pg = src.get(r.get("source_page") or -1)
        base = cur["sheets"][sh["id"]]
        row = {"sheet_id": sh["id"], "key": SF.sheet_key(sh), "role": sh.get("role"), "action": "draft", "has_input": True}
        reuse_src = [{"kind": "reuse", "ref": ru["id"], "label": f"원본 p.{(pg or {}).get('file_page') or (pg or {}).get('no')}", "page": (pg or {}).get("no")}] if pg else []
        w = (pg or {}).get("winmate") or {}
        if v in ("keep", "update") and pg and w.get("role") == sh.get("role") and pg.get("content") and \
                templates.available(cat, w.get("template")):
            copy_direct.append((sh, pg, v))
            continue
        if v in ("keep", "update") and pg:
            body, img_n = source_body(pg, nc=nc_texts, same=same)
            if v == "update":
                changes[sh["id"]] = apply_changes(body, a, store=store, year_now=int(a.get("year_now") or 0) or 2026, stats=_stats(a, pg))
            body["notes"] = trace_note(pg, v, img_n)
            copy_bases[sh["id"]] = {"body": body, "sources": reuse_src, "has_input": True}
            copy_rows.append(row)
        elif v == "rewrite" and pg:
            body = copy.deepcopy(base["body"])
            body["notes"] = trace_note(pg, v)
            llm_bases[sh["id"]] = {"body": body, "sources": [*base["sources"], *reuse_src], "has_input": True}
            llm_rows.append(row)
            rewrite_in.append({"sheet_key": row["key"], "role": sh.get("role") or "", "role_name": core.role_name(sh.get("role")),
                               "title": sh.get("title") or "", "note": r.get("note") or "이번 요구사항 기준으로 다시 씀",
                               "source_lines": [x["text"][:90] for x in pg.get("lines") or [] if x["id"] not in nc_ids][:12],
                               "sheet_id": sh["id"], "page": pg})
        elif v == "new":
            body = copy.deepcopy(base["body"])
            rq = (sh.get("repeat_key") or {})
            body["notes"] = f"요구사항 갭 · {rq.get('ref') or ''} 신규".strip()
            llm_bases[sh["id"]] = {"body": body, "sources": base["sources"], "has_input": base["has_input"]}
            llm_rows.append(row)
            draft_in.append(row)
            guidance.append(f"{sh.get('title')}: 요구사항 갭 {rq.get('ref') or ''} — 원본에 없던 요구사항이라 새 시트로 쓴다.")
        elif base["has_input"]:
            llm_bases[sh["id"]] = base
            llm_rows.append(row)
            draft_in.append(row)
    # 1) 복사 · 갱신 — 원본 수치는 원본 줄 그대로 허용(개선 · 수정은 원본 줄을 쓰는 것이 목적)
    for sh, pg, v in copy_direct:
        chs = await persist_copy(pid, key, sh, pg, v, a, nc=nc_texts, same=same, store=store, ru_id=ru["id"], job=job)
        if chs:
            changes[sh["id"]] = chs
    if copy_direct:
        await section_done(pid, key, job)
    if copy_rows:
        await SF.persist(pid, key, _prep(copy_rows, copy_bases, cur), {}, mode="reuse_improve", origin="reuse", job=job)
    # 2) 재작성 · 신규 · 자동(입력 있음) — LLM. 수치는 이번 입력에만 근거
    drafts: dict[str, dict[str, Any]] = {}
    if rewrite_in:
        user = prompts.reuse_rewrite(section_key=key, section_name=defs.SECTIONS[key]["name"], customer=(p.get("customer") or {}).get("name") or "",
                                     project=p.get("title") or "", requirements=_rq_lines(p), sheets=rewrite_in)
        res = await G.llm_json("pr.reuse_rewrite", system=prompts.RULES, user=user, schema=prompts.SECTION_DRAFT, confidential=True)
        got = SF.map_drafts(res, [r for r in llm_rows if any(x["sheet_id"] == r["sheet_id"] for x in rewrite_in)])
        drafts.update(got)
        for x in rewrite_in:
            if x["sheet_id"] in got:
                continue
            # 모델이 쓰지 않았으면 원본 줄(비복제 제외)을 바탕으로 — 원본 수치는 이번 입력에 없으면 자리표시
            body, _n = source_body(x["page"], nc=nc_texts, same=same)
            apply_changes(body, a, store=store, year_now=int(a.get("year_now") or 0) or 2026, stats=_stats(a, x["page"]))
            body, _m = C.ground_body(body, allowed_cur)
            body["notes"] = trace_note(x["page"], "rewrite")
            llm_bases[x["sheet_id"]]["body"] = body
    if draft_in:
        prep_d = {"rows": draft_in, "bases": {r["sheet_id"]: llm_bases[r["sheet_id"]] for r in draft_in}, "items": cur["items"]}
        drafts.update(await SF.draft(pid, key, prep_d, mode="reuse_improve", request=None, memos=memos, extra_lines=guidance))
    if llm_rows:
        await SF.persist(pid, key, _prep(llm_rows, llm_bases, cur), drafts, mode="reuse_improve", origin="reuse", job=job)
    done = [x[0]["id"] for x in copy_direct] + [r["sheet_id"] for r in copy_rows + llm_rows]
    if copy_direct and not (copy_rows or llm_rows):
        await F.sync_items(pid)
        await core.touch(pid)
        await core.index(pid)
    await _finish_meta(pid, done, ru=ru, mode="improve")
    return {"section_key": key, "filled": done, "changes": changes}


# ── 흐름 차용 ──────────────────────────────────────────────
def source_texts(ru: dict[str, Any]) -> list[str]:
    out = []
    for pg in ru.get("src_pages") or []:
        if pg.get("title"):
            out.append(pg["title"])
        out += [x["text"] for x in pg.get("lines") or []]
    return [t for t in out if len(norm(t)) >= 6]


def leak_paths(d: dict[str, Any], src_grams: list[set[str]], names: list[str]) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []

    def fn(t: str, path: str) -> str:
        if path.startswith("/signals") or path.endswith("/sheet_key") or path == "/sheet_key" or not t.strip():
            return t
        if any(n and n in t for n in names):
            hits.append((path, t))
            return t
        g = RA.gram3(t)
        if len(g) >= 4 and any(sg and len(g & sg) / max(1, len(g | sg)) >= 0.8 for sg in src_grams):
            hits.append((path, t))
        return t
    C.walk_strings(d, fn)
    return hits


async def fill_borrow(pid: str, key: str, ru: dict[str, Any], *, job: str | None, memos: list[str],
                      guide: dict[str, dict[str, Any]]) -> dict[str, Any]:
    shs = await core.sheets_of(pid, section_key=key)
    if not shs:
        return {"section_key": key, "filled": []}
    p = await core.load(pid)
    a = ru["analysis"]
    cur = await inputs.base_bodies(p, key, shs, mode="draft")
    rows = [{"sheet_id": sh["id"], "key": SF.sheet_key(sh), "role": sh.get("role"), "action": "draft",
             "has_input": cur["sheets"][sh["id"]]["has_input"]} for sh in shs]
    tone = a.get("tone")
    lines = []
    for sh in shs:
        g = guide.get(sh["id"]) or {}
        lines.append(f"{sh.get('title')}: 흐름 역할 「{g.get('flow_role') or '이번 유형 기본'}」" +
                     (f" · 이번엔 {' '.join(g.get('rq_ids') or [])}" if g.get("rq_ids") else "") + (f" · 톤 {tone}" if tone else ""))
    prep = {"rows": rows, "bases": cur["sheets"], "items": cur["items"]}
    drafts = await SF.draft(pid, key, prep, mode="reuse_borrow", request=None, memos=memos, extra_lines=lines)
    # 누출 검사(§10.12) — 원본 줄 · 원본에만 있는 고유명사
    src_grams = [RA.gram3(t) for t in source_texts(ru)]
    cust = (p.get("customer") or {}).get("name") or ""
    sc = a["context"].get("source_customer") or ""
    names = [n for n in {sc, sc.replace(" ", "")} if len(n) >= 2 and RA.norm_name(n) != RA.norm_name(cust)] if sc else []
    blanks: dict[str, list[str]] = {}
    rq = _rq_lines(p)
    by_id = {sh["id"]: sh for sh in shs}
    for sid, d in drafts.items():
        hits = leak_paths(d, src_grams, names)
        if not hits:
            continue
        sh = by_id.get(sid) or {}
        clean = [t for _pth, t in [(x, y) for x, y in _strings(d)] if t and not any(t == h[1] for h in hits)]
        for path, _text in hits:
            set_path(d, path, "")
            res = await G.llm_json("pr.reuse_line_rewrite", system=prompts.RULES,
                                   user=prompts.reuse_line_rewrite(role=sh.get("role") or "", role_name=core.role_name(sh.get("role")),
                                                                   title=sh.get("title") or "", field=path.strip("/"), neighbors=clean, requirements=rq),
                                   schema=prompts.LINE_REWRITE, confidential=True)
            new = ((res or {}).get("text") or "").strip()
            if new and not leak_paths({"t": new}, src_grams, names):
                set_path(d, path, new)
            else:
                blanks.setdefault(sid, []).append(path)
        log.info("흐름 차용 누출 검사 %s · %d줄 다시 씀 · %d줄 비움", sid, len(hits), len(blanks.get(sid) or []))
    for sh in shs:
        g = guide.get(sh["id"]) or {}
        b = cur["sheets"][sh["id"]]["body"]
        b["notes"] = f"흐름 차용 · {g.get('flow_role') or '이번 유형 기본'} · 원본 내용 0줄"
    await SF.persist(pid, key, prep, drafts, mode="reuse_borrow", origin="reuse", job=job)
    for sid, paths in blanks.items():
        fresh = await repo.aget("sheets", sid) or by_id.get(sid) or {}
        await F.add_item(pid, sheet=fresh, tag="정책", category="review", origin="reuse",
                         text={"pre": "", "mark": "흐름 차용 중 원본 문장과 너무 비슷해 비워 두었어요", "post": ""},
                         sub=f"{fresh.get('title')} · 이번 고객 기준으로 직접 채워 주세요({len(paths)}줄)")
    await _finish_meta(pid, [sh["id"] for sh in shs], ru=ru, mode="borrow")
    return {"section_key": key, "filled": [sh["id"] for sh in shs], "leak_blanks": sum(len(v) for v in blanks.values())}


def _strings(d: Any) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    C.walk_strings(d, lambda t, path: (out.append((path, t)), t)[1])
    return [(p_, t) for p_, t in out if not p_.endswith("sheet_key") and not p_.startswith("/signals")]
