#!/usr/bin/env python3
# ============================================================================
#  analyze_benchmarks.py — Analisa benchmark ze_json + saq-report lintas-device
# ============================================================================
#  Membaca SEMUA artefak KEEP hasil audit_raw.py, lalu:
#
#    1. out/benchmarks.csv — tabel tidy per benchmark: package, target,
#       run_id, commit, device (cpu/cores/os dari sidecar), benchmark,
#       fixture + sha256, agregat waktu (mean/median/stddev bila repetisi;
#       sampel tunggal bila tidak), bytes_per_second.
#    2. out/summary.md — ringkasan siap kutip skripsi:
#       - konteks device per run
#       - tabel per-target ze_json (P50 + throughput)
#       - perbandingan lintas-device (fixture sha256 identik + library sama)
#       - perbandingan lintas-PAKET: ze_json scanner64 (corpus_benchmark) vs
#         JSON.parse saq-report per fixture sha256 identik — perbandingan
#         inti skripsi
#       - test (correctness record)
#
#  Pemakaian:  python research/analyze_benchmarks.py [--raw <dir>] [--out <dir>]
# ============================================================================
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_raw import audit  # reuse gerbang integritas

# Pemetaan token nama benchmark -> fixture (stem, tanpa .json) — untuk target
# lama yang hand-register fixture commons.
FIXTURE_TOKENS = {
    "jeopardy": "jeopardy.json",
    "twitter": "twitter.json",
    "github_events": "github_events.json",
    "githubevents": "github_events.json",
    "update_center": "update-center.json",
    "updatecenter": "update-center.json",
    "mesh": "mesh.json",
    "canada": "canada.json",
    "citm_catalog": "citm_catalog.json",
    "citm": "citm_catalog.json",
    "tiny": "tiny.json",
    "literal": "literal.json",
}

# Nama benchmark corpus_benchmark: BM_Corpus_Scanner64_<grup>_<fixture>
# (grup sanitasi-lowercase: json_checker | commons | saq_report).
CORPUS_RE = re.compile(r"^BM_Corpus_Scanner64_(json_checker|commons|saq_report)_(.+)$")


def sanitize_stem(name: str) -> str:
    """Sama dengan sanitize() di corpus_benchmark/main.cpp (non-alnum -> '_')."""
    return re.sub(r"[^0-9A-Za-z]", "_", name)


def guess_fixture(benchmark_name: str) -> str | None:
    lowered = benchmark_name.lower()
    for token, fixture in FIXTURE_TOKENS.items():
        if token in lowered:
            return fixture
    return None


def short_device(cpu_model: str) -> str:
    """Ringkas nama CPU untuk label tabel/chart."""
    return " ".join(cpu_model.split())


