#!/usr/bin/env python3
"""두 지식 DB 를 표 단위로 비교한다(재현 확인용) — 파일 해시가 다를 때 어디가 다른지 본다.

    python build/compare_db.py <기준 DB> <새 DB>          # 표마다 행 수 · 내용 해시 · 행 순서
    python build/compare_db.py <기준 DB> <새 DB> --skip-qa  # qa.py 를 아직 안 돌렸으면 dr_metric · scenario_status · kb_meta 를 뺀다

- 내용 해시: 모든 컬럼을 정렬한 행들의 SHA-256(행 순서와 무관). 순서: rowid 순서까지 같은지.
- FTS5 가상 표(chunk_fts · entity_fts · image_fts)도 SELECT 로 같은지 본다.
- 종료 코드: 모두 같으면 0, 하나라도 다르면 1.
"""
from __future__ import annotations

import hashlib
import sqlite3
import sys

QA_TABLES = {"dr_metric", "scenario_status", "kb_meta"}


def tables(c: sqlite3.Connection) -> list[str]:
    rows = c.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    out = []
    for name, sql in rows:
        if "fts" in name and not (sql or "").upper().startswith("CREATE VIRTUAL"):
            continue          # FTS5 그림자 표(_data · _idx · _content …)는 가상 표 비교로 대신한다
        out.append(name)
    return out


def digest(c: sqlite3.Connection, t: str) -> tuple[int, str, str]:
    rows = [repr(r) for r in c.execute(f'SELECT * FROM "{t}"')]
    ordered = hashlib.sha256("\n".join(rows).encode()).hexdigest()[:12]
    content = hashlib.sha256("\n".join(sorted(rows)).encode()).hexdigest()[:12]
    return len(rows), content, ordered


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        return 2
    skip = QA_TABLES if "--skip-qa" in sys.argv else set()
    a, b = sqlite3.connect(args[0]), sqlite3.connect(args[1])
    ta, tb = set(tables(a)), set(tables(b))
    bad = 0
    for t in sorted(ta | tb):
        if t in skip:
            continue
        if t not in ta or t not in tb:
            print(f"ONLY {'A' if t in ta else 'B':4s} {t}")
            bad += 1
            continue
        na, ca, oa = digest(a, t)
        nb, cb, ob = digest(b, t)
        if ca != cb:
            state = "DIFF"
        elif oa != ob:
            state = "ORDER"   # 내용은 같고 행 순서만 다름
        else:
            state = "OK"
        bad += state == "DIFF"
        print(f"{state:5s} {t:26s} {na:>8} {nb:>8}")
    print("다른 표:", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
