"""작업(work) 서비스 로직 — 만들기 · 고치기 · prefill(R1) · 상태 · 경로 · workspace 색인(07-image §3.4 · §3.5 · §5.4)."""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.context import current_user
from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso
from winmate_common.platform import register_item

from . import config, kbapi, llm, texts, views
from .store import repo

log = logging.getLogger("winmate.image.service")

_project_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}


def default_conditions(kind: str) -> dict[str, Any]:
    return {"products": [], "style": "photo", "aspect": "16:9", "count": 4, "no_products": kind == "background"}


def default_composite() -> dict[str, Any]:
    return {"active_photo_id": None, "groups": [], "ref_dims": {"counter_width_mm": None, "install_height_mm": None},
            "options": {"perspective_light_match": True, "screen_menu": True}, "scale": {"mm_per_px": None, "method": "none"},
            "measures": []}


async def project_info(project_id: str | None) -> dict[str, Any] | None:
    if not project_id:
        return None
    hit = _project_cache.get(project_id)
    if hit and time.time() - hit[0] < 120:
        return hit[1]
    try:
        proj = await ServiceClient("workspace").get(f"/v1/projects/{project_id}")
    except Exception as exc:  # noqa: BLE001
        log.info("프로젝트를 읽지 못했습니다 %s: %s", project_id, exc)
        proj = None
    _project_cache[project_id] = (time.time(), proj)
    return proj


async def get_work(work_id: str, *, owner_check: bool = False) -> dict[str, Any]:
    doc = await repo().get("works", work_id)
    if doc is None or doc.get("deleted_at"):
        raise not_found("이미지 작업", work_id)
    return doc


async def runs_of(work_id: str) -> list[dict[str, Any]]:
    runs = await repo().all("runs", where={"work_id": work_id}, order_by="created_at")
    return runs


async def in_proposal(work_id: str) -> bool:
    imgs = await repo().all("images", where={"work_id": work_id})
    for im in imgs:
        if await repo().count("usages", where={"image_id": im["id"]}) and any(
                u.get("service") == "proposal" for u in await repo().all("usages", where={"image_id": im["id"]})):
            return True
    return False


async def work_thumb(work: dict[str, Any]) -> str | None:
    """대표 시안 최신 버전 썸네일(선택 시안 → 첫 완료 시안)."""
    img = None
    if work.get("selected_image_id"):
        img = await repo().get("images", work["selected_image_id"])
    if not img or img.get("status") != "done":
        imgs = [i for i in await repo().all("images", where={"work_id": work["id"]}, order_by="created_at")
                if i.get("status") == "done" and not i.get("hidden")]
        img = imgs[0] if imgs else None
    if not img or not img.get("current_version_id"):
        if work.get("kind") == "composite":
            photo = await repo().get("photos", (work.get("composite") or {}).get("active_photo_id"))
            if photo:
                from .filestore import thumb_url

                return thumb_url(photo.get("file_id"), 320)
        return None
    ver = await repo().get("versions", img["current_version_id"])
    if not ver:
        return None
    from .filestore import thumb_url

    return thumb_url(ver.get("master_file_id"), 320)


async def refresh_work(work_id: str, *, register: bool = True) -> dict[str, Any] | None:
    """runs 로 상태 · 경로 · 배지를 다시 계산해 저장하고 workspace 색인에 올린다."""
    work = await repo().get("works", work_id)
    if work is None or work.get("deleted_at"):
        return work
    runs = await runs_of(work_id)
    status = views.work_status(work, runs)
    route = views.work_route(work, runs)
    used = await in_proposal(work_id)
    badge = views.badge(work, runs, in_proposal=used)
    last = runs[-1] if runs else None
    meta = views.work_meta(work, last)

    def fn(doc: dict[str, Any]) -> None:
        doc.update({"status": status, "route": route, "badge": badge, "meta_line": meta, "in_proposal": used,
                    "last_run_id": last["id"] if last else None})

    saved = await repo().mutate("works", work_id, fn, missing_ok=True)
    if register and saved:
        await index_work(saved)
    return saved


