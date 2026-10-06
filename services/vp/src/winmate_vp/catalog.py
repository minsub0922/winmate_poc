"""레이아웃 카탈로그(05-vp.md §4.15) — 범용 35종 + 업종판 16 × 3.

정본 코드(저장 · 계약 · export)는 가운뎃점이 없다(`VP-F3`), 화면 코드는 가운뎃점(`VP-F·3`). 검색은 둘 다 받는다.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from . import config

ROLE_STEP = {"CH": "고객 과제", "VP": "가치 제안", "EF": "기대 효과", "REF": "레퍼런스"}
FAMILY_ORDER = ("제품 이미지판", "장면판", "이미지 없는 판", "이미지 없는 판(과제)", "이미지 없는 판(효과)", "현장 질문형", "실사 중심판", "업종판")


def norm(code: str | None) -> str:
    """`VP-F·3` · `vp-f3` · `VP-F 3` → `VP-F3`."""
    return re.sub(r"[\s·•ㆍ]", "", (code or "")).upper()


@lru_cache(maxsize=1)
def _generic() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for raw in config.layouts_raw():
        e = dict(raw)
        e["code"] = norm(e["code"])
        e.setdefault("pillars", None)
        e.setdefault("slots", None)
        e.setdefault("needs", [])
        e["industry_code"] = None
        e["pack_role"] = None
        out[e["code"]] = e
    return out


def pack_role_for(role: str) -> str:
    return str(config.routing().get("role_map", {}).get(role, "A"))


def _role_of_pack(letter: str) -> str:
    rm = config.routing().get("role_map", {})
    for role, let in rm.items():
        if let == letter:
            return role
    return {"A": "CH", "B": "VP", "C": "EF"}.get(letter, "VP")


def pack_code(industry_code: str, role: str) -> str:
    return f"VP-{industry_code}-{pack_role_for(role)}"


@lru_cache(maxsize=1)
def _packs() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    roles = config.routing().get("pack_roles", {})
    for ind in config.industries():
        for letter in ("A", "B", "C"):
            meta = roles.get(letter, {})
            code = f"VP-{ind['code']}-{letter}"
            out[code] = {
                "code": code, "display": code, "family": "업종판", "board": "pack", "role": _role_of_pack(letter),
                "name": f"{ind['name']} · {meta.get('name', '')}", "short": meta.get("name", ""), "when": meta.get("desc", ""),
                "shape": "", "thumb": {"kind": meta.get("thumb", "indVP"), "n": 3}, "pillars": None,
                "slots": ({"subject": "product", "per": "pillar", "grade": "C", "label": "칸 {i}"} if letter != "C" else None),
                "needs": [], "why": {"met": "업종판 준비됨", "unmet": "업종판 제작 중 · 출시 알림 켜짐"},
                "industry_code": ind["code"], "pack_role": letter,
            }
    return out


def entry(code: str | None) -> dict[str, Any] | None:
    c = norm(code)
    return _generic().get(c) or _packs().get(c)


def require(code: str) -> dict[str, Any]:
    e = entry(code)
    if e is None:
        raise KeyError(code)
    return e


def display(code: str | None) -> str:
    e = entry(code)
    return e["display"] if e else (code or "")


def is_pack(code: str | None) -> bool:
    return norm(code) in _packs()


def generic_codes() -> list[str]:
    return list(_generic())


def all_entries(pack_status: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """카탈로그 전체(`GET /v1/layouts`). pack_status: 업종 코드 → in_production | ready."""
    out = []
    for e in list(_generic().values()) + list(_packs().values()):
        d = dict(e)
        d["status"] = "ready" if not d["industry_code"] else (pack_status or {}).get(d["industry_code"], "in_production")
        out.append(d)
    return out


def twin(code: str) -> str | None:
    """이미지판 ↔ 이미지 없는 판 짝(VP-E↔VP-A, VP-F·n↔VP-B·n, VP-G↔VP-C, VP-H↔VP-D)."""
    e = entry(code)
    if not e:
        return None
    return e.get("twin") or e.get("twin_of")


def no_image(code: str) -> str:
    """이미지 없는 짝(이미 이미지 없는 판이면 그대로)."""
    e = entry(code)
    if e and e.get("twin") and e.get("board") == "image":
        return norm(e["twin"])
    return norm(code)


def with_pillars(code: str, n: int) -> str:
    c = norm(code)
    m = re.match(r"^(VP-[FB])(\d)$", c)
    if m and 2 <= n <= 4:
        return f"{m.group(1)}{n}"
    return c


def pillars_of(code: str) -> int | None:
    e = entry(code)
    return int(e["pillars"]) if e and e.get("pillars") else None


def thumb(code: str) -> dict[str, Any]:
    e = entry(code)
    t = (e or {}).get("thumb") or {"kind": "table", "n": 3}
    return {"kind": str(t.get("kind", "table")), "n": int(t.get("n", 3))}


def has_images(code: str) -> bool:
    e = entry(code)
    return bool(e and e.get("slots"))


def pick(code: str, *, why: str = "", chosen_by: str = "agent", pinned: bool = False, fit: int | None = None) -> dict[str, Any]:
    """LayoutPick(§5.2)."""
    e = require(code)
    return {
        "code": e["code"], "display": e["display"], "name": e["name"], "family": e["family"], "thumb": thumb(e["code"]),
        "industry_code": e.get("industry_code"), "pinned": pinned, "chosen_by": chosen_by, "fit": fit, "why": why,
    }


def chip_text(code: str, suffix: str = "") -> str:
    return f"{display(code)}{(' ' + suffix) if suffix else ''}"


def search_codes(q: str) -> set[str]:
    """`VP-F·3` · `VP-F3` 둘 다 같은 정본 코드로."""
    return {norm(q)} if re.match(r"^[A-Za-z]{2}-", (q or "").strip()) else set()
