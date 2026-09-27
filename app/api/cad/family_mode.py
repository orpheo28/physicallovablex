"""Product families in the stage pipeline (W21): stage 2 directions, stage 3 spec, stage 4 DFM, Studio.

When the brief maps to a W19/W21 parametric family (classify → seed_for: board, furniture, stick_vacuum, home_robot,
irrigation, solar_array, drone, hair_dryer, camera, smartphone), the three stage-2 directions are that family (three
parameter sets, < 1 s each with `families.export_family`) instead of W2's generic boxes. Wearables stay W17's
wearable_band / ring families.

    detect(brief, prompt) -> (category, family, variant) | None
    family_directions(pid, brief, prompt, hit, build=("d1", "d2", "d3")) -> [DesignDirection]
    family_of(direction) -> family name | None ;  fparams(direction) -> family parameters
    export_product(pid, direction, stem, colour=None, context=True) -> {"files", "measured", "params"}
    is_solid(direction) -> bool   # board / furniture / solar array: not a moulded shell

`DesignDirection.cad_parameters` of a family direction = the W2 housing keys (family 0-2, length, width, height,
fillet, wall … → the two-shell enclosure stage 3 builds for DFM on shell products) + `product_family` (code) + the
family parameters prefixed `fp_` + optional `fp_scale_x/y/z` (Studio dimension edits) + `density_g_cm3`.
Solid families (board, furniture, solar array) have no moulded enclosure: stage 3 exports the product itself as
enclosure.* and stage 4 replaces the moulded-shell checks with envelope / section checks on the product CAD.
"""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path
from typing import Any

from api.cad import families
from api.cad.build import FAMILY_CODES, normalize, project_dir

log = logging.getLogger("cad.family_mode")

KEY = "product_family"
PREFIX = "fp_"
SCALE = ("fp_scale_x", "fp_scale_y", "fp_scale_z")
CODES: dict[str, float] = {n: float(10 + i) for i, n in enumerate(families.names())}  # append-only: codes stay stable
NAMES: dict[float, str] = {v: k for k, v in CODES.items()}
SOLID = {"board", "furniture", "solar_array"}
CONTEXT_ROLES = {"roof", "wall"}  # scene context drawn with the product (the house under a PV array), not the product

# family -> shape text, material, finish, direction description, category label for humans
INFO: dict[str, dict[str, str]] = {
    "board": dict(shape="Surfboard hull (rocker, rails, fins)", material="PU foam core, fibreglass / polyester laminate",
                  finish="Gloss polish", desc="Shaped foam blank with rocker and soft rails, glassed; thruster fin boxes."),
    "furniture": dict(shape="Changing table / child furniture", material="Birch plywood 18 mm, water-based lacquer",
                      finish="Satin lacquer", desc="CNC-cut birch plywood frame, raised safety guards, wipe-clean pad, lower shelf."),
    "stick_vacuum": dict(shape="Cordless stick vacuum", material="PC/ABS (UL94 V-0)", finish="Satin",
                         desc="Floor head, aluminium wand, cyclone with clear bin, motor pod, pistol grip and battery."),
    "home_robot": dict(shape="Mobile home robot", material="PC/ABS (UL94 V-0)", finish="Soft-touch paint",
                       desc="Wheeled base, torso with a sensor head and one arm with a gripper."),
    "irrigation": dict(shape="Irrigation controller kit", material="ASA (UV-stable) housing", finish="Matte texture",
                       desc="Solar controller housing, solenoid valve on 1\" pipe, soil-moisture probe."),
    "solar_array": dict(shape="Rooftop PV array", material="Monocrystalline modules, anodised aluminium rails",
                        finish="Black frame", desc="Flush-mounted module array on rails, sized to the roof."),
    "drone": dict(shape="Quadcopter with gimbal", material="PA12-GF body, carbon-fibre arms", finish="Matte",
                  desc="Folding-arm quadcopter, top battery, 2-axis gimbal camera under the nose."),
    "hair_dryer": dict(shape="Pistol hair dryer", material="PC (heat-resistant, UL94 V-0)", finish="Soft-touch paint",
                       desc="Barrel with heater and fan duct, concentrator nozzle, intake filter cap, raked handle."),
    "camera": dict(shape="Camera body", material="PC/ABS (UL94 V-0)", finish="Leatherette + satin",
                   desc="Rounded body on an ODM camera module: lens barrel, grip, viewfinder, flash."),
    "smartphone": dict(shape="Slab smartphone", material="Aluminium 6063 frame, cover glass", finish="Bead-blasted anodised",
                       desc="Slab on an ODM reference board: aluminium frame, cover glass, rear camera island."),
}
# role -> density g/cm³ for the weight of solid products (Estimate); body density per family
ROLE_DENSITY = {"wood": 0.68, "fabric": 0.04, "metal": 2.70, "steel": 7.90, "glass": 2.50, "cell": 0.36, "rubber": 1.15,
                "fin": 1.60, "coat": 1.20, "accent": 1.15, "button": 1.15, "led": 1.20, "diffuser": 1.20, "clear": 1.20,
                "port": 2.0}
