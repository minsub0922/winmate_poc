"""생성 run · 대기열(§4.6 · §6.5) — run 만들기(사전 검사 R3 포함) · 보기 · 취소 · 대안 답 · 내 대기열.

run 하나 = jobs 잡 하나(`wm:q:image`, kind='run'). 사용자당 진행 run 은 IMAGE_MAX_RUNNING_PER_USER(1)개 —
나머지는 run.status='queued' 로 「내 대기열」에 남고, 워커가 차례가 오면 running 으로 바꾼다(scheduler.wait_turn).
"""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.context import current_user
from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import jobs

from . import config, policy, texts, views
from .service import autofill_description, get_work, references_of, refresh_work
from .store import repo

log = logging.getLogger("winmate.image.runs")

GEN = ("initial", "composite", "alternatives")
LIVE = ("queued", "running", "awaiting_input")


def run_in_progress(run_id: str | None = None) -> ApiError:
    return ApiError(409, "RUN_IN_PROGRESS", "이 작업은 이미 생성 중이에요. 끝나거나 취소한 뒤 다시 시도해 주세요",
                    {"run_id": run_id} if run_id else {})


async def next_shot_number(work_id: str) -> int:
    imgs = await repo().all("images", where={"work_id": work_id})
    nums = [int(i.get("shot_no") or 0) for i in imgs if i.get("run_kind") in GEN]
    return (max(nums) if nums else 0) + 1


async def precheck_text(work: dict[str, Any]) -> str:
    refs = await references_of(work["id"])
    parts = [work.get("description") or ""]
    parts += [p.get("name") or "" for p in (work.get("conditions") or {}).get("products") or []]
    parts += [r.get("label") or "" for r in refs if r.get("origin_kind") == "upload"]
    return " · ".join(x for x in parts if x)


async def run_precheck(work: dict[str, Any]) -> dict[str, Any]:
    """동기 사전 검사(LLM 8초 제한 → 넘으면 사전 · 정규식만). 참조 분석 결과가 이미 있으면 디스플레이 이슈도."""
    text = await precheck_text(work)
    refs = await references_of(work["id"])
    confidential = work.get("kind") == "composite" or any(r.get("confidential") for r in refs)
    cls, mode = await policy.classify_with_timeout(text, confidential=confidential)
    product_issues = await reference_product_issues(work["id"])
    issues = policy.build_issues(cls, product_issues)
    return {"issues": issues, "mode": mode, "applied_note": policy.applied_note(issues) if issues else None}


async def reference_product_issues(work_id: str) -> list[dict[str, Any]]:
    """분석이 끝난 참조(업로드 · 상단 이미지 검색) 속 디스플레이 → 제품 매칭(top1 < 0.6 → product_unrecognized)."""
    out = []
    for r in await references_of(work_id):
        an = r.get("analysis") or {}
        for d in an.get("displays") or []:
            if float(d.get("confidence") or 0) >= config.product_match_min():
                continue
            cands = an.get("candidates") or []
            out.append(policy.product_issue(0, reference_id=r["id"], thumb_url=r.get("thumb_url"), candidates=cands,
                                            box=d.get("box")))
            break
    return out[:1]


async def create_shots(*, work: dict[str, Any], run_id: str, run_kind: str, n: int, aspect: str, style: str,
                       base_image_id: str | None = None, labels: list[str] | None = None, letters: list[str] | None = None,
                       origin: str = "image", owner: str | None = None, aspects: list[str] | None = None) -> list[dict[str, Any]]:
    first = await next_shot_number(work["id"]) if run_kind in GEN else 0
    shots = []
    for i in range(n):
        iid = new_id("img")
        label = (labels[i] if labels and i < len(labels) else texts.shot_label(first + i))
        doc = {
            "work_id": work["id"], "run_id": run_id, "run_kind": run_kind, "owner": owner or work.get("owner"),
            "label": label, "letter": letters[i] if letters and i < len(letters) else None,
            "shot_no": first + i if run_kind in GEN else None, "index": i + 1,
            "aspect": aspects[i] if aspects and i < len(aspects) else aspect, "style": style,
            "kind": work.get("kind") or "space", "status": "waiting", "stage_label": "", "progress": 0.0,
            "base_image_id": base_image_id, "origin": origin, "current_version_id": None, "saved": False, "hidden": False,
            "customer_short": work.get("customer_short"), "subject_short": work.get("subject_short"),
            "project_id": work.get("project_id"), "work_title": work.get("title"), "created_at": now_iso(),
        }
        shots.append(await repo().put("images", iid, doc))
    return shots


