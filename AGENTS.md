# AGENTS.md — Panduan Sesi Agent (Workspace Skripsi v5)

> Wajib dibaca agent di setiap sesi. Bahasa kerja: **Indonesia** untuk semua dokumen,
> laporan, dan percakapan; **English** untuk kode, identifier, nama file, dan pesan commit.
>
> Sumber kebenaran rencana kerja: `PLANS.md` dan `TASKS.md` di root — baca keduanya
> sebelum mulai berubah. Dokumen ini hanya berisi aturan dan fakta operasional.

## 1. Identitas proyek

- Tujuan skripsi: **pengukuran komparatif** jalur parsing JSON yang dipakai server
  `saq-report/` (Node.js — baseline = `JSON.parse`/`JSON.stringify` bawaan V8) terhadap
  **`ze_json/`**: parser JSON on-demand C++23 yang sedang dikembangkan, diukur native
  (google-benchmark) dan via wasm64 di Node (`bindings/js`).
- **`ze_json/`** (submodule): library header-first di `include/ze_json/**`
  (`core`, `utils`, `meta`, `ondemand`), semua nama di `namespace zuu`, **tanpa STL di
  core** (typedef `core::*` sendiri, `core::Result`, `Arena`, makro `NOEXCEPT`,
  `RESTRICT`). `src/` = `stubs/compiler_rt.cpp` + scanner WIP
  (`src/ondemand/scalar.cpp` masih `// TODO`). API publik belum lengkap.
- **`bindings/js`**: binding Node raw wasm64 C-ABI (`ze_json.mjs` masih kosong).
  Node >= 24; rencana publikasi `@zuudevs/ze-json` di GitHub Packages.
- **`saq-report/`** (submodule — aplikasi Node.js/Express `saq-whatsapp`). Titik hot
  JSON di server SAQ: `express.json()` (middleware body parser),
  `repositories/JsonRepository.js` dan `MongoJsonRepository.js` (state store JSON
  per-domain: `assistants`, `courses`, `lecturers`, `schedules`, `reports`,
  `globalConfig`), dan `services/exportService.js` (`JSON.stringify` untuk export
  XLSX/DOCX). Tidak ada parser JSON pihak ketiga — baseline tetap V8 apa adanya.
- **Abaikan** `thesis-proposal/` dan `submission-thesis-supervisor/` (dokumen skripsi,
  bukan domain riset — arahan pemilik).
- Semua kecuali root `v5` adalah **submodules**. Direktori submodule yang kosong
  berarti belum init → `git submodule update --init`.

## 2. Literatur & provenance tabel codegen

- Implementasi **mengacu pada paper**. Literatur per DOI: `out/rag/<DOI>.chunks.json`
  (~50 artikel: simdjson, Mison, On-demand JSON, Number parsing GB/s, validasi UTF-8,
  JSONSki, JSON Tiles, Sparser, FAD.js, metodologi benchmark ilmiah, performa/energi
  WebAssembly, dsb). Sebelum menerapkan teknik, cari paper-nya di `out/rag/` dan
  cantumkan DOI-nya di komentar/laporan.
- `build/<preset>/generated/ze_json/core/lookups.hpp` **DIGENERASI — jangan edit
  manual**. Sumber tunggal: `ze_json/scripts/GenerateLookups.py` (dipanggil PRE_BUILD).
  Isi: `kNormalizedPowerOfFive`, `kPowerOfFiveReciprocal` (cite `10.1002_spe.2984`),
  `kUtf8Byte1High/Low`, `kUtf8Byte2High` (`10.1002_spe.2920`), `kJsonCharClass`,
  `kOndemandNodeType`. Aturan mutlak: setiap tabel punya tag `@cite <DOI>` di komentar
  headernya dan konstanta **provable** (dikalkulasi dari algoritma Python yang terbaca,
  bukan magic number). Tabel baru = tambahkan fungsi generator ber-@cite.
