# PhysicalLovableX — product one-pager

Full detail: `PRD.md`. This page is the summary; if they differ, PRD.md wins.

## Narrative
Hardware doesn't ship late because of design or because of the factory. It ships late because nobody translates the idea into what the factory can build. We do that translation.

**Pitch line:** From idea or prototype to 1,000 units shipped, without speaking the factory's language.
**Product line:** Describe it. See it. Refine it. Make it.

## Positioning
In software the AI writes code. In hardware, **CAD is code**: we let the AI write it, run it, measure it and fix it. The AI writes build123d code, it runs in a sandbox, the result is measured, and on an error the AI repairs its own code (like a coding agent on a compile error). The code is visible in the app ("CAD code" tab).

**Honest scope:** concept-level geometry. About 80% of the translation from idea to a factory-ready package is automated; humans and real factories cover the last 20% (tier 2, human-reviewed). A working prototype takes weeks, not minutes.

## The Studio — prompt-to-product loop (the demo)
1. **Describe.** One sentence: "A Whoop competitor, screenless, 5-day battery."
2. **See it.** The product in 3D, its unit cost, and the top factories, on one screen. **Measured live over several runs: first version in 18-24 s** (the AI-written CAD arrives in the background, ≈ 23 s for v1). The full stages 1-7 run took 56-76 s on 10 test prompts.
3. **Refine it by prompting.** "Add SpO2 and skin-temperature sensing", "make it pink", "thinner, 8 mm pod", "target retail $149". Each prompt creates a **new version** and shows what changed: CAD rebuilt, BOM with real LCSC parts, costs, DFM re-measured, certifications, factory shortlist. **Measured live over several runs: colour and feature refines 4-7 s; geometry refines, where the AI edits its own CAD program, 11-24 s** (≈ $0.01 per refine in one run); restoring a version 1.8 s (one run). Feature prompts add parts at real LCSC prices and change cost and the certification map; "thinner, 8 mm pod" edits the CAD code and is re-measured (8.0 mm in one run); the "make it pink" render arrived 16 s later (one run).
4. **Make it.** One action autofills the rest: factories via the production MCP, agent negotiation (auto-approvals flagged), tooling, QC, logistics and duties, cash plan, brand. **Measured live over several runs: 13 steps to the Launch Dossier in 54-88 s** (≈ $0.34 in one run). On the recorded showcases Make it opens instantly, at $0.
5. **Launch Dossier** (EN + CN): the Factory Pack plus the output of every stage and the assumption register.

The 13 stages remain the **detailed view**, grouped in four phases: **Design** (1-3) · **Make it manufacturable** (4-6) · **Source** (7-8) · **Launch** (9-13). Restoring an earlier version makes it current; later versions stay, and Make it runs again.

## Engineering layer (built)
- **Text-to-CAD:** the AI writes build123d code, run in a sandbox, measured, self-repaired on error. 7/7 live prompts produced a recognisable product (surfboard, changing table, home robot, stick vacuum, irrigation kit, rooftop solar, a vacuum edit v1→v2), one self-repair, ≈ 28-34 s per generation. Parametric families serve as seeds and fallbacks (board, furniture, stick_vacuum, home_robot, irrigation, solar_array, wearable_band, ring).
- **Category packs:** 10 packs with standards and verified citations.
- **Physics checks on the measured CAD** (pass / warn / fail): tip-over angle, board litres and buoyancy, battery life from the power budget, vacuum air watts, irrigation pressure, and PVGIS solar yield (**Sourced**, e.g. Biarritz 35 m² → 5.59 kWp, 6,860 kWh/yr).
- **Electronics architecture + power budget**, and a generated **firmware skeleton** (Zephyr BLE or Arduino Wi-Fi), labeled "not compiled or tested".
- **Prototype path** with cost and time (e.g. kitesurf wearable: $317, 4 weeks).
- Rooftop solar goes to certified installers (fictional) instead of factories.

## Production MCP over HTTP (built)
The 7 tools are served at `/mcp` (Streamable HTTP, Bearer token). Any agent (Claude Code, Claude Desktop, a ChatGPT connector, a script) can search capacity, request quotes and register capacity, in the same store as the web portal. Scripted proof: a factory agent registers "Tidewater Wearables (fictional)", which appears in the portal and ranks #1 (96/100) for "LSR silicone + PCBA, 2,000 units"; the buyer agent then requests a quote for 500 / 2,000 / 10,000. Setup: `mvp/docs/MCP_DEMO.md`.

