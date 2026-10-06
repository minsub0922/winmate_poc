"""그래프 공용 — 진행 추적(MI3G) · 근거(evidence) 모으기 · 주장 넣기 + 검증 · 영역 재사용 · 예산 · 웹 모드(§7.1 · §7.5 · §7.6)."""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.ids import now_iso
from winmate_common.jobs import JobContext

from .. import aix, claims as C, config, kbx, rules, verify
from .. import store as R
from ..store import nid

log = logging.getLogger("winmate.mi.graph")

STAGES = (("search", "검색"), ("organize", "정리"), ("write", "작성"))
URL_RE = re.compile(r"https?://[^\s\)\]\}\"'<>，。、]+")
KIND_LABEL = {"web": "공개 자료", "websearch_summary": "웹 검색 요약", "kb_case": "사내 사례 DB", "kb_official": "삼성 공식", "file": "사내 자료"}


def h(*parts: Any) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:16]


# ── 예산 · 웹 상태 ───────────────────────────────────────
@dataclass
class Budget:
    websearch: int = 16
    fetch: int = 30
    llm: int = 40
    used: dict[str, int] = field(default_factory=lambda: {"websearch": 0, "fetch": 0, "llm": 0})
    web_unavailable: bool = False
    mode: str = "summary_only"
    caps: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def for_depth(cls, depth: int) -> "Budget":
        b = config.routing().get("budgets", {}).get(str(depth)) or {"websearch": 16, "fetch": 30, "llm": 40}
        return cls(websearch=int(b["websearch"]), fetch=int(b["fetch"]), llm=int(b["llm"]))

    def take(self, kind: str) -> bool:
        cap = getattr(self, kind)
        if self.used[kind] >= cap:
            return False
        self.used[kind] += 1
        return True


async def init_web(budget: Budget) -> None:
    caps = await aix.capabilities()
    budget.caps = caps
    budget.mode = aix.web_mode(caps)
    ws = caps.get("websearch") or {}
    if caps and ws and ws.get("available") is False:
        budget.web_unavailable = True


