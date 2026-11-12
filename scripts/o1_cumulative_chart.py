#!/usr/bin/env python3
"""o1_cumulative_chart.py — cumulative effect of the O1 optimization cycle.

Compares the ze_json wasm64 full-parse throughput (context
`ze-parser/wasm-parse-full`) BEFORE the O1 cycle (pre-O1 state: binding
`ab09adb` + wasm `7e26044f`, the R5-verdict baseline) against AFTER
(post-O1: `main` `c1c91ce` + wasm `35b7f773`, all six accepted
optimizations), measured back-to-back in ONE dev_device session
(interleaved A/B with a post-O1 control run — B1 and B2 agree within
noise). V8 `JSON.parse` body-parse from the same session is drawn as a
reference line.

Sources (validated schema-v1 records, fresh runs 2026-11-12):
  pre-O1  : out/measurements/zuu-20261112010554-ab09adb_*
  post-O1 : out/measurements/zuu-20261112010545-c1c91ce_* +
            out/measurements/zuu-20261112010605-c1c91ce_*  (median of 2)
  v8 ref  : out/measurements/zuu-20261112010521-0340a72_*

Output: out/charts/o1_cumulative.png (gitignored analysis figure).

Usage: python scripts/o1_cumulative_chart.py [--out out/charts/o1_cumulative.png]
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
def short_corpus(c: str) -> str:
    if c.startswith("synthetic_"):
        return c[len("synthetic_"):]
    if c == "saq_payload_v1":
        return "saq"
    return c


CORPORA = ["synthetic_1k", "synthetic_10k", "synthetic_100k",
           "synthetic_1mb", "saq_payload_v1", "checker_batch"]
CONTEXT = "wasm-parse-full"


def corpus_medians(pattern: str, context: str = CONTEXT) -> dict[str, float]:
    """Median bytes/s per corpus over all matching validated records."""
    per_corpus: dict[str, list[float]] = {}
    for p in sorted(glob.glob(str(ROOT / pattern))):
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        for res in d["results"]:
            parts = res["name"].split("/")
            corpus = d["corpus"]["name"]
            if res["status"] == "ok" and len(parts) == 3 and parts[1] == context:
                per_corpus.setdefault(corpus, []).append(
                    res["metrics"]["bytes_per_second"])
    return {c: sorted(v)[len(v) // 2] for c, v in per_corpus.items()}


def v8_bodyparse(pattern: str) -> dict[str, float]:
    out = {}
    for p in sorted(glob.glob(str(ROOT / pattern))):
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        for res in d["results"]:
            if res["status"] == "ok" and "/body-parse/" in res["name"]:
                out[d["corpus"]["name"]] = res["metrics"]["bytes_per_second"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pre", default="out/measurements/zuu-20261112010554-ab09adb_*_record.json")
    ap.add_argument("--post", nargs="+", default=[
        "out/measurements/zuu-20261112010545-c1c91ce_*_record.json",
        "out/measurements/zuu-20261112010605-c1c91ce_*_record.json"])
    ap.add_argument("--v8", default="out/measurements/zuu-20261112010521-0340a72_*_record.json")
    ap.add_argument("--out", type=Path, default=ROOT / "out" / "charts" / "o1_cumulative.png")
    args = ap.parse_args()

    pre = corpus_medians(args.pre)
    post_vals = [corpus_medians(p) for p in args.post]
    post = {c: sorted([v[c] for v in post_vals])[len(post_vals) // 2]
            for c in CORPORA}
    v8 = v8_bodyparse(args.v8)

    x = list(range(len(CORPORA)))
    width = 0.36
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    ax.set_yscale("log")
    ax.set_ylim(1, 700)

    bars_pre = ax.bar([i - width / 2 for i in x], [pre[c] / 1e6 for c in CORPORA],
                      width, color="#90a4ae", label="pre-O1 (ab09adb + wasm 7e26044f)")
    bars_post = ax.bar([i + width / 2 for i in x], [post[c] / 1e6 for c in CORPORA],
                       width, color="#2e7d32", label="post-O1 (c1c91ce + wasm 35b7f773)")
    ax.plot(x, [v8[c] / 1e6 for c in CORPORA], "D--", color="#1565c0",
            markersize=7, linewidth=1.4, label="V8 JSON.parse body-parse (referensi)")

    for i, c in enumerate(CORPORA):
        ratio = post[c] / pre[c]
        top = post[c] / 1e6
        ax.annotate(f"×{ratio:.2f}", (i + width / 2, top), xytext=(0, 5),
                    textcoords="offset points", ha="center", fontsize=9.5,
                    fontweight="bold", color="#1b5e20")
        ax.annotate(f"{pre[c] / 1e6:.1f}", (i - width / 2, pre[c] / 1e6),
                    xytext=(0, 5), textcoords="offset points", ha="center",
                    fontsize=8, color="#455a64")

    ax.set_xticks(x)
    ax.set_xticklabels([short_corpus(c) for c in CORPORA], fontsize=10)
    ax.set_ylabel("throughput (MB/s, skala log)")
    ax.set_title(
        "Efek Kumulatif Siklus Optimasi O1 — wasm64 full-parse (dev_device, satu sesi)\n"
        "pre-O1 = baseline verdict R5; post-O1 = seluruh 6 optimasi diterima "
        "(median 2 run; kontrol B1≈B2 dalam noise)",
        fontsize=11.5,
    )
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(axis="y", which="both", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150)
    print(f"[+] {args.out}")
    for c in CORPORA:
        print(f"    {c:16s} pre {pre[c]/1e6:6.1f}  post {post[c]/1e6:6.1f}  "
              f"V8 {v8[c]/1e6:6.1f}  ratio ×{post[c]/pre[c]:.2f}")


if __name__ == "__main__":
    main()
