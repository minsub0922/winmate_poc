"""기존 제안서 활용 — 원본 읽기 · 9기준 분석 · 활용 방식 추천 · 계획(개선 / 흐름 차용) (§7.10 · §7.11 · §10.9).

결정적 규칙이 먼저다(구조 · 비복제 · 제품 · 수치 · 이미지 · 매핑 · 요구사항 대조). LLM(`pr.reuse_*`)은 흐름 메모 · 패턴 · 핵심 메시지 ·
원본 고객 맥락처럼 해석이 필요한 곳에만 쓰고, **모든 호출은 confidential=true(고정)** 이다. 비복제 줄 · 쪽은 이후 어떤 입력에도 넣지 않는다.
"""
from __future__ import annotations

import copy
import logging
import re
from typing import Any

from . import clients, config, content as C, core, defs, repo, versions as VER
from .graphs import common as G

log = logging.getLogger("winmate.proposal.reuse")

PALETTE = ["#1428A0", "#2E7D32", "#C2185B", "#EF6C00", "#6A1B9A", "#00838F", "#5D4037", "#283593", "#AD1457", "#558B2F"]
EXCLUDED_COLOR = "#9E9E9E"
ROLE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("견적 · 일정", ("견적", "단가", "가격표", "할인", "VAT", "부가세", "계약 조건", "납기", "추진 일정", "도입 일정", "구축 일정")),
    ("Why Samsung · 경쟁 비교", ("Why Samsung", "경쟁 비교", "삼성이어야")),
    ("도입 사례", ("사례", "레퍼런스", "도입 고객")),
    ("제품 스펙", ("스펙", "사양", "제품 비교", "규격")),
    ("공간 시나리오", ("동선", "시나리오", "하루", "공간별")),
    ("솔루션 구성", ("솔루션", "구성도", "MagicINFO", "배치", "시스템", "아키텍처")),
    ("가치 제안", ("가치", "기대 효과", "효과", "Before", "After", "Key Message")),
    ("고객 과제", ("과제", "인터뷰", "운영 문제", "불편", "고객 니즈", "운영 과제")),
    ("시장 변화", ("시장", "트렌드", "추이", "동향", "도입 현황", "경쟁 브랜드")),
    ("문제 제기", ("기로", "왜 지금", "배경", "문제 제기", "변화의")),
]
SECTION_FLOW = {"mi": "시장 변화", "bigMi": "시장 변화", "vp": "가치 제안", "birdseye": "공간 시나리오", "spaceProducts": "솔루션 구성",
                "solution": "솔루션 구성", "cases": "도입 사례", "why": "Why Samsung · 경쟁 비교", "spec": "제품 스펙", "spaceScenario": "공간 시나리오"}
ROLE_FLOW = {"CH": "고객 과제", "CB": "시장 변화", "US": "시장 변화", "MS": "시장 변화", "TR": "시장 변화", "CP": "시장 변화", "IM": "시장 변화",
             "VP": "가치 제안", "EF": "가치 제안"}
WHY = "Why Samsung · 경쟁 비교"
MODEL_RE = re.compile(r"\b([A-Z]{2}\d{2}[A-Z]{1,2}\d?)\b")
SOL_VER_RE = re.compile(r"(MagicINFO)\s*(?:Server\s*|v)?([5-9])(?![\d.]|\s?[대개곳명종일%])")
YEAR_RE = re.compile(r"(20\d{2})(?:\s*년|\.\d{1,2}|\s*기준)")
NUM_UNIT_RE = re.compile(r"(\d[\d,.]*)\s?(%|억 원|억원|만 원|원|개|곳|명|일|시간|대|배)")
STORE_RE = re.compile(r"(\d{2,4})\s?(?:개\s?)?(?:매장|점포)")
# 비복제(기준 9) — 강한 키워드는 그것만으로, 약한 키워드는 금액 · 날짜가 함께 있을 때 후보(§10.9). 확정은 LLM(기밀).
NONCOPY_STRONG = ("견적", "단가", "VAT", "부가세", "매출", "영업이익", "원가", "납기", "계약금", "계약 조건")
NONCOPY_WEAK = ("가격", "할인", "계약", "일정")
MONEY_RE = re.compile(r"\d[\d,.]*\s?(원|만 원|만원|억 원|억원|천원|USD)|\$\s?\d")
DATE_RE = re.compile(r"20\d{2}\s?[.\-/년]\s?\d{1,2}|\d{1,2}\s?월\s?\d{1,2}\s?일|\d{1,2}/\d{1,2}|D-\d+|\d+\s?주차")
STOP = {"및", "등", "the", "에서", "으로", "하는", "있는", "위한", "그리고"}
CURRENT_SOL = {"MagicINFO": "9"}
STAT_ROLES = ("시장 변화", "가치 제안", "고객 과제", "문제 제기")      # 기준일이 의미 있는 수치(시장 · 효과)가 나오는 흐름 단계


def norm_name(s: str) -> str:
    s = re.sub(r"\(주\)|㈜|주식회사|프랜차이즈|\s+", "", s or "")
    return s.lower()


def tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[0-9A-Za-z가-힣]{2,}", s or "") if t not in STOP}


def contains_score(rq: str, page: str) -> float:
    """요구 문장의 단어가 쪽 글에 얼마나 들어 있나(부분 일치 포함)."""
    x = tokens(rq)
    if not x:
        return 0.0
    y = tokens(page)
    hit = sum(1 for t in x if t in y or any(t in u or (len(u) >= 2 and u in t) for u in y))
    return hit / len(x)


def gram3(s: str) -> set[str]:
    t = re.sub(r"[\s\W_]+", "", re.sub(r"\d", "#", s or ""))
    return {t[i:i + 3] for i in range(max(0, len(t) - 2))}


def similar(a: str, b: str) -> float:
    """줄 유사도(§10.12) — 공백 · 문장부호 제거, 숫자 → #, 글자 3-gram 자카드."""
    x, y = gram3(a), gram3(b)
    return len(x & y) / max(1, len(x | y)) if x and y else 0.0