BODY_DENSITY = {"board": 0.065, "furniture": 1.15, "solar_array": 2.70}
FAMILY_ROLE_DENSITY = {"solar_array": {"metal": 0.45}}  # rails are hollow extrusions, drawn as solid bars
DENSITY_NOTE = {"board": "PU foam + fibreglass laminate effective density 0.065 g/cm³ (a 60 L board ≈ 4 kg)",
                "furniture": "birch plywood 0.68 g/cm³, foam pad 0.04, plastic 1.15",
                "solar_array": "PV module effective density 0.36 g/cm³ (≈ 21 kg per 1722 × 1134 × 30 mm module), hollow aluminium rails 0.45 effective"}
PROCESS = {"board": "hand / CNC shaping of a foam blank + hand lamination",
           "furniture": "CNC routing of plywood sheet + edge finishing + flat-pack assembly",
           "solar_array": "on-site installation of bought-in modules, rails and inverter"}
ROLE_PART = {  # family -> role -> (part name, process, material)
    "board": {"body": ("Board blank (shaped core + laminate)", "other", "PU foam + fibreglass/polyester"),
              "fin": ("Fins", "injection_molding", "Glass-filled nylon"), "rubber": ("Traction pad", "other", "EVA foam")},
    "furniture": {"wood": ("Birch plywood panels and legs", "cnc", "Birch plywood 18 mm"),
                  "fabric": ("Changing pad (wipe-clean foam)", "other", "PU foam, PVC-free cover"),
                  "body": ("Guard rails / trims", "cnc", "Birch plywood / HPL")},
    "solar_array": {"cell": ("PV modules", "other", "Monocrystalline glass-glass module"),
                    "metal": ("Mounting rails and clamps", "extrusion", "Anodised aluminium 6063")},
}
_NO_SCALE = re.compile(r"count|angle|deg|frac|twin_tip|solar|instant|shelf|^pad$|guard_sides|rows|cols|azimuth|pitch|tilt|"
                       r"^arm$|lens_count", re.I)

