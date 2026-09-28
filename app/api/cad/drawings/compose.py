"""Sheet composition: frame, title block, views laid out at a standard scale, dimensions, callouts, section A-A,
notes, and the assembly sheet (balloons tied to BOM lines + parts list).

Dimension selection rules
- every sheet: overall length (X, under the top view), height (Z, left of the front view), width (Y, under the
  left view) — measured on the solid's bounding box, general tolerance ISO 2768-m printed with the value;
- critical features (measured on the B-rep): holes (concave full cylinders / cones) and bosses (convex) grouped by
  diameter with a leader in the view that shows them as circles, hole pattern pitch; wall thickness in section A-A
  (hollow parts only); fillet radii as a note, never dimensioned;
- the isometric view is for reference only (not to scale for measurement).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from api.cad.drawings import geom as G
from api.cad.drawings.sheet import INK, INK2, INK3, MEASURED, WARN_INK, WARN_SOFT, Sheet, text_width

STANDARD = [50, 20, 10, 5, 2, 1, 1 / 2, 1 / 5, 1 / 10, 1 / 20, 1 / 50, 1 / 100]
GAP = 17.0  # between ortho views (holds dimensions and callouts)
TB_W, TB_H, WARN_H = 180.0, 34.0, 6.0
DISCLAIMER = "Generated from CAD — verify before release"

ISO2768M = [(0.5, 3, 0.1), (3, 6, 0.1), (6, 30, 0.2), (30, 120, 0.3), (120, 400, 0.5), (400, 1000, 0.8),
            (1000, 2000, 1.2), (2000, 4000, 2.0), (4000, 8000, 3.0)]


def tol(v: float) -> float:
    for lo, hi, t in ISO2768M:
        if lo <= v <= hi:
            return t
    return 0.1 if v < 0.5 else 3.0


def fmt(v: float) -> str:
    d = 2 if abs(v) < 10 else 1
    s = f"{v:.{d}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def scale_label(s: float) -> str:
    if s >= 1:
        return f"{float(f'{s:.2g}'):g}:1"
    return f"1:{float(f'{1 / s:.2g}'):g}"


# --------------------------------------------------------------------------- data


@dataclass
class PartDef:
    item: int
    key: str
    name: str
    material: str
    finish: str | None
    qty: int
    solids: list = field(default_factory=list)
    bom_id: str | None = None
    bom_part: str | None = None
    kind: str = "part"  # part | moulded
    wall_spec: float | None = None


@dataclass
class Meta:
    product: str
    pid: str
    version: int
    date: str
    source: str  # STEP file name the geometry was measured on


@dataclass
class Placed:
    view: G.View
    proj: G.Proj
    s: float
    ox: float
    oy: float
    bb: tuple  # model 2D bbox (umin, vmin, umax, vmax)

    def p(self, u: float, v: float) -> tuple[float, float]:
        return self.ox + (u - self.bb[0]) * self.s, self.oy + (self.bb[3] - v) * self.s

    def p3(self, pt) -> tuple[float, float]:
        return self.p(*self.view.p2(pt))

    @property
    def box(self) -> tuple[float, float, float, float]:
        return (self.ox, self.oy, self.ox + (self.bb[2] - self.bb[0]) * self.s, self.oy + (self.bb[3] - self.bb[1]) * self.s)


# --------------------------------------------------------------------------- primitives


def arrow(sh: Sheet, tip, towards) -> None:
    """Filled arrowhead (3 mm, ~18°) at `tip`, pointing away from `towards`."""
    tx, ty = tip
    dx, dy = tip[0] - towards[0], tip[1] - towards[1]
    n = math.hypot(dx, dy) or 1.0
    dx, dy = dx / n, dy / n
    L, W = 2.6, 0.45
    bx, by = tx - dx * L, ty - dy * L
    sh.poly([(tx, ty), (bx - dy * W, by + dx * W), (bx + dy * W, by - dx * W)])


def dim_h(sh: Sheet, x1: float, x2: float, y_from1: float, y_from2: float, y: float, label: str) -> None:
    """Horizontal linear dimension between x1 and x2 with the dimension line at y."""
    sgn = 1 if y > max(y_from1, y_from2) else -1
    for x, yf in ((x1, y_from1), (x2, y_from2)):
        sh.line([(x, yf + sgn * 1.0), (x, y + sgn * 1.5)], "dim")
    w = text_width(label, 2.5)
    if x2 - x1 > w + 7:
        sh.line([(x1, y), (x2, y)], "dim")
        arrow(sh, (x1, y), (x2, y))
        arrow(sh, (x2, y), (x1, y))
        sh.text((x1 + x2) / 2, y - 0.9, label, 2.5, "middle")
    else:  # arrows outside, text beside
        sh.line([(x1 - 5, y), (x2 + 4 + w + 1, y)], "dim")
        arrow(sh, (x1, y), (x1 - 5, y))
        arrow(sh, (x2, y), (x2 + 5, y))
        sh.text(x2 + 4, y - 0.9, label, 2.5, "start")


def dim_v(sh: Sheet, y1: float, y2: float, x_from1: float, x_from2: float, x: float, label: str) -> None:
    sgn = 1 if x > max(x_from1, x_from2) else -1
    for yy, xf in ((y1, x_from1), (y2, x_from2)):
        sh.line([(xf + sgn * 1.0, yy), (x + sgn * 1.5, yy)], "dim")
    w = text_width(label, 2.5)
    lo, hi = min(y1, y2), max(y1, y2)
    if hi - lo > w + 7:
        sh.line([(x, lo), (x, hi)], "dim")
        arrow(sh, (x, lo), (x, hi))
        arrow(sh, (x, hi), (x, lo))
        sh.text(x - 0.9, (lo + hi) / 2, label, 2.5, "middle", rot=-90)
    else:
        sh.line([(x, lo - 5), (x, hi + 5)], "dim")
        arrow(sh, (x, lo), (x, lo - 5))
        arrow(sh, (x, hi), (x, hi + 5))
        sh.text(x - 0.9, hi + 6, label, 2.5, "end", rot=-90)


def leader(sh: Sheet, anchor, knee, label: str, right: bool = True, dot: bool = False) -> None:
    w = text_width(label, 2.5)
    end = (knee[0] + (w + 2 if right else -(w + 2)), knee[1])
    sh.line([anchor, knee, end], "leader")
    if dot:
        sh.circle(anchor[0], anchor[1], 0.45, None, INK)
    else:
        arrow(sh, anchor, knee)
    sh.text(knee[0] + (1 if right else -1), knee[1] - 0.8, label, 2.5, "start" if right else "end")


def draw_proj(sh: Sheet, pl: Placed, hidden: bool = True) -> None:
    for pts in pl.proj.smooth:
        sh.line([pl.p(u, v) for u, v in pts], "smooth")
    if hidden:
        for pts in pl.proj.hidden:
            sh.line([pl.p(u, v) for u, v in pts], "hidden")
    for pts in pl.proj.visible:
        sh.line([pl.p(u, v) for u, v in pts], "visible")


def view_label(sh: Sheet, pl: Placed, text: str, below: float = 0.0, centre: bool = False) -> None:
    x0, _, x1, y1 = pl.box
    if centre:
        sh.text((x0 + x1) / 2, y1 + 5.5 + below, text, 2.2, "middle", color=INK2)
    else:
        sh.text(x1, y1 + 4.2 + below, text, 2.2, "end", color=INK2)


# --------------------------------------------------------------------------- frame + title block


def frame(sh: Sheet) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = 20.0, 10.0, sh.w - 10.0, sh.h - 10.0
    sh.rect(x0, y0, x1 - x0, y1 - y0, "frame")
    for x in ((x0 + x1) / 2,):  # centring marks
        sh.line([(x, 0), (x, y0)], "frame")
        sh.line([(x, y1), (x, sh.h)], "frame")
    for y in ((y0 + y1) / 2,):
        sh.line([(0, y), (x0, y)], "frame")
        sh.line([(x1, y), (sh.w, y)], "frame")
    return x0, y0, x1, y1


def projection_symbol(sh: Sheet, cx: float, cy: float) -> None:
    """ISO 128 / ISO 5456-2 first-angle symbol: truncated cone side view left, end view right."""
    h = 2.4
    x = cx - 5.5
    sh.line([(x - 3, cy - h / 2), (x + 3, cy - h), (x + 3, cy + h), (x - 3, cy + h / 2), (x - 3, cy - h / 2)], "thin")
    sh.line([(x - 4, cy), (x + 4, cy)], "center")
    sh.circle(cx + 3.5, cy, h, "thin")
    sh.circle(cx + 3.5, cy, h / 2, "thin")
    sh.line([(cx + 3.5 - h - 1, cy), (cx + 3.5 + h + 1, cy)], "center")


def title_block(sh: Sheet, fr, f: dict) -> tuple[float, float]:
    x1, y1 = fr[2], fr[3]
    x0, y0 = x1 - TB_W, y1 - TB_H
    # disclaimer strip
    sh.rect(x0, y0 - WARN_H, TB_W, WARN_H, "thin", WARN_SOFT)
    sh.text(x0 + TB_W / 2, y0 - WARN_H / 2 + 0.95, DISCLAIMER.upper(), 2.5, "middle", bold=True, color=WARN_INK)
    sh.rect(x0, y0, TB_W, TB_H, "frame")
    rows = [(0.0, 10.0), (10.0, 8.0), (18.0, 8.0), (26.0, 8.0)]
    for ry, _ in rows[1:]:
        sh.line([(x0, y0 + ry), (x1, y0 + ry)], "rule")

    def cell(cx: float, cy: float, w: float, h: float, cap: str, val: str, size: float = 2.6, bold: bool = False) -> None:
        sh.line([(cx, cy), (cx, cy + h)], "rule")
        sh.text(cx + 1.2, cy + 2.4, cap, 1.55, color=INK3)
        v = val
        while text_width(v, size, bold) > w - 2.4 and len(v) > 4:
            v = v[:-2].rstrip() + "…" if not v.endswith("…") else v[:-3].rstrip() + "…"
        sh.text(cx + 1.2, cy + h - 1.6, v, size, bold=bold)

    # row 1: brand | title
    sh.text(x0 + 2, y0 + 4.6, "PhysicalLovableX", 3.0, bold=True)
    sh.text(x0 + 2, y0 + 8.2, "Generated from CAD", 1.9, color=INK2)
    cell(x0 + 50, y0, 130, 10, "TITLE", f["title"], 3.6, True)
    # row 2
    cell(x0, y0 + 10, 60, 8, "PRODUCT", f["product"])
    cell(x0 + 60, y0 + 10, 60, 8, "MATERIAL", f["material"])
    cell(x0 + 120, y0 + 10, 60, 8, "FINISH", f["finish"])
    # row 3
    cell(x0, y0 + 18, 26, 8, "SCALE", f["scale"])
    cell(x0 + 26, y0 + 18, 18, 8, "UNITS", "mm")
    cell(x0 + 44, y0 + 18, 46, 8, "GENERAL TOLERANCES", "ISO 2768-m")
    cell(x0 + 90, y0 + 18, 26, 8, "PROJECTION", "")
    projection_symbol(sh, x0 + 104, y0 + 23.4)
    cell(x0 + 116, y0 + 18, 22, 8, "REV", f["rev"], 2.8, True)
    cell(x0 + 138, y0 + 18, 20, 8, "SIZE", f["size"])
    cell(x0 + 158, y0 + 18, 22, 8, "SHEET", f["sheet_no"])
    # row 4
    cell(x0, y0 + 26, 60, 8, "DRAWING NO.", f["dwg_no"], 2.3)
    cell(x0 + 60, y0 + 26, 30, 8, "DATE", f["date"], 2.3)
    sh.line([(x0 + 90, y0 + 26), (x0 + 90, y0 + 34)], "rule")
    sh.text(x0 + 91.2, y0 + 28.4, "LABEL", 1.55, color=INK3)
    sh.circle(x0 + 92.6, y0 + 31.6, 0.9, None, MEASURED)
    sh.text(x0 + 94.6, y0 + 32.4, "Measured — dimensions measured on the CAD (STEP)", 2.1)
    return x0, y0 - WARN_H


def notes_block(sh: Sheet, x: float, y_bottom: float, w: float, lines: list[str]) -> None:
    """NOTES, bottom-aligned at y_bottom, wrapped to width w."""
    size, lh = 2.1, 3.1
    wrapped: list[str] = []
    for i, ln in enumerate(lines, 1):
        words, cur, first = ln.split(), "", True
        for wd in words:
            cand = (cur + " " + wd).strip()
            if text_width(f"{i}. " + cand, size) > w and cur:
                wrapped.append((f"{i}. " if first else "    ") + cur)
                cur, first = wd, False
            else:
                cur = cand
        wrapped.append((f"{i}. " if first else "    ") + cur)
    y = y_bottom - lh * len(wrapped)
    sh.text(x, y - 1.2, "NOTES", 2.4, bold=True)
    for k, ln in enumerate(wrapped):
        sh.text(x, y + 2.6 + k * lh, ln, size)


def base_notes(p: PartDef | None, feats: G.Features | None, meta: Meta, extra: list[str] | None = None) -> list[str]:
    out = [f"Dimensions in mm, measured on the CAD model ({meta.source}); nominal values, label Measured.",
           "General tolerances ISO 2768-m unless stated: ±0.1 (≤6) · ±0.2 (6–30) · ±0.3 (30–120) · ±0.5 (120–400) · "
           "±0.8 (400–1000) · ±1.2 (1000–2000) · ±2 (2000–4000); angles ±0°30'."]
    if p is not None:
        out.append(f"Material: {p.material}." + (f" Finish: {p.finish}." if p.finish else ""))
    if feats is not None and feats.fillets:
        rs = ", ".join(f"R{fmt(r)}" for r in feats.fillets[:6])
        out.append(f"Fillets and rounds as modelled: {rs} (measured). Break sharp edges 0.2–0.5.")
    out += extra or []
    out.append(DISCLAIMER + ": concept-level CAD; critical tolerances are proposals to confirm with the factory.")
    return out


# --------------------------------------------------------------------------- layout


def _fit(ext: dict, area: tuple, iso_ext, iso_min: float, iso_pad: tuple[float, float], with_top: bool, with_left: bool):
    """Largest standard scale s for the ortho group (front, left to its right, top below) leaving the iso view at
    least `iso_min` mm in the free region (right of the group or below it)."""
    ax, ay, aw, ah = area
    fw, fh = ext["front"]
    lw = ext["left"][0] if with_left else 0.0
    th = ext["top"][1] if with_top else 0.0
    ml, mt, mb = 13.0, 12.0, 13.0  # H dim at left; callouts above; L dim below
    best = None
    for s in STANDARD:
        gw = ml + s * fw + (GAP + s * lw if with_left else 0)
        gh = mt + s * fh + (GAP + s * th if with_top else 0) + mb
        if gw > aw or gh > ah:
            continue
        iw, ih = iso_ext
        right = (aw - gw - 6 - iso_pad[0], ah - iso_pad[1])
        below = (aw - iso_pad[0], ah - gh - 4 - iso_pad[1])
        sr = min(right[0] / iw, right[1] / ih) if min(right) > 0 else 0
        sb = min(below[0] / iw, below[1] / ih) if min(below) > 0 else 0
        si, where = (sr, "right") if sr >= sb else (sb, "below")
        cand = (s, si, where, gw, gh)
        if si * max(iw, ih) >= iso_min:
            return cand
        if best is None or si * max(iw, ih) > best[1] * max(iw, ih):
            best = cand
    if best is None:  # nothing fits: smallest scale
        s = STANDARD[-1]
        best = (s, s, "right", ml + s * fw, mt + s * fh)
    return best


def layout(sh: Sheet, projs: dict, area: tuple, iso_min: float, iso_pad=(0.0, 0.0)) -> tuple[dict, float, float]:
    """projs: name → Proj (front required; top/left/iso optional). Returns placements, ortho scale, iso scale."""
    ext = {k: (max(b[2] - b[0], 1e-3), max(b[3] - b[1], 1e-3)) for k, p in projs.items() for b in [p.bbox()]}
    with_top, with_left = "top" in projs, "left" in projs
    iso_ext = ext.get("iso", (1.0, 1.0))
    s, si, where, gw, gh = _fit(ext, area, iso_ext, iso_min, iso_pad, with_top, with_left)
    ax, ay, aw, ah = area
    if "iso" in projs:
        # tidy iso scale: 2 significant digits, never above the ortho scale × 1.6 (keeps the sheet balanced)
        si = min(si, s * 1.6)
    iw, ih = iso_ext[0] * si, iso_ext[1] * si
    if "iso" in projs and where == "right":
        total_w = gw + 6 + iw + iso_pad[0]
        x = ax + max(0.0, (aw - total_w) / 2)
        y = ay + max(0.0, (ah - max(gh, ih + iso_pad[1])) / 2)
    else:
        x = ax + max(0.0, (aw - max(gw, iw + iso_pad[0])) / 2)
        y = ay + max(0.0, (ah - (gh + (ih + 4 + iso_pad[1] if "iso" in projs else 0))) / 2)
    pl: dict[str, Placed] = {}
    fx, fy = x + 13.0, y + 12.0
    fb = projs["front"].bbox()
    pl["front"] = Placed(G.View.of("front"), projs["front"], s, fx, fy, fb)
    fw, fh = ext["front"]
    if with_left:  # same Z reference as the front view (projection lines stay horizontal)
        lb = projs["left"].bbox()
        pl["left"] = Placed(G.View.of("left"), projs["left"], s, fx + s * fw + GAP, fy + (fb[3] - lb[3]) * s, lb)
    if with_top:
        tb = projs["top"].bbox()
        pl["top"] = Placed(G.View.of("top"), projs["top"], s, fx + (tb[0] - fb[0]) * s, fy + s * fh + GAP, tb)
    if "iso" in projs:
        ib = projs["iso"].bbox()
        if where == "right":
            ix = x + gw + 6 + iso_pad[0] / 2
            iy = y + max(0.0, (max(gh, ih) - ih) / 2)
        else:
            ix = x + max(0.0, (max(gw, iw + iso_pad[0]) - iw) / 2)
            iy = y + gh + 4
        pl["iso"] = Placed(G.View.of("iso"), projs["iso"], si, ix, iy, ib)
    return pl, s, si


# --------------------------------------------------------------------------- views + dimensions of one solid


def views_for(solid, defl_paper: float, scale_guess: float, hidden: bool, with_top: bool = True,
              section_x: float | None = None):
    shape = solid.wrapped
    d = defl_paper / max(scale_guess, 1e-3)
    projs = {"front": G.project(shape, G.View.of("front"), d, hidden)}
    if with_top:
        projs["top"] = G.project(shape, G.View.of("top"), d, hidden)
    sec = None
    if section_x is not None:
        try:
            half, polys = G.section(solid, section_x)
            if polys:
                projs["left"] = G.project(half.wrapped, G.View.of("left"), d, False)
                sec = polys
        except Exception:  # noqa: BLE001 — no section: plain left view
            sec = None
    if "left" not in projs:
        projs["left"] = G.project(shape, G.View.of("left"), d, hidden)
    projs["iso"] = G.project(shape, G.View.of("iso"), d, False)
    return projs, sec


def overall_dims(sh: Sheet, pl: dict, size3) -> None:
    L, W, H = size3
    f = pl["front"]
    x0, y0, x1, y1 = f.box
    dim_v(sh, y0, y1, x0, x0, x0 - 8, f"{fmt(H)} ±{fmt(tol(H))}")
    if "top" in pl:
        tx0, ty0, tx1, ty1 = pl["top"].box
        dim_h(sh, tx0, tx1, ty1, ty1, ty1 + 8, f"{fmt(L)} ±{fmt(tol(L))}")
    else:
        dim_h(sh, x0, x1, y1, y1, y1 + 8, f"{fmt(L)} ±{fmt(tol(L))}")
    if "left" in pl:
        lx0, ly0, lx1, ly1 = pl["left"].box
        dim_h(sh, lx0, lx1, ly1, ly1, ly1 + 8, f"{fmt(W)} ±{fmt(tol(W))}")


def hatch(sh: Sheet, polys: list[list[tuple[float, float]]], spacing: float) -> None:
    """45° hatching of the even-odd region (scanline in a rotated frame)."""
    c, s_ = math.cos(math.radians(45)), math.sin(math.radians(45))
    rot = [np.array([[x * c + y * s_, -x * s_ + y * c] for x, y in p]) for p in polys if len(p) >= 3]
    if not rot:
        return
    allp = np.vstack(rot)
    vmin, vmax = allp[:, 1].min(), allp[:, 1].max()
    v = vmin + spacing / 2
    while v < vmax:
        for a, b in G.wall_at_mid(rot, v):
            p1 = (a * c - v * s_, a * s_ + v * c)
            p2 = (b * c - v * s_, b * s_ + v * c)
            sh.line([p1, p2], "hatch")
        v += spacing


def section_marks(sh: Sheet, front: Placed, cx: float) -> None:
    """Cutting plane A-A on the front view: chain line with thick ends, arrows showing the viewing direction (+X)."""
    x0, y0, x1, y1 = front.box
    x, _ = front.p(cx, 0)
    top, bot = y0 - 6, y1 + 6
    sh.line([(x, top), (x, bot)], "center")
    for ya, yb in ((top, top + 3), (bot - 3, bot)):
        sh.line([(x, ya), (x, yb)], "cut")
    for y in (top, bot):
        sh.line([(x, y), (x + 5, y)], "thin")
        arrow(sh, (x + 6, y), (x, y))
        sh.text(x + 7.2, y + 1.0 + (0 if y == bot else 0), "A", 3.2, bold=True)


def feature_callouts(sh: Sheet, pl: dict, feats: G.Features, used_left_as_section: bool) -> None:
    """One leader per hole / boss group in the ortho view that shows it as circles; pitch dims for hole patterns."""
    slots = {"front": 0, "top": 0, "left": 0}
    for g in (feats.holes + feats.bosses)[:5]:
        ax = np.array(g.axis)
        vname = None
        for name in ("top", "front", "left"):
            if name not in pl or (name == "left" and used_left_as_section):
                continue
            if abs(float(ax @ np.abs(pl[name].view.N))) > 0.98:
                vname = name
                break
        if vname is None:
            continue
        v = pl[vname]
        r = g.diameter / 2 * v.s
        c3 = max(g.centers, key=lambda c: (v.view.p2(c)[0] + v.view.p2(c)[1]))
        cx, cy = v.p3(c3)
        for c in g.centers:  # centre marks
            px, py = v.p3(c)
            e = max(r + 1.2, 1.6)
            sh.line([(px - e, py), (px + e, py)], "center")
            sh.line([(px, py - e), (px, py + e)], "center")
        x0, y0, x1, y1 = v.box
        k = slots[vname]
        slots[vname] += 1
        if vname == "top":  # the free band right of the top view (under the left view's dimension)
            knee = (x1 + (14 if len(feats.holes) and g.kind == "hole" and g.count >= 2 else 8), y0 + 4 + 6 * k)
        else:  # above the view (the sheet keeps a 12 mm margin there)
            knee = (min(x1 + 4, cx + 10 + 6 * k), y0 - 4 - 5 * k)
        n = f"{g.count}× " if g.count > 1 else ""
        if g.kind == "hole":
            tol_txt = " +0.1/0"
            label = f"{n}Ø{fmt(g.diameter)}{tol_txt} ↧{fmt(g.depth)}" + (" (drafted)" if g.conical else "")
        else:
            label = f"{n}BOSS Ø{fmt(g.diameter)} ±{fmt(tol(g.diameter))}" + (" (drafted)" if g.conical else "")
        label = label.replace("↧", "depth ")
        ang = math.radians(-45)
        anchor = (cx + r * math.cos(ang), cy + r * math.sin(ang))
        leader(sh, anchor, knee, label)
        # pitch of a hole pattern (first group only)
        if g.kind == "hole" and g.count >= 2 and k == 0:
            pts = np.array([v.view.p2(c) for c in g.centers])
            us, vs = np.unique(np.round(pts[:, 0], 2)), np.unique(np.round(pts[:, 1], 2))
            if len(us) >= 2:
                a, b = v.p(us.min(), vs.min())[0], v.p(us.max(), vs.min())[0]
                ybase = max(v.p3(c)[1] for c in g.centers)
                dim_h(sh, a, b, ybase, ybase, y1 + (16 if vname == "top" else 4), f"{fmt(us.max() - us.min())} ±{fmt(tol(us.max() - us.min()))}")
            if len(vs) >= 2:
                a, b = v.p(us.max(), vs.max())[1], v.p(us.max(), vs.min())[1]
                dim_v(sh, a, b, v.p(us.max(), 0)[0], v.p(us.max(), 0)[0], x1 + 6, f"{fmt(vs.max() - vs.min())} ±{fmt(tol(vs.max() - vs.min()))}")


# --------------------------------------------------------------------------- sheets


def _sheet_area(fr, band_top: float, right_reserve: float = 0.0):
    x0, y0, x1, _ = fr
    return (x0 + 4, y0 + 4, x1 - x0 - 8 - right_reserve, band_top - y0 - 8)


def part_sheet(p: PartDef, meta: Meta, sheet_no: str, dwg_no: str) -> Sheet:
    solid = p.solids[0]
    bb = solid.bounding_box()
    size3 = (bb.size.X, bb.size.Y, bb.size.Z)
    mx = max(size3)
    feats = G.features(solid, mx)
    hollow = G.is_hollow(solid)
    cx = bb.center().X
    chosen = None
    for size in ("A4", "A3"):
        sh = Sheet(size)
        fr = frame(sh)
        band = fr[3] - TB_H - WARN_H - 2
        area = _sheet_area(fr, band)
        guess = min(area[2] / (size3[0] + size3[1] + 1), area[3] / (size3[2] + size3[1] + 1))
        projs, sec = views_for(solid, 0.03, guess, True, True, cx if hollow else None)
        pl, s, si = layout(sh, projs, area, 40.0, iso_pad=(0.0, 9.0))
        chosen = (sh, fr, band, projs, sec, pl, s, si)
        if size == "A4" and (s >= 1 or len(p.solids) and s >= guess * 0.66):
            break
    sh, fr, band, projs, sec, pl, s, si = chosen
    sh.meta = {"title": f"{p.name} — {dwg_no}"}
    draw_proj(sh, pl["front"])
    draw_proj(sh, pl["top"])
    if sec:
        lp = pl["left"]
        draw_proj(sh, lp, hidden=False)
        polys = [[lp.p3(pt) for pt in poly] for poly in sec]
        hatch(sh, polys, 1.6 if s * mx < 120 else 2.4)
        section_marks(sh, pl["front"], cx)
    else:
        draw_proj(sh, pl["left"])
    draw_proj(sh, pl["iso"], hidden=False)
    view_label(sh, pl["front"], "FRONT", 10 if "top" not in pl else 0)
    view_label(sh, pl["top"], "TOP", 10)
    view_label(sh, pl["left"], "SECTION A-A" if sec else "LEFT", 10)
    view_label(sh, pl["iso"], f"ISOMETRIC · reference, ≈{scale_label(si)} (not for measurement)", centre=True)
    overall_dims(sh, pl, size3)
    extra = []
    wall = None
    if sec:
        lp = pl["left"]
        polys2 = [np.array([lp.view.p2(pt) for pt in poly]) for poly in sec]
        vmin = min(p_[:, 1].min() for p_ in polys2)
        vmax = max(p_[:, 1].max() for p_ in polys2)
        best = None
        for frac in (0.5, 0.4, 0.6, 0.3, 0.7):
            spans = G.wall_at_mid(polys2, vmin + (vmax - vmin) * frac)
            if len(spans) >= 2:
                best = (spans, vmin + (vmax - vmin) * frac)
                break
        if best is not None:
            (a, b), vv = best[0][0], best[1]
            wall = b - a
            pa, pb = lp.p(a, vv), lp.p(b, vv)
            dim_h(sh, pa[0], pb[0], pa[1], pb[1], lp.box[1] - 5, f"WALL {fmt(wall)} ±0.1")
            spec_txt = f" (spec {fmt(p.wall_spec)} mm)" if p.wall_spec else ""
            extra.append(f"Nominal wall {fmt(wall)} mm measured in section A-A{spec_txt}; keep uniform ±0.1.")
    feature_callouts(sh, pl, feats, bool(sec))
    if p.kind == "moulded":
        extra.append("Moulded part (DFM model): 1.5° draft on vertical walls as modelled; parting line at the shell split.")
    if feats.holes:
        extra.append("Hole tolerances +0.1/0 proposed for M2.5 self-tapping pilot holes — confirm with the fastener supplier.")
    if p.qty > 1:
        extra.append(f"Quantity per product: {p.qty}.")
    tb_x, tb_top = title_block(sh, fr, {
        "title": p.name, "product": meta.product, "material": p.material or "—", "finish": p.finish or "—",
        "scale": scale_label(s), "rev": f"v{meta.version}", "size": sh.size, "sheet_no": sheet_no,
        "dwg_no": dwg_no, "date": meta.date})
    notes_block(sh, fr[0] + 4, fr[3] - 2, tb_x - fr[0] - 10, base_notes(p, feats, meta, extra))
    sh.meta.update({"scale": scale_label(s), "size": sh.size, "bbox_mm": [round(x, 2) for x in size3],
                    "wall_mm": round(wall, 2) if wall else None,
                    "holes": [{"d": g.diameter, "n": g.count} for g in feats.holes],
                    "bosses": [{"d": g.diameter, "n": g.count} for g in feats.bosses], "fillets": feats.fillets})
    return sh


def assembly_sheet(parts: list[PartDef], scene, meta: Meta, sheet_no: str, dwg_no: str, title: str) -> Sheet:
    sh = Sheet("A3")
    fr = frame(sh)
    band = fr[3] - TB_H - WARN_H - 2
    rows = len(parts)
    row_h = 5.0 if rows <= 30 else max(3.6, 150 / rows)
    table_h = row_h * (rows + 1)
    beside = _sheet_area(fr, band, TB_W + 6)  # views left of the parts list column
    above = _sheet_area(fr, band - table_h - 8)  # or full width above the parts list
    bb = scene.bounding_box()
    size3 = (bb.size.X, bb.size.Y, bb.size.Z)
    guess = min(beside[2] / (size3[0] + size3[1] + 1), beside[3] / (size3[2] + 1))
    d = 0.04 / max(guess, 1e-3)
    shape = scene.wrapped
    projs = {"front": G.project(shape, G.View.of("front"), d, False),
             "left": G.project(shape, G.View.of("left"), d, False),
             "iso": G.project(shape, G.View.of("iso"), d, False)}
    cands = [layout(sh, projs, a, 110.0, iso_pad=(44.0, 10.0)) for a in (beside, above) if a[3] > 60]
    pl, s, si = max(cands, key=lambda c: (c[1], c[2]))
    sh.meta = {"title": f"{title} — {dwg_no}"}
    for k in ("front", "left", "iso"):
        draw_proj(sh, pl[k], hidden=False)
    view_label(sh, pl["front"], "FRONT", 10)
    view_label(sh, pl["left"], "LEFT", 10)
    view_label(sh, pl["iso"], f"ISOMETRIC · reference, ≈{scale_label(si)}", centre=True)
    overall_dims(sh, pl, size3)
    # balloons: two columns either side of the iso view, sorted by anchor height
    iso = pl["iso"]
    x0, y0, x1, y1 = iso.box
    mid = (x0 + x1) / 2
    anchors = []
    for p in parts:
        try:
            pt, seen = G.visible_point(p.solids[0], shape, iso.view)
        except Exception:  # noqa: BLE001
            c = p.solids[0].bounding_box().center()
            pt, seen = np.array([c.X, c.Y, c.Z]), False
        anchors.append((p, iso.p3(pt), seen))
    R = 3.3
    for side in ("L", "R"):
        col = sorted([a for a in anchors if (a[1][0] < mid) == (side == "L")], key=lambda a: a[1][1])
        if not col:
            continue
        span_top, span_bot = max(fr[1] + 6, y0 - 4), min(band - 4, y1 + 4)
        step = max(2 * R + 1.2, min(11.0, (span_bot - span_top) / max(len(col), 1)))
        total = step * (len(col) - 1)
        ys = [min(max(a[1][1], span_top), span_bot) for a in col]
        start = max(span_top, min(np.mean(ys) - total / 2, span_bot - total))
        bx = (x0 - 16) if side == "L" else (x1 + 16)
        for i, (p, (ax, ay), seen) in enumerate(col):
            by = start + i * step
            ang = math.atan2(ay - by, ax - bx)
            ex, ey = bx + R * math.cos(ang), by + R * math.sin(ang)
            sh.line([(ex, ey), (ax, ay)], "leader" if seen else "hidden")  # dashed: the part is hidden in this view
            sh.circle(ax, ay, 0.55, None, INK)
            sh.circle(bx, by, R, "thin", "#FFFFFF")
            sh.text(bx, by + 1.2, str(p.item), 3.2, "middle", bold=True)
    # parts list above the title block: header at the bottom, items upwards (ISO 7573)
    tx = fr[2] - TB_W
    ty = band - 2
    cols = [("ITEM", 11), ("PART", 55), ("QTY", 10), ("MATERIAL", 46), ("FINISH", 38), ("BOM", 20)]
    hy = ty - row_h
    sh.rect(tx, hy, TB_W, row_h, "thin", "#EFEDE8")
    sh.rect(tx, ty - table_h, TB_W, table_h, "frame")
    cx_ = tx
    for name, w in cols:
        sh.text(cx_ + 1.2, hy + row_h - 1.5, name, 2.0, bold=True)
        cx_ += w
    for i, p in enumerate(parts):
        ry = hy - (i + 1) * row_h
        sh.line([(tx, ry + row_h), (tx + TB_W, ry + row_h)], "rule")
        vals = [str(p.item), p.name, str(p.qty), p.material or "—", p.finish or "—", p.bom_id or "—"]
        cx_ = tx
        for (name, w), v in zip(cols, vals):
            sz = min(2.2, row_h * 0.5)
            while text_width(v, sz) > w - 2.2 and len(v) > 3:
                v = v[:-2].rstrip() + "…" if not v.endswith("…") else v[:-3].rstrip() + "…"
            sh.text(cx_ + 1.2, ry + row_h - (row_h - sz * 0.72) / 2, v, sz, bold=(name == "ITEM"))
            cx_ += w
    cx_ = tx
    for _, w in cols[:-1]:
        cx_ += w
        sh.line([(cx_, ty - table_h), (cx_, ty)], "rule")
    sh.text(tx, ty - table_h - 1.6, "PARTS LIST · BOM = stage-3 BOM line", 2.0, color=INK2)
    tb_x, _ = title_block(sh, fr, {
        "title": title, "product": meta.product, "material": "See parts list", "finish": "See parts list",
        "scale": scale_label(s), "rev": f"v{meta.version}", "size": "A3", "sheet_no": sheet_no, "dwg_no": dwg_no,
        "date": meta.date})
    notes_block(sh, fr[0] + 4, fr[3] - 2, tb_x - fr[0] - 10, base_notes(None, None, meta, [
        "Assembly for reference: hidden lines omitted; balloon numbers = ITEM of the parts list, tied to the BOM line.",
        "Part geometry and internal layout are concept level; fasteners and electronics are not modelled."]))
    sh.meta.update({"scale": scale_label(s), "size": "A3", "bbox_mm": [round(x, 2) for x in size3],
                    "balloons": [{"item": p.item, "part_id": p.key, "bom_id": p.bom_id} for p in parts]})
    return sh
