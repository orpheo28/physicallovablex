# CAD_DETAIL_LEVEL basic vs pro (C1)

Blender renders (`api/cad/_blender_render.py`, 1200 px, 64 samples) of the family GLBs at `basic` and `pro`:
`drone_*` (body parting line, arm clamp screws + nuts, M5 prop nuts, motor screws underneath), `irrigation_*`
(4 × M4 lid screws, EPDM gasket under the lid), `home_robot_*` (rear access panel with 4 countersunk M3; wheel
bearings / axle screws inside), `camera_*` (end-cap M2 screws, bottom-plate parting line; tripod insert underneath).
`pod_internals_pro` / `lamp_internals_pro`: the pro enclosures with the top shell hidden (pod: the two top-shell
M2 insert bosses; lamp: W2 floor bosses, screws + inserts inside). Most hardware is inside or underneath, so the
exterior change is deliberately subtle — the parts list / anatomy / BOM carry the rest.
