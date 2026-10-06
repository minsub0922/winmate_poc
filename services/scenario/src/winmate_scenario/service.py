"""시나리오 작업 공통 — 문서 만들기 · 경로 · 상태 문구 · 응답 모양 · 장면 버전 · 이미지 stale · workspace 색인 · 잡 넣기."""
from __future__ import annotations

import logging
import re
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import jobs
from winmate_common.platform import register_item

from . import policy, repo, seed, texts
from . import timeline as tl

log = logging.getLogger("winmate.scenario.service")

SECTION = "공간 시나리오 생성"
STEPS = ["시나리오 유형", "공간 시나리오 입력", "솔루션 · 제품 입력", "시나리오 생성"]
TYPE_LABEL = {"with": "with 솔루션", "without": "without 솔루션"}
TYPE_SUB = {"with": "솔루션 + 연관 제품 활용", "without": "제품 활용만"}
TAG_LABEL = {"required": "꼭 필요", "recommended": "추천", "optional": "선택"}
MAX_SCENES_AUTO = 6
MAX_SCENES = 12


# ── 만들기 ─────────────────────────────────────────────────

def new_doc(*, type_: str = "with", start_mode: str = "blank", title: str | None = None, project_id: str | None = None,
            aerial: dict[str, Any] | None = None) -> dict[str, Any]:
    user = current_user()
    now = now_iso()
    return {
        "owner": user.id, "owner_name": user.name, "project_id": project_id, "customer_name": None,
        "title": title or "새 시나리오", "space_label": "", "vertical_code": None, "type": type_, "start_mode": start_mode,
        "template": None, "birdseye_link": None,
        "aerial": {"enabled": False, "source": "new", "birdseye_id": None, "title": None, "created": False, **(aerial or {})},
        "raw_text": "", "characters": [], "removed_characters": [], "needs": [], "status": "draft", "step": 1,
        "saved_version": 0, "dirty": False, "via_timeline": False, "slots": [], "roles": [], "scenes": [],
        "solution_picks": [], "product_picks": [], "related_products": [], "related_for": None,
        "recommendation": None, "suggestions": {"scene": None, "roles": [], "dismissed": []},
        "edit": {"undo": [], "redo": [], "changes": 0}, "generation": None, "active_job": None, "parse": None,
        "notices": {"real_names": False, "too_many": None}, "usages": [], "images_job": None, "space_keys": {},
        "spaces": [], "anonymized": False, "dismissed_alerts": [], "last_saved_at": None, "created_at": now,
    }


async def project_context(project_id: str | None) -> dict[str, Any]:
    """workspace 프로젝트 → {customer, industry_code}."""
    if not project_id:
        return {}
    try:
        p = await ServiceClient("workspace").get(f"/v1/projects/{project_id}")
    except Exception as exc:  # noqa: BLE001
        log.info("프로젝트 읽기 실패 %s: %s", project_id, exc)
        return {}
    ind = seed.industry_by_name(p.get("industry"))
    return {"customer": p.get("customer"), "industry_code": ind["code"] if ind else None}


async def storyboard_context(sb_id: str | None) -> dict[str, Any]:
    """SB4 → `/scenario/new?sb=`: 고객 · Part 2 공간(「[공간] 이름 — 목적」 줄)."""
    if not sb_id:
        return {}
    try:
        sb = await ServiceClient("storyboard").get(f"/v1/storyboards/{sb_id}")
    except Exception as exc:  # noqa: BLE001
        log.info("Storyboard 읽기 실패 %s: %s", sb_id, exc)
        return {}
    spaces = ((sb.get("outline") or {}).get("spaces") or [])
    lines = []
    for s in spaces:
        if not isinstance(s, dict) or not s.get("name"):
            continue
        lines.append(f"[공간] {s['name']}" + (f" — {s['purpose']}" if s.get("purpose") else ""))
    return {"customer": sb.get("customer_name"), "project_id": sb.get("project_id"), "space_lines": lines,
            "space_label": spaces[0]["name"] if spaces and isinstance(spaces[0], dict) else None}


# ── 경로 · 상태 ─────────────────────────────────────────────

