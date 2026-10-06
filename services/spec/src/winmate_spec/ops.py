"""API · 워커가 함께 쓰는 비동기 작업: 제품 해소 · 생애주기 · 미리 값 · 작업물 색인 · 알림 · 요구 원천."""
from __future__ import annotations

import logging
import re
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.jobs import jobs
from winmate_common.platform import register_item

from . import config, repo
from . import sheet as S
from .catalog import catalog, strip_ref
from .rules import text as T
from .rules.fmt import display_name_guess, series_size_of
from .rules.values import catalog_candidate

log = logging.getLogger("winmate.spec.ops")


# ── 제품 해소 ────────────────────────────────────────────

async def resolve_product(token: str, *, source: str, role: str = "proposed") -> dict[str, Any] | None:
    """ref · 모델코드 · mdl_ · fam_ · 표시명 → 시트 제품. 해소 안 되면 점선(직접 입력) 제품. 빈 글이면 None."""
    t = (token or "").strip()
    if not t:
        return None
    cat = catalog()
    if t.startswith("custom:"):
        name = t[len("custom:"):].strip()
        if not name:
            return None
        return S.custom_product(name, source=source, role=role)
    code = await cat.resolve(t)
    if code is None:
        name = strip_ref(t)
        return S.custom_product(name, source=source, role=role)
    spec = await cat.spec(code)
    if spec is None:
        return S.custom_product(strip_ref(t), source=source, role=role)
    ref = None
    if t.startswith("kb:model:"):
        ref = t
    return S.product_from_spec(spec, source=source, role=role, ref=ref)


async def compute_preview(sheet: dict[str, Any]) -> None:
    """제품마다 카탈로그 값(SP2 차이 문장 · `차이 있는 항목만`). 값은 카탈로그 원문 그대로."""
    cat = catalog()
    ver = await cat.version()
    codes = [p["model_code"] for p in sheet.get("products") or [] if p.get("model_code") and p.get("in_catalog", True)]
    specs = await cat.specs(codes) if codes else {}
    prev: dict[str, Any] = {}
    for p in sheet.get("products") or []:
        sp = specs.get(p.get("model_code") or "")
        if not sp:
            continue
        rows: dict[str, Any] = {}
        for rk in ("size_resolution", "brightness_contrast", "operation_hours", "power", "player_os", "magicinfo", "warranty", "io_ports",
                   "dimensions", "weight", "bezel", "certification", "accessories"):
            c = catalog_candidate(rk, sp, ver)
            if c.value is None and rk == "warranty":
                pol = cat.warranty_policy(sp)
                if pol and pol.get("years") is not None:
                    rows[rk] = {"years": pol["years"]}
                continue
            if c.value is not None:
                rows[rk] = c.value
        prev[p["id"]] = rows
    sheet["preview"] = prev


# ── 생애주기(§4.17.2) ────────────────────────────────────

def lifecycle_entry(key: str | None) -> dict[str, Any] | None:
    if not key:
        return None
    seed_lifecycle()
    return repo.get("lifecycle", key.upper())


_seeded: set[str] = set()


def seed_lifecycle() -> None:
    path = str(repo.store().path)
    if path in _seeded:
        return
    for e in config.lifecycle_seed():
        k = str(e.get("model_key") or "").upper()
        if k and repo.get("lifecycle", k) is None:
            repo.put("lifecycle", k, {"model_key": e.get("model_key"), "status": e.get("status", "discontinued"),
                                      "successor_model_code": e.get("successor_model_code"), "source_label": e.get("source_label") or "사내 제품 카탈로그",
                                      "as_of": str(e.get("as_of")) if e.get("as_of") else None, "note": e.get("note")})
    _seeded.add(path)


