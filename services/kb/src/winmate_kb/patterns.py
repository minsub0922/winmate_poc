"""KB 질의 패턴 엔드포인트 — `POST /v1/query/{code}` (패턴마다 요청 모델 하나, 응답은 query.py 공통 봉투).

입력 필드 이름은 `winmate-kb/build/query.py` 메서드 인자 그대로다(QUERY_COOKBOOK). 결과는 원본 봉투에
`kb_version` 을 더하고, 이미지 행에는 로컬 주소(`thumb_url` · `stored_url`)를 붙인다(사내망 오프라인 — 원본 URL 대신 쓴다).

주의: 이 모듈은 FastAPI 가 함수 주석을 실제 클래스로 읽어야 해서 `from __future__ import annotations` 를 쓰지 않는다.
"""
import re
from typing import Any, Callable, Literal, Optional, Union

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from winmate_common.errors import ApiError

from . import imagecards
from .engine import kb
from .index import idx

router = APIRouter(prefix="/v1")


class _Req(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KindId(_Req):
    kind: str = Field(description="family · category · solution · service · model · deployment · vertical · industry_section …")
    id: str


Target = Union[tuple[str, str], KindId]


def _norm_target(kind: str, ident: str) -> tuple[str, str]:
    """대상 id 를 KB id 로 맞춘다 — 기능 서비스가 카탈로그 id(magicinfo) · 표시 이름(MagicINFO) · 모델코드를 넘겨도 0건이 되지 않게.
    solution: magicinfo · sol_magicinfo · kb:solution:… · 이름/별칭 → sol_… (카탈로그에 KB id 가 여럿이면 첫 번째)
    family: fam_… 이 아니면 모델코드 · 이름으로 찾아 fam_…  · model: mdl_… 이 아니면 모델코드로."""
    kind, ident = (kind or "").strip(), (ident or "").strip()
    if not ident:
        return (kind, ident)
    try:
        if kind == "solution" and not ident.startswith("sol_"):
            from . import solutions as SOL

            cat = SOL.resolve(ident)
            if cat and cat.get("kb_ids"):
                return (kind, cat["kb_ids"][0])
            for l in kb().A1(ident)["result"].get("links") or []:
                if l.get("type") == "solution" and l.get("id"):
                    return (kind, l["id"])
        elif kind in ("family", "model") and not ident.startswith(("fam_", "mdl_")):
            from .index import idx

            I = idx()
            mid = I.resolve_model(ident) if hasattr(I, "resolve_model") else None
            if mid:
                return ("family", I.models[mid]["family_id"]) if kind == "family" else ("model", mid)
            for l in kb().A1(ident)["result"].get("links") or []:
                if l.get("type") == kind and l.get("id"):
                    return (kind, l["id"])
    except Exception:  # noqa: BLE001 — 못 맞추면 받은 그대로
        pass
    return (kind, ident)


def _t(x: Any) -> tuple[str, str]:
    if isinstance(x, KindId):
        return _norm_target(x.kind, x.id)
    return _norm_target(str(x[0]), str(x[1]))


class Envelope(BaseModel):
    """query.py 공통 봉투."""

    model_config = ConfigDict(extra="allow")
    pattern: str
    result: Optional[dict[str, Any]] = Field(description="패턴 결과(패턴마다 모양이 다르다 — QUERY_COOKBOOK). get_entity 가 못 찾으면 null")
    evidence_paths: list[Any] = Field(default_factory=list)
    tier_min: Optional[str] = None
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    decision_hint: Literal["auto", "check", "ask"]
    decision_reasons: list[str] = Field(default_factory=list)
    needs_confirmation: list[str] = Field(default_factory=list)
    fallback_level: Optional[str] = None
    modes_used: list[str] = Field(default_factory=list)
    timings_ms: dict[str, int] = Field(default_factory=dict)
    kb_version: Optional[str] = Field(None, description="추가 — KB 빌드 버전(kb_meta.schema_version)")


# ── 요청 모델 ─────────────────────────────────────────────

class S1Req(_Req):
    text: str = Field(min_length=1, description="요구사항 문장")
    limit: int = Field(8, ge=1, le=50)


class S2Req(_Req):
    vertical: str = Field(description="KR 업종 id(kr_hotel …)")
    space: Optional[str] = Field(None, description="공간 유형 id(guest_room …)")


class A1Req(_Req):
    text: str = Field(min_length=1)
    lang: str = "ko"


class TextReq(_Req):
    text: str = Field(min_length=1)


class A3Item(_Req):
    name_raw: str = ""
    value_raw: str = ""


class A3Req(_Req):
    items: list[A3Item] = Field(description="요구 스펙 항목(이름 · 값 원문)")
    category_root: Optional[str] = None


class B1Req(_Req):
    vertical_id: str


class C1Req(_Req):
    spaces: list[str] = Field(default_factory=list)
    text: Optional[str] = None


class C2Req(_Req):
    capabilities: list[str] = Field(default_factory=list, description="hard 역량(cap_ 접두 없어도 됨)")
    category: Optional[str] = None
    space: Optional[str] = None
    vertical: Optional[str] = None
    limit: int = Field(15, ge=1, le=100)
    soft: list[str] = Field(default_factory=list)
    text: Optional[str] = None


class C3Req(_Req):
    family_id: str


class C4Req(_Req):
    family_id: str
    capabilities: list[str] = Field(default_factory=list)
    category: Optional[str] = None


class C6Requirement(_Req):
    key: str = Field(description="정규 스펙 키(brightness_nit · operation_hours …)")
    op: Literal[">=", "<=", "==", "contains"]
    value: Union[float, str]
    attr_name: Optional[str] = Field(None, description="추가 — 같은 정규 키에 값이 여럿일 때 고를 속성 이름(예 `소비전력 (On Mode)`). "
                                                       "없으면 원본처럼 첫 행(06-spec kb 요청 ①)")


class C6Req(_Req):
    ref: str = Field(description="mdl_… 또는 fam_…(대표 모델)")
    requirements: list[C6Requirement]


class D1Req(_Req):
    vertical: Optional[str] = None
    spaces: list[str] = Field(default_factory=list)
    targets: list[Target] = Field(default_factory=list, description="[kind, id] 또는 {kind, id}")
    text: Optional[str] = None
    limit: int = Field(10, ge=1, le=200)


class D2Req(_Req):
    vertical: Optional[str] = None
    space: Optional[str] = None


class D3Req(_Req):
    deployment_ids: list[str] = Field(default_factory=list)
    target: Optional[Target] = None


class D5Req(_Req):
    targets: list[Target]
    min_support: int = Field(2, ge=1)


class E1Req(_Req):
    about: list[Target] = Field(default_factory=list)
    vertical: Optional[str] = None
    space: Optional[str] = None
    locale: Optional[str] = None


class E2Req(_Req):
    theme: str = Field(min_length=1)
    limit: int = Field(15, ge=1, le=100)
    locale: Optional[str] = None


class E3Req(_Req):
    vertical: Optional[str] = None
    spaces: list[str] = Field(default_factory=list)
    products: list[Target] = Field(default_factory=list)
    customer: Optional[str] = None
    text: Optional[str] = None
    locale: Optional[str] = "ko-KR"
    limit: int = Field(12, ge=1, le=50)


class G1Req(_Req):
    space: str
    category: Optional[str] = None
    vertical: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)


