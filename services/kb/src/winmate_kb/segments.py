"""Winmate 16업종(세그먼트): 코드표 · 사례 자동 분류 · 업종 인사이트 · 업종 판별 근거(03-mi §4.8 · §7.3, 04-competitor, 10-proposal 부록 C).

- KR · US 업종 대응: KB segment_mapping(시드 초안). `<<FILL…>>` 은 대응 없음으로 본다.
- 사례 → 업종 분류(rule_segment_v1, T5 규칙 초안): 사례 KR 업종이 그 업종 대응에 들면 prior + 단서 사전(제목 · 고객 유형 · 사이트 업종 문장).
  사례 1건 = 업종 1개. 점수가 문턱 미만이면 분류 안 함(GEN).
- 업종 판별 근거(classify): kb_score = (대응 있는 업종) 0.5 × A2대응 + 0.5 × 사례비율 / (대응 없는 업종) 사례비율,
  clue_score = 맞은 단서 가중치 합(1로 자름). A2대응 = 대응 KR 업종들의 A2 정규화 전 점수 최댓값(1로 자름),
  사례비율 = 문장 유사 사례 상위 10건 중 그 업종 사례 수 ÷ 5(1로 자름).
"""
from __future__ import annotations

import collections
import math
import re
import threading
from typing import Any

from winmate_common.errors import not_found

from . import curation
from .engine import kb, q
from .index import idx, jloads

_lock = threading.Lock()
_cache: dict[str, Any] = {}


def _clean_codes(raw: str | None) -> list[str]:
    return [c for c in (jloads(raw, []) or []) if isinstance(c, str) and c and not c.startswith("<<")]


def table() -> list[dict[str, Any]]:
    """16업종: 보드 이름 + KB 이름 · 대응(segment_mapping)."""
    if "table" in _cache:
        return _cache["table"]
    I = idx()
    maps = {r["winmate_segment"]: r for r in q("SELECT * FROM segment_mapping")}
    out = []
    for s in curation.load("segments").get("segments") or []:
        m = maps.get(s["id"]) or {}
        kr = _clean_codes(m.get("kr_vertical_codes"))
        us = _clean_codes(m.get("us_vertical_codes"))
        v = I.verticals.get(s["id"]) or {}
        out.append({**s, "kb_name": v.get("name_ko") or m.get("name_ko"), "kr_vertical_ids": kr, "us_vertical_ids": us,
                    "mapping_status": m.get("status") or v.get("status"),
                    "mapping_missing": [c for c in (jloads(m.get("kr_vertical_codes"), []) or []) if isinstance(c, str) and c.startswith("<<")]})
    _cache["table"] = out
    return out


def by_code(code: str) -> dict[str, Any] | None:
    c = (code or "").strip()
    for s in table():
        if s["code"].lower() == c.lower() or s["id"] == c:
            return s
    return None


def _kr_expand(vids: list[str]) -> set[str]:
    I = idx()
    out = set(vids)
    for v in vids:
        out |= set(I.vert_children.get(v, []))
    return out


