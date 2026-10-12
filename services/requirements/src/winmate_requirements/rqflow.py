"""고객 요구사항 — 새 콘텐츠 흐름(2026-10-08 · docs/scenarios/11-content-flow.md · 보드 webapp1 RQ0 · RQ1 · RQ_Done).

이전 정의서(`/v1/requirements*`)와 따로 둔 가벼운 자원 `/v1/rq-flows*`(DocStore 컬렉션 `rq_flows`, id `rqf_…`, 코드 `RQ-NN`).
- 폼 하나: 프로젝트명 · 고객사 · 최종 제안대상 · 제작자 의견(**고객 문서 · Storyboard 에서 빠진다**) · 키맨(가중치 합 100) · 키맨별 요구사항.
  요구사항마다 status `ok | check`(확인 필요), flag `none | vague(범위 불명확) | ask(고객에게 확인)`, 출처 by `manual | file`
  (`ai-pending | ai-accepted` 는 2026-10-12 에 지운 AI 심층 질의가 남긴 예전 값 — 읽기만 한다).
- 고치기는 폼 전체를 보낸다(PUT, `expected_version` 이 다르면 409). 화면은 자동 저장.
- 파일 첨부(`:fill` 202 잡 `rq.flow.fill`) — 파일 글 → `rq.flow_extract.v1` → 빈 칸만 채움(사람 값 보호). 모델이 안 되면 아무것도 바꾸지 않는다.
- AI 심층 질의(폼 개선 과정)는 2026-10-12 에 뺐다 — 폼 입력 · 파일 첨부 · 저장만 있다.
- 저장(`:finish`) — 처음이면 `create_flow` 로 Storyboard 를 만들고(sb_ids 에 저장), 다음부터는 `push_stage(sb, "rq")`(같은 ref 의 다른 Storyboard 는 허브가 함께 고친다).
  stage 값은 §6 `rq` 모양. ver = 저장 횟수.
- 지우기(`DELETE`) — 한 번도 저장하지 않은 초안만(status draft · ver 0 · sb_ids 없음). 저장한 것은 Storyboard 에 연결돼 있어 409 SAVED_CONTENT.
  소프트 삭제 + workspace 색인 지우기, 파일로 채우는 잡이 돌고 있으면 취소한다.
"""
from __future__ import annotations

import asyncio
import copy
import logging
import re
import uuid
from collections.abc import Callable
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError
from winmate_common.flow import create_flow, push_stage
from winmate_common.graph import run_graph
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import JobCanceled, JobContext, current_job, jobs
from winmate_common.platform import register_item, unregister_item
from winmate_common.store import VersionConflict

from . import llm, platform_calls, repo
from .fill import classify_by_name
from .models import JobAccepted, Model
from .textutil import clip, nfc, normalize_name, numbers_in, same_item

log = logging.getLogger("winmate.requirements.rqflow")

COLL = "rq_flows"
META = "rq_flow_meta"
FEATURE = "RQ"
MAX_KEYMEN = 8
MAX_REQS = 12
EXTRACT_TASK = "rq.flow_extract.v1"
FILL_KIND = "rq.flow.fill"

By = Literal["manual", "file", "ai-pending", "ai-accepted"]   # ai-* 는 예전 AI 심층 질의 값(읽기만)
Flag = Literal["none", "vague", "ask"]
Status = Literal["ok", "check"]


def route_of(fid: str) -> str:
    return f"/requirements/flow/{fid}"


