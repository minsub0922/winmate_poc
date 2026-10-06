#!/usr/bin/env python3
"""간단한 SQL 실행기(sqlite3 CLI 대용): python build/sql.py "SELECT ..." [--db path]"""
import os, sqlite3, sys
from pathlib import Path
db = Path(os.environ.get("WKB_KB", Path(__file__).resolve().parents[1] / "kb")) / "winmate_kb.sqlite"
args = sys.argv[1:]
if "--db" in args:
    i = args.index("--db"); db = Path(args[i + 1]); del args[i:i + 2]
c = sqlite3.connect(db)
for q in ";".join(args).split(";"):
    q = q.strip()
    if not q:
        continue
    cur = c.execute(q)
    if cur.description:
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        w = [min(40, max(len(str(x)) for x in [col] + [r[k] for r in rows])) for k, col in enumerate(cols)]
        print(" | ".join(str(col)[:40].ljust(w[k]) for k, col in enumerate(cols)))
        for r in rows:
            print(" | ".join(str(v)[:40].ljust(w[k]) for k, v in enumerate(r)))
        print(f"({len(rows)} rows)\n")
