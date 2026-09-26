# PhysicalLovableX — brand and UI spec

Use this to rebuild the web app's look 1:1 in Framer. Every value below is the one used in the code (`web/src/app/globals.css`, `web/src/components/ui.tsx`). Where they differ, the code wins.

**Character:** an engineering document from a premium hardware brand. Warm paper, ink, hairlines, one signal orange. The product and the numbers are the heroes. Quiet, precise, restrained.

**Reference screenshots** (`docs/screens/after/`):
1. `01_wow_lamp.png`: the overview. Product still on graph paper, condensed title, cost table, fictional factory shortlist.
2. `00_home.png`: the app home. Start form, example prompts, example cards.
3. `03_lamp_stage08.png`: stage view. Stepper, sidebar, stat and table styles, recommended column, transcript.
4. `04_factory_pack_lamp.png` (bonus): the document style. Title block and §-numbered sections.

---

## 1. Colour

### Core

| Token | Hex | Use |
|---|---|---|
| `paper` (background) | `#F7F6F3` | Page background everywhere |
| `paper-2` | `#EFEDE8` | Neutral pill background, skeletons, progress-bar track, ghost-button hover |
| `surface` | `#FFFFFF` | Cards, tables, inputs |
| `sunken` | `#FAF9F7` | Table-row hover, disabled inputs |
| `ink` | `#111111` | Primary text, ink buttons, active controls |
| `ink-2` (secondary) | `#5F5E5A` | Secondary text, micro-labels (AA on paper and white) |
| `ink-3` (tertiary) | `#8A8883` | Meta text, IDs, units. Large or non-essential text only |
| `ink-4` | `#B9B6AF` | Separators such as `×` and `/`, empty values `—` |
| `line` (hairline) | `#E6E4DF` | Default 1 px border and divider |
| `line-2` (strong hairline) | `#D6D3CC` | Table header rule, input and button borders |
| `accent` | `#FF4F00` | Primary button, active stage, key-number rule. Use it sparingly |
| `accent` hover | `#FF6A26` | Primary button hover |
| `accent-ink` | `#C43C00` | Accent used as text on light backgrounds (AA) |
| `accent-soft` | `#FFF1EA` | Tint behind recommended or highlighted items |
| `danger` / `danger-soft` | `#C4321F` / `#FBEEEC` | Errors, "not reachable", critical severity |

### Trust labels

Every number carries one of four labels. Each label is a tinted pill with a coloured dot.

| Label | Dot | Text | Tint (background) |
|---|---|---|---|
| Measured | `#1F8A4C` | `#1D6B3E` | `#ECF6EF` |
| Sourced | `#2F6FD6` | `#2556A8` | `#EDF2FB` |
| Estimate | `#C98A0B` | `#8A5D00` | `#FBF4E4` |
| Fictional — demo data | `#7C4DDB` | `#5D37AD` | `#F3EFFB` |

**Violet is reserved for fictional data.** A fictional card gets a 2 px left rule in `#7C4DDB` at 50 % opacity plus the label, never a dashed border.

---

## 2. Typography

| Family | Role | Weights |
|---|---|---|
| **Inter Tight** (Google) | All UI and body text | 400, 500, 600 |
| **Archivo, width axis at 72 %** (Google, variable `wdth`) | Condensed display: page titles, stage titles, the overview product name, the Factory Pack title. Always uppercase | 600 |
| **Geist Mono** (Google) | Numbers, units, codes, IDs, micro-labels, table headers. Tabular figures | 400, 500 |

Numbers always use tabular figures (`font-variant-numeric: tabular-nums`).

### Scale

Size / line-height in px; tracking in em.

