"""I2T(이미지 → 글 · JSON · 박스) — POST /v1/i2t/analyze.

- 이미지: file_id(files 서비스) · url · data_b64 → HEIC 는 JPEG 로, 긴 변 ≤ I2T_MAX_IMAGE_SIDE_PX, 장수 ≤ I2T_MAX_IMAGES_PER_CALL(넘으면 400)
- json_schema: 제공자 JSON 모드(I2T_SUPPORTS_JSON_SCHEMA) 또는 프롬프트 + 파싱, 검증 실패 시 2번까지 수리
- want_bbox: 결과 스키마를 {result, boxes[]} 로 감싸 박스를 함께 받고 [x0,y0,x1,y1](0..1)로 바꾼다.
  모델 좌표 규약은 I2T_BBOX_FORMAT(gemini_yxyx_1000 기본 · xyxy_1000 · xyxy_norm · xyxy_px).
  I2T_SUPPORTS_BBOX=false 면 boxes=[] + warnings.
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
from dataclasses import replace
from typing import Any

from . import config, imaging, jsonfix
from .errors import invalid, schema_mismatch
from .providers.base import I2TCall
from .runtime import track
from .schemas import I2TRequest

log = logging.getLogger("winmate.ai_tools.i2t")
MAX_REPAIRS = 2

_COORDS = {
    "gemini_yxyx_1000": "box_2d = [ymin, xmin, ymax, xmax] as integers normalized to 0-1000",
    "xyxy_1000": "box_2d = [xmin, ymin, xmax, ymax] as integers normalized to 0-1000",
    "xyxy_norm": "box_2d = [xmin, ymin, xmax, ymax] as fractions of the image size (0.0-1.0)",
    "xyxy_px": "box_2d = [xmin, ymin, xmax, ymax] in pixels of the given image",
}


def box_instruction(fmt: str, n_images: int) -> str:
    coords = _COORDS.get(fmt, _COORDS["gemini_yxyx_1000"])
    multi = " image_index is the 0-based index of the input image the box belongs to." if n_images > 1 else ""
    return (
        "\n\nPut your answer in `result`. Also detect the objects or regions relevant to the request and list them in "
        f"`boxes` with a short `label` each; {coords}.{multi}"
    )


def wrap_schema(user_schema: dict[str, Any] | None, *, lenient_boxes: bool = False) -> dict[str, Any]:
    """{result: <원래 스키마 | 문자열>, boxes: [{label, box_2d, image_index?, score?}]} — $defs 는 바깥으로 올린다.

    lenient_boxes: 검증용(박스 하나가 잘못돼도 수리하지 않고 그 박스만 버린다)."""
    wrapper: dict[str, Any] = {"type": "object", "required": ["result", "boxes"]}
    if user_schema is None:
        result: dict[str, Any] = {"type": "string", "description": "answer text"}
    else:
        result = copy.deepcopy(user_schema)
        for key in ("$defs", "definitions"):
            if key in result:
                wrapper[key] = result.pop(key)
        result.pop("$schema", None)
    if lenient_boxes:
        wrapper["properties"] = {"result": result, "boxes": {"type": "array"}}
        return wrapper
    wrapper["properties"] = {
        "result": result,
        "boxes": {"type": "array", "items": {"type": "object", "properties": {
            "label": {"type": "string"},
            "box_2d": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4},
            "image_index": {"type": "integer", "minimum": 0},
            "score": {"type": "number", "minimum": 0, "maximum": 1},
        }, "required": ["label", "box_2d"]}},
    }
    return wrapper


def convert_boxes(raw: Any, fmt: str, images: list[imaging.Img]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for b in raw if isinstance(raw, list) else []:
        if not isinstance(b, dict):
            continue
        c = b.get("box_2d") or b.get("box") or b.get("bbox")
        if not isinstance(c, list) or len(c) != 4:
            continue
        try:
            c = [float(x) for x in c]
        except (TypeError, ValueError):
            continue
        idx = b.get("image_index", 0)
        idx = int(idx) if isinstance(idx, (int, float)) and 0 <= int(idx) < len(images) else 0
        if fmt == "xyxy_1000":
            x0, y0, x1, y1 = (v / 1000 for v in c)
        elif fmt == "xyxy_norm":
            x0, y0, x1, y1 = c
        elif fmt == "xyxy_px":
            w, h = images[idx].width or 1, images[idx].height or 1
            x0, y0, x1, y1 = c[0] / w, c[1] / h, c[2] / w, c[3] / h
        else:  # gemini_yxyx_1000
            y0, x0, y1, x1 = (v / 1000 for v in c)
        x0, x1 = sorted((min(1.0, max(0.0, x0)), min(1.0, max(0.0, x1))))
        y0, y1 = sorted((min(1.0, max(0.0, y0)), min(1.0, max(0.0, y1))))
        if x1 - x0 <= 0 or y1 - y0 <= 0:
            continue
        score = b.get("score", b.get("confidence"))
        out.append({"label": str(b.get("label") or b.get("name") or ""), "box": [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)],
                    "score": float(score) if isinstance(score, (int, float)) else None, "image_index": idx})
    return out


async def load_images(refs: list[dict[str, Any]], max_side: int) -> list[imaging.Img]:
    async def one(ref: dict[str, Any]) -> imaging.Img:
        raw, _ = await imaging.load_raw(ref)
        return await asyncio.to_thread(imaging.prepare, raw, max_side)

    return list(await asyncio.gather(*(one(r) for r in refs)))


async def analyze(req: I2TRequest) -> dict[str, Any]:
    cfg = config.load("i2t")
    async with track("i2t", req.task, request=req.model_dump(exclude_none=True), confidential=req.confidential, cfg=cfg) as call:
        call.check_policy()
        if len(req.images) > cfg.max_images_per_call:
            raise invalid(f"이미지는 한 번에 {cfg.max_images_per_call}장까지 보낼 수 있습니다({len(req.images)}장)",
                          code="TOO_MANY_IMAGES", max=cfg.max_images_per_call, given=len(req.images))
        images = await load_images([i.model_dump(exclude_none=True) for i in req.images], cfg.max_image_side_px)
        kp = {"prompt": req.prompt, "json_schema": req.json_schema, "want_bbox": req.want_bbox,
              "max_tokens": req.max_tokens, "images": [i.sha256 for i in images]}
        hit = await call.replay(kp)
        if hit is not None:
            return call.done(dict(hit["response"]))
        await call.acquire()
        provider = call.provider()

        warnings: list[str] = []
        bbox = req.want_bbox and cfg.supports_bbox
        if req.want_bbox and not cfg.supports_bbox:
            warnings.append("bbox_unsupported: I2T_SUPPORTS_BBOX=false 라 박스 없이 답합니다")
        schema = wrap_schema(req.json_schema) if bbox else req.json_schema
        check = wrap_schema(req.json_schema, lenient_boxes=True) if bbox else req.json_schema
        prompt = req.prompt + (box_instruction(cfg.bbox_format, len(images)) if bbox else "")
        want_json = schema is not None
        native = want_json and cfg.supports_json_schema
        max_tokens = min(req.max_tokens, cfg.max_output_tokens) if req.max_tokens else cfg.max_output_tokens
        i2t_call = I2TCall(task=req.task, images=images, prompt=prompt,
                           system=jsonfix.schema_instruction(schema or {}) if want_json and not native else None,
                           temperature=cfg.temperature, max_tokens=max_tokens, json_schema=schema if native else None,
                           want_json=want_json, user_schema=req.json_schema, want_bbox=bbox, user_prompt=req.prompt)
        call.set_fallback("json_parse" if want_json and not native else "none")
        res = await call.invoke(provider.analyze, cfg, i2t_call)
        call.add_usage(res.usage)
        call.model = res.model or cfg.model

        content, json_value, boxes = res.text, None, []
        if res.boxes is not None or (res.authoritative and not want_json):
            # mock: 이미 나뉜 결과
            boxes = res.boxes or []
            if req.json_schema is not None:
                value, errors = jsonfix.parse_and_validate(res.text, req.json_schema, pre=res.json_value)
                if errors:
                    log.warning("mock 고정 응답이 스키마와 맞지 않습니다(%s): %s", req.task, errors[:3])
                json_value = value
        elif want_json:
            value, errors = jsonfix.parse_and_validate(res.text, check or {}, pre=res.json_value)
            repairs = 0
            cur = i2t_call
            while errors and not res.authoritative and repairs < MAX_REPAIRS:
                repairs += 1
                call.set_fallback("json_repair")
                cur = replace(cur, turns=[*cur.turns, ("assistant", res.text or "(빈 응답)"), ("user", jsonfix.repair_message(errors))])
                res = await call.invoke(provider.analyze, cfg, cur)
                call.add_usage(res.usage)
                value, errors = jsonfix.parse_and_validate(res.text, check or {}, pre=res.json_value)
            if errors and not (res.authoritative and value is not None):
                raise schema_mismatch(errors, res.text, attempts=repairs + 1, finish_reason=res.finish_reason)
            content = res.text
            if bbox and isinstance(value, dict):
                result = value.get("result")
                boxes = convert_boxes(value.get("boxes"), cfg.bbox_format, images)
                if req.json_schema is not None:
                    json_value = result
                    content = json.dumps(result, ensure_ascii=False)
                else:
                    content = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
            else:
                json_value = value
        out = {"provider": call.provider_name, "model": call.model, "content": content, "json": json_value,
               "boxes": boxes, "usage": dict(call.usage), "warnings": warnings, "fallback": call.fallback or "none"}
        call.record(kp, out)
        return call.done(out)
