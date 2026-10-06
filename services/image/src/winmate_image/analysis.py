"""참조 이미지 분석(§7.2 · §7.3 policy_check (2)(3)) — i2t JSON(+박스): 얼굴 · 로고 · 디스플레이 · 스타일 · 캡션 · 요소별 묘사,
로컬 팔레트(k-means 5색), 얼굴 · 로고 흐림 사본(bbox 지원 시) / 글 대체(bbox 미지원), 인식 못 한 디스플레이의 KB 후보(C2 상위 3).

업로드 참조는 기밀(confidential=true) — ai-tools 가 막으면 로컬 분석(팔레트)만 하고 글 대체로 보낸다.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from . import caps, config, imaging, kbapi, llm
from .filestore import load_image, save_image
from .store import repo

log = logging.getLogger("winmate.image.analysis")

PROMPT = ("이 참조 이미지를 분석하라: 사람 얼굴 박스(faces), 다른 회사 로고 박스(logos), 디스플레이 · 사이니지(displays: 박스 · 형태 분류 · 크기 힌트 · "
          "모델 추정과 신뢰도 0..1), 스타일(photo|illustration), 한 문장 캡션, 그리고 색감 · 조명(color_light) · 구도(composition) · "
          "제품 배치(placement) · 소재(material)를 각각 한 줄로 묘사하라.")


async def display_candidates(d: dict[str, Any]) -> list[dict[str, Any]]:
    """i2t 가 본 형태(분류 · 크기 힌트) → KB C2 상위 3 → 표시명."""
    text = " ".join(x for x in [d.get("visual_category"), d.get("size_hint"), d.get("model_guess")] if x)
    fams = await kbapi.c2(category="cat_smart-signage" if "사이니지" in text or "signage" in text.lower() or not text else None,
                          text=text or "사이니지 디스플레이", limit=5)
    out: list[dict[str, Any]] = []
    for f in fams:
        code = f.get("model")
        hit = await kbapi.resolve_product(code) if code else None
        if hit is None:
            continue
        p = kbapi.product_from_search(hit, 1)
        if any(x.get("model_code") == p.get("model_code") for x in out):
            continue
        out.append({**p, "score": float(f.get("score") or 0)})
        if len(out) >= 3:
            break
    guess = d.get("model_guess")
    if guess:
        hit = await kbapi.resolve_product(guess)
        if hit is not None:
            p = kbapi.product_from_search(hit, 1)
            out = [x for x in out if x.get("model_code") != p.get("model_code")]
            out.insert(0, {**p, "score": max(float(d.get("confidence") or 0), out[0]["score"] if out else 0.0)})
    return out[:3]


async def analyze_reference(ref_id: str) -> dict[str, Any] | None:
    ref = await repo().get("refs", ref_id)
    if ref is None or not ref.get("file_id"):
        return ref
    flags = await caps.flags()
    try:
        im = await load_image(ref["file_id"])
    except Exception as exc:  # noqa: BLE001
        log.warning("참조 이미지를 읽지 못했습니다 %s: %s", ref_id, exc)
        return ref
    pal = await asyncio.to_thread(imaging.palette, im, 5)
    analysis: dict[str, Any] = {"faces": [], "logos": [], "displays": [], "style": ref.get("visual_style") or "photo",
                                "palette": pal, "caption": ref.get("label"), "elements": {}, "candidates": [], "local": False}
    blocked = False
    res = None
    try:
        res = await llm.vision_task("img.ref_analyze", [ref["file_id"]], PROMPT, llm.RefAnalyzeOut, want_bbox=flags.bbox,
                                    confidential=bool(ref.get("confidential")), timeout=60)
    except llm.ModelBlocked:
        blocked = True
    if res is not None:
        j = res["json"]
        faces = [b for b in j.get("faces") or [] if len(b) == 4]
        logos = [b for b in j.get("logos") or [] if len(b) == 4]
        for b in res.get("boxes") or []:
            lab = str(b.get("label") or "").lower()
            if ("face" in lab or "얼굴" in lab) and b["box"] not in faces:
                faces.append(b["box"])
            elif ("logo" in lab or "로고" in lab) and b["box"] not in logos:
                logos.append(b["box"])
        analysis.update({"faces": faces, "logos": logos, "displays": j.get("displays") or [], "style": j.get("style") or analysis["style"],
                         "caption": j.get("caption") or analysis["caption"],
                         "elements": {k: j.get(k) for k in ("color_light", "composition", "placement", "material") if j.get(k)}})
    else:
        analysis["local"] = True
    # 인식 못 한 디스플레이(업로드 · 상단 이미지 검색 사진만 — 사내 자산은 이미 출처가 확인됨)
    if ref.get("origin_kind") in ("upload",) or ref.get("via") == "topbar":
        low = [d for d in analysis["displays"] if float(d.get("confidence") or 0) < config.product_match_min()]
        if low:
            analysis["candidates"] = await display_candidates(low[0])
    # 보낼 방법: 얼굴 · 로고가 있으면 bbox 로 흐린 사본, bbox 가 없으면 글 대체. 기밀 차단이면 글 대체.
    send_mode = "image"
    sanitized = None
    if blocked:
        send_mode = "text_fallback"
    elif analysis["faces"] or analysis["logos"]:
        if flags.bbox:
            blurred = await asyncio.to_thread(imaging.blur_boxes, im, analysis["faces"] + analysis["logos"], 0.03)
            fm = await save_image(blurred, f"{ref_id}_sanitized.png", parent_id=ref["file_id"], source="derived",
                                  meta={"ref_id": ref_id, "sanitized": True}, purpose="img.reference")
            sanitized = fm["id"]
        else:
            send_mode = "text_fallback"
    return await repo().patch("refs", ref_id, {"analysis": analysis, "send_mode": send_mode, "sanitized_file_id": sanitized,
                                               "visual_style": analysis["style"]})
