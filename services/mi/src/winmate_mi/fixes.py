"""확정 필요 항목(03-mi.md §5.5 · §4.12) — 만들기 · 값 검증 · 반영."""
from __future__ import annotations

import re
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.ids import now_iso

from . import anonymize, rules, verify
from .store import nid

SUB = {
    "NUMBER_PARTIAL": "출처 {n}건 중 {k}건만 수치가 있음",
    "NUMBER_NONE": "출처 {n}건에 수치가 없음",
    "CONFLICT": "출처 {n}건의 값이 서로 다름",
    "FILE": "사내 자료로 확정 · p.{page} 근거",
    "CUSTOMER_ONLY": "{where} 에 없음 · 고객 확인 필요",
    "SPEC_MISSING": "사내 스펙 값 필요",
    "READING_SPEC": "올린 사양서에서 값을 찾는 중",
    "READING": "올린 자료에서 값을 찾는 중",
    "SUMMARY_ONLY": "검색 요약에만 있는 값 · 원문 확인 필요",
    "STALE": "{year}년 자료 · 최신 값 확인 필요",
    "USER": "직접 입력으로 확정 · {name}",
    "MISSING": "근거 출처 없음 · 값 확인 필요",
    "NUMBER_UNSUPPORTED": "근거 구절에 없는 수치 · 값 확인 필요",
    "NOT_IN_FILE": "올린 자료에 이 값이 없어요",
    "COMPETITOR_UNKNOWN": "공개 자료에서 찾지 못함 · 값 확인 필요",
}
ACTION = {
    "NUMBER_PARTIAL": "출처 보기", "NUMBER_NONE": "출처 보기", "CONFLICT": "출처 비교", "FILE": "되돌리기", "USER": "되돌리기",
    "CUSTOMER_ONLY": "고객 질문 복사", "SPEC_MISSING": "Spec 시트에서", "READING": "취소", "READING_SPEC": "취소",
    "SUMMARY_ONLY": "출처 보기", "STALE": "출처 보기", "MISSING": "출처 보기", "NUMBER_UNSUPPORTED": "출처 보기", "NOT_IN_FILE": "출처 보기",
    "COMPETITOR_UNKNOWN": "출처 보기",
}


def sub_text(code: str, **kw: Any) -> str:
    t = SUB.get(code, "")
    try:
        return t.format(**kw)
    except KeyError:
        return t


def display_unit(raw: str) -> str:
    """'5,000억 원' → '억 원' · '42%' → '%' · '154 W' → 'W' · '320곳' → '곳'."""
    m = re.match(r"\[?[\d,\.]+\]?\s*(.*)", raw or "")
    return (m.group(1) if m else "").strip()


def _placeholder_unit(text: str) -> str | None:
    m = re.search(r"\[0+[0-9,\.]*\]\s*([^\s\d·,.\]]*(?:\s원)?)", text or "")
    if m:
        u = m.group(1).strip()
        return u or None
    return None


