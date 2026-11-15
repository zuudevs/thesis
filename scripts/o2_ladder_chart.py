#!/usr/bin/env python3
"""o2_ladder_chart.py — cumulative effect of the O2 scanner loop (ND-13/14).

Ladder of the s2-open decomposition across the accepted O2 states, rebuilt
strictly from COMMITTED validated nd9 --probe records (one per state):

  S0  core 0.3.0  pre-O2        (O2-1 sandwich baseline, wasm 8ec2d3cd)
  S1  core 0.3.1  +O2-1         (O2-1 sandwich candidate, wasm 1d8960c9)
  S1' core 0.3.1  window-2 re-baseline (O2-2 sandwich baseline)
  S2  core 0.3.2  +O2-2         (O2-2 sandwich candidate, wasm 9795f2e8)

S1 and S1' are the SAME code measured in two sandwich windows — drawing
both makes the window drift (~11% band, ND-12) visible instead of hidden:
the S1->S2 gain is judged in-window (S1' vs S2), the S0->S1 gain in its
own window. Series = Σmedian per op over the 6 saq documents for the
fused s2-open bound and its two dominant sub-stages (s2b-scan, s2c-match).

Sources (validator PASS, archived committed):
  reports/o2-1/zuu-20261114200912-b699f51-nd9-cost-dev_device.record.json
  reports/o2-1/zuu-20261114201432-1c530d0-nd9-cost-dev_device.record.json
  reports/o2-2/zuu-20261115040553-117e59d-nd9-cost-dev_device.record.json
  reports/o2-2/zuu-20261115034403-26e2bfa-nd9-cost-dev_device.record.json

Outputs (master, gitignored): out/charts/o2-ladder.{png,svg} +
out/charts/data/o2-ladder.csv. Archive copy: reports/charts/o2-ladder.svg
(committed provenance, P5-5 pattern).

Usage: python scripts/o2_ladder_chart.py
"""

from __future__ import annotations

import csv
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "out", "charts", "data")

GREEN = "#2e7d32"
BLUE = "#1565c0"
AMBER = "#f9a825"
GRAY = "#455a64"

# (label, record path relative to root, window id)
STAGES = [
    ("0.3.0\nS0 pre-O2", "reports/o2-1/zuu-20261114200912-b699f51-"
     "nd9-cost-dev_device.record.json", 1),
    ("0.3.1\nS1 +O2-1", "reports/o2-1/zuu-20261114201432-1c530d0-"
     "nd9-cost-dev_device.record.json", 1),
    ("0.3.1\nS1' window-2", "reports/o2-2/zuu-20261115040553-117e59d-"
     "nd9-cost-dev_device.record.json", 2),
    ("0.3.2\nS2 +O2-2", "reports/o2-2/zuu-20261115034403-26e2bfa-"
     "nd9-cost-dev_device.record.json", 2),
]
SERIES = [
    ("s2-open (fused bound)", "s2-open", GREEN),
    ("s2b-scan", "s2b-scan", BLUE),
    ("s2c-match", "s2c-match", AMBER),
]


def stage_sums(rec):
    """Σmedian per stage over the 6 document entries (the harness's Σ)."""
    sums = {}
    for r in rec["results"]:
        stage = r["extras"]["stage"]
        sums[stage] = sums.get(stage, 0.0) + r["extras"]["seconds_median"]
    return {k: v * 1000 for k, v in sums.items()}  # seconds -> ms


def main():
    points = []
    for label, rel, window in STAGES:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            raise SystemExit(f"missing committed record: {rel}")
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
        if rec.get("schema_version") != "1.0.0":
            raise SystemExit(f"unexpected schema in {rel}")
        sums = stage_sums(rec)
        points.append({"label": label, "window": window,
                       "run_id": rec["run_id"], **sums})

    xs = range(len(points))
    fig, ax = plt.subplots(figsize=(10.2, 6.4))
    # label offsets: s2b-scan sits between open (above) and match (above) at
    # every stage — draw its label BELOW the point so it never collides with
    # the s2-open value when the two curves converge (S0, S1).
    OFFSETS = {"s2-open": (0, 7), "s2b-scan": (0, -14), "s2c-match": (0, 7)}
    for name, key, color in SERIES:
        vals = [p[key] for p in points]
        ax.plot(xs, vals, "-o", color=color, lw=2.2, markersize=7,
                label=name)
        for x, v in zip(xs, vals):
            ax.annotate(f"{v:.4f}", (x, v), xytext=OFFSETS[key],
                        textcoords="offset points", ha="center",
                        fontsize=8.2, color=color)

    # window divider + shading: S1->S2 gain is judged in-window
    wx = 1.5
    ax.axvline(wx, color=GRAY, ls=":", lw=1.2)
    ax.annotate("window-1\n(sandwich O2-1)", (0.5, ax.get_ylim()[1] * 0.02),
                ha="center", fontsize=8.5, color=GRAY, annotation_clip=False)
    ax.annotate("window-2\n(sandwich O2-2)", (2.5, ax.get_ylim()[1] * 0.02),
                ha="center", fontsize=8.5, color=GRAY, annotation_clip=False)

    ax.axhline(0, color="#cfd8dc", lw=0.8)
    ax.set_xticks(list(xs), labels=[p["label"] for p in points], fontsize=9.5)
    ax.set_ylabel("Σmedian per op atas 6 dokumen saq (ms)")
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=9, loc="upper right")

    fig.suptitle("Ladder O2 — dekomposisi s2-open jalur count (saq_payload_v1)",
                 fontsize=13, fontweight="bold", y=0.99)
    fig.text(0.5, 0.94,
             "core 0.3.0 → 0.3.1 (O2-1 interior skip) → 0.3.2 (+O2-2 SWAR) · "
             "wasm 8ec2d3cd → 1d8960c9 → 9795f2e8 · Node 26.13.1 · tree bersih",
             ha="center", fontsize=9.5, color="#37474f")
    fig.text(0.5, 0.012,
             "Sumber: record PASS reports/o2-1/ + reports/o2-2/ (nd9 --probe, 15×4 siklus, warmup 3, tanpa trimming). "
             "Gain dinilai dalam-window: S0→S1 (−51% scan), S1'→S2 (−26% scan).\n"
             "S1 vs S1' = drift antar-window (band ~11%, ND-12). Komposisi pasca-O2: match ~21% dari open "
             "→ kandidat O2 berikutnya = pass pairing.",
             ha="center", fontsize=7.8, color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 0.925))

    os.makedirs(os.path.join(ROOT, "out", "charts"), exist_ok=True)
    for ext in ("png", "svg"):
        out = os.path.join(ROOT, "out", "charts", f"o2-ladder.{ext}")
        fig.savefig(out, dpi=200)
        print("wrote", os.path.relpath(out, ROOT))

    os.makedirs(DATA_DIR, exist_ok=True)
    csv_path = os.path.join(DATA_DIR, "o2-ladder.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(points[0].keys()))
        w.writeheader()
        for p in points:
            w.writerow({k: (round(v, 6) if isinstance(v, float) else v)
                        for k, v in p.items()})
    print("wrote", os.path.relpath(csv_path, ROOT))


if __name__ == "__main__":
    sys.exit(main())