- **Komentar gaya Doxygen wajib** untuk setiap kode inti yang mengimplementasikan
  teknik dari paper (`@cite <DOI>` + satu kalimat alasan kenapa pendekatan itu dipakai).
  Tabel di `lookups.hpp` dan benchmark/test code juga membawa `@cite` yang sama.
- Dokumentasi `ze_json/docs/` ditulis dalam **English**, diagram memakai sintaks
  **Mermaid** (bukan gambar biner) — lihat TASKS P6.
- Bibliografi hidup di `assets/bib/cites.bib`; semua entri **wajib year >= 2016** —
  validasi: `python scripts/eval-cite/check_valid_year.py`.

## 3. Lingkungan build (ze_json)

- Build hanya sah dari workspace ini: preset CMake hardcoded `<root>/.toolchains`
  (toolchain portabel: CMake 4.4.5, Ninja 1.13.2, Clang/LLVM 23.1.5, vcpkg 2026.10.16,
  MSVC BuildTools). Jangan mengonfigurasi `ze_json` di luar workspace.
- **Sebelum cmake/vcpkg/pip/python di sesi non-interaktif**: jalankan
  `scripts/env/activate.ps1` (PowerShell) atau `scripts\env\activate.bat` — me-set PATH,
  `TOOLCHAINS_DIR`, `CORPUS_DIR`, `OUT_DIR`, `VCPKG_VISUAL_STUDIO_PATH`. Profil VS Code
  `"PowerShell (ze_json)"` memuatnya otomatis. Tanpa env ini `OUT_DIR` kosong dan target
  export menulis ke path kosong.
- Mesin baru: jalankan `scripts\bootstraps\ze_json.bat` sekali (unduh toolchain ke
  `.toolchains/` + instal MSVC BuildTools; besar dan lama — jangan diulang).
- Python dipakai step build (codegen, validasi versi, unduh JSON_checker) →
  `pip install -r ze_json/scripts/requirements.txt` (hanya `urllib3`).
- Preset: `native-{debug,release,release-with-debug-info,sanitize,pgo}`,
  `wasm32-{debug,release}`, `wasm64-{debug,release}`. Alur standar (dari `ze_json/`):

  ```sh
  cmake --preset native-release
  cmake --build build/native-release
  ctest --test-dir build/native-release --output-on-failure
  ```

- Target library bernama `ze_json`. Build wasm freestanding (`-nostdlib --no-entry`,
  C-ABI, `global-base=3153920`) otomatis menyalin `ze_json.wasm` ke `bindings/js`
  lewat POST_BUILD — jangan salin manual.
- PGO (`native-pgo`) mulai di mode GENERATE → jalankan benchmark (menimbun `.profraw`)
  → `ninja pgo_merge` (gabung `build/benchmarks/*.profraw` → `merged.profdata`) →
  build ulang; preset otomatis pindah ke mode USE. `ninja pgo_clean` untuk reset.
- clang-tidy otomatis pada build native (`CXX_CLANG_TIDY`, config `.clang-tidy`).
  clang-format: `BasedOnStyle: LLVM`, `LineEnding: LF`. File yang ada sudah tercampur
  tabs/spaces — format hanya kode yang disentuh, jangan reformat menyeluruh.
- Debug build terinstrumentasi (`-fprofile-instr-generate -fcoverage-mapping`) —
  berguna untuk coverage; jangan dijadikan basis angka terukur.

## 4. Konvensi pengukuran (hukum komparasi)

- Semua hasil pengukuran menyusun **struktur JSON identik antara `ze_json` dan
  `saq-report`**: satu "measurement record" (`schema_version`, `run_id`, metadata
  host/tool/library/corpus/config, array `results`). Rincian schema + validator ada di
  `PLANS.md` §3 dan `schemas/` setelah fase P0 selesai.
