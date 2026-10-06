"""저장 문서 → API 모양(Pydantic 모델 dict). 상태 배지 · 경로 · 메타 문구는 여기서 정한다(07-image §4.1 · §5.4 · §10.5)."""
from __future__ import annotations

import time
from typing import Any

from . import config, texts
from .filestore import content_url, thumb_url
from .texts import parse_iso

ACTIVE_RUN = ("queued", "running")
GEN_KINDS = ("initial", "composite", "alternatives")


# ── 경로 ─────────────────────────────────────────────────

def route_type(work_id: str) -> str:
    return f"/image/new?work={work_id}"


def route_conditions(work_id: str) -> str:
    return f"/image/w/{work_id}/conditions"


def route_references(work_id: str) -> str:
    return f"/image/w/{work_id}/references"


def route_composite(work_id: str) -> str:
    return f"/image/w/{work_id}/composite"


def route_run(work_id: str, run_id: str) -> str:
    return f"/image/w/{work_id}/run/{run_id}"


def route_result(work_id: str, image_id: str | None = None) -> str:
    return f"/image/w/{work_id}/result" + (f"?image={image_id}" if image_id else "")


def route_edit(work_id: str, image_id: str) -> str:
    return f"/image/w/{work_id}/edit/{image_id}"


def route_variants(work_id: str, image_id: str) -> str:
    return f"/image/w/{work_id}/variants/{image_id}"


def route_export(work_id: str, image_id: str) -> str:
    return f"/image/w/{work_id}/export/{image_id}"


def run_route(run: dict[str, Any]) -> str:
    return route_run(run["work_id"], run["id"])


# ── 작업 ─────────────────────────────────────────────────

def echo(work: dict[str, Any]) -> str:
    kind = config.KIND_LABEL.get(work.get("kind") or "space", "공간")
    desc = (work.get("description") or "").strip()
    return f"{kind} · {desc}" if desc else kind


def run_brief(run: dict[str, Any] | None) -> dict[str, Any] | None:
    if not run:
        return None
    return {"id": run["id"], "kind": run["kind"], "status": run["status"], "job_id": run.get("job_id"),
            "done": int(run.get("done") or 0), "total": int(run.get("total") or 0), "held": int(run.get("held") or 0),
            "route": run_route(run)}


def run_count_label(run: dict[str, Any] | None, work: dict[str, Any]) -> str | None:
    if work.get("kind") == "composite":
        return None
    if not run:
        c = (work.get("conditions") or {}).get("count")
        return f"{c}장" if c else None
    total = int(run.get("total") or 0)
    k = run.get("kind")
    if k == "variants":
        return f"변형 {total}장"
    if k == "renditions":
        return f"{total}개 비율"
    if k == "edit":
        return "부분 수정"
    return f"{total}장" if total else None


def work_meta(work: dict[str, Any], run: dict[str, Any] | None) -> str:
    parts = []
    if work.get("customer_name"):
        parts.append(work["customer_name"])
    if work.get("kind") == "composite":
        parts.append("현장 사진 합성")
    else:
        parts.append(config.KIND_LABEL.get(work.get("kind") or "space", "공간"))
        c = run_count_label(run, work)
        if c:
            parts.append(c)
    return " · ".join(parts)


