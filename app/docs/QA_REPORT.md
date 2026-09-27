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

---

# Final QA — pivot (W23, 27 Sept 2026, 03:10-04:10)

**Verdict: ready with fixes.** The scripted live path (Whoop start + 4 refines, restore, `whoop_kitesurf` showcase, Launch Dossier, MCP) runs end to end with no error, no page scroll and 0 console errors. Five lines of the demo script promise something the screen does not show (see B), the SpO2 refine double-counts a sensor, and several gallery showcases show unit economics a VC will not believe (drone 97 % margin, smartphone $36/unit, solar −63 % margin, changing table −108 %). Fix the script wording before the freeze (W18, 30 min). Keep the jury away from the cost panels of those showcases unless W21 fixes them.

Rig: exactly Orphéo's commands, run from this checkout: `cd web && npm run sync-docs` (10 files), then `SKIP_BUILD=0 API_PORT=8123 WEB_PORT=3123 DB_PATH=api/data/w23.db FILES_DIR=api/data/files_w23 scripts/demo_start.sh`, which printed **READY** (every warm-up request ok). Browser: Playwright Chromium. Evidence: `tests/results/final/`. No code was changed. I filled the "Observed diffs" table in `docs/DEMO_SCRIPT.md`.

## A. Automated — PASS
| Check | Result |
|---|---|
| `uv run pytest` (whole) | **527 passed, 31 skipped**, 281 s (`pytest.txt`) |
| `npm run build` | OK, 0 warnings (`npm_build.txt`). The last build was made with the default API URL (:8000), so `SKIP_BUILD=1` works for the standard demo ports |
| `npm run lint` | exit 0 |
| `npx tsc --noEmit` | exit 0 |

## B. Timed rehearsal (live key, one run) — PASS, with script mismatches
| Step | Wall-clock | What changed on screen |
|---|---|---|
| Start: Whoop prompt → v1 | **20.5 s** (AI CAD patched in at 41.8 s; background checks at 43.8 s) | 3D band, 44 × 30 × 10 mm Measured, $30.12 / $28.83 / $27.65, 3 fictional factories, 4 certs, CAD code tab |
| Add SpO2 and skin-temperature sensing | **5.1 s** | 2 LCSC parts (Sourced), unit cost $28.83 → $43.54 |
| Make it pink | **3.9 s** (render at 16.8 s) | Colour chip only |
| Thinner, 8 mm pod | **14.3 s** | 8.0 mm Measured, AI CAD program v1 → v2 (real code diff) |
| Restore v2 → back to v4 | server 0.01-0.03 s, plus a confirm() click each | version switches |
| Target retail $149 | **3.1 s** | Target price chip only |
| **Total waiting** | **46.9 s** | |
| Showcase `whoop_kitesurf` Studio / Overview / stage 8 | 0.7 s / 0.07 s (client-side) / 0.65 s | 13/13, "Auto-approved (autofill mode)" + "Change factory" |
| Launch Dossier PDF (`whoop_kitesurf`) | 0.29 s, 37 pages | EN + CN (1,480 CJK characters on pages 5-8 and 22-23, "machine-translated" note), §10 "Engineering & prototype path" ($317, 4 weeks), "Build strategy — Module assembly", firmware "Generated code — not compiled or tested", assumption **a8_autofill** in the register (id column wraps as "a8_autof / ill"). Labels: Measured 61 · Sourced 76 · Estimate 394 · Fictional 71 |

Full observed-diffs table: `docs/DEMO_SCRIPT.md` → "Observed diffs". **Where the script and the screen disagree:**
1. 1:20: "the certification map changed: [read the row]". **Nothing changed.** SpO2 adds no certification row and shows no certification chip.
2. 1:20: the SpO2 refine adds "Optical heart-rate and SpO2 sensor" LCSC C6454833 $12.18. That is the same part v1 already has as "Optical heart-rate / PPG sensor module". Unit cost rises by +$14.71 (+51 %) for a duplicate part. An engineer on the jury will notice.
3. 2:05: "a colour change shows its cost: [read the delta]". The delta is $0, and the diff does not say "no change".
4. 2:30: "Thinner tightens the battery and sensor stack, and the checks tell me now". **No check changes.** Battery stays 200 mAh, 54 h, warn; there is no DFM or physics chip.
5. 3:30: "Margin at 3 volumes, break-even units". **Not in the Studio.** The $149 refine shows one price chip. The margins (53.7 / 59.3 / 61.5 %) and break-even (193) are on the Overview and stage 5 only.
6. 3:50: "Make it on the recorded `whoop_kitesurf`". The showcase header offers **"Make it again"**, a live re-run (≈ $0.34, 54-88 s), next to "Open overview". Tell the presenter to click **Open overview**, not Make it.

## C. Gallery (11 showcases × Studio, Engineering tab, CAD code tab, Overview, at 1440×900) — PASS on rendering, FAIL on credibility of some numbers
- All 44 views: **no page scroll**, **0 console errors**, **0 HTTP ≥ 400**. Studio opens in ≈ 1.9 s and the Overview in ≈ 2.2 s (full navigation). The four labels show on every Studio view. Also checked at 1280×800 and 1512×982: no page scroll on the app routes.
- Solar: "Cost per installation", "Installer shortlist", "Top installers", site-install build path ✔. PVGIS 1,227.2 kWh/kWp/yr is Sourced, and the 5.59 kWp / 6,860 kWh/yr figures match the docs ✔. **But the numbers conflict:** see F4.
- Drone: thrust-to-weight 3.7 pass, hover time 24.1 min warn, class C1 at 324 g (threshold cites EU 2019/945, checked 2026-09-27) ✔. The checks sit below the fold of the Engineering tab.
- ODM notes on minimal_phone, instant_camera and home_robot ✔. The hair dryer is module assembly.
- "AI-generated CAD (concept level)" appears only as a hover tooltip on the CAD code header, not as visible text (F12).

## D. Production MCP — PASS
- `factory_agent` against `http://localhost:8123/mcp` (no local token): registered **Tidewater Wearables (fictional)**. Portal count went from 15 to 16, and it ranks #1 at 96.0/100.
- `buyer_agent`: 2 searches → Tidewater covers both processes → profile ("not audited") → RFQ `rfq_e42923ad69`. The RFQ is visible on the Tidewater page.
- "Connect your agent" panel on `/factories` shows `claude mcp add --transport http physicallovablex http://localhost:8123/mcp --header "Authorization: Bearer <your token>"`. URL correct; see F22. `/mcp-status` returns 200.
- Claude Code 2.1.238 with the local MCP (inline `--mcp-config`, so the user config was not modified), the 3 MCP_DEMO prompts:
  - Prompt 1: 52 s. Calls: search_capacity × 2 (LSR, PCBA), get_factory_profile × 2. It also **sent 2 RFQs already** (1k/2k/5k tiers) and picked Coralline 94.1.
  - Prompt 2: 19 s. request_quote 500/2,000/10,000 → a second RFQ.
  - Prompt 3: 28 s. register_capacity → Tidewater `f_249680c559`.
  - Total ≈ 100 s against the 60 s slot (F15). Anthropic cost of these 3 prompts ≈ $1.53 (Claude Code account, not OpenRouter). I ran `POST /demo/reset` afterwards.
