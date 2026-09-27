# Demo script — Studio (6 min live) and 90-second video

Scenario: **the Whoop competitor.** Audience: the jury (Louise Texier, Raphaël Vullierme), 45 min slot; the live demo is a 6-minute core plus an ≈80 s MCP moment (total ≈7:20 — drop "Target retail $149" to come back to 6:00 if needed). Pre-demo setup: **`docs/DEMO_DAY.md`** (run `scripts/demo_start.sh`, wait for READY, credit and key check, Reset demo).

**Design of the live part:** type the idea and 3-4 refines live (cheap: 4-7 s for colour and feature changes, 11-24 s when the AI edits the geometry), then open the recorded `whoop_kitesurf` showcase via **"Open overview"** (never "Make it again" on stage — that starts a live run), then the ≈80-second, two-prompt **MCP moment in Claude Desktop**. Live Make it (54-88 s, ≈ $0.34 in one run) is optional, not part of the plan.

Rules on stage: say the labels out loud (Measured, Sourced, Estimate, Fictional — demo data). If a "Cached example" banner shows, say so. If a diff shows "no change" for a category, say "no change". Numbers are read off the screen at the time; they vary run to run.

**Reference numbers (measured live over several runs; they vary):** Studio start 18-24 s (the AI-written CAD arrives in the background, ≈ 23 s) · colour and feature refines 4-7 s · geometry refines (the AI edits its CAD program) 11-24 s · Make it 54-88 s · restore 1.8 s, refine ≈ $0.01, Make it ≈ $0.34 (one run each). Full stages 1-7 on 10 prompts: 56-76 s. Text-to-CAD: 7/7 live prompts recognisable, ≈ 28-34 s per generation. The detailed rehearsal table below (W23) has per-prompt evidence from one specific run.

**Why SpO2 and not heart rate:** a Whoop-class band already has heart-rate sensing, so "add heart-rate" would show no delta. "Add SpO2 and skin-temperature sensing" adds a part, so cost changes; as of the current build it also adds an FDA wellness/medical-device note to the certification map — say what the screen actually shows, since this line has changed behaviour before (see the table note below).

**Recorded showcases** (open instantly, $0). Complete through Make it (13/13): `whoop_kitesurf`, `changing_table`, `stick_vacuum`, `irrigation_biarritz`, `solar_biarritz`, `surfboard_beginner`, `drone_follow`. Start-only: `home_robot`, `hair_dryer`, `instant_camera`, `minimal_phone`. Use `whoop_kitesurf` for the Make it moment (same product family as the live scenario, prototype path $317 / 4 weeks); `drone_follow` shows drone checks (thrust-to-weight, hover time, EU class C0/C1/C2 from EUR-Lex, Sourced); `solar_biarritz` shows PVGIS yield.

Mapping to the case bullets: **L** = Lovable, **A** = Alibaba layer + production MCP, **I** = Infra, **V** = Value, **W** = Why now.

## Live demo — 6:00 core

