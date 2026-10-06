"""데이터시트 읽기(06-spec §7.4 `spec_datasheet`) — 사용자가 올린 데이터시트(PDF · 이미지)로 빈 칸 채우기 · 값 대조.

값은 쪽 텍스트에 그대로 있는 원문(value_raw)만 쓴다(§7.11-1). 문서의 모델코드가 그 제품과 다르면 쓰지 않는다.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from winmate_common.ai import ai
from winmate_common.errors import ApiError

from . import config, ops, repo
from . import sheet as S
from .catalog import catalog
from .compliance import ai_error, load_pages, ocr_pages
from .generate import merge_warnings
from .rules import warnings as W
from .rules.compliance import norm_ws
from .rules.fmt import first_number, numbers
from .rules.values import catalog_candidate, is_complete, render_text, values_conflict

log = logging.getLogger("winmate.spec.datasheet")

EXTRACT_SCHEMA = {"type": "object", "properties": {
    "model_codes": {"type": "array", "items": {"type": "string"}},
    "rows": {"type": "array", "items": {"type": "object", "properties": {
        "group": {"type": "string"}, "name_raw": {"type": "string"}, "value_raw": {"type": "string"}, "page": {"type": "integer"}},
        "required": ["name_raw", "value_raw", "page"]}}}, "required": ["rows"]}

ROW_KEYS = ("size_resolution", "brightness_contrast", "operation_hours", "power", "player_os", "magicinfo", "warranty", "io_ports",
            "dimensions", "weight", "bezel", "certification", "accessories")


def kb_name(name: str, norm: str | None) -> str | None:
    """데이터시트 행 이름 → KB 모양 `그룹 › 속성`(카탈로그 값 고르기 규칙을 그대로 쓰기 위해)."""
    n = name.strip()
    low = n.lower()
    if norm == "brightness_nit" or re.search(r"밝기|brightness", n, re.I):
        return "디스플레이 › 밝기 (Typ)"
    if norm == "power_consumption" or re.search(r"소비전력|power", n, re.I):
        if re.search(r"max|최대", n, re.I):
            return "전원 › 소비전력 (Max)"
        if re.search(r"typical|typ|일반|정격", n, re.I):
            return "전원 › 소비전력 (Typical)"
        if re.search(r"on mode", n, re.I):
            return "전원 › 소비전력 (On Mode)"
        if re.search(r"sleep|대기|stand", n, re.I):
            return "전원 › 소비전력 (Sleep Mode)"
        return None
    if norm == "operation_hours" or re.search(r"사용 시간|operation|운영 시간", n, re.I):
        return "디스플레이 › 제품 사용 시간"
    if re.search(r"명암비|contrast", n, re.I):
        return "디스플레이 › 명암비"
    if norm == "resolution" or re.search(r"해상도|resolution", n, re.I):
        return "디스플레이 › 해상도"
    if norm in ("screen_size_cm",) or re.search(r"대각선|diagonal", n, re.I):
        return "디스플레이 › 대각선 사이즈 (cm)"
    if norm == "weight_kg" or re.search(r"무게|weight", n, re.I):
        return "무게 › 무게 (박스 포장)" if re.search(r"포장|박스|package|gross", n, re.I) else "무게 › 제품 무게"
    if re.search(r"운영체제|os\b|tizen", low):
        return "SoC › 운영체제 버전"
    if re.search(r"베젤|bezel", n, re.I):
        return "기구사양 › 베젤 두께"
    if re.search(r"vesa", n, re.I):
        return "기구사양 › VESA 마운트"
    if re.search(r"가로x높이|w\s*x\s*h|dimension|크기", n, re.I):
        return "크기 › 제품(가로x높이x깊이)"
    for k, kb in (("hdmi", "연결성 › HDMI 입력"), ("dp", "연결성 › DP 입력"), ("usb", "연결성 › USB"), ("rj45", "연결성 › RJ45 입력"),
                  ("wifi", "연결성 › WiFi"), ("wi-fi", "연결성 › WiFi"), ("bluetooth", "연결성 › Bluetooth")):
        if re.search(rf"\b{re.escape(k)}\b", low):
            return kb
    return None


def pseudo_spec(rows: list[dict[str, Any]], norms: dict[int, str | None], base: dict[str, Any] | None) -> dict[str, Any]:
    spec: dict[str, Any] = {"model_code": (base or {}).get("model_code"), "attrs": {}, "derived": {}, "solutions": [], "provides": [],
                            "category_id": (base or {}).get("category_id")}
    for i, r in enumerate(rows):
        kb = kb_name(r["name_raw"], norms.get(i))
        if kb and kb not in spec["attrs"]:
            spec["attrs"][kb] = {"raw": r["value_raw"], "num": first_number(r["value_raw"]), "num2": None, "unit": None,
                                 "id": f"ds:{r.get('page')}:{i}", "norm_key": norms.get(i), "page": r.get("page")}
        if re.search(r"보증|warranty", r["name_raw"], re.I):
            y = first_number(r["value_raw"])
            if y is not None:
                spec["warranty_catalog"] = {"years": y, "ref": f"ds:{r.get('page')}:{i}", "quote": r["value_raw"]}
    b = spec["attrs"].get("디스플레이 › 밝기 (Typ)")
    if b:
        spec["derived"]["brightness_typ_nit"] = first_number(b["raw"])
    for k, d in (("무게 › 제품 무게", "weight_kg_set"), ("무게 › 무게 (박스 포장)", "weight_kg_package")):
        if spec["attrs"].get(k):
            spec["derived"][d] = spec["attrs"][k]["num"]
    dm = spec["attrs"].get("크기 › 제품(가로x높이x깊이)")
    if dm:
        ns = numbers(dm["raw"])
        if len(ns) >= 2:
            spec["derived"]["dimensions_mm"] = {"w": ns[0], "h": ns[1], "d": ns[2] if len(ns) > 2 else None}
    return spec


async def run(sid: str, ds_id: str) -> dict[str, Any]:
    s = await repo.amust("sheets", sid)
    ds = next((d for d in s.get("datasheets") or [] if d["id"] == ds_id), None)
    if ds is None:
        raise ApiError(404, "NOT_FOUND", f"데이터시트를 찾을 수 없어요: {ds_id}")
    p = next((x for x in s.get("products") or [] if x["id"] == ds["product_id"]), None)
    if p is None:
        raise ApiError(404, "NOT_FOUND", "데이터시트의 제품이 시트에 없어요.")
    meta, pages = await load_pages(ds["file_id"])
    pages = await ocr_pages(ds["file_id"], pages)
    payload = {"pages": [{"page": x["page"], "text": x["text"][:6000]} for x in pages], "expected_model_code": p.get("model_code")}
    try:
        ex = await ai().json("sp.datasheet_extract", json.dumps(payload, ensure_ascii=False), EXTRACT_SCHEMA,
                             system="데이터시트에서 스펙 행(이름 · 값 원문 · 쪽)을 그대로 옮긴다. 값은 원문 그대로.", confidential=True)
    except Exception as exc:  # noqa: BLE001
        raise ai_error(exc) from exc
    texts = {x["page"]: norm_ws(x["text"]) for x in pages}
    alltext = norm_ws(" ".join(x["text"] for x in pages))
    codes = [c for c in ex.get("model_codes") or [] if c]
    names = {(p.get("model_code") or "").upper(), (p.get("display_name") or "").upper()} - {""}
    model_ok = not codes or any(any(n and (n in c.upper() or c.upper() in n) for n in names) for c in codes)
    rows = []
    for r in ex.get("rows") or []:
        v = norm_ws(r.get("value_raw") or "")
        if not v or not (v in texts.get(r.get("page"), "") or v in alltext):
            continue    # 쪽 텍스트에 없는 값은 쓰지 않는다
        rows.append({"group": r.get("group"), "name_raw": r.get("name_raw") or "", "value_raw": r.get("value_raw") or "", "page": r.get("page")})
    status = "done" if model_ok else "model_mismatch"
    norms: dict[int, str | None] = {}
    if rows and model_ok:
        try:
            env = await catalog().a3([{"name_raw": r["name_raw"], "value_raw": r["value_raw"]} for r in rows])
            by = {m.get("name_raw"): m.get("attr") for m in (env.get("result") or {}).get("mapped") or []}
            norms = {i: by.get(r["name_raw"]) for i, r in enumerate(rows)}
        except ApiError:
            norms = {}
    base_spec = await catalog().spec(p["model_code"]) if p.get("model_code") else None
    ps = pseudo_spec(rows, norms, base_spec) if model_ok else {"attrs": {}}
    ver = meta.get("name") or "데이터시트"
    values: dict[str, Any] = {}
    for rk in ROW_KEYS:
        c = catalog_candidate(rk, ps, ver)
        if c.value is None:
            continue
        srcs = []
        for src in c.sources:
            a = next((x for x in ps["attrs"].values() if x.get("id") == src.get("ref")), None)
            srcs.append({"kind": "datasheet", "label": "데이터시트", "version_or_date": meta.get("name") or "", "tier": "T1", "ref": ds["file_id"],
                         "page": (a or {}).get("page"), "quote": src.get("quote")})
        if rk == "warranty" and ps.get("warranty_catalog"):
            srcs = [{"kind": "datasheet", "label": "데이터시트", "version_or_date": meta.get("name") or "", "tier": "T1", "ref": ds["file_id"],
                     "quote": ps["warranty_catalog"].get("quote")}]
        values[rk] = {"value": c.value, "sources": srcs}

    def fn(x: dict[str, Any]) -> dict[str, int]:
        d = next((y for y in x.get("datasheets") or [] if y["id"] == ds_id), None)
        if d is None:
            return {"filled": 0, "mismatch": 0}
        d.update({"status": status, "pages": meta.get("page_count") or len(pages), "values": values, "rows": rows[:200], "name": meta.get("name") or d.get("name")})
        filled = mismatch = 0
        if status != "done":
            S.refresh_status(x, x["id"])
            return {"filled": 0, "mismatch": 0}
        cells = x.setdefault("cells", {})
        new_ws = []
        for r in S.rows_ordered(x):
            v = values.get(r["row_key"])
            if not v:
                continue
            key = S.ck(r["id"], p["id"])
            c = cells.get(key) or {}
            if c.get("state") == "edited":
                continue
            complete = is_complete(r["row_key"], v["value"])
            if c.get("state") in ("flag", "pending", "checking") or c.get("value") is None or not is_complete(r["row_key"], c.get("value")):
                if complete or c.get("value") is None:
                    cells[key] = {**c, "value": v["value"], "state": "ok", "sources": v["sources"]}
                    cells[key].pop("flag_text", None)
                    filled += 1
                    for chk in x.get("checks") or []:
                        if chk.get("status") == "open" and chk.get("row_id") == r["id"] and chk.get("product_id") == p["id"]:
                            chk["status"] = "answered"
                            chk["answer"] = {"datasheet_id": ds_id}
                continue
            if complete and values_conflict(r["row_key"], v["value"], c.get("value")) and x.get("generated_at"):
                cur_kind = (c.get("sources") or [{}])[0].get("kind", "catalog")
                choices = [{"key": "catalog" if cur_kind == "catalog" else cur_kind, "kind": cur_kind, "value": c.get("value"),
                            "value_text": render_text(r["row_key"], c.get("value"), S.fmt_of(x))[0], "sources": c.get("sources") or []},
                           {"key": f"datasheet:{ds_id}", "kind": "datasheet", "value": v["value"],
                            "value_text": render_text(r["row_key"], v["value"], S.fmt_of(x))[0], "sources": v["sources"]}]
                new_ws.append(W.value_mismatch_source(r, p, choices=choices, current_key=choices[0]["key"], other_kind="datasheet",
                                                      version=(x.get("catalog") or {}).get("version") or ""))
                mismatch += 1
        for chk in x.get("checks") or []:
            if chk.get("status") == "open" and chk.get("kind") == "missing_product" and chk.get("product_id") == p["id"] and filled:
                chk["status"] = "answered"
                chk["answer"] = {"datasheet_id": ds_id}
        if new_ws:
            merge_warnings(x, new_ws, kinds={"value_mismatch_source"}, close_missing=False)
        if filled or mismatch:
            S.bump_version(x, "datasheet")
        S.refresh_status(x, x["id"])
        return {"filled": filled, "mismatch": mismatch}

    saved, info = await repo.amutate("sheets", sid, fn)
    await ops.publish(saved)
    return {"sheet_id": sid, "datasheet_id": ds_id, "status": status, **info, "at": config.now_iso()}
