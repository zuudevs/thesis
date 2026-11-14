#!/usr/bin/env python3
"""nd6_summary_chart.py — simplified ND-6 summary figures (PLANS P8-1).

Thesis-facing "win/loss" figures rebuilt strictly from VALIDATED measurement
records (schema v1, reports/nd6/**, validator PASS upstream):

1. nd6-summary-map — heatmap of in-situ speedup (median V8 / median ze_json)
   per workload per site. Workloads: ND-6 phase A (full materialization),
   phase B (L2 project), phase C per store (L1 traversal), phase D
   (mongo-cache acceptance path + file-store fallback). Green = ze_json
   wins (>1x), red = ze_json behind (<1x); acceptance target 1.5x is
   called out in the caption.
2. nd6-acceptance — phase D production path (warm mongo cache) speedup for
   the accepted dev runs + the server run, with the 1.5x target line and
   per-run p95 markers.

Design (simplification mandate, 2026-11-13):
- one figure tells the story; no log axes, no hatching, values on cells;
- fairness gate reused from nd6_charts.py (same run_id pair, same corpus
  sha256, both results status=ok) — every charted pair is in-situ;
- phase D (dev) uses the ACCEPTED post-cache-bytes runs (root bbee7bf,
  saq-report 8c7f2d4) — the superseded pre-cache run 0dcb418 is NOT charted;
- run provenance pinned below (fail loudly when a pinned record is missing)
  so the figure stays deterministic and reviewable;
- data vintage labeled explicitly (dev = Node 24 era; server = Node 26,
  root git dirty = exploratory). Regenerate after the ND-10 fresh run.

Outputs (master, gitignored): out/charts/nd6-summary-map.{png,svg},
out/charts/nd6-acceptance.{png,svg} + out/charts/data/*.csv.
Archive copies belong in reports/charts/ (committed provenance, P5-5).

Usage: python scripts/analyze_measurement/nd6_summary_chart.py
"""

from __future__ import annotations

import csv
import math
import os
import statistics
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib import colormaps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import nd6_charts as base  # noqa: E402  (reuses loader + fairness gate)

ROOT = base.ROOT
DATA_DIR = base.DATA_DIR

DOC_ORDER = base.DOC_ORDER

GREEN = "#2e7d32"
AMBER = "#f9a825"
RED = "#c62828"
GRAY = "#455a64"

# ---------------------------------------------------------------------------
# Pinned run provenance (deterministic; abort when a pinned record is absent)
# ---------------------------------------------------------------------------
# Two vintages, selected with `--vintage=nd6|nd10` (default nd10):
#
# nd6 (HISTORICAL, 2026-11-12/13): dev A/B/C = root 0dcb418, acceptance D =
#   bbee7bf main 064628 (2.85x) + confirm 064642 (3.00x); server = 714cbb9
#   batch (root dirty = exploratory). Vintage runtime MIXED (dev Node 24,
#   server Node 26) — superseded by ND-10 for the runtime-controlled claim.
#
# nd10 (FRESH, PLANS P8-3, 2026-11-13): ND-10 E1+E2 executed from CLEAN
#   trees on both sites, root 5a90545, ze_json d9e25ac, saq-report 8c7f2d4,
#   Node 26.13.1 (V8 14.6.202.34-node.40) IDENTICAL both sites, wasm
#   35b7f773... byte-identical (sidecar artifact.wasm_sha256), corpus
#   saq_payload_v1 sha256 9f826c8a... identical. D run + confirm run per
#   site. E1 (dev Node24-era -> Node26) vs old dev records is CONFOUNDED
#   (wasm 7e26044f-era -> 35b7f773; era sidecars lost) — labeled in report.
RUNS_ND6 = {
    ("A", "dev_device"): "zuu-20261112063944-0dcb418",
    ("B", "dev_device"): "zuu-20261112063949-0dcb418",
    ("C", "dev_device"): "zuu-20261112063955-0dcb418",
    ("D", "dev_device"): "zuu-20261112064628-bbee7bf",
    ("A", "saq_server"): "server-lanjut-20261113004447-714cbb9",
    ("B", "saq_server"): "server-lanjut-20261113004501-714cbb9",
    ("C", "saq_server"): "server-lanjut-20261113004510-714cbb9",
    ("D", "saq_server"): "server-lanjut-20261113004520-714cbb9",
}
CONFIRM_ND6 = ["zuu-20261112064642-bbee7bf"]  # dev only
RUNS_ND10 = {
    ("A", "dev_device"): "zuu-20261113173228-5a90545",
    ("B", "dev_device"): "zuu-20261113173230-5a90545",
    ("C", "dev_device"): "zuu-20261113173232-5a90545",
    ("D", "dev_device"): "zuu-20261113173306-5a90545",
    ("A", "saq_server"): "server-lanjut-20261113174303-5a90545",
    ("B", "saq_server"): "server-lanjut-20261113174305-5a90545",
    ("C", "saq_server"): "server-lanjut-20261113174306-5a90545",
    ("D", "saq_server"): "server-lanjut-20261113174348-5a90545",
}
CONFIRM_ND10 = [
    "zuu-20261113173308-5a90545",            # dev confirm
    "server-lanjut-20261113174349-5a90545",  # server confirm
]
# post-o1 (ND-12, 2026-11-14): fresh matrix AFTER the accepted O1 loop —
# root 7fb2ae4, ze_json fe877f2 (ABI v4), wasm c5b42b7d byte-identical both
# sites, Node 26.13.1, clean trees (dev .vscode owner edit stashed during
# the run, popped after; server .vscode stash from ND-10 still held).
RUNS_POST_O1 = {
    ("A", "dev_device"): "zuu-20261114022724-7fb2ae4",
    ("B", "dev_device"): "zuu-20261114022727-7fb2ae4",
    ("C", "dev_device"): "zuu-20261114022730-7fb2ae4",
    ("D", "dev_device"): "zuu-20261114022954-7fb2ae4",
    ("A", "saq_server"): "server-lanjut-20261114023810-7fb2ae4",
    ("B", "saq_server"): "server-lanjut-20261114023812-7fb2ae4",
    ("C", "saq_server"): "server-lanjut-20261114023813-7fb2ae4",
    ("D", "saq_server"): "server-lanjut-20261114024229-7fb2ae4",
}
CONFIRM_POST_O1 = [
    "zuu-20261114022956-7fb2ae4",            # dev confirm
    "server-lanjut-20261114024230-7fb2ae4",  # server confirm
]

