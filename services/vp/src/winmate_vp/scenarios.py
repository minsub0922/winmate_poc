"""라우팅 시나리오 12(VPC — 05-vp.md §3.7 · §9.12) — 플래너 + 질문 판정을 한 번에 돌리는 결정적 합성.

`run_case(fixture)` 는 워크플로가 쓰는 것과 같은 함수(decide · numbers · planner)를 쓴다.
픽스처: services/vp/tests/fixtures/vpc/{no}.json (재료 신호 + 기대값).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import catalog, decide, numbers
from .planner import PlannerInput, plan_of

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "vpc"

# 사람에게 물은 것 — 대표 하나(심각한 것 먼저)
ASK_ORDER = ("direction", "industry", "sb_mi_conflict", "metric", "approver", "investment", "km_bundle", "data_request",
             "pack_offer", "pinned")
ASK_LABEL = {
    "direction": "첫 메시지 방향", "industry": "업종", "sb_mi_conflict": "Storyboard ↔ MI 충돌", "approver": "결재자 · 기본값 있음",
    "investment": "투자비 → {label}로 계산", "km_bundle": "Key Message {n} → 4로 묶음", "data_request": "고객 데이터 요청 초안",
    "pack_offer": "업종판으로 바꿀지", "pinned": "없음 · 고정 {n}는 그대로",
}


def _nv(status: str) -> dict[str, Any]:
    if status in ("secured", "estimated"):
        return numbers.nv("1", status, value=1)
    return numbers.missing()


def metrics_from(fx: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for m in fx.get("metrics") or []:
        met = numbers.new_metric(m["label"], _nv(m.get("before", "secured")), _nv(m.get("after", "secured")),
                                 source_label=m.get("source", ""),
                                 industry_avg=({"before": [1, 2], "after": [1, 2], "unit": "", "basis": "업종 평균"}
                                               if m.get("industry_avg") else None))
        out.append(met)
    return out


def run_case(fx: dict[str, Any]) -> dict[str, Any]:
    pack_status = {fx["industry"].get("code_for_pack", ""): "ready"} if fx.get("pack_ready") else {}
    ind_in = fx.get("industry") or {}
    industry = decide.decide_industry(pinned=ind_in.get("pinned"), inherited=ind_in.get("inherited"),
                                      candidates=ind_in.get("candidates"), pack_status=None)
    if fx.get("pack_ready"):
        pack_status = {industry["code"]: "ready"}
    pin = dict(fx.get("planner") or {})
    metrics = metrics_from(fx)
    if metrics:
        proj = [numbers.projected_usable(m) for m in metrics]
        pin["usable_numbers"] = sum(1 for p in proj if p)
        pin["estimated_numbers"] = sum(1 for p in proj if p == "estimated")
    pin["industry_code"] = industry["code"] if industry["code"] != "GEN" else None
    pin["pack_ready"] = bool(pack_status.get(industry["code"]) == "ready")
    p = PlannerInput.from_dict(pin)
    if decide.needs_direction(p.themes) and not p.direction_answer:
        p.direction_open = True
    sig = fx.get("signals") or {}
    qs = decide.detect_questions(p, industry=industry, approver_unknown=bool(sig.get("approver_unknown")),
                                 has_rfp=bool(sig.get("has_rfp")), conflict=sig.get("conflict"))
    plan = plan_of(p)
    asks: list[dict[str, Any]] = []
    for q in qs:
        asks.append({"kind": q["kind"], "mode": q["mode"], "label": ASK_LABEL.get(q["kind"], q["kind"])})
    for m in metrics:
        if numbers.metric_status(m) == "ask" and not numbers.projected_usable(m):
            asks.append({"kind": "metric", "mode": "ask", "label": f"{m['label']}을 어떻게 채울지"})
    for d in plan["decisions"]:
        if d["mode"] != "check":
            continue
        if d["key"] == "투자비" and "연결된" in d["text"]:
            asks.append({"kind": "investment", "mode": "check", "label": ASK_LABEL["investment"].format(label=p.investment_label)})
        elif d["key"] == "Key Message":
            asks.append({"kind": "km_bundle", "mode": "check", "label": ASK_LABEL["km_bundle"].format(n=p.km_count)})
    ef = next((s for s in plan["sheets"] if s["role"] == "EF"), None)
    if ef and ef.get("tail") == "업종 평균":
        asks.append({"kind": "data_request", "mode": "check", "label": ASK_LABEL["data_request"]})
    if pin["pack_ready"] and fx.get("existing_work"):
        asks.append({"kind": "pack_offer", "mode": "check", "label": ASK_LABEL["pack_offer"]})
    if p.clone and p.pinned:
        asks.append({"kind": "pinned", "mode": "pin", "label": ASK_LABEL["pinned"].format(n=len(p.pinned))})
    asks.sort(key=lambda a: ASK_ORDER.index(a["kind"]))
    primary = asks[0] if asks else None
    return {
        "no": fx.get("no"), "name": fx.get("name"), "input": fx.get("input"), "flow_label": plan["flow_label"],
        "chips": [c["t"] for c in plan["chips"]], "chip_kinds": [c["kind"] for c in plan["chips"]],
        "industry": industry, "asked": primary, "asks": asks, "plan": plan, "questions": qs,
        "pack": "업종판 준비됨 → 교체 제안" if pin["pack_ready"] else ("업종판 제작 중 → 범용" if industry["code"] != "GEN" else "범용"),
    }


def load_fixtures() -> list[dict[str, Any]]:
    out = []
    if not FIXTURE_DIR.exists():
        return out
    for p in sorted(FIXTURE_DIR.glob("*.json"), key=lambda x: int(x.stem) if x.stem.isdigit() else 99):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def stats(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    """VPC 통계 4(보드 로직 그대로)."""
    no_ask = sum(1 for r in results if not r["asked"] or r["asked"]["mode"] == "pin")
    asked = sum(1 for r in results if r["asked"] and r["asked"]["mode"] == "ask")
    uniq: set[str] = set()
    for r in results:
        for c in r["chips"]:
            t = c.replace("#", "").replace("*", "").split(" ")[0]
            if catalog.entry(t) is not None and t[:2].isalpha() and "-" in t:
                uniq.add(catalog.norm(t))
    n = len(results) or 12
    return [
        {"n": f"{no_ask}/{n}", "t": "사람에게 묻지 않고 끝난 케이스 — 고정한 시트를 그대로 둔 복제 포함"},
        {"n": f"{asked}/{n}", "t": "'선택 필요'로 멈춘 케이스 — 방향 두 갈래 · 채울 수 없는 수치"},
        {"n": f"{len(uniq)}종", "t": "12개 케이스에서 쓰인 레이아웃 — 같은 재료 틀, 다른 결과"},
        {"n": "0/16", "t": "Value Props 업종판 준비 수 · 출시되면 12번처럼 교체 제안"},
    ]
