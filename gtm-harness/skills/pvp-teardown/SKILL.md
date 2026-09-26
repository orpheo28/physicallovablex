---
name: pvp-teardown
description: For one physical product, estimate its real landed manufacturing cost and its main production risks, keeping sourced figures strictly apart from estimates. It is a piece of value to offer a founder after a discovery call.
---

# PVP teardown

**Input:** a product, as a campaign or product URL, a spec sheet, photos or a BOM if the founder shares one.
**Output:** one page with three blocks: **Sourced**, **Estimated**, and **Risks**. Each line is tagged `[S]` (sourced, with a URL) or `[E]` (estimated, with its method). An `[E]` line is never presented as a fact.

## Steps
1. **Break the product down.**
   - Main parts: enclosure, PCB and electronics, battery, display, mechanics, packaging.
   - Materials and processes: injection moulding, CNC, die-casting, SMT.
   - Take these from the campaign page and teardown photos only.
2. **Sourced prices `[S]`.**
   - Look up component prices on distributor pages or official announcements, and note the URL and date.
   - Look up the retail or pledge price on the campaign page.
3. **Estimate the factory cost `[E]`.**
   - Price comparable parts (Alibaba or 1688 listings count as `[S]` for *that listing only*).
   - Apply them to the BOM, and state the method and the range.
4. **Build the landed cost.** Use the formula in `02_RECHERCHE/parallel/D_unit_economics.md`:
   `landed = FOB + freight + insurance + duties (HTS + surcharges) + broker/port + 3PL + agent + QC + mold amortisation`

   Reference values, all `[S]`:
   | Item | Value | Source |
   |---|---|---|
   | Simple injection mold (1 cavity, China) | $1,000-3,000 | [Zetar Mold](https://zetarmold.com/injection-mold-price-list-2026), vendor source |
   | Complex multi-cavity steel mold | $30,000-100,000 | same |
   | Pre-shipment inspection | $268 per man-day | [V-Trust](https://www.v-trust.com/en/our-network) |
   | Sourcing agent | 5-10% | [Dragon Sourcing](https://www.dragonsourcing.com/top-10-cost-insights-for-hiring-a-china-sourcing-agent/) |
   | US duties | By HTS line. Section 301 still applies, IEEPA ended 24/02/2026, de minimis suspended | `D_unit_economics.md` |

   Always look up the product's HTS code; never assume a country-wide rate.
5. **Find the risk points.** Use the thesis v2 buckets, and cite a comparable account from `outputs/accounts.csv` for each:
   - **Components:** single-source chip, memory price swings (KONKR), battery lead times (OneXPlayer 3).
   - **Certification:** radio or FCC exposure (HOVERAir AQUA, SwiftShape).
   - **DFM/engineering:** tight tolerances, a new process (Creality filament diameter, eufyMake ink pressure).
   - **Factory translation:** a spec the factory reads differently (Halliday).
6. **Write the "so what".** Name the 2 risks most likely to move the ship date, and the one question to ask the factory now.

## Output format
```
# <Product>: teardown (<date>)
Sourced [S]: retail $…, <component> $… (<URL>) …
Estimated [E]: BOM $…–…, factory cost $…–…, landed $…–… per unit. Method: …
Risks: 1. <bucket>: <why> (comparable: <account>, <URL>) 2. … 3. …
Top question for your factory: …
Confidence: low / medium. What would make it high: <BOM, factory quote>
```

## Rules
- Do not publish a single-point cost. Always give a range, with its method.
- Do not send the teardown cold. Offer it after a call, or when the founder asks for it (`03_DISCOVERY/messages.md`: sell nothing, promise nothing).
