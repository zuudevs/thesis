# AGENTS.md — Panduan Sesi Agent (Workspace Skripsi v5)

> Wajib dibaca agent di setiap sesi. Bahasa kerja: **Indonesia** untuk semua dokumen,
> laporan, dan percakapan; **English** untuk kode, identifier, nama file, dan pesan commit.
>
> Sumber kebenaran rencana kerja: `docs/project/plans.md` dan
> `docs/project/tasks.md` — baca keduanya
> sebelum mulai berubah. Dokumen ini hanya berisi aturan dan fakta operasional.

## 1. Identitas proyek

- Tujuan skripsi: **pengukuran komparatif** jalur parsing JSON yang dipakai server
  `saq-report/` (Node.js — baseline = `JSON.parse`/`JSON.stringify` bawaan V8) terhadap
  **`ze_json/`**: parser JSON on-demand C++23 yang sedang dikembangkan, diukur native
  (google-benchmark) dan via wasm64 di Node (`bindings/js`).
- **`ze_json/`** (submodule): library header-first di `include/ze_json/**`
  (`core`, `utils`, `meta`, `ondemand`), semua nama di `namespace zuu`, **tanpa STL di
  core** (typedef `core::*` sendiri, `core::Result`, `Arena`, makro `NOEXCEPT`,
  `RESTRICT`). `src/` = `stubs/compiler_rt.cpp`, `ondemand/scalar.cpp`
  (`scanner8` + reference, sejak P1-1/P1-2), `ondemand/parallel.cpp`
  (`scanner64` SWAR + `scanner128` SIMD — terukur & ditolak P4-2; `scanner32`
  stub 32-bit), `ondemand/{string,number}.cpp` (promosi scalar lazy),
  `abi/cabi.cpp`. **Parser on-demand (`Document`/`Value`/`ArrayIter`/
  `ObjectIter`) terimplement & teruji sejak P7** (75 TEST gtest, 6 target) —
  bukan TODO; status as-built: `docs/research/audit-2026-11-12.md` §3.
- **`bindings/js`**: binding Node raw wasm64 C-ABI (`ze_json.mjs`: `ZeJson`/
  `ZeDocument`/`ZeParser`, ABI v3 — `SCANNER_MODES` untuk memilih varian
  scanner + surface parser on-demand pada slot pool 64; `ZeParser` = jalur
  lazy frame `(ts, cursor)`, `ZeParser.parse()` = materialisasi penuh;
  kontrak di `include/ze_json/abi/cabi.hpp`).
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
  `docs/project/plans.md` §3 dan `schemas/` setelah fase P0 selesai.
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
  laporan. Bandingkan mode scanner antar-varian hanya **dalam satu run**
  (`harness.mjs --scanner all` mengukur 5 mode dengan satu `run_id`); record
  membawa `config.scanner_mode` (`multi` bila >1 mode dalam run).
- Penempatan output:
  - `out/measurements/` — record tervalidasi final (satu schema untuk semua sisi).
  - `out/raw/` — exhibit mentah dari tools + sidecar metadata.
  - `out/benchmarks/` + `out/tests/` — hasil google-benchmark & gtest per run via
    helper CMake (helper lama menulis `out/benchmark` singular — disetarakan di P0).
  - `out/charts/` — figur analisis untuk skripsi.
  - `out/rag/` — corpus paper (read-only).
  - `.cache/json_checker` = paket JSON_checker hasil unduhan (`InstallJsonChecker.py`,
    dari json.org) — tidak di-commit; korpusnya di `corpus/test/json_checker`.
- Tree `corpus/benchmarks/` terisi sejak P0-8 (`synthetic_{1k,10k,100k,1mb}`,
  `saq_payload_v1`, `checker_batch`) dengan `MANIFEST.json` sha256 per korpus
  (generator `scripts/corpus/make_corpus.py`) — provenance korpus terbukti.

## 5. Keadaan repo yang mudah terlewat

