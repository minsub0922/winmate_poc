"""대시보드 썸네일 우선순위 자산 선택 → 키 해시 목록(브라우저 탭에서 썸네일 생성용)."""
import json, sqlite3, sys, collections
sys.path.insert(0, "build")
import curation as C

c = sqlite3.connect("kb/winmate_kb.sqlite")
c.row_factory = sqlite3.Row
GP = C.GRADE_PRIORITY
sel = collections.OrderedDict()

def add(aid, why):
    sel.setdefault(aid, why)

rows = c.execute("""SELECT a.id, a.url, a.url_mobile, a.grade_hint, a.media_type, o.page_type, o.document_id, o.id oid
                    FROM image_asset a JOIN image_occurrence o ON o.asset_id=a.id ORDER BY o.id""").fetchall()
by_doc = collections.defaultdict(list)
for r in rows:
    if r["media_type"] not in ("image", "animation"):
        continue
    by_doc[(r["page_type"], r["document_id"])].append(r)

# 1) 업종 장면 항목·섹션에 붙은 이미지 전부
for r in c.execute("SELECT image_ids_json FROM industry_section_item WHERE image_ids_json IS NOT NULL"):
    for a in json.loads(r[0] or "[]"):
        add(a, "industry_item")
# 2) 업종·랜딩·솔루션·서비스 페이지: E 제외 전부
for (pt, d), rs in by_doc.items():
    if pt in ("industry", "landing", "solution", "service"):
        for r in rs:
            if r["grade_hint"] != "E":
                add(r["id"], pt)
# 3) 도입사례: 문서당 A 등급 최대 4장
for (pt, d), rs in by_doc.items():
    if pt == "case_study":
        n = 0
        for r in sorted(rs, key=lambda r: GP.get(r["grade_hint"], 9)):
            if r["grade_hint"] in ("A", "C") and n < 4:
                add(r["id"], "case"); n += 1
# 4) 제품 갤러리 첫 장(제품군당 1)
fam_first = {}
for r in c.execute("""SELECT d.target_id fid, a.id FROM depicts d JOIN image_asset a ON a.id=d.asset_id
                      JOIN image_occurrence o ON o.asset_id=a.id WHERE d.target_kind='family' AND o.page_type='pdp_gallery'
                      ORDER BY o.id"""):
    fam_first.setdefault(r["fid"], r["id"])
for fid, a in fam_first.items():
    add(a, "gallery_first")
# 5) PDP 특장점 A 등급 전부 + A?C·D 는 제품군당 1장 (등급 검수 표본)
fam_feat = collections.defaultdict(lambda: collections.Counter())
for r in c.execute("""SELECT d.target_id fid, a.id, a.grade_hint g FROM depicts d JOIN image_asset a ON a.id=d.asset_id
                      JOIN image_occurrence o ON o.asset_id=a.id WHERE d.target_kind='family' AND o.page_type='pdp_feature'
                      ORDER BY o.id"""):
    if r["g"] == "A":
        add(r["id"], "pdp_A")
    elif r["g"] in ("A?C", "D", "C") and fam_feat[r["fid"]][r["g"]] < 1:
        fam_feat[r["fid"]][r["g"]] += 1
        add(r["id"], "pdp_" + r["g"])
# 6) US 업종 섹션: 섹션당 1장
for (pt, d), rs in by_doc.items():
    if pt in ("us_vertical", "us_solution", "us_landing"):
        seen_sec = set()
        for r in rs:
            if r["grade_hint"] == "E":
                continue
            o = c.execute("SELECT section_path FROM image_occurrence WHERE id=?", (r["oid"],)).fetchone()[0]
            if o not in seen_sec:
                seen_sec.add(o); add(r["id"], pt)

assets = {r["id"]: r for r in c.execute("SELECT id, url, url_mobile FROM image_asset")}
out = []
for aid, why in sel.items():
    a = assets.get(aid)
    if not a:
        continue
    u = a["url"] or a["url_mobile"]
    out.append({"id": aid, "url": u, "key": C.img_key(u), "why": why})
print(len(out), collections.Counter(o["why"] for o in out))
hosts = collections.Counter(o["url"].split("/")[2] for o in out)
print(hosts)

def fnv(s):
    h = 0x811c9dc5
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xffffffff
    return h

def b36(n):
    s = "0123456789abcdefghijklmnopqrstuvwxyz"
    o = ""
    while True:
        n, r = divmod(n, 36); o = s[r] + o
        if not n: return o

hs = sorted({b36(fnv(o["key"]) % (36 ** 4)) for o in out})
json.dump(out, open("dashboard/thumb_select.json", "w"), ensure_ascii=False)
open("dashboard/thumb_hashes.txt", "w").write(" ".join(hs))
print(len(hs), sum(len(h) + 1 for h in hs))
