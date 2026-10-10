"""공간 시나리오 묶음(새 흐름, 2026-10-08 — 보드 webapp1 SC1(Gate) · SC2 · SC2_AI · SC2_Pick · SC2_Empty · SC_Done · SC_DoneJson).

깊이: 공간 → 시나리오(여러 개) → 장면(단계 수 자유) · 항목(자유).
- 공간마다 제품 · 솔루션이 하나 이상 있어야 한다(고르기 · 바꾸기). 없으면 저장할 수 없다(422 SPACE_WITHOUT_PRODUCT).
- 시나리오마다 공간 제품 · 솔루션 중에서 하나 이상을 고른다(없으면 저장 불가 422 SCENARIO_WITHOUT_PRODUCT).
- 장면 단계마다 '쓰인 제품'을 하나 고를 수 있다(시나리오 제품 중에서, 없어도 됨).
- 입력 폼은 고정하지 않는다: 시간대 · 기대 효과 · 연결 요구 · 페인 포인트 · 직접 이름 지은 항목을 필요할 때만 더한다.
- 'AI 시나리오 3안'(공간마다): KB 비슷한 사례(D1) + 공간 제품 → 후보 3개(ai-pending). 수락해야 시나리오가 된다.
  LLM 이 없거나 답이 비면 KB 사례를 참고로 단계를 [확인 필요] 로 둔 후보를 준다(지어내지 않는다).
- 시작은 Storyboard 허브에서(보드 Gate): `sb_id` 를 주면 `get_flow` 로 flow.json 을 읽어 `stages.dss` 의 공간 · 공간별 제품을 미리 채운다
  (DSS 솔루션은 links 가 가리키는 공간에 붙인다). Storyboard 가 없으면 404, DSS 전이면 422 PREREQUISITE_MISSING.
- 저장(`:finish`)하면 Storyboard flow.json 의 `stages.sc` 모양(`stage()`)을 만들어 허브에 `push_stage` 하고(요약 줄 · ContentPopup 카드 포함),
  `ver` 는 저장한 횟수다(docs/scenarios/11-content-flow.md §6).

저장소: DocStore("scenario") 컬렉션 `space_sets`(scs_ …).
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, Field
from winmate_common.errors import ApiError
from winmate_common.flow import get_flow, push_stage
from winmate_common.ids import new_id, now_iso
from winmate_common.platform import register_item
from winmate_common.store import VersionConflict

from . import kbq, llm, repo

log = logging.getLogger("winmate.scenario.spaceset")

COLL = "space_sets"
FIELD_PRESETS = ["시간대", "기대 효과", "연결 요구", "페인 포인트"]


# ── 모델(API) ───────────────────────────────────────────

class SSProduct(BaseModel):
    name: str
    kind: Literal["product", "solution"] = "product"
    ref: str | None = Field(None, description="KB 참조 kb:family:… · kb:solution:…")


class SSStep(BaseModel):
    text: str = ""
    product: str | None = Field(None, description="이 장면에 쓰인 제품 · 솔루션 이름(시나리오 제품 중 하나)")


class SSFieldKV(BaseModel):
    k: str = Field(min_length=1, max_length=30)
    v: str = ""


class SSScenario(BaseModel):
    id: str
    title: str = ""
    user: str = ""
    products: list[str] = Field(default_factory=list, description="이 시나리오에 쓰는 제품 · 솔루션 이름(공간 제품 중에서, 하나 이상)")
    steps: list[SSStep] = Field(default_factory=list)
    fields: list[SSFieldKV] = Field(default_factory=list, description="자유 항목(시간대 · 기대 효과 · …)")
    by: str = Field("manual", description="manual · ai-candidate-A … (수락한 AI 후보)")
    basis: str | None = None


class SSCandidate(SSScenario):
    cid: Literal["A", "B", "C"]
    mode: Literal["llm", "kb_only"] = "llm"


class SSSpace(BaseModel):
    id: str
    name: str
    products: list[SSProduct] = Field(default_factory=list)
    scenarios: list[SSScenario] = Field(default_factory=list)
    candidates: list[SSCandidate] = Field(default_factory=list, description="AI 3안(수락 전, 점선)")


class SSDssItem(BaseModel):
    """DSS 에서 고른 제품 · 솔루션(SC2_Pick 첫 묶음 `DSS-01 · 제품` · `DSS-01 · 솔루션`)."""
    name: str
    kind: Literal["product", "solution"] = "product"
    ref: str | None = None
    spaces: list[str] = Field(default_factory=list, description="DSS 에서 이 제품이 있던 공간(솔루션은 links 가 가리킨 공간)")
    links: list[str] = Field(default_factory=list, description="DSS 솔루션의 함께 쓰는 제품(공간 · 제품)")


class SSIssue(BaseModel):
    code: Literal["SPACE_WITHOUT_PRODUCT", "SCENARIO_WITHOUT_PRODUCT"]
    space_id: str
    scenario_id: str | None = None
    message: str


class SSCounts(BaseModel):
    spaces: int
    scenarios: int
    spaces_without_scenario: int
    spaces_without_product: int


class SSDoc(BaseModel):
    id: str
    code: str | None = Field(None, description="화면 · flow.json 에 쓰는 짧은 번호(SC-01 …)")
    title: str
    sb_id: str | None = None
    dss_ref: str | None = Field(None, description="시작할 때 읽은 Storyboard 의 DSS 코드(공간 목록 머리 「공간 · DSS-01」 · stages.sc.from)")
    dss_items: list[SSDssItem] = Field(default_factory=list, description="DSS 제품 · 솔루션(고르기 대화상자 묶음)")
    customer: str | None = None
    context_text: str | None = None
    spaces: list[SSSpace]
    status: Literal["draft", "done"] = "draft"
    ver: int = Field(0, description="저장(완료)한 횟수 = flow.json stages.sc.ver")
    issues: list[SSIssue] = Field(default_factory=list, description="저장을 막는 것(공간 · 시나리오에 제품 · 솔루션 없음)")
    counts: SSCounts
    version: int
    created_at: str
    updated_at: str


class SSListItem(BaseModel):
    id: str
    code: str | None = None
    title: str
    sb_id: str | None = None
    status: str
    ver: int = 0
    counts: SSCounts
    updated_at: str


class SSList(BaseModel):
    items: list[SSListItem]
    next_cursor: str | None = None


class SSSpaceIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    products: list[SSProduct] = Field(default_factory=list)


class SSCreate(BaseModel):
    title: str | None = Field(None, description="없으면 Storyboard 이름")
    sb_id: str | None = Field(None, description="Gate 에서 고른 Storyboard(SB-01 …). spaces 가 없으면 flow.json stages.dss 의 공간 · 제품으로 시작")
    context_text: str | None = Field(None, max_length=8000)
    spaces: list[SSSpaceIn] | None = Field(None, description="공간 · 제품을 직접 줄 때. 없으면 Storyboard DSS(sb_id) → context_text 로 KB S1 순으로 찾는다")


class SSPut(BaseModel):
    expected_version: int | None = Field(None, description="낙관적 잠금(지금 판). 다르면 409")
    spaces: list[SSSpace] = Field(description="공간 · 시나리오 · 장면 전체(화면이 고친 그대로). candidates 는 서버 목록을 유지하고 같은 id·cid 의 고친 내용만 반영")


class SSFlowSync(BaseModel):
    md_added: str = Field(description="Storyboard 요약본에 더해진 부분")
    synced: list[str] = Field(default_factory=list, description="같은 공간 시나리오가 연결돼 함께 바뀐 다른 Storyboard")


class SSStageOut(BaseModel):
    stage: dict[str, Any] = Field(description="Storyboard flow.json 의 stages.sc")
    summary_md: str
    flow_sync: SSFlowSync | None = Field(None, description="Storyboard 허브에 반영된 결과(sb_id 가 없거나 허브가 안 되면 null)")


class SSSuggestOut(BaseModel):
    set: SSDoc
    mode: Literal["llm", "kb_only"]


# ── 저장소 ──────────────────────────────────────────────

def _get(set_id: str) -> dict[str, Any]:
    d = repo.store().get(COLL, set_id)
    if not d:
        raise repo.not_found("공간 시나리오", set_id)
    return d


async def load(set_id: str) -> dict[str, Any]:
    return await asyncio.to_thread(_get, set_id)


async def update(set_id: str, fn: Callable[[dict[str, Any]], None], note: str | None = None, expected: int | None = None) -> dict[str, Any]:
    def _do() -> dict[str, Any]:
        for _ in range(5):
            cur = _get(set_id)
            if expected is not None and cur["version"] != expected:
                raise ApiError(409, "VERSION_CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러온 뒤 다시 저장해 주세요.",
                               {"current_version": cur["version"]})
            work = copy.deepcopy(cur)
            fn(work)
            try:
                return repo.store().put(COLL, set_id, work, expected_version=cur["version"], note=note)
            except VersionConflict:
                if expected is not None:
                    raise ApiError(409, "VERSION_CONFLICT", "다른 곳에서 먼저 고쳤어요.", {}) from None
                continue
        raise ApiError(409, "CONFLICT", "동시에 고쳐 저장하지 못했어요. 다시 시도해 주세요.")
    return await asyncio.to_thread(_do)


def issues(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for sp in d.get("spaces") or []:
        names = {p["name"] for p in sp.get("products") or []}
        if not names:
            out.append({"code": "SPACE_WITHOUT_PRODUCT", "space_id": sp["id"], "scenario_id": None,
                        "message": f"{sp['name']}에 제품 · 솔루션이 없어요. 공간마다 하나 이상 있어야 해요."})
        for sc in sp.get("scenarios") or []:
            if not [p for p in sc.get("products") or [] if p in names]:
                out.append({"code": "SCENARIO_WITHOUT_PRODUCT", "space_id": sp["id"], "scenario_id": sc["id"],
                            "message": f"{sp['name']} · {sc.get('title') or '새 시나리오'}에 쓰는 제품 · 솔루션을 하나 이상 골라 주세요."})
    return out


def counts(d: dict[str, Any]) -> dict[str, int]:
    sps = d.get("spaces") or []
    return {"spaces": len(sps), "scenarios": sum(len(s.get("scenarios") or []) for s in sps),
            "spaces_without_scenario": sum(1 for s in sps if not s.get("scenarios")),
            "spaces_without_product": sum(1 for s in sps if not s.get("products"))}


def to_api(d: dict[str, Any]) -> dict[str, Any]:
    return {**d, "issues": issues(d), "counts": counts(d)}


def _clean(d: dict[str, Any]) -> None:
    """시나리오 제품은 공간 제품 안에서만, 장면 제품은 시나리오 제품 안에서만."""
    for sp in d.get("spaces") or []:
        names = [p["name"] for p in sp.get("products") or []]
        for sc in sp.get("scenarios") or []:
            sc["products"] = [p for p in dict.fromkeys(sc.get("products") or []) if p in names]
            for st in sc.get("steps") or []:
                if st.get("product") and st["product"] not in sc["products"]:
                    st["product"] = None


async def _kb_spaces(text: str) -> list[dict[str, Any]]:
    r = await kbq.query("S1", {"text": text[:2000], "limit": 6})
    out: list[dict[str, Any]] = []
    for sp in r.get("by_space") or []:
        name = sp.get("space_name") or "공간"
        prods = [{"name": f["name"], "kind": "product", "ref": f"kb:family:{f['id']}"} for f in (sp.get("families") or [])[:2] if f.get("name")]
        prods += [{"name": s["name"], "kind": "solution", "ref": f"kb:solution:{s['id']}"} for s in (sp.get("solutions") or [])[:1] if s.get("name")]
        if not any(o["name"] == name for o in out):
            out.append({"name": name, "products": prods})
    return out


# ── 작업 ────────────────────────────────────────────────

def _pname(p: Any) -> str:
    return str((p.get("name") if isinstance(p, dict) else p) or "").strip()


def dss_spaces(dss: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """flow.json stages.dss → (공간 · 공간별 제품 · 솔루션, 고르기 대화상자용 DSS 제품 · 솔루션 목록).

    DSS 공간의 제품은 그대로, DSS 솔루션은 links(함께 쓰는 제품 「공간 · 제품」)가 가리키는 공간에 붙인다 —
    공간 이름이 들어 있으면 그 공간, 없으면 그 제품이 있는 공간. 어디도 가리키지 않으면 공간에 넣지 않고 고르기 목록에만 둔다.
    """
    spaces: list[dict[str, Any]] = []
    items: dict[str, dict[str, Any]] = {}
    for sp in dss.get("spaces") or []:
        name = _pname(sp)[:40]
        if not name or any(s["name"] == name for s in spaces):
            continue
        prods: list[dict[str, Any]] = []
        for p in (sp.get("products") or []) if isinstance(sp, dict) else []:
            pn = _pname(p)
            if not pn or any(x["name"] == pn for x in prods):
                continue
            kind = p.get("kind") if isinstance(p, dict) and p.get("kind") in ("product", "solution") else "product"
            ref = p.get("ref") if isinstance(p, dict) else None
            prods.append({"name": pn, "kind": kind, "ref": ref})
            it = items.setdefault(pn, {"name": pn, "kind": kind, "ref": ref, "spaces": [], "links": []})
            if name not in it["spaces"]:
                it["spaces"].append(name)
        spaces.append({"name": name, "products": prods})
    for so in dss.get("solutions") or []:
        sn = _pname(so)
        if not sn:
            continue
        links = [str(x) for x in ((so.get("links") or []) if isinstance(so, dict) else []) if x]
        ref = so.get("ref") if isinstance(so, dict) else None
        targets = [s for s in spaces if any(s["name"] in ln for ln in links)]
        if not targets:
            targets = [s for s in spaces if any(p["name"] in ln for p in s["products"] if p["kind"] == "product" for ln in links)]
        for s in targets:
            if not any(p["name"] == sn for p in s["products"]):
                s["products"].append({"name": sn, "kind": "solution", "ref": ref})
        it = items.setdefault(sn, {"name": sn, "kind": "solution", "ref": ref, "spaces": [], "links": links})
        it["spaces"] = list(dict.fromkeys(it["spaces"] + [s["name"] for s in targets]))
    return spaces, list(items.values())


async def create(body: SSCreate) -> dict[str, Any]:
    flow = await get_flow(body.sb_id) if body.sb_id else None
    dss = ((flow or {}).get("stages") or {}).get("dss") or None
    if body.sb_id and body.spaces is None:
        if flow is None:
            raise ApiError(404, "STORYBOARD_NOT_FOUND", f"Storyboard를 찾을 수 없어요: {body.sb_id}", {"sb_id": body.sb_id})
        if not dss:
            raise ApiError(422, "PREREQUISITE_MISSING", "DSS까지 된 Storyboard에서 시작할 수 있어요.", {"need": "dss"})
    dss_items: list[dict[str, Any]] = []
    if dss:
        from_dss, dss_items = dss_spaces(dss)
    if body.spaces is not None:
        spaces = [s.model_dump() for s in body.spaces]
    elif dss:
        spaces = from_dss
    else:
        spaces = await _kb_spaces(body.context_text) if body.context_text else []
    if not spaces:
        spaces = [{"name": "공간 1", "products": []}]
    context = body.context_text or ((flow or {}).get("summary_md") or "")[:4000] or None
    n = await asyncio.to_thread(repo.store().count, COLL)
    doc = {"code": f"SC-{n + 1:02d}", "title": body.title or (flow or {}).get("name") or "새 공간 시나리오", "sb_id": body.sb_id,
           "dss_ref": (dss or {}).get("ref"), "dss_items": dss_items, "customer": (flow or {}).get("customer"),
           "context_text": context, "status": "draft", "ver": 0,
           "spaces": [{"id": new_id("sp"), "name": s["name"], "products": s.get("products") or [], "scenarios": [], "candidates": []} for s in spaces]}
    set_id = new_id("scs")
    saved = await asyncio.to_thread(repo.store().put, COLL, set_id, doc, note="만듦")
    await register_item(feature="SC", item_id=set_id, title=saved["title"], status="draft", route=f"/scenario/spaces/{set_id}",
                        summary=f"공간 {len(spaces)}")
    return to_api(saved)


async def list_sets(limit: int, cursor: str | None) -> dict[str, Any]:
    items, nxt = await asyncio.to_thread(repo.store().list, COLL, limit=limit, cursor=cursor)
    return {"items": [{"id": d["id"], "code": d.get("code"), "title": d.get("title") or "", "sb_id": d.get("sb_id"), "status": d.get("status", "draft"),
                       "ver": int(d.get("ver") or 0), "counts": counts(d), "updated_at": d["updated_at"]} for d in items], "next_cursor": nxt}


async def put(set_id: str, body: SSPut) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        old = {s["id"]: s for s in d.get("spaces") or []}
        new = []
        for s in body.spaces:
            sd = s.model_dump()
            # 후보는 서버 값이 기준(AI 3안이 그사이 바뀌었을 수 있음) · 화면이 고친 후보는 cid 가 같을 때만 고친 값을 쓴다(보드 SC2_AI: 수락 전에도 고칠 수 있음)
            mine = {c["cid"]: c for c in sd.get("candidates") or []}
            keep = []
            for c in (old.get(s.id) or {}).get("candidates") or []:
                e = mine.get(c["cid"])
                if e and e.get("id") == c.get("id"):
                    c = {**c, **{k: e[k] for k in ("title", "user", "products", "steps", "fields") if k in e}}
                keep.append(c)
            sd["candidates"] = keep
            for sc in sd["scenarios"]:
                sc.setdefault("id", new_id("scn"))
            new.append(sd)
        d["spaces"] = new
        _clean(d)
        if d.get("status") == "done":
            d["status"] = "draft"
    return to_api(await update(set_id, fn, "고침", expected=body.expected_version))


# ── AI 시나리오 3안 ─────────────────────────────────────

class _Cand(BaseModel):
    title: str = Field(description="시나리오 이름(20자 안팎)")
    user: str = Field(description="사용자 역할(실명 금지)")
    products: list[str] = Field(description="이 장면에 쓰는 제품 · 솔루션 이름(입력 목록 중에서만)")
    steps: list[SSStep] = Field(description="장면 3~5단계. product 는 그 단계에 쓰인 제품(입력 목록 중, 없으면 null)")
    fields: list[SSFieldKV] = Field(default_factory=list, description="필요할 때만: 시간대 · 기대 효과 · 페인 포인트")


class _CandOut(BaseModel):
    candidates: list[_Cand] = Field(description="서로 다른 상황 3개")


def _mockish(s: str | None) -> bool:
    return not s or s.startswith("[mock") or "[mock]" in s


async def suggest(set_id: str, space_id: str) -> dict[str, Any]:
    d = await load(set_id)
    sp = next((s for s in d.get("spaces") or [] if s["id"] == space_id), None)
    if sp is None:
        raise repo.not_found("공간", space_id)
    names = [p["name"] for p in sp.get("products") or []]
    if not names:
        raise ApiError(422, "SPACE_WITHOUT_PRODUCT", f"{sp['name']}에 제품 · 솔루션을 먼저 하나 이상 넣어 주세요.", {"space_id": space_id})
    links = await kbq.a1(sp["name"])
    spaces = [l["id"] for l in links if l.get("type") == "space_type"]
    targets = [[p["ref"].split(":")[1], p["ref"].split(":", 2)[2]] for p in sp.get("products") or [] if (p.get("ref") or "").startswith("kb:")]
    body: dict[str, Any] = {"spaces": spaces, "targets": targets, "text": f"{sp['name']} " + " ".join(names), "limit": 5}
    cases = (await kbq.query("D1", body)).get("deployments") or []
    prompt = json.dumps({
        "요청": f"'{sp['name']}' 공간에서 아래 제품 · 솔루션이 쓰이는 사용자 시나리오 3개를 서로 다른 상황으로 만든다. "
                "제품은 목록 안에서만, 단계는 3~5개, 각 단계에 쓰인 제품을 하나 고른다(없으면 null).",
        "공간": sp["name"], "제품 · 솔루션": names, "이미 있는 시나리오": [s.get("title") for s in sp.get("scenarios") or []],
        "요구 · Storyboard": (d.get("context_text") or "")[:2000],
        "비슷한 도입사례(참고)": [{"제목": c.get("title"), "날짜": c.get("date")} for c in cases[:5]],
    }, ensure_ascii=False, indent=1)
    res = await llm.try_json("sc.space_candidates.v1", prompt, _CandOut, customer=d.get("customer"))
    out: list[dict[str, Any]] = []
    mode = "llm"
    for c in ((res.data if res else None) or {}).get("candidates") or []:
        if _mockish(c.get("title")):
            continue
        prods = [p for p in c.get("products") or [] if p in names] or names[:1]
        steps = [{"text": s.get("text") or "", "product": s.get("product") if s.get("product") in prods else None} for s in c.get("steps") or []]
        out.append({"title": c["title"], "user": c.get("user") or "", "products": prods, "steps": steps or [{"text": "[확인 필요]", "product": None}],
                    "fields": [f for f in c.get("fields") or [] if f.get("k")], "basis": "AI · 비슷한 도입사례 참고"})
        if len(out) == 3:
            break
    if not out:
        mode = "kb_only"
        for c in cases[:3]:
            out.append({"title": f"{sp['name']} — {(c.get('title') or '도입사례')[:24]} 참고", "user": "[확인 필요]", "products": names[:2],
                        "steps": [{"text": f"[확인 필요] 사례 '{c.get('title')}' 의 장면을 이 공간에 맞게 적어요", "product": names[0]}],
                        "fields": [], "basis": f"KB 도입사례 · {c.get('url') or c.get('title')}"})
        for t, u in [("첫 이용", "처음 오는 사용자"), ("혼잡 시간", "많이 몰리는 시간의 사용자"), ("야간 · 주말", "근무 외 시간의 사용자")][len(out):]:
            out.append({"title": f"{sp['name']} {t}", "user": u, "products": names[:2], "steps": [{"text": "[확인 필요]", "product": names[0]}],
                        "fields": [], "basis": "틀만(근거 없음)"})
    cands = [{"id": new_id("scn"), "cid": cid, "mode": mode, "by": "ai-pending", **c} for cid, c in zip(("A", "B", "C"), out)]

    def fn(doc: dict[str, Any]) -> None:
        s = next(x for x in doc["spaces"] if x["id"] == space_id)
        s["candidates"] = cands
    saved = await update(set_id, fn, "AI 시나리오 3안")
    return {"set": to_api(saved), "mode": mode}


async def accept(set_id: str, space_id: str, cid: str) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        s = next((x for x in d["spaces"] if x["id"] == space_id), None)
        if s is None:
            raise repo.not_found("공간", space_id)
        c = next((x for x in s.get("candidates") or [] if x["cid"] == cid), None)
        if c is None:
            raise repo.not_found("AI 후보", cid)
        s["candidates"] = [x for x in s["candidates"] if x["cid"] != cid]
        s.setdefault("scenarios", []).append({"id": c["id"], "title": c["title"], "user": c["user"], "products": c["products"],
                                              "steps": c["steps"], "fields": c.get("fields") or [], "by": f"ai-candidate-{cid}", "basis": c.get("basis")})
        _clean(d)
    return to_api(await update(set_id, fn, f"AI {cid}안 수락"))


async def drop(set_id: str, space_id: str, cid: str) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        s = next((x for x in d["spaces"] if x["id"] == space_id), None)
        if s is None:
            raise repo.not_found("공간", space_id)
        s["candidates"] = [x for x in s.get("candidates") or [] if x["cid"] != cid]
    return to_api(await update(set_id, fn, f"AI {cid}안 빼기"))


# ── 저장 · flow.json ────────────────────────────────────

def stage(d: dict[str, Any]) -> dict[str, Any]:
    """flow.json `stages.sc`(§6 · 보드 SC_DoneJson) — from 은 시작한 DSS 코드(없으면 Storyboard)."""
    c = counts(d)
    return {"ref": d.get("code") or d["id"], "ver": int(d.get("ver") or 0), "from": d.get("dss_ref") or d.get("sb_id"),
            "spaces": [{"name": s["name"], "products": [p["name"] for p in s.get("products") or []],
                        "scenarios": [{"id": sc["id"], "title": sc.get("title"), "user": sc.get("user"), "products": sc.get("products") or [],
                                       "steps": [{"text": st.get("text") or "", "product": st.get("product")} for st in sc.get("steps") or []],
                                       "fields": [{"k": f["k"], "v": f.get("v") or ""} for f in sc.get("fields") or []], "by": sc.get("by") or "manual"}
                                      for sc in s.get("scenarios") or []]} for s in d.get("spaces") or []],
            "rules": {"minProductsPerSpace": 1, "minProductsPerScenario": 1},
            "counts": {"spaces": c["spaces"], "scenarios": c["scenarios"], "spacesWithoutScenario": c["spaces_without_scenario"]}}


def summary_md(d: dict[str, Any]) -> str:
    """요약본 절(보드 SC_Done 왼쪽) — 머리 줄은 허브가 자기 이름으로 바꿔 붙인다."""
    c = counts(d)
    empty = [s["name"] for s in d.get("spaces") or [] if not s.get("scenarios")]
    lines = [f"## 시나리오 · {d.get('code') or d['id']} v{int(d.get('ver') or 0)}",
             f"- 공간 {c['spaces']} · 시나리오 {c['scenarios']}" + (f" · 시나리오 없는 공간 {len(empty)} ({' · '.join(empty)})" if empty else "")]
    top = max(d.get("spaces") or [{}], key=lambda s: len(s.get("scenarios") or []))
    if top.get("scenarios"):
        lines.append(f"- {top['name']} {len(top['scenarios'])}: " + " · ".join(sc.get("title") or "새 시나리오" for sc in top["scenarios"][:3]))
    lines.append("- 공간마다 제품 · 솔루션 1개 이상 확인됨")
    return "\n".join(lines)


def _needs_check(sc: dict[str, Any]) -> bool:
    return "[확인 필요]" in (sc.get("user") or "") or any("[확인 필요]" in (st.get("text") or "") for st in sc.get("steps") or [])


def card(d: dict[str, Any], st: dict[str, Any]) -> dict[str, Any]:
    """연결된 콘텐츠 보기 팝업(ContentPopup) 값 — 시나리오가 있는 공간 3곳 · 공간마다 시나리오 3개까지."""
    c = st["counts"]
    groups = [{"h": s["name"], "sub": f"시나리오 {len(s['scenarios'])}",
               "lines": [{"t": sc.get("title") or "새 시나리오", "note": "확인 필요" if _needs_check(sc) else None} for sc in s["scenarios"][:3]]}
              for s in st["spaces"] if s["scenarios"]][:3]
    check = sum(1 for s in st["spaces"] for sc in s["scenarios"] if _needs_check(sc))
    empty = c["spacesWithoutScenario"]
    return {"title": d.get("title") or "공간 시나리오",
            "facts": [["공간", str(c["spaces"])], ["시나리오", str(c["scenarios"])], ["시나리오 없는 공간", str(empty)]],
            "groups": groups,
            "foot": "공간마다 제품 · 솔루션 1개 이상 확인됨" + (f" · 확인 필요 시나리오 {check}" if check else ""),
            "line": f"공간 {c['spaces']} · 시나리오 {c['scenarios']}" + (f" · 시나리오 없는 공간 {empty}" if empty else "")}


async def finish(set_id: str) -> dict[str, Any]:
    d = await load(set_id)
    iss = issues(d)
    if iss:
        raise ApiError(422, iss[0]["code"], iss[0]["message"], {"issues": iss})

    def fn(doc: dict[str, Any]) -> None:
        doc["ver"] = int(doc.get("ver") or 0) + 1
        doc["status"] = "done"
        doc["saved_at"] = now_iso()
    saved = await update(set_id, fn, "저장")
    c = counts(saved)
    await register_item(feature="SC", item_id=set_id, title=saved.get("title") or "공간 시나리오", status="done", route=f"/scenario/spaces/{set_id}",
                        summary=f"공간 {c['spaces']} · 시나리오 {c['scenarios']}")
    st, md = stage(saved), summary_md(saved)
    sync = None
    if saved.get("sb_id"):
        value = {k: v for k, v in st.items() if k not in ("ref", "ver")}
        sync = await push_stage(saved["sb_id"], "sc", ref=st["ref"], ver=st["ver"], res_id=set_id, title=saved.get("title"),
                                value=value, md=md, card=card(saved, st))
    return {"stage": st, "summary_md": md, "flow_sync": {"md_added": sync["md_added"], "synced": sync.get("synced") or []} if sync else None}


async def get_stage(set_id: str) -> dict[str, Any]:
    d = await load(set_id)
    return {"stage": stage(d), "summary_md": summary_md(d)}
