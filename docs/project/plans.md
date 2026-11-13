# Rencana Skripsi (v5) — plans

> Dokumen strategi. Tugas operasional dipecah di [`tasks.md`](tasks.md). Ubah dokumen ini hanya
> bila ada keputusan besar baru (lingkup, metode, schema, atau target mesin).
> Riwayat migrasi: semula `PLANS.md` di root; dipindah ke `docs/project/plans.md`
> pada overhaul arsitektur dokumentasi 2026-11-12 (PW-2).

## 1. Tujuan & pertanyaan riset

**Judul kerja**: "`ze_json`: parser JSON on-demand berbasis C++23/SIMD sebagai
alternatif parsing JSON pada aplikasi Node.js (SAQ), diukur secara komparatif
antar-arsitektur sistem."

**Pertanyaan riset**:
- **RQ1** — Seberapa jauh performa `ze_json` (native + wasm64) berbeda dari baseline
  `JSON.parse`/`JSON.stringify` V8 yang dipakai server SAQ, pada korpus kerja SAQ
  yang riil?
- **RQ2** — Bagaimana pengaruh **arsitektur sistem** (site: server SAQ vs device dev;
  ISA: native x86-64 vs wasm64) terhadap hasil ukur yang setara?
  (Catatan: akses server SAQ belum tersedia — fase awal membatasi site dev;
  pengukuran server dijadwalkan ulang saat akses ada, runner identik — lihat P5.)
- **RQ3** — Optimasi apa yang berdampak terukur (berbasis paper) tanpa melanggar
  kebenaran (validitas, kepatuhan JSON)?

**Hipotesis kerja**: parser on-demand C++23/SIMD > V8 pada korpus besar dan
read-only; pada payload kecil SAQ keunggulan bisa tertelan overhead boundary
(wasm/ABI), bukan hilang di algoritme — ini diukur, bukan diasumsikan.

## 2. Prinsip berpegang

1. **Paper-driven**: setiap teknik algoritme ter-rute ke DOI di `out/rag/`; tabel
   konstanta dibangun via `GenerateLookups.py` dengan `@cite`.
2. **Measurement first**: tidak ada klaim tanpa angka; baseline dulu, satu perubahan
   per pengukuran (workflow skill `cpp-highperf-json`).
3. **Struktur identik**: semua hasil ukur (test & benchmark, kedua pustaka) tertulis
   dalam **schema JSON yang sama** — `ze_json` vs `saq-report` dibandingkan tanpa
   mapping manual.
4. **Dapat dipertanggungjawabkan**: metadata lengkap + exhibit mentah tersimpan +
   korpus manifest sha256 + git hash. Semua hasil dapat direkonstruksi dari artifacts.
5. **Tervalidasi**: record yang tidak lolos validator schema tidak boleh dipakai untuk
   kesimpulan atau chart.
6. **Rationale-first**: setiap pengukuran punya dasar tindakan tertulis — apa yang
   diuji dan paper apa dasarnya (`rationale` + `@cite` di kode) — bukan angka telanjang.
7. **Artifacts dulu, kesimpulan belakangan**: angka mentah google-benchmark / node
   harness dipertahankan apa adanya; analisis bekerja di atas record hasil normalisasi.

## 3. Rencana objek pengukuran (measurement schema v1)

Satu **measurement record** JSON per run (benchmark ATAU test), struktur identis untuk
kedua submodul. Artifacts:

- `schemas/measurement.schema.json` — JSON Schema (draft-07) definisi.
- `scripts/measurement-schema/validate.py` — validator stdlib (tanpa dependensi
  eksternal): record valid = metadata lengkap + konsistensi field & unit
  + **`rationale` non-kosong pada setiap entry `results[]`**.
- Record valid disimpan: `out/measurements/<run_id>-<library>-<site>.record.json`.
- Exhibit mentah + sidecar metadata dari tool asli: `out/raw/<run_id>/...`.

Fields minimum (contoh record):

