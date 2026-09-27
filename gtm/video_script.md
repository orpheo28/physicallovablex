# Demo video — 90 seconds (Studio, current product)

Replaces the pre-pivot desk-lamp script. Screen recording (QuickTime) + voice-over. **Not published**: shared unlisted with the jury only (PLAN §1). Total 90 s, ≈220 spoken words (≈145 wpm).

**Footage source, so it costs $0 and has no waiting:** the recorded showcase **`whoop_kitesurf`** ("Kitesurf recovery band", prompt *"A Whoop competitor for kitesurfers, screenless, 5-day battery"*, 4 versions, 13/13 stages). It opens instantly at $0 (`PRODUIT.md` "Build strategy and showcases").
**One exception, stated honestly:** the showcase's own refine is *"add heart-rate and HRV sensing"* (a feature chip only, no part, no cost change: `mvp/api/fixtures/showcase_whoop_kitesurf/versions.json`). The SpO2 shot is therefore **one live refine** typed on the showcase: 4-7 s, ≈ $0.01 (`PRODUIT.md` step 3). It is short enough to show in real time.

**Claims allowed (all from `PRODUIT.md`):** first version 18-24 s in live runs (the showcase card reads "first version in 20 s") · refine 4-7 s, geometry refine 11-24 s · the AI writes build123d code, it runs in a sandbox, is measured, and the AI repairs it on error · Make it = 13 steps to the Launch Dossier in 54-88 s in live runs · factories via the production MCP · auto-approvals flagged · Launch Dossier EN + CN with the assumption register · every number carries Measured / Sourced / Estimate / Fictional — demo data. Nothing else.

| # | Time | On screen | Voice-over |
|---|---|---|---|
| 1 | 0:00-0:06 | Title card, paper background `#F7F6F3`, ink, Archivo condensed uppercase: **"Describe it. See it. Refine it. Make it."** | "In software, AI writes the code. In hardware, CAD is code. So we let AI write it, run it, measure it, and fix it." |
| 2 | 0:06-0:14 | **Describe.** Studio prompt box on `/?mode=idea`; the prompt types in: *"A Whoop competitor for kitesurfers, screenless, 5-day battery"*. **Do not press Start** (that is a live run). Cut on the Enter key. Small caption, bottom right: "Recorded run". | "Describe a product in one sentence: a Whoop competitor for kitesurfers. Screenless, five-day battery." |
| 3 | 0:14-0:30 | **See it.** Showcase `whoop_kitesurf` opened from the gallery. 3D pod turning; unit cost at **500 / 2,000 / 10,000** with its **Estimate** pills; LCSC lines with **Sourced** pills; top-3 factory shortlist with the violet **"Fictional — demo data"** pill (hold 2 s, zoom). Version list: v1 card "first version in 20 s". | "In our live runs, about twenty seconds later, you see it. The product in 3D, its unit cost at three volumes, and three factories that could build it, on one screen. The factories are fictional, and labelled." |
| 4 | 0:30-0:48 | **Refine it.** Type **"Add SpO2 and skin-temperature sensing."** → Send. New version card (live, real time, 4-7 s). Diff chips: component(s) added with part number, LCSC price and **Sourced** pill; unit cost before → after; certifications area (read what it shows). | "Then refine it by asking. Add SpO2 and skin-temperature sensing. A new version, in seconds: real LCSC parts at their real prices, the new unit cost, and the certifications checked again." *(If the certifications area shows a new row, alt ending: "…and a new line on the certification map.")* |
| 5 | 0:48-1:02 | **CAD code.** Version v4 "thinner, 8 mm pod": **CAD code** tab, the build123d program (header `model_v….py · build123d · read-only`), the diff (`pod_thickness 10.0 → 8.0`); diff chips "AI CAD program v1 → v2 — edited by the AI" and "Pod thickness 10.0 → 8.0 mm" with the **Measured** pill. | "The CAD is a program the AI writes. It runs in a sandbox, the solid is measured, and when the code breaks, the AI repairs it. Thinner pod: eight millimetres, measured on the model, not claimed." |
| 6 | 1:02-1:18 | **Make it.** Click **"Open overview"** (never "Make it again"): 13/13 stepper in four phases. Stage 7 shortlist (Fictional pills) → stage 8 negotiation transcript and the banner "Auto-approved in autofill mode — review and change the selected factory before any real order" → one beat on stage 11 duties (**Sourced**) and stage 12 cash curve. Caption: "Pre-computed · live: 54-88 s". | "Make it fills in the thirteen steps: factories through our production MCP, an agent negotiation with every auto-approval flagged, tooling, quality, duties and cash. Live, that takes under ninety seconds." |
| 7 | 1:18-1:25 | **Launch Dossier.** Export → PDF: cover, a Chinese page, the assumption register, the label legend in the footer. | "Everything lands in one Launch Dossier, in English and Chinese. Every number carries its label: measured, sourced, estimate, or fictional." |
| 8 | 1:25-1:30 | End card, paper background: **"Describe it. See it. Refine it. Make it."** + `physicallovablex.vercel.app` + small line "Demo: factories, quotes and freight are fictional." | "From idea to a thousand units, without speaking the factory's language." |

