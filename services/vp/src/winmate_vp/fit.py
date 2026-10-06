"""레이아웃 적합도(05-vp.md §4.15.5) — `필요한 데이터가 있는지로 적합도를 매겨요`.

fit = round(100 × Σ wᵢ·sᵢ / Σ wᵢ), sᵢ ∈ [0, 1] — 개수 요구는 비율(부분 점수), strict 요구는 0/1. LLM 없음.
업종판 제작 중은 fit = −1(`준비 중`, 고를 수 없음). 강조 임계 85.
"""
from __future__ import annotations

from typing import Any

from . import catalog, config

KO_COUNT = {1: "하나", 2: "둘", 3: "셋", 4: "넷"}


def score(code: str, f: dict[str, Any], *, pack_status: dict[str, str] | None = None) -> int:
    e = catalog.entry(code)
    if e is None:
        return 0
    if e.get("industry_code"):
        return 100 if (pack_status or {}).get(e["industry_code"]) == "ready" else -1
    needs = e.get("needs") or []
    if not needs:
        return 50
    tot = sum(float(n.get("w", 1)) for n in needs)
    acc = 0.0
    for n in needs:
        v = f.get(n["key"])
        if n.get("strict"):
            s = 1.0 if v else 0.0
        else:
            need = float(n.get("min", 1)) or 1.0
            s = min(1.0, float(v or 0) / need)
        acc += float(n.get("w", 1)) * s
    return int(round(100 * acc / tot)) if tot else 0


def _met(code: str, f: dict[str, Any]) -> bool:
    e = catalog.entry(code) or {}
    for n in e.get("needs") or []:
        v = f.get(n["key"])
        if n.get("strict") and not v:
            return False
        if not n.get("strict") and float(v or 0) < float(n.get("min", 1)):
            return False
    return True


def why(code: str, f: dict[str, Any], *, current: str | None = None, pack_status: dict[str, str] | None = None) -> str:
    e = catalog.entry(code) or {}
    if e.get("industry_code"):
        return "업종판 준비됨" if (pack_status or {}).get(e["industry_code"]) == "ready" else "업종판 제작 중 · 출시 알림 켜짐"
    cur = catalog.norm(current) if current else None
    if cur and catalog.norm(code) != cur and catalog.twin(cur) and catalog.norm(catalog.twin(cur) or "") == catalog.norm(code) \
            and e.get("board") == "text":
        return "이미지 없이 — 지금과 같은 구성"
    tpl = (e.get("why") or {}).get("met" if _met(code, f) else "unmet", "")
    pillars = int(e.get("pillars") or 0)
    lack = max(0, pillars - int(f.get("values") or 0))
    fmt = {**{k: (int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in f.items()},
           "lack": KO_COUNT.get(lack, f"{lack}개")}
    try:
        text = tpl.format(**fmt)
    except (KeyError, ValueError):
        text = tpl
    if not int(f.get("km") or 0) and "Key Message 0" in text:  # Storyboard 없이 — 모은 가치 수로 말한다
        text = text.replace("Key Message 0", f"가치 {int(f.get('values') or 0)}")
    if catalog.norm(code) == "VP-M" and cur in ("VP-H", "VP-D"):
        text += " — 역할은 빠짐"
    if cur and catalog.norm(code) == cur:
        text += " — 지금"
    return text


def _vp_pool(n: int) -> list[str]:
    other = n + 1 if n < 4 else n - 1
    return ["VP-H", f"VP-F{n}", "VP-M", f"VP-F{other}", "VP-E", "VP-G", "VP-I", "VP-J", "VP-K", "VP-L", "VP-U"]


def candidates(role: str, f: dict[str, Any], *, current: str, requested: str | None = None, pillars: int | None = None,
               industry_code: str | None = None, pack_status: dict[str, str] | None = None, limit_image: int = 6) -> dict[str, Any]:
    """VP3L 후보 그리드 — [지금 · 요청한 것 · 적합도 순 · 이미지 없는 짝 · 업종판]."""
    cur = catalog.norm(current)
    req = catalog.norm(requested) if requested else None
    n = pillars or catalog.pillars_of(req or "") or catalog.pillars_of(cur) or 3
    if role == "VP":
        pool = _vp_pool(n)
    elif role == "CH":
        pool = ["CH-A", "CH-B", "CH-C"]
    else:
        pool = ["EF-A", "EF-B", "EF-C", "EF-D", "EF-E"]
    image_like = [c for c in pool if (catalog.entry(c) or {}).get("board") not in ("text",)]
    scored = [(c, score(c, f, pack_status=pack_status)) for c in image_like if c not in (cur, req)]
    scored.sort(key=lambda x: -x[1])
    picks: list[str] = []
    for c in (cur, req):
        if c and c not in picks:
            picks.append(c)
    n_img = limit_image if role == "VP" else len(pool)
    for c, _ in scored:
        if len([p for p in picks if (catalog.entry(p) or {}).get("board") != "text" and not catalog.is_pack(p)]) >= n_img:
            break
        picks.append(c)
    # 이미지 없는 짝 — 기둥 수를 직접 바꾸면 VP-B·n, 아니면 지금 레이아웃의 짝
    text_pick: str | None = None
    if role == "VP":
        if pillars:
            text_pick = f"VP-B{n}"
        else:
            tw = catalog.twin(cur)
            text_pick = catalog.norm(tw) if tw and (catalog.entry(tw) or {}).get("board") == "text" else f"VP-B{n}"
    if text_pick and text_pick not in picks:
        picks.append(text_pick)
    pack: str | None = None
    if industry_code and industry_code != "GEN":
        pack = catalog.pack_code(industry_code, role)
        if pack not in picks:
            picks.append(pack)
    out = []
    for c in picks:
        e = catalog.require(c)
        fit_v = score(c, f, pack_status=pack_status)
        state = "cur" if c == cur else "req" if c == req else ("no" if fit_v < 0 else "normal")
        out.append({"code": c, "display": e["display"], "thumb": catalog.thumb(c), "fit": fit_v,
                    "why": why(c, f, current=cur, pack_status=pack_status), "state": state, "family": e["family"]})
    header = {"image": sum(1 for x in out if not catalog.is_pack(x["code"]) and (catalog.entry(x["code"]) or {}).get("board") != "text"),
              "no_image": sum(1 for x in out if (catalog.entry(x["code"]) or {}).get("board") == "text"),
              "industry": sum(1 for x in out if catalog.is_pack(x["code"]))}
    return {"candidates": out, "header": header, "pillars": n}


def highlight(fit_v: int) -> bool:
    return fit_v >= int(config.th("fit_highlight"))
