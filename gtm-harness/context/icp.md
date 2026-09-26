# ICP

**Hypothesis: to be validated by discovery.**

## Segment A: funded hardware creator who is late on delivery
| | |
|---|---|
| **Size** | 314 Technology + Design campaigns were funded on Kickstarter in Q1 2026, for $67.23M in total ([TCF Q1 2026](https://www.tcf.team/blog/q1-2026-crowdfunding-report), third-party source, medium confidence). In 2025, Design & Tech funded projects grew 12% and pledged amounts grew 64% ([Kickstarter PBC Report 2025](https://d3mlfyygrfdi2i.cloudfront.net/Annual_PBC_Report_2025_V2Final-6104f68.pdf)). |
| **Proof of revenue** | Money is already pledged. Small teams in our list raised between $49,868 (Friend) and $3.8M (Circular Ring 2) (`outputs/accounts.csv`). |
| **Constraint** | The price is fixed at pledge time and the ship date is public. When input costs move, the margin absorbs it: RAM prices "nearly tripled" for KONKR ([GSMGoTech](https://www.gsmgotech.com/2026/03/ayaneo-konkr-pocket-fit-elite.html)). |
| **Urgency** | The pressure is public. Pilet backers built a refund site ([c33tech](https://c33tech.com/blog/2026/04/how_not_to_pilet_a_kickstarter/)). The Minimal Phone received BBB complaints in August 2026 ([iTechGuides](https://www.itechguides.com/with-backers-losing-patience-the-long-delayed-minimal-phone-was-rumored-to-ship-in-two-weeks-what-happened/)). |

## Segment B: growing DTC brand launching a product made in China
| | |
|---|---|
| **Size** | 3,100,790 active Shopify stores across all categories, not only physical goods ([Store Leads](https://storeleads.app/reports/shopify), medium confidence). There is no count of hardware DTC brands. |
| **Proof of revenue** | Third-party estimates, low confidence: Satechi ~$15M, MOFT ~$8.6M in 2025 online sales, Aer ~$5M (`outputs/accounts.csv`). |
| **Constraint** | US duties now depend on the HTS code. The IEEPA duties ended on 24/02/2026, but Section 301 still applies ([CBP](https://content.govdelivery.com/accounts/USDHSCBP/bulletins/40b11c9)). The de minimis exemption is suspended ([Federal Register](https://www.federalregister.gov/documents/2026/06/24/2026-12669/indefinite-suspension-of-the-de-minimis-exemption-for-mail-shipments-and-new-postal-informal-entry)). |
| **Urgency** | An announced launch date. Example: MOFT previewed its products at CES 2026 (`outputs/accounts.csv`). |

**Weak point:** none of the 4 DTC accounts has a documented production problem, and all 4 are scored 1 (`outputs/accounts.csv`). Segment B is the weaker hypothesis.

## Insight: the user is the buyer, and the buyer is the founder
In segment A, the public contact is the founder or CEO: The Minimal Phone, AIVELA, Wordrunner, GAMR, Circular (`outputs/accounts.csv`, `contact` column).
*Implication, to validate:* there is no buying committee, so the sales cycle should be short.

## Pain
- A public, dated promise that has been missed.
- Backer anger in the comments.
- Redesigns and component changes after the campaign, which make up 18 of 24 documented causes (`CLAUDE.md`).

## Tools on the market today
- **Backer management:** PledgeBox and BackerKit (`outputs/accounts.csv`, AERIONN and Peak Design rows).
- **Sourcing agents:** 5 to 10% of the order ([Dragon Sourcing](https://www.dragonsourcing.com/top-10-cost-insights-for-hiring-a-china-sourcing-agent/)).
- **Accio:** $19.90 to $199 a month ([pricing](https://www.accio.com/pricing?pricingScene=manager&region=accio_work&language=en)).
- **QC inspection:** $268 per man-day ([V-Trust](https://www.v-trust.com/en/our-network)).

## Anti-ICP
- **An idea with no proven demand:** no funded campaign and no sales.
- **Established manufacturers with their own supply chain:** AWOL Vision, Creality, AYANEO/KONKR, OneXPlayer, Hyper/Targus. Their urgency is high but their fit is low. Keep them as sources of verbatims, not as clients (`02_RECHERCHE/parallel/00_SYNTHESE.md` §3).

## Open question: is consumer electronics in or out of the ICP?
9 of the top 10 accounts are electronics. The only exception is the AERIONN titanium suitcase (`02_RECHERCHE/parallel/00_SYNTHESE.md` §3).
- **For:** electronics carries the certification and component risk that thesis v2 targets.
- **Against:** a quality guarantee is far harder to underwrite on electronics.

Decide after campaign 01.

## ICP knowledge test (a16z framework, applied 26/09)
Source: [a16z — A framework to define and refine your ICP](https://a16z.com/framework-define-refine-icp/). Step 1 ("can we state the 9 criteria?") applies now; step 2 (listening tours with best, lost and churned customers) applies once we have customers — until then, discovery calls play that role.

| # | Criterion | What we know (Segment A) | Status | How we close the gap |
|---|---|---|---|---|
| 1 | Company size / revenue | Small teams; campaigns $49,868 to $3.8M (`outputs/accounts.csv`) | Known | — |
| 2 | Business type | Crowdfunded hardware startup, first or second product, no own factory | Known | — |
| 3 | Geography & language | US-first (Kickstarter US, FCC); some EU (Circular Ring, Paris); factories in China | Partly | Count geographies in replies |
| 4 | Industry | Consumer electronics (9 of top 10) — non-electronics still open | **Open** | Decide after campaign 01 (see above) |
| 5 | Decision-maker title | Founder / CEO = user = buyer | Known (hypothesis on cycle length) | Ask who else signs a factory PO |
| 6 | Definable problem | Late delivery after a funded campaign; 18/24 documented causes = engineering, components, certification | Known (small sample) | Discovery question 1 |
| 7 | Company characteristics | Fixed pledge price, public ship date, backer pressure | Known | — |
| 8 | Tech / tool stack | PledgeBox, BackerKit, sourcing agents, Alibaba/1688, WeChat, spreadsheets | Partly | Discovery question 3 ("daily exchange with the factory") |
| 9 | Unique buyer behaviour | Buys under public time pressure; tolerance to delay unknown | **Open** | Discovery question 2 (what they paid third parties) — this is assumption A2 (painkiller vs vitamin) |

**Competitors' customers (a16z question 5, answerable now):** No Logo, Cavela and Sourcy serve e-commerce brands sourcing existing product types; Accio serves 230,000 online stores. None targets funded first-time hardware founders at the translation step — our gap, to confirm in calls.
**Selection rule once we have customers (a16z):** prioritise the intersection of highest lifetime value, fastest cycle and best retention — not the largest order alone.
