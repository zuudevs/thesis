#!/usr/bin/env python3
"""interior_histogram - string-interior length profile of the corpora (O2-2).

Walks each corpus document with the SAME string state machine scanner8 uses
(open quote -> interior until closing quote, backslash consumes the next
byte) and measures every string interior length. Decision input for O2-2
(SWAR 8-byte interior skip): the byte-weighted median interior length says
whether the byte majority is processed in runs long enough for an 8-byte
block step to pay off (P4-2 lesson: vector loses on short segments —
measure, don't assume).

Reported per corpus (document list from MANIFEST.json, provenance-guarded):
  interiors  - number of string interiors
  bytes      - total interior bytes
  p50/p90/max - count-weighted length distribution
  bw_p50     - BYTE-weighted median interior length (the GO/NO-GO metric)
  ge8_share  - share of interior bytes living in interiors >= 8 bytes

Usage (stdlib only):
    python scripts/corpus/interior_histogram.py [corpus ...]
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "corpus" / "benchmarks"


def interiors(data: bytes):
    """Yield interior lengths with scanner8's exact string state machine."""
    i, n = 0, len(data)
    in_string = False
    start = 0
    while i < n:
        if in_string:
            b = data[i]
            if b == 0x5C:  # escape: next byte is literal
                i += 2
                continue
            if b == 0x22:  # closing quote
                yield i - start
                in_string = False
            i += 1
            continue
        if data[i] == 0x22:  # opening quote
            in_string = True
            i += 1
            start = i
            continue
        i += 1


def pct(sorted_vals, p):
    """Percentile of a pre-sorted list (linear interpolation)."""
    if not sorted_vals:
        return 0.0
    idx = (p / 100) * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (idx - lo) * (sorted_vals[hi] - sorted_vals[lo])


def profile_corpus(corpus_dir: Path):
    manifest = json.loads((corpus_dir / "MANIFEST.json").read_text("utf-8"))
    lens = []
    for doc in manifest["documents"]:
        data = (corpus_dir / doc["file"]).read_bytes()
        if len(data) != doc["bytes"]:
            raise SystemExit(f"byte-count mismatch: {doc['file']}")
        lens.extend(interiors(data))
    lens.sort()
    total_bytes = sum(lens)
    ge8 = sum(v for v in lens if v >= 8)
    # byte-weighted median: the interior length where half the interior
    # BYTES live in shorter runs (cumulative bytes over sorted lengths)
    cum = 0
    bw_p50 = 0
    for v in lens:
        cum += v
        if cum >= total_bytes / 2:
            bw_p50 = v
            break
    return {
        "name": manifest["corpus_name"],
        "interiors": len(lens),
        "bytes": total_bytes,
        "p50": pct(lens, 50),
        "p90": pct(lens, 90),
        "max": max(lens) if lens else 0,
        "bw_p50": bw_p50,
        "ge8_share": ge8 / total_bytes * 100 if total_bytes else 0.0,
    }


def main():
    names = sys.argv[1:]
    dirs = ([BENCH / n for n in names] if names
            else sorted(p for p in BENCH.iterdir()
                        if (p / "MANIFEST.json").exists()))
    print(f"{'corpus':<18} {'ints':>7} {'intBytes':>9} {'p50':>5} {'p90':>5} "
          f"{'max':>6} {'bw_p50':>6} {'>=8B share':>10}")
    for d in dirs:
        r = profile_corpus(d)
        print(f"{r['name']:<18} {r['interiors']:>7} {r['bytes']:>9} "
              f"{r['p50']:>5.0f} {r['p90']:>5.0f} {r['max']:>6} "
              f"{r['bw_p50']:>6} {r['ge8_share']:>9.1f}%")


if __name__ == "__main__":
    main()