async def index_work(work: dict[str, Any]) -> None:
    """§5.4 workspace 색인 `{feature:'IMG', title, status, summary, route, project_id}`.

    다른 기능의 렌더 API 가 만든 숨은 작업(`internal` — 조감도 컷 · 시나리오 장면)은 IMG0 갤러리처럼 색인에도 올리지 않는다
    (사이드바 「이미지 생성」 이력 · 홈 최근 작업에 「조감 45° · 주간」 「장면 1 · 쇼윈도」가 쌓이던 것, 통합). 예전에 올라간 것은 지운다.
    """
    if work.get("internal"):
        from winmate_common.platform import unregister_item
        await unregister_item(work["id"])
        return
    badge = work.get("badge") or {}
    thumb = await work_thumb(work)
    await register_item(feature=config.FEATURE, item_id=work["id"], title=work.get("title") or "이미지 작업",
                        status=work.get("status") or "draft", route=work.get("route") or views.route_type(work["id"]),
                        summary=work.get("meta_line") or views.work_meta(work, None), project_id=work.get("project_id"),
                        meta={"status_label": badge.get("label"), "tone": badge.get("tone"), "icon": badge.get("icon"),
                              "kind": work.get("kind"), "thumb_url": thumb, "customer": work.get("customer_name")})


def apply_request_prefill(doc: dict[str, Any], prefill: dict[str, Any]) -> None:
    if prefill.get("kind") in ("space", "background", "scenario"):
        doc["kind"] = prefill["kind"]
        doc["conditions"]["no_products"] = prefill["kind"] == "background"
    if prefill.get("description"):
        doc["description"] = str(prefill["description"])[: config.DESC_MAX]
    if prefill.get("aspect") in config.GEN_ASPECTS:
        doc["conditions"]["aspect"] = prefill["aspect"]
    if prefill.get("style") in config.STYLES:
        doc["conditions"]["style"] = prefill["style"]
    if prefill.get("space_label"):
        doc.setdefault("prefill", {})
        doc["prefill"] = {**(doc.get("prefill") or {}), "space_label": prefill["space_label"]}


