# Curated build123d example library (C4)

Retrieved into the codegen prompt when `CODEGEN_RAG=1` (see `../retrieval.py`). Every file is a complete program that
runs in the codegen sandbox as-is. Each file's docstring gives its title, a description and `tags:`.
`index.json` holds the measured facts per example (bbox, volume, number of parts, seconds, ok).

| prefix | what it holds | source |
|---|---|---|
| `seed_<family>_<variant>` | Complete products: the seed programs of our parametric families, with the variants whose proportions differ | generated from `api/cad/families` (`python -m api.cad.codegen.library --seeds`) |
| `generic_device` | The engine's own conventions example | `engine.GENERIC_SEED` |
| `encl_*` | Enclosures: shells with draft, lids/lips, bosses, snap fits, battery doors, vents/grilles, bezels, knobs, cable gland, sheet-metal bracket, overmold, ribs | hand-written for this library |
| `form_*` | Revolves, lofts, sweeps and threads: bottle, threaded cap/neck, gear, pulley, swept handles, lamp shade, duct, impeller, propeller, spring, bent tube, ring, headphones, fittings | hand-written for this library |
| `mech_*` | Patterns, mirrors and joints: hinges, clevis, ball joint, slider, caster, tripod, lamp arm, wheels, heatsink, key grid, brackets, counterbores, perforated/honeycomb panels, battery pack, chair, drawer | hand-written for this library |

Maintenance:

```bash
uv run python -m api.cad.codegen.library --seeds        # after a family changes
uv run python -m api.cad.codegen.library --reindex      # run all examples in the sandbox → index.json
uv run python -m api.cad.codegen.library --check encl_vent_slots   # try one example, no write
```

An example that fails `--reindex` is marked `ok: false` in `index.json` and is never retrieved.

## Licences and provenance

- All `encl_` / `form_` / `mech_` programs were written from scratch for this repository (build123d 0.13 algebra
  API) and checked in the sandbox. No third-party code was copied.
- [Zero-To-CAD-1m](https://huggingface.co/datasets/ADSKAILab/Zero-To-CAD-1m) (Autodesk AI Lab, Apache-2.0,
  1M synthetic CadQuery programs) and Text-to-CadQuery (GitHub; no licence file found, so treated as all rights
  reserved) were used only as a checklist of operation vocabulary (shells, lofts, sweeps, patterns, fillets). They
  are CadQuery, not build123d, and none of their code or data is included or imported. If dataset programs are ever
  translated in bulk, Zero-To-CAD's Apache-2.0 needs an attribution + NOTICE here; Text-to-CadQuery must not be
  used until its licence is known.
- build123d is Apache-2.0.
