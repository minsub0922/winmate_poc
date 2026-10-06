"""조건으로 모델 찾기(SP1C) — 조건 행 판정 · 정렬 · 보일 카드 · 문장(06-spec §4.5.4, 결정적)."""
from __future__ import annotations

from typing import Any

from .fmt import category_label, fmt_num
from .values import attr, attr_like, is_none_value

SIZE_CHIPS = ["43", "50", "55", "65", "75+"]
USAGE_LABEL = {"menu_board": "메뉴보드", "wayfinding": "안내", "monitoring": "관제 · 모니터링", "meeting": "회의"}
INSTALL_LABEL = {"wall": "벽걸이", "stand": "스탠드", "ceiling": "천장", "portrait": "세로 설치"}
BRIGHT_LABEL = {"any": "상관없음", "desc": "높은 순", "outdoor": "실외용"}
REQUIRED_LABEL = {"continuous_operation": "24시간 운영", "wall": "벽걸이", "magicinfo": "MagicINFO 호환", "stand": "스탠드",
                  "outdoor": "실외용", "ceiling": "천장", "portrait": "세로 설치"}
# 용도 → C2 신호(제안, §4.5.4)
USAGE_C2 = {"menu_board": {"soft": ["remote_content_mgmt"], "space": "sales_floor"}, "wayfinding": {"space": "lobby"},
            "monitoring": {"soft": ["continuous_operation"], "space": "control_room"}, "meeting": {"soft": ["touch_interactive"], "space": "meeting_room"}}
EXTRA_KEYS = {"bezel_mm": "베젤", "weight_kg": "무게", "brightness_nit": "밝기", "power_w": "소비전력"}
HIGH_NIT = 700
OUTDOOR_NIT = 2500
MAX_CARDS = 6
MAX_OUT = 2


def required_label(key: str) -> str:
    if key.startswith("size:"):
        v = key.split(":", 1)[1]
        return f'{v}"' if v != "75+" else '75" 이상'
    return REQUIRED_LABEL.get(key, key)


def c2_params(conditions: dict[str, Any], text: str | None, extra_caps: list[str] | None = None) -> dict[str, Any]:
    soft: list[str] = []
    space = None
    for u in conditions.get("usage") or []:
        sig = USAGE_C2.get(u) or {}
        for s in sig.get("soft") or []:
            if s not in soft:
                soft.append(s)
        space = space or sig.get("space")
    req = conditions.get("required") or []
    if "continuous_operation" in req and "continuous_operation" not in soft:
        soft.append("continuous_operation")
    if "magicinfo" in req and "remote_content_mgmt" not in soft:
        soft.append("remote_content_mgmt")
    if conditions.get("brightness") == "outdoor":
        for s in ("sunlight_readable", "weatherproof"):
            if s not in soft:
                soft.append(s)
    for c in extra_caps or []:
        c = c.removeprefix("cap_")
        if c not in soft:
            soft.append(c)
    return {"category": "top_display", "space": space, "soft": soft, "text": text or None, "limit": 15}


def _nit(spec: dict[str, Any]) -> float | None:
    d = spec.get("derived") or {}
    if d.get("brightness_typ_nit") is not None:
        return float(d["brightness_typ_nit"])
    a = attr(spec, "디스플레이", "밝기 (Typ)")
    if a and a.get("num") is not None:
        return float(a["num"])
    return None


def _hours(spec: dict[str, Any]) -> float | None:
    a = attr(spec, "디스플레이", "제품 사용 시간")
    if not a:
        return None
    if a.get("num") is not None:
        return float(a["num"])
    from .fmt import first_number
    return first_number(a.get("raw"))


def _has_cap(spec: dict[str, Any], cap: str) -> bool:
    return any(p.get("capability_id") == cap for p in spec.get("provides") or [])


def _magicinfo(spec: dict[str, Any]) -> str:
    for s in spec.get("solutions") or []:
        if "magicinfo" in ((s.get("id") or "") + (s.get("name") or "")).lower():
            return "ok"
    for p in spec.get("provides") or []:
        if p.get("capability_id") == "cap_remote_content_mgmt" and "magicinfo" in (p.get("evidence") or "").lower():
            return "ok"
    a = (attr_like(spec, None, r"MagicINFO") or [(None, None)])[0][1]
    if a and is_none_value(a.get("raw")):
        return "no"
    return "check"


def _install_state(spec: dict[str, Any], kind: str) -> str:
    if kind == "wall":
        return "ok" if (attr(spec, "기구사양", "VESA 마운트") or attr(spec, "추가 기능", "마운트")) else "check"
    if kind == "stand":
        a = attr(spec, "추가 기능", "스탠드")
        return "ok" if a and not is_none_value(a.get("raw")) else "check"
    return "check"   # 천장 · 세로 설치: KB 근거 속성 없음(Q-SP-25)