def load_keep_runs(raw_dir: Path) -> list[dict]:
    """Semua report KEEP -> rekaman run-level (benchmark + konteks)."""
    keep = {r["file"] for r in audit(raw_dir) if r["verdict"] == "KEEP"}
    runs: list[dict] = []

    for rel in sorted(keep):
        file = raw_dir / rel
        parts = Path(rel).parts
        if len(parts) < 3:
            continue
        category, package = parts[0], parts[1]
        stem = file.stem
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if package == "saq-report":
            runs.append({
                "package": "saq-report", "category": category,
                "target": "saq-benchmark",
                "run_id": data.get("metadata", {}).get("run_id", stem),
                "commit": (data.get("metadata", {}).get("source", {}) or {}).get("git_commit"),
                "data": data, "sidecar": None,
                "machine": (data.get("metadata", {}).get("runtime", {}) or {}),
            })
            continue

        sidecar_path = file.with_name(stem + ".metadata.json")
        sidecar = None
        if sidecar_path.is_file():
            try:
                sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                sidecar = None
        md = (sidecar or {}).get("metadata", {})
        context = data.get("context", {})

        # Dua indeks fixture -> (sha256, size):
        #   by name   : utk benchmark lama (hand-register, nama file polos)
        #   by (grup, stem sanitasi): utk corpus_benchmark (nama grup+stem)
        fixtures: dict[str, dict] = {}
        fixtures_by_group_stem: dict[tuple[str, str], dict] = {}
        for d in md.get("datasets", []):
            path = d.get("path", "").replace("\\", "/")
            name = Path(path).name
            info = {"sha256": d.get("sha256"), "size_bytes": d.get("size_bytes")}
            fixtures[name] = info
            group = sanitize_stem(path.split("/", 1)[0]).lower() if "/" in path else ""
            stem_key = sanitize_stem(Path(path).stem)
            fixtures_by_group_stem[(group, stem_key)] = info

        runs.append({
            "package": package, "category": category,
            "target": stem.rsplit("_", 1)[0] if "_" in stem else stem,
            "run_id": context.get("ze_run_id") or md.get("run_id") or stem,
            "commit": context.get("ze_git_commit") or md.get("git", {}).get("commit"),
            "data": data, "sidecar": sidecar, "fixtures": fixtures,
            "fixtures_by_group_stem": fixtures_by_group_stem,
            "machine": md.get("machine", {}),
            "build": md.get("build", {}),
        })
    return runs


def benchmark_rows(run: dict) -> list[dict]:
    """Baris tidy dari satu report benchmark google-benchmark ze_json."""
    rows: list[dict] = []
    machine = run.get("machine", {})
    build = run.get("build", {})
    cpu = short_device(machine.get("cpu_model", "?"))
    fixtures = run.get("fixtures", {})
    fixtures_gs = run.get("fixtures_by_group_stem", {})

    # Kumpulkan entri per benchmark: agregat (mean/median/stddev/cv) atau
    # sampel tunggal. Dengan --benchmark_report_aggregates_only, field `name`
    # agregat diberi suffix _mean/_median/... — kunci grouping yang benar
    # adalah `run_name` (nama benchmark dasar).
    grouped: dict[str, dict[str, dict]] = defaultdict(dict)
    singles: list[dict] = []
    for b in run["data"].get("benchmarks", []):
        agg = b.get("aggregate_name")
        key = b.get("run_name") or b["name"]
        if agg:
            grouped[key][agg] = b
        else:
            singles.append(b)

    def fixture_info(benchmark_name: str) -> tuple[str, dict | None]:
        m = CORPUS_RE.match(benchmark_name)
        if m:
            group, stem = m.group(1), m.group(2)
            # run_name google-benchmark memuat suffix parameter
            # (/min_time:15.000/min_warmup_time:5.000) — buang agar stem
            # cocok dengan stem manifest (sanitasi sama dgn main.cpp).
            stem = re.split(r"/min_time", stem)[0]
            # stem di nama benchmark sudah sanitasi; cocokkan dgn manifest.
            return stem, fixtures_gs.get((group, stem))
        fixture = guess_fixture(benchmark_name)
        return (fixture or ""), fixtures.get(fixture) if fixture else None

    def emit(b: dict, fixture: str, info: dict | None, aggregate: str,
             base: dict, stddev: dict) -> None:
        rows.append({
            "package": run["package"], "target": run["target"],
            "run_id": run["run_id"], "commit": run["commit"] or "",
            "device_cpu": cpu,
            "device_cores": machine.get("logical_cores", ""),
            "os": machine.get("os_version", ""),
            "build_type": build.get("build_type", "") or b.get("context", {}).get("ze_build_type", ""),
            "library_version": build.get("library_version_number", ""),
            "benchmark": b["name"], "fixture": fixture,
            "fixture_sha256": (info or {}).get("sha256") or "",
            "aggregate": aggregate,
            "time_unit": base.get("time_unit", "ns"),
            "p50_cpu_time": base.get("cpu_time", ""),
            "p50_real_time": base.get("real_time", ""),
            "stddev_real_time": stddev.get("real_time", "") if stddev else "",
            "repetitions": base.get("repetitions", 1),
            "bytes_per_second": base.get("bytes_per_second", ""),
        })

    for b in singles:
        fixture, info = fixture_info(b["name"])
        emit(b, fixture, info, "single", b, None)

    for name, aggs in sorted(grouped.items()):
        fixture, info = fixture_info(name)
        mean = aggs.get("mean", {})
        median = aggs.get("median", {})
        stddev = aggs.get("stddev", {})
        base = median or mean
        if not base:
            continue  # hanya stddev/cv tanpa mean/median — tak ada P50
        aggregate = "median+mean" if median and mean else ("median" if median else "mean")
        emit(base, fixture, info, aggregate, base, stddev)
        # Nama benchmark tampil = nama dasar (tanpa suffix agregat).
        rows[-1]["benchmark"] = name
    return rows


