#!/usr/bin/env python3
"""Scaffold a starter .visual-diff.config.json from a mockup image.

Reads the mockup's real pixel dimensions and writes a config with correct
geometry (assuming a 2x export by default), sensible generic thresholds, and
empty regions/textBoxes stubs to fill in by inspecting the mockup.

Usage: init_config.py MOCKUP.png [OUT=.visual-diff.config.json]
                       [--scale N] [--force]
"""
import argparse, json, os, sys
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("mockup")
ap.add_argument("out", nargs="?", default=".visual-diff.config.json")
ap.add_argument("--scale", type=int, default=2,
                help="device scale the mockup was exported at (default 2)")
ap.add_argument("--force", action="store_true")
args = ap.parse_args()

if not os.path.isfile(args.mockup):
    sys.exit(f"mockup not found: {args.mockup}")
if os.path.exists(args.out) and not args.force:
    sys.exit(f"{args.out} already exists; pass --force to overwrite")

w, h = Image.open(args.mockup).size
cfg = {
    "mockup": args.mockup,
    "viewport": {"cssW": w // args.scale, "cssH": h // args.scale, "scale": args.scale},
    "ignore": [],
    "thresholds": {"minSsim": 0.92, "maxRmse": 12.0, "cellSsim": 0.80,
                   "maxCellFail": 0, "grid": 16},
    "regions": {},
    "textBoxes": {},
}
with open(args.out, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")

print(f"wrote {args.out}  ({w}x{h} mockup, scale {args.scale} "
      f"-> viewport {w // args.scale}x{h // args.scale})")
print("next:")
print("  - add 'ignore' masks [[x0,y0,x1,y1]] for cursors/dynamic artefacts in the mockup")
print("  - add named 'regions' {name:[x0,y0,x1,y1]} (mockup px) for --color sweeps")
print("  - add 'textBoxes' {name:[x0,y0,x1,y1]} for --measure glyph sizing")
