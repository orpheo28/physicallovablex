# PhysicalLovableX — brand and UI spec

Use this to rebuild the web app's look 1:1 in Framer. Every value below is the one used in the code (`web/src/app/globals.css`, `web/src/components/ui.tsx`). Where they differ, the code wins.

**Character (W26):** calm, premium, frictionless — in the spirit of Lovable, v0, Linear, Vercel and Apple, on warm paper. Space, not borders. One primary action per screen. The product and the numbers are the heroes; honesty labels are always there but quiet (a coloured dot, the full label in a tooltip).

**Reference screenshots** (`docs/screens/v3/`, before/after pairs `<screen>__before.png` / `<screen>__after.png`, 1440×900 unless suffixed `_1280` / `_1512`):
1. `home__after.png`: centered prompt, submit arrow inside the field, soft example chips, large gallery cards.
2. `studio_whoop__after.png`: two calm panes — conversation left, the product large on the right with a key-value grid under it. Icon rail for the 13 steps.
3. `overview_whoop__after.png`: product on graph paper, cost tiers, shortlist, spec strip on a tint.
4. `stage05_whoop__after.png`, `stage08_whoop__after.png`: stage view — light header, white surfaces without borders, hairline tables.
5. `studio_whoop_tooltip__after.png`, `studio_whoop_menu__after.png`, `home_more_ways__after.png`: tooltip, ⋯ menu and popover styles.

---

## 1. Colour

### Core

| Token | Hex | Use |
|---|---|---|
| `paper` (background) | `#F7F6F3` | Page background everywhere |
| `paper-2` | `#EFEDE8` | Neutral pill background, skeletons, progress-bar track, ghost-button hover |
| `surface` | `#FFFFFF` | Cards (borderless, on paper), tables, inputs, floating layers |
| `sunken` | `#FAF9F7` | Table-row hover, disabled inputs |
| `ink` | `#111111` | Primary text, ink buttons, active controls |
| `ink-2` (secondary) | `#5F5E5A` | Secondary text (AA on paper and white) |
| `ink-3` (tertiary) | `#8A8883` | Meta text, IDs, units. Large or non-essential text only |
| `ink-4` | `#B9B6AF` | Separators such as `×` and `/`, empty values `—` |
| `line` (hairline) | `#E6E4DF` | Table and list row rules, tab underlines (not boxes) |
| `line-2` (strong hairline) | `#D6D3CC` | Input borders, secondary-button inset, summary-row rules |
| `accent` | `#FF4F00` | The one primary action and the current state only |
| `accent` hover | `#FF6A26` | Primary button hover |
| `accent-ink` | `#C43C00` | Accent used as text on light backgrounds (AA) |
| `accent-soft` | `#FFF1EA` | Tint behind recommended or highlighted items |
| `danger` / `danger-soft` | `#C4321F` / `#FBEEEC` | Errors, "not reachable", critical severity |

**Accent discipline (W26):** `#FF4F00` marks exactly two things: the single primary action of the screen (Make it / Open overview / Export / Next / the home submit arrow) and the current state (current version dot, current step). Never a decorative rule, never a key-number underline.

### Trust labels

Every number carries one of four labels. **W26: the label is a 7 px coloured dot right after the value**; hovering (or focusing) the value or the dot shows a dark tooltip with the label name and its source or assumption. Screen readers read the label name (visually hidden text). The legend appears once, in the status bar.

| Label | Dot | Text (when printed) | Tint (banners only) |
|---|---|---|---|
| Measured | `#1F8A4C` | `#1D6B3E` | `#ECF6EF` |
| Sourced | `#2F6FD6` | `#2556A8` | `#EDF2FB` |
| Estimate | `#C98A0B` | `#8A5D00` | `#FBF4E4` |
| Fictional — demo data | `#7C4DDB` | `#5D37AD` | `#F3EFFB` |

- At **section level** (a factory shortlist, a quote list, a factory profile) the label is printed as text next to its dot ("● Fictional — demo data", 11–13 px, label ink colour), so a whole block of simulated records is never unlabeled at a glance.
- **Violet is reserved for fictional data.** A fictional section gets a 2 px left rule in `#7C4DDB` at 50 % opacity plus the printed label.
- The **Fictional banner** (factory portal) and the **Cached example** banner stay visible: a full-width tint (`fictional-soft` / `estimate-soft`), no border, one line of text.

