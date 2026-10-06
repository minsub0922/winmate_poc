"""작업 문서 · 화면 모양 — 상태 · 이동(§3.4), 목록 행(§4.2), 후보 · 기준 표시, workspace 색인(§5.9).

익명화(§4.0 · §10.6): 목록 · 사이드바 · 홈 · workspace 요약 · 알림 · 배너에는 실명을 쓰지 않는다(`경쟁사 {글자}` 만).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from winmate_common import platform
from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.ids import now_iso

from . import config, rules
from . import store as R

log = logging.getLogger("winmate.competitor.service")

INPUT_LABEL = {"free": "자유 양식", "requirements": "요구사항에서", "mi": "MI 작업에서"}
STATUS_CHIP = {"done": "완료", "upd": "업데이트 필요"}
SENT_ORDER = (("mi", "MI 작업"), ("proposal_why", "제안서"), ("storyboard", "Storyboard"), ("report", "리포트"))


def not_found(what: str, ident: str) -> ApiError:
    return ApiError(404, "NOT_FOUND", f"{what}을(를) 찾을 수 없어요", {"resource": what, "id": ident})


# ── 만들기 ───────────────────────────────────────────────
def new_doc(*, input_mode: str, text: str = "", extra_text: str = "", file_ids: list[str] | None = None, requirements_id: str | None = None,
            rq_version: int | None = None, mi_ref: dict[str, Any] | None = None, mi_bundle: dict[str, Any] | None = None,
            project_id: str | None = None, purpose: str | None = None, auto_run: bool = False) -> dict[str, Any]:
    from .reading import empty_slots

    user = current_user()
    now = now_iso()
    return {
        "id": R.nid("ca"), "owner_id": user.id, "owner_name": user.name, "project_id": project_id, "title": "", "title_auto": True,
        "input_mode": input_mode, "text": text or "", "extra_text": extra_text or "", "file_ids": list(file_ids or []),
        "requirements_id": requirements_id, "rq_version": rq_version, "mi_ref": mi_ref, "mi_bundle": mi_bundle,
        "purpose": purpose, "auto_run": bool(auto_run),
        "slots": empty_slots(), "segment": {"code": "GEN", "confidence": 0.0, "ambiguous": False, "candidates": []}, "chips": [],
        "rfp": {"competitor_mentions": [], "eval_criteria": []}, "include_names": [], "exclude_names": [], "notes": "", "requirements": [],
        "anonymize": True, "naming_mode": "letter", "status": "draft", "result_version": 0, "current_job_id": None, "current_job_kind": None,
        "last_screen": "input", "competitors": [], "criteria": [], "criteria_mode": "auto", "criteria_suggestions": [], "industry_cases": 0,
        "find": {"lines": [], "candidates_so_far": 0}, "ask": None, "run": None, "stopped": None, "samsung_products": [], "kb_cases": [],
        "needs_rejudge": False, "changes": [], "recheck": {}, "created_at": now, "updated_at": now, "analyzed_at": None, "next_recheck_at": None,
    }


# ── 칸 · 업종 표시 ───────────────────────────────────────
def slot_view(key: str, s: dict[str, Any] | None) -> dict[str, Any]:
    s = s or {}
    label = rules.SLOT_LABEL[key]
    value = s.get("value")
    found = s.get("found") or ("found" if value else "empty")
    chip = f"{label} · {value}" if value and found != "empty" else f"{label} · 비어 있음"
    return {"key": key, "label": label, "value": value if found != "empty" else None, "found": found, "origin": s.get("origin"),
            "confidence": s.get("confidence"), "chip_text": chip, "partial": found == "partial", "code": s.get("code")}


def slots_view(slots: dict[str, Any]) -> dict[str, Any]:
    return {k: slot_view(k, (slots or {}).get(k)) for k in rules.SLOT_ORDER}


def segment_view(seg: dict[str, Any] | None) -> dict[str, Any]:
    seg = seg or {}
    code = seg.get("code") or "GEN"
    s = config.segment(code)
    return {"code": code, "name": s.get("short", "범용"), "full": s.get("full", "범용"), "confidence": float(seg.get("confidence") or 0.0),
            "ambiguous": bool(seg.get("ambiguous")), "gap": seg.get("gap"),
            "candidates": [{"code": c["code"], "name": config.segment(c["code"]).get("short", ""), "confidence": float(c.get("confidence") or 0.0)}
                           for c in seg.get("candidates") or []][:5]}


def chips_view(doc: dict[str, Any], *, extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    out = []
    for k in doc.get("chips") or []:
        if k in rules.CHIP_LABEL:
            out.append({"key": k, "label": rules.CHIP_LABEL[k], "mode": "check"})
    return out + list(extra or [])


# ── 상태 · 이동(§3.4) ────────────────────────────────────
def status_label(status: str) -> str:
    return STATUS_CHIP.get(status, "확인 중")


def status_tone(status: str) -> str:
    return {"done": "done", "upd": "upd"}.get(status, "check")


def base(doc: dict[str, Any]) -> str:
    return f"/competitor/{doc['id']}"


def input_route(doc: dict[str, Any]) -> str:
    return f"{base(doc)}/input" + ("?input=requirements" if doc.get("input_mode") == "requirements" else "")


def changed_competitor(doc: dict[str, Any]) -> str | None:
    for ch in doc.get("changes") or []:
        if ch.get("kind") == "competitor_new_product" and ch.get("competitor_id"):
            return ch["competitor_id"]
    for ch in doc.get("changes") or []:
        if ch.get("competitor_id"):
            return ch["competitor_id"]
    return None


def route_for(doc: dict[str, Any]) -> str:
    st = doc.get("status") or "draft"
    ls = doc.get("last_screen") or ""
    if st == "draft":
        return input_route(doc)
    if st == "finding":
        return f"{base(doc)}/finding"
    if st == "ask":
        return f"{base(doc)}/ask"
    if st == "confirming":
        return f"{base(doc)}/candidates"
    if st == "analyzing":
        return f"{base(doc)}/run"
    if st == "failed":
        return input_route(doc)
    if st == "upd":
        cmp = changed_competitor(doc)
        return f"{base(doc)}/competitors/{cmp}" if cmp else f"{base(doc)}/result"
    if st in ("done", "stopped"):
        if st == "done" and ls == "send":
            return f"{base(doc)}/send"
        return f"{base(doc)}/result"
    return f"{base(doc)}/result"


def action_for(doc: dict[str, Any]) -> dict[str, Any]:
    st = doc.get("status")
    if st == "done":
        return {"label": "결과 보기", "route": f"{base(doc)}/result", "kind": "result"}
    if st == "upd":
        return {"label": "상세 보기", "route": route_for(doc), "kind": "detail"}
    return {"label": "이어서", "route": route_for(doc), "kind": "continue"}


# ── 경쟁사 표시 ──────────────────────────────────────────
def live_competitors(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in doc.get("competitors") or [] if not c.get("removed")]


def ordered(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(cands, key=lambda c: (len(c.get("letter") or ""), c.get("letter") or "", c.get("rank", 0)))


def on_competitors(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return ordered([c for c in live_competitors(doc) if c.get("on")])


def competitor_view(c: dict[str, Any]) -> dict[str, Any]:
    letter = c.get("letter") or "?"
    on = bool(c.get("on"))
    status = c.get("status") or "drop"
    return {"id": c["id"], "letter": letter, "display": f"경쟁사 {letter}", "real_name": c.get("real_name") or "",
            "aliases": list(c.get("aliases") or []), "kind_label": c.get("kind_label") or "", "why": c.get("why") or "",
            "chips": list(c.get("chips") or []), "confidence": c.get("confidence") if status != "user" else None,
            "confidence_label": rules.fmt_conf(c.get("confidence")) if status != "user" else "", "status": status,
            "status_label": rules.STATUS_LABEL.get(status, ""), "on": on, "pinned": bool(c.get("pinned")), "removed": bool(c.get("removed")),
            "origin": c.get("origin") or "auto", "rank": int(c.get("rank") or 0), "add_state": c.get("add_state"),
            "switch_label": f"경쟁사 {letter} " + ("빼기" if on else "넣기")}


def candidate_counts(cands: list[dict[str, Any]]) -> dict[str, int]:
    out = {"rec": 0, "check": 0, "drop": 0, "user": 0, "on": 0}
    for c in cands:
        out[c.get("status") or "drop"] = out.get(c.get("status") or "drop", 0) + 1
        if c.get("on"):
            out["on"] += 1
    return out


# ── 기준 표시 ────────────────────────────────────────────
def criterion_view(c: dict[str, Any]) -> dict[str, Any]:
    src = c.get("source") or "user"
    label = {"requirements": "요구", "default": "기본", "user": "직접 추가"}.get(src, "")
    if src == "industry_cases":
        label = f"업종 사례 {c['source_count']}건" if c.get("source_count") else "업종 사례"
    return {"id": c["id"], "name": c.get("name") or "", "source": src, "source_label": label, "source_count": c.get("source_count"),
            "importance": int(c.get("importance") or 3), "order": int(c.get("order") or 0), "enabled": bool(c.get("enabled", True)),
            "pinned": bool(c.get("pinned")), "requirement_ref": c.get("requirement_ref")}


def criteria_sorted(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(doc.get("criteria") or [], key=lambda c: int(c.get("order") or 0))


def enabled_criteria(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in criteria_sorted(doc) if c.get("enabled", True)]


def criteria_summary_text(summary: dict[str, int]) -> str:
    txt = f"요구사항에서 {summary.get('requirements', 0)} · 업종 사례에서 {summary.get('industry_cases', 0)} · 기본 {summary.get('default', 0)}"
    if summary.get("user"):
        txt += f" · 직접 {summary['user']}"
    return txt


# ── 실행 진행 ────────────────────────────────────────────
def run_line(letter: str, state: str, done_facts: list[str], current: str | None) -> str:
    if state == "done":
        return f"경쟁사 {letter} — 완료"
    if state == "partial":
        return f"경쟁사 {letter} — 일부만 찾음"
    if state == "wait":
        return f"경쟁사 {letter} — 대기"
    done = " · ".join(config.fact_progress_label(f) for f in done_facts)
    cur = config.fact_progress_label(current) if current else ""
    if done and cur:
        return f"경쟁사 {letter} — {done} 완료, {cur} 찾는 중"
    if cur:
        return f"경쟁사 {letter} — {cur} 찾는 중"
    if len(done_facts) >= len(config.fact_order()):
        return f"경쟁사 {letter} — 사실 정리 · 판정 중"
    if done:
        return f"경쟁사 {letter} — {done} 완료"
    return f"경쟁사 {letter} — 찾는 중"


def analyzed_ids(doc: dict[str, Any], version: dict[str, Any] | None) -> list[str]:
    if not version:
        return []
    return list(version.get("competitor_ids") or [])


# ── 화면용 작업 ──────────────────────────────────────────
def analysis_view(doc: dict[str, Any], *, version: dict[str, Any] | None = None) -> dict[str, Any]:
    live = live_competitors(doc)
    on = on_competitors(doc)
    run = doc.get("run")
    stopped = doc.get("stopped")
    mi_ref = doc.get("mi_ref")
    return {
        "id": doc["id"], "title": display_title(doc), "input_mode": doc.get("input_mode") or "free",
        "input_label": INPUT_LABEL.get(doc.get("input_mode") or "free", "자유 양식"), "text": doc.get("text") or "",
        "extra_text": doc.get("extra_text") or "", "file_ids": list(doc.get("file_ids") or []), "requirements_id": doc.get("requirements_id"),
        "rq_version": doc.get("rq_version"), "mi_ref": mi_ref if mi_ref and mi_ref.get("analysis_id") else None, "project_id": doc.get("project_id"),
        "purpose": doc.get("purpose"), "customer_name": ((doc.get("slots") or {}).get("customer") or {}).get("value"),
        "slots": slots_view(doc.get("slots") or {}), "found_count": rules.found_count(doc.get("slots") or {}),
        "segment": segment_view(doc.get("segment")), "chips": chips_view(doc), "rfp": doc.get("rfp") or {},
        "include_names": doc.get("include_names") or [], "exclude_names": doc.get("exclude_names") or [],
        "anonymize": bool(doc.get("anonymize", True)), "naming_mode": doc.get("naming_mode") or "letter",
        "status": doc.get("status") or "draft", "status_label": status_label(doc.get("status") or "draft"),
        "version": int(doc.get("result_version") or 0), "current_job_id": doc.get("current_job_id"), "current_job_kind": doc.get("current_job_kind"),
        "last_screen": doc.get("last_screen"), "route": route_for(doc), "competitor_count": len(live), "on_count": len(on),
        "analyzed_count": len((version or {}).get("competitor_ids") or []),
        "criteria_mode": doc.get("criteria_mode") or "auto", "ask": doc.get("ask"), "find": doc.get("find") or {},
        "run": run, "stopped": stopped, "needs_rejudge": bool(doc.get("needs_rejudge")), "owner_name": doc.get("owner_name") or "",
        "created_at": doc.get("created_at") or "", "updated_at": doc.get("updated_at") or "", "analyzed_at": doc.get("analyzed_at"),
        "next_recheck_at": doc.get("next_recheck_at"), "letters_on": [c["letter"] for c in on],
        "added_refs": [x["ref"] for x in [*(doc.get("samsung_products") or []), *(doc.get("kb_cases") or [])] if x.get("ref")],
    }


def display_title(doc: dict[str, Any]) -> str:
    return doc.get("title") or "새 분석"


# ── 목록 행(§4.2) ────────────────────────────────────────
def _sub(doc: dict[str, Any], now: datetime) -> tuple[str, str]:
    st = doc.get("status") or "draft"
    upd = doc.get("updated_at")
    if st in ("done", "upd"):
        an = doc.get("analyzed_at")
        edited = bool(doc.get("edited_at") and an and doc["edited_at"] > an)
        label = f"{rules.rel_time(doc.get('edited_at'), now)} 수정" if edited else f"{rules.md_label(an or upd)} 분석"
    elif rules.is_today(doc.get("created_at"), now):
        label = "오늘 시작"
    else:
        label = f"{rules.rel_time(upd, now)} 수정"
    return f"{doc.get('owner_name') or '시스템'} · {label}", label


def note_for(doc: dict[str, Any], version: dict[str, Any] | None) -> str:
    st = doc.get("status") or "draft"
    live = live_competitors(doc)
    if st == "draft":
        return "넣는 중"
    if st == "finding":
        return "찾는 중"
    if st == "ask":
        return "고객사 · 장소 확인 대기"
    if st == "confirming":
        cnt = candidate_counts(live)
        return f"추천 {cnt['rec']} · 확인 필요 {cnt['check']}"
    if st == "analyzing":
        run = doc.get("run") or {}
        comps = run.get("competitors") or []
        k = sum(1 for c in comps if c.get("state") in ("done", "partial"))
        return f"분석 중 {k} / {len(comps) or len(on_competitors(doc))}"
    if st == "stopped":
        k = len((version or {}).get("competitor_ids") or [])
        return f"중지됨 · {k}곳 분석"
    if st == "failed":
        return "찾지 못했어요" if not doc.get("result_version") else "분석을 마치지 못했어요"
    if st == "upd":
        ch = next((c for c in doc.get("changes") or [] if c.get("kind") == "competitor_new_product"), None)
        if ch:
            return f"완료 · 경쟁사 {ch.get('letter')} 신제품 {rules.ym(ch.get('date'))}"
        return "완료 · 출처 내용 변경"
    footer = (version or {}).get("footer") or {}
    return f"출처 {footer.get('sources', 0)} · 삼성 강점 {len((version or {}).get('strengths') or [])}"


def count_for(doc: dict[str, Any], version: dict[str, Any] | None) -> tuple[int | None, str]:
    st = doc.get("status") or "draft"
    if st in ("draft", "finding", "ask", "failed") and not doc.get("result_version"):
        return None, ""
    if st == "confirming":
        return len(live_competitors(doc)), "후보"
    if st == "analyzing":
        return len(on_competitors(doc)), "곳"
    return len((version or {}).get("competitor_ids") or []), "곳"


def sent_label(handoffs: list[dict[str, Any]]) -> str | None:
    have = {h.get("target") for h in handoffs if h.get("status") == "delivered"}
    parts = [label for key, label in SENT_ORDER if key in have]
    return " · ".join(parts) if parts else None


def list_item(doc: dict[str, Any], version: dict[str, Any] | None, handoffs: list[dict[str, Any]], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    sub, time_label = _sub(doc, now)
    count, unit = count_for(doc, version)
    st = doc.get("status") or "draft"
    return {"id": doc["id"], "title": display_title(doc), "sub": sub, "owner_name": doc.get("owner_name") or "", "time_label": time_label,
            "input_mode": doc.get("input_mode") or "free", "input_label": INPUT_LABEL.get(doc.get("input_mode") or "free", ""),
            "count": count, "count_label": str(count) if count is not None else "—", "count_unit": unit, "status": st,
            "status_label": status_label(st), "status_tone": status_tone(st), "note": note_for(doc, version), "sent_label": sent_label(handoffs),
            "action": action_for(doc), "route": route_for(doc), "updated_at": doc.get("updated_at") or "", "current_job_id": doc.get("current_job_id")}


def elapsed_days(doc: dict[str, Any]) -> int:
    """분석 뒤 지난 날 수(재확인 배너 `분석 {d}일 경과`). 분석일을 모르면 재확인 주기."""
    an = doc.get("analyzed_at")
    if not an:
        return config.recheck_days()
    try:
        d0 = datetime.fromisoformat(str(an).replace("Z", "+00:00")).astimezone(config.KST).date()
    except ValueError:
        return config.recheck_days()
    return max(0, (config.today() - d0).days)


def banner_text(doc: dict[str, Any]) -> str:
    ch = next((c for c in doc.get("changes") or [] if c.get("kind") == "competitor_new_product"), None)
    d = elapsed_days(doc)
    tail = f"{display_title(doc)} · " + (f"분석 {d}일 경과" if d >= 1 else "오늘 분석")
    if ch:
        return f"경쟁사 {ch.get('letter')} 가 {rules.ym(ch.get('date'))} 신제품을 냈어요 — {tail}"
    return f"출처 내용이 바뀌었어요 — {tail}"


# ── workspace 색인(§5.9) ─────────────────────────────────
def summary_for(doc: dict[str, Any], version: dict[str, Any] | None = None) -> str:
    seg = segment_view(doc.get("segment"))
    st = doc.get("status") or "draft"
    if version and st in ("done", "upd", "stopped"):
        n = len(version.get("competitor_ids") or [])
    else:
        n = len(on_competitors(doc)) if st in ("analyzing",) else len(live_competitors(doc))
    parts = [seg["name"] if seg["code"] != "GEN" or doc.get("status") != "draft" else "업종 미정", f"경쟁사 {n}곳"]
    src = ((version or {}).get("footer") or {}).get("sources")
    if src:
        parts.append(f"출처 {src}")
    return " · ".join(parts)


async def register(doc: dict[str, Any], version: dict[str, Any] | None = None) -> None:
    """작업 색인(실명 금지 — 요약은 업종 · 수 · 출처 수만)."""
    if version is None and doc.get("result_version"):
        version = await R.call(R.get_version, doc["id"], int(doc["result_version"]))
    if not doc.get("title") and (doc.get("status") or "draft") == "draft" and not (doc.get("text") or doc.get("requirements_id")):
        return
    await platform.register_item(feature="CA", item_id=doc["id"], title=display_title(doc), status=status_label(doc.get("status") or "draft"),
                                 route=route_for(doc), summary=summary_for(doc, version), project_id=doc.get("project_id"),
                                 meta={"input_mode": doc.get("input_mode"), "version": int(doc.get("result_version") or 0)})