class G2Req(_Req):
    kind: str = Field(description="family · category · solution …")
    ident: str
    limit: int = Field(20, ge=1, le=200)


class G4Req(_Req):
    family_id: str
    limit: int = Field(10, ge=1, le=100)


class G5Req(_Req):
    deployment_id: str
    limit: int = Field(30, ge=1, le=100)


class SearchReq(_Req):
    text: str = Field(min_length=1)
    k: int = Field(10, ge=1, le=50)
    modes: list[Literal["kw", "vec"]] = Field(default_factory=lambda: ["kw", "vec"])


class ImageSearchReq(_Req):
    text: str = Field(min_length=1)
    limit: int = Field(20, ge=1, le=200)
    grade: Optional[list[str]] = Field(None, description="등급 힌트 필터(A · A?C · C · D · E)")


EntityKind = Literal["family", "model", "category", "solution", "service", "vertical", "space_type", "deployment", "capability"]


class EntityReq(_Req):
    kind: EntityKind
    ident: str


# ── 실행기 ─────────────────────────────────────────────────

_INCH = re.compile(r"(\d+(?:\.\d+)?)\s*(?:인치|inch(?:es)?\b|in\b\.?|형|\"|”|″|''|吋)", re.I)
_CM = re.compile(r"\d\s*(?:cm|센티)", re.I)
_SIZE_NAME = re.compile(r"크기|사이즈|화면|디스플레이|모니터|TV|대각|인치|size|screen|display", re.I)
_INCH_NAME = re.compile(r"인치|inch", re.I)