```json
{
  "schema_version": "1.0.0",
  "kind": "benchmark | test",
  "run_id": "host-20261108T093000-1a2b3c4",
  "site": "dev_device | saq_server",
  "generator": "google_benchmark | gtest | node_harness",
  "library": {
    "name": "ze_json | saq_baseline",
    "version": "0.1.0 | node-24.x",
    "language_runtime": "C++23 clang 23.1.5 | node 24 (v8) | node 24 (wasm64)"
  },
  "git_commit": { "hash": "1a2b3c4", "dirty": false, "repo": "ze_json" },
  "host": {
    "hostname": "...", "os": "...", "os_version": "...", "arch": "x86_64 | wasm64",
    "cpu_model": "...", "cpu_cores": 24, "cpu_freq": "...", "ram_gb": 8,
    "toolchain": "clang 23.1.5 | v8 13.x"
  },
  "corpus": {
    "name": "json_checker | saq_payload_v1 | synthetic_1mb | ...",
    "document_count": 150,
    "total_bytes": 4420192,
    "max_document_bytes": 849152,
    "sha256": "hex-manifest"
  },
  "config": {
    "date_utc": "2026-11-08T02:14:00Z",
    "iterations": 1000,
    "warmup_runs": 5,
    "repeats": 5,
    "cpu_pinning": false,
    "threads": 1,
    "notes": ""
  },
  "results": [
    {
      "name": "scanner64/parse/region.json",
      "engine": "simd | scalar | v8 | wasm64_cabi",
      "status": "ok | skip | fail",
      "rationale": {
        "purpose": "menguji kecepatan structural scanning pada dokumen berorientasi transfer",
        "basis_papers": ["10.1145_3448016.3452809", "10.1002_spe.3313"]
      },
      "metrics": {
        "bytes_per_second": 123456.79,
        "seconds_mean": 0.00050201,
        "seconds_stddev": 0.00002312,
        "cpu_seconds": 0.00049988,
        "documents_per_second": 4975.01
      },
      "extras": {}
    }
  ]
}
```

Metrik agregat lanjutan (percentile, p50/p99) ditambahkan ke `metrics` bila tersedia
dari runner. Field tambahan selalu lewat `extras`, bukan di level root, agar schema
stabil. Field `rationale` wajib untuk setiap entry `results[]` — teksnya
sinkron dengan komentar Doxygen `@cite` di kode benchmark/test yang menghasilkannya.

## 4. Rencana corpus

| Korpus | Tujuan | Sumber | Lokasi target |
|---|---|---|---|
| `json_checker` | kebenaran parser (pass + fail cases) | JSON.org (unduhan, cached `.cache/json_checker`) | `corpus/test/json_checker` (ada) |
| `saq_payload_v1` | workload realistis SAQ | sampel payload & config dari `saq-report/` (anonim) | `corpus/benchmarks/saq_payload_v1` |
| `synthetic_N` | sensitivitas ukuran: ±1KB / 10KB / 100KB / 1MB | generator (seeded RNG) | `corpus/benchmarks/synthetic_N` |
| `checker_batch` | stress whole-document parse | kumpulan dokumen valid | `corpus/benchmarks/checker_batch` |

Setiap korpus punya `MANIFEST.json` (nama file, bytes, sha256) yang di-hash untuk
field `corpus.sha256` pada record — provenance korpus jadi provable.

## 5. Fase implementasi

### P0 — Fondasi pengukuran
- Schema v1 (`schemas/measurement.schema.json`) + validator
  (`scripts/measurement-schema/validate.py`) + contoh record (valid & invalid).
- `scripts/host-introspect.mjs` — kumpulkan hostname/os/arch/cpu/ram/freq/toolchain
  runtime dari Node (dipakai kedua site agar metadata identik).
- Converter raw google-benchmark JSON → record v1.
- Adaptasi script pembanding milik skill ke `scripts/analyze_measurement/`.
- Rapihkan konsistensi path output CMake helper (`out/benchmark` → `out/benchmarks`).

### P1 — Harness & korpus native (ze_json)
- Register target GTest di `ze_json/tests/CMakeLists.txt` (korpus `json_checker`);
  export via `add_export_test_target` → `out/tests/`.
- Register target google-benchmark di `ze_json/benchmarks/CMakeLists.txt`;
  export via `add_export_benchmark_target` → `out/benchmarks/`.
- Scalar reference + fast path scanner (scanner8/32/64/128), differential test
  identitas byte pada edge cases; hasil: record v1 pertama untuk `ze_json` native +
  baseline scalar internal.

### P2 — Harness baseline SAQ (Node)
- `scripts/node-benchmark/` di root workspace — runner multi-engine (`v8` dulu):
  konteks kerja ditiru dari SAQ: body-parse (buffer parse),
  store-read (mirip `JsonRepository.read()`), export-stringify (mirip
  `exportService`, termasuk `null, 2` indent).
- CLI: korpus, ukuran, repeat, engine, site; output record v1 + exhibit mentah.
- Jalankan di device dev → baseline dev; siapkan opsi run identik di server SAQ.