- Not tested: Claude Desktop (GUI) and the deployed Railway endpoint.

## E. Docs — PASS (3 claims false)
- `/docs`, the 7 pages, `/agents.md` (text/markdown) and `/llms.txt` (text/plain): 200.
- Login mode (`APP_PASSWORD=qa-pass`, `API_SHARED_KEY=qa-key`):
  - All 10 doc URLs are public (200, no redirect).
  - `/`, `/examples`, `/factories`, the Studio and `/mcp-status` redirect 307 to `/login?next=…`.
  - `/backend/*` returns 401 without a session.
  - API: `/health` 200; `/examples` and `/files` 401 without the key. `/mcp` 401 without a token, 200 with `Bearer qa-key`.
  - Wrong password → `?error=1`. The correct one returns to the deep link, and the gallery shows 12/12 images.
- Mobile (390 px): the app routes show the "Desktop only, for now" gate. Docs are readable, with no horizontal scroll.
- 10 doc claims checked against the API:

| # | Claim (file) | Verdict | Evidence |
|---|---|---|---|
| 1 | 7 MCP tools (production-mcp, MCP_DEMO) | TRUE | `tools/list` → 7 names |
| 2 | `GET /examples` → 11 showcases, 7 complete + 4 start-only (overview, PRD §8.5) | TRUE | 7 × `stages_done` 13, 4 × 7 |
| 3 | Biarritz 35 m² → 5.59 kWp, 6,860 kWh/yr, PVGIS Sourced (engineering) | TRUE | `/projects/demo_solar_biarritz/engineering` |
| 4 | Kitesurf wearable prototype $317, 4 weeks (engineering, PRD) | TRUE | Dossier §10 |
| 5 | Drone C0 < 250 g / C1 < 900 g / C2 < 4 kg, EUR-Lex (engineering) | TRUE | threshold text cites CELEX:32019R0945 |
| 6 | Firmware README says "Generated code — not compiled or tested" (engineering: "begins") | TRUE (line 3, after the title) | `firmware.zip` |
| 7 | v1 in under 35 s, AI CAD in the background (`cad_pending`) (engineering) | TRUE | 20.5 s, AI CAD at 41.8 s |
| 8 | "The 8 factories and 3 installers" (overview, limits, README, DEMO_SCRIPT, MCP_DEMO) | **FALSE** | `/factories` after reset: 11 factories + 1 integrator + 3 installers (15) |
| 9 | "Each refine: 3.9-4.9 s" (overview) | **FALSE for geometry** | colour/feature/price 3.1-5.1 s; "thinner, 8 mm" 14.3 s |
| 10 | Refine example "add heart-rate sensing" (overview) | **MISLEADING** | the Whoop v1 already has a PPG sensor; DEMO_SCRIPT itself says it shows no delta |

Every route cited in `studio-api.md` exists in the API's OpenAPI schema. The one exception is the shorthand "`GET /engineering`", which refers to `/projects/{id}/engineering`.

## F. Honesty sweep — mostly PASS, 2 major issues
- ✔ Every number on the Studio, Overview and stage 8 carries a badge. Factories and installers end in "(fictional)" and carry the "Fictional — demo data" pill. Self-registered factories read "not audited" and "No track record yet".
- ✔ Firmware is labeled "not compiled or tested", in the Dossier and in the zip README.
- ✔ Stage 2 and stage 13 of all showcases contain no real brand names. Generated names reuse across products (Veylo, Nuvora; F21). The user's own prompts mention Whoop and Dyson, which is fine.
- ✗ **Wrong "Sourced" labels** (F2, `F_sourced_bom_lines.txt`): "Smartphone ODM mainboard assembly" at $0.0518 Sourced. One LCSC part, C7587761 at $0.0124, is "Sourced" as a pistol-grip trigger switch, a TRIAC heater switch and motor/heater control switches. "Flash assembly" $0.0274. "Grouped passive components" and "Power regulation and passives group" both C6533463 at $0.0117. A wrong Sourced label breaks the core honesty promise.
- ✗ **Placeholder estimates make whole products implausible** (F3): drone 4S flight battery $0.28, motors $1.10, gimbal camera $1.38 → $18.77/unit, 97.1 % margin, break-even 15 units. Smartphone $35.69/unit. Stick vacuum $20.08. Instant camera $11.37. They are labeled Estimate, so it is honest to the letter, but the jury reads "$18.77 drone, 97 % margin".
- ✗ AI-CAD concept-level label: tooltip only (F12).
- Claims lists "W18d / W25b": **not found in the repo** (no file mentions them). Instead I checked the 10 doc claims in E, the README "Real vs simulated" block, and PRD §8.2-8.5:
  - TRUE: v1 18-24 s (20.5), colour/feature 4-7 s (3.9-5.1), geometry 11-24 s (14.3), restore fast, Make it instant on showcases, render ≈ 16 s (16.8), 8 mm Measured (8.0), a8_autofill present, build strategy per product, 11 showcases, drone checks, PVGIS.
  - FALSE: "the certification map changes" (not for SpO2) and "8 factories".

## G. Robustness
- **Key removed** (API restarted with `OPENROUTER_API_KEY=` empty; `/health` reports `llm_configured: false`):
  - Showcases, the PDF export (200) and the portal work.
  - A refine fails calmly: "The AI is not configured on this server, so prompts cannot be interpreted. Nothing changed — version 1 is still current." ✔
  - **But a new Studio start with the Whoop prompt gives v1 titled "Magnetic Rechargeable Desk Lamp: sensor pod on a strap"**, lamp cost $11.09 and a "Target retail price $39" chip, with **no Cached-example banner in the Studio**: only a small "cached" tag next to Brief. The Overview does show the banner. On a 402 mid-demo the presenter would see a wrong product name (F6).
- Login mode, mobile gate and docs on mobile: PASS (see E).
- 3 viewports: 1280×800, 1440×900 and 1512×982 with no page scroll on any app route. At 1280 the sidebar hides "Factory Pack" (F25).
- `demo_start.sh` guard works: with `SKIP_BUILD=1` on a `web/.next` that another session had rebuilt for API :8115, 38 warm-up requests failed and **READY was not printed** ✔ (F16).

## H. Demo friction
1. On the showcase, "Make it again" is the primary-looking action; the presenter needs "Open overview" (F7).
2. Restore needs a browser confirm() dialog per click. Its text mentions quotes and brand even when none exist (F23).
3. The Studio suggestion chip "Add heart-rate and HRV sensing" invites the no-delta prompt.
4. Margin and break-even after "Target retail $149" require a click to Overview.
5. The drone checks sit below the fold of the Engineering tab (scroll inside the panel).
6. The Overview reached by client navigation from the Studio flashes $0.00 and an empty shortlist for under 1 s (F18).
7. The MCP moment takes ≈ 100 s in Claude Code, and prompt 1 already sends RFQs (F15).
8. Home CTA wording changes with width: "Autofill steps 1–7" vs "Autofill all 13 steps" (F24).

