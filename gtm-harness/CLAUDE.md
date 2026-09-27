# CLAUDE.md: PhysicalLovableX GTM harness

Last updated: 2026-09-27. Read this first; the detail lives in the files it links. Paths are relative to this folder unless they start with a `Hexa_Case/` top-level folder (`00_ENONCE.md`, `02_RECHERCHE/`, `03_DISCOVERY/`, `04_LIVRABLE/`).

## Product (`context/profile.md`)
A working name for an idea Hexa WTF is scoping, not a launched company. **The Studio** turns one sentence into a 3D product with unit cost and a factory shortlist, re-computed on every prompt; **the Factory Pack** is the spec package a factory can quote without back-and-forth. Real: CAD, DFM, LCSC prices, duties, cost engine, MCP. Simulated: all factories and quotes (`04_LIVRABLE/PRODUIT.md`). No customers, no revenue.

## Who we sell to first (`context/icp.md`)
- **ECP (now, 3-6 months):** late crowdfunded **consumer-electronics** founders: funded campaign, prototype, no own factory, public ship date missed. User = buyer = founder.
- **ICP (later):** funded hardware startups before a campaign, and brands adding a physical product.
- **Consumer electronics first (decided 27/09):** 28 of 36 drafted accounts and 9 of the top 10 are electronics; LCSC parts and FCC checks add most there. A focus choice, not a finding.
- **Anti-ICP:** established brands with their own supply chain (AWOL, Creality, AYANEO…): verbatim sources only.

## Top 5 signals (`context/signals.md`: points, decay, bonuses, hooks, performance)
1. Estimated delivery date has passed (gate; +10 if > 12 months late)
2. Creator update names a production cause: factory, mold, sample, components, certification, redesign
3. Pre-order or "shipping soon" still showing after the promised date
4. New product announced (the next buying moment)
5. Backer comments about production (confirms only, never quoted)

## Positioning (`context/positioning.md`, `context/competitors.md`)
**"From idea or prototype to 1,000 units shipped, without speaking the factory's language."** We do the translation (DFM, components, certification, a spec in the factory's language), then commit to a landed price. Never in cold outreach. Real competitor: "my contact in Shenzhen"; threat #1: Alibaba's Accio; Monce (Paris) is factory-side and complementary.

## Current priorities (week of 27/09; refresh with `skills/weekly-update`)
1. **Campaign 01 send:** ~32 sendable cold drafts of 36 (`03_DISCOVERY/envoi/A_ENVOYER.md`); a human sends and logs in `SUIVI.md`; follow-up after 48 h (`RELANCE.md`). 0 logged on 27/09.
2. **Warm track:** 10 network messages, target 2 calls before Mon 28/09 11:30 (`RESEAU.md`; names never enter this repo).
3. **Calls:** target ≥ 3 coded calls by Mon 28/09 noon; each run with `playbooks/founder-replied.md`, coded within 30 min with `skills/call-debrief`.
4. **Deck:** PDF before Mon 28/09 12:00; fill [SENT] [REPLIES] [CALLS] from `tracking.md` (`04_LIVRABLE/deck/DECK_DRAFT.md`, appendix A).
5. **W1 plan (after W0):** Mon follow-ups; Tue widen to ~150 accounts; Wed score + research top 30; Thu-Fri 2 × 30 messages; Sat teardowns after calls; Sun keep / change the hook (deck slide 9).

## Thesis v2 (compressed)
> The bottleneck is neither design nor the factory: it is the translation between the two (manufacturability, components, certification, the factory's language). That is where launches slip.
- **Evidence:** documented delay causes on 30 enriched accounts: engineering 8, components 7, certification 3, factory 3, logistics 3, none stated 7 (hand-coded, small, not random; `02_RECHERCHE/parallel/00_SYNTHESE.md` §2). Examples: Pilet CM5 redesign ([c33tech](https://c33tech.com/blog/2026/04/how_not_to_pilet_a_kickstarter/)), HOVERAir AQUA FCC ban ([DroneXL](https://dronexl.co/2026/05/28/hoverair-aqua-global-launch-us-fcc-ban/)). Halliday's COO: "we didn't speak [the manufacturer's] language" ([Engadget](https://www.engadget.com/2216393/halliday-g2-smart-glasses/)).
- **Sourcing is a commodity:** Accio $19.90-199 a month ([pricing](https://www.accio.com/pricing?pricingScene=manager&region=accio_work&language=en)), 230,000 businesses ([PR Newswire](https://www.prnewswire.com/news-releases/alibabas-accio-work-now-powers-230-000-online-stores-globally-302756549.html)); No Logo 25% ([pricing](https://nologo.com/pricing)); agents 5-10% ([Dragon Sourcing](https://www.dragonsourcing.com/top-10-cost-insights-for-hiring-a-china-sourcing-agent/)). No competitor publishes on-time or defect rates (`02_RECHERCHE/parallel/B_concurrence.md`).
- **What could kill it:** backers tolerate delay: > 75% of Kickstarter projects deliver late ([Mollick](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2088298)), ~9% never deliver ([Mollick](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2699251)). Willingness to pay is unproven; campaign 01 tests it.

## Repo rules
- Every figure or claim carries a source (URL or path). No source, not written. Unverified = **Hypothesis**.
- Pages that could not be reopened (Kickstarter, Reddit, BackerKit 403) = "medium confidence", never quoted in outreach.
- **Outreach:** never mention Hexa or the project name; honest intro as someone studying hardware sourcing; sell nothing, promise nothing; ask for a conversation (`03_DISCOVERY/messages.md`).
- English, one page per file, no empty files, no generic templates.
- **Privacy:** no contact lists, no warm-network names, no raw transcripts, no founder files, no API keys in this repo (`outputs/accounts.csv` keeps public names and URLs only; emails removed 27/09). Nothing here sends, publishes or pushes; a human does.

## Map
```
context/  profile · icp · signals · positioning · competitors · personas/(founder, factory, partner)
   │
skills/   icp-scoring → account-research → signal-to-sequence → (human sends) → call-debrief → weekly-update
          pvp-teardown (after a call only)
workflows/ signal-routing · campaign-build · enrichment        playbooks/ new-signal-response · founder-replied · factory-intro
outputs/  accounts.csv (mirror, 45 rows) · research/ · pvp/ · campaign-01-discovery/ · RUN_LOG.md · weekly-log.md
Truth outside: 03_DISCOVERY/comptes.csv (55 rows) · envoi/SUIVI.md · A_ENVOYER.md · RELANCE.md · RESEAU.md · verbatims.md
```
