# Metrics

Last updated: 2026-09-27. **Every target here is our own and a Hypothesis, not a benchmark.** State on 27/09: 0 sent, 0 replies, 0 calls, 0 packs, 0 factory quotes (`03_DISCOVERY/envoi/SUIVI.md`). This file holds definitions and targets; live counts stay in `SUIVI.md` → `outputs/campaign-01-discovery/tracking.md`. Refreshed by `skills/weekly-update`.

## North Star (lighthouse phase, 90 days)
**Products with a real factory quote obtained from a Factory Pack.** Count one per product (not per quote) when a real factory, not demo data, returns a price for that product's human-reviewed Factory Pack.
- **Outcome, not activity.** Lovable's North Star is "daily active apps": apps created, edited or published that day, not logins and not revenue (Elena Verna, `02_RECHERCHE/lovable.md`, Vidéo 1). Our "app that works" is a product a factory will price.
- **Not revenue:** lighthouse founders are non-paying until proof of value (`context/profile.md`); revenue would read 0 for weeks and hide progress.
- **Not packs exported or sign-ups:** a pack no factory quotes is a document, not a step to production. "Factory Pack exported" stays an activation input (`PRD.md` §6).
- **One number, three assumptions:** the founder handed over a real product (A3), the pack translated it well enough to be quoted (A1), a factory engaged (A4) (`PRD.md` §3.1).
- **Link to the company North Star** (`PRD.md` §6: units delivered on time and within spec, published from run 1): the quote is the first gate on that path. Switch to units delivered once the first production run starts.

Target: ≥ 3 by the end of the lighthouse (Hypothesis, derived: each of the "≥ 3 production runs started" in the Phase 1 exit needs a quote first, `PRD.md` §18).

## Wow, aha, habit
| Moment | Definition | State | Source |
|---|---|---|---|
| **Wow** | Prompt → product in 3D + unit cost at three volumes + factory shortlist on one screen, in ~20 s | Measured 18-24 s for the first version over several live runs; the shortlist is fictional demo data | `PRODUIT.md`, "Wow moment" |
| **Aha** | The founder sees **their own** product's landed-cost range and top risks (DFM or certification, component) | Not measured: no founder has seen a pack | `skills/pvp-pack`, `skills/pvp-teardown` |
| **Habit / retention** | Second design started in the Studio; pack handed to a factory; reorder or new SKU | Not measured | `PRD.md` §18 (PMF per side) |

Verna's frame: the aha moment, the steps to reach it, then the first habit loops, all engagement-based, "nothing to do with monetization" (`lovable.md`, Vidéo 1). Where it breaks: a hardware founder launches every 12-18 months (`02_RECHERCHE/lecons_inputs.md`), so habit means depth (second design, pack sent, reorder), not daily use.

## Input metrics (6-week plan)
Headline chain from the plan: **150 messages → 30 replies (20%) → 15 calls → 10 packs accepted → 3 production commitments** (deck slide 9; own targets, Hypothesis).
| # | Stage | Counted when | Target (own, Hypothesis) | Due | Where it is logged |
|---|---|---|---|---|---|
| 1 | Signals found | Account with a dated, sourced signal S1-S6 | ~150 accounts | W1 | `context/signals.md`, `03_DISCOVERY/comptes.csv` |
| 2 | Scored | `icp-scoring` run (urgency + points) | ~150; gate: < 100 → go deeper on the best 40 | W1 | `outputs/accounts.csv` |
| 3 | Messages | Sent by a human, one quoted signal, tagged with a hook | 150 (60 new in W1) | W0-W6 | `SUIVI.md`, `workflows/hook-experiments.md` |
| 4 | Replies | Any answer, after the follow-up | 30 (20%) | W0-W6 | `SUIVI.md` |
| 5 | Calls | 20-minute call held | 15 (8 in W2) | W0-W6 | `SUIVI.md` |
| 6 | Causes coded | One root-cause tag (`skills/call-debrief`) | ≥ 15 | W6 | `03_DISCOVERY/verbatims.md` |
| 7 | Packs delivered | Human-signed pack from a real prototype | 5 | W3 | `outputs/RUN_LOG.md` |
| 8 | Packs sent to a factory | Founder consent + NDA + pack sent | No count in the plan: every accepted pack that clears `playbooks/factory-intro.md` step 4 | W4 | `factory-intro.md` step 5 log |
| 9 | Quotes returned ≤ 5 working days | Real quote, no back-and-forth | ≥ 3 (= North Star) | W4-W5 | same |
| 10 | Paid commitments | Deposit or LOI | 3 (from 3-5 asks) | W5 | `SUIVI.md` |

## PMF signals per side
| Side | Signal | Target (Hypothesis) | Source |
|---|---|---|---|
| Founder | Second design started, or a pack handed to a factory | Tracked from W3, no count set | deck slide 9; `PRD.md` §18 |
| Founder | Named spend to intermediaries, then a deposit or LOI (A2) | 3 signed commitments at W5 | `PRD.md` §3.1, §17 |
| Factory | Quote returned from the pack without back-and-forth | ≤ 5 working days | `PRD.md` §18; `playbooks/factory-intro.md` |
| Factory | Capacity profile completed (A4) | 3 factories onboarded in W4 | `PRD.md` §3.1 |
| Kill | Cause coded cash or demand; a trusted Shenzhen contact who translates well; < 3 packs accepted | Per `PRD.md` §3 and §3.1 | `skills/reply-handler` maps objections to A1-A4 |

## Leading vs lagging
| Leading (weekly, steer on these) | Lagging (confirm, do not steer) |
|---|---|
| Reply rate per hook (`workflows/hook-experiments.md`) | Paid commitments (deposit, LOI) |
| Share of coded calls naming a translation cause (A1) | Production runs started (Phase 1 exit) |
| Packs accepted / offered (A3) | Units delivered on time and within spec (`PRD.md` §6) |
| Days from pack sent to quote; clarification rounds (A4) | On-time and defect rates, published per run |
| Intros given by founders (Verna's referral score idea, `lovable.md`) | Reorders, second SKU |

## What we do not measure yet
- **LTV.** "Unless you've been in the business for 5 years plus, you do not know your LTV. Period." (Verna, `lovable.md`, Vidéo 1). `PRD.md` §6 sets no LTV target.
- **CAC and paid acquisition.** Verna: "unless your conversion window is under 3 months… don't start with paid marketing" (same source). Our window from first message to a production order is unknown and likely longer (Hypothesis), so **no paid acquisition** while it is > 3 months or unknown. Revisit once 3 paid commitments give a first measured window.
- **Sign-ups, page views, logins:** nothing is public before Hexa's go; vanity after it unless tied to the funnel above.
