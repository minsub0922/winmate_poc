"""§6.6 반입 — 드래그 앤 드롭 · 팝오버 「현재 작업에 추가」 · 다른 기능에서 보내기(handoff) · IMG4 이미지 자리.

- 팝업 항목(제품 · 솔루션 · 이미지 · 사례): 200 바로 추가 → 영향 시트만 다시 채우는 잡을 이어 돌린다(카드 「업데이트됨」).
- 사이드바 작업: 202 `proposal.import_extract` → `pending_confirm`(DnD_MIExtract) → `:apply` 202 `proposal.import_apply`.
- 보내기(via=handoff): 202 — 추출 뒤 확인 없이 바로 적용(보내는 화면이 이미 골랐다).
- 실행 취소: 반입이 바꾼 시트 · 연결 자료를 되돌린다. 그 뒤 같은 시트를 다른 변경이 바꿨으면 409 UNDO_CONFLICT.
"""
from __future__ import annotations

import re
from typing import Any

from winmate_common.ids import new_id

from .. import clients, config, content as C, core, defs, facts as F, handoff, links as L, plan, repo, templates
from .. import models as M
from ..errors import drop_not_accepted, not_found, section_not_in_type, undo_conflict, unprocessable
from ..graphs import common as G

ITEM_LABEL = {"product": "제품", "solution": "솔루션", "image": "이미지", "case": "유관 사례"}
SNAP_KEYS = ("content", "draft", "template", "status", "content_rev", "sources", "signals", "inferred", "evidence_note")


def _shell(ref: Any) -> str | None:
    """셸 참조 문자열(「kb:model:mdl_…」 · 「img:image:img_…」 · 「ws:item:…」)이면 그대로 남긴다(SourceChip.ref)."""
    if isinstance(ref, str) and ":" in ref:
        return ref
    if isinstance(ref, dict) and isinstance(ref.get("shell_ref") or ref.get("ref"), str):
        r = ref.get("shell_ref") or ref.get("ref")
        return r if ":" in r else None
    return None


def _ref_id(ref: Any) -> str:
    if isinstance(ref, dict):
        return str(ref.get("id") or ref.get("file_id") or ref.get("image_job_id") or ref.get("version_id") or "")
    return str(ref or "")


async def _default_section(p: dict[str, Any], feature: str | None, kind: str | None) -> str:
    keys = core.type_sections(p.get("type"))
    if feature:
        tgt = (defs.WORK_TARGETS.get(feature) or {}).get(p.get("type") or "standard") or []
        for k in tgt:
            if k in keys:
                return k
    if kind:
        cur = p.get("current_section_key")
        if cur in keys and kind in (defs.SECTIONS.get(cur, {}).get("items") or []):
            return cur
        for k in keys:
            if kind in (defs.SECTIONS[k].get("items") or []):
                return k
    return p.get("current_section_key") or (keys[0] if keys else "")


async def _snapshot_sheets(pid: str, key: str | None = None) -> dict[str, dict[str, Any]]:
    shs = await core.sheets_of(pid, section_key=key, include_excluded=True)
    return {s["id"]: {k: s.get(k) for k in SNAP_KEYS} for s in shs}


def _import_view(imp: dict[str, Any], can_undo: bool = False) -> M.Import:
    src = imp.get("source") or {}
    f = src.get("feature") or ""
    title = imp.get("source_title") or src.get("title") or src.get("label") or ""
    intro = (f"{defs.FEATURE_SHORT.get(f, '원')} 작업에서 이 섹션에 쓸 내용을 뽑았습니다. 어느 시트에, 어떤 템플릿으로 들어갈지 함께 표시했어요."
             if f else "")
    items = [M.ImportItem(**it) for it in imp.get("items") or []]
    return M.Import(id=imp["id"], proposal_id=imp["proposal_id"], section_key=imp["section_key"], via=imp.get("via") or "drag_item", source=src,
                    status=imp.get("status") or "extracting", items=items, ex_count=len(items),
                    panel_title=f"{defs.SECTIONS.get(imp['section_key'], {}).get('name', '')} · {title}" if f else title,
                    intro=intro or M.Import.model_fields["intro"].default, label=imp.get("label") or title, note=imp.get("note") or "",
                    toast=imp.get("toast") or "", affected_sheet_ids=imp.get("affected_sheet_ids") or [], new_sheet_ids=imp.get("new_sheet_ids") or [],
                    change_ids=imp.get("change_ids") or [], link_id=imp.get("link_id"), source_route=imp.get("source_route"),
                    job_id=imp.get("job_id"), error=imp.get("error"), can_undo=can_undo, created_by=(imp.get("created_by") or {}).get("name"),
                    created_at=imp.get("created_iso") or "")


