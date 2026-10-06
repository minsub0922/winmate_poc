"""화면 문장 · 요약(파생 값) — VP1A · VP1Q · VP3G · VP3 의 에이전트 문장과 말풍선 요약을 데이터로 만든다(§4.6 ~ §4.10).

수는 데이터, 문장 틀은 보드 원문(없는 자리는 05-vp.md 의 제안 템플릿).
"""
from __future__ import annotations

from typing import Any

from . import catalog, decide, materials, signals

KO_NUM = decide.KO_NUM
TYPE_SHORT = {"standard": "표준", "quickwin": "퀵윈", "solution": "Solution형"}


def _connected(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in doc.get("sources") or [] if s.get("connected")]


def source_counts(doc: dict[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for s in _connected(doc):
        out[s["kind"]] = out.get(s["kind"], 0) + 1
    for a in doc.get("attachments") or []:
        out[a.get("kind") or "other"] = out.get(a.get("kind") or "other", 0) + 1
    return out


def connect_bubble(doc: dict[str, Any]) -> str:
    """VP1A 말풍선 `· Storyboard 1 · MI 1 · RFP 1 (A커피_디지털메뉴보드_RFP.pdf)`."""
    c = source_counts(doc)
    parts = []
    for k, label in (("storyboard", "Storyboard"), ("mi", "MI"), ("requirements", "요구사항"), ("case", "유관 사례"), ("vp", "이전 가치 제안")):
        if c.get(k):
            parts.append(f"{label} {c[k]}")
    rfps = [a for a in doc.get("attachments") or [] if a.get("kind") == "rfp"]
    if rfps:
        parts.append(f"RFP {len(rfps)} ({rfps[0].get('filename')})")
    for k, label in (("quote", "견적"), ("meeting_notes", "회의록"), ("customer_photo", "고객 사진")):
        if c.get(k):
            parts.append(f"{label} {c[k]}")
    if not parts and (doc.get("note") or "").strip():
        parts.append("메모")
    return " · ".join(parts)


def question_bubble(doc: dict[str, Any]) -> str:
    """VP1Q 말풍선 `· Storyboard · MI 연결 · RFP 없음`."""
    c = source_counts(doc)
    names = [label for k, label in (("storyboard", "Storyboard"), ("mi", "MI"), ("requirements", "요구사항"), ("case", "유관 사례")) if c.get(k)]
    head = f"{' · '.join(names)} 연결" if names else "연결 자료 없음"
    return f"{head} · {'RFP 있음' if c.get('rfp') else 'RFP 없음'}"


def materials_footer(doc: dict[str, Any]) -> str:
    """VP3G `재료 · 대규모 MI 6시트 · RFP 평가 기준 · 견적 v2 · 유관 사례 3`."""
    f = doc.get("facts") or {}
    parts = []
    for s in _connected(doc):
        if s["kind"] == "storyboard":
            n = (s.get("gives") or {}).get("counts", {}).get("km") or 0
            parts.append(f"Storyboard KM {n}" if n else "Storyboard")
        elif s["kind"] == "mi":
            sheets = (s.get("extra") or {}).get("sheets") or 0
            big = (s.get("extra") or {}).get("usage") in ("large", "big", "bigMi", "proposal_large")
            parts.append(f"{'대규모 MI' if big else 'MI'} {sheets}시트" if sheets else "MI")
        elif s["kind"] == "requirements":
            parts.append("고객 요구사항")
        elif s["kind"] == "vp":
            parts.append("이전 가치 제안")
    rfp = f.get("rfp") or {}
    if rfp:
        parts.append("RFP 평가 기준" if rfp.get("evaluation_criteria") else "RFP")
    q = f.get("quote") or {}
    if q.get("total") or q.get("attached"):
        parts.append(q.get("version_label") or "견적")
    if f.get("meeting"):
        parts.append("회의록")
    cases = sum(1 for s in _connected(doc) if s["kind"] == "case")
    if cases:
        parts.append(f"유관 사례 {cases}")
    if not parts and (doc.get("note") or "").strip():
        parts.append("메모")
    return " · ".join(parts)


def generate_bubble(doc: dict[str, Any]) -> str:
    """VP3G 말풍선 `· Solution형 제안 연결 · 대규모 MI 6시트 · RFP · 견적 v2`."""
    tp = (doc.get("target_proposal") or {}).get("type") if doc.get("target_proposal") else None
    head = [f"{TYPE_SHORT[tp]} 제안 연결"] if tp and (doc.get("target_proposal") or {}).get("title") else []
    return " · ".join(head + ([materials_footer(doc)] if materials_footer(doc) else []))


def sources_n(doc: dict[str, Any]) -> int:
    return len(_connected(doc)) + len([a for a in doc.get("attachments") or [] if a.get("status") == "read"])


def review_intro(doc: dict[str, Any]) -> str:
    """VP1A `세 자료에서 재료 14개를 뽑아 4축으로 정리했어요. 같은 말은 합치고, 부딪치는 건 고쳐 썼어요. 확인이 필요한 건 하나뿐이에요.`"""
    items = [m for m in doc.get("materials") or [] if not m.get("excluded") and m.get("axis") != "product"]
    n_src = max(1, sources_n(doc))
    src = f"{KO_NUM.get(n_src, str(n_src))} 자료에서" if n_src > 1 else "자료에서"
    fixes = doc.get("fixes") or []
    merged = any(f["kind"] == "merge" for f in fixes)
    rewritten = any(f["kind"] == "rewrite" for f in fixes)
    k = sum(1 for f in fixes if f.get("mode") == "check" and f.get("decision") == "pending")
    mid = []
    if merged:
        mid.append("같은 말은 합치고")
    if rewritten:
        mid.append("부딪치는 건 고쳐 썼어요")
    elif merged:
        mid[-1] = "같은 말은 합쳤어요"
    head = f"{src} 재료 {len(items)}개를 뽑아 4축으로 정리했어요."
    body = (" " + ", ".join(mid) + ".") if mid else ""
    tail = " 확인이 필요한 건 하나뿐이에요." if k == 1 else (f" 확인이 필요한 건 {k}개예요." if k else " 확인이 필요한 건 없어요.")
    return head + body + tail


def auto_chips(doc: dict[str, Any]) -> list[str]:
    """VP1Q `자동으로 정한 것` — 업종 · 업종판 · 시트 수 · 커버리지 · 톤."""
    out: list[str] = []
    ind = doc.get("industry") or {}
    plan = doc.get("plan") or {}
    if ind.get("code"):
        src = {"mi": "MI 상속", "storyboard": "Storyboard 상속", "vp": "복제 원본", "requirements": "정의서 상속",
               "user": "직접 고름"}.get(ind.get("source") or "", "자동 판별")
        if ind.get("mode") != "ask":
            out.append(f"업종 {ind.get('cell') or ind.get('name')} · {src}")
        if ind.get("code") != "GEN":
            out.append("업종판 준비됨" if (ind.get("pack") or {}).get("status") == "ready" else "업종판 제작 중 → 범용")
    if plan.get("sheets") is not None and not any(q.get("kind") == "direction" and q.get("status") == "open" for q in doc.get("questions") or []):
        out.append(f"시트 {len(plan.get('sheets') or [])}")
    ch = len(signals.active(doc, "challenge"))
    from . import coverage
    need, have = coverage.number_slots(signals.active(doc))
    if ch or need:
        out.append(f"과제 {ch} · 근거 수치 {have}/{need}" if need else f"과제 {ch} · 근거 수치 없음")
    for r in plan.get("decisions") or []:
        if r.get("key") == "톤":
            parts = [p for p in (r.get("value") or "").split(" · ") if p]
            # 보드 순서: 경쟁사 언급 → 고객사명
            parts.sort(key=lambda p: 0 if "경쟁사" in p else 1)
            out.extend(parts)
    return out


def result_intro(doc: dict[str, Any]) -> str:
    sheets = [s for s in doc.get("sheets") or [] if s.get("kind", "main") == "main"]
    n = len(sheets)
    k = len([c for c in doc.get("checks") or [] if not c.get("resolved")])
    tail = f"확인할 것은 {k}개예요." if k else "확인할 것은 없어요."
    return f"가치 제안 {n}장을 만들었어요. 시트마다 고른 레이아웃과 이유를 붙여 두었고, {tail}"


def head_codes(doc: dict[str, Any]) -> str:
    """VP3G 진행 머리 `VP-H 이해관계자별 가치 · EF-B 투자 회수`."""
    plan = doc.get("plan") or {}
    parts = []
    for s in plan.get("sheets") or []:
        e = catalog.entry(s["layout"]["code"]) or {}
        parts.append(f"{s['layout']['display']} {e.get('short') or e.get('name') or ''}".strip())
    return " · ".join(parts)


def compute(doc: dict[str, Any]) -> None:
    qs = [q for q in doc.get("questions") or [] if q.get("status") == "open"]
    chips = auto_chips(doc)
    doc["labels"] = {
        "connect": connect_bubble(doc), "questions": question_bubble(doc), "materials_footer": materials_footer(doc),
        "generate": generate_bubble(doc), "head_codes": head_codes(doc),
    }
    doc["intros"] = {
        "materials_review": review_intro(doc) if doc.get("materials") else "",
        "questions": decide.questions_intro(len(qs), len(chips)) if qs else "",
        "questions_default": decide.default_summary(qs) if qs else "",
        "result": result_intro(doc) if doc.get("generated") else "",
        "structure": (doc.get("plan") or {}).get("intro") or "",
    }
    doc["auto_chips"] = chips
    doc["legend"] = materials.tag_names(doc.get("materials") or [])
