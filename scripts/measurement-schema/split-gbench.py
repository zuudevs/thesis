#!/usr/bin/env python3
"""split-gbench.py — split a multi-corpus google-benchmark JSON into per-corpus
raw exhibits + converter arguments (P1-6 onward).

A single benchmark session covers several corpora (synthetic ladder, SAQ
stores, checker batch) but the measurement record schema holds exactly ONE
corpus object per record (docs/project/plans.md section 3). This tool partitions the raw
google-benchmark rows by corpus label, writes one raw exhibit per corpus to
the run's exhibit directory, and emits `convert_args.json` so the converter
step (convert-gbench.py) can build one validated record per corpus with
run-identical metadata.

Label-to-corpus resolution: benchmark names look like
`BM_<Family>/<label>`; the corpus directory defaults to the label itself and
can be remapped with `--label <label>=<corpus_dir_name>` (e.g.
`saq=saq_payload_v1`). Corpus metadata (document_count, total_bytes,
max_document_bytes, manifest sha256) is read from the corpus MANIFEST.json —
never recomputed here, so provenance stays single-sourced.

Usage:
    python scripts/measurement-schema/split-gbench.py <gbench.json> \
        --out-dir out/raw/<run_id> [--label saq=saq_payload_v1 ...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = ROOT / "corpus" / "benchmarks"


def label_of(row: dict) -> str | None:
    name = row.get("run_name") or row.get("name") or ""
    parts = name.split("/")
    return parts[1] if len(parts) > 1 else None


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gbench", help="raw google-benchmark JSON from one session")
    ap.add_argument("--out-dir", required=True,
                    help="exhibit directory, e.g. out/raw/<run_id>")
    ap.add_argument("--label", action="append", default=[],
                    metavar="LABEL=CORPUS",
                    help="map a benchmark label to a corpus directory name")
    args = ap.parse_args(argv)

    try:
        gbench = json.loads(Path(args.gbench).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL unreadable gbench input: {exc}", file=sys.stderr)
        return 1

    rows = gbench.get("benchmarks") or []
    if not rows:
        print("FAIL gbench has no benchmarks[]", file=sys.stderr)
        return 1

    mapping: dict[str, str] = {}
    for item in args.label:
        if "=" not in item:
            print(f"FAIL --label expects LABEL=CORPUS, got {item!r}", file=sys.stderr)
            return 1
        key, value = item.split("=", 1)
        mapping[key] = value

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        label = label_of(row)
        if label is None:
            continue
        grouped.setdefault(label, []).append(row)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    convert_args: dict[str, dict] = {}
    print(f"{'label':<14} {'corpus':<16} {'rows':<5} {'docs':<5} "
          f"{'bytes':<10} corpus_sha256")
    for label in sorted(grouped):
        corpus_name = mapping.get(label, label)
        manifest_path = CORPUS_ROOT / corpus_name / "MANIFEST.json"
        if not manifest_path.exists():
            print(f"FAIL corpus manifest not found for label {label!r} "
                  f"({manifest_path})", file=sys.stderr)
            return 1
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        exhibit_path = out_dir / f"{label}_gbench.json"
        exhibit = {
            "context": gbench.get("context", {}),
            "benchmarks": grouped[label],
        }
        exhibit_path.write_text(
            json.dumps(exhibit, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")

        manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        convert_args[label] = {
            "gbench_file": str(exhibit_path),
            "corpus_name": corpus_name,
            "document_count": manifest["document_count"],
            "total_bytes": manifest["total_bytes"],
            "max_document_bytes": manifest.get("max_document_bytes"),
            "corpus_sha256": manifest_sha,
        }
        print(f"{label:<14} {corpus_name:<16} {len(grouped[label]):<5} "
              f"{manifest['document_count']:<5} "
              f"{manifest['total_bytes']:<10} {manifest_sha[:16]}...")

    args_path = out_dir / "convert_args.json"
    args_path.write_text(json.dumps(convert_args, indent=2) + "\n", encoding="utf-8")
    print(f"\n[+] {len(convert_args)} corpus exhibit(s) -> {out_dir}")
    print(f"[+] converter arguments -> {args_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
