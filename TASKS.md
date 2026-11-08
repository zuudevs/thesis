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

- [x] **P2-1** — `scripts/node-benchmark/harness.mjs` (root workspace): runner
  multi-engine (`v8` dulu; registry siap untuk `ze-wasm64` di P3) menulis
  record v1 + exhibit raw per korpus (`out/raw/<run_id>/node_harness_*.json`);
  `rationale` per benchmark (purpose + basis papers) tertanam di kode runner —
  sinkron dengan `@cite` di header JSDoc; host metadata di-import dari
  `scripts/host-introspect.mjs` (direfaktor: `collectHost()` + CLI guard).
- [x] **P2-2** — Tiga konteks kerja SAQ: `body-parse` (`JSON.parse(utf8)` ala
  `express.json()`), `store-read` (parse + rootKey unwrap ala
  `JsonRepository.read`, I/O disk disengaja dikecualikan — identik antar
  engine), `export-stringify` (`JSON.stringify(data, null, 2)` ala
  `exportService`).
- [x] **P2-3** — Korpus SAQ terintegrasi: `saq_payload_v1` (6 store, rootKey
  mapping dari `repositories/index.js`) + `synthetic_N` + `checker_batch`,
  manifest sha256 P0-8 diverifikasi ulang saat load (bytes on disk == manifest).
- [x] **P2-4** — Warmup (400 ms) + 5 repetisi × ≥300 ms + `--expose-gc` antar
  repetisi + host introspection lengkap di setiap record; `config.iterations`
  = median ops/repeat.
- [x] **P2-5** — Baseline dev dijalankan: run `zuu-20261108214228-0340a72`
  (saq-report `main` @ `0340a72`, site dev_device) — **6/6 record PASS
  validator**. Hasil V8 (median, MB/s): body-parse 137–391, store-read
  135–427, export-stringify 186–526 (per korpus; cv mayoritas < 8%, GC jitter
  pada stringify dokumen besar). Perbandingan sejenis dengan ze_json menunggu
  parser on-demand penuh (P4) — scan-only ze (≈0,7–1,2 GB/s) bukan
  apples-to-apples dengan V8 full-parse.

## P3 — Integrasi binding Node ze_json (wasm64)

- [x] **P3-1** — `bindings/js/ze_json.mjs`: raw wasm64 C-ABI (memory64 diekspor
  modul, 64 MiB; bump allocator `ze_alloc`/`ze_reset_heap` dari `__heap_base`
  linker; `ze_scanner8`/`ze_reference_scan` dengan hasil packed
  `(error<<32)|count`) — C-ABI shim baru `src/bindings/cabi.cpp`
  (`EXPORT_NAME`, compile-out di native); linker flags
  `--export-memory/--export=__heap_base/--initial-memory=67108864`;
  POST_BUILD tetap menyalin `ze_json.wasm` ke `bindings/js`.
- [x] **P3-2** — Smoke test `bindings/js/tests/main.mjs` + `npm run smoke`:
  ABI version, 8 kasus scan (termasuk escape & error), kesepakatan in-module
  scanner8 ↔ reference_scan, sanity allocator. **PASS**.
- [x] **P3-3** — Sinkronisasi `npm-publish.yml`: CMake 4.4.4 → 4.4.5 (target &
  path sudah benar di file terkini; langkah smoke kini berjalan atas test
  riil).
- [x] **P3-4** — Engine `ze-wasm64` di node harness: engine registry
  (`ENGINES`) — satu runner semua engine; konteks `wasm-scan` (batch
  semantics, sejajar C++/v8); library `ze_json` + `schemaEngine: wasm64_cabi`;
  run pertama `zuu-20261108220907-ca8f5f4` (dirty) **6/6 PASS validator**,
  396–648 MB/s (~20% di bawah native scanner8; ~3–4× V8 body-parse) —
  baseline kanonik menyusul pasca-merge.
- [x] **P3-5** — Differential test JS binding
  (`bindings/js/tests/differential.mjs`, `npm run differential`): 71 dokumen
  (seluruh korpus P0-8 + json_checker) — wasm scanner8 ↔ wasm reference_scan ↔
  JS reference **sepakat penuh** (outcome, count, indeks).

## P4 — Loop optimasi (skill cpp-highperf-json)

