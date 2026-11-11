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
  - **C1 (string-class table) DITOLAK dengan bukti sandwich** (2026-11-10):
    dispatch `kJsonStringClass` di `scan_string`/`decode_interior` kalah —
    load-tabel melawan chain 4-branch terprediksi. Back-to-back satu window
    mesin: baseline `d21304c` bersih (`zuu-20261110085449-d21304c`) vs
    kandidat (`zuu-20261110085656-d21304c`): regress seragam −12..−48%
    (ParseOpen staging ikut −12..−25% walau tak menyentuh scan_string →
    efek layout-kode; ParseRef saq −48%). Kontrol bisection B1 (tabel
    ada, string.cpp pre-C1, exhibit `out/raw/zuu-20261110085656-d21304c`
    gbench overwrote alias RUN_ID; angka run B1 = out/benchmarks
    `...85656....json` 09:02) ≈ baseline → penyebab = loop baru, bukan
    kehadiran tabel. Implementasi penuh C1 diarsip: temp c1bak; tidak
    masuk repo. Dasar riset hipotesis: Mison/simdjson klasifikasi tabel
    (cheaper) TIDAK berlaku untuk interior-string 1-load vs branch
    terprediksi di Zen 2 — konsisten P4-2 (vektor/SWAR kalah).
  - Sisa C1 yang LAYAK: repairs `@cite` Mison/simdjson di
    `gen_json_char_classes`/`gen_ondemand_node_types` + fix encoding
    generator (utf-8, LF) — di-commit terpisah.
  - Kandidat lanjutan: C2 reciprocal fast path number q<0
    (`kPowerOfFiveReciprocal`, tabel sudah codegen, gain diperkirakan
    kecil — frac token hanya 5.9k/1MB) → C3 UTF-8 SIMD pshufb (deferred).
  - **C2 (reciprocal fast path q<0) DITERIMA dengan bukti sandwich**
    (2026-11-10): `region_exact` q<0 kini membagi via reziprokal 128-bit
    codegen (`kPowerOfFiveReciprocal`, paper §9.1, `@cite
    10.1002_spe.2984`) — n×c satu produk u128 + koreksi eksak satu
    compare; pembagian bit-serial P7-2 dipertahankan sebagai
    `region_div_ref` (oracle) dan di-pin bit-exact oleh
    `NumberRegionFastPath.MatchesBitSerialReference` (corner + 150k fuzz,
    k=1..22, kedua tanda). Native sandwich satu window (baseline `0f56997`
    bersih `zuu-20261110093601-0f56997` vs dua run kandidat
    `zuu-20261110090821-0f56997` + `zuu-20261110100531-0f56997`, keduanya
    reproduksi): FullWalk ladder **+19.6..+33.2%** (frac q<0), checker
    +0.0% / saq +6.7% (dalam noise — kontrol mekanisme), ParseOpen
    +2.2..+10% (efek layout, tidak menyentuh parse_number); tanpa
    regresi di mana pun. Wasm64 dalam-window (baseline
    `zuu-20261110042040/042041` vs kandidat `...042923/042925`): checker
    +4.7%, synth100k +3.3% — paritas-ke-baik; run wasm C2 berdiri sendiri
    (`zuu-20261110035226`) −11..−40% vs baseline malam P7-7 adalah drift
    lintas-sesi (H5) — korpus tanpa frac ikut turun. Gerbang: ctest 6/6,
    smoke wasm PASS, differential 71×5 agree. Catatan skema: field
    `run_id` record dari convert-gbench kini diisi `--run-id` sinkron
    sidecar (run C2 ke atas; record lama memakai stamp konversi).