| Time | Action (type exactly) | Point at on screen | Say (1-2 sentences) | Case |
|---|---|---|---|---|
| 0:00-0:30 | Open `/?mode=idea`. Nothing typed yet. | The empty Studio prompt box. | "In software the AI writes code. In hardware, CAD is code: we let the AI write it, run it, measure it and fix it. Hardware ships late because nobody translates an idea into what a factory can build; this is that translation." | W, V |
| 0:30-1:20 | Type: **`A Whoop competitor: a screenless wrist-worn band, 5-day battery, tracks sleep and strain.`** → Start. | The 3D model, unit cost at 3 volumes, top-3 shortlist, the four label pills. Open the **"CAD code"** tab for 5 seconds. | "A first version in 18 to 24 seconds on our live runs. The AI wrote this CAD program, ran it in a sandbox, measured it, and repairs its own errors. The factories are fictional and labeled; the component prices are real." If it takes longer, talk over it; do not click. | L, A |
| 1:20-2:05 | Type: **`Add SpO2 and skin-temperature sensing.`** | Version list (v2). Diff chips: BOM (new part(s), Sourced LCSC price), cost. Open the certifications area and read what it says — either a new row/note or "no change"; do not claim which in advance. | "Each prompt is a version with a diff, in 4 to 7 seconds. This is a real LCSC part at its real price; unit cost moved by [read the delta]." Then read the certification line as it appears on screen, including "no change" if that is what it says. | L, I |
| 2:05-2:30 | Type: **`Make it pink.`** | The finish chip; cost unchanged (colour only); the concept render arrives about 16 s later — do not wait for it, come back to it. | "A colour change, and the cost says so: unchanged, colour only. The render lands in the background." | L |
| 2:30-3:30 | Type: **`Thinner, 8 mm pod.`** (11-24 s: the AI edits its CAD program) | Open the **"CAD code" tab**: the edited build123d lines. CAD chip: **8 mm, Measured**. Then click **restore v2** and back to the latest (1.8 s, one run). | "The AI edits its own CAD code, and the result is measured on the model, not claimed: 8 millimetres. Any version comes back in two seconds; Make it then runs again on it." | L, I |
| 3:30-3:50 | Type: **`Target retail $149.`** (skip if behind schedule) | Margin and break-even, in the Studio strip — no click to Overview needed. | "The price becomes a constraint: margin and break-even recompute, right here." | V |
| 3:50-4:50 | Open the **showcase gallery** → **`whoop_kitesurf`** → click **"Open overview"** (never "Make it again" on stage — that starts a live run, ≈ $0.34, 54-88 s). It is already complete, 13/13. | Stages 8-13 filled; the auto-approved quote flagged (`a8_autofill`); negotiation transcript; duties by product code; cash curve; the prototype path (e.g. kitesurf wearable $317, 4 weeks). If time allows, flip to `drone_follow` (drone checks) or `solar_biarritz` (PVGIS yield). | "This one is pre-computed: agents already requested quotes through the production MCP and negotiated. The approval reads \"Auto-approved (autofill mode)\" with a \"Change factory\" button; the Dossier records it as assumption a8_autofill. Live, Make it takes 54 to 88 seconds." Say: "Concept-level geometry: about 80% of the translation is automated, humans and real factories do the last 20%." | A, I, V |
| 4:50-5:00 | Show the Launch Dossier PDF (EN + CN) for a few seconds. | Factory Pack §1-§9, assumption register, labels. | "One Factory Pack, in English and Chinese: negotiation, QC, cash and logistics all read from it." | V |
| 5:00-6:20 (≈80 s, two prompts) | **MCP moment in Claude Desktop** — see the block below. | Claude Desktop with the production MCP connected, portal in a second tab. | "Any agent can query factory capacity. This is Claude, not our app." | A |

### The ≈80-second MCP moment (built — from `docs/MCP_DEMO.md`)
Two prompts, not three: Claude already requests a quote as part of answering the first prompt, so a separate "request a quote" prompt only duplicates it. Measured: ≈52 s + ≈28 s ≈ 80 s. A 3-prompt version measured ≈100 s and does not fit the slot.

Setup once (deployed; local: `claude mcp add --transport http physicallovablex-local http://localhost:8000/mcp`):
- **Claude Code:** `claude mcp add --transport http physicallovablex-production https://physicallovablex-production.up.railway.app/mcp --header "Authorization: Bearer $MCP_TOKEN"`
- **Claude Desktop:** copy the JSON config from `docs/MCP_DEMO.md` (uses `mcp-remote`, token in `env`), restart, check the tools are listed.
- **Before going on stage:** `POST /demo/reset` (clears test factories and RFQs), portal open in a second tab.

| # | Time | Type in Claude | What to point at |
|---|---|---|---|
| 1 | 0:00 (≈52 s) | *Find me a factory that can make 2,000 silicone fitness bands with PCBA before December, and request a quote from the best one for 500, 2,000 and 10,000.* | Claude calls `search_capacity` twice (LSR/silicone, then PCBA), `get_factory_profile`, then `request_quote` on its own — a ranked shortlist with score /100 and reasons, then an `rfq_id`. Switch to the portal: the RFQ is listed on that factory. If Claude stops after the shortlist without requesting a quote, ask once: *"Request it."* |
| 2 | ≈0:52 (≈28 s) | *Register my factory's capacity: Tidewater Wearables, Penang, LSR overmolding + PCBA + assembly, silicone and FR-4, MOQ 500, ISO 9001 and ISO 13485, 28-day lead time, 60,000 units/month, 35% loaded.* | `register_capacity` → `factory_id`; refresh the portal: **Tidewater Wearables (fictional)** is listed; re-run prompt 1's search and it ranks #1. |

