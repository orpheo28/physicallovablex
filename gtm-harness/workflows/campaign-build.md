# Workflow: campaign build

From audience to review, for any new campaign after campaign 01. Phases adapted from the GTM repository (credits in `README.md`). Two-person pre-seed: Orphéo (O) owns every phase; the agent drafts, a human decides and sends.

## Phase 1: audience (30 min)
- One segment, one signal family, one offer (1 ICP + 1 offer + 1 channel, deck slide 8).
- Pull accounts from `03_DISCOVERY/comptes.csv` with `skills/icp-scoring`: tier 1-2, bucket HOT or WARM, not suppressed (`workflows/signal-routing.md`).
- Required fields per account before it enters: `workflows/enrichment.md`, "Ready to draft".
- If fewer than ~30 accounts qualify, go deeper on the best ones rather than loosening the filter (deck slide 9, W1 rule).

## Phase 2: brief (20 min)
Create `outputs/YYYY-MM-DD-campaign-<name>/brief.md` with: objective (the one question the campaign settles), target and count, signal(s), channel, the 5 discovery questions, success criteria with dates (our own targets, labelled as such), and links to the drafts file and the log. Campaign 01 is the model (`outputs/campaign-01-discovery/brief.md`).

## Phase 3: sequence (per account)
Run `skills/signal-to-sequence`: email (≤ 90 words), LinkedIn note (≤ 300 characters), one follow-up at 48 h in the same thread. Drafts go in `03_DISCOVERY/envoi/` (contacts stay outside the harness).

## Phase 4: human QA gate (nothing leaves before this)
- [ ] The quoted sentence is copied from a source reopened by a human, with URL and date; snippet-only signals are not quoted.
- [ ] No Hexa, no project name, no pitch, no promise, no mention of backer anger (`03_DISCOVERY/messages.md`).
- [ ] Value test passed: without the ask, the message still gives something.
- [ ] Every ⚠️ in the draft is resolved or the message is dropped.
- [ ] Right language (French for Paris founders), right channel, founder name checked on a public page.
- [ ] The first 50 messages of any campaign are read and sent by hand, no tool (GTM Strategist, "Craft Irresistible Outbound Campaigns Using Claude Code", `04_LIVRABLE/GTM_Lessons_Substack_MajaVoje.md`).

## Phase 5: send (human only)
O sends by hand from their own accounts and logs each send in `SUIVI.md` the same hour. No sending tool, no automation, no API key in this repo.

## Phase 6: review
| When | What to read | Decision rule (our own, deck slide 9) |
|---|---|---|
| **48 h** after each send | Replies; who gets the follow-up | Send the `RELANCE.md` follow-up to every non-reply, same thread |
| **7 days** after the batch | Reply rate after follow-up, calls booked, tags coded | < 10% replies after follow-up → change the hook (signal wording, channel, language), not the volume. List < 100 → go deeper on the best 40 |
| **End of campaign** | Tags vs success criteria in the brief | Keep, change or kill; write one row in `context/icp.md` evolution log if the segment or signal changes |

Record the results table in the campaign's `tracking.md` and the per-signal counts in `context/signals.md`.
