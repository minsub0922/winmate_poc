"""로컬 이미지 연산(Pillow · numpy) — 모델 호출 없이 결정적으로 돈다.

- 해상도 사다리 · 업스케일(Lanczos3 + 약한 언샤프) · 비율 정규화 · 잘라내기 창 · 바깥 채우기 캔버스
- 부분 수정 합성: 안쪽 페더 · 이음매 보정 · 바깥 픽셀 검증 · 제품 테두리 보호 · 로컬 인페인트
- 밝기 보정(§7.6) · 참조 얼굴/로고 흐림 · 팔레트(k-means 5색)
- 현장 사진: 휘도 · 선명도 · 원근 워프 · 디스플레이 대역 그림 · 메뉴 템플릿 · 로컬 조화(색 전달 + 접촉 그림자 + 화면 반사)
- 메타데이터(PNG iTXt + XMP) · 「AI 생성 이미지」 표기
"""
from __future__ import annotations

import io
import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps, PngImagePlugin

Box = Sequence[float]  # [x0, y0, x1, y1] 0..1

TRAINED_MEDIA = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"

_FONTS = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in _FONTS:
        if Path(p).is_file():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # pragma: no cover
        return ImageFont.load_default()


# ── 읽기 · 쓰기 ──────────────────────────────────────────

def open_rgb(data: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(data))
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        return bg
    return im.convert("RGB")


def open_rgba(data: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(data))
    im = ImageOps.exif_transpose(im)
    return im.convert("RGBA")


def xmp_packet(*, version_id: str | None, model: str | None, sources: list[str] | None, dc_source: str | None,
               generated: bool = True) -> str:
    src = escape(dc_source or "")
    lines = [
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>',
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">',
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">',
        '<rdf:Description rdf:about="" xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:winmate="https://winmate.local/ns/1.0/">',
    ]
    if generated:
        lines.append(f"<Iptc4xmpExt:DigitalSourceType>{TRAINED_MEDIA}</Iptc4xmpExt:DigitalSourceType>")
    if src:
        lines.append(f"<dc:source>{src}</dc:source>")
    if version_id:
        lines.append(f"<winmate:version_id>{escape(version_id)}</winmate:version_id>")
    if model:
        lines.append(f"<winmate:model>{escape(model)}</winmate:model>")
    if sources:
        lines.append(f"<winmate:sources>{escape(json.dumps(sources, ensure_ascii=False))}</winmate:sources>")
    lines += ["</rdf:Description>", "</rdf:RDF>", "</x:xmpmeta>", '<?xpacket end="w"?>']
    return "".join(lines)


def encode(im: Image.Image, fmt: str = "PNG", *, meta: dict[str, Any] | None = None, quality: int = 90) -> tuple[bytes, str]:
    """PNG(iTXt winmate:* + XMP) 또는 JPEG(XMP). meta = {generated, version_id, model, sources, dc_source}."""
    buf = io.BytesIO()
    fmt = fmt.upper()
    xmp = None
    if meta is not None:
        xmp = xmp_packet(version_id=meta.get("version_id"), model=meta.get("model"), sources=meta.get("sources"),
                         dc_source=meta.get("dc_source"), generated=bool(meta.get("generated", True)))
    if fmt in ("JPG", "JPEG"):
        rgb = im.convert("RGB")
        kw: dict[str, Any] = {"quality": quality, "optimize": True}
        if xmp:
            kw["xmp"] = xmp.encode("utf-8")
        rgb.save(buf, "JPEG", **kw)
        return buf.getvalue(), "image/jpeg"
    info = PngImagePlugin.PngInfo()
    if meta is not None:
        info.add_itxt("winmate:generated", "true" if meta.get("generated", True) else "false")
        if meta.get("version_id"):
            info.add_itxt("winmate:version_id", str(meta["version_id"]))
        if meta.get("model"):
            info.add_itxt("winmate:model", str(meta["model"]))
        info.add_itxt("winmate:sources", json.dumps(meta.get("sources") or [], ensure_ascii=False))
        if xmp:
            info.add_itxt("XML:com.adobe.xmp", xmp)
    im.save(buf, "PNG", pnginfo=info, compress_level=6)
    return buf.getvalue(), "image/png"


def read_png_text(data: bytes) -> dict[str, str]:
    im = Image.open(io.BytesIO(data))
    im.load()
    return {k: str(v) for k, v in getattr(im, "text", {}).items()}


