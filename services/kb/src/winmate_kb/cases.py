"""도입사례: CaseCard · 사례 검색 · 사례 상세 · 제품 시트 활용 사례(00-shell §7.2.1 · §7.2.8 · §7.2.15 · §7.2.16)."""
from __future__ import annotations

import collections
import datetime as dt
import re
from typing import Any

from winmate_common.errors import ApiError, bad_request

from . import curation, imagecards
from .engine import kb, q
from .index import idx, norm

KST = dt.timezone(dt.timedelta(hours=9))
NOISE_ITEM = re.compile(r"^(img|image|이미지|사진)$|아이콘", re.I)


def today_kst() -> dt.date:
    return dt.datetime.now(KST).date()


def url_display(url: str | None) -> str | None:
    if not url:
        return None
    u = re.sub(r"^https?://(www\.)?", "", url)
    return u.rstrip("/")


def _ref(kind: str | None, ident: str | None) -> str | None:
    if not kind or not ident:
        return None
    if kind == "solution":
        from .solutions import catalog_by_kb

        cat = catalog_by_kb().get(ident)
        return f"kb:solution:{cat['id'] if cat else ident}"
    return f"kb:{kind}:{ident}"


def _target_label(kind: str, ident: str) -> str:
    I = idx()
    if kind == "solution":
        from .solutions import catalog_by_kb

        cat = catalog_by_kb().get(ident)
        if cat:
            return cat["name"]
    if kind == "model" and ident in I.models:
        return I.display_name(ident)[0]
    return str(kb().name(kind, ident))


def products(did: str) -> list[dict[str, Any]]:
    """deployment_item: 해소된 대상 이름 우선, case_related_link(T2) → prior_llm_offer(T5), 이미지 alt 같은 잡음 제외."""
    rows = q("""SELECT item_raw, target_kind, target_id, source, source_tier FROM deployment_item WHERE deployment_id=?
                ORDER BY CASE source WHEN 'case_related_link' THEN 0 ELSE 1 END, rowid""", (did,))
    out, seen = [], set()
    for r in rows:
        raw = (r["item_raw"] or "").strip()
        if r["target_id"]:
            label = _target_label(r["target_kind"], r["target_id"])
            ref = _ref(r["target_kind"], r["target_id"])
        else:
            if not raw or NOISE_ITEM.search(raw) or len(raw) > 40:
                continue
            label, ref = raw, None
        key = ref or norm(label)
        if key in seen or norm(label) in seen:
            continue
        seen.add(key)
        seen.add(norm(label))
        out.append({"label": label, "ref": ref, "tier": r["source_tier"]})
    return out


def tag_detail(did: str) -> str | None:
    short = curation.load("display").get("space_short") or {}
    for sp in idx().dep_spaces.get(did, []):
        if sp in short:
            return short[sp]
    return None


def card(did: str, match: dict[str, Any] | None = None, photos_all: bool = False,
         prefer_verticals: set[str] | None = None) -> dict[str, Any]:
    I = idx()
    d = I.deps[did]
    verts = I.dep_verts.get(did) or []
    v = verts[0] if verts else None
    if prefer_verticals:            # 업종 필터가 걸려 있으면 그 업종을 태그로(사례가 여러 업종일 때)
        v = next((x for x in verts if x in prefer_verticals), v)
    aids = I.dep_photos.get(did, [])
    shown = aids if photos_all else aids[:3]
    doc = d["document_id"]
    return {
        "id": did, "title": d["title"], "date": d["date"], "url": d["url"], "url_display": url_display(d["url"]),
        "vertical": {"id": v, "name": I.vertical_name(v) or v} if v else None,
        "tag_detail": tag_detail(did), "summary": None, "quote": d["quote"] or None,
        "products": products(did),
        "photos": {"count": len(aids), "items": [c for c in (imagecards.card(a, prefer_doc=doc) for a in shown) if c]},
        "match": match, "source_tier": d["source_tier"], "format": d["format"],
    }


# ── 사례 본문(일치 단어용) ─────────────────────────────────

_body_cache: dict[str, str] = {}


