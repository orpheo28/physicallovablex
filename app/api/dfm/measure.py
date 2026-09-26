"""Measured DFM checks on a STEP file (injection moulding, straight two-half pull). Owner: W2.

    measure(step_path, pull_dir=(0, 0, 1), finish=None, material=None, part_id=None) -> list[DFMIssue]
    facts(shape, pull_dir) -> dict            # raw measurements, no verdicts

Port of the measurement logic of earthtojake/text-to-cad `skills/dfm/scripts/mold_tool.py` (MIT, © 2026
Thompson Labs LLC — see api/dfm/README.md) from trimesh meshes to OCCT B-rep faces:
- draft: per face, the angle between the face and the pull axis (0° = parallel to the pull). A planar B-rep
  face is read exactly; a curved face is sampled on its tessellation and read at the 5th percentile of its
  area (a chord tilts less than the surface it cuts). Faces ≥ 45° from the pull are not walls. Curved faces
  sweeping through the pull (fillets, spread > 30°) are tangent bands, reported apart, never as walls.
  `min_wall_draft` ignores faces below an absolute area floor (0.1% of the surface, ≥ 1 mm²).
- undercut: straight-pull occlusion test per body. A sample leaning toward ±pull is withdrawn along that sign;
  a ray from it must leave the body. A zero-draft sample is a candidate only if blocked both ways.
- projection: silhouette area along the pull, rasterised → clamp-tonnage estimate (formula in the issue).
- wall thickness: sampled — a ray from each surface sample into the material; 5th percentile reported.
Every figure is `measured` except the tonnage, which is an estimate from a measured area.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from contracts.artifacts import DFMIssue, DFMMethod, LabeledValue, Severity

WALL_LIMIT_DEG = 45.0
ZERO_TOL_DEG = 0.05
MIN_DRAFT_DEG = 1.0  # polished / light finish
TEXTURE_DRAFT_DEG = 3.0  # 1° + 1° per 0.025 mm texture depth, MT-11010-class light texture ≈ 0.05 mm
TANGENT_SPREAD_DEG = 30.0
RASTER_CELLS = 400
PCABS_TONS_PER_IN2 = 3.0  # clamp pressure rule of thumb for PC/ABS (2-5 t/in² range for engineering resins)
SAFETY = 1.1

SOURCE = "text-to-cad DFM skill (mold_tool.py, MIT) ported to OCCT"
PROTOLABS = "Protolabs injection molding design guidelines"


# --------------------------------------------------------------------------- sampling


def _face_samples(face, tol: float) -> dict[str, Any] | None:
    """Triangle centres, areas and outward normals of one B-rep face."""
    verts, tris = face.tessellate(tol, 0.3)
    if not tris:
        return None
    v = np.array([[p.X, p.Y, p.Z] for p in verts])
    t = np.array(tris)
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    cross = np.cross(b - a, c - a)
    areas = 0.5 * np.linalg.norm(cross, axis=1)
    keep = areas > 1e-9
    if not keep.any():
        return None
    centers = ((a + b + c) / 3)[keep]
    areas = areas[keep]
    planar = face.geom_type.name == "PLANE" if hasattr(face.geom_type, "name") else str(face.geom_type) == "PLANE"
    if planar:
        n = face.normal_at()
        normals = np.tile([n.X, n.Y, n.Z], (len(centers), 1))
    else:
        # a chord centre lies off a curved surface: project it back so rays start on the real face
        from OCP.BRep import BRep_Tool
        from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
        from OCP.gp import gp_Pnt

        surf = BRep_Tool.Surface_s(face.wrapped)
        normals, projected = [], []
        for ctr in centers:
            proj = GeomAPI_ProjectPointOnSurf(gp_Pnt(*map(float, ctr)), surf)
            if proj.NbPoints() > 0:
                q = proj.NearestPoint()
                ctr = np.array([q.X(), q.Y(), q.Z()])
            projected.append(ctr)
            n = face.normal_at(tuple(ctr))
            normals.append([n.X, n.Y, n.Z])
        centers = np.array(projected)
        normals = np.array(normals)
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    return {"centers": centers, "areas": areas, "normals": normals, "planar": planar, "tris": (a[keep], b[keep], c[keep])}


def _weighted_percentile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cum = np.cumsum(w)
    return float(v[np.searchsorted(cum, q * cum[-1])]) if cum[-1] > 0 else float(v[0])


class _Rays:
    def __init__(self, solid, tol: float):
        from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector

        self.ix = IntCurvesFace_ShapeIntersector()
        self.ix.Load(solid.wrapped, tol)

    def hits(self, origin: np.ndarray, direction: np.ndarray, pmin: float = 0.0) -> list[float]:
        from OCP.gp import gp_Dir, gp_Lin, gp_Pnt

        line = gp_Lin(gp_Pnt(*map(float, origin)), gp_Dir(*map(float, direction)))
        self.ix.Perform(line, pmin, 1e9)
        if not self.ix.IsDone():
            return []
        return [self.ix.WParameter(i) for i in range(1, self.ix.NbPnt() + 1)]


# --------------------------------------------------------------------------- fact families


def facts(shape, pull_dir: Iterable[float] = (0, 0, 1)) -> dict[str, Any]:
    pull = np.array(list(pull_dir), dtype=float)
    pull /= np.linalg.norm(pull)
    bb = shape.bounding_box()
    diag = float(bb.diagonal)
    tol = max(diag / 250.0, 0.05)
    eps = 1e-3 * max(diag, 1.0)
    solids = shape.solids() or [shape]

    total_area = 0.0
    faces_out: list[dict] = []
    tangent_area = 0.0
    undercut = {"candidate_area_mm2": 0.0, "leaning_blocked_area_mm2": 0.0, "trapped_zero_draft_area_mm2": 0.0,
                "candidate_samples": 0, "largest": []}
    thickness_vals, thickness_w = [], []
    all_tris = []
    volume = 0.0

    for body_i, solid in enumerate(solids):
        volume += abs(solid.volume)
        rays = _Rays(solid, 1e-4)
        for face in solid.faces():
            s = _face_samples(face, tol)
            if s is None:
                continue
            all_tris.append(s["tris"])
            areas, normals, centers = s["areas"], s["normals"], s["centers"]
            face_area = float(areas.sum())
            total_area += face_area
            along = normals @ pull
            draft = np.degrees(np.arcsin(np.clip(np.abs(along), 0, 1)))
            # --- draft (pooled per B-rep face)
            spread = float(draft.max() - draft.min())
            reading = float(draft[0]) if s["planar"] else _weighted_percentile(draft, areas, 0.05)
            wall_sel = draft < WALL_LIMIT_DEG
            is_tangent = (not s["planar"]) and spread > TANGENT_SPREAD_DEG
            if is_tangent:
                tangent_area += float(areas[draft < ZERO_TOL_DEG * 20].sum())
            elif wall_sel.any():
                ctr = (centers * areas[:, None]).sum(0) / face_area
                faces_out.append({
                    "body": body_i, "draft_deg": round(reading, 3), "area_mm2": round(float(areas[wall_sel].sum()), 2),
                    "surface": "flat" if s["planar"] else "curved", "spread_deg": round(spread, 3),
                    "centroid_xyz": [round(float(x), 2) for x in ctr],
                    "opens_toward": "+pull" if float((along * areas).sum()) > 0 else ("-pull" if reading > ZERO_TOL_DEG else "none"),
                })
            # --- undercut (straight-pull occlusion, per body)
            zero = draft < ZERO_TOL_DEG
            for i in range(len(centers)):
                o = centers[i] + normals[i] * eps
                if zero[i]:
                    blocked = bool(rays.hits(o, pull, eps)) and bool(rays.hits(o, -pull, eps))
                    kind = "trapped_zero_draft_area_mm2"
                else:
                    sign = 1.0 if along[i] > 0 else -1.0
                    blocked = bool(rays.hits(o, sign * pull, eps))
                    kind = "leaning_blocked_area_mm2"
                if blocked:
                    undercut[kind] += float(areas[i])
                    undercut["candidate_area_mm2"] += float(areas[i])
                    undercut["candidate_samples"] += 1
                    undercut["largest"].append({"area_mm2": round(float(areas[i]), 2), "location_xyz": [round(float(x), 2) for x in centers[i]]})
                # --- wall thickness: ray into the material
                inside = rays.hits(centers[i] - normals[i] * eps, -normals[i], 0.0)
                if inside:
                    thickness_vals.append(min(inside) + eps)
                    thickness_w.append(float(areas[i]))

    # min wall draft over significant faces
    floor = max(1.0, 0.001 * total_area)
    significant = [f for f in faces_out if f["area_mm2"] >= floor] or faces_out
    min_draft = min(significant, key=lambda f: f["draft_deg"]) if significant else None
    zero_faces = [f for f in faces_out if f["draft_deg"] < ZERO_TOL_DEG]

    undercut["largest"] = sorted(undercut["largest"], key=lambda g: -g["area_mm2"])[:8]
    for k in ("candidate_area_mm2", "leaning_blocked_area_mm2", "trapped_zero_draft_area_mm2"):
        undercut[k] = round(undercut[k], 2)
    undercut["candidate_area_pct_of_surface"] = round(100 * undercut["candidate_area_mm2"] / total_area, 2) if total_area else 0.0

    thickness = None
    if thickness_vals:
        tv, tw = np.array(thickness_vals), np.array(thickness_w)
        thickness = {"p05_mm": round(_weighted_percentile(tv, tw, 0.05), 3),
                     "median_mm": round(_weighted_percentile(tv, tw, 0.5), 3), "samples": len(tv)}

    return {
        "pull_axis": [round(float(x), 4) for x in pull],
        "surface_area_mm2": round(total_area, 2),
        "volume_mm3": round(volume, 1),
        "body_count": len(solids),
        "draft": {
            "wall_faces": len(faces_out),
            "area_floor_mm2": round(floor, 2),
            "min_wall_draft": min_draft,
            "zero_draft_wall_area_mm2": round(sum(f["area_mm2"] for f in zero_faces), 2),
            "zero_draft_face_count": len(zero_faces),
            "zero_draft_tangent_area_mm2": round(tangent_area, 2),
            "lowest_draft_wall_faces": sorted(faces_out, key=lambda f: f["draft_deg"])[:8],
        },
        "undercut": undercut,
        "projection": _projection(all_tris, pull),
        "wall_thickness": thickness,
    }


def _projection(tri_sets: list, pull: np.ndarray) -> dict[str, Any]:
    """Silhouette area along the pull, rasterised on a grid sized to the part (mold_tool._projection_facts)."""
    if not tri_sets:
        return {"projected_area_mm2": 0.0}
    a = np.concatenate([t[0] for t in tri_sets])
    b = np.concatenate([t[1] for t in tri_sets])
    c = np.concatenate([t[2] for t in tri_sets])
    helper = np.array([1.0, 0, 0]) if abs(pull[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(pull, helper)
    u /= np.linalg.norm(u)
    v = np.cross(pull, u)
    P = np.stack([u, v], axis=1)
    pa, pb, pc = a @ P, b @ P, c @ P
    pts = np.concatenate([pa, pb, pc])
    span = pts.max(0) - pts.min(0)
    res = float(max(span.max(), 1e-9)) / RASTER_CELLS
    lo = pts.min(0) - res
    size = np.maximum(np.ceil((pts.max(0) + res - lo) / res).astype(int), 1)
    grid = np.zeros((size[1], size[0]), dtype=bool)
    for A, B, C in zip((pa - lo) / res, (pb - lo) / res, (pc - lo) / res):
        den = (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1])
        if abs(den) < 1e-12:
            continue
        x0, x1 = max(0, int(min(A[0], B[0], C[0]))), min(size[0] - 1, int(math.ceil(max(A[0], B[0], C[0]))))
        y0, y1 = max(0, int(min(A[1], B[1], C[1]))), min(size[1] - 1, int(math.ceil(max(A[1], B[1], C[1]))))
        if x1 < x0 or y1 < y0:
            continue
        xx = (np.arange(x0, x1 + 1) + 0.5)[None, :]
        yy = (np.arange(y0, y1 + 1) + 0.5)[:, None]
        w0 = ((B[1] - C[1]) * (xx - C[0]) + (C[0] - B[0]) * (yy - C[1])) / den
        w1 = ((C[1] - A[1]) * (xx - C[0]) + (A[0] - C[0]) * (yy - C[1])) / den
        grid[y0:y1 + 1, x0:x1 + 1] |= (w0 >= -1e-6) & (w1 >= -1e-6) & (w0 + w1 <= 1 + 1e-6)
    heights = np.concatenate([a, b, c]) @ pull
    return {"projected_area_mm2": round(float(grid.sum()) * res**2, 1), "raster_resolution_mm": round(res, 4),
            "depth_along_pull_mm": round(float(heights.max() - heights.min()), 3)}


# --------------------------------------------------------------------------- issues


def _m(value: float, unit: str, check: str) -> LabeledValue:
    return LabeledValue(value=round(float(value), 3), unit=unit, label="measured", source_or_assumption=check)


def _textured(finish: str | None) -> bool:
    f = (finish or "").lower()
    return any(k in f for k in ("texture", "mt-", "vdi", "bead", "matte", "grain"))


def issues_from_facts(f: dict[str, Any], finish: str | None = None, material: str | None = None,
                      part_id: str | None = None) -> list[DFMIssue]:
    metal = any(k in (material or "").lower() for k in ("alumin", "steel", "zinc"))
    out: list[DFMIssue] = []
    axis = "".join(f"{'+' if x > 0 else '-'}{'XYZ'[i]}" for i, x in enumerate(f["pull_axis"]) if abs(x) > 0.5) or str(f["pull_axis"])

    # draft
    md = f["draft"]["min_wall_draft"]
    if md is not None:
        d = md["draft_deg"]
        need = TEXTURE_DRAFT_DEG if _textured(finish) else MIN_DRAFT_DEG
        check = (f"Min wall draft vs pull {axis}: lowest-draft B-rep wall face ≥ {f['draft']['area_floor_mm2']} mm² "
                 f"({md['surface']}, {md['area_mm2']} mm² at {md['centroid_xyz']}) — {SOURCE}")
        if d < MIN_DRAFT_DEG:
            out.append(DFMIssue(
                id="m_draft", severity=Severity.minor if metal else Severity.major, category="draft",
                method=DFMMethod.measured, part_id=part_id,
                description=(f"Wall faces have {d:.2f}° draft along the pull direction ({axis}); "
                             f"{f['draft']['zero_draft_face_count']} face(s) are zero-draft "
                             f"({f['draft']['zero_draft_wall_area_mm2']} mm²)."),
                fix=f"Add ≥{need:.0f}° draft on all walls parallel to {axis} (more on textured faces), or move the parting line.",
                rule_citation=f"Draft ≥1° on walls, +1° per 0.025 mm texture depth — {PROTOLABS}; measured with {SOURCE}",
                measurement=_m(d, "deg", check)))
        elif d < need:
            out.append(DFMIssue(
                id="m_draft", severity=Severity.minor, category="draft", method=DFMMethod.measured, part_id=part_id,
                description=f"Minimum wall draft is {d:.2f}°: enough for a polished finish, short of the ~{need:.0f}° a textured finish ('{finish}') needs.",
                fix=f"Increase draft to {need:.0f}° on textured faces, or specify a lighter texture / polished finish.",
                rule_citation=f"Draft ≥1° plus 1° per 0.025 mm texture depth — {PROTOLABS}; measured with {SOURCE}",
                measurement=_m(d, "deg", check)))

    # undercuts
    uc = f["undercut"]
    if uc["candidate_area_mm2"] > max(1.0, 0.0005 * f["surface_area_mm2"]):
        loc = uc["largest"][0]["location_xyz"] if uc["largest"] else None
        out.append(DFMIssue(
            id="m_undercut", severity=Severity.major, category="undercut", method=DFMMethod.measured, part_id=part_id,
            description=(f"{uc['candidate_area_mm2']} mm² ({uc['candidate_area_pct_of_surface']}% of the surface) cannot be "
                         f"withdrawn along {axis} in a straight two-half tool (largest near {loc})."),
            fix="Redesign as pass-through core / bump-off, change the parting line, or budget a side action (slide/lifter).",
            rule_citation=f"Undercuts need side actions or a different pull — {PROTOLABS}; straight-pull occlusion test from {SOURCE}",
            measurement=_m(uc["candidate_area_mm2"], "mm2",
                           f"Ray from each surface sample along its withdrawal direction ({axis}) hits the same body — {SOURCE}")))

    # projection → clamp tonnage (estimate)
    pr = f["projection"]
    area = pr.get("projected_area_mm2", 0.0)
    if area > 0:
        tons = area / 645.16 * PCABS_TONS_PER_IN2 * SAFETY
        out.append(DFMIssue(
            id="m_projection", severity=Severity.minor, category="projection", method=DFMMethod.measured, part_id=part_id,
            description=(f"Projected area along {axis}: {area:.0f} mm² (part silhouette, per cavity). Estimated clamp force ≈ {tons:.1f} t "
                         f"(Estimate: area in² × {PCABS_TONS_PER_IN2} t/in² for PC/ABS × {SAFETY} safety) — "
                         f"per cavity; a family tool moulding both shells in one shot roughly doubles it."),
            fix=f"Quote on a press ≥ {math.ceil(tons * 1.2 / 10) * 10:.0f} t; keep both shells in one family mould only if tonnage allows.",
            rule_citation=f"Clamp force ≈ projected area × cavity-pressure factor (2-5 t/in²) — {PROTOLABS}; silhouette raster from {SOURCE}",
            measurement=_m(area, "mm2", f"Silhouette along {axis}, raster {pr.get('raster_resolution_mm')} mm — {SOURCE}")))

    # wall thickness (sampled)
    wt = f.get("wall_thickness")
    if wt:
        t = wt["p05_mm"]
        check = f"5th percentile of {wt['samples']} ray samples into the material (median {wt['median_mm']} mm)"
        if t < 1.0:
            sev, desc, fix = Severity.major, f"Thin walls: 5% of the surface sits on walls ≤ {t:.2f} mm.", "Keep PC/ABS walls ≥ 1.2 mm; thicken local thin sections."
        elif wt["median_mm"] > 4.0:
            sev, desc, fix = Severity.minor, f"Thick sections: median wall {wt['median_mm']:.2f} mm risks sink and long cycle time.", "Core out thick sections to 2-3 mm nominal."
        else:
            sev, desc, fix = Severity.minor, (f"Measured wall {t:.2f}-{wt['median_mm']:.2f} mm is within the PC/ABS 1.2-3.5 mm range; "
                                                "keep bosses/ribs ≤ 60% of nominal wall to avoid sink."), "No change to nominal wall; core bosses and ribs to ≤ 60% of the wall."
        out.append(DFMIssue(id="m_wall", severity=sev, category="wall_thickness", method=DFMMethod.measured, part_id=part_id,
                            description=desc, fix=fix,
                            rule_citation=f"PC/ABS wall 1.2-3.5 mm, ribs/bosses ≤ 60% of wall — {PROTOLABS}",
                            measurement=_m(t, "mm", check)))
    return out


def measure(step_path: str | Path, pull_dir: Iterable[float] = (0, 0, 1), finish: str | None = None,
            material: str | None = None, part_id: str | None = None) -> list[DFMIssue]:
    from build123d import import_step

    shape = import_step(str(step_path))
    return issues_from_facts(facts(shape, pull_dir), finish=finish, material=material, part_id=part_id)
