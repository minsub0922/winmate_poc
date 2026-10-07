#!/usr/bin/env python3
"""PPT 템플릿 ↔ 디자인 보드 나란히 비교 — export 가 만든 슬라이드가 원본 보드처럼 보이는지 눈으로 확인한다.

    # 스택(make up)이 떠 있고 LibreOffice 가 있어야 한다(SOFFICE_PATH 또는 PATH 의 soffice)
    uv run python services/export/scripts/compare_boards.py MS-B CM-A OP-B
    uv run python services/export/scripts/compare_boards.py --section why          # 섹션 전체(ready 만)
    uv run python services/export/scripts/compare_boards.py --all                  # ready 전부(약 10분)

산출물: data/ppt-compare/<날짜시각>/
  - <코드>.png       왼쪽 = 원본 보드(docs/templates/_rendered/<캔버스>/<보드>.jpg), 오른쪽 = export 슬라이드
  - index.html       전체를 한 페이지로(로컬 파일로 연다)
  - report.json      코드 · 보드 · 원형(archetype) · 경고 · 사용한 슬롯 출처(board_slots | example_slots)

채울 값(슬롯)
  - services/export/src/winmate_export/templates/board_slots/<코드>.json 이 있으면 그것(보드의 예시 데이터를 슬롯 모양으로 옮긴 것).
  - 없으면 GET /templates/{code} 의 example_slots(모양만 맞춘 채움 글 — 보드 고유 요소가 안 나올 수 있다).
  보드와 같은 내용으로 비교하려면 board_slots 를 먼저 만든다(보드 .dc.html 의 renderVals 예시 값 → 슬롯 모양).
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
BASE = os.environ.get("GATEWAY_URL", "http://127.0.0.1:5000").rstrip("/") + "/api/export/v1"
SLOTS_DIR = ROOT / "services" / "export" / "src" / "winmate_export" / "templates" / "board_slots"
W, H = 960, 540


def get(path: str):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.load(r)


def post(path: str, body: dict):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def codes_from(args) -> list[str]:
    if args.codes:
        return args.codes
    out, cursor = [], None
    while True:
        q = f"/templates?status=ready&limit=100" + (f"&section={args.section}" if args.section else "") + (f"&cursor={cursor}" if cursor else "")
        page = get(q)
        out += [t["code"] for t in page["items"]]
        cursor = page.get("next_cursor")
        if not cursor:
            return out


def soffice() -> str:
    s = os.environ.get("SOFFICE_PATH") or shutil.which("soffice") or shutil.which("libreoffice")
    if not s or s == "off":
        sys.exit("LibreOffice 가 없다 — SOFFICE_PATH 를 정하거나 설치한다(docs/OPERATIONS.md)")
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("codes", nargs="*")
    ap.add_argument("--section")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    if not (args.codes or args.section or args.all):
        ap.error("코드 · --section · --all 중 하나")
    import pypdfium2 as pdfium

    out = args.out or ROOT / "data" / "ppt-compare" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    report = []
    codes = codes_from(args)
    for i in range(0, len(codes), 30):                 # 덱 하나에 30장씩
        chunk, slides, metas = codes[i:i + 30], [], []
        for code in chunk:
            d = get(f"/templates/{code}")
            f = SLOTS_DIR / f"{code}.json"
            slots, basis = (json.loads(f.read_text(encoding="utf-8")), "board_slots") if f.exists() else (d.get("example_slots") or {}, "example_slots")
            slides.append({"template_code": code, "slots": slots})
            src = d.get("source") or {}
            board = None
            if src.get("path"):
                board = ROOT / src["path"].replace("docs/templates/source/", "docs/templates/_rendered/").replace(".dc.html", ".jpg")
            metas.append({"code": code, "name": d.get("name"), "archetype": d.get("archetype"), "board": str(board.relative_to(ROOT)) if board else None, "slots": basis})
        res = post("/exports", {"format": "pptx", "filename": f"compare_{i // 30}", "document": {"title": "compare", "slides": slides}})
        warns = res.get("warnings") or []
        with tempfile.TemporaryDirectory() as tmp:
            pptx = Path(tmp) / "deck.pptx"
            with urllib.request.urlopen(BASE.rsplit("/api/", 1)[0] + res["file"]["url"], timeout=120) as r:
                pptx.write_bytes(r.read())
            subprocess.run([soffice(), "--headless", "--convert-to", "pdf", "--outdir", tmp, str(pptx)], check=True, capture_output=True, timeout=600)
            pdf = pdfium.PdfDocument(str(Path(tmp) / "deck.pdf"))
            for n, m in enumerate(metas):
                slide = pdf[n].render(scale=1.0).to_pil().convert("RGB").resize((W, H))
                left = Image.open(ROOT / m["board"]).convert("RGB").resize((W, H)) if m["board"] and (ROOT / m["board"]).exists() else Image.new("RGB", (W, H), "#eeeeee")
                img = Image.new("RGB", (W * 2 + 24, H + 30), "white")
                ImageDraw.Draw(img).text((6, 8), f"{m['code']}  archetype={m['archetype']}  slots={m['slots']}    [left: board | right: export]", fill="black")
                img.paste(left, (0, 30))
                img.paste(slide, (W + 24, 30))
                img.save(out / f"{m['code']}.png")
                m["warnings"] = [w for w in warns if w.startswith(f"{m['code']} ") or f"#{n + 1}:" in w]
                report.append(m)
        print(f"{min(i + 30, len(codes))}/{len(codes)}")
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    rows = "\n".join(f"<h3>{html.escape(m['code'])} · {html.escape(m['name'] or '')}</h3><img src='{html.escape(m['code'])}.png' width='100%'>" for m in report)
    (out / "index.html").write_text(f"<!doctype html><meta charset=utf-8><title>PPT ↔ 보드</title><body style='font-family:sans-serif;max-width:1960px'>{rows}", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
