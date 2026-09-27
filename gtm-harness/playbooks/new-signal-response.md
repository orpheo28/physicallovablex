# Playbook: new signal response

**Trigger:** a new public, dated signal on a hardware account (a creator update naming a cause, a moved ship date, a "shipping soon" page past its date, a next product announced). Step format adapted from the GTM repository (credits in `README.md`). Routing rules: `workflows/signal-routing.md`.

## Step 1: validate (5 min)
- Open the source yourself. Copy the exact sentence, the URL and the date.
- Is it production (S1, S2, S4, S6) or logistics only? Logistics only → log and stop (`context/signals.md`).
- Page blocked (403)? Note it, find another public page, and do not quote a snippet (`workflows/enrichment.md`).

## Step 2: dedupe and suppress (2 min)
- Already in `03_DISCOVERY/comptes.csv` or `SUIVI.md`? Contacted, replied or declined → follow `signal-routing.md` step 1.
- Established brand → Tier 4, verbatim ask only.

## Step 3: score (5-10 min)
Run `skills/icp-scoring` on the account: urgency 1-5, points with decay and bonus, bucket, tier. Write the arithmetic.

## Step 4: respond by bucket
| Bucket | Response | Deadline |
|---|---|---|
| **HOT ≥ 60** | `skills/account-research` card → `skills/signal-to-sequence` drafts → QA gate → human sends | Within 48 h of finding the signal |
| **WARM 40-59** | Same, only if the signal has a quotable sentence; otherwise add to the weekly re-check | Next send batch |
| **COLD 20-39** | Add to `comptes.csv` with the signal; re-check weekly for a stronger signal | — |
| **SKIP < 20** | Log the reason in `notes` | — |

## Step 5: the first touch
- Quote their sentence, name the bucket you think it is in as a question ("was it the design, the components, certification or the factory?"), ask for 20 minutes, say you sell nothing.
- One signal per message. English, or French for Paris founders.
- Already contacted with no reply and the follow-up is due? Use the new signal in the `RELANCE.md` follow-up instead of a new thread.

## After the first touch
- Log the send in `SUIVI.md`, mirror it into `outputs/campaign-01-discovery/tracking.md` and the signal's row in `context/signals.md`.
- Reply → `playbooks/founder-replied.md`. No reply after 48 h → one follow-up, then the cooldown in `signal-routing.md`.
