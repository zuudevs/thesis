# ADR 0001 — Arah on-demand untuk jalur JSON SAQ

- **Status:** Accepted
- **Tanggal:** 2026-11-12 (audit Stage 1; direktif dieksekusi ND-2…ND-7)
- **Pengambil keputusan:** pemilik skripsi (disetujui), dieksekusi asisten

## Konteks

Server SAQ (`saq-report/`) menanggung jalur JSON panas V8: `express.json()`,
store JSON per-domain (`JsonRepository`/`MongoJsonRepository`), dan
`exportService.js` (`JSON.stringify`). RQ2 menuntut alternatif yang
terukur. Audit arah (`docs/research/audit-2026-11-12.md`, Stage 1/ND-1)
menemukan bahwa parser on-demand C++ (`Document`/`Value`) sudah as-built
sejak P7 (75 gtest, 6 target) namun belum terpapar sebagai API akses selektif
ke Node, dan belum terintegrasi ke call-site nyata SAQ.

## Keputusan

1. Jalur lanjutan = **on-demand/lazy**: tidak ada parser pihak ketiga; ze_json
   memperluas **permukaan JS tanpa mengubah ABI v3** — L1 `ZeParser.lazy()`
   (frame traversal, early-exit) dan L2 `ZeParser.project(shape)`
   (materialisasi subset terpilih satu pass, semantik bentuk V8) — ND-4.
2. Integrasi **read-only, satu call-site dulu** (kesepakatan pemilik):
   `GET /rekap` di saq-report via method repositori baru `readCount()`
   (opt-in env `SAQ_JSON_ENGINE=ze`; baseline V8 `read()` tidak disentuh) —
   ND-5, ADR 0005.
3. Validasi = matriks benchmark 4 fase A–D dengan protokol yang disetujui
   pemilik (ND-6) + laporan evaluasi (ND-7). Acceptance: **≥1.5×** pada jalur
   produksi.
4. Keputusan mekanisme selanjutnya mengikuti data: L2 `project` kalah di
   semua ukuran SAQ (fase B), L1 frame-walk menang terbatas (fase C), jalur
   repositori (fase D) menang setelah kandidat cache-bytes (ADR 0006).

## Konsekuensi

- **Hasil:** verdict 2.85×/3.00× (≥1.5× tercapai) pada `/rekap` cache Mongo
  (2 run independen; p95 2.10×/2.14×) — `reports/ondemand-saq-evaluation.md`.
- **Batas jujur:** workload D literal server utuh belum dijalankan (runner
  site-aware siap; akses server belum ada); file-store fallback 0.91×
  (I/O-bound); L1 masih count-only; angka = dev device.
- Call-site lain (dashboard/enrichment) menyusul setelah benchmark ND-6.
