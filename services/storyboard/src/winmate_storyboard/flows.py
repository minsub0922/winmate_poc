"""Storyboard 흐름(flow.json · summary.md) — 새 콘텐츠 흐름의 중심(docs/scenarios/11-content-flow.md · 보드 webapp1 SB0 · SB1 · Gate · Done).

- Storyboard 하나 = 문서 하나(컬렉션 `flows`, id = 코드 `SB-01`). 고객 요구사항을 저장하면 requirements 가 만든다(`POST /v1/flows`, internal).
- `stages.<콘텐츠>` 에는 참조만이 아니라 그 콘텐츠의 실제 값 전부가 들어간다. 콘텐츠 서비스가 저장할 때 `PUT /v1/flows/{id}/stages/{key}`(internal).
  같은 콘텐츠(ref)가 연결된 다른 Storyboard 에도 같은 값을 넣는다(수정 = 연결된 모든 Storyboard 에 반영).
- 요약본(summary.md)은 stage 가 바뀔 때마다 다시 쓴다. 사람이 고친 문장(`user_lines`)은 그 절 끝에 `✎` 표시로 남긴다.
- 분기(복제본): `POST /v1/flows/{id}:branch {stage}` → 새 Storyboard(parent) — 앞 단계(사전 작업)는 공유(sharedWith), 그 콘텐츠는 비운 채로.
"""
from __future__ import annotations

import asyncio
import logging
import copy
import json
import re
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, Field

from winmate_common.errors import ApiError
from winmate_common.ids import now_iso
from winmate_common.platform import register_item
from winmate_common.store import VersionConflict

from . import repo

log = logging.getLogger(__name__)

COLL = "flows"
META = "flow_meta"

StageKey = Literal["rq", "dss", "mi", "ca", "vp", "sp", "sc", "ppt"]
ORDER: list[str] = ["rq", "dss", "mi", "ca", "vp", "sp", "sc", "ppt"]
CONTENTS = ["mi", "ca", "vp", "sp", "sc"]
# 짧은 이름 — 진행 칸 · 완료 화면 「요약본에 더해진 부분」 머리(보드 Done: `## MI · MI-01 v2` · `## 경쟁사 · CA-01 v1` · `## 요구사항 · RQ-06 v1`)
LABEL = {"rq": "요구사항", "dss": "DSS", "mi": "MI", "ca": "경쟁사", "vp": "VP", "sp": "Spec", "sc": "시나리오", "ppt": "제안서"}
# 요약본 전체(summary.md) 절 머리 — 번호를 붙인다(보드 SB1: `## 1. 고객 요구사항 · RQ-01 v2` · `## 2. DSS · DSS-01 v1` · `## 3. Market Intelligence · MI-01 v1`)
NAME = {"rq": "고객 요구사항", "dss": "DSS", "mi": "Market Intelligence", "ca": "경쟁사 분석", "vp": "Value Proposition",
        "sp": "Spec 시트", "sc": "공간 시나리오", "ppt": "PPT 제작 · B2B 제안서"}
# 요약본 「남은 것」 줄(보드 SB1: `- 경쟁사 · VP · Spec · 공간 시나리오 → 제안서`)
REST = {"dss": "DSS", "mi": "MI", "ca": "경쟁사", "vp": "VP", "sp": "Spec", "sc": "공간 시나리오"}
# 사전 작업(없으면 시작 못 함)
NEEDS = {"rq": None, "dss": "rq", "mi": "dss", "ca": "dss", "vp": "dss", "sp": "dss", "sc": "dss", "ppt": "rq"}
# 콘텐츠 편집 화면(웹 라우트) — ref 를 넣어 쓴다
ROUTE = {"rq": "/requirements/flow/{ref}", "dss": "/dss/{ref}", "mi": "/mi/flow/{ref}", "ca": "/competitor/flow/{ref}",
         "vp": "/vp/values/{ref}", "sp": "/spec/flow/{ref}", "sc": "/scenario/spaces/{ref}", "ppt": "/proposal/{ref}"}


# ── 모델 ────────────────────────────────────────────────

class FlowCardLine(BaseModel):
    t: str
    note: str | None = Field(None, description="오른쪽 꼬리표(확인 필요 · 확장 · 출처 종류 …)")


class FlowCardGroup(BaseModel):
    h: str
    sub: str | None = None
    lines: list[FlowCardLine] = Field(default_factory=list)


class FlowCard(BaseModel):
    """연결된 콘텐츠 보기 팝업(ContentPopup)에 그대로 그리는 값 — 콘텐츠 서비스가 stage 와 함께 준다."""
    title: str
    facts: list[list[str]] = Field(default_factory=list, description="[[이름, 값]] 3칸")
    groups: list[FlowCardGroup] = Field(default_factory=list)
    foot: str | None = None
    line: str | None = Field(None, description="SB1 연결된 콘텐츠 줄의 한 줄 요약(예: RQ-01 v2 · 키맨 3 · 요구 12 · 확인 필요 4)")


