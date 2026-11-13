#!/usr/bin/env python3
"""make_corpus.py — deterministic benchmark corpus builder + manifest (TASKS P0-8).

Corpus families (docs/project/plans.md section 4, location corpus/benchmarks/<name>/):

  synthetic_1k|synthetic_10k|synthetic_100k|synthetic_1mb
      Size-sensitivity ladder (KiB nominal), one single document each, compact
      JSON (body-parse shaped: express.json() parses request bodies).
      Documents are byte-exact to their nominal target via an escape-free ASCII
      filler string, so the ladder is provable from the bytes themselves.
  saq_payload_v1
      Anonymized-but-structurally-faithful SAQ workloads mirroring saq-report
      v5 store shapes (config/paths.js + repositories/index.js): wrapped root
      objects for assistant/course/lecturer/schedule stores, bare array root
      for reports, bare object root for config_global; written pretty with
      indent 2 exactly like JsonRepository.write() = JSON.stringify(data, null, 2).
      Names/phones/emails come from synthetic pools — never real data
      (docs/project/plans.md section 8: SAQ data must not be shared).
  checker_batch
      Many small valid documents: pass1/2/3 copied byte-exact from
      corpus/test/json_checker plus 22 seeded valid documents exercising
      unicode, escapes, empty containers, floats/exponents, nesting, and
      >53-bit integers.

Each corpus directory receives a deterministic MANIFEST.json (timestamp-free,
so regenerating an unchanged corpus is byte-identical and its hash stays
stable). The measurement record field `corpus.sha256` is the sha256 of that
MANIFEST.json file itself, which makes corpus provenance reconstructible
(AGENTS.md section 4).

Usage:
    python scripts/corpus/make_corpus.py build all
    python scripts/corpus/make_corpus.py build synthetic_1mb --force
    python scripts/corpus/make_corpus.py verify --all
    python scripts/corpus/make_corpus.py verify --dir corpus/benchmarks/saq_payload_v1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH_ROOT = ROOT / "corpus" / "benchmarks"
CHECKER_DIR = ROOT / "corpus" / "test" / "json_checker"

DEFAULT_SEED = 20261108
KIB = 1024
DOC_VERSION = "1.0.0"

# Pure-ASCII hash-like pattern; safe inside JSON strings (no escaping drift),
# so a filler of length N adds exactly N bytes (byte-exact sizing).
FILLER_PATTERN = "d41d8c1e98f00b204e9800998ecf8427e-ab1f"  # 36 ascii chars

CORPUS_NAMES = ("synthetic_1k", "synthetic_10k", "synthetic_100k", "synthetic_1mb",
                "saq_payload_v1", "checker_batch")

PURPOSES = {
    "synthetic_1k": "size sensitivity baseline (~1 KiB single document, body-parse shaped)",
    "synthetic_10k": "size sensitivity ~10 KiB (payload-scale requests)",
    "synthetic_100k": "size sensitivity ~100 KiB (payload-scale requests)",
    "synthetic_1mb": "stress whole-document parse ~1 MiB (body-parse role)",
    "saq_payload_v1": "SAQ store-shaped workloads (anonymized; pretty indent-2 like JsonRepository)",
    "checker_batch": "many small valid documents (whole-document batch parse stress)",
}


# ---------------------------------------------------------------- helpers


def serialize(obj, indent: int | None = None) -> bytes:
    """Node-compatible JSON bytes: raw UTF-8 (ensure_ascii=False);
    indent=2 separators (",", ": ") match JSON.stringify(data, null, 2)."""
    if indent is None:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return json.dumps(obj, ensure_ascii=False, indent=indent, separators=(",", ": ")).encode("utf-8")


def write_bytes(path: Path, payload: bytes) -> tuple[int, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return len(payload), hashlib.sha256(payload).hexdigest()


def object_id(rng: random.Random) -> str:
    """24-hex ObjectId-like id (structure only; synthetic data)."""
    return f"{rng.getrandbits(96):024x}"


def fuzzy(rng: random.Random, alphabet: str, length: int) -> str:
    return "".join(rng.choice(alphabet) for _ in range(length))


def refuse(message: str):
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


# ---------------------------------------------------------------- synthetic


LABELS = ["alpha", "beta", "gamma", "delta", "omega", "theta", "sigma"]
TAGS = ["parsing", "simd", "ondemand", "scalar", "streaming", "batch", "wasm", "native"]
UNICODE_TOKENS = ["café", "naïve", "クール", "微基准", "✔ parsed", "🦉 owl", "nański"]
NUMBERS = [1.5, -2.25, 3.14159265358979, 2.5e-7, -1.25e8, 0.0]


def _synthetic_item(seed: int, index: int) -> dict:
    """Deterministic per-index item (child seed => item stream is count-independent)."""
    rng = random.Random(seed * 1_000_003 + index * 31 + 17)
    return {
        "index": index,
        "name": f"item-{index:05d}",
        "label": rng.choice(LABELS),
        "score": round(rng.uniform(-1000.0, 1000.0), 6),
        "weight": rng.randint(0, 100_000),
        "coefficient": NUMBERS[index % len(NUMBERS)],
        "tags": [rng.choice(TAGS) for _ in range(1 + index % 4)],
        "meta": {
            "sequence": index % 12,
            "unicode": UNICODE_TOKENS[index % len(UNICODE_TOKENS)] if index % 7 == 0 else "plain",
            "escaped": 'quote " back\\\\slash\ttab' if index % 11 == 0 else "safe",
        },
        "values": {
            "integers": [rng.randint(0, 10 ** 9) for _ in range(4 + index % 5)],
            "flags": [index % 3 == 0, index % 5 == 0, index % 9 == 0],
        },
        "active": index % 3 != 0,
    }


def build_synthetic(corpus_name: str, target_bytes: int, seed: int) -> list[tuple[str, bytes, str, str]]:
    """One document byte-exact at target_bytes (items count down; ASCII filler makes up the tail)."""
    header = {"corpus": corpus_name, "generator_seed": seed}
    probe_empty = serialize({**header, "items": [], "filler": ""})
    probe_item = serialize(_synthetic_item(seed, 0))
    avg_item = len(probe_item)
    count = max(2, (target_bytes - len(probe_empty) - 2 * avg_item) // avg_item)

    while count >= 2:
        items = [_synthetic_item(seed, i) for i in range(count)]
        base = serialize({**header, "items": items, "filler": ""})
        delta = target_bytes - len(base)
        if delta < 0:
            count -= 1
            continue
        filler = (FILLER_PATTERN * ((delta // len(FILLER_PATTERN)) + 1))[:delta]
        payload = serialize({**header, "items": items, "filler": filler})
        assert len(payload) == target_bytes, (
            f"{corpus_name}: sizing drift ({len(payload)} != {target_bytes})"
        )
        return [( "doc_01.json", payload, "generated", "single-document size ladder" )]
    raise RuntimeError(f"{corpus_name}: target bytes unreachable — structure exceeds corpus")


def build_synthetic_corpus(name: str, seed: int) -> list[tuple[str, bytes, str, str]]:
    targets = {
        "synthetic_1k": 1 * KIB,
        "synthetic_10k": 10 * KIB,
        "synthetic_100k": 100 * KIB,
        "synthetic_1mb": 1024 * KIB,
    }
    return build_synthetic(name, targets[name], seed)


# ---------------------------------------------------------------- saq_payload_v1

ASSISTANT_SHORT = ["Azka", "Bima", "Cahya", "Damar", "Eka", "Fajar", "Gilang", "Hana",
                   "Ifa", "Jati", "Kirana", "Laila", "Marsya", "Nadine", "Oka", "Putri",
                   "Rizky", "Salma", "Tirta", "Umar", "Vina", "Wafa", "Yoga", "Zaki", "Bani"]
ASSISTANT_LONG = [
    "Azka Ramadhani", "Bima Setiawan", "Cahya Pratama", "Damar Ardiansyah",
    "Eka Yudhistira", "Fajar Nugraha", "Gilang Permana", "Hana Aulia",
    "Ifa Kusumawati", "Jati Wibowo", "Kirana Puspita", "Laila Syafa",
    "Marsya Ramadhina", "Nadine Prasetya", "Oka Wibawa", "Putri Larasati",
    "Rizky Amelia", "Salma Faradisa", "Tirta Segara", "Umar Sanjaya",
    "Vina Octavia", "Wafa Hanifah", "Yoga Prasetyo", "Zaki Mubarok", "Bani Saffan",
]
LECTURERS = [
    ("Ananta Wijaya", "Dr., S.T., M.T."), ("Bani Soegiarto", "Prof. Dr.-Ing."),
    ("Cendra Hapsari", "S.Kom., M.Kom."), ("Dewisri Nakula", "S.T., M.Sc."),
    ("Endah Wilujeng", "Dr. Sc."), ("Fandi Alfarizi", "S.T."),
    ("Ganjar Simpatupang", "Ph.D."), ("Harja Wicaksono", "Ir., M.Sc."),
    ("Ismi Lutfiana", "S.Kom."), ("Joffry Basukin", "Dr.rer.nat."),
    ("Kinanti Pawestri", "S.T., M.T."), ("Lukmanul Hakim", "M.Kom."),
    ("Meilani Roslia", "Ph.D."), ("Nuryadi Sentosa", "S.T., M.Sc."),
    ("Oky Supriyadi", "S.Kom., M.MT."),
]
DEPARTMENTS = ["Teknik Informatika", "Teknologi Informasi", "Sistem Informasi", "Sains Data"]
COURSES = [
    ("IF4011", "Pemrograman Lanjut", 3), ("IF4012", "Basis Data", 3),
    ("IF4013", "Jaringan Komputer", 3), ("IF4014", "Sistem Operasi", 4),
    ("IF4201", "Rekayasa Perangkat Lunak", 3), ("IF4202", "Keamanan Aplikasi", 3),
    ("IF4203", "Pemrograman Website", 3), ("IF4204", "Analisis Algoritme", 3),
    ("IF4301", "Komputasi Awan", 3), ("IF4302", "Perencanaan Bisnis Digital", 2),
    ("TS4311", "Pemrosesan Data", 4), ("TS4312", "Metodologi Penelitian", 2),
    ("BD4021", "Kecerdasan Buatan", 3), ("BD4022", "Data Mining", 3),
]
DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]
TIME_SLOTS = ["07:00-09:40", "10:00-12:40", "13:00-15:40", "15:45-18:25", "19:00-21:40"]
CLASS_CODES = ["A-1", "A-2", "B-1", "B-2", "C-1"]
MATERI_POOL = [
    "Parsing yang hemat memori", "Perancangan antarmuka layar", "Membaca dan memvalidasi data",
    "Orientasi obyek dan encapsulasi", "Format pertukaran data", "Struktur data konversi",
    "Git dan kolaborasi repositori", "Pemodelan basis data relasional",
    "Uji coba integrasi berkelanjutan", "Instrumentasi pengukuran",
]
REPORT_STATUSES = ["Selesai", "Menunggu", "Pembatalan", "Draf"]


def _phone(rng: random.Random) -> str:
    return f"+62-81{rng.randint(10, 89)}-{fuzzy(rng, '0123456789', 4)}-{rng.randint(1000, 9999):04d}"


def build_saq(seed: int) -> list[tuple[str, bytes, str, str]]:
    """Six store-shaped documents mirroring saq-report v5 (anonymized, pretty indent-2)."""
    rng = random.Random(seed)
    assistant_ids = [object_id(rng) for _ in range(25)]
    course_ids = [object_id(rng) for _ in range(len(COURSES))]
    lecturer_ids = [object_id(rng) for _ in range(len(LECTURERS))]
    schedule_ids = [object_id(rng) for _ in range(120)]

    assistants = []
    for idx, aid in enumerate(assistant_ids):
        assistants.append({
            "id": aid,
            "nama_asisten": ASSISTANT_LONG[idx].upper(),
            "nama_panjang": ASSISTANT_LONG[idx],
            "panggilan": ASSISTANT_SHORT[idx],
            "no_telp": _phone(rng),
            "ttd": f"ttd_{aid[:10]}.png" if idx % 2 == 0 else None,
        })

    courses = []
    for idx, (code, name, credits) in enumerate(COURSES):
        courses.append({
            "id": course_ids[idx],
            "code": code,
            "name": name,
            "credits": credits,
            "description": f"Mata kuliah {name} pada program studi "
                           f"{DEPARTMENTS[idx % len(DEPARTMENTS)]}.",
            "department": DEPARTMENTS[idx % len(DEPARTMENTS)],
            "semester": 1 + (idx % 8),
        })

    lecturers = []
    for idx, (name, title) in enumerate(LECTURERS):
        mail_local = name.lower().replace(" ", ".")
        lecturers.append({
            "id": lecturer_ids[idx],
            "name": name,
            "title": title,
            "email": f"{mail_local}@example.ac.id",
            "phone": _phone(rng),
            "department": DEPARTMENTS[idx % len(DEPARTMENTS)],
        })

    schedules = []
    for idx, sid in enumerate(schedule_ids):
        schedules.append({
            "id": sid,
            "course_id": course_ids[idx % len(course_ids)],
            "lecturer_id": lecturer_ids[idx % len(lecturer_ids)],
            "class": CLASS_CODES[idx % len(CLASS_CODES)],
            "day": DAYS[idx % len(DAYS)],
            "time": TIME_SLOTS[idx % len(TIME_SLOTS)],
            "pj_assistant_id": assistant_ids[idx % len(assistant_ids)],
            "assistant_ids": assistant_ids[idx:(idx + 2 + idx % 4)],
        })

    rng_reports = random.Random(seed + 1)
    reports = []
    for idx in range(60):
        serial = 1 + idx % 27
        month = 1 + (idx % 5)
        year = 2026 - (idx % 2)
        weekday = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Ahad"][
            (serial + 4) % 7]
        image_id = object_id(rng_reports) if idx % 4 == 0 else None
        reports.append({
            "id": object_id(rng_reports),
            "schedule_id": schedule_ids[idx % len(schedule_ids)],
            "date": f"{year}-{month:02d}-{serial:02d}",
            "formattedDate": f"{weekday}, {serial} {['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'][month - 1]} {year}",
            "materi": MATERI_POOL[idx % len(MATERI_POOL)],
            "deskripsiKegiatan": (f"Aktivitas {MATERI_POOL[idx % len(MATERI_POOL)].lower()} "
                                  f"bersama {2 + idx % 5} asisten pada kelas "
                                  f"{CLASS_CODES[idx % len(CLASS_CODES)]} sesi {1 + idx % 4}."),
            "keterangan": "Jadwal terganti bulan depan." if idx % 9 == 0 else "",
            "attending_assistant_ids":
                assistant_ids[(idx * 3) % len(assistant_ids):][:2 + idx % 5],
            "status": REPORT_STATUSES[idx % len(REPORT_STATUSES)],
            "imagePath": f"laporan_images/report_{image_id[:10]}.png" if image_id else None,
            "imageFilename": f"report_{image_id[:10]}.png" if image_id else None,
        })

    global_config = {
        "semester": {"year": 2026, "term": "Ganjil"},
        "kurikulum": "2019",
        "jam_kerja": {"masuk": "08:00", "keluar": "17:00"},
        "batas_input_laporan": {"hari": "Sabtu", "jam": "23:59"},
        "notifikasi_wa_on": True,
        "cetak_kop_surat": "Universitas Teknologi Contoh",
        "ukuran_font_laporan": 12,
        "reset_mingguan": False,
    }

    docs = [
        ("config_asisten.json", {"assistants": assistants}, "wrapped {'assistants': [...]}"),
        ("courses.json", {"courses": courses}, "wrapped {'courses': [...]}"),
        ("lecturers.json", {"lecturers": lecturers}, "wrapped {'lecturers': [...]}"),
        ("schedules.json", {"schedules": schedules}, "wrapped {'schedules': [...]}"),
        ("reports.json", reports, "array root (repo rootKey null)"),
        ("config_global.json", global_config, "object root (repo rootKey null)"),
    ]
    return [(file, serialize(obj, indent=2), "generated_anonymized", role)
            for file, obj, role in docs]


# ---------------------------------------------------------------- checker_batch


def _checker_valid_doc(seed: int, index: int) -> dict:
    kind = index % 8
    rng = random.Random(seed * 7 + index)
    if kind == 0:
        return {"unicode": [UNICODE_TOKENS[i % len(UNICODE_TOKENS)] for i in range(6)],
                "text": f"Valid document #{index} — UTF-8 raw bytes and escapes."}
    if kind == 1:
        return {"array": [rng.randint(-2 ** 31, 2 ** 31 - 1) for _ in range(24)]}
    if kind == 2:
        return {"nested": {"level": 1,
                           "child": {"level": 2,
                                     "leaf": [1, {"a": 2}, None, True]}}}
    if kind == 3:
        return {"floats": [0.15625, -0.03125, 3.141592653589793, 6.02e23, 5e-324],
                "exponents": [1e0, 1e-3, 13.37e10]}
    if kind == 4:
        return {"strings": {"empty": "", "unicode": "café", "quote": 'He said "hi"',
                            "backslash": "back\\slash", "tab": "a\tb"}}
    if kind == 5:
        return {"empty": {"obj": {}, "arr": [], "null": None, "bools": [False, True]}}
    if kind == 6:
        return {"long": [{"i": i, "b": i % 2 == 0} for i in range(40)]}
    return {"big_int": 9007199254740993, "neg_big_int": -9007199254740993,
            "precision": 0.1 + 0.2}


def build_checker_batch(seed: int) -> list[tuple[str, bytes, str, str]]:
    """pass1..3 byte-exact copies + 22 seeded valid documents."""
    docs: list[tuple[str, bytes, str, str]] = []
    for pass_file in ("pass1.json", "pass2.json", "pass3.json"):
        source = CHECKER_DIR / pass_file
        docs.append((pass_file, source.read_bytes(),
                     f"copied:{source.relative_to(ROOT).as_posix()}", "json.org pass case"))
    for idx in range(22):
        docs.append((f"valid_{idx:02d}.json", serialize(_checker_valid_doc(seed, idx)),
                     "generated", "valid edge-shaped document"))
    return docs


# ---------------------------------------------------------------- build & verify

BUILDERS = {
    "synthetic_1k": build_synthetic_corpus,
    "synthetic_10k": build_synthetic_corpus,
    "synthetic_100k": build_synthetic_corpus,
    "synthetic_1mb": build_synthetic_corpus,
    "saq_payload_v1": build_saq,
    "checker_batch": build_checker_batch,
}


def build_corpus(corpus_name: str, seed: int, force: bool) -> dict:
    if corpus_name.startswith("synthetic_"):
        raw_docs = build_synthetic_corpus(corpus_name, seed)
    elif corpus_name == "saq_payload_v1":
        raw_docs = build_saq(seed)
    elif corpus_name == "checker_batch":
        raw_docs = build_checker_batch(seed)
    else:
        refuse(f"unknown corpus {corpus_name!r}")

    corpus_dir = BENCH_ROOT / corpus_name
    manifest_path = corpus_dir / "MANIFEST.json"
    if manifest_path.exists() and not force:
        refuse(f"{corpus_dir.relative_to(ROOT)} already has a MANIFEST.json (use --force)")

    documents = []
    for file, payload, source, role in sorted(raw_docs, key=lambda d: d[0]):
        size, sha = write_bytes(corpus_dir / file, payload)
        json.loads(payload.decode("utf-8"))  # every corpus document must be valid JSON
        documents.append({"file": file, "bytes": size, "sha256": sha,
                          "source": source, "role": role})

    manifest = {
        "schema_version": DOC_VERSION,
        "kind": "corpus_manifest",
        "corpus_name": corpus_name,
        "purpose": PURPOSES[corpus_name],
        "generation": {
            "script": "scripts/corpus/make_corpus.py",
            "seed": seed,
            "notes": "deterministic, timestamp-free; regenerating unchanged sources is byte-identical",
        },
        "encoding": "utf-8",
        "document_count": len(documents),
        "total_bytes": sum(d["bytes"] for d in documents),
        "max_document_bytes": max(d["bytes"] for d in documents),
        "documents": documents,
    }
    manifest_payload = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(manifest_payload)
    return {
        "name": corpus_name,
        "dir": str(corpus_dir.relative_to(ROOT)),
        "documents": len(documents),
        "total_bytes": manifest["total_bytes"],
        "max_document_bytes": manifest["max_document_bytes"],
        "corpus_sha256": hashlib.sha256(manifest_payload).hexdigest(),
    }


def verify_corpus(corpus_dir: Path) -> None:
    manifest_path = corpus_dir / "MANIFEST.json"
    if not manifest_path.exists():
        refuse(f"verify: no MANIFEST.json under {corpus_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("kind") != "corpus_manifest":
        refuse(f"verify: {corpus_dir} MANIFEST kind is {manifest.get('kind')!r}")

    computed = {
        "document_count": len(manifest["documents"]),
        "total_bytes": sum(d["bytes"] for d in manifest["documents"]),
        "max_document_bytes": max(d["bytes"] for d in manifest["documents"]),
    }
    for key, expected in computed.items():
        if manifest.get(key) != expected:
            refuse(f"verify: manifest.{key} = {manifest.get(key)} != computed {expected}")

    for entry in manifest["documents"]:
        path = corpus_dir / entry["file"]
        if not path.exists():
            refuse(f"verify: missing document {entry['file']}")
        payload = path.read_bytes()
        if len(payload) != entry["bytes"]:
            refuse(f"verify: {entry['file']} bytes {len(payload)} != manifest {entry['bytes']}")
        sha = hashlib.sha256(payload).hexdigest()
        if sha != entry["sha256"]:
            refuse(f"verify: {entry['file']} sha256 {sha} != manifest {entry['sha256']}")
        if entry.get("source", "").startswith("copied:"):
            reference = ROOT / entry["source"].split("copied:", 1)[1]
            if hashlib.sha256(reference.read_bytes()).hexdigest() != sha:
                refuse(f"verify: {entry['file']} no longer byte-identical to source "
                       f"{entry['source']}")
        json.loads(payload.decode("utf-8"))  # corpus documents must remain valid JSON

    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    print(f"OK   {corpus_dir.relative_to(ROOT)} - {computed['document_count']} doc(s), "
          f"{computed['total_bytes']} bytes, corpus_sha256={digest}")


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="generate (or regenerate with --force) corpus directories")
    b.add_argument("corpus", choices=["all", *CORPUS_NAMES])
    b.add_argument("--seed", type=int, default=DEFAULT_SEED)
    b.add_argument("--force", action="store_true",
                   help="overwrite an existing corpus (requires provenance review)")

    v = sub.add_parser("verify", help="recheck bytes/sha256/json against MANIFEST.json")
    v.add_argument("--dir", help="one corpus directory (contains MANIFEST.json)")
    v.add_argument("--all", action="store_true", help="verify every corpus under corpus/benchmarks")
    args = ap.parse_args(argv)

    if args.cmd == "verify":
        if args.all:
            targets = sorted(p for p in BENCH_ROOT.iterdir()
                             if p.is_dir() and (p / "MANIFEST.json").exists())
        elif args.dir:
            targets = [Path(args.dir)]
        else:
            ap.error("verify needs --dir <path> or --all")
        if not targets:
            refuse("verify: no corpora found under corpus/benchmarks")
        for target in targets:
            verify_corpus(target)
        return 0

    if args.corpus == "all":
        for name in CORPUS_NAMES:
            info = build_corpus(name, args.seed, args.force)
            print(f"[+] {info['name']:<16} docs={info['documents']:<2} "
                  f"bytes={info['total_bytes']:<8} corpus_sha256={info['corpus_sha256']}")
    else:
        info = build_corpus(args.corpus, args.seed, args.force)
        print(f"[+] {info['name']:<16} docs={info['documents']:<2} "
              f"bytes={info['total_bytes']:<8} corpus_sha256={info['corpus_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
