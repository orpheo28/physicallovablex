---
name: pvp-pack
description: Permissionless value. From a lead's public product (e.g. a late Kickstarter campaign), run the Studio, pull the 3 most useful findings with trust labels, and draft a message that offers the production-path sketch instead of attaching it.
---

# PVP pack

**Input:** one scored lead (HOT or WARM, Tier 1 in `context/icp.md`) with its public product: campaign or product page, public specs, teardown photos, creator updates. Public sources only (`workflows/enrichment.md`); never a founder's private file.
**Output:** `outputs/pvp/YYYY-MM-DD-pvp-pack-<product>.md` (prompt, run cost, 3 findings, draft), and the draft message in `03_DISCOVERY/envoi/A_ENVOYER.md` for a human to review and send. One line in `outputs/RUN_LOG.md`. Nothing is sent by the agent.
**Reads:** `context/signals.md` (hook H6 in `workflows/hook-experiments.md`), `context/positioning.md` (guardrails), `skills/pvp-teardown` (landed-cost method), `skills/signal-to-sequence` (outreach rules), `04_LIVRABLE/PRODUIT.md` (trust labels, what is fictional).

## Rules
- **Offer, never attach.** No unsolicited file, link or screenshot. The pack goes out only after the founder says yes.
- **Trust label on every number:** Measured / Sourced / Estimate / Fictional — demo data (`PRODUIT.md`). Landed cost is always an **Estimate** range with its method.
- **Factories in the MVP are fictional.** Never cite a factory, quote, capacity or lead time from the run in the message; label them "Fictional — demo data" in anything sent later, or remove them.
- Never mention Hexa, the project name or the Studio's name; strip branding from anything sent (`03_DISCOVERY/messages.md`).
- **Cost cap: $0.50 of LLM spend per lead** (Hypothesis, our choice: one Make it ≈ $0.34 in one run, a refine ≈ $0.01, `PRODUIT.md`). Stop and ask the human beyond it. The shared key has a hard cap of $10 (`04_LIVRABLE/PLAN.md`, "Budget"); 20 live runs per IP per day (`04_LIVRABLE/mvp/README.md`).
- The concept CAD is built from public specs, not their design: say so ("from your public specs").

## Steps
1. **Gate.** Account passes `workflows/signal-routing.md` steps 1-3 (dedupe, suppress, score) and has a quotable S1 or S2 sentence. Not contacted in the last 30 days.
2. **Write the Studio prompt** ("I have a prototype" mode):
   ```
   I have a prototype. {Product}: {one line from the campaign page}.
   Public specs ({URL}, {date}): {size, weight, battery, display, radios, sensors, materials}.
   Public parts only: {chip or module named in updates or teardowns}. Mark every other part as an assumption.
   Market: US (FCC). Retail or pledge price: ${…}. Volumes: 500 / 2,000 / 10,000.
   ```
3. **Run it.** Studio UI in prototype mode, or the API (`04_LIVRABLE/mvp/README.md`: create the project, autorun, poll). Run to the wow screen and stages 4-6 first; add Make it only if the landed cost needs duties and freight. Log the actual spend.
4. **Extract 3 findings**, each with its label and source:
   - **Landed-cost range** (Estimate): FOB range at 2,000 units → landed, method stated; cross-check with the `pvp-teardown` formula and the HTS line (Sourced).
   - **Top DFM or certification risk:** e.g. FCC Part 15 intentional radiator for a BLE device (Sourced from the certification map), or a wall-thickness warning (Measured on the concept CAD, so "check on your design").
   - **Top component risk:** LCSC stock or price for the named part (Sourced, snapshot date), single source, lead time.
   Drop any finding that is generic or that the founder's own update already states.
5. **Human check.** O (or the signing engineer once recruited, deck slide 9) reads the 3 findings. If one would not survive the founder's scrutiny, drop it; with fewer than 2 left, do not send.
6. **Draft the message** (same thread rules as `signal-to-sequence`; tag `S#-H6-<channel>`):
   ```
   Subject: {Product}: the production path, sketched

   Hi {First name}, I read your {date} update on {Product}: "{exact quote}".
   I study why hardware launches slip between prototype and production, and I'm
   not selling anything. From your public specs I sketched the production path
   for {Product}: a landed-cost range, one component risk, and the step I'd watch
   first: {top risk in one line, no number}.
   It's rough, public info only, every number labelled. Want it?
   ```
   Value test: delete "Want it?". The named risk must still be useful on its own.

## Output format
```
# <Product>: PVP pack (<date>)
Signal: <S#, URL, date, quote> | Prompt: <block> | Run: <stages, spend $…>
1. Landed cost [Estimate]: $…–… per unit at 2,000. Method: …
2. <DFM or certification> [Measured | Sourced]: … (<source>)
3. <Component> [Sourced, LCSC <date>]: …
Removed from anything sent: factory shortlist, quotes, lead times (Fictional — demo data)
Draft: <message> | Human check: <name of role, date>
```
A "yes, send it" is logged as a reply; it is not A3 (A3 = the founder hands over their real product, `PRD.md` §3.1).
