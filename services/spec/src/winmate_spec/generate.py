"""시트 생성 단계(06-spec §7.3 `spec_generate`) · 값 확인 답 반영 · 경고 만들기.

단계(SP3G 5단계, 진행 가중치 10 · 30 · 40 · 10 · 10)
  1 resolve_models  모델 확인     — 카탈로그 모델 · 생애주기 · 후속/대체
  2 fetch_specs     스펙 가져오기 — 행 × 제품 칸마다 후보 값(카탈로그 · 보증 정책 · 데이터시트)
  3 verify          값 검증       — 출처 비교 → 값 확인(missing · conflict · missing_product)
  4 mark_wins       우위 항목 표시 — §4.14.2(표시할 때 계산)
  5 compose         시트 구성     — 조종 메모 · 들어온 답 · 경고 · 상태 · 버전
모델(LLM)은 셀 값을 만들지 않는다 — 값은 카탈로그 · 정책 문서 · 데이터시트 · 사용자 입력 · 파생 계산에서만.
"""
from __future__ import annotations

import copy
import logging
import time
from typing import Any

from winmate_common.ids import new_id
from winmate_common.jobs import JobContext

from . import config, ops, repo
from . import sheet as S
from .catalog import catalog
from .rules import items as itemcat
from .rules import warnings as W
from .rules.compliance import evaluate_row
from .rules.values import (
    EXPECTED_UNIT, Candidate, InvalidValue, annual_energy, catalog_candidate, diff_part, flag_text, is_complete, merge_values, parse_input,
    render_text, values_conflict,
)

log = logging.getLogger("winmate.spec.generate")

STAGES = [("resolve_models", "모델 확인", 10), ("fetch_specs", "스펙 가져오기", 30), ("verify", "값 검증", 40),
          ("mark_wins", "우위 항목 표시", 10), ("compose", "시트 구성", 10)]
CUM = {"resolve_models": 10, "fetch_specs": 40, "verify": 80, "mark_wins": 90, "compose": 100}
SOURCE_CHIP = {"catalog": "카탈로그", "policy_doc": "보증 정책 문서", "datasheet": "데이터시트", "user": "직접 입력"}
SOURCE_BODY = {"policy_doc": "국내 보증 정책 문서", "datasheet": "제품 데이터시트(PDF)", "catalog": "사내 제품 카탈로그"}


class Progress:
    """잡 진행(없으면 조용히) + 시트 active_job.progress."""

    def __init__(self, ctx: JobContext | None, sid: str):
        self.ctx = ctx
        self.sid = sid
        self.t0 = time.time()

    async def step(self, stage: str, status: str, note: str | None = None, **data: Any) -> None:
        if self.ctx:
            label = next((s[1] for s in STAGES if s[0] == stage), stage)
            await self.ctx.step(stage, status, note=note, label=label, **data)

    async def progress(self, pct: int, message: str | None = None) -> None:
        if not self.ctx:
            return
        el = time.time() - self.t0
        eta = int(el * (100 - pct) / pct) if pct > 0 else None
        await self.ctx.progress(pct, message, eta_s=eta)

    async def log(self, text: str, mode: str = "auto") -> None:
        if self.ctx:
            await self.ctx.log(text, t=config.now_iso(), text=text, mode=mode)


def _targets(sheet: dict[str, Any], product_ids: list[str] | None) -> list[dict[str, Any]]:
    ps = S.products_ordered(sheet)
    return [p for p in ps if not product_ids or p["id"] in product_ids]


# ── 1 모델 확인 ──────────────────────────────────────────

async def stage_resolve(sid: str, product_ids: list[str] | None, prog: Progress) -> str:
    sheet = await repo.amust("sheets", sid)
    await prog.step("resolve_models", "run", "사내 카탈로그 매칭 중")
    cat = catalog()
    meta = await cat.meta()
    targets = _targets(sheet, product_ids)
    codes = [p["model_code"] for p in targets if p.get("model_code")]
    specs = await cat.specs(codes) if codes else {}
    updates: dict[str, dict[str, Any]] = {}
    matched = 0
    for p in targets:
        sp = specs.get(p.get("model_code") or "")
        if sp and sp.get("in_catalog", True):
            matched += 1
        lc = await ops.evaluate_lifecycle(p, sp)
        rep = None
        if lc["status"] in ("discontinued", "eol_planned", "unknown") and (not sp or not sp.get("in_catalog", True) or lc["status"] != "unknown"):
            rep = await ops.replacement_for(p, lc, sheet)
        upd: dict[str, Any] = {"lifecycle": lc, "replacement": rep}
        if sp:
            upd.update({"display_name": sp.get("display_name") or p["display_name"], "family_label_en": sp.get("family_label_en"),
                        "series_code": sp.get("series_code"), "size_inch": sp.get("size_inch"), "category_id": sp.get("category_id"),
                        "in_catalog": bool(sp.get("in_catalog", True))})
            fam = sp.get("family_label_en")
            upd["bubble_label"] = f"{fam} {upd['display_name']}" if fam else upd["display_name"]
        updates[p["id"]] = upd

    def fn(s: dict[str, Any]) -> None:
        for p in s.get("products") or []:
            if p["id"] in updates:
                p.update(updates[p["id"]])
        s["catalog"] = {"adapter": meta.get("adapter"), "version": meta["version"], "label": "사내 카탈로그"}

    await repo.amutate("sheets", sid, fn)
    note = f"사내 카탈로그 매칭 {matched} / {len(targets)}"
    await prog.step("resolve_models", "done", note, matched=matched, total=len(targets))
    await prog.progress(CUM["resolve_models"], "모델 확인")
    await prog.log(f"모델 확인 — {note}")
    return note


