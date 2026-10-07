#!/usr/bin/env python3
"""브라우저 탭 → 컨테이너 청크 전송 수신: tool-result 파일들에서 'WKBCHUNK:i:size:<b64>:END' 를 모아 합친다."""
import glob, json, re, sys
pat = re.compile(r"WKBCHUNK:(\d+):(\d+):([A-Za-z0-9+/=]*):END")

def chunks(files):
    got = {}
    for f in files:
        try:
            d = json.load(open(f))
        except Exception:
            continue
        for x in d if isinstance(d, list) else []:
            t = x.get("text", "") if isinstance(x, dict) else ""
            if "WKBCHUNK:" not in t:
                continue
            if t.strip().startswith('"'):
                t, _ = json.JSONDecoder().raw_decode(t.strip())
            for m in pat.finditer(t):
                got[int(m.group(1))] = (int(m.group(2)), m.group(3), f)
    return got

if __name__ == "__main__":
    g = chunks(sys.argv[1:])
    for i in sorted(g):
        size, b, f = g[i]
        print(i, size, len(b), "ok" if len(b) == size or i == max(g) else "SHORT", f[-20:])
