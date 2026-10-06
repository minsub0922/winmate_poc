"""제품 탐색(분류 · 시리즈 · 모델 표 · 검색)과 제품 상세(00-shell §7.2.3 ~ §7.2.7)."""
from __future__ import annotations

import collections
import re
from typing import Any

from . import curation, imagecards
from .engine import kb, q
from .index import NEG_VALUE, first_number, idx, norm


# ── 표시 형식 ─────────────────────────────────────────────

def fmt_num(v: float | None) -> str:
    if v is None:
        return ""
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v)):,}"
    return f"{v:,.3f}".rstrip("0").rstrip(".")


def res_label(w: float | None, h: float | None) -> str | None:
    if not w or not h:
        return None
    key = f"{int(w)}x{int(h)}"
    labels = curation.load("display").get("resolution_labels") or {}
    return labels.get(key) or f"{int(w)} × {int(h)}"


_LED_FALLBACK = {"brightness": re.compile(r"^Brightness$", re.I), "pixel_pitch": re.compile(r"^Pixel\s*Pitch$", re.I)}


def _led_fallback(mid: str, col: str) -> dict[str, Any] | None:
    """스마트 LED 사이니지: 정규 키가 없는 영문 스펙 행(Optical Parameter › Brightness · Physical Parameter › Pixel Pitch)과
    모델 옵션 `픽셀 피치` 를 그대로 보여 준다(값은 원문, 계산 없음)."""
    I = idx()
    m = I.models[mid]
    if I.fam_l2(m["family_id"]) != "cat_led-signage" or col not in _LED_FALLBACK:
        return None
    for r in q("SELECT attr_name, value_raw FROM spec_value WHERE model_id=? ORDER BY rowid", (mid,)):
        if _LED_FALLBACK[col].match((r["attr_name"] or "").strip()) and r["value_raw"]:
            n = first_number(r["value_raw"])
            if col == "brightness":
                return {"display": f"{fmt_num(n)}nit" if n is not None else r["value_raw"], "nit": n, "raw": r["value_raw"]}
            return {"display": r["value_raw"], "value": n, "unit": "mm", "raw": r["value_raw"]}
    if col == "pixel_pitch" and "피치" in (m["option_name"] or "") and m["option_value"]:
        return {"display": m["option_value"], "value": first_number(m["option_value"]), "unit": "mm", "raw": m["option_value"]}
    return None


def _value(mid: str, col: str) -> dict[str, Any]:
    I = idx()
    none = {"display": "—"}
    if col == "size":
        inch = I.inch(mid)
        cm = I.screen_cm(mid)
        if inch is None and cm is None:
            return none
        return {"display": f'{inch}"' if inch is not None else f"{fmt_num(cm)} cm", "cm": cm, "inch": inch}
    if col in _LED_FALLBACK and not I.spec_rows(mid, (curation.load("columns").get("columns") or {}).get(col, {}).get("norm_key") or ""):
        fb = _led_fallback(mid, col)
        if fb:
            return fb
    if col == "brightness":
        r = I.pick_spec(mid, "brightness_nit")
        if not r:
            return none
        n = first_number(r["value_raw"])   # Typ = 원문의 첫 수(06-spec §4.15.4: value_num 은 Peak 일 수 있다)
        if n is None:
            return {"display": r["value_raw"], "raw": r["value_raw"]}
        unit = "nit" if "nit" in (r["value_raw"] or "").lower() or "nit" in (r["value_unit"] or "") else (r["value_unit"] or "nit")
        disp = f"{fmt_num(n)}nit" if unit == "nit" else f"{fmt_num(n)} {unit}"
        return {"display": disp, "nit": n, "raw": r["value_raw"]}
    if col == "resolution":
        r = I.pick_spec(mid, "resolution")
        if not r or not r["value_num"] or not r["value_num2"]:
            return none
        return {"display": res_label(r["value_num"], r["value_num2"]) or r["value_raw"], "w": int(r["value_num"]),
                "h": int(r["value_num2"]), "raw": r["value_raw"]}
    key = (curation.load("columns").get("columns") or {}).get(col, {}).get("norm_key")
    if not key:
        return none
    r = I.pick_spec(mid, key)
    if not r:
        return none
    raw = r["value_raw"] or ""
    if key in ("panel_type", "os", "cpu", "energy_grade", "release_ym", "power_consumption"):
        return {"display": raw or "—", "raw": raw, "value": r["value_num"], "unit": r["value_unit"]}
    unit = r["value_unit"] or ""
    if r["value_num"] is None:
        return {"display": raw or "—", "raw": raw}
    return {"display": f"{fmt_num(r['value_num'])} {unit}".strip(), "value": r["value_num"], "unit": unit or None, "raw": raw}


