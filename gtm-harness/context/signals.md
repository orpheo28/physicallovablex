# Signals

Signals feed two numbers:
- **Score (1-5):** how urgent the production problem is. Rubric in `skills/icp-scoring/SKILL.md`.
- **Priority modifier:** whether the account is worth contacting now.

The weights are a design choice, calibrated on the 45 rows of `outputs/accounts.csv`. They are not a measured result.

| Signal | How to detect it | Weight | Seen in (source) |
|---|---|---|---|
| **Estimated delivery date has passed** | The "Estimated delivery" field on the Kickstarter or Indiegogo reward, compared with today. Check the creator's latest update for the new date. | **Gate:** required for a score of 3 or more. Without it, the score is capped at 2. | Wordrunner promised January 2026 ([Kickstarter](https://www.kickstarter.com/projects/astrohaus/wordrunner-mechanical-word-counting-keyboard)) |
| **Backer update mentions the factory, molds, a failed sample or a change of manufacturer** | Read the campaign's `/posts` page. Search for "factory", "mold", "tooling", "sample", "supplier", "manufacturer", "production pause". | **+1 level.** This documents the cause, and it is the only signal that tells design, components, certification and factory apart. | Pilet update #20, redesign to the CM5 ([c33tech](https://c33tech.com/blog/2026/04/how_not_to_pilet_a_kickstarter/)). Creality filament out of spec in factory tests ([Makers101](https://makers101.com/creality-filament-maker-m1-shredder-r1-live-tracker/)) |
| **Backer comments about production** | The campaign `/comments` page, plus Trustpilot, BBB, Reddit and brand forums. Kickstarter and Reddit often return 403, so fall back to search snippets. | **Alone: 2.** Mark it "medium confidence" if the page could not be reopened. It confirms a score but never raises it by itself. | SwiftShape ([Glowforge forum](https://community.glowforge.com/t/swiftshape/140166)). Smokpub, 1.7/5 ([Trustpilot](https://www.trustpilot.com/review/smokpub.com)) |
| **Pre-order extended or long stock-out** | The product page still shows "Pre-order" after the promised date. The Wayback Machine gives the history. | **Treated as "not shipped": 4** when the promised date has passed. | Wordrunner is still "PREORDER NOW" in September 2026 ([getfreewrite.com](https://getfreewrite.com/products/wordrunner)) |
| **Sourcing or supply-chain job posting at a small company** | LinkedIn Jobs, Welcome to the Jungle and the careers page. Filter on companies with fewer than 50 employees, and on "sourcing", "supply chain", "NPI", "operations". | **Priority +1, score unchanged.** It is a fit and timing signal for segment B. **Untested:** no account in `accounts.csv` was found this way. | none yet |
| **New product announced** | The brand's news page, press, a new campaign "Notify me" page, CES announcements. | **Priority +1, score unchanged.** It means there is a next product to secure. | Halliday G2 ([Engadget](https://www.engadget.com/2216393/halliday-g2-smart-glasses/)). Minimal Phone 2: verified 26/09, Kickstarter launch 11/08/2026, $800k+ ([Gizmochina](https://www.gizmochina.com/2026/08/11/minimal-phone-2-swaps-e-ink-for-3-92-inch-oled-retains-qwerty-keyboard/)) |

## Signals that raise a score to 5
The delivery date has passed, the product is not fully shipped, and at least one of the following is true:
- the product was redesigned after the campaign (AERIONN);
- the creator has gone silent (AERIONN);
- backers have organised refunds (Pilet);
- the product is more than 12 months late (Pilet).

Sources: the AERIONN, Pilet and The Minimal Phone rows in `outputs/accounts.csv`.

## Signals that do not count
- Logistics-only delays: VAT paperwork (Wyrmwood), a typhoon (Peak Design), missing merch (CyberBrick).
- Address collection (AYANEO Pocket AIR Mini).

These are rows scored 1 or 2 in `outputs/accounts.csv`. They are not production problems.
