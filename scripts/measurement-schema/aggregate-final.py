#!/usr/bin/env python3
"""aggregate-final.py — aggregate validated measurement records into the final
numbers report + throughput chart (TASKS P6-5).

Reads schema-v1 measurement records, keeps every entry (they are all
validator-PASS by construction), and emits:
  - a markdown report (median throughput per corpus/result, CV, run ids)
  - an optional grouped-bar chart (matplotlib) for the thesis

Usage:
  python scripts/measurement-schema/aggregate-final.py \
      --record ze_native=out/measurements/zuu-20261109042022-ca8f5f4_*_record.json \
      --record v8=out/measurements/zuu-20261108214228-0340a72_*_record.json \
      --record ze_wasm64=out/measurements/zuu-20261108221414-85afad7_*_record.json \
      --out reports/final-numbers.md --chart out/charts/final-throughput.png
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "measurement.schema.json"


def load_grouped(spec: str):
    """`label=glob` -> (label, list of (record, validation-ok))."""
    label, _, pattern = spec.partition("=")
    if not pattern:
        pattern, label = label, label
    entries = []
    for path in sorted(glob.glob(str(ROOT / pattern))):
        record = json.loads(Path(path).read_text(encoding="utf-8"))
        errors = validate(record, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")), "$")
        if errors:
            print(f"FAIL {path}: {errors}", file=sys.stderr)
            sys.exit(1)
        entries.append(record)
    if not entries:
        print(f"FAIL no records for '{spec}'", file=sys.stderr)
        sys.exit(1)
    return label, entries


def fmt_mb(v: float) -> str:
    return f"{v:,.1f}"


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", action="append", required=True, metavar="LABEL=GLOB",
                    help="validated record set, e.g. ze_native=out/measurements/<run>_*_record.json")
    ap.add_argument("--out", default="reports/final-numbers.md")
    ap.add_argument("--chart", default=None, help="optional PNG path (needs matplotlib)")
    args = ap.parse_args(argv)

    groups = [load_grouped(spec) for spec in args.record]

    lines: list[str] = []
    lines.append("# Final measurement numbers (validated records)")
    lines.append("")
    lines.append("All numbers are **medians over 5 repetitions** from schema-v1 records")
    lines.append("that PASS `scripts/measurement-schema/validate.py` (re-checked on load).")
    lines.append("Site `dev_device`, per-run host introspection embedded in every record;")
    lines.append("throughput in MB/s (1 MB = 1e6 bytes). Cross-engine comparison of")
    lines.append("*different workloads* (scan vs full parse) is NOT apples-to-apples —")
    lines.append("comparability notes live in the P4 bottleneck report.")
    lines.append("")

    for label, records in groups:
        runs = sorted({r["run_id"] for r in records})
        git = sorted({r["git_commit"]["hash"] + ("*" if r["git_commit"]["dirty"] else "")
                      for r in records})
        lines.append(f"## {label}")
        lines.append("")
        lines.append(f"- runs: {', '.join(runs)}")
        lines.append(f"- git: {', '.join(git)} — library: "
                     f"{records[0]['library']['name']} {records[0]['library']['version']} "
                     f"({records[0]['library']['language_runtime']})")
        lines.append("")
        lines.append("| corpus | result | MB/s | cv |")
        lines.append("|---|---|---:|---:|")
        for record in records:
            corpus = record["corpus"]["name"]
            for res in record["results"]:
                if res["status"] != "ok":
                    continue
                mbps = res["metrics"].get("bytes_per_second", 0) / 1e6
                mean = res["metrics"]["seconds_mean"]
                cv = (res["metrics"].get("seconds_stddev", 0.0) / mean * 100.0) if mean else 0.0
                lines.append(f"| {corpus} | `{res['name']}` | {fmt_mb(mbps)} | {cv:.1f}% |")
        lines.append("")

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[+] report -> {out_path}")

    if args.chart:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("FAIL matplotlib not installed; chart skipped", file=sys.stderr)
            return 1

        corpora_order = ["synthetic_1k", "synthetic_10k", "synthetic_100k",
                         "synthetic_1mb", "saq_payload_v1", "checker_batch"]
        series_labels = []
        data: dict[str, list[float | None]] = {}

        def series_name(group_label: str, res_name: str, engine: str) -> str | None:
            if group_label == "ze_native":
                if "Scanner8" in res_name:
                    return "ze native — scanner8 (structural scan)"
                if "Structural" in res_name:
                    return "ze native — structural_scan (dispatch)"
                return None
            if group_label == "v8":
                if "body-parse" in res_name:
                    return "V8 — JSON.parse (body-parse)"
                if "store-read" in res_name:
                    return "V8 — store-read (parse+unwrap)"
                if "export-stringify" in res_name:
                    return "V8 — JSON.stringify (export)"
                return None
            if group_label == "ze_wasm64":
                if "wasm-scan" in res_name:
                    return "ze wasm64 — structural scan (C-ABI)"
                if "wasm-parse-full" in res_name:
                    return "ze wasm64 — full parse (C-ABI)"
                return None
            return None

        lookup: dict[tuple[str, str, str], tuple[float, float]] = {}
        for label, records in groups:
            for record in records:
                corpus = record["corpus"]["name"]
                for res in record["results"]:
                    if res["status"] != "ok":
                        continue
                    name = series_name(label, res["name"], res["engine"])
                    if name is None:
                        continue
                    mbps = res["metrics"].get("bytes_per_second", 0) / 1e6
                    mean = res["metrics"]["seconds_mean"]
                    cv = (res["metrics"].get("seconds_stddev", 0.0) / mean * 100.0) if mean else 0.0
                    lookup[(name, corpus)] = (mbps, cv)
                    if name not in series_labels:
                        series_labels.append(name)

        for name in series_labels:
            data[name] = [lookup.get((name, c), (None, None))[0] for c in corpora_order]

        fig, ax = plt.subplots(figsize=(11, 5.5))
        width = 0.8 / max(len(series_labels), 1)
        import numpy
        xs = numpy.arange(len(corpora_order))
        for idx, name in enumerate(series_labels):
            values = [(v if v is not None else 0) for v in data[name]]
            ax.bar(xs + idx * width, values, width, label=name)
        ax.set_xticks(xs)
        ax.set_xticklabels([c.replace("synthetic_", "").replace("saq_payload_v1", "saq")
                            for c in corpora_order])
        ax.set_ylabel("throughput (MB/s)")
        ax.set_title("JSON processing throughput — validated records, site dev_device")
        ax.legend(fontsize=8, loc="upper left")
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        chart_path = ROOT / args.chart
        chart_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(chart_path, dpi=150)
        print(f"[+] chart  -> {chart_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
