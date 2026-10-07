"""I2T(이미지 → 텍스트)와 '말로 수정' — 도면 인식(BP1D) · 현장 사진 읽기(BR1P) · 2D 배치 말로 고치기(BP3).

모델이 없거나 실패하면 지어내지 않는다: 도면·사진은 '못 읽음'으로 돌려주고, 말로 수정은 정해진 문장 패턴만 규칙으로 처리한다.
"""
from __future__ import annotations

import re

from .analyze3d import LIB
from .llm import ModelClient

WALL_ENUM = ["front", "back", "left", "right"]

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "scale_text": {"type": "string", "description": "도면에서 읽은 축척 표기(없으면 빈 문자열)"},
        "width_mm": {"type": "number", "description": "정면(입구·도로 쪽) 벽 방향 안쪽 치수"},
        "depth_mm": {"type": "number", "description": "정면에서 안쪽으로의 치수"},
        "height_mm": {"type": "number", "description": "읽을 수 있을 때만"},
        "openings": {"type": "array", "items": {"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["window", "entrance", "door"]},
            "wall": {"type": "string", "enum": WALL_ENUM},
            "start_mm": {"type": "number", "description": "벽 시작점(정면·후면은 왼쪽 끝, 측벽은 정면 끝)에서 개구부 시작까지"},
            "length_mm": {"type": "number"},
            "label": {"type": "string"}}, "required": ["kind", "wall", "start_mm", "length_mm"]}},
        "pillars": {"type": "array", "items": {"type": "object", "properties": {
            "x_mm": {"type": "number"}, "y_mm": {"type": "number"}, "w_mm": {"type": "number"}, "d_mm": {"type": "number"}},
            "required": ["x_mm", "y_mm", "w_mm", "d_mm"]}},
        "outlets": {"type": "array", "items": {"type": "object", "properties": {"x_mm": {"type": "number"}, "y_mm": {"type": "number"}},
                                                "required": ["x_mm", "y_mm"]}},
        "uncertain": {"type": "array", "maxItems": 4, "items": {"type": "object", "properties": {
            "item": {"type": "string"}, "question": {"type": "string"}, "options": {"type": "array", "items": {"type": "string"}, "maxItems": 4}},
            "required": ["item", "question"]}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["width_mm", "depth_mm", "openings", "pillars", "uncertain", "confidence"],
}

PLAN_SYSTEM = """당신은 건축 평면도를 읽어 직사각형 공간의 구조를 mm 단위로 옮기는 도우미입니다.
좌표계: 원점 = 정면(입구·도로 쪽) 왼쪽 모서리, x = 오른쪽, y = 안쪽(정면에서 멀어지는 쪽). 벽 이름은 front/back/left/right.
- 치수선·축척 표기에서 읽을 수 있는 값만 쓰세요. 읽을 수 없는 값은 추정하지 말고 uncertain 에 질문으로 남기세요.
- 직사각형이 아닌 부분이 있으면 가장 큰 직사각형으로 단순화하고 uncertain 에 적으세요.
- 문 종류(비상구·백오피스 등)가 불분명하면 uncertain 에 선택지와 함께 물어보세요."""

