# Campaign 01: discovery

## Files behind this campaign
- **Drafts to send:** `03_DISCOVERY/envoi/A_ENVOYER.md`. It holds 36 drafts (#1-#23 from the enriched list, #24-#26 from the remaining accounts, #27-#36 new accounts found 27/09); #13 and #21-#23 have no direct contact, so about 32 are sendable. Warm-network track: `03_DISCOVERY/envoi/RESEAU.md`.
- **Live tracking:** `03_DISCOVERY/envoi/SUIVI.md` is the source of truth. `outputs/campaign-01-discovery/tracking.md` mirrors it with the signal table.
- **Follow-ups:** `03_DISCOVERY/envoi/RELANCE.md`, sent after 48 h without a reply, same channel and thread.
- **Verbatims:** `03_DISCOVERY/verbatims.md`.
- **Prep material:** `outputs/research/` (account cards) and `outputs/pvp/` (teardowns to offer after a call). Runs are listed in `outputs/RUN_LOG.md`.

**Window:** Saturday 26 to Monday 28 September 2026, before the deliverable is sent at noon.

## Objective
Settle **where hardware launches actually slip: design, components, certification, or the factory.**
- If founders mostly name design, components or certification, thesis v2 holds. That is what our desk coding suggests: 18 of 24 documented causes (`CLAUDE.md`).
- If they mostly name finding or managing a factory, the product should lean toward orchestration and sourcing, which is a crowded space (`context/competitors.md`).

## Target
**Update 27/09:** the drafts now cover 36 accounts (~32 sendable), 28 of them consumer electronics, the ECP chosen on 27/09 (`context/icp.md`, evolution log). A warm-network track runs in parallel (`03_DISCOVERY/envoi/RESEAU.md`, 10 people). The original target below is kept for reference.

The **top 30 of `outputs/accounts.csv`** are the 30 enriched rows, with scores from 5 down to 2. They split into two groups:
- **17 startups and small brands (prospects).** Priority goes to the synthesis top 10: The Minimal Phone, Pilet, Wordrunner, AIVELA, AERIONN, Halliday, SwiftShape, Circular Ring 2, Smokpub, GAMR (`02_RECHERCHE/parallel/00_SYNTHESE.md` §3).
- **13 established brands (verbatims only, not clients).** Examples: AWOL, KONKR/AYANEO, Creality, Hyper, eufyMake.

Contact each account through the channel in its `canal` column. Contact Circular Ring 2 in French.

## The 5 discovery questions
Translated from `03_DISCOVERY/messages.md`. All five are open questions, and none of them pitches.
1. Walk me through the last product you put into production, from idea to stock.
2. What took longer or cost more than planned?
3. How did you choose the factory, and what did you do to check it?
4. What went wrong on the first run?
5. How much did you pay intermediaries on this launch?

**Coding rule:** after each call, tag the main cause, with a single choice in the answers to questions 2 and 4 (run `skills/call-debrief`):
- design/engineering
- components
- certification
- factory
- logistics
- cash or demand (added 27/09 to match `RESEAU.md` and deck slide 9; either one is a kill-criterion signal)

Log the verbatim in `03_DISCOVERY/verbatims.md`.

## The two messages
Rules: no mention of Hexa or the project, honest introduction, no selling (`03_DISCOVERY/messages.md`). The full sequence and a worked example are in `skills/signal-to-sequence/SKILL.md`.

**Email**
> **Subject:** {Product}: your {update #n | month} update
> Hi {First name}, I read your {date} update on {Product}: "{exact quote of the signal}".
> I'm studying why hardware launches slip between prototype and mass production, and I'm talking to founders who have been through it. I'm not selling anything.
> Could you give me 20 minutes this week? I'd like to understand what actually took longer than planned: the design, the components, certification or the factory. Happy to share what I hear from the other founders in return.
> Orphéo Hellandsjo

**LinkedIn (300 characters max)**
> Hi {First name}, I read your {month} update on {Product} ({signal, 8 words max}). I'm studying why hardware launches slip after the prototype. Could I ask you 20 min about what really caused it? Not selling anything, and happy to share what other founders tell me.

## Success criteria
These are our own targets, not industry benchmarks. **Status 27/09: 0 sends logged in `SUIVI.md`**, so the Saturday-evening send target is not met on the log; the window closes Monday 28/09 noon.
| Metric | Target | Deadline |
|---|---|---|
| Personalised messages sent, each citing a sourced signal | 30 of 30 | Saturday 26 September, evening |
| Replies | 6 or more (20%) | Monday 28 September, noon |
| Calls held and coded by root cause | 3 or more | Monday 28 September, noon |
| Calls where the main cause is design, components or certification | at least 2 in 3 to confirm v2; at most 1 in 3 means revisit v2 | at the restitution |
| Founders who name an amount paid to intermediaries (question 5) | 2 or more | Monday 28 September, noon |

## Tracking
One row per signal type from `context/signals.md`. The live version, with counts per signal (36 drafts, warm track) and the update procedure, is in `outputs/campaign-01-discovery/tracking.md`, mirrored from `03_DISCOVERY/envoi/SUIVI.md`; per-signal results also feed the performance table in `context/signals.md`. The empty template is kept here for reference.

| Signal | Sent | Replies | Calls obtained |
|---|---|---|---|
| Estimated delivery date has passed | | | |
| Backer update mentioning the factory, molds, a failed sample or a manufacturer change | | | |
| Backer comments about production | | | |
| Pre-order extended or long stock-out | | | |
| Sourcing or supply-chain job posting at a small company | | | |
| New product announced | | | |
| **Total** | | | |