VINTAGE = "post-o1"
for _a in sys.argv[1:]:
    if _a.startswith("--vintage="):
        VINTAGE = _a.split("=", 1)[1]
if VINTAGE not in ("nd6", "nd10", "post-o1"):
    raise SystemExit("vintage must be nd6, nd10 or post-o1")

_RUNS_BY_VINTAGE = {"nd6": RUNS_ND6, "nd10": RUNS_ND10, "post-o1": RUNS_POST_O1}
_CONFIRMS_BY_VINTAGE = {
    "nd6": CONFIRM_ND6, "nd10": CONFIRM_ND10, "post-o1": CONFIRM_POST_O1}
RUNS = _RUNS_BY_VINTAGE[VINTAGE]
CONFIRM_RUNS = _CONFIRMS_BY_VINTAGE[VINTAGE]
PREFIX = VINTAGE  # output filename prefix: nd6-* / nd10-* / post-o1-*

PAIRS = {
    "A": ("A/{d}/v8-parse", "A/{d}/ze-parse"),
    "B": ("B/{d}/v8-selective", "B/{d}/ze-project-selective"),
    "C": ("C/{d}/v8-selective", "C/{d}/ze-l1-traversal"),
}

ROWS = [
    {"key": "A-agg", "phase": "A", "kind": "agg",
     "label": "A · materialisasi penuh (median 6 store)"},
    {"key": "B-agg", "phase": "B", "kind": "agg",
     "label": "B · L2 project (median 6 store)"},
    *[{"key": f"C-{d}", "phase": "C", "kind": "store", "doc": d,
       "label": f"C · L1 traversal · {d}"} for d in DOC_ORDER],
    {"key": "D-mongo", "phase": "D", "kind": "d", "path": "mongo-cache",
     "label": "D · mongo-cache (acceptance)"},
    {"key": "D-file", "phase": "D", "kind": "d", "path": "file-store",
     "label": "D · file-store"},
]

SITES = ["dev_device", "saq_server"]


# ---------------------------------------------------------------------------
# data collection (fairness-gated, in-situ pairs only)
# ---------------------------------------------------------------------------

def pick_record(nd6, phase, site):
    prefix = RUNS[(phase, site)]
    matches = [r for r in nd6 if r["site"] == site and r["run_id"].startswith(prefix)]
    if len(matches) != 1:
        raise SystemExit(f"pinned run {prefix} ({phase}/{site}): "
                         f"expected 1 record, found {len(matches)}")
    return matches[0]


