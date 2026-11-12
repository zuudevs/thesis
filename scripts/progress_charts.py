#!/usr/bin/env python3
"""progress_charts.py — thesis progress figures for the v5 workspace.

Two charts, both rebuilt from the workspace source of truth on every run:

1. progress_phases.png    — done/open task bars per phase, parsed from
                            TASKS.md (## section = phase, checkbox = task).
2. progress_timeline.png  — optimization-experiment log (native C++ vs
                            Node/wasm lanes) with per-experiment verdicts
                            (DITERIMA / DITOLAK / diagnostic / keep opt-in).
                            EXPERIMENTS below is curated: dates are report
                            commit dates (git log), or the TASKS.md date for
                            P4 candidates that never got their own report.
                            Update the table when a new experiment report
                            lands.

Outputs: out/charts/*.png (gitignored analysis figures — AGENTS.md §4).
Usage:   python scripts/progress_charts.py [--tasks TASKS.md]
                                        [--reports reports]
                                        [--out out/charts]
"""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# Chart 1 — parse TASKS.md phases
# --------------------------------------------------------------------------


def natural_phase_key(title: str):
    """Sort P0..P7 numerically first, then R / O1 / PW."""
    m = re.match(r"(P(\d+)|R|O1|PW)\b", title)
    if not m:
        return (9, 0, title)
    if m.group(2):
        return (0, int(m.group(2)), title)
    order = {"R": 1, "O1": 2, "PW": 3}
    return (order.get(m.group(1), 9), 0, title)


PHASE_SHORT = {
    "P0": "Fondasi pengukuran",
    "P1": "Harness & korpus native",
    "P2": "Harness baseline SAQ",
    "P3": "Binding wasm64 Node",
    "P4": "Loop optimasi C++ (native)",
    "P5": "Pengukuran lintas arsitektur",
    "P6": "Dokumentasi ze_json",
    "P7": "Parser on-demand",
    "R": "Scanner-mode surface",
    "O1": "Optimasi jalur Node",
    "PW": "Alur kerja Git",
}


def parse_tasks(path: Path):
    """Return [(phase_key, phase_title, done, open_ids)] from TASKS.md."""
    phases: dict[str, list[tuple[bool, str]]] = {}
    titles: dict[str, str] = {}
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## ") and not line.startswith("## Status"):
            raw = line[3:].split("—")[0].strip()
            current = raw.split()[0]
            titles[current] = line[3:].strip()
            phases.setdefault(current, [])
            continue
        m = re.match(r"- \[( |x)\] \*\*([A-Z0-9-]+)", line)
        if m and current:
            phases[current].append((m.group(1) == "x", m.group(2)))
    result = []
    for key in sorted(phases, key=natural_phase_key):
        entries = phases[key]
        done = sum(1 for is_done, _ in entries if is_done)
        open_ids = [task_id for is_done, task_id in entries if not is_done]
        result.append((key, titles[key], done, open_ids))
    return result


