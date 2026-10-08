"""솔루션 카탈로그 · 상세 · 이미지 · 활용 사례(00-shell §7.2.9 ~ §7.2.12).

카탈로그 11개는 큐레이션(curation/solutions.yaml, 갭 G-SOL-1). KB 에만 있는 솔루션(sol_samsung_health 등 5개)은
목록에 넣지 않지만(Q-KB-5) `GET /v1/solutions/sol_…` 로는 열 수 있다(제품 시트 지원 솔루션 링크용).
"""
from __future__ import annotations

import collections
import re
from functools import lru_cache
from typing import Any

from winmate_common.errors import not_found

from . import cases as C
from . import curation, imagecards
from .engine import kb, q
from .index import idx, jloads, norm


@lru_cache(maxsize=1)
def catalog() -> list[dict[str, Any]]:
    return list(curation.load("solutions").get("solutions") or [])


def catalog_by_id() -> dict[str, dict[str, Any]]:
    return {s["id"]: s for s in catalog()}


@lru_cache(maxsize=1)
def catalog_by_kb() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for s in catalog():
        for k in s.get("kb_ids") or []:
            out.setdefault(k, s)
    return out


def _kb_only(sol_id: str) -> dict[str, Any] | None:
    s = idx().solutions.get(sol_id)
    if not s:
        return None
    kinds = curation.load("display").get("solution_kind_labels") or {}
    return {"id": sol_id, "name": s["name_ko"] or sol_id, "domain": kinds.get(s["kind"] or "", s["kind"] or "솔루션"),
            "desc": "", "icon": "", "template_code": None, "kb_ids": [sol_id], "kb_match": "kb_only",
            "title_aliases": [], "category_path": [kinds.get(s["kind"] or "", "솔루션")], "subtitle": None,
            "purchase_note": "견적 문의 ({site_code}) · 단가 [견적 확인]"}


def resolve(ident: str) -> dict[str, Any] | None:
    """카탈로그 id(magicinfo) · KB id(sol_magicinfo) · 'kb:solution:…' → 카탈로그 항목(또는 KB 전용 항목)."""
    if not ident:
        return None
    if ident.startswith("kb:solution:"):
        ident = ident.split(":", 2)[2]
    cat = catalog_by_id().get(ident)
    if cat:
        return cat
    cat = catalog_by_kb().get(ident)
    if cat:
        return cat
    return _kb_only(ident)


@lru_cache(maxsize=1)
def _featured() -> dict[str, set[str]]:
    out: dict[str, set[str]] = collections.defaultdict(set)
    for r in q("SELECT src_id, dst_id FROM kg_edge WHERE rel='FEATURED_BY_SITE' AND dst_kind='solution'"):
        out[r["dst_id"]].add(r["src_id"])
    return out


def industries(sol: dict[str, Any]) -> list[str]:
    chips = curation.load("solutions").get("industry_chips") or {}
    vs = set().union(*[_featured().get(k, set()) for k in sol.get("kb_ids") or []]) if sol.get("kb_ids") else set()
    return [key for key, c in chips.items() if vs & set(c["verticals"])]


def list_item(sol: dict[str, Any]) -> dict[str, Any]:
    kb_ids = sol.get("kb_ids") or []
    return {"id": sol["id"], "name": sol["name"], "domain": sol.get("domain") or "", "desc": sol.get("desc") or "",
            "icon": sol.get("icon") or "", "template_code": sol.get("template_code"), "kb_id": kb_ids[0] if kb_ids else None,
            "industries": industries(sol), "kb_ids": kb_ids, "kb_match": sol.get("kb_match")}


def _aliases(sol: dict[str, Any]) -> list[str]:
    I = idx()
    al = [sol["name"]] + list(sol.get("title_aliases") or [])
    for k in sol.get("kb_ids") or []:
        s = I.solutions.get(k)
        if s:
            al += [s["name_ko"]] + list(jloads(s["aliases_json"], []) or [])
    out = []
    for a in al:
        if a and a not in out:
            out.append(a)
    return out


