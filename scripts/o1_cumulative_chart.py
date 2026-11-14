#!/usr/bin/env python3
"""o1_cumulative_chart.py — cumulative effect of the O1 optimization loop
(R5-12 ladder, supersedes the 2-state 2026-11-12 chart whose records were
lost with out/).

Four ze_json states measured BACK-TO-BACK in ONE dev_device window
(3 interleaved passes x 4 states x 6 corpora, harness `ze-parser` /
`wasm-parse-full`; median-of-6 per state per corpus — a pass-1
synthetic_1mb interference event is diluted by the extra passes):

  S0 d9e25ac  pre-O1            (the ND-10 vintage state)
  S1 ccdb610  +O1-4 kind mirror (ze_json PR #38)
  S2 a7e9c45  +O1-5 frame decode (ze_json PR #39)
  S3 ae209f0  +O1-7 thin step   (ze_json PR #40, ABI v4, wasm c5b42b7d)

V8 `JSON.parse` body-parse from the SAME window (2 runs, median) is drawn
as a reference line. Panel 2 shows the cumulative multiplier per corpus
(S0 = 1.0x). In-window ratios are the evidence; absolute cross-window
comparisons would carry ~11% machine drift (observed between the O1-5 and
O1-7 sandwich windows — this ladder exists precisely to remove that).

Sources (validated schema-v1 records, archived committed):
  reports/o1-loop/<run_id>-*_record.json  (run_ids pinned below)
  log: out/raw/o1_ladder_log.json + o1_ladder2_log.json (swap integrity)

Outputs: out/charts/o1-cumulative.{png,svg} (gitignored masters),
out/charts/data/o1-cumulative.csv; archive SVG belongs in
reports/charts/ (committed provenance, P5-5 pattern).

Usage: python scripts/o1_cumulative_chart.py
"""

from __future__ import annotations

import csv
import json
import os
import statistics
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE_DIR)
ARCHIVE = os.path.join(ROOT, "reports", "o1-loop")
DATA_DIR = os.path.join(ROOT, "out", "charts", "data")

CORPORA = ["synthetic_1k", "synthetic_10k", "synthetic_100k",
           "synthetic_1mb", "saq_payload_v1", "checker_batch"]
MAIN_CORPUS = "saq_payload_v1"

# Pinned run provenance (deterministic; abort when a pinned record absent).
STATES = {
    "S0": ["zuu-20261114012741", "zuu-20261114012816",
           "zuu-20261114012850", "zuu-20261114013402",
           "zuu-20261114013437", "zuu-20261114013511"],
    "S1": ["zuu-20261114012750", "zuu-20261114012824",
           "zuu-20261114012859", "zuu-20261114013411",
           "zuu-20261114013446", "zuu-20261114013520"],
    "S2": ["zuu-20261114012758", "zuu-20261114012833",
           "zuu-20261114012907", "zuu-20261114013420",
           "zuu-20261114013454", "zuu-20261114013528"],
    "S3": ["zuu-20261114012807", "zuu-20261114012842",
           "zuu-20261114012916", "zuu-20261114013428",
           "zuu-20261114013503", "zuu-20261114013537"],
}
V8_RUNS = ["zuu-20261114012733", "zuu-20261114012925"]
REF = "fe877f2"  # run_id suffix of every ze ladder run

STAGE_LABELS = [
    "S0 · pre-O1",
    "S1 · +O1-4",
    "S2 · +O1-5",
    "S3 · +O1-7 (v4)",
]
STAGE_COLORS = ["#90a4ae", "#aed581", "#66bb6a", "#2e7d32"]
RED = "#c62828"
GRAY = "#455a64"


def load_bps(run_id: str) -> dict[str, float]:
    """bytes/s per corpus for one harness record (single-context run)."""
    path = os.path.join(ARCHIVE, f"{run_id}-{REF}_{MAIN_CORPUS}_record.json")
    # records are per-corpus; find the record file for this run_id/corpus
    matches = [f for f in os.listdir(ARCHIVE)
               if f.startswith(run_id) and f.endswith("_record.json")]
    if not matches:
        raise SystemExit(f"pinned ladder record missing: {run_id}")
    out = {}
    for fn in matches:
        with open(os.path.join(ARCHIVE, fn), encoding="utf-8") as fh:
            d = json.load(fh)
        if not str(d.get("run_id", "")).startswith(run_id):
            continue
        corpus = d["corpus"]["name"]
        for res in d["results"]:
            if res.get("status") == "ok":
                out[corpus] = res["metrics"]["bytes_per_second"]
    if not out:
        raise SystemExit(f"no ok results in pinned record {run_id}")
    return out


