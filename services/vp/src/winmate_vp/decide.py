"""결정적 판정 — 업종(§3.3 단계 2) · 되묻기 질문(§3.4 · §4.7). LLM 없음.

비교 정밀도: 확신도 · 점수는 소수 둘째 자리로 반올림한 뒤 100배 정수로 비교한다(MI §3.3 와 같음 — 0.85 − 0.75 를 0.0999 로 보지 않게).
"""
from __future__ import annotations

from typing import Any

from winmate_common.ids import new_id

from . import config
from .planner import PlannerInput, Theme, direction_previews

KO_NUM = {1: "한", 2: "두", 3: "세", 4: "네", 5: "다섯", 6: "여섯", 7: "일곱", 8: "여덟"}


def pct(x: float | None) -> int:
    return int(round(float(x or 0) * 100))


def fmt2(x: float | None) -> str:
    return f"{float(x or 0):.2f}"


def pack_meta(code: str | None, pack_status: dict[str, str] | None) -> dict[str, str]:
    if not code or code == "GEN":
        return {"status": "in_production", "label": "범용"}
    st = (pack_status or {}).get(code, "in_production")
    return {"status": st, "label": "업종판 준비됨" if st == "ready" else "업종판 제작 중 → 범용"}


def industry_obj(code: str | None, *, source: str, mode: str, confidence: float | None = None,
                 top2: list[dict[str, Any]] | None = None, pack_status: dict[str, str] | None = None,
                 kr_vertical_id: str | None = None, inherited_from: str | None = None) -> dict[str, Any]:
    meta = config.industry(code)
    c = meta.get("code") or "GEN"
    return {"code": c, "name": meta["name"], "cell": meta.get("cell", meta["name"]), "source": source, "mode": mode,
            "confidence": confidence, "top2": top2, "kr_vertical_id": kr_vertical_id or ((meta.get("kr") or [None])[0]),
            "pack": pack_meta(c, pack_status), "inherited_from": inherited_from}


def decide_industry(*, pinned: str | None = None, inherited: dict[str, Any] | None = None,
                    candidates: list[dict[str, Any]] | None = None, pack_status: dict[str, str] | None = None) -> dict[str, Any]:
    """평가 순서 ① 사람이 정함(pin) ② 상속(auto) ③ 1위 < 0.50 → 범용 ④ 1 · 2위 차 < 0.10 → ask ⑤ ≥ 0.80 auto ⑥ 그 밖 check."""
    if pinned:
        return industry_obj(pinned, source="user", mode="pin", pack_status=pack_status)
    if inherited and inherited.get("code") and inherited["code"] in config.INDUSTRY_CODES:
        return industry_obj(inherited["code"], source=inherited.get("source", "mi"), mode="auto", pack_status=pack_status,
                            inherited_from=inherited.get("label"))
    cands = sorted([c for c in candidates or [] if c.get("code")], key=lambda c: -float(c.get("confidence") or 0))
    top2 = [{"code": c["code"], "score": round(float(c.get("confidence") or 0), 2)} for c in cands[:2]]
    if not cands:
        return industry_obj("GEN", source="classified", mode="auto", confidence=None, top2=[], pack_status=pack_status)
    s1 = pct(cands[0].get("confidence"))
    s2 = pct(cands[1].get("confidence")) if len(cands) > 1 else 0
    code = cands[0]["code"]
    if s1 < pct(config.th("industry_min")) or code not in config.INDUSTRY_CODES:
        return industry_obj("GEN", source="classified", mode="auto", confidence=s1 / 100, top2=top2, pack_status=pack_status)
    if len(cands) > 1 and s1 - s2 < pct(config.th("industry_ask_margin")) and cands[1]["code"] in config.INDUSTRY_CODES:
        return industry_obj(code, source="classified", mode="ask", confidence=s1 / 100, top2=top2, pack_status=pack_status)
    if s1 >= pct(config.th("industry_auto")):
        return industry_obj(code, source="classified", mode="auto", confidence=s1 / 100, top2=top2, pack_status=pack_status)
    return industry_obj(code, source="classified", mode="check", confidence=s1 / 100, top2=top2, pack_status=pack_status)


