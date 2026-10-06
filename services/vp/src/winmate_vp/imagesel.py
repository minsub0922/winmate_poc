"""이미지 칸 채우기(05-vp.md §4.16) — 공식 실사 우선 · 모든 이미지에 출처 메타데이터(srcRule).

출처 단계: ① 고객 현장 사진(공간 칸만) ② 공식 제품 컷 ③ 설치 사례 ④ 솔루션 화면 ⑤ 일러스트(Prod).
모드: 정확 모델 · 공식 화면 = 자동 / 설치 사례 · 같은 계열 · 유사 모델 · 일러스트 · 고객 사진 = 확인 권장.
"""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.ai import ai
from winmate_common.ids import new_id, now_iso
from winmate_common.platform import file_meta

from . import catalog, kbx, repo
from .decide import josa

log = logging.getLogger("winmate.vp.images")

TIER_LABEL = {"customer": "고객 현장 사진", "cut": "공식 제품 컷", "case": "설치 사례", "ui": "솔루션 화면", "illust": "일러스트"}
CAPTION = {"cut": "예시 사진(삼성 공식 이미지)", "ui": "예시 사진(삼성 공식 이미지)", "case": "도입사례 사진", "illust": "생성 이미지",
           "customer": "고객 제공 사진"}


def kb_asset(image_id: str) -> dict[str, Any]:
    return {"source": "kb", "asset_id": image_id, "file_id": None, "std_url": f"/api/kb/v1/images/{image_id}/file",
            "thumb_url": f"/api/kb/v1/images/{image_id}/thumb"}


def file_asset(file_id: str, source: str = "file") -> dict[str, Any]:
    return {"source": source, "asset_id": None, "file_id": file_id, "std_url": f"/api/files/v1/files/{file_id}/content",
            "thumb_url": f"/api/files/v1/files/{file_id}/thumbnail"}


def asset_key(asset: dict[str, Any] | None) -> str | None:
    if not asset:
        return None
    return f"kb:image:{asset['asset_id']}" if asset.get("asset_id") else (f"file:{asset.get('file_id')}" if asset.get("file_id") else None)


def _dims(d: dict[str, Any] | None) -> dict[str, Any] | None:
    if not d:
        return None
    return {"w": int(d.get("width") or d.get("w") or 0), "h": int(d.get("height") or d.get("h") or 0), "format": d.get("format") or "",
            "bytes": d.get("bytes")}


async def meta_from_kb(image_id: str, tier: str) -> dict[str, Any]:
    m = await kbx.image_meta(image_id) or {}
    n = await repo.usage_count(f"kb:image:{image_id}")
    kind = {"case": "도입사례", "ui": "솔루션", "cut": "제품"}.get(tier, "제품")
    sp = m.get("source_page") or {}
    stored = _dims(m.get("stored")) or _dims(m.get("original")) or {"w": 0, "h": 0, "format": "", "bytes": None}
    return {
        "title": m.get("title") or m.get("label") or image_id, "kind": kind,
        "source_page": {"title": sp.get("title") or sp.get("label") or "", "url": sp.get("url") or ""} if sp else None,
        "original_file_url": m.get("original_url"), "original": _dims(m.get("original")), "stored": stored,
        "posted_at": (m.get("posted") or {}).get("date"), "collected_at": m.get("collected_at") or now_iso(),
        "method": "공식 페이지에서 수집", "rights": m.get("usage_note") or ("“도입사례 사진” 표기 필수 · 대외 사용 범위 확인 필요"
                                                                 if tier == "case" else "삼성전자 저작물 · 대외 사용 범위 확인 필요"),
        "caption_rule": m.get("caption_rule") or CAPTION.get(tier, ""), "usage_history": {"count": n, "label": f"Winmate 제안서 {n}건"},
        "alt_on_source": m.get("alt") or None, "grade_hint": m.get("grade"), "tier_source": "T3_case" if tier == "case" else "T2_official",
    }