def route_of(doc: dict[str, Any]) -> str:
    sid = doc["id"]
    st = doc.get("status")
    gen = doc.get("generation") or {}
    if st == "done":
        return f"/scenario/{sid}/result"
    if st in ("generating", "failed") and gen.get("job_id"):
        return f"/scenario/{sid}/generate/{gen['job_id']}"
    step = int(doc.get("step") or 1)
    if step <= 1:
        return f"/scenario/{sid}/type"
    if step == 2:
        return f"/scenario/{sid}/timeline" if doc.get("via_timeline") else f"/scenario/{sid}/input"
    if step == 3:
        return f"/scenario/{sid}/solutions"
    return f"/scenario/{sid}/result" if doc.get("scenes") and any(s.get("status") == "done" for s in doc["scenes"]) \
        else f"/scenario/{sid}/solutions"


def in_proposal(doc: dict[str, Any]) -> bool:
    return any(u.get("service") == "proposal" for u in doc.get("usages") or [])


def birdseye_changed(doc: dict[str, Any]) -> bool:
    link = doc.get("birdseye_link") or {}
    return bool(link.get("keep_link") and link.get("changed"))


def status_parts(doc: dict[str, Any]) -> tuple[str, str, str | None]:
    st = doc.get("status")
    if st == "done":
        return "완료", ("제안서에 사용 중" if in_proposal(doc) else "제안서에 아직 안 넣음"), None
    if st == "generating":
        gen = doc.get("generation") or {}
        total = int(gen.get("total") or len(doc.get("scenes") or []))
        k = min(total, int(gen.get("done") or 0) + 1) if total else 0
        return "생성 중", f"장면 {k} / {total} 작성 중", None
    if st == "failed":
        return "생성 멈춤", "다시 시도", "다시 시도"
    if birdseye_changed(doc):
        return "작성 중", "조감도가 바뀌었어요", None
    step = max(1, min(4, int(doc.get("step") or 1)))
    return "작성 중", f"{step} / 4 · {STEPS[step - 1]}", None


def start_label(doc: dict[str, Any]) -> str:
    mode = doc.get("start_mode")
    if mode == "template":
        ind = seed.industry((doc.get("template") or {}).get("industry") or doc.get("vertical_code"))
        return f"업종 템플릿 · {ind['short']}" if ind else "업종 템플릿"
    if mode == "birdseye":
        title = (doc.get("birdseye_link") or {}).get("title") or ""
        return f"조감도 · {title}" if title else "조감도"
    return "직접 입력"


def customer_line(doc: dict[str, Any]) -> str:
    return texts.join([doc.get("customer_name") or "", doc.get("space_label") or ""]) or "고객 · 공간 미정"


def summary_line(doc: dict[str, Any]) -> str:
    return texts.join([doc.get("customer_name") or "", doc.get("space_label") or "", f"장면 {len(doc.get('scenes') or [])}"])


async def register(doc: dict[str, Any]) -> None:
    label, sub, _ = status_parts(doc)
    await register_item(
        feature="SC", item_id=doc["id"], title=doc.get("title") or "새 시나리오", status=doc.get("status") or "draft",
        route=route_of(doc), summary=summary_line(doc), project_id=doc.get("project_id"),
        meta={"status": {"code": doc.get("status"), "label": label, "sub": sub}, "step": doc.get("step"),
              "scenes": len(doc.get("scenes") or []), "type": doc.get("type"), "start_mode": doc.get("start_mode"),
              "in_proposal": in_proposal(doc), "version": doc.get("version") or 0},
    )


# ── 응답 모양 ───────────────────────────────────────────────

def industry_out(doc: dict[str, Any]) -> dict[str, Any] | None:
    ind = seed.industry(doc.get("vertical_code"))
    return {k: ind[k] for k in ("code", "name", "short", "case_label")} if ind else None