def industry_caption(ind: dict[str, Any] | None) -> str:
    """VP1 업종 칸 캡션(`업종 · 연결한 MI에서 상속`)."""
    if not ind:
        return "업종"
    src = ind.get("source")
    if ind.get("mode") == "pin" or src == "user":
        return "업종 · 직접 고름"
    if src == "mi":
        return "업종 · 연결한 MI에서 상속"
    if src == "storyboard":
        return "업종 · Storyboard에서 상속"
    if src in ("proposal", "requirements"):
        return "업종 · 연결한 자료에서 상속"
    return "업종 · 자동 판별"


# ── 질문(§3.4) ────────────────────────────────────────────

def _q(no: int, kind: str, mode: str, title: str, aside: str, options: list[dict[str, Any]], default_keys: list[str], *,
       multi: bool = False, context_text: str | None = None, hint: str | None = None) -> dict[str, Any]:
    return {"id": new_id("vqn"), "no": no, "kind": kind, "mode": mode, "title": f"{no} · {title}", "aside": aside,
            "context_text": context_text, "multi": multi, "options": options, "default_keys": default_keys, "hint": hint,
            "answer": None, "status": "open"}


def direction_question(no: int, p: PlannerInput, *, context_text: str | None = None,
                       first_messages: dict[str, str] | None = None) -> dict[str, Any]:
    """질문 1 · 방향(선택 필요) — 선택지 순서는 점수 순(① 1위 먼저 · ② 2위 먼저 · ③ 둘 다(추천))."""
    themes = sorted(p.themes, key=lambda t: -t.score)[:2]
    prev = {x["key"]: x for x in direction_previews(p)}
    fm = first_messages or {}
    opts = []
    for i, t in enumerate(themes):
        pv = prev[t.kind]
        opts.append({"key": t.kind, "label": f"{'①②'[i]} {t.label} 먼저", "desc": fm.get(t.kind) or f"'{t.label}'을 첫 메시지로",
                     "recommended": False, "preview": {"code": pv["code"], "display": pv["display"], "thumb": pv["thumb"],
                                                       "effect": pv["effect"]}})
    pv = prev["both"]
    l1, l2 = (themes[0].label, themes[1].label) if len(themes) > 1 else ("매출", "비용")
    opts.append({"key": "both", "label": "③ 둘 다", "desc": fm.get("both") or f"{l1}{josa(l1, '과', '와')} {l2}{josa(l2, '을', '를')} 나란히 — 경영진이 둘 다 볼 수 있게",
                 "recommended": True, "preview": {"code": pv["code"], "display": pv["display"], "thumb": pv["thumb"], "effect": pv["effect"]}})
    aside = " : ".join(f"{t.label} {fmt2(t.score)}" for t in themes) + " · 차이 0.10 미만"
    return _q(no, "direction", "ask", "이번 제안의 첫 메시지는?", aside, opts, ["both"], context_text=context_text)


def approver_question(no: int, industry: dict[str, Any] | None, *, has_rfp: bool) -> dict[str, Any]:
    meta = config.industry((industry or {}).get("code"))
    cell = meta.get("cell", meta["name"])
    opts = [{"key": a, "label": a, "recommended": a in meta.get("approver_default", [])} for a in meta.get("approvers", [])]
    aside = (f"RFP가 없어 {cell} 사례 기준으로 기본값을 뒀어요" if not has_rfp
             else f"결재 정보가 없어 {cell} 사례 기준으로 기본값을 뒀어요")
    return _q(no, "approver", "check", "누가 결재하나요?", aside, opts, list(meta.get("approver_default", [])), multi=True,
              hint="2명 이상이면 VP-H 이해관계자형으로")


