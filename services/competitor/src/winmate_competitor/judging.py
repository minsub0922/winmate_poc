"""분석 단계 공용(§7.6 · §7.7) — 삼성 칸(KB 만) · 판정 · 포지셔닝 · 강점/주의할 점 · 결과 버전 만들기.

- 삼성 칸: 기준 이름 → 정규 스펙 키(소비전력 · 밝기 …) · 솔루션 메시지(MagicINFO) · 사례(사내 사례 DB) · E2 메시지 순으로 KB 에서만.
  삼성 비교 제품은 TopBar 추가 → 요구 A1 → S1 순(§7.6 samsung_side).
- 판정: LLM `ca.verdicts`(경쟁사마다) — 경쟁사 사실이나 삼성 칸이 `[확인 필요]` 인 기준은 결정 규칙으로 `unknown`.
- 강점 · 주의할 점: 고르는 것은 규칙(rules.pick_*), 문장만 LLM `ca.strengths`(실패하면 규칙 문장). 근거에 없는 수치는 `[00]`.
"""
from __future__ import annotations

import copy
import logging
import re
from typing import Any

from rapidfuzz import fuzz

from winmate_common.ids import now_iso

from . import aix, config, kbx, prompts, rules, verify
from . import evidence as E

log = logging.getLogger("winmate.competitor.judging")

TBD = "[확인 필요]"
SPEC_MAP: list[tuple[tuple[str, ...], str, tuple[str, ...]]] = [
    (("전기", "전력", "에너지", "소비전력", "저전력"), "power_consumption", ("On",)),
    (("밝기", "휘도", "가독"), "brightness_nit", ()),
    (("해상도", "화질", "UHD", "4K"), "resolution", ()),
    (("운영 시간", "24시간", "상시", "내구", "연속"), "operation_hours", ()),
]
SOLUTION_KEYS = ("배포", "콘텐츠", "원격", "통합", "관리", "CMS", "일괄", "본사", "연동", "차등", "스케줄", "보안", "서버")
REF_KEYS = ("레퍼런스", "사례", "AS", "A/S", "유지보수", "지원", "설치")
PRICE_KEYS = ("가격", "단가", "비용", "가성비")
FACT_KEYS_FOR = [
    (("배포", "콘텐츠", "CMS", "관리", "원격", "솔루션", "연동", "일괄", "차등", "보안", "서버", "스케줄"), ["solution"]),
    (("가격", "단가", "비용", "가성비"), ["price"]),
    (("레퍼런스", "사례", "AS", "A/S", "유지보수", "설치", "지원"), ["references"]),
    (("전기", "전력", "에너지", "라인업", "크기", "인치", "밝기", "화질", "해상도", "디자인", "하드웨어", "제품", "내구"), ["lineup"]),
    (("동향", "신제품", "출시"), ["recent"]),
]


def is_price(name: str) -> bool:
    """가격 기준(삼성 가격은 KB 에 없음 → `[확인 필요]`). `매장별 가격 차등` 처럼 솔루션 기능을 말하면 가격 기준이 아니다."""
    return any(k in name for k in PRICE_KEYS) and not any(k in name for k in SOLUTION_KEYS)


def fact_keys_for(criterion: str) -> list[str]:
    for keys, facts in FACT_KEYS_FOR:
        if any(k in criterion for k in keys):
            return facts
    return list(config.fact_order())