# ── 크기 · 비율 ──────────────────────────────────────────

def upscale(im: Image.Image, size: tuple[int, int]) -> tuple[Image.Image, str]:
    """Lanczos3 + 약한 언샤프(업스케일 모델 없음). 같거나 작으면 Lanczos 만."""
    if im.size == size:
        return im.copy(), "none"
    out = im.resize(size, Image.Resampling.LANCZOS)
    if size[0] > im.width * 1.05:
        out = out.filter(ImageFilter.UnsharpMask(radius=1.2, percent=40, threshold=2))
        return out, "lanczos3+unsharp"
    return out, "lanczos3"


def center_crop_ratio(im: Image.Image, ratio: float) -> Image.Image:
    w, h = im.size
    if abs(w / h - ratio) < 1e-3:
        return im
    if w / h > ratio:
        nw = int(round(h * ratio))
        x0 = (w - nw) // 2
        return im.crop((x0, 0, x0 + nw, h))
    nh = int(round(w / ratio))
    y0 = (h - nh) // 2
    return im.crop((0, y0, w, y0 + nh))


def aspect_deviation(im: Image.Image, ratio: float) -> float:
    return abs((im.width / im.height) - ratio) / ratio


def normalize_aspect(im: Image.Image, ratio: float) -> Image.Image:
    """비율 정규화 — 가운데를 잘라 정확히 맞춘다(±2% 넘게 다르면 호출한 쪽이 aspect_cropped 경고를 남긴다)."""
    if aspect_deviation(im, ratio) < 1e-3:
        return im
    return center_crop_ratio(im, ratio)


def crop_window(w: int, h: int, ratio: float, boxes: Sequence[Box]) -> tuple[int, int, int, int]:
    """목표 비율의 가장 큰 창 — 제품 박스를 최대한 담도록 가운데를 옮긴다(px)."""
    if w / h > ratio:
        cw, ch = int(round(h * ratio)), h
    else:
        cw, ch = w, int(round(w / ratio))
    if boxes:
        x0 = min(b[0] for b in boxes) * w
        x1 = max(b[2] for b in boxes) * w
        y0 = min(b[1] for b in boxes) * h
        y1 = max(b[3] for b in boxes) * h
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    else:
        cx, cy = w / 2, h / 2
    left = int(round(min(max(cx - cw / 2, 0), w - cw)))
    top = int(round(min(max(cy - ch / 2, 0), h - ch)))
    return left, top, left + cw, top + ch