# three directions per family: (name, description, parameter overrides or a size factor, colour name, hex)
VARIANTS: dict[str, list[tuple[str, str, dict | float, str, str]]] = {
    "board": [("Classic", "Balanced outline: the reference shape for this brief.", {}, "Ocean blue", "#4F6F95"),
              ("Wide nose", "Fuller nose and more width up front: easier paddling and take-offs.", {"nose_width": 1.18, "width": 1.04}, "Sand", "#D9C7A3"),
              ("Performance", "Narrower, thinner, more rocker: turns tighter, needs more skill.", {"width": 0.93, "thickness": 0.9, "rocker_nose": 1.25}, "Coral", "#E07A5F")],
    "furniture": [("Nordic", "Reference frame with guards on three sides and a lower shelf.", {}, "Warm white", "#F2F2EF"),
                  ("Compact", "Smaller footprint for tight nurseries.", {"length": 0.88, "depth": 0.9}, "Sage", "#9DB09A"),
                  ("Soft", "Generous corner radii and a taller guard.", {"corner_radius": 2.2, "guard_height": 1.15}, "Oat", "#E6DCC8")],
    "stick_vacuum": [("Cyclone", "Reference layout: cyclone ring over a clear bin, pistol grip.", {}, "Nickel", "#9A9DA1"),
                     ("Big bin", "Larger clear bin and cyclone for bigger homes.", {"bin_diameter": 1.15, "bin_length": 1.12}, "Copper", "#B87333"),
                     ("Light", "Shorter, slimmer and lighter for quick clean-ups.", {"height": 0.93, "bin_diameter": 0.9, "motor_diameter": 0.9}, "Graphite", "#3A3D42")],
    "home_robot": [("Helper", "Reference: wheeled base, torso, sensor head, one arm.", {}, "Warm white", "#F2F2EF"),
                   ("Compact", "Low, compact body that fits under furniture.", "compact", "Graphite", "#3A3D42"),
                   ("Tall reach", "Taller torso and longer arm to reach shelves.", {"torso_height": 1.15, "arm_length": 1.15}, "Sage", "#9DB09A")],
    "irrigation": [("Solar kit", "Controller with a PV roof, valve and soil probe.", {}, "Warm white", "#EDEBE6"),
                   ("Slim", "Smaller controller housing.", {"housing_width": 0.82, "housing_height": 0.85}, "Moss", "#6B7F5E"),
                   ("Pro", "Larger controller for more zones.", {"housing_width": 1.2, "housing_height": 1.1}, "Graphite", "#3A3D42")],
    "solar_array": [("Flush mount", "Modules flush on rails, sized to the roof.", {}, "Black frame", "#2B2D30"),
                    ("Tilted racks", "10° extra tilt on racks for more winter yield.", {"module_tilt_deg": 10.0}, "Silver frame", "#9A9DA1"),
                    ("Compact", "One column fewer: lower cost, less yield.", {"cols": -1.0}, "All black", "#151618")],
    "drone": [("Follow", "Reference quad with a 2-axis gimbal under the nose.", {}, "Graphite", "#3A3D42"),
              ("Pocket", "Smaller frame and props for the lightest class.", "mini", "Arctic white", "#EDEDED"),
              ("Long range", "Longer arms, bigger props and battery for flight time.", {"arm_length": 1.12, "prop_diameter": 1.1, "battery_length": 1.15, "battery_height": 1.15}, "Signal orange", "#E8702A")],
    "hair_dryer": [("Pistol", "Reference barrel, concentrator and raked handle.", {}, "Stone", "#E8E4DC"),
                   ("Travel", "Shorter barrel and handle.", "compact", "Rose gold", "#C99A8B"),
                   ("Wide flow", "Wider outlet for a gentler, quieter airflow.", {"nozzle_outlet": 1.3, "barrel_diameter": 1.08}, "Midnight", "#1F2430")],
    "camera": [("Reference", "Body built around the ODM module, lens on the left.", {}, "Black", "#2B2D30"),
               ("Classic", "The other body style of the family.", "__other__", "Cream", "#EFE6D2"),
               ("Rangefinder", "Wider, lower body with an offset viewfinder.", {"width": 1.1, "height": 0.9}, "Mint", "#A8D5C2")],
    "smartphone": [("Slab", "Reference slab on the ODM board.", {}, "Graphite", "#3A3D42"),
                   ("Other size", "The other size of the family.", "__other__", "Chalk", "#EDEBE6"),
                   ("Pro camera", "Bigger camera island with three lenses.", {"bump_size": 1.25, "lens_count": 3.0}, "Sage", "#9DB09A")],
}


# preset -> (direction name, description) when a direction is a whole preset of the family
PRESET_NAME: dict[str, dict[str, tuple[str, str]]] = {
    "drone": {"follow": ("Follow", "7-inch-class quad with a 2-axis gimbal under the nose."),
              "mini": ("Pocket", "Smaller frame and 5-inch props for the lightest class.")},
    "hair_dryer": {"pistol": ("Pistol", "Full-size barrel, concentrator and raked handle."),
                   "compact": ("Travel", "Shorter barrel and handle.")},
    "home_robot": {"helper": ("Helper", "Wheeled base, torso, sensor head, one arm."),
                   "compact": ("Compact", "Low, compact body that fits under furniture.")},
    "camera": {"compact": ("Compact", "Compact body, lens on the left, rear display."),
               "instant": ("Instant", "Boxy instant-camera body: big lens, flash, print slot.")},
    "smartphone": {"slab": ("Slab", "Standard-size slab on the ODM board."), "mini": ("Mini", "Compact slab, one camera.")},
    "board": {"surf": ("Classic", "Balanced outline: the reference shape for this brief."),
              "kite": ("Twin tip", "Symmetric twin-tip kiteboard.")},
    "furniture": {"changing_table": ("Nordic", "Reference frame with guards on three sides and a lower shelf."),
                  "activity_table": ("Play", "Low activity table with rounded corners.")},
}


# --------------------------------------------------------------------------- detection


def brief_text(brief, prompt: str = "") -> str:
    """Founder words + name + one-liner. Not the key features: 'companion phone app' must not make a phone."""
    return " ".join(str(x) for x in [prompt, getattr(brief, "product_name", ""), getattr(brief, "one_liner", "")] if x)


def detect(brief, prompt: str = "") -> tuple[str, str, str | None] | None:
    from api.cad.codegen.classify import classify, seed_for

    text = brief_text(brief, prompt)
    cat = classify(text)
    fam, var = seed_for(cat, text)
    if fam in families.names():
        return cat, fam, var
    return None


