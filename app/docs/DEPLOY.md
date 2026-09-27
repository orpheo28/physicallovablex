# Deploy — Sunday evening checklist (Orphéo)

Agents never deploy. You do it, in the browser, ~40 min. Everything marked **(verify)** is a price or limit to re-check on the vendor page.

```
Framer ──"Get Started"──▶ Vercel (app/web, Next.js) ──/backend/* proxy, adds X-App-Key server-side──▶ Railway (app/, Docker: API + CAD, volume /data)
                                                                                                        └─▶ OpenRouter (key stays on Railway)
```
Why two hosts: build123d / OCCT is far too heavy for a Vercel function.
Tested locally with Docker: `/health` OK, demo projects seeded on an empty DB, cached PDF export 0.2 s, stage 2 + 3 CAD build 2.5 s + 0.4 s **without any key**, peak memory **≈ 365 MiB** (Railway trial limit: 1 GB RAM). Image (multi-stage): **2.0 GB on disk, ≈ 470 MB compressed** (was 3.3 GB); Railway's docs state no image-size limit for the trial **(verify)**.

Two different secrets — do not mix them up:
| Name | Where | What it does |
|---|---|---|
| `API_SHARED_KEY` | Railway **and** Vercel (same value, random 32+ chars) | the API refuses every request without header `X-App-Key: <value>` (except `GET /health`). The Vercel proxy adds it; browsers never see it. Empty = API open (local dev) |
| `APP_PASSWORD` | Vercel only (server-only) | the password a visitor types on the web app's password screen (cookie 7 days). Never reaches the API |
| `MCP_TOKEN` | Railway only (+ the MCP client: Claude / ChatGPT connector) | Bearer token of the production MCP at `/mcp`. **Separate from `API_SHARED_KEY`**: `/mcp` is exempt from the X-App-Key gate and checks `Authorization: Bearer <MCP_TOKEN>` itself (falls back to `API_SHARED_KEY` only if `MCP_TOKEN` is empty) |

Generate each key separately: `openssl rand -hex 24` (one for `API_SHARED_KEY`, another for `MCP_TOKEN`).

---

