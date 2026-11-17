#!/usr/bin/env python3
"""ND-6 Phase D + ND-11 Phase E research synthesis analysis (read-only).

Recomputes every reported statistic from validator-PASS measurement records
and raw per-round / per-request exhibits, runs round-level paired inference,
and emits CSV tables + Matplotlib figures + provenance metadata. Evidence
files are opened READ-ONLY: this script never mutates records, exhibits,
sidecars, or raw artifacts.

Boundaries compared (descriptive; never pooled across boundaries or sites):
  D (ND-6 phase D, `nd6_bench.mjs --phase D`)  = repository layer:
      baseline repo.read().length vs ze repo.readCount(); the mongo-cache
      canonical-bytes path is the acceptance gate (>=1.5x), the file-store
      path is reported alongside (I/O-bound, historically <1x).
  E (ND-11 phase E, `scripts/bench/nd11_phase_e.mjs`) = HTTP GET /rekap
      end-to-end (Express middleware -> handler -> 4 repo calls -> EJS
      render -> response), byte-identical apps, engine toggle only.

Statistical unit = the measurement round (15 rounds per run; AGENTS S6):
  - Phase E: alternation `(r+k)%2` with PER_ROUND=20 means each round holds
    20 requests TOTAL (10 v8 + 10 ze); n=150/engine, 300 total. Round median
    per engine -> paired ratio R_i = median(T_v8,i) / median(T_ze,i).
  - Phase D: each round value is the mean of `reps` iterations per engine
    path (reps = 2/5/30, harness `dt/reps`) -> R_i from the two round arrays.
    NOTE the ambiguous field name: Phase D record extras `reps_per_round`
    means "reps per engine per round" (2), while Phase E record extras
    `reps_per_round` (= config `iterations` = 20) means "requests per round
    TOTAL across both engines". The protocol column of the inventory CSV
    spells out the disambiguation for every run.
The 300 Phase E requests are NOT independent observations; inference uses
only the 15 round-level paired ratios of a single run.

Inference methods (assumptions stated in outputs):
  - headline speedup per run = median(T_v8,i)/median(T_ze,i) over the 15
    paired rounds (same convention as the harness `speedup_in_run`);
  - 95% CI: paired round-level bootstrap - resample the 15 rounds jointly
    (B=10000, numpy default_rng(seed), percentile interval), statistic =
    median(T_v8*)/median(T_ze*);
  - exact sign test (binomial, two-sided) on round wins R_i > 1;
  - exact Wilcoxon signed-rank (scipy, two-sided) on round differences
    d_i = median(T_v8,i) - median(T_ze,i) [ms]; zero_method='wilcox'
    (zeros dropped; none expected);
  - the median of the per-round ratios R_i (paired_median_ratio) is ALSO
    reported as a descriptive column; it differs from the ratio of medians
    (e.g. dev Phase D 2.850 vs 2.881) and both are labeled explicitly.
Single-run caveat: bootstrap/p-values quantify within-run round variability
only - they say nothing about run-to-run or site-to-site variation.

Reconciliation conventions (never tuned, only reported):
  - harness statistics: stddev = population (ddof=0); p95 = linear
    interpolation (both harnesses, `nd6_bench.mjs` L137-152,
    `nd11_phase_e.mjs`).
    - record stored precision: Phase D `seconds_mean/median/p95` =
    toPrecision(9), `seconds_stddev` = toPrecision(6) (`pushResult`
    L443-452); Phase E stores full float64. Record fields are therefore
    reconciled at relative tolerance 1e-5; exhibit-internal identities
    (`speedup_in_run`) at 1e-9.
  - compression index C = S_D / S_E is descriptive: it divides in-run
    medians from two DIFFERENT measurement boundaries (and different
    saq-report commits); it is not a measured parser-time share.

Exit code 1 on any reconciliation mismatch or validator failure.

@cite 10.1002_spe.3313 (on-demand JSON: boundary & provenance discipline)
@cite 10.14778_3115404.3115416 (Mison: structural index / scan staging)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import scipy
from scipy import stats as sps

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "nd-de-synthesis"  # deterministic SVG ids
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SEED = 20261117          # fixed bootstrap seed (documented, reproducible)
B_BOOT = 10_000          # bootstrap resamples of the 15 round pairs
TOL_RECORD = 1e-5        # record fields: toPrecision(6..9) rounding gives
                         # up to 5e-6 relative error on 6-digit fields
TOL_EXHIBIT = 1e-9       # exhibit-internal identities (full precision)

C_DEV = "#4C72B0"        # dev_device bars/lines
C_DEV2 = "#A1C9F4"       # dev second run (lighter)
C_SRV = "#DD8452"        # saq_server bars/lines
C_RATIO = "#2E7D32"      # paired-ratio overlay
C_V8 = "#9E9E9E"         # v8 grey

# -- evidence registry (all records must PASS the validator) ------------------
# Phase E HTTP runs: (run_id, site, label, evidence class)
PHASE_E = [
    ("zuu-20261116101458-8556513", "dev_device", "dev run 1", "primary"),
    ("zuu-20261116235636-ab255f5", "dev_device", "dev pilot", "pilot"),
    ("zuu-20261117000112-6979e3f", "dev_device", "dev re-run", "primary"),
    ("server-lanjut-20261117003513-530f751", "saq_server", "server", "primary"),
]
# Phase D repository runs: (run_id, site, label, class)
PHASE_D = [
    ("zuu-20261115010155-3376d07", "dev_device", "dev 0.3.1", "supporting"),
    ("zuu-20261115080840-6d87bf3", "dev_device", "dev 0.3.2", "primary"),
    ("server-lanjut-20261116060933-8a1324b", "saq_server", "server 0.3.2", "primary"),
]
# Phase A/B/C exhibits of the primary windows (selective-traversal narrative)
PHASE_ABC = [
    ("zuu-20261115071747-6d87bf3", "A"), ("zuu-20261115075332-6d87bf3", "B"),
    ("zuu-20261115080838-6d87bf3", "C"),
    ("server-lanjut-20261116060843-8a1324b", "A"),
    ("server-lanjut-20261116060900-8a1324b", "B"),
    ("server-lanjut-20261116060915-8a1324b", "C"),
]

D_PAIRS = [  # phase D exhibit path pairs: (label, v8 path, ze path)
    ("mongo-cache", "D-mongo-cache-v8", "D-mongo-cache-ze"),
    ("file-store", "D-file-store-v8", "D-file-store-ze"),
]

INTEGRITY: list[dict] = []
MISMATCHES: list[str] = []


# -- small helpers ------------------------------------------------------------
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def g(v) -> str:
    """Deterministic CSV float formatting (9 significant digits)."""
    return f"{float(v):.9g}"


def locate(basename: str, run_id: str, archive: str) -> tuple[Path, str]:
    """Locate a raw exhibit (out/raw first, then committed archive).

    Returns (path, provenance_source). All existing copies are sha-checked
    against each other (byte- or EOL-normalized) and the result recorded.
    """
    cands = [ROOT / "out/raw" / run_id / basename,
             ROOT / archive / "raw" / run_id / basename]
    existing = [c for c in cands if c.is_file()]
    if not existing:
        raise FileNotFoundError(f"{basename} for {run_id}: no candidate exists")
    status = "single-copy"
    if len(existing) > 1:
        hashes = {sha256_file(c) for c in existing}
        if len(hashes) == 1:
            status = "byte-identical"
        else:
            norm = {hashlib.sha256(c.read_bytes().replace(b"\r\n", b"\n"))
                    .hexdigest() for c in existing}
            status = ("eol-normalized-identical" if len(norm) == 1
                      else "CONTENT-DIFF")
            if status == "CONTENT-DIFF":
                MISMATCHES.append(
                    f"integrity: copies of {run_id}/{basename} differ")
    INTEGRITY.append({"file": f"{run_id}/{basename}",
                      "source": str(existing[0].relative_to(ROOT)),
                      "copies": len(existing), "status": status})
    src = "out/raw" if existing[0].parts[-4] == "out" else "reports archive"
    return existing[0], src


def validate_record(p: Path) -> bool:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/measurement-schema/validate.py"),
         str(p)], capture_output=True, text=True, cwd=ROOT)
    out = (r.stdout + r.stderr).strip()
    ok = out.startswith("PASS")
    if not ok:
        MISMATCHES.append(f"validator: {p.name} -> {out[:200]}")
    return ok


def load_record(rel: str) -> dict:
    p = ROOT / rel
    if not p.is_file():
        raise FileNotFoundError(p)
    ok = validate_record(p)
    INTEGRITY.append({"file": rel, "source": rel,
                      "copies": 1, "status": "validator-PASS" if ok
                      else "validator-FAIL"})
    if not ok:
        raise SystemExit(f"record failed validator: {p}")
    return read_json(p)


# -- statistics ---------------------------------------------------------------
def describe_ms(ms: np.ndarray) -> dict:
    ms = np.asarray(ms, float)
    return {
        "n": int(ms.size),
        "mean": float(np.mean(ms)),
        "median": float(np.median(ms)),
        "p95": float(np.percentile(ms, 95)),          # linear interpolation
        "std_pop": float(np.std(ms, ddof=0)),          # record convention
        "cv_pct": float(np.std(ms, ddof=0) / np.mean(ms) * 100.0),
    }


def bootstrap_median_ratio_ci(v8: np.ndarray, ze: np.ndarray,
                              seed: int = SEED, b: int = B_BOOT):
    """Paired round-level bootstrap CI of median(v8*)/median(ze*).

    The 15 rounds are resampled JOINTLY (same index set for both engines),
    preserving the round pairing; the statistic mirrors the headline
    speedup definition (ratio of medians).
    """
    rng = np.random.default_rng(seed)
    a, z = np.asarray(v8, float), np.asarray(ze, float)
    idx = rng.integers(0, a.size, size=(b, a.size))
    stat = np.median(a[idx], axis=1) / np.median(z[idx], axis=1)
    lo, hi = np.percentile(stat, [2.5, 97.5])
    return float(lo), float(hi)


def sign_test(ratios: np.ndarray):
    """Exact two-sided binomial sign test on 'ze faster' round wins."""
    a = np.asarray(ratios, float)
    k = int(np.sum(a > 1.0))
    n = int(a.size)
    p = float(sps.binomtest(k, n, 0.5, alternative="two-sided").pvalue)
    return k, n, p


def wilcoxon(diffs_ms: np.ndarray):
    """Exact Wilcoxon signed-rank on round differences (ms)."""
    res = sps.wilcoxon(np.asarray(diffs_ms, float), zero_method="wilcox",
                       alternative="two-sided", method="exact")
    # scipy >= 1.7: statistic = min(W+, W-)
    return float(res.statistic), float(res.pvalue)


# -- loaders ------------------------------------------------------------------
def load_exhibit_e(run_id: str):
    p, src = locate("nd11_phase_e.json", run_id, "reports/nd11")
    return read_json(p), src


def load_exhibit_d(run_id: str):
    p, src = locate("nd6_phase_D.json", run_id, "reports/nd14")
    return read_json(p), src


def load_exhibit_abc(run_id: str, ph: str):
    p, src = locate(f"nd6_phase_{ph}.json", run_id, "reports/nd14")
    return read_json(p), src


def phase_e_arrays(exh: dict):
    req = exh["requests"]
    v8 = np.array([x["seconds"] * 1000 for x in req["v8"]])
    v8r = np.array([int(x["round"]) for x in req["v8"]])
    ze = np.array([x["seconds"] * 1000 for x in req["ze"]])
    zer = np.array([int(x["round"]) for x in req["ze"]])
    return v8, v8r, ze, zer


def round_medians(vals: np.ndarray, rounds: np.ndarray):
    out_r, out_m = [], []
    for r in sorted(set(rounds.tolist())):
        out_r.append(r)
        out_m.append(float(np.median(vals[rounds == r])))
    return np.array(out_r), np.array(out_m)


def d_paths(exh: dict) -> dict:
    return {r["path"]: np.array(r["rounds_ms"], float)
            for r in exh["raw_rounds"]}


# -- reconciliation -----------------------------------------------------------
def check(name: str, want: float, got: float, what: str, tol: float) -> float:
    rel = abs(want - got) / max(abs(want), 1e-30)
    if rel > tol:
        MISMATCHES.append(
            f"{name}: {what} record={want!r} recomputed={got!r} rel={rel:.3g}")
    return rel


def _hash_from(version: str, repo: str) -> str:
    m = re.search(re.escape(repo) + r"@([0-9a-f]+)", version)
    return m.group(1) if m else ""


def _csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


# -- main analysis ------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="ND-6 Phase D + ND-11 Phase E synthesis analysis")
    ap.add_argument("--out", default=str(ROOT / "out/charts"),
                    help="output directory (default out/charts)")
    ap.add_argument("--archive", default=None,
                    help="optional archive dir (e.g. reports/charts); "
                         "copies CSV + figures there after generation")
    args = ap.parse_args()
    out = Path(args.out)
    data = out / "data"
    data.mkdir(parents=True, exist_ok=True)

    inv_rows: list[dict] = []
    d_stats_rows: list[dict] = []
    d_paired_rows: list[dict] = []
    e_stats_rows: list[dict] = []
    e_paired_rows: list[dict] = []
    abcd_rows: list[dict] = []
    infer_rows: list[dict] = []
    comp_rows: list[dict] = []
    d_primary: dict[str, dict] = {}   # site -> phase D mongo-cache summary
    e_runs: list[dict] = []           # primary phase E runs (in PHASE_E order)

    # === Phase D (repository layer) ==========================================
    for rid, site, label, klass in PHASE_D:
        rec = load_record(f"reports/nd14/{rid}-nd6-d-{site}.record.json")
        exh, src = load_exhibit_d(rid)
        paths = d_paths(exh)
        cfg = rec["config"]
        assert cfg["repeats"] == 15, (rid, cfg["repeats"])

        for plabel, v8p, zep in D_PAIRS:
            v8, ze = paths[v8p], paths[zep]
            assert v8.size == ze.size == 15, (rid, plabel)
            sv, sz = describe_ms(v8), describe_ms(ze)
            ratio = v8 / ze
            diffs = v8 - ze
            med_ratio = float(np.median(ratio))
            med_speedup = float(sv["median"] / sz["median"])
            p95_ratio = float(sv["p95"] / sz["p95"])
            mean_ratio = float(sv["mean"] / sz["mean"])
            lo, hi = bootstrap_median_ratio_ci(v8, ze)
            k, n, sp = sign_test(ratio)
            wstat, wp = wilcoxon(diffs)
            d_stats_rows.append({
                "run_id": rid, "site": site, "label": label, "class": klass,
                "path": plabel,
                "v8_median_ms": g(sv["median"]), "ze_median_ms": g(sz["median"]),
                "v8_mean_ms": g(sv["mean"]), "ze_mean_ms": g(sz["mean"]),
                "v8_p95_ms": g(sv["p95"]), "ze_p95_ms": g(sz["p95"]),
                "v8_std_ms": g(sv["std_pop"]), "ze_std_ms": g(sz["std_pop"]),
                "v8_cv_pct": g(sv["cv_pct"]), "ze_cv_pct": g(sz["cv_pct"]),
                "delta_median_ms": g(sv["median"] - sz["median"]),
                "n_rounds": 15, "reps_per_round": 2,
                "speedup_median": g(med_speedup),
                "speedup_p95": g(p95_ratio), "speedup_mean": g(mean_ratio),
                "paired_median_ratio": g(med_ratio),
                "boot_ci_lo": g(lo), "boot_ci_hi": g(hi),
                "seed": SEED, "B": B_BOOT,
                "ze_round_wins": f"{k}/15",
                "sign_p": g(sp), "wilcoxon_p": g(wp),
            })
            infer_rows.append({
                "run_id": rid, "site": site,
                "boundary": f"phase-D/{plabel}",
                "statistic": "median(T_v8,i)/median(T_ze,i) over 15 "
                             "paired rounds",
                "point": g(med_speedup), "ci95_lo": g(lo), "ci95_hi": g(hi),
                "method": f"round-level paired bootstrap (rounds resampled "
                          f"jointly), B={B_BOOT}, seed={SEED}, percentile",
                "ze_wins": f"{k}/{n}", "sign_p": g(sp),
                "wilcoxon_stat": g(wstat), "wilcoxon_p": g(wp),
                "note": "15 rounds = pairing unit; single run",
            })
            for i in range(15):
                d_paired_rows.append({
                    "run_id": rid, "site": site, "path": plabel,
                    "round": i + 1, "v8_ms": g(v8[i]), "ze_ms": g(ze[i]),
                    "ratio": g(v8[i] / ze[i]), "delta_ms": g(v8[i] - ze[i]),
                })

            # reconcile against record results (same 15 round values)
            rec_by_path = {r["extras"]["path"]: r for r in rec["results"]}
            for path, s in ((v8p, sv), (zep, sz)):
                rr = rec_by_path[path]
                assert rr["extras"]["rounds"] == 15
                assert rr["extras"]["reps_per_round"] == 2, (rid, path)
                check(f"{rid}/{path}", rr["metrics"]["seconds_mean"] * 1000,
                      s["mean"], "seconds_mean", TOL_RECORD)
                check(f"{rid}/{path}",
                      rr["metrics"]["seconds_stddev"] * 1000, s["std_pop"],
                      "seconds_stddev(pop)", TOL_RECORD)
                check(f"{rid}/{path}",
                      rr["extras"]["seconds_median"] * 1000, s["median"],
                      "seconds_median", TOL_RECORD)
                check(f"{rid}/{path}", rr["extras"]["seconds_p95"] * 1000,
                      s["p95"], "seconds_p95", TOL_RECORD)
            if plabel == "mongo-cache" and klass == "primary":
                d_primary[site] = {
                    "run_id": rid, "label": label, "site": site,
                    "speedup_median": med_speedup, "speedup_p95": p95_ratio,
                    "ci": (lo, hi), "ze_wins": k,
                    "record_medians_ms": (sv["median"], sz["median"]),
                }

        lib = rec["library"]
        inv_rows.append({
            "run_id": rid, "phase": "D", "site": site, "evidence_class": klass,
            "root_commit": rec["git_commit"]["hash"],
            "ze_json_commit": _hash_from(lib["version"], "ze_json"),
            "saq_report_commit": _hash_from(lib["version"], "saq-report"),
            "runtime": lib["language_runtime"],
            "wasm_sha256_16": lib["artifact_sha256"][:16],
            "core_version": lib["core_version"], "js_version": lib["js_version"],
            "abi_version": lib["abi_version"],
            "corpus_store": rec["corpus"]["name"],
            "corpus_manifest_sha16": rec["corpus"]["sha256"][:16],
            "protocol": (f"{cfg['repeats']} rounds x {cfg['iterations']} "
                         f"reps/engine/path; warmup {cfg['warmup_runs']}; "
                         f"alternating rounds; no trimming; round value = "
                         f"mean of reps (dt/reps)"),
            "coexistence_prod_same_host": "n/a",
            "validator": "PASS",
            "exhibit_source": f"{src}/nd6_phase_D.json",
        })

    # === Phase E (HTTP GET /rekap end-to-end) ================================
    for rid, site, label, klass in PHASE_E:
        rec = load_record(
            f"reports/nd11/{rid}-nd11-phase-e-{site}.record.json")
        exh, src = load_exhibit_e(rid)
        proto = exh["protocol"]
        rounds_expected, per_round_total = proto["rounds"], proto["per_round"]
        parity = exh.get("parity") or {}
        assert parity.get("unique_response_hashes") == 1, (rid, parity)
        assert parity.get("void") is False, (rid, parity)
        v8, v8r, ze, zer = phase_e_arrays(exh)
        n_req = {"v8": int(v8.size), "ze": int(ze.size)}

        if klass == "primary":
            assert n_req["v8"] == n_req["ze"] == 150, (rid, n_req)
            assert rounds_expected == 15 and per_round_total == 20, (rid,)
            for r in sorted(set(v8r.tolist())):
                assert int((v8r == r).sum()) == 10 \
                    and int((zer == r).sum()) == 10, (rid, r)

        sv, sz = describe_ms(v8), describe_ms(ze)
        vr, vm = round_medians(v8, v8r)
        zr, zm = round_medians(ze, zer)
        assert np.array_equal(vr, zr)
        ratio = vm / zm
        diffs = vm - zm
        med_ratio = float(np.median(ratio))
        lo, hi = bootstrap_median_ratio_ci(vm, zm)
        k, n, sp = sign_test(ratio)
        wstat, wp = wilcoxon(diffs)
        med_speedup = float(sv["median"] / sz["median"])
        mean_speedup = float(sv["mean"] / sz["mean"])
        p95_speedup = float(sv["p95"] / sz["p95"])

        # reconcile vs record
        rr = {r["engine"]: r for r in rec["results"]}
        assert rr["v8"]["extras"]["response_sha256"] \
            == rr["wasm64_cabi"]["extras"]["response_sha256"], rid
        for engine, s in (("v8", sv), ("wasm64_cabi", sz)):
            check(f"{rid}/{engine}",
                  rr[engine]["metrics"]["seconds_mean"] * 1000, s["mean"],
                  "seconds_mean", TOL_RECORD)
            check(f"{rid}/{engine}",
                  rr[engine]["metrics"]["seconds_stddev"] * 1000, s["std_pop"],
                  "seconds_stddev(pop)", TOL_RECORD)
            check(f"{rid}/{engine}",
                  rr[engine]["extras"]["seconds_median"] * 1000, s["median"],
                  "seconds_median", TOL_RECORD)
            check(f"{rid}/{engine}",
                  rr[engine]["extras"]["seconds_p95"] * 1000, s["p95"],
                  "seconds_p95", TOL_RECORD)
        check(f"{rid}", exh["speedup_in_run"], med_speedup, "speedup_in_run",
              TOL_EXHIBIT)

        stats_row = {
            "run_id": rid, "site": site, "label": label, "class": klass,
            "rounds": rounds_expected,
            "per_round_total": per_round_total,
            "n_requests_engine": n_req["v8"],
            "v8_median_ms": g(sv["median"]), "ze_median_ms": g(sz["median"]),
            "v8_mean_ms": g(sv["mean"]), "ze_mean_ms": g(sz["mean"]),
            "v8_p95_ms": g(sv["p95"]), "ze_p95_ms": g(sz["p95"]),
            "v8_std_ms": g(sv["std_pop"]), "ze_std_ms": g(sz["std_pop"]),
            "v8_cv_pct": g(sv["cv_pct"]), "ze_cv_pct": g(sz["cv_pct"]),
            "delta_median_ms": g(sv["median"] - sz["median"]),
            "speedup_median": g(med_speedup),
            "speedup_mean": g(mean_speedup), "speedup_p95": g(p95_speedup),
            "paired_median_ratio": g(med_ratio),
            "boot_ci_lo": g(lo), "boot_ci_hi": g(hi),
            "seed": SEED, "B": B_BOOT, "ze_round_wins": f"{k}/15",
            "sign_p": g(sp), "wilcoxon_p": g(wp),
            "response_sha256_16":
                rr["v8"]["extras"]["response_sha256"][:16],
            "response_bytes": rr["v8"]["extras"]["response_bytes"],
        }
        if klass == "primary":
            e_stats_rows.append(stats_row)
            e_runs.append({
                "run_id": rid, "site": site, "label": label,
                "stats": stats_row,
                "speedup_median": med_speedup,
                "paired_median_ratio": med_ratio, "ci": (lo, hi),
                "ze_wins": k,
                "med_round_v8": vm, "med_round_ze": zm,
                "samples": (v8, ze),
                "delta_median_ms": float(sv["median"] - sz["median"]),
            })
            for i in range(15):
                e_paired_rows.append({
                    "run_id": rid, "site": site, "round": int(vr[i]),
                    "v8_median_ms": g(vm[i]), "ze_median_ms": g(zm[i]),
                    "ratio": g(vm[i] / zm[i]), "delta_ms": g(vm[i] - zm[i]),
                })
            infer_rows.append({
                "run_id": rid, "site": site,
                "boundary": "phase-E/HTTP-rekap",
                "statistic": "median(T_v8,i)/median(T_ze,i) over 15 "
                             "paired rounds",
                "point": g(med_speedup), "ci95_lo": g(lo), "ci95_hi": g(hi),
                "method": f"round-level paired bootstrap (rounds resampled "
                          f"jointly), B={B_BOOT}, seed={SEED}, percentile",
                "ze_wins": f"{k}/{n}", "sign_p": g(sp),
                "wilcoxon_stat": g(wstat), "wilcoxon_p": g(wp),
                "note": "15 rounds = pairing unit (10 req/engine/round); "
                        "300 requests NOT independent; single run",
            })

        lib = rec["library"]
        coex = exh.get("coexistence") or {}
        split = ("(10 v8 + 10 ze)/round" if klass == "primary"
                 else "(alternating, uneven split)")
        inv_rows.append({
            "run_id": rid, "phase": "E", "site": site, "evidence_class": klass,
            "root_commit": rec["git_commit"]["hash"],
            "ze_json_commit": _hash_from(lib["version"], "ze_json"),
            "saq_report_commit": _hash_from(lib["version"], "saq-report"),
            "runtime": lib["language_runtime"],
            "wasm_sha256_16": lib["artifact_sha256"][:16],
            "core_version": lib["core_version"],
            "js_version": lib["js_version"],
            "abi_version": lib["abi_version"],
            "corpus_store": rec["corpus"]["name"],
            "corpus_manifest_sha16": rec["corpus"]["sha256"][:16],
            "protocol": (
                f"rounds={rounds_expected}, per_round={per_round_total} "
                f"TOTAL {split}, warmup {proto['warmup']}/engine untimed, "
                f"n={n_req['v8']}+{n_req['ze']}={n_req['v8'] + n_req['ze']} "
                f"requests, alternation (r+k)%2, no trimming"),
            "coexistence_prod_same_host": str(bool(
                coex.get("production_same_host"))),
            "validator": "PASS",
            "exhibit_source": f"{src}/nd11_phase_e.json",
        })

    # === Phase A/B/C (selective traversal context) ===========================
    for rid, ph in PHASE_ABC:
        exh, _ = load_exhibit_abc(rid, ph)
        by_doc: dict[str, dict] = {}
        for r in exh["raw_rounds"]:
            by_doc.setdefault(r["doc"], {})[r["path"]] = np.array(
                r["rounds_ms"], float)
        for doc, pmap in by_doc.items():
            v8p = [p for p in pmap if p.startswith("v8-") and p != "v8-clone"]
            zep = [p for p in pmap if p.startswith("ze-")]
            if not v8p or not zep:
                continue
            v8p, zep = v8p[0], zep[0]
            v8, ze = pmap[v8p], pmap[zep]
            sv, sz = describe_ms(v8), describe_ms(ze)
            ratio = v8 / ze
            abcd_rows.append({
                "run_id": rid, "phase": ph, "doc": doc,
                "v8_path": v8p, "ze_path": zep,
                "v8_median_ms": g(sv["median"]),
                "ze_median_ms": g(sz["median"]),
                "speedup_median": g(float(np.median(ratio))),
                "speedup_p95": g(float(sv["p95"] / sz["p95"])),
                "ze_round_wins": f"{int((ratio > 1).sum())}/15",
            })
            if ph == "A" and "v8-clone" in pmap:
                cl = pmap["v8-clone"]
                abcd_rows.append({
                    "run_id": rid, "phase": "A", "doc": doc,
                    "v8_path": "v8-clone", "ze_path": "(reference only)",
                    "v8_median_ms": g(float(np.median(cl))),
                    "ze_median_ms": "", "speedup_median": "",
                    "speedup_p95": "", "ze_round_wins": "",
                })

    # === compression index C = S_D / S_E (descriptive) =======================
    dev_d = d_primary.get("dev_device")
    srv_d = d_primary.get("saq_server")
    dev_e_runs = [r for r in e_runs if r["site"] == "dev_device"]
    srv_e = next((r for r in e_runs if r["site"] == "saq_server"), None)
    assert dev_d and srv_d and srv_e and len(dev_e_runs) == 2
    comp_specs = [("dev_device", dev_d, e) for e in dev_e_runs]
    comp_specs.append(("saq_server", srv_d, srv_e))
    for site, drow, e_run in comp_specs:
        comp_rows.append({
            "site": site, "S_D_run": drow["run_id"], "S_D_path": "mongo-cache",
            "S_D_median": g(drow["speedup_median"]),
            "S_E_run": e_run["run_id"], "S_E_label": e_run["label"],
            "S_E_median": g(e_run["speedup_median"]),
            "C_ratio": g(drow["speedup_median"] / e_run["speedup_median"]),
            "note": "descriptive index across two different boundaries; "
                    "not a parser-time share",
        })

    # === write CSVs ==========================================================
    _csv(data / "nd-de-inventory.csv", inv_rows)
    _csv(data / "nd-phase-d-stats.csv", d_stats_rows)
    _csv(data / "nd-phase-d-paired.csv", d_paired_rows)
    _csv(data / "nd-phase-e-stats.csv", e_stats_rows)
    _csv(data / "nd-phase-e-paired.csv", e_paired_rows)
    _csv(data / "nd-phase-abcd-stats.csv", abcd_rows)
    _csv(data / "nd-de-inference.csv", infer_rows)
    _csv(data / "nd-de-compression.csv", comp_rows)

    # === figures =============================================================
    _fig_speedup(out, dev_d, dev_e_runs, srv_d, srv_e)
    _fig_distribution(out, srv_e)
    _fig_paired_rounds(out, [srv_e] + dev_e_runs)
    _fig_compression(out, comp_specs)
    _fig1_mermaid(out)

    # === provenance metadata (timestamp-free -> byte-stable reruns) ==========
    prov = {
        "script": "scripts/analyze_measurement/nd_d_e_synthesis.py",
        "purpose": "ND-6 Phase D + ND-11 Phase E synthesis (read-only)",
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "inference": {
            "unit": "measurement round (15 per run)",
            "headline_statistic":
                "speedup = median(T_v8,i)/median(T_ze,i) over the 15 "
                "paired rounds (harness speedup_in_run convention)",
            "bootstrap": {"B": B_BOOT, "seed": SEED,
                          "rng": "numpy default_rng (PCG64)",
                          "statistic": "median(v8*)/median(ze*) over "
                                       "jointly resampled rounds",
                          "interval": "percentile 2.5/97.5"},
            "sign_test": "exact binomial two-sided (scipy binomtest)",
            "wilcoxon": "exact signed-rank two-sided, zero_method=wilcox "
                        "(scipy; statistic = min(W+, W-))",
            "not_independent": "300 Phase E requests are alternated within "
                               "rounds on one host session; only the 15 "
                               "round pairs carry inferential weight",
        },
        "reconciliation": {
            "record_tol_relative": TOL_RECORD,
            "exhibit_tol_relative": TOL_EXHIBIT,
            "record_stored_precision":
                "Phase D: seconds_mean/median/p95 toPrecision(9), "
                "seconds_stddev toPrecision(6) (nd6_bench.mjs pushResult); "
                "Phase E: full float64",
            "conventions": "stddev population ddof=0; p95 linear "
                           "interpolation (both harnesses)",
        },
        "compression_index": {
            "definition": "C = S_D/S_E (in-run medians)",
            "caveat": "crosses boundaries AND saq-report commits; "
                      "descriptive only",
        },
        "integrity": INTEGRITY,
        "evidence": inv_rows,
        "inputs_sha256": {},
        "mismatches": MISMATCHES,
    }
    for p in sorted(set(i["source"] for i in INTEGRITY)):
        prov["inputs_sha256"][p] = sha256_file(ROOT / p)
    prov_path = data / "nd-de-synthesis-provenance.json"
    prov_path.write_text(json.dumps(prov, indent=2, sort_keys=True),
                         encoding="utf-8")

    # === optional archive copy ===============================================
    if args.archive:
        arc = Path(args.archive)
        arc.mkdir(parents=True, exist_ok=True)
        names = ["nd-de-speedup-comparison", "nd-de-phase-e-distribution",
                 "nd-de-paired-rounds", "nd-de-compression"]
        for name in names:
            for ext in ("png", "svg"):
                shutil.copy2(out / f"{name}.{ext}", arc / f"{name}.{ext}")
        for f in sorted(data.glob("*.csv")) + [prov_path]:
            shutil.copy2(f, arc / f.name)
        shutil.copy2(out / "fig1-architecture.mmd",
                     arc / "fig1-architecture.mmd")

    # === console report ======================================================
    print("== ND-6 Phase D + ND-11 Phase E synthesis ==")
    for site, drow, e_run in (("dev_device", dev_d, dev_e_runs[0]),
                              ("saq_server", srv_d, srv_e)):
        print(f"[{site}] D(mongo-cache) {drow['speedup_median']:.3f}x "
              f"(p95 {drow['speedup_p95']:.3f}x, run {drow['run_id']})")
        print(f"[{site}] E(HTTP /rekap)  {e_run['speedup_median']:.3f}x "
              f"(paired {e_run['paired_median_ratio']:.3f}, "
              f"ze wins {e_run['stats']['ze_round_wins']}, "
              f"run {e_run['run_id']})")
        print(f"[{site}] C = S_D/S_E = "
              f"{drow['speedup_median'] / e_run['speedup_median']:.3f} "
              f"(descriptive)")
    print(f"[dev_device] E re-run        "
          f"{dev_e_runs[1]['speedup_median']:.3f}x "
          f"(paired {dev_e_runs[1]['paired_median_ratio']:.3f}, "
          f"ze wins {dev_e_runs[1]['stats']['ze_round_wins']}, "
          f"run {dev_e_runs[1]['run_id']})")
    print(f"[dev_device] C vs E re-run    "
          f"{dev_d['speedup_median'] / dev_e_runs[1]['speedup_median']:.3f} "
          f"(descriptive)")
    n_records = sum(1 for i in INTEGRITY if "validator" in i["status"])
    print("\nreconciliation: all recomputed values match accepted records "
          f"(record tol {TOL_RECORD:g}, exhibit tol {TOL_EXHIBIT:g}); "
          f"validator PASS on all {n_records} records; "
          f"integrity: {len(INTEGRITY)} evidence files checked")
    if MISMATCHES:
        print(f"\nMISMATCHES ({len(MISMATCHES)}):")
        for m in MISMATCHES:
            print("  -", m)
        return 1
    return 0


# -- figures ------------------------------------------------------------------
def _save(fig, out: Path, name: str):
    fig.savefig(out / f"{name}.png", dpi=300)
    fig.savefig(out / f"{name}.svg", metadata={"Date": None})
    plt.close(fig)


def _fig_speedup(out, dev_d, dev_e_runs, srv_d, srv_e):
    specs = [
        (0.0, dev_d["speedup_median"], C_DEV,
         "Phase D (repository layer)", dev_d["ci"]),
    ]
    for i, er in enumerate(dev_e_runs):
        specs.append((0.42 + 0.42 * i, er["speedup_median"],
                      C_DEV if i == 0 else C_DEV2,
                      f"Phase E run {i + 1} (HTTP)", er["ci"]))
    specs.append((1.4, srv_d["speedup_median"], C_SRV,
                  "Phase D (repository layer)", srv_d["ci"]))
    specs.append((1.82, srv_e["speedup_median"], C_SRV,
                  "Phase E (HTTP)", srv_e["ci"]))

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.axhline(1.0, color="#888888", lw=0.8, ls="--", zorder=1)
    xs = [s[0] for s in specs]
    hs = [s[1] for s in specs]
    cs = [s[2] for s in specs]
    yerr = np.array([[h - ci[0], ci[1] - h] for _, h, _, _, ci in specs]).T
    ax.bar(xs, hs, width=0.34, color=cs, zorder=2, yerr=yerr, capsize=3,
           error_kw={"lw": 0.9, "ecolor": "#444444"})
    for (x, h, _, _, ci) in specs:
        ax.text(x, max(h, ci[1]) + 0.08, f"{h:.2f}", ha="center", fontsize=9)
    ax.set_xticks([0.21, 1.61])
    ax.set_xticklabels(["Phase D - repository layer\n(mongo-cache path)",
                        "Phase E - HTTP GET /rekap\nend-to-end"])
    ax.set_ylabel("Speedup  $T_{V8}/T_{ze}$  (in-run median ratio)")
    ax.set_ylim(0, 3.55)
    ax.legend([Patch(facecolor=C_DEV), Patch(facecolor=C_DEV2),
               Patch(facecolor=C_SRV)],
              ["dev_device", "dev_device (re-run)", "saq_server"],
              frameon=False, fontsize=8, loc="upper right")
    ax.set_title("ze_json speedup across measurement boundaries "
                 "(ND-14 / ND-11)", fontsize=11)
    fig.text(0.01, 0.012,
             "Bars: median ratio within a single run_id. Whiskers: 95% CI "
             "(round-level paired bootstrap, B=10000, seed 20261117).\n"
             "Dev vs server = descriptive comparison (different hosts and "
             "commits), not a controlled experiment. Data: accepted records "
             "+ raw exhibits.",
             fontsize=6.8, color="#444444")
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    _save(fig, out, "nd-de-speedup-comparison")


def _fig_distribution(out, srv_e):
    v8, ze = srv_e["samples"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.6))
    for vals, c, lab in ((v8, C_V8, "V8 baseline"), (ze, C_SRV, "ze_json")):
        s = np.sort(vals)
        ax1.step(s, np.arange(1, s.size + 1) / s.size, where="post",
                 color=c, lw=1.6, label=lab)
    ax1.set_xlabel("Request latency (ms)")
    ax1.set_ylabel("ECDF  P(latency <= x)")
    ax1.legend(frameon=False, fontsize=8, loc="lower right")
    ax1.set_title("Empirical CDF", fontsize=10)
    bp = ax2.boxplot([v8, ze], tick_labels=["V8", "ze"], whis=1.5,
                     showfliers=True, widths=0.5, patch_artist=True)
    for patch, c in zip(bp["boxes"], (C_V8, C_SRV)):
        patch.set_facecolor(c)
        patch.set_alpha(0.5)
    rng = np.random.default_rng(SEED)
    for i, vals in enumerate((v8, ze), start=1):
        ax2.scatter(rng.normal(i, 0.05, vals.size), vals, s=6, alpha=0.35,
                    color="#333333", zorder=3)
    ax2.set_ylabel("Request latency (ms)")
    ax2.set_title("All 150 requests/engine (no trimming)", fontsize=10)
    fig.suptitle(f"ND-11 Phase E - saq_server ({srv_e['run_id']})",
                 fontsize=11, y=0.98)
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    _save(fig, out, "nd-de-phase-e-distribution")


def _fig_paired_rounds(out, runs):
    fig, axes = plt.subplots(len(runs), 1, figsize=(7.2, 2.3 * len(runs)),
                             sharex=True)
    if len(runs) == 1:
        axes = [axes]
    for ax, run in zip(axes, runs):
        r = np.arange(1, 16)
        ax.plot(r, run["med_round_v8"], "-o", color=C_V8, ms=3.5, lw=1.2,
                label="V8 round median")
        ax.plot(r, run["med_round_ze"], "-o", color=C_SRV, ms=3.5, lw=1.2,
                label="ze round median")
        ax2 = ax.twinx()
        ratio = run["med_round_v8"] / run["med_round_ze"]
        ax2.step(r, ratio, where="mid", color=C_RATIO, lw=1.0, ls="--",
                 alpha=0.9)
        ax2.set_ylim(min(0.9, float(ratio.min())) - 0.03,
                     max(1.25, float(ratio.max())) + 0.03)
        ax2.set_ylabel("$R_i$ = v8/ze", color=C_RATIO, fontsize=8)
        ax2.tick_params(axis="y", labelcolor=C_RATIO, labelsize=7)
        ax.set_ylabel("Round median (ms)", fontsize=8)
        wins = int((ratio > 1).sum())
        ax.set_title(f"{run['site']} - {run['label']} ({run['run_id']}): "
                     f"ze wins {wins}/15 rounds", fontsize=9, loc="left")
        ax.legend(frameon=False, fontsize=7, loc="upper right", ncols=2)
    axes[-1].set_xlabel("Round (1-15; every round shown)")
    fig.suptitle("Paired per-round comparison - Phase E HTTP /rekap "
                 "(round = pairing unit)", fontsize=11)
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    _save(fig, out, "nd-de-paired-rounds")


def _fig_compression(out, comp_specs):
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    y = 0
    yticks, ylabels = [], []
    for site, drow, e_run in comp_specs:
        yticks.append(y)
        ylabels.append(f"{site}\nD {drow['run_id'].rsplit('-', 1)[1]} / "
                       f"E {e_run['run_id'].rsplit('-', 1)[1]}")
        color = C_DEV if site == "dev_device" else C_SRV
        ax.plot([e_run["speedup_median"], drow["speedup_median"]], [y, y],
                color="#999999", lw=1.4, zorder=1)
        ax.scatter([drow["speedup_median"]], [y], s=64, color=color,
                   zorder=3, marker="s")
        ax.scatter([e_run["speedup_median"]], [y], s=64, color=color,
                   zorder=3, marker="o", alpha=0.75)
        ax.annotate(f"D {drow['speedup_median']:.2f}",
                    (drow["speedup_median"], y),
                    xytext=(4, 6), textcoords="offset points", fontsize=8)
        ax.annotate(f"E {e_run['speedup_median']:.2f}",
                    (e_run["speedup_median"], y),
                    xytext=(4, -12), textcoords="offset points", fontsize=8)
        c = drow["speedup_median"] / e_run["speedup_median"]
        ax.text(3.18, y, f"C = {c:.2f}", va="center", fontsize=9,
                fontweight="bold")
        y -= 1
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=8)
    ax.set_xlabel("Speedup $T_{V8}/T_{ze}$ (in-run, per boundary)")
    ax.set_xlim(0.8, 3.6)
    ax.set_ylim(min(yticks) - 0.6, 0.6)
    ax.axvline(1.0, color="#888888", lw=0.8, ls="--")
    ax.set_title("Speedup compression D -> E (C = $S_D$/$S_E$, "
                 "descriptive index)", fontsize=11)
    fig.text(0.01, 0.015,
             "D = ND-6 phase D repository layer (mongo-cache path); "
             "E = ND-11 HTTP GET /rekap end-to-end.\n"
             "C = ratio of in-run speedups across two DIFFERENT measurement "
             "boundaries (and different\nsaq-report commits) - a "
             "descriptive compression index, not a measured parser-time "
             "share. Dev row shows both accepted dev Phase E runs.",
             fontsize=6.8, color="#444444")
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    _save(fig, out, "nd-de-compression")


def _fig1_mermaid(out: Path) -> None:
    src = """%% ND-6 Phase D vs ND-11 Phase E measurement boundaries (synthesis figure 1)
