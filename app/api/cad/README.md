# api/cad/

**Owner: W2 — CAD + DFM.** Only this session edits this folder.

- `build.py` — `build_direction(params, out_dir, name=None)` → `{"step","stl","glb"}`. build123d two-shell
  enclosure (top/bottom split at `split_ratio`, real wall, 1.5° draft on every vertical wall via tapered
  extrusions, drafted M2.5 screw bosses). Families: 0 soft rounded box · 1 puck · 2 slim slab. Cached by
  params hash in `<out_dir>/_cache/`. Files live in `api/data/files/<project_id>/` (`FILES_DIR` overrides).
- `directions.py` — `@stage_handler(2)`: LLM "fast" proposes 3 directions (one per family) → clamped by
  `normalize`; deterministic presets by brief category when the LLM is unavailable. GLB at `/files/<pid>/dN.glb`.
- `spec.py` — `@stage_handler(3)`: direction from `inputs.direction_id` → chosen → first. Dimensions Measured
  from the STEP bounding box, weight = measured volume × stated density (Estimate). BOM/block diagram:
  LLM "fast" → cached example BOM → generic template. `cad_files` = chosen `/files/<pid>/dN.glb` ("Full product — materials", first GLB = viewer default) then
  `/files/<pid>/enclosure.{step,stl,glb}` ("Moulded parts (DFM)"; DFM reads the STEP).
- `look.py` (W12) — per-part PBR materials + full-product viewer GLB. `look_for(material, finish)` → role → glTF
  material (moulded body/lower shell in the direction colour, anodised aluminium, powder coat, TPE rubber, lit frosted
  diffuser, status light pipe, USB-C port, stainless steel). `build_assembly` = the two shells + feet/button/light
  pipe/port (+ diffuser for lighting, stainless bowl for pet/food) → **dN.glb**. dN.step/stl and `enclosure.*` stay
  the moulded shells only (DFM input); stage 3 recolours `enclosure.glb` from the chosen direction.
- `renders.py` (W12) — one AI concept render per direction (`LLM_IMAGE_MODEL` via OpenRouter, 1024² PNG,
  `/files/<pid>/dN.png` → `render_url`). Runs in parallel with the CAD builds; 25 s timeout + 1 retry inside a 27 s
  stage budget, else `render_url = null` (never fails stage 2). Honesty: Assumption `a2_render` (estimate)
  "AI concept render — illustrative, not the CAD".
- `_blender_render.py` (W12, offline) — `blender -b -P api/cad/_blender_render.py -- in.glb out.png [1600] [128]`:
  Cycles render of a material GLB (3-point area lights, shadow catcher, #F7F6F3 seamless background, 3/4 camera
  framed on the bbox, denoise). Produced `prebuilt/<id>/hero_dN.png` for both demos (Blender 5.2.2, ~45 s each).
  Caption: "Rendered from the CAD". Not in the live path.
- `files.py` — `GET /files/{project_id}/{filename}`: `api/data/files/<pid>/` → `api/cad/prebuilt/<pid>/` → 404.
  Whitelisted names, resolved path must stay in its base dir.
- `prebuilt/` — committed demo CAD, regenerate with `uv run python -m api.cad._prebuild`:
  `demo_desk_lamp` (d1 column / d2 arc / d3 puck concepts as full lamps with materials + dN.png renders (`--renders`); enclosure = moulded head housing + base shell) and
  `demo_tracker_card` (small presets; enclosure = d3 slim slab 86 × 54 mm).
- `test_cad.py` — `uv run pytest api/cad api/dfm`.

Contracts: `contracts/artifacts.py`, `contracts/api.md`, `contracts/stage_runner.md`, `contracts/fixtures.md`. Never edit `contracts/`, `api/main.py`, `pyproject.toml`, `web/package.json` — send a CONTRACT CHANGE REQUEST to the Monitor.
