# Persona: the factory owner (supply side)

Last updated: 2026-09-27. **Almost entirely Hypothesis:** no factory has been contacted, and the factories in the demo are fictional (`context/profile.md`). This face is reached in W4, through intermediaries only (`playbooks/factory-intro.md`).

## Overview
- **Titles (Hypothesis):** owner, general manager, sales or business-development manager at a contract manufacturer (PCBA, injection moulding, final assembly), mostly in China.
- **Decision role:** decides whether to quote, at what MOQ and price, and whether to share capacity through the production MCP (assumption A4, `PRD.md` §3.1).
- **Language:** the Factory Pack ships in EN + CN for this reason (`PRODUIT.md`).

## What we observe (sourced)
- Founders and factories misread each other: Halliday's COO, "we didn't speak [the manufacturer's] language" ([Engadget](https://www.engadget.com/2216393/halliday-g2-smart-glasses/)).
- Factories appear in founders' public updates as the place where problems surface: displays short at the assembler (Game Bub, update from Elecrow, Shenzhen), T1 mold samples late (PicoIDE) (`03_DISCOVERY/envoi/A_ENVOYER.md` #32, #28).
- Factory-side software already targets inbound order and quote handling in Europe: Monce claims 25 min → < 60 s per order ([meetmonce.com](https://meetmonce.com/), claimed). This suggests quote intake is costly for manufacturers; not verified for Chinese contract manufacturers.

## What they care about (Hypothesis)
- Orders that turn into production, not RFQs that die after samples.
- Specs they can quote without back-and-forth.
- Buyers who will not blame the factory for a design or certification gap.

## How they buy in (Hypothesis)
- Trust passes through people they already work with: sourcing agents, QC inspectors, 3PLs, CAD freelancers (deck slide 9, W4; `04_LIVRABLE/GTM_Lessons_PhysicalLovableX.md`, Crossbeam fiche and synthesis §4).
- In person beats digital as AI makes cold outreach suspect (same file, BoomPop fiche).

## PMF signal on this side (Hypothesis, deck slide 12)
A quote returned from the Factory Pack without back-and-forth, target within 5 working days.

## Objections (Hypothesis, to log from the first W4 conversations)
| Objection | Answer to test |
|---|---|
| "We don't share capacity data" | Fall back to RFQ-only; infer capacity from quotes (`PRD.md` §3.1, A4) |
| "Small MOQ, first-time founder, not worth it" | Show the pack quality and the committed-price model; start with simple products |
| "Who owns the relationship with the brand?" | Open question; do not promise exclusivity |

## Hooks
- Lead with a real, quotable Factory Pack (never a fictional demand figure).
- Arrive through an intermediary who vouches, with an NDA ready (`PRD.md` §15).
