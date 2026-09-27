# Playbook: a founder replied

**Trigger:** any reply to a campaign message or a warm-track message. Log the reply in `03_DISCOVERY/envoi/SUIVI.md` first, the same hour.

## Step 1: read the reply type
| Reply | Action |
|---|---|
| **Yes / "happy to talk"** | Step 2 today |
| **"Ask me by email"** | Send the one written question from the follow-up in `skills/signal-to-sequence`; code the answer like a call (step 4) |
| **"Not now"** | Thank them, ask if a later date works, log; no further message unless they propose one |
| **"No" / no interest** | Thank them, log, never contact again |
| **"Who are you / what is this for?"** | Answer truthfully: you are studying why hardware launches slip between prototype and production; nothing to sell. If asked whether you are building something, say you are exploring whether a tool could help, without naming the project or Hexa (`03_DISCOVERY/messages.md`) |
| **Referral to someone else** | Thank them, write to the person named with the referrer's permission, log as warm |

## Step 2: book the call (same day)
- Offer two or three 20-minute slots within 48 h, Google Meet (deck slide 9).
- Mark "Call booked" in `SUIVI.md`, then `outputs/campaign-01-discovery/tracking.md`.

## Step 3: prepare (15 min)
- Read or run `skills/account-research`: the sourced problem, the root-cause guess, the angle, what not to say.
- Have the `skills/pvp-teardown` page ready if one exists (`outputs/pvp/`), but do not send it before the call.
- Re-read the founder persona objections (`context/personas/hardware-founder.md`).

## Step 4: run the call (20 min, listen more than talk)
The 5 questions (`outputs/campaign-01-discovery/brief.md`), in order, all open:
1. Walk me through the last product you put into production, from idea to stock.
2. What took longer or cost more than planned?
3. How did you choose the factory, and what did you do to check it?
4. What went wrong on the first run?
5. How much did you pay intermediaries on this launch?
Then, if time allows, the qualification questions in `context/icp.md`. No pitch, no demo unless they ask.

## Step 5: after the call
- Within 30 min: write the entry in `03_DISCOVERY/verbatims.md`, then run `skills/call-debrief` (one root-cause tag, harness updates).
- Give value: send the teardown (`skills/pvp-teardown`) to anyone who took a call. Offer a free human-reviewed Factory Pack only if they named a translation blocker (design, components, certification or the factory's language) (deck slide 9, W2).
- Ask for one intro to another hardware founder.
- Blocker named is cash or demand → log it; it counts toward the kill criterion (deck slide 12).
