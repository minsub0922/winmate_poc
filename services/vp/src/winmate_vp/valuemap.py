"""가치 맵(새 VP 흐름, 2026-10-08 — 보드 webapp1 VP2 · VP2_AI · VP2_Pick · VP2_Detail · VpDetail · VP_DoneJson).

제품 · 솔루션마다 가치를 여러 개 두고, 가치마다 '고객의 니즈'(고객이 할 말처럼 쓴 한 문장)를 붙인다.
- 사용자가 VP 에 넣을 제품 · 솔루션을 고른다(DSS 후보 + 카탈로그). 고른 것만 저장된다.
- 가치: 공간 · 가치 메시지 · 고객의 니즈 · 연결 요구 · 출처(manual · ai-pending · ai-accepted).
- 니즈: 직접 쓰거나 AI 로 추론(`ai-pending` → 수락하면 `ai-accepted`). AI 가 먼저 묻지 않는다 — 버튼으로만.
- 'AI 가치 매칭 추천' = KB 원문 메시지(E1, 제품군 · 솔루션) + 요구 문장 → 가치 후보(니즈 포함) · 빈 니즈 추론. 점선(ai-pending)으로 넣고 수락해야 들어간다.
  LLM 이 없거나(mock · 장애) 답이 비면 KB 원문 메시지를 그대로 가치 후보로 쓰고(출처 표시), 니즈는 비워 둔다(지어내지 않는다).
- 연결된 가치 전체 = 이 맵 + 같은 제품 · 솔루션을 쓴 다른 맵의 가치 + KB 공식 메시지. 다른 맵 가치는 가져오기(복사)할 수 있다.
- 저장하면 Storyboard flow.json 의 `stages.vp` 모양(`stage()`)을 만든다.
- DSS 다시 가져오기(2026-10-10 · 보드에 없음): Storyboard(Gate)로 만든 맵은 가져온 DSS ref · ver(`dss_ref` · `dss_ver`)와 DSS 후보(`candidates`)를 남기고,
  GET 때 허브의 지금 stages.dss 와 견줘 `dss_changed` 를 알려 준다. `:resync-dss` — 새 DSS 제품 · 솔루션은 고를 수 있는 후보로만 더하고(자동으로 고르지 않음),
  골라 둔 것이 DSS 에서 빠지면 가치와 함께 남기고 「DSS에서 빠짐」 표시. 고르지 않은 빠진 후보는 후보에서 뺀다.
- 초안 지우기 · 같은 Storyboard 초안 이어 쓰기: 한 번도 저장하지 않은 맵만 지운다(저장한 것은 409 `SAVED_CONTENT`).
  Gate 에서 같은 Storyboard 로 다시 만들면 저장 전 초안을 돌려준다(복제본은 새 Storyboard 라 새 맵).

저장소: DocStore("vp") 컬렉션 `value_maps`(vmap_ …). 쓰기는 낙관적 잠금 + 재시도.
"""
from __future__ import annotations

import asyncio
import copy
import logging
import re
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from winmate_common.flow import get_flow, push_stage
from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso
from winmate_common.platform import register_item, unregister_item
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
    dss_status: Literal["removed"] | None = Field(None, description="removed = 골라 둔 것이 Storyboard 의 DSS 에서 빠짐(가치와 함께 남겨 둠)")
    values: list[VMValue] = Field(default_factory=list)


class VMCandidate(BaseModel):
    name: str
    kind: Literal["product", "solution"]
    ref: str | None = None
    spaces: list[str] = Field(default_factory=list)
    dss_status: Literal["added"] | None = Field(None, description="added = DSS 다시 가져오기로 새로 들어온 후보(고르지 않은 채로)")


class VMCounts(BaseModel):
    items: int
    values: int
    needs: int
    needs_missing: int
    pending: int


class VMDssChange(BaseModel):
    """Storyboard 의 DSS 가 맵을 만든(다시 가져온) 뒤 바뀌었다 — 편집 화면 위 안내 줄."""
    model_config = ConfigDict(populate_by_name=True)
    from_: str = Field(alias="from", description="맵이 가져온 DSS(DSS-01 v1)")
    to: str = Field(description="허브의 지금 DSS(DSS-01 v2 · 분기로 바뀌면 DSS-02 v1)")
    ref_changed: bool = Field(False, description="DSS 자체가 바뀜(분기 등으로 다른 DSS)")
    added: int = Field(description="새로 들어온 DSS 제품 · 솔루션")
    removed: int = Field(description="DSS 에서 빠진 제품 · 솔루션")
    changed: int = Field(0, description="놓인 공간이 바뀐 제품")
    added_names: list[str] = Field(default_factory=list)
    removed_names: list[str] = Field(default_factory=list)