- **ABI v3 sejak P7-5**: kontrak C-ABI = header
  `include/ze_json/abi/cabi.hpp` (sumber tunggal, dimirror `ze_json.mjs`);
  implementasi `src/abi/cabi.cpp` (pindahan dari `src/bindings/` — konvensi
  sisi core = **`abi`**, `bindings/` khusus adaptor bahasa, `ffi` dibatalkan).
  Ekspor scanner (v2): scanner8, reference_scan, scanner64, scanner128,
  structural_scan (pemilihan mode dari JS via `SCANNER_MODES`) **+ ekspor
  parser on-demand (v3): 13 fungsi** pada slot pool statis 64
  (`kParserSlotMax`; traversal stateless via frame `(cursor, token_start)`).
- Target wasm memakai **`-msimd128`** sejak R1 (PR zuudevs/ze_json#7) untuk
  `core::simd_*` — baseline wasm kanonik lama (`85afad7`, artefak tanpa
  simd128) **tidak sebanding langsung**; baseline kanonik wasm diukur ulang
  pada hash bersih pasca-R2 (TASKS R3).
- `ze_json/tests/CMakeLists.txt` dan `benchmarks/CMakeLists.txt` terisi sejak
  P1-3/P1-5: `ze_json_scanner_test` (diferensial + json_checker) dan
  `ze_json_scanner_benchmark` (korpus P0-8, export sidecar) — keduanya memakai
  helper export. Benchmark baru = register target yang memakai helper tersebut.
- Referensi workflow valid = `ci.yml` (ubuntu+windows, `native-debug`/
  `native-release`, env `CORPUS_DIR`/`TOOLCHAINS_DIR`/`CACHE_DIR`/
  `PROJECT_ROOT_DIR`) dan `npm-publish.yml` (build `wasm64-release` + smoke
  `bindings/js/tests/main.mjs` sebelum publish — telah disinkronkan; catatan
  "STALE" lama tidak berlaku lagi, diverifikasi Stage 2 2026-11-12).
- `compile_commands.json` di root adalah salinan untuk clangd; sinkronkan setelah
  reconfigure build.
- `ze_json/docs/` modular (architecture/ per-topik kebab-case, development/,
  requirements/, adr/) berisi **isi penuh English/Mermaid** sejak P6,
  direstrukturisasi 2026-11-12 (parser on-demand as-built + ABI v3 tercakup);
  `docs/` root = `research/audit-2026-11-12.md` (audit Stage 1, snapshot
  historis, Bahasa Indonesia).
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
| Rencana & tugas | `docs/project/plans.md`, `docs/project/tasks.md` |
| Preset build | `ze_json/CMakePresets.json` |
| Modul toolchain / wasm | `ze_json/cmake/modules/*` (`toolchain.cmake` — native chainload & wasm) |
| Env / bootstrap | `scripts/env/activate.ps1`, `scripts/bootstraps/ze_json.bat` |
| Build wasm64 terverifikasi | `scripts/build-wasm.ps1` (`-Fresh`/`-SkipGates`/`-VerifyOnly`) |
| Codegen tabel | `ze_json/scripts/GenerateLookups.py` |
| Korpus JSON_checker | `corpus/test/json_checker/` + `InstallJsonChecker.py` |
| Literatur (paper) | `out/rag/<DOI>.chunks.json` |
| Bibliografi | `assets/bib/cites.bib`; validasi tahun `scripts/eval-cite/` |
| Lapisan on-demand ze_json | `ze_json/include/ze_json/ondemand/{document,value}.hpp`, `ze_json/src/ondemand/document.cpp` |
| Binding JS | `ze_json/bindings/js/ze_json.mjs` (`ZeJson`/`ZeDocument`/`ZeParser`) |
| Audit arah on-demand | `docs/research/audit-2026-11-12.md` (snapshot historis; feed Stage 2–7) |
| Baseline Node | `saq-report/` (`MongoJsonRepository.js` clone hot path, `JsonRepository.js`, `exportService.js`, `express.json()`) |
| Kontrak C-ABI | `ze_json/include/ze_json/abi/cabi.hpp` (+ `src/abi/cabi.cpp`) |
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
  di `docs/project/plans.md` §10; pembuatannya di TASKS PW-1). Deskripsi PR boleh Indonesia.
- PR yang menyentuh jalur performa **wajib menautkan bukti pengukuran**: path record
  tervalidasi + path exhibit raw + status validator + hash baseline vs candidate.
- Artifacts hasil ukur tidak di-commit (`out/` gitignored); bila perlu arsip
  permanen, salin record tervalidasi ke `reports/` (di-commit, provenance verbatim).