async def resolve_request_products(items: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for it in items or []:
        if isinstance(it, dict) and (it.get("name") or it.get("short")) and (it.get("model_code") or it.get("family_id")):
            out.append({"family_id": it.get("family_id"), "model_code": it.get("model_code"),
                        "name": it.get("name") or it.get("short"), "short": it.get("short") or it.get("name"),
                        "qty": max(1, min(9, int(it.get("qty") or 1))), "source": "request"})
            continue
        mention = it if isinstance(it, str) else (it.get("model_code") or it.get("name") or it.get("short") or it.get("label") or "")
        qty = 1 if isinstance(it, str) else int(it.get("qty") or 1)
        if not mention:
            continue
        hit = await kbapi.resolve_product(str(mention))
        if hit:
            out.append(kbapi.product_from_search(hit, qty, "request"))
    return dedupe_products(out)


def dedupe_products(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out = []
    for p in items:
        key = p.get("model_code") or p.get("family_id") or p.get("name")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


async def create_work(*, kind: str | None, description: str | None, project_id: str | None, customer_name: str | None,
                      request_id: str | None, start: str, title: str | None) -> dict[str, Any]:
    user = current_user()
    k = kind or ("composite" if start == "composite" else "space")
    wid = new_id("imw")
    doc: dict[str, Any] = {
        "owner": user.id, "owner_name": user.name, "project_id": project_id, "customer_name": customer_name,
        "customer_short": texts.customer_short(customer_name), "title": title or ("현장 사진 합성" if k == "composite" else "새 작업"),
        "title_source": "user" if title else "default", "subject_short": None, "kind": k,
        "description": (description or "")[: config.DESC_MAX], "conditions": default_conditions(k),
        "composite": default_composite() if k == "composite" else None,
        "origin": {"service": "image", "ref": None, "request_id": None, "label": None}, "start": start,
        "stage": {"type": "type", "references": "references", "composite": "composite"}.get(start, "type"),
        "status": "draft", "rev": 1, "selected_image_id": None, "last_export": None, "prefill": None, "ref_notice": None,
        "deleted_at": None,
    }
    if request_id:
        req = await repo().get("requests", request_id)
        if req is None:
            raise not_found("이미지 요청", request_id)
        pre = req.get("prefill") or {}
        apply_request_prefill(doc, pre)
        doc["conditions"]["products"] = await resolve_request_products(pre.get("products") or [])
        doc["origin"] = {"service": req.get("from_service") or "image", "ref": req.get("from_ref"), "request_id": request_id,
                         "label": req.get("from_label")}
        doc["project_id"] = doc["project_id"] or req.get("project_id")
        if req.get("title") and not title:
            doc["title"] = str(req["title"])[:24]
            doc["title_source"] = "request"
    if doc.get("project_id") and not doc.get("customer_name"):
        proj = await project_info(doc["project_id"])
        if proj and proj.get("customer"):
            doc["customer_name"] = proj["customer"]
            doc["customer_short"] = texts.customer_short(proj["customer"], proj.get("customer_short"))
    await repo().put("works", wid, doc)
    return await refresh_work(wid) or doc


class VersionConflictError(ApiError):
    def __init__(self, current: int):
        super().__init__(409, "VERSION_CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러온 뒤 다시 시도해 주세요", {"version": current})


async def patch_work(work_id: str, changes: dict[str, Any], if_version: int | None) -> dict[str, Any]:
    await get_work(work_id)

    def fn(doc: dict[str, Any]) -> None:
        if if_version is not None and int(doc.get("rev") or 1) != int(if_version):
            raise VersionConflictError(int(doc.get("rev") or 1))
        if "kind" in changes and changes["kind"]:
            new_kind = changes["kind"]
            if new_kind != doc.get("kind"):
                cond = doc.get("conditions") or default_conditions(new_kind)
                if new_kind == "background" and not cond.get("products"):
                    cond["no_products"] = True
                elif new_kind != "background":
                    cond["no_products"] = False
                doc["conditions"] = cond
                if new_kind == "composite" and not doc.get("composite"):
                    doc["composite"] = default_composite()
            doc["kind"] = new_kind
        if "description" in changes and changes["description"] is not None:
            if changes["description"] != doc.get("description"):
                doc["prefill"] = {**(doc.get("prefill") or {}), "done": False}
            doc["description"] = changes["description"][: config.DESC_MAX]
        if changes.get("title"):
            doc["title"] = changes["title"].strip()[:60]
            doc["title_source"] = "user"
        if "customer_name" in changes:
            doc["customer_name"] = changes["customer_name"] or None
            doc["customer_short"] = texts.customer_short(doc["customer_name"])
        if changes.get("conditions") is not None:
            cond = dict(changes["conditions"])
            cond["products"] = dedupe_products(cond.get("products") or [])
            doc["conditions"] = cond
            if doc.get("stage") in (None, "type"):
                doc["stage"] = "conditions"
        if "selected_image_id" in changes and changes["selected_image_id"]:
            doc["selected_image_id"] = changes["selected_image_id"]
        if "stage" in changes and changes["stage"]:
            doc["stage"] = changes["stage"]
        doc["rev"] = int(doc.get("rev") or 1) + 1

    try:
        await repo().mutate("works", work_id, fn)
    except VersionConflictError:
        raise
    if "customer_name" in changes:
        await _sync_image_customer(work_id)
    return await refresh_work(work_id) or await get_work(work_id)


async def add_products(work_id: str, refs_in: list[str], qty: int = 1) -> dict[str, Any]:
    """셸 `현재 작업에 추가` · 끌어 놓기(제품) — 참조를 KB 제품으로 풀어 조건에 더한다. 합성 작업이면 배치 그룹도 하나씩 만든다."""
    work = await get_work(work_id)
    added: list[str] = []
    new_products: list[dict[str, Any]] = []
    for r in dict.fromkeys(refs_in):
        p = await kbapi.product_from_ref(r, qty)
        if p:
            new_products.append(p)
            added.append(r)
    if not new_products:
        if refs_in:
            raise ApiError(422, "PRODUCT_NOT_FOUND", "카탈로그에서 그 제품을 찾지 못했어요", {"refs": refs_in})
        return {"added": [], "work": work}
    comp = work.get("composite") or {}
    if work.get("kind") == "composite" and comp.get("active_photo_id"):
        from . import photos

        photo = await repo().get("photos", comp["active_photo_id"])
        if photo is not None:
            have = {g.get("model_code") or g.get("family_id") for g in comp.get("groups") or []}
            dims = await kbapi.spec_dims([p["model_code"] for p in new_products if p.get("model_code")])
            groups = list(comp.get("groups") or [])
            for p in new_products:
                if (p.get("model_code") or p.get("family_id")) in have:
                    continue
                g = photos.default_group(photo, p, dims.get(p.get("model_code") or ""), comp.get("scale") or {})
                # 새 그룹은 기존 그룹과 겹치지 않게 아래로 조금 내린다
                shift = 0.08 * len(groups)
                g["quad"] = [[x, min(0.98, y + shift)] for x, y in g["quad"]]
                groups.append(g)
            await photos.save_placements(work_id, {"photo_id": photo["id"], "groups": groups, "ref_dims": comp.get("ref_dims") or {},
                                                   "options": comp.get("options") or {}})
            return {"added": added, "work": await get_work(work_id)}

    def fn(doc: dict[str, Any]) -> None:
        cond = doc.get("conditions") or default_conditions(doc.get("kind") or "space")
        cond["products"] = dedupe_products(list(cond.get("products") or []) + new_products)[:9]
        cond["no_products"] = False
        doc["conditions"] = cond
        doc["rev"] = int(doc.get("rev") or 1) + 1

    await repo().mutate("works", work_id, fn)
    return {"added": added, "work": await refresh_work(work_id) or await get_work(work_id)}


async def autofill_description(work_id: str) -> bool:
    """「참조 이미지로 시작」처럼 장면 설명이 비어 있으면 참조의 i2t 캡션(없으면 라벨)으로 채운다(§4.4). 채웠으면 True."""
    work = await get_work(work_id)
    if len((work.get("description") or "").strip()) >= 2:
        return False
    refs = await references_of(work_id)
    cap = next((str((r.get("analysis") or {}).get("caption") or "").strip() for r in refs
                if str((r.get("analysis") or {}).get("caption") or "").strip()), "")
    if not cap and refs:
        cap = str(refs[0].get("label") or "").strip()
    if len(cap) < 2:
        return False
    text = cap[: config.DESC_MAX]

    def fn(doc: dict[str, Any]) -> None:
        if len((doc.get("description") or "").strip()) < 2:
            doc["description"] = text
            doc["description_source"] = "reference_caption"
            doc["prefill"] = {**(doc.get("prefill") or {}), "done": False}
            doc["rev"] = int(doc.get("rev") or 1) + 1

    await repo().mutate("works", work_id, fn)
    await refresh_work(work_id, register=False)
    return True


async def _sync_image_customer(work_id: str) -> None:
    work = await get_work(work_id)
    for im in await repo().all("images", where={"work_id": work_id}):
        await repo().patch("images", im["id"], {"customer_short": work.get("customer_short")})


async def delete_work(work_id: str) -> None:
    await get_work(work_id)
    await repo().patch("works", work_id, {"deleted_at": now_iso()})
    for im in await repo().all("images", where={"work_id": work_id}):
        await repo().patch("images", im["id"], {"hidden": True})
    from winmate_common.platform import unregister_item

    await unregister_item(work_id)


# ── prefill(R1) ─────────────────────────────────────────

def fallback_title(kind: str, description: str, space_label: str | None) -> str:
    base = (space_label or re.split(r"[,.·\n]", description or "")[0] or "새 이미지").strip()
    base = re.sub(r"\s+", " ", base)[:14]
    return f"{base} {config.KIND_TITLE_SUFFIX.get(kind, '시안')}"[:24]


def fallback_subject(description: str) -> str | None:
    m = re.search(r"(메뉴보드|사이니지|키오스크|비디오월|전자칠판|로비|카운터|매장|객실|강의실|회의실)", description or "")
    return m.group(1) if m else None


async def run_prefill(work_id: str) -> dict[str, Any]:
    """IMG1 → IMG2: 장면 설명에서 제품 · 수량(KB + LLM), 제목, 참조 검색어 · 업종(동기, 제한 10초 — 넘으면 KB 결과만)."""
    work = await get_work(work_id)
    desc = work.get("description") or ""
    kind = work.get("kind") or "space"
    total = config.prefill_timeout_s()
    t0 = time.monotonic()

    async def kb_part() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        links = await kbapi.a1(desc) if desc else []
        found: list[dict[str, Any]] = []
        codes = list(dict.fromkeys(kbapi.MODEL_CODE_RE.findall(desc)))[:6]
        for l in links:
            if l.get("type") in ("model", "family") and l.get("surface"):
                codes.append(str(l.get("surface")))
        for c in dict.fromkeys(codes):
            hit = await kbapi.resolve_product(c)
            if hit:
                found.append(kbapi.product_from_search(hit, 1, "prefill"))
        return links, found

    kb_task = asyncio.create_task(kb_part())
    llm_task = asyncio.create_task(llm.json_task("img.prefill", llm.prefill_prompt(config.KIND_LABEL.get(kind, kind), desc),
                                                 llm.PrefillOut, system=llm.SYSTEM_KO))
    # LLM 은 전체 제한(10초) 안에서 LLM 제한(8초)까지만 기다린다 — 넘으면 KB 결과만
    done, _ = await asyncio.wait({kb_task, llm_task}, timeout=min(config.llm_timeout_s(), total))
    timed_out = llm_task not in done
    if timed_out:
        llm_task.cancel()
    if kb_task not in done:
        rest = max(0.05, total - (time.monotonic() - t0))
        done2, _ = await asyncio.wait({kb_task}, timeout=rest)
        if kb_task not in done2:
            kb_task.cancel()
    links, kb_products = (kb_task.result() if kb_task.done() and not kb_task.cancelled() and kb_task.exception() is None
                          else ([], []))
    out: dict[str, Any] | None = None
    if not timed_out:
        try:
            out = llm_task.result()
        except Exception:  # noqa: BLE001 — 기밀 차단 · 실패면 KB 결과만
            out = None

    products = list(kb_products)
    if out:
        remain = max(0.05, total - (time.monotonic() - t0))
        try:
            resolved = await asyncio.wait_for(asyncio.gather(*(kbapi.resolve_product(m["mention"]) for m in out.get("products") or [])),
                                              timeout=remain)
        except asyncio.TimeoutError:
            resolved = []
            timed_out = True
        for m, hit in zip(out.get("products") or [], resolved):
            if hit:
                p = kbapi.product_from_search(hit, m.get("qty") or 1, "prefill")
                same = next((x for x in products if x.get("model_code") and x.get("model_code") == p.get("model_code")), None)
                if same:
                    same["qty"] = p["qty"]
                else:
                    products.append(p)
    products = dedupe_products(products)
    space_link = next((l for l in links if l.get("type") == "space_type"), None)
    space_label = (out or {}).get("space_label") or (space_link or {}).get("name")
    cat_link = next((l for l in links if l.get("type") == "category"), None)
    title = (out or {}).get("title") or fallback_title(kind, desc, space_label)
    subject = (out or {}).get("subject_short") or fallback_subject(desc)
    query = (out or {}).get("search_query") or " ".join(x for x in [(space_link or {}).get("name"), (cat_link or {}).get("name")] if x) or desc[:20]
    industry = (out or {}).get("industry")
    chips = industry_chips(industry)
    message = None
    if not products and kind != "background":
        message = "제품을 찾지 못했어요. 제품명을 입력해 주세요"

    def fn(doc: dict[str, Any]) -> None:
        cond = doc.get("conditions") or default_conditions(kind)
        user_products = [p for p in cond.get("products") or [] if p.get("source") in ("user", "request")]
        if kind == "background":
            cond["products"] = user_products
            cond["no_products"] = not user_products
        else:
            cond["products"] = dedupe_products(user_products + products)[:6]
        doc["conditions"] = cond
        if doc.get("title_source") in (None, "default", "auto"):
            doc["title"] = title[:24]
            doc["title_source"] = "auto"
        doc["subject_short"] = (subject or doc.get("subject_short") or None)
        if subject:
            doc["subject_short"] = subject[:6]
        if not doc.get("customer_name") and (out or {}).get("customer_name") and (out or {}).get("customer_name") in desc:
            doc["customer_name"] = out["customer_name"]
            doc["customer_short"] = texts.customer_short(out["customer_name"])
        doc["prefill"] = {"done": True, "search_query": query, "industry": industry, "industry_chips": chips,
                          "space_label": space_label, "space_type_id": (space_link or {}).get("id"),
                          "category_id": (cat_link or {}).get("id"), "kind_suggestion": (out or {}).get("kind_suggestion"),
                          "message": message, "timed_out": timed_out, "at": now_iso()}
        if doc.get("stage") in (None, "type"):
            doc["stage"] = "conditions"
        doc["rev"] = int(doc.get("rev") or 1) + 1

    await repo().mutate("works", work_id, fn)
    work = await refresh_work(work_id) or await get_work(work_id)
    return {"title": work.get("title") or title, "subject_short": work.get("subject_short"),
            "products": [{k: p.get(k) for k in ("family_id", "model_code", "name", "short", "qty")} for p in
                         (work.get("conditions") or {}).get("products") or []],
            "search_query": query, "industry_chips": chips, "kind_suggestion": (out or {}).get("kind_suggestion"),
            "customer_name": work.get("customer_name"), "timed_out": timed_out, "message": message, "work_doc": work}


def industry_chips(industry: str | None) -> list[str]:
    """업종 칩 4개 — 프로젝트(추정) 업종을 첫 칸, 나머지는 사례가 많은 업종 순(Winmate 16)."""
    order = ["FB", "RT", "HT", "OF", "ED", "MD", "RS", "PB", "TP", "FN", "MF", "VN", "ID", "SV", "AD"]
    chips: list[str] = []
    if industry:
        code = kbapi.segment_by_chip(industry)
        if code is None:
            for c, name in kbapi.SEGMENT_CHIP.items():
                if name.split(" ")[0] in industry or industry.split(" ")[0] in name:
                    code = c
                    break
        chips.append(kbapi.SEGMENT_CHIP.get(code, industry) if code else industry)
    for c in order:
        if len(chips) >= 4:
            break
        lab = kbapi.SEGMENT_CHIP[c]
        if lab not in chips:
            chips.append(lab)
    return chips


# ── 보기 ─────────────────────────────────────────────────

async def references_of(work_id: str) -> list[dict[str, Any]]:
    refs = await repo().all("refs", where={"work_id": work_id}, order_by="created_at")
    return sorted(refs, key=lambda r: (int(r.get("order") or 0), r.get("created_at") or ""))


async def work_view(work: dict[str, Any]) -> dict[str, Any]:
    runs = await runs_of(work["id"])
    refs = await references_of(work["id"])
    last = runs[-1] if runs else None
    active = [r for r in runs if r.get("status") in ("queued", "running", "awaiting_input")]
    n_images = await repo().count("images", where={"work_id": work["id"]})
    kind = work.get("kind") or "space"
    badge = work.get("badge") or views.badge(work, runs, in_proposal=bool(work.get("in_proposal")))
    notice = None
    topbar = [r for r in refs if r.get("via") == "topbar"]
    if topbar:
        notice = f"이미지 검색에서 선택한 {len(topbar)}장이 참조로 들어갔습니다"
    pre = work.get("prefill")
    return {
        "id": work["id"], "owner": work.get("owner") or "", "project_id": work.get("project_id"),
        "customer_name": work.get("customer_name"), "customer_short": work.get("customer_short"),
        "title": work.get("title") or "새 작업", "subject_short": work.get("subject_short"), "kind": kind,
        "kind_label": config.KIND_LABEL.get(kind, kind), "description": work.get("description") or "", "echo": views.echo(work),
        "conditions": work.get("conditions") or default_conditions(kind), "composite": work.get("composite"),
        "origin": work.get("origin"), "start": work.get("start") or "type", "status": work.get("status") or "draft",
        "badge": badge, "route": work.get("route") or views.work_route(work, runs),
        "selected_image_id": work.get("selected_image_id"), "last_export": work.get("last_export"),
        "prefill": ({"done": bool(pre.get("done")), "search_query": pre.get("search_query"), "industry": pre.get("industry"),
                     "industry_chips": list(pre.get("industry_chips") or []), "space_label": pre.get("space_label"),
                     "kind_suggestion": pre.get("kind_suggestion"), "message": pre.get("message"),
                     "timed_out": bool(pre.get("timed_out"))} if pre else None),
        "references": [views.reference_view(r) for r in refs], "ref_notice": notice,
        "latest_run": views.run_brief(last), "active_runs": [views.run_brief(r) for r in active],
        "image_count": n_images, "version": int(work.get("rev") or 1),
        "created_at": work.get("created_at") or "", "updated_at": work.get("updated_at") or "",
    }


async def work_row(work: dict[str, Any]) -> dict[str, Any]:
    runs = await runs_of(work["id"])
    last = runs[-1] if runs else None
    active = [r for r in runs if r.get("status") in ("queued", "running")]
    badge = views.badge(work, runs, in_proposal=bool(work.get("in_proposal")))
    return {
        "id": work["id"], "title": work.get("title") or "새 작업", "meta": views.work_meta(work, last),
        "time": texts.relative_time(work.get("updated_at")), "updated_at": work.get("updated_at") or "",
        "status": badge, "thumb_url": await work_thumb(work), "route": work.get("route") or views.work_route(work, runs),
        "kind": work.get("kind") or "space", "customer_short": work.get("customer_short"),
        "run": views.run_brief(active[-1]) if active else None,
    }
