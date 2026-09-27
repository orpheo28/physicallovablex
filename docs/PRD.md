# PRD — PhysicalLovableX

| | |
|---|---|
| Status | v1.2 — locked for the case study (26/09/2026) |
| Market | US-first founders (FCC first), Chinese factories; EU (CE/UKCA) supported in the certification map |
| Owner | Orphéo |
| Companion docs | `PRODUIT.md` (one-page definition), `PLAN.md` (build and delivery plan), `gtm-harness/context/*` (ICP, positioning, signals) |
| Evidence base | `../02_RECHERCHE/parallel/00_SYNTHESE.md`, `D_unit_economics.md`, `E_usines.md`, `B_concurrence.md`, `../02_RECHERCHE/lecons_inputs.md` |

---

## 1. TL;DR

PhysicalLovableX turns an idea or a working prototype into a manufactured, shipped, ready-to-sell product.

**The experience is a Studio:** describe a product in a sentence, see it in 3D with its cost and top factories, refine it by prompting ("measure heart rate", "make it pink", "thinner, 8 mm pod", "target $149"), then press **Make it** to autofill the rest of the pipeline up to a Launch Dossier (EN + CN). Every prompt creates a restorable version with visible diffs (§8.2). The 13 stages (§8) are the detailed view of the same project.

- **Top layer ("Lovable"):** plain language in → industrial design, CAD, technical spec, investment needed, where and how to produce.
- **Bottom layer ("Alibaba"):** the spec is matched to a curated network of Chinese factories that expose their capacity through a **production MCP**.
- **Our infra:** DFM, factory selection and negotiation, tooling, QC, logistics, financing.

**Positioning:** in software the AI writes code; in hardware, **CAD is code**. The AI writes build123d code, it runs in a sandbox, is measured, and is self-repaired on error. **Honest scope:** concept-level geometry; about 80% of the translation is automated; humans and real factories cover the last 20% (tier 2). A working prototype takes weeks, not minutes.

**The bet (thesis v2):** the bottleneck in hardware is neither design nor the factory. It is the **translation** between the two: making the product manufacturable, choosing components, passing certification, and speaking the factory's language.

**The primitive is the Factory Pack:** a spec package a factory can quote and build without back-and-forth. Every later layer consumes it.

---

## 2. Problem and evidence

| # | Evidence | Source |
|---|---|---|
| 1 | More than 75% of Kickstarter projects deliver late; ~9% never deliver | Mollick, SSRN (2014, 2015) — `00_SYNTHESE.md` facts 1-2 |
| 2 | Hardware demand is growing: Kickstarter Design & Tech pledges +64% in 2025; the most funded campaign ever is hardware (eufyMake E1, ~$47M) | Kickstarter PBC Report 2025 — facts 3-4 |
| 3 | In 30 hand-coded late campaigns, **18 of 24 documented causes** are engineering/redesign, components or certification — not factory access | `gtm-harness/CLAUDE.md` (small, non-random sample) |
| 4 | "We didn't speak [the manufacturer's] language" — Halliday COO | Engadget, 21/07/2026 |
| 5 | US duty now depends on the HTS line: IEEPA duties not collected since 24/02/2026, Section 301 remains, de minimis suspended | CBP, Federal Register — `D_unit_economics.md` |
| 6 | Factory capacity is not digitised: no public machine-capacity API found; what is digitised is discovery and RFQ | `E_usines.md` |
| 7 | Designers are disconnected from manufacturing; DFM is the biggest gap (Diode, Davide Asnaghi) | a16z podcast — `lecons_inputs.md` |

**What the market sells today:** sourcing and matching (Accio $19.90-199/month, agents 5-10%, No Logo 25% flat, Cavela, Haizol), text-to-CAD (Zoo, Backflip, Atech), QC ($268/man-day). **Nobody owns the translation and nobody publishes delivery or defect data** (`B_concurrence.md`).

### 2.1 Market anchors (verified) and sizing logic

| Anchor | Figure | Source |
|---|---|---|
| Kickstarter, all categories, 2025 | 20,374 funded projects, $891.8M pledged; Design & Tech pledges +64% vs 2024 | Kickstarter PBC Report 2025 |
| Kickstarter Technology + Design, Q1 2026 | 314 funded campaigns, $67.23M | TCF Q1 2026 (third-party, medium) |
| US imports of goods from China, 2025 | $308.4B | BEA, 19/02/2026 |
| Sourcing agent fee benchmark | 5-10% of order value | Dragon Sourcing |

**Sizing logic (to validate, not a claim):** revenue pool = hardware launches per year × average production order × take rate. Crowdfunding is only the **visible, datable** entry point (public ship dates make the pain measurable); the larger pool is DTC and Amazon brands importing physical products from China. No verified size exists for China sourcing agents (`C_marche.md`, "Manques").

---

## 3. Thesis and what would kill it

**Thesis v2:** founders lose months and margin between "the prototype works" and "the factory ships good units", because nobody translates the product into manufacturable, certifiable, quotable form.

