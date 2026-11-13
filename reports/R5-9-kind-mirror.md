# R5-9 — O1-4/H5: Mirror `valueKind` di JS (hapus 1 re-entry wasm per value)

Status: **DITERIMA** (ze_json PR #38, commit `ccdb610`, merged `f355f1a`,
2026-11-14). Baseline `d9e25ac` (wasm `35b7f773…` byte-identik — perubahan
JS-only, artifact identity utuh).

## 1. Hipotesis & perubahan

`ze_value_kind(slot, ts)` = validasi slot + bounds check + **satu load
tabel** `kOndemandNodeType[src_[ts]]` (`Document::classify`,
`src/ondemand/document.cpp`). Binding memanggilnya per value dari JS —
satu re-entry wasm penuh (trampoline + boxing BigInt dua arah + re-validasi
slot) untuk pekerjaan yang bisa dilakukan sisi JS: **lookup tabel dari
byte sumber sendiri**.

Perubahan (`bindings/js/ze_json.mjs`):
- tabel `kNodeKindByByte` — mirror provable member-set
  `GenerateLookups.py` (KEEP-IN-SYNC, `@cite` Mison + simdjson);
- `ZeParser.#srcBytes` = Uint8Array sumber milik pemanggil (stabil lintas
  heap-grow, byte-identik dengan salinan wasm yang ditulis `open()`);
- `#kindAt(ts)` = tabel JS + bounds mirror `classify()` (`ts >= len → 0`),
  fallback ke ABI bila parser dibangun tanpa `srcBytes`;
- 5 call-site beralih: `kind()`, `#materialize`, `get()`, `at()`,
  `#projectValue`. **Permukaan ABI tidak berubah.**

## 2. Kebenaran (gate)

- `tests/kind_mirror.mjs` (baru): tabel 256-byte == generated
  `lookups.hpp`; **1.266.946 pasangan in-situ** (41 dokumen × semua posisi
  × 6 korpus) mirror == `ze_value_kind`; bounds (`ts >= len`, `ts` 2^52).
- Regression: smoke PASS; lazy 43 checks PASS; differential 71 dokumen ×
  5 mode + parser/tree parity PASS; ctest native 6/6 PASS.

## 3. Pengukuran — sandwich satu window (protokol R5-8)

3 pasang (BASE `d9e25ac` ↔ CAND `ccdb610`), 6 korpus, engine `ze-parser`,
context `wasm-parse-full` (jalur A — materialisasi V8-shaped), 36 record
PASS validator; verifikasi sha256 file per swap (throw bila mismatch);
log atribusi `out/raw/o1_4_sandwich_log.json`; wasm identik kedua sisi.

| korpus | BASE MB/s | CAND MB/s | median cand/base | per-pasangan |
|---|---:|---:|---:|---|
| synthetic_1k | 18,07 | 19,49 | **1,085** | 1,085 / 0,995 / 1,101 |
| synthetic_10k | 11,68 | 13,02 | **1,115** | 1,126 / 1,025 / 1,115 |
| synthetic_100k | 10,98 | 11,73 | **1,075** | 1,075 / 1,006 / 1,075 |
| synthetic_1mb | 10,56 | 11,68 | **1,091** | 1,091 / 1,052 / 1,106 |
| saq_payload_v1 | 23,92 | 26,28 | **1,094** | 1,094 / 1,023 / 1,113 |
| checker_batch | 8,88 | 9,89 | **1,114** | 1,114 / 1,031 / 1,140 |

Median **+7,5% s/d +11,5%** — naik konsisten semua korpus, jauh di atas
envelope noise (drift ±2% antar pasangan, pola R5). Pair #2 sistematis
lebih rendah = drift mesin; tetap ≥0,995 dan tak membalik arah.

## 4. Interpretasi

- Berbeda dari O1-10/R5-8 (fusi step+kind → ABI v4 baru, **DITOLAK**
  netral 0,98–1,03): fusi masih melakukan SATU re-entry per value dan
  menambah kompleksitas ABI permanen. O1-4 menghapus re-entry klasifikasi
  **seluruhnya** — satu-satunya biaya tambahan sisi JS adalah satu load
  `Uint8Array` + indeks tabel, dan JS kehilangan dua boxing BigInt.
- Konsisten dengan ND-9 (boundary per-panggilan ≈ 0 pada agregat): gain
  bukan dari satu panggilan, tapi dari **penghapusan kelas panggilan**
  yang dilakukan sekali per value di jalur materialisasi.
- Implikasi ND-10/RQ2: A-path ze membaik ~9-11% di semua korpus; fase D
  tidak tersentuh (jalur count tidak memanggil valueKind).

## 5. Provenance

- ze_json PR #38 (`ccdb610` → merged `f355f1a`); branch
  `perf/o1-4-kind-mirror`; driver sandwich + log: temp
  (`o1_4_sandwich.mjs`) + `out/raw/o1_4_sandwich_log.json`; 36 record:
  `out/measurements/zuu-20261113{192020,192028,192037,192046,192054,192103}-*`.
- Prioritas lanjutan (profil O1-1): O1-5 (`#frame`/`#plain` hoist +
  dekode ramping, 9,1%) → O1-7 (ABI v4 thin-call — disetujui pemilik;
  ND-9 menempatkan manfaatnya di A/B, bukan fase D).
