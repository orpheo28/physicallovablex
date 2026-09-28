"""2D technical drawings from a version's CAD (C3). Behind CAD_DRAWINGS (default on since C5; 0 = off). No LLM.

    GET /projects/{id}/drawings?version=n       → DrawingSheet[]  (built on first request, cached per version)
    GET /files/{id}/drawings/{name}             → v<n>_<sheet>.svg / .pdf, v<n>_set.pdf (all sheets, one PDF)

    drawings(pid, n=None) -> list[DrawingSheet]
    set_pdf(pid, n=None) -> Path | None          # used by the Factory Pack / Launch Dossier

Source geometry: the version's full-product STEP (model_v<k>.step / d<n>.step, same stem as its GLB) → assembly sheet
(front, left, iso, balloons = parts list ITEM tied to the stage-3 BOM line) + one sheet per distinct part (identical
instances grouped, largest first, up to MAX_PART_SHEETS); when the moulded shells live in a separate STEP
(v<n>_enclosure.step, the DFM input) they get their own sheets (walls, bosses, holes, section A-A).
Solids are matched to GLB parts by program label (STEP 'body_2' = GLB mesh 'body.2'), else by bounding box.
Every value on a sheet is measured on the STEP (label Measured); "Generated from CAD — verify before release".
"""

from __future__ import annotations

import gzip
import json
import logging
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from contracts.artifacts import DrawingSheet

log = logging.getLogger("cad.drawings")

DRAWINGS_VERSION = "d2"  # d2 (C5): readable part names; bump when the sheet rules change (cached v<n>.json is rebuilt)
MAX_PART_SHEETS = 12
GENERIC_MOULDED = re.compile(r"PC/ABS", re.I)
# GLB look roles that are not materials (api.cad.look role names)
ROLE_WORDS = re.compile(r"^(lower shell|moulded body|body|button|accent|shell)$", re.I)
SAFE = re.compile(r"^v\d{1,4}_[A-Za-z0-9]{1,8}\.(svg|pdf)$")
_locks: dict[str, threading.Lock] = {}
_reg = threading.Lock()


def enabled() -> bool:
    return os.getenv("CAD_DRAWINGS", "1").strip().lower() in ("1", "true", "yes", "on")  # C5: on by default


def _lock(key: str) -> threading.Lock:
    with _reg:
        return _locks.setdefault(key, threading.Lock())


def out_dir(pid: str) -> Path:
    from api.cad.build import files_root

    return files_root() / pid / "drawings"


# --------------------------------------------------------------------------- sources


def _steps(ctx) -> tuple[Path | None, Path | None]:
    """(full-product STEP, moulded-shells STEP) of the version."""
    from api.cad.files import resolve_file

    spec = ctx.arts.get(3)
    urls = [f.url for f in (spec.cad_files if spec is not None else [])]
    steps = [u.rsplit("/", 1)[-1] for u in urls if u.lower().endswith((".step", ".stp"))]
    stem = Path(ctx.glb_url.rsplit("/", 1)[-1]).stem
    model = resolve_file(ctx.pid, f"{stem}.step")
    encl = next((resolve_file(ctx.pid, s) for s in steps if "enclosure" in s and resolve_file(ctx.pid, s)), None)
    if model is None:
        others = [resolve_file(ctx.pid, s) for s in steps if "enclosure" not in s]
        model = next((p for p in others if p is not None), None)
    if model is None:
        model, encl = encl, None
    if encl is not None and model is not None and encl.resolve() == model.resolve():
        encl = None
    return model, encl


def _leaf_solids(shape) -> list[tuple[str, object]]:
    """(label, solid) of every solid, the label of its nearest labelled ancestor."""
    out: list[tuple[str, object]] = []

    def walk(node, label: str) -> None:
        lab = node.label if node.label and node.label not in ("COMPOUND", "product", "SOLID") else label
        kids = list(getattr(node, "children", []) or [])
        if kids:
            for k in kids:
                walk(k, lab)
        else:
            for s in node.solids():
                out.append((lab, s))

    walk(shape, "")
    return out