# --------------------------------------------------------------------------- parameters


def family_of(direction) -> str | None:
    cp = getattr(direction, "cad_parameters", None) or {}
    return NAMES.get(float(cp.get(KEY, -1)))


def is_solid(direction) -> bool:
    return family_of(direction) in SOLID


def fparams(direction) -> dict[str, float]:
    cp = direction.cad_parameters or {}
    return {k[len(PREFIX):]: v for k, v in cp.items() if k.startswith(PREFIX) and k not in SCALE}


def scale_of(direction) -> tuple[float, float, float] | None:
    cp = direction.cad_parameters or {}
    s = tuple(float(cp.get(k, 1.0)) for k in SCALE)
    return None if all(abs(v - 1) < 1e-6 for v in s) else s  # type: ignore[return-value]


def _preset_for(name: str, spec: str, variant: str | None) -> str | None:
    """A whole-preset direction: the named preset, or another one than d1's (never the same shape twice)."""
    presets = list(families.module(name).PRESETS)
    if spec in presets and spec != variant:
        return spec
    return next((k for k in presets if k != variant), None)


def _apply_variant(name: str, base: dict[str, float], spec: dict | float | str, variant: str | None) -> dict[str, float]:
    if isinstance(spec, str):
        other = _preset_for(name, spec, variant)
        return families.params_for(name, other) if other else dict(base)
    if isinstance(spec, float):
        return families.params_for(name, **{k: v * spec for k, v in base.items() if not _NO_SCALE.search(k)})
    out = dict(base)
    for k, v in spec.items():
        if k not in out:
            continue
        out[k] = out[k] + v if k in ("cols", "rows") else (v if "deg" in k or "count" in k else out[k] * v)
    return families.params_for(name, **out)


def _from_text(name: str, base: dict[str, float], text: str) -> tuple[dict[str, float], list[str]]:
    """Sizes the founder stated (a 7'6" board, a 35 m² roof) → family parameters. Returns (params, notes)."""
    notes: list[str] = []
    p = dict(base)
    low = text.lower()
    if name == "board":
        m = re.search(r"(\d)\s*(?:'|’|ft|foot|feet)\s*(\d{1,2})?\s*(?:\"|”|''|in)?", text)
        if m:
            mm = (int(m.group(1)) * 12 + int(m.group(2) or 0)) * 25.4
            p["length"] = mm
            notes.append(f"Length {m.group(0).strip()} = {mm:.0f} mm from the prompt")
        if re.search(r"beginner|learn|longboard|mal|foamie|funboard", low):
            L = p["length"]
            p.update(width=max(p["width"], 560 if L >= 2100 else 540), thickness=max(p["thickness"], 72 if L >= 2100 else 66),
                     nose_width=max(p["nose_width"], 380 if L >= 2100 else 330), tail_width=max(p["tail_width"], 380),
                     rocker_nose=min(p["rocker_nose"], 100))
            notes.append("Beginner outline: wider, thicker, fuller nose, flatter rocker")
    if name == "solar_array":
        try:
            from api.engineering.solar import solar_design

            n = int(solar_design(text).module_count.value)
            rows = 2 if n >= 4 else 1
            p.update(rows=float(rows), cols=float(max(1, math.ceil(n / rows))))
            notes.append(f"{n} modules sized from the roof area (same rule as the engineering layer)")
        except Exception as e:  # noqa: BLE001
            log.info("solar sizing skipped: %s", e)
    return families.params_for(name, **p), notes


def housing(name: str, P: dict[str, float], measured_bbox: list[float]) -> dict[str, float]:
    """W2 two-shell enclosure standing for the product's main moulded housing (DFM, weight). Solid families: the
    product bbox, clamped by normalize (the enclosure files are replaced by the product itself)."""
    g = P.get
    if name == "stick_vacuum":
        L, W, H = g("bin_length", 230) * 1.1, g("motor_diameter", 72) * 1.4, g("bin_diameter", 96) * 1.1
    elif name == "home_robot":
        L, W, H = g("torso_diameter", 300), g("torso_diameter", 300) * 0.85, min(400.0, g("torso_height", 620) * 0.5)
    elif name == "irrigation":
        L, W, H = g("housing_width", 150), g("housing_depth", 60), g("housing_height", 190)
    elif name == "drone":
        L, W, H = g("body_length", 150), g("body_width", 82), g("body_height", 48)
    elif name == "hair_dryer":
        L, W, H = g("barrel_length", 185), g("barrel_diameter", 72), g("barrel_diameter", 72)
    elif name == "camera":
        L, W, H = g("width", 124), g("depth", 52), g("height", 78)
    elif name == "smartphone":
        return normalize({"family": 2, "length": g("length", 147), "width": g("width", 71.5), "height": g("thickness", 8.2),
                          "fillet": g("corner_radius", 10), "edge_fillet": 1.0, "wall": 1.2, "draft_deg": 1.0,
                          "split_ratio": 0.5, "boss_count": 4})
    else:
        L, W, H = sorted(measured_bbox, reverse=True)[:3] if measured_bbox else (300, 200, 100)
    short = min(L, W)
    return normalize({"family": 0, "length": L, "width": W, "height": H, "fillet": short * 0.25, "edge_fillet": min(H, short) * 0.08,
                      "wall": 2.2 if name in ("stick_vacuum", "home_robot", "hair_dryer") else 2.0, "draft_deg": 1.5,
                      "split_ratio": 0.5, "boss_count": 4})


