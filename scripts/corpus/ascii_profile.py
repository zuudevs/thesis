#!/usr/bin/env python3
"""ascii_profile - byte-class profile of the measurement corpora (P4-3).

Counts the share of non-ASCII bytes (>= 0x80) and backslash bytes (0x5C,
escape source) per corpus document. Document lists come from each corpus
MANIFEST.json (provenance: same file list the harnesses measure), never a
raw glob - MANIFEST.json itself is not a measurement document.

Purpose: P4-3 C3 closure evidence. `utf8_seq_advance` (src/ondemand/
string.cpp) only fires on multi-byte leads, and scanner8's interior loop
treats backslash as an escape trigger - both are ~absent from the measured
workloads, which bounds any table/SIMD UTF-8 or escape fast path to ~zero
gain on these corpora.

Usage (stdlib only):
    python scripts/corpus/ascii_profile.py                # all corpora
    python scripts/corpus/ascii_profile.py saq_payload_v1 # one corpus
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "corpus" / "benchmarks"


def profile_corpus(corpus_dir: Path) -> dict:
    manifest = json.loads((corpus_dir / "MANIFEST.json").read_text("utf-8"))
    total = nonascii = backslash = 0
    for doc in manifest["documents"]:
        data = (corpus_dir / doc["file"]).read_bytes()
        if len(data) != doc["bytes"]:  # provenance guard: manifest must match
            raise SystemExit(f"byte-count mismatch: {doc['file']} "
                             f"(manifest {doc['bytes']}, disk {len(data)})")
        total += len(data)
        nonascii += sum(1 for b in data if b >= 0x80)
        backslash += data.count(0x5C)
    return {
        "name": manifest["corpus_name"],
        "docs": manifest["document_count"],
        "total": total,
        "nonascii": nonascii,
        "backslash": backslash,
    }


def main() -> None:
    names = sys.argv[1:]
    dirs = ([BENCH / n for n in names] if names
            else sorted(p for p in BENCH.iterdir()
                        if (p / "MANIFEST.json").exists()))
    rows = [profile_corpus(d) for d in dirs]
    print(f"{'corpus':<18} {'docs':>4} {'bytes':>10} {'nonASCII':>9} "
          f"{'%':>7} {'backslash':>9} {'%':>7}")
    for r in rows:
        na = r["nonascii"] / r["total"] * 100
        bs = r["backslash"] / r["total"] * 100
        print(f"{r['name']:<18} {r['docs']:>4} {r['total']:>10} "
              f"{r['nonascii']:>9} {na:>6.3f}% {r['backslash']:>9} "
              f"{bs:>6.3f}%")


if __name__ == "__main__":
    main()