# ── 진행 추적(MI3G §4.10 · §6.4) ─────────────────────────
class RunTracker:
    def __init__(self, ctx: JobContext | None, aid: str, areas: list[str], reused: list[str], eta0: int, *, header: dict[str, Any] | None = None):
        self.ctx = ctx
        self.aid = aid
        self.areas = areas
        self.reused = set(reused)
        self.todo = [a for a in areas if a not in self.reused]
        self.eta0 = eta0
        self.t0 = time.time()
        self.samples: list[tuple[float, int]] = []
        self.stage = "search"
        self.stage_status = {s: "wait" for s, _ in STAGES}
        self.stage_note = {s: "" for s, _ in STAGES}
        self.area_status: dict[str, str] = {a: ("done" if a in self.reused else "wait") for a in areas}
        self.area_note: dict[str, str] = {a: ("이전 결과 그대로" if a in self.reused else "") for a in areas}
        self.gathered: set[str] = set()
        self.organized: set[str] = set(self.reused)
        self.write_total = 1
        self.write_done = 0
        self.sources = {"total": 0, "used": 0, "checking": 0, "excluded": 0}
        self.recent: list[dict[str, str]] = []
        self.header = header or {}
        self.last_pct = 0

    def pct(self) -> int:
        n = max(1, len(self.todo))
        search = 1.0 if not self.todo else len(self.gathered) / n
        organize = 1.0 if not self.todo else len([a for a in self.todo if a in self.organized]) / n
        write = self.write_done / max(1, self.write_total)
        p = rules.progress_pct(search, organize, write)
        self.last_pct = max(self.last_pct, min(99, p))
        return self.last_pct

    def eta(self, pct: int) -> int:
        now = time.time()
        self.samples.append((now, pct))
        self.samples = [s for s in self.samples if now - s[0] <= 60]
        if len(self.samples) >= 2 and self.samples[-1][1] > self.samples[0][1] and now - self.samples[0][0] >= 5:
            speed = (self.samples[-1][1] - self.samples[0][1]) / (self.samples[-1][0] - self.samples[0][0])
            return int((100 - pct) / speed)
        return int(self.eta0 * (1 - pct / 100))

    def add_source(self, kind: str, name: str, state: str) -> None:
        self.recent.insert(0, {"kind": "사내" if kind in ("kb_case", "kb_official", "file") else "공개", "name": name[:60],
                               "state": {"used": "사용", "checking": "확인 중"}.get(state, state)})
        self.recent = self.recent[:4]

    def set_counts(self, version: dict[str, Any]) -> None:
        srcs = list((version.get("sources") or {}).values())
        self.sources = {"total": len(srcs), "used": sum(1 for s in srcs if s.get("state", "used") == "used"),
                        "checking": sum(1 for s in srcs if s.get("state") == "checking"),
                        "excluded": sum(1 for s in srcs if s.get("state") == "excluded")}

    def snapshot(self) -> dict[str, Any]:
        pct = self.pct()
        eta = self.eta(pct)
        stages = []
        for s, name in STAGES:
            st = self.stage_status[s]
            note = self.stage_note[s]
            if s == "search":
                note = f"출처 {self.sources['total']}곳 확인" + (" · 완료" if st == "done" else "")
            elif s == "organize":
                done = len([a for a in self.areas if a in self.organized])
                note = f"영역 {done} / {len(self.areas)} 정리됨"
            elif s == "write":
                note = "결과 · 비교표 · 삼성 강점" if "competitor" in self.areas else "결과"
            stages.append({"stage": s, "name": name, "status": st, "note": note})
        areas = [{"area": a, "name": rules.AREA_TAB[a], "status": self.area_status[a], "note": self.area_note.get(a, "")} for a in self.areas]
        previewable = [a for a in self.areas if self.area_status.get(a) == "done"]
        return {"pct": pct, "eta_s": eta, "stage": self.stage, "stages": stages, "areas": areas, "sources": dict(self.sources),
                "recent_sources": list(self.recent), "previewable": previewable, **self.header}

    async def emit(self, message: str | None = None) -> None:
        snap = self.snapshot()
        cur = next((s for s in snap["stages"] if s["stage"] == self.stage), snap["stages"][0])
        data = {"stage": self.stage, "stage_status": cur["status"], "stage_note": cur["note"], "areas": snap["areas"], "sources": snap["sources"],
                "recent_sources": snap["recent_sources"], "previewable": snap["previewable"], "stages": snap["stages"]}
        await R.call(R.update_draft, self.aid, lambda d: d.update(progress=snap))
        await R.call(R.update_analysis, self.aid, lambda d: d.setdefault("run", {}).update(stage=self.stage, sources_total=self.sources["total"]))
        if self.ctx is None:
            return
        await self.ctx.jobs.emit(self.ctx.job.id, "step", data)
        await self.ctx.progress(snap["pct"], message or f"{dict(STAGES)[self.stage]} 중", eta_s=snap["eta_s"], stage=self.stage)

    async def set_stage(self, stage: str) -> None:
        for s, _ in STAGES:
            if s == stage:
                self.stage_status[s] = "run"
                break
            self.stage_status[s] = "done"
        self.stage = stage
        await self.emit()


async def memo_log(ctx: JobContext | None, state_memos: list[str]) -> list[str]:
    """노드 경계 규칙 ② — 새 조종 메모를 모으고 log 이벤트를 낸다."""
    if ctx is None:
        return []
    new = await ctx.new_memos()
    texts = [m.get("text", "") for m in new if m.get("text")]
    for t in texts:
        state_memos.append(t)
        await ctx.log(f"메모를 반영했어요 · {t[:40]}", text=f"메모를 반영했어요 · {t[:40]}")
    return texts


# ── 출처 · 근거 ──────────────────────────────────────────
def add_source(version: dict[str, Any], src: dict[str, Any]) -> str:
    srcs = version.setdefault("sources", {})
    # 중복: 같은 최종 URL · 같은 kb 문서 · 같은 내용 해시 · 같은 요약
    for sid, s in srcs.items():
        same = (src.get("final_url") and s.get("final_url") == src.get("final_url")) or \
               (src.get("kb_key") and s.get("kb_key") == src.get("kb_key")) or \
               (src.get("content_hash") and s.get("content_hash") == src.get("content_hash") and s.get("kind") == src.get("kind"))
        if same:
            for a in src.get("areas") or []:
                if a not in s.setdefault("areas", []):
                    s["areas"].append(a)
            if src.get("competitor_id") and not s.get("competitor_id"):
                s["competitor_id"] = src["competitor_id"]
            return sid
    sid = src.get("id") or nid("src")
    src["id"] = sid
    src.setdefault("state", "used")
    src.setdefault("retrieved_at", now_iso())
    srcs[sid] = src
    return sid


