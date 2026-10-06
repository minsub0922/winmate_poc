"""ImageCard · ImageMeta 만들기(00-shell §7.2.1). 외부 URL 은 original_url · source_page.url 에만 둔다."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from . import config, curation, images
from .index import idx

_TITLE_SUFFIX = re.compile(r"\s*[|ㅣ｜]\s*Samsung Business.*$", re.I)
_CASE_SHORT = re.compile(r"\s*(?:[–—]|\s-\s|_삼성|_)\s*")
_DATE_PATH = re.compile(r"/(20\d{2})/(\d{2})/(\d{2})/")


def clean_title(t: str | None) -> str | None:
    if not t:
        return t
    return _TITLE_SUFFIX.sub("", t).strip()


def case_short_name(title: str | None) -> str:
    """사례 제목의 앞부분(고객 · 지점 이름): '맥도날드 고양삼송DT점 – 삼성 스마트 사이니지' → '맥도날드 고양삼송DT점'."""
    t = (title or "").strip()
    parts = _CASE_SHORT.split(t, maxsplit=1)
    return (parts[0] or t).strip()


def domain_of(url: str | None) -> str:
    if not url:
        return "samsung.com"
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _pt(page_type: str | None) -> dict[str, Any]:
    pts = curation.load("display").get("page_types") or {}
    return pts.get(page_type or "") or {"kind": "product", "source_type_label": "삼성전자 공식 이미지"}


def kind_of(page_type: str | None, url: str | None = None) -> str:
    if page_type == "us_landing" and url and "/industries" in url:
        return "industry"
    return _pt(page_type)["kind"]


def pick_occurrence(asset_id: str, prefer_doc: str | None = None, prefer_page_type: str | None = None) -> dict[str, Any] | None:
    occs = idx().occ.get(asset_id) or []
    if not occs:
        return None
    if prefer_doc:
        for o in occs:
            if o["document_id"] == prefer_doc:
                return o
    if prefer_page_type:
        for o in occs:
            if o["page_type"] == prefer_page_type:
                return o
    pr = {p: i for i, p in enumerate(curation.load("display").get("occurrence_priority") or [])}
    return sorted(occs, key=lambda o: (pr.get(o["page_type"], 99), o["seq"] or 0))[0]


JUNK_ALT = {"img", "image", "이미지", "사진", "photo", "thumbnail", "thumb"}


def useful(v: str | None) -> bool:
    return bool(v and v.strip() and v.strip().lower() not in JUNK_ALT and len(v.strip()) >= 2)


def _title(asset_id: str, occ: dict[str, Any] | None) -> str:
    s = images.samples().get(asset_id)
    if s and s.get("title"):
        return s["title"]
    if occ:
        for v in (occ.get("alt"), occ.get("caption")):
            if useful(v):
                return v.strip()[:40]
        if occ.get("page_type") == "case_study":
            did = idx().dep_by_doc.get(occ["document_id"])
            if did:
                return f"{case_short_name(idx().deps[did]['title'])} 도입사례 사진"
        sp = occ.get("section_path")
        if sp:
            return sp.split(">")[-1].strip()[:40]
        d = idx().docs.get(occ["document_id"])
        if d and d["title"]:
            return (clean_title(d["title"]) or "")[:40]
    return "이미지"


def _grade(g: str | None) -> str:
    return g if g in ("A", "A?C", "C", "D", "E") else "C"


def card(asset_id: str, *, occ: dict[str, Any] | None = None, prefer_doc: str | None = None,
         prefer_page_type: str | None = None) -> dict[str, Any] | None:
    I = idx()
    a = I.assets.get(asset_id)
    if not a:
        return None
    if occ is None:
        occ = pick_occurrence(asset_id, prefer_doc, prefer_page_type)
    doc = I.docs.get(occ["document_id"]) if occ else None
    page_url = doc["url"] if doc else None
    return {
        "id": asset_id,
        "kind": kind_of(occ["page_type"] if occ else None, page_url),
        "title": _title(asset_id, occ),
        "alt": ((occ or {}).get("alt") or "").strip(),
        "stored_url": config.file_url(asset_id),
        "thumb_url": config.thumb_url(asset_id),
        "original": images.original_dims(asset_id, a["url"] or a["url_mobile"]),
        "focal": None,
        "source_domain": domain_of(page_url),
        "grade": _grade(a["grade_hint"]),
        "rights": a["rights"] if a["rights"] in ("official", "customer_case") else "official",
        "has_local": images.has_local(asset_id),
    }


def _source_label(occ: dict[str, Any], doc: dict[str, Any] | None) -> str:
    I = idx()
    pt = occ["page_type"]
    url = (doc or {}).get("url") or ""
    if pt == "case_study":
        did = I.dep_by_doc.get(occ["document_id"])
        title = I.deps[did]["title"] if did else (doc or {}).get("title")
        return f"{case_short_name(title)} 도입사례"
    if pt and pt.startswith("pdp"):
        m = re.search(r"/([A-Z0-9][A-Z0-9-]{5,})/?(?:#.*)?$", url)
        code = m.group(1) if m else None
        if not code:
            fid = I.doc_family(occ["document_id"])
            code = I.fams[fid]["default_model_code"] if fid else None
        return f"samsung.com · {code}" if code else "samsung.com 제품 페이지"
    return f"samsung.com · {clean_title((doc or {}).get('title')) or url}"


def meta(asset_id: str, *, occ: dict[str, Any] | None = None, prefer_doc: str | None = None,
         prefer_page_type: str | None = None, label_strip: str | None = None) -> dict[str, Any] | None:
    """ImageMeta. label_strip: 시리즈 갤러리면 alt 에서 뺄 시리즈 이름(`단독형 UHD M 시리즈 정면` → `정면`)."""
    I = idx()
    if occ is None:
        occ = pick_occurrence(asset_id, prefer_doc, prefer_page_type)
    base = card(asset_id, occ=occ)
    if base is None or occ is None:
        return None
    a = I.assets[asset_id]
    doc = I.docs.get(occ["document_id"])
    disp = curation.load("display")
    alt = base["alt"]
    label = base["title"]
    if occ["page_type"] == "pdp_gallery":
        fam = label_strip
        if fam is None:
            fid = I.doc_family(occ["document_id"])
            fam = I.fams[fid]["name_ko"] if fid else None
        if fam and alt.startswith(fam.strip()):
            label = alt[len(fam.strip()):].strip() or alt
        elif alt:
            label = alt
    # 게시일: 사례 = 사례 날짜, 그 밖 = 원본 경로의 /YYYY/MM/DD/
    posted = None
    if occ["page_type"] == "case_study":
        did = I.dep_by_doc.get(occ["document_id"])
        if did and I.deps[did]["date"]:
            posted = {"date": I.deps[did]["date"], "basis": "case_page"}
    if posted is None:
        m = _DATE_PATH.search(a["url"] or a["url_mobile"] or "")
        if m:
            posted = {"date": f"{m.group(1)}-{m.group(2)}-{m.group(3)}", "basis": "file_path"}
    rights = base["rights"]
    notes = disp.get("usage_notes") or {}
    caps = disp.get("caption_rules") or {}
    dep_rows = []
    for r in I_depicts(asset_id):
        dep_rows.append({"kind": r["target_kind"], "id": r["target_id"],
                         "name": _ent_name(r["target_kind"], r["target_id"]), "level": r["level_label"] or ""})
    return {
        **base,
        "label": label,
        "source_page": {"url": (doc or {}).get("url") or "", "title": (doc or {}).get("title"), "label": _source_label(occ, doc)},
        "original_url": a["url"] or a["url_mobile"] or "",
        "stored": images.stored_dims(asset_id),
        "posted": posted,
        "collected_at": (doc or {}).get("fetched_at"),
        "source_type_label": _pt(occ["page_type"])["source_type_label"],
        "usage_note": notes.get("customer_case") if rights == "customer_case" else notes.get("official"),
        "usage_note_short": notes.get("customer_case") if rights == "customer_case" else notes.get("official_short"),
        "caption_rule": caps.get(rights) or caps.get("official"),
        "page_note": None,
        "depicts": dep_rows,
        "context": {"space_type_id": occ.get("context_space_type_id"), "vertical_id": occ.get("context_vertical_id")},
    }


def I_depicts(asset_id: str) -> list[dict[str, Any]]:
    from .engine import q

    return q("SELECT target_kind, target_id, level_label FROM depicts WHERE asset_id=? ORDER BY rowid", (asset_id,))


def _ent_name(kind: str, ident: str) -> str:
    from .engine import kb

    try:
        return str(kb().name(kind, ident))
    except Exception:  # noqa: BLE001
        return ident


def image_row_urls(row: dict[str, Any]) -> dict[str, Any]:
    """패턴 결과의 이미지 행(query.py _img_rows)에 로컬 주소를 붙인다(브라우저로 넘길 때 외부 URL 대신 쓰라고)."""
    aid = row.get("id")
    if isinstance(aid, str) and aid.startswith("img_"):
        row["thumb_url"] = config.thumb_url(aid)
        row["stored_url"] = config.file_url(aid)
        row["has_local"] = images.has_local(aid)
        row["kind"] = kind_of(row.get("page_type"), row.get("page_url"))
    return row
