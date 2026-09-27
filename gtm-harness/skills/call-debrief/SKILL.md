---
name: call-debrief
description: Turn one discovery call into a synthesis with exactly one root-cause tag, then update the signal performance table, the ICP evolution log (when a pattern appears) and the persona objections. Never stores a raw transcript.
---

# Call debrief

**When:** within 30 minutes of each call (`03_DISCOVERY/envoi/RESEAU.md`; deck slide 9).
**Input:** the human's notes and the key verbatim, already written in `03_DISCOVERY/verbatims.md` (template there). No recording, no transcript file.
**Output:** `outputs/debriefs/YYYY-MM-DD-debrief-<account>.md` (one page, format below) plus the updates in step 4. Create the folder with the first debrief. Add one line to `outputs/RUN_LOG.md`.

## Privacy
- Never paste or store a transcript. Keep at most two short verbatim quotes (one or two sentences each) and synthesise the rest.
- Cold-track accounts: the company or product name is fine. **Warm-track calls:** anonymise as "warm-track founder, <category>". Never write a person's name, email or phone from `RESEAU.md` into the harness.
- A BOM or file shared in the call stays out of the repo.

## Steps
1. **Read** the entry in `verbatims.md`, the account's research card (`outputs/research/`) and its row in `tracking.md`.
2. **Answer the 5 questions** in one line each, from the notes only (questions in `outputs/campaign-01-discovery/brief.md`).
3. **Tag exactly one root cause** from the answers to questions 2 and 4:
   `design/engineering` · `components` · `certification` · `factory` · `logistics` · `cash` · `demand`.
   If the founder names two, pick the one that cost the most time and note the second as "secondary". `cash` or `demand` is a kill-criterion signal (deck slide 12): flag it at the top.
4. **Update the harness** (propose, then apply after the human confirms):
   - `context/signals.md`, performance table: +1 call on the account's signal row; +1 in the last column if the tag is design/engineering, components or certification.
   - `outputs/campaign-01-discovery/tracking.md`: "Main cause" column (after `SUIVI.md`).
   - `context/personas/hardware-founder.md`: add or count any objection heard; move it from Hypothesis to Observed with "(call, <date>)".
   - `context/competitors.md`, win/loss log: any alternative the founder uses instead.
   - `context/icp.md`, evolution log: only when a pattern appears (the same tag, segment or objection in 3+ calls), with the count.
5. **Next step for the founder:** follow `playbooks/founder-replied.md` step 5 (teardown or free human-reviewed Factory Pack only if they named a translation blocker).

## Output format
```
# Debrief: <account or "warm-track founder, <category>"> (<date>)
Signal that got the call: <S1-S6 or warm>
Root cause: <one tag> (secondary: <tag or none>) | Kill-criterion flag: yes/no
Q1-Q5: <one line each>
Paid to intermediaries: <amount + what for, or "not stated">
Verbatim (≤ 2 short quotes): "<...>"
Objection(s): <...>
Alternative used: <agent / contact in Shenzhen / none / ...>
What it changes: <one sentence for icp.md or CLAUDE.md, or "nothing yet">
Next step: <teardown offered / pack offered / intro asked / none>
```

## Restitution
After 3 coded calls, compare the tags with the success criteria in `brief.md`: ≥ 2 in 3 design, components or certification keeps thesis v2; ≤ 1 in 3 means revisit it (`CLAUDE.md`).
