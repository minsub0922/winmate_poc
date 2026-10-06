"""공간 입력 파이프라인(08-birdseye §4.2~§4.4 · §6.2 · §7.3~§7.5).

- 첨부 분류(R1): PDF → 도면, 이미지 → i2t 「평면도인가?」(be.classify_image · 기밀) — 막히거나 실패하면 로컬 판정(흰 바탕 + 선).
- 도면 인식 `be.plan_recognize`: 벡터 PDF(결정적) + i2t 보강 · 래스터(외곽 + i2t 박스) → 공간 모델 · 되묻기 · 치수 보정.
  기밀 차단 → 벡터/영상 처리만 + 「고객 도면이라 외부 모델 없이 기본 인식만 했어요」. bbox 미지원 → 「도면 모양을 사각형으로 단순화했어요 · 말로 고쳐 주세요」.
- 현장 사진 `be.photo_recognize`: 품질 검사(로컬) → i2t(벽 이름 · 요소 · 크기 힌트 · 추정) → 종합(be.photo_aggregate) → 사각형 모델(추정).
- QR 업로드 토큰(30분) · 사진에 없는 정보(be.photo_facts + 정규식).
- 공간 분석 `be.space_analyze`: 설명 해석(be.space_parse → 정규식) → 병합(도면 > 사진 > 설명, 사용자 칸 값 우선) → 기본값 →
  KB C1 역량 힌트 → 공간 모델 저장(판 기록).
"""
from __future__ import annotations

import asyncio
import base64
import copy
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import current_job, jobs
from winmate_common.platform import file_bytes, file_meta

from . import config, kbapi, llm
from . import photos as PH
from . import plans as PL
from . import service as svc
from . import space as S
from . import text as T
from .repo import repo

log = logging.getLogger("winmate.birdseye.inputs")

NOTICE_CONFIDENTIAL = "고객 도면이라 외부 모델 없이 기본 인식만 했어요"
NOTICE_SIMPLIFIED = "도면 모양을 사각형으로 단순화했어요 · 말로 고쳐 주세요"
NOTICE_MODEL_DOWN = "도면 해석 모델이 응답하지 않아 기본 인식만 했어요"
MSG_PHOTO_TYPES = "JPG · PNG · HEIC만 올릴 수 있어요"
MSG_PLAN_TYPES = "PDF · PNG · JPG · HEIC만 올릴 수 있어요"
W_ANALYZING = "공간을 파악하고 있어요"


# ── 파일 ─────────────────────────────────────────────────

async def _meta(file_id: str) -> dict[str, Any]:
    try:
        return await file_meta(file_id)
    except ApiError as exc:
        if exc.status == 404:
            raise ApiError(404, "NOT_FOUND", "파일을 찾을 수 없어요", {"file_id": file_id}) from exc
        raise


def _is_pdf(meta: dict[str, Any]) -> bool:
    return meta.get("kind") == "pdf" or meta.get("mime") == "application/pdf"


def _is_image(meta: dict[str, Any]) -> bool:
    """사진 · 래스터 도면으로 받는 그림(JPG · PNG · HEIC — files 가 HEIC 를 JPG 로 바꾼다)."""
    mime = str(meta.get("mime") or "").lower()
    up = config.rules()["upload"]
    ok = set(up["photo_mimes"]) | {m for m in up["plan_mimes"] if m.startswith("image/")}
    return mime in ok


def _check_size(meta: dict[str, Any]) -> None:
    max_mb = float(config.rules()["upload"]["max_mb"])
    if int(meta.get("size") or 0) > max_mb * 1024 * 1024:
        raise ApiError(413, "FILE_TOO_LARGE", f"파일은 {T.num(max_mb)}MB까지 올릴 수 있어요", {"file_id": meta.get("id")})


async def _progress(pct: float, message: str, **data: Any) -> None:
    ctx = current_job()
    if ctx is not None:
        await ctx.progress(pct, message, **data)


async def _page_png(file_id: str, page: int) -> bytes | None:
    """PDF 쪽 그림 — files(쪽 그림) → 안 되면 로컬(pypdfium2)."""
    try:
        data, _mime = await ServiceClient("files", timeout=60).get_bytes(f"/v1/files/{file_id}/pages/{page}/image")
        if data:
            return data
    except Exception as exc:  # noqa: BLE001
        log.info("files 쪽 그림 실패 → 로컬 렌더: %s", exc)
    try:
        pdf, _ = await file_bytes(file_id)
        return await asyncio.to_thread(_render_pdf_page, pdf, page)
    except Exception as exc:  # noqa: BLE001
        log.warning("PDF 쪽 렌더 실패: %s", exc)
        return None


def _render_pdf_page(pdf: bytes, page: int) -> bytes:
    import io

    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(pdf)
    try:
        idx = min(max(page - 1, 0), len(doc) - 1)
        pg = doc[idx]
        w, h = pg.get_size()
        scale = 1600 / max(w, h)
        img = pg.render(scale=scale).to_pil()
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "PNG")
        return buf.getvalue()
    finally:
        doc.close()


def _pdf_pages(pdf: bytes) -> int:
    import io

    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf)) as p:
        return len(p.pages)


def _b64img(png: bytes) -> dict[str, Any]:
    return {"data_b64": base64.b64encode(png).decode(), "mime": "image/png"}


async def _caps_i2t() -> dict[str, Any]:
    caps = await llm.caps()
    return caps.get("i2t") or {}


# ── 첨부 분류(R1) ────────────────────────────────────────

async def classify_image(meta: dict[str, Any]) -> tuple[bool, str]:
    """(평면도인가, 경로) — i2t(기밀) → 막히거나 실패하면 로컬 판정."""
    prompt = ("이 그림이 건물 배치를 위에서 내려다본 설계 그림(벽 · 문 · 창 기호)인지, 현장에서 찍은 사진인지 판정해 JSON 으로.\n"
              f"파일 이름: {meta.get('name') or ''}")
    try:
        res = await llm.vision_task("be.classify_image", [meta["id"]], prompt, PL.ImageKind, confidential=True, timeout=30)
    except llm.ModelBlocked:
        res = None
    js = (res or {}).get("json")
    if isinstance(js, dict) and "is_floor_plan" in js:
        return bool(js["is_floor_plan"]), "classify:i2t"
    try:
        data, _ = await file_bytes(meta["id"])
    except Exception:  # noqa: BLE001
        return False, "classify:local"
    return await asyncio.to_thread(PL.looks_like_plan, data), "classify:local"