async def create_run(work_id: str, *, kind: str, count: int | None, notify: bool) -> dict[str, Any]:
    work = await get_work(work_id)
    runs = await repo().all("runs", where={"work_id": work_id})
    busy = next((r for r in runs if r.get("kind") in GEN and r.get("status") in ("queued", "running")), None)
    if busy is not None:
        raise run_in_progress(busy.get("id"))
    cond = work.get("conditions") or {}
    if kind == "composite" or work.get("kind") == "composite":
        kind = "composite"
        comp = work.get("composite") or {}
        if not comp.get("active_photo_id"):
            raise ApiError(422, "PHOTO_REQUIRED", "현장 사진을 먼저 올려 주세요")
        n = config.COMPOSITE_COUNT
    else:
        if len((work.get("description") or "").strip()) < 2:
            if not await references_of(work_id):
                raise ApiError(422, "DESCRIPTION_REQUIRED", "장면 설명을 2자 이상 적어 주세요")
            if await autofill_description(work_id):
                work = await get_work(work_id)
        n = int(count or cond.get("count") or 4)
        if n not in config.COUNTS:
            raise ApiError(422, "VALIDATION_ERROR", "장수는 2장 또는 4장입니다")
        if count and count != cond.get("count"):
            cond = {**cond, "count": n}

            def fn(w: dict[str, Any]) -> None:
                w["conditions"] = cond

            await repo().mutate("works", work_id, fn)
    pre = await run_precheck(work)
    user = current_user()
    rid = new_id("ign")
    aspect = cond.get("aspect") or "16:9"
    if kind == "composite":
        photo = await repo().get("photos", (work.get("composite") or {}).get("active_photo_id"))
        if photo and photo.get("width") and photo.get("height"):
            aspect = config.nearest_aspect(int(photo["width"]), int(photo["height"]), ("16:9", "4:3", "1:1", "9:16"))
    refs = await references_of(work_id)
    run = {
        "work_id": work_id, "owner": work.get("owner") or user.id, "owner_name": work.get("owner_name") or user.name,
        "kind": kind, "params": {"count": n, "aspect": aspect, "style": cond.get("style") or "photo",
                                 "conditions": cond, "description": work.get("description") or ""},
        "status": "queued", "phase": "queued", "notify": bool(notify), "precheck": pre, "total": n, "done": 0, "held": 0,
        "title": work.get("title") or "", "summary_line": texts.run_summary_line(cond.get("products") or [], len(refs)),
        "queued_at": now_iso(), "created_at": now_iso(), "started_at": None, "finished_at": None, "error": None, "job_id": None,
        "notified": False,
    }
    await repo().put("runs", rid, run)
    await create_shots(work=work, run_id=rid, run_kind=kind, n=n, aspect=aspect, style=cond.get("style") or "photo")
    job = await jobs().enqueue("image", "run", {"run_id": rid}, title=f"{work.get('title') or '이미지'} · 이미지 {n}장",
                               ref=rid, project_id=work.get("project_id"))
    saved = await repo().patch("runs", rid, {"job_id": job.id})
    await refresh_work(work_id)
    return saved or run


