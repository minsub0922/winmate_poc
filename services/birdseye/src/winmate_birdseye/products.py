"""배치될 제품(08-birdseye §4.5 · §6.3) — kb 검색을 표시용으로 가공, 제품 목록(치수 · 크기 옵션 · 역할)."""
from __future__ import annotations

from typing import Any

from winmate_common.ids import new_id

from . import kbapi
from . import service as svc
from .repo import repo


async def search(q: str, limit: int = 5) -> list[dict[str, Any]]:
    if not q or not q.strip():
        return []
    return await kbapi.search(q.strip(), limit)


def _key(p: dict[str, Any]) -> str:
    return (p.get("model_code") or "") + "|" + (p.get("family_id") or "")


async def put_products(be_id: str, picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """목록을 통째로 바꾼다(빠진 제품은 지운다). 이미 있는 제품은 다시 kb 를 부르지 않는다."""
    await svc.get(be_id)
    cur = await svc.products(be_id)
    by_key = {_key(p): p for p in cur}
    keep_ids = set()
    out = []
    for order, pick in enumerate(picks):
        ref = pick.get("ref") or ""
        model_code = pick.get("model_code")
        if not model_code and ref.startswith("kb:model:"):
            model_code = ref.split(":", 2)[2].removeprefix("mdl_")
        family_id = pick.get("family_id")
        if not family_id and ref.startswith("kb:family:"):
            family_id = ref.split(":", 2)[2]
        k = (model_code or "") + "|" + (family_id or "")
        hit = by_key.get(k) or next((p for p in cur if model_code and p.get("model_code") == model_code), None) \
            or next((p for p in cur if not model_code and family_id and p.get("family_id") == family_id and not p.get("model_code")), None)
        if hit is not None:
            if hit.get("order") != order:
                hit = await repo().put("products", hit["id"], {**hit, "order": order})
            keep_ids.add(hit["id"])
            out.append(hit)
            continue
        data = await kbapi.resolve_product({"family_id": family_id, "model_code": model_code, "ref": ref, "label": pick.get("label")}, order)
        pid = new_id("bpi")
        doc = {"birdseye_id": be_id, **data}
        saved = await repo().put("products", pid, doc)
        keep_ids.add(pid)
        out.append(saved)
    for p in cur:
        if p["id"] not in keep_ids:
            await repo().delete("products", p["id"])
    # 단계는 공간 분석이 끝날 때 2 가 된다(미리 채운 제품이 단계를 건너뛰게 하지 않는다).
    await svc.index(be_id)
    return [view(p) for p in out]


def view(p: dict[str, Any]) -> dict[str, Any]:
    return {k: p.get(k) for k in ("id", "birdseye_id", "family_id", "model_code", "ref", "display_name", "short", "size_options",
                                  "chosen_size", "dims_m", "dims_source", "diag_inch", "category", "role", "mount_default", "order",
                                  "models_by_size", "dims_by_size")} | {
        "size_options": p.get("size_options") or [], "models_by_size": p.get("models_by_size") or {},
        "dims_by_size": p.get("dims_by_size") or {}, "category": p.get("category") or "", "order": p.get("order") or 0,
        "family_id": p.get("family_id") or "", "ref": p.get("ref") or "", "dims_source": p.get("dims_source") or "estimated",
        "role": p.get("role") or "display", "mount_default": p.get("mount_default") or "wall",
    }


def echo_line(products: list[dict[str, Any]]) -> str:
    """BE3 메아리 「제품 {n}개 · {표시명 ' / '}」."""
    if not products:
        return ""
    return f"제품 {len(products)}개 · {' / '.join(p.get('display_name') or p.get('short') or '' for p in products)}"


async def products_view(be_id: str) -> dict[str, Any]:
    """BE2 — 추가된 제품 칩 + 공간 W · 요약 칩 · 메아리."""
    from . import inputs

    sv = await inputs.space_view(be_id)
    items = [view(p) for p in await svc.products(be_id)]
    return {"items": items, "w_message": sv["w_message"], "chips": sv["summary_chips"], "echo": sv["echo"], "files": sv["files"],
            "analyzing": sv["analyzing"]}
