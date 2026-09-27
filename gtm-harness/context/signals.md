# Signals

Last updated: 2026-09-27. Format (detection, points, decay, combinations, hook, performance) adapted from the GTM repository signal library (credits in `README.md`).

Two numbers per account:
- **Urgency score (1-5):** how bad the production problem is. Rubric in `skills/icp-scoring/SKILL.md`. Unchanged.
- **Priority points (0-100):** whether to write *now*, and how hard to personalise. New on 27/09.

**Points, decay and bonuses are design choices (Hypothesis), not measured.** Calibrate them on the performance table below once replies exist. A signal library with no results is a hypothesis document.

## The six signals
| # | Signal | Detection method (public sources only, `workflows/enrichment.md`) | Points | Decay | Message hook (own words, quote the source) | Seen in |
|---|---|---|---|---|---|---|
| S1 | **Estimated delivery date has passed** (gate: without it, urgency is capped at 2) | Reward "Estimated delivery" on Kickstarter / Indiegogo / Crowd Supply vs today; latest creator update for the new date; Wayback for moved dates | 30, **+10 if > 12 months late** | None: it grows with lateness. Expires when fully shipped | "Your ship date moved from {A} to {B}. What took longer than planned?" | Wordrunner promised Jan 2026 ([Kickstarter](https://www.kickstarter.com/projects/astrohaus/wordrunner-mechanical-word-counting-keyboard)) |
| S2 | **Creator update names a production cause:** factory, mold or tooling, failed sample, component shortage or quality, certification (EMC, FCC), redesign | Read `/posts` or `/updates` and the brand blog; search "factory", "mold", "tooling", "sample", "supplier", "lead time", "EMC", "FCC", "redesign" | 25 | By update age: 0-30 d 100%, 31-90 d 75%, 91-180 d 50%, 181-365 d 25%, > 365 d 0% (the cause stays in `notes`; only the hook expires) | Quote their sentence, then ask what they would do differently at the prototype stage | Pilet update #20 ([c33tech](https://c33tech.com/blog/2026/04/how_not_to_pilet_a_kickstarter/)); PicoIDE T1 mold samples late, GameTank EMC revision, SlimeVR FCC filing (`03_DISCOVERY/envoi/A_ENVOYER.md` #28, #30, #36) |
| S3 | **Backer comments about production** (confirms, never raises alone; max urgency 2 alone) | `/comments`, Trustpilot, BBB, Reddit, brand forums; if 403, search snippet = medium confidence | 10 | Same as S2 | Never quoted. Use it only to choose which S1/S2 fact to cite | SwiftShape ([Glowforge forum](https://community.glowforge.com/t/swiftshape/140166)); Smokpub 1.7/5 ([Trustpilot](https://www.trustpilot.com/review/smokpub.com)) |
| S4 | **Pre-order extended or "shipping soon" past the promised date** | Live product page, re-read on each run; Wayback for history | 20 | None while the page still says it; 0 when it changes | "Your page still says {exact words} after {promised date}." | Wordrunner "PREORDER NOW" Sept 2026 ([getfreewrite.com](https://getfreewrite.com/products/wordrunner)); Brilliant Labs Halo "will begin shipping soon" on 27/09/2026 (`A_ENVOYER.md` #31) |
| S5 | **Sourcing or supply-chain job post at a company < 50 people** (untested: no account found this way) | Public LinkedIn Jobs, Welcome to the Jungle, careers pages; filter "sourcing", "supply chain", "NPI" | 10 | 0-30 d 100%, 31-60 d 50%, > 60 d 0% | "You are hiring for {role}: what should that person fix first?" | none yet |
| S6 | **New product announced** (next buying moment) | Brand news, press, new campaign page, CES | 15 | Full until the new product ships, then 0 | "After {product 1}, what are you doing differently on {product 2}?" | Halliday G2 ([Engadget](https://www.engadget.com/2216393/halliday-g2-smart-glasses/)); Minimal Phone 2, Kickstarter 11/08/2026 ([Gizmochina](https://www.gizmochina.com/2026/08/11/minimal-phone-2-swaps-e-ink-for-3-92-inch-oled-retains-qwerty-keyboard/)) |

## Combination bonus
| Combination | Bonus | Why |
|---|---|---|
| S1 + S2 | +15 | Late *and* the cause is written: the exact conversation campaign 01 needs |
| S1 + S6 | +10 | Late on product 1 while preparing product 2: the buying moment (`personas/hardware-founder.md`) |
| S4 + S6 | +10 | Still on pre-order while announcing the next one |

## Penalties and suppression (applied in `workflows/signal-routing.md`)
- Established brand with its own supply chain → Tier 4, no sales outreach, whatever the points (`context/icp.md`).
- Signal read only from a search snippet (page 403) → points × 0.5, and never quoted.
- No public channel to the founder → hold until one is found (`A_ENVOYER.md` #13, #21-#23).

## Buckets
Priority = points × decay + bonus, capped at 100. **HOT ≥ 60:** research card + hand-written message within 48 h. **WARM 40-59:** message if a fresh quote exists. **COLD 20-39:** monitor, re-check weekly. **SKIP < 20:** archive. Bucket names from GTM Strategist, "Craft Irresistible Outbound Campaigns Using Claude Code" (`04_LIVRABLE/GTM_Lessons_Substack_MajaVoje.md`).
Worked example, 27/09: Pilet = S1 30 + 10 (> 12 months late) + S2 25 × 50% (update #20, 11/04/2026, 169 days) + S1+S2 15 = **67.5, HOT**. Wordrunner = S1 30 + S4 20 = **50, WARM** (cause not stated, so no S2).

## Signals that do not count
Logistics-only delays: VAT paperwork (Wyrmwood), a typhoon (Peak Design), missing merch (CyberBrick), sizing kits (RingConn); address collection (AYANEO Pocket AIR Mini). Rows scored 1-2 in `outputs/accounts.csv`.

## Performance tracking (campaign 01, state 27/09: nothing sent)
"Drafts" = main signal each draft cites in `A_ENVOYER.md`, my coding (a human should check). "Sendable" excludes #13, #21-#23 (no direct channel, `SUIVI.md`). Update after every send batch and every call (`skills/call-debrief`, `skills/weekly-update`).
| Signal | Drafts | Sendable | Sent | Replies | Calls | Calls naming design, components or certification |
|---|---|---|---|---|---|---|
| S1 Delivery date passed | 5 | 5 | 0 | 0 | 0 | 0 |
| S2 Update names a production cause | 18 | 17 | 0 | 0 | 0 | 0 |
| S3 Backer comments | 5 | 4 | 0 | 0 | 0 | 0 |
| S4 Pre-order extended | 2 | 2 | 0 | 0 | 0 | 0 |
| S5 Job post | 0 | 0 | 0 | 0 | 0 | 0 |
| S6 New product | 1 | 1 | 0 | 0 | 0 | 0 |
| Other (logistics or no production problem) | 5 | 3 | 0 | 0 | 0 | 0 |
| **Cold total** | **36** | **32** | 0 | 0 | 0 | 0 |
| Warm network (no signal, `03_DISCOVERY/envoi/RESEAU.md`) | 10 planned | — | 0 | 0 | 0 | 0 |
