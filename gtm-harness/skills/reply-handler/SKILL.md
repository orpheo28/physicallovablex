---
name: reply-handler
description: Classify each reply to an outreach message into one of five types, draft the answer within 2 hours with 2 time slots when relevant, map any objection to the kill criteria A1-A4, and update the send log.
---

# Reply handler

**When:** each time a reply arrives on a campaign, warm-track or PVP message. **Draft within 2 hours** of the reply (Hypothesis, our SLA: speed is the one thing a 1-person team can promise).
**Input:** the reply text, the account's row in `03_DISCOVERY/envoi/SUIVI.md`, the message it answers, and its hook tag (`workflows/hook-experiments.md`).
**Output:** one draft answer for a human to review and send, the log updates in step 5, and one line per batch in `outputs/RUN_LOG.md`. Nothing is sent by the agent. The call itself is run with `playbooks/founder-replied.md`.
**Reads:** `playbooks/founder-replied.md`, `context/personas/hardware-founder.md` (objections), `04_LIVRABLE/PRD.md` §3 and §3.1 (kill criteria, A1-A4), `03_DISCOVERY/messages.md` (rules).

## Step 1: classify (exactly one)
| Type | Looks like | Answer |
|---|---|---|
| **Interested** | "Happy to talk", "send it" (PVP), a question about the work | Thank, propose 2 slots, one line on what the 20 minutes cover. PVP yes → send the pack (labels on, fictional factories removed) and propose the slots |
| **Not now** | "Shipping this month", "ask me in January" | Thank, ask which date works, log the date; no other message before it |
| **Wrong person** | "Talk to my co-founder / our ops lead" | Thank, ask for an intro or permission to write; never guess an address |
| **Objection** | Pushback with a reason (table below) | Answer the objection truthfully in 2-3 lines, then offer one written question instead of a call |
| **No** | "Not interested", "stop" | Thank in one line, suppress for good (`workflows/signal-routing.md`, cooldowns) |

## Step 2: map objections to A1-A4
| Objection heard | Assumption it tests | Truthful answer | Log as |
|---|---|---|---|
| "The delay was cash / demand, not production" | A1, kill criterion | Thank; ask what would have helped | Kill signal, count in `call-debrief` terms |
| "My contact in Shenzhen handles it" | A1, kill criterion | Ask what the contact missed on the first run, if anything | Loss if nothing missed (`context/competitors.md`) |
| "Backers are patient, delay is fine" / "wouldn't pay for that" | A2 | No argument; ask what they paid intermediaries | A2 negative |
| "What would it cost?" | A2 (positive) | Pricing is not set; ask what they paid intermediaries on this launch | A2 positive signal |
| "I can't share my design" | A3 | NDA before any factory sees a pack; say the LLM data policy is not in place yet | A3 risk |
| "Which factories? Are they real?" | A4 | No factory network yet; demo factories are fictional; real factories come through intermediaries | A4 open |
| "Is this a sales pitch?" | none | Studying why launches slip, nothing to sell | Objection count |

## Step 3: draft
- 2-5 lines, same thread, same channel, same language as the reply.
- **Two slots**, 20 minutes, within 48 h, in the founder's time zone (Google Meet, deck slide 9). Example: "Would Tue 14:00 or Wed 17:00 (your time) work for 20 minutes?"
- No pitch, no price, no promise; never Hexa or the project name.

## Step 4: human QA
The human checks the type, the A1-A4 mapping and the slots against a real calendar, then sends.

## Step 5: log (after the human sends)
1. `03_DISCOVERY/envoi/SUIVI.md` first, the same hour: reply type, date, next step.
2. `outputs/campaign-01-discovery/tracking.md`, then the reply count on the signal row in `context/signals.md`.
3. The reply against its hook tag in `workflows/hook-experiments.md`.
4. Any objection: count it in `context/personas/hardware-founder.md` (Hypothesis → Observed, "(reply, <date>)").

## Output format
```
<Account> | hook <S#-H#-channel> | type: <one of 5> | A-map: <A1-A4 or none>
Draft: <text> | Slots: <2> | Log: SUIVI ✓ tracking ✓ signals ✓ hooks ✓
```
