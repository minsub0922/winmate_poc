"""2D 조감도 내보내기 — DXF(R12) · XLSX · CSV · 제안서 연결 JSON · ZIP. 외부 라이브러리 없이 만든다."""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import zipfile
from xml.sax.saxutils import escape

from . import geometry as G
from . import space as S
from .catalog import MOUNT_NAMES, Catalog, screen_size
from .drawing import plan_svg
from .layout2d import STRATEGIES, STRATEGY_NAMES, Ctx, recommend_all
from .rules import Rules


# ── 수량표 데이터 ──

def _zone_of(project):
    zones = project.get("zones", [])

    def f(pl):
        for z in zones:
            if z["x0"] <= pl["x"] <= z["x1"] and z["y0"] <= pl["y"] <= z["y1"]:
                return z
        return None
    return f


def qty_rows(project: dict, catalog: Catalog, rules: Rules | None = None) -> list[dict]:
    rules = rules or Rules(project.get("rules_override"))
    recs = recommend_all(project, catalog, rules)
    zone_of = _zone_of(project)
    rows = []
    for line in project.get("lines", []):
        pls = [pl for pl in project.get("placements", []) if pl.get("line") == line["id"]]
        if not pls:
            continue
        prod = catalog.get(line["product"])
        if not prod:
            continue
        rec = recs.get(line["id"], {})
        anchor = rec.get("anchor_desc", "")
        if rec.get("strategy") and rec.get("qty_rec") != len(pls):
            try:  # 확정 수량 기준 위치 설명
                ctx = Ctx(project, catalog, rules, line)
                anchor = STRATEGIES[rec["strategy"]](ctx, prod, line.get("mount") or prod["default_mount"], len(pls))["anchor_desc"]
            except Exception:  # noqa: BLE001
                pass
        zs = sorted({z["no"] for z in (zone_of(pl) for pl in pls) if z})
        sw, sh = screen_size(prod, bool(pls[0].get("portrait")))
        rows.append({
            "short": prod["short"], "code": prod["code"], "name": prod["name"],
            "mount": MOUNT_NAMES.get(line.get("mount") or prod["default_mount"], ""),
            "strategy": STRATEGY_NAMES.get(rec.get("strategy", ""), ""),
            "zones": ", ".join(f"존 {z}" for z in zs), "anchor": anchor,
            "qty": len(pls), "qty_rec": rec.get("qty_rec"),
            "dims": f"{prod['w']:,.1f} × {prod['h']:,.1f} × {prod['d']:,.1f}",
            "screen": f"{sw:,.0f} × {sh:,.0f}",
            "power_w": prod.get("power_w"), "weight_kg": prod.get("weight_kg"),
            "rule_ids": ", ".join(rec.get("rule_ids", [])), "formula": rec.get("formula", ""),
            "source": (prod.get("source") or {}).get("url", ""),
        })
    return rows


# ── DXF ──

