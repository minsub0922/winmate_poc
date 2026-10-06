"""스펙 사전 · 여러 모델 나란히 비교 표 · 생애주기 · 배치 규칙(06-spec · 08-birdseye 가 요청한 KB 쪽 데이터).

2026-10-07 추가(docs/requests/kb.md)
- 보증(`warranty`): 스펙 API 원문 행 `품질보증기준` · `품질 보증 기간` · `보증기간`. 연수는 원문에 숫자가 있을 때만 읽는다
  (사이니지 · TV · 모니터는 `소비자분쟁해결기준에 따라 보상` 문구뿐 → years=null, status=statement_only).
- 소비전력(`power`): `소비전력 (Typical)` · `(Max)` · `(On Mode)` … 를 모드별로. LED 는 Max 가 ㎡당(W/㎡) 값이다.
- 치수(`dims_mm`): dims.py(속성 이름의 축 순서 · 단위 → mm).
- LED(`led`): 픽셀 피치 · 한 단위(캐비닛 또는 올인원 화면)의 픽셀 구성 · 그 둘을 곱한 발광 면적 · PDP 원문의 화면 크기 언급.
- 생애주기(`successors`): KB 에 후속 데이터는 없다(DR10). 사이니지 코드 규칙(display.yaml signage_lh)으로 같은 계열 · 같은 크기(LED 는 피치)
  모델을 relation='similar' 로 주고, 스펙 `동일모델의 출시년월` 로 더 최근인지(`newer`)를 단다. 'successor' 는 주지 않는다.
- 배치 규칙: `param_status`(unfilled · draft · approved) · `param_values`(빈칸 null) · 분류 id 로 거르기.
"""
from __future__ import annotations

import collections
import re
from functools import lru_cache
from typing import Any

import yaml

from . import catalog, config, curation, dims
from .engine import q
from .index import first_number, idx, jloads

DIM_RE = re.compile(r"(\d[\d,]*\.?\d*)\s*[x×X*]\s*(\d[\d,]*\.?\d*)(?:\s*[x×X*]\s*(\d[\d,]*\.?\d*))?\s*(mm|cm|m)?", re.I)

SALE_STATUS_NOTE = ("사이트 판매상태코드(saleStatCd) 원값. KB 수집본에는 '17'(589 제품군) · '15'(16 제품군)만 있고 코드표는 KB 에 없다(뜻 미확인). "
                    "두 값 모두 수집 시점(2026-10-04) 사이트 목록에 노출된 상품이라 DR09 기준 판매 중(lifecycle.status=on_sale)으로 본다. "
                    "단종 · 단종 예정을 뜻하는 코드는 수집본에 없다(목록에서 빠진 상품은 수집되지 않음 → lifecycle.status=not_in_catalog).")


def _f(s: str) -> float:
    return float(s.replace(",", ""))


def parse_dimensions(raw: str | None) -> dict[str, Any] | None:
    """'1237.9 x 708.8 x 28.5 mm' → {w, h, d, unit:'mm'}(mm 로 맞춤). 형식이 다르면 null. (예전 derived.dimensions_mm — 축 순서는 보지 않는다)"""
    if not raw:
        return None
    m = DIM_RE.search(raw)
    if not m:
        return None
    unit = (m.group(4) or "mm").lower()
    k = {"mm": 1.0, "cm": 10.0, "m": 1000.0}[unit]
    w, h = _f(m.group(1)) * k, _f(m.group(2)) * k
    d = _f(m.group(3)) * k if m.group(3) else None
    return {"w": round(w, 2), "h": round(h, 2), "d": round(d, 2) if d is not None else None, "unit": "mm", "raw": raw}


def _spec_rows(mid: str) -> list[dict[str, Any]]:
    return q("""SELECT id, group_name, attr_name, value_raw, norm_key, value_num, value_num2, value_unit, source_occurrence_id
                FROM spec_value WHERE model_id=? ORDER BY rowid""", (mid,))