async def enqueue_run(*, work: dict[str, Any], kind: str, params: dict[str, Any], n: int, base_image_id: str | None,
                      labels: list[str] | None = None, letters: list[str] | None = None, aspect: str | None = None,
                      notify: bool = True, title: str | None = None, origin: str = "image", shots: bool = True,
                      summary: str | None = None, aspects: list[str] | None = None) -> dict[str, Any]:
    """편집 · 변형 · 비율 · 렌더 API run(같은 작업 아래 새 run 으로 쌓인다)."""
    user = current_user()
    rid = new_id("ign")
    run = {
        "work_id": work["id"], "owner": work.get("owner") or user.id, "owner_name": work.get("owner_name") or user.name,
        "kind": kind, "params": params, "status": "queued", "phase": "queued", "notify": notify,
        "precheck": {"issues": [], "mode": "rules", "applied_note": None}, "total": n, "done": 0, "held": 0,
        "title": title or work.get("title") or "", "summary_line": summary or "", "base_image_id": base_image_id,
        "queued_at": now_iso(), "created_at": now_iso(), "started_at": None, "finished_at": None, "error": None,
        "job_id": None, "notified": False,
    }
    await repo().put("runs", rid, run)
    if shots and n:
        await create_shots(work=work, run_id=rid, run_kind=kind, n=n, aspect=aspect or params.get("aspect") or "16:9",
                           style=params.get("style") or "photo", base_image_id=base_image_id, labels=labels, letters=letters,
                           origin=origin, aspects=aspects)
    job = await jobs().enqueue("image", "run", {"run_id": rid}, title=title or f"{work.get('title') or '이미지'} · {kind}",
                               ref=rid, project_id=work.get("project_id"))
    saved = await repo().patch("runs", rid, {"job_id": job.id})
    if origin == "image":
        await refresh_work(work["id"])
    return saved or run


async def get_run(run_id: str) -> dict[str, Any]:
    run = await repo().get("runs", run_id)
    if run is None:
        raise not_found("생성 run", run_id)
    return run


async def shots_of(run_id: str) -> list[dict[str, Any]]:
    shots = await repo().all("images", where={"run_id": run_id}, order_by="created_at")
    return sorted(shots, key=lambda s: int(s.get("index") or 0))


async def queue_ahead(run: dict[str, Any]) -> int:
    if run.get("status") != "queued":
        return 0
    mine = await repo().all("runs", where={"owner": run.get("owner"), "status": ["queued", "running"]})
    key = (run.get("queued_at") or "", run.get("created_at") or "")
    return sum(1 for r in mine if r["id"] != run["id"] and (r.get("status") == "running" or
                                                            (r.get("queued_at") or "", r.get("created_at") or "") < key))


async def run_detail(run: dict[str, Any]) -> dict[str, Any]:
    shots = await shots_of(run["id"])
    versions: dict[str, dict[str, Any]] = {}
    for s in shots:
        if s.get("current_version_id"):
            v = await repo().get("versions", s["current_version_id"])
            if v:
                versions[v["id"]] = v
    return views.run_view(run, shots, versions=versions, queue_ahead=await queue_ahead(run))


async def set_notify(run_id: str, notify: bool) -> dict[str, Any]:
    await get_run(run_id)
    return await repo().patch("runs", run_id, {"notify": bool(notify)}) or await get_run(run_id)


async def cancel_run(run_id: str) -> dict[str, Any]:
    run = await get_run(run_id)
    if run.get("status") in ("succeeded", "failed", "canceled"):
        return run
    if run.get("job_id"):
        try:
            await jobs().cancel(run["job_id"])
        except Exception as exc:  # noqa: BLE001
            log.warning("잡 취소 실패 %s: %s", run["job_id"], exc)
    now = now_iso()
    for s in await shots_of(run_id):
        if s.get("status") in ("waiting", "composing", "rendering", "qc", "held"):
            await repo().patch("images", s["id"], {"status": "canceled", "stage_label": "취소됨"})
        elif s.get("status") == "done" and not s.get("saved"):
            # 「끝난 시안은 갤러리에 남김」
            await repo().patch("images", s["id"], {"saved": True, "saved_at": now})
    saved = await repo().patch("runs", run_id, {"status": "canceled", "phase": "done", "finished_at": now})
    await refresh_work(run["work_id"])
    return saved or run


async def cancel_shot(run_id: str, image_id: str) -> dict[str, Any]:
    run = await get_run(run_id)
    img = await repo().get("images", image_id)
    if img is None or img.get("run_id") != run_id:
        raise not_found("시안", image_id)
    if img.get("status") in ("done", "failed", "canceled"):
        return img
    saved = await repo().patch("images", image_id, {"status": "canceled", "stage_label": "취소됨"})
    if run.get("status") == "awaiting_input":
        # 보류 시안을 모두 취소하면 run 은 남은 것으로 끝난다
        left = [s for s in await shots_of(run_id) if s.get("status") == "held"]
        if not left:
            await finish_without_held(run)
    return saved or img


