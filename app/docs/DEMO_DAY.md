# Demo day — local restitution (Orphéo)

Why local and not `next dev`: a cold `next dev` compiles the first `/wow` in ~31 s. The script below runs the **production** build and pre-warms every route, so the first click on stage is instant (measured on a test run: all 81 warm-up requests OK, each ≤ 0.2 s after warm-up, PDF export 0.17 s).

## Start (one command)
```bash
cd ~/Desktop/Hexa_Case/04_LIVRABLE/mvp
scripts/demo_start.sh
```
What it does, in order: checks ports 8000/3000 are free → starts the API on **:8000** (default `api/data/app.db`) → `POST /demo/reset` (the two demo projects + the 15 fictional partners — 11 factories, 1 integrator, 3 installers — and the 11 showcases) → prints whether the live AI key is configured and the OpenRouter remaining credit → `npm run build` and `npm start` on **:3000** (production mode) → warms `/`, `/about`, `/new`, `/projects`, `/factories` + every factory page, and for **both** demo projects `/wow`, the 13 stages (page + API through the proxy), the Factory Pack, the PDF export and the 3D files → prints **READY** and the URLs. **Ctrl-C** stops API and web. Logs: `$TMPDIR/plx-demo/` (`api.log`, `web.log`, `web-build.log`).

Open: `http://localhost:3000/?mode=idea` (desk lamp: `/projects/demo_desk_lamp/wow`, tracker card: `/projects/demo_tracker_card/wow`).
If the script prints `FAIL` lines or does not print READY: read the log it names, fix, re-run. Do not start the demo on a non-READY.

Options (env): `SKIP_BUILD=1` reuse the last build (fast restart, same ports only) · `CHECK_CREDITS=0` skip the OpenRouter call · `API_PORT` / `WEB_PORT` (+ `DB_PATH`, `FILES_DIR`, `FACTORY_MCP_DB` for an isolated DB) · `API_SHARED_KEY` / `APP_PASSWORD` only if you want to rehearse the deployed auth locally (leave unset otherwise).

## Checklist

**The day before (with internet)**
1. `git status` clean on the demo commit; `uv sync` and `cd web && npm install` done.
2. `.env` has `OPENROUTER_API_KEY` and the 4 `LLM_*_MODEL` values; **`API_SHARED_KEY` and `APP_PASSWORD` empty** for local demo.
3. Run `scripts/demo_start.sh` once, end to end, online. **This build must happen online**: the web fonts are downloaded from Google Fonts *at build time* (they are served from the build afterwards). Leave the resulting `web/.next/` in place — it is your offline backup.
4. Live test with the key: New project → the desk-lamp prompt → the wow screen turns green in ≈ 1 min, no "Cached example" banner. Check `/health` → `llm_configured: true`.
5. Put the credit in order: the script prints `remaining`; a full live run costs little but a run that hits 402 falls back to the cached example. Top up on openrouter.ai if remaining is low.
6. Export the PDF of the desk lamp once and open it (the file you can show if the screen fails).

**One hour before**
1. Plug the laptop in, disable sleep/screensaver, close other apps, quit anything on ports 8000/3000.
2. `scripts/demo_start.sh` → wait for **READY** (≈ 1 min with a build, ≈ 20 s with `SKIP_BUILD=1` if the build is fresh).
3. Click through once: home → desk-lamp wow → stage 5 → stage 8 → Factory Pack → Export PDF → `/factories` → tracker card wow.
4. Full screen, browser zoom 100 %, one tab, notifications off. Keep `localhost:8000/health` in a second tab.

**During the demo**
- Start from the cached desk lamp (instant). Run a live prompt only if the network and credits are confirmed; it takes ≈ 1 min, talk over it.
- Label vocabulary to say out loud: Measured (computed on the CAD) · Sourced (real price/rate + date) · Estimate · Fictional — demo data (the factories are invented).
- A "Cached example" banner on a live run means the AI call failed and the cached example is shown: say so, do not pretend.

## Backup plan if the network fails
- **What still works with no internet:** everything on the two cached examples — 13 stages, the 3D models, the renders and hero shots (prebuilt files on disk in `api/cad/prebuilt/`), Factory Pack, PDF export, factory portal, the CAD build of a new project (build123d runs locally, stages 2–3 without a key). The API, web and data are all local; nothing loads from a CDN at runtime.
- **What does not work offline:** live AI (new idea → stages 1, 4 review, 8 negotiation, 13; concept renders) — the stage then serves the cached example with a visible banner; `npm run build` (fonts) — that is why you build the day before and use `SKIP_BUILD=1` (`scripts/demo_start.sh` reuses the build; it must have been built for the same API port, 8000).
- **If the web will not start:** `cd web && npm run dev` (slower first page, ~30 s) — or open the API-only proofs: `http://localhost:8000/docs`, the PDF export.
- **If the API will not start:** read `$TMPDIR/plx-demo/api.log`; most likely port 8000 busy (`lsof -nP -iTCP:8000 -sTCP:LISTEN`) or `.env` typo.
- **If everything fails on stage:** the deployed link (`docs/DEPLOY.md`, if you deployed) and the exported PDFs/screenshots (`docs/screens/after/`).
- **Reset the data at any time:** `curl -X POST localhost:8000/demo/reset`.
- **Stop all spend instantly:** unset `OPENROUTER_API_KEY` in `.env` and restart — every stage serves the cached example.