async def create_import(pid: str, body: M.ImportRequest) -> M.ImportResult | M.JobAccepted:
    p = await core.load(pid)
    if not p.get("type"):
        from ..errors import type_required
        raise type_required()
    src = body.source
    if src.service == "image" or (src.image_id and not src.kind and not src.feature):
        return await _import_image_work(p, body)
    feature = defs.norm_feature(src.feature) if src.feature else None
    feature = defs.feature_for_ref(feature, src.ref_id)
    kind = src.kind
    key = body.section_key or await _default_section(p, feature, kind)
    include_keys = body.include_keys
    if key not in core.type_sections(p.get("type")):
        # 보내기(via=handoff)인데 그 유형에 없는 섹션이면(SC5 「공간별 가치 제공 시나리오」 → 표준 · 퀵윈, BE6 「조감도」 → 퀵윈 · Solution형)
        # 제안서가 그 기능의 기본 섹션을 고른다(09-scenario §11 Q4 · 10-proposal §10.7). 보낸 쪽 키는 그 섹션 것이 아니라 버린다.
        alt = await _default_section(p, feature, None) if (body.via == "handoff" and feature and not kind) else None
        if not alt or alt not in core.type_sections(p.get("type")):
            raise section_not_in_type(key)
        key, include_keys = alt, None
    d = defs.SECTIONS[key]
    if kind:
        if kind not in (d.get("items") or []):
            raise drop_not_accepted(kind, key)
        return await _import_item(p, key, body)
    ref_id = src.ref_id or ""
    if feature and not ref_id and src.handoff_id:
        if feature in ("spec", "vp"):
            h = await clients.call(feature, "GET", f"/v1/handoffs/{src.handoff_id}", quiet=True)
            ref_id = str((h or {}).get("sheet_id" if feature == "spec" else "vp_id") or "")
        else:
            raise unprocessable("SOURCE_REQUIRED", f"{defs.FEATURE_LABEL.get(feature, feature)} 넘김은 작업 id(ref_id)와 함께 보내 주세요",
                                feature=feature, handoff_id=src.handoff_id)
    if not feature or not ref_id:
        raise unprocessable("SOURCE_REQUIRED", "넣을 작업(feature · ref_id)이나 항목(kind · ref)을 알려 주세요")
    allowed = set(d.get("sidebar") or [])
    if body.via == "handoff":
        allowed |= {f for f, t in defs.WORK_TARGETS.items() if key in (t.get(p.get("type") or "standard") or [])}
    if feature not in allowed:
        raise drop_not_accepted(feature, key)
    imp_id = new_id("imp")
    doc = {"id": imp_id, "proposal_id": pid, "section_key": key, "via": body.via,
           "source": {"feature": feature, "ref_id": ref_id, "version": src.version, "handoff_id": src.handoff_id, "title": src.title},
           "status": "extracting", "items": [], "include_keys": include_keys, "requested_section": body.section_key,
           "created_by": core.actor(), "created_iso": config.now_iso()}
    await repo.aput("imports", imp_id, doc)
    job_id = await G.enqueue("proposal.import_extract", {"proposal_id": pid, "import_id": imp_id},
                             title=f"{defs.FEATURE_LABEL.get(feature, feature)} 반입", ref=pid, project_id=p.get("project_id"))
    await repo.amutate("imports", imp_id, lambda x: x.update({"job_id": job_id}))
    return M.JobAccepted(job_id=job_id, kind="proposal.import_extract", proposal_id=pid, import_id=imp_id, section_key=key)


# ── 팝업 항목 ──────────────────────────────────────────────
async def _store_count(pid: str) -> tuple[str | None, dict[str, Any] | None]:
    f = await F.fact_by_key(pid, "store_count")
    if f and f.get("value") not in (None, ""):
        return str(f["value"]).replace(",", ""), f
    p = await core.load(pid)
    n = ((p.get("ctx") or {}).get("store_count") or "").replace(",", "")
    return (n or None), f


