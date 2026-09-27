# Landing page copy — for Orphéo's Framer page

## Framer build checklist
1. **Sections, in this order:** Hero → Built on real data → How it works → Change one thing → CAD is code → Two ways in → The problem → What Make it fills in → Every number carries a label → Build it the right way → Any agent can ask for a quote → Next: a real factory network → Closing CTA → Footer.
2. **Components:** `gtm/framer/SourceGrid.tsx` = "Built on real data" strip under the hero (6 cells, text below). `gtm/framer/DiffBeam.tsx` = "Change one thing", beside the table (Center `v2`, Caption and chips below). Set both in the right panel; do not edit the .tsx.
3. **Meta title:** `PhysicalLovableX — Describe it. See it. Refine it. Make it.`
4. **Meta description:** `Describe a hardware product in one sentence. See it in 3D with its cost, refine it by asking, export a Launch Dossier. Demo: factories are fictional.`
5. **Search:** noindex on (Site settings → SEO). Free `*.framer.website` domain. Delete the "Made in Framer" badge only if the plan allows.
6. **Favicon:** the neutral app icon `mvp/web/src/app/icon.svg` (export to PNG 32/180 px). Never the Hexa mark. No Hexa logo or name anywhere on the page.
7. **OG image:** `deck/screens/hero_*.png` when it exists (folder not created yet); until then `mvp/docs/screens/v2/studio_03_v1.png`, 1200 × 630 crop.
8. **CTA links:** every "Start a product" → `https://physicallovablex.vercel.app/?mode=idea`; "I have a prototype" → `https://physicallovablex.vercel.app/?mode=prototype`. Both params are read by the app (`StartProject.tsx`) and survive the password page. Open in the same tab.
9. **Mobile check (390 px):** H1 on 2-3 lines, tables stack or scroll inside their block, SourceGrid set to 2 columns × 3 rows, DiffBeam keeps ≥ 340 px width or swap for its static fallback `v2/w15c_studio_cad_code_diff.png`; no horizontal page scroll.
10. **Before publishing:** click every CTA once, confirm the footer line and every "Fictional — demo data" mention are visible, search the page for "Hexa" (0 hits).

---

**Product name is a working name** (`{PRODUCT}` = PhysicalLovableX). Tone (see `mvp/docs/BRAND.md`): precise, calm, engineering. Plain sentences, specific numbers, no superlatives, no "revolutionary". Do not add: logo walls, testimonials, pricing, "Backed by" pills, social-proof counters.
Body copy can be trimmed to fit; do not add claims. Sources in `[ ]` render as small footnote links. Every claim below is measured or sourced (PRODUIT.md, PRD.md §8-§10 and §16, PLAN.md §8, `mvp/docs/HONESTY_AUDIT.md`, `mvp/docs/DEMO_SCRIPT.md`). File paths in backticks are for Orphéo only: never print them on the page.

**Primary CTA (all buttons that start the product):** **Start a product** → `https://physicallovablex.vercel.app/?mode=idea`

---

## Hero
**H1:** Describe it. See it. Refine it. Make it.
**Subhead:** Say what you want to build in one sentence. In about 20 seconds you see the product in 3D, its unit cost, and a shortlist of demo factories. Then change it by asking: "thinner", "make it pink", "target $149". When it is right, Make it fills in the rest and assembles a Launch Dossier.
**CTA:** **Start a product**
**Secondary text link:** *I have a prototype* → `https://physicallovablex.vercel.app/?mode=prototype`
**Under the CTA (small):** A working demo. The factories and their quotes are fictional — demo data. Every number shows its source or its assumption.

## Built on real data (SourceGrid strip)
**Eyebrow:** Built on real data
Six cells, text only, no logos (not an endorsement). Pill on the detail face: **Sourced**. Name · tag · detail:

| Name | Tag | Detail |
|---|---|---|
| LCSC | Parts | 29,976 in-stock parts, priced. Snapshot 26 Sep 2026. |
| USITC HTS | Duties | US tariff lines and duty rates, by product code. |
| CBP rulings | Classification | 8 of 10 test products matched to an official ruling. |
| Drewry WCI | Freight | Sea-freight index for the shipping lane. 24 Sep 2026. |
| EU PVGIS | Energy | Solar yield per roof and per site, from the EU JRC. |
| eCFR | Standards | FCC Part 15 rules, quoted with section and link. |

[`mvp/api/costs/data/SNAPSHOT.md` · PLAN.md §8 pass 2-3 · `mvp/api/costs/data/freight_wci.json` · PRD.md §8.4 · `mvp/api/agents/certification.py`]

## How it works — four steps
Heading: **A conversation with your product.**