def column_profile(cat_id: str | None) -> dict[str, Any]:
    I = idx()
    cfg = curation.load("columns")
    l1 = I.l1_of(cat_id) if cat_id else None
    l2 = I.l2_of(cat_id) if cat_id else None
    profiles = cfg.get("profiles") or []
    for p in profiles:
        if p.get("l2") and l2 in p["l2"]:
            return p
    for p in profiles:
        if p.get("l1") and l1 in p["l1"]:
            return p
    return profiles[-1]


def columns_of(profile: dict[str, Any]) -> list[dict[str, str]]:
    defs = curation.load("columns").get("columns") or {}
    return [{"key": k, "label": defs.get(k, {}).get("label", k)} for k in profile["columns"]]


# ── 분류 ─────────────────────────────────────────────────

def categories(parent_id: str | None) -> list[dict[str, Any]]:
    I = idx()
    ids = I.cat_children.get(parent_id or None, []) if parent_id else I.cat_children.get(None, [])
    out = []
    for n, cid in enumerate(ids):
        c = I.cats[cid]
        fc = len(I.cat_fams.get(cid, set()))
        kids = bool(I.cat_children.get(cid))
        out.append({"id": cid, "name": c["name_ko"] or cid, "level": c["level"], "parent_id": c["parent_id"], "order": n + 1,
                    "has_children": kids or (c["level"] >= 2 and fc > 0), "family_count": fc})
    return out


def family_ids(category_id: str) -> list[str]:
    I = idx()
    fids = I.cat_fams.get(category_id, set())
    return sorted(fids, key=lambda f: (I.is_bundle(f), I.fams[f]["name_ko"] or "", f))


def gallery_thumb(fid: str) -> dict[str, Any] | None:
    g = idx().gallery.get(fid)
    if not g:
        return None
    return imagecards.card(g[0], prefer_page_type="pdp_gallery")


def family_item(fid: str) -> dict[str, Any]:
    I = idx()
    f = I.fams[fid]
    sub = I.fam_subcat(fid)
    return {"id": fid, "name": (f["name_ko"] or fid).strip(), "series_label": I.series_label(fid),
            "model_count": len(I.fam_models.get(fid, [])),
            "subcategory": {"id": sub, "name": I.cat_name(sub) or sub} if sub else None,
            "is_bundle": I.is_bundle(fid), "detail_url": f["detail_url"], "thumb": gallery_thumb(fid),
            "series_code": I.series_code(fid), "sale_status_code": f["sale_status_code"]}


def model_row(mid: str, cols: list[str], thumb_cache: dict[str, Any] | None = None) -> dict[str, Any]:
    I = idx()
    m = I.models[mid]
    fid = m["family_id"]
    name, basis = I.display_name(mid)
    if thumb_cache is not None:
        if fid not in thumb_cache:
            thumb_cache[fid] = gallery_thumb(fid)
        thumb = thumb_cache[fid]
    else:
        thumb = gallery_thumb(fid)
    return {"id": mid, "model_code": m["model_code"], "display_name": name, "display_name_basis": basis,
            "family": {"id": fid, "name": (I.fams[fid]["name_ko"] or fid).strip(), "series_label": I.series_label(fid)},
            "values": {c: _value(mid, c) for c in cols}, "thumb": thumb, "is_family_default": bool(m["is_family_default"])}


def sort_models(mids: list[str], by_family_order: list[str] | None = None) -> list[str]:
    I = idx()
    forder = {f: i for i, f in enumerate(by_family_order or [])}

    def key(mid: str) -> tuple:
        m = I.models[mid]
        inch = I.inch(mid)
        return (forder.get(m["family_id"], 10**6), m["family_id"], inch if inch is not None else 10**6, m["model_code"])

    return sorted(mids, key=key)


