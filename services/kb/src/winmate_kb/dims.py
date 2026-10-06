"""제품 치수 정규화(08-birdseye 요청 4 · 06-spec): 스펙 행 `그룹 › 속성 = 'A x B x C mm'` → {w, h, d}(mm).

결정적 규칙(사실을 만들지 않는다 — 원문 수치를 축 순서대로 옮기고 단위만 mm 로 맞춘다).
- 축 순서: 속성 이름(없으면 그룹 이름)의 낱말 순서.
  가로 · 폭 · W → w / 높이 · H → h / 깊이 · 두께 · D → d.
  `세로` 는 같은 이름에 `높이` 가 있으면 d(프린터 `가로x세로x높이` = W×D×H), 없으면 h(태블릿 `가로x세로x두께` = W×H×D).
  `(H x V)`(액티브 디스플레이)는 H = 가로(w), V = 세로(h). 낱말이 없으면 W×H×D 로 본다.
- 단위: 값 뒤의 mm · cm · m(없으면 이름의 (mm) · 기본 mm). 결과는 mm(소수 둘째 자리).
- 종류(kind): body(제품 · 본체 · 외관) · without_stand · with_stand · package(포장 · 박스 · 팔레트 · Gross) ·
  active_area(액티브 디스플레이) · indoor_unit · outdoor_unit · panel · other(타공 · 설치 공간 · 부속 …).
- `dims_mm`(대표) = body → without_stand 순서로 처음 읽힌 행. 없으면 null.
- 치수가 아닌 'A x B' 행(VESA · 마운트 · 간격 · 픽셀 피치 · 해상도 · Pixel Configuration · USB · 나사 · 용지 …)과
  지름(Φ) · 범위(~) 값은 읽지 않는다(범위인 축은 null).
"""
from __future__ import annotations

import re
from typing import Any

NUM = r"\d[\d,]*(?:\.\d+)?"
_ANN = r"(?:\s*(?:mm|cm)(?![A-Za-z]))?\s*(?:\([^)]*\))?"   # 610 mm x · 1191.936 (H) · 482(일반) 같은 숫자 뒤 단위 · 주석
_PRE = r"(?:[WHDwhd]\s*[:：]?\s*)?"               # W1237.9 · H:88 같은 축 글자 접두
SEP = r"\s*[x×X*]\s*"
TRIPLE = re.compile(rf"{_PRE}(?P<a>{NUM}){_ANN}{SEP}{_PRE}(?P<b>{NUM}){_ANN}(?:{SEP}{_PRE}(?P<c>{NUM}){_ANN})?")
UNIT_AFTER = re.compile(r"^\s*(mm|cm|m)\b", re.I)
UNIT_ANY = re.compile(r"(?<![A-Za-z])(mm|cm)(?![A-Za-z])", re.I)

DIM_LABEL = re.compile(r"크기|치수|사이즈|외관|(가로|폭).*(높이|세로|깊이|두께)|W\s*[x×X]\s*[HD]|H\s*x\s*V", re.I)
NOT_DIM = re.compile(r"VESA|베사|마운트|간격|피치|해상도|Pixel|LED\s*구성|USB|구멍|나사|볼트|화면\s*크기|대각|디스플레이\s*크기|스크린\s*사이즈|"
                     r"용지|인쇄|스캔|복사|글자|폰트|카메라|센서|배터리|메모리|저장|용량|출력|입력|전압|전류|주파수|팬모터|풍량", re.I)

_TOK = re.compile(r"가로|폭|세로|높이|깊이|두께|(?<![A-WYZa-wyz])[WHDV](?![A-WYZa-wyz])")   # x · X 는 구분자라 글자로 안 본다
_AXIS = {"가로": "w", "폭": "w", "W": "w", "높이": "h", "H": "h", "깊이": "d", "두께": "d", "D": "d"}


def _f(s: str) -> float:
    return float(s.replace(",", ""))


