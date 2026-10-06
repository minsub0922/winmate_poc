"""시드 — 업종 템플릿 16(§10.4) · 솔루션 동작 사전(§10.5) · 예시 골격(§10.6). `services/scenario/seed/*.yaml`."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from . import texts

SEED_DIR = Path(__file__).resolve().parents[2] / "seed"


@lru_cache(maxsize=1)
def _industries() -> list[dict[str, Any]]:
    raw = yaml.safe_load((SEED_DIR / "industry_templates.yaml").read_text(encoding="utf-8")) or {}
    return list(raw.get("industries") or [])


@lru_cache(maxsize=1)
def _solutions() -> list[dict[str, Any]]:
    raw = yaml.safe_load((SEED_DIR / "solution_actions.yaml").read_text(encoding="utf-8")) or {}
    return list(raw.get("solutions") or [])


@lru_cache(maxsize=1)
def _skeletons() -> dict[str, Any]:
    return yaml.safe_load((SEED_DIR / "skeletons.yaml").read_text(encoding="utf-8")) or {}


def industries() -> list[dict[str, Any]]:
    return _industries()


def industry(code: str | None) -> dict[str, Any] | None:
    if not code:
        return None
    return next((d for d in _industries() if d["code"] == code), None)


def industry_for_vertical(kr_vertical: str | None) -> dict[str, Any] | None:
    """KB KR 업종(kr_fnb …) → 업종 템플릿(FB …). 상위 업종(kr_retail_fnb)은 하위 첫 대응으로."""
    if not kr_vertical:
        return None
    for d in _industries():
        if kr_vertical in (d.get("kr_verticals") or []):
            return d
    parents = {"kr_retail_fnb": "FB", "kr_medical": "MD", "kr_education": "ED", "kr_public": "PB", "kr_construction": "RS"}
    return industry(parents.get(kr_vertical))


def industry_by_name(text: str | None) -> dict[str, Any] | None:
    """프로젝트 업종 글(「외식 · 카페」, 「리테일」 …) → 템플릿."""
    if not text:
        return None
    t = text.strip()
    for d in _industries():
        if t in (d["code"], d["name"], d["short"], d.get("case_label")):
            return d
    for d in _industries():
        if d["short"].split(" · ")[0] in t or d["name"].split(" · ")[0] in t:
            return d
    return None


# ── 솔루션 동작 사전 ─────────────────────────────────────────

def solutions() -> list[dict[str, Any]]:
    return _solutions()


def solution(solution_id: str | None) -> dict[str, Any] | None:
    if not solution_id:
        return None
    return next((s for s in _solutions() if s["id"] == solution_id or s.get("kb_id") == solution_id), None)


def solution_by_name(name: str | None) -> dict[str, Any] | None:
    if not name:
        return None
    low = name.strip().lower()
    for s in _solutions():
        names = {s["name"].lower(), s["id"].lower(), (s.get("kb_id") or "").lower()}
        if low in names or s["name"].lower().split(" · ")[0] == low:
            return s
    for s in _solutions():
        if s["name"].lower().split(" ")[0] in low or low in s["name"].lower():
            return s
    return None


def action(solution_id: str, code: str) -> dict[str, Any] | None:
    s = solution(solution_id)
    if s is None:
        return None
    return next((a for a in s["actions"] if a["code"] == code), None)


def action_by_label(solution_id: str, label: str) -> dict[str, Any] | None:
    s = solution(solution_id)
    if s is None:
        return None
    lab = (label or "").strip()
    return next((a for a in s["actions"] if a["label"] == lab or a["code"] == lab), None)


def action_label(solution_id: str, code: str) -> str:
    s = solution(solution_id)
    a = action(solution_id, code)
    if s is None or a is None:
        return ""
    return f"{s['name']} · {a['label']}"


def chip_labels(items: list[dict[str, Any]]) -> list[str]:
    """[{solution_id, action_code}] → 같은 솔루션 동작은 묶어 「MagicINFO · 원격 배포 · 장애 알림」."""
    order: list[str] = []
    grouped: dict[str, list[str]] = {}
    for it in items:
        sid = it.get("solution_id") or ""
        s = solution(sid)
        a = action(sid, it.get("action_code") or "")
        if s is None or a is None:
            continue
        if s["id"] not in grouped:
            order.append(s["id"])
            grouped[s["id"]] = []
        if a["label"] not in grouped[s["id"]]:
            grouped[s["id"]].append(a["label"])
    return [texts.join([solution(sid)["name"], *grouped[sid]]) for sid in order]  # type: ignore[index]


def match_actions(text: str, solution_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """문장 키워드 → 동작 후보(점수 높은 순): {solution_id, action_code, hits, required, optional}."""
    t = text or ""
    out: list[dict[str, Any]] = []
    for s in _solutions():
        if solution_ids is not None and s["id"] not in solution_ids:
            continue
        for a in s["actions"]:
            hits = sum(1 for k in a.get("keywords") or [] if k and k in t)
            req = sum(1 for k in a.get("required_keywords") or [] if k and k in t)
            if hits or req:
                out.append({"solution_id": s["id"], "action_code": a["code"], "hits": hits + 2 * req, "required": req > 0,
                            "optional": bool(a.get("optional"))})
    out.sort(key=lambda x: (-x["hits"], x["solution_id"], x["action_code"]))
    return out


# ── 예시 골격 ──────────────────────────────────────────────

def _lead(ind: dict[str, Any] | None) -> str:
    if ind and ind.get("presets") and ind["presets"][0].get("roles"):
        return str(ind["presets"][0]["roles"][0])
    return "점장"


def _fill(text: str, ind: dict[str, Any] | None) -> str:
    lead = _lead(ind)
    return text.replace("{책임자}가", texts.with_josa(lead, "이/가")).replace("{책임자}", lead)


def skeletons(industry_code: str | None) -> list[dict[str, str]]:
    """SC2 예시 골격 칩 3: 업종을 알면 프리셋 제목 앞 2 + 「장애 발생 상황」, 모르면 보드 3개."""
    gen = {g["title"]: g["text"] for g in _skeletons().get("generic") or []}
    ind = industry(industry_code)
    if ind is None:
        return [{"title": t, "text": _fill(x, None)} for t, x in gen.items()]
    out: list[dict[str, str]] = []
    for p in ind["presets"][:2]:
        if p["title"] in gen:
            out.append({"title": p["title"], "text": _fill(gen[p["title"]], ind)})
        else:
            out.append({"title": p["title"], "text": "\n".join(f"{step}. …" for step in p["flow"])})
    out.append({"title": "장애 발생 상황", "text": _fill(gen["장애 발생 상황"], ind)})
    return out
