"""아키타입 — 같은 칸 구조 · 배치를 쓰는 템플릿 묶음.

템플릿 코드마다 아키타입 하나와 매개변수(항목 수 · 이미지 유무 …)를 고른다(registry_data.TEMPLATE_MAP).
좌표는 'Winmate PPT' 디자인 캔버스(1280 × 720)의 실제 배치를 따랐다: 좌우 여백 64, 본문 1152,
머리(눈썹 44 · 제목 66 · 부제 112) · 본문(136/160 – 648) · 바닥(구분선 668 · 로고 680).

카드 항목(`card`)은 필드 묶음이다. 상자에 `part` 가 없으면 카드 전체(태그 · 제목 · 설명 · 항목 · 수치)를,
`part` 가 있으면 그 필드 하나만 그린다(예: 행형 비교의 왼쪽/오른쪽 칸).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .geometry import CW, GAP, X0, Y1, Builder, cols, f, frame, rows

# ── 필드 묶음 ───────────────────────────────────────────

KEY_LABELS = {
    "no": "번호", "tag": "태그", "title": "제목", "body": "설명", "kpi": "수치", "image": "이미지", "bullets": "항목",
    "note": "메모", "label": "구분", "role": "역할", "name": "이름", "when": "시점", "time": "시각", "so": "그래서(시사점)",
    "left": "왼쪽", "right": "오른쪽", "before": "도입 전", "after": "도입 후", "change": "변화", "quote": "현장의 말",
    "who": "말한 사람", "product": "제품", "value": "가치", "solution": "솔루션", "space": "공간", "x": "가로 위치(0–100)",
    "y": "세로 위치(0–100)", "size": "크기(0–100)", "owner": "담당", "days": "소요", "qty": "수량", "model": "모델",
    "spec": "사양", "chips": "칩(짧은 단어)", "sub": "보조 설명", "letter": "기호", "share": "비중", "need": "니즈",
    "start": "시작(0–100)", "end": "끝(0–100)", "mid": "가운데", "pain": "불편", "action": "행동", "touchpoint": "접점",
    "opportunity": "기회", "emotion": "감정(-2–2)", "kpi2": "수치 2", "metric": "지표", "result": "성과",
}


def F(**spec: Any) -> list[dict[str, Any]]:
    """F(title=28, body=90, kpi='kpi', image='image:C') → 필드 정의 목록."""
    out = []
    for key, v in spec.items():
        label = KEY_LABELS.get(key, key)
        if isinstance(v, int):
            out.append(f(key, "text", label, v))
        elif v == "kpi":
            out.append(f(key, "kpi", label))
        elif v == "bullets":
            out.append(f(key, "bullets", label))
        elif v == "number":
            out.append(f(key, "number", label))
        elif isinstance(v, str) and v.startswith("image"):
            grade = v.split(":", 1)[1] if ":" in v else None
            out.append(f(key, "image", label, image_grade=grade))
        else:
            raise ValueError(f"field spec {key}={v}")
    return out


def items(b: Builder, key: str, label: str, n: int, fields: list[dict[str, Any]], *, required: bool = True) -> str:
    return b.slot(key, "card", label, required=required, count=n, fields=fields)


def img_slot(b: Builder, key: str, label: str, grade: str = "A", *, count: int | None = None, required: bool = False,
             hint: str | None = None) -> str:
    return b.slot(key, "image", label, required=required, count=count, image_grade=grade, hint=hint)


# ── 공통 틀 밖(표지 · 목차 · 간지 · 마무리) ─────────────────

def cover_slots(b: Builder) -> None:
    b.slot("eyebrow", "text", "윗줄(예: B2B PROPOSAL · 제안서 종류)", max_chars=40, default="B2B PROPOSAL", default_en="B2B PROPOSAL")
    b.slot("title", "text", "제안서 제목", required=True, max_chars=40)
    b.slot("subtitle", "text", "부제(제안 범위 · 한 줄 요약)", max_chars=70)
    b.slot("customer", "text", "고객사", max_chars=30)
    b.slot("date", "text", "날짜(예: 2026.10)", max_chars=20)
    b.slot("presenter", "text", "제안사 · 담당(예: 삼성전자 B2B)", max_chars=40, default="Samsung Electronics", default_en="Samsung Electronics")
    b.slot("logo", "logo", "고객사 로고 — 비우면 디자인 로고")


def a_cover_split(b: Builder, **_: Any) -> None:            # C01
    cover_slots(b)
    img_slot(b, "image", "표지 이미지(공간 · 제품)", "A", hint="비우면 디자인의 표지 이미지")
    b.box("image", 640, 0, 640, 720, "image_full")
    b.box("logo", 64, 64, 140, 40, "logo")
    b.box("eyebrow", 64, 232, 520, 20, "eyebrow")
    b.box("title", 64, 262, 540, 150, "cover_title")
    b.box("subtitle", 64, 420, 540, 56, "subtitle")
    b.deco("rule_brand", 64, 520, 48, 4)
    b.box("customer", 64, 548, 520, 24, "heading")
    b.box("presenter", 64, 580, 520, 20, "small")
    b.box("date", 64, 606, 520, 20, "small")


def a_cover_full(b: Builder, **_: Any) -> None:             # C02
    cover_slots(b)
    img_slot(b, "image", "표지 이미지(풀블리드)", "A")
    b.box("image", 0, 0, 1280, 460, "image_full")
    b.deco("rule_brand", 0, 460, 1280, 6)
    b.box("logo", 64, 40, 110, 30, "logo_plate")
    b.box("eyebrow", 64, 500, 860, 20, "eyebrow")
    b.box("title", 64, 526, 860, 68, "cover_title")
    b.box("subtitle", 64, 600, 860, 26, "subtitle")
    b.box("customer", 960, 540, 256, 26, "heading", align="right")
    b.box("date", 960, 578, 256, 20, "small", align="right")
    b.box("presenter", 960, 604, 256, 20, "small", align="right")


def a_cover_type(b: Builder, **_: Any) -> None:             # C03
    cover_slots(b)
    b.box("logo", 1076, 64, 140, 40, "logo")
    b.box("eyebrow", 64, 200, 900, 20, "eyebrow")
    b.box("title", 64, 236, 1000, 180, "cover_title_xl")
    b.box("subtitle", 64, 430, 900, 30, "subtitle")
    b.deco("rule", 64, 560, 1152, 1)
    b.box("customer", 64, 584, 500, 24, "heading")
    b.box("presenter", 64, 616, 500, 20, "small")
    b.box("date", 916, 588, 300, 20, "small", align="right")


def a_cover_collage(b: Builder, **_: Any) -> None:          # C08
    cover_slots(b)
    img_slot(b, "images", "콜라주 이미지 3(공간 · 사용 장면 · 제품)", "A", count=3)
    b.slot("scope", "bullets", "제안 범위 칩(최대 3)", count=3)
    b.box("images", 596, 24, 344, 624, "image", index=0)
    b.box("images", 954, 24, 302, 352, "image", index=1)
    b.box("images", 954, 390, 302, 258, "image_contain", index=2)
    b.box("logo", 64, 64, 140, 40, "logo")
    b.box("eyebrow", 64, 200, 480, 20, "eyebrow")
    b.box("title", 64, 230, 500, 170, "cover_title")
    b.box("subtitle", 64, 410, 500, 50, "subtitle")
    b.box("scope", 64, 480, 500, 34, "chips")
    b.box("customer", 64, 580, 480, 24, "heading")
    b.box("date", 64, 612, 480, 20, "small")
    b.box("presenter", 64, 640, 480, 20, "small")


def a_cover_product(b: Builder, **_: Any) -> None:          # C09
    cover_slots(b)
    img_slot(b, "image", "대표 제품 컷(누끼)", "C", required=True)
    b.slot("kpis", "kpi", "대표 수치 3", count=3)
    b.deco("ring", 688, 76, 540, 540)
    b.box("image", 768, 36, 380, 640, "image_contain")
    b.box("logo", 64, 64, 140, 40, "logo")
    b.box("eyebrow", 64, 176, 560, 20, "eyebrow")
    b.box("title", 64, 206, 580, 160, "cover_title")
    b.box("subtitle", 64, 374, 560, 50, "subtitle")
    for i, (x, w) in enumerate(cols(3, 64, 560, 16)):
        b.box("kpis", x, 450, w, 96, "kpi_tile", index=i)
    b.box("customer", 64, 584, 560, 24, "heading")
    b.box("date", 64, 616, 560, 20, "small")
    b.box("presenter", 64, 644, 560, 20, "small")


def a_toc(b: Builder, n: int = 8, **_: Any) -> None:        # C04
    b.slot("eyebrow", "text", "윗줄", default="CONTENTS", default_en="CONTENTS", max_chars=30)
    b.slot("title", "text", "제목", default="목차", default_en="Contents", max_chars=20)
    items(b, "items", "목차 항목(섹션)", n, F(no=4, title=24, body=60))
    b.slot("footer", "text", "바닥글", max_chars=70)
    b.slot("logo", "logo", "고객사 로고")
    b.box("eyebrow", 64, 64, 400, 20, "eyebrow")
    b.box("title", 64, 92, 400, 60, "cover_title")
    for i in range(n):
        c, r = divmod(i, 4)
        b.box("items", 64 + c * 588, 200 + r * 108, 564, 92, "toc_row", index=i)
    b.box("logo", 64, 680, 72, 20, "logo")
    b.box("footer", 148, 680, 860, 20, "footer")


def a_toc_thumbs(b: Builder, n: int = 6, **_: Any) -> None:  # C10
    b.slot("eyebrow", "text", "윗줄", default="CONTENTS", default_en="CONTENTS", max_chars=30)
    b.slot("title", "text", "제목", default="목차", default_en="Contents", max_chars=20)
    items(b, "items", "섹션(대표 이미지 포함)", n, F(no=4, title=22, body=50, image="image:A"))
    b.slot("footer", "text", "바닥글", max_chars=70)
    b.slot("logo", "logo", "고객사 로고")
    b.box("eyebrow", 64, 44, 400, 20, "eyebrow")
    b.box("title", 64, 66, 600, 42, "title")
    for i in range(n):
        c, r = i % 3, i // 3
        b.box("items", 64 + c * 392, 136 + r * 256, 368, 236, "card_img", index=i)
    b.box("logo", 64, 680, 72, 20, "logo")
    b.box("footer", 148, 680, 860, 20, "footer")


def divider_slots(b: Builder) -> None:
    b.slot("no", "text", "섹션 번호(예: 01)", max_chars=4)
    b.slot("title", "text", "섹션 이름", required=True, max_chars=30)
    b.slot("subtitle", "text", "섹션이 말하는 것", max_chars=70)
    b.slot("sheets", "bullets", "이 섹션의 시트(최대 6)", count=6)


def a_divider_number(b: Builder, **_: Any) -> None:         # C05
    divider_slots(b)
    b.deco("panel_brand", 0, 0, 1280, 720)
    b.box("no", 96, 150, 600, 220, "divider_no")
    b.box("title", 96, 390, 900, 70, "divider_title")
    b.box("subtitle", 96, 470, 900, 30, "subtitle_inv")
    b.box("sheets", 96, 540, 1088, 100, "chips_inv")


def a_divider_image(b: Builder, **_: Any) -> None:          # C06
    divider_slots(b)
    img_slot(b, "image", "섹션 대표 이미지", "A")
    b.box("image", 0, 0, 560, 720, "image_full")
    b.box("no", 640, 150, 300, 120, "divider_no_brand")
    b.box("title", 640, 290, 576, 70, "divider_title_ink")
    b.box("subtitle", 640, 370, 576, 50, "subtitle")
    b.box("sheets", 640, 450, 576, 200, "list")


def a_divider_photo(b: Builder, **_: Any) -> None:          # C11
    divider_slots(b)
    img_slot(b, "image", "섹션 장면 사진(풀블리드)", "A", required=True)
    b.box("image", 0, 0, 1280, 720, "image_full")
    b.deco("panel_dark_alpha", 0, 500, 1280, 220)
    b.box("no", 64, 528, 140, 60, "divider_no_small")
    b.box("title", 64, 590, 700, 50, "divider_title")
    b.box("subtitle", 64, 646, 700, 26, "subtitle_inv")
    b.box("sheets", 820, 540, 396, 140, "list_inv")


def closing_slots(b: Builder) -> None:
    b.slot("eyebrow", "text", "윗줄", default="THANK YOU", default_en="THANK YOU", max_chars=30)
    b.slot("title", "text", "마무리 메시지", required=True, max_chars=40)
    b.slot("subtitle", "text", "다음 단계 · 요청", max_chars=90)
    items(b, "contacts", "연락처", 4, F(name=20, role=30, body=40), required=False)
    b.slot("logo", "logo", "고객사 로고")


def a_closing(b: Builder, **_: Any) -> None:                # C07
    closing_slots(b)
    b.box("logo", 64, 64, 140, 40, "logo")
    b.box("eyebrow", 64, 200, 600, 20, "eyebrow")
    b.box("title", 64, 232, 900, 120, "cover_title")
    b.box("subtitle", 64, 370, 900, 50, "subtitle")
    for i, (x, w) in enumerate(cols(4)):
        b.box("contacts", x, 500, w, 120, "contact", index=i)


def a_closing_image(b: Builder, **_: Any) -> None:          # C12
    closing_slots(b)
    img_slot(b, "image", "도입 후 모습(생성 시안 가능)", "A", required=True)
    b.box("image", 0, 0, 760, 720, "image_full")
    b.box("eyebrow", 808, 120, 408, 20, "eyebrow")
    b.box("title", 808, 150, 408, 150, "cover_title")
    b.box("subtitle", 808, 310, 408, 70, "subtitle")
    for i in range(4):
        b.box("contacts", 808, 400 + i * 66, 408, 58, "contact_row", index=i)
    b.box("logo", 808, 64, 140, 40, "logo")


# ── MI ──────────────────────────────────────────────────

def a_kpi_band(b: Builder, section: str = "mi", n: int = 4, **_: Any) -> None:     # MS-A
    y = frame(b, section, sub=True)
    b.slot("kpis", "kpi", "핵심 수치(값 · 단위 · 이름 · 보조)", required=True, count=n)
    b.slot("message", "text", "그래서 — 수치가 말하는 것 한 문장", max_chars=60)
    b.slot("bullets", "bullets", "근거 · 시사점(최대 3)", count=3)
    for i, (x, w) in enumerate(cols(n)):
        b.box("kpis", x, y + 16, w, 236, "kpi_card", index=i)
    b.deco("panel_tint", 64, 452, 1152, 196)
    b.box("message", 96, 476, 1088, 40, "heading")
    b.box("bullets", 96, 526, 1088, 108, "bullets")


def a_chart_insights(b: Builder, section: str = "mi", n: int = 3, chart_kind: str = "bar", sub: bool = True,
                     panel_w: int = 760, **_: Any) -> None:   # MS-B, MS-D, CP-B, CM-C …
    y = frame(b, section, sub=sub)
    b.slot("chart", "chart", f"차트({chart_kind})", required=True, hint=f"type={chart_kind}")
    b.slot("chart_title", "text", "차트 제목 · 단위", max_chars=40)
    items(b, "insights", "인사이트", n, F(no=3, title=24, body=80, kpi="kpi"))
    b.deco("panel", 64, y, panel_w, Y1 - y)
    b.box("chart_title", 88, y + 18, panel_w - 48, 22, "heading_sm")
    b.box("chart", 88, y + 50, panel_w - 48, Y1 - y - 70, "chart")
    x = 64 + panel_w + 24
    for i, (yy, hh) in enumerate(rows(n, y, Y1 - y, 16)):
        b.box("insights", x, yy, 1216 - x, hh, "card_white", index=i)


def a_plot_insights(b: Builder, section: str = "mi", n_points: int = 6, n: int = 3, quad: bool = False,
                    sub: bool = True, **_: Any) -> None:     # MS-D, CP-B, TR-C
    y = frame(b, section, sub=sub)
    items(b, "points", "점(이름 · x · y · 크기)", n_points, F(title=16, x="number", y="number", size="number", tag=10))
    b.slot("axis_x", "text", "가로축 이름", max_chars=24, default="→")
    b.slot("axis_y", "text", "세로축 이름", max_chars=24, default="↑")
    if quad:
        b.slot("quadrants", "text", "4분면 이름(왼쪽 위부터)", count=4, max_chars=14)
    items(b, "insights", "인사이트", n, F(no=3, title=24, body=80))
    b.deco("panel", 64, y, 760, Y1 - y)
    b.box("points", 96, y + 24, 700, Y1 - y - 60, "plot_quad" if quad else "plot", quadrants="quadrants" if quad else None)
    b.box("axis_x", 96, Y1 - 32, 700, 20, "caption", align="center")
    b.box("axis_y", 72, y + 4, 300, 20, "caption")
    for i, (yy, hh) in enumerate(rows(n, y, Y1 - y, 16)):
        b.box("insights", 848, yy, 368, hh, "card_white", index=i)


def a_circles_rows(b: Builder, section: str = "mi", **_: Any) -> None:            # MS-C
    y = frame(b, section, sub=True)
    b.slot("tiers", "kpi", "규모 계층(TAM · SAM · SOM)", required=True, count=3)
    items(b, "rows", "계층 설명", 3, F(label=8, title=24, body=70))
    b.slot("message", "text", "노릴 수 있는 몫 — 한 문장", max_chars=60)
    b.box("tiers", 84, y + 8, 560, 472, "kpi_circle", index=0)
    b.box("tiers", 164, y + 128, 400, 352, "kpi_circle", index=1)
    b.box("tiers", 244, y + 248, 240, 232, "kpi_circle", index=2)
    for i, (yy, hh) in enumerate(rows(3, y, 360, 12)):
        b.box("rows", 750, yy, 466, hh, "card_row_text", index=i)
    b.deco("panel_tint", 750, 552, 466, 96)
    b.box("message", 774, 568, 418, 64, "body_strong")


def a_drivers_outlook(b: Builder, section: str = "mi", **_: Any) -> None:        # MS-E
    y = frame(b, section)
    items(b, "drivers", "성장 동인", 3, F(no=3, title=24, body=90, kpi="kpi"))
    b.slot("outlook_title", "text", "전망 — 한 문장", max_chars=40)
    b.slot("outlook", "kpi", "전망 수치(지금 · 전망)", count=2)
    b.slot("outlook_body", "text", "그래서 고객에게", max_chars=120)
    for i, (yy, hh) in enumerate(rows(3, y, Y1 - y, 16)):
        b.box("drivers", 64, yy, 662, hh, "card", index=i)
    b.deco("panel_brand", 750, y, 466, Y1 - y)
    b.box("outlook_title", 778, y + 28, 410, 70, "heading_inv")
    b.box("outlook", 778, y + 110, 195, 150, "kpi_inv", index=0)
    b.box("outlook", 993, y + 110, 195, 150, "kpi_inv", index=1)
    b.box("outlook_body", 778, y + 290, 410, 190, "body_inv")


def a_timeline(b: Builder, section: str = "mi", n: int = 4, band: bool = True, sub: bool = False, **_: Any) -> None:  # TR-A, OP-A
    y = frame(b, section, sub=sub)
    items(b, "steps", "단계(시점 · 제목 · 설명)", n, F(when=12, title=22, body=90, tag=12))
    bottom = 500 if band else Y1
    b.deco("track", 64, y + 40, 1152, 4)
    for i, (x, w) in enumerate(cols(n)):
        b.deco("marker", x + 8, y + 30, 24, 24)
        b.box("steps", x, y + 72, w, bottom - y - 72, "card", index=i)
    if band:
        b.slot("message", "text", "그래서 — 다음 방향 한 문장", max_chars=70)
        b.slot("message_label", "text", "띠 라벨", max_chars=10, default="방향", default_en="Direction")
        b.deco("panel_tint", 64, 520, 1152, 128)
        b.box("message_label", 92, 544, 160, 26, "chip_brand")
        b.box("message", 92, 580, 1096, 52, "heading")


def a_trend_cards(b: Builder, section: str = "mi", n: int = 3, **_: Any) -> None:  # TR-B
    y = frame(b, section)
    items(b, "trends", "트렌드(제목 · 설명 · 근거 · 그래서)", n,
          F(no=3, title=24, body=90, bullets="bullets", so=70))
    b.slot("so_label", "text", "시사점 라벨", default="그래서 고객에게", default_en="So, for the customer", max_chars=20)
    for i, (x, w) in enumerate(cols(n)):
        b.box("trends", x, y, w, 340, "card", index=i)
        b.deco("arrow_down", x + w / 2 - 12, y + 348, 24, 22)
        b.box("trends", x, y + 376, w, Y1 - y - 376, "card_tint", index=i, part="so", label_slot="so_label")


def a_summary_3col(b: Builder, section: str = "mi", **_: Any) -> None:          # CB-A
    y = frame(b, section, sub=False)
    b.slot("summary", "text", "한 줄 요약", required=True, max_chars=70)
    items(b, "columns", "3단(제목 · 항목)", 3, F(tag=14, title=24, bullets="bullets", kpi="kpi"))
    b.deco("panel_dark", 64, y + 40, 1152, 64)
    b.box("summary", 92, y + 52, 1096, 40, "heading_inv")
    for i, (x, w) in enumerate(cols(3)):
        b.box("columns", x, y + 128, w, Y1 - y - 128, "card", index=i)


def a_tree(b: Builder, section: str = "mi", n_branch: int = 3, n_leaf: int = 5, root_style: str = "card_dark",
           headers: tuple[str, str, str] = ("경영 목표", "전략 방향", "실행 과제"), sub: bool = False, **_: Any) -> None:  # CB-B, CH-C
    y = frame(b, section, sub=sub)
    b.slot("headers", "text", "열 머리 3", count=3, max_chars=14, default=list(headers))
    b.slot("root", "card", "뿌리(목표 · 현상)", required=True, fields=F(tag=16, title=30, kpi="kpi", note=40))
    items(b, "branches", "가지(전략 · 직접 원인)", n_branch, F(no=3, title=22, body=50))
    items(b, "leaves", "잎(과제 · 근본 원인)", n_leaf, F(title=28, body=50, tag=10))
    top = y + 36
    for i, x in enumerate((64, 368, 732)):
        b.box("headers", x, y, 280, 20, "label", index=i)
    b.box("root", 64, top + 20, 240, Y1 - top - 40, root_style)
    b.deco("connector_h", 304, (top + Y1) / 2, 32, 2)
    b.deco("connector_v", 336, top + 50, 2, Y1 - top - 100)
    for i, (yy, hh) in enumerate(rows(n_branch, top, Y1 - top, 18)):
        b.deco("connector_h", 336, yy + hh / 2, 32, 2)
        b.box("branches", 368, yy, 300, hh, "card", index=i)
    b.deco("connector_v", 700, top + 30, 2, Y1 - top - 60)
    for i, (yy, hh) in enumerate(rows(n_leaf, top, Y1 - top, 12)):
        b.deco("connector_h", 700, yy + hh / 2, 32, 2)
        b.box("leaves", 732, yy, 484, hh, "card_white", index=i)


def a_process_pains(b: Builder, section: str = "mi", n: int = 5, n_pain: int = 3, **_: Any) -> None:  # CB-C
    y = frame(b, section, sub=True)
    items(b, "steps", "업무 단계(이름 · 담당 · 소요)", n, F(no=3, title=14, owner=14, days=8))
    items(b, "pains", "문제(해당 단계 아래)", n_pain, F(no=2, title=24, body=50))
    b.slot("totals", "kpi", "합계 수치", count=3)
    b.slot("totals_label", "text", "합계 라벨", max_chars=20, default="한 번에 드는 것")
    cw = (1152 - 38 * (n - 1)) / n
    xs = [64 + i * (cw + 38) for i in range(n)]
    for i, x in enumerate(xs):
        b.box("steps", x, y + 16, cw, 168, "card_step", index=i)
        if i < n - 1:
            b.deco("chevron", x + cw + 5, y + 86, 28, 28)
    at = [1, 2, n - 1] if n_pain == 3 and n >= 4 else list(range(n_pain))
    for i, k in enumerate(at[:n_pain]):
        b.deco("connector_v", xs[k] + cw / 2, y + 184, 2, 30)
        b.box("pains", xs[k], y + 214, cw, 150, "card_outline_ink", index=i)
    b.deco("panel", 64, 568, 1152, 72)
    b.box("totals_label", 92, 590, 220, 28, "heading_sm")
    for i, (x, w) in enumerate(cols(3, 330, 860, 16)):
        b.box("totals", x, 578, w, 52, "kpi_inline", index=i)


def a_swot(b: Builder, section: str = "mi", **_: Any) -> None:                 # CB-D
    y = frame(b, section)
    items(b, "quadrants", "S · W · O · T(기호 · 이름 · 항목)", 4, F(letter=1, title=8, bullets="bullets"))
    b.slot("axes", "text", "축 이름(도움 · 위험 · 내부 · 외부)", count=4, max_chars=10,
           default=["도움이 되는 것", "위험한 것", "내부", "외부"])
    b.slot("message", "text", "제안 방향 — S·O 를 잇는 한 문장", max_chars=70)
    b.box("axes", 128, y + 3, 536, 22, "label_brand", index=0, align="center")
    b.box("axes", 680, y + 3, 536, 22, "label", index=1, align="center")
    b.box("axes", 64, y + 36, 48, 192, "axis_v", index=2)
    b.box("axes", 64, y + 244, 48, 192, "axis_v", index=3)
    pos = [(128, y + 36, "card_tint"), (680, y + 36, "card"), (128, y + 244, "card_tint"), (680, y + 244, "card")]
    for i, (x, yy, st) in enumerate(pos):
        b.box("quadrants", x, yy, 536, 192, "card_swot" if st == "card" else "card_swot_tint", index=i)
    b.deco("panel_tint", 64, 592, 1152, 56)
    b.box("message", 92, 604, 1096, 32, "band_text")


def a_personas(b: Builder, section: str = "mi", n: int = 3, image: bool = False, header: bool = False,
               sub: bool = False, **_: Any) -> None:          # US-A, VP-D, VP-H(이미지)
    y = frame(b, section, sub=sub)
    fl = F(role=14, name=20, body=80, bullets="bullets", quote=60, kpi="kpi")
    if image:
        fl += F(image="image:C")
    items(b, "people", "사람(역할 · 이름 · 설명 · 니즈 · 말)", n, fl)
    if header:
        b.slot("message", "text", "공통 메시지(머리 띠)", max_chars=40)
        b.box("message", 370, y + 2, 540, 46, "pill_brand")
        y += 64
    for i, (x, w) in enumerate(cols(n)):
        b.box("people", x, y, w, Y1 - y, "card_img" if image else "card_person", index=i)


def a_journey(b: Builder, section: str = "mi", n: int = 5, **_: Any) -> None:  # US-B
    y = frame(b, section)
    items(b, "stages", "여정 단계(이름 · 행동 · 접점 · 감정 · 불편 · 기회)", n,
          F(title=12, action=40, touchpoint=24, emotion="number", pain=40, opportunity=40))
    b.slot("row_labels", "text", "행 이름", count=5, max_chars=8, default=["단계", "행동", "접점", "감정", "기회"])
    rows_y = [(y, 44), (y + 56, 99), (y + 157, 143), (y + 302, 75), (y + 379, Y1 - y - 379)]
    parts = ["title", "action", "touchpoint", "emotion", "opportunity"]
    cw = (1152 - 132 - 8 * (n - 1)) / n
    for r, ((yy, hh), part) in enumerate(zip(rows_y, parts)):
        b.box("row_labels", 64, yy, 120, hh, "row_label", index=r)
        if part == "emotion":
            b.box("stages", 196, yy, 1020, hh, "emotion_curve", part="emotion")
            continue
        for i in range(n):
            st = "cell_head" if part == "title" else ("cell_tint" if part == "opportunity" else "cell")
            b.box("stages", 196 + i * (cw + 8), yy, cw, hh, st, index=i, part=part)


def a_donut_needs(b: Builder, section: str = "mi", n: int = 4, **_: Any) -> None:  # US-C
    y = frame(b, section, sub=True)
    b.slot("chart", "chart", "구성 비율(도넛)", required=True, hint="type=doughnut")
    items(b, "segments", "사용자 구성(이름 · 비중 · 니즈 · 그래서)", n, F(title=14, share=6, need=50, so=50))
    b.slot("headers", "text", "표 머리", count=4, max_chars=10, default=["사용자", "비중", "니즈", "그래서"])
    b.deco("panel", 64, y, 440, Y1 - y)
    b.box("chart", 84, y + 20, 400, Y1 - y - 40, "chart")
    hx = [(528, 160), (700, 80), (792, 200), (1004, 212)]
    for i, (x, w) in enumerate(hx):
        b.box("headers", x, y, w, 24, "label", index=i)
    for i, (yy, hh) in enumerate(rows(n, y + 32, Y1 - y - 32, 8)):
        for (x, w), part in zip(hx, ("title", "share", "need", "so")):
            b.box("segments", x, yy, w, hh, "cell_strong" if part == "title" else ("cell_num" if part == "share" else ("cell_tint" if part == "so" else "cell")), index=i, part=part)


def a_table(b: Builder, section: str = "mi", sub: bool = True, style: str = "table", band: bool = False,
            side: int = 0, label: str = "표", **_: Any) -> None:   # CP-A, CM-A, SC-A, SC-B, BM-A, AX-A …
    y = frame(b, section, sub=sub)
    b.slot("table", "table", label, required=True)
    bottom = 576 if band else Y1
    tw = 1152 - (side + 24 if side else 0)
    b.box("table", 64, y, tw, bottom - y, style)
    if side:
        items(b, "notes", "옆 메모", 3, F(no=3, title=22, body=70), required=False)
        for i, (yy, hh) in enumerate(rows(3, y, bottom - y, 12)):
            b.box("notes", 64 + tw + 24, yy, side, hh, "card_white", index=i)
    if band:
        b.slot("message", "text", "표가 말하는 것 — 한 문장", max_chars=80)
        b.deco("panel_tint", 64, 592, 1152, 56)
        b.box("message", 92, 604, 1096, 32, "band_text")


def a_stacked_table(b: Builder, section: str = "mi", **_: Any) -> None:       # CP-C
    y = frame(b, section)
    b.slot("chart", "chart", "점유율 추이(100% 누적 막대)", required=True, hint="type=stacked100")
    b.slot("table", "table", "공급사 표(점유율 · 변화 · 주력)", required=True)
    b.deco("panel", 64, y, 564, Y1 - y)
    b.box("chart", 84, y + 20, 524, Y1 - y - 40, "chart")
    b.box("table", 652, y, 564, Y1 - y, "table")


def a_funnel(b: Builder, section: str = "mi", **_: Any) -> None:              # IM-A
    y = frame(b, section)
    b.slot("headers", "text", "열 머리 3", count=3, max_chars=10, default=["발견", "시사점", "제안 방향"])
    items(b, "findings", "발견(영역 · 내용)", 4, F(tag=6, title=50))
    items(b, "implications", "시사점", 2, F(tag=10, title=30, body=60, chips="bullets"))
    b.slot("direction", "card", "제안 방향(하나로)", required=True, fields=F(tag=10, title=40, bullets="bullets"))
    for i, x in enumerate((64, 488, 864)):
        b.box("headers", x, y, 320, 24, "label_brand" if i == 2 else "label", index=i)
    b.deco("funnel", 432, y + 36, 432, Y1 - y - 36)
    for i, (yy, hh) in enumerate(rows(4, y + 36, Y1 - y - 36, 12)):
        b.box("findings", 64, yy, 368, hh, "card_finding", index=i)
    for i, yy in enumerate((y + 76, y + 282)):
        b.box("implications", 488, yy, 320, 190, "card_tint", index=i)
    b.deco("circle_arrow", 440, y + 254, 40, 40)
    b.deco("circle_arrow_brand", 816, y + 254, 40, 40)
    b.box("direction", 864, y + 116, 352, 316, "card_brand", index=None)


def a_quad_center(b: Builder, section: str = "mi", center: bool = True, n: int = 4, sub: bool = False,
                  **_: Any) -> None:   # IM-B, ST-B, VP-B4(2×2)
    y = frame(b, section, sub=sub)
    items(b, "quadrants", "4분면 카드", n, F(tag=12, title=24, body=70, bullets="bullets", kpi="kpi"))
    cw, ch = 564, (Y1 - y - 24) / 2
    pos = [(64, y), (652, y), (64, y + ch + 24), (652, y + ch + 24)]
    for i, (x, yy) in enumerate(pos[:n]):
        b.box("quadrants", x, yy, cw, ch, "card", index=i)
    if center:
        b.slot("conclusion", "text", "결론(가운데)", required=True, max_chars=40)
        mid = y + ch + 12
        b.box("conclusion", 534, mid - 106, 212, 212, "circle_brand")


# ── MI 업종판(A 시장 · 트렌드 / B 고객 비즈니스 · 운영 과제 / C 사용자 여정) ─────────

def a_market_trend(b: Builder, section: str = "mi", **_: Any) -> None:         # MI-XX-A
    y = frame(b, section, sub=True)
    b.slot("chart", "chart", "시장 규모 추이(연도별 막대)", required=True, hint="type=bar · 마지막 해 강조")
    b.slot("chart_title", "text", "차트 제목", max_chars=30)
    b.slot("chart_note", "text", "단위 · 출처", max_chars=40)
    b.slot("kpis", "kpi", "핵심 수치 3", count=3)
    b.slot("headers", "text", "오른쪽 머리 2", count=2, max_chars=20, default=["업계를 움직이는 흐름", "그래서 고객에게"])
    items(b, "trends", "흐름 4(제목 · 설명 · 그래서 · 지표)", 4, F(no=3, title=20, body=70, so=50, kpi="kpi"))
    b.deco("panel", 64, y, 466, Y1 - y)
    b.box("chart_title", 88, y + 18, 418, 22, "heading_sm")
    b.box("chart_note", 88, y + 42, 418, 16, "caption")
    b.box("chart", 88, y + 70, 418, 270, "chart")
    for i, (x, w) in enumerate(cols(3, 80, 434, 10)):
        b.box("kpis", x, y + 352, w, 92, "kpi_tile", index=i)
    b.box("headers", 554, y, 330, 20, "label", index=0)
    b.box("headers", 898, y, 318, 20, "label_brand", index=1)
    for i, (yy, hh) in enumerate(rows(4, y + 26, Y1 - y - 26, 8)):
        b.box("trends", 554, yy, 330, hh, "card_white_row", index=i)
        b.deco("arrow", 888, yy + hh / 2 - 6, 18, 12)
        b.box("trends", 910, yy, 306, hh, "card_tint", index=i, part="so")


def a_biz_ops(b: Builder, section: str = "mi", n: int = 5, n_issue: int = 6, **_: Any) -> None:  # MI-XX-B
    y = frame(b, section, sub=True)
    items(b, "chain", "사업 흐름(단계 · 매출 · KPI)", n, F(no=3, title=14, body=40, kpi="kpi"))
    items(b, "issues", "운영 과제(단계 · 과제 · 영향)", n_issue, F(tag=12, title=26, body=60, kpi="kpi"))
    b.slot("chain_label", "text", "흐름 라벨", max_chars=20, default="돈이 되는 흐름")
    b.slot("issues_label", "text", "과제 라벨", max_chars=20, default="운영 과제")
    b.box("chain_label", 64, y, 400, 20, "label")
    cw = (1152 - 28 * (n - 1)) / n
    for i in range(n):
        x = 64 + i * (cw + 28)
        b.box("chain", x, y + 28, cw, 170, "card_step", index=i)
        if i < n - 1:
            b.deco("chevron", x + cw + 2, y + 100, 24, 24)
    b.box("issues_label", 64, y + 216, 400, 20, "label_brand")
    per = n_issue // 2 if n_issue > 3 else n_issue
    for i in range(n_issue):
        r, c = divmod(i, per)
        cws = cols(per)
        x, w = cws[c]
        hh = (Y1 - (y + 244) - 12 * (n_issue // per - 1)) / max(1, n_issue // per)
        b.box("issues", x, y + 244 + r * (hh + 12), w, hh, "card", index=i)


def a_user_journey(b: Builder, section: str = "mi", n: int = 5, n_seg: int = 3, **_: Any) -> None:  # MI-XX-C
    y = frame(b, section, sub=True)
    items(b, "segments", "사용자 · 이해관계자(이름 · 비중 · 동기)", n_seg, F(title=14, share=6, body=40))
    b.slot("segments_label", "text", "왼쪽 머리", max_chars=16, default="누가 쓰나")
    items(b, "stages", "여정 단계(이름 · 순간 · 불편 · 삼성이 바꾸는 것)", n,
          F(title=12, action=40, pain=40, opportunity=40))
    b.slot("row_labels", "text", "행 이름", count=3, max_chars=10, default=["순간", "불편", "바꾸는 것"])
    b.deco("panel", 64, y, 270, Y1 - y)
    b.box("segments_label", 82, y + 16, 234, 20, "label")
    for i, (yy, hh) in enumerate(rows(n_seg, y + 46, Y1 - y - 62, 10)):
        b.box("segments", 82, yy, 234, hh, "tile", index=i)
    x0 = 358 + 96
    cw = (1216 - x0 - 8 * (n - 1)) / n
    rws = [("title", y, 44, "cell_head"), ("action", y + 52, 140, "cell"), ("pain", y + 200, 140, "cell_outline"),
           ("opportunity", y + 348, Y1 - y - 348, "cell_tint")]
    for r, (part, yy, hh, st) in enumerate(rws):
        if r > 0:
            b.box("row_labels", 358, yy, 88, hh, "row_label", index=r - 1)
        for i in range(n):
            b.box("stages", x0 + i * (cw + 8), yy, cw, hh, st, index=i, part=part)


# ── VP · 고객 과제 · 기대 효과 ───────────────────────────────

def a_challenge_cards(b: Builder, section: str = "vp", n: int = 3, **_: Any) -> None:   # CH-A
    y = frame(b, section)
    items(b, "items", "과제(종류 · 제목 · 설명 · 현장의 말 · 영향 수치)", n,
          F(no=3, tag=8, title=26, body=80, quote=50, who=20, kpi="kpi"))
    for i, (x, w) in enumerate(cols(n)):
        b.box("items", x, y, w, Y1 - y, "card_challenge", index=i)


def a_rows_arrow(b: Builder, section: str = "vp", n: int = 4, change: bool = False, sub: bool = True,
                 headers: tuple[str, ...] = ("구분", "지금", "바라는 모습"), right_style: str = "cell_tint_strong",
                 kpi_cells: bool = False, image: bool = False, **_: Any) -> None:  # CH-B, VP-A, SF-B, P-K, P-N
    y = frame(b, section, sub=sub)
    ft = "kpi" if kpi_cells else 90
    spec: dict[str, Any] = {"label": 14, "left": ft, "right": ft}
    if change:
        spec["change"] = 12
    if image:
        spec["image"] = "image:C"
    items(b, "rows", "행(구분 · 왼쪽 · 오른쪽" + (" · 변화" if change else "") + ")", n, F(**spec))
    nh = len(headers) + (1 if change else 0)
    b.slot("headers", "text", "열 머리", count=nh, max_chars=12, default=list(headers) + (["변화"] if change else []))
    lw = 150 if not image else 220
    rw = 120 if change else 0
    mid = (1152 - lw - 44 - rw - 36) / 2
    xl = 64 + lw + 12
    xr = xl + mid + 44 + 12
    b.box("headers", 64, y + 12, lw, 30, "label", index=0)
    b.box("headers", xl, y + 12, mid, 30, "pill_gray", index=1)
    b.box("headers", xr, y + 12, mid, 30, "pill_brand_left", index=2)
    if change:
        b.box("headers", 1216 - rw, y + 12, rw, 30, "label", index=3, align="center")
    top = y + 56
    for i, (yy, hh) in enumerate(rows(n, top, Y1 - top, 0)):
        b.deco("rule", 64, yy, 1152, 1)
        if image:
            b.box("rows", 64, yy + 10, 88, hh - 20, "image_contain", index=i, part="image")
            b.box("rows", 160, yy, lw - 96, hh, "row_label_strong", index=i, part="label")
        else:
            b.box("rows", 64, yy, lw, hh, "row_label_strong", index=i, part="label")
        b.box("rows", xl, yy + 12, mid, hh - 24, "kpi_cell" if kpi_cells else "cell_gray", index=i, part="left")
        b.deco("circle_arrow_brand", xl + mid + 7, yy + hh / 2 - 15, 30, 30)
        b.box("rows", xr, yy + 12, mid, hh - 24, "kpi_cell_brand" if kpi_cells else right_style, index=i, part="right")
        if change:
            b.box("rows", 1216 - rw, yy + hh / 2 - 17, rw, 34, "pill_tint", index=i, part="change")
    b.deco("rule", 64, Y1, 1152, 1)


def a_pillars(b: Builder, section: str = "vp", n: int = 3, image: bool = False, grid2: bool = False,
              message: bool = False, style: str | None = None, sub: bool = False, img_grade: str = "C",
              **_: Any) -> None:
    """VP-B(2·3·4), ST-A, VP-F(이미지판), CL-B …"""
    y = frame(b, section, sub=sub)
    spec: dict[str, Any] = {"no": 3, "tag": 12, "title": 24, "body": 90, "kpi": "kpi"}
    if image:
        spec["image"] = f"image:{img_grade}"
    items(b, "pillars", "가치 기둥(제목 · 설명 · 근거 수치" + (" · 제품 이미지" if image else "") + ")", n, F(**spec))
    if message:
        b.slot("message", "text", "핵심 메시지(머리 띠)", max_chars=60)
        b.deco("panel_tint", 64, y, 1152, 56)
        b.box("message", 92, y + 12, 1096, 32, "band_text")
        y += 76
    st = style or ("card_img" if image else "card_pillar")
    if grid2:
        ch = (Y1 - y - 24) / 2
        for i in range(n):
            r, c = divmod(i, 2)
            b.box("pillars", 64 + c * 588, y + r * (ch + 24), 564, ch, "card_img_row" if image else st, index=i)
    else:
        for i, (x, w) in enumerate(cols(n)):
            b.box("pillars", x, y, w, Y1 - y, st, index=i)


def a_statement(b: Builder, section: str = "vp", n: int = 3, image: bool = False, **_: Any) -> None:  # VP-C, VP-G
    y = frame(b, section)
    b.slot("message", "text", "한 문장 메시지", required=True, max_chars=50)
    b.slot("message_sub", "text", "메시지 보충", max_chars=90)
    items(b, "proofs", "근거(수치 · 제목 · 설명)", n, F(kpi="kpi", title=22, body=60))
    if image:
        img_slot(b, "image", "대표 제품(히어로)", "C", required=True)
        items(b, "products", "함께 쓰는 제품(작은 컷)", 3, F(title=14, image="image:C"), required=False)
        b.box("message", 64, y + 10, 580, 200, "statement")
        b.box("message_sub", 64, y + 220, 580, 60, "body")
        b.deco("panel", 676, y - 32, 540, 340)
        b.box("image", 690, y - 22, 512, 320, "image_contain")
        for i, (x, w) in enumerate(cols(3, 676, 540, 12)):
            b.box("products", x, y + 324, w, 112 + 28, "card_img_small", index=i)
        for i, (x, w) in enumerate(cols(n, 64, 588, 12)):
            b.box("proofs", x, y + 300, w, Y1 - y - 300, "card_kpi", index=i)
    else:
        b.box("message", 64, y + 20, 1152, 180, "statement")
        b.box("message_sub", 64, y + 210, 1152, 40, "subtitle")
        for i, (x, w) in enumerate(cols(n)):
            b.box("proofs", x, y + 268, w, Y1 - y - 268, "card_kpi", index=i)


def a_kpi_rows(b: Builder, section: str = "vp", n: int = 4, **_: Any) -> None:          # EF-A, VP-XX-C
    y = frame(b, section, sub=True)
    items(b, "rows", "지표(이름 · 기준 · 지금 · 도입 후 · 변화)", n,
          F(title=16, body=24, before="kpi", after="kpi", change=10))
    b.slot("headers", "text", "열 머리", count=4, max_chars=10, default=["지표", "지금", "도입 후", "변화"])
    hx = [(64, 220), (300, 380), (744, 380), (1140, 76)]
    for i, (x, w) in enumerate(hx):
        b.box("headers", x, y + 8, w, 24, "label_brand" if i == 2 else "label", index=i)
    top = y + 40
    for i, (yy, hh) in enumerate(rows(n, top, Y1 - top - 24, 0)):
        b.deco("rule", 64, yy, 1152, 1)
        b.box("rows", 64, yy, 220, hh, "cell_title_body", index=i, part="title")
        b.box("rows", 300, yy + 8, 380, hh - 16, "kpi_bar", index=i, part="before")
        b.deco("arrow", 698, yy + hh / 2 - 8, 26, 16)
        b.box("rows", 744, yy + 8, 380, hh - 16, "kpi_bar_brand", index=i, part="after")
        b.box("rows", 1132, yy + hh / 2 - 17, 84, 34, "pill_tint", index=i, part="change")


def a_roi(b: Builder, section: str = "vp", **_: Any) -> None:                   # EF-B
    y = frame(b, section, sub=True)
    b.slot("chart", "chart", "누적 투자 · 누적 절감(선)", required=True, hint="type=line")
    b.slot("chart_title", "text", "차트 제목", max_chars=30, default="누적 금액")
    b.slot("stats", "kpi", "요약 수치(초기 투자 · 연간 절감 · 순효과)", count=3)
    b.slot("assumptions", "caption", "가정 · 산출 근거", max_chars=90)
    b.deco("panel", 64, y + 8, 760, Y1 - y - 8)
    b.box("chart_title", 88, y + 26, 300, 20, "heading_sm")
    b.box("chart", 88, y + 56, 712, Y1 - y - 80, "chart")
    for i, (yy, hh) in enumerate(rows(3, y + 8, 410, 8)):
        b.box("stats", 848, yy, 368, hh, "kpi_brand" if i == 2 else "kpi_card", index=i)
    b.box("assumptions", 848, 590, 368, 50, "caption")


def a_quant_qual(b: Builder, section: str = "vp", **_: Any) -> None:            # EF-C
    y = frame(b, section)
    b.slot("headers", "text", "머리 2", count=2, max_chars=14, default=["정량 효과", "정성 효과"])
    b.slot("kpis", "kpi", "정량 수치 4", count=4)
    items(b, "feels", "정성 효과(제목 · 설명 · 누가)", 4, F(no=2, title=22, body=60, who=16))
    b.box("headers", 64, y, 564, 24, "label_brand", index=0)
    b.box("headers", 652, y, 564, 24, "label", index=1)
    for i in range(4):
        r, c = divmod(i, 2)
        b.box("kpis", 64 + c * 290, y + 36 + r * 246, 274, 230, "kpi_card", index=i)
    for i, (yy, hh) in enumerate(rows(4, y + 36, Y1 - y - 36, 10)):
        b.box("feels", 652, yy, 564, hh, "card_row_text", index=i)


def a_chain_rows(b: Builder, section: str = "vp", n: int = 3, image: bool = True,
                 headers: tuple[str, str, str] = ("과제", "제품 · 솔루션", "가치"), kw: bool = False,
                 **_: Any) -> None:   # VP-E, VP-U, VP-XX-A
    y = frame(b, section)
    spec: dict[str, Any] = {"left": 50, "left_sub": 50, "mid": 20, "right": 40, "kpi": "kpi"}
    if image:
        spec["image"] = "image:C"
    if kw:
        spec["chips"] = "bullets"
    fl = F(**{k: v for k, v in spec.items() if k != "left_sub"}) + [f("left_sub", "text", "왼쪽 보충", 50)]
    items(b, "rows", "행(" + " → ".join(headers) + ")", n, fl)
    b.slot("headers", "text", "열 머리 3", count=3, max_chars=12, default=list(headers))
    xs = [(64, 340), (444, 360), (844, 372)]
    for i, (x, w) in enumerate(xs):
        b.box("headers", x, y, w, 22, "label_brand" if i == 2 else "label", index=i)
    for i, (yy, hh) in enumerate(rows(n, y + 32, Y1 - y - 32, 14)):
        b.box("rows", 64, yy, 340, hh, "cell_left_card", index=i, part="left")
        b.deco("arrow", 410, yy + hh / 2 - 8, 28, 16)
        if image:
            b.box("rows", 444, yy, 168, hh, "image_contain", index=i, part="image")
            b.box("rows", 620, yy, 184, hh, "cell_mid", index=i, part="mid")
        else:
            b.box("rows", 444, yy, 360, hh, "cell_mid", index=i, part="mid")
        b.deco("arrow", 810, yy + hh / 2 - 8, 28, 16)
        b.box("rows", 844, yy, 372, hh, "cell_value", index=i, part="right")


def a_chain_cols(b: Builder, section: str = "space_scenario", **_: Any) -> None:   # SS-B
    y = frame(b, section)
    img_slot(b, "image", "공간 이미지", "A")
    b.slot("space", "text", "공간 이름(사진 위 라벨)", max_chars=16)
    b.slot("headers", "text", "열 머리 3", count=3, max_chars=10, default=["솔루션", "제품", "가치"])
    items(b, "solutions", "솔루션(무엇이)", 2, F(letter=1, title=18, body=50))
    items(b, "products", "제품(무엇으로)", 3, F(title=16, body=20, image="image:C"))
    items(b, "values", "가치(어떤 가치를)", 2, F(no=6, title=26, kpi="kpi"))
    b.box("image", 64, y, 368, Y1 - y, "image")
    b.box("space", 82, Y1 - 46, 200, 28, "chip_dark")
    for i, x in enumerate((456, 736, 1016)):
        b.box("headers", x, y, 200, 22, "label_brand" if i == 2 else "label", index=i)
    b.deco("fan", 656, y + 36, 360, 440)
    for i, yy in enumerate((y + 54, y + 284)):
        b.box("solutions", 456, yy, 200, 168, "card_white", index=i)
        b.box("values", 1016, yy, 200, 168, "card_brand", index=i)
    for i, yy in enumerate((y + 36, y + 208, y + 380)):
        b.box("products", 736, yy, 200, 128, "card_product", index=i)


def a_hero_panel(b: Builder, section: str = "vp", n: int = 3, side: str = "left", img_w: int = 660,
                 grade: str = "A", full: bool = False, kpis: int = 0, item_style: str = "card_row_text",
                 message: bool = True, image_style: str = "image", **_: Any) -> None:  # VP-N, VP-T, P1-A, BV-C, SF-A, SS-A …
    if full:
        # 사진이 한쪽 전체를 덮는다 → 머리 · 바닥을 글 쪽으로 옮긴다(VP-N · C12 형).
        ix = 0 if side == "left" else 1280 - img_w
        px = img_w + 48 if side == "left" else 64
        pw = 1280 - img_w - 112
        ko, en = {"vp": ("VALUE PROPS", "VALUE PROPS")}.get(section, (None, None))
        b.slot("eyebrow", "text", "섹션 라벨", max_chars=40, default=ko, default_en=en)
        b.slot("title", "text", "제목 — 핵심 메시지", required=True, max_chars=40)
        b.slot("sources", "source", "출처 · 각주")
        b.slot("footer", "text", "바닥글", max_chars=60)
        b.slot("logo", "logo", "고객사 로고")
        b.box("eyebrow", px, 44, pw, 20, "eyebrow")
        b.box("title", px, 66, pw, 84, "title")
        b.box("sources", px, 651, pw, 15, "source")
        b.box("logo", px, 680, 72, 20, "logo")
        b.box("footer", px + 84, 680, pw - 84, 20, "footer")
        y = 172
    else:
        y = frame(b, section)
    img_slot(b, "image", "대표 이미지", grade, required=True)
    b.slot("image_caption", "caption", "이미지 캡션 · 출처", max_chars=50)
    if message:
        b.slot("message", "text", "핵심 문장", max_chars=60)
    if n:
        items(b, "items", "항목(제목 · 설명 · 수치)", n, F(no=3, tag=12, title=24, body=80, kpi="kpi", image="image:C"))
    if kpis:
        b.slot("kpis", "kpi", "수치", count=kpis)
    if full:
        b.box("image", ix, 0, img_w, 720, "image_full")
        b.box("image_caption", ix + 16, 690, img_w - 32, 16, "caption_inv")
    else:
        ix = 64 if side == "left" else 1216 - img_w
        b.box("image", ix, y, img_w, Y1 - y - 24, image_style)
        b.box("image_caption", ix, Y1 - 18, img_w, 16, "caption")
        px = ix + img_w + 24 if side == "left" else 64
        pw = 1152 - img_w - 24
    top = y
    if message:
        b.box("message", px, top, pw, 96, "heading_lg")
        top += 108
    if kpis:
        for i, (x, w) in enumerate(cols(kpis, px, pw, 12)):
            b.box("kpis", x, top, w, 96, "kpi_tile_line", index=i)
        top += 112
    if n:
        for i, (yy, hh) in enumerate(rows(n, top, Y1 - top, 12)):
            b.box("items", px, yy, pw, hh, item_style, index=i)


def a_full_image(b: Builder, section: str = "birdseye", chips: bool = True, **_: Any) -> None:   # BV-A, P-I
    y = frame(b, section)
    img_slot(b, "image", "전경 이미지(조감도 · 렌더)", "A", required=True)
    b.slot("caption", "text", "정보 줄(면적 · 층고 · 시점)", max_chars=40)
    b.slot("details", "text", "배치 요약(제품 · 위치)", max_chars=90)
    b.box("image", 64, y - 8, 1152, 470, "image")
    if chips:
        b.slot("legend", "bullets", "범례 칩(최대 3)", count=3)
        b.box("legend", 880, y + 8, 320, 30, "chips_white")
    b.box("caption", 64, 612, 380, 24, "body_strong")
    b.box("details", 460, 612, 756, 24, "body")


def a_mood_full(b: Builder, section: str = "space_products", **_: Any) -> None:          # P-I
    b.slot("eyebrow", "text", "섹션 라벨", max_chars=40, default="공간별 제품", default_en="PRODUCTS BY SPACE")
    b.slot("title", "text", "제목(사진 위)", required=True, max_chars=40)
    b.slot("subtitle", "text", "한 줄 설명", max_chars=80)
    img_slot(b, "image", "무드 컷(풀블리드)", "A", required=True)
    items(b, "products", "제품 표시", 3, F(title=16, body=24), required=False)
    b.slot("sources", "source", "출처")
    b.box("image", 0, 0, 1280, 720, "image_full")
    b.deco("panel_dark_alpha", 0, 0, 640, 720)
    b.box("eyebrow", 64, 64, 520, 20, "eyebrow_inv")
    b.box("title", 64, 96, 520, 120, "cover_title_inv")
    b.box("subtitle", 64, 230, 520, 60, "subtitle_inv")
    for i in range(3):
        b.box("products", 64, 470 + i * 62, 420, 54, "tile_dark", index=i)
    b.box("sources", 64, 690, 1152, 16, "caption_inv")


def a_two_images(b: Builder, section: str = "vp", bullets: bool = True, band: bool = True,
                 labels: tuple[str, str] = ("지금", "제안 후"), kpis: int = 0, chips: bool = False,
                 **_: Any) -> None:   # VP-L, SS-C, BV-B, VP-S, CD-B, GN-B
    y = frame(b, section)
    fl = F(tag=8, title=30, body=80, bullets="bullets", image="image:A")
    if chips:
        fl += F(chips="bullets")
    items(b, "sides", "두 시점(라벨 · 이미지 · 제목 · 항목)", 2, fl)
    b.slot("labels", "text", "라벨 2", count=2, max_chars=8, default=list(labels))
    img_h = 300 if (bullets or kpis) else 400
    bottom = 588 if band else Y1
    if kpis:
        bottom -= 72
    for i, x in enumerate((64, 652)):
        b.box("sides", x, y, 564, img_h, "image", index=i, part="image")
        b.box("labels", x + 18, y + 18, 120, 30, "pill_gray" if i == 0 else "pill_brand", index=i)
        b.box("sides", x, y + img_h + 16, 564, bottom - (y + img_h + 16), "card_text_plain", index=i)
    b.deco("circle_arrow_big", 614, y + img_h / 2 - 26, 52, 52)
    if kpis:
        b.slot("kpis", "kpi", "변화 수치", count=kpis)
        for i, (x, w) in enumerate(cols(kpis)):
            b.box("kpis", x, bottom + 8, w, 56, "kpi_inline", index=i)
    if band:
        b.slot("message", "text", "가치 — 한 문장", max_chars=70)
        b.slot("message_label", "text", "띠 라벨", max_chars=8, default="가치", default_en="Value")
        b.deco("panel_tint", 64, 600, 1152, 48)
        b.box("message_label", 88, 612, 60, 24, "label_brand")
        b.box("message", 160, 610, 1040, 28, "band_text")


def a_image_pins(b: Builder, section: str = "birdseye", n: int = 4, img_w: int = 760, grade: str = "A",
                 sub: bool = True, list_style: str = "card_pin", legend: bool = False, image_style: str = "image",
                 **_: Any) -> None:   # ZP-A, VP-I, VP-K, VM-C, ZP-D, VP-US, VP-P, P-J, P-H, IS-B
    y = frame(b, section, sub=sub)
    img_slot(b, "image", "바탕 이미지(조감도 · 사진 · 제품)", grade, required=True)
    items(b, "pins", "포인트(번호 · 제목 · 설명 · 위치 x,y)", n, F(no=3, title=22, body=70, tag=14, x="number", y="number"))
    b.box("image", 64, y, img_w, Y1 - y, image_style)
    b.box("pins", 64, y, img_w, Y1 - y, "pins")
    px = 64 + img_w + 24
    top = y
    if legend:
        items(b, "legend", "범례(기호 · 이름 · 설명)", 2, F(letter=1, title=16, body=24), required=False)
        for i in range(2):
            b.box("legend", px, top + i * 40, 1216 - px, 36, "legend_row", index=i)
        top += 96
    for i, (yy, hh) in enumerate(rows(n, top, Y1 - top, 10)):
        b.box("pins", px, yy, 1216 - px, hh, list_style, index=i)


def a_image_pins_wide(b: Builder, section: str = "vp", n: int = 5, grade: str = "A", sub: bool = False,
                      **_: Any) -> None:   # VP-K, ZP-C
    y = frame(b, section, sub=sub)
    img_slot(b, "image", "공간 · 동선 이미지(넓게)", grade, required=True)
    items(b, "pins", "포인트(번호 · 제목 · 설명 · 위치 x,y)", n, F(no=3, title=18, body=50, x="number", y="number"))
    ih = 300 if n <= 4 else 290
    b.box("image", 64, y - 8, 1152, ih, "image")
    b.box("pins", 64, y - 8, 1152, ih, "pins")
    for i, (x, w) in enumerate(cols(n, gap=16)):
        b.box("pins", x, y + ih + 8, w, Y1 - y - ih - 8, "card_pin_col", index=i)
        if i < n - 1:
            b.deco("chevron_small", x + w - 2, y + ih + 8 + (Y1 - y - ih - 8) / 2 - 8, 20, 16)


def a_plan_grid(b: Builder, section: str = "birdseye", n: int = 4, grade: str = "A", **_: Any) -> None:  # BV-D, ZP-B
    y = frame(b, section, sub=True)
    img_slot(b, "image", "평면 · 전체 조감도", "D" if grade == "A" else grade, required=True)
    items(b, "zones", "시점 · 존(번호 · 이름 · 렌더 · 설명 · 위치 x,y)", n,
          F(no=3, title=16, body=50, image=f"image:{grade}", chips="bullets", x="number", y="number"))
    b.box("image", 64, y, 368, Y1 - y, "image_contain_soft")
    b.box("zones", 64, y, 368, Y1 - y, "pins")
    ch = (Y1 - y - 16) / 2
    for i in range(n):
        r, c = divmod(i, 2)
        b.box("zones", 456 + c * 388, y + r * (ch + 16), 372, ch, "card_img", index=i)


def a_rows_images(b: Builder, section: str = "birdseye", n: int = 3, labels: tuple[str, str] = ("지금", "제안 시안"),
                  **_: Any) -> None:   # GN-C, MB-B
    y = frame(b, section, sub=True)
    items(b, "rows", "행(공간 · 지금 사진 · 시안 · 설명)", n,
          F(title=14, left="image:A", right="image:A", body=70, chips="bullets"))
    b.slot("headers", "text", "열 머리", count=2, max_chars=10, default=list(labels))
    b.box("headers", 220, y, 300, 22, "label", index=0)
    b.box("headers", 568, y, 300, 22, "label_brand", index=1)
    for i, (yy, hh) in enumerate(rows(n, y + 30, Y1 - y - 30, 14)):
        b.box("rows", 64, yy, 140, hh, "row_label_strong", index=i, part="title")
        b.box("rows", 220, yy, 300, hh, "image", index=i, part="left")
        b.deco("circle_arrow_brand", 528, yy + hh / 2 - 16, 32, 32)
        b.box("rows", 568, yy, 300, hh, "image", index=i, part="right")
        b.box("rows", 892, yy, 324, hh, "card_text_plain", index=i)


def a_matrix(b: Builder, section: str = "space_scenario", sub: bool = True, style: str = "matrix",
             label: str = "격자(행 = 공간, 열 = 솔루션)", band: bool = False, **_: Any) -> None:  # VM-A, VP-M, SM-B, VC-64, VC-24
    a_table(b, section, sub=sub, style=style, band=band, label=label)


def a_swimlane(b: Builder, section: str = "space_scenario", sub: bool = True, label: str = "레인(행) × 시각(열) 카드",
               **_: Any) -> None:   # OP-B, VM-D, VC-J, SS-XX-C
    y = frame(b, section, sub=sub)
    b.slot("lanes", "table", label, required=True,
           hint="table: columns=[레인 머리, 열1…], rows=[[레인 이름, 칸1…]] · 칸 = 문자열 또는 {title, body, tag}")
    b.box("lanes", 64, y, 1152, Y1 - y, "swimlane")


def a_gantt(b: Builder, section: str = "why", n: int = 5, **_: Any) -> None:      # SV-A, BM-D
    y = frame(b, section, sub=True)
    b.slot("periods", "text", "기간 눈금(예: 1월 … 6월)", count=6, max_chars=8)
    items(b, "phases", "단계(이름 · 시작 · 끝 · 담당 · 산출물)", n, F(title=18, start="number", end="number", owner=14, body=40))
    items(b, "milestones", "마일스톤", 3, F(title=16, x="number"), required=False)
    b.box("phases", 64, y, 1152, Y1 - y, "gantt", periods="periods", milestones="milestones")


def a_tiers(b: Builder, section: str = "solution", n: int = 3, side: int = 270, chips: int = 4, **_: Any) -> None:  # SA-A, SA-C, X-D
    y = frame(b, section, sub=True)
    items(b, "layers", "계층(이름 · 설명 · 구성 요소 칩)", n, F(tag=10, title=22, body=60, chips="bullets"))
    tw = 1152 - (side + 24 if side else 0)
    for i, (yy, hh) in enumerate(rows(n, y, Y1 - y, 20)):
        st = "layer_brand" if i == 1 and n >= 3 else ("layer_tint" if i == 0 else "layer")
        b.box("layers", 64, yy, tw, hh, st, index=i)
        if i < n - 1:
            b.deco("connector_v", 64 + tw / 2, yy + hh, 2, 20)
    if side:
        items(b, "notes", "옆 설명(보안 · 연동 · 운영)", 3, F(no=3, title=22, body=70), required=False)
        for i, (yy, hh) in enumerate(rows(3, y, Y1 - y, 12)):
            b.box("notes", 64 + tw + 24, yy, side, hh, "card_white", index=i)


def a_hub(b: Builder, section: str = "solution", n: int = 6, **_: Any) -> None:   # SA-B, VC-14
    y = frame(b, section, sub=True)
    b.slot("center", "card", "가운데(솔루션 · 공간)", required=True, fields=F(tag=12, title=18, body=40))
    items(b, "nodes", "연결된 것(기기 · 솔루션)", n, F(title=18, body=40, image="image:C"))
    cx, cy = 640, (y + Y1) / 2
    b.box("center", cx - 110, cy - 110, 220, 220, "circle_card_brand")
    pos = [(-470, -150), (-470, 0), (-470, 150), (220, -150), (220, 0), (220, 150)]
    if n == 4:
        pos = [(-470, -100), (-470, 100), (220, -100), (220, 100)]
    for i, (dx, dy) in enumerate(pos[:n]):
        x, yy = cx + dx, cy + dy - 46
        if dx < 0:
            b.deco("connector_h", x + 250, yy + 46, (cx - 110) - (x + 250), 2)
        else:
            b.deco("connector_h", cx + 110, yy + 46, x - (cx + 110), 2)
        b.box("nodes", x, yy, 250, 92, "card_white_node", index=i)


def a_steps_compare(b: Builder, section: str = "solution", n: int = 5, **_: Any) -> None:   # OP-C
    y = frame(b, section, sub=True)
    b.slot("labels", "text", "줄 라벨 2", count=2, max_chars=10, default=["도입 전", "도입 후"])
    items(b, "before", "도입 전 단계", n, F(title=14, days=8))
    items(b, "after", "도입 후 단계", n, F(title=14, days=8), required=False)
    b.slot("summary", "kpi", "줄어드는 것(수치 2)", count=2)
    b.slot("summary_title", "text", "요약 머리", max_chars=20, default="줄어드는 것")
    for r, (key, yy, st) in enumerate((("before", y + 4, "panel"), ("after", y + 228, "panel_line"))):
        b.deco(st, 64, yy, 858, 200)
        b.box("labels", 84, yy + 14, 200, 24, "label" if r == 0 else "label_brand", index=r)
        cw = (818 - 14 * (n - 1)) / n
        for i in range(n):
            b.box(key, 84 + i * (cw + 14), yy + 52, cw, 128, "card_white" if r == 0 else "card_tint", index=i)
    b.deco("panel_tint", 946, y + 4, 270, 424)
    b.box("summary_title", 968, y + 24, 226, 24, "label_brand")
    b.box("summary", 968, y + 64, 226, 160, "kpi_big", index=0)
    b.box("summary", 968, y + 240, 226, 160, "kpi_big", index=1)


def a_case_story(b: Builder, section: str = "cases", **_: Any) -> None:          # CD-A
    y = frame(b, section, sub=True)
    img_slot(b, "image", "사례 사진", "A", required=True)
    b.slot("customer", "text", "고객 · 업종 · 연도", max_chars=40)
    items(b, "parts", "과제 · 해결 · 성과", 3, F(tag=8, title=30, body=110))
    b.slot("kpis", "kpi", "성과 수치", count=3)
    b.box("image", 64, y, 466, 380, "image")
    b.box("customer", 64, y + 392, 466, 24, "body_strong")
    for i, (x, w) in enumerate(cols(3, 64, 466, 10)):
        b.box("kpis", x, y + 428, w, Y1 - y - 428, "kpi_tile_line", index=i)
    for i, (yy, hh) in enumerate(rows(3, y, Y1 - y, 14)):
        b.box("parts", 554, yy, 662, hh, "card_brand" if i == 2 else "card", index=i)


def a_case_numbers(b: Builder, section: str = "cases", **_: Any) -> None:        # CD-C
    y = frame(b, section)
    b.slot("customer", "text", "고객 · 업종 · 연도", max_chars=40)
    b.slot("kpis", "kpi", "성과 수치(크게)", required=True, count=3)
    b.slot("quote", "text", "고객 코멘트", max_chars=120)
    b.slot("who", "text", "말한 사람", max_chars=30)
    img_slot(b, "image", "사례 사진(작게)", "A")
    b.box("customer", 64, y, 700, 24, "label")
    for i, (x, w) in enumerate(cols(3)):
        b.box("kpis", x, y + 40, w, 220, "kpi_big_card", index=i)
    b.box("image", 64, y + 284, 368, Y1 - y - 284, "image")
    b.deco("panel_tint", 456, y + 284, 760, Y1 - y - 284)
    b.box("quote", 488, y + 310, 700, Y1 - 68 - (y + 310), "quote")
    b.box("who", 488, Y1 - 60, 700, 24, "small")


def a_logo_wall(b: Builder, section: str = "cases", n: int = 12, **_: Any) -> None:  # CL-C
    y = frame(b, section, sub=True)
    b.slot("count", "kpi", "사례 수(크게)", required=True)
    items(b, "logos", "레퍼런스(이름 · 업종 · 로고)", n, F(title=20, tag=12, image="image:E"))
    b.box("count", 64, y, 300, Y1 - y, "kpi_big_card")
    for i in range(n):
        r, c = divmod(i, 4)
        b.box("logos", 388 + c * 210, y + r * 166, 196, 152, "logo_tile", index=i)


def a_map_table(b: Builder, section: str = "why", **_: Any) -> None:          # SV-B, BM-E
    y = frame(b, section, sub=True)
    img_slot(b, "image", "지도 · 커버리지 그림", "D")
    items(b, "regions", "지역 타일(이름 · 수)", 6, F(title=12, kpi="kpi"), required=False)
    b.slot("table", "table", "표(권역 · 거점 · SLA)", required=True)
    # 지도 그림과 지역 타일은 둘 중 하나 — 그림이 있으면 타일은 그리지 않는다
    b.box("image", 64, y, 436, Y1 - y - 40, "image_contain", placeholder_unless="regions")
    b.box("regions", 64, y, 436, Y1 - y - 40, "region_tiles", unless="image")
    b.box("table", 540, y, 676, Y1 - y - 40, "table")


def a_spec_groups(b: Builder, section: str = "spec", **_: Any) -> None:       # SD-A
    y = frame(b, section, sub=True)
    b.slot("product", "card", "제품(이름 · 이미지 · 한 줄)", required=True, fields=F(title=20, body=60, image="image:C", tag=12))
    b.slot("table", "table", "그룹별 상세 사양(그룹 머리 행 포함)", required=True)
    b.box("product", 64, y, 368, Y1 - y, "card_img_tall")
    b.box("table", 456, y, 760, Y1 - y, "table_spec")


def a_drawing(b: Builder, section: str = "spec", **_: Any) -> None:           # SD-B, P-E, P-F
    y = frame(b, section, sub=True)
    img_slot(b, "image", "도면 · 입면 · 단면 그림", "D", required=True)
    b.slot("table", "table", "치수 · 설치 조건", required=True)
    b.slot("kpis", "kpi", "핵심 치수", count=3)
    b.deco("panel", 64, y, 660, Y1 - y)
    b.box("image", 84, y + 20, 620, Y1 - y - 40, "image_contain")
    for i, (x, w) in enumerate(cols(3, 748, 468, 10)):
        b.box("kpis", x, y, w, 96, "kpi_tile_line", index=i)
    b.box("table", 748, y + 112, 468, Y1 - y - 112, "table")


def a_space_map(b: Builder, section: str = "space_products", n: int = 3, img_w: int = 662, sub: bool = True,
                grade: str = "A", **_: Any) -> None:   # SM-A, SS-XX-A, VC-1Z, VC-43
    y = frame(b, section, sub=sub)
    img_slot(b, "image", "평면 · 조감도 이미지", grade)
    items(b, "spaces", "공간(번호 · 이름 · 제품 칩 · 가치)", n,
          F(no=3, title=16, chips="bullets", body=60, x="number", y="number"))
    b.box("image", 64, y, img_w, Y1 - y, "image_contain_soft")
    b.box("spaces", 64, y, img_w, Y1 - y, "pins")
    px = 64 + img_w + 24
    for i, (yy, hh) in enumerate(rows(n, y, Y1 - y, 8 if n > 4 else 12)):
        b.box("spaces", px, yy, 1216 - px, hh, "card_space_row", index=i)


def a_path_strip(b: Builder, section: str = "space_products", n: int = 5, image: bool = True, band: bool = True,
                 sub: bool = True, **_: Any) -> None:   # SM-C, ZP-C, VP-R, UX-A, VC-31
    y = frame(b, section, sub=sub)
    spec: dict[str, Any] = {"no": 3, "title": 16, "body": 60, "chips": "bullets"}
    if image:
        spec["image"] = "image:A"
    items(b, "steps", "동선 순서(번호 · 장소 · 일어나는 일" + (" · 사진" if image else "") + ")", n, F(**spec))
    bottom = 588 if band else Y1
    cw = (1152 - 28 * (n - 1)) / n
    for i in range(n):
        x = 64 + i * (cw + 28)
        b.box("steps", x, y, cw, bottom - y, "card_img" if image else "card", index=i)
        if i < n - 1:
            b.deco("chevron", x + cw + 2, y + 120, 24, 24)
    if band:
        b.slot("message", "text", "동선 전체가 말하는 것", max_chars=80)
        b.deco("panel_tint", 64, 600, 1152, 48)
        b.box("message", 92, 610, 1096, 28, "band_text")


def a_floors(b: Builder, section: str = "space_products", n: int = 6, **_: Any) -> None:   # SM-D
    y = frame(b, section)
    items(b, "floors", "층(층 · 쓰임 · 제품 칩)", n, F(tag=6, title=20, chips="bullets", body=50))
    b.slot("message", "text", "한 줄 요약(아래 띠)", max_chars=80)
    for i, (yy, hh) in enumerate(rows(n, y, 456, 6)):
        b.box("floors", 64, yy, 1152, hh, "floor_row", index=i)
    b.deco("panel_tint", 64, 606, 1152, 42)
    b.box("message", 92, 614, 1096, 26, "band_text")


def a_image_grid(b: Builder, section: str = "space_products", n: int = 6, cols_n: int = 3, card: bool = True,
                 sub: bool = True, grade: str = "A", **_: Any) -> None:   # SM-E, CL-D, AX-B, IS-A, P-T
    y = frame(b, section, sub=sub)
    items(b, "items", "카드(사진 · 이름 · 설명 · 칩)", n, F(image=f"image:{grade}", title=20, body=50, chips="bullets", tag=12))
    r_n = (n + cols_n - 1) // cols_n
    ch = (Y1 - y - 16 * (r_n - 1)) / r_n
    cws = cols(cols_n, gap=16 if cols_n > 3 else 24)
    for i in range(n):
        r, c = divmod(i, cols_n)
        x, w = cws[c]
        b.box("items", x, y + r * (ch + 16), w, ch, "card_img" if card else "image_tile", index=i)


def a_options3(b: Builder, section: str = "space_products", n: int = 3, image: bool = True, **_: Any) -> None:  # GN-A, P-G, P-O, GN-D
    y = frame(b, section, sub=True)
    spec: dict[str, Any] = {"tag": 10, "title": 22, "body": 70, "bullets": "bullets", "kpi": "kpi"}
    if image:
        spec["image"] = "image:A"
    items(b, "options", "안(이름 · 설명 · 구성 · 수치)", n, F(**spec))
    b.slot("recommended", "number", "추천 안 번호(1부터)", default=2)
    for i, (x, w) in enumerate(cols(n)):
        b.box("options", x, y, w, Y1 - y, "card_option", index=i, recommended="recommended")


def a_moodboard(b: Builder, section: str = "birdseye", **_: Any) -> None:     # MB-A, MB-B
    y = frame(b, section, sub=True)
    img_slot(b, "images", "무드 이미지 5(공간 · 소재 · 제품)", "A", count=5)
    b.slot("swatches", "text", "색 · 소재(HEX 또는 이름)", count=5, max_chars=16)
    items(b, "points", "조화 포인트", 3, F(no=3, title=22, body=60))
    b.box("images", 64, y, 420, Y1 - y, "image", index=0)
    b.box("images", 500, y, 260, 230, "image", index=1)
    b.box("images", 500, y + 246, 260, Y1 - y - 246, "image", index=2)
    b.box("images", 776, y, 200, 230, "image", index=3)
    b.box("images", 776, y + 246, 200, Y1 - y - 246, "image_contain", index=4)
    for i in range(5):
        b.box("swatches", 992, y + i * 36, 224, 28, "swatch", index=i)
    for i, (yy, hh) in enumerate(rows(3, y + 190, Y1 - y - 190, 10)):
        b.box("points", 992, yy, 224, hh, "card_white", index=i)


def a_split2(b: Builder, section: str = "space_scenario", band: bool = True, **_: Any) -> None:   # VC-12, VC-23, VC-21
    y = frame(b, section, sub=True)
    img_slot(b, "image", "공간 이미지(왼쪽 위)", "A")
    items(b, "sides", "두 갈래(솔루션 · 공간)", 2, F(tag=12, title=22, body=80, bullets="bullets", kpi="kpi"))
    b.box("image", 64, y, 1152, 180, "image")
    for i, (x, w) in enumerate(cols(2)):
        b.box("sides", x, y + 196, w, (Y1 - y - 196) - (64 if band else 0), "card_brand" if i == 0 else "card_dark", index=i)
    if band:
        b.slot("message", "text", "공통 기반 · 함께 쓰는 것", max_chars=80)
        b.deco("panel_tint", 64, 600, 1152, 48)
        b.box("message", 92, 610, 1096, 28, "band_text")


# ── 솔루션 전용 ─────────────────────────────────────────

def a_sol_intro(b: Builder, section: str = "solution", **_: Any) -> None:      # {SOL}-I
    y = frame(b, section)
    b.slot("solution_name", "text", "솔루션 이름", required=True, max_chars=24)
    b.slot("one_liner", "text", "한 줄 소개", max_chars=60)
    img_slot(b, "image", "솔루션 대표 이미지(KV · 화면)", "B")
    b.slot("logo_solution", "image", "솔루션 로고(있으면)", image_grade="E")
    items(b, "features", "핵심 기능 4(제목 · 고객 언어 설명)", 4, F(no=3, title=20, body=70))
    b.slot("devices", "bullets", "함께 쓰는 기기 칩", count=6)
    b.slot("when", "text", "언제 쓰나 — 한 문장", max_chars=70)
    b.box("logo_solution", 64, y, 160, 40, "image_contain_plain")
    b.box("solution_name", 64, y + 48, 560, 44, "heading_xl")
    b.box("one_liner", 64, y + 98, 560, 50, "subtitle")
    b.box("image", 64, y + 160, 560, 260, "image")
    b.box("devices", 64, y + 436, 560, 34, "chips")
    b.box("when", 64, y + 482, 560, 30, "band_text")
    for i in range(4):
        r, c = divmod(i, 2)
        b.box("features", 648 + c * 296, y + r * 262, 272, 250, "card", index=i)


def a_sol_diagram(b: Builder, section: str = "solution", **_: Any) -> None:    # {SOL}-D
    a_tiers(b, section, n=3, side=300)


def a_sol_scene(b: Builder, section: str = "solution", n: int = 4, **_: Any) -> None:   # {SOL}-S, -S-{IND}
    y = frame(b, section, sub=True)
    img_slot(b, "image", "공간 사진 · 평면", "A", required=True)
    b.slot("space", "text", "공간 라벨", max_chars=20)
    items(b, "steps", "장면(시각 · 제목 · 설명 · 기기 칩)", n, F(time=8, title=22, body=70, chips="bullets"))
    b.slot("kpis", "kpi", "가치 수치", count=3)
    b.box("image", 64, y, 520, Y1 - y, "image")
    b.box("space", 82, y + 18, 200, 28, "chip_dark")
    b.deco("track_v", 620, y + 10, 2, 400)
    for i, (yy, hh) in enumerate(rows(n, y, 404, 10)):
        b.deco("marker", 608, yy + 10, 26, 26)
        b.box("steps", 648, yy, 568, hh, "card_time", index=i)
    for i, (x, w) in enumerate(cols(3, 648, 568, 10)):
        b.box("kpis", x, Y1 - 72, w, 72, "kpi_tile_line", index=i)


# ── 공간 시나리오 업종판 D · E 형태(F1–F5) ──────────────────────

def a_form_users(b: Builder, section: str = "space_scenario", **_: Any) -> None:     # F1 이용자별
    y = frame(b, section, sub=True)
    img_slot(b, "image", "공간 사진", "A")
    items(b, "people", "이용자 · 직원 · 관리자(역할 · 얻는 것 · 쓰는 기기)", 3,
          F(role=14, name=20, body=80, bullets="bullets", kpi="kpi"))
    b.box("image", 64, y, 1152, 170, "image")
    for i, (x, w) in enumerate(cols(3)):
        b.box("people", x, y + 186, w, Y1 - y - 186, "card_person", index=i)


def a_form_problems(b: Builder, section: str = "space_scenario", **_: Any) -> None:  # F2 문제 → 해결
    y = frame(b, section, sub=True)
    img_slot(b, "image", "공간 사진", "A")
    items(b, "rows", "문제(지금 · 바뀐 뒤 · 지표)", 3, F(label=14, left=70, right=70, change=12))
    b.slot("headers", "text", "열 머리", count=2, max_chars=10, default=["지금", "바뀐 뒤"])
    b.box("image", 64, y, 368, Y1 - y, "image")
    b.box("headers", 456, y, 300, 26, "pill_gray", index=0)
    b.box("headers", 800, y, 300, 26, "pill_brand_left", index=1)
    for i, (yy, hh) in enumerate(rows(3, y + 40, Y1 - y - 40, 14)):
        b.box("rows", 456, yy, 320, hh, "cell_gray_titled", index=i, part="left", title_part="label")
        b.deco("circle_arrow_brand", 782, yy + hh / 2 - 13, 26, 26)
        b.box("rows", 814, yy, 300, hh, "cell_tint_strong", index=i, part="right")
        b.box("rows", 1124, yy + hh / 2 - 17, 92, 34, "pill_tint", index=i, part="change")


def a_form_path(b: Builder, section: str = "space_scenario", **_: Any) -> None:      # F3 동선 순서
    a_space_map(b, section, n=5, img_w=560)


def a_form_modes(b: Builder, section: str = "space_scenario", **_: Any) -> None:     # F4 운영 모드
    a_two_images(b, section, labels=("모드 1", "모드 2"), band=True)


def a_form_phases(b: Builder, section: str = "space_scenario", **_: Any) -> None:    # F5 단계별 도입
    a_timeline(b, section, n=3, band=True, sub=True)


# ── 공간별 제품 P{n}-{v} ─────────────────────────────────────

PROD_FIELDS = dict(tag=12, title=18, model=20, body=70, qty=8, bullets="bullets", kpi="kpi", image="image:C",
                   x="number", y="number")


def a_products(b: Builder, section: str = "space_products", n: int = 3, variant: str = "A", **_: Any) -> None:
    """공간 제품 소개 — n(1–5) × 변형 A 이미지 · B 공간 · 설치 · C 스펙 · D 강조."""
    sub = variant == "C" and n in (1, 2)
    y = frame(b, section, sub=sub)
    if not (variant == "C" and n == 5):
        items(b, "products", "제품(이름 · 모델 · 설명 · 수량 · 이미지 · 사진 위 위치 x,y)", n, F(**PROD_FIELDS))
    if variant == "B":
        img_slot(b, "space_image", "공간 · 설치 이미지(조감도 · 설치 컷)", "A", required=True)
    if variant == "A":
        if n == 1:
            b.slot("message", "text", "이 제품이 이 공간에서 하는 일", max_chars=60)
            b.deco("panel", 64, y, 662, Y1 - y)
            b.box("products", 84, y + 20, 622, Y1 - y - 40, "image_contain", index=0, part="image")
            b.box("message", 750, y, 466, 110, "heading_lg")
            b.box("products", 750, y + 122, 466, Y1 - y - 122, "card_white", index=0)
        else:
            for i, (x, w) in enumerate(cols(n, gap=24 if n < 5 else 16)):
                b.box("products", x, y, w, Y1 - y, "card_img_tall", index=i)
    elif variant == "B":
        if n == 1:
            b.box("space_image", 64, y - 8, 1152, 360, "image")
            b.box("products", 64, 508, 1152, 140, "card_row_img", index=0)
        elif n == 3:
            b.box("space_image", 64, y, 662, Y1 - y, "image")
            b.box("products", 64, y, 662, Y1 - y, "pins")
            for i, (yy, hh) in enumerate(rows(3, y, Y1 - y, 12)):
                b.box("products", 750, yy, 466, hh, "card_row_img", index=i)
        else:
            ih = 290 if n <= 4 else 280
            b.box("space_image", 64, y - 8, 1152, ih, "image")
            b.box("products", 64, y - 8, 1152, ih, "pins")
            for i, (x, w) in enumerate(cols(n, gap=16)):
                b.box("products", x, y + ih + 8, w, Y1 - y - ih - 8, "card_product_small", index=i)
    elif variant == "C":
        if n == 1:
            b.box("products", 64, y, 368, Y1 - y, "card_img_tall", index=0)
            b.slot("table", "table", "사양(항목 · 값)", required=True)
            b.box("table", 456, y, 760, Y1 - y, "table_spec")
        elif n == 2:
            b.slot("table", "table", "비교 사양(가운데 항목)", required=True)
            b.box("products", 64, y, 270, Y1 - y, "card_img_tall_tint", index=0)
            b.box("table", 358, y, 564, Y1 - y, "table_vs")
            b.box("products", 946, y, 270, Y1 - y, "card_img_tall", index=1)
        elif n == 3:
            b.slot("table", "table", "라인업 사양(행 = 항목)", required=True)
            b.deco("panel", 64, y, 1152, 250)
            for i, (x, w) in enumerate(cols(3, 184, 1032, 16)):
                b.box("products", x, y + 10, w, 230, "card_img_plain", index=i)
            b.box("table", 64, y + 266, 1152, Y1 - y - 266, "table_lineup")
        elif n == 4:
            for i in range(4):
                r, c = divmod(i, 2)
                b.box("products", 64 + c * 588, y + r * 262, 564, 250, "card_img_row_kpis", index=i)
        else:
            b.slot("table", "table", "목록(위치 · 제품 · 모델 · 수량 · 사양 · 비고)", required=True)
            b.box("table", 64, y, 1152, Y1 - y, "table_list")
    else:  # D 강조 — 주력 제품(앞 항목)을 크게
        if n == 1:
            b.slot("message", "text", "주력 제품 메시지", max_chars=50)
            b.box("message", 64, y + 40, 660, 260, "statement")
            b.box("products", 64, y + 320, 660, Y1 - y - 320, "card_white", index=0)
            b.deco("panel_tint", 750, y, 466, Y1 - y)
            b.box("products", 770, y + 20, 426, Y1 - y - 40, "image_contain", index=0, part="image")
        elif n == 5:
            for i, (x, w) in enumerate(cols(2)):
                b.box("products", x, y, w, 300, "card_img_row_dark" if i == 0 else "card_img_row", index=i)
            for i, (x, w) in enumerate(cols(3)):
                b.box("products", x, y + 316, w, Y1 - y - 316, "card_product_small", index=2 + i)
        else:
            main_w = {2: 760, 3: 564, 4: 564}[n]
            b.box("products", 64, y, main_w, Y1 - y, "card_img_tall_dark" if n == 4 else "card_img_tall_main", index=0)
            px = 64 + main_w + 24
            for i, (yy, hh) in enumerate(rows(n - 1, y, Y1 - y, 12)):
                b.box("products", px, yy, 1216 - px, hh, "card_row_img", index=1 + i)


# ── 구성 · 수량 ─────────────────────────────────────────────

def a_types_cols(b: Builder, section: str = "space_products", n: int = 3, **_: Any) -> None:   # BM-B
    y = frame(b, section)
    items(b, "types", "유형(이름 · 규모 · 제품별 수량 · 매장당 합계)", n,
          F(tag=10, title=18, body=30, bullets="bullets", kpi="kpi", note=40))
    b.slot("total", "text", "전체 합계 줄", max_chars=90)
    for i, (x, w) in enumerate(cols(n)):
        b.box("types", x, y, w, 444, "card_type", index=i)
    b.deco("panel_tint", 64, 596, 1152, 52)
    b.box("total", 92, 608, 1096, 28, "band_text")


def a_unit_kit(b: Builder, section: str = "space_products", **_: Any) -> None:    # BM-C, P-R
    y = frame(b, section)
    b.slot("kit", "card", "반복 유닛 키트(이름 · 설명 · 품목)", required=True, fields=F(title=18, body=30, bullets="bullets", image="image:D"))
    b.slot("multiplier", "kpi", "반복 수(× 300실)")
    b.slot("common", "card", "공용부(공간 · 품목)", fields=F(title=18, body=30, bullets="bullets"))
    b.slot("table", "table", "제품별 합계(유닛분 + 공용부 = 합계)", required=True)
    b.box("kit", 64, y, 340, 276, "card_outline")
    b.box("multiplier", 404, y, 136, 276, "kpi_multiplier")
    b.deco("plus", 540, y + 120, 28, 36)
    b.box("common", 568, y, 648, 276, "card")
    b.box("table", 64, y + 296, 1152, Y1 - y - 296, "table_totals")


# ── 이미지 출처 · 부록 ────────────────────────────────────────

def a_sources_table(b: Builder, section: str = "appendix", **_: Any) -> None:   # AX-A
    y = frame(b, section, sub=True, sub_w=616)      # 오른쪽은 요약 칩
    b.slot("summary", "bullets", "출처 유형 요약 칩", count=5)
    b.slot("table", "table", "이미지 표(썸네일 · 쓰인 곳 · 종류 · 출처 유형 · 상세 · 사용 조건)", required=True,
           hint="첫 열에 image file_id 를 넣으면 썸네일로 그린다")
    b.box("summary", 700, 110, 516, 28, "chips_right")
    b.box("table", 64, y - 10, 1152, Y1 - y - 12, "table_images")


# ── 레지스트리 ───────────────────────────────────────────────

ARCHETYPES: dict[str, Callable[..., None]] = {
    "cover_split": a_cover_split, "cover_full": a_cover_full, "cover_type": a_cover_type,
    "cover_collage": a_cover_collage, "cover_product": a_cover_product, "toc": a_toc, "toc_thumbs": a_toc_thumbs,
    "divider_number": a_divider_number, "divider_image": a_divider_image, "divider_photo": a_divider_photo,
    "closing": a_closing, "closing_image": a_closing_image,
    "kpi_band": a_kpi_band, "chart_insights": a_chart_insights, "plot_insights": a_plot_insights,
    "circles_rows": a_circles_rows, "drivers_outlook": a_drivers_outlook, "timeline": a_timeline,
    "trend_cards": a_trend_cards, "summary_3col": a_summary_3col, "tree": a_tree, "process_pains": a_process_pains,
    "swot": a_swot, "personas": a_personas, "journey": a_journey, "donut_needs": a_donut_needs, "table": a_table,
    "stacked_table": a_stacked_table, "funnel": a_funnel, "quad_center": a_quad_center,
    "market_trend": a_market_trend, "biz_ops": a_biz_ops, "user_journey": a_user_journey,
    "challenge_cards": a_challenge_cards, "rows_arrow": a_rows_arrow, "pillars": a_pillars, "statement": a_statement,
    "kpi_rows": a_kpi_rows, "roi": a_roi, "quant_qual": a_quant_qual, "chain_rows": a_chain_rows,
    "chain_cols": a_chain_cols, "hero_panel": a_hero_panel, "full_image": a_full_image, "mood_full": a_mood_full,
    "two_images": a_two_images, "image_pins": a_image_pins, "image_pins_wide": a_image_pins_wide,
    "plan_grid": a_plan_grid, "rows_images": a_rows_images, "matrix": a_matrix, "swimlane": a_swimlane,
    "gantt": a_gantt, "tiers": a_tiers, "hub": a_hub, "steps_compare": a_steps_compare, "case_story": a_case_story,
    "case_numbers": a_case_numbers, "logo_wall": a_logo_wall, "map_table": a_map_table, "spec_groups": a_spec_groups,
    "drawing": a_drawing, "space_map": a_space_map, "path_strip": a_path_strip, "floors": a_floors,
    "image_grid": a_image_grid, "options3": a_options3, "moodboard": a_moodboard, "split2": a_split2,
    "sol_intro": a_sol_intro, "sol_diagram": a_sol_diagram, "sol_scene": a_sol_scene,
    "form_users": a_form_users, "form_problems": a_form_problems, "form_path": a_form_path,
    "form_modes": a_form_modes, "form_phases": a_form_phases, "products": a_products, "types_cols": a_types_cols,
    "unit_kit": a_unit_kit, "sources_table": a_sources_table,
}


def build_layout(archetype: str, section: str, params: dict[str, Any]) -> Builder:
    fn = ARCHETYPES[archetype]
    b = Builder()
    fn(b, section=section, **params)
    return b


__all__ = ["ARCHETYPES", "build_layout", "CW", "GAP", "X0"]
