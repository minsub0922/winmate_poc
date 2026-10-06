"""PDF — pypdfium2(쪽 글자 · 문서 속성 · 목차 · 그림 추출 · 스캔 판별) + pdfplumber(단어 위치 · 글자 크기 · 표).

- 쪽 text 는 pypdfium2(내용 스트림 순서, CJK 에 강함). 인용 대조는 이 글자로 한다.
- blocks 는 pdfplumber 단어 → 줄 → 블록, XY-cut 으로 읽는 순서. 글자 크기로 제목(heading) 수준을 정한다.
  pdfplumber 로 읽지 않는 쪽(상한 초과 · 깨진 글꼴)은 pypdfium2 글자 사각형으로 줄 블록을 만든다.
- 글자 층이 없는(또는 거의 없는) 쪽은 warnings 에 `scanned_page:<n>` — 호출 측이 쪽 이미지를 i2t 로 읽는다.
"""
from __future__ import annotations

import io
import logging
from collections import Counter
from typing import Any

import pypdfium2.raw as pdfium_c

from .. import pdfium
from ..textutil import clean, is_bullet, is_caption
from .common import Doc, ParseContext, ParseError, heading_levels, norm_bbox, table_text

log = logging.getLogger("winmate.files.pdf")

MIN_IMG_PX = 48
MIN_IMG_AREA = 0.012      # 쪽 넓이 대비
MAX_IMGS_PER_PAGE = 30
MAX_CHARS_FOR_LAYOUT = 25_000
MAX_OBJECTS_FOR_LAYOUT = 20_000   # 도면(CAD) 같은 쪽은 pdfminer 가 수 분 걸릴 수 있다 → 글자 사각형 블록
MAX_OBJECTS_FOR_TABLES = 4_000    # 선이 아주 많은 쪽은 표 찾기를 건너뛴다
_BOLD = ("bold", "black", "heavy", "-bd", "extrabold", "semibold", "demibold")


# ── pypdfium2 단계 ────────────────────────────────────────────

def _to_display(l: float, b: float, r: float, t: float, rot: int, crop: tuple[float, ...]) -> list[float] | None:
    """PDF 좌표(왼쪽 아래 원점, 회전 전) → 화면 좌표 0..1(왼쪽 위 원점, /Rotate 반영)."""
    cx0, cy0, cx1, cy1 = crop
    mw, mh = cx1 - cx0, cy1 - cy0
    x0, x1 = l - cx0, r - cx0
    y0, y1 = b - cy0, t - cy0
    rot = rot % 360
    if rot == 90:
        return norm_bbox(y0, x0, y1, x1, mh, mw)
    if rot == 180:
        return norm_bbox(mw - x1, y0, mw - x0, y1, mw, mh)
    if rot == 270:
        return norm_bbox(mh - y1, mw - x1, mh - y0, mw - x0, mh, mw)
    return norm_bbox(x0, mh - y1, x1, mh - y0, mw, mh)


def _segments(textpage: Any, rot: int, crop: tuple[float, ...]) -> list[dict[str, Any]]:
    """pypdfium2 글자 사각형 → 줄 블록(대체 경로, 글자 크기 없음)."""
    segs = []
    try:
        n = textpage.count_rects()
    except Exception:  # noqa: BLE001
        return []
    for i in range(min(n, 4000)):
        l, b, r, t = textpage.get_rect(i)
        txt = clean(textpage.get_text_bounded(l, b, r, t))
        if txt:
            segs.append({"text": txt.replace("\n", " "), "bbox": _to_display(l, b, r, t, rot, crop) or [0.0, 0.0, 0.0, 0.0]})
    lines: list[dict[str, Any]] = []
    for seg in sorted(segs, key=lambda s: (s["bbox"][1], s["bbox"][0])):
        bb = seg["bbox"]
        if lines:
            lb = lines[-1]["bbox"]
            overlap = min(lb[3], bb[3]) - max(lb[1], bb[1])
            if overlap > 0.5 * min(lb[3] - lb[1], bb[3] - bb[1]) and -0.01 <= bb[0] - lb[2] < 0.05:
                lines[-1]["text"] += " " + seg["text"]
                lines[-1]["bbox"] = [min(lb[0], bb[0]), min(lb[1], bb[1]), max(lb[2], bb[2]), max(lb[3], bb[3])]
                continue
        lines.append(dict(seg))
    return [{"type": "list" if is_bullet(ln["text"]) else "body", "text": ln["text"], "bbox": ln["bbox"]} for ln in lines]


