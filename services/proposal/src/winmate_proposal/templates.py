"""템플릿 추천(결정적, §7.5 · §10.5 · §10.6) · 템플릿 고르기 후보(§4.16).

우선순위: 고정 > 업종 레이아웃(적용한 계열) > 솔루션 전용 > 데이터 모양 > 메시지 기본값.
카탈로그 정본은 export(`GET /v1/templates`). 카탈로그에 없거나 `in_production` 인 코드는 고르지 않는다(⚠Q4).
"""
from __future__ import annotations

import math
from typing import Any

from . import clients, defs

# ── 카탈로그 ───────────────────────────────────────────────
_LOCAL_NAMES: dict[str, tuple[str, str]] = {}
for _role, _r in defs.ROLES.items():
    for _code, _name, _when in _r["templates"]:
        if "{n}" not in _code:
            _LOCAL_NAMES.setdefault(_code, (_name, _when))


def local_name(code: str) -> tuple[str, str]:
    if code in _LOCAL_NAMES:
        return _LOCAL_NAMES[code]
    if len(code) == 4 and code[0] == "P" and code[1].isdigit() and code[2] == "-":
        n, v = int(code[1]), code[3]
        if n == 1 and v == "D":
            return ("메시지 강조", "제품 하나의 메시지를 강하게 말할 때")
        name, when = defs.PI_VARIANTS.get(v, ("", ""))
        return name, when
    parts = code.split("-")
    if len(parts) >= 2 and parts[0] in defs.SOLUTIONS:
        s = defs.SOLUTIONS[parts[0]]
        if len(parts) == 2:
            kind = {"I": "전용 소개", "D": "전용 구성도", "S": "전용 공간 시나리오"}.get(parts[1], "")
            return (f"{s['name']} {kind}", s.get(parts[1], ""))
        if len(parts) == 3:
            ind = defs.SOLUTION_INDUSTRY_NAME.get(parts[2], parts[2])
            return (f"{ind} 업종 버전", f"고객 업종이 {ind}일 때 — 그 업종의 공간 사진과 순서로")
    if len(parts) == 3 and parts[0] in ("MI", "VP", "SS") and parts[1] in defs.INDUSTRIES:
        ind = defs.INDUSTRIES[parts[1]]["name"]
        name, _thumb, desc = defs.IROLE[parts[0]].get(parts[2], ("", "", ""))
        return (f"{ind} · {name}", f"{ind} 고객용 — {desc}")
    return (code, "")


async def catalog(codes: list[str]) -> dict[str, dict[str, Any]]:
    return await clients.export_templates(codes)


def available(cat: dict[str, dict[str, Any]], code: str | None) -> bool:
    """export 카탈로그에 있고 출시(ready)된 코드. 카탈로그를 못 읽었으면(빈 dict) 부록 코드는 쓸 수 있다고 본다."""
    if not code:
        return False
    if not cat:
        return True
    t = cat.get(code)
    return bool(t) and t.get("status", "ready") == "ready"


def pi_code(n: int, v: str) -> str:
    n = max(1, min(5, int(n or 1)))
    return f"P{n}-{v}"


# ── 업종 레이아웃 ──────────────────────────────────────────
def industry_code(p: dict[str, Any]) -> str | None:
    il = p.get("industry_layout") or {}
    return il.get("industry_code") or (p.get("customer") or {}).get("industry_code") or ((il.get("detected") or {}).get("code"))


def family_on(p: dict[str, Any], fam: str) -> bool:
    il = p.get("industry_layout") or {}
    return bool(il.get("decided")) and (il.get("families") or {}).get(fam, "on") == "on" and bool(il.get("industry_code"))


def applied_variant(p: dict[str, Any], role: str, type_: str | None) -> tuple[str, str] | None:
    """§10.6 PR3I 「적용」이 바꾸는 역할 → (계열, 변형). 카드 상태(바꿔 쓰기)를 반영한다."""
    il = p.get("industry_layout") or {}
    ind = il.get("industry_code")
    cards = il.get("cards") or {}
    if role in ("MS", "CB", "US"):
        fam, v = "MI", {"MS": "A", "CB": "B", "US": "C"}[role]
    elif role == "VP":
        fam = "VP"
        b = f"VP-{ind}-B"
        v = "B" if cards.get(b) == "applied" else "A"
    elif role == "EF":
        fam, v = "VP", "C"
    elif type_ == "solution" and role in ("VM", "SS", "OP"):
        fam, v = "SS", {"VM": "A", "SS": "B", "OP": "C"}[role]
    elif type_ != "solution" and role == "SM":
        fam, v = "SS", "A"
    else:
        return None
    code = f"{fam}-{ind}-{v}"
    if cards.get(code) == "alt":
        return None
    return fam, v