def clue_hits(text: str, seg: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    low = (text or "").lower()
    for word, w in (seg.get("clues") or {}).items():
        if str(word).lower() in low:
            out.append({"text": str(word), "code": seg["code"], "weight": float(w)})
    return out


def _clue_score(hits: list[dict[str, Any]]) -> float:
    return min(1.0, sum(h["weight"] for h in hits))


def case_segments() -> dict[str, dict[str, Any]]:
    """사례(본문 있는 것) → {code, score, clues, method}. 업종 하나에 사례 하나."""
    if "cases" in _cache:
        return _cache["cases"]
    with _lock:
        if "cases" in _cache:
            return _cache["cases"]
        I = idx()
        cfg = curation.load("segments").get("classify") or {}
        prior = float(cfg.get("prior", 0.3))
        min_score = float(cfg.get("min_score", 0.4))
        segs = table()
        out: dict[str, dict[str, Any]] = {}
        for did in I.body_deployments():
            d = I.deps[did]
            text = " ".join(x for x in (d["title"], d["customer_type"], d["site_industry_text"]) if x)
            verts = _kr_expand(I.dep_verts.get(did) or [])
            best = None
            for n, s in enumerate(segs):
                hits = clue_hits(text, s)
                p = prior if verts & set(s["kr_vertical_ids"]) else 0.0
                sc = p + _clue_score(hits)
                key = (round(sc, 4), 1 if p else 0, -n)
                if best is None or key > best[0]:
                    best = (key, s, sc, hits, p)
            if best and best[2] >= min_score:
                _, s, sc, hits, p = best
                out[did] = {"code": s["code"], "score": round(sc, 3), "prior": p, "clues": hits}
            else:
                out[did] = {"code": "GEN", "score": round(best[2], 3) if best else 0.0, "prior": 0.0, "clues": []}
        _cache["cases"] = out
        return out


def segment_cases(code: str) -> list[str]:
    I = idx()
    ids = [d for d, x in case_segments().items() if x["code"] == code]
    return sorted(ids, key=lambda d: I.deps[d]["date"] or "", reverse=True)


def observed_mapping(code: str) -> dict[str, Any]:
    """이 업종으로 분류된 사례의 KR 업종(사례 페이지 사이트 업종 필터 → KB vertical_ids) 분포와 관측 대응(2건 이상 · 절반 이상).

    시드 대응(<<FILL>>)을 대신 채우는 계산값(T5) — 사례 분류 prior · classify 에는 쓰지 않는다(되먹임 방지 ·
    '호텔/서비스' 필터(kr_hotel)처럼 넓은 필터가 업종 판별 A2(호텔 페이지)와 뜻이 다르다)."""
    I = idx()
    cs = case_segments()
    ids = [d for d, x in cs.items() if x["code"] == code]
    dist = collections.Counter(v for d in ids for v in dict.fromkeys(I.dep_verts.get(d) or []))
    obs = [v for v, n in dist.most_common() if n >= 2 and n * 2 >= len(ids)]
    return {"distribution": [{"id": v, "name": I.vertical_name(v), "n": n} for v, n in sorted(dist.items(), key=lambda x: (-x[1], x[0]))],
            "observed": obs,
            "case_basis": {"prior": sum(1 for d in ids if cs[d]["prior"] > 0), "clue_only": sum(1 for d in ids if not cs[d]["prior"])}}


def list_out() -> dict[str, Any]:
    cs = case_segments()
    cnt = collections.Counter(x["code"] for x in cs.values())
    items = []
    for s in table():
        ob = observed_mapping(s["code"])
        basis = "seed" if s["kr_vertical_ids"] else ("observed_cases" if ob["observed"] else None)
        items.append({"code": s["code"], "id": s["id"], "name": s["name"], "full": s["full"], "short": s["short"],
                      "kb_name": s["kb_name"], "aliases": s.get("aliases") or [], "kr_vertical_ids": s["kr_vertical_ids"],
                      "us_vertical_ids": s["us_vertical_ids"], "mapping_status": s["mapping_status"],
                      "case_count": cnt.get(s["code"], 0), "mapping": basis is not None, "mapping_basis": basis,
                      "kr_vertical_ids_observed": ob["observed"], "observed_kr_verticals": ob["distribution"],
                      "case_basis": ob["case_basis"]})
    return {"items": items, "total_cases": len(cs), "classified_cases": len(cs) - cnt.get("GEN", 0),
            "unclassified_cases": cnt.get("GEN", 0), "method": "rule_segment_v1", "tier": "T5_rule_draft",
            "needs_confirmation": ["사례 → 업종 분류는 규칙 초안(사람 검수 전)", "업종 대응(segment_mapping)은 시드 초안 — 대응 없는 업종은 단서로만 분류",
                                   "mapping_basis=observed_cases 는 분류된 사례의 사이트 업종 필터에서 본 대응(계산값) — 시드 대응을 사람이 채우기 전 참고용"]}


# ── 요구 태그(R01~R24) · 제안 콘텐츠(P01~P22) 코드표 ──
# 이름표는 curation/req_tags.yaml(원문 winmate-kb/raw/prior_case_studies.json meta.taxonomy, T5 — scripts/make_req_tags.py 가 만든다).
# examples_specific · hint_terms 는 태그에 두드러진 낱말 · 문장(계산값)이다.

def req_tag_codebook() -> dict[str, Any]:
    """코드표 전체 — {source, source_tier, collected, status, req_tags[{code, label, description}], proposal_contents[{code, label}]}."""
    d = curation.load("req_tags")
    return {"source": d.get("source"), "source_tier": d.get("source_tier"), "collected": d.get("collected"),
            "status": d.get("status"), "req_tags": list(d.get("req_tags") or []),
            "proposal_contents": list(d.get("proposal_contents") or [])}


def req_tag(code: str) -> dict[str, Any] | None:
    return next((r for r in req_tag_codebook()["req_tags"] if r.get("code") == code), None)


_TOKEN = re.compile(r"[0-9A-Za-z가-힣][0-9A-Za-z가-힣·+]*")
_PARTICLES = ("으로", "와", "과", "을", "를", "은", "는", "의", "에", "로", "도")


def _strip_particle(t: str) -> str:
    """끝 조사 하나를 뗀다(남는 말이 2자 이상일 때만: 인테리어와 → 인테리어, 높이는 → 높이, 회의 → 회의)."""
    for p in _PARTICLES:
        if t.endswith(p) and len(t) - len(p) >= 2:
            return t[: -len(p)]
    return t


def _tokens(text: str) -> set[str]:
    return {_strip_particle(t) for t in _TOKEN.findall(text or "") if len(t) >= 2}


def _tag_stats() -> dict[str, Any]:
    """전체 사례(요구 태그 있는 것)의 요구 문장 낱말 문서 빈도와 태그별 빈도 — lift = P(낱말|태그) / P(낱말)."""
    if "tag_stats" in _cache:
        return _cache["tag_stats"]
    with _lock:
        if "tag_stats" in _cache:
            return _cache["tag_stats"]
        needs: dict[str, list[str]] = collections.defaultdict(list)
        tags: dict[str, set[str]] = collections.defaultdict(set)
        for r in q("SELECT deployment_id, need_raw, kind FROM deployment_need WHERE kind IN ('needs', 'req_tags') ORDER BY rowid"):
            if r["kind"] == "needs":
                needs[r["deployment_id"]].append(r["need_raw"])
            else:
                tags[r["deployment_id"]].add(r["need_raw"])
        cases = [d for d in tags if needs.get(d)]
        ctoks = {d: set().union(*(_tokens(s) for s in needs[d])) for d in cases}
        df = collections.Counter(w for d in cases for w in ctoks[d])
        tag_cases: dict[str, list[str]] = collections.defaultdict(list)
        for d in cases:
            for t in tags[d]:
                tag_cases[t].append(d)
        tdf = {t: collections.Counter(w for d in ds for w in ctoks[d]) for t, ds in tag_cases.items()}
        n = len(cases) or 1
        lift = {t: {w: (c / len(tag_cases[t])) / (df[w] / n) for w, c in tdf[t].items()} for t in tdf}
        hint = {}
        for t, counts in tdf.items():
            cands = [(w, lift[t][w], c) for w, c in counts.items() if c >= 3 and lift[t][w] > 1.2]
            cands.sort(key=lambda x: (-x[1], -x[2], x[0]))
            hint[t] = [w for w, _, _ in cands[:5]]
        out = {"lift": lift, "tdf": tdf, "hint": hint}
        _cache["tag_stats"] = out
        return out


def _specific_score(sentence: str, tag: str, st: dict[str, Any]) -> float:
    toks = _tokens(sentence)
    if not toks:
        return 0.0
    lf, tdf = st["lift"].get(tag, {}), st["tdf"].get(tag, {})
    s = sum(math.log(lf[w]) for w in toks if tdf.get(w, 0) >= 2 and lf.get(w, 0) > 1.0)
    return s / math.sqrt(len(toks))


def insights(code: str, top_req: int = 6, top_items: int = 4) -> dict[str, Any]:
    I = idx()
    seg = by_code(code)
    if seg is None:
        raise not_found("업종", code)
    ids = segment_cases(seg["code"])
    ph = ",".join("?" * len(ids)) or "''"
    req = collections.Counter()
    need_by_tag: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    if ids:
        tags_by_dep: dict[str, list[str]] = collections.defaultdict(list)
        needs_by_dep: dict[str, list[str]] = collections.defaultdict(list)
        for r in q(f"SELECT deployment_id, need_raw, kind FROM deployment_need WHERE deployment_id IN ({ph})", ids):
            if r["kind"] == "req_tags":
                tags_by_dep[r["deployment_id"]].append(r["need_raw"])
            elif r["kind"] == "needs":
                needs_by_dep[r["deployment_id"]].append(r["need_raw"])
        for did, tags in tags_by_dep.items():
            for t in set(tags):
                req[t] += 1
                need_by_tag[t].update(needs_by_dep.get(did, []))
    products: collections.Counter = collections.Counter()
    sols: collections.Counter = collections.Counter()
    for did in ids:
        for kind, ident in I.dep_targets.get(did, set()):
            if kind in ("family", "category"):
                products[(kind, ident)] += 1
            elif kind == "solution":
                sols[(kind, ident)] += 1
    k = kb()
    from .solutions import catalog_by_kb

    def item(kind: str, ident: str, n: int) -> dict[str, Any]:
        name = catalog_by_kb()[ident]["name"] if kind == "solution" and ident in catalog_by_kb() else str(k.name(kind, ident))
        return {"kind": kind, "id": ident, "name": name, "n": n}

    st = _tag_stats()
    used: set[str] = set()
    req_types = []
    for t, n in req.most_common(top_req):
        cands = sorted(need_by_tag[t].items(), key=lambda x: (-_specific_score(x[0], t, st), -x[1], x[0]))
        spec = [s for s, _ in cands if s not in used and _specific_score(s, t, st) > 0][:3]
        used.update(spec)
        tag = req_tag(t) or {}
        req_types.append({"code": t, "label": tag.get("label"), "description": tag.get("description"),
                          "label_source": "codebook" if tag.get("label") else None, "n": n,
                          "examples": [x for x, _ in need_by_tag[t].most_common(3)],
                          "examples_specific": spec, "hint_terms": st["hint"].get(t, [])})
    return {
        "code": seg["code"], "id": seg["id"], "name": seg["name"], "full": seg["full"], "short": seg["short"],
        "cases": len(ids), "case_ids": ids,
        "req_types": req_types,
        "products": [item(kd, i, n) for (kd, i), n in products.most_common(top_items)],
        "solutions": [item(kd, i, n) for (kd, i), n in sols.most_common(top_items)],
        "method": "rule_segment_v1", "tier": "T5_rule_draft",
        "gaps": [("요구 태그 이름표(label · description)는 이전 세션 사례 구조화 때 쓴 코드표(raw/prior_case_studies.json meta.taxonomy, T5 · 사람 검토 전)다. "
                  "examples 는 같은 사례의 요구 문장, examples_specific · hint_terms 는 태그에 두드러진 문장 · 낱말(계산값)")],
    }


def classify(text: str, top_cases: int = 10) -> dict[str, Any]:
    I = idx()
    k = kb()
    a2 = k.A2(text)
    raw = {c["id"]: float(c.get("raw_score") or 0.0) for c in a2.get("candidates") or []}
    sims = []
    for ref, s in k.vec_search(text, "entity", 400):
        if ref.startswith("entity:deployment:"):
            did = ref.split(":", 2)[2]
            if did in I.deps and I.deps[did]["document_id"]:
                sims.append((did, s))
        if len(sims) >= top_cases:
            break
    cs = case_segments()
    case_codes = collections.Counter(cs.get(d, {}).get("code") for d, _ in sims)
    items = []
    for s in table():
        a2c = min(1.0, max([raw.get(v, 0.0) for v in _kr_expand(s["kr_vertical_ids"])] or [0.0])) if s["kr_vertical_ids"] else None
        ratio = min(1.0, case_codes.get(s["code"], 0) / 5)
        kb_score = (0.5 * a2c + 0.5 * ratio) if a2c is not None else ratio
        hits = clue_hits(text, s)
        items.append({"code": s["code"], "id": s["id"], "name": s["name"], "kb_score": round(kb_score, 3),
                      "clue_score": round(_clue_score(hits), 3), "clues": hits,
                      "similar_case_ids": [d for d, _ in sims if cs.get(d, {}).get("code") == s["code"]],
                      "a2_match": round(a2c, 3) if a2c is not None else None, "case_ratio": round(ratio, 3),
                      "has_kr_mapping": bool(s["kr_vertical_ids"])})
    return {"items": items, "a2": {"top2": a2["result"].get("top2"), "decision_hint": a2["decision_hint"],
                                   "decision_reasons": a2["decision_reasons"]},
            "similar_case_ids": [d for d, _ in sims], "method": "rule_segment_v1 + A2 + LSA",
            "needs_confirmation": ["업종 단서 사전 · 사례 업종 분류는 초안(사람 검수 전)"]}
