#!/usr/bin/env python3
# ============================================================================
#  audit_raw.py — Gerbang integritas artefak pengukuran di $RAW
# ============================================================================
#  Memeriksa report + sidecar di bawah $RAW/{test,benchmark,coverage,
#  profiling} terhadap aturan provenance (docs/telemetry-sidecar.md), dengan
#  kontrak PER-PAKET (tiap paket punya skema sendiri):
#
#  ze_json   — R1 nama {TARGET}_{RUN_ID}.json (RUN_ID = <host>-<stamp 14-17
#              digit>-<commit hex 7-40 | nogit>); R2 berpasangan dengan
#              .metadata.json; R3 context.ze_run_id == RUN_ID & tanpa
#              error_occurred=true (khusus report benchmark); R4 sidecar
#              memuat schema_version + machine.cpu_model + datasets[].sha256
#              hex64 yang semuanya tercantum di manifest korpus aktif
#              ($RAW/ze_json/manifest.json); R5 layout nested <kategori>/<paket>/
#  saq-report— R1 nama = RUN_ID polos; R3 metadata.run_id == nama file &
#              errors kosong; R4 schema_version + metadata ada (report
#              self-contained, TANPA sidecar terpisah)
#  legacy    — file di root kategori (layout lama) hanya dicek R1 ze_json +
#              R5 (secara historis akan DELETE)
#
#  manifest.json di folder paket mana pun BUKAN artefak pengukuran — dilewati.
#
#  Mode:
#    python audit_raw.py            -> dry-run: daftar KEEP/DELETE + alasan
#    python audit_raw.py --prune    -> hapus berkas DELETE, lalu re-audit
# ============================================================================
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

CATEGORIES = ("test", "benchmark", "coverage", "profiling")
RUN_ID_RE = re.compile(r"^(?P<host>.+)-(?P<stamp>\d{14,17})-(?P<commit>nogit|[0-9a-fA-F]{7,40})$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def load_manifest_by_sha(raw_dir: Path) -> dict[str, str]:
    """sha256 -> path dataset dari manifest korpus aktif ({} bila tiada)."""
    path = raw_dir / "ze_json" / "manifest.json"
    if not path.is_file():
        return {}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        item.get("sha256"): item.get("path", "?")
        for item in manifest.get("files", [])
        if item.get("sha256")
    }