async def _pick_space(p: dict[str, Any], key: str, body: M.ImportRequest, label: str) -> dict[str, Any] | None:
    ctx = p.get("ctx") or {}
    spaces = ctx.get("spaces") or []
    if body.target_sheet_id:
        sh = await core.sheet_doc(p["id"], body.target_sheet_id)
        rk = sh.get("repeat_key") or {}
        sp = next((s for s in spaces if s["key"] == rk.get("ref")), None)
        if sp:
            return sp
    # 제품군의 적합 공간(kb C3) ∩ 섹션 공간 → 없으면 첫 공간
    fam = None
    ref = body.source.ref
    if isinstance(ref, dict) and (ref.get("kb_kind") == "family" or str(ref.get("id") or "").startswith("fam_")):
        fam = ref.get("id")
    if fam:
        c3 = await clients.kb_query("C3", {"family_id": fam})
        fit = [x.get("space_type") or x.get("space") or x.get("id") for x in ((c3 or {}).get("result") or {}).get("spaces") or []
               if isinstance(x, dict)]
        hit = next((s for s in spaces if s["key"] in fit), None)
        if hit:
            return hit
    return spaces[0] if spaces else None


async def _import_item(p: dict[str, Any], key: str, body: M.ImportRequest) -> M.ImportResult:
    pid = p["id"]
    src = body.source
    kind = src.kind or ""
    rid = _ref_id(src.ref) or (src.label or "")
    label = src.label or rid
    before = await _snapshot_sheets(pid)
    imp_id = new_id("imp")
    note = ""
    affected: list[str] = []
    created: list[str] = []
    confirm_ids: list[str] = []
    link = None
    fill_ids: list[str] = []
    if kind == "product":
        sp = await _pick_space(p, key, body, label)
        n, store_fact = await _store_count(pid)
        per = 1
        qty = int(n) * per if n and n.isdigit() else None
        model = label if re.fullmatch(r"[A-Z0-9-]{4,}", label or "") else (src.sub or label)
        link = await L.add_link(pid, feature="kb_product", ref_id=rid, section_key=key, via=body.via, title=label, fetch=False,
                                item={"model": model, "label": label, "sub": src.sub, "per_space": per, "shell_ref": _shell(src.ref)}, qty=qty,
                                space_key=(sp or {}).get("key"))
        await plan.refresh_context(pid)
        await plan.ensure_sections(pid)
        sync = await plan.sync_sheets(pid)
        created = sync.get("created") or []
        shs = await core.sheets_of(pid, section_key=key)
        target = next((s for s in shs if s.get("role") == "PI" and (s.get("repeat_key") or {}).get("ref") == (sp or {}).get("key")), None)
        if key == "spec":
            target = next((s for s in shs if s.get("role") == "SC"), None)
        if target:
            affected = [target["id"]] + [s["id"] for s in shs if s.get("split_of") == target["id"]]
        fill_ids = affected + [c for c in created if c not in affected]
        sheet_name = (target or {}).get("title") or (sp or {}).get("name") or defs.SECTIONS[key]["name"]
        # 수량 = 매장 수 × 공간당 대수 — 파생 값(매장 수가 확정되면 함께 바뀐다, V3)
        if not store_fact:
            store_fact = await F.upsert_fact(pid, key="store_count", label="매장 수", value=f"{int(n):,}" if n and n.isdigit() else None, unit="개",
                                             status="unconfirmed" if n else "placeholder", placeholder="[00]개",
                                             origin={"by": "customer" if n else "agent", "source_ref": "customer.scale_text"})
        await F.upsert_fact(pid, key=f"qty_{re.sub(r'[^0-9a-z]+', '_', model.lower())}", label=f"{label} 수량", unit="대", kind="derived",
                            formula=f"store_count * {per}", status="placeholder", placeholder="[00]대", origin={"by": "agent", "source_ref": "import"})
        if key == "spaceProducts":
            note = f"\"{sheet_name}\" 시트에 배치됨 · 수량 {qty if qty is not None else '[00]'}"
            # 수량 = 매장 수 × 공간당 대수(기본 1, 가정) → 확인 항목 「수량 가정」
            it = await F.add_item(pid, sheet=target, tag="수량 가정", category="fact", origin="import",
                                  text={"pre": f"{label} 수량", "mark": str(qty) if qty is not None else "[00]", "post": f"= 매장 수 × 공간당 {per}대"},
                                  sub=f"{sheet_name} · 공간당 대수는 가정이에요 — 확인해 주세요",
                                  fix={"sentence": [{"text": f"{label} — 전국"}, {"input": "store_count", "label": "매장 수"},
                                                    {"text": f"개 매장 × 공간당 {per}대"}], "formula": f"합계 = 매장 수 × {per}대"},
                                  action={"kind": "button", "label": "시트에서 보기", "target": {"route": core.route(pid, "preview", str((target or {}).get("sheet_no") or ""))}},
                                  dedupe=True)
            confirm_ids.append(it["id"])
            if qty is None and not store_fact:
                f = await F.upsert_fact(pid, key="store_count", label="매장 수", unit="개", status="placeholder", placeholder="[00]개",
                                        origin={"by": "agent", "source_ref": "import"})
                await F.add_item(pid, sheet=target, tag="고객 확인", fact_id=f["id"], origin="import", text={"pre": "전국", "mark": "[00]개", "post": "매장"},
                                 sub=f"{sheet_name} · 매장 수를 아직 받지 못했어요")
        else:
            note = f"\"{sheet_name}\" 시트에 반영됨"
    elif kind == "case":
        link = await L.add_link(pid, feature="kb_case", ref_id=rid, section_key=key, via=body.via, title=label, fetch=False,
                                item={"label": label, "sub": src.sub, "shell_ref": _shell(src.ref)})
        ctx = await plan.refresh_context(pid)
        if not any(c["id"] == rid for c in ctx.get("cases") or []):
            ctx["cases"] = [*(ctx.get("cases") or []), {"id": rid, "title": label, "source": "link", "link_id": link["id"]}]
            await repo.amutate("proposals", pid, lambda x: x.update({"ctx": ctx}))
        sync = await plan.sync_sheets(pid, sections=[key])
        created = sync.get("created") or []
        restored = sync.get("restored") or []
        new = created or restored
        fill_ids = list(new)
        shs = {s["id"]: s for s in await core.sheets_of(pid, section_key=key)}
        title = shs.get(new[0], {}).get("title") if new else f"사례 · {plan.case_short(label)}"
        note = f"새 시트 \"{title}\"이 추가됨"
        affected = list(new)
    elif kind == "solution":
        code = defs.solution_code_of(rid, label)
        if not code:
            raise unprocessable("SOLUTION_UNKNOWN", "이 솔루션은 아직 제안서에 넣을 수 없어요", ref=rid)
        name = defs.SOLUTIONS[code]["name"]
        link = await L.add_link(pid, feature="kb_solution", ref_id=rid, section_key=key, via=body.via, title=name, fetch=False,
                                item={"label": label, "code": code, "shell_ref": _shell(src.ref)})
        await plan.refresh_context(pid)
        await plan.ensure_sections(pid)
        sec = await core.section_doc(pid, "solution") if "solution" in core.type_sections(p.get("type")) else None
        if sec:
            def fn(s: dict[str, Any]) -> None:
                comp = s.get("composition") or []
                row = next((r for r in comp if r["code"] == code), None)
                if row:
                    row["state"] = "on"
                    row["user_set"] = True
                else:
                    comp.insert(0, {"code": code, "state": "on", "user_set": True})
                on = [r for r in comp if r["code"] in defs.SOLUTIONS and r["state"] == "on"]
                for r in comp:
                    if r["code"] == "SA" and not r.get("user_set"):
                        r["state"] = "on" if len(on) >= 2 else "off"
                s["composition"] = comp
            await repo.amutate("sections", sec["id"], fn)
        sync = await plan.sync_sheets(pid)
        created = sync.get("created") or []
        shs = await core.sheets_of(pid)
        if key == "spaceScenario":
            vm = next((s for s in shs if s.get("section_key") == key and s.get("role") == "VM"), None)
            ss = [s for s in shs if s.get("section_key") == key and s.get("role") == "SS"]
            affected = ([vm["id"]] if vm else []) + [s["id"] for s in ss[:1]]
            note = f"\"공간 × 솔루션 맵\"에 열 추가 · {(ss[0].get('title') if ss else '공간')} 시트 갱신"
        else:
            mine = [s["id"] for s in shs if s.get("solution_code") == code and s["section_key"] == "solution"]
            sa = [s["id"] for s in shs if s.get("role") == "SA" and s["section_key"] == "solution"]
            affected = mine + sa
            note = f"{name} 전용 시트 3장(소개 · 구성도 · 공간 시나리오)이 추가됨"
        fill_ids = list(dict.fromkeys(affected + created))
    elif kind == "image":
        shs = await core.sheets_of(pid, section_key=key)
        target = next((s for s in shs if s["id"] == body.target_sheet_id), None) or next(
            (s for s in shs if (s.get("draft") or {}).get("images") is not None or s.get("role") in ("BV", "PI", "SS", "CD", "SXS")), shs[0] if shs else None)
        if not target:
            raise drop_not_accepted("image", key)
        ref = src.ref if isinstance(src.ref, dict) else {"id": rid}
        img = C.image_ref({**ref, "label": label, "kind": ref.get("kind") or ("file" if ref.get("file_id") else "kb_image")})
        link = await L.add_link(pid, feature="kb_image" if img["kind"] == "kb_image" else "file", ref_id=rid, section_key=key, via=body.via,
                                title=label, fetch=False, item={"label": label, "image": img, "shell_ref": _shell(src.ref)})
        await _put_image(pid, target, img, by_user=True, import_id=imp_id)
        affected = [target["id"]]
        note = f"\"{target.get('title')}\" 시트에 반영됨"
    else:
        raise drop_not_accepted(kind, key)
    toast = f"「{label}」 추가됨 · {note}" if kind != "case" else note
    fill_job = None
    if fill_ids:
        from .sections import start_fill
        acc = await start_fill(pid, key, mode="draft", sheet_ids=fill_ids, origin="import", reuse_running=False)
        fill_job = acc.job_id
    doc = {"id": imp_id, "proposal_id": pid, "section_key": key, "via": body.via,
           "source": {"kind": kind, "ref": src.ref, "label": label, "sub": src.sub}, "status": "applied", "items": [], "label": label,
           "note": note, "toast": toast, "affected_sheet_ids": affected, "new_sheet_ids": created, "link_id": (link or {}).get("id"),
           "before": before, "fill_job_id": fill_job, "confirm_item_ids": confirm_ids, "created_by": core.actor(), "created_iso": config.now_iso()}
    await repo.aput("imports", imp_id, doc)
    await core.touch(pid, user_edit=True)
    await core.index(pid)
    chip = M.SourceChipOut(id=(link or {}).get("id") or "", label=label, feature=(link or {}).get("feature") or defs.ITEM_FEATURE.get(kind, kind))
    return M.ImportResult(import_id=imp_id, status="applied", section_key=key, label=label, note=note, toast=toast, affected_sheet_ids=affected,
                          new_sheet_ids=created, source_chip=chip, job_id=fill_job, confirm_item_ids=confirm_ids,
                          route=core.section_route(pid, key))


