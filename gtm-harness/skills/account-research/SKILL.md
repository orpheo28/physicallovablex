---
name: account-research
description: For one hardware account, find its precise, sourced production problem, classify the root cause (design, components, certification, factory, logistics) and derive the angle of approach.
---

# Account research

**Input:** one account, either a row of `outputs/accounts.csv` or a name plus URL.
**Output:** a card of about 15 lines, in the format below, saved as `outputs/research/YYYY-MM-DD-research-<account>.md` (cards from 26/09 keep their old names). Every fact has its URL and date. Anything without a source is labelled **Hypothesis**. Add one line to `outputs/RUN_LOG.md`.
**Reads:** `context/icp.md` (tiers, anti-ICP), `context/signals.md` (points, decay), `context/personas/hardware-founder.md` (objections, hooks), `workflows/enrichment.md` (allowed sources, 403 handling).

## Steps
1. **Start from what we know.** Read the account's row in `outputs/accounts.csv`: `signal`, `notes`, sources and confidence.
2. **Find the latest primary source.**
   - Creator updates: `/posts` on Kickstarter, `/updates` on Indiegogo, the brand blog.
   - Then press coverage and tracker sites (Kicktraq, Makers101).
   - Then backers: comments, Trustpilot, BBB, Reddit.
   - Quote the exact sentence where the creator names the problem.
3. **Pin the problem down.** Write *what* failed, *when* and *how many units* were affected. For example, AIVELA: "About half of the units made in that batch passed final checks… the rest were held back due to component quality issues" ([source](https://gadgetsandwearables.com/2026/02/12/aivela-ring-pro-shipping/), 12/02/2026).
4. **Classify the root cause into exactly one bucket**, adding a second only if the source names two:
   - `design/engineering`: redesign, DFM, tuning
   - `components`: shortage, price, quality
   - `certification`: FCC, CE, safety
   - `factory`: process, language, capacity
   - `logistics`
   This is the variable campaign 01 must settle (`outputs/campaign-01-discovery/brief.md`).
5. **Map the people.** Name the founder and CEO, the engineering co-founder if there is one, and the public channel. A LinkedIn profile or email must come from a public page. Write the channel *type* in the card (email, LinkedIn, platform message); the address itself stays in `03_DISCOVERY/`, never in the harness.
6. **Check what is next.** Look for a next product or new campaign. An unverified rumour stays **Hypothesis**; see the Minimal Phone 2 in `02_RECHERCHE/parallel/00_SYNTHESE.md`.
7. **Derive the angle.** Pick the question from `brief.md` that fits the root cause. Examples:
   - components: "How did you choose and qualify that component?"
   - factory: "How did you and the factory agree on the spec?"

## Output format
```
## <Account>: score <n> (<rubric reason>) | Priority <points> (<HOT/WARM/COLD/SKIP>) | Tier <1-4>
Problem: <what failed, when, units>. "<exact quote>" (<URL>, <date>)
Root cause: <bucket> | Confidence: high/medium
People: <founder, role> (<URL>); engineering co-founder: <name or "none found">
Channel: <email / LinkedIn / platform message>
Next product: <fact + URL> or "Hypothesis: …"
Angle: <one sentence tying their signal to one discovery question>
Do not say: <anything unverified, or anything that sounds like a pitch>
```

## Rules
- Never guess the cause from the product category. If the source does not say, write `cause: not stated`. Seven of the 30 enriched accounts are in that case (`CLAUDE.md`).
- Established manufacturers (see `context/icp.md`, Anti-ICP) get a card marked "verbatim source, not client".
