"""kb API (/v1). 이 파일 · patterns.py 의 엔드포인트가 contracts/kb.json 이 된다(make contracts).

화면(셸)용 = 00-shell §7.2.2 ~ §7.2.16 그대로. 기능 서비스용(태그 internal) = 질의 패턴 · 업종 세그먼트 · 스펙 표 · 생애주기 · 배치 규칙 · 엔티티.
KB 는 CPU 를 쓰는 동기 코드라 엔드포인트는 모두 동기 함수(스레드 풀)로 둔다.
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Path, Query, Response
from pydantic import BaseModel, Field

from winmate_common.errors import ApiError, bad_request, not_found

from . import cases as CS
from . import catalog, images, imagecards, segments, solutions, specs
from . import schemas as S
from .engine import engine, kb, q
from .index import idx
from .patterns import Envelope, finalize

router = APIRouter(prefix="/v1")

DEFAULT_LIMIT, MAX_LIMIT = 20, 100


def page(items: list[Any], limit: int, cursor: str | None) -> tuple[list[Any], str | None]:
    """목록 규약: ?limit=&cursor= → (이번 쪽, next_cursor). cursor 는 불투명 문자열(지금은 위치)."""
    off = 0
    if cursor:
        try:
            off = int(cursor)
            if off < 0:
                raise ValueError
        except ValueError:
            raise bad_request("cursor 가 올바르지 않습니다", cursor=cursor) from None
    chunk = items[off:off + limit]
    nxt = str(off + limit) if off + limit < len(items) else None
    return chunk, nxt


LimitQ = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="기본 20, 최대 100")
CursorQ = Query(None, description="이전 응답의 next_cursor")


class ServiceInfo(BaseModel):
    service: str
    title: str
    version: str


@router.get("/info", response_model=ServiceInfo, tags=["meta"])
def info() -> ServiceInfo:
    return ServiceInfo(service="kb", title="지식 DB — 제품 · 솔루션 · 업종 · 공간 · 사례 · 메시지 · 이미지 질의 (winmate-kb)", version="0.1.0")


# ── §7.2.2 메타 ───────────────────────────────────────────

@router.get("/meta", response_model=S.MetaOut, tags=["meta"])
def meta() -> dict[str, Any]:
    I = idx()
    m = I.meta
    collected = q("SELECT max(fetched_at) t FROM source_document")[0]["t"]
    pf = m.get("products_fetched_at")
    return {"kb_version": m.get("schema_version") or "kb_v1", "collected_at": collected, "products_fetched_at": pf,
            "catalog_version": pf[:7] if pf else None,
            "counts": {"case_pages": len(I.body_deployments()), "deployments": int(m.get("count.deployments") or len(I.deps)),
                       "families": int(m.get("count.families") or len(I.fams)), "models": int(m.get("count.models") or len(I.models)),
                       "image_assets": int(m.get("count.image_assets") or len(I.assets)),
                       "thumbnails": len(images.thumbs().by_asset), "local_images": images.local_count()},
            "warm": engine().warm}


# ── §7.2.3 분류 ───────────────────────────────────────────

@router.get("/categories", response_model=S.CategoryList, tags=["products"])
def list_categories(parent_id: str | None = Query(None, description="없으면 L1(9개)"), limit: int = LimitQ,
                    cursor: str | None = CursorQ) -> dict[str, Any]:
    if parent_id and parent_id not in idx().cats:
        raise not_found("분류", parent_id)
    items, nxt = page(catalog.categories(parent_id), limit, cursor)
    return {"items": items, "next_cursor": nxt}


# ── §7.2.4 시리즈 · 모델 표 ───────────────────────────────

@router.get("/families", response_model=S.FamilyList, tags=["products"])
def list_families(category_id: str = Query(..., description="L1 · L2 · L3 분류 id"), limit: int = LimitQ,
                  cursor: str | None = CursorQ) -> dict[str, Any]:
    if category_id not in idx().cats:
        raise not_found("분류", category_id)
    fids, nxt = page(catalog.family_ids(category_id), limit, cursor)
    return {"items": [catalog.family_item(f) for f in fids], "next_cursor": nxt}


@router.get("/models", response_model=S.ModelList, tags=["products"])
def list_models(family_id: str | None = Query(None), category_id: str | None = Query(None),
                q_: str | None = Query(None, alias="q", description="모델코드 일부 · 표시명 · 시리즈 코드 · 제품군 이름"),
                limit: int = LimitQ, cursor: str | None = CursorQ) -> dict[str, Any]:
    I = idx()
    if family_id and family_id not in I.fams:
        raise not_found("제품군", family_id)
    if category_id and category_id not in I.cats:
        raise not_found("분류", category_id)
    if not (family_id or category_id or (q_ and q_.strip())):
        raise bad_request("family_id · category_id · q 중 하나가 필요합니다")
    mids, cat = catalog.models_for(family_id, category_id, q_)
    prof = catalog.column_profile(cat)
    cols = catalog.columns_of(prof)
    chunk, nxt = page(mids, limit, cursor)
    cache: dict[str, Any] = {}
    return {"columns": cols, "items": [catalog.model_row(m, prof["columns"], cache) for m in chunk], "next_cursor": nxt,
            "profile": prof["id"]}


# ── §7.2.5 제품 검색 ──────────────────────────────────────

@router.get("/products/search", response_model=S.ProductSearchOut, tags=["products"])
def products_search(q_: str = Query(..., alias="q", min_length=1), limit: int = Query(5, ge=1, le=20),
                    kinds: str = Query("model,family", description="model · family 쉼표 목록")) -> dict[str, Any]:
    ks = [k.strip() for k in kinds.split(",") if k.strip()]
    bad = [k for k in ks if k not in ("model", "family")]
    if bad:
        raise ApiError(400, "UNSUPPORTED_FILTER", "kinds 는 model · family 만 받습니다", {"filters": ["kinds"], "values": bad})
    return {"items": catalog.product_search(q_, limit, ks)}


# ── §7.2.6 ~ §7.2.8 제품 상세 ─────────────────────────────
# 모델코드에 / 가 든 모델(LH012IWCMWS/XU · SL-C2410ND/KRM 등 58개)을 받으려고 경로 변환기를 path 로 둔다(08-birdseye 요청 1).
# path 는 끝까지 삼키므로 하위 자원(/images · /cases · /lifecycle)을 상세보다 먼저 등록한다. 계약 경로는 그대로 `{model_code}`.
# 서비스 클라이언트는 / 를 %2F 로 넣어 부르면 된다(계약 검증 `[^/]+` 통과) — 그대로 / 로 넣어도 kb 는 받는다.

ModelCodePath = Path(..., description="모델코드(LH55QMCEBGCXKR · / 가 든 코드는 %2F 로 · 그대로도 받음) · mdl_… · fam_…(대표 모델)")


def _model_or_404(model_code: str) -> str:
    mid = idx().resolve_model(model_code)
    if not mid:
        raise not_found("모델", model_code)
    return mid


@router.get("/models/{model_code:path}/images", response_model=S.ImageList, tags=["products"])
def get_model_images(model_code: str = ModelCodePath) -> dict[str, Any]:
    mid = _model_or_404(model_code)
    items = catalog.model_images(mid)
    return {"items": items, "total": len(items)}


@router.get("/models/{model_code:path}/cases", response_model=S.ModelCases, tags=["products"])
def get_model_cases(model_code: str = ModelCodePath, match: Literal["model", "series", "usage"] | None = Query(None)) -> dict[str, Any]:
    mid = _model_or_404(model_code)
    return CS.model_cases(mid, match)


class Successor(BaseModel):
    model_code: str
    id: str
    display_name: str
    relation: Literal["successor", "similar"] = Field(description="KB 에 후속 데이터가 없어(DR10) 지금은 similar 만 준다")
    reason: str = Field(description="예 `같은 계열(WM) · 같은 크기(55\") · 세대 B → F · 출시 2026-03 (더 최근)`")
    newer: bool | None = Field(description="출시년월(스펙 '동일모델의 출시년월', 같은 세대 중 가장 이른 값)로 본 원본보다 최근인지. 모르면 null")
    release_ym: str | None
    basis: str


class Lifecycle(BaseModel):
    ref: str
    model_code: str | None
    id: str | None = None
    status: Literal["on_sale", "not_in_catalog"] = Field(description="on_sale = KB(사이트 목록)에 있음(DR09) · not_in_catalog = KB 에 없음(단종이거나 미등록)")
    sale_status_code: str | None = Field(description=S.SALE_STATUS_DESC)
    sold_out_flag: str | None
    successor: dict[str, Any] | None = Field(description="공식 후속 모델 — KB 에 데이터가 없어 항상 null(DR10)")
    basis: str
    gaps: list[str]
    successors: list[Successor] = Field(default_factory=list, description=(
        "추가(06-spec 요청 2 · C5 대용) — 같은 계열 · 같은 크기(LED 는 피치 코드)의 다른 세대 KB 모델(사이니지 · LED 만, 표시명 규칙). "
        "원본보다 오래된 것으로 확인된 후보는 뺀다. 최근 출시 먼저. 후속 여부는 사람이 정한다"))
    release_ym: str | None = Field(None, description="추가 — 스펙 '동일모델의 출시년월'(YYYY-MM)")
    warranty: S.Warranty | None = Field(None, description="추가(06-spec 요청 1) — 스펙 보증 행 원문(없으면 null)")


@router.get("/models/{model_code:path}/lifecycle", response_model=Lifecycle, tags=["internal"])
def get_model_lifecycle(model_code: str = ModelCodePath) -> dict[str, Any]:
    """생애주기(06-spec §4.17): KB 에 있으면 판매 중(DR09), 없으면 not_in_catalog. 공식 후속 모델은 KB 에 없다(DR10) —
    `successors` 에 같은 계열 · 같은 크기 다른 세대 모델(relation=similar, newer)을 준다."""
    return specs.lifecycle(model_code)


@router.get("/models/{model_code:path}", response_model=S.ModelDetail, tags=["products"])
def get_model(model_code: str = ModelCodePath) -> dict[str, Any]:
    """모델코드(LH55QMCEBGCXKR · LH012IWCMWS/XU) · mdl_ · fam_(대표 모델) 모두 받는다."""
    mid = _model_or_404(model_code)
    mc = CS.model_cases(mid)
    shown = len(mc["items"])
    return catalog.model_detail(mid, {"shown": shown, "corpus": mc["corpus"]})


# ── §7.2.9 ~ §7.2.12 솔루션 ───────────────────────────────

@router.get("/solutions", response_model=S.SolutionList, tags=["solutions"])
def list_solutions(q_: str | None = Query(None, alias="q"),
                   industry: Literal["retail", "hospitality", "education", "healthcare", "office"] | None = Query(None),
                   limit: int = LimitQ, cursor: str | None = CursorQ) -> dict[str, Any]:
    items, nxt = page(solutions.search(q_, industry), limit, cursor)
    return {"items": items, "next_cursor": nxt}


@router.get("/solutions/{solution_id}", response_model=S.SolutionDetail, tags=["solutions"])
def get_solution(solution_id: str) -> dict[str, Any]:
    """카탈로그 id(magicinfo) 또는 KB id(sol_magicinfo)."""
    return solutions.detail(solution_id)


@router.get("/solutions/{solution_id}/images", response_model=S.SolutionImages, tags=["solutions"])
def get_solution_images(solution_id: str) -> dict[str, Any]:
    sol = solutions.resolve(solution_id)
    if sol is None:
        raise not_found("솔루션", solution_id)
    return solutions.images(sol)


@router.get("/solutions/{solution_id}/cases", response_model=S.SolutionCases, tags=["solutions"])
def get_solution_cases(solution_id: str) -> dict[str, Any]:
    return solutions.cases_out(solution_id)


# ── §7.2.13 · §7.2.14 이미지 ──────────────────────────────

def _browse_images() -> list[tuple[str, str | None]]:
    """검색어 없을 때: 사례 대표 사진(최신 사례부터) + 제품군 갤러리 첫 장."""
    I = idx()
    out = []
    for did in sorted(I.body_deployments(), key=lambda d: I.deps[d]["date"] or "", reverse=True):
        ph = I.dep_photos.get(did)
        if ph:
            out.append((ph[0], I.deps[did]["document_id"]))
    for fid in sorted(I.gallery, key=lambda f: (I.fams[f]["name_ko"] or "", f)):
        out.append((I.gallery[fid][0], f"doc_pdp_{I.fams[fid]['goods_id']}"))
    return out


@router.get("/images/search", response_model=S.ImageSearchOut, tags=["images"])
def images_search(q_: str | None = Query(None, alias="q"), source: Literal["all", "official", "case"] = Query("all"),
                  verified_only: bool = Query(True, description="출처 페이지와 원본 URL 이 모두 있는 이미지만(KB 이미지는 모두 해당)"),
                  grades: str | None = Query(None, description="등급 쉼표 목록. 기본 A,A?C,C(도식 D · 아이콘 E 제외 [제안])"),
                  limit: int = Query(24, ge=1, le=MAX_LIMIT), cursor: str | None = CursorQ) -> dict[str, Any]:
    I = idx()
    allowed = {g.strip() for g in (grades or "A,A?C,C").split(",") if g.strip()}
    rows: list[tuple[str, str | None]] = []
    if q_ and q_.strip():
        res = kb().image_search(q_.strip(), limit=400)["result"]["images"]
        rows = [(r["id"], r.get("page_type")) for r in res]
        prefer_pt = True
    else:
        rows = _browse_images()
        prefer_pt = False
    seen: set[str] = set()
    filtered = []
    for aid, hint in rows:
        a = I.assets.get(aid)
        if not a or aid in seen or a["grade_hint"] not in allowed:
            continue
        if verified_only and not (a["url"] or a["url_mobile"]) :
            continue
        seen.add(aid)
        filtered.append((aid, hint, a["rights"]))
    counts = {"official": sum(1 for x in filtered if x[2] == "official"), "case": sum(1 for x in filtered if x[2] == "customer_case")}
    counts["all"] = counts["official"] + counts["case"]
    if source != "all":
        want = "official" if source == "official" else "customer_case"
        filtered = [x for x in filtered if x[2] == want]
    chunk, nxt = page(filtered, limit, cursor)
    items = []
    for aid, hint, _ in chunk:
        c = imagecards.card(aid, prefer_page_type=hint) if prefer_pt else imagecards.card(aid, prefer_doc=hint)
        if c:
            items.append(c)
    return {"counts": counts, "items": items, "next_cursor": nxt}


@router.get("/images/{image_id}", response_model=S.ImageMeta, tags=["images"])
def get_image(image_id: str) -> dict[str, Any]:
    if image_id not in idx().assets:
        raise not_found("이미지", image_id)
    m = imagecards.meta(image_id)
    if m is None:
        raise not_found("이미지", image_id)
    return m


_IMG_RESPONSES: dict[int | str, dict[str, Any]] = {200: {"content": {"image/webp": {}, "image/jpeg": {}, "image/png": {}},
                                                         "description": "이미지 바이너리"}}


@router.get("/images/{image_id}/thumb", response_class=Response, responses=_IMG_RESPONSES, tags=["images"])
def get_image_thumb(image_id: str) -> Response:
    """썸네일(webp, 긴 변 160~176px). 없으면 404."""
    if image_id not in idx().assets:
        raise not_found("이미지", image_id)
    b = images.thumb_bytes(image_id)
    if b is None:
        raise not_found("이미지 썸네일", image_id)
    return Response(content=b, media_type="image/webp", headers={"Cache-Control": "public, max-age=604800", "X-KB-Image-Source": "thumbnail"})


@router.get("/images/{image_id}/file", response_class=Response, responses=_IMG_RESPONSES, tags=["images"])
def get_image_file(image_id: str) -> Response:
    """로컬 저장본(WKB_IMAGE_DIR/<id>.webp|jpg|png). 아직 없으면 썸네일. 둘 다 없으면 404."""
    if image_id not in idx().assets:
        raise not_found("이미지", image_id)
    local = images.local_file(image_id)
    got = images.file_bytes(image_id)
    if got is None:
        raise not_found("이미지 파일", image_id)
    data, mt = got
    return Response(content=data, media_type=mt, headers={"Cache-Control": "public, max-age=86400",
                                                           "X-KB-Image-Source": "local" if local else "thumbnail"})


# ── §7.2.15 · §7.2.16 사례 · 업종 ─────────────────────────

@router.get("/cases/search", response_model=S.CaseSearchOut, tags=["cases"], response_model_by_alias=True)
def cases_search(q_: str | None = Query(None, alias="q"), vertical_id: str | None = Query(None, description="kr_* 업종(하위 업종이면 상위 사례 필터로 찾는다)"),
                 target: str | None = Query(None, description="family:fam_… · solution:sol_…|magicinfo · category:cat_… · model:…"),
                 period: Literal["all", "1y", "3y", "5y"] = Query("all"),
                 region: str | None = Query(None, description="지원 안 함(갭 G-CASE-4) — 값이 있으면 400 UNSUPPORTED_FILTER"),
                 infer_vertical: bool = Query(False, description="업종이 없을 때 검색어로 판별(A2 decision_hint=auto 일 때만)"),
                 vertical_from: Literal["user", "task"] = Query("user", description="추가 — vertical_id 를 누가 정했나(applied.vertical.from)"),
                 limit: int = Query(10, ge=1, le=MAX_LIMIT), cursor: str | None = CursorQ) -> dict[str, Any]:
    if region:
        raise ApiError(400, "UNSUPPORTED_FILTER", "지역 필터는 아직 지원하지 않습니다(사례에 지역 데이터 없음)",
                       {"filters": ["region"], "gap": "G-CASE-4"})
    hits, corp, applied = CS.search(q_, vertical_id, target, period, infer_vertical, vertical_from)
    chunk, nxt = page(hits, limit, cursor)
    return {"corpus": corp, "applied": applied, "items": CS.finish_matches(chunk, applied), "next_cursor": nxt, "total": len(hits)}


@router.get("/cases/{case_id}", response_model=S.CaseDetail, tags=["cases"])
def get_case(case_id: str) -> dict[str, Any]:
    return CS.detail(case_id)


class SimilarCases(BaseModel):
    items: list[S.CaseCard]


@router.get("/cases/{case_id}/similar", response_model=SimilarCases, tags=["cases"])
def get_similar_cases(case_id: str, limit: int = Query(5, ge=1, le=20)) -> dict[str, Any]:
    """이 사례와 비슷한 사례(D1: 업종 · 공간 · 제품 · 제목 문장)."""
    return {"items": CS.similar(case_id, limit)}


@router.get("/verticals", response_model=S.VerticalList, tags=["verticals"])
def list_verticals(scheme: Literal["kr_site", "us_site", "winmate16"] = Query("kr_site"), limit: int = Query(MAX_LIMIT, ge=1, le=MAX_LIMIT),
                   cursor: str | None = CursorQ) -> dict[str, Any]:
    """kr_site = KR 사이트 업종 22(상위 10 · 하위 12) · us_site = 13 · winmate16 = Winmate 16업종(10-proposal 부록 C, K3)."""
    I = idx()
    if scheme == "winmate16":
        items = [{"id": s["id"], "name": s["name"], "parent_id": None, "scheme": "winmate16", "code": s["code"], "full": s["full"],
                  "short": s["short"], "kb_name": s["kb_name"], "kr_vertical_ids": s["kr_vertical_ids"],
                  "us_vertical_ids": s["us_vertical_ids"], "mapping_status": s["mapping_status"]} for s in segments.table()]
    else:
        items = [{"id": vid, "name": v["name_ko"] or v["name_en"] or vid, "parent_id": v["parent_id"], "scheme": v["scheme"],
                  "url": v["url"]} for vid, v in I.verticals.items() if v["scheme"] == scheme]
    chunk, nxt = page(items, limit, cursor)
    return {"items": chunk, "next_cursor": nxt}


class SpaceTypeItem(BaseModel):
    id: str
    name: str
    origin: str | None
    status: str | None
    default_attrs: dict[str, Any] | None
    case_count: int
    vertical_ids: list[str]


class SpaceTypeList(BaseModel):
    items: list[SpaceTypeItem]


@router.get("/space-types", response_model=SpaceTypeList, tags=["verticals"])
def list_space_types(vertical_id: str | None = Query(None, description="그 업종 페이지에 나온 공간만(HAS_SPACE)")) -> dict[str, Any]:
    I = idx()
    from .index import jloads

    has = {}
    for r in q("SELECT src_id, dst_id FROM kg_edge WHERE rel='HAS_SPACE'"):
        has.setdefault(r["dst_id"], set()).add(r["src_id"])
    cnt: dict[str, int] = {}
    for did, sps in I.dep_spaces.items():
        for s in sps:
            cnt[s] = cnt.get(s, 0) + 1
    items = []
    for sid, s in I.space_types.items():
        vs = sorted(has.get(sid, set()))
        if vertical_id and not (set(vs) & I.vertical_expand(vertical_id)):
            continue
        items.append({"id": sid, "name": s["name_ko"] or sid, "origin": s["origin"], "status": s["status"],
                      "default_attrs": jloads(s["default_attrs_json"], None), "case_count": cnt.get(sid, 0), "vertical_ids": vs})
    return {"items": items}


# ── 기능 서비스용(internal) ───────────────────────────────

class ObservedVertical(BaseModel):
    id: str
    name: str | None
    n: int = Field(description="이 업종으로 분류된 사례 중 그 KR 업종(사례 페이지의 사이트 업종 필터)인 사례 수")


class CaseBasis(BaseModel):
    prior: int = Field(description="KR 업종 대응(prior)과 단서로 분류된 사례 수")
    clue_only: int = Field(description="단서 사전만으로 분류된 사례 수(대응 없는 업종은 전부)")


class SegmentItem(BaseModel):
    code: str
    id: str
    name: str
    full: str
    short: str
    kb_name: str | None
    aliases: list[str]
    kr_vertical_ids: list[str] = Field(description="시드 대응(segment_mapping, 초안). `<<FILL>>` 은 빈 목록 — 사례 분류 prior 는 이것만 쓴다")
    us_vertical_ids: list[str]
    mapping_status: str | None
    case_count: int
    mapping: bool = Field(False, description="추가(03-mi 요청) — KR 업종 대응이 있는가(시드 대응 또는 사례 관측 대응)")
    mapping_basis: Literal["seed", "observed_cases"] | None = Field(
        None, description="추가 — seed = 시드 대응(kr_vertical_ids) · observed_cases = 시드는 빈칸이고 이 업종으로 분류된 사례의 사이트 업종 필터에서 "
                          "본 대응(kr_vertical_ids_observed, T5 · 사람 확인 전) · null = 둘 다 없음")
    kr_vertical_ids_observed: list[str] = Field(default_factory=list, description=(
        "추가 — 이 업종으로 분류된 사례의 KR 업종 중 2건 이상 · 절반 이상인 것(관측 대응, 계산값). 시드 대응이 있는 업종도 참고로 준다"))
    observed_kr_verticals: list[ObservedVertical] = Field(default_factory=list, description="추가 — 이 업종 사례의 KR 업종 분포(많은 순)")
    case_basis: CaseBasis | None = Field(None, description="추가 — 이 업종 사례가 어떻게 분류됐나(prior+단서 · 단서만)")


class SegmentList(BaseModel):
    items: list[SegmentItem]
    total_cases: int
    classified_cases: int
    unclassified_cases: int
    method: str
    tier: str
    needs_confirmation: list[str]


@router.get("/segments", response_model=SegmentList, tags=["internal"])
def list_segments() -> dict[str, Any]:
    """Winmate 16업종 · 업종별 사례 수(03-mi MI1I). 사례 → 업종은 규칙 초안(rule_segment_v1)."""
    return segments.list_out()


class ReqType(BaseModel):
    code: str
    label: str | None = Field(description="R01~R24 한국어 이름표 — KB 에 코드표가 없어 항상 null(데이터 공백, 지어내지 않음)")
    n: int
    examples: list[str] = Field(description="이 태그가 붙은 사례들의 요구 문장 상위 3(빈도순, 이름표 아님 · 태그끼리 겹칠 수 있음)")
    examples_specific: list[str] = Field(default_factory=list, description=(
        "추가 — 이 태그에 두드러진 요구 문장 상위 3(문장 낱말의 태그 lift 합 순, 같은 응답의 앞 태그가 쓴 문장은 뺌). 이름표 아님"))
    hint_terms: list[str] = Field(default_factory=list, description=(
        "추가 — 이 태그가 붙은 사례 요구 문장에서 전체 대비 두드러진 낱말(lift, 3건 이상) 최대 5. 이름표 아님"))


class InsightItem(BaseModel):
    kind: str
    id: str
    name: str
    n: int


class SegmentInsights(BaseModel):
    code: str
    id: str
    name: str
    full: str
    short: str
    cases: int
    case_ids: list[str]
    req_types: list[ReqType]
    products: list[InsightItem]
    solutions: list[InsightItem]
    method: str
    tier: str
    gaps: list[str]


@router.get("/segments/{code}/insights", response_model=SegmentInsights, tags=["internal"])
def get_segment_insights(code: str, top_req: int = Query(6, ge=1, le=24), top_items: int = Query(4, ge=1, le=20)) -> dict[str, Any]:
    """업종 인사이트(03-mi MI1I): 요구 유형 상위 · 많이 쓰인 제품 · 솔루션. code = FB … 또는 wm_…"""
    return segments.insights(code, top_req, top_items)


class ClassifyIn(BaseModel):
    text: str = Field(min_length=1)


class Clue(BaseModel):
    text: str
    code: str
    weight: float


class ClassifyItem(BaseModel):
    code: str
    id: str
    name: str
    kb_score: float
    clue_score: float
    clues: list[Clue]
    similar_case_ids: list[str]
    a2_match: float | None
    case_ratio: float
    has_kr_mapping: bool


class ClassifyOut(BaseModel):
    items: list[ClassifyItem]
    a2: dict[str, Any]
    similar_case_ids: list[str]
    method: str
    needs_confirmation: list[str]


@router.post("/segments/classify", response_model=ClassifyOut, tags=["internal"])
def classify_segments(body: ClassifyIn) -> dict[str, Any]:
    """업종 판별 KB 근거(03-mi §7.3): 16업종마다 kb_score · clue_score · clues · similar_case_ids."""
    return segments.classify(body.text)


@router.get("/entities/{kind}/{entity_id}", response_model=Envelope, tags=["internal"])
def get_entity(kind: Literal["family", "model", "category", "solution", "service", "vertical", "space_type", "deployment", "capability"],
               entity_id: str) -> dict[str, Any]:
    """엔티티 통합 보기(query.py `entity`, 봉투). 없으면 404."""
    env = kb().entity(kind, entity_id)
    if env.get("result") is None:
        raise not_found(kind, entity_id)
    return finalize(env)


class SpecAttr(BaseModel):
    id: str
    category_id: str
    group: str | None
    name: str | None
    norm_key: str | None
    unit: str | None
    n_values: int | None


class SpecAttrList(BaseModel):
    items: list[SpecAttr]


@router.get("/spec/attributes", response_model=SpecAttrList, tags=["internal"])
def list_spec_attributes(category_id: str | None = Query(None, description="L1 · L2 분류(없으면 전체)"),
                         q_: str | None = Query(None, alias="q", description="속성 · 그룹 이름 일부 또는 정규 키")) -> dict[str, Any]:
    """스펙 속성 사전(spec_attr_def): 분류별 그룹 · 속성 이름 · 정규 키 · 단위."""
    return {"items": specs.attributes(category_id, q_)}


class SpecTableIn(BaseModel):
    models: list[str] = Field(min_length=1, max_length=20, description="모델코드 · mdl_ · fam_(대표 모델)")
    keys: list[str] | None = Field(None, description="정규 키로 행 거르기")
    groups: list[str] | None = Field(None, description="스펙 그룹 이름으로 행 거르기")


class SpecTableModel(BaseModel):
    ref: str
    id: str
    model_code: str
    display_name: str
    display_name_basis: str
    family_id: str
    family_name: str | None
    series_label: str | None
    category_id: str | None
    has_spec: bool
    source_url: str | None
    label_en: str | None


class SpecCell(BaseModel):
    raw: str | None
    num: float | None
    num2: float | None
    unit: str | None
    spec_value_id: str
    source: str | None
    source_url: str | None


class SpecRow(BaseModel):
    group: str
    attr_name: str
    norm_key: str | None
    values: dict[str, SpecCell] = Field(description="모델코드 → 값")


class SpecDims(BaseModel):
    w: float
    h: float
    d: float | None
    unit: str
    raw: str


class SpecResolution(BaseModel):
    w: int
    h: int
    label: str | None


class SpecOption(BaseModel):
    name: str | None
    value: str | None


class PowerValue(BaseModel):
    mode: Literal["typical", "max", "on", "sleep", "standby", "off", "dpms", "yearly", "rated", "average", "unspecified"] = Field(
        description="속성 이름에서 읽은 측정 모드(`소비전력 (Typical)` → typical · `Power Consumption (Max)` → max · `정격소비전력` → rated …)")
    value: float | None = Field(description="원문의 첫 수(없음 · 문자면 null)")
    unit: str | None = Field(description="W · kW · W/㎡ · kWh/year(원문에서)")
    per_m2: bool = Field(description="㎡당 값(LED 사이니지의 Max)")
    raw: str
    attr: str = Field(description="원문 행 `그룹 › 속성`")
    spec_value_id: str


class PowerSet(BaseModel):
    typical: PowerValue | None = Field(description="`(Typical)` 행. 사이니지는 14개 모델(BEH · BEF · BED · WMF)에만 있다 — On Mode 는 typical 로 보지 않는다")
    max: PowerValue | None = Field(description="`(Max)` 행. LCD 사이니지에는 없고, LED 는 ㎡당(W/㎡) 값이다")
    values: list[PowerValue] = Field(description="소비전력 행 전부(원래 순서)")


class SpecDerived(BaseModel):
    screen_size_cm: float | None
    screen_size_inch: int | None = Field(description="00-shell §9.2 규칙. 스마트 LED 사이니지는 코드 숫자가 픽셀 피치라 쓰지 않는다(화면 크기 데이터 없음 → null)")
    dimensions_mm: SpecDims | None = Field(description="예전 값 — 첫 'AxBxC' 를 가로×높이×깊이로 본다(축 순서를 보지 않음). 새 값은 dims_mm")
    brightness_typ_nit: float | None
    weight_kg_set: float | None
    weight_kg_package: float | None
    resolution: SpecResolution | None
    option: SpecOption
    dims_mm: S.Dims | None = Field(None, description="추가 — 속성 이름의 축 순서로 읽은 본체 치수(mm), 모델 상세 dims_mm 과 같다")
    power: PowerSet | None = Field(None, description="추가(06-spec 요청 4) — 소비전력 행을 모드별로. 행이 없으면 null")
    warranty: S.Warranty | None = Field(None, description="추가(06-spec 요청 1) — 스펙 보증 행 원문. 행이 없으면 null")


class SpecTableOut(BaseModel):
    models: list[SpecTableModel]
    unresolved: list[str]
    rows: list[SpecRow]
    derived: dict[str, SpecDerived] = Field(description="모델코드 → 파생값")
    catalog_version: str | None
    notes: list[str]


@router.post("/spec/table", response_model=SpecTableOut, tags=["internal"])
def spec_table(body: SpecTableIn) -> dict[str, Any]:
    """여러 모델의 스펙을 나란히(같은 그룹 › 속성 = 한 행, 값은 원문 + 정규 수치 · 단위 · 출처) + 파생값(인치 · 치수 mm · 밝기 Typ)."""
    return specs.table(body.models, body.keys, body.groups)


class PlacementRule(BaseModel):
    id: str = Field(description="규칙 id(= 08-birdseye rule_id, 예 pr_warn_power_distance)")
    kind: str | None
    space: str | None
    category: str | None = Field(description="시드 분류 코드(signage · hvac_system_ac · *)")
    expression: str | None
    params: dict[str, Any] = Field(description="KB 원문 그대로(빈칸은 `<<FILL…>>` 문자열) — 덮어쓸 때는 param_values 를 쓰세요")
    status: str | None
    active: bool
    param_status: Literal["unfilled", "draft", "approved"] = Field(
        "unfilled", description="추가(08-birdseye 요청 3) — unfilled = 계수 빈칸이 있음(KB v1 은 모두) · draft = 다 채웠지만 승인 전 · "
                                "approved = 사람 승인(status active). approved 일 때만 엔진 기본값을 덮어쓰세요")
    param_values: dict[str, Any] = Field(default_factory=dict, description="추가 — 계수 값(빈칸은 null)")
    missing_params: list[str] = Field(default_factory=list, description="추가 — 빈칸인 계수 이름")
    param_notes: dict[str, str] = Field(default_factory=dict, description="추가 — 빈칸 안내 문구(`<<FILL: 용도별 단위면적당 부하>>` 의 설명)")
    explanation_ko: str | None = Field(None, description="추가 — 시드 설명 문구")
    category_ids: list[str] = Field(default_factory=list, description="추가 — 이 규칙 분류의 KB 분류 id(시드 categories.yaml 의 목록 URL 로 이음)")
    source_tier: str | None = Field(None, description="추가 — T5_seed_draft(시드 초안) · T4_expert(승인)")


class PlacementRuleList(BaseModel):
    items: list[PlacementRule]
    note: str


@router.get("/placement-rules", response_model=PlacementRuleList, tags=["internal"])
def list_placement_rules(category: str | None = Query(None, description="시드 코드(signage · hvac_system_ac) 또는 KB 분류 id(cat_smart-signage · "
                                                                       "top_display · cat_smart-signage__videowall) — 분류를 주면 `*` 규칙도 함께"),
                         space: str | None = Query(None, description="공간 유형 id(그 공간 규칙 + `*`)")) -> dict[str, Any]:
    """배치 · 수량 규칙(KB placement_rule). 지금은 모두 draft · 계수 빈칸 → active=false · param_status=unfilled(08-birdseye)."""
    items = specs.placement_rules(category, space)
    return {"items": items, "note": specs.placement_note(items)}
