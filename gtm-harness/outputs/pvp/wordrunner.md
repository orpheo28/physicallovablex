> **Demo of the harness, not a figure to quote.** The FOB ratio (20-35% of retail) is an unsourced hypothesis tagged [E]; a real teardown uses the founder's BOM after the discovery call.

# Wordrunner (Astrohaus / Freewrite): teardown (2026-09-26)

Run of `skills/pvp-teardown`. Not to be sent cold: offer it after a call or on request. No teardown photos or BOM were available, so parts come from spec text only.

## Sourced
- [S] Price on the product page: $379 pre-order, $459 regular ([getfreewrite.com](https://getfreewrite.com/products/wordrunner), 2026-09-26, read through a summary tool). A November 2025 article gives $500 ([Good e-Reader](https://goodereader.com/blog/technology/freewrite-wordrunner-is-shipping-out-in-january), 2025-11-15). The two prices disagree; I did not resolve which is current.
- [S] Spec on the product page: die-cast aluminium body, tactile switches rated 80 million presses, 8-digit mechanical counter, gasket mount, USB-C plus Bluetooth for up to 4 devices, one-month battery target (same page).
- [E] Switch history: the CES 2025 prototype reportedly used Kailh Box Brown switches, while the current listing says "tactile switches". This comes from a web-search summary of press coverage (Tom's Hardware, Pocket-lint and others); I did not identify or open the page, so it is unverified.
- [S] Promise: shipping January 2026 (Good e-Reader, 2025-11-15). The Kickstarter had targeted the end of 2025.
- [S] Status: the page still reads "Preorder now to secure the best price and earliest priority" and gives no ship date (getfreewrite.com, 2026-09-26).
- [S] Campaign size: $235,528, 723 backers (`outputs/accounts.csv`, Wordrunner row).
- [S] Reference values (listing only): Fanstel BT840F, an nRF52840 module, $7.17 each at 1,000 pieces ([Fanstel](https://www.fanstel.com/bt840); found through a search summary). Wordrunner's actual chip is not stated, so this shows the price class of a Bluetooth module, not its BOM line.
- [S] Reference values: sourcing agent 5-10% ([Dragon Sourcing](https://www.dragonsourcing.com/top-10-cost-insights-for-hiring-a-china-sourcing-agent/)); pre-shipment inspection $268 per man-day ([V-Trust](https://www.v-trust.com/en/our-network)).

## Estimated
- [E] Parts (from spec text): die-cast aluminium case, PCB with wireless MCU, 88 switches with keycaps, electromechanical counter and timer, joystick, gasket and dampening foam, battery, packaging.
- [E] Factory cost (FOB) $76-161 per unit. Method: 20-35% of the retail price, on $379 (low end) and $459 (high end). **The 20-35% ratio is my assumption, with no source**; a metal keyboard with a mechanical counter may sit higher.
- [E] Landed cost, before freight and duties: $80-177 per unit. Method: FOB × 1.05-1.10 for the sourcing agent (sourced above).
- [E] Mould amortisation for a die-cast case: $11-111 per unit. Method: a tooling budget of $8,000-80,000 divided by 723 units, the backer count. The $8,000-80,000 range comes from a web-search summary of die-casting cost guides whose page I did not identify, so treat it as unverified. Pre-orders after the campaign would lower the per-unit figure by an unknown amount.
- [E] Not estimated: freight, insurance, 3PL and duties. The HTS code was not looked up. A human must add both.

## Risks
1. **DFM/engineering (most likely to move the ship date):** the die-cast case, the gasket mount and an electromechanical word counter are all mechanisms that a factory has to tune, and the case tooling is the slow, expensive part. Comparable: eufyMake E1, ink pressure and metering tank ([eufyMake AMA recap](https://www.eufymake.com/blogs/news/eufymake-live-ama-recap), cited in `03_DISCOVERY/envoi/A_ENVOYER.md` #14, not reopened). Creality, filament diameter ([Makers101](https://makers101.com/creality-filament-maker-m1-shredder-r1-live-tracker/)).
2. **Components (most likely to move the ship date):** the switch went from Kailh Box Brown on the prototype (unverified, see Estimated) to an unnamed "tactile" switch on the listing, which suggests a part change after the prototype. **Hypothesis:** a Reddit post reportedly mentions tooling and component changes, but it could not be opened (`outputs/accounts.csv`, Wordrunner row). Comparable: OneXPlayer 3, battery lead times, and KONKR, RAM price ([GSMGoTech](https://www.gsmgotech.com/2026/03/ayaneo-konkr-pocket-fit-elite.html)).
3. **Certification (lower):** a Bluetooth radio needs FCC and CE. **Hypothesis:** no source mentions a certification problem; the risk is only structural. Comparable: SwiftShape and HOVERAir AQUA, per the skill list.

## Top question for your factory
Which one part (case, counter mechanism or switch) is still waiting on a signed-off sample, and on what date did you last approve one?

## Confidence
Low. What would make it medium: the BOM, a case tooling quote, the chip name, the HTS code, and the current price.

## Unverified
- The Kickstarter page and updates returned 403, so no creator statement about the cause was read.
- The price ($379 / $459 / $500) and the current ship date.
- The fetch tool summarises pages with a small model; the getfreewrite.com figures should be checked by eye.
