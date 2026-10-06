"""문장 · 제목 · 파일명 · 상태 · 목록 표시(06-spec §3.6 · §4.2.4 · §4.3.5 · §4.7.1 · §4.10 · §4.16.6, §7.9-5 · 6)."""
from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from .. import config
from . import items as itemcat
from .fmt import category_short, fmt_num, josa, safe_filename

LANG_LABEL = {"ko": "한국어", "en": "English", "ko_en": "한/영"}
FORMAT_LABEL = {"xlsx": "XLSX", "pdf": "PDF", "pptx": "PPT"}
FORMAT_NAME = {"xlsx": "Excel", "pdf": "PDF", "pptx": "PPT 슬라이드"}
FROM_LABEL = {"vp": "Value Proposition", "mi": "Market Intelligence", "birdseye": "공간 조감도", "product_detail": "제품 상세",
              "proposal": "제안서", "home": "홈"}
GRADE_SHORT = {(3840, 2160): "4K", (1920, 1080): "FHD", (2560, 1440): "QHD", (7680, 4320): "8K"}
KIND_NAME = {"compare": "비교표", "single": "단일 시트", "per_product": "제품별 시트", "req": "요구사항 대응표"}


def visible_products(sheet: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(sheet.get("products") or [], key=lambda p: p.get("ord", 0))


def kind_name(sheet: dict[str, Any]) -> str:
    if sheet.get("layout") == "per_product" and len(sheet.get("products") or []) > 1:
        return KIND_NAME["per_product"]
    k = sheet.get("kind") or "single"
    if k == "req":
        return KIND_NAME["compare"] if len(sheet.get("products") or []) > 1 else KIND_NAME["single"]
    return KIND_NAME.get(k, "비교표")


def names(products: list[dict[str, Any]], sep: str) -> str:
    return sep.join(p.get("display_name") or "" for p in products)


# ── 제안 제목(§4.3.5) ───────────────────────────────────

def suggested_title(sheet: dict[str, Any]) -> str:
    ps = visible_products(sheet)
    start = sheet.get("start")
    if start == "requirements":
        comp = sheet.get("compliance") or {}
        cp = " ".join(x for x in (comp.get("customer"), comp.get("place")) if x)
        if cp:
            return f"{cp} 요구 스펙 대응표"
        if ps:
            return f"{ps[0]['display_name']} 요구 스펙 대응표"
        return "요구 스펙 대응표"
    if start == "find" and sheet.get("step", 1) == 1:
        fd = sheet.get("finder") or {}
        cp = " ".join(x for x in (fd.get("customer"), fd.get("place")) if x)
        if cp:
            return f"{cp} 후보 비교"
    if start == "clone" and sheet.get("clone_of_title"):
        return f"{sheet['clone_of_title']} (복제)"
    if not ps:
        if start == "find":
            fd = sheet.get("finder") or {}
            cp = " ".join(x for x in (fd.get("customer"), fd.get("place")) if x)
            if cp:
                return f"{cp} 후보 비교"
        return "새 Spec 시트"
    if len(ps) == 1:
        return f"{ps[0]['display_name']} 스펙"
    sizes = {p.get("size_inch") for p in ps}
    series = [p.get("series_code") for p in ps]
    if len(sizes) == 1 and None not in sizes and all(series) and len(set(series)) == 2 and len(ps) == 2:
        return f"{series[0]} vs {series[1]} {ps[0]['size_inch']}\" 비교"
    if all(series) and len(set(series)) == 1 and len(sizes) == len(ps) and None not in sizes:
        return f"{series[0]} {'/'.join(str(s) for s in sorted(sizes))} 비교"  # type: ignore[type-var]
    return f"{ps[0]['display_name']} 외 {len(ps) - 1}개 비교"


def display_title(sheet: dict[str, Any]) -> str:
    return sheet.get("title") if sheet.get("title_confirmed") and sheet.get("title") else suggested_title(sheet)


# ── 시트 제목(§4.10 · §4.16.5) ──────────────────────────

def table_title(sheet: dict[str, Any], lang: str = "ko", *, products: list[dict[str, Any]] | None = None) -> str:
    ps = products if products is not None else [p for p in visible_products(sheet) if p.get("role") != "existing"] or visible_products(sheet)
    allp = visible_products(sheet)
    if not ps:
        return "Spec 시트" if lang != "en" else "Specifications"
    fams = {p.get("family_label_en") for p in ps}
    fam = next(iter(fams)) if len(fams) == 1 else None
    if len(ps) == 1:
        p = ps[0]
        base = f"{p.get('family_label_en') or ''} {p['display_name']}".strip()
        if lang == "en":
            return f"Samsung {base} Specifications"
        return f"{base} 스펙"
    sizes = {p.get("size_inch") for p in ps}
    vs = " vs ".join(p["display_name"] for p in ps)
    if lang == "en":
        if fam and len(sizes) == 1 and None not in sizes:
            return f"Samsung {fam} {ps[0]['size_inch']}\" Comparison"
        if fam:
            return f"Samsung {fam} Comparison"
        return "Samsung Product Comparison"
    if fam and len(sizes) == 1 and None not in sizes:
        head = f"{fam} {ps[0]['size_inch']}\" 비교"
    elif fam:
        head = f"{fam} 비교"
    else:
        head = "제품 비교"
    if any(p.get("role") == "existing" for p in allp):
        return f"{head} — 기존 장비 포함"
    return f"{head} — {vs}"


def source_line(sheet: dict[str, Any], cells: dict[str, Any]) -> str:
    cat = sheet.get("catalog") or {}
    out = f"출처: 사내 제품 카탈로그 {cat.get('version') or ''}".rstrip()
    if any((c or {}).get("state") == "sync_pending" for c in cells.values()):
        out += " · [값]은 카탈로그 동기화 후 자동 채움"
    ds = len([d for d in sheet.get("datasheets") or [] if d.get("status") == "done"])
    user = len([c for c in cells.values() if (c or {}).get("state") == "edited"])
    if ds:
        out += f" · 데이터시트 {ds}건"
    if user:
        out += f" · 직접 입력 {user}칸"
    return out


# ── 에이전트 문장 ─────────────────────────────────────────

def _short_value(item_key: str, v: dict[str, Any] | None) -> tuple[str, str, str] | None:
    """차이 요약 조각: (짧은 이름, 값 글, 단위)."""
    if not v:
        return None
    if item_key == "brightness_contrast":
        if v.get("nit") is None:
            return None
        return ("밝기", fmt_num(v["nit"]), "nit")
    if item_key == "operation_hours":
        return ("운영 시간", str(v.get("text") or ""), "") if v.get("text") else None
    if item_key == "power":
        return ("소비전력", fmt_num(v["typ"]), "W") if v.get("typ") is not None else None
    if item_key == "warranty":
        return ("보증", fmt_num(v["years"]), "년") if v.get("years") is not None else None
    if item_key == "player_os":
        return ("OS", str(v.get("os")), "") if v.get("os") else None
    if item_key == "magicinfo":
        return ("MagicINFO", "지원" if v.get("supported") else "미지원", "") if v.get("supported") is not None else None
    if item_key == "size_resolution":
        return ("크기", str(v.get("inch")), '"') if v.get("inch") else None
    return None


def diff_sentence(sheet: dict[str, Any], values: dict[str, list[dict[str, Any] | None]]) -> str:
    """SP2 에이전트(§4.7.1). values: item_key → 제품 순서대로 대표 행 값."""
    ps = visible_products(sheet)
    tail = " 시트에 넣을 스펙 항목과 출력 형식을 골라주세요."
    pre = any(i.get("prechecked_by") == "requirement" for i in sheet.get("items") or [])
    tail2 = " 고객 요구사항과 관련된 항목을 미리 체크해 두었습니다." if pre else ""
    if len(ps) <= 1:
        name = ps[0]["display_name"] if ps else "제품"
        return f"{name}의 스펙 항목과 출력 형식을 골라주세요.{tail2}"
    common = []
    sizes = [(v or {}).get("inch") for v in values.get("size_resolution") or []]
    if sizes and None not in sizes and len(set(sizes)) == 1:
        common.append(f'{sizes[0]}"')
    res = [((v or {}).get("w"), (v or {}).get("h")) for v in values.get("size_resolution") or []]
    if res and (None, None) not in res and len(set(res)) == 1 and res[0] in GRADE_SHORT:
        common.append(GRADE_SHORT[res[0]])
    cats = {p.get("category_id") for p in ps}
    common.append(category_short(next(iter(cats)) if len(cats) == 1 else None))
    diffs: list[tuple[str, str]] = []
    for key in itemcat.default_keys():
        vals = values.get(key) or []
        if len(vals) != len(ps):
            continue
        sv = [_short_value(key, v) for v in vals]
        if any(x is None for x in sv):
            continue
        texts = [x[1] for x in sv]  # type: ignore[index]
        if len(set(texts)) <= 1:
            continue
        short, unit = sv[0][0], sv[0][2]  # type: ignore[index]
        sep = " vs " if len(ps) == 2 else " / "
        diffs.append((short, f"{short}({sep.join(texts)}{unit})"))
        if len(diffs) == 2:
            break
    who = "두 모델은" if len(ps) == 2 else f"{len(ps)}개 모델은"
    if not diffs:
        lead = "두 모델의 주요 스펙이 같습니다." if len(ps) == 2 else f"{len(ps)}개 모델의 주요 스펙이 같습니다."
        return f"{lead}{tail}{tail2}"
    if len(diffs) == 1:
        body = f"{diffs[0][1]}{josa(diffs[0][0], '이', '가')} 다릅니다."
    else:
        body = f"{diffs[0][1]}{josa(diffs[0][0], '과', '와')} {diffs[1][1]}{josa(diffs[1][0], '이', '가')} 다릅니다."
    return f"{who} 같은 {' '.join(common)}지만 {body}{tail}{tail2}"


def sp2_user_line(sheet: dict[str, Any]) -> str:
    ps = visible_products(sheet)
    if not ps:
        return ""
    fams = {p.get("family_label_en") for p in ps}
    if len(fams) == 1 and next(iter(fams)):
        return f"제품 {len(ps)}개 · {next(iter(fams))} {' / '.join(p['display_name'] for p in ps)}"
    return f"제품 {len(ps)}개 · " + " / ".join((p.get("bubble_label") or p["display_name"]) for p in ps)


def checked_count(sheet: dict[str, Any]) -> int:
    return len([i for i in sheet.get("items") or [] if i.get("checked")])


def sp3g_user_line(sheet: dict[str, Any]) -> str:
    ps = visible_products(sheet)
    return f"{names(ps, ' · ')} · 항목 {checked_count(sheet)}개 · {kind_name(sheet)} · {LANG_LABEL.get((sheet.get('format') or {}).get('language', 'ko'), '한국어')}"


def sp3g_agent(sheet: dict[str, Any]) -> str:
    ps = visible_products(sheet)
    who = "두 모델" if len(ps) == 2 else (f"{len(ps)}개 모델" if len(ps) > 2 else (ps[0]["display_name"] if ps else "제품"))
    return (f"사내 카탈로그에서 {who}의 스펙을 채우고 있어요. 값이 비었거나 출처끼리 다른 곳은 추측하지 않고 여기서 여쭤볼게요. "
            "답하지 않으면 [확정 필요]로 두고 시트를 완성합니다.")


def sp3g_subtitle(sheet: dict[str, Any]) -> str:
    ps = visible_products(sheet)
    return f"{names(ps, ' vs ')} · 항목 {checked_count(sheet)}개 · {kind_name(sheet)}"


def sp3_agent(sheet: dict[str, Any]) -> str:
    ver = (sheet.get("catalog") or {}).get("version") or ""
    ps = visible_products(sheet)
    if len(ps) <= 1:
        return f"스펙 시트가 완성되었습니다. 셀을 클릭하면 값을 직접 고칠 수 있고, 출처는 사내 카탈로그 {ver} 기준입니다."
    mid = " 파란 셀은 우위 항목입니다." if (sheet.get("options") or {}).get("highlight_wins", True) else ""
    return f"비교표가 완성되었습니다.{mid} 셀을 클릭하면 값을 직접 고칠 수 있고, 출처는 사내 카탈로그 {ver} 기준입니다."


def from_note(sheet: dict[str, Any]) -> str | None:
    o = sheet.get("origin") or {}
    src = o.get("from")
    n = len([p for p in sheet.get("products") or [] if p.get("source") == "link"])
    if not src or src in ("home", "clone") or not n:
        return None
    return f"{FROM_LABEL.get(src, src)}에서 넘겨받은 제품 {n}개를 넣어 두었어요."


# ── 파일명(§4.16.6) ─────────────────────────────────────

_GENERIC = ("프랜차이즈", "주식회사", "(주)", "㈜", "그룹")


def customer_short(name: str | None) -> str:
    if not name:
        return ""
    s = name
    for g in _GENERIC:
        s = s.replace(g, "")
    return re.sub(r"\s+", "", s)


def default_filename(sheet: dict[str, Any], lang: str | None = None) -> str:
    lang = lang or (sheet.get("format") or {}).get("language", "ko")
    ps = [p for p in visible_products(sheet)]
    cust = customer_short(sheet.get("customer_name"))
    kind = sheet.get("kind")
    if lang == "en":
        if kind == "req":
            base = f"Samsung_{ps[0]['display_name'] if ps else 'Spec'}_Compliance_EN"
        elif len(ps) == 1:
            base = f"Samsung_{ps[0]['display_name']}_Specifications_EN"
        else:
            fams = {p.get("family_label_en") for p in ps}
            fam = (next(iter(fams)) or "Product").split()[-1] if len(fams) == 1 and next(iter(fams)) else "Product"
            sizes = {p.get("size_inch") for p in ps}
            size = f"_{ps[0]['size_inch']}" if len(sizes) == 1 and None not in sizes else ""
            base = f"Samsung_{fam}{size}_Comparison_EN"
        return safe_filename(base)
    if kind == "req":
        mid = ps[0]["display_name"] if ps else "대응표"
        base = "_".join(x for x in (cust, mid, "요구사항대응표") if x)
    elif len(ps) <= 1:
        base = "_".join(x for x in (cust, ps[0]["display_name"] if ps else "", "스펙") if x)
    else:
        base = "_".join(x for x in (cust, "-".join(p["display_name"] for p in ps), "스펙비교") if x)
    if lang == "ko_en":
        base += "_KO-EN"
    return safe_filename(base)


# ── 상태 · 이어하기(§3.6) ───────────────────────────────

def open_checks(sheet: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in sheet.get("checks") or [] if c.get("status") == "open"]


def open_warnings(sheet: dict[str, Any]) -> list[dict[str, Any]]:
    return [w for w in sheet.get("warnings") or [] if w.get("status") in ("open", "decided")]


def status_of(sheet: dict[str, Any], sid: str) -> tuple[str, str, str]:
    """(ui_status, status_text, resume_route) — 위에서부터 처음 맞는 줄."""
    job = sheet.get("active_job") or {}
    if job and job.get("status") in ("queued", "running") and job.get("kind") in ("spec_generate", "spec_recheck"):
        pct = int(job.get("progress") or 0)
        return "run", f"생성 중 {pct}%", f"/spec/{sid}/generating?job={job['id']}"
    oc = open_checks(sheet)
    if oc:
        last = sheet.get("last_job_id") or ""
        return "check", f"값 확인 필요 {len(oc)}", f"/spec/{sid}/generating" + (f"?job={last}" if last else "")
    comp = sheet.get("compliance") or {}
    if sheet.get("start") == "requirements" and sheet.get("step", 1) == 1:
        unknown = [r for r in comp.get("rows") or [] if r.get("verdict") == "unknown"]
        if unknown:
            return "check", f"확인 필요 {len(unknown)}", f"/spec/{sid}/requirements"
    ow = open_warnings(sheet)
    if ow:
        if all(w.get("kind") == "catalog_changed" for w in ow):
            return "warn", f"카탈로그 변경 {len(ow)}", f"/spec/{sid}/warnings"
        return "warn", f"경고 {len(ow)}", f"/spec/{sid}/warnings"
    step = sheet.get("step", 1)
    if step in (1, 2) or not sheet.get("generated_at"):
        st = step if step in (1, 2) else 2
        if st == 1:
            start = sheet.get("start")
            route = {"find": "find", "requirements": "requirements"}.get(start or "", "products")
            return "draft", f"작성 중 {st}/3", f"/spec/{sid}/{route}"
        return "draft", f"작성 중 {st}/3", f"/spec/{sid}/items"
    return "done", "완료", f"/spec/{sid}"


# ── SP0 표시(§4.2.4) ────────────────────────────────────

def type_icon(sheet: dict[str, Any]) -> str:
    start = sheet.get("start")
    if sheet.get("step", 1) == 1 and start == "find":
        return "find"
    if start == "requirements":
        return "req"
    return "compare" if len(sheet.get("products") or []) >= 2 else "single"


def sub_line(sheet: dict[str, Any]) -> str:
    step = sheet.get("step", 1)
    start = sheet.get("start")
    if step == 1 and start == "find":
        n = len([c for c in (sheet.get("finder") or {}).get("candidates") or [] if not c.get("out")])
        n = n or len((sheet.get("finder") or {}).get("candidates") or [])
        return f"조건 검색 · 후보 {n}개"
    if start == "requirements" and step == 1:
        return f"요구사항 대응표 · 요구 {len((sheet.get('compliance') or {}).get('rows') or [])}개"
    kind = "비교표" if len(sheet.get("products") or []) >= 2 else "단일 시트"
    if sheet.get("layout") == "per_product" and len(sheet.get("products") or []) >= 2:
        kind = "제품별 시트"
    if start == "requirements":
        return f"요구사항 대응표 · 요구 {len((sheet.get('compliance') or {}).get('rows') or [])}개"
    if step == 2:
        return f"{kind} · 항목 · 형식 고르는 중"
    if step >= 3:
        return f"{kind} · {checked_count(sheet)}개 항목"
    return f"{kind} · 제품 입력 중"


def output_label(sheet: dict[str, Any]) -> str:
    if not sheet.get("format_confirmed"):
        return "정하지 않음"
    f = sheet.get("format") or {}
    fm = " + ".join(FORMAT_LABEL.get(x, x.upper()) for x in f.get("formats") or ["xlsx"])
    return f"{fm} · {LANG_LABEL.get(f.get('language', 'ko'), '한국어')}"


def when_label(iso: str | None) -> str:
    dt = config.parse_iso(iso)
    if dt is None:
        return ""
    now = config.now().astimezone(config.KST)
    d = dt.astimezone(config.KST)
    if d.date() == now.date():
        return f"오늘 {d:%H:%M}"
    if d.date() == (now - timedelta(days=1)).date():
        return "어제"
    if d.year == now.year:
        return f"{d.month}월 {d.day}일"
    return f"{d:%Y-%m-%d}"


def saved_label(iso: str | None) -> str:
    """SP4 도크 `방금 저장됨` · `5분 전 저장됨`."""
    dt = config.parse_iso(iso)
    if dt is None:
        return "저장 전"
    secs = (config.now() - dt).total_seconds()
    if secs < 60:
        return "방금 저장됨"
    if secs < 3600:
        return f"{int(secs // 60)}분 전 저장됨"
    if secs < 86400:
        return f"{int(secs // 3600)}시간 전 저장됨"
    return f"{when_label(iso)} 저장됨"


def kst_date(iso: str | None) -> str:
    dt = config.parse_iso(iso)
    return dt.astimezone(config.KST).strftime("%Y-%m-%d") if dt else ""


def banner_text(detected_at: str | None, n: int) -> str:
    dt = config.parse_iso(detected_at) or config.now()
    d = dt.astimezone(config.KST)
    return f"사내 카탈로그가 {d.month}월 {d.day}일 갱신되었습니다. 저장된 시트 {n}개에서 값이 달라져 다시 확인이 필요해요."

