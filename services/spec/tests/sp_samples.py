"""보드 예시 견본 파일(테스트 · e2e · mock 시연 공용) — 06-spec §9 픽스처.

- `B병원_로비디스플레이_요구규격서.pdf` 4쪽(요구 12개, 인용 문장이 쪽 글에 그대로 있음)
- `ds_QB55C.pdf` 1쪽 데이터시트(밝기 400 nit · 소비전력 Typical 100 W · Max 150 W)
- `고객사_스펙양식.xlsx`(행 Model · Screen · Brightness (cd/m2) · Power · Remarks)

`python services/spec/tests/sp_samples.py <폴더>` 로 파일을 만든다(e2e 견본 web/e2e/spec/fixtures/).
mocks/ai-tools/sp.extract_requirements.json · sp.datasheet_extract.json 의 인용 · 값은 이 글과 같아야 한다.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

REQ_PAGES = [
    ["B병원 로비 디스플레이 구매 요구 규격서", "1. 개요",
     "본 규격서는 B 병원 본관 로비와 대기실에 설치할 안내 디스플레이의 요구 사항을 정한다.", "2026년 9월 B 병원 시설관리팀"],
    ["2. 디스플레이 성능", "2.1 화면 크기는 55인치 이상으로 한다.", "2.2 해상도는 UHD 이상이어야 한다.",
     "2.3 밝기는 450 cd/㎡ 이상이어야 한다.", "2.4 진료 시간과 관계없이 24시간 상시 표출이 가능해야 한다."],
    ["3. 운영 및 설치", "3.1 본관과 별관에 일괄 배포가 가능한 원격 콘텐츠 관리를 지원해야 한다.",
     "3.2 대기실 2곳에는 65인치 이상 제품을 설치한다.", "3.3 소비전력은 200 W 이하로 한다.",
     "3.4 제품 무게는 20kg 이하로 한다.", "3.5 동작 온도 0~40℃ 범위에서 정상 동작해야 한다."],
    ["4. 제출 및 보증", "4.1 납품 시 의료기관 설치 인증서를 제출해야 한다.", "4.2 Wi-Fi 지원 제품이어야 한다.",
     "4.3 무상 보증 3년 이상을 제공해야 한다."],
]

DS_LINES = ["Samsung Smart Signage QB55C (LH55QBCEBGCXKR) Data Sheet", "디스플레이", "밝기 (Typ) 400 nit", "명암비 4,000:1",
            "전원", "소비전력 (Typical) 100 W", "소비전력 (Max) 150 W"]


def _pdf(pages: list[list[str]]) -> bytes:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfgen import canvas
    try:
        pdfmetrics.getFont("HYGothic-Medium")
    except KeyError:
        pdfmetrics.registerFont(UnicodeCIDFont("HYGothic-Medium"))
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for lines in pages:
        y = 780
        for i, ln in enumerate(lines):
            c.setFont("HYGothic-Medium", 15 if i == 0 else 11)
            c.drawString(64, y, ln)
            y -= 28 if i == 0 else 22
        c.showPage()
    c.save()
    return buf.getvalue()


def requirement_pdf() -> bytes:
    return _pdf(REQ_PAGES)


def datasheet_pdf() -> bytes:
    return _pdf([DS_LINES])


def template_xlsx() -> bytes:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Spec"
    for r, label in enumerate(["Model", "Screen", "Brightness (cd/m2)", "Power", "Remarks"], start=1):
        ws.cell(row=r, column=1, value=label)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


FILES = {"B병원_로비디스플레이_요구규격서.pdf": requirement_pdf, "ds_QB55C.pdf": datasheet_pdf, "고객사_스펙양식.xlsx": template_xlsx}


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in FILES.items():
        (out / name).write_bytes(fn())
        print("wrote", out / name)