def badge(work: dict[str, Any], runs: list[dict[str, Any]], *, in_proposal: bool) -> dict[str, Any]:
    """§4.1 상태 배지(우선순위 위→아래, 하나만)."""
    active = [r for r in runs if r.get("status") in ACTIVE_RUN]
    if active:
        r = sorted(active, key=lambda x: x.get("created_at") or "")[-1]
        return {"code": "running", "label": f"생성 중 {int(r.get('done') or 0)} / {int(r.get('total') or 0)}", "tone": "brand", "icon": "clock"}
    waiting = [r for r in runs if r.get("status") == "awaiting_input"]
    if waiting:
        held = int(waiting[-1].get("held") or 0)
        return {"code": "awaiting_input", "label": f"{held}장 생성 불가 · 대안 보기", "tone": "ink", "icon": "info"}
    if work.get("kind") == "composite" and not runs:
        return {"code": "placing", "label": "제품 위치 지정 중", "tone": "gray", "icon": "edit"}
    if in_proposal:
        return {"code": "in_proposal", "label": "제안서 사용 중", "tone": "brand", "icon": "check"}
    last = runs[-1] if runs else None
    le = work.get("last_export") or {}
    if le.get("format") and (not last or (le.get("at") or "") >= (last.get("finished_at") or last.get("created_at") or "")):
        fmt = str(le["format"]).upper()
        return {"code": "exported", "label": f"{fmt}{texts.josa(fmt, '으로/로')} 내보냄", "tone": "gray", "icon": "download"}
    if last is None:
        return {"code": "draft", "label": "작성 중", "tone": "gray", "icon": "edit"}
    st = last.get("status")
    if st == "failed":
        return {"code": "failed", "label": "생성 실패 · 다시 시도", "tone": "ink", "icon": "info"}
    if st == "canceled":
        return {"code": "canceled", "label": "취소됨", "tone": "gray", "icon": "none"}
    return {"code": "done", "label": "완료", "tone": "gray", "icon": "check"}


def work_status(work: dict[str, Any], runs: list[dict[str, Any]]) -> str:
    """§3.5 — 진행 중 run 이 하나라도 있으면 running, 아니면 가장 최근 run 의 상태."""
    if any(r.get("status") == "running" for r in runs):
        return "running"
    if any(r.get("status") == "queued" for r in runs):
        return "queued"
    if not runs:
        return "draft"
    last = runs[-1]
    return {"queued": "queued", "running": "running", "awaiting_input": "awaiting_input", "succeeded": "done",
            "failed": "failed", "canceled": "canceled"}.get(last.get("status") or "", "draft")


def work_route(work: dict[str, Any], runs: list[dict[str, Any]]) -> str:
    """§5.4 route 규칙."""
    wid = work["id"]
    live = [r for r in runs if r.get("status") in ("queued", "running", "awaiting_input")]
    if live:
        # 생성 run 우선(편집 · 변형은 그 화면에서 진행을 보인다)
        gen = [r for r in live if r.get("kind") in GEN_KINDS] or live
        r = sorted(gen, key=lambda x: x.get("created_at") or "")[-1]
        if r.get("kind") in GEN_KINDS or r.get("kind") == "renditions":
            return route_run(wid, r["id"])
        if r.get("kind") == "variants" and r.get("base_image_id"):
            return route_variants(wid, r["base_image_id"])
        if r.get("kind") == "edit" and r.get("base_image_id"):
            return route_edit(wid, r["base_image_id"])
        return route_run(wid, r["id"])
    le = work.get("last_export") or {}
    last = runs[-1] if runs else None
    if le.get("image_id") and (not last or (le.get("at") or "") >= (last.get("finished_at") or last.get("created_at") or "")):
        return route_export(wid, le["image_id"])
    if last is not None and last.get("status") == "succeeded":
        return route_result(wid)
    if last is not None and last.get("status") in ("failed",):
        return route_run(wid, last["id"])
    if work.get("kind") == "composite":
        return route_composite(wid)
    stage = work.get("stage") or "type"
    if stage == "references":
        return route_references(wid)
    if stage == "conditions" or (last is not None):
        return route_conditions(wid)
    return route_type(wid)


# ── 참조 ─────────────────────────────────────────────────

def role_label(aspects: list[str]) -> str:
    return " · ".join(config.ASPECT_LABEL.get(a, a) for a in aspects)


