# Persona: the hardware founder (user and buyer)

Last updated: 2026-09-27. **Observed** = sourced. **Hypothesis** = campaign 01 must test it. Objections are updated by `skills/call-debrief`.

## Overview
- **Titles:** founder, co-founder, CEO of a small team (`outputs/accounts.csv`, `contact` column).
- **Decision role:** user = buyer = decider in Segment A: the public contact is the founder (The Minimal Phone, AIVELA, Wordrunner, GAMR, Circular). **Hypothesis:** decides alone or as a co-founder pair, no committee (`context/icp.md`).
- **Found at:** funded crowdfunding campaigns (Kickstarter, Indiegogo, Crowd Supply), first or second product, manufacturing in Asia, consumer electronics first.
- **Primary metric (Hypothesis):** units shipped against the public date, and margin at a price fixed at pledge time.

## Their days (observed)
- Writing public production updates: Pilet update #20 ([c33tech](https://c33tech.com/blog/2026/04/how_not_to_pilet_a_kickstarter/)); Circular: "By Week 5, we were down to 60 remaining orders" ([Circular](https://www.circular.xyz/post/circular-ring-2-release-notes-oct-2025)).
- Answering comments one by one: GAMR explains raw-material delays ([Kickstarter](https://www.kickstarter.com/projects/active-gaming-pad/gamr-active-gaming-play-pad/comments?comment=Q29tbWVudC00ODAyODk5Ng%3D%3D), medium confidence).
- Running PledgeBox and BackerKit (`outputs/accounts.csv`).

## What blocks them (observed)
- Component quality: AIVELA, "About half of the units made in that batch passed final checks" ([Gadgets & Wearables](https://gadgetsandwearables.com/2026/02/12/aivela-ring-pro-shipping/)).
- Certification: HOVERAir AQUA US backers refunded after an FCC ban ([DroneXL](https://dronexl.co/2026/05/28/hoverair-aqua-global-launch-us-fcc-ban/)).
- The factory's language: Halliday's COO, "we didn't speak [the manufacturer's] language" ([Engadget](https://www.engadget.com/2216393/halliday-g2-smart-glasses/)).

## Triggers (when they would listen)
| Trigger | Status | Signal |
|---|---|---|
| A public date already missed | Observed pattern (`outputs/accounts.csv`) | S1, S4 |
| A written production cause in an update | Observed | S2 |
| A next product being prepared (Halliday G2, Minimal Phone 2) | Observed; buying moment = **Hypothesis** | S6 |
| Backer pressure (refund site, BBB, 1.7/5 Trustpilot) | Observed ([c33tech](https://c33tech.com/blog/2026/04/how_not_to_pilet_a_kickstarter/), [iTechGuides](https://www.itechguides.com/with-backers-losing-patience-the-long-delayed-minimal-phone-was-rumored-to-ship-in-two-weeks-what-happened/), [Trustpilot](https://www.trustpilot.com/review/smokpub.com)) | S3 (never quoted) |

## Who influences them
- Backers (observed, above).
- An engineering co-founder (observed: Looktech CTO; Blisstil founder is the engineer; The Minimal Company, Astrohaus, Soulscircuit have two co-founders, `outputs/accounts.csv`). **Hypothesis:** holds a veto on outside DFM or component advice.

## How they buy (Hypothesis)
- Buy when a public date is at risk, not before the campaign.
- Compare against a sourcing agent at 5-10% ([Dragon Sourcing](https://www.dragonsourcing.com/top-10-cost-insights-for-hiring-a-china-sourcing-agent/)), not against a SaaS subscription.
- Evaluate by seeing their own product run through the Studio ("show, don't tell", deck slide 4).

## Objections (none heard yet; all Hypothesis)
| Objection | Where it comes from | Answer to test |
|---|---|---|
| "I already have a factory / a contact in Shenzhen" | Kill criterion (`PRD.md` §3) | Ask what the contact missed on the first run (question 4); if nothing, log as a loss |
| "No time, we are shipping" | Their days, above | Offer one written question instead (follow-up in `skills/signal-to-sequence`) |
| "My unreleased design must not leak" | Deck slide 12; `PRD.md` §15 | NDA before any factory sees a pack; say LLM data policy is not in place yet |
| "Is this a sales pitch?" | Outreach rules | Truthful: studying why launches slip, nothing to sell |

## Hooks
- Cite *their* signal: update number and date, their words. Never a generic "saw you're delayed".
- Ask about the cause, never pitch. Talk to the founder and the engineering co-founder together.
- Circular Ring 2 (Paris): write in French (`02_RECHERCHE/parallel/00_SYNTHESE.md` §3).