def extend_canvas(im: Image.Image, ratio: float, size: tuple[int, int]) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """바깥 채우기 캔버스: 목표 비율 · 크기(size) 캔버스 가운데에 원본을 줄여 놓고, 빈 곳은 가장자리 거울 반사 + 블러 힌트.

    돌려주는 box = 캔버스 안 원본 영역(px)."""
    cw, ch = size
    r0 = im.width / im.height
    if r0 >= ratio:      # 원본이 더 넓다 → 위아래를 채운다
        iw, ih = cw, max(1, int(round(cw / r0)))
    else:                # 원본이 더 좁다 → 양옆을 채운다
        iw, ih = max(1, int(round(ch * r0))), ch
    small = im.resize((iw, ih), Image.Resampling.LANCZOS)
    x0, y0 = (cw - iw) // 2, (ch - ih) // 2
    arr = np.asarray(small)
    pad_y = (y0, ch - ih - y0)
    pad_x = (x0, cw - iw - x0)
    mode = "symmetric"
    padded = np.pad(arr, (pad_y, pad_x, (0, 0)), mode=mode) if (ih > 1 and iw > 1) else np.pad(arr, (pad_y, pad_x, (0, 0)), mode="edge")
    canvas = Image.fromarray(padded[:ch, :cw].astype(np.uint8))
    blurred = canvas.filter(ImageFilter.GaussianBlur(radius=max(4, min(cw, ch) // 40)))
    mask = Image.new("L", (cw, ch), 255)
    mask.paste(0, (x0, y0, x0 + iw, y0 + ih))
    canvas = Image.composite(blurred, canvas, mask)
    canvas.paste(small, (x0, y0))
    return canvas, (x0, y0, x0 + iw, y0 + ih)


def outpaint_side_label(base_aspect: str, target_aspect: str) -> str:
    """「{위쪽|아래쪽|양옆|위아래}은 새로 채움」의 방향 — 넓은 → 좁은(세로) 비율이면 위아래, 반대면 양옆."""
    from .config import ratio_of

    rb, rt = ratio_of(base_aspect), ratio_of(target_aspect)
    if abs(rb - rt) < 1e-3:
        return ""
    return "위아래" if rt < rb else "양옆"


# ── 마스크 · 합성 ────────────────────────────────────────

def rect_mask(size: tuple[int, int], rect: Box) -> Image.Image:
    w, h = size
    m = Image.new("L", size, 0)
    x0, y0, x1, y1 = (int(round(rect[0] * w)), int(round(rect[1] * h)), int(round(rect[2] * w)), int(round(rect[3] * h)))
    if x1 > x0 and y1 > y0:
        ImageDraw.Draw(m).rectangle([x0, y0, x1 - 1, y1 - 1], fill=255)
    return m


def mask_from_image(mask: Image.Image, size: tuple[int, int]) -> Image.Image:
    """흰색(≥128) = 수정. 알파가 있으면 불투명(알파 > 0) 픽셀 중 흰색만."""
    if mask.mode == "RGBA":
        a = mask.split()[-1]
        g = mask.convert("L")
        m = ImageChops.multiply(g.point(lambda v: 255 if v >= 128 else 0), a.point(lambda v: 255 if v > 0 else 0))
    else:
        m = mask.convert("L").point(lambda v: 255 if v >= 128 else 0)
    if m.size != size:
        m = m.resize(size, Image.Resampling.NEAREST)
    return m


def dilate(mask: Image.Image, px: int) -> Image.Image:
    out = mask
    left = px
    while left > 0:
        k = min(left, 3)
        out = out.filter(ImageFilter.MaxFilter(2 * k + 1))
        left -= k
    return out


def erode(mask: Image.Image, px: int) -> Image.Image:
    out = mask
    left = px
    while left > 0:
        k = min(left, 3)
        out = out.filter(ImageFilter.MinFilter(2 * k + 1))
        left -= k
    return out


def inward_alpha(mask: Image.Image, radius: int) -> np.ndarray:
    """마스크 안쪽으로만 번지는 페더 알파(0..1). 마스크 밖은 정확히 0."""
    m = np.asarray(mask.convert("L")) >= 128
    if radius <= 0:
        return m.astype(np.float32)
    acc = np.zeros(m.shape, np.float32)
    cur = mask.convert("L").point(lambda v: 255 if v >= 128 else 0)
    for _ in range(radius):
        acc += (np.asarray(cur) >= 128).astype(np.float32)
        cur = cur.filter(ImageFilter.MinFilter(3))
    alpha = acc / float(radius)
    # 부드럽게(안쪽만) — 블러 뒤 다시 마스크로 자른다
    a_img = Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius / 3))
    alpha = np.asarray(a_img).astype(np.float32) / 255.0
    alpha = np.where(m, np.clip(alpha, 0, 1), 0.0)
    return alpha.astype(np.float32)


def composite_inward(base: Image.Image, edited: Image.Image, mask: Image.Image, radius: int) -> Image.Image:
    """edited 를 base 위에 mask 안쪽만 페더로 붙인다(마스크 밖 픽셀은 base 와 바이트 단위로 같다)."""
    if edited.size != base.size:
        edited = edited.resize(base.size, Image.Resampling.LANCZOS)
    a = inward_alpha(mask, radius)[..., None]
    b = np.asarray(base.convert("RGB")).astype(np.float32)
    e = np.asarray(edited.convert("RGB")).astype(np.float32)
    out = b + a * (e - b)
    res = np.where(a > 0, np.clip(np.rint(out), 0, 255), b).astype(np.uint8)
    return Image.fromarray(res)


def seam_harmonize(base: Image.Image, result: Image.Image, mask: Image.Image, ring: int) -> Image.Image:
    """마스크 바깥 ring px 링과 안쪽 ring px 링의 평균 · 표준편차를 맞춘다(안쪽만 바꿈, 가장자리일수록 강하게)."""
    m = mask.convert("L").point(lambda v: 255 if v >= 128 else 0)
    outer = np.asarray(ImageChops.subtract(dilate(m, ring), m)) >= 128
    inner_core = erode(m, ring)
    inner = np.asarray(ImageChops.subtract(m, inner_core)) >= 128
    mm = np.asarray(m) >= 128
    if outer.sum() < 16 or inner.sum() < 16:
        return result
    r = np.asarray(result.convert("RGB")).astype(np.float32)
    out = r.copy()
    # 가장자리 가중치: 안쪽 링에서 1 → 0
    w = inward_alpha(m, ring)
    weight = np.where(mm, 1.0 - w, 0.0)[..., None]
    for c in range(3):
        o = r[..., c][outer]
        i = r[..., c][inner]
        mo, so = float(o.mean()), float(o.std()) + 1e-3
        mi, si = float(i.mean()), float(i.std()) + 1e-3
        scale = min(max(so / si, 0.5), 2.0)
        adj = (r[..., c] - mi) * scale + mo
        out[..., c] = r[..., c] + weight[..., 0] * (adj - r[..., c])
    res = np.where(mm[..., None], np.clip(np.rint(out), 0, 255), r).astype(np.uint8)
    return Image.fromarray(res)


def verify_outside(base: Image.Image, result: Image.Image, mask: Image.Image, pad: int) -> bool:
    """(마스크 ⊕ pad) 바깥 픽셀이 바이트 단위로 같은가."""
    grown = np.asarray(dilate(mask.convert("L").point(lambda v: 255 if v >= 128 else 0), pad)) >= 128
    a = np.asarray(base.convert("RGB"))
    b = np.asarray(result.convert("RGB"))
    if a.shape != b.shape:
        return False
    diff = np.any(a != b, axis=2)
    return not bool(np.any(diff & ~grown))


def protect_products(mask: Image.Image, products: Sequence[dict[str, Any]], *, screen_target: bool) -> Image.Image:
    """제품 외형 고정: 디스플레이는 「바깥 박스 − 3% 안쪽 박스」 테두리 띠를, 그 밖의 제품은 박스 전체를 마스크에서 뺀다.

    screen_target=True(지시가 화면 콘텐츠를 겨냥)면 디스플레이의 화면 박스만 허용한다."""
    w, h = mask.size
    out = mask.convert("L").copy()
    draw = ImageDraw.Draw(out)
    allow = Image.new("L", mask.size, 0)
    adraw = ImageDraw.Draw(allow)
    for p in products:
        box = p.get("bbox") or p.get("box")
        if not box:
            continue
        x0, y0, x1, y1 = box[0] * w, box[1] * h, box[2] * w, box[3] * h
        kind = (p.get("kind") or "display").lower()
        if kind in ("display", "screen", "signage", "tv", "monitor", "kiosk", "led"):
            ix = (x1 - x0) * 0.03
            iy = (y1 - y0) * 0.03
            inner = (x0 + ix, y0 + iy, x1 - ix, y1 - iy)
            # 테두리 띠 = 바깥 - 안쪽
            band = Image.new("L", mask.size, 0)
            bd = ImageDraw.Draw(band)
            bd.rectangle([x0, y0, x1, y1], fill=255)
            bd.rectangle([inner[0], inner[1], inner[2], inner[3]], fill=0)
            out = ImageChops.subtract(out, band)
            draw = ImageDraw.Draw(out)
            if screen_target:
                adraw.rectangle([inner[0], inner[1], inner[2], inner[3]], fill=255)
        else:
            draw.rectangle([x0, y0, x1, y1], fill=0)
    if screen_target and allow.getbbox() is not None:
        out = ImageChops.multiply(out, allow)
    return out.point(lambda v: 255 if v >= 128 else 0)


def mask_area_ratio(mask: Image.Image) -> float:
    a = np.asarray(mask.convert("L")) >= 128
    return float(a.mean()) if a.size else 0.0


def diffusion_inpaint(im: Image.Image, mask: Image.Image, iterations: int = 0) -> Image.Image:
    """작은 영역(글자 · 사람 지우기) 로컬 인페인트 — 마스크 안을 바깥 픽셀로 확산해 채운다(OpenCV 없이)."""
    m = np.asarray(mask.convert("L")) >= 128
    if not m.any():
        return im.copy()
    arr = np.asarray(im.convert("RGB")).astype(np.float32)
    known = ~m
    out = arr.copy()
    ys, xs = np.where(m)
    span = max(int(ys.max() - ys.min()), int(xs.max() - xs.min()), 4)
    iters = iterations or min(400, span * 2)
    filled = known.copy()
    acc = out * filled[..., None]
    for _ in range(iters):
        # 4-이웃 평균으로 미지 영역을 채운다
        s = np.zeros_like(out)
        c = np.zeros(m.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh = np.roll(np.roll(acc, dy, 0), dx, 1)
            fh = np.roll(np.roll(filled, dy, 0), dx, 1).astype(np.float32)
            s += sh
            c += fh
        newv = s / np.maximum(c, 1e-6)[..., None]
        upd = m & (c > 0)
        out[upd] = newv[upd]
        filled = filled | upd
        acc = out * filled[..., None]
    res = np.where(m[..., None], np.clip(np.rint(out), 0, 255), arr).astype(np.uint8)
    return Image.fromarray(res)


# ── 보정 ─────────────────────────────────────────────────

def luma(im: Image.Image) -> np.ndarray:
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def brighten(im: Image.Image, *, gamma: float = 0.9, exposure: float = 0.08) -> Image.Image:
    """감마 0.9 + 노출 +8%(하이라이트 보호: 상위 1% 휘도는 압축)."""
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255.0
    y = luma(im)
    p99 = float(np.quantile(y, 0.99)) if y.size else 1.0
    out = np.power(np.clip(a, 0, 1), gamma) * (1.0 + exposure)
    # 하이라이트 보호: p99 위는 부드럽게 눌러 1 을 넘지 않게
    knee = max(0.6, min(p99, 0.95))
    over = out > knee
    out = np.where(over, knee + (1 - knee) * (1 - np.exp(-(out - knee) / max(1e-3, (1 - knee)))), out)
    return Image.fromarray(np.clip(np.rint(out * 255), 0, 255).astype(np.uint8))


def adjust_brightness(im: Image.Image, amount: float) -> Image.Image:
    """-0.3..0.3 노출 조정(양수 = 밝게)."""
    if amount >= 0:
        return brighten(im, gamma=1.0 - amount * 0.5, exposure=amount)
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    return Image.fromarray(np.clip(np.rint(a * (1 + amount)), 0, 255).astype(np.uint8))


def harmonize_region(base: Image.Image, mask: Image.Image, ring: int) -> Image.Image:
    """「주변과 밝기 맞추기」 — seam_harmonize 와 같은 계산을 선택 영역 결과에만."""
    return seam_harmonize(base, base, mask, ring)


def quality(im: Image.Image) -> dict[str, float]:
    """휘도 평균 · 라플라시안 분산(선명도) · 포화 비율."""
    small = im.copy()
    small.thumbnail((640, 640))
    y = luma(small)
    lap = np.abs(
        -4 * y[1:-1, 1:-1] + y[:-2, 1:-1] + y[2:, 1:-1] + y[1:-1, :-2] + y[1:-1, 2:]
    ) if y.shape[0] > 2 and y.shape[1] > 2 else np.zeros((1, 1))
    clipped = float(((y <= 0.02) | (y >= 0.98)).mean()) if y.size else 0.0
    return {"luma_mean": round(float(y.mean()), 4), "laplacian_var": round(float(lap.var() * 1000), 4),
            "clipped_ratio": round(clipped, 4)}


def blur_boxes(im: Image.Image, boxes: Sequence[Box], sigma_ratio: float = 0.03) -> Image.Image:
    """참조 속 얼굴 · 로고 영역 가우시안 블러(σ = 짧은 변의 3%)."""
    out = im.copy()
    w, h = im.size
    sigma = max(2.0, min(w, h) * sigma_ratio)
    for b in boxes:
        x0, y0, x1, y1 = (max(0, int(b[0] * w)), max(0, int(b[1] * h)), min(w, int(math.ceil(b[2] * w))), min(h, int(math.ceil(b[3] * h))))
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        pad = int(sigma * 2)
        ex = (max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad))
        region = out.crop(ex).filter(ImageFilter.GaussianBlur(sigma))
        region = region.filter(ImageFilter.GaussianBlur(sigma))
        out.paste(region.crop((x0 - ex[0], y0 - ex[1], x1 - ex[0], y1 - ex[1])), (x0, y0))
    return out


def region_variance(im: Image.Image, box: Box) -> float:
    w, h = im.size
    x0, y0, x1, y1 = int(box[0] * w), int(box[1] * h), max(int(box[0] * w) + 1, int(box[2] * w)), max(int(box[1] * h) + 1, int(box[3] * h))
    a = np.asarray(im.convert("L").crop((x0, y0, x1, y1))).astype(np.float32)
    return float(a.var()) if a.size else 0.0


def palette(im: Image.Image, k: int = 5) -> list[str]:
    """k-means 5색 hex(결정적 초기값)."""
    small = im.convert("RGB").copy()
    small.thumbnail((96, 96))
    px = np.asarray(small).reshape(-1, 3).astype(np.float32)
    if len(px) == 0:
        return []
    order = np.argsort(px.sum(axis=1))
    init_idx = [order[int(i * (len(order) - 1) / max(1, k - 1))] for i in range(k)]
    cent = px[init_idx].copy()
    for _ in range(12):
        d = ((px[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2)
        lab = d.argmin(axis=1)
        for j in range(k):
            sel = px[lab == j]
            if len(sel):
                cent[j] = sel.mean(axis=0)
    counts = np.bincount(lab, minlength=k)
    ranked = [cent[j] for j in np.argsort(-counts)]
    return ["#%02x%02x%02x" % tuple(int(round(v)) for v in c) for c in ranked]


# ── 박스 ─────────────────────────────────────────────────

def iou(a: Box, b: Box) -> float:
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def boxes_iou(expected: Sequence[Box], got: Sequence[Box]) -> float:
    """기대 박스마다 가장 잘 맞는 박스의 IoU 평균(기대가 없으면 1)."""
    if not expected:
        return 1.0
    if not got:
        return 0.0
    return float(np.mean([max(iou(e, g) for g in got) for e in expected]))


def edge_map(im: Image.Image, box: tuple[int, int, int, int]) -> np.ndarray:
    crop = im.convert("L").crop(box).filter(ImageFilter.FIND_EDGES)
    a = np.asarray(crop)
    thr = max(24, float(np.quantile(a, 0.85))) if a.size else 24
    return a >= thr


def edge_iou(a: Image.Image, b: Image.Image, box: tuple[int, int, int, int]) -> float:
    """제품 쿼드 영역의 가장자리 IoU(1px 여유)."""
    ea = edge_map(a, box)
    eb = edge_map(b.resize(a.size) if b.size != a.size else b, box)
    if not ea.any() and not eb.any():
        return 1.0
    ga = np.asarray(Image.fromarray(ea.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3))) >= 128
    gb = np.asarray(Image.fromarray(eb.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3))) >= 128
    inter = float((ga & gb).sum())
    union = float((ga | gb).sum())
    return inter / union if union else 1.0


# ── 원근 · 합성 ──────────────────────────────────────────

def perspective_coeffs(dst: Sequence[Sequence[float]], src: Sequence[Sequence[float]]) -> list[float]:
    """Image.transform(PERSPECTIVE) 계수: 출력 좌표(dst) → 입력 좌표(src)."""
    matrix = []
    for (x, y), (u, v) in zip(dst, src):
        matrix.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        matrix.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    a = np.array(matrix, dtype=np.float64)
    b = np.array([c for p in src for c in p], dtype=np.float64)
    res = np.linalg.solve(a, b)
    return [float(v) for v in res]


def warp_into(canvas: Image.Image, src: Image.Image, quad_px: Sequence[Sequence[float]]) -> tuple[Image.Image, Image.Image]:
    """src(RGBA 가능)를 canvas 의 쿼드(px, 왼쪽 위부터 시계 방향)에 원근으로 붙인다 → (결과, 붙인 영역 마스크)."""
    w, h = canvas.size
    sw, sh = src.size
    coeffs = perspective_coeffs(quad_px, [(0, 0), (sw, 0), (sw, sh), (0, sh)])
    rgba = src.convert("RGBA")
    warped = rgba.transform((w, h), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC)
    mask = warped.split()[-1]
    out = canvas.convert("RGB").copy()
    out.paste(warped.convert("RGB"), (0, 0), mask)
    return out, mask


def quad_px(quad: Sequence[Sequence[float]], size: tuple[int, int]) -> list[tuple[float, float]]:
    w, h = size
    return [(float(p[0]) * w, float(p[1]) * h) for p in quad]


def quad_bbox(quad: Sequence[Sequence[float]]) -> list[float]:
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    return [min(xs), min(ys), max(xs), max(ys)]


def split_quad(quad: Sequence[Sequence[float]], n: int, *, vertical: bool, gap_ratio: float = 0.0) -> list[list[list[float]]]:
    """그룹 쿼드를 n 칸으로 나눈다(가로 3연 · 세로 3연). gap_ratio = 칸 사이 간격(전체 대비)."""
    if n <= 1:
        return [[list(p) for p in quad]]
    tl, tr, br, bl = [np.array(p, dtype=np.float64) for p in quad]
    cells = []
    total_gap = gap_ratio * (n - 1)
    cell = (1.0 - total_gap) / n
    for i in range(n):
        a = i * (cell + gap_ratio)
        b = a + cell
        if not vertical:
            p0 = tl + (tr - tl) * a
            p1 = tl + (tr - tl) * b
            p3 = bl + (br - bl) * a
            p2 = bl + (br - bl) * b
        else:
            p0 = tl + (bl - tl) * a
            p3 = tl + (bl - tl) * b
            p1 = tr + (br - tr) * a
            p2 = tr + (br - tr) * b
        cells.append([p0.tolist(), p1.tolist(), p2.tolist(), p3.tolist()])
    return cells


def display_proxy(w: int, h: int, *, bezel_ratio: float = 0.012, screen: Image.Image | None = None,
                  ceiling: bool = False) -> Image.Image:
    """디스플레이 대역(검은 얇은 베젤 + 화면) RGBA — 결정적 합성 초안의 제품 그림."""
    w, h = max(8, w), max(8, h)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], fill=(18, 20, 23, 255))
    b = max(2, int(round(min(w, h) * bezel_ratio * 2.2)))
    if screen is not None:
        im.paste(screen.convert("RGB").resize((w - 2 * b, h - 2 * b), Image.Resampling.LANCZOS), (b, b))
    else:
        grad = np.linspace(0, 1, h - 2 * b, dtype=np.float32)[:, None]
        base = np.array([20, 40, 160], np.float32) * (1 - grad[..., None] * 0.5) + np.array([10, 16, 60], np.float32) * grad[..., None] * 0.5
        arr = np.repeat(base, w - 2 * b, axis=1).astype(np.uint8)
        im.paste(Image.fromarray(arr), (b, b))
    if ceiling:
        bw = max(2, w // 40)
        canvas = Image.new("RGBA", (w, h + h // 6), (0, 0, 0, 0))
        cd = ImageDraw.Draw(canvas)
        for x in (w // 4, 3 * w // 4):
            cd.rectangle([x - bw, 0, x + bw, h // 6], fill=(60, 64, 70, 255))
        canvas.paste(im, (0, h // 6), im)
        return canvas
    return im


_MENU_COLORS = [((36, 28, 22), (210, 160, 90)), ((20, 30, 40), (90, 170, 200)), ((40, 20, 24), (220, 110, 90)),
                ((24, 34, 22), (150, 200, 110))]


def menu_template(w: int, h: int, idx: int = 0) -> Image.Image:
    """로고 없는 메뉴 템플릿(번들 대신 결정적으로 그림): 어두운 바탕 + 사진 칸 + 글자 막대."""
    bg, accent = _MENU_COLORS[idx % len(_MENU_COLORS)]
    im = Image.new("RGB", (max(8, w), max(8, h)), bg)
    d = ImageDraw.Draw(im)
    pad = max(2, w // 20)
    ph = int(h * 0.45)
    d.rectangle([pad, pad, w - pad, pad + ph], fill=accent)
    d.ellipse([w // 2 - ph // 4, pad + ph // 4, w // 2 + ph // 4, pad + 3 * ph // 4], fill=tuple(min(255, c + 40) for c in accent))
    y = pad + ph + pad
    bar = max(2, h // 18)
    for i in range(3):
        if y + bar > h - pad:
            break
        d.rectangle([pad, y, int(w * (0.85 - 0.15 * i)), y + bar], fill=(235, 230, 220))
        d.rectangle([int(w * 0.88), y, w - pad, y + bar], fill=accent)
        y += bar * 2
    return im


def local_harmonize(photo: Image.Image, composite: Image.Image, mask: Image.Image, *, strength: float = 1.0,
                    variant: int = 0) -> Image.Image:
    """현장 사진 로컬 조화: 제품 영역 색 전달(주변 평균으로 살짝) + 아래 접촉 그림자 + 화면 반사 그라데이션."""
    w, h = composite.size
    m = mask.convert("L").point(lambda v: 255 if v >= 128 else 0)
    bb = m.getbbox()
    out = composite.convert("RGB").copy()
    if bb is None:
        return out
    x0, y0, x1, y1 = bb
    # 1) 접촉 그림자: 제품 아래 · 오른쪽으로 부드러운 그림자
    shadow = Image.new("L", (w, h), 0)
    off = max(2, (y1 - y0) // 30)
    sd = ImageDraw.Draw(shadow)
    sd.rectangle([x0 + off, y0 + off * 2, x1 + off, y1 + off * 2], fill=int(110 * strength))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(3, (y1 - y0) // 18)))
    shadow = ImageChops.subtract(shadow, m)
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    out = Image.composite(dark, out, shadow.point(lambda v: int(v * 0.55)))
    # 2) 색 전달: 주변(쿼드 둘레 링) 평균 색으로 제품 화면을 아주 조금 물들인다
    ring = ImageChops.subtract(dilate(m, max(4, (x1 - x0) // 12)), m)
    p = np.asarray(photo.convert("RGB").resize((w, h))).astype(np.float32)
    rm = np.asarray(ring) >= 128
    if rm.any():
        env = p[rm].mean(axis=0)
        a = np.asarray(out).astype(np.float32)
        mm = (np.asarray(m) >= 128)[..., None]
        tint = 0.06 + 0.02 * (variant % 3)
        a = np.where(mm, a * (1 - tint) + env * tint, a)
        out = Image.fromarray(np.clip(np.rint(a), 0, 255).astype(np.uint8))
    # 3) 화면 반사: 왼쪽 위 → 오른쪽 아래 밝은 그라데이션(제품 영역 안)
    grad = np.zeros((h, w), np.float32)
    gx = np.linspace(1, 0, x1 - x0, dtype=np.float32)[None, :]
    gy = np.linspace(1, 0, y1 - y0, dtype=np.float32)[:, None]
    grad[y0:y1, x0:x1] = np.clip((gx * 0.6 + gy * 0.4) - 0.35, 0, 1) * 0.22 * strength
    grad *= (np.asarray(m) >= 128)
    a = np.asarray(out).astype(np.float32)
    a = a + grad[..., None] * (255 - a)
    return Image.fromarray(np.clip(np.rint(a), 0, 255).astype(np.uint8))


# ── 표기 ─────────────────────────────────────────────────

def bake_ai_label(im: Image.Image, text: str = "AI 생성 이미지") -> Image.Image:
    """오른쪽 아래(여백 = 짧은 변의 2%)에 글자(높이 = 짧은 변의 1.6%, 흰 글자 + 50% 검정 그림자)."""
    out = im.convert("RGB").copy()
    w, h = out.size
    short = min(w, h)
    size = max(10, int(round(short * 0.016)))
    margin = max(4, int(round(short * 0.02)))
    f = font(size)
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    bbox = d.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = w - margin - tw - bbox[0]
    y = h - margin - th - bbox[1]
    sh = max(1, size // 10)
    d.text((x + sh, y + sh), text, font=f, fill=(0, 0, 0, 128))
    d.text((x, y), text, font=f, fill=(255, 255, 255, 255))
    return Image.alpha_composite(out.convert("RGBA"), layer).convert("RGB")


def ai_label_box(size: tuple[int, int]) -> tuple[int, int, int, int]:
    """표기 영역(px) — 검증용."""
    w, h = size
    short = min(w, h)
    margin = max(4, int(round(short * 0.02)))
    s = max(10, int(round(short * 0.016)))
    return (w - margin - s * 9, h - margin - s * 2, w - margin + 2, h - margin + 2)


def checker(w: int, h: int, seed: int = 0) -> Image.Image:
    """테스트 · 대체용 결정적 패턴."""
    rng = np.random.default_rng(seed)
    base = rng.integers(40, 200, size=(max(1, h // 16) + 1, max(1, w // 16) + 1, 3)).astype(np.uint8)
    im = Image.fromarray(base).resize((w, h), Image.Resampling.NEAREST)
    return im