def industry_question(no: int, industry: dict[str, Any]) -> dict[str, Any]:
    top2 = industry.get("top2") or []
    opts = []
    for i, t in enumerate(top2[:2]):
        meta = config.industry(t["code"])
        opts.append({"key": t["code"], "label": meta["name"], "recommended": i == 0})
    opts.append({"key": "GEN", "label": "범용", "recommended": False})
    aside = " : ".join(f"{config.industry(t['code'])['cell']} {fmt2(t['score'])}" for t in top2[:2]) + " · 차이 0.10 미만"
    return _q(no, "industry", "ask", "어느 업종으로 볼까요?", aside, opts, [top2[0]["code"]] if top2 else ["GEN"])


def conflict_question(no: int, summary: str) -> dict[str, Any]:
    opts = [{"key": "sb", "label": "Storyboard 기준", "recommended": False},
            {"key": "mi", "label": "MI 기준", "recommended": False},
            {"key": "both", "label": "둘 다 살려 고쳐 쓰기", "recommended": True}]
    return _q(no, "sb_mi_conflict", "ask", "Storyboard Key Message와 MI 과제가 부딪쳐요", summary, opts, ["both"])


def direction_gap(themes: list[Theme]) -> int | None:
    ts = sorted(themes, key=lambda t: -t.score)
    if len(ts) < 2:
        return None
    return pct(ts[0].score) - pct(ts[1].score)


def needs_direction(themes: list[Theme]) -> bool:
    gap = direction_gap(themes)
    kinds = {t.kind for t in sorted(themes, key=lambda t: -t.score)[:2]}
    return gap is not None and gap < pct(config.th("direction_ask_margin")) and kinds == {"gain", "cost"}


def detect_questions(p: PlannerInput, *, industry: dict[str, Any] | None, approver_unknown: bool, has_rfp: bool,
                     conflict: str | None = None, direction_context: str | None = None,
                     first_messages: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """열린 질문 목록(번호 순). 방향 → 결재자 → 업종 → SB ↔ MI 충돌."""
    out: list[dict[str, Any]] = []
    if needs_direction(p.themes):
        out.append(direction_question(len(out) + 1, p, context_text=direction_context, first_messages=first_messages))
    if approver_unknown:
        out.append(approver_question(len(out) + 1, industry, has_rfp=has_rfp))
    if industry and industry.get("mode") == "ask":
        out.append(industry_question(len(out) + 1, industry))
    if conflict:
        out.append(conflict_question(len(out) + 1, conflict))
    return out


def questions_intro(n_questions: int, n_auto: int) -> str:
    q = KO_NUM.get(n_questions, str(n_questions))
    return f"{q} 가지만 확인할게요. 나머지 {n_auto}개는 정한 대로 진행합니다."


def default_summary(questions: list[dict[str, Any]]) -> str:
    """`답이 없으면 ③ 둘 다 · 운영본부장으로 진행하고, 결과에서 언제든 바꿀 수 있어요.`"""
    parts = []
    for q in questions:
        keys = q.get("default_keys") or []
        labels = [o["label"] for o in q.get("options") or [] if o["key"] in keys]
        if labels:
            parts.append(" · ".join(labels))
    if not parts:
        return "답이 없으면 추천값으로 진행하고, 결과에서 언제든 바꿀 수 있어요."
    last = parts[-1]
    return f"답이 없으면 {' · '.join(parts)}{josa(last, '으로', '로')} 진행하고, 결과에서 언제든 바꿀 수 있어요."


# ── 한국어 조사 ────────────────────────────────────────────

def has_batchim(word: str) -> bool | None:
    w = (word or "").strip().rstrip(")]'\"’”")
    if not w:
        return None
    ch = w[-1]
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28 != 0
    if ch.isdigit():
        return ch in "013678"
    if ch.isalpha():
        return ch.lower() in "lmnr"
    return None


def josa(word: str, with_batchim: str, without: str) -> str:
    """josa('오출고율', '과', '와') → '과'. '으로/로' 는 ㄹ 받침이면 '로'."""
    w = (word or "").strip()
    b = has_batchim(w)
    if b is None:
        return without
    if with_batchim == "으로" and w and "가" <= w[-1] <= "힣" and (ord(w[-1]) - 0xAC00) % 28 == 8:
        return without
    return with_batchim if b else without