def _extract_image(obj: Any) -> tuple[bytes, str, str] | None:
    buf = io.BytesIO()
    try:
        obj.extract(buf, fb_format="png")
        data = buf.getvalue()
    except Exception:  # noqa: BLE001
        data = b""
    if not data:
        try:
            bitmap = obj.get_bitmap(render=False)
            try:
                pil = bitmap.to_pil().copy()
            finally:
                bitmap.close()  # 잠금 안에서 닫는다(GC 가 다른 스레드에서 닫지 않게)
            out = io.BytesIO()
            pil.save(out, "PNG")
            data = out.getvalue()
        except Exception:  # noqa: BLE001
            return None
    if data[:3] == b"\xff\xd8\xff":
        return data, "jpg", "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return data, "png", "image/png"
    try:  # JPEG 2000 · TIFF 등 → PNG
        from PIL import Image

        out = io.BytesIO()
        Image.open(io.BytesIO(data)).save(out, "PNG")
        return out.getvalue(), "png", "image/png"
    except Exception:  # noqa: BLE001
        return None


def _pdfium_pass(data: bytes, doc: Doc, ctx: ParseContext) -> list[dict[str, Any]]:
    """쪽마다 {no, w, h, text, chars, scanned, segments, images}. 문서 속성 · 목차는 doc.meta 로."""
    pages: list[dict[str, Any]] = []
    # PDFium 은 전역 잠금 안에서만 부른다. 쪽마다 잠금을 풀어 다른 파일 미리보기가 오래 기다리지 않게 한다
    with pdfium.LOCK:
        try:
            pdf = pdfium.open_pdf(ctx.src_path or data)
        except pdfium.EncryptedPdf as exc:
            raise ParseError("FILE_ENCRYPTED", "암호가 걸린 PDF 라 읽을 수 없어요") from exc
        except Exception as exc:  # noqa: BLE001
            raise ParseError("PARSE_FAILED", f"PDF 를 열 수 없어요: {exc}") from exc
    try:
        with pdfium.LOCK:
            props = pdfium.props_from_metadata(pdf.get_metadata_dict(skip_empty=True))
            doc.meta.update({k: v for k, v in props.items() if v})
            try:
                outline = []
                for bm in pdf.get_toc(max_depth=4):
                    if len(outline) >= 300:
                        break
                    dest = bm.get_dest()
                    idx = dest.get_index() if dest is not None else None
                    title = clean(bm.get_title())
                    if title:
                        outline.append({"level": int(bm.level) + 1, "title": title[:200],
                                        "page": (idx + 1) if isinstance(idx, int) and idx >= 0 else None})
                if outline:
                    doc.meta["outline"] = outline
            except Exception:  # noqa: BLE001
                pass
            n = len(pdf)
        for i in range(n):
            no = i + 1
            info: dict[str, Any] = {"no": no, "w": 0.0, "h": 0.0, "text": "", "chars": 0, "scanned": False,
                                    "segments": [], "images": []}
            pages.append(info)
            with pdfium.LOCK:
                try:
                    page = pdf[i]
                except Exception as exc:  # noqa: BLE001
                    doc.warn(f"page_error:{no}")
                    log.info("page %s open failed: %s", no, exc)
                    continue
                try:
                    _read_page(page, info, doc)
                except Exception as exc:  # noqa: BLE001
                    doc.warn(f"page_error:{no}")
                    log.info("page %s read failed: %s", no, exc)
                finally:
                    page.close()
    finally:
        with pdfium.LOCK:
            pdf.close()
    return pages


