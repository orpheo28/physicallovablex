# api/costs/

**Owner: W3 — Costs.** Only this session edits this folder. Stages 5 (Investment), 11 (Logistics), 12 (Financing), plus BOM matching and component risk used by stage 4.

## Public interfaces (cross-session contract — signatures are stable)
```python
from api.costs.lcsc import match_bom, component_risk
match_bom(items: list[BOMItem], order_qty: int = 2000) -> list[BOMItem]
#   electronic lines → lcsc_pn + unit_cost_est (Sourced "LCSC price, 2026-09-26", price break at order_qty × qty per unit);
#   unmatched → Estimate with the assumption written in source_or_assumption. Non-electronic lines unchanged. Input not mutated.
component_risk(items: list[BOMItem]) -> list[ComponentRiskItem]
#   electronic lines + Li-ion cells: low stock (<1000 medium, <100 high), extended part, single source, unmatched, UN38.3;
#   alternatives from the snapshot; stock = Sourced LabeledValue. lead_time_weeks is None.
from api.costs.financing import cash_curve, check_cash
from api.costs.landed import landed_cost, hts_line
```

## Modules
| File | Role |
|---|---|
| `lcsc.py` | snapshot loader, matcher, component risk |
| `bom.py` | BOM from stage 3 spec → pasted BOM → LLM ('fast') proposal → category template, then `match_bom` |
| `engine.py` | `@stage_handler(5)`: tiers, tooling, certifications, cash breakdown, margin, break-even |
| `landed.py` | `landed_cost()`, HTS lookup, `@stage_handler(11)` |
| `financing.py` | `cash_curve`, `check_cash`, `@stage_handler(12)` |
| `hts.py` | reads the USITC HTS cache: `duty_for(hts10, s301_heading)` → MFN + Section 301 rate + source_url + fetched_on |
| `precedent.py` | `find_precedent(example, text)`: closest cached CBP CROSS ruling (deterministic, no LLM, no network) |
| `freight.py` | Drewry WCI snapshot: lane rate ÷ units per 40ft (units = 67 m³ ÷ packed unit volume, Estimate) |
| `_fetch_hts.py`, `_fetch_cross.py` | one-off fetch scripts (never run in tests or at demo time); outputs committed |
| `data/` | `jlcpcb_parts.csv` (see `SNAPSHOT.md`), `hts.json` (fallback lines), `hts/<heading>.json`, `cross/<slug>.json`, `freight_wci.json` |

**Sourced data (W13).** Stage 11 HTS = code of the closest cached CBP ruling (assumption a7, label sourced, "not a binding
classification"); MFN from the cached USITC schedule; Section 301 is Sourced only when a cached ruling cites the 9903.88.xx
heading for the same 10-digit code, else Estimate 25%. Sea FCL freight = Drewry lane rate (a8, Sourced) ÷ units per 40ft (a9,
Estimate); LCL/air/express stay Fictional. No precedent → previous behaviour, label estimate. Destination: Los Angeles, East
Coast (New York lane) when the brief says so. Refresh: rerun the `_fetch_*.py` scripts and commit `data/`.

Stage 5 inputs: `volumes`, `volume_factor` (0.5-1.0), `reference_quantity`. Stage 11 inputs: `section_122`, optional `mode`.
Tests: `uv run pytest api/costs` (offline, temp DB, no key).
