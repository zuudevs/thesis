# P4 — Analisa Hotspot AMD uProf (P4-6 tambahan, 2026-11-10)

Profiler: **AMD uProf 5.3.521.0** (`AMDuProfCLI.exe`), mesin `dev_device`
(AMD Ryzen 5 5500U, Zen 2, 6C/12T, L1 32 KiB/L2 512 KiB/L3 4 MiB).
Target: `ze_json_parser_benchmark.exe` preset **native-release-with-debug-info**
(`8b281f6` — sumber identik dengan `native-release` main, + simbol PDB untuk
atribusi; optimasi level sama, jadi ranking hotspot sah untuk binary release).

> Limitasi lama "profiler khusus tidak tersedia" (P4-6) **dicabut** — uProf
> terpasang dan PMU counter berfungsi. Catatan lingkungan: uProf melaporkan
> `Virtual Machine: Yes, Hypervisor: Microsoft Hyper-V` (VBS/Core Isolation
> aktif) — PMU tetap terbaca, tapi pembacaan counter di bawah hypervisor
> dicatat sebagai keterbatasan interpretasi.

## Metodologi

- Config `hotspots` (TBP 10 ms + callstack user) untuk ranking fungsi; config
  `branch` + `cpi` (PMU) untuk karakter branch/IPC. Durasi collect 14-60 s,
  benchmark `--benchmark_filter=BM_ParseOnDemandFullWalk/<corpus>`
  `--benchmark_repetitions=1`.
- Raw exhibit: `out/raw/uprof-20261110/{saq-fullwalk,synth1mb-fullwalk,synth1mb-branch}/`
  (`session.uprof` + `report.csv` + database `*.db`).
- Counter metodologi: `@cite 10.1109_PMBS56514.2022.00011` (Unified Hardware
  Counter Metrics).
- Profil dipakai untuk **ranking**, bukan angka throughput (overhead profiler
  mendistorsi timing; angka keputusan tetap dari google-benchmark sandwich).

## Hasil — ranking hotspot FullWalk

### `saq_payload_v1` (string-heavy: 67.5% string byte, 0 frac token, 21.8% ws)

Total in-process 47.93 s CPU:

| # | Fungsi | CPU_TIME | % (dari 47.9 s) |
|---|---|---|---|
| 1 | `scanner8` (structural_scan) | 16.81 s | **35.1%** |
| 2 | `scan_string` | 14.30 s | **29.8%** |
| 3 | `ObjectIter::operator++` | 3.85 s | 8.0% |
| 4 | `ObjectIter::operator*` | 2.89 s | 6.0% |
| 5 | `walk_value` | 2.50 s | 5.2% |
| 6 | `next_key_after_comma` | 1.42 s | 3.0% |
| 7 | `ArrayIter::operator++` | 1.25 s | 2.6% |
| 8 | `frame_token_len` | 1.11 s | 2.3% |
| 9 | `Document::open` | 1.03 s | 2.1% |
| 10 | `Value::get_string_span` | 0.97 s | 2.0% |

Dua pekerja byte-scanning (`scanner8` + `scan_string`) = **65%**; iterator
walk = ~17%; number layer tidak masuk 10 besar.

### `synthetic_1mb` (ladder: ~13% digit byte, 5.9k frac + 29k int token/MB)

Total in-process 52.23 s CPU:

| # | Fungsi | CPU_TIME | % |
|---|---|---|---|
| 1 | `scanner8` | 11.47 s | **22.0%** |
| 2 | `parse_number` | 6.01 s | 11.5% |
| 3 | `walk_value` | 5.66 s | 10.8% |
| 4 | `scan_string` | 4.74 s | 9.1% |
| 5 | `ObjectIter::operator++` | 4.35 s | 8.3% |
| 6 | `scan_number` (simbol clone kedua) | 4.12 s | 7.9% |
| 7 | `ArrayIter::operator++` | 3.33 s | 6.4% |
| 8 | `ObjectIter::operator*` | 2.81 s | 5.4% |
| 9 | `frame_token_len` | 1.93 s | 3.7% |
| 10 | `Document::open` | 1.34 s | 2.6% |

