#!/usr/bin/env python3
"""Winmate KB 질의 라이브러리 + CLI (LLM 없이 결정적으로 동작하는 질의 패턴).

패턴 코드는 docs/06_QUERY_PATTERNS.md 를 따른다. 모든 결과는 봉투(envelope) 형태:
  {pattern, result, evidence_paths, tier_min, candidates, decision_hint, decision_reasons,
   needs_confirmation, fallback_level, modes_used, timings_ms}

사용 예
  python build/query.py search "호텔 객실 TV 원격 관리"
  python build/query.py A1 "호텔 로비에 24시간 운영할 실외 사이니지"
  python build/query.py S1 "호텔 로비와 외부 입구에 24시간 운영할 사이니지가 필요해"
  python build/query.py B1 kr_hotel
  python build/query.py G1 guest_room --category cat_hotel-tvs
  python build/query.py entity family fam_G000183916
  python build/query.py E3 --vertical kr_hotel --space guest_room --customer "비즈니스호텔 체인" --text "객실 TV 통합 관리"
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import curation as C  # noqa: E402

KB_DIR = Path(os.environ.get("WKB_KB", ROOT / "kb"))
DB_PATH = KB_DIR / "winmate_kb.sqlite"
MODEL_DIR = KB_DIR / "models"
TIER_RANK = {"T1": 1, "T2": 2, "T3": 3, "T4": 4, "T5": 5, "T6": 6}
TH = {"auto_score_min": 0.7, "auto_margin_min": 0.15, "industry_ask_margin": 0.10, "precedent_min": 1}


def norm(s):
    if not s:
        return ""
    s = s.replace(" ", " ").replace("™", "").replace("®", "")
    return re.sub(r"[\s·∙\-_/()\[\]]+", "", s).lower()


def tier_of(t):
    return TIER_RANK.get((t or "T6")[:2], 6)


class KB:
    def __init__(self, path=DB_PATH):
        self.c = sqlite3.connect(path)
        self.c.row_factory = sqlite3.Row
        self._lsa = None
        self._vec = None
        self._alias = None
        self._names = None

    # ── 공통 ──
    def q(self, sql, args=()):
        return [dict(r) for r in self.c.execute(sql, args)]

    def names(self):
        if self._names is None:
            self._names = {}
            for kind, sql in {
                "family": "SELECT id, name_ko n FROM product_family", "model": "SELECT id, model_code n FROM product_model",
                "category": "SELECT id, name_ko n FROM category", "solution": "SELECT id, name_ko n FROM solution",
                "service": "SELECT id, name_ko n FROM service_product", "vertical": "SELECT id, coalesce(name_ko,name_en) n FROM vertical",
                "space_type": "SELECT id, name_ko n FROM space_type", "deployment": "SELECT id, title n FROM deployment",
                "capability": "SELECT id, name_ko n FROM capability"}.items():
                for r in self.c.execute(sql):
                    self._names[(kind, r[0])] = r[1]
            # 하위 분류는 '상위 > 하위'로 표시(예: '주거용 실내외기 > 기타')
            for cid, name, parent, level in self.c.execute("SELECT id, name_ko, parent_id, level FROM category WHERE level=3"):
                pn = self._names.get(("category", parent))
                if pn:
                    self._names[("category", cid)] = f"{pn} > {name}"
        return self._names

    def name(self, kind, i):
        return self.names().get((kind, i)) or i

    def occ_url(self, occ_id):
        if not occ_id:
            return None, None
        r = self.c.execute("""SELECT d.url, b.section_path FROM occurrence o JOIN source_document d ON d.id=o.document_id
                              LEFT JOIN document_block b ON b.id=o.block_id WHERE o.id=?""", (occ_id,)).fetchone()
        return (r[0], r[1]) if r else (None, None)

    def envelope(self, pattern, result, evidence=None, candidates=None, reasons=None, needs=None, fallback=None,
                 modes=None, t0=None, tiers=None):
        tiers = [t for t in (tiers or []) if t]
        tier_min = max(tiers, key=tier_of) if tiers else None
        reasons = list(reasons or [])
        cands = candidates or []
        hint = "auto"
        if cands:
            s1 = cands[0]["score"]
            s2 = cands[1]["score"] if len(cands) > 1 else 0
            if s1 < TH["auto_score_min"] or (s1 - s2) < TH["auto_margin_min"]:
                hint = "check"
                reasons.append("LOW_MARGIN" if (s1 - s2) < TH["auto_margin_min"] else "LOW_SCORE")
        if tier_min and tier_of(tier_min) >= 3:
            hint = "check" if hint == "auto" else hint
            reasons.append("LOW_TIER")
        if fallback:
            reasons.append("FALLBACK_USED")
        if "ASK" in reasons or "AMBIGUOUS_INDUSTRY" in reasons:
            hint = "ask"
        return {"pattern": pattern, "result": result, "evidence_paths": evidence or [], "tier_min": tier_min,
                "candidates": cands[:10], "decision_hint": hint, "decision_reasons": sorted(set(reasons)),
                "needs_confirmation": needs or [], "fallback_level": fallback, "modes_used": modes or [],
                "timings_ms": {"total": int((time.time() - (t0 or time.time())) * 1000)}}

    # ── 검색 기반 ──
    def lsa(self):
        if self._lsa is None:
            import joblib
            files = sorted(MODEL_DIR.glob("*.joblib"))
            if not files:
                return None
            import warnings
            with warnings.catch_warnings():   # 저장한 scikit-learn 버전과 달라도 TF-IDF·SVD 는 그대로 쓸 수 있다
                warnings.simplefilter("ignore")
                self._lsa = joblib.load(files[-1])
        return self._lsa

    def embed(self, texts):
        m = self.lsa()
        if not m:
            return None
        z = m["svd"].transform(m["tfidf"].transform(texts)).astype(np.float32)
        z /= np.linalg.norm(z, axis=1, keepdims=True) + 1e-9
        return z

    def vectors(self, space):
        if self._vec is None:
            self._vec = {}
        if space not in self._vec:
            rows = self.c.execute("SELECT ref, vec FROM vec_index WHERE space=?", (space,)).fetchall()
            if not rows:
                self._vec[space] = ([], None)
            else:
                dt = np.float16 if len(rows[0][1]) == 2 * self.c.execute("SELECT dim FROM vec_index LIMIT 1").fetchone()[0] else np.float32
                self._vec[space] = ([r[0] for r in rows], np.vstack([np.frombuffer(r[1], dtype=dt) for r in rows]).astype(np.float32))
        return self._vec[space]

    def vec_search(self, text, space, k=20):
        refs, M = self.vectors(space)
        z = self.embed([text])
        if z is None or M is None:
            return []
        s = M @ z[0]
        idx = np.argsort(-s)[:k]
        return [(refs[i], float(s[i])) for i in idx]

    @staticmethod
    def fts_query(text):
        toks = [t for t in re.split(r"[\s,./·()\[\]\"'?!:;]+", text or "") if len(t) >= 3]
        if not toks:
            toks = [t for t in re.split(r"\s+", text or "") if t]
            toks = [t for t in toks if len(t) >= 3]
        return " OR ".join('"' + t.replace('"', '') + '"' for t in toks[:12])

    def kw_search(self, text, table="chunk_fts", col="chunk_id", k=20):
        fq = self.fts_query(text)
        if not fq:
            return []
        try:
            rows = self.c.execute(f"SELECT {col}, bm25({table}) s FROM {table} WHERE {table} MATCH ? ORDER BY s LIMIT ?",
                                  (fq, k)).fetchall()
        except sqlite3.OperationalError:
            return []
        return [(r[0], -float(r[1])) for r in rows]

    PARTICLE = re.compile(r"(으로|에서|에게|까지|부터|이랑|하고|과|와|을|를|이|가|은|는|의|에|로|도|만)$")
    STOP = {"기능", "제품", "솔루션", "삼성", "사용", "필요", "제공", "관련", "위한", "있는", "하는"}

    def query_tokens(self, text):
        toks = []
        for t in re.split(r"[\s,./·()\[\]\"'?!:;]+", text or ""):
            t = t.strip()
            if len(t) >= 3:
                t2 = self.PARTICLE.sub("", t)
                t = t2 if len(t2) >= 2 else t
            if len(t) >= 2 and t not in self.STOP and t not in toks:
                toks.append(t)
        return toks

    def like_search(self, toks, table="text_chunk", col="id", textcol="text", k=200):
        if not toks:
            return []
        for need in range(len(toks), max(0, len(toks) - 2), -1):
            # 모든 토큰(→ 하나 빠진 조합) 순으로 부분 문자열 일치
            import itertools
            hits = []
            for combo in itertools.combinations(toks, need):
                where = " AND ".join(f"{textcol} LIKE ?" for _ in combo)
                hits += [r[0] for r in self.c.execute(f"SELECT {col} FROM {table} WHERE {where} LIMIT ?", [f"%{t}%" for t in combo] + [k])]
                if len(hits) >= k:
                    break
            if hits:
                return list(dict.fromkeys(hits))[:k]
        return []

    def search(self, text, k=10, modes=("kw", "vec")):
        """하이브리드 검색: 키워드(trigram BM25 + 2글자 토큰 부분일치) + LSA 벡터 → RRF 후 토큰 포괄도로 재정렬."""
        t0 = time.time()
        toks = self.query_tokens(text)
        fused = collections.defaultdict(float)
        if "kw" in modes:
            for r, (cid, _) in enumerate(self.kw_search(" ".join(t for t in toks if len(t) >= 3) or text, k=100)):
                fused[cid] += 1 / (60 + r)
            for r, cid in enumerate(self.like_search(toks)):
                fused[cid] += 1 / (60 + r)
        if "vec" in modes:
            for r, (cid, _) in enumerate(self.vec_search(text, "chunk", 100)):
                fused[cid] += 1 / (60 + r)
        cand = sorted(fused.items(), key=lambda x: -x[1])[:300]
        rows = {}
        if cand:
            ids = [c for c, _ in cand]
            for row in self.c.execute(f"SELECT c.*, d.title FROM text_chunk c LEFT JOIN source_document d ON d.id=c.document_id WHERE c.id IN ({','.join('?' * len(ids))})", ids):
                rows[row["id"]] = row
        mx = max([v for _, v in cand] or [1])
        scored = []
        for cid, v in cand:
            row = rows.get(cid)
            if not row:
                continue
            body = (row["section_path"] or "") + " " + row["text"]
            cov = sum(1 for t in toks if t in body) / len(toks) if toks else 0
            scored.append((0.5 * v / mx + 0.5 * cov, cid, row, cov))
        scored.sort(key=lambda x: -x[0])
        hits = [{"chunk_id": cid, "score": round(sc, 4), "coverage": round(cov, 2), "title": row["title"], "section": row["section_path"],
                 "page_type": row["page_type"], "url": row["url"], "text": row["text"][:400],
                 "entities": json.loads(row["entity_refs_json"] or "[]")[:8]} for sc, cid, row, cov in scored[:k]]
        ents = collections.defaultdict(float)
        if "kw" in modes:
            fq = self.fts_query(" ".join(t for t in toks if len(t) >= 3) or text)
            if fq:
                try:
                    for r, row in enumerate(self.c.execute(
                            "SELECT kind, id FROM entity_fts WHERE entity_fts MATCH ? ORDER BY bm25(entity_fts, 5.0, 1.0) LIMIT 30", (fq,))):
                        ents[f"{row[0]}:{row[1]}"] += 1 / (60 + r)
                except sqlite3.OperationalError:
                    pass
            for r, ref in enumerate(self.like_search(toks, "entity_doc", "kind || ':' || id", "(name || ' ' || text)", 60)):
                ents[ref] += 1 / (60 + r)
        if "vec" in modes:
            for r, (ref, _) in enumerate(self.vec_search(text, "entity", 30)):
                ents[ref.split(":", 1)[1]] += 1 / (60 + r)
        ent_hits = [{"ref": e, "name": self.name(*e.split(":", 1)), "score": round(s_, 4)}
                    for e, s_ in sorted(ents.items(), key=lambda x: -x[1])[:k]]
        return self.envelope("search", {"tokens": toks, "chunks": hits, "entities": ent_hits}, modes=list(modes), t0=t0,
                             evidence=[[{"kind": "doc_block", "ref": h["chunk_id"], "source_url": h["url"]}] for h in hits])

    # ── A. 해석 ──
    def alias_index(self):
        if self._alias is None:
            rows = self.q("SELECT surface, surface_norm, target_kind, target_id FROM alias")
            by = collections.defaultdict(set)
            for r in rows:
                by[r["surface_norm"]].add((r["target_kind"], r["target_id"]))
            surfaces = sorted({r["surface"] for r in rows if len(r["surface_norm"]) >= 2}, key=len, reverse=True)
            codes = sorted({r["surface"] for r in rows if r["target_kind"] == "model"}, key=len, reverse=True)
            self._alias = (by, re.compile("|".join(re.escape(s) for s in surfaces), re.I),
                           re.compile(r"(?<![A-Z0-9])(" + "|".join(re.escape(c) for c in codes) + r")(?![A-Z0-9])") if codes else None)
        return self._alias

    def A1(self, text, lang="ko"):
        """엔티티 링킹: 모델코드·별칭(제품군·카테고리·솔루션·업종) + 공간·역량 키워드."""
        t0 = time.time()
        by, are, cre = self.alias_index()
        links, used = [], []
        if cre:
            for m in cre.finditer(text):
                links.append({"span": [m.start(), m.end()], "surface": m.group(0), "type": "model",
                              "id": by[norm(m.group(0))] and sorted(by[norm(m.group(0))])[0][1], "conf": 1.0, "method": "code_exact"})
                used.append((m.start(), m.end()))
        for m in are.finditer(text):
            if any(a <= m.start() < b for a, b in used):
                continue
            hits = sorted(by.get(norm(m.group(0)), []), key=lambda h: (C.KIND_PRIORITY.get(h[0], 9), h[1]))
            if not hits:
                continue
            k, t = hits[0]
            links.append({"span": [m.start(), m.end()], "surface": m.group(0), "type": k, "id": t, "name": self.name(k, t),
                          "conf": 0.9 if len(hits) == 1 else 0.6, "method": "alias",
                          "alternatives": [{"type": a, "id": b, "name": self.name(a, b)} for a, b in hits[1:6]]})
            used.append((m.start(), m.end()))
        for sp, kw in C.spaces_in_text(text, lang):
            links.append({"surface": kw, "type": "space_type", "id": sp, "name": self.name("space_type", sp), "conf": 0.8,
                          "method": "space_keyword"})
        for cap, kw in C.caps_from_text(text):
            links.append({"surface": kw, "type": "capability", "id": "cap_" + cap, "name": self.name("capability", "cap_" + cap),
                          "conf": 0.7, "method": "need_keyword"})
        return self.envelope("A1", {"links": links}, modes=["sql", "rule"], t0=t0)

    def A2(self, text):
        """업종 판별: 업종명 언급 > 공간 신호(업종 페이지 HAS_SPACE) > 제품 신호(FEATURED_BY_SITE) > 벡터 유사도."""
        t0 = time.time()
        score = collections.defaultdict(float)
        signals = collections.defaultdict(list)
        kr = {r["id"]: r for r in self.q("SELECT id, name_ko, parent_id FROM vertical WHERE scheme='kr_site'")}
        for vid, r in kr.items():
            if r["name_ko"] and len(r["name_ko"]) >= 2 and r["name_ko"] in text:
                score[vid] += 1.0
                signals[vid].append(f"업종명 '{r['name_ko']}'")
        links = self.A1(text)["result"]["links"]
        spaces = [l["id"] for l in links if l["type"] == "space_type"]
        ents = [(l["type"], l["id"]) for l in links if l["type"] in ("family", "category", "solution", "service")]
        for sp in spaces:
            vs = self.q("SELECT src_id v, count(*) n FROM kg_edge WHERE rel='HAS_SPACE' AND dst_id=? AND src_id LIKE 'kr_%' GROUP BY src_id", (sp,))
            tot = sum(v["n"] for v in vs) or 1
            for v in vs:
                score[v["v"]] += 0.6 * v["n"] / tot
                signals[v["v"]].append(f"공간 '{self.name('space_type', sp)}'")
        for k, i in ents:
            vs = self.q("SELECT DISTINCT src_id v FROM kg_edge WHERE rel='FEATURED_BY_SITE' AND dst_kind=? AND dst_id=? AND src_id LIKE 'kr_%'", (k, i))
            for v in vs:
                score[v["v"]] += 0.3 / max(1, len(vs))
                signals[v["v"]].append(f"제품·솔루션 '{self.name(k, i)}'")
        for ref, s in self.vec_search(text, "entity", 60):
            kind, i = ref.split(":", 1)[1].split(":", 1)
            if kind == "vertical" and i in kr and s > 0.1:
                score[i] += 0.4 * s
                signals[i].append(f"유사도 {s:.2f}")
        # 하위 업종 점수를 상위로도 집계
        for vid in list(score):
            p = kr.get(vid, {}).get("parent_id")
            if p:
                score[p] = max(score[p], score[vid])
        ranked = sorted(score.items(), key=lambda x: -x[1])
        top = ranked[0][1] if ranked else 0
        cands = [{"id": v, "name": self.name("vertical", v), "score": round(s / top, 3) if top else 0,
                  "signals": signals[v][:6]} for v, s in ranked[:6]]
        reasons = []
        leaves = [c for c in cands if not any(kr.get(x, {}).get("parent_id") == c["id"] for x in kr)]
        if len(leaves) >= 2 and leaves[0]["score"] - leaves[1]["score"] < TH["industry_ask_margin"]:
            reasons.append("AMBIGUOUS_INDUSTRY")
        if not cands:
            reasons.append("ASK")
        return self.envelope("A2", {"top2": cands[:2], "ask": bool(reasons)}, candidates=[{"id": c["id"], "score": c["score"],
                             "reasons": c["signals"]} for c in cands], reasons=reasons, modes=["sql", "kg", "vec"], t0=t0)

    def A3(self, items, category_root=None):
        """요구 스펙 항목(이름·값 원문) → 정규 속성 키."""
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from build_kb import normalize_spec
        out, unmapped = [], []
        for it in items:
            key, n1, n2, unit = normalize_spec("", it.get("name_raw", ""), it.get("value_raw", ""))
            if key:
                out.append({"name_raw": it.get("name_raw"), "attr": key, "value": n1, "value2": n2, "unit": unit})
            else:
                unmapped.append(it)
        return self.envelope("A3", {"mapped": out, "unmapped": unmapped}, modes=["rule"])

    # ── B. 프리셋 ──
    def B1(self, vertical_id):
        """업종 프리셋: 업종 페이지의 장면 순서 = 공간 시퀀스, 장면별 추천 항목, 히어로 문구, 추천 솔루션, 대표 사례."""
        t0 = time.time()
        vids = [vertical_id] + [r["id"] for r in self.q("SELECT id FROM vertical WHERE parent_id=?", (vertical_id,))]
        ph = ",".join("?" * len(vids))
        secs = self.q(f"""SELECT s.*, d.url FROM industry_section s JOIN source_document d ON d.id=s.document_id
                          WHERE s.vertical_id IN ({ph}) ORDER BY s.vertical_id, s.seq""", vids)
        items = collections.defaultdict(list)
        for it in self.q(f"""SELECT i.* FROM industry_section_item i JOIN industry_section s ON s.id=i.section_id
                             WHERE s.vertical_id IN ({ph}) ORDER BY i.seq""", vids):
            items[it["section_id"]].append({"name": it["item_name"], "kind": it["item_kind"], "target": [it["target_kind"], it["target_id"]],
                                            "target_name": self.name(it["target_kind"], it["target_id"]) if it["target_id"] else None,
                                            "space_label": it["item_space_label"], "link": it["link_url"],
                                            "images": json.loads(it["image_ids_json"] or "[]")})
        seq, hero, rec, cases = [], [], [], []
        for s in secs:
            ent = {"section_id": s["id"], "vertical": s["vertical_id"], "title": s["title"], "description": s["description"],
                   "space_label": s["space_label"], "space_types": json.loads(s["space_types_json"] or "[]"),
                   "space_names": [self.name("space_type", x) for x in json.loads(s["space_types_json"] or "[]")],
                   "items": items[s["id"]], "source": s["url"]}
            {"hero": hero, "recommend": rec, "cases": cases}.get(s["kind"], seq).append(ent)
        order = []
        for e in seq:
            for sp in e["space_types"]:
                if sp not in order:
                    order.append(sp)
        needs = []
        if not seq:
            needs.append("이 업종의 업종 페이지 장면이 없음(US 업종이거나 수집 누락)")
        needs.append("페르소나·시간대·비교축은 사이트에 구조화된 소스가 없음(카탈로그·제안서 필요)")
        return self.envelope("B1", {"vertical": vertical_id, "space_sequence": [{"space_type": x, "name": self.name("space_type", x)} for x in order],
                                    "hero": hero, "scenes": seq, "recommended": rec, "cases": cases},
                             needs=needs, modes=["sql", "kg"], t0=t0, tiers=["T2_official"],
                             evidence=[[{"kind": "occurrence", "ref": s["section_id"], "source_url": s["source"]}] for s in seq])

    def B2(self, text):
        """요구사항 결핍 → 질문: 언급된 공간이 요구하는 역량 중 문장에 없는 것."""
        t0 = time.time()
        sp = [s for s, _ in C.spaces_in_text(text)]
        have = {c for c, _ in C.caps_from_text(text)}
        gaps = []
        for s in sp:
            for r in self.q("SELECT capability_id, strength FROM requires WHERE space_type_id=?", (s,)):
                cap = r["capability_id"].replace("cap_", "")
                if cap not in have:
                    gaps.append({"space": s, "capability": cap, "strength": r["strength"],
                                 "question_ko": f"{self.name('space_type', s)}에 '{self.name('capability', r['capability_id'])}'이(가) 필요한가요?"})
        if not sp:
            gaps.append({"space": None, "capability": None, "strength": "hard", "question_ko": "설치할 공간(예: 로비, 객실, 매장 입구)을 알려 주세요."})
        return self.envelope("B2", {"gaps": gaps}, modes=["rule", "kg"], t0=t0, tiers=["T5_seed_draft"],
                             needs=["requires 엣지는 시드 초안(전문가 승인 전)"])

    # ── C. 추론 ──
    def C1(self, spaces=(), text=None):
        t0 = time.time()
        caps = {}
        for s in spaces:
            for r in self.q("SELECT capability_id, strength FROM requires WHERE space_type_id=?", (s,)):
                caps.setdefault(r["capability_id"], {"id": r["capability_id"], "name": self.name("capability", r["capability_id"]),
                                                     "strength": r["strength"], "from": []})["from"].append(f"space:{s}(requires,draft)")
        for cap, kw in C.caps_from_text(text or ""):
            cid = "cap_" + cap
            e = caps.setdefault(cid, {"id": cid, "name": self.name("capability", cid), "strength": "hard", "from": []})
            e["strength"] = "hard"
            e["from"].append(f"text:'{kw}'")
        return self.envelope("C1", {"capabilities": list(caps.values())}, modes=["kg", "rule"], t0=t0,
                             tiers=["T5_seed_draft"] if spaces else [])

    def _cat_subtree(self, cid):
        out, frontier = {cid}, [cid]
        while frontier:
            nxt = [r["id"] for r in self.q(f"SELECT id FROM category WHERE parent_id IN ({','.join('?' * len(frontier))})", frontier)]
            nxt = [x for x in nxt if x not in out]
            out |= set(nxt)
            frontier = nxt
        return out

    def _family_cats(self, fid):
        cats = {r["category_id"] for r in self.q("SELECT category_id FROM family_category WHERE family_id=?", (fid,))}
        r = self.c.execute("SELECT category_id, subcategory_slug FROM product_family WHERE id=?", (fid,)).fetchone()
        if r and r[0]:
            cats.add(r[0])
            if r[1]:
                cats.add(f"{r[0]}__{r[1]}")
        # 상위 체인
        frontier = list(cats)
        while frontier:
            ps = [x["parent_id"] for x in self.q(f"SELECT parent_id FROM category WHERE id IN ({','.join('?' * len(frontier))}) AND parent_id IS NOT NULL", frontier)]
            ps = [p for p in ps if p not in cats]
            cats |= set(ps)
            frontier = ps
        return cats

    def site_recommended(self, space=None, vertical=None):
        """업종 페이지가 공간·업종에 추천한 대상(카테고리·제품군·솔루션)과 근거 섹션."""
        rows = []
        if space:
            rows += self.q("SELECT dst_kind k, dst_id i, evidence ev, 'space' via FROM kg_edge WHERE rel='RECOMMENDED_BY_SITE' AND src_id=?", (space,))
        if vertical:
            vids = [vertical] + [r["id"] for r in self.q("SELECT id FROM vertical WHERE parent_id=?", (vertical,))]
            rows += self.q(f"SELECT dst_kind k, dst_id i, evidence ev, 'vertical' via FROM kg_edge WHERE rel='FEATURED_BY_SITE' AND src_id IN ({','.join('?' * len(vids))})", vids)
        return rows

    NON_RELAXABLE = {"cap_weatherproof", "cap_sunlight_readable", "cap_wide_temp_operation"}

    def categories_level(self, cid):
        if not hasattr(self, "_cat_level"):
            self._cat_level = {r["id"]: r["level"] for r in self.q("SELECT id, level FROM category")}
        return self._cat_level.get(cid)

    def family_sims(self, text):
        """문장 ↔ 제품군 엔티티 문서 LSA 유사도."""
        refs, M = self.vectors("entity")
        z = self.embed([text]) if text else None
        if z is None or M is None:
            return {}
        s = M @ z[0]
        return {r.split(":", 2)[2]: float(v) for r, v in zip(refs, s) if r.startswith("entity:family:")}

    def C2(self, capabilities=(), category=None, space=None, vertical=None, limit=15, soft=(), text=None):
        """후보 제품군.
        후보 풀 = 카테고리 소속 ∪ (공간·업종에 사이트가 추천한 카테고리·제품군) ∪ hard 역량 제공 제품군.
        hard 역량은 모두 충족해야 남는다(없으면 완화하고 HARD_CONFLICT 표시).
        점수 = 0.45 역량 + 0.35 사이트 추천 + 0.1 카테고리 일치 + 0.1 선례."""
        t0 = time.time()
        caps = [c if c.startswith("cap_") else "cap_" + c for c in capabilities]
        softs = [c if c.startswith("cap_") else "cap_" + c for c in soft if c not in capabilities]
        fams = {f["id"]: f for f in self.q("SELECT id, name_ko, category_id, default_model_code FROM product_family")}
        fcats = {fid: self._family_cats(fid) for fid in fams}
        prov = collections.defaultdict(dict)
        for r in self.q("SELECT family_id, capability_id, evidence FROM provides"):
            prov[r["family_id"]][r["capability_id"]] = r["evidence"]
        rec = self.site_recommended(space, vertical)
        rec_cats = collections.defaultdict(list)
        rec_fams = collections.defaultdict(list)
        rec_sols = collections.OrderedDict()
        for r in rec:
            if r["k"] == "category":
                rec_cats[r["i"]].append(r)
            elif r["k"] == "family":
                rec_fams[r["i"]].append(r)
            elif r["k"] in ("solution", "service"):
                rec_sols.setdefault((r["k"], r["i"]), r)
        catsub = self._cat_subtree(category) if category else set()
        pool = set()
        if category:
            pool |= {f for f in fams if fcats[f] & catsub}
        if space or vertical:
            site_pool = {f for f in fams if f in rec_fams or (fcats[f] & set(rec_cats))}
            pool = (pool & site_pool) if (category and pool & site_pool) else (pool | site_pool if not category else pool)
        if caps and not category:
            pool |= {f for f in fams if all(c in prov[f] for c in caps)}
        if not (category or space or vertical or caps):
            pool = set(fams)
        prec = collections.Counter()
        for r in self.q("SELECT dst_kind, dst_id FROM kg_edge WHERE rel='USES' AND src_kind='deployment'"):
            prec[(r["dst_kind"], r["dst_id"])] += 1
        sims = self.family_sims(text) if text else {}
        max_w = max([sum((2 if self.categories_level(r["i"]) == 3 else 1) for c in fcats[f] if c in rec_cats for r in rec_cats[c])
                     for f in pool] or [1]) or 1
        out = []
        for fid in pool:
            f = fams[fid]
            sat = {c: prov[fid][c] for c in caps if c in prov[fid]}
            miss = [c for c in caps if c not in sat]
            ssat = [c for c in softs if c in prov[fid]]
            cap_score = (len(sat) / len(caps)) if caps else 0.5
            cap_score = min(1.0, cap_score + 0.1 * len(ssat))
            site = rec_fams.get(fid, []) + [x for c in fcats[fid] if c in rec_cats for x in rec_cats[c]]
            w = sum((2 if self.categories_level(r["i"]) == 3 else 1) for r in site if r["k"] == "category")
            site_score = 1.0 if fid in rec_fams else ((0.4 + 0.6 * w / max_w) if site else 0.0)
            cat_score = 1.0 if (category and fcats[fid] & catsub) else 0.0
            p = prec[("family", fid)] + 0.2 * sum(prec[("category", c)] for c in fcats[fid])
            sim = max(0.0, sims.get(fid, 0.0))
            score = 0.4 * cap_score + 0.3 * site_score + 0.1 * cat_score + 0.1 * min(1.0, p / 5) + 0.1 * min(1.0, sim / 0.5)
            reasons = [f"충족 {self.name('capability', c)}: {ev}" for c, ev in sat.items()]
            reasons += [f"충족(soft) {self.name('capability', c)}" for c in ssat]
            reasons += [f"사이트 추천: {self.name(r['k'], r['i'])} ({r['via']})" for r in site[:2]]
            if p:
                reasons.append(f"선례 점수 {p:.1f}")
            if sim > 0.2:
                reasons.append(f"요구 문장 유사도 {sim:.2f}")
            out.append({"id": fid, "name": f["name_ko"], "model": f["default_model_code"], "category": self.name("category", f["category_id"]),
                        "score": round(score, 3), "satisfies": sat, "missing_hard": miss, "satisfies_soft": ssat,
                        "site_recommendation": bool(site), "precedent": round(p, 1), "reasons": reasons})
        reasons_env, needs = [], []
        strict = [o for o in out if not o["missing_hard"]]
        out = [o for o in out if not (set(o["missing_hard"]) & self.NON_RELAXABLE)]   # 환경 역량은 완화하지 않는다
        if caps and not strict and out:
            reasons_env.append("HARD_CONFLICT")
            needs.append("hard 역량을 모두 충족하는 후보가 없어 일부 충족 후보를 표시")
        elif caps:
            out = strict
        out.sort(key=lambda x: (-x["score"], x["name"] or ""))
        if caps or softs:
            needs.append("역량 판정은 presence 규칙 초안(rule_presence_v1) — 임계값 규칙은 전문가 승인 전 비활성")
        sols = [{"kind": k, "id": i, "name": self.name(k, i), "via": r["via"], "evidence": r["ev"]} for (k, i), r in rec_sols.items()]
        sols.sort(key=lambda x: 0 if x["via"] == "space" else 1)
        return self.envelope("C2", {"families": out[:limit], "solutions": sols, "n_pool": len(pool)},
                             candidates=[{"id": o["id"], "score": o["score"], "reasons": o["reasons"][:3]} for o in out[:10]],
                             reasons=reasons_env, modes=["sql", "kg", "rule"], t0=t0, needs=needs,
                             tiers=["T2_official"] + (["T5_rule_draft"] if caps else []),
                             evidence=[[{"kind": "rule", "ref": c, "summary_ko": ev} for c, ev in o["satisfies"].items()] for o in out[:limit]])

    def C3(self, family_id):
        """역방향: 이 제품군(또는 소속 카테고리)이 추천된 업종·공간, 사용한 도입사례."""
        t0 = time.time()
        cats = self._family_cats(family_id)
        targets = [("family", family_id)] + [("category", c) for c in cats]
        fits = []
        for k, i in targets:
            for r in self.q("SELECT src_id, evidence FROM kg_edge WHERE rel='RECOMMENDED_BY_SITE' AND dst_kind=? AND dst_id=?", (k, i)):
                v, sid = (r["evidence"] or "|").split("|", 1)
                fits.append({"space": r["src_id"], "space_name": self.name("space_type", r["src_id"]), "vertical": v or None,
                             "vertical_name": self.name("vertical", v) if v else None, "via": f"{k}:{self.name(k, i)}", "section": sid})
        deps = self.q(f"""SELECT DISTINCT src_id FROM kg_edge WHERE rel IN ('USES','MENTIONS') AND src_kind='deployment'
                          AND ((dst_kind='family' AND dst_id=?) OR (dst_kind='category' AND dst_id IN ({','.join('?' * len(cats)) or "''"})))""",
                      [family_id] + list(cats))
        agg = collections.Counter((f["vertical"], f["space"]) for f in fits)
        uniq = []
        for (v, s), n in agg.most_common():
            f = next(x for x in fits if x["vertical"] == v and x["space"] == s)
            uniq.append({**f, "n_sections": n})
        return self.envelope("C3", {"fits": uniq, "deployments": [{"id": d["src_id"], "title": self.name("deployment", d["src_id"])} for d in deps[:30]],
                                    "precedent_count": len(deps)}, modes=["kg"], t0=t0, tiers=["T2_official"])

    def C4(self, family_id, capabilities=(), category=None):
        t0 = time.time()
        caps = [c if c.startswith("cap_") else "cap_" + c for c in capabilities]
        prov = {r["capability_id"]: r["evidence"] for r in self.q("SELECT capability_id, evidence FROM provides WHERE family_id=?", (family_id,))}
        nspec = self.c.execute("SELECT count(*) FROM spec_value WHERE family_id=?", (family_id,)).fetchone()[0]
        reasons = []
        for c in caps:
            if c not in prov:
                reasons.append({"kind": "spec_unknown" if nspec == 0 else "capability_not_evidenced", "capability": c,
                                "detail": f"'{self.name('capability', c)}' 근거(사이트 분류·스펙·문구)를 찾지 못함"})
        if category and not (self._family_cats(family_id) & self._cat_subtree(category)):
            reasons.append({"kind": "not_in_category", "detail": f"{self.name('category', category)} 소속 아님"})
        fam = self.c.execute("SELECT sale_status_code FROM product_family WHERE id=?", (family_id,)).fetchone()
        if fam is None:
            reasons.append({"kind": "unknown_family", "detail": family_id})
        return self.envelope("C4", {"family": family_id, "reasons": reasons, "satisfied": prov}, modes=["sql", "rule"], t0=t0)

    def C6(self, ref, requirements):
        """요구 스펙 충족 판정: requirements=[{key, op(>=,<=,==,contains), value}]. 스펙 없으면 unknown."""
        t0 = time.time()
        if ref.startswith("mdl_"):
            rows = self.q("SELECT * FROM spec_value WHERE model_id=?", (ref,))
        else:
            rows = self.q("SELECT * FROM spec_value WHERE family_id=? AND model_id=(SELECT id FROM product_model WHERE family_id=? AND is_family_default=1)",
                          (ref, ref)) or self.q("SELECT * FROM spec_value WHERE family_id=?", (ref,))
        by = collections.defaultdict(list)
        for r in rows:
            if r["norm_key"]:
                by[r["norm_key"]].append(r)
        out = []
        for q in requirements:
            vals = by.get(q["key"], [])
            if not vals:
                out.append({"attr": q["key"], "required": f"{q['op']} {q['value']}", "actual": None, "verdict": "unknown"})
                continue
            r = vals[0]
            v = r["value_num"]
            ok = None
            if q["op"] in (">=", "<=", "==") and v is not None:
                ok = {">=": v >= float(q["value"]), "<=": v <= float(q["value"]), "==": v == float(q["value"])}[q["op"]]
            elif q["op"] == "contains":
                ok = str(q["value"]).lower() in (r["value_raw"] or "").lower() or str(q["value"]).lower() in (r["value_unit"] or "").lower()
            out.append({"attr": q["key"], "required": f"{q['op']} {q['value']}", "actual": r["value_raw"],
                        "verdict": "unknown" if ok is None else ("pass" if ok else "fail"), "source": r["source_occurrence_id"],
                        "attr_name": r["attr_name"]})
        return self.envelope("C6", {"ref": ref, "rows": out}, modes=["sql"], t0=t0, tiers=["T2_official"])

    # ── D. 선례 ──
    def D1(self, vertical=None, spaces=(), targets=(), text=None, limit=10):
        """유사 사례: 업종·공간·제품 겹침 + 문장 유사도. targets=[(kind,id)]."""
        t0 = time.time()
        deps = self.q("SELECT id, title, url, date, format, vertical_ids_json, document_id FROM deployment")
        dv = {d["id"]: set(json.loads(d["vertical_ids_json"] or "[]")) for d in deps}
        ds = collections.defaultdict(set)
        for r in self.q("SELECT deployment_id, space_type_id FROM deployment_space WHERE space_type_id IS NOT NULL"):
            ds[r["deployment_id"]].add(r["space_type_id"])
        du = collections.defaultdict(set)
        for r in self.q("SELECT src_id, dst_kind, dst_id FROM kg_edge WHERE src_kind='deployment' AND rel IN ('USES','MENTIONS')"):
            du[r["src_id"]].add((r["dst_kind"], r["dst_id"]))
        tgt = set(tuple(t) for t in targets)
        tgt_cats = set()
        for k, i in tgt:
            if k == "family":
                tgt_cats |= {("category", c) for c in self._family_cats(i)}
        vtop = None
        if vertical:
            r = self.c.execute("SELECT parent_id FROM vertical WHERE id=?", (vertical,)).fetchone()
            vtop = r[0] if r and r[0] else vertical
        sim = {}
        if text:
            for ref, s in self.vec_search(text, "entity", 400):
                if ref.startswith("entity:deployment:"):
                    sim[ref.split(":", 2)[2]] = s
        kpi = collections.Counter(r["deployment_id"] for r in self.q("SELECT deployment_id FROM kpi_claim"))
        photos = {r["d"] for r in self.q("SELECT DISTINCT target_id d FROM depicts WHERE target_kind='deployment'")}
        out = []
        for d in deps:
            b = {"vertical": 1.0 if vtop and (vtop in dv[d["id"]] or vertical in dv[d["id"]]) else 0.0,
                 "space": len(ds[d["id"]] & set(spaces)) / len(spaces) if spaces else 0.0,
                 "product": (1.0 if du[d["id"]] & tgt else (0.6 if du[d["id"]] & tgt_cats else 0.0)) if tgt else 0.0,
                 "text": max(0.0, sim.get(d["id"], 0.0))}
            w = {"vertical": 0.3 if vertical else 0, "space": 0.25 if spaces else 0, "product": 0.3 if tgt else 0, "text": 0.15 if text else 0}
            tw = sum(w.values()) or 1
            s = sum(b[k] * w[k] for k in b) / tw
            if s <= 0:
                continue
            out.append({"id": d["id"], "title": d["title"], "url": d["url"], "format": d["format"], "date": d["date"], "score": round(s, 3),
                        "similarity_breakdown": {k: round(v, 2) for k, v in b.items()}, "kpis_count": kpi[d["id"]],
                        "has_photos": d["id"] in photos})
        out.sort(key=lambda x: -x["score"])
        return self.envelope("D1", {"deployments": out[:limit]}, candidates=[{"id": o["id"], "score": o["score"], "reasons": []} for o in out[:10]],
                             modes=["kg", "vec"], t0=t0, tiers=["T3_case"])

    def D2(self, vertical=None, space=None):
        t0 = time.time()
        if vertical:
            ids = [r["src_id"] for r in self.q("SELECT src_id FROM kg_edge WHERE rel='IN_VERTICAL' AND dst_id=?", (vertical,))]
        elif space:
            ids = [r["deployment_id"] for r in self.q("SELECT DISTINCT deployment_id FROM deployment_space WHERE space_type_id=?", (space,))]
        else:
            ids = [r["id"] for r in self.q("SELECT id FROM deployment")]
        if not ids:
            return self.envelope("D2", {"n": 0}, t0=t0)
        ph = ",".join("?" * len(ids))
        top = self.q(f"""SELECT dst_kind k, dst_id i, count(DISTINCT src_id) n FROM kg_edge WHERE rel IN ('USES') AND src_id IN ({ph})
                         GROUP BY k, i ORDER BY n DESC LIMIT 20""", ids)
        sp = self.q(f"SELECT space_type_id s, count(DISTINCT deployment_id) n FROM deployment_space WHERE deployment_id IN ({ph}) AND space_type_id IS NOT NULL GROUP BY s ORDER BY n DESC LIMIT 15", ids)
        needs = self.q(f"SELECT need_raw t, count(*) n FROM deployment_need WHERE kind='req_tags' AND deployment_id IN ({ph}) GROUP BY t ORDER BY n DESC LIMIT 15", ids)
        return self.envelope("D2", {"n": len(ids), "top_items": [{**t, "name": self.name(t["k"], t["i"])} for t in top],
                                    "top_spaces": [{**s, "name": self.name("space_type", s["s"])} for s in sp], "common_req_tags": needs},
                             modes=["sql"], t0=t0, tiers=["T3_case", "T5_llm_extracted"])

    def D3(self, deployment_ids=(), target=None):
        t0 = time.time()
        ids = list(deployment_ids)
        if target:
            ids += [r["src_id"] for r in self.q("SELECT DISTINCT src_id FROM kg_edge WHERE src_kind='deployment' AND rel='USES' AND dst_kind=? AND dst_id=?", target)]
        if not ids:
            return self.envelope("D3", {"kpis": [], "count": 0}, t0=t0)
        rows = self.q(f"SELECT k.*, d.title, d.url FROM kpi_claim k JOIN deployment d ON d.id=k.deployment_id WHERE k.deployment_id IN ({','.join('?' * len(ids))})", ids)
        return self.envelope("D3", {"kpis": rows, "count": len(rows)}, modes=["sql"], t0=t0, tiers=["T3_case", "T5_llm_extracted"],
                             needs=["KPI 문장은 이전 세션 LLM 추출(T5) — 원문 대조 필요", "claim_flag=1: 대외 사용 전 확인"] if rows else [])

    def D5(self, targets, min_support=2):
        """공존 패턴: 도입사례에서 함께 쓰인 대상(support·confidence·lift)."""
        t0 = time.time()
        rows = self.q("SELECT src_id d, dst_kind k, dst_id i FROM kg_edge WHERE src_kind='deployment' AND rel='USES'")
        sets = collections.defaultdict(set)
        for r in rows:
            sets[r["d"]].add((r["k"], r["i"]))
        N = len(sets) or 1
        tg = set(tuple(t) for t in targets)
        base = [d for d, s in sets.items() if tg <= s]
        cnt = collections.Counter()
        for d in base:
            cnt.update(sets[d] - tg)
        freq = collections.Counter()
        for s in sets.values():
            freq.update(s)
        out = []
        for (k, i), n in cnt.most_common(50):
            if n < min_support:
                continue
            conf = n / len(base)
            lift = conf / (freq[(k, i)] / N)
            out.append({"kind": k, "id": i, "name": self.name(k, i), "support": n, "confidence": round(conf, 3), "lift": round(lift, 2)})
        return self.envelope("D5", {"base_count": len(base), "co_items": out}, modes=["sql"], t0=t0, tiers=["T2_official", "T5_llm_extracted"])

    # ── E. 메시지 ──
    def _vp_rows(self, where, args):
        rows = self.q(f"""SELECT v.*, d.url FROM value_prop v LEFT JOIN occurrence o ON o.id=v.source_occurrence_id
                          LEFT JOIN source_document d ON d.id=o.document_id WHERE {where}""", args)
        return rows

    def E1(self, about=(), vertical=None, space=None, locale=None):
        """대상별 메시지 계층: tagline → key_message → proof_point (원문 그대로, 출처 포함)."""
        t0 = time.time()
        conds, args = [], []
        for k, i in about:
            conds.append("(v.about_kind=? AND v.about_id=?)")
            args += [k, i]
        if vertical:
            vids = [vertical] + [r["id"] for r in self.q("SELECT id FROM vertical WHERE parent_id=?", (vertical,))]
            conds.append(f"v.vertical_id IN ({','.join('?' * len(vids))})")
            args += vids
        if space:
            conds.append("v.space_type_id=?")
            args.append(space)
        if not conds:
            return self.envelope("E1", {"tree": []}, t0=t0)
        where = "(" + " OR ".join(conds) + ")"
        if locale:
            where += " AND v.locale=?"
            args.append(locale)
        rows = self._vp_rows(where, args)
        kids = collections.defaultdict(list)
        for r in rows:
            if r["parent_id"]:
                kids[r["parent_id"]].append(r)
        tree = {"taglines": [], "key_messages": [], "usps": []}
        for r in rows:
            item = {"id": r["id"], "text": r["text"], "about": [r["about_kind"], r["about_id"]], "about_name": self.name(r["about_kind"], r["about_id"]),
                    "claim_flag": r["claim_flag"], "source_url": r["url"], "method": r["method"], "tier": r["source_tier"]}
            if r["level"] == "tagline":
                tree["taglines"].append(item)
            elif r["level"] == "key_message":
                item["proof_points"] = [{"id": k["id"], "text": k["text"], "claim_flag": k["claim_flag"]} for k in kids.get(r["id"], [])]
                tree["key_messages"].append(item)
            elif r["level"] == "usp":
                tree["usps"].append(item)
            elif r["level"] == "proof_point" and not r["parent_id"]:
                tree["key_messages"].append({**item, "level": "proof_point_only", "proof_points": []})
        needs = ["claim 포함 문구(숫자·최고·최초 등) — 대외 사용 전 확인"] if any(r["claim_flag"] for r in rows) else []
        return self.envelope("E1", {"tree": tree, "n": len(rows)}, modes=["sql"], t0=t0, needs=needs,
                             tiers=list({r["source_tier"] for r in rows}))

    def E2(self, theme, limit=15, locale=None):
        """테마 검색: 문장과 비슷한 메시지(LSA 유사도 + 키워드)와 그 대상 제품·사례."""
        t0 = time.time()
        rows = self.q("SELECT id, text, level, about_kind, about_id, locale, claim_flag FROM value_prop" + (" WHERE locale=?" if locale else ""),
                      (locale,) if locale else ())
        if not rows:
            return self.envelope("E2", {"messages": []}, t0=t0)
        Z = self.embed([r["text"] for r in rows])
        z = self.embed([theme])
        sims = (Z @ z[0]) if Z is not None else np.zeros(len(rows))
        toks = [t for t in re.split(r"\s+", theme) if len(t) >= 2]
        scored = []
        for r, s in zip(rows, sims):
            kw = sum(1 for t in toks if t in r["text"]) / (len(toks) or 1)
            scored.append((0.6 * float(s) + 0.4 * kw, r))
        scored.sort(key=lambda x: -x[0])
        msgs = [{"id": r["id"], "text": r["text"], "level": r["level"], "about": [r["about_kind"], r["about_id"]],
                 "about_name": self.name(r["about_kind"], r["about_id"]), "score": round(s, 3), "claim_flag": r["claim_flag"]}
                for s, r in scored[:limit]]
        prods = collections.Counter((m["about"][0], m["about"][1]) for m in msgs if m["about"][0] in ("family", "solution", "category"))
        return self.envelope("E2", {"messages": msgs, "supporting": [{"kind": k, "id": i, "name": self.name(k, i), "n": n} for (k, i), n in prods.most_common(8)]},
                             modes=["vec", "kw"], t0=t0, tiers=["T2_official"])

    # ── E3. 요구사항 컨텍스트 → 메시지 묶음 ──
    E3_W = {"product": 0.35, "vertical": 0.25, "space": 0.2, "customer": 0.15, "text": 0.35}
    E3_INFER = 0.5          # 입력하지 않고 문장에서 추론한 항목의 가중치 배율
    E3_MIN = 0.1            # 묶음에 넣을 최소 점수
    LEVEL_RANK = {"tagline": 0, "key_message": 1, "usp": 2, "proof_point": 3}
    E3_KM_KINDS = ("industry_section", "category", "solution", "service", "vertical", "document")

    def _e3_data(self):
        """E3 공통 자료(한 번만): 메시지 행·벡터, 제품군 분류, 그래프 이웃."""
        if getattr(self, "_e3", None) is None:
            vps = self.q("""SELECT v.id, v.level, v.text, v.parent_id, v.about_kind, v.about_id, v.vertical_id, v.space_type_id, v.locale,
                                   v.claim_flag, v.source_tier, v.method, d.url FROM value_prop v LEFT JOIN occurrence o ON o.id=v.source_occurrence_id
                                   LEFT JOIN source_document d ON d.id=o.document_id ORDER BY v.rowid""")
            deps = self.q("SELECT id, title, url, date, customer_type, site_industry_text, quote, vertical_ids_json FROM deployment ORDER BY rowid")
            cat_parent = {r["id"]: r["parent_id"] for r in self.q("SELECT id, parent_id FROM category")}
            fam_cats = collections.defaultdict(set)
            for r in self.q("SELECT family_id, category_id FROM family_category"):
                fam_cats[r["family_id"]].add(r["category_id"])
            for r in self.q("SELECT id, category_id, subcategory_slug FROM product_family"):
                cs = fam_cats[r["id"]]
                if r["category_id"]:
                    cs.add(r["category_id"])
                    if r["subcategory_slug"]:
                        cs.add(f"{r['category_id']}__{r['subcategory_slug']}")
                frontier = list(cs)
                while frontier:
                    ps = [cat_parent.get(x) for x in frontier]
                    ps = [p for p in ps if p and p not in cs]
                    cs |= set(ps)
                    frontier = ps
            edges = collections.defaultdict(list)
            for r in self.q("SELECT src_kind, src_id, rel, dst_kind, dst_id FROM kg_edge WHERE rel IN ('USES','MENTIONS','FEATURED_BY_SITE','RECOMMENDED_BY_SITE','FEATURED_CASE','SOLD_AS') ORDER BY rowid"):
                edges[r["rel"]].append((r["src_kind"], r["src_id"], r["dst_kind"], r["dst_id"]))
            dep_use = collections.defaultdict(set)
            for rel in ("USES", "MENTIONS"):
                for sk, si, dk, di in edges[rel]:
                    if sk == "deployment":
                        dep_use[si].add((dk, di))
            dep_space = collections.defaultdict(set)
            for r in self.q("SELECT deployment_id, space_type_id FROM deployment_space WHERE space_type_id IS NOT NULL"):
                dep_space[r["deployment_id"]].add(r["space_type_id"])
            sec = {r["id"]: r for r in self.q("SELECT id, vertical_id, title, space_types_json FROM industry_section")}
            sec_items = collections.defaultdict(set)
            for r in self.q("SELECT section_id, target_kind, target_id FROM industry_section_item WHERE target_id IS NOT NULL"):
                sec_items[r["section_id"]].add((r["target_kind"], r["target_id"]))
            fam_caps = collections.defaultdict(set)
            for r in self.q("SELECT family_id, capability_id FROM provides"):
                fam_caps[r["family_id"]].add(r["capability_id"])
            kpis = collections.defaultdict(list)
            for r in self.q("SELECT deployment_id, text, claim_flag FROM kpi_claim ORDER BY rowid"):
                kpis[r["deployment_id"]].append({"text": r["text"], "claim_flag": r["claim_flag"]})
            Z = self.embed([r["text"] for r in vps])
            Zd = self.embed([" ".join(x for x in (d["title"], d["customer_type"], d["quote"]) if x) for d in deps])
            self._e3 = {"vps": vps, "Z": Z, "deps": deps, "Zd": Zd, "cat_parent": cat_parent, "fam_cats": fam_cats, "edges": edges,
                        "dep_use": dep_use, "dep_space": dep_space, "sec": sec, "sec_items": sec_items, "fam_caps": fam_caps, "kpis": kpis,
                        "kids": collections.defaultdict(list)}
            for i, r in enumerate(vps):
                if r["parent_id"]:
                    self._e3["kids"][r["parent_id"]].append(i)
        return self._e3

    def E3(self, vertical=None, spaces=(), products=(), customer=None, text=None, locale="ko-KR", limit=12):
        """요구사항 컨텍스트(업종·공간·제품·타겟고객·요구사항, 모두 선택) → 원문 메시지 묶음.

        입력하지 않은 업종·공간·제품은 타겟고객·요구사항 문장에서 추론한다(가중치 0.5배).
        점수 = Σ(항목 가중치 × 항목 일치도) / Σ(쓴 항목 가중치)
          제품 0.35 · 업종 0.25 · 공간 0.2 · 타겟고객 0.15 · 문장 유사도 0.35(= 0.6×LSA + 0.4×토큰 포괄도)
        결과: 헤드라인(tagline) · 핵심 메시지(+근거 문장) · 제품 메시지(제품군별) · 근거 사례(인용·KPI) · 전체 순위."""
        t0 = time.time()
        E = self._e3_data()
        spaces = [s for s in (spaces or []) if s]
        products = [tuple(p) for p in (products or []) if p and p[1]]
        customer = (customer or "").strip() or None
        text = (text or "").strip() or None
        ctx_text = " ".join(x for x in (customer, text) if x)
        reasons, needs = [], []
        ctx = {"vertical": None, "spaces": [], "products": [], "customer": None, "text": text, "capabilities": [], "missing": []}
        vrow = {r["id"]: r for r in self.q("SELECT id, parent_id, scheme FROM vertical")}
        # 업종
        v_from = None
        if vertical:
            v_from = "input"
        elif ctx_text:
            a2 = self.A2(ctx_text)
            top = a2["result"]["top2"][0] if a2["result"]["top2"] else None
            if top and any(not s.startswith("유사도") for s in top["signals"]):
                vertical, v_from = top["id"], "inferred"
                if "AMBIGUOUS_INDUSTRY" in a2["decision_reasons"]:
                    reasons.append("AMBIGUOUS_INDUSTRY")
                ctx["vertical_alternatives"] = [{"id": c["id"], "name": self.name("vertical", c["id"]), "score": c["score"]} for c in a2["candidates"][1:4]]
        if vertical:
            ctx["vertical"] = {"id": vertical, "name": self.name("vertical", vertical), "from": v_from}
        vset = set([vertical] + [i for i, r in vrow.items() if r["parent_id"] == vertical]) if vertical else set()
        vpar = vrow.get(vertical, {}).get("parent_id") if vertical else None
        # 공간
        sp_from = None
        if spaces:
            sp_from = "input"
            ctx["spaces"] = [{"id": s, "name": self.name("space_type", s), "from": "input"} for s in spaces]
        elif ctx_text:
            found = C.spaces_in_text(ctx_text, "ko", vertical)
            if found:
                spaces, sp_from = [s for s, _ in found], "inferred"
                ctx["spaces"] = [{"id": s, "name": self.name("space_type", s), "from": "inferred", "surface": kw} for s, kw in found]
        spset = set(spaces)
        # 제품
        p_from = None
        if products:
            p_from = "input"
            ctx["products"] = [{"kind": k, "id": i, "name": self.name(k, i), "from": "input"} for k, i in products]
        elif ctx_text:
            seen = []
            for l in self.A1(ctx_text)["result"]["links"]:
                k, i = l["type"], l["id"]
                if k == "model" and i:
                    r = self.c.execute("SELECT family_id FROM product_model WHERE id=?", (i,)).fetchone()
                    k, i = ("family", r[0]) if r and r[0] else (None, None)
                if k in ("family", "category", "solution", "service") and i and (k, i) not in seen:
                    seen.append((k, i))
                    ctx["products"].append({"kind": k, "id": i, "name": self.name(k, i), "from": "inferred", "surface": l["surface"]})
            products, p_from = seen, ("inferred" if seen else None)
        caps = [c for c, _ in C.caps_from_text(text)] if text else []
        caps = ["cap_" + c for c in caps]
        ctx["capabilities"] = [{"id": c, "name": self.name("capability", c)} for c in caps]
        pset = set(products)
        pcat = {i for k, i in products if k == "category"}
        pfam = {i for k, i in products if k == "family"}
        psol = {i for k, i in products if k in ("solution", "service")}
        pfam_cats = set().union(*[E["fam_cats"].get(f, set()) for f in pfam]) if pfam else set()
        cat_desc = set()          # 선택 분류의 하위 분류(자신 포함)
        if pcat:
            kids_of = collections.defaultdict(list)
            for c, p in E["cat_parent"].items():
                if p:
                    kids_of[p].append(c)
            frontier = list(pcat)
            cat_desc |= pcat
            while frontier:
                nx = [k for x in frontier for k in kids_of[x] if k not in cat_desc]
                cat_desc |= set(nx)
                frontier = nx
        cat_anc = set()
        for c in pcat:
            p = E["cat_parent"].get(c)
            while p and p not in cat_anc:
                cat_anc.add(p)
                p = E["cat_parent"].get(p)
        sold_fams = {di for sk, si, dk, di in E["edges"]["SOLD_AS"] if si in psol and dk == "family"}
        sol_selling = {si for sk, si, dk, di in E["edges"]["SOLD_AS"] if di in pfam}
        feat = {(dk, di) for sk, si, dk, di in E["edges"]["FEATURED_BY_SITE"] if si in vset}
        feat_case = {di for sk, si, dk, di in E["edges"]["FEATURED_CASE"] if si in vset}
        feat_n = collections.Counter(di for sk, si, dk, di in E["edges"]["FEATURED_BY_SITE"] if si in vset and dk == "category")
        feat_cats = set(feat_n)
        rec = {(dk, di) for sk, si, dk, di in E["edges"]["RECOMMENDED_BY_SITE"] if si in spset}
        rec_n = collections.Counter(di for sk, si, dk, di in E["edges"]["RECOMMENDED_BY_SITE"] if si in spset and dk == "category")
        rec_cats = set(rec_n)
        # 타겟고객 → 사례
        cust_dep = {}
        if customer:
            toks = [norm(t) for t in self.query_tokens(customer)]
            toks = [t for t in toks if t]
            tot = sum(len(t) for t in toks)
            for d in E["deps"]:
                # 글자 수로 가중한 토큰 포괄도(짧은 일반어 '체인'·'본사' 하나만 맞는 사례는 빠지게)
                hay = norm(" ".join(x for x in (d["customer_type"], d["title"], d["site_industry_text"]) if x))
                cov = sum(len(t) for t in toks if t in hay) / tot if tot else 0
                if cov >= 0.5:
                    cust_dep[d["id"]] = cov
            ctx["customer"] = {"text": customer, "deployments": [{"id": d["id"], "title": d["title"], "customer_type": d["customer_type"], "cov": round(cust_dep[d["id"]], 2)}
                                                                 for d in E["deps"] if d["id"] in cust_dep][:12]}
        # 가중치
        W = self.E3_W
        w = {"product": W["product"] * (1 if p_from == "input" else self.E3_INFER) if (pset or caps) else 0,
             "vertical": W["vertical"] * (1 if v_from == "input" else self.E3_INFER) if vset else 0,
             "space": W["space"] * (1 if sp_from == "input" else self.E3_INFER) if spset else 0,
             "customer": W["customer"] if customer else 0,
             "text": W["text"] if ctx_text else 0}
        tw = sum(w.values())
        ctx["weights"] = {k: round(v, 3) for k, v in w.items()}
        ctx["missing"] = [k for k, v in (("vertical", vset), ("space", spset), ("product", pset), ("customer", customer), ("text", text)) if not v]
        if not tw:
            return self.envelope("E3", {"context": ctx, "headline": [], "key_messages": [], "products": [], "cases": [], "ranked": [], "n_scored": 0, "n_candidates": 0},
                                 reasons=["ASK"], t0=t0)
        vn = lambda i: self.name("vertical", i)
        cn = lambda i: self.name("category", i)

        # 엔티티 단위 일치도(제품·업종·공간·고객) — 항목마다 가장 높은 근거 하나
        cache = {}

        def ent(kind, i):
            key = (kind, i)
            if key in cache:
                return cache[key]
            s = {"product": 0.0, "vertical": 0.0, "space": 0.0, "customer": 0.0}
            why = {}

            def up(k, v, r):
                if v > s[k]:
                    s[k], why[k] = v, r
            if kind == "family":
                fc = E["fam_cats"].get(i, set())
                if (kind, i) in pset:
                    up("product", 1.0, "선택 제품")
                hit = sorted(fc & pcat)
                if hit:
                    up("product", 0.8, f"선택 분류 '{cn(hit[0])}'의 제품")
                if i in sold_fams:
                    up("product", 0.8, "선택 솔루션의 판매 제품")
                hc = sorted(E["fam_caps"].get(i, set()) & set(caps))
                if hc:
                    up("product", 0.5, f"요구 역량 '{self.name('capability', hc[0])}' 제공")
                # 업종·공간 페이지가 그 분류를 여러 장면에서 추천할수록 높게(0.3 ~ 0.5)
                hf = sorted(fc & feat_cats, key=lambda x: (-feat_n[x], x))
                if hf:
                    up("vertical", min(0.5, 0.2 + 0.1 * feat_n[hf[0]]), f"업종 페이지 추천 분류 '{cn(hf[0])}'({feat_n[hf[0]]}곳)의 제품")
                hr = sorted(fc & rec_cats, key=lambda x: (-rec_n[x], x))
                if hr:
                    up("space", min(0.5, 0.2 + 0.1 * rec_n[hr[0]]), f"공간 추천 분류 '{cn(hr[0])}'({rec_n[hr[0]]}곳)의 제품")
            elif kind == "category":
                if (kind, i) in pset:
                    up("product", 1.0, "선택 분류")
                if i in cat_desc:
                    up("product", 0.8, "선택 분류의 하위 분류")
                if i in pfam_cats:
                    up("product", 0.6, "선택 제품의 분류")
                if i in cat_anc:
                    up("product", 0.5, "선택 분류의 상위 분류")
                if i in feat_cats:
                    up("vertical", 0.4, "업종 페이지 추천 분류")
                if i in rec_cats:
                    up("space", 0.4, "공간 추천 분류")
            elif kind in ("solution", "service"):
                if (kind, i) in pset:
                    up("product", 1.0, "선택 솔루션")
                if i in sol_selling:
                    up("product", 0.6, "선택 제품을 파는 솔루션")
                if (kind, i) in feat:
                    up("vertical", 0.4, "업종 페이지 추천 솔루션")
                if (kind, i) in rec:
                    up("space", 0.4, "공간 추천 솔루션")
            elif kind == "deployment":
                du = E["dep_use"].get(i, set())
                if du & pset:
                    up("product", 1.0, "선택 제품을 쓴 사례")
                elif du & ({("category", c) for c in pcat | pfam_cats}):
                    up("product", 0.6, "선택 제품 분류를 쓴 사례")
                d = next((x for x in E["deps"] if x["id"] == i), None)
                dv = set(json.loads(d["vertical_ids_json"] or "[]")) if d else set()
                if dv & vset or i in feat_case:
                    up("vertical", 1.0, "업종 사례" if dv & vset else "업종 페이지 대표 사례")
                elif vpar and vpar in dv:
                    up("vertical", 0.5, f"상위 업종 '{vn(vpar)}' 사례")
                if E["dep_space"].get(i, set()) & spset or ("deployment", i) in rec:
                    up("space", 1.0, "같은 공간 사례")
                if i in cust_dep:
                    up("customer", cust_dep[i], f"고객 유형 '{(d or {}).get('customer_type') or ''}'")
            elif kind == "industry_section":
                sr = E["sec"].get(i)
                if sr:
                    if sr["vertical_id"] in vset:
                        up("vertical", 1.0, f"업종 '{vn(sr['vertical_id'])}' 페이지 장면")
                    elif vpar and sr["vertical_id"] == vpar:
                        up("vertical", 0.5, f"상위 업종 '{vn(vpar)}' 페이지 장면")
                    if set(json.loads(sr["space_types_json"] or "[]")) & spset:
                        up("space", 1.0, "같은 공간 장면")
                    its = E["sec_items"].get(i, set())
                    if its & pset:
                        up("product", 0.8, "장면 항목에 선택 제품")
                    elif any((k == "category" and (c in cat_desc or c in pfam_cats)) or (k == "family" and E["fam_cats"].get(c, set()) & pcat) for k, c in its):
                        up("product", 0.6, "장면 항목에 선택 분류")
            elif kind == "vertical":
                if i in vset:
                    up("vertical", 1.0, f"업종 '{vn(i)}' 헤드라인")
                elif vpar and i == vpar:
                    up("vertical", 0.5, f"상위 업종 '{vn(i)}' 헤드라인")
            cache[key] = (s, why)
            return cache[key]

        # 문장 유사도
        theme = ctx_text
        toks = self.query_tokens(theme) if theme else []
        sims = (E["Z"] @ self.embed([theme])[0]) if theme and E["Z"] is not None else None

        def tsim(i, body):
            if not theme:
                return 0.0
            kw = sum(1 for t in toks if t in body) / len(toks) if toks else 0.0
            cos = float(sims[i]) if sims is not None else 0.0
            return max(0.0, min(1.0, 0.6 * cos + 0.4 * kw))

        def combine(s, why, st, extra=None):
            s = dict(s)
            why = dict(why)
            if extra:
                for k, (v, r) in extra.items():
                    if v > s[k]:
                        s[k], why[k] = v, r
            s["text"] = st
            if st > 0:
                why["text"] = f"요구사항 유사 {st:.2f}"
            sc = sum(w[k] * s[k] for k in w) / tw
            return sc, s, [why[k] for k in ("product", "vertical", "space", "customer", "text") if w[k] and s.get(k, 0) > 0 and k in why]

        vps = E["vps"]
        scored = [None] * len(vps)
        for idx, r in enumerate(vps):
            if locale and r["locale"] != locale:
                continue
            s, why = ent(r["about_kind"], r["about_id"])
            extra = {}
            if r["vertical_id"] and r["vertical_id"] in vset:
                extra["vertical"] = (1.0, f"업종 '{vn(r['vertical_id'])}' 페이지 문구")
            elif vpar and r["vertical_id"] == vpar:
                extra["vertical"] = (0.5, f"상위 업종 '{vn(vpar)}' 페이지 문구")
            if r["space_type_id"] and r["space_type_id"] in spset:
                extra["space"] = (1.0, f"공간 '{self.name('space_type', r['space_type_id'])}' 장면 문구")
            sc, sg, why_l = combine(s, why, tsim(idx, r["text"]), extra)
            if sc > 0:
                scored[idx] = (round(sc, 4), sg, why_l)

        def about_name(k, i):
            if k == "industry_section":
                sr = E["sec"].get(i)
                return f"{vn(sr['vertical_id'])} · {sr['title'] or ''}" if sr else i
            return self.name(k, i)

        def item(idx, sc=None):
            r = vps[idx]
            s4, sg, why_l = scored[idx] if scored[idx] else (0.0, {}, [])
            return {"id": r["id"], "level": r["level"], "text": r["text"], "about": [r["about_kind"], r["about_id"]],
                    "about_name": about_name(r["about_kind"], r["about_id"]), "score": round(sc if sc is not None else s4, 3),
                    "signals": {k: round(v, 2) for k, v in sg.items() if v}, "reasons": why_l, "claim_flag": r["claim_flag"],
                    "source_url": r["url"], "tier": r["source_tier"], "method": r["method"], "parent_id": r["parent_id"]}

        order = sorted([i for i, x in enumerate(scored) if x and x[0] >= self.E3_MIN],
                       key=lambda i: (-scored[i][0], self.LEVEL_RANK.get(vps[i]["level"], 9)))
        # 같은 문장(여러 제품군에 공통으로 붙은 문구 등)은 첫 번째만 남기고 개수를 센다
        seen, dedup = {}, []
        for i in order:
            k = norm(vps[i]["text"])
            if k in seen:
                seen[k]["dup"] += 1
                continue
            it = item(i)
            it["dup"] = 0
            seen[k] = it
            dedup.append((i, it))
        headline = [it for i, it in dedup if vps[i]["level"] == "tagline"][:3]
        # 핵심 메시지: 하위 근거 문장 점수의 0.9배까지 끌어올린다
        km = []
        km_seen = set()
        for idx, r in enumerate(vps):
            if r["about_kind"] not in self.E3_KM_KINDS or r["level"] not in ("key_message", "proof_point") or (r["level"] == "proof_point" and r["parent_id"]):
                continue
            if locale and r["locale"] != locale:
                continue
            own = scored[idx][0] if scored[idx] else 0.0
            kid = max([scored[j][0] for j in E["kids"].get(r["id"], []) if scored[j]] or [0.0])
            eff = round(max(own, 0.9 * kid), 4)
            if eff >= self.E3_MIN:
                km.append((eff, idx))
        km.sort(key=lambda x: (-x[0], self.LEVEL_RANK.get(vps[x[1]]["level"], 9)))
        key_messages = []
        for eff, idx in km:
            k = norm(vps[idx]["text"])
            if k in km_seen:
                continue
            km_seen.add(k)
            it = item(idx, eff)
            kids = sorted([j for j in E["kids"].get(vps[idx]["id"], []) if not locale or vps[j]["locale"] == locale],
                          key=lambda j: -(scored[j][0] if scored[j] else 0.0))
            it["proof_points"] = [item(j) for j in kids[:4]]
            key_messages.append(it)
            if len(key_messages) >= limit:
                break
        # 제품 메시지: 제품군별 묶음
        groups = collections.OrderedDict()
        for i, it in dedup:
            if vps[i]["about_kind"] != "family":
                continue
            g = groups.setdefault(vps[i]["about_id"], [])
            if len(g) < 4:
                g.append(it)
        prods = [{"kind": "family", "id": f, "name": self.name("family", f), "score": its[0]["score"], "items": its} for f, its in list(groups.items())[:8]]
        # 근거 사례: 사례 단위 점수(문장 유사도는 제목·고객 유형·인용으로)
        dep_msgs = collections.defaultdict(list)
        for idx, r in enumerate(vps):
            if r["about_kind"] == "deployment" and (not locale or r["locale"] == locale):
                dep_msgs[r["about_id"]].append(idx)
        dsims = (E["Zd"] @ self.embed([theme])[0]) if theme and E["Zd"] is not None else None
        cases = []
        for j, d in enumerate(E["deps"]):
            if d["id"] not in dep_msgs and d["id"] not in E["kpis"]:
                continue
            s, why = ent("deployment", d["id"])
            body = " ".join(x for x in (d["title"], d["customer_type"], d["quote"]) if x)
            st = 0.0
            if theme:
                kw = sum(1 for t in toks if t in body) / len(toks) if toks else 0.0
                st = max(0.0, min(1.0, 0.6 * (float(dsims[j]) if dsims is not None else 0.0) + 0.4 * kw))
            sc, sg, why_l = combine(s, why, st)
            if round(sc, 4) < self.E3_MIN:
                continue
            cases.append({"id": d["id"], "title": d["title"], "url": d["url"], "date": d["date"], "customer_type": d["customer_type"],
                          "score": round(sc, 3), "_s": round(sc, 4), "signals": {k: round(v, 2) for k, v in sg.items() if v}, "reasons": why_l,
                          "quotes": [item(i) for i in dep_msgs.get(d["id"], [])], "kpis": E["kpis"].get(d["id"], [])[:4]})
        cases.sort(key=lambda x: -x["_s"])
        for c in cases:
            c.pop("_s")
        ranked = [it for _, it in dedup[:60]]
        if any(it["claim_flag"] for it in ranked) or any(k["claim_flag"] for c in cases[:6] for k in c["kpis"]):
            needs.append("claim(수치·최상급) 문구는 대외 사용 전 원문 확인")
        if any(c["quotes"] for c in cases[:6]):
            needs.append("사례 인용(T5)은 사례 원문에서 확인")
        inferred = [n for n, f in (("업종", v_from), ("공간", sp_from), ("제품", p_from)) if f == "inferred"]
        if inferred:
            needs.append(f"문장에서 추론한 {'·'.join(inferred)}이 맞는지 확인")
        return self.envelope("E3", {"context": ctx, "headline": headline, "key_messages": key_messages, "products": prods,
                                    "cases": cases[:6], "ranked": ranked, "n_scored": sum(1 for x in scored if x),
                                    "n_candidates": len(order)},
                             reasons=reasons, needs=needs, modes=["sql", "kg", "rule", "vec", "kw"], t0=t0,
                             tiers=sorted({it["tier"] for it in ranked if it["tier"]}))

    # ── G. 이미지 ──
    def _img_rows(self, where, args, limit=30):
        rows = self.q(f"""SELECT a.id, a.url, a.url_mobile, a.grade_hint, a.grade_hint_reason, a.rights, o.alt, o.caption, o.section_path,
                                 o.context_space_type_id sp, o.context_vertical_id v, o.context_entities_json ents, o.page_type, d.url page_url, d.title
                          FROM image_asset a JOIN image_occurrence o ON o.asset_id=a.id JOIN source_document d ON d.id=o.document_id
                          WHERE {where}""", args)
        best = {}
        for r in rows:
            k = r["id"]
            if k not in best or C.GRADE_PRIORITY.get(r["grade_hint"], 9) < C.GRADE_PRIORITY.get(best[k]["grade_hint"], 9):
                best[k] = r
        out = sorted(best.values(), key=lambda r: (C.GRADE_PRIORITY.get(r["grade_hint"], 9), 0 if r["rights"] == "customer_case" else 1))
        for r in out:
            r["caption_rule"] = "도입사례 사진" if r["rights"] == "customer_case" else "예시 사진(삼성 공식 이미지)"
            r["space_name"] = self.name("space_type", r["sp"]) if r["sp"] else None
            r["entities"] = [[k, i, self.name(k, i)] for k, i in json.loads(r["ents"] or "[]")]
        return out[:limit]

    def G1(self, space, category=None, vertical=None, limit=20):
        """공간 × 카테고리 배치 이미지. 폴백: 공간+카테고리 → 공간 → 카테고리 문맥 → 카테고리 제품 이미지."""
        t0 = time.time()
        cats = self._cat_subtree(category) if category else set()
        fams = set()
        if category:
            fams = {r["id"] for r in self.q("SELECT id FROM product_family")
                    if self._family_cats(r["id"]) & cats}
        tgt_ids = cats | fams

        def ent_match(r):
            return any(e[1] in tgt_ids for e in r["entities"])

        levels = []
        rows = self._img_rows("o.context_space_type_id=?" + (" AND o.context_vertical_id=?" if vertical else ""),
                              (space, vertical) if vertical else (space,), 400)
        if category:
            lv0 = [r for r in rows if ent_match(r)]
            levels.append(("space+category", lv0))
        levels.append(("space_only", rows))
        if category:
            ids = list(tgt_ids)[:900]
            dep = self._img_rows(f"a.id IN (SELECT asset_id FROM depicts WHERE target_id IN ({','.join('?' * len(ids))}))", ids, 400)
            levels.append(("category_context", [r for r in dep if r["grade_hint"] in ("A", "A?C") and r["page_type"] != "pdp_gallery"]))
            levels.append(("category_product_cut", [r for r in dep if r["grade_hint"] == "C"]))
        for lv, rs in levels:
            if rs:
                fb = None if lv == levels[0][0] else lv
                return self.envelope("G1", {"images": rs[:limit], "level": lv}, fallback=fb, modes=["sql", "kg"], t0=t0,
                                     tiers=["T2_official"], needs=["VLM 판정 전: 등급은 페이지 유형·파일명 기반 힌트"])
        return self.envelope("G1", {"images": [], "level": None}, fallback="none", t0=t0)

    def G2(self, kind, ident, limit=20):
        """제품군·카테고리·솔루션이 등장하는 이미지(설치·사례 우선)."""
        t0 = time.time()
        ids = [ident]
        if kind == "category":
            ids = list(self._cat_subtree(ident))
            ids += [r["id"] for r in self.q("SELECT id FROM product_family") if self._family_cats(r["id"]) & set(ids)]
        ph = ",".join("?" * len(ids))
        rows = self._img_rows(f"a.id IN (SELECT asset_id FROM depicts WHERE target_id IN ({ph}))", ids, 500)
        deps = [r["src_id"] for r in self.q(f"SELECT DISTINCT src_id FROM kg_edge WHERE src_kind='deployment' AND rel='USES' AND dst_id IN ({ph})", ids)]
        case_imgs = []
        if deps:
            case_imgs = self._img_rows(f"o.page_type='case_study' AND a.id IN (SELECT asset_id FROM depicts WHERE target_kind='deployment' AND target_id IN ({','.join('?' * len(deps))}))", deps, 200)
        seen, out = set(), []
        for r in sorted(case_imgs + rows, key=lambda r: (C.GRADE_PRIORITY.get(r["grade_hint"], 9), 0 if r["rights"] == "customer_case" else 1)):
            if r["id"] not in seen:
                seen.add(r["id"])
                out.append(r)
        return self.envelope("G2", {"images": out[:limit], "n_total": len(out), "via_deployments": len(deps)}, modes=["sql", "kg"], t0=t0,
                             tiers=["T2_official", "T3_case"])

    def G4(self, family_id, limit=10):
        t0 = time.time()
        rows = self._img_rows("o.page_type='pdp_gallery' AND a.id IN (SELECT asset_id FROM depicts WHERE target_kind='family' AND target_id=?)", (family_id,), limit)
        return self.envelope("G4", {"images": rows}, modes=["sql"], t0=t0, tiers=["T2_official"])

    def G5(self, deployment_id, limit=30):
        t0 = time.time()
        rows = self._img_rows("o.page_type='case_study' AND a.id IN (SELECT asset_id FROM depicts WHERE target_kind='deployment' AND target_id=?)",
                              (deployment_id,), limit)
        return self.envelope("G5", {"images": rows}, modes=["sql"], t0=t0, tiers=["T3_case"])

    def image_search(self, text, limit=20, grade=None):
        """이미지 검색: image_doc(alt·캡션·섹션·맥락) 키워드 + 벡터 → 토큰 포괄도로 재정렬, 같은 점수면 A 등급 우선."""
        t0 = time.time()
        toks = self.query_tokens(text)
        fused = collections.defaultdict(float)
        for r, (aid, _) in enumerate(self.kw_search(" ".join(t for t in toks if len(t) >= 3) or text, "image_fts", "asset_id", 100)):
            fused[aid] += 1 / (60 + r)
        for r, aid in enumerate(self.like_search(toks, "image_doc", "asset_id", "text", 200)):
            fused[aid] += 1 / (60 + r)
        for r, (ref, _) in enumerate(self.vec_search(text, "image", 100)):
            fused[ref.split(":", 1)[1]] += 1 / (60 + r)
        ids = [a for a, _ in sorted(fused.items(), key=lambda x: -x[1])[:400]]
        if not ids:
            return self.envelope("image_search", {"images": []}, t0=t0)
        docs = dict(self.c.execute(f"SELECT asset_id, text FROM image_doc WHERE asset_id IN ({','.join('?' * len(ids))})", ids).fetchall())
        rows = {r["id"]: r for r in self._img_rows(f"a.id IN ({','.join('?' * len(ids))})", ids, 1000)}
        mx = max(fused[a] for a in ids)
        scored = []
        for a in ids:
            if a not in rows or (grade and rows[a]["grade_hint"] not in grade):
                continue
            cov = sum(1 for t in toks if t in (docs.get(a) or "")) / len(toks) if toks else 0
            g = C.GRADE_PRIORITY.get(rows[a]["grade_hint"], 9)
            scored.append((0.4 * fused[a] / mx + 0.6 * cov - 0.02 * g, a))
        scored.sort(key=lambda x: -x[0])
        out = [rows[a] for _, a in scored[:limit]]
        return self.envelope("image_search", {"tokens": toks, "images": out}, modes=["kw", "vec"], t0=t0)

    # ── 엔티티 ──
    def entity(self, kind, ident):
        t0 = time.time()
        table = {"family": "product_family", "model": "product_model", "category": "category", "solution": "solution",
                 "service": "service_product", "vertical": "vertical", "space_type": "space_type", "deployment": "deployment",
                 "capability": "capability"}[kind]
        row = self.q(f"SELECT * FROM {table} WHERE id=?", (ident,))
        if not row:
            return self.envelope("get_entity", None, reasons=["NOT_FOUND"], t0=t0)
        out = {"kind": kind, "id": ident, "row": row[0],
               "aliases": [r["surface"] for r in self.q("SELECT DISTINCT surface FROM alias WHERE target_kind=? AND target_id=?", (kind, ident))],
               "edges_out": collections.defaultdict(list), "edges_in": collections.defaultdict(list)}
        for r in self.q("SELECT rel, dst_kind, dst_id, source_tier, confidence, evidence FROM kg_edge WHERE src_kind=? AND src_id=?", (kind, ident)):
            out["edges_out"][r["rel"]].append({"to": [r["dst_kind"], r["dst_id"]], "name": self.name(r["dst_kind"], r["dst_id"]),
                                               "tier": r["source_tier"], "conf": r["confidence"], "evidence": r["evidence"]})
        for r in self.q("SELECT rel, src_kind, src_id, source_tier, confidence, evidence FROM kg_edge WHERE dst_kind=? AND dst_id=?", (kind, ident)):
            out["edges_in"][r["rel"]].append({"from": [r["src_kind"], r["src_id"]], "name": self.name(r["src_kind"], r["src_id"]),
                                              "tier": r["source_tier"], "conf": r["confidence"]})
        out["mentions_by_source"] = self.q("""SELECT d.page_type, d.url, d.title, count(*) n FROM mention m JOIN source_document d ON d.id=m.document_id
                                              WHERE m.resolved_kind=? AND m.resolved_id=? GROUP BY d.id ORDER BY n DESC LIMIT 40""", (kind, ident))
        out["value_props"] = self.q("SELECT level, text, claim_flag, method FROM value_prop WHERE about_kind=? AND about_id=?", (kind, ident))
        if kind == "family":
            out["models"] = self.q("SELECT model_code, option_name, option_value, is_family_default FROM product_model WHERE family_id=?", (ident,))
            out["key_specs"] = self.q("""SELECT norm_key, attr_name, value_raw, value_num, value_unit FROM spec_value WHERE family_id=? AND norm_key IS NOT NULL
                                         AND model_id=(SELECT id FROM product_model WHERE family_id=? AND is_family_default=1)""", (ident, ident))
            out["tags"] = self.q("SELECT site_group, site_label, site_filter FROM product_tag WHERE family_id=?", (ident,))
            out["features"] = self.q("SELECT headline FROM feature_block WHERE family_id=? ORDER BY seq", (ident,))
            out["provides"] = self.q("SELECT capability_id, rule_id, evidence FROM provides WHERE family_id=?", (ident,))
        out["edges_out"] = dict(out["edges_out"])
        out["edges_in"] = dict(out["edges_in"])
        return self.envelope("get_entity", out, modes=["sql", "kg"], t0=t0)

    # ── 시나리오 체인 ──
    CLAUSE_SPLIT = re.compile(r"\s*(?:[,，;·/]|\s그리고\s|\s및\s|(?<=[가-힣A-Za-z0-9])(?:와|과|랑|하고)\s)\s*")

    def S1(self, text, limit=8):
        """요구사항 문장 → A1/A2 → (절 단위) 공간·카테고리·역량 묶기 → C1 → C2 → D1."""
        t0 = time.time()
        a2 = self.A2(text)
        vertical = a2["result"]["top2"][0]["id"] if a2["result"]["top2"] else None
        clauses = [c for c in self.CLAUSE_SPLIT.split(text) if c and c.strip()]
        groups = []
        carry_space = None
        for cl in clauses:
            links = self.A1(cl)["result"]["links"]
            sps = [l["id"] for l in links if l["type"] == "space_type"]
            cats = [l["id"] for l in links if l["type"] == "category"]
            caps = [l["id"] for l in links if l["type"] == "capability"]
            if not sps and carry_space and (cats or caps):
                sps = [carry_space]
            if sps:
                carry_space = sps[-1]
            if sps or cats or caps:
                groups.append({"clause": cl, "spaces": sps, "categories": cats, "capabilities": caps})
        if not groups:
            groups = [{"clause": text, "spaces": [], "categories": [], "capabilities": []}]
        # 같은 공간 그룹 병합
        merged = collections.OrderedDict()
        for g in groups:
            for sp in (g["spaces"] or [None]):
                m = merged.setdefault(sp, {"space": sp, "clauses": [], "categories": [], "capabilities": []})
                m["clauses"].append(g["clause"])
                m["categories"] += [c for c in g["categories"] if c not in m["categories"]]
                m["capabilities"] += [c for c in g["capabilities"] if c not in m["capabilities"]]
        # 공간 없는 역량·카테고리는 모든 공간에 적용
        glob = merged.pop(None, None)
        if glob and merged:
            for m in merged.values():
                m["categories"] += [c for c in glob["categories"] if c not in m["categories"]]
                m["capabilities"] += [c for c in glob["capabilities"] if c not in m["capabilities"]]
        elif glob:
            merged[None] = glob
        per_space, all_caps, all_targets = [], [], []
        for sp, m in merged.items():
            req = self.q("SELECT capability_id, strength FROM requires WHERE space_type_id=?", (sp,)) if sp else []
            hard = list(m["capabilities"]) + [r["capability_id"] for r in req if r["strength"] == "hard" and r["capability_id"] not in m["capabilities"]]
            soft = [r["capability_id"] for r in req if r["strength"] == "soft" and r["capability_id"] not in hard]
            cat = m["categories"][0] if m["categories"] else None
            ctext = " ".join(m["clauses"])
            c2 = self.C2(hard, category=cat, space=sp, vertical=vertical, limit=limit, soft=soft, text=ctext)
            if cat and hard and ("HARD_CONFLICT" in c2["decision_reasons"] or not c2["result"]["families"]):
                c2b = self.C2(hard, category=None, space=sp, vertical=vertical, limit=limit, soft=soft, text=ctext)
                if c2b["result"]["families"] and "HARD_CONFLICT" not in c2b["decision_reasons"]:
                    c2 = c2b
                    c2["decision_reasons"] = sorted(set(c2["decision_reasons"]) | {"CATEGORY_RELAXED"})
                    cat = None
            per_space.append({"space": sp, "space_name": self.name("space_type", sp) if sp else None, "clauses": m["clauses"],
                              "category": cat, "category_name": self.name("category", cat) if cat else None,
                              "capabilities": {"hard": hard, "soft": soft}, "families": c2["result"]["families"],
                              "solutions": c2["result"]["solutions"][:6], "decision_reasons": c2["decision_reasons"]})
            all_caps += [c for c in hard + soft if c not in all_caps]
            all_targets += [("category", c) for c in m["categories"]] + [("family", f["id"]) for f in c2["result"]["families"][:3]]
        spaces = [p["space"] for p in per_space if p["space"]]
        d1 = self.D1(vertical=vertical, spaces=spaces, targets=all_targets, text=text, limit=5)
        reasons = list(a2["decision_reasons"]) + [r for p in per_space for r in p["decision_reasons"] if r == "HARD_CONFLICT"]
        return self.envelope("S1", {"vertical": a2["result"]["top2"], "by_space": per_space,
                                    "capabilities": [{"id": c, "name": self.name("capability", c)} for c in all_caps],
                                    "similar_cases": d1["result"]["deployments"]},
                             reasons=reasons, modes=["sql", "kg", "rule", "vec"], t0=t0,
                             tiers=["T2_official", "T5_rule_draft"] + (["T5_seed_draft"] if spaces else []),
                             needs=["역량·requires 는 초안(전문가 승인 전)", "판매 상태(단종·미판매)는 사이트 목록 노출 여부만 반영"])

    def S2(self, vertical, space=None):
        """업종(·공간) → 장면: 업종 페이지 장면 + 메시지 + 배치 이미지 + 유사 사례."""
        t0 = time.time()
        b1 = self.B1(vertical)["result"]
        scenes = [s for s in b1["scenes"] if not space or space in s["space_types"]]
        for s in scenes:
            s["value_props"] = self.E1(about=[("industry_section", s["section_id"])])["result"]["tree"]
            sp = s["space_types"][0] if s["space_types"] else None
            s["images"] = self.G1(sp, vertical=None)["result"]["images"][:4] if sp else []
        d1 = self.D1(vertical=vertical, spaces=[space] if space else [], limit=5)["result"]["deployments"]
        return self.envelope("S2", {"vertical": vertical, "space": space, "hero": b1["hero"], "scenes": scenes, "similar_cases": d1},
                             modes=["sql", "kg"], t0=t0, tiers=["T2_official", "T3_case"])


def main():
    ap = argparse.ArgumentParser(description="Winmate KB 질의")
    ap.add_argument("pattern")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--category")
    ap.add_argument("--space")
    ap.add_argument("--vertical")
    ap.add_argument("--caps", help="쉼표 구분 역량 코드")
    ap.add_argument("--product", action="append", default=[], help="E3: kind:id (여러 번)")
    ap.add_argument("--customer", help="E3: 타겟고객")
    ap.add_argument("--text", help="E3: 요구사항 문장")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--db", default=str(DB_PATH))
    a = ap.parse_args()
    kb = KB(a.db)
    p = a.pattern
    x = " ".join(a.args)
    if p == "search":
        r = kb.search(x, k=a.limit)
    elif p == "images":
        r = kb.image_search(x, limit=a.limit)
    elif p == "entity":
        r = kb.entity(a.args[0], a.args[1])
    elif p in ("A1", "A2", "B2", "S1", "E2"):
        r = getattr(kb, p)(x)
    elif p == "B1":
        r = kb.B1(x)
    elif p == "C1":
        r = kb.C1([s for s in (a.space or "").split(",") if s], x or None)
    elif p == "C2":
        r = kb.C2([c for c in (a.caps or "").split(",") if c], category=a.category, space=a.space, vertical=a.vertical, limit=a.limit)
    elif p == "C3":
        r = kb.C3(x)
    elif p == "D1":
        r = kb.D1(vertical=a.vertical, spaces=[s for s in (a.space or "").split(",") if s], text=x or None, limit=a.limit)
    elif p == "D2":
        r = kb.D2(vertical=a.vertical, space=a.space)
    elif p == "E1":
        r = kb.E1(about=[tuple(a.args[:2])] if len(a.args) >= 2 else [], vertical=a.vertical, space=a.space)
    elif p == "E3":
        r = kb.E3(vertical=a.vertical, spaces=[s for s in (a.space or "").split(",") if s],
                  products=[tuple(v.split(":", 1)) for v in a.product], customer=a.customer, text=a.text or x or None)
    elif p == "G1":
        r = kb.G1(x, category=a.category, vertical=a.vertical, limit=a.limit)
    elif p == "G2":
        r = kb.G2(a.args[0], a.args[1], limit=a.limit)
    elif p == "S2":
        r = kb.S2(x or a.vertical, a.space)
    else:
        raise SystemExit(f"unknown pattern {p}")
    print(json.dumps(r, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