def pack(name: str, P: dict[str, float], measured_bbox: list[float], density: float | None = None,
         scale: tuple[float, float, float] | None = None) -> dict[str, float]:
    cp = {**housing(name, P, measured_bbox), KEY: CODES[name], **{PREFIX + k: float(v) for k, v in P.items()}}
    if scale:
        cp.update({k: round(float(s), 4) for k, s in zip(SCALE, scale)})
    cp["density_g_cm3"] = density if density is not None else (BODY_DENSITY.get(name) or (2.7 if "Alumin" in INFO[name]["material"] else 1.15))
    return cp


# --------------------------------------------------------------------------- build


def _parts(name: str, P: dict[str, float], scale=None, context: bool = True) -> list:
    _, parts = families.module(name).build(P)
    if not context:
        parts = [p for p in parts if (p.label or "body").split(".")[0] not in CONTEXT_ROLES]
    if scale:
        from build123d import scale as b3d_scale

        out = []
        for p in parts:
            q = b3d_scale(p, by=tuple(scale))
            q.label = p.label
            out.append(q)
        parts = out
    return parts


def board_section_mm(direction) -> float | None:
    """Hull thickness measured on a 20 mm slice of the board body at the widest station (mid-length)."""
    try:
        from build123d import Box, Pos

        parts = _parts("board", fparams(direction), scale_of(direction), context=False)
        body = max((p for p in parts if (p.label or "").startswith("body")), key=lambda p: p.volume)
        bb = body.bounding_box()
        cut = body & (Pos(bb.center().X, bb.center().Y, bb.center().Z) * Box(20, bb.size.Y * 2, bb.size.Z * 2))
        return round(cut.bounding_box().size.Z, 1)
    except Exception as e:  # noqa: BLE001
        log.info("board section not measured: %s", e)
        return None


def measured_parts(direction) -> dict[str, Any]:
    """Measured facts of the product (context roles excluded), rebuilt from the direction's parameters (< 1 s)."""
    return families.measure_parts(_parts(family_of(direction), fparams(direction), scale_of(direction), context=False))


def export_product(pid: str, direction_or_name, stem: str, colour: str | None = None, context: bool = True,
                   params: dict | None = None, scale=None, out_dir: Path | None = None) -> dict[str, Any]:
    """<stem>.step/.stl/.glb in the project folder (+ measured facts of the product, context excluded)."""
    from api.cad.families import export_parts, family_look

    if isinstance(direction_or_name, str):
        name, P = direction_or_name, families.params_for(direction_or_name, **(params or {}))
    else:
        name, P = family_of(direction_or_name), fparams(direction_or_name)
        scale = scale or scale_of(direction_or_name)
        if colour is None:
            from api.cad.look import colour_of

            colour = colour_of(direction_or_name.finish)
    parts = _parts(name, P, scale, context)
    files = export_parts(parts, (out_dir or project_dir(pid)) / stem, family_look(colour or families.DEFAULT_COLOUR.get(name)))
    product = [p for p in parts if (p.label or "body").split(".")[0] not in CONTEXT_ROLES]
    return {"files": files, "measured": families.measure_parts(product), "params": P, "family": name}


def _lv_mm(v: float, note: str):
    from contracts.artifacts import LabeledValue

    return LabeledValue(value=round(v, 1), unit="mm", label="measured", source_or_assumption=note)


