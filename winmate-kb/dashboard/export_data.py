#!/usr/bin/env python3
"""KB(SQLite) → 검증 대시보드 데이터 파일(JSON·gzip·바이너리).

python dashboard/export_data.py            # dashboard/build/data/ 에 쓴다 → build_site.py 가 조각내 site/data/ 로
대시보드는 이 파일들만 읽는다(DB 를 그대로 옮긴 사본, 가공은 표시용 조인·인덱스 정도).
"""
from __future__ import annotations

import collections
import gzip
import json
import os
import sqlite3
import struct
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build"))
import curation as C  # noqa: E402

DB = Path(os.environ.get("WKB_DB", ROOT / "kb" / "winmate_kb.sqlite"))
OUT = Path(os.environ.get("WKB_DASH_OUT", ROOT / "dashboard" / "build" / "data"))
OUT.mkdir(parents=True, exist_ok=True)

c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row


def rows(sql, args=()):
    return [tuple(r) for r in c.execute(sql, args)]


def dump(name, obj, gz=True):
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    p = OUT / (name + (".json.gz" if gz else ".json"))
    p.write_bytes(gzip.compress(raw, 9, mtime=0) if gz else raw)
    print(f"{p.name:28s} raw {len(raw)/1e6:6.2f} MB  file {p.stat().st_size/1e6:6.2f} MB")


# ── 공통: 문서·섹션 문자열 표(출처 인덱스) ──────────────────────────
docs = rows("SELECT id, url, title, page_type, locale, kind FROM source_document ORDER BY rowid")
DOC = {d[0]: i for i, d in enumerate(docs)}
SEC, SECI = [], {}


def sec(s):
    if s is None:
        return -1
    if s not in SECI:
        SECI[s] = len(SEC)
        SEC.append(s)
    return SECI[s]


occ = {}
for oid, did, sp in c.execute("""SELECT o.id, o.document_id, b.section_path FROM occurrence o
                                 LEFT JOIN document_block b ON b.id=o.block_id"""):
    occ[oid] = (DOC.get(did, -1), sp)


def src(oid):
    """출처 occurrence → [문서 인덱스, 섹션 인덱스]."""
    if not oid or oid not in occ:
        return None
    d, s = occ[oid]
    return [d, sec(s)]


# ── core: 메타·리포트·온톨로지 ────────────────────────────────────
meta = dict(rows("SELECT key, value FROM kb_meta"))
probes = json.loads(meta.pop("qa.probes", "[]") or "[]")
tests = []
tj = ROOT / "dashboard" / "build" / "tests.json"
tj.parent.mkdir(parents=True, exist_ok=True)
if os.environ.get("WKB_SKIP_TESTS") != "1" or not tj.exists():
    env = dict(os.environ, WKB_TEST_JSON=str(tj), WKB_TEST_REPORT=str(ROOT / "dashboard" / "build" / "SCENARIO_TEST_REPORT.md"))
    subprocess.run([sys.executable, str(ROOT / "tests" / "test_scenarios.py")], check=True, env=env, cwd=ROOT,
                   stdout=subprocess.DEVNULL)
tests = json.loads(tj.read_text())
counts = {t: c.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in [
    "source_document", "document_block", "category", "product_family", "product_model", "product_tag", "spec_value",
    "feature_block", "vertical", "space_type", "capability", "provides", "requires", "industry_section", "industry_section_item",
    "deployment", "deployment_item", "kpi_claim", "value_prop", "image_asset", "image_occurrence", "alias", "mention", "kg_edge",
    "text_chunk"]}
