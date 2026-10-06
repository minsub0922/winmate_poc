"""텍스트류 — TXT · MD · CSV/TSV · JSON · HTML · XML · YAML. 인코딩 판별(utf-8 · cp949/euc-kr · utf-16).

블록에는 시작 줄 번호(line)를 붙인다(출처 표기 `줄 12`). 긴 글은 약 50,000자마다 쪽을 나눈다.
CSV/TSV 는 sheets 로도 준다.
"""
from __future__ import annotations

import csv
import io
import re
from typing import Any

from ..textutil import clean, decode_text, first_line, is_bullet
from .common import Doc, ParseContext, table_text

PAGE_CHARS = 50_000
MAX_ROWS = 2000
_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_MD_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def _paragraphs(lines: list[str]) -> list[tuple[int, list[str]]]:
    """빈 줄로 나눈 문단: (시작 줄 번호, 줄들)."""
    out: list[tuple[int, list[str]]] = []
    cur: list[str] = []
    start = 0
    for i, line in enumerate(lines, start=1):
        if line.strip():
            if not cur:
                start = i
            cur.append(line.rstrip())
        elif cur:
            out.append((start, cur))
            cur = []
    if cur:
        out.append((start, cur))
    return out


def _plain_blocks(lines: list[str]) -> list[dict[str, Any]]:
    blocks = []
    for start, para in _paragraphs(lines):
        text = clean("\n".join(para))
        if not text:
            continue
        bullets = sum(1 for ln in para if is_bullet(ln))
        kind = "list" if bullets and bullets >= len(para) / 2 else "body"
        blocks.append({"type": kind, "text": text, "line": start})
    return blocks


def _md_blocks(lines: list[str]) -> tuple[list[dict[str, Any]], list[list[list[str]]]]:
    blocks: list[dict[str, Any]] = []
    tables: list[list[list[str]]] = []
    i = 0
    in_code = False
    buf: list[str] = []
    buf_start = 0

    def flush() -> None:
        nonlocal buf
        if buf:
            text = clean("\n".join(buf))
            if text:
                bullets = sum(1 for ln in buf if is_bullet(ln))
                blocks.append({"type": "list" if bullets and bullets >= len(buf) / 2 else "body", "text": text, "line": buf_start})
        buf = []

    while i < len(lines):
        line = lines[i]
        no = i + 1
        if line.strip().startswith("```"):
            if in_code:
                buf.append(line)
                flush()
                in_code = False
            else:
                flush()
                in_code = True
                buf_start = no
                buf.append(line)
            i += 1
            continue
        if in_code:
            buf.append(line)
            i += 1
            continue
        m = _MD_HEADING.match(line)
        if m:
            flush()
            level = len(m.group(1))
            blocks.append({"type": "title" if level == 1 and not any(b["type"] == "title" for b in blocks) else "heading",
                           "text": clean(m.group(2)), "level": level, "line": no})
            i += 1
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and _MD_TABLE_SEP.match(lines[i + 1]):
            flush()
            rows = []
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                if not _MD_TABLE_SEP.match(lines[j]):
                    rows.append([clean(c) for c in lines[j].strip().strip("|").split("|")])
                j += 1
            tables.append(rows)
            blocks.append({"type": "table", "text": table_text(rows), "line": no})
            i = j
            continue
        if not line.strip():
            flush()
        else:
            if not buf:
                buf_start = no
            buf.append(line)
        i += 1
    flush()
    return blocks, tables


def _csv_rows(text: str, fmt: str) -> list[list[str]]:
    delim = "\t" if fmt == "tsv" else ","
    if fmt not in ("tsv",):
        try:
            delim = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            delim = ","
    rows = []
    for r_i, row in enumerate(csv.reader(io.StringIO(text), delimiter=delim)):
        if r_i >= MAX_ROWS + 1:
            break
        rows.append([c.strip() for c in row])
    return rows


