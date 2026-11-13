# ND-10 — Desain Kontrol Lintas Runtime & Mesin (isolasi variabel)

> Status: **desain, belum dieksekusi**. Revisi AUD-1 2026-11-13 atas keputusan
> pemilik: Node 24 TIDAK dipasang ulang di dev — kontrol runtime mengandalkan
> identitas artefak + histori berlabel, kontrol mesin memakai dev(Node 26) vs
> server(Node 26).

## 1. Latar (fakta terverifikasi)

- Verdict dev 2.85×/3.00× (fase D) direkam pada Node 24.19.0 / V8 13.6
  (`reports/nd6/`, run `...0dcb418`/`...bbee7bf`) — 2026-11-12.
- Verdict server 1.30× (p95 1.46×) direkam pada Node 26.13.0 / V8
  14.6.202.34-node.40 (`reports/nd6-server-phase-matrix.md`) — 2026-11-13,
  root server dirty (exploratory per protokol §3.9).
- Dev kini Node **26.13.1** — string build V8 **identik dengan server**
  (`14.6.202.34-node.40`, diverifikasi `process.versions.v8` kedua mesin).
  Beda: patch Node .0 vs .1, hardware (i5-9400 vs Ryzen 5 5500U), OS build.
- Dua variabel berubah sekaligus antara verdict dev lama dan server →
  penyebab kompresi rasio **belum dapat diklaim** (hukum satu-variabel).

## 2. E1 — Kontrol runtime (dev, satu mesin)

- Jalankan matriks ND-6 4 fase di dev, Node 26.13.1, **tree bersih**
  (gate fail-fast aktif), commit sama dengan era server
  (`ze_json d9e25ac`, `saq-report 8c7f2d4`), korpus byte-exact.
- Prasyarat validitas perbandingan vs histori dev Node 24:
  **wasm byte-identik**. Cek: `artifact_sha256` record baru (field baru
  harness) vs sidecar `out/raw/zuu-2026111206*/metadata.json` era `0dcb418`.
  - Identik → perbandingan dev(Node24)→dev(Node26) = kontrol runtime
    (wasm sama, korpus sama, mesin sama; mesin-state antar-hari = catatan).
  - Tidak identik / sidecar tak terekam → perbandingan dilabel
    **confounded** (ze code ikut berubah); kontrol runtime turun status
    *unknown*; opsi cadangan: Node 24 portable di luar PATH (keputusan
    pemilik, sudah ditolak sementara).
- Keluaran: rasio in-run per runtime + latensi absolut per engine terpisah;
  variasi antar-ronde dilaporkan.

## 3. E2 — Kontrol mesin (dev vs server, runtime setara)

- Re-run matriks ND-6 di `saq_server` **dari tree bersih** (SSH via
  `scripts/ssh-remote/saq-remote.py`; workspace `D:\SKRIPSI\RAFI\sources`) —
  Node 26.13.1; `artifact_sha256` + Node/V8 tercatat; sha256 wasm server
  harus == dev (byte-identik) agar sebanding.
- Bandingkan **rasio in-run** per site (bukan latensi absolut lintas mesin
  seolah satu variabel); hardware/OS/patch-Node = confounder dinyatakan.
- Yang diperbaiki dari batch 11-13: root server harus commit/stash dulu
  (keputusan pemilik) supaya lulus gate; `--allow-dirty` hanya exploratory.

## 4. Matriks interpretasi

| Hasil E1 (dev Node24→26, wasm identik) | Hasil E2 (dev26 vs server26) | Kesimpulan yang sah |
|---|---|---|
| Rasio turun ~1.3× | dev≈server | runtime (V8 14.6) penyebab utama kompresi — klaim kausal pertama yang sah |
| Rasio tetap ~2.8× | server jauh lebih rendah | hardware/OS dominan — klaim kausal lintas mesin masih perlu hati-hati (confounder OS/patch) |
| Campuran | campuran | komponen kombinasi; dekomposisi lanjut = ND-9 |

- Segala angka lintas site tetap **narasi riset**; bukti = rasio in-run
  per run_id (AGENTS §4).

## 5. Yang tidak dilakukan

- Tidak mengubah protokol ND-6 (rounds/warmup/korpus/metrik).
- Tidak menginstal Node 24 (keputusan pemilik); tidak mengubah pointer
  submodule; tidak klaim kausal sebelum E1+E2 tereksekusi.
