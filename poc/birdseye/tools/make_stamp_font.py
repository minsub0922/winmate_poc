#!/usr/bin/env python3
"""렌더 이미지에 'AI 생성 · 개략' 표시를 굽기 위한 작은 한글 글꼴(Noto Sans CJK KR Bold 부분 집합, SIL OFL 1.1).

    python tools/make_stamp_font.py /usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc
"""
import json
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTCollection

ROOT = Path(__file__).resolve().parents[1]
mat = json.loads((ROOT / "birdseye/seed/materials.json").read_text(encoding="utf-8"))
text = "AI 생성 · 개략 Winmate PoC 도입 전 후 다른 안 한 줄 요청 0123456789°×-—·:/()"
for d in (mat["cameras"], mat["lighting"]):
    text += " ".join(v["label"] for v in d.values())
chars = sorted(set(text) | set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"))
src = sys.argv[1] if len(sys.argv) > 1 else "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
coll = TTCollection(src)
font = coll.fonts[1]  # Noto Sans CJK KR
opts = subset.Options()
opts.name_IDs = ["*"]
opts.notdef_outline = True
opts.layout_features = ["*"]
sub = subset.Subsetter(opts)
sub.populate(text="".join(chars))
sub.subset(font)
# 이름 바꾸기(수정본이므로 원래 이름을 쓰지 않음)
for rec in font["name"].names:
    if rec.nameID in (1, 3, 4, 6, 16, 17):
        new = {1: "Winmate Stamp", 3: "WinmateStamp-Bold-subset", 4: "Winmate Stamp Bold", 6: "WinmateStamp-Bold",
               16: "Winmate Stamp", 17: "Bold"}[rec.nameID]
        rec.string = new
out = ROOT / "birdseye/fonts/WinmateStamp-Bold.otf"
font.save(out)
print(out, out.stat().st_size, "bytes,", len(chars), "glyphs requested")
