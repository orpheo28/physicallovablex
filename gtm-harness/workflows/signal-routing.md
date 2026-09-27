# Workflow: signal routing

What happens when a signal fires, from detection to the log. Decision-tree format adapted from the GTM repository (credits in `README.md`). Every step is run by a person or by Claude Code on request; nothing here is automated, and only a human sends.

## Where signals come from
Manual detection only, on the public sources in `workflows/enrichment.md`: campaign updates and comments, product pages, press, Wayback. Cadence: a full re-run on Tuesday of each week (deck slide 9, W1 day plan); a re-check of every drafted account's latest update before its message is sent.

## Decision tree
```
Signal found on account X (URL + date + exact wording)
│
├─ 1. Dedupe: is X already in 03_DISCOVERY/comptes.csv or SUIVI.md?
│     ├─ Contacted < 7 days ago, no reply → no new message; attach the signal to the RELANCE.md follow-up
│     ├─ Replied or declined → no outreach; add the signal to the account's notes
│     └─ Known, never contacted → go to 2 with the new signal
│
├─ 2. Suppress
│     ├─ Established brand with its own supply chain → Tier 4: verbatim ask only, never a sales angle
│     ├─ Logistics-only delay, or cause is demand/cash only → log, no outreach (context/signals.md)
│     ├─ No public channel to the founder → hold; look for one (enrichment.md)
│     └─ Signal only from a search snippet (403) → keep, points × 0.5, never quoted
│
├─ 3. Score (skills/icp-scoring): urgency 1-5, priority points with decay and bonus, tier
│     ├─ HOT ≥ 60  → 4 within 48 h
│     ├─ WARM 40-59 → 4 if a fresh quotable sentence exists, else monitor
│     ├─ COLD 20-39 → monitor; re-check on the weekly run
│     └─ SKIP < 20 → archive with reason
│
├─ 4. Research (skills/account-research): card with sourced problem, one root-cause bucket, angle
│
├─ 5. Draft (skills/signal-to-sequence) → A_ENVOYER.md
│
├─ 6. Human approves (QA gate in workflows/campaign-build.md): every ⚠️ resolved or the message dropped
│
├─ 7. Human sends by hand (email, LinkedIn, platform message)
│
└─ 8. Log: SUIVI.md → outputs/campaign-01-discovery/tracking.md → context/signals.md performance
       Reply? → playbooks/founder-replied.md. No reply after 48 h → RELANCE.md follow-up, same thread.
```

## Cooldowns (Hypothesis, our choice)
- One follow-up only, ≥ 48 h after the first message (`03_DISCOVERY/envoi/RELANCE.md`).
- After the follow-up, no new message for 30 days unless a new S2 or S6 signal fires.
- Never message a founder who said no.

## Weekly decay check (part of `skills/weekly-update`)
1. For every scored account, recompute points with today's date (decay table in `context/signals.md`).
2. Re-open the live product page for S4 accounts and the latest update for S1: a fully shipped product loses S1 and S4.
3. List bucket changes for the human; do not downgrade an account with an open conversation.
