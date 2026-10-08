"""winmate-kb 질의 라이브러리(`winmate-kb/build/query.py` 의 `KB`)를 서비스 안에서 안전하게 쓰는 층.

- KB 는 sqlite 연결 하나를 쥐고 있고(스레드 간 공유 불가), 무거운 캐시(LSA 모델 · 벡터 · 별칭 색인 · E3 자료)를
  인스턴스 속성으로 둔다. 여기서는 **스레드마다 연결**(읽기 전용 · immutable)을 열고, 캐시는 모든 스레드가
  **한 벌을 공유**하도록 속성을 공용 저장소로 돌린다(`ThreadKB`). 캐시를 처음 만드는 구간만 잠근다.
- query.py 를 고치지 않는다(다른 세션 소유). 바꾼 동작은 하위 클래스 재정의 두 개뿐이다:
  - `A2`: 결과에 정규화 전 점수 `raw_score` 를 더한다(계산은 원본과 같다 — 10-proposal Q24 · K1 요청).
  - `E2`: 메시지 14,699개의 문장 벡터를 매번 다시 계산하지 않고 한 번만 계산해 둔다(결과는 원본과 같다).
"""
from __future__ import annotations

import collections
import importlib.util
import logging
import re
import sqlite3
import sys
import threading
import time
from pathlib import Path
from types import ModuleType
from typing import Any

from . import config

log = logging.getLogger("winmate.kb.engine")

class _Shared:
    """모든 스레드의 KB 인스턴스가 함께 쓰는 캐시."""

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self._lsa = None
        self._vec = None
        self._alias = None
        self._names = None
        self._e3 = None
        self._e2: dict[Any, Any] = {}
        # 검색 방식 상태(키워드만으로 도는 중인지) — /healthz · kb_doctor
        self.vector_failed = False
        self.vector_error: str | None = None
        self.fts_error: str | None = None
        # _cat_level 은 query.py 가 hasattr 로 검사하므로 처음엔 속성이 없어야 한다


def _shared_attr(name: str) -> property:
    def fget(self: Any) -> Any:
        return getattr(self._shared, name)          # 없으면 AttributeError → hasattr False

    def fset(self: Any, value: Any) -> None:
        setattr(self._shared, name, value)

    return property(fget, fset)