def saqreport_rows(run: dict) -> list[dict]:
    """Baris tidy dari satu report saq-report (JSON.parse baseline)."""
    rows: list[dict] = []
    meta = run["data"].get("metadata", {})
    runtime = meta.get("runtime", {})
    cpu = short_device(runtime.get("cpu_model", "?"))
    for result in run["data"].get("results", []):
        if result.get("status") != "success":
            continue
        measurement = (result.get("measurements", {}) or {}).get("parse-only")
        if not measurement or measurement.get("skipped"):
            continue
        latency = measurement.get("latency", {})
        throughput = measurement.get("throughput", {})
        elapsed_ns = measurement.get("total_elapsed_ns") or 0
        payload = result.get("payload", {})
        rows.append({
            "package": "saq-report", "target": run["target"],
            "run_id": run["run_id"], "commit": run["commit"] or "",
            "device_cpu": cpu,
            "device_cores": runtime.get("logical_cores", ""),
            "os": (meta.get("environment", {}) or {}).get("os_release", ""),
            "build_type": "node-" + str(runtime.get("node_version", "")),
            "library_version": meta.get("benchmark_version", ""),
            "benchmark": "JSON.parse/parse-only",
            "fixture": Path(result.get("file", "")).stem,
            "fixture_sha256": payload.get("sha256", ""),
            "aggregate": "median+ci95",
            "time_unit": "ns",
            "p50_cpu_time": latency.get("median_ns", ""),
            "p50_real_time": latency.get("median_ns", ""),
            "stddev_real_time": latency.get("stddev_ns", ""),
            "repetitions": measurement.get("samples") and len(measurement["samples"]) or "",
            "bytes_per_second": (throughput.get("data_processed_bytes") / (elapsed_ns / 1e9))
                                if elapsed_ns else "",
        })
    return rows


CSV_FIELDS = [
    "package", "target", "run_id", "commit", "device_cpu", "device_cores", "os",
    "build_type", "library_version", "benchmark", "fixture", "fixture_sha256",
    "aggregate", "time_unit", "p50_cpu_time", "p50_real_time", "stddev_real_time",
    "repetitions", "bytes_per_second",
]


