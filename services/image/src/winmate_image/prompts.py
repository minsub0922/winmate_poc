"""프롬프트 만들기(결정적) — 조건 · 제품 외형 · 참조(이미지 / 글 대체) · 정책 대안 · 스타일 · 배경 여백 · 사람 정책.

LLM 이 구도(compose)를 정해 주면 그 영문 지시를 앞에 두고, 나머지 사실(제품 외형 · 정책)은 여기서 붙인다.
"""
from __future__ import annotations

from typing import Any

from . import config

STYLE_EN = {
    "photo": "photorealistic architectural visualization, realistic materials and lighting, high detail",
    "minimal_3d": "minimal 3D render, soft matte clay-like materials, clean even studio lighting",
    "illustration": "flat vector illustration, clean shapes, limited color palette",
}
KIND_EN = {
    "space": "A realistic commercial interior scene where the Samsung products are installed and in use.",
    "background": "An atmospheric background image for a presentation cover or section slide.",
    "scenario": "A candid moment of people using the Samsung products in a real business setting.",
    "composite": "A photo of the customer's real space with the Samsung products installed.",
}
SHOT_ANGLES = [
    ("정면 눈높이 · 낮", "Eye-level front view, bright daytime light."),
    ("살짝 높은 3/4 시점 · 오후", "Slightly elevated three-quarter view, warm late-afternoon light."),
    ("넓은 화각 낮은 시점 · 저녁", "Low wide-angle view showing the whole space, evening ambient lighting."),
    ("제품 중심 근접", "Medium close-up focusing on the products, soft natural light."),
]
STRENGTH_EN = {"low": "loosely inspired by", "mid": "follow", "high": "closely match"}
ASPECT_EN = {"color_light": "color palette and lighting", "composition": "composition and camera angle",
             "placement": "product placement", "material": "materials and textures"}
PEOPLE_EN = {
    "none": "No people in the scene.",
    "fictional": "Any people are fictional and must not resemble any real person or celebrity.",
    "back_hands": "People appear only from behind or as hands; no faces.",
    "generic": "Any people are generic, fictional and not identifiable.",
    "silhouette": "People appear only as distant, unidentifiable silhouettes.",
}
TEXT_AREA_EN = {
    "left": "Keep the left 40% of the frame as a calm, simple area with no objects, suitable for overlaying text.",
    "right": "Keep the right 40% of the frame as a calm, simple area with no objects, suitable for overlaying text.",
    "top": "Keep the top 35% of the frame as a calm, simple area, suitable for overlaying text.",
    "bottom": "Keep the bottom 35% of the frame as a calm, simple area, suitable for overlaying text.",
}


def arrangement_en(arr: str | None, qty: int) -> str:
    if qty <= 1:
        return ""
    if arr == "col3":
        return f", {qty} units stacked vertically"
    if arr == "separate":
        return f", {qty} units placed separately"
    return f", {qty} identical units mounted side by side in a horizontal row"


def product_sentence(p: dict[str, Any], dims: dict[str, Any] | None, *, arrangement: str | None = None) -> str:
    """제품 외형 문장 — 스펙 비율 · 베젤 · 색(예 “55-inch 16:9 landscape panel, thin black bezel (11.5 mm)”)."""
    qty = int(p.get("qty") or 1)
    d = dims or {}
    w, h = d.get("w_mm"), d.get("h_mm")
    orient = "portrait" if (w and h and h > w) else "landscape"
    inch = d.get("screen_inch")
    bezel = d.get("bezel_mm")
    name = p.get("name") or p.get("short") or "display"
    head = f"Samsung {name}" if not str(name).lower().startswith("samsung") else str(name)
    parts = [f"{head}{f' ×{qty}' if qty > 1 else ''}:"]
    size = f"{int(inch)}-inch " if isinstance(inch, (int, float)) else ""
    parts.append(f"{size}16:9 {orient} panel, thin black bezel" + (f" ({bezel:g} mm)" if isinstance(bezel, (int, float)) else ""))
    tail = arrangement_en(arrangement or ("row3" if qty > 1 else None), qty)
    return " ".join(parts) + tail + ". Keep the product's exact shape and proportions."


def reference_text(i: int, ref: dict[str, Any], *, sent_as_image: bool) -> str:
    aspects = [a for a in ref.get("aspects") or [] if a in ASPECT_EN]
    st = STRENGTH_EN.get(ref.get("strength") or "mid", "follow")
    names = ", ".join(ASPECT_EN[a] for a in aspects) or "overall mood"
    if sent_as_image:
        return f"Reference image {i}: {st} only its {names}; ignore people's faces and other brands' logos in it."
    an = ref.get("analysis") or {}
    desc = []
    for a in aspects:
        v = (an.get("elements") or {}).get(a) or an.get(a)
        if v:
            desc.append(f"{ASPECT_EN[a]}: {v}")
    if not desc and an.get("caption"):
        desc.append(an["caption"])
    pal = an.get("palette") or []
    line = f"Reference {i} ({ref.get('label') or 'reference'}) — {st} its {names}"
    if desc:
        line += ": " + "; ".join(desc)
    if pal:
        line += f". Palette: {', '.join(pal[:5])}"
    return line + "."


