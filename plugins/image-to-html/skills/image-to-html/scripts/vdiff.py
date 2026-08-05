#!/usr/bin/env python3
"""Config-aware orchestrator: render a candidate HTML and gate it against a mockup.

All per-project values — mockup path, device scale, ignore masks, thresholds,
named regions — live in a project profile (JSON), NOT in this skill. The engine
ships generic; the profile carries the project. Config resolution order:

    --config PATH  >  $VDIFF_CONFIG  >  ./.visual-diff.config.json
                   >  ./visual-diff.config.json  >  built-in generic defaults

Usage:
    vdiff.py CANDIDATE.html [OUTDIR=out] [--config PATH] [--mockup PNG]
             [--color] [--measure]

Exit code: 0 if the render PASSes the configured gate, 1 if it FAILs (so it can
be used directly in CI). Read OUTDIR/report.json and the highlight PNGs for the
worst-first breakdown.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULTS = {
    "mockup": None,
    "viewport": {"cssW": 1440, "cssH": 900, "scale": 2},
    "ignore": [],
    "thresholds": {"minSsim": 0.92, "maxRmse": 12.0, "cellSsim": 0.80,
                   "maxCellFail": 0, "grid": 16},
    "regions": {},
    "textBoxes": {},
}


def deep_merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(explicit):
    if explicit:
        candidates = [explicit]
    elif os.environ.get("VDIFF_CONFIG"):
        candidates = [os.environ["VDIFF_CONFIG"]]
    else:
        candidates = [".visual-diff.config.json", "visual-diff.config.json"]
    for c in candidates:
        if c and os.path.isfile(c):
            with open(c) as f:
                return deep_merge(DEFAULTS, json.load(f)), c
    return dict(DEFAULTS), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate")
    ap.add_argument("outdir", nargs="?", default="out")
    ap.add_argument("--config")
    ap.add_argument("--mockup", help="override the config's mockup path")
    ap.add_argument("--color", action="store_true",
                    help="also run colorsweep (uses config.regions for named rows)")
    ap.add_argument("--measure", action="store_true",
                    help="also run measure on config.textBoxes")
    args = ap.parse_args()

    cfg, cfg_path = load_config(args.config)
    mockup = args.mockup or cfg.get("mockup")
    if not mockup:
        sys.exit("no mockup: set 'mockup' in the config or pass --mockup")
    if not os.path.isfile(mockup):
        sys.exit(f"mockup not found: {mockup}")

    from PIL import Image
    mw, mh = Image.open(mockup).size
    scale = cfg["viewport"].get("scale", 2) or 1
    cw, ch = mw // scale, mh // scale

    os.makedirs(args.outdir, exist_ok=True)
    cand_png = os.path.join(args.outdir, "candidate.png")
    print(f"config: {cfg_path or '(built-in generic defaults)'}   "
          f"mockup {mw}x{mh}  scale {scale}  -> render {cw}x{ch}")

    # 1) render the candidate at the mockup's geometry
    subprocess.run(["bash", os.path.join(HERE, "render.sh"),
                    args.candidate, cand_png, str(cw), str(ch), str(scale)],
                   check=True)

    # 2) compare (writes report.json + highlight PNGs; always exits 0 itself)
    th = cfg["thresholds"]
    cmp_cmd = [sys.executable, os.path.join(HERE, "compare.py"),
               "--ref", mockup, "--cand", cand_png, "--out", args.outdir,
               "--grid", str(th.get("grid", 16)),
               "--min-ssim", str(th.get("minSsim", 0.92)),
               "--max-rmse", str(th.get("maxRmse", 12.0)),
               "--cell-ssim", str(th.get("cellSsim", 0.80)),
               "--max-cell-fail", str(th.get("maxCellFail", 0))]
    for rect in cfg.get("ignore", []):
        cmp_cmd += ["--ignore", ",".join(str(int(v)) for v in rect)]
    subprocess.run(cmp_cmd, check=True)

    # 3) optional colour/tint sweep
    if args.color:
        regions = cfg.get("regions") or {}
        extra = []
        if regions:
            rpath = os.path.join(args.outdir, "_regions.json")
            with open(rpath, "w") as f:
                json.dump(regions, f)
            extra = [rpath]
        subprocess.run([sys.executable, os.path.join(HERE, "colorsweep.py"),
                        mockup, cand_png] + extra, check=False)

    # 4) optional glyph measurement
    if args.measure:
        boxes = cfg.get("textBoxes") or {}
        if boxes:
            bpath = os.path.join(args.outdir, "_textboxes.json")
            with open(bpath, "w") as f:
                json.dump(boxes, f)
            subprocess.run([sys.executable, os.path.join(HERE, "measure.py"),
                            mockup, bpath], check=False)
        else:
            print("--measure given but config.textBoxes is empty; skipping")

    # gate on the report
    report = {}
    rp = os.path.join(args.outdir, "report.json")
    if os.path.isfile(rp):
        with open(rp) as f:
            report = json.load(f)
    sys.exit(0 if report.get("PASS") else 1)


if __name__ == "__main__":
    main()