async def evaluate_lifecycle(p: dict[str, Any], spec: dict[str, Any] | None) -> dict[str, Any]:
    """순서: internal(픽스처) → (KB C5 없음) → spec 생애주기 표 → KB 존재 여부."""
    cat = catalog()
    keys = [p.get("model_code"), p.get("display_name")]
    internal = None
    for k in keys:
        if k:
            internal = cat.internal_lifecycle(k)
            if internal:
                break
    entry = None
    if not internal:
        for k in keys:
            entry = await repo.run(lifecycle_entry, k)
            if entry:
                break
    src = internal or entry
    if src:
        status = src.get("status") or "discontinued"
        succ_code = src.get("successor_model_code")
        successor = None
        if succ_code:
            sp = await cat.spec(succ_code) if await cat.resolve(succ_code) else None
            successor = {"model_code": (sp or {}).get("model_code") or succ_code, "display_name": (sp or {}).get("display_name") or succ_code,
                         "relation": _relation(p, sp)}
        return {"status": status if status in ("on_sale", "discontinued", "eol_planned") else "unknown",
                "source": src.get("source_label") or "사내 제품 카탈로그", "as_of": src.get("as_of"), "successor": successor,
                "sold_out": False}
    if spec is not None and spec.get("in_catalog", True) and p.get("in_catalog", True):
        return {"status": "on_sale", "source": "KB(samsung.com 수집) — 목록 노출 = 판매 중(DR09)", "as_of": (await cat.meta()).get("fetched_at"),
                "successor": None, "sold_out": bool(spec.get("sold_out"))}
    return {"status": "unknown", "source": "사내 카탈로그에 없음", "as_of": None, "successor": None, "sold_out": False}


def _relation(p: dict[str, Any], succ: dict[str, Any] | None) -> str:
    ss = series_size_of(p.get("display_name")) or series_size_of(p.get("model_code"))
    if ss:
        return f'같은 {ss[1]}" {ss[0]} 라인업'
    if succ and succ.get("size_inch"):
        return f'같은 {succ["size_inch"]}" 라인업'
    return "후속 모델"


async def replacement_for(p: dict[str, Any], lifecycle: dict[str, Any], sheet: dict[str, Any]) -> dict[str, Any] | None:
    """현행 대체 모델: 후속 → (없으면) 같은 시리즈 · 같은 크기 판매 중 모델 중 출시가 가장 최근(제안, 결정적)."""
    cat = catalog()
    succ = lifecycle.get("successor")
    code = succ.get("model_code") if succ else None
    label = succ.get("display_name") if succ else None
    relation = succ.get("relation") if succ else None
    if not code:
        ss = series_size_of(p.get("display_name")) or series_size_of(display_name_guess(p.get("display_name") or "") or "")
        if not ss:
            return None
        series, size = ss
        try:
            items = await cat.search(f"{series}{size}", limit=10, kinds="model")
        except ApiError:
            items = []
        cands = []
        for it in items:
            dn = (it.get("display_name") or "").upper()
            if it.get("model_code") and dn.startswith(f"{series}{size}") and dn != (p.get("display_name") or "").upper():
                cands.append(it["model_code"])
        if not cands:
            return None
        specs = await cat.specs(cands)
        best = sorted(specs.values(), key=lambda s: (-(s.get("release_num") or 0), s.get("model_code") or ""))
        if not best:
            return None
        code, label = best[0]["model_code"], best[0]["display_name"]
        relation = f'같은 {size}" {series} 라인업'
    in_sheet = any(x.get("model_code") == code for x in sheet.get("products") or [] if x["id"] != p["id"])
    return {"label": label, "relation_text": relation or "후속 모델", "already_in_sheet": in_sheet, "model_code": code}


# ── 작업물 색인 · 알림 ─────────────────────────────────────

