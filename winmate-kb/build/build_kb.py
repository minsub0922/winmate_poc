#!/usr/bin/env python3
"""Winmate KB 빌드: raw/ 덤프 + seed/ 시드 → kb/winmate_kb.sqlite

입력(raw/)
  wkb_products.json     상품 목록 API(cxhr/pf/goodsList) 덤프: 카테고리, 상품 카드, 옵션(변형), 목록 필터 소속
  wkb_filter_meta.json  목록 페이지 필터 패널의 공식 그룹명·라벨, 탭, 목록별 소속 상품
  wkb_specs.json        스펙 API(xhr/goods/getGoodsSpecList) 덤프: goodsId → [[그룹, 항목, 값], ...]
  wkb_features.json     PDP HTML 파싱 덤프: goodsId → {title, desc, ctg1, ctg2, feats:[{h,text,imgs}]}
  wkb_pages*.json       업종·솔루션·서비스·랜딩·도입사례·US 페이지 선형화 덤프: path → {kind, blocks:[...]}
  prior_case_studies.json  이전 세션에서 도입사례 본문을 LLM으로 구조화한 결과(T5)

원칙: 사실(이름·수치·문구)은 원문에서만. 모든 사실 행은 source_occurrence_id·source_tier·method 를 가진다.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(os.environ.get("WKB_RAW", ROOT / "raw"))
SEED = ROOT / "seed"
KB_DIR = Path(os.environ.get("WKB_KB", ROOT / "kb"))
DB_PATH = KB_DIR / "winmate_kb.sqlite"
SITE = "https://www.samsung.com"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import curation as C  # noqa: E402


def hid(*parts) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:16]


def norm(s: str | None) -> str:
    if not s:
        return ""
    s = s.replace(" ", " ").replace("™", "").replace("®", "")
    return re.sub(r"[\s·∙\-_/()\[\]]+", "", s).lower()


def load_json(name: str, default=None):
    p = RAW / name
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def to_path(u: str | None) -> str | None:
    if not u:
        return None
    m = re.match(r"(?:https?://(?:www\.)?samsung\.com)?(/[^?#]*)", u.strip())
    if not m:
        return None
    p = re.sub(r"/{2,}", "/", m.group(1))
    return p if p.endswith("/") else p + "/"


def load_pages() -> dict:
    pages: dict = {}
    for p in sorted(RAW.glob("wkb_pages*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        items = d.get("items", d)
        pages.update(items)   # 나중 파일이 앞 파일을 덮는다(v2 가 v1 을 대체)
    return pages


def media_type(u: str) -> str:
    m = re.search(r"\.(jpe?g|png|gif|webp|svg|mp4|webm)(?:$|\?)", u.lower())
    if not m:
        return "image"
    return {"mp4": "video", "webm": "video", "svg": "vector", "gif": "animation"}.get(m.group(1), "image")


# ── 스펙 정규화 규칙 ───────────────────────────────────────
NUM = r"-?\d+(?:[.,]\d+)?"


def nums(s: str) -> list[float]:
    out = []
    for x in re.findall(NUM, s or ""):
        try:
            out.append(float(x.replace(",", "")))
        except ValueError:
            pass
    return out


SPEC_RULES: list[tuple[str, re.Pattern, str | None]] = [
    ("screen_size_cm", re.compile(r"(대각선\s*사이즈|화면\s*크기|화면크기|디스플레이\s*크기|스크린\s*사이즈)"), "cm"),
    ("brightness_nit", re.compile(r"^밝기"), "nit"),
    ("resolution", re.compile(r"^해상도"), None),
    ("pixel_pitch_mm", re.compile(r"픽셀\s*피치"), "mm"),
    ("operation_hours", re.compile(r"^(제품\s*)?(사용|작동|운영|동작)\s*시간$|Operation\s*Hour", re.I), None),
    ("operating_temp_c", re.compile(r"(동작|사용|작동)\s*온도(?!\s*범위\s*\()"), "°C"),
    ("touch", re.compile(r"^터치"), None),
    ("cooling_capacity_kw", re.compile(r"냉방\s*(능력|성능)|정격\s*냉방"), "kW"),
    ("heating_capacity_kw", re.compile(r"난방\s*(능력|성능)|정격\s*난방"), "kW"),
    ("power_consumption", re.compile(r"소비\s*전력"), None),
    ("energy_grade", re.compile(r"에너지\s*소비\s*효율\s*등급|효율\s*등급"), None),
    ("capacity_l", re.compile(r"(전체|총)\s*용량"), "L"),
    ("dimensions", re.compile(r"(크기|치수|사이즈)\s*\(?.*(가로|W).*\)?"), "mm"),
    ("weight_kg", re.compile(r"(무게|제품\s*중량|^중량)"), "kg"),
    ("release_ym", re.compile(r"출시\s*년월"), None),
    ("panel_type", re.compile(r"패널\s*타입"), None),
    ("refrigerant", re.compile(r"냉매(\s*종류)?$"), None),
    ("smartthings", re.compile(r"SmartThings", re.I), None),
    ("wifi", re.compile(r"^(WiFi|Wi-Fi|무선\s*랜)", re.I), None),
    ("os", re.compile(r"^(OS|운영체제)$", re.I), None),
    ("cpu", re.compile(r"^(프로세서|CPU|칩셋)"), None),
    ("ip_rating_field", re.compile(r"(방수|방진|IP\s*등급)"), None),
]
IP_RE = re.compile(r"\bIP\s?([0-6X][0-9X])\b", re.I)


def normalize_spec(group: str, attr: str, value: str):
    """(norm_key, num, num2, unit) — 매칭 없으면 (None, ...)."""
    g = group or ""
    a = attr or ""
    v = (value or "").strip()
    ns = nums(v)
    # 그룹이 의미를 주는 경우
    if re.search(r"동작\s*조건", g) and re.match(r"^(동작\s*)?온도", a):
        return "operating_temp_c", (ns[0] if ns else None), (ns[1] if len(ns) > 1 else None), "°C"
    if re.search(r"사용\s*온도\s*범위", g + " " + a):
        mode = "cool" if "냉방" in (g + a) else "heat" if "난방" in (g + a) else None
        if mode:
            return f"outdoor_temp_{mode}_c", (ns[0] if ns else None), (ns[1] if len(ns) > 1 else None), "°C"
    for key, pat, unit in SPEC_RULES:
        if not pat.search(a):
            continue
        if key == "dimensions" and not re.search(r"[x×X*]", v):
            continue
        if key == "resolution":
            vv = re.sub(r"(?<=\d),(?=\d{3})", "", v)
            m = re.search(r"(\d{3,5})\s*[x×X*]\s*(\d{3,5})", vv)
            return key, (float(m.group(1)) if m else None), (float(m.group(2)) if m else None), ("dpi" if re.search(r"\bdpi?\b", vv.lower()) else "px")
        if key in ("cooling_capacity_kw", "heating_capacity_kw"):
            if "kcal" in a.lower() or "kcal" in v.lower():
                return None, None, None, None
            if re.search(r"전류|소비\s*전력|전력|COP|EER|효율|풍량", a) or re.search(r"전력|전기", g) \
                    or re.search(r"\d\s*(A|W|Btu|RT)\b", v):
                return None, None, None, None
            if "최소/정격/최대" not in a and re.search(r"최소|최대", a):
                key = key.replace("_kw", "_min_kw" if "최소" in a else "_max_kw")
            if "최소/정격/최대" in a and len(ns) >= 3:
                return key, ns[1], ns[2], "kW"
            return key, (ns[0] if ns else None), (ns[-1] if len(ns) > 1 else None), "kW"
        if key == "operating_temp_c":
            return key, (ns[0] if ns else None), (ns[1] if len(ns) > 1 else None), "°C"
        if key == "brightness_nit":
            if not re.search(r"nit|cd", v + a, re.I):
                return None, None, None, None
            return key, (max(ns) if ns else None), None, "nit"
        if key == "screen_size_cm":
            if "inch" in a.lower() or "인치" in a or '"' in v:
                return "screen_size_inch", (ns[0] if ns else None), None, "inch"
            return key, (ns[0] if ns else None), None, "cm"
        if key == "operation_hours":
            m = re.search(r"(\d{1,2})\s*/\s*7", v)
            return key, (float(m.group(1)) if m else None), None, "h/7d"
        if key == "release_ym":
            m = re.search(r"(20\d{2})\D{0,3}(\d{1,2})?", v)
            return key, (float(m.group(1)) if m else None), (float(m.group(2)) if m and m.group(2) else None), None
        if key == "dimensions":
            return key, (ns[0] if ns else None), (ns[1] if len(ns) > 1 else None), "mm"
        if key in ("refrigerant", "wifi", "cpu", "os", "smartthings", "touch", "panel_type"):
            return key, None, None, None                  # 문자 속성: 숫자를 뽑지 않는다(R-410A → -410 같은 오해 방지)
        if key == "pixel_pitch_mm":
            n = ns[0] if ns else None
            if n is not None and ("㎛" in v or "µm" in v or "um" in v.lower() or n > 5):
                n = n / 1000                               # ㎛ 표기(또는 5 초과 = ㎛로 판단)
            return key, n, None, "mm"
        if "최소/정격/최대" in a and len(ns) >= 3:      # 정격값을 대표값으로, 최대를 보조값으로
            n1, n2 = ns[1], ns[2]
        else:
            n1, n2 = (ns[0] if ns else None), (ns[1] if len(ns) > 1 else None)
        if key == "weight_kg":
            if re.search(r"\d\s*g\b", v) and not re.search(r"kg", v, re.I):
                n1 = n1 / 1000 if n1 is not None else None
                n2 = n2 / 1000 if n2 is not None else None
            return key, n1, n2, "kg"
        if key == "power_consumption":
            u = "kW" if re.search(r"kW", v) else ("W" if re.search(r"\bW\b|W$", v) else None)
            return key, n1, n2, u
        return key, n1, n2, unit
    return None, None, None, None


CLAIM_RE = re.compile(r"\d|최고|최초|1위|No\.?\s?1|유일|최대|최소|세계", re.I)


# ── DB 헬퍼 ─────────────────────────────────────────────
class DB:
    def __init__(self, path: Path):
        if path.exists():
            path.unlink()
        self.c = sqlite3.connect(path)
        self.c.executescript((Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))
        self.c.execute("PRAGMA foreign_keys = OFF")
        self.buf: dict[str, list] = collections.defaultdict(list)
        self.cols: dict[str, list[str]] = {}

    def add(self, table: str, **row):
        cols = self.cols.get(table)
        if cols is None:
            cols = [r[1] for r in self.c.execute(f"PRAGMA table_info({table})")]
            self.cols[table] = cols
            unknown = set(row) - set(cols)
            if unknown:
                raise KeyError(f"{table}: unknown columns {unknown}")
        self.buf[table].append(tuple(
            json.dumps(row.get(k), ensure_ascii=False) if isinstance(row.get(k), (list, dict)) else row.get(k)
            for k in cols))
        if len(self.buf[table]) >= 5000:
            self.flush(table)

    def flush(self, table: str | None = None):
        for t in ([table] if table else list(self.buf)):
            rows = self.buf.pop(t, [])
            if rows:
                ph = ",".join("?" * len(self.cols[t]))
                self.c.executemany(f"INSERT OR IGNORE INTO {t} VALUES ({ph})", rows)
        self.c.commit()

    def q(self, sql: str, args=()):
        self.flush()
        return self.c.execute(sql, args).fetchall()


# ── 빌드 ────────────────────────────────────────────────
class Builder:
    def __init__(self):
        KB_DIR.mkdir(parents=True, exist_ok=True)
        self.db = DB(DB_PATH)
        self.stats = collections.Counter()
        self.notes: list[str] = []
        self.doc_page_type: dict[str, str] = {}
        self.block_index: dict[str, dict] = {}
        self.alias_rows: list[tuple] = []
        self.images: dict[str, dict] = {}         # canonical key → asset
        self.img_occ: list[dict] = []
        self.occ_by_asset_doc: dict[tuple, dict] = {}
        self.occ_by_doc: dict[str, list] = collections.defaultdict(list)
        self.family_by_goods: dict[str, str] = {}
        self.family_by_url: dict[str, str] = {}
        self.family_name: dict[str, str] = {}
        self.model_by_code: dict[str, str] = {}
        self.cat_by_listpath: dict[str, str] = {}
        self.cat_by_root: dict[str, str] = {}
        self.cat_by_no: dict[str, str] = {}
        self.categories: dict[str, dict] = {}
        self.cat_filters: dict[str, set] = collections.defaultdict(set)
        self.solution_by_url: dict[str, str] = {}
        self.solution_site_code: dict[str, str] = {}
        self.vertical_by_slug: dict[str, str] = {}
        self.case_by_path: dict[str, str] = {}
        self.vp_seen: set = set()
        self.spec_attrs: dict = {}
        self.page_items: dict = {}

    # ── 0. 소스·시드 ──
    def sources(self):
        db = self.db
        db.add("source", id="src_site_kr", kind="web_site", name="삼성전자 비즈니스 (KR)", location=SITE + "/sec/business/",
               notes="내장 브라우저에서 페이지 HTML·상품 API를 받아 결정적 파서로 구조화")
        db.add("source", id="src_site_us", kind="web_site", name="Samsung Business (US)", location=SITE + "/us/business/",
               notes="업종(버티컬)·디스플레이·솔루션 페이지 일부")
        db.add("source", id="src_prior_cases", kind="prior_extraction", name="도입사례 구조화 결과(이전 세션)",
               location="raw/prior_case_studies.json",
               notes="KR 고객도입사례 218건을 LLM으로 구조화한 결과. 사람 검토 전(T5)")

    def seeds(self):
        db = self.db
        ont = SEED / "ontology"
        v = yaml.safe_load((ont / "verticals.yaml").read_text(encoding="utf-8"))
        for top in v["kr_verticals"]:
            db.add("vertical", id=top["code"], code=top["code"], name_ko=top["name_ko"], scheme="kr_site",
                   url=top.get("url"), status="active")
            for ch in top.get("children", []):
                db.add("vertical", id=ch["code"], code=ch["code"], name_ko=ch["name_ko"], parent_id=top["code"],
                       scheme="kr_site", url=ch.get("url"), status="active")
        for u in v["us_verticals"]:
            db.add("vertical", id=u["code"], code=u["code"], name_en=u["name_en"], scheme="us_site", status="active")
        for s in v["winmate_segments"]:
            db.add("vertical", id=s["code"], code=s["code"], name_ko=s["name_ko"], scheme="winmate16", status=s.get("status"))
            db.add("segment_mapping", winmate_segment=s["code"], name_ko=s["name_ko"],
                   kr_vertical_codes=json.dumps(s.get("kr"), ensure_ascii=False),
                   us_vertical_codes=json.dumps(s.get("us"), ensure_ascii=False),
                   catalog_chapter=s.get("catalog_chapter"), status=s.get("status"))
        for top in v["kr_verticals"]:
            for node in [top] + top.get("children", []):
                u = node.get("url")
                if u:
                    self.vertical_by_slug[u.rstrip("/").split("/")[-1]] = node["code"]
                self.alias_rows.append((node["name_ko"], "vertical", node["code"], "seed_name", "seed"))
        for slug, code in C.US_VERTICAL_SLUGS.items():
            self.vertical_by_slug["us:" + slug] = code

        st = yaml.safe_load((ont / "space_types.yaml").read_text(encoding="utf-8"))
        for s in st["space_types"]:
            db.add("space_type", id=s["code"], code=s["code"], name_ko=s["name_ko"],
                   default_attrs_json=s.get("default_attrs"), origin="seed", status="draft")
        for code, name in C.EXTRA_SPACE_TYPES:
            db.add("space_type", id=code, code=code, name_ko=name, origin="kb_build_curated", status="draft")
        self.space_codes = {s["code"] for s in st["space_types"]} | {c for c, _ in C.EXTRA_SPACE_TYPES}

        ss = yaml.safe_load((ont / "solutions_services.yaml").read_text(encoding="utf-8"))
        for s in ss["solutions"]:
            url = s.get("url") if str(s.get("url", "")).startswith("http") else None
            sid = "sol_" + s["code"]
            db.add("solution", id=sid, code=s["code"], name_ko=s["name_ko"], aliases_json=s.get("aliases", []),
                   kind=s.get("kind"), site_code=s.get("site_code"), url=url, origin="seed")
            if url:
                self.solution_by_url[to_path(url)] = sid
            if s.get("site_code"):
                self.solution_site_code[s["site_code"]] = sid
                self.alias_rows.append((s["site_code"], "solution", sid, "site_code", "seed"))
            for a in [s["name_ko"]] + s.get("aliases", []):
                self.alias_rows.append((a, "solution", sid, "seed_name", "seed"))
        for s in ss["services"]:
            url = s.get("url") if str(s.get("url", "")).startswith("http") else None
            sid = "svc_" + s["code"]
            db.add("service_product", id=sid, code=s["code"], name_ko=s["name_ko"], aliases_json=s.get("aliases", []),
                   target_category=s.get("target_category"), url=url)
            if url:
                self.solution_by_url[to_path(url)] = sid
            for a in [s["name_ko"]] + s.get("aliases", []):
                self.alias_rows.append((a, "service", sid, "seed_name", "seed"))

        cr = yaml.safe_load((ont / "capability_rules.yaml").read_text(encoding="utf-8"))
        for c in cr["capabilities"]:
            db.add("capability", id="cap_" + c["code"], code=c["code"], name_ko=c["name_ko"], description=c.get("desc_ko"))
        for r in cr["rules"]:
            db.add("capability_rule", id=r["id"], capability_id="cap_" + r["capability"], category=r["category"],
                   expression=r["expression"], params_json=r.get("params"), explanation_ko=r.get("explanation_ko"),
                   status=r.get("status", "draft"), origin="seed")
        for r in C.AUTO_RULES:
            db.add("capability_rule", id=r["id"], capability_id="cap_" + r["cap"], category=r["category"],
                   expression=r["expression"], explanation_ko=r["explain"], status="draft_auto", origin="kb_build_v1")
        for q in cr["requires"]:
            db.add("requires", space_type_id=q["space"], capability_id="cap_" + q["capability"],
                   strength=q["strength"], status="draft", origin="seed")
        pr = yaml.safe_load((ont / "placement_rules.yaml").read_text(encoding="utf-8"))
        for r in pr["placement_rules"]:
            db.add("placement_rule", id=r["id"], kind=r["kind"], space=r["space"], category=r["category"],
                   expression=r["expression"], params_json=r.get("params"), status=r.get("status"))
        sr = yaml.safe_load((SEED / "sheet_roles.yaml").read_text(encoding="utf-8"))
        for r in sr["sheet_roles"]:
            db.add("sheet_role", code=r["code"], name_ko=r["name_ko"], says_ko=r["says_ko"], section=r["section"])
        # 도입사례 id 미리 계산(업종 페이지 '고객 도입사례' 링크 해소용)
        d = load_json("prior_case_studies.json") or {"cases": []}
        for c in d["cases"]:
            p = to_path(c.get("url"))
            if p:
                self.case_by_path[p] = "dep_" + str(c["id"])
        db.flush()

    # ── 공통: 문서·블록·이미지 ──
    def add_doc(self, doc_id, kind, page_type, url, title=None, desc=None, og=None, locale="ko-KR",
                fetched=None, published=None, meta=None, source_id="src_site_kr"):
        self.db.add("source_document", id=doc_id, source_id=source_id, kind=kind, page_type=page_type, url=url,
                    title=title, description=desc, og_image=og, locale=locale, fetched_at=fetched,
                    published_at=published, content_hash=None, status="ok", meta_json=meta)
        self.doc_page_type[doc_id] = page_type
        self.stats["documents"] += 1

    def add_block(self, doc_id, seq, btype, *, level=None, text=None, href=None, img=None, alt=None, section=None, dup=0):
        bid = f"{doc_id}:{seq}"
        if alt:
            alt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", alt)).strip() or None
        self.db.add("document_block", id=bid, document_id=doc_id, seq=seq, block_type=btype, level=level,
                    text=text, href=href, img_src=img, img_alt=alt, section_path=section, is_duplicate=dup)
        self.db.add("occurrence", id="occ_" + bid, document_id=doc_id, block_id=bid,
                    kind="image" if btype == "img" else "text", locator_json=None)
        if not dup:
            self.block_index[bid] = {"doc": doc_id, "t": btype, "text": text, "alt": alt, "section": section}
        self.stats["blocks"] += 1
        return bid

    def add_image(self, url, *, doc_id, block_id, page_type, alt=None, caption=None, section=None,
                  grade_hint=None, reason=None, rights="official", space=None, vertical=None, entities=None, mobile_url=None):
        base = C.img_base(url)
        if not base or base.startswith("data:") or re.search(r"img_baseimg_null|blank\.gif|spacer\.gif", base):
            return None
        key = C.img_key(url)
        mobile = C.is_mobile_img(url)
        a = self.images.get(key)
        if a is None:
            a = {"id": "img_" + hid(key), "url": None, "url_mobile": None, "media_type": media_type(base),
                 "grade_hint": grade_hint, "reason": reason, "rights": rights, "n": 0}
            self.images[key] = a
        if mobile:
            a["url_mobile"] = a["url_mobile"] or base
        else:
            a["url"] = a["url"] or base
        if mobile_url and not a["url_mobile"]:
            a["url_mobile"] = C.img_base(mobile_url)
        if grade_hint and (a["grade_hint"] is None or C.GRADE_PRIORITY.get(grade_hint, 9) < C.GRADE_PRIORITY.get(a["grade_hint"], 9)):
            a["grade_hint"], a["reason"] = grade_hint, reason
        if rights == "customer_case":
            a["rights"] = rights
        k = (a["id"], doc_id)
        if k in self.occ_by_asset_doc:          # 같은 문서 안의 PC/MO·중복 섹션 재등장
            o = self.occ_by_asset_doc[k]
            o["alt"] = o["alt"] or alt
            o["caption"] = o["caption"] or caption
            return a["id"]
        a["n"] += 1
        if alt:
            alt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", alt)).strip() or None
        o = {"id": "io_" + hid(a["id"], doc_id), "asset_id": a["id"], "document_id": doc_id,
             "block_id": block_id, "page_type": page_type, "alt": alt, "caption": caption,
             "section_path": section, "context_space_type_id": space, "context_vertical_id": vertical,
             "context_entities_json": entities}
        self.img_occ.append(o)
        self.occ_by_asset_doc[k] = o
        self.occ_by_doc[doc_id].append(o)
        return a["id"]

    def add_vp(self, level, text, about_kind, about_id, occ, tier, method, *, parent=None, vertical=None, space=None,
               locale="ko-KR"):
        text = (text or "").strip()
        if not text or len(text) < 3:
            return None
        k = (about_kind, about_id, level, norm(text))
        if k in self.vp_seen:
            return None
        self.vp_seen.add(k)
        vid = "vp_" + hid(about_kind, about_id, level, text)
        self.db.add("value_prop", id=vid, level=level, text=text, parent_id=parent, about_kind=about_kind, about_id=about_id,
                    vertical_id=vertical, space_type_id=space, locale=locale, claim_flag=int(bool(CLAIM_RE.search(text))),
                    source_occurrence_id=occ, source_tier=tier, method=method)
        self.stats["value_props"] += 1
        return vid

    def add_category(self, cid, code, name, level, parent=None, **kw):
        if cid in self.categories:
            return
        self.categories[cid] = {"name": name, "parent": parent, "level": level}
        self.db.add("category", id=cid, code=code, parent_id=parent, name_ko=name, level=level, **kw)

    # ── 1. 상품 ──
    def products(self):
        P = load_json("wkb_products.json")
        if not P:
            self.notes.append("wkb_products.json 없음 — 상품 단계 건너뜀")
            return
        FM = load_json("wkb_filter_meta.json", {}) or {}
        fmeta = FM.get("meta", {})
        members = FM.get("members", {})
        specs = load_json("wkb_specs.json", None)
        if specs is None:
            specs = P.get("specs", {}) or {}
        feats = load_json("wkb_features.json", None)
        if feats is None:
            feats = P.get("features", {}) or {}
        db = self.db
        fetched = P.get("fetchedAt") or P.get("startedAt")
        for top, name in C.CATEGORY_TOP.items():
            self.add_category(top, top, name, 1, origin="kb_build_curated")
        for c in P["cats"]:
            if not c.get("no"):
                continue
            root = c["p"].split("/")[0]
            cid = "cat_" + root
            self.add_category(cid, root, c.get("title") or root, 2, C.CATEGORY_PARENT.get(root),
                              list_url=f"{SITE}/sec/business/{c['p']}/", site_disp_clsf_no=str(c["no"]),
                              site_filters_json=c.get("allFilters"), origin="site_list")
            self.cat_by_listpath[c["p"]] = cid
            self.cat_by_root[root] = cid
            self.cat_by_no[str(c["no"])] = cid
            self.cat_filters[cid] |= set(c.get("allFilters") or [])
            self.alias_rows.append((c.get("title") or root, "category", cid, "site_list_title", "site"))
        # 상품의 대표 목록: 사이트 목록 순서상 처음 소속된 목록
        primary: dict[str, str] = {}
        for c in P["cats"]:
            for g in members.get(str(c.get("no")), []):
                primary.setdefault(g, self.cat_by_no.get(str(c["no"])))
        subcats: dict[tuple, str] = {}
        order = list(dict.fromkeys(P["cardOrder"]))
        for gid in order:
            p = P["products"][gid]
            if gid in self.family_by_goods:
                continue
            cid = primary.get(gid) or self.cat_by_listpath.get(p["catPath"])
            fid = "fam_" + gid
            self.family_by_goods[gid] = fid
            sub = p.get("dlgtDispClsfEnNm")
            if sub:
                subcats.setdefault((cid, sub), None)
            comp = p.get("compDispClsfEnNm")
            url = f"{SITE}/sec/business/{p['goodsDetailUrl']}" if p.get("goodsDetailUrl") else None
            if url:
                self.family_by_url[to_path(url)] = fid
            f = feats.get(gid) or {}
            doc_id = "doc_pdp_" + gid
            reg = p.get("sysRegDtm")
            self.add_doc(doc_id, "pdp_page", "pdp", url, title=f.get("title"), desc=f.get("desc"), og=f.get("ogImage"),
                         fetched=fetched, meta={"goodsId": gid, "category_list": p["catPath"]})
            seq = 1
            card_bid = self.add_block(doc_id, seq, "p", text=f"{p.get('goodsNm')} ({p.get('mdlCode')})", section="상품 카드")
            db.add("product_family", id=fid, goods_id=gid, category_id=cid, subcategory_slug=sub, name_ko=p.get("goodsNm"),
                   default_model_code=p.get("mdlCode"), marketing_model=p.get("mdlNm"), grp_path=p.get("grpPath"),
                   detail_url=url, usp_json=p.get("uspDescList"), sale_status_code=p.get("saleStatCd"),
                   registered_at=(str(reg) if reg else None), goods_type_code=p.get("goodsTpCd"),
                   pdp_title=f.get("title"), pdp_description=f.get("desc"), ctg1=f.get("ctg1"), ctg2=f.get("ctg2"),
                   source_occurrence_id="occ_" + card_bid, source_tier="T2_official")
            self.family_name[fid] = p.get("goodsNm") or ""
            self.stats["families"] += 1
            # 복수 목록 소속 + 비교 분류(comp)
            for cno, gids in members.items():
                if gid in gids and self.cat_by_no.get(str(cno)):
                    db.add("family_category", family_id=fid, category_id=self.cat_by_no[str(cno)], role="list")
            if comp and comp != (p["catPath"] or "").split("/")[0]:
                ccid = self.cat_by_root.get(comp) or "cat_" + comp
                if ccid not in self.categories:
                    self.add_category(ccid, comp, C.SUBCAT_LABEL.get(comp, comp), 2, C.CATEGORY_PARENT.get(comp),
                                      list_url=f"{SITE}/sec/business/{comp}/all-{comp}/",
                                      site_disp_clsf_no=str(p.get("compDispClsfNo") or ""), origin="site_api_comp")
                    self.cat_by_listpath[f"{comp}/all-{comp}"] = ccid
                    self.cat_by_root[comp] = ccid
                db.add("family_category", family_id=fid, category_id=ccid, role="comp")
            for a, kind in ((p.get("goodsNm"), "site_name"), (p.get("mdlNm"), "marketing_model"), (p.get("grpPath"), "grp_path")):
                if a:
                    self.alias_rows.append((a, "family", fid, kind, "site"))
            for i, u in enumerate(p.get("uspDescList") or []):
                seq += 1
                bid = self.add_block(doc_id, seq, "usp", text=u, section="USP")
                self.add_vp("usp", u, "family", fid, "occ_" + bid, "T2_official", "site_api_verbatim")
            for im in p.get("images") or []:
                seq += 1
                bid = self.add_block(doc_id, seq, "img", img=C.img_base(im["src"]), alt=im.get("alt"), section="갤러리")
                aid = self.add_image(im["src"], doc_id=doc_id, block_id=bid, page_type="pdp_gallery", alt=im.get("alt"),
                                     section="갤러리", grade_hint="C", reason="상품 갤러리(단독컷)", entities=[["family", fid]])
                if aid:
                    db.add("depicts", asset_id=aid, target_kind="family", target_id=fid, level_label="confirmed",
                           evidence="pdp_gallery", confidence=0.98)
            seq = self.pdp_features(fid, doc_id, f, seq)
            # 모델(옵션)
            models = {p.get("mdlCode"): {"goodsId": gid, "optName": None, "optValue": None, "default": 1}}
            for vg, vv in (P.get("variants") or {}).items():
                if vv.get("parentGoodsId") == gid and vv.get("mdlCode"):
                    if vv["mdlCode"] == p.get("mdlCode"):
                        models[vv["mdlCode"]].update(optName=vv.get("optName"), optValue=vv.get("optValue"), soldOut=vv.get("soldOut"))
                    else:
                        models.setdefault(vv["mdlCode"], {"goodsId": vg, "optName": vv.get("optName"),
                                                          "optValue": vv.get("optValue"), "default": 0, "soldOut": vv.get("soldOut")})
            for code, m in models.items():
                if not code or code in self.model_by_code:
                    continue
                mid = "mdl_" + code
                self.model_by_code[code] = mid
                db.add("product_model", id=mid, model_code=code, goods_id=m["goodsId"], family_id=fid,
                       option_name=m.get("optName"), option_value=(m.get("optValue") or "").replace("‎", "") or None,
                       is_family_default=m["default"], sold_out_flag=m.get("soldOut"),
                       source_occurrence_id="occ_" + card_bid, source_tier="T2_official")
                self.alias_rows.append((code, "model", mid, "model_code", "site"))
                self.stats["models"] += 1
                rows = specs.get(m["goodsId"]) or []
                if not rows:
                    continue
                sdoc = "doc_spec_" + m["goodsId"]
                self.add_doc(sdoc, "spec_api", "spec", (url or "") + "#spec", title=f"{p.get('goodsNm')} 스펙 ({code})",
                             fetched=fetched, meta={"goodsId": m["goodsId"], "model_code": code})
                root = (p["catPath"] or "").split("/")[0]
                for k, (g, a, v) in enumerate(rows):
                    bid = self.add_block(sdoc, k + 1, "spec", text=f"{g} > {a}: {v}", section=g)
                    key, n1, n2, unit = normalize_spec(g or "", a or "", v or "")
                    attr_id = "attr_" + hid(root, g, a)
                    self.spec_attrs[attr_id] = (root, g, a, key, unit)
                    db.add("spec_value", id="sv_" + hid(mid, g, a, k), model_id=mid, family_id=fid, attr_id=attr_id,
                           group_name=g, attr_name=a, value_raw=v, norm_key=key, value_num=n1, value_num2=n2,
                           value_unit=unit, source_occurrence_id="occ_" + bid, source_tier="T2_official",
                           method="spec_api_parse")
                    self.stats["spec_values"] += 1
                    if v:
                        for ip in IP_RE.findall(v):
                            db.add("spec_value", id="sv_" + hid(mid, g, a, k, "ip"), model_id=mid, family_id=fid,
                                   attr_id=attr_id, group_name=g, attr_name=a, value_raw=v, norm_key="ip_rating",
                                   value_num=None, value_num2=None, value_unit="IP" + ip.upper().replace(" ", ""),
                                   source_occurrence_id="occ_" + bid, source_tier="T2_official", method="spec_api_regex")
        # 하위 분류(사이트 dlgtDispClsfEnNm). 이름은 필터 패널 공식 라벨 > 큐레이션 라벨 > slug
        sub_names = {}
        for (cid, sub) in sorted(subcats, key=lambda x: (str(x[0]), str(x[1]))):
            if not cid:
                continue
            cno = next((n for n, c in self.cat_by_no.items() if c == cid), None)
            lab = ((fmeta.get(cno) or {}).get(sub) or {}).get("label") if cno else None
            name = lab or C.SUBCAT_LABEL.get(sub, sub)
            sub_names[f"{cid}__{sub}"] = (cid, name)
            self.add_category(f"{cid}__{sub}", f"{cid}__{sub}", name, 3, cid, origin="site_filter_label" if lab else "site_api")
        dup = collections.Counter(norm(n) for _, n in sub_names.values())
        for sid, (cid, name) in sub_names.items():
            parent = self.categories.get(cid, {}).get("name") or ""
            self.alias_rows.append((f"{parent} {name}", "category", sid, "subcat_label_qualified", "site"))
            if dup[norm(name)] == 1 and len(norm(name)) >= 3:   # '실내기'·'기타'처럼 여러 목록에 같은 라벨이면 단독 별칭을 만들지 않는다
                self.alias_rows.append((name, "category", sid, "subcat_label", "site"))
        # 목록 필터 → product_tag (공식 그룹·라벨 포함)
        for cno, fmap in (P.get("filters") or {}).items():
            cid = self.cat_by_no.get(str(cno))
            meta = fmeta.get(str(cno), {})
            listed = set(members.get(str(cno), []))
            for flt, gids in fmap.items():
                fm = meta.get(flt) or {}
                if not fm and listed and len(listed) > 2 and set(gids) >= listed:
                    # 필터 패널에 없는 값이고 목록 전체가 그대로 돌아왔다 = 사이트가 무시한 필터(예: 'flip', 'built-in-wifi')
                    self.notes.append(f"무효 필터 제외: {cid} '{flt}' ({len(gids)}개 = 목록 전체)")
                    continue
                kind, val = C.classify_filter(flt, fm.get("group"))
                for g in gids:
                    fid = self.family_by_goods.get(g)
                    if fid:
                        db.add("product_tag", family_id=fid, tag_kind=kind, tag_value=fm.get("label") or val, site_filter=flt,
                               category_id=cid, site_group=fm.get("group"), site_label=fm.get("label"),
                               source_tier="T2_official", method="site_list_filter")
                        self.stats["product_tags"] += 1
        # 솔루션 ↔ 상품 카드(솔루션도 사이트에서 상품 코드로 판매)
        for code, sid in self.solution_site_code.items():
            mid = self.model_by_code.get(code)
            if mid:
                fid = db.q("SELECT family_id FROM product_model WHERE id=?", (mid,))[0][0]
                db.add("kg_edge", src_kind="solution", src_id=sid, rel="SOLD_AS", dst_kind="family", dst_id=fid,
                       source_tier="T2_official", method="site_code_match", confidence=1.0, evidence=code)
        db.flush()

    def pdp_features(self, fid, doc_id, f, seq):
        """PDP 특장점 컴포넌트(v2 파서: type, h, sub, desc, disc, imgs[{src, mo_src, alt}], items[]) 또는 v1(h, text, imgs)."""
        db = self.db
        k = 0
        for i, ft in enumerate(f.get("feats") or []):
            head = (ft.get("h") or ft.get("sub") or "").strip() or None
            body = (ft.get("desc") or "").strip()
            if not body:
                body = (ft.get("text") or "").strip()
                if head and body.startswith(head):
                    body = body[len(head):].strip()
            disc = (ft.get("disc") or "").strip() or None
            if body and disc and body.endswith(disc):
                body = body[: -len(disc)].strip()
            if not head and not body and not ft.get("imgs"):
                continue
            seq += 1
            sec = f"특장점 > {head or (ft.get('type') or '') + ' ' + str(i + 1)}"
            bid = self.add_block(doc_id, seq, "feature", level=2, text=(head or "") + ("\n" + body if body else ""), section=sec)
            db.add("feature_block", id="ft_" + hid(fid, i), family_id=fid, seq=k, parent_seq=None, component_type=ft.get("type"),
                   headline=head, sub=ft.get("sub"), body=body[:1500] or None, disclaimer=disc, n_images=len(ft.get("imgs") or []),
                   source_occurrence_id="occ_" + bid, source_tier="T2_official")
            parent = k
            k += 1
            vid = None
            if head and 4 <= len(head) <= 120:
                vid = self.add_vp("key_message", head, "family", fid, "occ_" + bid, "T2_official", "pdp_html_verbatim")
            if vid and body and 10 <= len(body) <= 400:
                self.add_vp("proof_point", body, "family", fid, "occ_" + bid, "T2_official", "pdp_html_verbatim", parent=vid)
            seq = self._pdp_images(fid, doc_id, ft.get("imgs") or [], sec, seq)
            for j, it in enumerate(ft.get("items") or []):
                if not (it.get("h") or it.get("desc") or it.get("imgs")):
                    continue
                seq += 1
                isec = f"{sec} > {it.get('h') or j + 1}"
                ib = self.add_block(doc_id, seq, "feature", level=3, text=(it.get("h") or "") + ("\n" + it["desc"] if it.get("desc") else ""), section=isec)
                db.add("feature_block", id="ft_" + hid(fid, i, j), family_id=fid, seq=k, parent_seq=parent, component_type="item",
                       headline=it.get("h"), sub=None, body=(it.get("desc") or None), disclaimer=None, n_images=len(it.get("imgs") or []),
                       source_occurrence_id="occ_" + ib, source_tier="T2_official")
                k += 1
                if it.get("h") and 4 <= len(it["h"]) <= 120:
                    self.add_vp("key_message", it["h"], "family", fid, "occ_" + ib, "T2_official", "pdp_html_verbatim")
                seq = self._pdp_images(fid, doc_id, [x for x in (it.get("imgs") or []) if x.get("src")], isec, seq)
        return seq

    def _pdp_images(self, fid, doc_id, imgs, sec, seq):
        db = self.db
        for im in imgs:
            src = im.get("src")
            if not src:
                continue
            seq += 1
            alt = im.get("alt")
            ib = self.add_block(doc_id, seq, "img", img=C.img_base(src), alt=alt, section=sec)
            g0 = C.grade_hint_for("pdp", {"src": src}, None)[0]
            ga, ra, sp = C.grade_from_alt(alt)
            if g0 == "E":
                hint, reason = "E", "파일명이 아이콘·로고 패턴"
            elif ga:
                hint, reason = ga, ra
            else:
                hint, reason = "A?C", "PDP 특장점 이미지(공간 연출 또는 기능 컷)"
            aid = self.add_image(src, doc_id=doc_id, block_id=ib, page_type="pdp_feature", alt=alt, section=sec,
                                 grade_hint=hint, reason=reason, space=sp, entities=[["family", fid]], mobile_url=im.get("mo_src"))
            if aid and hint != "E":
                db.add("depicts", asset_id=aid, target_kind="family", target_id=fid,
                       level_label="probable" if hint in ("A", "A?C", "C") else "context",
                       evidence="pdp_feature_context" + ("+alt_scene" if hint == "A" else ""), confidence=0.75 if hint == "A" else 0.65)
        return seq

    # ── 2. 별칭 ──
    def build_aliases(self):
        for a, k, t in C.CURATED_ALIASES:
            if k == "category" and t not in self.categories:
                self.notes.append(f"큐레이션 별칭 대상 없음: {a} → {t}")
                continue
            self.alias_rows.append((a, k, t, "curated", "kb_build_curated"))
        generic = {norm(a) for a, k, *_ in self.alias_rows if k == "category"}
        self.alias_map: dict[str, set] = collections.defaultdict(set)
        kept = []
        for surface, kind, tid, akind, src in self.alias_rows:
            n = norm(surface)
            if not surface or len(n) < 2:
                continue
            if kind == "family" and akind == "site_name" and (n in generic or len(n) < 3):
                continue   # '냉장고' 같은 일반명은 카테고리로만 해소
            self.alias_map[n].add((kind, tid))
            kept.append((surface, kind, tid, akind, src))
            self.db.add("alias", surface=surface, surface_norm=n, target_kind=kind, target_id=tid, kind=akind, source=src)
        surfaces = sorted({s for s, k, *_ in kept if s and len(norm(s)) >= 3 and k != "vertical"}, key=len, reverse=True)
        self.alias_re = re.compile("|".join(re.escape(s) for s in surfaces))
        code_set = sorted(self.model_by_code, key=len, reverse=True)
        self.code_re = re.compile(r"(?<![A-Z0-9])(" + "|".join(re.escape(c) for c in code_set) + r")(?![A-Z0-9])") if code_set else None
        self.db.flush()

    # ── 3. 페이지 ──
    LANDING_ABOUT = {"/sec/business/system-air-conditioners/": ("category", "top_hvac"),
                     "/sec/business/smart-signage/": ("category", "top_display"),
                     "/sec/business/mobile/": ("category", "top_mobile"),
                     "/sec/business/printers/": ("category", "top_it"),
                     "/sec/business/pc/": ("category", "cat_notebook"),
                     "/sec/business/monitor/": ("category", "cat_monitors"),
                     "/sec/business/harman/": ("category", "cat_harman")}

    def pages(self):
        pages = load_pages()
        if not pages:
            self.notes.append("wkb_pages*.json 없음 — 페이지 단계 건너뜀")
            return
        self.page_items = pages
        db = self.db
        for u, it in pages.items():   # 사전 데이터에 없는 도입사례 페이지도 id 를 미리 정한다
            if it.get("kind") == "case_kr" and u not in self.case_by_path:
                self.case_by_path[u] = "dep_pg_" + hid(u)
        for u, it in pages.items():
            kind = it.get("kind")
            page_type = C.page_type_of(u, kind)
            doc_id = "doc_pg_" + hid(u)
            src = "src_site_us" if u.startswith("/us/") else "src_site_kr"
            locale = "en-US" if src == "src_site_us" else "ko-KR"
            title = it.get("title")
            if page_type == "case_study":   # 사례 페이지 <title>은 모두 같다 → 본문 h2(사례 제목)를 쓴다
                h2 = next((b.get("x") for b in it.get("blocks") or [] if b.get("t") == "h" and b.get("l") == 2), None)
                title = h2 or title
            self.add_doc(doc_id, "web_page", page_type, it.get("url") or SITE + u, title=title, desc=it.get("desc"),
                         og=it.get("ogImage"), locale=locale, fetched=it.get("fetchedAt"), published=it.get("pubDate"),
                         source_id=src, meta={"http_status": it.get("status"), "path": u})
            it["_doc"] = doc_id
            it["_ptype"] = page_type
            self.linearize(doc_id, page_type, u, it.get("blocks") or [])
            sid = self.solution_by_url.get(u)
            if sid:
                db.add("kg_edge", src_kind="solution" if sid.startswith("sol_") else "service", src_id=sid, rel="DESCRIBED_BY",
                       dst_kind="document", dst_id=doc_id, source_tier="T2_official", method="seed_url", confidence=1.0, evidence=u)
                self.db.c.execute(f"UPDATE {'solution' if sid.startswith('sol_') else 'service_product'} SET document_id=? WHERE id=?",
                                  (doc_id, sid))
            about = None
            if sid:
                about = ("solution" if sid.startswith("sol_") else "service", sid)
            elif u in self.LANDING_ABOUT and self.LANDING_ABOUT[u][1] in self.categories:
                about = self.LANDING_ABOUT[u]
            elif page_type in ("us_solution",):
                about = ("document", doc_id)
            if about and page_type in ("solution", "service", "landing", "us_solution"):
                self.heading_vps(doc_id, it.get("blocks") or [], about, locale)
        db.flush()

    def heading_vps(self, doc_id, blocks, about, locale):
        """솔루션·서비스·랜딩 페이지의 헤딩 → key_message, 바로 뒤 설명 → proof_point (원문 그대로)."""
        n = 0
        for i, b in enumerate(blocks):
            if b.get("t") != "h" or int(b.get("l") or 9) > 3:
                continue
            x = re.sub(r"\s+", " ", b.get("x") or "").strip()
            if not (4 <= len(x) <= 90) or x in C.NAV_KO:
                continue
            occ = f"occ_{doc_id}:{i + 1}"
            vid = self.add_vp("key_message", x, about[0], about[1], occ, "T2_official", "page_heading_verbatim", locale=locale)
            if vid:
                for j in range(i + 1, min(i + 4, len(blocks))):
                    y = re.sub(r"\s+", " ", blocks[j].get("x") or "").strip()
                    if blocks[j].get("t") == "h":
                        break
                    if blocks[j].get("t") == "p" and 15 <= len(y) <= 400:
                        self.add_vp("proof_point", y, about[0], about[1], f"occ_{doc_id}:{j + 1}", "T2_official",
                                    "page_text_verbatim", parent=vid, locale=locale)
                        break
                n += 1
            if n >= 40:
                break

    def linearize(self, doc_id, page_type, u, blocks):
        stack: dict[int, str] = {}
        seen_sig: set = set()
        sections: list[tuple[int, int]] = []
        start = None
        for i, b in enumerate(blocks):
            if b.get("t") == "h" and b.get("l") == 2:
                if start is not None:
                    sections.append((start, i))
                start = i
        if start is not None:
            sections.append((start, len(blocks)))
        dup_idx: set[int] = set()
        for s, e in sections:
            sig = tuple((b.get("t"), b.get("x") or C.img_key(b.get("src"))) for b in blocks[s:e] if b.get("t") in ("h", "p", "img"))
            sig = tuple(x for x in sig if x[0] != "img" or x[1])
            if sig in seen_sig:
                dup_idx.update(range(s, e))
            else:
                seen_sig.add(sig)
        vertical = self.vertical_for(u)
        for i, b in enumerate(blocks):
            t = b.get("t")
            if t == "h":
                lvl = int(b.get("l") or 2)
                stack[lvl] = re.sub(r"\s+", " ", b.get("x") or "").strip()
                for k in list(stack):
                    if k > lvl:
                        del stack[k]
            section = " > ".join(stack[k] for k in sorted(stack) if k >= 2 and stack[k]) or None
            dup = 1 if i in dup_idx else 0
            if t == "img":
                bid = self.add_block(doc_id, i + 1, "img", img=C.img_base(b.get("src")), alt=b.get("alt"), section=section, dup=dup)
                if dup:
                    continue
                cap = None
                j = i + 1
                while j < len(blocks) and blocks[j].get("t") == "img":
                    j += 1
                if page_type == "case_study" and j < len(blocks) and blocks[j].get("t") == "p" \
                        and 4 <= len(blocks[j].get("x") or "") <= 120 and (blocks[j].get("x") or "").strip() not in C.CAPTION_STOP \
                        and not (blocks[j].get("x") or "").strip().startswith("*"):
                    cap = blocks[j]["x"]
                hint, reason, rights = C.grade_hint_for(page_type, b, cap)
                self.add_image(b.get("src"), doc_id=doc_id, block_id=bid, page_type=page_type, alt=b.get("alt"),
                               caption=cap, section=section, grade_hint=hint, reason=reason, rights=rights, vertical=vertical)
            elif t == "a":
                self.add_block(doc_id, i + 1, "a", text=b.get("x"), href=b.get("href"), section=section, dup=dup)
            else:
                self.add_block(doc_id, i + 1, t, level=b.get("l"), text=b.get("x"), section=section, dup=dup)

    def vertical_for(self, u: str):
        if u.startswith("/us/"):
            m = re.search(r"/industries/([a-z\-]+)/", u)
            return self.vertical_by_slug.get("us:" + m.group(1)) if m else None
        slug = u.rstrip("/").split("/")[-1]
        return self.vertical_by_slug.get(slug)

    # ── 4. 업종 섹션 ──
    def industry_sections(self):
        db = self.db
        label_counts = collections.Counter()
        for u, it in self.page_items.items():
            if it.get("_ptype") not in ("industry", "us_vertical"):
                continue
            en = u.startswith("/us/")
            lang, locale = ("en", "en-US") if en else ("ko", "ko-KR")
            vertical = self.vertical_for(u)
            doc_id = it["_doc"]
            blocks = it.get("blocks") or []
            dup = {s for s, d in db.q("SELECT seq, is_duplicate FROM document_block WHERE document_id=?", (doc_id,)) if d}
            secs = C.parse_industry_blocks(blocks, dup, locale=lang)
            for k, s in enumerate(secs):
                sid = "sec_" + hid(doc_id, k)
                labels = s.get("labels") or []
                spaces: list[str] = []
                for lb in labels:
                    sp = C.spaces_for_label(lb, lang, vertical)
                    label_counts[(lb, locale, sp[0] if sp else None)] += 1
                    spaces += [x for x in sp if x not in spaces]
                method = "label_dict" if spaces else None
                if s["kind"] == "scene":   # 제목의 공간 표현도 더한다(예: '…로비 공간' + 라벨 '호텔 리셉션')
                    tsp = [x for x, _ in C.spaces_in_text(s.get("title") or "", lang, vertical)]
                    add = [x for x in tsp if x not in spaces]
                    if add:
                        spaces += add
                        method = (method + "+title_keyword") if method else "title_keyword"
                space = spaces[0] if spaces else None
                occ = f"occ_{doc_id}:{s['start'] + 1}"
                db.add("industry_section", id=sid, vertical_id=vertical, document_id=doc_id, seq=k, kind=s["kind"],
                       title=s.get("title"), description=s.get("description"), tagline=s.get("tagline"),
                       space_label=s.get("space_label"), space_type_id=space, space_types_json=spaces or None,
                       space_method=method or "none", labels_json=labels or None, chips_json=s.get("chips") or None,
                       block_from=s["start"] + 1, block_to=s["end"], source_occurrence_id=occ,
                       source_tier="T2_official", method="industry_parser_v2")
                self.stats["industry_sections"] += 1
                if s["kind"] == "scene":
                    t_id = self.add_vp("key_message", s.get("title"), "industry_section", sid, occ, "T2_official",
                                       "industry_heading_verbatim", vertical=vertical, space=space, locale=locale)
                    if s.get("description"):
                        docc = f"occ_{doc_id}:{s['desc_idx'] + 1}" if s.get("desc_idx") is not None else occ
                        self.add_vp("proof_point", s["description"], "industry_section", sid, docc, "T2_official",
                                    "industry_text_verbatim", parent=t_id, vertical=vertical, space=space, locale=locale)
                if s["kind"] == "hero" and s.get("title"):
                    self.add_vp("tagline", ((s.get("tagline") + " ") if s.get("tagline") else "") + s["title"],
                                "vertical", vertical, occ, "T2_official", "industry_hero_verbatim", vertical=vertical, locale=locale)
                kept = []
                for item in s.get("items", []):
                    tk, tid, how, conf, path, flt = self.resolve_item(item, fuzzy=item.get("item_kind") == "listed_item")
                    if item.get("item_kind") == "listed_item" and not tid and not item.get("product_cue"):
                        continue   # 링크 없는 나열 항목 중 제품명이 아닌 기능 문구(예: '장수명', '에너지 절감')는 버린다
                    kept.append((item, (tk, tid, how, conf, path, flt)))
                for j, (item, res) in enumerate(kept):
                    tk, tid, how, conf, path, flt = res
                    if en and how == "name_alias":
                        conf = min(conf, 0.5)   # US 페이지 이름 → KR 카탈로그 대응은 약하게
                    isl = item.get("space_label")
                    isp = C.space_for_label(isl, lang, vertical) if isl else None
                    img_ids = []
                    for im in item.get("imgs", []):
                        b = blocks[im]
                        a = self.images.get(C.img_key(b.get("src")))
                        if not a:
                            continue
                        img_ids.append(a["id"])
                        o = self.occ_by_asset_doc.get((a["id"], doc_id))
                        if o:
                            o["context_space_type_id"] = isp or space
                            o["context_vertical_id"] = vertical
                            o["context_entities_json"] = [[tk, tid]] if tid else None
                            o["section_path"] = " > ".join(x for x in (s.get("title"), item.get("name")) if x)
                        if tid:
                            db.add("depicts", asset_id=a["id"], target_kind=tk, target_id=tid,
                                   level_label="confirmed" if s["kind"] == "cases" else "probable",
                                   evidence="industry_section_item_context", confidence=0.9 if s["kind"] == "cases" else 0.6)
                    db.add("industry_section_item", id="si_" + hid(sid, j), section_id=sid, seq=j, item_kind=item.get("item_kind"),
                           item_name=item.get("name"), item_tagline=item.get("tagline"), link_url=item.get("href"),
                           link_path=path, link_filter=flt, item_space_label=isl, item_space_type_id=isp,
                           target_kind=tk, target_id=tid, resolve_method=how, confidence=conf,
                           image_ids_json=sorted(set(img_ids)) or None,
                           source_occurrence_id=f"occ_{doc_id}:{item['idx'] + 1}", source_tier="T2_official")
                    self.stats["industry_items"] += 1
                    if item.get("tagline") and tid and s["kind"] == "scene":
                        tl = item["tagline"]
                        if re.search(r"(된|한|는|운|진|갖춘|있는|위한|의|로)$", tl) and item.get("name"):
                            tl = f"{tl} {item['name']}"     # '호텔 운영에 최적화된' + '링크 클라우드 솔루션'
                        tocc = f"occ_{doc_id}:{(item['tagline_idx'] if item.get('tagline_idx') is not None else item['idx']) + 1}"
                        self.add_vp("key_message", tl, tk, tid, tocc, "T2_official",
                                    "industry_item_tagline_verbatim", vertical=vertical, space=isp or space, locale=locale)
        for (label, loc, space), n in label_counts.items():
            db.add("space_label", label=label, locale=loc, space_type_id=space,
                   method="curated_dict" if space else "unmapped", status="draft", occurrences=n)
        db.flush()

    def resolve_item(self, item, fuzzy=False):
        """업종 섹션 항목·도입사례 관련 제품 → (target_kind, target_id, method, confidence, link_path, filter)."""
        href = item.get("href") or ""
        path = flt = None
        if href:
            m = re.match(r"(?:https?://(?:www\.)?samsung\.com)?(/[^?#]*)(?:\?([^#]*))?", href.strip())
            if m:
                path, flt = to_path(m.group(1)), m.group(2)
                if path in self.solution_by_url:   # 솔루션 상세 URL 은 상품 카드이기도 하다 → 솔루션 엔티티를 우선(SOLD_AS 로 상품과 연결)
                    tid = self.solution_by_url[path]
                    return ("solution" if tid.startswith("sol_") else "service"), tid, "link_solution_page", 0.95, path, flt
                if path in self.family_by_url:
                    return "family", self.family_by_url[path], "link_pdp", 0.95, path, flt
                if path in self.case_by_path:
                    return "deployment", self.case_by_path[path], "link_case_page", 0.95, path, flt
                lm = re.match(r"/sec/business/([^/]+)/(all-[^/]+)/$", path)
                if lm:
                    cid = self.cat_by_listpath.get(f"{lm.group(1)}/{lm.group(2)}") or self.cat_by_root.get(lm.group(1))
                    if cid:
                        f0 = (flt or "").split("&")[0].split("+")[0].strip()
                        if f0 and f"{cid}__{f0}" in self.categories:
                            return "category", f"{cid}__{f0}", "link_category_list+subcat", 0.92, path, flt
                        return "category", cid, "link_category_list" + ("+filter" if flt else ""), 0.9, path, flt
                rm = re.match(r"/sec/business/([^/]+)/$", path)
                if rm and rm.group(1) in self.cat_by_root:
                    return "category", self.cat_by_root[rm.group(1)], "link_category_landing", 0.85, path, flt
                if path in self.LANDING_ABOUT and self.LANDING_ABOUT[path][1] in self.categories:
                    k, t = self.LANDING_ABOUT[path]
                    return k, t, "link_category_landing", 0.85, path, flt
                cm = re.search(r"/([A-Za-z0-9\-]{6,})/$", path)
                if cm and cm.group(1).upper() in self.model_by_code:
                    mid = self.model_by_code[cm.group(1).upper()]
                    return "model", mid, "link_model_code", 0.9, path, flt
                for pre, k, t in C.LEGACY_PATH_MAP:
                    if path.startswith(pre) and (t in self.categories or k != "category"):
                        return k, t, "link_legacy_path", 0.75, path, flt
                seg = path.split("/")[3] if path.startswith("/sec/business/") and len(path.split("/")) > 3 else None
                if seg and seg in self.cat_by_root:
                    return "category", self.cat_by_root[seg], "link_path_root", 0.7, path, flt
            if path is None or path.startswith("/us/") or "samsungknox.com" in href:
                for frag, k, t in C.US_PATH_MAP:
                    if frag in href and (t in self.categories or k != "category"):
                        return k, t, "us_link_path_map", 0.55, path, flt
        tk, tid, conf = (self.alias_lookup_fuzzy if fuzzy else self.alias_lookup)(item.get("name"))
        if tid:
            return tk, tid, "name_alias" if not fuzzy else "name_alias_substring", conf, path, flt
        return None, None, "unresolved", 0.0, path, flt

    def alias_lookup(self, name):
        n = norm(name)
        if not n:
            return None, None, 0
        hits = self.alias_map.get(n)
        if hits:
            k, t = sorted(hits, key=lambda h: (C.KIND_PRIORITY.get(h[0], 9), h[1]))[0]
            return k, t, 0.75 if len(hits) == 1 else 0.55
        return None, None, 0

    def alias_lookup_fuzzy(self, text):
        n = norm(text)
        if not n:
            return None, None, 0
        if n in self.alias_map:
            hits = self.alias_map[n]
            k, t = sorted(hits, key=lambda h: (C.KIND_PRIORITY.get(h[0], 9), h[1]))[0]
            return k, t, 0.8 if len(hits) == 1 else 0.6
        best = None
        for m in self.alias_re.finditer(text):
            s = norm(m.group(0))
            if s in self.alias_map and (best is None or len(s) > len(best)):
                best = s
        if best:
            hits = self.alias_map[best]
            k, t = sorted(hits, key=lambda h: (C.KIND_PRIORITY.get(h[0], 9), h[1]))[0]
            return k, t, 0.6 if len(hits) == 1 else 0.45
        return None, None, 0

    # ── 5. 도입사례 ──
    def cases(self):
        d = load_json("prior_case_studies.json") or {"cases": []}
        db = self.db
        by_path = {u: it for u, it in self.page_items.items() if it.get("_ptype") == "case_study"}
        matched = set()
        rows = []
        for c in d["cases"]:
            p = to_path(c.get("url"))
            it = by_path.get(p) if p else None
            if it:
                matched.add(p)
            rows.append(("dep_" + str(c["id"]), c, it))
        for p, it in by_path.items():
            if p not in matched:
                rows.append(("dep_pg_" + hid(p), None, it))
        for did, c, it in rows:
            c = c or {}
            site_ind = site_scale = None
            title = c.get("title")
            date = c.get("date")
            if it:
                blocks = it.get("blocks", [])
                texts = [re.sub(r"\s+", " ", b.get("x") or "").strip() for b in blocks if b.get("t") == "p"]
                site_ind = "; ".join(sorted({t.split(":", 1)[1].strip() for t in texts if re.match(r"^업종\s*:", t)})) or None
                site_scale = "; ".join(sorted({t.split(":", 1)[1].strip() for t in texts if re.match(r"^규모\s*:", t)})) or None
                if not title:
                    h = next((b for b in blocks if b.get("t") == "h" and b.get("l") == 2), None)
                    title = h.get("x") if h else it.get("title")
                if not date:
                    date = next((t for t in texts if re.fullmatch(r"20\d{2}[-.]\d{2}[-.]\d{2}", t)), None)
            verts = sorted({C.KR_CASE_INDUSTRY.get(x) for x in c.get("industry", []) if C.KR_CASE_INDUSTRY.get(x)})
            db.add("deployment", id=did, prior_id=c.get("id"), title=title, date=date,
                   url=c.get("url") or (it.get("url") if it else None), format=c.get("format") or ("page" if it else None),
                   document_id=it.get("_doc") if it else None, customer_type=c.get("customer_type"),
                   scale=c.get("scale"), quote=c.get("quote"), industry_raw_json=c.get("industry"),
                   product_group_json=c.get("product"), solution_group_json=c.get("solution"), vertical_ids_json=verts,
                   site_industry_text=site_ind, site_scale_text=site_scale, source_tier="T3_case",
                   method=("prior_llm_extract" if c.get("customer_type") is not None else "prior_listing_only") if c else "page_only")
            self.stats["deployments"] += 1
            v0 = verts[0] if verts else None
            for sp in c.get("space") or []:
                db.add("deployment_space", deployment_id=did, space_raw=sp, space_type_id=C.space_for_label(sp, "ko", v0),
                       method="curated_keyword")
            for o in c.get("offer") or []:
                tk, tid, conf = self.alias_lookup_fuzzy(o)
                db.add("deployment_item", deployment_id=did, item_raw=o, target_level=C.LEVEL_OF.get(tk), target_kind=tk,
                       target_id=tid, resolve_method="alias_substring" if tid else "unresolved", confidence=conf,
                       source="prior_llm_offer", source_tier="T5_llm_extracted")
            for kind in ("needs", "constraints", "decision_factors", "req_tags", "proposal_content", "new_req"):
                for x in c.get(kind) or []:
                    db.add("deployment_need", deployment_id=did, need_raw=x, kind=kind)
            for k, pr in enumerate(c.get("proof") or []):
                db.add("kpi_claim", id="kpi_" + hid(did, k), deployment_id=did, text=pr,
                       has_number=int(bool(re.search(r"\d", pr))), claim_flag=1, source_tier="T3_case", method="prior_llm_extract")
                self.stats["kpi_claims"] += 1
            if c.get("quote"):
                self.add_vp("proof_point", c["quote"], "deployment", did, None, "T5_llm_extracted", "prior_llm_quote")
            if it:
                self.case_related(did, it)
                for o in self.occ_by_doc.get(it["_doc"], []):
                    o["context_entities_json"] = (o.get("context_entities_json") or []) + [["deployment", did]]
                    if v0:
                        o["context_vertical_id"] = o.get("context_vertical_id") or v0
                    if o["page_type"] == "case_study":
                        db.add("depicts", asset_id=o["asset_id"], target_kind="deployment", target_id=did,
                               level_label="confirmed", evidence="case_page", confidence=0.95)
        db.flush()

    def case_related(self, did, it):
        """도입사례 페이지 하단 '관련 제품' 링크 = 사이트가 직접 밝힌 사용 제품(T2)."""
        blocks = it.get("blocks", [])
        start = next((i for i, b in enumerate(blocks) if b.get("t") == "p" and (b.get("x") or "").strip() == "관련 제품"), None)
        if start is None:
            return
        i = start + 1
        while i < len(blocks):
            b = blocks[i]
            if b.get("t") == "p" and (b.get("x") or "").strip() and not (b.get("x") or "").strip().startswith("*"):
                break
            if b.get("t") == "a" and b.get("href"):
                name = (b.get("x") or "").strip()
                if not name and i + 1 < len(blocks) and blocks[i + 1].get("t") == "img":
                    name = (blocks[i + 1].get("alt") or "").strip()
                tk, tid, how, conf, path, flt = self.resolve_item({"name": name, "href": b["href"]}, fuzzy=True)
                self.db.add("deployment_item", deployment_id=did, item_raw=name or b["href"], target_level=C.LEVEL_OF.get(tk),
                            target_kind=tk, target_id=tid, resolve_method=how, confidence=conf, source="case_related_link",
                            link_url=b["href"], source_tier="T2_official")
                self.stats["case_related_links"] += 1
            i += 1

    # ── 6. 언급 ──
    def mentions(self):
        db = self.db
        n = 0
        for bid, b in self.block_index.items():
            if b["t"] in ("spec",):
                continue
            text = " ".join(x for x in (b.get("text"), b.get("alt")) if x)
            if not text:
                continue
            spans = []
            if self.code_re:
                for m in self.code_re.finditer(text):
                    spans.append((m.start(), m.end(), m.group(0), "model", self.model_by_code[m.group(0)], "code_exact", 1.0))
            for m in self.alias_re.finditer(text):
                s = norm(m.group(0))
                hits = self.alias_map.get(s)
                if not hits:
                    continue
                k, t = sorted(hits, key=lambda h: (C.KIND_PRIORITY.get(h[0], 9), h[1]))[0]
                if any(a <= m.start() < e for a, e, *_ in spans):
                    continue
                conf = 0.9 if k in ("family", "solution", "service") else 0.7
                if len(hits) > 1:
                    conf -= 0.2
                spans.append((m.start(), m.end(), m.group(0), k, t, "alias_exact", conf))
            for a, e, surf, k, t, how, conf in spans:
                db.add("mention", id="men_" + hid(bid, a, surf), occurrence_id="occ_" + bid, document_id=b["doc"], block_id=bid,
                       surface=surf, mention_type=k, resolved_level=C.LEVEL_OF.get(k), resolved_kind=k, resolved_id=t,
                       method=how, confidence=round(conf, 2))
                n += 1
        self.stats["mentions"] = n
        db.flush()

    # ── 7. 역량 ──
    def capabilities(self):
        db = self.db
        rows = db.q("SELECT id, category_id, subcategory_slug, name_ko FROM product_family")
        tags = collections.defaultdict(set)
        for fid, flt in db.q("SELECT family_id, site_filter FROM product_tag"):
            tags[fid].add(flt)
        specs = collections.defaultdict(list)
        for fid, key, raw, n1, unit, a in db.q("SELECT family_id, norm_key, value_raw, value_num, value_unit, attr_name FROM spec_value"):
            specs[fid].append((key, raw or "", n1, unit, a or ""))
        feat_text = collections.defaultdict(str)
        for fid, h, body in db.q("SELECT family_id, headline, body FROM feature_block"):
            feat_text[fid] += " " + (h or "") + " " + (body or "")
        for fid, cid, sub, name in rows:
            ctx = {"category": cid or "", "sub": sub or "", "name": name or "", "tags": tags[fid], "specs": specs[fid],
                   "text": (name or "") + " " + feat_text[fid]}
            for r in C.AUTO_RULES:
                ev = r["fn"](ctx)
                if ev:
                    db.add("provides", family_id=fid, model_id=None, capability_id="cap_" + r["cap"], rule_id=r["id"],
                           evidence=ev[:300], source_tier="T2_official", method="rule_presence_v1")
                    self.stats["provides"] += 1
        db.flush()

    # ── 8. 이미지 저장 ──
    def save_images(self):
        db = self.db
        for a in self.images.values():
            db.add("image_asset", id=a["id"], url=a["url"] or a["url_mobile"], url_mobile=a["url_mobile"],
                   media_type=a["media_type"], grade_hint=a["grade_hint"], grade_hint_reason=a["reason"], rights=a["rights"],
                   n_occurrences=a["n"], vlm_status="pending")
        for o in self.img_occ:
            db.add("image_occurrence", **o)
        self.stats["image_assets"] = len(self.images)
        self.stats["image_occurrences"] = len(self.img_occ)
        db.flush()

    # ── 9. KG ──
    def kg(self):
        db = self.db

        def E(sk, si, rel, dk, di, tier, method, conf, ev=None):
            db.add("kg_edge", src_kind=sk, src_id=si, rel=rel, dst_kind=dk, dst_id=di, source_tier=tier, method=method,
                   confidence=conf, evidence=ev)

        for fid, cid, sub in db.q("SELECT id, category_id, subcategory_slug FROM product_family"):
            if cid:
                tgt = f"{cid}__{sub}" if sub and f"{cid}__{sub}" in self.categories else cid
                E("family", fid, "IN_CATEGORY", "category", tgt, "T2_official", "site_api", 1.0)
        for fid, cid, role in db.q("SELECT family_id, category_id, role FROM family_category"):
            E("family", fid, "LISTED_IN" if role == "list" else "IN_COMP_CATEGORY", "category", cid, "T2_official", "site_list", 1.0)
        for cid, parent in db.q("SELECT id, parent_id FROM category WHERE parent_id IS NOT NULL"):
            E("category", cid, "CHILD_OF", "category", parent, "T2_official", "site_structure", 1.0)
        for vid, parent in db.q("SELECT id, parent_id FROM vertical WHERE parent_id IS NOT NULL"):
            E("vertical", vid, "CHILD_OF", "vertical", parent, "T2_official", "site_structure", 1.0)
        for seg, kr, us, status in db.q("SELECT winmate_segment, kr_vertical_codes, us_vertical_codes, status FROM segment_mapping"):
            for v in (json.loads(kr or "[]") or []) + (json.loads(us or "[]") or []):
                if v and not str(v).startswith("<<"):
                    E("vertical", seg, "MAPS_TO", "vertical", v, "T5_seed_draft", "seed", 0.6, status)
        for mid, fid in db.q("SELECT id, family_id FROM product_model"):
            E("model", mid, "VARIANT_OF", "family", fid, "T2_official", "site_api", 1.0)
        for fid, kind, val, flt in db.q("SELECT family_id, tag_kind, tag_value, site_filter FROM product_tag"):
            E("family", fid, "HAS_TAG", "tag", f"{kind}:{flt}", "T2_official", "site_list_filter", 1.0, val)
        for fid, cap, rule, ev in db.q("SELECT family_id, capability_id, rule_id, evidence FROM provides"):
            E("family", fid, "PROVIDES", "capability", cap, "T5_rule_draft", rule, 0.8, ev)
        for sp, cap, strength in db.q("SELECT space_type_id, capability_id, strength FROM requires"):
            E("space_type", sp, "REQUIRES_" + strength.upper(), "capability", cap, "T5_seed_draft", "seed", 0.5)
        for sid, vert, spaces in db.q("SELECT id, vertical_id, space_types_json FROM industry_section WHERE vertical_id IS NOT NULL AND space_types_json IS NOT NULL"):
            for sp in json.loads(spaces):
                E("vertical", vert, "HAS_SPACE", "space_type", sp, "T2_official", "industry_page_section", 0.9, sid)
        for sid, vert, spaces, kind, tk, tid, isp in db.q("""SELECT s.id, s.vertical_id, s.space_types_json, s.kind, i.target_kind, i.target_id,
                i.item_space_type_id FROM industry_section_item i JOIN industry_section s ON s.id=i.section_id WHERE i.target_id IS NOT NULL"""):
            if kind == "cases":
                if vert:
                    E("vertical", vert, "FEATURED_CASE", tk, tid, "T2_official", "industry_page_cases", 0.9, sid)
                continue
            for sp in ([isp] if isp else json.loads(spaces or "[]")):
                E("space_type", sp, "RECOMMENDED_BY_SITE", tk, tid, "T2_official", "industry_page_section", 0.85, f"{vert}|{sid}")
            if vert:
                E("vertical", vert, "FEATURED_BY_SITE", tk, tid, "T2_official",
                  "industry_page_recommend" if kind == "recommend" else "industry_page_section", 0.85, sid)
        for did, vids in db.q("SELECT id, vertical_ids_json FROM deployment"):
            for v in json.loads(vids or "[]"):
                E("deployment", did, "IN_VERTICAL", "vertical", v, "T3_case", "site_case_filter", 0.9)
        for did, sp in db.q("SELECT DISTINCT deployment_id, space_type_id FROM deployment_space WHERE space_type_id IS NOT NULL"):
            E("deployment", did, "AT_SPACE", "space_type", sp, "T5_llm_extracted", "prior_llm+curated_keyword", 0.6)
        for did, tk, tid, conf, src in db.q("SELECT deployment_id, target_kind, target_id, max(confidence), source FROM deployment_item WHERE target_id IS NOT NULL GROUP BY deployment_id, target_kind, target_id, source"):
            if src == "case_related_link":
                E("deployment", did, "USES", tk, tid, "T2_official", "case_related_link", max(conf, 0.9))
            else:
                E("deployment", did, "USES", tk, tid, "T5_llm_extracted", "prior_llm+alias", conf)
        for doc, kind, tid, cnt in db.q("""SELECT d.id, m.resolved_kind, m.resolved_id, count(*) FROM mention m
                JOIN deployment d ON d.document_id=m.document_id GROUP BY d.id, m.resolved_kind, m.resolved_id"""):
            E("deployment", doc, "MENTIONS", kind, tid, "T3_case", "case_page_mention", min(0.95, 0.5 + 0.1 * cnt), str(cnt))
        for aid, tk, tid, lvl, conf in db.q("SELECT asset_id, target_kind, target_id, level_label, max(confidence) FROM depicts GROUP BY asset_id, target_kind, target_id, level_label"):
            E("image", aid, "DEPICTS_" + lvl.upper(), tk, tid, "T2_official", "context", conf)
        for aid, sp in db.q("SELECT DISTINCT asset_id, context_space_type_id FROM image_occurrence WHERE context_space_type_id IS NOT NULL"):
            E("image", aid, "SHOWN_IN_CONTEXT_OF", "space_type", sp, "T2_official", "page_context", 0.6)
        for vid, about_kind, about_id in db.q("SELECT id, about_kind, about_id FROM value_prop WHERE about_id IS NOT NULL"):
            E("value_prop", vid, "ABOUT", about_kind, about_id, "T2_official", "verbatim", 1.0)
        db.flush()
        self.stats["kg_edges"] = db.q("SELECT count(*) FROM kg_edge")[0][0]

    # ── 10. 텍스트 청크·FTS ──
    def chunks(self):
        db = self.db
        rows = db.q("""SELECT b.id, b.document_id, b.block_type, b.text, b.img_alt, b.section_path, d.page_type, d.url
                       FROM document_block b JOIN source_document d ON d.id=b.document_id
                       WHERE b.is_duplicate=0 AND b.block_type IN ('h','p','feature','usp','spec','img')
                       ORDER BY b.document_id, b.seq""")
        ment = collections.defaultdict(set)
        for bid, k, t in db.q("SELECT block_id, resolved_kind, resolved_id FROM mention"):
            ment[bid].add(f"{k}:{t}")
        state = {"cur": None, "buf": [], "refs": set(), "seen": set()}
        emitted = set()

        def flush():
            cur, buf = state["cur"], state["buf"]
            if cur and buf:
                text = "\n".join(buf)
                # id = 문서·섹션·전체 본문 해시(앞 80자만 쓰면 같은 머리글의 다른 청크가 충돌해 text_chunk 에서 빠졌다)
                cid = "ch_" + hid(cur[0], cur[1], text)
                if cid not in emitted:          # 같은 문서·섹션의 완전 중복 청크는 한 번만(text_chunk 와 FTS 를 같게)
                    emitted.add(cid)
                    db.add("text_chunk", id=cid, document_id=cur[0], page_type=cur[2], section_path=cur[1], text=text,
                           entity_refs_json=sorted(state["refs"]), url=cur[3])
                    db.c.execute("INSERT INTO chunk_fts(text, section_path, chunk_id) VALUES (?,?,?)", (text, cur[1] or "", cid))
                    self.stats["chunks"] += 1
            state["buf"], state["refs"] = [], set()

        for bid, doc, bt, text, alt, sec, ptype, url in rows:
            key = (doc, sec, ptype, url)
            t = text if bt != "img" else (f"[이미지] {alt}" if alt else None)
            if not t:
                continue
            t = t.strip()
            if key != state["cur"]:
                flush()
                state["cur"] = key
                state["seen"] = set()
            elif sum(len(x) for x in state["buf"]) > 900:
                flush()
            if t in state["seen"]:      # 같은 섹션 안 반복 문구(PC/MO 잔여 중복)
                continue
            state["seen"].add(t)
            state["buf"].append(t)
            state["refs"] |= ment.get(bid, set())
        flush()
        db.flush()

    # ── 11. 메타 ──
    def finish(self):
        db = self.db
        cnt = collections.Counter(r[0] for r in db.q("SELECT attr_id FROM spec_value"))
        for aid, (root, g, a, key, unit) in self.spec_attrs.items():
            db.add("spec_attr_def", id=aid, category_root=root, group_name=g, attr_name=a, norm_key=key, unit=unit, n_values=cnt[aid])
        self.stats["chunks"] = db.q("SELECT count(*) FROM text_chunk")[0][0]   # 같은 id 청크는 한 번만 들어간다
        for k, v in self.stats.items():
            db.add("kb_meta", key="count." + k, value=str(v))
        db.add("kb_meta", key="notes", value=json.dumps(self.notes, ensure_ascii=False))
        P = load_json("wkb_products.json") or {}
        db.add("kb_meta", key="products_fetched_at", value=P.get("fetchedAt") or P.get("startedAt"))
        db.add("kb_meta", key="schema_version", value="kb_v1")
        db.flush()
        fk = db.c.execute("PRAGMA foreign_key_check").fetchall()
        byt = collections.Counter(r[0] for r in fk)
        db.add("kb_meta", key="foreign_key_violations", value=json.dumps(dict(byt), ensure_ascii=False))
        db.flush()
        db.c.execute("ANALYZE")
        db.c.commit()

    def run(self):
        self.sources()
        self.seeds()
        self.products()
        self.build_aliases()
        self.pages()
        self.industry_sections()
        self.cases()
        self.mentions()
        self.capabilities()
        self.save_images()
        self.kg()
        self.chunks()
        self.finish()
        return self.stats


if __name__ == "__main__":
    st = Builder().run()
    print(json.dumps(st, ensure_ascii=False, indent=1))
