---
name: icp-scoring
description: Score a list of hardware accounts from 1 to 5 on production urgency, then rank them by fit. Use it on any new list of crowdfunding campaigns or DTC brands.
---

# ICP scoring

**Input:** a list of accounts, each with a name and a campaign or website URL (CSV or inline).
**Output:** rows in the `outputs/accounts.csv` format (`nom,type,url,produit,signal,statut_livraison,contact,canal,score,…,notes`). Every score is justified by at least one source URL in `notes`.

The rubric below is derived from the 45 scored rows of `outputs/accounts.csv`. Each level cites the anchor accounts to calibrate against.

## Step 1: collect the signals
For each account:
1. Open the campaign page, its updates and comments, then Trustpilot, BBB, forums and the product page.
2. Record the signals from `context/signals.md`, each with its URL and date.
3. If a page cannot be reopened (Kickstarter and Reddit often return 403), write "Confidence: medium (relayed, page not reopened)".

## Step 2: urgency score (1-5)
| Score | Rule | Anchors |
|---|---|---|
| **5** | The date has passed, the product is not fully shipped, **and** at least one of: a post-campaign redesign, creator silence, organised refunds, or more than 12 months late. | AERIONN, Pilet, The Minimal Phone, AWOL |
| **4** | The date has passed, the product is not fully shipped (or is still on pre-order) or has been cancelled, **and** there is either a documented production cause or high-confidence backer evidence. | SwiftShape, Wordrunner, AIVELA, Creality, Hyper, Smokpub |
| **3** | Shipped at least 3 months late (with or without a stated cause), **or** a creator-confirmed delay with unknown shipping status. | Halliday, Circular Ring 2, Phrozen, HOVERAir, GAMR |
| **2** | Less than 3 months late, **or** a non-production cause (logistics, VAT, weather), **or** only a relayed signal that was not re-verified. | Peak Design, Wyrmwood, Friend, Rokid |
| **1** | No documented delivery problem. This covers DTC launches with no incident, and logistics or size-kit issues only. | Satechi, MOFT, RingConn |

Rules:
- Without the "date has passed" gate, the score is capped at 2.
- A backer comment alone never gives more than 2.

## Step 3: fit filter
This step decides the ranking, not the score. Keep an account in the top list only if all of these hold:
- It is a startup or small brand. Established manufacturers with their own supply chain are out: AWOL, Creality, AYANEO/KONKR, OneXPlayer, Hyper/Targus (`02_RECHERCHE/parallel/00_SYNTHESE.md` §3).
- There is a reachable contact: a named founder, an email or a LinkedIn profile.
- Priority +1 if a next product is announced or there is a sourcing job posting (`context/signals.md`).

Rank by score, then by fit, then by contactability.

## Step 4: write the justification
Put this in `notes`:
- `Source signal: <URL> (<date>)`
- `Amount: …`
- `Signal confidence: high|medium`
- the reason for the score in one line, with the rubric level

Never state a delay, an amount or a founder's name without its URL.

## Checks before handing over
- [ ] Every score of 4 or 5 has at least one signal with high confidence.
- [ ] Established brands are flagged "verbatim, not client".
- [ ] Anything unverified is marked "to verify" and is not used in outreach.
