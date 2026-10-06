"""도면 인식(08-birdseye §4.3 · §7.4) — 벡터 PDF(결정적) · 래스터(영상 처리 + i2t 박스) → 공간 모델.

raw(인식 원본, 환산 m) → model_from_raw(raw, 치수 선택 배율, 문 종류, 말로 고치기 연산) → SpaceModel.
- 벡터: pdfplumber 선 · 사각형 · 곡선 · 글자 — 두꺼운 선 = 벽, 벽 틈 + 호 = 문, 얇은 평행선 = 창, 채운 사각 ≥ 300 mm = 기둥,
  빗금 · EV/STAIRS 글자 사각 = 코어, 「1:100」 = 축척, 「24.0 m」 = 치수.
- 래스터: 어두운 굵은 선의 외곽(행 · 열 누적) + i2t(json + bbox) → 창 · 문 · 기둥 · 코어 · 치수.
  bbox 미지원 → 개수 · 글자만 + 외곽 사각형 단순화(plan:raster_nobbox). i2t 불가 → 영상 처리 외곽만.
- 치수 질문: |표기 − 환산| / 표기 > 1%. 문 종류 질문: 신뢰도 < 0.6. 위치어 = 주출입구 기준 앞 · 뒤 · 왼 · 오른.
"""
from __future__ import annotations

import copy
import io
import math
import re
from typing import Any

from pydantic import BaseModel, Field

from . import config
from . import space as S
from . import text as T

PT_M = 25.4 / 72.0 / 1000.0          # 1 pt(용지) = m
SIDES = ("top", "right", "bottom", "left")
KO_COUNT = {1: "한", 2: "두", 3: "세", 4: "네", 5: "다섯", 6: "여섯", 7: "일곱", 8: "여덟", 9: "아홉", 10: "열"}


# ── i2t 스키마 ──────────────────────────────────────────

class I2TDoor(BaseModel):
    side: str = Field(description="top · right · bottom · left (그림 기준)")
    order: int = 0
    type: str = Field("unknown", description="main · emergency · backoffice · normal · unknown")
    confidence: float = 0.5


class I2TWindow(BaseModel):
    side: str
    label: str = ""


class I2TDim(BaseModel):
    side: str
    text: str = ""
    value_m: float | None = None


class I2TCore(BaseModel):
    kinds: list[str] = Field(default_factory=list)


class PlanI2T(BaseModel):
    is_floor_plan: bool = True
    doors: list[I2TDoor] = Field(default_factory=list)
    windows: list[I2TWindow] = Field(default_factory=list)
    scale_text: str | None = None
    dims: list[I2TDim] = Field(default_factory=list)
    columns: int | None = None
    cores: list[I2TCore] = Field(default_factory=list)


class ImageKind(BaseModel):
    is_floor_plan: bool = False
    reason: str = ""


PLAN_PROMPT = ("이 그림은 건물 평면도({mode})다. 벽 · 창 · 문 · 기둥 · 코어(EV · 계단)와 축척 글자(예 1:100), 치수 글자(예 24.0 m)를 읽어라. "
               "문마다 그림 기준 변(top · right · bottom · left), 그 변에서의 순서, 종류(main = 주출입구 · emergency = 비상구 · "
               "backoffice = 백오피스 출입 · normal · unknown)와 신뢰도(0~1)를 적어라. 상자 label 은 window · door · column · core · dim 중 하나.")


# ── 벡터 PDF ─────────────────────────────────────────────

def _scale_from_words(words: list[dict[str, Any]]) -> int | None:
    text = " ".join(w["text"] for w in words)
    for pat in (r"1\s*:\s*(\d{2,4})", r"S\s*=\s*1\s*/\s*(\d{2,4})", r"SCALE\s*1\s*/\s*(\d{2,4})"):
        m = re.search(pat, text, re.I)
        if m:
            v = int(m.group(1))
            if 10 <= v <= 2000:
                return v
    return None