## Bugs
| id | severity | where | repro | expected | actual | owner | screenshot |
|---|---|---|---|---|---|---|---|
| F1 | major | Studio refine (Whoop live) | Whoop prompt → "Add SpO2 and skin-temperature sensing." | SpO2 reuses the existing PPG sensor (or swaps it), cost delta ≈ skin-temp only | Adds a 2nd "Optical heart-rate and SpO2 sensor" LCSC C6454833 $12.18; unit $28.83 → $43.54 | W21 backend | `B2_spo2_settled.png`, `B3_pink_settled.png` |
| F2 | major | Stage 5 BOM of showcases (and Dossier) | open `demo_minimal_phone` / `demo_hair_dryer` / `demo_stick_vacuum` stage 5 | "Sourced" only for a plausible catalogue match | Smartphone mainboard $0.05 Sourced; one $0.012 part (C7587761) Sourced as 3 different switches; flash assembly $0.03 | W21 backend | `F_sourced_bom_lines.txt` |
| F3 | major | Gallery unit costs, Overview margins | open `/examples`, drone / phone / vacuum / camera overview | module-level prices for modules (battery, motors, display, camera) | Drone $18.77/unit, 97.1 % margin, break-even 15; phone $35.69; vacuum $20.08; camera $11.37 (placeholder $0.28-$2.21 per module) | W21 backend | `C0_examples.png`, `C_drone_follow_overview.png` |
| F4 | major | `demo_solar_biarritz` Overview / Studio | open overview | one installation priced consistently with engineering (€10,621) | Margins −71.9 / −62.9 / −54.6 %, "Break-even: not reachable" (landed $21,105.71 > retail $12,960), "Cash, first 2,000 [installations]: $42,556,864", tiers 500/2,000/10,000 installations for one roof; EUR in engineering vs USD in costs; v2 diff "$2,951.62 → $10,146.17" after adding a battery priced $0.30 | W21 backend | `C_solar_biarritz_overview.png`, `C_solar_biarritz_Engineering.png` |
| F5 | major | DEMO_SCRIPT live table | follow the script lines at 1:20, 2:05, 2:30, 3:30, 3:50 | say what the screen shows | cert map does not change; pink cost delta $0 unstated; no check changes on 8 mm; margin not in Studio; showcase button is "Make it again" | W18 docs | `B2_*`, `B4_*`, `B6_price_settled.png`, `B7_whoop_showcase_studio.png` |
| F6 | major | Studio, fallback / 402 / no key | no key → Whoop prompt → Start designing | "Cached example" banner in the Studio, product name kept | v1 "Magnetic Rechargeable Desk Lamp: sensor pod on a strap", lamp costs, "$39" chip; only a tiny "cached" tag (Overview has the banner) | W15 web (+W21 summary) | `G_nokey_refine.png`, `G_nokey_overview.png` |
| F7 | major | Showcase Studio header | open `/projects/demo_whoop_kitesurf/studio` | the instant path is obvious | "Make it again" (live, ≈ $0.34, 54-88 s) sits next to "Open overview"; one wrong click on stage starts a live run | W15 web / W18 docs | `B7_whoop_showcase_studio.png` |
| F8 | major | `changing_table` showcase Overview | open overview | positive or explained margin | unit $165.38 > retail $149, margin −108 %, break-even 0 | W21 backend | `C_changing_table_overview.png` |
| F9 | minor | Engineering (live Whoop) | Whoop prompt → Engineering | generic wearable pack | "Wearable (water sports, skin contact)", IP68 target, for a prompt with no water use | W21 | `B4_engineering.json` |
| F10 | minor | Stage 5 BOM (live Whoop) | Whoop v1 stage 5 | MCU and charger priced as such | nRF52832 at $0.14 ("placeholder for an 'antenna' line"); MCP73831 at $2.21 ("'cell' line"); nRF52832 and BMI270 not in the snapshot | W21 | — |
| F11 | minor | Studio diff | "Make it pink", "Thinner, 8 mm" | "Cost: no change", "Certifications: no change" (PRD §8.2) | categories without change are silent | W15 / W21 | `B3_pink_settled.png` |
| F12 | minor | CAD code tab | any Studio → CAD code | visible "AI-generated CAD (concept level)" | only in a `title` tooltip | W15 | `C_whoop_kitesurf_CAD_code.png` |
| F13 | minor | Docs | read limits / overview / README / DEMO_SCRIPT / MCP_DEMO | factory count matches the network | "8 factories" vs 11 factories + 1 integrator + 3 installers | W18 | — |
| F14 | minor | `docs/public/overview.md`, Studio chips | read "Refine" row, "Recorded timings" | examples that show a delta, geometry timing | "add heart-rate sensing" example, "Each refine: 3.9-4.9 s"; Studio chip "Add heart-rate and HRV sensing" | W18 / W15 | `B1_v1_settled.png` |
| F15 | minor | MCP moment (Claude Code, local) | run the 3 MCP_DEMO prompts | ≈ 60 s, RFQ at prompt 2 | 52 + 19 + 28 s ≈ 100 s; prompt 1 already sends 2 RFQs, prompt 2 duplicates | W18 docs (prompt wording / timing) | `mcp_p1-3.jsonl` |
| F16 | minor | `scripts/demo_start.sh` + shared `web/.next` | `SKIP_BUILD=1` after another session built for :8115 | reuse only a build for the same API port (as documented) | the web proxy targets :8115, 38 warm-up FAIL (READY withheld, correctly). On demo day, use `SKIP_BUILD=0` or no other session building | W9 deploy | `demo_start_login.log` (first run) |
| F17 | minor | `.env` | inspect | `APP_PASSWORD` empty (DEMO_DAY) | set (4 chars). No effect today (web does not read the root `.env`), but contradicts the checklist | W9 / Orphéo | — |
| F18 | polish | Overview after Studio → "Open overview" | click through | numbers on first paint | ≈ 0.5 s of "$0.00" and an empty shortlist | W15 | `B8_whoop_overview.png` |
| F19 | polish | Stage 8 (autofill) | `whoop_kitesurf` stage 8 | one approval state | "Recommendation … Awaiting approval." shown with "Auto-approved (autofill mode)" | W21 | `B9_whoop_stage8.png` |
| F20 | polish | Dossier assumption register | PDF p. 33 | full id | "a8_autof / ill", "a8_anch / or" wrap | W21 export | `whoop_kitesurf_dossier.pdf` |
| F21 | polish | Stage 13 names | compare showcases | unique names | "Veylo" (band, vacuum), "Nuvora" (vacuum, changing table) | W21 fixtures | — |
| F22 | polish | "Connect your agent" panel | `/factories` locally | command matching MCP_DEMO (`physicallovablex-local`, no header locally) | name `physicallovablex` plus a `<your token>` header | W15 | `D_portal.png` |
| F23 | polish | Restore | click "Restore v2" | in-app confirm; text fits the state | native `window.confirm`, mentions quotes/brand when none exist | W15 | — |
| F24 | polish | Home CTA | 1440 vs 1512 | one label | "Autofill steps 1–7 with AI" vs "Autofill all 13 steps with AI"; status says 13 | W15 | `G_1512__mode_idea.png` |
| F25 | polish | Sidebar at 1280×800 | open a Studio | "Factory Pack" visible | cut off below "Brand & listing" | W15 | `G_1280_projects_demo_whoop_kitesurf_studio.png` |
| F26 | polish | Example cards | `/examples` | full label | "$27.19/unit @ 2,000 (E..." truncates "Estimate" | W15 | `C0_examples.png` |
| F27 | polish | Firmware | `whoop_kitesurf` firmware | Zephyr for BLE (docs) | Arduino project "for generic (BLE GATT …)" | W21 | `fw.zip` |
| F28 | polish | AI CAD edit | "Thinner, 8 mm pod" code diff | the parameter drives the geometry | loft z-planes edited as literals next to `P["pod_thickness"]` | W21 | `B4_cad_code.diff` |

