"""Standard parts + DFM details for professional, manufacturable CAD (C1). Everything is gated by the env var
CAD_DETAIL_LEVEL = basic (default: the CAD is unchanged) | pro (fasteners, inserts, bosses, snap-fits, joinery…).

    from api.cad.stdparts import screw, heat_set_insert, screw_boss, …   # also allowed inside the codegen sandbox
    detail_level() -> "basic" | "pro"

See README.md (dimension tables, rules and their citations, dependency decision). This package imports only
build123d + math at module level so the sandboxed AI programs can use it; `bom.bom_items` imports the contracts lazily.
"""

# these imports are the public API (see SANDBOX_NAMES)
from api.cad.stdparts.dfm import (RULES, boss_dims, clearance_hole, gasket_groove, gusset, parting_split,  # noqa: F401
                                  rib, screw_boss, snap_fit, tap_hole, uniform_fillet, weld_lip)
from api.cad.stdparts.hardware import (StdPart, bearing, cam_lock, dowel_pin, fin_box, gasket,  # noqa: F401
                                       heat_set_insert, hex_nut, leash_plug, magnet, pt_screw, screw, spur_gear,
                                       tripod_insert, washer, wood_dowel, wood_screw)
from api.cad.stdparts.joints import add_parts, material_role, named, screw_joint, std_length  # noqa: F401
from api.cad.stdparts.level import detail_level, is_pro  # noqa: F401

# names an AI program may import from api.cad.stdparts (api.cad.codegen.sandbox enforces this list)
SANDBOX_NAMES = frozenset({
    "screw", "pt_screw", "hex_nut", "washer", "heat_set_insert", "dowel_pin", "wood_dowel", "wood_screw", "cam_lock",
    "magnet", "bearing", "spur_gear", "tripod_insert", "fin_box", "leash_plug", "gasket",
    "screw_boss", "boss_dims", "rib", "gusset", "snap_fit", "uniform_fillet", "parting_split", "clearance_hole",
    "tap_hole", "weld_lip", "gasket_groove", "screw_joint", "std_length", "material_role",
    "add_parts", "named",
})

PROMPT_SNIPPET = """
Professional detail (CAD_DETAIL_LEVEL=pro) — make the model manufacturable, with real standard parts:
- You may also write `from api.cad.stdparts import screw, heat_set_insert, screw_boss, …` (named imports only) —
  helpers with ISO dimensions. Hardware: screw(size "M1.6"-"M5", length, head "pan"|"countersunk"|"socket"),
  pt_screw(d, length) (thread-forming, plastics), heat_set_insert(size), hex_nut(size), washer(size),
  dowel_pin(d, length), wood_dowel(d), wood_screw(d, length), cam_lock(), magnet(d, h), bearing("608"),
  spur_gear(module, teeth, thickness, bore), tripod_insert(), fin_box(), leash_plug(), gasket(L, W, r, cord).
  Each returns a StdPart: place it with `.at(x, y, z, rx, ry, rz)` (screws: head underside on z=0, shank to -Z;
  ry=180 drives it upward) and label it like any part, role "steel" (screws, nuts, bearings) or "brass" (inserts).
- DFM generators (each applies a cited rule): screw_boss(size, height, wall, fastener="insert"|"pt"),
  rib(length, height, wall) (0.6 × wall thick), gusset(height, depth, wall), snap_fit(length, thickness, width),
  clearance_hole(size, depth, fit, head) / tap_hole(size, depth) (tools to subtract, ISO 273 / ISO 2306),
  parting_split(shape, z) -> (lower, upper), weld_lip(L, W, r), gasket_groove(L, W, r, cord) (tool to subtract).
- screw_joint(size, at=(x, y, z), direction=(0, 0, -1), grip, head, into="insert"|"pt"|"nut"|"tap", boss_len=None)
  -> placed [screw, insert/nut, boss] sized by the rules; add_parts(parts, shapes) labels + appends them.
  StdPart.along(origin, direction) places a part with its shank / body along `direction`.
- Housings: two halves split at the parting line, joined by 4 screws into inserts in drafted bosses (or snap-fits
  on small parts); name variables after what they are (lid_screws, inserts, bosses) so the parts list reads well.
"""

__all__ = sorted(SANDBOX_NAMES | {"StdPart", "RULES", "detail_level", "is_pro", "SANDBOX_NAMES", "PROMPT_SNIPPET"})
