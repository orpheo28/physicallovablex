# CLAUDE.md: PhysicalLovableX GTM harness

## What PhysicalLovableX is
A working name for an idea Hexa WTF is scoping. It is not a launched company. The concept is AI infrastructure that turns an idea into a manufactured, shipped product: design, specs, factory matching across a curated network of Chinese manufacturers (a "production MCP" for factory capacity), tooling, QC, logistics and financing. Source: `00_ENONCE.md`.

## Thesis v2
> "The bottleneck in hardware is neither design nor the factory. It's the translation between the two: making a product manufacturable, choosing components, passing certification, and speaking the factory's language. That's where launches slip, and that's where AI actually helps."

**Evidence**
1. **Most delays come from engineering, components and certification, not from access to a factory.** I coded the documented cause of delay for the 30 enriched accounts in `outputs/accounts.csv`:
   - engineering or redesign: 8
   - components: 7
   - certification: 3
   - factory or supplier: 3
   - logistics: 3
   - no stated cause: 7
   (One account has two causes.) Examples: Pilet moved to the Raspberry Pi CM5 ([c33tech](https://c33tech.com/blog/2026/04/how_not_to_pilet_a_kickstarter/)); HOVERAir AQUA hit an FCC ban ([DroneXL](https://dronexl.co/2026/05/28/hoverair-aqua-global-launch-us-fcc-ban/)); RAM prices "nearly tripled" for KONKR ([GSMGoTech](https://www.gsmgotech.com/2026/03/ayaneo-konkr-pocket-fit-elite.html)). The sample is small and hand-picked, not statistical (`02_RECHERCHE/parallel/00_SYNTHESE.md` §2).
2. **Sourcing is already a commodity.**
   - Alibaba's Accio costs $19.90 to $199 a month ([pricing](https://www.accio.com/pricing?pricingScene=manager&region=accio_work&language=en)), and 230,000 businesses used Accio Work one month after launch ([PR Newswire](https://www.prnewswire.com/news-releases/alibabas-accio-work-now-powers-230-000-online-stores-globally-302756549.html)).
   - No Logo charges 25% flat on top of cost ([nologo.com/pricing](https://nologo.com/pricing)).
   - Sourcing agents charge 5 to 10% ([Dragon Sourcing](https://www.dragonsourcing.com/top-10-cost-insights-for-hiring-a-china-sourcing-agent/)).
3. **No competitor publishes its on-time delivery rate, defect rate or rejected lots.** Competitors count users and suppliers instead (`02_RECHERCHE/parallel/B_concurrence.md`).
4. **Halliday's COO:** "As a newcomer to the industry, we didn't speak [the manufacturer's] language" ([Engadget](https://www.engadget.com/2216393/halliday-g2-smart-glasses/), 21/07/2026).

**What could kill it:** backers tolerate delays. More than 75% of Kickstarter projects deliver late ([Mollick](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2088298)), but only about 9% never deliver ([Mollick](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2699251)), and Kickstarter still set a record in 2025 ([PBC Report](https://d3mlfyygrfdi2i.cloudfront.net/Annual_PBC_Report_2025_V2Final-6104f68.pdf)). Founders' willingness to pay to remove the delay is not proven. Campaign 01 exists to test it.

## Repo rules
- **Every figure or factual claim carries a source**: a URL, or a file path relative to the `Hexa_Case/` root. No source, not written.
- **Invent nothing.** Anything unverified is labelled **Hypothesis**. Scores and estimates state how they were computed.
- Mark signals from pages that could not be reopened (Kickstarter and Reddit often return 403) as "medium confidence".
- For verification, use native web search and fetch.
- **Outreach:** never mention Hexa or the project name. Introduce yourself honestly as someone studying hardware sourcing. Sell nothing, promise nothing, and ask for a conversation, never a sale (`03_DISCOVERY/messages.md`).
- One page per file, written in English. No empty files, no generic templates.

## How the files fit together
```
context/icp.md ─┬─> skills/icp-scoring ──────> outputs/accounts.csv (score + justification)
context/signals.md ┘         │
                             v
               skills/account-research ─> precise problem + angle
                             │
                             v
context/positioning.md ─> skills/signal-to-sequence ─> message citing the signal
context/competitors.md ─> skills/pvp-teardown ──────> cost and risk teardown to offer
context/personas/ ─> tone and objections for every skill
outputs/campaign-01-discovery/brief.md = the live campaign; its results update icp.md and this thesis
```
