"""연결 자료 읽기 — storyboard · mi · requirements · kb(사례) · 이전 VP · workspace(연결 후보).

다른 서비스는 계약대로 `ServiceClient` 로만 부른다. 실패하면 그 자료만 비우고 계속한다(화면이 멈추지 않게).
결과 = {title, candidates(재료 후보), gives(뽑을 수 있는 재료 요약), industry(상속 후보), customer, extra}
"""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError

from . import kbx, materials, repo

log = logging.getLogger("winmate.vp.sources")

KIND_LABEL = {"storyboard": "Storyboard", "mi": "Market Intelligence", "requirements": "고객 요구사항", "case": "유관 사례",
              "vp": "이전 가치 제안", "rfp": "RFP", "quote": "견적"}
FEATURE_KIND = {"SB": "storyboard", "MI": "mi", "RQ": "requirements", "VP": "vp"}
KIND_ICON = {"storyboard": "sb", "mi": "mi", "requirements": "rq", "case": "case", "vp": "vp"}


def _axes_label(axes: list[str]) -> str:
    ko = {"challenge": "과제", "value": "가치", "evidence": "근거", "stakeholder": "이해관계자"}
    return " · ".join(ko[a] for a in axes if a in ko)


def gives_of(cands: list[dict[str, Any]], kind: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    c = {"challenge": 0, "value": 0, "evidence": 0, "stakeholder": 0, "km": 0, "requirements": 0, "users": 0, "strengths": 0,
         "numbers": 0, "kpis": 0}
    for x in cands:
        c[x["axis"]] = c.get(x["axis"], 0) + 1
        if x.get("km_id"):
            c["km"] += 1
        if x["tag"] == "RQ" and x["axis"] == "challenge":
            c["requirements"] += 1
        if x.get("mi_user"):
            c["users"] += 1
        if x.get("strength"):
            c["strengths"] += 1
        if x["axis"] == "evidence":
            c["numbers"] += 1
        if x.get("kpi_id"):
            c["kpis"] += 1
    if kind == "storyboard":
        parts = [f"Key Message {c['km']}"] + ([f"요구사항 {c['requirements']}"] if c["requirements"] else [])
        axes = ["value"] + (["challenge"] if c["requirements"] else [])
    elif kind == "mi":
        ch = sum(1 for x in cands if x["axis"] == "challenge")
        parts = [f"과제 {ch}", f"사용자 {c['users']}", f"삼성 강점 {c['strengths']}", f"수치 {c['numbers']}"]
        axes = ["challenge", "evidence", "stakeholder"]
    elif kind == "requirements":
        parts = [f"요구사항 {c['requirements']}", f"키맨 {sum(1 for x in cands if x['axis'] == 'stakeholder')}"]
        axes = ["challenge", "stakeholder"]
    elif kind == "case":
        labels = (extra or {}).get("kpi_labels") or []
        parts = [f"효과 수치 {c['kpis']}" + (f" ({' · '.join(labels[:2])})" if labels else "")]
        axes = ["evidence"]
    else:
        parts = [f"재료 {len(cands)}"]
        axes = sorted({x["axis"] for x in cands if x["axis"] in ("challenge", "value", "evidence", "stakeholder")})
    target = "기대 효과" if kind == "case" else _axes_label(axes)
    summary = " · ".join(p for p in parts if p) + (f" → {target}" if target else "")
    counts = {k: v for k, v in c.items() if v}
    return {"summary": summary, "counts": counts, "axes": axes}


async def load_storyboard(sb_id: str) -> dict[str, Any]:
    sb = ServiceClient("storyboard")
    doc = await sb.get(f"/v1/storyboards/{sb_id}")
    kms = (await sb.get(f"/v1/storyboards/{sb_id}/key-messages")).get("items") or []
    rq_items: list[dict[str, Any]] = []
    keymen: list[dict[str, Any]] = []
    ref = doc.get("requirement_ref") or {}
    if ref.get("requirement_id") and ref.get("version"):
        try:
            snap = await ServiceClient("requirements").get(f"/v1/requirements/{ref['requirement_id']}/versions/{ref['version']}")
            s = snap.get("snapshot") or {}
            rq_items = list(s.get("items_flat") or [])
            keymen = list(s.get("keymen") or [])
        except Exception as exc:  # noqa: BLE001
            log.warning("정의서 읽기 실패 %s: %s", ref.get("requirement_id"), exc)
    industry = None
    try:
        h = await sb.get(f"/v1/storyboards/{sb_id}/proposal-handoff", params={"type": "standard", "section": "vp"})
        ic = ((h or {}).get("customer") or {}).get("industry_code")
        if ic:
            industry = {"code": ic, "source": "storyboard", "label": "Storyboard"}
    except Exception as exc:  # noqa: BLE001
        log.info("storyboard proposal-handoff 없음 %s: %s", sb_id, exc)
    cands = materials.from_storyboard(sb_id, kms, rq_items=rq_items, keymen=keymen)
    return {"title": doc.get("title") or sb_id, "candidates": cands, "gives": gives_of(cands, "storyboard"), "industry": industry,
            "customer": doc.get("customer_name"), "project_id": doc.get("project_id"), "version": doc.get("version"),
            "extra": {"kms": kms, "rq_ref": ref}}


async def load_mi(mi_id: str) -> dict[str, Any]:
    mi = ServiceClient("mi")
    bundle = await mi.get(f"/v1/analyses/{mi_id}/bundle", params={"target": "vp"})
    title = mi_id
    version = bundle.get("version")
    try:
        a = await mi.get(f"/v1/analyses/{mi_id}")
        title = a.get("title") or title
        if version:
            title = f"{title} v{version}" if not title.rstrip().endswith(f"v{version}") else title
    except Exception as exc:  # noqa: BLE001
        log.info("MI 제목 읽기 실패 %s: %s", mi_id, exc)
    seg = ((bundle.get("customer") or {}).get("segment")) or bundle.get("segment")
    industry = {"code": seg, "source": "mi", "label": f"MI v{version}" if version else "MI"} if seg else None
    cands = materials.from_mi(mi_id, bundle)
    return {"title": title, "candidates": cands, "gives": gives_of(cands, "mi"), "industry": industry,
            "customer": (bundle.get("customer") or {}).get("name"), "version": version,
            "extra": {"sheets": len(bundle.get("sheets") or []), "usage": bundle.get("usage")}}


async def load_requirements(rq_id: str) -> dict[str, Any]:
    snap = await ServiceClient("requirements").get(f"/v1/requirements/{rq_id}/versions/latest")
    cands = materials.from_requirements(rq_id, snap)
    return {"title": snap.get("title") or rq_id, "candidates": cands, "gives": gives_of(cands, "requirements"), "industry": None,
            "customer": snap.get("customer_name"), "project_id": snap.get("project_id"), "version": snap.get("version"),
            "extra": {}}


async def load_case(dep_id: str, idx: int = 1) -> dict[str, Any]:
    dep = await kbx.case_detail(dep_id) or {"id": dep_id, "title": dep_id}
    kpis = await kbx.case_kpis([dep_id])
    cands = materials.from_case(dep, kpis, idx)
    labels = [k.get("text", "")[:12] for k in kpis if k.get("has_number")]
    return {"title": dep.get("title") or dep_id, "candidates": cands, "gives": gives_of(cands, "case", {"kpi_labels": labels}),
            "industry": None, "customer": None, "extra": {"deployment": dep, "kpis": kpis}}


async def load_vp(vp_id: str) -> dict[str, Any]:
    doc = await repo.require_vp(vp_id)
    cands = materials.from_vp(vp_id, doc)
    ind = doc.get("industry") or {}
    return {"title": doc.get("title") or vp_id, "candidates": cands, "gives": gives_of(cands, "vp"),
            "industry": {"code": ind["code"], "source": "vp", "label": "이전 가치 제안"} if ind.get("code") and ind["code"] != "GEN" else None,
            "customer": doc.get("customer_name"), "extra": {}}


async def load(kind: str, ref_id: str, idx: int = 1) -> dict[str, Any]:
    try:
        if kind == "storyboard":
            return await load_storyboard(ref_id)
        if kind == "mi":
            return await load_mi(ref_id)
        if kind == "requirements":
            return await load_requirements(ref_id)
        if kind == "case":
            return await load_case(ref_id, idx)
        if kind == "vp":
            return await load_vp(ref_id)
    except ApiError as exc:
        log.warning("자료 읽기 실패 %s %s: %s %s", kind, ref_id, exc.code, exc.message)
        return {"title": ref_id, "candidates": [], "gives": {"summary": "읽지 못했어요", "counts": {}, "axes": []}, "error": exc.message}
    except Exception as exc:  # noqa: BLE001
        log.warning("자료 읽기 실패 %s %s: %s", kind, ref_id, exc)
        return {"title": ref_id, "candidates": [], "gives": {"summary": "읽지 못했어요", "counts": {}, "axes": []}, "error": str(exc)}
    return {"title": ref_id, "candidates": [], "gives": {"summary": "", "counts": {}, "axes": []}}


async def workspace_items(feature: str, q: str | None, *, limit: int = 20) -> list[dict[str, Any]]:
    try:
        r = await ServiceClient("workspace").get("/v1/items", params={"feature": feature, "q": q or None, "owner": "all", "limit": limit})
        return list((r or {}).get("items") or [])
    except Exception as exc:  # noqa: BLE001
        log.warning("workspace 항목 읽기 실패 %s: %s", feature, exc)
        return []


def short_customer(name: str | None) -> str:
    """`A 커피 프랜차이즈` → 검색어 `A 커피`(앞 두 낱말)."""
    words = (name or "").split()
    return " ".join(words[:2]) if len(words) > 2 else (name or "")