# ── 데이터 모양 규칙(§10.5) ─────────────────────────────────
def _n(sig: dict[str, Any], key: str) -> int:
    v = sig.get(key)
    if isinstance(v, (list, tuple)):
        return len(v)
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def data_shape(role: str, sig: dict[str, Any], *, customer_short: str = "", prev_code: str | None = None,
               product_count: int = 1, birdseye: bool = False) -> tuple[str, str, str]:
    """(코드, 이유, source) — source = data_shape | message."""
    s = sig or {}
    if role == "MS":
        years = s.get("years") or []
        if len(years) >= 3:
            return "MS-B", f"연결된 MI에 연도별 시장 규모({min(years)}~{max(years)})가 있어요", "data_shape"
        if s.get("tam") or s.get("expansion"):
            return "MS-C", "전 매장 확장 계획이 있어 노릴 수 있는 몫이 핵심이에요", "data_shape"
        if _n(s, "segments") >= 3:
            return "MS-D", "세그먼트마다 규모와 성장률이 있어요", "data_shape"
        if _n(s, "metrics") >= 3:
            return "MS-A", "지표는 여럿인데 연도별 추이는 없어요", "data_shape"
        return "MS-E", "수치는 적어도 왜 커지는지 설득해요", "message"
    if role == "TR":
        n = _n(s, "trends")
        if n >= 5:
            return "TR-C", "트렌드가 많아 우선순위가 필요해요", "data_shape"
        if n and s.get("trends_linked"):
            return "TR-B", f"트렌드 {n}개가 모두 {customer_short or '고객'} 과제와 이어져요", "data_shape"
        if s.get("timeline"):
            return "TR-A", "과거에서 다음으로 가는 방향을 보여줘요", "data_shape"
        return "TR-B", f"트렌드마다 '그래서 {customer_short or '고객'}은'을 붙여요", "message"
    if role == "CB":
        if s.get("ops_steps"):
            p1, p2 = (list(s.get("ops_problems") or []) + ["", ""])[:2]
            probs = " · ".join(x for x in (p1, p2) if x)
            return "CB-C", f"요구사항이 {s.get('ops_area') or '매장'} 운영 문제({probs})예요" if probs else "업무 단계마다 문제가 있어요", "data_shape"
        if s.get("strategy_goal"):
            return "CB-B", f"고객 전략 문서에 '{s['strategy_goal']}' 목표가 있어요", "data_shape"
        if s.get("swot"):
            return "CB-D", "내부 · 외부 상황을 균형 있게 봐요", "data_shape"
        return "CB-A", "공개 자료로 현황을 요약해요", "message"
    if role == "US":
        if s.get("journey"):
            return "US-B", "매장 방문 흐름 인터뷰가 있어요", "data_shape"
        if s.get("share"):
            return "US-C", "방문객 구성 비율 데이터가 있어요", "data_shape"
        return "US-A", "사용자 유형이 뚜렷이 나뉘어요", "message"
    if role == "CP":
        n, k = _n(s, "competitors"), _n(s, "criteria")
        if s.get("share"):
            return "CP-C", "점유율 데이터가 있어요", "data_shape"
        if n >= 5:
            return "CP-B", f"공급사 {n}곳을 두 축으로 나눌 수 있어요", "data_shape"
        if n and k >= 3:
            return "CP-A", f"경쟁사 {n}곳을 요구사항 {k}개로 비교해요", "data_shape"
        return "CP-A", "공급사를 항목별로 따져봐요", "message"
    if role == "IM":
        if s.get("executive"):
            return "IM-B", "경영진용 한 장 요약이에요", "data_shape"
        return "IM-A", "MI를 제안 방향 하나로 좁혀요", "message"
    if role == "CH":
        if s.get("desired_state"):
            return "CH-B", "요구사항에 바라는 운영 모습이 적혀 있어요", "data_shape"
        if s.get("root_cause"):
            return "CH-C", "원인을 짚어 제안의 필요성을 만들어요", "data_shape"
        return "CH-A", "문제와 그 비용을 함께 보여줘요", "message"
    if role == "VP":
        km = _n(s, "km")
        if _n(s, "stakeholders") >= 3:
            return "VP-D", "의사결정자가 여럿이에요", "data_shape"
        if km == 1:
            return "VP-C", "메시지 하나를 강하게 말해요", "data_shape"
        if 2 <= km <= 4:
            return "VP-B", f"Storyboard Key Message가 {km}개예요", "data_shape"
        if s.get("pairs"):
            return "VP-A", "과제마다 해법을 짝지어요", "data_shape"
        return "VP-B", "Key Message 수만큼 기둥으로 세워요", "message"
    if role == "EF":
        if _n(s, "kpi_pairs") >= 2:
            return "EF-A", "개선 수치(전/후)가 있어요", "data_shape"
        if s.get("roi"):
            return "EF-B", "재무 관점으로 설득해요", "data_shape"
        return "EF-C", "수치와 체감 효과를 함께 말해요", "message"
    if role == "BV":
        if s.get("two_views"):
            return "BV-B", "주간/야간, 도입 전/후를 비교해요", "data_shape"
        if s.get("executive"):
            return "BV-C", "경영진에게 제안 전체를 요약해요", "data_shape"
        return "BV-A", "조감도 1장에 공간 전체가 들어와요", "data_shape"
    if role == "ZP":
        if _n(s, "pins"):
            return "ZP-A", f"조감도 위에 포인트 {_n(s, 'pins')}곳이 표시돼 있어요", "data_shape"
        if s.get("zone_images"):
            return "ZP-B", "존마다 디테일 이미지가 있어요", "data_shape"
        if s.get("path"):
            return "ZP-C", "손님 동선 순서로 설명해요", "data_shape"
        return "ZP-A", "조감도 한 장 위에 포인트를 찍어요", "message"
    if role == "SM":
        n = _n(s, "spaces")
        if n >= 5 or _n(s, "cells") >= 12 or s.get("qty_table"):
            return "SM-B", "공간 · 제품이 많아 교차표가 필요해요", "data_shape"
        return "SM-A", f"공간이 {n or 1}곳이라 존 맵으로 충분해요", "data_shape"
    if role == "PI":
        if s.get("hero_product"):
            v, why = "D", "주력 제품을 지정했어요"
        elif s.get("spec_focus"):
            v, why = "C", "요구사항이 사양 비교 중심이에요"
        elif birdseye:
            v, why = "B", "조감도 배치안이 연결돼 설치 모습이 핵심이에요"
        else:
            v, why = "A", "제품 사진이 좋아요"
        code = pi_code(product_count, v)
        if prev_code and prev_code == code:
            for alt in ("B", "A", "C"):
                if alt != v:
                    code = pi_code(product_count, alt)
                    break
        elif prev_code and prev_code != code:
            why += " · 앞 시트와도 겹치지 않아요"
        return code, why, "data_shape"
    if role == "BM":
        if _n(s, "store_types") >= 2:
            return "BM-B", "매장 규모가 여러 가지예요", "data_shape"
        return "BM-A", "견적 전에 전체 물량을 확정해요", "message"
    if role == "SA":
        if _n(s, "solutions") >= 2:
            return "SA-A", "두 솔루션이 본사 → 매장으로 함께 배포돼요", "data_shape"
        if s.get("hub"):
            return "SA-B", "솔루션 하나가 여러 기기를 묶어요", "data_shape"
        return "SA-A", "본사 → 클라우드 → 매장 구조예요", "message"
    if role == "OP":
        if _n(s, "roles") >= 2:
            return "OP-B", "여러 역할이 한 흐름에 관여해요", "data_shape"
        if s.get("before_after"):
            return "OP-C", "업무가 얼마나 줄어드는지 보여줘요", "data_shape"
        return "OP-A", "하루 · 이벤트 흐름을 따라가요", "message"
    if role == "SF":
        if _n(s, "features") >= 3:
            return "SF-B", "기능을 고객의 언어로 옮겨요", "data_shape"
        return "SF-A", "솔루션 하나를 소개해요", "message"
    if role == "VM":
        n, m = _n(s, "spaces"), _n(s, "solutions")
        if n >= 2 and m >= 2:
            return "VM-A", f"공간 {n}곳 × 솔루션 {m}개가 격자로 맞아요", "data_shape"
        if n == 3 and m == 1:
            return "VM-B", "공간이 3곳이라 나란히 봐요", "data_shape"
        if s.get("birdseye_pins"):
            return "VM-C", "조감도가 있어 위치로 보여줘요", "data_shape"
        if s.get("timeline"):
            return "VM-D", "시간에 따라 공간을 넘나들어요", "data_shape"
        return "VM-A", "공간과 솔루션이 격자로 맞아요", "message"
    if role == "SS":
        if s.get("before_after"):
            return "SS-C", "도입 전후 차이가 눈에 보이는 공간이에요", "data_shape"
        if _n(s, "scenes") >= 3:
            return "SS-A", f"시간대별 장면 {_n(s, 'scenes')}개가 있어요", "data_shape"
        return "SS-B", "솔루션 → 제품 → 가치가 한 공간에서 이어져요", "message"
    if role == "CD":
        if s.get("before_after_photos"):
            return "CD-B", "도입 전후 사진이 있어요", "data_shape"
        if s.get("story"):
            return "CD-A", "과제 · 해결 · 성과가 모두 있는 사례예요", "data_shape"
        if _n(s, "public_kpis") >= 2:
            return "CD-C", "성과 수치가 공개된 사례예요", "data_shape"
        return "CD-A", "사례를 이야기로 풀어요", "message"
    if role == "CL":
        if _n(s, "cases") >= 6:
            return "CL-C", "사례 수 자체가 메시지예요", "data_shape"
        if _n(s, "cases") >= 3:
            return "CL-B", "업종이 다른 사례 세 건이에요", "data_shape"
        return "CL-A", "비슷한 사례 두 건을 나란히 봐요", "message"
    if role == "CM":
        n, k = _n(s, "competitors"), _n(s, "criteria")
        if s.get("criteria_are_rq"):
            return "CM-B", "고객 요구사항을 기준으로 비교해요", "data_shape"
        if n >= 3 and k >= 5 and s.get("scores"):
            return "CM-C", "여러 기준을 한 번에 종합해요", "data_shape"
        if n:
            return "CM-A", f"경쟁사 {n}곳을 항목 {k}개로 비교해요", "data_shape"
        return "CM-A", "항목별로 우위를 보여요", "message"
    if role == "ST":
        n = _n(s, "strengths")
        if _n(s, "rq_answered") >= 4:
            return "ST-B", "요구사항 4개에 하나씩 답해요", "data_shape"
        if _n(s, "verified_numbers") >= 1:
            return "ST-C", "검증된 수치가 있어요", "data_shape"
        return "ST-A", f"강점이 {n or 3}개이고 수치는 아직 검증 전이에요", "data_shape"
    if role == "SV":
        if s.get("nationwide"):
            return "SV-B", "매장이 전국에 흩어져 있어요", "data_shape"
        return "SV-A", "일정 · 단계 · 책임을 제시해요", "message"
    if role == "SC":
        if _n(s, "spec_conditions") >= 3:
            return "SC-B", "요구사항 충족을 증명해야 해요", "data_shape"
        return "SC-A", f"제품 {_n(s, 'products') or 2}종의 사양 차이를 보여줘요", "data_shape"
    if role == "SD":
        if s.get("install_req"):
            return "SD-B", "설치 검토가 필요해요", "data_shape"
        return "SD-A", "주력 제품 1종의 전체 사양이에요", "data_shape"
    default = (defs.ROLES.get(role) or {}).get("default") or ""
    return default, "", "message"