class FlowStageIn(BaseModel):
    ref: str = Field(description="콘텐츠 코드(RQ-01 · DSS-01 · MI-01 …)")
    ver: int = 1
    res_id: str | None = Field(None, description="콘텐츠 서비스 자원 id(편집 화면 라우트에 쓴다). 없으면 ref")
    value: dict[str, Any] = Field(default_factory=dict, description="stages.<key> 에 들어갈 실제 값(ref · ver 는 따로)")
    md: str = Field("", description="요약본에 더할 줄(첫 줄이 '## ' 머리면 빼고 쓴다)")
    card: FlowCard | None = None
    title: str | None = None


class FlowCreate(BaseModel):
    name: str
    customer: str | None = None
    target: str | None = Field(None, description="최종 제안대상(대표이사 …)")
    rq: FlowStageIn | None = None


class KeyPillar(BaseModel):
    """Key message 를 받쳐 줄 메시지(전략 수립 팝업 · 3칸) — 근거는 연결된 콘텐츠 코드(RQ-01 대표이사 1 · DSS-01 로비 …)"""
    text: str = ""
    evidence: list[str] = Field(default_factory=list)


class FlowPatch(BaseModel):
    name: str | None = None
    key_message: str | None = None
    key_message_by: str | None = Field(None, description="manual · ai-accepted")
    key_pillars: list[KeyPillar] | None = Field(None, description="받쳐 줄 메시지(최대 3) — 빈 칸은 빼고 저장")
    summary_md: str | None = Field(None, description="사람이 고친 요약본 전체 — 새로 더한 문장만 절마다 남긴다")
    expected_version: int | None = None


class FlowBranch(BaseModel):
    stage: StageKey = Field(description="복제본을 만들 콘텐츠 — 그 앞 단계(사전 작업)만 공유한다")


class FlowCell(BaseModel):
    key: str
    label: str
    state: Literal["done", "none"]
    ref: str | None = None
    ver: int | None = None
    res_id: str | None = None
    route: str | None = None
    shared: list[str] = Field(default_factory=list)


class FlowListItem(BaseModel):
    id: str
    name: str
    customer: str | None = None
    parent: str | None = None
    is_branch: bool = False
    cells: list[FlowCell]
    progress: str = Field(description="요구사항까지 · DSS까지 · DSS + 콘텐츠 n/5")
    contents_done: int
    eligible: bool | None = Field(None, description="content= 를 줬을 때: 사전 작업이 됐는지")
    need: str | None = Field(None, description="eligible=false 면 먼저 할 것(rq · dss)")
    existing: FlowCell | None = Field(None, description="content= 를 줬을 때: 이미 연결된 그 콘텐츠")
    key_message: str | None = Field(None, description="SB0 Key message 칸(없으면 null)")
    branch_point: dict[str, Any] | None = Field(None, description="분기면 {stage, from_ref} — SB0 「SB-01 · MI에서 분기」")
    updated_at: str


class FlowList(BaseModel):
    items: list[FlowListItem]
    next_cursor: str | None = None


class FlowHistory(BaseModel):
    at: str
    key: str
    ref: str
    ver: int
    md: str
    note: str | None = None


class FlowBranchRef(BaseModel):
    """SB1 「분기 n」 팝오버 한 줄 — SB-02 · MI에서 분기 · MI-02 리테일 테넌트 관점"""
    id: str
    name: str
    stage: str | None = None
    ref: str | None = None
    title: str | None = None


class FlowDoc(BaseModel):
    id: str
    version: int
    content_rev: int = Field(0, description="콘텐츠 판 — stage(제안서 ppt 칸 제외) · Key message · 요약본이 바뀔 때만 오른다(제안서의 「Storyboard 업데이트됨」 비교용)")
    name: str
    customer: str | None = None
    target: str | None = None
    parent: str | None = None
    branch_point: dict[str, Any] | None = None
    branches: list[str] = Field(default_factory=list)
    branch_items: list[FlowBranchRef] = Field(default_factory=list, description="branches 의 이름 · 분기한 콘텐츠(GET · PATCH 응답에서 채움)")
    key_message: dict[str, Any] | None = Field(None, description="{text, by, at, pillars[{text, evidence[]}]}")
    cells: list[FlowCell]
    progress: str
    contents_done: int
    stages: dict[str, Any] = Field(description="flow.json stages — 콘텐츠 실제 값")
    cards: dict[str, FlowCard] = Field(default_factory=dict)
    summary_md: str
    user_lines: dict[str, list[str]] = Field(default_factory=dict)
    flow_json: dict[str, Any] = Field(description="flow.json 전체(화면 JSON 보기 · 완료 화면 강조에 그대로 쓴다)")
    history: list[FlowHistory] = Field(default_factory=list)
    created_at: str
    updated_at: str


class FlowStageOut(BaseModel):
    flow: FlowDoc
    key: str
    md_added: str = Field(description="요약본에 더해진 부분(완료 화면 왼쪽)")
    synced: list[str] = Field(default_factory=list, description="같은 ref 라 함께 바뀐 다른 Storyboard")


