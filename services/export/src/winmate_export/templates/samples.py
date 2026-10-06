"""견본 칸 값 — 템플릿 칸 정의만 보고 모든 칸을 채운 예시(GET /v1/templates/{code} 의 example_slots · 테스트).

값은 자리표시 문구다(사실이 아님). 이미지 · 로고는 주어진 file_id 를 쓴다(없으면 비운다).
"""
from __future__ import annotations

from typing import Any

FILL = "스마트 매장 운영 효율을 높이는 통합 디스플레이 솔루션과 데이터 기반 고객 경험 혁신 방안"


def _text(n: int | None, i: int = 0) -> str:
    n = max(4, int(n or 24))
    return (f"{i + 1}. " + FILL * 3)[:n]


def _field(f: dict[str, Any], i: int, img: str | None) -> Any:
    t, k = f["type"], f["key"]
    if t == "number":
        return {"x": 20 + i * 15, "y": 25 + i * 12, "emotion": [-1, 1, 2, -2, 0][i % 5], "start": i * 20,
                "end": i * 20 + 30, "size": 30 + i * 10}.get(k, 10 + i)
    if t == "kpi":
        return {"value": f"{12 + i}", "unit": "%", "label": "운영 효율"}
    if t == "bullets":
        return ["첫째 항목", "둘째 항목 [확인 필요]"]
    if t == "image":
        return {"file_id": img} if img else None
    if k == "no":
        return f"{i + 1:02d}"
    return _text(f.get("max_chars"), i)


def sample_slots(t: dict[str, Any], img: str | None = None, logo: str | None = None, *, title: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for s in t["slots"]:
        typ, n, k = s["type"], s.get("count"), s["key"]
        if k == "footer":
            continue
        if typ == "card":
            items = [{f["key"]: _field(f, i, img) for f in s.get("fields", [])} for i in range(n or 1)]
            out[k] = items if n else items[0]
        elif typ in ("text", "caption"):
            if n:
                out[k] = [_text(s.get("max_chars"), i) for i in range(n)]
            elif k == "title":
                out[k] = title if title is not None else _text(s.get("max_chars"))
            elif k == "no":
                out[k] = "01"
            else:
                out[k] = _text(s.get("max_chars"))
        elif typ == "number":
            out[k] = [str(10 + i) for i in range(n)] if n else "42"
        elif typ == "bullets":
            out[k] = [_text(30, i) for i in range(n or 3)]
        elif typ == "kpi":
            def mk(i: int) -> dict[str, Any]:
                return {"value": f"{20 + i}", "unit": "%", "label": "체류 시간", "sub": "전년 대비", "bar": 50 + i * 10}
            out[k] = [mk(i) for i in range(n)] if n else mk(0)
        elif typ == "image":
            if img:
                out[k] = [{"file_id": img} for _ in range(n)] if n else {"file_id": img}
        elif typ == "logo":
            if logo:
                out[k] = logo
        elif typ == "source":
            out[k] = [{"label": "출처 이름", "url": "https://example.com"}]
        elif typ == "table":
            out[k] = {"columns": ["구분", "현재", "제안"], "rows": [["항목 1", "120", "150 [확인 필요]"], ["항목 2", "수동", "자동"]]}
        elif typ == "chart":
            out[k] = {"type": "bar", "categories": ["2023", "2024", "2025"], "series": [{"name": "시장", "values": [10, 14, 19]}],
                      "unit": ""}
    return out
