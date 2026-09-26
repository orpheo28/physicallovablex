# JLCPCB / LCSC parts snapshot

| | |
|---|---|
| Source repo | https://github.com/CDFER/jlcpcb-parts-database (derived from https://github.com/yaqwsx/jlcparts) |
| Files used | `jlcpcb-components-basic-preferred.csv` and `jlcpcb-components.sqlite3` (in-stock parts, ≥5 pcs), both from https://cdfer.github.io/jlcpcb-parts-database/ |
| Snapshot date | **2026-09-26** (file `Last-Modified: 2026-09-26 05:54 GMT`; per-part `fetched_at` between 2026-09-14 and 2026-09-25) |
| Licence | MIT (Copyright (c) 2024 Chris) — https://github.com/CDFER/jlcpcb-parts-database/blob/main/LICENSE |
| Local file | `jlcpcb_parts.csv` (~7.7 MB, 29,976 parts) |

## What is in it
- The published basic/preferred CSV held only 109 rows on the snapshot date (diodes, transistors, ESD; 1 basic, 105 preferred). It has no connectors or power ICs, so it cannot serve a BOM matcher on its own.
- We therefore merged it with the in-stock SQLite of the same repo (same licence): every part with a category, stock ≥ 5 and a price. Columns trimmed to
  `lcsc, category, subcategory, mfr, package, manufacturer, library_type, preferred, basic, description (≤160 chars), stock, price, fetched_at`.
- `library_type`: `base` = JLCPCB basic part, `expand` = extended part (JLCPCB charges a feeder loading fee per extended part type). `preferred = 1` = JLCPCB preferred part.
- `price` is the LCSC quantity-break string `min-max:price,…` in USD; `lcsc` is the numeric part of the LCSC/JLCPCB number (`C<lcsc>`).
- Part numbers of this snapshot differ from the older W0 fixture examples (`C725790` etc. came from a live jlcsearch query); both are real LCSC parts, the desk-lamp fixture is not regenerated from this file.

## Refresh
```
curl -sL https://cdfer.github.io/jlcpcb-parts-database/jlcpcb-components-basic-preferred.csv
curl -sL https://cdfer.github.io/jlcpcb-parts-database/jlcpcb-components.sqlite3
```
then re-run the merge described above and update `SNAPSHOT_DATE` in `api/costs/lcsc.py`.
