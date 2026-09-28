# api/cad/stdparts/ — standard parts + DFM detail (C1)

**Switch:** `CAD_DETAIL_LEVEL=basic|pro` (default `basic`; read at call time). At `basic` every family, seed program
and GLB is exactly what it was before C1 (golden test `tests/test_c1_stdparts.py::test_basic_is_unchanged`, recorded
from the pre-C1 HEAD). At `pro` the families add real hardware, joints and moulding features.

| module | what |
|---|---|
| `tables.py` | dimension tables (ISO / datasheets) + unit-price Estimates + citations |
| `hardware.py` | `StdPart` constructors: `screw` (pan ISO 14583 / countersunk ISO 14581 / socket ISO 4762), `pt_screw`, `hex_nut`, `washer`, `heat_set_insert`, `dowel_pin`, `wood_dowel`, `wood_screw`, `cam_lock`, `magnet`, `bearing`, `spur_gear`, `tripod_insert`, `fin_box`, `leash_plug`, `gasket` |
| `dfm.py` | rule-applying generators: `screw_boss`, `rib`, `gusset`, `snap_fit`, `uniform_fillet`, `parting_split`, `clearance_hole`, `tap_hole`, `weld_lip`, `gasket_groove` (+ `RULES` with citations) |
| `joints.py` | `screw_joint` (screw + insert / nut / tapped / thread-forming + boss, sized from the tables), `add_parts`, `named`, `material_role`, `std_length` |
| `bom.py` | `bom_lines(parts)`, `bom_items(lines)` → `BOMItem`, `merge_into(spec_items, lines)`, `family_lines(name, params)`, `hardware_names` / `node_extras` (GLB node names + extras) |
| `enclosure.py` | W2 / W17 two-shell products (lamp, boxes, tracker card, wearable pod): `enclosure_details(params)`, `pro_viewer_parts(params, features)`, `joint_for(params)` — in-process only |
| `level.py` | `detail_level()`, `is_pro()` |

A `StdPart` has `.part` (build123d solid in its own frame), `.meta` (kind, role, standard, size, material…) and `.bom`
(part text, standard, `unit_price_usd`, `price_label="estimate"`). `.at(x, y, z, rx, ry, rz)` / `.along(origin,
direction)` place a copy tagged `std_meta`. Geometry is cached per spec and drawn as 16-sided prisms (below the GLB
30° crease angle, so they shade round at ~60 triangles each); threads are not modelled (length / pitch in the meta).

## Dimension tables (all mm)

| part | standard | M2 | M2.5 | M3 | M4 | M5 |
|---|---|---|---|---|---|---|
| socket head dk / k / key | ISO 4762 | 3.98 / 2 / 1.5 | 4.68 / 2.5 / 2 | 5.68 / 3 / 2.5 | 7.22 / 4 / 3 | 8.72 / 5 / 4 |
| pan head dk / k / drive | ISO 14583 | 4.0 / 1.6 / T6 | 5.0 / 2.1 / T8 | 5.6 / 2.4 / T10 | 8.0 / 3.1 / T20 | 9.5 / 3.7 / T25 |
| countersunk dk / k | ISO 14581 (90°) | 4.4 / 1.2 | 5.5 / 1.5 | 6.3 / 1.65 | 9.4 / 2.7 | 10.4 / 2.7 |
| hex nut m / s | ISO 4032 | 1.6 / 4 | 2 / 5 | 2.4 / 5.5 | 3.2 / 7 | 4.7 / 8 |
| washer d1 / d2 / h | ISO 7089 | 2.2 / 5 / 0.35 | 2.7 / 6 / 0.55 | 3.2 / 7 / 0.55 | 4.3 / 9 / 0.9 | 5.3 / 10 / 1.1 |
| clearance fine / medium / coarse | ISO 273 | 2.2 / 2.4 / 2.6 | 2.7 / 2.9 / 3.1 | 3.2 / 3.4 / 3.6 | 4.3 / 4.5 / 4.8 | 5.3 / 5.5 / 5.8 |
| tap drill (d − P) | ISO 2306 | 1.6 | 2.05 | 2.5 | 3.3 | 4.2 |
| heat-set insert OD / L / hole | McMaster-Carr 94459A | 3.6 / 4 / 3.2 | 4.0 / 4 / 3.6 * | 4.7 / 5.7 / 4.0 | 6.3 / 8.2 / 5.6 | 7.1 / 9.5 / 6.4 |
| insert boss OD (2 × hole) | Covestro part design guide | 6.4 | 7.2 | 8.0 | 11.2 | 12.8 |

M1.6: ISO 4762 3.14 / 1.6, ISO 1580 pan 3.2 / 1.0, ISO 7046 countersunk 3.0 / 0.96, ISO 4032 1.3 / 3.2.
\* M2.5 insert interpolated (not in the 94459A table) — Estimate. Values cross-checked against the data tables of
bd_warehouse 0.3.0 (Apache-2.0).

