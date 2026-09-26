> **Demo of the harness, not a figure to quote.** The FOB ratio (20-35% of retail) is an unsourced hypothesis tagged [E]; a real teardown uses the founder's BOM after the discovery call.

# Halliday G1 (with the G2 ship date in view): teardown (2026-09-26)

Run of `skills/pvp-teardown`. Not to be sent cold: offer it after a call or on request. No teardown photos or BOM were available, so parts come from spec text only.

## Sourced
- [S] G1 pledge and retail price: $399 early backer, $489 standard ([CNX Software](https://www.cnx-software.com/2025/02/27/halliday-proactive-ai-smart-glasses-feature-invisible-display-real-time-translation-and-hands-free-control/), 2025-02-27).
- [S] G1 spec: monochrome green microLED "DigiWindow" module (3.5 mm, from Gyges Labs), 35 g, 8 h continuous battery, no camera, controller ring, USB-C (same CNX page). Engadget gives the module as 3.6 mm, so the two sources differ by 0.1 mm.
- [S] Promise: "Shipping is slated to commence by April 2025" (same CNX page). General availability came in Oct 2025 (`outputs/accounts.csv`, Halliday row).
- [S] Campaign size: $3.3M, 8,020 backers, per Kicktraq (`outputs/accounts.csv`, Halliday row; Kicktraq page not reopened).
- [S] What the COO says about G1: the display was unreadable at that size, component choices "prioritized weight over durability", the USB-C port was a problem and G2 uses a pogo-pin clip, and "as a newcomer to the industry, we didn't speak [the manufacturer's] language" ([Engadget](https://www.engadget.com/2216393/halliday-g2-smart-glasses/), 2026-07-21).
- [S] G2: $599 retail, $499 backer, $299 for G1 owners; waveguide prisms in both lenses; 12 h battery; touchpad; no camera; shipment expected September 2026 (same Engadget page).
- [S] Reference values: sourcing agent 5-10% ([Dragon Sourcing](https://www.dragonsourcing.com/top-10-cost-insights-for-hiring-a-china-sourcing-agent/)); pre-shipment inspection $268 per man-day ([V-Trust](https://www.v-trust.com/en/our-network)).

## Estimated
- [E] Parts (from spec text): frame and hinges (moulded or machined), prescription lens, microLED module with optics, battery, PCB with Bluetooth SoC, mic and speaker, ring controller, charging accessory, case. Materials are not stated in any source.
- [E] Factory cost (FOB) $98-171 per G1 unit. Method: 20-35% of the $489 retail price. **The 20-35% ratio is my assumption, with no source**; replace it with a factory quote.
- [E] Landed cost, before freight and duties: $103-188 per unit. Method: FOB × 1.05-1.10 for the sourcing agent (5-10%, sourced above).
- [E] Not estimated: freight, insurance, 3PL, duties and mould amortisation. The HTS code was not looked up, and no tooling quote exists. A human must add both before this number means anything.

## Risks
1. **DFM/engineering (most likely to move the ship date):** G2 changes two interfaces against G1: a waveguide-prism display and a pogo-pin charger instead of USB-C ([Engadget](https://www.engadget.com/2216393/halliday-g2-smart-glasses/)). A new optical part usually needs several sample rounds. Comparable: Creality, filament diameter out of spec in factory tests ([Makers101](https://makers101.com/creality-filament-maker-m1-shredder-r1-live-tracker/)).
2. **Factory translation (most likely to move the ship date):** the team itself names it as the G1 lesson ([Engadget](https://www.engadget.com/2216393/halliday-g2-smart-glasses/)). A waveguide spec has tight tolerances, and a tolerance read differently is the case where a "pass" on one side is a "fail" on the other. Comparable: Halliday G1.
3. **Certification (lower):** a new charging interface may need retesting. **Hypothesis:** no source mentions FCC or CE for G2. Comparable: HOVERAir AQUA, FCC ban ([DroneXL](https://dronexl.co/2026/05/28/hoverair-aqua-global-launch-us-fcc-ban/)).

## Top question for your factory
For the G2 waveguide lens module, which line of the spec does your inspection read differently from our drawing, and what was the pass rate on the pilot lot?

## Confidence
Low. What would make it medium: the BOM, one factory quote, the HTS code, and the pilot-lot pass rate.

## Unverified
- Whether G2 has actually shipped. Search results said non-prescription orders began shipping on 2026-09-15 and prescription orders in October, but I could not identify the page, so I did not use it as a fact.
- Kickstarter pages return 403, so no creator update was read directly.
