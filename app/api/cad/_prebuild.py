"""Regenerate the committed demo CAD in api/cad/prebuilt/<project_id>/. Owner: W2 (look + renders: W12).

    uv run python -m api.cad._prebuild              # GLB/STEP/STL (offline, deterministic)
    uv run python -m api.cad._prebuild --renders    # + missing AI concept renders dN.png (needs key + LLM_IMAGE_MODEL)
    uv run python -m api.cad._prebuild --renders --force   # regenerate all 6 renders

demo_desk_lamp:    d1/d2/d3.glb = the three fixture concepts (column, arc, puck) as full lamps with materials
                   (anodised stem, moulded head + base, lit diffuser, rubber ring);
                   enclosure.{step,stl,glb} = the two injection-moulded parts of d1 (head housing + base shell),
                   laid out side by side — the aluminium stem is an extrusion and is not part of the moulded set.
demo_tracker_card: d1/d2.glb = the 'small' rounded-box / puck presets as finished tags (button, light pipe);
                   d3.glb = the wallet card with its edge button; enclosure.{step,stl,glb} = the card slab at its real
                   size (85.6 × 54 × 2.8 mm, 0.5 mm wall, 1° draft, no bosses — ultrasonic-welded), built below the
                   generator's 1.2 mm wall clamp.
dN.png = AI concept renders ("AI concept render — illustrative, not the CAD"), prompt from the fixture brief +
direction + the colour used in the GLB, so image and 3D agree.
File names are underscore-prefixed so api.discovery does not import this module at startup.
"""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path

from api.cad.build import PREBUILT_DIR, _shell_half, build_direction, export_all, normalize
from api.cad.look import _labelled, build_assembly, describe_features, export_look, look_for

log = logging.getLogger("cad.prebuild")
FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

# direction -> (colour name, material string, finish string) used for the GLB materials AND the render prompt
LAMP_LOOK = {
    "d1": ("Warm white with natural anodised aluminium stem", "Aluminium 6063 + PC/ABS", "MT-11010 texture, warm white"),
    "d2": ("Graphite", "PC/ABS", "Soft-touch paint, graphite"),
    "d3": ("Charcoal base with warm white lamp", "Zinc die-cast + PC", "Powder coat, charcoal"),
}
TRACKER_LOOK = {
    "d1": ("Warm white", "Polycarbonate", "Matte VDI 24 texture, warm white"),
    "d2": ("Graphite", "Polycarbonate", "Soft-touch paint, graphite"),
    "d3": ("Black", "Polycarbonate", "Matte VDI 24 texture, black"),
}
LAMP_EXTRA = {
    "d1": "; details: slim round natural-silver anodised aluminium stem, long thin rectangular warm white LED head balanced centred on top of the stem like a T "
          "with a frosted diffuser strip underneath glowing warm white, square soft-cornered base with one small silver touch button",
    "d2": "; details: one continuous graphite arc from a round base to a round puck head, frosted diffuser under the head glowing warm white",
    "d3": "; details: low round charcoal powder-coated disc base with a warm white puck lamp tilted about 20° on it, "
          "frosted diffuser face glowing warm white",
}


def _two_shells(p: dict) -> list:
    """Bottom + top shell of normalized params p, top placed at its assembled height, labelled accent/body."""
    from build123d import Location, Plane

    p = normalize(p)
    fam, L, W, H, wall, d = int(p["family"]), p["length"], p["width"], p["height"], p["wall"], p["draft_deg"]
    hb = H * p["split_ratio"]
    from api.cad.build import pro_clearance

    bottom = _shell_half(fam, L, W, p["fillet"], hb, wall, d, p["edge_fillet"], int(p["boss_count"]), pro_clearance(p))
    top = _shell_half(fam, L, W, p["fillet"], H - hb, wall, d, p["edge_fillet"], 0).mirror(Plane.XY).moved(Location((0, 0, H)))
    return [_labelled(bottom, "accent", 1), _labelled(top, "body", 1)]


def _card_weld_lip():
    """Energy director of the welded ID-1 card at its real 0.5 mm wall (enclosure_details would use the generator's
    1.2 mm wall clamp): on the bottom-shell rim, mid-wall, at the split height."""
    from build123d import Location

    from api.cad.stdparts import dfm

    wall = 0.5
    lip = dfm.weld_lip(85.6 - wall, 54.0 - wall, max(3.5 - wall / 2, 0.5), base=min(0.6, wall * 0.4))
    placed = lip.moved(Location((0, 0, 1.4)))
    placed.std_meta = dict(lip.std_meta, name="Ultrasonic weld energy director", group="weld_lip")
    return [placed]


