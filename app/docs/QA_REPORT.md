# QA report — W10 (26 Sept 2026, evening)

**Verdict: ready with fixes** (fixture path and password mode are solid; section F, the one live UI run, is **not done yet** — waiting for "W9e done").

Test rig: API `:8110` (`DB_PATH=api/data/w10.db`, `OPENROUTER_API_KEY` emptied = fixture path), web `:3110`.
Caveat: another session's `next dev` (pid 93663, port 3111) holds the Next 16 lock on `web/`, so a second dev server could not start from `web/`.
I ran a **snapshot copy** of `web/` (taken ≈ 21:40, uncommitted W9e state) from the scratchpad. Re-check the final `web/` after W9e.
Scripts and screenshots: `tests/results/qa/` (Playwright scripts `b*.mjs`, `g.mjs`; stage dumps in `stages/`).

## A. Automated — PASS
- `uv run pytest`: **225 passed, 3 skipped** (71 s). Log: `tests/results/qa/pytest.txt`.
- `tests/run_prompts.py --base-url :8110`, key unset: **10/10 PASS, no 5xx**; wow 4.1–6.2 s, 4 fallbacks per prompt (expected without a key). Report: `tests/results/20260926-214714.md`.

## B. Browser (no password) — PASS with minor findings
| Check | Result |
|---|---|
| `/` start screen, 10 prompt chips, both example cards | OK. Open example → overview in 0.8 s |
| Deep link `/?mode=idea&prompt=Bike%20light…` | Pre-filled (also `mode=prototype`) |
| Overview lamp + tracker: hero image, Studio render / 3D model / Concept toggle | OK. Captions correct: "Rendered from the CAD — direction Column", "AI concept render — illustrative, not the CAD"; model-viewer loads in ≈ 4 s |
| 3 volumes, margins, cash, break-even, shortlist (3, fictional) | OK, all badged |
| All 13 stages × 2 examples | 26/26 render, no NaN/undefined/error text, no broken image, no console error, ≈ 2 s each |
| Factory Pack: 9 sections (§1–§9), CN block | OK. Print view: see B3 |
| PDF export (both) | Downloads in 0.25 s. 25 pages, A4, 611 CJK characters (CN section pages 3–6, 16, rendered with STSong-Light), labels on numbers (Measured 45 / Sourced 60 / Estimate 310 / Fictional 46), legend footer on each page |
| Stage 2 "Render" on a new project | "Render unavailable — 3D shown instead" ✔ (no key) |
| Stage 3 Edit spec → Save spec → reload | Saved and persisted; edited number becomes Estimate |
| Stage 8 (new project) Run → "Approve recommended quote" | "Approved by you", persists after reload |
| Factory portal: Register capacity | New "QA Test Works (fictional)" appears (9 factories) and its page opens (profile, "not audited", 0 RFQs) |
| `/about`, 404, unknown project, unknown factory | All handled with friendly messages + retry/back |
| Reset demo | Confirm dialog → `/projects` shows only the 2 examples, spec edit gone, factories back to 8, recent-projects list empty |
| Autorun on fixtures (new idea) | Modal stepper 1/7 → 3/7 → 7/7, lands on overview in **5.8 s** (real bike-light CAD, 4 parts, 140×90×40 mm Measured) |

## C. Password mode — PASS
- `APP_PASSWORD=qa-pass` + `API_SHARED_KEY=qa-key`: every page 307 → `/login?next=…`; wrong password → "Wrong password. Try again."; correct → returns to the **deep link, prompt still pre-filled**.
- After login: images, 3D and PDF export work (proxy adds the key).
- `/backend/*` without session → 401 (also `/backend/…/export`); API without key → 401 (incl. `/files/…`); `/health` public → 200; API with key → 200.

