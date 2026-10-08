"""가치 맵(새 VP 흐름, 2026-10-08 — 보드 webapp1 VP2 · VP2_AI · VP2_Pick · VP2_Detail · VpDetail · VP_DoneJson).

제품 · 솔루션마다 가치를 여러 개 두고, 가치마다 '고객의 니즈'(고객이 할 말처럼 쓴 한 문장)를 붙인다.
- 사용자가 VP 에 넣을 제품 · 솔루션을 고른다(DSS 후보 + 카탈로그). 고른 것만 저장된다.
- 가치: 공간 · 가치 메시지 · 고객의 니즈 · 연결 요구 · 출처(manual · ai-pending · ai-accepted).
- 니즈: 직접 쓰거나 AI 로 추론(`ai-pending` → 수락하면 `ai-accepted`). AI 가 먼저 묻지 않는다 — 버튼으로만.
- 'AI 가치 매칭 추천' = KB 원문 메시지(E1, 제품군 · 솔루션) + 요구 문장 → 가치 후보(니즈 포함) · 빈 니즈 추론. 점선(ai-pending)으로 넣고 수락해야 들어간다.
  LLM 이 없거나(mock · 장애) 답이 비면 KB 원문 메시지를 그대로 가치 후보로 쓰고(출처 표시), 니즈는 비워 둔다(지어내지 않는다).
- 연결된 가치 전체 = 이 맵 + 같은 제품 · 솔루션을 쓴 다른 맵의 가치 + KB 공식 메시지. 다른 맵 가치는 가져오기(복사)할 수 있다.
- 저장하면 Storyboard flow.json 의 `stages.vp` 모양(`stage()`)을 만든다.

저장소: DocStore("vp") 컬렉션 `value_maps`(vmap_ …). 쓰기는 낙관적 잠금 + 재시도.
"""
from __future__ import annotations

import asyncio
import copy
import logging
import re
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, Field
from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso
from winmate_common.platform import register_item
from winmate_common.store import VersionConflict

from . import kbx, llm, repo

log = logging.getLogger("winmate.vp.valuemap")

COLL = "value_maps"
MAX_VALUES_PER_ITEM = 8
SUGGEST_PER_ITEM = 2

By = Literal["manual", "ai-pending", "ai-accepted"]


# ── 모델(API) ───────────────────────────────────────────

class VMNeed(BaseModel):
    text: str
    by: By = "manual"


class VMValue(BaseModel):
    id: str
    space: str = Field(description="공간(로비 · 회의실 …) 또는 '전체'")
    message: str = Field(description="고객에게 주는 가치 한 문장")
    need: VMNeed | None = Field(None, description="고객의 니즈 — 고객이 할 말처럼 쓴 한 문장(예: 여름에도 쾌적한 교실 환경이 필요해요)")
    req: str | None = Field(None, description="연결 요구(예: RQ-01 에너지 20% 절감)")
    by: By = "manual"
    basis: str | None = Field(None, description="AI 후보의 근거(KB 메시지 원문 출처 · 요구)")


class VMItem(BaseModel):
    key: str = Field(description="맵 안에서 제품 · 솔루션을 가리키는 키(이름에서 만든 slug)")
    name: str
    kind: Literal["product", "solution"]
    ref: str | None = Field(None, description="KB 참조 — kb:family:fam_… · kb:solution:sol_… · kb:model:…")
    spaces: list[str] = Field(default_factory=list)
    from_dss: bool = True
    values: list[VMValue] = Field(default_factory=list)


class VMCandidate(BaseModel):
    name: str
    kind: Literal["product", "solution"]
    ref: str | None = None
    spaces: list[str] = Field(default_factory=list)


class VMCounts(BaseModel):
    items: int
    values: int
    needs: int
    needs_missing: int
    pending: int


class VMDoc(BaseModel):
    id: str
    code: str | None = Field(None, description="화면 · flow.json 에 쓰는 짧은 번호(VP-01 …)")
    title: str
    sb_id: str | None = None
    context_text: str | None = Field(None, description="요구 · Storyboard 요약(AI 추천 문맥)")
    candidates: list[VMCandidate] = Field(default_factory=list, description="DSS 에서 온 고를 수 있는 제품 · 솔루션")
    items: list[VMItem] = Field(default_factory=list, description="고른 제품 · 솔루션(이 순서로 보인다)")
    status: Literal["draft", "done"] = "draft"
    counts: VMCounts
    version: int
    created_at: str
    updated_at: str