def _pro_export(parts: list, params: dict, stem: Path, look: dict, details: list | None = None) -> None:
    """C5 (CAD_DETAIL_LEVEL=pro): the chosen demo direction + its enclosure hardware (api.cad.stdparts.enclosure),
    exported with a labelled STEP next to the GLB (assembly checks, drawings); the STL is not kept."""
    from api.cad.families import export_parts
    from api.cad.stdparts import joints
    from api.cad.stdparts.enclosure import enclosure_details

    export_parts(joints.add_parts(parts, details if details is not None else enclosure_details(params), "body"), stem, look)
    stem.with_suffix(".stl").unlink(missing_ok=True)


def _look(did: str, table: dict) -> dict:
    _, material, finish = table[did]
    return look_for(material, finish)


def desk_lamp() -> None:
    from build123d import Axis, CenterArc, Circle, Compound, Cylinder, Location, Plane, Pos, RectangleRounded, Rot, extrude, sweep

    out = PREBUILT_DIR / "demo_desk_lamp"
    out.mkdir(parents=True, exist_ok=True)
    base = dict(family=0, length=120, width=120, height=22, fillet=20, edge_fillet=3, wall=2.2)
    head = dict(family=0, length=180, width=40, height=18, fillet=10, edge_fillet=2, wall=2.0, boss_count=0)

    # d1 Column: base shell + Ø16 anodised stem 300 mm + head housing on top, lit diffuser strip under the head
    base_parts = _two_shells(base)
    stem = _labelled(Cylinder(8, 300).moved(Pos(0, 0, 22 + 150)), "metal", 1)
    head_parts = [s.moved(Location((0, 0, 322))) for s in _two_shells(head)]
    diffuser = _labelled(Pos(0, 0, 321.6) * extrude(RectangleRounded(160, 26, 6), 0.8), "diffuser", 1)
    button = _labelled(Pos(0, -38, 22.2) * Cylinder(6, 1.2), "metal", 2)
    ring = _labelled(Pos(0, 0, -0.6) * (Cylinder(50, 1.2) - Cylinder(44, 1.2)), "rubber", 1)
    from api.cad.stdparts import is_pro

    if is_pro():  # the head's shells get their own labels (one part per solid in the labelled STEP / parts list)
        head_pro = [_labelled(s, s.label.split(".")[0], 2) for s in head_parts]
        _pro_export(base_parts + [stem, diffuser, button, ring] + head_pro, base, out / "d1", _look("d1", LAMP_LOOK))
    else:
        export_look(base_parts + [stem, diffuser, button, ring] + head_parts, out / "d1.glb", _look("d1", LAMP_LOOK))

    # enclosure = the moulded parts of d1, side by side (head housing next to the base shell)
    moulded = _two_shells(base) + [s.moved(Location((0, 100, 0))) for s in _two_shells(head)]
    export_all(_unlabelled(moulded), out / "enclosure")
    export_look(_two_shells(base) + [s.moved(Location((0, 100, 0))) for s in _two_shells(head)], out / "enclosure.glb",
                _look("d1", LAMP_LOOK))

    # d2 Arc: puck base + swept arc (same moulded colour) + puck head, lit diffuser under the head
    arc_base = _two_shells(dict(family=1, length=110, height=20, edge_fillet=4))
    try:
        path = CenterArc((0, 0), 180, 0, 90)  # quarter arc in XY, rotated into XZ below
        prof = Plane(origin=path @ 0, z_dir=path % 0) * Circle(12)
        arc = sweep(prof, path).rotate(Axis.X, 90).moved(Location((-180, 0, 20)))
    except Exception as e:  # noqa: BLE001
        log.info("arc sweep failed, straight stem instead: %s", e)
        arc = Cylinder(12, 180).moved(Pos(0, 0, 110))
    arc_head = [s.moved(Location((-180, 0, 200))) for s in _two_shells(dict(family=1, length=70, height=24, edge_fillet=3, boss_count=0))]
    arc_diff = _labelled(Pos(-180, 0, 199.4) * extrude(Circle(26), 0.8), "diffuser", 1)
    feet = _labelled(Pos(0, 0, -0.6) * (Cylinder(45, 1.2) - Cylinder(39, 1.2)), "rubber", 1)
    export_look(arc_base + [_labelled(arc, "body", 2), arc_diff, feet] + arc_head, out / "d2.glb", _look("d2", LAMP_LOOK))

    # d3 Puck: low powder-coated disc base + tilted puck lamp with a lit diffuser face
    disc = _labelled(Cylinder(65, 15).moved(Pos(0, 0, 7.5)), "coat", 1)
    puck_parts = _two_shells(dict(family=1, length=90, height=45, edge_fillet=6))
    puck_parts.append(_labelled(Pos(0, 0, 44.8) * extrude(Circle(30), 0.8), "diffuser", 1))
    puck = [s.moved(Rot(20, 0, 0)).moved(Location((0, 0, 40))) for s in puck_parts]
    ring = _labelled(Pos(0, 0, -0.6) * (Cylinder(58, 1.2) - Cylinder(52, 1.2)), "rubber", 1)
    export_look([disc, ring] + puck, out / "d3.glb", look_for("Zinc die-cast + PC", "Powder coat, charcoal", colour="#EDEBE6"))
    _clean(out)


