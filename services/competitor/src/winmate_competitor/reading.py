"""네 칸 읽기(§7.2) — `/v1/parse`(CA1 · CA1R 칩)와 find 잡 `read_input · extract_slots · classify_segment` 가 함께 쓴다.

1. 정의서(CA1R): §4.10 `정의서 → 4칸`(origin=definition). 스냅숏 context 가 비어 있는 칸만 LLM 으로 읽는다.
2. 자유 양식 · 첨부: LLM `ca.extract_slots`(confidential) — 실패하면 KB 만으로 업종 · 제품, 고객사 · 장소는 비움(§4.4 2).
3. 업종: kb `segments/classify` 근거 + LLM `ca.classify_segment` → 03-mi.md §7.3 식 → 1 · 2위 차이 < 0.10 이면 두 갈래(partial).
4. 덧붙일 내용: LLM `ca.include_exclude` → include · exclude.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from winmate_common import platform
from winmate_common.errors import ApiError

from . import aix, config, kbx, prompts, rqx, rules

log = logging.getLogger("winmate.competitor.reading")


def empty_slot() -> dict[str, Any]:
    return {"value": None, "found": "empty", "origin": None, "confidence": None, "partial": False}


def empty_slots() -> dict[str, dict[str, Any]]:
    return {k: empty_slot() for k in rules.SLOT_ORDER}


def set_slot(slots: dict[str, Any], key: str, value: str | None, *, origin: str, confidence: float | None = None,
             partial: bool = False, **extra: Any) -> None:
    v = (value or "").strip() or None
    found = rules.slot_found(v, confidence, partial)
    slots[key] = {"value": v, "found": found, "origin": origin if v else None, "confidence": confidence, "partial": found == "partial",
                  **extra}


# ── 파일 · 정의서 ────────────────────────────────────────
async def files_text(file_ids: list[str]) -> tuple[str, bool]:
    """첨부(RFP · 회의록) 텍스트 앞부분. 아직 추출 중이면 reading=True."""
    parts: list[str] = []
    reading = False
    for fid in (file_ids or [])[:5]:
        try:
            doc = await platform.parsed_document(fid)
        except ApiError as exc:
            if exc.status in (202, 409, 425):
                reading = True
            log.info("파일 추출 실패 %s: %s", fid, exc)
            continue
        except Exception as exc:  # noqa: BLE001
            log.info("파일 추출 실패 %s: %s", fid, exc)
            continue
        txt = doc.get("text") or "\n".join(p.get("text") or "" for p in doc.get("pages") or [])
        if txt:
            parts.append(f"[{doc.get('title') or fid}]\n{txt[:6000]}")
    return "\n\n".join(parts), reading


def place_from_definition(region: str | None, spaces: list[str]) -> tuple[str | None, bool]:
    sp = " · ".join(dict.fromkeys(s for s in spaces if s))[:40]
    if region and sp:
        return f"{region} {sp}", False
    if region:
        return region, False
    if sp:
        return sp, True        # 지역을 못 읽으면 칩 `일부`
    return None, False


def product_from_definition(products: list[str], solutions: list[str]) -> str | None:
    parts = [p for p in [*(products[:1]), *(solutions[:1])] if p]
    return " + ".join(parts) if parts else None


# ── 업종 판별(03-mi.md §7.3 같은 식) ─────────────────────
async def classify(text: str, *, budget: aix.Budget | None = None, confidential: bool = True,
                   inherited: dict[str, Any] | None = None) -> dict[str, Any]:
    """→ segment {code, confidence, ambiguous, gap, candidates, clues, mode, llm_ok}."""
    if inherited and inherited.get("code"):
        return {"code": inherited["code"], "confidence": float(inherited.get("confidence") or 1.0), "ambiguous": False, "gap": None,
                "candidates": [{"code": inherited["code"], "confidence": float(inherited.get("confidence") or 1.0)}], "clues": [],
                "mode": "inherit", "llm_ok": True}
    seg_lines = [f"{s['code']} {s['full']}" for s in config.segments()]
    kb_task = kbx.classify(text)
    llm_task = aix.llm("ca.classify_segment", prompts.classify_segment(text, seg_lines), prompts.ClassifySegmentOut,
                       confidential=confidential, budget=budget)
    kb_res, llm_res = await asyncio.gather(kb_task, llm_task, return_exceptions=True)
    kb_items = {it["code"]: it for it in ((kb_res or {}).get("items") or [])} if isinstance(kb_res, dict) else {}
    p: dict[str, float] = {}
    llm_ok = not isinstance(llm_res, BaseException)
    if llm_ok:
        for s in llm_res.segments:  # type: ignore[union-attr]
            if s.code in config.SEGMENT_CODES:
                p[s.code] = max(p.get(s.code, 0.0), float(s.p))
    elif not isinstance(llm_res, aix.LLMFailed):
        log.warning("업종 LLM 실패: %s", llm_res)
    cands = []
    local = _local_clues(text)
    for code in config.SEGMENT_CODES:
        it = kb_items.get(code) or {}
        kb = float(it.get("kb_score") or 0.0)
        clue = float(it.get("clue_score") if it else local.get(code, 0.0))
        conf = rules.segment_conf(p.get(code, 0.0) if llm_ok else None, kb, clue)
        if conf > 0:
            cands.append({"code": code, "confidence": conf})
    dec = rules.segment_decision(cands)
    clues = []
    for code in [c["code"] for c in dec["candidates"][:2]]:
        for cl in ((kb_items.get(code) or {}).get("clues") or [])[:3]:
            clues.append({"text": cl.get("text"), "code": code})
    dec.update(clues=clues, mode="auto", llm_ok=llm_ok)
    if not llm_ok:
        dec["mode"] = "check"
    return dec


def _local_clues(text: str) -> dict[str, float]:
    """kb 단서가 없을 때(kb 장애) 업종 별칭 사전으로 단서 점수."""
    out: dict[str, float] = {}
    t = text or ""
    for s in config.segments():
        hits = sum(1 for a in s.get("aliases") or [] if a and a in t)
        if hits:
            out[s["code"]] = min(1.0, 0.4 * hits)
    return out


def industry_slot(slots: dict[str, Any], seg: dict[str, Any], *, origin: str, hint: str | None = None) -> None:
    code = seg.get("code")
    if code and code != "GEN":
        set_slot(slots, "industry", config.segment(code)["short"], origin=origin, confidence=seg.get("confidence"),
                 partial=bool(seg.get("ambiguous")), code=code)
    elif hint:
        set_slot(slots, "industry", hint[:20], origin=origin, confidence=seg.get("confidence"), partial=True, code="GEN")
    else:
        slots["industry"] = {**empty_slot(), "code": "GEN"}


async def kb_product(text: str) -> tuple[str | None, list[str]]:
    """KB A1 로 읽은 제품군(카테고리 · 제품군 · 솔루션 이름) — LLM 이 못 읽을 때의 대체 · 제품 칸 보강."""
    links = await kbx.a1(text)
    names: list[str] = []
    for ln in links:
        if ln.get("type") in ("category", "family", "model", "solution") and ln.get("name"):
            nm = str(ln["name"]).split(">")[-1].strip()
            if nm not in names:
                names.append(nm)
    if not names:
        return None, []
    return " + ".join(names[:2]), names


# ── 한 번에 읽기 ─────────────────────────────────────────
async def read(*, text: str | None, file_ids: list[str] | None = None, requirements_id: str | None = None, rq_version: int | None = None,
               extra_text: str | None = None, mi_bundle: dict[str, Any] | None = None, budget: aix.Budget | None = None,
               with_files: bool = True) -> dict[str, Any]:
    """네 칸 · 업종 · RFP · include/exclude 를 읽는다. 돌려주는 dict 는 작업 문서에 그대로 넣을 수 있는 모양."""
    slots = empty_slots()
    text = (text or "").strip()
    extra = (extra_text or "").strip()
    rfp = {"competitor_mentions": [], "eval_criteria": []}
    out: dict[str, Any] = {"slots": slots, "rfp": rfp, "include_names": [], "exclude_names": [], "notes": "", "reading_files": False,
                           "degraded": False, "definition": None, "requirements": [], "author_note": None}
    ftxt, reading = ("", False)
    if with_files and file_ids:
        ftxt, reading = await files_text(file_ids)
    out["reading_files"] = reading
    out["files_text"] = ftxt[:12000]

    inherited_seg: dict[str, Any] | None = None
    definition_text = ""
    # 1) 정의서
    if requirements_id:
        snap = await rqx.snapshot(requirements_id, rq_version)
        if snap:
            d = rqx.read(snap)
            out["definition"] = {k: d[k] for k in ("customer", "project_name", "title", "spaces", "products", "solutions", "version", "project_id",
                                                   "scale_text")}
            out["author_note"] = d.get("author_note")
            out["requirements"] = [{"id": it["id"], "text": it["text"], "weight": it.get("weight"), "origin": "definition", "code": it.get("code")}
                                   for it in d["items"] if it.get("text")]
            if d.get("customer"):
                set_slot(slots, "customer", d["customer"][:60], origin="definition", confidence=1.0)
            prod = product_from_definition(d["products"], d["solutions"])
            if prod:
                set_slot(slots, "product", prod, origin="definition", confidence=1.0)
            vert = d.get("vertical") or {}
            top = (vert.get("top2") or [None])[0]
            if top and not vert.get("ask"):
                codes = config.segment_for_kr(top.get("id"))
                if len(codes) == 1:
                    inherited_seg = {"code": codes[0], "confidence": min(1.0, float(top.get("score") or 1.0))}
            definition_text = "\n".join(filter(None, [d.get("project_name") or "", *[it["text"] for it in d["items"]]]))
            out["_def_spaces"] = d["spaces"]
            if d["spaces"] and not slots["place"]["value"]:
                pass  # 지역은 아래 LLM 으로 읽고 공간 이름과 합친다
    elif mi_bundle:
        cust = (mi_bundle.get("customer") or {})
        name = cust.get("name") if isinstance(cust, dict) else cust
        if name:
            set_slot(slots, "customer", str(name)[:60], origin="mi", confidence=1.0)
        seg_code = mi_bundle.get("segment") or (cust.get("segment") if isinstance(cust, dict) else None)
        if seg_code and seg_code in config.SEGMENT_CODES:
            inherited_seg = {"code": seg_code, "confidence": 1.0}
        reqs = mi_bundle.get("requirements") or []
        out["requirements"] = [{"id": r.get("id"), "text": r.get("text") or "", "weight": r.get("weight"), "origin": "mi"} for r in reqs if r.get("text")]
        definition_text = "\n".join(r.get("text") or "" for r in reqs)

    # 2) 자유 양식 · 첨부 → LLM(빈 칸만)
    body = "\n".join(filter(None, [text, definition_text, extra]))
    want = [k for k in ("customer", "place", "product") if not slots[k]["value"] or (k == "place" and out.get("_def_spaces"))]
    llm_out: prompts.ExtractSlotsOut | None = None
    if (body or ftxt) and want:
        try:
            llm_out = await aix.llm("ca.extract_slots", prompts.extract_slots(body, rfp_text=ftxt, only=want), prompts.ExtractSlotsOut,
                                    confidential=True, budget=budget)
        except aix.LLMFailed as exc:
            log.info("칸 읽기 LLM 실패 → KB 만으로: %s", exc.message)
            out["degraded"] = True
    origin_free = "input" if text else ("definition" if requirements_id else ("mi" if mi_bundle else "input"))
    if llm_out is not None:
        if "customer" in want and llm_out.customer.value:
            set_slot(slots, "customer", llm_out.customer.value[:60], origin=origin_free, confidence=llm_out.customer.confidence)
        if "place" in want:
            if requirements_id and out.get("_def_spaces") is not None:
                region = llm_out.place.region or (llm_out.place.value if llm_out.place.kind == "region" else None)
                val, partial = place_from_definition(region, out.get("_def_spaces") or [])
                if val:
                    set_slot(slots, "place", val, origin="definition", confidence=1.0 if not partial else 0.5, partial=partial)
                elif llm_out.place.value:
                    set_slot(slots, "place", llm_out.place.value[:40], origin=origin_free, confidence=llm_out.place.confidence)
            elif llm_out.place.value:
                set_slot(slots, "place", llm_out.place.value[:40], origin=origin_free, confidence=llm_out.place.confidence,
                         region=llm_out.place.region)
        if "product" in want and llm_out.product.value:
            set_slot(slots, "product", llm_out.product.value[:40], origin=origin_free, confidence=llm_out.product.confidence,
                     partial=not llm_out.product.specific, categories=llm_out.product.categories[:4])
        if llm_out.competitor_mentions:
            rfp["competitor_mentions"] = [m for m in llm_out.competitor_mentions if m][:10]
        if llm_out.eval_criteria:
            rfp["eval_criteria"] = [m for m in llm_out.eval_criteria if m][:10]
    elif requirements_id and out.get("_def_spaces"):
        val, partial = place_from_definition(None, out["_def_spaces"])
        if val:
            set_slot(slots, "place", val, origin="definition", confidence=0.5, partial=partial)
    # 첨부에서 읽은 언급은 rfp 로만 쓴다(텍스트 속 언급도 같은 칸)
    # 3) 제품이 비면 KB A1
    if not slots["product"]["value"] and body:
        prod, cats = await kb_product(body)
        if prod:
            set_slot(slots, "product", prod, origin="input" if text else "definition", confidence=0.6, partial=True, categories=cats)
    # 4) 업종
    seg = await classify("\n".join(filter(None, [text, definition_text, ftxt[:3000], extra])) or "-", budget=budget, inherited=inherited_seg)
    industry_slot(slots, seg, origin="definition" if inherited_seg and requirements_id else ("mi" if inherited_seg else origin_free),
                  hint=(llm_out.industry_hint if llm_out else None))
    out["segment"] = seg
    # 5) 덧붙일 내용
    if extra:
        try:
            ie = await aix.llm("ca.include_exclude", prompts.include_exclude(extra), prompts.IncludeExcludeOut, confidential=True, budget=budget)
            out["include_names"] = [n.strip() for n in ie.include if n and n.strip()][:10]
            out["exclude_names"] = [n.strip() for n in ie.exclude if n and n.strip()][:10]
            out["notes"] = ie.notes[:500]
        except aix.LLMFailed:
            pass
    out.pop("_def_spaces", None)
    return out


def author_note_free(slots: dict[str, Any], note: str | None) -> dict[str, Any]:
    """제작자 의견(내부용) 문장이 칸 값에 들어가지 않게 한다(AC-CA-06) — 들어갔으면 그 칸을 비운다."""
    if not note:
        return slots
    n = re.sub(r"\s+", " ", note).strip()
    for k, v in slots.items():
        val = (v or {}).get("value") or ""
        if val and len(n) >= 6 and (n in val or (len(val) >= 10 and val in n)):
            slots[k] = empty_slot()
    return slots