# ── 삼성 비교 제품 ───────────────────────────────────────
async def samsung_products(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """TopBar 로 추가한 제품 → 요구 A1 → S1 공간별 추천 1순위 제품군의 대표 모델."""
    out: list[dict[str, Any]] = []
    for p in doc.get("samsung_products") or []:
        if p.get("kind") in ("model", "family") and p.get("model_code"):
            out.append(p)
    if out:
        return out[:3]
    prod = ((doc.get("slots") or {}).get("product") or {}).get("value") or ""
    req_text = "\n".join(r.get("text") or "" for r in doc.get("requirements") or [])
    text = "\n".join(filter(None, [doc.get("text") or "", req_text, prod]))
    for ln in await kbx.a1(text):
        if ln.get("type") == "model" and ln.get("id"):
            code = str(ln["id"]).removeprefix("mdl_")
            out.append({"kind": "model", "model_code": code, "name": ln.get("name") or code})
        elif ln.get("type") == "family" and ln.get("id"):
            m = await kbx.model(ln["id"])
            if m and m.get("model_code"):
                out.append({"kind": "family", "model_code": m["model_code"], "name": m.get("display_name") or m["model_code"],
                            "family_id": ln["id"], "family_name": ln.get("name")})
        if out:
            break
    if out:
        return out[:3]
    s1 = await kbx.s1("\n".join(filter(None, [prod, req_text[:400]])) or prod or "-")
    for sp in s1.get("by_space") or []:
        for fam in sp.get("families") or []:
            if fam.get("model"):
                out.append({"kind": "family", "model_code": fam["model"], "name": fam.get("name") or fam["model"], "family_id": fam.get("id"),
                            "family_name": fam.get("name")})
                break
        if out:
            break
    return out[:1]


def _solution_ids(doc: dict[str, Any]) -> list[str]:
    ids = [p.get("solution_id") for p in doc.get("samsung_products") or [] if p.get("kind") == "solution" and p.get("solution_id")]
    return ids or ["magicinfo"]


# ── 삼성 칸 ──────────────────────────────────────────────
async def samsung_side(doc: dict[str, Any], bag: dict[str, Any], criteria: list[dict[str, Any]]) -> dict[str, Any]:
    prods = await samsung_products(doc)
    model = prods[0] if prods else None
    spec = await kbx.spec_table([model["model_code"]]) if model else None
    seg = config.segment((doc.get("segment") or {}).get("code"))
    ins = await kbx.insights(seg.get("code", "GEN"))
    cells: dict[str, Any] = {}
    for c in criteria:
        try:
            cells[c["id"]] = await _cell(doc, bag, c, model=model, spec=spec, seg=seg, ins=ins)
        except Exception as exc:  # noqa: BLE001 — 한 칸 실패가 분석을 막지 않는다
            log.warning("삼성 칸 실패 %s: %s", c.get("name"), exc)
            cells[c["id"]] = {"text": TBD, "claim_ids": [], "products": [], "tbd": True}
    bag["samsung_products"] = prods
    return cells


def _kb_src(bag: dict[str, Any], *, kind: str, subtype: str, title: str, text: str, url: str | None, kb_key: str) -> tuple[str, dict[str, Any]]:
    sid = E.add_source(bag, {"kind": kind, "subtype": subtype, "title": title, "publisher": "samsung.com" if url else "사내 사례 DB", "url": url,
                             "published_at": None, "published_basis": "kb", "authority": 2, "mode": "kb", "kb_key": kb_key}, text)
    return sid, {"source_id": sid, "kind": kind, "title": title, "text": text}


async def _cell(doc: dict[str, Any], bag: dict[str, Any], crit: dict[str, Any], *, model: dict[str, Any] | None, spec: dict[str, Any] | None,
                seg: dict[str, Any], ins: dict[str, Any]) -> dict[str, Any]:
    name = crit.get("name") or ""
    claim_ids: list[str] = []
    products: list[str] = []
    if is_price(name):
        return {"text": TBD, "claim_ids": [], "products": [], "tbd": True}
    # 1) 정규 스펙 키
    for keys, norm, hints in SPEC_MAP:
        if not any(k in name for k in keys) or not spec or not model:
            continue
        rows = [r for r in spec.get("rows") or [] if r.get("norm_key") == norm]
        if hints:
            rows = sorted(rows, key=lambda r: 0 if any(hh in (r.get("attr_name") or "") for hh in hints) else 1)
        for r in rows[:1]:
            val = (r.get("values") or {}).get(model["model_code"]) or {}
            if not val.get("raw"):
                continue
            disp = (spec.get("models") or [{}])[0].get("display_name") or model.get("name") or model["model_code"]
            line = f"{r.get('attr_name')}: {val['raw']}"
            text = f"{disp} 스펙\n{line}"
            _, e = _kb_src(bag, kind="kb_official", subtype="스펙", title=f"{disp} 스펙", text=text, url=val.get("source_url"),
                           kb_key=f"spec:{model['model_code']}:{r.get('attr_name')}")
            cid = E.make_claim(bag, text=f"{disp} {r.get('attr_name')} {val['raw']}", cites=[(e, line)], criterion_id=crit["id"], block="samsung")
            if cid:
                claim_ids.append(cid)
                products.append(disp)
        # 같은 테마 E2 메시지(사이니지 · 디스플레이 관련만)
        for m in await kbx.e2(f"{name} {'사이니지' if model else ''}".strip(), limit=5):
            about = m.get("about_name") or ""
            if any(k in about for k in ("사이니지", "디스플레이", "MagicINFO", "VXT")) and m.get("text"):
                _, e = _kb_src(bag, kind="kb_official", subtype="메시지", title=f"삼성 공식 · {about}", text=m["text"], url=None,
                               kb_key=f"msg:{m.get('id')}")
                cid = E.make_claim(bag, text=m["text"][:60], cites=[(e, m["text"][:60])], criterion_id=crit["id"], block="samsung")
                if cid:
                    claim_ids.append(cid)
                break
        if claim_ids:
            return _cell_out(bag, claim_ids, products)
    # 2) 솔루션 메시지
    if any(k in name for k in SOLUTION_KEYS):
        for sol_id in _solution_ids(doc):
            sol = await kbx.solution(sol_id)
            if not sol:
                continue
            msgs = [m for m in sol.get("messages") or [] if m.get("text")]
            words = [w for w in re.split(r"[\s·]+", name) if len(w) >= 2]
            pick = next((m for m in msgs if any(w in m["text"] for w in words)), None) or (msgs[0] if msgs else None)
            if not pick:
                continue
            sname = sol.get("name") or sol_id
            _, e = _kb_src(bag, kind="kb_official", subtype="메시지", title=f"삼성 공식 · {sname}", text=pick["text"], url=pick.get("source_url"),
                           kb_key=f"sol:{sol_id}:{pick['text'][:40]}")
            cid = E.make_claim(bag, text=f"{sname} · {pick['text']}", cites=[(e, pick["text"])], criterion_id=crit["id"], block="samsung",
                               allow_numbers_from=[sname])
            if cid:
                claim_ids.append(cid)
                products.append(sname)
                break
        if claim_ids:
            return _cell_out(bag, claim_ids, products)
    # 3) 사례(사내 사례 DB)
    if any(k in name for k in REF_KEYS) or crit.get("source") == "industry_cases":
        n = int(ins.get("cases") or 0)
        if n and seg.get("code") != "GEN":
            line = f"{seg['full']} 도입사례 {n}건"
            _, e = _kb_src(bag, kind="kb_case", subtype="사례", title=f"사내 사례 DB · {seg['full']}", text=line, url=None,
                           kb_key=f"cases:{seg['code']}")
            cid = E.make_claim(bag, text=f"같은 업종 도입사례 {n}건", cites=[(e, line)], criterion_id=crit["id"], block="samsung")
            if cid:
                claim_ids.append(cid)
        prod = ((doc.get("slots") or {}).get("product") or {}).get("value") or ""
        for ch in (await kbx.search(f"{seg.get('full', '')} {prod} {name}".strip(), k=3))[:3]:
            if ch.get("page_type") != "case_study" or not ch.get("title"):
                continue
            title = str(ch["title"])
            _, e = _kb_src(bag, kind="kb_case", subtype="사례", title=title, text=f"{title}\n{ch.get('text') or ''}", url=ch.get("url"),
                           kb_key=f"chunk:{ch.get('chunk_id')}")
            cid = E.make_claim(bag, text=f"삼성 사례 · {title[:40]}", cites=[(e, title[:40])], criterion_id=crit["id"], block="samsung")
            if cid:
                claim_ids.append(cid)
            break
        if claim_ids:
            return _cell_out(bag, claim_ids, products)
    # 4) E2 메시지(관련 제품군)
    for m in await kbx.e2(f"{name} 사이니지", limit=5):
        about = m.get("about_name") or ""
        if any(k in about for k in ("사이니지", "디스플레이", "MagicINFO", "VXT")) and m.get("text"):
            _, e = _kb_src(bag, kind="kb_official", subtype="메시지", title=f"삼성 공식 · {about}", text=m["text"], url=None, kb_key=f"msg:{m.get('id')}")
            cid = E.make_claim(bag, text=m["text"][:60], cites=[(e, m["text"][:60])], criterion_id=crit["id"], block="samsung")
            if cid:
                claim_ids.append(cid)
            break
    if claim_ids:
        return _cell_out(bag, claim_ids, products)
    return {"text": TBD, "claim_ids": [], "products": [], "tbd": True}


def _cell_out(bag: dict[str, Any], claim_ids: list[str], products: list[str]) -> dict[str, Any]:
    texts = [bag["claims"][c]["text"] for c in claim_ids if c in bag["claims"]]
    return {"text": " · ".join(texts)[:120], "claim_ids": claim_ids, "products": products, "tbd": False}


# ── 사실 → 주장 ──────────────────────────────────────────
def facts_from_llm(bag: dict[str, Any], cmp_id: str, out: prompts.ExtractFactsOut, ev: list[dict[str, Any]], *, keys: list[str] | None = None) -> dict[str, Any]:
    by_id = {e["id"]: e for e in ev}
    facts: dict[str, Any] = {}
    for key in keys or config.fact_order():
        item: prompts.FactItem = getattr(out.facts, key)
        claim_ids: list[str] = []
        for cl in item.claims:
            cites = [(by_id[c.evidence_id], c.quote) for c in cl.citations if c.evidence_id in by_id and c.quote]
            if not cites or not (cl.text or "").strip():
                continue
            cid = E.make_claim(bag, text=cl.text.strip(), cites=cites, competitor_id=cmp_id, fact_key=key, block="fact")
            if cid:
                claim_ids.append(cid)
        facts[key] = fact_entry(bag, key, item.text, claim_ids)
    return facts


def fact_entry(bag: dict[str, Any], key: str, text: str | None, claim_ids: list[str]) -> dict[str, Any]:
    if not claim_ids:
        return {"text": TBD, "claim_ids": [], "tbd": True, "sources": 0, "has_kb": False, "check": True}
    quotes = E.claim_quotes(bag, claim_ids)
    t = (text or "").strip()
    if not t or TBD in t:
        t = " · ".join(bag["claims"][c]["text"] for c in claim_ids)
    t, _ = verify.scrub_numbers(t, quotes)
    sids = E.claim_sources(bag, claim_ids)
    kinds = [(bag["sources"].get(s) or {}).get("kind") for s in sids]
    statuses = [bag["claims"][c]["status"] for c in claim_ids]
    check = any(s not in ("matched", "confirmed") for s in statuses) or "[00]" in t
    return {"text": t[:120], "claim_ids": claim_ids, "tbd": False, "sources": len(sids), "has_kb": any(k in E.KB_KINDS for k in kinds), "check": check}


def fact_texts(facts: dict[str, Any]) -> dict[str, str]:
    return {config.fact_label(k): (facts.get(k) or {}).get("text") or TBD for k in config.fact_order()}


# ── 판정 ─────────────────────────────────────────────────
def _match_criterion(name: str, criteria: list[dict[str, Any]]) -> dict[str, Any] | None:
    n = verify.N(name)
    for c in criteria:
        if verify.N(c["name"]) == n:
            return c
    best, score = None, 0.0
    for c in criteria:
        s = fuzz.ratio(n, verify.N(c["name"]))
        if s > score:
            best, score = c, s
    return best if score >= 80 else None


async def judge(doc: dict[str, Any], bag: dict[str, Any], cmp: dict[str, Any], facts: dict[str, Any], criteria: list[dict[str, Any]],
                cells: dict[str, Any], budget: aix.Budget | None) -> list[dict[str, Any]]:
    by_crit: dict[str, dict[str, Any]] = {}
    try:
        out = await aix.llm("ca.verdicts", prompts.verdicts(cmp.get("real_name") or cmp["letter"], criteria, fact_texts(facts),
                                                             {k: v.get("text") for k, v in cells.items()}),
                            prompts.VerdictsOut, confidential=True, budget=budget)
        for row in out.rows:
            c = _match_criterion(row.criterion, criteria)
            if c and c["id"] not in by_crit:
                by_crit[c["id"]] = {"verdict": row.verdict, "rationale": row.rationale}
    except aix.LLMFailed as exc:
        log.info("판정 LLM 실패 → 모두 unknown: %s", exc.message)
    quotes = [q for k in config.fact_order() for q in E.claim_quotes(bag, (facts.get(k) or {}).get("claim_ids") or [])]
    rows = []
    for c in criteria:
        got = by_crit.get(c["id"]) or {"verdict": "unknown", "rationale": ""}
        keys = fact_keys_for(c["name"])
        comp_tbd = all((facts.get(k) or {}).get("tbd", True) for k in keys)
        cell = cells.get(c["id"]) or {"tbd": True}
        v = got["verdict"]
        if comp_tbd or cell.get("tbd"):
            v = "unknown"
        rationale, _ = verify.scrub_numbers(got.get("rationale") or "", quotes + E.claim_quotes(bag, cell.get("claim_ids") or []))
        claim_ids = [cid for k in keys for cid in (facts.get(k) or {}).get("claim_ids") or []] + list(cell.get("claim_ids") or [])
        rows.append({"criterion_id": c["id"], "competitor_id": cmp["id"], "verdict": v, "rationale": rationale[:120], "claim_ids": claim_ids})
    return rows


async def positioning(bag: dict[str, Any], cmp: dict[str, Any], facts: dict[str, Any], budget: aix.Budget | None) -> dict[str, Any]:
    quotes = [q for k in config.fact_order() for q in E.claim_quotes(bag, (facts.get(k) or {}).get("claim_ids") or [])]
    claim_ids = [cid for k in ("lineup", "solution") for cid in (facts.get(k) or {}).get("claim_ids") or []]
    known = [facts[k]["text"] for k in ("lineup", "solution", "references") if not (facts.get(k) or {}).get("tbd", True)]
    if not known:
        return {"text": cmp.get("kind_label") or TBD, "claim_ids": []}
    try:
        out = await aix.llm("ca.positioning", prompts.positioning(cmp.get("real_name") or cmp["letter"], fact_texts(facts)), prompts.PositioningOut,
                            confidential=True, budget=budget)
        text, removed = verify.scrub_numbers(out.text.strip(), quotes)
        if text and not removed:
            return {"text": text[: int(config.routing().get("positioning_max", 40))], "claim_ids": claim_ids}
    except aix.LLMFailed:
        pass
    return {"text": " · ".join(known)[: int(config.routing().get("positioning_max", 40))], "claim_ids": claim_ids}


# ── 강점 · 주의할 점(§7.7) ───────────────────────────────
async def strengths_cautions(doc: dict[str, Any], bag: dict[str, Any], competitors: list[dict[str, Any]], criteria: list[dict[str, Any]],
                             verdicts: list[dict[str, Any]], cells: dict[str, Any], facts: dict[str, dict[str, Any]], *,
                             use_llm: bool = True) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rs = config.routing()
    picks = rules.pick_strengths(criteria, verdicts, max_n=int((rs.get("strengths") or {}).get("max", 3)))
    cpicks = rules.pick_cautions(criteria, verdicts, competitors, max_n=int((rs.get("cautions") or {}).get("max", 2)))
    letter = {c["id"]: c["letter"] for c in competitors}
    texts: dict[str, Any] = {}
    ctexts: dict[str, str] = {}
    if use_llm and (picks or cpicks):
        try:
            out = await aix.llm("ca.strengths", prompts.strengths(
                [{"name": p["criterion"]["name"], "samsung": (cells.get(p["criterion"]["id"]) or {}).get("text") or TBD,
                  "wins": len(p["competitor_ids"])} for p in picks],
                [{"letter": letter.get(p["competitor_id"], "?"), "name": p["criterion"]["name"],
                  "fact": " · ".join((facts.get(p["competitor_id"]) or {}).get(k, {}).get("text") or TBD for k in fact_keys_for(p["criterion"]["name"]))}
                 for p in cpicks]), prompts.StrengthsOut, confidential=True)
            for s in out.strengths:
                c = _match_criterion(s.criterion, [p["criterion"] for p in picks])
                if c:
                    texts[c["id"]] = s
            for ct in out.cautions:
                ctexts[ct.letter.strip().upper().removeprefix("경쟁사").strip()] = ct.note
        except aix.LLMFailed:
            pass
    smax = rs.get("strengths") or {}
    strengths = []
    for p in picks:
        crit = p["criterion"]
        cell = cells.get(crit["id"]) or {}
        quotes = E.claim_quotes(bag, cell.get("claim_ids") or [])
        t = texts.get(crit["id"])
        title = (t.title.strip() if t and t.title.strip() else crit["name"])[: int(smax.get("title_max", 12))]
        note_raw = t.note.strip() if t and t.note.strip() else (cell.get("text") or TBD)
        note, _ = verify.scrub_numbers(note_raw, quotes)
        strengths.append({"title": title, "note": note[: int(smax.get("note_max", 30))], "criterion_ids": [crit["id"]],
                          "competitor_ids": p["competitor_ids"], "claim_ids": list(cell.get("claim_ids") or []), "score": p["score"]})
    cautions = []
    for p in cpicks:
        crit = p["criterion"]
        cf = facts.get(p["competitor_id"]) or {}
        keys = fact_keys_for(crit["name"])
        claim_ids = [cid for k in keys for cid in (cf.get(k) or {}).get("claim_ids") or []]
        quotes = E.claim_quotes(bag, claim_ids)
        L = letter.get(p["competitor_id"], "?")
        fact_txt = next((cf[k]["text"] for k in keys if not (cf.get(k) or {}).get("tbd", True)), crit["name"])
        raw = ctexts.get(L) or f"{fact_txt} · {crit['name']}에서 불리할 수 있어요"
        note, _ = verify.scrub_numbers(raw, quotes)
        cautions.append({"competitor_id": p["competitor_id"], "note": note[:60], "criterion_ids": [crit["id"]], "claim_ids": claim_ids})
    return strengths, cautions


# ── 집계 · 버전 문서 ─────────────────────────────────────
def counts_for(bag: dict[str, Any], cmp_id: str, verdicts: list[dict[str, Any]], facts: dict[str, Any]) -> dict[str, int]:
    mine = [v for v in verdicts if v.get("competitor_id") == cmp_id]
    ids = [cid for k in config.fact_order() for cid in (facts.get(k) or {}).get("claim_ids") or []]
    return {"up": sum(1 for v in mine if v["verdict"] == "samsung_better"), "eq": sum(1 for v in mine if v["verdict"] == "similar"),
            "dn": sum(1 for v in mine if v["verdict"] == "samsung_worse"), "unknown": sum(1 for v in mine if v["verdict"] == "unknown"),
            "sources": len(E.claim_sources(bag, ids))}


def build_version(doc: dict[str, Any], work: dict[str, Any], *, competitor_ids: list[str], criteria: list[dict[str, Any]], strengths: list[dict[str, Any]],
                  cautions: list[dict[str, Any]], kind: str, stopped: bool = False, summary: str = "") -> dict[str, Any]:
    """작업본 → 결과 버전 문서(분석한 경쟁사만, 그 주장 · 인용 · 출처만 복사)."""
    comps = {c["id"]: c for c in doc.get("competitors") or []}
    wc = work.get("competitors") or {}
    facts = {cid: copy.deepcopy((wc.get(cid) or {}).get("facts") or {}) for cid in competitor_ids}
    pos = {cid: copy.deepcopy((wc.get(cid) or {}).get("positioning") or {"text": "", "claim_ids": []}) for cid in competitor_ids}
    crit_ids = {c["id"] for c in criteria}
    verdicts = [v for cid in competitor_ids for v in (wc.get(cid) or {}).get("verdicts") or [] if v.get("criterion_id") in crit_ids]
    cells = {k: v for k, v in (work.get("samsung_cells") or {}).items() if k in crit_ids}
    keep_claims: set[str] = set()
    for cid in competitor_ids:
        for f in facts[cid].values():
            keep_claims.update(f.get("claim_ids") or [])
    for cell in cells.values():
        keep_claims.update(cell.get("claim_ids") or [])
    claims = {k: copy.deepcopy(v) for k, v in (work.get("claims") or {}).items() if k in keep_claims}
    citations = [copy.deepcopy(c) for c in work.get("citations") or [] if c.get("claim_id") in keep_claims]
    sids = {c["source_id"] for c in citations}
    sources = {k: copy.deepcopy(v) for k, v in (work.get("sources") or {}).items() if k in sids}
    bag = {"claims": claims, "citations": citations, "sources": sources}
    counts = {cid: counts_for(bag, cid, verdicts, facts[cid]) for cid in competitor_ids}
    f = E.footer(bag)
    return {
        "kind": kind, "stopped": stopped, "created_at": now_iso(), "summary": summary,
        "competitor_ids": competitor_ids,
        "competitors": {cid: {k: comps.get(cid, {}).get(k) for k in ("letter", "real_name", "aliases", "kind_label", "why", "confidence", "origin",
                                                                    "pinned", "status")} | {"state": (wc.get(cid) or {}).get("state") or "done"}
                        for cid in competitor_ids},
        "criteria": [{k: c.get(k) for k in ("id", "name", "source", "source_count", "importance", "order", "enabled", "pinned")} for c in criteria],
        "facts": facts, "positioning": pos, "samsung_cells": cells, "verdicts": verdicts, "counts": counts, "strengths": strengths,
        "cautions": cautions, "footer": f, "chips": list(doc.get("chips") or []), "claims": claims, "citations": citations, "sources": sources,
        "samsung_products": list(work.get("samsung_products") or []),
    }