**Kill criteria (tested by discovery, see §3.1 and §20):**
- Founders say the delay was tolerable and they would not pay to remove it (vitamin, not painkiller) — `00_SYNTHESE.md` §2.1.
- Founders say the blocker was cash or demand, not translation.
- Founders already have a trusted "contact in Shenzhen" who does the translation well.

### 3.1 Riskiest assumptions — test, metric, decision

| # | Assumption | Test | Metric | Decision rule |
|---|---|---|---|---|
| A1 | The blocker is translation (DFM, components, certification, factory language), not factory access | 30 discovery messages → calls | Share of founders naming a translation-type blocker first | Majority → keep thesis v2; minority → reposition on the blocker they name |
| A2 | It is a painkiller: founders pay to remove it | Ask what they paid third parties and what they would pay for a committed landed price | Named spend + willingness to pay | No spend and no willingness → drop tier 2 pricing, keep tier 1 as data play |
| A3 | Founders will hand over a real product | Offer a free human-reviewed Factory Pack to call participants | Packs accepted | < 3 accepted in lighthouse → rethink wedge |
| A4 | Factories will share capacity through the MCP | Onboard 3 factories manually in lighthouse | Capacity profiles completed; RFQ-to-quote time | Refusal → RFQ-only flow, capacity inferred from quotes |

---

## 4. Users

### 4.1 Primary — Segment A: funded hardware creator (user = buyer = founder)
- Small team, first or second product, no own factory, money already pledged, public ship date.
- Examples from our list: The Minimal Phone, Pilet, Wordrunner, AIVELA, SwiftShape, Circular Ring 2, GAMR (`03_DISCOVERY/comptes.csv`).
- **Job to be done:** "Get my working prototype produced at the promised price and quality, on a date I can tell my backers."

### 4.2 Secondary — Segment B: DTC brand adding a physical product
- Weaker hypothesis: no documented production problem in our 4 DTC accounts (`icp.md`).

**Early Customer Profile vs ICP (27/09):** the early customer is 4.1 narrowed to late crowdfunded consumer-electronics founders (beachhead scoring 26/30, access ×2; `icp.md` "Beachhead scoring", deck A8, my scoring = hypothesis); the later ICP is funded hardware startups (prototype, no campaign) and 4.2 brands, once one case is documented end to end.

### 4.3 Top of funnel — idea-stage creator
- Plain-language idea, no prototype. Served free (land grab), feeds data and future Segment A.

### 4.4 Supply side — factory
- SME factory in China selling through agents, trading companies, 1688, Canton Fair (`E_usines.md`).
- **Job to be done:** "Receive qualified, complete RFQs that I can quote fast, and fill idle capacity."

**Not a target:** established manufacturers with their own chain (Anker/eufyMake, Creality, AYANEO) — high urgency, low fit.

---

## 5. Goals and non-goals

### Goals — demo (this week)
- G1. A reviewer types any product idea and reaches an exportable Factory Pack in under 5 minutes.
- G2. The full concept is visible end to end: 13 stages, from brief to brand, with a founder view and a factory view.
- G3. Every number shows its assumption; every simulated element is labeled.
- G4. The demo never crashes in front of the jury.

### Goals — business (after the case, for Hexa)
- G5. Prove founders will hand over a real product for production (lighthouse, tier 2).
- G6. Publish the first on-time and defect rate in the category.

### Non-goals
- Photorealistic rendering or advanced CAD (commodity).
- A real marketplace, payments, real logistics booking.
- Automating the last 10%: humans review every Factory Pack before it reaches a real factory.
- Paid acquisition (see `lecons_inputs.md`, Lovable).

---

## 6. Success metrics

| Level | Metric | Target |
|---|---|---|
| Demo | Time from prompt to wow screen and Factory Pack (auto-run mode) | < 5 min live, < 30 s cached |
| Demo | Test prompts completed without crash (see Appendix A) | 10/10 |
| Activation | **Factory Pack exported** (the "wow moment") | North-star input |
| Quality | Factory Packs signed off by a human engineer before reaching a real factory | 100% (tier 2) |
| Conversion | Factory Pack → RFQ sent to real factories (tier 2) | Tracked from lighthouse |
| North star | **Units delivered on time and within spec** | Published publicly from run 1 |
| Trust | On-time rate, defect rate, rejected lots | Published per run |
| Supply | Factories with capacity registered in the MCP; RFQ-to-quote time | Tracked from lighthouse |

No LTV targets: meaningless at this stage (Elena Verna, `lecons_inputs.md`).

---

## 7. Product principles

1. **Translation over generation.** Design is the input; the value is what makes it manufacturable.
2. **Show the assumption.** No number without its source or hypothesis, one click away.
3. **Label the fiction.** "Fictional — demo data" and "Estimate" are visible, never hidden.
4. **Humans on the last 10%.** AI drafts; an engineer signs before a real factory sees it.
5. **One artifact, many consumers.** Every stage reads from and writes to the project; the Factory Pack is the spine.
6. **Wow first.** The first screen after the prompt must show the product, its cost and a factory shortlist.