async def _put_image(pid: str, sheet: dict[str, Any], img: dict[str, Any], *, by_user: bool, import_id: str | None = None,
                     caption: str | None = None) -> dict[str, Any]:
    from .sections import refill_content
    draft = dict(sheet.get("draft") or {})
    imgs = list(draft.get("images") or [])
    if caption:
        img = {**img, "caption_rule": caption}
    imgs = [img] + imgs[1:] if imgs else [img]
    draft["images"] = imgs
    draft.setdefault("title", sheet.get("title") or "")
    content = await refill_content(pid, {**sheet, "draft": draft})
    old = sheet.get("content")

    def fn(x: dict[str, Any]) -> None:
        x["draft"] = draft
        x["content"] = content
        x["content_rev"] = int(x.get("content_rev") or 0) + 1
        x["status"] = "updated" if x.get("status") in ("ready", "updated") else "ready"
        x["sources"] = [*(x.get("sources") or []), {"kind": "image", "ref": img.get("id"), "label": img.get("label") or "이미지",
                                                    "url": img.get("source_url")}][-6:]
    saved, _ = await repo.amutate("sheets", sheet["id"], fn)
    await core.record_change(pid, sheet=saved, where="이미지", kind="content", path="/images/0", from_=core.snippet(old.get("title") if old else ""),
                             to=img.get("label") or img.get("id"), import_id=import_id,
                             summary=f"{int(saved.get('sheet_no') or 0):02d} 이미지 넣음")
    return saved


