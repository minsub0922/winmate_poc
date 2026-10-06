"""값(fact, §5.6) · 확인 항목(confirm_item, §5.8) 도우미.

- 시트 글의 플레이스홀더(`[00]시간`)는 값 토큰 `{{fact:fct_…}}` 로 바꾸고, 값마다 열린 확인 항목을 정확히 1개 둔다(V9).
- 값이 확정되면 그 값을 쓰는 모든 시트가 토큰으로 함께 바뀐다(V3 값 전파).
"""
from __future__ import annotations

import re
from typing import Any

from winmate_common.ids import new_id

from . import config, content as C, core, defs, repo


async def facts_of(pid: str) -> dict[str, dict[str, Any]]:
    return {f["id"]: f for f in await repo.alist("facts", {"proposal_id": pid})}


async def fact_by_key(pid: str, key: str) -> dict[str, Any] | None:
    items = await repo.alist("facts", {"proposal_id": pid, "key": key})
    return items[0] if items else None


async def upsert_fact(pid: str, *, key: str, label: str, value: str | None = None, unit: str | None = None,
                      status: str = "placeholder", placeholder: str = "[00]", origin: dict[str, Any] | None = None,
                      kind: str = "input", formula: str | None = None, evidence: dict[str, Any] | None = None,
                      keep_confirmed: bool = True) -> dict[str, Any]:
    cur = await fact_by_key(pid, key)
    if cur:
        def fn(f: dict[str, Any]) -> None:
            if keep_confirmed and f.get("status") == "confirmed":
                return
            if value not in (None, ""):
                f["value"] = value
                f["status"] = status if status != "placeholder" else "unconfirmed"
            if unit:
                f["unit"] = unit
            if formula:
                f["formula"] = formula
                f["kind"] = "derived"
        saved, _ = await repo.amutate("facts", cur["id"], fn)
        return saved
    doc = {"id": new_id("fct"), "proposal_id": pid, "key": key, "label": label, "value": value, "unit": unit, "kind": kind,
           "formula": formula, "status": status if value not in (None, "") or status == "placeholder" else "placeholder",
           "placeholder": placeholder, "evidence": evidence, "origin": origin or {"by": "agent"}, "history": [],
           "moved_to_note": False}
    return await repo.aput("facts", doc["id"], doc)


# 자리표시([00]시간) + 확인 표시([확정 필요] · [확인 필요]) — 둘 다 값 토큰 + 확인 항목(V9)
MARK_ANY = re.compile(defs.PLACEHOLDER_RE.pattern + "|" + defs.CONFIRM_MARK_RE.pattern)

# 여러 시트가 함께 쓰는 값(V3) — (판별, 이름, 확인 항목 태그, 이유)
SHARED: dict[str, tuple[Any, str, str, str]] = {
    "store_count": (lambda pre, post, unit: unit in ("개", "곳", "") and (post.strip().startswith("매장") or pre.strip().endswith("매장 수"))
                    or (unit == "" and pre.strip().endswith("매장")), "매장 수", "고객 확인", "매장 수를 아직 받지 못했어요"),
}


def _struct_label(body: dict[str, Any], path: str) -> str | None:
    """표 칸 · 수치 칸이면 그 줄 이름(「유지보수 응답 시간 · 경쟁사 A」 · 「교체 주기」)."""
    m = re.fullmatch(r"/kpis/(\d+)/value", path)
    if m:
        k = (body.get("kpis") or [])[int(m.group(1))] if int(m.group(1)) < len(body.get("kpis") or []) else {}
        return (k or {}).get("label") or None
    m = re.fullmatch(r"/(?:table|slots/[^/]+)/rows/(\d+)/cells/(\d+)/text", path)
    if m:
        t = body.get("table") or {}
        rows = t.get("rows") or []
        r, c = int(m.group(1)), int(m.group(2))
        if r < len(rows):
            cols = t.get("columns") or []
            col = cols[c + 1] if c + 1 < len(cols) else ""
            return " · ".join(x for x in (rows[r].get("label"), col) if x) or None
    return None


def _key_of(label: str, unit: str) -> str:
    base = re.sub(r"[^0-9A-Za-z가-힣]+", "_", label).strip("_").lower()[:40]
    return f"{base}_{(unit or 'n').strip()}" if base else f"value_{(unit or 'n').strip()}"


