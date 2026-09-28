---
name: weekly-update
description: Find the stale sections of the harness, draft the updates from what the repo and the discovery files already say, ask the human for what the agent cannot know, then log the run in outputs/weekly-log.md.
---

# Weekly update

**When:** every Sunday evening (end of each week in deck slide 9), and after any day with sends or calls while a campaign is live. About 15 minutes.
**Input:** the current repo plus the discovery files it mirrors.
**Output:** proposed edits (current vs proposed), applied only after the human confirms, and one row in `outputs/weekly-log.md`. Structure adapted from the GTM repository weekly-update skill (credits in `README.md`).

## Reads
1. `CLAUDE.md`: "Current priorities" and its date.
2. `context/signals.md`: performance table; `context/icp.md`: evolution log; `context/competitors.md`: win/loss log; `context/personas/*.md`: objections.
3. `outputs/campaign-01-discovery/tracking.md` (and any `outputs/YYYY-MM-DD-campaign-*/`), `outputs/RUN_LOG.md`, `outputs/weekly-log.md`.
4. Sources of truth outside the harness: `03_DISCOVERY/envoi/SUIVI.md`, `RESEAU.md` (counts only), `03_DISCOVERY/verbatims.md`, `03_DISCOVERY/comptes.csv`.

## Step 1: staleness check (print the list before drafting)
| File / section | Stale if |
|---|---|
| `CLAUDE.md`, Current priorities | Older than 7 days, or a priority is done |
| `tracking.md` | Differs from `SUIVI.md` (any sent, reply or call not mirrored) |
| `signals.md`, performance table | Counts differ from `tracking.md`, or a coded call is missing |
| `icp.md`, evolution log | 5 new coded calls since the last entry, or 30 days |
| Personas, objections | An objection heard in 2+ calls is not in the table |
| `competitors.md`, win/loss log | A call named an alternative (agent, "contact in Shenzhen", No Logo…) not logged |
| `outputs/accounts.csv` | Row count differs from `03_DISCOVERY/comptes.csv` (45 vs 55 on 27/09) |
| Signal decay | A drafted or scored account crossed a decay step (30, 90, 180, 365 days) or has fully shipped |

## Step 2: draft each stale section
Use this block per section:
```
### <file> — <section>
Last updated: <date> | STALE: <reason>
CURRENT: <existing lines>
PROPOSED: <draft, every number traced to SUIVI.md, verbatims.md or a URL>
QUESTIONS FOR THE HUMAN: <what the repo cannot know>
```
Order: priorities, tracking, signal performance, decay re-check, ICP log, personas, competitors.
- **Signal performance:** count sends, replies and calls per signal from `tracking.md`. Flag any signal with 10+ sends and 0 replies: change the hook, not the volume (deck slide 9, W1 rule).
- **Hook experiments:** fill the weekly row per hook tag and apply the decision rule in `workflows/hook-experiments.md`; refresh the funnel state line in `context/metrics.md`.
- **Decay:** list accounts whose bucket changes (HOT → WARM…). Never downgrade an account with an open conversation.
- **Competitors and ICP:** draft only from a coded call or a sourced fact. Otherwise just ask.

## Step 3: confirm, apply, log
Show all proposals in one message. Apply only what the human confirms. Then add one row to `outputs/weekly-log.md`:
`| YYYY-MM-DD | <files changed> | <most significant change, one sentence> |`

## Rules
- Invent no performance data. If a number is not in `SUIVI.md` or `verbatims.md`, ask for it.
- Copy counts, never names, from `RESEAU.md`.
- Nothing is sent, published or pushed by this skill.