def models_for(family_id: str | None, category_id: str | None, text: str | None) -> tuple[list[str], str | None]:
    """(정렬된 모델 id, 열 프로필을 정할 분류)."""
    I = idx()
    if family_id:
        mids = list(I.fam_models.get(family_id, []))
        cat = I.fam_l2(family_id)
        mids = sort_models(mids)
    elif category_id:
        fids = family_ids(category_id)
        mids = [m for f in fids for m in I.fam_models.get(f, [])]
        mids = sort_models(mids, fids)
        cat = category_id
    else:
        mids, cat = [], None
    if text and text.strip():
        hits = search_models(text)
        if family_id or category_id:
            allowed = set(mids)
            mids = [m for m in hits if m in allowed]
        else:
            mids = hits
            if mids:
                cat = I.fam_l2(I.models[mids[0]]["family_id"])
    return mids, cat


# ── 검색 ─────────────────────────────────────────────────

def _sale_rank(fid: str) -> int:
    f = idx().fams[fid]
    return 0 if f["sale_status_code"] == "17" else 1


def _newer(fid: str) -> str:
    """같은 점수 · 판매 상태면 최근 등록 먼저(정렬 키: 등록 시각 역순 문자열)."""
    ts = idx().fams[fid]["registered_at"] or "0"
    return f"{10**15 - int(ts) if ts.isdigit() else 10**15:016d}"


def search_models(text: str) -> list[str]:
    """제품 탐색 표 검색: 모델코드 일부 · 표시명 · 시리즈 코드 · 제품군 이름(00-shell §5.3.3)."""
    I = idx()
    t = norm(text)
    if not t:
        return []
    scored: dict[str, float] = {}
    fam_hit: dict[str, float] = {}
    for fid, f in I.fams.items():
        names = [norm(f["name_ko"]), norm(f["marketing_model"]), norm(f["grp_path"])]
        if t in names:
            fam_hit[fid] = 90
        elif any(t in n for n in names if n):
            fam_hit[fid] = 60
    for mid, m in I.models.items():
        code = m["model_code"].lower()
        code_n = norm(m["model_code"])           # / · - 를 뺀 코드(LH012IWCMWS/XU → lh012iwcmwsxu) — 검색어도 norm 이라 맞춰 본다
        dn = I.display_name(mid)[0].lower()
        s = 0.0
        if t == code or t == dn or t == code_n:
            s = 100
        elif code.startswith(t) or dn.startswith(t) or code_n.startswith(t):
            s = 85
        elif t in code or t in code_n:
            s = 75
        if fam_hit.get(m["family_id"]):
            s = max(s, fam_hit[m["family_id"]])
        if s:
            scored[mid] = s
    return sorted(scored, key=lambda mid: (-scored[mid], _sale_rank(I.models[mid]["family_id"]),
                                           I.models[mid]["family_id"], I.inch(mid) or 10**6, I.models[mid]["model_code"]))


def _highlight(display: str, text: str) -> list[list[int]]:
    out: list[list[int]] = []
    low = display.lower()
    for tok in [text.strip()] + text.split():
        tok = tok.strip().lower()
        if not tok:
            continue
        i = low.find(tok)
        if i >= 0:
            out.append([i, i + len(tok)])
            if tok == text.strip().lower():
                break
    # 겹침 합치기
    out.sort()
    merged: list[list[int]] = []
    for a, b in out:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def _meta_line(fid: str, mids: list[str]) -> str:
    I = idx()
    parts = []
    l2 = I.fam_l2(fid)
    if l2:
        parts.append(I.cat_name(l2) or l2)
    inches = sorted({i for i in (I.inch(m) for m in mids) if i is not None})
    if inches:
        parts.append(" / ".join(f'{i}"' for i in inches))
    labels = []
    for m in mids:
        r = I.pick_spec(m, "resolution")
        if r and r["value_num"] and r["value_num2"]:
            lab = res_label(r["value_num"], r["value_num2"])
            if lab and lab not in labels:
                labels.append(lab)
    if labels:
        parts.append(" / ".join(labels[:2]))
    return " · ".join(parts)


