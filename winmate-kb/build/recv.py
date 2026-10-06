#!/usr/bin/env python3
"""브라우저 → 컨테이너 데이터 전송 수신기: 저장된 tool-result 파일에서 'WKBGZ1:<raw>:<b64len>:<b64>' 를 꺼내 풀어 저장."""
import base64, gzip, json, sys
src, dst = sys.argv[1], sys.argv[2]
d = json.load(open(src))
texts = [x.get("text", "") for x in d if isinstance(x, dict)]
t = next(x for x in texts if "WKBGZ1:" in x).strip()
if t.startswith('"'):
    t, _ = json.JSONDecoder().raw_decode(t)
t = t[t.index("WKBGZ1:"):]
tag, rawlen, blen, b64 = t.split(":", 3)
b64 = b64.strip()[: int(blen)]
raw = gzip.decompress(base64.b64decode(b64))
assert len(raw.decode("utf-8")) == int(rawlen), (len(raw), rawlen)
json.loads(raw)
open(dst, "wb").write(raw)
print(dst, len(raw), "bytes ok")