class KeyMessageCand(BaseModel):
    text: str
    basis: str | None = None
    id: str | None = Field(None, description="후보 이름(A · B · C)")
    pillars: list[KeyPillar] = Field(default_factory=list, description="받쳐 줄 메시지 3(근거 포함)")


class KeyMessageOut(BaseModel):
    candidates: list[KeyMessageCand]
    mode: Literal["llm", "rule"]


# ── 저장소 ──────────────────────────────────────────────

def _st():
    return repo.store()


def _get(fid: str) -> dict[str, Any]:
    d = _st().get(COLL, fid)
    if not d:
        raise ApiError(404, "NOT_FOUND", f"Storyboard를 찾을 수 없어요: {fid}", {"resource": "flow", "id": fid})
    return d


async def load(fid: str) -> dict[str, Any]:
    return await asyncio.to_thread(_get, fid)


def _update_sync(fid: str, fn: Callable[[dict[str, Any]], None], expected: int | None = None, note: str | None = None) -> dict[str, Any]:
    for _ in range(5):
        cur = _get(fid)
        if expected is not None and cur["version"] != expected:
            raise ApiError(409, "VERSION_CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러와 주세요.", {"version": cur["version"]})
        work = copy.deepcopy(cur)
        fn(work)
        work["updated_at"] = now_iso()
        try:
            return _st().put(COLL, fid, work, expected_version=cur["version"], note=note)
        except VersionConflict:
            if expected is not None:
                raise ApiError(409, "VERSION_CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러와 주세요.") from None
            continue
    raise ApiError(409, "CONFLICT", "동시에 고쳐 저장하지 못했어요. 다시 시도해 주세요.")


async def update(fid: str, fn: Callable[[dict[str, Any]], None], expected: int | None = None, note: str | None = None) -> dict[str, Any]:
    return await asyncio.to_thread(_update_sync, fid, fn, expected, note)


def _next_code() -> str:
    st = _st()
    for _ in range(10):
        m = st.get(META, "counter") or {"n": 0}
        n = int(m.get("n") or 0) + 1
        try:
            st.put(META, "counter", {"n": n}, expected_version=m.get("version"))
        except VersionConflict:
            continue
        code = f"SB-{n:02d}"
        if not st.get(COLL, code):
            return code
    raise ApiError(409, "CONFLICT", "Storyboard 번호를 정하지 못했어요. 다시 시도해 주세요.")


def _list_all() -> list[dict[str, Any]]:
    st = _st()
    items, cur = [], None
    while True:
        page, cur = st.list(COLL, limit=200, cursor=cur)
        items.extend(page)
        if not cur:
            break
    return items


# ── 파생 값 ─────────────────────────────────────────────