def _category_path(fid: str) -> list[str]:
    I = idx()
    l2 = I.fam_l2(fid)
    out = []
    l1 = I.l1_of(l2)
    if l1:
        out.append(I.cat_name(l1) or l1)
    if l2:
        out.append(I.cat_name(l2) or l2)
    sub = I.fam_subcat(fid)
    if sub:
        out.append(I.cat_name(sub) or sub)
    return out


def label_en(mid: str) -> str | None:
    I = idx()
    m = I.models[mid]
    en = (curation.load("display").get("series_en") or {}).get(I.fam_l2(m["family_id"]) or "")
    name, basis = I.display_name(mid)
    return f"{en} {name}" if en and basis == "code_rule" else None


def product_search(text: str, limit: int = 5, kinds: list[str] | None = None) -> list[dict[str, Any]]:
    """00-shell §7.2.5: 별칭 정확 · 부분 일치(모델코드 · marketing_model · grp_path · 이름) → entity_fts(trigram) → 벡터."""
    I = idx()
    kinds = kinds or ["model", "family"]
    t = norm(text)
    if not t:
        return []
    fam_score: dict[str, float] = {}
    mod_score: dict[str, float] = {}
    by, _, _ = kb().alias_index()
    for kind, ident in by.get(t, set()):
        if kind == "family" and ident in I.fams:
            fam_score[ident] = max(fam_score.get(ident, 0), 100)
        elif kind == "model" and ident in I.models:
            mod_score[ident] = max(mod_score.get(ident, 0), 100)
    for fid, f in I.fams.items():
        names = [norm(f["name_ko"]), norm(f["marketing_model"]), norm(f["grp_path"])]
        if fid in fam_score:
            continue
        if any(n == t for n in names if n):
            fam_score[fid] = 95
        elif any(n.startswith(t) for n in names if n):
            fam_score[fid] = 80
        elif any(t in n for n in names if n):
            fam_score[fid] = 70
    for mid, m in I.models.items():
        if mid in mod_score:
            continue
        code = m["model_code"].lower()
        code_n = norm(m["model_code"])
        dn = I.display_name(mid)[0].lower()
        if t == dn or t == code_n:
            mod_score[mid] = 98
        elif code.startswith(t) or dn.startswith(t) or code_n.startswith(t):
            mod_score[mid] = 88 if len(t) >= 4 else 60
        elif len(t) >= 4 and (t in code or t in code_n):
            mod_score[mid] = 75
    if not fam_score and not mod_score and len(t) >= 2:
        # entity_fts(trigram) → 벡터(유사도 문턱 0.35) 순서로 제품군만 보탠다
        fq = kb().fts_query(text)
        if fq:
            try:
                rows = q("SELECT id FROM entity_fts WHERE entity_fts MATCH ? AND kind='family' ORDER BY bm25(entity_fts, 5.0, 1.0) LIMIT 20", (fq,))
            except Exception:  # noqa: BLE001
                rows = []
            for r, row in enumerate(rows):
                if row["id"] in I.fams:
                    fam_score.setdefault(row["id"], 50 - r)
        if not fam_score:
            # 벡터는 순서만 돕는다: 검색어 토큰(2자 이상)이 엔티티 문서에 실제로 있는 제품군만(‘zzzz’ 같은 잡음 차단)
            toks = [x for x in kb().query_tokens(text) if len(x) >= 2]
            cands = [(ref.split(":")[2], s) for ref, s in kb().vec_search(text, "entity", 40)
                     if ref.count(":") == 2 and ref.split(":")[1] == "family" and s >= 0.35]
            if toks and cands:
                ph = ",".join("?" * len(cands))
                docs = {r["id"]: (r["name"] or "") + " " + (r["text"] or "")
                        for r in q(f"SELECT id, name, text FROM entity_doc WHERE kind='family' AND id IN ({ph})", [c for c, _ in cands])}
                for fid, s in cands:
                    body = docs.get(fid, "").lower()
                    if fid in I.fams and any(t.lower() in body for t in toks):
                        fam_score.setdefault(fid, 30 * s)
    items: list[tuple[float, int, int, str, str, dict[str, Any]]] = []
    if "family" in kinds:
        for fid, s in fam_score.items():
            f = I.fams[fid]
            mids = I.fam_models.get(fid, [])
            name = (f["name_ko"] or fid).strip()
            items.append((s, _sale_rank(fid), 1 if I.is_bundle(fid) else 0, _newer(fid), fid, {
                "kind": "family", "id": fid, "display_name": name, "label": name, "model_code": None, "family_id": fid,
                "family_name": name, "category_path": _category_path(fid), "meta_line": _meta_line(fid, mids),
                "thumb_fid": fid, "highlight": _highlight(name, text), "score": round(s, 2)}))
    if "model" in kinds:
        for mid, s in mod_score.items():
            m = I.models[mid]
            fid = m["family_id"]
            name, _ = I.display_name(mid)
            items.append((s, _sale_rank(fid), (1 if I.is_bundle(fid) else 0) * 2 + (0 if m["is_family_default"] else 1), _newer(fid), mid, {
                "kind": "model", "id": mid, "display_name": name, "label": label_en(mid) or name, "model_code": m["model_code"],
                "family_id": fid, "family_name": (I.fams[fid]["name_ko"] or fid).strip(), "category_path": _category_path(fid),
                "meta_line": _meta_line(fid, [mid]), "thumb_fid": fid,
                "highlight": _highlight(name, text) or _highlight(m["model_code"], text), "score": round(s, 2)}))
    items.sort(key=lambda x: (-x[0], x[1], x[2], x[3], x[4]))
    out = []
    for *_, it in items[:limit]:
        it["thumb"] = gallery_thumb(it.pop("thumb_fid"))
        out.append(it)
    return out