def short_title(t: str, n: int = 16) -> str:
    t = (t or "").strip()
    if len(t) <= n:
        return t
    cut = t[:n]
    sp = max(cut.rfind(" "), cut.rfind("·"))
    return (cut[:sp] if sp >= n // 2 else cut).rstrip(" ·:,") + "…"


def is_noncopy_candidate(text: str) -> bool:
    t = text or ""
    if any(k in t for k in NONCOPY_STRONG):
        return True
    return any(k in t for k in NONCOPY_WEAK) and bool(MONEY_RE.search(t) or DATE_RE.search(t))


def role_of_text(title: str, text: str, *, first: bool = False) -> tuple[str, list[str], float]:
    """(역할, 후보, 신뢰도) — 키워드 규칙. 제목이 먼저, 본문은 보조."""
    if first:
        return "표지", ["표지"], 0.97
    hits: list[tuple[str, float]] = []
    for role, kws in ROLE_KEYWORDS:
        score = sum(2.0 for k in kws if k in (title or "")) + sum(0.5 for k in kws if k in (text or "")[:600])
        if score:
            hits.append((role, score))
    if not hits:
        return "가치 제안", ["가치 제안"], 0.55
    hits.sort(key=lambda x: -x[1])
    top = hits[0]
    conf = min(0.95, 0.6 + top[1] / 10)
    if len(hits) > 1 and hits[1][1] >= top[1] * 0.8 and top[0] != "견적 · 일정":
        return top[0], [top[0], hits[1][0]], 0.6
    return top[0], [top[0]], conf


def target_for(flow_role: str | None, title: str, keys: list[str], w: dict[str, Any] | None = None) -> tuple[str | None, str | None]:
    """원본 쪽 → 이번 제안서 (섹션, 시트 역할). Winmate 원본은 그 시트 자리를 먼저(§10.9 흐름 단계 → 섹션)."""
    if w and w.get("section_key") in keys:
        return w["section_key"], w.get("role")
    t = title or ""
    if flow_role == "시장 변화":
        sec = "mi" if "mi" in keys else ("bigMi" if "bigMi" in keys else None)
        if any(k in t for k in ("경쟁", "브랜드")):
            return sec, "CP"
        if any(k in t for k in ("트렌드", "추이", "동향")):
            return sec, "TR"
        if any(k in t for k in ("고객사", "비즈니스", "매장 수")):
            return sec, "CB"
        return sec, "MS"
    if flow_role in ("고객 과제", "문제 제기"):
        return ("vp" if "vp" in keys else None), "CH"
    if flow_role == "가치 제안":
        return ("vp" if "vp" in keys else None), ("EF" if "효과" in t else "VP")
    if flow_role == "솔루션 구성":
        if any(k in t for k in ("배치", "공간", "동선")) and "spaceProducts" in keys:
            return "spaceProducts", "SM"
        if "solution" in keys:
            return "solution", None
        if "spaceScenario" in keys:
            return "spaceScenario", "VM"
        return None, None
    if flow_role == "공간 시나리오":
        for k, r in (("spaceScenario", "SS"), ("spaceProducts", "PI"), ("solution", None)):
            if k in keys:
                return k, r
        return None, None
    if flow_role == "도입 사례":
        return ("cases" if "cases" in keys else None), "CD"
    if flow_role == "제품 스펙":
        return ("spec" if "spec" in keys else None), "SC"
    if flow_role == WHY:
        return ("why" if "why" in keys else None), "CM"
    return None, None


# ── 읽기 ───────────────────────────────────────────────────
def _body_lines(body: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for t in [body.get("subtitle"), body.get("message"), *[x if isinstance(x, str) else "" for x in body.get("bullets") or []],
              *[f"{x.get('title') or ''} · {x.get('body') or ''}".strip(" ·") for x in body.get("points") or [] if isinstance(x, dict)],
              *[f"{x.get('title') or ''} · {x.get('body') or ''}".strip(" ·") for x in body.get("steps") or [] if isinstance(x, dict)],
              *[f"{x.get('label') or ''} {x.get('value') or ''}{x.get('unit') or ''}".strip() for x in body.get("kpis") or [] if isinstance(x, dict)],
              *[f"{x.get('model') or x.get('name') or ''} {x.get('qty') or ''}".strip() for x in body.get("products") or [] if isinstance(x, dict)]]:
        if t and isinstance(t, str) and t.strip() and t not in out:
            out.append(t.strip())
    return out


async def read_sources(sources: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """→ (원본 메타[], 쪽[{no, source_idx, file_page, title, lines[{id, text}], notes, images[], winmate?, body?}])

    Winmate 원본은 버전 스냅숏(값 토큰은 원본 값으로 풀어 둠), 파일은 files 파싱 결과(쪽 · 노트 · 이미지 · 레이아웃).
    """
    pages: list[dict[str, Any]] = []
    metas: list[dict[str, Any]] = []
    for idx, src in enumerate(sources):
        if src.get("kind") == "proposal":
            sp = await repo.aget("proposals", src.get("proposal_id") or "")
            if not sp:
                continue
            v = src.get("version") or int(sp.get("saved_version") or 0)
            ver = await VER.get_version(sp["id"], v) if v else None
            snap = (ver or {}).get("snapshot") or await VER.snapshot(sp["id"])
            facts = {f["id"]: f for f in snap.get("facts") or [] if f.get("id")}
            by_key = {f.get("key"): f for f in facts.values()}
            sheets = sorted([s for s in snap.get("sheets") or [] if s.get("status") != "excluded" and not s.get("hidden")],
                            key=lambda s: (s.get("sheet_no") or 999, s.get("order") or 0))
            first_no = len(pages) + 1
            pages.append({"no": first_no, "source_idx": idx, "file_page": 1, "title": f"표지 · {core.title_display(sp)}", "lines": [],
                          "notes": "", "images": [], "winmate": {"role": "COVER", "section_key": None}, "body": {}})
            for s in sheets:
                body = C.walk_strings(copy.deepcopy(s.get("draft") or {}), lambda t, _p: C.resolve_text(t, facts, by_key=by_key))
                content = C.walk_strings(copy.deepcopy(s.get("content") or {}), lambda t, _p: C.resolve_text(t, facts, by_key=by_key))
                n = len(pages) + 1
                imgs = [{"kind": im.get("kind"), "id": im.get("id") or im.get("ref") or im.get("image_id"), "rights": im.get("rights"),
                         "label": im.get("label") or im.get("caption")}
                        for im in body.get("images") or [] if isinstance(im, dict)]
                # 줄은 사용자가 보고 고친 칸 글(content) 기준 — 칸이 비었으면 본문(draft)에서
                texts = [t for _p, t in C.content_lines(content)] or _body_lines(body)
                texts = list(dict.fromkeys(t.strip() for t in texts if t and t.strip()))
                t_ = s.get("template") or {}
                pages.append({"no": n, "source_idx": idx, "file_page": n - first_no + 1,
                              "title": content.get("title") or body.get("title") or s.get("title") or "", "sheet_title": s.get("title"),
                              "lines": [{"id": f"p{n}l{i}", "text": t} for i, t in enumerate(texts)], "notes": content.get("notes") or "",
                              "images": imgs, "body": body, "content": content,
                              "winmate": {"role": s.get("role"), "section_key": s.get("section_key"), "template": t_.get("code"),
                                          "product_count": t_.get("product_count"), "sheet_id": s["id"], "ident": s.get("ident"),
                                          "solution_code": s.get("solution_code"), "repeat_ref": (s.get("repeat_key") or {}).get("ref"),
                                          "sheet_no": s.get("sheet_no")}})
            metas.append({"kind": "proposal", "proposal_id": sp["id"], "version": v, "name": core.title_display(sp), "format": "winmate",
                          "pages": len(sheets) + 1, "author": sp.get("owner_name"),
                          "doc_date": (sp.get("submitted_at") or (ver or {}).get("created_iso") or sp.get("created_iso") or "")[:7].replace("-", "."),
                          "customer": (sp.get("customer") or {}).get("name"), "type": sp.get("type"),
                          "industry_code": (sp.get("customer") or {}).get("industry_code"), "status": sp.get("status"),
                          "rq_ref": sp.get("rq_ref"), "snapshot_hash": (ver or {}).get("hash")})
        else:
            fid = src.get("file_id") or ""
            meta = await clients.file_meta(fid) or {}
            from .graphs.start import parsed_pages
            try:
                _m, pgs = await parsed_pages(fid, wait_s=90)
            except Exception as exc:  # noqa: BLE001
                log.warning("원본 파싱 실패 %s: %s", fid, type(exc).__name__)
                pgs = []
            raw = await clients.call("files", "GET", f"/v1/files/{fid}/parsed", quiet=True) or {}
            raw_pages = {int(p.get("no") or 0): p for p in raw.get("pages") or []}
            first_n = len(pages) + 1
            for pg in pgs:
                rp = raw_pages.get(int(pg["no"])) or {}
                if rp.get("hidden"):
                    continue
                text = pg.get("text") or ""
                lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                title = (pg.get("title") or (lines[0] if lines else "")).strip()
                body_lines = [ln for ln in lines if ln != title]
                n = len(pages) + 1
                pages.append({"no": n, "source_idx": idx, "file_page": int(pg["no"]), "title": title,
                              "lines": [{"id": f"p{n}l{i}", "text": t} for i, t in enumerate(body_lines[:40])], "notes": rp.get("notes") or "",
                              "images": [{"kind": "file", "id": x, "file_id": x} for x in rp.get("image_file_ids") or []],
                              "layout": rp.get("layout"), "winmate": None, "file_id": fid})
            dp = meta.get("doc_props") if isinstance(meta.get("doc_props"), dict) else {}
            dm = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
            kind = (meta.get("kind") or "").lower()
            fmt = kind if kind in ("pptx", "pdf") else ("pptx" if (meta.get("name") or "").lower().endswith(".pptx") else "pdf")
            metas.append({"kind": "file", "file_id": fid, "name": meta.get("name") or fid, "format": fmt,
                          "pages": len([p for p in pages if p["source_idx"] == idx]) or int(meta.get("pages") or 0),
                          "author": dp.get("author") or dm.get("author") or meta.get("owner_name"),
                          "doc_date": (dp.get("created") or dm.get("created") or dp.get("modified") or meta.get("created_at") or "")[:7].replace("-", "."),
                          "customer": None, "first_page": first_n})
    return metas, pages


# ── 흐름 · 섹션(결정적 집계 — 역할을 고치면 바로 다시 계산) ─────────
def flow_steps(out_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for pg in out_pages:
        if pg["flow_role"] == "표지":
            continue
        if steps and steps[-1]["name"] == pg["flow_role"]:
            steps[-1]["count"] += 1
            steps[-1]["to"] = pg["no"]
        else:
            steps.append({"name": pg["flow_role"], "count": 1, "from": pg["no"], "to": pg["no"], "excluded": pg["excluded"], "dashed": False, "note": ""})
    if WHY not in {s["name"] for s in steps}:
        pos = next((i for i, s in enumerate(steps) if s["name"] in ("제품 스펙", "견적 · 일정")), len(steps))
        steps.insert(pos, {"name": WHY, "count": 0, "dashed": True, "excluded": False, "note": "원본에 없음 → 이번엔 추가 제안"})
    for s in steps:
        if s.get("excluded"):
            s["note"] = f"{s['count']}장 · 자동 제외"
        s["range"] = (f"p.{s['from']}–{s['to']}" if s.get("from") and s.get("to") and s["from"] != s["to"]
                      else (f"p.{s['from']}" if s.get("from") else ""))
    return steps


def page_sections(out_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for pg in out_pages:
        name = pg["flow_role"]
        w = pg.get("winmate") or {}
        if w.get("section_key"):
            name = defs.SECTIONS.get(w["section_key"], {}).get("name", name)
        elif w.get("role") == "COVER":
            name = "표지"
        if sections and sections[-1]["name"] == name and sections[-1]["excluded"] == pg["excluded"]:
            sections[-1]["count"] += 1
            sections[-1]["to"] = pg["no"]
        else:
            sections.append({"name": name, "count": 1, "from": pg["no"], "to": pg["no"], "excluded": pg["excluded"]})
    ci = 0
    for s in sections:
        if s["excluded"]:
            s["color"] = EXCLUDED_COLOR
        else:
            s["color"] = PALETTE[ci % len(PALETTE)]
            ci += 1
    for pg in out_pages:
        sec = next(s for s in sections if s["from"] <= pg["no"] <= s["to"])
        pg["section_name"], pg["section_color"] = sec["name"], sec["color"]
    return sections


def flow_summary(steps: list[dict[str, Any]], pattern: dict[str, Any], broken: list[str]) -> str:
    b = next((x for x in broken if "Why Samsung" in x), broken[0] if broken else None)
    return (" → ".join(s["name"].replace(" · 경쟁 비교", "") for s in steps if not s.get("dashed"))[:90] + f" · '{pattern.get('name') or '문제 해결형'}'" +
            (f" · {b.replace(' 단계 없음', ' 고리 없음')}" if b else ""))


def rebuild(a: dict[str, Any]) -> dict[str, Any]:
    """역할 태그를 고친 뒤 — 섹션 · 스토리라인 · 끊긴 고리 · 기준 2 요약을 다시(메모는 다음 분석에서)."""
    a["source_sections"] = page_sections(a["pages"])
    steps = flow_steps(a["pages"])
    fl = a.get("flow") or {}
    names = {s["name"] for s in steps if not s.get("dashed")}
    broken = [b for b in fl.get("broken") or [] if "Why Samsung" not in b]
    if WHY not in names:
        broken.append("Why Samsung 단계 없음")
    fl.update({"steps": [{k: s.get(k) for k in ("name", "count", "dashed", "excluded", "note", "range", "from", "to")} for s in steps],
               "broken": broken})
    a["flow"] = fl
    for c in a.get("criteria") or []:
        if c["no"] == 2 and c.get("state") != "edited":
            c["summary"] = flow_summary(steps, fl.get("pattern") or {}, broken)
    return a


# ── 9기준 ──────────────────────────────────────────────────
async def analyze(p: dict[str, Any], metas: list[dict[str, Any]], pages: list[dict[str, Any]], *, locks: dict[str, Any],
                  prev: dict[str, Any] | None) -> dict[str, Any]:
    prev = prev or {}
    prev_pages = {pg["no"]: pg for pg in prev.get("pages") or []}
    locked_pages = {int(x) for x in locks.get("pages") or []}
    out_pages = []
    by_no = {pg["no"]: pg for pg in pages}
    file_first = {m.get("first_page") for m in metas if m.get("kind") == "file"}
    # 1 · 2 구조 · 역할
    for pg in pages:
        w = pg.get("winmate") or None
        if w:
            if w["role"] == "COVER":
                role, cands, conf = "표지", ["표지"], 0.99
            else:
                role = ROLE_FLOW.get(w["role"] or "") or SECTION_FLOW.get(w.get("section_key") or "", "가치 제안")
                cands, conf = [role], 0.95
        else:
            role, cands, conf = role_of_text(pg["title"], " ".join(x["text"] for x in pg["lines"]), first=pg["no"] in file_first)
        state = "auto" if len(cands) < 2 else "need"
        pp = prev_pages.get(pg["no"]) or {}
        if pg["no"] in locked_pages and pp.get("flow_role"):
            role, state = pp["flow_role"], "edited"
        elif pp.get("role_state") == "ok" and pp.get("flow_role") == role:
            state = "ok"
        noncopy_page = role == "견적 · 일정"
        out_pages.append({"no": pg["no"], "source_idx": pg["source_idx"], "file_page": pg.get("file_page"), "title": pg["title"],
                          "text_excerpt": " · ".join(x["text"] for x in pg["lines"][:3])[:120], "flow_role": role, "role_state": state,
                          "role_candidates": cands, "confidence": conf, "excluded": noncopy_page,
                          "exclude_reason": "비복제 · 가격 · 견적 · 일정" if noncopy_page else None, "locked": pg["no"] in locked_pages,
                          "winmate": pg.get("winmate"), "images": pg.get("images") or [], "file_id": pg.get("file_id")})
    excluded = {pg["no"] for pg in out_pages if pg["excluded"]}
    # 9 비복제 줄 — 규칙 후보(제외 쪽은 이미 통째로 빠짐) → LLM 확정(기밀)
    cands_nc = [{"page": pg["no"], "line_id": ln["id"], "text": ln["text"]} for pg in pages if pg["no"] not in excluded
                for ln in pg["lines"] if is_noncopy_candidate(ln["text"])]
    noncopy_lines = list(cands_nc)
    if cands_nc:
        res = await G.llm_json("pr.reuse_noncopy", system="비복제 판정 — 가격 · 견적 · 단가 · 일정 · 고객 내부 수치(매출 등)만 비복제. 그 밖은 keep_ids 로.",
                               user="원본 제안서 줄(기밀). 비복제가 아니면 keep_ids 에 넣는다.\n" + "\n".join(f"- {x['line_id']} · {x['text'][:100]}" for x in cands_nc[:60]),
                               schema={"type": "object", "properties": {"keep_ids": {"type": "array", "items": {"type": "string"}}}},
                               confidential=True)
        keep = set((res or {}).get("keep_ids") or [])
        noncopy_lines = [x for x in cands_nc if x["line_id"] not in keep]
    nc_ids = {x["line_id"] for x in noncopy_lines}

    def clean_lines(no: int) -> list[dict[str, Any]]:
        return [x for x in by_no[no]["lines"] if x["id"] not in nc_ids] if no not in excluded else []

    sections = page_sections(out_pages)
    steps = flow_steps(out_pages)
    names = {s["name"] for s in steps if not s.get("dashed")}
    rq = [x for x in ((p.get("ctx") or {}).get("rq") or {}).get("items") or []]
    # 2 흐름 · 메모(LLM, 기밀) — 비복제 쪽 · 줄은 넣지 않는다
    text_for_llm = "\n".join(f"p.{pg['no']} [{pg['flow_role']}] {pg['title']} — " + " / ".join(x["text"][:60] for x in clean_lines(pg["no"]))[:200]
                             for pg in out_pages if not pg["excluded"])
    flow_res = await G.llm_json("pr.reuse_flow", system="원본 제안서의 설득 흐름 분석(기밀). 이번 요구사항 R 번호로 메모를 단다.",
                                user=f"원본 쪽(역할 태그 포함):\n{text_for_llm[:6000]}\n이번 요구사항:\n" +
                                     "\n".join(f"- {x.get('code')} {x.get('text')}" for x in rq),
                                schema={"type": "object", "properties": {
                                    "pattern": {"type": "object", "properties": {"name": {"type": "string"}, "en": {"type": "string"}}},
                                    "broken": {"type": "array", "items": {"type": "string"}},
                                    "evidence": {"type": "array", "items": {"type": "object", "properties": {
                                        "page": {"type": "integer"}, "text": {"type": "string"}, "warn": {"type": "boolean"}}}},
                                    "memos": {"type": "array", "items": {"type": "object", "properties": {
                                        "text": {"type": "string"}, "tag": {"type": "string"}, "action": {"type": "string"}}}}}},
                                confidential=True) or {}
    ev = {int(e.get("page") or 0): e for e in flow_res.get("evidence") or [] if isinstance(e, dict)}
    for pg in out_pages:
        e = ev.get(pg["no"])
        if e and not pg["excluded"]:
            pg["evidence"], pg["evidence_warn"] = e.get("text") or "", bool(e.get("warn"))
        elif pg["flow_role"] == "표지":
            pg["evidence"], pg["evidence_warn"] = "—", False
        elif pg["excluded"]:
            pg["evidence"], pg["evidence_warn"] = "자동 제외", False
        else:
            src_lines = clean_lines(pg["no"])
            has_src = any("출처" in x["text"] for x in src_lines)
            has_num = any(NUM_UNIT_RE.search(x["text"]) for x in src_lines)
            pg["evidence"] = "[출처 없음] · 수치 출처 미기재" if has_num and not has_src else ("출처 표기 있음" if has_src else "")
            pg["evidence_warn"] = bool(has_num and not has_src)
    broken = [b for b in flow_res.get("broken") or [] if isinstance(b, str)]
    for pg in out_pages:
        if pg.get("evidence_warn") and len(broken) < 3:
            broken.append(f"p.{pg['no']} 출처 없음")
    if WHY not in names:
        broken.append("Why Samsung 단계 없음")
    broken = list(dict.fromkeys(broken))
    pattern = flow_res.get("pattern") if isinstance(flow_res.get("pattern"), dict) and (flow_res.get("pattern") or {}).get("name") else \
        {"name": "문제 해결형", "en": "Problem → Solution"}
    content_pages = [pg for pg in out_pages if not pg["excluded"] and pg["flow_role"] != "표지"]
    flow = {"steps": [{k: s.get(k) for k in ("name", "count", "dashed", "excluded", "note", "range", "from", "to")} for s in steps],
            "pattern": pattern,
            "claims": {"linked": sum(1 for pg in content_pages if pg.get("evidence") and not pg.get("evidence_warn")), "total": len(content_pages)},
            "broken": broken, "memos": [{"no": i + 1, "text": m.get("text"), "tag": m.get("tag") or "", "action": m.get("action") or ""}
                                        for i, m in enumerate([m for m in flow_res.get("memos") or [] if isinstance(m, dict) and m.get("text")][:5])]}
    # 3 핵심 메시지(LLM, 기밀)
    msg = await G.llm_json("pr.reuse_messages", system="원본 제안서 Key Message · 톤(기밀).",
                           user="원본 쪽:\n" + text_for_llm[:4000], schema={"type": "object", "properties": {
                               "km": {"type": "array", "items": {"type": "string"}}, "tone": {"type": "string"}}}, confidential=True) or {}
    km = [x for x in msg.get("km") or [] if isinstance(x, str)][:4]
    # 4 고객 · 맥락
    cur_cust = (p.get("customer") or {}).get("name") or ""
    src_cust = next((m.get("customer") for m in metas if m.get("customer")), None)
    src_scale = src_ind = None
    if src_cust:
        src_ind = next((defs.INDUSTRIES.get(m.get("industry_code") or "", {}).get("name") for m in metas if m.get("industry_code")), None)
    else:
        head = [pg for pg in out_pages if not pg["excluded"]][:6]
        cm = await G.llm_json("pr.reuse_context_match", system="원본 제안서의 고객 · 업종 · 규모를 원문에서만(기밀). 없으면 빈 문자열.",
                              user="원본 앞쪽:\n" + "\n".join(f"p.{pg['no']} {pg['title']} — " + " / ".join(x["text"] for x in clean_lines(pg["no"])[:4])
                                                             for pg in head),
                              schema={"type": "object", "properties": {"customer": {"type": "string"}, "industry": {"type": "string"},
                                                                       "scale": {"type": "string"}}}, confidential=True) or {}
        src_cust = (cm.get("customer") or "").strip() or None
        src_scale = (cm.get("scale") or "").strip() or None
        src_ind = (cm.get("industry") or "").strip() or None
        if not src_cust and cur_cust:
            head_text = " ".join(pg["title"] + " " + " ".join(x["text"] for x in clean_lines(pg["no"])) for pg in head[:2])
            if norm_name(cur_cust) and norm_name(cur_cust) in norm_name(head_text):
                src_cust = cur_cust
    same = bool(src_cust) and bool(cur_cust) and norm_name(src_cust) == norm_name(cur_cust)
    if len({norm_name(m.get("customer") or "") for m in metas if m.get("customer")}) > 1:
        same = False
    coverage = []
    # 경쟁 비교 쪽은 요구사항을 비교 기준으로 늘어놓을 뿐이라 「다룸」의 근거로는 마지막에만 본다
    compare_roles = {"CP", "CM", "ST"}
    primary = [pg for pg in content_pages if pg["flow_role"] != WHY and (pg.get("winmate") or {}).get("role") not in compare_roles]
    secondary = [pg for pg in content_pages if pg not in primary]
    for it in rq:
        best, bp = 0.0, None
        for group in (primary, secondary):
            for pg in group:
                sc = contains_score(it.get("text") or "", pg["title"] + " " + " ".join(x["text"] for x in clean_lines(pg["no"])))
                if sc > best:
                    best, bp = sc, pg
            if best >= 0.4:
                break
        state = "has" if best >= 0.75 else ("part" if best >= 0.4 else "none")
        where = ((f"원본 p.{bp['no']} {short_title(bp['title'])}" + (" · 그대로 이어감" if state == "has" else " · 기준 다름"))
                 if bp and state != "none" else "원본에 없음 → 신규 시트 1장")
        coverage.append({"rq_id": it.get("id") or it.get("code"), "code": it.get("code") or it.get("id"), "name": it.get("text") or "", "state": state,
                         "state_label": {"has": "있음", "part": "일부", "none": "없음 → 신규"}[state], "where": where,
                         "page": bp["no"] if bp and state != "none" else None})
    overlap = sum(1 for c in coverage if c["state"] in ("has", "part"))
    context = {"same_customer": same, "source_customer": src_cust, "current_customer": cur_cust,
               "overlap": [{"rq_id": c["rq_id"], "code": c["code"], "source_ref": c["where"]} for c in coverage if c["state"] != "none"],
               "overlap_count": overlap, "current_total": len(coverage), "coverage": coverage, "source_scale": src_scale,
               "source_industry": src_ind, "rq_linked": bool(rq)}
    # 5 제품 · 솔루션
    models: dict[str, list[int]] = {}
    sol_versions: dict[str, set[str]] = {}
    for pg in content_pages:
        txt = pg["title"] + " " + " ".join(x["text"] for x in clean_lines(pg["no"]))
        for m in MODEL_RE.finditer(txt):
            models.setdefault(m.group(1), []).append(pg["no"])
        for m in SOL_VER_RE.finditer(txt):
            sol_versions.setdefault(m.group(1), set()).add(m.group(2))
    lifecycle: dict[str, dict[str, Any]] = {}
    if models:
        lc = await clients.call("spec", "POST", "/v1/lifecycle:check", json={"model_codes": sorted(models)[:30], "locale": "ko"}, quiet=True)
        for it in (lc or {}).get("items") or []:
            lifecycle[it.get("model_code")] = it
    products = []
    for code, pgs in sorted(models.items()):
        lc = lifecycle.get(code) or {}
        succ = [s.get("model_code") for s in lc.get("successors") or [] if s.get("model_code")]
        products.append({"model": code, "pages": sorted(set(pgs)), "count": len(pgs), "status": lc.get("status") or "unknown",
                         "successor": succ[0] if lc.get("status") == "discontinued" and succ else None})
    sol_diff = [{"name": k, "from": sorted(v, key=int)[-1], "to": CURRENT_SOL.get(k)} for k, v in sol_versions.items()
                if CURRENT_SOL.get(k) and sorted(v, key=int)[-1] != CURRENT_SOL.get(k)]
    # 6 수치
    numbers = []
    year_now = config.today_kst().year
    for pg in content_pages:
        for ln in clean_lines(pg["no"]):
            y = YEAR_RE.search(ln["text"])
            year = int(y.group(1)) if y else None
            for m in NUM_UNIT_RE.finditer(ln["text"]):
                if year and m.group(1) == str(year):
                    continue
                numbers.append({"page": pg["no"], "line_id": ln["id"], "value": m.group(0), "year": year, "sourced": "출처" in ln["text"],
                                "stale": bool(year and year <= year_now - 2 and pg["flow_role"] in STAT_ROLES), "role": pg["flow_role"]})
    # 7 이미지
    images = []
    for pg in out_pages:
        if pg["excluded"]:
            continue
        for im in pg.get("images") or []:
            k = im.get("kind")
            cls = ("official" if (k == "kb_image" or im.get("rights") == "official") else
                   "generated" if k == "image_job" else
                   "customer" if (im.get("rights") in ("customer", "customer_case", "site_photo") or (k == "file" and pg["flow_role"] in ("고객 과제", "공간 시나리오", "도입 사례")))
                   else "unknown")
            reusable = cls in ("official", "generated") or (cls == "customer" and same)
            images.append({"page": pg["no"], "id": im.get("id"), "kind": k, "class": cls, "reusable": reusable})
    # 8 디자인 매핑
    keys_std = core.type_sections(p.get("type") or "standard")
    mapping = []
    for pg in out_pages:
        if pg["flow_role"] == "표지":
            continue
        w = pg.get("winmate") or None
        sec, role = target_for(pg["flow_role"], pg["title"], keys_std, w)
        role = (w or {}).get("role") or role
        ok = bool(sec) and not pg["excluded"]
        mapping.append({"page": pg["no"], "section_key": sec, "role": role, "ok": ok, "title": pg["title"],
                        "template": (w or {}).get("template") or ((defs.ROLES.get(role or "") or {}).get("default") if role else None)})
    # 기준 표(§10.9 · PRU2)
    n_pages = len(out_pages)
    nc_pages = [pg for pg in out_pages if pg["excluded"]]
    stale_n = sum(1 for x in numbers if x["stale"])
    effect = [x for x in numbers if x["role"] == "가치 제안"]
    unsourced = sum(1 for x in effect if not x["sourced"])
    disc = [x for x in products if x["successor"]]
    cust_label = src_cust or "원본 고객"
    sales_n = sum(1 for x in noncopy_lines if any(k in x["text"] for k in ("매출", "영업이익", "원가")))
    est_n = sum(1 for pg in nc_pages if any(k in pg["title"] for k in ("견적", "단가", "가격")))
    sch_n = len(nc_pages) - est_n
    conf_flow = int(round(100 * sum(pg["confidence"] for pg in out_pages) / max(1, n_pages)))
    has_cover = bool(out_pages) and out_pages[0]["flow_role"] == "표지"
    n_secs = len([s for s in sections if not s["excluded"] and s["name"] != "표지"])
    model_counts = " · ".join(f"{x['model']}" + (f" ×{x['count']}" if x["count"] > 1 else "") for x in products[:4])
    crit_rows = {
        1: (f"{n_pages}장 → 섹션 {n_secs}개 복원 · 표지 {'있음' if has_cover else '없음'} · 목차 · 부록 없음" +
            (f" · 견적 {len(nc_pages)}장 분리" if nc_pages else ""), 96 if all(pg.get("winmate") for pg in out_pages) else 90),
        2: (flow_summary(steps, pattern, broken), min(95, conf_flow) if any(not pg.get("winmate") for pg in out_pages) else 92),
        3: (f"KM {len(km)}개" + (f" · '{' · '.join(km[:3])}'" if km else "") + (f" · 톤 {msg.get('tone')}" if msg.get("tone") else ""), 88 if km else 60),
        4: (f"{cust_label}" + (f" · {src_ind}" if src_ind else "") + (f" {src_scale}" if src_scale else "") +
            f" · 이번 {len(coverage)}건과 겹침 {overlap} · 다름 {len(coverage) - overlap}", 90 if src_cust else 65),
        5: ((model_counts or "모델 표기 없음") +
            (f" · 단종 {len(disc)}종(" + ", ".join(f"{x['model']} → {x['successor']}" for x in disc) + ")" if disc else "") +
            (f" · 버전 {len(sol_diff)}종(" + ", ".join(f"{x['name']} {x['to']}" for x in sol_diff) + ")" if sol_diff else ""), 93),
        6: (f"수치 {len(numbers)}건" + (f" · {year_now - 2}년 이전 기준 {stale_n}건(오래됨)" if stale_n else "") +
            (f" · 효과 수치 {len(effect)}건 중 출처 없음 {unsourced}건" if effect else ""), 85),
        7: (f"{len(images)}개 · 삼성 공식 {sum(1 for i in images if i['class'] in ('official', 'generated'))} 재사용 가능 · {cust_label} 사진 "
            f"{sum(1 for i in images if i['class'] == 'customer')} " + ("재사용 가능" if same else "사용 불가") +
            f" · 출처 미상 {sum(1 for i in images if i['class'] == 'unknown')}", 79 if any(i["class"] == "unknown" for i in images) or not images else 88),
        8: (f"{sum(1 for m in mapping if m['ok'])}장 Winmate 시트 유형 매핑 · 매핑 실패 {sum(1 for m in mapping if not m['ok'])}장",
            74 if any(not m["ok"] for m in mapping) else 90),
        9: (" · ".join(x for x in [f"견적 {est_n}장" if est_n else "", f"일정 {sch_n}장" if sch_n else "",
                                   f"{cust_label} 매출 {sales_n}건" if sales_n else "",
                                   f"민감 줄 {len(noncopy_lines) - sales_n}건" if len(noncopy_lines) > sales_n else ""] if x) +
            (" → 자동 제외" if (nc_pages or noncopy_lines) else "비복제 항목 없음"), 99),
    }
    prev_crit = {c["no"]: c for c in prev.get("criteria") or []}
    locked_crit = {int(x) for x in locks.get("criteria") or []}
    criteria = []
    for no, key, name, must, mode in defs.CRITERIA:
        summary, conf = crit_rows[no]
        pc = prev_crit.get(no) or {}
        if no in locked_crit and pc.get("state") == "edited":
            criteria.append(pc)
            continue
        state = "ok" if mode == "auto" and conf >= 80 else "need"
        if pc.get("state") == "ok" and pc.get("summary") == summary:
            state = "ok"          # 다시 분석해도 결과가 같으면 사용자가 한 확인은 그대로
        criteria.append({"no": no, "key": key, "name": name, "must": must, "summary": summary, "confidence": conf, "state": state})
    a = {"pages": out_pages, "source_sections": sections, "criteria": criteria, "flow": flow, "context": context,
         "km": km, "tone": msg.get("tone"), "noncopy_lines": noncopy_lines, "products": products, "sol_diff": sol_diff,
         "numbers": numbers, "images": images, "mapping": mapping, "year_now": year_now}
    apply_user_edits(a, prev_crit, locked_crit)
    a["recommendation"] = recommend(a["context"], len(metas))
    return a


def apply_user_edits(a: dict[str, Any], prev_crit: dict[int, dict[str, Any]], locked: set[int]) -> None:
    """고정된(수정함) 기준의 사용자 수정값을 분석 결과에 다시 얹는다."""
    for no in locked:
        ed = (prev_crit.get(no) or {}).get("user_edits") or {}
        if no == 4 and "same_customer" in ed:
            a["context"]["same_customer"] = bool(ed["same_customer"])
        if no == 5 and ed.get("reject_successors"):
            rej = set(ed["reject_successors"])
            for x in a.get("products") or []:
                if x["model"] in rej:
                    x["successor"] = None


def recommend(context: dict[str, Any], n_sources: int) -> dict[str, str]:
    """§10.9 — 같은 고객 + 겹침 3건 이상 → 개선 · 수정, 다른 고객(또는 섞임) → 흐름 차용."""
    k, n = context.get("overlap_count") or 0, context.get("current_total") or 0
    if context.get("same_customer"):
        if k >= 3:
            return {"mode": "improve", "reason": f"같은 고객이고 요구사항이 {k}건 겹쳐요", "badge": f"추천 · 같은 고객 · 겹침 {k} / {n}"}
        return {"mode": "improve", "reason": f"같은 고객이에요(요구사항 겹침 {k}건 · 확인 권장)", "badge": f"추천 · 같은 고객 · 겹침 {k} / {n} · 확인 권장"}
    return {"mode": "borrow", "reason": "다른 고객 제안서라 설득 구조만 가져와요", "badge": "추천 · 다른 고객"}


# ── 계획 ───────────────────────────────────────────────────
def plan_improve(p: dict[str, Any], a: dict[str, Any], pages: list[dict[str, Any]], *, locks: dict[str, Any],
                 prev_plan: dict[str, Any] | None, type_: str) -> dict[str, Any]:
    """원본 쪽마다 판정 + 근거(규칙 우선, §7.11). 고친 판정(locks.rows)은 그대로."""
    prev_rows = {r["row_id"]: r for r in (prev_plan or {}).get("rows") or []}
    locked = set(locks.get("rows") or [])
    keys = core.type_sections(type_)
    store = ((p.get("ctx") or {}).get("store_count") or "").replace(",", "")
    disc = {x["model"]: x["successor"] for x in a.get("products") or [] if x.get("successor")}
    stale = {}
    for x in a.get("numbers") or []:
        if x["stale"]:
            stale.setdefault(x["page"], x["year"])
    unsourced_pages = {x["page"] for x in a.get("numbers") or [] if not x["sourced"] and x["role"] == "가치 제안"}
    nc_ids = {x["line_id"] for x in a.get("noncopy_lines") or []}
    cov = a["context"].get("coverage") or []
    by_no = {pg["no"]: pg for pg in pages}
    rows = []
    auto_src = 0
    for pg in a["pages"]:
        if pg["flow_role"] == "표지":
            auto_src += 1
            continue
        w = pg.get("winmate") or {}
        if w.get("section_key") == "spec" or (not w and pg["flow_role"] == "제품 스펙"):
            auto_src += 1          # 제품 스펙은 판정 없이 Spec 시트 작업으로 다시 만든다(§10.10)
            continue
        src = by_no.get(pg["no"]) or {"lines": []}
        txt = pg["title"] + " " + " ".join(x["text"] for x in src["lines"] if x["id"] not in nc_ids)
        rid = f"p{pg['no']}"
        rq_ids = [c["code"] for c in cov if c.get("page") == pg["no"]]
        noncopy = bool(pg["excluded"])
        sec, role = target_for(pg["flow_role"], pg["title"], keys, w or None)
        change: dict[str, Any] | None = None
        st = STORE_RE.search(txt)
        if noncopy:
            verdict, note = "drop", "비복제 · 가격 · 견적 · 일정은 가져오지 않아요"
        elif w.get("section_key") == "birdseye" or "조감도" in pg["title"]:
            verdict, note = "drop", "매장 구조 달라 새로 생성 · 조감도 작업으로"
        elif not sec:
            verdict, note = "drop", "이번 유형에 맞는 자리가 없어요"
        elif any(m in txt for m in disc):
            m = next(m for m in disc if m in txt)
            verdict, note, change = "update", f"{m} 단종 → {disc[m]} 후속 치환", {"kind": "model", "from": m, "to": disc[m]}
        elif any(x["name"] in txt for x in a.get("sol_diff") or []):
            x = next(x for x in a["sol_diff"] if x["name"] in txt)
            verdict, note, change = "update", f"{x['name']} {x['from']} → {x['to']} · 기능 표 갱신", {"kind": "solution", "name": x["name"], "from": x["from"], "to": x["to"]}
        elif pg["no"] in stale:
            y = stale[pg["no"]]
            verdict, note, change = "update", f"{y} 수치 → 최신 [00] 조사로 갱신", {"kind": "stale", "year": y}
        elif store and st and st.group(1) != store:
            verdict, note, change = "update", f"매장 {st.group(1)} → {int(store):,} 갱신", {"kind": "store", "from": st.group(1), "to": store}
        elif pg["no"] in unsourced_pages:
            verdict, note, change = "rewrite", "효과 수치 기준 바뀜 · 출처 없는 수치는 쓰지 않아요", {"kind": "unsourced"}
        elif any(c.get("page") == pg["no"] and c["state"] == "part" for c in cov):
            verdict, note = "rewrite", "이번 요구사항 기준으로 다시 씀"
        else:
            verdict, note = "keep", "변화 없음 · 그대로 이어감"
        pr = prev_rows.get(rid)
        if rid in locked and pr and not noncopy:
            verdict = pr["verdict"]
        rows.append({"row_id": rid, "group": pg.get("section_name") or pg["flow_role"], "page": pg["no"], "file_page": pg.get("file_page"),
                     "thumb_kind": (w.get("template") if w else None), "sheet_name": (pg["title"] or pg["flow_role"])[:40], "verdict": verdict,
                     "note": note, "rq_ids": rq_ids, "locked": rid in locked or noncopy, "noncopy": noncopy, "flow_role": pg["flow_role"],
                     "role": role, "section_key": sec, "change": change, "ident": w.get("ident"), "repeat_ref": w.get("repeat_ref")})
    for c in cov:
        if c["state"] != "none":
            continue
        rid = f"n{c['code']}"
        pr = prev_rows.get(rid)
        rows.append({"row_id": rid, "group": "요구사항 갭에서 추가", "page": None, "sheet_name": c["name"][:40],
                     "verdict": pr["verdict"] if (rid in locked and pr) else "new", "note": "원본에 없음 → 신규 시트", "rq_ids": [c["code"]],
                     "locked": rid in locked, "noncopy": False, "flow_role": None, "role": "OP", "section_key": None, "change": None,
                     "rq": {"code": c["code"], "name": c["name"]}})
    return {"rows": rows, "requirement_coverage": cov, "auto_source_pages": auto_src, **improve_totals(p, a, rows, type_, auto_src)}


def improve_totals(p: dict[str, Any], a: dict[str, Any], rows: list[dict[str, Any]], type_: str, auto_src: int) -> dict[str, Any]:
    """판정 집계 · 「원본 m장 → 새 제안서 n장」(§10.10)."""
    from . import plan as PL
    ctx = p.get("ctx") or {}
    keys = core.type_sections(type_)
    totals = {k: sum(1 for r in rows if r["verdict"] == k) for k in ("keep", "update", "rewrite", "new", "drop")}
    used = {}
    for r in rows:
        if r["verdict"] in ("keep", "update", "rewrite") and r.get("section_key"):
            used[r["section_key"]] = used.get(r["section_key"], 0) + 1
    auto_sheets = 0
    for k in keys:
        n = PL.sheet_count_for(k, PL.default_composition(k, ctx), ctx)
        auto_sheets += max(0, n - used.get(k, 0))
    n_sheets = totals["keep"] + totals["update"] + totals["rewrite"] + totals["new"] + auto_sheets
    secs_with = len([k for k in keys if used.get(k) or PL.sheet_count_for(k, PL.default_composition(k, ctx), ctx)])
    new_total = core.slides_total(p, n_sheets, secs_with)
    only = [{"label": f"{k} · Key Message", "tag": "제외 제안"} for k in (a.get("km") or [])[:1]] + [
        {"label": f"{pg['title'][:24]} · p.{pg['no']}", "tag": "비복제"} for pg in a["pages"] if pg["excluded"]]
    drop_names = list(dict.fromkeys(short_title(r["sheet_name"], 14) for r in rows if r["verdict"] == "drop"))[:3]
    return {"totals": totals, "source_total": len(a["pages"]), "new_total": new_total, "auto_sheets": auto_sheets, "only_in_source": only,
            "summary_note": (f"제외 {totals['drop']}장에는 {' · '.join(drop_names)}이 들어 있어요. 유저가 고친 판정은 다시 분석해도 바뀌지 않아요."
                             if totals["drop"] else "유저가 고친 판정은 다시 분석해도 바뀌지 않아요.")}


def borrow_targets(name: str, keys: list[str]) -> list[str]:
    if name == "솔루션 구성":
        return [k for k in ("solution", "spaceProducts") if k in keys]
    if name == "시장 변화":
        return [k for k in ("bigMi", "mi") if k in keys][:1]
    if name == "공간 시나리오":
        return [k for k in ("spaceScenario", "solution") if k in keys][:1]
    sec = defs.FLOW_TO_SECTION.get(name)
    return [sec] if sec in keys else []


def plan_borrow(p: dict[str, Any], a: dict[str, Any], *, type_: str) -> dict[str, Any]:
    """흐름 단계 → 이번 유형의 섹션 · 시트 구성(§7.11 H6). 원본 내용은 쓰지 않는다."""
    from . import plan as PL
    keys = core.type_sections(type_)
    ctx = p.get("ctx") or {}
    cov = a["context"].get("coverage") or []
    sec_n = {k: PL.sheet_count_for(k, PL.default_composition(k, ctx), ctx) for k in keys}
    consumed = {k: 0 for k in keys}
    rows: list[dict[str, Any]] = []

    def rq_in(s: dict[str, Any]) -> list[str]:
        return [c["code"] for c in cov if c.get("page") and s.get("from") and s["from"] <= c["page"] <= (s.get("to") or s["from"])]

    for s in a["flow"]["steps"]:
        name = s["name"]
        if s.get("excluded") or name == "견적 · 일정":
            rows.append({"src_step": name, "src_count": s["count"], "src_range": s.get("range") or "", "kind": "drop", "new_label": "제외",
                         "note": "비복제 · 가격 · 견적 · 일정은 가져오지 않아요", "rq_ids": [], "new_count": 0, "targets": []})
            continue
        if s.get("dashed"):
            if "why" in keys and consumed["why"] < sec_n["why"]:
                n = sec_n["why"] - consumed["why"]
                consumed["why"] = sec_n["why"]
                rq_ids = [c["code"] for c in cov if any(k in c["name"] for k in ("연동", "POS", "지원", "신뢰"))][:2]
                rows.append({"src_step": name, "src_count": 0, "src_range": "원본에 없음", "kind": "new", "new_label": f"Why Samsung {n}장",
                             "note": "경쟁 비교 · 요구사항 신뢰 근거", "rq_ids": rq_ids, "new_count": n, "targets": ["why"]})
            continue
        if name == "문제 제기":
            rows.append({"src_step": name, "src_count": s["count"], "src_range": s.get("range") or "", "kind": "flow", "new_label": "표지 · 제안 배경",
                         "note": "신규 작성 · 이번 프로젝트 배경으로", "rq_ids": [], "new_count": 0, "targets": []})
            continue
        if name == "고객 과제" and "vp" in keys and consumed["vp"] == 0 and sec_n["vp"] > 1:
            consumed["vp"] = 1
            rows.append({"src_step": name, "src_count": s["count"], "src_range": s.get("range") or "", "kind": "flow",
                         "new_label": "Value Props 안 '과제' 1장", "note": "요구사항이 근거 · 원본 인터뷰는 쓰지 않아요", "rq_ids": rq_in(s),
                         "new_count": 1, "targets": ["vp"]})
            continue
        targets = [t for t in borrow_targets(name, keys) if sec_n[t] - consumed[t] > 0]
        if not targets:
            rows.append({"src_step": name, "src_count": s["count"], "src_range": s.get("range") or "", "kind": "flow", "new_label": "앞 섹션에 합침",
                         "note": "같은 섹션으로 이어져요", "rq_ids": rq_in(s), "new_count": 0, "targets": []})
            continue
        n = sum(sec_n[t] - consumed[t] for t in targets)
        for t in targets:
            consumed[t] = sec_n[t]
        note = {"시장 변화": "수치는 MI 작업으로 새로 조사", "가치 제안": "흐름 유지 · Key Message는 이번 고객 톤으로",
                "도입 사례": "이번 업종 사례로 교체 · 원본 고객 사례 사용 안 함", "제품 스펙": "Spec 시트 작업으로 생성"}.get(name, "흐름 유지 · 내용은 이번 고객 자료로")
        rows.append({"src_step": name, "src_count": s["count"], "src_range": s.get("range") or "", "kind": "flow",
                     "new_label": " + ".join(defs.SECTIONS[t]["name"] for t in targets) + f" {n}장", "note": note,
                     "rq_ids": rq_in(s), "new_count": n, "targets": targets})
    # 원본 흐름에 없던 이번 유형 섹션은 흐름 뒤에 그대로(제외 아님)
    for k in keys:
        if sec_n[k] - consumed[k] > 0:
            n = sec_n[k] - consumed[k]
            consumed[k] = sec_n[k]
            rows.append({"src_step": "이번 유형 기본", "src_count": 0, "src_range": "원본에 없음", "kind": "new",
                         "new_label": f"{defs.SECTIONS[k]['name']} {n}장", "note": "이번 유형의 기본 섹션", "rq_ids": [], "new_count": n,
                         "targets": [k]})
    gaps = [c for c in cov if c["state"] == "none"]
    for c in gaps[:3]:
        rows.append({"src_step": "요구사항 갭", "src_count": 0, "src_range": "원본에 없음", "kind": "new", "new_label": f"{c['name'][:16]} 1장",
                     "note": f"{c['code']} · 이번 요구사항에 맞춰 신규", "rq_ids": [c["code"]], "new_count": 1, "targets": [],
                     "rq": {"code": c["code"], "name": c["name"]}})
    counts = {"flow": sum(r["new_count"] for r in rows if r["kind"] == "flow"), "new": sum(r["new_count"] for r in rows if r["kind"] == "new"),
              "drop": sum(r["src_count"] for r in rows if r["kind"] == "drop")}
    imgs = a.get("images") or []
    steps_real = [s for s in a["flow"]["steps"] if not s.get("dashed") and not s.get("excluded")]
    take = [{"label": "단계 순서", "sub": f"{len(steps_real)}단계 → {len(keys)}섹션"},
            {"label": "시트 역할", "sub": f"{len(a['pages'])}장 역할 태그"},
            {"label": "주장 → 근거 구조", "sub": f"{(a['flow'].get('claims') or {}).get('linked', 0)}개 연결"},
            {"label": "템플릿 유형", "sub": f"매핑 성공 {sum(1 for m in a.get('mapping') or [] if m['ok'])}장"},
            {"label": "톤", "sub": a.get("tone") or "원본 톤"}]
    cust = a["context"].get("source_customer") or "원본 고객"
    not_take = [{"label": "고객 정보", "sub": cust + (f" · {a['context'].get('source_scale')}" if a["context"].get("source_scale") else "")},
                {"label": "매장 사진", "sub": f"{sum(1 for i in imgs if i['class'] == 'customer')}장 · 사용 불가"},
                {"label": "수치", "sub": f"시장 · 효과 수치 {len(a.get('numbers') or [])}건"},
                {"label": "견적 · 일정", "sub": f"비복제 {sum(1 for pg in a['pages'] if pg['excluded'])}장"},
                {"label": f"{cust} 사례", "sub": f"도입 사례 {sum(1 for pg in a['pages'] if pg['flow_role'] == '도입 사례')}장"},
                {"label": "출처 미상 이미지", "sub": f"{sum(1 for i in imgs if i['class'] == 'unknown')}개 · 분류 보류"}]
    return {"rows": rows, "take": take, "not_take": not_take, "sections": len(keys), "sheets": sum(r["new_count"] for r in rows), "counts": counts}
