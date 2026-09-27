# Concepts

## Factory Pack

The Factory Pack is the primitive: a spec package a factory can quote and build without back-and-forth. It contains the structured spec, CAD, BOM with component risk, DFM alerts, certification checklist, estimated landed cost, questions for the factory (EN + CN) and the assumption register.

Every later step consumes it: negotiation starts from it, QC checks against it, financing uses its cost model, logistics uses its landed cost. Each Studio version produces its own Factory Pack. Fetch it with `GET /projects/{id}/factory-pack`.

## Versions and diffs

Every prompt in the Studio creates a **version**. A version records:

- `message` — what you asked.
- `status` — `running`, `done` or `failed`.
- `changes[]` — a typed diff. Each change has an `area` (color, material, shape, dimensions, feature, component, price, markets, requirement, certification, cost), a `label`, `before`, `after` and a `label_kind`.
- `preview` — GLB and render URLs, the CAD program URL (`code_url`), measured dimensions, unit costs, top factories, required certifications.
- `cad_pending` — true while the AI CAD model of the version is generated or edited in the background.

How a refine works: one LLM call turns your message into typed operations (set color, set material, set dimensions, add a component, `regenerate_geometry` for a change of form, ...). Code then applies them deterministically: every value is re-checked and clamped, the CAD is rebuilt, the spec is measured on the new STEP, the BOM is matched to LCSC parts, DFM re-runs, costs and the shortlist are recomputed. The model never invents a measurement.

Restoring a version makes it current. Steps 8-13 and the Factory Pack of the previous current version are discarded (they described another product); Make it rebuilds them.

## The 13 steps in 4 phases

| Phase | # | Step |
|---|---|---|
| **Design** | 1 | Brief |
| | 2 | Industrial design (3 directions) |
| | 3 | CAD + technical spec |
| **Make it manufacturable** | 4 | DFM, components, certification |
| | 5 | Investment (500 / 2k / 10k, tooling, cash, margin, break-even) |
| | 6 | Where and how to produce |
| **Source** | 7 | Factory matching |
| | 8 | RFQ + agent negotiation |
| **Launch** | 9 | Tooling + samples |
| | 10 | Quality control (AQL) |
| | 11 | Logistics + duties |
| | 12 | Financing (cash curve) |
| | 13 | Brand + distribution |

Steps 1-7 are what the Studio keeps current. **Make it** runs 8-13 and assembles the Factory Pack.

## Honesty labels

Every number renders with one label. Hover for its source or assumption.

| Label | Meaning |
|---|---|
| **Measured** | Computed on the CAD (e.g. bounding box from the STEP, wall thickness, draft). |
| **Sourced** | A real price or official rate with a date and URL (LCSC parts, HTS duty rates, Drewry index, PVGIS, standards citations). |
| **Estimate** | An assumption, shown. Mechanical parts, assembly, tooling ranges, certification costs, lead times. |
| **Fictional — demo data** | Invented for the demo: the factory network, quotes, negotiation replies, carrier freight, transit days. |

If a step could not run live it serves a cached example and the app shows a "Cached example" banner (`fallback: true`). A cached example may be a different product.

## Build strategies

The engineering layer picks how a product of its category realistically gets built. All figures (MOQ, entry cost, lead time) are Estimates with stated assumptions.

| Strategy | Meaning | Categories |
|---|---|---|
| **Full design** | You design every part; a factory builds to your CAD and drawings. | furniture (baby), surfboard, lighting, tracker, generic |
| **Module assembly** | You design around bought-in, pre-certified modules (motor + driver, battery pack, radio module, heater + fan). | drone, irrigation, wearable, hair dryer, vacuum, rooftop solar |
| **ODM customization** | Nobody designs these from scratch for a first product: customise an ODM's reference platform. | smartphone, camera, home robot |

The result is the `build_strategy` field of the engineering artifact (`GET /projects/{id}/engineering`); its `strategy` is `full_design`, `module_assembly` or `odm_customization`. It is also shown in the Factory Pack and the Launch Dossier.

## Categories supported

Category packs: wearable, furniture (baby), home robot, vacuum, irrigation, rooftop solar, surfboard, lighting, tracker, **drone**, **hair dryer**, **camera**, **smartphone**, and a generic consumer-electronics pack. Factories can list specialities: a specialist of another category scores 50% on process fit in matching.

## Showcase gallery

`GET /examples` lists recorded examples, complete through Make it. Opening one costs nothing: everything is cached, including Studio versions and AI CAD programs. See [Engineering](/docs/engineering).