def _occ_doc(occ_id: str | None) -> str | None:
    """occ_<document_id>:<seq> → document_id."""
    if not occ_id or not occ_id.startswith("occ_"):
        return None
    return occ_id[4:].rsplit(":", 1)[0]


def _doc_meta(occ_id: str | None, fallback_url: str | None = None) -> tuple[str | None, str | None]:
    """(원문 URL, 수집 시각)."""
    d = idx().docs.get(_occ_doc(occ_id) or "")
    if not d:
        return fallback_url, None
    return d["url"] or fallback_url, d["fetched_at"]


# ── 치수 ─────────────────────────────────────────────────

def model_dims(mid: str, rows: list[dict[str, Any]] | None = None) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """(대표 치수 dims_mm, 읽힌 치수 행 전부)."""
    got = dims.rows_dims(rows if rows is not None else _spec_rows(mid))
    return dims.primary(got), got


# ── 보증 ─────────────────────────────────────────────────

WARRANTY_ATTR = re.compile(r"보증\s*(기간|기준)")
_W_PERIOD = re.compile(r"(?:품질\s*)?보증\s*기간\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(년|개월)")
_W_BARE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(년|개월)\s*$")
_W_PARTS = re.compile(r"부품\s*보유\s*(?:년한|연한|기간)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*년")
_W_CLAIM = re.compile(r"\d+\s*(년|개월)[^.\n]{0,20}보증|보증[^.\n]{0,20}?\d+\s*(년|개월)")


@lru_cache(maxsize=4)
def _feature_rows(kind: str) -> dict[str, list[dict[str, Any]]]:
    """제품군 → 특장점 행(seq 순). feature_block 에 family_id 색인이 없어 한 번만 훑어 둔다.
    kind: warranty = '보증' 이 든 행 · led = 스마트 LED 사이니지 제품군의 행."""
    if kind == "warranty":
        rows = q("""SELECT family_id, seq, headline, sub, body FROM feature_block
                    WHERE coalesce(headline,'') || ' ' || coalesce(sub,'') || ' ' || coalesce(body,'') LIKE '%보증%' ORDER BY family_id, seq""")
    else:
        I = idx()
        fids = sorted(f for f in I.fams if I.fam_l2(f) == "cat_led-signage")
        ph = ",".join("?" * len(fids)) or "''"
        rows = q(f"SELECT family_id, seq, headline, sub, body FROM feature_block WHERE family_id IN ({ph}) ORDER BY family_id, seq", fids)
    out: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows:
        out[r["family_id"]].append(r)
    return dict(out)


def _warranty_claims(fid: str, limit: int = 3) -> list[dict[str, Any]]:
    """PDP 특장점 원문 중 '보증 + 기간' 문장(부품 · 혜택 문구일 수 있어 연수로 읽지 않는다)."""
    I = idx()
    f = I.fams.get(fid)
    if not f:
        return []
    url = (I.docs.get(f"doc_pdp_{f['goods_id']}") or {}).get("url") or f["detail_url"]
    out: list[dict[str, Any]] = []
    for r in _feature_rows("warranty").get(fid, []):
        for t in (r["headline"], r["sub"], r["body"]):
            if not t or "보증" not in t or not _W_CLAIM.search(t):
                continue
            sent = catalog._sentence_with(t, "보증")
            if sent and all(c["text"] != sent for c in out):
                out.append({"text": sent, "source_url": url})
            if len(out) >= limit:
                return out
    return out


