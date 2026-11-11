# R5-2 — Drop Array Pre-Size Count Pass (dan Bug Kuadratik `ze_count_elements`)

Eksperimen #1 dari rencana optimasi R5-lanjutan (TASKS **O1-6**;
`reports/R5-1-materialize-assign.md` adalah eksperimen #0/H1). Satu
perubahan per pengukuran, wrapper JS-only — artifact wasm byte-identik
(`7e26044f…`).

## 1. Hipotesis & perubahan

`#readArray` memanggil `countElements()` sebelum materialisasi untuk
pre-size `new Array(count.value)` + assert panjang. `count_elements()`
(C++) me-replay seluruh subtree (1× `begin_array` + 1 langkah
`ArrayIter` per anak) SEBELUM traversal materialisasi me-derive ulang
verdict framing yang sama. Perubahan: buang pass hitung; materialisasi
dengan `push()` dinamis. Kehilangan cakupan: tidak ada (mesin framing
sama); yang hilang hanya assert internal mismatch.

## 2. Temuan utama: pass hitung itu KUADRATIK

Profil CPU V8 @`synthetic_1mb` menunjukkan `Value::begin_array()` =
**66.9% self-time** di BASE — dan lenyap di CAND. Rantai penyebab
(terverifikasi di source):

1. `ze_count_elements` mem-frames Value dengan **cursor=0**
   (`src/abi/cabi.cpp:453` — komentar: "cursor 0 = re-derive by index
   walk");
2. `begin_array()` → `first_index_at_or_after(doc, 0, token_start)`
   berjalan **linear dari index 0** sampai posisi array
   (`document.cpp:69-72`) — per array;
3. total **O(#arrays × #indexes)** ≈ kuadratik terhadap ukuran dokumen;
   di 1mb (~39k index × 9.7k array) ≈ 190M langkah index.

`containerBegin` tidak pernah kena karena wrapper mengoper **cursor
kontinuasi** (frame.cursor) — amortisasi "each index visited once per
walk" hanya berlaku untuk cursor kontinuasi; cursor=0 membuat walk
menjadi O(posisi).

## 3. Protocol sandwich

Satu window (2026-11-12, UTC 22:0x), 3 pasang bergantian
BASE(`521a3f9`) ↔ CAND(`480de7c`), konteks `wasm-parse-full`, 6 korpus,
flag standar harness; 36 record validator **PASS**. Slot dari timestamp
invokasi: BASE `220617`/`220637`/`220656`, CAND `220628`/`220647`/
`220706`.

Catatan integritas data: (a) `ops` per repeat BERBEDA antar sisi
(BASE 1 op/repeat, CAND 2 op/repeat di 1mb) — record sudah per-op;
agregasi manual dari `elapsedMs` tanpa `ops` salah baca. (b) Dua pasang
record profil CPU (221010/221015) dibuat lalu DIHAPUS karena run profil
menulis record yang skewed oleh overhead profiler. (c) Upaya pertama
pagi ini memakai timestamp `0506xx` lokal — run_id memakai UTC; tidak ada
record yang hilang.

## 4. Hasil (median MB/s; cand/base)

| korpus | BASE | CAND | rasio | pairs BASE | pairs CAND |
|---|---|---|---|---|---|
| synthetic_1k | 12.7 | 13.0 | 1.030 | 12.6/12.7/12.8 | 12.7/13.0/13.3 |
| synthetic_10k | 8.2 | 8.6 | 1.049 | 8.1/8.2/8.3 | 6.3*/8.6/8.9 |
| synthetic_100k | 6.8 | 8.8 | **1.299** | 6.4/6.8/6.8 | 7.2*/8.8/8.8 |
| synthetic_1mb | 2.2 | 8.8 | **3.947** | 2.2/2.2/2.3 | 6.8*/8.8/8.8 |
| saq_payload_v1 | 18.5 | 19.3 | 1.040 | 18.5/18.5/18.5 | 16.5*/19.3/19.5 |
| checker_batch | 7.5 | 7.6 | 1.015 | 7.4/7.5/7.5 | 7.6/7.6/7.6 |

\* outlier satu pasangan (dilihat per-repeat: bimodal ringan, kemungkinan
transisi tier JIT); median tetap robust. Gain super-linear pada korpus
besar (100k 1.3× → 1mb 3.9×) konsisten dengan akar kuadratik §2 — dan
memprediksi korpus lebih besar lagi mendekati baseline penuh.

## 5. Kebenaran

- Smoke PASS + differential 71 dokumen × 5 mode + parser/tree parity
  (head `480de7c` dan `2f00bf3`).
- ze_json PR #25: `480de7c` (perf) + `2f00bf3` (comment fix), merged
  `07b452e`. wasm tidak berubah.

## 6. Tindak lanjut (TASKS)

- **O1-8 (baru)** — perbaiki kuadratik di sisi C++: `first_index_at_or_after`
  binary search (index array sorted — jawaban identik, O(log n), robust
  terhadap cursor basi) atau `ze_count_elements` menerima cursor
  (perubahan ABI). Kandidat perubahan measured-core → gerbang native
  penuh (ctest, sanitize, differential C++) — **keputusan pemilik**.
  API publik `countElements()`/`ze_count_elements` tetap terpasang
  (tooling), jadi bug ini tetap hidup untuk pemanggil lain sampai
  diperbaiki.
- Eksperimen berikutnya sesuai rencana: #3 TextDecoder zero-copy,
  #4 fusi scan string, #5 batch ABI.
