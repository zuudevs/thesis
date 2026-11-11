# P5 — Baseline Server SAQ: V8 & ze_json wasm64 in-situ

Eksekusi: pemilik via SSH, 2026-11-11, mengikuti
`reports/P5-saq-server-runbook.md`. Analisa & validasi: asisten.
Semua record **validator PASS (12/12)**; exhibit mentah di
`out/raw/<run_id>/`, record tervalidasi di
`out/measurements/<run_id>_<corpus>_record.json`.

## 1. Run yang masuk

| run_id | provenance | engine | site |
|---|---|---|---|
| `server-lanjut-20261111040248-0340a72` | saq-report `0340a72` (PR #2) | v8 (baseline V8) | saq_server |
| `server-lanjut-20261111041314-b8deda6` | ze_json `b8deda6` (post-C2) | ze-parser (wasm64 C-ABI) | saq_server |

- Korpus: 6 korpus `corpus/benchmarks/` (manifest sha256 per dokumen
  terbawa di setiap sidecar + record) — byte-identik antara kedua run.
- Konfigurasi harness identik dengan runbook: `--repeats 5`,
  `min_time 200 ms`, `warmup 300 ms`, `gc_between_repeats=true`.
- Host server: `server-lanjut` — Intel Core i5-9400 (6C, 2.90 GHz),
  8 GB RAM, Windows 11 Education, **Node 26.13.0 (V8 14.6.202.34)**.
  Host dev (pembanding): `zuu` — AMD Ryzen 5 5500U (12T, 2.10 GHz),
  Node 24.19.0 (V8 13.6.233.17).

## 2. Baseline V8 saq-report di server (P5-2)

Tiga konteks jalur panas JSON server SAQ (bytes/s, mean; cv):

| korpus | body-parse | store-read | export-stringify |
|---|---|---|---|
| checker_batch | 206.6 (6.9%) | 206.0 (1.9%) | 311.4 (1.5%) |
| saq_payload_v1 | 571.8 (1.8%) | 571.5 (6.0%) | 604.2 (3.7%) |
| synthetic_1k | 335.2 (3.3%) | 327.5 (3.4%) | 446.9 (2.3%) |
| synthetic_10k | 268.2 (3.8%) | 279.0 (0.9%) | 413.3 (2.3%) |
| synthetic_100k | 267.0 (1.0%) | 263.5 (0.6%) | 371.6 (7.9%) |
| synthetic_1mb | 259.2 (0.8%) | 259.8 (1.1%) | 336.6 (1.9%) |

Pola konsisten dengan situs dev: body-parse ≈ store-read (payload JSON
sama dikonsumsi dua jalur). **Catatan akuntansi**: body-parse,
store-read, dan wasm-parse-full diakuntansi atas **byte input**
(total bytes korpus per op); export-stringify atas **byte output**
(restringify ident-2, konvensi harness P2) — jangan dibandingkan
langsung lintas konteks: di korpus ident-2 output ≈ input
(saq 604 vs parse 572 — setara), di synthetic_1mb output 1.93x input
(record 336.6 MB/s output ≈ 174.8 MB/s input, yaitu stringify lebih
lambat dari parse per byte input). cv < 8% di seluruh sel; korpus
mikro (checker_batch) paling berisik — sesuai ekspektasi runbook §7.

### Verifikasi satuan (audit 2026-11-11)

Dikonstruksi ulang dari exhibit mentah: `bytes/s = ops × bytesPerOp /
elapsed_s`, record memakai **median-of-repeats** — cocok persis untuk
semua sel yang diaudit (ze saq 17.37, V8 saq body-parse 571.80, 1mb
body-parse 259.2, 1mb export 336.6-as-output). Satu op = satu pass
penuh atas seluruh korpus di semua konteks (batch semantics, sama
dengan pola benchmark C++ P1-5/P1-6). Rasio V8/ze §3 memakai body-parse
(input bytes) vs wasm-parse-full (input bytes) — apples-to-apples.

## 3. ze_json wasm64 in-situ di server (P5-3) & rasio V8/ze

`ze-parser/wasm-parse-full` (full walk parser wasm64, ABI v3):

| korpus | ze-parser (MB/s) | cv | V8/ze rasio (body-parse) |
|---|---|---|---|
| checker_batch | 6.28 | 1.8% | 32.9x |
| saq_payload_v1 | 17.37 | 3.0% | 32.9x |
| synthetic_1k | 11.09 | 2.5% | 30.2x |
| synthetic_10k | 7.23 | 1.9% | 37.1x |
| synthetic_100k | 5.05 | 2.5% | 52.8x |
| synthetic_1mb | 1.58 | 1.4% | 164.2x |

**Interpretasi**: parser wasm64 on-demand kini ±30-165x di bawah V8
native di server (di mesin yang sama, korpus identik). Rasio membuka
miring seiring ukuran korpus (30x → 164x) — walk per-byte wasm memang
tidak bisa mengikuti JIT native, dan di korpus besar dominasi kerja
per-byte (bukan per-dokumen). Angka ini adalah **garis bawah
on-demand wasm** (full walk); jalur scanner/staging native belum
diekspos via wasm benchmark, jadi rasio ini BUKAN ukuran potensi
ze_json, melainkan status jalur wasm saat ini (temuan tesis: gap
wasm-vs-native dan margin kerja implementasi).

## 4. Perbandingan lintas situs (P5-4 kolom @server)

Provenance saq-report identik (commit `0340a72`) antara run dev dan
server; korpus byte-identik (manifest sha256); versi Node/V8 beda
(dev 24.19.0/13.6 vs server 26.13.0/14.6) — dicatat sebagai bagian
dari eksperimen RQ2 (same code, different site/runtime).
Run dev dibuat dengan flag harness identik: `zuu-20261111073103-0340a72`
(V8) dan `zuu-20261111073127-79a41bd` (ze-parser; diff
`b8deda6..79a41bd` = infrastruktur cmake saja, jalur parser/wasm
tidak disentuh — komparabel). Semua record validator PASS.

### V8: server vs dev (bytes/s, cv)

| korpus | konteks | dev | server | srv/dev |
|---|---|---|---|---|
| checker_batch | body-parse | 139.5 (1.0%) | 206.6 (6.9%) | 1.48 |
| checker_batch | store-read | 139.5 (15.4%) | 206.0 (1.9%) | 1.48 |
| checker_batch | export-stringify | 221.7 (12.2%) | 311.4 (1.5%) | 1.40 |
| saq_payload_v1 | body-parse | 402.0 (10.2%) | 571.8 (1.8%) | 1.42 |
| saq_payload_v1 | store-read | 339.1 (15.4%) | 571.5 (6.0%) | 1.69 |
| saq_payload_v1 | export-stringify | 509.0 (7.7%) | 604.2 (3.7%) | 1.19 |
| synthetic_1k | body-parse | 209.2 (18.7%) | 335.2 (3.3%) | 1.60 |
| synthetic_1k | store-read | 222.2 (10.0%) | 327.5 (3.4%) | 1.47 |
| synthetic_1k | export-stringify | 389.2 (1.6%) | 446.9 (2.3%) | 1.15 |
| synthetic_10k | body-parse | 155.2 (9.3%) | 268.2 (3.8%) | 1.73 |
| synthetic_10k | store-read | 167.4 (2.9%) | 279.0 (0.9%) | 1.67 |
| synthetic_10k | export-stringify | 302.3 (11.6%) | 413.3 (2.3%) | 1.37 |
| synthetic_100k | body-parse | 153.7 (9.1%) | 267.0 (1.0%) | 1.74 |
| synthetic_100k | store-read | 163.6 (2.5%) | 263.5 (0.6%) | 1.61 |
| synthetic_100k | export-stringify | 235.3 (11.9%) | 371.6 (7.9%) | 1.58 |
| synthetic_1mb | body-parse | 133.3 (18.1%) | 259.2 (0.8%) | 1.94 |
| synthetic_1mb | store-read | 165.4 (5.1%) | 259.8 (1.1%) | 1.57 |
| synthetic_1mb | export-stringify | 244.8 (4.0%) | 336.6 (1.9%) | 1.38 |

- Server lebih cepat **1.19–1.94x** di semua sel — konsisten dengan
  perbedaan kelas mesin (desktop 6C/2.9 GHz vs laptop mobile
  2.1 GHz) + runtime (Node 26 vs 24).
- **Gap body-parse membuka seiring ukuran korpus** (1.42 → 1.94 pada
  saq → 1mb): parser terikat throughput memori + clock; desktop
  menang keduanya. export-stringify gap paling kecil (1.19–1.40).
- **Kualitas run**: server jauh lebih stabil (cv ≤ 8% seluruh sel) vs
  dev (cv hingga 18.7% — laptop dengan gangguan latar). Perbandingan
  lintas situs memakai mean dengan cv dilaporkan; interpretasi RQ2
  memakai tren antar-korpus, bukan sel individual.

### ze-parser wasm64: server vs dev

| korpus | dev | server | srv/dev |
|---|---|---|---|
| checker_batch | 4.47 (6.6%) | 6.28 (1.8%) | 1.41 |
| saq_payload_v1 | 10.40 (13.5%) | 17.37 (3.0%) | 1.67 |
| synthetic_1k | 8.67 (1.3%) | 11.09 (2.5%) | 1.28 |
| synthetic_10k | 5.91 (2.9%) | 7.23 (1.9%) | 1.22 |
| synthetic_100k | 4.07 (14.2%) | 5.05 (2.5%) | 1.24 |
| synthetic_1mb | 1.71 (18.5%) | 1.58 (1.4%) | 0.92 |

ze wasm: server lebih cepat 1.22–1.67x di 5/6 korpus; synthetic_1mb
hampir paritas (0.92 — sel dev cv 18.5%, mean tidak robust). Gap ze
lebih kecil dari gap V8 → profil kerja wasm (interpreter-based,
memory-bound) kurang diuntungkan clock desktop dibanding JIT native.

## 5. Provenance & keterbatasan

- **Hash provenance**: `0340a72` (saq-report) dan `b8deda6` (ze_json)
  keduanya commit valid di history submodule — diambil otomatis oleh
  harness dari git di server.
- **`ze_json.wasm` tidak ter-track git**: server mendapat artefak via
  salin manual (runbook §4); sidecar TIDAK menyimpan sha256 artefak,
  sehingga byte-identik dev-vs-server tidak ter-verify. **Tindak
  lanjut**: catat sha256 artefak saat salin (atau commit artefak ke
  submodule) sebelum RQ2 final; untuk saat ini semua interpretasi
  wasm dibatasi in-situ per situs (aman, karena perbandingan V8/ze
  dilakukan dalam satu situs).
- **Node beda antar situs** (24 vs 26): bagian dari faktor "site" RQ2,
  bukan noise; disebut di setiap tabel.
- V8@server dan ze@server adalah **dua run terpisah** berjarak ~10
  menit di mesin idle yang sama — bukan sandwich; perbandingan
  antar-engine di §3 disertai cv kedua run.

## 6. Status tugas

- **P5-1** ✓ runner + runbook dipakai apa adanya di server (tanpa
  perubahan harness).
- **P5-2** ✓ baseline V8@server v1 (6 korpus × 3 konteks) + run dev
  ber-flag identik untuk pembanding (provenance `0340a72` sama).
- **P5-3** ✓ ze-wasm64@server v1 + run dev pembanding.
- **P5-4** ✓ kolom `@server` terisi (tabel §4): V8 server/dev
  1.19–1.94x, ze wasm server/dev 0.92–1.67x, gap V8 membuka di korpus
  besar, gap ze lebih kecil. Fase awal RQ2 (in-situ per situs + rasio
  antar-situs ber-provenance) tercukupi.

## 7. Figur analisis (P5-5)

Dibangun murni dari record tervalidasi (matplotlib 3.11): master PNG di
`out/charts/` (gitignored), arsip vektor ter-commit di `reports/charts/`:

| figur | isi |
|---|---|
| `p5_server_v8_contexts.svg` | Baseline V8@server — 3 konteks × 6 korpus (median-of-repeats) |
| `p5_server_insitu_ratio.svg` | Rasio in-situ V8/ze-parser per korpus (32.9x → 164.2x) |
| `p5_crosssite_v8_bodyparse.svg` | V8 body-parse dev vs server (provenance saq-report identik `0340a72`) |
