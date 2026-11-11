# R5 — Matriks Fase × Jalur × Situs (server SAQ re-run, `ab09adb`)

Eksekusi server: pemilik via SSH, 2026-11-11 (batch siang UTC), mengikuti
polanya `reports/P5-saq-server-runbook.md`. Run dev pendamping: asisten,
window berbeda (satu mesin, dua invocation; sel bising di-re-run terpisah).
Semua record **validator PASS (34/34)**.

## 1. Run yang masuk

| run_id | provenance | isi | site |
|---|---|---|---|
| `server-lanjut-20261111123614-0340a72` | saq-report `0340a72` | v8: 3 konteks × 6 korpus | saq_server |
| `server-lanjut-20261111123444-ab09adb` | ze_json `ab09adb` | ze-parser fase: open/walk/full × 6 | saq_server |
| `server-lanjut-20261111123516-ab09adb` | ze_json `ab09adb` | ze-wasm64 `--scanner all` (5 mode) × 6 | saq_server |
| `server-lanjut-20261111093404-b8deda6` | ze_json `b8deda6` (pagi) | ze-parser parse-full × 6 (sanity artifact lama) | saq_server |
| `zuu-20261111131706-ab09adb` | ze_json `ab09adb` | fase × 6 (dev) | dev_device |
| `zuu-20261111131733-ab09adb` | ze_json `ab09adb` | scanner-all × 4 (dev) + re-run checker/saq (`131901`, `131908`) + fase checker re-run (`131915`) | dev_device |

- Host server: i5-9400 @2.90 GHz, Node 26.13.0 (V8 14.6) — identik P5.
  Dev: Ryzen 5 5500U, Node 24.19.0.
- **Catatan akuntansi**: batch server dijalankan TANPA `--expose-gc`
  (`gc_between_repeats=false`, berbeda dari P5-2 yang `true`). Pembanding
  **in-situ satu batch** (123614 V8 vs 123444/123516 ze) tetap valid;
  perbandingan dengan record P5-2 lama bersifat kualitatif.
- **Provenance artifact**: `dirty=true` pada record (untracked artifact),
  konten tracked bersih. **Menunggu sha256 output `build-wasm.ps1` dari
  server** untuk menutup rantai provenance artifact wasm (vs dev
  `7e26044f…`); sel `b8deda6`-vs-`ab09adb` di §5 sengaja tidak
  diinterpretasi sebagai efek kode.

## 2. Dekomposisi fase (ze-parser @`ab09adb`, MB/s; share % dari waktu full)

| korpus | open | walk | full | open% | walk% | materialisasi% |
|---|---|---|---|---|---|---|
| **server** | | | | | | |
| synthetic_1k | 334.9 | 35.5 | 12.6 | 3.8 | 31.8 | 64.4 |
| synthetic_10k | 359.3 | 22.8 | 9.0 | 2.5 | 37.2 | 60.3 |
| synthetic_100k | 362.3 | 23.3 | 6.2 | 1.7 | 24.8 | 73.5 |
| synthetic_1mb | 346.7 | 21.6 | 1.7 | 0.5 | 7.3 | **92.2** |
| saq_payload_v1 | 433.2 | 56.0 | 21.2 | 4.9 | 33.0 | 62.1 |
| checker_batch | 168.6 | 18.1 | 7.7 | 4.5 | 37.7 | 57.8 |
| **dev** | | | | | | |
| synthetic_1k | 291.4 | 27.9 | 8.1 | 2.8 | 26.3 | 71.0 |
| synthetic_10k | 357.7 | 15.7 | 5.8 | 1.6 | 35.3 | 63.0 |
| synthetic_100k | 372.1 | 14.7 | 4.3 | 1.2 | 28.1 | 70.8 |
| synthetic_1mb | 332.7 | 14.4 | 2.0 | 0.6 | 13.3 | 86.1 |
| saq_payload_v1 | 572.7 | 46.4 | 12.7 | 2.2 | 25.1 | 72.6 |
| checker_batch* | 182.3 | 16.7 | 5.1 | 2.8 | 27.8 | 69.4 |

\* checker_batch dev = re-run `131915` (cv open masih 25% — lower
confidence; walk/full cv ≤ 7%).

**Bacaan**: staging (`open`) 0.5–5% dari waktu penuh; traversal struktural
(`walk`) 7–38%; **materialisasi JS mendominasi 58–92%** dan membuka lebar
di korpus besar (1mb server 92%).

## 3. Rasio in-situ vs V8 body-parse (satu batch server; kolom dev kualitatif lintas-window)

| korpus | server full/V8 | server walk/V8 | server open/V8 | dev full/V8 | dev walk/V8 | dev open/V8 |
|---|---|---|---|---|---|---|
| synthetic_1k | 28.7 | 10.2 | **1.1** | 25.8 | 7.5 | **0.7** |
| synthetic_10k | 31.9 | 12.7 | **0.8** | 26.7 | 9.9 | **0.4** |
| synthetic_100k | 44.3 | 11.8 | **0.8** | 35.6 | 10.4 | **0.4** |
| synthetic_1mb | 154.5 | 12.1 | **0.8** | 68.1 | 9.3 | **0.4** |
| saq_payload_v1 | 29.2 | 11.1 | **1.4** | 31.7 | 8.7 | **0.7** |
| checker_batch | 27.2 | 11.5 | **1.2** | 25.8 | 11.9 | **0.9** |

