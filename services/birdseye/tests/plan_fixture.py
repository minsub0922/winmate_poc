"""벡터 도면 PDF 픽스처(AC 10 — 외벽 4 · 전면 창 2구간 · 문 2 · 기둥 600×600 2 · EV/계단 코어 · 「1:100」 · 치수 「24.0 m」, 환산 23.6 m).

외부 라이브러리 없이 PDF 1.4 를 직접 쓴다(선 · 사각형 · 베지어 호 · Helvetica 글자). 좌표는 화면 기준 mm(축척 1:100 이면 1 mm = 0.1 m).
"""
from __future__ import annotations

PT_PER_MM = 72.0 / 25.4


class Page:
    def __init__(self, w_mm: float = 420, h_mm: float = 297):
        self.w = w_mm * PT_PER_MM
        self.h = h_mm * PT_PER_MM
        self.ops: list[str] = []

    def _p(self, x_mm: float, y_mm: float) -> tuple[float, float]:
        return x_mm * PT_PER_MM, self.h - y_mm * PT_PER_MM

    def line(self, x0: float, y0: float, x1: float, y1: float, width_mm: float = 0.2) -> None:
        a, b = self._p(x0, y0)
        c, d = self._p(x1, y1)
        self.ops.append(f"{width_mm * PT_PER_MM:.3f} w {a:.3f} {b:.3f} m {c:.3f} {d:.3f} l S")

    def rect(self, x: float, y: float, w: float, h: float, fill: bool = False, width_mm: float = 0.2) -> None:
        a, b = self._p(x, y + h)
        op = "f" if fill else "S"
        self.ops.append(f"{width_mm * PT_PER_MM:.3f} w {a:.3f} {b:.3f} {w * PT_PER_MM:.3f} {h * PT_PER_MM:.3f} re {op}")

    def arc(self, cx: float, cy: float, r: float, a0: float, a1: float, width_mm: float = 0.2) -> None:
        """사분원(화면 기준 각도, 도) — 베지어 한 개."""
        import math

        k = 0.5522847498 * r
        t0, t1 = math.radians(a0), math.radians(a1)
        p0 = (cx + r * math.cos(t0), cy + r * math.sin(t0))
        p3 = (cx + r * math.cos(t1), cy + r * math.sin(t1))
        d0 = (-math.sin(t0), math.cos(t0))
        d1 = (-math.sin(t1), math.cos(t1))
        sgn = 1 if a1 > a0 else -1
        p1 = (p0[0] + d0[0] * k * sgn, p0[1] + d0[1] * k * sgn)
        p2 = (p3[0] - d1[0] * k * sgn, p3[1] - d1[1] * k * sgn)
        pts = [self._p(*p) for p in (p0, p1, p2, p3)]
        self.ops.append(f"{width_mm * PT_PER_MM:.3f} w {pts[0][0]:.3f} {pts[0][1]:.3f} m "
                        f"{pts[1][0]:.3f} {pts[1][1]:.3f} {pts[2][0]:.3f} {pts[2][1]:.3f} {pts[3][0]:.3f} {pts[3][1]:.3f} c S")

    def text(self, x: float, y: float, s: str, size_pt: float = 9) -> None:
        a, b = self._p(x, y)
        safe = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        self.ops.append(f"BT /F1 {size_pt:.1f} Tf {a:.3f} {b:.3f} Td ({safe}) Tj ET")


def write_pdf(page: Page) -> bytes:
    content = ("\n".join(page.ops)).encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page.w:.3f} {page.h:.3f}] /Contents 4 0 R "
        f"/Resources << /Font << /F1 5 0 R >> >> >>".encode(),
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def lobby_plan(annotated_m: float = 24.0, drawn_m: float = 23.6, depth_m: float | None = None, scale_text: bool = True) -> bytes:
    """정면(위) 벽 = 전면 유리창 2구간 + 가운데 주출입구, 뒤쪽 벽 오른쪽에 문, 왼쪽 아래 EV · 계단 코어, 가운데 기둥 2개."""
    s = drawn_m / annotated_m            # 표기 → 그림 비율
    W = drawn_m * 10                     # 1:100 → mm
    D = (depth_m if depth_m is not None else 16.5 * s) * 10
    ox, oy = 60.0, 50.0
    pg = Page()
    wall = 2.0                           # 0.2 m 벽 = 2 mm
    k = 10 * s                           # 표기 1 m 당 그림 mm

    def X(m: float) -> float:
        return ox + m * k

    def Y(m: float) -> float:
        return oy + m * k

    # 정면 벽: 0~1 m 벽 · 1~11 창 · 11~13 문 · 13~23 창 · 23~24 벽(표기 m 기준)
    pg.line(X(0), Y(0), X(1), Y(0), wall)
    pg.line(X(23), Y(0), X(24), Y(0), wall)
    for a, b in ((1, 11), (13, 23)):
        for dy in (-0.07, 0.0, 0.07):
            pg.line(X(a), Y(0) + dy * k, X(b), Y(0) + dy * k, 0.15)
    pg.arc(X(11), Y(0), 2 * k, 0, 90, 0.15)           # 주출입구(2.0 m)
    pg.line(X(11), Y(0), X(11), Y(2.0), 0.15)
    # 오른쪽 · 뒤쪽 · 왼쪽 벽
    depth_e = D / k
    pg.line(X(24), Y(0), X(24), Y(depth_e), wall)
    pg.line(X(24), Y(depth_e), X(22.0), Y(depth_e), wall)
    pg.line(X(21.1), Y(depth_e), X(0), Y(depth_e), wall)
    pg.arc(X(22.0), Y(depth_e), 0.9 * k, 180, 270, 0.15)  # 뒤쪽 문(0.9 m)
    pg.line(X(0), Y(depth_e), X(0), Y(0), wall)
    # 기둥 600 × 600 2개
    for cx in (8.2, 15.8):
        pg.rect(X(cx) - 3 * s, Y(8.0 * (depth_e / 16.5)) - 3 * s, 6 * s, 6 * s, fill=True)
    # 코어(EV · 계단) — 왼쪽 아래 4 × 4 m
    cy0 = depth_e - 4.0
    pg.rect(X(0), Y(cy0), 4 * k, 4 * k, fill=False, width_mm=0.3)
    for i in range(1, 8):
        pg.line(X(0) + i * 5 * s, Y(cy0), X(0), Y(cy0) + i * 5 * s, 0.1)
    pg.text(X(1.2), Y(cy0 + 1.8), "EV", 9)
    pg.text(X(1.2), Y(cy0 + 2.8), "STAIRS", 7)
    # 치수 · 축척 · 제목
    pg.line(X(0), Y(0) - 12, X(24), Y(0) - 12, 0.1)
    pg.text(X(11.2), Y(0) - 14, f"{annotated_m:.1f} m", 9)
    if scale_text:
        pg.text(ox, oy + D + 25, "LOBBY PLAN 1F  SCALE 1:100", 9)
    pg.text(X(11.2), Y(0) + 25, "ENTRANCE", 6)
    return write_pdf(pg)


if __name__ == "__main__":  # pragma: no cover
    import sys

    open(sys.argv[1] if len(sys.argv) > 1 else "lobby_plan_1F.pdf", "wb").write(lobby_plan())
