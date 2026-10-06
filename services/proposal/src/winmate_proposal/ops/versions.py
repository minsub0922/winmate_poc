"""§6.11 버전 · 변경 이력(PR7V) — 버전 목록 · 저장 · 비교 · 되돌리기(전체 → 새 버전 / 시트만) · 바뀐 곳 되돌리기."""
from __future__ import annotations

import copy
import re
from typing import Any

from .. import config, core, defs, facts as F, repo, versions as VER
from .. import models as M
from ..errors import not_found, unprocessable, version_not_found

KIND_LABEL = {"text": "텍스트", "content": "텍스트", "format": "서식", "notes": "텍스트 · 노트", "structure": "구조", "value": "값",
              "template": "템플릿", "source": "자료"}
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


async def _changes(pid: str) -> list[dict[str, Any]]:
    now = config.now_iso()
    rows = [c for c in await repo.alist("changes", {"proposal_id": pid}) if (c.get("expires_at") or "9999") > now]
    return sorted(rows, key=lambda c: c.get("ts") or "")


def _change_line(c: dict[str, Any]) -> M.VersionChange:
    t = config.parse_iso(c.get("ts"))
    hhmm = f"{(t.astimezone(config.KST) if t else config.now()).strftime('%H:%M')}" if t else ""
    text = c.get("summary") or c.get("where") or ""
    if c.get("actor") == "W" and "· W" not in text:
        text += " · W"
    return M.VersionChange(change_id=c["id"], t=hhmm, text=text)


async def list_versions(pid: str, include: str = "changes,events") -> M.VersionsView:
    p = await core.load(pid)
    cur = int(p.get("saved_version") or 0)
    vs = await VER.list_versions(pid)
    chs = await _changes(pid)
    inc = set((include or "").split(","))
    items = []
    for v in sorted(vs, key=lambda x: -int(x["n"])):
        n = int(v["n"])
        author = VER.author_label(v.get("author"))
        changes = [_change_line(c) for c in chs if int(c.get("after_version") or 0) == n - 1 and n > 1] if "changes" in inc else []
        changes.reverse()
        df = v.get("derived_from") or {}
        items.append(M.VersionItem(n=n, label=f"v{n}", kind=v.get("kind") or "manual", desc=v.get("desc") or "", author_label=author,
                                   created_at=v.get("created_iso") or "", time_label=f"{config.when_label(v.get('created_iso'))} · {author}",
                                   current=(n == cur), derived_label=df.get("label"), changes=changes))
    events = []
    if "events" in inc:
        for e in p.get("review_events") or []:
            k = e.get("kind") or ""
            if k in ("request", "resubmit"):
                txt = f"{'검토 요청' if k == 'request' else '다시 검토 요청'} · {config.when_label(e.get('at'))} · {int(e.get('reviewers') or 0)}명에게"
                events.append(M.VersionEvent(at=e.get("at") or "", text=txt, kind="review_request"))
            elif k.startswith("decision:"):
                d = k.split(":", 1)[1]
                events.append(M.VersionEvent(at=e.get("at") or "", text=f"{'승인' if d == 'approve' else '수정 요청'} · {config.when_label(e.get('at'))}",
                                             kind="review_decision"))
    pending = [_change_line(c) for c in chs if int(c.get("after_version") or 0) == cur][::-1]
    return M.VersionsView(current=cur, current_label=f"v{cur} · 현재" if cur else "", versions=items, events=events, change_count=len(chs),
                          pending_changes=pending, header_label=f"버전 {cur} · 변경 기록 {len(chs)}", next_save_label=f"지금 상태를 v{cur + 1}로 저장")


async def save_version(pid: str, body: M.VersionCreate) -> M.VersionCreated:
    p = await core.load(pid)
    doc = await VER.create(pid, kind="manual", desc=(body.desc or "").strip() or "직접 저장", author=core.actor(),
                           pptx_file_id=(p.get("files") or {}).get("pptx_file_id"))
    await core.index(pid, force=True)
    return M.VersionCreated(n=int(doc["n"]))


def _sheets_of(snap: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["id"]: s for s in snap.get("sheets") or [] if s.get("status") != "excluded" and not s.get("hidden")}


