"""이미지 바이너리: 썸네일 묶음(WTHB) · 원본 로컬 사본 · 원본 메타.

- 썸네일: `winmate-kb/dashboard/build/thumbs_pack*.bin` — b'WTHB' + uint32 머리 길이 + JSON 머리
  `[[hash, w, h, w0, h0, len], ...]` + webp 바이트를 이어 붙인 것. hash = fnv36(curation.img_key(asset.url or url_mobile)).
  w·h 는 썸네일 크기, w0·h0 는 썸네일을 만들 때 브라우저가 읽은 원본 크기다(→ 원본 가로·세로, G-IMG-1 일부).
- 원본 로컬 사본: `WKB_IMAGE_DIR/<asset_id>.(webp|jpg|jpeg|png)` (scripts/kb_fetch_images.py 가 채운다). 없으면 썸네일.
- 원본 메타 사이드카: `WKB_IMAGE_DIR/_originals.json` — {"images": {asset_id: {"original": {...}, "stored": {...}}}}.
"""
from __future__ import annotations

import json
import logging
import mmap
import re
import struct
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config, curation
from .engine import engine, q

log = logging.getLogger("winmate.kb.images")

_EXT_FORMAT = {"jpg": "JPG", "jpeg": "JPG", "png": "PNG", "webp": "WEBP", "gif": "GIF", "svg": "SVG", "avif": "AVIF", "mp4": "MP4"}
LOCAL_EXTS = ("webp", "jpg", "jpeg", "png")
MEDIA = {"webp": "image/webp", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}


def fnv36(s: str) -> str:
    h = 0x811c9dc5
    for b in s.encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xffffffff
    a, o = "0123456789abcdefghijklmnopqrstuvwxyz", ""
    while True:
        h, r = divmod(h, 36)
        o = a[r] + o
        if not h:
            return o


def format_of_url(url: str | None) -> str | None:
    if not url:
        return None
    m = re.search(r"\.([A-Za-z0-9]{3,4})(?:$|[?#$])", url.split("?")[0])
    return _EXT_FORMAT.get(m.group(1).lower()) if m else None


@dataclass(frozen=True)
class ThumbEntry:
    pack: int
    offset: int
    length: int
    width: int
    height: int
    orig_width: int
    orig_height: int


class Thumbs:
    def __init__(self) -> None:
        self.dir = config.thumbs_dir()
        self.packs: list[mmap.mmap] = []
        self.files: list[Path] = []
        by_hash: dict[str, ThumbEntry] = {}
        for pf in sorted(self.dir.glob("thumbs_pack*.bin")):
            with open(pf, "rb") as f:
                mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            if mm[:4] != b"WTHB":
                log.warning("WTHB 형식이 아니다: %s", pf)
                continue
            hl = struct.unpack("<I", mm[4:8])[0]
            head = json.loads(mm[8:8 + hl])
            off = 8 + hl
            idx = len(self.packs)
            for h, w, hh, w0, h0, ln in head:
                by_hash.setdefault(h, ThumbEntry(idx, off, ln, int(w), int(hh), int(w0 or 0), int(h0 or 0)))
                off += ln
            self.packs.append(mm)
            self.files.append(pf)
        self.by_hash = by_hash
        C = engine().C
        self.by_asset: dict[str, ThumbEntry] = {}
        for r in q("SELECT id, url, url_mobile FROM image_asset"):
            key = C.img_key(r["url"] or r["url_mobile"]) or ""
            e = by_hash.get(fnv36(key))
            if e is not None:
                self.by_asset[r["id"]] = e
        log.info("thumbs: %d packs, %d hashes, %d / assets", len(self.packs), len(by_hash), len(self.by_asset))

    def get(self, asset_id: str) -> ThumbEntry | None:
        return self.by_asset.get(asset_id)

    def data(self, e: ThumbEntry) -> bytes:
        return self.packs[e.pack][e.offset:e.offset + e.length]


_thumbs: Thumbs | None = None
_lock = threading.Lock()


def thumbs() -> Thumbs:
    global _thumbs
    if _thumbs is None:
        with _lock:
            if _thumbs is None:
                _thumbs = Thumbs()
    return _thumbs


# ── 로컬 원본 사본 ───────────────────────────────────────

