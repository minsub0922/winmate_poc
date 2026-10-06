"""재료 후보 — 연결 자료(Storyboard · MI · 정의서 · 사례 · 이전 VP · RFP · 메모)에서 결정적으로 뽑는다(05-vp.md §7.1).

후보는 안정 키(`SB-KM1` · `MI-C2` · `RFP-C1` …)를 가진다. LLM(`vp.extract_materials.v1`)은 이 키로만 재료를 가리키고
(수치는 입력 수치의 키로만), 모델이 실패하거나 아무것도 주지 않으면 후보를 그대로 재료로 쓴다(지어내지 않는다).
"""
from __future__ import annotations

import re
from typing import Any

from rapidfuzz import fuzz
from winmate_common.ids import new_id

from . import config, coverage, numbers

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"
COST_WORDS = ("비용", "인건비", "전기료", "배송비", "인쇄", "예산", "손실", "낭비", "억", "만 원", "운영비", "유지비", "요금", "비 부담")
AXIS_KO = {"challenge": "과제", "value": "가치", "evidence": "근거 수치", "stakeholder": "이해관계자", "product": "제품"}
TAG_NAME = {"SB": "Storyboard", "MI": "MI", "RFP": "RFP", "CS": "유관 사례", "RQ": "고객 요구사항", "QT": "견적", "USER": "메모",
            "KB": "KB", "VP": "이전 가치 제안"}


def has_cost(text: str) -> bool:
    t = text or ""
    return any(w in t for w in COST_WORDS)


def _cand(key: str, axis: str, text: str, tag: str, ref_id: str = "", *, locator: str | None = None, as_of: str | None = None,
          **extra: Any) -> dict[str, Any]:
    c = {"key": key, "axis": axis, "text": (text or "").strip(), "tag": tag, "ref_id": ref_id, "locator": locator, "as_of": as_of}
    c.update(extra)
    return c


def _num_from_mi(n: dict[str, Any]) -> dict[str, Any]:
    val = n.get("value")
    st = n.get("status") or ""
    status = "secured" if st in ("matched", "confirmed") else ("missing" if (st == "missing" or not val) else "estimated")
    disp = str(val) if val else "[00]"
    v1, v2, unit = numbers.parse_display(disp)
    return numbers.nv(disp, status, value=v1, value2=v2, unit=unit or None,
                      source={"kind": "mi", "label": n.get("footnote") or "MI", "refs": [], "as_of": n.get("as_of")})


