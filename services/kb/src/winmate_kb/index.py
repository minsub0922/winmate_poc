"""KB 에서 한 번 읽어 두는 색인(읽기 전용 DB 라 프로세스 수명 동안 그대로 쓴다).

화면용 API 가 자주 쓰는 표(분류 · 제품군 · 모델 · 정규 스펙 · 문서 · 이미지 등장 · 사례 · 사진)를 메모리에 둔다.
"""
from __future__ import annotations

import collections
import json
import math
import re
import threading
from functools import cached_property
from typing import Any
from urllib.parse import unquote

from . import curation
from .engine import engine, q

NEG_VALUE = re.compile(r"^(없음|미지원|미적용|해당\s*없음|no|n/?a|x|-|—|불가)$", re.I)
NUM = re.compile(r"-?\d[\d,]*\.?\d*")


def norm(s: str | None) -> str:
    """query.py 의 norm 과 같다(공백 · 기호 제거, 소문자)."""
    if not s:
        return ""
    s = s.replace(" ", " ").replace("™", "").replace("®", "")
    return re.sub(r"[\s·∙\-_/()\[\]]+", "", s).lower()


def first_number(s: str | None) -> float | None:
    if not s:
        return None
    m = NUM.search(s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def jloads(s: str | None, default: Any = None) -> Any:
    if not s:
        return default
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        return default


class Index:
    def __init__(self) -> None:
        disp = curation.load("display")
        self.meta = {r["key"]: r["value"] for r in q("SELECT key, value FROM kb_meta")}

        # ── 분류 ──
        self.cats = {r["id"]: r for r in q("SELECT id, code, parent_id, name_ko, level, list_url, site_disp_clsf_no, origin FROM category")}
        self.cat_children: dict[str | None, list[str]] = collections.defaultdict(list)
        for cid, c in self.cats.items():
            if c["level"] == 1:
                self.cat_children[None].append(cid)
            elif c["parent_id"] in self.cats:
                self.cat_children[c["parent_id"]].append(cid)
        order = {c: i for i, c in enumerate(disp.get("l1_order") or [])}
        self.cat_children[None].sort(key=lambda c: (order.get(c, 99), c))
        for k, v in self.cat_children.items():
            if k is not None:
                v.sort(key=lambda c: c.lower())

        # ── 제품군 · 모델 ──
        self.fams = {r["id"]: r for r in q("SELECT * FROM product_family")}
        self.models: dict[str, dict[str, Any]] = {}
        self.model_by_code: dict[str, str] = {}
        self.fam_models: dict[str, list[str]] = collections.defaultdict(list)
        for m in q("SELECT * FROM product_model ORDER BY rowid"):
            self.models[m["id"]] = m
            self.model_by_code[m["model_code"].upper()] = m["id"]
            self.fam_models[m["family_id"]].append(m["id"])
        self.fam_by_goods = {f["goods_id"]: fid for fid, f in self.fams.items()}
        self.fam_list_cats: dict[str, set[str]] = collections.defaultdict(set)
        self.cat_fams: dict[str, set[str]] = collections.defaultdict(set)
        for r in q("SELECT family_id, category_id, role FROM family_category"):
            if r["role"] == "list":
                self.fam_list_cats[r["family_id"]].add(r["category_id"])
                self.cat_fams[r["category_id"]].add(r["family_id"])
        for fid, f in self.fams.items():
            if f["category_id"]:
                if f["category_id"] in self.cats and not self.fam_list_cats[fid]:
                    self.cat_fams[f["category_id"]].add(fid)
                if f["subcategory_slug"]:
                    sub = f"{f['category_id']}__{f['subcategory_slug']}"
                    if sub in self.cats:
                        self.cat_fams[sub].add(fid)
        # L1 = 자식 L2 들의 합
        for l1 in self.cat_children[None]:
            for l2 in self.cat_children.get(l1, []):
                self.cat_fams[l1] |= self.cat_fams.get(l2, set())

        # ── 정규 스펙(모델별, 목록 열 · 칩용) ──
        self.mspec: dict[str, dict[str, list[dict[str, Any]]]] = collections.defaultdict(lambda: collections.defaultdict(list))
        for r in q("""SELECT id, model_id, family_id, group_name, attr_name, value_raw, norm_key, value_num, value_num2, value_unit,
                             source_occurrence_id FROM spec_value WHERE norm_key IS NOT NULL ORDER BY rowid"""):
            self.mspec[r["model_id"]][r["norm_key"]].append(r)
        self.models_with_spec = {r["model_id"] for r in q("SELECT DISTINCT model_id FROM spec_value")}

        # ── 문서 ──
        self.docs = {r["id"]: r for r in q("SELECT id, url, title, page_type, fetched_at, meta_json FROM source_document")}

        # ── 업종 ──
        self.verticals = {r["id"]: r for r in q("SELECT * FROM vertical ORDER BY rowid")}
        self.vert_children: dict[str, list[str]] = collections.defaultdict(list)
        for vid, v in self.verticals.items():
            if v["parent_id"]:
                self.vert_children[v["parent_id"]].append(vid)

        # ── 사례 ──
        self.deps = {r["id"]: r for r in q("SELECT * FROM deployment ORDER BY rowid")}
        self.dep_by_doc = {d["document_id"]: did for did, d in self.deps.items() if d["document_id"]}
        self.dep_verts = {did: jloads(d["vertical_ids_json"], []) for did, d in self.deps.items()}
        self.dep_targets: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
        for r in q("SELECT src_id, dst_kind, dst_id FROM kg_edge WHERE src_kind='deployment' AND rel IN ('USES','MENTIONS')"):
            self.dep_targets[r["src_id"]].add((r["dst_kind"], r["dst_id"]))
        self.dep_spaces: dict[str, list[str]] = collections.defaultdict(list)
        for r in q("SELECT deployment_id, space_type_id FROM deployment_space WHERE space_type_id IS NOT NULL ORDER BY rowid"):
            if r["space_type_id"] not in self.dep_spaces[r["deployment_id"]]:
                self.dep_spaces[r["deployment_id"]].append(r["space_type_id"])

        # ── 이미지 ──
        self.assets = {r["id"]: r for r in q("SELECT id, url, url_mobile, media_type, grade_hint, rights FROM image_asset")}
        self.occ: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
        for r in q("""SELECT o.id, o.asset_id, o.document_id, o.page_type, o.alt, o.caption, o.section_path,
                             o.context_space_type_id, o.context_vertical_id, o.context_entities_json, b.seq
                      FROM image_occurrence o LEFT JOIN document_block b ON b.id=o.block_id ORDER BY o.rowid"""):
            self.occ[r["asset_id"]].append(r)
        depicts = q("SELECT asset_id, target_kind, target_id, level_label FROM depicts")
        conf_fam = collections.defaultdict(set)
        conf_dep = collections.defaultdict(set)
        for r in depicts:
            if r["level_label"] == "confirmed":
                if r["target_kind"] == "family":
                    conf_fam[r["target_id"]].add(r["asset_id"])
                elif r["target_kind"] == "deployment":
                    conf_dep[r["target_id"]].add(r["asset_id"])
        # 제품군 갤러리(G4 와 같은 조건: pdp_gallery ∩ depicts confirmed) — PDP 갤러리 순서
        self.gallery: dict[str, list[str]] = {}
        for fid, aids in conf_fam.items():
            rows = []
            for a in aids:
                for o in self.occ.get(a, []):
                    if o["page_type"] == "pdp_gallery":
                        rows.append((o["seq"] if o["seq"] is not None else 10**9, a))
                        break
            rows.sort()
            if rows:
                self.gallery[fid] = [a for _, a in rows]
        # 사례 사진(G5 와 같은 조건: case_study ∩ depicts deployment) — 등급 A 먼저, 그다음 본문 순서
        gp = engine().C.GRADE_PRIORITY
        # 여러 사례 페이지에 같이 나오는 사진(관련 글 썸네일 · 제품 컷 등)은 뒤로 보낸다(빼지는 않는다)
        case_docs: dict[str, set[str]] = collections.defaultdict(set)
        for a, occs in self.occ.items():
            for o in occs:
                if o["page_type"] == "case_study":
                    case_docs[a].add(o["document_id"])
        self.shared_case_assets = {a for a, ds in case_docs.items() if len(ds) >= 3}
        self.dep_photos: dict[str, list[str]] = {}
        for did, aids in conf_dep.items():
            rows = []
            for a in aids:
                occs = [o for o in self.occ.get(a, []) if o["page_type"] == "case_study"]
                if not occs:
                    continue
                g = gp.get(self.assets[a]["grade_hint"], 9) if a in self.assets else 9
                if a in self.shared_case_assets:
                    g += 10
                rows.append((g, min((o["seq"] or 10**9) for o in occs), a))
            rows.sort()
            if rows:
                self.dep_photos[did] = [a for _, _, a in rows]

        # ── 솔루션(KB) ──
        self.solutions = {r["id"]: r for r in q("SELECT * FROM solution")}
        self.solution_docs = {s["document_id"]: sid for sid, s in self.solutions.items() if s["document_id"]}
        self.space_types = {r["id"]: r for r in q("SELECT * FROM space_type ORDER BY rowid")}

    # ── 분류 ──
    def l1_of(self, cid: str | None) -> str | None:
        seen = 0
        while cid and seen < 6:
            c = self.cats.get(cid)
            if not c:
                return None
            if c["level"] == 1:
                return cid
            cid = c["parent_id"]
            seen += 1
        return None

    def l2_of(self, cid: str | None) -> str | None:
        seen = 0
        while cid and seen < 6:
            c = self.cats.get(cid)
            if not c:
                return None
            if c["level"] == 2:
                return cid
            if c["level"] == 1:
                return None
            cid = c["parent_id"]
            seen += 1
        return None

    def cat_name(self, cid: str | None) -> str | None:
        c = self.cats.get(cid or "")
        return c["name_ko"] if c else None

    def cat_subtree(self, cid: str) -> set[str]:
        out, frontier = {cid}, [cid]
        while frontier:
            nxt = [c for x in frontier for c in self.cat_children.get(x, []) if c not in out]
            out |= set(nxt)
            frontier = nxt
        return out

    def fam_cats_all(self, fid: str) -> set[str]:
        """제품군이 속한 모든 분류(목록 + 하위 분류 + 상위 체인)."""
        f = self.fams.get(fid)
        cats = set(self.fam_list_cats.get(fid, set()))
        if f and f["category_id"]:
            cats.add(f["category_id"])
            if f["subcategory_slug"]:
                cats.add(f"{f['category_id']}__{f['subcategory_slug']}")
        out = set()
        for c in cats:
            cur, n = c, 0
            while cur and cur in self.cats and n < 6:
                out.add(cur)
                cur = self.cats[cur]["parent_id"]
                n += 1
        return out

    def fam_l2(self, fid: str) -> str | None:
        f = self.fams.get(fid)
        if not f:
            return None
        if f["category_id"] in self.cats:
            return self.l2_of(f["category_id"]) or f["category_id"]
        for c in sorted(self.fam_list_cats.get(fid, set())):
            l2 = self.l2_of(c)
            if l2:
                return l2
        return None

    def fam_l1(self, fid: str) -> str | None:
        return self.l1_of(self.fam_l2(fid))

    def fam_subcat(self, fid: str) -> str | None:
        f = self.fams.get(fid)
        if f and f["category_id"] and f["subcategory_slug"]:
            sub = f"{f['category_id']}__{f['subcategory_slug']}"
            return sub if sub in self.cats else None
        return None

    # ── 모델 ──
    def resolve_model(self, ref: str) -> str | None:
        """모델코드 · mdl_ · fam_(대표 모델) → mdl_ id. `/` 가 든 코드(LH012IWCMWS/XU)는 그대로 · %2F 로 받는다."""
        if not ref:
            return None
        r = ref.strip()
        if "%" in r:
            r = unquote(r)
        r = r.rstrip("/")
        if not r:
            return None
        if r.startswith("mdl_") and r in self.models:
            return r
        if r.startswith("fam_") and r in self.fams:
            return self.default_model(r)
        mid = self.model_by_code.get(r.upper())
        if mid:
            return mid
        if r.lower().startswith("kb:model:"):
            return self.resolve_model(r.split(":", 2)[2])
        return None

    def default_model(self, fid: str) -> str | None:
        ids = self.fam_models.get(fid, [])
        for mid in ids:
            if self.models[mid]["is_family_default"]:
                return mid
        f = self.fams.get(fid)
        if f and f["default_model_code"]:
            mid = self.model_by_code.get(f["default_model_code"].upper())
            if mid:
                return mid
        return ids[0] if ids else None

    def spec_rows(self, mid: str, key: str) -> list[dict[str, Any]]:
        return self.mspec.get(mid, {}).get(key, [])

    def pick_spec(self, mid: str, key: str) -> dict[str, Any] | None:
        rows = self.spec_rows(mid, key)
        if not rows:
            return None
        prefer = (curation.load("columns").get("prefer_attrs") or {}).get(key) or []
        for name in prefer:
            for r in rows:
                if r["attr_name"] == name:
                    return r
        return rows[0]

    def screen_cm(self, mid: str) -> float | None:
        r = self.pick_spec(mid, "screen_size_cm")
        return r["value_num"] if r and r["value_num"] else None

    def inch(self, mid: str) -> int | None:
        """00-shell §9.2: 모델코드의 크기 숫자 → 없으면 ceil(cm ÷ 2.54 − 0.05). 단순 반올림 금지.

        스마트 LED 사이니지(cat_led-signage)는 코드 숫자를 쓰지 않는다 — LH012IWCMWS 의 012 는 픽셀 피치(1.26 mm) 코드다
        (KB product_model.option 픽셀 피치로 확인). LED 는 화면 대각 데이터가 없어 null(08-birdseye 요청 2).
        """
        m = self.models.get(mid)
        if not m:
            return None
        cm = self.screen_cm(mid)
        l2 = self.fam_l2(m["family_id"]) or ""
        mm = re.match(r"^[A-Z]{2}(\d{2,3})", m["model_code"])
        if mm and l2 in CODE_INCH_L2:
            n = int(mm.group(1))
            if 10 <= n <= 300 and (cm is None or abs(n - cm / 2.54) <= 2.5):
                return n
        if cm:
            return math.ceil(cm / 2.54 - 0.05)
        return None

    def display_name(self, mid: str) -> tuple[str, str]:
        """(표시명, 근거). 갭 G-PRD-1: 규칙(display.yaml)에 맞으면 규칙, 아니면 모델코드."""
        m = self.models[mid]
        code = m["model_code"]
        l1 = self.fam_l1(m["family_id"])
        for rule in curation.load("display").get("display_name_rules") or []:
            if rule.get("l1") and l1 not in rule["l1"]:
                continue
            mm = re.match(rule["pattern"], code)
            if mm:
                return rule["template"].format(**mm.groupdict()), "code_rule"
        return code, "model_code"

    def series_label(self, fid: str) -> str:
        """00-shell §7.2.4 [제안]: marketing_model 이 영문 짧은 코드(≤6자)면 '{코드} Series', 아니면 제품군 이름."""
        f = self.fams[fid]
        mk = (f["marketing_model"] or "").strip()
        if mk and len(mk) <= 6 and re.fullmatch(r"[A-Za-z0-9]+", mk) and re.search(r"[A-Za-z]", mk):
            return f"{mk} Series"
        return (f["name_ko"] or fid).strip()

    def series_code(self, fid: str) -> str | None:
        f = self.fams[fid]
        mk = (f["marketing_model"] or "").strip()
        if mk and len(mk) <= 6 and re.fullmatch(r"[A-Za-z0-9]+", mk):
            return mk
        return None

    def is_bundle(self, fid: str) -> bool:
        f = self.fams[fid]
        name = f["name_ko"] or ""
        return f["goods_type_code"] == "20" or " + " in name or bool(re.search(r"\+(?=[^\s)])", name))

    def doc_family(self, doc_id: str | None) -> str | None:
        if doc_id and doc_id.startswith("doc_pdp_"):
            return self.fam_by_goods.get(doc_id[len("doc_pdp_"):])
        return None

    def vertical_name(self, vid: str | None) -> str | None:
        v = self.verticals.get(vid or "")
        return (v["name_ko"] or v["name_en"]) if v else None

    def vertical_expand(self, vid: str) -> set[str]:
        """업종과 그 하위 · 상위(사례 필터는 상위 KR 업종으로 붙어 있다)."""
        out = {vid}
        out |= set(self.vert_children.get(vid, []))
        v = self.verticals.get(vid)
        if v and v["parent_id"]:
            out.add(v["parent_id"])
        return out

    def body_deployments(self) -> list[str]:
        return [did for did, d in self.deps.items() if d["document_id"]]

    @cached_property
    def checked_at(self) -> str | None:
        """사례 코퍼스 확인 시각 = 사례 페이지 수집 시각 최댓값."""
        ts = [self.docs[d["document_id"]]["fetched_at"] for d in self.deps.values()
              if d["document_id"] and d["document_id"] in self.docs and self.docs[d["document_id"]]["fetched_at"]]
        return max(ts) if ts else None


DISPLAY_L2 = {"cat_smart-signage", "cat_led-signage", "cat_tvs", "cat_hotel-tvs", "cat_monitors"}
CODE_INCH_L2 = DISPLAY_L2 - {"cat_led-signage"}      # 모델코드 숫자 = 인치인 분류(LED 는 피치 코드)

_idx: Index | None = None
_lock = threading.Lock()


def idx() -> Index:
    global _idx
    if _idx is None:
        with _lock:
            if _idx is None:
                _idx = Index()
    return _idx