1. **Describe it.** "A Whoop competitor, screenless, 5-day battery." One sentence is enough.
2. **See it.** The product in 3D, its unit cost at 500, 2,000 and 10,000 units, and a shortlist of three demo factories, on one screen. 18 to 24 seconds in our live runs.
3. **Refine it.** Ask for a change in plain words. A colour or feature change takes 4 to 7 seconds; when the AI has to edit the geometry, 11 to 24 seconds. Each one makes a new version and shows what moved: the CAD, the parts list, the cost, the manufacturing checks, the certifications, the factory shortlist. Go back to any version.
4. **Make it.** One click fills in the rest: quotes and negotiation with the demo factories, tooling, quality control, shipping and duties, cash plan, brand. 54 to 88 seconds in our live runs. You get a Launch Dossier in English, with a machine-translated Chinese version to be reviewed by a native speaker.

## What changes when you type a sentence
Heading: **Change one thing. See everything that follows.**
One worked example, the Whoop scenario, from recorded live runs.

**DiffBeam settings:** Center `v2` · Caption `“Add SpO2 and skin-temperature sensing”` · left chips `CAD`, `BOM`, `Cost` · right chips `DFM`, `Certs`, `Factories` (the six things a version can change: CAD, parts list, cost, manufacturing checks, certifications, factory shortlist).

| You type | The version shows |
|---|---|
| "Add SpO2 and skin-temperature sensing." | New sensor parts in the parts list, each at its LCSC price on the snapshot date. The unit cost moves with them, and the certification map is checked again. |
| "Make it pink." | A new finish, with its concept render a few seconds later. Colour only, so the cost stays the same. |
| "Thinner, 8 mm pod." | The AI edits its own CAD code. The pod is measured again on the new model (8.0 mm in one run), and the checks run again. |
| "Target retail $149." | Margin and break-even recomputed against the new price. |

*Line under the table:* Every version is saved. Restoring one took 1.8 seconds in our run; run Make it again on the restored version.

## In hardware, CAD is code
Heading: **In software the AI writes code. In hardware, CAD is code.**
Body: The AI writes the CAD program for your product, runs it in a sandbox, measures the result and fixes its own errors, the way a coding agent fixes a compile error. You can read the code in the "CAD code" tab. Then the manufacturing checks run on the measured model, for example draft angles and undercuts, and concept-level physics checks such as tip-over angle, battery life from the power budget, or solar yield from official PVGIS data.
Numbers: In 7 of 7 live test prompts the AI produced a recognisable product (surfboard, changing table, home robot, stick vacuum, irrigation kit, rooftop solar, and an edit of the vacuum from v1 to v2). One needed a self-repair. Each generation took 28 to 34 seconds.
**What this is, and is not.** Concept-level geometry, to reason about dimensions, fit, mass and cost. It is not production-tooled CAD. Most of the translation from idea to a package a factory can quote is automated; people and real factories handle the rest. A working prototype takes weeks, not minutes.

## Two ways in
Heading: **Start from an idea, or from a prototype.**
| | |
|---|---|
| **I have an idea** | One sentence. You get a first product in 3D with its cost, then refine it by asking. → **Start a product** (`?mode=idea`) |
| **I have a prototype** | Describe what you built and paste its parts list (BOM). The same pipeline checks components, certifications, cost and what will slow your first production run. → **I have a prototype** (`?mode=prototype`) |

## The problem — 3 sourced facts
**Heading:** Most launches slip between "the prototype works" and "the factory ships good units."

1. **More than 75% of Kickstarter projects deliver late, and about 9% never deliver.** [Mollick, SSRN 2014 / 2015: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2088298 · https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2699251]
2. **In 30 late campaigns we coded by hand, 18 of 24 documented causes were engineering or redesign, components or certification, not factory access.** Small, hand-picked sample, not a statistic. [Footnote text on the page: "Our desk research, September 2026." Source for Orphéo: PRD.md §2, row 3.]
3. **"As a newcomer to the industry, we didn't speak [the manufacturer's] language."** Halliday's COO, on the first smart glasses. [Engadget, 21/07/2026: https://www.engadget.com/2216393/halliday-g2-smart-glasses/]

*Line under the facts:* Design tools and sourcing tools already exist. The gap is the translation between them. That is what a Factory Pack is for: a spec package built so a factory can quote it without back-and-forth.

## What "Make it" fills in
Heading: **From a design to a launch plan, in four phases.**
| Phase | What you get |
|---|---|
| **Design** | Brief, three design directions, CAD (STEP included) and an editable spec. |
| **Make it manufacturable** | Manufacturing checks measured on your CAD, a parts list with real component prices, certifications by market, unit cost and cash needed, how each part is made. |
| **Source** | A ranked shortlist and quotes requested through the production MCP (below). In the demo the factories and their quotes are fictional; an agent compares them and negotiates, and you can review every step. |
| **Launch** | Tooling and sample milestones, an inspection plan, shipping with duties by product code, your cash curve, and a brand: name, packaging, landing copy, listing drafts. |
*Closing line:* **Export it all as one Launch Dossier (PDF).** Prefer the detail? All 13 stages are there to open and edit.
*Small print:* "Make it" approves some decisions for you (for example the recommended quote). They are flagged "Auto-approved", and you can reopen any of them.