async def meta_from_file(file_id: str, *, kind: str, title: str, method: str) -> dict[str, Any]:
    try:
        fm = await file_meta(file_id)
    except Exception:  # noqa: BLE001
        fm = {}
    n = await repo.usage_count(f"file:{file_id}")
    gen = kind == "생성"
    fmt = (fm.get("mime") or "image/png").split("/")[-1].upper().replace("JPEG", "JPG")
    md = fm.get("meta") or {}
    return {
        "title": title, "kind": kind, "source_page": None, "original_file_url": None, "original": None,
        "stored": {"w": int(md.get("width") or 0), "h": int(md.get("height") or 0), "format": fmt, "bytes": fm.get("size")},
        "posted_at": None, "collected_at": fm.get("created_at") or now_iso(), "method": method,
        "rights": "생성 이미지 · 실제 모습과 다를 수 있어요" if gen else "고객 제공 · 고객 확인 전 외부 사용 불가",
        "caption_rule": "생성 이미지" if gen else "고객 제공 사진", "usage_history": {"count": n, "label": f"Winmate 제안서 {n}건"},
        "alt_on_source": None, "grade_hint": None, "tier_source": "T6_generated" if gen else "customer",
    }


# ── 칸 정의 ────────────────────────────────────────────────

def _first_ref(refs: list[dict[str, Any]]) -> dict[str, Any] | None:
    for kind in ("model", "family", "solution", "category"):
        for r in refs or []:
            if r.get("kind") == kind:
                return r
    return None


def slot_specs(doc: dict[str, Any], sheet: dict[str, Any]) -> list[dict[str, Any]]:
    e = catalog.entry(sheet["layout"]["code"]) or {}
    sd = e.get("slots")
    if not sd:
        return []
    disp = sheet["layout"]["display"]
    c = sheet.get("content") or {}
    per = sd.get("per")
    lab = sd.get("label", "칸 {i}")
    out: list[dict[str, Any]] = []
    prods = [r for m in doc.get("materials") or [] if not m.get("excluded") for r in m.get("product_refs") or []]

    def add(i: int, label: str, refs: list[dict[str, Any]], kind_hint: str | None = None, name: str | None = None) -> None:
        ref = _first_ref(refs)
        subj_kind = kind_hint or ("solution" if ref and ref.get("kind") == "solution" else ("product" if ref else sd.get("subject", "product")))
        if subj_kind == "product" and not ref:
            subj_kind = "space" if sd.get("subject") == "space" else "product"
        out.append({"code": f"{disp} · {lab.format(i=i, side='전' if i == 1 else '후')}", "label": label, "idx": i,
                    "subject": {"kind": subj_kind, "refs": [ref] if ref else [], "label": name or (ref or {}).get("name") or label}})
    if per == "pillar":
        for i, p in enumerate(c.get("pillars") or [], 1):
            add(i, p.get("title", ""), p.get("product_refs") or [])
    elif per == "stakeholder":
        for i, s in enumerate(c.get("stakeholders") or [], 1):
            add(i, s.get("role", ""), s.get("product_refs") or [])
    elif per in ("pair", "question"):
        for i, p in enumerate(c.get("pairs") or [], 1):
            add(i, p.get("challenge", ""), [p["product"]] if p.get("product") else [])
    elif per == "product":
        seen = []
        for r in prods:
            if r not in seen:
                seen.append(r)
        for i, r in enumerate(seen[: int(sd.get("max", 4))], 1):
            add(i, r.get("name", ""), [r])
    elif per == "one":
        refs = []
        for p in c.get("pillars") or []:
            refs += p.get("product_refs") or []
        refs = refs or prods
        label = (c.get("one_liner") or {}).get("statement") or sheet.get("title") or "제품"
        if sd.get("subject") in ("space", "customer", "case"):
            add(1, label, [], kind_hint=sd["subject"])
        else:
            add(1, label[:30], refs)
    elif per == "first":
        ch = (c.get("challenges") or [{}])[0]
        add(1, ch.get("title") or sheet.get("title") or "과제", [], kind_hint="space", name=ch.get("title"))
    elif per == "before_after":
        add(1, "도입 전", [], kind_hint="space")
        add(2, "도입 후", [], kind_hint="space")
    elif per == "space":
        for i, sp in enumerate(((doc.get("facts") or {}).get("spaces") or [])[: int(sd.get("max", 4))], 1):
            add(i, sp.get("name", ""), [], kind_hint="space", name=sp.get("name"))
    for s in out:
        if s["subject"]["kind"] == "space":
            sp = ((doc.get("facts") or {}).get("spaces") or [None])[0]
            s["subject"]["space_type_id"] = (sp or {}).get("id") if isinstance(sp, dict) else None
    return out


# ── 매칭 ──────────────────────────────────────────────────