(Total-bytes V8 123614: body-parse 208–619 MB/s; export-stringify 313–634.)

**Bacaan inti R5**:
1. **Staging sudah parity V8 di kedua situs** (open/V8 0.4–1.4×; V8 saat itu
   melakukan parse+materialize penuh, ze hanya staging). Scanner bukan lagi
   bottleneck pengukuran ini.
2. **Walk tanpa materialisasi tetap 7.5–12.7× lebih lambat dari V8 penuh**
   — overhead per-step C-ABI frame re-entry (boxing BigInt per panggilan,
   3–4 calls per value), bukan biaya scanning-nya.
3. **Full parse 27–155×** di server; di korpus besar gap memburuk
   (154×) karena materialisasi mendominasi.

## 4. Matriks scanner `--scanner all` (MB/s; server satu run `123516`, dev = `131733` + re-run `131901`/`131908`)

| korpus | structural | scanner8 | scanner64 | scanner128 | reference |
|---|---|---|---|---|---|
| **server** | | | | | |
| synthetic_1k | 434.2 | 443.8 | 811.7 | **996.0** | 374.6 |
| synthetic_10k | 374.0 | 411.6 | 745.6 | **827.0** | 365.3 |
| synthetic_100k | 432.5 | 429.7 | 689.3 | **692.2** | 349.0 |
| synthetic_1mb | 437.7 | 436.7 | 670.9 | **688.1** | 368.8 |
| saq_payload_v1 | 482.7 | 479.0 | 869.5 | **906.3** | 426.7 |
| checker_batch | 301.5 | 297.4 | 414.3 | **466.5** | 300.0 |
| **dev** | | | | | |
| synthetic_1k | 471.2 | 514.4 | 685.1 | **810.4** | 356.6 |
| synthetic_10k | 490.1 | 440.5 | 559.2 | **561.4** | 359.3 |
| synthetic_100k | 550.0 | 563.4 | 572.3 | 493.0 | 322.7 |
| synthetic_1mb | 463.6 | **543.8** | 536.2 | 471.4 | 344.8 |
| saq_payload_v1* | 620.9 | 680.9 | 882.3 | **969.9** | 545.4 |
| checker_batch* | 366.0 | 330.4 | 354.2 | **372.3** | 265.1 |

\* baris dev saq/checker dari re-run (run pertama bising, cv sampai 47%).

**Bacaan**:
- **Server: ranking bersih & konsisten — scanner128 > scanner64 >
  scanner8 ≈ structural > reference** di SEMUA korpus; 128 unggul
  1.5–2.2× atas scanner8. i5-9400 (Intel, AVX2 era) menyukai lowering
  SIMD128-nya.
- **Dev: campur** — 128 menang di 1k/10k/saq/checker, tapi flat di
  100k dan kalah di 1mb (scanner8 544). Zen 2 wasm tidak konsisten
  menikmati lane lebar.
- Implikasi konfigurasi (bukan riset): **`scanner128` kandidat mode
  default untuk jalur wasm** di kedua situs; keputusan final menunggu
  run dev yang lebih tenang di 100k/1mb.

## 5. Sanity artifact lama vs baru (server, TIDAK untuk disimpulkan)

parse-full `b8deda6` (pagi) vs `ab09adb` (siang): 1.10–1.34× lebih cepat.
Window berbeda (pagi vs siang, cv sampai 10%) dan status artifact (rebuild
atau reuse) belum terkonfirmasi tanpa sha256 → **dibiarkan tanpa
interpretasi** sampai hash build-wasm dilaporkan pemilik. Library code
antara kedua hash identik pada jalur wasm (fix number `6258d43` terbukti
byte-identik; PR #22/#23 hanya preset/benchmark), sehingga delta ini
diduga window — bukan kode.

## 6. Verdict & prioritas optimasi berikutnya

Urutan kerja yang didukung matriks ini:

1. **Materialisasi JS (fase 3)** — dominan 58–92% waktu full; korpus besar
   paling tertekan (full/V8 154× @1mb). Target: kurangi biaya per-node
   (defineProperty/key handling, decode string → Buffer, boxing BigInt
   konversi hasil skalar) di `ze_json.mjs`/ABI v3.
2. **Walk ABI batching (fase 2)** — walk 7.5–12.7× vs V8 penuh meski
   tanpa materialisasi; target: kurangi panggilan per value (batch frame
   per call / index-walk ala Mison) sehingga boxing BigInt diamortisasi.
3. **Staging (fase 1)** — sudah parity; cukup keputusan konfigurasi
   (mode default `scanner128` untuk wasm), tanpa riset baru.

Provenance artifact wasm server: menunggu sha256 dari pemilik untuk
menutup P5-7.

## 7. Bukti

- Server: `out/raw/server-lanjut-20261111{093404,123444,123516,123614}-*/`,
  record `out/measurements/server-lanjut-20261111..._record.json` (24).
- Dev: `out/raw/zuu-20261111131{706,733,901,908,915}-ab09adb/`, record
  masing-masing (10).
- Validasi: 34/34 PASS (`scripts/measurement-schema/validate.py`).
