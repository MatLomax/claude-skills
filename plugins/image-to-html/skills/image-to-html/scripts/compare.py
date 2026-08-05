#!/usr/bin/env python3
"""
Objective visual comparison of a candidate render against a reference mockup.

Emits NUMBERS (not vibes): global SSIM / RMSE / mismatch%, a worst-first ranked
grid of where the two images differ most, an edge-XOR analysis that specifically
catches missing/extra borders, and a per-cell mean-luminance check that catches
"the card has no background". Also writes highlight PNGs so a human glance lands
on the actual problems instead of the whole page.

Usage:
  python compare.py --ref mockup.png --cand candidate.png --out OUTDIR \
      [--grid 16] [--worst 12] [--edge-lo 80 --edge-hi 160] \
      [--ignore x0,y0,x1,y1 ...]     # rectangles to mask (e.g. mockup cursor)

Exit code 0 always; read the JSON/console report for pass/fail against thresholds.
"""
import argparse, json, os, sys
import numpy as np
import cv2
from skimage.metrics import structural_similarity as ssim


def load_rgb(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        sys.exit(f"cannot read image: {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def apply_ignores(img, ignores, fill=0):
    for (x0, y0, x1, y1) in ignores:
        img[y0:y1, x0:x1] = fill
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--cand", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--grid", type=int, default=16, help="NxN region grid")
    ap.add_argument("--worst", type=int, default=12, help="worst cells to list")
    ap.add_argument("--edge-lo", type=int, default=80)
    ap.add_argument("--edge-hi", type=int, default=160)
    ap.add_argument("--ignore", action="append", default=[],
                    help="x0,y0,x1,y1 rectangle(s) to mask before comparing")
    # pass thresholds (objective gate)
    ap.add_argument("--min-ssim", type=float, default=0.92)
    ap.add_argument("--max-rmse", type=float, default=12.0)   # 0..255
    ap.add_argument("--max-cell-fail", type=int, default=0,
                    help="allowed cells below --cell-ssim")
    ap.add_argument("--cell-ssim", type=float, default=0.80)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    ref = load_rgb(args.ref)
    cand = load_rgb(args.cand)

    # normalise size: candidate is resized to the reference geometry
    H, W = ref.shape[:2]
    if cand.shape[:2] != (H, W):
        cand = cv2.resize(cand, (W, H), interpolation=cv2.INTER_AREA)

    ignores = []
    for s in args.ignore:
        x0, y0, x1, y1 = (int(v) for v in s.split(","))
        ignores.append((x0, y0, x1, y1))
    ref = apply_ignores(ref.copy(), ignores)
    cand = apply_ignores(cand.copy(), ignores)

    ref_g = cv2.cvtColor(ref, cv2.COLOR_RGB2GRAY)
    cand_g = cv2.cvtColor(cand, cv2.COLOR_RGB2GRAY)

    # ---- global metrics ----
    ssim_full, ssim_map = ssim(ref_g, cand_g, full=True)
    diff = np.abs(ref.astype(np.int16) - cand.astype(np.int16)).astype(np.uint8)
    per_px = diff.max(axis=2)                       # worst channel per pixel
    rmse = float(np.sqrt(np.mean((ref.astype(np.float32) - cand.astype(np.float32)) ** 2)))
    mae = float(np.mean(per_px))
    mismatch_pct = float((per_px > 25).mean() * 100)  # >25/255 = visibly different

    # ---- difference heatmap ----
    heat = cv2.applyColorMap(per_px, cv2.COLORMAP_TURBO)
    cv2.imwrite(os.path.join(args.out, "diff_heatmap.png"), heat)

    # ---- SSIM map (dark = structurally different) ----
    ssim_vis = ((1 - ssim_map) * 255).clip(0, 255).astype(np.uint8)
    cv2.imwrite(os.path.join(args.out, "ssim_diff.png"),
                cv2.applyColorMap(ssim_vis, cv2.COLORMAP_MAGMA))

    # ---- edge XOR: catches missing / extra borders ----
    e_ref = cv2.Canny(ref_g, args.edge_lo, args.edge_hi)
    e_cand = cv2.Canny(cand_g, args.edge_lo, args.edge_hi)
    edge_img = np.zeros((H, W, 3), np.uint8)
    edge_img[(e_ref > 0) & (e_cand == 0)] = (0, 200, 0)     # green = in mockup, MISSING in candidate
    edge_img[(e_cand > 0) & (e_ref == 0)] = (0, 0, 255)     # red   = EXTRA in candidate (stray borders)
    edge_img[(e_ref > 0) & (e_cand > 0)] = (90, 90, 90)     # grey  = matched edges
    cv2.imwrite(os.path.join(args.out, "edge_xor.png"),
                cv2.cvtColor(edge_img, cv2.COLOR_RGB2BGR))
    missing_edge_pct = float(((e_ref > 0) & (e_cand == 0)).sum() / max(1, (e_ref > 0).sum()) * 100)
    extra_edge_px = int(((e_cand > 0) & (e_ref == 0)).sum())

    # ---- per-region grid, worst-first ----
    g = args.grid
    cells = []
    for gy in range(g):
        for gx in range(g):
            y0, y1 = gy * H // g, (gy + 1) * H // g
            x0, x1 = gx * W // g, (gx + 1) * W // g
            r = ref_g[y0:y1, x0:x1]
            c = cand_g[y0:y1, x0:x1]
            if r.size == 0:
                continue
            win = min(7, r.shape[0] - (r.shape[0] + 1) % 2, r.shape[1] - (r.shape[1] + 1) % 2)
            cs = ssim(r, c, win_size=win if win >= 3 else 3) if min(r.shape) >= 3 else 1.0
            cr = float(np.sqrt(np.mean((r.astype(np.float32) - c.astype(np.float32)) ** 2)))
            lum = float(ref[y0:y1, x0:x1].mean() - cand[y0:y1, x0:x1].mean())  # +ve => candidate darker/missing-white
            cells.append({"cell": [gx, gy], "px": [x0, y0, x1, y1],
                          "ssim": round(float(cs), 3), "rmse": round(cr, 1),
                          "lum_delta": round(lum, 1)})
    cells.sort(key=lambda d: d["ssim"])
    worst = cells[:args.worst]
    n_fail = sum(1 for c in cells if c["ssim"] < args.cell_ssim)

    # annotate worst cells on a copy of the candidate
    annot = cv2.cvtColor(cand, cv2.COLOR_RGB2BGR).copy()
    for c in worst:
        x0, y0, x1, y1 = c["px"]
        cv2.rectangle(annot, (x0, y0), (x1, y1), (0, 0, 255), 3)
        cv2.putText(annot, f'{c["ssim"]:.2f}', (x0 + 4, y0 + 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.imwrite(os.path.join(args.out, "worst_cells.png"), annot)

    passed = (ssim_full >= args.min_ssim and rmse <= args.max_rmse
              and n_fail <= args.max_cell_fail)

    report = {
        "geometry": {"w": W, "h": H, "resized_candidate": cand.shape[:2] != (H, W)},
        "global": {"ssim": round(float(ssim_full), 4), "rmse": round(rmse, 2),
                   "mae": round(mae, 2), "mismatch_pct": round(mismatch_pct, 2)},
        "edges": {"missing_border_pct": round(missing_edge_pct, 1),
                  "extra_border_px": extra_edge_px},
        "grid": {"n": g, "cells_below_%.2f" % args.cell_ssim: n_fail},
        "thresholds": {"min_ssim": args.min_ssim, "max_rmse": args.max_rmse,
                       "cell_ssim": args.cell_ssim, "max_cell_fail": args.max_cell_fail},
        "PASS": bool(passed),
        "worst_cells": worst,
        "artifacts": ["diff_heatmap.png", "ssim_diff.png", "edge_xor.png", "worst_cells.png"],
    }
    with open(os.path.join(args.out, "report.json"), "w") as f:
        json.dump(report, f, indent=2)

    # console summary
    print(f"{'PASS' if passed else 'FAIL':4}  ssim={ssim_full:.4f} (>= {args.min_ssim})"
          f"  rmse={rmse:.2f} (<= {args.max_rmse})  mismatch={mismatch_pct:.2f}%")
    print(f"      edges: missing_border={missing_edge_pct:.1f}%  extra_border_px={extra_edge_px}")
    print(f"      grid {g}x{g}: {n_fail} cells below ssim {args.cell_ssim}")
    print("      worst regions (px x0,y0,x1,y1  ssim  rmse  lumΔ):")
    for c in worst[:args.worst]:
        print(f"        {tuple(c['px'])!s:26} ssim={c['ssim']:.2f} rmse={c['rmse']:.1f} lumΔ={c['lum_delta']:+.1f}")
    print(f"      artifacts -> {args.out}")


if __name__ == "__main__":
    main()
