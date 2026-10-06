"""업종 판별(§10.3) · 유형 추천(§10.4).

업종: kb `POST /v1/segments/classify`(16업종 점수 · 단서) + A2(KR 업종 → 16업종) 를 합친다. kb A2 단독 점수는 1위로 정규화돼
0.80 · 0.50 경계가 걸리지 않으므로(⚠Q24) 16업종 단서 점수(clue_score)와 사례 점수(kb_score) 중 큰 값을 확신도로 쓴다.
- 자동: 1위 ≥ 0.80 이고 2위와 차 ≥ 0.10 · 확인 권장: 1위 0.50~0.79 · 선택 필요: 1·2위 차 < 0.10 또는 1위 < 0.50 · 고정: 사용자가 고름
"""
from __future__ import annotations

import re
from typing import Any

from . import clients, defs

CAPABILITY_WORDS = (("원격", "원격 관리"), ("일괄", "원격 관리"), ("콘텐츠", "원격 관리"), ("에너지", "에너지 관리"),
                    ("단말", "단말 관리"), ("공조", "공조 관리"))
PRODUCT_WORDS = ("교체", "수량", "대수", "모델", "인치", "제품", "구매", "납품")
MODEL_RE = re.compile(r"\b[A-Z]{2,}[0-9]{2,}[A-Z0-9]*\b")


def detect_text(p: dict[str, Any], ctx: dict[str, Any]) -> str:
    rfp = p.get("rfp") or {}
    rfp_ind = next((f.get("value") for f in rfp.get("fields") or [] if f.get("key") == "industry"), "")
    parts = [(p.get("customer") or {}).get("name") or "", p.get("title") or "", rfp_ind or "",
             (p.get("customer") or {}).get("scale_text") or ""]
    parts += [it.get("text") or "" for it in ((ctx or {}).get("rq") or {}).get("items") or []]
    return " ".join(x for x in parts if x).strip()


async def detect(p: dict[str, Any], ctx: dict[str, Any] | None = None, *, chip_codes: list[str] | None = None) -> dict[str, Any] | None:
    """→ {code, label, score, mode, evidence[], second?}. 고객 업종을 사용자가 정했으면 pinned."""
    cust = p.get("customer") or {}
    if cust.get("industry_user_set") and cust.get("industry_code") in defs.INDUSTRIES and not chip_codes:
        code = cust["industry_code"]
        return {"code": code, "label": defs.INDUSTRIES[code]["full"], "score": 1.0, "mode": "pinned", "evidence": ["직접 선택"]}
    text = detect_text(p, ctx or {})
    if not text:
        return None
    res = await clients.kb_post("/v1/segments/classify", {"text": text[:2000]})
    items = list((res or {}).get("items") or [])
    scored = []
    for it in items:
        code = it.get("code")
        if code not in defs.INDUSTRIES:
            continue
        if chip_codes and code not in chip_codes:
            continue
        s = max(float(it.get("clue_score") or 0), float(it.get("kb_score") or 0))
        scored.append((s, code, it))
    if not scored:
        a2 = await clients.kb_query("A2", {"text": text[:2000]})
        for c in ((a2 or {}).get("result") or {}).get("top2") or []:
            codes = defs.KR_TO_CODES.get(c.get("id") or "") or []
            for code in codes:
                if chip_codes and code not in chip_codes:
                    continue
                scored.append((float(c.get("raw_score") or c.get("score") or 0), code, {"clues": [{"text": s} for s in c.get("signals") or []]}))
    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    top_s, code, top = scored[0]
    second = scored[1] if len(scored) > 1 else (0.0, None, {})
    gap = top_s - second[0]
    if gap < 0.10 or top_s < 0.50:
        mode = "ask"
    elif top_s >= 0.80:
        mode = "auto"
    else:
        mode = "check"
    return {"code": code, "label": defs.INDUSTRIES[code]["full"], "score": round(top_s, 3), "mode": mode,
            "evidence": evidence(p, top), "second": {"code": second[1], "score": round(second[0], 3)} if second[1] else None}


def evidence(p: dict[str, Any], top: dict[str, Any]) -> list[str]:
    """「근거 · 고객사명 'A 커피 프랜차이즈' · RFP p.2 '커피 전문점' · 매장 메뉴보드 320곳」"""
    out: list[str] = []
    cust = (p.get("customer") or {}).get("name") or ""
    clues = [c.get("text") for c in top.get("clues") or [] if c.get("text")]
    if cust and any(c in cust for c in clues):
        out.append(f"고객사명 '{cust}'")
    rfp = p.get("rfp") or {}
    fld = next((f for f in rfp.get("fields") or [] if f.get("key") == "industry" and f.get("source")), None)
    if fld and (fld.get("source") or {}).get("quote"):
        src = fld["source"]
        out.append(f"RFP {src.get('page_label') or ('p.' + str(src.get('page')))} '{src['quote']}'".replace("RFP p.None", "RFP"))
    scale = (p.get("customer") or {}).get("scale_text")
    if scale:
        out.append(scale)
    for c in clues:
        if len(out) >= 3:
            break
        if not any(c in x for x in out):
            out.append(f"'{c}'")
    return out[:3]


def chip_codes(chip: str | None) -> list[str] | None:
    if not chip:
        return None
    return defs.INDUSTRY_CHIPS.get(chip.strip())


# ── 유형 추천(§10.4) ───────────────────────────────────────
async def recommend_type(p: dict[str, Any], ctx: dict[str, Any]) -> dict[str, str]:
    has = (ctx or {}).get("has") or {}
    items = ((ctx or {}).get("rq") or {}).get("items") or []
    text = " ".join(it.get("text") or "" for it in items)
    if has.get("birdseye") and has.get("scenario") and p.get("start_mode") in ("works", "handoff"):
        return {"type": "standard", "reason": "조감도 · 시나리오가 있어 공간 섹션까지 채울 수 있어요."}
    spaces = 0
    sol_signals: set[str] = set()
    if text:
        a1 = await clients.kb_query("A1", {"text": text[:2000]})
        for ln in ((a1 or {}).get("result") or {}).get("links") or []:
            if ln.get("type") == "space_type":
                spaces += 1
            if ln.get("type") == "solution":
                sol_signals.add(ln.get("id") or "")
    low = text.lower()
    for code, s in defs.SOLUTIONS.items():
        if any(kw.lower() in low for kw in s.get("kw") or []):
            sol_signals.add(code)
    capability = next((cap for w, cap in CAPABILITY_WORDS if w in text), None)
    if capability:
        sol_signals.add(f"cap:{capability}")
    if has.get("birdseye") or has.get("scenario"):
        spaces = max(spaces, 1)
    if any(v.get("state") == "on" for v in ((ctx or {}).get("solutions") or {}).values()) or has.get("scenario"):
        sol_signals.add("link")
    models = MODEL_RE.findall(text)
    n_sol = len({s for s in sol_signals if not s.startswith("cap:")} or sol_signals)
    if n_sol >= 2 and spaces >= 2 and not models:
        return {"type": "solution", "reason": "요구사항이 여러 공간의 솔루션 운영 중심이라"}
    if spaces >= 1 and sol_signals:
        cap = capability or "원격 관리"
        return {"type": "standard", "reason": f"요구사항에 공간 구성과 {cap} 솔루션이 함께 있어"}
    if text and not sol_signals and any(w in text for w in PRODUCT_WORDS):
        return {"type": "quickwin", "reason": "요구사항이 제품 · 수량 중심이라"}
    return {"type": "standard", "reason": "요구사항을 모두 담을 수 있는 기본형이라"}
