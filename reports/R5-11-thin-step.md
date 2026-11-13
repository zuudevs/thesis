# R5-11 — O1-7/H7: ABI v4 thin step family (nol boxing BigInt per re-entry)

Status: **DITERIMA** (ze_json PR #40, commit `ae209f0`, merged `fe877f2`,
2026-11-14). Baseline `f355f1a` (O1-4+O1-5 terpasang). Keputusan ABI
**disetujui pemilik** sebelum eksekusi (2026-11-13/14).

## 1. Hipotesis & perubahan

R5-8 + ND-9 menempatkan sisa overhead jalur materialisasi di **bentuk
panggilan**: tiap step membayar 3× boxing `BigInt(param)` + 1× result
BigInt + objek frame — dan O1-10 membuktikan menggabungkan panggilan
tidak cukup (netral). O1-7 mengubah BENTUK kontraknya (additive):

- **v4 thin step family** (4 export baru, append-only): `ze_*4(u32 slot,
  u32 ts, u32 cursor, u64 out) -> i32` — scalar args sebagai i32 (nol
  `BigInt(...)` per call), frame lewat out pair u32 `(token_start,
  cursor)` (tepat kedua half v3), status i32 (0 ok / 1 done / <0 =
  −JsonErrc); out pointer pre-boxed **sekali per generasi heap**;
- binding: deteksi soft + guard sub-2-GiB → fallback v3 (jalur umum
  sub-4-GiB tetap utuh; semua signature/packing v3 tidak disentuh);
- gate `build-wasm.ps1`: 21 → 25 ekspor; wasm baru `c5b42b7d…` (v4).

## 2. Kebenaran (gate)

smoke PASS (ABI v4, walk via thin); lazy 43 checks; differential 71
dokumen × 5 mode + parser/tree parity; kind_mirror 4 groups; **ctest
native 6/6** (cabi.cpp v4 terkompilasi & teruji); `-VerifyOnly`: 25
ekspor + reproducible build.

## 3. Pengukuran — sandwich dua-artefak (protokol R5-8)

3 pasang (BASE `f355f1a`: binding+`35b7f773…` ↔ CAND `ae209f0`:
binding+`c5b42b7d…`), 6 korpus, `wasm-parse-full`, 36 record; sha256
KEDUA file diverifikasi per swap; log `out/raw/o1_7_sandwich_log.json`.

| korpus | BASE MB/s | CAND MB/s | median cand/base | per-pasangan |
|---|---:|---:|---:|---|
| synthetic_1k | 19,49 | 24,83 | **1,274** | 1,314 / 1,256 / 1,274 |
| synthetic_10k | 12,83 | 17,25 | **1,341** | 1,402 / 1,341 / 1,337 |
| synthetic_100k | 11,51 | 16,33 | **1,451** | 1,451 / 1,707 / 1,392 |
| synthetic_1mb | 11,47 | 15,68 | **1,401** | 1,401 / 1,547 / 1,355 |
| saq_payload_v1 | 26,14 | 33,64 | **1,299** | 1,313 / 1,269 / 1,299 |
| checker_batch | 9,63 | 12,79 | **1,329** | 1,332 / 1,329 / 1,076 |

Median **+27,4% s/d +45,1%**; 18/18 pasangan > 1,0. Eksperimen terbesar
dalam seri O1.

## 4. Interpretasi

- Hipotesis "biaya di bentuk frame, bukan jumlah panggilan" (R5-8) +
  "boundary kecil per panggilan tapi dikali banyak re-entry per value"
  (ND-9) terkonfirmasi: menghilangkan kelas boxing per re-entry bernilai
  +27–45% end-to-end pada materialisasi.
- Kumulatif loop O1 (O1-4 → O1-5 → O1-7) vs baseline `d9e25ac`:
  ~1,6–2,1× pada jalur A (perkiraan median antar-window — **narasi**,
  bukan bukti in-run; bukti tunggal = tiap sandwich).
- **Implikasi ND-10/RQ2**: verdict fase A 0,04× (ND-10, Node 26) direkam
  PRA-O1-4/5/7 → matriks ND-6 layak diukur ulang (fresh run baru) untuk
  melihat efek kumulatif pada verdict acceptance fase D & fase C;
  keputusan re-measure = pemilik (protokol ND-10 sudah siap).

## 5. Provenance

- ze_json PR #40 (`ae209f0` → merged `fe877f2`); branch
  `perf/o1-7-thin-step`; log sandwich `out/raw/o1_7_sandwich_log.json`;
  36 record `out/measurements/zuu-20261113{202723,202731,202740,202749,202757,202806}-*`.
- Desain kontrak: `include/ze_json/abi/cabi.hpp` §v4 (source of truth);
  mirror `ABI_VERSION=4` binding (fail-loud).
