# ND-9 — Diagnosis Biaya Jalur Count (`readCount()`), TEREKSEKUSI

Eksekusi: 2026-11-13/14 (dev + server), setelah ND-10 — tree bersih, gate
fail-fast, 15 ronde + 3 warmup, CYCLES=4 bracket-samples, tanpa trimming,
parity guard **360/360 PASS per site** (countElements == jumlah child root
V8 per dokumen per siklus). Protokol: `docs/measurement/nd9-parser-cost-diagnosis.md`
— **diagnosis, bukan optimasi**; stage diukur dari ekspor ABI yang sudah
ada; stage bertumpuk dilaporkan sebagai batas terikat (s2-open secara
inseparable memuat arena carve + structural scan + bracket match).

**Verdict: `s2-open` mendominasi jalur count (~88–90% dari total per-op),
biaya boundary JS/BigInt per panggilan ABI ≈ 0** — hipotesis "boxing ABI =
penyebab utama" di jalur `readCount()` **terbantahkan**; kandidat
perbaikan fase D harus menyasar *open* (scan/match), bukan thin-call.

## 1. Identitas run

| | dev | server |
|---|---|---|
| run_id | `zuu-20261113181631-4940f1d` | `server-lanjut-20261113181730-5a90545` |
| root / ze_json / saq-report | `4940f1d` / `d9e25ac` / `8c7f2d4` | `5a90545` / `d9e25ac` / `8c7f2d4` |
| Runtime | Node 26.13.1 (V8 14.6) | Node 26.13.1 (identik) |
| wasm sha256 | `35b7f773…` | `35b7f773…` (byte-identik, sidecar) |
| Record | PASS validator | PASS validator |

Catatan: root hash beda antar site (dev mengekor PR #56 dokumentasi);
**isi harness identik** — komparasi sah pada level library (ze_json/saq-report/wasm
identik, warisan verifikasi ND-10).

## 2. Hasil — Σmedian per siklus penuh (6 dokumen, ms/op)

| Stage (batas komponen) | dev | server | Porsi (dev) | Porsi (server) |
|---|---:|---:|---:|---:|
| s1-copy — alloc + write JS→wasm | 0,0057 | 0,0066 | 3,6% | 3,1% |
| **s2-open — arena + scan + match** (batas atas tiap komponen di dalamnya) | **0,1397** | **0,1933** | **88,1%** | **90,0%** |
| s3-count — traversal `countElements` | 0,0103 | 0,0116 | 6,5% | 5,4% |
| s4-close — close + resetHeap | 0,0027 | 0,0031 | 1,7% | 1,4% |
| s5-boundary — floor per-panggilan ABI (×4096, 0 argumen) | ~0,0000 | ~0,0000 | ≈0% | ≈0% |
| **Σ per siklus** | **0,158** | **0,215** | | |

Konsistensi silang: Σ ≈ 0,158 ms (dev) berimpit dengan ze fase D ND-10
(0,134–0,140 ms/op) — jalur yang diukur sama.

## 3. Interpretasi yang sah

1. **Dominasi open, bukan traversal/boundary.** Di ukuran dokumen SAQ
   (3,6–39 KB), biaya `ze_parser_open` (arena carve 3×src_size×8 +
   structural scan satu pass + bracket match) menelan ~9 dari 10 bagian
   waktu jalur count. `countElements` sendiri murah (6%) — index struktural
   bekerja sesuai desain Mison (`@cite 10.14778_3115404.3115416`).
2. **Boundary ABI terbantahkan sebagai bottleneck fase D.** Floor per
   panggilan (boxing BigInt→u64) terukur ≈ nol pada agregat per-op.
   Implikasi: kandidat *slot reuse* / *ABI v4 thin-call* **tidak menyasar
   fase D**; O1-7 tetap relevan untuk jalur **materialisasi (fase A/B)**
   yang melakukan re-entry per value (profil R5: walk 7,5–12,7× vs V8) —
   diagnosis ini tidak mengukur jalur tersebut.
3. **Gap hardware terlokalisasi di open:** server +38% vs dev pada s2-open
   (0,193 vs 0,140 ms) dengan runtime/wasm/korpus identik — konsisten
   dengan sisa gap fase D ND-10 (server 1,13× vs dev 1,45×). Bandwidth/
   latensi memori i5-9400 (DDR4-2133) vs Ryzen 5 5500U kandidat penjelas;
   klaim kausal perlu pengukuran counter (di luar scope ini).
4. **Arah countermeasure fase D:** biaya ze saat ini sudah dekat floor
   open; peningkatan rasio D hanya mungkin dari (a) mempercepat open
   (instrumentasi core lanjutan: scan vs carve vs match — eksperimen
   terpisah), atau (b) bekerja di level yang menghindari open per-request
   (caching bytes kanonik sudah ada di `saq-report 8c7f2d4`). Kandidat
   §7 plan doc diprioritaskan ulang berdasarkan tabel ini.

## 5. Batas

- s2-open tidak didekomposisi (butuh instrumentasi core) — dilaporkan
  sebagai batas terikat, sesuai larangan protokol.
- Diagnosis hanya jalur count; tidak mengklaim apa pun tentang jalur
  materialisasi (A/B) atau HTTP end-to-end (ND-11).

## 6. Arsip

- Record: `reports/nd9/zuu-20261113181631-4940f1d-nd9-cost-dev_device.record.json`,
  `reports/nd9/server-lanjut-20261113181730-5a90545-nd9-cost-saq_server.record.json`
- Raw exhibit: `reports/nd9/raw/<run_id>/{metadata.json,nd9_stages.json}`
- Generator: `scripts/bench/nd9_cost_diagnosis.mjs` (tanpa perubahan kode)