Counts: **blocker 0 · major 8 · minor 9 · polish 11.**

## Live spend
OpenRouter `GET /api/v1/key` `usage`: before **$10.9098** → after **$11.2222** = **$0.312** (budget $0.60). That covers the Whoop start, 4 refines and the background AI CAD, renders, DFM review and LLM firmware. Every other check used fixtures or ran with the key removed. Separately, the Claude Code MCP run cost ≈ $1.53 on the Anthropic account.

## Before Tuesday (recommended, in order)
1. W18: rewrite the 5 script lines in F5. Say "no change" for certifications, drop the battery sentence, read margin on the Overview or drop the step, and say "Open overview" on the showcase. Fix the "8 factories" count.
2. W21: F1 (do not add a PPG when one exists). It is cheap and it is on the live path.
3. Presenter: do not open the cost panels of solar, changing_table, drone or phone (F3, F4, F8). Use the drone Engineering tab (checks) only.
4. W15: add the Cached-example banner to the Studio (F6). It is the fallback path of the live demo.
5. Demo day: `SKIP_BUILD=0` (or make sure no other session rebuilt `web/.next`), `POST /demo/reset` after the MCP rehearsal.

---

# Final regression — pass-5 candidate (W23b, 27 Sept 2026, 13:20-14:50)

**Verdict: ready for pass-5.** Blockers: none. Of the 28 "Final QA — pivot" bugs, 19 are fixed, 2 partly fixed, 5 not fixed (minor or polish) and 2 not re-verified (see the table). The scripted live path now matches the script line by line:
- SpO2 upgrades the existing sensor and adds the FDA row.
- "Cost unchanged · certifications unchanged" is printed on the card.
- Margin and break-even appear in the Studio strip.
- The showcase header offers "Open overview".
- The MCP moment takes 79 s.

Three new major issues should go into pass-5:
- The solar showcase shows three different "per installation" figures, and its Studio diff still prints a battery at $0.30.
- A rare proxy reset can make a 13/13 showcase Overview show "HTTP 500" and an **"Autofill all 13 steps with AI"** button.
- A rehearsal now costs $0.92 (it was $0.31), mostly from photos.

Rig: exactly as on demo day. Ports 8000/3000 were free: `cd web && npm run sync-docs` (10 files), then `SKIP_BUILD=0 scripts/demo_start.sh` printed **READY** (default DB `api/data/app.db`). Login mode was rerun with `SKIP_BUILD=1 APP_PASSWORD API_SHARED_KEY` and also printed READY. Evidence: `tests/results/final2/`. No code was changed. Everything was stopped at the end; `web/.next` is the :8000 build from 13:22.

## 1. Automated — PASS
`uv run pytest` **551 passed, 31 skipped** (291 s) · `npx tsc --noEmit` exit 0 · `npm run lint` exit 0 · `npm run build` (inside demo_start) OK.