def to_scenario(doc: dict[str, Any]) -> dict[str, Any]:
    """저장된 문서 → Scenario 응답. DocStore 의 version(작업본 수정 번호)은 rev, 저장 버전은 saved_version → version."""
    gen = doc.get("generation")
    return {
        "id": doc["id"], "title": doc.get("title") or "새 시나리오", "customer_name": doc.get("customer_name"),
        "space_label": doc.get("space_label") or "", "project_id": doc.get("project_id"), "vertical_code": doc.get("vertical_code"),
        "industry": industry_out(doc), "type": doc.get("type") or "with", "type_label": TYPE_LABEL[doc.get("type") or "with"],
        "type_sub": TYPE_SUB[doc.get("type") or "with"], "start_mode": doc.get("start_mode") or "blank", "template": doc.get("template"),
        "birdseye_link": doc.get("birdseye_link"), "aerial": doc.get("aerial") or {"enabled": False, "source": "new"},
        "raw_text": doc.get("raw_text") or "", "characters": doc.get("characters") or [],
        "removed_characters": doc.get("removed_characters") or [], "needs": doc.get("needs") or [],
        "status": doc.get("status") or "draft", "step": int(doc.get("step") or 1), "route": route_of(doc),
        "version": int(doc.get("saved_version") or 0), "rev": int(doc.get("version") or 0),
        "dirty": bool(doc.get("dirty")), "via_timeline": bool(doc.get("via_timeline")),
        "solution_picks": doc.get("solution_picks") or [], "product_picks": doc.get("product_picks") or [],
        "related_products": doc.get("related_products") or [], "related_for": doc.get("related_for"),
        "scene_count": len(doc.get("scenes") or []), "slot_count": len(doc.get("slots") or []),
        "role_count": len(doc.get("roles") or []),
        "generation": ({k: gen.get(k) for k in ("job_id", "status", "scope", "done", "total", "failed_reason")} if gen else None),
        "active_job": doc.get("active_job"), "parse": doc.get("parse"), "notices": doc.get("notices") or {},
        "usages": doc.get("usages") or [], "in_proposal": in_proposal(doc), "images_job": doc.get("images_job"),
        "anonymized": bool(doc.get("anonymized")), "last_saved_at": doc.get("last_saved_at"), "created_at": doc.get("created_at") or "", "updated_at": doc.get("updated_at") or "",
    }


def row_out(stored: dict[str, Any]) -> dict[str, Any]:
    label, sub, action = status_parts(stored)
    return {
        "id": stored["id"], "title": stored.get("title") or "새 시나리오", "customer_line": customer_line(stored),
        "start_mode": stored.get("start_mode") or "blank", "start_label": start_label(stored), "type": stored.get("type") or "with",
        "type_label": "with 솔루션" if stored.get("type") == "with" else "without", "scene_count": len(stored.get("scenes") or []),
        "status": stored.get("status") or "draft", "status_label": label, "status_sub": sub, "status_action": action,
        "birdseye_changed": birdseye_changed(stored), "in_proposal": in_proposal(stored), "route": route_of(stored),
        "updated_at": stored.get("updated_at") or "",
    }


# ── 장면 ──────────────────────────────────────────────────

_SENT = re.compile(r"(?<=[.!?。다])\s+")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.split(text or "") if s.strip()]


SNAP_KEYS = ("title", "story", "beats", "solutions", "products", "characters", "place", "space_key", "confirm_tokens", "evidence")


def scene_snapshot(sc: dict[str, Any]) -> dict[str, Any]:
    import copy
    return copy.deepcopy({k: sc.get(k) for k in SNAP_KEYS})


def product_key(p: dict[str, Any]) -> str:
    return str(p.get("family_id") or p.get("model_code") or p.get("short") or p.get("label") or "")


def sol_key(s: dict[str, Any]) -> str:
    return f"{s.get('solution_id')}:{s.get('action_code')}"


def mark_new(sc: dict[str, Any], prev: dict[str, Any] | None) -> None:
    """직전 버전에 없던 항목 → is_new(「새로」)."""
    if prev is None:
        for k in ("products", "solutions", "characters"):
            for it in sc.get(k) or []:
                it["is_new"] = False
        return
    pp = {product_key(p) for p in prev.get("products") or []}
    ps = {sol_key(s) for s in prev.get("solutions") or []}
    pc = {c.get("role_id") for c in prev.get("characters") or []}
    for p in sc.get("products") or []:
        p["is_new"] = product_key(p) not in pp
    for s in sc.get("solutions") or []:
        s["is_new"] = sol_key(s) not in ps
    for c in sc.get("characters") or []:
        c["is_new"] = c.get("role_id") not in pc


def changed_sentences(sc: dict[str, Any], prev: dict[str, Any] | None) -> list[str]:
    if prev is None:
        return []
    old = set(sentences(prev.get("story") or ""))
    return [s for s in sentences(sc.get("story") or "") if s not in old]


_GENERAL = (("Tab", "태블릿"), ("탭", "태블릿"), ("Kiosk", "키오스크"), ("키오스크", "키오스크"), ("Signage", "사이니지"),
            ("사이니지", "사이니지"), ("메뉴보드", "사이니지"), ("Flip", "전자칠판"), ("전자칠판", "전자칠판"), ("Wall", "LED 사이니지"),
            ("워치", "워치"), ("Watch", "워치"), ("에어컨", "에어컨"), ("모니터", "모니터"), ("TV", "TV"), ("스마트폰", "스마트폰"),
            ("Galaxy S", "스마트폰"))


