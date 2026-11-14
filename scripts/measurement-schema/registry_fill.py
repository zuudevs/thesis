#!/usr/bin/env python3
"""registry_fill — version-registry backfill for measurement records (R5-13).

Scans measurement records (``reports/**`` and ``out/measurements/**``,
READ-ONLY) and writes a sidecar per run into ``reports/registry/`` holding
the standard version triple for ze_json runs:

  js_version    - ZE_JSON_JS_VERSION (bindings/js independent semver)
  core_version  - core semver (CMake project VERSION / vcpkg.json)
  abi_version   - ze_abi_version() value = ZE_JSON_CORE_VERSION_NUMBER
  wasm_sha256   - sha256 of the actually-loaded wasm artifact

The exhibits themselves (out/raw, committed record files) are NEVER
modified - AGENTS section 4 keeps artifacts verbatim; the sidecar is the
normalized provenance layer. Resolution sources, in priority order:

  record   - the record already carries js/core/abi_version (post-R5-13
             harnesses read the generated bindings/js/package.json).
  git      - resolved from the ze_json repo at the pinned commit
             (``library.version`` carries ``ze_json@<hash>``).
  inferred - ABI numeric read from the record's language_runtime label
             ("C-ABI v3") when the commit is not resolvable locally.
  unknown  - nothing resolvable; the gap is reported, never guessed.

saq_baseline records carry no ze_json version registry and are skipped.

Usage (stdlib only, no third-party deps):
  python scripts/measurement-schema/registry_fill.py             # write
  python scripts/measurement-schema/registry_fill.py --dry-run   # report
  python scripts/measurement-schema/registry_fill.py --scan out/measurements
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCAN = ["reports", "out/measurements"]
ZMJS = "bindings/js/ze_json.mjs"
PKG = "bindings/js/package.json"
VCPKG = "vcpkg.json"
CMAKE = "CMakeLists.txt"
WASM_SHA = "bindings/js/ze_json.wasm.sha256"

ZE_HASH_RE = re.compile(r"ze_json@([0-9a-fA-F]{7,40})")
SAQ_HASH_RE = re.compile(r"saq-report@([0-9a-fA-F]{7,40})")
ABI_LABEL_RE = re.compile(r"(?:C-)?ABI\s*v?(\d+)")
ABI_LITERAL_RE = re.compile(r"export\s+const\s+ABI_VERSION\s*=\s*(\d+)")
ABI_DERIVED_RE = re.compile(r"export\s+const\s+ABI_VERSION\s*=\s*CORE_VERSION_NUMBER")
SEMVER_RE = re.compile(r'"version"\s*:\s*"(\d+\.\d+\.\d+)"')
CMAKE_VERSION_RE = re.compile(r"VERSION\s+(\d+\.\d+\.\d+)")
SEMVER_ONLY_RE = re.compile(r"^\d+\.\d+\.\d+$")
RUNID_HASH_RE = re.compile(r"-([0-9a-f]{7,40})$")
NATIVE_RT_RE = re.compile(r"C\+\+23|native-(?:release|debug|pgo|sanitize)")

# Known wasm artifact identities -> ze_abi_version() of that binary.
# Sources: swap-driver sandwich logs (out/raw/o1_7_sandwich_log.json,
# o1_ladder*_log.json - sha256 verified per swap) and build-wasm gates
# (scripts/build-wasm.ps1 -VerifyOnly output, reports/ of the era).
KNOWN_ARTIFACT_ABI = {
    # v3 artifact shipped for ND-10 E1/E2 (ze_json pre-O1-7 wasm64).
    "35b7f7737f0806f651d8b0acc79a2b6013d94ae26b7c68a83af7e16d7eef3185": 3,
    # v4 artifact (O1-7 thin-step family, tree ae209f0/fe877f2).
    "c5b42b7d1782294e3dbb1db984f05b8121ce71c42943c75e5d8cfd3e19f6c4fd": 4,
    # post-registry artifact (R5-13, tree ee5e000, abi 2026000200).
    "19baac8c84ccc0cdbd965586e483526d72ea99feb24681313f1c096cae00f57f": 2026000200,
}


def git_show(commit: str, path: str) -> str | None:
    """Read <commit>:<path> from the ze_json submodule repo, None on failure."""
    cmd = ["git", "-C", str(PROJECT_ROOT / "ze_json"),
           "show", f"{commit}:{path}"]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=30, check=True)
        return proc.stdout.decode("utf-8", errors="replace")
    except (subprocess.SubprocessError, OSError):
        return None


def parse_pkg(text: str) -> dict:
    """Extract version/coreVersion/coreSemver from package.json text."""
    out = {"version": None, "coreVersion": None, "coreSemver": None}
    m = SEMVER_RE.search(text)
    if m:
        out["version"] = m.group(1)
    m = re.search(r'"coreVersion"\s*:\s*(\d+)', text)
    if m:
        out["coreVersion"] = int(m.group(1))
    m = re.search(r'"coreSemver"\s*:\s*"([^"]+)"', text)
    if m:
        out["coreSemver"] = m.group(1)
    return out


def resolve_from_git(commit: str) -> tuple[dict, list]:
    """Resolve the version triple at a pinned ze_json commit."""
    versions = {"js_version": None, "core_version": None,
                "abi_version": None, "wasm_sha256": None}
    notes = []

    pkg_text = git_show(commit, PKG)
    pkg = parse_pkg(pkg_text) if pkg_text else {}
    if pkg.get("version"):
        versions["js_version"] = pkg["version"]

    mjs_text = git_show(commit, ZMJS)
    if mjs_text:
        m = ABI_LITERAL_RE.search(mjs_text)
        if m:
            versions["abi_version"] = int(m.group(1))
        elif ABI_DERIVED_RE.search(mjs_text) and pkg.get("coreVersion"):
            versions["abi_version"] = pkg["coreVersion"]

    vcpkg_text = git_show(commit, VCPKG)
    if vcpkg_text:
        m = SEMVER_RE.search(vcpkg_text)
        if m:
            versions["core_version"] = m.group(1)
    if versions["core_version"] is None:
        cmake_text = git_show(commit, CMAKE)
        if cmake_text:
            m = CMAKE_VERSION_RE.search(cmake_text)
            if m:
                versions["core_version"] = m.group(1)
    if versions["core_version"] is None and pkg.get("coreSemver"):
        versions["core_version"] = pkg["coreSemver"]

    # Preferred canonical identity: the tracked wasm sidecar at that commit.
    sha_text = git_show(commit, WASM_SHA)
    if sha_text:
        m = re.search(r"([0-9a-fA-F]{64})", sha_text)
        if m:
            versions["wasm_sha256"] = m.group(1).lower()

    if any(v is None for v in versions.values()):
        notes.append(f"partial resolution at ze_json@{commit}")
    return versions, notes


def record_versions(record: dict) -> dict:
    """Standard fields straight from the record (post-R5-13 harnesses)."""
    lib = record.get("library") or {}
    return {
        "js_version": lib.get("js_version"),
        "core_version": lib.get("core_version"),
        "abi_version": lib.get("abi_version"),
        "wasm_sha256": lib.get("artifact_sha256"),
    }


def fill_gaps(base: dict, patch: dict) -> tuple[dict, list]:
    """Overlay non-None patch values onto base, keeping provenance notes."""
    merged = dict(base)
    notes = []
    for key, value in patch.items():
        if value is None:
            continue
        if merged.get(key) is None:
            merged[key] = value
        elif merged[key] != value:
            notes.append(f"conflict {key}: {merged[key]} vs {value} (kept first)")
    return merged, notes


def infer_abi_from_label(record: dict) -> int | None:
    runtime = str((record.get("library") or {}).get("language_runtime") or "")
    m = ABI_LABEL_RE.search(runtime)
    return int(m.group(1)) if m else None


def infer_from_record(record: dict, native: bool = False
                      ) -> tuple[dict, list]:
    """Legacy-harness records (pre-R5-13) carry usable registry data:

    - ``library.version`` written as a plain semver is the npm/js version
      the old wasm harness read from bindings/js/package.json; for native
      C++ gbench/gtest records it is the core semver instead.
    - the language_runtime label carries the loaded artifact's ABI
      ("C-ABI v3") - authoritative for wasm-swap runs (O1 ladder).
    - pre-registry policy mirrored core semver into the npm version
      (verified pairs 0.1.0/0.1.1/0.1.2 across the manual-sync commits),
      so core_version := js_version is a documented, cited assumption.
    """
    lib = record.get("library") or {}
    version = str(lib.get("version") or "").strip()
    versions, notes = {}, []
    if SEMVER_ONLY_RE.match(version):
        if native:
            versions["core_version"] = version
            notes.append("core_version from legacy library.version "
                         "(native record: plain semver = core semver)")
        else:
            versions["js_version"] = version
            notes.append("js_version from legacy library.version "
                         "(plain semver)")
            versions["core_version"] = version
            notes.append("core_version paired with js_version (pre-registry "
                         "manual sync policy; pairs verified at 47eb27a/"
                         "9d1d6a2/26769c0)")
    abi = infer_abi_from_label(record)
    if abi is not None:
        versions["abi_version"] = abi
        notes.append(f"abi_version from language_runtime label (ABI v{abi})")
    sha = lib.get("artifact_sha256")
    if isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{64}", sha):
        versions["wasm_sha256"] = sha
    return versions, notes


def is_native_record(record: dict) -> bool:
    """Native C++ records (gbench/gtest export): no wasm C-ABI surface."""
    rt = str((record.get("library") or {}).get("language_runtime") or "")
    return bool(NATIVE_RT_RE.search(rt))


def is_gap(versions: dict) -> bool:
    return any(versions.get(k) is None
               for k in ("js_version", "core_version", "abi_version"))


def scan_records(scan_roots: list[Path]) -> tuple[list, int, int]:
    """Collect (record, path) pairs for ze_json runs; skip saq_baseline."""
    found, skipped, broken = [], 0, 0
    seen_paths = set()
    for root in scan_roots:
        if not root.is_dir():
            continue
        pattern = "*record*.json"
        for path in sorted(root.rglob(pattern)):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                broken += 1
                continue
            if not isinstance(record, dict):
                broken += 1
                continue
            lib = record.get("library") or {}
            name = lib.get("name")
            if name == "saq_baseline":
                skipped += 1
                continue
            if name != "ze_json" or not record.get("run_id"):
                broken += 1
                continue
            found.append((record, path))
    return found, skipped, broken


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scan", nargs="*", default=DEFAULT_SCAN,
                    help="directories to scan for measurement records")
    ap.add_argument("--out", default=str(PROJECT_ROOT / "reports" / "registry"),
                    help="sidecar output directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="report only; write nothing")
    args = ap.parse_args()

    scan_roots = [(PROJECT_ROOT / s) if not Path(s).is_absolute() else Path(s)
                  for s in args.scan]
    records, skipped_baseline, broken = scan_records(scan_roots)

    by_run: dict[str, dict] = {}
    for record, path in records:
        run_id = record["run_id"]
        entry = by_run.setdefault(run_id, {
            "record": record, "paths": [], "versions": None, "notes": []})
        entry["paths"].append(str(path.relative_to(PROJECT_ROOT))
                              if path.is_relative_to(PROJECT_ROOT) else str(path))
        rv = record_versions(record)
        if entry["versions"] is None:
            entry["versions"] = rv
        else:
            entry["versions"], nn = fill_gaps(entry["versions"], rv)
            entry["notes"].extend(nn)

    out_dir = Path(args.out)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    git_cache: dict[str, dict] = {}
    summary = {"record": 0, "git": 0, "inferred": 0, "unknown": 0}
    unknowns = []
    written = 0

    for run_id, entry in sorted(by_run.items()):
        record = entry["record"]
        versions = dict(entry["versions"] or {})
        notes = list(entry["notes"])
        native = is_native_record(record)

        lib = record.get("library") or {}
        version_str = str(lib.get("version") or "")
        ze_m = ZE_HASH_RE.search(version_str)
        ze_hash = ze_m.group(1) if ze_m else None
        saq_m = SAQ_HASH_RE.search(version_str)
        saq_hash = saq_m.group(1) if saq_m else None

        # CMake-generated records (gbench/gtest export) stamp RUN_ID with the
        # ze_json commit itself; node-harness records stamp the root commit
        # and carry ze_json@<hash> inside library.version instead.
        rid_m = RUNID_HASH_RE.search(run_id)
        rid_hash = rid_m.group(1) if rid_m else None

        source = "record" if not is_gap(versions) else None

        for candidate in (ze_hash, rid_hash):
            if source is not None or not candidate:
                continue
            if candidate not in git_cache:
                resolved, rnotes = resolve_from_git(candidate)
                git_cache[candidate] = resolved
                notes.extend(rnotes)
            versions, n = fill_gaps(versions, git_cache.get(candidate, {}))
            notes.extend(n)
            if not is_gap(versions):
                source = "git"

        if source is None:
            inferred, n = infer_from_record(record, native=native)
            versions, n2 = fill_gaps(versions, inferred)
            notes.extend(n)
            notes.extend(n2)

        complete = not is_gap(versions) or (
            native and versions.get("core_version") is not None)
        if source is None and complete:
            source = "inferred"

        # Loaded-artifact identity, strongest first:
        #   1. record artifact_sha256 that maps to a KNOWN artifact - that
        #      binary's ze_abi_version() is fact (ND-10/ND-12 runs carry the
        #      v4 artifact sha while the harness HARDCODED a "v3" label).
        #   2. language_runtime ABI label - dynamic in the swap-aware
        #      drivers and correct for the old eras it covered; the only
        #      loaded-artifact witness left when no sha is recorded
        #      (nd6-era harness, O1 ladder S0-S2 v3 swaps at tree fe877f2).
        label_abi = infer_abi_from_label(record)
        rec_sha = (lib.get("artifact_sha256") or None)
        if isinstance(rec_sha, str) and \
                not re.fullmatch(r"[0-9a-f]{64}", rec_sha):
            rec_sha = None
        known_abi = KNOWN_ARTIFACT_ABI.get(rec_sha)
        if known_abi is not None:
            if versions.get("abi_version") != known_abi:
                notes.append(
                    f"abi_version {versions.get('abi_version')} -> "
                    f"{known_abi}: record artifact_sha256 matches a known "
                    "wasm binary (label may be a hardcoded harness string)")
                versions["abi_version"] = known_abi
        elif label_abi is not None:
            if versions.get("abi_version") != label_abi:
                notes.append(f"abi_version {versions.get('abi_version')} "
                             f"-> {label_abi}: language_runtime label is "
                             "the loaded-artifact truth (wasm-swap runs)")
                versions["abi_version"] = label_abi
        if source is None and native and \
                versions.get("core_version") is not None:
            notes.append("js_version/abi_version not applicable "
                         "(native C++ record, no wasm C-ABI surface)")
            source = "inferred"

        summary[source] += 1
        if source == "unknown":
            unknowns.append(run_id)

        tree_commit = ze_hash or rid_hash
        sidecar = {
            "schema_version": "1.0.0",
            "kind": "version_registry",
            "run_id": run_id,
            "site": record.get("site"),
            "phase": record.get("phase"),
            "generator": "registry_fill.py",
            "library": {"name": "ze_json"},
            "git_commit": {
                "ze_json": tree_commit,
                "ze_json_source": ("library.version pin" if ze_hash else
                                   "run_id suffix (cmake-generated RUN_ID)"
                                   if rid_hash else None),
                "saq_report": saq_hash,
            },
            "versions": versions,
            "source": source,
            "source_paths": entry["paths"],
            "resolved_at": datetime.now(timezone.utc).astimezone().isoformat(
                timespec="seconds"),
            "notes": notes,
        }
        if not args.dry_run:
            target = out_dir / f"{run_id}.json"
            target.write_text(json.dumps(sidecar, indent=2) + "\n",
                              encoding="utf-8")
            written += 1

    total = sum(summary.values())
    print(f"scanned: {len(records)} ze_json record file(s) "
          f"-> {len(by_run)} unique run(s)")
    print(f"skipped: {skipped_baseline} saq_baseline record file(s), "
          f"{broken} unreadable/non-ze_json")
    print(f"sidecars: {written if not args.dry_run else total} "
          f"(dry-run={args.dry_run}) by source: "
          f"record={summary['record']} git={summary['git']} "
          f"inferred={summary['inferred']} unknown={summary['unknown']}")
    if unknowns:
        print("unknown (unresolvable) runs:")
        for u in unknowns:
            print(f"  - {u}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