def pair_speedups(rec, phase, log_rows, docs):
    b_fmt, c_fmt = PAIRS[phase]
    out = []
    for d in docs:
        b = base.result_by_name(rec, b_fmt.format(d=d))
        c = base.result_by_name(rec, c_fmt.format(d=d))
        if b is None or c is None:
            continue
        if not base.check_pair(rec, b, c, log_rows,
                               f"summary:{phase}:{rec['site']}:{d}"):
            continue
        bp, cp = base.p95_of(b)[0], base.p95_of(c)[0]
        out.append({
            "doc": d,
            "baseline": b,
            "candidate": c,
            "speedup": base.median_of(b)[0] / base.median_of(c)[0],
            "p95": (bp / cp) if bp and cp else None,
        })
    return out


def d_speedups(rec, log_rows):
    out = []
    for path in ("mongo-cache", "file-store"):
        b = base.result_by_name(rec, f"D/D-{path}-v8")
        c = base.result_by_name(rec, f"D/D-{path}-ze")
        if b is None or c is None:
            continue
        if not base.check_pair(rec, b, c, log_rows,
                               f"summary:D:{rec['site']}:{path}"):
            continue
        bp, cp = base.p95_of(b)[0], base.p95_of(c)[0]
        out.append({
            "doc": path,
            "baseline": b,
            "candidate": c,
            "speedup": base.median_of(b)[0] / base.median_of(c)[0],
            "p95": (bp / cp) if bp and cp else None,
        })
    return out


def build_cells(nd6, log_rows):
    cells = {}
    for row in ROWS:
        for site in SITES:
            rec = pick_record(nd6, row["phase"], site)
            if row["kind"] == "d":
                items = [x for x in d_speedups(rec, log_rows)
                         if x["doc"] == row["path"]]
            else:
                docs = DOC_ORDER if row["kind"] == "agg" else [row["doc"]]
                items = pair_speedups(rec, row["phase"], log_rows, docs)
            if not items:
                raise SystemExit(f"no valid in-situ pair for "
                                 f"{row['key']}/{site} in {rec['run_id']}")
            speeds = [x["speedup"] for x in items]
            cell = {"speedup": statistics.median(speeds),
                    "items": items, "rec": rec}
            if row["kind"] == "agg":
                cell["min"], cell["max"] = min(speeds), max(speeds)
            cells[(row["key"], site)] = cell
    return cells


# ---------------------------------------------------------------------------
# figure 1 — win/loss heatmap
# ---------------------------------------------------------------------------