class VMResync(BaseModel):
    """마지막 DSS 다시 가져오기 결과(토스트 · 표시)."""
    model_config = ConfigDict(populate_by_name=True)
    at: str
    from_: str = Field(alias="from")
    to: str
    added: list[str] = Field(default_factory=list, description="새 후보(고르기 대화상자에 「새로」) — 자동으로 고르지 않음")
    removed: list[str] = Field(default_factory=list, description="고르지 않은 채 DSS 에서 빠져 후보에서 뺀 것")
    kept: list[str] = Field(default_factory=list, description="골라 둔 것이 DSS 에서 빠져 남기고 「DSS에서 빠짐」 표시한 것")
    updated: list[str] = Field(default_factory=list, description="DSS 공간이 바뀐 고른 것")


class VMDoc(BaseModel):
    id: str
    code: str | None = Field(None, description="화면 · flow.json 에 쓰는 짧은 번호(VP-01 …)")
    title: str
    sb_id: str | None = None
    dss_ref: str | None = Field(None, description="Storyboard(Gate)로 만들 때 가져온 DSS 코드(DSS-01 …) — 없으면 DSS 다시 가져오기 대상이 아님")
    dss_ver: int | None = Field(None, description="가져온 DSS 판(허브 stages.dss.ver)")
    dss_changed: VMDssChange | None = Field(
        None, description="허브의 DSS 가 바뀌었으면 그 차이(GET · :resync-dss 응답에서만 계산 — 다른 고침 응답은 null)")
    last_resync: VMResync | None = None
    context_text: str | None = Field(None, description="요구 · Storyboard 요약(AI 추천 문맥)")
    candidates: list[VMCandidate] = Field(default_factory=list, description="DSS 에서 온 고를 수 있는 제품 · 솔루션")
    items: list[VMItem] = Field(default_factory=list, description="고른 제품 · 솔루션(이 순서로 보인다)")
    status: Literal["draft", "done"] = "draft"
    ver: int | None = Field(None, description="저장(완료) 판 — flow.json stages.vp.ver")
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


class VMFlowSync(BaseModel):
    md_added: str = Field(description="Storyboard 요약본에 더해진 부분")
    synced: list[str] = Field(default_factory=list, description="같은 VP 가 연결돼 함께 바뀐 다른 Storyboard")


class VMStageOut(BaseModel):
    stage: dict[str, Any] = Field(description="Storyboard flow.json 의 stages.vp")
    summary_md: str
    flow_sync: VMFlowSync | None = Field(None, description="Storyboard 허브에 반영된 결과(sb_id 가 없거나 허브가 안 되면 null)")


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


def to_api(d: dict[str, Any], dss_changed: dict[str, Any] | None = None) -> dict[str, Any]:
    return {**d, "counts": counts(d), "dss_changed": dss_changed}


