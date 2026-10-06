"""시안 · 버전 · 편집(§4.7 · §4.9 · §4.10 · §5.2 · §5.3 · §6.6).

버전은 지우지 않고 쌓는다(부분 수정 · 보정 · 복원마다 새 버전). 영역 「되돌리기」는 현재 버전 포인터만 기준 버전으로 옮긴다.
비율 run 결과는 새 시안(`{원 라벨} · {비율}`, base_image_id)이다.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from PIL import Image

from winmate_common.context import current_user
from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso

from . import caps, config, imaging, llm, texts, views
from .filestore import content_url, load_image, save_image, thumb_url
from .service import get_work, refresh_work
from .store import repo

log = logging.getLogger("winmate.image.images")

PRESET_TEXT = {
    "erase_text": ("글자", "text", "글자를 지우고 주변과 자연스럽게 채워줘"),
    "erase_people": ("사람", "person", "사람을 지우고 배경을 자연스럽게 채워줘"),
    "screen_content": ("제품 화면", "screen", None),
}
NO_BBOX_NOTE = "자동 영역 인식이 없어 전체 이미지에 적용해요"


def capability_unsupported(message: str, **details: Any) -> ApiError:
    return ApiError(422, "CAPABILITY_UNSUPPORTED", message, details)


async def get_image(image_id: str) -> dict[str, Any]:
    img = await repo().get("images", image_id)
    if img is None:
        raise not_found("시안", image_id)
    return img


async def current_version(img: dict[str, Any]) -> dict[str, Any] | None:
    return await repo().get("versions", img.get("current_version_id"))


async def versions_of(image_id: str) -> list[dict[str, Any]]:
    vs = await repo().all("versions", where={"image_id": image_id}, order_by="created_at")
    return sorted(vs, key=lambda v: int(v.get("n") or 0))


# ── 버전 만들기(API · 워커 공통) ─────────────────────────

def dc_source(img: dict[str, Any]) -> str:
    return views.route_result(img["work_id"], img["id"])


async def create_version(img: dict[str, Any], *, op: str, master: Image.Image, generation: dict[str, Any],
                         parent_version_id: str | None = None, op_params: dict[str, Any] | None = None,
                         qc: dict[str, Any] | None = None, native: dict[str, Any] | None = None,
                         extra_renditions: list[dict[str, Any]] | None = None, confidential: bool = False,
                         set_current: bool = True, label: str | None = None) -> dict[str, Any]:
    vid = new_id("imv")
    existing = await versions_of(img["id"])
    n = (max(int(v.get("n") or 0) for v in existing) + 1) if existing else 1
    sources = [r.get("source_url") for r in generation.get("references") or [] if r.get("source_url")]
    embed = {"generated": True, "version_id": vid, "model": generation.get("model"), "sources": sources, "dc_source": dc_source(img)}
    parent_file = (native or {}).get("file_id")
    fm = await save_image(master, f"{img['id']}_v{n}.png", embed=embed, confidential=confidential,
                          project_id=img.get("project_id"), parent_id=parent_file,
                          meta={"image_id": img["id"], "version_id": vid, "rights": "generated", "is_generated": True,
                                "ai_generated": True, "caption_rule": "생성 이미지", "op": op}, purpose="img.master")
    rends = []
    if native and native.get("file_id"):
        rends.append({"kind": "native", "w": int(native["w"]), "h": int(native["h"]), "file_id": native["file_id"], "method": "t2i"})
    rends.append({"kind": "fhd", "w": master.width, "h": master.height, "file_id": fm["id"],
                  "method": (generation.get("upscale") or {}).get("method") or "lanczos3"})
    rends.append({"kind": "thumb", "w": 320, "h": max(1, round(320 * master.height / master.width)), "file_id": fm["id"],
                  "method": "files_thumbnail"})
    rends += extra_renditions or []
    edits = [v for v in existing if v.get("op") in ("edit_region", "edit_global", "adjust")]
    k = len([v for v in existing if v.get("op") in ("edit_region", "edit_global", "adjust", "restore")]) + 1
    region_n = (op_params or {}).get("region_n")
    lab = label or texts.version_label(n, op, op_index=k, region_n=region_n, aspect=img.get("aspect"))
    doc = {"image_id": img["id"], "n": n, "parent_version_id": parent_version_id, "op": op, "op_params": op_params or {},
           "label": lab, "master_file_id": fm["id"], "width": master.width, "height": master.height, "bytes": fm.get("size"),
           "native": native or {}, "renditions": rends, "generation": generation, "qc": qc or {}, "confidential": confidential,
           "created_at": now_iso()}
    _ = edits
    saved = await repo().put("versions", vid, doc)
    if set_current:
        await repo().patch("images", img["id"], {"current_version_id": vid})
    return saved


async def add_rendition(version: dict[str, Any], rendition: dict[str, Any]) -> dict[str, Any]:
    def fn(v: dict[str, Any]) -> None:
        rs = [r for r in v.get("renditions") or [] if r.get("kind") != rendition["kind"]]
        rs.append(rendition)
        v["renditions"] = rs

    return await repo().mutate("versions", version["id"], fn) or version


async def ensure_rendition(version: dict[str, Any], kind: str, aspect: str) -> dict[str, Any]:
    """fhd · uhd · uhd8k 렌디션이 없으면 만든다(로컬 업스케일 — Lanczos3 + 언샤프)."""
    have = next((r for r in version.get("renditions") or [] if r.get("kind") == kind), None)
    if have:
        return have
    if kind == "uhd8k" and config.upscaler() == "none":
        raise capability_unsupported("×4는 업스케일 모델이 있어야 해요")
    size = config.size_for(aspect, kind)
    src = await load_image(version["master_file_id"])
    out, method = await asyncio.to_thread(imaging.upscale, src, size)
    gen = version.get("generation") or {}
    embed = {"generated": True, "version_id": version["id"], "model": gen.get("model"),
             "sources": [r.get("source_url") for r in gen.get("references") or [] if r.get("source_url")], "dc_source": None}
    fm = await save_image(out, f"{version['image_id']}_v{version.get('n')}_{kind}.png", embed=embed,
                          confidential=bool(version.get("confidential")), parent_id=version["master_file_id"],
                          meta={"version_id": version["id"], "rendition": kind, "rights": "generated", "is_generated": True,
                                "ai_generated": True}, purpose="img.rendition")
    rend = {"kind": kind, "w": size[0], "h": size[1], "file_id": fm["id"], "method": method}
    await add_rendition(version, rend)
    return rend


# ── 목록 · 보기 ─────────────────────────────────────────

async def used_count(image_id: str) -> int:
    return await repo().count("usages", where={"image_id": image_id})


RUNNING = ("waiting", "composing", "rendering", "qc")


async def list_images(*, owner: str, origins: list[str], kind: str | None, customer: str | None, aspect: str | None,
                      in_proposal: bool | None, q: str | None, work_id: str | None, saved: bool | None, limit: int,
                      cursor: str | None, include_running: bool = True) -> dict[str, Any]:
    """갤러리 — 기본은 「내 이미지」(저장한 시안 · 내보낸 시안 · 취소 때 남긴 시안) + 진행 중 run 마다 타일 하나(「생성 중 {done} / {total}」).
    work_id 를 주면 그 작업의 완성 시안 전부."""
    where: dict[str, Any] = {"work_id": work_id} if work_id else {"owner": owner}
    imgs = await repo().all("images", where=where, order_by="-created_at", limit=3000)
    out = []
    seen_runs: set[str] = set()
    runs_cache: dict[str, dict[str, Any] | None] = {}
    works_cache: dict[str, dict[str, Any]] = {}
    for im in imgs:
        if im.get("hidden"):
            continue
        if (im.get("origin") or "image") not in origins:
            continue
        st = im.get("status")
        rid = im.get("run_id")
        if st in RUNNING:
            if not include_running:
                continue
            if work_id is None:
                if rid in seen_runs:
                    continue
                seen_runs.add(rid or im["id"])
        elif st == "done":
            if saved is not None:
                if bool(im.get("saved")) != saved:
                    continue
            elif work_id is None and not im.get("saved"):
                continue
        else:
            continue
        if kind and (im.get("kind") or "space") != kind:
            continue
        if customer and (im.get("customer_short") or "") != customer:
            continue
        if aspect and (im.get("aspect") or "") != aspect:
            continue
        title = views.image_title(im)
        if q and q.strip():
            # 낱말마다(공백 기준) 제목 · 고객사 · 작업 제목 · 장면 설명 중 어딘가에 있으면 맞음
            if im["work_id"] not in works_cache:
                works_cache[im["work_id"]] = await repo().get("works", im["work_id"]) or {}
            wk = works_cache[im["work_id"]]
            hay = " ".join([title, im.get("customer_short") or "", im.get("work_title") or "", wk.get("title") or "",
                            wk.get("description") or "", wk.get("customer_name") or ""])
            if not all(tok in hay for tok in q.split()):
                continue
        n_used = await used_count(im["id"])
        if in_proposal is not None and (n_used > 0) != in_proposal:
            continue
        ver = await repo().get("versions", im.get("current_version_id")) if im.get("current_version_id") else None
        if rid not in runs_cache:
            runs_cache[rid] = await repo().get("runs", rid) if rid else None
        if st in RUNNING and runs_cache[rid] is not None:
            shots_ = await repo().all("images", where={"run_id": rid})
            runs_cache[rid] = {**runs_cache[rid], "done": sum(1 for x in shots_ if x.get("status") == "done"), "total": len(shots_)}
        out.append(views.image_tile(im, version=ver, run=runs_cache[rid], used_in_count=n_used))
    from .refs import _paginate

    page, nxt = _paginate(out, limit, cursor)
    return {"items": page, "total": len(out), "next_cursor": nxt}


async def image_detail(img: dict[str, Any]) -> dict[str, Any]:
    vs = await versions_of(img["id"])
    cur = next((v for v in vs if v["id"] == img.get("current_version_id")), None)
    work = await repo().get("works", img["work_id"]) or {}
    usages = await repo().all("usages", where={"image_id": img["id"]})
    gen = (cur or {}).get("generation") or {}
    prods = (work.get("conditions") or {}).get("products") or []
    space = ((work.get("prefill") or {}).get("space_label"))
    return {
        "id": img["id"], "work_id": img["work_id"], "run_id": img.get("run_id"), "label": img.get("label") or "시안",
        "title": views.image_title(img), "letter": img.get("letter"), "variant_name": img.get("variant_name"),
        "aspect": img.get("aspect") or "16:9", "style": img.get("style") or "photo", "kind": img.get("kind") or "space",
        "status": img.get("status") or "waiting", "origin": img.get("origin") or "image", "saved": bool(img.get("saved")),
        "hidden": bool(img.get("hidden")), "base_image_id": img.get("base_image_id"), "current_version_id": img.get("current_version_id"),
        "current": views.version_view(cur, image=img) if cur else None, "versions": [views.version_view(v, image=img) for v in vs],
        "file_id": (cur or {}).get("master_file_id"), "url": content_url((cur or {}).get("master_file_id")),
        "thumb_url": thumb_url((cur or {}).get("master_file_id"), 640), "width": (cur or {}).get("width"), "height": (cur or {}).get("height"),
        "rights": "generated", "caption_rule": "생성 이미지",
        "scene": {"space": space, "products": [p.get("name") or p.get("short") for p in prods]},
        "prompt": gen.get("prompt_ko") or gen.get("prompt_en"), "qc_flag": bool(img.get("qc_flag")), "qc_reason": img.get("qc_reason"),
        "layout_note": img.get("layout_note"),
        "used_in": [{"image_id": u["image_id"], "version_id": u.get("version_id") or "", "service": u.get("service") or "proposal",
                     "ref": u.get("ref") or "", "label": u.get("label") or "", "created_at": u.get("created_at") or ""} for u in usages],
        "customer_short": img.get("customer_short"), "subject_short": img.get("subject_short") or work.get("subject_short"),
        "work_title": work.get("title") or "", "products": prods, "project_id": img.get("project_id"),
        "created_at": img.get("created_at") or "",
    }


async def image_info(img: dict[str, Any], version_id: str | None = None) -> dict[str, Any]:
    """상단바 이미지 정보 행(§5.2)."""
    ver = await repo().get("versions", version_id or img.get("current_version_id"))
    if ver is None:
        raise not_found("버전", version_id or img.get("current_version_id"))
    gen = ver.get("generation") or {}
    native = ver.get("native") or {}
    date = (gen.get("created_at") or ver.get("created_at") or "")[:10]
    rows = [{"k": "출처 페이지", "v": "Winmate 이미지 작업", "href": views.route_result(img["work_id"], img["id"])}]
    model = gen.get("model") or ("로컬 합성" if gen.get("call") == "local" else "[확인 필요]")
    if native.get("w"):
        rows.append({"k": "원본", "v": f"{native['w']}×{native['h']} · PNG · {model} · 생성 {date}"})
    else:
        rows.append({"k": "원본", "v": f"{ver.get('width')}×{ver.get('height')} · PNG · {model} · 생성 {date}"})
    best = sorted([r for r in ver.get("renditions") or [] if r.get("kind") in ("fhd", "uhd", "uhd8k")], key=lambda r: int(r.get("w") or 0))
    if best:
        r = best[-1]
        up = (gen.get("upscale") or {}).get("method") if r.get("kind") == "fhd" else r.get("method")
        rows.append({"k": "저장본", "v": f"{r['w']}×{r['h']} · 업스케일({up or r.get('method') or 'lanczos3'})"})
    rows.append({"k": "생성", "v": f"{date} · Winmate 이미지 생성"})
    for i, ref in enumerate(gen.get("references") or [], 1):
        if ref.get("source_url"):
            rows.append({"k": f"참조 {i}", "v": ref.get("source_label") or ref.get("source_url"), "href": ref.get("source_url")})
    rows.append({"k": "사용 조건", "v": "“AI 생성 이미지” 표기 권장 · 대외 사용 범위 확인 필요"})
    uses = await repo().all("usages", where={"image_id": img["id"]})
    n = len([u for u in uses if u.get("service") == "proposal"])
    # 조감도(참조 이미지) · 시나리오(장면 이미지)에 쓰인 것도 같은 줄에 붙인다(통합 — 다른 기능 사용 등록이 보이게)
    others = [(lab, len({u.get("ref") for u in uses if u.get("service") == svc}))
              for svc, lab in (("birdseye", "조감도"), ("scenario", "시나리오"))]
    tail = "".join(f" · {lab} {k}건" for lab, k in others if k)
    rows.append({"k": "사용 이력", "v": f"Winmate 제안서 {n}건{tail}"})
    return {"image_id": img["id"], "version_id": ver["id"], "title": views.image_title(img), "rows": rows}


async def save_image_flag(image_id: str) -> dict[str, Any]:
    img = await get_image(image_id)
    if img.get("status") != "done":
        raise ApiError(409, "NOT_READY", "아직 만들어지지 않은 시안이에요")
    await repo().patch("images", image_id, {"saved": True, "saved_at": now_iso()})
    return {"image_id": image_id, "saved": True}


async def restore_version(image_id: str, n: int) -> dict[str, Any]:
    img = await get_image(image_id)
    vs = await versions_of(image_id)
    src = next((v for v in vs if int(v.get("n") or 0) == n), None)
    if src is None:
        raise not_found("버전", f"{image_id}@{n}")
    vid = new_id("imv")
    nn = max(int(v.get("n") or 0) for v in vs) + 1
    doc = {k: src.get(k) for k in ("master_file_id", "width", "height", "bytes", "native", "renditions", "generation", "qc", "confidential")}
    doc.update({"image_id": image_id, "n": nn, "parent_version_id": src["id"], "op": "restore",
                "op_params": {"restored_from": n}, "label": f"{src.get('label') or texts.version_label(n, src.get('op') or 'generate')} 복원",
                "created_at": now_iso()})
    saved = await repo().put("versions", vid, doc)
    await repo().patch("images", image_id, {"current_version_id": vid})
    await refresh_work(img["work_id"], register=False)
    return saved


# ── 감지 · 영역 ─────────────────────────────────────────

async def detections(img: dict[str, Any], kinds: list[str], version_id: str | None = None) -> dict[str, Any]:
    f = await caps.flags()
    vid = version_id or img.get("current_version_id")
    ver = await repo().get("versions", vid)
    if ver is None:
        raise not_found("버전", vid)
    if not f.bbox:
        raise capability_unsupported("지금 모델은 객체 인식을 지원하지 않아요")
    cached = await repo().get("detections", vid)
    if cached and set(kinds) <= set(cached.get("kinds") or []):
        return {"version_id": vid, "supported": True, "boxes": [b for b in cached.get("boxes") or [] if b["kind"] in kinds or b["kind"] == "product"]}
    boxes: list[dict[str, Any]] = []
    try:
        res = await llm.vision_task("img.detect", [ver["master_file_id"]],
                                    "이미지에서 물체(object) · 글자(text) · 사람(person) · 화면(screen)을 찾아 종류 · 이름 · 박스를 돌려줘.",
                                    llm.DetectOut, want_bbox=True, confidential=bool(ver.get("confidential")), timeout=30)
    except llm.ModelBlocked:
        res = None
    if res:
        for i, it in enumerate(res["json"].get("items") or []):
            if it.get("box") and len(it["box"]) == 4:
                boxes.append({"kind": it["kind"], "label": it.get("label") or it["kind"], "box": it["box"]})
        for b in res.get("boxes") or []:
            lab = str(b.get("label") or "")
            kind = next((k for k in ("text", "person", "screen") if k in lab.lower()), "object")
            if not any(x["box"] == b["box"] for x in boxes):
                boxes.append({"kind": kind, "label": lab or kind, "box": b["box"]})
    shorts = [str(x.get("short") or "") for x in ((await repo().get("works", img["work_id"]) or {}).get("conditions") or {}).get("products") or []]
    for j, p in enumerate((ver.get("qc") or {}).get("products") or []):
        if p.get("box"):
            name = shorts[0] if len(shorts) == 1 else (shorts[j] if j < len(shorts) else "")
            boxes.append({"kind": "product", "label": f"{name} 제품".strip() if name else "제품", "box": p["box"]})
    out = [{"id": f"det_{i + 1}", **b} for i, b in enumerate(boxes)]
    await repo().put("detections", vid, {"version_id": vid, "kinds": list(set(kinds) | {"object", "text", "person", "screen"}),
                                         "boxes": out})
    return {"version_id": vid, "supported": True, "boxes": [b for b in out if b["kind"] in kinds or b["kind"] == "product"]}


def region_status_label(st: str) -> str:
    return {"pending": "대기 · 적용 전", "applying": "적용 중", "applied": "적용됨 · 비교 중", "reverted": "되돌림",
            "failed": "실패 · 다시 적용"}.get(st, st)


def region_view(r: dict[str, Any]) -> dict[str, Any]:
    st = r.get("status") or "pending"
    return {"id": r["id"], "image_id": r["image_id"], "base_version_id": r.get("base_version_id"), "n": int(r.get("n") or 1),
            "shape": r.get("shape") or "rect", "rect": r.get("rect"), "mask_file_id": r.get("mask_file_id"),
            "detection_id": r.get("detection_id"), "label": r.get("label") or f"영역 {r.get('n')}", "instruction": r.get("instruction") or "",
            "status": st, "status_label": region_status_label(st), "result_version_id": r.get("result_version_id"),
            "protect_products": bool(r.get("protect_products", True)), "run_id": r.get("run_id"), "error": r.get("error"),
            "created_at": r.get("created_at") or ""}


async def regions_of(image_id: str) -> list[dict[str, Any]]:
    rs = await repo().all("regions", where={"image_id": image_id}, order_by="created_at")
    return sorted(rs, key=lambda r: int(r.get("n") or 0))


async def name_region(ver: dict[str, Any], rect: list[float] | None, n: int) -> str:
    """i2t 가 영역 크롭을 보고 “위치어 + 명사” 12자 이내 이름(실패 시 「영역 {n}」)."""
    if not rect:
        return f"영역 {n}"
    try:
        im = await load_image(ver["master_file_id"])
        w, h = im.size
        box = (int(rect[0] * w), int(rect[1] * h), max(int(rect[0] * w) + 2, int(rect[2] * w)), max(int(rect[1] * h) + 2, int(rect[3] * h)))
        crop = im.crop(box)
        import base64

        data, mime = await asyncio.to_thread(imaging.encode, crop, "PNG")
        cx = (rect[0] + rect[2]) / 2
        pos = "왼쪽" if cx < 0.36 else ("오른쪽" if cx > 0.64 else "가운데")
        res = await llm.vision_task("img.region_name", [{"data_b64": base64.b64encode(data).decode(), "mime": mime}],
                                    f"전체 이미지에서 {pos} 부분을 잘라낸 그림이다. “위치어 + 명사” 12자 이내 이름을 지어라(예 가운데 메뉴보드 화면).",
                                    llm.RegionNameOut, confidential=bool(ver.get("confidential")), timeout=8)
        name = ((res or {}).get("json") or {}).get("name") or ""
        name = name.strip()[:12]
        return name or f"영역 {n}"
    except Exception as exc:  # noqa: BLE001
        log.info("영역 이름을 짓지 못했습니다: %s", exc)
        return f"영역 {n}"


async def create_region(image_id: str, body: dict[str, Any]) -> dict[str, Any]:
    img = await get_image(image_id)
    ver = await current_version(img)
    if ver is None:
        raise ApiError(409, "NOT_READY", "아직 만들어지지 않은 시안이에요")
    existing = await regions_of(image_id)
    preset = body.get("preset")
    note = None
    global_instruction = None
    created: list[dict[str, Any]] = []
    if preset:
        word, kind, text = PRESET_TEXT[preset]
        f = await caps.flags()
        boxes: list[dict[str, Any]] = []
        if f.bbox:
            try:
                det = await detections(img, [kind])
                boxes = [b for b in det["boxes"] if b["kind"] == kind or (kind == "screen" and b["kind"] == "product")]
            except ApiError:
                boxes = []
        if kind == "screen" and not boxes:
            boxes = [{"id": None, "kind": "product", "label": "제품 화면", "box": p["box"]}
                     for p in ((ver.get("qc") or {}).get("products") or []) if p.get("box")]
        if preset == "screen_content":
            sug = await llm.json_task("img.screen_content", "장면에 맞는 사이니지 화면 콘텐츠를 한 문장으로 제안하라(로고 · 가격 · 수치 없이).",
                                      llm.ScreenContentOut, system=llm.SYSTEM_KO, timeout=8)
            text = (sug or {}).get("content_ko") or "장면에 어울리는 메뉴 사진 콘텐츠를 화면에 넣어줘"
        if not boxes:
            if preset == "screen_content":
                rect = [0.3, 0.25, 0.7, 0.6]
                boxes = [{"id": None, "label": "제품 화면", "box": rect}]
            else:
                return {"region": None, "regions": [], "note": NO_BBOX_NOTE, "global_instruction": text}
        for b in boxes[:3]:
            n = len(existing) + len(created) + 1
            box = b["box"]
            if kind == "screen" or b.get("kind") == "product":
                ix, iy = (box[2] - box[0]) * 0.03, (box[3] - box[1]) * 0.03
                box = [box[0] + ix, box[1] + iy, box[2] - ix, box[3] - iy]
            created.append(await _put_region(img, ver, n, shape="object" if b.get("id") else "rect", rect=box, mask_file_id=None,
                                             detection_id=b.get("id"), label=(await name_region(ver, box, n)) if not b.get("label") else
                                             (b["label"] if len(b["label"]) <= 12 else b["label"][:12]),
                                             instruction=text or ""))
        return {"region": region_view(created[0]), "regions": [region_view(r) for r in created], "note": note,
                "global_instruction": global_instruction}
    shape = body.get("shape") or "rect"
    rect = body.get("rect")
    if shape == "object":
        f = await caps.flags()
        if not f.bbox:
            raise capability_unsupported("지금 모델은 객체 인식을 지원하지 않아요")
        det = await repo().get("detections", ver["id"])
        hit = next((b for b in (det or {}).get("boxes") or [] if b["id"] == body.get("detection_id")), None)
        if hit is None:
            raise not_found("감지 결과", body.get("detection_id"))
        rect = hit["box"]
    if shape == "rect":
        if not rect or len(rect) != 4 or not (rect[2] > rect[0] and rect[3] > rect[1]):
            raise ApiError(422, "VALIDATION_ERROR", "사각 영역 [x0,y0,x1,y1](0..1)이 필요합니다")
        rect = [max(0.0, min(1.0, float(v))) for v in rect]
    if shape == "brush" and not body.get("mask_file_id"):
        raise ApiError(422, "VALIDATION_ERROR", "브러시 영역은 마스크 파일이 필요합니다")
    n = len(existing) + 1
    label = body.get("label") or await name_region(ver, rect, n)
    r = await _put_region(img, ver, n, shape=shape, rect=rect, mask_file_id=body.get("mask_file_id"),
                          detection_id=body.get("detection_id"), label=label, instruction=body.get("instruction") or "")
    return {"region": region_view(r), "regions": [region_view(r)], "note": None, "global_instruction": None}


async def _put_region(img: dict[str, Any], ver: dict[str, Any], n: int, *, shape: str, rect: list[float] | None,
                      mask_file_id: str | None, detection_id: str | None, label: str, instruction: str) -> dict[str, Any]:
    rid = new_id("ire")
    work = await repo().get("works", img["work_id"]) or {}
    has_products = bool((work.get("conditions") or {}).get("products"))
    doc = {"image_id": img["id"], "base_version_id": ver["id"], "n": n, "shape": shape, "rect": rect, "mask_file_id": mask_file_id,
           "detection_id": detection_id, "label": label, "instruction": instruction, "status": "pending", "result_version_id": None,
           "protect_products": has_products, "run_id": None, "error": None, "created_at": now_iso()}
    return await repo().put("regions", rid, doc)


async def patch_region(image_id: str, region_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    r = await repo().get("regions", region_id)
    if r is None or r.get("image_id") != image_id:
        raise not_found("수정 영역", region_id)
    upd = {k: v for k, v in changes.items() if v is not None}
    if r.get("status") in ("applied", "reverted", "failed") and ("rect" in upd or "mask_file_id" in upd):
        upd["status"] = "pending"
    return await repo().patch("regions", region_id, upd) or r


async def delete_region(image_id: str, region_id: str) -> None:
    r = await repo().get("regions", region_id)
    if r is None or r.get("image_id") != image_id:
        raise not_found("수정 영역", region_id)
    if r.get("status") == "applying":
        raise ApiError(409, "REGION_BUSY", "적용 중인 영역은 지울 수 없어요")
    await repo().delete("regions", region_id)


async def revert_region(image_id: str, region_id: str) -> dict[str, Any]:
    img = await get_image(image_id)
    r = await repo().get("regions", region_id)
    if r is None or r.get("image_id") != image_id:
        raise not_found("수정 영역", region_id)
    if r.get("status") != "applied":
        raise ApiError(409, "NOT_APPLIED", "적용된 영역만 되돌릴 수 있어요")
    base = r.get("base_version_id")
    await repo().patch("images", image_id, {"current_version_id": base})
    saved = await repo().patch("regions", region_id, {"status": "reverted"})
    await refresh_work(img["work_id"], register=False)
    return {"current_version_id": base, "region": region_view(saved or r)}


# ── 편집 · 보정 · 변형 · 비율(잡) ────────────────────────

async def start_edit(image_id: str, body: dict[str, Any]) -> dict[str, Any]:
    from . import runs

    img = await get_image(image_id)
    f = await caps.flags()
    work = await get_work(img["work_id"])
    base_vid = body.get("base_version_id") or img.get("current_version_id")
    if not base_vid:
        raise ApiError(409, "NOT_READY", "아직 만들어지지 않은 시안이에요")
    mode = body.get("mode") or "region"
    region_ids: list[str] = []
    if mode == "region":
        rs = await regions_of(image_id)
        ids = body.get("region_ids") or [r["id"] for r in rs if r.get("status") in ("pending", "failed")]
        region_ids = [r["id"] for r in rs if r["id"] in ids]
        if not region_ids:
            raise ApiError(422, "VALIDATION_ERROR", "적용할 영역이 없습니다")
        missing = [r for r in rs if r["id"] in region_ids and not (r.get("instruction") or "").strip()]
        if missing:
            raise ApiError(422, "INSTRUCTION_REQUIRED", f"영역 {missing[0].get('n')} 지시문을 적어 주세요")
        if not f.edit:
            # 편집 미지원: 작은 영역(≤ 2%)의 지우기만 로컬 인페인트로
            pass
        for rid in region_ids:
            await repo().patch("regions", rid, {"status": "applying", "error": None})
    else:
        if not f.edit:
            raise capability_unsupported("지금 모델로는 전체 수정을 할 수 없어요")
        if not (body.get("instruction") or "").strip():
            raise ApiError(422, "INSTRUCTION_REQUIRED", "수정 요청을 적어 주세요")
    params = {"base_version_id": base_vid, "region_ids": region_ids, "mode": mode, "instruction": body.get("instruction"),
              "protect_products": bool(body.get("protect_products", True)), "image_id": image_id}
    run = await runs.enqueue_run(work=work, kind="edit", params=params, n=0, base_image_id=image_id, shots=False,
                                 title=f"{img.get('label')} 부분 수정", summary=img.get("label"))
    await repo().patch("runs", run["id"], {"total": max(1, len(region_ids)), "image_ids": [image_id]})
    for rid in region_ids:
        await repo().patch("regions", rid, {"run_id": run["id"]})
    return {"job_id": run["job_id"], "run_id": run["id"], "status": "queued"}


async def adjust(image_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """동기 로컬 보정(§7.6) — 「밝기 올리기」 · 밝기 값 · 「주변과 밝기 맞추기」(영역). 모델 호출 없음."""
    img = await get_image(image_id)
    vid = body.get("base_version_id") or img.get("current_version_id")
    ver = await repo().get("versions", vid)
    if ver is None or ver.get("image_id") != image_id:
        raise not_found("버전", vid)
    base = await load_image(ver["master_file_id"])
    params: dict[str, Any] = {}
    if body.get("harmonize_region_id"):
        r = await repo().get("regions", body["harmonize_region_id"])
        if r is None or r.get("image_id") != image_id:
            raise not_found("수정 영역", body["harmonize_region_id"])
        mask = await region_mask(r, base.size)
        out = await asyncio.to_thread(imaging.harmonize_region, base, mask, config.ring_px())
        params = {"harmonize_region_id": r["id"], "region_n": r.get("n")}
    else:
        amount = body.get("brightness")
        if amount is None or body.get("preset") == "brighten":
            out = await asyncio.to_thread(imaging.brighten, base)
            params = {"preset": "brighten", "gamma": 0.9, "exposure": 0.08}
        else:
            out = await asyncio.to_thread(imaging.adjust_brightness, base, float(amount))
            params = {"brightness": float(amount)}
    gen = dict(ver.get("generation") or {})
    gen["fallbacks"] = list(gen.get("fallbacks") or [])
    gen["call"] = "local"
    saved = await create_version(img, op="adjust", master=out, generation=gen, parent_version_id=ver["id"], op_params=params,
                                 qc=ver.get("qc"), native=None, confidential=bool(ver.get("confidential")))
    await refresh_work(img["work_id"], register=False)
    return saved


async def region_mask(region: dict[str, Any], size: tuple[int, int]) -> Image.Image:
    if region.get("shape") == "brush" and region.get("mask_file_id"):
        from .filestore import load_bytes

        data = await load_bytes(region["mask_file_id"])
        m = imaging.open_rgba(data)
        return imaging.mask_from_image(m, size)
    return imaging.rect_mask(size, region.get("rect") or [0.4, 0.4, 0.6, 0.6])


async def next_letters(base_image_id: str, n: int) -> list[str]:
    sib = [i for i in await repo().all("images", where={"run_kind": "variants"}) if i.get("base_image_id") == base_image_id]
    used = len(sib)
    return [config.VARIANT_LETTERS[(used + i) % 26] for i in range(n)]


async def start_variants(image_id: str, body: dict[str, Any]) -> dict[str, Any]:
    from . import runs

    img = await get_image(image_id)
    if img.get("status") != "done":
        raise ApiError(409, "NOT_READY", "완성된 시안으로만 변형을 만들 수 있어요")
    work = await get_work(img["work_id"])
    n = int(body.get("count") or 4)
    letters = await next_letters(image_id, n)
    f = await caps.flags()
    mode = "edit" if f.edit else ("ref" if f.ref_images else "text")
    params = {"base_version_id": img.get("current_version_id"), "axis": body.get("axis") or "any",
              "instruction": body.get("instruction"), "mode": mode, "aspect": img.get("aspect"), "style": img.get("style")}
    run = await runs.enqueue_run(work=work, kind="variants", params=params, n=n, base_image_id=image_id,
                                 labels=[f"{x} · 변형" for x in letters], letters=letters, aspect=img.get("aspect"),
                                 title=f"{img.get('label')} 변형 {n}장", summary=f"{img.get('label')} 기준 · 제품 배치 유지")
    return {"job_id": run["job_id"], "run_id": run["id"], "status": "queued"}


async def start_renditions(image_id: str, body: dict[str, Any]) -> dict[str, Any]:
    from . import runs

    img = await get_image(image_id)
    if img.get("status") != "done":
        raise ApiError(409, "NOT_READY", "완성된 시안으로만 비율을 만들 수 있어요")
    f = await caps.flags()
    fit = body.get("fit") or "recompose"
    up = body.get("upscale") or "2x"
    aspects = list(dict.fromkeys(body.get("aspects") or []))
    base_aspect = img.get("aspect") or "16:9"
    needs_model = [a for a in aspects if a != base_aspect]
    if up == "4x" and config.upscaler() == "none":
        raise capability_unsupported("×4는 업스케일 모델이 있어야 해요", upscale=up)
    if needs_model and fit == "recompose" and not (f.ref_images or f.edit):
        raise capability_unsupported("지금 모델로는 다시 구성할 수 없어요", fit=fit)
    if needs_model and fit == "outpaint" and not f.edit:
        raise capability_unsupported("지금 모델로는 바깥 채우기를 할 수 없어요", fit=fit)
    work = await get_work(img["work_id"])
    stored = dict(img.get("aspect_instructions") or {})
    instr = {**stored, **(body.get("instructions") or {})}
    params = {"base_version_id": img.get("current_version_id"), "aspects": aspects, "fit": fit, "upscale": up,
              "instructions": instr, "base_aspect": base_aspect, "style": img.get("style")}
    labels = [f"{img.get('label')} · {a}" for a in aspects]
    run = await runs.enqueue_run(work=work, kind="renditions", params=params, n=len(aspects), base_image_id=image_id,
                                 labels=labels, title=f"{img.get('label')} · {len(aspects)}개 비율", aspects=aspects,
                                 summary=f"{' + '.join(aspects)} · {config.UPSCALE_LABEL.get(up, up)} 업스케일")
    return {"job_id": run["job_id"], "run_id": run["id"], "status": "queued"}


# ── 사용 등록 ───────────────────────────────────────────

async def add_usage(image_id: str, body: dict[str, Any]) -> dict[str, Any]:
    img = await get_image(image_id)
    ver = await repo().get("versions", body["version_id"])
    if ver is None or ver.get("image_id") != image_id:
        raise not_found("버전", body["version_id"])
    uid = f"{image_id}|{body['service']}|{body['ref']}"
    doc = {"image_id": image_id, "version_id": body["version_id"], "service": body["service"], "ref": body["ref"],
           "label": body.get("label") or "", "created_at": now_iso()}
    await repo().put("usages", uid, doc)
    await refresh_work(img["work_id"])
    return doc


async def delete_usage(image_id: str, service: str, ref: str) -> None:
    img = await get_image(image_id)
    await repo().delete("usages", f"{image_id}|{service}|{ref}")
    await refresh_work(img["work_id"])


# ── 자유 입력 해석(R6) ──────────────────────────────────

async def interpret(image_id: str, text: str, screen: str) -> dict[str, Any]:
    img = await get_image(image_id)
    if screen in ("result", "edit"):
        out = await llm.json_task("img.edit_intent", f"시안: {img.get('label')}\n수정 요청: {text}\n\n"
                                  "영역 지정형(한 부분만 바꿈) · 전체 수정형(전체 분위기 · 색) · 변형형(다른 버전 여러 장) 중 하나로 나눠라.",
                                  llm.EditIntentOut, system=llm.SYSTEM_KO, timeout=10)
        if out is None:
            return {"action": "region_edit", "instruction": text, "region": None, "options": {}, "question": None}
        if out["action"] == "ask":
            return {"action": "ask", "instruction": out.get("instruction_ko") or text, "region": None, "options": {},
                    "question": out.get("question") or "어느 부분을 바꿀까요?"}
        if out["action"] == "region_edit":
            region = None
            kind = out.get("target_kind") or "none"
            boxes: list[dict[str, Any]] = []
            f = await caps.flags()
            if f.bbox and kind in ("screen", "text", "person", "object"):
                try:
                    det = await detections(img, [kind if kind != "object" else "object"])
                    boxes = [b for b in det["boxes"] if b["kind"] in (kind, "product")]
                except ApiError:
                    boxes = []
            rect = boxes[0]["box"] if boxes else [0.3, 0.25, 0.7, 0.65]
            ver = await current_version(img)
            if ver is not None:
                n = len(await regions_of(image_id)) + 1
                r = await _put_region(img, ver, n, shape="object" if boxes else "rect", rect=rect, mask_file_id=None,
                                      detection_id=boxes[0]["id"] if boxes else None,
                                      label=(out.get("region_hint") or f"영역 {n}")[:12], instruction=out.get("instruction_ko") or text)
                region = {"id": r["id"], "rect": rect, "label": r["label"]}
            await repo().patch("images", image_id, {"edit_echo": text})
            return {"action": "region_edit", "instruction": out.get("instruction_ko") or text, "region": region, "options": {},
                    "question": None}
        return {"action": out["action"], "instruction": out.get("instruction_en") or out.get("instruction_ko") or text,
                "region": None, "options": {}, "question": None}
    if screen == "variants":
        out = await llm.json_task("img.variant_request", f"변형 요청: {text}\n\n특정 비율의 구도 지시인지(aspect_instruction), 새 변형 지시인지(variants) 나눠라.",
                                  llm.VariantRequestOut, system=llm.SYSTEM_KO, timeout=10)
        if out and out["action"] == "aspect_instruction" and out.get("aspect"):
            stored = dict(img.get("aspect_instructions") or {})
            stored[out["aspect"]] = out.get("instruction") or text
            await repo().patch("images", image_id, {"aspect_instructions": stored})
            return {"action": "aspect_instruction", "instruction": stored[out["aspect"]], "aspect": out["aspect"], "region": None,
                    "options": {}, "question": None}
        if out and out["action"] == "ask":
            return {"action": "ask", "instruction": text, "region": None, "options": {}, "question": out.get("question")}
        return {"action": "variants", "instruction": (out or {}).get("instruction") or text, "region": None, "options": {}, "question": None}
    out = await llm.json_task("img.export_request", f"내보내기 요청: {text}\n\n캡션 · 영문 파일명 · 원본 함께 · 형식 · AI 표기 · 다른 시안 함께를 골라라.",
                              llm.ExportRequestOut, system=llm.SYSTEM_KO, timeout=10)
    if out is None:
        return {"action": "ask", "instruction": text, "region": None, "options": {}, "question": "어떻게 내보낼까요?"}
    q = out.pop("question", None)
    return {"action": "export_options" if not q else "ask", "instruction": text, "region": None, "options": out, "question": q}


async def caption(image_id: str) -> str:
    img = await get_image(image_id)
    work = await repo().get("works", img["work_id"]) or {}
    out = await llm.json_task("img.caption", f"장면: {work.get('description')}\n시안: {img.get('label')}\n\n"
                              "제안서 이미지 아래에 달 한 줄 캡션(20자 안팎, 수치 · 가격 없이)을 써라.", llm.CaptionOut,
                              system=llm.SYSTEM_KO, timeout=10)
    base = ((out or {}).get("caption") or work.get("title") or img.get("label") or "").strip()
    return f"{base} (AI 생성 이미지)" if "AI 생성" not in base else base


async def english_filename(image_id: str, ext: str, version_id: str | None) -> str:
    img = await get_image(image_id)
    work = await repo().get("works", img["work_id"]) or {}
    ver = await repo().get("versions", version_id or img.get("current_version_id")) or {}
    out = await llm.json_task("img.filename_en", f"고객사 약칭: {img.get('customer_short') or ''}\n주제: {work.get('subject_short') or ''}\n"
                              f"시안 라벨: {img.get('label')}\n\n파일명에 쓸 영문 단어(공백 없이 PascalCase)로 바꿔라.", llm.FilenameOut,
                              system=llm.SYSTEM_KO, timeout=10)
    import re

    def clean(s: str | None) -> str:
        return re.sub(r"[^A-Za-z0-9]+", "", s or "")

    # 원문에 없는 조각(고객사 · 주제)은 LLM 이 채워도 쓰지 않는다(지어내지 않기)
    parts = [clean((out or {}).get("customer_en")) if img.get("customer_short") else "",
             clean((out or {}).get("subject_en")) if work.get("subject_short") else "",
             clean((out or {}).get("label_en")) or clean(img.get("letter") or "") or "Draft"]
    name = "_".join(p for p in parts if p) or "Image"
    return f"{name}_v{int(ver.get('n') or 1)}.{ext}"


async def owner_of(img: dict[str, Any]) -> str:
    return img.get("owner") or current_user().id
