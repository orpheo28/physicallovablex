# Workflow: enrichment

Which sources to use, in which order, and what an account needs before a message is drafted. Waterfall idea adapted from the GTM repository (credits in `README.md`); the tools are not: **public sources only, no paid enrichment, no scraping behind a login.**

## Source waterfall (stop when the required fields are filled)
| Order | Source | What it gives | Confidence |
|---|---|---|---|
| 1 | Campaign page and creator updates: Kickstarter `/posts`, Indiegogo `/updates`, Crowd Supply updates, BackerKit updates | Promised date, new date, the creator's own words on the cause (S1, S2) | High if reopened |
| 2 | Brand site: product page (pre-order wording), blog, imprint or contact page | S4, public channel, legal entity | High |
| 3 | Press and specialist blogs: Hackster, Road to VR, Engadget, CNX Software, Gizmochina | Dates, causes, next product (S6) | High to medium |
| 4 | Trackers and history: Kicktraq, Wayback Machine | Amount raised, moved dates | Medium |
| 5 | Backers: `/comments`, Trustpilot, BBB, Reddit, brand forums | Confirmation only (S3) | Medium |
| 6 | Public LinkedIn profile or company page (as shown without logging in, or found through web search) | Founder name, role, co-founder | Medium: check it is the same person |

Not allowed: paid enrichment databases or email finders, guessing email patterns, logging in to scrape (LinkedIn, Kickstarter, Discord), buying lists.

## 403 and blocked pages
Kickstarter, Reddit, BackerKit and Hackster often return 403 to automated reads (`outputs/RUN_LOG.md`; `03_DISCOVERY/envoi/A_ENVOYER.md` #27, #34).
1. Try the web-search snippet or another public page that quotes the same update.
2. If only a snippet exists: mark "Confidence: medium (relayed, page not reopened)", apply points × 0.5, and **do not quote it** in a message.
3. Add "human to open in a browser" to the account's ⚠️ line; a human reopens it before the QA gate.
4. Never fill a gap with a guess; write "not stated".

## Ready to draft (required fields)
- [ ] Signal: URL, date, exact wording, confidence
- [ ] Urgency score, priority points, bucket, tier (`skills/icp-scoring`)
- [ ] Category (consumer electronics or not) and anti-ICP check
- [ ] Named founder or co-founder, from a public page
- [ ] One public channel (email published on their site, LinkedIn, platform message)
- [ ] Root-cause bucket or "not stated" (`skills/account-research`)

## Where the data lives
- Account rows and public contact points: `03_DISCOVERY/comptes.csv` (outside the harness). The harness mirror `outputs/accounts.csv` holds 45 rows vs 55 in `comptes.csv` on 27/09; see `outputs/weekly-log.md`.
- Research cards in the harness name the channel type only, not the address.
- Warm-network names never enter the harness (`03_DISCOVERY/envoi/RESEAU.md` stays outside).

## Re-enrich cadence (Hypothesis)
| Bucket | Re-check the latest update and product page |
|---|---|
| HOT | Before each send, and weekly |
| WARM | Weekly |
| COLD | Every 2 weeks |
| SKIP / Tier 4 | Only on a new signal |

## Deliverability
Messages are few and hand-sent from personal accounts (36 drafts in campaign 01; 60 new in W1, deck slide 9). No sending tool, no domain warm-up is set up. **Hypothesis to revisit** if W1 volume goes through one mailbox: watch bounces and replies marked as spam.