---

## 2. Typography

| Family | Role | Weights |
|---|---|---|
| **Inter Tight** (Google) | All UI and body text | 400, 500, 600 |
| **Archivo, width axis at 72 %** (Google, variable `wdth`) | Condensed display: **only the home headline** ("WHAT DO YOU WANT TO MAKE?"), uppercase | 600 |
| **Geist Mono** (Google) | **Only numbers, units and code** (prices, dimensions, scores, IDs, CAD programs). Tabular figures. Never labels or headers | 400, 500 |

W26: every title (page, stage, product name, Factory Pack title) is Inter Tight 600, tracking −0.022 em, sentence case (`.title`). Labels and table headers are sentence-case Inter Tight — no letter-spaced mono capitals.

Numbers always use tabular figures (`font-variant-numeric: tabular-nums`).

### Scale

Size / line-height in px; tracking in em.

| Name | Size / LH | Weight | Tracking | Use |
|---|---|---|---|---|
| 2xs | 11 / 16 | 500 | 0 | Pills, badges |
| label | 12.5 / 18, Inter Tight, sentence case, `#8A8883` | 500 | 0 | Field and stat labels, table headers (`.micro`, `Th`) |
| xs | 12 / 16 | 400–500 | 0 | Segmented control |
| sm | 13 / 20 | 400–500 | 0 | Meta, captions, buttons |
| base | 14 / 22 | 400 | 0 | Body, table cells |
| md | 16 / 26 | 400–600 | 0 / −0.01 | Lead paragraphs, card titles |
| lg | 20 / 28 | 500–600 | −0.015 | Sub-headings, recommendation name |
| xl | 28 / 34 | 500–600 | −0.02 | Big numbers (mono) |
| section title | 14 / 22, Inter Tight | 600 | −0.01 | Card and section titles |
| page title | 26–28 / 32–34, Inter Tight | 600 | −0.022 | Page and stage titles |
| product title | 28–40 (clamp) / 1.08, Inter Tight | 600 | −0.022 | Overview product name, Factory Pack title |
| home headline | 44–72 (clamp 7.4vh) / 0.95, **Archivo 72 % wdth, UPPERCASE** | 600 | −0.01 | Home only |
| marketing H1 (`/about`) | 44–64 (clamp) / 1.02, Inter Tight | 600 | −0.035 | Landing headline, max width 14ch |

Keep body line lengths under 72ch.

---

## 3. Layout and spacing

- **Grid:** 4 px base, 8 px rhythm. Spacing steps: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80.
- **Container:** max width 1320 px; side padding 24 px (40 px from 1024 px up). Left-aligned.
- **Section spacing:** 80 px vertical between marketing sections. Inside the app: 24 px between cards, 32 px after the page header.
- **Top bar:** 52 px high, paper, **no rule**. Lockup left, project progress centred (not in the Studio), three nav items right: Examples · Factory portal · Docs (the lockup is "new project").
- **Space, not borders.** Group with whitespace, alignment and white surfaces on paper (no outline). Hairlines only where they carry meaning: table rows, list rows, tab underlines, the Factory Pack section rules.
- **One primary action per screen** (accent). Secondary actions are quiet text buttons (ghost) or live in a "⋯" menu.
- **Never truncate important text.** Wrap or reflow; ellipsis only with the full text on hover.

---

## 4. Radius, borders, elevation

- **Radius (concentric):** 6 px (`rounded-sm`: chips inside surfaces, menu items), 8 px (`rounded`: buttons, inputs, segmented controls), 12 px (`rounded-md`: cards, media, banners), 16 px (`rounded-lg`: floating layers — prompt field, composer, menus, dialogs), fully round (chips, send button, dots).
- **Borders:** none on surfaces. 1 px `#E6E4DF` for table/list row rules and tab underlines; `#D6D3CC` for form inputs; `#D6D3CC` 1 px for Factory Pack section rules.
- **Elevation — one shadow, floating layers only** (prompt field, composer, menus, popovers, dialogs, tooltip): `0 0 0 1px rgb(17 17 17 / .06), 0 2px 4px rgb(17 17 17 / .04), 0 12px 32px -12px rgb(17 17 17 / .18)` (`shadow-float`). No shadow on cards; no glow, no gradients, no glassmorphism. Dialog backdrop: ink at 30 %.
- **Images:** a 1 px outline `rgb(0 0 0 / .06)` inset (`.img-outline`), radius 12 px.
- **Focus:** 2 px `#111111` outline, 2 px offset, on every focusable element; the prompt field and composer show focus as a darker ring on the whole card.

