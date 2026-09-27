"""Studio (W17): refine the product by prompting. Contract: contracts/api.md "Studio".

- store.py   — studio_version / studio_state tables (versions + stage 1-7 snapshots, current version)
- patch.py   — the ONE LLM call per refine: message + product state → typed PATCH (route "main")
- apply.py   — deterministic apply: brief, direction, CAD (version files), spec, BOM (LCSC), DFM, costs, shortlist
- product.py — family choice (wearable_band / ring), vocabularies, wearable certifications, preview, change list
- engine.py  — start / refine / restore jobs, per-project FIFO worker + write lock, guarded background work
- pin.py     — stages 1-3 return the current version for Studio projects, so "Make it" continues from it
- routes.py  — register(router)
"""
