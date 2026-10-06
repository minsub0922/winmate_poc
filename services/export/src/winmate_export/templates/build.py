"""템플릿 카탈로그 만들기 — `python -m winmate_export.templates.build`

입력
- docs/templates/source/<캔버스>/canvas.json — 'Winmate PPT' 디자인 캔버스 5개의 보드 제목 · 노트(코드 · 이름 · 언제 쓰나)
- winmate-kb/seed/sheet_roles.yaml — 시트 역할 이름 · 섹션 · 제안서 유형 · 알려진 data_shape
- registry_data.py — 코드 → 아키타입 · 매개변수, 업종 · 솔루션 메타
출력
- services/export/src/winmate_export/templates/catalog.json(체크인) — 서비스가 읽는 카탈로그
- docs/templates/CATALOG.md — 사람이 읽는 목록

결정적이다(타임스탬프 없음): 같은 입력이면 같은 파일. 테스트가 체크인한 catalog.json 과 다시 만든 결과를 비교한다.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from .archetypes import build_layout
from .registry_data import (
    CANVASES,
    EXTRA_ROLES,
    FALLBACK_ROLES,
    GENERIC,
    IND_ARCH,
    INDUSTRIES,
    INDUSTRY_ORDER,
    INDUSTRY_ROLES,
    PI_VARIANTS,
    SECTIONS,
    SOLUTION_INDUSTRIES,
    SOLUTION_ORDER,
    SOLUTIONS,
    SPEC_NAMES,
    SS_FORMS,
    VARIANTS,
)

CATALOG_VERSION = 1
HERE = Path(__file__).resolve().parent
CATALOG_PATH = HERE / "catalog.json"


def repo_root() -> Path:
    for p in (HERE, *HERE.parents):
        if (p / "config" / "services.yaml").is_file():
            return p
    raise RuntimeError("repo root not found")


# ── 입력 읽기 ─────────────────────────────────────────────

def load_canvases(root: Path) -> dict[str, dict[str, Any]]:
    out = {}
    for name in CANVASES:
        d = root / "docs" / "templates" / "source" / name
        canvas = json.loads((d / "canvas.json").read_text(encoding="utf-8"))
        src = json.loads((d / "SOURCE.json").read_text(encoding="utf-8")) if (d / "SOURCE.json").is_file() else {}
        out[name] = {"canvas": canvas, "source": src}
    return out


def load_roles(root: Path) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, Any]]]:
    roles: dict[str, dict[str, str]] = {}
    shapes: dict[str, dict[str, Any]] = {}
    p = root / "winmate-kb" / "seed" / "sheet_roles.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8")) if p.is_file() else {}
    for r in (data or {}).get("sheet_roles", []):
        roles[r["code"]] = {"name": r["name_ko"], "says": r.get("says_ko", ""), "section": r["section"]}
    for t in (data or {}).get("templates", []):
        code = str(t.get("code", ""))
        if code.startswith("<<") or not t.get("data_shape"):
            continue
        shapes[code] = t["data_shape"]
    for code, (name, says, section) in FALLBACK_ROLES.items():
        roles.setdefault(code, {"name": name, "says": says, "section": section})
    for code, (name, says, section) in EXTRA_ROLES.items():
        roles[code] = {"name": name, "says": says, "section": section}
    return roles, shapes


def board_title(canvases: dict[str, Any], canvas: str, board: str) -> str | None:
    b = canvases[canvas]["canvas"]["boards"].get(board)
    return b.get("title") if b else None


def split_title(title: str | None) -> tuple[str, str, str]:
    """'MS-A 핵심 수치 4 — 지표는 …' → (코드 토큰, 이름, 설명)."""
    if not title:
        return "", "", ""
    head, _, tail = title.partition(" — ")
    token, _, name = head.partition(" ")
    return token.strip(), name.strip(), tail.strip()


def ss_forms(canvases: dict[str, Any]) -> dict[str, list[str]]:
    """공간 시나리오 업종 줄 노트(si00…) → {업종: [④ 형태, ⑤ 형태]}."""
    out: dict[str, list[str]] = {}
    notes = canvases["ss"]["canvas"].get("notes", {})
    for key, n in notes.items():
        if not key.startswith("si"):
            continue
        text = n.get("text", "")
        ind = text.split(" ", 1)[0]
        forms = re.findall(r"[④⑤][^④⑤]*?\(([^)]+)\)", text)
        if ind in INDUSTRIES and forms:
            out[ind] = forms[:2]
    return out


# ── 표시 코드 · 정규화 ─────────────────────────────────────

def display_code(code: str) -> str:
    m = re.fullmatch(r"(VP-[BF])(\d)", code)
    if m:
        return f"{m.group(1)}·{m.group(2)}"
    if code in ("VP-UC", "VP-US"):
        return f"VP-U·{code[-1]}"
    if code.startswith("VP-UC-"):
        return "VP-U·C-" + code.split("-")[-1]
    m = re.fullmatch(r"VC-(\d)(\w+)", code)
    if m:
        return f"VC-{m.group(1)}·{m.group(2)}"
    return code


def normalize_code(code: str) -> str:
    return re.sub(r"[\s·•]", "", code or "").upper()


# ── data_shape · 썸네일 n ──────────────────────────────────

SHAPE_ALIASES = {"people": "stakeholders", "products": "product_count", "spaces": "space_count", "pins": "points",
                 "pillars": "pillars", "kpis": "numbers"}


def derive_shape(slots: list[dict[str, Any]]) -> dict[str, Any]:
    shape: dict[str, Any] = {}
    grades: dict[str, int] = {}
    numbers = 0
    for s in slots:
        key, t, n = s["key"], s["type"], s.get("count")
        if t == "card" and n:
            shape[SHAPE_ALIASES.get(key, key)] = n
            for fd in s.get("fields", []):
                if fd["type"] == "image":
                    g = fd.get("image_grade") or "A"
                    grades[g] = grades.get(g, 0) + n
                if fd["type"] == "kpi":
                    numbers += n
        elif t == "card":
            for fd in s.get("fields", []):
                if fd["type"] == "image":
                    g = fd.get("image_grade") or "A"
                    grades[g] = grades.get(g, 0) + 1
        elif t == "kpi":
            numbers += n or 1
        elif t == "image":
            g = s.get("image_grade") or "A"
            grades[g] = grades.get(g, 0) + (n or 1)
        elif t in ("table", "chart"):
            shape[t] = True
    if numbers:
        shape["numbers_max"] = numbers
    if grades:
        shape["image_slots"] = [{"grade": g, "count": c} for g, c in sorted(grades.items())]
    shape["image_based"] = bool(grades)
    return shape


def main_count(slots: list[dict[str, Any]]) -> int | None:
    skip = {"headers", "row_labels", "labels", "axes", "contacts", "legend", "quadrants_labels"}
    for s in slots:
        if s["type"] == "card" and s.get("count") and s["key"] not in skip:
            return int(s["count"])
    return None


def merge_shape(derived: dict[str, Any], known: dict[str, Any] | None, extra: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(derived)
    for src in (known or {}, extra or {}):
        for k, v in src.items():
            if isinstance(v, str) and v.startswith("<<"):
                continue
            if k == "image_slots" and isinstance(v, list):
                if any(isinstance(x.get("count"), str) for x in v):
                    continue
            out[k] = v
    return out


# ── 템플릿 하나 만들기 ──────────────────────────────────────

def make_entry(*, code: str, role: str, arch: str, params: dict[str, Any], roles: dict[str, dict[str, str]],
               name: str, when: str, thumb: str, kind: str, source: dict[str, Any] | None,
               status: str = "ready", industry: str | None = None, industry_scheme: str | None = None,
               solution: str | None = None, variant: str | None = None, base: str | None = None,
               product_count: int | None = None, sample_title: str | None = None,
               known_shape: dict[str, Any] | None = None, extra_shape: dict[str, Any] | None = None) -> dict[str, Any]:
    r = roles[role]
    section = r["section"]
    params = {k: v for k, v in params.items() if k != "section"}
    layout = build_layout(arch, section, params)
    entry: dict[str, Any] = {
        "code": code,
        "display_code": display_code(code),
        "name": name,
        "sheet_role": role,
        "role_name": r["name"],
        "says": r.get("says", ""),
        "section": section,
        "section_name": SECTIONS[section]["name"],
        "kind": kind,
        "family": None,
        "industry": industry,
        "industry_name": None,
        "industry_scheme": industry_scheme,
        "industry_aliases": [],
        "solution": solution,
        "solution_name": SOLUTIONS[solution]["name"] if solution else None,
        "variant": variant,
        "product_count": product_count,
        "proposal_types": list(SECTIONS[section]["proposal_types"]),
        "description": when,
        "when": when,
        "sample_title": sample_title,
        "status": status,
        "base": base,
        "archetype": arch,
        "params": {k: (list(v) if isinstance(v, tuple) else v) for k, v in params.items()},
        "thumb_kind": thumb,
        "thumb_n": main_count(layout.slots),
        "data_shape": merge_shape(derive_shape(layout.slots), known_shape, extra_shape),
        "slots": layout.slots,
        "boxes": layout.boxes,
        "source": source,
    }
    if industry:
        if industry_scheme == "solution":
            entry["industry_name"] = SOLUTION_INDUSTRIES[industry]["name"]
            entry["industry_aliases"] = SOLUTION_INDUSTRIES[industry]["aliases"]
        else:
            entry["industry_name"] = INDUSTRIES[industry]["name"]
            entry["industry_aliases"] = [industry]
    m = re.match(r"^(MI|VP|SS)-[A-Z]{2}-[A-E]$", code)
    entry["family"] = m.group(1) if m else (solution or code.split("-")[0])
    return entry


def source_ref(canvases: dict[str, Any], canvas: str, board: str | None, boards: list[str] | None = None) -> dict[str, Any] | None:
    if not board:
        return {"canvas": canvas, "board": None, "artifact": CANVASES[canvas]["artifact"],
                "path": None, "title": None, "note": "캔버스 보드 없음(제작 중) — 같은 역할 바탕 레이아웃 사용"}
    title = board_title(canvases, canvas, board)
    d = {"canvas": canvas, "board": board, "title": title, "artifact": CANVASES[canvas]["artifact"],
         "version": canvases[canvas]["source"].get("version"), "path": f"docs/templates/source/{canvas}/{board}"}
    if boards:
        d["boards"] = boards
    return d


def build_catalog(root: Path | None = None) -> dict[str, Any]:
    root = root or repo_root()
    canvases = load_canvases(root)
    roles, known_shapes = load_roles(root)
    forms = ss_forms(canvases)
    entries: list[dict[str, Any]] = []

    # 1) 범용 · 공통
    for code, g in GENERIC.items():
        canvas, board = g["board"]
        token, bname, bwhen = split_title(board_title(canvases, canvas, board))
        sname, swhen = SPEC_NAMES.get(code, ("", ""))
        name = sname or bname or code
        when = swhen or bwhen
        kind = "common" if g["role"] in ("COVER", "TOC", "DIVIDER", "CLOSING") else "generic"
        if code == "SC-A":
            name, when = "사양 비교표 2~5개", "제품 간 사양 차이를 볼 때(제품 수만큼 열)"
        entries.append(make_entry(
            code=code, role=g["role"], arch=g["arch"], params=g.get("p", {}), roles=roles, name=name, when=when,
            thumb=g.get("thumb", "table"), kind=kind, source=source_ref(canvases, canvas, board, g.get("boards")),
            status=g.get("status", "ready"), known_shape=known_shapes.get(code), extra_shape=g.get("shape")))

    # 2) 업종 변형(같은 바탕 레이아웃)
    by_code = {e["code"]: e for e in entries}
    for code, v in VARIANTS.items():
        base = GENERIC[v["base"]]
        canvas, board = v["board"]
        _, bname, bwhen = split_title(board_title(canvases, canvas, board))
        ind = v["industry"]
        name = f"{by_code[v['base']]['name']} · {INDUSTRIES[ind]['name']}"
        entries.append(make_entry(
            code=code, role=base["role"], arch=base["arch"], params=base.get("p", {}), roles=roles, name=name,
            when=f"{INDUSTRIES[ind]['name']} 현장 질문 예시 — {by_code[v['base']]['when']}", thumb=base["thumb"],
            kind="industry", source=source_ref(canvases, canvas, board), industry=ind, industry_scheme="winmate16",
            base=v["base"]))

    # 3) 업종판 MI · VP · SS
    for family, canvas in (("MI", "mi"), ("VP", "vp"), ("SS", "ss")):
        variants = INDUSTRY_ROLES[family]
        for ind in INDUSTRY_ORDER:
            for var, (vname, thumb, vdesc, vroles) in variants.items():
                code = f"{family}-{ind}-{var}"
                board = f"L_{family}_{ind}_{var}.dc.html"
                title = board_title(canvases, canvas, board)
                _, bname, sample = split_title(title)
                arch, params = IND_ARCH.get((family, var), (None, {}))
                desc = vdesc
                if family == "SS" and var in ("D", "E"):
                    f_list = forms.get(ind, [])
                    form_name = f_list["DE".index(var)] if len(f_list) > "DE".index(var) else "문제 → 해결"
                    arch, form_desc, thumb = SS_FORMS.get(form_name, SS_FORMS["문제 → 해결"])
                    params = {}
                    # 보드 이름: '… · 공간 시나리오 · 매장 외부 · 대기' → 공간 이름
                    space = bname.split("공간 시나리오 · ", 1)[1] if "공간 시나리오 · " in (bname or "") else ""
                    vname = f"공간 시나리오 · {space}" if space else vname
                    desc = form_desc
                status = "ready" if title else "in_production"
                role = vroles[0]
                entries.append(make_entry(
                    code=code, role=role, arch=arch, params=params, roles=roles,
                    name=f"{INDUSTRIES[ind]['name']} · {vname}", when=f"{INDUSTRIES[ind]['name']} 고객용 — {desc}",
                    thumb=thumb, kind="industry", source=source_ref(canvases, canvas, board if title else None),
                    status=status, industry=ind, industry_scheme="winmate16", variant=var,
                    sample_title=sample or None, extra_shape={"roles": vroles}))

    # 4) 공간 제품 소개 P{n}-{v}
    for n in range(1, 6):
        for var, (vname, vwhen, thumb) in PI_VARIANTS.items():
            code = f"P{n}-{var}"
            board = f"L_P{n}{var}.dc.html"
            _, bname, _ = split_title(board_title(canvases, "pi", board))
            name = "메시지 강조" if (n == 1 and var == "D") else vname
            when = "제품 하나의 메시지를 강하게 말할 때" if (n == 1 and var == "D") else vwhen
            entries.append(make_entry(
                code=code, role="PI", arch="products", params={"n": n, "variant": var}, roles=roles,
                name=f"제품 {n}개 · {name}", when=when, thumb="pD1" if (n == 1 and var == "D") else thumb,
                kind="product", source=source_ref(canvases, "pi", board), variant=var, product_count=n,
                extra_shape={"product_count": n}))

    # 5) 솔루션 전용 · 업종 버전
    boards = canvases["common"]["canvas"]["boards"]
    for sol in SOLUTION_ORDER:
        meta = SOLUTIONS[sol]
        for part, arch, role, thumb, pname in (("I", "sol_intro", "SXI", "solIntro", "전용 소개"),
                                                ("D", "sol_diagram", "SXD", "solDiagram", "전용 구성도"),
                                                ("S", "sol_scene", "SXS", "solScene", "전용 공간 시나리오")):
            code = f"{sol}-{part}"
            board = f"L_{sol}_{part}.dc.html"
            entries.append(make_entry(
                code=code, role=role, arch=arch, params={}, roles=roles, name=f"{meta['name']} {pname}",
                when=meta[part], thumb=thumb, kind="dedicated",
                source=source_ref(canvases, "common", board if board in boards else None), solution=sol))
        for board in sorted(b for b in boards if b.startswith(f"L_{sol}_S_")):
            ind = board[len(f"L_{sol}_S_"):-len(".dc.html")]
            code = f"{sol}-S-{ind}"
            _, bname, sample = split_title(boards[board].get("title"))
            iname = SOLUTION_INDUSTRIES.get(ind, {"name": ind})["name"]
            entries.append(make_entry(
                code=code, role="SXS", arch="sol_scene", params={}, roles=roles,
                name=f"{meta['name']} 공간 시나리오 · {iname} 업종 버전",
                when=f"고객 업종이 {iname}일 때 — 그 업종의 공간 사진과 순서로", thumb="solSceneInd",
                kind="industry_solution", source=source_ref(canvases, "common", board), industry=ind,
                industry_scheme="solution", solution=sol, base=f"{sol}-S", sample_title=sample or None))

    entries.sort(key=sort_key)
    stats = catalog_stats(entries)
    aliases = {
        # 스펙이 항목 수 없이 부르는 계열 코드 → 칸 데이터의 항목 수로 고른다(없으면 default)
        "VP-B": {"by": "pillars", "options": {"2": "VP-B2", "3": "VP-B3", "4": "VP-B4"}, "default": "VP-B3"},
        "VP-F": {"by": "pillars", "options": {"2": "VP-F2", "3": "VP-F3", "4": "VP-F4"}, "default": "VP-F3"},
        "SC-A2": {"default": "SC-A"}, "SC-A3": {"default": "SC-A"}, "SC-A4": {"default": "SC-A"}, "SC-A5": {"default": "SC-A"},
        "COVER": {"default": "C01"}, "TOC": {"default": "C04"}, "DIVIDER": {"default": "C05"}, "CLOSING": {"default": "C07"},
    }
    reference = reference_boards(canvases, {e["source"]["board"] for e in entries if e.get("source") and e["source"].get("board")}
                                 | {b for e in entries for b in (e.get("source") or {}).get("boards", []) or []})
    return {
        "version": CATALOG_VERSION,
        "slide": {"width_px": 1280, "height_px": 720, "width_in": 13.333, "height_in": 7.5, "ratio": "16:9"},
        "design": {"brand_hex": "#1428a0", "ink": "#121417", "font": "Noto Sans KR", "number_font": "Manrope"},
        "sources": {k: {"title": v["title"], "artifact": v["artifact"], "version": canvases[k]["source"].get("version"),
                        "path": f"docs/templates/source/{k}/"} for k, v in CANVASES.items()},
        "stats": stats,
        "sections": SECTIONS,
        "roles": roles,
        "industries": INDUSTRIES,
        "solution_industries": SOLUTION_INDUSTRIES,
        "solutions": {k: {"name": v["name"], "desc": v["desc"]} for k, v in SOLUTIONS.items()},
        "reference_boards": reference,
        "aliases": aliases,
        "templates": entries,
    }


SECTION_ORDER = ["common", "mi", "vp", "birdseye", "space_products", "solution", "space_scenario", "cases", "why", "spec", "appendix"]
KIND_ORDER = ["common", "generic", "product", "industry", "dedicated", "industry_solution"]


def sort_key(e: dict[str, Any]) -> tuple[Any, ...]:
    return (SECTION_ORDER.index(e["section"]), e["sheet_role"], KIND_ORDER.index(e["kind"]), e["code"])


def catalog_stats(entries: list[dict[str, Any]]) -> dict[str, Any]:
    by_role: dict[str, int] = {}
    by_section: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for e in entries:
        by_role[e["sheet_role"]] = by_role.get(e["sheet_role"], 0) + 1
        by_section[e["section"]] = by_section.get(e["section"], 0) + 1
        by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
        by_status[e["status"]] = by_status.get(e["status"], 0) + 1
    ready = [e for e in entries if e["status"] == "ready"]
    return {
        "total": len(entries),
        "ready": len(ready),
        "industry": sum(1 for e in ready if e["kind"] == "industry"),
        "dedicated": sum(1 for e in entries if e["kind"] in ("dedicated", "industry_solution")),
        "by_role": dict(sorted(by_role.items())),
        "by_section": by_section,
        "by_kind": by_kind,
        "by_status": by_status,
    }


def reference_boards(canvases: dict[str, Any], used: set[str]) -> list[dict[str, Any]]:
    """템플릿이 아닌 보드(지도 · 시스템 · 분석 · 컴포넌트) — 원본 추적용."""
    out = []
    for name, c in canvases.items():
        for board, b in c["canvas"]["boards"].items():
            if board in used:
                continue
            out.append({"canvas": name, "board": board, "title": b.get("title"), "page": b.get("page")})
    return sorted(out, key=lambda r: (r["canvas"], r["board"]))


# ── 문서(CATALOG.md) ───────────────────────────────────────

def slot_summary(slots: list[dict[str, Any]]) -> str:
    parts = []
    for s in slots:
        if s["key"] in ("eyebrow", "sources", "footer", "logo"):
            continue
        t = s["type"]
        if t == "card" and s.get("fields"):
            t = "card{" + ",".join(f["key"] for f in s["fields"]) + "}"
        if t == "image" and s.get("image_grade"):
            t = f"image:{s['image_grade']}"
        n = f"×{s['count']}" if s.get("count") else ""
        req = "*" if s.get("required") else ""
        parts.append(f"`{s['key']}{req}` {t}{n}")
    return " · ".join(parts)


def geometry_summary(boxes: list[dict[str, Any]]) -> str:
    content = [b for b in boxes if b.get("slot") and b["slot"] not in ("eyebrow", "title", "subtitle", "sources", "footer", "logo")]
    if not content:
        return "—"
    x0 = min(b["x"] for b in content)
    y0 = min(b["y"] for b in content)
    x1 = max(b["x"] + b["w"] for b in content)
    y1 = max(b["y"] + b["h"] for b in content)
    return f"본문 {round(x0 * 1280)},{round(y0 * 720)}–{round(x1 * 1280)},{round(y1 * 720)} · 상자 {len(boxes)}"


def render_markdown(cat: dict[str, Any]) -> str:
    st = cat["stats"]
    lines = [
        "# Winmate 시트 템플릿 카탈로그",
        "",
        "> 자동 생성 — 직접 고치지 말 것. `uv run python -m winmate_export.templates.build` 로 다시 만든다.",
        "> 원본: `docs/templates/source/<캔버스>/`(Design 캔버스 project 파일 사본) · 기계용: "
        "`services/export/src/winmate_export/templates/catalog.json` · API: `GET /api/export/v1/templates`.",
        "",
        "## 요약",
        "",
        f"- 템플릿 **{st['total']}**종 (출시 {st['ready']} · 제작 중 {st['by_status'].get('in_production', 0)} · 내부용 {st['by_status'].get('internal', 0)})",
        f"- 업종판(출시) {st['industry']} · 솔루션 전용 {st['dedicated']}(전용 33 + 업종 버전 21)",
        "- 슬라이드 16:9(13.333 × 7.5 in) · 좌표는 1280 × 720 캔버스 기준 상대값(0..1) · 글꼴 `Noto Sans KR` · 포인트 색 `#1428a0`",
        "",
        "| 섹션 | 수 |",
        "|---|---|",
    ]
    for sec in SECTION_ORDER:
        if sec in st["by_section"]:
            lines.append(f"| {cat['sections'][sec]['name']} (`{sec}`) | {st['by_section'][sec]} |")
    lines += ["", "| 역할 | 이름 | 수 |", "|---|---|---|"]
    for role, n in st["by_role"].items():
        lines.append(f"| `{role}` | {cat['roles'][role]['name']} | {n} |")
    lines += [
        "",
        "## 원본 캔버스",
        "",
        "| 폴더 | 캔버스 | 아티팩트 | 판 |",
        "|---|---|---|---|",
    ]
    for k, s in cat["sources"].items():
        lines.append(f"| `{s['path']}` | {s['title']} | {s['artifact']} | `{s['version']}` |")
    lines += [
        "",
        "## 칸(slot) 형식",
        "",
        "| type | 값 |",
        "|---|---|",
        "| `text` · `caption` | 문자열 또는 `{ko, en}` |",
        "| `bullets` | 문자열 목록 |",
        "| `number` | 숫자 또는 문자열(`[00]`) |",
        "| `kpi` | `{value, unit?, label?, sub?, delta?, bar?(0–100)}` 또는 문자열 |",
        "| `image` · `logo` | files `file_id` 또는 `{file_id, caption?, credit?, ai_generated?, fit?}` |",
        "| `table` | `{columns:[…], rows:[[…]], highlight_col?, highlight_rows?, group_rows?}` — 칸은 문자열 또는 `{text, bold?, fill?}` |",
        "| `chart` | `{type: bar\\|line\\|hbar\\|stacked\\|stacked100\\|pie\\|doughnut\\|radar\\|scatter\\|bubble, categories:[…], series:[{name, values}], unit?, highlight_last?}` |",
        "| `source` | 문자열 또는 `[{label, url?}]` |",
        "| `card` | 필드 묶음 객체(`fields` 참고). `count` 가 있으면 목록 |",
        "",
        "`*` = 필수. 업종 변형은 바탕 템플릿과 같은 칸 · 배치를 쓴다(`base`). 이미지 등급 A 공간+제품 · B 솔루션 화면 · C 제품 컷 · D 도식 · E 아이콘/로고.",
        "",
    ]
    cur = None
    for e in cat["templates"]:
        if e["section"] != cur:
            cur = e["section"]
            lines += [f"## {cat['sections'][cur]['name']} (`{cur}`)", "",
                      "| 코드 | 이름 | 역할 | 업종 · 솔루션 | 상태 | 아키타입 | 칸 | 배치 | 원본 보드 |",
                      "|---|---|---|---|---|---|---|---|---|"]
        tag = e.get("industry") and f"{e['industry']} {e.get('industry_name') or ''}".strip() or (e.get("solution") or "")
        board = (e.get("source") or {}).get("board") or "—"
        lines.append(
            f"| `{e['code']}` | {e['name']} | `{e['sheet_role']}` | {tag} | {e['status']} | `{e['archetype']}` | "
            f"{slot_summary(e['slots'])} | {geometry_summary(e['boxes'])} | `{e['source']['canvas']}/{board}` |")
    lines += ["", "## 참고 보드(템플릿 아님)", "", "| 캔버스 | 보드 | 제목 |", "|---|---|---|"]
    for r in cat["reference_boards"]:
        lines.append(f"| {r['canvas']} | `{r['board']}` | {r.get('title') or ''} |")
    lines.append("")
    return "\n".join(lines)


def dumps(cat: dict[str, Any]) -> str:
    """머리는 들여쓰기, 템플릿은 한 줄에 하나(차이 보기 쉽고 작다)."""
    head = {k: v for k, v in cat.items() if k != "templates"}
    text = json.dumps(head, ensure_ascii=False, indent=1)
    lines = [json.dumps(t, ensure_ascii=False, separators=(",", ":")) for t in cat["templates"]]
    body = ',\n  '.join(lines)
    return text[:-2] + ',\n "templates": [\n  ' + body + '\n ]\n}\n'


def main(argv: list[str]) -> int:
    root = repo_root()
    cat = build_catalog(root)
    text = dumps(cat)
    if "--check" in argv:
        cur = CATALOG_PATH.read_text(encoding="utf-8") if CATALOG_PATH.is_file() else ""
        if cur != text:
            print("✗ catalog.json 이 원본과 다르다 → python -m winmate_export.templates.build")
            return 1
        print("✓ catalog.json 최신")
        return 0
    CATALOG_PATH.write_text(text, encoding="utf-8")
    md = root / "docs" / "templates" / "CATALOG.md"
    md.write_text(render_markdown(cat), encoding="utf-8")
    st = cat["stats"]
    print(f"✓ {CATALOG_PATH.relative_to(root)} — {st['total']} templates ({st['by_status']})")
    print(f"✓ {md.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
