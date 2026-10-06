#!/usr/bin/env python3
"""카세트 두 벌 비교 — 맥(Gemini)에서 기록한 것과 사내망(사내 모델)에서 기록한 것을 같은 키끼리 맞대 본다.

    uv run python services/ai-tools/scripts/cassette_compare.py data/cassettes data/cassettes-intranet
    uv run python services/ai-tools/scripts/cassette_compare.py A B --task rq.extract_form --show 5

키(파일 이름)는 정규화한 요청 해시라서, 같은 입력으로 돌린 호출끼리 짝이 맞는다.
비교: JSON 결과는 스키마 키 · 값 일치율, 텍스트는 길이와 앞부분, 이미지(t2i)는 크기만.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def flat(v: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(v, dict):
        out: dict[str, Any] = {}
        for k, x in v.items():
            out.update(flat(x, f"{prefix}.{k}" if prefix else str(k)))
        return out
    if isinstance(v, list):
        out = {f"{prefix}[#]": len(v)}
        for i, x in enumerate(v[:50]):
            out.update(flat(x, f"{prefix}[{i}]"))
        return out
    return {prefix: v}


def compare(a: dict[str, Any], b: dict[str, Any]) -> tuple[float, str]:
    ra, rb = a.get("response") or {}, b.get("response") or {}
    if ra.get("json") is not None or rb.get("json") is not None:
        fa, fb = flat(ra.get("json")), flat(rb.get("json"))
        keys = set(fa) | set(fb)
        same = sum(1 for k in keys if fa.get(k) == fb.get(k))
        shape = sum(1 for k in keys if k in fa and k in fb)
        return same / max(1, len(keys)), f"json 값 일치 {same}/{len(keys)} · 키 일치 {shape}/{len(keys)}"
    if "images" in ra:
        sa = [(i.get("width"), i.get("height")) for i in ra.get("images") or []]
        sb = [(i.get("width"), i.get("height")) for i in rb.get("images") or []]
        return (1.0 if sa == sb else 0.0), f"이미지 {sa} vs {sb}"
    ta = ra.get("content") or ra.get("summary") or ""
    tb = rb.get("content") or rb.get("summary") or ""
    return (1.0 if ta == tb else 0.0), f"글 {len(ta)}자 vs {len(tb)}자 · A:{ta[:30]!r} B:{tb[:30]!r}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--task", default="")
    ap.add_argument("--show", type=int, default=20)
    args = ap.parse_args()
    a_root, b_root = Path(args.a), Path(args.b)
    rows, missing = [], []
    for pa in sorted(a_root.rglob("*.json")):
        rel = pa.relative_to(a_root)
        if args.task and rel.parts[1:2] != (args.task,):
            continue
        pb = b_root / rel
        if not pb.is_file():
            missing.append(str(rel))
            continue
        score, note = compare(json.loads(pa.read_text(encoding="utf-8")), json.loads(pb.read_text(encoding="utf-8")))
        rows.append((score, str(rel), note))
    rows.sort()
    for score, rel, note in rows[: args.show]:
        print(f"{score:5.2f}  {rel}  {note}")
    if rows:
        avg = sum(r[0] for r in rows) / len(rows)
        print(f"\n짝 {len(rows)}개 · 평균 일치 {avg:.2f} · B 에 없는 카세트 {len(missing)}개")
    else:
        print(f"짝이 없습니다(B 에 없는 카세트 {len(missing)}개)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