- [x] **P4-1** — Profil baseline: profiler khusus **tidak tersedia** di device
  (AMD uProf/VTune tidak terinstal; hanya WPR ETW — analisis ETW di luar jangkauan
  sesi) → sesuai skill, analisis turun ke **static analysis + bukti terukur**
  (lower-confidence, dicatat). Hipotesis tercatat di PR P4-2: (H1) SWAR 8-lane
  klasifikasi; (H2) serial table-load latency tersembunyi via unroll; (H3)
  prefix-xor string mask ala simdjson; (H4) per-doc overhead di batch kecil;
  (H5) clock drift antar-sesi (terbukti: scanner8 727→934 MB/s antar run —
  perbandingan sah hanya dalam-run; cpu_pinning untuk P5).
- [x] **P4-2** — Dispatch infra + SWAR `scanner64` + SSE2 `scanner128` + **fix
  correctness `utils/swar.hpp`**: gerbang diferensial menangkap false positive
  formula `haszero` klasik sebagai mask per-byte (borrow lintas byte; 30/200k
  acak; diverifikasi 2.000.256 kasus untuk formula pengganti
  `~(v|((v&0x7F..)+0x7F..))&0x80..`). `structural_scan()` = dispatch statis
  resolve-sekali; scanner64 & scanner128 teruji (fixtures + fuzz + korpus;
  ctest 100%). **Hasil ukur (dua eksperimen): kedua varian vektor kalah dari
  scanner8 di 5/6 korpus** (compact JSON quote-dense → jalur serial dominan;
  klasifikasi vektor lebih mahal dari 1 load tabel) → **keduanya ditolak**;
  dispatch default tetap `scanner8`; varian dipertahankan teruji untuk
  bahasan skripsi. Laporan lengkap: `reports/P4-bottleneck-report.md`.
  Perbaikan kecil tambahan: rekaman `InsufficientBuffer` di jalur serial
  kini diteruskan (sebelumnya diabaikan diam-diam).
- [ ] **P4-3** — Optimasi scanner/number parser/UTF-8 validator via tabel
  `lookups.hpp` (codegen paper-driven, `@cite` DOI).
- [ ] **P4-4** — PGO cycle (bila dipilih di `PLANS.md` §7): build `native-pgo` →
  run benchmark → `ninja pgo_merge` → rebuild (preset otomatis USE).
- [x] **P4-5** — Disiplin satu-perubahan-per-ukur dijalankan pada P4-2 (SWAR
  diukur terpisah, ditolak karena regress di luar noise); record lama vs baru
  tersimpan (`out/measurements/zuu-20261109042022-*` baseline kanonik vs
  `zuu-20261109053632-*` P4-2); temuan metodologi: clock drift antar-sesi →
  bandingkan hanya dalam-run.
- [x] **P4-6** — Laporan bottleneck + checklist: `reports/P4-bottleneck-report.md`
  (limitasi pengukuran: profiler tak tersedia + clock drift antar-sesi; dua
  eksperimen vektor ditolak dengan tabel angka dalam-run; fix correctness
  swar.hpp diterima; future work: pipeline simdjson-style penuh, unroll
  scanner8, number parser & UTF-8 validator, PGO menunggu keputusan pemilik).

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

- [x] **P6-1** — `ze_json/docs/architecture/README.md` **isi penuh** (English):
  lapisan, alur data (Mermaid), kontrak scanner lengkap + status varian
  (measured decision: scanner8 default; SWAR/SSE2 ditolak), C-ABI wasm64
  (tabel ekspor + diagram), arsitektur pengukuran.
- [x] **P6-2** — `ze_json/docs/development/README.md` **isi penuh** (English):
  matriks build/preset, gerbang kebenaran (Mermaid), pipeline pengukuran
  kanonik 4 langkah + perintah persis, pengembangan binding, tabel
  troubleshooting environment (MSVC fallback, ASan, GTest race, pipeline-kill,
  konvensi nama record, autocrlf).
- [x] **P6-3** — `ze_json/docs/requirement/README.md` **isi penuh** (English):
  tabel toolchain versi persis, env variables + fallback, presets, korpus
  (provenance manifest), CI parity.
- [x] **P6-4** — Sinkronisasi dokumen: `AGENTS.md` (status docs & scanner),
  `TASKS.md` (tick P0..P6 dengan nota hasil terverifikasi), pointer submodule
  diperbarui per merge.
- [x] **P6-5** — Angka final + chart siap transfer ke skripsi:
  `reports/final-numbers.md` (agregat 3 jalur: ze_native / V8 / ze-wasm64,
  semua record lolos validator ulang saat load; generator
  `scripts/measurement-schema/aggregate-final.py` stdlib-only) + chart
  `out/charts/final-throughput.png` (matplotlib, dari record kanonik).

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