class VMListItem(BaseModel):
    id: str
    code: str | None = None
    title: str
    sb_id: str | None = None
    status: str
    counts: VMCounts
    updated_at: str


class VMList(BaseModel):
    items: list[VMListItem]
    next_cursor: str | None = None


class VMCreate(BaseModel):
    title: str | None = None
    sb_id: str | None = None
    context_text: str | None = Field(None, max_length=8000)
    candidates: list[VMCandidate] | None = Field(None, description="DSS 제품 · 솔루션. 없으면 context_text 로 KB S1 에서 공간별 후보를 찾는다")
    select_all: bool = Field(True, description="후보를 처음부터 모두 고른다")


class VMSetItems(BaseModel):
    items: list[VMCandidate] = Field(description="고를 제품 · 솔루션(순서대로). 빠진 것의 가치는 지운다")


class VMAddValue(BaseModel):
    space: str = "전체"
    message: str = Field(min_length=1, max_length=200)
    need: str | None = Field(None, max_length=200)
    req: str | None = Field(None, max_length=120)


class VMPatchValue(BaseModel):
    space: str | None = None
    message: str | None = Field(None, max_length=200)
    need: str | None = Field(None, max_length=200, description="빈 문자열이면 니즈를 지운다")
    req: str | None = None
    accept: bool | None = Field(None, description="AI 가치 후보 수락(ai-pending → ai-accepted)")
    accept_need: bool | None = Field(None, description="AI 니즈 추론 수락")


class VMSuggestBody(BaseModel):
    item_keys: list[str] | None = Field(None, description="이 제품 · 솔루션만(없으면 고른 것 모두)")


class VMSuggestResult(BaseModel):
    map: VMDoc
    added_values: int
    added_needs: int
    mode: Literal["llm", "kb_only"] = Field(description="llm = 모델이 다듬음 · kb_only = 모델 없이 KB 원문 메시지만(니즈는 비움)")


class VMInferNeedResult(BaseModel):
    map: VMDoc
    need: VMNeed | None
    reason: str | None = None


class VMLinkedValue(BaseModel):
    space: str
    message: str
    need: str | None = None
    req: str | None = None
    by: str
    map_id: str
    map_title: str
    sb_id: str | None = None
    value_id: str


class VMOfficialMessage(BaseModel):
    level: str
    text: str
    source_url: str | None = None
    claim_flag: bool = False


class VMLinked(BaseModel):
    item: VMItem
    here: list[VMLinkedValue]
    other: list[VMLinkedValue]
    official: list[VMOfficialMessage] = Field(description="KB 원문 메시지(삼성 공식 · 원문 그대로)")


class VMImportValue(BaseModel):
    from_map: str
    value_id: str


class VMStageOut(BaseModel):
    stage: dict[str, Any] = Field(description="Storyboard flow.json 의 stages.vp")
    summary_md: str


# ── 저장소 ──────────────────────────────────────────────

def _store():
    return repo.store()


def slug(name: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z가-힣]+", "-", (name or "").strip().lower()).strip("-")
    return s or "item"


def _get(map_id: str) -> dict[str, Any]:
    d = _store().get(COLL, map_id)
    if not d:
        raise not_found("가치 맵", map_id)
    return d


async def load(map_id: str) -> dict[str, Any]:
    return await asyncio.to_thread(_get, map_id)


async def update(map_id: str, fn: Callable[[dict[str, Any]], None], note: str | None = None) -> dict[str, Any]:
    def _do() -> dict[str, Any]:
        for _ in range(5):
            cur = _get(map_id)
            work = copy.deepcopy(cur)
            fn(work)
            try:
                return _store().put(COLL, map_id, work, expected_version=cur["version"], note=note)
            except VersionConflict:
                continue
        raise ApiError(409, "CONFLICT", "다른 곳에서 동시에 고쳐 저장하지 못했어요. 다시 시도해 주세요.")
    return await asyncio.to_thread(_do)