def general_name(p: dict[str, Any]) -> str:
    """제품 → KB 카테고리 일반명(갤럭시 탭 → 「태블릿」). 모르면 약칭."""
    text = f"{p.get('label') or ''} {p.get('short') or ''} {p.get('category') or ''}"
    for needle, name in _GENERAL:
        if needle in text:
            return name
    if re.match(r"^[A-Z]{2}\d{2}[A-Z]$", p.get("short") or ""):
        return "사이니지"
    return p.get("short") or p.get("label") or "제품"


def stale_of(doc: dict[str, Any], sc: dict[str, Any]) -> dict[str, Any] | None:
    """이미지 생성 시점 조건 스냅숏(제품 · 인물 · 솔루션) ↔ 지금 장면 → 새로 생긴 제품 일반명 · 새 인물 → 「({요소} 장면 없음)」."""
    img = sc.get("image")
    if not img:
        return None
    snap = img.get("snapshot") or {}
    have_p = set(snap.get("products") or [])
    have_c = set(snap.get("characters") or [])
    missing: list[str] = []
    for p in sc.get("products") or []:
        if (p.get("short") or p.get("label")) not in have_p:
            g = general_name(p)
            if g not in missing:
                missing.append(g)
    if snap.get("characters") is not None:
        for c in sc.get("characters") or []:
            r = tl.role_by_id(doc, c.get("role_id"))
            if r and r["name"] not in have_c and r["name"] not in missing:
                missing.append(r["name"])
    if not missing and not sc.get("image_stale_forced"):
        return None
    return {"missing": missing}


def image_snapshot(doc: dict[str, Any], sc: dict[str, Any]) -> dict[str, Any]:
    names = []
    for c in sc.get("characters") or []:
        r = tl.role_by_id(doc, c.get("role_id"))
        if r:
            names.append(r["name"])
    return {"products": [p.get("short") or p.get("label") for p in sc.get("products") or []], "characters": names,
            "solutions": [s.get("label") for s in sc.get("solutions") or []]}


def product_chip(p: dict[str, Any]) -> str:
    s = p.get("short") or p.get("label") or ""
    return f"{s} ×{p['qty']}" if p.get("qty") and int(p["qty"]) > 1 else s


def scene_out(doc: dict[str, Any], sc: dict[str, Any], prev: dict[str, Any] | None = None) -> dict[str, Any]:
    slot = tl.slot_by_id(doc, sc.get("slot_id")) or {}
    beats = []
    for b in sc.get("beats") or []:
        r = tl.role_by_id(doc, b.get("role_id"))
        beats.append({**b, "label": (r or {}).get("name") or ""})
    chars = []
    for c in sc.get("characters") or []:
        r = tl.role_by_id(doc, c.get("role_id"))
        if r:
            chars.append({"role_id": c["role_id"], "name": r["name"], "is_new": bool(c.get("is_new"))})
    primary_role = next((b.get("role_id") for b in sc.get("beats") or [] if b.get("primary")), None)
    pov = [c["role_id"] for c in chars if c["role_id"] != primary_role]
    img = sc.get("image")
    if img:
        n = img.get("n")
        source = {"image_render": "이미지 생성", "image_flow": "이미지 생성", "picked": "내 이미지"}.get(img.get("source") or "", "이미지 생성")
        if str(img.get("version_id") or "").startswith("kb:image:"):
            source = "사내 자산"
        img = {**img, "label": texts.join([f"v{n}" if n else "", source, texts.relative_label(img.get("created_at"))])}
    title = sc.get("title") or ""
    return {
        "id": sc["id"], "no": sc.get("no") or 0, "slot_id": sc.get("slot_id"), "time": slot.get("time"), "label": slot.get("label") or "",
        "title": title, "short_title": texts.clip(title, 24), "place": sc.get("place") or "", "space_key": sc.get("space_key"),
        "story": sc.get("story") or "", "beats": beats, "solutions": sc.get("solutions") or [],
        "solution_chips": seed.chip_labels(sc.get("solutions") or []), "products": sc.get("products") or [],
        "characters": chars, "confirm_tokens": sc.get("confirm_tokens") or [], "evidence": sc.get("evidence") or [],
        "image": img, "image_request_id": sc.get("image_request_id"), "image_stale": stale_of(doc, sc),
        "image_job": sc.get("image_job"), "locked": bool(sc.get("locked")), "status": sc.get("status") or "waiting",
        "version": int(sc.get("version") or 0), "reason": sc.get("reason") or "", "zone_ref": sc.get("zone_ref"),
        "story_check": bool(sc.get("story_check")), "rewriting": bool(sc.get("rewriting")), "is_new": bool(sc.get("is_new")),
        "partial_story": sc.get("partial_story"), "changed_sentences": changed_sentences(sc, prev), "pov_role_ids": pov,
    }


