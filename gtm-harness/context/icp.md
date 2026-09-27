# ICP

Last updated: 2026-09-27. **Hypothesis: to be validated by discovery.** Structure (tiers, qualification, anti-ICP, evolution log) adapted from the GTM repository format (credits in `README.md`).

## Early Customer Profile (now) vs ICP (later)
- **ECP, now (disposable after 3-6 months):** late crowdfunded **consumer-electronics** founders (PCB + enclosure). Funded campaign, first or second product, working prototype, no own factory, public ship date missed.
- **ICP, later (once one case is documented end to end):** funded hardware startups before a campaign, and brands adding a physical product (beachhead rows 3-4 below).
- Idea-stage users stay the free funnel (`context/profile.md`). Method: GTM Strategist, "Before there is Ideal, there is Early" (`04_LIVRABLE/GTM_Lessons_Substack_MajaVoje.md`).

## Segment evidence
| | Segment A: funded creator, late (ECP) | Segment B: DTC brand launching a China-made product (later) |
|---|---|---|
| Size | 314 Technology + Design campaigns funded on Kickstarter in Q1 2026, $67.23M ([TCF Q1 2026](https://www.tcf.team/blog/q1-2026-crowdfunding-report), medium confidence) | 3,100,790 active Shopify stores, all categories ([Store Leads](https://storeleads.app/reports/shopify), medium); no count of hardware DTC brands |
| Money | Already pledged: $49,868 (Friend) to $3.8M (Circular Ring 2) (`outputs/accounts.csv`) | Satechi ~$15M, MOFT ~$8.6M, Aer ~$5M, third-party, low confidence (`outputs/accounts.csv`) |
| Constraint | Price fixed at pledge; RAM "nearly tripled" for KONKR ([GSMGoTech](https://www.gsmgotech.com/2026/03/ayaneo-konkr-pocket-fit-elite.html)) | Duty by HTS line; Section 301 remains, de minimis suspended ([CBP](https://content.govdelivery.com/accounts/USDHSCBP/bulletins/40b11c9), [Federal Register](https://www.federalregister.gov/documents/2026/06/24/2026-12669/indefinite-suspension-of-the-de-minimis-exemption-for-mail-shipments-and-new-postal-informal-entry)) |
| Urgency | Public: Pilet refund site ([c33tech](https://c33tech.com/blog/2026/04/how_not_to_pilet_a_kickstarter/)); Minimal Phone BBB complaints ([iTechGuides](https://www.itechguides.com/with-backers-losing-patience-the-long-delayed-minimal-phone-was-rumored-to-ship-in-two-weeks-what-happened/)) | Weak: none of 4 accounts has a documented production problem, all scored 1 |

User = buyer = founder in Segment A: the public contact is the founder or CEO (The Minimal Phone, AIVELA, Wordrunner, GAMR, Circular; `outputs/accounts.csv`). **Hypothesis:** no committee, so a short cycle.

## Tiers (for routing; score from `skills/icp-scoring`, points from `context/signals.md`)
| Tier | Definition | Action |
|---|---|---|
| **1** | ECP: consumer electronics, urgency score 4-5, named founder with a public channel, signal ≤ 180 days old | Research card + hand-written message (`workflows/signal-routing.md`) |
| **2** | Score 3, or non-electronics late, or shipped late recently (e.g. Game Bub, Modos: `03_DISCOVERY/envoi/A_ENVOYER.md` #32, #35) | Message if a fresh quote exists; discovery value, lower urgency |
| **3** | Score 2, or channel is only a support inbox or contact form | Send last; look for a direct channel first |
| **4 (monitor / verbatim only)** | Score 1, established brands, logistics-only delays | No sales outreach; may ask for a verbatim |

## Qualification questions (ask in the call, after the 5 discovery questions)
1. Is there a working prototype and a BOM? (entry mode "I have a prototype")
2. Is a next product or a new batch planned in the next 12 months? (buying moment, `personas/hardware-founder.md`)
3. Who else signs a factory PO: an engineering co-founder, an investor?
4. How much did you pay intermediaries on this launch? (discovery question 5, willingness-to-pay proxy)
5. Is the blocker cash or demand rather than production? If yes, this is a kill signal (deck slide 12).

## Anti-ICP
| Exclusion | Why | Source |
|---|---|---|
| Established manufacturers with their own supply chain (AWOL, Creality, AYANEO/KONKR, OneXPlayer, Hyper/Targus, Anker/eufyMake) | High urgency, low fit; verbatim sources only | `02_RECHERCHE/parallel/00_SYNTHESE.md` §3; deck slide 5 (Anker/eufyMake) |
| Idea with no proven demand (no campaign, no sales) | Not a buyer; served free as funnel | this file, v1 |
| Logistics-only delays (VAT, typhoon, sizing kits) | Not a production problem | `context/signals.md` |
| Makers / hobbyists | Not shipping 1,000 units; ICP = founders with commercial intent | `02_RECHERCHE/lecons_inputs.md` |

## Beachhead scoring (27/09, my scoring, Hypothesis)
Method: GTM Strategist, "The One GTM Decision You Cannot Afford to Get Wrong" (`GTM_Lessons_Substack_MajaVoje.md`). 1-5 per criterion, access ×2, max 30. Mirrored on deck appendix A8.
| # | Segment | Pain | Pay | Cycle | Growth | Access ×2 | Total |
|---|---|---|---|---|---|---|---|
| 1 | **Late crowdfunded consumer-electronics founders (ECP)** | 5 | 3 | 4 | 4 | 10 | **26** |
| 2 | Late crowdfunded non-electronics | 4 | 3 | 4 | 3 | 6 | 20 |
| 3 | Funded hardware startups, no campaign yet (later ICP) | 3 | 4 | 3 | 3 | 4 | 17 |
| 4 | DTC / Amazon brands adding a product (later ICP) | 2 | 4 | 3 | 3 | 4 | 16 |
| 5 | Established hardware brands (anti-ICP) | 3 | 5 | 1 | 3 | 2 | 14 |
| 6 | Idea-stage creators (funnel) | 2 | 1 | 2 | 3 | 6 | 14 |
| 7 | Makers / hobbyists | 1 | 1 | 2 | 3 | 6 | 13 |
| 8 | SME manufacturers (no repo evidence) | 3 | 4 | 1 | 2 | 2 | 12 |
Row evidence is in deck A8. Unweighted, row 1 still leads (21 vs 17). Re-score after campaign 01 replies.

## a16z knowledge test (26/09, [a16z](https://a16z.com/framework-define-refine-icp/))
Known: size, business type, industry (decided 27/09), decision-maker, problem, characteristics. Partly known: geography (US-first, some EU), tool stack (PledgeBox, BackerKit, agents, WeChat). **Open:** buyer behaviour under delay, i.e. whether they pay (assumption A2). Closed by discovery questions 2, 3 and 5.

## ICP evolution log
| Date | Change | Reason / source |
|---|---|---|
| 2026-09-26 | Thesis v1 (prompt → design → factory marketplace) replaced by v2 (translation is the bottleneck) | 18 of 24 documented delay causes are engineering, components or certification; sourcing is cheap and crowded (`CLAUDE.md`; deck slide 3) |
| 2026-09-27 | Consumer electronics first (was an open question) | 28 of 36 drafted accounts and 9 of the top 10 are electronics; LCSC parts + FCC checks add most there. Focus choice, not a finding; a quality guarantee is harder to underwrite on electronics (deck slide 5) |
| 2026-09-27 | ECP ≠ ICP: late crowdfunded electronics founders now; startups and brands later | Beachhead scoring above (access decides) |
| 2026-09-27 | Studio pivot: positioning moved, ICP unchanged | Deck appendix B item 10 |
| 2026-09-27 | 10 accounts added from Crowd Supply and founder blogs (batch 3); `03_DISCOVERY/comptes.csv` now 55 rows | `A_ENVOYER.md` #27-#36 |
