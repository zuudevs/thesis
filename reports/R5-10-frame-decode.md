# R5-10 — O1-5/H6: Hoist konstanta frame decoder + fast path dekode eksak

Status: **DITERIMA** (ze_json PR #39, commit `a7e9c45`, merged `47ff76e`,
2026-11-14). Baseline `f355f1a` (sudah memuat O1-4; wasm `35b7f773…`
byte-identik — perubahan JS-only).

## 1. Hipotesis & perubahan

`#frame`/`#plain` mendekode packed u64 dengan aritmetika BigInt di setiap
panggilan; `#frame` mengalokasikan `BigInt(STEP_SENTINEL)` **per
panggilan** hanya untuk membandingkan hi (profil O1-1: 9,1% gabungan
#frame/#plain). Perubahan (`bindings/js/ze_json.mjs`):

- `kStepSentinelU32` — perbandingan hi sebagai number (nol alokasi BigInt);
- `kFrameDone` — singleton frozen untuk verdict done (stateless; mutasi
  aksidental fail-loud di ESM strict);
- `#frame` fast path: packed value < 2^53 → dekode hi/lo aritmetika float
  **eksak** (`Math.floor(n/2^32)`, `n%2^32`) — nol alokasi BigInt.
  Sentinel (~2^64) tak terjangkau jalur ini by construction; slow path
  (hi ≥ 2^21 / raw negatif) mempertahankan `asUintN`;
- `#plain` fast path: hasil `[0, 2^32)` → `Number(rawRet)` langsung.

Cakupan fast path: seluruh dokumen < 2 MiB (cursor < 2^21) — semua
korpus pengukuran + workload SAQ (3,6–39 KB).

## 2. Kebenaran (gate)

smoke PASS; lazy 43 checks PASS; differential 71 dokumen × 5 mode +
parser/tree parity PASS; kind_mirror 4 groups PASS. Semua jalur step
(containerBegin/arrayNext/objectField/objectNext + done/error/frame)
terlatih differential; wasm & ABI tak tersentuh.

## 3. Pengukuran — sandwich satu window (protokol R5-8)

3 pasang (BASE `f355f1a` ↔ CAND `a7e9c45`), 6 korpus, `wasm-parse-full`,
36 record PASS; sha256 per swap terverifikasi; log
`out/raw/o1_5_sandwich_log.json`.

| korpus | BASE MB/s | CAND MB/s | median cand/base | per-pasangan |
|---|---:|---:|---:|---|
| synthetic_1k | 19,79 | 21,78 | **1,101** | 1,101 / 1,086 / 1,117 |
| synthetic_10k | 13,17 | 14,33 | **1,075** | 1,088 / 1,075 / 1,047 |
| synthetic_100k | 11,66 | 13,50 | **1,165** | 1,168 / 1,117 / 1,165 |
| synthetic_1mb | 11,79 | 13,04 | **1,105** | 1,117 / 1,082 / 1,105 |
| saq_payload_v1 | 26,29 | 29,39 | **1,125** | 1,125 / 1,109 / 1,136 |
| checker_batch | 9,71 | 11,16 | **1,143** | 1,143 / 1,150 / 1,123 |

Median **+7,5% s/d +16,5%**; **18/18 pasangan > 1,0** (1,047–1,168).

## 4. Interpretasi

- Profil 9,1% `#frame`/`#plain` terkonfirmasi nyata pasca-O1-4 — alokasi
  BigInt per call (termasuk `BigInt(STEP_SENTINEL)`) adalah biaya yang
  konsisten terukur, berbeda dengan R5-8 yang menghapus SATU panggilan
  tapi tetap membayar dekode BigInt + objek frame.
- Kumulatif O1-4+O1-5 vs baseline `d9e25ac`: ~1,19–1,30× pada jalur
  materialisasi A (perkiraan dari median per korpus, window berbeda —
  narasi, bukan bukti in-run).
- Sisa overhead kini dominan di **objek frame yang dialokasikan per
  step** + pekerjaan materialisasi JS — persis target **O1-7 (thin-call)**
  yang telah disetujui pemilik (ND-9 menempatkan manfaat O1-7 di A/B).

## 5. Provenance

- ze_json PR #39 (`a7e9c45` → merged `47ff76e`); branch
  `perf/o1-5-frame-decode`; log sandwich `out/raw/o1_5_sandwich_log.json`;
  36 record `out/measurements/zuu-20261113{195852,195900,195909,195917,195926,195935}-*`.