def local_file(asset_id: str) -> Path | None:
    d = config.image_dir()
    for ext in LOCAL_EXTS:
        p = d / f"{asset_id}.{ext}"
        if p.is_file():
            return p
    return None


_dims_cache: dict[tuple[str, float], dict[str, Any]] = {}


def file_dims(p: Path) -> dict[str, Any] | None:
    try:
        st = p.stat()
    except OSError:
        return None
    key = (str(p), st.st_mtime)
    hit = _dims_cache.get(key)
    if hit is not None:
        return hit
    try:
        from PIL import Image

        with Image.open(p) as im:
            w, h = im.size
            fmt = (im.format or p.suffix.lstrip(".")).upper()
    except Exception:  # noqa: BLE001 — 깨진 파일은 메타 없음
        return None
    out = {"width": int(w), "height": int(h), "format": "JPG" if fmt == "JPEG" else fmt, "bytes": int(st.st_size)}
    _dims_cache[key] = out
    return out


_sidecar: tuple[float, dict[str, Any]] | None = None


def sidecar() -> dict[str, Any]:
    """kb_fetch_images.py 가 남긴 원본 메타(있을 때만)."""
    global _sidecar
    p = config.image_meta_path()
    try:
        mt = p.stat().st_mtime
    except OSError:
        return {}
    if _sidecar is None or _sidecar[0] != mt:
        try:
            data = json.loads(p.read_text(encoding="utf-8")).get("images") or {}
        except Exception:  # noqa: BLE001
            data = {}
        _sidecar = (mt, data)
    return _sidecar[1]


def samples() -> dict[str, dict[str, Any]]:
    return {x["asset_id"]: x for x in (curation.load("image_samples").get("images") or [])}


def original_dims(asset_id: str, url: str | None) -> dict[str, Any] | None:
    """원본 메타(G-IMG-1): 사이드카(내려받은 원본) → 보드 표본 → 썸네일을 만들 때 잰 원본 크기(용량 없음)."""
    sc = sidecar().get(asset_id) or {}
    o = sc.get("original")
    if o and o.get("width"):
        return {"width": int(o["width"]), "height": int(o["height"]), "format": o.get("format") or format_of_url(url),
                "bytes": o.get("bytes"), "basis": "download"}
    s = samples().get(asset_id)
    if s and s.get("original"):
        o = s["original"]
        return {"width": int(o["width"]), "height": int(o["height"]), "format": o.get("format"), "bytes": o.get("bytes"),
                "basis": "board_sample"}
    e = thumbs().get(asset_id)
    if e and e.orig_width:
        return {"width": e.orig_width, "height": e.orig_height, "format": format_of_url(url), "bytes": None,
                "basis": "browser_probe"}
    return None


def stored_dims(asset_id: str) -> dict[str, Any] | None:
    """저장본(G-IMG-2) = 화면에 실제로 주는 로컬 사본. 원본 사본이 없으면 썸네일."""
    p = local_file(asset_id)
    if p is not None:
        d = file_dims(p)
        if d:
            return {**d, "basis": "local_file"}
    e = thumbs().get(asset_id)
    if e:
        return {"width": e.width, "height": e.height, "format": "WEBP", "bytes": e.length, "basis": "thumbnail"}
    return None


def has_local(asset_id: str) -> bool:
    return thumbs().get(asset_id) is not None or local_file(asset_id) is not None


def thumb_bytes(asset_id: str) -> bytes | None:
    t = thumbs()
    e = t.get(asset_id)
    return t.data(e) if e else None


def file_bytes(asset_id: str) -> tuple[bytes, str] | None:
    """원본 사본이 있으면 그것, 없으면 썸네일(webp)."""
    p = local_file(asset_id)
    if p is not None:
        try:
            return p.read_bytes(), MEDIA.get(p.suffix.lstrip(".").lower(), "application/octet-stream")
        except OSError:
            pass
    b = thumb_bytes(asset_id)
    return (b, "image/webp") if b is not None else None


def local_count() -> int:
    d = config.image_dir()
    if not d.is_dir():
        return 0
    return sum(1 for p in d.iterdir() if p.suffix.lstrip(".").lower() in LOCAL_EXTS)