---

## 5. Components

### Buttons

Font: Inter Tight 500. Radius 8 px. No border. Transition 150 ms `cubic-bezier(.2,.7,.2,1)` on colour, background, shadow and scale; **press = scale 0.96**.

| Variant | Background | Text | Hover |
|---|---|---|---|
| **Primary** (one per screen) | `#FF4F00` | `#111111` | bg `#FF6A26` |
| **Ink** | `#111111` | `#FFFFFF` | bg `#2A2A2A` |
| **Secondary** | `#FFFFFF` + 1 px inset `#D6D3CC` | `#111111` | bg `#FAF9F7`, inset `#B9B6AF` |
| **Ghost** (quiet text button) | transparent | `#5F5E5A` | text `#111111`, bg `#EFEDE8` |
| **Disabled** (all variants) | `#EFEDE8` (neutral grey fill) | `#8A8883` | none; not-allowed cursor. Never a pale version of the enabled colour |

**Round submit buttons** (home prompt, Studio composer): 36 / 32 px circles with an up-arrow. Enabled: accent (home) or ink (Studio send). Disabled: `#EFEDE8` with `#B9B6AF` arrow.

**"⋯" menu:** 32 px ghost square with three dots; opens a 260 px floating panel (radius 16, `shadow-float`, 6 px padding) of items (13 px 500 title + 11 px `#8A8883` hint).

| Size | Height | Horizontal padding | Font | Icon gap |
|---|---|---|---|---|
| sm | 28 px | 10 px | 13 px | 6 px |
| md (default) | 32 px | 12 px | 13 px | 8 px |
| lg | 40 px | 16 px | 14 px | 8 px |

The landing CTAs are 20 px-padded cards: primary orange with ink text, or white with a `#D6D3CC` border. Title 16/26 at 600, sub-label 14/22. Arrow icon at the top right.

### Cards

- **W26b: a card is not a box.** A titled section sits directly on paper: title Inter Tight 16 px 600 ink, meta on the right in 13 px `#5F5E5A`, content under it; sections are separated by space (24 px), not by surfaces or rules. A fictional section keeps its 2 px violet left rule (16 px indent) and the printed label.
- White surfaces (no border, no shadow, 12–16 px radius) are kept only for things that read as one object: the stat strip, the negotiation chat, the recommendation, the quote comparison, the portal's MCP card and partner table, the Factory Pack document.
- **Stat strip:** one white surface, 2–5 cells separated by space only. Cell: label (12.5 px sentence case), the number (mono 28 px) with its dot, 13 px secondary text. The key cell's number is 600 weight — no accent rule.
- **Key-value grid** (Studio, under the product): three columns on paper, no surface — the object (Size, Look, Build path, Compliance "4 certifications ▾"), the cost (tiers or per installation, BOM lines), the makers (top 3 with a 40 px score bar and score). Labels 13 px `#8A8883`, values 13 px ink.

### Tables

- Header: Inter Tight 12.5 px 500, sentence case, `#8A8883`, no wrapping, 1 px `#E6E4DF` rule below.
- Rows: 1 px `#E6E4DF` dividers. Cell padding 10 px vertical, 12 px horizontal. First and last columns sit flush with the card padding.
- Numbers in Geist Mono, right-aligned, each followed by its trust dot. Row hover `#FAF9F7`.
- Summary rows (unit cost, totals) get a `#D6D3CC` rule above and 500 weight.
- A **recommended column** (quote comparison, W26b) gets a subtle `#FFF1EA` tint at 70 % over the whole column and a small "Recommended" label in `#C43C00` above the factory name — no rules, no pill.

### Chips, pills and badges

