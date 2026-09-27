# Quickstart

## In the app

1. **Describe a product.** Choose "I have an idea", type one sentence and start. Example: `A Whoop competitor: a screenless wrist-worn band, 5-day battery, tracks sleep and strain.`
2. **See version 1.** The 3D model, unit cost at three volumes and the top factories appear. Open the **CAD code** tab to read the program the AI wrote.
3. **Refine three times.** For example:
   - `Add heart-rate and HRV sensing`
   - `Thinner, 8 mm pod`
   - `Target retail $149`

   Each prompt creates a new version with a diff. Restore any earlier version from the version list.
4. **Make it.** The remaining steps run automatically: factories, negotiation, tooling, QC, shipping and duties, cash plan, brand. Auto-approved quotes are flagged: review the selected factory before any real order.
5. **Download the Launch Dossier** (PDF) from the export button.

## Through the API

Set your base URL and key. When the API is gated, every route except `GET /health` needs the `X-App-Key` header. When it is not gated (local dev), the header is ignored.

```bash
export API=http://localhost:8000          # or your deployed API URL
export APP_KEY=...                        # your key; never commit it
```

**1. Create the project** (returns `201`):

```bash
curl -s -X POST $API/projects \
  -H "X-App-Key: $APP_KEY" -H "Content-Type: application/json" \
  -d '{"mode":"idea","prompt":"A Whoop competitor: a screenless wrist-worn band, 5-day battery, tracks sleep and strain."}'
# → {"id":"...", ...}   keep the id
export PID=<id>
```

**2. Start the Studio** (returns `202`, builds version 1 in the background):

```bash
curl -s -X POST $API/projects/$PID/studio/start -H "X-App-Key: $APP_KEY"
# → {"version":1}
```

**3. Poll versions** every 1-2 s until version 1 is `done` and `render_pending` / `background_pending` are false:

```bash
curl -s $API/projects/$PID/versions -H "X-App-Key: $APP_KEY"
```

**4. Refine** (returns `202`; the new version starts `running`):

```bash
curl -s -X POST $API/projects/$PID/refine \
  -H "X-App-Key: $APP_KEY" -H "Content-Type: application/json" \
  -d '{"message":"Add heart-rate and HRV sensing"}'
# → {"version":2}
```

Poll `GET /projects/$PID/versions` again and read the `changes` array of the new version.

**5. Make it** (returns `202`; runs stages 1-13):

```bash
curl -s -X POST "$API/projects/$PID/autorun?through=13" -H "X-App-Key: $APP_KEY"
# poll every 2 s until autorun.state is "done"
curl -s $API/projects/$PID -H "X-App-Key: $APP_KEY"
```

**6. Download the Launch Dossier:**

```bash
curl -s $API/projects/$PID/export -H "X-App-Key: $APP_KEY" -o launch-dossier.pdf
```

Notes:

- `refine` and `autorun` return `409` while the other is running, and `refine` returns `409` before `studio/start`.
- A refine that fails leaves the previous version current; the failed version carries a plain-language `error`.
- Full reference: [Studio API](/docs/studio-api).
