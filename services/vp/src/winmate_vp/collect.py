"""재료 잡 단계(05-vp.md §7.1) — 연결 자료 다시 읽기 · 첨부 판별/추출 · 업종 · 재료 · 정리 · 추론 · 수치 · 질문.

그래프 노드(workflows.vp_materials)가 문서 사본을 받아 이 함수들을 부른다. 모델 호출은 llm(confidential)만,
모델이 실패하거나 빈 값을 주면 결정적 대체 경로로 내려간다(지어내지 않는다 — 없으면 [00] · [확인 필요]).
"""
from __future__ import annotations

import logging
import re
from typing import Any

from winmate_common.ai import ai
from winmate_common.client import ServiceClient
from winmate_common.ids import new_id, now_iso
from winmate_common.platform import parsed_document

from . import config, coverage, decide, kbx, llm, materials, numbers, ops_work, signals, sources, writer
from .planner import Theme

log = logging.getLogger("winmate.vp.collect")

PROBLEM_WORDS = ("문제", "불편", "어려", "부족", "지연", "비용", "부담", "오류", "낭비", "느리", "개선이 필요", "번거", "늘어나", "대기",
                 "오표기", "누락", "손실")
TO_BE_WORDS = ("바라는", "원하는", "되도록", "목표", "하고 싶", "구현", "기대")
REPLACE_WORDS = ("교체", "리뉴얼", "노후", "기존 설비")
MODEL_RE = re.compile(r"\b([A-Z]{1,4}\d{2,3}[A-Z][A-Z0-9]{0,6})\b")
KIND_KO = {"rfp": "RFP", "quote": "견적", "meeting_notes": "회의록", "customer_photo": "고객 사진", "other": "기타"}


# ── 1. 연결 자료 다시 읽기 ───────────────────────────────────