- **Chips** (example prompts, suggestions, tags): 28–32 px high, fully round, `#EFEDE8` at 80 %, text `#5F5E5A` 13 px, no border; hover full `#EFEDE8` + ink text; selected = ink fill, white text.
- **Pills** (status, "Example project"): 20 px high, 8 px padding, fully round, 11 px 500, sentence case, no border.
- **Trust labels:** a dot + tooltip (section 1), not a pill.
- **Tooltip:** ink `#111111` panel, radius 10, 8 × 10 px padding, 12.5 / 18 white text; first line = dot + label name (500), then the source in white at 75 %. Fades in over 120 ms.
- **Neutral pill:** bg `#EFEDE8`, text `#5F5E5A`, dot `#B9B6AF`. Used for "Example project" and modes.
- **Accent pill:** bg `#FFF1EA`, text `#C43C00`, dot `#FF4F00`. Used for "Chosen" and "Recommended".
- **Status:** Validated uses the measured green, Draft uses the estimate amber.
- **Severity** is text plus an 8 px square: critical/high `#C4321F`, major/medium `#C98A0B`, minor `#B9B6AF`.
- **Layer tags** (Lovable, Core…): 20 px pill, `#EFEDE8`, 11 px 500 sentence case, `#5F5E5A` (Core in ink). No accent.
- **Step status** in a stage header: plain text ("✓ Validated" ink-2, "● Draft" amber, "Not started" ink-3) — not a trust label.

### Inputs

Form fields: white background, 1 px `#D6D3CC` border, 8 px radius, 8 × 12 px padding, 14/20 text, placeholder `#8A8883`. Hover border `#B9B6AF`. Focus: border `#111111` plus a 3 px ring of `rgba(17,17,17,.06)`.

**Prompt field (home) and composer (Studio):** a floating white card (radius 16, `shadow-float`), a borderless textarea (home 20 / 28, Studio 14 / 22), and a toolbar row inside the card — home: the "Idea · Prototype" segmented switch, "More ways to start ▾" (Autofill all 13 steps · Go step by step), then the round submit arrow on the right; Studio: "Enter to send · Shift+Enter for a new line" (11 px), then the round send button. Enter submits.

**Segmented control:** `#EFEDE8` track, 2 px padding, radius 8; selected segment = white with a 1 px hairline shadow, ink text; others `#5F5E5A`.

### Progress

- **Top-bar progress** (overview, stages, Factory Pack; **not in the Studio**): 13 segments 12 × 2 px, 2 px gaps. Validated `#111111`, draft `#C98A0B`, not started `#D6D3CC`, current `#FF4F00`; then "Step 5 of 13 · Costs & investment" in Inter Tight 13 px.
- **Progress bars:** 3 px, fully round, track `#EFEDE8`, fill `#FF4F00` (or ink for scores).

### Graph-paper texture

Placed behind product stills and the 3D view only, never behind text.
- Cell 24 × 24 px, centred.
- Lines 1 px `#111111` at **4.5 % opacity** (`rgba(17,17,17,.045)`) on `#F7F6F3`.
- Radial fade: an elliptical mask centred on the product, opaque to 35 %, transparent at 72 %. So the grid dissolves before the edges and never shows a box.
- The product still blends into the paper with "darken" blending and brightness 1.03, which removes the render's own background.

### Product photos (W27 / W26c)

- AI photos styled from our CAD (docs/PHOTOGRAPHY.md). **The label is always visible under the photo**, 11–13 px `#8A8883`: "Photo-styled from the CAD (AI image, geometry from our CAD)"; staged shots (lifestyle, in hand) add " · Staged scene — illustrative", printed in the Estimate ink `#8A5D00`.
- Photos: radius 12, the 1 px image outline, no frame or shadow; 4:5 (hero, lifestyle, in hand) or 1:1 (packshot, detail).
- **Studio / Overview:** the view toggle reads "Photo · 3D" (Overview also "Lifestyle" when recorded); the photo replaces the concept render. While a photo is being made: "Taking the photo, about 12 s…" in a small chip on the viewer.
- **Gallery cards:** a small pill on the image, "AI photo · geometry from our CAD" (full label in the tooltip); on hover the lifestyle photo fades in (300 ms) and the pill reads "AI photo · staged scene, illustrative".
- **Listing photos** (stage 13, and the Studio "⋯" → "Listing photos" dialog): a 4-up grid Packshot · Lifestyle · In hand · Detail, each with its label and a "Download" text link; empty slots read "Not generated yet". "Generate listing photos" is secondary on stage 13, primary in the dialog.
- **Calm states** (one tinted line, never a red error): no image model → the button is disabled with "No image model is configured here…"; 403 read-only demo, 409 a photo job already running, 429 daily limit, 503 no model — each one plain sentence that says what still works.

