# TASKS.md — Daftar Tugas Skripsi (v5)

> Checklist operasional; satu perubahan = satu task ID. Tandai `[x]` hanya setelah
> DoD (`PLANS.md` §9) terpenuhi. Setiap sesi kerja di `ze_json` dimulai dengan
> memuat skill `cpp-highperf-json` dan `scripts/env/activate.ps1`.

## P0 — Fondasi pengukuran

- [x] **P0-1** — `schemas/measurement.schema.json` (JSON Schema draft-07) sesuai
  rancangan `PLANS.md` §3, termasuk kewajiban field `rationale`
  (`purpose` + `basis_papers[]`) pada setiap entry `results[]`.
- [x] **P0-2** — Validator `scripts/measurement-schema/validate.py` (stdlib-only;
  `python scripts/measurement-schema/validate.py <record.json>`; exit 0 = valid);
  record tanpa `rationale` = invalid.
- [x] **P0-3** — Contoh record + uji validator `scripts/measurement-schema/samples/`:
  hasil terverifikasi = 1 PASS (valid.record.json) + 3 FAIL sesuai kelas kesalahan
  (metadata tak lengkap → `cpu_model` hilang; `basis_papers` kosong; engine di luar
  enum).
- [x] **P0-4** — `scripts/host-introspect.mjs` (Node ≥24): hostname/os/arch/cpu/
  ram/freq/toolchain runtime — dipakai kedua site agar metadata identik.
  Dijalankan sukses (Node v24.19.0; host `zuu`: Ryzen 5 5500U, 12 core, RAM 7.4 GB);
  output tersimpan di `.temp/host.json`.
- [x] **P0-5** — Converter raw google-benchmark JSON → record v1
  (`scripts/measurement-schema/convert-gbench.py`). Uji end-to-end lulus: fixture
  gbench (2 keluarga × 2 repetisi + agregat mean/median/stddev) → record tervalidasi
  PASS via `validate.py`; engine auto-detect benar (`Scanner64`→simd,
  `Scanner8_scalar`→scalar); `--purpose` + `--basis-papers` wajib (ditolak bila kosong);
  file hanya ditulis bila validasi PASS.
- [x] **P0-6** — Adaptasi script `compare`/`summary`/`trend` milik skill ke
  `scripts/analyze_measurement/main.py` agar menerima record v1 (bukan raw gbench).
  Terverifikasi end-to-end dengan sampel (`scripts/analyze_measurement/samples/`):
  `summary` + CSV ✓; `compare` baseline→candidate exit 1 pada regresi (verdict
  IMPROVED/REGRESSED, noise = max(threshold, 2×CV)) ✓; `trend` ✓; perbandingan
  lintas-host ditolak exit 2 (penjaga AGENTS §4: kind/generator/site/host/corpus/
  library/preset harus sama; hash git boleh beda) ✓. Default dir `out/measurements`.
- [x] **P0-7** — Konsistensi lokasi output: helper CMake `Benchmark.cmake`
  `out/benchmark/` → `out/benchmarks/` dan `Testing.cmake` `out/test/` → `out/tests/`
  (6 kemunculan, konsisten §4 AGENTS.md).
- [x] **P0-8** — Seed korpus `corpus/benchmarks/` lengkap dengan `MANIFEST.json`
  per korpus (generator deterministik stdlib-only
  `scripts/corpus/make_corpus.py`, seed 20261108, timestamp-free → regenerasi
  tanpa perubahan sumber = byte identik): `synthetic_1k/10k/100k/1mb` (masing-masing
  1 dokumen **byte-exact** pada 1/10/100/1024 KiB, compact — peran body-parse),
  `saq_payload_v1` (6 dokumen store SAQ anonim — bentuk & rootKey mirroring
  `repositories/index.js`, pretty indent-2 persis `JSON.stringify(null, 2)`;
  total 88.381 B), `checker_batch` (25 dokumen valid: pass1–3 kopi byte-exact +
  22 generated edge-shaped; 5.573 B). `verify --all` lulus untuk keenam korpus
  termasuk re-check provinsi `copied:` terhadap berkas sumber; `corpus/**` dipin
  `-text` di `.gitattributes` (anti-rewrite EOL oleh `core.autocrlf=true`).
  `corpus.sha256` pada record = sha256 file `MANIFEST.json` (didokumentasikan di
  `corpus/benchmarks/README.md` + `schemas/README.md`).
