"""시트 작성(05-vp.md §7.2-3 · §7.4) — 역할 · 레이아웃별 내용.

- 먼저 재료 · 수치 · KB 메시지만으로 결정적 초안을 만든다(제목 틀은 보드 문장, 사실은 재료 문장 그대로).
- LLM `vp.write_sheet.v1` 은 그 초안을 다듬는다 — 재료 · 수치 · 제품은 입력 id 로만 가리키고, 틀린 id · 빈 값 · mock 자리표시는 버린다.
- 숫자 검증(§7.7)은 guards 가 맡는다.
"""
from __future__ import annotations

import copy
import logging
import re
from typing import Any

from winmate_common.ids import new_id

from . import catalog, llm, materials, numbers, signals
from .decide import josa

log = logging.getLogger("winmate.vp.writer")

KO_N = {1: "한", 2: "두", 3: "세", 4: "네", 5: "다섯", 6: "여섯"}
LIMITS = {"title": 44, "points": 90, "item_title": 26, "item_body": 70}


def ko_n(n: int) -> str:
    return KO_N.get(n, str(n))


def shape_of(code: str) -> str:
    c = catalog.norm(code)
    e = catalog.entry(c) or {}
    if e.get("industry_code"):
        return {"A": "pairs", "B": "stakeholders", "C": "metrics"}.get(e.get("pack_role") or "", "pillars")
    if c.startswith("CH-"):
        return "challenges"
    if c.startswith("EF-"):
        return "metrics"
    if c in ("VP-G", "VP-C"):
        return "one_liner"
    if c in ("VP-H", "VP-D"):
        return "stakeholders"
    if c in ("VP-E", "VP-A", "VP-U"):
        return "pairs"
    return "pillars"


def mock_text(s: Any) -> bool:
    return isinstance(s, str) and (s.strip().startswith("[mock") or not s.strip())


def clean(s: Any) -> str | None:
    if not isinstance(s, str) or mock_text(s):
        return None
    return s.strip()


def cut(s: str, n: int) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    for sep in (" · ", ", ", " — ", " "):
        i = s.rfind(sep, 0, n)
        if i >= n * 0.5:
            return s[:i].rstrip(" ·,—")
    return s[: n - 1].rstrip() + "…"


END_RE = re.compile(r"\s*(이|가|은|는)?\s*(크다|많다|반복된다|길다|있다|된다|한다|이다|없다|어렵다|부족하다|늘어난다|필요하다)[.!]?$")
GOAL_END = re.compile(r"\s*(?:하는|되는|는|을|를)?\s*것이\s*(?:목표|필요)(?:이)?다$|\s*(?:을|를)\s*원한다$|\s*(?:하고|되고)\s*싶다$")
KEY_WORDS = ("비용", "부담", "오표기", "대기", "불편", "지연", "낭비", "손실", "인건비", "전기료", "시간", "오류", "누락", "교체", "운영")
CONNECT = ("어", "고", "서", "며", "면", "때마다", "아")


def short_phrase(text: str, n: int = 20) -> str:
    """긴 문장 → 칸에 들어갈 짧은 말(서술어를 떼고, 길면 핵심 낱말로 끝나는 마지막 절) — 낱말은 원문 그대로."""
    t = re.sub(r"[.!?]+$", "", (text or "").strip())
    t = GOAL_END.sub("", t).strip()
    t = END_RE.sub("", t).strip()
    if len(t) <= n:
        return t
    toks = t.split()
    idx = max((i for i, tok in enumerate(toks) if any(k in tok for k in KEY_WORDS)), default=None)
    if idx is None:
        return cut(t, n)
    out: list[str] = []
    for tok in reversed(toks[: idx + 1]):
        if len(" ".join([tok] + out)) > n:
            break
        out.insert(0, tok)
    if not out:
        return cut(t, n)
    for i in range(len(out) - 2, -1, -1):
        if out[i].endswith(CONNECT) and len(" ".join(out[i + 1:])) >= 6:
            out = out[i + 1:]
            break
    last = out[-1]
    core = re.sub(r"(이|가|을|를|은|는)$", "", last)
    if core != last and any(core.endswith(k) for k in KEY_WORDS):
        out[-1] = core
    return " ".join(out)


# ── 문맥 ──────────────────────────────────────────────────

