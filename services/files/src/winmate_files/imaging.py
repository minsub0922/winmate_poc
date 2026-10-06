"""Pillow 도우미 — EXIF 회전, HEIC→JPEG, 썸네일, 파일 형식 아이콘, 슬라이드 자리표시 카드, 한글 글꼴."""
from __future__ import annotations

import io
import logging
import os
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, ImageDraw, ImageFont, ImageOps

log = logging.getLogger("winmate.files.imaging")

_heif_lock = threading.Lock()
_heif_ready = False

# 사진이 크면(예 48MP) 디코딩 폭탄 검사에 걸리지 않게 여유를 둔다(기본 89MP → 180MP)
Image.MAX_IMAGE_PIXELS = 180_000_000


def ensure_heif() -> bool:
    global _heif_ready
    if _heif_ready:
        return True
    with _heif_lock:
        if _heif_ready:
            return True
        try:
            import pillow_heif

            pillow_heif.register_heif_opener()
            _heif_ready = True
        except Exception as exc:  # noqa: BLE001
            log.warning("pillow-heif 사용 불가: %s", exc)
    return _heif_ready


def open_image(data: bytes) -> Image.Image:
    ensure_heif()
    img = Image.open(io.BytesIO(data))
    return img


def oriented(img: Image.Image) -> Image.Image:
    try:
        return ImageOps.exif_transpose(img) or img
    except Exception:  # noqa: BLE001 — 깨진 EXIF
        return img


_EXIF_NAMES = {v: k for k, v in ExifTags.TAGS.items()}


def _exif_dt(value: Any, offset: Any = None) -> str | None:
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.strptime(value.strip()[:19], "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    tz = None
    if isinstance(offset, str) and len(offset) >= 6 and offset[0] in "+-":
        try:
            sign = 1 if offset[0] == "+" else -1
            hh, mm = int(offset[1:3]), int(offset[4:6])
            tz = timezone(sign * timedelta(hours=hh, minutes=mm))
        except ValueError:
            tz = None
    if tz is None:
        return dt.strftime("%Y-%m-%dT%H:%M:%S")  # 시간대 모름(현지 시각)
    return dt.replace(tzinfo=tz).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def exif_summary(img: Image.Image) -> dict[str, Any]:
    try:
        exif = img.getexif()
    except Exception:  # noqa: BLE001
        return {}
    if not exif:
        return {}
    out: dict[str, Any] = {}
    try:
        sub = exif.get_ifd(ExifTags.IFD.Exif)
    except Exception:  # noqa: BLE001
        sub = {}
    orientation = exif.get(_EXIF_NAMES["Orientation"])
    if orientation:
        out["orientation"] = int(orientation)
    for key in ("Make", "Model", "Software", "Artist"):
        v = exif.get(_EXIF_NAMES[key])
        if isinstance(v, str) and v.strip("\x00 "):
            out[key.lower()] = v.strip("\x00 ")[:120]
    taken = _exif_dt(sub.get(_EXIF_NAMES["DateTimeOriginal"]), sub.get(0x9011)) or _exif_dt(exif.get(_EXIF_NAMES["DateTime"]))
    if taken:
        out["taken_at"] = taken
    return out


def image_info(data: bytes) -> dict[str, Any]:
    """가로 · 세로(EXIF 회전 반영) · 형식 · 프레임 수 · EXIF 요약. 실패하면 {}."""
    try:
        img = open_image(data)
    except Exception:  # noqa: BLE001
        return {}
    w, h = img.size
    exif = exif_summary(img)
    if exif.get("orientation") in (5, 6, 7, 8):
        w, h = h, w
    frames = int(getattr(img, "n_frames", 1) or 1)
    info: dict[str, Any] = {"width": w, "height": h, "format": (img.format or "").lower(), "mode": img.mode}
    if frames > 1:
        info["frames"] = frames
    if exif:
        info["exif"] = exif
    return info


def heic_to_jpeg(data: bytes, quality: int = 90) -> tuple[bytes, dict[str, Any]]:
    """HEIC/HEIF → JPEG(회전 적용, EXIF 의 회전 값 제거, ICC 유지)."""
    if not ensure_heif():
        raise RuntimeError("pillow-heif 없음")
    img = Image.open(io.BytesIO(data))
    exif = exif_summary(img)
    img = oriented(img)
    icc = img.info.get("icc_profile")
    exif_bytes = img.info.get("exif")
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    kw: dict[str, Any] = {"quality": quality, "optimize": True}
    if icc:
        kw["icc_profile"] = icc
    if exif_bytes:
        kw["exif"] = exif_bytes
    img.save(buf, "JPEG", **kw)
    exif.pop("orientation", None)
    return buf.getvalue(), {"width": img.size[0], "height": img.size[1], "exif": exif}


def fit_width(img: Image.Image, w: int, *, max_ratio: float = 2.0, upscale: bool = False) -> Image.Image:
    """가로 w 에 맞춘다(세로는 w*max_ratio 까지). 작은 그림은 키우지 않는다."""
    iw, ih = img.size
    if iw <= 0 or ih <= 0:
        return img
    target_w = w if (upscale or iw > w) else iw
    target_h = round(ih * target_w / iw)
    max_h = int(w * max_ratio)
    if target_h > max_h:
        target_h = max_h
        target_w = max(1, round(iw * target_h / ih))
    if (target_w, target_h) == (iw, ih):
        return img
    return img.resize((max(1, target_w), max(1, target_h)), Image.Resampling.LANCZOS)


def encode(img: Image.Image, fmt: str, *, quality: int = 82) -> bytes:
    fmt = fmt.lower()
    buf = io.BytesIO()
    if fmt in ("jpeg", "jpg"):
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            rgba = img.convert("RGBA")
            bg.paste(rgba, mask=rgba.split()[-1])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(buf, "JPEG", quality=quality, optimize=True)
    elif fmt == "webp":
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.mode or img.mode == "P" else "RGB")
        img.save(buf, "WEBP", quality=quality, method=4)
    else:
        if img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
            img = img.convert("RGBA" if "A" in img.mode else "RGB")
        img.save(buf, "PNG", optimize=False, compress_level=6)
    return buf.getvalue()