def counts(d: dict[str, Any]) -> dict[str, int]:
    vals = [v for it in d.get("items") or [] for v in it.get("values") or []]
    done = [v for v in vals if v.get("by") != "ai-pending"]
    needs = [v for v in done if v.get("need") and (v["need"].get("by") != "ai-pending")]
    pending = sum(1 for v in vals if v.get("by") == "ai-pending") + sum(1 for v in done if v.get("need") and v["need"].get("by") == "ai-pending")
    return {"items": len(d.get("items") or []), "values": len(done), "needs": len(needs), "needs_missing": len(done) - len(needs), "pending": pending}


def to_api(d: dict[str, Any]) -> dict[str, Any]:
    return {**d, "counts": counts(d)}


def _item_from(c: dict[str, Any], keep: dict[str, dict[str, Any]], from_dss: bool) -> dict[str, Any]:
    k = slug(c["name"])
    old = keep.get(k)
    return {"key": k, "name": c["name"], "kind": c["kind"], "ref": c.get("ref") or (old or {}).get("ref"),
            "spaces": list(c.get("spaces") or (old or {}).get("spaces") or []), "from_dss": from_dss,
            "values": list((old or {}).get("values") or [])}


async def _kb_candidates(text: str) -> list[dict[str, Any]]:
    """요구 문장 → KB S1(공간별 후보 제품군 · 솔루션, 공간마다 상위 2개). 실패하면 빈 목록."""
    r = await kbx.result("S1", {"text": text[:2000], "limit": 6})
    out: dict[str, dict[str, Any]] = {}
    for sp in r.get("by_space") or []:
        space = sp.get("space_name") or ""
        for f in (sp.get("families") or [])[:2]:
            name = f.get("name")
            if not name:
                continue
            c = out.setdefault(name, {"name": name, "kind": "product", "ref": f"kb:family:{f['id']}" if f.get("id") else None, "spaces": []})
            if space and space not in c["spaces"]:
                c["spaces"].append(space)
        for so in (sp.get("solutions") or [])[:2]:
            name = so.get("name")
            if not name:
                continue
            c = out.setdefault(name, {"name": name, "kind": "solution", "ref": f"kb:solution:{so['id']}" if so.get("id") else None, "spaces": []})
            if space and space not in c["spaces"]:
                c["spaces"].append(space)
    return list(out.values())[:12]


# ── 작업 ────────────────────────────────────────────────

async def create(body: VMCreate) -> dict[str, Any]:
    cands = [c.model_dump() for c in body.candidates] if body.candidates is not None else (
        await _kb_candidates(body.context_text) if body.context_text else [])
    seen: set[str] = set()
    uniq = []
    for c in cands:
        if slug(c["name"]) not in seen:
            seen.add(slug(c["name"]))
            uniq.append(c)
    n = await asyncio.to_thread(_store().count, COLL)
    doc = {"code": f"VP-{n + 1:02d}", "title": body.title or "새 VP", "sb_id": body.sb_id, "context_text": body.context_text, "candidates": uniq,
           "items": [_item_from(c, {}, True) for c in uniq] if body.select_all else [], "status": "draft"}
    map_id = new_id("vmap")
    saved = await asyncio.to_thread(_store().put, COLL, map_id, doc, note="만듦")
    await register_item(feature="VP", item_id=map_id, title=saved["title"], status="draft", route=f"/vp/values/{map_id}",
                        summary="제품 · 솔루션 가치 · 고객의 니즈")
    return to_api(saved)


async def list_maps(limit: int, cursor: str | None) -> dict[str, Any]:
    items, nxt = await asyncio.to_thread(_store().list, COLL, limit=limit, cursor=cursor)
    return {"items": [{"id": d["id"], "code": d.get("code"), "title": d.get("title") or "", "sb_id": d.get("sb_id"), "status": d.get("status", "draft"),
                       "counts": counts(d), "updated_at": d["updated_at"]} for d in items], "next_cursor": nxt}


