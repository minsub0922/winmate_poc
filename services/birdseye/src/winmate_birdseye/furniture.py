"""가구 추천 · 선택(08-birdseye §4.6 · §10.4).

- 추천: LLM(be.furniture_recommend, 닫힌 카탈로그 순위) → 막히면 규칙 표(furniture:rules). 카드 4개, 첫 추천만 상위 3개 미리 선택.
- 이유 줄 「{앵커 위치} · {목적}」 — 시청 거리 같은 수치는 엔진이 계산(ceil_0.5(대각 m × 1.5)).
- 직접 입력: 카탈로그 별칭 → LLM(be.furniture_match) → 없으면 사용자 가구(1.0×0.6×0.8 m, 「· 치수 추정」).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from winmate_common.ids import new_id

from . import config, llm
from . import service as svc
from . import text as T
from .engine import seat_distance, tiny_of
from .repo import repo


class RecItem(BaseModel):
    code: str
    why: str = ""


class RecOut(BaseModel):
    items: list[RecItem] = Field(default_factory=list)


class MatchOut(BaseModel):
    code: str | None = None


def _largest_display(products: list[dict[str, Any]]) -> dict[str, Any] | None:
    disp = [p for p in products if p.get("role") in ("led_wall", "display", "interactive")]
    if not disp:
        return None

    def size(p: dict[str, Any]) -> float:
        from .engine import size_inch

        sizes = [size_inch(s) or 0 for s in p.get("size_options") or []]
        return max([p.get("diag_inch") or 0] + sizes)

    return max(disp, key=lambda p: (size(p), -p.get("order", 0)))


def _interactive(products: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((p for p in products if p.get("role") == "interactive"), None)


def conditions(b: dict[str, Any], model: dict[str, Any] | None, products: list[dict[str, Any]]) -> set[str]:
    m = model or {}
    out = {"always", f"chip_{b.get('space_chip') or 'store_lobby'}"}
    if any(o.get("kind") == "window" and o.get("faces_outdoor") for o in m.get("openings", [])):
        out.add("window_outdoor")
    if m.get("columns"):
        out.add("columns")
    big = _largest_display(products)
    if big is not None:
        from .engine import size_inch

        sz = max([big.get("diag_inch") or 0] + [size_inch(s) or 0 for s in big.get("size_options") or []])
        if big.get("role") == "led_wall" or sz >= 75:
            out.add("large_display")
    if _interactive(products):
        out.add("interactive_display")
    return out


def rule_ranking(b: dict[str, Any], model: dict[str, Any] | None, products: list[dict[str, Any]]) -> list[str]:
    conds = conditions(b, model, products)
    scored: dict[str, int] = {}
    for r in config.catalog()["recommend_rules"]:
        if r["when"] in conds:
            scored[r["code"]] = max(scored.get(r["code"], 0), int(r["score"]))
    if "columns" not in conds:
        scored.pop("column_wrap_frame", None)
    return [c for c, _ in sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))]


def reason(code: str, b: dict[str, Any], model: dict[str, Any] | None, products: list[dict[str, Any]]) -> str:
    """「{앵커 위치} · {목적}」."""
    item = config.catalog_item(code) or {}
    purpose = item.get("purpose") or ""
    m = model or {}
    big = _largest_display(products)
    if code == "lounge_sofa_set" or code == "table_set":
        wins = [o for o in m.get("openings", []) if o.get("kind") == "window"]
        where = "유리창 앞" if any(o.get("faces_outdoor") for o in wins) else ("창가" if wins else "입구 쪽")
        return f"{where} · {purpose}"
    if code == "column_wrap_frame":
        return f"기둥 {len(m.get('columns', []))}개 · {purpose}"
    if code in ("viewing_bench", "meeting_table", "operator_desk"):
        if big is None:
            return f"빈 영역 · {purpose.format(d='—', rows=item.get('rows') or 1)}"
        from .engine import size_inch

        diag = big.get("diag_inch") or max([size_inch(s) or 0 for s in big.get("size_options") or []] or [0])
        d = seat_distance(diag, config.rules()) if diag else None
        name = tiny_of(big.get("short") or big.get("display_name") or "디스플레이")
        return f"{name} 정면 · {purpose.format(d=T.num(d) if d else '—', rows=item.get('rows') or 1)}"
    if code == "experience_counter":
        tgt = _interactive(products) or big
        name = tiny_of(tgt.get("short") or "") if tgt else "디스플레이"
        return f"{name} 앞 · {purpose}"
    if code == "info_desk":
        return f"주출입구 옆 · {purpose}"
    if code == "plant":
        return f"모서리 · {purpose}"
    if code == "display_shelf":
        return f"빈 벽 · {purpose}"
    return purpose


def summary_phrase(code: str, products: list[dict[str, Any]], model: dict[str, Any] | None) -> str:
    big = _largest_display(products)
    big_name = tiny_of(big.get("short") or "") if big else ""
    m = model or {}
    if code == "lounge_sofa_set":
        wins = [o for o in m.get("openings", []) if o.get("kind") == "window"]
        return ("유리창 앞 라운지" if any(o.get("faces_outdoor") for o in wins) else "창가 라운지") if wins else "라운지 소파"
    if code == "column_wrap_frame":
        return "기둥 랩핑 프레임"
    if code == "viewing_bench":
        return f"{big_name} 앞 관람 벤치" if big_name else "관람 벤치"
    if code == "experience_counter":
        tgt = _interactive(products) or big
        return f"{tiny_of(tgt.get('short') or '')} 앞 체험 카운터" if tgt else "체험 카운터"
    if code == "info_desk":
        return "입구 안내 데스크"
    if code == "operator_desk":
        return f"{big_name} 정면 운영석" if big_name else "운영석"
    if code == "meeting_table":
        return f"{big_name} 앞 회의 테이블" if big_name else "회의 테이블"
    item = config.catalog_item(code) or {}
    return item.get("name") or code


def w_message(codes: list[str], products: list[dict[str, Any]], model: dict[str, Any] | None) -> str:
    phrases = [summary_phrase(c, products, model) for c in codes[:3]]
    if not phrases:
        return "공간 특징과 제품 배치를 살리는 가구를 추천합니다. 넣을 가구를 고르거나 직접 추가하세요."
    joined = ", ".join(phrases)
    return f"공간 특징과 제품 배치를 살리는 가구를 추천합니다. {joined}{T.josa(phrases[-1], '이/가')} 핵심입니다. 넣을 가구를 고르거나 직접 추가하세요."


def default_qty(code: str, model: dict[str, Any] | None) -> tuple[int, int | None]:
    item = config.catalog_item(code) or {}
    if code == "column_wrap_frame":
        return max(1, len((model or {}).get("columns", []))), None
    if item.get("rows"):
        return 1, int(item["rows"])
    return 1, None


def display_name(code: str, rows: int | None) -> str:
    item = config.catalog_item(code) or {}
    name = item.get("name") or code
    if rows:
        return f"{name} ({rows}열)"
    return name


def chip_label(f: dict[str, Any]) -> str:
    name = f.get("name") or ""
    tail = f" ×{f['qty']}" if int(f.get("qty") or 1) > 1 else ""
    est = " · 치수 추정" if f.get("dims_estimated") else ""
    return f"{name}{tail}{est}"


def _item_doc(be_id: str, code: str, *, selected: bool, rank: int | None, reason_line: str, model: dict[str, Any] | None,
              source: str = "recommended") -> dict[str, Any]:
    item = config.catalog_item(code) or {}
    qty, rows = default_qty(code, model)
    h = float(item.get("h") or 0.8)
    if code == "column_wrap_frame":
        h = max(0.5, float(((model or {}).get("ceiling_h") or {}).get("value") or 3.0) - 0.3)
    return {
        "birdseye_id": be_id, "catalog_code": code, "name": display_name(code, rows), "short": item.get("short") or item.get("name"),
        "tiny": item.get("tiny") or item.get("short"), "qty": qty, "rows": rows, "reason": reason_line, "source": source,
        "dims_m": {"w": float(item.get("w") or 1.0), "d": float(item.get("d") or 0.6), "h": round(h, 2)}, "dims_estimated": False,
        "selected": selected, "rec_rank": rank, "anchor": item.get("anchor") or "free", "zone": item.get("zone"),
        "parts": item.get("parts") or [], "wrap_margin_m": item.get("wrap_margin_m"),
    }


async def recommend(be_id: str, exclude: list[str]) -> dict[str, Any]:
    """다음 4개(보인 것 제외). 첫 추천이면 상위 3개 미리 선택."""
    b = await svc.get(be_id)
    model = await svc.space_model(be_id)
    products = await svc.products(be_id)
    ranking = rule_ranking(b, model, products)
    path = "furniture:rules"
    catalog_codes = [it["code"] for it in config.catalog()["items"]]
    prompt = (f"공간: {b.get('description') or b.get('space_label')}\n특징: {', '.join(f['label'] for f in (model or {}).get('features', []))}\n"
              f"기둥 {len((model or {}).get('columns', []))}개\n제품: {', '.join(p.get('display_name', '') for p in products)}\n"
              f"카탈로그(이 코드만): {', '.join(catalog_codes)}\n공간 특징과 제품 배치를 살리는 순서로 코드를 고른다.")
    try:
        res = await llm.json_task("be.furniture_recommend", prompt, RecOut, confidential=True)
    except llm.ModelBlocked:
        res = None
    if res and res.get("items"):
        codes = []
        for it in res["items"]:
            c = it.get("code")
            if c in catalog_codes and c not in codes:
                if c == "column_wrap_frame" and not (model or {}).get("columns"):
                    continue
                codes.append(c)
        if len(codes) >= 2:
            ranking = codes + [c for c in ranking if c not in codes]
            path = "furniture:llm"
    prev = b.get("recommendations") or {}
    first = not prev.get("shown")
    shown_before = list(dict.fromkeys((prev.get("history") or []) + list(exclude or [])))
    nxt = [c for c in ranking if c not in shown_before][:4] if not first else ranking[:4]
    if not nxt:
        nxt = [c for c in ranking if c not in (exclude or [])][:4]
    cur = await svc.furniture(be_id)
    by_code = {f.get("catalog_code"): f for f in cur if f.get("catalog_code")}
    for rank, code in enumerate(nxt, start=1):
        line = reason(code, b, model, products)
        if code in by_code:
            f = by_code[code]
            await repo().put("furniture", f["id"], {**f, "reason": line, "rec_rank": rank})
            continue
        doc = _item_doc(be_id, code, selected=first and rank <= 3, rank=rank, reason_line=line, model=model)
        doc["order"] = len(cur) + rank
        await repo().put("furniture", new_id("bfi"), doc)
    recs = {"shown": nxt, "history": list(dict.fromkeys(shown_before + nxt)), "ranking": ranking, "path": path,
            "w_codes": (prev.get("w_codes") or ranking[:3]) if not first else nxt[:3]}
    await svc.touch(be_id, recommendations=recs, furniture_none=False)
    b = await svc.get(be_id)
    if int(b.get("step") or 1) < 3:
        await svc.set_step(be_id, 3)
    await svc.index(be_id)
    return recs


async def match_name(name: str) -> str | None:
    n = (name or "").strip().replace(" ", "")
    if not n:
        return None
    for it in config.catalog()["items"]:
        names = [it["name"], it.get("short") or ""] + list(it.get("aliases") or [])
        for x in names:
            if x and x.replace(" ", "") == n:
                return it["code"]
    for it in config.catalog()["items"]:
        names = [it["name"], it.get("short") or ""] + list(it.get("aliases") or [])
        if any(x and len(x) >= 2 and (x.replace(" ", "") in n) for x in names):
            return it["code"]
    codes = [it["code"] for it in config.catalog()["items"]]
    try:
        res = await llm.json_task("be.furniture_match", f"가구 이름: {name}\n카탈로그 코드: {', '.join(codes)}\n같은 가구면 코드, 아니면 null.",
                                  MatchOut, confidential=False, timeout=15)
    except llm.ModelBlocked:
        res = None
    code = (res or {}).get("code")
    return code if code in codes else None


async def put(be_id: str, items: list[dict[str, Any]], none: bool, replace: bool = True) -> list[dict[str, Any]]:
    b = await svc.get(be_id)
    model = await svc.space_model(be_id)
    products = await svc.products(be_id)
    cur = await svc.furniture(be_id)
    by_id = {f["id"]: f for f in cur}
    by_code = {f.get("catalog_code"): f for f in cur if f.get("catalog_code")}
    touched = set()
    if none:
        for f in cur:
            if f.get("selected"):
                await repo().put("furniture", f["id"], {**f, "selected": False})
        await svc.touch(be_id, furniture_none=True)
        return [view(f) for f in await svc.furniture(be_id)]
    for it in items:
        f = by_id.get(it.get("id") or "") or (by_code.get(it.get("catalog_code")) if it.get("catalog_code") else None)
        if f is None and it.get("name") and not it.get("catalog_code"):
            code = await match_name(it["name"])
            if code:
                f = by_code.get(code)
                if f is None:
                    doc = _item_doc(be_id, code, selected=True, rank=None, reason_line=reason(code, b, model, products), model=model,
                                    source="user")
                    doc["order"] = len(cur) + len(touched) + 1
                    saved = await repo().put("furniture", new_id("bfi"), doc)
                    by_code[code] = saved
                    f = saved
            else:
                dflt = config.catalog()["custom_default"]
                doc = {"birdseye_id": be_id, "catalog_code": None, "name": T.clip(it["name"], 20), "short": T.clip(it["name"], 20),
                       "tiny": T.clip(it["name"], 10), "qty": int(it.get("qty") or 1), "rows": None, "reason": "직접 입력",
                       "source": "custom", "dims_m": {"w": float(dflt["w"]), "d": float(dflt["d"]), "h": float(dflt["h"])},
                       "dims_estimated": True, "selected": True, "rec_rank": None, "anchor": "free", "zone": None, "parts": [],
                       "order": len(cur) + len(touched) + 1}
                saved = await repo().put("furniture", new_id("bfi"), doc)
                touched.add(saved["id"])
                continue
        if f is None and it.get("catalog_code"):
            code = it["catalog_code"]
            if config.catalog_item(code) is None:
                continue
            doc = _item_doc(be_id, code, selected=bool(it.get("selected", True)), rank=None,
                            reason_line=reason(code, b, model, products), model=model, source="user")
            doc["order"] = len(cur) + len(touched) + 1
            f = await repo().put("furniture", new_id("bfi"), doc)
        if f is None:
            continue
        upd = {**f, "selected": bool(it.get("selected", True))}
        if it.get("qty"):
            upd["qty"] = int(it["qty"])
        if it.get("rows"):
            upd["rows"] = int(it["rows"])
            upd["name"] = display_name(f.get("catalog_code") or "", upd["rows"]) if f.get("catalog_code") else f["name"]
        await repo().put("furniture", f["id"], upd)
        touched.add(f["id"])
    if replace:
        for f in await svc.furniture(be_id):
            if f["id"] not in touched and f.get("selected") and f.get("source") != "custom":
                await repo().put("furniture", f["id"], {**f, "selected": False})
            elif f["id"] not in touched and f.get("source") == "custom" and f.get("selected"):
                # 직접 넣은 가구는 목록에 없으면 지운다
                await repo().delete("furniture", f["id"])
    await svc.touch(be_id, furniture_none=False)
    return [view(f) for f in await svc.furniture(be_id)]


def view(f: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f["id"], "birdseye_id": f["birdseye_id"], "catalog_code": f.get("catalog_code"), "name": f.get("name", ""),
        "short": f.get("short") or "", "tiny": f.get("tiny") or "", "qty": int(f.get("qty") or 1), "rows": f.get("rows"),
        "reason": f.get("reason") or "", "source": f.get("source") or "recommended", "dims_m": f.get("dims_m") or {"w": 1, "d": 0.6, "h": 0.8},
        "dims_estimated": bool(f.get("dims_estimated")), "selected": bool(f.get("selected")), "rec_rank": f.get("rec_rank"),
        "chip_label": chip_label(f),
    }


async def furniture_view(be_id: str, job_id: str | None = None, running: bool = False) -> dict[str, Any]:
    from . import products as P

    b = await svc.get(be_id)
    model = await svc.space_model(be_id)
    products = await svc.products(be_id)
    cur = await svc.furniture(be_id)
    recs = b.get("recommendations") or {}
    shown = recs.get("shown") or []
    by_code = {f.get("catalog_code"): f for f in cur if f.get("catalog_code")}
    cards = []
    for rank, code in enumerate(shown, start=1):
        f = by_code.get(code)
        cards.append({"code": code, "name": f["name"] if f else display_name(code, default_qty(code, model)[1]),
                      "reason": (f or {}).get("reason") or reason(code, b, model, products), "rank": rank,
                      "selected": bool(f and f.get("selected")), "qty": int((f or {}).get("qty") or 1), "rows": (f or {}).get("rows"),
                      "item_id": f["id"] if f else None})
    selected = [view(f) for f in cur if f.get("selected")]
    more = len([c for c in recs.get("ranking") or [] if c not in (recs.get("history") or [])]) > 0
    return {"cards": cards, "selected": selected, "shown_codes": shown,
            "w_message": w_message(recs.get("w_codes") or shown, products, model) if shown else "공간 특징에 맞는 가구를 고르고 있어요",
            "echo": P.echo_line(products), "running": running, "job_id": job_id, "none": bool(b.get("furniture_none")),
            "more_available": more or not recs}


def engine_furniture(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """엔진 입력 모양(선택된 것만)."""
    out = []
    for f in items:
        if not f.get("selected"):
            continue
        out.append({"id": f["id"], "catalog_code": f.get("catalog_code"), "name": f.get("name"), "short": f.get("short"),
                    "tiny": f.get("tiny"), "qty": int(f.get("qty") or 1), "rows": f.get("rows"), "anchor": f.get("anchor") or "free",
                    "zone": f.get("zone"), "dims_m": f.get("dims_m"), "parts": f.get("parts") or [], "selected": True,
                    "source": f.get("source"), "order": f.get("order", 0), "wrap_margin_m": f.get("wrap_margin_m")})
    return out