Word count: ≈ 206 (≈ 85 s at 145 wpm, leaving a few beats of silence on shots 3 and 6). Mapping to the case: 0:00 Why now · 0:06-0:48 Lovable layer · 0:48 CAD is code · 1:02 Alibaba layer + Infra (production MCP) · 1:18 Value (Factory Pack / Dossier).

## Recording checklist
**Setup**
- [ ] `mvp/scripts/demo_start.sh` → wait for **READY** (production build, routes pre-warmed; `mvp/docs/DEMO_DAY.md`). `localhost:8000/health` shows `llm_configured: true` (needed for the one live refine only).
- [ ] **Reset demo** first: `curl -X POST localhost:8000/demo/reset` (restores the 11 showcases, clears test factories).
- [ ] Browser window **1440×900**, zoom 100 %, one tab, notifications off, cursor highlight off, dark mode off.
- [ ] QuickTime → File → New Screen Recording → "Record selected portion", frame the 1440×900 window; internal mic off (voice-over recorded separately).

**Record in this order (not the edit order), so the live refine does not change what the other shots show**
1. Title and end cards (Keynote or Figma, `mvp/docs/BRAND.md` tokens), exported as 1440×900 stills.
2. Shot 2: type the prompt in the empty Studio box; stop before Start.
3. Shots 3, 5, 6, 7 on `whoop_kitesurf` as it opens (v4 is current): See it → CAD code tab on v4 → **Open overview** → stages 7, 8, 11, 12 → Export Launch Dossier (instant, $0).
4. **Last:** shot 4, the SpO2 refine on the same showcase (≈ $0.01, 4-7 s). It creates v5 and makes it current, which is why everything else is recorded before it. Record it twice; keep the take whose diff reads cleanly.
5. `curl -X POST localhost:8000/demo/reset` again, so the showcase is back to its recorded state.

**Honesty rules**
- [ ] Trust labels visible in every product shot; **"Fictional — demo data" on screen at least twice** (shot 3 shortlist, shot 8 end card).
- [ ] Cut time is labelled ("Recorded run", "Pre-computed · live: 54-88 s"); never present a cut as real time. The SpO2 refine is shown in real time.
- [ ] Read the SpO2 diff off the screen: do not voice a certification change unless the screen shows one (`mvp/docs/DEMO_SCRIPT.md`, note under the W23 table). Check the diff does not list the heart-rate / PPG sensor twice (old bug F1); if it does, re-take or drop the part name from the zoom.
- [ ] The self-repair is said, not shown: none of the 11 recorded showcases needed a repair (sourced claim: 1 repair in 7 live prompts, `PRODUIT.md`). Do not add a caption implying it happens on screen.
- [ ] Never click "Make it again" or restore a version on the showcase during recording (a live run, ≈ $0.34, 54-88 s).
- [ ] No "Hexa" in the voice-over, no real factory name, no "cheaper" or "faster than". Jury-only video, so the top-bar lockup can stay; if the footage is ever reused publicly, crop the 48 px top bar and the Factory Pack title block (both carry the Hexa logo).

**Voice-over timing**
- [ ] Record the voice-over after the edit, one take per shot, at ≈145 wpm; stopwatch each line against its time slot.
- [ ] Over 90 s? Cut in this order: "on one screen" (shot 3) → the label sentence in shot 7 → "not claimed" (shot 5).
- [ ] Export 1440×900 H.264, check audio levels, watch once with sound off: the story must still read from the captions.
