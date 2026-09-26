# Landing page copy — MVP (for the W1 frontend session)

**Product name is a working name** (`{PRODUCT}`). The MVP is a case-study demo: keep the trust labels on screen. Buttons and headings are final; body copy can be trimmed to fit, but do not add claims. Sources in `[ ]` render as small footnote links. Style: plain, no superlatives, no "revolutionary".

---

## Hero
**H1:** From idea to 1,000 units shipped.
**Alt H1 (A/B):** Your idea, translated into what a factory can build.
**Subhead:** Hardware doesn't ship late because of design or because of the factory. It ships late because nobody translates the idea into what the factory can build. We do that translation, and hand you a Factory Pack any factory can quote.
**Under the CTAs (small):** Demo with simulated factories. Every number shows its source or its assumption.

## Two CTAs
| Button | Sub-label | Action |
|---|---|---|
| **I have an idea** | Describe it in a sentence. Get the product, its cost and a factory shortlist in about 5 minutes. | Start in idea mode (brief with ≤5 questions) |
| **I have a prototype** | Paste your BOM. We check what will slow your first production run. | Start in prototype mode (BOM paste) |

## The problem — 3 sourced facts
**Heading:** Most launches slip between "the prototype works" and "the factory ships good units."

1. **More than 75% of Kickstarter projects deliver late, and about 9% never deliver.** [Mollick, SSRN 2014 / 2015: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2088298 · https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2699251]
2. **In 30 late campaigns we coded by hand, 18 of 24 documented causes were engineering or redesign, components or certification, not factory access.** Small, hand-picked sample, not a statistic. [`gtm-harness/CLAUDE.md`]
3. **"As a newcomer to the industry, we didn't speak [the manufacturer's] language."** Halliday's COO, on the first smart glasses. [Engadget, 21/07/2026: https://www.engadget.com/2216393/halliday-g2-smart-glasses/]

*Line under the facts:* Design tools and sourcing tools already exist. The gap is the translation between them.

## The flow — 13 stages in 13 short lines
Heading: **From brief to brand, in 13 stages.**
1. **Brief:** an idea, or a prototype and its BOM.
2. **Design:** three directions to choose from.
3. **CAD + spec:** a 3D model and an editable spec, STEP included.
4. **DFM:** manufacturing checks, measured on your CAD.
5. **Investment:** unit cost at 500, 2,000 and 10,000 units, plus cash needed.
6. **Production plan:** how each part is made, and where.
7. **Factory matching:** a ranked shortlist from the factory network.
8. **RFQ + negotiation:** agents request and compare quotes; you approve.
9. **Tooling + samples:** milestones from first mold to golden sample.
10. **Quality control:** an inspection plan built from your spec.
11. **Logistics:** landed cost with duties by product code.
12. **Financing:** your cash curve, and the options to fund it.
13. **Brand + distribution:** name, packaging, landing copy, listing draft.
*Closing line:* **Export it all as one Launch Dossier (PDF).**

## Trust labels — explained
Heading: **You will always know what is real.**
Every number on screen carries one of four labels.
| Label | What it means |
|---|---|
| **Measured** | Computed on your CAD model, for example draft angles and undercuts. |
| **Sourced** | A real price or official rate, with its date. Example: an electronics part at its LCSC price on the snapshot date. |
| **Estimate** | An assumption we show you, and you can change. |
| **Fictional — demo data** | Simulated for this demo: the factories, their quotes, freight rates. |
*Line:* Click any number to see its source or its assumption.

## Real vs simulated (small block, honesty)
**Real:** brief, design, CAD, spec, measured checks, certification map, component prices, cost engine, production plan, brand kit. **Simulated:** the 8 factories, their capacity, quotes and replies, freight rates.

## Next: real factory network
Heading: **Next: a real factory network.**
Body: Today the factories in this demo are fictional. Next, we onboard real factories by hand, one at a time, through a production MCP: an open interface where a factory lists its processes, MOQ, certifications, lead times and current load, and any agent (ours, Claude, ChatGPT or your own) can ask for capacity and request a quote. Every Factory Pack is reviewed by a human engineer before a real factory sees it.
Sub-line: **Want to be among the first founders or factories?** [Join the list] (⚠️ the form is not built in the MVP; render as a mailto or a disabled button labelled "Coming after the demo").
Footnote: The production MCP is described in `PRD.md` §10; it will create capacity data that is not public today (`02_RECHERCHE/parallel/E_usines.md`).

## Footer
"Demo built for a case study. All factories, quotes and freight are fictional. No real personal data is stored." Password-protected deployment note not shown.