- [x] **P4-4** — PGO cycle (bila dipilih di `PLANS.md` §7): build `native-pgo` →
  run benchmark → `ninja pgo_merge` → rebuild (preset otomatis USE). **SIKLUS
  DIEKSEKUSI 2026-11-11 — hasil CAMPUR, PGO tidak diadopsi sebagai preset
  default** (lihat rincian di bawah).
  - **Bug infrastruktur ditemukan & diperbaiki**: `add_optimizations_target`
    tidak pernah dipanggil — flag PGO tidak pernah diterapkan (GENERATE
    menghasilkan binary tanpa instrumentasi, nol `.profraw`). Fix: fungsi baru
    `add_pgo_flags(<target>)` (Optimization.cmake) yang HANYA memuat flag
    GENERATE/USE — tanpa `-march=native` milik fungsi lama (jaga baseline
    `native-release` tetap canonical); dipasang pada `ze_json` + dua driver
    benchmark. Training: parser benchmark (6 korpus) + scanner benchmark,
    CWD `build/native-pgo/benchmarks` → 2 `.profraw` → `pgo_merge` →
    reconfigure auto-USE → rebuild → ctest 6/6.
  - **Bukti sandwich** (baseline `native-release` vs kandidat `native-pgo`
    USE, 70 detik apart, kontrol baseline stabil ±1-2% lintas 28 menit;
    record tervalidasi): `zuu-20261111001542-8b281f6_*` (PGO) vs
    `zuu-20261111004055-8b281f6_*` (baseline):
    **FullWalk +20.9..+24.6%** di ladder (1mb 158.6→191.8 MB/s; 100k +24.4%,
    10k +24.6%), 1k +12.8%, checker +5.9%, saq −0.8% (flat) — TEREPRODUKSI
    dua run PGO independen (00:43 & 01:11, angka identik ±0.6%).
    **TAPI ParseOpen (staging) −23..−31% seragam di semua korpus**
    (saq 1303.7→896.6 MB/s) dan ParseReference +10..+47% — PGO
    mendistribusikan ulang performa antar komponen (layout/inlining).
  - **Keputusan**: FullWalk (jalur utama on-demand) menang jelas, tetapi
    regresi staging −27% tidak dapat dibawa ("jangan bawa hasil setengah
    jadi", PLANS §8) — PGO **tidak** dijadikan preset pengukuran skripsi;
    hasil dicatat sebagai temuan tesis (redistribusi komponen oleh PGO).
    Kandidat lanjutan opsional (P4-4b, deferred): retraining berimbang /
    `-fprofile-use` layout-only untuk memulihkan staging.
  - **P4-4b DIEKSEKUSI 2026-11-11 (setelah eksplorasi cmake perintah pemilik
    — "pakai optimization target")**: infrastruktur dikonsolidasikan —
    `add_pgo_flags` dihapus, logika GENERATE/USE pindah ke
    `add_optimizations_target`, seluruh flag set di-gate `ENABLE_TARGET_
    OPTIMIZATIONS` (default OFF → `native-release` canonical tetap no-op
    semantik, terverifikasi 0 flag baru di build.ninja + angka baseline
    ≡ kemarin), `-march=native` di-gate ganda `ENABLE_MARCH_NATIVE`
    (default OFF), `ENABLE_IPO` kini dideklarasikan (OFF), preset baru
    **`native-release-march`**, dan `add_profiling_target` (uProf per-config
    `ninja hotspots_ze_json_parser_benchmark` dsb.) diperbaiki
    (`EXPORT_OUT_DIR`→`OUT_DIR`, `report -i` direktori sesi) + di-wire ke
    kedua driver benchmark. Runbook server SAQ:
    `reports/P5-saq-server-runbook.md` (PR root terpisah).
    - **E1 — `native-release-march` (flag set + march) DITOLAK**: sandwich
      vs canonical (`zuu-20261111090544` vs `zuu-20261111090519`,
      window ~3.5 menit, kontrol stabil): FullWalk ladder flat
      (−0.4..−1.8%), saq −8.1%, **ParseOpen −6.5..−22.4%** (sections/
      ICF/linker-layout merugikan staging), ParseReference ±3%.
      march=native tidak memberi apa-apa di Zen 2 untuk jalur ini.
    - **E2 — `native-pgo` full-set (profil retrain atas flag set baru)
      DITOLAK sebagai default**: sandwich vs canonical
      (`zuu-20261111092425` vs `zuu-20261111090519`): FullWalk ladder
      **+11.9..+23.2%** (1mb 156.5→192.8 MB/s) — TAPI **ParseOpen
      −12.5..−25.1%** — PGO TIDAK memulihkan regresi staging dari flag
      set; pola campur P4-4 berulang.
    - **Keputusan P4-4b**: `native-release` tetap satu-satunya preset
      pengukuran skripsi; infrastruktur opt-in (preset march + target
      uProf + gate flag) masuk repo sebagai tooling eksperimen.
      Kesimpulan tesis: staging (scanner8+pairing) sangat sensitif
      layout — flag optimasi tambahan maupun PGO konsisten
      mendistribusikan performa DARI staging KE jalur walk.
    - **E3 — `native-release-ipo` (target-opts + LTO) KEEP sebagai
      preset opt-in berlabel, TIDAK dijadikan preset pengukuran**
      (ze_json PR #22 `df00ad9`): sandwich satu-window vs baseline
      `native-release` (`zuu-20261111175828`) dan kontrol
      `native-release-march` (`zuu-20261111180305`), kandidat
      `zuu-20261111180226`, semua `47bb543`, 36 record validator PASS.
      `ipo/base`: **ParseOpen 0.72–0.87x ✓**, FullWalk 0.88–0.98x ✓,
      tapi ReferenceScan **1.34–1.56x ✗**, ParseReference 1.10–1.19x ✗,
      Scanner64/128 1.01–1.14x ✗; `ipo/march` membuktikan LTO murni
      menguntung jalur parser & memulihkan regresi march pada
      Scanner8/Structural (0.66–0.83) namun merugikan jalur oracle.
      Laporan: `reports/E3-lto-sandwich.md` (root PR #29).
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
  **Update 2026-11-11**: limitasi "profiler tak tersedia" DICABUT — AMD uProf
  5.3.521.0 terpasang & PMU counter berfungsi (host di bawah Hyper-V; tetap
  terbaca). Analisa hotspot: `reports/P4-uprof-hotspots.md` — `scanner8`
  22-35% + `scan_string` 9-30% = dominan; IPC 1.84, mispredict hanya 0.82%
  (branch-dense tapi well-predicted) → gain berikutnya harus dari penghapusan
  branch (SIMD), bukan prediksi; iterator walk ~17-20% = kandidat struktural
  baru. Raw exhibit: `out/raw/uprof-20261110/`.

## P5 — Pengukuran lintas arsitektur (site server ditunda — akses SAQ belum ada)

- [x] **P5-1** — Paket runner untuk server SAQ: instruksi deploy konsisten
  (`node scripts/host-introspect.mjs` + `node scripts/node-benchmark/harness.mjs
  --site=saq_server`); hasil dipindah ke `out/measurements/`. — **SELESAI
  2026-11-11**: runbook `reports/P5-saq-server-runbook.md` (root PR #23),
  dieksekusi pemilik via SSH tanpa perubahan harness.
- [x] **P5-2** — Baseline V8 di server SAQ → record v1. — **SELESAI
  2026-11-11**: `server-lanjut-20261111040248-0340a72` (saq-report `0340a72`,
  Node 26.13.0/V8 14.6, i5-9400; repeats 5, cv ≤ 8%): 6 korpus × 3 konteks
  (body-parse 206.6–571.8 MB/s, store-read ≈ body-parse, export-stringify
  +19..+55%) — 6 record validator PASS; laporan `reports/P5-saq-server-baseline.md`.
- [x] **P5-3** — (opsional) ze-wasm64 di server SAQ → record v1. — **SELESAI
  2026-11-11**: `server-lanjut-20261111041314-b8deda6` (ze_json `b8deda6`,
  wasm64 C-ABI): 6.28–17.37 MB/s (korpus mikro..saq) turun ke 1.58 MB/s
  (1mb); **rasio in-situ V8/ze = 30–165x** (membuka di korpus besar) —
  garis bawah jalur full-walk wasm, bukan potensi ze_json.
- [x] **P5-4** — Perbandingan lintas mesin — **kolom @server terisi
  2026-11-11** (provenance saq-report `0340a72` identik antara situs;
  run dev ber-flag identik `zuu-20261111073103-0340a72` V8 +
  `zuu-20261111073127-79a41bd` ze-parser, diff cmake-only): **V8
  srv/dev 1.19–1.94x** (desktop 2.9 GHz + Node 26 vs laptop 2.1 GHz +
  Node 24; gap body-parse membuka di korpus besar 1.42→1.94), **ze
  wasm srv/dev 0.92–1.67x** (gap lebih kecil → profil memory-bound
  kurang diuntungkan clock). Kualitas run: server cv ≤ 8%, dev hingga
  18.7%. Keterbatasan tercatat: `ze_json.wasm` tidak ter-track git →
  artefak disalin manual, sidecar tanpa sha256 — interpretasi wasm
  dibatasi in-situ per situs; tindak lanjut: catat sha256 saat salin.
  (Fase awal dalam satu site dev tetap sumber komparatif utama.)
- [x] **P5-5** — Analisis & chart ke `out/charts/` (murni dari record validated). —
  **SELESAI 2026-11-11**: 3 figur matplotlib (arsip `reports/charts/`,
  master `out/charts/`): `p5_server_v8_contexts.png` (V8@server 3 konteks × 6
  korpus), `p5_server_insitu_ratio.png` (rasio V8/ze 32.9→164.2x),
  `p5_crosssite_v8_bodyparse.png` (dev vs server, provenance identik).
  Audit satuan P5-5: formula record terkonstruksi ulang dari raw exhibit
  (`bytes/s = ops × bytesPerOp / elapsed`, median-of-repeats) — cocok persis;
  konteks parse/walk memakai byte input korpus (apples-to-apples), sedangkan
  export-stringify memakai **byte output** restringify ident-2 (konvensi
  harness P2; di saq output≈input, di 1mb output 1.93x input) — dicatat
  eksplisit di laporan P5 agar tidak salah baca.
- [x] **P5-6** — Script build+verify wasm terstandar (`scripts/build-wasm.ps1`,
  root PR #27 `8fd14fe`): memaksa preset `wasm64-release`, verifikasi wajib
  build type / 9 export ABI / SIMD v128 / sidecar sha256
  `bindings/js/ze_json.wasm.sha256`, gate differential + smoke — menutup
  tindak lanjut P5-4 (artefak ke server kini terprovenance; hash dev saat
  ini `7e26044f…`, byte-identik sebelum/sesudah fix number).
- [x] **P5-7 (R5)** — Re-build wasm DI SERVER SAQ via `scripts/build-wasm.ps1`
  (salin `ze_json` submodule @`ab09adb` + script ke server, jalankan, catat
  sha256, bandingkan vs `7e26044f…`), lalu re-run harness dengan konteks fase
  baru (`wasm-open` / `wasm-walk-full` / `wasm-parse-full`, root PR #29;
  pasangan native `BM_ParseOnDemandWalkOnly` — ze_json PR #23) +
  `--scanner all` → matriks fase × jalur × situs untuk menentukan prioritas
  optimasi berikutnya (walk iterator vs staging). — **MATRIKS SELESAI
  2026-11-11** (`reports/R5-server-phase-matrix.md`, 34 record validator
  PASS): staging parity V8 di kedua situs (open/V8 0.4–1.4x), walk tanpa
  materialisasi 7.5–12.7x vs V8 (overhead per-step C-ABI), full 27–155x —
  **materialisasi JS mendominasi 58–92% waktu full**; scanner128 ranking
  bersih #1 di server (1.5–2.2x atas scanner8, semua korpus), dev campur.
  Prioritas: (1) jalur materialisasi JS, (2) batching walk ABI, (3) staging
  cukup konfigurasi (default scanner128). **Provenance artifact ditutup
  2026-11-11**: sha256 `ze_json.wasm` di server dilaporkan pemilik
  `7e26044fd61ea16af81a57630ab1e594b54ecf767cbb0126592b1f1c26928499` ==
  sidecar dev `bindings/js/ze_json.wasm.sha256` == re-hash independen
  (`certutil`) file build dev @`ab09adb` — artifact server byte-identik
  dengan build dev (provenance run server `123444`/`123516` penuh).

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

## R — Fondasi & scanner-mode surface (pra-parser; keputusan pemilik 2026-11-09)

- [x] **R1** — Refactor fondasi (ze_json PR #7 → `25645e6`): kontrak C-ABI jadi
  header tunggal `include/ze_json/abi/cabi.hpp` (v1, dimirror `ze_json.mjs`);
  `src/bindings/cabi.cpp` → `src/abi/cabi.cpp` (konvensi sisi core = **`abi`**;
  `bindings/` khusus adaptor bahasa; `ffi` dibatalkan); `swar_eq` pindah ke
  `utils/swar.hpp` (constexpr, API `repeat_byte_v`, migrasi `kOnes`/`kHigh`
  milik pemilik diteruskan) + gerbang serial 12 pola adversarial & 200k sweep
  (`TEST(SwarUtil)`); `core/simd.hpp` diperluas 5 op inline multi-ISA
  (wasm-simd128 ↔ SSE2, makro dihapus); `scanner128` kini dapat dibangun di
  wasm64 (`-msimd128` pada target wasm — **flag baru, baseline wasm lama tidak
  sebanding langsung**); doc stale `scanner.hpp` diperbaiki. Gerbang: ctest
  100%, npm smoke+differential 71/71.
- [x] **R2** — Scanner-mode surface (ze_json PR #8 → `ed2ffa1`): ABI v2 dengan
  ekspor additive `ze_scanner64` / `ze_scanner128` / `ze_structural_scan`;
  JS dapat memilih mode (`SCANNER_MODES`: structural | scanner8 | scanner64 |
  scanner128 | reference) via `binding.scan(mode)` + `ZeDocument({scanner})`
  (+ `hasScanner`/`assertScanner`, alias `scan8`/`referenceScan` dipertahankan);
  harness `--scanner` (default `scanner8` = kontinuitas kanonik; `all` = 5
  mode satu `run_id`); schema +`config.scanner_mode`. Gerbang: smoke PASS
  (abi=2), differential **71 × 5 mode**. Matriks in-run (dirty-run
  `zuu-20261109012207-25645e6`, 6/6 PASS, disebut sesuai AGENTS §4): di wasm
  pemenang **berbeda dari native** — scanner128 menang `saq_payload_v1`
  (1022 vs scanner8 721 MB/s) & `synthetic_1k` (889 vs 609); scanner8 tetap
  menang compact besar (10k/100k/1mb); dispatch default **tetap scanner8**
  (komentar "change ONLY this line" di parallel.cpp berlaku bila kelak
  diperlukan).
- [x] **R3** — Re-baseline kanonik wasm pada hash bersih pasca-`-msimd128`:
  `zuu-20261109015052-ed2ffa1` (scanner8 default, 6/6 PASS, tree bersih) —
  615 / 611 / 617 / 632 / 732 / 395 MB/s (1k/10k/100k/1mb/saq/checker);
  **baseline wasm pengganti** untuk analisis berikutnya (yang lama `85afad7`
  diarsip apa adanya, tidak sebanding lintas-flag).

## P7 — Implementasi parser on-demand (sampai tuntas; keputusan pemilik 2026-11-09)

- [x] **P7-1** — **Validator UTF-8** (ze_json PR #9 → `27e3218`): method
  Niagara dua-tabel (`10.1002_spe.2920`) + referensi scalar table-free.
  **Tabel `kUtf8Byte*` lama terbukti salah** lewat sweep diferensial
  ekshaustif vs oracle RFC 3629 ketat (surrogate ED A0-BF diterima, overlong
  `F0 8x` diterima, `F0 9x`/`F4 8x` valid ditolak) → generator diperbaiki
  dengan derivasi + nota provenance. Verifikasi: 1-byte & 2-byte penuh,
  3-byte lead ≥ C0 penuh (4.194.304), 4-byte terstruktur — 0 mismatch.
  Gerbang permanen `tests/utf8_test.cpp`: truth Tabel 8 hard-coded, sweep
  ekshaustif 1/2-byte + **3-byte penuh 16.777.216**, 4-byte terstruktur,
  truncation, json_checker pass, fuzz 200k — ctest **100% (2/2)**; wasm
  fresh build + smoke (abi=2) + differential 71×5 sepakat.
- [x] **P7-2** — **Number parser** (ze_json PR #10 → `55571fa`): grammar
  RFC 8259 + dekomposisi, lalu 4 jalur **satu kali pembulatan** masing-masing:
  ±0; integer ≤ 19 digit (u64→double tunggal); region eksak 128-bit
  (m < 2^53, |q| ≤ 22 — divisi bit-serial tanpa `__udivti3`, wasm tetap
  `-nostdlib`-clean); slow path bigint kapasitas-tetap (cap 768 digit dengan
  lipat LSD→eksponen, power-of-five scaling, divisor-shift untuk skala
  negatif). Semantik V8 (±Infinity/±0, "-0"). **Oracle `std::strtod`**:
  kurasi batas + sweep 1–19 digit × ±30 + string 20–800 digit +
  **fuzz 300k** + **200k round-trip %.17g** + tie subnormal eksak
  (2^-1075, 1.5/2.5 × 2^-1074 ties-to-even) — ctest **100% (3/3)**; wasm
  smoke (abi=2) + differential 71×5 sepakat. Bug tertangkap gerbang:
  digits_len memuat '.'; `is_zero` uji `n` bukan nilai; skala s2 negatif
  butuh divisor-shift; lipat LSD cap.
- [x] **P7-3** — **String token scan + unescape** (ze_json PR #11 →
  `8edcc8f`): `scan_string` (grammar RFC 8259 + `StringParts`
  {total_len, inner_len = batas atas decode, escape_count}) dengan
  validasi raw multibyte pakai anchor scalar P7-1 (encoded surrogate /
  overlong / truncation → `InvalidUtf8`; raw ctrl → `InvalidJson`).
  `unescape_string` walker **dua pass** (panjang → tulis) sehingga error
  grammar dan `InsufficientBuffer` tak menyentuh `dst`. Semantik V8
  diprobe empiris dan dikunci pemilik: pasangan surrogate → 4-byte UTF-8
  astral; **lone surrogate escape → pass-through verbatim 6 byte
  (kasus-preserve)**; `\u0000` → 0x00. Gerbang ctest **100% (4/4)**
  (simdjson `10.48550_arXiv.1902.08318` + Mison `10.14778_3115404.3115416`):
  sweep ekshaustif `\uXXXX` 65.536 × dua kasus, matriks pair 256×256,
  sweep raw ctrl 0x00–0x7F, tabel UTF-8 raw, prefix truncation,
  paritas kelas error, kontrak cap, span prefix-consumption, dan
  **fuzz 120k** (generatif + korup) vs referensi scalar terpisah;
  wasm smoke (abi=2) + differential 71×5 sepakat (string belum
  terekspos ABI — v3 di P7-5).
- [x] **P7-4** — **Value/Document API on-demand** (ze_json PR #12 →
  `a12d361`): `Value` (klasifikasi launcher satu load via tabel
  `kOndemandNodeType` tergenerate; materialisasi skalar malas memakai
  layer P7-2/P7-3; `StringSpan` zero-copy + flag `escaped`),
  `Document::open` (scan + staging), `get_root` (framing akar eager:
  scalar wajib tail whitespace, kontainer wajib pemilik seluruh
  indeks), `ArrayIter`/`ObjectIter` (skip kontainer anak hanya via
  indeks — latitude on-demand `10.1002_spe.3313`; framing skalar
  eksak; sticky error; empty container done-at-begin), `Field`.
  **Tabel match bracket LIFO** di-stage saat open (depth satu-counter
  tidak sound untuk cross-type `[ { ] }`; `kNoBracket` = pelanggaran
  framing). Perbaikan bersama: `utils/alloc.hpp` placement-new
  freestanding dibegi guard `__has_include(<new>)` (bentrok dengan
  TU hosted gtest). Gerbang `tests/value_test.cpp`: root framing +
  penolakan baseline-V8 (`[1 2]`, koma ekor, `:` hilang, `,` liar,
  literal rusak, root ganda), klasifikasi launcher, skip latitude
  (subtree rusak tak-tersentuh vs tersentuh→error), skip iteratif
  5000-level (tanpa rekursi), detached value, decode span lewat
  P7-3 — ctest **100% (5/5)**; wasm64 build hijau + harness smoke
  5 mode + record validator PASS; ABI tetap v2 (P7-5 = v3).
- [x] **P7-5** — **C-ABI v3 + wrapper JS parser** (ze_json PR #13 →
  `9479c08`): kontrak v3 di `cabi.hpp` (append-only; `kAbiVersion=3`)
  — pool slot statis `kParserSlotMax=64` (handle = slot id), Arena +
  Document placement-new per slot, arena kerja ter-carve dari bump
  heap bersama (`src_size*8*3+64`), `ze_reset_heap` menutup semua
  slot dulu; 11 ekspor parser (`ze_parser_open/root/close`,
  `ze_container_begin`, `ze_array_next`, `ze_object_next`,
  `ze_object_field`, `ze_value_kind`, `ze_get_string`,
  `ze_get_number`, `ze_get_bool`, `ze_is_null`,
  `ze_count_elements`) dengan packing scalar (ok = low-32; error =
  `JsonErrc<<32`) + step (`(cursor<<32)|ts`, done =
  `kStepSentinel<<32`) — traversal merekonstruksi iterator C++
  eksak dari frame lalu operator++/** ASLI dipetakankan (paper
  `10.1002_spe.3313`, Mison `10.14778_3115404.3115416`); angka via
  buffer dst 8 byte LE (`-0.0`/subnormal tidak bisa lewat packing);
  string lewat P7-3 (semantik V8 terkunci). Binding: `ABI_VERSION=3`
  + `NODE_KINDS`/`STEP_SENTINEL`/`PARSER_SLOT_MAX`, normalisasi
  `BigInt.asUintN(64)` (sentinel wasm i64 tiba bertanda — tanpa ini
  done terbaca `code -1`), kelas `ZeParser`: `parse()` materialisasi
  pohon berbentuk V8 (object null-prototype, `defineProperty`
  source-order/`__proto__` own-key/dup last-wins, dst tumbuh-
  gandakan, retry aman). Fix bersama: stubs i128 — `__ashlti3`/
  `__lshrti3` ditambah (clang-lowering shift variabel fast path
  P7-2) dan `__multi3` di-reimplement limb-32 murni (u64 promotion
  lama re-enter `__multi3` → rekursi tak hingga); terverifikasi
  driver sweep i128 ALL OK (boundary 0/63/64/127/128+). Gerbang:
  smoke main.mjs PARITAS (paritas tree 24 + divergensi `-0`/
  lone-surrogate + `__proto__` + 24 reject + frame walk + pool
  penuh + resetHeap), differential `compareParser` verdict + tree
  parity **71 dokumen × 5 mode sepakat** (escape-surrogate =
  verdict-only), ctest native **100% (5/5)**, wasm64 hijau,
  record `zuu-20261110001242-fdad44d_checker_batch_record.json`
  validator PASS (bukti instansiasi, bukan perbandingan).
- [x] **P7-6** — **Reference parser full-walk + gerbang json_checker**
  (ze_json PR #14 → merge `a5610d9`):
  `include/ze_json/ondemand/reference_parser.hpp` — walker rekursif
  byte-murni TANPA indeks struktural & TANPA tabel tergenerate:
  `ref_value_kind` klasifikasi 8-kasus branchy (bug tabel tergenerate
  tak bisa lolos gerbang diferensial), `ref_parse_document(src,size)`
  verdict `Result<size,JsonErrc>` + consumed; grammar token
  DI-REUSE dari P7-2/P7-3 (`scan_string`/`scan_number` — sumber
  kebenaran tunggal, header hanya menyumbang frame walk); semantik
  framing mirror document.cpp (EmptyJson ws-only; scalar root tail
  ws-only; object key wajib `"string"`+`:`+value — `{"a"}` reject;
  cross-type closer / `[1 2]` / `[1,]` reject). Gerbang
  `tests/reference_parser_test.cpp`: json_checker **31 fail REJECT
  dua sisi + fail1 (root string) & fail18 (nesting 20) ACCEPT dua
  sisi (paritas V8, exceptions legacy checker) + pass1-3 ACCEPT**,
  6 korpus benchmarks verdict-equality, ~94 fixture adversarial
  framing (kedua sisi sepakat DAN ekspektasi terkunci), invariants
  event (root pertama ts=0 input tanpa ws, ts monotonik non-berkurang,
  VALUES saja — keys bukan event), tally manual event count
  (`[1,2,3]`=4, `{"a":1}`=2, `"lonely"`=1, `{"a":{"b":null}}`=3).
  ctest native **100% (6/6)**, wasm64 hijau, smoke PASS, differential
  **71×5 sepakat** (reference parser tidak menyentuh ABI — tetap v3).


- [x] **P7-7** — **Benchmark komponen parser: native google-benchmark +
  harness engine `ze-parser`** (ze_json PR #15 → merge `d21304c`;
  root PR harness → merge `33bbf76`):
  **Bentuk "Native + binding JS"** (keputusan pemilik).
  (a) `ze_json/benchmarks/parser_benchmark.cpp` — target
  `ze_json_parser_benchmark` (helper `add_export_benchmark_target` +
  sidecar `METADATA_OUT`), 3 level × 6 korpus P0-8, Repetitions(5):
  `BM_ParseReference` (`ref_parse_document` anchor P7-6 — lantai
  grammar tanpa indeks), `BM_ParseOpen` (`Document::open` — staging
  scan+indeks+match ke arena), `BM_ParseOnDemandFullWalk` (open +
  `get_root` + visit SEMUA nilai + promote semua skalar via accessor
  asli); `Arena::reset()` rewind per dokumen (buffer tetap hot);
  korpus loader static-cache pola scanner_benchmark (P1-5/P1-6).
  (b) Baseline native run `zuu-20261110082340-a5610d9` — 6 record
  validator PASS (`out/measurements/zuu-20261110082340-a5610d9_*`,
  engine `scalar`, generator `google_benchmark`) + exhibit raw
  `out/raw/zuu-20261110082340-a5610d9/`: staging 743–1267 MB/s,
  full-walk 59–360 MB/s (saq 360, synthetic 122–177, checker_batch
  59), reference floor 522–1126 MB/s → **walk layer 3–4× lebih mahal
  dari staging** (target P4-3). Run sanity pertama (RUN_ID kosong)
  dibuang — tak digunakan analisis.
  (c) Harness `scripts/node-benchmark/harness.mjs` engine baru
  `ze-parser` — context `wasm-parse-full` (`ZeParser.parse()`
  materialisasi V8-shaped penuh, pasangan side JS
  `BM_ParseOnDemandFullWalk`; context basisPapers
  `10.1002_spe.3313`/`10.14778_3115404.3115416`/
  `10.1145_2807591.2807644`) + **kontrak rewind: `resetHeap()` per
  DOKUMEN di `run()`** (pattern differential.mjs — awal rewind
  sekali per korpus → carve mengakumulasi → trap OOB
  `Document::open`; fix = rewind sesudah tiap close).
  Baseline wasm run `zuu-20261110012919-a5610d9` — 6 record validator
  PASS (engine `wasm64_cabi`, generator `node_harness`):
  materialisasi 2.2–16.1 MB/s (saq 16.1, ladder 5.9–9.9,
  checker_batch 6.6, 1mb 2.2) → **biaya traverse ABI per-call
  mendominasi** (walk native 360 MB/s vs wasm 16 MB/s di saq).
  Smoke eksplorasi `zuu-20261110012913-a5610d9` (checker_batch saja)
  bukan run analisis.
  (d) Wiring CMake P0 yang lupa exhaust-kan: `MeasurementRegistry.cmake`
  baru di-include dari root `CMakeLists.txt` (sebelumnya tak pernah
  wired → `RUN_ID` kosong di nama file export; run pertama produksi
  `*_ze_json_parser_benchmark_.json` → dibuang); fix
  `HandleGit.cmake` `${GIT_EXECUTABLE}` → `${GIT_EXE}` (variabel
  `find_program` sebenarnya; hash kosong → rev-parse gagal quiet).
  Baseline loop P4-3: satu perubahan per pengukuran, re-run kedua
  target export pada hash sama, banding in-situ.

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