async def finish_without_held(run: dict[str, Any]) -> None:
    if run.get("job_id"):
        try:
            await jobs().provide_input(run["job_id"], {"answers": [], "skip_held": True})
            await repo().patch("runs", run["id"], {"status": "queued", "queued_at": now_iso()})
        except Exception as exc:  # noqa: BLE001
            log.info("보류 없음 처리 실패: %s", exc)


async def answer(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    run = await get_run(run_id)
    if run.get("status") != "awaiting_input":
        raise ApiError(409, "NOT_AWAITING_INPUT", "대안을 기다리는 생성이 아니에요")
    pre = run.get("precheck") or {}
    issues = policy.apply_answers(pre.get("issues") or [], body.get("answers") or [], all_recommended=bool(body.get("all_recommended")))
    pre = {**pre, "issues": issues, "applied_note": policy.applied_note(issues)}
    await repo().patch("runs", run_id, {"precheck": pre, "status": "queued", "queued_at": now_iso(), "phase": "queued"})
    if body.get("skip_held"):
        for s in await shots_of(run_id):
            if s.get("status") == "held":
                await repo().patch("images", s["id"], {"status": "canceled", "stage_label": "취소됨"})
    try:
        await jobs().provide_input(run["job_id"], {"answers": body.get("answers") or [], "skip_held": bool(body.get("skip_held")),
                                                   "all_recommended": bool(body.get("all_recommended"))})
    except (KeyError, ValueError) as exc:
        raise ApiError(409, "NOT_AWAITING_INPUT", f"잡이 입력을 기다리지 않습니다: {exc}") from exc
    await refresh_work(run["work_id"])
    return await get_run(run_id)


async def custom_alternative(run_id: str, text: str) -> dict[str, Any]:
    run = await get_run(run_id)
    if run.get("status") != "awaiting_input":
        raise ApiError(409, "NOT_AWAITING_INPUT", "대안을 기다리는 생성이 아니에요")
    pre = run.get("precheck") or {}
    issues = pre.get("issues") or []
    judged = await policy.judge_custom(text, issues)
    if judged is None or judged.get("issue_type") == "none":
        return {"accepted": False, "issue_id": None, "message": "어느 항목의 대안인지 알 수 없어요. 항목을 골라 다시 적어 주세요", "run": run}
    target = next((i for i in issues if i["type"] == judged["issue_type"]), None)
    if target is None:
        return {"accepted": False, "issue_id": None, "message": "해당하는 보류 사유가 없어요", "run": run}
    if not judged.get("safe"):
        return {"accepted": False, "issue_id": target["id"], "message": "그 방법으로는 만들 수 없어요 · 다른 대안을 골라 주세요", "run": run}
    target["selected"] = "custom"
    target["custom_text"] = judged.get("option_text") or text
    target["state_label"] = "대안 선택됨"
    pre = {**pre, "issues": issues, "applied_note": policy.applied_note(issues)}
    saved = await repo().patch("runs", run_id, {"precheck": pre})
    return {"accepted": True, "issue_id": target["id"], "message": f"‘{target['custom_text']}’ 대안으로 바꿨어요", "run": saved or run}


async def queue_for(owner: str) -> dict[str, Any]:
    mine = await repo().all("runs", where={"owner": owner, "status": ["queued", "running"]}, order_by="created_at")
    running = [r for r in mine if r.get("status") == "running"]
    queued = sorted([r for r in mine if r.get("status") == "queued"], key=lambda r: (r.get("queued_at") or "", r.get("created_at") or ""))
    items = []
    for pos, r in enumerate(queued, 1):
        work = await repo().get("works", r["work_id"]) or {}
        issues = (r.get("precheck") or {}).get("issues") or []
        held = policy.held_count(int(r.get("total") or 0), issues)
        meta_parts = [work.get("customer_short") or work.get("customer_name")] if (work.get("customer_short") or work.get("customer_name")) else []
        meta_parts.append(views.run_count_label(r, work) or config.KIND_LABEL.get(work.get("kind") or "space", ""))
        items.append({"run_id": r["id"], "work_id": r["work_id"], "title": work.get("title") or r.get("title") or "이미지 작업",
                      "meta": " · ".join(x for x in meta_parts if x), "position": pos, "state_label": texts.queue_label(pos),
                      "note": f"{held}장은 생성 불가 · 안내 보기" if held else None,
                      "note_route": views.run_route(r) if held else None})
    return {"items": items, "running": views.run_brief(running[0]) if running else None}