def direction(pid: str, did: str, name: str, P: dict[str, float], vname: str, vdesc: str, cname: str, chex: str,
              build: bool = True, scale=None):
    from contracts.artifacts import DesignDirection, Dimensions

    info = INFO[name]
    if build:
        res = export_product(pid, name, did, colour=chex, params=P, scale=scale)
        bbox = res["measured"]["bbox_mm"]
    else:
        bbox = families.measure_parts(_parts(name, P, scale, context=False))["bbox_mm"]
    note = "Bounding box of the built family CAD (build123d/OCCT)"
    return DesignDirection(
        id=did, name=vname, description=f"{vdesc} {info['desc']}", shape=info["shape"], material=info["material"],
        finish=f"{info['finish']} · {cname} {chex}",
        dimensions=Dimensions(length=_lv_mm(bbox[0], note), width=_lv_mm(bbox[1], note), height=_lv_mm(bbox[2], note)),
        cad_parameters=pack(name, P, bbox, scale=scale), glb_url=f"/files/{pid}/{did}.glb" if build else None)


def family_directions(pid: str, brief, prompt: str, hit: tuple[str, str, str | None],
                      build: tuple[str, ...] = ("d1", "d2", "d3")) -> tuple[list, list[str]]:
    """Three directions of the family (d1 = reference + sizes from the prompt). Directions not in `build` get
    glb_url None (Studio builds them lazily with `build_direction_files`). Returns (directions, notes)."""
    _, name, variant = hit
    base = families.params_for(name, variant)
    base, notes = _from_text(name, base, brief_text(brief, prompt) + " " + " ".join(getattr(brief, "key_features", []) or []))
    out = []
    names = PRESET_NAME.get(name, {})
    for i, (vname, vdesc, spec, cname, chex) in enumerate(VARIANTS[name], 1):
        did = f"d{i}"
        P = base if i == 1 else _apply_variant(name, base, spec, variant)
        if i == 1 and variant in names:
            vname, vdesc = names[variant]
        elif isinstance(spec, str) and (preset := _preset_for(name, spec, variant)) in names:
            vname, vdesc = names[preset]
        out.append(direction(pid, did, name, P, vname, vdesc, cname, chex, build=did in build))
    return out, notes


def build_direction_files(pid: str, d) -> None:
    """Studio lazy build of a family direction (dN.glb + step/stl)."""
    export_product(pid, d, d.id)
    d.glb_url = f"/files/{pid}/{d.id}.glb"


# --------------------------------------------------------------------------- stage 3 helpers (solid products)


def spec_parts(name: str, measured: dict[str, Any]) -> list:
    """SpecParts of a solid product grouped by role (dimensions Measured on the largest part of each group)."""
    from contracts.artifacts import Dimensions, ProcessType, SpecPart

    groups: dict[str, list[dict]] = {}
    for row in measured["parts"]:
        groups.setdefault(row["role"], []).append(row)
    table = ROLE_PART.get(name, {})
    out = []
    for i, (role, rows) in enumerate(sorted(groups.items(), key=lambda kv: -sum(r["volume_mm3"] for r in kv[1])), 1):
        pname, proc, mat = table.get(role, (role.replace("_", " ").capitalize() + " parts", "other", INFO[name]["material"]))
        big = max(rows, key=lambda r: r["volume_mm3"])
        note = "Bounding box of the largest part of this group, built family CAD (build123d/OCCT)"
        out.append(SpecPart(id=f"p{i}", name=pname, material=mat, finish=INFO[name]["finish"], process_hint=ProcessType(proc),
                            tolerance="±1 mm (shaped / routed parts)" if name != "solar_array" else "Per module datasheet",
                            dimensions=Dimensions(length=_lv_mm(big["bbox_mm"][0], note), width=_lv_mm(big["bbox_mm"][1], note),
                                                  height=_lv_mm(big["bbox_mm"][2], note)), quantity=len(rows)))
    return out


def solid_weight(name: str, measured: dict[str, Any]):
    from contracts.artifacts import LabeledValue

    total = 0.0
    over = FAMILY_ROLE_DENSITY.get(name, {})
    for row in measured["parts"]:
        dens = BODY_DENSITY.get(name, 1.15) if row["role"] == "body" else over.get(row["role"], ROLE_DENSITY.get(row["role"], 1.15))
        total += row["volume_mm3"] / 1000.0 * dens
    vol = measured["volume_mm3"] / 1000.0
    return LabeledValue(value=round(total, 1), unit="g", label="estimate",  # grams, like every stage-3 weight
                        source_or_assumption=f"Solid volume {vol:.1f} cm³ (measured) × densities per part ({DENSITY_NOTE.get(name, 'per material')})")


