"""시안 하나를 만드는 공통 단계 — T2I 호출(재시도 · 오류 구분) · 품질 확인(i2t) · 후처리(비율 · fhd 마스터 · 메타 · 버전) ·
진행 이벤트(jobs SSE `step` · `progress` · `partial`) · 지연 EMA(진행률 추정).
"""
from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Any

from PIL import Image

from winmate_common.ai import ai
from winmate_common.ids import now_iso
from winmate_common.jobs import JobCanceled, JobContext

from . import config, imaging, llm, texts
from .filestore import load_image, thumb_url
from .images import create_version
from .store import repo

log = logging.getLogger("winmate.image.shots")

STAGE_LABEL = {"waiting": "대기 중", "composing": "장면 구성 중", "rendering": "렌더링 중", "qc": "품질 확인 중", "done": "완료",
               "held": "보류 · 대안 필요", "canceled": "취소됨", "failed": "실패"}
STATE_FRAC = {"waiting": 0.0, "composing": 0.1, "rendering": 0.5, "qc": 0.85, "done": 1.0, "failed": 1.0, "canceled": 1.0,
              "held": 0.0}


class ShotCanceled(Exception):
    pass


class ShotFailed(Exception):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


# ── 지연 EMA ─────────────────────────────────────────────

def ema_key(provider: str | None, model: str | None, op: str) -> str:
    return f"{provider or 'unknown'}|{model or 'unknown'}|{op}"


async def expected_s(key: str) -> float:
    doc = await repo().get("stats", key)
    if doc and doc.get("ema_s"):
        return max(0.5, float(doc["ema_s"]))
    return config.default_ema_s()


async def update_ema(key: str, seconds: float, alpha: float = 0.3) -> None:
    def fn(doc: dict[str, Any]) -> None:
        prev = doc.get("ema_s")
        doc["ema_s"] = seconds if not prev else (alpha * seconds + (1 - alpha) * float(prev))
        doc["n"] = int(doc.get("n") or 0) + 1

    try:
        if await repo().get("stats", key) is None:
            await repo().put("stats", key, {"ema_s": seconds, "n": 1})
        else:
            await repo().mutate("stats", key, fn)
    except Exception as exc:  # noqa: BLE001
        log.info("EMA 저장 실패: %s", exc)


# ── 상태 · 이벤트 ────────────────────────────────────────

async def check(ctx: JobContext | None, image_id: str | None = None, run_id: str | None = None) -> None:
    """취소 확인 — 잡 취소 플래그 · run 취소 · 시안 취소."""
    if ctx is not None:
        await ctx.check_cancel()
    if run_id:
        run = await repo().get("runs", run_id)
        if run is not None and run.get("status") == "canceled":
            raise JobCanceled()
    if image_id:
        img = await repo().get("images", image_id)
        if img is not None and img.get("status") == "canceled":
            raise ShotCanceled()


async def set_shot(ctx: JobContext | None, image_id: str, state: str, *, stage: str | None = None, label: str | None = None,
                   **fields: Any) -> dict[str, Any] | None:
    upd: dict[str, Any] = {"status": state, "stage_label": label or STAGE_LABEL.get(state, ""), **fields}
    if state in ("composing", "rendering") and "started_at" not in fields:
        cur = await repo().get("images", image_id)
        if cur is not None and not cur.get("started_at"):
            upd["started_at"] = now_iso()

    def fn(doc: dict[str, Any]) -> None:
        if doc.get("status") == "canceled" and state not in ("canceled",):
            return
        doc.update(upd)

    img = await repo().mutate("images", image_id, fn, missing_ok=True)
    if ctx is not None and img is not None:
        try:
            await ctx.jobs.emit(ctx.job.id, "step", {
                "stage": stage or {"composing": "compose", "rendering": "render", "qc": "qc", "done": "postprocess"}.get(state, state),
                "label": img.get("stage_label") or "",
                "shot": {"image_id": image_id, "state": img.get("status"), "progress": int(STATE_FRAC.get(img.get("status") or "", 0) * 100),
                         "eta_s": None, "preview_file_id": img.get("preview_file_id")}})
        except Exception as exc:  # noqa: BLE001
            log.info("이벤트 실패: %s", exc)
    return img


