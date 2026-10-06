"""사내 카탈로그 어댑터(06-spec §4.15.1).

- `kb`(v1 기본): kb 서비스 계약(`/v1/meta` · `/v1/spec/table` · `/v1/models/{code}` · `/v1/entities/family/{id}` ·
  `/v1/products/search` · `/v1/models?family_id=` · `/v1/models/{code}/lifecycle` · `/v1/query/{A1|A3|C2|C4}`)만 쓴다.
- `fixture`(테스트 CAT_FIX): kb 값 위에 JSON 픽스처를 덮는다(버전 · 값 추가/삭제 · KB 에 없는 모델 · 보증 · 생애주기).

모델 스펙(dict)
  {model_code, kb_model_id, family_id, display_name, label_en, family_label_en, series_label, series_code, family_name,
   category_id, source_url, release_ym, size_inch,
   attrs: {"그룹 › 속성": {raw, num, num2, unit, id, norm_key}}, derived: {...}, solutions: [...], provides: [...],
   sale_status_code, sold_out, warranty_catalog?: {years, ref}}
값은 KB 원문(value_raw)과 KB 가 원문에서 계산한 파생값뿐이다 — 모델(LLM)은 값을 만들지 않는다(§7.11).
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError

from . import config
from .rules.fmt import category_en, family_en_from_label, first_number, inch_from_cm, inch_from_code, series_code

log = logging.getLogger("winmate.spec.catalog")

_MAX_CACHE = 800


def _kb() -> ServiceClient:
    return ServiceClient("kb", timeout=60)


def strip_ref(token: str) -> str:
    t = token.strip()
    for p in ("kb:model:", "kb:family:"):
        if t.startswith(p):
            return t[len(p):]
    return t


class KbCatalog:
    adapter = "kb"

    def __init__(self) -> None:
        self._meta: tuple[float, dict[str, Any]] | None = None
        self._specs: dict[tuple[str, str], dict[str, Any]] = {}
        self._resolve: dict[tuple[str, str], str | None] = {}
        self._family: dict[tuple[str, str], dict[str, Any]] = {}
        self._fam_models: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self._c2: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    # ── 버전 ───────────────────────────────────────────
    async def meta(self) -> dict[str, Any]:
        if self._meta and time.time() - self._meta[0] < 60:
            return self._meta[1]
        try:
            m = await _kb().get("/v1/meta")
        except ApiError as exc:
            if self._meta:
                return self._meta[1]
            raise ApiError(503, "UPSTREAM_UNAVAILABLE", "사내 카탈로그(kb)에 연결하지 못했어요. 잠시 뒤 다시 시도해 주세요.",
                           {"upstream": "kb", "code": exc.code}) from exc
        version = m.get("catalog_version") or (m.get("products_fetched_at") or "")[:7] or "unknown"
        out = {"version": version, "fetched_at": m.get("products_fetched_at"), "label": "사내 카탈로그",
               "source_label": "사내 제품 카탈로그", "adapter": self.adapter}
        self._meta = (time.time(), out)
        return out

    async def version(self) -> str:
        return (await self.meta())["version"]

    def _trim(self) -> None:
        if len(self._specs) > _MAX_CACHE:
            for k in list(self._specs)[: len(self._specs) // 2]:
                self._specs.pop(k, None)

    # ── 해소 ───────────────────────────────────────────
    async def resolve(self, token: str) -> str | None:
        """ref · 모델코드 · mdl_ · fam_(대표 모델) · 표시명 → 모델코드. 못 찾으면 None."""
        t = strip_ref(token)
        if not t or t.startswith("custom:"):
            return None
        ver = await self.version()
        key = (ver, t.upper())
        if key in self._resolve:
            return self._resolve[key]
        code: str | None = None
        try:
            r = await _kb().post("/v1/spec/table", json={"models": [t]})
            if r.get("models"):
                code = r["models"][0]["model_code"]
        except ApiError as exc:
            if exc.status >= 500:
                raise
        if code is None and re.fullmatch(r"[A-Za-z]{2}\d{2,3}[A-Za-z]{1,2}", t):
            try:
                s = await _kb().get("/v1/products/search", params={"q": t, "limit": 5, "kinds": "model"})
                for it in s.get("items") or []:
                    if (it.get("display_name") or "").upper() == t.upper() and it.get("model_code"):
                        code = it["model_code"]
                        break
            except ApiError as exc:
                if exc.status >= 500:
                    raise
        self._resolve[key] = code
        return code

    # ── 스펙 ───────────────────────────────────────────
    async def specs(self, codes: list[str]) -> dict[str, dict[str, Any]]:
        ver = await self.version()
        want = [c for c in dict.fromkeys(codes) if c and (ver, c) not in self._specs]
        if want:
            await self._fetch(ver, want)
        return {c: self._specs[(ver, c)] for c in codes if (ver, c) in self._specs}

    async def spec(self, code: str) -> dict[str, Any] | None:
        return (await self.specs([code])).get(code)

    async def _fetch(self, ver: str, codes: list[str]) -> None:
        kb = _kb()
        tables = []
        for i in range(0, len(codes), 20):
            tables.append(await kb.post("/v1/spec/table", json={"models": codes[i:i + 20]}))
        models: dict[str, dict[str, Any]] = {}
        for tb in tables:
            for m in tb.get("models") or []:
                code = m["model_code"]
                fam_en = family_en_from_label(m.get("label_en"), m.get("display_name")) or category_en(m.get("category_id"))
                models[code] = {
                    "model_code": code, "kb_model_id": m.get("id"), "family_id": m.get("family_id"),
                    "display_name": m.get("display_name") or code, "label_en": m.get("label_en"),
                    "family_label_en": fam_en, "series_label": m.get("series_label"), "series_code": series_code(m.get("series_label")),
                    "family_name": m.get("family_name"), "category_id": m.get("category_id"), "source_url": m.get("source_url"),
                    "has_spec": m.get("has_spec", True), "attrs": {}, "derived": (tb.get("derived") or {}).get(code) or {},
                    "solutions": [], "provides": [], "sale_status_code": None, "sold_out": False, "in_catalog": True,
                }
            for row in tb.get("rows") or []:
                key = f"{row['group']} › {row['attr_name']}"
                for code, cell in (row.get("values") or {}).items():
                    if code in models and cell and cell.get("raw") is not None:
                        models[code]["attrs"][key] = {"raw": cell.get("raw"), "num": cell.get("num"), "num2": cell.get("num2"),
                                                      "unit": cell.get("unit"), "id": cell.get("spec_value_id"),
                                                      "norm_key": row.get("norm_key")}
        sem = asyncio.Semaphore(6)

        async def detail(code: str) -> None:
            if "/" in code:      # 경로에 넣을 수 없는 모델코드(LED 캐비닛 등) — 상세 없이 표 값만
                return
            async with sem:
                try:
                    d = await kb.get(f"/v1/models/{code}")
                except ApiError as exc:
                    log.warning("kb model detail %s: %s", code, exc)
                    return
            m = models[code]
            m["solutions"] = [{"id": s.get("id"), "kb_id": s.get("kb_id"), "name": s.get("name"),
                               "evidence_text": (s.get("evidence") or {}).get("text"), "source_url": (s.get("evidence") or {}).get("source_url")}
                              for s in d.get("supported_solutions") or []]
            m["sale_status_code"] = d.get("sale_status_code")
            m["sold_out"] = (d.get("sold_out_flag") or "").upper() == "Y"
            m["label_en"] = m.get("label_en") or d.get("label_en")
            for f in d.get("facts") or []:
                if f.get("label") == "출시":
                    m["release_ym"] = f.get("value")

        await asyncio.gather(*(detail(c) for c in models))
        fams = {m["family_id"] for m in models.values() if m.get("family_id")}
        for fid in fams:
            fe = await self.family(fid)
            for m in models.values():
                if m.get("family_id") == fid:
                    m["provides"] = fe.get("provides") or []
                    m["series_code"] = m.get("series_code") or fe.get("series_code")
        for code, m in models.items():
            m["size_inch"] = (m["derived"].get("screen_size_inch") or inch_from_code(code)
                              or inch_from_cm((m["attrs"].get("디스플레이 › 대각선 사이즈 (cm)") or {}).get("num")))
            rel = (m["attrs"].get("상품 기본정보 › 동일모델의 출시년월") or {})
            m["release_num"] = (rel.get("num") or 0) * 100 + (rel.get("num2") or 0)
            self._specs[(ver, code)] = m
        self._trim()

    async def family(self, family_id: str) -> dict[str, Any]:
        ver = await self.version()
        key = (ver, family_id)
        if key in self._family:
            return self._family[key]
        out: dict[str, Any] = {"id": family_id, "provides": [], "models": [], "series_code": None, "name": None}
        try:
            env = await _kb().get(f"/v1/entities/family/{family_id}")
            r = env.get("result") or {}
            row = r.get("row") or {}
            mm = row.get("marketing_model")
            out.update({
                "provides": [{"capability_id": p.get("capability_id"), "evidence": p.get("evidence")} for p in r.get("provides") or []],
                "models": [{"model_code": x.get("model_code"), "is_family_default": bool(x.get("is_family_default")),
                            "option_value": x.get("option_value")} for x in r.get("models") or []],
                "series_code": mm if mm and re.fullmatch(r"[A-Za-z0-9-]{2,8}", mm) else None,
                "name": row.get("name_ko"), "category_id": row.get("category_id"), "default_model_code": row.get("default_model_code"),
            })
        except ApiError as exc:
            log.warning("kb family %s: %s", family_id, exc)
        self._family[key] = out
        return out

    async def family_models(self, family_id: str) -> list[dict[str, Any]]:
        """제품군의 모델 전부(모델코드 · 표시명 · 크기 · 대표 여부)."""
        ver = await self.version()
        key = (ver, family_id)
        if key in self._fam_models:
            return self._fam_models[key]
        out = []
        try:
            r = await _kb().get("/v1/models", params={"family_id": family_id, "limit": 100})
            for it in r.get("items") or []:
                size = (it.get("values") or {}).get("size") or {}
                out.append({"model_code": it["model_code"], "display_name": it.get("display_name") or it["model_code"],
                            "size_inch": size.get("inch") or inch_from_code(it["model_code"]),
                            "is_family_default": bool(it.get("is_family_default")), "kb_model_id": it.get("id")})
        except ApiError as exc:
            log.warning("kb models of %s: %s", family_id, exc)
        self._fam_models[key] = out
        return out

    async def search(self, q: str, limit: int = 5, kinds: str = "model,family") -> list[dict[str, Any]]:
        r = await _kb().get("/v1/products/search", params={"q": q, "limit": limit, "kinds": kinds})
        return r.get("items") or []

    async def lifecycle_kb(self, code_or_name: str) -> dict[str, Any]:
        if "/" in strip_ref(code_or_name):
            return {"status": "not_in_catalog", "model_code": None}
        try:
            return await _kb().get(f"/v1/models/{strip_ref(code_or_name)}/lifecycle")
        except ApiError:
            return {"status": "not_in_catalog", "model_code": None}

    # ── 질의 패턴 ──────────────────────────────────────
    async def c2(self, **body: Any) -> dict[str, Any]:
        body = {k: v for k, v in body.items() if v not in (None, [], "")}
        key = json.dumps(body, sort_keys=True, ensure_ascii=False)
        hit = self._c2.get(key)
        if hit and time.time() - hit[0] < 600:
            return hit[1]
        r = await _kb().post("/v1/query/C2", json=body)
        self._c2[key] = (time.time(), r)
        return r

    async def c4(self, family_id: str, capabilities: list[str] | None = None, category: str | None = None) -> dict[str, Any]:
        return await _kb().post("/v1/query/C4", json={"family_id": family_id, "capabilities": capabilities or [], "category": category})

    async def a1(self, text: str) -> dict[str, Any]:
        return await _kb().post("/v1/query/A1", json={"text": text})

    async def a3(self, items: list[dict[str, str]]) -> dict[str, Any]:
        return await _kb().post("/v1/query/A3", json={"items": items})

    # ── 보증(§4.15.8) ──────────────────────────────────
    def warranty_policy(self, spec: dict[str, Any]) -> dict[str, Any] | None:
        cfg = config.warranty_config()
        for e in cfg.get("entries") or []:
            mt = e.get("match") or {}
            if (mt.get("model_code") and mt["model_code"] == spec.get("model_code")) or \
               (mt.get("series") and mt["series"] == spec.get("series_code")) or \
               (mt.get("category") and mt["category"] == spec.get("category_id")):
                return {"years": e.get("years"), "label": cfg.get("source_label") or "국내 보증 정책 문서",
                        "file_id": cfg.get("file_id"), "as_of": cfg.get("as_of"), "ref": cfg.get("file_id") or "warranty.yaml"}
        return None

    def internal_lifecycle(self, code_or_name: str) -> dict[str, Any] | None:
        return None


class FixtureCatalog(KbCatalog):
    """테스트 CAT_FIX — kb 값 위에 픽스처를 덮는다(06-spec §9 전제)."""

    adapter = "fixture"

    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = Path(path)

    def _fx(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}

    async def meta(self) -> dict[str, Any]:
        fx = self._fx()
        return {"version": fx.get("version", "fixture"), "fetched_at": fx.get("detected_at"), "label": "사내 카탈로그",
                "source_label": "사내 제품 카탈로그", "adapter": self.adapter}

    def _fixture_model(self, token: str) -> tuple[str, dict[str, Any]] | None:
        t = strip_ref(token).upper()
        for code, m in (self._fx().get("models") or {}).items():
            if code.upper() == t or (m.get("display_name") or "").upper() == t or (m.get("kb_model_id") or "").upper() == t:
                return code, m
        return None

    async def resolve(self, token: str) -> str | None:
        hit = self._fixture_model(token)
        if hit and (hit[1].get("base") or hit[1].get("standalone")):
            return hit[0]
        return await super().resolve(token)

    async def specs(self, codes: list[str]) -> dict[str, dict[str, Any]]:
        fx_models = self._fx().get("models") or {}
        base_codes = []
        for c in codes:
            m = fx_models.get(c) or {}
            base_codes.append(m.get("base") or c)
        ver = await self.version()
        base = await super().specs([b for b in base_codes if b])
        out: dict[str, dict[str, Any]] = {}
        for c, b in zip(codes, base_codes):
            src = base.get(b)
            fm = fx_models.get(c)
            if src is None and not fm:
                continue
            s = copy.deepcopy(src) if src else {"attrs": {}, "derived": {}, "solutions": [], "provides": []}
            if fm:
                for k in ("display_name", "label_en", "family_label_en", "series_code", "family_id", "category_id", "kb_model_id"):
                    if fm.get(k):
                        s[k] = fm[k]
                if fm.get("base"):
                    s["model_code"] = c
                    s["kb_model_id"] = fm.get("kb_model_id")
                    s["in_catalog"] = bool(fm.get("in_catalog", False))
                for k in fm.get("remove") or []:
                    s["attrs"].pop(k, None)
                for k, v in (fm.get("set") or {}).items():
                    g, _, n = k.partition(" › ")
                    s["attrs"][k] = {"raw": v, "num": first_number(v), "num2": None, "unit": None, "id": f"fx:{c}:{n}", "norm_key": None}
                    if k == "디스플레이 › 밝기 (Typ)":
                        s["derived"]["brightness_typ_nit"] = first_number(v)
                for k, v in (fm.get("derived") or {}).items():
                    s["derived"][k] = v
                if fm.get("warranty_years") is not None:
                    s["warranty_catalog"] = {"years": fm["warranty_years"], "ref": f"fx:{c}:warranty", "quote": f"보증 {fm['warranty_years']}년"}
                if fm.get("solutions") is not None:
                    s["solutions"] = fm["solutions"]
            s.setdefault("model_code", c)
            s.setdefault("display_name", c)
            s["size_inch"] = s.get("size_inch") or (s.get("derived") or {}).get("screen_size_inch") or inch_from_code(c)
            out[c] = s
        _ = ver
        return out

    def warranty_policy(self, spec: dict[str, Any]) -> dict[str, Any] | None:
        fx = self._fx()
        pol = (fx.get("policy_warranty") or {}).get(spec.get("model_code") or "")
        if pol is None:
            return super().warranty_policy(spec)
        return {"years": pol, "label": fx.get("policy_label") or "국내 보증 정책 문서", "file_id": fx.get("policy_file_id"),
                "as_of": fx.get("policy_as_of"), "ref": fx.get("policy_file_id") or "policy:fixture"}

    def internal_lifecycle(self, code_or_name: str) -> dict[str, Any] | None:
        hit = self._fixture_model(code_or_name)
        if hit and hit[1].get("lifecycle"):
            return {**hit[1]["lifecycle"], "model_code": hit[0]}
        return None

    async def lifecycle_kb(self, code_or_name: str) -> dict[str, Any]:
        hit = self._fixture_model(code_or_name)
        if hit and hit[1].get("base"):
            return {"status": "not_in_catalog" if not hit[1].get("in_catalog") else "on_sale", "model_code": hit[0]}
        return await super().lifecycle_kb(code_or_name)


_catalog: KbCatalog | None = None
_catalog_key: tuple[str, str | None] | None = None


def catalog() -> KbCatalog:
    global _catalog, _catalog_key
    key = (config.catalog_adapter_name(), config.catalog_fixture_path())
    if _catalog is None or _catalog_key != key:
        _catalog = FixtureCatalog(key[1]) if key[0] == "fixture" and key[1] else KbCatalog()
        _catalog_key = key
    return _catalog


def reset_catalog() -> None:
    """테스트용."""
    global _catalog, _catalog_key
    _catalog = None
    _catalog_key = None
