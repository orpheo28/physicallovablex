# Campaign 01: tracking

**Source of truth:** `03_DISCOVERY/envoi/SUIVI.md`. This file mirrors it and adds the signal type per account. **State on 2026-09-27: nothing has been sent, so every count is 0** (`SUIVI.md` columns empty).
Drafts: `03_DISCOVERY/envoi/A_ENVOYER.md`, **36 drafts** in 3 batches (#1-#23 enriched list, #24-#26 remaining accounts, #27-#36 new accounts found 27/09); #13 and #21-#23 have no direct channel, so **~32 are sendable**. Follow-ups after 48 h without a reply: `03_DISCOVERY/envoi/RELANCE.md`. Warm track: `03_DISCOVERY/envoi/RESEAU.md` (10 people, target 2 calls before Mon 28/09 11:30).

## Summary table
"Drafts" counts each draft by the main signal it cites in `A_ENVOYER.md`; the signal type is my coding (S1-S6 in `context/signals.md`), not a field in the source files. A human should check it. The same counts feed the performance table in `context/signals.md`.
| Signal | Drafts | Sendable | Sent | Replies | Calls obtained |
|---|---|---|---|---|---|
| S1 Estimated delivery date has passed | 5 | 5 | 0 | 0 | 0 |
| S2 Creator update names a production cause (factory, mold, sample, components, certification, redesign) | 18 | 17 | 0 | 0 | 0 |
| S3 Backer comments about production | 5 | 4 | 0 | 0 | 0 |
| S4 Pre-order extended or "shipping soon" past the date | 2 | 2 | 0 | 0 | 0 |
| S5 Sourcing or supply-chain job posting | 0 | 0 | 0 | 0 | 0 |
| S6 New product announced | 1 | 1 | 0 | 0 | 0 |
| Other (logistics only or no production problem cited) | 5 | 3 | 0 | 0 | 0 |
| **Cold total** | **36** | **32** | 0 | 0 | 0 |

## Warm track (counts only; names stay in `RESEAU.md`, never here)
| Messages planned | Sent | Replies | Calls | Causes coded |
|---|---|---|---|---|
| 10 | 0 | 0 | 0 | — |

## Account table (mirror of `SUIVI.md`, plus the signal type)
| # | Account | Channel | Signal type | Sent (date/time) | Reply | Call booked | Main cause (after call) | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | The Minimal Phone | LinkedIn | Delivery date passed | | | | | |
| 2 | Pilet (Soulscircuit) | Kickstarter message | Update names a cause (factory, redesign) | | | | | |
| 3 | Wordrunner (Astrohaus / Freewrite) | Email | Pre-order extended | | | | | |
| 4 | AIVELA Ring Pro | Website contact form | Update names a cause (factory, redesign) | | | | | |
| 5 | AERIONN Forma | Kickstarter message | Backer comments | | | | | |
| 6 | Halliday | LinkedIn | New product announced | | | | | |
| 7 | SwiftShape | Email | Backer comments | | | | | |
| 8 | Circular Ring 2 | LinkedIn | Delivery date passed | | | | | |
| 9 | Smokpub | Website contact form | Backer comments | | | | | |
| 10 | GAMR (GameX Studios) | Email | Update names a cause (factory, redesign) | | | | | |
| 11 | Phrozen Arco | LinkedIn (company page) | Delivery date passed | | | | | |
| 12 | Looktech AI Glasses | Website contact form | Delivery date passed | | | | | |
| 13 | HOVERAir AQUA | Website (About page, no contact address) | Update names a cause (factory, redesign) | | | | | |
| 14 | eufyMake E1 | Website contact form | Update names a cause (factory, redesign) | | | | | |
| 15 | Trio 3 & Trio 3 Pro (MobilePixels) | Email | Update names a cause (factory, redesign) | | | | | |
| 16 | CyberBrick (Bambu Lab) | Kickstarter message | Other: logistics only | | | | | |
| 17 | Wyrmwood Modular Table (EU shipping) | Website contact form | Other: logistics only | | | | | |
| 18 | LISSOME R1 | Email | Update names a cause (factory, redesign) | | | | | |
| 19 | ZoomYao Max | Kickstarter message | Update names a cause (factory, redesign) | | | | | |
| 20 | Blisstil Serenade | Kickstarter message | Update names a cause (factory, redesign) | | | | | |
| 21 | Roller Pro (Peak Design) | Backerkit FAQ page (no contact address) | Other: logistics only | | | | | |
| 22 | Friend (Omi) | Help-centre page (email obfuscated) | Other: no production problem cited | | | | | |
| 23 | Rokid AR Lite | Website (homepage, no contact address) | Backer comments | | | | | |
| 24 | Valerion VisionMaster | Kickstarter message | Backer comments | | | | | |
| 25 | JSAUX FlipGo | Email | Delivery date passed | | | | | |
| 26 | RingConn Gen 2 | Kickstarter message | Other: logistics only (sizing kits) | | | | | |
| 27 | Mecha Comet (Mecha Systems) | LinkedIn | Update names a cause (antenna redesign, PCB rev 9) | | | | | Batch 3 |
| 28 | PicoIDE (Polpotronics) | Email | Update names a cause (T1 mold samples late) | | | | | Batch 3 |
| 29 | MNT Reform Next (MNT Research) | Website support portal | Update names a cause (part lead times and prices) | | | | | Batch 3 |
| 30 | GameTank (Clydeware) | LinkedIn | Update names a cause (EMC revision) | | | | | Batch 3 |
| 31 | Brilliant Labs Halo | LinkedIn | Pre-order "shipping soon" past Q4 2025 | | | | | Batch 3 |
| 32 | Game Bub (Second Bedroom) | Email | Update names a cause (LCD driver chip shortage) | | | | | Batch 3 |
| 33 | Pebble Round 2 (Core Devices) | LinkedIn | Update names a cause (steel case cosmetic defect) | | | | | Batch 3 |
| 34 | Nocturne (Measure Things) | Email | Update names a cause (tooling change, lead times; medium confidence) | | | | | Batch 3 |
| 35 | Modos Paper Monitor (Modos Tech) | Email | Update names a cause (half of 6" panels failed quality) | | | | | Batch 3 |
| 36 | SlimeVR Butterfly Trackers | LinkedIn | Update names a cause (FCC filing, mould timing) | | | | | Batch 3 |

## How to update
1. Update `03_DISCOVERY/envoi/SUIVI.md` first. It is the source of truth. Fill "Envoyé", "Réponse" and "Call fixé" as things happen.
2. Copy the same values into the account table above. Same row number, same account.
3. Recompute the summary table (and the performance table in `context/signals.md`) by counting rows per signal type. Sent = rows with a date in "Sent". Replies = rows with a reply. Calls = rows with a call booked.
4. After each call, write the verbatim in `03_DISCOVERY/verbatims.md`, then run `skills/call-debrief`: it fills "Main cause" with one tag (design/engineering, components, certification, factory, logistics, cash, demand) and updates `context/signals.md`.
5. Log any follow-up sent from `RELANCE.md` in "Notes" with its date.
6. Warm track: copy only the counts from `RESEAU.md` into the warm-track table above.
7. At the restitution, compare the causes with the success criteria in `brief.md`, then update `context/icp.md` (evolution log) and `CLAUDE.md`. `skills/weekly-update` checks that this file matches `SUIVI.md`.