def reference_view(ref: dict[str, Any]) -> dict[str, Any]:
    origin_kind = ref.get("origin_kind") or ref.get("source_kind") or "kb_asset"
    if origin_kind == "topbar":
        origin_kind = "kb_asset"
    return {
        "id": ref["id"], "work_id": ref["work_id"], "order": int(ref.get("order") or 0), "source_kind": ref.get("source_kind") or "kb_asset",
        "source_ref": ref.get("source_ref"), "origin_kind": origin_kind, "file_id": ref.get("file_id"),
        "thumb_url": ref.get("thumb_url") or thumb_url(ref.get("file_id")), "label": ref.get("label") or "참조 이미지",
        "source_label": ref.get("source_label") or "", "source_url": ref.get("source_url"), "rights": ref.get("rights") or "unknown",
        "aspects": list(ref.get("aspects") or ["composition"]), "strength": ref.get("strength") or "mid",
        "role_label": role_label(list(ref.get("aspects") or ["composition"])), "analysis": ref.get("analysis"),
        "sanitized_file_id": ref.get("sanitized_file_id"), "send_mode": ref.get("send_mode"), "via": ref.get("via") or "picker",
        "strong_allowed": origin_kind != "upload", "created_at": ref.get("created_at") or "",
    }


# ── run · 시안 ───────────────────────────────────────────

STAGE_LABEL = {"product_fit": "제품 외형 맞춤", "compose": "장면 구성", "render": "렌더링", "qc": "품질 확인"}
STAGE_ORDER = ["product_fit", "compose", "render", "qc"]


def _elapsed(started_at: str | None) -> float | None:
    t = parse_iso(started_at)
    if t is None:
        return None
    return max(0.0, time.time() - t.timestamp())


def shot_progress(img: dict[str, Any]) -> tuple[int, int | None]:
    """(progress 0..100, eta_s) — 시안별 `min(0.95, 경과 ÷ 최근 지연 EMA)`(추정치)."""
    st = img.get("status")
    if st == "done":
        return 100, 0
    if st in ("waiting", "held", "canceled", "failed"):
        return 0, None
    exp = float(img.get("expected_s") or config.default_ema_s())
    el = _elapsed(img.get("started_at"))
    if el is None:
        return int(round(float(img.get("progress") or 0) * 100)), int(exp)
    frac = min(0.95, el / max(1.0, exp))
    if st == "composing":
        frac = min(frac, 0.45)
    if st == "qc":
        frac = max(frac, 0.9)
    return int(round(frac * 100)), int(max(0.0, exp - el))


def shot_view(img: dict[str, Any], *, wait_for: str | None = None, version: dict[str, Any] | None = None) -> dict[str, Any]:
    pct, eta = shot_progress(img)
    st = img.get("status") or "waiting"
    stage_label = {"waiting": "대기 중", "composing": "장면 구성 중", "rendering": "렌더링 중", "qc": "품질 확인 중",
                   "done": "완료", "held": "보류 · 대안 필요", "canceled": "취소됨", "failed": "실패"}.get(st, "")
    fid = (version or {}).get("master_file_id") or img.get("file_id")
    return {
        "image_id": img["id"], "index": int(img.get("index") or 1), "label": img.get("label") or "시안",
        "letter": img.get("letter"), "state": st, "stage_label": img.get("stage_label") or stage_label, "progress": pct,
        "eta_s": eta, "started_at": img.get("started_at"), "expected_s": img.get("expected_s"),
        "preview_url": thumb_url(img.get("preview_file_id"), 640) if img.get("preview_file_id") and st != "done" else None,
        "thumb_url": thumb_url(fid, 640) if fid and st == "done" else None,
        "url": content_url(fid) if fid and st == "done" else None,
        "aspect": img.get("aspect") or "16:9", "width": (version or {}).get("width") or img.get("width"),
        "height": (version or {}).get("height") or img.get("height"),
        "qc_flag": bool(img.get("qc_flag")), "qc_reason": img.get("qc_reason"), "layout_note": img.get("layout_note"),
        "wait_for": wait_for if st == "waiting" else None, "error": img.get("error"),
    }


