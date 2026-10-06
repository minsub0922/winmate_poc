#!/usr/bin/env python3
"""검색 인덱스 빌드: entity_doc/entity_fts, image_doc/image_fts, vec_index(LSA 밀집 벡터).

신경망 임베딩 모델을 받을 수 없는 환경(HF 차단)이라 문자 n-gram TF-IDF → TruncatedSVD(LSA) 로
밀집 벡터를 만든다. 같은 인터페이스(vec_index.model)로 나중에 신경망 임베딩으로 교체할 수 있다.
"""
from __future__ import annotations

import collections
import json
import os
import sqlite3
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[1]
KB_DIR = Path(os.environ.get("WKB_KB", ROOT / "kb"))
DB_PATH = KB_DIR / "winmate_kb.sqlite"
MODEL_DIR = KB_DIR / "models"
MODEL_NAME = "lsa_char24_v2"
DIM = 192
MAX_FEATURES = 45000


def names(c):
    out = {}
    for kind, sql in {
        "family": "SELECT id, name_ko FROM product_family",
        "model": "SELECT id, model_code FROM product_model",
        "category": "SELECT id, name_ko FROM category",
        "solution": "SELECT id, name_ko FROM solution",
        "service": "SELECT id, name_ko FROM service_product",
        "vertical": "SELECT id, coalesce(name_ko, name_en) FROM vertical",
        "space_type": "SELECT id, name_ko FROM space_type",
        "deployment": "SELECT id, title FROM deployment",
        "capability": "SELECT id, name_ko FROM capability",
    }.items():
        for i, n in c.execute(sql):
            out[(kind, i)] = n
    return out


def entity_docs(c, N):
    docs = {}

    def add(kind, i, name, parts):
        text = " | ".join(p for p in parts if p)
        docs[(kind, i)] = (name or i, text)

    fam_tags = collections.defaultdict(list)
    for fid, lab, flt in c.execute("SELECT family_id, coalesce(site_label, tag_value), site_filter FROM product_tag"):
        fam_tags[fid].append(lab or flt)
    fam_models = collections.defaultdict(list)
    for fid, code, ov in c.execute("SELECT family_id, model_code, option_value FROM product_model"):
        fam_models[fid].append(code + (f"({ov})" if ov else ""))
    fam_feat = collections.defaultdict(list)
    for fid, h in c.execute("SELECT family_id, headline FROM feature_block WHERE headline IS NOT NULL ORDER BY seq"):
        fam_feat[fid].append(h)
    fam_caps = collections.defaultdict(list)
    for fid, cap in c.execute("SELECT family_id, capability_id FROM provides"):
        fam_caps[fid].append(N.get(("capability", cap), cap))
    fam_cats = collections.defaultdict(list)
    for fid, cid in c.execute("SELECT family_id, category_id FROM family_category"):
        fam_cats[fid].append(N.get(("category", cid), cid))
    keyspec = collections.defaultdict(list)
    for fid, attr, raw in c.execute("""SELECT family_id, attr_name, value_raw FROM spec_value
            WHERE norm_key IN ('screen_size_cm','screen_size_inch','brightness_nit','operation_hours','touch','cooling_capacity_kw',
                               'ip_rating','resolution','capacity_l','os','cpu') GROUP BY family_id, attr_name"""):
        keyspec[fid].append(f"{attr} {raw}")
    for fid, name, cid, sub, code, usp, desc in c.execute(
            "SELECT id, name_ko, category_id, subcategory_slug, default_model_code, usp_json, pdp_description FROM product_family"):
        usp = " / ".join(json.loads(usp or "[]") or [])
        add("family", fid, name, [name, code, N.get(("category", cid)), N.get(("category", f"{cid}__{sub}")),
                                  " ".join(fam_cats[fid]), usp, " / ".join(fam_feat[fid][:8]), ", ".join(fam_tags[fid]),
                                  ", ".join(fam_caps[fid]), "; ".join(keyspec[fid][:10]), " ".join(fam_models[fid][:30]), desc])
    alias = collections.defaultdict(set)
    for s, k, t in c.execute("SELECT surface, target_kind, target_id FROM alias"):
        alias[(k, t)].add(s)
    for cid, name, parent in c.execute("SELECT id, name_ko, parent_id FROM category"):
        add("category", cid, name, [name, N.get(("category", parent)), " ".join(sorted(alias[("category", cid)]))])
    vps = collections.defaultdict(list)
    for k, t, txt in c.execute("SELECT about_kind, about_id, text FROM value_prop"):
        vps[(k, t)].append(txt)
    for sid, name, aliases, kind in c.execute("SELECT id, name_ko, aliases_json, kind FROM solution"):
        add("solution", sid, name, [name, " ".join(json.loads(aliases or "[]")), kind, " / ".join(vps[("solution", sid)][:12])])
    for sid, name, aliases in c.execute("SELECT id, name_ko, aliases_json FROM service_product"):
        add("service", sid, name, [name, " ".join(json.loads(aliases or "[]")), " / ".join(vps[("service", sid)][:12])])
    sec_titles = collections.defaultdict(list)
    for v, t, lab in c.execute("SELECT vertical_id, title, space_label FROM industry_section WHERE vertical_id IS NOT NULL"):
        sec_titles[v].append(f"{t}{' [' + lab + ']' if lab else ''}")
    for vid, nko, nen, scheme in c.execute("SELECT id, name_ko, name_en, scheme FROM vertical"):
        add("vertical", vid, nko or nen, [nko, nen, scheme, " / ".join(sec_titles[vid][:30])])
    sp_labels = collections.defaultdict(set)
    for lab, sp in c.execute("SELECT label, space_type_id FROM space_label WHERE space_type_id IS NOT NULL"):
        sp_labels[sp].add(lab)
    for sp, t in c.execute("SELECT space_type_id, title FROM industry_section WHERE space_type_id IS NOT NULL"):
        sp_labels[sp].add(t)
    for sid, name in c.execute("SELECT id, name_ko FROM space_type"):
        add("space_type", sid, name, [name, sid, " / ".join(sorted(sp_labels[sid]))[:1500]])
    dep_items = collections.defaultdict(list)
    for d, raw in c.execute("SELECT deployment_id, item_raw FROM deployment_item"):
        dep_items[d].append(raw)
    dep_sp = collections.defaultdict(list)
    for d, raw in c.execute("SELECT deployment_id, space_raw FROM deployment_space"):
        dep_sp[d].append(raw)
    for did, title, ind, cust, scale in c.execute("SELECT id, title, industry_raw_json, customer_type, scale FROM deployment"):
        add("deployment", did, title, [title, " ".join(json.loads(ind or "[]") or []), cust, scale, ", ".join(dep_sp[did]),
                                       ", ".join(dep_items[did][:20])])
    for cid, name, desc in c.execute("SELECT id, name_ko, description FROM capability"):
        add("capability", cid, name, [name, desc])
    return docs