def body_text(did: str) -> str:
    hit = _body_cache.get(did)
    if hit is not None:
        return hit
    I = idx()
    d = I.deps[did]
    parts = [d["title"] or "", d["customer_type"] or "", d["quote"] or ""]
    if d["document_id"]:
        parts += [r["text"] or "" for r in q("SELECT text FROM text_chunk WHERE document_id=?", (d["document_id"],))]
    parts += [r["need_raw"] or "" for r in q("SELECT need_raw FROM deployment_need WHERE deployment_id=?", (did,))]
    s = "\n".join(parts)
    _body_cache[did] = s
    return s


def match_terms(did: str, tokens: list[str]) -> list[str]:
    """갭 G-CASE-3 [제안]: 검색어 토큰 중 사례 본문 · 요구에 나온 것 최대 2개."""
    if not tokens:
        return []
    body = body_text(did)
    return [t for t in tokens if t in body][:2]


# ── 대상(제품 칩) 필터 ─────────────────────────────────────

def target_set(target: str) -> tuple[set[tuple[str, str]], list[tuple[str, str]]]:
    """'family:fam_…' · 'solution:sol_…|magicinfo' · 'category:cat_…' · 'model:…' → (사례가 가리킬 수 있는 대상 집합, D1 대상)."""
    I = idx()
    if ":" not in target:
        raise bad_request("target 형식은 '<kind>:<id>' 입니다", target=target)
    kind, ident = target.split(":", 1)
    out: set[tuple[str, str]] = set()
    d1: list[tuple[str, str]] = []
    if kind == "family":
        if ident not in I.fams:
            raise ApiError(404, "NOT_FOUND", f"제품군을 찾을 수 없습니다: {ident}", {"resource": "family", "id": ident})
        out.add(("family", ident))
        out |= {("model", m) for m in I.fam_models.get(ident, [])}
        d1.append(("family", ident))
    elif kind == "model":
        mid = I.resolve_model(ident)
        if not mid:
            raise ApiError(404, "NOT_FOUND", f"모델을 찾을 수 없습니다: {ident}", {"resource": "model", "id": ident})
        out |= {("model", mid), ("family", I.models[mid]["family_id"])}
        d1.append(("family", I.models[mid]["family_id"]))
    elif kind == "category":
        if ident not in I.cats:
            raise ApiError(404, "NOT_FOUND", f"분류를 찾을 수 없습니다: {ident}", {"resource": "category", "id": ident})
        sub = I.cat_subtree(ident)
        out |= {("category", c) for c in sub}
        fams = {f for c in sub for f in I.cat_fams.get(c, set())}
        out |= {("family", f) for f in fams}
        d1.append(("category", ident))
    elif kind == "solution":
        from .solutions import resolve

        sol = resolve(ident)
        if sol is None:
            raise ApiError(404, "NOT_FOUND", f"솔루션을 찾을 수 없습니다: {ident}", {"resource": "solution", "id": ident})
        out |= {("solution", k) for k in sol["kb_ids"]}
        d1 += [("solution", k) for k in sol["kb_ids"]]
    else:
        raise bad_request("target 종류는 family · model · category · solution 중 하나입니다", target=target)
    return out, d1


def _period_cutoff(period: str | None) -> str | None:
    if not period or period == "all":
        return None
    m = re.fullmatch(r"(\d+)y", period)
    if not m:
        raise bad_request("period 는 all · 1y · 3y · 5y 중 하나입니다", period=period)
    n = int(m.group(1))
    t = today_kst()
    try:
        cut = t.replace(year=t.year - n)
    except ValueError:  # 2월 29일
        cut = t.replace(year=t.year - n, day=28)
    return cut.isoformat()


def corpus(period: str | None = None) -> dict[str, Any]:
    I = idx()
    cut = _period_cutoff(period)
    ids = [d for d in I.body_deployments() if not cut or (I.deps[d]["date"] or "") >= cut]
    return {"count": len(ids), "checked_at": I.checked_at}