async def attach(be_id: str, file_ids: list[str]) -> dict[str, Any]:
    """BE1 파일 첨부 → 도면(BE1D) · 현장 사진(BE1P). 섞이면 BE1D 먼저."""
    b = await svc.get(be_id)
    metas = []
    for fid in file_ids:
        m = await _meta(fid)
        if not (_is_pdf(m) or _is_image(m)):
            raise ApiError(415, "FILE_TYPE_UNSUPPORTED", MSG_PLAN_TYPES, {"file_id": fid, "mime": m.get("mime")})
        _check_size(m)
        metas.append(m)
    kinds: list[tuple[dict[str, Any], str]] = []
    for m in metas:
        if _is_pdf(m):
            kinds.append((m, "plan"))
        else:
            is_plan, _path = await classify_image(m)
            kinds.append((m, "plan" if is_plan else "photo"))
    items = []
    for m, kind in kinds:
        if kind == "plan":
            acc = await add_plan(be_id, m["id"], 1, meta=m)
            items.append({"file_id": m["id"], "name": m.get("name") or "", "kind": "plan", "plan_id": acc["plan_id"], "photo_id": None,
                          "job_id": acc["job_id"]})
        else:
            acc = await add_photo(be_id, m["id"], meta=m)
            items.append({"file_id": m["id"], "name": m.get("name") or "", "kind": "photo", "plan_id": None, "photo_id": acc["photo_id"],
                          "job_id": acc["job_id"]})
    plan_ids = [i["plan_id"] for i in items if i["kind"] == "plan"]
    if plan_ids:
        route = f"/birdseye/{be_id}/space/plan?plan={plan_ids[0]}"
    elif any(i["kind"] == "photo" for i in items):
        route = f"/birdseye/{be_id}/space/photos"
    else:
        route = f"/birdseye/{be_id}/space"
    _ = b
    return {"items": items, "route": route}


# ── 도면 ─────────────────────────────────────────────────

