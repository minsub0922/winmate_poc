"""REST 처리 3 — 요구 추적 · 일정 · 내보내기 · 공유 · 검토 요청 · 다음 작업 넘기기 · 제안서 넘김(§6.5, 10-proposal §8.0)."""
from __future__ import annotations

import logging
import re
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError
from winmate_common.ids import now_iso

from . import llm, ops_outline, repo, rq, rules, service
from .models import ExportRequest, PutResolution
from .tracebuild import LINK_ORDER

log = logging.getLogger("winmate.storyboard.ops")


# ── 요구 추적 ──────────────────────────────────────────────

def _item(d: dict[str, Any], rq_item_id: str) -> dict[str, Any]:
    it = next((i for i in (d.get("trace") or {}).get("items") or [] if i["rq_item_id"] == rq_item_id or i["code"] == rq_item_id),
              None)
    if it is None:
        raise ApiError(404, "NOT_FOUND", f"추적 항목을 찾을 수 없어요: {rq_item_id}")
    return it


def place_result_label(d: dict[str, Any], it: dict[str, Any], target: dict[str, Any]) -> str:
    if target["kind"] == "space":
        others = [p["label"].replace("Part 2", "").strip() for p in it.get("places") or [] if p["kind"] == "space"
                  and p.get("id") != target["id"]]
        name = target["label"]
        return f"{name}{' · ' + ' · '.join(others) if others else ''}에 넣음"
    return f"{target['label']}에 넣음"


RESULT_BADGE = {"place": "직접", "keep_unconfirmed": "확인 필요", "ask_customer": "확인 필요", "defer_main": "보류", "exclude": "제외"}
RESULT_LINK = {"place": "direct", "keep_unconfirmed": "unconfirmed", "ask_customer": "unconfirmed", "defer_main": "deferred",
               "exclude": "excluded"}