def _read_page(page: Any, info: dict[str, Any], doc: Doc) -> None:
    no = info["no"]
    w, h = page.get_size()
    rot = page.get_rotation() or 0
    try:
        crop = tuple(page.get_cropbox())
    except Exception:  # noqa: BLE001
        crop = (0.0, 0.0, w, h) if rot % 180 == 0 else (0.0, 0.0, h, w)
    info.update({"w": w, "h": h})
    tp = page.get_textpage()
    try:
        info["text"] = clean(tp.get_text_range())
        info["chars"] = tp.count_chars()
        if 0 < info["chars"] < 60_000:
            info["segments"] = _segments(tp, rot, crop)
    finally:
        tp.close()
    page_area = max(w * h, 1.0)
    n_objects = pdfium_c.FPDFPage_CountObjects(page.raw)
    # 폼 XObject 안까지 센다(도면은 폼 하나에 수만 개가 들어 있기도 하다). 상한에서 멈춘다
    nested = 0
    for _obj in page.get_objects(max_depth=3):
        nested += 1
        if nested > MAX_OBJECTS_FOR_LAYOUT:
            break
    info["objects"] = max(n_objects, nested)
    boxes = []
    coverage = 0.0
    for obj in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE], max_depth=3):
        try:
            l, b, r, t = obj.get_bounds()
        except Exception:  # noqa: BLE001
            continue
        frac = min(1.0, max(0.0, r - l) * max(0.0, t - b) / page_area)
        coverage = max(coverage, frac)
        boxes.append((obj, (l, b, r, t), frac))
    text_len = len("".join(info["text"].split()))
    scanned = (text_len == 0 and n_objects > 0) or (text_len < 20 and coverage > 0.4)
    info["scanned"] = scanned
    if scanned:
        doc.warn(f"scanned_page:{no}")
    taken = 0
    for obj, (l, b, r, t), frac in boxes:
        if taken >= MAX_IMGS_PER_PAGE:
            break
        if frac < MIN_IMG_AREA or (scanned and frac > 0.6):
            continue
        try:
            pw, ph = obj.get_px_size()
        except Exception:  # noqa: BLE001
            continue
        if pw < MIN_IMG_PX or ph < MIN_IMG_PX:
            continue
        bbox = _to_display(l, b, r, t, rot, crop)
        ref = None
        if doc.ctx.extract_children:
            blob = _extract_image(obj)
            if blob:
                data_bytes, ext, mime = blob
                ref = doc.add_child(data_bytes, f"p{no}_image{taken + 1}.{ext}", mime, {"from": "pdf", "px": [pw, ph]}, page=no)
        else:
            doc.skip_child()
        info["images"].append({"bbox": bbox, "ref": ref})
        taken += 1


# ── pdfplumber 단계 ───────────────────────────────────────────

class _Blk:
    __slots__ = ("x0", "top", "x1", "bottom", "lines", "size", "bold", "kind", "rows", "image")

    def __init__(self, x0: float, top: float, x1: float, bottom: float, kind: str = "text"):
        self.x0, self.top, self.x1, self.bottom = x0, top, x1, bottom
        self.lines: list[str] = []
        self.size = 0.0
        self.bold = False
        self.kind = kind          # text | list | table | image
        self.rows: list[list[str]] | None = None
        self.image: dict[str, Any] | None = None


def _is_bold(fontname: str | None) -> bool:
    f = (fontname or "").lower()
    return any(k in f for k in _BOLD)


def _clean_cell(v: Any) -> str:
    if v is None:
        return ""
    return " ".join(clean(str(v)).split())


