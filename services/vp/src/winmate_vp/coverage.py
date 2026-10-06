"""재료 커버리지 4축(05-vp.md §4.5 · §7.3) — 결정적 계산(LLM 없음).

percent = min(100, round(100 × 가진 수 / 필요 수)) (제안)
- 과제: 필요 3 · 가진 = 과제 재료 수
- 가치: 필요 = KM 수(없으면 3) · 가진 = 가치 재료 수(KM + 삼성 강점 …)
- 근거 수치: 필요 = 수치 칸 수(전 → 후 지표 = 2칸, 단일 수치 = 1칸) · 가진 = 확보 + 추정 칸
- 이해관계자: 결재 40 · 운영 20 · 이용자 40 가중 합(제안)
수준: ≥ 90 `충분` · ≥ 50 `보통` · < 50 `부족`(제안 경계)
"""
from __future__ import annotations

from typing import Any

from . import config

AXES = (("challenge", "과제"), ("value", "가치"), ("evidence", "근거 수치"), ("stakeholder", "이해관계자"))
FILLED = ("secured", "estimated")


def level(percent: int) -> str:
    if percent >= int(config.th("coverage_full")):
        return "충분"
    if percent >= int(config.th("coverage_mid")):
        return "보통"
    return "부족"


def group_of(label: str, *, approver: bool = False) -> str:
    """이해관계자 묶음 — approver · operator · user(키워드, 결재 표시가 있으면 approver)."""
    if approver:
        return "approver"
    groups = config.routing()["stakeholder_groups"]
    text = label or ""
    for key in ("approver", "user", "operator"):
        if any(w in text for w in groups[key]["words"]):
            return key
    return "operator"


def _active(items: list[dict[str, Any]], axis: str) -> list[dict[str, Any]]:
    return [m for m in items if m.get("axis") == axis and not m.get("excluded")]


def number_slots(items: list[dict[str, Any]]) -> tuple[int, int]:
    """(필요 칸, 채운 칸)."""
    need = have = 0
    for m in _active(items, "evidence"):
        met = m.get("metric")
        if met:
            for side in ("before", "after"):
                need += 1
                if ((met.get(side) or {}).get("status")) in FILLED:
                    have += 1
        else:
            need += 1
            if ((m.get("number") or {}).get("status")) in FILLED:
                have += 1
    return need, have


def stakeholder_groups(items: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"approver": [], "operator": [], "user": []}
    for m in _active(items, "stakeholder"):
        g = m.get("group") or group_of(m.get("text", ""), approver=bool(m.get("approver")))
        out.setdefault(g, []).append(m)  # type: ignore[arg-type]
    return out  # type: ignore[return-value]


def compute(items: list[dict[str, Any]], *, km_count: int = 0, strengths: int = 0, mi_users: list[str] | None = None,
            memo_only: bool = False) -> list[dict[str, Any]]:
    """CoverageAxis[4]."""
    out = []
    # 과제
    ch = _active(items, "challenge")
    cost = sum(1 for m in ch if m.get("cost"))
    p = min(100, round(100 * len(ch) / 3))
    if not ch:
        summary = "아직 없어요"
        todo = "사례 DB로 과제를 추론해요" if memo_only else "RFP를 올리면 과제를 바로 읽어요"
    else:
        summary = f"{len(ch)}개 · 비용 수치가 붙은 것 {cost}"
        todo = "그대로 사용" if p >= int(config.th("coverage_full")) else f"{3 - len(ch)}개는 사례 DB로 보완해요"
    out.append({"axis": "challenge", "label": "과제", "percent": p, "summary": summary, "level": level(p), "todo": todo})
    # 가치
    va = _active(items, "value")
    need = km_count if km_count > 0 else 3
    p = min(100, round(100 * len(va) / need)) if need else 0
    if km_count or strengths:
        summary = " · ".join(x for x in (f"Key Message {km_count}" if km_count else "", f"삼성 강점 {strengths}" if strengths else "") if x)
    else:
        summary = f"{len(va)}개" if va else "아직 없어요"
    if p >= int(config.th("coverage_full")):
        n = min(km_count or len(va), int(config.th("km_max")))
        todo = f"KM {km_count} → 가치 기둥 {n} 후보" if km_count else f"가치 {len(va)} → 기둥 {min(len(va), 4)} 후보"
    else:
        todo = "삼성 강점 · 메시지 DB에서 채워요"
    out.append({"axis": "value", "label": "가치", "percent": p, "summary": summary, "level": level(p), "todo": todo})
    # 근거 수치
    need_n, have_n = number_slots(items)
    p = min(100, round(100 * have_n / need_n)) if need_n else 0
    missing = need_n - have_n
    if need_n == 0:
        summary, todo = "수치 없음", "만들 때 사례 DB에서 찾아 채워요"
    else:
        summary = f"{have_n} / {need_n}" + (f" · 전 → 후 값 {missing}개 비어 있음" if missing else "")
        todo = "만들 때 사례 DB에서 찾아 채워요" if missing else "그대로 사용"
    out.append({"axis": "evidence", "label": "근거 수치", "percent": p, "summary": summary, "level": level(p), "todo": todo})
    # 이해관계자
    groups = config.routing()["stakeholder_groups"]
    sg = stakeholder_groups(items)
    p = sum(int(groups[g]["weight"]) for g in ("approver", "operator", "user") if sg.get(g))
    p = min(100, p)
    labels = []
    for g in ("approver", "operator", "user"):
        for m in sg.get(g, []):
            t = m.get("text", "")  # type: ignore[union-attr]
            labels.append(f"{t}(결재)" if g == "approver" and "결재" not in t else t)
    summary = " · ".join(labels[:4]) if labels else "아직 없어요"
    if not sg.get("user"):
        user_role = next((u for u in (mi_users or []) if group_of(u) == "user"), None)
        todo = f"{user_role} 관점은 MI 사용자에서 가져와요" if user_role else "이용자 관점은 사례에서 찾아요"
    elif not sg.get("approver"):
        todo = "결재자는 업종 기본값으로 두고 확인해요"
    else:
        todo = "그대로 사용"
    out.append({"axis": "stakeholder", "label": "이해관계자", "percent": p, "summary": summary, "level": level(p), "todo": todo})
    return out
