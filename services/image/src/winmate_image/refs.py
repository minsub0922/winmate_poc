"""참조 이미지(IMG2R · §4.4 · §6.3) — 고르기 · 따를 요소 · 강도 · 검색 탭 4개 · 분석(비동기).

출처별:
- kb_asset · case_photo: KB 이미지 id → 메타(권리 · 출처 URL · 캡션 규칙) + files 사본(한 번만, kbfiles 캐시)
- my_image: 내 생성 시안(img_) → 현재 버전 기준 렌디션
- upload: files 업로드(file_id) — 권리 미확인(강도 「강」 불가), 모델 호출은 기밀
- topbar: 셸 ref(`kb:image:…` · `img:image:…`) — 상단 이미지 검색에서 「현재 작업에 추가」 · 끌어 놓기
"""
from __future__ import annotations

import base64
import logging
from typing import Any

from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import jobs

from . import config, kbapi, views
from .filestore import save_bytes, thumb_url
from .service import get_work, references_of, refresh_work
from .store import repo

log = logging.getLogger("winmate.image.refs")

LIMIT_MSG = "참조는 3장까지 고를 수 있어요"
STRONG_MSG = "올린 사진은 ‘중’까지 따를 수 있어요"


def reference_limit() -> ApiError:
    return ApiError(422, "REFERENCE_LIMIT", LIMIT_MSG, {"max": config.MAX_REFERENCES})


def strength_not_allowed() -> ApiError:
    return ApiError(422, "STRENGTH_NOT_ALLOWED", STRONG_MSG, {"allowed": ["low", "mid"]})