async def _import_image_work(p: dict[str, Any], body: M.ImportRequest) -> M.ImportResult:
    """IMG4 「제안서에 넣기」 — 이미지 생성 결과를 시트 이미지 칸에(replace_slot) 또는 새 시트로(new_sheet)."""
    pid = p["id"]
    src = body.source
    image_id = src.image_id or _ref_id(src.ref)
    version_id = src.version_id or (str(src.version) if src.version else None)
    snap = await handoff.fetch("image", image_id, proposal_type=p.get("type"), version=version_id)
    asset = ((snap or {}).get("assets") or [{}])[0] if snap else {"kind": "image_job", "id": image_id, "rights": "generated",
                                                                    "caption_rule": "생성 이미지"}
    if version_id:
        asset = {**asset, "version_id": version_id}
    label = ((snap or {}).get("source") or {}).get("title") or src.label or "생성 이미지"
    tgt = body.target or M.ImportTarget()
    before = await _snapshot_sheets(pid)
    imp_id = new_id("imp")
    created: list[str] = []
    if tgt.mode == "new_sheet" or not (tgt.sheet_id or body.target_sheet_id):
        keys = core.type_sections(p.get("type"))
        key = body.section_key if body.section_key in keys else next((k for k in ("birdseye", "spaceProducts", "spaceScenario") if k in keys), keys[0])
        doc = {"id": new_id("sht"), "proposal_id": pid, "section_key": key, "ident": f"{key}|BV|img|{image_id}", "order": 999, "sheet_no": 0,
               "role": "BV", "solution_code": None, "repeat_key": {"kind": "image", "ref": image_id, "label": label}, "title": label,
               "template": {"code": None, "mode": "auto"}, "content": {}, "draft": {"title": label}, "signals": {"photos": 1}, "sources": [],
               "status": "need", "origin": "user", "inferred": False, "content_rev": 0, "extra": True}
        cat = await clients.export_catalog()
        templates.apply_recommendation(doc, templates.recommend(doc, p, cat))
        await repo.aput("sheets", doc["id"], doc)
        await plan.renumber(pid)
        created = [doc["id"]]
        sheet = await core.sheet_doc(pid, doc["id"])
    else:
        sheet = await core.sheet_doc(pid, tgt.sheet_id or body.target_sheet_id or "")
        key = sheet["section_key"]
    img = C.image_ref({**asset, "label": label})
    link = await L.add_link(pid, feature="image", ref_id=image_id, section_key=key, via=body.via, version=None, title=label, fetch=False,
                            item={"image": img, "version_id": version_id})
    saved = await _put_image(pid, sheet, img, by_user=True, import_id=imp_id, caption=body.caption)
    await handoff.register_usage("image", image_id, proposal=p, label=saved.get("title") or "", version=version_id, sheet_ref=f"{pid}:{saved['id']}")
    note = f"\"{saved.get('title')}\" 시트에 넣었어요"
    doc2 = {"id": imp_id, "proposal_id": pid, "section_key": key, "via": body.via,
            "source": {"service": "image", "image_id": image_id, "version_id": version_id, "label": label}, "status": "applied", "label": label,
            "note": note, "toast": f"「{label}」 추가됨 · {note}", "affected_sheet_ids": [saved["id"]], "new_sheet_ids": created,
            "link_id": link["id"], "before": before, "created_by": core.actor(), "created_iso": config.now_iso(),
            "usage_ref": f"{pid}:{saved['id']}"}
    await repo.aput("imports", imp_id, doc2)
    await core.touch(pid, user_edit=True)
    await core.index(pid)
    return M.ImportResult(import_id=imp_id, status="applied", section_key=key, label=label, note=note, toast=doc2["toast"],
                          affected_sheet_ids=[saved["id"]], new_sheet_ids=created,
                          source_chip=M.SourceChipOut(id=link["id"], label=label, feature="image"), route=core.route(pid))


