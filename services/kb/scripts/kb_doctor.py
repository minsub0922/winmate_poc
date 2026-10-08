"""kb 점검 — 이미지 검색 · 유관 사례 검색 · 솔루션이 안 될 때 원인을 한 번에 찾는다(사내망 · 맥 공통, 네트워크 불필요).

    uv run python services/kb/scripts/kb_doctor.py              # 파일 · 판 · 검색 직접 점검(kb 서비스 코드로)
    uv run python services/kb/scripts/kb_doctor.py --gateway    # + 떠 있는 스택을 게이트웨이(5000)로 점검
    uv run python services/kb/scripts/kb_doctor.py --json       # 기계가 읽는 결과

끝에 '고칠 것' 목록을 낸다. 실패가 있으면 종료 코드 1.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("KB_WARMUP", "0")
os.environ.setdefault("DATA_DIR", str(ROOT / "data"))

results: list[dict] = []
fixes: list[str] = []


def check(name: str, ok: bool, detail: str = "", fix: str | None = None, warn: bool = False) -> bool:
    results.append({"check": name, "status": "ok" if ok else ("warn" if warn else "fail"), "detail": detail})
    if not ok and fix:
        fixes.append(fix)
    return ok


def files() -> Path | None:
    from winmate_kb import config

    db = config.db_path()
    if not check("지식 DB 파일", db.is_file(), str(db),
                 "지식 DB 가 없다 → 저장소 루트에서 `PATH=$PWD/.venv/bin:$PATH bash winmate-kb/build/run_all.sh && (cd winmate-kb && ../.venv/bin/python dashboard/thumb_select.py)` (git 에 없는 산출물 · run_all.sh 는 python3 를 부르므로 .venv 를 PATH 앞에 둬야 벡터 모델 판이 맞는다)"):
        return None
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        n_img = c.execute("SELECT count(*) FROM image_asset").fetchone()[0]
        n_dep = c.execute("SELECT count(*) FROM deployment").fetchone()[0]
        n_vec = c.execute("SELECT count(*) FROM vec_index").fetchone()[0]
        check("DB 행 수", n_img > 0 and n_dep > 0 and n_vec > 0, f"image_asset {n_img} · deployment {n_dep} · vec_index {n_vec}",
              "DB 가 비었거나 index_kb.py 를 안 돌렸다 → `.venv/bin/python winmate-kb/build/index_kb.py`")
        try:
            c.execute("SELECT count(*) FROM image_fts WHERE image_fts MATCH 'lobby'").fetchone()
            check("sqlite FTS5", True, sqlite3.sqlite_version)
        except sqlite3.Error as exc:
            check("sqlite FTS5", False, f"{sqlite3.sqlite_version} · {exc}",
                  "이 파이썬의 sqlite 에 FTS5 가 없다 → 키워드 검색은 부분 일치로만 돈다(동작은 함). uv 파이썬(.venv)으로 실행하는지 확인", warn=True)
    except sqlite3.Error as exc:
        check("DB 열기", False, str(exc), "DB 파일이 깨졌다 → winmate-kb 를 다시 빌드한다")
    models = sorted((config.kb_dir() / "models").glob("*.joblib"))
    check("벡터 모델 파일", bool(models), ", ".join(m.name for m in models) or "없음",
          "벡터 모델이 없다 → `cd winmate-kb && python build/index_kb.py` (없어도 키워드 검색으로는 돈다)", warn=not models)
    from winmate_kb import images

    t = images.thumbs()
    n_thumbs = len(t.by_asset)
    check("썸네일 묶음", n_thumbs > 0, f"이미지 {n_thumbs}장에 썸네일 · 묶음 {len(t.files)}개 · {config.thumbs_dir()}",
          "썸네일 묶음(winmate-kb/dashboard/build/thumbs_pack*.bin)이 없다 → git 에 있으니 `git lfs`/복사 누락을 확인한다(없으면 이미지 칸이 빈다)")
    img_dir = Path(os.environ.get("WKB_IMAGE_DIR") or (Path(os.environ["DATA_DIR"]) / "kb" / "images"))
    n_local = len(list(img_dir.glob("*.webp"))) if img_dir.is_dir() else 0
    check("로컬 이미지 사본", n_local > 0, f"{n_local}장 · {img_dir}",
          "큰 이미지 사본이 없다(썸네일만 보임) → 인터넷 되는 PC 에서 `kb_fetch_images.py --only-priority` 후 폴더째 옮긴다", warn=True)
    return db


def versions() -> None:
    import numpy
    import sklearn

    check("파이썬 · numpy · scikit-learn", True,
          f"python {platform.python_version()} ({sys.executable}) · numpy {numpy.__version__} · scikit-learn {sklearn.__version__}")
    if not sys.executable.startswith(str(ROOT / ".venv")):
        check("실행 파이썬", False, sys.executable,
              "저장소 .venv 가 아닌 파이썬으로 돌고 있다 → `uv run python …` 로 실행한다. KB 빌드(run_all.sh)도 같은 .venv 파이썬으로 해야 벡터 모델 판이 맞는다", warn=True)


def engine_checks() -> None:
    from winmate_kb.engine import engine

    eng = engine()
    k = eng.kb()
    t0 = time.time()
    m = k.lsa()
    sh = eng.shared
    check("벡터 모델 읽기", m is not None and not sh.vector_failed, sh.vector_error or f"{time.time() - t0:.1f}s",
          "벡터 모델을 못 읽는다(판 차이 · 깨진 복사) → 이 PC 에서 `.venv/bin/python winmate-kb/build/index_kb.py` 로 다시 만든다. "
          "그동안 검색은 키워드로만 돈다(결과 품질↓)", warn=True)

    def run(name: str, fn, fix: str) -> None:
        t = time.time()
        try:
            n = fn()
            check(name, n > 0, f"{n}건 · {time.time() - t:.2f}s", fix)
        except Exception as exc:  # noqa: BLE001
            check(name, False, f"{type(exc).__name__}: {exc}"[:300], fix)

    from winmate_kb import imagerank, solutions

    run("이미지 검색(로비)", lambda: len(imagerank.ranked("로비", 50)), "이미지 검색 실패 → 위 오류 · `pm2 logs kb` 를 본다")
    run("사례 검색(호텔 로비 사이니지)", lambda: len(k.D1(text="호텔 로비 사이니지", limit=10)["result"]["deployments"]), "사례 검색 실패 → 위 오류 · `pm2 logs kb`")
    run("솔루션 메시지(MagicINFO)", lambda: len(solutions.detail("magicinfo")["messages"]), "솔루션 메시지 0 → DB 의 value_prop 확인")
    run("솔루션 이미지(MagicINFO)", lambda: solutions.images(solutions.resolve("magicinfo"))["total"], "솔루션 이미지 0 → depicts · image_occurrence 확인")
    run("솔루션 사례(MagicINFO)", lambda: solutions.cases_out("magicinfo")["total"], "솔루션 사례 0 → kg_edge USES · 사례 본문 확인")


def gateway(base: str) -> None:
    def get(path: str) -> tuple[int, bytes, dict]:
        req = urllib.request.Request(base + path, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read(), {k.lower(): v for k, v in r.headers.items()}
        except urllib.error.HTTPError as e:
            return e.code, e.read(), {k.lower(): v for k, v in e.headers.items()}
        except Exception as exc:  # noqa: BLE001
            return 0, str(exc).encode(), {}

    st, body, _ = get("/api/_health")
    ok = st == 200
    kbh = {}
    if ok:
        try:
            kbh = json.loads(body)["services"]["kb"]["checks"]["kb"]
        except Exception:  # noqa: BLE001
            kbh = {}
    check("게이트웨이 · kb 상태", ok and bool(kbh.get("ok")), json.dumps(kbh, ensure_ascii=False)[:300] if ok else body[:200].decode(errors="ignore"),
          "게이트웨이 · kb 가 안 떴다 → `make up && make health`, `pm2 logs kb --lines 100`")
    if kbh.get("search_mode") == "keyword_only":
        check("kb 검색 방식", False, f"keyword_only · {kbh.get('vector_error')}",
              "kb 서비스가 벡터 모델을 못 읽어 키워드로만 찾는 중 → 이 PC 에서 index_kb.py 다시 실행 후 `pm2 restart kb`", warn=True)
    for name, path in [("GET 이미지 검색", "/api/kb/v1/images/search?" + urllib.parse.urlencode({"q": "로비", "limit": 6})),
                       ("GET 사례 검색", "/api/kb/v1/cases/search?" + urllib.parse.urlencode({"q": "로비", "limit": 3})),
                       ("GET 솔루션 이미지", "/api/kb/v1/solutions/magicinfo/images")]:
        st, body, _ = get(path)
        detail = body[:200].decode(errors="ignore")
        n = 0
        if st == 200:
            d = json.loads(body)
            n = len(d.get("items") or []) or d.get("total") or 0
        check(name, st == 200 and n > 0, f"HTTP {st} · {n}건" + ("" if st == 200 else f" · {detail}"),
              f"{name} 실패(HTTP {st}) → 응답 본문의 error.code 를 보고, 401/403 이면 AUTH_MODE · 게이트웨이 계약 캐시(`pm2 restart gateway`)를 확인")
    st, body, hd = get("/api/kb/v1/images/img_d1f741646ea0d62d/thumb")
    check("GET 썸네일", st == 200 and hd.get("content-type", "").startswith("image/"), f"HTTP {st} · {hd.get('content-type')}",
          "썸네일이 안 나온다 → 썸네일 묶음 폴더(WKB_THUMBS_DIR) 확인")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gateway", nargs="?", const="http://localhost:5000", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, str(ROOT / "services" / "kb" / "src"))
    versions()
    if files():
        engine_checks()
    if a.gateway:
        gateway(a.gateway.rstrip("/"))
    failed = [r for r in results if r["status"] == "fail"]
    if a.json:
        print(json.dumps({"results": results, "fixes": fixes, "failed": len(failed)}, ensure_ascii=False, indent=2))
    else:
        mark = {"ok": "✓", "warn": "!", "fail": "✗"}
        for r in results:
            print(f" {mark[r['status']]} {r['check']:<28} {r['detail']}")
        if fixes:
            print("\n고칠 것")
            for f in dict.fromkeys(fixes):
                print(f" - {f}")
        print(f"\n실패 {len(failed)} · 경고 {sum(1 for r in results if r['status'] == 'warn')}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