| Name | Size / LH | Weight | Tracking | Use |
|---|---|---|---|---|
| 2xs | 11 / 16 | 500 | 0 | Pills, badges |
| micro-label | 10.5 / 16, **Geist Mono, UPPERCASE** | 500 | +0.06 | Section headers, table headers, stat labels |
| xs | 12 / 16 | 400–500 | 0 | Segmented control |
| sm | 13 / 20 | 400–500 | 0 | Meta, captions, buttons |
| base | 14 / 22 | 400 | 0 | Body, table cells |
| md | 16 / 26 | 400–600 | 0 / −0.01 | Lead paragraphs, card titles |
| lg | 20 / 28 | 500–600 | −0.015 | Sub-headings, recommendation name |
| xl | 28 / 34 | 500–600 | −0.02 | Big numbers (mono) |
| display title | 34 / 36, Archivo 72 % wdth, UPPERCASE | 600 | −0.01 | Page and stage titles |
| display document | 48 / 48, same | 600 | −0.01 | Factory Pack title |
| display hero | 60 / 57 (line-height 0.95), same | 600 | −0.01 | Overview product name |
| marketing H1 (`/about`) | 44–64 (clamp) / 1.02, Inter Tight | 600 | −0.035 | Landing headline, max width 14ch |

Keep body line lengths under 72ch.

---

## 3. Layout and spacing

- **Grid:** 4 px base, 8 px rhythm. Spacing steps: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80.
- **Container:** max width 1320 px; side padding 24 px (40 px from 1024 px up). Left-aligned.
- **Section spacing:** 80 px vertical between marketing sections. Inside the app: 24 px between cards, 32 px after the page header.
- **Sticky header:** 56 px high, paper at 90 % opacity with a 6 px backdrop blur, and a 1 px hairline at the bottom.
- Use hairline dividers and tables instead of boxes. Use one primary action per screen.

---

## 4. Radius, borders, elevation

- **Radius:** 3 px (small chips, inner marks), 4 px (buttons, inputs), 6 px (cards, media), fully round (pills, dots).
- **Borders:** 1 px `#E6E4DF` by default. Use 1 px `#D6D3CC` for controls and under table headers. Use 1 px `#111111` (ink) for document section rules and the Factory Pack title block.
- **Elevation:** no drop shadows, no glow, no gradients, no glassmorphism. Only the dialog backdrop uses ink at 30 % opacity.
- **Focus:** 2 px `#111111` outline, 2 px offset, on every focusable element.

---

## 5. Components

### Buttons

Font: Inter Tight 500. Radius 4 px. 1 px border. Transition 150 ms `cubic-bezier(.2,.7,.2,1)` on colour only.

| Variant | Background | Text | Border | Hover |
|---|---|---|---|---|
| **Primary** | `#FF4F00` | `#111111` | `#FF4F00` | bg and border `#FF6A26` |
| **Ink** | `#111111` | `#FFFFFF` | `#111111` | bg and border `#2A2A2A` |
| **Secondary** | `#FFFFFF` | `#111111` | `#D6D3CC` | border `#B9B6AF`, bg `#FAF9F7` |
| **Ghost** | transparent | `#5F5E5A` | transparent | text `#111111`, bg `#EFEDE8` |
| Disabled | same as its variant | | | opacity 45 %, not-allowed cursor |

| Size | Height | Horizontal padding | Font | Icon gap |
|---|---|---|---|---|
| sm | 28 px | 10 px | 13 px | 6 px |
| md (default) | 32 px | 12 px | 13 px | 8 px |
| lg | 40 px | 16 px | 14 px | 8 px |

The landing CTAs are 20 px-padded cards: primary orange with ink text, or white with a `#D6D3CC` border. Title 16/26 at 600, sub-label 14/22. Arrow icon at the top right.

### Cards

- White surface, 1 px `#E6E4DF` border, 6 px radius, no shadow.
- Header: at least 44 px high, 20 px horizontal padding, 1 px hairline below. Title Inter Tight 14 px 500 ink; meta on the right in 13 px `#5F5E5A`.
- Body padding 20 px.
- **Stat strip:** one card split into 2–5 cells by 1 px hairlines, 20 × 16 px cell padding. Cell content: micro-label, then the number (mono 28 px) with its label pill, then 13 px secondary text. The key cell gets a 2 px `#FF4F00` top rule.

### Tables