def image_docs(c, N):
    acc = collections.defaultdict(list)
    for aid, alt, cap, sec, ptype, sp, vert, ents, title in c.execute(
            """SELECT o.asset_id, o.alt, o.caption, o.section_path, o.page_type, o.context_space_type_id, o.context_vertical_id,
                      o.context_entities_json, d.title FROM image_occurrence o LEFT JOIN source_document d ON d.id=o.document_id"""):
        parts = [alt, cap, sec, title, ptype, N.get(("space_type", sp)), N.get(("vertical", vert))]
        for k, i in json.loads(ents or "[]") or []:
            parts.append(N.get((k, i)))
        acc[aid] += [p for p in parts if p]
    for aid, k, i in c.execute("SELECT asset_id, target_kind, target_id FROM depicts"):
        if N.get((k, i)):
            acc[aid].append(N[(k, i)])
    for aid, gh, reason in c.execute("SELECT id, grade_hint, grade_hint_reason FROM image_asset"):
        acc[aid] += [f"grade:{gh}" if gh else "", reason or ""]
    out = {}
    for aid, parts in acc.items():
        seen, uniq = set(), []
        for p in parts:
            if p and p not in seen:
                seen.add(p)
                uniq.append(p)
        out[aid] = " | ".join(uniq)[:3000]
    return out


def main():
    c = sqlite3.connect(DB_PATH)
    N = names(c)
    for t in ("entity_doc", "entity_fts", "image_doc", "image_fts", "vec_index"):
        c.execute(f"DELETE FROM {t}")
    E = entity_docs(c, N)
    for (k, i), (name, text) in E.items():
        c.execute("INSERT INTO entity_doc VALUES (?,?,?,?)", (k, i, name, text))
        c.execute("INSERT INTO entity_fts(name, text, kind, id) VALUES (?,?,?,?)", (name, text, k, i))
    I = image_docs(c, N)
    for aid, text in I.items():
        c.execute("INSERT INTO image_doc VALUES (?,?)", (aid, text))
        c.execute("INSERT INTO image_fts(text, asset_id) VALUES (?,?)", (text, aid))
    chunks = c.execute("SELECT id, coalesce(section_path,'') || ' ' || text FROM text_chunk").fetchall()
    corpus = [("chunk", r[0], r[1]) for r in chunks] + [("entity", f"{k}:{i}", f"{n} {t}") for (k, i), (n, t) in E.items()] \
        + [("image", aid, t) for aid, t in I.items()]
    texts = [t for *_, t in corpus]
    if len(texts) < 10:
        print("too few docs for LSA", len(texts))
        c.commit()
        return
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2, max_df=0.5, sublinear_tf=True, max_features=MAX_FEATURES,
                          dtype=np.float32)
    X = vec.fit_transform(texts)
    dim = min(DIM, X.shape[1] - 1, X.shape[0] - 1)
    svd = TruncatedSVD(n_components=dim, random_state=0)
    Z = svd.fit_transform(X).astype(np.float32)
    Z /= np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9
    for (space, ref, _), z in zip(corpus, Z):
        c.execute("INSERT INTO vec_index VALUES (?,?,?,?,?)", (f"{space}:{ref}" if space != "chunk" else ref, space, MODEL_NAME,
                                                             dim, z.astype(np.float16).tobytes()))   # float16 저장(용량 절반)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    svd.components_ = svd.components_.astype(np.float32)
    for old in MODEL_DIR.glob("*.joblib"):
        old.unlink()
    vec.stop_words_ = None   # 학습 중 잘린 n-gram 목록(질의에 불필요, 용량 큼)
    joblib.dump({"tfidf": vec, "svd": svd, "name": MODEL_NAME, "dim": dim}, MODEL_DIR / f"{MODEL_NAME}.joblib", compress=3)
    for k, v in {"index.model": MODEL_NAME, "index.dim": dim, "index.n_chunk": len(chunks), "index.n_entity": len(E),
                 "index.n_image": len(I), "index.explained_variance": round(float(svd.explained_variance_ratio_.sum()), 4)}.items():
        c.execute("INSERT OR REPLACE INTO kb_meta VALUES (?,?)", (k, str(v)))
    c.commit()
    c.execute("VACUUM")
    print(json.dumps({"entities": len(E), "images": len(I), "chunks": len(chunks), "dim": dim,
                      "explained_variance": round(float(svd.explained_variance_ratio_.sum()), 4)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
