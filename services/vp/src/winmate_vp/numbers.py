"""수치 규칙(05-vp.md §4.12 · §4.17) — NumberValue · 기대 효과 지표 · EF 자동 전환 · 투자 회수 · 고객 데이터 요청 초안.

모두 결정적이다. 값이 없으면 `[00]`(단위 유지), 추정은 `[추정]`, 확정 전 문구는 `[확인 필요]`.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from winmate_common.ids import new_id

from . import config
from .decide import josa

USABLE = ("secured", "estimated")
STATUS_LABEL = {"secured": "확보", "estimated": "추정", "ask": "선택 필요"}
OPTIONS = ["요청하기", "업종 평균", "빼기"]
HANDLING_OF = {"요청하기": "request", "업종 평균": "industry_avg", "빼기": "exclude"}


def nv(display: str, status: str, *, value: float | None = None, value2: float | None = None, unit: str | None = None,
       source: dict[str, Any] | None = None, basis: str | None = None) -> dict[str, Any]:
    return {"display": display, "value": value, "value2": value2, "unit": unit, "status": status, "source": source,
            "estimate_basis": basis}


def placeholder(unit: str | None = None, shape: str = "[00]") -> str:
    return f"{shape}{unit or ''}"


def missing(unit: str | None = None, shape: str = "[00]") -> dict[str, Any]:
    return nv(placeholder(unit, shape), "missing", unit=unit)


def fmt_num(v: float) -> str:
    if v is None:
        return ""
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v)):,}"
    return f"{v:,.1f}".rstrip("0").rstrip(".")


def range_display(lo: float, hi: float, unit: str = "") -> str:
    if abs(lo - hi) < 1e-9:
        return f"{fmt_num(lo)}{unit}"
    return f"{fmt_num(lo)}~{fmt_num(hi)}{unit}"


_NUM_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)")


def parse_display(text: str) -> tuple[float | None, float | None, str]:
    """'3~5초' → (3, 5, '초'), '12초' → (12, None, '초'), '[00]시간' → (None, None, '시간')."""
    t = (text or "").strip()
    if t.startswith("["):
        return None, None, re.sub(r"^\[[^\]]*\]", "", t)
    nums = _NUM_RE.findall(t)
    unit = _NUM_RE.sub("", t).replace("~", "").replace("–", "").strip()
    vals = [float(n.replace(",", "")) for n in nums]
    if not vals:
        return None, None, unit
    return vals[0], (vals[1] if len(vals) > 1 else None), unit


# ── 기대 효과 지표(Metric) ──────────────────────────────────

def metric_status(m: dict[str, Any]) -> str:
    """secured · estimated · ask(비어 있고 처리 미정) · requested · excluded."""
    h = m.get("handling")
    if h == "exclude":
        return "excluded"
    b, a = (m.get("before") or {}).get("status"), (m.get("after") or {}).get("status")
    if b in USABLE and a in USABLE:
        return "estimated" if "estimated" in (a, b) else "secured"
    if h == "request":
        return "requested"
    return "ask"


def decorate(m: dict[str, Any]) -> dict[str, Any]:
    """화면용 status · status_label · how · options."""
    st = metric_status(m)
    m["state"] = st
    if st in ("secured", "estimated"):
        m["status"] = st
        m["status_label"] = STATUS_LABEL[st]
        m["options"] = []
        if not m.get("how"):
            m["how"] = "그대로 사용" if st == "secured" else "[추정] 표시"
    elif st == "excluded":
        m["status"] = "excluded"
        m["status_label"] = "빼기"
        m["options"] = []
        m["how"] = "기대 효과에서 뺐어요"
    elif st == "requested":
        m["status"] = "requested"
        m["status_label"] = "요청"
        m["options"] = []
        m["how"] = "고객에게 요청 · 답이 오면 바꿔요"
    else:
        m["status"] = "ask"
        m["status_label"] = STATUS_LABEL["ask"]
        m["options"] = list(OPTIONS)
        m["how"] = ""
    return m


def recommended_handling(m: dict[str, Any]) -> str:
    """미결 행의 추천 처리 — 업종 평균을 계산할 수 있으면 `industry_avg`, 아니면 `request`(§4.12)."""
    return "industry_avg" if m.get("industry_avg") else "request"


def projected_usable(m: dict[str, Any]) -> str | None:
    """반영했을 때의 상태(secured · estimated · None)."""
    st = metric_status(m)
    if st in USABLE:
        return st
    if st == "ask":
        return "estimated" if recommended_handling(m) == "industry_avg" else None
    if m.get("handling") == "industry_avg" and m.get("industry_avg"):
        return "estimated"
    return None


def counts(metrics: list[dict[str, Any]]) -> dict[str, int]:
    sts = [metric_status(m) for m in metrics]
    return {"total": len(metrics), "secured": sts.count("secured"), "estimated": sts.count("estimated"),
            "missing": sum(1 for s in sts if s in ("ask", "requested"))}


def rule(metrics: list[dict[str, Any]], current: str) -> dict[str, Any]:
    """자동 전환 규칙(§4.12) — `지금 확보 {a} + 추정 {b} = {u} → {코드} 유지` + (어떤 미결 지표를 빼면 u < 3 일 때만) 꼬리."""
    nmin = int(config.th("numbers_min"))
    proj = [projected_usable(m) for m in metrics]
    a, b = proj.count("secured"), proj.count("estimated")
    u = a + b
    cur = current if current in ("EF-A", "EF-C") else current
    switch: str | None = None
    if cur == "EF-A" and u < nmin:
        switch = "EF-C"
    elif cur == "EF-C" and u >= nmin:
        switch = "EF-A"
    head = f"지금 확보 {a} + 추정 {b} = {u} → " + (f"{switch}로 바뀌어요" if switch else f"{cur} 유지")
    tail = None
    if not switch and cur == "EF-A":
        for m, pu in zip(metrics, proj):
            if metric_status(m) == "ask" and pu and u - 1 < nmin:
                tail = f"'{m['label']}'{josa(m['label'], '을', '를')} 빼면 EF-C로 바뀌어요"
                break
    text = head + (f" · {tail}" if tail else "")
    return {"usable": u, "secured": a, "estimated": b, "current": cur, "would_switch_to": switch, "tail": tail, "text": text}


def apply_defaults(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """`이대로 반영` — 미결 행을 추천 처리로(업종 평균 → [추정], 못 하면 요청하기)."""
    for m in metrics:
        if metric_status(m) == "ask":
            h = recommended_handling(m)
            m["handling"] = h
            m["decided_by"] = "default"
            if h == "industry_avg":
                use_industry_avg(m)
        decorate(m)
    return metrics


def use_industry_avg(m: dict[str, Any]) -> None:
    avg = m.get("industry_avg") or {}
    unit = avg.get("unit") or (m.get("before") or {}).get("unit") or ""
    basis = avg.get("basis") or "업종 평균 범위"
    for side in ("before", "after"):
        cur = m.get(side) or {}
        if cur.get("status") in USABLE:
            continue
        rng = avg.get(side)
        if rng:
            m[side] = nv(f"{range_display(rng[0], rng[1], unit)} [추정]", "estimated", value=rng[0], value2=rng[1], unit=unit,
                         source={"kind": "industry_avg", "label": basis, "refs": avg.get("refs") or []}, basis=basis)
        else:
            m[side] = nv(placeholder(unit), "missing", unit=unit)
    if (m.get("before") or {}).get("status") in USABLE and (m.get("after") or {}).get("status") in USABLE:
        m["source_label"] = "없음 → 업종 평균"
        m["how"] = f"{basis} · [추정] 표시"


def new_metric(label: str, before: dict[str, Any], after: dict[str, Any], *, source_label: str, how: str = "",
               industry_avg: dict[str, Any] | None = None, material_id: str | None = None) -> dict[str, Any]:
    return decorate({"id": new_id("vmt"), "label": label, "before": before, "after": after, "source_label": source_label,
                     "handling": None, "how": how, "industry_avg": industry_avg, "material_id": material_id})


# ── 투자 회수(EF-B) ─────────────────────────────────────────

def roi(investment: float, savings: list[float]) -> list[float]:
    """회수 기간(개월) = I ÷ (S / 12) — 절감액 범위 3개 시나리오(§4.17-5)."""
    out = []
    for s in savings[:3]:
        out.append(round(investment / (s / 12), 1) if s and s > 0 else 0.0)
    return out


def savings_scenarios(lo: float, hi: float) -> list[float]:
    """절감액 범위 → [낮음, 중간, 높음]."""
    return [lo, round((lo + hi) / 2, 2), hi]


# ── 고객 데이터 요청 초안(§4.12) ────────────────────────────

def join_ko(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    head = ", ".join(items[:-1])
    return f"{head}{josa(items[-2], '과', '와')} {items[-1]}"


def data_request(metrics: list[dict[str, Any]], team: str | None) -> dict[str, Any]:
    """대상 지표 = 처리 `요청하기` · 미결 + `추정` 행(§4.12)."""
    targets = ([m["label"] for m in metrics if metric_status(m) in ("requested", "ask")]
               + [m["label"] for m in metrics if metric_status(m) == "estimated"])
    to = f"{team}께" if team else "담당자께"
    lst = join_ko(targets) or "기대 효과 지표"
    text = (f"{to} — 최근 3개월 {lst}{josa(targets[-1] if targets else '지표', '을', '를')} 알려 주시면, "
            "제안서의 기대 효과를 추정치가 아닌 실제 수치로 바꿔 드리겠습니다.")
    subject = "기대 효과 수치 요청"
    return {"text": text, "to_hint": team or "담당자", "mailto": f"mailto:?subject={quote(subject)}&body={quote(text)}", "targets": targets}


def money_ko(v: float | None) -> str:
    """원 → `3.2억 원` · `1,200만 원` · `[00]억 원`(없으면)."""
    if not v:
        return "[00]억 원"
    if v >= 100000000:
        return f"{fmt_num(round(v / 100000000, 1))}억 원"
    if v >= 10000:
        return f"{fmt_num(round(v / 10000))}만 원"
    return f"{fmt_num(v)}원"
