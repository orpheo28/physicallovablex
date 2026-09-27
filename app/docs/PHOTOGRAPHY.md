# Product photography (W27)

Our old concept renders were text-to-image: the prompt *described* the product and the model invented one. They looked
generic and did not match the CAD. Professional AI product photography works the other way round: give the model a
**reference image of the real product** and let the prompt direct **only light, surface, lens and framing**. That is
what `api/cad/photos/` does — the reference is our own CAD.

## Pipeline

```
reference (in order)                                   prompt (api/cad/photos/shots.py)
 a. PNG/JPEG captured from the 3D viewer (client)  ─┐   shot direction: surface · light · lens · framing · shadow
 b. Blender render of the CAD (hero_v<n>.png /       ├─► + "Preserve the exact geometry, proportions, colours,
    hero_<dN>.png)                                   │     materials and details of the referenced product. No added
 c. none → text-only prompt (design described)     ─┘     text, logos, watermarks or extra objects unless stated."
                          │
                          ▼
   OpenRouter chat completion: [image_url(reference), text(prompt)], modalities [image, text],
   image_config.aspect_ratio 4:5 | 1:1, model LLM_IMAGE_MODEL  (api/cad/renders._call)
                          │
                          ▼
   centre-crop to the shot ratio, long edge 1280 px → /files/<pid>/photo_v<n>_<shot>.png (tmp + rename:
   a failed shot keeps the previous file) → Version.preview.photos (+ render_url for hero_studio), photos.json,
   stage 13 listing_photos (kit), Launch Dossier "Listing photos" page
```

- `render_product_photo(project_id, version, shot, reference_png=None)` — `api/cad/photos/engine.py`.
- Routes (`api/cad/photos/routes.py`, contract: `contracts/api.md` → "W27 — product photos"):
  `POST /projects/{id}/versions/{n}/photo?shot=…`, `POST /projects/{id}/photos/kit`, `GET /projects/{id}/photos`.
- With a reference, the prompt contains **no product description** (tested). The category (engineering pack key:
  wearable, vacuum, solar_roof…) only picks the lifestyle scene and the in-hand gesture.
- The text-only fallback (`renders.PROMPT`, still used by stage 2 and live Studio concept renders) was rewritten in the
  same photographic language: warm paper seamless #F4F1EA, 45° soft key + bounce fill + rim, 100 mm macro look,
  contact shadow.

## Shot library

| Shot | Ratio | Direction (abridged) |
|---|---|---|
| `hero_studio` | 4:5 | warm paper seamless #F4F1EA, no horizon · soft key camera-left 45°, bounce fill right, subtle rim, all lights off-camera · 100 mm macro look f/8, same ¾ angle as the reference · contact shadow · matte stays matte |
| `packshot_white` | 1:1 | infinite white #FFFFFF, no props · two off-camera softboxes + top fill, faint contact shadow only · 85 mm f/11 · product fills ~85 % · marketplace-compliant main image |
| `lifestyle` | 4:5 | scene from the category table · natural light of the scene · 50 mm f/2.8, product sharp at real scale · ≤ 3 props · any person anonymous, no face |
| `in_hand_scale` | 4:5 | hands / forearms only (gesture from the table), neutral warm-grey seamless · soft window light · 85 mm f/4 |
| `detail_macro` | 1:1 | close-up of an edge / joint / surface · raking soft light · 100 mm macro f/2.8, shallow depth of field |

Category → scene (`SCENES` in shots.py; scenes name place and light, never the product):

| Category | Lifestyle scene | In-hand / scale |
|---|---|---|
| wearable | wrist of a kitesurfer on a beach at golden hour, kite lines blurred, no face | worn on a wrist |
| furniture_baby | calm Scandinavian nursery, morning daylight, muslin blanket, plant, no baby | adult hand on the top edge |
| vacuum | bright modern apartment, oak parquet, sofa edge and rug out of focus | hand on the handle |
| solar_roof | clay-tile roof of a white Basque house in Biarritz at midday | gloved installer's hand on the frame |
| drone | in flight above the Atlantic coastline, kitesurfer tiny in the distance | held in an open palm |
| irrigation | small lush garden bed, lavender, morning sun, droplets | hand adjusting it |
| surfboard | on the sand at golden hour, waves behind | under one arm, no face |
| hair_dryer | bathroom vanity, marble, folded towel, window light | held in one hand |
| home_robot | family living-room floor, three wooden toys | adult hand placing a block |
| camera | sunlit café table, coffee, blank-backed prints face down | held in two hands |
| smartphone | linen tablecloth by a window, book, tea, screen off | held in one hand |
| lighting / tracker / generic | home-office desk at dusk / entry table with keys / modern living space | one hand |