def _dims_from_words(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for i, w in enumerate(words):
        t = w["text"]
        m = re.fullmatch(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*m", t)
        val = None
        if m:
            val = float(m.group(1).replace(",", "."))
        elif re.fullmatch(r"\d{1,3}(?:[.]\d{1,2})?", t) and i + 1 < len(words) and words[i + 1]["text"].lower() == "m":
            val = float(t)
        elif re.fullmatch(r"\d{1,3},\d{3}", t):
            val = float(t.replace(",", "")) / 1000.0
        if val and 0.5 <= val <= 300:
            out.append({"value_m": val, "x": (w["x0"] + w["x1"]) / 2, "y": (w["top"] + w["bottom"]) / 2, "text": t})
    return out


def analyze_vector(pdf_bytes: bytes, page_no: int = 1) -> dict[str, Any] | None:
    """벡터 요소가 없으면 None(래스터로)."""
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        if page_no > len(pdf.pages):
            page_no = 1
        page = pdf.pages[page_no - 1]
        lines = list(page.lines)
        rects = list(page.rects)
        curves = list(page.curves)
        words = page.extract_words()
        pw, ph = float(page.width), float(page.height)
        pages = len(pdf.pages)
    thick = [ln for ln in lines if (ln.get("linewidth") or 0) >= 2.5]
    if len(thick) < 3:
        return None
    hs = [ln for ln in thick if abs(ln["top"] - ln["bottom"]) < 1.0]
    vs = [ln for ln in thick if abs(ln["x0"] - ln["x1"]) < 1.0]
    if not hs or not vs:
        return None
    xmin = min(min(ln["x0"] for ln in hs), min(ln["x0"] for ln in vs))
    xmax = max(max(ln["x1"] for ln in hs), max(ln["x0"] for ln in vs))
    ymin = min(min(ln["top"] for ln in hs), min(ln["top"] for ln in vs))
    ymax = max(max(ln["top"] for ln in hs), max(ln["bottom"] for ln in vs))
    tol = 4.0
    ratio = _scale_from_words(words)
    scale_source = "pdf_text" if ratio else "default"
    side_len = {"top": xmax - xmin, "bottom": xmax - xmin, "left": ymax - ymin, "right": ymax - ymin}

    def side_of_h(y: float) -> str | None:
        if abs(y - ymin) <= tol:
            return "top"
        if abs(y - ymax) <= tol:
            return "bottom"
        return None

    def side_of_v(x: float) -> str | None:
        if abs(x - xmin) <= tol:
            return "left"
        if abs(x - xmax) <= tol:
            return "right"
        return None

    covered: dict[str, list[tuple[float, float]]] = {s: [] for s in SIDES}
    for ln in hs:
        sd = side_of_h(ln["top"])
        if sd:
            covered[sd].append((ln["x0"] - xmin, ln["x1"] - xmin))
    for ln in vs:
        sd = side_of_v(ln["x0"])
        if sd:
            covered[sd].append((min(ln["top"], ln["bottom"]) - ymin, max(ln["top"], ln["bottom"]) - ymin))
    # 창: 얇은 평행선(벽 띠 안)
    thin = [ln for ln in lines if (ln.get("linewidth") or 0) < 2.5]
    win_cov: dict[str, list[tuple[float, float]]] = {s: [] for s in SIDES}
    for ln in thin:
        if abs(ln["top"] - ln["bottom"]) < 1.0:
            sd = side_of_h(ln["top"])
            if sd and (ln["x1"] - ln["x0"]) > 10:
                win_cov[sd].append((round(ln["x0"] - xmin, 1), round(ln["x1"] - xmin, 1)))
        elif abs(ln["x0"] - ln["x1"]) < 1.0:
            sd = side_of_v(ln["x0"])
            if sd and (ln["bottom"] - ln["top"]) > 10:
                win_cov[sd].append((round(ln["top"] - ymin, 1), round(ln["bottom"] - ymin, 1)))
    openings: list[dict[str, Any]] = []
    for sd in SIDES:
        segs = sorted(covered[sd])
        merged: list[list[float]] = []
        for a, b in segs:
            if merged and a <= merged[-1][1] + 1.0:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        gaps = []
        cur = 0.0
        for a, b in merged:
            if a - cur > 3.0:
                gaps.append((cur, a))
            cur = max(cur, b)
        if side_len[sd] - cur > 3.0:
            gaps.append((cur, side_len[sd]))
        wins: dict[tuple[float, float], int] = {}
        for a, b in win_cov[sd]:
            wins[(a, b)] = wins.get((a, b), 0) + 1
        win_iv = sorted((a, b) for (a, b), n in wins.items() if n >= 2)
        win_merged: list[list[float]] = []
        for a, b in win_iv:
            if win_merged and a <= win_merged[-1][1] + 1.0:
                win_merged[-1][1] = max(win_merged[-1][1], b)
            else:
                win_merged.append([a, b])
        for g0, g1 in gaps:
            inside = [(a, b) for a, b in win_merged if a >= g0 - 2 and b <= g1 + 2]
            for a, b in inside:
                openings.append({"side": sd, "kind": "window", "s0": a, "s1": b})
            rest = []
            cur2 = g0
            for a, b in inside:
                if a - cur2 > 0:
                    rest.append((cur2, a))
                cur2 = max(cur2, b)
            if g1 - cur2 > 0:
                rest.append((cur2, g1))
            for r0, r1 in rest:
                if r1 - r0 <= 3.0:
                    continue
                has_arc = False
                for c in curves:
                    cx0, cx1, ct, cb = c["x0"], c["x1"], c["top"], c["bottom"]
                    if sd in ("top", "bottom"):
                        y = ymin if sd == "top" else ymax
                        if (ct - 2 <= y <= cb + 2) and cx1 >= xmin + r0 - 3 and cx0 <= xmin + r1 + 3:
                            has_arc = True
                    else:
                        x = xmin if sd == "left" else xmax
                        if (cx0 - 2 <= x <= cx1 + 2) and cb >= ymin + r0 - 3 and ct <= ymin + r1 + 3:
                            has_arc = True
                openings.append({"side": sd, "kind": "door" if has_arc else "opening", "s0": r0, "s1": r1})
    # 기둥 · 코어
    columns = []
    cores = []
    for r in rects:
        x0, x1, t, b = r["x0"], r["x1"], r["top"], r["bottom"]
        if x0 < xmin - 1 or x1 > xmax + 1 or t < ymin - 1 or b > ymax + 1:
            continue
        w, h = x1 - x0, b - t
        if r.get("fill") and not r.get("stroke") and max(w, h) / max(min(w, h), 1e-6) < 1.6 and min(w, h) >= 8.0:
            columns.append({"cx": (x0 + x1) / 2 - xmin, "cy": (t + b) / 2 - ymin, "w": w, "d": h})
        elif r.get("stroke") and not r.get("fill") and min(w, h) > 30:
            inside = [wd["text"].upper() for wd in words if x0 <= wd["x0"] <= x1 and t <= wd["top"] <= b]
            hatch = sum(1 for ln in thin if x0 - 1 <= min(ln["x0"], ln["x1"]) and max(ln["x0"], ln["x1"]) <= x1 + 1
                        and t - 1 <= ln["top"] and ln["bottom"] <= b + 1 and abs(ln["x0"] - ln["x1"]) > 1 and abs(ln["top"] - ln["bottom"]) > 1)
            kinds = []
            if any(k in ("EV", "ELEV", "ELEVATOR", "E/V") for k in inside):
                kinds.append("ev")
            if any(k.startswith("STAIR") or "계단" in k for k in inside):
                kinds.append("stairs")
            if any(k in ("WC", "화장실", "TOILET") for k in inside):
                kinds.append("toilet")
            if kinds or hatch >= 3:
                cores.append({"x0": x0 - xmin, "y0": t - ymin, "x1": x1 - xmin, "y1": b - ymin, "kinds": kinds or ["shaft"]})
    # 치수 글자 → 가장 가까운 평행 변
    dims = []
    for d in _dims_from_words(words):
        cands = []
        if xmin - 5 <= d["x"] <= xmax + 5:
            cands += [("top", abs(d["y"] - ymin)), ("bottom", abs(d["y"] - ymax))]
        if ymin - 5 <= d["y"] <= ymax + 5:
            cands += [("left", abs(d["x"] - xmin)), ("right", abs(d["x"] - xmax))]
        if not cands:
            continue
        sd, dist = min(cands, key=lambda c: c[1])
        if dist > 80:
            continue
        dims.append({"side": sd, "annotated_m": d["value_m"], "len_pt": side_len[sd]})
    # 축척이 없으면 치수로(첫 치수의 변)
    if not ratio and dims:
        d0 = dims[0]
        ratio = round(d0["annotated_m"] / (d0["len_pt"] * PT_M))
        scale_source = "dimension"
    m_pt = (ratio or 100) * PT_M
    if not ratio:
        scale_source = "default"
    raw = {
        "kind": "vector_pdf", "pages": pages, "page": page_no,
        "scale": {"ratio": ratio or 100, "source": scale_source},
        "w": round((xmax - xmin) * m_pt, 3), "h": round((ymax - ymin) * m_pt, 3),
        "openings": [{**o, "s0": round(o["s0"] * m_pt, 3), "s1": round(o["s1"] * m_pt, 3)} for o in openings],
        "columns": [{"cx": round(c["cx"] * m_pt, 3), "cy": round(c["cy"] * m_pt, 3), "w": round(c["w"] * m_pt, 3), "d": round(c["d"] * m_pt, 3)}
                    for c in columns],
        "cores": [{"x0": round(c["x0"] * m_pt, 3), "y0": round(c["y0"] * m_pt, 3), "x1": round(c["x1"] * m_pt, 3),
                   "y1": round(c["y1"] * m_pt, 3), "kinds": c["kinds"]} for c in cores],
        "dims": [{"side": d["side"], "annotated_m": d["annotated_m"], "computed_m": round(d["len_pt"] * m_pt, 2)} for d in dims],
        "page_box": [round(xmin / pw, 4), round(ymin / ph, 4), round(xmax / pw, 4), round(ymax / ph, 4)],
        "simplified": False,
    }
    return raw


# ── 래스터 ───────────────────────────────────────────────

def raster_outline(img_bytes: bytes) -> dict[str, Any] | None:
    """어두운 굵은 선 외곽(행 · 열 누적) — [x0, y0, x1, y1] 0..1 과 그림 크기."""
    import numpy as np
    from PIL import Image

    im = Image.open(io.BytesIO(img_bytes)).convert("L")
    W0, H0 = im.size
    scale = 1000 / max(W0, H0) if max(W0, H0) > 1000 else 1.0
    if scale != 1.0:
        im = im.resize((int(W0 * scale), int(H0 * scale)))
    a = np.asarray(im, dtype=np.float32) / 255.0
    H, W = a.shape
    dark = a < 0.45
    rows = dark.sum(axis=1) / W
    cols = dark.sum(axis=0) / H
    r_idx = [i for i, v in enumerate(rows) if v >= 0.25]
    c_idx = [i for i, v in enumerate(cols) if v >= 0.25]
    if len(r_idx) < 2 or len(c_idx) < 2:
        return None
    y0, y1 = min(r_idx), max(r_idx)
    x0, x1 = min(c_idx), max(c_idx)
    if (x1 - x0) < W * 0.1 or (y1 - y0) < H * 0.1:
        return None
    return {"box": [round(x0 / W, 4), round(y0 / H, 4), round(x1 / W, 4), round(y1 / H, 4)], "size": [W0, H0]}


def looks_like_plan(img_bytes: bytes) -> bool:
    """i2t 를 못 쓸 때 — 흰 바탕 + 가는 어두운 선이 많으면 도면으로 본다."""
    import numpy as np
    from PIL import Image

    try:
        im = Image.open(io.BytesIO(img_bytes)).convert("L")
    except Exception:  # noqa: BLE001
        return False
    im.thumbnail((400, 400))
    a = np.asarray(im, dtype=np.float32) / 255.0
    white = float((a > 0.85).mean())
    dark = float((a < 0.3).mean())
    return white > 0.6 and dark < 0.2 and raster_outline(img_bytes) is not None


def analyze_raster(img_bytes: bytes, i2t: dict[str, Any] | None, *, bbox_supported: bool, description_area_m2: float | None
                   ) -> dict[str, Any]:
    out = raster_outline(img_bytes)
    box = out["box"] if out else [0.1, 0.1, 0.9, 0.9]
    W0, H0 = out["size"] if out else (1000, 700)
    bw = (box[2] - box[0]) * W0
    bh = (box[3] - box[1]) * H0
    js = (i2t or {}).get("json") or {}
    boxes = (i2t or {}).get("boxes") or []
    # 축척: 치수 글자(정면 폭) → px 당 m, 아니면 설명 면적, 아니면 가로 20 m 가정
    ratio_text = js.get("scale_text")
    dims_in = [d for d in js.get("dims") or [] if d.get("value_m")]
    m_px = None
    scale_source = "default"
    dims = []
    if dims_in:
        d0 = dims_in[0]
        side_px = bw if d0.get("side") in ("top", "bottom") else bh
        m_px = float(d0["value_m"]) / max(side_px, 1.0)
        scale_source = "dimension"
    elif description_area_m2:
        m_px = math.sqrt(description_area_m2 / max(bw * bh, 1.0))
        scale_source = "description"
    else:
        m_px = 20.0 / max(bw, 1.0)
    ratio = None
    if ratio_text:
        m = re.search(r"1\s*[:/]\s*(\d{2,4})", str(ratio_text))
        if m:
            ratio = int(m.group(1))
            scale_source = "pdf_text" if scale_source == "default" else scale_source
    w_m, h_m = bw * m_px, bh * m_px
    for d in dims_in:
        side_px = bw if d.get("side") in ("top", "bottom") else bh
        dims.append({"side": d.get("side", "top"), "annotated_m": float(d["value_m"]), "computed_m": round(side_px * m_px, 2)})
    openings: list[dict[str, Any]] = []
    columns: list[dict[str, Any]] = []
    cores: list[dict[str, Any]] = []
    simplified = False
    use_boxes = bool(boxes) and bbox_supported

    def to_m(bx: list[float]) -> tuple[float, float, float, float]:
        x0 = (bx[0] - box[0]) * W0 * m_px
        y0 = (bx[1] - box[1]) * H0 * m_px
        x1 = (bx[2] - box[0]) * W0 * m_px
        y1 = (bx[3] - box[1]) * H0 * m_px
        return x0, y0, x1, y1

    if use_boxes:
        for b in boxes:
            lab = str(b.get("label", "")).lower()
            x0, y0, x1, y1 = to_m(b["box"])
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if lab in ("window", "door"):
                dists = {"top": abs(cy), "bottom": abs(cy - h_m), "left": abs(cx), "right": abs(cx - w_m)}
                sd = min(dists, key=lambda k: dists[k])
                if sd in ("top", "bottom"):
                    s0, s1 = max(0.0, x0), min(w_m, x1)
                else:
                    s0, s1 = max(0.0, y0), min(h_m, y1)
                if s1 - s0 > 0.3:
                    openings.append({"side": sd, "kind": lab, "s0": round(s0, 3), "s1": round(s1, 3)})
            elif lab == "column":
                columns.append({"cx": round(cx, 3), "cy": round(cy, 3), "w": round(max(0.3, x1 - x0), 3), "d": round(max(0.3, y1 - y0), 3)})
            elif lab == "core":
                cores.append({"x0": round(max(0.0, x0), 3), "y0": round(max(0.0, y0), 3), "x1": round(min(w_m, x1), 3),
                              "y1": round(min(h_m, y1), 3), "kinds": ["ev", "stairs"]})
    elif js:
        simplified = True
        n = int(js.get("columns") or 0)
        for j in range(n):
            columns.append({"cx": round(w_m * (j + 1) / (n + 1), 3), "cy": round(h_m / 2, 3), "w": 0.6, "d": 0.6})
        door_sides = [d.get("side", "top") for d in js.get("doors") or []] or ["top"]
        for sd in sorted(set(door_sides)):
            L = w_m if sd in ("top", "bottom") else h_m
            openings.append({"side": sd, "kind": "door", "s0": round(L / 2 - 0.9, 3), "s1": round(L / 2 + 0.9, 3)})
        for wdw in js.get("windows") or []:
            sd = wdw.get("side", "top")
            L = w_m if sd in ("top", "bottom") else h_m
            openings.append({"side": sd, "kind": "window", "s0": 1.0, "s1": round(max(1.5, L / 2 - 1.2), 3)})
    else:
        simplified = True
    return {
        "kind": "raster", "pages": 1, "page": 1, "scale": {"ratio": ratio, "source": scale_source},
        "w": round(w_m, 3), "h": round(h_m, 3), "openings": openings, "columns": columns, "cores": cores, "dims": dims,
        "page_box": box, "simplified": simplified,
    }


# ── raw → 공간 모델 ──────────────────────────────────────

def _side_wall(sd: str, w: float, h: float) -> tuple[list[float], list[float]]:
    return {"top": ([0.0, 0.0], [w, 0.0]), "right": ([w, 0.0], [w, h]), "bottom": ([w, h], [0.0, h]), "left": ([0.0, h], [0.0, 0.0])}[sd]


def _side_len(sd: str, w: float, h: float) -> float:
    return w if sd in ("top", "bottom") else h


def _offset_on_wall(sd: str, s0: float, s1: float, w: float, h: float) -> float:
    """raw 변 좌표(왼→오, 위→아래) → 벽 a 점에서의 offset(벽은 시계 방향)."""
    if sd in ("top", "right"):
        return s0
    L = _side_len(sd, w, h)
    return L - s1


def _rel_word(main_side: str, sd: str) -> str:
    """주출입구 기준 위치어(들어와서 방 안을 볼 때)."""
    order = ["top", "right", "bottom", "left"]
    i = (order.index(sd) - order.index(main_side)) % 4
    return {0: "앞", 1: "왼", 2: "뒤", 3: "오른"}[i]


def door_types(raw: dict[str, Any], i2t_json: dict[str, Any] | None, *, i2t_ok: bool) -> list[dict[str, Any]]:
    """문마다 {idx, type, confidence, main}. i2t 가 없으면 주출입구 = 창이 있는 변의 가장 넓은 문, 나머지는 질문."""
    doors = [(i, o) for i, o in enumerate(raw["openings"]) if o["kind"] in ("door", "opening")]
    out = []
    by_side: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for i, o in doors:
        by_side.setdefault(o["side"], []).append((i, o))
    for sd in by_side:
        by_side[sd].sort(key=lambda t: t[1]["s0"])
    hints = {}
    if i2t_ok and i2t_json:
        for d in i2t_json.get("doors") or []:
            lst = by_side.get(str(d.get("side")))
            if not lst:
                continue
            k = min(max(int(d.get("order") or 0), 0), len(lst) - 1)
            hints[lst[k][0]] = d
    main_idx = None
    for i, o in doors:
        h = hints.get(i)
        if h and h.get("type") == "main" and float(h.get("confidence") or 0) >= 0.6:
            main_idx = i
            break
    if main_idx is None and doors:
        win_sides = {o["side"] for o in raw["openings"] if o["kind"] == "window"}
        cand = [(i, o) for i, o in doors if o["side"] in win_sides] or doors
        main_idx = max(cand, key=lambda t: (round(t[1]["s1"] - t[1]["s0"], 3), -t[0]))[0]
    for i, o in doors:
        h = hints.get(i) or {}
        if i == main_idx:
            out.append({"idx": i, "type": "main", "confidence": float(h.get("confidence") or 0.7), "main": True})
        else:
            typ = h.get("type") or "unknown"
            if typ == "main":
                typ = "normal"
            out.append({"idx": i, "type": typ, "confidence": float(h.get("confidence") or 0.0) if i2t_ok else 0.0, "main": False})
    return out


def model_from_raw(raw: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """plan: {dims_choice{side: {choice, manual_m}}, doors[{idx,type,confidence,main}], answers{qid: option}, edits[], i2t_windows}."""
    rules = config.rules()
    qcfg = rules["questions"]
    factor = 1.0
    dims_out = []
    questions = []
    choices = plan.get("dim_choices") or {}
    # 치수
    qn = 0
    for k, d in enumerate(raw.get("dims") or []):
        did = f"d{k + 1}"
        ch = choices.get(did) or {}
        choice = ch.get("choice") or qcfg.get("default_dim", "annotated")
        manual = ch.get("manual_m")
        a, c = d["annotated_m"], d["computed_m"]
        asked = a > 0 and abs(a - c) / a > float(qcfg["dim_mismatch_ratio"])
        label = {"top": "정면 폭", "bottom": "후면 폭", "left": "왼쪽 깊이", "right": "오른쪽 깊이"}.get(d["side"], "폭")
        dims_out.append({"id": did, "label": label, "wall_id": None, "annotated_m": a, "computed_m": c, "choice": choice,
                         "manual_m": manual, "answered": bool(ch), "asked": asked, "side": d["side"]})
        if k == 0:
            if choice == "annotated" and c > 0:
                factor = a / c
            elif choice == "manual" and manual and c > 0:
                factor = float(manual) / c
            else:
                factor = 1.0
        if asked:
            qn += 1
            questions.append({
                "id": f"q_{did}", "n": qn, "kind": "dim", "ref": did, "title": f"치수 보정 · {label}",
                "sub": f"도면 표기 {T.m(a)} m · 축척 1:{raw['scale'].get('ratio') or '—'} 환산 {T.m(c)} m",
                "options": [{"value": "annotated", "label": f"표기값 {T.m(a)} m"}, {"value": "computed", "label": f"환산값 {T.m(c)} m"},
                            {"value": "manual", "label": "직접 입력"}],
                "answered": bool(ch), "answer": choice, "manual_m": manual,
            })
    W = round(raw["w"] * factor, 2)
    H = round(raw["h"] * factor, 2)
    doors = {d["idx"]: d for d in plan.get("doors") or []}
    answers = plan.get("answers") or {}
    main = next((raw["openings"][d["idx"]] for d in doors.values() if d.get("main")), None)
    main_side = main["side"] if main else next((o["side"] for o in raw["openings"] if o["kind"] == "window"), "top")
    order = ["top", "right", "bottom", "left"]
    mi = order.index(main_side)
    screen = {"top": "위쪽", "right": "오른쪽", "bottom": "아래쪽", "left": "왼쪽"}
    labels = {sd: screen[sd] for sd in order}
    labels[main_side] = "정면"
    labels[order[(mi + 2) % 4]] = "후면"
    dim_sides = {d["side"] for d in raw.get("dims") or []}
    walls = []
    wid = {}
    for k, sd in enumerate(order, start=1):
        a, b = _side_wall(sd, W, H)
        wid[sd] = f"w{k}"
        walls.append({"id": f"w{k}", "a": a, "b": b, "thickness": 0.2, "kind": "exterior", "label": labels.get(sd, ""),
                      "dim_known": sd in dim_sides, "room_id": "r1"})
    for d in dims_out:
        d["wall_id"] = wid.get(d.pop("side", "top"))
    openings = []
    assumptions = []
    on = 0
    win_labels = {w.get("side"): w.get("label") for w in plan.get("i2t_windows") or [] if w.get("label")}
    for i, o in enumerate(raw["openings"]):
        sd = o["side"]
        s0, s1 = o["s0"] * factor, o["s1"] * factor
        off = round(_offset_on_wall(sd, s0, s1, W, H), 2)
        width = round(s1 - s0, 2)
        if o["kind"] == "window":
            on += 1
            lab = win_labels.get(sd) or ("전면 유리창" if sd == main_side else "창")
            openings.append({"id": f"o{on}", "kind": "window", "wall_id": wid[sd], "offset": off, "width": width, "label": lab,
                             "faces_outdoor": sd == main_side})
            continue
        d = doors.get(i) or {"type": "unknown", "confidence": 0.0, "main": False}
        qid = f"q_door{i}"
        ans = answers.get(qid)
        if ans == "wall":
            continue
        on += 1
        rel = _rel_word(main_side, sd)
        typ = d["type"]
        conf = float(d.get("confidence") or 0.0)
        assumed = False
        if ans in ("emergency", "backoffice"):
            typ, conf = ans, 1.0
        rec = {"id": f"o{on}", "kind": "door", "wall_id": wid[sd], "offset": off, "width": width,
               "label": "주출입구" if d.get("main") else f"{rel}쪽 문", "door_type": "main" if d.get("main") else typ,
               "is_main": bool(d.get("main")), "confidence": round(conf, 2), "faces_outdoor": False, "assumed": False, "raw_idx": i}
        if not d.get("main") and ans is None and (typ == "unknown" or conf < float(qcfg["door_confidence_min"])):
            qn += 1
            questions.append({
                "id": qid, "n": qn, "kind": "door", "ref": rec["id"], "title": f"{rel}쪽 문은 어떤 문인가요?", "sub": None,
                "options": [{"value": "emergency", "label": "비상구"}, {"value": "backoffice", "label": "백오피스 출입"},
                            {"value": "wall", "label": "벽으로 처리"}],
                "answered": False, "answer": None, "manual_m": None,
            })
        elif ans is not None:
            qn += 1
            questions.append({
                "id": qid, "n": qn, "kind": "door", "ref": rec["id"], "title": f"{rel}쪽 문은 어떤 문인가요?", "sub": None,
                "options": [{"value": "emergency", "label": "비상구"}, {"value": "backoffice", "label": "백오피스 출입"},
                            {"value": "wall", "label": "벽으로 처리"}],
                "answered": True, "answer": ans, "manual_m": None,
            })
        if assumed:
            rec["assumed"] = True
        openings.append(rec)
    columns = [{"id": f"c{k}", "center": [round(c["cx"] * factor, 2), round(c["cy"] * factor, 2)],
                "w": round(c["w"] * factor, 2), "d": round(c["d"] * factor, 2), "label": ""}
               for k, c in enumerate(sorted(raw.get("columns") or [], key=lambda c: (round(c["cx"], 2), round(c["cy"], 2))), start=1)]
    cores = [{"id": f"k{k}", "polygon": [[round(c["x0"] * factor, 2), round(c["y0"] * factor, 2)], [round(c["x1"] * factor, 2), round(c["y0"] * factor, 2)],
                                          [round(c["x1"] * factor, 2), round(c["y1"] * factor, 2)], [round(c["x0"] * factor, 2), round(c["y1"] * factor, 2)]],
              "kinds": c.get("kinds") or []} for k, c in enumerate(raw.get("cores") or [], start=1)]
    model = {
        "rooms": [{"id": "r1", "label": plan.get("room_label") or "", "space_types": plan.get("space_types") or [],
                   "outline": [[0.0, 0.0], [W, 0.0], [W, H], [0.0, H]]}],
        "walls": walls, "openings": openings, "columns": columns, "cores": cores, "power_points": [],
        "ceiling_h": {"value": float(plan.get("ceiling_m") or 3.0), "estimated": not plan.get("ceiling_m")},
        "scale": {"ratio": raw["scale"].get("ratio"), "source": raw["scale"].get("source", "default"), "correction": round(factor, 4)},
        "dims": dims_out, "area_m2": round(W * H, 2), "features": [], "assumptions": assumptions, "questions": questions,
        "facts": [], "estimated": bool(raw.get("simplified")) or raw["scale"].get("source") == "default", "source": "plan",
        "meta_paths": list(plan.get("meta_paths") or []),
    }
    for e in plan.get("edits") or []:
        apply_space_op(model, e)
    S.recompute_area(model)
    model["features"] = S.features_from_model(model)
    return model


def finalize_defaults(model: dict[str, Any]) -> dict[str, Any]:
    """「이 구조로 계속」 — 미해결 질문에 안전 기본값(문 = 출입 가능, 치수 = 표기값)을 쓰고 가정으로 남긴다."""
    m = copy.deepcopy(model)
    for q in m.get("questions", []):
        if q.get("answered"):
            continue
        if q["kind"] == "door":
            for o in m["openings"]:
                if o["id"] == q["ref"]:
                    o["door_type"] = "normal"
                    o["assumed"] = True
                    word = q["title"].split("은 어떤")[0]
                    m["assumptions"].append({"kind": "door_unknown", "ref": o["id"], "action": "BE1D",
                                             "text_ko": f"{word} 종류를 몰라 출입 가능한 문(앞 1.2 m 비움)으로 두었어요."})
        elif q["kind"] == "dim":
            label = q["title"].replace("치수 보정 · ", "")
            ann = next((d for d in m.get("dims", []) if d["id"] == q["ref"]), None)
            if ann:
                m["assumptions"].append({"kind": "dim_default", "ref": ann["id"], "action": "BE1D",
                                         "text_ko": f"{label}은 도면 표기값 {T.m(ann['annotated_m'])} m로 맞췄어요."})
    return m


# ── 말로 고치기(공간 모델 연산) ──────────────────────────

class SpaceOp(BaseModel):
    op: str = Field(description="remove · add_column · set_door · set_window_full · set_dim")
    target: str | None = Field(None, description="c1 · o2 · w1 …")
    value: str | None = None
    number: float | None = None


class SpaceOps(BaseModel):
    ops: list[SpaceOp] = Field(default_factory=list)


def apply_space_op(model: dict[str, Any], op: dict[str, Any]) -> None:
    kind = op.get("op")
    tgt = op.get("target")
    if kind == "remove" and tgt:
        model["columns"] = [c for c in model["columns"] if c["id"] != tgt]
        model["openings"] = [o for o in model["openings"] if o["id"] != tgt]
        model["cores"] = [k for k in model["cores"] if k["id"] != tgt]
    elif kind == "add_column" and op.get("value"):
        try:
            x, y = (float(v) for v in str(op["value"]).split(","))
        except ValueError:
            return
        n = len(model["columns"]) + 1
        model["columns"].append({"id": f"c{n}", "center": [round(x, 2), round(y, 2)], "w": 0.6, "d": 0.6, "label": ""})
    elif kind == "set_door" and tgt and op.get("value"):
        for o in model["openings"]:
            if o["id"] == tgt and o["kind"] == "door":
                o["door_type"] = op["value"]
                o["confidence"] = 1.0
    elif kind == "set_window_full" and tgt:
        wall = next((w for w in model["walls"] if w["id"] == tgt), None)
        if wall:
            L = math.hypot(wall["b"][0] - wall["a"][0], wall["b"][1] - wall["a"][1])
            doors = [o for o in model["openings"] if o["wall_id"] == tgt and o["kind"] == "door"]
            model["openings"] = [o for o in model["openings"] if not (o["wall_id"] == tgt and o["kind"] == "window")]
            cur = 0.3
            n = len(model["openings"])
            for d in sorted(doors, key=lambda d: d["offset"]):
                if d["offset"] - cur > 0.5:
                    n += 1
                    model["openings"].append({"id": f"o{n + 10}", "kind": "window", "wall_id": tgt, "offset": round(cur, 2),
                                              "width": round(d["offset"] - cur, 2), "label": "전면 유리창", "faces_outdoor": True})
                cur = d["offset"] + d["width"]
            if L - 0.3 - cur > 0.5:
                n += 1
                model["openings"].append({"id": f"o{n + 10}", "kind": "window", "wall_id": tgt, "offset": round(cur, 2),
                                          "width": round(L - 0.3 - cur, 2), "label": "전면 유리창", "faces_outdoor": True})


def regex_space_ops(text: str, model: dict[str, Any]) -> list[dict[str, Any]]:
    """LLM 이 막힐 때 — 「오른쪽 기둥은 철거됐어」 · 「창은 끝까지 유리야」."""
    ops = []
    cols = sorted(model.get("columns", []), key=lambda c: (c["center"][0], c["center"][1]))
    if "기둥" in text and re.search(r"철거|없|빼|제거|뺐", text) and cols:
        if "오른" in text:
            ops.append({"op": "remove", "target": cols[-1]["id"]})
        elif "왼" in text:
            ops.append({"op": "remove", "target": cols[0]["id"]})
        elif "모두" in text or "전부" in text:
            ops += [{"op": "remove", "target": c["id"]} for c in cols]
    if re.search(r"창.*끝까지|끝까지.*유리|전면.*유리", text):
        front = next((w for w in model.get("walls", []) if w.get("label") == "정면"), None)
        if front:
            ops.append({"op": "set_window_full", "target": front["id"]})
    return ops


# ── 화면(BE1D) ──────────────────────────────────────────

def element_rows(model: dict[str, Any], questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    walls = model.get("walls", [])
    ext = sum(1 for w in walls if w.get("kind") == "exterior")
    inn = sum(1 for w in walls if w.get("kind") == "interior")
    if walls:
        rows.append({"key": "wall", "label": "벽", "summary": f"외벽 {ext}면" + (f" · 내벽 {inn}" if inn else "")})
    wins = [o for o in model.get("openings", []) if o["kind"] == "window"]
    if wins:
        groups: dict[str, int] = {}
        for o in wins:
            lab = (o.get("label") or "창").split(" (")[0]
            groups[lab] = groups.get(lab, 0) + 1
        rows.append({"key": "window", "label": "창", "summary": " · ".join(f"{k} {v}구간" for k, v in groups.items())})
    doors = [o for o in model.get("openings", []) if o["kind"] == "door"]
    if doors:
        main = sum(1 for o in doors if o.get("is_main"))
        others: dict[str, int] = {}
        for o in doors:
            if o.get("is_main"):
                continue
            others[o.get("label") or "문"] = others.get(o.get("label") or "문", 0) + 1
        parts = ([f"주출입구 {main}"] if main else []) + [f"{k} {v}" for k, v in others.items()]
        door_q = next((q for q in questions if q["kind"] == "door"), None)
        rows.append({"key": "door", "label": "문", "summary": " · ".join(parts), "question_n": door_q["n"] if door_q else None})
    cols = model.get("columns", [])
    if cols:
        sizes = {(round(c["w"] * 1000 / 10) * 10, round(c["d"] * 1000 / 10) * 10) for c in cols}
        if len(sizes) == 1:
            w, d = next(iter(sizes))
            rows.append({"key": "column", "label": "기둥", "summary": f"{len(cols)}개 · {w} × {d} mm"})
        else:
            rows.append({"key": "column", "label": "기둥", "summary": f"{len(cols)}개 · 크기 다름"})
    cores = model.get("cores", [])
    if cores:
        names = []
        for k in cores:
            for kd in k.get("kinds") or []:
                nm = {"ev": "EV", "stairs": "계단", "toilet": "화장실", "shaft": "샤프트"}.get(kd, kd)
                if nm not in names:
                    names.append(nm)
        rows.append({"key": "core", "label": "코어", "summary": " · ".join(names + ["배치 제외"])})
    return rows


def round_column_mm(v: float) -> int:
    return int(round(v * 1000 / 10) * 10)


def w_message(questions: list[dict[str, Any]], status: str) -> str:
    if status == "recognizing":
        return "도면을 읽고 있어요"
    if status == "failed":
        return "도면을 읽지 못했어요. 다른 도면을 올리거나 다시 인식해 주세요."
    open_q = [q for q in questions if not q.get("answered")]
    k = len(open_q)
    head = "도면에서 공간 구조를 읽었습니다. 벽 · 창 · 문 · 기둥이 표시한 대로 맞는지 보시고"
    if k == 0:
        return f"{head} 계속해 주세요."
    names = []
    for q in open_q:
        if q["kind"] == "dim":
            names.append(f"{q['title'].replace('치수 보정 · ', '')} 치수")
        else:
            names.append(q["title"].split("은 어떤")[0])
    cnt = f"{KO_COUNT.get(k, str(k))} 곳"
    return f"{head}, 확인이 필요한 {cnt}({', '.join(names)})을 정해 주세요."


def scale_label(model: dict[str, Any]) -> str:
    sc = model.get("scale") or {}
    area = T.area_label(model.get("area_m2"))
    if sc.get("ratio") and sc.get("source") in ("pdf_text", "dimension"):
        return f"축척 1:{sc['ratio']} 감지 · 면적 {area}"
    return f"축척 감지 못 함 · 면적 {area}"


def file_meta_label(page: int, size: int | None) -> str:
    """「1쪽 · 2.4 MB」 — 0.1 MB 보다 작으면 KB(「1쪽 · 2 KB」)."""
    b = size or 0
    if b < 0.1 * 1024 * 1024:
        return f"{page}쪽 · {max(1, round(b / 1024))} KB"
    return f"{page}쪽 · {b / (1024 * 1024):.1f} MB"