core = {
    "meta": meta, "counts": counts,
    "dr": rows("SELECT dr, name, metric, value, status, note FROM dr_metric ORDER BY dr"),
    "scen": rows("SELECT scenario, name, status, reasons FROM scenario_status ORDER BY rowid"),
    "probes": probes,
    "tests": [{k: t.get(k) for k in ("scenario", "name", "pass", "detail", "lines", "decision", "reasons")} for t in tests],
    "docs": [[d[1], d[2], d[3], d[4]] for d in docs],
    "V": rows("SELECT id, code, name_ko, name_en, parent_id, scheme, url, status FROM vertical ORDER BY rowid"),
    "S": rows("SELECT id, code, name_ko, origin, status FROM space_type ORDER BY rowid"),
    "SL": rows("SELECT label, locale, space_type_id, method, status, occurrences FROM space_label ORDER BY occurrences DESC"),
    "K": rows("SELECT id, code, name_ko, description FROM capability ORDER BY rowid"),
    "CAT": rows("SELECT id, parent_id, name_ko, level, list_url, origin FROM category ORDER BY rowid"),
    "SOL": rows("SELECT id, code, name_ko, aliases_json, kind, url FROM solution ORDER BY rowid"),
    "SVC": rows("SELECT id, code, name_ko, aliases_json, target_category, url FROM service_product ORDER BY rowid"),
    "SEG": rows("SELECT winmate_segment, name_ko, kr_vertical_codes, us_vertical_codes, catalog_chapter, status FROM segment_mapping"),
    "REQ": rows("SELECT space_type_id, capability_id, strength, status, origin FROM requires ORDER BY rowid"),
    "CRULE": rows("SELECT id, capability_id, category, expression, params_json, explanation_ko, status, origin FROM capability_rule"),
}

# ── 제품: 제품군·모델·태그·역량·핵심 스펙 ────────────────────────────
fams = []
fam_cats = collections.defaultdict(list)
for fid, cid, role in c.execute("SELECT family_id, category_id, role FROM family_category ORDER BY rowid"):
    fam_cats[fid].append([cid, role])
for r in c.execute("""SELECT id, goods_id, category_id, subcategory_slug, name_ko, default_model_code, marketing_model, grp_path,
                             detail_url, usp_json, sale_status_code, registered_at, pdp_title, pdp_description, ctg1, ctg2,
                             source_occurrence_id, source_tier FROM product_family ORDER BY rowid"""):
    r = dict(r)
    fams.append({"id": r["id"], "goods": r["goods_id"], "cat": r["category_id"], "sub": r["subcategory_slug"], "name": r["name_ko"],
                 "model": r["default_model_code"], "mkt": r["marketing_model"], "grp": r["grp_path"], "url": r["detail_url"],
                 "usp": json.loads(r["usp_json"] or "[]"), "sale": r["sale_status_code"], "reg": r["registered_at"],
                 "pdpt": r["pdp_title"], "pdpd": r["pdp_description"], "ctg": [r["ctg1"], r["ctg2"]],
                 "cats": fam_cats[r["id"]], "src": src(r["source_occurrence_id"]), "tier": r["source_tier"]})
models = rows("""SELECT id, model_code, family_id, option_name, option_value, is_family_default, sold_out_flag FROM product_model
                 ORDER BY rowid""")
tags = rows("SELECT family_id, tag_kind, tag_value, site_filter, category_id, site_group, site_label, source_tier, method FROM product_tag ORDER BY rowid")
prov = rows("SELECT family_id, model_id, capability_id, rule_id, evidence, source_tier, method FROM provides ORDER BY rowid")
keyspec = rows("""SELECT s.family_id, s.norm_key, s.attr_name, s.value_raw, s.value_num, s.value_unit FROM spec_value s
                  JOIN product_model m ON m.id=s.model_id AND m.is_family_default=1 WHERE s.norm_key IS NOT NULL ORDER BY s.rowid""")
feat_heads = collections.defaultdict(list)
for fid, h in c.execute("SELECT family_id, headline FROM feature_block WHERE headline IS NOT NULL AND headline<>'' ORDER BY family_id, seq"):
    if h not in feat_heads[fid]:
        feat_heads[fid].append(h)
nspec = dict(rows("SELECT family_id, count(*) FROM spec_value GROUP BY family_id"))
nfeat = dict(rows("SELECT family_id, count(*) FROM feature_block GROUP BY family_id"))
for f in fams:
    f["heads"] = feat_heads[f["id"]][:14]
    f["nspec"] = nspec.get(f["id"], 0)
    f["nfeat"] = nfeat.get(f["id"], 0)

# ── 업종 장면 ────────────────────────────────────────────────────
sections = []
for r in c.execute("""SELECT id, vertical_id, document_id, seq, kind, title, description, tagline, space_label, space_type_id,
                             space_types_json, space_method, labels_json, chips_json, source_occurrence_id, source_tier, method
                      FROM industry_section ORDER BY rowid"""):
    r = dict(r)
    sections.append([r["id"], r["vertical_id"], DOC.get(r["document_id"], -1), r["seq"], r["kind"], r["title"], r["description"],
                     r["tagline"], r["space_label"], r["space_type_id"], json.loads(r["space_types_json"] or "[]"), r["space_method"],
                     json.loads(r["labels_json"] or "[]"), json.loads(r["chips_json"] or "[]"), src(r["source_occurrence_id"]),
                     r["source_tier"], r["method"]])
