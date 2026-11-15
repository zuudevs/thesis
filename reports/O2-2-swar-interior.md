# O2-2 — SWAR interior skip 8-byte (DITERIMA — menang di semua family)

Tanggal: 2026-11-15. Kandidat kedua keluarga **O2**, kondisional (GO
terbatas dari histogram ND-14). Perubahan (`src/ondemand/scalar.cpp`,
commit `515fddd`, ze_json PR #45 → merge `01a143f`, tag **`core/0.3.2`**,
wasm `9795f2e8…`): loop interior string kini berjalan per **blok SWAR
8-byte** — satu unaligned load, dua mask `utils::swar_eq` (`"` dan `\`,
bentuk carry-free hasil fix P4-2), skip 8 byte per blok bersih; lane
match pertama meresume scalar residue sehingga pasangan escape yang
melintasi batas blok dikonsumsi persis (backslash pasangan quote selalu
LEBIH AWAL di blok — match pertama selalu backslash). Byte-identity vs
`reference_scan` tetap gerbang. `@cite 10.1002_spe.2984`.

## 1. Identitas run (sandwich back-to-back, satu window)

| Sifat | Baseline (0.3.1) | Kandidat (0.3.2) |
|---|---|---|
| run_id nd9 | `zuu-20261115040553-117e59d` | `zuu-20261115034403-26e2bfa` |
| ze_json / wasm | `0aacd82` / `1d8960c9…` (rebuild byte-identik) | `01a143f` / `9795f2e8…` (abi 2026000302) |
| root | `117e59d` (main, pointer `0aacd82`) | `26e2bfa` (branch, pointer `01a143f`) |
| protokol | nd9 `--probe` 15×4, warmup 3, saq_payload_v1, tree bersih, validator PASS | identik |

Native gbench `BM_Scanner8/` (filter, Repetitions 5): `zuu-20261115035000-26e2bfa`
(kandidat) vs `zuu-20261115041100-117e59d` (baseline) — 12 record konversi
validator PASS (`reports/o2-2/`).

## 2. Hasil

### 2.1 wasm saq (nd9 sandwich — metrik acceptance)

| stage | baseline 0.3.1 | kandidat 0.3.2 | Δ |
|---|---:|---:|---:|
| **s2-open (fused)** | 0,1085 ms | **0,0822 ms** | **−24,2%** |
| s2b-scan | 0,0980 ms | 0,0721 ms | **−26,4%** |

### 2.2 native gbench `BM_Scanner8` (median, seluruh family)

| family | base 0.3.1 | cand 0.3.2 | Δ |
|---|---:|---:|---:|
| **saq** (acceptance) | 63,65 µs | 40,54 µs | **−36,3%** |
| synthetic_1k | 0,98 µs | 0,49 µs | −49,9% |
| synthetic_10k | 14,39 µs | 7,78 µs | −45,9% |
| synthetic_100k | 110,04 µs | 81,61 µs | −25,8% |
| synthetic_1mb | 1158,74 µs | 845,00 µs | −27,1% |
| checker_batch | 5,81 µs | 4,52 µs | −22,2% |

## 3. Verdict: **DITERIMA** — melampaui kriteria GO terbatas

Kriteria GO terbatas (ND-14 §4): saq menang **dan** synthetic tidak
regress. Hasil: saq menang (−36,3% native, −26,4% scan wasm sandwich)
**dan seluruh family synthetic justru menang** (−25,8%..−49,9%) —
kekhawatiran histogram tentang interior pendek (bw_p50 6 B) terbukti
tidak berbahaya: 1 load + 2 operasi SWAR per 8 byte tetap lebih murah
daripada 8× (2 compare + increment) bahkan di run pendek. Tidak ada
regress di family mana pun.

Implikasi: jalur scan native kini ~1,24–2,2 GB/s tergantung korpus;
komposisi s2-open wasm pasca-O2 (saq): scan 0,0721 / match 0,0169 /
carve 0,0014 dari fused 0,0822 — **match kini ~21% dari open**,
kandidat O2 berikutnya bergeser ke pass pairing (bukan scan).

## 4. Batas klaim

- Bukti = baseline↔kandidat run terpisah dalam satu window (pola
  C2/R5-9/O2-1), tree bersih keduanya, preset/korpus identik, sha
  artifact tercatat di record + sidecar.
- gbench = backend **native** (proxy algoritma; backend wasm diukur
  lewat nd9 sandwich saq). Konversi record 12/12 PASS.
- Site dev; server menyusul (sesi terpadu).

## 5. Deliverables

- ze_json PR #45 (`perf/o2-2-swar-interior`, `515fddd`) → merged
  `01a143f`, tag `core/0.3.2`; js tetap 0.3.0.
- Arsip `reports/o2-2/` (2 record nd9 + 12 record gbench + raw),
  sidecar `reports/registry/` (4 run baru), sinkronisasi tasks/plans.
- @cite: `10.1002_spe.2984` (SWAR), `10.14778_3115404.3115416` (Mison),
  `10.1002_spe.3313` (provenance).