def _item_from(c: dict[str, Any], keep: dict[str, dict[str, Any]], from_dss: bool) -> dict[str, Any]:
    k = slug(c["name"])
    old = keep.get(k)
    # DSS 에서 빠져 남겨 둔 것은 다시 골라도 표시를 잇는다(후보에 없으니 DSS 밖으로 잘못 세지 않게)
    gone = None if from_dss else ("removed" if (old or {}).get("dss_status") == "removed" else None)
    return {"key": k, "name": c["name"], "kind": c["kind"], "ref": c.get("ref") or (old or {}).get("ref"),
            "spaces": list(c.get("spaces") or (old or {}).get("spaces") or []), "from_dss": from_dss, "dss_status": gone,
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

def dss_candidates(flow: dict[str, Any]) -> list[dict[str, Any]]:
    """Storyboard flow.json stages.dss → 고를 수 있는 제품 · 솔루션(공간 붙여서)."""
    dss = (flow.get("stages") or {}).get("dss") or {}
    out: dict[str, dict[str, Any]] = {}
    for sp in dss.get("spaces") or []:
        for p in sp.get("products") or []:
            name = p.get("name") if isinstance(p, dict) else p
            if not name:
                continue
            c = out.setdefault(name, {"name": name, "kind": "product", "ref": (p.get("ref") if isinstance(p, dict) else None), "spaces": []})
            if sp.get("name") and sp["name"] not in c["spaces"]:
                c["spaces"].append(sp["name"])
    for so in dss.get("solutions") or []:
        name = so.get("name") if isinstance(so, dict) else so
        if name:
            out.setdefault(name, {"name": name, "kind": "solution", "ref": so.get("ref") if isinstance(so, dict) else None, "spaces": []})
    return list(out.values())


def flow_context(flow: dict[str, Any]) -> str:
    """AI 추천 문맥 — 요약본(md) 앞부분."""
    return (flow.get("summary_md") or "")[:4000]


def ever_saved(d: dict[str, Any]) -> bool:
    """한 번이라도 저장(허브 stages.vp 반영)했는가 — 했으면 Storyboard 에 연결돼 지울 수 없다."""
    return bool(d.get("ver")) or bool(d.get("saved_at")) or d.get("status") == "done"


def _open_draft(sb_id: str) -> dict[str, Any] | None:
    """같은 Storyboard(Gate)로 만든 저장 전 초안(가장 최근 것) — Gate 에서 다시 시작해도 초안이 둘이 되지 않게."""
    items, _ = _store().list(COLL, where={"sb_id": sb_id}, limit=50)
    return next((d for d in items if d.get("dss_ref") and not ever_saved(d)), None)


def _next_code() -> str:
    """VP-NN — 지운 초안이 있어도 겹치지 않게 남은 코드 중 가장 큰 번호 + 1(지운 초안은 허브에 간 적 없어 번호를 다시 써도 된다)."""
    items, _ = _store().list(COLL, limit=10000, order_by="-created_at")
    nums = [int(m.group(1)) for d in items if (m := re.fullmatch(r"VP-(\d+)", d.get("code") or ""))]
    return f"VP-{max(nums, default=0) + 1:02d}"


def _uniq(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out = []
    for c in cands:
        if slug(c["name"]) not in seen:
            seen.add(slug(c["name"]))
            out.append(c)
    return out


async def create(body: VMCreate) -> tuple[dict[str, Any], bool]:
    """(맵, 새로 만들었나). Storyboard(Gate · candidates 없이)로 시작할 때 같은 Storyboard 의 저장 전 초안이 있으면 그것을 돌려준다."""
    flow = await get_flow(body.sb_id) if body.sb_id else None
    if body.sb_id and flow is None and body.candidates is None:
        raise ApiError(404, "STORYBOARD_NOT_FOUND", f"Storyboard를 찾을 수 없어요: {body.sb_id}")
    dss = ((flow or {}).get("stages") or {}).get("dss")
    if flow is not None and body.candidates is None and not dss:
        raise ApiError(422, "PREREQUISITE_MISSING", "DSS까지 된 Storyboard에서 시작할 수 있어요.", {"need": "dss"})
    from_hub = flow is not None and body.candidates is None
    if from_hub and body.sb_id:
        existing = await asyncio.to_thread(_open_draft, body.sb_id)
        if existing:
            return to_api(existing, dss_diff(existing, flow)), False
    if body.candidates is not None:
        cands = [c.model_dump() for c in body.candidates]
    elif flow is not None:
        cands = dss_candidates(flow)
    else:
        cands = await _kb_candidates(body.context_text) if body.context_text else []
    if flow is not None and not body.context_text:
        body.context_text = flow_context(flow)
    if flow is not None and not body.title:
        body.title = flow.get("name")
    uniq = _uniq(cands)
    doc = {"code": await asyncio.to_thread(_next_code), "title": body.title or "새 VP", "sb_id": body.sb_id, "context_text": body.context_text, "candidates": uniq,
           "items": [_item_from(c, {}, True) for c in uniq] if body.select_all else [], "status": "draft",
           "dss_ref": (dss or {}).get("ref") if from_hub else None, "dss_ver": (dss or {}).get("ver") if from_hub else None}
    map_id = new_id("vmap")
    saved = await asyncio.to_thread(_store().put, COLL, map_id, doc, note="만듦")
    await register_item(feature="VP", item_id=map_id, title=saved["title"], status="draft", route=f"/vp/values/{map_id}",
                        summary="제품 · 솔루션 가치 · 고객의 니즈")
    return to_api(saved), True


async def get_with_status(map_id: str) -> dict[str, Any]:
    """GET — Storyboard(Gate)로 만든 맵이면 허브의 지금 DSS 와 견준 차이(dss_changed)를 함께. 허브가 안 되면 null."""
    d = await load(map_id)
    flow = await get_flow(d["sb_id"]) if d.get("sb_id") and d.get("dss_ref") else None
    return to_api(d, dss_diff(d, flow) if flow else None)


async def delete(map_id: str) -> None:
    def _do() -> None:   # 확인과 지우기를 한 번에 — DocStore.delete(expected_version) 가 같은 트랜잭션에서 판을 본다
        d = _get(map_id)
        if ever_saved(d):
            raise ApiError(409, "SAVED_CONTENT", "저장한 콘텐츠는 Storyboard에 연결돼 있어 지울 수 없어요",
                           {"ref": d.get("code"), "sb_id": d.get("sb_id")})
        try:   # 확인 → 지우기 사이에 저장이 끼면 지우지 않는다(DocStore 판 확인, 같은 트랜잭션)
            _store().delete(COLL, map_id, expected_version=d["version"])
        except VersionConflict as exc:
            raise ApiError(409, "VERSION_CONFLICT", "방금 다른 곳에서 저장했어요. 새로 불러와 주세요.", {}) from exc
    await asyncio.to_thread(_do)
    await unregister_item(map_id)


# ── DSS 다시 가져오기 ────────────────────────────────────

def dss_label(ref: str | None, ver: Any) -> str:
    if not ref:
        return "DSS"
    return f"{ref} v{ver}" if ver else ref


def dss_diff(d: dict[str, Any], flow: dict[str, Any] | None) -> dict[str, Any] | None:
    """맵이 가져온 DSS 후보(candidates) ↔ 허브의 지금 stages.dss. 바뀐 것이 없으면 None(고르기 · 가치는 사람 몫이라 차이가 아니다).
    DSS 자체가 바뀌면(분기 등 ref 다름) 내용이 같아도 알린다."""
    dss = ((flow or {}).get("stages") or {}).get("dss")
    if not dss or not d.get("dss_ref"):
        return None
    new = {slug(c["name"]): c for c in dss_candidates(flow or {})}
    old = {slug(c["name"]): c for c in d.get("candidates") or []}
    added = [c["name"] for k, c in new.items() if k not in old]
    removed = [c["name"] for k, c in old.items() if k not in new]
    changed = [c["name"] for k, c in new.items() if k in old and set(c.get("spaces") or []) != set(old[k].get("spaces") or [])]
    ref_changed = dss.get("ref") != d.get("dss_ref")
    if not (added or removed or changed or ref_changed):
        return None
    return {"from": dss_label(d.get("dss_ref"), d.get("dss_ver")), "to": dss_label(dss.get("ref"), dss.get("ver")), "ref_changed": ref_changed,
            "added": len(added), "removed": len(removed), "changed": len(changed), "added_names": added[:20], "removed_names": removed[:20]}


async def resync(map_id: str) -> dict[str, Any]:
    """허브의 지금 DSS 로 후보를 맞춘다(사람이 고른 것 · 가치는 남긴다).
    - 새 DSS 제품 · 솔루션 → 후보에만 더한다(표시 added · 자동으로 고르지 않음).
    - 골라 둔 것이 DSS 에서 빠짐 → 가치와 함께 남기고 「DSS에서 빠짐」(dss_status removed). 고르지 않은 빠진 후보는 후보에서 뺀다.
    - 골라 둔 것의 DSS 공간이 바뀌면 공간만 DSS 값으로.
    """
    d = await load(map_id)
    if not d.get("sb_id") or not d.get("dss_ref"):
        raise ApiError(422, "NO_STORYBOARD", "Storyboard(DSS)로 만든 맵이 아니에요.")
    flow = await get_flow(d["sb_id"])
    if flow is None:
        raise ApiError(404, "STORYBOARD_NOT_FOUND", f"Storyboard를 찾을 수 없어요: {d['sb_id']}")
    dss = (flow.get("stages") or {}).get("dss")
    if not dss:
        raise ApiError(422, "PREREQUISITE_MISSING", "Storyboard에 DSS가 없어요.", {"need": "dss"})
    new_c = _uniq(dss_candidates(flow))
    frm = dss_label(d.get("dss_ref"), d.get("dss_ver"))
    log_: dict[str, list[str]] = {k: [] for k in ("added", "removed", "kept", "updated")}

    def fn(doc: dict[str, Any]) -> None:
        for v in log_.values():
            v.clear()
        old = {slug(c["name"]): c for c in doc.get("candidates") or []}
        new = {slug(c["name"]): c for c in new_c}
        chosen = {it["key"] for it in doc.get("items") or []}
        cands = []
        for c in new_c:
            k = slug(c["name"])
            cands.append({**c, "dss_status": "added" if k not in old else None})
            if k not in old:
                log_["added"].append(c["name"])
        log_["removed"] += [c["name"] for k, c in old.items() if k not in new and k not in chosen]
        for it in doc.get("items") or []:
            nc = new.get(it["key"])
            if nc is not None:
                if set(it.get("spaces") or []) != set(nc.get("spaces") or []):
                    log_["updated"].append(it["name"])
                it["spaces"] = list(nc.get("spaces") or [])
                it["ref"] = it.get("ref") or nc.get("ref")
                it["from_dss"], it["dss_status"] = True, None
            elif it["key"] in old or it.get("dss_status") == "removed":
                if it.get("dss_status") != "removed":
                    log_["kept"].append(it["name"])
                it["from_dss"], it["dss_status"] = False, "removed"
        doc["candidates"] = cands
        doc["dss_ref"], doc["dss_ver"] = dss.get("ref"), dss.get("ver")
        doc["last_resync"] = {"at": now_iso(), "from": frm, "to": dss_label(dss.get("ref"), dss.get("ver")), **{k: list(v) for k, v in log_.items()}}
    saved = await update(map_id, fn, "DSS 다시 가져오기")
    return to_api(saved, dss_diff(saved, flow))


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
                          "addedOutsideDss": [it["name"] for it in d.get("items") or [] if it["key"] not in dss and it.get("dss_status") != "removed"],
                          "droppedFromDss": [it["name"] for it in d.get("items") or [] if it.get("dss_status") == "removed"]},
            "items": items, "counts": {"items": c["items"], "values": c["values"], "needs": c["needs"], "needsMissing": c["needs_missing"]}}


