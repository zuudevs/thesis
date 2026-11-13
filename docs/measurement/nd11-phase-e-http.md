# ND-11 — Desain Phase E: HTTP `/rekap` End-to-End (eksperimen TERPISAH)

> Status: **desain, belum dieksekusi**. Phase E adalah satu-satunya dasar
> sah untuk klaim "berhasil pada endpoint produksi" — Phase D ND-6 mengukur
> lapisan repository (lihat errata di plan doc §2 dan AGENTS §6).

## 1. Boundary yang diukur

Request HTTP `GET /rekap` penuh pada aplikasi Express saq-report:
middleware chain (termasuk static/auth bila aktif) → routing → handler
(`routes/rekapRoutes.js` L25–47) → 4 repo call (`readCount()`/`read().length`)
→ **render EJS** (`res.render('rekap-pilihan')`) → serialisasi respons.
Bagian yang TIDAK termasuk: database eksternal (store lokal SAQ), browser.

## 2. Prasyarat

- Server SAQ: workspace `D:\SKRIPSI\RAFI\sources` tree bersih (gate),
  `npm install --ignore-scripts` di `saq-report/` (runbook §fase D).
- Dua instance aplikasi di mesin server (localhost — jaringan bukan
  variabel): `SAQ_JSON_ENGINE=ze` (port A) dan default V8 (port B), kode
  + data store identik, boot berurutan, health-check sebelum ukur.
- Load generator = runner Node lokal di mesin server (bukan dari dev —
  latensi jaringan tidak masuk angka).

## 3. Protokol (mengikuti §3 plan doc, tanpa mengubah definisi metrik)

- 15 ronde, warmup 3 request/jalur, **alternating** v8↔ze per ronde,
  tanpa trimming, GC tidak berlaku lintas proses (catat saja).
- Satu `run_id` untuk pasangan v8↔ze (rasio dalam satu run_id).
- Metrik per request: latensi (median, P95, mean, stddev) per engine;
  sampling di sisi generator (`performance.now` sekitar `fetch`).
- **Parity**: body HTML `/rekap` kedua engine harus byte-identik (stats
  sama dari parity gate ND-5; template sama) — diverifikasi per ronde;
  mismatch = run void.
- Record: schema v1.0.0; `results[].engine` = `v8` / `wasm64_cabi`;
  `rationale` + `@cite` (10.1002_spe.3313); metadata lengkap + `artifact_sha256`
  wasm yang dipakai instance ze; `config` mencatat data store LIVE (bukan
  korpus `saq_payload_v1` — provenance store: sha256 per file store saat run).

## 4. Interpretasi & batas

- Fase E menjawab RQ3/H4 pada boundary aplikasi penuh; angka E **tidak
  boleh digabung/dibandingkan langsung** dengan angka D (boundary beda) —
  dilaporkan berdampingan sebagai dua level pengukuran.
- Bila E < D ratio: biaya non-parser (middleware/render/HTTP) menutupi
  parser — temuan sah dan justru menjawab "pada kondisi apa manfaat
  muncul/hilang" (RQ utama).
- Tidak ada perubahan kode aplikasi; engine toggle = env yang sudah ada
  (`SAQ_JSON_ENGINE`), baseline V8 tidak diubah.

## 5. Yang tidak dilakukan

- Tidak mengubah handler/route/template; tidak menambah cache baru;
  tidak menjalankan E sebelum re-run bersih D server (urutan prioritas:
  server bersih dulu → dev Node 26 → ND-9 → E).