async def compare(pid: str, a: int | None, b: int | None, mode: str, sheet: str | None) -> M.CompareView:
    p = await core.load(pid)
    cur = int(p.get("saved_version") or 0)
    if cur == 0:
        raise unprocessable("NO_VERSION", "저장된 버전이 아직 없어요")
    b = b or cur
    a = a or max(1, b - 1)
    if a == b:
        raise unprocessable("SAME_VERSION", "같은 버전끼리는 비교할 수 없어요")
    va, vb = await VER.get_version(pid, a), await VER.get_version(pid, b)
    if not va:
        raise version_not_found(a)
    if not vb:
        raise version_not_found(b)
    lo, hi = sorted((a, b))
    sa, sb = _sheets_of(va.get("snapshot") or {}), _sheets_of(vb.get("snapshot") or {})
    chs = [c for c in await _changes(pid) if lo <= int(c.get("after_version") or 0) < hi and c.get("sheet_id")]
    diffs: list[M.DiffItem] = []
    counted: dict[str, int] = {}
    for c in chs:
        if c.get("reverted_by"):
            continue
        sid = c["sheet_id"]
        fr, to = c.get("from"), c.get("to")
        diffs.append(M.DiffItem(**{"n": len(diffs) + 1, "change_id": c["id"], "sheet_id": sid, "sheet_no": c.get("sheet_no"), "where": c.get("where") or "",
                                   "kind": KIND_LABEL.get(c.get("kind") or "", c.get("kind") or ""), "from": fr, "to": to,
                                   "from_swatch": fr if isinstance(fr, str) and HEX.match(fr) else None,
                                   "to_swatch": to if isinstance(to, str) and HEX.match(to) else None,
                                   "why": c.get("reason") or ("W" if c.get("actor") == "W" else ""), "bbox": c.get("bbox"),
                                   "revertable": bool(c.get("from_full") is not None or c.get("op"))}))
        counted[sid] = counted.get(sid, 0) + 1
    # 기록이 없는 차이(다시 생성 등)는 스냅숏 비교로
    for sid, s2 in sb.items():
        s1 = sa.get(sid)
        if sid in counted:
            continue
        if s1 is None or (s1.get("content") or {}) != (s2.get("content") or {}):
            where = "새 시트" if s1 is None else "시트 내용"
            diffs.append(M.DiffItem(**{"n": len(diffs) + 1, "sheet_id": sid, "sheet_no": s2.get("sheet_no"), "where": where,
                                       "kind": "구조" if s1 is None else "텍스트", "from": core.snippet(((s1 or {}).get("content") or {}).get("title")),
                                       "to": core.snippet((s2.get("content") or {}).get("title")), "why": "", "revertable": False}))
            counted[sid] = counted.get(sid, 0) + 1
    changed = []
    names = {**{k: v for k, v in sa.items()}, **sb}
    for sid, n in counted.items():
        s = names.get(sid) or {}
        changed.append(M.CompareSheet(sheet_no=int(s.get("sheet_no") or 0), sheet_id=sid, name=s.get("title") or "", count=n))
    changed.sort(key=lambda x: -x.count)
    if sheet:
        diffs = [d for d in diffs if d.sheet_id == sheet]
        for i, d in enumerate(diffs):
            d.n = i + 1
    rev = (p.get("review") or {}).get("version")

    focus = sheet or (changed[0].sheet_id if changed else None)

    def side(v: dict[str, Any], tag: str) -> M.CompareSide:
        n = int(v["n"])
        meta = config.when_label(v.get("created_iso"))
        if n == cur:
            meta += " · 현재"
        elif rev and n == int(rev):
            meta += " · 검토 요청한 버전"
        snap = v.get("snapshot") or {}
        sh = _sheets_of(snap).get(focus or "") if focus else None
        disp = None
        if sh and sh.get("content"):
            facts = {f["id"]: f for f in snap.get("facts") or [] if f.get("id")}
            from .. import content as C
            disp = C.display_content(sh["content"], facts)
        return M.CompareSide(n=n, label=f"{tag} v{n}", meta=meta, png_url=None, sheet_id=focus if sh else None, display=disp)
    return M.CompareView(a=side(va, "A"), b=side(vb, "B"), changed_sheets=changed, diffs=diffs,
                         header_label=f"바뀐 시트 {len(changed)} · 바뀐 곳 {sum(c.count for c in changed)}", sheet_id=sheet,
                         footer_note=f"되돌려도 v{max(a, b)}는 이력에 남아요. 언제든 다시 돌아올 수 있어요.")


