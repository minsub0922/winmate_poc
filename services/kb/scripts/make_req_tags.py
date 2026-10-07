#!/usr/bin/env python3
"""요구 태그(R01~R24) · 제안 콘텐츠(P01~P22) 코드표 → curation/req_tags.yaml

원문: winmate-kb/raw/prior_case_studies.json 의 meta.taxonomy(이전 세션에서 사례를 구조화할 때 쓴 코드표, T5).
KB 빌드는 이 코드표를 DB 에 싣지 않는다(deployment_need 에는 코드만). kb 서비스는 이 파일로 이름표를 붙인다.

    uv run python services/kb/scripts/make_req_tags.py           # 다시 만든다
    uv run python services/kb/scripts/make_req_tags.py --check   # 파일이 원문과 같은지(다르면 종료 코드 1)

나누는 규칙(글자는 바꾸지 않는다)
- R: "R01 다지점·원격 통합 관리 (콘텐츠/기기를 본사·관리실에서 일괄)" → label "다지점·원격 통합 관리", description "콘텐츠/기기를 본사·관리실에서 일괄".
  괄호가 없으면 description 은 null.
- P: 한 문자열에 "P01 …  P02 …" 처럼 이어져 있다 → 코드마다 나눠 label 에 그대로(괄호 포함) 둔다.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "winmate-kb" / "raw" / "prior_case_studies.json"
OUT = Path(__file__).resolve().parents[1] / "src" / "winmate_kb" / "curation" / "req_tags.yaml"

R_RE = re.compile(r"^(R\d{2})\s+(.+?)(?:\s+\((.+)\))?$")
P_RE = re.compile(r"(P\d{2})\s+(.+?)(?=\s{2,}P\d{2}\s|\n|$)")

HEADER = """\
# 요구 태그(R01~R24) · 제안 콘텐츠(P01~P22) 코드표 — services/kb/scripts/make_req_tags.py 가 만든다(손으로 고치지 않는다)
# 원문: winmate-kb/raw/prior_case_studies.json meta.taxonomy — 이전 세션에서 도입사례를 LLM 으로 구조화할 때 쓴 코드표.
#   사람 검토 전(T5). KB DB 의 deployment_need(kind=req_tags · proposal_content)는 이 코드만 담는다.
"""


def build(meta: dict) -> dict:
    tax = meta["taxonomy"]
    req = []
    for line in tax["req_tags"]:
        m = R_RE.match(line.strip())
        if not m:
            raise ValueError(f"R 코드 줄을 못 읽음: {line!r}")
        req.append({"code": m.group(1), "label": m.group(2).strip(), "description": (m.group(3) or None)})
    prop = [{"code": c, "label": t.strip()} for c, t in P_RE.findall(tax["proposal_content"])]
    codes = [p["code"] for p in prop]
    if codes != [f"P{i:02d}" for i in range(1, len(codes) + 1)]:
        raise ValueError(f"P 코드 순서가 이상함: {codes}")
    return {"source": "winmate-kb/raw/prior_case_studies.json#meta.taxonomy", "source_tier": "T5_llm_extracted",
            "collected": meta.get("collected"), "status": "draft", "req_tags": req, "proposal_contents": prop}


def render(data: dict) -> str:
    return HEADER + yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=200)


def main() -> int:
    meta = json.loads(RAW.read_text(encoding="utf-8"))["meta"]
    text = render(build(meta))
    if "--check" in sys.argv:
        same = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print("같다" if same else f"다르다 — 다시 만들 것: {OUT}")
        return 0 if same else 1
    OUT.write_text(text, encoding="utf-8")
    d = build(meta)
    print(f"{OUT} — R {len(d['req_tags'])} · P {len(d['proposal_contents'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