def draw_map(cells):
    if VINTAGE == "nd6":
        site_labels = [
            "dev_device\n2026-11-12 · Node 24.19.0 (V8 13.6)",
            "saq_server\n2026-11-13 · Node 26.13.0 (V8 14.6)\n* git dirty → exploratory",
        ]
    elif VINTAGE == "nd10":
        site_labels = [
            "dev_device\nNode 26.13.1 (V8 14.6) · tree bersih",
            "saq_server\nNode 26.13.1 (V8 14.6) · tree bersih",
        ]
    else:
        site_labels = [
            "dev_device\npasca-O1 (v4) · tree bersih",
            "saq_server\npasca-O1 (v4) · tree bersih",
        ]
    zlog = lambda v: math.log10(v)  # noqa: E731
    z = [[zlog(cells[(r["key"], s)]["speedup"]) for s in SITES] for r in ROWS]
    norm = TwoSlopeNorm(vmin=math.log10(0.03), vcenter=0.0, vmax=math.log10(3.2))
    cmap = colormaps["RdYlGn"]

    fig, ax = plt.subplots(figsize=(10.8, 7.8))
    im = ax.imshow(z, cmap=cmap, norm=norm, aspect="auto")

    for i, row in enumerate(ROWS):
        for j, site in enumerate(SITES):
            cell = cells[(row["key"], site)]
            v = cell["speedup"]
            rgba = cmap(norm(zlog(v)))
            lum = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
            txt = f"{v:.2f}×"
            if row["kind"] == "agg":
                txt += f"\n[{cell['min']:.2f}–{cell['max']:.2f}]"
            ax.text(j, i, txt, ha="center", va="center", fontsize=10.5,
                    fontweight="bold",
                    color="white" if lum < 0.45 else "black")

    ax.set_xticks(range(len(SITES)), labels=site_labels, fontsize=9.5)
    ax.set_yticks(range(len(ROWS)), labels=[r["label"] for r in ROWS],
                  fontsize=9.5)
    ax.set_xticks([x - 0.5 for x in range(1, len(SITES))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(ROWS))], minor=True)
    ax.grid(which="minor", color="white", linewidth=2.2)
    ax.tick_params(which="minor", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    ticks = (0.05, 0.1, 0.25, 0.5, 1.0, 1.5, 3.0)
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02,
                        ticks=[zlog(t) for t in ticks])
    cbar.ax.set_yticklabels([f"{t:g}×" for t in ticks], fontsize=8.5)
    cbar.set_label("speedup (skala log)", fontsize=9)

    if VINTAGE == "nd6":
        title = "ze_json vs baseline V8 — peta speedup ND-6 (in-situ, satu run_id)"
        sub = ("Hijau = ze_json unggul (>1×) · merah = perlu perbaikan (<1×) · "
               "target acceptance ≥ 1,5×")
        foot = ("Speedup = median V8 / median ze dalam pasangan in-situ (fairness gate: satu run_id, korpus sha256 sama, status ok). "
                "A/B = median lintas 6 store (bracket = min–max).\n"
                "Fase D dev = run utama post-cache-bytes (run konfirmasi 3,00× ada di figur acceptance). Sumber: record PASS reports/nd6/. "
                "*Server git dirty = exploratory. Vintage runtime campuran (dev Node 24, server Node 26).")
    elif VINTAGE == "nd10":
        title = "ze_json vs baseline V8 — peta speedup ND-10 (kontrol runtime + mesin)"
        sub = ("Fresh run 2026-11-13 · Node 26.13.1 identik di kedua site · wasm 35b7f773 byte-identik · tree bersih · "
               "hijau = unggul (>1×) · merah = perlu perbaikan (<1×)")
        foot = ("Speedup = median V8 / median ze dalam pasangan in-situ (fairness gate: satu run_id, korpus sha256 sama, status ok). "
                "A/B = median lintas 6 store (bracket = min–max).\n"
                "E1: verdict era Node 24 (2,85×/3,00×) tidak reproducible di Node 26 — komparasi antar-era confounded "
                "(wasm era lama 7e26044f tak terekam sidecarnya). Sumber: record PASS reports/nd10/.")
    else:
        title = "ze_json vs baseline V8 — peta speedup pasca-O1 (ND-12, countermeasure terpasang)"
        sub = ("Fresh run 2026-11-14 · ABI v4 (O1-4+O1-5+O1-7) · wasm c5b42b7d byte-identik · Node 26.13.1 · tree bersih · "
               "hijau = unggul (>1×) · merah = perlu perbaikan (<1×)")
        foot = ("Speedup = median V8 / median ze dalam pasangan in-situ (fairness gate: satu run_id, korpus sha256 sama, status ok). "
                "A/B = median lintas 6 store (bracket = min–max).\n"
                "Window ini mesin lebih lambat absolut (editor berjalan) — rasio in-window yang menjadi bukti. "
                "Fase D file-store warm page-cache (confounder dinyatakan). Sumber: record PASS reports/nd12/.")
    fig.suptitle(title, fontsize=13, fontweight="bold", y=0.99)
    fig.text(0.5, 0.955, sub, ha="center", fontsize=9.5, color="#37474f")
    fig.text(0.5, 0.012, foot, ha="center", fontsize=7.8, color="#555555")
    fig.tight_layout(rect=(0, 0.035, 1, 0.935))
    base.save(fig, f"{PREFIX}-summary-map")


# ---------------------------------------------------------------------------
# figure 2 — phase D acceptance
# ---------------------------------------------------------------------------

