# Positioning

Last updated: 2026-09-27. **Hypothesis: to be validated by discovery.** Format (pillars, matrix, guardrails) adapted from the GTM repository (credits in `README.md`).

## One-liner
**"From idea or prototype to 1,000 units shipped, without speaking the factory's language."** Product line: "Describe it. See it. Refine it. Make it." (`04_LIVRABLE/PRODUIT.md`). Outreach never uses either line: discovery messages sell nothing (guardrails below).

**Mechanism:** we do the translation between the product and the factory (DFM, component choice, certification, a spec in the factory's language) and package it as a Factory Pack. Only because we do that work can we later commit to a landed price and a quality level (thesis v2, `CLAUDE.md`).

## Value pillars
| Pillar | Leads for | Proof we have (real) | Proof we lack |
|---|---|---|---|
| **1. Translation, re-computed on every change** | Founder, engineering co-founder | Studio measured: first version 18-24 s, feature refine 4-7 s with real LCSC parts, DFM re-measured on the CAD, certification map (`PRODUIT.md`). Halliday's COO: "we didn't speak [the manufacturer's] language" ([Engadget](https://www.engadget.com/2216393/halliday-g2-smart-glasses/)) | Concept-level geometry, 7 live prompts; ~20% stays human (`PRODUIT.md`) |
| **2. One committed landed price** (tier 2) | Founder with a fixed pledge price | Landed-cost formula and cost engine built: FOB, freight, insurance, duties by HTS line, broker, 3PL, QC, mold amortisation (`02_RECHERCHE/parallel/D_unit_economics.md`; `PRODUIT.md`). Why it matters: KONKR RAM "nearly tripled" ([GSMGoTech](https://www.gsmgotech.com/2026/03/ayaneo-konkr-pocket-fit-elite.html)) | No real factory quote yet; factories in the demo are fictional (`context/profile.md`) |
| **3. Quality and delivery, published** | Founder, backers, factories | Trust labels on every number (Measured / Sourced / Estimate / Fictional) are built (`PRODUIT.md`). No competitor publishes on-time rate, defect rate or rejected lots (`02_RECHERCHE/parallel/B_concurrence.md`, "Lecture" §2) | No run yet: the on-time and defect rates start at run 1 |

## Messaging matrix (per face)
| Face | Persona file | Lead with | Proof to show | Avoid |
|---|---|---|---|---|
| **Founder** (ECP, user = buyer) | `personas/hardware-founder.md` | Their own dated signal and one question about the cause. After a call only: a teardown or a free human-reviewed Factory Pack | Their signal; `outputs/pvp/` teardown; live Studio refine ("show, don't tell", deck slide 4) | Pitching in the first message; backer anger; "faster", "cheaper" |
| **Factory** (supply side, W4) | `personas/factory-owner.md` | A clean, quotable RFQ: the Factory Pack in EN + CN, fewer back-and-forth rounds | A sample Factory Pack; RFQ-to-quote time once measured | Cold RFQ blasts; presenting fictional volumes as real demand |
| **Partner** (intermediary who already has trust) | `personas/ecosystem-partner.md` | Value first: anonymised findings on why launches slip; a pack their client can use | Campaign 01 synthesis (W6 report, deck slide 9) | Asking for intros before giving anything |

## What we say (after a call, never in cold outreach)
- "One landed price, committed." (tier 2, Hypothesis until a real quote exists)
- "If the lot fails QC, it's on us." (Hypothesis: not underwritten yet)
- "We translate your product for the factory: DFM, components, certification."

## Guardrails: what we do not say
| Don't say | Why |
|---|---|
| "Cheaper" | Sourcing is already cheap: Accio $19.90-199 a month, agents 5-10% (`CLAUDE.md`). A guarantee costs money. |
| "Faster" | Most documented delays are engineering, components or certification (`CLAUDE.md`). No delivery data yet. |
| "AI designs your product" | Text-to-CAD is crowded: RapidDirect, Adam, Zoo (`02_RECHERCHE/parallel/B_concurrence.md` §3). Design is not where launches slip. |
| "Our factories" / "our customers" | Factories are fictional demo data; there are no customers (`context/profile.md`). |
| Hexa or the project name in outreach | Repo rule (`03_DISCOVERY/messages.md`). |