async def restore(pid: str, n: int, body: M.RestoreIn) -> M.RestoreResult:
    p = await core.load(pid)
    v = await VER.get_version(pid, n)
    if not v:
        raise version_not_found(n)
    snap = v.get("snapshot") or {}
    if body.scope == "sheet":
        if not body.sheet_id:
            raise unprocessable("SHEET_REQUIRED", "되돌릴 시트를 알려 주세요")
        old = next((s for s in snap.get("sheets") or [] if s["id"] == body.sheet_id), None)
        if not old:
            raise unprocessable("SHEET_NOT_IN_VERSION", f"v{n}에는 이 시트가 없어요", sheet_id=body.sheet_id)
        cur_sh = await core.sheet_doc(pid, body.sheet_id)

        def fn(x: dict[str, Any]) -> None:
            for k in ("content", "draft", "template", "title", "signals", "sources", "status"):
                x[k] = copy.deepcopy(old.get(k))
            x["content_rev"] = int(x.get("content_rev") or 0) + 1
            if int(p.get("saved_version") or 0) > 0:
                x["edited_since_version"] = True
        saved, _ = await repo.amutate("sheets", body.sheet_id, fn)
        cid = await core.record_change(pid, sheet=saved, where="시트 전체", kind="structure", path="/", from_=core.snippet((cur_sh.get("content") or {}).get("title")),
                                       to=core.snippet((old.get("content") or {}).get("title")), reason=f"v{n}로 되돌림",
                                       summary=f"{int(saved.get('sheet_no') or 0):02d} 시트를 v{n}로 되돌림",
                                       extra={"op": "content", "from_full": cur_sh.get("content"), "to_full": old.get("content")})
        await F.sync_items(pid)
        await core.touch(pid, user_edit=True)
        return M.RestoreResult(scope="sheet", change_ids=[cid])
    # 전체 → 지금 상태를 그 버전 스냅숏으로 바꾸고 새 버전(kind restore)
    keep_ids = {s["id"] for s in snap.get("sheets") or []}
    for s in await repo.alist("sheets", {"proposal_id": pid}):
        if s["id"] not in keep_ids:
            await repo.adelete("sheets", s["id"])
    for s in snap.get("sheets") or []:
        await repo.aput("sheets", s["id"], {**copy.deepcopy(s), "proposal_id": pid, "content_rev": int(s.get("content_rev") or 0) + 1,
                                           "edited_since_version": False})
    for coll, rows in (("sections", snap.get("sections") or []), ("facts", snap.get("facts") or []), ("confirm_items", snap.get("confirm_items") or [])):
        ids = {r["id"] for r in rows}
        for r in await repo.alist(coll, {"proposal_id": pid}):
            if r["id"] not in ids:
                await repo.adelete(coll, r["id"])
        for r in rows:
            await repo.aput(coll, r["id"], {k: v for k, v in copy.deepcopy(r).items() if k not in ("created_at", "updated_at", "_cas")})
    pf = snap.get("proposal") or {}

    def fn2(x: dict[str, Any]) -> None:
        for k in ("type", "industry_layout", "design", "current_section_key", "customer", "title", "schedule"):
            if k in pf:
                x[k] = copy.deepcopy(pf[k])
    await core.mutate(pid, fn2)
    doc = await VER.create(pid, kind="restore", desc=f"v{n} 전체로 되돌림", author=core.actor(), pptx_file_id=v.get("pptx_file_id"),
                           extra={"restored_from": n, "slide_map": v.get("slide_map"), "slides": v.get("slides"), "file_name": v.get("file_name")})
    await core.index(pid, force=True)
    return M.RestoreResult(scope="all", new_version=int(doc["n"]))