items = []
for r in c.execute("""SELECT id, section_id, seq, item_kind, item_name, item_tagline, link_url, link_path, link_filter, item_space_label,
                             item_space_type_id, target_kind, target_id, resolve_method, confidence, image_ids_json, source_occurrence_id,
                             source_tier FROM industry_section_item ORDER BY rowid"""):
    r = dict(r)
    items.append([r["id"], r["section_id"], r["seq"], r["item_kind"], r["item_name"], r["item_tagline"], r["link_url"], r["link_filter"],
                  r["item_space_label"], r["item_space_type_id"], r["target_kind"], r["target_id"], r["resolve_method"], r["confidence"],
                  json.loads(r["image_ids_json"] or "[]"), src(r["source_occurrence_id"]), r["source_tier"]])

# ── 사례 ────────────────────────────────────────────────────────
deps = []
for r in c.execute("""SELECT id, prior_id, title, date, url, format, document_id, customer_type, scale, quote, industry_raw_json,
                             product_group_json, solution_group_json, vertical_ids_json, site_industry_text, site_scale_text, source_tier, method
                      FROM deployment ORDER BY rowid"""):
    r = dict(r)
    deps.append({"id": r["id"], "title": r["title"], "date": r["date"], "url": r["url"], "format": r["format"],
                 "doc": DOC.get(r["document_id"], -1) if r["document_id"] else -1, "cust": r["customer_type"], "scale": r["scale"],
                 "quote": r["quote"], "ind": json.loads(r["industry_raw_json"] or "[]"), "pg": json.loads(r["product_group_json"] or "[]"),
                 "sg": json.loads(r["solution_group_json"] or "[]"), "v": json.loads(r["vertical_ids_json"] or "[]"),
                 "sind": r["site_industry_text"], "sscale": r["site_scale_text"], "tier": r["source_tier"], "method": r["method"]})
dep_items = rows("""SELECT deployment_id, item_raw, target_level, target_kind, target_id, resolve_method, confidence, source, link_url, source_tier
                    FROM deployment_item ORDER BY rowid""")
dep_space = rows("SELECT deployment_id, space_raw, space_type_id, method FROM deployment_space ORDER BY rowid")
dep_need = rows("SELECT deployment_id, need_raw, kind FROM deployment_need ORDER BY rowid")
kpis = rows("SELECT id, deployment_id, text, has_number, claim_flag, source_tier, method FROM kpi_claim ORDER BY rowid")
dep_photo = [r[0] for r in c.execute("SELECT DISTINCT target_id FROM depicts WHERE target_kind='deployment' ORDER BY target_id")]

# ── 그래프·별칭·언급 집계 ──────────────────────────────────────────
edges = rows("SELECT src_kind, src_id, rel, dst_kind, dst_id, source_tier, method, confidence, evidence FROM kg_edge ORDER BY rowid")
alias = rows("SELECT surface, surface_norm, target_kind, target_id, kind, source FROM alias ORDER BY rowid")
ment = rows("""SELECT resolved_kind, resolved_id, document_id, count(*) n FROM mention WHERE resolved_id IS NOT NULL
               GROUP BY resolved_kind, resolved_id, document_id""")
ment = [[k, i, DOC.get(d, -1), n] for k, i, d, n in ment]
ment_types = rows("""SELECT resolved_kind, resolved_id, method, count(*) FROM mention WHERE resolved_id IS NOT NULL
                     GROUP BY resolved_kind, resolved_id, method""")

kw = {"KW_KO": C.KW_KO, "KW_EN": C.KW_EN, "REQ_CAP": C.REQ_CAP_KEYWORDS, "KIND_PRIORITY": C.KIND_PRIORITY,
      "GRADE_PRIORITY": C.GRADE_PRIORITY, "RESIDENTIAL": sorted(C.RESIDENTIAL_VERTICALS),
      "COMMERCIAL_KITCHEN": sorted(C.COMMERCIAL_KITCHEN_VERTICALS)}

