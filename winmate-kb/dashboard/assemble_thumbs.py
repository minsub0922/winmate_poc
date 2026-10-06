#!/usr/bin/env python3
"""브라우저 탭에서 넘어온 썸네일 묶음 청크(tool-result 파일들) → 바이너리 묶음 파일.

python dashboard/assemble_thumbs.py <TAG> <총 base64 길이> <FNV 체크섬> <출력 파일>
  TAG: 청크 머리표('WKBCHUNK' 또는 'WKBCHUNK2' …), 청크 형식 '<TAG>:<i>:<길이>:<base64>:END'
"""
import base64
import glob
import json
import re
import sys

tag, total, checksum, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
pat = re.compile(re.escape(tag) + r":(\d+):(\d+):([A-Za-z0-9+/=]*):END")
got = {}
for f in sorted(glob.glob("/root/.claude/projects/-home-claude/*/tool-results/*.txt") + glob.glob("/root/.claude/projects/-home-claude/*/tool-results/*.json")):
    try:
        d = json.load(open(f))
    except Exception:
        continue
    for x in d if isinstance(d, list) else []:
        t = x.get("text", "") if isinstance(x, dict) else ""
        if tag + ":" not in t:
            continue
        s = t.strip()
        if s.startswith('"'):
            s, _ = json.JSONDecoder().raw_decode(s)
        for m in pat.finditer(s):
            i, n, b = int(m.group(1)), int(m.group(2)), m.group(3)
            if len(b) == n:
                got[i] = b
n = max(got) + 1 if got else 0
missing = [i for i in range(n) if i not in got]
b64 = "".join(got[i] for i in range(n) if i in got)
print(f"chunks {len(got)} / {n}, missing {missing}, b64 {len(b64)} / {total}")
if missing or len(b64) != total:
    sys.exit(1)
raw = base64.b64decode(b64)
h = 0x811c9dc5
for byte in raw:
    h = ((h ^ byte) * 0x01000193) & 0xffffffff
print("checksum", h, "ok" if h == checksum else "MISMATCH")
if h != checksum:
    sys.exit(1)
open(out, "wb").write(raw)
print(out, len(raw), "bytes")