## You will always know what is real
Heading: **Every number carries a label.**
| Label | What it means |
|---|---|
| **Measured** | Computed on your CAD model, for example draft angles, undercuts, a pod thickness. |
| **Sourced** | A real price or official rate, with its date. Example: an electronics part at its LCSC price on the snapshot date. |
| **Estimate** | An assumption we show you, and you can change. Example: mechanical parts, assembly, tooling. |
| **Fictional — demo data** | Invented for this demo and labeled as such: the factories, their quotes and replies, carrier freight quotes. |
*Line:* Each number shows its label and, next to it, its source or its assumption.

**Real in the demo:** design, AI-written CAD and its measurements, measured manufacturing checks, physics checks, solar yield from PVGIS, certification map, component prices and stock (dated snapshot), duty lines from US customs rulings (a customs broker confirms the classification), the Drewry sea-freight index, cost engine, production plan, brand kit.
**Fictional — demo data:** the 15 partners (11 factories, 1 integrator, 3 installers), their capacity, quotes and negotiation replies, their past performance, carrier freight quotes and transit days. **Not final:** firmware skeletons are generated and not compiled or tested; auto-approved decisions stand in for a human.

## Build it the right way
Heading: **Each product gets the honest way to be built.**
Body: Furniture, boards, lamps and trackers can be designed in full. A drone, an irrigation kit or a wearable is assembled from existing modules. A smartphone, a camera or a home robot is customised from an ODM platform. The build strategy is chosen automatically, with the industrial path that goes with it. Rooftop solar goes to installers (fictional) instead of factories.
Sub-line: **Browse 11 recorded examples**, from a kitesurf wearable to a follow-me drone. 7 of them run all the way to the Launch Dossier; all open instantly.

## Any agent can ask for a quote
Heading: **Any agent can ask for a quote.**
Body: The factory network sits behind a production MCP: seven tools, served over HTTP, in the same store as the factory portal. An agent (Claude Code, Claude Desktop, a ChatGPT connector, your own script) can search capacity, read a factory profile, request a quote for 500, 2,000 and 10,000 units, send a counter-offer, and register a new factory. Access needs a token from us.
Proof line: In a scripted test, a factory agent registered "Tidewater Wearables (fictional)". It appeared in the factory portal and ranked first (96/100) for "LSR silicone + PCBA, 2,000 units"; a buyer agent then requested its quote.
Honesty line: **Fictional — demo data.** Every factory and quote on the network is invented. Accepting a quote returns an order draft, not a purchase order.
Links: *Read the tool reference* → `https://physicallovablex.vercel.app/docs/production-mcp` · *For agents* → `https://physicallovablex.vercel.app/agents.md` (both public, no password).

## Next: a real factory network
Heading: **Next: a real factory network.**
Body: Today every factory in this demo is fictional. The plan is to onboard real factories by hand, one at a time, onto the same production MCP: each factory lists its processes, MOQ, certifications, lead times and current load. That capacity data is not public today; onboarding creates it. A human engineer will review every Factory Pack before a real factory sees it.
Sub-line: **Want to be among the first founders or factories?** [Join the list] (⚠️ render as a mailto or a disabled button labelled "Coming after the demo").

## Closing CTA
**Line:** Most of the delay sits between the idea and the factory. Start with a sentence.
**CTA:** **Start a product** → `https://physicallovablex.vercel.app/?mode=idea`
Secondary text link: *I have a prototype* → `https://physicallovablex.vercel.app/?mode=prototype`

## Footer
"Demo built for a case study. PhysicalLovableX is a working name. All factories, quotes and freight quotes are fictional — demo data. No real personal data is stored."

---

## Copy notes for Framer
- Timing claims allowed today (several live runs, say "in our live runs"): first version 18-24 s; colour or feature change 4-7 s; geometry change 11-24 s; Make it 54-88 s; text-to-CAD generation 28-34 s. Full stages 1-7 on 10 prompts: 56-76 s. One-run values must say "in one run": restore 1.8 s, "make it pink" render 16 s, 8.0 mm pod. Never "always", "guaranteed", or "minutes to a factory".
- Never claim: real factories, real or binding quotes, a guaranteed or committed price, production speed, a finished prototype. Do not print internal file names, the jury, or Hexa.
- Hero alt (A/B): *Your idea, translated into a package a factory can quote.*
- Layout: follow `mvp/docs/BRAND.md` (paper background, ink, hairlines, one orange accent for the primary button, labels as tinted pills). Show the Studio as a real screenshot or a short screen recording (`mvp/docs/screens/motion/studio_whoop.webm`, poster `v2/studio_03_v1.png`), not an illustration.
- The app behind the CTA asks for a password (APP_PASSWORD) and its top bar and login card carry the Hexa lockup: see open questions in the session report before publishing.
