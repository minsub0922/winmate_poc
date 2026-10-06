"""작업(analysis) 도메인 로직 — 새 작업 · 공개 모양 · 설계 결정 · 의존 다시 계산 · 경로 · workspace 색인."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.ids import now_iso
from winmate_common.platform import register_item

from . import anonymize, config, layout, rules
from . import store as R

log = logging.getLogger("winmate.mi")

DECISION_LABEL = {"segment": "업종", "usage": "쓰임", "scope": "분석 범위", "competitors": "경쟁사", "naming": "경쟁사 표기",
                  "internal": "사내 자료", "depth": "깊이"}
DECISION_ORDER = ["segment", "usage", "scope", "competitors", "naming", "internal", "depth"]
DEPENDS = {"segment": [], "usage": [], "scope": ["segment"], "competitors": ["segment", "scope"], "naming": ["usage"],
           "internal": ["segment"], "depth": ["usage", "scope"]}
INPUT_SCREENS = {"input", "industry", "scope", "design", "design/industry", "competitors"}


def not_found(what: str = "분석 작업", ident: str | None = None) -> ApiError:
    return ApiError(404, "NOT_FOUND", f"{what}을(를) 찾을 수 없어요", {"id": ident})


def hash_of(*parts: Any) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:16]


# ── 새 작업 ──────────────────────────────────────────────
def new_doc(**kw: Any) -> dict[str, Any]:
    user = current_user()
    now = now_iso()
    doc: dict[str, Any] = {
        "id": R.nid("mi"), "owner_id": user.id, "owner_name": user.name, "project_id": kw.get("project_id"),
        "title": "", "title_pinned": False, "topic": "", "customer_name": kw.get("customer_name"),
        "requirements_text": kw.get("requirements_text") or "", "requirements": [], "files": [], "links": kw.get("links") or {},
        "segment": {}, "usage": {}, "scope": {"areas": [], "mode": None, "reasons": {}, "reduced": []},
        "anonymize": True, "anonymize_pinned": False, "naming_mode": "letter", "internal": {}, "depth": {"target_sources": 30, "eta_s": 180},
        "status": "draft", "result_version": 0, "current_job_id": None, "design_job_id": None, "design_status": "none",
        "last_screen": "input", "memos": [], "competitors": [], "criteria": [], "samsung_products": [], "preset": None,
        "req_summary": "", "scope_desc": {}, "input_kind": "", "one_line_memo": False, "extracted": {}, "decisions": {},
        "created_at": now, "updated_at": now, "analyzed_at": None, "next_recheck_at": None, "edit_after_analysis": False,
        "registered": {}, "latest_handoff": None, "run": {}, "upd_changes": [],
    }
    return doc


# ── 공개 모양 ────────────────────────────────────────────
def competitors_public(doc: dict[str, Any]) -> list[dict[str, Any]]:
    comps = doc.get("competitors") or []
    live = anonymize.live(comps)
    out = []
    for c in sorted(comps, key=lambda c: (c.get("order", 0), c.get("letter", ""))):
        label, _desc = anonymize.preview_label(c, doc.get("anonymize", True), doc.get("naming_mode", "letter"), live)
        tag = {"auto": "자동 추천", "user": "직접 추가", "ca_import": "경쟁사 분석에서", "mi_rfp": "RFP 언급"}.get(c.get("origin", "auto"), "")
        out.append({**c, "display": anonymize.workspace_label(c), "export_display": label, "tag": tag})
    return out


def criteria_with_pct(criteria: list[dict[str, Any]], segment_short: str = "") -> list[dict[str, Any]]:
    """가중치 → 비율: 마지막 행을 뺀 행은 round(w ÷ Σw × 100), 마지막 행은 100 − 앞 행 합(AC-MI-85)."""
    items = sorted([dict(c) for c in criteria or []], key=lambda c: c.get("order", 0))
    on = [c for c in items if c.get("enabled", True)]
    total = sum(int(c.get("weight", 1)) for c in on) or 1
    acc = 0
    for i, c in enumerate(on):
        pct = 100 - acc if i == len(on) - 1 else rules.half_up(int(c.get("weight", 1)) / total * 100)
        acc += pct
        c["pct"] = pct
    for c in items:
        c.setdefault("pct", 0)
        src = c.get("source", "user")
        c["source_label"] = {"requirements": "요구사항", "user": "직접 추가",
                             "industry_cases": f"업종 사례 {c.get('source_count') or 0}건",
                             "preset": f"업종 사례 {c.get('source_count') or 0}건"}.get(src, "직접 추가")
    return items


def ordered_criteria(criteria: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """비교표 행 순서 = 켜진 기준을 가중치 내림차순, 같으면 MI2C 순서."""
    on = [c for c in criteria or [] if c.get("enabled", True)]
    return sorted(on, key=lambda c: (-int(c.get("weight", 1)), c.get("order", 0)))


def route_for(doc: dict[str, Any]) -> str:
    aid = doc["id"]
    st = doc.get("status", "draft")
    last = doc.get("last_screen") or ""
    if st in ("queued", "running", "failed"):
        return f"/mi/{aid}/run"
    if st == "done":
        return f"/mi/{aid}/verify" if last == "verify" else f"/mi/{aid}/result"
    if st == "upd":
        return f"/mi/{aid}/result"
    if last in INPUT_SCREENS:
        return f"/mi/{aid}/{last}"
    if st == "ask":
        return f"/mi/{aid}/design/industry"
    if st in ("designing", "designed"):
        return f"/mi/{aid}/design"
    if st == "stopped":
        return f"/mi/{aid}/competitors" if "competitor" in ((doc.get("scope") or {}).get("areas") or []) else f"/mi/{aid}/scope"
    return f"/mi/{aid}/input"


def areas_of(doc: dict[str, Any]) -> list[str]:
    return [a for a in rules.AREAS if a in ((doc.get("scope") or {}).get("areas") or [])]


def default_title(doc: dict[str, Any]) -> str:
    """`{고객사} {주제} 분석` — 고객사가 없으면(MI1I 프리셋 등) 업종 이름으로 `{업종} {주제} 분석`."""
    cust = (doc.get("customer_name") or "").strip()
    topic = doc.get("topic") or "시장"
    if cust:
        return f"{cust} {topic} 분석"[:30]
    code = (doc.get("segment") or {}).get("code")
    if code and code != "GEN":
        return f"{config.segment(code).get('short') or code} {topic} 분석"[:30]
    return ""


def public(doc: dict[str, Any]) -> dict[str, Any]:
    seg = doc.get("segment") or {}
    short = config.segment(seg.get("code")).get("short") if seg.get("code") else ""
    n_areas = len(areas_of(doc)) or 4
    pub = {k: v for k, v in doc.items() if k not in ("result_version", "decisions", "registered", "extracted", "title_pinned",
                                                     "anonymize_pinned", "run", "upd_changes", "latest_handoff", "edit_after_analysis")}
    pub["version"] = int(doc.get("result_version") or 0)
    pub["title"] = doc.get("title") or default_title(doc) or ""
    pub["status_label"] = rules.STATUS_LABEL.get(doc.get("status", "draft"), "작성 중")
    pub["competitors"] = competitors_public(doc)
    pub["criteria"] = criteria_with_pct(doc.get("criteria") or [], short)
    pub["route"] = route_for(doc)
    eta = rules.run_eta_s(n_areas)
    pub["eta_s"] = eta
    pub["run_label"] = rules.run_label(n_areas)
    pub["edited_after_analysis"] = bool(doc.get("edit_after_analysis"))
    pub["links"] = doc.get("links") or {}
    pub["segment"] = doc.get("segment") or {}
    pub["usage"] = doc.get("usage") or {}
    pub["scope"] = doc.get("scope") or {}
    pub["internal"] = doc.get("internal") or {}
    pub["depth"] = doc.get("depth") or {}
    return pub


# ── 색인(§5.12) ──────────────────────────────────────────
def summary_for(doc: dict[str, Any]) -> str:
    seg = (doc.get("segment") or {}).get("code")
    parts = []
    if seg:
        parts.append(config.segment(seg)["short"])
    areas = areas_of(doc)
    if areas:
        parts.append(rules.scope_label(areas))
    run = doc.get("run") or {}
    if doc.get("result_version"):
        parts.append(f"출처 {int(run.get('sources_used') or 0)}곳")
        if int(run.get("fix_open") or 0):
            parts.append(f"확정 필요 {int(run['fix_open'])}")
    return " · ".join(parts)


async def register(doc: dict[str, Any], *, force: bool = False) -> None:
    title = doc.get("title") or default_title(doc) or "새 분석"
    body = {"title": title, "status": rules.STATUS_LABEL.get(doc.get("status", "draft"), "작성 중"), "route": route_for(doc),
            "summary": summary_for(doc), "version": int(doc.get("result_version") or 0)}
    # 경쟁사 실명은 절대 색인에 넣지 않는다(AC-MI-73)
    body["title"] = anonymize.scrub(body["title"], doc.get("competitors") or [], {})
    body["summary"] = anonymize.scrub(body["summary"], doc.get("competitors") or [], {})
    if not force and doc.get("registered") == body:
        return
    await register_item(feature="MI", item_id=doc["id"], title=body["title"], status=body["status"], route=body["route"],
                        summary=body["summary"], project_id=doc.get("project_id"),
                        meta={"version": body["version"], "segment": (doc.get("segment") or {}).get("code"),
                              "status_code": doc.get("status")})
    try:
        await R.call(R.patch_analysis, doc["id"], {"registered": body})
    except KeyError:
        pass


# ── 설계 결정(§5.2) ──────────────────────────────────────
def decision_inputs(doc: dict[str, Any], key: str) -> Any:
    seg = (doc.get("segment") or {})
    usage = doc.get("usage") or {}
    scope = doc.get("scope") or {}
    req = [r.get("text") for r in doc.get("requirements") or []] + [doc.get("requirements_text") or ""]
    files = [(f.get("file_id"), f.get("classification"), f.get("include", True)) for f in doc.get("files") or []]
    if key == "segment":
        return [req, files, doc.get("links"), seg.get("mode") == "pin" and seg.get("code")]
    if key == "usage":
        return [(doc.get("links") or {}).get("proposal_id"), (doc.get("links") or {}).get("proposal_type"), req, usage.get("mode") == "pin" and usage.get("value")]
    if key == "scope":
        return [req, seg.get("code"), scope.get("mode") == "pin" and scope.get("areas")]
    if key == "competitors":
        return [seg.get("code"), scope.get("areas"), req, [m.get("text") for m in doc.get("memos") or []],
                [(c.get("real_name"), c.get("removed")) for c in doc.get("competitors") or []]]
    if key == "naming":
        return [usage.get("value"), doc.get("anonymize_pinned") and doc.get("anonymize"), doc.get("naming_mode")]
    if key == "internal":
        return [seg.get("code"), files]
    if key == "depth":
        return [usage.get("value"), scope.get("areas")]
    return None


def make_decision(doc: dict[str, Any], key: str, display_value: str, reason: str, mode: str) -> dict[str, Any]:
    aid = doc["id"]
    routes = {"segment": f"/mi/{aid}/design/industry", "usage": "#usage", "scope": f"/mi/{aid}/scope", "competitors": f"/mi/{aid}/competitors",
              "naming": f"/mi/{aid}/competitors", "internal": "#internal", "depth": f"/mi/{aid}/scope"}
    prev = (doc.get("decisions") or {}).get(key) or {}
    h = hash_of(decision_inputs(doc, key))
    changed = prev.get("display_value") != display_value or prev.get("mode") != mode or prev.get("reason") != reason or prev.get("input_hash") != h
    d = {"key": key, "label": DECISION_LABEL[key], "display_value": display_value, "reason": reason, "mode": mode,
         "change_route": routes[key], "depends_on": DEPENDS[key], "input_hash": h,
         "updated_at": now_iso() if changed or not prev.get("updated_at") else prev["updated_at"]}
    doc.setdefault("decisions", {})[key] = d
    return d


def segment_display(doc: dict[str, Any]) -> tuple[str, str]:
    seg = doc.get("segment") or {}
    code = seg.get("code")
    if not code:
        return "[확인 필요]", ""
    s = config.segment(code)
    if seg.get("mix"):
        mx = seg["mix"]
        return f"섞어서 보기 · {config.segment(mx['a'])['short']} + {config.segment(mx['c'])['short']}", "시장 · 비즈니스와 사용자 여정을 나눠 봐요"
    if code == "GEN":
        return "범용 · 16개 업종 밖", "16개 업종 어디에도 0.50 이상 맞지 않음"
    if seg.get("inherited_from"):
        src = {"storyboard": "Storyboard", "requirements": "정의서", "proposal": "제안서", "mi": "이전 MI 작업"}.get(seg["inherited_from"], "연결 작업")
        return f"{s['short']} ({code}) · 상속", f"연결된 {src}에 업종이 있음"
    conf = seg.get("confidence")
    val = f"{s['short']} ({code})" + (f" · {rules.fmt2(conf)}" if conf is not None else "")
    if seg.get("mode") == "pin":
        return val, "사람이 정한 업종"
    clues = [c["text"] for c in seg.get("clues") or [] if c.get("code") == code][:3]
    reason = (" · ".join(clues) + " 단서 일치") if clues else "요구사항 · 사례 DB 유사도"
    return val, reason


def usage_display(doc: dict[str, Any], n_sheets: int | None = None) -> tuple[str, str]:
    u = doc.get("usage") or {}
    v = u.get("value") or "none"
    label = rules.USAGE_LABEL.get(v, "").format(n=n_sheets or 6)
    return label, u.get("reason") or ""


def refresh_decisions(doc: dict[str, Any], *, kb_case_count: int | None = None) -> None:
    """결정적 결정(쓰임 · 표기 · 사내 자료 · 깊이 · 범위 · 경쟁사 표시)을 지금 값으로 다시 만든다. 바뀐 결정만 updated_at 이 바뀐다."""
    seg_val, seg_reason = segment_display(doc)
    seg = doc.get("segment") or {}
    if seg.get("code"):
        make_decision(doc, "segment", seg_val, seg_reason, seg.get("mode") or "auto")
    u = doc.get("usage") or {}
    if u.get("value"):
        sheets = layout.preview_sheets(doc)
        val, reason = usage_display(doc, len(sheets))
        make_decision(doc, "usage", val, reason, u.get("mode") or "auto")
    scope = doc.get("scope") or {}
    areas = areas_of(doc)
    if areas:
        reason = scope.get("reason_text") or "요구사항 · 업종 기준"
        make_decision(doc, "scope", rules.scope_decision_label(areas), reason, scope.get("mode") or "auto")
    comps = anonymize.live(doc.get("competitors") or [])
    if "competitor" in areas:
        cdec = (doc.get("decisions") or {}).get("competitors") or {}
        if comps:
            letters = " · ".join(c["letter"] for c in comps)
            val = f"경쟁사 {letters}"
        else:
            val = "분석할 때 찾아요"
        mode = cdec.get("mode") or ("check" if any(c.get("origin") == "auto" for c in comps) or not comps else "auto")
        if any(c.get("pinned") for c in comps) and not any(c.get("origin") == "auto" for c in comps):
            mode = "pin"
        reason = cdec.get("reason") or ("지정 없음 → " + config.segment(seg.get("code")).get("short", "업종") + " 사례 빈도 상위 3")
        make_decision(doc, "competitors", val, reason, mode)
        anon = doc.get("anonymize", True)
        if anon:
            nval = "익명 (경쟁사 A · B · C)" if doc.get("naming_mode", "letter") == "letter" else "유형으로 표기"
        else:
            nval = "실명 · 사내용"
        if doc.get("anonymize_pinned"):
            nmode, nreason = "pin", "사람이 정한 표기"
        elif rules.is_customer_facing(u.get("value")):
            nmode, nreason = "auto", "고객에게 내는 제안서라 기본값 익명"
        else:
            nmode, nreason = "auto", "내부용이라 실명"
        make_decision(doc, "naming", nval, nreason, nmode)
    else:
        for k in ("competitors", "naming"):
            (doc.get("decisions") or {}).pop(k, None)
    internal = doc.get("internal") or {}
    if kb_case_count is not None:
        internal["kb_case_count"] = kb_case_count
    excl_names = [f.get("name") or "첨부" for f in doc.get("files") or [] if f.get("classification") == "confidential"]
    count = int(internal.get("kb_case_count") or 0)
    summary = internal.get("summary_override") or f"도입사례 {count}건"
    val = summary + (f" · {', '.join(n.rsplit('.', 1)[0] for n in excl_names[:2])} 제외" if excl_names else "")
    internal["summary"] = summary
    doc["internal"] = internal
    make_decision(doc, "internal", val, "대외비 수치는 고객 제출물에 넣지 않음", internal.get("mode") or "auto")
    depth_n = rules.depth_for(u.get("value"))
    eta = rules.run_eta_s(len(areas) or 4)
    doc["depth"] = {"target_sources": depth_n, "eta_s": eta}
    make_decision(doc, "depth", f"{rules.minutes_label(eta)} · 출처 {depth_n}곳 내외", "3시트 분량 조사량 · 대규모 MI면 2배", "auto")


def design_view(doc: dict[str, Any]) -> dict[str, Any]:
    decs = doc.get("decisions") or {}
    # 설계 잡 중간(decide_competitors 가 mode · reason 만 먼저 적고 refresh_decisions 전)에는 덜 만든 줄이 있다 — 다 만든 줄만 보인다
    rows = [decs[k] for k in DECISION_ORDER if k in decs and decs[k].get("key") and decs[k].get("label")]
    tally = {m: sum(1 for d in rows if d.get("mode") == m) for m in ("auto", "check", "ask")}
    sheets = layout.preview_sheets(doc)
    u = (doc.get("usage") or {}).get("value") or "none"
    type_name = rules.USAGE_TYPE_NAME.get(u, "리포트")
    head = f"{type_name} MI 섹션 · 업종 레이아웃 먼저" if u in ("standard", "solution") else f"{type_name} · 업종 레이아웃 먼저"
    return {
        "status": doc.get("design_status") or "none",
        "job_id": doc.get("design_job_id"),
        "decisions": rows,
        "tally": tally,
        "sheets_preview": sheets,
        "sheets_head": head,
        "usage_label": rules.USAGE_LABEL.get(u, "").format(n=len(sheets)),
        "ask": doc.get("design_ask"),
        "run_label": rules.run_label(len(areas_of(doc)) or 4),
        "error": doc.get("design_error"),
    }


def apply_scope_keywords(text: str, areas: list[str], reasons: dict[str, str]) -> tuple[list[str], dict[str, str], list[str]]:
    """키워드 규칙은 추가만(§7.4 decide_scope). 근거 문구 `요구에 '{구}' · '{구}' 있음`."""
    kw = config.routing().get("keywords", {})
    phrases: list[str] = []
    out = list(areas)
    for area, key in (("competitor", "competitor"), ("user", "user")):
        hits = rules.keyword_hits(text, kw.get(key, []))
        if hits:
            if area not in out:
                out.append(area)
            ph = rules.phrase_around(text, hits[0])
            reasons[area] = f"요구에 '{ph}' 있음"
            phrases.append(ph)
    return [a for a in rules.AREAS if a in out], reasons, phrases


def default_criteria(doc: dict[str, Any], insights: dict[str, Any] | None) -> list[dict[str, Any]]:
    """기준 = 요구사항에서 최대 3(가중치 5 · 4 · 3) + 업종 사례 1(가중치 2) + 프리셋 항목 + 직접 추가(§4.9 기본값)."""
    existing = doc.get("criteria") or []
    if any(c.get("pinned") for c in existing):
        return existing
    out: list[dict[str, Any]] = []
    order = 0
    reqs = [r for r in doc.get("requirements") or [] if r.get("origin") != "preset"]
    weights = [5, 4, 3]
    for i, r in enumerate(reqs[:3]):
        name = (r.get("label") or r.get("text") or "")[:24]
        if not name:
            continue
        out.append({"id": R.nid("crt"), "name": name, "source": "requirements", "weight": weights[i], "order": order, "enabled": True,
                    "pinned": False, "requirement_id": r.get("id")})
        order += 1
    preset = [r for r in doc.get("requirements") or [] if r.get("origin") == "preset"]
    names = {c["name"] for c in out}
    for r in preset:
        name = (r.get("label") or r.get("text") or "")[:24]
        if name and name not in names:
            out.append({"id": R.nid("crt"), "name": name, "source": "preset", "source_count": r.get("weight"), "weight": 2, "order": order,
                        "enabled": True, "pinned": False, "requirement_id": r.get("id")})
            names.add(name)
            order += 1
    if insights and not preset:
        for rt in insights.get("req_types") or []:
            name = (rt.get("label") or "")[:24]
            if name and name not in names:
                out.append({"id": R.nid("crt"), "name": name, "source": "industry_cases", "source_count": rt.get("n"), "weight": 2,
                            "order": order, "enabled": True, "pinned": False})
                break
    for c in existing:
        if c.get("source") == "user" and c["name"] not in names:
            out.append({**c, "order": len(out)})
    return out


def eta_for_run(doc: dict[str, Any], areas: list[str], mode: str) -> int:
    if mode == "changed_only":
        return rules.changed_eta_s(len(areas))
    return rules.run_eta_s(len(areas))