def _text_aliases(sol: dict[str, Any]) -> list[str]:
    """글자 일치용 이름 — 짧은 영문(2~4자, 예 DeX)은 단어 경계로만 쓰도록 길이 3 이상만 LIKE 에 넘긴다."""
    out = []
    for a in _aliases(sol) + list(sol.get("text_aliases") or []):
        if a and len(a.strip()) >= 3 and a not in out:
            out.append(a.strip())
    return out


def _word_ok(alias: str, text: str) -> bool:
    if re.fullmatch(r"[A-Za-z.]{2,4}", alias):
        return bool(re.search(r"(?<![A-Za-z])" + re.escape(alias) + r"(?![A-Za-z])", text or ""))
    return alias.lower() in (text or "").lower()


def _text_match_images(sol: dict[str, Any], exclude: set[str], limit: int = 12) -> list[str]:
    """KB 에 솔루션 id 가 없을 때 — alt · 캡션 · 섹션 글에 이름이 나오는 이미지(등급 A · A?C · C, 아이콘 제외)."""
    I = idx()
    hits: list[str] = []
    for a in _text_aliases(sol):
        for r in q("SELECT asset_id, text FROM image_doc WHERE text LIKE ? LIMIT 400", (f"%{a}%",)):
            aid = r["asset_id"]
            asset = I.assets.get(aid)
            if not asset or aid in exclude or aid in hits or asset["grade_hint"] not in ("A", "A?C", "C"):
                continue
            if _word_ok(a, r["text"]):
                hits.append(aid)
    pri = {"A": 0, "A?C": 1, "C": 2}
    hits.sort(key=lambda a: pri.get(I.assets[a]["grade_hint"], 9))
    return hits[:limit]


def search(text: str | None, industry: str | None) -> list[dict[str, Any]]:
    sols = list(catalog())
    if industry:
        chips = curation.load("solutions").get("industry_chips") or {}
        if industry not in chips:
            from winmate_common.errors import ApiError

            raise ApiError(400, "UNSUPPORTED_FILTER", f"지원하지 않는 업종 칩: {industry}",
                           {"filters": ["industry"], "allowed": list(chips)})
        sols = [s for s in sols if industry in industries(s)]
    t = (text or "").strip()
    if not t:
        return [list_item(s) for s in sols]
    nt = norm(t)
    hit: list[dict[str, Any]] = []
    for s in sols:
        if any(nt and (nt in norm(a) or (len(norm(a)) >= 3 and norm(a) in nt)) for a in _aliases(s)) or nt in norm(s.get("desc")):
            hit.append(s)
    if len(nt) >= 2:
        # 해결 과제 문장 → E2 메시지의 about 솔루션
        msgs = kb().E2(t, limit=40)["result"]["messages"]
        allowed = {s["id"] for s in sols}
        for m in msgs:
            if m["score"] < 0.2:
                continue
            kind, ident = m["about"]
            if kind != "solution":
                continue
            cat = catalog_by_kb().get(ident)
            if cat and cat["id"] in allowed and cat not in hit:
                hit.append(cat)
    return [list_item(s) for s in hit]


# ── 상세 ─────────────────────────────────────────────────

def _supported_devices(sol: dict[str, Any]) -> dict[str, Any] | None:
    I = idx()
    kb_ids = sol.get("kb_ids") or []
    if not kb_ids:
        return None
    ph = ",".join("?" * len(kb_ids))
    rows = q(f"""SELECT document_id, count(*) n FROM mention WHERE resolved_kind='solution' AND resolved_id IN ({ph})
                 AND document_id LIKE 'doc_pdp_%' GROUP BY document_id ORDER BY n DESC, document_id""", kb_ids)
    fams = []
    for r in rows:
        fid = I.doc_family(r["document_id"])
        if fid and fid not in fams:
            fams.append(fid)
    if not fams:
        return None
    sd = sol.get("supported_devices") or {}
    label = sd.get("label")
    if not label:
        cnt = collections.Counter(I.fam_l2(f) for f in fams if I.fam_l2(f))
        top = cnt.most_common(1)[0][0] if cnt else None
        label = f"삼성 {I.cat_name(top)}" if top else "삼성 제품"
    ex_fid = sd.get("example_family_id") if sd.get("example_family_id") in fams else fams[0]
    mid = I.default_model(ex_fid)
    example = None
    if mid:
        example = {"family_id": ex_fid, "series_label": I.series_label(ex_fid), "model_code": I.models[mid]["model_code"],
                   "display_name": I.display_name(mid)[0]}
    return {"label": label, "example": example, "family_ids": fams}


