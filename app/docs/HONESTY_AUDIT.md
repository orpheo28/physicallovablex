# Honesty audit (W9, 2026-09-26)

Scope: fixtures of both demo projects (`api/fixtures/desk_lamp`, `tracker_card`, `network`), the API outputs after `/demo/reset`,
the Launch Dossier PDF of each (`pdftotext` of `GET /projects/{id}/export`, 1 202 / 1 289 lines) and the visible copy in `web/src`
(read-only, W11 still editing). Reproduce the fixture part: `uv run python docs/audit_honesty.py [-v]`.
Rules checked: (1) every number carries a label, (2) "Sourced" = source + URL + date, (3) no real company as a factory,
(4) "Measured" only when produced by code, (5) no claim that the product does not back.

## Verdict
No blocker. Labels are present on every money/size/time figure that matters; the network is fully invented; the only "Measured"
values come from code. What remains is **provenance polish** (URLs on "Sourced" values, one inconsistent label, one unsupported
time claim). None of it changes a number.

## 1. Numbers without a label
- **Fixtures, PDF:** none that matter. Every `LabeledValue` has a label; the PDF prints `[Estimate]/[Sourced]/[Measured]` next to it.
- Bare numbers by design (contract fields that are not claims): stage ids, quantities/volumes (500/2 000/10 000), ranks, scoring
  weights/scores in stage 7, `cad_parameters` (design inputs to the CAD, mm), `size_bytes`, AQL levels, `pct_of_order`.
- **Network numbers** (`factories.json` capacity, load, lead time, defect/on-time rate; `rfqs.json` and `08_negotiation.json`
  prices, tooling, MOQ, lead times): unlabeled per field but every record has `label: "fictional"` and the PDF prints
  "Fictional — demo data" on the section. Acceptable per contract; the PDF quote table (desk lamp lines 751-760, tracker card
  827-836) shows prices as `$14.95` without a per-cell badge — the section header carries it.
- PDF prose figures (retail €89 / $24.99, "~10 h at 50 %", "125 units") come from the brief or a labeled value; no orphan figure found.
- **Web copy** (`web/src/app/about/page.tsx:90`, `web/src/components/StartProject.tsx:69`): "a factory shortlist in about **5 minutes**".
  Measured wow screen is ≈ 1 min on cached/live 10/10 runs (README "Latest live run"); "5 minutes" is not backed. → W11.

## 2. "Sourced" without URL + date
Date is present everywhere; **URL is missing** on these (the contract only asks `<source>, <YYYY-MM-DD>`, so this is stricter than the schema):

| What | Where | Missing | Owner |
|---|---|---|---|
| LCSC/JLCPCB unit prices (BOM, 4 lamp / 8 tracker lines) and stock | `api/costs/_common.py` (`LCSC_SOURCE` = "LCSC price via jlcsearch, 2026-09-26"), `api/costs/lcsc.py:240,291`; fixtures `03_cad_spec.json` bom[].unit_cost_est, `04_dfm.json` component_risks[].stock, `05_costs.json` bom_lines[], `factory_pack.json` bom[] (× 2 projects; the script flags 22 lamp + 47 tracker labelled values in total, all of the above) | URL. `lcsc_pn` exists on each line → `https://www.lcsc.com/product-detail/<PN>.html` | W3 (lcsc.py), W6 (regenerate fixtures) |
| `extended` = qty × unit price labeled Sourced | `05_costs.json` bom_lines[].extended ("24 × 0.0077") | it is a computation on a Sourced value: label **Estimate** or say "derived from sourced unit price" | W3 / W6 |
| Pre-shipment inspection **$268/man-day** ("V-Trust") | `api/fixtures/build_desk_lamp.py:62,457,490`, `build_tracker_card.py` (same); fixtures `09_tooling.json` milestones[6].payment, `10_qc.json` man_day_rate/inspection_cost | URL; the cited source is an **internal file** (`D_unit_economics.md`) | W6, W13 (find a public URL or downgrade) |
| Same rate, other label | live code `api/agents/tooling.py:202` labels it **Estimate** ("V-Trust rate") while the fixtures say **Sourced** → two labels for one number | pick one | W4 + W6 |
| ISO 2859-1 sample size (125 units, code letter K) | `build_*.py:479`, `10_qc.json` sample_size | URL/date (standard table, not a price) — label is defensible as Sourced, add "ISO 2859-1 Table 1/2-A, ed. year" | W4 / W6 |
| IEEPA line ($0) | `11_logistics.json` landed_cost_breakdown[5] | has CSMS number + date, no URL | W3 |
| Section 301 / HTS general rates, CBP CROSS rulings, Drewry WCI, eCFR | fixtures | **OK** (URL + fetched date present, e.g. `05_costs.json:41`) | — |

