"""내보내기(05-vp.md §7.5 vp_export) — 넘김 묶음(Package) → export 서비스 문서(slides: template_code · slots · notes).

레이아웃 코드 = export 템플릿 코드(docs/templates/CATALOG.md · Value Props). 칸 모양은 템플릿 아키타입을 따른다.
이미지 칸 값은 files `file_id` — KB 이미지는 저장본을 files 로 옮겨 쓴다(출처 · 캡션 규칙 유지).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.platform import save_file

from . import catalog, numbers

log = logging.getLogger("winmate.vp.export")


class ImageCache:
    def __init__(self, project_id: str | None):
        self.project_id = project_id
        self.done: dict[str, str | None] = {}

    async def file_of(self, slot: dict[str, Any] | None) -> dict[str, Any] | None:
        if not slot or not slot.get("asset"):
            return None
        a = slot["asset"]
        meta = slot.get("meta") or {}
        fid = a.get("file_id")
        if not fid and a.get("asset_id"):
            key = a["asset_id"]
            if key not in self.done:
                try:
                    data, mime = await ServiceClient("kb").get_bytes(f"/v1/images/{key}/file")
                    ext = (mime.split("/")[-1] or "png").replace("jpeg", "jpg")
                    fm = await save_file(f"{key}.{ext}", data, mime, source="kb", confidential=False, project_id=self.project_id,
                                         meta={"kb_image_id": key, "caption_rule": meta.get("caption_rule"), "rights": meta.get("rights")},
                                         purpose="vp_export")
                    self.done[key] = fm.get("id")
                except Exception as exc:  # noqa: BLE001 — 이미지 하나가 내보내기를 막지 않는다
                    log.warning("KB 이미지 옮기기 실패 %s: %s", key, exc)
                    self.done[key] = None
            fid = self.done[key]
        if not fid:
            return None
        return {"file_id": fid, "caption": meta.get("caption_rule") or None, "credit": (meta.get("source_page") or {}).get("title") or None,
                "ai_generated": slot.get("tier") == "illust" or None, "fit": slot.get("fit") or "cover"}


def _disp(v: dict[str, Any] | None) -> str:
    return (v or {}).get("display") or "[00]"


def _change(m: dict[str, Any]) -> str:
    b, a = m.get("before") or {}, m.get("after") or {}
    if b.get("value") and a.get("value") and (b.get("unit") or "") == (a.get("unit") or ""):
        try:
            pct = round((float(a["value"]) - float(b["value"])) / float(b["value"]) * 100)
            return f"{pct:+d}%"
        except (TypeError, ZeroDivisionError, ValueError):
            return ""
    return ""


async def slots_of(sheet: dict[str, Any], imgs: ImageCache, customer: str) -> dict[str, Any]:
    code = catalog.norm(sheet["layout"]["code"])
    c = sheet.get("content") or {}
    title = sheet.get("title") or ""
    slots_by_idx = {i: s for i, s in enumerate(sheet.get("image_slots") or [])}
    first_img = await imgs.file_of(slots_by_idx.get(0))
    e = catalog.entry(code) or {}
    pack_role = e.get("pack_role")
    if code.startswith("CH-") and code != "CH-B" and code != "CH-C" or (pack_role == "A" and c.get("challenges") and not c.get("pairs")):
        items = [{"no": f"{i:02d}", "tag": "과제", "title": ch["title"], "body": ch.get("body") or "", "quote": "",
                  "who": "", "kpi": _disp(ch.get("impact"))} for i, ch in enumerate(c.get("challenges") or [], 1)]
        return {"title": title, "items": items}
    if code == "CH-B":
        rows = [{"label": f"{i:02d}", "left": ch["title"], "right": ch.get("body") or "[확인 필요]"} for i, ch in enumerate(c.get("challenges") or [], 1)]
        return {"title": title, "subtitle": sheet.get("points") or "", "rows": rows, "headers": ["", "지금", "바라는 모습"]}
    if code == "CH-C":
        chs = c.get("challenges") or []
        root = chs[0] if chs else {"title": "[확인 필요]"}
        return {"title": title, "subtitle": sheet.get("points") or "", "headers": ["문제", "원인", "근본 원인"],
                "root": {"tag": "문제", "title": root["title"], "kpi": _disp(root.get("impact")), "note": root.get("body") or ""},
                "branches": [{"no": f"{i:02d}", "title": ch["title"], "body": ch.get("body") or ""} for i, ch in enumerate(chs[:3], 1)],
                "leaves": [{"title": ch["title"], "body": "", "tag": "원인"} for ch in chs[:3]]}
    if code in ("VP-E", "VP-U") or (pack_role == "A"):
        rows = []
        for i, p in enumerate(c.get("pairs") or []):
            rows.append({"left": p["challenge"], "mid": (p.get("product") or {}).get("name") or "", "right": p.get("value") or "", "kpi": "",
                         "image": await imgs.file_of(slots_by_idx.get(i)) if code != "VP-A" else None, "left_sub": ""})
        return {"title": title, "rows": rows, "headers": ["고객 과제" if code != "VP-U" else "현장 질문", "삼성 제품 · 솔루션", "가치"]}
    if code == "VP-A":
        rows = [{"label": f"{i:02d}", "left": p["challenge"], "right": p.get("value") or ""} for i, p in enumerate(c.get("pairs") or [], 1)]
        return {"title": title, "rows": rows, "headers": ["", "과제", "해결"]}
    if code in ("VP-G", "VP-C"):
        ol = c.get("one_liner") or {}
        proofs = [{"kpi": "", "title": e_, "body": ""} for e_ in (ol.get("evidence") or [])[:3]]
        out: dict[str, Any] = {"title": title, "message": ol.get("statement") or "", "message_sub": sheet.get("points") or "", "proofs": proofs}
        if code == "VP-G":
            out["image"] = first_img
        return out
    if code in ("VP-H", "VP-D") or pack_role == "B":
        people = []
        for i, s in enumerate(c.get("stakeholders") or []):
            p = {"role": s["role"], "name": s["role"], "body": s.get("value") or "", "bullets": [], "quote": "", "kpi": s.get("kpi") or ""}
            if code == "VP-H":
                p["image"] = await imgs.file_of(slots_by_idx.get(i))
            people.append(p)
        return {"title": title, "people": people, "message": sheet.get("points") or ""}
    if code == "EF-B":
        roi = c.get("roi") or {}
        pay = roi.get("payback_months") or []
        stats = [{"value": _disp(roi.get("investment")), "label": "투자비"}]
        if pay:
            stats.append({"value": f"{numbers.fmt_num(min(pay))}~{numbers.fmt_num(max(pay))}", "unit": "개월", "label": "회수 기간"})
        else:
            stats.append({"value": "[00]", "unit": "개월", "label": "회수 기간"})
        sav = roi.get("savings") or []
        stats.append({"value": _disp(sav[1] if len(sav) > 1 else (sav[0] if sav else None)), "label": "연 절감액(기준)"})
        chart = {"type": "bar", "categories": roi.get("scenario_labels") or ["보수", "기준", "낙관"],
                 "series": [{"name": "회수 기간(개월)", "values": pay or [0, 0, 0]}], "unit": "개월"}
        return {"title": title, "subtitle": sheet.get("points") or "", "chart": chart, "chart_title": "절감액 시나리오별 회수 기간",
                "stats": stats, "assumptions": "회수 기간 = 투자비 ÷ (연 절감액 ÷ 12) · 절감액은 범위로 표기 [추정]"}
    if code == "EF-C":
        kpis = [{"value": _disp(m.get("after")), "label": m["label"], "sub": f"지금 {_disp(m.get('before'))}"} for m in (c.get("metrics") or [])[:4]]
        feels = [{"no": f"{i:02d}", "title": q, "body": "", "who": ""} for i, q in enumerate((c.get("qualitative") or [])[:4], 1)]
        return {"title": title, "headers": ["수치로 보는 효과", "현장이 느끼는 변화"], "kpis": kpis, "feels": feels}
    if code == "EF-A" or pack_role == "C":
        rows = [{"title": m["label"], "body": m.get("source_label") or "", "before": _disp(m.get("before")), "after": _disp(m.get("after")),
                 "change": _change(m)} for m in (c.get("metrics") or [])[:4]]
        return {"title": title, "subtitle": sheet.get("points") or "", "rows": rows, "headers": ["지표", "지금", "도입 후", "변화"]}
    if code == "VP-M":
        pillars = c.get("pillars") or []
        prods = []
        for p in pillars:
            for r in p.get("product_refs") or []:
                if r.get("name") and r["name"] not in prods:
                    prods.append(r["name"])
        rows = [[p["title"]] + ["●" if any(r.get("name") == pr for r in p.get("product_refs") or []) else "" for pr in prods] for p in pillars]
        return {"title": title, "table": {"columns": ["가치"] + prods, "rows": rows}}
    if code in ("VP-I", "VP-J", "VP-P", "VP-US", "VP-K"):
        n = 5 if code == "VP-K" else (3 if code in ("VP-P", "VP-US") else 4)
        pos = [(0.2, 0.3), (0.7, 0.3), (0.25, 0.7), (0.72, 0.68), (0.5, 0.5)]
        pins = []
        for i, p in enumerate((c.get("pillars") or [])[:n]):
            pin = {"no": f"{i + 1:02d}", "title": p["title"], "body": p.get("body") or "", "x": pos[i][0], "y": pos[i][1]}
            if code != "VP-K":
                pin["tag"] = ((p.get("product_refs") or [{}])[0]).get("name") or ""
            pins.append(pin)
        return {"title": title, "image": first_img, "pins": pins}
    if code in ("VP-L", "VP-S"):
        ps = c.get("pillars") or []
        sides = []
        for i, lab in enumerate(("도입 전", "도입 후")):
            p = ps[i] if i < len(ps) else {"title": "[확인 필요]", "body": ""}
            sides.append({"tag": lab, "title": p["title"], "body": p.get("body") or "", "bullets": [], "image": await imgs.file_of(slots_by_idx.get(i))})
        return {"title": title, "sides": sides, "labels": ["도입 전", "도입 후"], "message": sheet.get("points") or "", "message_label": "달라지는 것"}
    if code in ("VP-N", "VP-Q", "VP-T"):
        items = [{"no": f"{i:02d}", "tag": "가치", "title": p["title"], "body": p.get("body") or "", "kpi": ""}
                 for i, p in enumerate((c.get("pillars") or [])[:3], 1)]
        ref = c.get("reference") or {}
        return {"title": title, "image": first_img, "image_caption": ((slots_by_idx.get(0) or {}).get("meta") or {}).get("caption_rule") or "",
                "message": ref.get("summary") or sheet.get("points") or "", "items": items}
    if code == "VP-R":
        steps = [{"no": f"{i:02d}", "title": p["title"], "body": p.get("body") or "", "chips": [], "image": await imgs.file_of(slots_by_idx.get(i - 1))}
                 for i, p in enumerate((c.get("pillars") or [])[:4], 1)]
        return {"title": title, "steps": steps, "message": sheet.get("points") or ""}
    # pillars 계열(VP-F · VP-B · VP-O · VP-UC · EF-D · EF-E)
    out_p = []
    for i, p in enumerate(c.get("pillars") or []):
        card = {"no": f"{i + 1:02d}", "tag": ((p.get("product_refs") or [{}])[0]).get("name") or "가치", "title": p["title"],
                "body": p.get("body") or "", "kpi": ""}
        if catalog.has_images(code):
            card["image"] = await imgs.file_of(slots_by_idx.get(i))
        out_p.append(card)
    if code in ("EF-D", "EF-E") and c.get("metrics"):
        out_p = [{"no": f"{i + 1:02d}", "tag": "효과", "title": m["label"], "body": m.get("source_label") or "",
                  "kpi": f"{_disp(m.get('before'))} → {_disp(m.get('after'))}"} for i, m in enumerate(c["metrics"][:3])]
    return {"title": title, "pillars": out_p}


async def build_document(doc: dict[str, Any], pkg: dict[str, Any], *, include_notes: bool, summary_only: bool = False) -> dict[str, Any]:
    imgs = ImageCache(doc.get("project_id"))
    cust = doc.get("customer_name") or ""
    slides = []
    sheets = pkg["sheets"]
    if summary_only:
        one = next((s for s in sheets if catalog.norm(s["layout"]["code"]) in ("VP-G", "VP-C")), None)
        sheets = [one] if one else sheets[:1]
    for s in sheets:
        code = catalog.norm(s["layout"]["code"])
        e = catalog.entry(code) or {}
        if e.get("industry_code") and not await _template_ready(code):
            code = catalog.norm((doc.get("plan") or {}).get("fallback", {}).get(s["role"]) or {"CH": "CH-A", "VP": "VP-F3", "EF": "EF-A"}.get(s["role"], "VP-F3"))
            s = {**s, "layout": {**s["layout"], "code": code}}
        slide = {"template_code": code, "slots": await slots_of(s, imgs, cust), "sheet_id": s.get("sheet_id")}
        if include_notes and s.get("speaker_notes"):
            slide["notes"] = s["speaker_notes"]
        foot = [{"label": x} for x in (pkg.get("sources_footer") or [])[:4]]
        if foot:
            slide["sources"] = foot
        slides.append(slide)
    return {"title": doc.get("title") or "가치 제안", "slides": slides}


_ready_cache: dict[str, bool] = {}


async def _template_ready(code: str) -> bool:
    if code in _ready_cache:
        return _ready_cache[code]
    try:
        t = await ServiceClient("export").get(f"/v1/templates/{code}")
    except Exception:  # noqa: BLE001
        return False   # 호출 실패(예: export 상세 500)는 기억하지 않는다 — export 가 고쳐지면 vp 재시작 없이 다시 묻는다(통합)
    ok = (t or {}).get("status") == "ready"
    _ready_cache[code] = ok
    return ok


async def run(doc: dict[str, Any], pkg: dict[str, Any], *, fmt: str, include_notes: bool) -> dict[str, Any]:
    """export 서비스로 파일 만들기 → {file_id, filename, warnings}."""
    summary = fmt == "pdf_summary"
    document = await build_document(doc, pkg, include_notes=include_notes, summary_only=summary)
    name = f"{doc.get('title') or '가치 제안'}" + (" 한 장 요약" if summary else "")
    body = {"format": "pdf" if summary else "pptx", "filename": name, "document": document, "confidential": True,
            "project_id": doc.get("project_id"), "source_ref": f"vp:{doc['id']}", "tbd_mode": "keep_marks"}
    ex = ServiceClient("export", timeout=180)
    res = await ex.post("/v1/exports", json=body)
    if res.get("status") != "done":
        eid = res.get("export_id")
        for _ in range(120):
            await asyncio.sleep(1.0)
            res = await ex.get(f"/v1/exports/{eid}")
            if res.get("status") in ("done", "failed"):
                break
        if res.get("status") != "done":
            from winmate_common.errors import ApiError
            raise ApiError(502, "EXPORT_FAILED", "파일을 만들지 못했어요. 잠시 후 다시 시도해 주세요.", {"export_id": eid})
    f = res.get("file") or {}
    return {"file_id": f.get("id"), "filename": f.get("name"), "warnings": res.get("warnings") or [],
            "slide_count": res.get("slide_count") or len(document["slides"])}