### P3 — Integrasi binding Node ze_json (wasm64)
- Implement `bindings/js/ze_json.mjs` (memory handshake wasm64, C-ABI) + smoke test
  `bindings/js/tests/main.mjs` (`npm run smoke`).
- Sinkronkan `npm-publish.yml` yang stale (target `ze_json_core` → `ze_json`,
  path `bindings/js/test` → `bindings/js/tests`, CMake 4.4.4 → 4.4.5).
- Engine `ze-wasm64` aktif pada node harness → satu runner untuk semua engine.

### P4 — Loop optimasi (skill cpp-highperf-json)
- Baseline → profile → hipotesis → satu perubahan per pengukuran → differential
  test → re-measure. Keputusan besar (PGO, flag distributability, fitur baru) lewat
  pertanyaan ke pemilik.
- Setiap fast-path wajib punya reference scalar + differential test + lulus
  `native-sanitize`.

### P5 — Pengukuran lintas arsitektur (site server DITUNDA)
- Status: akses server SAQ belum tersedia — **pengukuran saat ini hanya
  `site=dev_device`**: V8 baseline + ze native + ze wasm64.
- Runner tetap dibuat site-aware (`--site`, introspeksi host) agar ketika akses
  server SAQ didapatkan, baseline `site=saq_server` (V8; opsi ze-wasm64 bila
  infrastruktur izin) dijalankan dengan prosedur identik — tanpa ubah harness.
- Analisis: delta per korpus, per engine; interpretasi RQ2 dengan introspeksi host
  (CPU model/core/freq) di setiap record; pembatasan dev-only dicatat di laporan.
- Chart ke `out/charts/`.

### P6 — Dokumentasi & penulisan skripsi
- Isi `ze_json/docs/{architecture,development,requirement}/` dalam **English**, semua
  diagram memakai sintaks **Mermaid** (embedded di markdown):
  - `architecture/` — komponen & data flow scanner, pipeline on-demand, binding wasm64.
  - `development/` — alur build/harness/korpus/testing dari perspektif kontributor.
  - `requirement/` — dependensi, toolchain, python, korpus, env variables.
- Chart + angka konsisten untuk dokumen skripsi (`thesis-proposal/` /
  `submission-thesis-supervisor/` — dikelola pemilik).
- Update `AGENTS.md` / `plans.md` / `tasks.md` bila keputusan berubah.

## 6. Paper kunci (mapping DOI → penggunaan)

| DOI (file di `out/rag/`) | Judul | Dipakai untuk |
|---|---|---|
| `10.1002_spe.3313` | On-demand JSON: A better way to parse documents? | desain API on-demand |
| `10.48550_arXiv.1902.08318` | Parsing Gigabytes of JSON per Second | arsitektur simdjson, staging |
| `10.14778_3115404.3115416` | Mison | structural indexing / pre-scan |
| `10.1002_spe.2984` | Number parsing at a gigabyte per second | tabel float via GenerateLookups |
| `10.1002_spe.2920` | Validating UTF-8 in less than one instruction per byte | tabel UTF-8 via codegen |
| `10.1002_spe.3036` / `10.1002_spe.3261` | Transcoding billions… / AVX-512 | string transcoding |
| `10.14778_3236187.3236207` | Sparser (Filter Before You Parse) | pre-filter pada semi-terstruktur |
| `10.1145_3448016.3452809` | JSON Tiles | struktur semantik akses on-demand |
| `10.14778_3778092.3778109` | Streaming Validation of JSON Against Schemas | mekanisme validasi record |
| `10.1145_2807591.2807644` | Scientific Benchmarking of Parallel Computing Systems | metodologi & statistik benchmark |
| `10.1109_PMBS56514.2022.00011` | Unified Hardware Counter Metrics | profiling counters |
| `10.1145_3744916.3764533` | Empirical Study of WebAssembly Usage in Node.js | lanskap integrasi wasm di Node |
| `10.1145_3593434.3593454` / `10.1109_ICT4S55073.2022.00014` | Energy & runtime WASM vs JS | energi (opsional/proxy) |
| `10.1145_3487552.3487827` | Understanding the Performance of WebAssembly Applications | interpretasi hasil wasm |
| `10.1002_spe.2777` / `10.1145_3859286` | Base64 SIMD | utility base64 decode |

## 7. Keputusan yang butuh persetujuan pemilik

- **Integrasi runtime penuh**: apakah `ze_json` (wasm64) dipasang sebagai pengganti
  nyata jalur `express.json()`/`JsonRepository` di SAQ produksi, atau penelitian cukup
  di harness komparatif (rekomendasi: cukup harness sampai P3lesai; keputusan
  integrasi runtime setelah angka P5).
