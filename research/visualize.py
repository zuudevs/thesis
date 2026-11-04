#!/usr/bin/env python3
# ============================================================================
#  visualize.py — 5 chart bermakna dari benchmarks.csv (SVG + PDF vector)
# ============================================================================
#  Semua chart regenerate dari research/out/benchmarks.csv (hasil
#  analyze_benchmarks.py). Saat data server SAQ sudah ada (device kedua di
#  CSV), chart otomatis menampilkan kelompok per-device tanpa perubahan kode.
#
#  Chart:
#    1. throughput_by_fixture   — GB/s per fixture (scanner64 vs GRAM base)
#    2. span_hybrid_vs_prehybrid — paired bar per dataset nyata (H1/H2)
#    3. scanner8_vs_64          — efek lebar SIMD per fixture
#    4. gram_base_vs_tapewalk   — isolasi biaya tulis tape
#    5. perf_vs_size            — throughput vs ukuran dataset (log-log)
#    6. cross_package           — ze_json scanner64 vs JSON.parse per fixture
#                                  korpus terpadu (join sha256; chart inti)
# ============================================================================
from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "out"
TIME_TO_NS = {"ns": 1.0, "us": 1e3, "ms": 1e6, "s": 1e9}
# Nama benchmark corpus_benchmark: BM_Corpus_Scanner64_<grup>_<fixture>
CORPUS_RE = re.compile(r"^BM_Corpus_Scanner64_(json_checker|commons|saq_report)_(.+)$")