async def add_plan(be_id: str, file_id: str, page: int = 1, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    b = await svc.get(be_id)
    m = meta or await _meta(file_id)
    if not (_is_pdf(m) or _is_image(m)):
        raise ApiError(415, "FILE_TYPE_UNSUPPORTED", MSG_PLAN_TYPES, {"file_id": file_id, "mime": m.get("mime")})
    _check_size(m)
    pid = new_id("bep")
    job_id = new_id("job")
    doc = {
        "birdseye_id": be_id, "file_id": file_id, "file_name": m.get("name") or "", "size": m.get("size"), "mime": m.get("mime"),
        "page": max(1, int(page or 1)), "pages": int(m.get("pages") or 1), "kind": None, "status": "recognizing",
        "stage_label": "도면을 읽고 있어요", "job_id": job_id, "raw": None, "i2t": None, "doors": [], "dim_choices": {},
        "answers": {}, "edits": [], "model": None, "notices": [], "meta_paths": [], "error": None, "finalized": False,
        "page_box": None, "i2t_windows": [],
    }
    await repo().put("plans", pid, doc)

    def fn(d: dict[str, Any]) -> None:
        inputs = dict(d.get("inputs") or {})
        ids = list(inputs.get("plan_file_ids") or [])
        if file_id not in ids:
            ids.append(file_id)
        inputs["plan_file_ids"] = ids
        d["inputs"] = inputs

    await repo().mutate("birdseyes", be_id, fn)
    await jobs().enqueue("birdseye", "plan_recognize", {"plan_id": pid, "birdseye_id": be_id}, title=f"{b['title']} · 도면 인식",
                         ref=be_id, project_id=b.get("project_id"), owner=b["owner"], owner_name=b.get("owner_name") or "", job_id=job_id)
    await svc.index(be_id)
    return {"job_id": job_id, "plan_id": pid}


async def _plan(be_id: str, pid: str) -> dict[str, Any]:
    p = await repo().get("plans", pid)
    if p is None or p.get("birdseye_id") != be_id:
        raise not_found("도면", pid)
    return p


async def recognize_again(be_id: str, pid: str, page: int | None = None) -> dict[str, Any]:
    """「다시 인식」(같은 파일 재처리) · 쪽 바꾸기."""
    b = await svc.get(be_id)
    p = await _plan(be_id, pid)
    job_id = new_id("job")
    await repo().patch("plans", pid, {"status": "recognizing", "stage_label": "도면을 읽고 있어요", "job_id": job_id, "error": None,
                                      "page": max(1, int(page or p.get("page") or 1)), "raw": None, "model": None, "notices": [],
                                      "meta_paths": [], "doors": [], "dim_choices": {} if page and page != p.get("page") else p.get("dim_choices", {}),
                                      "answers": {} if page and page != p.get("page") else p.get("answers", {}),
                                      "edits": [] if page and page != p.get("page") else p.get("edits", []), "finalized": False})
    await jobs().enqueue("birdseye", "plan_recognize", {"plan_id": pid, "birdseye_id": be_id}, title=f"{b['title']} · 도면 다시 인식",
                         ref=be_id, project_id=b.get("project_id"), owner=b["owner"], owner_name=b.get("owner_name") or "", job_id=job_id)
    await svc.index(be_id)
    return {"job_id": job_id, "plan_id": pid}


class PlanState(TypedDict, total=False):
    plan_id: str
    birdseye_id: str
    kind: str
    raw: dict[str, Any] | None
    i2t: dict[str, Any] | None
    i2t_ok: bool
    bbox: bool
    notices: list[str]
    meta_paths: list[str]


async def _pn_fetch(state: PlanState) -> dict[str, Any]:
    p = await repo().get("plans", state["plan_id"])
    if p is None:
        raise ApiError(404, "NOT_FOUND", "도면을 찾을 수 없어요")
    await _progress(10, "도면 불러오는 중")
    data, mime = await file_bytes(p["file_id"])
    raw = None
    kind = "raster"
    pages = int(p.get("pages") or 1)
    if mime == "application/pdf" or data[:5] == b"%PDF-":
        try:
            pages = await asyncio.to_thread(_pdf_pages, data)
        except Exception:  # noqa: BLE001
            pages = int(p.get("pages") or 1)
        try:
            raw = await asyncio.to_thread(PL.analyze_vector, data, int(p.get("page") or 1))
        except Exception as exc:  # noqa: BLE001
            log.warning("벡터 인식 실패 → 래스터: %s", exc)
            raw = None
        if raw is not None:
            kind = "vector_pdf"
    await repo().patch("plans", p["id"], {"kind": kind, "pages": pages, "stage_label": "벽 · 창 · 문 찾는 중"})
    return {"kind": kind, "raw": raw, "notices": [], "meta_paths": []}


async def _plan_image(p: dict[str, Any], kind: str) -> dict[str, Any] | str | None:
    if kind == "vector_pdf" or str(p.get("mime") or "") == "application/pdf":
        png = await _page_png(p["file_id"], int(p.get("page") or 1))
        return _b64img(png) if png else None
    return p["file_id"]


async def _pn_i2t(state: PlanState) -> dict[str, Any]:
    p = await repo().get("plans", state["plan_id"]) or {}
    await _progress(35, "도면 요소 읽는 중")
    kind = state.get("kind") or "raster"
    i2t_caps = await _caps_i2t()
    sup = i2t_caps.get("supports") or {}
    bbox = bool(sup.get("bbox", True)) and kind == "raster"
    notices = list(state.get("notices") or [])
    meta_paths = list(state.get("meta_paths") or [])
    img = await _plan_image(p, kind)
    res = None
    ok = False
    if img is not None:
        try:
            res = await llm.vision_task("be.plan_analyze", [img], PL.PLAN_PROMPT.format(mode="벡터 PDF" if kind == "vector_pdf" else "그림"),
                                        PL.PlanI2T, want_bbox=bbox, confidential=True)
            ok = res is not None and isinstance(res.get("json"), dict)
            if not ok:
                notices.append(NOTICE_MODEL_DOWN)
        except llm.ModelBlocked:
            notices.append(NOTICE_CONFIDENTIAL)
            res = None
    if not ok:
        meta_paths.append("plan:vector_only" if kind == "vector_pdf" else "plan:raster_cv")
    return {"i2t": res if ok else None, "i2t_ok": ok, "bbox": bbox, "notices": notices, "meta_paths": meta_paths}


async def _pn_geometry(state: PlanState) -> dict[str, Any]:
    p = await repo().get("plans", state["plan_id"]) or {}
    b = await svc.get(state["birdseye_id"])
    await _progress(60, "치수 확인 중")
    raw = state.get("raw")
    notices = list(state.get("notices") or [])
    meta_paths = list(state.get("meta_paths") or [])
    if raw is None:
        if str(p.get("mime") or "") == "application/pdf":
            img = await _page_png(p["file_id"], int(p.get("page") or 1))
        else:
            img, _ = await file_bytes(p["file_id"])
        if not img:
            raise ApiError(422, "PLAN_UNREADABLE", "도면을 읽지 못했어요. 다른 도면을 올리거나 다시 인식해 주세요.")
        area_m2 = T.pyeong_to_m2(b["area_input_pyeong"]) if b.get("area_input_pyeong") else None
        if area_m2 is None:
            for r in S.regex_parse(b.get("description") or ""):
                if r.get("area_pyeong"):
                    area_m2 = T.pyeong_to_m2(r["area_pyeong"])
                    break
        i2t = state.get("i2t")
        bbox_supported = bool(state.get("bbox")) and bool((i2t or {}).get("boxes"))
        raw = await asyncio.to_thread(PL.analyze_raster, img, i2t, bbox_supported=bbox_supported, description_area_m2=area_m2)
        if raw.get("simplified"):
            if NOTICE_SIMPLIFIED not in notices:
                notices.append(NOTICE_SIMPLIFIED)
            if state.get("i2t_ok"):
                meta_paths.append("plan:raster_nobbox")
    return {"raw": raw, "notices": notices, "meta_paths": meta_paths}


async def _pn_model(state: PlanState) -> dict[str, Any]:
    p = await repo().get("plans", state["plan_id"]) or {}
    b = await svc.get(state["birdseye_id"])
    await _progress(85, "인식 결과 정리 중")
    raw = state["raw"] or {}
    js = (state.get("i2t") or {}).get("json") or {}
    doors = PL.door_types(raw, js, i2t_ok=bool(state.get("i2t_ok")))
    parsed = S.regex_parse(b.get("description") or "")
    ceiling = b.get("ceiling_input_m") or next((r.get("ceiling_m") for r in parsed if r.get("ceiling_m")), None)
    info = config.chip_info(b.get("space_chip"))
    plan_state = {
        "dim_choices": p.get("dim_choices") or {}, "doors": doors, "answers": p.get("answers") or {}, "edits": p.get("edits") or [],
        "i2t_windows": js.get("windows") or [], "ceiling_m": ceiling, "room_label": parsed[0]["label"] if parsed else info["space_label"],
        "space_types": list(info["space_types"]), "meta_paths": state.get("meta_paths") or [],
    }
    model = PL.model_from_raw(raw, plan_state)
    await repo().patch("plans", p["id"], {
        "status": "recognized", "stage_label": "", "raw": raw, "i2t": js or None, "doors": doors, "model": model,
        "notices": state.get("notices") or [], "meta_paths": state.get("meta_paths") or [], "page_box": raw.get("page_box"),
        "i2t_windows": js.get("windows") or [], "ceiling_m": ceiling, "room_label": plan_state["room_label"],
        "space_types": plan_state["space_types"], "error": None,
    })
    await svc.index(b["id"])
    return {}


def plan_graph() -> StateGraph:
    g = StateGraph(PlanState)
    for name, fn in (("fetch", _pn_fetch), ("i2t", _pn_i2t), ("geometry", _pn_geometry), ("model", _pn_model)):
        g.add_node(name, fn)
    g.add_edge(START, "fetch")
    g.add_edge("fetch", "i2t")
    g.add_edge("i2t", "geometry")
    g.add_edge("geometry", "model")
    g.add_edge("model", END)
    return g


async def plan_failed(plan_id: str, message: str) -> None:
    p = await repo().get("plans", plan_id)
    if p is None:
        return
    await repo().patch("plans", plan_id, {"status": "failed", "stage_label": "", "error": message})
    await svc.index(p["birdseye_id"])


def _plan_state_of(p: dict[str, Any]) -> dict[str, Any]:
    return {"dim_choices": p.get("dim_choices") or {}, "doors": p.get("doors") or [], "answers": p.get("answers") or {},
            "edits": p.get("edits") or [], "i2t_windows": p.get("i2t_windows") or [], "ceiling_m": p.get("ceiling_m"),
            "room_label": p.get("room_label"), "space_types": p.get("space_types") or [], "meta_paths": p.get("meta_paths") or []}


async def rebuild_plan(p: dict[str, Any], **changes: Any) -> dict[str, Any]:
    """답 · 치수 선택 · 말로 고치기 → 모델 다시 계산(결정적)."""
    p = {**p, **changes}
    if not p.get("raw"):
        raise ApiError(409, "PLAN_NOT_READY", "도면 인식이 아직 끝나지 않았어요")
    model = PL.model_from_raw(p["raw"], _plan_state_of(p))
    await repo().patch("plans", p["id"], {**changes, "model": model})
    if p.get("finalized"):
        await refresh_space(p["birdseye_id"])
    await svc.index(p["birdseye_id"])
    return model


def plan_view(p: dict[str, Any]) -> dict[str, Any]:
    model = p.get("model")
    questions = (model or {}).get("questions") or []
    elements = PL.element_rows(model, questions) if model else []
    open_q = [q for q in questions if not q.get("answered")]
    status = p.get("status") or "recognizing"
    is_pdf = str(p.get("mime") or "") == "application/pdf" or p.get("kind") == "vector_pdf"
    page = int(p.get("page") or 1)
    return {
        "id": p["id"], "birdseye_id": p["birdseye_id"], "file_id": p["file_id"], "file_name": p.get("file_name") or "",
        "file_meta": PL.file_meta_label(page, p.get("size")), "page": page, "pages": int(p.get("pages") or 1), "kind": p.get("kind"),
        "status": status, "stage_label": p.get("stage_label") or "", "job_id": p.get("job_id"),
        "scale_label": PL.scale_label(model) if model else "", "area_m2": float((model or {}).get("area_m2") or 0),
        "elements": elements, "head": f"{len(elements)}종 · 확인 {len(open_q)}" if model else "", "questions": questions,
        "check_count": len(open_q), "w_message": PL.w_message(questions, status), "notices": p.get("notices") or [],
        "meta_paths": p.get("meta_paths") or [],
        "page_image_url": (f"/api/files/v1/files/{p['file_id']}/pages/{page}/image" if is_pdf else f"/api/files/v1/files/{p['file_id']}/content"),
        "page_box": p.get("page_box"), "error": p.get("error"), "model": model,
    }


async def list_plans(be_id: str) -> list[dict[str, Any]]:
    await svc.get(be_id)
    ps = await repo().all("plans", where={"birdseye_id": be_id}, order_by="created_at")
    return [plan_view(p) for p in sorted(ps, key=lambda x: x["created_at"])]


async def get_plan(be_id: str, pid: str) -> dict[str, Any]:
    return plan_view(await _plan(be_id, pid))


async def _active_plan(be_id: str) -> dict[str, Any] | None:
    ps = await repo().all("plans", where={"birdseye_id": be_id}, order_by="created_at")
    ps = [p for p in ps if p.get("status") == "recognized" and p.get("model")]
    if not ps:
        return None
    return sorted(ps, key=lambda x: x["created_at"])[-1]


async def answer(be_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """되묻기 답(문 종류) · 치수 선택 → SpaceModel."""
    await svc.get(be_id)
    plan_id = body.get("plan_id")
    p = await _plan(be_id, plan_id) if plan_id else await _active_plan(be_id)
    if p is None:
        raise ApiError(409, "PLAN_NOT_READY", "확인할 도면이 없어요")
    if body.get("question_id"):
        qid = body["question_id"]
        opt = body.get("option")
        if opt not in ("emergency", "backoffice", "wall", "main", "normal"):
            raise ApiError(400, "INVALID_ARGUMENT", "답을 골라 주세요", {"field": "option"})
        qs = {q["id"] for q in ((p.get("model") or {}).get("questions") or [])}
        if qid not in qs and qid not in (p.get("answers") or {}):
            raise not_found("되묻기", qid)
        answers = dict(p.get("answers") or {})
        answers[qid] = opt
        model = await rebuild_plan(p, answers=answers)
    elif body.get("dim_id"):
        did = body["dim_id"]
        choice = body.get("choice") or "annotated"
        if choice == "manual" and not body.get("manual_m"):
            raise ApiError(400, "INVALID_ARGUMENT", "치수를 m 로 적어 주세요", {"field": "manual_m"})
        dims = {d["id"] for d in ((p.get("model") or {}).get("dims") or [])}
        if did not in dims:
            raise not_found("치수", did)
        choices = dict(p.get("dim_choices") or {})
        choices[did] = {"choice": choice, "manual_m": body.get("manual_m") if choice == "manual" else None}
        model = await rebuild_plan(p, dim_choices=choices)
    else:
        raise ApiError(400, "INVALID_ARGUMENT", "question_id 또는 dim_id 가 필요해요")
    return model


# ── 말로 고치기(공간 모델 연산) ──────────────────────────

def _model_brief(model: dict[str, Any]) -> str:
    walls = "; ".join(f"{w['id']}={w.get('label') or '벽'}" for w in model.get("walls", []))
    ops = "; ".join(f"{o['id']}={o.get('label') or o['kind']}({o['kind']}, 벽 {o['wall_id']})" for o in model.get("openings", []))
    cols = "; ".join(f"{c['id']}=({c['center'][0]}, {c['center'][1]})" for c in model.get("columns", []))
    minx, miny, maxx, maxy = S.bbox_of(model)
    return (f"평면 x {minx}~{maxx} m(오른쪽이 큼), y {miny}~{maxy} m(아래가 큼, 위 = 정면)\n벽: {walls}\n개구부: {ops or '없음'}\n기둥: {cols or '없음'}")


async def space_nl_edit(be_id: str, text: str) -> dict[str, Any]:
    """BE1D 「말로 고치기」 → 공간 모델 연산(LLM · 기밀) → 막히면 정규식."""
    p = await _active_plan(be_id)
    model = (p or {}).get("model") or await svc.space_model(be_id)
    if model is None:
        raise ApiError(409, "SPACE_NOT_READY", "고칠 공간 모델이 아직 없어요")
    prompt = (f"{_model_brief(model)}\n요청: {text}\n요청을 공간 모델 연산으로 바꾼다. op 는 remove(target) · add_column(value 'x,y') · "
              "set_door(target, value emergency|backoffice|normal|main) · set_window_full(target 벽 id) 중 하나.")
    path = "space_ops:llm"
    try:
        res = await llm.json_task("be.space_ops", prompt, PL.SpaceOps, confidential=True)
    except llm.ModelBlocked:
        res = None
    ops = [o for o in ((res or {}).get("ops") or []) if o.get("op")]
    valid_ids = {c["id"] for c in model.get("columns", [])} | {o["id"] for o in model.get("openings", [])} | \
        {k["id"] for k in model.get("cores", [])} | {w["id"] for w in model.get("walls", [])}
    ops = [o for o in ops if o.get("op") == "add_column" or (o.get("target") in valid_ids)]
    if not ops:
        ops = PL.regex_space_ops(text, model)
        path = "space_ops:regex"
    if not ops:
        return {"ops": [], "path": path, "applied": 0}
    if p is not None:
        await rebuild_plan(p, edits=list(p.get("edits") or []) + ops)
    else:
        m = copy.deepcopy(model)
        for op in ops:
            PL.apply_space_op(m, op)
        S.recompute_area(m)
        m["features"] = _merge_features(S.features_from_model(m), m.get("features") or [])
        await save_space(be_id, m)
    return {"ops": ops, "path": path, "applied": len(ops)}


def _merge_features(base: list[dict[str, Any]], prev: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kinds = {f["kind"] for f in base}
    out = list(base)
    for f in prev:
        if f["kind"] not in kinds and f["kind"] not in ("columns", "storefront_window", "window"):
            out.append(f)
            kinds.add(f["kind"])
    prev_by = {f["kind"]: f for f in prev}
    for f in out:
        old = prev_by.get(f["kind"])
        if old and old.get("hint_cap") and not f.get("hint_cap"):
            f["hint_cap"] = old["hint_cap"]
            f["cap_label"] = old.get("cap_label")
    return out


# ── 현장 사진 ────────────────────────────────────────────

async def _photos(be_id: str) -> list[dict[str, Any]]:
    ps = await repo().all("photos", where={"birdseye_id": be_id}, order_by="created_at")
    return sorted(ps, key=lambda p: (int(p.get("n") or 0), p["created_at"]))


async def add_photo(be_id: str, file_id: str, *, replace_photo_id: str | None = None, is_ceiling: bool = False,
                    meta: dict[str, Any] | None = None, owner: tuple[str, str] | None = None) -> dict[str, Any]:
    b = await svc.get(be_id)
    m = meta or await _meta(file_id)
    if not _is_image(m):
        raise ApiError(415, "FILE_TYPE_UNSUPPORTED", MSG_PHOTO_TYPES, {"file_id": file_id, "mime": m.get("mime")})
    _check_size(m)
    existing = await _photos(be_id)
    n = None
    if replace_photo_id:
        old = next((p for p in existing if p["id"] == replace_photo_id), None)
        if old is None:
            raise not_found("사진", replace_photo_id)
        n = old["n"]
        is_ceiling = bool(old.get("is_ceiling")) or is_ceiling
        await repo().delete("photos", replace_photo_id)
        existing = [p for p in existing if p["id"] != replace_photo_id]
    max_photos = int(config.rules()["upload"]["max_photos"])
    if n is None and len(existing) >= max_photos:
        raise ApiError(409, "TOO_MANY_PHOTOS", f"사진은 {max_photos}장까지 올릴 수 있어요")
    if n is None:
        n = max([int(p.get("n") or 0) for p in existing] + [0]) + 1
    phid = new_id("beh")
    job_id = new_id("job")
    await repo().put("photos", phid, {
        "birdseye_id": be_id, "file_id": file_id, "n": n, "wall_label": None, "dir_slot": "ceiling" if is_ceiling else None,
        "status": "recognizing", "stage_label": PH.STAGES[0], "quality": {}, "quality_status": None, "i2t": None, "found": [],
        "is_ceiling": is_ceiling, "ceiling_h_m": None, "job_id": job_id, "meta_path": None,
    })
    count = len(existing) + 1

    def fn(d: dict[str, Any]) -> None:
        inputs = dict(d.get("inputs") or {})
        inputs["photo_count"] = count
        d["inputs"] = inputs

    await repo().mutate("birdseyes", be_id, fn)
    own, own_name = owner or (b["owner"], b.get("owner_name") or "")
    await jobs().enqueue("birdseye", "photo_recognize", {"photo_id": phid, "birdseye_id": be_id}, title=f"{b['title']} · 사진 {n} 인식",
                         ref=be_id, project_id=b.get("project_id"), owner=own, owner_name=own_name, job_id=job_id)
    await svc.index(be_id)
    return {"job_id": job_id, "photo_id": phid}


async def recognize_photo_again(be_id: str, phid: str) -> dict[str, Any]:
    b = await svc.get(be_id)
    p = await repo().get("photos", phid)
    if p is None or p.get("birdseye_id") != be_id:
        raise not_found("사진", phid)
    job_id = new_id("job")
    await repo().patch("photos", phid, {"status": "recognizing", "stage_label": PH.STAGES[0], "job_id": job_id})
    await jobs().enqueue("birdseye", "photo_recognize", {"photo_id": phid, "birdseye_id": be_id}, title=f"{b['title']} · 사진 {p['n']} 다시 인식",
                         ref=be_id, project_id=b.get("project_id"), owner=b["owner"], owner_name=b.get("owner_name") or "", job_id=job_id)
    return {"job_id": job_id, "photo_id": phid}


class PhotoState(TypedDict, total=False):
    photo_id: str
    birdseye_id: str
    quality: dict[str, float]
    quality_status: str | None
    i2t: dict[str, Any] | None
    path: str


async def _ph_quality(state: PhotoState) -> dict[str, Any]:
    p = await repo().get("photos", state["photo_id"])
    if p is None:
        raise ApiError(404, "NOT_FOUND", "사진을 찾을 수 없어요")
    await _progress(15, PH.STAGES[0])
    data, _ = await file_bytes(p["file_id"])
    try:
        q = await asyncio.to_thread(PH.quality, data)
    except Exception as exc:  # noqa: BLE001
        raise ApiError(422, "PHOTO_UNREADABLE", "사진을 읽지 못했어요") from exc
    qs = PH.judge(q)
    await repo().patch("photos", p["id"], {"quality": q, "quality_status": qs, "stage_label": PH.STAGES[1]})
    return {"quality": q, "quality_status": qs}


async def _ph_i2t(state: PhotoState) -> dict[str, Any]:
    p = await repo().get("photos", state["photo_id"]) or {}
    b = await svc.get(state["birdseye_id"])
    await _progress(45, PH.STAGES[1])
    sup = (await _caps_i2t()).get("supports") or {}
    try:
        res = await llm.vision_task("be.photo_analyze", [p["file_id"]], PH.photo_prompt(int(p.get("n") or 1), b.get("description") or ""),
                                    PH.PhotoI2T, want_bbox=bool(sup.get("bbox", False)), confidential=True)
    except llm.ModelBlocked:
        return {"i2t": None, "path": "photo:quality_only"}
    if res is None or not isinstance(res.get("json"), dict):
        return {"i2t": None, "path": "photo:failed"}
    await repo().patch("photos", p["id"], {"stage_label": PH.STAGES[2]})
    return {"i2t": res["json"], "path": "photo:i2t"}


async def _ph_save(state: PhotoState) -> dict[str, Any]:
    p = await repo().get("photos", state["photo_id"]) or {}
    await _progress(80, PH.STAGES[2])
    js = state.get("i2t") or {}
    path = state.get("path") or "photo:i2t"
    qs = state.get("quality_status")
    if path == "photo:failed":
        status = "failed"
    elif qs:
        status = qs
    else:
        status = "recognized"
    is_ceiling = bool(p.get("is_ceiling")) or bool(js.get("is_ceiling"))
    est = js.get("est") or {}
    slot = p.get("dir_slot")
    if is_ceiling:
        slot = "ceiling"
    elif js.get("dir_slot"):
        slot = str(int(js["dir_slot"]))
    await repo().patch("photos", p["id"], {
        "status": status, "stage_label": None, "i2t": js or None, "found": PH.found_label(js) if js else [],
        "wall_label": (js.get("wall_label") or None) if not is_ceiling else "천장", "dir_slot": slot, "is_ceiling": is_ceiling,
        "ceiling_h_m": est.get("ceiling_h_m") if is_ceiling else None, "meta_path": path,
    })
    if status != "failed":
        await aggregate(state["birdseye_id"])
    await svc.index(state["birdseye_id"])
    return {}


def photo_graph() -> StateGraph:
    g = StateGraph(PhotoState)
    for name, fn in (("quality", _ph_quality), ("i2t", _ph_i2t), ("save", _ph_save)):
        g.add_node(name, fn)
    g.add_edge(START, "quality")
    g.add_edge("quality", "i2t")
    g.add_edge("i2t", "save")
    g.add_edge("save", END)
    return g


async def photo_failed(photo_id: str, message: str) -> None:
    p = await repo().get("photos", photo_id)
    if p is None:
        return
    await repo().patch("photos", photo_id, {"status": "failed", "stage_label": None, "error": message})
    await svc.index(p["birdseye_id"])


def _usable(p: dict[str, Any]) -> bool:
    return p.get("status") in ("recognized", "accepted")


async def aggregate(be_id: str) -> dict[str, Any] | None:
    """사진 종합(LLM, 기밀) → {area_m2_est, ceiling_h_m_est, walls, facts_ko}. 실패하면 사진별 추정만."""
    b = await svc.get(be_id)
    ps = [p for p in await _photos(be_id) if _usable(p)]
    if not ps:
        await repo().patch("birdseyes", be_id, {"photo_agg": None})
        return None
    lines = []
    for p in ps:
        js = p.get("i2t") or {}
        lines.append(f"사진 {p['n']}: 벽 {p.get('wall_label') or '?'} · 방향 {p.get('dir_slot') or '?'} · 요소 "
                     f"{', '.join(PH.found_label(js)) or '없음'} · 추정 {js.get('est') or {}}" + (" · 천장" if p.get("is_ceiling") else ""))
    facts = (b.get("photo_facts") or {}).get("facts_ko") or []
    prompt = (f"공간 설명: {(b.get('description') or '')[:400]}\n사용자 사실: {', '.join(facts) or '없음'}\n" + "\n".join(lines) +
              "\n사진들을 종합해 면적(㎡) · 층고(m) 추정, 벽(방향 1 정면 · 2 왼쪽 · 3 오른쪽 · 4 뒤)별 폭 추정, 사실 칩(facts_ko, 짧게)을 JSON 으로. "
              "사진에 없는 수치는 null.")
    try:
        agg = await llm.json_task("be.photo_aggregate", prompt, PH.PhotoAggregate, confidential=True, timeout=45)
    except llm.ModelBlocked:
        agg = None
    if agg is None:
        walls = []
        for p in ps:
            js = p.get("i2t") or {}
            w = (js.get("est") or {}).get("wall_width_m")
            if p.get("dir_slot") and str(p["dir_slot"]).isdigit():
                walls.append({"dir": int(p["dir_slot"]), "label": p.get("wall_label") or "", "width_m_est": w})
        ceil = next((p.get("ceiling_h_m") for p in ps if p.get("is_ceiling") and p.get("ceiling_h_m")), None)
        agg = {"area_m2_est": None, "ceiling_h_m_est": ceil, "walls": walls, "facts_ko": [], "path": "photo:local_agg"}
    await repo().patch("birdseyes", be_id, {"photo_agg": agg})
    return agg


def _photo_view(p: dict[str, Any]) -> dict[str, Any]:
    q = p.get("quality") or {}
    st = p.get("status") or "recognizing"
    return {
        "id": p["id"], "birdseye_id": p["birdseye_id"], "file_id": p["file_id"], "n": int(p.get("n") or 0), "wall_label": p.get("wall_label"),
        "dir_slot": p.get("dir_slot"), "status": st, "status_label": PH.status_label(p),
        "needs_check": st in ("backlit", "dark", "blurry", "failed"), "stage_label": p.get("stage_label"),
        "quality": {"mean": q.get("mean", 0), "bright_ratio": q.get("bright_ratio", 0), "rest_mean": q.get("rest_mean", 0),
                    "lap_var": q.get("lap_var", 0)},
        "found": p.get("found") or [], "is_ceiling": bool(p.get("is_ceiling")), "ceiling_h_m": p.get("ceiling_h_m"),
        "job_id": p.get("job_id"), "url": f"/api/files/v1/files/{p['file_id']}/content",
        "thumb_url": f"/api/files/v1/files/{p['file_id']}/thumbnail?w=320", "created_at": p["created_at"],
    }


async def photo_model(b: dict[str, Any], ps: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    ps = ps if ps is not None else await _photos(b["id"])
    usable = [p for p in ps if _usable(p)]
    if not usable:
        return None
    rooms = b.get("parsed_rooms") or S.regex_parse(b.get("description") or "")
    return PH.rect_from_photos(chip=b.get("space_chip") or "store_lobby", description_rooms=rooms,
                               area_field_pyeong=b.get("area_input_pyeong"), ceiling_field_m=b.get("ceiling_input_m"),
                               agg=b.get("photo_agg"), photos=usable, facts=b.get("photo_facts"))


async def photo_set(be_id: str) -> dict[str, Any]:
    b = await svc.get(be_id)
    ps = await _photos(be_id)
    model = await photo_model(b, ps)
    facts = list(((b.get("photo_facts") or {}).get("facts_ko") or []))
    for f in (b.get("photo_agg") or {}).get("facts_ko") or []:
        if f not in facts:
            facts.append(f)
    summ = PH.summarize(ps, space_name=S.space_name(b, None), description=b.get("description") or "", facts=facts, model=model)
    return {
        "items": [_photo_view(p) for p in ps], "counts": summ["counts"], "head": summ["head"], "dir_count": summ["dir_count"],
        "dir_label": summ["dir_label"], "has_ceiling": summ["has_ceiling"], "ceiling_label": summ["ceiling_label"],
        "basis_count": summ["basis_count"], "summary_chips": summ["summary_chips"], "w_message": summ["w_message"],
        "echo": b.get("description") or "", "can_continue": summ["can_continue"], "max_photos": int(config.rules()["upload"]["max_photos"]),
    }


async def accept_photo(be_id: str, phid: str, accept: bool) -> dict[str, Any]:
    p = await repo().get("photos", phid)
    if p is None or p.get("birdseye_id") != be_id:
        raise not_found("사진", phid)
    if accept and p.get("status") in ("backlit", "dark", "blurry"):
        await repo().patch("photos", phid, {"status": "accepted", "accepted_from": p["status"]})
    elif not accept and p.get("status") == "accepted":
        await repo().patch("photos", phid, {"status": p.get("accepted_from") or "backlit"})
    await aggregate(be_id)
    await svc.index(be_id)
    return _photo_view(await repo().get("photos", phid) or p)


async def delete_photo(be_id: str, phid: str) -> None:
    p = await repo().get("photos", phid)
    if p is None or p.get("birdseye_id") != be_id:
        raise not_found("사진", phid)
    await repo().delete("photos", phid)
    count = len(await _photos(be_id))

    def fn(d: dict[str, Any]) -> None:
        inputs = dict(d.get("inputs") or {})
        inputs["photo_count"] = count
        d["inputs"] = inputs

    await repo().mutate("birdseyes", be_id, fn)
    await aggregate(be_id)
    await svc.index(be_id)


async def add_facts(be_id: str, text: str) -> dict[str, Any]:
    """BE1P 「사진에 없는 정보」 → 사실 칩 · 공간 모델(사용자 값 > 추정)."""
    b = await svc.get(be_id)
    rx = PH.regex_facts(text)
    prompt = (f"사용자가 사진에 없는 공간 정보를 적었다: {text}\n짧은 사실 칩(facts_ko, 예 「상황판 벽 폭 약 9 m」 「운영석 2열」)과 "
              "모델 갱신 값(updates: wall_label · wall_width_m · ceiling_h_m · area_m2)을 JSON 으로. 글에 없는 수치는 null.")
    try:
        res = await llm.json_task("be.photo_facts", prompt, PH.PhotoFacts, confidential=True, timeout=30)
    except llm.ModelBlocked:
        res = None
    facts_new = [f for f in ((res or {}).get("facts_ko") or []) if f] or rx["facts_ko"]
    upd = {k: v for k, v in ((res or {}).get("updates") or {}).items() if v is not None}
    for k, v in rx["updates"].items():
        upd.setdefault(k, v)
    old = b.get("photo_facts") or {"facts_ko": [], "updates": {}}
    facts = list(old.get("facts_ko") or [])
    for f in facts_new:
        if f not in facts:
            facts.append(f)
    merged = {"facts_ko": facts, "updates": {**(old.get("updates") or {}), **upd}}
    await repo().patch("birdseyes", be_id, {"photo_facts": merged})
    if upd.get("ceiling_h_m") and not b.get("ceiling_input_m"):
        lo, hi = config.rules()["ceiling_range_m"]
        if lo <= float(upd["ceiling_h_m"]) <= hi:
            await repo().patch("birdseyes", be_id, {"ceiling_input_m": float(upd["ceiling_h_m"])})
    await aggregate(be_id)
    b = await svc.get(be_id)
    model = await photo_model(b)
    if model is None:
        rooms = b.get("parsed_rooms") or S.regex_parse(b.get("description") or "")
        model = S.rect_model(rooms, chip=b.get("space_chip") or "store_lobby", area_field_pyeong=b.get("area_input_pyeong"),
                             ceiling_field_m=b.get("ceiling_input_m"))
        model["facts"] = facts
    sm = await svc.space_model(be_id)
    if sm is not None:
        await refresh_space(be_id)
    return {"facts": facts, "model": model}


# ── QR 업로드 토큰 ───────────────────────────────────────

def qr_rows(text: str) -> list[str] | None:
    """QR 모듈 행("0101…") — reportlab qrencoder 가 없으면 None(주소만 보인다)."""
    try:
        from reportlab.graphics.barcode.qrencoder import QRCode, QRErrorCorrectLevel
    except Exception:  # noqa: BLE001
        return None
    try:
        qr = QRCode(None, QRErrorCorrectLevel.M)
        qr.addData(text)
        qr.make()
        n = qr.getModuleCount()
        return ["".join("1" if qr.isDark(r, c) else "0" for c in range(n)) for r in range(n)]
    except Exception:  # noqa: BLE001
        return None


async def create_token(be_id: str) -> dict[str, Any]:
    b = await svc.get(be_id)
    token = secrets.token_urlsafe(16)
    minutes = int(config.rules()["upload"]["token_minutes"])
    expires = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")
    await repo().put("tokens", token, {"birdseye_id": be_id, "owner": b["owner"], "owner_name": b.get("owner_name") or "",
                                       "expires_at": expires, "used_count": 0})
    path = f"/m/upload/{token}"
    url = f"{config.public_base_url()}{path}" if config.public_base_url() else path
    return {"token": token, "url": url, "path": path, "expires_at": expires, "qr": qr_rows(url)}


def _expired(t: dict[str, Any]) -> bool:
    try:
        exp = datetime.fromisoformat(str(t["expires_at"]).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return True
    return datetime.now(timezone.utc) >= exp


async def _token(token: str) -> dict[str, Any]:
    t = await repo().get("tokens", token)
    if t is None:
        raise ApiError(404, "NOT_FOUND", "올리기 주소를 찾을 수 없어요")
    if _expired(t):
        raise ApiError(410, "TOKEN_EXPIRED", "QR 유효 시간이 지났어요. PC 화면에서 새 QR을 만들어 주세요.")
    return t


async def token_info(token: str) -> dict[str, Any]:
    t = await repo().get("tokens", token)
    if t is None:
        raise ApiError(404, "NOT_FOUND", "올리기 주소를 찾을 수 없어요")
    b = await repo().get("birdseyes", t["birdseye_id"])
    if b is None or b.get("deleted_at"):
        raise ApiError(404, "NOT_FOUND", "조감도 작업을 찾을 수 없어요")
    return {"token": token, "valid": not _expired(t), "expires_at": t["expires_at"], "title": b.get("title") or "",
            "photo_count": int((b.get("inputs") or {}).get("photo_count") or 0)}


async def token_principal(token: str) -> dict[str, Any]:
    """게이트웨이 전용: 업로드 토큰 → 주인(로그인 없는 휴대폰 요청을 주인 이름으로 통과시킬 때)."""
    t = await repo().get("tokens", token)
    if t is None:
        return {"valid": False}
    b = await repo().get("birdseyes", t["birdseye_id"])
    if b is None or b.get("deleted_at") or _expired(t):
        return {"valid": False}
    return {"valid": True, "owner": t["owner"], "owner_name": t.get("owner_name") or "", "birdseye_id": t["birdseye_id"],
            "expires_at": t["expires_at"]}


async def token_photo(token: str, file_id: str) -> dict[str, Any]:
    t = await _token(token)
    acc = await add_photo(t["birdseye_id"], file_id, owner=(t["owner"], t.get("owner_name") or ""))

    def fn(d: dict[str, Any]) -> None:
        d["used_count"] = int(d.get("used_count") or 0) + 1

    await repo().mutate("tokens", token, fn, missing_ok=True)
    return acc


# ── 공간 분석(be.space_analyze) ──────────────────────────

async def save_space(be_id: str, model: dict[str, Any]) -> dict[str, Any]:
    saved = await repo().put("space", be_id, {"birdseye_id": be_id, "model": model, "source": model.get("source", "description")},
                             history=True)
    return saved


def _merge_parsed(llm_rooms: list[dict[str, Any]] | None, rx_rooms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """LLM 결과의 빈 숫자는 글에서 읽은 값(정규식)으로만 채운다(지어내지 않음)."""
    if not llm_rooms:
        return rx_rooms
    out = []
    for i, r in enumerate(llm_rooms):
        rr = dict(r)
        rx = rx_rooms[i] if i < len(rx_rooms) else {}
        for k in ("area_pyeong", "ceiling_m"):
            if not rr.get(k) and rx.get(k):
                rr[k] = rx[k]
        if not rr.get("label") and rx.get("label"):
            rr["label"] = rx["label"]
        kinds = {f.get("kind") for f in rr.get("features") or []}
        for f in rx.get("features") or []:
            if f.get("kind") not in kinds:
                rr.setdefault("features", []).append(f)
        out.append(rr)
    return out


async def parse_description(b: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    desc = (b.get("description") or "").strip()
    rx = S.regex_parse(desc)
    if not desc:
        return [], []
    try:
        res = await llm.json_task("be.space_parse", f"공간 설명:\n{desc}", S.ParsedSpace, system=S.PARSE_SYSTEM, confidential=True)
    except llm.ModelBlocked:
        res = None
    rooms = (res or {}).get("rooms") or []
    if not rooms:
        return rx, ["space:regex"]
    return _merge_parsed(rooms, rx), []


async def build_space(b: dict[str, Any], parsed: list[dict[str, Any]], caps: list[dict[str, Any]], paths: list[str],
                      *, finalize: bool = True) -> dict[str, Any]:
    be_id = b["id"]
    chip = b.get("space_chip") or "store_lobby"
    info = config.chip_info(chip)
    plan = await _active_plan(be_id)
    ps = await _photos(be_id)
    usable = [p for p in ps if _usable(p)]
    if plan is not None:
        m = PL.finalize_defaults(plan["model"]) if finalize else copy.deepcopy(plan["model"])
        m["questions"] = [q for q in m.get("questions", [])]
        m["source"] = "mixed" if usable else "plan"
        m = S.with_features_from_description(m, parsed)
        if not m["rooms"][0].get("label"):
            m["rooms"][0]["label"] = (parsed[0].get("label") if parsed else None) or info["space_label"]
        if not m["rooms"][0].get("space_types"):
            m["rooms"][0]["space_types"] = list(info["space_types"])
        ceiling = b.get("ceiling_input_m") or next((r.get("ceiling_m") for r in parsed if r.get("ceiling_m")), None)
        ceil_photo = next((p.get("ceiling_h_m") for p in usable if p.get("is_ceiling") and p.get("ceiling_h_m")), None)
        lo, hi = config.rules()["ceiling_range_m"]
        m["assumptions"] = [a for a in m.get("assumptions", []) if a.get("kind") != "ceiling_estimate"]
        if ceiling:
            m["ceiling_h"] = {"value": round(min(max(float(ceiling), lo), hi), 2), "estimated": False}
        elif ceil_photo:
            m["ceiling_h"] = {"value": round(min(max(float(ceil_photo), lo), hi), 2), "estimated": True}
        else:
            m["ceiling_h"] = {"value": float(info["ceiling_m"]), "estimated": True}
            m["assumptions"].append({"kind": "ceiling_estimate", "ref": None, "action": "BE1",
                                     "text_ko": f"층고를 알 수 없어 {T.num(info['ceiling_m'])} m로 잡았어요."})
    elif usable:
        m = await photo_model({**b, "parsed_rooms": parsed}, ps) or {}
    else:
        m = S.rect_model(parsed, chip=chip, area_field_pyeong=b.get("area_input_pyeong"), ceiling_field_m=b.get("ceiling_input_m"))
    if plan is None and usable and parsed:
        m = S.with_features_from_description(m, parsed)
    if b.get("ceiling_input_m"):
        m = S.apply_fields(m, ceiling_field_m=b.get("ceiling_input_m"))
    m = S.apply_caps(m, caps)
    for pth in paths:
        if pth not in m.setdefault("meta_paths", []):
            m["meta_paths"].append(pth)
    return m


class SpaceState(TypedDict, total=False):
    birdseye_id: str
    parsed: list[dict[str, Any]]
    paths: list[str]
    caps: list[dict[str, Any]]
    model: dict[str, Any]
    version: int


async def _sa_load(state: SpaceState) -> dict[str, Any]:
    await _progress(5, "입력 불러오는 중")
    b = await svc.get(state["birdseye_id"])
    # 「이 구조로 계속」: 인식된 도면은 확정(미해결 질문은 안전 기본값 + 가정)
    for p in await repo().all("plans", where={"birdseye_id": b["id"]}):
        if p.get("status") == "recognized" and not p.get("finalized"):
            await repo().patch("plans", p["id"], {"finalized": True})
    return {"paths": []}


async def _sa_parse(state: SpaceState) -> dict[str, Any]:
    await _progress(25, "공간 설명 해석 중")
    b = await svc.get(state["birdseye_id"])
    parsed, paths = await parse_description(b)
    return {"parsed": parsed, "paths": list(state.get("paths") or []) + paths}


async def _sa_merge(state: SpaceState) -> dict[str, Any]:
    await _progress(55, "공간 모델 만드는 중")
    b = await svc.get(state["birdseye_id"])
    m = await build_space(b, state.get("parsed") or [], [], state.get("paths") or [])
    return {"model": m}


async def _sa_caps(state: SpaceState) -> dict[str, Any]:
    await _progress(75, "공간 특징 확인 중")
    b = await svc.get(state["birdseye_id"])
    m = state["model"]
    types = list(b.get("space_types") or [])
    caps = await kbapi.capabilities_for(types, S.caps_text(m, b.get("description") or ""))
    m = S.apply_caps(copy.deepcopy(m), caps)
    return {"model": m, "caps": [{"id": c.get("id"), "name": c.get("name")} for c in caps if c.get("id")]}


async def _sa_save(state: SpaceState) -> dict[str, Any]:
    await _progress(92, "저장 중")
    be_id = state["birdseye_id"]
    saved = await save_space(be_id, state["model"])
    b = await svc.get(be_id)
    changes: dict[str, Any] = {"parsed_rooms": state.get("parsed") or [], "space_caps": state.get("caps") or [], "analyzing_job_id": None}
    if int(b.get("step") or 1) < 2:
        changes["step"] = 2
    await repo().patch("birdseyes", be_id, changes)
    await svc.index(be_id)
    return {"version": int(saved.get("version") or 1)}


def space_graph() -> StateGraph:
    g = StateGraph(SpaceState)
    for name, fn in (("load_inputs", _sa_load), ("parse_description", _sa_parse), ("merge", _sa_merge), ("capability_hints", _sa_caps),
                     ("save", _sa_save)):
        g.add_node(name, fn)
    g.add_edge(START, "load_inputs")
    g.add_edge("load_inputs", "parse_description")
    g.add_edge("parse_description", "merge")
    g.add_edge("merge", "capability_hints")
    g.add_edge("capability_hints", "save")
    g.add_edge("save", END)
    return g


async def refresh_space(be_id: str) -> dict[str, Any] | None:
    """이미 분석한 공간을 모델 호출 없이 다시 합친다(도면 답 · 사실 입력 · 칸 값 변경 뒤)."""
    b = await svc.get(be_id)
    if await svc.space_model(be_id) is None:
        return None
    m = await build_space(b, b.get("parsed_rooms") or S.regex_parse(b.get("description") or ""), b.get("space_caps") or [], [])
    old = await svc.space_model(be_id) or {}
    m["meta_paths"] = list(dict.fromkeys((old.get("meta_paths") or []) + (m.get("meta_paths") or [])))
    await save_space(be_id, m)
    return m


async def start_analyze(be_id: str) -> dict[str, Any]:
    b = await svc.get(be_id)
    inputs = b.get("inputs") or {}
    if not ((b.get("description") or "").strip() or inputs.get("plan_file_ids") or inputs.get("photo_count")):
        raise ApiError(400, "INPUT_REQUIRED", "공간 설명을 적거나 도면 · 사진을 첨부해 주세요")
    job_id = new_id("job")
    await repo().patch("birdseyes", be_id, {"analyzing_job_id": job_id})
    await jobs().enqueue("birdseye", "space_analyze", {"birdseye_id": be_id}, title=f"{b['title']} · 공간 분석", ref=be_id,
                         project_id=b.get("project_id"), owner=b["owner"], owner_name=b.get("owner_name") or "", job_id=job_id)
    return {"job_id": job_id, "status": "queued"}


async def _job_running(job_id: str | None) -> bool:
    if not job_id:
        return False
    j = await jobs().get(job_id)
    return j is not None and j.status in ("queued", "running")


async def input_files(be_id: str) -> list[dict[str, Any]]:
    out = []
    for p in await repo().all("plans", where={"birdseye_id": be_id}, order_by="created_at"):
        out.append({"file_id": p["file_id"], "name": p.get("file_name") or "도면", "kind": "plan",
                    "route": f"/birdseye/{be_id}/space/plan?plan={p['id']}"})
    ps = await _photos(be_id)
    if ps:
        out.append({"file_id": ps[0]["file_id"], "name": f"현장 사진 {len(ps)}장", "kind": "photo", "route": f"/birdseye/{be_id}/space/photos"})
    return out


async def space_view(be_id: str) -> dict[str, Any]:
    b = await svc.get(be_id)
    doc = await repo().get("space", be_id)
    model = doc.get("model") if doc else None
    running = await _job_running(b.get("analyzing_job_id"))
    name = S.space_name(b, model)
    return {
        "model": model, "summary_chips": S.summary_chips(model), "w_message": W_ANALYZING if running or model is None else S.w_message(name, model),
        "features_text": S.features_text(model), "space_name": name, "analyzing": running,
        "job_id": b.get("analyzing_job_id") if running else None, "version": int(doc.get("version") or 0) if doc else 0,
        "echo": b.get("description") or "", "files": await input_files(be_id),
    }