def _a3(r: A3Req) -> dict[str, Any]:
    """A3 + 화면 크기 단위 보정(06-spec kb 요청 ② · 2026-10-07 요청 3). normalize_spec 은 이름으로만 정하고 값 속 단위를 못 본다.

    - 항목과 결과는 입력 순서로 짝짓는다(같은 이름 항목이 여럿이어도 섞이지 않음).
    - screen_size_cm 인데 값에 인치 표현(55인치 · 55형 · 55" · 55” · 55'' · 55 inch)이 있으면 → screen_size_inch(+ value_cm = ×2.54).
    - screen_size_inch(이름에 인치)인데 값이 cm 로만 적혀 있으면 → screen_size_cm(+ value_inch).
    - 이름으로 못 알아본 항목도 이름이 비었거나 크기 · 화면 · 디스플레이 낱말이고 값이 인치 표현이면 → screen_size_inch.
    - unit_basis: value(값의 단위) · name(이름의 단위) · default(단위 없음 → KB 기본 cm, 확인 필요).
    """
    src = [i.model_dump() for i in r.items]
    env = kb().A3(src, r.category_root)
    res = env["result"]
    unmapped_ids = {id(x) for x in res["unmapped"]}
    it_mapped = iter(res["mapped"])
    pairs: list[Optional[dict[str, Any]]] = [None if id(x) in unmapped_ids else next(it_mapped, None) for x in src]
    notes: list[str] = []
    for i, (it, m) in enumerate(zip(src, pairs)):
        name, val = it.get("name_raw") or "", it.get("value_raw") or ""
        label = name or val or f"#{i + 1}"
        if m is None:
            mm = _INCH.search(val) or (_INCH.search(name) if not val.strip() else None)
            if mm and (not name.strip() or _SIZE_NAME.search(name) or not val.strip()):
                v = float(mm.group(1))
                pairs[i] = {"name_raw": it.get("name_raw"), "attr": "screen_size_inch", "value": v, "value2": None, "unit": "inch",
                            "value_cm": round(v * 2.54, 1), "unit_basis": "value", "mapped_by": "inch_expression"}
                notes.append(f"이름으로 몰라 값의 인치 표현으로 screen_size_inch 로 읽음: {label}")
            continue
        if m.get("attr") not in ("screen_size_cm", "screen_size_inch"):
            continue
        v = m.get("value")
        inch_in_val, cm_in_val = bool(_INCH.search(val)), bool(_CM.search(val))
        if m["attr"] == "screen_size_cm" and inch_in_val:
            m.update(attr="screen_size_inch", unit="inch", unit_basis="value")
            if v is not None:
                m["value_cm"] = round(float(v) * 2.54, 1)
            notes.append(f"값의 인치 단위를 인식해 screen_size_inch 로 바꿈: {label}")
        elif m["attr"] == "screen_size_inch" and cm_in_val and not inch_in_val:
            m.update(attr="screen_size_cm", unit="cm", unit_basis="value")
            if v is not None:
                m["value_inch"] = round(float(v) / 2.54, 1)
            notes.append(f"이름은 인치지만 값이 cm 라 screen_size_cm 로 바꿈: {label}")
        elif m["attr"] == "screen_size_inch":
            m["unit_basis"] = "value" if inch_in_val else ("name" if _INCH_NAME.search(name) else "value")
            if v is not None:
                m["value_cm"] = round(float(v) * 2.54, 1)
        else:                                             # screen_size_cm
            m["unit_basis"] = "value" if cm_in_val else "default"
            if v is not None:
                m["value_inch"] = round(float(v) / 2.54, 1)
            if not cm_in_val:
                notes.append(f"단위가 없어 cm 로 읽음(인치일 수 있음 — 확인 필요): {label}")
    res["mapped"] = [m for m in pairs if m is not None]
    res["unmapped"] = [x for x, m in zip(src, pairs) if m is None]
    if notes:
        env["needs_confirmation"] = list(env.get("needs_confirmation") or []) + notes
    return env


