#!/usr/bin/env python3
"""convert-gbench.py — raw Google Benchmark JSON -> measurement record v1.

Usage:
    python scripts/measurement-schema/convert-gbench.py <gbench.json> --out <record.json> \\
        --host <host.json-from-host-introspect> \\
        --git-commit <short-hash> [--dirty] --repo ze_json \\
        --corpus-name <name> --document-count N --total-bytes N --corpus-sha256 <64hex> \\
        [--max-document-bytes N] \\
        [--library ze_json|saq_baseline] [--library-version 0.1.0] [--language-runtime ...] \\
        [--engine simd|scalar|v8|wasm64_cabi] [--preset native-release] \\
        [--run-id ...] [--warmup-runs N] [--threads N] [--cpu-pinning] \\
        --purpose "<why this measurement exists>" \\
        --basis-papers <DOI>[,<DOI>...]

Guarantees (per AGENTS.md section 4):
- rationale is REQUIRED (purpose >= 12 chars, >= 1 DOI); converter refuses to emit
  a record that would fail schema validation;
- after assembly the record is validated against schemas/measurement.schema.json;
  the output file is written only when validation PASSes (exit 0), otherwise exit 1
  and nothing is written.
"""

from __future__ import annotations

import argparse
import json
import socket
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "measurement.schema.json"

# nanoseconds per gbench time_unit
TIME_TO_NS = {"ns": 1.0, "us": 1e3, "ms": 1e6, "s": 1e9}
ENGINES = ("scalar", "simd", "v8", "wasm64_cabi")


def _num(row: dict, key: str):
    val = row.get(key)
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    return None


def _seconds(row: dict, key: str) -> float | None:
    unit = row.get("time_unit", "ns")
    scale = TIME_TO_NS.get(unit)
    if scale is None:
        return None
    val = _num(row, key)
    if val is None:
        return None
    return val * scale * 1e-9


def _family_rows(benchmarks: list[dict]):
    raw: dict[str, list[dict]] = {}
    agg: dict[str, dict[str, dict]] = {}
    for row in benchmarks:
        run_name = row.get("run_name") or row["name"]
        if row.get("run_type") == "aggregate":
            agg.setdefault(run_name, {})[row.get("aggregate_name", "none")] = row
        else:
            raw.setdefault(run_name, []).append(row)
    return raw, agg


def _spread_value(rows: list[dict], aggs: dict[str, dict], key: str):
    """Family-constant value: prefer median/mean aggregate row, else raw median."""
    for agg_name in ("median", "mean"):
        if agg_name in aggs:
            val = _num(aggs[agg_name], key)
            if val is not None:
                return val
    vals = [v for v in (_num(r, key) for r in rows) if v is not None]
    return statistics.median(vals) if vals else None


def _seconds_stats(ok_rows: list[dict], aggs: dict[str, dict], key: str):
    """Returns (seconds stats). Preferred: median/mean aggregate; fallback: raw median."""
    seconds = [s for s in (_seconds(r, key) for r in ok_rows) if s is not None]
    best = None
    for agg_name in ("median", "mean"):
        if agg_name in aggs:
            val = _seconds(aggs[agg_name], key)
            if val is not None:
                best = val
                break
    mean = best if best is not None else (statistics.median(seconds) if seconds else None)

    stddev = None
    if "stddev" in aggs:
        stddev = _seconds(aggs["stddev"], key)
    if stddev is None and len(seconds) >= 2:
        stddev = statistics.stdev(seconds)
    return mean, stddev


def _result_for_name(row_name: str, raws: list[dict], aggs: dict[str, dict],
                     engine_default: str, purpose: dict) -> dict:
    ok_rows = [r for r in raws if not r.get("error_occurred")]
    error_seen = (len(ok_rows) != len(raws)) or bool(ok_rows[0].get("error_occurred"))

    seconds_mean, seconds_stddev = _seconds_stats(ok_rows, aggs, "real_time")

    metrics: dict = {}
    if seconds_mean is not None:
        metrics["seconds_mean"] = seconds_mean
    if seconds_stddev is not None:
        metrics["seconds_stddev"] = seconds_stddev
    for key in ("bytes_per_second", "items_per_second"):
        val = _spread_value(ok_rows, aggs, key)
        if val is not None:
            metrics[key] = val
    cpu_vals = [s for s in (_seconds(r, "cpu_time") for r in ok_rows) if s is not None]
    if cpu_secs_mean := (statistics.mean(cpu_vals) if cpu_vals else None):
        metrics["cpu_seconds"] = cpu_secs_mean

    engine = "scalar" if "scalar" in row_name.lower() else engine_default

    iterations = [int(r["iterations"]) for r in raws if isinstance(r.get("iterations"), int)]
    return {
        "name": row_name,
        "engine": engine,
        "status": "fail" if error_seen else "ok",
        "rationale": purpose,
        "metrics": metrics,
        "extras": {},
        "_iterations": max(iterations) if iterations else None,
    }


