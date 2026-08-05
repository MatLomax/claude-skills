#!/usr/bin/env python3
"""Measure the tight glyph bounding box (height/width) of named text regions in
an image, so font sizes can be matched objectively between a mockup and a render.

For each named box [x0,y0,x1,y1] it auto-detects background (median of the box
border), builds an ink mask (|luma-bg| > thr), and reports the tight extent of
the ink. Height is the primary font-size signal. Works for dark-on-light and
light-on-dark (e.g. a button).

Usage: measure.py IMAGE boxes.json [thr=60] [out.json]
  boxes.json = {"name": [x0,y0,x1,y1], ...}
Prints one row per box: name  h  w  ink%  bbox
Writes a JSON map to out.json only if that argument is given.
"""
import sys, json
import numpy as np, cv2

img = cv2.imread(sys.argv[1], cv2.IMREAD_GRAYSCALE)
boxes = json.load(open(sys.argv[2]))
thr = int(sys.argv[3]) if len(sys.argv) > 3 else 60
out_path = sys.argv[4] if len(sys.argv) > 4 else None

out = {}
for name, (x0, y0, x1, y1) in boxes.items():
    crop = img[y0:y1, x0:x1].astype(int)
    if crop.size == 0:
        print(f"{name:18} EMPTY box"); continue
    border = np.concatenate([crop[0], crop[-1], crop[:, 0], crop[:, -1]])
    bg = np.median(border)
    ink = np.abs(crop - bg) > thr
    ys, xs = np.where(ink)
    if len(ys) == 0:
        print(f"{name:18} no ink (bg={bg:.0f})"); out[name] = None; continue
    h = int(ys.max() - ys.min() + 1); w = int(xs.max() - xs.min() + 1)
    pct = 100.0 * ink.mean()
    bb = (x0 + int(xs.min()), y0 + int(ys.min()), x0 + int(xs.max()), y0 + int(ys.max()))
    out[name] = {"h": h, "w": w, "ink_pct": round(pct, 1), "bbox": bb}
    print(f"{name:18} h={h:4d} w={w:5d} ink={pct:5.1f}%  bbox={bb}")

if out_path:
    json.dump(out, open(out_path, "w"))
    print(f"wrote {out_path}")