def run_stages(run: dict[str, Any], shots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    phase = run.get("phase") or ("queued" if run.get("status") == "queued" else "product_fit")
    active = [s for s in shots if s.get("status") not in ("held", "canceled")]
    n = len(active)
    rendered = sum(1 for s in active if s.get("status") in ("qc", "done", "failed"))
    done_all = n > 0 and all(s.get("status") in ("done", "failed") for s in active)
    status = run.get("status")
    out = []
    for key in STAGE_ORDER:
        label = STAGE_LABEL[key]
        if key == "render":
            label = f"렌더링 {rendered} / {n}"
        if status == "succeeded" or done_all and phase in ("render", "qc", "done", "postprocess"):
            state = "done"
        elif phase == "queued" or status == "queued":
            state = "todo"
        else:
            pi = STAGE_ORDER.index(phase) if phase in STAGE_ORDER else (len(STAGE_ORDER) if phase in ("done", "postprocess") else 0)
            ki = STAGE_ORDER.index(key)
            if key == "qc" and phase == "render":
                state = "now" if any(s.get("status") == "qc" for s in active) else "todo"
            elif key == "render" and phase == "render" and rendered >= n and n > 0:
                state = "done"
            else:
                state = "done" if ki < pi else ("now" if ki == pi else "todo")
        out.append({"key": key, "label": label, "state": state})
    return out


def run_eta(shots: list[dict[str, Any]], conc: int) -> int | None:
    pend = [s for s in shots if s.get("status") in ("waiting", "composing", "rendering", "qc")]
    if not pend:
        return None
    running = [s for s in pend if s.get("status") != "waiting"]
    waiting = [s for s in pend if s.get("status") == "waiting"]
    rem = [shot_progress(s)[1] or 0 for s in running]
    exp = float((running or waiting)[0].get("expected_s") or config.default_ema_s())
    total = (max(rem) if rem else 0) + (len(waiting) / max(1, conc)) * exp
    return int(round(total))


def wait_for_label(shots: list[dict[str, Any]]) -> str | None:
    """대기 카드 「시안 {j}가 끝나면 시작해요」 — j = 진행 중 시안 중 가장 먼저 시작한 것."""
    started = [s for s in shots if s.get("status") in ("composing", "rendering", "qc") and s.get("started_at")]
    if not started:
        return None
    first = sorted(started, key=lambda s: s.get("started_at") or "")[0]
    lab = first.get("label") or f"시안 {first.get('index')}"
    return f"{lab}{texts.josa(lab, '이/가')} 끝나면 시작해요"


def run_view(run: dict[str, Any], shots: list[dict[str, Any]], *, versions: dict[str, dict[str, Any]] | None = None,
             queue_ahead: int | None = None) -> dict[str, Any]:
    shots = sorted(shots, key=lambda s: (int(s.get("index") or 0), s.get("created_at") or ""))
    versions = versions or {}
    wf = wait_for_label(shots)
    done = sum(1 for s in shots if s.get("status") == "done")
    total = len(shots) if shots else int(run.get("total") or 0)
    held = sum(1 for s in shots if s.get("status") == "held")
    eta = run_eta(shots, config.shot_concurrency())
    st = run.get("status")
    if st == "queued":
        head = f"대기 중 · 앞에 {queue_ahead}건" if queue_ahead else "대기 중"
    elif st == "succeeded":
        head = f"생성 완료 · {done} / {total}"
    else:
        head = f"생성 중 · {done} / {total} 완료"
    precheck = run.get("precheck") or {}
    return {
        "id": run["id"], "work_id": run["work_id"], "kind": run["kind"], "status": st, "job_id": run.get("job_id"),
        "notify": bool(run.get("notify", True)), "title": run.get("title") or "", "stages": run_stages(run, shots),
        "shots": [shot_view(s, wait_for=wf, version=versions.get(s.get("current_version_id") or "")) for s in shots],
        "done": done, "total": total, "held": held, "eta_s": eta, "eta_label": texts.remaining(eta) if eta is not None else "",
        "summary_line": run.get("summary_line") or "", "head": head, "issues": precheck.get("issues") or [],
        "applied_note": precheck.get("applied_note"),
        "change_note": (f"요청 중 {len(precheck.get('issues') or [])}가지를 바꿔서 만들었어요"
                        if precheck.get("issues") and not held and st in ("succeeded", "running") else None),
        "error": run.get("error"), "queue_ahead": queue_ahead,
        "base_image_id": run.get("base_image_id"), "params": run.get("params") or {}, "route": run_route(run),
        "created_at": run.get("created_at") or "", "started_at": run.get("started_at"), "finished_at": run.get("finished_at"),
    }


# ── 시안 · 버전 ──────────────────────────────────────────

def rendition_view(r: dict[str, Any]) -> dict[str, Any]:
    return {"kind": r["kind"], "w": int(r["w"]), "h": int(r["h"]), "file_id": r["file_id"], "method": r.get("method") or "",
            "url": content_url(r["file_id"]) or ""}


def version_view(v: dict[str, Any], *, image: dict[str, Any] | None = None) -> dict[str, Any]:
    label = v.get("label") or texts.version_label(int(v.get("n") or 1), v.get("op") or "generate")
    img_label = (image or {}).get("label") or "시안"
    title = texts.export_title(img_label, int(v.get("n") or 1), v.get("op") or "generate", (image or {}).get("aspect"))
    return {
        "id": v["id"], "image_id": v["image_id"], "n": int(v.get("n") or 1), "parent_version_id": v.get("parent_version_id"),
        "op": v.get("op") or "generate", "op_params": v.get("op_params") or {}, "label": label,
        "short_label": label.split(" · ")[0] if label else "", "title": title,
        "master_file_id": v["master_file_id"], "url": content_url(v["master_file_id"]) or "",
        "thumb_url": thumb_url(v["master_file_id"], 640) or "", "width": int(v.get("width") or 0), "height": int(v.get("height") or 0),
        "native": v.get("native") or {}, "renditions": [rendition_view(r) for r in v.get("renditions") or []],
        "generation": v.get("generation") or {}, "qc": v.get("qc") or {},
        "is_current": bool(image and image.get("current_version_id") == v["id"]), "created_at": v.get("created_at") or "",
    }


def gallery_meta(img: dict[str, Any], *, running: bool) -> str:
    parts = []
    if img.get("customer_short"):
        parts.append(img["customer_short"])
    parts.append(config.KIND_LABEL.get(img.get("kind") or "space", "공간"))
    parts.append("생성 중" if running else (img.get("aspect") or "16:9"))
    return " · ".join(parts)


def image_title(img: dict[str, Any]) -> str:
    """갤러리 제목 — 작업 주제 + 시안 라벨(예 메뉴보드 시안 1)."""
    subj = img.get("subject_short")
    lab = img.get("label") or "시안"
    if subj and not lab.startswith(subj):
        return f"{subj} {lab}"
    return lab


def image_tile(img: dict[str, Any], *, version: dict[str, Any] | None, run: dict[str, Any] | None,
               used_in_count: int) -> dict[str, Any]:
    running = img.get("status") in ("waiting", "composing", "rendering", "qc")
    fid = (version or {}).get("master_file_id")
    rb = run_brief(run) if running and run else None
    wid = img["work_id"]
    return {
        "id": img["id"], "title": image_title(img), "label": img.get("label") or "시안",
        "width": (version or {}).get("width"), "height": (version or {}).get("height"), "format": "PNG" if fid else None,
        "bytes": (version or {}).get("bytes"), "created_at": img.get("created_at") or "", "file_id": fid,
        "thumb_url": thumb_url(fid, 320) if fid else None, "kind": img.get("kind") or "space", "aspect": img.get("aspect") or "16:9",
        "customer_short": img.get("customer_short"), "status": img.get("status") or "waiting", "used_in_count": used_in_count,
        "origin": img.get("origin") or "image", "meta": gallery_meta(img, running=running), "work_id": wid,
        "run_id": img.get("run_id"), "current_version_id": img.get("current_version_id"),
        "progress_done": (rb or {}).get("done"), "progress_total": (rb or {}).get("total"),
        "route": route_result(wid, img["id"]), "run_route": rb["route"] if rb else None, "saved": bool(img.get("saved")),
    }
