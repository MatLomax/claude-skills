#!/usr/bin/env python3
"""Per-region and per-cell RGB colour comparison between a mockup and a candidate.
Reports channel-wise deltas (ref - cand) so hue/tint errors that a luminance-only
diff hides become visible. Positive R-B => the mockup is warmer than the candidate.

Usage:
  colorsweep.py REF.png CAND.png [regions.json] [grid=16]

regions.json (optional): {"name": [x0,y0,x1,y1], ...} in the mockup's pixel space.
Without it, only the coarse grid channel-delta ranking is printed (no project
knowledge is baked in)."""
import sys, json
import numpy as np
from PIL import Image

ref = np.asarray(Image.open(sys.argv[1]).convert('RGB'), dtype=np.float64)
cand = np.asarray(Image.open(sys.argv[2]).convert('RGB'), dtype=np.float64)
H, W, _ = ref.shape
if cand.shape != ref.shape:
    cand = np.asarray(Image.open(sys.argv[2]).convert('RGB').resize((W, H)), dtype=np.float64)


def stats(a):
    return a.reshape(-1, 3).mean(0)


def warmth(rgb):
    return rgb[0] - rgb[2]  # R - B


regions = {}
if len(sys.argv) > 3 and sys.argv[3] not in ("-", ""):
    regions = json.load(open(sys.argv[3]))

if regions:
    print(f"{'region':<28}{'ref RGB':>20}{'cand RGB':>20}{'Δ(r-c)':>18}{'warmΔ':>9}")
    print("-" * 97)
    for name, (x0, y0, x1, y1) in regions.items():
        r = stats(ref[y0:y1, x0:x1]); c = stats(cand[y0:y1, x0:x1])
        d = r - c
        wr, wc = warmth(r), warmth(c)
        print(f"{name:<28}{str(r.round(1)):>20}{str(c.round(1)):>20}"
              f"{str(d.round(1)):>18}{wr-wc:>+9.1f}")

# ---- coarse grid channel-delta ranking: where is colour most wrong ----
G = int(sys.argv[4]) if len(sys.argv) > 4 else 16
ch, cw = H // G, W // G
cells = []
for gy in range(G):
    for gx in range(G):
        rb = ref[gy*ch:(gy+1)*ch, gx*cw:(gx+1)*cw].reshape(-1, 3).mean(0)
        cb = cand[gy*ch:(gy+1)*ch, gx*cw:(gx+1)*cw].reshape(-1, 3).mean(0)
        d = rb - cb
        cells.append((np.abs(d).sum(), gx, gy, rb, cb, d, warmth(rb)-warmth(cb)))
cells.sort(reverse=True)
print(f"\nTop colour-delta cells (grid {G}x{G}, cell {cw}x{ch}px):")
print(f"{'cell':<10}{'px (x,y)':<16}{'ref':>18}{'cand':>18}{'Δ':>16}{'warmΔ':>8}")
for s, gx, gy, rb, cb, d, wd in cells[:14]:
    print(f"({gx:2d},{gy:2d})   {str((gx*cw, gy*ch)):<16}{str(rb.round(0)):>18}"
          f"{str(cb.round(0)):>18}{str(d.round(0)):>16}{wd:>+8.1f}")