async def publish(sheet: dict[str, Any]) -> None:
    """상태가 바뀔 때마다 workspace 항목(§3.6). 보관된 시트는 목록에서 빠진다."""
    sid = sheet["id"]
    ui, text, route = T.status_of(sheet, sid)
    if sheet.get("archived_at"):
        try:
            await ServiceClient("workspace").delete(f"/v1/items/{sid}")
        except Exception as exc:  # noqa: BLE001
            log.warning("workspace 항목 삭제 실패 %s: %s", sid, exc)
        return
    await register_item(feature=config.FEATURE, item_id=sid, title=T.display_title(sheet), status=ui, route=route, summary=text,
                        project_id=sheet.get("project_id"),
                        meta={"kind": sheet.get("kind"), "models": [p.get("display_name") for p in S.products_ordered(sheet)][:8],
                              "version": sheet.get("doc_version", 0), "customer": sheet.get("customer_name")})


async def notify(owner: str | None, data: dict[str, Any]) -> None:
    if not owner:
        return
    try:
        await jobs().push_notification(owner, {"service": config.SERVICE, **data})
    except Exception as exc:  # noqa: BLE001
        log.warning("알림 실패: %s", exc)


def user() -> tuple[str, str]:
    u = current_user()
    return u.id, u.name


# ── 잡 상태 맞추기 ───────────────────────────────────────

async def reconcile_job(sheet: dict[str, Any]) -> dict[str, Any]:
    """시트에 남은 active_job 이 이미 끝났으면(취소 · 실패 · 워커 밖에서 끝남) 시트 상태를 맞춘다."""
    aj = sheet.get("active_job")
    if not aj:
        return sheet
    try:
        job = await jobs().get(aj["id"])
    except Exception:  # noqa: BLE001
        return sheet
    if job is None or job.status in ("succeeded", "failed", "canceled"):
        status = job.status if job else "failed"

        def fix(s: dict[str, Any]) -> None:
            cur = s.get("active_job") or {}
            if cur.get("id") != aj["id"]:
                return
            s["active_job"] = None
            if status == "canceled" and cur.get("kind") == "spec_generate":
                restore_backup(s)
                s["step"] = 2
            if status == "failed":
                s["last_error"] = (job.error or {}).get("message") if job else "작업을 마치지 못했어요."
                if cur.get("kind") == "spec_generate":
                    restore_backup(s)
            if cur.get("kind") == "spec_find" and s.get("finder"):
                s["finder"]["status"] = "done" if status == "succeeded" else "failed"
            if cur.get("kind") == "spec_compliance" and s.get("compliance"):
                if s["compliance"].get("status") == "running":
                    s["compliance"]["status"] = "failed" if status != "succeeded" else "done"
            S.refresh_status(s, s["id"])

        sheet, _ = await repo.amutate("sheets", sheet["id"], fix)
        await publish(sheet)
    elif job.status in ("queued", "running"):
        sheet["active_job"] = {**aj, "status": job.status, "progress": job.progress}
    return sheet


def restore_backup(s: dict[str, Any]) -> None:
    b = s.pop("gen_backup", None)
    if b is None:
        return
    for k in ("cells", "checks", "rows", "generated_at"):
        if k in b:
            s[k] = b[k]


# ── 요구 원천(requirements 정의서, 01-requirements §5.8 · §5.9) ──

