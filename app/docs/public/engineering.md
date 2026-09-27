# Engineering

Concept-level engineering computed from the current project state: the brief (stage 1), the chosen direction and its shape family (stage 2), and the measured CAD (stage 3: bounding box, STEP solid volume, weight, BOM). Every number is a labeled value; every check carries its formula and a verdict — `pass`, `warn`, `fail` or `info` — against a stated threshold.

Fetch it with `GET /projects/{id}/engineering` (see [Studio API](/docs/studio-api)). Re-run it after each refine with `POST /projects/{id}/engineering/recompute`.

## Text-to-CAD

The AI writes build123d code, runs it in a sandbox, measures the result and repairs its own errors. The program is visible in the app's "CAD code" tab. In the Studio, version 1 is built from a parametric product family in under 35 s, then the AI model is generated in the background (`Version.cad_pending`) and patched in. Families seed and back up the AI model: board, furniture, stick vacuum, home robot, irrigation, solar array, drone, hair dryer, camera, smartphone, plus the wearable band and ring. Read the program at `GET /projects/{id}/cad/code/{k}` (`Version.preview.code_url`). A refine such as "wider nose" uses `regenerate_geometry` to edit that program and re-measure it. The geometry is concept level (see [Limits](/docs/limits)).

## Category packs

Each pack lists the applicable standards with citations, design risks and required tests. Categories: **wearable**, **furniture (baby)**, **home robot**, **vacuum**, **irrigation**, **rooftop solar**, **surfboard**, **lighting**, **tracker**, **drone**, **hair dryer**, **camera**, **smartphone**, and **generic** (consumer electronics).

Standards references are **Sourced** when the URL was checked to load (the date is in the citation note) and **Estimate** ("Standard to be confirmed") otherwise. Tests include drop, ingress, salt spray, tip-over and thermal, depending on the category.

## Physics checks

Computed on the measured CAD, each with inputs, formula, threshold and verdict. Examples per category: tip-over angle (furniture, robots), board volume in litres and buoyancy (surfboard), battery life from the power budget, vacuum air watts, irrigation pressure, and the IP-rating sealing checklist. Each check has a `domain` (including `flight` and `regulatory`). Values derive from measured geometry; assumptions such as density are labeled Estimate.

New categories add:

- **Drone:** `thrust_to_weight`, `hover_time` (momentum theory from battery Wh and hover power) and `drone_class` — EU C0 under 250 g, C1 under 900 g, C2 under 4 kg, **Sourced** from Regulation (EU) 2019/945.
- **Hair dryer** (IEC 60335-2-23): `dryer_power`, `dryer_airflow` and `outlet_temperature` = P / (ρ Q c_p).
- **Camera and smartphone** (ODM): radio certifications 47 CFR Parts 2/15/22/24/27, RED, PTCRB/GCF.

## Electronics architecture

`electronics` holds a power tree, netlist-level connections, a power budget with average current and battery life, and the note "PCB layout: next step (human or text-to-PCB)". No PCB layout is produced (see [Limits](/docs/limits)).

## Firmware skeleton

`firmware` is a generated project (framework `zephyr` BLE or `arduino` Wi-Fi) served as `GET /files/{id}/firmware.zip`. It is created from a template on the first `GET /engineering`; with an LLM key an LLM-generated version follows in the background (`pending_llm: true`, then GET again; `generated_by` says `template` or `llm:<model>`). Its README begins "Generated code — not compiled or tested". Treat it as a starting point.

## Prototype path

`prototype` gives the cost and time to a first prototype: enclosure volume (Measured), cost lines, a dev-kit BOM with parts matched to the LCSC snapshot (Sourced), assembly steps, `timeline_weeks` and `total_cost`. Example from the recorded run: a kitesurf wearable came to $317 and 4 weeks.

## Rooftop solar and PVGIS

For a rooftop-solar project (category `solar_roof`), `solar` holds the site-install analysis. Yield comes from **PVGIS (EU JRC)**, fetched on the date shown and labeled **Sourced**. Module count, kWp, annual kWh and payback are **Estimates**. Example: Biarritz, 35 m² → 5.59 kWp, 6,860 kWh/yr. Instead of factories, the project is matched with 3 certified installers, which are **Fictional — demo data**; `partner_word` is `installers` and `site_install` is true.

## Build strategy

`EngineeringArtifact.build_strategy` says how the category realistically gets built. `strategy` is `full_design`, `module_assembly` or `odm_customization`; the object also has `title`, `explanation`, `customisable[]`, `not_customisable[]`, `moq`, `entry_cost` and `lead_time` (Estimates with their assumption), `path[]` (for ODM: find an ODM with a close reference platform, customise enclosure, colours, display, sensors and software, then carry over or redo certifications), `certifications_note` and `assumptions[]`. It appears in the Factory Pack (section 10 summary) and the Launch Dossier ("Build strategy"). See [Concepts](/docs/concepts).

## Where it shows up

The Factory Pack has an "Engineering & prototype path" section (`FactoryPack.engineering`), and the Launch Dossier has a chapter of the same name after the 13 steps. When stage 3 is missing or cached, the artifact has `fallback: true`.