def draw_acceptance(nd6, log_rows):
    if VINTAGE == "nd6":
        rt_dev = "2026-11-12 · Node 24.19.0 (V8 13.6)"
        rt_srv = "2026-11-13 · Node 26.13.0 · git dirty (exploratory)"
    elif VINTAGE == "nd10":
        rt_dev = "2026-11-13 · Node 26.13.1 · tree bersih"
        rt_srv = rt_dev
    else:
        rt_dev = "2026-11-14 · pasca-O1 (ABI v4) · tree bersih"
        rt_srv = rt_dev
    if VINTAGE == "nd6":
        spec = [
            (RUNS[("D", "dev_device")], f"dev · run utama\n{rt_dev}"),
            (RUNS[("D", "saq_server")], f"server · run utama\n{rt_srv}"),
            *[(rid, f"dev · konfirmasi\n{rt_dev}") for rid in CONFIRM_RUNS],
        ]
    else:
        spec = [
            (RUNS[("D", "dev_device")], "dev · utama"),
            (RUNS[("D", "saq_server")], "server · utama"),
            *[(rid, "dev · konfirmasi" if rid.startswith("zuu-")
               else "server · konfirmasi") for rid in CONFIRM_RUNS],
        ]
    bars = []
    for prefix, label in spec:
        matches = [r for r in nd6 if r["run_id"].startswith(prefix)]
        if len(matches) != 1:
            raise SystemExit(f"acceptance run {prefix}: expected 1, found {len(matches)}")
        rec = matches[0]
        b = base.result_by_name(rec, "D/D-mongo-cache-v8")
        c = base.result_by_name(rec, "D/D-mongo-cache-ze")
        if b is None or c is None or \
                not base.check_pair(rec, b, c, log_rows,
                                    f"acceptance:{rec['site']}"):
            raise SystemExit(f"acceptance pair rejected by fairness gate ({prefix})")
        bp, cp = base.p95_of(b)[0], base.p95_of(c)[0]
        speedup = base.median_of(b)[0] / base.median_of(c)[0]
        bars.append({
            "label": label,
            "color": GREEN if speedup >= 1.5 else (AMBER if speedup >= 1.0 else RED),
            "star": "*" if rec["dirty"] else "", "rec": rec,
            "speedup": speedup,
            "p95": (bp / cp) if bp and cp else None,
        })

    fig, ax = plt.subplots(figsize=(9.2, 6.4))
    xs = range(len(bars))
    vals = [b["speedup"] for b in bars]
    ax.bar(xs, vals, 0.55, color=[b["color"] for b in bars],
           edgecolor="#263238", linewidth=0.6)
    for x, b in zip(xs, bars):
        ax.annotate(f"{b['speedup']:.2f}×{b['star']}", (x, b["speedup"]),
                    xytext=(0, 5), textcoords="offset points", ha="center",
                    fontsize=12, fontweight="bold", color="#263238")
        if b["p95"]:
            ax.plot([x - 0.22, x + 0.22], [b["p95"]] * 2,
                    color="#263238", lw=1.8, zorder=3)
            ax.annotate(f"p95 {b['p95']:.2f}×", (x + 0.24, b["p95"]),
                        fontsize=8, va="center", color="#37474f")

    ax.axhline(1.0, color=GRAY, ls="--", lw=1)
    ax.axhline(1.5, color=RED, ls="--", lw=1.4)
    ax.annotate("1× (setara)", (len(bars) - 1 + 0.42, 1.0), fontsize=8.5,
                va="center", ha="left", color=GRAY)
    ax.annotate("target 1,5×", (len(bars) - 1 + 0.42, 1.5), fontsize=8.5,
                va="center", ha="left", color=RED)
    ax.set_xlim(-0.5, len(bars) - 1 + 1.05)
    ax.set_xticks(list(xs), labels=[b["label"] for b in bars], fontsize=9)
    ax.set_ylim(0, max(vals + [b["p95"] for b in bars if b["p95"]]) * 1.2)
    ax.set_ylabel("Speedup fase D = T_baseline / T_ze (median)")
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)

    if VINTAGE == "nd6":
        acc_title = "ND-6 fase D — acceptance jalur produksi (cache Mongo ter-load)"
        acc_sub = ("Satu iterasi = GET /rekap atas 4 repository pada LAPISAN REPOSITORY "
                   "saq-report (bukan HTTP end-to-end).")
        acc_foot = ("Baseline repo.read().length (V8) vs ze repo.readCount() (structural count, wasm64 C-ABI) dalam satu run_id.\n"
                    "File-store fallback: lihat peta (I/O-bound). Vintage runtime campuran (dev Node 24, server Node 26).")
    elif VINTAGE == "nd10":
        acc_title = "ND-10 fase D — acceptance jalur produksi (kontrol runtime + mesin)"
        acc_sub = ("Node 26.13.1 identik di kedua site · wasm 35b7f773 byte-identik · tree bersih · "
                   "target ≥ 1,5× TIDAK tercapai di kedua site.")
        acc_foot = ("Baseline repo.read().length (V8) vs ze repo.readCount() (structural count, wasm64 C-ABI) dalam satu run_id.\n"
                    "E1: verdict era Node 24 (2,85×/3,00×) turun ~1,4× di Node 26 → runtime V8 14.6 = penyebab dominan kompresi (wasm era lama tak terekam sidecarnya → confounded).")
    else:
        acc_title = "Pasca-O1 fase D — acceptance jalur produksi (ND-12)"
        acc_sub = ("ABI v4 (O1-4+O1-5+O1-7) · wasm c5b42b7d byte-identik · Node 26.13.1 · tree bersih · "
                   "fase D tak tersentuh loop O1 (konsisten ND-9).")
        acc_foot = ("Baseline repo.read().length (V8) vs ze repo.readCount() (structural count, wasm64 C-ABI) dalam satu run_id.\n"
                    "File-store warm page-cache (confounder dinyatakan). Window mesin lebih lambat absolut — rasio in-window yang menjadi bukti.")
    fig.suptitle(acc_title, fontsize=13, fontweight="bold", y=0.99)
    fig.text(0.5, 0.935, acc_sub, ha="center", fontsize=9, color="#37474f")
    fig.text(0.5, 0.015, acc_foot, ha="center", fontsize=7.8, color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 0.915))
    base.save(fig, f"{PREFIX}-acceptance")
    return bars