---

## 8. Scope — the Studio and the 13 stages

The product has one project and two ways to see it. The **Studio** (§8.2) is the primary interface: prompt, see, refine, Make it. The **13 stages** below are the detailed view of the same project: every Studio action reads and writes the same stage artifacts. Stages are grouped in four phases, as in the UI: **Design** (Brief · Design options · 3D model & spec) · **Make it manufacturable** (Manufacturability check · Costs & investment · Production plan) · **Source** (Factory shortlist · Quotes & negotiation) · **Launch** (Tooling & samples · Quality control · Shipping & duties · Cash plan · Brand & listing).

### 8.0 The 13 stages (detailed view)
Each stage: reads the project state, writes one artifact, has a cached fallback, and shows a status (not started / draft / validated).

| # | Stage | Input | Output (artifact) | Key requirements | Acceptance criteria | Demo |
|---|---|---|---|---|---|---|
| 1 | **Brief** | Prompt, or prototype description + pasted BOM | `brief.json` | Two modes; ≤5 clarifying questions (markets, volume, target price, battery, wireless) | Both modes produce a valid brief; questions skippable | Real |
| 2 | **Industrial design** | Brief | 3 design directions | Parametric variants (dimensions, shape, material); user picks one | 3 distinct directions rendered; choice persisted | Real |
| 3 | **CAD + spec** | Chosen direction | `spec.json`, STEP, STL | build123d enclosure; GLB viewer (`<model-viewer>`, fallback three.js); dimensions, materials, electronics block diagram | STEP downloads and opens; viewer rotates; spec editable | Real |
| 4 | **DFM** | Spec + BOM + CAD | `dfm.json` | **Measured** geometry checks on the CAD (draft angles, undercuts, projection along pull direction — adapted from the text-to-cad DFM skill) + AI-reviewed alerts (wall thickness, tolerances, assembly); risky components (EOL, single source, lead time, stock) with alternatives; certifications by market (CE, FCC, UKCA, battery transport) | ≥3 relevant alerts per test case; every alert has a fix and a cited rule; each alert labeled **"Measured"** or **"AI-reviewed"** | Real |
| 5 | **Investment** | Spec + BOM + DFM | `costs.json` | Electronic BOM lines matched to **real LCSC/JLCPCB parts** (price + stock, snapshot date); mechanical parts and assembly estimated; unit cost at 500 / 2,000 / 10,000; tooling; certification cost; total cash needed; margin at target price; break-even units | Formulas in §11; each line labeled **"LCSC price, <date>"** or **"Estimate"** with its assumption | Real (partly sourced) |
| 6 | **Production plan** | Spec + costs | `production_plan.json` | Process per part (injection, CNC, sheet metal, PCBA), region, lead times | One process per part with reason | Real |
| 7 | **Factory matching** | Factory Pack | Ranked shortlist | Query production MCP; score on process fit, MOQ, certifications, load, lead time | Top 3 with explicit reasons | Simulated network |
| 8 | **RFQ + negotiation** | Factory Pack + shortlist | Quotes, transcript, selected factory | Agent sends RFQ via MCP; 3 factory agents reply; negotiation agent compares and counters (price, MOQ, lead time, payment terms); user approves | Transcript visible; final terms stored | Simulated |
| 9 | **Tooling + samples** | Selected quote | Milestone plan | T0 / T1 / golden sample, dates, 30/70 payment schedule | Timeline rendered; dates consistent with lead times | Generated plan |
| 10 | **QC** | Spec + DFM | Inspection plan | AQL level, critical/major/minor defects derived from spec, pre-shipment inspection cost ($268/man-day benchmark) | Every critical defect maps to a spec line | Generated plan |
| 11 | **Logistics** | Costs + quote | Final landed cost | Incoterm, sea vs air, duties by assumed HTS (Section 301 note), broker/port, warehouse | Landed cost reconciles with stage 5 | Simulated rates |
| 12 | **Financing** | Milestones + costs | Cash curve | Cash out per milestone; options: preorders, crowdfunding, inventory financing | Curve sums to total cash of stage 5 | Generated plan |
| 13 | **Brand + distribution** | Brief + spec | Brand kit | Name options, packaging spec, landing copy, Shopify/Amazon listing draft | All four present | Real |

**Final export: Launch Dossier (PDF)** — Factory Pack (EN + CN) + outputs of all stages + assumption register.

### 8.1 The Factory Pack (primitive) — required contents
1. Product summary and target markets
2. Structured spec (dimensions, materials, finishes, tolerances)
3. CAD (STEP) and drawings
4. BOM with component risk and alternatives
5. DFM alerts and resolutions
6. Certification checklist by market
7. Target quantities and cost estimate
8. Questions for the factory (EN + CN; CN is machine-translated and labeled "to be reviewed by a native speaker")
9. Assumption register

---

### 8.2 Studio: prompt-to-product loop