%% Data flow of the SAQ Express app and where each boundary starts/stops.
flowchart LR
    subgraph GEN["Load generator (same host, localhost)"]
        H["nd6_bench.mjs / nd11_phase_e.mjs"]
    end

    subgraph APP["SAQ Express app - two byte-identical instances<br/>(v8 baseline port A / ze port B, SAQ_JSON_ENGINE toggle)"]
        MW["Express middleware"] --> RT["GET /rekap handler"]
        RT --> RP["Repository layer"]
        RP --> EJ["EJS render"] --> RS["HTTP response"]
    end

    subgraph REP["Repository internals (per store)"]
        V8P["baseline: canonical bytes -> JSON.parse / clone -> .length"]
        ZEP["ze: canonical bytes -> wasm64 C-ABI -> structural scan + count"]
    end

    subgraph ST["Store"]
        MG[("dev: anonymized corpus mirror (file / local throwaway Mongo)<br/>server: LIVE MongoDB json_store (counts pre = post)")]
    end

    H -- "HTTP GET /rekap" --> MW
    V8P -.-> RP
    ZEP -.-> RP
    RP <--> MG

    style MW stroke-dasharray: 3 3
    classDef dbound stroke:#2E7D32,stroke-width:2px;
    class V8P,ZEP dbound;
"""
    (out / "fig1-architecture.mmd").write_text(src, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
