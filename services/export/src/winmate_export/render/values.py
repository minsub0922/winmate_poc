"""칸 값 다루기 — 언어 고르기({ko, en}) · 확인 필요 표시 · 형식별 정규화."""
from __future__ import annotations

import contextvars
import re
from typing import Any

# 근거 없는 값의 자리표시(AGENTS.md: `[확인 필요]` · `[00]`) — 짧은 대괄호 토큰을 모두 표시 대상으로 본다
MARKER = re.compile(r"\[[^\[\]\n]{0,18}\]")
EN_MARKERS = [
    (re.compile(r"\[\s*(?:수치\s*)?(?:확인|확정)\s*필요\s*\]"), "[TBD]"),
    (re.compile(r"\[\s*추정\s*\]"), "[Est.]"),
]
# 영어 문서의 확인 필요 표시(ProposalRenderDoc.tbd_label 로 바꿀 수 있다)
TBD_LABEL: contextvars.ContextVar[str] = contextvars.ContextVar("wm_export_tbd_label", default="[TBD]")
LABELS = {
    "source": {"ko": "출처", "en": "Source"},
    "ai": {"ko": "AI 생성 이미지", "en": "AI-generated image"},
    "confidential": {"ko": "CONFIDENTIAL", "en": "CONFIDENTIAL"},
    "confirm": {"ko": "[확인 필요]", "en": "[TBD]"},
    "image": {"ko": "이미지", "en": "Image"},
}


def label(key: str, lang: str) -> str:
    if key == "confirm" and lang == "en":
        return TBD_LABEL.get()
    return LABELS[key]["en" if lang == "en" else "ko"]


def localize(value: Any, lang: str) -> Any:
    """{ko, en} 이면 언어에 맞는 값을. both(inline)는 '한국어\\n영어'."""
    if isinstance(value, dict) and ("ko" in value or "en" in value) and not ({"value", "file_id", "title", "columns", "series"} & set(value)):
        ko, en = value.get("ko"), value.get("en")
        if lang == "en":
            return en if en not in (None, "") else ko
        if lang == "both":
            if ko and en and ko != en:
                return f"{ko}\n{en}"
            return ko or en
        return ko if ko not in (None, "") else en
    return value


def to_text(value: Any, lang: str = "ko") -> str:
    value = localize(value, lang)
    if value is None:
        return ""
    if isinstance(value, bool):
        return "●" if value else ""
    if isinstance(value, (int, float)):
        return format_number(value)
    if isinstance(value, dict):
        for k in ("text", "title", "label", "value", "name"):
            if k in value:
                return to_text(value[k], lang)
        return ""
    if isinstance(value, list):
        return " · ".join(to_text(v, lang) for v in value if v not in (None, ""))
    s = str(value)
    if lang == "en":
        s = en_markers(s)
    return s


_ILLEGAL_XML = re.compile(r"[\000-\010\013\014\016-\037]")
EXCEL_CELL_MAX = 32767


def excel_text(s: str) -> str:
    """엑셀 칸 · 메모 · 시트 이름에 넣을 글 — XML 에 못 넣는 제어 문자를 빼고 칸 한도(32,767자)로 자른다(openpyxl 은 제어 문자에 오류를 낸다)."""
    s = _ILLEGAL_XML.sub("", s)
    return s if len(s) <= EXCEL_CELL_MAX else s[: EXCEL_CELL_MAX - 1] + "…"


def en_markers(s: str) -> str:
    """[확인 필요] · [확정 필요] → [TBD], [추정] → [Est.]"""
    for rx, rep in EN_MARKERS:
        s = rx.sub(TBD_LABEL.get() if rep == "[TBD]" else rep, s)
    return s


def format_number(v: float | int) -> str:
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int) or float(v).is_integer():
        return f"{int(v):,}"
    return f"{v:,.1f}"


def split_markers(text: str) -> list[tuple[str, bool]]:
    """텍스트를 (조각, 표시 여부) 로 나눈다."""
    out: list[tuple[str, bool]] = []
    pos = 0
    for m in MARKER.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], False))
        out.append((m.group(0), True))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], False))
    return out or [("", False)]


def has_marker(text: str) -> bool:
    return bool(MARKER.search(text or ""))


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def as_bullets(value: Any, lang: str) -> list[str]:
    value = localize(value, lang)
    if value is None:
        return []
    if isinstance(value, str):
        return [s.strip(" •-·") for s in value.split("\n") if s.strip(" •-·")]
    return [t for t in (to_text(v, lang) for v in as_list(value)) if t]


def as_kpi(value: Any, lang: str) -> dict[str, str]:
    value = localize(value, lang)
    if value is None or value == "":
        return {}
    if isinstance(value, (int, float, str)):
        return {"value": to_text(value, lang)}
    if isinstance(value, dict):
        out = {k: to_text(value.get(k), lang) for k in ("value", "unit", "label", "sub", "delta", "pre") if value.get(k) not in (None, "")}
        bar = value.get("bar")
        if isinstance(bar, (int, float)):
            out["bar"] = str(max(0.0, min(100.0, float(bar))))
        return out
    return {"value": to_text(value, lang)}


def as_card(value: Any, lang: str) -> dict[str, Any]:
    value = localize(value, lang)
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    return {"title": value}


def image_ref(value: Any) -> dict[str, Any] | None:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        return {"file_id": value}
    if isinstance(value, dict):
        fid = value.get("file_id") or value.get("id")
        if fid:
            return {**value, "file_id": fid}
    return None


def as_sources(value: Any, lang: str) -> list[dict[str, str]]:
    out = []
    for v in as_list(localize(value, lang)):
        if isinstance(v, dict):
            lbl = to_text(v.get("label") or v.get("title") or v.get("name") or v.get("url"), lang)
            if lbl:
                out.append({"label": lbl, "url": v.get("url") or ""})
        elif v not in (None, ""):
            out.append({"label": to_text(v, lang), "url": ""})
    return out


def as_table(value: Any, lang: str) -> dict[str, Any]:
    value = localize(value, lang)
    if not value:
        return {"columns": [], "rows": []}
    if isinstance(value, list):
        rows = [list(r) if isinstance(r, (list, tuple)) else [r] for r in value]
        return {"columns": rows[0] if rows else [], "rows": rows[1:]}
    cols = value.get("columns") or []
    rows = value.get("rows") or []
    norm_rows = []
    for r in rows:
        if isinstance(r, dict):
            keys = [c.get("key") if isinstance(c, dict) else c for c in cols]
            norm_rows.append([r.get(k) for k in keys])
        else:
            norm_rows.append(list(r))
    out = dict(value)
    out["columns"] = cols
    out["rows"] = norm_rows
    return out


def cell_text(cell: Any, lang: str) -> str:
    if isinstance(cell, dict) and not ({"ko", "en"} & set(cell)):
        return to_text(cell.get("text", cell.get("value", cell.get("title", ""))), lang)
    return to_text(cell, lang)


def col_label(col: Any, lang: str) -> str:
    if isinstance(col, dict) and not ({"ko", "en"} & set(col)):
        return to_text(col.get("label") or col.get("title") or col.get("key"), lang)
    return to_text(col, lang)


def collect_file_ids(obj: Any, out: set[str] | None = None) -> set[str]:
    """문서 JSON 에서 file_id 를 모두 모은다(이미지 미리 받기)."""
    out = out if out is not None else set()
    if isinstance(obj, dict):
        fid = obj.get("file_id")
        if isinstance(fid, str) and fid:
            out.add(fid)
        for k, v in obj.items():
            if k != "file_id":
                collect_file_ids(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect_file_ids(v, out)
    return out