## 1. Accounts (done: GitHub)
1. Vercel: vercel.com → **Sign up → Continue with GitHub** → plan **Hobby**. (free)
2. Railway: railway.com → **Login with GitHub** → **Trial** plan. One-time $5 credit valid 30 days, ≤ 1 GB RAM, shared vCPU **(verify)** ([trial limits](https://docs.railway.com/reference/pricing/free-trial)); trial volumes are deleted 30 days after credits expire — fine for a demo. The volume is small (≈ 0.5 GB **(verify)**): the API keeps only the 30 most recent generated-CAD folders (`MAX_STORED_PROJECTS=30`, ~5-10 MB each).

## 2. Export the repo and push (you)
The public/jury repo is a clean export, not `physicallovablex-mvp`.
```bash
cd ~/Desktop/Hexa_Case/04_LIVRABLE
./export_repo.sh                       # → ~/physicallovablex-export (app/ gtm-harness/ gtm/ docs/ README.md) + 1 local commit
```
It aborts (nothing committed) if it finds a discovery contact email, a key-like string, a forbidden path or a file > 50 MB.
Files under `gtm-harness/` and `gtm/` that contain an email address (prospect contacts) are left out automatically and listed in the summary ("excluded: contains email"); the rest is kept.
Then push:
```bash
cd ~/physicallovablex-export
gh repo create physicallovablex --private --source=. --push
```
Check on github.com/orpheo28/physicallovablex that there is no `.env` and that `app/Dockerfile` and `app/web/` exist.

## 3. Railway — the API
1. Railway → **New Project** → **Deploy from GitHub repo** → first time **Configure GitHub App** → allow only `physicallovablex` → pick it.
2. Click the new service → **Settings**:
   - **Source → Root Directory: `app`** (the repo root has no Dockerfile; the API lives in `app/`).
   - **Build**: builder should say *Dockerfile* (auto-detected: `app/Dockerfile`). If it says Nixpacks/Railpack, choose Dockerfile.
   - **Deploy → Healthcheck Path: `/health`** (also set in `app/railway.toml`, but Railway may not read the file from a sub-folder, so set it here too).
   - **Networking → Generate Domain** → copy `https://<api>.up.railway.app` = **API URL**.
3. **Volume**: on the project canvas `Ctrl/Cmd+K` → *Create Volume* (or right-click the service → **Attach Volume**) → mount path **`/data`**. Without it, every redeploy wipes projects (demo projects are re-seeded on an empty DB anyway).
4. Service → **Variables** → **Raw Editor** → paste, fill, **Update Variables**:
```
OPENROUTER_API_KEY=<your key>
LLM_MAIN_MODEL=<slug>
LLM_FAST_MODEL=<slug>
LLM_CN_MODEL=<slug>
LLM_IMAGE_MODEL=google/gemini-3.1-flash-image     # stage-2 concept renders + Studio photos; empty = no renders/photos
LLM_IMAGE_MAX_RENDERS=1         # stage-2 auto-renders only the first N directions (images are the priciest call)
LLM_MAX_REQUESTS=300            # global cap per API process (resets on restart): the hard cost ceiling
LLM_MAX_TOKENS=8000
LLM_TIMEOUT_S=60
RATE_LIMIT_PER_DAY=20           # live runs per visitor IP per 24 h → 429 after
MAX_STORED_PROJECTS=30
DB_PATH=/data/app.db
FILES_DIR=/data/files
FACTORY_MCP_DB=/data/network.db
API_SHARED_KEY=<the openssl value>
MCP_TOKEN=<a second openssl rand -hex 24>     # Bearer token for POST /mcp (the production MCP endpoint); falls back to API_SHARED_KEY if unset — set its own so you can hand it to an MCP client without also handing out the web/API key
CORS_ORIGINS=https://placeholder.invalid     # replaced in step 5.4 by the Vercel origin
```
   The three `/data` paths are also the image defaults (listed so a wrong volume mount is obvious); `SEED_DEMO_ON_EMPTY=1` is baked in. Do not set `PORT`.
5. Wait for the deploy (first build ≈ 10 min). Check: `https://<api>/health` → `"status":"ok"`, `"llm_configured":true`. Then
   `curl -s -o /dev/null -w "%{http_code}\n" https://<api>/projects` → **401**, and with `-H "X-App-Key: <API_SHARED_KEY>"` → **200** (two demo projects).

**W21 additions (Studio + AI CAD + engineering):**
```
CODEGEN_ENABLED=1               # 0 = no AI-written CAD: parametric families only (labelled "Parametric family CAD"), no codegen LLM calls
CODEGEN_MEM_MB=1280             # address-space cap of the CAD sandbox child (OCP needs ~1.1 GB of address space; 900 segfaults)
CODEGEN_DATA_MB=640             # data-segment cap of the sandbox child: what stops a runaway model from OOM-ing the 1 GB container
STUDIO_RATE_LIMIT_PER_DAY=100   # Studio prompts per visitor IP per 24 h (start, refine, restore, engineering recompute); 0 = off
PHOTO_RATE_LIMIT_PER_DAY=30     # Studio photo (image-model) jobs per visitor IP per 24 h, own bucket, only counted with a live key; 0 = off
```
`CODEGEN_*`, `STUDIO_RATE_LIMIT_PER_DAY` and `PHOTO_RATE_LIMIT_PER_DAY` have safe defaults: nothing to set on Railway unless you want to change them. All five are baked into the image with these defaults (plus `MALLOC_ARENA_MAX=2`, `OPENBLAS_NUM_THREADS=1`); set them on Railway only to change them.
Memory check (W21, `docker run --memory=1g`, one Studio start with AI CAD running in the API process + its sandbox child, three product families in a row, fake LLM endpoint): **container peak 810 MB** (cgroup `memory.peak`, incl. page cache), anonymous memory peak 678 MB, API peak RSS 649 MB, sandbox child ≈ 450 MB RSS of which most is shared OCP libraries; `oom_kill 0`. Idle API: 496 MB RSS.
Showcase gallery: after `POST /demo/reset` (or a fresh volume with `SEED_DEMO_ON_EMPTY=1`), `GET /examples` lists the recorded showcases (`demo_<slug>`); opening them costs nothing (every stage, version, AI CAD program and engineering result is cached in the image).

**Zero-cost public mode:** add `DEMO_READONLY=1` (live AI runs → 403 "Read-only demo"; cached demos, factory portal, PDF and 3D keep working; key not needed).

## 4. Vercel — the web app
1. vercel.com → **Add New… → Project** → **Import** `physicallovablex` → **Root Directory → Edit → `app/web`** (Framework: Next.js, auto). Leave build/install commands.
2. **Environment Variables** (Production, Preview):

| Name | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<api>.up.railway.app` (no trailing slash) |
| `API_SHARED_KEY` | same value as on Railway — **server-only, no `NEXT_PUBLIC_` prefix** |
| `APP_PASSWORD` | the password you give the jury — **server-only** |

3. **Deploy** (~2 min). Copy the URL `https://<vercel-project>.vercel.app` = **Web URL**.

Server-only means **no `NEXT_PUBLIC_` prefix**: the Next build was checked (dummy values) and neither the names nor the values reach `.next/static` or any client bundle; the proxy adds `X-App-Key` on `/backend/*` and drops the browser's cookie before forwarding. Railway must **not** have `APP_PASSWORD` (the API never reads it) and must have the **same** `API_SHARED_KEY` as Vercel. The password screen keeps the query string: `/?mode=idea` → `/login?next=%2F%3Fmode%3Didea` → back to `/?mode=idea`.

## 5. Connect the two
4. Railway → service → Variables → set `CORS_ORIGINS=https://<vercel-project>.vercel.app` (scheme + host, no path; comma-separate a custom domain too). It redeploys in ~1 min.

## 6. Test (3 min)
0. **Before the demo: `curl -X POST -H "X-App-Key: <API_SHARED_KEY>" https://<api>/demo/reset`** — clean DB, the 2 cached examples + the 11 showcases (`GET /examples`), fresh factory network (15 fictional partners).
   MCP smoke test (7 tools; the endpoint is stateless, no session id needed):
   ```bash
   # without the token → 401
   curl -s -o /dev/null -w "%{http_code}\n" -X POST https://<api>/mcp -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
   # with the token → 200 and 7 tool names
   curl -s -X POST https://<api>/mcp -H "Authorization: Bearer $MCP_TOKEN" -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
     | grep -o '"name":"[a-z_]*"' | sort -u        # 7 lines
   ```
1. Open the Web URL → password screen → password → home.
2. Open the desk-lamp example: 3D model loads, 13 stages, **Export** downloads the PDF.
3. New project with the desk-lamp prompt → autorun ≈ 1 min → stages turn green; no "Cached example" banner when the key is valid.
4. `/factories` → every card says "Fictional — demo data".
5. Wrong password → stays on the password screen. `curl https://<api>/projects` without the header → 401.
6. `https://<vercel-project>.vercel.app/docs` and `/agents.md` load with **no password prompt** (public, served from the web build — no `X-App-Key` involved).
7. Open the `whoop_kitesurf` showcase (`/projects/demo_whoop_kitesurf/wow` behind the password screen, or from the gallery on the home page): 3D model, engineering and firmware load instantly (recorded in the image — no LLM call).

## 7. Framer
Framer → the **Get Started** button → Link → web page → `https://<vercel-project>.vercel.app/?mode=idea` → **Publish**. (Prototype flow: `/?mode=prototype`.)

## 8. Cleanup (optional)
Delete the old repo: github.com/orpheo28/physicallovablex-mvp → Settings → Danger Zone → Delete this repository. Only after Railway and Vercel point at `physicallovablex`.

## Redeploy after changes
The pushed clone at `~/physicallovablex-export` is separate from this working tree (`mvp/`). Two ways to ship a later change:

### The everyday command: `ship.sh`
```bash
cd ~/Desktop/Hexa_Case/04_LIVRABLE
./ship.sh --commit "what changed, one line"       # you edited mvp/ yourself and want it committed too
./ship.sh "what changed, one line"                 # mvp/ is already committed (e.g. you committed it in your editor)
```
One command, in order, stopping at the first failure (nothing partial is ever pushed):
1. *(only with `--commit`)* in `mvp/`, stages **only** safe paths — `web/ api/ contracts/ factory_mcp/ docs/ scripts/` and any
   new `*.py` under `tests/`; it never stages `.env*`, `*.db`, `api/data/` or `tests/results/` scratch, even if one of those
   sits inside a staged folder (checked twice: by folder, then a denylist scan of whatever got staged). If `web/` changed it
   runs `npm run build` first; if `api/`, `contracts/` or `factory_mcp/` changed it runs `uv run pytest -q -x`; either failing
   **aborts with nothing committed**. Otherwise it commits with your message. If `mvp/` already matches your message (nothing
   pending in the safe paths), it says so and moves on — this is also how you use it after committing by hand.
2. Runs `./export_repo.sh --update ~/physicallovablex-export "your message"` — full checks, one commit, never pushes (below).
3. Prints a diff stat grouped by top folder (`app/web`, `app` outside web, `gtm`, `gtm-harness`, `docs`) and, from that, what
   will redeploy: **Vercel** if `app/web/` changed, **Railway** if `app/` changed outside `app/web/`, or **nothing** if only
   `gtm/`, `gtm-harness/` or `docs/` changed — assuming the two dashboard settings below are in place.
4. Asks **`Push to GitHub? [y/N]`**. Only `y` runs `git push` in the export dir; anything else (including Enter) prints the
   command instead and pushes nothing. Never `--force`.

### The lower-level command: `export_repo.sh --update`
`ship.sh` step 2 is exactly this — call it directly when `mvp/` is already committed and you just want to export + look at the
diff yourself before deciding to push:
1. `cd ~/Desktop/Hexa_Case/04_LIVRABLE && ./export_repo.sh --update` — builds the export fresh into a temp folder with the
   same checks as the first export (aborts before touching anything on a planted key, a forbidden path, a file over 50 MB, or a
   discovery email), then syncs it into `~/physicallovablex-export` and makes **one** commit `Update: <label>` (label defaults to
   `mvp`'s current tag or short hash, e.g. `pass-5`; pass your own: `./export_repo.sh --update ~/physicallovablex-export my-label`).
   It prints `git status --short | wc -l` and a diff stat before committing, and says "nothing to commit" if the export is
   unchanged. It never pushes.
2. `cd ~/physicallovablex-export && git push` — Railway and Vercel are both connected to this GitHub repo's `main` branch, so
   each auto-deploys from the push (watch their Deployments tab).
3. **Before this first push after the W21/W22/W23 additions**, add these Railway variables (Vercel needs no new ones):

| Variable | Value | Why |
|---|---|---|
| `MCP_TOKEN` | `openssl rand -hex 24` | gates `POST /mcp` (falls back to `API_SHARED_KEY` if left unset — set it so the MCP token can be handed out separately from the web/API key) |
| `CODEGEN_ENABLED` *(optional)* | `1` (default, already in the image) | AI-written CAD in Studio; `0` = parametric families only |
| `CODEGEN_MEM_MB` *(optional)* | `1280` (default) | AI CAD sandbox address-space cap |
| `CODEGEN_DATA_MB` *(optional)* | `640` (default) | AI CAD sandbox data-segment cap |
| `STUDIO_RATE_LIMIT_PER_DAY` *(optional)* | `100` (default) | Studio prompts per visitor IP per 24 h |
| `PHOTO_RATE_LIMIT_PER_DAY` *(optional)* | `30` (default) | Studio photo jobs per visitor IP per 24 h |

   Also confirm (already set from §3, re-check after the redeploy): `LLM_IMAGE_MODEL=google/gemini-3.1-flash-image` and
   `LLM_IMAGE_MAX_RENDERS=1`.
4. **Smoke test** after both deployments finish:
   ```bash
   curl -s https://<api>/health                                                       # "status":"ok"
   curl -s -o /dev/null -w "%{http_code}\n" -X POST https://<api>/mcp -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'   # 401
   curl -s -X POST https://<api>/mcp -H "Authorization: Bearer $MCP_TOKEN" -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
     | grep -o '"name":"[a-z_]*"' | sort -u                                           # 200, 7 tool names
   ```
   Then in a browser: `https://<vercel-project>.vercel.app/docs` and `/agents.md` open with no password prompt; the password
   screen still gates everything else; log in and open the `whoop_kitesurf` showcase (loads instantly, no LLM call).

### Selective redeploys (set once, so a `gtm/`- or `docs/`-only push costs nothing)
Both `ship.sh` and `git push` alone trigger a build check on both dashboards by default; these two settings make each platform
skip its build when nothing relevant to it changed, matching the "will redeploy" line `ship.sh` prints.
- **Railway** → the API service → **Settings → Build → Watch Paths** → add `app/**` then `!app/web/**` (the `!` excludes;
  order matters — the exclude line must come after the include). Railway then only rebuilds when a push touches `app/`
  outside `app/web/`.
- **Vercel** → the project → **Settings → Git → Ignored Build Step** → **"Only build if there are changes to..."** and set the
  path to `app/web`, or paste this custom command (skips the build unless something under `app/web/` changed since the last
  deploy — exit code 1 tells Vercel to proceed, 0 tells it to skip):
  ```bash
  git diff --quiet HEAD^ HEAD -- app/web && exit 0 || exit 1
  ```

---

## Roll back / stop the spend
- **Vercel:** Deployments → last good → ⋯ → **Promote to Production**.
- **Railway:** Deployments → previous → ⋯ → **Rollback** (volume untouched).
- **Stop all LLM spend now:** Railway → `DEMO_READONLY=1` (redeploys ~1 min), or delete `OPENROUTER_API_KEY`, and revoke the key on openrouter.ai.
- **Reset demo data:** `curl -X POST -H "X-App-Key: <API_SHARED_KEY>" https://<api>/demo/reset`.

## Costs (all **verify**)
- Vercel Hobby: $0 (non-commercial).
- Railway trial: $5 one-time credit, 30 days; then Hobby ≈ $5/month incl. $5 usage. One ~0.4 GB service + small volume ≈ a few dollars/month. Delete the service after the jury to stop billing.
- OpenRouter: pay per token. Your ceilings: `LLM_MAX_REQUESTS` (global), `LLM_MAX_TOKENS` (per call), `RATE_LIMIT_PER_DAY` (per IP). Also set a credit limit on the key on openrouter.ai and watch Activity.

## Plan B: the live demo runs on the laptop
```bash
cd app                                   # (or mvp/ in the working tree)
cp .env.example .env                     # OPENROUTER_API_KEY + 4 models; leave API_SHARED_KEY empty
uv sync
uv run uvicorn api.main:app --port 8000
curl -X POST localhost:8000/demo/reset
# second terminal
cd web && npm install && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev      # http://localhost:3000
```

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| Railway: "Dockerfile does not exist" | Root Directory not set to `app` |
| Railway build fails at `uv sync` | run `uv lock` in `app/`, re-export, push |
| Deploy "unhealthy" | Healthcheck Path not `/health`, or a crash: read the deploy logs |
| Web "API unreachable" | `NEXT_PUBLIC_API_URL` needs `https://` and no trailing slash; check Railway logs |
| Browser CORS error | `CORS_ORIGINS` ≠ the exact Vercel origin |
| 401 on everything | `API_SHARED_KEY` differs between Vercel and Railway |
| 429 "Daily limit reached" | one IP used its `RATE_LIMIT_PER_DAY`; raise it or restart the API |
| 403 "Read-only demo" | `DEMO_READONLY=1` is set (intended for the zero-cost mode) |
| Projects vanish after redeploy | no volume at `/data` |
| Old project's 3D files 404 | pruned by `MAX_STORED_PROJECTS`; re-run stage 2/3 |
| Everything "Cached example" | key/models missing or OpenRouter credits exhausted → check `/health` |