### Charts

- Cumulative line: ink `#111111`, 1.5 px, 2.5 px dots.
- Bars: `#FF4F00`, 14 px wide, 1 px top radius.
- Grid: horizontal only, `#E6E4DF`.
- Axis ticks: Geist Mono 11 px `#8A8883`, no tick marks.
- Tooltip: white, 1 px hairline, 4 px radius, no shadow.
- Part-of-whole series order: `#111111`, `#FF4F00`, `#8A8883`, `#3F5E7C`, `#C9C5BC`, `#B7793F`, `#5C5B57`, `#7C8F6A`, `#E3DFD6`, `#9A6B8F`.

---

## 6. Iconography

- Inline SVG line icons only, 1.5 px stroke, round caps and joins, `currentColor`, 12–16 px.
- The set is small: arrow-right, download, chevron, check, warning triangle, edit pencil, info circle.
- No icon libraries, no filled or duotone icons, no emoji.
- **Lockup** (replaces the orange-square wordmark; `web/src/components/Lockup.tsx`):
  1. Hexa logo `web/public/brand/hexa-logo.webp` (source 2000 × 720), **22 px high** (≈ 61 px wide), no recolouring, no effects.
  2. 12 px gap, a **1 × 16 px hairline divider** in `#D6D3CC`, 12 px gap.
  3. "PhysicalLovableX" in Inter Tight **14 px 600**, −0.01 em, ink `#111111`.
  4. 12 px gap, a **"Case study" tag** (W26): Inter Tight 11 px 500, sentence case, `#5F5E5A` on `#EFEDE8`, 20 px high, fully round, 8 px side padding, no border.
  - Large variant (`size="lg"`): logo 26 px, divider 20 px, wordmark 16 px.
  - Used in the top bar (links home), the login card, the mobile gate and the Factory Pack title block (there without the tag). Clear space around it: at least the logo height.
  - **The favicon stays neutral** (`web/src/app/icon.svg`); never use the Hexa mark as a favicon or app icon.

---

## 7. Motion

UI feedback: 120–200 ms, `cubic-bezier(.2,.7,.2,1)`, on colour, background, shadow, opacity or scale (press 0.96) — properties always named, never `transition: all`. Gallery images scale to 1.03 on hover over 500 ms `cubic-bezier(.2,0,0,1)`. The 3D model fades in over 400 ms and turns at 12°/s. No bounce, no loops, no confetti. Respect `prefers-reduced-motion`: the final state shows at once.

Exactly **three motion moments** (anime.js v4, loaded on demand in client components, `web/src/lib/motion.ts`), easing `outExpo` or `inOutQuad`, 150–700 ms per element, transform / opacity / height only (no layout shift). Numbers always end exactly on the real value; trust labels and banners never animate.
1. **Autofill stepper:** a 1 px ink line draws down each phase column as the polled progress arrives (600 ms); a step that completes gets its check stroke drawn (320 ms).
2. **Overview entrance** (once per visit, ≈ 1.2 s): the product fades up 8 px (600 ms); the unit costs count up to their value (700 ms, 80 ms apart); the factory rows fade in 4 px, 80 ms apart, and their score bars fill.
- **Studio (also anime.js):** a new answer fades up 6 px (360 ms); when a version completes, its change rows stagger in (3 px, 300 ms, 40 ms apart); the product cross-fades (400 ms) when the version or view changes; changed numbers tick from the old value.
3. **Progress draw** (first load per session, ≈ 600 ms): the 13 top-bar segments draw left to right, then the current step settles in the accent.

## 7b. App shell (desktop)