## D. Honesty sweep — mostly PASS
- Numbers on overview and stages 5, 7, 8, 11, 12 carry badges either per value or at card level (stage 8 quote table, stage 7 scores = "Fictional — demo data" on the card/section).
- Freight options, FOB and insurance lines: Fictional; duties: Sourced; the rest: Estimate. HTS 8513.10.40.00 links to the CROSS ruling and to USITC.
- "Cached example" banner: appears only where `fallback` is true (new project brief). Never on the two demo projects. ✔
- No real company names in factory data (8 fictional names, all "(fictional)"). "Tether" (stage 13 lamp brand option) is a real trademark: see B14.
- Unbadged numbers (polish, see B12): overview "Parts · BOM lines 6 · 18", share-% in cash and landed breakdowns, financing card text ($63,100, $76,000, 626 buyers), stage 7 "62% loaded / 35 days" (covered by card-level label).

## E. Concept coverage (MONITOR §1) — all present, no missing item
| Concept item | Screen | Click path |
|---|---|---|
| Prompt → product + brand (one prompt) | Start `/` → overview `/projects/{id}/wow` → stage 13 | Type prompt (or chip / deep link) → Start → Skip questions → Start autorun → overview; stage 13 for name, packaging, landing copy, Shopify/Amazon drafts |
| Lovable: industrial design | Stage 2 (3 directions, AI concept render + 3D) and overview toggle | Overview → Open all 13 stages → 02 |
| Lovable: CAD files | Stage 3 (STEP / STL / GLB, viewer), Factory Pack §3 | … → 03; download STEP |
| Lovable: technical specification | Stage 3 (editable spec), Factory Pack §2 | … → 03 → Edit spec |
| Lovable: investment needed | Overview cost tiers + cash; stage 5 (3 volumes, tooling, cert, cash breakdown, BOM with LCSC prices); stage 12 (cash curve) | Overview; stage 05 |
| Lovable: how / where to produce | Stage 6 (process + region + lead time per part), stage 7 | … → 06 |
| Lovable: logistics | Stage 11 (landed cost, HTS/duties, freight options) | … → 11 |
| Alibaba: curated network | Factory portal `/factories` (8 fictional factories), stage 7 shortlist with score breakdown | Nav → Factory portal; stage 07 |
| Alibaba: production MCP, factories offer capacity | `/factories` "Offer your capacity" (`register_capacity`), factory page, stage 7 "Queried the production MCP", stage 8 transcript | Factory portal → Register capacity → factory page |
| Infra: DFM | Stage 4 (measured + AI-reviewed alerts, certification map) | … → 04 |
| Infra: factory selection + negotiation | Stages 7-8 (RFQ, side-by-side quotes, agent transcript EN/中文, approve) | overview "Request quotes" → 08 |
| Infra: tooling | Stage 9 (timeline, payments) + cost in stage 5 | … → 09 |
| Infra: quality control | Stage 10 (ISO 2859-1 plan, defects mapped to spec lines) | … → 10 |
| Infra: financing | Stage 12 (cash curve, 6 financing options) | … → 12 |
| Factory Pack (primitive) | `/projects/{id}/factory-pack` (9 sections), PDF | Overview → Read the Factory Pack; Export Launch Dossier |
| Why now | `/about` covers the translation gap; the generative-AI "why now" point is not on screen (deck only) | (not a bug, noted) |