**Principle:** the founder never fills a form to get a first product, and never re-runs a pipeline by hand to change one. They talk to the product; the pipeline re-computes.

| Step | What the user does | What the system does | Stages touched | Status |
|---|---|---|---|---|
| Describe | Types one sentence (idea mode) or pastes a BOM (prototype mode) | Brief, first design direction, CAD, DFM, costs, production plan, factory shortlist; shown as 3D + unit cost at 3 volumes + top-3 factories | 1-7 | Real (shortlist fictional) |
| Refine | Types a change: add a sensor, change a colour, change a dimension, change a target price | Interprets the prompt as a spec change, creates a **new version**, re-runs only what the change invalidates, shows the diff | 3-7 as needed | Real (target: see below) |
| Restore | Clicks an earlier version | That version becomes current; later versions stay in the timeline. Stages 8-13 and the Factory Pack are cleared and **Make it must run again** | all | Real |
| Make it | One click | Autofills stages 8-13: RFQ through the production MCP, agent negotiation (auto-approval flagged), tooling, QC, logistics and duties, cash plan, brand; assembles the Factory Pack and the Launch Dossier | 8-13 | Simulated (factories, quotes, freight) + generated plans + real brand kit |

**A version** = a full snapshot of the project (spec, CAD, BOM, costs, DFM, certifications, shortlist) plus the prompt that created it. Restoring never deletes later versions, but it clears stages 8-13 and the Factory Pack (they belong to the version they were built from), so Make it runs again after a restore or a refine.

**The diff** shown after each prompt lists what changed, each with its label:
- **CAD** rebuilt (dimensions and features, **Measured** on the new model);
- **BOM** lines added, removed or swapped, electronic lines with the real LCSC part number, price and stock (**Sourced**, snapshot date);
- **Costs**: unit cost at 500 / 2,000 / 10,000, cash needed, margin at the target price (delta vs the previous version);
- **DFM**: alerts opened or closed, re-measured on the new CAD (**Measured** / AI-reviewed);
- **Certifications**: rows added or removed in the certification map by market;
- **Factory shortlist**: reordered or changed factories and why (**Fictional — demo data**).
A prompt that changes nothing in a category says so ("no change"); the diff is never padded.

**Make it and auto-approval.** Autofill takes the decisions a human would take with sensible defaults, notably approving the negotiation agent's recommended quote. On screen (stage 8) the approval reads **"Auto-approved (autofill mode)"** with a **"Change factory"** action. The Launch Dossier carries the assumption `a8_autofill`: "Auto-approved in autofill mode — review and change the selected factory before any real order". The user can reopen any stage and change it.

**Performance (measured).** Ranges are from several live runs through the UI; single values are marked "one run".
| Item | Value | Status |
|---|---|---|
| First version (v1), live | 18-24 s (AI-written CAD ≈ 23 s in the background) | **Measured**, several runs |
| Stages 1-7, live AI, 10 PRD prompts | 56-76 s (≈ 1 min) | **Measured** (`tests/results/20260926-203730.md`) |
| Colour or feature refine | 4-7 s (≈ $0.01 each in one run) | **Measured**, several runs |
| Geometry refine (the AI edits its CAD program) | 11-24 s | **Measured**, several runs |
| "Make it pink" concept render | arrived 16 s after the refine | **Measured**, one run |
| Restore a version | 1.8 s | **Measured**, one run |
| Make it: 13 steps to the Launch Dossier, live | 54-88 s (≈ $0.34 in one run) | **Measured**, several runs |
| Text-to-CAD generation | ≈ 28-34 s | **Measured**, 7 live prompts |
| Cached example, opening a stage | ≈ 1-2 s | **Measured** (QA report) |
| Make it on a recorded showcase (7 of 11 are 13/13) | instant, $0 | **Built** (W21) |

**Fallbacks.** Every Studio step keeps the platform rule (§12): schema validation, one retry, then the cached fixture with a visible "Cached example" banner. If a refine prompt cannot be applied, a version card with status **failed** and a plain-language error appears in the timeline, and the previous version stays current ("vN is still the current product"). Live AI down: the cached desk-lamp example (complete, stages 1-13) and the factory portal remain fully usable.

**Not in scope:** free-form CAD editing beyond parametric changes; changes that need a new mechanism or a different product category (the Studio says so and suggests a new project); multi-user editing.

### 8.3 Text-to-CAD: the AI writes the CAD

CAD is code (build123d). Instead of picking a template, the AI **writes the CAD program** for the product, which is executed in a sandbox and then measured on the resulting solid. On an execution or geometry error, the error is fed back and the AI repairs its code (like a coding agent on a compile error). The code is shown in a "CAD code" tab. Parametric families (board, furniture, stick_vacuum, home_robot, irrigation, solar_array, wearable_band, ring) are used as seeds and as fallbacks when generation fails.