def _c6(r: C6Req) -> dict[str, Any]:
    """C6 + 속성 이름 선택. attr_name 이 없으면 query.py 와 같다(그 키의 첫 행)."""
    if not any(x.attr_name for x in r.requirements):
        return kb().C6(r.ref, [x.model_dump(exclude={"attr_name"}) for x in r.requirements])
    k = kb()
    import time

    t0 = time.time()
    ref = r.ref
    if ref.startswith("mdl_"):
        rows = k.q("SELECT * FROM spec_value WHERE model_id=?", (ref,))
    else:
        rows = k.q("SELECT * FROM spec_value WHERE family_id=? AND model_id=(SELECT id FROM product_model WHERE family_id=? AND is_family_default=1)",
                   (ref, ref)) or k.q("SELECT * FROM spec_value WHERE family_id=?", (ref,))
    by: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row["norm_key"]:
            by.setdefault(row["norm_key"], []).append(row)
    out = []
    for req in r.requirements:
        vals = by.get(req.key, [])
        if req.attr_name:
            vals = [v for v in vals if v["attr_name"] == req.attr_name]
        if not vals:
            out.append({"attr": req.key, "required": f"{req.op} {req.value}", "actual": None, "verdict": "unknown",
                        "attr_name": req.attr_name})
            continue
        row = vals[0]
        v = row["value_num"]
        ok = None
        if req.op in (">=", "<=", "==") and v is not None:
            ok = {">=": v >= float(req.value), "<=": v <= float(req.value), "==": v == float(req.value)}[req.op]
        elif req.op == "contains":
            ok = str(req.value).lower() in (row["value_raw"] or "").lower() or str(req.value).lower() in (row["value_unit"] or "").lower()
        out.append({"attr": req.key, "required": f"{req.op} {req.value}", "actual": row["value_raw"],
                    "verdict": "unknown" if ok is None else ("pass" if ok else "fail"), "source": row["source_occurrence_id"],
                    "attr_name": row["attr_name"]})
    return k.envelope("C6", {"ref": ref, "rows": out}, modes=["sql"], t0=t0, tiers=["T2_official"])


def _entity(r: EntityReq) -> dict[str, Any]:
    return kb().entity(r.kind, r.ident)