- **Dasar tindakan (rationale) wajib** di setiap hasil pengukuran: benchmark/test
  code membawa komentar Doxygen yang menyatakan apa yang diuji dan paper dasarnya
  (`@cite`), dan record membawa field `rationale` yang isinya sama. Record tanpa
  `rationale` dianggap tidak lengkap oleh validator — tidak boleh dipakai analisis.
- `run_id` = `hostname-<YYYYMMDDHHMMSS>-<git-hash>` (`RUN_ID` di
  `cmake/modules/MeasurementRegistry.cmake`).
- Helper CMake mengoper env ke executable: `ZE_METADATA_OUT` (test via
  `add_export_test_target`) dan `METADATA_OUT` (benchmark via
  `add_export_benchmark_target`) — executable wajib menulis sidecar `metadata.json`
  ke path tersebut; jangan tukar semantik-nya diam-diam.
- Hasil google-benchmark (`--benchmark_out`) dan gtest (`--gtest_output`) diperlakukan
  sebagai **exhibit mentah** (`out/raw/<run_id>/...`) yang dipertahankan apa adanya;
  lalu dinormalisasi ke measurement record (`out/measurements/<run_id>_..._record.json`)
  sebelum dipakai analisis.
- **Dilarang membandingkan** angka lintas: mesin, preset/build type, git hash, atau
  korpus yang berbeda. Working tree dirty → hash suffix `-dirty` dan disebut di
  laporan.
- Penempatan output:
  - `out/measurements/` — record tervalidasi final (satu schema untuk semua sisi).
  - `out/raw/` — exhibit mentah dari tools + sidecar metadata.
  - `out/benchmarks/` + `out/tests/` — hasil google-benchmark & gtest per run via
    helper CMake (helper lama menulis `out/benchmark` singular — disetarakan di P0).
  - `out/charts/` — figur analisis untuk skripsi.
  - `out/rag/` — corpus paper (read-only).
  - `.cache/json_checker` = paket JSON_checker hasil unduhan (`InstallJsonChecker.py`,
    dari json.org) — tidak di-commit; korpusnya di `corpus/test/json_checker`.
- Tree `corpus/benchmarks/` masih kosong — pengisiannya dijadwalkan (TASKS P0) dengan
  manifest sha256 agar provenance korpus terbukti.

## 5. Keadaan repo yang mudah terlewat

- `ze_json/tests/CMakeLists.txt` dan `benchmarks/CMakeLists.txt` **masih kosong** —
  belum ada target GTest/benchmark; helper export tersedia tapi tidak terpakai.
  Menambah tes = register target yang memakai helper tersebut.
- `.github/workflows/npm-publish.yml` **STALE**: menyebut target `ze_json_core`
  (tidak eksis), path `bindings/js/test` (seharusnya `tests/`), CMake 4.4.4. Jangan
  jadikan pola referensi. Referensi workflow valid = `ci.yml` (ubuntu+windows,
  `native-debug`/`native-release`, env `CORPUS_DIR`/`TOOLCHAINS_DIR`/`CACHE_DIR`/
  `PROJECT_ROOT_DIR`).
- `compile_commands.json` di root adalah salinan untuk clangd; sinkronkan setelah
  reconfigure build.
- `ze_json/docs/{architecture,development,requirement}/` dan `docs/` root masih
  kosong — isinya dijadwalkan (TASKS P6).
- Build aktif sekarang: `ze_json/build/native-release` dan `build/wasm64-release`
  (keduanya gitignored).

## 6. Metodologi (gate sebelum mengklaim optimasi)

- Muat skill **`cpp-highperf-json`** terlebih dahulu saat mengembangkan `ze_json`
  (skill dir: `C:\Users\ASUS\.config\opencode\skills\cpp-highperf-json`). Workflow:
  baseline → profile → **satu perubahan per pengukuran** → differential test →
  re-measure → report. Script pembanding milik skill
  (`scripts/analyze_benchmark_result/main.py`) dijadwalkan diadaptasi ke
  `scripts/analyze_measurement/` workspace (TASKS P0).
