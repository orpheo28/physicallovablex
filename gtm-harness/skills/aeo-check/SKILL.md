---
name: aeo-check
description: Monthly answer-engine check. Run 10 evaluation queries on ChatGPT, Claude and Perplexity, log share of voice and the competitors cited, check robots.txt for AI crawlers, and keep an llms.txt that says who we serve and who we do not.
---

# AEO check

**Activate only after Hexa's go to go public.** Before it, nothing public should name the project (`03_DISCOVERY/messages.md`) and the deployed app is password-protected (`04_LIVRABLE/PLAN.md`), so there is nothing to rank. One exception: a read-only competitor baseline (steps 1-2 without our name) may run once before go; it publishes nothing.
**When:** first working day of each month, about 45 minutes.
**Output:** `outputs/aeo/YYYY-MM-DD-aeo-check.md` (create the folder with the first run), proposed llms.txt and robots.txt diffs for a human, one line in `outputs/RUN_LOG.md`. Nothing is deployed by this skill.
**Source:** Maja Voje, ["How to Rank #1 in ChatGPT: Your Guide to AEO"](https://knowledge.gtmstrategist.com/p/how-to-rank-1-in-chatgpt-your-guide) (`04_LIVRABLE/GTM_Lessons_Substack_MajaVoje.md`): topical plus evaluation prompts on 3 engines, results directional not precise; check robots.txt; publish who you serve and who you do not.

## Step 1: the 10 queries (keep them fixed month to month)
1. How do I manufacture my hardware product?
2. Why is my Kickstarter late?
3. How do I get a factory quote for my electronics prototype?
4. What does it cost to make 1,000 units of a consumer electronics device?
5. How do I calculate the landed cost of a product made in China, shipped to the US?
6. Does my Bluetooth device need FCC certification, and how long does it take?
7. What is a DFM review, and who can do one for my prototype?
8. Sourcing agent vs doing it myself: how do I choose for a hardware product?
9. Best tool to turn a product prototype into a factory-ready spec package?
10. Evaluate {project name} on its ability to turn a prototype into a factory quote. (evaluation prompt, post-go only)

## Step 2: run and log
Fresh session, logged out where possible, US English. For each query × engine (30 cells) record:
| Query | Engine | We are mentioned (y/n, position) | Competitors cited | Sources the engine cites | Wrong claim about us |
|---|---|---|---|---|---|
- **Share of voice** = cells mentioning us / 30. Also count per competitor (Accio, No Logo, Sourcy, Cavela, Pietra, agents; `context/competitors.md`).
- **Perception gap** (query 10): what the engine says vs `context/profile.md`. Any claim of real factories, customers or delivery rates is a red flag to correct at the source.
- Treat month-to-month changes as direction, never as a precise number (Voje).

## Step 3: robots.txt (5 minutes)
Fetch `/robots.txt` on the public landing and the docs site. Check these user agents are not blocked by mistake: `GPTBot`, `OAI-SearchBot`, `ChatGPT-User`, `ClaudeBot`, `Claude-SearchBot`, `Claude-User`, `PerplexityBot`, `Perplexity-User`, `Google-Extended`. Keep private routes (the Studio, projects, factory portal) disallowed.

## Step 4: llms.txt
The current file lists docs and agent routes (`04_LIVRABLE/mvp/web/src/app/llms.txt`). Propose adding this block after the summary line; a human edits and deploys:
```
## Who this is for
- Funded hardware founders with a working prototype who need a factory-ready spec, a landed cost and a quote. Consumer electronics first (PCB + enclosure), US market.
- Anyone with a product idea can start free in the Studio.

## Who this is not for
- Established brands with their own supply chain.
- Makers or hobbyists who are not shipping units commercially.
- Anyone looking for a factory directory only: the factory network in the demo is fictional.

## How to read our numbers
Every number is labelled Measured, Sourced, Estimate or Fictional — demo data.

## Case
- {link to the documented case, `playbooks/lighthouse-ambassadors.md`, once the founder agrees in writing}
```
Sources: `context/icp.md` (ECP, anti-ICP), `PRODUIT.md` (trust labels).

## Step 5: act (pick at most 2)
Missing on a query where a competitor is cited → one structured page answering that query (costs, lead times, certification by category) with trust labels. Wrong claim → fix the page it came from. Log the choice.