def warranty(mid: str, rows: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """스펙 API 의 보증 행(원문). 없으면 null. 연수는 원문에 '보증기간 : N년' · 'N년'(속성이 '…기간') 이 있을 때만."""
    I = idx()
    m = I.models.get(mid)
    if not m:
        return None
    rows = rows if rows is not None else _spec_rows(mid)
    row = next((r for r in rows if WARRANTY_ATTR.search(r["attr_name"] or "") and (r["value_raw"] or "").strip()), None)
    if row is None:
        return None
    text = row["value_raw"].strip()
    pm = _W_PERIOD.search(text) or (_W_BARE.match(text) if "기간" in (row["attr_name"] or "") else None)
    years = months = None
    if pm:
        n = float(pm.group(1))
        months = round(n * 12) if pm.group(2) == "년" else round(n)
        years = round(months / 12, 2)
    parts = _W_PARTS.search(text)
    f = I.fams[m["family_id"]]
    url, as_of = _doc_meta(row["source_occurrence_id"], f["detail_url"])
    return {"status": "stated" if years is not None else "statement_only", "years": years, "months": months,
            "parts_years": float(parts.group(1)) if parts else None, "text": text,
            "attr": f"{row['group_name'] or ''} › {row['attr_name'] or ''}", "source_ref": row["source_occurrence_id"],
            "source_url": url, "as_of": as_of, "claims": _warranty_claims(m["family_id"])}


# ── 소비전력 ─────────────────────────────────────────────

POWER_ATTR = re.compile(r"소비\s*전력|Power\s*Consumption", re.I)
POWER_MODES: list[tuple[str, re.Pattern[str]]] = [
    ("typical", re.compile(r"\(\s*Typ(?:ical)?\s*\)|Typical", re.I)),
    ("max", re.compile(r"\(\s*Max\s*\)|최대", re.I)),
    ("on", re.compile(r"On\s*Mode", re.I)),
    ("sleep", re.compile(r"Sleep", re.I)),
    ("standby", re.compile(r"Stand-?\s*by|대기", re.I)),
    ("off", re.compile(r"Off\s*Mode", re.I)),
    ("dpms", re.compile(r"DPMS", re.I)),
    ("yearly", re.compile(r"Yearly|연간", re.I)),
    ("rated", re.compile(r"정격")),
    ("average", re.compile(r"평균")),
]


def _power_unit(raw: str) -> tuple[str | None, bool]:
    if re.search(r"kWh\s*/\s*(year|년)", raw, re.I):
        return "kWh/year", False
    if re.search(r"W\s*/\s*(㎡|m2|m²)", raw, re.I):
        return "W/㎡", True
    if re.search(r"kW(?!h)", raw):
        return "kW", False
    if re.search(r"(?<![A-Za-z])W(?![A-Za-z/])", raw):
        return "W", False
    return None, False


def power(mid: str, rows: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """소비전력 행을 모드별로(원문 그대로 + 첫 수 · 단위). typical · max 는 그 모드의 첫 행. 소비전력 행이 없으면 null."""
    rows = rows if rows is not None else _spec_rows(mid)
    vals = []
    for r in rows:
        a = r["attr_name"] or ""
        raw = (r["value_raw"] or "").strip()
        if not raw or not POWER_ATTR.search(a):
            continue
        mode = next((k for k, p in POWER_MODES if p.search(a)), "unspecified")
        unit, per_m2 = _power_unit(raw)
        vals.append({"mode": mode, "value": first_number(raw), "unit": unit, "per_m2": per_m2, "raw": raw,
                     "attr": f"{r['group_name'] or ''} › {a}", "spec_value_id": r["id"]})
    if not vals:
        return None
    def pick(mode: str) -> dict[str, Any] | None:
        return next((v for v in vals if v["mode"] == mode), None)

    return {"typical": pick("typical"), "max": pick("max"), "values": vals}


# ── LED ─────────────────────────────────────────────────

_PX = re.compile(r"(\d{2,5})\s*[x×X]\s*(\d{2,5})")
_SIZE_MENTION = re.compile(r"(최대|최소)?\s*(\d{2,3})\s*(?:인치|형|\"|”|″)")


def led_info(mid: str, rows: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """스마트 LED 사이니지만. 모델코드 숫자(LH012…)는 픽셀 피치 코드라 화면 크기가 아니다(index.inch 참고)."""
    I = idx()
    m = I.models.get(mid)
    if not m or I.fam_l2(m["family_id"]) != "cat_led-signage":
        return None
    rows = rows if rows is not None else _spec_rows(mid)
    pitch, basis = None, None
    for r in rows:
        if r["norm_key"] == "pixel_pitch_mm" and r["value_num"]:
            pitch, basis = float(r["value_num"]), "spec"
            break
        if re.search(r"Pixel\s*Pitch|픽셀\s*피치", r["attr_name"] or "", re.I) and first_number(r["value_raw"]):
            pitch, basis = first_number(r["value_raw"]), "spec"
            break
    if pitch is None and "피치" in (m["option_name"] or "") and first_number(m["option_value"]):
        pitch, basis = first_number(m["option_value"]), "option"
    px = None
    for r in rows:
        if re.search(r"Pixel\s*Configuration|LED\s*구성", r["attr_name"] or "", re.I) and r["value_raw"]:
            mm = _PX.search(r["value_raw"])
            if mm:
                px = {"w": int(mm.group(1)), "h": int(mm.group(2)), "raw": r["value_raw"],
                      "attr": f"{r['group_name'] or ''} › {r['attr_name'] or ''}"}
                break
    area = ({"w": round(px["w"] * pitch, 1), "h": round(px["h"] * pitch, 1), "basis": "unit_pixels × pixel_pitch_mm"}
            if px and pitch else None)
    f = I.fams[m["family_id"]]
    url = (I.docs.get(f"doc_pdp_{f['goods_id']}") or {}).get("url") or f["detail_url"]
    mentions: list[dict[str, Any]] = []
    for r in _feature_rows("led").get(m["family_id"], []):
        for t in (r["headline"], r["sub"], r["body"]):
            for mm in _SIZE_MENTION.finditer(t or ""):
                sent = catalog._sentence_with(t, mm.group(0).strip())
                if not any(x["text"] == sent for x in mentions):
                    mentions.append({"inch": int(mm.group(2)), "qualifier": mm.group(1), "text": sent, "source_url": url})
    return {"pixel_pitch_mm": pitch, "pitch_basis": basis, "unit_pixels": px, "unit_active_mm": area, "size_mentions": mentions,
            "note": "KB 에 화면 구성 옵션(대각 · 가로×세로) 표가 없다. unit_pixels 는 한 단위(캐비닛 또는 올인원 화면)의 픽셀 수, "
                    "unit_active_mm 는 그 픽셀 수 × 픽셀 피치(계산값)다."}


# ── 출시년월 · 같은 계열 모델 ─────────────────────────────

_YM = re.compile(r"(\d{2,4})\s*년\s*(\d{1,2})\s*월|(20\d{2})\s*[.\-/]\s*(\d{1,2})")


def parse_ym(raw: str | None) -> str | None:
    """'2024년 3월' · '26년 3월' · '2024.03' → '2024-03'."""
    m = _YM.search(raw or "")
    if not m:
        return None
    y, mo = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
    yy = int(y)
    if yy < 100:
        yy += 2000
    mon = int(mo)
    if not (2000 <= yy <= 2100 and 1 <= mon <= 12):
        return None
    return f"{yy:04d}-{mon:02d}"


def release_ym(mid: str) -> str | None:
    for r in idx().spec_rows(mid, "release_ym"):
        ym = parse_ym(r["value_raw"])
        if ym:
            return ym
    return None


_SHORT = re.compile(r"^(?P<line>[A-Z]{2})(?P<size>\d{2,3})(?P<gen>[A-Z])$")


def series_key(code: str) -> tuple[str, str, str] | None:
    """(계열 2자, 크기 · 피치 숫자, 세대 1자). display.yaml signage_lh 규칙(LH55QMCE… → QM · 55 · C) 또는 표시명(QM55C)."""
    c = (code or "").strip().upper()
    for rule in curation.load("display").get("display_name_rules") or []:
        mm = re.match(rule["pattern"], c)
        if mm and {"line", "size", "gen"} <= set(mm.groupdict()):
            return mm.group("line"), mm.group("size"), mm.group("gen")
    mm = _SHORT.match(c)
    return (mm.group("line"), mm.group("size"), mm.group("gen")) if mm else None


@lru_cache(maxsize=1)
def _series_groups() -> dict[tuple[str, str], dict[str, list[str]]]:
    """(계열, 크기) → 세대 → KB 모델 id(사이니지 · LED, 표시명 규칙에 맞는 것)."""
    I = idx()
    out: dict[tuple[str, str], dict[str, list[str]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for mid, m in I.models.items():
        if I.fam_l1(m["family_id"]) != "top_display":
            continue
        k = series_key(m["model_code"])
        if k:
            out[(k[0], k[1])][k[2]].append(mid)
    return out


def _gen_release(mids: list[str]) -> str | None:
    yms = [ym for ym in (release_ym(x) for x in mids) if ym]
    return min(yms) if yms else None


def similar_models(ref: str, mid: str | None) -> list[dict[str, Any]]:
    """같은 계열 · 같은 크기(LED 는 피치 코드)의 다른 세대 KB 모델. 원본 세대가 더 최근으로 알려진 후보는 뺀다."""
    I = idx()
    code = I.models[mid]["model_code"] if mid else ref
    key = series_key(code)
    if not key:
        return []
    line, size, gen = key
    groups = _series_groups().get((line, size)) or {}
    src_rel = _gen_release(groups.get(gen, [])) if mid else None
    out = []
    for g, mids in groups.items():
        if g == gen and mid:                       # KB 모델 자신의 세대는 뺀다(KB 에 없는 입력이면 같은 표시명 모델도 후보)
            continue
        rep = min(mids, key=lambda x: (release_ym(x) is None, not I.models[x]["is_family_default"], len(I.models[x]["model_code"]),
                                       I.models[x]["model_code"]))
        rel = _gen_release(mids)
        newer = (rel > src_rel) if (rel and src_rel) else None
        if newer is False:
            continue
        led = I.fam_l2(I.models[rep]["family_id"]) == "cat_led-signage"
        if led:
            opt = I.models[rep]["option_value"] if "피치" in (I.models[rep]["option_name"] or "") else None
            what = f"같은 픽셀 피치 코드({size}{' = ' + opt if opt else ''})"
        else:
            what = f'같은 크기({int(size)}")'
        reason = f"같은 계열({line}) · {what} · " + (f"세대 {gen} → {g}" if g != gen else f"같은 세대({g}) — 입력은 KB 모델코드가 아님")
        if rel:
            reason += f" · 출시 {rel}" + (" (더 최근)" if newer else "")
        out.append({"model_code": I.models[rep]["model_code"], "id": rep, "display_name": I.display_name(rep)[0], "relation": "similar",
                    "reason": reason, "newer": newer, "release_ym": rel,
                    "basis": "code_rule(display.yaml signage_lh) + 스펙 '동일모델의 출시년월'"})
    out.sort(key=lambda x: x["model_code"])
    out.sort(key=lambda x: x["release_ym"] or "", reverse=True)          # 최근 출시 먼저, 출시년월 모름은 뒤
    return out


# ── 스펙 사전 · 표 ────────────────────────────────────────

def attributes(category_id: str | None, text: str | None) -> list[dict[str, Any]]:
    I = idx()
    roots: set[str] | None = None
    if category_id:
        if category_id not in I.cats:
            from winmate_common.errors import not_found

            raise not_found("분류", category_id)
        sub = I.cat_subtree(category_id)
        roots = {c[4:] for c in sub if c.startswith("cat_") and "__" not in c}
        if I.l2_of(category_id):
            roots.add(I.l2_of(category_id)[4:])  # type: ignore[index]
    rows = q("SELECT id, category_root, group_name, attr_name, norm_key, unit, n_values FROM spec_attr_def ORDER BY rowid")
    out = []
    t = (text or "").strip().lower()
    for r in rows:
        if roots is not None and r["category_root"] not in roots:
            continue
        if t and t not in (r["attr_name"] or "").lower() and t not in (r["group_name"] or "").lower() and t != (r["norm_key"] or ""):
            continue
        out.append({"id": r["id"], "category_id": f"cat_{r['category_root']}", "group": r["group_name"], "name": r["attr_name"],
                    "norm_key": r["norm_key"], "unit": r["unit"], "n_values": r["n_values"]})
    return out


def table(refs: list[str], keys: list[str] | None = None, groups: list[str] | None = None) -> dict[str, Any]:
    """모델 여럿의 스펙을 나란히(같은 그룹 › 속성 = 한 행). 값은 value_raw 원문 + 정규 수치 · 단위 · 출처."""
    I = idx()
    models, unresolved = [], []
    for ref in refs:
        mid = I.resolve_model(ref)
        if not mid:
            unresolved.append(ref)
            continue
        if any(m["id"] == mid for m in models):
            continue
        m = I.models[mid]
        name, basis = I.display_name(mid)
        f = I.fams[m["family_id"]]
        models.append({"ref": ref, "id": mid, "model_code": m["model_code"], "display_name": name, "display_name_basis": basis,
                       "family_id": m["family_id"], "family_name": f["name_ko"], "series_label": I.series_label(m["family_id"]),
                       "category_id": I.fam_l2(m["family_id"]), "has_spec": mid in I.models_with_spec,
                       "source_url": f["detail_url"], "label_en": catalog.label_en(mid)})
    rows: "collections.OrderedDict[tuple[str, str], dict[str, Any]]" = collections.OrderedDict()
    derived: dict[str, dict[str, Any]] = {}
    for m in models:
        mid = m["id"]
        url = m["source_url"]
        allrows = _spec_rows(mid)
        for r in allrows:
            if keys and r["norm_key"] not in keys:
                continue
            if groups and r["group_name"] not in groups:
                continue
            key = (r["group_name"] or "", r["attr_name"] or "")
            row = rows.setdefault(key, {"group": key[0], "attr_name": key[1], "norm_key": r["norm_key"], "values": {}})
            if row["norm_key"] is None and r["norm_key"]:
                row["norm_key"] = r["norm_key"]
            row["values"][m["model_code"]] = {"raw": r["value_raw"], "num": r["value_num"], "num2": r["value_num2"],
                                               "unit": r["value_unit"], "spec_value_id": r["id"],
                                               "source": r["source_occurrence_id"], "source_url": url}
        legacy = None
        for r in allrows:
            if r["value_raw"] and re.search(r"제품.*(가로|W)", r["attr_name"] or "") and not re.search(r"포장|박스", r["attr_name"] or ""):
                legacy = parse_dimensions(r["value_raw"])
                if legacy:
                    break
        bright = I.pick_spec(mid, "brightness_nit")
        wset = next((r for r in I.spec_rows(mid, "weight_kg") if r["attr_name"] in ("제품 무게", "무게", "본체 무게")), None)
        wpkg = next((r for r in I.spec_rows(mid, "weight_kg") if "포장" in (r["attr_name"] or "") or "박스" in (r["attr_name"] or "")), None)
        derived[m["model_code"]] = {
            "screen_size_cm": I.screen_cm(mid), "screen_size_inch": I.inch(mid),
            "dimensions_mm": legacy,
            "dims_mm": model_dims(mid, allrows)[0],
            "brightness_typ_nit": first_number(bright["value_raw"]) if bright else None,
            "weight_kg_set": wset["value_num"] if wset else None,
            "weight_kg_package": wpkg["value_num"] if wpkg else None,
            "resolution": ({"w": int(r["value_num"]), "h": int(r["value_num2"]), "label": catalog.res_label(r["value_num"], r["value_num2"])}
                           if (r := I.pick_spec(mid, "resolution")) and r["value_num"] and r["value_num2"] else None),
            "option": {"name": I.models[mid]["option_name"], "value": I.models[mid]["option_value"]},
            "power": power(mid, allrows),
            "warranty": warranty(mid, allrows),
        }
    return {"models": models, "unresolved": unresolved, "rows": list(rows.values()), "derived": derived,
            "catalog_version": (idx().meta.get("products_fetched_at") or "")[:7] or None,
            "notes": ["값은 KB value_raw 원문(T2 공식 스펙 API)", "derived 는 원문에서 계산한 값(크기 인치 = 00-shell §9.2 규칙)",
                      "brightness_typ_nit = '밝기 (Typ)' 원문의 첫 수(KB value_num 은 Peak 일 수 있음)",
                      "dims_mm = 속성 이름의 축 순서로 읽은 본체 치수(mm) · dimensions_mm 은 예전 값(첫 'AxBxC' 를 가로×높이×깊이로 봄)",
                      "power = 소비전력 행 모드별(LED 의 Max 는 W/㎡) · warranty = 스펙 보증 행 원문(연수는 원문에 숫자가 있을 때만)"]}


# ── 생애주기 ─────────────────────────────────────────────

LIFECYCLE_GAPS = [
    "DR10 단종 · 후속 대응표 없음(KB) — successor 는 항상 null, successors 는 코드 규칙 · 출시년월로 찾은 같은 계열 모델(relation=similar)",
    "보증 연수: 스펙 원문에 숫자가 있을 때만(프린터 1년 · LED 조명 2년 등). 사이니지 · TV · 모니터는 '소비자분쟁해결기준에 따라 보상' 문구뿐 → warranty.years=null",
    "sale_status_code 뜻 미확인(코드표 없음) — 원값만 준다(15 · 17 모두 사이트 목록 노출 상품)",
]


def lifecycle(ref: str) -> dict[str, Any]:
    """KB 생애주기: 사이트 목록에 있으면 판매 중으로 본다(DR09). 단종 · 후속(DR10, C5)은 KB 에 없다."""
    I = idx()
    mid = I.resolve_model(ref)
    if not mid:
        return {"ref": ref, "model_code": None, "status": "not_in_catalog", "sale_status_code": None, "sold_out_flag": None,
                "successor": None, "successors": similar_models(ref, None), "release_ym": None, "warranty": None,
                "basis": "KB(samsung.com 수집)에 없는 모델 — 단종이거나 아직 등록되지 않았을 수 있음", "gaps": LIFECYCLE_GAPS}
    m = I.models[mid]
    f = I.fams[m["family_id"]]
    return {"ref": ref, "model_code": m["model_code"], "id": mid, "status": "on_sale", "sale_status_code": f["sale_status_code"],
            "sold_out_flag": m["sold_out_flag"], "successor": None, "successors": similar_models(ref, mid),
            "release_ym": release_ym(mid), "warranty": warranty(mid),
            "basis": "DR09: 사이트 목록 노출 = 판매 중으로 간주(KB 2026-10-04 수집)", "gaps": LIFECYCLE_GAPS}


# ── 배치 규칙 ─────────────────────────────────────────────

_FILL = re.compile(r"^<<\s*FILL\s*:?\s*(.*?)\s*>>$", re.S)


@lru_cache(maxsize=1)
def _seed_rules() -> dict[str, dict[str, Any]]:
    """winmate-kb/seed/ontology/placement_rules.yaml(설명 문구). 없으면 빈 dict."""
    p = config.wkb_root() / "seed" / "ontology" / "placement_rules.yaml"
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return {r["id"]: r for r in data.get("placement_rules") or [] if isinstance(r, dict) and r.get("id")}


@lru_cache(maxsize=1)
def _seed_category_map() -> dict[str, set[str]]:
    """시드 분류 코드(signage · hvac_system_ac …) → KB 분류 id. 시드 categories.yaml 의 목록 URL(/<slug>/all-<slug>/)로 잇는다."""
    I = idx()
    p = config.wkb_root() / "seed" / "ontology" / "categories.yaml"
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    out: dict[str, set[str]] = {}

    def walk(node: dict[str, Any]) -> set[str]:
        ids: set[str] = set()
        mm = re.search(r"/sec/business/([^/]+)/all-\1/", node.get("url") or "")
        if mm and f"cat_{mm.group(1)}" in I.cats:
            ids.add(f"cat_{mm.group(1)}")
        for ch in node.get("children") or []:
            if isinstance(ch, dict):
                ids |= walk(ch)
        if node.get("code"):
            out[node["code"]] = ids
        return ids

    for n in data.get("categories") or []:
        if isinstance(n, dict):
            walk(n)
    return out


def _cat_family(cid: str) -> set[str]:
    """KB 분류 id 와 그 위 · 아래 분류(L1 을 주면 아래 L2 전부, L3 를 주면 위 L2 까지)."""
    I = idx()
    out = set(I.cat_subtree(cid))
    cur, n = cid, 0
    while cur and cur in I.cats and n < 6:
        out.add(cur)
        cur = I.cats[cur]["parent_id"]
        n += 1
    return out


def placement_rules(category: str | None, space: str | None) -> list[dict[str, Any]]:
    """category: 시드 코드(signage …) · KB 분류 id(cat_smart-signage · top_display · cat_smart-signage__videowall) 모두 받는다."""
    I = idx()
    cmap = _seed_category_map()
    want: set[str] | None = None
    if category and category in I.cats:
        want = _cat_family(category)
    elif category and category in cmap:
        want = cmap[category]                       # signage_lcd → cat_smart-signage(시드 하위 코드도 상위 규칙에 맞춘다)
    seeds = _seed_rules()
    out = []
    for r in q("SELECT * FROM placement_rule ORDER BY rowid"):
        rule_cats = cmap.get(r["category"] or "", set())
        if category and r["category"] != "*" and r["category"] != category and not (want and rule_cats & want):
            continue
        if space and r["space"] not in (space, "*"):
            continue
        params = jloads(r["params_json"], {}) or {}
        values: dict[str, Any] = {}
        missing: list[str] = []
        notes: dict[str, str] = {}
        for k, v in params.items():
            fm = _FILL.match(v.strip()) if isinstance(v, str) else None
            if fm:
                values[k] = None
                missing.append(k)
                if fm.group(1):
                    notes[k] = fm.group(1)
            else:
                values[k] = v
        filled = not missing
        approved = filled and r["status"] in ("active", "approved")
        out.append({"id": r["id"], "kind": r["kind"], "space": r["space"], "category": r["category"], "expression": r["expression"],
                    "params": params, "status": r["status"], "active": r["status"] == "active" and filled,
                    "param_status": "approved" if approved else ("draft" if filled else "unfilled"),
                    "param_values": values, "missing_params": missing, "param_notes": notes,
                    "explanation_ko": (seeds.get(r["id"]) or {}).get("explanation_ko"),
                    "category_ids": sorted(rule_cats) if r["category"] != "*" else [],
                    "source_tier": "T5_seed_draft" if r["status"] != "active" else "T4_expert"})
    return out


def placement_note(items: list[dict[str, Any]]) -> str:
    n_ok = sum(1 for r in items if r["param_status"] == "approved")
    if n_ok:
        return f"승인된 규칙 {n_ok}개(param_status=approved) — 그 params 로 엔진 기본값을 덮어쓰세요"
    return ("KB v1 의 배치 규칙은 모두 초안(계수 <<FILL>>, param_status=unfilled) — 엔진 기본값을 그대로 쓰세요. "
            "param_status=approved 인 규칙만 params(param_values)로 덮어쓰세요")