async def kb_file(kb_image_id: str, *, alt: str | None = None) -> str | None:
    """KB 이미지를 files 에 한 번만 복사한다(참조 · 제품 단독컷을 T2I 로 보낼 때 file_id 가 필요)."""
    hit = await repo().get("kbfiles", kb_image_id)
    if hit and hit.get("file_id"):
        return hit["file_id"]
    data = await kbapi.image_bytes(kb_image_id)
    if not data:
        return None
    mime = "image/webp" if data[:4] == b"RIFF" else ("image/png" if data[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg")
    ext = {"image/webp": "webp", "image/png": "png"}.get(mime, "jpg")
    try:
        meta = await save_bytes(f"kb_{kb_image_id}.{ext}", data, mime, source="derived",
                                meta={"kb_image_id": kb_image_id, "alt": alt, "purpose": "img.reference"}, purpose="img.reference")
    except Exception as exc:  # noqa: BLE001
        log.warning("kb 이미지를 files 에 복사하지 못했습니다 %s: %s", kb_image_id, exc)
        return None
    await repo().put("kbfiles", kb_image_id, {"file_id": meta["id"]})
    return meta["id"]


def _alt_style(alt: str | None) -> str:
    a = alt or ""
    return "illustration" if any(k in a for k in ("일러스트", "아이소메트릭", "그래픽", "illustration", "isometric")) else "photo"


async def resolve(source_kind: str, source_ref: str | None, file_id: str | None, *, owner: str) -> dict[str, Any]:
    """참조 출처 → {origin_kind, file_id, thumb_url, label, source_label, source_url, rights, alt, confidential}."""
    sk, ref = source_kind, source_ref or ""
    via = None
    if sk == "topbar":
        via = "topbar"
        if ref.startswith("kb:image:"):
            sk, ref = "kb_asset", ref.split(":", 2)[2]
        elif ref.startswith("img:image:"):
            sk, ref = "my_image", ref.split(":", 2)[2]
        elif ref.startswith("img_") and len(ref) > 20:
            sk = "my_image"
        elif ref.startswith("img_"):
            sk = "kb_asset"
        else:
            raise ApiError(422, "INVALID_REFERENCE", "참조로 쓸 수 없는 항목입니다", {"ref": source_ref})
    if sk in ("kb_asset", "case_photo"):
        meta = await kbapi.image_meta(ref)
        if meta is None:
            raise not_found("KB 이미지", ref)
        rights = meta.get("rights") or "unknown"
        if rights not in ("official", "customer_case"):
            raise ApiError(422, "INVALID_REFERENCE", "출처 · 권리가 확인된 사내 자산만 참조로 쓸 수 있어요", {"rights": rights})
        fid = await kb_file(ref, alt=meta.get("alt"))
        label = (meta.get("label") or meta.get("title") or meta.get("alt") or "사내 자산 이미지").strip()
        if label in ("img", "image"):
            label = f"{((meta.get('source_page') or {}).get('label') or '사내 자산')} 사진"
        if sk == "case_photo":
            src_label = "유관 사례 · 도입사례 사진"
        elif via == "topbar":
            src_label = "이미지 검색 · " + ("도입사례 사진" if rights == "customer_case" else "삼성 공식 이미지")
        else:
            src_label = "사내 자산 · " + ("도입사례 사진" if rights == "customer_case" else "삼성 공식 이미지")
        return {"origin_kind": sk if sk == "case_photo" else "kb_asset", "file_id": fid, "thumb_url": meta.get("thumb_url"),
                "label": label[:60], "source_label": src_label, "source_url": (meta.get("source_page") or {}).get("url") or meta.get("original_url"),
                "rights": rights, "alt": meta.get("alt"), "source_ref": ref, "confidential": False, "via": via,
                "caption_rule": meta.get("caption_rule"), "visual_style": _alt_style(meta.get("alt"))}
    if sk == "my_image":
        img = await repo().get("images", ref)
        if img is None or img.get("status") != "done" or not img.get("current_version_id"):
            raise not_found("생성 이미지", ref)
        ver = await repo().get("versions", img["current_version_id"])
        fid = (ver or {}).get("master_file_id")
        return {"origin_kind": "my_image", "file_id": fid, "thumb_url": thumb_url(fid, 320), "label": views.image_title(img),
                "source_label": "이미지 검색 · 내 생성 이미지" if via == "topbar" else "내 생성 이미지 · AI 생성", "source_url": None,
                "rights": "generated", "alt": None, "source_ref": ref, "confidential": bool((ver or {}).get("generation", {}).get("confidential")),
                "via": via, "visual_style": "photo"}
    if sk == "upload":
        fid = file_id or (ref if ref.startswith("file_") else None)
        if not fid:
            raise ApiError(422, "INVALID_REFERENCE", "올린 파일이 없습니다")
        from .filestore import meta as fmeta

        fm = await fmeta(fid)
        if fm is None:
            raise not_found("파일", fid)
        if fm.get("kind") not in ("image", None) and not str(fm.get("mime") or "").startswith("image/"):
            raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", "JPG · PNG · HEIC 이미지만 올릴 수 있어요")
        if int(fm.get("size") or 0) > 20 * 1024 * 1024:
            raise ApiError(413, "PAYLOAD_TOO_LARGE", "20MB 이하 이미지만 올릴 수 있어요")
        return {"origin_kind": "upload", "file_id": fid, "thumb_url": thumb_url(fid, 320), "label": (fm.get("name") or "올린 사진")[:60],
                "source_label": "내 파일 · 업로드", "source_url": None, "rights": "unknown", "alt": None, "source_ref": fid,
                "confidential": True, "via": "upload", "visual_style": "photo"}
    raise ApiError(422, "INVALID_REFERENCE", "알 수 없는 참조 출처입니다", {"source_kind": source_kind})


def default_aspects(origin_kind: str) -> list[str]:
    return ["composition"] if origin_kind == "kb_asset" else ["color_light"]


async def add_reference(work_id: str, body: dict[str, Any], *, analyze: bool = True) -> dict[str, Any]:
    work = await get_work(work_id)
    refs = await references_of(work_id)
    if len(refs) >= config.MAX_REFERENCES:
        raise reference_limit()
    info = await resolve(body["source_kind"], body.get("source_ref"), body.get("file_id"), owner=work.get("owner") or "")
    # 같은 출처는 두 번 넣지 않는다
    for r in refs:
        if r.get("source_ref") == info["source_ref"] and r.get("origin_kind") == info["origin_kind"]:
            return r
    strength = body.get("strength") or "mid"
    if info["origin_kind"] == "upload" and strength == "high":
        raise strength_not_allowed()
    rid = new_id("imr")
    doc = {
        "work_id": work_id, "order": (max([int(r.get("order") or 0) for r in refs]) + 1) if refs else 1,
        "source_kind": body["source_kind"], "source_ref": info["source_ref"], "origin_kind": info["origin_kind"],
        "file_id": info["file_id"], "thumb_url": info["thumb_url"], "label": body.get("label") or info["label"],
        "source_label": info["source_label"], "source_url": info["source_url"], "rights": info["rights"],
        "aspects": list(body.get("aspects") or default_aspects(info["origin_kind"])), "strength": strength,
        "analysis": None, "sanitized_file_id": None, "send_mode": None, "confidential": info["confidential"],
        "via": body.get("via") or info.get("via") or "picker", "alt": info.get("alt"), "visual_style": info.get("visual_style"),
        "created_at": now_iso(),
    }
    saved = await repo().put("refs", rid, doc)
    await _touch(work_id)
    if analyze and info["file_id"]:
        try:
            await jobs().enqueue("image", "analyze_reference", {"ref_id": rid}, title="참조 이미지 분석", ref=rid,
                                 project_id=work.get("project_id"))
        except Exception as exc:  # noqa: BLE001 — 분석은 생성 때 다시 한다
            log.info("참조 분석 잡을 넣지 못했습니다: %s", exc)
    return saved


async def patch_reference(work_id: str, ref_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    ref = await repo().get("refs", ref_id)
    if ref is None or ref.get("work_id") != work_id:
        raise not_found("참조 이미지", ref_id)
    if changes.get("strength") == "high" and ref.get("origin_kind") == "upload":
        raise strength_not_allowed()
    upd = {k: v for k, v in changes.items() if v is not None}
    if "aspects" in upd and not upd["aspects"]:
        raise ApiError(422, "VALIDATION_ERROR", "따를 요소를 하나 이상 골라 주세요")
    saved = await repo().patch("refs", ref_id, upd)
    await _touch(work_id)
    return saved or ref


async def delete_reference(work_id: str, ref_id: str) -> None:
    ref = await repo().get("refs", ref_id)
    if ref is None or ref.get("work_id") != work_id:
        raise not_found("참조 이미지", ref_id)
    await repo().delete("refs", ref_id)
    await _touch(work_id)


def _key(it: dict[str, Any]) -> str:
    k = str(it.get("source_ref") or it.get("file_id") or "")
    for pre in ("kb:image:", "img:image:"):
        if k.startswith(pre):
            return k[len(pre):]
    return k


async def set_references(work_id: str, items: list[dict[str, Any]], via: str) -> list[dict[str, Any]]:
    """IMG2R 「참조 n장 적용」 — 고른 묶음으로 바꾼다(같은 출처는 요소 · 강도 · 순서만 갱신)."""
    if len(items) > config.MAX_REFERENCES:
        raise reference_limit()
    await get_work(work_id)
    current = await references_of(work_id)
    keep: set[str] = set()
    to_add: list[tuple[int, dict[str, Any]]] = []
    for i, it in enumerate(items, 1):
        hit = next((r for r in current if r.get("source_ref") == _key(it)), None)
        if hit is None:
            to_add.append((i, it))
            continue
        if it.get("strength") == "high" and hit.get("origin_kind") == "upload":
            raise strength_not_allowed()
        upd: dict[str, Any] = {"order": i}
        if it.get("aspects"):
            upd["aspects"] = it["aspects"]
        if it.get("strength"):
            upd["strength"] = it["strength"]
        await repo().patch("refs", hit["id"], upd)
        keep.add(hit["id"])
    for r in current:
        if r["id"] not in keep:
            await repo().delete("refs", r["id"])
    for i, it in to_add:
        saved = await add_reference(work_id, {**it, "via": it.get("via") or via})
        await repo().patch("refs", saved["id"], {"order": i})
    await _touch(work_id)
    if items:
        from .service import autofill_description

        await autofill_description(work_id)
    return await references_of(work_id)


async def _touch(work_id: str) -> None:
    def fn(doc: dict[str, Any]) -> None:
        doc["rev"] = int(doc.get("rev") or 1) + 1

    await repo().mutate("works", work_id, fn, missing_ok=True)
    await refresh_work(work_id, register=False)


# ── 검색 ─────────────────────────────────────────────────

def _kb_item(row: dict[str, Any], *, source_kind: str = "kb_asset") -> dict[str, Any] | None:
    rights = row.get("rights")
    if rights not in ("official", "customer_case"):
        return None
    alt = row.get("alt") or ""
    label = (row.get("caption") or alt or row.get("title") or "사내 자산").strip()
    if label in ("img", "image"):
        label = f"{row.get('title') or '도입사례'} 사진"
    verified = bool(row.get("url") and (row.get("page_url") or row.get("source_url")))
    if source_kind == "case_photo":
        src = "유관 사례 · 도입사례 사진"
    else:
        src = "사내 자산 · " + ("도입사례 사진" if rights == "customer_case" else "삼성 공식 이미지")
    return {"source_kind": source_kind, "source_ref": row["id"], "thumb_url": row.get("thumb_url") or f"/api/kb/v1/images/{row['id']}/thumb",
            "label": label[:40], "alt": alt or None, "source_label": src, "source_url": row.get("page_url") or row.get("case_url"),
            "rights": rights, "verified": verified, "visual_style": _alt_style(alt), "file_id": None, "_v": row.get("v")}


def _paginate(items: list[dict[str, Any]], limit: int, cursor: str | None) -> tuple[list[dict[str, Any]], str | None]:
    off = 0
    if cursor:
        try:
            off = int(base64.urlsafe_b64decode(cursor.encode()).decode())
        except Exception:  # noqa: BLE001
            off = 0
    page = items[off: off + limit]
    nxt = base64.urlsafe_b64encode(str(off + limit).encode()).decode() if off + limit < len(items) else None
    return page, nxt


async def search(*, tab: str, q: str | None, industry: str | None, style: str, work_id: str | None, limit: int,
                 cursor: str | None, owner: str) -> dict[str, Any]:
    work = await get_work(work_id) if work_id else None
    pre = (work or {}).get("prefill") or {}
    query = (q if q is not None else pre.get("search_query")) or (work or {}).get("description", "")[:30] or ""
    chips = list(pre.get("industry_chips") or [])
    if not chips:
        from .service import industry_chips

        chips = industry_chips(None)
    items: list[dict[str, Any]] = []
    verified_head = True
    if tab == "kb":
        rows: list[dict[str, Any]] = []
        if pre.get("space_type_id"):
            rows += await kbapi.g1(pre["space_type_id"], pre.get("category_id"), None, limit=8)
        rows += await kbapi.image_search(query, limit=48)
        seen: set[str] = set()
        for r in rows:
            it = _kb_item(r)
            if it and it["source_ref"] not in seen:
                seen.add(it["source_ref"])
                items.append(it)
    elif tab == "cases":
        seg = kbapi.segment_by_chip(industry) if industry else None
        vertical = (kbapi.SEGMENT_KR.get(seg) or (None,))[0] if seg else None
        cases = await kbapi.d1(vertical=vertical, spaces=[pre["space_type_id"]] if pre.get("space_type_id") else [], text=query, limit=4)
        seen = set()
        for c in cases:
            for ph in await kbapi.case_photos(c["id"], limit=3):
                ph = {**ph, "page_url": c.get("url"), "url": c.get("url"), "v": vertical}
                it = _kb_item(ph, source_kind="case_photo")
                if it and it["source_ref"] not in seen:
                    seen.add(it["source_ref"])
                    it["label"] = (ph.get("title") or c.get("title") or it["label"])[:40]
                    items.append(it)
        industry = None
    elif tab == "mine":
        verified_head = False
        imgs = await repo().all("images", where={"owner": owner}, order_by="-created_at", limit=500)
        for im in imgs:
            if im.get("status") != "done" or im.get("hidden") or not im.get("saved") or im.get("origin") not in ("image", "scenario", None):
                continue
            ver = await repo().get("versions", im.get("current_version_id"))
            fid = (ver or {}).get("master_file_id")
            title = views.image_title(im)
            if q and q.strip() and q.strip() not in title and q.strip() not in (im.get("customer_short") or ""):
                continue
            items.append({"source_kind": "my_image", "source_ref": im["id"], "thumb_url": thumb_url(fid, 320), "label": title,
                          "alt": None, "source_label": "내 생성 이미지 · AI 생성", "source_url": None, "rights": "generated",
                          "verified": False, "visual_style": "photo", "file_id": fid})
        industry = None
    else:
        raise ApiError(422, "VALIDATION_ERROR", "tab 은 kb · mine · cases 중 하나입니다")
    # 업종 · 스타일 필터
    if industry and tab == "kb":
        seg = kbapi.segment_by_chip(industry)
        ks = set(kbapi.SEGMENT_KR.get(seg or "", ()))
        if ks:
            items = [i for i in items if i.get("_v") in ks]
    if style in ("photo", "illustration"):
        items = [i for i in items if i["visual_style"] == style]
    for i in items:
        i.pop("_v", None)
    total = len(items)
    page, nxt = _paginate(items, limit, cursor)
    head = f"{total} 개 · 검수 완료" if verified_head else f"{total} 개"
    return {"items": page, "total": total, "next_cursor": nxt, "head": head, "query": query, "industry_chips": chips}