def _sibling_unit(body: dict[str, Any], path: str) -> str:
    """KPI 값 칸(…/value)의 자리표시는 단위가 옆 칸(unit)에 있다 → 확인 항목 표시용(「[0]명」)."""
    if not path.endswith("/value"):
        return ""
    cur: Any = body
    for part in [x for x in path.split("/")[:-1] if x]:
        try:
            cur = cur[int(part)] if isinstance(cur, list) else cur.get(part)
        except (ValueError, IndexError, AttributeError, TypeError):
            return ""
        if cur is None:
            return ""
    u = cur.get("unit") if isinstance(cur, dict) else None
    return str(u).strip() if u and len(str(u).strip()) <= 4 else ""


async def tokenize(pid: str, body: dict[str, Any], *, sheet_title: str, origin: str = "section_fill") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """body 글의 플레이스홀더를 값 토큰으로. → (새 body, 만든 값 목록[{fact, pre, post}])"""
    made: list[dict[str, Any]] = []
    jobs: list[tuple[str, str, str, str]] = []   # (path, placeholder, pre, post)

    def scan(t: str, path: str) -> str:
        for m in MARK_ANY.finditer(t or ""):
            jobs.append((path, m.group(0), t[max(0, m.start() - 28):m.start()], t[m.end():m.end() + 18]))
        return t
    skip = ("signals", "images", "series", "notes", "footnotes", "source_list")
    C.walk_strings({k: v for k, v in body.items() if k not in skip}, scan)
    if not jobs:
        return body, made
    mapping: dict[tuple[str, int], str] = {}
    counter: dict[str, int] = {}
    for path, ph, pre, post in jobs:
        is_mark = not ph.startswith("[0")
        unit = "" if is_mark else re.sub(r"^\[0{1,2}\]\s?", "", ph).strip()
        shared = None if is_mark else next((k for k, (test, _l, _t, _r) in SHARED.items() if test(pre, post, unit)), None)
        if shared:
            label, tag, why = SHARED[shared][1], SHARED[shared][2], SHARED[shared][3]
            key = shared
        else:
            label = _struct_label(body, path) or C.label_near(pre) or sheet_title
            tag, why = "수치", None
            key = _key_of(f"{sheet_title}_{label}", unit)
            n = counter.get(key, 0)
            counter[key] = n + 1
            key = f"{key}_{n}" if n else key
        f = await upsert_fact(pid, key=key, label=label, placeholder=ph if ph.startswith("[") else "[00]", unit=unit or None,
                              status="placeholder", origin={"by": "agent", "source_ref": origin})
        made.append({"fact": f, "pre": pre.strip() or (_struct_label(body, path) or ""), "post": post.strip(), "path": path, "placeholder": ph,
                     "tag": tag, "why": why, "mark_unit": "" if is_mark or unit else _sibling_unit(body, path)})
        mapping[(path, len([x for x in mapping if x[0] == path]))] = f["id"]

    def rep(t: str, path: str) -> str:
        i = 0

        def sub(m: re.Match[str]) -> str:
            nonlocal i
            fid = mapping.get((path, i))
            i += 1
            return "{{fact:" + fid + "}}" if fid else m.group(0)
        return MARK_ANY.sub(sub, t)
    new = C.walk_strings({k: v for k, v in body.items() if k not in skip}, rep)
    for k in skip:
        if k in body:
            new[k] = body[k]
    return new, made


def text_parts(pre: str, mark: str, post: str) -> dict[str, str]:
    return {"pre": (pre or "").strip()[-30:], "mark": mark, "post": (post or "").strip()[:24]}