def evidence(ev_list: list[dict[str, Any]], *, source_id: str, kind: str, title: str, text: str, page: int | None = None,
             label: str | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    e = {"id": f"E{len(ev_list) + 1}", "source_id": source_id, "kind": kind, "kind_label": label or KIND_LABEL.get(kind, kind), "title": title,
         "text": text or "", "page": page, **(extra or {})}
    ev_list.append(e)
    return e


def strip_urls(text: str) -> str:
    return re.sub(r"\s{2,}", " ", URL_RE.sub("", text or "")).strip()


def pub_from_text(text: str) -> str | None:
    """요약 · 본문에서 발행 연월(YYYY년 M월 · YYYY.MM · YYYY-MM)을 읽는다(가장 늦은 것)."""
    found = []
    for m in re.finditer(r"(20\d{2})\s*(?:년\s*(\d{1,2})\s*월|[.\-/](\d{1,2})(?![\d]))", text or ""):
        y = int(m.group(1))
        mo = int(m.group(2) or m.group(3) or 1)
        if 1 <= mo <= 12:
            found.append(f"{y:04d}-{mo:02d}-01")
    return max(found) if found else None


def subtype_for(url: str | None, title: str) -> tuple[str, int]:
    """(subtype, authority)."""
    u = (url or "").lower()
    t = title or ""
    if any(k in u for k in (".go.kr", "kosis", "gov", "dart.fss", "kostat")) or any(k in t for k in ("통계", "정부", "공시")):
        return "정부·통계", 1
    if any(k in u for k in ("/ir", "investor", "dart")) or any(k in t for k in ("IR", "사업보고서", "보도자료")):
        return "공시·IR", 2
    if any(k in u for k in ("news", "article", "press", "biz", "daily")) or "기사" in t:
        return "기사", 4
    if any(k in t for k in ("보고서", "리포트", "report")) or u.endswith(".pdf"):
        return "시장 보고서", 3
    if any(k in u for k in ("/product", "/solution", "/display", "/signage")) or "제품" in t:
        return "제품 페이지", 2
    return "기타", 5


async def web_gather(version: dict[str, Any], ev: list[dict[str, Any]], budget: Budget, tracker: RunTracker | None, *, task: str, query: str,
                     area: str, sensitive: list[str], competitor_id: str | None = None, recency_months: int = 24,
                     known_published: str | None = None) -> int:
    """웹 검색 1회 → 근거 · 출처 등록. 돌려주는 값 = 새 근거 수. 검색어 보호를 통과 못 하면 건너뛴다."""
    if budget.web_unavailable:
        return 0
    q = aix.query_guard(query, sensitive)
    if not q:
        return 0
    if not budget.take("websearch"):
        return 0
    try:
        res = await aix.websearch(task, q)
    except ApiError as exc:
        if exc.status in (429, 502, 503, 504) or exc.code in ("UPSTREAM_UNAVAILABLE", "TIMEOUT", "RATE_LIMITED", "DAILY_LIMIT_EXCEEDED", "PROVIDER_ERROR", "NOT_CONFIGURED"):
            budget.web_unavailable = True
            return 0
        raise
    added = 0
    summary = res.get("summary") or ""
    urls: list[tuple[str, str]] = []
    if budget.mode == "sources":
        for s in res.get("sources") or []:
            if s.get("url"):
                urls.append((s["url"], s.get("title") or ""))
        if (budget.caps.get("search_api") or {}).get("available"):
            try:
                sr = await aix.search(q, limit=3)
                for r in (sr.get("results") or [])[:3]:
                    urls.insert(0, (r["url"], r.get("title") or ""))
            except ApiError:
                pass
    for u in URL_RE.findall(summary):
        urls.append((u.rstrip(".,"), ""))
    fetched = 0
    seen = set()
    for url, title in urls:
        if url in seen:
            continue
        seen.add(url)
        if not budget.take("fetch"):
            break
        page = await aix.fetch(url)
        if not page:
            continue
        text = page.get("text") or "\n".join(page.get("pages") or [])
        final = page.get("final_url") or url
        sub, auth = subtype_for(final, page.get("title") or title)
        pub = page.get("published_at") or pub_from_text(text[:3000])
        src = {"kind": "web", "subtype": sub, "title": page.get("title") or title or final, "publisher": rules_host(final), "url": final,
               "final_url": final, "published_at": pub[:10] if pub else None, "published_basis": "meta" if page.get("published_at") else ("text" if pub else "unknown"),
               "retrieved_at": page.get("fetched_at") or now_iso(), "content_hash": page.get("content_hash") or h(text), "authority": auth,
               "classification": "public", "state": "used", "mode": budget.mode, "areas": [area], "competitor_id": competitor_id, "query": q}
        if src["published_at"] and rules.is_stale(src["published_at"]):
            # 24개월 넘음 → 제외 · 오래됨(대체 검색은 호출한 쪽에서 한 번 더)
            src["state"] = "excluded"
            src["excluded_reason"] = "stale"
        sid = add_source(version, src)
        if sid == src.get("id"):
            R.save_snapshot(sid, text, page.get("pages"))
        if tracker:
            tracker.add_source("web", src["title"], src["state"] if src["state"] != "excluded" else "제외 · 오래됨")
        if src["state"] != "excluded":
            pages = page.get("pages") or []
            if pages:
                for i, ptxt in enumerate(pages[:20], start=1):
                    evidence(ev, source_id=sid, kind="web", title=src["title"], text=ptxt, page=i, label=f"공개 자료 · {sub}")
            else:
                evidence(ev, source_id=sid, kind="web", title=src["title"], text=text, label=f"공개 자료 · {sub}")
            added += 1
        fetched += 1
    if summary and (budget.mode == "summary_only" or fetched == 0):
        stext = strip_urls(summary)
        pub = pub_from_text(stext) or known_published
        src = {"kind": "websearch_summary", "subtype": "", "title": f"웹 검색 요약 · {q}", "publisher": "웹 검색 요약", "url": None,
               "published_at": pub[:10] if pub else None, "published_basis": "text" if pub else "unknown", "retrieved_at": now_iso(),
               "content_hash": h(stext), "authority": 6, "classification": "public", "state": "used", "mode": budget.mode, "areas": [area],
               "competitor_id": competitor_id, "query": q, "summary": stext}
        if src["published_at"] and rules.is_stale(src["published_at"]):
            src["state"] = "excluded"
            src["excluded_reason"] = "stale"
        sid = add_source(version, src)
        if sid == src.get("id"):
            R.save_snapshot(sid, stext)
        if tracker:
            tracker.add_source("websearch_summary", src["title"], src["state"] if src["state"] != "excluded" else "제외 · 오래됨")
        if src["state"] != "excluded":
            evidence(ev, source_id=sid, kind="websearch_summary", title=src["title"], text=stext)
            added += 1
    if tracker:
        tracker.set_counts(version)
    return added


def rules_host(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url or "")
    return (m.group(1) if m else "").removeprefix("www.")


# ── kb 근거 ──────────────────────────────────────────────
async def kb_search_evidence(version: dict[str, Any], ev: list[dict[str, Any]], tracker: RunTracker | None, *, text: str, area: str, k: int = 4) -> int:
    res = await kbx.safe_query("search", {"text": text[:400] or "-", "k": k})
    if not res:
        return 0
    n = 0
    for ch in ((res.get("result") or {}).get("chunks") or [])[:k]:
        page_type = ch.get("page_type") or ""
        kind = "kb_case" if page_type == "case_study" else "kb_official"
        title = ch.get("title") or "삼성 사례"
        src = {"kind": kind, "subtype": "사례" if kind == "kb_case" else "메시지", "title": title, "publisher": "samsung.com", "url": ch.get("url"),
               "published_at": None, "published_basis": "kb", "retrieved_at": now_iso(), "authority": 2, "classification": "public", "state": "used",
               "mode": "kb", "areas": [area], "kb_key": f"chunk:{ch.get('chunk_id')}", "tier": "T3" if kind == "kb_case" else "T2",
               "kb_ref": {"pattern": "search", "entity_kind": "doc_block", "entity_id": ch.get("chunk_id"), "document_url": ch.get("url"), "tier": "T3"}}
        sid = add_source(version, src)
        if tracker:
            tracker.add_source(kind, title, "used")
        evidence(ev, source_id=sid, kind=kind, title=title, text=ch.get("text") or "")
        n += 1
    if tracker:
        tracker.set_counts(version)
    return n


async def kb_segment_evidence(version: dict[str, Any], ev: list[dict[str, Any]], tracker: RunTracker | None, *, segment: str, area: str) -> int:
    """업종 인사이트(사례 → 업종 분류 · 제품 · 솔루션 · 요구) → `사내 사례 DB` 도입 경향 근거."""
    if not segment or segment == "GEN":
        return 0
    try:
        ins = await kbx.insights(segment)
    except ApiError:
        return 0
    s = config.segment(segment)
    cases = int(ins.get("cases") or 0)
    if not cases:
        return 0
    prods = " · ".join(f"{p['name']} {p['n']}건" for p in (ins.get("products") or [])[:4])
    sols = " · ".join(f"{p['name']} {p['n']}건" for p in (ins.get("solutions") or [])[:4])
    lines = [f"{s['short']} 도입사례 {cases}건", f"많이 쓰인 제품: {prods}" if prods else "", f"많이 쓰인 솔루션: {sols}" if sols else ""]
    text = "\n".join(x for x in lines if x)
    title = f"{s['short']} 도입사례 {cases}건 (사례 DB)"
    src = {"kind": "kb_case", "subtype": "사례", "title": title, "publisher": "Samsung 사례 DB", "url": None, "published_at": None,
           "published_basis": "kb", "retrieved_at": now_iso(), "authority": 2, "classification": "public", "state": "used", "mode": "kb",
           "areas": [area], "kb_key": f"segment:{segment}", "tier": "T5", "kb_ref": {"pattern": "segments", "entity_kind": "vertical", "entity_id": s.get("kb_id")}}
    sid = add_source(version, src)
    if tracker:
        tracker.add_source("kb_case", title, "used")
    evidence(ev, source_id=sid, kind="kb_case", title=title, text=text)
    return 1


async def kb_cases_evidence(version: dict[str, Any], ev: list[dict[str, Any]], tracker: RunTracker | None, *, case_ids: list[str], area: str,
                            with_kpi: bool = False) -> int:
    n = 0
    for cid in case_ids[:5]:
        c = await kbx.case(cid)
        if not c:
            continue
        needs = [x.get("text", "") for x in c.get("needs") or [] if x.get("kind") == "needs"]
        kpis = [f"{k.get('label') or ''} {k.get('value') or ''}".strip() for k in c.get("kpis") or []] if with_kpi else []
        text = "\n".join(x for x in [c.get("quote") or "", ("요구: " + " · ".join(needs)) if needs else "", ("성과: " + " · ".join(kpis)) if kpis else ""] if x)
        if not text:
            continue
        src = {"kind": "kb_case", "subtype": "사례", "title": c.get("title") or cid, "publisher": "samsung.com", "url": c.get("url"),
               "published_at": None, "case_date": c.get("date"), "published_basis": "kb", "retrieved_at": now_iso(), "authority": 2,
               "classification": "public", "state": "used", "mode": "kb", "areas": [area], "kb_key": f"case:{cid}", "tier": "T3",
               "kb_ref": {"pattern": "D1", "entity_kind": "deployment", "entity_id": cid, "document_url": c.get("url"), "tier": c.get("source_tier")}}
        sid = add_source(version, src)
        if tracker:
            tracker.add_source("kb_case", src["title"], "used")
        evidence(ev, source_id=sid, kind="kb_case", title=src["title"], text=text)
        n += 1
    return n


async def file_evidence(version: dict[str, Any], ev: list[dict[str, Any]], tracker: RunTracker | None, *, analysis: dict[str, Any], area: str,
                        allow_confidential: bool = False, kinds: tuple[str, ...] | None = None) -> int:
    from winmate_common.platform import parsed_document

    n = 0
    excluded = set((analysis.get("internal") or {}).get("excluded_file_ids") or [])
    included = set((analysis.get("internal") or {}).get("included_file_ids") or [])
    for f in analysis.get("files") or []:
        if not f.get("include", True) or f["file_id"] in excluded:
            continue
        # 대외비 파일은 사용자가 사내 자료로 넣겠다고 고른 것만(넘길 때 묻기 3으로 다시 확인)
        if f.get("classification") == "confidential" and not allow_confidential and f["file_id"] not in included:
            continue
        if kinds and f.get("doc_kind") not in kinds:
            continue
        try:
            doc = await parsed_document(f["file_id"])
        except Exception:  # noqa: BLE001
            continue
        name = f.get("name") or doc.get("title") or "첨부"
        src = {"kind": "file", "subtype": f.get("doc_kind", "other"), "title": name, "publisher": analysis.get("owner_name", ""), "url": None,
               "file_id": f["file_id"], "published_at": None, "published_basis": "unknown", "retrieved_at": now_iso(), "authority": 2,
               "classification": "customer" if f.get("doc_kind") in ("rfp", "minutes", "customer_material") and f.get("classification") != "confidential"
               else f.get("classification", "internal"), "state": "used", "mode": "file", "areas": [area], "kb_key": f"file:{f['file_id']}",
               "page_count": doc.get("page_count")}
        sid = add_source(version, src)
        pages = doc.get("pages") or []
        texts = [p.get("text") or "" for p in pages] or [doc.get("text") or ""]
        R.save_snapshot(sid, doc.get("text") or "\n".join(texts), texts)
        if tracker:
            tracker.add_source("file", name, "used")
        for i, t in enumerate(texts[:20], start=1):
            if t.strip():
                evidence(ev, source_id=sid, kind="file", title=name, text=t, page=i if pages else None, label=f"사내 자료 · {name}")
        n += 1
    return n


# ── 주장 넣기 + 검증(§7.6) ───────────────────────────────
def _find_evidence(ev_by_id: dict[str, dict[str, Any]], ev_list: list[dict[str, Any]], evidence_id: str, quote: str) -> dict[str, Any] | None:
    """인용이 가리키는 근거. 번호가 틀렸어도 같은 구절이 다른 근거에 그대로 있으면 그 근거로 잇는다(결정적 대조).
    구절이 어디에도 없으면 가리킨 근거로 두어 QUOTE_NOT_FOUND 로 남긴다. 없는 번호면 None(인용 버림)."""
    e = ev_by_id.get(evidence_id)
    if e and verify.quote_check(quote, e["text"])[0] != "fail":
        return e
    for e2 in ev_list:
        if verify.quote_check(quote, e2["text"])[0] == "ok":
            return e2
    for e2 in ev_list:
        if verify.quote_check(quote, e2["text"])[0] == "partial":
            return e2
    return e


def ingest_claim(version: dict[str, Any], *, area: str, text: str, citations: list[dict[str, Any]], ev_list: list[dict[str, Any]],
                 block_path: str = "", metric_key: str | None = None, metric_label: str | None = None, known_names: list[str] | None = None,
                 inferred: bool = False, cell: dict[str, Any] | None = None, allow_kinds: tuple[str, ...] | None = None,
                 claim_id: str | None = None, extra: dict[str, Any] | None = None) -> str:
    """주장 하나: 인용 검사 → 요약 인용 정리 → 상태 모으기 → 근거 없는 수치 [00](§7.6.3~§7.6.6).
    주장 문장 속 URL 은 지운다(수집에 성공한 출처의 URL 만 출처 카드에 나간다, AC-MI-32)."""
    cid = claim_id or nid("clm")
    text = strip_urls(text)
    ev_by_id = {e["id"]: e for e in ev_list}
    srcs = version.setdefault("sources", {})
    cits: list[dict[str, Any]] = []
    seen_src: set[str] = set()
    for c in citations:
        e = _find_evidence(ev_by_id, ev_list, str(c.get("evidence_id") or ""), c.get("quote") or "")
        if e is None:
            continue
        src = srcs.get(e["source_id"]) or {}
        if allow_kinds and src.get("kind") not in allow_kinds:
            continue
        if allow_kinds and src.get("kind") == "file" and src.get("classification") in ("confidential", "internal"):
            continue
        if e["source_id"] in seen_src:
            continue
        res = verify.check_citation(claim_text=text, quote=c.get("quote") or "", source=src,
                                    source_text=e["text"], known_names=known_names)
        if res.drop:
            continue
        seen_src.add(e["source_id"])
        cits.append({"claim_id": cid, "source_id": e["source_id"], "quote": verify.strip_ellipsis(c.get("quote") or ""), "highlight": res.highlight,
                     "quote_span": list(res.quote_span) if res.quote_span else None, "page": e.get("page") or c.get("page"),
                     "check": res.check, "status": res.status, "reason_code": res.reason_code, "reason_text": res.reason_text,
                     "verified_at": now_iso(), "value": verify.num_to_dict(res.value)})
    removed = verify.prune_summary_citations(cits, srcs)
    live = [c for c in cits if not c.get("dropped")]
    masked, bad = verify.mask_unsupported(text, live)
    if any(n.kind != "year" for n in verify.parse_numbers(text)) and not live:
        masked, bad = verify.mask_unsupported(text, [])
    claim = {"id": cid, "area": area, "block_path": block_path, "text": masked, "orig_text": text if bad else None,
             "numbers": [verify.num_to_dict(n) for n in verify.parse_numbers(masked)], "metric_key": metric_key, "metric_label": metric_label,
             "inferred": inferred, "created_by": "agent", "unsupported": [n.raw for n in bad], "cell": cell, **(extra or {})}
    if bad:
        claim["reasons"] = [{"code": "NUMBER_UNSUPPORTED", "text": verify.reason_text("NUMBER_UNSUPPORTED")}]
    version.setdefault("claims", {})[cid] = claim
    version.setdefault("citations", []).extend(cits)
    C.recompute(version, cid)
    # 충돌이면 문장에 두 값을 함께(§7.6.5)
    cf = claim.get("conflict")
    if cf:
        other = [v for v in cf["values"] if v["source_id"] != cf["primary_source_id"]]
        if other:
            alt = verify.fmt_value(other[0]["value"], other[0]["unit"])
            if alt not in claim["text"]:
                claim["text"] = f"{claim['text'].rstrip('. ')} · 다른 출처 {alt}"
    if removed:
        C.refresh_source_states(version)
    return cid


def refresh_numeric_fields(version: dict[str, Any]) -> None:
    """블록의 숫자 칸(시장 규모 값 · 성장률 · 구성 비율)을 주장 문장에서 다시 읽는다(확정 · 재분석 뒤)."""
    doc = version.get("document") or {}
    claims = version.get("claims") or {}

    def val(cid: str | None) -> float | None:
        c = claims.get(cid or "") or {}
        if "[00]" in c.get("text", ""):
            return None
        nums = [n for n in verify.parse_numbers(c.get("text", "")) if n.kind != "year" and n.unit not in ("년", "개월")]
        if not nums:
            return None
        n = nums[0]
        return round(n.value / (n.mult or 1), 4)

    mk = doc.get("market") or {}
    for p in mk.get("size_series") or []:
        p["value"] = val(p.get("claim"))
    if mk.get("cagr"):
        mk["cagr"]["value"] = val(mk["cagr"].get("claim"))
    for c in (doc.get("user") or {}).get("composition") or []:
        c["value"] = val(c.get("claim"))


def copy_area(dst: dict[str, Any], src: dict[str, Any], area: str) -> None:
    """이전 버전의 영역 결과(블록 · 주장 · 인용 · 출처)를 그대로 옮긴다(재사용)."""
    dst.setdefault("document", {})[area] = copy.deepcopy((src.get("document") or {}).get(area))
    claims = {k: copy.deepcopy(v) for k, v in (src.get("claims") or {}).items() if v.get("area") == area}
    dst.setdefault("claims", {}).update(claims)
    cits = [copy.deepcopy(c) for c in src.get("citations") or [] if c.get("claim_id") in claims]
    dst.setdefault("citations", []).extend(cits)
    srcs = dst.setdefault("sources", {})
    for c in cits:
        s = (src.get("sources") or {}).get(c["source_id"])
        if s and c["source_id"] not in srcs:
            srcs[c["source_id"]] = copy.deepcopy(s)
    for sid, s in (src.get("sources") or {}).items():
        if area in (s.get("areas") or []) and sid not in srcs:
            srcs[sid] = copy.deepcopy(s)
    st = (src.get("area_status") or {}).get(area)
    dst.setdefault("area_status", {})[area] = "reused" if st in ("done", "reused") else (st or "reused")
    dst.setdefault("area_hashes", {})[area] = (src.get("area_hashes") or {}).get(area)
    if area == "competitor":
        dst.setdefault("area_hashes", {})["competitor_write"] = (src.get("area_hashes") or {}).get("competitor_write")


def drop_area(version: dict[str, Any], area: str) -> None:
    """영역을 다시 돌기 전에 그 영역 주장 · 인용을 지운다."""
    ids = {k for k, v in (version.get("claims") or {}).items() if v.get("area") == area}
    version["claims"] = {k: v for k, v in (version.get("claims") or {}).items() if k not in ids}
    version["citations"] = [c for c in version.get("citations") or [] if c.get("claim_id") not in ids]
    (version.get("document") or {}).pop(area, None)


def sensitive_texts(analysis: dict[str, Any]) -> list[str]:
    out = [analysis.get("requirements_text") or ""] + [r.get("text", "") for r in analysis.get("requirements") or []]
    ext = analysis.get("extracted") or {}
    out += ext.get("file_texts") or []
    if ext.get("author_note"):
        out.append(ext["author_note"])
    return [t for t in out if t]


def known_names(analysis: dict[str, Any]) -> list[str]:
    names = []
    for c in analysis.get("competitors") or []:
        names.append(c.get("real_name") or "")
    return [n for n in names if n]


def area_hashes(analysis: dict[str, Any], kb_ver: str) -> dict[str, str]:
    reqs = sorted((r.get("text") or "") for r in analysis.get("requirements") or []) + [analysis.get("requirements_text") or ""]
    seg = (analysis.get("segment") or {}).get("code")
    mix = (analysis.get("segment") or {}).get("mix")
    files = sorted((f["file_id"], f.get("classification"), f.get("include", True)) for f in analysis.get("files") or [])
    depth = (analysis.get("depth") or {}).get("target_sources")
    memos = [m.get("text") for m in analysis.get("memos") or [] if m.get("where") == "run"]
    comps = sorted((c.get("real_name") or "") for c in analysis.get("competitors") or [] if not c.get("removed"))
    crit_names = sorted(c["name"] for c in analysis.get("criteria") or [] if c.get("enabled", True))
    prods = sorted((p.get("ref") or p.get("model_code") or p.get("name") or "") for p in analysis.get("samsung_products") or [])
    crit_w = sorted((c["name"], c.get("weight"), c.get("order")) for c in analysis.get("criteria") or [] if c.get("enabled", True))
    extra_cases = sorted((analysis.get("extracted") or {}).get("extra_cases") or [])
    return {
        "market": h("market", seg, mix and mix.get("a"), reqs, depth, memos, kb_ver),
        "customer": h("customer", analysis.get("customer_name"), files, reqs, seg),
        "user": h("user", seg, mix and mix.get("c"), reqs, files),
        "competitor": h("competitor", comps, crit_names, prods, reqs, extra_cases),
        "competitor_write": h("competitor_write", crit_w),
    }


def table_text(analysis: dict[str, Any], version: dict[str, Any]) -> str:
    cp = (version.get("document") or {}).get("competitor") or {}
    table = cp.get("table") or {}
    crit = {c["id"]: c["name"] for c in analysis.get("criteria") or []}
    comps = {c["id"]: c for c in analysis.get("competitors") or []}
    lines = []
    for crt in table.get("criteria") or []:
        cells = []
        for col in table.get("columns") or []:
            cell = ((table.get("cells") or {}).get(crt) or {}).get(col) or {}
            name = "삼성" if col == "samsung" else f"{comps.get(col, {}).get('real_name', col)}({col})"
            cells.append(f"{name}: {cell.get('text', '')}")
        lines.append(f"[{crt}] {crit.get(crt, crt)} — " + " | ".join(cells))
    for s in cp.get("strengths") or []:
        lines.append(f"강점: {s.get('title')} — {s.get('note')}")
    return "\n".join(lines)


async def emit_partial(ctx: JobContext | None, data: dict[str, Any]) -> None:
    if ctx is not None:
        await ctx.partial(data)


async def gather_limited(coros: list[Any], limit: int) -> list[Any]:
    sem = asyncio.Semaphore(limit)

    async def run(c: Any) -> Any:
        async with sem:
            return await c

    return await asyncio.gather(*(run(c) for c in coros), return_exceptions=True)