## Build strategy and showcases (built)
- **Build strategy chosen automatically:** *full design* (furniture, board, lamp, tracker) / *module assembly* (drone, irrigation, wearable, hair dryer, vacuum) / *ODM customisation* (smartphone, camera, home robot), with the honest industrial path for each. New categories: drone, hair dryer, camera, smartphone.
- **Showcase gallery** of 11 recorded examples. Complete through Make it (13/13): whoop_kitesurf, changing_table, stick_vacuum, irrigation_biarritz, solar_biarritz, surfboard_beginner, drone_follow. Start-only: home_robot, hair_dryer, instant_camera, minimal_phone. They open instantly, at $0.
- Drone checks: thrust-to-weight, hover time, EU class C0/C1/C2 (**Sourced** from EUR-Lex).

## Primitive — the Factory Pack
A spec package a factory can quote and build without back-and-forth: structured spec, CAD, BOM with component risk, DFM alerts, certification checklist, estimated landed cost, questions for the factory (EN + CN), assumption register.
Every later layer consumes it: negotiation starts from it, QC checks against it, financing uses its cost model, logistics uses its landed cost. It is also the data that compounds into the moat. Each Studio version produces its own Factory Pack.

## Enablers
1. Spec copilot  2. DFM + component check  3. Certification map  4. Cost and landed-cost engine  5. Factory matching through the production MCP  6. Factory Pack export

## The full journey (13 stages, detailed view)
| # | Phase | Stage | Concept layer | Demo |
|---|---|---|---|---|
| 1 | Design | Brief (idea OR prototype + BOM) | Lovable | Real |
| 2 | Design | Industrial design (3 directions) | Lovable | Real |
| 3 | Design | CAD + technical spec | Lovable | Real |
| 4 | Manufacturable | DFM, components, certification | Core | Real — geometry checks **measured** on the CAD |
| 5 | Manufacturable | Investment (500 / 2k / 10k, tooling, cash, margin, break-even) | Lovable | Real — electronics at **real LCSC prices**, rest "Estimate" |
| 6 | Manufacturable | Where and how to produce | Lovable | Real |
| 7 | Source | Factory matching + factory portal (MCP) | Alibaba | Simulated |
| 8 | Source | RFQ + agent negotiation | Infra | Simulated |
| 9 | Launch | Tooling + samples | Infra | Generated plan |
| 10 | Launch | Quality control (AQL) | Infra | Generated plan |
| 11 | Launch | Logistics + duties | Infra | Duties Sourced (CBP rulings), freight lane derived from Drewry WCI, carrier and transit simulated |
| 12 | Launch | Financing (cash curve, options) | Infra | Generated plan |
| 13 | Launch | Brand + distribution (name, packaging, landing, listing) | Idea → brand | Real |
Final export: Launch Dossier.

## Trust labels
Every number carries one label: **Measured** (on the CAD), **Sourced** (real price or official rate, dated), **Estimate** (assumption shown), **Fictional — demo data**.

**Real:** brief, design, CAD, measured DFM, certification map, LCSC part prices and stock (snapshot dated), HTS line from CBP rulings, Drewry freight index, eCFR citations, cost engine, production plan, brand kit. **Fictional:** the 15 partners (11 factories, 1 integrator, 3 installers), their capacity, quotes and negotiation replies, carrier freight quotes and transit days.

## Two entry modes
- **"I have an idea"** — demo headline, faithful to the brief; starts the Studio.
- **"I have a prototype"** — GTM wedge: founders with a working prototype and money pledged who are stuck on production.

## Wow moment
Prompt → the product in 3D, its unit cost at three volumes, and a top-3 factory shortlist on one screen (first version in 18-24 s over several live runs; 56-76 s for the full stages 1-7 on 10 prompts). Then the change that sells the product: type "add SpO2 and skin-temperature sensing" and watch real LCSC parts, the cost, the certification map and the version diff change in 4-7 s.

## Business model (hypothesis)
Free up to the Factory Pack (land grab, data) → commission on the production order (tier 2, human-accompanied, committed landed price) → take rate on financing and logistics (tier 3).

## Not building
Sophisticated CAD rendering (commodity: Zoo, Backflip, Atech), a real marketplace, payments, real logistics booking.