def tracker_card() -> None:
    from build123d import Box, Pos

    from api.cad.directions import _PRESETS

    out = PREBUILT_DIR / "demo_tracker_card"
    out.mkdir(parents=True, exist_ok=True)
    fams = {"rounded_box": 0, "puck": 1}
    for i, (fam, code) in enumerate(fams.items(), 1):
        params = {"family": code, **_PRESETS["small"][fam]}
        build_direction(params, out, name=f"d{i}")
        build_assembly(params, out / f"d{i}.glb", _look(f"d{i}", TRACKER_LOOK), {"button", "led"})
    export_all(_card_slab(), out / "enclosure")
    card = _card_parts()
    export_look(card, out / "enclosure.glb", _look("d3", TRACKER_LOOK))
    edge_button = _labelled(Pos(-85.6 / 2 - 0.1, 0, 1.4) * Box(0.6, 9, 1.2), "button", 1)
    from api.cad.stdparts import is_pro

    if is_pro():  # welded card: energy director on the bottom-shell rim (no screws)
        card3 = dict(family=2, length=85.6, width=54.0, height=2.8, fillet=3.5, edge_fillet=0.3, wall=0.5, draft_deg=1.0,
                     boss_count=0, split_ratio=0.5)
        _pro_export(_card_parts() + [edge_button], card3, out / "d3", _look("d3", TRACKER_LOOK), _card_weld_lip())
    else:
        export_look(_card_parts() + [edge_button], out / "d3.glb", _look("d3", TRACKER_LOOK))
    _clean(out)


def _card_slab():
    """ID-1 card tracker: two 1.4 mm welded shells, 0.5 mm wall (matches the tracker_card fixture spec)."""
    return _unlabelled(_card_parts())


def _card_parts() -> list:
    from build123d import Location, Plane

    length, width, height, wall, draft = 85.6, 54.0, 2.8, 0.5, 1.0
    half = height / 2
    bottom = _shell_half(2, length, width, 3.5, half, wall, draft, 0.3, 0)
    top = _shell_half(2, length, width, 3.5, half, wall, draft, 0.3, 0).mirror(Plane.XY).moved(Location((0, 0, height)))
    return [_labelled(bottom, "accent", 1), _labelled(top, "body", 1)]


def _unlabelled(parts: list):
    """Compound for the STEP/STL export: the role labels only matter for the viewer GLB."""
    from build123d import Compound

    for s in parts:
        s.label = ""
    return Compound(children=parts)


def _clean(out) -> None:
    from api.cad.stdparts import is_pro

    shutil.rmtree(out / "_cache", ignore_errors=True)
    keep = {"demo_desk_lamp": "d1", "demo_tracker_card": "d3"}.get(out.name) if is_pro() else None  # C5: chosen direction
    for k in ("step", "stl"):
        for i in (1, 2, 3):
            if not (k == "step" and f"d{i}" == keep):
                (out / f"d{i}.{k}").unlink(missing_ok=True)


# --------------------------------------------------------------------------- AI concept renders


def renders(pid: str, fixture: str, table: dict, extras: dict | None = None, force: bool = False) -> None:
    import time

    from api.cad.renders import build_prompt, is_configured, render
    from contracts.artifacts import BriefArtifact, DesignArtifact

    if not is_configured():
        print("renders skipped: OPENROUTER_API_KEY / LLM_IMAGE_MODEL not set")
        return
    brief = BriefArtifact.model_validate_json((FIXTURES / fixture / "01_brief.json").read_text())
    design = DesignArtifact.model_validate_json((FIXTURES / fixture / "02_design.json").read_text())
    for d in design.directions:
        path = PREBUILT_DIR / pid / f"{d.id}.png"
        if path.exists() and not force:
            continue
        colour, material, finish = table[d.id]
        d = d.model_copy(update={"material": material, "finish": finish})
        extra = (extras or {}).get(d.id) or describe_features({"button", "led"} if d.id != "d3" else set())
        t = time.monotonic()
        ok = render(build_prompt(brief, d, colour, extra), path)
        print(f"{pid}/{d.id}.png", "ok" if ok else "FAILED", f"{time.monotonic() - t:.1f}s")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    desk_lamp()
    tracker_card()
    if "--renders" in sys.argv:
        force = "--force" in sys.argv
        renders("demo_desk_lamp", "desk_lamp", LAMP_LOOK, LAMP_EXTRA, force)
        renders("demo_tracker_card", "tracker_card", TRACKER_LOOK,
                {"d3": "; details: extremely thin flat card, exactly credit-card size 85.6 × 54 mm and only 2.8 mm thick — as thin as two stacked bank cards, perfectly flat, no bulge, shown lying flat next to nothing; one tiny flush button on the short edge"}, force)
    for f in sorted(PREBUILT_DIR.rglob("*")):
        if f.is_file():
            print(f.relative_to(PREBUILT_DIR), f.stat().st_size)
