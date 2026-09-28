"""Drawing sheet: a list of 2D primitives in paper millimetres (origin top-left, y down), rendered to SVG and to PDF
(ReportLab canvas, vector) from the same list — both outputs are identical by construction.

Line weights follow ISO 128 pairs (0.5 visible / 0.25 hidden / 0.18 dimension, centre, tangent / 0.13 hatch).
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

from reportlab.pdfbase.pdfmetrics import stringWidth

SIZES = {"A3": (420.0, 297.0), "A4": (297.0, 210.0)}
FONT, FONT_B = "Helvetica", "Helvetica-Bold"
SVG_FONT = "Helvetica, Arial, sans-serif"

INK, INK2, INK3 = "#111111", "#5F5E5A", "#8A8883"
MEASURED = "#1F8A4C"
WARN_INK, WARN_SOFT = "#C43C00", "#FFF1EA"

# style → (width mm, colour, dash mm | None)
STYLES = {
    "visible": (0.5, INK, None),
    "smooth": (0.18, INK3, None),
    "hidden": (0.25, INK, (2.0, 1.0)),
    "center": (0.18, INK, (7.0, 1.2, 1.0, 1.2)),
    "dim": (0.18, INK, None),
    "leader": (0.18, INK, None),
    "hatch": (0.13, INK, None),
    "thin": (0.25, INK, None),
    "rule": (0.18, INK, None),
    "frame": (0.7, INK, None),
    "cut": (0.7, INK, None),
}


def text_width(s: str, size: float, bold: bool = False) -> float:
    return stringWidth(s, FONT_B if bold else FONT, size)


@dataclass
class Sheet:
    size: str
    items: list[tuple] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def w(self) -> float:
        return SIZES[self.size][0]

    @property
    def h(self) -> float:
        return SIZES[self.size][1]

    # ---- primitives
    def line(self, pts, style: str = "visible") -> None:
        pts = [(float(x), float(y)) for x, y in pts]
        if len(pts) >= 2:
            self.items.append(("pl", pts, style))

    def rect(self, x: float, y: float, w: float, h: float, style: str = "thin", fill: str | None = None) -> None:
        self.items.append(("rect", x, y, w, h, style, fill))

    def circle(self, x: float, y: float, r: float, style: str | None = "thin", fill: str | None = None) -> None:
        self.items.append(("circle", x, y, r, style, fill))

    def poly(self, pts, fill: str = INK) -> None:
        self.items.append(("poly", [(float(x), float(y)) for x, y in pts], fill))

    def text(self, x: float, y: float, s: str, size: float = 2.5, anchor: str = "start", bold: bool = False,
             rot: float = 0.0, color: str = INK) -> None:
        self.items.append(("text", x, y, str(s), size, anchor, bold, rot, color))

    # ---- renderers
    def svg(self) -> str:
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w:g}mm" height="{self.h:g}mm" '
               f'viewBox="0 0 {self.w:g} {self.h:g}" font-family="{SVG_FONT}">',
               f'<title>{escape(self.meta.get("title", "Drawing"))}</title>',
               f'<rect x="0" y="0" width="{self.w:g}" height="{self.h:g}" fill="#FFFFFF"/>']
        for it in self.items:
            k = it[0]
            if k == "pl":
                out.append(f'<polyline points="{_pts(it[1])}" fill="none" {_stroke(it[2])}/>')
            elif k == "rect":
                _, x, y, w, h, st, fill = it
                out.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" fill="{fill or "none"}" '
                           f'{_stroke(st) if st else "stroke=\"none\""}/>')
            elif k == "circle":
                _, x, y, r, st, fill = it
                out.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{r:.3f}" fill="{fill or "none"}" '
                           f'{_stroke(st) if st else "stroke=\"none\""}/>')
            elif k == "poly":
                out.append(f'<polygon points="{_pts(it[1])}" fill="{it[2]}" stroke="none"/>')
            elif k == "text":
                _, x, y, s, size, anchor, bold, rot, color = it
                tr = f' transform="rotate({rot:g} {x:.3f} {y:.3f})"' if rot else ""
                out.append(f'<text x="{x:.3f}" y="{y:.3f}" font-size="{size:g}" text-anchor="{anchor}" fill="{color}"'
                           f'{" font-weight=\"bold\"" if bold else ""}{tr}>{escape(s)}</text>')
        out.append("</svg>")
        return "\n".join(out)

    def draw_pdf(self, c) -> None:
        """Draw on a ReportLab canvas whose current page is this sheet's size (in points)."""
        from reportlab.lib.units import mm

        c.saveState()
        c.translate(0, self.h * mm)
        c.scale(mm, -mm)
        c.setLineCap(1)
        c.setLineJoin(1)
        for it in self.items:
            k = it[0]
            if k == "pl":
                _apply(c, it[2])
                p = c.beginPath()
                p.moveTo(*it[1][0])
                for pt in it[1][1:]:
                    p.lineTo(*pt)
                c.drawPath(p, stroke=1, fill=0)
            elif k in ("rect", "circle"):
                st, fill = it[-2], it[-1]
                if st:
                    _apply(c, st)
                if fill:
                    c.setFillColor(fill)
                if k == "rect":
                    c.rect(it[1], it[2], it[3], it[4], stroke=1 if st else 0, fill=1 if fill else 0)
                else:
                    c.circle(it[1], it[2], it[3], stroke=1 if st else 0, fill=1 if fill else 0)
            elif k == "poly":
                c.setFillColor(it[2])
                p = c.beginPath()
                p.moveTo(*it[1][0])
                for pt in it[1][1:]:
                    p.lineTo(*pt)
                p.close()
                c.drawPath(p, stroke=0, fill=1)
            elif k == "text":
                _, x, y, s, size, anchor, bold, rot, color = it
                c.saveState()
                c.translate(x, y)
                c.scale(1, -1)
                if rot:
                    c.rotate(-rot)
                c.setFillColor(color)
                c.setFont(FONT_B if bold else FONT, size)
                {"start": c.drawString, "middle": c.drawCentredString, "end": c.drawRightString}[anchor](0, 0, s)
                c.restoreState()
        c.restoreState()

    def pdf(self) -> bytes:
        return pdf_of([self])


def pdf_of(sheets: list[Sheet], title: str = "Drawings") -> bytes:
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(sheets[0].w * mm, sheets[0].h * mm), pageCompression=1)
    c.setTitle(title)
    c.setAuthor("PhysicalLovableX")
    c.setSubject("Generated from CAD — verify before release")
    for s in sheets:
        c.setPageSize((s.w * mm, s.h * mm))
        s.draw_pdf(c)
        c.showPage()
    c.save()
    return buf.getvalue()


def _pts(pts) -> str:
    return " ".join(f"{x:.3f},{y:.3f}" for x, y in pts)


def _stroke(style: str) -> str:
    w, col, dash = STYLES[style]
    d = f' stroke-dasharray="{",".join(f"{x:g}" for x in dash)}"' if dash else ""
    return f'stroke="{col}" stroke-width="{w:g}" stroke-linecap="round" stroke-linejoin="round"{d}'


def _apply(c, style: str) -> None:
    w, col, dash = STYLES[style]
    c.setStrokeColor(col)
    c.setLineWidth(w)
    c.setDash(list(dash) if dash else [])