- Wajib "reference scalar" untuk setiap fast path + differential test identitas byte
  (edge: input kosong, <1 SIMD vector, lintas blok, unicode escape, angka batas,
  string panjang; korpus JSON_checker). `native-sanitize` (ASan/UBSan) hanya untuk
  cek kebenaran — tidak pernah untuk mengumpulkan angka.
- SIMD: runtime dispatch per-ISA; scalar fallback selalu ada; tail/sisa panjang
  ditangani eksplisit. `-march=native` hanya untuk build lokal (bukan build
  distributable), dan dicantumkan di laporan angka yang memakainya.
- Baseline & mesin: SAAT INI akses server SAQ belum tersedia — **semua pengukuran
  hanya di device pengembang (situs dev)**. Runner tetap dibuat site-aware
  (`--site=...`) sehingga ketika akses server ada, prosedur identik dijalankan
  tanpa mengubah harness. Perbandingan lintas arsitektur server-vs-dev ditunda
  (RQ2 fase awal = in-situ dev saja).
- Jangan membuat folder `results/benchmark/` baru — gunakan lokasi di §4.

## 7. Peta cepat file kunci

| Kebutuhan | Lokasi |
|---|---|
| Rencana & tugas | `PLANS.md`, `TASKS.md` (root) |
| Preset build | `ze_json/CMakePresets.json` |
| Modul toolchain / wasm | `ze_json/cmake/modules/*` (`toolchain.cmake`; `ToolChain.cmake` = wasm) |
| Env / bootstrap | `scripts/env/activate.ps1`, `scripts/bootstraps/ze_json.bat` |
| Codegen tabel | `ze_json/scripts/GenerateLookups.py` |
| Korpus JSON_checker | `corpus/test/json_checker/` + `InstallJsonChecker.py` |
| Literatur (paper) | `out/rag/<DOI>.chunks.json` |
| Bibliografi | `assets/bib/cites.bib`; validasi tahun `scripts/eval-cite/` |
| Baseline Node | `saq-report/` (`JsonRepository.js`, `exportService.js`, `express.json()`) |
| Schema pengukuran | `schemas/`, `scripts/measurement-schema/` (dibuat di fase P0) |

## 8. Alur kerja Git (berlaku di semua repo)

Scope: root `v5`, `ze_json`, `saq-report` (serta submodul dokumen bila nanti disentuh).

- **Jangan push langsung ke `main`** — buat branch (contoh: `perf/scanner-simd`) lalu
  **Pull Request** dulu; merge setelah pratinjau lulus. Kalau akses proteksi branch
  tersedia, aktifkan; jika tidak, ini disiplin manual.
- **Commit message wajib Conventional Commits** (English): `type(scope): subject`.
  - `type`: `feat`, `fix`, `perf`, `refactor`, `test`, `docs`, `build`, `ci`, `chore`, `style`, `revert`.
  - `scope` pakai nama modul: `scanner`, `lookups`, `cmake`, `bench`, `harness`,
    `binding-js`, `saq-baseline`, `measurement-schema`, `docs`.
  - Breaking change: tambahkan `!` setelah type + footer `BREAKING CHANGE:`.
- **Template PR wajib** di setiap repo: `.github/PULL_REQUEST_TEMPLATE.md`
  (seksi Rationale / Changes / Measurement Evidence / Checklist — rincian template
  di `PLANS.md` §10; pembuatannya di TASKS PW-1). Deskripsi PR boleh Indonesia.
- PR yang menyentuh jalur performa **wajib menautkan bukti pengukuran**: path record
  tervalidasi + path exhibit raw + status validator + hash baseline vs candidate.
- Artifacts hasil ukur tidak di-commit (`out/` gitignored); bila perlu arsip
  permanen, salin record tervalidasi ke `reports/` (di-commit, provenance verbatim).