class _Dxf:
    LAYERS = [("WALL", 8, "CONTINUOUS"), ("OPENING", 5, "CONTINUOUS"), ("PILLAR", 8, "CONTINUOUS"),
              ("OUTLET", 30, "CONTINUOUS"), ("PRODUCT", 5, "CONTINUOUS"), ("PRODUCT_CEILING", 5, "DASHED"),
              ("FIXTURE", 9, "DASHED"), ("ZONE", 150, "DASHED"), ("FLOW", 5, "DASHED"), ("DIM", 7, "CONTINUOUS"),
              ("TEXT", 7, "CONTINUOUS")]

    def __init__(self):
        self.e: list[str] = []

    @staticmethod
    def _p(x, y):
        return x, -y  # 도면 아래쪽(+y) → DXF 아래쪽(−Y)

    def line(self, layer, a, b):
        (x1, y1), (x2, y2) = self._p(*a), self._p(*b)
        self.e += ["0", "LINE", "8", layer, "10", f"{x1:.1f}", "20", f"{y1:.1f}", "30", "0.0",
                   "11", f"{x2:.1f}", "21", f"{y2:.1f}", "31", "0.0"]

    def poly(self, layer, pts, closed=True):
        self.e += ["0", "POLYLINE", "8", layer, "66", "1", "70", "1" if closed else "0", "10", "0.0", "20", "0.0", "30", "0.0"]
        for pt in pts:
            x, y = self._p(*pt)
            self.e += ["0", "VERTEX", "8", layer, "10", f"{x:.1f}", "20", f"{y:.1f}", "30", "0.0"]
        self.e += ["0", "SEQEND", "8", layer]

    def circle(self, layer, c, r):
        x, y = self._p(*c)
        self.e += ["0", "CIRCLE", "8", layer, "10", f"{x:.1f}", "20", f"{y:.1f}", "30", "0.0", "40", f"{r:.1f}"]

    def arc(self, layer, c, r, a0, a1):
        x, y = self._p(*c)
        self.e += ["0", "ARC", "8", layer, "10", f"{x:.1f}", "20", f"{y:.1f}", "30", "0.0", "40", f"{r:.1f}",
                   "50", f"{a0:.2f}", "51", f"{a1:.2f}"]

    def text(self, layer, at, s, h=250.0, center=False, rot=0.0):
        x, y = self._p(*at)
        self.e += ["0", "TEXT", "8", layer, "10", f"{x:.1f}", "20", f"{y:.1f}", "30", "0.0", "40", f"{h:.1f}", "1", str(s)]
        if rot:
            self.e += ["50", f"{rot:.1f}"]
        if center:
            self.e += ["72", "1", "11", f"{x:.1f}", "21", f"{y:.1f}", "31", "0.0"]

    def build(self) -> bytes:
        head = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "9", "$DWGCODEPAGE", "3", "ANSI_949",
                "0", "ENDSEC"]
        tables = ["0", "SECTION", "2", "TABLES",
                  "0", "TABLE", "2", "LTYPE", "70", "2",
                  "0", "LTYPE", "2", "CONTINUOUS", "70", "0", "3", "Solid line", "72", "65", "73", "0", "40", "0.0",
                  "0", "LTYPE", "2", "DASHED", "70", "0", "3", "Dashed __ __", "72", "65", "73", "2", "40", "600.0",
                  "49", "400.0", "49", "-200.0",
                  "0", "ENDTAB",
                  "0", "TABLE", "2", "LAYER", "70", str(len(self.LAYERS))]
        for name, color, lt in self.LAYERS:
            tables += ["0", "LAYER", "2", name, "70", "0", "62", str(color), "6", lt]
        tables += ["0", "ENDTAB", "0", "ENDSEC"]
        ents = ["0", "SECTION", "2", "ENTITIES"] + self.e + ["0", "ENDSEC", "0", "EOF"]
        txt = "\r\n".join(head + tables + ents) + "\r\n"
        return txt.encode("cp949", errors="replace")


def to_dxf(project: dict, catalog: Catalog, validation: dict | None = None) -> bytes:
    sp = project["space"]
    W, D = sp["width"], sp["depth"]
    d = _Dxf()
    t = 200.0
    labels = S.letter_labels(sp)
    for wall in S.WALLS:
        L = S.wall_length(sp, wall)
        ops = sorted(S.openings(sp, wall), key=lambda o: o["start"])
        cur = -t
        segs = []
        for o in ops:
            segs.append((cur, o["start"]))
            cur = o["start"] + o["length"]
        segs.append((cur, L + t))
        for a, b in segs:
            if b <= a:
                continue
            if wall == "front":
                r = G.rect_poly(a, -t, b, 0)
            elif wall == "back":
                r = G.rect_poly(a, D, b, D + t)
            elif wall == "left":
                r = G.rect_poly(-t, a, 0, b)
            else:
                r = G.rect_poly(W, a, W + t, b)
            d.poly("WALL", r)
        for o in ops:
            a, b = o["start"], o["start"] + o["length"]
            p0, p1 = S.wall_point(sp, wall, a, -t / 2), S.wall_point(sp, wall, b, -t / 2)
            d.line("OPENING", p0, p1)
            if o["kind"] == "door":
                hinge = S.wall_point(sp, wall, a, 0)
                tip = S.wall_point(sp, wall, a, o["length"])
                d.line("OPENING", hinge, tip)
            mid = S.wall_point(sp, wall, (a + b) / 2, -t - 400)
            d.text("TEXT", mid, labels.get(o["id"], o["kind"]), 220, center=True)
    for p in sp.get("pillars", []):
        d.poly("PILLAR", S.pillar_poly(p))
    for o in sp.get("outlets", []):
        d.circle("OUTLET", (o["x"], o["y"]), 90)
        d.text("OUTLET", (o["x"] + 150, o["y"] + 150), o.get("label") or o["id"], 150)
    for pl in project.get("placements", []):
        prod = catalog.get(pl["product"])
        if not prod:
            continue
        mount = pl.get("mount") or prod["default_mount"]
        layer = "PRODUCT_CEILING" if mount in ("ceiling", "ceiling_hang") else "PRODUCT"
        poly = S.placement_poly(pl, prod)
        d.poly(layer, poly)
        c = G.centroid(poly)
        d.text("TEXT", (c[0], c[1] + 350), prod["short"], 180, center=True)
    for f in project.get("fixtures", []):
        poly = S.fixture_poly(f)
        d.poly("FIXTURE", poly)
        c = G.centroid(poly)
        d.text("FIXTURE", c, f.get("label") or f["type"], 160, center=True)
    for z in project.get("zones", []):
        d.poly("ZONE", G.rect_poly(z["x0"], z["y0"], z["x1"], z["y1"]))
        d.text("ZONE", (z["x0"] + 200, z["y0"] + 450), f"{z['no']} {z.get('name', '')}", 260)
    fl = (validation or {}).get("flow") or {}
    path = fl.get("path") or []
    for a, b in zip(path, path[1:]):
        d.line("FLOW", a, b)
    # 치수: 전체 폭·깊이
    d.line("DIM", (0, -1500), (W, -1500))
    d.text("DIM", (W / 2, -1650), f"{W:,.0f}", 250, center=True)
    d.line("DIM", (-1500, 0), (-1500, D))
    d.text("DIM", (-1650, D / 2), f"{D:,.0f}", 250, center=True, rot=90)
    d.text("TEXT", (0, D + 1200), f"{sp.get('name', '')} · 단위 mm · 원점(0,0) = 정면 왼쪽 모서리 · Winmate 2D 조감도 PoC", 250)
    return d.build()