def _html(text: str) -> tuple[str | None, list[dict[str, Any]], list[list[list[str]]], str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(text, "lxml")
    for t in soup(["script", "style", "noscript", "template"]):
        t.decompose()
    title = clean(soup.title.get_text()) if soup.title else None
    blocks: list[dict[str, Any]] = []
    tables: list[list[list[str]]] = []
    root = soup.body or soup
    for el in root.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "table", "pre", "blockquote", "figcaption"]):
        if el.find_parent(["table"]) is not None and el.name != "table":
            continue
        if el.name in ("p", "li") and el.find_parent(["li"]) is not None and el.name == "p":
            continue
        if el.name == "table":
            rows = []
            for tr in el.find_all("tr"):
                cells = [" ".join(clean(td.get_text(" ")).split()) for td in tr.find_all(["td", "th"])]
                if any(cells):
                    rows.append(cells)
            if rows:
                tables.append(rows)
                blocks.append({"type": "table", "text": table_text(rows)})
            continue
        t = clean(el.get_text(" "))
        if not t:
            continue
        if el.name.startswith("h"):
            blocks.append({"type": "heading", "text": t, "level": int(el.name[1])})
        elif el.name == "li":
            blocks.append({"type": "list", "text": t})
        elif el.name == "figcaption":
            blocks.append({"type": "caption", "text": t})
        else:
            blocks.append({"type": "body", "text": t})
    full = clean(root.get_text("\n"))
    return title, blocks, tables, full


def parse_text(data: bytes, ctx: ParseContext) -> dict[str, Any]:
    doc = Doc("text", ctx)
    raw, enc = decode_text(data)
    doc.meta["encoding"] = enc
    if enc == "latin-1":
        doc.warn("encoding_guess:latin-1")
    fmt = ctx.fmt
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    tables: list[list[list[str]]] = []
    title: str | None = None
    if fmt == "html":
        title, blocks, tables, full = _html(normalized)
        text = full
    elif fmt == "md":
        blocks, tables = _md_blocks(lines)
        text = clean(normalized)
        title = next((b["text"] for b in blocks if b["type"] == "title"), None)
    elif fmt in ("csv", "tsv"):
        rows = _csv_rows(normalized, fmt)
        truncated = len(rows) > MAX_ROWS
        rows = rows[:MAX_ROWS]
        ncols = max((len(r) for r in rows), default=0)
        from openpyxl.utils import get_column_letter

        doc.sheets = [{"name": ctx.name.rsplit(".", 1)[0][:100] or "sheet", "rows": rows,
                       "dims": f"A1:{get_column_letter(ncols)}{len(rows)}" if rows and ncols else None,
                       "merged": [], "hidden": False, "row_count": len(rows), "truncated": truncated}]
        if truncated:
            doc.warn(f"rows_truncated:{MAX_ROWS}")
        blocks = [{"type": "table", "text": table_text(rows[:200]), "line": 1}] if rows else []
        text = clean(normalized)
    elif fmt in ("json", "xml", "yaml"):
        text = clean(normalized)
        blocks = [{"type": "body", "text": text[:20_000], "line": 1}] if text else []
    else:
        blocks = _plain_blocks(lines)
        text = clean(normalized)
    # 쪽 나누기(긴 글)
    if len(text) <= PAGE_CHARS or fmt in ("csv", "tsv", "json", "xml", "yaml"):
        page = doc.page(1, text=text, blocks=blocks, tables=tables)
    else:
        page = None
        cur_blocks: list[dict[str, Any]] = []
        size = 0
        for b in blocks:
            if cur_blocks and size + len(b["text"]) > PAGE_CHARS:
                doc.page(len(doc.pages) + 1, text="\n\n".join(x["text"] for x in cur_blocks), blocks=cur_blocks)
                cur_blocks, size = [], 0
            cur_blocks.append(b)
            size += len(b["text"]) + 2
        if cur_blocks or not doc.pages:
            doc.page(len(doc.pages) + 1, text="\n\n".join(x["text"] for x in cur_blocks), blocks=cur_blocks)
        if tables:
            doc.pages[0]["tables"] = tables
    if page is not None and fmt == "html":
        page["title"] = title
    doc.title = title or first_line(text, 120)
    return doc.finish()