def build(analysis: dict[str, Any], version: dict[str, Any], previous: dict[str, dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    """결과 버전 → 확정 필요 항목. 주장 상태가 matched · confirmed 가 아닌 것 + 표 · 시트의 [00] · [확인 필요] 자리. 같은 metric_key 는 하나로."""
    claims = version.get("claims") or {}
    srcs = version.get("sources") or {}
    doc = version.get("document") or {}
    prev = list((previous or {}).values())
    items: dict[str, dict[str, Any]] = {}
    seen_metric: dict[str, str] = {}
    files = analysis.get("files") or []
    where = "IR 자료" if any(f.get("doc_kind") == "ir" for f in files) else "공개 자료"

    def carry_over(it: dict[str, Any]) -> dict[str, Any]:
        for p in prev:
            same = (it.get("claim_id") and p.get("claim_id") == it.get("claim_id")) or \
                   (it.get("cell_ref") and p.get("cell_ref") == it.get("cell_ref")) or \
                   (it.get("metric_key") and p.get("metric_key") == it.get("metric_key"))
            if same:
                keep = {k: p[k] for k in ("id", "carry", "history", "note", "suggestion", "applied") if k in p}
                it.update(keep)
                if p.get("reason_code") == "NOT_IN_FILE" and p.get("status") == "warn":
                    it.update(reason_code="NOT_IN_FILE", sub_text=p.get("sub_text"))
                if p.get("status") in ("ok", "wait"):
                    for k in ("status", "value", "value_source", "file_id", "file_name", "page", "job_id", "confirmed_by", "confirmed_at",
                              "reason_code", "sub_text", "unit"):
                        if k in p:
                            it[k] = p[k]
                break
        return it

    for cid, c in claims.items():
        st = c.get("status")
        has_placeholder = "[00]" in (c.get("text") or "") or "[확인 필요]" in (c.get("text") or "")
        if st in ("matched",) and not has_placeholder:
            continue
        if st == "confirmed" and not has_placeholder:
            # 확정된 항목은 목록에 남긴다(이전 항목을 이어받을 때만)
            if not any(p.get("claim_id") == cid for p in prev):
                continue
        if c.get("area") == "competitor" and c.get("cell") and c["cell"].get("col") == "samsung" and st == "matched":
            continue
        mk = c.get("metric_key")
        if mk and mk in seen_metric:
            continue
        cits = [x for x in version.get("citations") or [] if x.get("claim_id") == cid and not x.get("dropped")]
        nums = [n for n in c.get("numbers") or [] if n.get("kind") != "year"]
        unit = display_unit(nums[0]["raw"]) if nums else (_placeholder_unit(c.get("text", "")) or None)
        if st == "conflict":
            code, sub = "CONFLICT", sub_text("CONFLICT", n=len({x["source_id"] for x in cits}))
        elif st == "stale":
            years = [rules.parse_iso(srcs.get(x["source_id"], {}).get("published_at")) for x in cits]
            y = min((d.year for d in years if d), default=None)
            code, sub = "STALE", sub_text("STALE", year=y or "[0000]")
        elif st == "missing":
            if c.get("area") == "customer" and (nums or has_placeholder):
                code, sub = "CUSTOMER_ONLY", sub_text("CUSTOMER_ONLY", where=where)
            elif c.get("cell") and c["cell"].get("col") == "samsung":
                code, sub = "SPEC_MISSING", sub_text("SPEC_MISSING")
            elif c.get("cell"):
                code, sub = "COMPETITOR_UNKNOWN", sub_text("COMPETITOR_UNKNOWN")
            else:
                code, sub = "MISSING", sub_text("MISSING")
        elif c.get("unsupported"):
            code, sub = "NUMBER_UNSUPPORTED", sub_text("NUMBER_UNSUPPORTED")
        elif cits and all(srcs.get(x["source_id"], {}).get("kind") == "websearch_summary" for x in cits):
            code, sub = "SUMMARY_ONLY", sub_text("SUMMARY_ONLY")
        elif any(x.get("reason_code") == "NUMBER_MISSING" for x in cits):
            k = sum(1 for x in cits if (x.get("check") or {}).get("numbers") == "ok")
            code = "NUMBER_PARTIAL" if k else "NUMBER_NONE"
            sub = sub_text(code, n=len(cits), k=k)
        elif c.get("area") == "customer" and has_placeholder:
            code, sub = "CUSTOMER_ONLY", sub_text("CUSTOMER_ONLY", where=where)
        else:
            k = sum(1 for x in cits if x.get("status") == "matched")
            code, sub = ("NUMBER_PARTIAL", sub_text("NUMBER_PARTIAL", n=len(cits), k=k)) if cits else ("MISSING", sub_text("MISSING"))
        if not nums and not has_placeholder and st != "conflict":
            input_kind = "text"
        else:
            input_kind = "number"
        title = c.get("metric_label") or _title_from(c.get("text", ""))
        if (mk and str(mk).endswith("ratio")) or "비율" in title:
            input_kind = "ratio"
        it = {
            "id": nid("fix"), "claim_id": cid, "cell_ref": (f"{c['cell']['crt']}:{c['cell']['col']}" if c.get("cell") else None),
            "tab": c.get("area", "market"), "title": title, "metric_key": mk, "input_kind": input_kind, "unit": unit or ("%" if input_kind == "ratio" else None),
            "status": "warn", "reason_code": code, "sub_text": sub, "value": None, "value_source": None, "carry": True, "history": [],
            "competitor": bool(c.get("cell") and c["cell"].get("col") != "samsung"), "samsung_model": c.get("samsung_model"),
        }
        if input_kind == "ratio":
            it["placeholder"] = "직영 : 가맹" if "직영" in title or "가맹" in title else "값 : 값"
        items[it["id"]] = carry_over(it)
        if mk:
            seen_metric[mk] = it["id"]
    # 표 칸 자리표시(주장 없는 칸)
    table = (doc.get("competitor") or {}).get("table") or {}
    comps = {c["id"]: c for c in analysis.get("competitors") or []}
    crit_names = {c["id"]: c.get("name", "") for c in analysis.get("criteria") or []}
    for crt in table.get("criteria") or []:
        for col in table.get("columns") or []:
            cell = ((table.get("cells") or {}).get(crt) or {}).get(col) or {}
            if not cell.get("placeholder") or cell.get("claim_ids"):
                continue
            ref = f"{crt}:{col}"
            if any(i.get("cell_ref") == ref for i in items.values()):
                continue
            who = "삼성" if col == "samsung" else anonymize.workspace_label(comps.get(col, {"letter": "?"}))
            if col == "samsung":
                prod = ((doc.get("competitor") or {}).get("samsung_products") or [{}])[0]
                who = prod.get("name") or "삼성"
            code = "SPEC_MISSING" if col == "samsung" else "COMPETITOR_UNKNOWN"
            unit = _placeholder_unit(cell.get("text", ""))
            it = {"id": nid("fix"), "claim_id": None, "cell_ref": ref, "tab": "competitor", "title": f"{who} {crit_names.get(crt, '')}".strip(),
                  "metric_key": None, "input_kind": "number" if unit else "text", "unit": unit, "status": "warn", "reason_code": code,
                  "sub_text": sub_text(code), "value": None, "value_source": None, "carry": True, "history": [], "competitor": col != "samsung",
                  "samsung_model": (((doc.get("competitor") or {}).get("samsung_products") or [{}])[0].get("model_code") if col == "samsung" else None)}
            items[it["id"]] = carry_over(it)
    return items


def _title_from(text: str) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    t = re.sub(r"(입니다|습니다|해요|예요|이에요|됩니다|있습니다|늘었습니다|전망입니다)\.?$", "", t).strip()
    return t[:34] + ("…" if len(t) > 34 else "")


def public(it: dict[str, Any], analysis: dict[str, Any] | None = None) -> dict[str, Any]:
    out = dict(it)
    out["tab_label"] = rules.AREA_FIX_TAB.get(it.get("tab", "market"), "시장조사")
    code = it.get("reason_code", "")
    act = ACTION.get(code, "출처 보기")
    if it.get("status") == "ok":
        act = "되돌리기"
    elif it.get("status") == "wait":
        act = "취소"
    out["actions"] = [act]
    out.setdefault("placeholder", "값 입력")
    return out


def counts(items: dict[str, dict[str, Any]]) -> dict[str, int]:
    vals = list(items.values())
    return {"all": len(vals), "open": sum(1 for i in vals if i.get("status") == "warn"), "ok": sum(1 for i in vals if i.get("status") == "ok"),
            "wait": sum(1 for i in vals if i.get("status") == "wait")}


_NUM_OK = re.compile(r"^\s*-?\d{1,3}(,\d{3})*(\.\d+)?\s*$|^\s*-?\d+(\.\d+)?\s*$")
_RATIO_OK = re.compile(r"^\s*\d+(\.\d+)?\s*:\s*\d+(\.\d+)?\s*$")


def validate_value(it: dict[str, Any], value: str) -> str:
    v = (value or "").strip()
    kind = it.get("input_kind", "number")
    if not v:
        raise ApiError(422, "INVALID_VALUE", "값을 입력해 주세요", {"fix_id": it.get("id")})
    if kind == "ratio":
        if not _RATIO_OK.match(v):
            raise ApiError(422, "INVALID_VALUE", "비율은 6 : 4 처럼 입력해 주세요", {"fix_id": it.get("id"), "input_kind": kind})
        a, b = [x.strip() for x in v.split(":")]
        return f"{a} : {b}"
    if kind == "number":
        if not _NUM_OK.match(v):
            raise ApiError(422, "INVALID_VALUE", "숫자로 입력해 주세요(쉼표 · 소수 가능)", {"fix_id": it.get("id"), "input_kind": kind})
        return v
    return v


def history_entry(it: dict[str, Any], by: str) -> dict[str, Any]:
    return {"at": now_iso(), "status": it.get("status", "warn"), "value": it.get("value"), "value_source": it.get("value_source"),
            "sub_text": it.get("sub_text", ""), "by": by, "reason_code": it.get("reason_code"), "unit": it.get("unit"),
            "file_id": it.get("file_id"), "file_name": it.get("file_name"), "page": it.get("page")}


def _fmt_num(v: str) -> str:
    m = re.fullmatch(r"(-?)(\d+)(\.\d+)?", (v or "").replace(",", "").strip())
    if not m:
        return v
    return f"{m.group(1)}{int(m.group(2)):,}{m.group(3) or ''}"


def _copula(text: str) -> str:
    """값을 바꾼 뒤 '이에요/예요' 를 앞 글자 받침에 맞춘다."""
    return re.sub(r"([0-9가-힣])(이에요|예요)", lambda m: m.group(1) + ("이에요" if rules.has_batchim(m.group(1)) else "예요"), text)


def value_text(it: dict[str, Any]) -> str:
    v = it.get("value") or ""
    if it.get("input_kind") == "number":
        v = _fmt_num(v)
    u = it.get("unit") or ""
    if not u or it.get("input_kind") in ("text",):
        return v
    if it.get("input_kind") == "ratio":
        return v
    sep = " " if u in ("W", "nit", "mm", "kg") else ("" if u in ("%", "%p", "곳", "개", "명", "대", "배") or not u[0].isalpha() and not u.startswith("억") else " ")
    if u.startswith("억") or u.startswith("조") or u.startswith("만"):
        sep = ""
    return f"{v}{sep}{u}"


def apply_to_text(text: str, it: dict[str, Any]) -> str:
    """주장 문장의 [00]{단위} 자리(없으면 같은 단위 수치 → 기간이 아닌 첫 수치)를 확정 값으로 바꾼다."""
    val = value_text(it)
    if it.get("input_kind") == "ratio":
        m = re.search(r"\[0+[0-9,\.]*\]\s*:\s*\[0+[0-9,\.]*\]", text)
        if m:
            return _copula(text[:m.start()] + val + text[m.end():])
    if "[00]" in text:
        unit = it.get("unit") or ""
        pat = re.compile(r"\[0+[0-9,\.]*\]\s*" + (re.escape(unit) if unit and it.get("input_kind") != "ratio" else ""))
        new, n = pat.subn(val, text, count=1)
        if n:
            return _copula(new)
        return _copula(text.replace("[00]", it.get("value") or "", 1))
    if "[확인 필요]" in text:
        return text.replace("[확인 필요]", val, 1)
    nums = [n for n in verify.parse_numbers(text) if n.kind != "year"]
    unit_norm = verify._unit_of(str(it.get("unit") or "").replace("억 원", "원").replace("조 원", "원").replace("만 원", "원").strip())
    same = [n for n in nums if unit_norm and n.unit == unit_norm]
    prim = same or [n for n in nums if n.unit not in ("년", "개월", "시간", "분", "초")] or nums
    if prim:
        return _copula(verify._raw_regex(prim[0].raw).sub(val, text, count=1))
    return text