def search(text: str | None, vertical_id: str | None, target: str | None, period: str | None,
           infer_vertical: bool, vertical_from: str = "user") -> tuple[list[tuple[str, dict[str, Any] | None]], dict[str, Any], dict[str, Any]]:
    """→ ([(사례 id, match)], corpus, applied)."""
    I = idx()
    k = kb()
    cut = _period_cutoff(period)
    pool = [d for d in I.body_deployments() if not cut or (I.deps[d]["date"] or "") >= cut]
    corp = {"count": len(pool), "checked_at": I.checked_at}
    text = (text or "").strip() or None
    applied = None
    if vertical_id:
        if vertical_id not in I.verticals:
            raise ApiError(404, "NOT_FOUND", f"업종을 찾을 수 없습니다: {vertical_id}", {"resource": "vertical", "id": vertical_id})
        applied = {"id": vertical_id, "name": I.vertical_name(vertical_id) or vertical_id, "from": vertical_from}
    elif infer_vertical and text:
        a2 = k.A2(text)
        top = (a2["result"].get("top2") or [None])[0]
        if top and a2["decision_hint"] == "auto":
            applied = {"id": top["id"], "name": I.vertical_name(top["id"]) or top["id"], "from": "inferred"}
    if applied:
        vset = I.vertical_expand(applied["id"])
        pool = [d for d in pool if set(I.dep_verts.get(d) or []) & vset]
    d1_targets: list[tuple[str, str]] = []
    if target:
        tset, d1_targets = target_set(target)
        pool = [d for d in pool if I.dep_targets.get(d, set()) & tset]
    spaces: list[str] = []
    if text:
        for l in k.A1(text)["result"]["links"]:
            if l["type"] == "space_type" and l["id"] not in spaces:
                spaces.append(l["id"])
            elif l["type"] in ("family", "category", "solution") and l.get("id") and (l["type"], l["id"]) not in d1_targets:
                d1_targets.append((l["type"], l["id"]))
    if not (text or applied or d1_targets):
        ordered = sorted(pool, key=lambda d: (I.deps[d]["date"] or ""), reverse=True)
        return [(d, None) for d in ordered], corp, {"vertical": applied}
    r = k.D1(vertical=applied["id"] if applied else None, spaces=spaces, targets=d1_targets, text=text, limit=100000)
    allowed = set(pool)
    tokens = k.query_tokens(text) if text else []
    hits = [x for x in r["result"]["deployments"] if x["id"] in allowed]
    hits.sort(key=lambda x: I.deps[x["id"]]["date"] or "", reverse=True)   # 같은 점수면 최신 먼저
    hits.sort(key=lambda x: -x["score"])
    out = [(x["id"], {"score": x["score"], "breakdown": x["similarity_breakdown"], "terms": tokens}) for x in hits]
    return out, corp, {"vertical": applied}