SXD_REASONS = {"MGI": "요구사항에 사내 서버 · 보안 조건이 있어요", "STP": "매장 기기가 여러 종류이고 매장이 많아요"}
SXS_REASONS = {"MGI": "POS 가격 연동이 핵심 장면이에요", "STP": "영업시간 기반 에너지 절감이 요구사항에 있어요"}


def dedicated(role: str, sol: str, sig: dict[str, Any]) -> tuple[str, str]:
    s = defs.SOLUTIONS.get(sol) or {"name": sol}
    if role == "SXI":
        return f"{sol}-I", f"연결된 솔루션 — {s['name']} 전용 템플릿이 있어요"
    if role == "SXD":
        return f"{sol}-D", (sig or {}).get("reason") or SXD_REASONS.get(sol) or f"{s['name']} — {s.get('D', '')}".strip(" —")
    return f"{sol}-S", (sig or {}).get("reason") or SXS_REASONS.get(sol) or f"{s['name']} — {s.get('S', '')}".strip(" —")


def recommend(sheet: dict[str, Any], p: dict[str, Any], cat: dict[str, dict[str, Any]], *, prev_code: str | None = None,
              birdseye: bool = False) -> dict[str, Any]:
    """추천(코드 · 이유 · source). 고정 여부와 상관없이 늘 계산한다(카드의 「추천」 표시)."""
    role = sheet.get("role") or ""
    sig = sheet.get("signals") or {}
    type_ = p.get("type")
    ind = industry_code(p)
    customer_short = ((p.get("customer") or {}).get("name") or "").replace(" 프랜차이즈", "")
    # 반입 힌트(§10.5 끝) — 카탈로그에 있으면 그대로
    hint = (sheet.get("template") or {}).get("import_hint")
    # 업종 레이아웃(적용한 계열)
    av = applied_variant(p, role, type_) if ind else None
    if av and family_on(p, av[0]):
        code = f"{av[0]}-{ind}-{av[1]}"
        if available(cat, code):
            name, _ = local_name(code)
            return {"code": code, "source": "industry", "reason": f"{defs.INDUSTRIES.get(ind, {}).get('name', ind)} 업종 레이아웃이에요 · {name}"}
    if role in ("SXI", "SXD", "SXS") and sheet.get("solution_code"):
        sol = sheet["solution_code"]
        code, reason = dedicated(role, sol, sig)
        # 고객 업종 코드가 그 솔루션 업종 버전과 같을 때만 업종 버전(§7.5 · AC-086 — FB 처럼 다른 체계는 전용 S)
        if role == "SXS" and ind and ind in ((defs.SOLUTIONS.get(sol) or {}).get("ind") or []):
            ind_code = f"{sol}-S-{ind}"
            if available(cat, ind_code):
                name = defs.SOLUTION_INDUSTRY_NAME.get(ind, ind)
                return {"code": ind_code, "source": "dedicated", "reason": f"고객 업종이 {name}이라 그 업종 버전이 맞아요"}
        if available(cat, code):
            return {"code": code, "source": "dedicated", "reason": reason}
    pc = int((sheet.get("template") or {}).get("product_count") or sig.get("products_n") or 1)
    code, reason, source = data_shape(role, sig, customer_short=customer_short, prev_code=prev_code, product_count=pc,
                                      birdseye=birdseye or bool(sig.get("birdseye")))
    hint_role = ((cat.get(hint) or {}).get("sheet_role") if (cat and hint) else None) or (hint.split("-")[0] if hint else None)
    if hint and hint_role not in (role, defs.IND_FOR.get(role, ("",))[0]):
        hint = None    # 다른 역할 템플릿(예 MI 의 CP-A 를 Why Samsung 경쟁 비교에) — 쓰지 않는다
    if hint and available(cat, hint):
        if hint == code and reason:
            return {"code": hint, "source": "import", "reason": reason}
        return {"code": hint, "source": "import", "reason": (sheet.get("template") or {}).get("import_reason") or "보낸 작업이 고른 템플릿이에요"}
    if code and not available(cat, code):
        fallback = (defs.ROLES.get(role) or {}).get("default") or code
        if role == "PI":
            fallback = pi_code(pc, "A")
        if available(cat, fallback):
            code, source = fallback, "message"
    return {"code": code or None, "source": source, "reason": reason}