def card(d: dict[str, Any], st: dict[str, Any]) -> dict[str, Any]:
    """연결된 콘텐츠 보기 팝업(ContentPopup) 값."""
    c = counts(d)
    groups = []
    for it in st["items"][:3]:
        groups.append({"h": it["name"], "sub": f"가치 {len(it['values'])}",
                       "lines": [{"t": v["message"], "note": None if v.get("need") else "확인 필요"} for v in it["values"][:3]]})
    return {"title": d.get("title") or "VP", "facts": [["제품 · 솔루션", str(c["items"])], ["가치", str(c["values"])], ["고객의 니즈", f"{c['needs']}/{c['values']}"]],
            "groups": groups, "foot": "니즈가 빈 가치는 확인 필요로 표시돼요",
            "line": f"{d.get('code')} v{d.get('ver') or 1} · 제품 · 솔루션 {c['items']} · 가치 {c['values']} · 니즈 {c['needs']}/{c['values']}"}


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
        doc["ver"] = int(doc.get("ver") or 0) + 1 if doc.get("status") == "done" or doc.get("saved_at") else 1
        doc["status"] = "done"
        doc["saved_at"] = now_iso()
    saved = await update(map_id, fn, "저장")
    await register_item(feature="VP", item_id=map_id, title=saved.get("title") or "VP", status="done", route=f"/vp/values/{map_id}",
                        summary=f"가치 {c['values']} · 니즈 {c['needs']}/{c['values']}")
    st, md = stage(saved), summary_md(saved)
    sync = None
    if saved.get("sb_id"):
        sync = await push_stage(saved["sb_id"], "vp", ref=saved.get("code") or map_id, ver=int(saved.get("ver") or 1), res_id=map_id,
                                title=saved.get("title"), value=st, md=md, card=card(saved, st))
    return {"stage": st, "summary_md": md, "flow_sync": {"md_added": sync["md_added"], "synced": sync["synced"]} if sync else None}


async def get_stage(map_id: str) -> dict[str, Any]:
    d = await load(map_id)
    return {"stage": stage(d), "summary_md": summary_md(d)}