# ── 2 스펙 가져오기 ──────────────────────────────────────

def _cand_dict(c: Candidate) -> dict[str, Any]:
    return {"kind": c.kind, "label": c.label, "value": c.value, "sources": c.sources, "alt_measures": c.alt_measures}


def datasheet_candidates(sheet: dict[str, Any], product_id: str, row_key: str) -> list[dict[str, Any]]:
    out = []
    for d in sheet.get("datasheets") or []:
        if d.get("product_id") != product_id or d.get("status") != "done":
            continue
        v = (d.get("values") or {}).get(row_key)
        if v and v.get("value"):
            out.append({"kind": "datasheet", "label": "데이터시트", "value": v["value"], "sources": v.get("sources") or [],
                        "alt_measures": [], "datasheet_id": d["id"]})
    return out


async def stage_fetch(sid: str, product_ids: list[str] | None, prog: Progress, row_ids: list[str] | None = None) -> str:
    await prog.step("fetch_specs", "run", "스펙 가져오는 중")
    cat = catalog()
    ver = await cat.version()
    sheet = await repo.amust("sheets", sid)
    targets = _targets(sheet, product_ids)
    codes = [p["model_code"] for p in targets if p.get("model_code")]
    specs = await cat.specs(codes) if codes else {}
    policies = {p["id"]: cat.warranty_policy(specs[p["model_code"]]) for p in targets if p.get("model_code") in specs}

    def fn(s: dict[str, Any]) -> tuple[int, int]:
        S.sync_rows(s)
        rows = S.rows_ordered(s)
        cells = s.setdefault("cells", {})
        gen = s.setdefault("gen", {})
        cands_all: dict[str, list[dict[str, Any]]] = {}
        total = filled = 0
        tps = [p for p in S.products_ordered(s) if not product_ids or p["id"] in product_ids]
        for r in rows:
            if r["row_key"].startswith(("derived:", "template:")) or (row_ids and r["id"] not in row_ids):
                continue
            for p in tps:
                key = S.ck(r["id"], p["id"])
                total += 1
                old = cells.get(key) or {}
                if old.get("state") == "edited":
                    filled += 1
                    continue
                sp = specs.get(p.get("model_code") or "")
                cands: list[dict[str, Any]] = []
                if sp:
                    c = catalog_candidate(r["row_key"], sp, ver)
                    cands.append(_cand_dict(c))
                    if r["row_key"] == "warranty":
                        pol = policies.get(p["id"])
                        if pol and pol.get("years") is not None:
                            cands.append({"kind": "policy_doc", "label": pol.get("label") or "국내 보증 정책 문서", "value": {"years": pol["years"]},
                                          "sources": [{"kind": "policy_doc", "label": pol.get("label") or "국내 보증 정책 문서",
                                                       "version_or_date": str(pol.get("as_of") or ""), "tier": "T2", "ref": pol.get("ref") or "",
                                                       "quote": f"보증 {pol['years']}년"}], "alt_measures": []})
                cands += datasheet_candidates(s, p["id"], r["row_key"])
                cands_all[key] = cands
                comp = [c for c in cands if is_complete(r["row_key"], c["value"])]
                if len(_group_candidates(r["row_key"], comp)) == 1:
                    filled += 1
                first = next((c for c in cands if c["value"]), None)
                cat_c = next((c for c in cands if c["kind"] == "catalog"), None)
                cells[key] = {"value": first["value"] if first else None, "state": "checking", "sources": (first or {}).get("sources") or [],
                              "catalog_value": (cat_c or {}).get("value"), "catalog_text": render_text(r["row_key"], (cat_c or {}).get("value"), _ko())[0]
                              if cat_c and cat_c.get("value") else None, "alt_measures": (cat_c or {}).get("alt_measures") or []}
        gen["cands"] = cands_all
        return total, filled

    _, (total, filled) = await repo.amutate("sheets", sid, fn)
    note = f"{total}칸 중 {filled}칸 채움"
    await prog.step("fetch_specs", "done", note, cells=total, filled=filled)
    await prog.progress(CUM["fetch_specs"], "스펙 가져오기")
    await prog.log(f"스펙 가져오기 — {note}")
    return note


def _ko() -> Any:
    from .rules.values import Fmt
    return Fmt()


# ── 3 값 검증 ────────────────────────────────────────────