# ── XLSX ──

def _col(n: int) -> str:
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _sheet_xml(rows: list[list], widths: list[int], bold_rows: set[int]) -> str:
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
           '<sheetViews><sheetView workbookViewId="0"/></sheetViews><cols>']
    for i, w in enumerate(widths):
        out.append(f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>')
    out.append("</cols><sheetData>")
    for r, row in enumerate(rows):
        out.append(f'<row r="{r + 1}">')
        for c, v in enumerate(row):
            ref = f"{_col(c)}{r + 1}"
            st = ' s="1"' if r in bold_rows else ""
            if v is None or v == "":
                continue
            if isinstance(v, bool):
                v = "예" if v else "아니오"
            if isinstance(v, (int, float)):
                st2 = ' s="2"' if (isinstance(v, int) or float(v).is_integer()) and abs(v) >= 1000 and not st else st
                out.append(f'<c r="{ref}"{st2}><v>{v}</v></c>')
            else:
                out.append(f'<c r="{ref}" t="inlineStr"{st}><is><t xml:space="preserve">{escape(str(v))}</t></is></c>')
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def to_xlsx(sheets: list[tuple[str, list[list], list[int], set[int]]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                   + "".join(f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                             for i in range(len(sheets))) + "</Types>")
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                   '</Relationships>')
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(f'<sheet name="{escape(n)}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, (n, *_r) in enumerate(sheets))
                   + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i + 1}.xml"/>'
                             for i in range(len(sheets)))
                   + f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                   + "</Relationships>")
        z.writestr("xl/styles.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                   '<fonts count="2"><font><sz val="10"/><name val="맑은 고딕"/></font><font><b/><sz val="10"/><name val="맑은 고딕"/></font></fonts>'
                   '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
                   '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
                   '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
                   '<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
                   '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
                   '<xf numFmtId="3" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs>'
                   '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
                   '</styleSheet>')
        for i, (name, rows, widths, bold) in enumerate(sheets):
            z.writestr(f"xl/worksheets/sheet{i + 1}.xml", _sheet_xml(rows, widths, bold))
    return buf.getvalue()