async def prev_snapshot(sc: dict[str, Any]) -> dict[str, Any] | None:
    v = int(sc.get("version") or 0)
    if v < 2:
        return None
    pv = await repo.get_scene_version(sc["id"], v - 1)
    return (pv or {}).get("scene")


async def commit_scene_versions(doc: dict[str, Any], scene_ids: list[str], reason: str) -> None:
    """update 가 끝난 문서에서 장면 스냅숏을 버전으로 남긴다(scene.version 은 update 안에서 올려 둔다)."""
    for sid in scene_ids:
        sc = tl.scene_by_id(doc, sid)
        if sc is None or not sc.get("version"):
            continue
        await repo.put_scene_version(sid, int(sc["version"]), scene_snapshot(sc), reason, scenario_id=doc["id"])


def bump_scene(sc: dict[str, Any], reason: str) -> None:
    sc["version"] = int(sc.get("version") or 0) + 1
    sc["reason"] = reason


# ── 증거 · 수치 ─────────────────────────────────────────────

def evidence_corpus(doc: dict[str, Any], sc: dict[str, Any] | None = None) -> str:
    parts = [doc.get("raw_text") or "", " ".join(doc.get("needs") or [])]
    for s in doc.get("scenes") or []:
        for b in s.get("beats") or []:
            parts.append(b.get("text") or "")
    for p in doc.get("product_picks") or []:
        parts.append(f"{p.get('label')} {p.get('short')} {p.get('qty') or ''}")
    if sc is not None:
        for p in sc.get("products") or []:
            parts.append(f"{p.get('label')} {p.get('short')} {p.get('qty') or ''}")
        for e in sc.get("evidence") or []:
            if e.get("kind") in ("kb_message", "kb_case"):
                parts.append(e.get("text") or "")
    for r in doc.get("roles") or []:
        parts.append(" ".join([r.get("intro") or "", *(r.get("wants") or []), *(r.get("pains") or [])]))
    return "\n".join(parts)


def finalize_text(doc: dict[str, Any], sc: dict[str, Any]) -> None:
    """경쟁사 · 실존 인물 · 최상급 후처리 + 근거 없는 수치 [00] + confirm_tokens."""
    corpus = evidence_corpus(doc, sc)
    title = policy.clean(sc.get("title") or "")
    story = policy.clean(sc.get("story") or "")
    title, _ = policy.mark_unsupported(title, corpus)
    story, _ = policy.mark_unsupported(story, corpus)
    sc["title"] = title
    sc["story"] = story
    for b in sc.get("beats") or []:
        b["text"] = policy.clean(b.get("text") or "")
    sc["confirm_tokens"] = policy.placeholder_tokens(title) + policy.placeholder_tokens(story)


# ── 잡 ────────────────────────────────────────────────────

async def enqueue(kind: str, doc: dict[str, Any], payload: dict[str, Any], *, title: str | None = None,
                  scene_id: str | None = None, job_id: str | None = None) -> str:
    job = await jobs().enqueue("scenario", kind, {"scenario_id": doc["id"], **payload},
                               title=title or doc.get("title") or "공간 시나리오", ref=doc["id"],
                               project_id=doc.get("project_id"), job_id=job_id)
    return job.id


def set_active(doc: dict[str, Any], job_id: str | None, kind: str | None = None, scene_id: str | None = None) -> None:
    doc["active_job"] = {"job_id": job_id, "kind": kind, "scene_id": scene_id} if job_id else None


async def clear_active(sc_id: str, job_id: str) -> None:
    def fn(d: dict[str, Any]) -> dict[str, Any] | None:
        aj = d.get("active_job") or {}
        if aj.get("job_id") != job_id:
            return None
        d["active_job"] = None
        return d
    try:
        await repo.update(sc_id, fn)
    except ApiError:
        pass


def require_editable(doc: dict[str, Any]) -> None:
    if doc.get("status") == "generating":
        raise ApiError(409, "GENERATION_IN_PROGRESS", "시나리오를 생성하는 중이에요. 끝난 뒤에 고쳐 주세요.",
                       {"job_id": (doc.get("generation") or {}).get("job_id")})


def new_scenario_id() -> str:
    return new_id("sc")