def _glb_labels(path: Path) -> dict[str, str]:
    """Program label ('body_2') → part_id, from the finished GLB (part node → mesh children named '<label>')."""
    from pygltflib import GLTF2

    g = GLTF2.load(str(path))
    out = {}
    for n in g.nodes:
        if isinstance(n.extras, dict) and "part_id" in n.extras:
            for k in n.children or []:
                nm = g.nodes[k].name or ""
                out[nm.replace(".", "_")] = n.extras["part_id"]
    return out


def _match_by_box(solid, meta: dict, used: set[str]) -> str | None:
    """GLB part whose measured size (and centre) matches the solid; GLB axes (x, y up, z) = STEP (X, Z, -Y)."""
    bb = solid.bounding_box()
    sz = (bb.size.X, bb.size.Z, bb.size.Y)
    c = (bb.center().X, bb.center().Z, -bb.center().Y)
    tol = 0.02 * max(sz) + 0.3

    def cost(m) -> float:
        ds = sum(abs(a - b) for a, b in zip(sz, m["measured_bbox_mm"]))
        dc = sum(abs(a - b) for a, b in zip(c, m.get("centroid_mm") or c))
        return ds + 0.5 * dc + (1e6 if ds > tol else 0) + (1e3 if m["part_id"] in used else 0)

    best = min(meta.values(), key=cost)
    return best["part_id"] if cost(best) < 1e6 else None


# W29 fallback names that only say which colour / material role a solid had (api.cad.parts.MATERIAL_ROLE_DEFAULT)
GENERIC_NAME = re.compile(r"^(dark|metal|steel|rubber|wood|coat|accent|body|bodies|lower body|part)( parts?)?( \d+)?$", re.I)
ROLE_NOUN = {"shell_top": "Housing", "shell_bottom": "Lower housing", "frame": "Structural part", "arm": "Arm",
             "strap": "Strap", "window": "Window", "button": "Button", "other": "Detail part", "component": "Component",
             "fastener": "Hardware part", "prop": "Propeller", "motor": "Motor", "battery": "Battery pack"}


def sheet_name(name: str, role: str | None, material: str) -> str:
    """C5: a readable title for a part whose only name is its colour role ('Dark part 3', 'Bodies'): role noun +
    material ('Structural part 3 — PA12-GF'); real names are kept."""
    m = GENERIC_NAME.match((name or "").strip())
    if not m:
        return name
    noun = ROLE_NOUN.get(role or "", "Part")
    if (role or "") in ("", "other") and m.group(1).lower() in ("body", "bodies"):
        noun = "Housing"
    mat = re.split(r"[,(;·]", material or "")[0].strip()
    return f"{noun}{m.group(3) or ''}" + (f" — {mat[:32]}" if mat and not ROLE_WORDS.match(mat) else "")


def _pretty(label: str) -> str:
    s = re.sub(r"[_\-]+", " ", re.sub(r"_\d+$", "", label or "part")).strip()
    return s[:1].upper() + s[1:] if s else "Part"