- One screen, the page never scrolls: top bar 52 px · main panel · status bar 28 px (the one trust-label legend as dots + names, the demo disclaimer). No rules between them. Only designated regions scroll: a thin 8 px scrollbar in `#D6D3CC` (`#B9B6AF` on hover) and 20 px fades at the top / bottom edge, shown only when there is more content that way (`.scroll-y`, `ScrollArea`).
- Project screens: a 248–256 px left rail, **no border**, with the 13 steps in 4 phases (Design · Make it manufacturable · Source · Launch; phase names 11 px sentence case), plain-language names first; status icons done (ink check), draft (amber check), current (accent ring), to do (hollow ring). Active item = white pill.
- **Studio:** the rail collapses to a 56 px **icon rail**: Studio, Overview, Factory Pack icons, then the **4 phases** (Design · pencil, Make it manufacturable · gear, Source · factory, Launch · box), each a 13 px line icon inside a 28 px progress ring (track `#E6E4DF`, arc `#5F5E5A` = share of steps done; amber if a step is a draft, accent while autofill runs in that phase). Hover/label: "Design: 3 of 3 steps done"; a click opens the phase's first step not done. At 1280 px the conversation gets 380–430 px, the composer is one auto-growing line (`field-sizing: content`), and two suggestion chips show (three from 1440 px). Left pane (360–440 px): the conversation — user messages as `#EFEDE8` bubbles on the right (radius 16, 4 px bottom-right corner), answers as plain text (the one-sentence summary), a change list (label · before → after · dot) separated by faint hairlines, a quiet meta line (v3 · 01:52 · built in 3.8 s · ● Current) with Preview / Restore appearing on hover; 3 suggestion chips and the floating composer at the bottom. Right pane: a slim header (product name 20 px 600, versions v1…vN as a segmented control with an accent dot on the current one, Concept / 3D toggle, ⋯, **one** primary "Make it" or "Open overview"), the product as large as possible on graph paper, quiet text tabs (Product · Engineering · CAD code · Firmware), then the key-value grid.
- **Overview (W26b):** the Studio's system — the product large on the left with a two-column key-value spec (size, weight, material, parts) under it; on the right the product title (Inter Tight 28–40 px), the prompt, the cost block (1 or 3 tiers; per installation when the unit basis says so) with cash / break-even / retail as plain key-values, and the shortlist as a quiet list (rank in `#B9B6AF`, name, reasons in full, score "86 / 100" with a 3 px `#8A8883` bar). One primary action in the header: "Export Launch Dossier", which reads "Download Launch Dossier" once Make it is done; the ready state is a single line under the prompt (ink check + "Launch Dossier ready.").
- **Negotiation (W26b):** the chat has no chrome: pill tabs per factory, 28 px round avatars (`#EFEDE8` platform, violet-soft factory), bubbles in `#F7F6F3` / `#EFEDE8` at 60 %, radius 16 with a 4 px corner; quote cards on a tint (the recommended one on `#FFF1EA`) with "Recommended" as text. The approval bar is a light `#F7F6F3` row inside the chat (amber-dot "Auto-approved (autofill mode)", a secondary "Change factory"); the side panel holds the recommendation and the quote comparison table.
- **Portal (W26b):** the "Connect your agent" card is white (radius 16) with the Claude Code command in one ink block (white mono text, "Copy" inside it) and the MCP tools as soft mono chips; load bars `#8A8883`, amber from 80 % load.
- Stage screens: a light header (one 13 px line "Step 5 of 13 · Phase · trade term", layer tag, status, provenance; the title; "What this step does" / "What you decide here" at 13 px), the content in its own scroll region, and a footer without a rule: "← Previous" and one primary "Next: <step> →".
- Below 1024 px wide (or a touch-first screen under 1280 px) nothing of the app renders: a full-screen "Built for desktop" message with the lockup and the URL to copy.

---

## 8. Do / don't

**Do**
- Show every number with its trust dot (label + source in the tooltip). The "Fictional — demo data" section labels and the "Cached example" banner stay visible as text.
- Let one thing per screen be bold: the product, or the key number.
- Use the condensed uppercase display type only for the home headline. Everything else is Inter Tight; Geist Mono only for numbers, units and code.
- Group with space and white surfaces on paper; keep hairlines for tables and lists.
- Put one primary action per screen; the rest are quiet text buttons or in "⋯".
- Use plain, specific copy: "about a minute (measured on 10 test prompts)", not "blazing fast".

**Don't**
- Add logo walls, testimonials, pricing tables, "Backed by" pills or social-proof counters.
- Add gradients, glow, glassmorphism, shadows on cards (the one shadow is for floating layers), dashed coloured borders, or outlines around every block.
- Use letter-spaced mono capitals for labels, or print trust labels as pills next to every number.
- Use orange for body text or large fills. Use `#C43C00` when orange must be text.
- Use violet for anything that is not fictional data, or green, blue or amber outside the trust labels, status and severity.
- Add a dark theme. The design is light only, made for screen share.
