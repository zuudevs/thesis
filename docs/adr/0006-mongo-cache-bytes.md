# ADR 0006 — Kandidat cache-bytes Mongo (`_cacheBytes`)

- **Status:** Accepted
- **Tanggal:** ND-6 (2026-11-12); saq-report PR #4 (`8c7f2d4`)
- **Pengambil keputusan:** pemilik skripsi; dieksekusi mengikuti disiplin
  satu-perubahan-per-eksperimen

## Konteks

Setelah ADR 0005, fase D masih hanya **1.10×** (`...064001-0dcb418`).
Profil menunjukkan penyebab: jalur `readCount()` mem-`JSON.stringify` cache
**setiap panggilan** (~88 KB × 4 store per request `/rekap`) — biaya V8 yang
tidak dihindari parser on-demand sekalipun. Kandidat perbaikan satu baris
perubahan perilaku: stringify sekali per mutasi cache.

## Keputusan

- `MongoJsonRepository` menyimpan **bytes kanonik** (`_cacheBytes`) hasil
  `JSON.stringify(cache)` sekali, di-invalidate (`null`) pada setiap
  mutasi cache dan dibangun ulang lazy saat dibutuhkan berikutnya.
  `readCount()` jalur ze mengonsumsi bytes itu untuk structural count —
  tidak ada stringify per request pada jalur cache.
- Satu perubahan per eksperimen: kandidat diukur terpisah
  (`...064628/064642-bbee7bf`) terhadap run sebelumnya dalam korpus
  & mesin yang sama.

## Konsekuensi

- **Hasil terukur:** fase D 1.10× → **2.85×** (run utama) + **3.00×**
  (run konfirmasi), p95 2.10×/2.14× — acceptance ≥1.5× tercapai
  (`reports/ondemand-saq-evaluation.md`; arsip record `reports/nd6/`).
- Trade-off: memori menahan bytes kanonik per store (≈ ukuran serialized
  store); invalidation harus benar di setiap jalur mutasi (diuji parity).
- Kandidat hanya menyentuh jalur ze opt-in; baseline V8 tetap identik.
