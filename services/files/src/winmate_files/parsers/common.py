"""파서 공통 — 레코드와 무관한 파싱 결과(Doc)와 자식 바이너리(Child).

파서는 file id 를 모른다. 이미지 · 첨부는 내용 sha256(ref)으로 가리키고, 서비스가 레코드마다
자식 파일을 만든 뒤 ref → file id 로 바꾼다(materialize).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..textutil import clean

TEXT_LIMIT = 500_000
PAGE_TEXT_LIMIT = 100_000
MIN_CHILD_PX = 24


class ParseError(Exception):
    """파일이 깨졌거나 읽을 수 없다(422)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class Unsupported(Exception):
    """이 형식은 파싱하지 않는다(415)."""


@dataclass
class Child:
    key: str
    data: bytes
    name: str
    mime: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParseContext:
    name: str
    fmt: str
    extract_children: bool = True
    max_children: int = 300
    pdf_layout_max_pages: int = 300
    src_path: Path | None = None
    # LibreOffice 변환(없으면 None): (원본 바이트, 이름, 목표 확장자) → 바이트 | None
    convert: Callable[[bytes, str, str], bytes | None] | None = None


class Doc:
    def __init__(self, kind: str, ctx: ParseContext):
        self.kind = kind
        self.ctx = ctx
        self.title: str | None = None
        self.pages: list[dict[str, Any]] = []
        self.sheets: list[dict[str, Any]] | None = None
        self.email: dict[str, Any] | None = None
        self.meta: dict[str, Any] = {}
        self.warnings: list[str] = []
        self.children: dict[str, Child] = {}
        self._skipped_children = 0

    # ── 자식 ───────────────────────────────────────────
    def add_child(self, data: bytes, name: str, mime: str, meta: dict[str, Any] | None = None, *, page: int | None = None) -> str | None:
        """자식 바이너리를 등록하고 ref(sha256)를 돌려준다. 깊이 제한 · 상한이면 None."""
        if not data:
            return None
        if not self.ctx.extract_children:
            self._skipped_children += 1
            return None
        key = hashlib.sha256(data).hexdigest()
        child = self.children.get(key)
        if child is None:
            if len(self.children) >= self.ctx.max_children:
                self._skipped_children += 1
                return None
            child = Child(key, data, name, mime, dict(meta or {}))
            self.children[key] = child
        if page is not None:
            pages = child.meta.setdefault("pages", [])
            if page not in pages:
                pages.append(page)
        return key

    def skip_child(self) -> None:
        """깊이 제한 등으로 뽑지 않은 자식 수만 센다."""
        self._skipped_children += 1

    def page(self, no: int, **kw: Any) -> dict[str, Any]:
        p: dict[str, Any] = {"no": no, "text": "", "blocks": [], "tables": [], "image_refs": [], "images": []}
        p.update(kw)
        self.pages.append(p)
        return p

    def warn(self, w: str) -> None:
        if w not in self.warnings:
            self.warnings.append(w)

    # ── 마무리 ─────────────────────────────────────────
    def finish(self) -> dict[str, Any]:
        texts = []
        for p in self.pages:
            t = p.get("text") or ""
            if len(t) > PAGE_TEXT_LIMIT:
                p["text"] = t[:PAGE_TEXT_LIMIT]
                self.warn(f"page_text_truncated:{p['no']}")
            if p["text"]:
                texts.append(p["text"])
            p["image_refs"] = list(dict.fromkeys(r for r in p.get("image_refs", []) if r))
        text = "\n\n".join(texts)
        if len(text) > TEXT_LIMIT:
            self.warn(f"text_truncated:{len(text)}")
            text = text[:TEXT_LIMIT]
        if self._skipped_children:
            reason = "depth" if not self.ctx.extract_children else "limit"
            self.warn(f"children_skipped:{reason}:{self._skipped_children}")
        title = clean(self.title)[:300] if self.title else None
        return {
            "kind": self.kind,
            "title": title or None,
            "text": text,
            "page_count": len(self.pages),
            "pages": self.pages,
            "sheets": self.sheets,
            "email": self.email,
            "meta": {k: v for k, v in self.meta.items() if v not in (None, "", [], {})},
            "warnings": self.warnings,
            "_children": list(self.children.values()),  # 서비스가 꺼내 저장한다(직렬화 전 제거)
        }


def norm_bbox(x0: float, y0: float, x1: float, y1: float, w: float, h: float) -> list[float] | None:
    if w <= 0 or h <= 0:
        return None
    vals = [x0 / w, y0 / h, x1 / w, y1 / h]
    vals = [round(min(1.0, max(0.0, v)), 4) for v in vals]
    if vals[2] < vals[0]:
        vals[0], vals[2] = vals[2], vals[0]
    if vals[3] < vals[1]:
        vals[1], vals[3] = vals[3], vals[1]
    return vals


def table_text(rows: list[list[str]]) -> str:
    return "\n".join("\t".join(c.replace("\n", " ").replace("\t", " ") for c in row) for row in rows)


def heading_levels(sizes: list[float], body: float) -> dict[float, int]:
    """본문보다 큰 글자 크기들 → 제목 수준(큰 것부터 1)."""
    distinct = sorted({round(s, 1) for s in sizes if s >= body * 1.15}, reverse=True)
    return {s: min(i + 1, 6) for i, s in enumerate(distinct)}
