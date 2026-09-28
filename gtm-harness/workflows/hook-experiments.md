# Workflow: hook experiments

How we learn which opening works. Every message carries a tag; every Sunday the reply rate per tag decides what changes. Run inside `skills/weekly-update` (step 2). Nothing here is automated; a human sends and logs. **All thresholds are Hypothesis (our choice)** except the 10% rule, which is the plan's (deck slide 9, W1 Sunday).

## Tag every message
Format: `<signal>-<hook>-<channel>`, e.g. `S2-H1-email`. The human adds it in a `hook` column of `03_DISCOVERY/envoi/SUIVI.md` when sending; the follow-up keeps the tag of the first message. Warm-track messages are tagged `W-<channel>`.

| Hook | Opening (wording in `context/signals.md` or the skill named) | Signals it fits |
|---|---|---|
| **H1** Cause question | Quote their update, ask what actually took longer (`skills/signal-to-sequence`, default) | S2, S1 |
| **H2** Date moved | "Your ship date moved from {A} to {B}. What took longer than planned?" | S1 |
| **H3** Still on pre-order | "Your page still says {exact words} after {promised date}." | S4 |
| **H4** Next product | "After {product 1}, what are you doing differently on {product 2}?" | S6 |
| **H5** Job post | "You are hiring for {role}: what should that person fix first?" | S5 (untested) |
| **H6** PVP offer | "I sketched the production path for {Product}: want it?" (`skills/pvp-pack`) | S1 + S2 |

New variant = new ID (H1b, H7…), registered here before the first send. Change **one variable at a time**: signal wording, channel or language (deck slide 9).

## Weekly read (Sunday)
1. Count per tag from `SUIVI.md`: sent, replies **after the follow-up** (≥ 48 h after it), calls.
2. Fill one row per tag below. Judge a tag only with **≥ 10 sends** (same floor as `skills/weekly-update`).
3. Apply the decision rule, then log the learning.

## Decision rule
| Reply rate after follow-up | Decision |
|---|---|
| **< 10%** | **Change the hook, not the volume** (deck slide 9): keep the send count, swap one variable, give the new ID ≥ 10 sends |
| 0 replies on ≥ 10 sends | Retire the hook for that signal |
| 10-19% | Keep; test one variant alongside |
| ≥ 20% (the plan's reply target, `context/metrics.md`) | Make it the default for that signal |
| Replies but 0 calls on ≥ 5 replies | The hook attracts the wrong reply: check the ask, not the opening |

## Results (state 27/09: nothing sent)
| Week | Tag | Sent | Replies after follow-up | Reply rate | Calls | Decision |
|---|---|---|---|---|---|---|
| W0 | all | 0 | 0 | — | 0 | none yet |

## Learnings log
One line per decision, newest first. Mirror a learning into `context/signals.md` (hook column) once it holds for two weeks.
| Date | Tag(s) | What we saw (counts) | What we changed |
|---|---|---|---|
| — | — | Fill from the first Sunday read | — |