| Item | Result | Status |
|---|---|---|
| Live prompts producing a recognisable product | 7/7 (surfboard, changing table, home robot, stick vacuum, irrigation kit, rooftop solar, vacuum edit v1→v2) | **Measured** |
| Self-repairs needed | 1 in 7 | **Measured** |
| Time per generation | ≈ 28-34 s | **Measured** |
Scope: **concept-level geometry** to reason about dimensions, fit, mass and cost. It is not production-tooled CAD; a human engineer reviews before a real factory sees it (§7, principle 4).

### 8.4 Engineering layer

- **Category packs:** 10 packs, each with the applicable standards and verified citations (used by the certification map and by DFM).
- **Physics checks on the measured CAD**, each returning pass / warn / fail with its inputs: tip-over angle, board volume in litres and buoyancy, battery life from the power budget, vacuum air watts, irrigation pressure, and solar yield from PVGIS (**Sourced**; e.g. Biarritz, 35 m² → 5.59 kWp, 6,860 kWh/yr).
- **Electronics architecture and power budget** per product.
- **Firmware skeleton** (Zephyr BLE or Arduino Wi-Fi), generated and labeled **"not compiled or tested"**.
- **Prototype path:** parts, cost and time to a first prototype (e.g. kitesurf wearable: $317, 4 weeks).
- **Non-factory supply:** rooftop solar routes to certified installers (**Fictional — demo data**) instead of factories.

### 8.5 Build strategy and showcase (built, W21)

- **Build strategy auto-selected** per product, with the honest industrial path: **full design** (furniture, board, lamp, tracker), **module assembly** (drone, irrigation, wearable, hair dryer, vacuum), **ODM customisation** (smartphone, camera, home robot). New categories: drone, hair dryer, camera, smartphone.
- **Showcase gallery:** 11 recorded examples opening instantly at no AI cost. Complete through Make it (13/13): whoop_kitesurf, changing_table, stick_vacuum, irrigation_biarritz, solar_biarritz, surfboard_beginner, drone_follow. Start-only: home_robot, hair_dryer, instant_camera, minimal_phone.
- **Drone checks:** thrust-to-weight, hover time, and EU class C0/C1/C2 (**Sourced** from EUR-Lex).


## 9. Two views

- **Founder app:** project dashboard, stage sidebar (13), timeline from brief to delivered, status per stage, "Export Launch Dossier".
- **Factory portal:** a fictional factory logs in, sees its capacity profile (processes, MOQ, certifications, lead times, current load), and the RFQs received. This makes the two-sided "Alibaba layer" visible.

---

## 10. Production MCP — specification

Local MCP server. All data fictional in the demo.

| Tool | Caller | Input | Output |
|---|---|---|---|
| `register_capacity` | Factory | processes[], materials[], moq, certifications[], lead_time_days, monthly_capacity, current_load_pct | factory_id |
| `search_capacity` | Platform | process, material, quantity, certifications_required[], deadline | ranked factories + reasons |
| `get_factory_profile` | Platform | factory_id | profile, audit notes, past performance (fictional) |
| `request_quote` | Platform | factory_id, factory_pack_id, quantities[] | rfq_id |
| `submit_quote` | Factory agent | rfq_id, unit_price per tier, tooling, moq, lead_time, payment_terms, exceptions[] | quote_id |
| `counter_offer` | Platform agent | quote_id, proposed changes, rationale | new quote version |
| `accept_quote` | Platform (after user approval) | quote_id | order draft |

**Transport (built):** the same 7 tools are served over HTTP at `/mcp` on the API (Streamable HTTP, JSON), in the same process and store as the web portal, with Bearer-token auth (`MCP_TOKEN`). Any MCP client (Claude Code, Claude Desktop through `mcp-remote`, a ChatGPT connector, a script) can use it; setup in `mvp/docs/MCP_DEMO.md`. Scripted proof: a factory agent registers "Tidewater Wearables (fictional)", which then appears in the web portal and ranks #1 (96/100) for "LSR silicone + PCBA, 2,000 units"; a buyer agent then requests a quote for 500 / 2,000 / 10,000. All factories stay fictional.