Say: "That factory never had a public API. Now it has one, and Claude, ChatGPT or our own buyer agent use it the same way. All factories are fictional." Read the actual score off the screen (a rehearsed run showed Tidewater at 96/100 for "LSR silicone + PCBA, 2,000 units").
If the network or connection fails: run the two scripted agents locally (`uv run python -m factory_mcp.demo.factory_agent`, then `buyer_agent`; commands in `docs/MCP_DEMO.md`) and show the printed transcript, or open `/factories` and stage 7. After the demo: `POST /demo/reset`.

### Timing notes
- Colour and feature refines take 4-7 s; the geometry refine takes 11-24 s, so budget for it and talk over it. If one is slow, keep talking over the diff of the previous one.
- The 6:00 core plus the ≈80 s MCP moment totals ≈7:20. If behind: drop "Target retail $149" first, then the restore, then the Dossier PDF pause. Never drop the MCP moment — it is the Alibaba-layer proof.
- Ahead of time: rehearse the exact prompts once so you know which diff lines and numbers appear (see the rehearsal table below), and time the MCP moment once — if it runs past ≈90 s, drop the "Request it." follow-up prompt.

## Fallback paths (unchanged)

| Situation | What to do |
|---|---|
| Live AI slow (> 90 s on first result) | Keep talking once; at 90 s open **Open example → desk lamp** (cached, complete 1-13). Say: "Same path, pre-computed." Continue at the 3D screen. |
| Live AI down, 402, or a "Cached example" banner appears | Say it: "AI is unavailable, this is the pre-computed example." Use the cached desk lamp: overview → stage 4 DFM (measured) → 5 (LCSC-sourced BOM) → 8 negotiation → 11 duties → 12 cash → Export PDF. Showcase examples work the same way. |
| A refine prompt fails or takes > 30 s | A failed refine leaves a "failed" version card with a plain-language error and the previous version stays current: say so. Try a simpler prompt ("Make it pink"), otherwise open the `whoop_kitesurf` showcase. |
| Web or API will not start | `docs/DEMO_DAY.md` "Backup plan"; the exported PDFs and `docs/screens/after/`. |

**Factory portal + MCP (always available):** `/factories` → the 15 fictional partners (11 factories, 1 integrator, 3 installers) → "Offer your capacity" → register a factory → its page → stage 7. Reset with `curl -X POST localhost:8000/demo/reset` afterwards.

## Pre-demo checklist
Follow **`docs/DEMO_DAY.md`** (day before, one hour before, backup plan). Add for this script:
1. Run the Whoop scenario once online; confirm each prompt produces a version and a diff, and note the numbers (table below) — in particular, what the SpO2 prompt currently shows in certifications and cost.
2. Confirm `whoop_kitesurf` opens via "Open overview" and is complete 13/13; never click "Make it again" on stage during rehearsal (it costs ≈$0.34 and 54-88 s each time).
3. Set up Claude Desktop with the production MCP (`docs/MCP_DEMO.md`), run the ≈80-second, two-prompt moment once and time it — if it runs long, drop the "Request it." follow-up, then **`POST /demo/reset`** (clears the test factories and RFQs) right before going on stage.
4. Full screen, browser zoom 100 %, one tab, `localhost:8000/health` in a second tab (`llm_configured: true`), credit checked.

