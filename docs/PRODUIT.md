# PhysicalLovableX — product one-pager

Full detail: `PRD.md`. This page is the summary; if they differ, PRD.md wins.

## Narrative
Hardware doesn't ship late because of design or because of the factory. It ships late because nobody translates the idea into what the factory can build. We do that translation.

**Pitch line:** From idea or prototype to 1,000 units shipped, without speaking the factory's language.

## Primitive — the Factory Pack
A spec package a factory can quote and build without back-and-forth: structured spec, CAD, BOM with component risk, DFM alerts, certification checklist, estimated landed cost, questions for the factory (EN + CN), assumption register.
Every later layer consumes it: negotiation starts from it, QC checks against it, financing uses its cost model, logistics uses its landed cost. It is also the data that compounds into the moat.

## Enablers
1. Spec copilot  2. DFM + component check  3. Certification map  4. Cost and landed-cost engine  5. Factory matching through the production MCP  6. Factory Pack export

## The full journey (13 stages)
| # | Stage | Concept layer | Demo |
|---|---|---|---|
| 1 | Brief (idea OR prototype + BOM) | Lovable | Real |
| 2 | Industrial design (3 directions) | Lovable | Real |
| 3 | CAD + technical spec | Lovable | Real |
| 4 | DFM, components, certification | Core | Real — geometry checks **measured** on the CAD |
| 5 | Investment (500 / 2k / 10k, tooling, cash, margin, break-even) | Lovable | Real — electronics at **real LCSC prices**, rest "Estimate" |
| 6 | Where and how to produce | Lovable | Real |
| 7 | Factory matching + factory portal (MCP) | Alibaba | Simulated |
| 8 | RFQ + agent negotiation | Infra | Simulated |
| 9 | Tooling + samples | Infra | Generated plan |
| 10 | Quality control (AQL) | Infra | Generated plan |
| 11 | Logistics + duties | Infra | Simulated rates |
| 12 | Financing (cash curve, options) | Infra | Generated plan |
| 13 | Brand + distribution (name, packaging, landing, listing) | Idea → brand | Real |
Final export: Launch Dossier.

## Trust labels
Every number carries one label: **Measured** (on the CAD), **Sourced** (real price or official rate, dated), **Estimate** (assumption shown), **Fictional — demo data**.

## Two entry modes
- **"I have an idea"** — demo headline, faithful to the brief.
- **"I have a prototype"** — GTM wedge: founders with a working prototype and money pledged who are stuck on production.

## Wow moment
Prompt → in under 5 minutes: the product in 3D, its unit cost at three volumes, and a top-3 factory shortlist, on one screen.

## Business model (hypothesis)
Free up to the Factory Pack (land grab, data) → commission on the production order (tier 2, human-accompanied, committed landed price) → take rate on financing and logistics (tier 3).

## Not building
Sophisticated CAD rendering (commodity: Zoo, Backflip, Atech), a real marketplace, payments, real logistics booking.
