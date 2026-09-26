# api/dfm/

**Owner: W2 — CAD + DFM.** Only this session edits this folder.

- `measure.py` — measured geometry checks on a STEP file (straight two-half pull along ±Z by default):
  draft per B-rep face (flag < 1°, < 3° on textured finishes), undercut candidates (ray occlusion per body),
  projected area → clamp-tonnage estimate, sampled wall thickness. Every `measurement` is `label: measured`
  with the check in `source_or_assumption`; the tonnage is stated as an Estimate with its formula.
- `stage.py` — `@stage_handler(4)`: measured issues first, then `api.agents.dfm_review.ai_review` (W4),
  `api.agents.certification.certification_map` (W4) and `api.costs.lcsc.component_risk` (W3), each in its own
  try/except → that section from the project's cached example with an Assumption. ≥3 issues guaranteed.
  If the measured part fails (no STEP, OCCT crash) the handler raises and the runner serves the fixture.
- `test_dfm.py` — `uv run pytest api/cad api/dfm` (offline, no key).

## Credit

The measurement logic (draft per face vs pull with flat faces read exactly and curved faces at the 5th
percentile of their area, tangent bands excluded, absolute area floor; straight-pull occlusion undercut
test per body with zero-draft faces trapped only if blocked both ways; rasterised silhouette projection) is
ported from **earthtojake/text-to-cad**, `skills/dfm/scripts/mold_tool.py` (DFM skill, PR #391),
MIT License, Copyright (c) 2026 Thompson Labs LLC — https://github.com/earthtojake/text-to-cad.
The port works on OCCT B-rep faces (build123d/OCP) instead of trimesh meshes, so it needs no extra dependency.

MIT License text (as required): Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions: The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT
WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.

Contracts: `contracts/artifacts.py`, `contracts/api.md`, `contracts/stage_runner.md`, `contracts/fixtures.md`. Never edit `contracts/`, `api/main.py`, `pyproject.toml`, `web/package.json` — send a CONTRACT CHANGE REQUEST to the Monitor.