### Observed diffs (W23b rehearsal, 27 Sept 13:23, one live run, `demo_start.sh` on :8000/:3000, production build)
Measured through the UI (Playwright, 1440×900). Times run from Send (Enter) to the version card turning "done". "Photo" is when the auto-captured Photo for that version was ready. Evidence: `tests/results/final2/B*.png`, `tests/results/final2/B4_cad_code.diff`.
| Prompt | Time (s) | Chips that changed | Cost (unit @ 2,000) | Certifications | Photo |
|---|---|---|---|---|---|
| start | **21.6** (card: "first version in 21 s"); AI-written CAD patched in at 42.1 s | v1 "Screenless Fitness Band": 44 × 30 × 10 mm Measured, 14 BOM lines, $27.20 / $26.21 / $25.33, 4 certifications, shortlist Coralline 88 · Lumen Peak 86 · Harborlight 85 | — | FCC Part 15C, UN38.3, IEC 62133-2, 47 CFR § 2.1093 | 34.9 s, "Photo-styled from the CAD (AI image, geometry from our CAD)"; it matches the model (captured before the AI CAD landed) |
| add SpO2 and skin-temperature sensing | **4.9** (background done at 17.9 s) | Component added: "Skin-contact temperature sensor × 1 — LCSC C7472806, $4.10/unit" (Sourced) · Component upgraded: "Optical PPG heart-rate sensor → Optical heart-rate / SpO2 sensor (PPG, red + IR, MAX30102)" (Estimate) · Feature × 2 · Certification required · Unit cost · Certification budget $11,000 → $13,500 | **$26.21 → $31.00 (+$4.79)**, no duplicate sensor | **+1 row: "US FDA general-wellness vs medical-device boundary (SpO2 / body-temperature claims)"**, 4 → 5 | 18.8 s |
| make it pink | **3.5** | Colour: Warm white #EDEBE6 → Pink #FFC0CB; the card says "Cost unchanged · certifications unchanged" | unchanged ($31.00) | unchanged | 20.5 s, pink pod |
| thinner, 8 mm pod | **13.8** | Pod thickness 10.0 → **8.0 mm Measured**, enclosure weight 5.6 → 5.2 g, AI CAD program v1 → v2 — edited by the AI; "Cost unchanged · certifications unchanged" | unchanged ($31.00; $30.12 → $30.11 at 10k) | unchanged | 26.1 s |
| restore v2, back to v4 | server 0.01-0.03 s; the UI asks with an in-app dialog ("Restore v3?" → Cancel / Restore) | — | — | — | — |
| target retail $149 | **3.3** | Target retail price $199.00 → $149.00 | unit cost unchanged. **Studio strip: "Margin @2k 70.4 %", "Break-even 174 units"** | — | 17.8 s (a new photo even though the look did not change) |

CAD code diff for "thinner, 8 mm": a single line, `"pod_thickness": 10.0 → 8.0` (the parameter drives the geometry). Listing photos (··· → Listing photos → Generate): **4 shots in 16.6 s**. Packshot and detail are labeled "Photo-styled from the CAD…"; lifestyle and in hand add "· Staged scene — illustrative". All look like the CAD. The packshot has dark curved artifacts at its edges.
Total waiting in the live part (typing excluded): 21.6 + 4.9 + 3.5 + 13.8 + 3.3 = **47.1 s**. OpenRouter spend for the whole rehearsal: **$0.92**. That covers the start, the 4 refines, the background CAD, reviews and firmware, 5 auto photos, the 4-shot listing kit and one Dossier export of the live project. The previous build, without photos, spent $0.31.

---

## Video — 90 seconds

Screen recording, voice-over. Cut waiting time, but write "sped up" or show a timer; do not present cut time as real time. Style: `docs/BRAND.md`.

| Time | Screen | Voice-over |
|---|---|---|
| 0:00-0:08 | Title on paper background: "Describe it. See it. Refine it. Make it." | "In software the AI writes code. In hardware, CAD is code." |
| 0:08-0:22 | Type the Whoop prompt; the 3D product, cost at 3 volumes, factories; the "CAD code" tab for two seconds. | "Describe a product in a sentence. The AI writes the CAD, runs it, measures it, and shows you the product with its cost and factories, in about twenty seconds." |
| 0:22-0:40 | "Add SpO2 and skin-temperature sensing"; diff chips; zoom on the new LCSC part(s) with the Sourced pill and the unit-cost change; then "Make it pink" (cost unchanged). | "Refine it by asking. Each change is a version with a diff: a real component at its real price, the cost delta, in a few seconds." |
| 0:40-0:55 | "Thinner, 8 mm pod" (sped up); the CAD code edit; 8 mm Measured; restore a version. | "The AI edits its own CAD code, and the result is measured on the model, not claimed. Every version can be restored." |
| 0:55-1:15 | The `whoop_kitesurf` showcase, opened via "Open overview": flagged auto-approval, negotiation transcript, factory portal with the "Fictional — demo data" pill. | "Make it fills in the rest: factories, agent negotiation you can review, tooling, quality, duties, cash. The factories are fictional, and labeled." |
| 1:15-1:30 | Claude Desktop calls the production MCP, then Launch Dossier PDF, end card with the URL. | "Any agent can query factory capacity through the MCP. One Launch Dossier, in English and Chinese. Start a product." |

Mapping: 0:00 Why now · 0:08 Lovable · 0:22-0:55 Value · 0:55 Infra + Alibaba · 1:15 MCP + Value.
The video must not claim: real factories, real quotes, or a finished prototype in minutes. Record the MCP shot only from a rehearsed Claude Desktop session on the deployed endpoint; do not claim a specific certification or cost outcome for SpO2 until it is re-verified per the note above.