## F. Live run — DONE (26 Sept, on final web/ = be8a720, fresh copy, ports 8110/3110)
No stale lock remained (no listener on 3111, pid 93663 dead). Live key, models main gpt-6-sol / fast gpt-6-luna.
Prompt "Bike light with brake detection" via deep link (pre-filled ✔) → Start → Skip questions → Start autorun.
| Milestone | Wall-clock |
|---|---|
| Start → project created, brief (live) shown with 5 questions | 6.9 s |
| Autorun stepper 1/7 → 2/7 (+14.5 s) → 3/7 (+24.6 s) → 5/7 (+46.7 s) → 6/7 (+50.7 s) → 7/7 (+54.7 s) | advances stage by stage, never stuck |
| Auto-redirect to overview | +56.1 s after autorun, **63 s total from Start** (target < 3 min ✔) |
Server stage times: s1 6.3 s, s2 12.0 s, s3 11.9 s, s4 21.1 s (slowest), s5 0.1 s, s6 3.3 s, s7 0 s. No fallback, no "Cached example" banner, console clean.
Overview: 3D model loads (direction Signal Pebble, 78×34×27 mm Measured), 1 AI concept render (Concept toggle, caption "AI concept render — illustrative, not the CAD"), 3 volumes ($12.46 / $11.48 / $10.54, margins, cash $42,538, break-even 412, retail $39.00, all Estimate), shortlist of 3 fictional factories. (No "Studio render" toggle on a generated project: normal, only cached examples have it.)
"Generate concept render" on direction C: button became "Rendering…", the render was patched in within about a minute (not precisely timed; 2 of 3 directions rendered afterwards, one with a working image at `/backend/files/…/d1.png`, no error). One direction (B) still shows the button, as designed.
**OpenRouter spend** (`GET /api/v1/key`, `usage`): before $7.3917 → after $7.5487 = **≈ $0.157** for the whole run (stages 1-7 + 2 renders; the key endpoint lags by a few seconds; a first read right after the run showed no change). Limit remaining on the key: $42.45 of $50.
New observations from the live run: B1/B2 not reproducible here (no fallback happened, so the fix could not be judged); stage 4 takes 21 s, so it dominates the autorun; two shortlist factories tie at 78/100 (no tie-break note).
Note: the overview redirect worked in one step; routes were pre-warmed, so the cold-compile delay (B13) was not in these times.

## G. Demo-script dry run (PLAN §6, cached lamp) — 6.2 s of app time, 8 clicks
Path measured: `/` → chip click → Open example (0.8 s, lands on overview) → Open all 13 stages → 04 DFM (1.1 s) → 08 negotiation (0.8 s) → 09 timeline (0.8 s) → 12 cash (1.2 s) → Export (0.3 s). Screenshots `g1…g5`.
Friction:
1. "Prompt typed → wow" in the script: with a key, typing the lamp prompt and pressing **Start** launches a live run (≈ 1 min, not cached); the fast path is the **Open example** card. Use it in the video (or add a cached shortcut for the exact lamp prompt).
2. Autorun costs an extra confirm click ("Skip questions, autorun stages 2–7" → modal → "Start autorun").
3. The sidebar stage jumps are fine, but there is no "next stage" button; the video path needs 4 sidebar clicks.
4. Subtitle "From fixture, 26 Sept 2026" on every stage of the cached examples reads as dev jargon.
5. Tracker overview shows a **−7.9 % margin at 500 units** (correct, honest); be ready to explain it.

