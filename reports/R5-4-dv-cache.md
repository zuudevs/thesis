# R5-4 — Cache DataView untuk `getDouble`

Eksperimen **#3** dari rencana optimasi R5-lanjutan (TASKS **O1-3**;
`reports/R5-3-text-decoder-decode.md` = eksperimen #2). Satu perubahan
per pengukuran, wrapper JS-only — artifact wasm byte-identik
(`7e26044f…` diverifikasi ulang).

## 1. Hipotesis & perubahan

`ZeJson.getDouble` membangun `new DataView(memory.buffer, dstPtr, 8)`
per angka yang diparse (alokasi objek per number). Modul wasm tidak
pernah grow memory (64 MiB statis — tidak ada `memory.grow` di
`cabi.cpp`) → backing buffer stabil seumur modul → view dicache.

Perubahan: cache DataView per pasangan (backing-buffer identity,
`dstPtr`). Harness mem-parses satu dokumen per open + `resetHeap()`
per dokumen (rewind bump heap) → `numPtr` selalu alamat sama → hot
path hit 100%. Guard buffer-identity membangun ulang view bila build
masa depan mulai grow (kontrak no-growth didokumentasikan).

## 2. Protocol

Dua window sandwich (dev, 2026-11-12 UTC 22:09xx dan 22:14–22:26xx),
3 pasang per window, 6 pasang total BASE(`3e10e47`) ↔ CAND(`2fb661f`),
konteks `wasm-parse-full`, 6 korpus; **72 record validator PASS**.
Slot dari timestamp invokasi (BASE ganjil, CAND genap).

## 3. Hasil (median MB/s; cand/base, 6 pasang)

| korpus | BASE | CAND | rasio | num/KB |
|---|---|---|---|---|
| synthetic_1k | 14.2 | 15.0 | 1.055 | — (per-call overhead dominan) |
| synthetic_10k | 9.4 | 9.9 | 1.047 | — |
| synthetic_100k | 9.4 | 9.6 | 1.022 | — |
| synthetic_1mb | 9.3 | 9.5 | 1.021 | **34.8** |
| saq_payload_v1 | 20.9 | 20.2 | 0.967 | **3.1** |
| checker_batch | 7.8 | 8.0 | 1.035 | **20.0** |

Korpus angka-dense memberi gain konsisten (1mb 1.021×, checker
1.035×); dokumen kecil lebih besar (1k 1.055×) karena overhead
per-call (alokasi + GC) lebih dominan.

## 4. Catatan integritas: saq -2% = noise, bukan sinyal

- Bobot angka saq nyaris nol (30 numbers / 9 KB = 3.1 num/KB):
  efek cache ~0 di korpus itu — tidak ada mekanisme yang membuat
  CAND *lebih lambat* secara alami di sana.
- Mesin terukur **drift +7%** antar window (BASE median 19.8 →
  20.9 MB/s); pasangan adjacent B↔C menyebarkan -6.4%…+0.4%.
- Per-repeat `elapsedMs` BASE vs CAND hampir identik (~200–204 ms,
  ops 42–48) — selisih median datang dari pembagian `ops`/window.
- Keputusan: terima (gain konsisten pada korpus yang relevan, tanpa
  regresi mekanistik); saq dipantau di window eksperimen berikutnya.

## 5. Kebenaran & provenance

- Smoke PASS + differential 71 dokumen × 5 mode + parser/tree parity
  (head `2fb661f`).
- ze_json PR #27: `2fb661f`, merged `a4ae62d`. Wasm tidak berubah
  (sha256 `7e26044f…`).
- Record: `out/measurements/zuu-2026111122{2009,2018,2027,2035,2044,2053,2143,2152,2200,2209,2217,2226}-2fb661f_*.json`;
  raw di `out/raw/` (out/ gitignored).
- Site: `dev_device`; angka hanya dibandingkan in-situ satu window.

## 6. Tindak lanjut

- Eksperimen berikutnya: #4 fusi scan string C++ (wasm berubah —
  gerbang native penuh: ctest, sanitize, differential C++, rebuild +
  sha256 baru), #5 batch ABI, #6 investigasi wrong-map `#frame`.
