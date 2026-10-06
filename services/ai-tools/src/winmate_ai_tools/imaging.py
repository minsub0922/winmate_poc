"""이미지 다루기 — 불러오기(file_id · url · data_b64) · HEIC→JPEG · 축소 · 비율 · 마스크 · 잘라 붙이기 · 캔버스 확장 · mock 이미지.

Pillow 작업은 CPU 를 쓰므로 async 코드에서는 `await asyncio.to_thread(fn, ...)` 로 부른다.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import ipaddress
import logging
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from winmate_common.contracts import ContractViolation
from winmate_common.errors import ApiError

from .errors import files_unavailable, invalid

log = logging.getLogger("winmate.ai_tools.imaging")

try:  # HEIC/HEIF(아이폰 사진)
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:  # noqa: BLE001
    log.warning("pillow-heif 를 불러오지 못해 HEIC 를 열 수 없습니다")

MAX_DOWNLOAD = 20 * 1024 * 1024
GEMINI_ASPECTS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
CROP_ASPECTS = ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3"]
_MIME = {"JPEG": "image/jpeg", "MPO": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif",
         "HEIF": "image/heif", "HEIC": "image/heic", "BMP": "image/bmp", "TIFF": "image/tiff"}


@dataclass
class Img:
    data: bytes
    mime: str
    width: int
    height: int

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    @property
    def ext(self) -> str:
        return {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(self.mime, "bin")

    def pil(self) -> Image.Image:
        return open_image(self.data)


# ── 불러오기 ───────────────────────────────────────────────

def _decode_b64(data: str) -> tuple[bytes, str | None]:
    mime = None
    if data.startswith("data:"):
        head, _, data = data.partition(",")
        mime = head[5:].split(";")[0] or None
    try:
        return base64.b64decode(data, validate=False), mime
    except (binascii.Error, ValueError) as exc:
        raise invalid(f"data_b64 를 해석하지 못했습니다: {exc}", code="BAD_IMAGE") from exc


def blocked_host(host: str) -> bool:
    if host in ("localhost", "localhost.localdomain") or host.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast


async def download(url: str, *, timeout_s: float = 30.0, max_bytes: int = MAX_DOWNLOAD) -> tuple[bytes, str | None]:
    if url.startswith("data:"):
        return _decode_b64(url)
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise invalid(f"이미지 url 은 http(s) 또는 data: 만 됩니다: {url[:80]}", code="BAD_IMAGE")
    if blocked_host(u.hostname):
        raise invalid("내부 주소(localhost 등) 이미지는 url 로 받을 수 없습니다. file_id 또는 data_b64 를 쓰세요", code="BAD_IMAGE")
    try:
        async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as c:
            async with c.stream("GET", url) as resp:
                if resp.status_code >= 400:
                    raise invalid(f"이미지를 내려받지 못했습니다(HTTP {resp.status_code}): {url[:120]}", code="BAD_IMAGE")
                buf = bytearray()
                async for chunk in resp.aiter_bytes():
                    buf += chunk
                    if len(buf) > max_bytes:
                        raise invalid(f"이미지가 너무 큽니다(>{max_bytes // (1024 * 1024)}MB)", code="BAD_IMAGE")
                return bytes(buf), resp.headers.get("content-type")
    except httpx.TimeoutException as exc:
        raise ApiError(504, "TIMEOUT", f"이미지 내려받기 시간 초과: {url[:120]}") from exc
    except httpx.HTTPError as exc:
        raise invalid(f"이미지를 내려받지 못했습니다: {exc}", code="BAD_IMAGE") from exc


async def file_bytes(file_id: str) -> tuple[bytes, str]:
    """files 서비스에서 원본 바이트를 받는다(ServiceClient → 게이트웨이)."""
    from winmate_common.platform import file_bytes as _fb

    try:
        return await _fb(file_id)
    except ApiError as exc:
        if exc.status == 404:
            raise ApiError(404, "NOT_FOUND", f"파일을 찾을 수 없습니다: {file_id}", {"file_id": file_id}) from exc
        raise files_unavailable(exc.message, file_id=file_id, upstream_code=exc.code) from exc
    except ContractViolation as exc:
        raise files_unavailable(str(exc), file_id=file_id) from exc
    except httpx.HTTPError as exc:
        raise files_unavailable(str(exc) or type(exc).__name__, file_id=file_id) from exc


async def load_raw(ref: dict[str, Any]) -> tuple[bytes, str | None]:
    """{file_id} | {url} | {data_b64, mime} → (바이트, mime 힌트)."""
    if ref.get("file_id"):
        data, mime = await file_bytes(str(ref["file_id"]))
        return data, mime
    if ref.get("data_b64"):
        data, mime = _decode_b64(str(ref["data_b64"]))
        return data, ref.get("mime") or mime
    if ref.get("url"):
        return await download(str(ref["url"]))
    raise invalid("이미지에는 file_id · url · data_b64 중 하나가 필요합니다", code="BAD_IMAGE")


def open_image(data: bytes) -> Image.Image:
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
        return im
    except Exception as exc:  # noqa: BLE001
        raise invalid(f"이미지를 열지 못했습니다: {type(exc).__name__}: {exc}", code="BAD_IMAGE") from exc


def encode(im: Image.Image, fmt: str | None = None, *, quality: int = 90) -> tuple[bytes, str]:
    """PIL → (바이트, mime). fmt 없으면 알파가 있으면 PNG, 아니면 JPEG."""
    if fmt is None:
        fmt = "PNG" if has_alpha(im) else "JPEG"
    buf = io.BytesIO()
    if fmt == "JPEG":
        im = im.convert("RGB") if im.mode not in ("RGB", "L") else im
        im.save(buf, "JPEG", quality=quality, optimize=True)
        return buf.getvalue(), "image/jpeg"
    if im.mode not in ("RGB", "RGBA", "L", "LA", "P"):
        im = im.convert("RGBA" if has_alpha(im) else "RGB")
    im.save(buf, "PNG", optimize=False)
    return buf.getvalue(), "image/png"


def has_alpha(im: Image.Image) -> bool:
    return im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info)


def to_rgb(im: Image.Image) -> Image.Image:
    """합성용 모드(RGB 또는 RGBA)로."""
    if has_alpha(im):
        return im.convert("RGBA")
    return im.convert("RGB") if im.mode != "RGB" else im


def prepare(data: bytes, max_side: int) -> Img:
    """모델에 보낼 형태로: HEIC·GIF·BMP 등 → JPEG/PNG, EXIF 회전 적용, 긴 변 ≤ max_side. 손댈 필요 없으면 원본 바이트."""
    im = open_image(data)
    fmt = (im.format or "").upper()
    w, h = im.size
    try:
        orientation = im.getexif().get(274, 1)
    except Exception:  # noqa: BLE001
        orientation = 1
    needs = (
        fmt not in ("JPEG", "PNG", "WEBP")
        or max(w, h) > max_side
        or orientation not in (None, 1)
        or (fmt == "JPEG" and im.mode not in ("RGB", "L"))
    )
    if not needs:
        return Img(data, _MIME[fmt], w, h)
    im = ImageOps.exif_transpose(im)
    if max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    im = to_rgb(im)
    out, mime = encode(im)
    return Img(out, mime, im.width, im.height)


def from_pil(im: Image.Image, fmt: str = "PNG") -> Img:
    data, mime = encode(im, fmt)
    return Img(data, mime, im.width, im.height)


# ── 비율 ───────────────────────────────────────────────────

def parse_aspect(aspect: str) -> float:
    try:
        a, b = aspect.replace("x", ":").replace("/", ":").split(":")
        r = float(a) / float(b)
        if not (0.1 <= r <= 10) or not math.isfinite(r):
            raise ValueError
        return r
    except (ValueError, ZeroDivisionError):
        raise invalid(f"aspect 형식이 올바르지 않습니다: {aspect!r} (예: 16:9)", aspect=aspect) from None


def size_for_aspect(ratio: float, max_side: int, *, multiple: int = 1) -> tuple[int, int]:
    if ratio >= 1:
        w, h = max_side, max_side / ratio
    else:
        w, h = max_side * ratio, max_side
    if multiple > 1:
        return max(multiple, int(round(w / multiple)) * multiple), max(multiple, int(round(h / multiple)) * multiple)
    return max(1, int(round(w))), max(1, int(round(h)))


def nearest_aspect(ratio: float, choices: list[str]) -> str:
    return min(choices, key=lambda c: abs(math.log(parse_aspect(c)) - math.log(ratio)))


def center_crop(im: Image.Image, ratio: float, *, tolerance: float = 0.005) -> Image.Image:
    w, h = im.size
    if abs(w / h - ratio) / ratio <= tolerance:
        return im
    if w / h > ratio:
        nw = int(round(h * ratio))
        x0 = (w - nw) // 2
        return im.crop((x0, 0, x0 + nw, h))
    nh = int(round(w / ratio))
    y0 = (h - nh) // 2
    return im.crop((0, y0, w, y0 + nh))


# ── 마스크 · 합성 ──────────────────────────────────────────

def mask_from_box(box: list[float], size: tuple[int, int]) -> Image.Image:
    w, h = size
    x0, y0, x1, y1 = (max(0.0, min(1.0, float(v))) for v in box)
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    m = Image.new("L", size, 0)
    px = (int(math.floor(x0 * w)), int(math.floor(y0 * h)), int(math.ceil(x1 * w)), int(math.ceil(y1 * h)))
    if px[2] > px[0] and px[3] > px[1]:
        ImageDraw.Draw(m).rectangle((px[0], px[1], px[2] - 1, px[3] - 1), fill=255)
    return m


def mask_from_image(mask: Image.Image, size: tuple[int, int]) -> Image.Image:
    """마스크 이미지 → L(255=수정). 투명한 곳이 있으면 투명=수정(OpenAI 방식), 아니면 밝은 곳(≥128)=수정."""
    if has_alpha(mask):
        alpha = mask.convert("RGBA").getchannel("A")
        if alpha.getextrema()[0] < 255:
            m = alpha.point(lambda a: 255 if a < 128 else 0)
        else:
            m = mask.convert("L").point(lambda v: 255 if v >= 128 else 0)
    else:
        m = mask.convert("L").point(lambda v: 255 if v >= 128 else 0)
    if m.size != size:
        m = m.resize(size, Image.Resampling.NEAREST)
    return m


def feather_inward(mask: Image.Image, radius: float) -> Image.Image:
    """마스크 안쪽으로만 부드럽게(바깥은 0 그대로 — 마스크 밖 픽셀은 절대 바뀌지 않는다)."""
    if radius <= 0:
        return mask
    return ImageChops.darker(mask, mask.filter(ImageFilter.GaussianBlur(radius)))


def composite(original: Image.Image, edited: Image.Image, mask: Image.Image, feather: float) -> Image.Image:
    """mask(255=수정) 안쪽만 edited 로 바꾼다. 마스크 밖은 original 픽셀 그대로."""
    base = to_rgb(original)
    ed = edited if edited.size == base.size else edited.resize(base.size, Image.Resampling.LANCZOS)
    ed = ed.convert(base.mode)
    alpha = feather_inward(mask, feather)
    return Image.composite(ed, base, alpha)


def crop_box_for_mask(mask: Image.Image, *, min_pad: int = 64, pad_ratio: float = 0.25,
                      aspects: list[str] = CROP_ASPECTS) -> tuple[int, int, int, int] | None:
    """마스크 bbox 를 넓힌 크롭 상자: max(64px, 짧은 변의 25%) 여백 + 가장 가까운 지원 비율로 넓힘(줄이지 않음) + 이미지 안으로."""
    bbox = mask.getbbox()
    if bbox is None:
        return None
    W, H = mask.size
    x0, y0, x1, y1 = bbox
    pad = max(min_pad, pad_ratio * min(x1 - x0, y1 - y0))
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    cw, ch = x1 - x0, y1 - y0
    target = parse_aspect(nearest_aspect(cw / ch, aspects))
    if cw / ch < target:
        grow = ch * target - cw
        x0, x1 = x0 - grow / 2, x1 + grow / 2
    else:
        grow = cw / target - ch
        y0, y1 = y0 - grow / 2, y1 + grow / 2

    def fit(a: float, b: float, limit: int) -> tuple[int, int]:
        size = b - a
        if size >= limit:
            return 0, limit
        if a < 0:
            a, b = 0, size
        if b > limit:
            a, b = limit - size, limit
        return int(math.floor(a)), int(math.ceil(b))

    ix0, ix1 = fit(x0, x1, W)
    iy0, iy1 = fit(y0, y1, H)
    return max(0, ix0), max(0, iy0), min(W, ix1), min(H, iy1)


def send_size(w: int, h: int, *, max_long: int = 1024, min_long: int = 512) -> tuple[int, int]:
    """크롭을 제공자에 보낼 크기: 긴 변 > 1024 → 1024, < 512 → 512."""
    long_side = max(w, h)
    scale = 1.0
    if long_side > max_long:
        scale = max_long / long_side
    elif long_side < min_long:
        scale = min_long / long_side
    return max(1, int(round(w * scale))), max(1, int(round(h * scale)))


def extend_canvas(im: Image.Image, ratio: float) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """목표 비율로 캔버스를 넓힌다: 빈 곳 = 가장자리 거울 반사 + 블러, 원본은 가운데 그대로. → (캔버스, 원본 상자)"""
    src = to_rgb(im)
    w, h = src.size
    if w / h < ratio:
        W, H = int(round(h * ratio)), h
    else:
        W, H = w, int(round(w / ratio))
    x0, y0 = (W - w) // 2, (H - h) // 2
    arr = np.asarray(src)
    pads = ((y0, H - h - y0), (x0, W - w - x0)) + (((0, 0),) if arr.ndim == 3 else ())
    fits = y0 <= h and (H - h - y0) <= h and x0 <= w and (W - w - x0) <= w
    padded = np.pad(arr, pads, mode="symmetric" if fits else "edge")
    canvas = Image.fromarray(np.ascontiguousarray(padded))
    canvas = canvas.filter(ImageFilter.GaussianBlur(max(4.0, max(W, H) / 40)))
    canvas.paste(src, (x0, y0))
    return canvas, (x0, y0, x0 + w, y0 + h)


# ── mock 이미지 ────────────────────────────────────────────
_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/Library/Fonts/AppleGothic.ttf",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
]


@lru_cache(maxsize=16)
def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in _FONT_CANDIDATES:
        if Path(p).is_file():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # 오래된 Pillow
        return ImageFont.load_default()


def _colors(seed: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    d = hashlib.sha256(seed.encode("utf-8")).digest()
    a = (60 + d[0] % 150, 60 + d[1] % 150, 60 + d[2] % 150)
    b = (40 + d[3] % 180, 40 + d[4] % 180, 40 + d[5] % 180)
    return a, b


def _wrap(text: str, font: Any, width: int, max_lines: int) -> list[str]:
    lines: list[str] = []
    for para in text.splitlines() or [""]:
        cur = ""
        for ch in para:
            if font.getlength(cur + ch) > width and cur:
                lines.append(cur)
                cur = ch.lstrip()
                if len(lines) >= max_lines:
                    return lines
            else:
                cur += ch
        lines.append(cur)
        if len(lines) >= max_lines:
            break
    return lines[:max_lines]


def mock_generate(prompt: str, ratio: float, max_side: int, *, seed: str, label: str = "[mock] T2I",
                  refs: list[Image.Image] | None = None) -> Image.Image:
    """결정적 mock 이미지: 그라데이션 + 프롬프트 글자(정확한 비율, 긴 변 = max_side)."""
    w, h = size_for_aspect(ratio, max_side)
    c1, c2 = _colors(seed)
    t = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :, None]
    s = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    mix = np.clip(0.65 * t + 0.35 * s, 0, 1)
    arr = (np.array(c1, dtype=np.float32) * (1 - mix) + np.array(c2, dtype=np.float32) * mix).astype(np.uint8)
    im = Image.fromarray(arr)
    if refs:
        th = max(24, h // 5)
        x = 8
        for r in refs[:4]:
            tn = to_rgb(r).convert("RGB")
            tn.thumbnail((th * 2, th))
            im.paste(tn, (x, h - tn.height - 8))
            x += tn.width + 8
    draw = ImageDraw.Draw(im)
    fs = max(12, min(w, h) // 18)
    font = _font(fs)
    margin = max(8, w // 30)
    draw.text((margin, margin), label, fill=(255, 255, 255), font=_font(max(12, fs + 4)))
    y = margin + int(fs * 1.8)
    for line in _wrap(prompt or "", font, w - 2 * margin, max(1, (h - y - margin) // int(fs * 1.4) - (2 if refs else 0))):
        draw.text((margin, y), line, fill=(255, 255, 255), font=font)
        y += int(fs * 1.4)
    return im


def mock_edit(im: Image.Image, prompt: str) -> Image.Image:
    """결정적 mock 편집: 색 반전 + 옅은 색조 + 지시문 글자(모든 픽셀이 바뀐다)."""
    base = to_rgb(im).convert("RGB")
    inv = ImageOps.invert(base)
    tint = Image.new("RGB", base.size, _colors(prompt)[0])
    out = Image.blend(inv, tint, 0.2)
    draw = ImageDraw.Draw(out)
    fs = max(10, min(out.size) // 16)
    draw.text((6, 6), "[mock edit]", fill=(255, 255, 255), font=_font(fs))
    for i, line in enumerate(_wrap(prompt or "", _font(fs), max(10, out.width - 12), 3)):
        draw.text((6, 6 + int(fs * 1.4) * (i + 1)), line, fill=(255, 255, 255), font=_font(fs))
    return out
