# Run log

One line per skill run. Date is the run date. "Human must check" is what I could not verify myself.

**File naming (from 27/09):** new output files are named `YYYY-MM-DD-[type]-[name].md` (types: research, pvp, scoring, debrief, campaign), inside the existing folders (`research/`, `pvp/`, `debriefs/`) or at the root of `outputs/` for scoring runs and campaign folders. **Index of files created before 27/09 (not renamed):** `research/the-minimal-phone.md`, `research/pilet.md`, `research/wordrunner.md` (2026-09-26, research); `pvp/halliday.md`, `pvp/wordrunner.md` (2026-09-26, pvp); `campaign-01-discovery/` (2026-09-26, campaign; would be `2026-09-26-campaign-01-discovery/`); `accounts.csv` (copy of `03_DISCOVERY/comptes.csv` before batch 3). Harness changes that are not skill runs go in `weekly-log.md`.

| Date | Skill | Input | Output file | What a human must still check |
|---|---|---|---|---|
| 2026-09-26 | pvp-teardown | Halliday G1 (campaign URL, Engadget and CNX specs; G2 for the ship date) | `outputs/pvp/halliday.md` | The 20-35% FOB-to-retail ratio is my assumption. HTS code and duties not done. Whether G2 has shipped (the 2026-09-15 date is unsourced). |
| 2026-09-26 | pvp-teardown | Wordrunner (product page, press) | `outputs/pvp/wordrunner.md` | Current price ($379, $459 or $500). Same 20-35% assumption. The $8,000-80,000 die-cast tooling range comes from an unidentified search snippet. HTS code and duties not done. |
| 2026-09-26 | account-research | The Minimal Phone (A_ENVOYER #1) | `outputs/research/the-minimal-phone.md` | The screen-sensor cause rests on a search summary (page timed out). Minimal Phone 2 shipping "December" is unsourced. Decide whether Phone 2 may now be cited. |
| 2026-09-26 | account-research | Pilet (A_ENVOYER #2) | `outputs/research/pilet.md` | No creator sentence retrieved (Kickstarter 403). Display-from-scratch detail is from a search summary of Hackster. Update #22 unverified. |
| 2026-09-26 | account-research | Wordrunner (A_ENVOYER #3) | `outputs/research/wordrunner.md` | Root cause is "not stated". Reopen the Kickstarter updates and the Reddit post by hand. Check the ship date on the live page. |
| 2026-09-27 | (harness upgrade, not a skill run) | Maja Voje's GTM repository article, KarlRaf/gtm-starter-kit | context, skills, workflows, playbooks, README (see `weekly-log.md`) | Signal points, decay and bonuses are my design choices; signal coding of drafts #24-#36 is mine; `accounts.csv` (45 rows) lags `comptes.csv` (55). |

Kickstarter returned 403 on every attempt, so no creator update was read directly in any run.