# ── 제품 상세 ─────────────────────────────────────────────

def _spec_all(mid: str) -> list[dict[str, Any]]:
    return q("""SELECT id, group_name, attr_name, value_raw, norm_key, value_num, value_num2, value_unit, source_occurrence_id
                FROM spec_value WHERE model_id=? ORDER BY rowid""", (mid,))


def _present(v: str | None) -> bool:
    return bool(v and v.strip() and not NEG_VALUE.match(v.strip()))


def _row_value(rowdef: dict[str, Any], vals: list[str | None], mid: str) -> str | None:
    fmt = rowdef.get("format")
    present = [v for v in vals if v is not None and str(v).strip() != ""]
    if not present:
        return None
    if fmt == "size_inch":
        v = vals[0]
        inch = idx().inch(mid)
        return f"{v} ({inch}형)" if v and inch else v
    if fmt == "unit_from_name":
        v = vals[0]
        m = re.search(r"\(([A-Za-z%]+)\)\s*$", rowdef["attrs"][0][1])
        if v and m and not re.search(r"[A-Za-z%]", v):
            return f"{v} {m.group(1)}"
        return v
    if fmt == "presence_pair":
        names = rowdef.get("names") or []
        if all(v is None or not v.strip() or v.strip() in ("있음", "없음") for v in vals):
            have = [n for n, v in zip(names, vals) if v and v.strip() == "있음"]
            if not have:
                return "없음"
            return " · ".join(have) + " 있음"
    if fmt == "presence_names":
        names = rowdef.get("names") or []
        have = [n for n, v in zip(names, vals) if _present(v)]
        return " · ".join(have) if have else "없음"
    prefixes = rowdef.get("prefixes") or [""] * len(vals)
    parts = [f"{p}{v}" for p, v in zip(prefixes, vals) if v is not None and str(v).strip() != ""]
    return " · ".join(parts)