def _load_module(name: str, path: Path) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"모듈을 불러오지 못했다: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_thread_kb(Q: ModuleType) -> type:
    Base = Q.KB
    TH = Q.TH

    class ThreadKB(Base):  # type: ignore[misc, valid-type]
        _lsa = _shared_attr("_lsa")
        _vec = _shared_attr("_vec")
        _alias = _shared_attr("_alias")
        _names = _shared_attr("_names")
        _e3 = _shared_attr("_e3")
        _cat_level = _shared_attr("_cat_level")

        def __init__(self, path: Path, shared: _Shared):  # noqa: D107 — 부모 __init__ 은 부르지 않는다(캐시 초기화 방지)
            self._shared = shared
            uri = f"file:{path}?mode=ro&immutable=1"
            self.c = sqlite3.connect(uri, uri=True, check_same_thread=False)
            self.c.row_factory = sqlite3.Row

        # ── 캐시 만들기는 잠금 안에서 한 번만 ──
        # 벡터 모델(LSA joblib)을 못 읽으면(파일 없음 · 깨짐 · numpy/scikit-learn 판 차이) 예외를 올리지 않고
        # None 을 돌려 키워드 검색만으로 돈다. 이유는 `_shared.vector_error` 에 남겨 /healthz · kb_doctor 가 보여 준다.
        def lsa(self):  # type: ignore[override]
            if self._shared.vector_failed:
                return None
            if self._shared._lsa is None:
                with self._shared.lock:
                    if self._shared.vector_failed:
                        return None
                    try:
                        m = Base.lsa(self)
                    except Exception as exc:  # noqa: BLE001
                        self._shared.vector_failed = True
                        self._shared.vector_error = f"{type(exc).__name__}: {exc}"[:300]
                        log.error("벡터 모델을 읽지 못해 키워드 검색으로 돈다: %s", self._shared.vector_error)
                        return None
                    if m is None and not self._shared.vector_error:
                        self._shared.vector_error = "models/*.joblib 없음"
                    return m
            return self._shared._lsa

        def embed(self, texts):  # type: ignore[override]
            try:
                return Base.embed(self, texts)
            except Exception as exc:  # noqa: BLE001 — 모델은 읽혔지만 변환이 깨질 때(판 차이)
                with self._shared.lock:
                    self._shared.vector_failed = True
                    self._shared.vector_error = f"embed {type(exc).__name__}: {exc}"[:300]
                log.error("문장 벡터를 만들지 못해 키워드 검색으로 돈다: %s", self._shared.vector_error)
                return None

        def vectors(self, space):  # type: ignore[override]
            v = self._shared._vec
            if v is None or space not in v:
                with self._shared.lock:
                    try:
                        return Base.vectors(self, space)
                    except Exception as exc:  # noqa: BLE001 — vec_index 가 없거나 차원이 다르면 벡터 없이
                        self._shared.vector_error = f"vec_index[{space}] {type(exc).__name__}: {exc}"[:300]
                        log.error("벡터 색인을 읽지 못했다: %s", self._shared.vector_error)
                        if self._shared._vec is None:
                            self._shared._vec = {}
                        self._shared._vec[space] = ([], None)
                        return self._shared._vec[space]
            return v[space]

        def _kw_entity_sim(self, text, k):
            """벡터 없이 엔티티 유사도를 흉내 — 토큰 포괄도(entity_doc 이름 · 본문 부분 일치). D1 · A2 가 0건이 되지 않게."""
            toks = self.query_tokens(text or "")
            if not toks:
                return []
            cnt: collections.Counter = collections.Counter()
            for t in toks:
                for (ref,) in self.c.execute("SELECT kind || ':' || id FROM entity_doc WHERE (name || ' ' || text) LIKE ? LIMIT 3000", (f"%{t}%",)):
                    cnt[ref] += 1
            return [("entity:" + ref, round(0.8 * n / len(toks), 4)) for ref, n in cnt.most_common(k)]

        def vec_search(self, text, space, k=20):  # type: ignore[override]
            refs, M = self.vectors(space)
            z = self.embed([text])
            if z is None or M is None or not len(refs):
                return self._kw_entity_sim(text, k) if space == "entity" else []
            if M.shape[1] != z.shape[1]:            # 모델과 색인을 다른 빌드에서 가져왔을 때
                self._shared.vector_error = f"차원 불일치: 색인 {M.shape[1]} · 모델 {z.shape[1]} (index_kb.py 를 다시 돌린다)"
                return []
            return Base.vec_search(self, text, space, k)

        def kw_search(self, text, table="chunk_fts", col="chunk_id", k=20):  # type: ignore[override]
            try:
                return Base.kw_search(self, text, table, col, k)
            except sqlite3.Error as exc:            # FTS5 없는 sqlite · 깨진 FTS 표 → 부분 일치(like_search)만
                self._shared.fts_error = f"{table} {type(exc).__name__}: {exc}"[:300]
                return []

        def alias_index(self):  # type: ignore[override]
            if self._shared._alias is None:
                with self._shared.lock:
                    return Base.alias_index(self)
            return self._shared._alias

        def names(self):  # type: ignore[override]
            if self._shared._names is None:
                with self._shared.lock:
                    return Base.names(self)
            return self._shared._names

        def _e3_data(self):  # type: ignore[override]
            if self._shared._e3 is None:
                with self._shared.lock:
                    return Base._e3_data(self)
            return self._shared._e3

        def categories_level(self, cid):  # type: ignore[override]
            if not hasattr(self._shared, "_cat_level"):
                with self._shared.lock:
                    return Base.categories_level(self, cid)
            return self._shared._cat_level.get(cid)

        # ── A2: 원본과 같은 계산 + 정규화 전 점수(raw_score) ──
        def A2(self, text):  # type: ignore[override]
            t0 = time.time()
            score = collections.defaultdict(float)
            signals = collections.defaultdict(list)
            kr = {r["id"]: r for r in self.q("SELECT id, name_ko, parent_id FROM vertical WHERE scheme='kr_site'")}
            for vid, r in kr.items():
                if r["name_ko"] and len(r["name_ko"]) >= 2 and r["name_ko"] in text:
                    score[vid] += 1.0
                    signals[vid].append(f"업종명 '{r['name_ko']}'")
            links = self.A1(text)["result"]["links"]
            spaces = [l["id"] for l in links if l["type"] == "space_type"]
            ents = [(l["type"], l["id"]) for l in links if l["type"] in ("family", "category", "solution", "service")]
            for sp in spaces:
                vs = self.q("SELECT src_id v, count(*) n FROM kg_edge WHERE rel='HAS_SPACE' AND dst_id=? AND src_id LIKE 'kr_%' GROUP BY src_id", (sp,))
                tot = sum(v["n"] for v in vs) or 1
                for v in vs:
                    score[v["v"]] += 0.6 * v["n"] / tot
                    signals[v["v"]].append(f"공간 '{self.name('space_type', sp)}'")
            for k, i in ents:
                vs = self.q("SELECT DISTINCT src_id v FROM kg_edge WHERE rel='FEATURED_BY_SITE' AND dst_kind=? AND dst_id=? AND src_id LIKE 'kr_%'", (k, i))
                for v in vs:
                    score[v["v"]] += 0.3 / max(1, len(vs))
                    signals[v["v"]].append(f"제품·솔루션 '{self.name(k, i)}'")
            for ref, s in self.vec_search(text, "entity", 60):
                kind, i = ref.split(":", 1)[1].split(":", 1)
                if kind == "vertical" and i in kr and s > 0.1:
                    score[i] += 0.4 * s
                    signals[i].append(f"유사도 {s:.2f}")
            for vid in list(score):
                p = kr.get(vid, {}).get("parent_id")
                if p:
                    score[p] = max(score[p], score[vid])
            ranked = sorted(score.items(), key=lambda x: -x[1])
            top = ranked[0][1] if ranked else 0
            cands = [{"id": v, "name": self.name("vertical", v), "score": round(s / top, 3) if top else 0,
                      "raw_score": round(s, 4), "signals": signals[v][:6]} for v, s in ranked[:6]]
            reasons = []
            leaves = [c for c in cands if not any(kr.get(x, {}).get("parent_id") == c["id"] for x in kr)]
            if len(leaves) >= 2 and leaves[0]["score"] - leaves[1]["score"] < TH["industry_ask_margin"]:
                reasons.append("AMBIGUOUS_INDUSTRY")
            if not cands:
                reasons.append("ASK")
            return self.envelope("A2", {"top2": cands[:2], "ask": bool(reasons)},
                                 candidates=[{"id": c["id"], "score": c["score"], "raw_score": c["raw_score"],
                                              "reasons": c["signals"]} for c in cands],
                                 reasons=reasons, modes=["sql", "kg", "vec"], t0=t0)

        # ── E2: 원본과 같은 계산, 문장 벡터만 한 번 계산해 둔다 ──
        def _e2_rows(self, locale):
            key = locale or ""
            hit = self._shared._e2.get(key)
            if hit is None:
                with self._shared.lock:
                    hit = self._shared._e2.get(key)
                    if hit is None:
                        rows = self.q("SELECT id, text, level, about_kind, about_id, locale, claim_flag FROM value_prop"
                                      + (" WHERE locale=?" if locale else ""), (locale,) if locale else ())
                        Z = self.embed([r["text"] for r in rows]) if rows else None
                        hit = (rows, Z)
                        self._shared._e2[key] = hit
            return hit

        def E2(self, theme, limit=15, locale=None):  # type: ignore[override]
            import numpy as np

            t0 = time.time()
            rows, Z = self._e2_rows(locale)
            if not rows:
                return self.envelope("E2", {"messages": []}, t0=t0)
            z = self.embed([theme])
            sims = (Z @ z[0]) if Z is not None else np.zeros(len(rows))
            toks = [t for t in re.split(r"\s+", theme) if len(t) >= 2]
            scored = []
            for r, s in zip(rows, sims):
                kw = sum(1 for t in toks if t in r["text"]) / (len(toks) or 1)
                scored.append((0.6 * float(s) + 0.4 * kw, r))
            scored.sort(key=lambda x: -x[0])
            msgs = [{"id": r["id"], "text": r["text"], "level": r["level"], "about": [r["about_kind"], r["about_id"]],
                     "about_name": self.name(r["about_kind"], r["about_id"]), "score": round(s, 3), "claim_flag": r["claim_flag"]}
                    for s, r in scored[:limit]]
            prods = collections.Counter((m["about"][0], m["about"][1]) for m in msgs if m["about"][0] in ("family", "solution", "category"))
            return self.envelope("E2", {"messages": msgs, "supporting": [{"kind": k, "id": i, "name": self.name(k, i), "n": n}
                                                                      for (k, i), n in prods.most_common(8)]},
                                 modes=["vec", "kw"], t0=t0, tiers=["T2_official"])

    return ThreadKB