def load_rows() -> list[dict]:
    csv_path = OUT_DIR / "benchmarks.csv"
    if not csv_path.is_file():
        print("benchmarks.csv tidak ada — jalankan analyze_benchmarks.py dulu.")
        sys.exit(1)
    with open(csv_path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def short_fixture(fixture: str) -> str:
    return fixture.replace(".json", "").replace("-", "_") if fixture else "synthetic"


def short_bench(name: str) -> str:
    """Buang suffix parameter google-benchmark (…/min_time:15.000/...)."""
    return name.split("/")[0]


def device_tag(rows: list[dict]) -> str:
    cpus = sorted({r["device_cpu"] for r in rows})
    return cpus[0] if len(cpus) == 1 else f"{len(cpus)} device"


def save(fig, name: str) -> None:
    for ext in ("svg", "pdf"):
        fig.savefig(OUT_DIR / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    print(f"  {name}.svg + .pdf")


def gbps(value: str) -> float | None:
    try:
        return float(value) / 1e9
    except (TypeError, ValueError):
        return None


def p50_ns(row: dict) -> float | None:
    try:
        return float(row["p50_real_time"]) * TIME_TO_NS.get(row["time_unit"], 1.0)
    except (TypeError, ValueError, KeyError):
        return None


# ---------------------------------------------------------------- chart 1
def chart_throughput_by_fixture(rows: list[dict]) -> None:
    """GB/s per fixture nyata — scanner64 vs GRAM base (pipeline inti)."""
    picks: dict[str, dict[str, float]] = defaultdict(dict)
    for r in rows:
        bench = short_bench(r["benchmark"])
        val = gbps(r["bytes_per_second"])
        if val is None:
            continue
        m64 = re.match(r"BM_Scanner64_(\w+)$", bench)
        if m64:
            picks[m64.group(1).lower()]["scanner64"] = max(
                picks[m64.group(1).lower()].get("scanner64", 0), val)
        mgram = re.match(r"BM_GRAM_Base_(\w+)$", bench)
        if mgram:
            picks[mgram.group(1).lower()]["gram_base"] = val
    items = sorted((f, v) for f, v in picks.items()
                   if "scanner64" in v or "gram_base" in v)
    if not items:
        print("  (chart 1 dilewati — tidak ada data scanner64/GRAM base)")
        return
    fixtures = [f for f, _ in items]
    s64 = [v.get("scanner64", 0) for _, v in items]
    gram = [v.get("gram_base", 0) for _, v in items]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(fixtures))
    w = 0.38
    ax.bar([i - w / 2 for i in x], s64, w, label="scanner64")
    ax.bar([i + w / 2 for i in x], gram, w, label="GRAM base (parse+type)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(fixtures, rotation=30, ha="right")
    ax.set_ylabel("Throughput (GB/s)")
    ax.set_title(f"Throughput per fixture — {device_tag(rows)}")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    save(fig, "throughput_by_fixture")


# ---------------------------------------------------------------- chart 2
def chart_span_hybrid(rows: list[dict]) -> None:
    """Paired bar Hybrid vs PreHybrid per dataset nyata (span_iso)."""
    picks: dict[str, dict[str, float]] = defaultdict(dict)
    for r in rows:
        bench = short_bench(r["benchmark"])
        m = re.match(r"BM_SpanReal_(Hybrid|PreHybrid)_(\w+)$", bench)
        if not m:
            continue
        val = gbps(r["bytes_per_second"])
        if val is not None:
            picks[m.group(2)][m.group(1)] = val
    if not picks:
        print("  (chart 2 dilewati — tidak ada data SpanReal)")
        return
    datasets = sorted(picks)
    hybrid = [picks[d].get("Hybrid", 0) for d in datasets]
    pre = [picks[d].get("PreHybrid", 0) for d in datasets]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(datasets))
    w = 0.38
    ax.bar([i - w / 2 for i in x], hybrid, w, label="scanner64 (span hybrid)")
    ax.bar([i + w / 2 for i in x], pre, w, label="replika pra-hybrid")
    ax.set_xticks(list(x))
    ax.set_xticklabels(datasets, rotation=30, ha="right")
    ax.set_ylabel("Throughput (GB/s)")
    ax.set_title("Isolasi biaya span non-string — dataset nyata bersebelahan")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    save(fig, "span_hybrid_vs_prehybrid")


# ---------------------------------------------------------------- chart 3
def chart_scanner_width(rows: list[dict]) -> None:
    """Scanner8 vs Scanner64 per fixture — efek lebar SIMD."""
    picks: dict[str, dict[str, float]] = defaultdict(dict)
    for r in rows:
        bench = short_bench(r["benchmark"])
        m = re.match(r"BM_Scanner(8|64)_(\w+)$", bench)
        if not m:
            continue
        val = gbps(r["bytes_per_second"])
        if val is not None:
            picks[m.group(2)][m.group(1)] = val
    items = sorted((f, v) for f, v in picks.items() if "8" in v and "64" in v)
    if not items:
        print("  (chart 3 dilewati — tidak ada pasangan Scanner8/64)")
        return
    fixtures = [f for f, _ in items]
    s8 = [v.get("8", 0) for _, v in items]
    s64 = [v.get("64", 0) for _, v in items]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(fixtures))
    w = 0.38
    ax.bar([i - w / 2 for i in x], s8, w, label="scanner8")
    ax.bar([i + w / 2 for i in x], s64, w, label="scanner64")
    ax.set_xticks(list(x))
    ax.set_xticklabels(fixtures, rotation=30, ha="right")
    ax.set_ylabel("Throughput (GB/s)")
    ax.set_title("Efek lebar SIMD scanner (8 vs 64 bit)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    save(fig, "scanner8_vs_64")


# ---------------------------------------------------------------- chart 4
def chart_gram(rows: list[dict]) -> None:
    """GRAM base vs tapewalk — biaya tulis tape terisolasi."""
    picks: dict[str, dict[str, float]] = defaultdict(dict)
    for r in rows:
        bench = short_bench(r["benchmark"])
        m = re.match(r"BM_GRAM_(Base|Tapewalk)_(\w+)$", bench)
        if not m:
            continue
        val = gbps(r["bytes_per_second"])
        if val is not None:
            picks[m.group(2)][m.group(1)] = val
    items = sorted((f, v) for f, v in picks.items() if "Base" in v and "Tapewalk" in v)
    if not items:
        print("  (chart 4 dilewati — tidak ada pasangan GRAM)")
        return
    fixtures = [f for f, _ in items]
    base = [v.get("Base", 0) for _, v in items]
    tape = [v.get("Tapewalk", 0) for _, v in items]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(fixtures))
    w = 0.38
    ax.bar([i - w / 2 for i in x], base, w, label="GRAM base (typed access)")
    ax.bar([i + w / 2 for i in x], tape, w, label="GRAM tapewalk")
    ax.set_xticks(list(x))
    ax.set_xticklabels(fixtures, rotation=30, ha="right")
    ax.set_ylabel("Throughput (GB/s)")
    ax.set_title("Biaya tulis tape GRAM — base vs tapewalk")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    save(fig, "gram_base_vs_tapewalk")