Layer number (`parse_number` + `scan_number`, dua simbol — LLVM
cloning/partial-inline) ≈ **19.4%** di ladder vs hampir nol di saq —
konsisten komposisi korpus. `scanner8` tetap raja di kedua korpus.

## Karakter counter PMU (whole-process, jendela 14 s, synth1mb FullWalk)

| Metrik | Nilai | Interpretasi |
|---|---|---|
| IPC | **1.84** | Tinggi — pipeline tidak stall berat; bukan memory-bound (1 MB muat L3) |
| CPI | 0.54 | Sehat |
| Branch density | **248.3 / 1000 inst** | ~25% instruksi adalah branch — sangat branch-dense (khas scanner scalar) |
| Branch mispredict | 2.03 / 1000 inst (**0.82%** dari branch) | RENDAH — branch terprediksi baik |
| `scanner8` spesifik | IPC 1.55, density 331/1000, misp 0.82% | Fungsi paling branch-dense & IPC terendah |
| L1 BTB correction | ~187 / 1000 inst | BTB override sering (banyak situs branch) |

## Implikasi (P4-3 A5 — keputusan kandidat berikutnya)

1. **Bottleneck #1 lintas korpus = `scanner8`** (22-35%), disusul `scan_string`.
   Karakternya: branch-dense tapi **well-predicted** (misp 0.8%) dan IPC cukup
   tinggi → gain berikutnya harus datang dari **menghapus branch** (klasifikasi
   SIMD per-blok ala simdjson/Mison), BUKAN dari memperbaiki prediksi.
   KONSISTEN dengan bukti P4-2/P4-3: klasifikasi vektor/SWAR kalah karena
   overhead loop-vektor > biaya branch terprediksi pada Zen 2 @ 2.1 GHz ini —
   jadi C3 (UTF-8 SIMD / SIMD classification) tetap **deferred** dan kini punya
   alasan counter eksplisit: IPC 1.84 + misp 0.8% menyisakan sedikit headroom
   stall; target vektor harus mengurangi jumlah instruksi per byte, bukan
   mengurangi mispredict.
2. **Number layer ≈ 19% di ladder** — sudah terima gain C2 (+20-33% FullWalk
   ladder). Sisa peluang: jalur slow-path (>15 digit) yang kini keluar dari
   10 besar; prioritas rendah.
3. **Iterator walk (~17-20%)** — `ObjectIter::operator++/*` di saq 14%:
   kandidat "struktural" (mengurangikerja per token) yang belum pernah disentuh
   eksperimen; menarik untuk P4 lanjutan bila PGO tidak menutup celah.
4. **PGO (P4-4) kini berjalan di titik yang tepat**: profil panas terpusat di
   sedikit fungsi → inlining/layout PGO berpeluang menutup jarak antara
   native-release dan batas IPC.

## Reproduksi

```powershell
& "C:\Program Files\AMD\AMDuProf\bin\AMDuProfCLI.exe" collect --config hotspots `
  -o out\raw\uprof-20261110\saq-fullwalk `
  -w ze_json\build\native-release-with-debug-info\benchmarks `
  --env-var "CORPUS_DIR=<root>\corpus" `
  ze_json\build\native-release-with-debug-info\benchmarks\ze_json_parser_benchmark.exe `
  --benchmark_filter=BM_ParseOnDemandFullWalk/saq --benchmark_repetitions=1
& "C:\Program Files\AMD\AMDuProf\bin\AMDuProfCLI.exe" report -i out\raw\uprof-20261110\saq-fullwalk
```

Catatan operasional: CLI uProf men-paging output ("Press any key...") saat
stdout di-redirect — jalankan di window terpisah atau kirim keypress otomatis.