def qty_workbook(project: dict, catalog: Catalog, validation: dict | None = None, include_fixtures: bool = True,
                 today: str | None = None) -> bytes:
    today = today or dt.date.today().isoformat()
    sp = project["space"]
    rows = qty_rows(project, catalog)
    head = [["프로젝트", project.get("proposal") or project.get("customer") or ""],
            ["공간", f"{sp.get('name', '')} · {sp['width']:,.0f} × {sp['depth']:,.0f} mm · 층고 {sp['height']:,.0f}"],
            ["도면", f"v{project.get('version', 1)} · 작성 {today} · 단가 미포함"], []]
    hdr = ["No", "제품", "모델 코드", "제품명", "설치 방식", "존", "위치", "수량", "권장 수량", "외형 W×H×D (mm)", "화면 가로×세로 (mm)",
           "소비전력 (W)", "무게 (kg)", "근거 룰", "식", "치수 출처"]
    t1 = head + [hdr]
    bold = {len(head)}
    total = 0
    for i, r in enumerate(rows):
        total += r["qty"]
        t1.append([i + 1, r["short"], r["code"], r["name"], r["mount"], r["zones"], r["anchor"], r["qty"], r["qty_rec"],
                   r["dims"], r["screen"], r["power_w"], r["weight_kg"], r["rule_ids"], r["formula"], r["source"]])
    t1.append(["", f"합계 {len(rows)}종", "", "", "", "", "", total])
    bold.add(len(t1) - 1)
    if include_fixtures and project.get("fixtures"):
        t1.append([])
        t1.append(["", "집기 (동선 검토용 · 참고)"])
        bold.add(len(t1) - 1)
        counts: dict[str, list] = {}
        for f in project["fixtures"]:
            counts.setdefault(f.get("label", f["type"]).rsplit(" ", 1)[0] if f["type"] == "bench" else f.get("label", f["type"]), []).append(f)
        for k, fs in counts.items():
            t1.append(["", k, "", f"{fs[0]['w']:,.0f} × {fs[0]['d']:,.0f} mm", "", "", "", len(fs)])
    zone_of = _zone_of(project)
    met = (validation or {}).get("metrics", {}).get("placements", {})
    t2 = [["ID", "제품", "모델 코드", "X (mm)", "Y (mm)", "회전 (°)", "하단 높이 (mm)", "화면 가로×세로 (mm)", "설치 방식", "존",
           "가까운 콘센트", "배선 거리 (m)"]]
    for pl in project.get("placements", []):
        prod = catalog.get(pl["product"])
        if not prod:
            continue
        sw, sh = screen_size(prod, bool(pl.get("portrait")))
        z = zone_of(pl)
        pw = (met.get(pl["id"]) or {}).get("power") or {}
        t2.append([pl["id"], prod["short"], prod["code"], round(pl["x"]), round(pl["y"]), round(pl.get("rot", 0)),
                   round(pl.get("bottom", 0)), f"{sw:,.0f} × {sh:,.0f}", MOUNT_NAMES.get(pl.get("mount") or prod["default_mount"], ""),
                   f"존 {z['no']}" if z else "", pw.get("outlet") or "", round(pw["mm"] / 1000, 1) if pw.get("mm") is not None else ""])
    t3 = [["ID", "종류", "이름", "X (mm)", "Y (mm)", "가로 (mm)", "깊이 (mm)", "높이 (mm)", "회전 (°)"]]
    for f in project.get("fixtures", []):
        t3.append([f["id"], f["type"], f.get("label", ""), f["x"], f["y"], f["w"], f["d"], f.get("h", ""), f.get("rot", 0)])
    t4 = [["존", "이름", "x0", "y0", "x1", "y1", "면적 (㎡)", "포인트 문구"]]
    for z in project.get("zones", []):
        a = (z["x1"] - z["x0"]) * (z["y1"] - z["y0"]) / 1e6
        t4.append([z["no"], z.get("name", ""), z["x0"], z["y0"], z["x1"], z["y1"], round(a, 1), z.get("point", "")])
    t5 = [["수준", "룰", "제목", "내용"]]
    for w in (validation or {}).get("warnings", []):
        t5.append([{"error": "오류", "warn": "경고", "info": "참고", "memo": "메모"}.get(w["level"], w["level"]) + (" (무시)" if w.get("ignored") else ""),
                   w["rule_id"], w["title"], w["detail"]])
    for n in project.get("notes", []):
        t5.append(["메모", n.get("rule_id") or "", n["id"], n["text"]])
    return to_xlsx([("제품 수량표", t1, [5, 12, 18, 30, 12, 12, 22, 7, 9, 22, 18, 11, 9, 28, 60, 60], bold),
                    ("배치 좌표", t2, [8, 12, 18, 9, 9, 8, 13, 18, 12, 8, 12, 12], {0}),
                    ("집기", t3, [6, 16, 18, 9, 9, 9, 9, 9, 8], {0}),
                    ("존", t4, [6, 18, 8, 8, 8, 8, 10, 40], {0}),
                    ("검토", t5, [10, 28, 26, 70], {0})])