graph = {"fam": fams, "models": models, "tags": tags, "prov": prov, "keyspec": keyspec, "sections": sections, "items": items,
         "deps": deps, "dep_items": dep_items, "dep_space": dep_space, "dep_need": dep_need, "kpis": kpis, "dep_photo": dep_photo,
         "edges": edges, "alias": alias, "ment": ment, "ment_types": ment_types, "kw": kw}

# ── 메시지(value_prop) ─────────────────────────────────────────
vps = [[r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], src(r[10]), r[11], r[12]] for r in c.execute(
    """SELECT id, level, text, parent_id, about_kind, about_id, vertical_id, space_type_id, locale, claim_flag, source_occurrence_id,
              source_tier, method FROM value_prop ORDER BY rowid""")]

# ── 상품 상세(지연 로딩): 특장점 블록·스펙 전체 ─────────────────────
feats = [[r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], src(r[10]), r[11]] for r in c.execute(
    """SELECT id, family_id, seq, parent_seq, component_type, headline, sub, body, disclaimer, n_images, source_occurrence_id, source_tier
       FROM feature_block ORDER BY family_id, seq""")]
specs = [[r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], src(r[9]), r[10]] for r in c.execute(
    """SELECT model_id, family_id, group_name, attr_name, value_raw, norm_key, value_num, value_num2, value_unit, source_occurrence_id, method
       FROM spec_value ORDER BY rowid""")]

# ── 이미지 ───────────────────────────────────────────────────────
assets = rows("SELECT id, url, url_mobile, media_type, grade_hint, grade_hint_reason, rights, n_occurrences, vlm_status FROM image_asset ORDER BY rowid")
AIDX = {a[0]: i for i, a in enumerate(assets)}
iocc = [[AIDX[r[0]], DOC.get(r[1], -1), r[2], r[3], r[4], sec(r[5]), r[6], r[7], json.loads(r[8] or "[]")] for r in c.execute(
    """SELECT asset_id, document_id, page_type, alt, caption, section_path, context_space_type_id, context_vertical_id, context_entities_json
       FROM image_occurrence ORDER BY rowid""")]
depicts = [[AIDX[r[0]], r[1], r[2], r[3], r[4]] for r in c.execute(
    "SELECT asset_id, target_kind, target_id, level_label, confidence FROM depicts ORDER BY rowid")]

# ── 검색 문서(브라우저 검색 엔진용, rowid 순서 = SQLite 스캔 순서) ─────────────
chunks = [[r[0], DOC.get(r[1], -1), r[2], r[3], r[4], json.loads(r[5] or "[]")] for r in c.execute(
    "SELECT id, document_id, page_type, section_path, text, entity_refs_json FROM text_chunk ORDER BY rowid")]
edocs = rows("SELECT kind, id, name, text FROM entity_doc ORDER BY rowid")
idocs = rows("SELECT asset_id, text FROM image_doc ORDER BY rowid")
search = {"chunks": chunks, "edocs": edocs, "idocs": idocs}

core["SEC"] = SEC
dump("core", core)
dump("graph", graph)
dump("msgs", vps)
dump("pdp", {"feats": feats, "specs": specs})
dump("images", {"assets": assets, "occ": iocc, "depicts": depicts})
dump("search", search)

# ── 벡터: LSA 모델(TF-IDF 어휘·idf + SVD 성분 float16) · 문서 벡터 float16 ──────────────
import joblib  # noqa: E402

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    m = joblib.load(sorted((ROOT / "kb" / "models").glob("*.joblib"))[-1])
tf, svd = m["tfidf"], m["svd"]
vocab = [None] * len(tf.vocabulary_)
for g, i in tf.vocabulary_.items():
    vocab[i] = g
comp = svd.components_.astype(np.float32).T.copy()          # (n_feat, dim)
idf = tf.idf_.astype(np.float32)
nf, dim = comp.shape
# float16 성분: int8 이면 질의 벡터가 흔들려 점수가 0.001 단위로 Python 과 달라진다
(OUT / "lsa.bin").write_bytes(struct.pack("<4sII", b"WLSH", nf, dim) + idf.tobytes() + comp.astype(np.float16).tobytes())
dump("lsa_vocab", {"name": m["name"], "dim": int(dim), "vocab": vocab, "params": {"analyzer": tf.analyzer, "ngram": list(tf.ngram_range),
                                                                                   "sublinear_tf": tf.sublinear_tf, "lowercase": tf.lowercase}})
print(f"lsa.bin {(OUT / 'lsa.bin').stat().st_size/1e6:.2f} MB")

