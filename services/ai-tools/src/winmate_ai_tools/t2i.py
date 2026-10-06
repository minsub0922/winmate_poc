"""T2I(이미지 생성 · 편집) — POST /v1/t2i/generate · /v1/t2i/edit.

생성
- aspect(기본 T2I_DEFAULT_ASPECT). Gemini 가 받지 않는 비율이면 가장 가까운 비율로 만든 뒤 가운데를 잘라 맞춘다(aspect_cropped).
- 참조 이미지: T2I_SUPPORTS_REFERENCE_IMAGES=false 면 빼고 fallbacks 에 references_dropped(호출한 쪽이 로컬 합성 가능).
  T2I_MAX_REFERENCE_IMAGES 를 넘으면 앞에서부터 그만큼만(warnings).
- n > T2I_IMAGES_PER_CALL 이면 여러 번 부른다. 하루 한도는 이미지 장수로 센다.
- 결과는 files 서비스에 저장(source=generated, meta={task, prompt, aspect, provider, model, references, ai_generated, …metadata}).

편집
- mask(이미지 또는 box) + T2I_SUPPORTS_MASK=false(기본): 마스크 상자(+여백)를 잘라 제공자 편집 → 원래 크기로 → 마스크 안쪽만
  페더로 붙인다(mask_crop_paste). 마스크 밖 픽셀은 원본과 바이트 단위로 같다(PNG 로 저장).
- mask + T2I_SUPPORTS_MASK=true(+ 제공자가 지원): 전체 이미지 + 마스크로 편집하고, 마찬가지로 마스크 안쪽만 합성한다.
- aspect 가 원본과 다르면: 캔버스를 넓혀(가장자리 반사 + 블러) "자연스럽게 확장" 지시로 편집 → 원래 영역은 원본 픽셀로(outpaint_extend).
- T2I_SUPPORTS_EDIT=false: 참조 이미지를 받으면 원본을 참조로 넣어 생성(edit_as_generate), 아니면 501 EDIT_UNSUPPORTED.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from PIL import Image, ImageOps

from winmate_common.contracts import ContractViolation
from winmate_common.errors import ApiError

from . import config, imaging
from .errors import files_unavailable, invalid, unsupported
from .providers.base import EditCall, Ref, T2ICall
from .runtime import Call, track
from .schemas import ReferenceImage, T2IEditRequest, T2IGenerateRequest

log = logging.getLogger("winmate.ai_tools.t2i")

# (이름, 바이트, mime, meta, confidential) → file_id
Sink = Callable[[str, bytes, str, dict[str, Any], bool], Awaitable[str]]

REF_MAX_SIDE = 1536
EDIT_MAX_SIDE = 1536
_ROLE = {
    "product": "product reference — keep the product's exact shape, proportions, bezel, colors and logo",
    "style": "style reference — borrow only color palette, materials and lighting mood",
    "composition": "composition reference — follow its layout and camera angle",
    "subject": "subject reference — depict this subject",
    "base": "base image — reproduce this image faithfully and apply only the requested change",
}
_STRENGTH = {"low": "loosely", "mid": "moderately", "high": "closely"}


async def files_sink(name: str, data: bytes, mime: str, meta: dict[str, Any], confidential: bool) -> str:
    from winmate_common.platform import save_file

    project_id = meta.get("project_id") if isinstance(meta.get("project_id"), str) else None
    try:
        res = await save_file(name, data, mime, source="generated", confidential=confidential, project_id=project_id, meta=meta)
    except ApiError as exc:
        raise files_unavailable(exc.message, upstream_code=exc.code) from exc
    except ContractViolation as exc:
        raise files_unavailable(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — httpx 연결 오류 등
        raise files_unavailable(f"{type(exc).__name__}: {exc}") from exc
    fid = (res or {}).get("id") or (res or {}).get("file_id")
    if not fid:
        raise files_unavailable("응답에 파일 id 가 없습니다", response=str(res)[:200])
    return str(fid)


def ref_text(refs: list[Ref], offset: int = 0) -> str:
    if not refs:
        return ""
    lines = ["Reference images (in the order attached):"]
    for i, r in enumerate(refs):
        lines.append(f"- Image {i + 1 + offset}: {_ROLE.get(r.role, r.role)} (follow {_STRENGTH.get(r.strength, 'moderately')}).")
    return "\n".join(lines)


def compose_prompt(prompt: str, *, negative: str | None = None, style: str | None = None, refs: list[Ref] | None = None,
                   offset: int = 0) -> str:
    parts = [prompt.strip()]
    if style:
        parts.append(f"Style: {style.strip()}")
    if negative:
        parts.append(f"Avoid: {negative.strip()}")
    rt = ref_text(refs or [], offset)
    if rt:
        parts.append(rt)
    return "\n\n".join(p for p in parts if p)


def provider_aspect(provider_name: str, aspect: str, ratio: float) -> str:
    if provider_name == "gemini":
        canon = aspect.replace(" ", "")
        return canon if canon in imaging.GEMINI_ASPECTS else imaging.nearest_aspect(ratio, imaging.GEMINI_ASPECTS)
    return aspect


async def _load(ref: dict[str, Any], max_side: int) -> imaging.Img:
    raw, _ = await imaging.load_raw(ref)
    return await asyncio.to_thread(imaging.prepare, raw, max_side)


async def load_refs(cfg: config.CapConfig, refs: list[ReferenceImage] | None,
                    fallbacks: list[str], warnings: list[str]) -> tuple[list[Ref], list[dict[str, Any]]]:
    """참조 이미지를 불러온다 → (제공자에 보낼 참조, 카세트 키 · 메타용 요약). 지원 안 하면 빼고 fallback 을 남긴다."""
    refs = refs or []
    loaded = await asyncio.gather(*(_load(r.model_dump(exclude_none=True, exclude={"role", "strength"}), REF_MAX_SIDE) for r in refs))
    summary = [{"file_id": r.file_id, "role": r.role, "strength": r.strength, "sha256": img.sha256} for r, img in zip(refs, loaded)]
    send = [Ref(img=img, role=r.role, strength=r.strength) for r, img in zip(refs, loaded)]
    if send and not cfg.supports_reference_images:
        fallbacks.append("references_dropped")
        send = []
    if len(send) > cfg.max_reference_images:
        warnings.append(f"references_truncated: 참조 이미지는 {cfg.max_reference_images}장까지만 보냈습니다({len(send)}장)")
        send = send[: cfg.max_reference_images]
    return send, summary


async def _save_all(call: Call, req: Any, pils_or_bytes: list[tuple[bytes, str, int, int]], *, sink: Sink | None,
                    meta_base: dict[str, Any]) -> list[dict[str, Any]]:
    sink = sink or files_sink
    out = []
    for i, (data, mime, w, h) in enumerate(pils_or_bytes):
        ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime, "png")
        meta = {**meta_base, "index": i, **(req.metadata or {}), "ai_generated": True}
        fid = await sink(f"{req.task}_{call.id}_{i + 1}.{ext}", data, mime, meta, req.confidential)
        out.append({"file_id": fid, "width": w, "height": h, "mime": mime})
    return out


async def _replay_images(call: Call, req: Any, hit: dict[str, Any], sink: Sink | None) -> dict[str, Any]:
    resp = dict(hit["response"])
    blobs = hit.get("_blobs") or []
    items = []
    for i, img in enumerate(resp.get("images") or []):
        data = blobs[i] if i < len(blobs) else b""
        if not data:
            raise ApiError(404, "CASSETTE_MISS", "카세트의 이미지 파일이 없습니다", {"key": call.key, "index": i})
        items.append((data, img.get("mime") or "image/png", int(img.get("width") or 0), int(img.get("height") or 0)))
    resp["images"] = await _save_all(call, req, items, sink=sink, meta_base={
        "task": req.task, "prompt": req.prompt, "replayed": True, "cassette_key": call.key,
        "provider": hit.get("provider"), "model": hit.get("model")})
    return call.done(resp)


ASPECT_EXACT = 0.005    # 이보다 작게 다르면 그대로
ASPECT_FLAG = 0.03      # 이보다 크게 달라 잘랐으면 fallbacks 에 aspect_cropped (Gemini 1K 출력은 1~3% 안팎 오차)


def _postprocess(data: bytes, mime: str, ratio: float | None) -> tuple[bytes, str, int, int, bool]:
    """요청 비율과 다르면 가운데를 잘라 정확히 맞춘다 → (바이트, mime, w, h, 크게 잘랐는지)."""
    im = imaging.open_image(data)
    w, h = im.size
    dev = abs(w / h - ratio) / ratio if ratio else 0.0
    if ratio is not None and dev > ASPECT_EXACT:
        cropped = imaging.center_crop(imaging.to_rgb(im), ratio, tolerance=ASPECT_EXACT)
        out, m = imaging.encode(cropped, "PNG")
        return out, m, cropped.width, cropped.height, dev > ASPECT_FLAG
    if mime not in ("image/png", "image/jpeg", "image/webp"):
        out, m = imaging.encode(imaging.to_rgb(im), "PNG")
        return out, m, w, h, False
    return data, mime, w, h, False


# ── 생성 ───────────────────────────────────────────────────

async def generate(req: T2IGenerateRequest, *, sink: Sink | None = None) -> dict[str, Any]:
    cfg = config.load("t2i")
    async with track("t2i", req.task, request=req.model_dump(exclude_none=True), confidential=req.confidential,
                     cfg=cfg, units=req.n) as call:
        call.check_policy()
        aspect = (req.aspect or cfg.default_aspect).strip()
        ratio = imaging.parse_aspect(aspect)
        fallbacks: list[str] = []
        warnings: list[str] = []
        refs, ref_summary = await load_refs(cfg, req.reference_images, fallbacks, warnings)
        kp = {"op": "generate", "prompt": req.prompt, "negative_prompt": req.negative_prompt, "aspect": aspect, "n": req.n,
              "style": req.style, "seed": req.seed,
              "references": [{"image": r["sha256"], "role": r["role"], "strength": r["strength"]} for r in ref_summary]}
        hit = await call.replay(kp)
        if hit is not None:
            return await _replay_images(call, req, hit, sink)
        await call.acquire()
        provider = call.provider()
        prov_aspect = provider_aspect(provider.name, aspect, ratio)
        size = imaging.size_for_aspect(ratio, cfg.max_side_px, multiple=64 if provider.name == "openai_compat" else 1)
        prompt = compose_prompt(req.prompt, negative=req.negative_prompt, style=req.style, refs=refs)
        images: list[Any] = []
        remaining, rounds = req.n, 0
        while remaining > 0 and rounds < req.n * 2:
            rounds += 1
            k = min(cfg.images_per_call, remaining)
            res = await call.invoke(provider.generate, cfg, T2ICall(task=req.task, prompt=prompt, aspect=prov_aspect, ratio=ratio,
                                                                     size=size, n=k, refs=refs,
                                                                     seed=None if req.seed is None else req.seed + len(images)))
            got = res.images[:k]
            images += got
            remaining -= len(got)
            call.model = res.model or cfg.model
            warnings += [w for w in res.warnings if w not in warnings]
        if len(images) < req.n:
            warnings.append(f"fewer_images: {req.n}장 중 {len(images)}장만 만들었습니다")
        processed = []
        for g in images:
            data, mime, w, h, cropped = await asyncio.to_thread(_postprocess, g.data, g.mime, ratio)
            if cropped and "aspect_cropped" not in fallbacks:
                fallbacks.append("aspect_cropped")
            processed.append((data, mime, w, h))
        meta = {"task": req.task, "prompt": req.prompt, "negative_prompt": req.negative_prompt, "style": req.style,
                "seed": req.seed, "aspect": aspect, "provider": call.provider_name, "model": call.model, "call_id": call.id,
                "references": ref_summary, "fallbacks": fallbacks, "operation": "generate"}
        saved = await _save_all(call, req, processed, sink=sink, meta_base={k: v for k, v in meta.items() if v is not None})
        out = {"provider": call.provider_name, "model": call.model, "images": saved, "fallbacks": fallbacks, "warnings": warnings}
        call.record(kp, out, blobs=[(d, {"image/jpeg": "jpg", "image/webp": "webp"}.get(m, "png")) for d, m, _, _ in processed])
        return call.done(out)


# ── 편집 ───────────────────────────────────────────────────

OUTPAINT_HINT = ("The blurred border areas were added only to extend the frame. Replace them with natural, seamless content "
                 "that continues the scene (same perspective, lighting and style). Keep the sharp central content unchanged.")
REGION_HINT = "This is a cropped region of a larger image; keep the edges consistent with the surroundings."
EDIT_HINT = "Keep the composition, perspective, lighting and everything not mentioned unchanged."


async def _load_mask(req: T2IEditRequest, size: tuple[int, int]) -> tuple[Image.Image | None, Any]:
    m = req.mask
    if m is None:
        return None, None
    if m.box is not None:
        return imaging.mask_from_box(m.box, size), {"box": [round(float(v), 6) for v in m.box]}
    raw, _ = await imaging.load_raw(m.model_dump(exclude_none=True, exclude={"box"}))
    mask = await asyncio.to_thread(lambda: imaging.mask_from_image(imaging.open_image(raw), size))
    data, _ = imaging.encode(mask, "PNG")
    return mask, {"image": hashlib.sha256(data).hexdigest()}


async def edit(req: T2IEditRequest, *, sink: Sink | None = None) -> dict[str, Any]:
    cfg = config.load("t2i")
    async with track("t2i", req.task, request=req.model_dump(exclude_none=True), confidential=req.confidential,
                     cfg=cfg, units=req.n) as call:
        call.check_policy()
        fallbacks: list[str] = []
        warnings: list[str] = []
        raw, _ = await imaging.load_raw(req.image.model_dump(exclude_none=True))
        base_sha = hashlib.sha256(raw).hexdigest()
        base = await asyncio.to_thread(lambda: imaging.to_rgb(ImageOps.exif_transpose(imaging.open_image(raw))))
        mask, mask_key = await _load_mask(req, base.size)
        if mask is not None and mask.getbbox() is None:
            raise invalid("마스크에 수정할 영역이 없습니다", code="EMPTY_MASK")
        target_ratio = imaging.parse_aspect(req.aspect) if req.aspect else None
        refs, ref_summary = await load_refs(cfg, req.reference_images, fallbacks, warnings)
        kp = {"op": "edit", "image": base_sha, "mask": mask_key, "prompt": req.prompt, "aspect": req.aspect, "n": req.n,
              "references": [{"image": r["sha256"], "role": r["role"], "strength": r["strength"]} for r in ref_summary]}
        hit = await call.replay(kp)
        if hit is not None:
            return await _replay_images(call, req, hit, sink)

        if not cfg.supports_edit and not cfg.supports_reference_images:
            raise unsupported("EDIT_UNSUPPORTED", "지금 설정된 T2I 제공자는 이미지 편집도 참조 이미지도 지원하지 않습니다",
                              env="T2I_SUPPORTS_EDIT=false, T2I_SUPPORTS_REFERENCE_IMAGES=false")
        await call.acquire()
        provider = call.provider()
        as_generate = not cfg.supports_edit
        if as_generate:
            fallbacks.append("edit_as_generate")

        # 작업 캔버스와 수정 영역(255) — 비율이 다르면 캔버스를 넓힌다
        working, region = base, mask
        prompt = req.prompt.strip()
        w, h = base.size
        if target_ratio is not None and abs((w / h) - target_ratio) / target_ratio > 0.01:
            def _extend() -> tuple[Image.Image, Image.Image]:
                canvas, box = imaging.extend_canvas(base, target_ratio)
                m = Image.new("L", canvas.size, 255)
                m.paste(mask if mask is not None else Image.new("L", base.size, 0), box[:2])
                return canvas, m

            working, region = await asyncio.to_thread(_extend)
            fallbacks.append("outpaint_extend")
            prompt = f"{prompt}\n\n{OUTPAINT_HINT}" if prompt else OUTPAINT_HINT
        native_mask = region is not None and cfg.supports_mask and provider.native_mask and not as_generate
        if req.mask is not None and not native_mask:
            fallbacks.append("mask_crop_paste")

        async def edit_once(img: Image.Image, text: str, mask_img: Image.Image | None) -> Image.Image:
            send = img
            if max(send.size) > EDIT_MAX_SIDE:
                send = send.copy()
                send.thumbnail((EDIT_MAX_SIDE, EDIT_MAX_SIDE), Image.Resampling.LANCZOS)
            src = await asyncio.to_thread(imaging.from_pil, send, "PNG")
            ratio = send.width / send.height
            aspect = imaging.nearest_aspect(ratio, imaging.GEMINI_ASPECTS) if provider.name == "gemini" \
                else f"{send.width}:{send.height}"
            size = (send.width, send.height)
            if as_generate:
                res = await call.invoke(provider.generate, cfg, T2ICall(
                    task=req.task, prompt=compose_prompt(text, refs=[Ref(src, "base", "high"), *refs]), aspect=aspect,
                    ratio=ratio, size=size, n=1, refs=[Ref(src, "base", "high"), *refs]))
            else:
                mimg = None
                if mask_img is not None:
                    m = mask_img if mask_img.size == send.size else mask_img.resize(send.size, Image.Resampling.NEAREST)
                    mimg = await asyncio.to_thread(imaging.from_pil, m, "PNG")
                res = await call.invoke(provider.edit, cfg, EditCall(
                    task=req.task, image=src, prompt=compose_prompt(f"Edit the first image: {text}\n{EDIT_HINT}", refs=refs, offset=1),
                    aspect=aspect, size=size, mask=mimg, refs=refs, n=1))
            call.model = res.model or cfg.model
            return await asyncio.to_thread(lambda: imaging.to_rgb(imaging.open_image(res.images[0].data)))

        results: list[Image.Image] = []
        for i in range(req.n):
            text = prompt if i == 0 else f"{prompt}\n(variation {i + 1})"
            if region is None:
                edited = await edit_once(working, text, None)
                want = working.width / working.height
                dev = abs(edited.width / edited.height - want) / want
                if dev > ASPECT_EXACT:
                    edited = imaging.center_crop(edited, want, tolerance=ASPECT_EXACT)
                    if dev > ASPECT_FLAG and "aspect_cropped" not in fallbacks:
                        fallbacks.append("aspect_cropped")
                results.append(edited)
            elif native_mask:
                edited = await edit_once(working, text, region)
                feather = max(2.0, min(working.size) * 0.01)
                results.append(await asyncio.to_thread(imaging.composite, working, edited, region, feather))
            else:
                box = imaging.crop_box_for_mask(region)
                assert box is not None
                crop = working.crop(box)
                mcrop = region.crop(box)
                sw, sh = imaging.send_size(*crop.size)
                send = crop.resize((sw, sh), Image.Resampling.LANCZOS) if (sw, sh) != crop.size else crop
                edited = await edit_once(send, f"{text}\n{REGION_HINT}", None)
                feather = max(2.0, min(crop.size) * 0.02)

                def _paste(crop: Image.Image = crop, edited: Image.Image = edited, mcrop: Image.Image = mcrop,
                           box: tuple[int, int, int, int] = box, feather: float = feather) -> Image.Image:
                    patched = imaging.composite(crop, edited, mcrop, feather)
                    out = working.copy()
                    out.paste(patched, box[:2])
                    return out

                results.append(await asyncio.to_thread(_paste))

        processed = []
        for im in results:
            data, mime = await asyncio.to_thread(imaging.encode, im, "PNG")
            processed.append((data, mime, im.width, im.height))
        meta = {"task": req.task, "prompt": req.prompt, "aspect": req.aspect, "provider": call.provider_name,
                "model": call.model, "call_id": call.id, "operation": "edit", "source_file_id": req.image.file_id,
                "source_sha256": base_sha, "mask": mask_key, "references": ref_summary, "fallbacks": fallbacks}
        saved = await _save_all(call, req, processed, sink=sink, meta_base={k: v for k, v in meta.items() if v is not None})
        out = {"provider": call.provider_name, "model": call.model, "images": saved, "fallbacks": fallbacks, "warnings": warnings}
        call.record(kp, out, blobs=[(d, "png") for d, _, _, _ in processed])
        return call.done(out)
