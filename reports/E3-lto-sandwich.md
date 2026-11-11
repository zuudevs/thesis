# E3 — LTO Sandwich: `native-release-ipo` vs `native-release(-march)`

Eksekusi: asisten (window tunggal, 2026-11-11, mesin dev `zuu` — AMD Ryzen 5 5500U,
clang/LLVM 23.1.5). Semua record **validator PASS (36/36)**; exhibit mentah di
`out/raw/<run_id>/`, record tervalidasi di
`out/measurements/<run_id>_<korpus>_{scanner,parser}_record.json`.

## 1. Pertanyaan & desain

**Pertanyaan (TASKS E3):** apakah LTO (`ENABLE_IPO=ON`, `-flto=thin` via
`add_optimizations_target`) menuntung jalur pengukuran `ze_json` secara
signifikan untuk dijadikan preset pengukuran, atau tetap opt-in?

**Desain sandwich satu-window** (satu blok sekuensial, tanpa intervensi lain,
5 repetisi per instance, median-of-repetitions; semua run commit `47bb543`):

| run_id | preset | peran |
|---|---|---|
| `zuu-20261111175828-47bb543` | `native-release` | baseline |
| `zuu-20261111180305-47bb543` | `native-release-march` | kontrol `-march=native` + target-opts |
| `zuu-20261111180226-47bb543` | `native-release-ipo` | kandidat target-opts + LTO |

Atribusi: `march/base` = efek opsi target + `-march=native`;
`ipo/march` = **efek murni LTO** (di atas flag set yang sama);
`ipo/base` = efek gabungan vs baseline kanonik. `-flto=thin` terverifikasi
aktif di FLAGS build dir kandidat; ctest 6/6 hijau di ketiga preset.

**Catatan akuntansi:** saat window, `CMakePresets.json` (preset kandidat itu
sendiri) belum di-commit di tree `ze_json` → ketiga record disimpan dengan
`git_commit.dirty=true` (dikonfigurasi sengaja; isi perubahan = preset
eksperimen ini). Angka **tidak** dibandingkan lintas window/mesin/preset lain.

## 2. Hasil — scanner (median µs per op; rasio median)

| family | base range (µs) | march/base | ipo/march | ipo/base |
|---|---|---|---|---|
| BM_Scanner8 | 0.98–1117 | **1.20–1.54 ✗** | **0.66–0.82 ✓** | 0.96–1.09 (netral) |
| BM_Structural | 1.0–1461 | **1.10–1.48 ✗** | **0.67–0.83 ✓** | 0.82–1.14 (campur) |
| BM_Scanner64 | 0.7–1282 | 0.99–1.09 | 0.96–1.06 | **1.05–1.14 ✗** |
| BM_Scanner128 | 0.7–1369 | 0.99–1.05 | 1.00–1.06 | **1.01–1.08 ✗** |
| BM_ReferenceScan | 1.1–1471 | 0.94–1.01 | **1.34–1.61 ✗** | **1.34–1.56 ✗** |

Anomali sampling: `BM_Structural/synthetic_1mb` baseline stddev 531 µs
(mean 1622 vs median 1461) — sel `march/base=1.10` korpus itu rendah
kepercayaannya; pola family tetap terbaca dari 5 korpus lainnya.

## 3. Hasil — parser (median µs per op; rasio median)

| family | base range (µs) | march/base | ipo/march | ipo/base |
|---|---|---|---|---|
| BM_ParseOpen | 1.4–1806 | **0.88–0.96 ✓** | **0.81–0.98 ✓** | **0.72–0.87 ✓** |
| BM_ParseOnDemandFullWalk | 5.2–7303 | **0.86–0.99 ✓** | 0.90–1.07 | **0.88–0.98 ✓** |
| BM_ParseReference | 1.3–1760 | 1.01–1.21 | 0.96–1.18 | **1.10–1.19 ✗** |

## 4. Atribusi & pembacaan

1. **LTO (ipo/march) membantu jalur parser on-demand**: `ParseOpen`
   0.81–0.98 (korpus besar 0.81–0.85) dan memulihkan regresi `march` pada
   `Scanner8`/`Structural` (0.66–0.83). LTO melipat kode inlining antar TU
   (arena/scanner/number) sehingga jalur panjang `Document::open` menguntung.
2. **Harganya jalur reference**: `BM_ReferenceScan` 1.34–1.61× dan
   `BM_ParseReference` 1.10–1.19× lebih lambat — oracle kebenaran ikut
   terdegradasi; kemungkinan layout/pertukaran inline yang merugikan loop
   bit-serial panjang (tidak diselidiki lebih jauh — bukan target E3).
3. **`Scanner64/128` netral di ipo/march tapi tetap 1.01–1.14× di ipo/base**
   (dibawa oleh flag set target-opts, bukan LTO-nya).
4. **`-march=native` sendiri merugikan `Scanner8`/`Structural`** (1.20–1.54×)
   konsisten di semua korpus — mekanisme tidak dibuktikan (dugaan: lowering
   vektorizer atas lookup tabel 8-bit); kontrol ini hanya pemisah efek LTO.
5. **`BM_Structural/synthetic_1mb`** satu-satunya korpus yang menunjukkan
   `ipo/base` jelas menang (0.841) — tapi baseline-nya tidak stabil (stddev
   531 µs); diperlakukan sebagai sinyal lemah, bukan bukti.

## 5. Verdict

**KEEP sebagai preset opt-in berlabel — TIDAK dijadikan preset pengukuran
kanonik.**

- Untung `ParseOpen` (−13…−28%) dan `FullWalk` (−2…−12%) nyata, tapi harga
  jalur reference (oracle) 10–56% dan `Scanner64/128` 1–14% membuat profil
  library keseluruhan menurun; mempromosikannya akan membuat semua record
  berikutnya tidak sebanding dengan baseline kanonik `native-release`.
- Preset disimpan di `CMakePresets.json` sebagai `native-release-ipo`
  (displayName berlabel *E3 experiment; local labeled builds only*), pola
  yang sama dengan `native-release-march`.
- Alternatif mengejar untung `ParseOpen` tanpa harga reference: jalur PGO
  yang sudah ada (`native-pgo`, P4-4) — P4 report sudah mencatat pola serupa
  pada `ParseOpen`; re-evaluasi per-path (mis. `-flto` hanya untuk target
  parser) tidak disarankan karena melanggar "satu flag set per preset
  pengukuran" (AGENTS.md §4/§6).

## 6. Bukti

- Exhibit mentah: `out/raw/zuu-20261111{175828,180226,180305}-47bb543/`
  (2 gbench + 2 sidecar metadata + `host.json` + split per target).
- Record tervalidasi: `out/measurements/zuu-20261111{175828,180226,180305}-47bb543_<korpus>_{scanner,parser}_record.json`
  — 36 record, semua validator PASS.
- Baseline → kandidat: `47bb543` → `47bb543` (hash sama; variannya flags
  preset, keduanya di-commit/berlabel eksplisit; `dirty=true` karena preset
  kandidat sendiri belum di-commit saat window).
