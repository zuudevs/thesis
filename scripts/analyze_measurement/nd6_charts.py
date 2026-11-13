#!/usr/bin/env python3
"""Generate the ND-6 supervision charts (BAGIAN 5 of the supervision audit).

Reads validated measurement records from reports/nd6/**, applies the fairness
gate (in-situ pairs only: same run_id, site, host, corpus name+sha256, phase,
operation class, comparable metric), and writes:

  out/charts/nd6-phase-a.png/.svg
  out/charts/nd6-phase-b.png/.svg
  out/charts/nd6-phase-c.png/.svg
  out/charts/nd6-phase-d-latency.png/.svg
  out/charts/nd6-phase-d-speedup.png/.svg
  out/charts/nd6-file-store.png/.svg
  out/charts/nd6-p95.png/.svg
  out/charts/data/*.csv (+ captions.md, fairness-pairs.csv)

Deterministic: no randomness, fixed ordering. Metrics come from
extras.seconds_median / extras.seconds_p95 (fallback metrics.seconds_mean for
suite records, which have no rounds structure). Speedup = T_baseline / T_candidate
on the SAME metric; baseline = V8 (engine=v8), candidate = ze_json wasm64 C-ABI.

IMPORTANT (carried into every caption):
- P95 here is the P95 over per-round per-operation means (15 rounds, 2 reps),
  NOT a P95 over individual calls; CI95 is NOT claimed anywhere because
  out/raw/<run_id>/ exhibits are not available in this working copy.
- Server records (git_commit.dirty=true) are exploratory and drawn hatched.
- Phase A/B/C/D boundaries differ; charts never mix boundaries without labels.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import OrderedDict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RECORDS_DIR = os.path.join(ROOT, "reports", "nd6")
OUT_DIR = os.path.join(ROOT, "out", "charts")
DATA_DIR = os.path.join(OUT_DIR, "data")

DOC_ORDER = ["courses", "assistants", "lecturers", "schedules", "reports", "globalConfig"]

BASE_FILL = "#c8c8c8"
CAND_FILL = "#4a4a4a"
CAND_HATCH = "//"
EXPLORATORY_EDGE = "#b2182b"
REF_1_COLOR = "#333333"
REF_15_COLOR = "#b2182b"


def fmt_si(seconds: float) -> str:
    """Format a duration in seconds with a reasonable unit."""
    if seconds is None:
        return "?"
    if seconds < 1e-5:
        return f"{seconds * 1e9:.0f} ns"
    if seconds < 1e-2:
        return f"{seconds * 1e6:.2f} us"
    if seconds < 10:
        return f"{seconds * 1e3:.2f} ms"
    return f"{seconds:.2f} s"


def to_unit(seconds: float, unit: str) -> float:
    factor = {"ns": 1e9, "us": 1e6, "ms": 1e3, "s": 1.0}[unit]
    return seconds * factor


def parse_lib_version(text: str):
    m = re.search(r"ze_json@([0-9a-f]+),\s*saq-report@([0-9a-f]+)", text or "")
    if m:
        return m.group(1), m.group(2)
    return None, None


def load_records():
    recs = []
    for dirpath, _dirnames, filenames in os.walk(RECORDS_DIR):
        for fn in sorted(filenames):
            if "record" not in fn or not fn.endswith(".json"):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
            ze, saq = parse_lib_version((d.get("library") or {}).get("version", ""))
            rel = os.path.relpath(path, RECORDS_DIR).replace("\\", "/")
            recs.append(
                {
                    "path": path,
                    "rel": rel,
                    "record": d,
                    "run_id": d.get("run_id", ""),
                    "site": d.get("site", ""),
                    "host": (d.get("host") or {}).get("hostname", ""),
                    "node": ((d.get("host") or {}).get("toolchain", "") or "").split("+")[0].strip(),
                    "dirty": bool((d.get("git_commit") or {}).get("dirty", False)),
                    "commit": (d.get("git_commit") or {}).get("hash", ""),
                    "corpus_name": (d.get("corpus") or {}).get("name", ""),
                    "corpus_sha": (d.get("corpus") or {}).get("sha256", ""),
                    "ze_hash": ze or (d.get("git_commit") or {}).get("hash", ""),
                    "saq_hash": saq or (d.get("library") or {}).get("version", ""),
                    "kind": d.get("kind", ""),
                }
            )
    return recs


def nd6_phase_records(recs):
    """Only records whose results use the ND-6 phase naming (A|B|C|D/...)."""
    out = []
    for r in recs:
        names = [x.get("name", "") for x in r["record"].get("results", [])]
        if any(re.match(r"^[ABCD]/", n) for n in names):
            out.append(r)
    return out


def result_by_name(rec, name):
    for x in rec["record"].get("results", []):
        if x.get("name") == name:
            return x
    return None


def median_of(res):
    ex = res.get("extras") or {}
    if ex.get("seconds_median") is not None:
        return float(ex["seconds_median"]), "median"
    return float((res.get("metrics") or {})["seconds_mean"]), "mean"


def p95_of(res):
    ex = res.get("extras") or {}
    if ex.get("seconds_p95") is not None:
        return float(ex["seconds_p95"]), "p95"
    return None, None


def check_pair(rec, base_res, cand_res, log_rows, pair_desc):
    """Fairness gate (BAGIAN 5.1). Returns True if the pair may be charted."""
    checks = OrderedDict()
    checks["same_run_id"] = True  # results of one record share run_id by construction
    checks["same_site"] = True
    checks["same_corpus_sha"] = True
    checks["engines_differ"] = base_res.get("engine") != cand_res.get("engine")
    checks["status_ok_both"] = base_res.get("status") == "ok" and cand_res.get("status") == "ok"
    checks["same_doc_bytes"] = (base_res.get("extras") or {}).get("doc_bytes") == (
        cand_res.get("extras") or {}
    ).get("doc_bytes")
    ok = all(checks.values())
    log_rows.append(
        {
            "chart_pair": pair_desc,
            "run_id": rec["run_id"],
            "site": rec["site"],
            "corpus": rec["corpus_name"],
            "corpus_sha": rec["corpus_sha"],
            "dirty": rec["dirty"],
            "baseline_result": base_res.get("name"),
            "candidate_result": cand_res.get("name"),
            **checks,
            "accepted": ok,
        }
    )
    return ok


def run_label(rec):
    tag = "server (eksploratif, dirty)" if rec["dirty"] else "dev (bersih)"
    return f"{rec['run_id']} · {tag} · saq@{rec['saq_hash']}"


def exploratory(rec):
    return rec["dirty"]


def style_bar(bar, rec, cand=False):
    if cand:
        bar.set_hatch(CAND_HATCH)
    if exploratory(rec):
        bar.set_edgecolor(EXPLORATORY_EDGE)
        bar.set_linewidth(1.4)


def save(fig, name):
    png = os.path.join(OUT_DIR, f"{name}.png")
    svg = os.path.join(OUT_DIR, f"{name}.svg")
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")
    plt.close(fig)
    print("wrote", os.path.relpath(png, ROOT), "and .svg")


def write_csv(name, fieldnames, rows):
    path = os.path.join(DATA_DIR, name)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    print("wrote", os.path.relpath(path, ROOT))


def fig_panel_title(fig, title, sub):
    fig.suptitle(title, fontsize=13, fontweight="bold", y=0.99)
    fig.text(0.5, 0.945, sub, ha="center", fontsize=8.5, color="#444444")


# ---------------------------------------------------------------- charts ----

def chart_phase_pair(recs, log_rows, phase, cand_op, cand_label, chart_name, title_note):
    """Phases A/B/C: per-document grouped bars, dev + server panels."""
    dev_recs = [r for r in recs if r["site"] == "dev_device" and f"-{phase.lower()}-" in os.path.basename(r["rel"])]
    srv_recs = [r for r in recs if r["site"] == "saq_server" and f"-{phase.lower()}-" in os.path.basename(r["rel"])]
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2))
    unit = "us"
    csv_rows = []
    panels = [
        ("dev_device", dev_recs),
        ("saq_server", srv_recs),
    ]
    for ax, (site, srecs) in zip(axes, panels):
        if not srecs:
            ax.set_visible(False)
            continue
        rec = srecs[0]
        docs = [d for d in DOC_ORDER if result_by_name(rec, f"{phase}/{d}/v8-selective") or result_by_name(rec, f"{phase}/{d}/v8-parse")]
        width = 0.27
        xs = range(len(docs))
        vals = {"v8": [], "clone": [], "ze": []}
        used_docs = []
        for d in docs:
            if phase == "A":
                b = result_by_name(rec, f"A/{d}/v8-parse")
                cl = result_by_name(rec, f"A/{d}/v8-clone")
                c = result_by_name(rec, f"A/{d}/ze-parse")
            else:
                b = result_by_name(rec, f"{phase}/{d}/v8-selective")
                cl = None
                c = result_by_name(rec, f"{phase}/{d}/{cand_op}")
            if b is None or c is None:
                continue
            ok = check_pair(rec, b, c, log_rows, f"{chart_name}:{d}")
            if not ok:
                continue
            used_docs.append(d)
            vals["v8"].append(median_of(b)[0])
            vals["clone"].append(median_of(cl)[0] if cl else None)
            vals["ze"].append(median_of(c)[0])
            csv_rows.append(
                {
                    "chart": chart_name,
                    "site": rec["site"],
                    "run_id": rec["run_id"],
                    "dirty": rec["dirty"],
                    "phase": phase,
                    "document": d,
                    "baseline_op": b["name"],
                    "candidate_op": c["name"],
                    "metric": median_of(b)[1],
                    "baseline_seconds_median": median_of(b)[0],
                    "candidate_seconds_median": median_of(c)[0],
                    "speedup_median": median_of(b)[0] / median_of(c)[0],
                    "baseline_seconds_p95": (p95_of(b)[0] if p95_of(b)[0] else ""),
                    "candidate_seconds_p95": (p95_of(c)[0] if p95_of(c)[0] else ""),
                    "corpus_name": rec["corpus_name"],
                    "corpus_sha256": rec["corpus_sha"],
                    "ze_json_commit": rec["ze_hash"],
                    "saq_report_commit": rec["saq_hash"],
                    "node": rec["node"],
                    "rounds": (b.get("extras") or {}).get("rounds", ""),
                }
            )
        if not used_docs:
            ax.set_visible(False)
            continue
        n_bars = 3 if phase == "A" else 2
        offsets = {3: [-width, 0.0, width], 2: [-width / 2, width / 2]}[n_bars]
        series = [("Baseline V8 parse", vals["v8"], BASE_FILL, None, offsets[0])]
        if phase == "A":
            series.append(("Baseline V8 clone", vals["clone"], "#efefef", None, offsets[1]))
            series.append((f"Candidate ze ({cand_label})", vals["ze"], CAND_FILL, CAND_HATCH, offsets[2]))
        else:
            series.append((f"Candidate ze ({cand_label})", vals["ze"], CAND_FILL, CAND_HATCH, offsets[1]))
        for label, vlist, fill, hatch, off in series:
            xs_i = [i + off for i in range(len(used_docs))]
            yy = [to_unit(v, unit) if v else 0 for v in vlist]
            bars = ax.bar(xs_i, yy, width * 0.9, label=label, color=fill, hatch=hatch, edgecolor="#222222", linewidth=0.4)
            for bar, rec_ in zip(bars, [rec] * len(bars)):
                style_bar(bar, rec_, cand=(hatch == CAND_HATCH))
        ax.set_xticks(list(range(len(used_docs))))
        ax.set_xticklabels(used_docs, rotation=20, ha="right", fontsize=9)
        ax.set_yscale("log")
        ax.set_ylabel(f"Latensi median per operasi ({unit}; skala log)")
        ax.set_title(f"Site: {site} — host {rec['host']}, {rec['node']}" + (" [eksploratif: git dirty]" if rec["dirty"] else " [bersih]"), fontsize=10)
        ax.grid(axis="y", which="both", alpha=0.3)
        ax.set_axisbelow(True)
        ax.legend(fontsize=8)
        ax.annotate(
            f"run {rec['run_id']} · korpus {rec['corpus_name']} · 15 ronde × 2 reps",
            (0.02, 0.02), xycoords="axes fraction", fontsize=7.5, color="#555555",
        )
    fig_panel_title(
        fig,
        f"ND-6 Fase {phase} — {title_note}",
        "Latensi median per dokumen; baseline V8 vs ze_json wasm64 C-ABI dalam satu run_id. "
        "Perbandingan lintas run tidak digabung. Sumber: record PASS reports/nd6/.",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, chart_name)
    return csv_rows


def phase_d_data(recs, log_rows, chart_tag):
    rows = []
    for rec in nd6_phase_records(recs):
        names = [x.get("name", "") for x in rec["record"].get("results", [])]
        if not any(n.startswith("D/") for n in names):
            continue
        for store in ("mongo-cache", "file-store"):
            b = result_by_name(rec, f"D/D-{store}-v8")
            c = result_by_name(rec, f"D/D-{store}-ze")
            if b is None or c is None:
                continue
            ok = check_pair(rec, b, c, log_rows, f"{chart_tag}:{store}")
            if not ok:
                continue
            bm, metric = median_of(b)
            cm, _ = median_of(c)
            bp, _ = p95_of(b)
            cp, _ = p95_of(c)
            rows.append(
                {
                    "rec": rec,
                    "store": store,
                    "base_med": bm,
                    "cand_med": cm,
                    "base_p95": bp,
                    "cand_p95": cp,
                    "speedup_med": bm / cm,
                    "speedup_p95": (bp / cp) if bp and cp else None,
                    "metric": metric,
                }
            )
    return rows


def chart_d_latency(recs, log_rows):
    rows = phase_d_data(recs, log_rows, "nd6-phase-d-latency")
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.0))
    csv_rows = []
    for ax, site in zip(axes, ("dev_device", "saq_server")):
        site_rows = [r for r in rows if r["rec"]["site"] == site]
        if not site_rows:
            ax.set_visible(False)
            continue
        mongo = [r for r in site_rows if r["store"] == "mongo-cache"]
        labels = [f"{r['rec']['run_id']}\nsaq@{r['rec']['saq_hash']}" for r in mongo]
        xs = range(len(mongo))
        width = 0.38
        b_vals = [to_unit(r["base_med"], "ms") for r in mongo]
        c_vals = [to_unit(r["cand_med"], "ms") for r in mongo]
        bars_b = ax.bar([x - width / 2 for x in xs], b_vals, width, label="Baseline V8 (repo.read().length)", color=BASE_FILL, edgecolor="#222222", linewidth=0.4)
        bars_c = ax.bar([x + width / 2 for x in xs], c_vals, width, label="Candidate ze (repo.readCount())", color=CAND_FILL, hatch=CAND_HATCH, edgecolor="#222222", linewidth=0.4)
        for bar, rec_ in zip(bars_c, [r["rec"] for r in mongo]):
            style_bar(bar, rec_, cand=True)
        for bar, rec_ in zip(bars_b, [r["rec"] for r in mongo]):
            style_bar(bar, rec_, cand=False)
        for i, r in enumerate(mongo):
            ax.annotate(
                f"{r['speedup_med']:.2f}×",
                (i + width / 2, to_unit(r["cand_med"], "ms")),
                textcoords="offset points", xytext=(0, 3), ha="center", fontsize=9, fontweight="bold",
            )
            csv_rows.append(
                {
                    "chart": "nd6-phase-d-latency",
                    "site": site,
                    "run_id": r["rec"]["run_id"],
                    "dirty": r["rec"]["dirty"],
                    "store": r["store"],
                    "baseline_seconds_median": r["base_med"],
                    "candidate_seconds_median": r["cand_med"],
                    "speedup_median": r["speedup_med"],
                    "baseline_seconds_p95": r["base_p95"],
                    "candidate_seconds_p95": r["cand_p95"],
                    "speedup_p95": r["speedup_p95"],
                    "corpus_name": r["rec"]["corpus_name"],
                    "corpus_sha256": r["rec"]["corpus_sha"],
                    "ze_json_commit": r["rec"]["ze_hash"],
                    "saq_report_commit": r["rec"]["saq_hash"],
                    "node": r["rec"]["node"],
                    "rounds": 15,
                }
            )
        ax.set_xticks(list(xs))
        ax.set_xticklabels(labels, fontsize=7.6)
        ax.set_ylabel("Latensi median per request (ms; skala log)")
        ax.set_title(f"Site: {site} — Mongo cache (warm)" + (" [eksploratif: git dirty]" if site_rows[0]["rec"]["dirty"] else ""), fontsize=10)
        ax.set_yscale("log")
        ax.grid(axis="y", which="both", alpha=0.3)
        ax.set_axisbelow(True)
        ax.legend(fontsize=8)
        ax.annotate(
            f"korpus {mongo[0]['rec']['corpus_name']} (sha256 cocok) · 15 ronde × 2 reps · 1 iterasi = GET /rekap 4 repo",
            (0.02, 0.02), xycoords="axes fraction", fontsize=7.5, color="#555555",
        )
    fig_panel_title(
        fig,
        "ND-6 Fase D — Latensi Mongo Cache per Run (boundary lapisan repository)",
        "Satu iterasi = request GET /rekap atas 4 repository (baseline repo.read().length vs ze repo.readCount()). "
        "Bukan endpoint HTTP end-to-end; middleware dan render EJS di luar boundary. Fase D memakai warm cache bytes kanonik.",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, "nd6-phase-d-latency")
    return csv_rows


def chart_d_speedup(recs, log_rows):
    rows = phase_d_data(recs, log_rows, "nd6-phase-d-speedup")
    fig, ax = plt.subplots(figsize=(12.0, 5.4))
    order = [r for r in rows if r["rec"]["site"] == "dev_device"] + [r for r in rows if r["rec"]["site"] == "saq_server"]
    labels = [
        f"{r['store']} · {r['rec']['site']} · saq@{r['rec']['saq_hash']}" + (" [eksploratif]" if r["rec"]["dirty"] else "")
        for r in order
    ]
    vals = [r["speedup_med"] for r in order]
    bars = ax.bar(range(len(order)), vals, 0.62, color=CAND_FILL, hatch=CAND_HATCH, edgecolor="#222222", linewidth=0.5)
    for bar, rec_, v in zip(bars, [r["rec"] for r in order], vals):
        style_bar(bar, rec_, cand=False)
        ax.annotate(f"{v:.2f}×", (bar.get_x() + bar.get_width() / 2, v), textcoords="offset points", xytext=(0, 3), ha="center", fontsize=9, fontweight="bold")
    ax.axhline(1.0, color=REF_1_COLOR, linestyle="--", linewidth=1)
    ax.axhline(1.5, color=REF_15_COLOR, linestyle="--", linewidth=1.2)
    ax.annotate("1× (setara)", (len(order) - 0.4, 1.0), fontsize=8, ha="right", va="bottom")
    ax.annotate("1,5× (ambang acceptance)", (len(order) - 0.4, 1.5), fontsize=8, ha="right", va="bottom", color=REF_15_COLOR)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("Speedup  =  T_baseline / T_candidate  (median)")
    ax.set_ylim(0, max(2.0, max(vals) * 1.25))
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    fig_panel_title(
        fig,
        "ND-6 Fase D — Speedup per Run (Mongo cache dan File store terpisah)",
        "Rasio dalam satu run_id per site (in-situ). Run server bergaris merah = git dirty (eksploratif). "
        "Run dev dengan saq-report@7930009 mendahului cache bytes kanonik (8c7f2d4) — lihat interpretasi caption.",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, "nd6-phase-d-speedup")
    csv_rows = [
        {
            "chart": "nd6-phase-d-speedup",
            "site": r["rec"]["site"],
            "run_id": r["rec"]["run_id"],
            "dirty": r["rec"]["dirty"],
            "store": r["store"],
            "speedup_median": r["speedup_med"],
            "speedup_p95": r["speedup_p95"],
            "baseline_seconds_median": r["base_med"],
            "candidate_seconds_median": r["cand_med"],
            "saq_report_commit": r["rec"]["saq_hash"],
            "ze_json_commit": r["rec"]["ze_hash"],
        }
        for r in order
    ]
    return csv_rows


def chart_file_store(recs, log_rows):
    rows = [r for r in phase_d_data(recs, log_rows, "nd6-file-store") if r["store"] == "file-store"]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))
    csv_rows = []
    for ax, site in zip(axes, ("dev_device", "saq_server")):
        srows = [r for r in rows if r["rec"]["site"] == site]
        if not srows:
            ax.set_visible(False)
            continue
        labels = [r["rec"]["run_id"] + ("" if not r["rec"]["dirty"] else "\n[eksploratif]") for r in srows]
        xs = range(len(srows))
        width = 0.38
        b_vals = [to_unit(r["base_med"], "ms") for r in srows]
        c_vals = [to_unit(r["cand_med"], "ms") for r in srows]
        bars_b = ax.bar([x - width / 2 for x in xs], b_vals, width, label="Baseline V8", color=BASE_FILL, edgecolor="#222222", linewidth=0.4)
        bars_c = ax.bar([x + width / 2 for x in xs], c_vals, width, label="Candidate ze", color=CAND_FILL, hatch=CAND_HATCH, edgecolor="#222222", linewidth=0.4)
        for bar, rec_ in zip(bars_c, [r["rec"] for r in srows]):
            style_bar(bar, rec_, cand=True)
        for i, r in enumerate(srows):
            ax.annotate(f"{r['speedup_med']:.2f}× (regresi)" if r["speedup_med"] < 1 else f"{r['speedup_med']:.2f}×",
                        (i, to_unit(r["cand_med"], "ms")), textcoords="offset points", xytext=(0, 4), ha="center", fontsize=9, fontweight="bold",
                        color=REF_15_COLOR if r["speedup_med"] < 1 else "#222222")
            csv_rows.append(
                {
                    "chart": "nd6-file-store",
                    "site": site,
                    "run_id": r["rec"]["run_id"],
                    "dirty": r["rec"]["dirty"],
                    "baseline_seconds_median": r["base_med"],
                    "candidate_seconds_median": r["cand_med"],
                    "speedup_median": r["speedup_med"],
                    "baseline_seconds_p95": r["base_p95"],
                    "candidate_seconds_p95": r["cand_p95"],
                    "corpus_name": r["rec"]["corpus_name"],
                    "corpus_sha256": r["rec"]["corpus_sha"],
                    "saq_report_commit": r["rec"]["saq_hash"],
                    "ze_json_commit": r["rec"]["ze_hash"],
                }
            )
        ax.set_xticks(list(xs))
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylabel("Latensi median per request (ms)")
        ax.set_ylim(0, max(b_vals + c_vals) * 1.25)
        ax.set_title(f"Site: {site}" + (" [eksploratif: git dirty]" if srows[0]["rec"]["dirty"] else ""), fontsize=10)
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        ax.legend(fontsize=8)
        ax.annotate("Sumbu mulai dari 0 (tanpa pemotongan).", (0.02, 0.02), xycoords="axes fraction", fontsize=7.5, color="#555555")
    fig_panel_title(
        fig,
        "ND-6 Fase D — File Store: ze lebih lambat dari V8 pada ketiga run",
        "Jalur file store tanpa cache bytes kanonik Mongo. Hasil negatif ditampilkan apa adanya: speedup 0,91×–0,95×.",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, "nd6-file-store")
    return csv_rows


def chart_p95(recs, log_rows):
    """P95-based speedup for all valid in-situ pairs (phases A-D)."""
    rows = []
    for rec in nd6_phase_records(recs):
        for res in rec["record"].get("results", []):
            name = res.get("name", "")
            if name.endswith("-v8") or name.endswith("/v8-parse") or name.endswith("/v8-selective"):
                pass
        # build pairs per document for A, B, C
        for phase, cand_op in (("A", "ze-parse"), ("B", "ze-project-selective"), ("C", "ze-l1-traversal")):
            docs = DOC_ORDER if phase != "A" else DOC_ORDER
            for d in docs:
                if phase == "A":
                    b = result_by_name(rec, f"A/{d}/v8-parse")
                    c = result_by_name(rec, f"A/{d}/ze-parse")
                else:
                    b = result_by_name(rec, f"{phase}/{d}/v8-selective")
                    c = result_by_name(rec, f"{phase}/{d}/{cand_op}")
                if b is None or c is None:
                    continue
                ok = check_pair(rec, b, c, log_rows, f"nd6-p95:{phase}:{d}")
                if not ok:
                    continue
                bp, _ = p95_of(b)
                cp, _ = p95_of(c)
                if bp is None or cp is None:
                    continue
                rows.append({"rec": rec, "phase": phase, "doc": d, "speedup": bp / cp, "base_p95": bp, "cand_p95": cp})
        # phase D
        for store in ("mongo-cache", "file-store"):
            b = result_by_name(rec, f"D/D-{store}-v8")
            c = result_by_name(rec, f"D/D-{store}-ze")
            if b is None or c is None:
                continue
            ok = check_pair(rec, b, c, log_rows, f"nd6-p95:D:{store}")
            if not ok:
                continue
            bp, _ = p95_of(b)
            cp, _ = p95_of(c)
            if bp is None or cp is None:
                continue
            rows.append({"rec": rec, "phase": "D", "doc": store, "speedup": bp / cp, "base_p95": bp, "cand_p95": cp})

    fig, axes = plt.subplots(1, 2, figsize=(14.5, 7.2), sharex=False)
    csv_rows = []
    for ax, site in zip(axes, ("dev_device", "saq_server")):
        srows = [r for r in rows if r["rec"]["site"] == site]
        if not srows:
            ax.set_visible(False)
            continue
        srows.sort(key=lambda r: (r["phase"], r["doc"]))
        labels = [f"{r['phase']}·{r['doc']}" for r in srows]
        vals = [r["speedup"] for r in srows]
        colors = {"A": "#bdbdbd", "B": "#8c8c8c", "C": "#4a4a4a", "D": "#2166ac"}
        bars = ax.barh(range(len(srows)), vals, 0.66, color=[colors[r["phase"]] for r in srows], edgecolor="#222222", linewidth=0.4)
        for bar, rec_, v in zip(bars, [r["rec"] for r in srows], vals):
            if exploratory(rec_):
                bar.set_edgecolor(EXPLORATORY_EDGE)
                bar.set_linewidth(1.4)
            ax.annotate(f"{v:.2f}×", (v, bar.get_y() + bar.get_height() / 2), textcoords="offset points", xytext=(3, -2), fontsize=7.5, va="center")
        ax.axvline(1.0, color=REF_1_COLOR, linestyle="--", linewidth=1)
        ax.axvline(1.5, color=REF_15_COLOR, linestyle="--", linewidth=1.2)
        ax.set_yticks(range(len(srows)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("Speedup P95 = P95_baseline / P95_candidate")
        ax.set_title(f"Site: {site}" + (" — termasuk run eksploratif (git dirty, tepi merah)" if any(exploratory(r['rec']) for r in srows) else ""), fontsize=10)
        ax.grid(axis="x", alpha=0.3)
        ax.set_axisbelow(True)
        for r in srows:
            csv_rows.append(
                {
                    "chart": "nd6-p95",
                    "site": r["rec"]["site"],
                    "run_id": r["rec"]["run_id"],
                    "dirty": r["rec"]["dirty"],
                    "phase": r["phase"],
                    "target": r["doc"],
                    "speedup_p95": r["speedup"],
                    "baseline_seconds_p95": r["base_p95"],
                    "candidate_seconds_p95": r["cand_p95"],
                    "saq_report_commit": r["rec"]["saq_hash"],
                }
            )
        ax.annotate(
            "P95 dihitung atas rata-rata per operasi antar 15 ronde (bukan distribusi panggilan individual). Tanpa CI95 (raw exhibit tidak tersedia).",
            (0.02, 0.01), xycoords="axes fraction", fontsize=7.5, color="#555555",
        )
    handles = [
        Patch(facecolor=colors["A"], label="Fase A (materialisasi penuh)"),
        Patch(facecolor=colors["B"], label="Fase B (L2 project)"),
        Patch(facecolor=colors["C"], label="Fase C (L1 traversal)"),
        Patch(facecolor=colors["D"], label="Fase D (lapisan repository)"),
        Patch(facecolor="white", edgecolor=EXPLORATORY_EDGE, label="Tepi merah = run git dirty (eksploratif)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=5, fontsize=8.5, frameon=False)
    fig_panel_title(
        fig,
        "ND-6 — Speedup berbasis P95 untuk semua pasangan in-situ yang sah",
        "Setiap batang = satu pasangan baseline/candidate dalam satu run_id. Garis 1× dan 1,5× sebagai referensi eksperimen.",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    save(fig, "nd6-p95")
    return csv_rows


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    recs = load_records()
    nd6 = nd6_phase_records(recs)
    print(f"loaded {len(recs)} records, {len(nd6)} ND-6 phase records")
    log_rows = []

    a_rows = chart_phase_pair(nd6, log_rows, "A", "ze-parse", "parse penuh", "nd6-phase-a", "Materialisasi penuh (V8 parse / V8 clone / ze parse)")
    b_rows = chart_phase_pair(nd6, log_rows, "B", "ze-project-selective", "L2 project", "nd6-phase-b", "Akses selektif V8 vs L2 project(shape)")
    c_rows = chart_phase_pair(nd6, log_rows, "C", "ze-l1-traversal", "L1 traversal", "nd6-phase-c", "Akses selektif V8 vs L1 traversal")
    dlat_rows = chart_d_latency(nd6, log_rows)
    dspeed_rows = chart_d_speedup(nd6, log_rows)
    fs_rows = chart_file_store(nd6, log_rows)
    p95_rows = chart_p95(nd6, log_rows)

    write_csv("nd6-phase-a.csv", list(a_rows[0].keys()) if a_rows else ["chart"], a_rows)
    write_csv("nd6-phase-b.csv", list(b_rows[0].keys()) if b_rows else ["chart"], b_rows)
    write_csv("nd6-phase-c.csv", list(c_rows[0].keys()) if c_rows else ["chart"], c_rows)
    write_csv("nd6-phase-d-latency.csv", list(dlat_rows[0].keys()) if dlat_rows else ["chart"], dlat_rows)
    write_csv("nd6-phase-d-speedup.csv", list(dspeed_rows[0].keys()) if dspeed_rows else ["chart"], dspeed_rows)
    write_csv("nd6-file-store.csv", list(fs_rows[0].keys()) if fs_rows else ["chart"], fs_rows)
    write_csv("nd6-p95.csv", list(p95_rows[0].keys()) if p95_rows else ["chart"], p95_rows)
    if log_rows:
        write_csv("fairness-pairs.csv", list(log_rows[0].keys()), log_rows)
    print("done")


if __name__ == "__main__":
    sys.exit(main())