- [x] **P0-9** — Korpus `corpus/test/json_checker` tersedia & konsisten dengan
  `InstallJsonChecker.py`: 33 `fail*.json` + 3 `pass*.json` + `README.md` (teks
  identik hasil `write_info()`) = 37 berkas; cache paket `.cache/json_checker/`
  utuh (`.c`, header, `CMakeLists.txt` dari `install()`).
- [x] **P0-10** — README singkat di `schemas/` (merujuk `PLANS.md` §3 + cara validasi
  + penunjuk converter/analyzer).

## P1 — Harness & korpus native (ze_json)

- [x] **P1-1** — Scalar reference scanner di `include/ze_json/ondemand/reference.hpp`
  (`reference_scan`, header-only, **bebas tabel lookup** — switch karakter eksplisit
  agar bug codegen tak bisa merusak referensi; kontrak scanner tertulis penuh di
  Doxygen: indeks struktural `{ } [ ] , :` di luar string, error EmptyJson /
  InvalidJson / InsufficientBuffer + presedensnya).
- [x] **P1-2** — Fast path `scanner8` di `src/ondemand/scalar.cpp` memakai tabel
  `kJsonCharClass` (satu load tabel + dua tes masker per byte); Doxygen `@cite`
  Mison (10.14778_3115404.3115416) + simdjson (10.48550_arXiv.1902.08318),
  sinkron dengan rationale test.
- [x] **P1-3** — Differential test `tests/scanner_test.cpp`: 15 kasus tepi (input
  kosong, null src/dst, whitespace varian, escape `\"` `\\`, UTF-8 multibyte,
  struktural di dalam string, angka opaque, string tak tertutup, dangling escape,
  kapasitas exact/kurang-satu, zero-structural) + fuzz deterministik 500 iterasi
  (seed 20261108, input 0..4096 B) — **reference vs scanner8 identik 100%**; plus
  test tabel `kJsonCharClass` 256 byte terhadap set karakter referensi.
- [x] **P1-4** — Integrasi `json_checker` ke tests + registrasi CMake:
  `tests/CMakeLists.txt` (target `ze_json_scanner_test`, link GTest, `add_test`,
  `add_export_test_target`, korpus via macro `ZE_JSON_CORPUS_DIR` dinormalisasi
  POSIX), `enable_testing()` ditambahkan di CMakeLists root. ctest
  native-release **100% lulus** (pass1–3: indeks struktural identik; fail1–33:
  kedua jalur sepakat — fail1/fail18 dikecualikan sebagai legacy RFC 8259;
  grammar error lain = ranah parser, bukan scanner).
- [x] **P1-5** — Register target google-benchmark di `ze_json/benchmarks/`
  (`ze_json_scanner_benchmark` + `add_export_benchmark_target` →
  `out/benchmarks/ze_json/`): 12 benchmark (4 korpus sintetis + saq batch +
  checker batch × reference/scanner8), korpus dimuat dari `corpus/benchmarks/`
  (P0-8), 5 repetisi ter-bake, **sidecar metadata export** (kontrak §4:
  `export_sidecar.hpp` dipakai benchmark DAN test — test retrofit custom main,
  link `GTest::gtest` saja).
- [x] **P1-6** — Record v1 pertama `ze_json` dengan `rationale` per entry:
  run `zuu-20261109035547-3211b7d` (site dev_device, native-release, commit
  `3211b7d` + **dirty** — file P1 belum ter-commit saat run; baseline kanonik
  di-re-run setelah merge). Pipeline penuh: helper export → split per korpus
  (`split-gbench.py` baru, reusable) → konversi (`convert-gbench.py`,
  `run_id` bersama, hash manifest P0-8) → **6/6 record PASS validator** →
  exhibit mentah di `out/raw/<run_id>/`. Hasil baseline (bytes/s,
  reference → scanner8): 1k 1.01G→932M (−7.5%), 10k 796M→777M (−2.4%),
  100k 765M→759M (≈noise), 1mb 727M→752M (+3.5%), saq 1.18G→994M (−16%),
  checker_batch 743M→783M (+5.4%) — observasi: tabel lookup tidak otomatis
  menang di korpus kecil/whitespace-heavy; SWAR (P4-2) kandidat utama.