def _parts(ctx, step: Path, kind: str = "part") -> tuple[object, list]:
    """Import a STEP, group its solids into PartDefs (item numbers, names, material, finish, BOM line, qty)."""
    from build123d import Compound, import_step

    from api.cad.drawings.compose import PartDef
    from api.studio.parts import enriched

    scene = import_step(str(step))
    leaves = _leaf_solids(scene)
    try:
        meta = {p["part_id"]: p for p in enriched(ctx)}
    except Exception as e:  # noqa: BLE001
        log.info("drawings: no part metadata for %s: %s", ctx.pid, e)
        meta = {}
    labels = _glb_labels(ctx.path) if kind == "part" else {}
    spec = ctx.arts.get(3)
    spec_parts = {p.name.lower(): p for p in (spec.parts if spec is not None else [])}
    from api.studio import product as P

    direction = P.chosen(ctx.arts.get(2))
    d_mat = (direction.material or "").strip() if direction is not None else ""
    d_fin = (direction.finish or "").strip() if direction is not None else ""
    bom = {b.id: b for b in (spec.bom if spec is not None else [])}
    groups: dict[str, list] = {}
    used: set[str] = set()
    for lab, s in leaves:
        pid = labels.get(lab)
        if pid is None and meta and kind == "part":
            pid = _match_by_box(s, meta, used)
        if pid is not None:
            used.add(pid)
        groups.setdefault(pid or f"~{lab or len(groups)}", []).append(s)
    defs: list[PartDef] = []
    for key, solids in groups.items():
        m = meta.get(key, {})
        if key.startswith("~"):
            lab = key[1:]
            name = _pretty(lab) if not lab.isdigit() else "Part"
        else:
            name = m.get("name") or _pretty(key)
        if kind == "moulded":
            z = solids[0].bounding_box().center().Z
            name = key[1:] if key.startswith("~") else name
            name = _pretty(name)
        sp = spec_parts.get(name.lower())
        material = (sp.material if sp else None) or m.get("material") or ""
        finish = (sp.finish if sp else None) or m.get("finish")
        if d_mat and (ROLE_WORDS.match(material.strip()) or not material):
            material, finish = d_mat, finish or d_fin
        elif sp is None and d_mat and GENERIC_MOULDED.search(material) and not GENERIC_MOULDED.search(d_mat):
            material, finish = d_mat, d_fin or finish  # the viewer's default shell look, not the product's material
        name = sheet_name(name, m.get("role"), material)
        geom = solids[0] if len(solids) == 1 else Compound(children=[s for s in solids])
        d = PartDef(item=0, key=key.lstrip("~"), name=name, material=material, finish=finish, qty=1, solids=[geom],
                    bom_id=m.get("bom_item_id"), kind=kind,
                    wall_spec=sp.wall_thickness.value if sp is not None and sp.wall_thickness is not None else None)
        if d.bom_id and d.bom_id in bom:
            d.bom_part = bom[d.bom_id].part
        d._z = z if kind == "moulded" else 0.0  # type: ignore[attr-defined]
        defs.append(d)
    # identical instances (motor 1…4) → one item, qty n
    merged: dict[tuple, object] = {}
    for d in defs:
        g = d.solids[0]
        bb = g.bounding_box().size
        sig = (re.sub(r"\s*\d+$", "", d.name).lower(), tuple(sorted(round(x, 1) for x in (bb.X, bb.Y, bb.Z))),
               round(g.volume, 0), d.material)
        if sig in merged:
            merged[sig].qty += 1
        else:
            d.name = re.sub(r"\s+\d+$", "", d.name) if any(
                re.sub(r"\s*\d+$", "", e.name).lower() == sig[0] and e is not d for e in defs) else d.name
            merged[sig] = d
    items = sorted(merged.values(), key=lambda d: -d.solids[0].volume)
    for i, d in enumerate(items, 1):
        d.item = i
    return scene, items


# --------------------------------------------------------------------------- build


def _matches_a_part(shells: list, items: list) -> bool:
    """The DFM enclosure gets its own sheets only when it is the product's housing: its two largest dimensions
    match a part of the full-product model within 5 % (a generic stand-in box is left to the DFM stage)."""
    import numpy as np

    def top2(d) -> np.ndarray:
        return np.array(sorted(tuple(d.solids[0].bounding_box().size))[-2:])

    for sh in shells:
        a = top2(sh)
        if any(np.all(np.abs(a - top2(it)) <= 0.05 * a) for it in items):
            return True
    return False


def _names(ctx) -> str:
    brief = ctx.arts.get(1)
    if brief is not None and getattr(brief, "product_name", None):
        return brief.product_name
    from api.stages import runner

    return runner.get_project(ctx.pid).name