## 2. Re-verification of F1-F28
| id | status | evidence |
|---|---|---|
| F1 SpO2 duplicate PPG | **fixed** | "Component upgraded: Optical PPG heart-rate sensor → Optical heart-rate / SpO2 sensor (MAX30102)", only the skin-temperature part is added (LCSC C7472806 $4.10); unit cost +$4.79 (`B2_spo2_settled.png`) |
| F2 wrong "Sourced" matches | **mostly fixed** | smartphone mainboard, TRIAC and trigger switches, flash assembly and grouped passives are gone. Residual: home_robot "DC-DC buck converter module" $0.0512 Sourced (N11) (`F_sourced_bom_lines.txt`) |
| F3 implausible gallery economics | **fixed** | drone $190.54 (73.8 %), phone $183.90 (54.5 %), vacuum $98.09 (39 %), camera $65.74 (53 %) (`C_economics.txt`) |
| F4 solar negative margins / $42 M cash | **partly fixed** | one installation, 44.7 % margin, break-even 3 installations, cash $111,639, battery $3,400 in stage 5. New inconsistencies: N1, N2 |
| F5 script lines vs screen | **fixed** | every line of the live table matched the screen (section 3) |
| F6 no banner in Studio on fallback | **fixed** | "Cached example — AI unavailable (no API key / credits)… may show another product such as the desk lamp" plus a "First version from a pre-computed example" card (`G_nokey_refine.png`) |
| F7 "Make it again" next to "Open overview" | **fixed** | the showcase header shows only "Open overview" (orange) (`B9_showcase_studio.png`) |
| F8 changing table −108 % | **fixed** | $122.53 unit, 11.1 % margin, break-even 314 |
| F9 live Whoop gets "water sports" pack | **not re-verified** | the live project was wiped by the MCP reset before I checked. The showcase is kitesurf, so the pack is correct there |
| F10 nRF52832 priced as antenna | **not re-verified** | same reason |
| F11 no "no change" in diffs | **fixed** | "Cost unchanged · certifications unchanged" |
| F12 concept-level label tooltip only | **fixed** | CAD code tab shows "AI-generated CAD (concept level) — geometry measured on the result" |
| F13 "8 factories" | **fixed** in the public docs, README and script. Residual: `docs/HONESTY_AUDIT.md:45` (internal) |
| F14 overview.md heart-rate example / 3.9-4.9 s | **fixed** |
| F15 MCP ≈100 s, duplicate RFQ | **fixed** | 2 prompts: 45.4 s + 33.2 s = **78.6 s**, 1 RFQ |
| F16 shared `web/.next` | **process, open** | not reproduced this time (the BUILD_ID was this run's) |
| F17 `.env` `APP_PASSWORD` set | **not fixed** | still set (no effect on the web; contradicts DEMO_DAY) |
| F18 overview $0.00 flash | **changed** | now a count-up animation (N8) |
| F19 "Awaiting approval" + "Auto-approved" | **not fixed** | both on stage 8 of `whoop_kitesurf` |
| F20 Dossier id wraps "a8_autof / ill" | **not fixed** | PDF assumption register |
| F21 repeated brand names | **not fixed** | Veylo (band, vacuum), Nuvora (vacuum, changing table) |
| F22 Connect-your-agent command | **fixed** | `claude mcp add --transport http physicallovablex-local <url>` |
| F23 native confirm() on restore | **fixed** | in-app dialog "Restore v3?", Cancel / Restore v3 (`F23_restore_confirm.png`) |
| F24 home CTA label varies | **fixed** | autofill moved under "More ways to start" |
| F25 Factory Pack hidden at 1280 | **fixed** | visible in the sidebar at 1280×800 |
| F26 card "(E…" truncation | **fixed** | cards show "$27.64/unit ●" |
| F27 BLE wearable firmware = Arduino | **not fixed** | "arduino … BLE GATT service" (docs say Zephyr for BLE) |
| F28 CAD edit leaves literals | **fixed** | diff is the single `pod_thickness` line |

## 3. Timed rehearsal (live key, one run)
| Step | Wall-clock | On screen | Auto Photo |
|---|---|---|---|
| Start (Whoop idea) | **21.6 s** (AI CAD at 42.1 s) | 44 × 30 × 10 mm Measured, $27.20 / $26.21 / $25.33, 14 BOM lines, 4 certs, Coralline 88 · Lumen Peak 86 · Harborlight 85 | 34.9 s, looks like the CAD, labeled |
| Add SpO2 and skin-temperature sensing | **4.9 s** | skin-temp LCSC C7472806 $4.10 (Sourced); PPG upgraded to MAX30102 (Estimate); **FDA row added**, wording "US FDA general-wellness vs medical-device boundary (SpO2 / body-temperature claims)"; $26.21 → **$31.00**; cert budget $11,000 → $13,500 | 18.8 s |
| Make it pink | **3.5 s** | colour chip, "Cost unchanged · certifications unchanged" | 20.5 s, pink |
| Thinner, 8 mm pod | **13.8 s** | **8.0 mm Measured**, 5.2 g, AI CAD program v2; code diff = 1 line | 26.1 s |
| Restore v2 → v4 | 0.01-0.03 s server + in-app dialog | — | — |
| Target retail $149 | **3.3 s** | price chip; **strip: Margin @2k 70.4 %, Break-even 174 units** | 17.8 s (not needed, spend) |
| **Total waiting** | **47.1 s** | | |
| Listing photos (··· → Listing photos → Generate) | **16.6 s**, 4 shots | packshot, lifestyle, in hand, detail. All look like the CAD. Labels on all; lifestyle and in-hand add "Staged scene — illustrative". Packshot has dark curved artifacts at the edges (N7) (`B8_listing_done.png`) | |
| Showcase: /examples → `whoop_kitesurf` → Open overview | 0.05 s → 0.44 s | 13/13, $28.82 / $27.64 / $26.54, margin 80.1 %, break-even 99; stage 8 "Auto-approved (autofill mode)" + "Change factory" | |
| Launch Dossier (`whoop_kitesurf`) | 0.28 s, 38 pages | EN + CN (1,145 CJK characters), a8_autofill, build strategy, firmware "not compiled or tested". **"Listing photos" page 30: one photo only** (lifestyle, labeled). N5 | |
| Launch Dossier (live project) | 3.5 s | "Listing photos" page with hero, packshot, lifestyle, in hand (+ detail) | |
Full per-prompt table: `docs/DEMO_SCRIPT.md` → "Observed diffs (W23b…)".

## 4. MCP (2 prompts, Claude Code 2.1.238, local `http://localhost:8000/mcp`, after `POST /demo/reset`) — PASS
- **Prompt 1 (45.4 s):** search_capacity × 2 (LSR, PCBA), get_factory_profile × 2, request_quote to **Coralline for 500 / 2,000 / 10,000** → `rfq_d3982dd7ad`, which is listed on Coralline's RFQs.
- **Prompt 2 (33.2 s):** register_capacity → **Tidewater Wearables (fictional)** `f_fdb701b839`. Claude re-ran the search itself: Tidewater ranks #1 at 96/100. The portal lists it (16 partners) and its page returns 200.
- **Total 78.6 s**, one RFQ. Anthropic cost ≈ $1.51 (Claude Code account, not OpenRouter). Claude Desktop itself not tested.

## 5. Gallery — PASS with the solar issues
All 11 showcases:
- Studio and Overview fit the viewport at 1440×900.
- **0 console errors and 0 HTTP ≥ 400** in the sweep.
- Every Studio has a Photo view labeled "Photo-styled from the CAD (AI image, geometry from our CAD)".
- The gallery hover switches to the lifestyle shot, labeled "AI photo · staged scene, illustrative" (`C0_examples_hover.png`).

| Showcase | Unit @ 2k | Retail | Margin @ 2k | Break-even |
|---|---|---|---|---|
| whoop_kitesurf | $27.64 | $199 | 80.1 % | 99 units |
| surfboard_beginner | $224.55 | $549 | 35.1 % | 45 |
| stick_vacuum | $98.09 | $249 | 39.0 % | 153 |
| drone_follow | $190.54 | $999 | 73.8 % | 26 |
| solar_biarritz (per installation, pilot of 10) | installer cost $9,597.86 | $17,343.50 installed | 44.7 % | **3 installations** (stage 5 only) |
| changing_table | $122.53 | $289 | 11.1 % | 314 |
| irrigation_biarritz | $44.11 | $139.32 | 53.5 % | 163 |
| minimal_phone | $183.90 | $549 | 54.5 % | 152 |
| hair_dryer | $42.93 | $129 | 52.2 % | 113 |
| instant_camera | $65.74 | $199 | 53.3 % | 119 |
| home_robot | $234.74 | $699 | 44.4 % | 74 |

All plausible now; whoop at 80 % is high but labeled Estimate.

Solar ("Cost per installation", "Installer shortlist" with 3 fictional installers): the Studio strip and the Overview say **$11,471 "Turnkey, one installation"** (the PV-only figure). The current version v2 adds a battery: its own diff says "Installed price per roof $11,471 → $17,343.50", and the gallery card shows $17,344. On top of that, the v2 diff lists "Stationary solar battery pack … **$0.30/unit**" and "Battery inverter … $0.30/unit", although stage 5 prices them at $3,400 and $950. Break-even in installations (3) is in stage 5 only; the Overview shows payback 8.6 years instead.

## 6. Design sanity — PASS (one intermittent issue)
- Home, Studio, Overview, stage 8, portal and the solar Studio at **1440×900 and 1280×800**: no page scroll and no ellipsis/clamp truncation of visible text.
- Mobile 390 px: app routes show the "Desktop only" gate; `/docs` pages are readable with no horizontal scroll.
- **Login mode:**
  - Public: `/docs`, the 7 pages, `/agents.md` and `/llms.txt` return 200.
  - Gated: app routes redirect 307 to `/login?next=…`; `/backend/*` returns 401; API `/examples` without the key returns 401.
  - `/mcp` returns 401 without a token and 200 with a Bearer token.
  - A wrong password goes to `?error=1`. With a session cookie, the Studio, the PDF export and the photo files return 200.
- **Console errors: 1 in the whole run.** `GET /backend/projects/demo_whoop_kitesurf/stages/5` → 500 (web log: "Failed to proxy … read ECONNRESET").
  - The Overview then showed a red "Could not load a step: HTTP 500 · Retry" banner. The cost block was replaced by "Unit cost appears once step 5 has run" and an orange **"Autofill all 13 steps with AI"** button (`D6_1440_projects_demo_whoop_kitesurf_wow.png`).
  - 1 hit in ≈ 35 Overview loads; not reproduced in 12 loads with 5 s idle gaps. It looks like the Node proxy reusing a keep-alive socket that uvicorn closed.
  - On stage: click **Retry**, never Autofill.

## 7. Budget safety (API restarted with `OPENROUTER_API_KEY=` empty) — PASS
- Showcases open, and their photos and PDF export work.
- New Whoop start: v1 in 1.4 s with the **Cached example banner in the Studio** (F6 fixed).
- A refine fails calmly: "The AI is not configured on this server… Nothing changed — version 1 is still current." A "Put this prompt back in the box" link is offered.
- The Photo toggle is disabled on the new project.
- In Listing photos, "Generate listing photos" is disabled with the note "No image model is configured here, so new photos can't be made. The photos below were recorded with the example." The showcase has 3 of 4 tiles "Not generated yet" (N5).

## Bugs (open)
| id | severity | where | repro | expected | actual | owner | screenshot |
|---|---|---|---|---|---|---|---|
| N1 | major | `solar_biarritz` Studio strip, Overview, gallery card | open the showcase | one per-installation figure for the current version (with battery) | strip/Overview "$11,471 Turnkey, one installation" (PV only); v2 diff "$11,471 → $17,343.50"; gallery card $17,344; stage 5 installer cost $9,597.86 | W21 backend (+W26 web for the strip) | `C_solar_biarritz_studio_photo.png`, `C_solar_biarritz_overview.png` |
| N2 | major | `solar_biarritz` Studio v2 card | open the Studio | battery lines priced as in stage 5 | "Stationary solar battery pack… $0.30/unit", "Battery inverter/charger… $0.30/unit" (recorded diff text; stage 5 has $3,400 / $950) | W21 backend (fixture) | `C_solar_biarritz_studio_photo.png` |
| N3 | major (intermittent) | Overview of a 13/13 project | ≈ 1 in 35 loads, a proxy ECONNRESET on `/stages/5` | silent retry; never offer Autofill on a validated project | red "HTTP 500" banner, "Unit cost appears once step 5 has run", orange "Autofill all 13 steps with AI" (a live run if clicked) | W26 web (retry + hide Autofill when 13/13) / W9 (uvicorn `--timeout-keep-alive` > Node idle) | `D6_1440_projects_demo_whoop_kitesurf_wow.png` |
| N4 | minor | Live spend | full rehearsal | ≈ $0.31 as before | **$0.92**: a hero photo is auto-generated for every version, including price-only ("Target retail $149"); the v1 photo is captured at 35 s from the pre-AI geometry (AI CAD lands at 42 s) | W21 backend (skip the photo when the look is unchanged) / W18 docs (DEMO_DAY budget) | — |
| N5 | minor | Showcase listing kit | `whoop_kitesurf` → ··· → Listing photos; Dossier p. 30 | 4 recorded shots | 1 of 4 (lifestyle); 3 "Not generated yet" tiles; Dossier "Listing photos" page has one photo | W21 backend (fixtures) | `G_nokey_listing.png`, `pdf_listing-30.png` |
| N6 | minor | Solar Overview / Studio strip | open solar | "break-even in installations" visible | only in stage 5 ("3 installations"); Overview shows payback | W26 web | `C_solar_biarritz_overview.png` |
| F9 / F10 | minor | live Whoop engineering / BOM | Whoop prompt | — | not re-verified (the project was wiped by the reset) | W21 | — |
| F17 | minor | `.env` | inspect | `APP_PASSWORD` empty (DEMO_DAY) | set | W9 / Orphéo | — |
| F16 | minor (process) | shared `web/.next` | another session builds for another port | — | not reproduced this time; keep `SKIP_BUILD=0` on demo day | W9 | — |
| N7 | polish | Listing packshot | Generate listing photos | clean white packshot | dark curved artifacts at the left and right edges | W21 (photo prompt) | `B8_listing_done.png` |
| N8 | polish | Overview | open the Overview | final numbers | count-up passes through intermediate values ($27.37 / $24.56 / $20.01) for ≈ 0.5 s | W26 web | `B10_showcase_overview_300ms.png` |
| N9 | polish | 3D viewers | pink `whoop_kitesurf` | same colours | strap white in the Studio viewer, pink in the Overview viewer | W26 web | `B9_showcase_studio.png`, `B10_showcase_overview.png` |
| N10 | polish | Fallback title | no key → Whoop prompt | short name | two-line title-cased prompt "A Whoop Competitor: a Screenless Wrist-worn Band, 5-day Battery, Tracks Sleep and Strain" | W26 / W21 | `G_nokey_refine.png` |
| N11 | polish | `home_robot` BOM | stage 5 | module priced as a module | "DC-DC buck converter module" $0.0512 Sourced (bare-IC match) | W21 | `F_sourced_bom_lines.txt` |
| N12 | polish | Gallery card | `/examples` | whole product | stick vacuum photo shows only the pole | W21 (photo framing) | `C0_examples_hover.png` |
| F19 | polish | Stage 8 | `whoop_kitesurf` stage 8 | one approval state | "Awaiting approval" + "Auto-approved (autofill mode)" | W21 | — |
| F20 | polish | Dossier assumption register | PDF | full id | "a8_autof / ill" | W21 | `whoop.txt` |
| F21 | polish | Stage 13 names | compare showcases | unique | Veylo ×2, Nuvora ×2 | W21 | — |
| F27 | polish | Firmware | `whoop_kitesurf` Firmware tab | Zephyr for BLE (docs) | Arduino | W21 | — |
| F13b | polish | `docs/HONESTY_AUDIT.md:45` | read | 11 factories | "The 8 factories" | W18 docs | — |

Counts (open): **blocker 0 · major 3 · minor 6 · polish 11** (F9/F10 counted as one row; F16 is process).

## Live spend
OpenRouter `usage`: before **$13.4005** → after **$14.3205** = **$0.920** (budget $1.00).
- At the 13:28 read, after the start, 4 refines, 5 auto photos and the 4-shot listing kit: $0.647.
- The remaining $0.27 posted later: the key endpoint lags, plus one live-project Dossier export (3.5 s).
- Everything after that ran with the key removed.
- Claude Code MCP prompts: ≈ $1.51 on the Anthropic account.

## Before pass-5 / demo day
1. W21: N1 + N2 (solar showcase figures), or keep solar out of the demo. The script only offers it "if time allows".
2. W26 / W9: N3. Retry `/stages/*` once on a proxy error, and never show "Autofill" on a 13/13 project. Presenter: if the red banner appears, click Retry.
3. W21: N4. No new photo when the look is unchanged. Budget ≈ $1 per rehearsal until then; check the credit.
4. W21: N5. Record the 4-shot kit for `whoop_kitesurf`, since the Dossier page is shown on stage.

---

# 3D wave regression (W23c, 27 Sept 2026, 19:43-20:25 — after W28 web + W29 backend)

**Verdict: ready.** No blocker. Every item of the core demo path passed:
- The live Whoop idea, "Add SpO2 and skin-temperature sensing", and "Make it pink" with its auto photo.
- The `whoop_kitesurf` showcase, "Open overview" and the Launch Dossier, now with 4 listing photos.
- The Connect-your-agent panel.

The new 3D stage works on all 11 showcases: presets, hover tooltip, part card, part edits, Exploded, X-ray, Anatomy, and the `?viewer=basic` fallback.

Four major issues are open, none of them on the scripted path:
- After a part edit, the Photo view shows the **previous look's photo**.
- The vacuum anatomy caption says the battery lasts **"4 min"**.
- Proxy ECONNRESET 500s are more frequent.
- **Live spend went over budget: $0.568 against $0.30.**

Rig: ports 8000/3000 were free. `cd web && npm run sync-docs`, then `SKIP_BUILD=0 scripts/demo_start.sh` printed **READY**. The no-key + login run (`OPENROUTER_API_KEY=` empty, `APP_PASSWORD`, `API_SHARED_KEY`, `SKIP_BUILD=1`) also printed READY. Evidence: `tests/results/final3/`. No code was changed. At the end I ran `/demo/reset` and stopped everything.

## 1. Automated — PASS
`uv run pytest` **584 passed, 31 skipped** (342 s) · `npx tsc --noEmit` exit 0 · `npm run lint` exit 0 · build inside demo_start OK.
API log at startup: `ERROR:discovery:plug-in api.cad.partnames_curated register() failed: register() missing 1 required positional argument: 'rules'` (P1).

## 2. 3D stage on 11 showcases + 2 demos — PASS with notes
- **Showcases (11/11):** Studio and Overview each render one WebGL canvas.
  - rAF ≈ 60-61 fps. This is headless Chromium, so it is a smoke test, not a GPU benchmark.
  - Controls present: ¾ / Front / Side / Top / Reset / Exploded / X-ray / Anatomy, plus the Photo/3D toggle.
  - No page scroll. **Console errors: none from the 3D stage.** The only warning is `THREE.Clock … deprecated`.
- **Hover** shows the part name ("Top shell").
- **Click** opens "Edit this part":
  - Size (Measured), look, unit price (Estimate), BOM line link.
  - 8 colour swatches plus a custom one, Material and Finish selects, 2 parameter sliders, Apply.
- **Demos (desk lamp, tracker card):**
  - The Overview "3D model" toggle loads the new stage. Clicking a part opens a **view-only** card (size, look, "Edit this part in the Studio →"). ✔
  - But `/projects/demo_desk_lamp/studio` shows an endless "Building the first version: CAD, BOM, costs, factories" spinner and a **"Start the Studio"** button, which would start a live run. The card's "Edit this part in the Studio →" link leads there (M4).

## 3. Edit this part on `whoop_kitesurf` (v4 → v7, reset afterwards) — PASS with 2 issues
| Edit | New version | Wall-clock | Diff on the card | Cost | Measured |
|---|---|---|---|---|---|
| Colour: Sage swatch | v5 | 1.6 s | "Top shell colour → Sage (#9DB09A)"; "Cost unchanged · certifications unchanged" | unchanged $27.64 | 44 × 30 × 8 |
| Material: Aluminium 6063-T5 | v6 | 1.6 s | "Top shell material PC/ABS → Aluminium 6063-T5 (+$12.34/unit, Estimate)", enclosure weight 5.2 → 12.2 g, tooling $3,730 → $1,490 | **$27.64 → $39.98** | — |
| Pod thickness slider 8 → 10 mm + Apply | v7 | 3.8 s | "Pod thickness 8.0 → 10.0 mm (Measured)", "Top shell size 44.0 × 3.8 × 30.0 → 44.0 × 5.8 × 30.0 mm" (Measured), weight 13.2 g | $39.98 → $40.05 | **44 × 30 × 10** |

- CAD code diff v2 → v3: the single line `"pod_thickness": 8.0 → 10.0` (`B_cad_code_v2_v3.diff`).
- Photos: `look_changed: true` on v5-v7, but no photo job ran (showcase, `job: idle`). The **Photo view on v5 (Sage) still shows the pink v4 photo**, captioned "Photo-styled from the CAD…" (M1, `B_photo_after_colour.png`).
- The colour edit also **re-ranked the factory shortlist**, while the card says only "Cost unchanged · certifications unchanged" (m2):
  - before: Lumen Peak 86 · Harborlight 85 · Cobalt River 76
  - after: Coralline 88 · Lumen Peak 86 · Harborlight 85
- The thickness edit lists the pod thickness change twice (p2).

## 4. Exploded + X-ray (whoop, drone, vacuum) — PASS, labels overlap
- Exploded separates parts along their layers; X-ray makes the shells translucent. Labels are part names (Battery pack, Propeller 1, Wi-Fi vision compute module, Main PCB, MAX30102 …).
- **Label overlap, minor:**
  - drone: "Landing legs" covers "Gimbal camera".
  - vacuum: 3 labels crowd the top ("Battery lead +", "High-speed BLDC vacuum motor assembly", "Battery pack").
- whoop Exploded: the top shell and battery leave the frame at the top.
- Stray thin red/black "cable" lines on the drone read as artefacts.
- Screenshots: `C_*_exploded.png`, `C_*_xray.png`.

## 5. Anatomy (whoop, drone, vacuum, surfboard, phone) — PASS
- All 5 open in ≤ 0.17 s. Steps: 6 / 6 / 6 / 7 / 7.
- Navigation works four ways, each checked on all 5: **Next button, ArrowRight, mouse wheel, ArrowLeft** back.
- **Esc exits**, and `window.scrollY` stays 0 throughout: the page never scrolls.
- "Illustrative internal layout — not a routed PCB" is visible on every step.
- The scale ruler shows "Field of view ≈ 18 cm / 62 cm / 2.4 m / 4.6 m / 28 cm".
- Captions are labeled, e.g. "MAX30102 Optical heart-rate sensor (LCSC C6454833, OESIP-14, $12.18 (Sourced)) + QMI8658A 6-axis IMU ($1.01 (Estimate))" and "Smartphone ODM mainboard assembly ($78.20 (Estimate))". The surfboard shows construction layers (deck laminate, foam core + stringer, bottom laminate, fins).
- **Wrong numbers surfaced by the vacuum captions (M2):**
  - "6 × 18650 Li-ion, 21.6 V, 56 Wh — battery life **4 min** (Estimate)". It comes from engineering `battery_life` **fail 0.07 h** = 2,600 mAh × 85 % / **31,750 mA**; 180 W on a 21.6 V pack is ≈ 8.3 A, so ≈ 16 min.
  - "Back together … weight **280.6 g**" (enclosure only; a stick vacuum weighs ≈ 2.5 kg).
- **Framing, polish:**
  - whoop step 4 camera is inside the shell (huge shapes, small sensor).
  - vacuum step 4 is very tight, with the "18650 cells" label cut at the top.
  - The FOV pill covers the "10 cm" ruler tick.

## 6. `?viewer=basic` — PASS
Studio and Overview (whoop, drone) fall back to `<model-viewer>`: no WebGL stage controls, the model renders, no scroll, no errors.

## 7. Core demo path (live key, one run) — PASS
| Step | Wall-clock | Result |
|---|---|---|
| Whoop idea → v1 | **23.7 s** (AI CAD 44.3 s, Photo 38.2 s) | "Screenless Recovery Band", 44 × 30 × 10 mm, $27.10 / $26.06 / $25.09, 4 certs |
| Add SpO2 and skin-temperature sensing | **5.2 s** | skin-temp LCSC C7472806 $4.10 (Sourced) + FDA row + cert budget $10,400 → $12,900; $26.06 → **$30.85**; no new photo (look unchanged) ✔ |
| Make it pink | **4.2 s**, auto Photo at **17.3 s** | pink photo matches the CAD, labeled (`F_pink_photo_s.png`) |
| `/examples` → `whoop_kitesurf` → **Open overview** | 0.05 s → 0.06 s | header shows only "Open overview"; $28.82 / $27.64 / $26.54, $91,397, $199 |
| Launch Dossier | 0.35 s, 38 pages | "Listing photos" page with **4 shots** (packshot, lifestyle, in hand, detail), labeled (N5 fixed) |
| MCP panel `/factories` | — | "Connect your agent · `claude mcp add --transport http physicallovablex-local http://localhost:8000/mcp` · Local API: no token needed" ✔ |

## 8. Layout, mobile, login, docs — PASS
- **1440×900 and 1280×800** (home, examples, whoop Studio + Overview + stage 8, portal, live Studio, Anatomy): no page scroll and no ellipsis truncation.
- Mobile 390 px: the gate is shown on app routes; docs are readable (scrollWidth 390).
- Login mode:
  - Public: the docs pages, `/agents.md` and `/llms.txt` return 200.
  - Gated: app routes redirect 307 to `/login?next=…`; `/backend/…/parts` and `/anatomy` return 401 without a session; API `/parts` and the anatomy GLB return 401 without the key.
  - After login the 3D stage and Anatomy work.

## 9. Budget safety (no key) — PASS
- Showcase 3D, Anatomy and the part card work.
- "Generate listing photos" is disabled with the note "No image model is configured here, so new photos can't be made. The photos below were recorded with the example."
- Refine: "The AI is not configured on this server… Nothing changed — version 4 is still current."

## Proxy resets (carry-over N3, now more frequent)
- 6 `Failed to proxy … read ECONNRESET` this session: `/stages/1` on the whoop and drone Overviews, and `/openapi.json`. Three came in one 13-project sweep.
- When it hits the Overview, it shows "Could not load a step" (see W23b N3). On stage: click **Retry**.

## Bugs (open)
| id | severity | where | repro | expected | actual | owner | screenshot |
|---|---|---|---|---|---|---|---|
| M1 | major | Studio Photo view after a part edit (showcase) | whoop → click pod → Sage → Photo | a photo of the new look, or "no photo for this version yet" with 3D shown | the pink v4 photo, captioned "Photo-styled from the CAD", under a Sage v5 (no photo job ran although `look_changed: true`) | W28 web (fallback) + W29 backend (photo job for part edits) | `B_photo_after_colour.png` |
| M2 | major | Vacuum engineering + Anatomy captions | `demo_stick_vacuum` → Anatomy step 4 / step 6 | ≈ 16 min at 180 W on a 21.6 V pack; whole-product weight | "battery life 4 min" (`battery_life` fail 0.07 h, 31.75 A average: single-cell voltage used); "weight 280.6 g" (enclosure only) | W29 backend | `D_stick_vacuum_step4.png` |
| M3 | major (intermittent) | Proxy `/backend/*` | browse ≈ 25 pages | no 500 | 6 ECONNRESET 500s this session (3 in one sweep) → "Could not load a step" on the Overview | W28 web (silent retry) / W9 (keep-alive) | — |
| M4 | major (budget) | Live spend | idea + SpO2 + pink | ≤ $0.30 | **$0.568** for this QA. The core path (AI CAD, review, firmware LLM, 2 photos) posts cost with a delay. One rehearsal of the 3-prompt path is not under $0.30 | W29 backend / W18 docs (DEMO_DAY budget) | — |
| m1 | minor | Demo projects' Studio | `/projects/demo_desk_lamp/studio`; Overview part card → "Edit this part in the Studio →" | view-only, or a clear "example without Studio versions" | endless "Building the first version…" spinner + "Start the Studio" (live run) | W28 web | `A_desk_lamp_studio.png`, `A_desk_lamp_overview_partclick.png` |
| m2 | minor | Part edit (colour) | whoop → Sage | shortlist unchanged, or shown in the diff | shortlist re-ranked silently (Lumen/Harborlight/Cobalt → Coralline/Lumen/Harborlight) | W29 backend | `B_edit_colour.png` |
| m3 | minor | Exploded labels | drone, vacuum Exploded | no overlap | "Landing legs" over "Gimbal camera"; 3 labels stacked on the vacuum head | W28 web | `C_drone_follow_exploded.png`, `C_stick_vacuum_exploded.png` |
| m4 | minor | Exploded framing | whoop Exploded | whole stack in frame | top shell and battery cut at the top | W28 web | `C_whoop_kitesurf_exploded.png` |
| m5 | minor | Material edit | whoop → Aluminium | tooling change explained | tooling $3,730 → $1,490 with no note (CNC vs mould?) | W29 backend | `B_edit_material.png` |
| P1 | polish | API startup | `demo_start.sh` | clean log | `ERROR:discovery:plug-in api.cad.partnames_curated register() failed` | W29 backend | api.log |
| p2 | polish | Thickness edit diff | slider 8 → 10 | one line | "Pod thickness 8.0 → 10.0 mm (Measured)" and "Pod thickness 8.0 mm → 10.0 mm" | W29 backend | `B_edit_thickness.png` |
| p3 | polish | Anatomy cameras | whoop step 4, vacuum step 4 | part framed | camera inside the shell / too tight, label cut | W29 backend (camera) / W28 | `D_whoop_kitesurf_step4.png` |
| p4 | polish | Scale ruler | any anatomy step | ticks readable | FOV pill covers "10 cm" | W28 web | `A_hover_pod.png` |
| p5 | polish | Part card | click the pod | sliders and Apply visible | inner scroll needed; sliders have no aria-label | W28 web | `A_partcard_pod2.png` |
| p6 | polish | "Anatomy" button | any Studio | inactive look when off | always filled black (reads as active) | W28 web | `A_whoop_studio.png` |
| p7 | polish | Drone Exploded | drone | clean | thin red/black line segments across the view | W28 / W29 | `C_drone_follow_exploded.png` |
| p8 | polish | Console | any 3D page | no warning | `THREE.Clock … deprecated, use THREE.Timer` | W28 web | — |
| p9 | polish | Desk lamp part names | Overview part card | descriptive | "Metal part" | W29 backend | `A_desk_lamp_overview_partclick.png` |

Counts: **blocker 0 · major 4 · minor 5 · polish 9.**

## Live spend
OpenRouter `usage`: before **$14.7286** → after **$15.2964** = **$0.568**. Budget was $0.30: **over by $0.27**.
- Read at 20:00, right after "Make it pink": $0.228. The remaining $0.34 posted later.
- No other live AI action ran after that: showcase pages, Dossier export and reads only. I then removed the key.
- My mistake: I did not wait for the delayed billing before judging the budget. W23b already showed the lag.