async def resolve(sb_id: str, rq_item_id: str, body: PutResolution) -> tuple[dict[str, Any], str | None]:
    doc = await repo.require_sb(sb_id)
    if not doc.get("trace"):
        raise ApiError(409, "PREPARE_NOT_READY", "요구 추적이 아직 없어요")
    it = _item(doc, rq_item_id)
    if body.kind == "exclude" and not (body.reason or "").strip():
        raise ApiError(422, "REASON_REQUIRED", "제외 사유를 적어 주세요")
    option = None
    if body.kind == "place":
        option = next((o for o in ((it.get("question") or {}).get("options") or []) if o["id"] == body.option_id
                       and o["kind"] == "place"), None)
        if option is None or not option.get("target"):
            raise ApiError(422, "VALIDATION_FAILED", "놓을 곳을 골라 주세요", {"option_id": body.option_id})
    cq: dict[str, Any] | None = None
    if body.kind == "ask_customer":
        ref = doc.get("requirement_ref") or {}
        short = it.get("short") or it.get("text", "")[:24]
        cq = await rq.add_customer_question(
            ref["requirement_id"], sb_id=sb_id, text=f"'{short}' 관련 범위와 근거 자료를 알려 주실 수 있을까요?",
            short_label=short, place_label=it.get("places_label") or "요구 추적",
            target={"kind": "item", "id": it["rq_item_id"]})
    out: dict[str, Any] = {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        item = _item(d, rq_item_id)
        kind = body.kind
        if kind == "place":
            label = place_result_label(d, item, option["target"])  # type: ignore[index]
        elif kind == "keep_unconfirmed":
            label = "확인 필요로 유지 — 추정하지 않음"
        elif kind == "ask_customer":
            label = "고객에게 묻기"
            if not any(p["kind"] == "customer_question" for p in item["places"]):
                item["places"].append({"kind": "customer_question", "id": (cq or {}).get("id"), "label": "고객에게 묻기"})
        elif kind == "defer_main":
            label = "본제안으로 미룸"
        else:
            label = f"제외 — {(body.reason or '').strip()}"
        item["resolution"] = {"kind": kind, "option_id": body.option_id, "reason": (body.reason or "").strip() or None,
                              "result_label": label, "badge": RESULT_BADGE[kind], "at": now_iso()}
        item["state"] = "resolved"
        # 연결 유형은 정리 전 연결에서 다시 계산(다시 정리해도 앞 결과가 남지 않게). 놓기 · 미루기 · 제외는 `미확인` 을 덜어 낸다
        base = item.get("base_link_types")
        if base is None:
            base = list(item.get("link_types") or [])
            item["base_link_types"] = base
        links = [x for x in base if not (kind in ("place", "defer_main", "exclude") and x == "unconfirmed")]
        if RESULT_LINK[kind] not in links:
            links.append(RESULT_LINK[kind])
        item["link_types"] = sorted(links, key=lambda x: LINK_ORDER.index(x) if x in LINK_ORDER else len(LINK_ORDER))
        secs = {s["id"]: s for s in (d.get("outline") or {}).get("sections") or []}
        spaces = {s["id"]: s for s in (d.get("outline") or {}).get("spaces") or []}
        item["places_label"] = rules.places_label(item["places"], secs, spaces) or item.get("places_label")
        out.update(item)
        return d

    await service.mutate(sb_id, fn)
    job_id = None
    if body.kind == "place":
        job_id = await service.enqueue(sb_id, "sb.trace.apply", {"rq_item_id": it["rq_item_id"], "option_id": body.option_id},
                                       active=False)
    return out, job_id


async def ack_extensions(sb_id: str) -> None:
    await repo.require_sb(sb_id)

    def fn(d: dict[str, Any]) -> dict[str, Any] | None:
        tr = d.get("trace")
        if not tr:
            return None
        for e in tr.get("extensions") or []:
            e["acknowledged"] = True
        tr["extensions_acknowledged"] = True
        return d

    await service.mutate(sb_id, fn, content=False)


# ── 내보내기 ──────────────────────────────────────────────

async def start_export(sb_id: str, body: ExportRequest) -> str:
    doc = await service.load(sb_id)
    if not (doc.get("outline") or {}).get("ready"):
        raise ApiError(409, "PREPARE_NOT_READY", "목차가 다 만들어진 뒤에 내보낼 수 있어요")
    if doc.get("has_unsaved_changes") or not doc.get("saved_version"):
        await ops_outline.save(sb_id, None)      # 작업본이 최신 버전과 다르면 먼저 저장(에이전트 자동)
        doc = await repo.require_sb(sb_id)
    return await service.enqueue(sb_id, "sb.export", {"format": body.format, "options": body.options.model_dump(),
                                                      "version": doc.get("saved_version")}, active=False, doc=doc)


# ── 공유 · 검토 · 넘기기 ────────────────────────────────────

async def share(sb_id: str) -> str:
    doc = await repo.require_sb(sb_id)
    try:
        res = await ServiceClient("workspace").post("/v1/share-links", json={
            "target": f"storyboard:{sb_id}", "route": f"/storyboard/{sb_id}/outline/all", "title": doc.get("title") or ""})
    except ApiError as exc:
        raise ApiError(502, "UPSTREAM_FAILED", "공유 링크를 만들지 못했어요", {"upstream": exc.code}) from exc
    return res.get("url") or f"/share/{res.get('token', '')}"


async def review_request(sb_id: str, note: str | None, reviewers: list[str] | None = None) -> dict[str, Any]:
    doc = await repo.require_sb(sb_id)
    if not doc.get("saved_version"):
        raise ApiError(409, "PREPARE_NOT_READY", "저장한 뒤에 검토를 요청할 수 있어요")
    ws = ServiceClient("workspace")
    me = service.owner_now()["id"]
    if not reviewers:
        try:
            users = (await ws.get("/v1/users")).get("items") or []
        except ApiError:
            users = []
        other = next((u["id"] for u in users if u.get("id") != me), None)
        reviewers = [other or me]
    try:
        res = await ws.post("/v1/reviews", json={
            "target": f"storyboard:{sb_id}:v{doc['saved_version']}", "title": f"{doc.get('title')} · 스토리보드 v{doc['saved_version']}",
            "route": f"/storyboard/{sb_id}/outline/all", "reviewers": reviewers, "message": note})
    except ApiError as exc:
        raise ApiError(502, "UPSTREAM_FAILED", "검토 요청을 보내지 못했어요", {"upstream": exc.code}) from exc

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["review_requested"] = True
        d["status"] = "shared"
        return d

    await service.mutate(sb_id, fn, content=False)
    return {"review_id": res.get("id"), "status": res.get("status") or "requested"}


def _part1_codes_label(codes: list[str]) -> str:
    if not codes:
        return ""
    return "Part " + " · ".join(codes)


async def _mi_topic(doc: dict[str, Any]) -> dict[str, Any]:
    h = rules.content_hash(doc)
    cached = doc.get("mi_topic") or {}
    if cached.get("hash") == h:
        return cached
    secs = [s for s in (doc.get("outline") or {}).get("sections") or [] if s.get("status") == "needs_confirmation"]
    codes_fallback = [s.get("code") for s in secs if s["group_key"] == "part1" and s.get("code")][:2]
    res = {"hash": h, "codes": codes_fallback, "find": (f"{secs[0]['name']} 수치의 출처 찾기" if secs else "시장 · 고객 근거 찾기")}
    if secs:
        try:
            out = await llm.call("sb.mi_topic", llm.p_mi_topic([{"code": s.get("code"), "name": s["name"],
                                                                 "lines": [ln["text"] for ln in s.get("lines") or []]} for s in secs]),
                                 llm.SbMiTopic)
            codes = [c for c in out.get("codes") or [] if re.match(r"^\d-\d+$", c)]
            res.update(codes=codes or codes_fallback, find=(out.get("find") or res["find"]).strip())
        except ApiError as exc:
            log.info("MI 주제 LLM 없이: %s", exc.code)

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["mi_topic"] = res
        return d

    await service.mutate(doc["id"], fn, content=False)
    return res


async def handoff_cards(sb_id: str) -> list[dict[str, Any]]:
    doc = await repo.require_sb(sb_id)
    rq_id = (doc.get("requirement_ref") or {}).get("requirement_id") or ""
    spaces = (doc.get("outline") or {}).get("spaces") or []
    n = len(spaces)
    done = {h["target"] for h in doc.get("handoffs") or []}
    mi = await _mi_topic(doc)
    codes = _part1_codes_label(mi.get("codes") or [])
    complete = [sp["name"] for sp in spaces if sp.get("filled_count") == 5 and sp.get("status") == "supplemented"]
    sc_desc = f"Part 2의 {n}개 공간을 시트로"
    if complete:
        names = " · ".join(complete)
        sc_desc += f" — {names}{rules.eun(complete[-1])} 5칸 그대로"
    return [
        {"target": "proposal", "title": "B2B 제안서", "emphasized": True, "done": "proposal" in done,
         "description": f"Part 1 → MI · VP · Part 2 → 공간 시나리오 {n}장 · Part 3 → Why Samsung",
         "route": f"/proposal/new?sb={sb_id}&rq={rq_id}"},
        {"target": "mi", "title": "Market Intelligence", "done": "mi" in done,
         "description": f"{codes} 근거 — {mi.get('find')}" if codes else f"근거 — {mi.get('find')}",
         "route": f"/mi/new?rq={rq_id}&sb={sb_id}"},
        {"target": "scenario", "title": "공간 시나리오", "done": "scenario" in done, "description": sc_desc,
         "route": f"/scenario/new?sb={sb_id}"},
    ]


async def handoff(sb_id: str, target: str) -> str:
    cards = await handoff_cards(sb_id)
    card = next((c for c in cards if c["target"] == target), None)
    if card is None:
        raise ApiError(404, "NOT_FOUND", f"넘길 곳을 찾을 수 없어요: {target}")

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d.setdefault("handoffs", []).append({"target": target, "at": now_iso()})
        d["status"] = "shared"
        return d

    await service.mutate(sb_id, fn, content=False)
    return card["route"]


# ── 제안서 넘김(ProposalHandoff v1) ─────────────────────────

def _facts(doc: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    outline = doc.get("outline") or {}
    for s in outline.get("sections") or []:
        for ln in s.get("lines") or []:
            for i, tok in enumerate(rules.tokens_of(ln.get("text", ""))):
                out.append({"key": f"{s['key']}.{ln['id']}.{i}", "label": f"{rules.section_label(s)} · {ln['text'][:40]}",
                            "status": "placeholder", "placeholder": tok})
    for sp in outline.get("spaces") or []:
        for k, sl in (sp.get("slots") or {}).items():
            for i, tok in enumerate(rules.tokens_of(rules.slot_text(sl))):
                out.append({"key": f"space:{sp['key']}.{k}.{i}", "label": f"{rules.space_label(sp)} · {rules.SLOT_FULL[k]}",
                            "status": "placeholder", "placeholder": tok})
    return out


async def proposal_handoff(sb_id: str, proposal_type: str, section: str | None) -> dict[str, Any]:
    doc = await repo.require_sb(sb_id)
    ref = doc.get("requirement_ref") or {}
    outline = doc.get("outline") or {}
    dr = doc.get("direction") or {}
    opt = next((o for o in dr.get("options") or [] if o["id"] == dr.get("selected_option_id")), None) or {}
    msgs = [{"id": m["id"], "text": m["text"], "place_label": m["place_label"], "audience": m.get("audience"),
             "axis_label": m.get("axis_label"), "open_flags": sum(1 for f in m.get("flags") or [] if f["kind"] == "unverified_claim"
                                                                  and f["state"] != "applied")} for m in dr.get("key_messages") or []]
    items: list[dict[str, Any]] = []
    sec_key = (section or "").lower()
    if sec_key in ("", "vp", "value_props") and msgs:
        warn = sum(m["open_flags"] for m in msgs)
        items.append({"key": "key_messages", "label": f"Key Message {len(msgs)}", "from_label": "기획 방향 · 핵심 메시지",
                      "sheet_role": "VP", "sheet_title": "가치 제안", "template_hint": {"code": "VP-B", "name": "가치 기둥"},
                      "status": "warn" if warn else "ok", "status_label": f"[확인 필요] {warn}건" if warn else "그대로 들어가요",
                      "include_default": True,
                      "content": {"pillars": [{"title": m["place_label"], "text": m["text"], "audience": m.get("audience")} for m in msgs]},
                      "sources": [{"kind": "storyboard", "ref": sb_id, "label": "Storyboard"}]})
    if sec_key in ("", "mi", "why", "outline"):
        for g in ("part1", "part3"):
            secs = [s for s in outline.get("sections") or [] if s["group_key"] == g]
            if not secs or (sec_key == "mi" and g != "part1") or (sec_key == "why" and g != "part3"):
                continue
            nc = sum(1 for s in secs if s.get("status") in ("needs_confirmation", "tbd"))
            grp = next((x for x in outline.get("groups") or [] if x["key"] == g), {})
            items.append({"key": f"outline.{g}", "label": grp.get("name") or g, "from_label": "목차",
                          "sheet_role": "CB" if g == "part1" else "ST", "sheet_title": grp.get("name"),
                          "status": "warn" if nc else "ok", "status_label": f"[확정 필요] {nc}건" if nc else "그대로 들어가요",
                          "include_default": True,
                          "content": {"sections": [{"code": s.get("code"), "name": s["name"], "direction": s.get("direction"),
                                                    "lines": [ln["text"] for ln in s.get("lines") or []], "status": s.get("status"),
                                                    "products": [p["name"] for p in s.get("products") or []]} for s in secs]},
                          "sources": [{"kind": "storyboard", "ref": sb_id, "label": "Storyboard"}]})
    if sec_key in ("", "space_scenario", "solution", "scenario"):
        for sp in outline.get("spaces") or []:
            full = sp.get("filled_count") == 5
            items.append({"key": f"space.{sp['key'] or sp['id']}", "label": f"Part 2 {sp['name']}", "from_label": "Part 2 공간 시나리오",
                          "sheet_role": "SS", "sheet_title": sp["name"], "status": "ok" if full else "warn",
                          "status_label": "그대로 들어가요" if full else f"5칸 중 {sp.get('filled_count', 0)}칸",
                          "include_default": True, "repeat_key": {"kind": "space", "ref": sp["id"], "label": sp["name"]},
                          "content": {"purpose": sp.get("purpose"), "slots": {k: rules.slot_text((sp.get("slots") or {}).get(k))
                                                                                for k in rules.SLOT_KEYS},
                                      "products": [p["name"] for p in sp.get("products") or []],
                                      "is_extension": sp.get("is_extension", False)},
                          "sources": [{"kind": "storyboard", "ref": sb_id, "label": "Storyboard"}]})
    audience = []
    for m in msgs:
        if m.get("audience") and m["audience"] not in audience:
            audience.append(m["audience"])
    return {
        "source": {"feature": "storyboard", "ref_id": sb_id, "version": int(doc.get("saved_version") or 0),
                   "title": doc.get("title") or "", "updated_at": doc.get("updated_at") or "", "route": doc.get("route") or ""},
        "target": {"proposal_type": proposal_type or "standard", "section_key": section or "all"},
        "customer": {"name": doc.get("customer_name"), "decision_makers": " · ".join(audience) or None},
        "rq_ref": {"rq_id": ref["requirement_id"], "version": int(ref.get("version") or 0)} if ref.get("requirement_id") else None,
        "key_messages": msgs, "strategy": {"title": opt.get("title"), "one_liner": opt.get("one_liner"), "audience": audience,
                                           "mapping": opt.get("mapping") or []},
        "items": items, "facts": _facts(doc), "assets": [], "live_link": False,
    }