def _sid(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ── 모델(API) — 스키마 이름은 RF 접두 ─────────────────────

class RFReq(Model):
    id: str
    text: str
    status: Status = Field("ok", description="ok · check(확인 필요)")
    flag: Flag = Field("none", description="none · vague(범위 불명확) · ask(고객에게 확인)")
    by: By = "manual"


class RFKeyman(Model):
    id: str
    role: str = Field("", description="키맨 직함 · 역할(예: 자산관리팀장)")
    weight: int = Field(0, ge=0, le=100)
    weight_by: By = "manual"
    reqs: list[RFReq] = Field(default_factory=list)


class RFSource(Model):
    file_id: str
    name: str
    pages: int | None = None
    filled: int = 0
    read_at: str


class RFCounts(Model):
    keymen: int
    reqs: int
    check: int
    weight_sum: int


class RFDoc(Model):
    id: str
    version: int
    code: str
    title: str = Field("", description="프로젝트명")
    customer: str = ""
    target: str = Field("", description="최종 제안대상")
    target_by: By | None = None
    customer_by: By | None = None
    title_by: By | None = None
    note: str = Field("", description="제작자 의견 — 고객 문서 · Storyboard 에서 빠진다(internal)")
    keymen: list[RFKeyman] = Field(default_factory=list)
    sources: list[RFSource] = Field(default_factory=list)
    fill_job: str | None = Field(None, description="파일 첨부 잡(진행 중일 때)")
    status: Literal["draft", "done"] = "draft"
    ver: int = Field(0, description="저장(완료) 횟수 = stage ver")
    sb_ids: list[str] = Field(default_factory=list, description="이 요구사항이 연결된 Storyboard(처음 저장 때 자동 생성)")
    counts: RFCounts
    created_at: str
    updated_at: str
    saved_at: str | None = None


class RFListItem(Model):
    id: str
    code: str
    title: str
    customer: str
    status: Literal["draft", "done"]
    ver: int
    sb_ids: list[str]
    counts: RFCounts
    updated_at: str


class RFList(Model):
    items: list[RFListItem]
    next_cursor: str | None = None


class RFReqIn(BaseModel):
    id: str | None = None
    text: str = Field("", max_length=300)
    status: Status | None = None
    flag: Flag | None = None
    by: By | None = None


class RFKeymanIn(BaseModel):
    id: str | None = None
    role: str = Field("", max_length=80)
    weight: int = Field(0, ge=0, le=100)
    weight_by: By | None = None
    reqs: list[RFReqIn] = Field(default_factory=list, max_length=MAX_REQS)


class RFCreate(BaseModel):
    title: str = Field("", max_length=120)
    customer: str = Field("", max_length=80)
    target: str = Field("", max_length=80)
    note: str = Field("", max_length=2000)
    keymen: list[RFKeymanIn] | None = Field(None, max_length=MAX_KEYMEN, description="없으면 빈 키맨 하나")


class RFUpdate(RFCreate):
    keymen: list[RFKeymanIn] | None = Field(None, max_length=MAX_KEYMEN, description="없으면 그대로")
    expected_version: int | None = Field(None, description="다르면 409 VERSION_CONFLICT")


class RFFillIn(BaseModel):
    file_ids: list[str] = Field(min_length=1, max_length=5)


class RFFlowSync(Model):
    md_added: str
    synced: list[str] = Field(default_factory=list)


class RFStageOut(Model):
    stage: dict[str, Any] = Field(description="Storyboard flow.json 의 stages.rq(§6)")
    summary_md: str
    flow_sync: RFFlowSync | None = Field(None, description="허브 반영 결과(허브가 안 되면 null)")
    sb_id: str | None = None
    sb_name: str | None = None
    created: bool = Field(False, description="이번 저장으로 Storyboard 가 새로 만들어졌는지")
    doc: RFDoc


# ── 저장소 ──────────────────────────────────────────────

def _store():
    return repo.store()


def _get(fid: str) -> dict[str, Any]:
    st = _store()
    d = st.get(COLL, fid)
    if d is None and fid.upper().startswith("RQ-"):     # 허브 라우트가 ref(코드)로 올 때
        items, _ = st.list(COLL, where={"code": fid.upper()}, limit=1)
        d = items[0] if items else None
    if not d:
        raise repo.not_found("고객 요구사항", fid)
    return d


async def load(fid: str) -> dict[str, Any]:
    return await asyncio.to_thread(_get, fid)


def _update_sync(fid: str, fn: Callable[[dict[str, Any]], None], expected: int | None) -> dict[str, Any]:
    st = _store()
    for _ in range(8):
        cur = _get(fid)
        if expected is not None and cur["version"] != expected:
            raise ApiError(409, "VERSION_CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러와 주세요.", {"version": cur["version"]})
        work = copy.deepcopy(cur)
        fn(work)
        try:
            return st.put(COLL, cur["id"], work, expected_version=cur["version"], keep_history=False)
        except VersionConflict:
            if expected is not None:
                raise ApiError(409, "VERSION_CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러와 주세요.") from None
            continue
    raise ApiError(409, "CONFLICT", "동시에 고쳐 저장하지 못했어요. 다시 시도해 주세요.")


async def update(fid: str, fn: Callable[[dict[str, Any]], None], expected: int | None = None) -> dict[str, Any]:
    return await asyncio.to_thread(_update_sync, fid, fn, expected)


async def _hub_max() -> int:
    """허브에 이미 있는 rq ref 중 가장 큰 번호 — 같은 ref 로 다른 Storyboard 가 묶이지 않게."""
    try:
        res = await ServiceClient("storyboard", timeout=10).get("/v1/flows/contents/rq")
    except Exception as exc:  # noqa: BLE001
        log.info("허브 rq 목록을 못 읽음(번호는 로컬만): %s", exc)
        return 0
    n = 0
    for it in res.get("items") or []:
        m = re.match(r"RQ-(\d+)$", str(it.get("ref") or ""))
        if m:
            n = max(n, int(m.group(1)))
    return n


def _next_code_sync(floor: int) -> str:
    st = _store()
    for _ in range(10):
        m = st.get(META, "counter")
        n = max(int((m or {}).get("n") or 0), floor) + 1
        try:
            st.put(META, "counter", {"n": n}, expected_version=(m or {}).get("version", 0), keep_history=False)
        except VersionConflict:
            continue
        code = f"RQ-{n:02d}"
        items, _ = st.list(COLL, where={"code": code}, limit=1)
        if not items:
            return code
        floor = n
    raise ApiError(409, "CONFLICT", "요구사항 번호를 정하지 못했어요. 다시 시도해 주세요.")


# ── 정규화 · 파생 값 ─────────────────────────────────────

def _clean(s: str | None, n: int) -> str:
    return clip(re.sub(r"\s+", " ", nfc(s or "")).strip(), n)


def _req_from(r: RFReqIn | dict[str, Any], old: dict[str, Any] | None) -> dict[str, Any] | None:
    raw = r.model_dump() if isinstance(r, BaseModel) else dict(r)
    text = _clean(raw.get("text"), 300)
    if not text:
        return None
    o = old or {}
    flag = raw.get("flag") or o.get("flag") or "none"
    status = raw.get("status") or ("check" if flag != "none" else o.get("status") or "ok")
    if raw.get("flag") == "none" and raw.get("status") is None:
        status = "ok"
    by = raw.get("by") or o.get("by") or "manual"
    if o and o.get("text") != text and raw.get("by") is None:
        by = "manual"                                  # 사람이 문장을 고치면 직접 쓴 값
    return {"id": raw.get("id") or o.get("id") or _sid("q_"), "text": text, "status": status, "flag": flag, "by": by}


def _keymen_from(items: list[RFKeymanIn], old: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {k["id"]: k for k in old}
    out = []
    for k in items[:MAX_KEYMEN]:
        ok = by_id.get(k.id or "") or {}
        old_reqs = {r["id"]: r for r in ok.get("reqs") or []}
        reqs = [x for x in (_req_from(r, old_reqs.get(r.id or "")) for r in k.reqs[:MAX_REQS]) if x]
        wby = k.weight_by or ("manual" if ok and ok.get("weight") != k.weight else ok.get("weight_by") or "manual")
        out.append({"id": k.id or ok.get("id") or _sid("k_"), "role": _clean(k.role, 80), "weight": int(k.weight), "weight_by": wby, "reqs": reqs})
    return out


def _kms(d: dict[str, Any]) -> list[dict[str, Any]]:
    return [k for k in d.get("keymen") or [] if k.get("role") or k.get("reqs")]


def counts(d: dict[str, Any]) -> dict[str, int]:
    kms = _kms(d)
    reqs = [r for k in kms for r in k.get("reqs") or []]
    return {"keymen": len(kms), "reqs": len(reqs), "check": sum(1 for r in reqs if r.get("status") == "check"),
            "weight_sum": sum(int(k.get("weight") or 0) for k in kms)}


_DROPPED = ("deep", "target_ask")   # 예전 AI 심층 질의가 문서에 남긴 칸 — 응답에 싣지 않는다


def to_api(d: dict[str, Any]) -> dict[str, Any]:
    return {**{k: v for k, v in d.items() if k not in _DROPPED}, "counts": counts(d)}


def display_title(d: dict[str, Any]) -> str:
    t, c = d.get("title") or "", d.get("customer") or ""
    if t and c:
        return t if t.startswith(c) else f"{c} · {t}"
    return t or c or "새 요구사항"


_TAIL = ("리뉴얼", "구축", "사업", "프로젝트", "제안", "도입", "개선", "구축사업", "조성")


def sb_name(d: dict[str, Any]) -> str:
    """Storyboard 이름 — 프로젝트명에서 끝의 일반 낱말(리뉴얼 · 구축 …)을 뺀 것(보드: 성수 플래그십 리테일 리뉴얼 → 성수 플래그십 리테일)."""
    t = (d.get("title") or "").strip()
    if not t:
        return f"{d.get('customer') or '새'} 제안"
    words = t.split()
    while len(words) > 1 and words[-1] in _TAIL:
        words.pop()
    return clip(" ".join(words), 40)


def _list_sync(limit: int, cursor: str | None) -> tuple[list[dict[str, Any]], str | None]:
    return _store().list(COLL, limit=limit, cursor=cursor)


async def list_flows(limit: int, cursor: str | None) -> dict[str, Any]:
    items, nxt = await asyncio.to_thread(_list_sync, limit, cursor)
    return {"items": [{"id": d["id"], "code": d["code"], "title": display_title(d), "customer": d.get("customer") or "", "status": d.get("status") or "draft",
                       "ver": int(d.get("ver") or 0), "sb_ids": d.get("sb_ids") or [], "counts": counts(d), "updated_at": d["updated_at"]} for d in items],
            "next_cursor": nxt}


async def _index(d: dict[str, Any]) -> None:
    c = counts(d)
    await register_item(feature=FEATURE, item_id=d["id"], title=display_title(d), status="done" if d.get("status") == "done" else "draft",
                        route=route_of(d["id"]), summary=f"{d['code']} · 키맨 {c['keymen']} · 요구 {c['reqs']}" + (f" · 확인 필요 {c['check']}" if c["check"] else ""))


# ── 만들기 · 고치기 ─────────────────────────────────────

async def create(body: RFCreate) -> dict[str, Any]:
    floor = await _hub_max()
    code = await asyncio.to_thread(_next_code_sync, floor)
    keymen = _keymen_from(body.keymen, []) if body.keymen is not None else [{"id": _sid("k_"), "role": "", "weight": 100, "weight_by": "manual", "reqs": []}]
    doc = {"code": code, "title": _clean(body.title, 120), "customer": _clean(body.customer, 80), "target": _clean(body.target, 80),
           "target_by": "manual" if body.target.strip() else None, "customer_by": None, "title_by": None,
           "note": (body.note or "").strip()[:2000], "keymen": keymen, "sources": [], "fill_job": None,
           "status": "draft", "ver": 0, "sb_ids": [], "saved_at": None}
    fid = new_id("rqf")
    saved = await asyncio.to_thread(_store().put, COLL, fid, doc, keep_history=False)
    await _index(saved)
    return to_api(saved)


async def put_form(fid: str, body: RFUpdate) -> dict[str, Any]:
    before = await load(fid)
    if before.get("fill_job"):
        raise ApiError(409, "FILLING", "파일에서 폼을 채우는 중이에요. 끝난 뒤 고쳐 주세요.", {"job_id": before["fill_job"]})

    def fn(d: dict[str, Any]) -> None:
        for f, n in (("title", 120), ("customer", 80), ("target", 80)):
            v = _clean(getattr(body, f), n)
            if v != (d.get(f) or ""):
                d[f] = v
                d[f"{f}_by"] = "manual" if v else None
        d["note"] = (body.note or "").strip()[:2000]
        if body.keymen is not None:
            d["keymen"] = _keymen_from(body.keymen, d.get("keymen") or [])
    saved = await update(before["id"], fn, body.expected_version)
    if display_title(saved) != display_title(before):
        await _index(saved)
    return to_api(saved)


# ── 지우기(저장 전 초안만) ───────────────────────────────

SAVED_MSG = "저장한 콘텐츠는 Storyboard에 연결돼 있어 지울 수 없어요"


def is_saved(d: dict[str, Any]) -> bool:
    """한 번이라도 저장(:finish)했는지 — 저장하면 Storyboard 에 연결된다(status done · ver ≥ 1 · sb_ids)."""
    return d.get("status") == "done" or int(d.get("ver") or 0) > 0 or bool(d.get("sb_ids"))


def _delete_sync(fid: str, expected: int | None) -> dict[str, Any]:
    cur = _get(fid)
    if expected is not None and cur["version"] != expected:
        raise ApiError(409, "VERSION_CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러와 주세요.", {"version": cur["version"]})
    if is_saved(cur):
        raise ApiError(409, "SAVED_CONTENT", SAVED_MSG, {"code": cur["code"], "ver": int(cur.get("ver") or 0), "sb_ids": cur.get("sb_ids") or []})
    try:   # 확인 → 지우기 사이에 저장이 끼면 지우지 않는다(DocStore 판 확인, 같은 트랜잭션)
        _store().delete(COLL, cur["id"], expected_version=cur["version"])
    except VersionConflict as exc:
        raise ApiError(409, "VERSION_CONFLICT", "방금 다른 곳에서 저장했어요. 새로 불러와 주세요.", {}) from exc
    return cur


async def delete(fid: str, expected: int | None = None) -> None:
    """저장 전 초안 지우기(소프트 삭제) — 저장한 것은 409 SAVED_CONTENT, 없으면 404. 채우는 잡은 취소하고 색인도 지운다."""
    cur = await asyncio.to_thread(_delete_sync, fid, expected)
    if cur.get("fill_job"):
        try:
            await jobs().cancel(cur["fill_job"])
        except Exception as exc:  # noqa: BLE001 — 잡 취소 실패가 지우기를 막지 않는다
            log.info("채우기 잡 취소 실패 %s: %s", cur["fill_job"], exc)
    await unregister_item(cur["id"])


def gone(fid: str) -> bool:
    """지운(또는 없는) 초안인지 — 잡이 도는 사이 지워졌으면 조용히 끝낸다."""
    return _store().get(COLL, fid) is None


# ── 파일 첨부(잡 rq.flow.fill) ───────────────────────────

class _ExReq(BaseModel):
    text: str = Field(description="요구 한 문장(60자 이내, 원문 표현)")
    vague: bool = Field(False, description="범위 · 대상이 불분명하면 true")


class _ExKeyman(BaseModel):
    role: str = Field(description="키맨 직함 · 역할(예: 자산관리팀장)")
    weight: int | None = Field(None, description="문서에 비중이 적힌 경우만(0~100), 아니면 null")
    reqs: list[_ExReq] = Field(default_factory=list)


class RFExtraction(BaseModel):
    project_name: str | None = None
    customer_name: str | None = None
    final_audience: str | None = Field(None, description="문서에 명시된 경우만")
    author_notes: list[str] = Field(default_factory=list, description="제작자(우리 영업)의 목표 · 내부 전략 — 고객 요구가 아님")
    keymen: list[_ExKeyman] = Field(default_factory=list)


async def start_fill(fid: str, body: RFFillIn) -> dict[str, Any]:
    d = await load(fid)
    if d.get("fill_job"):
        raise ApiError(409, "FILLING", "이미 파일에서 폼을 채우는 중이에요.", {"job_id": d["fill_job"]})
    for f in body.file_ids:
        await platform_calls.file_meta(f)              # 없으면 404 FILE_NOT_FOUND
    job_id = new_id("job")

    def fn(doc: dict[str, Any]) -> None:
        if doc.get("fill_job"):
            raise ApiError(409, "FILLING", "이미 파일에서 폼을 채우는 중이에요.", {"job_id": doc["fill_job"]})
        doc["fill_job"] = job_id
    await update(d["id"], fn)
    await jobs().enqueue("requirements", FILL_KIND, {"rq_flow_id": d["id"], "file_ids": body.file_ids},
                         title=f"{display_title(d)} · 파일로 채우기", ref=d["id"], job_id=job_id)
    return JobAccepted(job_id=job_id, status="queued", ref={"kind": "rq_flow", "id": d["id"]}).model_dump()


class _FillState(TypedDict, total=False):
    rq_flow_id: str
    file_ids: list[str]
    files: list[dict[str, Any]]
    extractions: list[dict[str, Any]]
    filled: int
    note: str | None


async def _fill_read(state: _FillState) -> dict[str, Any]:
    files = []
    for fid in state["file_ids"]:
        f: dict[str, Any] = {"file_id": fid, "name": fid, "kind": None, "pages": None, "text": "", "error": None}
        try:
            meta = await platform_calls.file_meta(fid)
            f["name"], f["kind"] = meta.get("name") or fid, meta.get("kind")
            parsed = await platform_calls.parsed(fid)
            pages = parsed.get("pages") or []
            email = parsed.get("email") or None
            text = "\n".join(f"--- {i + 1} ---\n{p.get('text') or ''}" for i, p in enumerate(pages))
            if email:
                text = f"제목: {email.get('subject') or ''}\n{email.get('body') or ''}"
            f["pages"] = len(pages) or None
            f["text"] = text[:30000]
            if not f["text"].strip():
                f["error"] = "읽을 글자가 없어요"
        except Exception as exc:  # noqa: BLE001
            f["error"] = getattr(exc, "message", None) or "읽지 못했어요"
        files.append(f)
    job = current_job()
    if job:
        await job.progress(30, "파일을 읽었어요")
    return {"files": files}


def _extract_prompt(f: dict[str, Any], kind: str) -> str:
    return (
        f"다음은 고객에게서 받은 {'제안 요청 문서' if kind == 'rfp' else '회의 · 미팅 메모' if kind == 'meeting_memo' else '메일' if kind == 'mail' else '문서'}입니다"
        f"(파일: {f['name']}).\n고객 요구사항 폼을 채울 값을 뽑아 주세요.\n"
        "- project_name: 프로젝트(사업) 이름, 문서 표현 그대로(120자 이내)\n- customer_name: 고객사 이름\n"
        "- final_audience: 최종 제안을 받는 사람 · 기구 — 문서에 명시된 경우만(추론 금지)\n"
        "- keymen: 고객 쪽 의사결정 관여자(role)와 그 사람이 바라는 것(reqs, 60자 이내 원문 표현). 범위가 불분명한 요구는 vague=true. "
        "비중(weight)은 문서에 적힌 경우만\n- author_notes: 제작자(우리 영업)의 목표 · 내부 전략(예: 스펙인이 목표) — 고객 요구가 아니다\n"
        "문서에 없는 값은 비워 두세요. 문서에 없는 숫자 · 고객명 · 모델명을 쓰지 마세요.\n\n[문서]\n" + f["text"]
    )


async def _fill_extract(state: _FillState) -> dict[str, Any]:
    out = []
    note = None
    for f in state["files"]:
        if f.get("error"):
            continue
        kind = classify_by_name(f["name"], f.get("kind")) or "other"
        try:
            ex = await llm.call_json(EXTRACT_TASK, _extract_prompt(f, kind), RFExtraction, timeout=150)
        except ApiError as exc:
            note = exc.message
            continue
        out.append({"file": f, "ex": ex})
    job = current_job()
    if job:
        await job.progress(75, "폼에 넣는 중")
    return {"extractions": out, "note": note}


def _mockish(s: Any) -> bool:
    return not isinstance(s, str) or not s.strip() or "[mock" in s


def _grounded(value: str, text: str) -> bool:
    """문서에 없는 숫자가 섞인 값은 버린다(숫자 가드)."""
    return numbers_in(value) <= numbers_in(text)


def merge_extraction(d: dict[str, Any], ex: dict[str, Any], f: dict[str, Any]) -> int:
    """빈 칸만 채운다 — 사람이 쓴 값 · 키맨 · 요구는 그대로 두고 없는 것만 더한다. 채운 칸 수."""
    text = f.get("text") or ""
    n = 0
    for key, field, lim in (("project_name", "title", 120), ("customer_name", "customer", 80), ("final_audience", "target", 80)):
        v = ex.get(key)
        if not _mockish(v) and not (d.get(field) or "").strip() and _grounded(v, text):
            d[field] = _clean(v, lim)
            d[f"{field}_by"] = "file"
            n += 1
    notes = [x.strip() for x in ex.get("author_notes") or [] if not _mockish(x)]
    if notes and not (d.get("note") or "").strip():
        d["note"] = "\n".join(notes)[:2000]
        n += 1
    kms = [k for k in d.get("keymen") or [] if k.get("role") or k.get("reqs")]   # 빈 키맨 자리는 파일 값으로 바꾼다
    added_km = False
    for ek in ex.get("keymen") or []:
        role = _clean(ek.get("role"), 80)
        if _mockish(role):
            continue
        km = next((k for k in kms if normalize_name(k.get("role")) == normalize_name(role)), None)
        if km is None:
            if len(kms) >= MAX_KEYMEN:
                continue
            w = ek.get("weight")
            km = {"id": _sid("k_"), "role": role, "weight": int(w) if isinstance(w, int) and 0 <= w <= 100 else 0,
                  "weight_by": "file" if isinstance(w, int) else "manual", "reqs": [], "_w": isinstance(w, int)}
            kms.append(km)
            added_km = True
            n += 1
        for er in ek.get("reqs") or []:
            t = _clean(er.get("text"), 300)
            if _mockish(t) or not _grounded(t, text) or len(km["reqs"]) >= MAX_REQS:
                continue
            if any(same_item(t, r["text"]) for r in km["reqs"]):
                continue
            vague = bool(er.get("vague"))
            km["reqs"].append({"id": _sid("q_"), "text": t, "status": "check" if vague else "ok", "flag": "vague" if vague else "none", "by": "file"})
            n += 1
    if added_km:
        _balance(kms)
    for k in kms:
        k.pop("_w", None)
    d["keymen"] = kms or d.get("keymen") or []
    return n


def _balance(kms: list[dict[str, Any]]) -> None:
    """키맨을 더한 뒤 가중치 합 100 — 문서에 비중이 적힌 키맨(_w)은 그대로, 나머지는 남은 몫을 고르게(없으면 모두 고르게)."""
    fixed = [k for k in kms if k.get("_w")]
    rest = [k for k in kms if not k.get("_w")]
    left = 100 - sum(int(k["weight"]) for k in fixed)
    if not rest or left < 0:
        normalize_weights(kms)
        return
    share, extra = divmod(left, len(rest))
    for i, k in enumerate(rest):
        k["weight"] = share + (1 if i < extra else 0)


def normalize_weights(kms: list[dict[str, Any]]) -> bool:
    """합이 100 이 아니면 비율대로 맞춘다(합 0 이면 고르게). 바꿨으면 True."""
    if not kms:
        return False
    tot = sum(int(k.get("weight") or 0) for k in kms)
    if tot == 100:
        return False
    if tot <= 0:
        raw = [100 / len(kms)] * len(kms)
    else:
        raw = [int(k.get("weight") or 0) * 100 / tot for k in kms]
    base = [int(x) for x in raw]
    order = sorted(range(len(kms)), key=lambda i: raw[i] - base[i], reverse=True)
    for i in order[: 100 - sum(base)]:
        base[i] += 1
    for k, w in zip(kms, base, strict=True):
        k["weight"] = w
    return True


async def _fill_merge(state: _FillState) -> dict[str, Any]:
    filled = 0
    srcs = []
    for e in state.get("extractions") or []:
        srcs.append(e)

    def fn(d: dict[str, Any]) -> None:
        nonlocal filled
        filled = 0
        for e in srcs:
            k = merge_extraction(d, e["ex"], e["file"])
            filled += k
            f = e["file"]
            d["sources"] = [s for s in d.get("sources") or [] if s["file_id"] != f["file_id"]] + [
                {"file_id": f["file_id"], "name": f["name"], "pages": f.get("pages"), "filled": k, "read_at": now_iso()}]
        d["fill_job"] = None
    await update(state["rq_flow_id"], fn)
    return {"filled": filled}


def _fill_graph() -> StateGraph:
    g = StateGraph(_FillState)
    g.add_node("read", _fill_read)
    g.add_node("extract", _fill_extract)
    g.add_node("merge", _fill_merge)
    g.add_edge(START, "read")
    g.add_edge("read", "extract")
    g.add_edge("extract", "merge")
    g.add_edge("merge", END)
    return g


async def handle_fill(ctx: JobContext) -> dict[str, Any]:
    fid = ctx.payload["rq_flow_id"]
    try:
        final = await run_graph(ctx, _fill_graph(), {"rq_flow_id": fid, "file_ids": list(ctx.payload.get("file_ids") or [])},
                                step_labels={"read": "파일 읽기", "extract": "값 뽑기", "merge": "폼에 넣기"})
    except BaseException as exc:
        if isinstance(exc, Exception) and await asyncio.to_thread(gone, fid):   # 채우는 사이 초안을 지웠다 — 되살리지 않고 취소로 끝낸다
            log.info("지운 초안의 채우기 잡을 끝냄 %s", fid)
            raise JobCanceled("초안이 지워졌어요") from exc
        await update(fid, lambda d: d.update(fill_job=None))
        raise
    await ctx.progress(100, "완료")
    return {"rq_flow_id": fid, "filled": int((final or {}).get("filled") or 0), "note": (final or {}).get("note")}


# ── 저장 · flow.json ────────────────────────────────────

def stage(d: dict[str, Any]) -> dict[str, Any]:
    """Storyboard flow.json stages.rq(§6) — ref · ver 는 허브가 붙인다. 제작자 의견은 넣지 않는다."""
    kms = [k for k in _kms(d) if k.get("role") or k.get("reqs")]
    reqs = []
    for k in kms:
        for r in k.get("reqs") or []:
            reqs.append({"id": r["id"], "text": r["text"], "status": r.get("status") or "ok", "by": r.get("by") or "manual", "keyman": k.get("role") or ""})
    ranked = sorted(kms, key=lambda k: -int(k.get("weight") or 0))
    goals = [r["text"] for k in ranked for r in k.get("reqs") or [] if r.get("status") != "check"][:3]
    c = counts(d)
    return {"customer": d.get("customer") or "", "title": d.get("title") or "", "target": d.get("target") or "",
            "targetBy": d.get("target_by"),
            "keymen": [{"role": k.get("role") or "", "weight": int(k.get("weight") or 0), "needs": [r["text"] for r in k.get("reqs") or []]} for k in kms],
            "goals": goals, "requirements": reqs, "counts": {"keymen": c["keymen"], "reqs": c["reqs"], "check": c["check"]},
            "sources": [{"file": s["name"], "pages": s.get("pages")} for s in d.get("sources") or []]}


def summary_md(d: dict[str, Any], st: dict[str, Any] | None = None) -> str:
    """요약본 절 본문(`- …`) — 머리(## n. 고객 요구사항 · RQ-NN vN)는 허브가 붙인다."""
    st = st or stage(d)
    lines = []
    if not st["target"]:
        lines.append("- 최종 제안대상 [확인 필요]")
    by_role: dict[str, list[dict[str, Any]]] = {}
    for r in st["requirements"]:
        by_role.setdefault(r["keyman"], []).append(r)
    for k in st["keymen"]:
        rs = by_role.get(k["role"], [])
        body = " · ".join(r["text"] + (" [확인 필요]" if r["status"] == "check" else "") for r in rs) or "요구 [확인 필요]"
        lines.append(f"- {k['role'] or '키맨'}({k['weight']}%): {body}")
    if not st["keymen"]:
        lines.append("- 키맨 · 요구 [확인 필요]")
    return "\n".join(lines)


def card(d: dict[str, Any], st: dict[str, Any]) -> dict[str, Any]:
    """연결된 콘텐츠 보기 팝업(ContentPopup) 값 — 보드 RQ-01 예시 모양."""
    c = st["counts"]
    by_role: dict[str, list[dict[str, Any]]] = {}
    for r in st["requirements"]:
        by_role.setdefault(r["keyman"], []).append(r)
    groups = [{"h": k["role"] or "키맨", "sub": f"{k['weight']}%",
               "lines": [{"t": r["text"], "note": "확인 필요" if r["status"] == "check" else None} for r in by_role.get(k["role"], [])]}
              for k in st["keymen"]]
    return {"title": d.get("title") or display_title(d),
            "facts": [["고객사", st["customer"] or "[확인 필요]"], ["최종 제안대상", st["target"] or "[확인 필요]"],
                      ["요구", f"{c['reqs']}" + (f" · 확인 필요 {c['check']}" if c["check"] else "")]],
            "groups": groups, "foot": "제작자 의견은 고객 문서에서 빠져요",
            "line": f"{d['code']} v{d.get('ver') or 1} · 키맨 {c['keymen']} · 요구 {c['reqs']}" + (f" · 확인 필요 {c['check']}" if c["check"] else "")}


async def finish(fid: str) -> dict[str, Any]:
    d = await load(fid)
    if d.get("fill_job"):
        raise ApiError(409, "FILLING", "파일에서 폼을 채우는 중이에요. 끝난 뒤 저장해 주세요.", {"job_id": d["fill_job"]})
    if not (d.get("title") or "").strip() and not (d.get("customer") or "").strip() and not counts(d)["reqs"]:
        raise ApiError(422, "EMPTY_FORM", "프로젝트명 · 고객사 · 요구사항 중 하나는 적어 주세요.")

    def fn(doc: dict[str, Any]) -> None:
        normalize_weights(_kms(doc))
        doc["ver"] = int(doc.get("ver") or 0) + 1
        doc["status"] = "done"
        doc["saved_at"] = now_iso()
    saved = await update(d["id"], fn)
    st = stage(saved)
    md = summary_md(saved, st)
    title = display_title(saved)
    payload = {"ref": saved["code"], "ver": int(saved["ver"]), "res_id": saved["id"], "title": title, "value": st, "md": md, "card": card(saved, st)}
    created = False
    sync = None
    sb_id = (saved.get("sb_ids") or [None])[0]
    name = None
    if sb_id:
        out = await push_stage(sb_id, "rq", ref=payload["ref"], ver=payload["ver"], res_id=payload["res_id"], title=title, value=st, md=md, card=payload["card"])
        if out:
            sync = {"md_added": out.get("md_added") or "", "synced": out.get("synced") or []}
            name = (out.get("flow") or {}).get("name")
    else:
        flow = await create_flow(sb_name(saved), customer=saved.get("customer") or None, target=saved.get("target") or None, rq=payload)
        if flow:
            created = True
            sb_id, name = flow["id"], flow.get("name")
            hist = flow.get("history") or []
            sync = {"md_added": (hist[-1].get("md") if hist else "") or f"## 고객 요구사항 · {payload['ref']} v{payload['ver']}\n{md}", "synced": []}

            def keep(doc: dict[str, Any]) -> None:
                doc["sb_ids"] = list(dict.fromkeys([*(doc.get("sb_ids") or []), flow["id"]]))
            saved = await update(saved["id"], keep)
    await _index(saved)
    return {"stage": st, "summary_md": md, "flow_sync": sync, "sb_id": sb_id, "sb_name": name, "created": created, "doc": to_api(saved)}