def axis_order(attr: str | None, group: str | None = None) -> tuple[list[str], str]:
    """(축 순서 ['w','h','d'], 근거 'attr' · 'group' · 'default')."""
    for label, basis in ((attr or "", "attr"), (group or "", "group")):
        toks = _TOK.findall(label)
        if not toks:
            continue
        if "H" in toks and "V" in toks:               # (H x V): 가로(Horizontal) × 세로(Vertical)
            out = ["w" if t == "H" else "h" if t == "V" else _AXIS.get(t, "") for t in toks]
        else:
            has_height = "높이" in toks or "H" in toks
            out = [("d" if has_height else "h") if t == "세로" else _AXIS.get(t, "") for t in toks]
        seen: list[str] = []
        for a in out:
            if a and a not in seen:
                seen.append(a)
        if len(seen) >= 2:
            for a in ("w", "h", "d"):
                if a not in seen:
                    seen.append(a)
            return seen, basis
    return ["w", "h", "d"], "default"


def kind_of(group: str | None, attr: str | None) -> str:
    g, a = group or "", attr or ""
    t = f"{g} {a}"
    if re.search(r"포장|박스|팔레트|Gross|패키지", t, re.I):
        return "package"
    if re.search(r"엑티브|액티브|active", a, re.I):
        return "active_area"
    if re.search(r"타공|설치|조리실|이어버드|케이스|접힌|하이드로", a + " " + g):
        return "other"
    if re.search(r"스탠드\s*(제외|미포함)", a):
        return "without_stand"
    if re.search(r"스탠드\s*포함", a):
        return "with_stand"
    if re.search(r"판넬|패널", t):
        return "panel"
    if "실내기" in t:
        return "indoor_unit"
    if "실외기" in t:
        return "outdoor_unit"
    return "body"


def is_dim_label(group: str | None, attr: str | None) -> bool:
    a = attr or ""
    if NOT_DIM.search(a):
        return False
    return bool(DIM_LABEL.search(a) or (DIM_LABEL.search(group or "") and not NOT_DIM.search(group or "")))


def parse_value(raw: str | None, attr: str | None = None, group: str | None = None) -> dict[str, Any] | None:
    """'1,237.9 x 708.8 x 28.5 mm' → {w, h, d, unit:'mm', order:'WxHxD', order_basis}. 못 읽으면 null."""
    if not raw or re.search(r"[Φφø⌀]", raw):
        return None
    m = TRIPLE.search(raw)
    if not m:
        return None
    vals: list[float | None] = [_f(m.group("a")), _f(m.group("b"))]
    if m.group("c"):
        vals.append(_f(m.group("c")))
    rest = raw[m.end():]
    if re.match(r"^\s*[~∼～]\s*\d", rest):           # 마지막 축이 범위(405~755) → 그 축은 비운다
        vals[-1] = None
    um = UNIT_AFTER.match(rest) or UNIT_ANY.search(raw[m.start():]) or UNIT_ANY.search(attr or "")
    unit = (um.group(1).lower() if um else "mm")
    k = {"mm": 1.0, "cm": 10.0, "m": 1000.0}[unit]
    order, basis = axis_order(attr, group)
    out: dict[str, float | None] = {"w": None, "h": None, "d": None}
    for ax, v in zip(order, vals):
        out[ax] = round(v * k, 2) if v is not None else None
    if out["w"] is None and out["h"] is None:
        return None
    return {**out, "unit": "mm", "order": "x".join(a.upper() for a in order[:len(vals)]), "order_basis": basis}


def rows_dims(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """스펙 행(spec_value) → 읽힌 치수 행 전부(원래 순서). 각 행: {w, h, d, unit, raw, attr, kind, order, order_basis, spec_value_id}."""
    out = []
    for r in rows:
        g, a, raw = r.get("group_name"), r.get("attr_name"), r.get("value_raw")
        if not raw or not is_dim_label(g, a):
            continue
        p = parse_value(raw, a, g)
        if p is None:
            continue
        out.append({**p, "raw": raw, "attr": f"{g or ''} › {a or ''}", "kind": kind_of(g, a), "spec_value_id": r.get("id")})
    return out


def primary(dims: list[dict[str, Any]]) -> dict[str, Any] | None:
    """대표 치수(dims_mm): body → without_stand 순서로 처음 행."""
    for kind in ("body", "without_stand"):
        for d in dims:
            if d["kind"] == kind and d["w"] is not None and d["h"] is not None:
                return d
    return None