# ---------------------------------------------------------------- chart 5
def chart_perf_vs_size(rows: list[dict]) -> None:
    """Log-log throughput vs ukuran dataset (scanner64)."""
    points: dict[tuple[str, str], tuple[float, float]] = {}
    for r in rows:
        bench = short_bench(r["benchmark"])
        m = re.match(r"BM_Scanner(8|64)_(\w+)$", bench)
        if not m:
            continue
        fixture = m.group(2).lower()
        val = gbps(r["bytes_per_second"])
        t = p50_ns(r)
        if val is None or t is None:
            continue
        # size = throughput * time
        size_bytes = val * 1e9 * (t / 1e9)
        points[(m.group(1), fixture)] = (size_bytes, val)
    if not points:
        print("  (chart 5 dilewati — tidak ada titik)")
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    for width in sorted({b for b, _ in points}):
        xs = [v[0] for k, v in points.items() if k[0] == width]
        ys = [v[1] for k, v in points.items() if k[0] == width]
        labels = [k[1] for k, v in points.items() if k[0] == width]
        ax.scatter(xs, ys, s=42, label=f"scanner{width}")
        for x, y, lab in zip(xs, ys, labels):
            ax.annotate(lab, (x, y), fontsize=7, xytext=(4, 3),
                        textcoords="offset points")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Ukuran payload (byte, dari P50 × throughput)")
    ax.set_ylabel("Throughput (GB/s)")
    ax.set_title(f"Throughput vs ukuran payload — {device_tag(rows)}")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    save(fig, "perf_vs_size")


# ---------------------------------------------------------------- chart 6
def chart_cross_package(rows: list[dict]) -> None:
    """ze_json scanner64 (corpus_benchmark) vs JSON.parse — join per sha256."""
    ze: dict[str, dict] = {}   # sha256 -> row (korpus terpadu)
    saq: dict[str, dict] = {}
    for r in rows:
        if not r["fixture_sha256"]:
            continue
        if r["package"] == "ze_json" and CORPUS_RE.match(r["benchmark"]):
            ze.setdefault(r["fixture_sha256"], r)
        elif r["package"] == "saq-report" and r["benchmark"] == "JSON.parse/parse-only":
            saq.setdefault(r["fixture_sha256"], r)
    joined = sorted((sha for sha in ze if sha in saq),
                    key=lambda sha: ze[sha]["fixture"])
    if not joined:
        print("  (chart 6 dilewati — belum ada pasangan lintas-paket joinable)")
        return

    fixtures = [ze[sha]["fixture"] for sha in joined]
    ze_gbs = [gbps(ze[sha]["bytes_per_second"]) or 0 for sha in joined]
    saq_gbs = [gbps(saq[sha]["bytes_per_second"]) or 0 for sha in joined]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(fixtures))
    w = 0.38
    ax.bar([i - w / 2 for i in x], ze_gbs, w, label="ze_json scanner64 (C++)")
    ax.bar([i + w / 2 for i in x], saq_gbs, w, label="JSON.parse (Node V8)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(fixtures, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Throughput (GB/s)")
    ax.set_title(f"Lintas-paket pada korpus terpadu — {device_tag(rows)}")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    save(fig, "cross_package_throughput")


def main() -> int:
    rows = load_rows()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Device: {device_tag(rows)} — {len(rows)} baris benchmark")
    chart_throughput_by_fixture(rows)
    chart_span_hybrid(rows)
    chart_scanner_width(rows)
    chart_gram(rows)
    chart_perf_vs_size(rows)
    chart_cross_package(rows)
    print(f"Selesai. Output: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    main()