def solid_bom(name: str, measured: dict[str, Any], brief=None) -> list:
    """Mechanical BOM of a solid product when the BOM LLM is unavailable (never a phantom MCU on a surfboard)."""
    from contracts.artifacts import BOMCategory, BOMItem, LabeledValue

    def est(v: float, why: str) -> LabeledValue:
        return LabeledValue(value=v, unit="USD", label="estimate", source_or_assumption=why)

    n_role = {r: sum(1 for p in measured["parts"] if p["role"] == r) for r in {p["role"] for p in measured["parts"]}}
    M, K = BOMCategory.mechanical, BOMCategory.packaging
    if name == "board":
        rows = [("PU foam blank (pre-rockered)", M, 1, 38.0), ("Fibreglass cloth 6 oz + 4 oz deck patch", M, 1, 22.0),
                ("Polyester laminating + hot-coat resin", M, 1, 18.0), ("Fin boxes (FCS-type plugs)", M, max(1, n_role.get("fin", 3)), 3.5),
                ("Fins, glass-filled nylon", M, max(1, n_role.get("fin", 3)), 4.0), ("Leash plug", M, 1, 1.2),
                ("Traction pad (EVA)", M, 1, 9.0), ("Board sock + protective wrap", K, 1, 6.0)]
    elif name == "furniture":
        rows = [("Birch plywood 18 mm sheet, CNC-cut (panels, legs, guards)", M, 1, 46.0), ("Cam-lock + dowel fittings kit", M, 1, 3.2),
                ("Wood screws 4 × 30 mm", M, 16, 0.03), ("Changing pad, wipe-clean foam, PVC-free cover", M, 1, 14.0),
                ("Anti-tip wall strap kit", M, 1, 1.5), ("Water-based lacquer (EN 71-3)", M, 1, 3.0),
                ("Flat-pack carton + corner protectors", K, 1, 7.5), ("Assembly instructions (pictograms)", K, 1, 0.4)]
    else:  # solar_array
        mods = max(1, n_role.get("cell", 10))
        rows = [("PV module 430 W monocrystalline", M, mods, 105.0), ("String inverter 5 kW (or microinverters)", M, 1, 850.0),
                ("Aluminium mounting rails, per module", M, mods, 18.0), ("Mid / end clamps", M, mods * 2, 1.2),
                ("Roof hooks (tile)", M, mods * 2, 4.5), ("DC cable 6 mm² + MC4 connectors", M, 1, 60.0),
                ("AC protection box (breaker, surge protector)", M, 1, 140.0)]
    items = []
    count = {"mechanical": 0, "packaging": 0}
    for part, cat, qty, usd in rows:
        key = str(getattr(cat, "value", cat))
        count[key] += 1
        items.append(BOMItem(id=("m" if key == "mechanical" else "k") + str(count[key]), part=part, category=cat, qty=qty,
                             unit_cost_est=est(usd, "Template estimate (category default, not a quote)")))
    return items


# --------------------------------------------------------------------------- stage 4 (solid products)


