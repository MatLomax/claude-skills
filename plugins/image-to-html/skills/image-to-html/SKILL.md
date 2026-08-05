---
name: image-to-html
description: >-
  Reconstruct an HTML page from a mockup image and objectively gate the render
  against it — numbers and highlight PNGs, not eyeballing. Per-region SSIM, edge-XOR
  border detection, colour/tint sweeps, and glyph measurement. Explicit-invoke only
  (/image-to-html). Use when rebuilding a page from a screenshot/mockup, or checking a
  render matches a design. NOT for: pixel-diffing two arbitrary images, OCR, or design
  critique.
disable-model-invocation: true
---

# image-to-html

Rebuild an HTML page from a reference mockup, then prove the render matches with
**objective measurements** instead of a subjective glance. Global similarity
scores lie — a render with a transparent card, wrong-size icon, and a stray
border still scored SSIM 0.99 in testing. This harness gates on **per-region**
failures and **edge** deltas, which localise the exact defects.

The engine is generic. Everything project-specific — mockup path, device scale,
ignore masks, thresholds, named regions — lives in a **project profile** file,
not in this skill.

## Setup (once per project)

```bash
cd <this skill's scripts dir>          # or copy scripts alongside your work
python3 -m venv .venv
.venv/bin/pip install opencv-python-headless scikit-image pillow numpy
```

Rendering uses a cached Playwright `chrome-headless-shell` (no Node). It is
found automatically under `~/.cache/ms-playwright`; override with
`CHROME_HEADLESS_SHELL=/path/to/chrome-headless-shell`. Run the Python scripts
with the venv interpreter (`.venv/bin/python`).

## The project profile

Resolved by `vdiff.py` in this order:
`--config PATH` → `$VDIFF_CONFIG` → `./.visual-diff.config.json` →
`./visual-diff.config.json` → built-in generic defaults.

Scaffold one from a mockup (reads its real dimensions):

```bash
.venv/bin/python scripts/init_config.py path/to/mockup.png
# -> writes .visual-diff.config.json with correct geometry + empty stubs
```

Schema and a filled example are in `assets/`. Fields: `mockup`, `viewport`
(`cssW`/`cssH`/`scale` — candidate render geometry is `mockup_px / scale`),
`ignore` (mask rects), `thresholds`, `regions` (for `--color`), `textBoxes`
(for `--measure`).

### Defining regions and masks (agent-guided — this is the visual part)

`init_config.py` gets geometry right automatically, but `ignore`/`regions`/
`textBoxes` need judgement — look at the mockup and reason about coordinates
(all in **mockup pixels**, i.e. the 2x space if scale is 2):

- **`ignore`** — rectangles over anything that legitimately differs run-to-run:
  a text cursor in the screenshot, a timestamp, a locally-unavailable webfont's
  text. Masked before comparison so they don't spam the gate.
- **`regions`** — a handful of named boxes over meaningful surfaces (a card
  interior, the header band, a footer). The `--color` sweep reports per-region
  RGB and warmth (R−B) deltas, catching tint errors a luminance diff hides.
- **`textBoxes`** — tight boxes around single lines of text. `--measure`
  reports the glyph height in px, so font sizes can be matched objectively.

## Workflow

1. **Init** the profile from the mockup (above); fill in masks/regions.
2. **Build** `candidate.html` — your reconstruction of the page.
3. **Gate:**
   ```bash
   .venv/bin/python scripts/vdiff.py candidate.html out/
   #   add --color to also run the tint sweep, --measure for glyph sizing
   ```
   `vdiff.py` renders the candidate at the mockup's geometry, compares, writes
   `out/report.json` + highlight PNGs, and exits 0 on PASS / 1 on FAIL.
4. **Read the artifacts** (below), fix the worst regions, repeat.

## Reading the gate

Trust these over the global SSIM number:

- **`out/worst_cells.png`** — candidate with the worst regions boxed + scored.
  Any card/field/label region below ~0.80 SSIM is a real defect.
- **`report.json` → `worst_cells[].lum_delta`** — strongly positive in a card
  region ⇒ **missing background** (candidate is darker/emptier than the mockup).
- **`out/edge_xor.png`** — **green** = edges the mockup has that the candidate is
  missing; **red** = extra edges/borders the candidate invented; grey = matched.
  High `edges.extra_border_px` ⇒ stray borders; high `missing_border_pct` ⇒ an
  outline the mockup has is absent.
- **`out/diff_heatmap.png`** / **`out/ssim_diff.png`** — per-pixel and structural
  difference maps for a fast visual scan.

## Deep-dive tools (optional)

- **`scripts/colorsweep.py REF CAND [regions.json] [grid]`** — per-region and
  per-cell RGB/tint deltas. `vdiff.py --color` runs it from `config.regions`.
- **`scripts/measure.py IMAGE boxes.json [thr] [out.json]`** — tight glyph
  height/width for named text boxes. `vdiff.py --measure` runs it from
  `config.textBoxes`.
- **`scripts/render.sh in.html out.png [cssW cssH scale]`** — standalone render.

## Limits (honest)

- Measures **pixels**, not intent — it flags shape/colour/position drift, not
  wrong copy.
- Local fonts must match the mockup's or text regions flag as noise: install the
  webfont, `ignore` the text areas, or raise `cellSsim` tolerance there.
- Anti-aliasing/sub-pixel shifts add low-level noise — that's why the gate is
  per-region SSIM, not exact pixel equality.
- A human still confirms the final result, but on **boxed, ranked defects**, not
  a raw page.
