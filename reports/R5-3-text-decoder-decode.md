# R5-3 — Decode Span Wasm dengan TextDecoder Cached (Zero-Copy)

Eksperimen **#2** dari rencana optimasi R5-lanjutan (TASKS **O1-2**;
`reports/R5-2-array-count-drop.md` = eksperimen #1). Satu perubahan per
pengukuran, wrapper JS-only — artifact wasm byte-identik (`7e26044f…`
diverifikasi ulang dengan sha256 sebelum push).

## 1. Hipotesis & perubahan

Jalur decode wasm → JS memakai
`Buffer.from(bytes).toString('utf8')`: **copy** span ke heap JS +
alokasi Buffer + decode, per string DAN per key object. Profil R5
(@1mb): `utf8Slice` 1.7% + `toString [node:buffer]` 0.9% +
`fromArrayLike` 0.6% + `get buffer` 0.5% ≈ 5–6% self-time.

Perubahan: satu `TextDecoder('utf8', { ignoreBOM: true })` module-level
(stateless) menggantinya di ketiga situs (`getString`, `#materialize`
case 3, key object) — `decode(view)` membaca backing store wasm
langsung. `ignoreBOM: true` artinya *tidak* meng-strip U+FEFF: JSON
string boleh sah diawali `\uFEFF` dan JSON.parse mempertahankannya —
default TextDecoder akan menghapusnya (divergensi). Analisis
`encodeInto`: salah arah (string → byte) untuk jalur parse; tool yang
tepat byte → string adalah `decode`.

## 2. Gate kebenaran (fixture baru di smoke)

- Parity BOM: `"\uFEFFBOM-kept"` (string diawali BOM) dan
  `{"\uFEFFk":"a\uFEFFb"}` (BOM sebagai key + di tengah) — stringify
  identik dengan JSON.parse.
- Guard malformed-byte: paritas replacement-char decoder-WHATWG vs
  V8-Buffer pada 6 input (`0xFF`, overlong, encoded-surrogate,
  > U+10FFFF, truncated ×2) — **semua SAME** (keduanya satu U+FFFD per
  maximal subpart). Unreachable dari decode C++ (output selalu UTF-8
  valid — raw byte divalidasi, escape menghasilkan ASCII/pasangan
  valid, lone surrogate dipass-through sebagai teks literal) —
  dipasang untuk pemanggil langsung masa depan.
- Surrogate: sudah tercakup (smoke lone-surrogate pass-through +
  differential `SURROGATE_ESCAPE` verdict-only) — tidak berubah.
- Smoke PASS + differential 71 dokumen × 5 mode + parser/tree parity
  (head `b0fdd11`).

## 3. Protocol sandwich

Satu window (2026-11-12, UTC 22:16xx), 3 pasang bergantian
BASE(`07b452e`) ↔ CAND(`b0fdd11`), konteks `wasm-parse-full`, 6 korpus,
flag standar; **36 record validator PASS**. Slot dari timestamp
invokasi: BASE `1613`/`1631`/`1648`, CAND `1622`/`1639`/`1657`
(hash record tetap `b0fdd11` karena HEAD sama — file binding di-swap
in-worktree; mapping slot dari urutan timestamp, pola sama dengan
R5-1/R5-2).

## 4. Hasil (median MB/s; cand/base)

| korpus | BASE | CAND | rasio | pairs BASE | pairs CAND |
|---|---|---|---|---|---|
| synthetic_1k | 13.3 | 14.6 | 1.096 | 13.2/13.3/13.4 | 12.5*/14.6/14.7 |
| synthetic_10k | 8.8 | 9.8 | 1.109 | 6.2*/8.8/8.9 | 8.8/9.8/9.8 |
| synthetic_100k | 8.7 | 9.5 | 1.090 | 7.4/8.7/8.9 | 9.5/9.5/9.6 |
| synthetic_1mb | 8.6 | 9.5 | 1.103 | 7.4/8.6/8.7 | 9.5/9.5/9.6 |
| saq_payload_v1 | 19.1 | 21.5 | 1.125 | 15.5*/19.1/19.5 | 21.4/21.5/21.6 |
| checker_batch | 7.6 | 8.1 | 1.067 | 6.9/7.6/7.6 | 8.0/8.1/8.1 |

\* outlier satu pasangan (bimodal ringan transisi tier JIT, pola yang
sama dilihat di R5-1/R5-2); median robust. Gain konsisten 6.7–12.5%
di SEMUA korpus — sebanding dengan estimasi profil jalur Buffer,
sedikit lebih besar (Buffer juga mengalokasi; GC pressure ikut turun).

## 5. Kebenaran & provenance

- ze_json PR #26: `b0fdd11` (perf), merged `3e10e47`. Wasm tidak
  berubah (sha256 `7e26044f…`).
- Record: `out/measurements/zuu-2026111122{1613,1622,1631,1639,1648,1657}-b0fdd11_*.json`;
  raw per-repeat di `out/raw/` (out/ gitignored).
- Site: `dev_device`; angka hanya dibandingkan in-situ satu window.

## 6. Tindak lanjut

- Eksperimen berikutnya sesuai rencana: #3 cache `DataView` untuk
  `getDouble` (profil 4.7%; wasm memory tidak pernah grow — aman),
  lalu #4 fusi scan string C++ (wasm berubah — gerbang native penuh),
  #5 batch ABI, #6 investigasi wrong-map `#frame` (tracing terpisah).