def _layout_page(pl_page: Any, *, find_tables: bool = True) -> tuple[list[_Blk], list[list[list[str]]], list[tuple[float, int]], bool]:
    """(블록, 표, (글자 크기, 글자 수) 목록, 글자 깨짐 여부)."""
    tables: list[list[list[str]]] = []
    table_blocks: list[_Blk] = []
    try:
        found = pl_page.find_tables() if find_tables else []
    except Exception:  # noqa: BLE001
        found = []
    for t in found:
        try:
            rows = [[_clean_cell(c) for c in row] for row in t.extract()]
        except Exception:  # noqa: BLE001
            continue
        rows = [r for r in rows if any(c for c in r)]
        if len(rows) < 2 or max((len(r) for r in rows), default=0) < 2:
            continue  # 글상자 테두리 같은 1×n 은 표로 보지 않는다
        blk = _Blk(*t.bbox, kind="table")
        blk.rows = rows
        tables.append(rows)
        table_blocks.append(blk)
    words = pl_page.extract_words(keep_blank_chars=False, use_text_flow=False, extra_attrs=["size", "fontname"],
                                  x_tolerance=1.5, y_tolerance=2.5)
    if not words:
        return table_blocks, tables, [], False
    garbled = sum(1 for w in words if "(cid:" in w["text"])
    if garbled > max(3, len(words) * 0.1):
        return table_blocks, tables, [], True

    def in_table(w: dict[str, Any]) -> bool:
        cx, cy = (w["x0"] + w["x1"]) / 2, (w["top"] + w["bottom"]) / 2
        return any(b.x0 - 1 <= cx <= b.x1 + 1 and b.top - 1 <= cy <= b.bottom + 1 for b in table_blocks)

    words = [w for w in words if not in_table(w)]
    sizes = [(round(float(w.get("size") or 0), 1), len(w["text"])) for w in words]
    # 줄: 위치가 가까운 단어끼리. 단어 사이가 크게 벌어지면(단 · 표 칸) 다른 줄
    words.sort(key=lambda w: (round(w["top"] / 2), w["x0"]))
    lines: list[dict[str, Any]] = []
    for w in words:
        size = float(w.get("size") or 0) or (w["bottom"] - w["top"])
        ln = lines[-1] if lines else None
        if (ln is not None and abs(ln["top"] - w["top"]) <= max(2.0, 0.45 * min(ln["size"], size))
                and 0 <= w["x0"] - ln["x1"] <= max(3.0 * size, 12)):
            ln["words"].append(w)
            ln["x1"] = max(ln["x1"], w["x1"])
            ln["bottom"] = max(ln["bottom"], w["bottom"])
            ln["size"] = max(ln["size"], size)
            continue
        lines.append({"x0": w["x0"], "x1": w["x1"], "top": w["top"], "bottom": w["bottom"], "size": size, "words": [w]})
    # 블록: 세로로 이어지고 가로로 겹치고 글자 크기 · 굵기가 같은 줄끼리. 글머리 줄은 목록 블록에만 붙는다
    blocks: list[_Blk] = []
    open_blocks: list[_Blk] = []
    for ln in sorted(lines, key=lambda x: (x["top"], x["x0"])):
        text = " ".join(w["text"] for w in ln["words"]).strip()
        if not text:
            continue
        bold = all(_is_bold(w.get("fontname")) for w in ln["words"])
        bullet = is_bullet(text)
        target = None
        for b in reversed(open_blocks):
            gap = ln["top"] - b.bottom
            overlap = min(b.x1, ln["x1"]) - max(b.x0, ln["x0"])
            similar = b.size > 0 and 0.85 <= ln["size"] / b.size <= 1.18
            if not (-2 <= gap <= 0.9 * ln["size"] and overlap > 0 and similar and b.bold == bold):
                continue
            if bullet and b.kind != "list":
                continue
            target = b
            break
        if target is None:
            target = _Blk(ln["x0"], ln["top"], ln["x1"], ln["bottom"], kind="list" if bullet else "text")
            target.size = ln["size"]
            target.bold = bold
            blocks.append(target)
            open_blocks.append(target)
            open_blocks = [b for b in open_blocks if ln["top"] - b.bottom < 3 * ln["size"]][-12:]
        target.lines.append(text)
        target.x0, target.x1 = min(target.x0, ln["x0"]), max(target.x1, ln["x1"])
        target.bottom = max(target.bottom, ln["bottom"])
    return blocks + table_blocks, tables, sizes, False