def image_thumbnail(data: bytes, w: int, fmt: str) -> bytes:
    img = open_image(data)
    try:
        img.seek(0)
    except Exception:  # noqa: BLE001
        pass
    if img.format == "JPEG":
        img.draft("RGB", (w * 2, w * 4))  # 큰 JPEG 빠른 축소 디코딩
    img = oriented(img)
    if img.mode in ("CMYK", "YCbCr", "I", "I;16", "F"):
        img = img.convert("RGB")
    return encode(fit_width(img, w), fmt)


def page_image(data: bytes, w: int, fmt: str) -> bytes:
    """이미지 파일 그대로를 '1쪽'으로(회전 반영, 가로 w 이하로 줄임)."""
    img = oriented(open_image(data))
    if img.mode in ("CMYK", "YCbCr", "I", "I;16", "F"):
        img = img.convert("RGB")
    return encode(fit_width(img, w, max_ratio=100.0), fmt)


# ── 글꼴 ───────────────────────────────────────────────────────

_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-{w}.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-{w}.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-{w}.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic{nw}.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/Library/Fonts/AppleGothic.ttf",
    "C:/Windows/Fonts/malgun{mw}.ttf",
]


@lru_cache(maxsize=4)
def _font_file(bold: bool) -> tuple[str | None, int]:
    env_path = os.environ.get("FILES_FONT_PATH")
    if env_path and Path(env_path).is_file():
        return env_path, 0
    w = "Bold" if bold else "Regular"
    for pat in _FONT_CANDIDATES:
        p = pat.format(w=w, nw="Bold" if bold else "", mw="bd" if bold else "")
        if Path(p).is_file():
            index = 0
            if p.endswith(".ttc") and "NotoSansCJK" in p:
                index = _ttc_index(p, "KR")
            return p, index
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}", f"sans-serif:lang=ko{':weight=bold' if bold else ''}"],
                             capture_output=True, text=True, timeout=5)
        p = out.stdout.strip()
        if p and Path(p).is_file():
            return p, 0
    except (OSError, subprocess.SubprocessError):
        pass
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
        if Path(p).is_file():
            return p, 0
    return None, 0


def _ttc_index(path: str, tag: str) -> int:
    for i in range(10):
        try:
            f = ImageFont.truetype(path, 12, index=i)
        except OSError:
            break
        if tag in " ".join(f.getname()):
            return i
    return 0


@lru_cache(maxsize=64)
def font(size: int, bold: bool = False) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    path, index = _font_file(bold)
    if path:
        try:
            return ImageFont.truetype(path, size, index=index)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, fnt: Any, max_w: int, max_lines: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            trial = cur + ch
            if draw.textlength(trial, font=fnt) <= max_w:
                cur = trial
                continue
            # 공백 기준으로 끊을 수 있으면 끊는다
            if " " in cur and not ch.isspace():
                head, _, tail = cur.rpartition(" ")
                lines.append(head)
                cur = tail + ch
            else:
                lines.append(cur)
                cur = ch.lstrip()
            if len(lines) >= max_lines:
                break
        if len(lines) >= max_lines:
            break
        lines.append(cur)
        if len(lines) >= max_lines:
            break
    lines = [ln for ln in lines if ln is not None][:max_lines]
    joined = "".join(text.split())
    shown = "".join("".join(lines).split())
    if lines and len(shown) < len(joined):
        last = lines[-1]
        while last and draw.textlength(last + "…", font=fnt) > max_w:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


# ── 파일 형식 아이콘 ───────────────────────────────────────────

KIND_COLORS = {
    "pdf": (217, 48, 37), "pptx": (210, 71, 38), "docx": (43, 87, 154), "xlsx": (33, 115, 70),
    "text": (95, 99, 104), "email": (103, 58, 183), "zip": (121, 85, 72), "svg": (0, 137, 123),
    "image": (20, 40, 160), "other": (96, 125, 139),
}