class Ctx:
    def __init__(self, doc: dict[str, Any]):
        self.doc = doc
        f = doc.get("facts") or {}
        self.customer = (doc.get("customer_name") or "").strip() or "고객"
        self.items = signals.active(doc)
        self.by_id = {m["id"]: m for m in self.items}
        self.handles = materials.handles(self.items)
        self.handle_of = {m["id"]: h for h, m in self.handles.items()}
        self.challenges = self._order_ch([m for m in self.items if m["axis"] == "challenge"])
        self.values = self._order_values([m for m in self.items if m["axis"] == "value"])
        self.evidence = [m for m in self.items if m["axis"] == "evidence" and not any(t["tag"] == "QT" for t in m.get("sources") or [])]
        self.stakeholders = self._order_sk([m for m in self.items if m["axis"] == "stakeholder"])
        self.products = list(f.get("products") or []) or signals.products_of(doc)
        self.kb_messages = list(f.get("kb_messages") or [])
        self.metrics = [m for m in (f.get("metrics") or [])]
        self.metric_handles = {f"N{i + 1}": m for i, m in enumerate(self.metrics)}
        self.rfp = f.get("rfp") or {}
        self.quote = f.get("quote") or {}
        self.industry = doc.get("industry") or {}

    @staticmethod
    def _order_ch(chs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def rank(m: dict[str, Any]) -> tuple[int, int, int]:
            tags = {t["tag"] for t in m.get("sources") or []}
            src = 0 if tags & {"RFP", "MTG"} else 1 if "RQ" in tags else 2 if "SB" in tags else 3
            return (src, 0 if m.get("cost") else 1, -len(tags))
        return sorted(chs, key=rank)

    @staticmethod
    def _order_values(vals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def rank(m: dict[str, Any]) -> tuple[int, str]:
            keys = m.get("origin_keys") or [m.get("key") or ""]
            k = keys[0] if keys else ""
            if m.get("km_id") or str(k).startswith("SB-KM"):
                return (0, k)
            if m.get("state") in ("rewritten", "merged"):
                return (1, k)
            if str(k).startswith("MI-S"):
                return (2, k)
            return (3, k)
        return sorted(vals, key=rank)

    @staticmethod
    def _order_sk(sks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        order = {"approver": 0, "operator": 1, "user": 2}
        return sorted(sks, key=lambda m: (0 if m.get("approver") else 1, order.get(m.get("group") or "", 3)))

    def product_ref(self, i: int) -> dict[str, Any] | None:
        if not self.products:
            return None
        return self.products[i % len(self.products)]

    def kb_message_for(self, ref: dict[str, Any] | None, near: str = "") -> dict[str, Any] | None:
        if not ref:
            return None
        cands = [k for k in self.kb_messages if k.get("about_id") == ref.get("id") or k.get("about_name") == ref.get("name")]
        if not cands:
            return None
        cands.sort(key=lambda k: (int(k.get("claim_flag") or 0), k.get("level") != "key_message", len(k.get("text") or "") > 60,
                                  -materials.similar(k.get("text", ""), near)))
        return cands[0]

    def kb_title_for(self, ref: dict[str, Any] | None) -> dict[str, Any] | None:
        """기둥 제목으로 쓸 수 있는 짧은 공식 메시지(핵심 메시지 · 헤드라인, 30자 이하, claim 아닌 것 먼저)."""
        if not ref:
            return None
        cands = [k for k in self.kb_messages if (k.get("about_id") == ref.get("id") or k.get("about_name") == ref.get("name"))
                 and k.get("level") in ("key_message", "headline", "tagline") and len(k.get("text") or "") <= 30]
        cands.sort(key=lambda k: (int(k.get("claim_flag") or 0), len(k.get("text") or "")))
        return cands[0] if cands else None

    def related_evidence(self, text: str, k: int = 2) -> list[dict[str, Any]]:
        scored = sorted(((materials.similar(text, e["text"]), e) for e in self.evidence), key=lambda x: -x[0])
        return [e for s, e in scored if s >= 45][:k]

    def src_line(self, m: dict[str, Any]) -> str:
        parts = []
        for t in m.get("sources") or []:
            nm = {"SB": "Storyboard", "MI": "MI", "RFP": "RFP", "CS": "유관 사례", "RQ": "요구사항", "QT": "견적", "USER": "메모",
                  "KB": "KB", "VP": "이전 가치 제안"}.get(t["tag"], t["tag"])
            parts.append(f"{nm} {t['locator']}" if t.get("locator") else nm)
        return " · ".join(dict.fromkeys(parts))


# ── 결정적 초안 ────────────────────────────────────────────

def unit_guess(text: str) -> str | None:
    if re.search(r"비용|비\b|인쇄|배송|전기료|예산|운영비|억|원", text or ""):
        return "억" if "억" in (text or "") else "원"
    if re.search(r"시간|리드타임|대기", text or ""):
        return "시간" if "시간" in (text or "") else "분"
    if re.search(r"오표기|오류|누락|건", text or ""):
        return "건"
    if re.search(r"율|률|%", text or ""):
        return "%"
    return None


def det_challenges(ctx: Ctx, n: int = 3) -> list[dict[str, Any]]:
    out = []
    for m in ctx.challenges[:n]:
        num = m.get("number")
        if not num:
            ev = ctx.related_evidence(m["text"], 1)
            num = ev[0].get("number") if ev and ev[0].get("number") else None
        if not num:
            num = numbers.missing(unit_guess(m["text"]))
        body = ctx.src_line(m)
        if m.get("state") == "inferred":
            body = (body + " · " if body else "") + "사례 DB로 추론 [확인 필요]"
        out.append({"id": new_id("vch"), "title": short_phrase(m["text"], LIMITS["item_title"]), "body": body, "impact": num,
                    "source_ids": [m["id"]]})
    return out


def to_be_texts(ctx: Ctx) -> list[str]:
    """바라는 모습(RFP · 정의서 to-be) — CH-B 오른쪽 칸."""
    out = [m["text"] for m in ctx.values if any(str(k).startswith("RFP-T") for k in m.get("origin_keys") or [m.get("key")])]
    return out or [m["text"] for m in ctx.values]


def det_pillars(ctx: Ctx, n: int) -> list[dict[str, Any]]:
    vals = list(ctx.values)
    pillars: list[dict[str, Any]] = []
    extra: list[str] = []
    if len(vals) > n:
        extra = [v["text"] for v in vals[n:]]
        vals = vals[:n]
    for i, v in enumerate(vals):
        refs = list(v.get("product_refs") or [])
        if not refs and ctx.product_ref(i):
            refs = [ctx.product_ref(i)]
        kbm = ctx.kb_message_for(refs[0] if refs else None, v["text"])
        proofs = ctx.related_evidence(v["text"], 2)
        body_bits = []
        if refs:
            body_bits.append(refs[0].get("name") or "")
        if kbm:
            body_bits.append(kbm["text"])
        elif proofs:
            body_bits.append(proofs[0]["text"])
        pillars.append({"id": new_id("vpl"), "title": short_phrase(v["text"], LIMITS["item_title"]), "body": cut(" · ".join(b for b in body_bits if b), LIMITS["item_body"]),
                        "proof_ids": [p["id"] for p in proofs] + ([kbm["id"]] if kbm else []), "product_refs": refs[:2],
                        "km_ref": v.get("km_id"), "material_id": v["id"]})
    if extra and pillars:
        last = pillars[-1]
        last["body"] = cut((last["body"] + " · " if last["body"] else "") + "함께: " + " · ".join(extra), LIMITS["item_body"] + 20)
    i = len(pillars)
    for ref in ctx.products:
        if len(pillars) >= n:
            break
        kbm = ctx.kb_title_for(ref)
        if not kbm or any(p["title"] == kbm["text"] for p in pillars):
            continue
        pillars.append({"id": new_id("vpl"), "title": cut(kbm["text"], LIMITS["item_title"]), "body": ref.get("name") or "",
                        "proof_ids": [kbm["id"]], "product_refs": [ref], "km_ref": None, "from_kb": True})
        i += 1
    for ch in ctx.challenges:
        if len(pillars) >= n:
            break
        title = f"{short_phrase(ch['text'], 14)} 해결"
        if any(p["title"] == title for p in pillars):
            continue
        ref = ctx.product_ref(len(pillars))
        pillars.append({"id": new_id("vpl"), "title": title, "body": (ref or {}).get("name") or "[확인 필요]", "proof_ids": [ch["id"]],
                        "product_refs": [ref] if ref else [], "km_ref": None, "from_challenge": True})
    while len(pillars) < n:
        pillars.append({"id": new_id("vpl"), "title": "[확인 필요]", "body": "", "proof_ids": [], "product_refs": [], "km_ref": None})
    return pillars[:n]


def det_one_liner(ctx: Ctx) -> dict[str, Any]:
    vals = ctx.values
    if len(vals) == 1 or (vals and ctx.doc.get("facts", {}).get("km_count") == 1):
        statement = vals[0]["text"]
    elif vals:
        statement = " · ".join(v["text"] for v in vals[:2])
    elif ctx.products:
        kbm = ctx.kb_message_for(ctx.products[0])
        statement = kbm["text"] if kbm else "[확인 필요]"
    else:
        statement = "[확인 필요]"
    ev: list[str] = []
    for e in ctx.evidence[:3]:
        ev.append(e["text"])
    for v in vals[2:]:
        if len(ev) >= 3:
            break
        ev.append(v["text"])
    for c in ctx.challenges:
        if len(ev) >= 3:
            break
        ev.append(f"{c['text']} 해결")
    while len(ev) < 3:
        ev.append("[확인 필요]")
    return {"statement": cut(statement, 60), "evidence": [cut(x, 40) for x in ev[:3]], "image_slot_id": None}


def det_stakeholders(ctx: Ctx, n: int) -> list[dict[str, Any]]:
    out = []
    dms = list(ctx.rfp.get("decision_makers") or [])
    roles: list[tuple[str, str, dict[str, Any] | None]] = []
    for d in dms:
        roles.append((d.get("role") or "", d.get("kpi") or "", None))
    for m in ctx.stakeholders:
        role = m["text"].split(" · ")[0]
        if all(role != r[0] and role not in r[0] for r in roles):
            roles.append((role, "", m))
    vals = ctx.values or []
    for i, (role, kpi, m) in enumerate(roles[:n]):
        v = vals[i % len(vals)] if vals else None
        refs = list((v or {}).get("product_refs") or []) or ([ctx.product_ref(i)] if ctx.product_ref(i) else [])
        out.append({"id": new_id("vsk"), "role": role, "kpi": kpi or "", "value": cut((v or {}).get("text") or "[확인 필요]", LIMITS["item_body"]),
                    "product_refs": refs[:2], "image_slot_id": None})
    return out


def det_pairs(ctx: Ctx, code: str) -> list[dict[str, Any]]:
    c = catalog.norm(code)
    if c == "VP-U":
        qs = [m for m in ctx.challenges if signals.QUESTION_RE.search(m["text"])] or ctx.challenges
    else:
        qs = ctx.challenges
    out = []
    for i, ch in enumerate(qs[:3]):
        ref = None
        for r in ch.get("product_refs") or []:
            ref = r
            break
        ref = ref or ctx.product_ref(i)
        kbm = ctx.kb_message_for(ref, ch["text"])
        val = next((v["text"] for v in ctx.values if ref and any(x.get("id") == ref.get("id") for x in v.get("product_refs") or [])), None)
        out.append({"challenge": cut(ch["text"], 30), "product": ref, "value": cut(val or (kbm or {}).get("text") or "[확인 필요]", 50),
                    "image_slot_id": None})
    return out


def select_metrics(ctx: Ctx, code: str, existing: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """기대 효과 지표 — 사용자가 처리한 것은 그대로 두고, 재료 잡이 만든 후보에서 고른다."""
    keep = {m["label"]: m for m in existing or []}
    out = []
    for m in ctx.metrics:
        cur = keep.get(m["label"])
        out.append(copy.deepcopy(cur) if cur and cur.get("decided_by") else copy.deepcopy(m))
    for m in existing or []:
        if m["label"] not in {x["label"] for x in out} and m.get("decided_by") == "user":
            out.append(copy.deepcopy(m))
    cap = 4
    c = catalog.norm(code)
    if c == "EF-C":
        usable = [m for m in out if numbers.projected_usable(m)]
        rest = [m for m in out if not numbers.projected_usable(m)]
        out = usable[:2] + rest[: max(0, 2 - len(usable[:2]))] if usable else out[:2]
        cap = 2
    for m in out:
        numbers.decorate(m)
    return out[:cap]


def det_roi(ctx: Ctx, metrics: list[dict[str, Any]]) -> dict[str, Any] | None:
    q = ctx.quote
    inv = q.get("total")
    savings: list[float] = []
    basis = ""
    for m in metrics:
        a = m.get("after") or {}
        if (a.get("unit") or "") in ("원", "만", "억") and a.get("value") is not None:
            mult = {"원": 1, "만": 10000, "억": 100000000}[a["unit"]]
            lo = float(a["value"]) * mult
            hi = float(a.get("value2") or a["value"]) * mult
            savings = numbers.savings_scenarios(lo, hi)
            basis = a.get("estimate_basis") or m.get("source_label") or ""
            break
    inv_nv = numbers.nv(numbers.money_ko(inv), "secured" if inv else "missing", value=inv, unit="원",
                        source={"kind": "quote", "label": q.get("version_label") or "견적", "refs": [q.get("file_id") or ""]} if inv else None)
    sav = [numbers.nv(f"연 {numbers.fmt_num(round(s / 10000))}만 원", "estimated", value=s, unit="원",
                      source={"kind": "case", "label": basis or "절감액 범위", "refs": []}, basis=basis or None) for s in savings]
    pay = numbers.roi(inv, savings) if inv and savings else []
    return {"investment": inv_nv, "savings": sav, "payback_months": pay, "scenario_labels": ["보수", "기준", "낙관"][: len(sav) or 3],
            "quote_file_id": q.get("file_id")}


def det_qualitative(ctx: Ctx) -> list[str]:
    out = [v["text"] for v in ctx.values[:4]]
    for s in ctx.stakeholders:
        if len(out) >= 4:
            break
        if s.get("group") == "user":
            out.append(f"{s['text'].split(' · ')[0]}의 체감 변화 [확인 필요]")
    return [cut(x, 40) for x in out[:4]]


def title_of(ctx: Ctx, code: str, content: dict[str, Any]) -> str:
    c = catalog.norm(code)
    cust = ctx.customer
    ga = josa(cust, "이", "가")
    shape = shape_of(c)
    if shape == "challenges":
        n = len(content.get("challenges") or []) or 3
        if c == "CH-B":
            return f"{cust}의 지금과 바라는 모습"
        if c == "CH-C":
            return f"{cust}에서 반복되는 문제와 근본 원인"
        return f"{cust}{ga} 지금 겪는 {ko_n(n)} 가지 문제"
    if shape == "pillars":
        n = len(content.get("pillars") or []) or 3
        if c.startswith("VP-B"):
            return f"{cust}{ga} 얻는 {ko_n(n)} 가지 가치"
        if c == "VP-I":
            p = (ctx.products or [{}])[0].get("name") or "제품"
            return f"{p} 한 대로 얻는 가치"
        if c in ("VP-J", "VP-P"):
            p = next((x.get("name") for x in ctx.products if x.get("kind") == "solution"), None) or "솔루션"
            return f"{p} 화면 하나로 이어지는 운영"
        if c in ("VP-K", "VP-R"):
            return "공간마다 손님이 만나는 가치"
        if c in ("VP-L", "VP-S"):
            return "같은 자리, 도입 전과 후"
        if c == "VP-M":
            return f"제품 {ko_n(max(1, len(ctx.products)))} 종이 만드는 가치"
        if c == "VP-Q":
            return "같은 문제를 먼저 푼 곳"
        return f"{cust}{ga} 얻는 {ko_n(n)} 가지 가치와 그 가치를 만드는 제품"
    if shape == "one_liner":
        return f"{cust}에 드리는 한 문장"
    if shape == "stakeholders":
        return f"{cust}의 결정권자마다 다른 가치와 각자 쓰는 제품" if c != "VP-D" else f"{cust}의 결정권자마다 다른 가치"
    if shape == "pairs":
        if c == "VP-U":
            return "현장에서 받은 질문에 대한 답"
        return f"{cust}의 과제마다 맞는 제품과 가치"
    if c == "EF-B":
        roi = content.get("roi") or {}
        pay = [p for p in roi.get("payback_months") or [] if p]
        if pay:
            return f"투자 회수까지 약 {numbers.fmt_num(min(pay))}~{numbers.fmt_num(max(pay))}개월"
        return "투자 회수 기간 [00]개월"
    if c == "EF-C":
        return f"{cust}{ga} 체감할 변화 — 수치와 현장의 목소리"
    n = len(content.get("metrics") or []) or 3
    return f"도입 1년 후, {ko_n(n)} 가지 지표가 이렇게 달라집니다"


def points_of(code: str, content: dict[str, Any]) -> str:
    shape = shape_of(code)
    if shape == "challenges":
        chs = content.get("challenges") or []
        bits = []
        for ch in chs:
            imp = (ch.get("impact") or {}).get("display") or ""
            t = short_phrase(ch["title"], 14)
            bits.append(f"{t} {imp}" if imp and "[" not in imp else t)  # 빈 수치([00])는 카드 요약에 넣지 않는다
        if catalog.norm(code) == "CH-B" and chs and (chs[0].get("body") or "").strip():
            bits[0] = f"{bits[0]} → {short_phrase(chs[0]['body'], 18)}"
        return " · ".join(bits)
    if shape == "pillars":
        return " · ".join(p["title"] for p in content.get("pillars") or [])
    if shape == "one_liner":
        return (content.get("one_liner") or {}).get("statement") or ""
    if shape == "stakeholders":
        return " · ".join(f"{s['role']} — {s['value']}" for s in (content.get("stakeholders") or [])[:3])
    if shape == "pairs":
        return " · ".join(f"{p['challenge']} → {(p.get('product') or {}).get('name') or '제품'}" for p in (content.get("pairs") or [])[:3])
    ms = content.get("metrics") or []
    if catalog.norm(code) == "EF-B":
        roi = content.get("roi") or {}
        inv = (roi.get("investment") or {}).get("display") or "[00]억 원"
        return f"투자비 {inv} · 절감액 범위 {len(roi.get('savings') or []) or '[00]'}개 시나리오"
    if not ms:
        return " · ".join(content.get("qualitative") or [])
    first = ms[0]
    head = f"{first['label']} {first['before']['display']} → {first['after']['display']}"
    return " · ".join([head] + [m["label"] for m in ms[1:]])


def deterministic(doc: dict[str, Any], sheet: dict[str, Any], ctx: Ctx | None = None) -> dict[str, Any]:
    ctx = ctx or Ctx(doc)
    code = sheet["layout"]["code"]
    shape = shape_of(code)
    content: dict[str, Any] = {}
    if sheet.get("kind") == "reference":
        content["reference"] = (sheet.get("content") or {}).get("reference")
        content["pillars"] = det_pillars(ctx, 3)
    elif shape == "challenges":
        content["challenges"] = det_challenges(ctx, 3)
        if catalog.norm(code) == "CH-B":
            tb = to_be_texts(ctx)
            for i, ch in enumerate(content["challenges"]):
                ch["body"] = short_phrase(tb[i % len(tb)], 30) if tb else "[확인 필요]"
        if catalog.is_pack(code):
            content["pairs"] = det_pairs(ctx, code)
    elif shape == "pillars":
        n = catalog.pillars_of(code) or (2 if catalog.norm(code) in ("VP-L", "VP-S") else 4 if catalog.norm(code) in ("VP-M", "VP-O") else 3)
        content["pillars"] = det_pillars(ctx, n)
    elif shape == "one_liner":
        content["one_liner"] = det_one_liner(ctx)
        content["pillars"] = det_pillars(ctx, 1)
    elif shape == "stakeholders":
        content["stakeholders"] = det_stakeholders(ctx, 4 if catalog.norm(code) == "VP-H" else 3)
    elif shape == "pairs":
        content["pairs"] = det_pairs(ctx, code)
        if catalog.is_pack(code):
            content["challenges"] = det_challenges(ctx, 3)
    else:
        existing = ((sheet.get("content") or {}).get("metrics")) or None
        ms = select_metrics(ctx, code, existing)
        content["metrics"] = ms
        if catalog.norm(code) == "EF-C" or not ms:
            content["qualitative"] = det_qualitative(ctx)
        if catalog.norm(code) == "EF-B":
            content["roi"] = det_roi(ctx, ms)
    return content


# ── LLM 다듬기 ─────────────────────────────────────────────

def _slots_text(code: str) -> str:
    shape = shape_of(code)
    n = catalog.pillars_of(code) or 3
    return {
        "challenges": f"title ≤ {LIMITS['title']}자 · points ≤ {LIMITS['points']}자 · challenges 3개(title ≤ 24자 · body ≤ 60자 · impact_number_id)",
        "pillars": f"title ≤ {LIMITS['title']}자 · points ≤ {LIMITS['points']}자 · pillars {n}개(title ≤ {LIMITS['item_title']}자 · body ≤ {LIMITS['item_body']}자 · proof_ids · product_ids)",
        "one_liner": "title · one_liner(statement ≤ 60자 · evidence_ids 3)",
        "stakeholders": "title · stakeholders(role · kpi · value ≤ 60자 · product_ids)",
        "pairs": "title · pairs(challenge · product_id · value ≤ 50자)",
        "metrics": "title · points · metric_ids(순서) · qualitative(체감 문장)",
    }[shape]


def prompt_of(doc: dict[str, Any], sheet: dict[str, Any], draft: dict[str, Any], ctx: Ctx, memos: list[str]) -> str:
    code = sheet["layout"]["code"]
    e = catalog.entry(code) or {}
    lines = [f"역할: {sheet['role']} ({sheet.get('step_label') or ''}) · 레이아웃: {code} {e.get('name', '')}",
             f"칸: {_slots_text(code)}", f"고객사: {ctx.customer} · 업종: {ctx.industry.get('name') or '범용'}", "", "재료(id):"]
    for h, m in list(ctx.handles.items())[:40]:
        num = f" · 수치 {m['number']['display']}" if m.get("number") else ""
        lines.append(f"- [{h}] ({materials.AXIS_KO.get(m['axis'], m['axis'])} · {ctx.src_line(m)}) {m['text']}{num}")
    if ctx.products:
        lines.append("제품(id):")
        lines += [f"- [{p.get('id')}] {p.get('name')} ({p.get('kind')})" for p in ctx.products[:8]]
    if ctx.metrics:
        lines.append("수치(id):")
        lines += [f"- [{h}] {m['label']}: 지금 {m['before']['display']} → 도입 후 {m['after']['display']}" for h, m in list(ctx.metric_handles.items())[:8]]
    if ctx.kb_messages:
        lines.append("KB 메시지(id · 삼성 공식):")
        lines += [f"- [{k['id']}] ({k.get('about_name') or ''}) {k.get('text')}" for k in ctx.kb_messages[:12]]
    if memos:
        lines.append("조종 메모(반영): " + " / ".join(memos))
    lines.append("")
    lines.append("초안(재료 그대로 — 다듬되 사실 · 수치는 바꾸지 않는다):")
    lines.append(llm.dump(_draft_view(draft)))
    return "\n".join(lines)


def _draft_view(c: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if c.get("challenges"):
        out["challenges"] = [{"title": x["title"], "impact": (x.get("impact") or {}).get("display")} for x in c["challenges"]]
    if c.get("pillars"):
        out["pillars"] = [{"title": p["title"], "body": p.get("body"), "products": [r.get("name") for r in p.get("product_refs") or []]} for p in c["pillars"]]
    if c.get("one_liner"):
        out["one_liner"] = c["one_liner"]
    if c.get("stakeholders"):
        out["stakeholders"] = [{"role": s["role"], "kpi": s.get("kpi"), "value": s.get("value")} for s in c["stakeholders"]]
    if c.get("pairs"):
        out["pairs"] = [{"challenge": p["challenge"], "product": (p.get("product") or {}).get("name"), "value": p.get("value")} for p in c["pairs"]]
    if c.get("metrics"):
        out["metrics"] = [{"label": m["label"]} for m in c["metrics"]]
    if c.get("qualitative"):
        out["qualitative"] = c["qualitative"]
    return out


def merge_llm(draft: dict[str, Any], out: dict[str, Any] | None, ctx: Ctx) -> tuple[dict[str, Any], str | None, str | None]:
    """LLM 결과 → (content, title, points). 틀린 id · 빈 값은 초안 그대로."""
    if not out:
        return draft, None, None
    c = copy.deepcopy(draft)
    pid = {p.get("id"): p for p in ctx.products}
    kb_ids = {k.get("id") for k in ctx.kb_messages}

    def mat_id(h: str) -> str | None:
        if h in ctx.handles:
            return ctx.handles[h]["id"]
        return h if h in kb_ids else None
    if c.get("challenges") and out.get("challenges"):
        mets = ctx.metric_handles
        for ch, o in zip(c["challenges"], out["challenges"]):
            if clean(o.get("title")):
                ch["title"] = cut(o["title"], 30)
            if clean(o.get("body")):
                ch["body"] = cut(o["body"], 70)
            nid = o.get("impact_number_id") or ""
            if nid in mets and (mets[nid].get("before") or {}).get("status") in numbers.USABLE:
                ch["impact"] = mets[nid]["before"]
            elif nid in ctx.handles and ctx.handles[nid].get("number"):
                ch["impact"] = ctx.handles[nid]["number"]
    if c.get("pillars") and out.get("pillars"):
        for p, o in zip(c["pillars"], out["pillars"]):
            if clean(o.get("title")):
                p["title"] = cut(o["title"], LIMITS["item_title"])
            if clean(o.get("body")):
                p["body"] = cut(o["body"], LIMITS["item_body"])
            proofs = [x for x in (mat_id(i) for i in o.get("proof_ids") or []) if x]
            if proofs:
                p["proof_ids"] = proofs
            prods = [pid[i] for i in o.get("product_ids") or [] if i in pid]
            if prods:
                p["product_refs"] = prods[:2]
            if o.get("km_ref"):
                p["km_ref"] = p.get("km_ref") or o["km_ref"]
    if c.get("one_liner") and out.get("one_liner"):
        o = out["one_liner"]
        if clean(o.get("statement")):
            c["one_liner"]["statement"] = cut(o["statement"], 60)
        ev = [cut(ctx.handles[i]["text"], 40) for i in o.get("evidence_ids") or [] if i in ctx.handles]
        ev += [cut(x, 40) for x in o.get("evidence") or [] if clean(x)]
        if len(ev) >= 1:
            c["one_liner"]["evidence"] = (ev + c["one_liner"]["evidence"])[:3]
    if c.get("stakeholders") and out.get("stakeholders"):
        for s, o in zip(c["stakeholders"], out["stakeholders"]):
            for k in ("role", "kpi", "value"):
                if clean(o.get(k)):
                    s[k] = cut(o[k], 60)
            prods = [pid[i] for i in o.get("product_ids") or [] if i in pid]
            if prods:
                s["product_refs"] = prods[:2]
    if c.get("pairs") and out.get("pairs"):
        for p, o in zip(c["pairs"], out["pairs"]):
            if clean(o.get("challenge")):
                p["challenge"] = cut(o["challenge"], 30)
            if clean(o.get("value")):
                p["value"] = cut(o["value"], 50)
            if o.get("product_id") in pid:
                p["product"] = pid[o["product_id"]]
    if c.get("metrics") is not None and out.get("metric_ids"):
        labels = [ctx.metric_handles[i]["label"] for i in out["metric_ids"] if i in ctx.metric_handles]
        by = {m["label"]: m for m in c["metrics"]}
        order = [lab for lab in labels if lab in by]
        if order:
            c["metrics"] = [by[lab] for lab in order] + [m for m in c["metrics"] if m["label"] not in order]
    if out.get("qualitative") and c.get("qualitative") is not None:
        q = [cut(x, 40) for x in out["qualitative"] if clean(x)]
        if q:
            c["qualitative"] = q[:4]
    return c, clean(out.get("title")), clean(out.get("points"))


async def write_sheet(doc: dict[str, Any], sheet: dict[str, Any], *, memos: list[str] | None = None, use_llm: bool = True) -> dict[str, Any]:
    """시트 하나 작성 → 고친 사본(title · points · content · speaker_notes · status=done)."""
    ctx = Ctx(doc)
    s = copy.deepcopy(sheet)
    draft = deterministic(doc, s, ctx)
    title = points = None
    if use_llm:
        out = await llm.try_call("vp.write_sheet.v1", prompt_of(doc, s, draft, ctx, memos or []), llm.WriteSheet)
        draft, title, points = merge_llm(draft, out, ctx)
    s["content"] = {**{k: None for k in ("challenges", "pillars", "one_liner", "stakeholders", "pairs", "metrics", "qualitative", "roi", "reference")},
                    **draft}
    if s.get("kind") == "reference" and (sheet.get("content") or {}).get("reference"):
        s["content"]["reference"] = sheet["content"]["reference"]
    code = s["layout"]["code"]
    s["title"] = cut(title or title_of(ctx, code, s["content"]), LIMITS["title"])
    if s.get("kind") == "reference":
        ref = s["content"].get("reference") or {}
        s["title"] = cut(ref.get("title") or "같은 문제를 먼저 푼 곳", LIMITS["title"])
    s["points"] = cut(points or points_of(code, s["content"]), LIMITS["points"])
    s["speaker_notes"] = notes_of(ctx, s)
    s["status"] = "done"
    return s


def notes_of(ctx: Ctx, s: dict[str, Any]) -> str:
    out = []
    c = s.get("content") or {}
    used: list[str] = []
    for ch in c.get("challenges") or []:
        used += ch.get("source_ids") or []
    for p in c.get("pillars") or []:
        used += [p.get("material_id")] if p.get("material_id") else []
        used += p.get("proof_ids") or []
    srcs = []
    for i in used:
        m = ctx.by_id.get(i)
        if m:
            srcs.append(ctx.src_line(m))
    if srcs:
        out.append("근거: " + " / ".join(dict.fromkeys(x for x in srcs if x)))
    if any(ch.get("body", "").endswith("[확인 필요]") for ch in c.get("challenges") or []):
        out.append("추론한 과제는 고객 확인 전 [확인 필요]")
    return "\n".join(out)


def meta_label(doc: dict[str, Any], s: dict[str, Any]) -> str:
    c = s.get("content") or {}
    refs: set[str] = set()
    for ch in c.get("challenges") or []:
        refs.update(ch.get("source_ids") or [])
    for p in c.get("pillars") or []:
        if p.get("material_id"):
            refs.add(p["material_id"])
        refs.update(p.get("proof_ids") or [])
    by = {m["id"]: m for m in doc.get("materials") or []}
    n = sum(max(1, len((by.get(i) or {}).get("sources") or [])) for i in refs)
    est = 0
    for m in c.get("metrics") or []:
        n += sum(1 for side in ("before", "after") if (m.get(side) or {}).get("status") == "secured")
        if numbers.metric_status(m) == "estimated":
            est += 1
    for ch in c.get("challenges") or []:
        if (ch.get("impact") or {}).get("status") == "estimated":
            est += 1
    if c.get("stakeholders"):
        n += len(c["stakeholders"])
    if c.get("pairs"):
        n += len(c["pairs"])
    if c.get("one_liner"):
        n += len([e for e in c["one_liner"].get("evidence") or [] if e and "[확인 필요]" not in e])
    slots = [x for x in doc.get("image_slots") or [] if x.get("sheet_id") == s["id"] and not x.get("extra")]
    if slots:
        k = sum(1 for x in slots if x.get("tier") in ("cut", "ui", "case") and x.get("asset"))
        return f"근거 {n} · 공식 실사 {k}"
    return f"근거 {n} · 추정 {est}"