def _xy_cut(blocks: list[_Blk], depth: int = 0) -> list[_Blk]:
    """읽는 순서: 세로 단(양쪽 블록 2개 이상) → 가로 띠 순으로 자른다."""
    if len(blocks) <= 1 or depth > 40:
        return blocks
    for axis in ("x", "y"):
        if axis == "x":
            bs = sorted(blocks, key=lambda b: b.x0)
            lo, hi = (lambda b: b.x0), (lambda b: b.x1)
        else:
            bs = sorted(blocks, key=lambda b: b.top)
            lo, hi = (lambda b: b.top), (lambda b: b.bottom)
        groups: list[list[_Blk]] = [[bs[0]]]
        edge = hi(bs[0])
        for b in bs[1:]:
            if lo(b) >= edge - 0.5:
                groups.append([b])
                edge = hi(b)
            else:
                groups[-1].append(b)
                edge = max(edge, hi(b))
        if len(groups) > 1:
            if axis == "x" and min(len(g) for g in groups) < 2:
                continue  # 옆 주석 · 그림 하나로 단을 나누지 않는다
            out: list[_Blk] = []
            for g in groups:
                out.extend(_xy_cut(g, depth + 1))
            return out
    return sorted(blocks, key=lambda b: (round(b.top), b.x0))