def apply_recommendation(sheet: dict[str, Any], rec: dict[str, Any], *, force: bool = False) -> bool:
    """고정이 아니면 추천을 코드로. 바뀌면 True."""
    t = sheet.setdefault("template", {})
    t["recommended_code"] = rec.get("code")
    t["reason"] = rec.get("reason")
    if t.get("mode") == "pinned" and not force:
        return False
    if t.get("locked_manual") and t.get("code") and not force:
        return False
    old = t.get("code")
    t["code"] = rec.get("code")
    t["source"] = rec.get("source")
    t["mode"] = "auto"
    return old != t["code"]


# ── 템플릿 고르기 후보(§4.16) ───────────────────────────────
def candidate_codes(sheet: dict[str, Any], p: dict[str, Any], product_count: int | None) -> list[tuple[str, str]]:
    """(코드, 종류) 최대 5 — 보드 로직 그대로."""
    role = sheet.get("role") or ""
    ind = industry_code(p)
    out: list[tuple[str, str]] = []
    if role == "PI":
        n = max(1, min(5, int(product_count or (sheet.get("template") or {}).get("product_count") or 1)))
        return [(pi_code(n, v), "product") for v in ("A", "B", "C", "D")]
    if role in ("SXI", "SXD", "SXS"):
        sol = sheet.get("solution_code") or ""
        letter = {"SXI": "I", "SXD": "D", "SXS": "S"}[role]
        out.append((f"{sol}-{letter}", "dedicated"))
        if role == "SXS":
            for ic in (defs.SOLUTIONS.get(sol) or {}).get("ind", []):
                out.append((f"{sol}-S-{ic}", "industry_solution"))
        generic = {"SXI": ["SF-A", "SF-B"], "SXD": ["SA-A", "SA-B", "SA-C"], "SXS": ["OP-A", "OP-B", "SS-A"]}[role]
        out += [(c, "generic") for c in generic]
        return out[:5]
    if role in defs.IND_FOR and ind:
        fam, v = defs.IND_FOR[role]
        out.append((f"{fam}-{ind}-{v}", "industry"))
    out += [(c, "generic") for c, _n2, _w in (defs.ROLES.get(role) or {}).get("templates", [])]
    return out[:5]