def _ptr_parent(doc: Any, path: str) -> tuple[Any, str]:
    from .sections import _parts, _resolve
    parts = _parts(path)
    return _resolve(doc, parts, create=True)


async def revert_change(pid: str, change_id: str) -> M.RevertResult:
    await core.load(pid)
    c = await repo.aget("changes", change_id)
    if not c or c.get("proposal_id") != pid:
        raise not_found("변경 기록", change_id, "CHANGE_NOT_FOUND")
    if c.get("reverted_by"):
        raise unprocessable("ALREADY_REVERTED", "이미 되돌린 변경이에요")
    op = c.get("op")
    sid = c.get("sheet_id")
    if op == "fact" and c.get("fact_id"):
        f, _ = await repo.amutate("facts", c["fact_id"], lambda x: x.update({"value": c.get("from_full"), "status": c.get("from_status") or (
            "confirmed" if c.get("from_full") not in (None, "") else "placeholder")}))
        if f.get("status") == "placeholder":
            await F.add_item(pid, sheet=await repo.aget("sheets", sid) if sid else None, tag="수치", fact_id=f["id"], origin="user",
                             text={"pre": f.get("label") or "", "mark": f.get("placeholder") or "[00]", "post": ""}, sub="값 확정을 되돌렸어요")
        for u in (await F.used_in(pid)).get(c["fact_id"], []):
            await repo.amutate("sheets", u["sheet_id"], lambda x: x.update({"content_rev": int(x.get("content_rev") or 0) + 1}))
    elif sid:
        sh = await core.sheet_doc(pid, sid)

        def fn(x: dict[str, Any]) -> None:
            content = copy.deepcopy(x.get("content") or {})
            path = c.get("path") or "/"
            if op in ("content",) or path == "/":
                if isinstance(c.get("from_full"), dict):
                    content = copy.deepcopy(c["from_full"])
            elif op == "template":
                ff = c.get("from_full") or {}
                x["template"] = ff.get("template") or x.get("template")
                content = ff.get("content") or content
            elif op in ("set", "delete"):
                parent, last = _ptr_parent(content, path)
                if isinstance(parent, list):
                    i = int(last) if last != "-" else len(parent)
                    if op == "set":
                        if i < len(parent):
                            parent[i] = c.get("from_full")
                    else:
                        parent.insert(i, c.get("from_full"))
                elif c.get("from_full") is None and op == "set":
                    parent.pop(last, None)
                else:
                    parent[last] = c.get("from_full")
            elif op == "insert":
                parent, last = _ptr_parent(content, path)
                if isinstance(parent, list):
                    i = int(last) if last != "-" else len(parent) - 1
                    if 0 <= i < len(parent):
                        parent.pop(i)
                else:
                    parent.pop(last, None)
            elif op == "move" and c.get("move_from"):
                from .sections import _get, apply_op
                val = copy.deepcopy(_get(content, path))
                apply_op(content, M.SheetOp(op="delete", path=path))
                apply_op(content, M.SheetOp(op="insert", path=c["move_from"], value=val))
            else:
                raise unprocessable("NOT_REVERTABLE", "이 변경은 되돌릴 수 없어요")
            x["content"] = content
            x["content_rev"] = int(x.get("content_rev") or 0) + 1
        saved, _ = await repo.amutate("sheets", sid, fn)
        _ = sh
    else:
        raise unprocessable("NOT_REVERTABLE", "이 변경은 되돌릴 수 없어요")
    sheet = await repo.aget("sheets", sid) if sid else None
    new_id_ = await core.record_change(pid, sheet=sheet, where=c.get("where") or "", kind=c.get("kind") or "text", path=c.get("path") or "",
                                       from_=c.get("to"), to=c.get("from"), reason="되돌리기",
                                       summary=f"{c.get('summary') or ''} · 되돌림", extra={"op": "revert", "reverts": change_id})
    await repo.amutate("changes", change_id, lambda x: x.update({"reverted_by": new_id_}))
    await F.sync_items(pid)
    await core.touch(pid, user_edit=True)
    return M.RevertResult(change_id=new_id_, reverted_change_id=change_id, sheet_id=sid)
