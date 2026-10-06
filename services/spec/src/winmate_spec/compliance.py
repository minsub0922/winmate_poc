"""고객 요구 규격서 → 대응표(06-spec §4.6 · §7.2 `spec_compliance`).

LLM 은 요구 항목 · 문장 · 쪽 · 인용만 뽑는다(confidential). 인용 실재 · 숫자 일치 · 정규 키 · 판정은 결정적(§7.11).
"""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any
from urllib.parse import quote

from winmate_common.ai import ai
from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError
from winmate_common.ids import new_id
from winmate_common.platform import file_meta, parsed_document

from . import ops, repo
from . import sheet as S
from .catalog import catalog
from .rules import compliance as C
from .rules.fmt import GRADE_ALIASES, numbers

log = logging.getLogger("winmate.spec.compliance")

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "customer": {"type": "string"}, "place": {"type": "string"},
        "model_mentions": {"type": "array", "items": {"type": "string"}},
        "items": {"type": "array", "items": {"type": "object", "properties": {
            "item": {"type": "string"}, "requirement": {"type": "string"}, "page": {"type": "integer"}, "quote": {"type": "string"},
            "kind": {"type": "string", "enum": ["numeric", "grade", "capability", "procedural", "text"]},
            "key_hint": {"type": "string"}, "op": {"type": "string", "enum": [">=", "<=", "==", "contains"]},
            "value": {"type": ["number", "string"]}, "unit": {"type": "string"}, "scope": {"type": "string"}},
            "required": ["item", "requirement", "page", "quote", "kind"]}},
    },
    "required": ["items"],
}
OCR_SCHEMA = {"type": "object", "properties": {"text": {"type": "string"}, "tables": {"type": "array"}}, "required": ["text"]}
CLASSIFY_SCHEMA = {"type": "object", "properties": {"verdict": {"type": "string", "enum": ["pass", "fail", "unknown"]},
                                                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                                                    "value_label": {"type": "string"}, "note": {"type": "string"}},
                   "required": ["verdict", "evidence_ids"]}
FORMAT_LABEL = {"pdf": "PDF", "docx": "DOCX", "xlsx": "XLSX", "pptx": "PPTX", "image": "이미지", "text": "TXT", "email": "메일", "other": "파일"}


class PolicyError(ApiError):
    pass


def ai_error(exc: Exception) -> ApiError:
    """ai-tools 오류 → 한국어 잡 오류(§3 기밀 · 장애)."""
    if isinstance(exc, ApiError):
        if exc.code == "POLICY_CONFIDENTIAL" or exc.status == 403:
            return ApiError(403, "POLICY_CONFIDENTIAL", "보안 정책으로 고객 자료를 외부 모델에 보낼 수 없어요. 사내 모델 설정을 확인해 주세요.")
        if exc.status == 504 or exc.code in ("TIMEOUT", "LLM_TIMEOUT"):
            return ApiError(504, "TIMEOUT", "AI 응답이 늦어 멈췄어요. 잠시 뒤 다시 시도해 주세요.")
        if exc.status >= 500:
            return ApiError(503, "UPSTREAM_UNAVAILABLE", "AI 도구에 연결하지 못했어요. 잠시 뒤 다시 시도해 주세요.")
        return exc
    return ApiError(500, "INTERNAL", f"처리 중 오류가 났어요: {exc}")