def _slot(sheet_id: str, spec: dict[str, Any], tier: str, asset: dict[str, Any] | None, *, fit: str, why: str, mode: str,
          flags: dict[str, Any], meta: dict[str, Any] | None, request_draft: str | None = None, extra: bool = False) -> dict[str, Any]:
    return {"id": new_id("vis"), "sheet_id": sheet_id, "code": spec["code"], "label": spec["label"], "subject": spec["subject"],
            "tier": tier, "tier_label": TIER_LABEL[tier], "asset": asset, "fit": fit, "focal": None, "why": why, "mode": mode,
            "flags": flags, "meta": meta, "request_draft": request_draft, "extra": extra}


async def illustration(label: str, *, product: str | None = None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    prompt = (f"삼성 B2B 제안서 시트용 일러스트 — 주제 '{label}'" + (f", 제품 {product}" if product else "")
              + ". Prod 톤 · 평면 일러스트 · 글자와 로고 없음 · 흰 배경 · 파란 포인트색(#1428a0).")
    try:
        res = await ai().generate_image("vp.illustration", prompt, aspect="16:9", n=1, confidential=True,
                                        metadata={"feature": "VP", "purpose": "image_slot"})
    except Exception as exc:  # noqa: BLE001 — 생성이 막혀도 칸은 남긴다(일러스트 자리)
        log.warning("일러스트 생성 실패: %s", exc)
        return None, None
    imgs = res.get("images") or []
    first = imgs[0] if imgs and isinstance(imgs[0], dict) else {}
    fid = first.get("file_id")
    if not fid:
        return None, None
    model = (res.get("model") or res.get("provider") or "T2I")
    meta = await meta_from_file(fid, kind="생성", title=label, method=f"생성 이미지 · {model} · {now_iso()[:10]}")
    if first.get("width"):
        meta["stored"].update({"w": int(first["width"]), "h": int(first.get("height") or 0),
                               "format": (first.get("mime") or "image/png").split("/")[-1].upper()})
    return file_asset(fid, "generated"), meta


def _subject_name(spec: dict[str, Any]) -> str:
    return spec["subject"].get("label") or spec["label"]


async def match(doc: dict[str, Any], sheet_id: str, spec: dict[str, Any], ctx: dict[str, Any], *, style: str | None = None,
                extra: bool = False) -> dict[str, Any]:
    """칸 하나 채우기. ctx: {solutions: kb_id→{id,name}, customer_photos: [...], vertical, case_photo: {...}}."""
    subj = spec["subject"]
    ref = (subj.get("refs") or [None])[0]
    customer = doc.get("customer_name") or "고객"
    if style == "illustration":
        asset, meta = await illustration(spec["label"], product=(ref or {}).get("name"))
        return _slot(sheet_id, spec, "illust", asset, fit="cover", why="실사를 모두 빼고 같은 톤의 일러스트로", mode="check",
                     flags={"generated": True}, meta=meta, extra=extra)
    if subj["kind"] in ("space", "customer"):
        photo = next((p for p in ctx.get("customer_photos") or [] if p.get("file_id")), None)
        if photo:
            meta = await meta_from_file(photo["file_id"], kind="고객 사진", title=photo.get("filename") or "고객 매장 사진",
                                        method=f"고객 업로드 · {photo.get('filename') or photo['file_id']}")
            return _slot(sheet_id, spec, "customer", file_asset(photo["file_id"]), fit="cover", why="고객이 준 현장 사진 · 고객 확인 전 외부 사용 불가",
                         mode="check", flags={"customer_unconfirmed": True}, meta=meta, extra=extra)
        if subj["kind"] == "space" and subj.get("space_type_id"):
            imgs, level = await kbx.space_images(subj["space_type_id"], vertical=ctx.get("vertical"))
            pick = next((i for i in imgs if str(i.get("grade_hint") or "").startswith("A") and i.get("has_local", True)), None)
            if pick:
                meta = await meta_from_kb(pick["id"], "case")
                return _slot(sheet_id, spec, "case", kb_asset(pick["id"]), fit="cover",
                             why="같은 공간의 공식 사진 · 다른 고객사 공간 → 외부 제출 전 인용 확인", mode="check",
                             flags={"other_brand_visible": True, "case_caption_required": True, "fallback_level": level}, meta=meta, extra=extra)
        asset, meta = await illustration(spec["label"])
        return _slot(sheet_id, spec, "illust", asset, fit="cover", why="고객 매장 사진 없음 → 일러스트 · 사진 요청 초안 준비, 받으면 자동 교체",
                     mode="check", flags={"generated": True}, meta=meta,
                     request_draft=f"{customer} 담당자께 — '{spec['label']}' 칸에 넣을 현재 매장 사진을 보내 주시면, 일러스트 대신 실제 모습으로 바꿔 드리겠습니다.",
                     extra=extra)
    if subj["kind"] == "case":
        cp = ctx.get("case_photo")
        if cp:
            meta = await meta_from_kb(cp["image_id"], "case")
            return _slot(sheet_id, spec, "case", kb_asset(cp["image_id"]), fit="cover",
                         why=f"같은 {ctx.get('industry_cell') or '업종'} 업종 · 다른 고객사 브랜드 노출 → 외부 제출 전 인용 확인", mode="check",
                         flags={"other_brand_visible": True, "case_caption_required": True}, meta=meta, extra=extra)
        asset, meta = await illustration(spec["label"])
        return _slot(sheet_id, spec, "illust", asset, fit="cover", why="같은 업종 사례 사진이 없어 일러스트로", mode="check",
                     flags={"generated": True}, meta=meta, extra=extra)
    if ref and ref.get("kind") == "solution":
        sol = (ctx.get("solutions") or {}).get(ref["id"]) or {"id": ref["id"].replace("sol_", ""), "name": ref.get("name")}
        imgs = await kbx.solution_images(sol["id"])
        official = [i for i in imgs if i.get("group") == "official" and i.get("has_local", True)]
        if official:
            pick = official[0]
            meta = await meta_from_kb(pick["id"], "ui")
            nm = sol.get("name") or ref.get("name") or "솔루션"
            return _slot(sheet_id, spec, "ui", kb_asset(pick["id"]), fit="contain" if spec["idx"] % 2 == 1 else "contain",
                         why=f"{nm}{josa(nm, '이', '가')} 만드는 가치 · 공개 화면이라 \"실제 데이터 아님\" 표시", mode="auto",
                         flags={"not_real_data": True}, meta=meta, extra=extra)
        case = [i for i in imgs if i.get("group") == "case"] or await kbx.subject_images("solution", ref["id"], limit=4)
        if case:
            pick = case[0]
            meta = await meta_from_kb(pick["id"], "case")
            return _slot(sheet_id, spec, "case", kb_asset(pick["id"]), fit="cover",
                         why=f"{ref.get('name')} 설치 사례 · 다른 고객사 브랜드 노출 → 외부 제출 전 인용 확인", mode="check",
                         flags={"other_brand_visible": True, "case_caption_required": True}, meta=meta, extra=extra)
    if ref and ref.get("kind") in ("family", "model"):
        fam = ref.get("family_id") or (ref["id"] if ref["kind"] == "family" else None)
        imgs = await kbx.product_images(fam) if fam else []
        if imgs:
            pick = imgs[0]
            meta = await meta_from_kb(pick["id"], "cut")
            nm = ref.get("name") or "제안 제품"
            return _slot(sheet_id, spec, "cut", kb_asset(pick["id"]), fit="contain",
                         why=f"제안 모델 {nm}{josa(nm, '과', '와')} 같은 모델의 공식 컷", mode="auto", flags={}, meta=meta, extra=extra)
        case = await kbx.subject_images(ref["kind"], ref["id"], limit=4)
        if case:
            pick = case[0]
            meta = await meta_from_kb(pick["id"], "case")
            return _slot(sheet_id, spec, "case", kb_asset(pick["id"]), fit="cover",
                         why=f"{ref.get('name')} 설치 사례 · 다른 고객사 브랜드 노출 → 외부 제출 전 인용 확인", mode="check",
                         flags={"other_brand_visible": True, "case_caption_required": True}, meta=meta, extra=extra)
    asset, meta = await illustration(spec["label"], product=(ref or {}).get("name"))
    return _slot(sheet_id, spec, "illust", asset, fit="cover", why="공식 실사가 없어 일러스트 · 실사를 찾으면 바꿔요", mode="check",
                 flags={"generated": True}, meta=meta, extra=extra)


async def candidates(doc: dict[str, Any], slot: dict[str, Any], ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """바꿀 수 있는 후보 최대 4(지금 것 포함)."""
    out: list[dict[str, Any]] = []
    cur = slot.get("asset")
    if cur:
        out.append({"asset": cur, "name": (slot.get("meta") or {}).get("title") or slot["label"], "tier": slot["tier"],
                    "tier_label": slot["tier_label"], "current": True, "mode": slot["mode"], "meta": slot.get("meta")})
    subj = slot.get("subject") or {}
    ref = (subj.get("refs") or [None])[0]
    seen = {asset_key(cur)} if cur else set()
    pool: list[tuple[str, dict[str, Any]]] = []
    if ref and ref.get("kind") == "solution":
        sol = (ctx.get("solutions") or {}).get(ref["id"]) or {"id": ref["id"].replace("sol_", "")}
        for i in await kbx.solution_images(sol["id"]):
            pool.append(("ui" if i.get("group") == "official" else "case", i))
    elif ref and ref.get("kind") in ("family", "model"):
        fam = ref.get("family_id") or (ref["id"] if ref["kind"] == "family" else None)
        for i in (await kbx.product_images(fam) if fam else []):
            pool.append(("cut", i))
        for i in await kbx.subject_images(ref["kind"], ref["id"], limit=4):
            pool.append(("case", i))
    elif subj.get("space_type_id"):
        imgs, _ = await kbx.space_images(subj["space_type_id"], vertical=ctx.get("vertical"))
        pool += [("case", i) for i in imgs]
    for tier, im in pool:
        if len(out) >= 3:
            break
        a = kb_asset(im["id"])
        if asset_key(a) in seen or not im.get("has_local", True):
            continue
        seen.add(asset_key(a))
        meta = await meta_from_kb(im["id"], tier)
        out.append({"asset": a, "name": meta.get("title") or im["id"], "tier": tier,
                    "tier_label": TIER_LABEL[tier] + (" · 확인 권장" if tier == "case" else ""), "current": False,
                    "mode": "check" if tier == "case" else "auto", "meta": meta})
    if slot.get("tier") != "illust":
        out.append({"asset": None, "name": f"{_subject_name(slot)} 일러스트", "tier": "illust", "tier_label": "일러스트",
                    "current": False, "mode": "check", "meta": None})
    return out[:4]


async def replace(slot: dict[str, Any], asset: dict[str, Any], *, tier: str | None = None) -> dict[str, Any]:
    """칸 자산 교체 — 메타 · 플래그 · 모드 재계산."""
    s = dict(slot)
    if asset.get("source") == "kb" and asset.get("asset_id"):
        im = await kbx.image_meta(asset["asset_id"]) or {}
        t = tier or ("case" if im.get("kind") == "case" or im.get("rights") == "customer_case" else
                     ("ui" if im.get("kind") == "solution" else "cut"))
        s["asset"] = kb_asset(asset["asset_id"])
        s["meta"] = await meta_from_kb(asset["asset_id"], t)
        s["tier"] = t
        s["tier_label"] = TIER_LABEL[t]
        if t == "case":
            s["mode"], s["flags"] = "check", {"other_brand_visible": True, "case_caption_required": True}
            s["why"] = "설치 사례 사진 · 다른 고객사 브랜드 노출 → 외부 제출 전 인용 확인"
            s["fit"] = "cover"
        elif t == "ui":
            s["mode"], s["flags"] = "auto", {"not_real_data": True}
            s["why"] = "공식 솔루션 화면 · \"실제 데이터 아님\" 표시"
            s["fit"] = "contain"
        else:
            s["mode"], s["flags"] = "auto", {}
            s["why"] = "공식 제품 컷"
            s["fit"] = "contain"
    elif asset.get("file_id"):
        gen = asset.get("source") == "generated"
        s["asset"] = file_asset(asset["file_id"], "generated" if gen else "file")
        s["meta"] = await meta_from_file(asset["file_id"], kind="생성" if gen else "고객 사진", title=slot["label"],
                                         method="생성 이미지" if gen else f"고객 업로드 · {asset['file_id']}")
        s["tier"] = "illust" if gen else "customer"
        s["tier_label"] = TIER_LABEL[s["tier"]]
        s["mode"] = "check"
        s["flags"] = {"generated": True} if gen else {"customer_unconfirmed": True}
        s["why"] = "생성 이미지" if gen else "고객이 준 현장 사진 · 고객 확인 전 외부 사용 불가"
        s["fit"] = "cover"
    return s


def meta_complete(slot: dict[str, Any]) -> bool:
    """§7.7-5 — 자산이 있으면 메타 필수 필드가 모두 있어야 한다."""
    if not slot.get("asset"):
        return True
    m = slot.get("meta") or {}
    if not (m.get("stored") and m.get("collected_at") and m.get("rights") and m.get("usage_history")):
        return False
    if slot.get("tier") in ("cut", "ui", "case"):
        return bool((m.get("source_page") or {}).get("url")) and bool(m.get("original_file_url"))
    return True