## Bugs
| id | severity | screen / route | steps to reproduce | expected | actual | owner | screenshot |
|---|---|---|---|---|---|---|---|
| B1 | major | Overview `/projects/{id}/wow` (and PDF header) | New idea with no key / 402 / failing LLM → autorun → overview | Visible "Cached example" flag, since the brief (stage 1) is another product's fixture | Overview shows lamp-derived retail price ($96.12, €89 brief) for a bike light with **no** banner. Only the stage-1 page and the "cached" tag in the sidebar reveal it. Risk: budget is ≈ $3, a 402 mid-demo silently shows a wrong product | W11 web (W7 if the flag must come from the API) | `5x_fx_wow.png`, `50_after_start.png` |
| B2 | minor | Cached banner (any stage) | Same as B1, open stage 1 | Plain wording ("AI unavailable, showing an example") | Raw exception text: "LLMNotConfigured: [main] OPENROUTER_API_KEY or model env var missing" (or the provider error on a 402) | W11 web | `50_after_start.png` |
| B3 | minor | Factory Pack print `/projects/{id}/factory-pack` → Print | Print/PDF (media print) | All columns inside A4 | Right edge clipped: spec table QTY column and "4 files" count cut off (page 2 of the 8-page print) | W11 web | `pk_both.png` |
| B4 | minor | Stage 12 (and stage 5 cash) vs stage 8 | Lamp: stage 8 approved FOB $13.00 / tooling $9,400; look at stage 12 | Cash curve consistent with the approved quote, or an explicit note | Stage 12 keeps stage 5's $12.50 (first order $25,000, tooling $10,100) and says "Matches stage 5 total". Stage 11 does reconcile ("+1.3 %"), stage 12 does not | W7 backend | `stages/demo_desk_lamp_s12.png` |
| B5 | minor | Stage 5 BOM table | Open stage 5 | Stock column filled for LCSC-sourced lines (README says price + stock) | "STOCK" shows "—" on every line; the PDF does show "Stock 1.09M" | W11 web | `stages/demo_desk_lamp_s05.png` |
| B6 | polish | Stage 9 | Open stage 9 | "1 day" | "1 days" | W11 web | `g4_timeline.png` |
| B7 | polish | PDF §2 and stage 7 shortlist | Read spec table / shortlist reasons | "Injection molding" | Raw enums `injection_molding`, `pcba` (wraps as "injection_mol / ding" in the PDF table) | W6/W7 | dossier PDF p. 3 |
| B8 | polish | Every stage subtitle on the demo examples | Open any stage | "Pre-computed example" | "From fixture, 26 Sept 2026" | W11 web | `stages/*.png` |
| B9 | polish | Overview on 390 px viewport | Resize to phone width | No horizontal scroll | Page scrolls horizontally (desktop demo, low priority) | W11 web | `99_mobile_wow.png` |
| B10 | polish | Generated projects (no studio render) | Open overview / stage 2 of a new project | No failing request | `GET /files/{id}/hero_d1.png` → 404 twice (console 404s; UI falls back to 3D correctly) | W11 web | — |
| B11 | polish | Stage 5 / 10 / 11 | Look at "Pre-shipment inspection $540" | Estimate-mixed number labeled Estimate | Badged Sourced although the 2 man-days behind it are an Estimate (rate is Sourced) | W7 backend | `stages/demo_desk_lamp_s05.txt` |
| B12 | polish | Overview, stage 5/11/12 | Numbers without an own badge | Every number badged | Parts · BOM lines "6 · 18", share-%, financing card figures ($63,100, $76,000, 626 buyers) unbadged | W11 web | `10_lamp_wow.png` |
| B13 | polish | `npm run dev` demo | First visit of a route after start | Instant | Cold route compile: first `/wow` ≈ 31 s. Pre-warm every route or demo on a production build | W9 deploy / Orphéo | — |
| B14 | polish | Stage 13 lamp | Read name options | Names not clashing with a known brand | "Tether" is a real trademark (crypto) | W6 fixtures | `stages/demo_desk_lamp_s13.png` |
| B15 | polish | Factory page of a self-registered factory | Register capacity → open its page | Empty stats shown as "no data" | "On-time 0 %, defect 0 %, archetype balanced" shown as facts | W5/W11 | `73_new_factory_page.png` |

Counts: blocker 0 · major 1 · minor 4 · polish 10.

## Not done / known issues
- Section F (live run, spend) — pending "W9e done".
- Tested on a snapshot copy of `web/`, not the final W9e commit; `web/` must be re-smoke-tested after W9e (start, both examples, autorun, export).
- Not tested: the stdio production MCP server, Docker/Railway deployment, non-fixture LLM outputs for stages 8-13 (live path only covers stages 1-7 in autorun).
- CN text quality not judged (machine-translated, labeled as such); STSong-Light is not embedded in the PDF, so a viewer without a CJK fallback font would show boxes (Preview and Acrobat were not checked visually beyond `pdftoppm`).