def build(*, kind: str, description: str, style: str, aspect: str, products: list[dict[str, Any]],
          dims: dict[str, dict[str, Any]], shot_en: str | None, effects: dict[str, Any], ref_lines: list[str],
          text_area: str | None = None, extra: list[str] | None = None, identity_line: str | None = None) -> dict[str, str]:
    """→ {prompt_en, negative}."""
    lines = []
    if shot_en:
        lines.append(shot_en.strip())
    lines.append(KIND_EN.get(kind, KIND_EN["space"]))
    if description:
        lines.append(f"Scene (Korean): {description}")
    for p in products:
        d = dims.get(p.get("model_code") or "") or {}
        lines.append(product_sentence(p, d, arrangement=p.get("arrangement")))
    if identity_line:
        lines.append(identity_line)
    if kind == "background":
        lines.append(TEXT_AREA_EN.get(text_area or "left", TEXT_AREA_EN["left"]))
    lines.extend(effects.get("lines") or [])
    people = effects.get("people")
    if people:
        lines.append(PEOPLE_EN.get(people, PEOPLE_EN["fictional"]))
    lines.extend(ref_lines)
    lines.extend(extra or [])
    lines.append(f"Style: {STYLE_EN.get(style, STYLE_EN['photo'])}. Aspect ratio {aspect}.")
    lines.append("Do not draw product specifications, certification marks or prices.")
    negative = ", ".join(effects.get("negatives") or [])
    return {"prompt_en": "\n".join(lines), "negative": negative}


def shot_plan(n: int, composed: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    """시안별 구도 — LLM(compose) 결과가 모자라면 결정적 기본 구도로 채운다."""
    out = []
    for i in range(n):
        if composed and i < len(composed) and (composed[i].get("prompt_en") or "").strip():
            out.append({"angle_ko": composed[i].get("angle_ko") or SHOT_ANGLES[i % 4][0], "prompt_en": composed[i]["prompt_en"]})
        else:
            ko, en = SHOT_ANGLES[i % len(SHOT_ANGLES)]
            out.append({"angle_ko": ko, "prompt_en": en})
    return out


def qc_correction(qc: dict[str, Any], products: list[dict[str, Any]]) -> str:
    fixes = []
    if qc.get("logo_visible") or qc.get("brand_text"):
        fixes.append("Remove any logos, brand marks or trademark text.")
    if qc.get("faces_fail"):
        fixes.append("Do not show identifiable faces.")
    if qc.get("count_fail") and products:
        fixes.append("Show exactly " + ", ".join(f"{int(p.get('qty') or 1)} {p.get('short') or p.get('name')}" for p in products) + ".")
    if qc.get("aspect_fail"):
        fixes.append("Keep the product proportions accurate (16:9 panels).")
    if qc.get("gibberish_text"):
        fixes.append("Avoid any rendered text.")
    return "Correction: " + " ".join(fixes) if fixes else ""


def edit_instruction(instruction: str, region_label: str | None) -> str:
    """§7.4 지시문 — `"{instruction}. Change only the {region_label}. Keep camera, lighting, and everything else identical."`"""
    inst = (instruction or "").strip().rstrip(".")
    if region_label:
        return f"{inst}. Change only the {region_label}. Keep camera, lighting, and everything else identical."
    return f"{inst}. Keep camera, lighting, composition and everything else identical."


def variant_instruction(item: dict[str, Any], *, keep_layout: bool = True) -> str:
    base = (item.get("instruction_en") or item.get("label") or "").strip().rstrip(".")
    tail = " Keep the products' placement, shape and proportions exactly as in the base image." if keep_layout else ""
    return f"{base}.{tail}"


VARIANT_DEFAULT = {
    "any": [{"label": "오후 자연광", "instruction_en": "Change to warm afternoon natural light through the windows"},
            {"label": "저녁 조명", "instruction_en": "Change to an evening scene with warm interior lighting"},
            {"label": "측면 시점", "instruction_en": "Show the same space from a slightly different side angle"},
            {"label": "제품 근접", "instruction_en": "Move the camera closer to the products"}],
    "lighting": [{"label": "아침 햇살", "instruction_en": "Change only the lighting to soft morning sunlight"},
                 {"label": "한낮 조명", "instruction_en": "Change only the lighting to bright midday light"},
                 {"label": "노을빛", "instruction_en": "Change only the lighting to golden sunset light"},
                 {"label": "야간 조명", "instruction_en": "Change only the lighting to night-time interior lighting"}],
    "people": [{"label": "손님 2명", "instruction_en": "Add two fictional customers (not resembling real persons)"},
               {"label": "붐비는 시간", "instruction_en": "Add a few fictional customers to show a busy moment"},
               {"label": "직원 응대", "instruction_en": "Add a fictional staff member helping a fictional customer"},
               {"label": "뒷모습 손님", "instruction_en": "Add fictional customers seen only from behind"}],
}


def kind_label(kind: str) -> str:
    return config.KIND_LABEL.get(kind, kind)