def file_icon(label: str, kind: str, w: int) -> bytes:
    """문서 모양 아이콘(접힌 모서리 + 형식 글자) PNG. 가로 w, 세로 w*1.25."""
    w = max(32, min(w, 1024))
    h = int(w * 1.25)
    scale = 4
    W, H = w * scale, h * scale
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    color = KIND_COLORS.get(kind, KIND_COLORS["other"])
    m = int(W * 0.14)
    fold = int(W * 0.22)
    x0, y0, x1, y1 = m, int(H * 0.06), W - m, H - int(H * 0.06)
    body = [(x0, y0), (x1 - fold, y0), (x1, y0 + fold), (x1, y1), (x0, y1)]
    d.polygon(body, fill=(255, 255, 255, 255), outline=(200, 205, 214, 255))
    d.line(body + [body[0]], fill=(200, 205, 214, 255), width=max(2, W // 80))
    d.polygon([(x1 - fold, y0), (x1 - fold, y0 + fold), (x1, y0 + fold)], fill=(226, 229, 234, 255))
    band_h = int(H * 0.2)
    by0 = int(H * 0.55)
    d.rectangle([x0 - int(W * 0.06), by0, x1 - int(W * 0.1), by0 + band_h], fill=color + (255,))
    text = (label or "FILE")[:5]
    size = int(band_h * 0.62)
    fnt = font(size, bold=True)
    while size > 8 and d.textlength(text, font=fnt) > (x1 - x0) * 0.9:
        size -= 2
        fnt = font(size, bold=True)
    tw = d.textlength(text, font=fnt)
    tx = (x0 - int(W * 0.06) + x1 - int(W * 0.1) - tw) / 2
    d.text((tx, by0 + band_h / 2), text, font=fnt, fill=(255, 255, 255, 255), anchor="lm")
    # 본문 줄 무늬
    for i in range(3):
        ly = int(H * 0.22) + i * int(H * 0.08)
        d.rounded_rectangle([x0 + int(W * 0.1), ly, x1 - int(W * 0.18) - (i == 2) * int(W * 0.15), ly + int(H * 0.025)],
                            radius=int(H * 0.012), fill=(226, 229, 234, 255))
    img = img.resize((w, h), Image.Resampling.LANCZOS)
    return encode(img, "png")


# ── 슬라이드 자리표시 카드(LibreOffice 없을 때) ─────────────────


def slide_card(
    *,
    title: str | None,
    body: list[str],
    images: list[list[float]],
    page_no: int,
    page_count: int,
    aspect: float,
    w: int,
    label: str = "PPTX",
) -> Image.Image:
    """슬라이드 제목 · 본문 몇 줄 · 이미지 자리(bbox)를 그린 카드. aspect = 가로/세로."""
    w = max(64, min(w, 2048))
    h = max(36, int(round(w / max(0.3, min(aspect, 4.0)))))
    scale = 2
    W, H = w * scale, h * scale
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=(214, 219, 228), width=max(2, W // 300))
    # 이미지 자리
    for bb in images[:8]:
        try:
            x0, y0, x1, y1 = (max(0.0, min(1.0, float(v))) for v in bb)
        except (TypeError, ValueError):
            continue
        if x1 - x0 < 0.02 or y1 - y0 < 0.02:
            continue
        box = [int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)]
        d.rectangle(box, fill=(238, 241, 247), outline=(214, 219, 228))
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        r = min(box[2] - box[0], box[3] - box[1]) * 0.18
        d.polygon([(cx - r, cy + r * 0.7), (cx - r * 0.2, cy - r * 0.5), (cx + r * 0.3, cy + r * 0.2),
                   (cx + r * 0.6, cy - r * 0.1), (cx + r, cy + r * 0.7)], fill=(200, 207, 220))
    pad = int(W * 0.06)
    tsize = max(10, int(H * 0.085))
    tfont = font(tsize, bold=True)
    y = int(H * 0.12)
    if title:
        for line in _wrap(d, title.strip(), tfont, W - pad * 2, 2):
            d.text((pad, y), line, font=tfont, fill=(18, 20, 23))
            y += int(tsize * 1.3)
    bsize = max(8, int(H * 0.05))
    bfont = font(bsize)
    y += int(bsize * 0.6)
    for para in body:
        if y > H - int(H * 0.16):
            break
        for line in _wrap(d, para.strip(), bfont, W - pad * 2, 2):
            if y > H - int(H * 0.16):
                break
            d.text((pad, y), line, font=bfont, fill=(89, 97, 112))
            y += int(bsize * 1.4)
    # 바닥: 형식 배지 · 쪽 번호
    small = font(max(8, int(H * 0.045)), bold=True)
    badge = f" {label} "
    bw = d.textlength(badge, font=small)
    by = H - int(H * 0.1)
    d.rounded_rectangle([pad, by - int(H * 0.035), pad + bw, by + int(H * 0.035)], radius=int(H * 0.02), fill=(234, 238, 251))
    d.text((pad, by), badge, font=small, fill=(20, 40, 160), anchor="lm")
    num = f"{page_no} / {page_count}" if page_count else str(page_no)
    d.text((W - pad, by), num, font=small, fill=(138, 145, 160), anchor="rm")
    return img.resize((w, h), Image.Resampling.LANCZOS)