async def requirement_items(sheet: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """연결된 정의서(스냅숏) 항목. 돌려줌: ([{id, code, text, short, entities, source_kind}], {rq_id, version}). 없으면 ([], None)."""
    rq_ref = sheet.get("rq_ref") or {}
    rq_id = rq_ref.get("rq_id") or rq_ref.get("id")
    version = rq_ref.get("version") or "latest"
    client = ServiceClient("requirements", timeout=30)
    try:
        if not rq_id and sheet.get("project_id"):
            lst = await client.get("/v1/requirements", params={"project_id": sheet["project_id"], "has_version": True, "owner": "all", "limit": 5})
            items = lst.get("items") or []
            if items:
                rq_id = items[0]["id"]
        if not rq_id:
            return [], None
        snap = await client.get(f"/v1/requirements/{rq_id}/versions/{version}")
    except (ApiError, Exception) as exc:  # noqa: BLE001 — 요구 원천은 선택(없으면 기본 7개만)
        log.info("requirements 원천 없음: %s", exc)
        return [], None
    out = []
    files = {f.get("file_id"): f for f in (snap.get("snapshot") or {}).get("source_files") or []}
    for it in (snap.get("snapshot") or {}).get("items_flat") or []:
        src = it.get("source") or {}
        kind = src.get("kind") or ("file" if files or it.get("evidence") else "user")
        out.append({"id": it.get("id"), "code": it.get("code"), "text": it.get("text") or "", "short": it.get("short"),
                    "entities": it.get("entities") or [], "source_kind": kind})
    return out, {"rq_id": rq_id, "version": snap.get("version")}


async def register_rq_link(sheet: dict[str, Any], ref: dict[str, Any] | None, used_item_ids: list[str]) -> None:
    if not ref or not ref.get("rq_id"):
        return
    try:
        await ServiceClient("requirements", timeout=20).put(
            f"/v1/requirements/{ref['rq_id']}/links/spec/{sheet['id']}",
            json={"title": T.display_title(sheet), "route": f"/spec/{sheet['id']}", "rq_version": int(ref.get("version") or 1),
                  "depends_on": [{"target": {"kind": "item", "id": i}, "places": [{"label": "Spec 시트"}]} for i in used_item_ids[:50]]})
    except Exception as exc:  # noqa: BLE001
        log.info("requirements 링크 등록 실패: %s", exc)


_SPECY = re.compile(r"\d|인치|nit|cd|W\b|kg|24시간|보증|해상도|UHD|FHD|4K|8K|밝기|소비전력|무게|운영", re.I)


async def requirement_rules_from_definition(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """정의서 항목 → 스펙성 요구(A3 로 정규 키가 붙는 것 + A1 역량)."""
    if not items:
        return []
    cat = catalog()
    cand = [it for it in items if _SPECY.search(it.get("text") or "") or any(e.get("type") == "capability" for e in it.get("entities") or [])]
    if not cand:
        return []
    try:
        a3 = await cat.a3([{"name_raw": (it.get("short") or it.get("text") or "")[:60], "value_raw": it.get("text") or ""} for it in cand])
        mapped = (a3.get("result") or {}).get("mapped") or []
    except ApiError:
        mapped = []
    by_name = {}
    for m in mapped:
        by_name.setdefault(m.get("name_raw"), m)
    rules = []
    from .rules.compliance import op_of
    for it in cand:
        caps = [e["id"] for e in it.get("entities") or [] if e.get("type") == "capability"]
        text = it.get("text") or ""
        if not caps:
            try:     # 정의서에 개체 연결이 아직 없으면 KB A1 로(결정적)
                env = await cat.a1(text)
                caps = [x["id"] for x in (env.get("result") or {}).get("links") or [] if x.get("type") == "capability"]
            except ApiError:
                caps = []
        if re.search(r"24\s*시간|24/7|상시", text) and "cap_continuous_operation" not in caps:
            caps.insert(0, "cap_continuous_operation")
        if re.search(r"원격|일괄 배포|콘텐츠 관리|CMS", text) and "cap_remote_content_mgmt" not in caps:
            caps.append("cap_remote_content_mgmt")
        m = by_name.get((it.get("short") or it.get("text") or "")[:60])
        key = m.get("attr") if m else None
        if key and key not in ("screen_size_inch", "screen_size_cm", "brightness_nit", "operation_hours", "weight_kg", "power_consumption"):
            key = None
        if not key and not caps:
            continue
        summary = it.get("short") or (it.get("text") or "")[:24]
        rules.append({"id": it["id"], "label": summary, "kind": "capability" if caps else "numeric", "key": key,
                      "op": op_of(it.get("text") or ""), "value": (m or {}).get("value"), "capabilities": caps,
                      "source_label": "RFP" if it.get("source_kind") == "file" else "요구사항 정의서", "text": it.get("text")})
    return rules