# ── 읽기 · 적용 · 실행 취소 ─────────────────────────────────
async def _undo_conflict(pid: str, imp: dict[str, Any]) -> bool:
    ids = set(imp.get("affected_sheet_ids") or []) | set(imp.get("new_sheet_ids") or [])
    if not ids:
        return False
    since = imp.get("applied_iso") or imp.get("created_iso") or ""
    mine_jobs = {imp.get("fill_job_id"), imp.get("job_id")} - {None}
    for c in await repo.alist("changes", {"proposal_id": pid}):
        if c.get("sheet_id") not in ids or (c.get("ts") or "") < since:
            continue
        if c.get("import_id") == imp["id"] or c.get("job_id") in mine_jobs or c.get("reverted_by"):
            continue
        return True
    return False


async def get_import(pid: str, imp_id: str) -> M.Import:
    await core.load(pid)
    imp = await repo.aget("imports", imp_id)
    if not imp or imp.get("proposal_id") != pid:
        raise not_found("반입", imp_id, "IMPORT_NOT_FOUND")
    can = imp.get("status") == "applied" and not await _undo_conflict(pid, imp)
    return _import_view(imp, can_undo=can)


async def apply_import(pid: str, imp_id: str, body: M.ImportApply) -> M.JobAccepted:
    p = await core.load(pid)
    imp = await repo.aget("imports", imp_id)
    if not imp or imp.get("proposal_id") != pid:
        raise not_found("반입", imp_id, "IMPORT_NOT_FOUND")
    if imp.get("status") not in ("pending_confirm", "failed"):
        raise unprocessable("IMPORT_NOT_PENDING", "이미 반영했거나 아직 뽑는 중이에요", status=imp.get("status"))
    known = {it["key"] for it in imp.get("items") or []}
    bad = [k for k in body.keys if k not in known]
    if bad:
        raise unprocessable("IMPORT_KEY_UNKNOWN", "추출 목록에 없는 항목이에요", keys=bad)
    job_id = await G.enqueue("proposal.import_apply", {"proposal_id": pid, "import_id": imp_id, "keys": body.keys},
                             title="반입 반영", ref=pid, project_id=p.get("project_id"))
    await repo.amutate("imports", imp_id, lambda x: x.update({"status": "applying", "job_id": job_id}))
    return M.JobAccepted(job_id=job_id, kind="proposal.import_apply", proposal_id=pid, import_id=imp_id, section_key=imp["section_key"])


