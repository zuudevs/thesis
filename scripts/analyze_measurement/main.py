#!/usr/bin/env python3
"""analyze_measurement.py — summarize / compare / trend over measurement records v1.

Ported to the skripsi workspace as docs/project/tasks.md P0-6 from the cpp-highperf-json skill
script (scripts/analyze_benchmark_result/main.py). The analyzer now reads validated
measurement records (schemas/measurement.schema.json) instead of raw google-benchmark
files; raw exhibits stay untouched under out/raw/<run_id>/.

Subcommands
  summary  Summarize one record; optionally append rows to --csv
  compare  Baseline vs candidate; exit 1 on throughput regression, exit 2 when the
           comparison is illegal or a record is not analysis-legal
  trend    Throughput of one topic across all matching records (oldest first);
           --chart needs matplotlib

Comparison legality (AGENTS.md section 4): two records may only be compared
in-situ -- same kind, generator, site, host, corpus (name + sha256), library, and
build preset (config.notes "preset=..."). git hashes are ALLOWED to differ (that
is the point of baseline-vs-candidate); everything else must match or the tool
refuses (exit 2). Records that fail measurement-schema validation are refused
(exit 2) in every subcommand -- they must never drive analysis.

Record discovery for --topic: any *_record.json / *.record.json under the
directory whose file name contains the topic substring; compare picks the two
newest by mtime.

Examples
  python scripts/analyze_measurement/main.py summary --input out/measurements/<run_id>_record.json
  python scripts/analyze_measurement/main.py compare --baseline <recA> --candidate <recB>
  python scripts/analyze_measurement/main.py compare --topic parse_scan
  python scripts/analyze_measurement/main.py trend --topic parse_scan --chart out/charts/parse_scan.png
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "measurement-schema"))
from validate import validate  # noqa: E402  (schema-driven, stdlib-only)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "measurement.schema.json"

EXIT_OK = 0
EXIT_REGRESSION = 1
EXIT_ILLEGAL = 2


def refuse(code: int, message: str) -> int:
    """Print a refusal/error to stderr and exit with the given code."""
    print(message, file=sys.stderr)
    raise SystemExit(code)


@dataclass
class Row:
    name: str
    engine: str
    status: str
    throughput: float          # bytes/s | items/s | docs/s | ops/s (1/seconds_mean)
    unit: str
    seconds_mean: float | None = None
    seconds_stddev: float | None = None
    cpu_seconds: float | None = None
    cv_pct: float | None = None
    extras: dict = field(default_factory=dict)


@dataclass
class Rec:
    path: str
    run_id: str
    kind: str
    generator: str
    site: str
    hostname: str
    corpus_name: str
    corpus_sha256: str
    library_name: str
    git_hash: str
    dirty: bool
    preset: str | None
    rows: dict[str, Row]
    excluded: dict[str, Row]   # status != ok


def _pick_throughput(metrics: dict) -> tuple[float, str] | None:
    """Primary basis: bytes_per_second; fallbacks: items/s, docs/s, ops/s (1/seconds_mean)."""
    if metrics.get("bytes_per_second", 0) > 0:
        return float(metrics["bytes_per_second"]), "B/s"
    if metrics.get("items_per_second", 0) > 0:
        return float(metrics["items_per_second"]), "items/s"
    if metrics.get("documents_per_second", 0) > 0:
        return float(metrics["documents_per_second"]), "docs/s"
    seconds_mean = metrics.get("seconds_mean")
    if isinstance(seconds_mean, (int, float)) and seconds_mean > 0:
        return 1.0 / seconds_mean, "ops/s"
    return None


def _preset_from(notes: str | None) -> str | None:
    if not notes:
        return None
    match = re.search(r"preset=([^;\s]+)", notes)
    return match.group(1) if match else None


def load(path: str) -> Rec:
    """Load + schema-validate one record; refusal (exit 2) is mandatory on failure."""
    record_path = Path(path)
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        refuse(EXIT_ILLEGAL, f"FAIL unreadable record ({record_path}): {exc}")
    errors = validate(record, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")), "$")
    if errors:
        lines = "\n".join(f"  - {e}" for e in errors)
        refuse(EXIT_ILLEGAL,
               f"FAIL record not analysis-legal ({record_path.name}); "
               f"validated records only (AGENTS.md section 4):\n{lines}")

    rows: dict[str, Row] = {}
    excluded: dict[str, Row] = {}
    for res in record.get("results", []):
        metrics = res.get("metrics", {})
        picked = _pick_throughput(metrics)
        throughput, unit = picked if picked else (0.0, "ops/s")
        extras = {k: float(v) for k, v in res.get("extras", {}).items()
                  if isinstance(v, (int, float)) and not isinstance(v, bool)}
        row = Row(
            name=res["name"],
            engine=res["engine"],
            status=res["status"],
            throughput=throughput,
            unit=unit,
            seconds_mean=metrics.get("seconds_mean"),
            seconds_stddev=metrics.get("seconds_stddev"),
            cpu_seconds=metrics.get("cpu_seconds"),
            cv_pct=(metrics["seconds_stddev"] / metrics["seconds_mean"] * 100.0
                    if metrics.get("seconds_mean") and metrics.get("seconds_stddev") is not None
                    else None),
            extras=extras,
        )
        (rows if res["status"] == "ok" else excluded)[res["name"]] = row

    git = record.get("git_commit", {})
    return Rec(
        path=str(record_path),
        run_id=record["run_id"],
        kind=record["kind"],
        generator=record["generator"],
        site=record["site"],
        hostname=record.get("host", {}).get("hostname", "?"),
        corpus_name=record.get("corpus", {}).get("name", "?"),
        corpus_sha256=record.get("corpus", {}).get("sha256", ""),
        library_name=record.get("library", {}).get("name", "?"),
        git_hash=git.get("hash", "?"),
        dirty=bool(git.get("dirty")),
        preset=_preset_from(record.get("config", {}).get("notes")),
        rows=rows,
        excluded=excluded,
    )


# ---------------------------------------------------------------- formatting


def fmt_tp(value: float, unit: str) -> str:
    if unit == "B/s":
        for label, divisor in (("GB/s", 1e9), ("MB/s", 1e6), ("KB/s", 1e3)):
            if value >= divisor:
                return f"{value / divisor:.2f} {label}"
        return f"{value:.0f} B/s"
    for label, divisor in (("G", 1e9), ("M", 1e6), ("K", 1e3)):
        if value >= divisor:
            return f"{value / divisor:.2f} {label}{unit}"
    return f"{value:.1f} {unit}"


def fmt_val(value: float) -> str:
    if abs(value) >= 1e9:
        return f"{value / 1e9:.2f}G"
    if abs(value) >= 1e6:
        return f"{value / 1e6:.2f}M"
    if abs(value) >= 1e3:
        return f"{value / 1e3:.2f}K"
    return f"{value:.2f}"


def table(rows: list[list[str]], header: list[str]) -> str:
    widths = [max(len(str(r[i])) for r in [header] + rows) for i in range(len(header))]
    line = lambda r: "  ".join(str(c).ljust(w) for c, w in zip(r, widths))
    return "\n".join([line(header), "  ".join("-" * w for w in widths)] + [line(r) for r in rows])


def git_tag(rec: Rec) -> str:
    return f"{rec.git_hash}{'*' if rec.dirty else ''}"


# ------------------------------------------------------------------ commands


def cmd_summary(a: argparse.Namespace) -> int:
    rec = load(a.input)
    print(f"run_id    : {rec.run_id}\ngit/site  : {git_tag(rec)} / {rec.site}\n"
          f"library   : {rec.library_name} (preset={rec.preset or '-'})\n"
          f"corpus    : {rec.corpus_name} ({rec.corpus_sha256[:12]}...)\n")
    rows = [[n, f"[{b.engine}]", fmt_tp(b.throughput, b.unit), f"{b.seconds_mean * 1e6:.1f}",
             "" if b.cv_pct is None else f"{b.cv_pct:.1f}%", b.status]
            for n, b in sorted(rec.rows.items())]
    print(table(rows, ["result", "engine", "throughput", "real us", "cv", "status"]))

    for n, b in sorted(rec.excluded.items()):
        print(f"excluded (status={b.status}): {n}")

    if a.csv:
        os.makedirs(os.path.dirname(a.csv) or ".", exist_ok=True)
        exists = os.path.exists(a.csv)
        with open(a.csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(["record_file", "run_id", "git", "result", "engine",
                                 "throughput", "unit", "real_ns", "cpu_ns", "cv_pct"])
            for n, b in sorted(rec.rows.items()):
                writer.writerow([Path(a.input).name, rec.run_id, git_tag(rec), n, b.engine,
                                 f"{b.throughput:.6g}", b.unit,
                                 "" if b.seconds_mean is None else f"{b.seconds_mean * 1e9:.6g}",
                                 "" if b.cpu_seconds is None else f"{b.cpu_seconds * 1e9:.6g}",
                                 "" if b.cv_pct is None else f"{b.cv_pct:.3f}"])
        print(f"\nappended to {a.csv}")
    return EXIT_OK


def matching_topic_files(topic: str, directory: str) -> list[str]:
    dir_path = Path(directory)
    files = [p for p in (*dir_path.glob("*_record.json"), *dir_path.glob("*.record.json"))
             if topic in p.name]
    return sorted(files, key=lambda p: p.stat().st_mtime)


def _guard_dims(rec: Rec) -> tuple[tuple[str, str], ...]:
    return (
        ("kind", rec.kind),
        ("generator", rec.generator),
        ("site", rec.site),
        ("host", rec.hostname),
        ("corpus", f"{rec.corpus_name}@{rec.corpus_sha256[:12]}"),
        ("library", rec.library_name),
        ("preset", rec.preset or "(none)"),
    )


def guarded(files: list[Rec]) -> list[tuple[str, str]]:
    """Inconsistency list of guard dimensions across records vs the first one ([] = legal)."""
    if len(files) < 2:
        return []
    dims0 = _guard_dims(files[0])
    inconsistencies = []
    for rec in files[1:]:
        for (dim, value0), (_, value) in zip(dims0, _guard_dims(rec)):
            if value0 != value:
                inconsistencies.append((dim, f"{Path(files[0].path).name}: {value0} "
                                              f"vs {Path(rec.path).name}: {value}"))
    return inconsistencies


def cmd_compare(a: argparse.Namespace) -> int:
    base_p, cand_p = a.baseline, a.candidate
    if a.topic:
        found = matching_topic_files(a.topic, a.dir)
        if len(found) < 2:
            refuse(EXIT_ILLEGAL, f"FAIL need >= 2 topic files under {a.dir}, found {len(found)}")
        base_p, cand_p = str(found[-2]), str(found[-1])
    if not base_p or not cand_p:
        refuse(EXIT_ILLEGAL, "FAIL give --baseline and --candidate, or --topic")

    base_rec, cand_rec = load(base_p), load(cand_p)
    inconsistencies = guarded([base_rec, cand_rec])
    if inconsistencies:
        lines = "\n".join(f"  - {dim}: {detail}" for dim, detail in inconsistencies)
        refuse(EXIT_ILLEGAL,
               f"FAIL comparison illegal (AGENTS.md section 4):\n{lines}\n"
               f"Numbers may only be compared in-situ: same kind/generator/site/host/"
               f"corpus/library/preset. Commit hashes may differ.")

    print(f"baseline : {base_p} ({git_tag(base_rec)}, run {base_rec.run_id})\n"
          f"candidate: {cand_p} ({git_tag(cand_rec)}, run {cand_rec.run_id})\n"
          f"noise floor: max({a.threshold}%, 2 x CV)\n")

    rows, regressions = [], 0
    common = sorted(set(base_rec.rows) & set(cand_rec.rows))
    for name in common:
        b, c = base_rec.rows[name], cand_rec.rows[name]
        if b.throughput <= 0 or c.throughput <= 0:
            rows.append([name, fmt_tp(b.throughput, b.unit), fmt_tp(c.throughput, c.unit),
                         "-", "-", "no throughput metric"])
            continue
        if b.unit != c.unit:
            rows.append([name, f"{fmt_tp(b.throughput, b.unit)} ({b.unit})",
                         f"{fmt_tp(c.throughput, c.unit)} ({c.unit})",
                         "-", "-", "different metric basis (not compared)"])
            continue
        delta = (c.throughput / b.throughput - 1.0) * 100.0
        cvs = [x for x in (b.cv_pct, c.cv_pct) if x is not None]
        noise = max(a.threshold, 2 * max(cvs)) if cvs else a.threshold
        state = ("within noise" if abs(delta) <= noise
                 else "IMPROVED" if delta > 0 else "REGRESSED")
        regressions += state == "REGRESSED"
        rows.append([name, fmt_tp(b.throughput, b.unit), fmt_tp(c.throughput, c.unit),
                     f"{delta:+.1f}%", f"{noise:.1f}%", state])

    print(table(rows, ["result", "baseline", "candidate", "delta", "noise", "verdict"]))

    counter_rows = []
    for name in common:
        b_extras, c_extras = base_rec.rows[name].extras, cand_rec.rows[name].extras
        for k in sorted(set(b_extras) & set(c_extras)):
            bv, cv_ = b_extras[k], c_extras[k]
            if bv == 0 and cv_ == 0:
                continue
            d = (cv_ / bv - 1.0) * 100.0 if bv else float("inf")
            counter_rows.append([name, k, fmt_val(bv), fmt_val(cv_), f"{d:+.1f}%"])
    if counter_rows:
        print("\nSecondary counters (from extras; judge per counter):")
        print(table(counter_rows, ["result", "counter", "baseline", "candidate", "delta"]))

    for label, only in (("only in baseline", set(base_rec.rows) - set(cand_rec.rows)),
                        ("only in candidate", set(cand_rec.rows) - set(base_rec.rows))):
        if only:
            print(f"\n{label}: {', '.join(sorted(only))}")

    if regressions:
        print(f"\n{regressions} throughput regression(s) beyond noise.")
        return EXIT_REGRESSION
    print("\nNo throughput regression beyond noise.")
    return EXIT_OK


def cmd_trend(a: argparse.Namespace) -> int:
    files = matching_topic_files(a.topic, a.dir)
    if not files:
        refuse(EXIT_ILLEGAL, f"FAIL no records matching topic '{a.topic}' under {a.dir}")
    recs = [load(str(path)) for path in files]
    inconsistencies = guarded(recs)
    if inconsistencies:
        lines = "\n".join(f"  - {dim}: {detail}" for dim, detail in inconsistencies)
        refuse(EXIT_ILLEGAL,
               f"FAIL trend illegal (AGENTS.md section 4):\n{lines}\n"
               f"A trend line is a comparison too: records must share kind/generator/"
               f"site/host/corpus/library/preset; commit hashes may differ.")
    series: dict[str, list[tuple[str, float, str]]] = {}
    for rec in recs:
        for name, row in rec.rows.items():
            series.setdefault(name, []).append((f"{git_tag(rec)}", row.throughput, row.unit))

    rows = [[n, " -> ".join(f"{tag}:{fmt_tp(v, u)}" for tag, v, u in pts)]
            for n, pts in sorted(series.items())]
    print(table(rows, ["result", "throughput (oldest first)"]))

    if a.chart:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            refuse(EXIT_ILLEGAL, "FAIL matplotlib not installed; chart skipped")
        fig, ax = plt.subplots(figsize=(9, 5))
        for name, pts in sorted(series.items()):
            base = pts[0][1] or 1.0
            ax.plot([t for t, _, _ in pts], [v / base * 100 for _, v, _ in pts],
                    marker="o", label=name)
        ax.set_ylabel("throughput, % of first record")
        ax.set_xlabel("git commit")
        ax.axhline(100, color="gray", lw=0.8)
        ax.legend(fontsize=7)
        fig.tight_layout()
        os.makedirs(os.path.dirname(a.chart) or ".", exist_ok=True)
        fig.savefig(a.chart, dpi=150)
        print(f"\nchart written to {a.chart}")
    return EXIT_OK


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("summary", help="summarize one measurement record")
    s.add_argument("--input", required=True)
    s.add_argument("--csv", help="append rows to this CSV (e.g. out/measurements/<topic>.csv)")
    s.set_defaults(fn=cmd_summary)

    c = sub.add_parser("compare", help="baseline vs candidate record")
    c.add_argument("--baseline")
    c.add_argument("--candidate")
    c.add_argument("--topic", help="use the two newest *_record.json matching this substring")
    c.add_argument("--dir", default="out/measurements")
    c.add_argument("--threshold", type=float, default=3.0,
                   help="minimum noise band in percent (default 3)")
    c.set_defaults(fn=cmd_compare)

    t = sub.add_parser("trend", help="throughput across matching records")
    t.add_argument("--topic", required=True)
    t.add_argument("--dir", default="out/measurements")
    t.add_argument("--chart", help="write PNG here (needs matplotlib)")
    t.set_defaults(fn=cmd_trend)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