# ---------------------------------------------------------------------------
# csv exhibits + verification output
# ---------------------------------------------------------------------------

def write_csv(name, fieldnames, rows):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, name)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    print("wrote", os.path.relpath(path, ROOT))


def main():
    recs = base.load_records()
    extra_dirs = {"nd10": ["nd10"], "post-o1": ["nd12", "nd10"]}.get(VINTAGE, [])
    for extra in extra_dirs:
        base.RECORDS_DIR = os.path.join(base.ROOT, "reports", extra)
        recs = base.load_records() + recs
    nd6 = base.nd6_phase_records(recs)
    print(f"loaded {len(recs)} records ({len(nd6)} ND-6 phase records)")
    log_rows = []

    cells = build_cells(nd6, log_rows)
    draw_map(cells)
    bars = draw_acceptance(nd6, log_rows)

    map_rows = []
    for row in ROWS:
        for site in SITES:
            cell = cells[(row["key"], site)]
            for it in cell["items"]:
                map_rows.append({
                    "row": row["key"], "label": row["label"], "site": site,
                    "run_id": cell["rec"]["run_id"],
                    "dirty": cell["rec"]["dirty"], "node": cell["rec"]["node"],
                    "doc": it["doc"],
                    "speedup": round(it["speedup"], 4),
                    "row_median": round(cell["speedup"], 4),
                    "row_min": round(cell.get("min", it["speedup"]), 4),
                    "row_max": round(cell.get("max", it["speedup"]), 4),
                    "baseline_result": it["baseline"]["name"],
                    "candidate_result": it["candidate"]["name"],
                    "baseline_seconds_median": base.median_of(it["baseline"])[0],
                    "candidate_seconds_median": base.median_of(it["candidate"])[0],
                    "speedup_p95": it["p95"],
                    "ze_json_commit": cell["rec"]["ze_hash"],
                    "saq_report_commit": cell["rec"]["saq_hash"],
                })
    write_csv(f"{PREFIX}-summary-map.csv", list(map_rows[0].keys()), map_rows)

    acc_rows = [{
        "site": b["rec"]["site"], "run_id": b["rec"]["run_id"],
        "dirty": b["rec"]["dirty"], "node": b["rec"]["node"],
        "path": "mongo-cache", "speedup_median": round(b["speedup"], 4),
        "speedup_p95": round(b["p95"], 4) if b["p95"] else None,
        "ze_json_commit": b["rec"]["ze_hash"],
        "saq_report_commit": b["rec"]["saq_hash"],
    } for b in bars]
    write_csv(f"{PREFIX}-acceptance.csv", list(acc_rows[0].keys()), acc_rows)
    if log_rows:
        write_csv(f"{PREFIX}-summary-fairness.csv", list(log_rows[0].keys()), log_rows)

    print("\n== summary map ==")
    for row in ROWS:
        d = cells[(row["key"], "dev_device")]["speedup"]
        s = cells[(row["key"], "saq_server")]["speedup"]
        print(f"{row['label']:<44} dev {d:6.2f}x   server {s:6.2f}x")
    print("\n== acceptance ==")
    for b in bars:
        p95 = f"{b['p95']:.2f}x" if b["p95"] else "n/a"
        print(f"{b['rec']['site']:<11} {b['rec']['run_id']}  "
              f"{b['speedup']:.2f}x (p95 {p95})")


if __name__ == "__main__":
    main()