class Engine:
    """프로세스에 하나. `engine().kb()` 는 호출한 스레드의 KB 인스턴스(연결은 스레드마다, 캐시는 공유)."""

    def __init__(self) -> None:
        self.root = config.wkb_root()
        self.kb_dir = config.kb_dir()
        self.db_path = config.db_path()
        if not self.db_path.is_file():
            raise FileNotFoundError(f"지식 DB 가 없다: {self.db_path} (WKB_ROOT/WKB_KB 확인)")
        build = config.build_dir()
        if str(build) not in sys.path:
            sys.path.insert(0, str(build))
        self.Q = _load_module("wkb_query", build / "query.py")
        # query.py 는 import 할 때 WKB_KB 를 읽는다 → 서비스 설정 경로로 맞춘다
        self.Q.KB_DIR = self.kb_dir
        self.Q.MODEL_DIR = self.kb_dir / "models"
        self.Q.DB_PATH = self.db_path
        self.C = sys.modules.get("curation") or _load_module("curation", build / "curation.py")
        self.shared = _Shared()
        self.KBClass = _make_thread_kb(self.Q)
        self._local = threading.local()
        self.warm = False
        self.warm_seconds: float | None = None
        self.warm_error: str | None = None
        self.loaded_at = time.time()

    def kb(self) -> Any:
        inst = getattr(self._local, "kb", None)
        if inst is None:
            inst = self.KBClass(self.db_path, self.shared)
            self._local.kb = inst
        return inst

    def q(self, sql: str, args: tuple | list = ()) -> list[dict[str, Any]]:
        return self.kb().q(sql, args)

    def one(self, sql: str, args: tuple | list = ()) -> dict[str, Any] | None:
        rows = self.kb().q(sql, args)
        return rows[0] if rows else None

    def warmup(self) -> None:
        """무거운 캐시를 미리 만든다(첫 요청 지연 제거)."""
        t0 = time.time()
        try:
            k = self.kb()
            k.lsa()
            for space in ("chunk", "entity", "image"):
                k.vectors(space)
            k.alias_index()
            k.names()
            k.categories_level("top_display")
            k._e3_data()
            k._e2_rows(None)
            from . import images, index

            images.thumbs()
            index.idx()
            k.search("호텔 객실 TV")
            self.warm = True
            self.warm_seconds = round(time.time() - t0, 2)
            log.info("kb warmup done in %.1fs", self.warm_seconds)
        except Exception as exc:  # noqa: BLE001 — 데우기 실패해도 요청 때 다시 만든다
            self.warm_error = f"{type(exc).__name__}: {exc}"
            log.exception("kb warmup failed")


_engine: Engine | None = None
_engine_lock = threading.Lock()


def engine() -> Engine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = Engine()
    return _engine


def kb() -> Any:
    return engine().kb()


def q(sql: str, args: tuple | list = ()) -> list[dict[str, Any]]:
    return engine().kb().q(sql, args)


def one(sql: str, args: tuple | list = ()) -> dict[str, Any] | None:
    return engine().one(sql, args)