def build(ctx) -> list[DrawingSheet]:
    from api.cad.drawings import compose as C
    from api.cad.drawings.sheet import pdf_of

    model, encl = _steps(ctx)
    if model is None:
        raise LookupError("this version has no STEP file")
    product = _names(ctx)
    meta = C.Meta(product=product, pid=ctx.pid, version=ctx.n, date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                  source=model.name)
    scene, items = _parts(ctx, model)
    plan: list[tuple[str, str, object]] = [("A1", "assembly", None)]
    big = max(tuple(items[0].solids[0].bounding_box().size)) if items else 1.0
    drawn = [d for d in items if max(tuple(d.solids[0].bounding_box().size)) >= min(3.0, 0.03 * big)]
    for i, d in enumerate(drawn[:MAX_PART_SHEETS], 1):
        plan.append((f"P{i:02d}", "part", d))
    moulded = []
    if encl is not None:
        try:
            _, ms = _parts(ctx, encl, kind="moulded")
            if 1 <= len(ms) <= 4 and _matches_a_part(ms, items):
                moulded = sorted(ms, key=lambda d: getattr(d, "_z", 0.0))
        except Exception as e:  # noqa: BLE001
            log.info("drawings: moulded shells skipped: %s", e)
    for i, d in enumerate(moulded, 1):
        d.name = f"{d.name} — moulded (DFM model)"
        plan.append((f"M{i:02d}", "moulded", d))
    total = len(plan)
    out = out_dir(ctx.pid)
    out.mkdir(parents=True, exist_ok=True)
    short = re.sub(r"^(demo_|p_)", "", ctx.pid).upper()[:16]
    sheets, rows = [], []
    base = f"/files/{ctx.pid}/drawings"
    for k, (sid, kind, d) in enumerate(plan, 1):
        dwg = f"PLX-{short}-V{ctx.n}-{sid}"
        try:
            if kind == "assembly":
                sh = C.assembly_sheet(items, scene, C.Meta(**{**meta.__dict__}), f"{k}/{total}", dwg,
                                      f"{product} — general assembly")
            else:
                m = meta if kind == "part" else C.Meta(**{**meta.__dict__, "source": encl.name})
                sh = C.part_sheet(d, m, f"{k}/{total}", dwg)
        except Exception as e:  # noqa: BLE001 — one bad solid never loses the other sheets
            log.warning("drawings: sheet %s of %s v%s failed: %s", sid, ctx.pid, ctx.n, e, exc_info=True)
            continue
        name = f"v{ctx.n}_{sid}"
        (out / f"{name}.svg").write_text(sh.svg(), encoding="utf-8")
        (out / f"{name}.pdf").write_bytes(pdf_of([sh], sh.meta.get("title", name)))
        sheets.append(sh)
        rows.append(DrawingSheet(
            sheet=sid, kind=kind, part_id=None if d is None else d.key,
            title=(f"{product} — general assembly" if d is None else d.name), svg_url=f"{base}/{name}.svg",
            pdf_url=f"{base}/{name}.pdf", set_pdf_url=f"{base}/v{ctx.n}_set.pdf", version=ctx.n, size=sh.size,
            scale=sh.meta.get("scale", "1:1"), bbox_mm=sh.meta.get("bbox_mm", [0, 0, 0]),
            bom_item_id=None if d is None else d.bom_id, qty=1 if d is None else d.qty))
    if not sheets:
        raise LookupError("no drawing could be generated from this CAD")
    (out / f"v{ctx.n}_set.pdf").write_bytes(pdf_of(sheets, f"Drawings — {product} v{ctx.n}"))
    with gzip.open(out / f"v{ctx.n}_ir.json.gz", "wt", encoding="utf-8") as fh:  # the Launch Dossier redraws these
        json.dump([{"size": sh.size, "meta": sh.meta, "items": sh.items} for sh in sheets], fh)
    src = [model.name, model.stat().st_size] + ([encl.name, encl.stat().st_size] if encl else [])
    (out / f"v{ctx.n}.json").write_text(json.dumps({"_v": DRAWINGS_VERSION, "src": src,
                                                    "sheets": [r.model_dump(mode="json") for r in rows]}, indent=1))
    return rows