def audit(raw_dir: Path) -> list[dict]:
    """Tinjau semua berkas artefak; tiap record: {file, verdict, reasons}."""
    manifest_by_sha = load_manifest_by_sha(raw_dir)
    records: list[dict] = []

    report_files: list[Path] = []
    sidecar_files: set[Path] = set()
    for category in CATEGORIES:
        cat_dir = raw_dir / category
        if not cat_dir.is_dir():
            continue
        for file in sorted(cat_dir.rglob("*.json")):
            if file.name == "manifest.json":
                continue  # jangkar korpus, bukan artefak pengukuran
            if file.name.endswith(".metadata.json"):
                sidecar_files.add(file)
            else:
                report_files.append(file)

    def add(path: Path, verdict: str, *reasons: str) -> None:
        records.append({
            "file": path.relative_to(raw_dir).as_posix(),
            "verdict": verdict,
            "reasons": list(reasons),
        })

    for report in report_files:
        rel_parts = report.relative_to(raw_dir).parts
        package = rel_parts[1] if len(rel_parts) >= 3 else None
        stem = report.stem
        reasons: list[str] = []
        verdict = "KEEP"

        # ---- R1 nama ------------------------------------------------------
        if package == "saq-report":
            # Nama file = RUN_ID polos.
            run_id = stem if RUN_ID_RE.fullmatch(stem) else None
            if run_id is None:
                verdict = "DELETE"
                reasons.append("R1: nama bukan RUN_ID valid (<host>-<stamp>-<commit>)")
        else:
            # ze_json / legacy: {TARGET}_{RUN_ID}.json
            match = re.fullmatch(r"(?P<target>.+)_(?P<run_id>.+)", stem)
            run_id = match.group("run_id") if match else None
            if not match or not RUN_ID_RE.fullmatch(run_id):
                verdict = "DELETE"
                reasons.append("R1: RUN_ID di nama tidak valid (harap <TARGET>_<host>-<stamp>-<commit>)")

        # ---- R2 pasangan sidecar (ze_json/legacy saja) ---------------------
        sidecar = report.with_name(stem + ".metadata.json")
        has_sidecar = sidecar in sidecar_files
        if package in (None, "ze_json") and not has_sidecar:
            verdict = "DELETE"
            reasons.append("R2: tanpa sidecar .metadata.json berpasangan")

        # ---- R3 isi report -------------------------------------------------
        data = None
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            verdict = "DELETE"
            reasons.append(f"R3: report tak bisa di-parse: {error}")

        if data is not None:
            if package == "saq-report":
                meta = data.get("metadata", {})
                if run_id and meta.get("run_id") != run_id:
                    verdict = "DELETE"
                    reasons.append("R3: metadata.run_id != RUN_ID nama file")
                if data.get("errors"):
                    verdict = "DELETE"
                    reasons.append(f"R3: report memuat {len(data['errors'])} error")
            elif package == "ze_json":
                # google-benchmark report punya context; gtest report tidak.
                if "benchmarks" in data and run_id and \
                        data.get("context", {}).get("ze_run_id") != run_id:
                    verdict = "DELETE"
                    reasons.append("R3: context.ze_run_id != RUN_ID nama file")
                if any(b.get("error_occurred") for b in data.get("benchmarks", [])):
                    verdict = "DELETE"
                    reasons.append("R3: ada benchmark error_occurred=true")
            # legacy: cukup R1+R5 (data historis, tidak dipakai analisa)

        # ---- R5 layout nested per-paket ------------------------------------
        if len(rel_parts) < 3:
            verdict = "DELETE"
            reasons.append("R5: artefak di root kategori — layout lama (harus <kategori>/<paket>/)")

        # ---- R4 sidecar (ze_json) -------------------------------------------
        if package == "ze_json" and has_sidecar:
            try:
                doc = json.loads(sidecar.read_text(encoding="utf-8"))
                if not doc.get("schema_version"):
                    verdict = "DELETE"
                    reasons.append("R4: sidecar tanpa schema_version")
                meta = doc.get("metadata", {})
                if not meta.get("machine", {}).get("cpu_model"):
                    verdict = "DELETE"
                    reasons.append("R4: sidecar tanpa machine.cpu_model")
                datasets = meta.get("datasets", [])
                if not datasets:
                    verdict = "DELETE"
                    reasons.append("R4: sidecar tanpa daftar dataset")
                bad_sha = [d.get("sha256") for d in datasets
                           if not HEX64_RE.fullmatch(str(d.get("sha256", "")))]
                if bad_sha:
                    verdict = "DELETE"
                    reasons.append(f"R4: {len(bad_sha)} dataset sha256 tidak berformat hex64")
                if manifest_by_sha:
                    stale = [d.get("sha256") for d in datasets
                             if d.get("sha256") not in manifest_by_sha]
                    if stale:
                        verdict = "DELETE"
                        reasons.append(
                            f"R4: {len(stale)} sha256 dataset tidak ada di manifest "
                            "korpus aktif (run memakai korpus lama)")
            except (OSError, json.JSONDecodeError) as error:
                verdict = "DELETE"
                reasons.append(f"R4: sidecar tak bisa di-parse: {error}")

        add(report, verdict, *reasons)

    # Sidecar yatim (tanpa report berpasangan) — hanya relevan utk ze_json.
    for sidecar in sorted(sidecar_files):
        paired_report = sidecar.with_name(sidecar.name[:-len(".metadata.json")] + ".json")
        if not paired_report.is_file():
            add(sidecar, "DELETE", "R2: sidecar yatim tanpa report .json berpasangan")

    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit integritas artefak pengukuran di $RAW")
    parser.add_argument("--raw", type=Path, default=None, help="Folder $RAW (default: env RAW)")
    parser.add_argument("--prune", action="store_true",
                        help="Hapus berkas DELETE lalu re-audit (default dry-run)")
    args = parser.parse_args()

    raw_dir = args.raw or Path(os.environ.get("RAW", ""))
    if not raw_dir.is_dir():
        print(f"$RAW tidak valid: {raw_dir}")
        return 2

    records = audit(raw_dir)
    deletes = [r for r in records if r["verdict"] == "DELETE"]
    keeps = [r for r in records if r["verdict"] == "KEEP"]

    print(f"Artefak diperiksa: {len(records)} | KEEP {len(keeps)} | DELETE {len(deletes)}")
    if deletes:
        print("\n-- Melanggar aturan:")
        for r in deletes:
            print(f"  {r['file']}")
            for reason in r["reasons"]:
                print(f"      - {reason}")

    if args.prune:
        removed_total = 0
        # Iteratif: menghapus report bisa membuat sidecar-nya yatim,
        # yang juga harus dihapus sampai audit stabil.
        for _ in range(5):
            batch = [r for r in audit(raw_dir) if r["verdict"] == "DELETE"]
            if not batch:
                break
            for r in batch:
                file = raw_dir / r["file"]
                if file.is_file():
                    file.unlink()
                    removed_total += 1
        print(f"\n[prune] {removed_total} berkas dihapus.")
        remaining = audit(raw_dir)
        still_bad = [r for r in remaining if r["verdict"] == "DELETE"]
        print(f"[prune] Re-audit: KEEP {len(remaining) - len(still_bad)} | DELETE {len(still_bad)}")
        return 0 if not still_bad else 1

    return 0 if not deletes else 1


if __name__ == "__main__":
    sys.exit(main())
