"""참고 사례 — winmate-kb 의 공간 배치 이미지(A·D 등급)를 공간 유형 × 제품군으로 찾는다(읽기 전용 SQL, numpy 불필요).

폴백 순서: 공간+제품 → 공간만 → 제품이 나온 설치·사례 사진. 결과마다 원문 링크와 캡션 규칙을 붙인다.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

GRADE = {"A": 0, "D": 1, "A?C": 2, "C": 3, "E": 4}


def _conn(kb_dir: Path):
    c = sqlite3.connect(f"file:{kb_dir / 'winmate_kb.sqlite'}?mode=ro", uri=True, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def _rows(c, where: str, args) -> list[dict]:
    rows = c.execute(f"""SELECT a.id, a.url, a.grade_hint, a.rights, o.alt, o.caption, o.page_type, d.url page_url, d.title,
                                o.context_space_type_id sp, o.context_entities_json ents
                         FROM image_asset a JOIN image_occurrence o ON o.asset_id=a.id JOIN source_document d ON d.id=o.document_id
                         WHERE {where} LIMIT 600""", args).fetchall()
    best: dict[str, dict] = {}
    for r in rows:
        r = dict(r)
        k = r["id"]
        if k not in best or GRADE.get(r["grade_hint"], 9) < GRADE.get(best[k]["grade_hint"], 9):
            best[k] = r
    return list(best.values())


def reference_images(kb_dir: Path | None, space_type: str, family_ids: list[str], category_ids: list[str], limit: int = 3) -> dict:
    if not kb_dir or not (Path(kb_dir) / "winmate_kb.sqlite").exists():
        return {"available": False, "images": [], "level": None, "note": "winmate-kb 연결 안 됨(WKB_KB)"}
    c = _conn(Path(kb_dir))
    try:
        targets = set(family_ids) | set(category_ids)

        def score(r):
            ents = {e[1] for e in json.loads(r.get("ents") or "[]") if isinstance(e, list) and len(e) > 1}
            s = 0.0
            if ents & set(family_ids):
                s += 3
            elif ents & set(category_ids):
                s += 1.5
            s += {"A": 1.5, "D": 1.2, "A?C": 0.6}.get(r["grade_hint"], 0)
            if r.get("rights") == "customer_case":
                s += 0.5
            return s

        levels = []
        sp_rows = _rows(c, "o.context_space_type_id=? AND a.grade_hint IN ('A','A?C','D')", (space_type,))
        with_prod = [r for r in sp_rows if score(r) >= 3]
        levels.append(("공간+제품", with_prod))
        levels.append(("공간만", sp_rows))
        if targets:
            ph = ",".join("?" * len(targets))
            dep = _rows(c, f"a.id IN (SELECT asset_id FROM depicts WHERE target_id IN ({ph})) AND a.grade_hint IN ('A','D')", tuple(targets))
            levels.append(("제품 설치·사례", dep))
        for name, rows in levels:
            if rows:
                rows.sort(key=lambda r: -score(r))
                out = []
                seen_pages = set()
                for r in rows:
                    if r["page_url"] in seen_pages and len(rows) > limit:
                        continue
                    seen_pages.add(r["page_url"])
                    out.append({"asset_id": r["id"], "url": r["url"], "page_url": r["page_url"], "title": r["title"],
                                "alt": (r.get("alt") or r.get("caption") or "")[:120], "grade": r["grade_hint"],
                                "caption_rule": "도입사례 사진" if r.get("rights") == "customer_case" else "예시 사진(삼성 공식 이미지)",
                                "space": r.get("sp")})
                    if len(out) >= limit:
                        break
                return {"available": True, "images": out, "level": name,
                        "note": None if name == "공간+제품" else f"폴백: {name}"}
        return {"available": True, "images": [], "level": None, "note": "맞는 이미지 없음"}
    finally:
        c.close()