PATTERNS: list[dict[str, Any]] = [
    {"code": "S1", "method": "S1", "name": "요구사항 → 공간별 제품 추천", "model": S1Req,
     "run": lambda r: kb().S1(r.text, limit=r.limit),
     "desc": "요구 문장을 절 단위로 나눠 공간 · 분류 · 역량을 묶고 공간마다 후보 제품군(C2) · 솔루션 · 유사 사례(D1)를 낸다(체인 A1 · A2 → C1 → C2 → D1)."},
    {"code": "S2", "method": "S2", "name": "업종 → 장면 구성", "model": S2Req,
     "run": lambda r: kb().S2(r.vertical, r.space),
     "desc": "업종 페이지 장면(공간 · 항목 · 메시지 · 배치 이미지)과 유사 사례(체인 B1 → E1 → G1 → D1)."},
    {"code": "A1", "method": "A1", "name": "엔티티 링킹", "model": A1Req,
     "run": lambda r: kb().A1(r.text, r.lang),
     "desc": "문장 속 모델코드 · 제품 · 분류 · 솔루션 · 업종 별칭과 공간 · 역량 키워드를 찾는다."},
    {"code": "A2", "method": "A2", "name": "업종 판별", "model": TextReq,
     "run": lambda r: kb().A2(r.text),
     "desc": "KR 업종 top-2(애매하면 ask). 추가: 후보마다 정규화 전 점수 raw_score."},
    {"code": "A3", "method": "A3", "name": "요구 스펙 항목 → 정규 키", "model": A3Req, "run": _a3,
     "desc": "이름 · 값 원문 → 정규 스펙 키 · 수치 · 단위. 추가: 값의 '인치' 를 screen_size_inch 로 보정."},
    {"code": "B1", "method": "B1", "name": "업종 프리셋", "model": B1Req,
     "run": lambda r: kb().B1(r.vertical_id),
     "desc": "업종 페이지 장면 순서 = 공간 시퀀스, 장면별 추천 항목, 히어로 문구, 추천 솔루션, 대표 사례."},
    {"code": "B2", "method": "B2", "name": "요구사항 결핍 → 확인 질문", "model": TextReq,
     "run": lambda r: kb().B2(r.text),
     "desc": "문장에 나온 공간이 요구하는 역량 중 문장에 없는 것을 질문으로."},
    {"code": "C1", "method": "C1", "name": "공간 · 요구 → 역량", "model": C1Req,
     "run": lambda r: kb().C1(r.spaces, r.text),
     "desc": "공간(requires 초안)과 문장 키워드로 hard · soft 역량."},
    {"code": "C2", "method": "C2", "name": "후보 제품군", "model": C2Req,
     "run": lambda r: kb().C2(r.capabilities, category=r.category, space=r.space, vertical=r.vertical, limit=r.limit,
                               soft=r.soft, text=r.text),
     "desc": "역량 충족 + 사이트 추천 + 분류 일치 + 선례 + 문장 유사도로 후보 제품군."},
    {"code": "C3", "method": "C3", "name": "제품 → 적합 업종 · 공간 · 사례", "model": C3Req,
     "run": lambda r: kb().C3(r.family_id),
     "desc": "이 제품군(또는 소속 분류)이 추천된 업종 · 공간과 쓰인 도입사례(역방향)."},
    {"code": "C4", "method": "C4", "name": "제외 사유", "model": C4Req,
     "run": lambda r: kb().C4(r.family_id, r.capabilities, r.category),
     "desc": "역량 근거 없음 · 분류 밖 같은 제외 사유."},
    {"code": "C6", "method": "C6", "name": "요구 스펙 충족 판정", "model": C6Req, "run": _c6,
     "desc": "정규 스펙 키로 pass · fail · unknown(스펙 없으면 추정하지 않음). 추가: attr_name 으로 속성 고르기."},
    {"code": "D1", "method": "D1", "name": "유사 사례", "model": D1Req,
     "run": lambda r: kb().D1(vertical=r.vertical, spaces=r.spaces, targets=[_t(x) for x in r.targets], text=r.text, limit=r.limit),
     "desc": "업종 · 공간 · 제품 겹침 + 문장 유사도로 분해 점수."},
    {"code": "D2", "method": "D2", "name": "사례 통계", "model": D2Req,
     "run": lambda r: kb().D2(vertical=r.vertical, space=r.space),
     "desc": "업종(또는 공간) 사례 수 · 많이 쓴 제품 · 공간 · 요구 태그."},
    {"code": "D3", "method": "D3", "name": "성과 KPI", "model": D3Req,
     "run": lambda r: kb().D3(r.deployment_ids, _t(r.target) if r.target else None),
     "desc": "사례 KPI 문장(claim_flag, T5 — 원문 대조 필요)."},
    {"code": "D5", "method": "D5", "name": "공존 패턴", "model": D5Req,
     "run": lambda r: kb().D5([_t(x) for x in r.targets], r.min_support),
     "desc": "사례에서 함께 쓰인 제품 · 솔루션(support · confidence · lift)."},
    {"code": "E1", "method": "E1", "name": "메시지 계층", "model": E1Req,
     "run": lambda r: kb().E1([_t(x) for x in r.about], r.vertical, r.space, r.locale),
     "desc": "대상 · 업종 · 공간별 원문 메시지(tagline → key message → proof point, 출처 · claim)."},
    {"code": "E2", "method": "E2", "name": "테마로 메시지 찾기", "model": E2Req,
     "run": lambda r: kb().E2(r.theme, r.limit, r.locale),
     "desc": "문장과 비슷한 원문 메시지와 그 대상(제품 · 솔루션)."},
    {"code": "E3", "method": "E3", "name": "컨텍스트 → 메시지 묶음", "model": E3Req,
     "run": lambda r: kb().E3(r.vertical, r.spaces, [_t(x) for x in r.products], r.customer, r.text, r.locale, r.limit),
     "desc": "업종 · 공간 · 제품 · 타겟고객 · 요구사항(모두 선택) → 헤드라인 · 핵심 메시지 · 제품 메시지 · 근거 사례."},
    {"code": "G1", "method": "G1", "name": "공간 × 분류 배치 이미지", "model": G1Req,
     "run": lambda r: kb().G1(r.space, r.category, r.vertical, r.limit),
     "desc": "공간 맥락 이미지(등급순), 없으면 폴백(fallback_level)."},
    {"code": "G2", "method": "G2", "name": "제품 · 분류가 나오는 이미지", "model": G2Req,
     "run": lambda r: kb().G2(*_norm_target(r.kind, r.ident), r.limit),
     "desc": "설치 · 사례 사진 우선."},
    {"code": "G4", "method": "G4", "name": "제품 단독컷", "model": G4Req,
     "run": lambda r: kb().G4(r.family_id, r.limit),
     "desc": "제품군 PDP 갤러리(confirmed)."},
    {"code": "G5", "method": "G5", "name": "사례 사진", "model": G5Req,
     "run": lambda r: kb().G5(r.deployment_id, r.limit),
     "desc": "도입사례 페이지 사진."},
    {"code": "search", "method": "search", "name": "하이브리드 검색", "model": SearchReq,
     "run": lambda r: kb().search(r.text, k=r.k, modes=tuple(r.modes)),
     "desc": "원문 청크 · 엔티티(trigram BM25 + 부분 일치 + LSA 벡터 → RRF), 결과마다 원문 URL · 섹션."},
    {"code": "image_search", "method": "image_search", "name": "이미지 검색", "model": ImageSearchReq, "aliases": ["images"],
     "run": lambda r: kb().image_search(r.text, limit=r.limit, grade=r.grade),
     "desc": "alt · 캡션 · 섹션 · 맥락으로 이미지 검색(등급 힌트 재정렬)."},
    {"code": "get_entity", "method": "entity", "name": "엔티티 통합 보기", "model": EntityReq, "aliases": ["entity"], "run": _entity,
     "desc": "흩어진 정보(언급 문서 · 메시지 · 그래프 엣지 · 스펙 · 태그)를 엔티티 하나에 모은다. 못 찾으면 result=null, decision_reasons=[NOT_FOUND]."},
]