def from_storyboard(sb_id: str, kms: list[dict[str, Any]], *, rq_items: list[dict[str, Any]] | None = None,
                    keymen: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    out = []
    for i, km in enumerate(kms, 1):
        out.append(_cand(f"SB-KM{i}", "value", km.get("text", ""), "SB", sb_id, locator=f"KM{CIRCLED[i - 1] if i <= 10 else i}",
                         km_id=km.get("id"), audience=km.get("audience")))
    seen_aud: set[str] = set()
    for km in kms:
        aud = (km.get("audience") or "").strip()
        if aud and aud not in seen_aud:
            seen_aud.add(aud)
            out.append(_cand(f"SB-A{len(seen_aud)}", "stakeholder", aud, "SB", sb_id, group=coverage.group_of(aud)))
    out += from_rq_parts(rq_items or [], keymen or [], prefix="RQ", ref_id=sb_id)
    return out


def from_rq_parts(items: list[dict[str, Any]], keymen: list[dict[str, Any]], *, prefix: str = "RQ", ref_id: str = "") -> list[dict[str, Any]]:
    out = []
    for i, it in enumerate(items, 1):
        text = it.get("short") or it.get("text") or ""
        out.append(_cand(f"{prefix}-{it.get('code') or i}", "challenge", text, "RQ", ref_id, locator=it.get("code"),
                         cost=has_cost(it.get("text") or text), full=it.get("text")))
    ranked = sorted(keymen, key=lambda k: -int(k.get("weight") or 0))
    for i, k in enumerate(ranked, 1):
        name = k.get("name") or ""
        if not name:
            continue
        out.append(_cand(f"{prefix}-KM{i}", "stakeholder", name, "RQ", ref_id, approver=(i == 1),
                         group="approver" if i == 1 else coverage.group_of(name), weight=k.get("weight")))
    return out


def from_requirements(rq_id: str, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    snap = snapshot.get("snapshot") or snapshot
    return from_rq_parts(list(snap.get("items_flat") or []), list(snap.get("keymen") or []), prefix="RQ", ref_id=rq_id)


def from_mi(mi_id: str, bundle: dict[str, Any]) -> list[dict[str, Any]]:
    vm = bundle.get("vp_materials") or {}
    out = []
    for i, c in enumerate(vm.get("challenges") or [], 1):
        t = c.get("text") or ""
        out.append(_cand(f"MI-C{i}", "challenge", t, "MI", mi_id, cost=has_cost(t)))
    for i, u in enumerate(vm.get("users") or [], 1):
        role = u.get("role") or ""
        out.append(_cand(f"MI-U{i}", "stakeholder", role, "MI", mi_id, group=coverage.group_of(role), mi_user=True,
                         goal=u.get("goal"), pain=u.get("pain")))
    for i, s in enumerate(vm.get("strengths") or [], 1):
        out.append(_cand(f"MI-S{i}", "value", s.get("title") or "", "MI", mi_id, note=s.get("note"), strength=True))
    for i, n in enumerate(vm.get("numbers") or [], 1):
        out.append(_cand(f"MI-N{i}", "evidence", n.get("text") or "", "MI", mi_id, as_of=n.get("as_of"),
                         age=n.get("source_age_months"), number=_num_from_mi(n), area=n.get("area"), footnote=n.get("footnote")))
    return out


def from_case(dep: dict[str, Any], kpis: list[dict[str, Any]], idx: int = 1) -> list[dict[str, Any]]:
    out = []
    did = dep.get("id") or dep.get("deployment_id") or ""
    for i, k in enumerate([k for k in kpis if k.get("has_number")], 1):
        out.append(_cand(f"CS{idx}-K{i}", "evidence", k.get("text") or "", "CS", did, kpi_id=k.get("id"), claim=bool(k.get("claim_flag")),
                         number=numbers.nv(_first_number(k.get("text") or ""), "estimated",
                                           source={"kind": "case", "label": f"유관 사례 · {dep.get('title', '')}"[:80], "refs": [did],
                                                   "tier": "T3_case"}, basis="유관 사례")))
    for i, p in enumerate(dep.get("products") or [], 1):
        ref = p.get("ref") or ""
        m = re.match(r"kb:(family|model|solution|category):(.+)$", ref)
        if m:
            out.append(_cand(f"CS{idx}-P{i}", "product", p.get("label") or "", "CS", did,
                             product={"kind": m.group(1), "id": m.group(2), "name": p.get("label") or m.group(2)}))
    return out


def _first_number(text: str) -> str:
    m = re.search(r"\d[\d,]*(?:\.\d+)?\s*(?:%|배|분|초|시간|일|개월|년|명|건|곳|대|원|만|억|kWh|W)?", text or "")
    return m.group(0).strip() if m else "[00]"


def from_rfp(att_id: str, ext: dict[str, Any], *, label: str = "RFP") -> list[dict[str, Any]]:
    out = []
    loc_prefix = "회의록 " if label == "회의록" else ""
    for i, c in enumerate(ext.get("challenges") or [], 1):
        t = c.get("text") or ""
        loc = f"{loc_prefix}p.{c['page']}" if c.get("page") else (loc_prefix.strip() or None)
        out.append(_cand(f"RFP-C{i}", "challenge", t, "RFP", att_id, locator=loc, cost=has_cost(t + " " + (c.get("quote") or "")),
                         quote=c.get("quote")))
    for i, d in enumerate(ext.get("decision_makers") or [], 1):
        role = d.get("role") or ""
        appr = any(w in role for w in config.routing()["stakeholder_groups"]["approver"]["words"]) or i == 1
        out.append(_cand(f"RFP-D{i}", "stakeholder", role + (" · 결재" if appr and "결재" not in role and i == 1 else ""), "RFP", att_id,
                         locator=f"p.{d['page']}" if d.get("page") else None, approver=appr and i == 1,
                         group="approver" if appr else coverage.group_of(role), kpi=d.get("kpi")))
    for i, t in enumerate(ext.get("to_be") or [], 1):
        txt = t.get("text") or ""
        out.append(_cand(f"RFP-T{i}", "value", txt, "RFP", att_id, locator=f"{loc_prefix}p.{t['page']}" if t.get("page") else None))
    for i, n in enumerate(ext.get("numbers") or [], 1):
        disp = n.get("display") or ""
        v1, v2, unit = numbers.parse_display(disp)
        out.append(_cand(f"RFP-N{i}", "evidence", n.get("text") or disp, "RFP", att_id,
                         locator=f"{loc_prefix}p.{n['page']}" if n.get("page") else None,
                         number=numbers.nv(disp, "secured", value=v1, value2=v2, unit=unit or None,
                                           source={"kind": "rfp", "label": label, "refs": [att_id]})))
    return out


NOTE_APPROVER = re.compile(r"결재(?:는|자는|자|권자는)?\s*([A-Za-z가-힣·]+?)(?:[,.\s]|이고|이며|와|과|$)")


def from_note(note: str) -> list[dict[str, Any]]:
    out = []
    m = NOTE_APPROVER.search(note or "")
    if m:
        who = m.group(1).strip()
        if who and who not in ("는", "자"):
            out.append(_cand("USER-D1", "stakeholder", f"{who} · 결재", "USER", "", approver=True, group="approver"))
    return out


def from_vp(src_id: str, doc: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for i, m in enumerate([x for x in doc.get("materials") or [] if not x.get("excluded")], 1):
        out.append(_cand(f"VP-{i}", m.get("axis", "value"), m.get("text", ""), "VP", src_id, number=m.get("number"),
                         metric=m.get("metric"), cost=m.get("cost"), approver=m.get("approver"), group=m.get("group"),
                         product_refs=m.get("product_refs") or []))
    return out


# ── 재료 만들기 ────────────────────────────────────────────

def _tag(c: dict[str, Any]) -> dict[str, Any]:
    return {"tag": c["tag"], "ref_id": c.get("ref_id") or "", "locator": c.get("locator"), "as_of": c.get("as_of")}


def item_from(c: dict[str, Any], *, text: str | None = None, axis: str | None = None, extra_tags: list[dict[str, Any]] | None = None,
              number: dict[str, Any] | None = None, state: str = "new") -> dict[str, Any]:
    tags = [_tag(c)] + list(extra_tags or [])
    uniq = []
    seen = set()
    for t in tags:
        k = (t["tag"], t.get("ref_id"))
        if k not in seen:
            seen.add(k)
            uniq.append(t)
    refs = list(c.get("product_refs") or [])
    if c.get("product"):
        refs.append(c["product"])
    return {
        "id": new_id("vmi"), "key": c["key"], "axis": axis or c["axis"], "text": (text or c["text"]).strip(), "sources": uniq,
        "state": state, "number": number if number is not None else c.get("number"), "metric": c.get("metric"),
        "product_refs": refs, "cost": bool(c.get("cost")), "approver": bool(c.get("approver")),
        "group": c.get("group"), "excluded": False, "flags": [], "origin_keys": [c["key"]], "age": c.get("age"),
        "km_id": c.get("km_id"), "claim": c.get("claim"), "mi_user": c.get("mi_user"),
    }


def preview_items(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """VP1 커버리지 미리보기(LLM 없음) — MI 사용자는 이해관계자로 세지 않는다(`손님 관점은 MI 사용자에서 가져와요`)."""
    return [item_from(c) for c in cands if c["axis"] != "product" and not (c["axis"] == "stakeholder" and c.get("mi_user"))]


def preview_facts(cands: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "km_count": sum(1 for c in cands if c.get("km_id")),
        "strengths": sum(1 for c in cands if c.get("strength")),
        "mi_users": [c["text"] for c in cands if c.get("mi_user")],
    }


def from_llm(cands: list[dict[str, Any]], llm_items: list[dict[str, Any]], *, cap: int = 6) -> list[dict[str, Any]]:
    """LLM 재료(키 참조) → 재료. 모르는 키 · 빈 문장은 버린다. LLM 이 비운 축은 후보로 채운다."""
    by_key = {c["key"]: c for c in cands}
    out: list[dict[str, Any]] = []
    used_axes: set[str] = set()
    for it in llm_items or []:
        refs = [r.strip() for r in re.split(r"[,\s]+", str(it.get("source_ref") or "")) if r.strip() in by_key]
        if not refs or not (it.get("text") or "").strip():
            continue
        base = by_key[refs[0]]
        axis = it.get("axis") if it.get("axis") in AXIS_KO else base["axis"]
        num = None
        nref = it.get("number_ref")
        if nref and nref in by_key and by_key[nref].get("number"):
            num = by_key[nref]["number"]
        elif base.get("number"):
            num = base["number"]
        item = item_from(base, text=it["text"], axis=axis, extra_tags=[_tag(by_key[r]) for r in refs[1:]], number=num)
        item["origin_keys"] = refs
        if it.get("cost") is not None:
            item["cost"] = bool(it.get("cost")) or item["cost"]
        if it.get("approver"):
            item["approver"] = True
            item["group"] = "approver"
        if axis == "stakeholder" and not item.get("group"):
            item["group"] = coverage.group_of(item["text"], approver=item["approver"])
        if it.get("metric"):
            item["metric"] = _metric_from_llm(it["metric"], by_key)
        for r in refs:
            item["product_refs"] += [x for x in (by_key[r].get("product_refs") or []) if x not in item["product_refs"]]
            if by_key[r].get("product") and by_key[r]["product"] not in item["product_refs"]:
                item["product_refs"].append(by_key[r]["product"])
            if by_key[r].get("km_id") and not item.get("km_id"):
                item["km_id"] = by_key[r]["km_id"]
            if by_key[r].get("age") is not None and item.get("age") is None:
                item["age"] = by_key[r]["age"]
        out.append(item)
        used_axes.add(axis)
    for axis in ("challenge", "value", "evidence", "stakeholder"):
        if axis in used_axes:
            continue
        for c in [c for c in cands if c["axis"] == axis][:cap]:
            out.append(item_from(c))
    for c in cands:
        if c["axis"] == "product" and c.get("product"):
            out.append(item_from(c))
    return out


def _metric_from_llm(m: dict[str, Any], by_key: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    label = (m.get("label") or "").strip()
    if not label:
        return None

    def side(v: Any) -> dict[str, Any]:
        if isinstance(v, dict):
            disp = str(v.get("display") or "[00]")
            st = v.get("status") or ("missing" if disp.startswith("[") else "secured")
            v1, v2, unit = numbers.parse_display(disp)
            return numbers.nv(disp, st, value=v1, value2=v2, unit=unit or v.get("unit"),
                              source={"kind": v.get("source_kind") or "customer", "label": v.get("source_label") or "", "refs": []},
                              basis=v.get("basis"))
        return numbers.missing()
    return {"label": label, "before": side(m.get("before")), "after": side(m.get("after"))}


def dedupe(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """같은 축에서 문장이 사실상 같은 재료를 합친다(자동 · `합침`)."""
    fixes: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    for it in items:
        twin = next((k for k in kept if k["axis"] == it["axis"] and it["axis"] != "product" and not k.get("excluded")
                     and _norm(k["text"]) == _norm(it["text"])), None)
        if twin is None:
            kept.append(it)
            continue
        twin["sources"] += [t for t in it["sources"] if t not in twin["sources"]]
        twin["state"] = "merged"
        twin["origin_keys"] = list(dict.fromkeys(twin.get("origin_keys", []) + it.get("origin_keys", [])))
    return kept, fixes


def _norm(t: str) -> str:
    return re.sub(r"[\s·,.'\"()\-]", "", t or "")


def similar(a: str, b: str) -> int:
    return int(fuzz.token_set_ratio(_norm(a), _norm(b)))


def tag_names(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    """VP1A 출처 범례(쓰인 출처만, SB · MI · RFP · CS · RQ 순)."""
    used: list[str] = []
    for it in items:
        if it.get("excluded"):
            continue
        for t in it.get("sources") or []:
            if t["tag"] not in used:
                used.append(t["tag"])
    order = ["SB", "MI", "RFP", "CS", "RQ", "QT", "USER", "VP", "KB"]
    return [{"tag": t, "name": TAG_NAME.get(t, t)} for t in order if t in used]


def handles(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """프롬프트용 안정 이름(재료 키 — 겹치면 `#2`) → 재료. 모델 출력은 이 이름으로 재료를 가리킨다(mock 고정 응답도 같은 이름을 쓴다)."""
    out: dict[str, dict[str, Any]] = {}
    for m in items:
        base = str(m.get("key") or m["id"])
        h, n = base, 2
        while h in out:
            h = f"{base}#{n}"
            n += 1
        out[h] = m
    return out
