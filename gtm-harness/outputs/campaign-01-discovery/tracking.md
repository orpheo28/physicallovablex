# Campaign 01: tracking

**Source of truth:** `03_DISCOVERY/envoi/SUIVI.md`. This file mirrors it and adds the signal-by-signal table from `brief.md`. **State on 2026-09-26: nothing has been sent, so every count is 0.**
Drafts: `03_DISCOVERY/envoi/A_ENVOYER.md` (23 messages). Follow-ups after 48 h without a reply: `03_DISCOVERY/envoi/RELANCE.md`.

## Summary table (from `brief.md`)
| Signal | Planned (drafts) | Sent | Replies | Calls obtained |
|---|---|---|---|---|
| Estimated delivery date has passed | 4 | | | |
| Backer update mentioning the factory, molds, a failed sample or a manufacturer change | 9 | | | |
| Backer comments about production | 4 | | | |
| Pre-order extended or long stock-out | 1 | | | |
| Sourcing or supply-chain job posting at a small company | 0 | | | |
| New product announced | 1 | | | |
| Other (logistics only or no production problem cited; not a signal in `context/signals.md`) | 4 | | | |
| **Total** | **23** | 0 | 0 | 0 |

"Planned" counts the drafts by the main signal each one cites in `A_ENVOYER.md`. The signal type is my coding of that cited signal, not a field in the source files. A human should check it. The brief targets 30 messages; the drafts cover 23, because only 23 accounts have a contact and a channel (`A_ENVOYER.md`, header).

## Account table (mirror of `SUIVI.md`, plus the signal type)
| # | Account | Channel | Signal type | Sent (date/time) | Reply | Call booked | Main cause (after call) | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | The Minimal Phone | LinkedIn | Delivery date passed | | | | | |
| 2 | Pilet (Soulscircuit) | Kickstarter message | Backer update (factory, redesign) | | | | | |
| 3 | Wordrunner (Astrohaus / Freewrite) | Email | Pre-order extended | | | | | |
| 4 | AIVELA Ring Pro | Website contact form | Backer update (factory, redesign) | | | | | |
| 5 | AERIONN Forma | Kickstarter message | Backer comments | | | | | |
| 6 | Halliday | LinkedIn | New product announced | | | | | |
| 7 | SwiftShape | Email | Backer comments | | | | | |
| 8 | Circular Ring 2 | LinkedIn | Delivery date passed | | | | | |
| 9 | Smokpub | Website contact form | Backer comments | | | | | |
| 10 | GAMR (GameX Studios) | Email | Backer update (factory, redesign) | | | | | |
| 11 | Phrozen Arco | LinkedIn (company page) | Delivery date passed | | | | | |
| 12 | Looktech AI Glasses | Website contact form | Delivery date passed | | | | | |
| 13 | HOVERAir AQUA | Website (About page, no contact address) | Backer update (factory, redesign) | | | | | |
| 14 | eufyMake E1 | Website contact form | Backer update (factory, redesign) | | | | | |
| 15 | Trio 3 & Trio 3 Pro (MobilePixels) | Email | Backer update (factory, redesign) | | | | | |
| 16 | CyberBrick (Bambu Lab) | Kickstarter message | Other: logistics only | | | | | |
| 17 | Wyrmwood Modular Table (EU shipping) | Website contact form | Other: logistics only | | | | | |
| 18 | LISSOME R1 | Email | Backer update (factory, redesign) | | | | | |
| 19 | ZoomYao Max | Kickstarter message | Backer update (factory, redesign) | | | | | |
| 20 | Blisstil Serenade | Kickstarter message | Backer update (factory, redesign) | | | | | |
| 21 | Roller Pro (Peak Design) | Backerkit FAQ page (no contact address) | Other: logistics only | | | | | |
| 22 | Friend (Omi) | Help-centre page (email obfuscated) | Other: no production problem cited | | | | | |
| 23 | Rokid AR Lite | Website (homepage, no contact address) | Backer comments | | | | | |

## How to update
1. Update `03_DISCOVERY/envoi/SUIVI.md` first. It is the source of truth. Fill "Envoyé", "Réponse" and "Call fixé" as things happen.
2. Copy the same values into the account table above. Same row number, same account.
3. Recompute the summary table by counting rows per signal type. Sent = rows with a date in "Sent". Replies = rows with a reply. Calls = rows with a call booked.
4. After each call, write the verbatim in `03_DISCOVERY/verbatims.md`, then fill "Main cause" with one bucket: design/engineering, components, certification, factory or logistics (coding rule in `brief.md`).
5. Log any follow-up sent from `RELANCE.md` in "Notes" with its date.
6. At the restitution, compare the causes with the success criteria in `brief.md`, then update `context/icp.md` and `CLAUDE.md`.