def _add_local_urls(obj: Any, depth: int = 0) -> None:
    """결과 안의 이미지 행(id 가 img_ 이고 url 이 있는 dict)에 로컬 주소를 붙인다."""
    if depth > 6:
        return
    if isinstance(obj, dict):
        if isinstance(obj.get("id"), str) and obj["id"].startswith("img_") and "url" in obj:
            imagecards.image_row_urls(obj)
        for v in obj.values():
            if isinstance(v, (dict, list)):
                _add_local_urls(v, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, (dict, list)):
                _add_local_urls(v, depth + 1)


def finalize(env: dict[str, Any]) -> dict[str, Any]:
    _add_local_urls(env.get("result"))
    env["kb_version"] = idx().meta.get("schema_version")
    return env


def run(code: str, req: Any) -> dict[str, Any]:
    p = next((x for x in PATTERNS if x["code"] == code or code in x.get("aliases", [])), None)
    if p is None:
        raise ApiError(404, "NOT_FOUND", f"패턴을 찾을 수 없습니다: {code}", {"resource": "pattern", "id": code})
    try:
        env = p["run"](req)
    except KeyError as exc:
        raise ApiError(400, "INVALID_ARGUMENT", f"알 수 없는 값: {exc}", {"pattern": code}) from exc
    return finalize(env)


def _make_endpoint(code: str, model: type) -> Callable[..., Any]:
    def endpoint(body):  # type: ignore[no-untyped-def]
        return run(code, body)

    endpoint.__annotations__ = {"body": model, "return": Envelope}
    endpoint.__name__ = f"query_{code}"
    return endpoint


for _p in PATTERNS:
    for _code in [_p["code"]] + list(_p.get("aliases", [])):
        alias_note = f" (= {_p['code']})" if _code != _p["code"] else ""
        router.add_api_route(
            f"/query/{_code}", _make_endpoint(_code, _p["model"]), methods=["POST"], response_model=Envelope,
            name=f"query_{_code}", tags=["internal"], summary=f"{_p['code']} · {_p['name']}{alias_note}",
            description=_p["desc"] + f"\n\nquery.py: `KB.{_p['method']}`",
        )


class PatternInfo(BaseModel):
    code: str
    method: str
    name: str
    description: str
    route: str
    aliases: list[str]
    request_schema: dict[str, Any]


class PatternList(BaseModel):
    items: list[PatternInfo]
    envelope_fields: list[str]


@router.get("/patterns", response_model=PatternList, tags=["internal"])
def list_patterns() -> PatternList:
    """KB 질의 패턴 목록(설명 · 요청 JSON 스키마). 실행은 `POST /v1/query/{code}`."""
    items = [PatternInfo(code=p["code"], method=p["method"], name=p["name"], description=p["desc"],
                         route=f"/v1/query/{p['code']}", aliases=list(p.get("aliases", [])),
                         request_schema=p["model"].model_json_schema()) for p in PATTERNS]
    return PatternList(items=items, envelope_fields=list(Envelope.model_fields))