def cells(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for k in ORDER:
        s = (d.get("stages") or {}).get(k)
        meta = (d.get("stage_meta") or {}).get(k) or {}
        res = meta.get("res_id") or (s or {}).get("ref")
        out.append({"key": k, "label": LABEL[k], "state": "done" if s else "none", "ref": (s or {}).get("ref"), "ver": (s or {}).get("ver"),
                    "res_id": res if s else None, "route": ROUTE[k].format(ref=res) if s and res else None,
                    "shared": list((s or {}).get("sharedWith") or [])})
    return out


def progress(d: dict[str, Any]) -> tuple[str, int]:
    st = d.get("stages") or {}
    n = sum(1 for k in CONTENTS if st.get(k))
    if not st.get("dss"):
        return ("요구사항까지" if st.get("rq") else "시작 전"), n
    return ("DSS까지" if n == 0 else f"DSS + 콘텐츠 {n}/5"), n


def _branch_label(d: dict[str, Any]) -> str:
    return "main" if not d.get("parent") else (d.get("branch_name") or "분기")


def _section_body(md: str) -> list[str]:
    lines = [ln.rstrip() for ln in (md or "").strip().splitlines()]
    if lines and lines[0].startswith("## "):
        lines = lines[1:]
    return [ln for ln in lines if ln.strip()]


def summary(d: dict[str, Any]) -> str:
    st = d.get("stages") or {}
    ul = d.get("user_lines") or {}
    def mark(key: str) -> list[str]:
        return [f"{ln} ✎" if not ln.endswith("✎") else ln for ln in ul.get(key) or []]
    rq = st.get("rq") or {}
    head = [f"# {d['name']} — Storyboard 요약"]
    meta = []
    if d.get("customer"):
        meta.append(f"고객: {d['customer']}")
    if d.get("target") or rq.get("target"):
        meta.append(f"최종 제안대상: {d.get('target') or rq.get('target')}")
    meta.append(_branch_label(d))
    head.append(" · ".join(meta))
    head += mark("head")
    out = head[:]
    km = (d.get("key_message") or {}).get("text")
    pills = [f"- {p['text']}" for p in (d.get("key_message") or {}).get("pillars") or [] if (p.get("text") or "").strip()]
    if km or ul.get("km"):
        out += ["", "## Key message"] + ([km] if km else []) + (pills if km else []) + mark("km")
    n = 0
    for k in ORDER:
        if k == "ppt" or not st.get(k):
            continue
        n += 1
        s = st[k]
        out += ["", f"## {n}. {NAME[k]} · {s.get('ref')} v{s.get('ver')}"] + list((d.get("md_sections") or {}).get(k) or []) + mark(k)
    rest = [REST[k] for k in CONTENTS if not st.get(k)]
    if rest or not st.get("dss"):
        todo = ([] if st.get("dss") else [REST["dss"]]) + rest + ["제안서"]
        out += ["", "## 남은 것", "- " + " · ".join(todo[:-1]) + " → " + todo[-1]]
    return "\n".join(out)


def progress_code(d: dict[str, Any]) -> str:
    """flow.json `progress`(보드 SB1_Json · Done: 'rq' · 'dss+1/5') — 화면 문구는 progress()."""
    st = d.get("stages") or {}
    if not st.get("dss"):
        return "rq" if st.get("rq") else ""
    return f"dss+{sum(1 for k in CONTENTS if st.get(k))}/5"


def flow_json(d: dict[str, Any]) -> dict[str, Any]:
    st = d.get("stages") or {}
    out: dict[str, Any] = {"id": d["id"], "name": d["name"], "parent": d.get("parent"), "branches": d.get("branches") or [],
                           "keyMessage": (d.get("key_message") or {}).get("text")}
    pills = [p.get("text") for p in (d.get("key_message") or {}).get("pillars") or [] if p.get("text")]
    if pills:   # 받쳐 줄 메시지는 세웠을 때만(보드 SB1_Json 키 순서 그대로)
        out["keyPillars"] = pills
    out.update({"stages": {k: st.get(k) for k in ORDER}, "progress": progress_code(d),
                "summary": f"storyboards/{d['id']}/summary.md", "updatedAt": d.get("updated_at")})
    return out


def to_api(d: dict[str, Any], branch_items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    p, n = progress(d)
    return {"id": d["id"], "version": d["version"], "content_rev": int(d.get("content_rev") or 0), "name": d["name"], "customer": d.get("customer"), "target": d.get("target"),
            "parent": d.get("parent"), "branch_point": d.get("branch_point"), "branches": d.get("branches") or [],
            "branch_items": branch_items or [],
            "key_message": d.get("key_message"), "cells": cells(d), "progress": p, "contents_done": n,
            "stages": {k: (d.get("stages") or {}).get(k) for k in ORDER}, "cards": d.get("cards") or {},
            "summary_md": summary(d), "user_lines": d.get("user_lines") or {}, "flow_json": flow_json(d),
            "history": (d.get("history") or [])[-30:], "created_at": d["created_at"], "updated_at": d["updated_at"]}


def list_item(d: dict[str, Any], content: str | None = None) -> dict[str, Any]:
    p, n = progress(d)
    cs = cells(d)
    it = {"id": d["id"], "name": d["name"], "customer": d.get("customer"), "parent": d.get("parent"), "is_branch": bool(d.get("parent")),
          "cells": cs, "progress": p, "contents_done": n, "key_message": (d.get("key_message") or {}).get("text") or None,
          "branch_point": d.get("branch_point") if d.get("parent") else None, "updated_at": d["updated_at"]}
    if content:
        need = NEEDS.get(content)
        ok = not need or bool((d.get("stages") or {}).get(need))
        it["eligible"] = ok
        it["need"] = None if ok else need
        ex = next((c for c in cs if c["key"] == content and c["state"] == "done"), None)
        it["existing"] = ex
    return it


def _branch_ref(b: dict[str, Any]) -> dict[str, Any]:
    bp = b.get("branch_point") or {}
    k = bp.get("stage")
    s = ((b.get("stages") or {}).get(k) or {}) if k else {}
    meta = ((b.get("stage_meta") or {}).get(k) or {}) if k else {}
    return {"id": b["id"], "name": b["name"], "stage": k, "ref": s.get("ref"), "title": meta.get("title")}


def _branch_items_sync(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for bid in d.get("branches") or []:
        b = _st().get(COLL, bid)
        if b:
            out.append(_branch_ref(b))
    return out


async def get_api(fid: str, d: dict[str, Any] | None = None) -> dict[str, Any]:
    """GET · PATCH 응답 — flow + 분기 이름(SB1 「분기 n」 팝오버)."""
    d = d or await load(fid)
    return to_api(d, await asyncio.to_thread(_branch_items_sync, d))


async def index(d: dict[str, Any]) -> None:
    """workspace 작업물 색인(사이드바 · 작업 내역) — 경로는 SB1(/storyboard/flow/{id})."""
    p, _ = progress(d)
    await register_item(feature="SB", item_id=d["id"], title=(d.get("name") or d["id"])[:200], status="in_progress",
                        route=f"/storyboard/flow/{d['id']}", summary=f"{d['id']} · {d.get('customer') or ''} · {p}".replace(" ·  · ", " · "),
                        meta={"kind": "flow", "parent": d.get("parent"), "key_message": (d.get("key_message") or {}).get("text"),
                              # 고객사 · 판(stage 를 넣고 뺄 때마다 오름) — 제안서가 고객사로 거르고 「Storyboard 업데이트됨」을 판으로 비교한다(요청 proposal · 2026-10-10)
                              "customer": d.get("customer"), "version": int(d.get("content_rev") or 0)})


# ── 동작 ────────────────────────────────────────────────

def _apply_stage(d: dict[str, Any], key: str, body: FlowStageIn, note: str | None = None) -> str:
    st = d.setdefault("stages", {})
    old = st.get(key) or {}
    shared = [x for x in (old.get("sharedWith") or []) if x != d["id"]]
    val = {k: v for k, v in (body.value or {}).items() if k not in ("ref", "ver", "sharedWith")}
    st[key] = {"ref": body.ref, "ver": body.ver, **val, "sharedWith": shared}
    d.setdefault("stage_meta", {})[key] = {"res_id": body.res_id or body.ref, "title": body.title, "at": now_iso()}
    lines = _section_body(body.md)
    d.setdefault("md_sections", {})[key] = lines
    if body.card:
        d.setdefault("cards", {})[key] = body.card.model_dump()
    md_added = "\n".join([f"## {LABEL[key]} · {body.ref} v{body.ver}", *lines])   # 보드 Done 머리(짧은 이름 · 번호 없음)
    d.setdefault("history", []).append({"at": now_iso(), "key": key, "ref": body.ref, "ver": body.ver, "md": md_added, "note": note})
    d["history"] = d["history"][-60:]
    return md_added


async def create(body: FlowCreate) -> dict[str, Any]:
    def _do() -> dict[str, Any]:
        code = _next_code()
        t = now_iso()
        d = {"id": code, "name": body.name.strip() or "새 Storyboard", "customer": body.customer, "target": body.target, "parent": None,
             "branches": [], "stages": {}, "stage_meta": {}, "md_sections": {}, "cards": {}, "user_lines": {}, "history": [],
             "key_message": None, "created_at": t, "updated_at": t}
        if body.rq:
            _apply_stage(d, "rq", body.rq, "요구사항 저장 · Storyboard 자동 생성")
        d["content_rev"] = 1
        return _st().put(COLL, code, d)
    saved = await asyncio.to_thread(_do)
    await index(saved)
    return to_api(saved)


async def list_flows(limit: int, content: str | None, q: str | None) -> dict[str, Any]:
    items = await asyncio.to_thread(_list_all)
    if q:
        ql = q.strip().lower()
        items = [d for d in items if ql in (d.get("name") or "").lower() or ql in (d.get("customer") or "").lower() or ql in d["id"].lower()]
    # 메인 다음 분기 순(부모 바로 아래), 최근 수정 순
    items.sort(key=lambda d: d.get("updated_at") or "", reverse=True)
    roots = [d for d in items if not d.get("parent")]
    kids: dict[str, list[dict[str, Any]]] = {}
    for d in items:
        if d.get("parent"):
            kids.setdefault(d["parent"], []).append(d)
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in roots:
        ordered.append(r)
        seen.add(r["id"])
        for c in kids.get(r["id"], []):
            ordered.append(c)
            seen.add(c["id"])
    ordered += [d for d in items if d["id"] not in seen]
    out = [list_item(d, content) for d in ordered[:limit]]
    if content:   # 고를 수 있는 것 먼저(보드 Gate: 막힌 것은 아래)
        out.sort(key=lambda x: 0 if x["eligible"] else 1)
    return {"items": out, "next_cursor": None}


async def put_stage(fid: str, key: str, body: FlowStageIn) -> dict[str, Any]:
    if key not in ORDER:
        raise ApiError(404, "NOT_FOUND", f"모르는 콘텐츠예요: {key}")
    holder: dict[str, str] = {}

    def fn(d: dict[str, Any]) -> None:
        need = NEEDS.get(key)
        if need and not (d.get("stages") or {}).get(need) and key != "ppt":
            raise ApiError(422, "PREREQUISITE_MISSING", f"사전 작업({NAME[need]})이 먼저 있어야 해요.", {"need": need})
        holder["md"] = _apply_stage(d, key, body)
        if key != "ppt":
            d["content_rev"] = int(d.get("content_rev") or 0) + 1
    saved = await update(fid, fn, note=f"{key} {body.ref} v{body.ver}")
    await index(saved)
    # 같은 ref 를 가진 다른 Storyboard 도 같이(수정 = 연결된 모든 Storyboard)
    synced = []
    for other in await asyncio.to_thread(_list_all):
        if other["id"] == fid:
            continue
        s = (other.get("stages") or {}).get(key)
        if s and s.get("ref") == body.ref:
            o2 = await update(other["id"], lambda d: (_apply_stage(d, key, body, f"{fid} 에서 고친 내용 반영"),
                                                      d.update({"content_rev": int(d.get("content_rev") or 0) + (key != "ppt")})))
            await index(o2)
            synced.append(other["id"])
    return {"flow": to_api(saved), "key": key, "md_added": holder.get("md", ""), "synced": synced}


CLEARABLE = {"ppt"}   # 지금은 제안서 칸만 — 콘텐츠 칸은 저장 이력이라 비우지 않는다


def _clear_stage(d: dict[str, Any], key: str, note: str) -> None:
    old = (d.get("stages") or {}).pop(key, None)
    for k in ("stage_meta", "md_sections", "cards"):
        (d.get(k) or {}).pop(key, None)
    (d.get("user_lines") or {}).pop(key, None)
    if old:
        d.setdefault("history", []).append({"at": now_iso(), "key": key, "ref": old.get("ref"), "ver": old.get("ver"), "md": "", "note": note})
        d["history"] = d["history"][-60:]


async def clear_stage(fid: str, key: str, ref: str | None) -> dict[str, Any]:
    """stages.<key> 비우기(internal) — 제안서를 지우면 proposal 이 부른다. `ref` 를 주면 그 ref 일 때만. 같은 ref 를 가진 다른 Storyboard 도 함께."""
    if key not in CLEARABLE:
        raise ApiError(422, "STAGE_NOT_CLEARABLE", f"{NAME.get(key, key)} 칸은 비울 수 없어요(저장 이력).", {"key": key, "allowed": sorted(CLEARABLE)})
    cur = await load(fid)
    st = (cur.get("stages") or {}).get(key)
    if not st or (ref and st.get("ref") != ref):
        return {"flow": to_api(cur), "key": key, "md_added": "", "synced": []}
    the_ref = st.get("ref")
    saved = await update(fid, lambda d: _clear_stage(d, key, f"{the_ref} 연결 끊김"), note=f"{key} {the_ref} 비움")
    await index(saved)
    synced = []
    for other in await asyncio.to_thread(_list_all):
        if other["id"] == fid:
            continue
        s2 = (other.get("stages") or {}).get(key)
        if s2 and s2.get("ref") == the_ref:
            o2 = await update(other["id"], lambda d: _clear_stage(d, key, f"{fid} 에서 {the_ref} 연결 끊김"))
            await index(o2)
            synced.append(other["id"])
    return {"flow": to_api(saved), "key": key, "md_added": "", "synced": synced}


async def patch(fid: str, body: FlowPatch) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> None:
        if body.name is not None and body.name.strip():
            d["name"] = body.name.strip()
        old = d.get("key_message") or {}
        pills = ([{"text": p.text.strip(), "evidence": [e.strip() for e in p.evidence if e.strip()]} for p in body.key_pillars if p.text.strip()][:3]
                 if body.key_pillars is not None else list(old.get("pillars") or []))
        if body.key_message is not None:
            t = body.key_message.strip()
            d["key_message"] = {"text": t, "by": body.key_message_by or "manual", "at": now_iso(), "pillars": pills} if t else None
        elif body.key_pillars is not None and old.get("text"):
            d["key_message"] = {**old, "pillars": pills, "at": now_iso()}
        if body.summary_md is not None:
            d["user_lines"] = _user_lines(d, body.summary_md)
        if body.key_message is not None or body.key_pillars is not None or body.summary_md is not None:
            d["content_rev"] = int(d.get("content_rev") or 0) + 1
    saved = await update(fid, fn, expected=body.expected_version, note="고침")
    if body.name is not None or body.key_message is not None:
        await index(saved)
    return await get_api(fid, saved)


def _section_key(heading: str) -> str | None:
    h = heading[3:].strip()
    if h.startswith("Key message"):
        return "km"
    if h.startswith("남은 것"):
        return None
    # `1. 고객 요구사항 · RQ-01 v2`(요약본) · `MI · MI-01 v2`(완료 화면에서 붙여 넣은 머리) 둘 다
    m = re.match(r"(?:\d+\.\s*)?(.+?)\s+·", h)
    name = (m.group(1) if m else h).strip()
    for table in (NAME, LABEL):
        for k, v in table.items():
            if name == v:
                return k
    for k, v in NAME.items():
        if name.startswith(v):
            return k
    return None


def _user_lines(d: dict[str, Any], md: str) -> dict[str, list[str]]:
    base = copy.deepcopy(d)
    base["user_lines"] = {}
    gen = set(ln.strip() for ln in summary(base).splitlines())
    out: dict[str, list[str]] = {}
    key: str | None = "head"
    for ln in md.splitlines():
        s = ln.strip()
        if s.startswith("## "):
            key = _section_key(s)
            continue
        if s.startswith("# ") or not s or key is None:
            continue
        s2 = s[:-1].rstrip() if s.endswith("✎") else s
        if s2 in gen or s in gen:
            continue
        out.setdefault(key, []).append(s2)
    return out


async def branch(fid: str, body: FlowBranch) -> dict[str, Any]:
    src = await load(fid)
    key = body.stage
    keep = []
    k = NEEDS.get(key)
    while k:   # 사전 작업 사슬(dss → rq)
        keep.append(k)
        k = NEEDS.get(k)

    def _do() -> dict[str, Any]:
        code = _next_code()
        t = now_iso()
        letters = "BCDEFGHIJ"
        n_br = len(src.get("branches") or [])
        bname = f"분기 {letters[min(n_br, len(letters) - 1)]}"
        st = {}
        meta, md, cards = {}, {}, {}
        for k2 in keep:
            if (src.get("stages") or {}).get(k2):
                s = copy.deepcopy(src["stages"][k2])
                s["sharedWith"] = sorted(set((s.get("sharedWith") or []) + [fid]) - {code})
                st[k2] = s
                meta[k2] = (src.get("stage_meta") or {}).get(k2)
                md[k2] = (src.get("md_sections") or {}).get(k2)
                if (src.get("cards") or {}).get(k2):
                    cards[k2] = src["cards"][k2]
        d = {"id": code, "name": f"{src['name']} · {bname}", "branch_name": bname, "customer": src.get("customer"), "target": src.get("target"),
             "parent": fid, "branch_point": {"stage": key, "from_ref": ((src.get("stages") or {}).get(key) or {}).get("ref")},
             "branches": [], "stages": st, "stage_meta": meta, "md_sections": md, "cards": cards, "user_lines": {},
             "history": [{"at": t, "key": key, "ref": "", "ver": 0, "md": f"{fid} 에서 분기 · {NAME[key]} 복제본", "note": "분기"}],
             # Key message 는 콘텐츠로 세우는 전략이라 분기에서 새로 세운다(보드 SB0 · SBPopup: SB-02 Key message 「아직 없음」)
             "key_message": None, "created_at": t, "updated_at": t}
        d["content_rev"] = 1
        return _st().put(COLL, code, d)
    new = await asyncio.to_thread(_do)

    def fn(d: dict[str, Any]) -> None:
        d["branches"] = list(dict.fromkeys((d.get("branches") or []) + [new["id"]]))
        for k2 in keep:
            s = (d.get("stages") or {}).get(k2)
            if s:
                s["sharedWith"] = sorted(set((s.get("sharedWith") or []) + [new["id"]]))
    await index(await update(fid, fn, note=f"분기 {new['id']}"))
    await index(new)
    return to_api(await load(new["id"]))


# ── Key message 후보(AI 추가기능) ──────────────────────

class _KM(BaseModel):
    candidates: list[KeyMessageCand]


_REF_RE = re.compile(r"^(RQ|DSS|MI|CA|VP|SP|SC)-[0-9A-Za-z]+")
_REF_KEY = {"RQ": "rq", "DSS": "dss", "MI": "mi", "CA": "ca", "VP": "vp", "SP": "sp", "SC": "sc"}


def _pool(d: dict[str, Any]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """연결된 콘텐츠의 실제 문장(지어내지 않는다) → (Key message 후보 문장, 받쳐 줄 메시지 문장) · 근거 코드."""
    st = d.get("stages") or {}
    heads: list[tuple[str, str]] = []
    rest: list[tuple[str, str]] = []
    rq = st.get("rq") or {}
    r = rq.get("ref") or "RQ"
    for t in rq.get("goals") or []:
        if isinstance(t, str) and t.strip():
            heads.append((t.strip(), r))
    for km in rq.get("keymen") or []:
        if not isinstance(km, dict):
            continue
        for j, n in enumerate(km.get("needs") or []):
            if isinstance(n, str) and n.strip():
                (heads if j == 0 else rest).append((n.strip(), f"{r} {km.get('role') or ''}".strip()))
    for it in rq.get("requirements") or []:
        if isinstance(it, dict) and (it.get("text") or "").strip() and it.get("status") != "check":
            rest.append((it["text"].strip(), f"{r} {it.get('id') or ''}".strip()))
    vp = st.get("vp") or {}
    for it in vp.get("items") or []:
        for v in (it or {}).get("values") or []:
            if (v.get("message") or "").strip():
                heads.append((v["message"].strip(), f"{vp.get('ref')} {it.get('name') or ''}".strip()))
    sc = st.get("sc") or {}
    for sp in sc.get("spaces") or []:
        for c in (sp or {}).get("scenarios") or []:
            if (c.get("title") or "").strip():
                rest.append((c["title"].strip(), f"{sc.get('ref')} {sp.get('name') or ''}".strip()))
    for k in ("mi", "ca", "dss"):
        for ln in ((d.get("md_sections") or {}).get(k) or [])[:3]:
            t = ln.lstrip("- ").strip()
            if t and k != "dss":
                rest.append((t, (st.get(k) or {}).get("ref") or k.upper()))
    def uniq(xs: list[tuple[str, str]]) -> list[tuple[str, str]]:
        seen: set[str] = set()
        out = []
        for t, b in xs:
            t = t[:60]
            if t not in seen:
                seen.add(t)
                out.append((t, b))
        return out
    return uniq(heads), uniq(rest)


def _rule_candidates(d: dict[str, Any]) -> list[dict[str, Any]]:
    heads, rest = _pool(d)
    out: list[dict[str, Any]] = []
    for i, (t, b) in enumerate(heads[:3]):
        others = [x for x in heads + rest if x[0] != t]
        if others:
            others = others[i % len(others):] + others[:i % len(others)]
        out.append({"id": "ABC"[i], "text": t, "basis": b, "pillars": [{"text": pt, "evidence": [pb]} for pt, pb in others[:3]]})
    return out


def _fix_basis(d: dict[str, Any], ev: str) -> str | None:
    """근거 코드는 이 Storyboard 에 연결된 콘텐츠 것만 — 모델이 다른 코드를 쓰면 같은 종류의 실제 코드로 바꾸고, 없으면 버린다."""
    ev = (ev or "").strip()
    m = _REF_RE.match(ev)
    if not m:
        return ev or None
    key = _REF_KEY[m.group(1)]
    real = ((d.get("stages") or {}).get(key) or {}).get("ref")
    if not real:
        return None
    return real + ev[m.end():]


def _norm_cand(d: dict[str, Any], c: dict[str, Any], i: int) -> dict[str, Any] | None:
    t = (c.get("text") or c.get("km") or "").strip()
    if not t:
        return None
    pills = []
    for p in (c.get("pillars") or [])[:3]:
        if isinstance(p, str):
            p = {"text": p}
        pt = (p.get("text") or "").strip()
        if not pt:
            continue
        evs = list(p.get("evidence") or ([p["basis"]] if p.get("basis") else []))
        pills.append({"text": pt, "evidence": [e for e in (_fix_basis(d, x) for x in evs) if e]})
    return {"id": c.get("id") or "ABC"[i], "text": t, "basis": _fix_basis(d, c.get("basis") or "") if c.get("basis") else None, "pillars": pills}


async def key_message_candidates(fid: str) -> dict[str, Any]:
    d = await load(fid)
    refs = [f"{k}: {(d.get('stages') or {})[k].get('ref')}" for k in ORDER if (d.get("stages") or {}).get(k)]
    try:
        from winmate_common.ai import ai

        prompt = json.dumps({"task": "연결된 콘텐츠로 제안의 Key message(한 줄, 20자 안팎) 후보 3개(id A·B·C). 후보마다 받쳐 줄 메시지(pillars) 3개와 "
                                     "근거(evidence: 연결된 콘텐츠 코드 + 짧은 위치, 예 'RQ-01 대표이사')를 붙인다. 수치 · 고객명은 입력에 있는 것만.",
                             "refs": refs, "summary_md": summary(d)[:6000]}, ensure_ascii=False)
        res = await ai().json("sb.key_message.v1", prompt, _KM, confidential=True, temperature=0.4)
        data = (res or {}).get("json") if isinstance((res or {}).get("json"), dict) else (res or {})   # ai().json 은 검증된 dict 를 돌려준다
        raw = data.get("candidates") or []
        cands = [c for c in (_norm_cand(d, x, i) for i, x in enumerate(raw[:3]) if isinstance(x, dict)) if c]
        if cands:
            return {"candidates": cands, "mode": "llm"}
    except Exception as exc:  # noqa: BLE001 — 모델이 없으면 규칙 후보
        log.info("sb.key_message.v1 실패 → 규칙 후보: %s", exc)
    return {"candidates": _rule_candidates(d), "mode": "rule"}


# ── 콘텐츠 목록(보드 List — 콘텐츠 하나에 연결된 Storyboard 들) ──

class FlowSbRef(BaseModel):
    id: str
    name: str
    is_branch: bool = False


class FlowContentItem(BaseModel):
    key: str
    ref: str
    ver: int
    title: str
    res_id: str
    route: str
    storyboards: list[FlowSbRef]
    updated_at: str


class FlowContentList(BaseModel):
    items: list[FlowContentItem]


async def list_contents(key: str) -> dict[str, Any]:
    items = await asyncio.to_thread(_list_all)
    by: dict[str, dict[str, Any]] = {}
    for d in sorted(items, key=lambda x: x.get("created_at") or ""):
        s = (d.get("stages") or {}).get(key)
        if not s:
            continue
        meta = (d.get("stage_meta") or {}).get(key) or {}
        ref = s.get("ref")
        res = meta.get("res_id") or ref
        it = by.setdefault(ref, {"key": key, "ref": ref, "ver": s.get("ver") or 1, "title": meta.get("title") or ref, "res_id": res,
                                 "route": ROUTE[key].format(ref=res), "storyboards": [], "updated_at": meta.get("at") or d.get("updated_at")})
        it["ver"] = max(it["ver"], s.get("ver") or 1)
        if meta.get("at") and meta["at"] > (it["updated_at"] or ""):
            it["updated_at"] = meta["at"]
            it["title"] = meta.get("title") or it["title"]
        it["storyboards"].append({"id": d["id"], "name": d["name"], "is_branch": bool(d.get("parent"))})
    out = sorted(by.values(), key=lambda x: x["updated_at"] or "", reverse=True)
    return {"items": out}
