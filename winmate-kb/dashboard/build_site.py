#!/usr/bin/env python3
"""대시보드 페이지 조립: src/page.html 에 engine.js·app.js 를 넣고, data/ 의 큰 파일을 조각으로 나눠 manifest 를 쓴다.

python dashboard/build_site.py [--b64]
  --b64 : 바이너리를 base64 텍스트 조각(.txt)으로 싣는다(호스트가 바이너리 형식을 받지 않을 때)
입력: dashboard/build/data/(export_data.py 산출물)
산출물: dashboard/site/index.html, dashboard/site/data/manifest.json, dashboard/site/data/*(조각) — site/ 를 그대로 정적 서버로 열 수 있다
"""
import gzip
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC, SITE = ROOT / "src", ROOT / "site"
DATA = ROOT / "build" / "data"
PARTS = SITE / "data"
B64 = "--b64" in sys.argv
LIMIT = 12 * 1024 * 1024          # 조각 크기(호스트 한도 15~16MB 보다 작게)

page = (SRC / "page.html").read_text(encoding="utf-8")
engine = (SRC / "engine.js").read_text(encoding="utf-8")
app = (SRC / "app.js").read_text(encoding="utf-8")
assert "</script" not in engine.lower() and "</script" not in app.lower()
page = page.replace("/*__ENGINE__*/", engine).replace("/*__APP__*/", app)
(SITE / "index.html").write_text(page, encoding="utf-8")

par = ROOT / "build" / "parity.json"
if par.exists():
    s = json.loads(par.read_text())["summary"]
    (DATA / "parity.json.gz").write_bytes(gzip.compress(json.dumps({"summary": s}, ensure_ascii=False).encode(), 9, mtime=0))

if PARTS.exists():
    shutil.rmtree(PARTS)
PARTS.mkdir(parents=True)
files = {}
for p in sorted(DATA.iterdir()):
    if p.name == "manifest.json" or p.is_dir():
        continue
    raw = p.read_bytes()
    binary = p.suffix in (".bin", ".gz")
    enc = "b64" if (B64 and binary) else "raw"
    body = raw
    if enc == "b64":
        import base64
        if p.suffix == ".bin":          # float16 등 바이너리: gzip 이 3% 이상 줄이면 압축(로더가 gzip 머리를 보고 푼다)
            z = gzip.compress(raw, 9, mtime=0)
            if len(z) < 0.97 * len(raw):
                body = z
        body = base64.b64encode(body)
    limit = LIMIT                       # 12 MiB(4의 배수 → base64 조각마다 따로 풀 수 있음)
    parts = []
    for i in range(0, len(body), limit):
        name = p.name + (f".p{i // limit}" if len(body) > limit else "") + (".txt" if enc == "b64" else "")
        (PARTS / name).write_bytes(body[i:i + limit])
        parts.append(name)
    files[p.name] = {"parts": parts, "size": len(raw), "enc": enc}
(PARTS / "manifest.json").write_text(json.dumps({"files": files}, ensure_ascii=False, indent=1))
total = sum((PARTS / n).stat().st_size for f in files.values() for n in f["parts"])
print(f"index.html {(SITE / 'index.html').stat().st_size / 1e6:.2f} MB · data {len(files)} files, {sum(len(f['parts']) for f in files.values())} parts, {total / 1e6:.1f} MB")
for k, v in files.items():
    print(f"  {k:24s} {v['size'] / 1e6:6.2f} MB  {len(v['parts'])} part(s) {v['enc']}")