def qty_csv(project: dict, catalog: Catalog) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["제품", "모델 코드", "설치 방식", "존", "위치", "수량", "외형 W×H×D (mm)", "근거 룰"])
    for r in qty_rows(project, catalog):
        w.writerow([r["short"], r["code"], r["mount"], r["zones"], r["anchor"], r["qty"], r["dims"], r["rule_ids"]])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def proposal_payload(project: dict, catalog: Catalog, validation: dict | None = None) -> dict:
    """B2B 제안서 시트(SM-A 공간 맵 · SM-B 수량표 · ZP-A 존별 포인트)로 넘길 데이터."""
    rows = qty_rows(project, catalog)
    zone_of = _zone_of(project)
    zp = []
    for z in project.get("zones", []):
        items = {}
        for pl in project.get("placements", []):
            if zone_of(pl) is z:
                pr = catalog.get(pl["product"])
                items[pr["short"]] = items.get(pr["short"], 0) + 1
        zp.append({"no": z["no"], "name": z.get("name", ""), "products": [{"short": k, "qty": v} for k, v in items.items()],
                   "point": z.get("point", ""), "rect_mm": [z["x0"], z["y0"], z["x1"], z["y1"]]})
    return {
        "source": {"kind": "2d_birdseye", "project_id": project.get("id"), "version": project.get("version", 1),
                   "space": project["space"].get("name"), "generated": dt.datetime.now().isoformat(timespec="seconds")},
        "sheets": {
            "SM-A": {"title": "공간별 제품 · 공간 맵", "drawing": "plan.svg", "summary": f"{len(rows)}종 {sum(r['qty'] for r in rows)}대"},
            "SM-B": {"title": "공간별 제품 · 수량표", "rows": [{k: r[k] for k in ("short", "code", "name", "mount", "zones", "qty")} for r in rows]},
            "ZP-A": {"title": "조감도 · 존별 포인트", "drawing": "zones.svg", "zones": zp},
        },
        "review": (validation or {}).get("summary"),
        "notes": [n["text"] for n in project.get("notes", [])],
    }


def bundle_zip(project: dict, catalog: Catalog, items: list[str], paper: str = "A3", include_fixtures: bool = True,
               validation: dict | None = None, today: str | None = None) -> bytes:
    buf = io.BytesIO()
    name = project["space"].get("name") or project.get("title") or "birdseye"
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if "plan" in items:
            z.writestr("plan.svg", plan_svg(project, catalog, "plan", paper, validation=validation, today=today))
        if "zones" in items:
            z.writestr("zones.svg", plan_svg(project, catalog, "zones", paper, validation=validation, today=today))
        if "flow" in items:
            z.writestr("flow.svg", plan_svg(project, catalog, "flow", paper, validation=validation, today=today))
        if "qty" in items:
            z.writestr("qty.xlsx", qty_workbook(project, catalog, validation, include_fixtures, today))
            z.writestr("qty.csv", qty_csv(project, catalog))
        if "cad" in items:
            z.writestr("layout.dxf", to_dxf(project, catalog, validation))
        z.writestr("proposal_payload.json", json.dumps(proposal_payload(project, catalog, validation), ensure_ascii=False, indent=1))
        z.writestr("project.json", json.dumps(project, ensure_ascii=False, indent=1))
        z.writestr("README.txt", "\n".join([
            f"{name} — Winmate 2D 조감도 PoC 내보내기",
            f"버전 v{project.get('version', 1)} · {today or dt.date.today().isoformat()}",
            "",
            "plan.svg / zones.svg / flow.svg : 도면(종이 mm 단위, 100% 인쇄 시 표제란 축척과 일치). 브라우저에서 열어 PDF로 인쇄할 수 있어요.",
            "qty.xlsx : 제품 수량표 · 배치 좌표 · 집기 · 존 · 검토 / qty.csv : 수량표만",
            "layout.dxf : CAD(R12, 단위 mm, 원점 = 정면 왼쪽 모서리, Y는 아래로 음수)",
            "proposal_payload.json : 제안서 시트(SM-A · SM-B · ZP-A)로 넘길 데이터",
            "project.json : 작업 원본(다시 불러오기용)",
            "",
            "치수·사양은 winmate-kb(samsung.com/sec/business 수집본) 원문 값이고, 배치 룰 계수는 PoC 임시값이에요.",
        ]))
    return buf.getvalue()