# 문서 벡터: DB 의 float16 값 그대로. 엔티티·이미지(요구사항 질의·이미지 검색) / 청크(원문 검색) 파일 분리 → 필요한 것만 받는다
if (OUT / "vec.bin").exists():
    (OUT / "vec.bin").unlink()
vrefs, files = {}, {"vec_core.bin": ["entity", "image"], "vec_chunk.bin": ["chunk"]}
for fname, spaces in files.items():
    blob = bytearray(struct.pack("<4sI", b"WVEH", dim))
    for space in spaces:
        rs = c.execute("SELECT ref, vec FROM vec_index WHERE space=? ORDER BY rowid", (space,)).fetchall()
        M = np.vstack([np.frombuffer(r[1], dtype=np.float16) for r in rs])
        vrefs[space] = [r[0] for r in rs]
        blob += struct.pack("<I", M.shape[0]) + M.tobytes()
    (OUT / fname).write_bytes(bytes(blob))
    print(f"{fname} {(OUT / fname).stat().st_size/1e6:.2f} MB")
dump("vec_refs", {"dim": int(dim), "files": files, "refs": vrefs})

# ── 썸네일: dashboard/build/thumbs_pack*.bin(브라우저 탭에서 만든 webp 묶음, 'WTHB' 형식) → 지연 로딩용 묶음 ──
# 화면이 필요한 묶음만 받도록 관련 이미지끼리 모은다: 0) 제품군 대표 이미지 1) 업종·랜딩·솔루션 2) 도입사례(문서별) 3) 상품 상세(제품군별) 4) US
for old in OUT.glob("thumbs*"):
    old.unlink()
packs_in = sorted((ROOT / "dashboard" / "build").glob("thumbs_pack*.bin"))
if packs_in:
    def fnv36(s):
        h = 0x811c9dc5
        for b in s.encode("utf-8"):
            h = ((h ^ b) * 0x01000193) & 0xffffffff
        a, o = "0123456789abcdefghijklmnopqrstuvwxyz", ""
        while True:
            h, r = divmod(h, 36)
            o = a[r] + o
            if not h:
                return o
    th = {}
    for pf in packs_in:
        raw = pf.read_bytes()
        assert raw[:4] == b"WTHB", pf
        hl = struct.unpack("<I", raw[4:8])[0]
        off = 8 + hl
        for h, w, hh, w0, h0, ln in json.loads(raw[8:8 + hl]):
            th.setdefault(h, (w, hh, raw[off:off + ln]))
            off += ln
    first = {}
    for ai, di, pt in ((o[0], o[1], o[2]) for o in iocc):
        first.setdefault(ai, (pt, di))
    fam_of = {}
    for ai, kind, tid, *_ in depicts:
        if kind == "family":
            fam_of.setdefault(ai, tid)
    gallery_first = {}
    for ai, kind, tid, *_ in depicts:
        if kind == "family" and first.get(ai, ("",))[0] == "pdp_gallery":
            gallery_first.setdefault(tid, ai)
    gf = set(gallery_first.values())

    def group(ai):
        pt, di = first.get(ai, ("", -1))
        if ai in gf:
            return (0, "", di)
        if pt in ("industry", "landing", "solution", "service"):
            return (1, "", di)
        if pt == "case_study":
            return (2, "", di)
        if pt.startswith("pdp"):
            return (3, fam_of.get(ai, ""), di)
        return (4, "", di)
    order = sorted(range(len(assets)), key=lambda ai: (group(ai), ai))
    PACK = 2_500_000
    index, packs, cur = {}, [], bytearray()
    for ai in order:
        a = assets[ai]
        h = fnv36(C.img_key(a[1] or a[2]) or "")
        if h not in th:
            continue
        w, hh, buf = th[h]
        if len(cur) + len(buf) > PACK and cur:
            packs.append(cur)
            cur = bytearray()
        index[a[0]] = [len(packs), len(cur), len(buf), w, hh]
        cur += buf
    if cur:
        packs.append(cur)
    for n, b in enumerate(packs):
        (OUT / f"thumbs_{n:02d}.bin").write_bytes(bytes(b))
    dump("thumbs", {"packs": len(packs), "idx": index})
    print(f"thumbs: {len(index)} / {len(assets)} images in {len(packs)} packs, {sum(len(b) for b in packs)/1e6:.2f} MB")
