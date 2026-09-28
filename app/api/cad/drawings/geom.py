"""Geometry for the drawings: exact hidden-line projection (OCCT HLRBRep), measured features, section cuts.

All values are measured on the STEP solids (mm). Views are orthographic; 2D coordinates of a view are
(p·X, p·Y) with Y = N × X, N pointing from the model towards the viewer (the HLR projector frame).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepLib import BRepLib
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Line, GeomAbs_Torus
from OCP.gp import gp_Ax2, gp_Dir, gp_Lin, gp_Pnt
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.TopAbs import TopAbs_EDGE, TopAbs_REVERSED
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

# name → (N towards the viewer, X to the right). First-angle (ISO E): left view drawn right of the front,
# top view drawn below it.
VIEW_DIRS = {
    "front": ((0, -1, 0), (1, 0, 0)),
    "top": ((0, 0, 1), (1, 0, 0)),
    "left": ((-1, 0, 0), (0, -1, 0)),
    "iso": ((1, -1, 1), (1, 1, 0)),
}


@dataclass
class View:
    name: str
    N: np.ndarray
    X: np.ndarray
    Y: np.ndarray

    @classmethod
    def of(cls, name: str) -> "View":
        n, x = (np.array(v, float) for v in VIEW_DIRS[name])
        n, x = n / np.linalg.norm(n), x / np.linalg.norm(x)
        return cls(name, n, x, np.cross(n, x))

    def p2(self, p) -> tuple[float, float]:
        p = np.asarray(p, float)
        return float(p @ self.X), float(p @ self.Y)


@dataclass
class Proj:
    visible: list[np.ndarray] = field(default_factory=list)  # sharp edges + silhouettes (thick)
    smooth: list[np.ndarray] = field(default_factory=list)  # tangent edges (thin)
    hidden: list[np.ndarray] = field(default_factory=list)  # hidden edges (dashed)

    def bbox(self) -> tuple[float, float, float, float]:
        pts = [p for p in self.visible + self.smooth] or [np.zeros((1, 2))]
        a = np.vstack(pts)
        return float(a[:, 0].min()), float(a[:, 1].min()), float(a[:, 0].max()), float(a[:, 1].max())


def _edges(comp) -> list:
    out = []
    if comp is None or comp.IsNull():
        return out
    ex = TopExp_Explorer(comp, TopAbs_EDGE)
    while ex.More():
        out.append(TopoDS.Edge(ex.Current()))
        ex.Next()
    return out


def edge_points(edge, defl: float, three_d: bool = False) -> np.ndarray | None:
    try:
        c = BRepAdaptor_Curve(edge)
    except Exception:  # noqa: BLE001
        return None
    u0, u1 = c.FirstParameter(), c.LastParameter()
    if c.GetType() == GeomAbs_Line:
        pts = [c.Value(u0), c.Value(u1)]
    else:
        d = GCPnts_QuasiUniformDeflection(c, max(defl, 1e-4), u0, u1)
        if not d.IsDone() or d.NbPoints() < 2:
            pts = [c.Value(u0 + (u1 - u0) * t) for t in np.linspace(0, 1, 16)]
        else:
            pts = [d.Value(i) for i in range(1, d.NbPoints() + 1)]
    a = np.array([[p.X(), p.Y(), p.Z()] for p in pts])
    return a if three_d else a[:, :2]


def project(shape, view: View, defl: float, hidden: bool = True) -> Proj:
    """Exact HLR of a TopoDS shape in `view`; polylines in view coordinates (mm)."""
    algo = HLRBRep_Algo()
    algo.Add(shape)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*view.N), gp_Dir(*view.X))))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    out = Proj()
    groups = [(out.visible, [h.VCompound(), h.OutLineVCompound()]), (out.smooth, [h.Rg1LineVCompound()])]
    if hidden:
        groups.append((out.hidden, [h.HCompound(), h.OutLineHCompound()]))
    for dst, comps in groups:
        for comp in comps:
            for e in _edges(comp):
                BRepLib.BuildCurves3d_s(e, 1e-5)
                pts = edge_points(e, defl)
                if pts is not None and len(pts) >= 2 and np.ptp(pts, axis=0).max() > 1e-6:
                    dst.append(pts)
    return out


# --------------------------------------------------------------------------- measured features


@dataclass
class HoleGroup:
    kind: str  # "hole" | "boss"
    diameter: float
    depth: float
    axis: tuple[float, float, float]
    centers: list[tuple[float, float, float]]
    conical: bool = False

    @property
    def count(self) -> int:
        return len(self.centers)


@dataclass
class Features:
    holes: list[HoleGroup] = field(default_factory=list)
    bosses: list[HoleGroup] = field(default_factory=list)
    fillets: list[float] = field(default_factory=list)


def _face_normal(face, u: float, v: float) -> np.ndarray:
    s = BRepAdaptor_Surface(face)
    from OCP.BRepLProp import BRepLProp_SLProps

    props = BRepLProp_SLProps(s, u, v, 1, 1e-6)
    if not props.IsNormalDefined():
        return np.zeros(3)
    n = props.Normal()
    vec = np.array([n.X(), n.Y(), n.Z()])
    return -vec if face.Orientation() == TopAbs_REVERSED else vec


def features(solid, size: float) -> Features:
    """Holes and bosses (full cylindrical / conical faces, concave = hole, convex = boss) and fillet radii (partial
    cylinders and tori). Measured on the B-rep; grouped by diameter and axis."""
    raw: dict[tuple, HoleGroup] = {}
    fillets: set[float] = set()
    for f in solid.faces():
        face = f.wrapped
        s = BRepAdaptor_Surface(face)
        t = s.GetType()
        u0, u1, v0, v1 = s.FirstUParameter(), s.LastUParameter(), s.FirstVParameter(), s.LastVParameter()
        if t == GeomAbs_Torus:
            fillets.add(round(s.Torus().MinorRadius(), 1))
            continue
        if t not in (GeomAbs_Cylinder, GeomAbs_Cone):
            continue
        span = u1 - u0
        um, vm = (u0 + u1) / 2, (v0 + v1) / 2
        p = s.Value(um, vm)
        pt = np.array([p.X(), p.Y(), p.Z()])
        if t == GeomAbs_Cylinder:
            ax = s.Cylinder().Axis()
        else:
            ax = s.Cone().Axis()
        o = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()])
        d = np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
        rel = pt - o
        radial = rel - (rel @ d) * d
        r = float(np.linalg.norm(radial))
        if r < 1e-6:
            continue
        if span < 2 * math.pi * 0.98:
            if span <= math.pi * 0.55 and r < size * 0.25:
                fillets.add(round(r, 1))
            continue
        n = _face_normal(face, um, vm)
        concave = float(n @ radial) < 0
        if r * 2 > size * 0.35:  # the part's own round body, not a feature
            continue
        pa, pb = s.Value(um, v0), s.Value(um, v1)
        a3, b3 = np.array([pa.X(), pa.Y(), pa.Z()]), np.array([pb.X(), pb.Y(), pb.Z()])
        depth = abs(float((b3 - a3) @ d))
        if depth < 0.3:
            continue
        # Ø at the base of a drafted (conical) feature: the larger end for a hole opening, measured radius otherwise
        if t == GeomAbs_Cone:
            ra = float(np.linalg.norm((a3 - o) - ((a3 - o) @ d) * d))
            rb = float(np.linalg.norm((b3 - o) - ((b3 - o) @ d) * d))
            r = min(ra, rb) if concave else max(ra, rb)
        ctr = o + (((a3 + b3) / 2 - o) @ d) * d
        axis = tuple(round(abs(x), 2) for x in d)
        key = ("hole" if concave else "boss", round(2 * r, 1), axis, t == GeomAbs_Cone)
        g = raw.setdefault(key, HoleGroup(key[0], round(2 * r, 2), round(depth, 2), axis, [], t == GeomAbs_Cone))
        if not any(np.linalg.norm(np.array(c) - ctr) < 0.05 for c in g.centers):
            g.centers.append(tuple(float(x) for x in ctr))
        g.depth = max(g.depth, round(depth, 2))
    out = Features(fillets=sorted(x for x in fillets if x > 0.05))
    for g in raw.values():
        (out.holes if g.kind == "hole" else out.bosses).append(g)
    out.holes.sort(key=lambda g: (-g.count, g.diameter))
    out.bosses.sort(key=lambda g: (-g.count, g.diameter))
    return out


def is_hollow(solid) -> bool:
    bb = solid.bounding_box()
    box = max(bb.size.X * bb.size.Y * bb.size.Z, 1e-9)
    return solid.volume / box < 0.45 and min(bb.size.X, bb.size.Y, bb.size.Z) > 1.0


# --------------------------------------------------------------------------- section A-A (plane x = cx, looking +X)


def section(solid, cx: float):
    """Keep x ≥ cx (the material behind the cutting plane seen from the left view); returns (half, cut polygons 3D)."""
    from build123d import Keep, Plane

    half = solid.split(Plane.YZ.offset(cx), keep=Keep.TOP)
    polys: list[np.ndarray] = []
    for f in half.faces():
        if f.geom_type.name != "PLANE":
            continue
        c = f.center()
        n = f.normal_at(c)
        if abs(c.X - cx) > 1e-3 or abs(abs(n.X) - 1) > 1e-6:
            continue
        for w in [f.outer_wire(), *f.inner_wires()]:
            pts = []
            for e in w.order_edges():
                a = edge_points(e.wrapped, 0.02, three_d=True)
                if a is None:
                    continue
                if e.wrapped.Orientation() == TopAbs_REVERSED:
                    a = a[::-1]
                pts.append(a)
            if pts:
                polys.append(np.vstack(pts))
    return half, polys


def wall_at_mid(polys2d: list[np.ndarray], y: float) -> list[tuple[float, float]]:
    """Material spans of the section (even-odd) along the horizontal line at height y."""
    xs = []
    for poly in polys2d:
        a = np.vstack([poly, poly[:1]])
        for (x1, y1), (x2, y2) in zip(a[:-1], a[1:]):
            if (y1 <= y < y2) or (y2 <= y < y1):
                xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    xs.sort()
    return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]


# --------------------------------------------------------------------------- visibility (balloon anchors)


def visible_point(target, scene, view: View) -> tuple[np.ndarray, bool]:
    """A point on `target` that the viewer of `view` sees (ray towards the viewer hits nothing), else the nearest."""
    cands = []
    for f in target.faces():
        try:
            c = f.center()
            cands.append(np.array([c.X, c.Y, c.Z]))
        except Exception:  # noqa: BLE001
            continue
    bb = target.bounding_box()
    cands.append(np.array([bb.center().X, bb.center().Y, bb.center().Z]))
    cands.sort(key=lambda p: -(p @ view.N))
    inter = IntCurvesFace_ShapeIntersector()
    inter.Load(scene, 1e-4)
    for p in cands[:24]:
        start = p + view.N * 0.05
        inter.Perform(gp_Lin(gp_Pnt(*start), gp_Dir(*view.N)), 0.0, 1e7)
        if inter.NbPnt() == 0:
            return p, True
    return cands[0], False


__all__ = ["View", "Proj", "project", "features", "Features", "HoleGroup", "is_hollow", "section", "wall_at_mid",
           "visible_point", "edge_points", "BRep_Tool"]