def spec_block(mid: str, fam_url: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """(spec 블록, 원본 스펙 행). 사이니지 프로필(부록 B)이 절반 이상 맞으면 프로필, 아니면 KB 원래 그룹 · 행 전체."""
    I = idx()
    rows = _spec_all(mid)
    by = {(r["group_name"], r["attr_name"]): r for r in rows}
    l1 = I.fam_l1(I.models[mid]["family_id"])
    cfg = curation.load("spec_profiles")
    for pid, prof in (cfg.get("profiles") or {}).items():
        if prof.get("l1") and l1 not in prof["l1"]:
            continue
        groups, total, hit = [], 0, 0
        for g in prof["groups"]:
            out_rows = []
            for rd in g["rows"]:
                total += 1
                vals = [by.get((a[0], a[1]), {}).get("value_raw") if (a[0], a[1]) in by else None for a in rd["attrs"]]
                v = _row_value(rd, vals, mid)
                if v is None:
                    continue
                hit += 1
                out_rows.append({"label": rd["label"], "value": v,
                                 "attrs": [f"{a[0]} › {a[1]}" for a, x in zip(rd["attrs"], vals) if x is not None]})
            if out_rows:
                groups.append({"name": g["name"], "column": g.get("column"), "rows": out_rows})
        if total and hit / total >= float(prof.get("min_coverage", 0.5)):
            return {"profile": pid, "source_url": fam_url, "groups": groups}, rows
    groups_raw: dict[str, list[dict[str, Any]]] = collections.OrderedDict()
    for r in rows:
        groups_raw.setdefault(r["group_name"] or "기타", []).append(
            {"label": r["attr_name"], "value": r["value_raw"] or "", "attrs": [f"{r['group_name']} › {r['attr_name']}"]})
    return {"profile": None, "source_url": fam_url, "groups": [{"name": k, "column": None, "rows": v} for k, v in groups_raw.items()]}, rows


def key_chips(mid: str, rows: list[dict[str, Any]], profile: str | None) -> list[str]:
    I = idx()
    by = {(r["group_name"], r["attr_name"]): r for r in rows}
    chips: list[str] = []
    cfg = curation.load("spec_profiles").get("key_chips") or {}
    order = cfg.get(profile or "") or cfg.get("default") or []
    for c in order:
        v = None
        if c == "resolution_label":
            r = I.pick_spec(mid, "resolution")
            v = res_label(r["value_num"], r["value_num2"]) if r else None
        elif c == "brightness_raw":
            r = by.get(("디스플레이", "밝기 (Typ)")) or I.pick_spec(mid, "brightness_nit")
            v = r["value_raw"] if r else None
        elif c == "operation_hours_raw":
            r = I.pick_spec(mid, "operation_hours")
            v = r["value_raw"] if r else None
        elif c == "thickness":
            r = by.get(("크기", "제품(가로x높이x깊이)"))
            if r and r["value_raw"]:
                nums = re.findall(r"\d[\d,]*\.?\d*", r["value_raw"])
                if len(nums) >= 3:
                    v = f"두께 {nums[2]} mm"
        elif c == "os_raw":
            r = by.get(("SoC", "운영체제 버전")) or I.pick_spec(mid, "os")
            v = r["value_raw"] if r else None
        elif c == "panel_raw":
            r = I.pick_spec(mid, "panel_type")
            v = r["value_raw"] if r else None
        if v and v not in chips:
            chips.append(v)
    return chips


def facts(mid: str, rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    I = idx()
    by = {(r["group_name"], r["attr_name"]): r for r in rows}
    out = []
    for f in curation.load("spec_profiles").get("facts") or []:
        r = by.get((f["attr"][0], f["attr"][1]))
        if r is None and f.get("norm_key"):
            r = I.pick_spec(mid, f["norm_key"])
        if not r or not r["value_raw"]:
            continue
        v = r["value_raw"].strip()
        if f.get("squeeze_tilde"):
            v = re.sub(r"\s*~\s*", "~", v)
        out.append({"label": f["label"], "value": v})
    return out


def title_line(mid: str) -> str:
    I = idx()
    m = I.models[mid]
    name = (I.fams[m["family_id"]]["name_ko"] or "").strip()
    r = I.pick_spec(mid, "screen_size_cm")
    inch = I.inch(mid)
    if r and r["value_raw"] and inch:
        return f"{name} {r['value_raw']} ({inch}형)"
    if m["option_value"]:
        return f"{name} {m['option_value']}"
    return name


def supported_solutions(fid: str) -> list[dict[str, Any]]:
    """제품 페이지(PDP) 문서에서 해소된 솔루션 언급 + 근거 문장(00-shell §7.2.6)."""
    I = idx()
    goods = I.fams[fid]["goods_id"]
    doc_id = f"doc_pdp_{goods}"
    rows = q("""SELECT m.resolved_id, m.surface, b.text, b.block_type, b.seq FROM mention m LEFT JOIN document_block b ON b.id=m.block_id
                WHERE m.document_id=? AND m.resolved_kind='solution' ORDER BY b.seq""", (doc_id,))
    if not rows:
        return []
    from .solutions import catalog_by_kb

    url = (I.docs.get(doc_id) or {}).get("url") or I.fams[fid]["detail_url"]
    kinds = curation.load("display").get("solution_kind_labels") or {}
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        sid = r["resolved_id"]
        if sid not in I.solutions:
            continue
        text = r["text"] or ""
        sent = _sentence_with(text, r["surface"])
        cur = out.get(sid)
        if cur is None or (not cur["evidence"]["text"] and sent):
            cat = catalog_by_kb().get(sid)
            out[sid] = {"id": cat["id"] if cat else sid, "kb_id": sid, "name": r["surface"],
                        "catalog_name": cat["name"] if cat else None,
                        "kind_label": kinds.get(I.solutions[sid]["kind"] or "", I.solutions[sid]["kind"] or "솔루션"),
                        "evidence": {"text": sent or (text.strip()[:200] if text else ""), "source_url": url}}
    return list(out.values())


def _sentence_with(text: str, surface: str | None) -> str:
    if not text:
        return ""
    lines = [x.strip() for x in re.split(r"\n+", text) if x.strip()]
    sents = [s.strip() for line in lines for s in re.split(r"(?<=[.!?。])\s+", line) if s.strip()]
    if surface:
        for s in sents:
            if surface.lower() in s.lower():
                return s
    return sents[-1] if sents else text.strip()


def model_detail(mid: str, cases_info: dict[str, Any]) -> dict[str, Any]:
    from . import specs

    I = idx()
    m = I.models[mid]
    fid = m["family_id"]
    f = I.fams[fid]
    name, basis = I.display_name(mid)
    l2 = I.fam_l2(fid)
    l1 = I.l1_of(l2)
    path = [{"id": c, "name": I.cat_name(c) or c} for c in (l1, l2) if c]
    spec, rows = spec_block(mid, f["detail_url"])
    dims_main, dims_all = specs.model_dims(mid, rows)
    doc_spec = I.docs.get(f"doc_spec_{m['goods_id']}") or I.docs.get(f"doc_spec_{f['goods_id']}")
    doc_pdp = I.docs.get(f"doc_pdp_{f['goods_id']}")
    verified = (doc_spec or doc_pdp or {}).get("fetched_at")
    return {
        "id": mid, "model_code": m["model_code"], "display_name": name, "display_name_basis": basis,
        "family": {"id": fid, "name": (f["name_ko"] or fid).strip(), "series_label": I.series_label(fid), "detail_url": f["detail_url"]},
        "category_path": path, "title_line": title_line(mid), "key_chips": key_chips(mid, rows, spec["profile"]),
        "facts": facts(mid, rows), "supported_solutions": supported_solutions(fid), "spec": spec, "documents": None,
        "verified_at": verified, "counts": {"images": len(I.gallery.get(fid, [])), "cases": cases_info["shown"]},
        "case_corpus": cases_info["corpus"], "label_en": label_en(mid),
        "sale_status_code": f["sale_status_code"], "sold_out_flag": m["sold_out_flag"],
        "warranty": specs.warranty(mid, rows), "dims_mm": dims_main, "dims_all": dims_all, "led": specs.led_info(mid, rows),
        "release_ym": specs.release_ym(mid),
    }


def model_images(mid: str) -> list[dict[str, Any]]:
    """G4 와 같은 조건(시리즈 pdp_gallery ∩ depicts confirmed), PDP 갤러리 순서."""
    I = idx()
    fid = I.models[mid]["family_id"]
    fam_name = (I.fams[fid]["name_ko"] or "").strip()
    doc = f"doc_pdp_{I.fams[fid]['goods_id']}"
    out = []
    for aid in I.gallery.get(fid, []):
        mm = imagecards.meta(aid, prefer_doc=doc, prefer_page_type="pdp_gallery", label_strip=fam_name)
        if mm:
            out.append(mm)
    return out