async def undo_import(pid: str, imp_id: str) -> M.UndoResult:
    await core.load(pid)
    imp = await repo.aget("imports", imp_id)
    if not imp or imp.get("proposal_id") != pid:
        raise not_found("반입", imp_id, "IMPORT_NOT_FOUND")
    if imp.get("status") != "applied":
        raise unprocessable("IMPORT_NOT_APPLIED", "반영된 반입만 되돌릴 수 있어요", status=imp.get("status"))
    if await _undo_conflict(pid, imp):
        raise undo_conflict()
    before = imp.get("before") or {}
    restored = []
    removed_sheets = []
    for sid in imp.get("new_sheet_ids") or []:
        if sid not in before:
            await repo.adelete("sheets", sid)
            removed_sheets.append(sid)
    for sid in imp.get("affected_sheet_ids") or []:
        snap = before.get(sid)
        if not snap or sid in removed_sheets:
            continue
        await repo.amutate("sheets", sid, lambda x, snap=snap: x.update({**snap, "content_rev": int(x.get("content_rev") or 0) + 1}))
        restored.append(sid)
    removed_links = []
    for link_id in list(dict.fromkeys([*(imp.get("link_ids") or []), *([imp["link_id"]] if imp.get("link_id") else [])])):
        ln = await repo.aget("links", link_id)
        if ln:
            await repo.amutate("links", ln["id"], lambda x: x.update({"status": "removed"}))
            removed_links.append(ln["id"])
            if ln.get("feature") == "image" and imp.get("usage_ref"):
                await handoff.unregister_usage("image", ln.get("ref_id") or "", proposal_id=pid, sheet_ref=imp["usage_ref"])
            elif ln.get("feature") in ("birdseye", "scenario", "vp", "spec") and ln.get("ref_id"):
                # 같은 원본을 아직 쓰는 연결이 없을 때만 원본 쪽 표시를 거둔다(VP 「연결된 제안서」 · Spec 연결은 통합)
                others = [x for x in await repo.alist("links", {"proposal_id": pid}) if x["id"] != ln["id"] and x.get("feature") == ln.get("feature")
                          and x.get("ref_id") == ln.get("ref_id") and x.get("status") != "removed"]
                if not others:
                    await handoff.unregister_usage(ln.get("feature") or "", ln.get("ref_id") or "", proposal_id=pid)
    for cid in imp.get("confirm_item_ids") or []:
        await repo.amutate("confirm_items", cid, lambda x: x.update({"status": "dismissed"}))
    src = imp.get("source") or {}
    if src.get("kind") in ("product", "case", "solution"):
        await plan.refresh_context(pid)
        if src.get("kind") == "solution":
            sec = next((s for s in await core.sections_of(pid) if s["key"] == "solution"), None)
            code = defs.solution_code_of(_ref_id(src.get("ref")), src.get("label"))
            if sec and code:
                def fn(s: dict[str, Any]) -> None:
                    for r in s.get("composition") or []:
                        if r["code"] == code:
                            r["state"] = "off"
                await repo.amutate("sections", sec["id"], fn)
        sync = await plan.sync_sheets(pid)
        removed_sheets += [x for x in sync.get("excluded") or [] if x in (imp.get("new_sheet_ids") or [])]
    await plan.renumber(pid)
    await repo.amutate("imports", imp_id, lambda x: x.update({"status": "undone", "undone_iso": config.now_iso()}))
    await core.record_change(pid, sheet=None, where="반입", kind="source", path=f"/imports/{imp_id}", from_=imp.get("label"), to=None,
                             summary=f"실행 취소 · {imp.get('label') or ''}", import_id=imp_id)
    await F.sync_items(pid)
    await core.touch(pid, user_edit=True)
    await core.index(pid)
    return M.UndoResult(import_id=imp_id, status="undone", removed_link_ids=removed_links, restored_sheet_ids=restored,
                        removed_sheet_ids=removed_sheets)