def evaluate(spec: dict[str, Any], conditions: dict[str, Any], extra: list[dict[str, Any]]) -> dict[str, Any]:
    """모델 하나의 조건 행. 돌려줌: {rows, ok, total, out, req_ok, nit, hours}."""
    rows: list[dict[str, Any]] = []
    req = list(conditions.get("required") or [])
    sizes = list(conditions.get("sizes") or [])
    inch = spec.get("size_inch")
    if sizes:
        if inch is None:
            st, val = "check", "확인 필요"
        else:
            ok = any((s == "75+" and inch >= 75) or (s != "75+" and int(s) == inch) for s in sizes)
            st, val = ("ok", f'{inch}"') if ok else ("no", f'{inch}" · 조건 밖')
        rows.append({"key": "size", "label": "크기", "value_text": val, "state": st, "required": any(r.startswith("size") for r in req)})
    nit = _nit(spec)
    outdoor = conditions.get("brightness") == "outdoor"
    if nit is None:
        st, val = "check", "확인 필요"
    else:
        val = f"{fmt_num(nit)} nit" + (" · 고휘도" if nit >= HIGH_NIT else "")
        st = "ok"
        if outdoor and not (_has_cap(spec, "cap_sunlight_readable") or _has_cap(spec, "cap_weatherproof") or nit >= OUTDOOR_NIT):
            st, val = "no", f"{fmt_num(nit)} nit · 조건 밖"
    rows.append({"key": "brightness", "label": "밝기", "value_text": val, "state": st, "required": outdoor and "outdoor" in req})
    hours = _hours(spec)
    if "continuous_operation" in req:
        if hours is None:
            st, val = "check", "확인 필요"
        elif hours >= 24:
            st, val = "ok", "24시간"
        else:
            st, val = "no", f"{fmt_num(hours)}시간 · 조건 밖"
        rows.append({"key": "operation", "label": "운영", "value_text": val, "state": st, "required": True})
    installs = list(conditions.get("install") or [])
    if "wall" in req and "wall" not in installs:
        installs.append("wall")
    if "stand" in req and "stand" not in installs:
        installs.append("stand")
    if installs:
        states = [_install_state(spec, k) for k in installs]
        st = "no" if "no" in states else ("check" if "check" in states else "ok")
        rows.append({"key": "install", "label": "설치", "value_text": " · ".join(INSTALL_LABEL.get(k, k) for k in installs), "state": st,
                     "required": any(k in req for k in installs)})
    if "magicinfo" in req:
        st = _magicinfo(spec)
        rows.append({"key": "cms", "label": "CMS", "value_text": "MagicINFO" if st != "check" else "확인 필요", "state": st, "required": True})
    for ex in extra or []:
        if ex.get("kind") != "filter" or not ex.get("key"):
            continue
        v = _extra_value(spec, ex["key"])
        if v is None:
            st = "check"
        else:
            op, target = ex.get("op") or ">=", float(ex.get("value") or 0)
            st = "ok" if ((op == ">=" and v >= target) or (op == "<=" and v <= target)) else "no"
        rows.append({"key": f"extra:{ex['id']}", "label": ex.get("label") or EXTRA_KEYS.get(ex["key"], ex["key"]),
                     "value_text": (fmt_num(v) if v is not None else "확인 필요"), "state": st, "required": False})
    ok = len([r for r in rows if r["state"] == "ok"])
    out = any(r["state"] == "no" for r in rows)
    req_rows = [r for r in rows if r.get("required")]
    return {"rows": rows, "ok": ok, "total": len(rows), "out": out, "req_ok": all(r["state"] == "ok" for r in req_rows),
            "nit": nit, "hours": hours, "no": len([r for r in rows if r["state"] == "no"])}


def _extra_value(spec: dict[str, Any], key: str) -> float | None:
    from .fmt import first_number
    if key == "brightness_nit":
        return _nit(spec)
    if key == "weight_kg":
        d = spec.get("derived") or {}
        return d.get("weight_kg_set")
    if key == "bezel_mm":
        a = attr(spec, "기구사양", "베젤 두께")
        return first_number((a or {}).get("raw"))
    if key == "power_w":
        for name, a in attr_like(spec, "전원", r"소비전력"):
            if "Typ" in name or "일반" in name:
                return a.get("num")
    return None


def rank(cands: list[dict[str, Any]], conditions: dict[str, Any], extra: list[dict[str, Any]]) -> list[dict[str, Any]]:
    desc = conditions.get("brightness") == "desc"
    sort_extra = [e for e in extra or [] if e.get("kind") == "sort"]

    def key(c: dict[str, Any]) -> tuple:
        k: list[Any] = [c["out"], not c["req_ok"], -c["ok"]]
        k.append(-(c.get("nit") or 0) if desc else 0)
        for e in sort_extra:
            v = c.get("extra_values", {}).get(e.get("key") or "")
            v = v if v is not None else 1e9
            k.append(v if (e.get("op") or "asc") == "asc" else -v)
        k.append(-(c.get("c2_score") or 0))
        k.append(c.get("model_code") or "")
        return tuple(k)

    return sorted(cands, key=key)


def visible(cands: list[dict[str, Any]], hide_out: bool) -> list[dict[str, Any]]:
    """보이는 카드 = 조건 밖 아닌 것 전부 + 조건 밖 중 no 가 가장 적은 2개(최대 6장). hide_out 이면 조건 밖 숨김."""
    inside = [c for c in cands if not c["out"]]
    outside = sorted([c for c in cands if c["out"]], key=lambda c: (c.get("no", 0), cands.index(c)))
    shown = inside[:MAX_CARDS]
    if not hide_out:
        room = MAX_CARDS - len(shown)
        if room > 0:
            pick = outside[: min(MAX_OUT, room)]
            shown = [c for c in cands if c in shown or c in pick]
    return shown


def series_label_of(spec: dict[str, Any]) -> str:
    return f"{category_label(spec.get('category_id'))} {spec.get('series_code') or ''}".strip()


def agent_text(n: int, conditions: dict[str, Any]) -> tuple[str, str]:
    desc = conditions.get("brightness") == "desc"
    sort = "밝기가 높은 순" if desc else "조건 일치 순"
    req = [required_label(r) for r in conditions.get("required") or []]
    pre = f"필수 조건({' · '.join(req)})을 먼저 맞추고 " if req else ""
    return (f"조건에 맞는 후보 {n}개를 찾았습니다. {pre}{sort}으로 정렬했어요. 시트에 넣을 모델을 고르면 비교표로 만듭니다.", sort)