- **PGO**: profil di device dev (default) vs server SAQ (perlu izin infrastruktur).
- **`-march=native`**: dipakai untuk hasil internal dev; untuk angka yang dipublikasi
  gunakan ISA dispatch runtime (rekomendasi).
- **Dependensi analitik tambahan** (numpy/pandas untuk chart & statistik) — hindari
  bila Python stdlib + node cukup.
- **Status akses server SAQ**: belum tersedia saat ini (keterbatasan pemilik) —
  pengukuran site server ditunda; runner tetap disiapkan site-aware agar
  prosedur identik siap jalan begitu akses ada.

## 8. Risiko & mitigasi

| Risiko | Mitigasi |
|---|---|
| Overhead wasm menelan gain native | pisahkan kategori native vs wasm vs V8; laporkan per-site |
| Noise angka (thermal, background) | repeats + warmup + introspeksi host; bandingkan hanya in-situ |
| Korpus SAQ kecil (tidak cukup untuk GB/s) | tambah `synthetic_N` untuk ekstrapolasi |
| Data SAQ tidak boleh dibagikan | anonimisasi; manifest hash tetap sah sebagai provenance |
| Konfigurasi PGO gagal/lama | dokumentasi fail/skip; jangan bawa hasil setengah jadi |
| Format tool skill vs schema jadi beda | normalisasi dulu, baru compare |
| Baseline server beda hardware | introspeksi host wajib; catat di record setiap run |
| Akses server SAQ belum tersedia | pengukuran dev-only dulu; runner site-aware; limitation dicatat di pembahasan; re-run penuh saat akses ada |

## 9. Definisi selesai (DoD per fase)

Fase hanya dianggap selesai bila:
1. Deliverable files ada di lokasi yang dijanjikan.
2. Record pengukuran (bila ada) lolos validator schema.
3. `plans.md`/`tasks.md` diperbarui bila keputusan berubah.
4. Tidak ada berkas hasil ukur baru yang tidak lolos schema.
5. Build tetap hijau (`ctest`); working tree bersih dari artifacts.
6. Perubahan lewat **Pull Request** dengan pesan commit konvensional (§10);
   PR terkait performa melampirkan path record + status validator.

## 10. Alur kerja Git & Pull Request (berlaku di semua repo)

- Lingkup: **root `v5`, `ze_json`, `saq-report`** (dan submodul dokumen bila nanti
  disentuh). Tidak ada push langsung ke `main` — buat branch (contoh:
  `perf/scanner-simd`, `feat/measurement-schema`) → **Pull Request** → review → merge.
- Judul PR & commit mengikuti **Conventional Commits 1.0.0** (English):
  `type(scope): subject`
  - `type`: `feat`, `fix`, `perf`, `refactor`, `test`, `docs`, `build`, `ci`, `chore`, `style`, `revert`.
  - `scope` pakai nama modul proyek: `scanner`, `lookups`, `cmake`, `bench`,
    `harness`, `binding-js`, `saq-baseline`, `measurement-schema`, `docs`.
  - Perubahan breaking: `!` setelah type + footer `BREAKING CHANGE:`.
- Template PR wajib ada di setiap repo: `.github/PULL_REQUEST_TEMPLATE.md` (task
  `tasks.md` PW-1). Deskripsi PR boleh Indonesia; seksi template sebagai berikut:

  ```markdown
  ## Rationale
  <!-- What changed and why (TASKS ID; DOI if technique comes from a paper). -->

  ## Changes
  <!-- Key files touched (path -> change). -->

  ## Measurement Evidence (required for performance-affecting changes)
  <!-- Record path (out/measurements/...), raw exhibit path (out/raw/...),
       validator output (PASS/FAIL), baseline vs candidate short-hash,
       same preset + same corpus. -->

  ## Checklist
  <!-- - [ ] ctest green on touched presets
       - [ ] native-sanitize pass for new C++ paths
       - [ ] scalar <-> fast-path differential test green
       - [ ] Doxygen @cite added for new core code
       - [ ] Conventional Commits followed
       - [ ] plans.md / tasks.md updated if a decision changed -->
  ```

- Artifacts hasil ukur tetap di `out/` (gitignored); PR me-refer path + hasil
  validator. Bila butuh arsip permanen di repo, salin record yang tervalidasi ke
  `reports/` (di-commit) dengan provenance verbatim — exhibit mentah tidak di-commit.