async def run_progress(ctx: JobContext | None, run_id: str, *, base: int = 20) -> None:
    """머리 진행률: 제품 외형 맞춤 10 · 장면 구성 10 · 렌더링 65 · 품질 확인 10 · 후처리 5."""
    shots = [s for s in await repo().all("images", where={"run_id": run_id}) if s.get("status") not in ("held", "canceled")]
    if not shots:
        return
    frac = sum(STATE_FRAC.get(s.get("status") or "", 0.0) for s in shots) / len(shots)
    done = sum(1 for s in shots if s.get("status") == "done")
    pct = int(base + (100 - base) * frac)

    def fn(doc: dict[str, Any]) -> None:
        doc["done"] = done

    await repo().mutate("runs", run_id, fn, missing_ok=True)
    if ctx is not None:
        await ctx.progress(min(99, pct), f"{done} / {len(shots)} 완료", done=done, total=len(shots))


async def set_phase(run_id: str, phase: str) -> None:
    await repo().patch("runs", run_id, {"phase": phase})


async def dev_delay() -> None:
    d = config.dev_shot_delay_s()
    if d > 0:
        await asyncio.sleep(d)


# ── T2I ──────────────────────────────────────────────────

def img_ref(file_id: str | None = None, *, data: bytes | None = None, mime: str = "image/png") -> dict[str, Any]:
    if data is not None:
        return {"data_b64": base64.b64encode(data).decode(), "mime": mime}
    return {"file_id": file_id}


