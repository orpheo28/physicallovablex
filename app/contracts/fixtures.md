# Fixtures contract

```
api/fixtures/
  <example>/                  # desk_lamp (W0), tracker_card (W6)
    project.json              # contracts.Project — id "demo_<example>", example "<example>"
    01_brief.json … 13_brand.json   # one file per stage: f"{n:02d}_{STAGE_NAMES[n]}.json"
    factory_pack.json         # contracts.FactoryPack
  network/
    factories.json            # contracts.Factory[] — fictional factory portal data
    rfqs.json                 # contracts.RFQWithQuotes[]
  build_desk_lamp.py          # source of the desk lamp set (computes consistent numbers)
```

Rules
- Every file validates against `contracts/artifacts.py` — `uv run pytest tests/test_fixtures.py`.
- A fixture's `project_id` is replaced by the requesting project's id when served as a fallback.
- Missing file in an example → the runner uses the `desk_lamp` file for that stage.
- Consistency (tested for the desk lamp): stage 5 `cash_breakdown` sums to `total_cash_needed`; stage 12
  `total_cash` equals it (`matches_stage5_total`); stage 11 landed cost within 10% of stage 5 (`reconciles_with_stage5`);
  3 volume tiers 500/2,000/10,000; ≥3 DFM alerts; ≥3 shortlisted factories.
- Honesty: real LCSC prices only with `sourced` + "LCSC price via jlcsearch, <date>"; every factory/quote/freight
  number `fictional`; no real factory names (the demo ones end with "(fictional)").

Former placeholders, now real: stage 4 `measured` issues come from `api/dfm/measure.py` on the committed CAD;
`cad_files` point to committed files in `api/cad/prebuilt/<id>/` (cad_files[0] = full-product GLB); HTS/301 from CBP precedent.

Both builders take landed cost, duties, freight and stages 11-12 from the live code (`api/fixtures/_live.py`).
To edit the desk lamp set: change `build_desk_lamp.py`, run `uv run python -m api.fixtures.build_desk_lamp`, run the tests.