async def refresh_sources(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """연결한 자료를 지금 판으로 다시 읽는다(실패하면 전에 읽은 후보를 그대로)."""
    out: list[dict[str, Any]] = []
    for i, s in enumerate([x for x in doc.get("sources") or [] if x.get("connected")], 1):
        data = await sources.load(s["kind"], s["ref_id"], idx=i)
        if data.get("error") and s.get("cand"):
            out.append(s)
            continue
        out.append({**s, "title": s.get("title") or data.get("title") or s["ref_id"], "gives": data.get("gives") or s.get("gives") or {},
                    "cand": data.get("candidates") or [], "industry": data.get("industry"), "customer": data.get("customer"),
                    "project_id": data.get("project_id"), "fetched_version": data.get("version"), "fetched_at": now_iso(),
                    "error": data.get("error"), "extra": ops_work._slim_extra(s["kind"], data.get("extra") or {})})
    return out


# ── 2. 첨부 읽기 ───────────────────────────────────────────

def _pages(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    pages = [{"no": int(p.get("no") or i), "text": (p.get("text") or "").strip(), "images": list(p.get("image_file_ids") or [])}
             for i, p in enumerate(parsed.get("pages") or [], 1)]
    if not pages and parsed.get("text"):
        pages = [{"no": 1, "text": str(parsed["text"]).strip(), "images": []}]
    for sh in parsed.get("sheets") or []:
        rows = [" · ".join(str(c) for c in r if c not in (None, "")) for r in (sh.get("rows") or [])[:200]]
        pages.append({"no": len(pages) + 1, "text": "\n".join(r for r in rows if r), "images": []})
    return pages


def _paged_text(pages: list[dict[str, Any]], limit: int = 12000) -> str:
    out, n = [], 0
    for p in pages:
        t = p["text"][:2500]
        if not t:
            continue
        chunk = f"[p.{p['no']}]\n{t}"
        if n + len(chunk) > limit:
            break
        out.append(chunk)
        n += len(chunk)
    return "\n\n".join(out)


def _lines(text: str) -> list[str]:
    parts = re.split(r"[\n\r]+|(?<=[.!?。])\s+", text or "")
    return [re.sub(r"^[\-•·*\d.)\s]+", "", p).strip() for p in parts if p and p.strip()]


JOSA_TAIL = re.compile(r"(이|가|은|는|을|를|의|께서|과|와|이다|이며|이고|에게|으로|로)$")
SENT_END = re.compile(r"(다|요|음|함|됨|임|것)[.!]?$")
NUM_LINE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(곳|개|억|만\s*원|원|%|분|시간|일|개월|명|대|건|배)")


def is_heading(line: str) -> bool:
    """`현황과 문제` 같은 소제목 — 짧고 서술어가 없다."""
    t = line.strip()
    return len(t) < 8 or (len(t) <= 16 and not SENT_END.search(t)) or " " not in t


def role_of(line: str, word: str) -> str:
    """`결재는 본사 운영본부장이 한다` → `본사 운영본부장`(결재 낱말 자체는 역할이 아니다)."""
    toks = line.replace(",", " ").split()
    for i, tok in enumerate(toks):
        if word in tok and tok.rstrip(".") not in ("결재는", "결재", "결재자", "결재자는"):
            core = JOSA_TAIL.sub("", tok.rstrip(".")) or tok
            prev = toks[i - 1] if i > 0 else ""
            if prev in ("본사", "본점", "그룹", "재단", "학교", "병원", "지점", "센터") and len(core) < 10:
                return f"{prev} {core}"
            return core
    return ""


def scan_numbers(pages: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    """쪽 텍스트 속 수치(단위 있는 것만, 평가 배점 제외) — 문장 그대로 근거로."""
    out = []
    for p in pages:
        for line in _lines(p["text"]):
            if "점" in line and re.search(r"\d+\s*점", line):
                continue
            m = NUM_LINE.search(line)
            if not m or len(out) >= limit:
                continue
            out.append({"text": _num_phrase(line, m), "quote": line[:120], "display": f"{m.group(1)}{m.group(2).replace(' ', '')}",
                        "page": p["no"]})
    return out


def _num_phrase(line: str, m: re.Match[str]) -> str:
    """수치 앞의 말 몇 낱말 + 수치(예 `직영 · 가맹 매장 320곳`) — 원문 그대로 잘라 쓴다."""
    words = line[:m.start()].rstrip().split(" ")
    acc: list[str] = []
    for w in reversed(words):
        if acc and len(" ".join([w] + acc)) > 14:
            break
        acc.insert(0, w)
    head = " ".join(acc).strip(" ·,:")
    num = f"{m.group(1)}{m.group(2).replace(' ', '')}"
    return f"{head} {num}" if head else line[:60]


def _chip(line: str) -> str:
    """RFP 문장 → 재료 칩 길이의 구(같은 말을 줄이기만 한다 — 원문은 quote 로 남긴다)."""
    full = line.strip().rstrip(".")
    short = writer.short_phrase(full, 24)
    return short if len(short) >= 6 else full


def heuristic_rfp(pages: list[dict[str, Any]]) -> dict[str, Any]:
    """LLM 없이 RFP · 회의록에서 과제 · 평가 기준 · 결재 구조를 고른다(문장 그대로 — 지어내지 않음)."""
    approver_words = config.routing()["stakeholder_groups"]["approver"]["words"]
    out: dict[str, Any] = {"customer": None, "challenges": [], "evaluation_criteria": [], "decision_makers": [], "to_be": [],
                           "competitor_mentions": [], "replacement": False}
    seen_dm: set[str] = set()
    for p in pages:
        for line in _lines(p["text"]):
            m = re.search(r"([가-힣A-Za-z][가-힣A-Za-z ·/()]{0,24}?)\s*[:：(]?\s*(\d{1,3})\s*점", line)
            if m and len(out["evaluation_criteria"]) < 8:
                out["evaluation_criteria"].append({"name": m.group(1).strip(" ·:("), "points": int(m.group(2)), "page": p["no"]})
                continue
            if is_heading(line):
                continue
            if any(w in line for w in REPLACE_WORDS):
                out["replacement"] = True
            for w in approver_words:
                if w == "결재" or w not in line:
                    continue
                role = role_of(line, w)
                if role and role not in seen_dm and len(out["decision_makers"]) < 5:
                    seen_dm.add(role)
                    out["decision_makers"].append({"role": role, "kpi": None, "page": p["no"]})
            if 6 <= len(line) <= 90 and any(w in line for w in PROBLEM_WORDS) and len(out["challenges"]) < 5:
                out["challenges"].append({"text": _chip(line), "page": p["no"], "quote": line})
            elif 6 <= len(line) <= 90 and any(w in line for w in TO_BE_WORDS) and len(out["to_be"]) < 3:
                out["to_be"].append({"text": _chip(line), "page": p["no"], "quote": line})
    return out


def heuristic_quote(text: str, filename: str) -> dict[str, Any]:
    out: dict[str, Any] = {"version_label": None, "total_investment": None, "items": [], "page": None}
    vm = re.search(r"[vV]\s?(\d{1,2})\b", filename or "") or re.search(r"[vV]\s?(\d{1,2})\b", (text or "")[:400])
    out["version_label"] = f"견적 v{vm.group(1)}" if vm else "견적"
    m = re.search(r"(합\s*계|총\s*액|총\s*금액|견적\s*금액|Total)[^\d\n]{0,12}([\d,]{4,})\s*(원|만\s*원|억\s*원)?", text or "")
    if m:
        v = float(m.group(2).replace(",", ""))
        unit = (m.group(3) or "원").replace(" ", "")
        v = v * (10000 if unit == "만원" else 100000000 if unit == "억원" else 1)
        out["total_investment"] = {"value": v, "currency": "KRW",
                                   "vat_included": True if re.search(r"(VAT|부가세)\s*포함", text or "") else None}
    return out


async def read_attachment(att: dict[str, Any]) -> dict[str, Any]:
    """첨부 하나 — 종류 판별 · 추출. 돌려준 사본에 status · detected_kind · summary · extract 가 들어 있다."""
    a = dict(att)
    kind = a.get("kind") or "other"
    try:
        if kind == "customer_photo":
            res = await llm.vision("vp.photo_classify.v1", [a["file_id"]],
                                   "제안서용 고객 현장 사진이다. 공간 종류 · 실내외 · 보이는 제품 범주 · 브랜드 노출 · 사람 수 · 품질을 JSON 으로.",
                                   llm.PhotoClassify)
            ex = res or {}
            a["extract"] = ex
            bits = [x for x in (ex.get("space_type_guess"), {"indoor": "실내", "outdoor": "실외"}.get(ex.get("indoor_outdoor") or "")) if x]
            a["summary"] = "고객 사진" + (f" · {' · '.join(bits)}" if bits else "")
            a["status"], a["detected_kind"] = "read", "customer_photo"
            return a
        parsed = await parsed_document(a["file_id"])
        pages = _pages(parsed)
        if not any(p["text"] for p in pages):
            imgs = [i for p in pages for i in p["images"]][:3]
            for i, fid in enumerate(imgs, 1):
                ocr = await llm.vision("vp.page_ocr.v1", [fid], "쪽 이미지의 글자를 그대로 옮겨 적는다.", llm.PageOcr)
                if ocr and ocr.get("text"):
                    pages.append({"no": i, "text": ocr["text"], "images": []})
        text = "\n".join(p["text"] for p in pages)
        if kind == "other":
            res = await llm.try_call("vp.attachment_kind.v1",
                                     f"파일 이름: {a.get('filename')}\n앞부분:\n{text[:1500]}\n\n이 파일의 종류를 고른다(rfp · quote · meeting_notes · customer_photo · other).",
                                     llm.AttachmentKindOut)
            if res and float(res.get("confidence") or 0) >= 0.5:
                kind = res["kind"]
            else:
                kind = ops_work.guess_kind(a.get("filename") or "", a.get("mime") or "")
                if kind == "other" and any(w in text[:3000] for w in ("제안요청", "평가 기준", "평가항목", "과업 내용")):
                    kind = "rfp"
            a["kind"] = kind
        a["detected_kind"] = kind
        if kind in ("rfp", "meeting_notes"):
            res = await llm.try_call("vp.rfp_extract.v1",
                                     f"{'RFP(제안요청서)' if kind == 'rfp' else '회의록'} 쪽 텍스트다. 고객이 직접 말한 과제 · 평가 기준(배점) · 결재 구조(역할 · KPI) · "
                                     f"바라는 모습 · 경쟁사 언급 · 기존 설비 교체 여부를 쪽 번호와 함께 원문 그대로 뽑는다.\n\n{_paged_text(pages)}",
                                     llm.RfpExtract)
            ex = res if res and (res.get("challenges") or res.get("evaluation_criteria") or res.get("decision_makers")) else heuristic_rfp(pages)
            ex["numbers"] = scan_numbers(pages)
            a["extract"] = ex
            a["text_head"] = text[:3000]
            a["summary"] = (f"{KIND_KO[kind]} · 과제 {len(ex.get('challenges') or [])} · 평가 기준 {len(ex.get('evaluation_criteria') or [])}"
                            f" · 결재 구조 {len(ex.get('decision_makers') or [])}")
        elif kind == "quote":
            res = await llm.try_call("vp.quote_extract.v1",
                                     f"견적서 쪽 텍스트다. 판(버전) 이름 · 총 투자비(원) · 품목(이름 · 수량 · 금액)을 원문 그대로 뽑는다.\n파일 이름: {a.get('filename')}\n\n{_paged_text(pages)}",
                                     llm.QuoteExtract)
            ex = res if res and res.get("total_investment") else heuristic_quote(text, a.get("filename") or "")
            a["text_head"] = text[:2000]
            if not ex.get("version_label"):
                ex["version_label"] = heuristic_quote("", a.get("filename") or "")["version_label"]
            a["extract"] = ex
            tot = (ex.get("total_investment") or {}).get("value")
            a["summary"] = f"{ex.get('version_label') or '견적'}" + (f" · 총 {numbers.money_ko(float(tot))}" if tot else " · 총액 [확인 필요]")
        else:
            a["extract"] = {"text": text[:4000]}
            a["summary"] = f"{KIND_KO.get(kind, '기타')} · {len(pages)}쪽"
        a["status"] = "read"
    except Exception as exc:  # noqa: BLE001 — 첨부 하나가 잡을 멈추지 않는다(기밀 차단은 위로)
        from winmate_common.errors import ApiError
        if isinstance(exc, ApiError) and exc.code == "POLICY_CONFIDENTIAL":
            raise
        log.warning("첨부 읽기 실패 %s: %s", a.get("file_id"), exc)
        a["status"] = "failed"
        a["summary"] = "읽지 못했어요"
    return a


def merge_attachment_facts(d: dict[str, Any]) -> None:
    """첨부 추출 → facts.rfp · facts.meeting · facts.quote."""
    f = d.setdefault("facts", {})
    rfp: dict[str, Any] = {}
    meet: dict[str, Any] = {}
    quote: dict[str, Any] | None = None
    for a in d.get("attachments") or []:
        ex = a.get("extract") or {}
        if a.get("status") != "read":
            continue
        if a.get("kind") in ("rfp", "meeting_notes"):
            tgt = rfp if a["kind"] == "rfp" else meet
            for k in ("challenges", "evaluation_criteria", "decision_makers", "to_be", "competitor_mentions", "numbers"):
                tgt.setdefault(k, []).extend(ex.get(k) or [])
            tgt["replacement"] = bool(tgt.get("replacement") or ex.get("replacement"))
            tgt.setdefault("att_ids", []).append(a["id"])
            tgt.setdefault("filenames", []).append(a.get("filename"))
            if ex.get("customer") and not tgt.get("customer"):
                tgt["customer"] = ex["customer"]
        elif a.get("kind") == "quote" and quote is None:
            tot = (ex.get("total_investment") or {}).get("value")
            quote = {"attached": True, "file_id": a["file_id"], "att_id": a["id"], "total": float(tot) if tot else None,
                     "currency": (ex.get("total_investment") or {}).get("currency") or "KRW",
                     "vat_included": (ex.get("total_investment") or {}).get("vat_included"),
                     "version_label": ex.get("version_label") or "견적", "items": ex.get("items") or [],
                     "source": "attached" if a.get("origin", "user") == "user" else "linked"}
    f["rfp"] = rfp or None
    f["meeting"] = meet or None
    if quote:
        f["quote"] = quote
    elif not any(a.get("kind") == "quote" for a in d.get("attachments") or []):
        f.pop("quote", None)


# ── 3. 업종 ───────────────────────────────────────────────

def industry_text(d: dict[str, Any]) -> str:
    f = d.get("facts") or {}
    parts = [d.get("customer_name") or "", d.get("note") or "", d.get("title") or ""]
    parts += [c.get("text", "") for c in ((f.get("rfp") or {}).get("challenges") or [])][:8]
    parts += [c.get("text", "") for s in d.get("sources") or [] if s.get("connected") for c in s.get("cand") or []][:30]
    return " ".join(p for p in parts if p)[:4000]


async def classify_industry(d: dict[str, Any], pack: dict[str, str]) -> dict[str, Any] | None:
    """§3.3 단계 2 — 고정 · 상속이면 그대로, 아니면 MI 판별기(대체: kb 빠른 경로)."""
    ind = d.get("industry") or {}
    if ind.get("mode") == "pin" or ind.get("source") in ("mi", "storyboard", "vp", "requirements", "proposal"):
        return ind or None
    text = industry_text(d)
    if not text.strip():
        return decide.decide_industry(candidates=[], pack_status=pack)
    cands: list[dict[str, Any]] = []
    try:
        res = await ServiceClient("mi").post("/v1/segments/detect", json={"text": text})
        cands = [{"code": c["code"], "confidence": float(c.get("confidence") or 0)} for c in (res or {}).get("candidates") or []]
    except Exception as exc:  # noqa: BLE001
        log.info("MI 업종 판별 실패 → kb 빠른 경로: %s", exc)
        cands = await kbx.segments_classify(text)
    return decide.decide_industry(candidates=cands, pack_status=pack)


# ── 4. 재료 ───────────────────────────────────────────────

def all_candidates(d: dict[str, Any]) -> list[dict[str, Any]]:
    f = d.get("facts") or {}
    cands = [c for s in d.get("sources") or [] if s.get("connected") for c in s.get("cand") or []]
    rfp = f.get("rfp") or {}
    if rfp:
        cands += materials.from_rfp(",".join(rfp.get("att_ids") or []), rfp, label="RFP")
    meet = f.get("meeting") or {}
    if meet:
        mc = materials.from_rfp(",".join(meet.get("att_ids") or []), meet, label="회의록")
        for c in mc:
            c["key"] = c["key"].replace("RFP-", "MTG-")
        cands += mc
    q = f.get("quote") or {}
    if q.get("total"):
        cands.append(materials._cand("QT-1", "evidence", f"투자비 {numbers.money_ko(q['total'])}", "QT", q.get("att_id") or "",
                                     locator=q.get("version_label"),
                                     number=numbers.nv(numbers.money_ko(q["total"]), "secured", value=q["total"], unit="원",
                                                       source={"kind": "quote", "label": q.get("version_label") or "견적", "refs": []})))
    cands += materials.from_note(d.get("note") or "")
    seen: set[str] = set()
    out = []
    for c in cands:
        if c["key"] in seen or not (c.get("text") or "").strip():
            continue
        seen.add(c["key"])
        out.append(c)
    return out


def _cand_line(c: dict[str, Any]) -> str:
    tag = materials.TAG_NAME.get(c["tag"], c["tag"])
    loc = f" · {c['locator']}" if c.get("locator") else ""
    num = f" · 수치 {c['number']['display']}" if c.get("number") else ""
    return f"- [{c['key']}] ({materials.AXIS_KO.get(c['axis'], c['axis'])} · {tag}{loc}) {c['text']}{num}"


async def extract_materials(d: dict[str, Any], cands: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    """5축 재료(LLM `vp.extract_materials.v1` — 후보 키로만) → 모델이 비우면 후보 그대로."""
    res = None
    if cands:
        prompt = (f"고객사: {d.get('customer_name') or '[확인 필요]'}\n덧붙인 말: {d.get('note') or '없음'}\n\n"
                  "아래 후보에서 가치 제안 재료를 5축(challenge · value · evidence · stakeholder · product)으로 고른다. "
                  "재료마다 source_ref 에 후보 키를 적고(여러 개면 쉼표), 같은 말은 하나로 합친다. 문장은 시트 칩 한 줄로 짧게. "
                  "수치는 후보에 있는 것만 number_ref 로 가리킨다. 축마다 6개까지.\n\n후보:\n" + "\n".join(_cand_line(c) for c in cands[:80]))
        res = await llm.try_call("vp.extract_materials.v1", prompt, llm.ExtractMaterials)
    items = materials.from_llm(cands, (res or {}).get("items") or [])
    topic = (res or {}).get("title")
    return items, (topic.strip() if isinstance(topic, str) and topic.strip() and not topic.startswith("[") else None)


async def resolve_products(d: dict[str, Any], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """재료 문장 · 견적 품목에서 제품 · 솔루션 해소(KB A1 · 모델 코드 검색) → 재료 product_refs · 공간."""
    f = d.setdefault("facts", {})
    texts = [m["text"] for m in items if not m.get("excluded")]
    texts += [i.get("name") or "" for i in ((f.get("quote") or {}).get("items") or [])]
    texts.append(d.get("note") or "")
    texts += [(a.get("text_head") or "")[:1500] for a in d.get("attachments") or [] if a.get("kind") in ("rfp", "quote", "meeting_notes")]
    blob = "\n".join(t for t in texts if t)[:4000]
    found: list[dict[str, Any]] = []
    spaces: list[dict[str, Any]] = []
    if blob.strip():
        r = await kbx.result("A1", {"text": blob})
        for ln in r.get("links") or []:
            t = ln.get("type")
            if t == "space_type":
                if ln.get("id") and all(s["id"] != ln["id"] for s in spaces):
                    spaces.append({"id": ln["id"], "name": ln.get("name") or ln.get("surface") or ln["id"]})
            elif t in ("family", "model", "solution", "category") and ln.get("id"):
                found.append({"kind": t, "id": ln["id"], "name": ln.get("surface") if t == "model" else (ln.get("name") or ln.get("surface")),
                              "surface": ln.get("surface") or "", "family_id": ln.get("family_id")})
        for code in dict.fromkeys(MODEL_RE.findall(blob)):
            if any(code == (x.get("surface") or "") for x in found):
                continue
            for it in (await kbx.product_search(code, limit=1))[:1]:
                if it.get("kind") == "model":
                    found.append({"kind": "model", "id": it["id"], "name": it.get("display_name") or code, "surface": code,
                                  "family_id": it.get("family_id")})
    for m in items:
        if m.get("axis") == "stakeholder" or m.get("excluded"):
            continue
        for p in found:
            ref = {k: v for k, v in p.items() if k != "surface"}
            if p["surface"] and p["surface"] in m["text"] and all(r.get("id") != p["id"] for r in m.get("product_refs") or []):
                m.setdefault("product_refs", []).append(ref)
    prods: list[dict[str, Any]] = []
    for p in found + [r for m in items if not m.get("excluded") for r in m.get("product_refs") or []]:
        ref = {k: v for k, v in p.items() if k != "surface"}
        if all(x.get("id") != ref.get("id") for x in prods):
            prods.append(ref)
    f["products"] = prods
    if spaces:
        f["spaces"] = spaces[:6]
    return items


# ── 5. 정리(합침 · 고쳐 씀 · 다시 찾음 · 충돌) ─────────────────

def _src_label(m: dict[str, Any]) -> str:
    tags = [materials.TAG_NAME.get(t["tag"], t["tag"]) for t in m.get("sources") or []]
    return " · ".join(dict.fromkeys(tags)) or "자료"


def _merged_item(group: list[dict[str, Any]], text: str, state: str) -> dict[str, Any]:
    base = group[0]
    tags: list[dict[str, Any]] = []
    for g in group:
        for t in g.get("sources") or []:
            if all((t["tag"], t.get("ref_id")) != (x["tag"], x.get("ref_id")) for x in tags):
                tags.append(t)
    refs: list[dict[str, Any]] = []
    for g in group:
        for r in g.get("product_refs") or []:
            if all(r.get("id") != x.get("id") for x in refs):
                refs.append(r)
    num = next((g.get("number") for g in group if g.get("number") and g["number"].get("status") in numbers.USABLE), None) \
        or next((g.get("number") for g in group if g.get("number")), None)
    return {**base, "id": new_id("vmi"), "text": text.strip(), "sources": tags, "state": state, "number": num, "product_refs": refs,
            "cost": any(g.get("cost") for g in group), "approver": any(g.get("approver") for g in group), "excluded": False,
            "origin_keys": list(dict.fromkeys(k for g in group for k in g.get("origin_keys") or [])),
            "km_id": next((g.get("km_id") for g in group if g.get("km_id")), None)}


def _fix(kind: str, from_text: str, to_text: str, mode: str, old: list[str], new: list[str], **extra: Any) -> dict[str, Any]:
    return {"id": new_id("vfx"), "kind": kind, "kind_label": {"merge": "합침", "rewrite": "고쳐 씀", "refetch": "다시 찾음"}[kind],
            "from_text": from_text, "to_text": to_text, "mode": mode, "decision": "pending" if mode == "check" else "accepted",
            "decided_by": None if mode == "check" else "default", "item_ids": old, "result_ids": new, **extra}


def dedupe_with_fixes(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """같은 축 · 같은 말(정규화 동일 또는 아주 비슷함)은 합친다(자동)."""
    fixes: list[dict[str, Any]] = []
    out = list(items)
    live = [m for m in out if not m.get("excluded") and m["axis"] in ("challenge", "value", "evidence")]
    used: set[str] = set()
    for i, a in enumerate(live):
        if a["id"] in used:
            continue
        group = [a]
        for b in live[i + 1:]:
            if b["id"] in used or b["axis"] != a["axis"]:
                continue
            same_src = {t["tag"] for t in a.get("sources") or []} == {t["tag"] for t in b.get("sources") or []}
            if materials._norm(a["text"]) == materials._norm(b["text"]) or (not same_src and materials.similar(a["text"], b["text"]) >= 88):
                group.append(b)
        if len(group) < 2:
            continue
        tags_a = {t["tag"] for t in a.get("sources") or []}
        if all(materials._norm(g["text"]) == materials._norm(a["text"]) and {t["tag"] for t in g.get("sources") or []} == tags_a for g in group):
            # 같은 자료에서 같은 말이 두 번 — 정리 기록 없이 하나만 남긴다
            for g in group[1:]:
                used.add(g["id"])
                g["excluded"] = True
                g["dup_of"] = a["id"]
            used.add(a["id"])
            continue
        for g in group:
            used.add(g["id"])
            g["excluded"] = True
        merged = _merged_item(group, min((g["text"] for g in group), key=len), "merged")
        out.append(merged)
        frm = " = ".join(f"'{g['text']}'({_src_label(g)})" for g in group[:2])
        fixes.append(_fix("merge", frm, f"'{merged['text']}' 하나로", "auto", [g["id"] for g in group], [merged["id"]]))
    return out, fixes


async def reconcile(d: dict[str, Any], items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    """LLM `vp.reconcile.v1`(합침 · 고쳐 씀 · 충돌) + 결정적 합침 → (재료, 정리, SB ↔ MI 충돌 요약)."""
    items, fixes = dedupe_with_fixes(items)
    live = materials.handles([m for m in items if not m.get("excluded") and m["axis"] != "product"])
    conflict: str | None = None
    if len(live) >= 2:
        lines = [f"- [{h}] ({materials.AXIS_KO[m['axis']]} · {_src_label(m)}) {m['text']}" for h, m in live.items()]
        res = await llm.try_call("vp.reconcile.v1",
                                 "재료 목록이다. 같은 말은 merges(합친 문장), 서로 부딪치는 말은 rewrites(둘 다 살린 한 문장 · 이유), "
                                 "Storyboard 와 MI 가 정반대를 말하면 conflicts 로. 재료는 [ ] 안의 이름으로만 가리키고 새 사실은 만들지 않는다.\n\n" + "\n".join(lines),
                                 llm.ReconcileOut)
        for mg in (res or {}).get("merges") or []:
            grp = [live[i] for i in mg.get("item_ids") or [] if i in live and not live[i].get("excluded")]
            if len(grp) < 2 or not (mg.get("merged_text") or "").strip() or str(mg.get("merged_text")).startswith("[mock"):
                continue
            for g in grp:
                g["excluded"] = True
            new = _merged_item(grp, mg["merged_text"], "merged")
            items.append(new)
            fixes.append(_fix("merge", " = ".join(f"'{g['text']}'({_src_label(g)})" for g in grp[:2]), f"'{new['text']}' 하나로", "auto",
                              [g["id"] for g in grp], [new["id"]]))
        for rw in (res or {}).get("rewrites") or []:
            grp = [live[i] for i in rw.get("item_ids") or [] if i in live and not live[i].get("excluded")]
            if not grp or not (rw.get("rewritten_text") or "").strip() or str(rw.get("rewritten_text")).startswith("[mock"):
                continue
            for g in grp:
                g["excluded"] = True
            new = _merged_item(grp, rw["rewritten_text"], "rewritten")
            items.append(new)
            frm = " ↔ ".join(f"{_src_label(g)} '{g['text']}'" for g in grp[:2])
            fixes.append(_fix("rewrite", frm, f"'{new['text']}'", "check", [g["id"] for g in grp], [new["id"]], reason=rw.get("reason") or ""))
        for cf in (res or {}).get("conflicts") or []:
            a, b = live.get(cf.get("a_item_id") or ""), live.get(cf.get("b_item_id") or "")
            if not a or not b or cf.get("kind") != "contradiction":
                continue
            ta = {t["tag"] for t in a.get("sources") or []}
            tb = {t["tag"] for t in b.get("sources") or []}
            if ({"SB"} <= ta and {"MI"} <= tb) or ({"MI"} <= ta and {"SB"} <= tb):
                sb, mi = (a, b) if "SB" in ta else (b, a)
                summ = cf.get("summary")
                conflict = summ if summ and not str(summ).startswith("[mock") else f"Storyboard '{sb['text']}' ↔ MI '{mi['text']}'"
    items, more = await refetch_stale(items)
    fixes += more
    return items, fixes, conflict


async def refetch_stale(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """출처 기한(24개월) 지난 수치 → 요약형 웹 검색으로 대체 출처 찾기(다시 찾음 · 자동). 못 찾으면 [확인 필요]."""
    limit = int(config.th("source_age_months"))
    fixes: list[dict[str, Any]] = []
    for m in items:
        if m.get("excluded") or m.get("age") is None or int(m.get("age") or 0) <= limit:
            continue
        label = re.sub(r"\[[^\]]*\]|\d[\d,.]*\s*%?", "", m["text"]).strip(" ·")
        found = None
        try:
            res = await ai().websearch("vp.refetch_source", f"{label} 최신 통계 리포트", max_sources=3)
            src = (res.get("sources") or [{}])[0] if res.get("sources") else {}
            if (res.get("summary") or "").strip() and not str(res.get("summary")).startswith("[mock"):
                found = src.get("title") or "최신 리포트 [기관, 연도]"
        except Exception as exc:  # noqa: BLE001
            log.info("다시 찾기 실패 %s: %s", label, exc)
        before = dict(m)
        unit = ((m.get("number") or {}).get("unit")) or ("%" if "%" in m["text"] else None)
        m["number"] = numbers.missing(unit)
        m["state"] = "refetched"
        m["text"] = f"{label} {numbers.placeholder(unit)}".strip()
        if found:
            to = "최신 리포트 [기관, 연도]로 교체" if found.startswith("최신 리포트") else f"최신 리포트 '{found}'로 교체"
            m["flags"] = list(dict.fromkeys((m.get("flags") or []) + ["출처 교체"]))
        else:
            to = "대체 자료를 못 찾아 [확인 필요]로 표시"
            m["flags"] = list(dict.fromkeys((m.get("flags") or []) + ["[확인 필요]"]))
        fixes.append(_fix("refetch", f"{_src_label(before)} 수치 '{label}' 출처가 {int(before.get('age') or 0)}개월 지남", to, "auto",
                          [m["id"]], [m["id"]], before_number=before.get("number"), before_text=before.get("text")))
    return items, fixes


# ── 6. 메모뿐 → 사례 DB로 과제 추론 ─────────────────────────

async def infer_from_memo(d: dict[str, Any], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    note = (d.get("note") or "").strip()
    vertical = (d.get("industry") or {}).get("kr_vertical_id")
    cases = await kbx.similar_cases(vertical=vertical, text=f"{d.get('customer_name') or ''} {note}", limit=3)
    added = 0
    for c in cases[:2]:
        did = c.get("id") or ""
        det = await kbx.case_detail(did) or {}
        for need in (det.get("needs") or c.get("needs") or [])[:2]:
            t = need.get("text") if isinstance(need, dict) else str(need)
            if not t or added >= 3:
                continue
            items.append({"id": new_id("vmi"), "key": f"CS-INF{added + 1}", "axis": "challenge", "text": t.strip()[:60],
                          "sources": [{"tag": "CS", "ref_id": did, "locator": None, "as_of": None}], "state": "inferred",
                          "number": None, "metric": None, "product_refs": [], "cost": materials.has_cost(t), "approver": False,
                          "group": None, "excluded": False, "flags": ["추론"], "origin_keys": []})
            added += 1
    if not added:
        e3 = await kbx.messages(vertical=vertical, products=None, customer=d.get("customer_name"), text=note)
        for km in (e3.get("key_messages") or [])[:2]:
            items.append({"id": new_id("vmi"), "key": f"KB-{km.get('id')}", "axis": "value", "text": km.get("text", "")[:60],
                          "sources": [{"tag": "KB", "ref_id": km.get("id") or "", "locator": None, "as_of": None}], "state": "inferred",
                          "number": None, "metric": None, "product_refs": [], "cost": False, "approver": False, "group": None,
                          "excluded": False, "flags": ["추론"], "origin_keys": [], "claim": bool(km.get("claim_flag"))})
    return items


# ── 7. 수치(기대 효과 지표) ─────────────────────────────────

def _label_of(text: str) -> str:
    from .writer import short_phrase
    t = re.sub(r"\[[^\]]*\]\s*\S*", "", text or "")
    t = re.sub(r"(연|월|매장당|건당|약)?\s*(?<![A-Za-z\d.])\d[\d,.]*\s*(?:~\s*\d[\d,.]*)?\s*(%|배|분|초|시간|일|개월|년|명|건|곳|대|억\s*원|만\s*원|원|만|억|kWh|W)?(?![A-Za-z\d])", "", t)
    return short_phrase(re.sub(r"\s{2,}", " ", t).strip(" ·,-"), 16)


SCALE_UNITS = ("곳", "개", "대", "명", "개소", "층")
# 기대 효과 지표가 될 수 있는 단위(전 → 후로 달라지는 값). 규모 · 건수 · 날짜 · 제품 스펙(인치 · W)은 지표로 쓰지 않는다.
KPI_UNITS = ("%", "배", "분", "초", "시간", "일", "개월", "원", "만원", "억원", "만", "억", "kWh", "회")


def _kpi_like(m: dict[str, Any]) -> bool:
    num = m.get("number") or {}
    unit = (num.get("unit") or "").replace(" ", "")
    text = m.get("text") or ""
    if unit not in KPI_UNITS or MODEL_RE.search(text):
        return False
    v = num.get("value")
    if isinstance(v, (int, float)) and 1990 <= v <= 2100 and unit in ("", "년"):
        return False
    return True


def metrics_from_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """재료 → 기대 효과 지표(전 → 후). 전 → 후 짝이 있는 재료 먼저, 수치 하나만 있는 근거는 '지금' 값으로."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in items:
        if m.get("excluded") or m["axis"] != "evidence":
            continue
        met = m.get("metric")
        if met and met.get("label"):
            lab = met["label"].strip()
            if lab in seen:
                continue
            seen.add(lab)
            out.append(numbers.new_metric(lab, met.get("before") or numbers.missing(), met.get("after") or numbers.missing(),
                                          source_label=_src_label(m), material_id=m["id"]))
    for m in items:
        if m.get("excluded") or m["axis"] != "evidence" or m.get("metric") or not m.get("number"):
            continue
        if any(t["tag"] == "QT" for t in m.get("sources") or []):
            continue
        if (m["number"].get("unit") or "") in SCALE_UNITS or not _kpi_like(m):
            continue
        lab = _label_of(m["text"])
        if not lab or lab in seen or len(lab) > 24:
            continue
        seen.add(lab)
        num = m["number"]
        out.append(numbers.new_metric(lab, num, numbers.missing(num.get("unit")), source_label=_src_label(m), material_id=m["id"]))
    return out[:6]


def metrics_from_challenges(items: list[dict[str, Any]], have: list[dict[str, Any]], *, limit: int = 4) -> list[dict[str, Any]]:
    """지표가 모자라면 상위 과제를 지표 이름으로(값은 [00] — 사례 · 업종 평균 · 요청으로 채운다)."""
    out = list(have)
    labels = {m["label"] for m in out}
    for m in writer.Ctx._order_ch([x for x in items if not x.get("excluded") and x["axis"] == "challenge"]):
        if len(out) >= limit:
            break
        lab = _label_of(m["text"])[:16]
        if not lab or lab in labels:
            continue
        labels.add(lab)
        unit = "원" if m.get("cost") else None
        out.append(numbers.new_metric(lab, numbers.missing(unit), numbers.missing(unit), source_label="없음", material_id=m["id"]))
    return out


_KPI_NUM = re.compile(r"(\d[\d,.]*)\s*(%|배|분|초|시간|일|개월|년|명|건|곳|대|원|만|억|kWh|W)")


def _kpi_numbers(text: str) -> list[tuple[float, str]]:
    out = []
    for v, u in _KPI_NUM.findall(text or ""):
        try:
            out.append((float(v.replace(",", "")), u))
        except ValueError:
            continue
    return out


async def case_ranges(metrics: list[dict[str, Any]], kpis: list[dict[str, Any]], *, basis: str) -> dict[str, dict[str, Any]]:
    """사례 KPI 문장 → 지표별 '도입 후' 범위(LLM `vp.kpi_metric_extract.v1`, 대체: 낱말 겹침 + 같은 단위 수치)."""
    if not metrics or not kpis:
        return {}
    by_label: dict[str, list[float]] = {}
    unit_of: dict[str, str] = {}
    refs: dict[str, list[str]] = {}
    lines = "\n".join(f"- [{k.get('id')}] {k.get('text')}" for k in kpis[:30] if k.get("has_number", True))
    res = await llm.try_call("vp.kpi_metric_extract.v1",
                             "지표 이름과 사례 KPI 문장(id)이다. 같은 지표를 말하는 KPI 만 골라 전 · 후 수치와 단위를 문장 그대로 옮긴다.\n"
                             f"지표: {', '.join(m['label'] for m in metrics)}\n\nKPI:\n{lines}", llm.KpiMetricExtract)
    kp = {k.get("id"): k for k in kpis}
    for mt in (res or {}).get("matches") or []:
        if mt.get("kpi_id") not in kp or mt.get("after") is None:
            continue
        lab = mt.get("metric_label") or ""
        if lab not in {m["label"] for m in metrics}:
            continue
        by_label.setdefault(lab, []).append(float(mt["after"]))
        unit_of[lab] = mt.get("unit") or unit_of.get(lab, "")
        refs.setdefault(lab, []).append(mt["kpi_id"])
    if not res:
        for m in metrics:
            words = [w for w in re.split(r"[\s·,]+", m["label"]) if len(w) >= 2]
            want = ((m.get("before") or {}).get("unit") or "").strip()
            for k in kpis:
                t = k.get("text") or ""
                if not words or not any(w in t for w in words):
                    continue
                for v, u in _kpi_numbers(t):
                    if want and u != want:
                        continue
                    by_label.setdefault(m["label"], []).append(v)
                    unit_of[m["label"]] = u
                    refs.setdefault(m["label"], []).append(k.get("id") or "")
                    break
    out = {}
    for lab, vals in by_label.items():
        lo, hi = min(vals), max(vals)
        out[lab] = {"after": [lo, hi], "unit": unit_of.get(lab, ""), "n": len(vals), "refs": refs.get(lab, []), "basis": basis.format(n=len(vals))}
    return out


async def fill_numbers(d: dict[str, Any], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """§4.17 찾는 순서 — 고객 자료(재료) → 유관 사례(D1 → D3) → 업종 평균(D2 → D3) → 비워 두고 요청."""
    f = d.setdefault("facts", {})
    ind = d.get("industry") or {}
    vertical = ind.get("kr_vertical_id")
    metrics = metrics_from_items(items)
    metrics = metrics_from_challenges(items, metrics, limit=4)
    case_ids = [s["ref_id"] for s in d.get("sources") or [] if s.get("connected") and s["kind"] == "case"]
    text = " ".join(m["text"] for m in items if not m.get("excluded"))[:1200]
    sim = await kbx.similar_cases(vertical=vertical, text=text, limit=3)
    case_ids += [c["id"] for c in sim if c.get("id") and c["id"] not in case_ids]
    same_vertical = [c for c in sim if vertical and float((c.get("similarity_breakdown") or {}).get("vertical") or 0) >= 1.0]
    f["same_vertical_case"] = bool(same_vertical)
    top = next((c for c in same_vertical if c.get("has_photos")), None)
    if top:
        imgs = await kbx.case_images(top["id"], limit=2)
        if imgs:
            f["case_photo"] = {"image_id": imgs[0]["id"], "deployment_id": top["id"], "title": top.get("title") or ""}
    kpis = await kbx.case_kpis(case_ids[:4])
    ranges = await case_ranges(metrics, kpis, basis="유관 사례 {n}건 범위")
    avg: dict[str, dict[str, Any]] = {}
    if vertical:
        same = await kbx.similar_cases(vertical=vertical, text="", limit=8)
        dep_ids = [x.get("id") for x in same if x.get("id")][:8]
        if dep_ids:
            vk = await kbx.case_kpis(dep_ids)
            avg = await case_ranges(metrics, vk, basis=f"{ind.get('cell') or ind.get('name') or '같은 업종'} 사례 {{n}}건 평균 범위")
    for m in metrics:
        r = ranges.get(m["label"])
        if r and (m.get("after") or {}).get("status") not in numbers.USABLE:
            lo, hi = r["after"]
            unit = r["unit"] or (m.get("after") or {}).get("unit") or ""
            m["after"] = numbers.nv(f"{numbers.range_display(lo, hi, unit)}", "estimated", value=lo, value2=hi if hi != lo else None, unit=unit,
                                    source={"kind": "case", "label": f"유관 사례 {r['n']}", "refs": r["refs"], "tier": "T3_case"},
                                    basis=r["basis"])
            m["source_label"] = (m.get("source_label") + " · " if m.get("source_label") and m["source_label"] != "없음" else "") + f"유관 사례 {r['n']}"
            m["how"] = f"사례 {r['n']}건 범위로 표기" if r["n"] >= 2 else "유관 사례 값 · [추정] 표시"
        a = avg.get(m["label"])
        if a:
            m["industry_avg"] = {"after": a["after"], "before": None, "unit": a["unit"], "basis": a["basis"], "refs": a["refs"]}
        numbers.decorate(m)
        if m["status"] == "ask" and not m.get("industry_avg") and m.get("source_label") == "없음":
            m["source_label"] = "없음 · 사례에도 없음"
    f["metrics"] = metrics
    f["per_product_numbers"] = False
    return metrics


# ── 8. 방향 테마 · 질문 ───────────────────────────────────

def keyword_themes(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """결정적 대체 — 테마 점수 = Σ w(출처) × 관련도 / Σ w(어느 테마든 관련 있는 재료만)."""
    words = config.routing().get("direction_words") or {}
    w_src = config.routing().get("direction_weights") or {}
    acc = {"gain": 0.0, "cost": 0.0}
    tot = 0.0
    for m in items:
        if m.get("excluded") or m["axis"] not in ("challenge", "value", "evidence"):
            continue
        rel = {k: (1.0 if any(w in m["text"] for w in (words.get(k) or {}).get("words") or []) else 0.0) for k in acc}
        if not any(rel.values()):
            continue
        w = max((float(w_src.get(t["tag"], 0.5)) for t in m.get("sources") or []), default=0.5)
        tot += w
        for k in acc:
            acc[k] += w * rel[k]
    if tot <= 0:
        return []
    out = []
    for k in ("gain", "cost"):
        if acc[k] > 0:
            out.append({"key": k, "label": (words.get(k) or {}).get("label") or ("매출" if k == "gain" else "비용"), "kind": k,
                        "score": round(acc[k] / tot, 2)})
    return out


NOTE_PRIORITY = re.compile(r"([가-힣A-Za-z][가-힣A-Za-z ·]{0,14}?)\s*(?:이|가|을|를)?\s*(?:1순위|1 순위|최우선|가장 중요|제일 중요|우선이)")


def note_priority(note: str) -> str | None:
    """메모의 우선순위 지시(예 `비용 절감이 1순위`) → gain | cost. 없으면 None."""
    m = NOTE_PRIORITY.search(note or "")
    if not m:
        return None
    words = config.routing().get("direction_words") or {}
    phrase = m.group(1)
    hits = [k for k in ("gain", "cost") if any(w in phrase for w in (words.get(k) or {}).get("words") or [])]
    return hits[0] if len(hits) == 1 else None


def _note_item(d: dict[str, Any]) -> list[dict[str, Any]]:
    """방향 점수용 메모(가중치 USER 0.5) — 재료로 남기지는 않는다."""
    note = (d.get("note") or "").strip()
    if not note:
        return []
    return [{"id": "note", "key": "USER-NOTE", "axis": "challenge", "text": note[:200], "sources": [{"tag": "USER", "ref_id": ""}]}]


def pin_direction(themes: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    words = config.routing().get("direction_words") or {}
    top = max((t["score"] for t in themes), default=0.0)
    out = [t for t in themes if t["kind"] != kind]
    out = [{**t, "score": round(min(t["score"], max(0.0, top - 0.2)), 2)} for t in out]
    return [{"key": kind, "label": (words.get(kind) or {}).get("label") or ("매출" if kind == "gain" else "비용"), "kind": kind,
             "score": round(max(top, 0.6), 2)}] + out


async def direction_themes(d: dict[str, Any], items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    live = [m for m in items if not m.get("excluded") and m["axis"] in ("challenge", "value", "evidence")] + _note_item(d)
    if not live:
        return [], None
    hs = materials.handles(live[:40])
    lines = "\n".join(f"- [{h}] ({_src_label(m)}) {m['text']}" for h, m in hs.items())
    res = await llm.try_call("vp.direction_tags.v1",
                             "재료마다 '매출 · 성장(gain)' 과 '비용 · 운영(cost)' 테마 관련도(0~1)를 매긴다. 테마 이름은 재료의 말로 짧게(예 매출 · 인건비). "
                             "summary 에는 'Storyboard는 …을, MI는 …를 가장 큰 과제로 봐요.' 처럼 재료 근거로만 한 문장.\n\n" + lines,
                             llm.DirectionTags)
    w_src = config.routing().get("direction_weights") or {}
    if res and res.get("themes") and res.get("relevance"):
        themes = {t["key"]: t for t in res["themes"] if t.get("key") and t.get("kind") in ("gain", "cost")}
        acc: dict[str, float] = {k: 0.0 for k in themes}
        tot = 0.0
        for h, m in hs.items():
            rels = [r for r in res["relevance"] if r.get("item_id") == h and r.get("theme_key") in themes]
            if not rels or not any(float(r.get("value") or 0) > 0 for r in rels):
                continue
            w = max((float(w_src.get(t["tag"], 0.5)) for t in m.get("sources") or []), default=0.5)
            tot += w
            for r in rels:
                acc[r["theme_key"]] += w * max(0.0, min(1.0, float(r.get("value") or 0)))
        if tot > 0:
            out = [{"key": t["kind"], "label": t["label"], "kind": t["kind"], "score": round(acc[k] / tot, 2)}
                   for k, t in themes.items() if acc[k] > 0]
            by_kind: dict[str, dict[str, Any]] = {}
            for t in sorted(out, key=lambda x: -x["score"]):
                by_kind.setdefault(t["kind"], t)
            summary = res.get("summary")
            return list(by_kind.values()), (summary if summary and not str(summary).startswith("[mock") else None)
    return keyword_themes(live), None


async def direction_first_messages(d: dict[str, Any], themes: list[dict[str, Any]], items: list[dict[str, Any]]) -> dict[str, str]:
    live = [m for m in items if not m.get("excluded") and m["axis"] in ("challenge", "value")]
    lines = "\n".join(f"- [{h}] {m['text']}" for h, m in materials.handles(live[:30]).items())
    res = await llm.try_call("vp.direction_options.v1",
                             "방향 테마별로 제안서의 첫 메시지 한 문장과 그 근거 제품을 재료 안에서만 쓴다. both 는 두 테마를 나란히 말하는 한 문장.\n"
                             f"테마: {', '.join(t['key'] + '=' + t['label'] for t in themes)}\n\n재료:\n{lines}", llm.DirectionOptions)
    out: dict[str, str] = {}
    for o in (res or {}).get("options") or []:
        msg = (o.get("first_message") or "").strip()
        if not msg or msg.startswith("[mock"):
            continue
        prods = " · ".join(p for p in o.get("products") or [] if p and not p.startswith("[mock"))
        out[o.get("theme_key") or ""] = f"'{msg.strip(chr(39))}'" + (f" — {prods}" if prods else "")
    if (res or {}).get("both") and not str(res["both"]).startswith("[mock"):
        out["both"] = res["both"]
    return out


def approver_unknown(d: dict[str, Any]) -> bool:
    """§3.4 2번 — 결재자를 모르고 RFP 도 없을 때."""
    has_rfp = bool((d.get("facts") or {}).get("rfp")) or any(a.get("kind") == "rfp" for a in d.get("attachments") or [])
    known = any(m.get("approver") for m in signals.active(d, "stakeholder"))
    return not known and not has_rfp


async def detect_questions(d: dict[str, Any], items: list[dict[str, Any]], conflict: str | None) -> list[dict[str, Any]]:
    f = d.setdefault("facts", {})
    themes, summary = await direction_themes(d, items)
    pinned = note_priority(d.get("note") or "")
    if pinned and themes:
        themes = pin_direction(themes, pinned)
        f["direction_from_note"] = pinned
    f["themes"] = themes
    f["direction_summary"] = summary
    p = signals.planner_input(d)
    p.themes = [Theme(**t) for t in themes]
    fm: dict[str, str] = {}
    if decide.needs_direction(p.themes):
        fm = await direction_first_messages(d, themes, items)
    has_rfp = bool(f.get("rfp"))
    qs = decide.detect_questions(p, industry=d.get("industry"), approver_unknown=approver_unknown(d), has_rfp=has_rfp,
                                 conflict=conflict, direction_context=summary, first_messages=fm)
    for q in qs:
        q["selected_keys"] = list(q.get("default_keys") or [])
    return qs


# ── 정리 요약(VP1A · VP1Q 문장) ─────────────────────────────

def stakeholder_from_keymen(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for s in d.get("sources") or []:
        if not s.get("connected"):
            continue
        for c in s.get("cand") or []:
            if c.get("tag") == "RQ" and c["axis"] == "stakeholder" and str(c.get("key", "")).startswith("RQ-KM"):
                out.append({"name": c["text"], "weight": c.get("weight"), "items": c.get("items") or [c["key"]]})
    return out


def group_fill(items: list[dict[str, Any]]) -> None:
    for m in items:
        if m.get("axis") == "stakeholder" and not m.get("group"):
            m["group"] = coverage.group_of(m["text"], approver=bool(m.get("approver")))