async def t2i_generate(task: str, prompt: str, *, aspect: str, refs: list[dict[str, Any]] | None, negative: str | None,
                       confidential: bool, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    t0 = time.monotonic()

    async def run() -> dict[str, Any]:
        return await ai().generate_image(task, prompt, aspect=aspect, n=1, references=refs or None,
                                         negative_prompt=negative or None, confidential=confidential, metadata=metadata)

    res = await llm.call(run)
    if not res.get("images"):
        raise llm.ModelFailed("NO_IMAGE", "이미지 모델이 그림을 돌려주지 않았어요")
    g = res["images"][0]
    return {"file_id": g["file_id"], "width": int(g["width"]), "height": int(g["height"]), "model": res.get("model"),
            "provider": res.get("provider"), "fallbacks": list(res.get("fallbacks") or []), "warnings": list(res.get("warnings") or []),
            "seconds": time.monotonic() - t0, "call": "t2i.generate"}


async def t2i_edit(task: str, image: dict[str, Any] | str, prompt: str, *, mask: dict[str, Any] | None = None,
                   refs: list[dict[str, Any]] | None = None, aspect: str | None = None, confidential: bool,
                   metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    t0 = time.monotonic()

    async def run() -> dict[str, Any]:
        return await ai().edit_image(task, image, prompt, mask=mask, references=refs or None, aspect=aspect, n=1,
                                     confidential=confidential, metadata=metadata)

    res = await llm.call(run)
    if not res.get("images"):
        raise llm.ModelFailed("NO_IMAGE", "이미지 모델이 그림을 돌려주지 않았어요")
    g = res["images"][0]
    return {"file_id": g["file_id"], "width": int(g["width"]), "height": int(g["height"]), "model": res.get("model"),
            "provider": res.get("provider"), "fallbacks": list(res.get("fallbacks") or []), "warnings": list(res.get("warnings") or []),
            "seconds": time.monotonic() - t0, "call": "t2i.edit"}


FALLBACK_MAP = {"references_dropped": "reference:text_fallback", "mask_crop_paste": "mask:crop_paste",
                "outpaint_extend": "outpaint:extend", "edit_as_generate": "edit:as_generate", "aspect_cropped": "aspect:cropped"}


def map_fallbacks(fbs: list[str]) -> list[str]:
    return [FALLBACK_MAP.get(f, f) for f in fbs]


def model_error(exc: Exception) -> ShotFailed:
    if isinstance(exc, llm.ModelFailed):
        if 400 <= exc.status < 500 and exc.status not in (408, 429):
            return ShotFailed("provider_refused", exc.message or "이미지 모델이 요청을 거절했어요")
        return ShotFailed("model_error", "이미지 모델이 응답하지 않아요")
    return ShotFailed("model_error", "이미지 모델이 응답하지 않아요")


# ── 품질 확인 ───────────────────────────────────────────

QC_PROMPT = ("이 생성 이미지를 검사하라: 삼성 디스플레이 제품 개수와 각 제품 박스, 다른 회사 로고 · 상표 글자가 보이는지, "
             "식별 가능한 사람 얼굴 수, 깨진(알아볼 수 없는) 글자가 있는지.")


async def quality_check(file_id: str, *, width: int, height: int, products: list[dict[str, Any]], allow_faces: bool,
                        confidential: bool, want_bbox: bool, expect_boxes: list[list[float]] | None = None) -> dict[str, Any]:
    """→ {status: ok|check|skipped, checks, products:[{box, kind}], reason, fails{…}}"""
    try:
        res = await llm.vision_task("img.qc", [file_id], QC_PROMPT, llm.QcOut, want_bbox=want_bbox, confidential=confidential,
                                    timeout=60)
    except llm.ModelBlocked:
        res = None
    if res is None:
        return {"status": "skipped", "checks": [], "products": [], "reason": "품질 확인을 하지 못했어요(자동 검사 결과 없음)"}
    j = res["json"]
    prods = [p for p in j.get("products") or [] if p.get("box")]
    for b in res.get("boxes") or []:
        lab = str(b.get("label") or "").lower()
        if any(k in lab for k in ("display", "screen", "product", "signage", "디스플레이", "제품")) and not any(p.get("box") == b["box"] for p in prods):
            prods.append({"box": b["box"], "kind": "display"})
    checks = []
    fails: dict[str, bool] = {}
    want = sum(int(p.get("qty") or 1) for p in products) if products else None
    mock_matched = False
    if res.get("provider") == "mock" and (want is not None or expect_boxes):
        # mock 검출은 고정 응답(상자 3개)이라 렌더 API(조감도 · 시나리오)의 제품 수 · 배치와 늘 어긋났다(「제품 수 다름」 → 늘 check).
        # mock 에서는 요청한 수량 · 배치 상자를 그대로 맞은 것으로 본다(실제 모델 경로는 그대로) — image 요청 「렌더 mock QC」, 통합.
        if expect_boxes:
            prods = [{"box": list(b), "kind": "display"} for b in expect_boxes]
        if want is not None:
            j = {**j, "product_count": want}
        mock_matched = True
    if want is not None:
        got = int(j.get("product_count") or len(prods))
        ok = got == want
        checks.append({"key": "product_count", "ok": ok, "expected": want, "got": got})
        fails["count_fail"] = not ok
        if prods and width and height and not mock_matched:
            tol = config.product_aspect_tol()
            bad = 0
            for p in prods:
                b = p["box"]
                bw, bh = (b[2] - b[0]) * width, (b[3] - b[1]) * height
                if bw <= 0 or bh <= 0:
                    continue
                r = bw / bh
                target = 16 / 9 if r >= 1 else 9 / 16
                if abs(r - target) / target > tol:
                    bad += 1
            checks.append({"key": "product_aspect", "ok": bad == 0})
            fails["aspect_fail"] = bad > 0
    logo = bool(j.get("logo_visible")) or bool(j.get("brand_text"))
    checks.append({"key": "logo", "ok": not logo})
    faces = int(j.get("identifiable_faces") or 0)
    face_fail = faces > 0 and not allow_faces
    checks.append({"key": "faces", "ok": not face_fail, "count": faces})
    gib = bool(j.get("gibberish_text"))
    checks.append({"key": "text", "ok": not gib})
    if expect_boxes:
        from .imaging import boxes_iou

        iou = boxes_iou(expect_boxes, [p["box"] for p in prods])
        checks.append({"key": "layout_iou", "ok": iou >= 0.3, "value": round(iou, 3)})
    fails.update({"logo_visible": logo, "faces_fail": face_fail, "gibberish_text": gib})
    status = "ok" if all(c["ok"] for c in checks) else "check"
    reasons = []
    if fails.get("count_fail"):
        reasons.append("제품 수가 달라요")
    if fails.get("aspect_fail"):
        reasons.append("제품 비율이 달라요")
    if logo:
        reasons.append("로고 · 상표 글자가 보여요")
    if face_fail:
        reasons.append("식별 가능한 얼굴이 있어요")
    if gib:
        reasons.append("깨진 글자가 있어요")
    out = {"status": status, "checks": checks, "products": prods, "reason": " · ".join(reasons) or None, "fails": fails,
           "model": res.get("model")}
    if mock_matched:
        out["mock_matched"] = True
    return out


# ── 후처리 · 저장 ────────────────────────────────────────

def generation_meta(*, provider: str | None, model: str | None, call: str, prompt_ko: str, prompt_en: str,
                    references: list[dict[str, Any]], products: list[dict[str, Any]], policy_meta: dict[str, Any],
                    fallbacks: list[str], upscale: dict[str, Any] | None, confidential: bool, origin: dict[str, Any],
                    extra: dict[str, Any] | None = None) -> dict[str, Any]:
    g = {"is_generated": True, "rights": "generated", "caption_rule": "생성 이미지", "provider": provider, "model": model,
         "call": call, "prompt_ko": prompt_ko, "prompt_en": prompt_en, "seed": None, "references": references,
         "products": products, "policy": policy_meta, "fallbacks": list(dict.fromkeys(fallbacks)), "upscale": upscale,
         "confidential": confidential, "origin": origin, "created_at": now_iso()}
    if extra:
        g.update(extra)
    return g


async def to_master(native: Image.Image, aspect: str, fallbacks: list[str]) -> tuple[Image.Image, dict[str, Any]]:
    """비율 정규화(±2% 넘게 다르면 aspect_cropped) → fhd 마스터(Lanczos3 + 언샤프)."""
    ratio = config.ratio_of(aspect)
    dev = imaging.aspect_deviation(native, ratio)
    if dev > 0.02 and "aspect:cropped" not in fallbacks:
        fallbacks.append("aspect:cropped")
    norm = imaging.normalize_aspect(native, ratio)
    size = config.size_for(aspect, "fhd")
    master, method = await asyncio.to_thread(imaging.upscale, norm, size)
    up = {"from": [native.width, native.height], "to": [size[0], size[1]],
          "method": method if config.upscaler() == "none" else f"{config.upscaler()}+lanczos3"}
    if method == "none":
        up["method"] = "none"
    if config.upscaler() == "none" and method != "none":
        fallbacks.append("upscale:lanczos")
    return master, up


async def finish_shot(ctx: JobContext | None, run: dict[str, Any], img: dict[str, Any], *, native_file_id: str | None,
                      native_im: Image.Image, op: str, generation: dict[str, Any], qc: dict[str, Any], confidential: bool,
                      parent_version_id: str | None = None, op_params: dict[str, Any] | None = None, started: float | None = None,
                      ema: str | None = None, label: str | None = None, extra_img: dict[str, Any] | None = None) -> dict[str, Any]:
    """마스터 · 버전 1 저장 → 시안 done(QC 실패면 「확인 필요」) → partial 이벤트."""
    await check(ctx, img["id"], run["id"])
    fbs = list(generation.get("fallbacks") or [])
    master, up = await to_master(native_im, img.get("aspect") or "16:9", fbs)
    generation = {**generation, "fallbacks": list(dict.fromkeys(fbs)), "upscale": up}
    if qc.get("status") == "skipped" and "qc:skipped" not in generation["fallbacks"]:
        generation["fallbacks"].append("qc:skipped")
    native = {"w": native_im.width, "h": native_im.height, "file_id": native_file_id} if native_file_id else None
    # 저장 직전 다시 취소 확인(진행 시안 취소 = 결과 폐기)
    await check(ctx, img["id"], run["id"])
    ver = await create_version(img, op=op, master=master, generation=generation, parent_version_id=parent_version_id,
                               op_params=op_params, qc={k: v for k, v in qc.items() if k != "fails"}, native=native,
                               confidential=confidential)
    flag = qc.get("status") in ("check", "skipped")
    upd = {"status": "done", "stage_label": "완료", "progress": 1.0, "finished_at": now_iso(), "qc_flag": flag,
           "qc_reason": qc.get("reason") if flag else None, **(extra_img or {})}
    if label:
        upd["label"] = label

    def fn(doc: dict[str, Any]) -> None:
        if doc.get("status") == "canceled":
            return
        doc.update(upd)

    saved = await repo().mutate("images", img["id"], fn, missing_ok=True)
    if saved and saved.get("status") == "canceled":
        return ver
    if ema and started is not None:
        await update_ema(ema, time.monotonic() - started)
    if ctx is not None:
        await ctx.partial({"image_id": img["id"], "state": "done", "version_id": ver["id"],
                           "thumb_url": thumb_url(ver["master_file_id"], 640), "label": (saved or img).get("label")})
        await set_shot(ctx, img["id"], "done", stage="postprocess", label="완료")
    await run_progress(ctx, run["id"])
    return ver


async def load_native(file_id: str) -> Image.Image:
    return await load_image(file_id)


def shot_label_for(run_kind: str, img: dict[str, Any]) -> str:
    return img.get("label") or texts.shot_label(int(img.get("index") or 1))
