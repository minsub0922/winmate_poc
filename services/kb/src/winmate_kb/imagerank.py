"""이미지 검색 재정렬 — 글자 일치만으로는 '로비' 가 업종 페이지의 화면 예시 그림을 먼저 준다.

질의에서 공간 · 업종 · 제품/솔루션을 뽑아(A1) 다음 신호를 더한다.
  점수 = 0.45 × 글자 순위 + 0.25 × 공간 일치 + 0.12 × 업종 일치 + 0.2 × 대상(제품군 · 분류 · 솔루션) 등장
         + 0.08 × 장면 사진(등급 A) + 0.05 × 공간이 있는 도입사례 사진
후보도 넓힌다: 글자로 못 찾았어도 공간 × 분류 배치 이미지(G1) · 대상이 나오는 이미지(G2) 를 붙인다(공간+제품 이미지 우선).
"""
from __future__ import annotations

from typing import Any

from .engine import kb

W_TEXT, W_SPACE, W_VERT, W_TARGET, W_SCENE, W_CASE = 0.45, 0.25, 0.12, 0.2, 0.08, 0.05


def _links(text: str) -> tuple[set[str], set[str], list[tuple[str, str]]]:
    k = kb()
    spaces: set[str] = set()
    verts: set[str] = set()
    targets: list[tuple[str, str]] = []
    for l in k.A1(text)["result"].get("links") or []:
        t, i = l.get("type"), l.get("id")
        if not i:
            continue
        if t == "space_type":
            spaces.add(i)
        elif t == "vertical":
            verts.add(i)
        elif t == "model":
            r = k.c.execute("SELECT family_id FROM product_model WHERE id=?", (i,)).fetchone()
            if r and r[0] and ("family", r[0]) not in targets:
                targets.append(("family", r[0]))
        elif t in ("family", "category", "solution", "service") and (t, i) not in targets:
            targets.append((t, i))
    return spaces, verts, targets


def ranked(text: str, limit: int = 400) -> list[dict[str, Any]]:
    """→ 이미지 행(query.py `_img_rows` 모양) 목록, 재정렬 · 확장 후."""
    k = kb()
    base = k.image_search(text, limit=limit)["result"].get("images") or []
    spaces, verts, targets = _links(text)
    if not (spaces or verts or targets):
        return base
    rows: dict[str, dict[str, Any]] = {}
    text_rank: dict[str, float] = {}
    n = max(len(base), 1)
    for i, r in enumerate(base):
        rows.setdefault(r["id"], r)
        text_rank.setdefault(r["id"], 1.0 - i / n)
    # 확장: 공간 × 분류 배치(G1), 대상 등장(G2)
    cats = [i for t, i in targets if t == "category"]
    for sp in list(spaces)[:2]:
        for r in (k.G1(sp, cats[0] if cats else None, None, limit=60)["result"].get("images") or []):
            rows.setdefault(r["id"], r)
    target_ids: set[str] = set()
    for t, i in targets[:3]:
        target_ids.add(i)
        if t == "category":
            continue
        for r in (k.G2(t, i, limit=60)["result"].get("images") or []):
            rows.setdefault(r["id"], r)
    depicted: dict[str, set[str]] = {}
    if target_ids:
        ids = list(rows)
        for j in range(0, len(ids), 900):
            part = ids[j:j + 900]
            ph = ",".join("?" * len(part))
            for aid, tid in k.c.execute(f"SELECT asset_id, target_id FROM depicts WHERE asset_id IN ({ph})", part):
                depicted.setdefault(aid, set()).add(tid)
    scored = []
    for aid, r in rows.items():
        ents = {e[1] for e in r.get("entities") or []} | depicted.get(aid, set())
        s = W_TEXT * text_rank.get(aid, 0.0)
        if spaces and r.get("sp") in spaces:
            s += W_SPACE
        if verts and r.get("v") in verts:
            s += W_VERT
        if target_ids and ents & target_ids:
            s += W_TARGET
        if r.get("grade_hint") == "A":
            s += W_SCENE
        if r.get("rights") == "customer_case" and r.get("sp"):
            s += W_CASE
        scored.append((s, text_rank.get(aid, 0.0), aid))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [rows[a] for _, _, a in scored[:limit]]