- Header: Geist Mono 10.5 px, uppercase, +0.06 em, `#5F5E5A`, no wrapping, 1 px `#D6D3CC` rule below.
- Rows: 1 px `#E6E4DF` dividers. Cell padding 10 px vertical, 12 px horizontal. First and last columns sit flush with the card padding.
- Numbers in Geist Mono, right-aligned, each with its trust pill. Row hover `#FAF9F7`.
- Summary rows (unit cost, totals) get a `#D6D3CC` rule above and 500 weight.
- A **recommended column** gets an `#FFF1EA` fill, 1 px `#FF4F00` side rules, a 3 px `#FF4F00` top rule and a "Recommended" accent pill.

### Pills and badges

- 20 px high (18 px small), 8 px horizontal padding (6 px small), fully round. Font 11 px 500 (10.5 px small), sentence case. Leading 6 px dot.
- **Trust labels:** colours as in section 1.
- **Neutral pill:** bg `#EFEDE8`, text `#5F5E5A`, dot `#B9B6AF`. Used for "Example project" and modes.
- **Accent pill:** bg `#FFF1EA`, text `#C43C00`, dot `#FF4F00`. Used for "Chosen" and "Recommended".
- **Status:** Validated uses the measured green, Draft uses the estimate amber.
- **Severity** is text plus an 8 px square: critical/high `#C4321F`, major/medium `#C98A0B`, minor `#B9B6AF`.
- **Layer tags** (Lovable, Core…): 18 px high, 1 px `#D6D3CC` border, 3 px radius, 10 px uppercase at +0.08 em, `#5F5E5A`. The Core tag is accent-tinted.

### Inputs

White background, 1 px `#D6D3CC` border, 4 px radius, 7 × 10 px padding, 14/20 text, placeholder `#8A8883`. Hover border `#B9B6AF`. Focus: border `#111111` plus a 3 px ring of `rgba(17,17,17,.06)`.

### Progress

- **Stepper:** 13 segments, 2 px high with 4 px gaps. Validated `#111111`, draft `#C98A0B`, not started `#D6D3CC`, current `#FF4F00`. A mono 10.5 px stage number sits under each segment.
- **Progress bars:** 3 px, fully round, track `#EFEDE8`, fill `#FF4F00` (or ink for scores).

### Graph-paper texture

Placed behind product stills and the 3D view only, never behind text.
- Cell 24 × 24 px, centred.
- Lines 1 px `#111111` at **4.5 % opacity** (`rgba(17,17,17,.045)`) on `#F7F6F3`.
- Radial fade: an elliptical mask centred on the product, opaque to 35 %, transparent at 72 %. So the grid dissolves before the edges and never shows a box.
- The product still blends into the paper with "darken" blending and brightness 1.03, which removes the render's own background.

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
- **Wordmark:** a 16 px orange `#FF4F00` rounded square (2 px radius) with an 8 px ink `#111111` square inside, followed by "PhysicalLovableX" in Inter Tight 14 px 600.

---

## 7. Motion

150–200 ms, `cubic-bezier(.2,.7,.2,1)`, on colour, width or opacity only. The 3D model fades in over 400 ms and turns at 12°/s. No bounce, no confetti, no staggered section entrances. Respect `prefers-reduced-motion`.

---

## 8. Do / don't

**Do**
- Show every number with its trust label. The "Fictional — demo data" and "Cached example" labels stay visible and styled, never hidden.
- Let one thing per screen be bold: the product still, or the key number with its orange rule.
- Use condensed uppercase display type only for titles. Everything else is Inter Tight.
- Use Geist Mono uppercase micro-labels for section headers and table heads.
- Use hairlines and tables before boxes, and keep content left-aligned.
- Use plain, specific copy: "about a minute (measured on 10 test prompts)", not "blazing fast".

**Don't**
- Add logo walls, testimonials, pricing tables, "Backed by" pills or social-proof counters.
- Add gradients, glow, glassmorphism, drop-shadow cards, dashed coloured borders, or large radii everywhere.
- Use orange for body text or large fills. Use `#C43C00` when orange must be text.
- Use violet for anything that is not fictional data, or green, blue or amber outside the trust labels, status and severity.
- Add a dark theme. The design is light only, made for screen share.