def write_csv(rows: list[dict], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def fmt_ns(value, unit="ns") -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "-"
    if unit == "ns":
        if v >= 1e6:
            return f"{v / 1e6:.2f} ms"
        if v >= 1e3:
            return f"{v / 1e3:.1f} us"
        return f"{v:.1f} ns"
    return f"{v:.3f} {unit}"


def fmt_gbs(value) -> str:
    try:
        return f"{float(value) / 1e9:.2f} GB/s"
    except (TypeError, ValueError):
        return "-"


def device_label(rows_for_target: list[dict]) -> str:
    cpus = sorted({r["device_cpu"] for r in rows_for_target})
    cores = sorted({str(r["device_cores"]) for r in rows_for_target}, key=lambda s: (len(s), s))
    return f"{cpus[0] if cpus else '?'} ({cores[0] if cores else '?'} core)"


def write_summary(rows: list[dict], runs: list[dict], out_md: Path) -> None:
    bench_rows = [r for r in rows if r["package"] == "ze_json"]
    saq_rows = [r for r in rows if r["package"] == "saq-report"]
    test_runs = [r for r in runs if r["category"] == "test"]
    lines: list[str] = []
    lines.append("# Ringkasan benchmark ze_json + saq-report\n")
    lines.append(f"Sumber: `{out_md.parent}` — dihasilkan otomatis oleh "
                 "`research/analyze_benchmarks.py`. Angka hanya sah untuk "
                 "fixture sha256 yang tercantum (docs/telemetry-sidecar.md).\n")

    # Konteks device per run.
    lines.append("## Konteks device\n")
    seen: set[tuple[str, str]] = set()
    for r in rows:
        key = (r["run_id"], r["device_cpu"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- `{r['run_id']}` ({r['package']}) — commit `{r['commit'] or '?'}` — "
                     f"{r['device_cpu']} ({r['device_cores']} core) — {r['os']} — "
                     f"build {r['build_type'] or '?'}, library {r['library_version'] or '?'}")
    lines.append("")

    # Tabel per target ze_json.
    by_target: dict[str, list[dict]] = defaultdict(list)
    for r in bench_rows:
        by_target[r["target"]].append(r)

    for target in sorted(by_target):
        rows_t = by_target[target]
        devices = {r["device_cpu"] for r in rows_t}
        lines.append(f"## {target} — {device_label(rows_t)}\n")
        lines.append("| Benchmark | Fixture | P50 | Throughput | Repetisi |")
        lines.append("|---|---|---|---|---|")
        for r in sorted(rows_t, key=lambda x: x["benchmark"]):
            lines.append(
                f"| `{r['benchmark']}` | {r['fixture'] or '-'} | "
                f"{fmt_ns(r['p50_real_time'], r['time_unit'])} | "
                f"{fmt_gbs(r['bytes_per_second'])} | {r['repetitions']} |")
        lines.append("")

        # Perbandingan lintas-device bila ada >1 device untuk kombinasi
        # (benchmark, fixture_sha256) yang identik.
        if len(devices) > 1:
            grouped: dict[tuple, dict[str, dict]] = defaultdict(dict)
            for r in rows_t:
                grouped[(r["benchmark"], r["fixture_sha256"])][r["device_cpu"]] = r
            comparisons = {k: v for k, v in grouped.items() if len(v) > 1}
            if comparisons:
                lines.append(f"### Perbandingan lintas-device ({len(comparisons)} pasangan joinable)\n")
                lines.append("| Benchmark | Device A | Device B | Rasio P50 |")
                lines.append("|---|---|---|---|")
                for (bench, sha), bydev in sorted(comparisons.items()):
                    devs = sorted(bydev)
                    a, b = bydev[devs[0]], bydev[devs[1]]
                    try:
                        ratio = float(b["p50_real_time"]) / float(a["p50_real_time"])
                        ratio_s = f"{ratio:.2f}x"
                    except (TypeError, ValueError, ZeroDivisionError):
                        ratio_s = "-"
                    lines.append(f"| `{bench}` | {fmt_ns(a['p50_real_time'], a['time_unit'])} "
                                 f"({devs[0][:18]}) | {fmt_ns(b['p50_real_time'], b['time_unit'])} "
                                 f"({devs[1][:18]}) | {ratio_s} |")
                lines.append("")

    # ------------------------------------------------------------------
    # Perbandingan lintas-PAKET: ze_json scanner64 (corpus_benchmark) vs
    # JSON.parse saq-report — join per fixture sha256 identik.
    # ------------------------------------------------------------------
    corpus_ze = [r for r in bench_rows if CORPUS_RE.match(r["benchmark"])]
    saq_parse = [r for r in saq_rows if r["benchmark"] == "JSON.parse/parse-only"]
    if corpus_ze and saq_parse:
        by_sha_ze: dict[str, dict] = {}
        for r in corpus_ze:
            if r["fixture_sha256"]:
                # Bila lintas-device, ambil device terbaru (run_id terbesar).
                by_sha_ze.setdefault(r["fixture_sha256"], r)
        by_sha_saq: dict[str, dict] = {}
        for r in saq_parse:
            if r["fixture_sha256"]:
                by_sha_saq.setdefault(r["fixture_sha256"], r)

        joined = sorted(
            (sha for sha in by_sha_ze if sha in by_sha_saq),
            key=lambda sha: by_sha_ze[sha]["fixture"],
        )
        lines.append("## Lintas-paket — ze_json scanner64 vs JSON.parse (korpus terpadu)\n")
        lines.append(f"Join: fixture sha256 identik ({len(joined)} fixture dari korpus "
                     "terpadu $SAMPLE). P50 = median antar-repetisi (ze_json) / median "
                     "antar-sampel (saq-report). Rasio = P50 JSON.parse ÷ P50 scanner64 "
                     "(>1 berarti ze_json lebih cepat).\n")
        if joined:
            lines.append("| Fixture | ze_json scanner64 | JSON.parse (Node) | Rasio |")
            lines.append("|---|---|---|---|")
            for sha in joined:
                ze = by_sha_ze[sha]
                saq = by_sha_saq[sha]
                try:
                    ratio = float(saq["p50_real_time"]) / float(ze["p50_real_time"])
                    ratio_s = f"{ratio:.2f}x"
                except (TypeError, ValueError, ZeroDivisionError):
                    ratio_s = "-"
                lines.append(
                    f"| {ze['fixture']} | {fmt_ns(ze['p50_real_time'], ze['time_unit'])} "
                    f"({fmt_gbs(ze['bytes_per_second'])}) | "
                    f"{fmt_ns(saq['p50_real_time'], saq['time_unit'])} "
                    f"({fmt_gbs(saq['bytes_per_second'])}) | {ratio_s} |")
            lines.append("")
        else:
            lines.append("_Belum ada pasangan joinable — pastikan kedua paket dijalankan "
                         "di korpus terpadu yang sama (runner research/run_benchmarks.*)._ \n")

    # Test reports (correctness record).
    if test_runs:
        lines.append("## Test (correctness record)\n")
        lines.append("| Target | Run ID | Tests | Failures |")
        lines.append("|---|---|---|---|")
        for run in sorted(test_runs, key=lambda x: x["target"]):
            data = run["data"]
            lines.append(f"| {run['target']} | `{run['run_id']}` | "
                         f"{data.get('tests', '?')} | {data.get('failures', '?')} |")
        lines.append("")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analisa benchmark ze_json + saq-report")
    parser.add_argument("--raw", type=Path, default=None, help="Folder $RAW (default: env RAW)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Folder output (default: research/out)")
    args = parser.parse_args()

    raw_dir = args.raw or Path(os.environ.get("RAW", ""))
    if not raw_dir.is_dir():
        print(f"$RAW tidak valid: {raw_dir}")
        return 2
    out_dir = args.out or Path(__file__).resolve().parent / "out"

    runs = load_keep_runs(raw_dir)
    rows: list[dict] = []
    for run in runs:
        if run["category"] != "benchmark":
            continue
        if run["package"] == "ze_json":
            rows.extend(benchmark_rows(run))
        elif run["package"] == "saq-report":
            rows.extend(saqreport_rows(run))

    if not rows:
        print("Tidak ada baris benchmark — jalankan audit_raw.py dulu.")
        return 1

    write_csv(rows, out_dir / "benchmarks.csv")
    write_summary(rows, runs, out_dir / "summary.md")
    print(f"CSV : {out_dir / 'benchmarks.csv'} ({len(rows)} baris)")
    print(f"MD  : {out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