def _cached(pid: str, n: int) -> list[DrawingSheet] | None:
    f = out_dir(pid) / f"v{n}.json"
    try:
        raw = json.loads(f.read_text())
    except (OSError, ValueError):
        return None
    if raw.get("_v") != DRAWINGS_VERSION:
        return None
    rows = [DrawingSheet.model_validate(r) for r in raw.get("sheets", [])]
    d = out_dir(pid)
    if not all((d / r.svg_url.rsplit("/", 1)[-1]).is_file() for r in rows) or not all(
            (d / f"v{n}_{x}").is_file() for x in ("set.pdf", "ir.json.gz")):
        return None
    return rows


def drawings(pid: str, n: int | None = None) -> list[DrawingSheet]:
    """Raises runner.NotFound (404) for an unknown project / version, LookupError when the version has no STEP."""
    from api.studio.parts import version_context

    ctx = version_context(pid, n)
    with _lock(f"{pid}:{ctx.n}"):
        hit = _cached(pid, ctx.n)
        if hit is not None:
            return hit
        return build(ctx)


def set_pdf(pid: str, n: int | None = None) -> Path | None:
    """All sheets of the version as one PDF (built if needed); None when drawings are off or impossible."""
    if not enabled():
        return None
    try:
        rows = drawings(pid, n)
    except Exception as e:  # noqa: BLE001
        log.info("drawings: none for %s: %s", pid, e)
        return None
    p = out_dir(pid) / rows[0].set_pdf_url.rsplit("/", 1)[-1] if rows else None
    return p if p is not None and p.is_file() else None


def sheets_for_pdf(pid: str, n: int | None = None) -> list:
    """The version's sheets as drawable Sheet objects (for the Launch Dossier); [] when off or impossible."""
    from api.cad.drawings.sheet import Sheet

    if not enabled():
        return []
    try:
        rows = drawings(pid, n)
        f = out_dir(pid) / f"v{rows[0].version}_ir.json.gz"
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception as e:  # noqa: BLE001
        log.info("drawings: no sheets for the dossier of %s: %s", pid, e)
        return []
    return [Sheet(size=r["size"], items=r["items"], meta=r.get("meta") or {}) for r in raw]


def register(router: APIRouter) -> None:
    on = enabled()  # the web shows the Drawings tab only when the route is in the OpenAPI schema

    @router.get("/projects/{project_id}/drawings", response_model=list[DrawingSheet], tags=["drawings"],
                include_in_schema=on)
    def get_drawings(project_id: str, version: int | None = None) -> list[DrawingSheet]:
        if not enabled():
            raise HTTPException(404, "drawings are not enabled (CAD_DRAWINGS=0)")
        try:
            return drawings(project_id, version)
        except LookupError as e:
            raise HTTPException(404, str(e)) from None

    @router.api_route("/files/{project_id}/drawings/{filename}", methods=["GET", "HEAD"], tags=["drawings"],
                      include_in_schema=False)
    def get_drawing_file(project_id: str, filename: str) -> Response:
        from api.cad.files import SAFE as SAFE_ID

        if not enabled() or not SAFE_ID.match(project_id) or not SAFE.match(filename):
            raise HTTPException(404, "drawing not found")
        root = out_dir(project_id).resolve()
        path = (root / filename).resolve()
        if path.parent == root and not path.is_file():  # C5: a link from a Factory Pack before the sheets were built
            try:
                drawings(project_id, int(filename[1:].split("_", 1)[0]))
            except Exception as e:  # noqa: BLE001
                log.info("drawings: %s not built on demand: %s", filename, e)
        if path.parent != root or not path.is_file():
            raise HTTPException(404, f"drawing {filename} not found for project {project_id}")
        media = "image/svg+xml" if path.suffix == ".svg" else "application/pdf"
        return Response(content=path.read_bytes(), media_type=media, headers={
            "Content-Disposition": f'inline; filename="{project_id}_{path.name}"', "Cache-Control": "no-cache"})


__all__ = ["drawings", "build", "set_pdf", "sheets_for_pdf", "enabled", "out_dir", "register", "DRAWINGS_VERSION"]
