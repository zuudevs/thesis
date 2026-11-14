# R5-12 — Ladder kumulatif loop O1 (satu window, 4 state × 6 korpus)

Status: **lengkap** (chart `o1-cumulative`, script
`scripts/o1_cumulative_chart.py`, 2026-11-14). Motivasi: absolut
lintas-window sandwich membawa **drift mesin ~11%** (state konten-identik
`a7e9c45`/`47ff76e` terukur 29,39 vs 26,14 MB/s di window O1-5 vs O1-7)
→ trend kumulatif yang jujur butuh ladder satu window.

## 1. Protokol

4 state ze_json diukur **back-to-back dalam satu window** (interleaved,
swap binding+wasm terverifikasi sha256 per state; log
`out/raw/o1_ladder_log.json` + `o1_ladder2_log.json`):

| Stage | State | Isi |
|---|---|---|
| S0 | `d9e25ac` | pre-O1 (kondisi ND-10) |
| S1 | `ccdb610` | +O1-4 kind-mirror (PR #38) |
| S2 | `a7e9c45` | +O1-5 frame-decode (PR #39) |
| S3 | `ae209f0` | +O1-7 thin-step v4 (PR #40, wasm `c5b42b7d…`) |

3 pasangan interleaved × 4 state × 6 korpus (`ze-parser/wasm-parse-full`)
+ **3 pass tambahan** (median-of-6) setelah terdeteksi interferensi sesaat
pada pass-1 `synthetic_1mb` (5,14 MB/s vs 14,93 pass-2 — terdilusi).
**2 run V8** (`v8/body-parse`) di awal & akhir window sebagai garis
referensi. 156 record PASS validator diarsip **committed**:
`reports/o1-loop/` (run_id pinned di script — chart reproducible tanpa `out/`).

## 2. Hasil (median-of-6, MB/s)

| korpus | S0 | S1 | S2 | S3 | kumulatif | V8 (ref) |
|---|---:|---:|---:|---:|---:|---:|
| synthetic_1k | 16,52 | 17,89 | 19,82 | 22,53 | **1,36×** | 355 |
| synthetic_10k | 10,85 | 11,98 | 13,50 | 15,25 | **1,41×** | 263 |
| synthetic_100k | 10,23 | 10,83 | 12,55 | 14,35 | **1,40×** | 247 |
| synthetic_1mb | 9,35 | 10,69 | 11,90 | 14,33 | **1,53×** | 232 |
| saq_payload_v1 | 21,01 | 21,87 | 26,81 | 30,93 | **1,47×** | 560 |
| checker_batch | 8,09 | 8,85 | 9,50 | 12,18 | **1,51×** | 193 |

**Semua korpus naik monoton S0→S3 (18/18 sel per-state ≥ naik); kumulatif
1,36×–1,53×.** Kontribusi per langkah (saq): O1-4 +4%, O1-5 +23%,
O1-7 +15%. Gap ke V8 (saq): ~26× → ~18×.

## 3. Interpretasi & batas

- Ladder satu window menghilangkan drift antar-window; ratio in-window
  per langkah konsisten dengan sandwich R5-9/10/11 (bukti tetap
  per-sandwich; ladder = gambaran kumulatif yang drift-controlled).
- O1-5 tampak paling besar di saq (+23%) pada ladder ini — per-gabungan
  antar langkah tidak additive-linear (interaksi kodegen/layout); klaim
  per-langkah tetap milik sandwich masing-masing.
- Gap 18× ke V8 tetap besar → prioritas lanjutan: re-measure ND-6
  pasca-O1 (verdict fase), open-path (ND-9 s2-open), ND-11 HTTP.

## 4. Artefak

- Chart: `out/charts/o1-cumulative.{png,svg}` + arsip
  `reports/charts/o1-cumulative.svg`; CSV `out/charts/data/o1-cumulative.csv`.
- Script: `scripts/o1_cumulative_chart.py` (rewrite — sumber lama yang
  menunjuk `out/` kosong digantikan; run_id pinned → reproducible).
- Record: `reports/o1-loop/` (156; 12 ze run × 6 korpus + 2 V8 run × 6
  korpus × 2 window? — 12+12 = 84 ze + V8 12 = lihat folder).