async def add_item(pid: str, *, sheet: dict[str, Any] | None, tag: str, text: dict[str, str], sub: str = "", fact_id: str | None = None,
                   category: str = "fact", origin: str = "section_fill", action: dict[str, Any] | None = None,
                   fix: dict[str, Any] | None = None, where: str | None = None, why: str | None = None,
                   dedupe: bool = True) -> dict[str, Any]:
    if dedupe:
        existing = await repo.alist("confirm_items", {"proposal_id": pid})
        for it in existing:
            if it.get("status") != "open":
                continue
            if fact_id and it.get("fact_id") == fact_id:
                sid = (sheet or {}).get("id")
                if sid and sid not in (it.get("linked_sheet_ids") or []):
                    it, _ = await repo.amutate("confirm_items", it["id"], lambda x: x.update(
                        {"linked_sheet_ids": [*(x.get("linked_sheet_ids") or []), sid]}))
                return it
            if (not fact_id and it.get("sheet_id") == (sheet or {}).get("id") and it.get("tag") == tag
                    and (it.get("text") or {}).get("mark") == text.get("mark") and it.get("category") == category):
                return it
    doc = {"id": new_id("cfm"), "proposal_id": pid, "category": category, "tag": tag, "sheet_id": (sheet or {}).get("id"),
           "section_key": (sheet or {}).get("section_key"), "fact_id": fact_id, "text": text, "sub": sub, "action": action, "fix": fix,
           "linked_sheet_ids": [(sheet or {}).get("id")] if sheet else [], "where": where, "why": why, "status": "open",
           "resolution": None, "candidates": [], "origin": origin, "evidence": None, "created_iso": config.now_iso()}
    return await repo.aput("confirm_items", doc["id"], doc)


async def items_for_tokens(pid: str, sheet: dict[str, Any], made: list[dict[str, Any]], *, origin: str, reason: str) -> list[str]:
    """새 플레이스홀더 값마다 확인 항목(태그 수치)."""
    out = []
    for m in made:
        f = m["fact"]
        if f.get("status") != "placeholder":
            continue
        title = sheet.get("title") or core.role_name(sheet.get("role"))
        it = await add_item(pid, sheet=sheet, tag=m.get("tag") or "수치", fact_id=f["id"], origin=origin,
                            text=text_parts(m.get("pre", ""), (f.get("placeholder") or m.get("placeholder") or "[00]") + (m.get("mark_unit") or ""),
                                            m.get("post", "")),
                            sub=f"{title} · {m.get('why') or reason}",
                            action={"kind": "button", "label": "시트에서 보기", "target": {"route": core.route(pid, "preview", str(sheet.get("sheet_no") or ""))}},
                            fix={"sentence": [{"text": m.get("pre", "")}, {"input": f["key"], "label": f.get("label")}, {"text": m.get("post", "")}],
                                 "formula": None})
        out.append(it["id"])
    return out


async def close_items_for_fact(pid: str, fact_id: str, *, by: dict[str, Any], value: str | None, evidence: dict[str, Any] | None) -> list[str]:
    closed = []
    for it in await repo.alist("confirm_items", {"proposal_id": pid, "fact_id": fact_id}):
        if it.get("status") == "open":
            await repo.amutate("confirm_items", it["id"], lambda x: x.update({
                "status": "confirmed", "resolution": {"value": value, "evidence": evidence, "by": by, "at": config.now_iso()}}))
            closed.append(it["id"])
    return closed


async def used_in(pid: str) -> dict[str, list[dict[str, Any]]]:
    """fact_id → [{sheet_id, sheet_no, path}]"""
    out: dict[str, list[dict[str, Any]]] = {}
    for sh in await core.sheets_of(pid):
        for fid, path in C.tokens_in(sh.get("content") or {}):
            out.setdefault(fid, []).append({"sheet_id": sh["id"], "sheet_no": sh.get("sheet_no"), "path": path})
    return out


async def sync_items(pid: str) -> None:
    """V9 — 열린 항목이 가리키는 값이 이미 확정됐거나 어느 시트에도 없으면 닫는다."""
    facts = await facts_of(pid)
    uses = await used_in(pid)
    for it in await repo.alist("confirm_items", {"proposal_id": pid}):
        if it.get("status") != "open" or not it.get("fact_id"):
            continue
        f = facts.get(it["fact_id"])
        if f is None or f.get("status") == "confirmed":
            await repo.amutate("confirm_items", it["id"], lambda x: x.update({"status": "confirmed"}))
        elif it["fact_id"] not in uses and it.get("origin") in ("section_fill", "one_click", "check"):
            await repo.amutate("confirm_items", it["id"], lambda x: x.update({"status": "dismissed"}))