Sources cited only by name (fine, they are citations of design rules / benchmarks labeled Estimate): Protolabs (DFM rule citations,
`04_dfm.json`), Zetar Mold and Dragon Sourcing (`05_costs.json` assumptions, "vendor, medium").

## 3. Real company names in factory data
- `api/fixtures/network/*.json`, `desk_lamp/07_matching.json`, `08_negotiation.json`, `tracker_card/*`: **none** (checked against
  Foxconn, Jabil, Luxshare, Goertek, Pegatron, Wistron, Xiaomi, Huawei, Anker, IKEA, PCBWay, Xometry, Fictiv, JLCPCB, Alibaba…).
- The 8 factories are Orchid / Silverfern / Kestrel Bay… and every name ends with "(fictional)" (PDF: "Kestrel Bay Manufacturing (fictional)").
- Real names appear only as **sources or price references** (LCSC/JLCPCB, V-Trust, Protolabs, Zetar Mold, USITC, CBP, Drewry) — not as suppliers.
- Live factory agents/`POST /factories` force the `(fictional)` suffix and `label: fictional` (contracts/api.md) — not re-tested here.

## 4. "Measured" not produced by `measure.py`
- Code emitting `label="measured"`: `api/dfm/measure.py:260` (draft, undercut, projected area, wall thickness) and
  `api/cad/spec.py:203` (overall dimensions from the STEP bounding box, live stage 3). Nothing else in `api/**/*.py`.
- Fixtures: the 6 measured values per project are all DFM m1-m3 (draft, projection, wall) with the check text; they match
  `measure.py`'s output on `api/cad/prebuilt/<id>/enclosure.step` (per README/W6).
- **Inconsistency (not dishonest):** live stage 3 labels dimensions **Measured** (`api/cad/spec.py:203`) but the cached fixtures
  (`03_cad_spec.json` overall_dimensions, both projects) say **Estimate**, and the README table says "Measured / Estimate". Either
  regenerate the fixture dims from the STEP (Measured) or keep Estimate and fix the README row. → W2 / W6.
- **Structural risk:** `contracts/artifacts.py` `LabeledValue.label` accepts any label from LLM output. Nothing stops a stage handler
  built on an LLM reply from returning `measured`/`sourced`. Not exercised here (no live LLM run in this audit); a post-validation guard in the
  stage runner ("LLM-derived values may only be estimate/fictional") would make the rule enforceable. → W0/Monitor (optional).

## 5. Other observations
- EUR→USD 1.08 is a fixed demo assumption, stated as assumption a-* in `01_brief.json:11` and `05_costs.json:11` and shown as
  Estimate (retail $96.12). Fine; the PDF headline says Estimate.
- `README.md` says stage 5 unmatched parts are Estimate: confirmed in the PDF BOM (LEDs/IC/MOSFET Sourced, everything else Estimate).
- `web/src/app/about/page.tsx` facts (Mollick SSRN, Engadget) have URLs; the "30 late campaigns" line is flagged "Small, hand-picked
  sample, not a statistic" — good. Note "internal GTM research" has no URL by nature.
- Both PDFs end with the label legend and "Chinese text is machine-translated — to be reviewed by a native speaker".
- **Deploy-related:** the web app must show the "Cached example" banner when `fallback: true` (contract) — not audited on the deployed build.

## Follow-ups for the Monitor (file — owner — issue)
1. `web/src/app/about/page.tsx:90`, `web/src/components/StartProject.tsx:69` — W11 — "about 5 minutes" unsupported (≈ 1 min measured).
2. `api/costs/_common.py` / `api/costs/lcsc.py:240,291` + regenerate `api/fixtures/*/{03,04,05}*.json`, `factory_pack.json` — W3 + W6 — add LCSC product URL to Sourced prices/stock.
3. `api/fixtures/build_desk_lamp.py:62,457,490` and `build_tracker_card.py` — W6/W13 — V-Trust $268 cited to an internal file, no URL; label differs from `api/agents/tooling.py:202`.
4. `05_costs.json` bom_lines[].extended — W3/W6 — Sourced label on a derived product.
5. `api/cad/spec.py:203` vs `03_cad_spec.json` overall_dimensions — W2/W6 — Measured (live) vs Estimate (fixture) vs README.
6. `api/fixtures/*/11_logistics.json` landed_cost_breakdown[5] — W3 — IEEPA line: add the CSMS URL.