async def set_items(map_id: str, body: VMSetItems) -> dict[str, Any]:
    if not body.items:
        raise ApiError(422, "NO_ITEMS", "제품 · 솔루션을 하나 이상 골라 주세요.")

    def fn(d: dict[str, Any]) -> None:
        keep = {it["key"]: it for it in d.get("items") or []}
        dss = {slug(c["name"]) for c in d.get("candidates") or []}
        d["items"] = [_item_from(c.model_dump(), keep, slug(c.name) in dss) for c in body.items]
    return to_api(await update(map_id, fn, "제품 · 솔루션 고르기"))


def _find_value(d: dict[str, Any], value_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    for it in d.get("items") or []:
        for v in it.get("values") or []:
            if v["id"] == value_id:
                return it, v
    raise not_found("가치", value_id)


async def add_value(map_id: str, item_key: str, body: VMAddValue) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        it = next((x for x in d.get("items") or [] if x["key"] == item_key), None)
        if it is None:
            raise not_found("제품 · 솔루션", item_key)
        if len(it.get("values") or []) >= MAX_VALUES_PER_ITEM:
            raise ApiError(422, "TOO_MANY_VALUES", f"가치는 제품 · 솔루션마다 {MAX_VALUES_PER_ITEM}개까지예요.")
        it.setdefault("values", []).append({"id": new_id("val"), "space": body.space or "전체", "message": body.message.strip(),
                                            "need": {"text": body.need.strip(), "by": "manual"} if body.need and body.need.strip() else None,
                                            "req": body.req, "by": "manual", "basis": None})
    return to_api(await update(map_id, fn, "가치 추가"))


async def patch_value(map_id: str, value_id: str, body: VMPatchValue) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        _, v = _find_value(d, value_id)
        if body.space is not None:
            v["space"] = body.space
        if body.message is not None:
            v["message"] = body.message.strip()
            if v["by"] == "ai-pending":
                v["by"] = "ai-accepted"          # 고쳐 쓰면 받아들인 것으로
        if body.req is not None:
            v["req"] = body.req or None
        if body.need is not None:
            v["need"] = {"text": body.need.strip(), "by": "manual"} if body.need.strip() else None
        if body.accept:
            v["by"] = "ai-accepted"
            if v.get("need") and v["need"].get("by") == "ai-pending":
                v["need"]["by"] = "ai-accepted"
        if body.accept_need and v.get("need") and v["need"].get("by") == "ai-pending":
            v["need"]["by"] = "ai-accepted"
    return to_api(await update(map_id, fn, "가치 고침"))


async def delete_value(map_id: str, value_id: str) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        it, v = _find_value(d, value_id)
        it["values"] = [x for x in it["values"] if x["id"] != value_id]
    return to_api(await update(map_id, fn, "가치 지움"))


async def accept_all(map_id: str) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        for it in d.get("items") or []:
            for v in it.get("values") or []:
                if v["by"] == "ai-pending":
                    v["by"] = "ai-accepted"
                if v.get("need") and v["need"].get("by") == "ai-pending":
                    v["need"]["by"] = "ai-accepted"
    return to_api(await update(map_id, fn, "AI 추천 모두 수락"))


# ── AI 추가기능 ─────────────────────────────────────────

def _kb_about(ref: str | None) -> tuple[str, str] | None:
    if not ref or not ref.startswith("kb:"):
        return None
    parts = ref.split(":", 2)
    if len(parts) != 3:
        return None
    kind, ident = parts[1], parts[2]
    if kind == "model":
        return None
    return (kind, ident)


async def _official(item: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    """KB 원문 메시지(E1). 참조가 없으면 이름으로 A1 링크를 찾아 쓴다(kb 가 카탈로그 id · 이름도 KB id 로 맞춘다)."""
    about = _kb_about(item.get("ref"))
    if about is None:
        about = ("solution", item["name"]) if item["kind"] == "solution" else None
        if about is None:
            for l in await kbx.link_entities(item["name"]):
                if l.get("type") in ("family", "solution") and l.get("id"):
                    about = (l["type"], l["id"])
                    break
    if about is None:
        return []
    r = await kbx.result("E1", {"about": [{"kind": about[0], "id": about[1]}], "locale": "ko-KR"})
    tree = r.get("tree") or {}
    out = []
    for lvl in ("taglines", "key_messages", "usps"):
        for m in tree.get(lvl) or []:
            out.append({"level": {"taglines": "tagline", "key_messages": "key_message", "usps": "usp"}[lvl], "text": m["text"],
                        "source_url": m.get("source_url"), "claim_flag": bool(m.get("claim_flag"))})
    return out[:limit]


def _short(text: str, n: int = 60) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


class _SugValue(BaseModel):
    item_key: str
    space: str = Field(description="입력 공간 중 하나 또는 '전체'")
    message: str = Field(description="고객이 얻는 가치 한 문장(40자 안팎, 근거 메시지에 있는 내용만)")
    need: str = Field(description="그 가치가 풀어 주는 고객의 니즈 — 고객이 할 말처럼 '…했으면 해요 / …이 필요해요'(30자 안팎)")
    req: str | None = Field(None, description="맞닿는 요구(입력 요구 문장 그대로의 짧은 이름), 없으면 null")
    basis_ids: list[str] = Field(default_factory=list, description="근거 메시지 id(M1 …)")


class _SugNeed(BaseModel):
    value_id: str
    need: str


class _SugOut(BaseModel):
    values: list[_SugValue] = Field(default_factory=list)
    needs: list[_SugNeed] = Field(default_factory=list)


def _mockish(s: str | None) -> bool:
    return not s or s.startswith("[mock") or "[mock]" in s


async def suggest(map_id: str, body: VMSuggestBody) -> dict[str, Any]:
    d = await load(map_id)
    keys = set(body.item_keys or [it["key"] for it in d.get("items") or []])
    items = [it for it in d.get("items") or [] if it["key"] in keys]
    msgs: dict[str, list[dict[str, Any]]] = {}
    handle: dict[str, dict[str, Any]] = {}
    n = 0
    for it in items:
        off = await _official(it, limit=6)
        msgs[it["key"]] = []
        for m in off:
            n += 1
            h = f"M{n}"
            handle[h] = {**m, "item_key": it["key"]}
            msgs[it["key"]].append({"id": h, "text": m["text"]})
    empty_needs = [{"value_id": v["id"], "item": it["name"], "space": v["space"], "message": v["message"]}
                   for it in items for v in it.get("values") or [] if v.get("by") != "ai-pending" and not v.get("need")]
    prompt = llm.dump({
        "요청": "제품 · 솔루션마다 고객 가치 후보를 최대 2개 만들고(이미 있는 가치와 겹치지 않게), 각 가치에 고객의 니즈를 붙인다. "
                "또 '니즈가 빈 가치'마다 니즈를 한 문장 추론한다. 니즈는 고객이 할 말처럼 쓴다(예: 학교 · 교실 · 에어컨 → '여름에도 쾌적한 교실 환경이 필요해요').",
        "요구 · Storyboard": (d.get("context_text") or "")[:3000],
        "제품 · 솔루션": [{"item_key": it["key"], "이름": it["name"], "공간": it.get("spaces") or ["전체"],
                       "이미 있는 가치": [v["message"] for v in it.get("values") or []], "근거 메시지": msgs.get(it["key"], [])} for it in items],
        "니즈가 빈 가치": empty_needs,
    })
    out = await llm.try_call("vp.values_suggest.v1", prompt, _SugOut, temperature=0.3)
    mode = "llm"
    sug_values: list[dict[str, Any]] = []
    sug_needs: dict[str, str] = {}
    if out:
        for sv in out.get("values") or []:
            if sv.get("item_key") in keys and not _mockish(sv.get("message")):
                basis = [handle[b] for b in sv.get("basis_ids") or [] if b in handle]
                sug_values.append({**sv, "need": None if _mockish(sv.get("need")) else sv.get("need"),
                                   "basis": ("KB 원문 · " + _short(basis[0]["text"], 40)) if basis else "요구 · Storyboard"})
        for sn in out.get("needs") or []:
            if not _mockish(sn.get("need")):
                sug_needs[sn["value_id"]] = sn["need"]
    if not sug_values and not sug_needs:
        mode = "kb_only"                               # 모델 없이 — KB 원문 메시지를 그대로 후보로, 니즈는 비움
        for it in items:
            have = {v["message"] for v in it.get("values") or []}
            for m in msgs.get(it["key"], [])[: SUGGEST_PER_ITEM]:
                if m["text"] not in have:
                    sug_values.append({"item_key": it["key"], "space": (it.get("spaces") or ["전체"])[0], "message": _short(m["text"], 80),
                                       "need": None, "req": None, "basis": "KB 원문 메시지 그대로 · " + (handle[m["id"]].get("source_url") or "출처 미상")})
    added_v = added_n = 0

    def fn(doc: dict[str, Any]) -> None:
        nonlocal added_v, added_n
        by_key = {it["key"]: it for it in doc.get("items") or []}
        per: dict[str, int] = {}
        for sv in sug_values:
            it = by_key.get(sv["item_key"])
            if not it or per.get(it["key"], 0) >= SUGGEST_PER_ITEM or len(it.get("values") or []) >= MAX_VALUES_PER_ITEM:
                continue
            if any(v["message"] == sv["message"] for v in it.get("values") or []):
                continue
            per[it["key"]] = per.get(it["key"], 0) + 1
            it.setdefault("values", []).append({"id": new_id("val"), "space": sv.get("space") or "전체", "message": sv["message"],
                                                "need": {"text": sv["need"], "by": "ai-pending"} if sv.get("need") else None,
                                                "req": sv.get("req"), "by": "ai-pending", "basis": sv.get("basis")})
            added_v += 1
        for it in doc.get("items") or []:
            for v in it.get("values") or []:
                if v["id"] in sug_needs and not v.get("need"):
                    v["need"] = {"text": sug_needs[v["id"]], "by": "ai-pending"}
                    added_n += 1
    saved = await update(map_id, fn, "AI 가치 매칭 추천")
    return {"map": to_api(saved), "added_values": added_v, "added_needs": added_n, "mode": mode}


class _NeedOut(BaseModel):
    need: str = Field(description="고객이 할 말처럼 쓴 니즈 한 문장(30자 안팎) — '…했으면 해요 / …이 필요해요'")


async def infer_need(map_id: str, value_id: str) -> dict[str, Any]:
    d = await load(map_id)
    it, v = _find_value(d, value_id)
    prompt = llm.dump({
        "요청": "이 가치가 풀어 주는 고객의 니즈를 고객이 할 말처럼 한 문장으로 쓴다. 입력에 없는 수치 · 고객명은 쓰지 않는다. "
                "예: 학교 · 교실 · 에어컨 · '냉방 성능' → '여름에도 쾌적한 교실 환경이 필요해요'",
        "제품 · 솔루션": it["name"], "공간": v.get("space"), "가치": v["message"], "연결 요구": v.get("req"),
        "요구 · Storyboard": (d.get("context_text") or "")[:1500],
    })
    out = await llm.try_call("vp.need_infer.v1", prompt, _NeedOut, temperature=0.3)
    need = (out or {}).get("need")
    if _mockish(need):
        return {"map": to_api(d), "need": None, "reason": "지금은 AI 로 니즈를 추론하지 못했어요. 직접 적어 주세요."}

    def fn(doc: dict[str, Any]) -> None:
        _, vv = _find_value(doc, value_id)
        vv["need"] = {"text": need.strip(), "by": "ai-pending"}
    saved = await update(map_id, fn, "AI 니즈 추론")
    return {"map": to_api(saved), "need": {"text": need.strip(), "by": "ai-pending"}, "reason": None}


# ── 연결된 가치 전체 ─────────────────────────────────────

def _lv(d: dict[str, Any], v: dict[str, Any]) -> dict[str, Any]:
    return {"space": v.get("space") or "전체", "message": v["message"], "need": (v.get("need") or {}).get("text") if (v.get("need") or {}).get("by") != "ai-pending" else None,
            "req": v.get("req"), "by": v.get("by"), "map_id": d["id"], "map_title": d.get("title") or "", "sb_id": d.get("sb_id"), "value_id": v["id"]}


async def linked(map_id: str, item_key: str) -> dict[str, Any]:
    d = await load(map_id)
    it = next((x for x in d.get("items") or [] if x["key"] == item_key), None)
    if it is None:
        raise not_found("제품 · 솔루션", item_key)
    here = [_lv(d, v) for v in it.get("values") or [] if v.get("by") != "ai-pending"]
    others, _ = await asyncio.to_thread(_store().list, COLL, limit=200)
    other = []
    for od in others:
        if od["id"] == map_id:
            continue
        for oit in od.get("items") or []:
            if oit["key"] == item_key or (it.get("ref") and oit.get("ref") == it.get("ref")):
                other += [_lv(od, v) for v in oit.get("values") or [] if v.get("by") != "ai-pending"]
    return {"item": it, "here": here, "other": other[:40], "official": await _official(it, limit=12)}


async def import_value(map_id: str, item_key: str, body: VMImportValue) -> dict[str, Any]:
    src = await load(body.from_map)
    _, sv = _find_value(src, body.value_id)

    def fn(d: dict[str, Any]) -> None:
        it = next((x for x in d.get("items") or [] if x["key"] == item_key), None)
        if it is None:
            raise not_found("제품 · 솔루션", item_key)
        if any(v["message"] == sv["message"] for v in it.get("values") or []):
            return
        it.setdefault("values", []).append({"id": new_id("val"), "space": sv.get("space") or "전체", "message": sv["message"],
                                            "need": {"text": sv["need"]["text"], "by": "manual"} if sv.get("need") else None,
                                            "req": None, "by": "manual", "basis": f"{src.get('title') or src['id']} 에서 가져옴"})
    return to_api(await update(map_id, fn, "다른 제안에서 가져옴"))


# ── 저장 · flow.json ────────────────────────────────────

def stage(d: dict[str, Any]) -> dict[str, Any]:
    dss = {slug(c["name"]) for c in d.get("candidates") or []}
    chosen = {it["key"] for it in d.get("items") or []}
    items = []
    for it in d.get("items") or []:
        vals = []
        for v in it.get("values") or []:
            if v.get("by") == "ai-pending":
                continue
            need = v.get("need") if (v.get("need") or {}).get("by") != "ai-pending" else None
            vals.append({"id": v["id"], "space": v.get("space"), "message": v["message"],
                         "need": {"text": need["text"], "by": need["by"]} if need else None, "req": v.get("req"), "by": v["by"]})
        items.append({"name": it["name"], "kind": it["kind"], "ref": it.get("ref"), "spaces": it.get("spaces") or [], "values": vals})
    c = counts(d)
    return {"ref": d.get("code") or d["id"], "id": d["id"], "ver": d.get("version"), "from": d.get("sb_id"),
            "selection": {"fromDss": len(chosen & dss), "excluded": [x["name"] for x in d.get("candidates") or [] if slug(x["name"]) not in chosen],
                          "addedOutsideDss": [it["name"] for it in d.get("items") or [] if it["key"] not in dss]},
            "items": items, "counts": {"items": c["items"], "values": c["values"], "needs": c["needs"], "needsMissing": c["needs_missing"]}}


def summary_md(d: dict[str, Any]) -> str:
    c = counts(d)
    st = stage(d)
    lead = [v for it in st["items"] for v in it["values"] if v.get("need")][:2]
    lines = [f"## VP · {d.get('code') or d['id']} v{d.get('version')}", f"- 제품 · 솔루션 {c['items']} · 가치 {c['values']} · 고객의 니즈 {c['needs']}/{c['values']}"]
    if lead:
        lines.append("- 대표 니즈: " + " · ".join(f"“{v['need']['text']}”" for v in lead))
    if c["needs_missing"]:
        lines.append(f"- 니즈 비어 있음 {c['needs_missing']}")
    return "\n".join(lines)


async def finish(map_id: str) -> dict[str, Any]:
    d = await load(map_id)
    c = counts(d)
    if c["values"] == 0:
        raise ApiError(422, "NO_VALUES", "가치를 하나 이상 적어 주세요.")

    def fn(doc: dict[str, Any]) -> None:
        doc["status"] = "done"
        doc["saved_at"] = now_iso()
    saved = await update(map_id, fn, "저장")
    await register_item(feature="VP", item_id=map_id, title=saved.get("title") or "VP", status="done", route=f"/vp/values/{map_id}",
                        summary=f"가치 {c['values']} · 니즈 {c['needs']}/{c['values']}")
    return {"stage": stage(saved), "summary_md": summary_md(saved)}


async def get_stage(map_id: str) -> dict[str, Any]:
    d = await load(map_id)
    return {"stage": stage(d), "summary_md": summary_md(d)}