def _text_messages(sol: dict[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    """KB 에 솔루션 id 가 없을 때 — 원문 메시지 중 이름이 나오는 문장(about 이 다른 대상이어도), basis=text_match."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for a in _text_aliases(sol):
        rows = q("""SELECT v.text, v.level, v.claim_flag, d.url FROM value_prop v LEFT JOIN occurrence o ON o.id=v.source_occurrence_id
                    LEFT JOIN source_document d ON d.id=o.document_id WHERE v.text LIKE ? AND v.locale='ko-KR' LIMIT 200""", (f"%{a}%",))
        for r in rows:
            t = r["text"]
            if t in seen or not _word_ok(a, t):
                continue
            seen.add(t)
            out.append({"level": r["level"] or "key_message", "text": t, "children": [], "source_url": r["url"],
                        "claim_flag": bool(r["claim_flag"]), "basis": "text_match"})
    lv = {"tagline": 0, "key_message": 1, "usp": 2, "proof_point": 3}
    out.sort(key=lambda m: lv.get(m["level"], 9))
    return out[:limit]


def _messages(sol: dict[str, Any]) -> list[dict[str, Any]]:
    kb_ids = sol.get("kb_ids") or []
    if not kb_ids:
        return _text_messages(sol)
    tree = kb().E1(about=[("solution", k) for k in kb_ids])["result"].get("tree") or {}
    out = []
    for t in tree.get("taglines") or []:
        out.append({"level": "tagline", "text": t["text"], "children": [], "source_url": t.get("source_url"), "claim_flag": bool(t.get("claim_flag"))})
    for k in tree.get("key_messages") or []:
        out.append({"level": k.get("level") or "key_message", "text": k["text"],
                    "children": [p["text"] for p in k.get("proof_points") or []], "source_url": k.get("source_url"),
                    "claim_flag": bool(k.get("claim_flag"))})
    for u in tree.get("usps") or []:
        out.append({"level": "usp", "text": u["text"], "children": [], "source_url": u.get("source_url"), "claim_flag": bool(u.get("claim_flag"))})
    return out


def _profile(sol: dict[str, Any]) -> dict[str, Any] | None:
    p = sol.get("profile")
    if not p:
        return None
    I = idx()
    deploy = []
    for d in p.get("deploy") or []:
        did = d.get("evidence_deployment_id")
        ev = None
        if did and did in I.deps:
            ev = {"deployment_id": did, "title": I.deps[did]["title"], "date": I.deps[did]["date"]}
        deploy.append({"name": d["name"], "desc": d["desc"], "evidence": ev})
    return {"intro": p["intro"], "pillars": p.get("pillars") or [], "parts": p.get("parts") or [], "deploy": deploy,
            "device_functions": p.get("device_functions") or [], "source_note": p.get("source_note") or ""}


def case_ids(sol: dict[str, Any]) -> tuple[list[str], list[str]]:
    """(제목에 명시, 본문 언급) — kg_edge(USES · MENTIONS → 솔루션) ∪ 제목에 이름 · 별칭, 본문 있는 사례만, 날짜 내림차순."""
    I = idx()
    kb_ids = set(sol.get("kb_ids") or [])
    body = set(I.body_deployments())
    by_edge = {d for d, t in I.dep_targets.items() if any(k == "solution" and i in kb_ids for k, i in t)}
    pats = []
    for a in _aliases(sol):
        if re.fullmatch(r"[A-Za-z.]{2,4}", a):
            pats.append(("re", re.compile(r"(?<![A-Za-z])" + re.escape(a) + r"(?![A-Za-z])", re.I)))
        elif len(norm(a)) >= 3:
            pats.append(("norm", norm(a)))
    by_title = set()
    for did in body:
        t = I.deps[did]["title"] or ""
        nt = norm(t)
        for kind, p in pats:
            if (kind == "re" and p.search(t)) or (kind == "norm" and p in nt):
                by_title.add(did)
                break
    by_text: set[str] = set()
    if not kb_ids:                       # KB 에 솔루션 id 가 없으면 사례 본문 글자로(G-SOL-1 보완)
        doc_dep = {I.deps[d]["document_id"]: d for d in body if I.deps[d]["document_id"]}
        for a in _text_aliases(sol):
            for r in q("SELECT DISTINCT document_id, text FROM text_chunk WHERE text LIKE ?", (f"%{a}%",)):
                did = doc_dep.get(r["document_id"])
                if did and _word_ok(a, r["text"]):
                    by_text.add(did)
    union = (by_edge | by_title | by_text) & body

    def by_date(ids: set[str]) -> list[str]:
        return sorted(ids, key=lambda d: I.deps[d]["date"] or "", reverse=True)

    return by_date(by_title & union), by_date(union - by_title)


def detail(ident: str) -> dict[str, Any]:
    I = idx()
    sol = resolve(ident)
    if sol is None:
        raise not_found("솔루션", ident)
    kb_ids = sol.get("kb_ids") or []
    ks = [I.solutions[k] for k in kb_ids if k in I.solutions]
    site_codes = [s["site_code"] for s in ks if s["site_code"]]
    purchase = None
    if ks:
        note = sol.get("purchase_note") or "견적 문의 ({site_code}) · 단가 [견적 확인]"
        purchase = {"site_code": " · ".join(site_codes) or None, "label": note.format(site_code=" · ".join(site_codes) or "[확인 필요]")}
    docs = [I.docs[s["document_id"]] for s in ks if s["document_id"] in I.docs]
    verified = max((d["fetched_at"] for d in docs if d["fetched_at"]), default=None)
    title_ids, body_ids = case_ids(sol)
    imgs = images(sol)
    gaps = []
    if not ks:
        gaps.append("G-SOL-1")
    if not sol.get("profile"):
        gaps.append("G-SOL-2")
    if not sol.get("intro_url"):
        gaps.append("G-SOL-3")
    return {
        "id": sol["id"], "name": sol["name"], "version_label": sol.get("version_label"),
        "category_path": list(sol.get("category_path") or []), "subtitle": sol.get("subtitle"),
        "key_chips": list(sol.get("key_chips") or []), "purchase": purchase,
        "quote_url": ks[0]["url"] if ks and ks[0]["url"] and not ks[0]["url"].startswith("<<") else None,
        "intro_url": sol.get("intro_url"), "supported_devices": _supported_devices(sol), "profile": _profile(sol),
        "messages": _messages(sol), "verified_at": verified,
        "counts": {"images": imgs["total"], "cases": len(title_ids) + len(body_ids)},
        "kb_id": kb_ids[0] if kb_ids else None, "kb_ids": kb_ids, "template_code": sol.get("template_code"),
        "proposal_templates": sol.get("proposal"), "gaps": gaps,
    }


def images(sol: dict[str, Any], case_limit: int = 4, context_limit: int = 12) -> dict[str, Any]:
    """official = KB 의 솔루션 페이지 이미지(아이콘 E 제외 — 소개 페이지 이미지는 갭 G-SOL-3),
    context = 다른 공식 페이지에서 이 솔루션이 나오는 이미지(묘사 · 추정 묘사 · 이름 일치, 최대 12),
    case = 활용 사례 대표 사진 1장씩(최대 4)."""
    I = idx()
    kb_ids = sol.get("kb_ids") or []
    groups = []
    official = []
    titles = []
    for k in kb_ids:
        s = I.solutions.get(k)
        if not s or not s["document_id"]:
            continue
        doc = s["document_id"]
        if I.docs.get(doc):
            titles.append(imagecards.clean_title(I.docs[doc]["title"]) or "")
        seen_rows = q("SELECT asset_id FROM image_occurrence o LEFT JOIN document_block b ON b.id=o.block_id WHERE o.document_id=? ORDER BY b.seq", (doc,))
        for r in seen_rows:
            a = I.assets.get(r["asset_id"])
            if not a or a["grade_hint"] == "E" or a["media_type"] not in ("image", "animation", None):
                continue
            if any(x["id"] == r["asset_id"] for x in official):
                continue
            m = imagecards.meta(r["asset_id"], prefer_doc=doc)
            if m:
                official.append(m)
    groups.append({"key": "official", "label": "공식 소개 이미지",
                   "source_label": "samsung.com " + (" · ".join(t for t in titles if t) or sol["name"]), "items": official})
    # 공간 · 업종 페이지에서 이 솔루션이 나오는 이미지(묘사 · 추정 묘사, KB id 가 없으면 글자 일치) — 사례 사진은 아래 묶음
    ctx_ids: list[str] = []
    have = {x["id"] for x in official}
    if kb_ids:
        ph = ",".join("?" * len(kb_ids))
        rows = q(f"""SELECT asset_id a FROM depicts WHERE target_kind='solution' AND target_id IN ({ph})
                     UNION SELECT src_id a FROM kg_edge WHERE rel='DEPICTS_PROBABLE' AND dst_kind='solution' AND dst_id IN ({ph})""",
                 list(kb_ids) + list(kb_ids))
        pri = {"A": 0, "A?C": 1, "C": 2, "D": 3}
        cand = [r["a"] for r in rows if r["a"] in I.assets and r["a"] not in have and I.assets[r["a"]]["grade_hint"] in pri
                and I.assets[r["a"]]["rights"] != "customer_case"]
        cand.sort(key=lambda a: pri.get(I.assets[a]["grade_hint"], 9))
        ctx_ids = cand
    if len(ctx_ids) < 4:
        ctx_ids += [a for a in _text_match_images(sol, have | set(ctx_ids)) if I.assets[a]["rights"] != "customer_case"]
    ctx_items = []
    for aid in dict.fromkeys(ctx_ids):
        m = imagecards.meta(aid)
        if m:
            ctx_items.append(m)
        if len(ctx_items) >= context_limit:
            break
    if ctx_items:
        groups.append({"key": "context", "label": "공간 · 업종 페이지 이미지",
                       "source_label": "samsung.com 공간 · 업종 · 제품 페이지" + ("" if kb_ids else " · 이름 일치(확인 필요)"), "items": ctx_items})
    title_ids, body_ids = case_ids(sol)
    case_items = []
    for did in title_ids + body_ids:
        ph = I.dep_photos.get(did)
        if not ph:
            continue
        m = imagecards.meta(ph[0], prefer_doc=I.deps[did]["document_id"])
        if m:
            case_items.append(m)
        if len(case_items) >= case_limit:
            break
    groups.append({"key": "case", "label": "도입사례 사진", "source_label": "samsung.com 고객 도입사례", "items": case_items})
    return {"groups": groups, "total": sum(len(g["items"]) for g in groups)}


def cases_out(ident: str) -> dict[str, Any]:
    I = idx()
    sol = resolve(ident)
    if sol is None:
        raise not_found("솔루션", ident)
    title_ids, body_ids = case_ids(sol)
    return {"corpus": C.corpus(), "total": len(title_ids) + len(body_ids),
            "title_explicit": [C.card(d) for d in title_ids],
            "body_mentions": [{"id": d, "title": I.deps[d]["title"], "date": I.deps[d]["date"], "url": I.deps[d]["url"]} for d in body_ids]}