def _all_rows(raw: dict) -> list[dict]:
    rows: list[dict] = []
    for family_rows in raw.values():
        rows.extend(family_rows)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gbench")
    ap.add_argument("--out", required=True)
    ap.add_argument("--host", required=True,
                    help="host.json produced by scripts/host-introspect.mjs")
    ap.add_argument("--run-id")
    ap.add_argument("--git-commit", required=True)
    ap.add_argument("--repo", default="ze_json", choices=["v5", "ze_json", "saq_report"])
    ap.add_argument("--dirty", action="store_true")
    ap.add_argument("--site", default="dev_device", choices=["dev_device", "saq_server"])
    ap.add_argument("--library", default="ze_json", choices=["ze_json", "saq_baseline"])
    ap.add_argument("--library-version", default="0.1.0")
    ap.add_argument("--language-runtime", default="C++23 clang 23.1.5 (native-release)")
    ap.add_argument("--engine", default="simd", choices=list(ENGINES))
    ap.add_argument("--generator", default="google_benchmark",
                    choices=["google_benchmark", "gtest", "node_harness"])
    ap.add_argument("--preset", default=None,
                    help="recorded into config.notes (e.g. preset=native-release)")
    ap.add_argument("--corpus-name", required=True)
    ap.add_argument("--document-count", type=int, required=True)
    ap.add_argument("--total-bytes", type=int, required=True)
    ap.add_argument("--max-document-bytes", type=int)
    ap.add_argument("--corpus-sha256", required=True,
                    help="sha256 hex (64) of the corpus MANIFEST.json")
    ap.add_argument("--warmup-runs", type=int, default=0)
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--cpu-pinning", action="store_true")
    ap.add_argument("--purpose", required=True, help="rationale purpose (why this measurement)")
    ap.add_argument("--basis-papers", required=True,
                    help="comma separated DOI list, e.g. 10.1002_spe.3313,10.1145_3448016.3452809")
    args = ap.parse_args()

    purpose_text = args.purpose.strip()
    if len(purpose_text) < 12:
        print("FAIL rationale.purpose must be >= 12 characters; no record written",
              file=sys.stderr)
        return 1
    basis_papers = [s.strip() for s in args.basis_papers.split(",") if s.strip()]
    if not basis_papers:
        print("FAIL rationale.basis_papers must contain at least one DOI; no record written",
              file=sys.stderr)
        return 1
    rationale = {"purpose": purpose_text, "basis_papers": basis_papers}

    try:
        gbench = json.loads(Path(args.gbench).read_text(encoding="utf-8"))
        host = json.loads(Path(args.host).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL input read: {exc}", file=sys.stderr)
        return 1

    benchmarks = gbench.get("benchmarks") or []
    if not benchmarks:
        print("FAIL gbench has empty benchmarks[]", file=sys.stderr)
        return 1

    raw, agg = _family_rows(benchmarks)
    results = [
        _result_for_name(run_name, raw[run_name], agg.get(run_name, {}),
                         args.engine, rationale)
        for run_name in raw
    ]

    all_rows = _all_rows(raw)
    repeats = max(
        (int(r.get("repetitions", 1)) for r in all_rows if isinstance(r.get("repetitions"), int)),
        default=1,
    )
    iterations = max(
        (int(e["_iterations"] or 1) for e in results),
        default=1,
    )
    threads = args.threads or max(
        (int(r.get("threads", 1)) for r in all_rows if isinstance(r.get("threads"), int)),
        default=1,
    )

    now = datetime.now(timezone.utc)
    date_utc = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = args.run_id or (
        f"{socket.gethostname()}-{now.strftime('%Y%m%d%H%M%S')}-{args.git_commit}"
    )

    notes_parts = [f"source={Path(args.gbench).name}"]
    if args.preset:
        notes_parts.append(f"preset={args.preset}")

    record = {
        "schema_version": "1.0.0",
        "kind": "benchmark",
        "run_id": run_id,
        "site": args.site,
        "generator": args.generator,
        "library": {
            "name": args.library,
            "version": args.library_version,
            "language_runtime": args.language_runtime,
        },
        "git_commit": {"hash": args.git_commit, "dirty": bool(args.dirty), "repo": args.repo},
        "host": host,
        "corpus": {
            "name": args.corpus_name,
            "document_count": args.document_count,
            "total_bytes": args.total_bytes,
            **({"max_document_bytes": args.max_document_bytes} if args.max_document_bytes else {}),
            "sha256": args.corpus_sha256,
        },
        "config": {
            "date_utc": date_utc,
            "iterations": iterations,
            "warmup_runs": args.warmup_runs,
            "repeats": repeats,
            "cpu_pinning": bool(args.cpu_pinning),
            "threads": threads,
            "notes": "; ".join(notes_parts),
        },
        "results": [
            {
                "name": e["name"],
                "engine": e["engine"],
                "status": e["status"],
                "rationale": e["rationale"],
                "metrics": e["metrics"],
                "extras": e["extras"],
            }
            for e in results
        ],
    }

    out_path = Path(args.out).resolve()
    errors = validate(record, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")), "$")
    if errors:
        print("FAIL record validation; nothing written:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS {len(record['results'])} result(s) -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