async def load_pages(file_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    meta = await file_meta(file_id)
    doc = await parsed_document(file_id)
    pages = [{"page": p.get("no"), "text": p.get("text") or ""} for p in doc.get("pages") or []]
    if not pages and doc.get("text"):
        pages = [{"page": 1, "text": doc["text"]}]
    if doc.get("sheets") and not any(p["text"] for p in pages):
        pages = [{"page": i + 1, "text": "\n".join(" | ".join(str(c) for c in row if c is not None) for row in sh.get("rows") or [])}
                 for i, sh in enumerate(doc["sheets"])]
    return {**meta, "page_count": doc.get("page_count") or len(pages), "kind": doc.get("kind") or meta.get("kind")}, pages


async def ocr_pages(file_id: str, pages: list[dict[str, Any]], *, confidential: bool = True) -> list[dict[str, Any]]:
    """글자 층이 없는 쪽은 쪽 이미지를 I2T(`sp.page_ocr`)로 전사."""
    for p in pages:
        if (p.get("text") or "").strip():
            continue
        try:
            data, mime = await ServiceClient("files").get_bytes(f"/v1/files/{file_id}/pages/{p['page']}/image", params={"w": 1280, "format": "png"})
            res = await ai().vision("sp.page_ocr", [{"data_b64": base64.b64encode(data).decode(), "mime": mime}],
                                    "이 쪽의 글과 표를 그대로 옮겨 적어 주세요.", schema=OCR_SCHEMA, confidential=confidential)
            p["text"] = ((res.get("json") or {}).get("text") or res.get("content") or "").strip()
            p["ocr"] = True
        except ApiError as exc:
            if exc.code == "POLICY_CONFIDENTIAL" or exc.status == 403:
                raise ai_error(exc) from exc
            log.info("쪽 %s 전사 실패: %s", p["page"], exc)
    return pages


async def extract(pages: list[dict[str, Any]], note: str | None) -> dict[str, Any]:
    payload = {"pages": [{"page": p["page"], "text": p["text"][:6000]} for p in pages], "note": note}
    try:
        return await ai().json("sp.extract_requirements", json.dumps(payload, ensure_ascii=False), EXTRACT_SCHEMA,
                               system="고객 요구 규격서에서 요구 항목을 뽑는다. quote 는 그 쪽 원문을 그대로 옮긴다(바꾸지 않는다). 숫자는 원문 그대로.",
                               confidential=True)
    except Exception as exc:  # noqa: BLE001
        raise ai_error(exc) from exc


async def map_rows(items: list[dict[str, Any]], pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """인용 검증 + 정규 키(A3 → 인치 보정 · 등급 사전 · key_hint 허용 목록) + 역량(A1)."""
    cat = catalog()
    texts = {p["page"]: p["text"] for p in pages}
    rows: list[dict[str, Any]] = []
    a3_in = [{"name_raw": it.get("item") or "", "value_raw": it.get("requirement") or ""} for it in items]
    mapped: list[dict[str, Any] | None] = [None] * len(items)
    try:
        env = await cat.a3(a3_in) if a3_in else {"result": {}}
        by = {}
        for m in (env.get("result") or {}).get("mapped") or []:
            by.setdefault((m.get("name_raw"), m.get("value_raw")), m)
            by.setdefault(m.get("name_raw"), m)
        for i, it in enumerate(items):
            mapped[i] = by.get(it.get("item"))
    except ApiError as exc:
        log.info("A3 실패: %s", exc)
    for i, it in enumerate(items):
        req = it.get("requirement") or ""
        quote_ = it.get("quote") or ""
        page = int(it.get("page") or 0) or None
        valid = C.quote_ok(quote_, texts.get(page, "")) and C.numbers_ok(req, quote_)
        kind = it.get("kind") or "text"
        m = mapped[i] or {}
        key = m.get("attr")
        value, value2 = m.get("value"), m.get("value2")
        nums = numbers(req)
        if key == "screen_size_cm" and re.search(r"인치|inch|\"", req, re.I):
            key = "screen_size_inch"
        if not key and it.get("key_hint") in C.ALLOWED_KEYS:
            key = it["key_hint"]
            value = nums[0] if nums else None
            value2 = nums[1] if len(nums) > 1 else None
        llm_v = it.get("value") if isinstance(it.get("value"), (int, float)) else None
        if llm_v is not None and float(llm_v) in nums:
            value = float(llm_v)   # 원문 숫자와 같을 때만(범위 요구 `대기실 2곳 65인치 이상`)
        grade = next((g for g in GRADE_ALIASES if re.search(rf"\b{re.escape(g)}\b", req, re.I)), None)
        if grade and (kind in ("grade", "numeric") or key == "resolution"):
            kind, key = "grade", "resolution"
        caps: list[str] = []
        if kind in ("capability", "text") or not key:
            try:
                env = await cat.a1(f"{it.get('item')} {req} {quote_}")
                caps = [x["id"] for x in (env.get("result") or {}).get("links") or [] if x.get("type") == "capability"]
            except ApiError:
                caps = []
        if key == "operation_hours" or (kind == "capability" and re.search(r"24\s*시간|24/7", req + quote_)):
            caps = list(dict.fromkeys(["cap_continuous_operation", *caps]))
            kind = "capability"
        if re.search(r"원격|일괄 배포|콘텐츠 관리|CMS", f"{it.get('item')} {req}") and "cap_remote_content_mgmt" not in caps:
            caps.append("cap_remote_content_mgmt")
            kind = "capability"
        if key == "wifi" or re.search(r"wi-?fi|무선", f"{it.get('item')} {req}", re.I):
            key, kind = "wifi", "capability" if kind == "text" else kind
        if re.search(r"보증", f"{it.get('item')} {req}") and kind != "procedural":
            key = "warranty_years"
            value = nums[0] if nums else None
            kind = "numeric"
        if key and kind == "text":
            kind = "numeric"
        op = it.get("op") if it.get("op") in (">=", "<=", "==") else C.op_of(req, "<=" if key in C.LOWER_IS_BETTER else ">=")
        rows.append({"id": new_id("srq"), "ord": i, "item": it.get("item") or "", "requirement": req, "quote": quote_, "page": page,
                     "kind": kind, "parsed": {"key": key, "op": op, "value": value, "value2": value2, "unit": m.get("unit") or it.get("unit"),
                                              "grade": grade, "capabilities": caps, "scope": it.get("scope")},
                     "valid_quote": valid})
    return rows


async def resolve_target(s: dict[str, Any], mentions: list[str], note: str | None, rows: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, bool]:
    """대응 모델: 말 · 규격서의 모델 언급(kb 해소) → 시트 첫 제품 → 규격서 수치로 찾기 1위(check). 돌려줌: (제품, 찾기로 골랐는지)."""
    cat = catalog()
    cands = list(mentions or [])
    from .rules.fmt import display_name_guess
    for t in (note or "",):
        g = display_name_guess(t)
        if g:
            cands.insert(0, g)
    for c in cands:
        code = await cat.resolve(c)
        if code:
            prod = await ops.resolve_product(code, source="requirements")
            return prod, False
    ps = S.products_ordered(s)
    if ps:
        return ps[0], False
    from . import finder as FS
    st = FS.empty_state()
    sizes = []
    for r in rows:
        k = (r.get("parsed") or {}).get("key")
        v = (r.get("parsed") or {}).get("value")
        if k == "screen_size_inch" and v and not (r.get("parsed") or {}).get("scope"):
            n = int(v)
            sizes.append("75+" if n >= 75 else str(n))
    st["conditions"]["sizes"] = [x for x in sizes if x in ("43", "50", "55", "65", "75+")][:1]
    if any("cap_continuous_operation" in ((r.get("parsed") or {}).get("capabilities") or []) for r in rows):
        st["conditions"]["required"] = ["continuous_operation"]
    st = await FS.compute(st)
    first = next((c for c in st["candidates"] if not c["out"]), None)
    if not first:
        return None, True
    return await ops.resolve_product(first["ref"], source="requirements"), True


async def classify(row: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """그 밖 글 요구: 근거 목록 안의 id 를 반드시 인용한 판정만 인정(§7.11-3)."""
    evidence = [{"id": a.get("id") or k, "text": f"{k}: {a.get('raw')}", "source": "사내 제품 카탈로그"} for k, a in list((spec.get("attrs") or {}).items())[:80]]
    payload = {"requirement": {"item": row["item"], "requirement": row["requirement"], "quote": row["quote"]},
               "model": {"display_name": spec.get("display_name")}, "evidence": evidence}
    try:
        res = await ai().json("sp.classify_requirement", json.dumps(payload, ensure_ascii=False), CLASSIFY_SCHEMA,
                              system="근거 목록만 보고 요구 충족을 판정한다. 근거 id 를 인용하지 못하면 unknown.", confidential=True)
    except ApiError as exc:
        raise ai_error(exc) from exc
    ids = {e["id"] for e in evidence}
    ev = [x for x in res.get("evidence_ids") or [] if x in ids]
    verdict = res.get("verdict") if res.get("verdict") in ("pass", "fail") and ev else "unknown"
    return {"verdict": verdict, "value_text": (res.get("value_label") or "—") if verdict != "unknown" else "—",
            "note": res.get("note") if verdict != "unknown" else (res.get("note") or None)}


async def evaluate(s: dict[str, Any], rows: list[dict[str, Any]], target: dict[str, Any] | None) -> list[dict[str, Any]]:
    cat = catalog()
    spec = None
    if target and target.get("model_code"):
        spec = await cat.spec(target["model_code"])
    pol = cat.warranty_policy(spec) if spec else None
    for r in rows:
        if r.get("user_override"):
            continue
        if not r.get("valid_quote", True):
            r.update({"verdict": "unknown", "value_text": "—", "note": "원문 확인 필요"})
            continue
        req = {"kind": r["kind"], **(r.get("parsed") or {}), "item": r["item"], "requirement": r["requirement"]}
        if r["kind"] == "text" and spec and not (r.get("parsed") or {}).get("key") and not (r.get("parsed") or {}).get("capabilities"):
            res = await classify(r, spec)
        else:
            res = C.evaluate_row(req, spec, warranty=pol)
        r.update({"verdict": res["verdict"], "value_text": res.get("value_text") or "—", "note": res.get("note"),
                  "target_product_id": (target or {}).get("id"),
                  "evidence": {"text": (res.get("evidence") or {}).get("raw"), "ref": (res.get("evidence") or {}).get("id")} if res.get("evidence") else None})
    return rows


async def alternatives(rows: list[dict[str, Any]], target: dict[str, Any] | None) -> None:
    """미충족 행 대안: ① 같은 제품군에서 요구를 맞추는 가장 작은 크기 ② (없으면) 대안 없음 표시만."""
    if not target or not target.get("family_id"):
        return
    cat = catalog()
    models = sorted([m for m in await cat.family_models(target["family_id"]) if m["model_code"] != target.get("model_code")],
                    key=lambda m: (m.get("size_inch") or 999, m["model_code"]))
    specs = await cat.specs([m["model_code"] for m in models]) if models else {}
    for r in rows:
        r.pop("alternative", None)
        if r.get("verdict") != "fail":
            continue
        req = {"kind": r["kind"], **(r.get("parsed") or {})}
        for m in models:
            sp = specs.get(m["model_code"])
            if sp and C.evaluate_row(req, sp)["verdict"] == "pass":
                r["alternative"] = {"product_ref": f"kb:model:{sp.get('kb_model_id')}" if sp.get("kb_model_id") else m["model_code"],
                                    "label": sp.get("display_name") or m["model_code"], "model_code": m["model_code"]}
                break


def agent_and_title(s: dict[str, Any]) -> None:
    comp = s.get("compliance") or {}
    rows = comp.get("rows") or []
    tp = next((p for p in s.get("products") or [] if p["id"] == comp.get("target_product_id")), None)
    c = C.counts(rows)
    text = C.agent_text(len(rows), tp["display_name"] if tp else "모델", c, any(r.get("alternative") for r in rows))
    if comp.get("picked_by_finder") and tp:
        text += f" 대응 모델은 조건이 가장 잘 맞는 {tp['display_name']}로 골랐어요."
    comp["agent_text"] = text
    comp["folded_line"] = C.folded_line(rows)
    if not s.get("title_confirmed"):
        from .rules.text import suggested_title
        s["title"] = suggested_title(s)
        s["title_confirmed"] = True


async def run(sid: str, *, doc_id: str | None, file_id: str | None, note: str | None, prog: Any = None, reevaluate: bool = False) -> dict[str, Any]:
    s = await repo.amust("sheets", sid)
    comp = s.get("compliance") or {"docs": [], "rows": [], "include": {"table": True, "spec": True, "page_refs": True, "alternative": False}}
    if reevaluate:
        rows = comp.get("rows") or []
        target = next((p for p in s.get("products") or [] if p["id"] == comp.get("target_product_id")), None)
        rows = await evaluate(s, rows, target)
        await alternatives(rows, target)
    else:
        if prog:
            await prog("load_doc", "run", "규격서를 읽고 있어요")
        meta, pages = await load_pages(file_id or "")
        n = len(pages)
        if prog:
            await prog("load_doc", "done", f"규격서를 읽고 있어요 · {n}쪽 중 {n}쪽")
        pages = await ocr_pages(file_id or "", pages)
        ex = await extract(pages, note)
        if prog:
            await prog("extract_requirements", "done", f"요구 항목 {len(ex.get('items') or [])}개 인식")
        new_rows = await map_rows(ex.get("items") or [], pages)
        doc = {"id": doc_id or new_id("srd"), "file_id": file_id, "name": meta.get("name") or "규격서", "format": FORMAT_LABEL.get(meta.get("kind") or "", "파일"),
               "pages": meta.get("page_count") or n, "recognized": len(new_rows), "status": "done", "note": note,
               "page_texts": {str(p["page"]): p["text"][:20000] for p in pages}}
        for r in new_rows:
            r["doc_id"] = doc["id"]
        target, picked = await resolve_target(s, ex.get("model_mentions") or [], note, new_rows)
        if target and not S.has_ref(s, target.get("ref"), target.get("model_code")):
            target["source"] = "requirements"

            def add_target(x: dict[str, Any]) -> None:
                target["ord"] = len(x.get("products") or [])
                x.setdefault("products", []).append(target)
                S.recompute_kind(x)

            s, _ = await repo.amutate("sheets", sid, add_target)
        elif target:
            target = next((p for p in s.get("products") or [] if p.get("model_code") == target.get("model_code") or p.get("ref") == target.get("ref")), target)
        all_rows = [r for r in comp.get("rows") or []] + new_rows
        all_rows = await evaluate(s, all_rows, target)
        await alternatives(all_rows, target)
        rows = all_rows
        comp["docs"] = [d for d in comp.get("docs") or [] if d["id"] != doc["id"]] + [doc]
        comp["customer"] = ex.get("customer") or comp.get("customer")
        comp["place"] = ex.get("place") or comp.get("place")
        comp["target_product_id"] = (target or {}).get("id")
        comp["picked_by_finder"] = picked
        comp["note"] = note
    comp["rows"] = rows
    comp["status"] = "done"
    comp["error"] = None

    def fn(x: dict[str, Any]) -> None:
        cur = x.get("compliance") or {}
        x["compliance"] = {**cur, **comp}
        if not reevaluate and x.get("compliance", {}).get("customer") and not x.get("customer_name"):
            x["customer_name"] = x["compliance"]["customer"]
        agent_and_title(x)
        x["active_job"] = None
        S.refresh_status(x, x["id"])

    saved, _ = await repo.amutate("sheets", sid, fn)
    await ops.publish(saved)
    c = C.counts(rows)
    return {"sheet_id": sid, "rows": len(rows), "counts": c}


def ask_draft(s: dict[str, Any]) -> dict[str, Any]:
    comp = s.get("compliance") or {}
    rows = [r for r in comp.get("rows") or [] if r.get("verdict") == "unknown"]
    title = (s.get("title") if s.get("title_confirmed") else None) or "요구 스펙 대응표"
    lines = [f"[{title}] 확인이 필요한 요구 항목 {len(rows)}건입니다.", ""]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. {r['item']} — {r['requirement']}" + (f" (원문 p.{r['page']})" if r.get("page") else ""))
    lines += ["", "확인 부탁드립니다."]
    text = "\n".join(lines)
    subject = f"[확인 요청] {title} · {len(rows)}건"
    return {"text": text, "mailto": f"mailto:?subject={quote(subject)}&body={quote(text)}", "count": len(rows)}


def page_view(s: dict[str, Any], doc_id: str, n: int) -> dict[str, Any]:
    comp = s.get("compliance") or {}
    doc = next((d for d in comp.get("docs") or [] if d["id"] == doc_id), None)
    if doc is None:
        raise ApiError(404, "NOT_FOUND", f"규격서를 찾을 수 없어요: {doc_id}")
    quotes = [{"row_id": r["id"], "text": r.get("quote") or ""} for r in comp.get("rows") or [] if r.get("doc_id") == doc_id and r.get("page") == n]
    return {"page": n, "image_file_id": doc.get("file_id"),
            "image_url": f"/api/files/v1/files/{doc['file_id']}/pages/{n}/image?w=900" if doc.get("file_id") else None,
            "text": (doc.get("page_texts") or {}).get(str(n), ""), "quotes": quotes}

