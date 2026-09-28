# api/cad/assembly/ — assemblies, joints, measured interference (C2)

**Owner: C2.** Behind `CAD_ASSEMBLY=1` (default 0 = no route, no engineering group, no cost lines). Contract:
`contracts/api.md` "Assembly (C2)". Tests: `tests/test_c2_assembly.py`.

Pipeline (per version, cached in `FILES_DIR/<pid>/assembly_v<n>.json`):
1. **Solids** — the labelled STEP next to the version GLB (`model_v<k>.step`, `v<n>.step`, `v<n>_enclosure.step`), grouped into
   parts by the GLB's W29 node tree (`part_id` → mesh children `<role>.<n>`). Legacy W2 directions without a labelled STEP → 404.
2. **Contacts** (`engine.measure_pairs`) — OCCT boolean common for every pair with overlapping boxes (> 0.01 mm³ counts),
   BRepExtrema distance for pairs within 3 mm.
3. **Tree + mates** (`mates.py`) — Prim's spanning tree from the root (largest shell / frame) over the contact graph; each part
   waits for its best-paired parent (prop → motor → arm → hinge → fuselage, lens → gimbal camera, button → the part it shares a
   name word with…); soft parts (rubber / fabric) never carry structural parts. `classify` → kind / method / DOF + rule.
4. **Joints** (`engine.Posed`) — build123d `RigidJoint` / `RevoluteJoint` / `LinearJoint` on the parent, the child copied into
   the joint frame with a `RigidJoint` at its origin, `connect_to` re-places it (closure residual measured).
5. **Checks** — interference classified by rigid bodies (union over rigid / locked joints); motion study (props 12 poses,
   buttons pressed 0.5 mm, lids 0-100°, gimbal ±20°) with the moving subtree; clearances; screw material by line ∩ solid →
   ISO screw length, insert fit and engagement; fasteners → BOM lines (`fasteners.py`, C1 `api.cad.stdparts` if importable).
6. **Exploded vectors** — from the joint axis, cumulative along the tree.

Measured on the four recorded showcases (engine c2.1): whoop 6 parts / 0 interferences (strap drawn 1.4 mm clear of the pod →
`asm_support` warn), stick vacuum 28 / 0 (52 fasteners), home robot 27 / 0 (5 floating parts → warn), drone 25 / **6
interferences**: its 5-inch props overlap each other (motors 100 mm apart, Ø127 mm props) and sweep through the top battery —
a real defect of the recorded concept, found by the motion study.

## C5 — how to enable
1. Set `CAD_ASSEMBLY=1` (API env: Railway + local). Route, engineering "assembly" group (→ Factory Pack via `engineering`) and
   the `EngineeringArtifact.assembly` field turn on; nothing else is needed for those.
2. Parts metadata (owner of `api/studio/parts.py`), in `enriched()` after the loop builds `out`:
   ```python
   from api.cad.assembly import service as asm
   if asm.enabled():
       try:
           extra = asm.part_extras(ctx.pid, ctx.n)
           for e in out:
               e.update(extra.get(e["part_id"], {}))
       except Exception:  # noqa: BLE001 — parts never fail because of the assembly
           pass
   ```
3. Costs (owner of `api/costs/bom.py`), in `load_bom` just before `return match_bom(items, order_qty), gen, notes`:
   ```python
   from api.cad.assembly.service import costs_hook
   items = costs_hook(ctx, items)   # no-op when CAD_ASSEMBLY=0; replaces a generic "Fastener set" line
   ```
4. Web (W1): show `checks` with `domain == "assembly"` as an "Assembly" group; exploded view may use
   `PartMeta.explode_vector × explode_distance_mm`. PDF / Factory Pack renderer: `pack.engineering.assembly` (tree + checks).