# ── IMG4 이미지 자리 ───────────────────────────────────────
SCENE_WORDS = ("카운터", "메뉴보드", "쇼윈도", "외부", "대기", "주문", "픽업", "로비", "객실", "교실", "병실", "매장")


async def image_slots(pid: str, *, image_ref: str | None, image_version: str | None, image_id: str | None) -> M.ImageSlots:
    p = await core.load(pid)
    scene_text = ""
    if image_id or image_ref:
        img = await clients.call("image", "GET", f"/v1/images/{image_id or image_ref}", quiet=True)
        scene = (img or {}).get("scene") or {}
        scene_text = " ".join(str(x) for x in (scene.get("space"), scene.get("label"), (img or {}).get("title")) if x)
    out = []
    keys = core.type_sections(p.get("type"))
    for sh in await core.sheets_of(pid):
        if sh["section_key"] not in keys:
            continue
        code = (sh.get("template") or {}).get("code")
        detail = await clients.export_template_detail(code, (sh.get("template") or {}).get("product_count")) if code else None
        slots = [s for s in ((detail or {}).get("slot_schema") or {}).get("slots") or []
                 if s.get("type") == "image" or any(f.get("key") == "image" for f in s.get("fields") or [])]
        if not slots:
            continue
        name = sh.get("title") or ""
        sec_name = defs.SECTIONS[sh["section_key"]]["name"]
        rec = bool(scene_text) and any(w in name and w in scene_text for w in SCENE_WORDS)
        out.append(M.ImageSlot(sheet_id=sh["id"], sheet_no=int(sh.get("sheet_no") or 0), name=name, sheet_title=name,
                               section=f"{sec_name} · " + ("같은 공간 장면" if rec else core.role_name(sh.get("role"))), section_name=sec_name,
                               section_key=sh["section_key"], slot=slots[0]["id"], slots=sum(int(s.get("boxes") or 1) for s in slots),
                               recommended=rec, preview_url=core.sheet_thumb(sh)))
    if out and not any(x.recommended for x in out):
        out[0].recommended = True
    return M.ImageSlots(proposal_id=pid, proposal_title=core.title_display(p), image_ref=image_ref or image_id, sheets=out, slots=out)