def main() -> None:
    bps: dict[str, dict[str, float]] = {}
    for state, run_ids in STATES.items():
        per_pass = [load_bps(r) for r in run_ids]
        bps[state] = {c: statistics.median(p[c] for p in per_pass)
                      for c in CORPORA}
    v8: dict[str, float] = {}
    for corpus in CORPORA:
        vals = []
        for rid in V8_RUNS:
            path = os.path.join(
                ARCHIVE, f"{rid}-8c7f2d4_{corpus}_record.json")
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
            for res in d["results"]:
                if res.get("status") == "ok" and "/body-parse/" in res["name"]:
                    vals.append(res["metrics"]["bytes_per_second"])
        v8[corpus] = statistics.median(vals)

    states = list(STATES)
    # ---- panel data ----
    saq = [bps[s][MAIN_CORPUS] / 1e6 for s in states]
    v8_main = v8[MAIN_CORPUS] / 1e6

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(12.8, 5.6), gridspec_kw={"width_ratios": [1, 1.35]})

    # Panel 1 — saq_payload_v1 ladder + V8 reference
    x = range(len(states))
    bars = ax1.bar(x, saq, 0.58, color=STAGE_COLORS,
                   edgecolor="#263238", linewidth=0.6)
    for xi, v in zip(x, saq):
        ax1.annotate(f"{v:.1f}", (xi, v), xytext=(0, 4),
                     textcoords="offset points", ha="center",
                     fontsize=11, fontweight="bold", color="#263238")
    for i in range(1, len(states)):
        gain = (saq[i] / saq[i - 1] - 1) * 100
        ax1.annotate(f"+{gain:.0f}%", ((i - 0.5), max(saq[i - 1], saq[i]) * 1.04),
                     ha="center", fontsize=9.5, color=GREEN if gain > 0 else RED,
                     fontweight="bold")
    ax1.axhline(v8_main, color=RED, ls="--", lw=1.4)
    ax1.annotate(f"V8 JSON.parse {v8_main:.0f} MB/s (referensi, window sama)",
                 (len(states) - 0.55, v8_main), fontsize=8.5, va="bottom",
                 ha="right", color=RED)
    ax1.set_xticks(list(x), labels=STAGE_LABELS, fontsize=8.5)
    ax1.set_ylim(0, max(v8_main, max(saq)) * 1.22)
    ax1.set_ylabel("MB/s (median 6 pasang, satu window)")
    ax1.set_title("saq_payload_v1 — tangga state O1", fontsize=11.5,
                  fontweight="bold")
    ax1.grid(axis="y", alpha=0.3)
    ax1.set_axisbelow(True)
    ax1.spines[["top", "right"]].set_visible(False)

    # Panel 2 — cumulative multiplier per corpus (S0 = 1.0x; the legend
    # carries the final multiplier, no per-line end annotations)
    for corpus in CORPORA:
        ratios = [bps[s][corpus] / bps["S0"][corpus] for s in states]
        ax2.plot(range(len(states)), ratios, marker="o", lw=1.8,
                 label=f"{corpus} ({ratios[-1]:.2f}×)")
    ax2.axhline(1.0, color=GRAY, ls=":", lw=1)
    ax2.set_xticks(range(len(states)), labels=["S0", "S1", "S2", "S3"],
                   fontsize=10)
    ax2.set_xlim(-0.15, len(states) - 1 + 0.25)
    ax2.set_ylabel("multiplier kumulatif vs S0 (pre-O1)")
    ax2.set_title("multiplier kumulatif — 6 korpus", fontsize=11.5,
                  fontweight="bold")
    ax2.grid(alpha=0.3)
    ax2.set_axisbelow(True)
    ax2.legend(fontsize=8, loc="upper left", framealpha=0.9)
    ax2.spines[["top", "right"]].set_visible(False)

    fig.suptitle("Dampak kumulatif loop O1 — ze_json wasm64 full-parse "
                 "(satu window, median 6 pasangan interleaved)",
                 fontsize=13, fontweight="bold", y=0.99)
    fig.text(0.5, 0.935,
             "S0 pre-O1 → S3 v4: seluruh korpus naik monoton "
             "(kumulatif 1,38×–1,52×); gap ke V8 menyempit ~26× → ~18× "
             "(saq_payload_v1).",
             ha="center", fontsize=9.5, color="#37474f")
    fig.text(0.5, 0.012,
             "Ladder satu window 2026-11-14: 3 pasangan interleaved × 4 state × 6 korpus "
             "(ze-parser/wasm-parse-full); swap binding+wasm terverifikasi sha256 per state; "
             "pass-1 synthetic_1mb interference terdilusi median-of-6.\n"
             "In-window ratio = bukti; absolut lintas window membawa drift mesin ~11% "
             "(alasan ladder ini ada). Sumber: record PASS reports/o1-loop/ "
             "(run_id pinned). Regenerasi: python scripts/o1_cumulative_chart.py",
             ha="center", fontsize=7.8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.9))

    os.makedirs(DATA_DIR, exist_ok=True)
    for ext in ("png", "svg"):
        out = os.path.join(ROOT, "out", "charts", f"o1-cumulative.{ext}")
        fig.savefig(out, dpi=300)
        print("wrote", os.path.relpath(out, ROOT))

    csv_path = os.path.join(DATA_DIR, "o1-cumulative.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["corpus", "S0_pre_o1_MBps", "S1_o1_4_MBps",
                    "S2_o1_5_MBps", "S3_o1_7_MBps", "cumulative_S3_vs_S0",
                    "v8_reference_MBps"])
        for corpus in CORPORA:
            row = [bps[s][corpus] / 1e6 for s in states]
            w.writerow([corpus] + [f"{v:.4f}" for v in row]
                       + [f"{row[-1] / row[0]:.4f}", f"{v8[corpus] / 1e6:.4f}"])
    print("wrote", os.path.relpath(csv_path, ROOT))

    print("\n== ladder (median-of-6, MB/s) ==")
    for corpus in CORPORA:
        vals = [bps[s][corpus] / 1e6 for s in states]
        cum = vals[-1] / vals[0]
        print(f"{corpus:<16} " + "  ".join(f"{v:6.2f}" for v in vals)
              + f"   cum {cum:.3f}x   (V8 {v8[corpus] / 1e6:.0f})")


GREEN = "#2e7d32"

if __name__ == "__main__":
    main()