Principles used (astorie.ai product-photography prompts, pebblely.com AI product photography prompts): let the
reference carry identity and keep the prompt about photography; name the light source, its direction and quality;
name a concrete surface; state lens and framing and the aspect ratio; ground the product with a contact shadow;
2-3 props maximum; marketplace packshots on pure white.

## Honesty labels

| Case | `label` |
|---|---|
| reference = viewer capture or Blender CAD render | **Photo-styled from the CAD (AI image, geometry from our CAD)** |
| no reference (text-only) | **AI concept image (no CAD reference)** |
| lifestyle / in-hand (`staged: true`) | the above + **" · Staged scene — illustrative"** |

The UI shows the label under every photo. Showcase projects carry an extra stage-2 assumption `a2_photo`; `a2_render`
(concept render) is unchanged.

## Model choice — A/B (hero_studio, Blender reference)

`docs/screens/photos/ab/`: `whoop_hero_{flash,pro}.png`, `vacuum_hero_{flash,pro}.png`.

| Model | Cost / image (OpenRouter usage) | Time | Verdict |
|---|---|---|---|
| `google/gemini-3.1-flash-image` (Nano Banana 2) | **$0.068** (1K, 4:5) | ~11-13 s | faithful geometry and colour, keeps small details (status LED), believable paper texture and contact shadow |
| `google/gemini-3-pro-image` | ~$0.137 (2×) | ~20 s | equally faithful, slightly flatter; on the vacuum it added a visible bounce card (an extra object — prompt since fixed: "all lights off-camera") |

**Pick: Flash for live and for the recorded showcases** — Pro was not clearly better at 2× the price and ~2× the latency.
`LLM_IMAGE_MODEL_SHOWCASE` (optional) switches the recorder to another model.

## Showcases

Reference = Blender render of the current version's GLB (`api/cad/_blender_render.py`, 1200 px, 64 spp) →
`api/cad/prebuilt/showcase_<slug>/hero_v<n>.png`. Then:

```
uv run python -m api.fixtures._showcase photos [slugs…] --budget 2.0 [--lifestyle a,b]   # live, prints spend
FILES_DIR=$(mktemp -d) OPENROUTER_API_KEY= uv run python -m api.fixtures._showcase apply-photos        # fixtures, $0
```

Contact sheets: `docs/screens/photos/showcases/` (CAD references, hero_studio, lifestyle).

`photos` writes `photo_v<n>_hero_studio.png` + `photo_v<n>_lifestyle.png` (256-colour dithered PNG like the other
recorded renders) and `photos.json` (manifest: reference, model, cost, seconds). `apply-photos` sets the current
version's `preview.photos` + `render_url` (hero_studio replaces the concept image in the Studio and on the gallery
card), the chosen direction's `render_url` (02_design + snapshot), `13_brand.listing_photos` (lifestyle), assumption
`a2_photo`, and rebuilds `example.json` (`hero_image_url`, `hero_image_label`, `photos`).

## Costs

- Flash: $0.068 per image (1K). A listing kit (4 shots, generated in parallel) ≈ $0.27 and ~15 s end to end
  (measured on demo_stick_vacuum, `docs/screens/photos/kit/`); hero + lifestyle ≈ $0.14.
- W27 recording spend: A/B $0.41 (2 × Flash + 2 × Pro) · 11 showcases × (hero_studio + lifestyle) = 22 images $1.49 ·
  live kit check $0.27 — ≈ $2.18 total.
- Pro: ≈ $0.137 per image.
- Live guard: per-IP `PHOTO_RATE_LIMIT_PER_DAY` (default 30 jobs), `DEMO_READONLY` → 403, `LLM_MAX_REQUESTS` counts
  every image request, 402 stops the job calmly ("Image credits exhausted (HTTP 402) — the previous photo is kept.").

## For the UI (W26c)

1. Capture the viewer: with three.js / react-three-fiber create the renderer with `preserveDrawingBuffer: true`
   (or call `gl.render(scene, camera)` right before capturing), frame the product ¾ from slightly above on a plain
   background, then `gl.domElement.toBlob(b => …, "image/png")` (≤ 2 MB: a 1024-1400 px canvas is plenty; use
   `image/jpeg` 0.9 if larger). Transparent pixels are flattened onto #F4F1EA server-side.
2. `POST /projects/{id}/versions/{n}/photo?shot=hero_studio` with `FormData` field `image` (or JSON
   `{image_base64}`) → 202. Without an image the server uses the Blender CAD render when present, else text-only.
3. Poll `GET /projects/{id}/photos` every ~2 s while `job.state === "running"`; show `photos[]` with their `label`.
4. "Listing kit" button → `POST /projects/{id}/photos/kit` (same optional image) → same polling; stage 13 shows
   `listing_photos`.
