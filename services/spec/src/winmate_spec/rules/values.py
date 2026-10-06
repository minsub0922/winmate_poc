"""셀 값 — 카탈로그 원천 → 정규 값(언어 · 단위와 무관) → 표시(언어 · 단위 · 숫자 형식).

정규 값(row_key 별 dict, 값이 없는 부분은 None):
  size_resolution     {inch, w, h}
  brightness_contrast {nit, ca, cb}
  operation_hours     {text, hours}
  power               {typ, max}
  player_os           {os, builtin}
  magicinfo           {supported}
  warranty            {years}
  io_ports            {hdmi, dp, usb, rs232_in, rs232_out, rj45, wifi, bt}
  dimensions          {w, h, d}           (mm)
  weight              {set, pkg}          (kg)
  bezel               {mm, tail}
  certification       {kc, safety, emc}
  accessories         {mount, stand}
  derived:annual_energy_cost {kwh, krw, hours, price}
  template:* · 자유 입력 {text}
값은 모두 출처 레코드(카탈로그 행 · 데이터시트 행 · 정책 문서 · 사용자 입력 · 파생 계산)에서만 온다(§7.11-1).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from .fmt import (
    PENDING_EN, PENDING_KO, fmt_num, grade_label, inch_from_cm, inch_from_code, kg_to_lb, mm_to_in, numbers, parse_resolution,
)

NUMERIC_ROWS = {"size_resolution", "brightness_contrast", "operation_hours", "power", "warranty", "dimensions", "weight", "bezel"}
CONVERTIBLE_LENGTH = {"dimensions", "bezel"}
CONVERTIBLE_WEIGHT = {"weight"}
# 차이 계산에서 빼는 식별 코드(KC 번호 · 액세서리 모델명) — §4.7.2
DIFF_EXCLUDED = {"certification", "accessories"}


# ── 모델 스펙(어댑터가 만든 dict) 읽기 ────────────────────

def attr(spec: dict[str, Any], group: str, name: str) -> dict[str, Any] | None:
    a = (spec.get("attrs") or {}).get(f"{group} › {name}")
    if a and (a.get("raw") or "").strip() not in ("", "-", "—"):
        return a
    return None


def attr_like(spec: dict[str, Any], group: str | None, pattern: str) -> list[tuple[str, dict[str, Any]]]:
    rx = re.compile(pattern, re.I)
    out = []
    for key, a in (spec.get("attrs") or {}).items():
        g, _, n = key.partition(" › ")
        if group and g != group:
            continue
        if rx.search(n) and (a.get("raw") or "").strip() not in ("", "-", "—"):
            out.append((n, a))
    return out


def raw(spec: dict[str, Any], group: str, name: str) -> str | None:
    a = attr(spec, group, name)
    return a.get("raw").strip() if a else None


def is_none_value(s: str | None) -> bool:
    return (s or "").strip() in ("없음", "No", "N/A", "-", "미지원", "Not supported")


@dataclass
class Candidate:
    """칸 하나에 대한 한 출처의 값."""
    value: dict[str, Any] | None
    sources: list[dict[str, Any]] = field(default_factory=list)
    alt_measures: list[dict[str, str]] = field(default_factory=list)
    kind: str = "catalog"          # catalog · datasheet · policy_doc · user · derived
    label: str = "카탈로그"

    def complete(self, row_key: str) -> bool:
        return is_complete(row_key, self.value)


def catalog_source(spec: dict[str, Any], a: dict[str, Any] | None, *, version: str, quote: str | None = None) -> dict[str, Any]:
    return {"kind": "catalog", "label": "사내 제품 카탈로그", "version_or_date": version, "tier": "T2",
            "ref": (a or {}).get("id") or spec.get("model_code") or "", "quote": quote or (a or {}).get("raw"),
            "url": spec.get("source_url")}


# ── 칸 값 고르기(§4.15.4 속성 이름으로 고름) ───────────────

_TYP = re.compile(r"Typical|Typ\b|Typ\.|일반|정격", re.I)
_MAX = re.compile(r"\bMax\b|최대", re.I)
_ALT = re.compile(r"On Mode|Sleep Mode|Stand-?by|대기", re.I)


def catalog_candidate(row_key: str, spec: dict[str, Any], version: str) -> Candidate:
    """카탈로그(KB) 모델 스펙 → 이 행의 후보 값(없으면 value=None 또는 부분 None)."""
    d = spec.get("derived") or {}
    src: list[dict[str, Any]] = []

    def add(a: dict[str, Any] | None) -> None:
        if a:
            src.append(catalog_source(spec, a, version=version))

    if row_key == "size_resolution":
        a_cm = attr(spec, "디스플레이", "대각선 사이즈 (cm)")
        a_res = attr(spec, "디스플레이", "해상도")
        inch = d.get("screen_size_inch") or inch_from_code(spec.get("model_code")) or inch_from_cm((a_cm or {}).get("num"))
        res = (d.get("resolution") or {})
        w, h = res.get("w"), res.get("h")
        if not w and a_res:
            pr = parse_resolution(a_res.get("raw"))
            w, h = pr if pr else (None, None)
        add(a_cm)
        add(a_res)
        if inch is None and w is None:
            return Candidate(None, src)
        return Candidate({"inch": inch, "w": w, "h": h}, src)

    if row_key == "brightness_contrast":
        a_b = attr(spec, "디스플레이", "밝기 (Typ)") or attr(spec, "디스플레이", "밝기")
        a_c = attr(spec, "디스플레이", "명암비")
        nit = d.get("brightness_typ_nit")
        if nit is None and a_b:
            nit = (numbers(a_b.get("raw")) or [None])[0]
        ca = cb = None
        if a_c:
            m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*:\s*(\d[\d,]*(?:\.\d+)?)", a_c.get("raw") or "")
            if m:
                ca, cb = float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))
        add(a_b)
        add(a_c)
        if nit is None and ca is None:
            return Candidate(None, src)
        return Candidate({"nit": nit, "ca": ca, "cb": cb}, src)

    if row_key == "operation_hours":
        a = attr(spec, "디스플레이", "제품 사용 시간")
        if not a:
            return Candidate(None, src)
        add(a)
        text = a["raw"].strip()
        hours = a.get("num") or (numbers(text) or [None])[0]
        return Candidate({"text": text, "hours": hours}, src)

    if row_key == "power":
        typ = mx = None
        alts: list[dict[str, str]] = []
        for name, a in attr_like(spec, "전원", r"소비전력"):
            num = a.get("num") if a.get("num") is not None else (numbers(a.get("raw")) or [None])[0]
            if _ALT.search(name):
                label = re.sub(r"^.*\(([^)]*)\).*$", r"\1", name).strip() or name
                alts.append({"label": label, "value_text": f"{fmt_num(num)} W" if num is not None else a["raw"],
                             "footnote": f"{label} 기준", "num": num, "ref": a.get("id")})
                continue
            if _MAX.search(name) and mx is None:
                mx = num
                add(a)
            elif _TYP.search(name) and typ is None:
                typ = num
                add(a)
        if typ is None and mx is None:
            return Candidate(None, src, alt_measures=alts)
        return Candidate({"typ": typ, "max": mx}, src, alt_measures=alts)

    if row_key == "player_os":
        a = attr(spec, "SoC", "운영체제 버전") or (attr_like(spec, None, r"운영체제|OS 버전") or [(None, None)])[0][1]
        if not a:
            return Candidate(None, src)
        add(a)
        has_soc = any(k.startswith("SoC ›") for k in (spec.get("attrs") or {}))
        return Candidate({"os": a["raw"].strip(), "builtin": bool(has_soc)}, src)

    if row_key == "magicinfo":
        for sol in spec.get("solutions") or []:
            if "magicinfo" in (sol.get("id") or "").lower() or "magicinfo" in (sol.get("name") or "").lower():
                src.append({"kind": "catalog", "label": "사내 제품 카탈로그", "version_or_date": version, "tier": "T2",
                            "ref": sol.get("kb_id") or sol.get("id") or "", "quote": sol.get("evidence_text"),
                            "url": sol.get("source_url")})
                return Candidate({"supported": True}, src)
        for p in spec.get("provides") or []:
            if p.get("capability_id") == "cap_remote_content_mgmt" and "magicinfo" in (p.get("evidence") or "").lower():
                src.append({"kind": "catalog", "label": "사내 제품 카탈로그", "version_or_date": version, "tier": "T2",
                            "ref": p.get("capability_id"), "quote": p.get("evidence")})
                return Candidate({"supported": True}, src)
        a = (attr_like(spec, None, r"MagicINFO") or [(None, None)])[0][1]
        if a and is_none_value(a.get("raw")):
            add(a)
            return Candidate({"supported": False}, src)
        return Candidate(None, src)

    if row_key == "warranty":
        # KB 에는 보증 연수가 없다 — 어댑터가 따로 넣은 값(fixture · internal)만
        w = spec.get("warranty_catalog")
        if w and w.get("years") is not None:
            return Candidate({"years": w["years"]}, [{"kind": "catalog", "label": "사내 제품 카탈로그", "version_or_date": version,
                                                      "tier": "T2", "ref": w.get("ref") or spec.get("model_code") or "",
                                                      "quote": w.get("quote")}])
        return Candidate(None, src)

    if row_key == "io_ports":
        g = "연결성"
        v: dict[str, Any] = {}
        for key, name in (("hdmi", "HDMI 입력"), ("dp", "DP 입력"), ("usb", "USB")):
            a = attr(spec, g, name)
            if a:
                add(a)
                v[key] = None if is_none_value(a["raw"]) else a["raw"].strip()
        for key, name in (("rs232_in", "RS232 입력"), ("rs232_out", "RS232 출력"), ("rj45", "RJ45 입력"), ("wifi", "WiFi"), ("bt", "Bluetooth")):
            a = attr(spec, g, name)
            if a:
                add(a)
                v[key] = not is_none_value(a["raw"])
        if not v:
            return Candidate(None, src)
        return Candidate(v, src)

    if row_key == "dimensions":
        dm = d.get("dimensions_mm")
        a = attr(spec, "크기", "제품(가로x높이x깊이)")
        add(a)
        if dm:
            return Candidate({"w": dm.get("w"), "h": dm.get("h"), "d": dm.get("d")}, src)
        if a:
            ns = numbers(a["raw"])
            if len(ns) >= 2:
                return Candidate({"w": ns[0], "h": ns[1], "d": ns[2] if len(ns) > 2 else None}, src)
        return Candidate(None, src)

    if row_key == "weight":
        a_set = attr(spec, "무게", "제품 무게")
        a_pkg = attr(spec, "무게", "무게 (박스 포장)")
        add(a_set)
        add(a_pkg)
        s = d.get("weight_kg_set") if d.get("weight_kg_set") is not None else (a_set or {}).get("num")
        p = d.get("weight_kg_package") if d.get("weight_kg_package") is not None else (a_pkg or {}).get("num")
        if s is None and p is None:
            return Candidate(None, src)
        return Candidate({"set": s, "pkg": p}, src)

    if row_key == "bezel":
        a = attr(spec, "기구사양", "베젤 두께")
        if not a:
            return Candidate(None, src)
        add(a)
        m = re.match(r"\s*(\d+(?:\.\d+)?)\s*mm\s*(.*)$", a["raw"], re.I)
        if m:
            return Candidate({"mm": float(m.group(1)), "tail": m.group(2).strip() or None}, src)
        return Candidate({"text": a["raw"].strip()}, src)

    if row_key == "certification":
        kc = attr(spec, "상품 기본정보", "KC 인증 필 유무")
        sa = attr(spec, "인증정보", "안전 규격")
        emc = attr(spec, "인증정보", "EMC")
        for a in (kc, sa, emc):
            add(a)
        v = {"kc": kc["raw"].strip() if kc else None, "safety": sa["raw"].strip() if sa else None, "emc": emc["raw"].strip() if emc else None}
        if not any(v.values()):
            return Candidate(None, src)
        return Candidate(v, src)

    if row_key == "accessories":
        mo = attr(spec, "추가 기능", "마운트")
        st = attr(spec, "추가 기능", "스탠드")
        add(mo)
        add(st)
        v = {"mount": mo["raw"].strip() if mo and not is_none_value(mo["raw"]) else None,
             "stand": st["raw"].strip() if st and not is_none_value(st["raw"]) else None}
        if not any(v.values()):
            return Candidate(None, src)
        return Candidate(v, src)

    return Candidate(None, src)


REQUIRED_PARTS = {
    "size_resolution": ("inch", "w"),
    "brightness_contrast": ("nit",),
    "operation_hours": ("text",),
    "power": ("typ", "max"),
    "player_os": ("os",),
    "magicinfo": ("supported",),
    "warranty": ("years",),
    "dimensions": ("w", "h"),
    "weight": ("set",),
}


def is_complete(row_key: str, value: dict[str, Any] | None) -> bool:
    if not value:
        return False
    if "text" in value and row_key not in ("operation_hours",) and len(value) == 1:
        return bool(value["text"])
    for p in REQUIRED_PARTS.get(row_key, ()):
        if value.get(p) is None:
            return False
    return True


def missing_parts(row_key: str, value: dict[str, Any] | None) -> list[str]:
    if not value:
        return list(REQUIRED_PARTS.get(row_key, ("value",)))
    return [p for p in REQUIRED_PARTS.get(row_key, ()) if value.get(p) is None]


def values_conflict(row_key: str, a: dict[str, Any] | None, b: dict[str, Any] | None) -> bool:
    """두 출처 값이 서로 다른가 — 양쪽에 다 있는 부분만 비교(한쪽에 없는 부분은 다름이 아님)."""
    if not a or not b:
        return False
    if ("text" in a and len(a) == 1) or ("text" in b and len(b) == 1):
        return diff_key(row_key, a) != diff_key(row_key, b)
    keys = ("hours",) if row_key == "operation_hours" else tuple(k for k in a if k in b)
    for k in keys:
        x, y = a.get(k), b.get(k)
        if x is None or y is None:
            continue
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) and not isinstance(y, bool):
            if abs(float(x) - float(y)) > 1e-9:
                return True
        elif re.sub(r"\s+", "", str(x)).lower() != re.sub(r"\s+", "", str(y)).lower():
            return True
    return False


def merge_values(a: dict[str, Any] | None, b: dict[str, Any] | None) -> dict[str, Any] | None:
    """다르지 않은 두 값 — a 에 없는 부분을 b 로 채운다."""
    if not a:
        return dict(b) if b else None
    out = dict(a)
    for k, v in (b or {}).items():
        if out.get(k) is None and v is not None:
            out[k] = v
    return out


def same_value(row_key: str, a: dict[str, Any] | None, b: dict[str, Any] | None) -> bool:
    """출처끼리 같은 값인가(표시 정규화 뒤 비교)."""
    return diff_key(row_key, a) == diff_key(row_key, b)


def diff_key(row_key: str, v: dict[str, Any] | None) -> str:
    """차이 계산용 정규 문자열(숫자 · 단위 사이 공백 무시)."""
    if not v:
        return ""
    if "text" in v and len(v) == 1:
        return re.sub(r"\s+", "", str(v["text"])).lower()
    parts = []
    for k in sorted(v):
        x = v[k]
        if isinstance(x, float) and x.is_integer():
            x = int(x)
        parts.append(f"{k}={x}")
    return re.sub(r"\s+", "", "|".join(parts)).lower()


# ── 표시 ────────────────────────────────────────────────

@dataclass
class Fmt:
    language: str = "ko"          # ko · en · ko_en
    length_unit: str = "mm"       # mm · inch · both
    weight_unit: str = "kg"       # kg · lb · both
    number_format: str = "1,234.5"

    @classmethod
    def of(cls, f: dict[str, Any] | None) -> "Fmt":
        f = f or {}
        return cls(language=f.get("language", "ko"), length_unit=f.get("length_unit", "mm"), weight_unit=f.get("weight_unit", "kg"),
                   number_format=f.get("number_format", "1,234.5"))


@dataclass
class Line:
    """표시 한 줄(영문 · 한/영에서 1 · 2번 항목은 두 줄)."""
    label: str
    text: str
    converted: bool = False
    original_text: str | None = None
    pending: bool = False


def pending_text(lang: str) -> str:
    return {"ko": PENDING_KO, "en": PENDING_EN}.get(lang, f"{PENDING_KO} / {PENDING_EN}")


def _n(x: Any, f: Fmt, **kw: Any) -> str:
    return fmt_num(x, f.number_format, **kw)


def _bi(ko: str, en: str, lang: str) -> str:
    if lang == "ko":
        return ko
    if lang == "en":
        return en
    return ko if ko == en else f"{ko} / {en}"


def _pend(lang: str) -> str:
    return pending_text("ko" if lang == "ko" else ("en" if lang == "en" else "ko_en"))


def render_text(row_key: str, value: dict[str, Any] | None, f: Fmt, lang: str | None = None) -> tuple[str, bool, str | None]:
    """한 언어(ko · en · ko_en) 한 줄 글. 돌려줌: (글, 단위 바뀜, 원래 값 글)."""
    lang = lang or f.language
    if value is None:
        return _pend(lang), False, None
    if "text" in value and len(value) == 1:
        return str(value["text"]), False, None
    P = _pend(lang)
    if row_key == "size_resolution":
        inch = f'{value["inch"]}"' if value.get("inch") else P
        res = f'{value["w"]}×{value["h"]}' if value.get("w") else P
        return f"{inch} · {res}", False, None
    if row_key == "brightness_contrast":
        nit = f"{_n(value['nit'], f)} nit" if value.get("nit") is not None else P
        con = f"{_n(value['ca'], f)}:{_n(value['cb'], f)}" if value.get("ca") is not None else None
        return (f"{nit} · {con}" if con else nit), False, None
    if row_key == "operation_hours":
        return str(value.get("text") or P), False, None
    if row_key == "power":
        sep = " · " if lang == "ko" else " / "
        t = f"{_n(value['typ'], f)} W" if value.get("typ") is not None else P
        m = f"{_n(value['max'], f)} W" if value.get("max") is not None else P
        return f"{t}{sep}{m}", False, None
    if row_key == "player_os":
        os_ = value.get("os") or P
        if value.get("builtin"):
            return _bi(f"{os_} · 내장", f"{os_} · Built-in", lang), False, None
        return os_, False, None
    if row_key == "magicinfo":
        s = value.get("supported")
        if s is None:
            return P, False, None
        return (_bi("지원", "Supported", lang) if s else _bi("미지원", "Not supported", lang)), False, None
    if row_key == "warranty":
        y = value.get("years")
        if y is None:
            return P, False, None
        yy = _n(y, f)
        return _bi(f"{yy}년", f"{yy} year" + ("" if float(y) == 1 else "s"), lang), False, None
    if row_key == "io_ports":
        parts_ko, parts_en = [], []
        for key, lab in (("hdmi", "HDMI"), ("dp", "DP"), ("usb", "USB")):
            if value.get(key):
                parts_ko.append(f"{lab} {value[key]}")
                parts_en.append(f"{lab} {value[key]}")
        rin, rout = value.get("rs232_in"), value.get("rs232_out")
        if rin or rout:
            ko = "RS232 " + " · ".join([x for x, on in (("입력", rin), ("출력", rout)) if on])
            en = "RS232 " + " · ".join([x for x, on in (("In", rin), ("Out", rout)) if on])
            parts_ko.append(ko)
            parts_en.append(en)
        for key, lab in (("rj45", "RJ45"), ("wifi", "Wi-Fi"), ("bt", "Bluetooth")):
            if value.get(key):
                parts_ko.append(lab)
                parts_en.append(lab)
        if not parts_ko:
            return P, False, None
        return _bi(" · ".join(parts_ko), " · ".join(parts_en), lang), False, None
    if row_key == "dimensions":
        w, h, d = value.get("w"), value.get("h"), value.get("d")
        if w is None:
            return P, False, None
        dims = [x for x in (w, h, d) if x is not None]
        sep_mm = "×" if lang != "en" else " × "
        mm = sep_mm.join(_n(x, f) for x in dims) + " mm"
        inch = " × ".join(_n(mm_to_in(x), f) for x in dims) + " in"
        original = " x ".join(_plain_num(x) for x in dims) + " mm"
        if f.length_unit == "inch":
            return inch, True, original
        if f.length_unit == "both":
            return f"{mm} ({inch})", True, original
        return mm, False, None
    if row_key == "weight":
        s, p = value.get("set"), value.get("pkg")
        if s is None and p is None:
            return P, False, None
        if f.weight_unit == "lb":
            t = f"{_n(kg_to_lb(s), f)} lb" if s is not None else P
            u = f"{_n(kg_to_lb(p), f)} lb" if p is not None else P
            orig = f"{_plain_num(s)} kg / {_plain_num(p)} kg"
            return f"{t} / {u}", True, orig
        if f.weight_unit == "both":
            t = f"{_n(s, f)} kg ({_n(kg_to_lb(s), f)} lb)" if s is not None else P
            u = f"{_n(p, f)} kg ({_n(kg_to_lb(p), f)} lb)" if p is not None else P
            orig = f"{_plain_num(s)} kg / {_plain_num(p)} kg"
            return (_bi(f"{t} · 포장 {u}", f"{t} / {u}", lang) if lang != "ko" else f"{t} · 포장 {u}"), True, orig
        t = f"{_n(s, f)} kg" if s is not None else P
        u = f"{_n(p, f)} kg" if p is not None else P
        return _bi(f"{t} · 포장 {u}", f"{t} / {u}", lang), False, None
    if row_key == "bezel":
        mm = value.get("mm")
        tail = value.get("tail")
        if mm is None:
            return P, False, None
        t_mm = f"{_n(mm, f)} mm" + (f" {tail}" if tail else "")
        t_in = f"{_n(mm_to_in(mm), f)} in" + (f" {tail}" if tail else "")
        if f.length_unit == "inch":
            return t_in, True, t_mm
        if f.length_unit == "both":
            return f"{t_mm} ({_n(mm_to_in(mm), f)} in)", True, t_mm
        return t_mm, False, None
    if row_key == "certification":
        ko, en = [], []
        if value.get("kc"):
            ko.append(f"KC {value['kc']}")
            en.append(f"KC {value['kc']}")
        if value.get("safety"):
            ko.append(f"안전 {value['safety']}")
            en.append(f"Safety {value['safety']}")
        if value.get("emc"):
            ko.append(f"EMC {value['emc']}")
            en.append(f"EMC {value['emc']}")
        if not ko:
            return P, False, None
        return _bi(" · ".join(ko), " · ".join(en), lang), False, None
    if row_key == "accessories":
        ko, en = [], []
        if value.get("mount"):
            ko.append(f"마운트 {value['mount']}")
            en.append(f"Mount {value['mount']}")
        if value.get("stand"):
            ko.append(f"스탠드 {value['stand']}")
            en.append(f"Stand {value['stand']}")
        if not ko:
            return P, False, None
        return _bi(" · ".join(ko), " · ".join(en), lang), False, None
    if row_key == "derived:annual_energy_cost":
        krw = value.get("krw")
        if krw is None:
            return P, False, None
        return _bi(f"{_n(krw, f, decimals=0)}원", f"KRW {_n(krw, f, decimals=0)}", lang), False, None
    return str(value.get("text") or P), False, None


def _plain_num(x: Any) -> str:
    if x is None:
        return "—"
    d = Decimal(str(x))
    s = format(d, "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def render_lines(row_key: str, value: dict[str, Any] | None, f: Fmt, label_ko: str, en_lines: list[str]) -> list[Line]:
    """시트 행 하나를 언어 설정대로 줄(들)로. 영문 · 한/영에서 size_resolution · brightness_contrast 는 두 줄."""
    lang = f.language
    pend = value is None
    if lang == "ko" or len(en_lines) < 2 or row_key not in ("size_resolution", "brightness_contrast"):
        text, conv, orig = render_text(row_key, value, f, lang)
        label = label_ko if lang == "ko" else (en_lines[0] if lang == "en" and en_lines else f"{label_ko} / {en_lines[0]}" if en_lines else label_ko)
        return [Line(label, text, conv, orig, pend)]
    P = _pend(lang)
    lines: list[Line] = []
    v = value or {}
    if row_key == "size_resolution":
        inch = f'{v["inch"]}"' if v.get("inch") else P
        grade = grade_label(v.get("w"), v.get("h"))
        res = grade or (f'{v["w"]} × {v["h"]}' if v.get("w") else P)
        res_ko = f'{v["w"]}×{v["h"]}' if v.get("w") else P
        lines.append(Line(en_lines[0] if lang == "en" else f"화면 크기 / {en_lines[0]}", inch, pending=pend))
        lines.append(Line(en_lines[1] if lang == "en" else f"해상도 / {en_lines[1]}", res if lang == "en" else _bi(res_ko, res, lang),
                          pending=pend))
    else:
        nit = f"{_n(v['nit'], f)} nit" if v.get("nit") is not None else P
        con = f"{_n(v['ca'], f)}:{_n(v['cb'], f)}" if v.get("ca") is not None else P
        lines.append(Line(en_lines[0] if lang == "en" else f"밝기 / {en_lines[0]}", nit, pending=pend))
        lines.append(Line(en_lines[1] if lang == "en" else f"명암비 / {en_lines[1]}", con, pending=pend))
    return lines


def diff_part(row_key: str, values: list[dict[str, Any] | None], f: Fmt | None = None) -> tuple[str | None, list[str]]:
    """두 값 이상이 한 칸에서 다를 때 다른 부분만(SP3W `밝기 · QB55C` / `카탈로그 · 350 nit`).
    돌려줌: (부분 이름 또는 None = 행 전체, 값마다 글)."""
    f = f or Fmt()
    vs = [v or {} for v in values]
    if row_key == "brightness_contrast":
        nits = {repr(v.get("nit")) for v in vs if v.get("nit") is not None}
        cons = {repr((v.get("ca"), v.get("cb"))) for v in vs if v.get("ca") is not None}
        if len(nits) > 1 and len(cons) <= 1:
            return "밝기", [f"{_n(v['nit'], f)} nit" if v.get("nit") is not None else PENDING_KO for v in vs]
        if len(cons) > 1 and len(nits) <= 1:
            return "명암비", [f"{_n(v['ca'], f)}:{_n(v['cb'], f)}" if v.get("ca") is not None else PENDING_KO for v in vs]
    if row_key == "size_resolution":
        inches = {repr(v.get("inch")) for v in vs if v.get("inch")}
        res = {repr((v.get("w"), v.get("h"))) for v in vs if v.get("w")}
        if len(inches) > 1 and len(res) <= 1:
            return "화면 크기", [f'{v["inch"]}"' if v.get("inch") else PENDING_KO for v in vs]
        if len(res) > 1 and len(inches) <= 1:
            return "해상도", [f'{v["w"]}×{v["h"]}' if v.get("w") else PENDING_KO for v in vs]
    return None, [render_text(row_key, v or None, f, "ko")[0] for v in values]


def flag_text(kind: str, n_sources: int = 2) -> str:
    return "값 없음" if kind in ("missing", "missing_product") else f"출처 {n_sources}곳 다름"


# ── 입력 파서(값 확인 · 셀 수정, §7.9-8) ────────────────────

class InvalidValue(Exception):
    def __init__(self, expected_unit: str | None, message: str):
        super().__init__(message)
        self.expected_unit = expected_unit
        self.message = message


EXPECTED_UNIT = {"power": "W", "brightness_contrast": "nit", "warranty": "년", "dimensions": "mm", "weight": "kg", "bezel": "mm",
                 "size_resolution": '"', "operation_hours": "/7"}

def _units(text: str) -> list[str]:
    out = []
    for m in re.finditer(r"(kwh|kw|wh|nits?|cd/㎡|cd/m2|cd/m²|years?|yrs?|개월|months?|mm|cm|inch|in\b|인치|kg|lbs?|시간|년|\"|w\b|h\b)", text, re.I):
        out.append(m.group(1).lower())
    return out


def parse_input(row_key: str, text: str, current: dict[str, Any] | None = None) -> dict[str, Any]:
    """사용자 입력 → 정규 값. 숫자 · 단위 검사(결정적) — 단위가 다르면 InvalidValue(expected_unit)."""
    t = (text or "").strip()
    if not t:
        raise InvalidValue(EXPECTED_UNIT.get(row_key), "값을 넣어 주세요.")
    us = _units(t)
    ns = numbers(t)
    if row_key == "power":
        bad = [u for u in us if u not in ("w",)]
        if bad or not ns:
            raise InvalidValue("W", "W 단위로 넣어 주세요.")
        typ = ns[0]
        mx = ns[1] if len(ns) > 1 else None
        return {"typ": typ, "max": mx}
    if row_key == "brightness_contrast":
        bad = [u for u in us if u not in ("nit", "nits", "cd/㎡", "cd/m2", "cd/m²")]
        if bad or not ns:
            raise InvalidValue("nit", "nit 단위로 넣어 주세요.")
        m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*:\s*(\d[\d,]*(?:\.\d+)?)", t)
        cur = current or {}
        rest = t.replace(m.group(0), " ") if m else t
        rest_nums = numbers(rest)
        nit = rest_nums[0] if rest_nums else cur.get("nit")
        ca = float(m.group(1).replace(",", "")) if m else cur.get("ca")
        cb = float(m.group(2).replace(",", "")) if m else cur.get("cb")
        return {"nit": nit, "ca": ca, "cb": cb}
    if row_key == "warranty":
        bad = [u for u in us if u not in ("년", "years", "year", "yrs", "yr")]
        if bad or not ns:
            raise InvalidValue("년", "년 단위로 넣어 주세요.")
        return {"years": ns[0]}
    if row_key == "dimensions":
        bad = [u for u in us if u not in ("mm",)]
        if bad or len(ns) < 2:
            raise InvalidValue("mm", "mm 단위로 가로 × 세로 × 깊이를 넣어 주세요.")
        return {"w": ns[0], "h": ns[1], "d": ns[2] if len(ns) > 2 else None}
    if row_key == "weight":
        bad = [u for u in us if u not in ("kg",)]
        if bad or not ns:
            raise InvalidValue("kg", "kg 단위로 넣어 주세요.")
        return {"set": ns[0], "pkg": ns[1] if len(ns) > 1 else None}
    if row_key == "bezel":
        bad = [u for u in us if u not in ("mm",)]
        if bad or not ns:
            raise InvalidValue("mm", "mm 단위로 넣어 주세요.")
        tail = re.sub(r"^\s*\d+(?:\.\d+)?\s*mm\s*", "", t, flags=re.I).strip() or None
        return {"mm": ns[0], "tail": tail}
    if row_key == "operation_hours":
        m = re.search(r"(\d{1,2})\s*/\s*7", t)
        if m:
            return {"text": f"{m.group(1)}/7", "hours": float(m.group(1))}
        m = re.search(r"(\d{1,2})\s*(시간|h)", t, re.I)
        if m:
            return {"text": f"{m.group(1)}/7", "hours": float(m.group(1))}
        raise InvalidValue("/7", "하루 운영 시간(예 24/7)으로 넣어 주세요.")
    if row_key == "size_resolution":
        m = re.search(r"(\d{2,3})\s*(\"|인치|inch|in\b|형)", t, re.I)
        r = parse_resolution(t)
        cur = current or {}
        if not m and not r:
            raise InvalidValue('"', '크기(55")나 해상도(3840×2160)로 넣어 주세요.')
        return {"inch": int(m.group(1)) if m else cur.get("inch"), "w": r[0] if r else cur.get("w"), "h": r[1] if r else cur.get("h")}
    if row_key == "magicinfo":
        low = t.lower()
        if any(x in low for x in ("미지원", "not", "없음", "불가")):
            return {"supported": False}
        if any(x in low for x in ("지원", "supported", "있음", "가능", "yes")):
            return {"supported": True}
        return {"text": t}
    return {"text": t}


# ── 우위(§4.14.2) ───────────────────────────────────────

def _score(row_key: str, v: dict[str, Any] | None) -> tuple[float, ...] | None:
    """클수록 좋은 점수(같으면 다음 기준). 없으면 None(그 행은 우위 없음)."""
    if not v:
        return None
    if "text" in v and len(v) == 1:
        return None
    try:
        if row_key == "size_resolution":
            if not v.get("w") or not v.get("h"):
                return None
            return (float(v["w"]) * float(v["h"]),)
        if row_key == "brightness_contrast":
            if v.get("nit") is None:
                return None
            c = (float(v["ca"]) / float(v["cb"] or 1)) if v.get("ca") is not None else 0.0
            return (float(v["nit"]), c)
        if row_key == "operation_hours":
            return (float(v["hours"]),) if v.get("hours") is not None else None
        if row_key == "power":
            if v.get("typ") is None:
                return None
            return (-float(v["typ"]), -float(v["max"]) if v.get("max") is not None else 0.0)
        if row_key == "warranty":
            return (float(v["years"]),) if v.get("years") is not None else None
        if row_key == "bezel":
            return (-float(v["mm"]),) if v.get("mm") is not None else None
        if row_key == "derived:annual_energy_cost":
            return (-float(v["krw"]),) if v.get("krw") is not None else None
    except (TypeError, ValueError):
        return None
    return None


def compute_wins(row_key: str, values: list[dict[str, Any] | None]) -> list[bool]:
    """행 하나의 우위 칸. 셀 중 하나라도 값이 없으면 우위 없음. 동점이 전부면 없음."""
    n = len(values)
    if n < 2:
        return [False] * n
    if row_key == "magicinfo":
        sup = [v.get("supported") if v else None for v in values]
        if any(s is None for s in sup):
            return [False] * n
        if all(sup) or not any(sup):
            return [False] * n
        return [bool(s) for s in sup]
    scores = [_score(row_key, v) for v in values]
    if any(s is None for s in scores):
        return [False] * n
    best = max(scores)  # type: ignore[type-var]
    wins = [s == best for s in scores]
    if all(wins):
        return [False] * n
    return wins


# ── 파생 행(§4.15.7) ────────────────────────────────────

def annual_energy(power: dict[str, Any] | None, op: dict[str, Any] | None, price: float | None) -> dict[str, Any] | None:
    if not power or power.get("typ") is None or not op or op.get("hours") is None:
        return None
    kwh = float(Decimal(str(power["typ"])) * Decimal(str(op["hours"])) * 365 / 1000)
    out: dict[str, Any] = {"kwh": round(kwh, 1), "hours": op["hours"], "price": price}
    out["krw"] = round(kwh * price) if price else None
    return out