**Why MCP:** any agent (ours, Claude, ChatGPT, a buyer's own agent) can query capacity in the same way — "Waniwani for industrial capacity". Research shows capacity data does not exist publicly (`E_usines.md`): the MCP must **create** it through factory onboarding, not aggregate it.

---

## 11. Cost and landed-cost model

**Landed cost per unit** = FOB + freight + insurance + duties (HTS + Section 301 where applicable) + broker/port + 3PL + agent/platform fee + QC + tooling amortisation (`D_unit_economics.md`).

| Parameter | Default assumption | Source |
|---|---|---|
| Simple injection mold (1 cavity) | $1,000-3,000 | Zetar Mold 2026 (vendor, medium) |
| Complex multi-cavity steel mold | $30,000-100,000 | idem |
| Sourcing agent benchmark | 5-10% of order | Dragon Sourcing |
| Pre-shipment inspection | $268 per man-day | V-Trust |
| Section 301 | 7.5% / 25%+ by HTS line — shown as assumption | CBP / White House |
| IEEPA | not collected since 24/02/2026 | CBP CSMS 67834313 |
| De minimis | suspended | Federal Register 24/06/2026 |
| Section 122 | 10% temporary surcharge announced Feb 2026 for 150 days; current status to verify — shown as a toggle | CBP CSMS 67844987 |
| Volume curve | unit cost falls with tier (500 → 2,000 → 10,000); factor exposed as editable assumption | Demo assumption |
| Electronic components | Real unit prices and stock from the JLCPCB/LCSC basic & preferred parts snapshot (daily-updated, MIT); live lookup via jlcsearch where available | [CDFER/jlcpcb-parts-database](https://github.com/CDFER/jlcpcb-parts-database), [jlcsearch](https://github.com/tscircuit/jlcsearch) |
| HTS line (cached examples) | Set by hand from the official USITC HTS and cited; live lookup out of scope | [hts.usitc.gov](https://hts.usitc.gov/) |

Deterministic Python computes the numbers; the LLM only proposes BOM lines and assumptions. Every output lists its assumptions.

---

## 12. AI system

| Agent | Role | Model use |
|---|---|---|
| Spec copilot | Brief → structured spec; clarifying questions | LLM, JSON schema output |
| Design generator | 3 parametric directions → build123d parameters | LLM → deterministic CAD |
| DFM reviewer | Measured geometry checks first, then AI-reviewed alerts, component risks, certifications | Deterministic geometry checks (build123d/OCCT) + LLM with checklist prompt; LLM never overrides a measurement |
| Cost engine | BOM → costs | LLM proposes BOM lines; Python matches electronic lines to the LCSC snapshot and computes all maths |
| Matcher | Scores factories from MCP | Deterministic scoring |
| Negotiation agent | Compares quotes, counters, recommends | LLM with policy (price, MOQ, lead time, terms) |
| Factory agents (×3, fictional) | Reply to RFQs with personalities (cheap/slow, fast/expensive, balanced) | LLM |
| Planner | Tooling, QC, logistics, financing plans | LLM + Python checks |
| Brand agent | Names, packaging, copy, listing | LLM |

All LLM calls: JSON schema validation, retry once, then cached fallback.

---

## 13. Data model (SQLite)

`Project`(id, name, mode, created_at, status) · `Brief` · `DesignOption` · `Spec` · `BOMItem`(part, qty, unit_cost_est, risk, alternative) · `DFMIssue`(severity, description, fix) · `Certification`(market, standard, cost_est, lead_time) · `CostModel`(tier, unit_cost, tooling, landed_cost, assumptions_json) · `Factory`(fictional=true, profile_json) · `RFQ` · `Quote`(version) · `NegotiationTurn` · `Milestone` · `QCPlan` · `LogisticsPlan` · `FinancingPlan` · `BrandKit` · `Artifact`(stage, path, type).

---

## 14. UX — key moments

1. **Landing:** hero ("Describe it. See it. Refine it. Make it."), the four-phase flow, two buttons: "I have an idea" / "I have a prototype".
2. **Describe → first result:** one sentence in; a progress indicator on every step; the **wow screen** appears with the product in 3D, unit cost at 3 volumes and top-3 factories in one view. Stages 2-7 run with sensible defaults (first design direction, default volumes) and remain editable.
3. **Refine by prompting:** a prompt box under the product; a "CAD code" tab shows the AI-written build123d program with line numbers (when the version has one), an "Engineering" tab shows the checks (pass / warn / fail), power budget, standards and prototype path, and a "Firmware" tab offers the generated skeleton as a zip ("not compiled or tested"). After each prompt, a new version appears in the version list and **diff chips** show what changed (CAD, BOM, cost, DFM, certifications, shortlist), with the cost delta. Any version can be restored.
4. **Make it:** one button. Progress shows stages 8-13 as they complete; auto-approved decisions are marked.
5. **Detailed view:** the 13 stages in four phases, for anyone who wants to inspect or override a stage. Includes the negotiation transcript (agent-to-factory messages, side-by-side quotes, the recommendation) and the timeline with the cash curve underneath.
6. **Export:** Launch Dossier PDF (EN + CN).
7. **Showcase gallery:** 11 recorded examples (7 complete through Make it), instant.
8. **Reset demo:** one button restores the two cached projects.

## 15. Non-functional requirements

- **Robustness:** every stage has a cached fallback; no unhandled exception reaches the UI; two fully cached examples (magnetic desk lamp, simple electronic accessory) run offline.
- **Latency:** each live stage < 30 s; progress indicator on every call.
- **Cost guard:** max tokens per request; max requests per session; key only server-side.
- **Security:** `.env` never committed; password-protected deployment via env var; no real personal data.
- **Models:** model-agnostic client (OpenAI-compatible, via OpenRouter) with three routes from env: `LLM_MAIN_MODEL` (reasoning), `LLM_FAST_MODEL` (light steps, factory agents), `LLM_CN_MODEL` (Chinese Factory Pack, a Chinese-native model). Never hard-coded. Product point: the infra routes each task to the best model; production use with real founders' unreleased designs requires an IP/data-residency policy per provider.
- **Honesty:** four labels, used consistently on screen and in the PDF — **Measured** (computed on the CAD), **Sourced** (real price or official rate, with date), **Estimate** (assumption shown), **Fictional — demo data** (factories, quotes, freight). README lists real vs simulated.

---

## 16. Real vs simulated (demo)

| Real (live AI + code) | Simulated (labeled) |
|---|---|
| Brief, design, CAD/STEP/GLB, spec, versions and diffs, **measured DFM checks**, certification map, **real LCSC component prices and stock** (dated snapshot), **HTS line from CBP CROSS rulings** and duty rates with their cited headings, **Drewry WCI** freight index as the base of the sea-freight lane, eCFR citations, cost engine, production plan, brand kit, plans for tooling/QC/financing, the negotiation logic (real agent loop over the MCP tools) | The 15 fictional partners (11 factories, 1 integrator, 3 installers), their capacity, quotes and negotiation replies; carrier freight quotes and transit days; factory past performance; the auto-approval in Make it (a real code path, but the decision stands in for a human) |

Also real: the AI-written CAD code and its measurements, physics checks on the measured CAD, PVGIS solar yield (Sourced). Simulated or labeled: the firmware skeleton is generated and **not compiled or tested**; certified solar installers are fictional. Estimates stay estimates: mechanical parts, assembly, tooling ranges, certification costs and lead times, and the classification precedent itself (confirm with a broker) are labeled **Estimate** on screen.

## 17. Business model and GTM link (hypotheses)

| Tier | Offer | Role in GTM | Price hypothesis |
|---|---|---|---|
| 1 — Self-serve | Idea/prototype → Factory Pack, free | Land grab, data, wow moment | Free (freemium = marketing budget) |
| 2 — Accompanied production | Human-reviewed pack, RFQ, negotiation, samples, QC, committed landed price | Lighthouse: 10 founders with proven demand | Commission on the production order (benchmarks: agents 5-10%, No Logo 25%) |
| 3 — Infra | Financing, logistics, reorders, MCP access for third-party agents | Venture scale | Take rate + financing margin |

Pricing is not optimised at this stage; it is a hypothesis to test in lighthouse conversations (variant to test: pay at validated milestones — factory quote, sample, order). Lighthouse founders are non-paying customers until proof of value; we test willingness to pay (amount already paid to intermediaries, W5 deposit/LOI), we don't optimise price. Go-to-market = 1 ICP + 1 offer + 1 channel (late funded electronics founders + free human-reviewed Factory Pack + signal-based founder outreach); one complete case (prototype → Factory Pack → factory quote) becomes the main sales artifact in W5-W6 before widening.

**Why venture-scale despite low frequency:** a founder launches a product every 12-18 months (unlike Lovable's daily use), but each production run is $20k-200k of order value; retention comes from reorders and new SKUs (`lecons_inputs.md`).

**Entry wedge:** "I have a prototype" mode for Segment A — founders with a working prototype and money pledged.

**One category first (decided 27/09):** consumer electronics (PCB + enclosure: wearables, minimalist phones, small devices). 28 of the 36 drafted discovery accounts are in it (`03_DISCOVERY/envoi/A_ENVOYER.md`; 9 of the top 10 in `icp.md`), and it is where real LCSC parts and FCC / certification checks add most. The Studio stays broad; the lighthouse, the outreach and the first factories come from this one category. Focus choice, not a finding: revisit after campaign 01 (`GTM_Lessons_PhysicalLovableX.md`: Walsh, Holly Chen, Klaviyo fiches).

---

## 18. Roadmap

| Phase | When | What | Exit criteria |
|---|---|---|---|
| 0 — Demo | This week | This PRD, 13-stage demo | Case study delivered |
| 1 — Lighthouse | 90 days | 10 founders in consumer electronics, concierge tier 2, 3 real factories onboarded by hand through ecosystem intermediaries (sourcing agents, QC inspectors, 3PLs, CAD freelancers), not cold RFQ | ≥3 production runs started; first published on-time/defect rates; PMF signal per side: founders start a second design or hand a pack to a factory, factories return a quote from the pack without back-and-forth (target ≤5 working days, hypothesis) |
| 2 — Land grab | 3-9 months | Self-serve tier 1 public; community; makerspace "build a product" weekends | Factory Packs exported per week; pack → RFQ conversion |
| 3 — Infra | 9-24 months | Real production MCP network, financing, logistics; open Factory Pack format | Factories self-register capacity; third-party agents query the MCP |

---

## 19. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Delay is tolerated → vitamin | Discovery kill criteria (§3); target founders with public pressure (refund sites, complaints) |
| Sourcing commoditised (Accio, agents, No Logo) | Compete on translation + committed price + published outcomes, not on price |
| Accio owns the supply side | MCP open to any agent; own the spec layer, not the supplier list |
| Guarantee costs money | Price the guarantee in the commission; start with simple products |
| Factories won't share capacity | Onboard manually in lighthouse, introduced by intermediaries who already hold factory trust (sourcing agents, QC inspectors, 3PLs, CAD freelancers) rather than cold RFQ; RFQ flow creates the data |
| Founder-market fit (the founder has not shipped hardware) | Advisor who has run a production + the engineer who signs every pack |
| Design confidentiality / IP (factories; third-party LLMs) | NDA with every factory before it sees a pack; IP / data-residency policy per LLM provider before production use (§15) |
| One category too narrow | The Studio stays broad (solar, drones, lamps still run); only the lighthouse is focused; revisit after campaign 01 |
| AI errors in DFM/certification | Human engineer signs every pack before a real factory sees it |
| Tariff volatility | HTS-level duty engine, assumptions visible, updated per run |

---

## 20. Open questions for discovery

1. When did you realise delivery would slip, and what blocked first: design, components, certification, or factory?
2. What did you pay third parties (agents, engineers, QC), and would you pay for a committed landed price?
3. What does your daily exchange with the factory look like?
4. What would you do differently first?
5. Do you have a next product, and when?

Results go to `03_DISCOVERY/verbatims.md`; this PRD is updated after every 5 conversations.

---

## Appendix A — Test prompts (all must pass)
1. Magnetic rechargeable desk lamp, minimalist, sold €89 (cached)
2. Bluetooth tracker card for wallets (cached — the "simple electronic accessory")
3. Smart dog bowl that weighs food, Wi-Fi
4. Mechanical keyboard with hot-swap switches, aluminium case
5. Portable espresso maker, manual pump, no electronics
6. Kids' audio player with NFC figurines
7. Smart ring measuring sleep (prototype mode, pasted BOM)
8. E-ink phone, minimalist (prototype mode)
9. Bike light with brake detection
10. Desktop air-quality monitor with CO2 sensor

### Studio scenario (demo and video) — "the Whoop competitor"
Start (idea mode): *"A Whoop competitor: a screenless wrist-worn band, 5-day battery, tracks sleep and strain."*
Then, one prompt at a time, each creating a version:
1. *"Add SpO2 and skin-temperature sensing."* → BOM gains sensor parts with their LCSC numbers, prices and stock (Sourced); cost and DFM re-measured; the certification map changes. (Not "add heart-rate": a Whoop-class band already has it, so the diff would show nothing.)
2. *"Make it pink."* → finish and colour change; cost delta small or nil, and the diff says so; a concept render arrives later.
3. *"Thinner, 8 mm pod."* → the AI edits its CAD program (visible in the "CAD code" tab); measured dimensions and DFM re-measured (8.0 mm in one run); alerts may open.
4. *"Target retail $149."* → margin, break-even and shortlist re-computed against the new price.
5. **Make it** → stages 8-13 autofilled; Launch Dossier exported.
Measured live over several runs: start 18-24 s; colour and feature refines 4-7 s; geometry refines 11-24 s; Make it 54-88 s. One-run values: restore 1.8 s, Make it ≈ $0.34, refine ≈ $0.01, "thinner, 8 mm pod" measured 8.0 mm, pink render 16 s later.
Acceptance: each prompt yields a new version with a diff and can be restored; no crash; every number labeled. Certification and DFM diff lines per prompt are confirmed on the live build before the demo (`mvp/docs/DEMO_SCRIPT.md`).

## Appendix B — Build accelerators (open source)
- [earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad) (MIT) — CAD agent skills, STEP/STL/GLB export, viewer; DFM skill ([PR #391](https://github.com/earthtojake/text-to-cad/pull/391), merged 21/09/2026) → stage 3-4.
- [CDFER/jlcpcb-parts-database](https://github.com/CDFER/jlcpcb-parts-database) (MIT) and [jlcsearch](https://github.com/tscircuit/jlcsearch) (MIT) → stage 5.
- three.js GLTFLoader; fallback [occt-import-js](https://github.com/kovacsv/occt-import-js) → 3D viewer.
- [USITC HTS](https://hts.usitc.gov/) → stage 11.
- Optional: [build123d-mcp](https://github.com/pzfreo/build123d-mcp), [Vercel Next.js FastAPI starter](https://vercel.com/templates/next.js/nextjs-fastapi-starter).
- Q3 evidence only: [Text2CAD](https://huggingface.co/datasets/SadilKhan/Text2CAD), [CAD-Coder](https://huggingface.co/datasets/gudo7208/CAD-Coder), [Text-to-CadQuery](https://github.com/Text-to-CadQuery/Text-to-CadQuery).

## Appendix C — Sources
See `../02_RECHERCHE/parallel/00_SYNTHESE.md` (verified facts with URLs), `D_unit_economics.md`, `E_usines.md`, `B_concurrence.md`, `../02_RECHERCHE/concurrents.md`, `../02_RECHERCHE/lecons_inputs.md`.