PHOTO_SCHEMA = {
    "type": "object",
    "properties": {
        "structure": {"type": "array", "maxItems": 6, "items": {"type": "string"}, "description": "구조·규모를 짧은 구절로(예: '약 45평 추정')"},
        "mood": {"type": "array", "maxItems": 6, "items": {"type": "string"}, "description": "분위기·마감을 짧은 구절로"},
        "width_mm_est": {"type": "number"}, "depth_mm_est": {"type": "number"}, "height_mm_est": {"type": "number"},
        "floor": {"type": "string", "enum": list(LIB["floors"])}, "wall": {"type": "string", "enum": list(LIB["walls"])},
        "accent": {"type": "string", "enum": list(LIB["accents"])},
        "photos": {"type": "array", "items": {"type": "object", "properties": {
            "index": {"type": "integer"}, "view": {"type": "string"}, "ok": {"type": "boolean"}, "issue": {"type": "string"}},
            "required": ["index", "ok"]}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["structure", "mood", "photos", "confidence"],
}

PHOTO_SYSTEM = """당신은 현장 사진 여러 장으로 실내 공간의 구조와 분위기를 읽는 도우미입니다. 결과는 3D 조감도(개략 이미지)에 쓰므로
크기는 추정값이어도 되지만, '추정'임을 구절에 밝히세요. 사람 얼굴·로고는 언급하지 마세요. 역광·흐림처럼 다시 찍으면 좋을 사진은
photos 에 ok=false 와 이유를 적으세요. 마감은 enum 중 가장 가까운 값을 고르세요."""

NL_SCHEMA = {
    "type": "object",
    "properties": {
        "ops": {"type": "array", "maxItems": 6, "items": {"type": "object", "properties": {
            "op": {"type": "string", "enum": ["move", "rotate", "delete", "set_bottom"]},
            "target": {"type": "string", "description": "대상 ID(목록에 있는 것만)"},
            "dx_mm": {"type": "number"}, "dy_mm": {"type": "number"}, "angle_deg": {"type": "number"}, "value_mm": {"type": "number"}},
            "required": ["op", "target"]}},
        "reply": {"type": "string", "description": "무엇을 바꿨는지 한 문장"},
    },
    "required": ["ops", "reply"],
}


def recognize_plan(client: ModelClient | None, image: str, confidential: bool) -> dict:
    if client is None:
        return {"ok": False, "source": "rules", "reason": "I2T 클라이언트 없음"}
    raw, meta = client.generate_json(PLAN_SYSTEM, "이 평면도에서 공간 구조를 읽어 주세요.", PLAN_SCHEMA, "birdseye_plan",
                                     images=[image], confidential=confidential)
    if not raw:
        return {"ok": False, "source": meta.get("source"), "reason": meta.get("reason") or "도면을 읽지 못했어요"}
    try:
        W, D = float(raw["width_mm"]), float(raw["depth_mm"])
    except (KeyError, TypeError, ValueError):
        return {"ok": False, "source": "llm", "reason": "가로·세로 치수를 읽지 못했어요"}
    if not (1000 <= W <= 200000 and 1000 <= D <= 200000):
        return {"ok": False, "source": "llm", "reason": f"치수가 이상해요({W:.0f} × {D:.0f})"}
    ops = []
    for i, o in enumerate(raw.get("openings") or []):
        if o.get("kind") in ("window", "entrance", "door") and o.get("wall") in WALL_ENUM:
            L = W if o["wall"] in ("front", "back") else D
            a = max(0.0, min(L, float(o.get("start_mm") or 0)))
            ln = max(100.0, min(L - a, float(o.get("length_mm") or 0)))
            ops.append({"id": f"O{i + 1}", "kind": o["kind"], "wall": o["wall"], "start": round(a), "length": round(ln),
                        "label": o.get("label") or "", "sill": 0 if o["kind"] != "window" else 900,
                        "head": 2400 if o["kind"] != "window" else 2400})
    pillars = [{"id": f"P{i + 1}", "label": f"기둥 {i + 1}", "x": round(p["x_mm"]), "y": round(p["y_mm"]), "w": round(p["w_mm"]),
                "d": round(p["d_mm"])} for i, p in enumerate(raw.get("pillars") or []) if 0 < p.get("x_mm", -1) < W and 0 < p.get("y_mm", -1) < D]
    outlets = [{"id": f"C{i + 1}", "label": f"C{i + 1}", "x": round(o["x_mm"]), "y": round(o["y_mm"]), "on": ""}
               for i, o in enumerate(raw.get("outlets") or [])]
    space = {"width": round(W), "depth": round(D), "height": round(raw.get("height_mm") or 3000), "openings": ops, "pillars": pillars,
             "outlets": outlets, "source": "plan_upload"}
    return {"ok": True, "source": meta.get("source"), "space": space, "scale_text": raw.get("scale_text", ""),
            "uncertain": raw.get("uncertain") or [], "confidence": raw.get("confidence"), "height_read": raw.get("height_mm") is not None}


def read_photos(client: ModelClient | None, images: list[str], text: str, confidential: bool) -> dict:
    if client is None:
        return {"ok": False, "source": "rules", "reason": "I2T 클라이언트 없음"}
    if not images:
        return {"ok": False, "source": "rules", "reason": "사진이 없어요"}
    raw, meta = client.generate_json(PHOTO_SYSTEM, f"사용자 설명: {text or '(없음)'}\n사진 {len(images)}장의 순서대로 index 0부터.",
                                     PHOTO_SCHEMA, "birdseye_photos", images=images[:4], confidential=confidential)
    if not raw:
        return {"ok": False, "source": meta.get("source"), "reason": meta.get("reason") or "사진을 읽지 못했어요"}
    est = {}
    for k in ("width_mm_est", "depth_mm_est", "height_mm_est"):
        v = raw.get(k)
        if isinstance(v, (int, float)) and 1000 <= v <= 200000:
            est[k] = round(v / 100) * 100
    return {"ok": True, "source": meta.get("source"), "structure": raw.get("structure", []), "mood": raw.get("mood", []),
            "estimate": est, "finishes": {k: raw.get(k) for k in ("floor", "wall", "accent") if raw.get(k)},
            "photos": raw.get("photos", []), "confidence": raw.get("confidence")}


# ── 말로 수정(2D) ──

_UNIT = {"mm": 1, "cm": 10, "m": 1000, "": 1}
_DIRS = {"오른쪽": (1, 0), "왼쪽": (-1, 0), "위": (0, -1), "위쪽": (0, -1), "아래": (0, 1), "아래쪽": (0, 1), "안쪽": (0, 1),
         "정면": (0, -1), "앞": (0, -1), "뒤": (0, 1), "뒤쪽": (0, 1)}


def _targets(project: dict, catalog) -> list[dict]:
    items = []
    for f in project.get("fixtures", []):
        items.append({"id": f["id"], "label": f.get("label") or f["type"], "kind": "fixture"})
    for pl in project.get("placements", []):
        p = catalog.get(pl["product"])
        items.append({"id": pl["id"], "label": (p["short"] if p else pl["product"]), "kind": "product"})
    return items


def _match(items, name):
    name = name.strip()
    exact = [it for it in items if it["label"] == name]
    if exact:
        return exact
    return [it for it in items if name and (name in it["label"] or it["label"] in name)]


def nl_edit_rules(project: dict, catalog, text: str) -> dict:
    items = _targets(project, catalog)
    t = text.strip()
    ops = []
    m = re.search(r"(.+?)(?:을|를)?\s*(\d+(?:\.\d+)?)\s*(mm|cm|m)?\s*(오른쪽|왼쪽|위쪽|아래쪽|위|아래|안쪽|정면|앞|뒤쪽|뒤)\s*(?:으로|로)", t) or \
        re.search(r"(.+?)(?:을|를)?\s*(오른쪽|왼쪽|위쪽|아래쪽|위|아래|안쪽|정면|앞|뒤쪽|뒤)\s*(?:으로|로)\s*(\d+(?:\.\d+)?)\s*(mm|cm|m)?", t)
    if m:
        g = m.groups()
        if g[1] and g[1][0].isdigit():
            name, val, unit, d = g[0], float(g[1]), g[2] or "", g[3]
        else:
            name, d, val, unit = g[0], g[1], float(g[2]), g[3] or ""
        dist = val * _UNIT[unit]
        for it in _match(items, name):
            dx, dy = _DIRS[d]
            ops.append({"op": "move", "target": it["id"], "dx_mm": dx * dist, "dy_mm": dy * dist})
    m = re.search(r"(.+?)(?:을|를)?\s*(\d+)\s*도\s*(?:회전|돌려)", t)
    if m:
        for it in _match(items, m.group(1)):
            ops.append({"op": "rotate", "target": it["id"], "angle_deg": float(m.group(2))})
    m = re.search(r"(.+?)(?:을|를)?\s*(?:삭제|빼|없애)", t)
    if m and not ops:
        for it in _match(items, m.group(1)):
            if it["kind"] == "fixture":
                ops.append({"op": "delete", "target": it["id"]})
    m = re.search(r"(.+?)\s*하단(?:을|를)?\s*(\d+)\s*(mm|cm|m)?", t)
    if m:
        for it in _match(items, m.group(1)):
            if it["kind"] == "product":
                ops.append({"op": "set_bottom", "target": it["id"], "value_mm": float(m.group(2)) * _UNIT[m.group(3) or ""]})
    reply = f"{len(ops)}개 항목을 바꿨어요" if ops else "이해하지 못했어요 — 예: '라운지 소파 600 오른쪽으로', '관람 벤치 1열 삭제', 'QM43C 하단 1200'"
    return {"ops": ops, "reply": reply, "source": "rules"}


def nl_edit(client: ModelClient | None, project: dict, catalog, text: str) -> dict:
    items = _targets(project, catalog)
    if client is not None:
        lst = "\n".join(f"- {it['id']}: {it['label']} ({'집기' if it['kind'] == 'fixture' else '제품'})" for it in items)
        sys = ("2D 배치 도면을 사용자의 말에 따라 고치는 도우미입니다. 좌표: x 오른쪽, y 아래(안쪽), 단위 mm. "
               "'위'는 y 감소, '아래'는 y 증가. 목록에 있는 ID 만 쓰세요. 제품(삼성)은 삭제하지 마세요.")
        raw, meta = client.generate_json(sys, f"[대상 목록]\n{lst}\n\n[요청] {text}", NL_SCHEMA, "birdseye_nl_edit",
                                         confidential=bool(project.get("confidential")))
        if raw:
            ids = {it["id"]: it for it in items}
            ops = [o for o in raw.get("ops", []) if o.get("target") in ids and not (o.get("op") == "delete" and ids[o["target"]]["kind"] == "product")]
            return {"ops": ops, "reply": raw.get("reply", ""), "source": meta.get("source")}
    return nl_edit_rules(project, catalog, text)


def apply_nl_ops(project: dict, ops: list[dict]) -> list[str]:
    log = []
    for o in ops:
        coll = None
        it = None
        for c in ("fixtures", "placements"):
            for x in project.get(c, []):
                if x["id"] == o["target"]:
                    coll, it = c, x
        if not it:
            continue
        if o["op"] == "move":
            it["x"] = round(it["x"] + float(o.get("dx_mm") or 0))
            it["y"] = round(it["y"] + float(o.get("dy_mm") or 0))
            log.append(f"{o['target']} 이동")
        elif o["op"] == "rotate":
            it["rot"] = (float(it.get("rot", 0)) + float(o.get("angle_deg") or 0)) % 360
            log.append(f"{o['target']} 회전")
        elif o["op"] == "delete" and coll == "fixtures":
            project["fixtures"] = [x for x in project["fixtures"] if x["id"] != o["target"]]
            log.append(f"{o['target']} 삭제")
        elif o["op"] == "set_bottom" and coll == "placements":
            it["bottom"] = float(o.get("value_mm") or it.get("bottom", 0))
            log.append(f"{o['target']} 하단")
    return log


# ── 존별 포인트 문구(BP3Z) ──

ZP_SCHEMA = {
    "type": "object",
    "properties": {
        "zones": {"type": "array", "maxItems": 12, "items": {"type": "object", "properties": {
            "no": {"type": "integer"}, "name": {"type": "string", "description": "존 이름(바꾸라는 요청이 없으면 그대로)"},
            "point": {"type": "string", "description": "고객 관점 한 문장, 40자 안팎, ~요/~습니다 체"}},
            "required": ["no", "name", "point"]}},
        "reply": {"type": "string"},
    },
    "required": ["zones", "reply"],
}

_ZP_RULE = {
    "window": "길을 지나는 고객도 창 너머 메시지를 볼 수 있어요",
    "lounge": "들어오자마자 안내를 받고 편히 기다릴 수 있어요",
    "pillar": "기둥마다 길 안내와 프로모션을 보여줘요",
    "mediawall": "큰 화면 앞에 앉아 브랜드 영상을 감상해요",
    "ledgrid": "큰 화면 앞에 앉아 브랜드 영상을 감상해요",
    "videowall": "운영석 어디서든 상황판을 한눈에 봐요",
    "stand": "상담석에서 제품을 직접 시연하며 설명해요",
    "wall_seats": "기다리는 동안 안내 화면으로 순서를 확인해요",
    "reception": "접수 순서와 안내를 바로 확인해요",
    "rhythm": "벽을 따라 걸으며 콘텐츠를 차례로 봐요",
    "retail": "진열 사이에서 제품 정보를 바로 확인해요",
    "dining": "자리에서 메뉴와 이벤트를 확인해요",
    "meeting": "회의 자료를 큰 화면으로 함께 봐요",
    "class": "어느 자리에서든 수업 화면이 잘 보여요",
    "bed": "객실에서 편하게 콘텐츠를 즐겨요",
}


def _zone_items(project: dict, catalog) -> list[dict]:
    out = []
    for z in sorted(project.get("zones", []), key=lambda z: z.get("no", 0)):
        x0, x1 = sorted((z["x0"], z["x1"]))
        y0, y1 = sorted((z["y0"], z["y1"]))
        prods: dict[str, int] = {}
        for pl in project.get("placements", []):
            if x0 <= pl["x"] <= x1 and y0 <= pl["y"] <= y1:
                p = catalog.get(pl["product"])
                k = p["short"] if p else pl["product"]
                prods[k] = prods.get(k, 0) + 1
        fx = [f.get("label") or f["type"] for f in project.get("fixtures", []) if x0 <= f["x"] <= x1 and y0 <= f["y"] <= y1]
        out.append({"no": z.get("no"), "key": z.get("key"), "name": z.get("name", ""), "point": z.get("point", ""),
                    "products": prods, "fixtures": fx[:6]})
    return out


def zone_points(client: ModelClient | None, project: dict, catalog, text: str) -> dict:
    """존 이름·포인트 문구 다듬기. 이름 바꾸기('존 2 이름을 '웰컴 라운지'로')는 규칙으로도 처리한다."""
    zs = _zone_items(project, catalog)
    t = (text or "").strip()
    renames = {int(m.group(1)): m.group(2).strip() for m in
               re.finditer(r"존\s*(\d+)\s*(?:의)?\s*(?:이름)?(?:을|를)?\s*['‘’\"“”「](.+?)['‘’\"“”」]\s*(?:으로|로)", t)}
    if client is not None and zs:
        lst = "\n".join(f"- 존 {z['no']} · {z['name']} · 제품 {', '.join(f'{k} ×{n}' for k, n in z['products'].items()) or '없음'} · 집기 {', '.join(z['fixtures']) or '없음'}"
                        for z in zs)
        sys = ("B2B 제안서의 '존별 포인트'를 쓰는 도우미입니다. 존마다 고객 관점 한 문장(40자 안팎, ~요 체)으로 씁니다. "
               "제품 모델명을 지어내지 말고 목록에 있는 것만 쓰세요. 이름 바꾸라는 요청이 없으면 이름은 그대로 두세요.")
        raw, meta = client.generate_json(sys, f"[존 목록]\n{lst}\n\n[요청] {t or '존마다 포인트 문구를 써 주세요'}", ZP_SCHEMA,
                                         "birdseye_zone_points", confidential=bool(project.get("confidential")))
        if raw:
            got = {z.get("no"): z for z in raw.get("zones", []) if isinstance(z, dict)}
            res = []
            for z in zs:
                g = got.get(z["no"], {})
                res.append({"no": z["no"], "name": renames.get(z["no"]) or (g.get("name") or z["name"]).strip()[:24],
                            "point": (g.get("point") or z["point"] or "").strip()[:80]})
            return {"zones": res, "reply": raw.get("reply") or "존 문구를 다듬었어요", "source": meta.get("source")}
    res = []
    for z in zs:
        point = z["point"]
        if not point or "문장" in t or "포인트" in t or not t:
            prods = " · ".join(f"{k} ×{n}" for k, n in z["products"].items())
            base = _ZP_RULE.get(z["key"] or "", "이 존의 쓰임을 한눈에 보여줘요")
            point = f"{base} ({prods})" if prods else base
        res.append({"no": z["no"], "name": renames.get(z["no"], z["name"]), "point": point})
    reply = ("이름 " + ", ".join(f"존 {k} → {v}" for k, v in renames.items()) + " · " if renames else "") + "규칙 기반 문구로 채웠어요"
    return {"zones": res, "reply": reply, "source": "rules"}