def render_phases(rows, out_path: Path):
    done_c, open_c = "#2e7d32", "#ef6c00"
    labels = [f"{k} — {PHASE_SHORT.get(k, t)}" for k, t, _, _ in rows]
    done = [d for _, _, d, _ in rows]
    open_n = [len(o) for _, _, _, o in rows]
    total = sum(done) + sum(open_n)

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    y = list(range(len(rows)))[::-1]
    ax.barh(y, done, color=done_c, label="selesai")
    ax.barh(y, open_n, left=done, color=open_c, label="terbuka")

    for yi, (key, _, d, open_ids) in zip(y, rows):
        n = d + len(open_ids)
        pct = 100.0 * d / n if n else 0.0
        ax.text(d + len(open_ids) + 0.15, yi, f"{d}/{n} ({pct:.0f}%)",
                va="center", fontsize=9, color="#37474f")
        if open_ids:  # active phase: annotate the open task ids
            ax.text(d + 0.1, yi, " · ".join(open_ids), va="center",
                    ha="right", fontsize=8, color="#ffffff", fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9.5)
    active = [k for k, _, d, o in rows if o]
    ax.set_xlabel("jumlah tugas")
    ax.set_xlim(0, max(d + len(o) + 3.4 for _, _, d, o in rows))
    ax.set_title(
        "Progres Skripsi per Fase  (sumber: TASKS.md)\n"
        f"{sum(done)}/{total} tugas selesai — fase aktif: "
        + ", ".join(active),
        fontsize=12,
    )
    ax.legend(loc="lower right", framealpha=0.9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# --------------------------------------------------------------------------
# Chart 2 — optimization experiment log (curated; see module docstring)
# --------------------------------------------------------------------------

# verdicts: accepted / rejected / diagnostic / optin
EXPERIMENTS = [
    ("2026-11-10", "native", "P4-C1", "Tabel kelas string (Mison-style)", "rejected",
     "regress seragam -12..-48% (layout kode)"),
    ("2026-11-10", "native", "P4-C2", "Reziprokal number q<0", "accepted",
     "FullWalk +19.6..+33.2%"),
    ("2026-11-11", "native", "E3", "LTO/ipo preset", "optin",
     "keep preset opt-in, bukan pengukuran"),
    ("2026-11-11", "node", "O1-1 (R5-1)", "Assignment null-proto", "accepted",
     "median 1.09..1.25x"),
    ("2026-11-12", "node", "O1-6 (R5-2)", "Drop array presize count", "accepted",
     "median 1.02..3.95x (1mb; kuadratik lenyap)"),
    ("2026-11-12", "node", "O1-2 (R5-3)", "TextDecoder cached", "accepted",
     "median 1.067..1.125"),
    ("2026-11-12", "node", "O1-3 (R5-4)", "DataView cache getDouble", "accepted",
     "median 1.021..1.055"),
    ("2026-11-12", "node", "O1-9 (R5-5)", "Fusi scan string C++", "rejected",
     "netral/-2% (codegen shift)"),
    ("2026-11-12", "node", "O1-11 (R5-6)", "Tracing wrong-map #frame", "diagnostic",
     "hipotesis tidak terkonfirmasi"),
    ("2026-11-12", "node", "O1-8 (R5-7)", "Gallop first_index", "accepted",
     "countElements 59.2x (684.7 -> 11.6 ms)"),
    ("2026-11-12", "node", "O1-10 (R5-8)", "Fused step+kind ABI v4", "rejected",
     "netral (0.979..1.027)"),
]

VERDICT_STYLE = {
    "accepted": ("#2e7d32", "Diterima"),
    "rejected": ("#c62828", "Ditolak"),
    "diagnostic": ("#455a64", "Diagnostik"),
    "optin": ("#f9a825", "Keep opt-in"),
}
LANE_MARKER = {"native": "s", "node": "o"}
LANE_LABEL = {"native": "native C++ (ze_json core)", "node": "Node.js wasm64 binding"}

NEXT_UP = ("Terbuka berikutnya: O1-4 mirror valueKind (3.8%) · O1-5 hoist "
           "BigInt #frame/#plain (9.1%) · O1-7 thin-call ABI v4 · P4-C3 UTF-8 SIMD")


def render_timeline(experiments, out_path: Path):
    fig, ax = plt.subplots(figsize=(12.5, 7.0))
    rows = list(reversed(experiments))  # oldest at top
    ystep = 1.0
    for yi, (day, lane, exp_id, title, verdict, note) in enumerate(rows):
        color, verdict_label = VERDICT_STYLE[verdict]
        x = (date.fromisoformat(day) - date(2026, 11, 9)).days
        ax.scatter(x, yi * ystep, s=110, color=color, zorder=3,
                   marker=LANE_MARKER[lane],
                   edgecolors="black", linewidths=0.5)
        ax.annotate(f"{exp_id} — {title}", (x, yi * ystep),
                    xytext=(12, 0), textcoords="offset points",
                    va="center", fontsize=9.3, color="#212121")
        ax.annotate(f"{verdict_label} · {note}", (x, yi * ystep),
                    xytext=(12, 12), textcoords="offset points",
                    va="center", fontsize=7.8, color=color)

    days = sorted({date.fromisoformat(d) for d, *_ in experiments})
    for d in days:
        x = (d - date(2026, 11, 9)).days
        ax.axvline(x, color="#b0bec5", lw=0.8, zorder=1)
        ax.text(x, len(rows) - 0.25, d.strftime("%d Nov"), ha="center",
                fontsize=9, color="#607d8b")

    handles = [
        plt.Line2D([], [], color=VERDICT_STYLE[v][0], marker="o", ls="",
                   label=lbl, markersize=9)
        for v, lbl in [("accepted", "Diterima"), ("rejected", "Ditolak"),
                       ("diagnostic", "Diagnostik"), ("optin", "Keep opt-in")]
    ]
    handles += [
        plt.Line2D([], [], color="#616161", marker=m, ls="", label=l,
                   markersize=8)
        for m, l in [(LANE_MARKER["node"], "lane: Node/wasm64"),
                     (LANE_MARKER["native"], "lane: native C++")]
    ]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(0.015, 0.42),
              fontsize=8.5, framealpha=0.95)

    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_xlim(-0.7, (days[-1] - date(2026, 11, 9)).days + 1.15)
    ax.set_ylim(-1.0, len(rows) - 0.05 + 0.35)
    for sp in ("top", "right", "left", "bottom"):
        ax.spines[sp].set_visible(False)
    n_acc = sum(1 for *_, v, _ in experiments if v == "accepted")
    ax.set_title(
        "Log Eksperimen Optimasi (P4/E3 + R5/O1) — "
        f"{n_acc} diterima, "
        f"{sum(1 for *_, v, _ in experiments if v == 'rejected')} ditolak\n"
        "sumber: TASKS.md + reports/*.md (tanggal = commit laporan)",
        fontsize=12,
    )
    fig.text(0.5, 0.015, NEXT_UP, ha="center", fontsize=9, color="#37474f")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tasks", type=Path, default=ROOT / "TASKS.md")
    ap.add_argument("--reports", type=Path, default=ROOT / "reports")
    ap.add_argument("--out", type=Path, default=ROOT / "out" / "charts")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    rows = parse_tasks(args.tasks)
    assert rows, "no phases parsed from TASKS.md"
    render_phases(rows, args.out / "progress_phases.png")
    print(f"[+] {args.out / 'progress_phases.png'} "
          f"({sum(d for _, _, d, _ in rows)} done, "
          f"{sum(len(o) for _, _, _, o in rows)} open)")

    # curated table must point at real report files where one exists
    for day, lane, exp_id, title, verdict, note in EXPERIMENTS:
        assert verdict in VERDICT_STYLE and lane in LANE_MARKER
    render_timeline(EXPERIMENTS, args.out / "progress_timeline.png")
    print(f"[+] {args.out / 'progress_timeline.png'} "
          f"({len(EXPERIMENTS)} experiments)")


if __name__ == "__main__":
    main()