## Regression (final) — fixtures only, no live calls (26 Sept, evening)
Latest commit, fresh copy of `web/`, API on `:8110` with `OPENROUTER_API_KEY` emptied. Scripts and evidence in `tests/results/qa/reg/` (+ `stages/`).

**Smoke: PASS.** `pytest` 227 passed / 3 skipped; `run_prompts` 10/10, no 5xx; both demo overviews (hero, Studio/3D/Concept toggle, captions correct); all 13 stages of both examples render (no NaN / error text, no broken image, no console error); Factory Pack 9 sections; PDF export of both examples downloads in 0.25 s; portal (register capacity → "(fictional)" factory + page, 8 → back to 8 after reset); `/about`, 404; Reset demo; spec edit persists; login mode (redirect with deep link kept and prompt pre-filled, wrong password message, `/backend` 401 without session, API 401 without key / 200 with key, 3D + PDF work after login).

| id | status | evidence |
|---|---|---|
| B1 | **fixed** | New idea, no key → autorun → overview shows banner "Cached example — AI was unavailable for part of this run — some figures come from a pre-computed example" (`reg/B1_overview.png`); Factory Pack page has it too; PDF cover: "Cached example — AI was unavailable… Numbers derived from those stages describe the example product, not this project", and the stage table marks Brief "cached example (fallback)" (`reg/B1_dossier_newidea.pdf`) |
| B2 | **fixed** | Banner reads "AI unavailable (no API key / credits). This is a pre-computed example…", raw error moved behind a collapsed "Details" (`reg/B2_banner.png`) |
| B3 | **partly fixed** | Print no longer clips (QTY column and counts visible, 11 pages). New residual: in the §2 spec table, Dimensions and Wall text overlap ("180×40×18 mm" runs into "2 mm") — cosmetic, `reg/pkz-02.png`. Downgraded to polish (B3b) |
| B4 | **fixed** | Lamp stage 12 now: "Differs from stage 5 by $+664 ($58,678 vs $58,014) because the negotiated quote qt_orchid_v2 replaced the estimate: FOB $13.00 vs $12.50 × 2,000, tooling $9,400 vs $10,100…"; milestones say "2,000 × negotiated FOB" |
| B5 | **fixed** | Stage 5 BOM Stock column filled (e.g. C210311 → 1.09M) |
| B6 | **fixed** | Stage 9 shows "1 day" |
| B7 | **fixed** | No `injection_molding` / `pcba` enums left in stages 1-13 or in the PDF (spec and tooling tables read "Injection molding") |
| B8 | **fixed** | 0 stage subtitles say "From fixture"; now "Pre-computed example" / "Cached example, …" |
| B9 | **partly fixed** | Overview at 390 px now overflows by 6 px only (scrollWidth 396). Not needed for the Mac demo; polish |
| B10 | **fixed** | New-project run, overview + PDF + pack: console clean, no 404 shown (`p.errs` empty) |
| B11 | **fixed** | Stage 5 "Pre-shipment inspection $540.00" now badged Estimate |
| B12 | **mostly fixed** | Overview now "6 parts · 18 lines" (unit words); financing card figures no longer flagged by the scan; remaining unbadged: share-% in the cash and landed breakdowns (derived values, polish) |
| B13 | **not fixed** (process) | Cold `npm run dev` compile is unchanged by code; use pre-warm or a production build for the jury |
| B14 | **fixed** | Lamp stage 13 names: "Magwick — … coined, short, ownable. Trademark search needed before use.", "Orlune Column" (Tether gone) |
| B15 | **fixed** | Self-registered factory shows "TRACK RECORD — No track record yet / No completed orders on record" instead of 0 % (`reg/B15_factory.png`); archetype still reads "balanced" (cosmetic) |

Remaining open (all polish): B3b print table overlap, B9 6 px mobile overflow, B12 share-% badges, B13 dev-server cold compile, archetype "balanced" on self-registered factories, two-way tie at 78/100 without tie-break note.
Counts now: blocker 0 · major 0 · minor 0 · polish 6 open.