def solid_issues(name: str, measured: dict[str, Any], part_id: str | None = None, params: dict | None = None) -> list:
    """Measured checks that make sense for a solid product (the moulded-shell checks do not): process fit, stock
    size, thinnest section. Every issue carries a Measured value from the product CAD."""
    from contracts.artifacts import DFMIssue, DFMMethod, LabeledValue, Severity

    def m(v: float, unit: str, check: str) -> LabeledValue:
        return LabeledValue(value=round(v, 1), unit=unit, label="measured", source_or_assumption=check)

    bb = measured["bbox_mm"]
    vol_l = measured["volume_mm3"] / 1e6
    src = "measured on the product CAD (build123d/OCCT)"
    out = [DFMIssue(
        id="m_process", severity=Severity.minor, category="other", method=DFMMethod.measured, part_id=part_id,
        description=(f"Solid product ({vol_l:.1f} L of material): not an injection-moulded shell, so draft, undercut, wall "
                     f"thickness and clamp tonnage do not apply. Process: {PROCESS.get(name, 'see production plan')}."),
        fix="Quote the listed process; send the STEP as the shaping / routing / layout file.",
        rule_citation="Moulded-shell DFM rules apply to injection moulding only (Protolabs design guide)",
        measurement=m(vol_l, "L", f"Solid volume of all parts, {src}"))]
    parts = measured["parts"]
    if name == "board":
        L, T = max(bb), min(sorted(bb)[:2])
        if params and params.get("section_mm"):  # the bbox includes the rocker: use the measured mid-length section
            T = float(params["section_mm"])
        ok = L <= 2745  # 9'0" blanks are the common long stock
        out.append(DFMIssue(id="m_stock", severity=Severity.minor if ok else Severity.major, category="material",
                            method=DFMMethod.measured, part_id=part_id,
                            description=f"Board length {L:.0f} mm ({L / 304.8:.1f} ft) {'fits' if ok else 'exceeds'} standard PU blank stock (up to 9'0\" / 2745 mm).",
                            fix="Order the next blank size up with the right rocker; keep 20-30 mm shaping allowance.",
                            rule_citation="Blank sizes of the major foam suppliers (6'0\" to 9'0\" shortboard/mid-length ranges) — Estimate",
                            measurement=m(L, "mm", f"Overall length, {src}")))
        out.append(DFMIssue(id="m_section", severity=Severity.minor if T >= 55 else Severity.major, category="wall_thickness",
                            method=DFMMethod.measured, part_id=part_id,
                            description=f"Maximum hull thickness {T:.0f} mm (with rocker the bbox is taller): {'enough float for the brief' if T >= 55 else 'thin for a beginner board'}.",
                            fix="Keep ≥ 65 mm at the centre for beginners; move volume under the chest, not into the rails.",
                            rule_citation="Surf shaping rule of thumb: beginner mid-lengths 65-80 mm thick — Estimate",
                            measurement=m(T, "mm", f"Smallest extent of the hull, {src}")))
    elif name == "furniture":
        wood = [p for p in parts if p["role"] == "wood"] or parts
        thin = min(min(p["bbox_mm"]) for p in wood)
        big = max(wood, key=lambda p: p["bbox_mm"][0] * p["bbox_mm"][1])
        a, b = sorted(big["bbox_mm"], reverse=True)[:2]
        fits = a <= 2440 and b <= 1220
        out.append(DFMIssue(id="m_stock", severity=Severity.minor if fits else Severity.major, category="material",
                            method=DFMMethod.measured, part_id=part_id,
                            description=f"Largest panel {a:.0f} × {b:.0f} mm {'fits' if fits else 'does not fit'} a 2440 × 1220 mm plywood sheet; nest all panels on as few sheets as possible.",
                            fix="Nest the CNC programme on full sheets; grain along the longest side.",
                            rule_citation="Standard plywood sheet 2440 × 1220 mm (8 × 4 ft)",
                            measurement=m(a, "mm", f"Largest panel length, {src}")))
        out.append(DFMIssue(id="m_section", severity=Severity.minor if thin >= 12 else Severity.major, category="wall_thickness",
                            method=DFMMethod.measured, part_id=part_id,
                            description=f"Thinnest wooden part {thin:.0f} mm: {'OK for screws and cam locks' if thin >= 12 else 'too thin for cam-lock fittings'}.",
                            fix="Keep structural panels ≥ 15 mm (18 mm birch ply); round every accessible edge r ≥ 2 mm (child safety).",
                            rule_citation="Cam-lock fittings need ≥ 15 mm board; EN 12221 asks for rounded accessible edges — Estimate",
                            measurement=m(thin, "mm", f"Smallest extent of the wooden parts, {src}")))
    else:
        mods = [p for p in parts if p["role"] == "cell"]
        n = len(mods)
        area = sum(p["bbox_mm"][0] * p["bbox_mm"][1] for p in mods) / 1e6 if mods else 0
        out.append(DFMIssue(id="m_stock", severity=Severity.minor, category="assembly", method=DFMMethod.measured, part_id=part_id,
                            description=f"{n} modules on the layout (projected module area ≈ {area:.1f} m²): standard 1722 × 1134 mm class, bought in.",
                            fix="Keep the 45 cm roof-edge margin; check rafter spacing against the roof-hook pitch on site.",
                            rule_citation="Installer practice: edge margins for wind uplift zones (EN 1991-1-4) — Estimate",
                            measurement=m(n, "modules", f"Modules counted in the layout CAD, {src}")))
        out.append(DFMIssue(id="m_section", severity=Severity.minor, category="other", method=DFMMethod.measured, part_id=part_id,
                            description=f"Array footprint {bb[0] / 1000:.1f} × {bb[1] / 1000:.1f} m incl. rails.",
                            fix="Survey the roof (area, orientation, shading) before ordering.",
                            rule_citation="Site survey before PV design — installer practice",
                            measurement=m(max(bb[0], bb[1]), "mm", f"Array footprint, {src}")))
    return out


__all__ = ["detect", "family_directions", "family_of", "fparams", "is_solid", "export_product", "measured_parts",
           "spec_parts", "solid_weight", "solid_bom", "solid_issues", "build_direction_files", "CODES", "SOLID", "INFO",
           "KEY", "PREFIX", "SCALE", "housing", "pack", "direction"]