Other parts: bearings ISO 15 (608 = 8 × 22 × 7, 625, 688, 6000, 6001, 6200) · dowel pins ISO 2338 m6 · wood dowels
DIN 68150 (Ø8 × 35) · cam connector Häfele Minifix 15 (Ø15 × 13.5 cam, Ø8 bolt hole, 24 mm edge) · tripod socket
ISO 1222 (1/4"-20 UNC, 5.5 mm min depth) · spur gears ISO 53 (20°, addendum 1·m, dedendum 1.25·m) · NdFeB discs,
fin box, leash plug: catalogue classes. Unit prices: catalogue order of magnitude at ~2,000 pcs, labelled Estimate.

## DFM rules (dfm.RULES)

| generator | rule | source |
|---|---|---|
| `screw_boss(…, "insert")` | hole = insert datasheet hole, OD = 2 × hole, height ≥ insert length + 0.5 | McMaster-Carr 94459A; Covestro *Part and Mold Design* |
| `screw_boss(…, "pt")` | hole 0.8·d, OD 2·d, engagement ≥ 2·d | EJOT DELTA PT design guide |
| bosses | 0.5° outside draft | Protolabs design guide |
| `rib` / `gusset` | thickness 0.6 × wall, height ≤ 3 × wall, 0.5° draft | Protolabs (60 % rule); Covestro |
| `snap_fit` | y = 0.67·ε·L²/h, L ≥ 5·h, ε(PC/ABS) = 2.5 %, 30° lead-in, 90° retention | Covestro *Snap-Fit Joints for Plastics* |
| `uniform_fillet` | r_in ≥ 0.5·t, r_out = r_in + t | Protolabs |
| `clearance_hole` / `tap_hole` | ISO 273 fits, DIN 974-1 counterbores / d − P | ISO 273, DIN 974-1, ISO 2306 |
| `weld_lip` | 90° energy director, height = base / 2 | Branson / Emerson ultrasonic part design |
| `gasket_groove` | depth 0.75·cord (25 % squeeze), width 1.4·cord | Parker O-Ring Handbook ORD 5700 |
| `parting_split` | split on the widest section, 0.3 mm reveal | Protolabs |
| draft | families keep their own draft (W2 1.5°, tapers): pro never removes it | — |

## Families at pro (`# === PRO DETAIL ===` block in each family module)

| family | pro detail |
|---|---|
| drone | body split on its parting line, 4 × M2 into inserts; 8 × M3 socket + nuts clamp the arms; motors on M3 16 × 19 (≥ 22 mm stators) or M2 12 × 12; M5 prop nuts |
| stick_vacuum | motor housing split + 3 radial PT screws into bosses; floor head 4 × PT screws into bosses; snap-fit bin latch + release button |
| home_robot | 6001-2Z bearing per wheel + M5 axle screw + washer; torso → base 4 × M4 into inserts in bosses; rear access panel, 4 × M3 countersunk into inserts |
| camera | bottom plate split off, 4 × M2 countersunk into inserts; 2 × M2 per end cap; ISO 1222 tripod insert |
| smartphone (ODM) | 2 × M1.6 countersunk at the bottom edge into the tapped frame; 6 × M1.6 board screws into tapped midframe bosses |
| irrigation | EPDM perimeter gasket in a face-seal groove, lid 4 × M4 into inserts |
| furniture | 16 beech dowels Ø8 × 35 + 8 Minifix cams at the rail / leg joints, 8 wood screws 4 × 30 into the top |
| board | fin boxes flush in the bottom (replace the basic slabs) + leash plug in the deck — no screws |
| lamp / boxes (W2 0-1) | `enclosure.py`: screws up through W2's floor bosses into inserts in new top-shell bosses (M2 / M2.5 / M3 by footprint) |
| tracker card (W2 slab ≤ 90 × 14) | ultrasonic-weld energy director on the bottom-shell rim, screwless |
| wearable pod (W17) | 2 × M2 into inserts in top-shell bosses |

Placed hardware becomes one GLB node per spec (`"M3 × 12 socket screws ×16"`, role fastener, layer `fasteners`,
extras: standard, size, count, `bom_item_id` = `hwN`, `unit_price` Estimate, DFM rule for features). The spec BOM
lines come from `bom.family_lines(name, params)` → `bom.merge_into(spec_items, lines)` (same `hwN` ids).

## Codegen sandbox

AI programs may `from api.cad.stdparts import <name>` for the names in `SANDBOX_NAMES` only (AST check in
`codegen/sandbox.py`, re-checked by the runner's import guard; `import api…`, star imports and other modules stay
forbidden). The package imports only build123d / math / dataclasses / os at module level. At pro the family seed
code includes its pro block; `PROMPT_SNIPPET` documents the helpers for the system prompt.

## Dependency decision: bd_warehouse not added

bd_warehouse 0.3.0 installs against build123d 0.13 and its fasteners / bearings build, but: `SpurGear` fails
("Edges are disconnected"), a `HeatSetNut` is 90 faces / 0.6 s (knurls) — 8 of them blow the 5 s budget, its fastener
classes are BuildPart-context oriented, and the codegen sandbox needs an auditable pure-build123d module. We vendor the
few parametric parts as our own code (numbers cross-checked against bd_warehouse's CSVs, credited above); no new
dependency, pyproject.toml / uv.lock unchanged.