def _group_candidates(rk: str, comp: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """출처 값 묶기 — 서로 다르지 않은(양쪽에 있는 부분이 같은) 값은 한 묶음."""
    groups: list[list[dict[str, Any]]] = []
    for c in comp:
        g = next((g for g in groups if not values_conflict(rk, g[0]["value"], c["value"])), None)
        if g is None:
            groups.append([c])
        else:
            g.append(c)
    return {str(i): g for i, g in enumerate(groups)}


def _missing_check(r: dict[str, Any], p: dict[str, Any], alt: list[dict[str, Any]]) -> dict[str, Any]:
    unit = EXPECTED_UNIT.get(r["row_key"])
    short = itemcat.ROW_SHORT.get(r["row_key"], r["label_ko"])
    num_unit = unit if unit in ("W", "nit", "년", "mm", "kg") else None
    return {"id": new_id("svc"), "n": 0, "kind": "missing", "title": f"{r['label_ko']} · {p['display_name']}",
            "body": "사내 카탈로그에 값이 없어요. 데이터시트가 있으면 읽어서 채울게요.", "row_id": r["id"], "product_id": p["id"],
            "unit": num_unit, "input_label": f"{short} 값 입력", "placeholder": f"값 입력 · {num_unit}" if num_unit else "값 입력",
            "options": [], "alt_measures": [{"label": a["label"], "value_text": a["value_text"], "footnote": a.get("footnote") or f"{a['label']} 기준",
                                             "num": a.get("num")} for a in alt or []],
            "status": "open", "answer": None, "data": {}}


def _conflict_check(r: dict[str, Any], p: dict[str, Any], groups: list[list[dict[str, Any]]]) -> dict[str, Any]:
    opts = []
    values = {}
    other = next((g[0]["kind"] for g in groups if g[0]["kind"] != "catalog"), "datasheet")
    part, texts = diff_part(r["row_key"], [g[0]["value"] for g in groups], _ko())
    for g, txt in zip(groups, texts):
        c = g[0]
        key = c["kind"] if c["kind"] != "datasheet" else f"datasheet:{c.get('datasheet_id', '')}"
        opts.append({"key": key, "label": SOURCE_CHIP.get(c["kind"], c["label"]), "value_text": txt,
                     "tier": (c["sources"][0].get("tier") if c["sources"] else ""), "source_ref": (c["sources"][0].get("ref") if c["sources"] else ""),
                     "preselected": c["kind"] == "catalog"})
        values[key] = {"value": c["value"], "sources": [s for x in g for s in x["sources"]], "kind": c["kind"]}
    if not any(o["preselected"] for o in opts) and opts:
        opts[0]["preselected"] = True
    return {"id": new_id("svc"), "n": 0, "kind": "conflict", "title": f"{part or r['label_ko']} · {p['display_name']}",
            "body": f"카탈로그와 {SOURCE_BODY.get(other, other)}의 값이 서로 달라요.", "row_id": r["id"], "product_id": p["id"],
            "unit": None, "input_label": None, "placeholder": None, "options": opts, "alt_measures": [], "status": "open", "answer": None,
            "data": {"values": values}}


async def stage_verify(sid: str, product_ids: list[str] | None, auto_answer: bool, prog: Progress, row_ids: list[str] | None = None) -> str:
    sheet = await repo.amust("sheets", sid)
    has_ds = any(d.get("status") == "done" for d in sheet.get("datasheets") or [])
    await prog.step("verify", "run", "데이터시트와 대조 중" if has_ds else "출처 대조 중")
    price = config.electricity_price()

    def fn(s: dict[str, Any]) -> int:
        auto = auto_answer or bool(s.get("gen_auto_defer"))   # `모두 [확정 필요]로 두기` 를 생성 중에 눌렀으면 새 확인도 미룸
        rows = S.rows_ordered(s)
        cells = s.setdefault("cells", {})
        cands_all = (s.get("gen") or {}).get("cands") or {}
        tps = [p for p in S.products_ordered(s) if not product_ids or p["id"] in product_ids]
        tp_ids = {p["id"] for p in tps}
        # 이번 범위의 열린 값 확인은 새로 만든다(답한 것은 그대로 기록)
        s["checks"] = [c for c in s.get("checks") or [] if not (c.get("status") in ("open", "deferred") and c.get("product_id") in tp_ids
                                                                 and (not row_ids or c.get("row_id") in row_ids))]
        new_checks: list[dict[str, Any]] = []
        for r in rows:
            rk = r["row_key"]
            if rk.startswith("derived:") or (row_ids and r["id"] not in row_ids):
                continue
            for p in tps:
                key = S.ck(r["id"], p["id"])
                cell = cells.get(key) or {}
                if cell.get("state") == "edited":
                    continue
                if rk.startswith("template:"):
                    cells[key] = {"value": None, "state": "pending", "sources": []}
                    continue
                if not p.get("in_catalog", True) or not p.get("model_code"):
                    cells[key] = {"value": None, "state": "pending", "sources": [], "catalog_value": None}
                    continue
                cands = cands_all.get(key) or []
                comp = [c for c in cands if is_complete(rk, c["value"])]
                groups = _group_candidates(rk, comp)
                cat_c = next((c for c in cands if c["kind"] == "catalog"), None) or {}
                base = {"catalog_value": cat_c.get("value"), "catalog_text": cell.get("catalog_text"), "alt_measures": cat_c.get("alt_measures") or []}
                if len(groups) >= 2:
                    chk = _conflict_check(r, p, list(groups.values()))
                    new_checks.append(chk)
                    cells[key] = {**base, "value": None, "state": "flag", "flag_text": flag_text("conflict", len(groups)), "sources": [],
                                  "check_id": chk["id"], "flag_kind": "conflict"}
                elif len(groups) == 1:
                    g = next(iter(groups.values()))
                    srcs = [x for c in g for x in c["sources"]]
                    merged = g[0]["value"]
                    for c in g[1:]:
                        merged = merge_values(merged, c["value"])
                    cells[key] = {**base, "value": merged, "state": "ok", "sources": srcs}
                elif (p.get("lifecycle") or {}).get("status") in ("discontinued", "eol_planned"):
                    # 단종 모델의 빈 칸은 값 확인 대신 경고 카드(§4.15.5)
                    partial = next((c["value"] for c in cands if c["value"]), None)
                    cells[key] = {**base, "value": partial, "state": "pending", "sources": next((c["sources"] for c in cands if c["value"]), [])}
                else:
                    partial = next((c["value"] for c in cands if c["value"]), None)
                    chk = _missing_check(r, p, cat_c.get("alt_measures") or [])
                    new_checks.append(chk)
                    cells[key] = {**base, "value": partial, "state": "flag", "flag_text": flag_text("missing"),
                                  "sources": next((c["sources"] for c in cands if c["value"]), []), "check_id": chk["id"], "flag_kind": "missing"}
        # 점선(직접 입력) 제품 — 제품당 하나(기존 장비 역할은 경고로만)
        for p in (tps if not row_ids else []):
            if (not p.get("in_catalog", True) or not p.get("model_code")) and p.get("role") != "existing" and \
               (p.get("lifecycle") or {}).get("status") not in ("discontinued", "eol_planned"):
                new_checks.append({"id": new_id("svc"), "n": 0, "kind": "missing_product", "title": p["display_name"],
                                   "body": "카탈로그에 없는 제품이에요. 데이터시트를 올리면 읽어서 채울게요.", "row_id": None, "product_id": p["id"],
                                   "unit": None, "input_label": None, "placeholder": None, "options": [], "alt_measures": [], "status": "open",
                                   "answer": None, "data": {}})
        # 파생 행
        for r in rows:
            if row_ids and r["id"] not in row_ids:
                continue
            if r["row_key"] == "derived:annual_energy_cost":
                chk = _derive_row(s, r, price if (r.get("derived") or {}).get("price") is None else r["derived"]["price"])
                if chk:
                    new_checks.append(chk)
            elif r["row_key"].startswith("template:"):
                if not any(c.get("row_id") == r["id"] and c.get("status") in ("open", "answered") for c in s.get("checks") or []):
                    first = S.products_ordered(s)[0] if s.get("products") else None
                    if first and all((cells.get(S.ck(r["id"], p["id"])) or {}).get("state") != "edited" for p in S.products_ordered(s)):
                        new_checks.append({"id": new_id("svc"), "n": 0, "kind": "missing", "title": r["label_ko"],
                                           "body": "고객사 양식에 있는 항목이에요. 값을 넣어 주세요.", "row_id": r["id"], "product_id": first["id"],
                                           "unit": None, "input_label": f"{r['label_ko']} 값 입력", "placeholder": "값 입력", "options": [],
                                           "alt_measures": [], "status": "open", "answer": None, "data": {"template_row": True}})
        # 번호 = 생성 순서(행 순 → 열 순)
        row_ord = {r["id"]: i for i, r in enumerate(rows)}
        col_ord = {p["id"]: i for i, p in enumerate(S.products_ordered(s))}
        new_checks.sort(key=lambda c: (row_ord.get(c.get("row_id") or "", 10_000), col_ord.get(c["product_id"], 0)))
        start = max([c.get("n", 0) for c in s.get("checks") or [] if c.get("status") == "answered"] + [0])
        for i, c in enumerate(new_checks):
            c["n"] = start + i + 1
            c["job_id"] = (s.get("active_job") or {}).get("id")
            if auto:
                c["status"] = "deferred"
        s["checks"] = (s.get("checks") or []) + new_checks
        if auto:
            for k, c in cells.items():
                if c.get("state") == "flag":
                    c["state"] = "pending"
                    c.pop("flag_text", None)
        return len([c for c in new_checks if c["status"] == "open"])

    _, k = await repo.amutate("sheets", sid, fn)
    note = (f"데이터시트와 대조 중 · {k}곳 확인 필요" if has_ds else f"출처 대조 중 · {k}곳 확인 필요")
    end = f"{k}곳 확인 필요" if k else "확인할 곳 없음"
    await prog.step("verify", "run", note, open_checks=k)
    await prog.step("verify", "done", end, open_checks=k)
    await prog.progress(CUM["verify"], "값 검증")
    await prog.log(f"값 검증 — {end}", "check" if k else "auto")
    return end


def _derive_row(s: dict[str, Any], r: dict[str, Any], price: float | None) -> dict[str, Any] | None:
    """연간 전기료(추정) = 일반 소비전력 × 하루 운영 시간 × 365 ÷ 1000 × 단가. 단가 없으면 값 확인(계산 기준)."""
    cells = s.setdefault("cells", {})
    rows = {x["row_key"]: x for x in s.get("rows") or []}
    hours_used = None
    for p in S.products_ordered(s):
        pw = (cells.get(S.ck(rows["power"]["id"], p["id"])) or {}).get("value") if "power" in rows else None
        op = (cells.get(S.ck(rows["operation_hours"]["id"], p["id"])) or {}).get("value") if "operation_hours" in rows else None
        if pw is None:
            pw = (s.get("preview", {}).get(p["id"]) or {}).get("power")
        if op is None:
            op = (s.get("preview", {}).get(p["id"]) or {}).get("operation_hours")
        v = annual_energy(pw, op, price)
        key = S.ck(r["id"], p["id"])
        if v and v.get("krw") is not None:
            cells[key] = {"value": v, "state": "derived", "sources": [{"kind": "derived", "label": "계산", "version_or_date": "", "tier": "T6",
                                                                        "ref": f"{rows.get('power', {}).get('id')}·{rows.get('operation_hours', {}).get('id')}"}]}
            hours_used = v.get("hours")
        else:
            cells[key] = {"value": None, "state": "pending", "sources": []}
    r.setdefault("derived", {})
    r["derived"].update({"key": "annual_energy_cost", "price": price})
    if price:
        h = f"하루 {int(hours_used) if hours_used else '[운영 시간]'}시간 · 365일 · 1kWh당 {int(price) if float(price).is_integer() else price}원"
        r["derived"]["basis"] = h
        return None
    r["derived"]["basis"] = None
    if any(c.get("row_id") == r["id"] and c.get("status") == "open" for c in s.get("checks") or []):
        return None
    first = S.products_ordered(s)[0]
    return {"id": new_id("svc"), "n": 0, "kind": "missing", "title": f"{r['label_ko']} · 계산 기준",
            "body": "연간 전기료를 계산할 전기 단가가 없어요. 1kWh당 단가(원)를 넣으면 계산할게요.", "row_id": r["id"], "product_id": first["id"],
            "unit": "원/kWh", "input_label": "전기 단가 값 입력", "placeholder": "값 입력 · 원/kWh", "options": [], "alt_measures": [],
            "status": "open", "answer": None, "data": {"derived_price": True}}


# ── 값 확인 답 ───────────────────────────────────────────

def validate_answer(s: dict[str, Any], chk: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    """답 형식 검사(결정적). 틀리면 InvalidValue. 돌려줌: 정리된 답."""
    if answer.get("option_key"):
        if not any(o["key"] == answer["option_key"] for o in chk.get("options") or []):
            raise InvalidValue(None, "고를 수 없는 값이에요.")
        return {"option_key": answer["option_key"]}
    if answer.get("alt_measure"):
        if not any(a["label"] == answer["alt_measure"] for a in chk.get("alt_measures") or []):
            raise InvalidValue(None, "고를 수 없는 측정값이에요.")
        return {"alt_measure": answer["alt_measure"]}
    text = (answer.get("value_text") or "").strip()
    if not text:
        return {}
    if (chk.get("data") or {}).get("derived_price"):
        from .rules.fmt import numbers
        ns = numbers(text)
        if not ns or any(u in text.lower() for u in ("kwh", "w ")) and "원" not in text:
            raise InvalidValue("원/kWh", "1kWh당 원 단위로 넣어 주세요.")
        return {"value_text": text, "price": ns[0]}
    row = next((r for r in s.get("rows") or [] if r["id"] == chk.get("row_id")), None)
    if row is None or (chk.get("data") or {}).get("template_row") or chk.get("kind") == "missing_product":
        return {"value_text": text}
    cur = ((s.get("cells") or {}).get(S.ck(row["id"], chk["product_id"])) or {}).get("value")
    parse_input(row["row_key"], text, cur)
    return {"value_text": text}


def apply_answer(s: dict[str, Any], chk: dict[str, Any], answer: dict[str, Any], *, by: str) -> None:
    """답을 칸에 반영(검사는 validate_answer 가 먼저 한다). 답이 없으면 deferred → [확정 필요]."""
    cells = s.setdefault("cells", {})
    row = next((r for r in s.get("rows") or [] if r["id"] == chk.get("row_id")), None)
    key = S.ck(chk["row_id"], chk["product_id"]) if chk.get("row_id") else None
    now = config.now_iso()
    if not answer:
        chk["status"] = "deferred"
        if key and key in cells:
            c = cells[key]
            if c.get("state") == "flag":
                c["state"] = "pending"
                c.pop("flag_text", None)
                c["value"] = c.get("value") if c.get("flag_kind") == "missing" else None
        return
    chk["answer"] = {k: v for k, v in answer.items() if k in ("option_key", "value_text", "alt_measure", "datasheet_id")}
    chk["status"] = "answered"
    if (chk.get("data") or {}).get("derived_price") and row is not None:
        row.setdefault("derived", {})["price"] = answer.get("price")
        _derive_row(s, row, answer.get("price"))
        return
    if answer.get("option_key") and key:
        v = ((chk.get("data") or {}).get("values") or {}).get(answer["option_key"]) or {}
        cells[key] = {**(cells.get(key) or {}), "value": v.get("value"), "state": "ok", "sources": v.get("sources") or [], "check_id": chk["id"]}
        cells[key].pop("flag_text", None)
        return
    if answer.get("alt_measure") and key:
        alt = next((a for a in chk.get("alt_measures") or [] if a["label"] == answer["alt_measure"]), None)
        if alt:
            cells[key] = {**(cells.get(key) or {}), "value": {"typ": alt.get("num"), "max": None}, "state": "ok",
                          "footnote": alt.get("footnote") or f"{alt['label']} 기준", "check_id": chk["id"]}
            cells[key].pop("flag_text", None)
        return
    text = answer.get("value_text") or ""
    if (chk.get("data") or {}).get("template_row") and row is not None:
        for p in S.products_ordered(s):
            cells[S.ck(row["id"], p["id"])] = {"value": {"text": text}, "state": "edited", "edited_by": by, "edited_at": now,
                                               "sources": [{"kind": "user", "label": "직접 입력", "version_or_date": now[:10], "tier": "고정", "ref": by}]}
        return
    if key and row is not None:
        cur = (cells.get(key) or {}).get("value")
        try:
            val = parse_input(row["row_key"], text, cur)
        except InvalidValue:
            val = {"text": text}
        cells[key] = {**(cells.get(key) or {}), "value": val, "state": "edited", "edited_by": by, "edited_at": now, "check_id": chk["id"],
                      "sources": [{"kind": "user", "label": "직접 입력", "version_or_date": now[:10], "tier": "고정", "ref": by}]}
        cells[key].pop("flag_text", None)


def apply_answers(s: dict[str, Any], answers: list[dict[str, Any]], *, by: str, complete: bool = True) -> None:
    """`답 반영하고 완성` — 답이 있는 확인은 반영, 없는 열린 확인은(complete) 미리 고른 칩 또는 [확정 필요]."""
    by_id = {a["check_id"]: a for a in answers}
    for chk in s.get("checks") or []:
        if chk.get("status") != "open":
            continue
        a = by_id.get(chk["id"])
        ans: dict[str, Any] = {}
        if a:
            ans = {k: v for k, v in a.items() if k in ("option_key", "value_text", "alt_measure", "price") and v}
        elif chk.get("answer"):
            ans = dict(chk["answer"])
        if not ans and chk["kind"] == "conflict":
            pre = next((o for o in chk.get("options") or [] if o.get("preselected")), None)
            if pre:
                ans = {"option_key": pre["key"]}
        if not ans and not complete:
            continue
        if ans.get("value_text") and (chk.get("data") or {}).get("derived_price") and "price" not in ans:
            from .rules.fmt import numbers
            ns = numbers(ans["value_text"])
            ans["price"] = ns[0] if ns else None
        apply_answer(s, chk, ans, by=by)


# ── 경고(생애주기 · 요구 미충족) ──────────────────────────

def merge_warnings(s: dict[str, Any], new: list[dict[str, Any]], *, kinds: set[str], close_missing: bool = True) -> None:
    """같은 지문의 열린 경고는 그대로(결정 유지), 사라진 원인의 열린 경고는 닫음(close_missing), 무시한 지문은 다시 만들지 않음."""
    dismissed = set(s.get("dismissed_fingerprints") or [])
    keep: list[dict[str, Any]] = []
    new_fp = {w["fingerprint"]: w for w in new}
    for w in s.get("warnings") or []:
        if w["kind"] in kinds and w.get("status") in ("open", "decided"):
            if w["fingerprint"] in new_fp:
                keep.append(w)
                new_fp.pop(w["fingerprint"])
            elif not close_missing:
                keep.append(w)
            continue
        keep.append(w)
    for fp, w in new_fp.items():
        if fp in dismissed:
            continue
        if any(x["fingerprint"] == fp and x.get("status") in ("applied",) and x["kind"] in ("discontinued", "not_in_catalog") for x in keep):
            continue
        keep.append(w)
    s["warnings"] = keep


def lifecycle_warnings(s: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    ver = (s.get("catalog") or {}).get("version") or ""
    cells = s.get("cells") or {}
    for p in S.products_ordered(s):
        lc = p.get("lifecycle") or {}
        empty = []
        for r in S.rows_ordered(s):
            c = cells.get(S.ck(r["id"], p["id"])) or {}
            if c.get("state") in ("pending", "flag") or c.get("value") is None:
                empty.append(itemcat.ROW_SHORT.get(r["row_key"], r["label_ko"]))
        if lc.get("status") in ("discontinued", "eol_planned"):
            out.append(W.discontinued(p, empty_labels=empty, replacement=p.get("replacement"), version=ver))
        elif not p.get("in_catalog", True) or not p.get("model_code"):
            out.append(W.not_in_catalog(p, version=ver))
    return out


async def requirement_warnings(s: dict[str, Any]) -> list[dict[str, Any]]:
    """연결된 요구(SP1R 대응표 · requirements 정의서)를 시트 모델이 못 맞추면 `요구 미충족`."""
    cat = catalog()
    ver = (s.get("catalog") or {}).get("version") or ""
    rules: list[dict[str, Any]] = []
    comp = s.get("compliance") or {}
    for r in comp.get("rows") or []:
        if r.get("kind") in ("numeric", "grade", "capability") and (r.get("parsed") or {}).get("key") or (r.get("parsed") or {}).get("capabilities"):
            rules.append({"id": r["id"], "label": r["item"], "summary": r["requirement"], "source_label": "규격서", **(r.get("parsed") or {}),
                          "kind": r.get("kind")})
    items, ref = await ops.requirement_items(s)
    defs = await ops.requirement_rules_from_definition(items)
    for d in defs:
        rules.append({"id": d["id"], "label": d["label"], "summary": d["label"], "source_label": d["source_label"], "key": d.get("key"),
                      "op": d.get("op"), "value": d.get("value"), "capabilities": d.get("capabilities"), "kind": d["kind"]})
    if ref:
        await ops.register_rq_link(s, ref, [d["id"] for d in defs])
    if not rules:
        return []
    codes = [p["model_code"] for p in S.products_ordered(s) if p.get("model_code") and p.get("role") != "existing"]
    specs = await cat.specs(codes) if codes else {}
    rows_by_item = {r.get("item_key"): r for r in S.rows_ordered(s)}
    from .rules.items import REQ_KEY_TO_ITEM
    out = []
    for p in S.products_ordered(s):
        if p.get("role") == "existing" or not p.get("model_code"):
            continue
        sp = specs.get(p["model_code"])
        if not sp:
            continue
        for rule in rules:
            res = evaluate_row(rule, sp)
            if res["verdict"] != "fail":
                continue
            ik = REQ_KEY_TO_ITEM.get(rule.get("key") or "") or next((REQ_KEY_TO_ITEM.get(c) for c in rule.get("capabilities") or [] if REQ_KEY_TO_ITEM.get(c)), None)
            row = rows_by_item.get(ik)
            label = row["label_ko"] if row else rule["label"]
            out.append(W.requirement_unmet(row, p, item_label=label, source_label=rule["source_label"], summary=rule["summary"],
                                           fp_key=f"{rule['id']}:{res.get('value_text')}", version=ver))
    return out


# ── 5 시트 구성 ──────────────────────────────────────────

async def stage_compose(sid: str, mode: str, prog: Progress, ctx: JobContext | None) -> dict[str, Any]:
    await prog.step("compose", "run", "시트 구성 중")
    sheet = await repo.amust("sheets", sid)
    memo_ops: list[dict[str, Any]] = []
    if ctx is not None:
        memos = await ctx.new_memos()
        for m in memos:
            from .revise import interpret
            try:
                res = await interpret(sheet, m.get("text") or "", context="generating")
                memo_ops += res.get("ops") or []
                await prog.log(f"조종 메모 반영: {m.get('text')}", "pin")
            except Exception as exc:  # noqa: BLE001
                await prog.log(f"조종 메모를 반영하지 못했어요: {exc}", "check")
    req_ws = await requirement_warnings(sheet) if mode != "rerender" else None
    tr = await translate_free_texts(sheet)
    user = ops.user()

    def fn(s: dict[str, Any]) -> dict[str, Any]:
        if memo_ops:
            from .revise import apply_sheet_ops
            apply_sheet_ops(s, memo_ops)
            for r in S.rows_ordered(s):
                if r["row_key"] == "derived:annual_energy_cost" and not any(
                        (s.get("cells") or {}).get(S.ck(r["id"], p["id"])) for p in S.products_ordered(s)):
                    chk = _derive_row(s, r, config.electricity_price())
                    if chk:
                        chk["n"] = max([c.get("n", 0) for c in s.get("checks") or []] + [0]) + 1
                        s.setdefault("checks", []).append(chk)
        if s.get("pending_answers") is not None:
            apply_answers(s, s.get("pending_answers") or [], by=user[0], complete=True)
            s["pending_answers"] = None
        ensure_template_checks(s)
        if mode != "rerender":
            merge_warnings(s, lifecycle_warnings(s), kinds={"discontinued", "not_in_catalog"})
            if req_ws is not None:
                merge_warnings(s, req_ws, kinds={"requirement_unmet"})
        # 생성 중 표시(flag)는 끝나면 [확정 필요](열린 값 확인은 그대로)
        for c in (s.get("cells") or {}).values():
            if c.get("state") == "checking":
                c["state"] = "ok" if c.get("value") else "pending"
            if c.get("state") == "flag":
                c["state"] = "pending"
                c.pop("flag_text", None)
        if tr:
            s["translations"] = {**(s.get("translations") or {}), **tr}
        s["step"] = 3
        s["generated_at"] = config.now_iso()
        if not s.get("title_confirmed"):
            from .rules.text import suggested_title
            s["title"] = suggested_title(s)
            s["title_confirmed"] = True
        S.bump_version(s, "rerender" if mode == "rerender" else "generate")
        s["last_job_id"] = (s.get("active_job") or {}).get("id") or s.get("last_job_id")
        s["active_job"] = None
        s.pop("gen", None)
        s.pop("gen_backup", None)
        s.pop("gen_auto_defer", None)
        s["format_confirmed"] = True
        S.refresh_status(s, s["id"])
        return {"open_checks": len([c for c in s.get("checks") or [] if c.get("status") == "open"]),
                "open_warnings": len([w for w in s.get("warnings") or [] if w.get("status") in ("open", "decided")])}

    saved, info = await repo.amutate("sheets", sid, fn)
    await repo.aput("snapshots", f"{sid}.v{saved['doc_version']}", S.snapshot_of(saved))
    await ops.publish(saved)
    from .links import mark_links_changed
    await mark_links_changed(saved)
    f = saved.get("format") or {}
    from .rules.text import LANG_LABEL, kind_name
    note = f"{kind_name(saved)} · {LANG_LABEL.get(f.get('language', 'ko'), '한국어')}"
    await prog.step("compose", "done", note)
    await prog.progress(100, "완료")
    if info["open_checks"]:
        route = f"/spec/{sid}/generating"
    elif info["open_warnings"]:
        route = f"/spec/{sid}/warnings"
    else:
        route = f"/spec/{sid}"
    return {"sheet_id": sid, "version": saved["doc_version"], "next_route": route, **info}


async def translate_free_texts(sheet: dict[str, Any]) -> dict[str, str]:
    """영문 · 한/영: 자유 글(메모 · 양식 행 이름)만 `sp.translate`. 숫자 · 모델코드 · 단위 집합이 바뀌면 원문 유지(§7.11-5)."""
    lang = (sheet.get("format") or {}).get("language", "ko")
    if lang == "ko":
        return {}
    texts = []
    have = sheet.get("translations") or {}
    for r in sheet.get("rows") or []:
        if (r.get("memo") or {}).get("text") and r["memo"]["text"] not in have:
            texts.append({"id": r["id"] + ":memo", "ko": r["memo"]["text"]})
        if r["row_key"].startswith("template:") and r["label_ko"] not in have:
            texts.append({"id": r["id"] + ":label", "ko": r["label_ko"]})
    if not texts:
        return {}
    from winmate_common.ai import ai
    from .rules.fmt import numbers
    try:
        res = await ai().json("sp.translate", _translate_prompt(texts), {"type": "object", "properties": {"texts": {"type": "array", "items": {
            "type": "object", "properties": {"id": {"type": "string"}, "en": {"type": "string"}}, "required": ["id", "en"]}}}, "required": ["texts"]},
            confidential=bool(sheet.get("customer_name")))
    except Exception as exc:  # noqa: BLE001 — 번역 실패는 원문 유지
        log.info("번역 실패(원문 유지): %s", exc)
        return {}
    out = {}
    src = {t["id"]: t["ko"] for t in texts}
    for t in res.get("texts") or []:
        ko = src.get(t.get("id") or "")
        en = (t.get("en") or "").strip()
        if not ko or not en:
            continue
        if sorted(numbers(ko)) != sorted(numbers(en)):
            continue
        out[ko] = en
    return out


def _translate_prompt(texts: list[dict[str, str]]) -> str:
    import json
    return ("다음 한국어 문장을 영어로 옮겨 주세요. 숫자 · 모델코드 · 단위는 그대로 둡니다. id 는 그대로 돌려줍니다.\n"
            + json.dumps({"texts": texts, "target": "en"}, ensure_ascii=False))


def ensure_template_checks(s: dict[str, Any]) -> None:
    """양식에만 있는 행(template:*)은 값 확인 하나(행마다) — 답이 없으면 [확정 필요]."""
    ps = S.products_ordered(s)
    if not ps:
        return
    cells = s.setdefault("cells", {})
    for r in S.rows_ordered(s):
        if not r["row_key"].startswith("template:"):
            continue
        for p in ps:
            cells.setdefault(S.ck(r["id"], p["id"]), {"value": None, "state": "pending", "sources": []})
        if any(c.get("row_id") == r["id"] and c.get("status") in ("open", "answered", "deferred") for c in s.get("checks") or []):
            continue
        if any((cells.get(S.ck(r["id"], p["id"])) or {}).get("state") == "edited" for p in ps):
            continue
        s.setdefault("checks", []).append({
            "id": new_id("svc"), "n": max([c.get("n", 0) for c in s.get("checks") or []] + [0]) + 1, "kind": "missing", "title": r["label_ko"],
            "body": "고객사 양식에 있는 항목이에요. 값을 넣어 주세요.", "row_id": r["id"], "product_id": ps[0]["id"], "unit": None,
            "input_label": f"{r['label_ko']} 값 입력", "placeholder": "값 입력", "options": [], "alt_measures": [], "status": "open",
            "answer": None, "data": {"template_row": True}})


def backup(s: dict[str, Any]) -> None:
    s["gen_backup"] = {"cells": copy.deepcopy(s.get("cells") or {}), "checks": copy.deepcopy(s.get("checks") or []),
                       "rows": copy.deepcopy(s.get("rows") or []), "generated_at": s.get("generated_at")}