- [x] **P1-7** — Skeleton `ze_json/docs/{architecture,development,requirement}/`
  (+ `docs/README.md` indeks): English, diagram Mermaid, tabel status implementasi
  sesuai kondisi P1, alur build/test + pipeline pengukuran (build → export →
  split → convert → validate → analyze), tabel toolchain & env variables. Isi
  penuh tetap di P6.
- [x] **P1-8** — Baseline kanonik tersimpan: run `zuu-20261109042022-ca8f5f4`
  (ze_json `main` @ `ca8f5f4` pasca-merge PR #2, tree bersih, tanpa dirty) —
  6/6 record PASS validator, exhibit mentah di `out/raw/zuu-20261109042022-ca8f5f4/`.
  Sanity check `compare` dirty(3211b7d) vs kanonik(ca8f5f4): *within noise* di
  kedua jalur (−4.2%/−3.3% vs floor 6.3%/5.2%) — pipeline terverifikasi
  end-to-end. Hasil kanonik ≈ P1-6: 1k 1.01G→933M, 10k 801M→781M,
  100k 772M→767M, 1mb 696M→727M, saq 1.16G→985M, checker 712M→706M
  (MB/s; lihat record untuk angka penuh).

## P2 — Harness baseline SAQ (Node)

- [ ] **P2-1** — `scripts/node-benchmark/harness.mjs` (root workspace): runner
  multi-engine (`v8` dulu) menulis record v1 + exhibit raw terstruktur; runner
  juga mengirim konten `rationale` per benchmark (purpose + basis papers) —
  konsisten dengan `@cite` di kode.
- [ ] **P2-2** — Konteks kerja SAQ: body-parse (`JSON.parse` dari buffer),
  store-read (mirip `JsonRepository.read`), export-stringify (mirip
  `exportService`: `JSON.stringify(data, null, 2)`).
- [ ] **P2-3** — Integrasi korpus SAQ (`saq_payload_v1` + `synthetic_N`) dari P0-8.
- [ ] **P2-4** — Warmup + repeats + host introspection (metadata lengkap di setiap
  record).
- [ ] **P2-5** — Baseline dev (situs dev) dijalankan; exhibit raw tersimpan di
  `out/raw/<run_id>/`.

## P3 — Integrasi binding Node ze_json (wasm64)

- [ ] **P3-1** — `bindings/js/ze_json.mjs`: raw wasm64 C-ABI (handshake memory,
  pointer, view `Uint8Array`) mengikuti kontrak `package.json` (`ze_json.wasm`
  hasil build wasm64 POST_BUILD).
- [ ] **P3-2** — Smoke test `bindings/js/tests/main.mjs` + `npm run smoke`:
  minimal parse & validate menghasilkan output konsisten.
- [ ] **P3-3** — Sinkronkan `npm-publish.yml` yang stale (target `ze_json_core` →
  `ze_json`, path `bindings/js/test` → `bindings/js/tests`, CMake 4.4.4 → 4.4.5).
- [ ] **P3-4** — Engine `ze-wasm64` di node harness — satu runner untuk semua engine
  (`v8`, `ze-wasm64`; opsi native NAPI mengikuti keputusan `PLANS.md` §7).
- [ ] **P3-5** — Differential test JS binding: hasil parse/validate identik byte-per-byte
  dengan C++ native pada korpus yang sama.

## P4 — Loop optimasi (skill cpp-highperf-json)

- [ ] **P4-1** — Profile baseline (perf / VTune / AMD uProf — modul sudah tersedia
  `HandleProfiler.cmake`): pilih 5 hotspot utama; tulis hipotesis per hotspot
  (what / evidence / expected effect).
- [ ] **P4-2** — SIMD runtime dispatch (`simd.hpp` per-ISA + scalar fallback; resolve
  pointer sekali, bukan per call; tail ditangani eksplisit).
- [ ] **P4-3** — Optimasi scanner/number parser/UTF-8 validator via tabel
  `lookups.hpp` (codegen paper-driven, `@cite` DOI).
- [ ] **P4-4** — PGO cycle (bila dipilih di `PLANS.md` §7): build `native-pgo` →
  run benchmark → `ninja pgo_merge` → rebuild (preset otomatis USE).
- [ ] **P4-5** — Satu perubahan per re-measure; tolak kolej perubahan yang tidak
  memberi gain di luar noise; simpan record lama vs baru.
- [ ] **P4-6** — Laporan bottleneck (template skill) + checklist optimasi per tahap.

## P5 — Pengukuran lintas arsitektur (site server ditunda — akses SAQ belum ada)

- [ ] **P5-1** — Paket runner untuk server SAQ: instruksi deploy konsisten
  (`node scripts/host-introspect.mjs` + `node scripts/node-benchmark/harness.mjs
  --site=saq_server`); hasil dipindah ke `out/measurements/`. — **disiapkan sekarang,
  eksekusi ditunda sampai akses server SAQ dapat.**
- [ ] **P5-2** — Baseline V8 di server SAQ → record v1. — **ditunda** (akses belom
  tersedia; runner site-aware siap).
- [ ] **P5-3** — (opsional, bila izin tersedia) ze-wasm64 di server SAQ → record v1. —
  **ditunda**.
- [ ] **P5-4** — Perbandingan lintas mesin — **fase awal dalam satu site dev**:
  `v8@dev` vs `ze-native@dev` vs `ze-wasm64@dev` (semua validated + introspeksi host
  lengkap); kolom `@server` ditambah begitu akses SAQ ada.
- [ ] **P5-5** — Analisis & chart ke `out/charts/` (murni dari record validated).

## P6 — Dokumentasi & penulisan skripsi

- [ ] **P6-1** — Isi `ze_json/docs/architecture/` dalam **English** (komponen, header,
  scanner design) — diagram memakai **Mermaid**.
- [ ] **P6-2** — Isi `ze_json/docs/development/` dalam **English** (build, harness,
  korpus, testing) — alur bergambar **Mermaid**.
- [ ] **P6-3** — Isi `ze_json/docs/requirement/` dalam **English** (C++23, toolchain,
  Python, korpus, env variables).
- [ ] **P6-4** — Sinkronkan `AGENTS.md` / `PLANS.md` / `TASKS.md` bila keputusan
  berubah (schema, target mesin, engine harness).
- [ ] **P6-5** — Angka final + chart siap ditransfer ke dokumen skripsi
  (`thesis-proposal/` di luar lingkup — hanya data dan referensi yang diberikan).

## PW — Alur kerja Git (berlaku di semua repo: root v5, ze_json, saq-report)

- [x] **PW-1** — Buat `.github/PULL_REQUEST_TEMPLATE.md` di ketiga repo (root v5,
  `ze_json/`, `saq-report/`) sesuai template `PLANS.md` §10 (seksi: Rationale /
  Changes / Measurement Evidence / Checklist).
- [x] **PW-2** — Dokumentasikan konvensi commit (Conventional Commits — type & scope
  list) di `AGENTS.md` §8 dan tautkan dari template PR.
- [ ] **PW-3** — Aktifkan proteksi `main` bila punya akses settings (wajib PR);
  jika tidak, catat sebagai disiplin manual di `AGENTS.md`.
- Selalu: branch per perubahan (contoh `perf/scanner-simd`), deskripsi PR
  Indonesia, judul `type(scope): subject` (English), bukti pengukuran
  ditautkan bila perubahan menyentuh performa.

## Status mesin & environment

- Dev device = workspace ini (Windows x86_64, toolchain portabel) — **satu-satunya
  site pengukuran aktif saat ini** (akses server SAQ belum tersedia).
- Runner dibuat site-aware (`--site=dev_device|saq_server`); site server diaktifkan
  begitu akses dapat, dengan prosedur runner identik (tanpa perubahan harness).
- Build aktif: `ze_json/build/native-release` + `build/wasm64-release`.
- Working tree `ze_json` harus bersih (commit/stash) sebelum mengumpulkan hasil;
  bila dirty, simpan record dengan suffix `<hash>-dirty` dan sebut di laporan.