def finish_matches(items: list[tuple[str, dict[str, Any] | None]], applied: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """페이지에 든 사례만 카드로(일치 단어는 이때 계산)."""
    pref = idx().vertical_expand(applied["vertical"]["id"]) if applied and applied.get("vertical") else None
    out = []
    for did, m in items:
        if m is not None:
            m = {**m, "terms": match_terms(did, m.get("terms") or [])}
        out.append(card(did, m, prefer_verticals=pref))
    return out


def detail(did: str) -> dict[str, Any]:
    I = idx()
    if did not in I.deps:
        raise ApiError(404, "NOT_FOUND", f"도입사례를 찾을 수 없습니다: {did}", {"resource": "case", "id": did})
    c = card(did, None, photos_all=True)
    kpis = [{"id": r["id"], "text": r["text"], "has_number": bool(r["has_number"]), "claim_flag": bool(r["claim_flag"]),
             "source_tier": r["source_tier"]} for r in q("SELECT * FROM kpi_claim WHERE deployment_id=? ORDER BY rowid", (did,))]
    needs = [{"kind": r["kind"], "text": r["need_raw"]} for r in q("SELECT kind, need_raw FROM deployment_need WHERE deployment_id=? ORDER BY rowid", (did,))]
    spaces = [{"id": s, "name": (I.space_types.get(s) or {}).get("name_ko") or s} for s in I.dep_spaces.get(did, [])]
    return {**c, "kpis": kpis, "needs": needs, "spaces": spaces}


def similar(did: str, limit: int = 5) -> list[dict[str, Any]]:
    """이 사례와 비슷한 사례(D1: 같은 업종 · 공간 · 제품 + 제목 문장)."""
    I = idx()
    if did not in I.deps:
        raise ApiError(404, "NOT_FOUND", f"도입사례를 찾을 수 없습니다: {did}", {"resource": "case", "id": did})
    d = I.deps[did]
    verts = I.dep_verts.get(did) or []
    targets = sorted(t for t in I.dep_targets.get(did, set()) if t[0] in ("family", "category", "solution"))
    r = kb().D1(vertical=verts[0] if verts else None, spaces=I.dep_spaces.get(did, []), targets=targets, text=d["title"], limit=limit + 20)
    out = []
    for x in r["result"]["deployments"]:
        if x["id"] == did or not I.deps[x["id"]]["document_id"]:
            continue
        out.append(card(x["id"], {"score": x["score"], "breakdown": x["similarity_breakdown"], "terms": []}))
        if len(out) >= limit:
            break
    return out


# ── 제품 시트 · 활용 사례 ─────────────────────────────────

def _case_docs_mentioning(kind: str, ident: str) -> set[str]:
    I = idx()
    out = set()
    for r in q("SELECT DISTINCT document_id FROM mention WHERE resolved_kind=? AND resolved_id=?", (kind, ident)):
        did = I.dep_by_doc.get(r["document_id"])
        if did:
            out.add(did)
    return out


def usage_for_family(fid: str) -> tuple[str | None, str | None, str | None]:
    """갭 G-CASE-5 [제안]: (용도 이름, 공간, 분류) — C3(제품군) 적합 공간 중 장면이 가장 많은 공간 × 제품군 분류 → 용도 사전."""
    I = idx()
    fits = kb().C3(fid)["result"]["fits"]
    agg: dict[str, int] = collections.OrderedDict()
    for f in fits:
        agg[f["space"]] = agg.get(f["space"], 0) + int(f.get("n_sections") or 1)
    if not agg:
        return None, None, I.fam_l2(fid)
    space = sorted(agg.items(), key=lambda x: -x[1])[0][0]
    l2 = I.fam_l2(fid)
    label = None
    for u in curation.load("display").get("usage_labels") or []:
        if u["space"] == space and u["category"] == l2:
            label = u["label"]
            break
    if label is None:
        for u in curation.load("display").get("usage_labels") or []:
            if u["space"] == space and u["category"] == "*":
                label = u["label"]
                break
    if label is None:
        sp = (I.space_types.get(space) or {}).get("name_ko") or space
        label = f"{sp} {I.cat_name(l2) or ''}".strip()
    return label, space, l2


def model_cases(mid: str, match: str | None = None, usage_limit: int = 3) -> dict[str, Any]:
    I = idx()
    fid = I.models[mid]["family_id"]
    body = set(I.body_deployments())
    by_model = {d for d, t in I.dep_targets.items() if ("model", mid) in t} | _case_docs_mentioning("model", mid)
    by_series = {d for d, t in I.dep_targets.items() if ("family", fid) in t} | _case_docs_mentioning("family", fid)
    by_model &= body
    by_series &= body

    def by_date(ids: set[str]) -> list[str]:
        return sorted(ids, key=lambda d: I.deps[d]["date"] or "", reverse=True)

    label, space, l2 = usage_for_family(fid)
    usage: list[tuple[str, dict[str, Any]]] = []
    if space or l2:
        r = kb().D1(vertical=None, spaces=[space] if space else [], targets=[("category", l2)] if l2 else [], text=label, limit=200)
        for x in r["result"]["deployments"]:
            if x["id"] in body and x["id"] not in by_model and x["id"] not in by_series and I.dep_photos.get(x["id"]):
                usage.append((x["id"], {"score": x["score"], "breakdown": x["similarity_breakdown"], "terms": []}))
            if len(usage) >= usage_limit:
                break
    counts = {"model": len(by_model), "series": len(by_series), "usage": len(usage)}
    default = next((k for k in ("model", "series", "usage") if counts[k]), None)
    which = match or default
    items: list[dict[str, Any]] = []
    if which == "model":
        items = [{**card(d), "match_type": "model"} for d in by_date(by_model)]
    elif which == "series":
        items = [{**card(d), "match_type": "series"} for d in by_date(by_series)]
    elif which == "usage":
        items = [{**card(d, m), "match_type": "usage"} for d, m in usage]
    for it in items:
        it["used_products_line"] = " · ".join(p["label"] for p in it["products"])
    return {"corpus": corpus(), "counts": counts, "usage_label": label, "default_match": default, "items": items}