def _layout_pass(data: bytes, pages: list[dict[str, Any]], doc: Doc, ctx: ParseContext) -> tuple[dict[int, Any], Counter[float]]:
    layout: dict[int, Any] = {}
    sizes: Counter[float] = Counter()
    limit = min(len(pages), ctx.pdf_layout_max_pages)
    if len(pages) > ctx.pdf_layout_max_pages:
        doc.warn(f"layout_skipped_after:{ctx.pdf_layout_max_pages}")
    if not limit or not any(p["chars"] for p in pages[:limit]):
        return layout, sizes
    try:
        import pdfplumber

        pl = pdfplumber.open(str(ctx.src_path) if ctx.src_path else io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        doc.warn("layout_unavailable")
        log.info("pdfplumber open failed: %s", exc)
        return layout, sizes
    try:
        for i in range(limit):
            info = pages[i]
            if not info["chars"] or info["scanned"] or info["chars"] > MAX_CHARS_FOR_LAYOUT:
                continue
            if info.get("objects", 0) > MAX_OBJECTS_FOR_LAYOUT:
                doc.warn(f"layout_skipped:{i + 1}:complex")
                continue
            try:
                pl_page = pl.pages[i]
                with_tables = info.get("objects", 0) <= MAX_OBJECTS_FOR_TABLES
                if not with_tables:
                    doc.warn(f"tables_skipped:{i + 1}:complex")
                blocks, tables, page_sizes, garbled = _layout_page(pl_page, find_tables=with_tables)
                if garbled:
                    doc.warn(f"layout_fallback:{i + 1}")
                    blocks = [b for b in blocks if b.kind == "table"]
                    info["use_segments"] = True
                layout[i] = (blocks, tables, float(pl_page.width), float(pl_page.height))
                for s, n in page_sizes:
                    if s > 0:
                        sizes[s] += n
                try:
                    pl_page.close()
                except Exception:  # noqa: BLE001
                    pass
            except Exception as exc:  # noqa: BLE001
                doc.warn(f"layout_error:{i + 1}")
                log.info("layout page %s failed: %s", i + 1, exc)
    finally:
        try:
            pl.close()
        except Exception:  # noqa: BLE001
            pass
    return layout, sizes


def _image_block(im: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    blk: dict[str, Any] = {"type": "image", "text": "", "bbox": im["bbox"]}
    if im["ref"]:
        blk["ref"] = im["ref"]
        page["image_refs"].append(im["ref"])
        page["images"].append({"ref": im["ref"], "bbox": im["bbox"]})
    return blk


def parse_pdf(data: bytes, ctx: ParseContext) -> dict[str, Any]:
    doc = Doc("pdf", ctx)
    pages = _pdfium_pass(data, doc, ctx)
    layout, sizes = _layout_pass(data, pages, doc, ctx)
    body_size = sizes.most_common(1)[0][0] if sizes else 10.0
    block_sizes = [round(b.size, 1) for blocks, *_ in layout.values() for b in blocks if b.kind != "table"]
    levels = heading_levels(block_sizes, body_size)
    bold_level = (max(levels.values()) + 1) if levels else 1

    for i, info in enumerate(pages):
        no = info["no"]
        w, h = info["w"], info["h"]
        page = doc.page(no, text=info["text"], size=[round(w, 2), round(h, 2)] if w and h else None)
        out: list[dict[str, Any]] = []
        placed_images = False
        if i in layout:
            blocks, tables, pw, ph = layout[i]
            page["tables"] = tables
            img_blocks = []
            for im in info["images"]:
                bb = im["bbox"]
                if not bb:
                    continue
                ib = _Blk(bb[0] * pw, bb[1] * ph, bb[2] * pw, bb[3] * ph, kind="image")
                ib.image = im
                img_blocks.append(ib)
            placed_images = len(img_blocks) == len(info["images"])
            for b in _xy_cut(list(blocks) + (img_blocks if placed_images else [])):
                bbox = norm_bbox(b.x0, b.top, b.x1, b.bottom, pw, ph)
                if b.kind == "image" and b.image is not None:
                    out.append(_image_block(b.image, page))
                    continue
                if b.kind == "table":
                    out.append({"type": "table", "text": table_text(b.rows or []), "bbox": bbox})
                    continue
                text = ("\n" if b.kind == "list" else " ").join(b.lines).strip()
                if not text:
                    continue
                size = round(b.size, 1)
                entry: dict[str, Any] = {"type": "body", "text": text, "bbox": bbox, "font_size": size or None}
                short = len(b.lines) <= 3 and len(text) <= 200
                if size in levels and short:
                    entry.update(type="heading", level=levels[size])
                elif (b.bold and len(b.lines) == 1 and len(text) <= 80 and size >= body_size * 0.95
                      and not text.endswith((".", "다", "요")) and b.kind != "list"):
                    entry.update(type="heading", level=bold_level)
                elif b.kind == "list":
                    entry["type"] = "list"
                elif is_caption(text):
                    entry["type"] = "caption"
                out.append(entry)
            if info.get("use_segments"):
                out = out + info["segments"]
        else:
            out = list(info["segments"])
        if not placed_images:
            for im in info["images"]:
                out.append(_image_block(im, page))
        if info["scanned"] and not any(b["type"] != "image" for b in out):
            out.insert(0, {"type": "image", "text": "", "bbox": [0.0, 0.0, 1.0, 1.0]})
        if no == 1 and doc.title is None:
            heads = [b for b in out if b["type"] == "heading" and b.get("level") == 1]
            if heads:
                heads[0]["type"] = "title"
                doc.title = heads[0]["text"][:300]
        for b in out:
            if b["type"] in ("title", "heading") and b.get("bbox") and b["bbox"][1] <= 0.4:
                page["title"] = b["text"][:200]
                break
        if not page["text"]:
            page["text"] = "\n".join(b["text"] for b in out if b["text"])
        page["blocks"] = out
    doc.title = doc.meta.get("title") or doc.title
    if sizes:
        doc.meta["body_font_size"] = body_size
    return doc.finish()
