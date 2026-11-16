# ND-11 — Phase E: HTTP `GET /rekap` end-to-end (dev tereksekusi)

Eksekusi: 2026-11-16 di `dev_device` (implementasi + pengukuran penuh),
atas rencana "implementasi di device dulu, server menyusul". Desain:
[`docs/measurement/nd11-phase-e-http.md`](../docs/measurement/nd11-phase-e-http.md).
Pertanyaan: **pada boundary byte-identik aplikasi penuh (middleware →
handler 4 repo → render EJS → respons), seberapa besar sisa keunggulan
jalur ze_json?** — fase D ND-6 mengukur lapisan repository; Phase E
mengukur apa yang benar-benar ditanggung endpoint.

## 1. Identitas run

| Sifat | Nilai |
|---|---|
| run_id | `zuu-20261116101458-8556513` |
| root / ze_json / saq-report | `8556513` / `01a143f` (core 0.3.2, js 0.3.0, abi `2026000302`) / `501cc03` |
| wasm | `9795f2e8…` (byte-identik sesi server terpadu; sidecar `reports/registry/`) |
| Runtime | Node 26.13.1 (V8 14.6.202.34-node.40) |
| Site | `dev_device` (ZenBook UX425UAZ) — tree bersih (tracked), gate fail-fast lulus |
| Korpus/store | `saq_payload_v1-live-store`: 6 file store anonim di-copy ke `saq-report/` (semua path gitignored), sha256 per file di `extras.store_sha256` record + exhibit |
| Instance | 2× `node server.js` di localhost: v8 (`SAQ_JSON_ENGINE` kosong) port 3000 · ze (`SAQ_JSON_ENGINE=ze`) port 3001; `SAQ_DISABLE_WHATSAPP=1` di keduanya (saq-report PR #5 — boot WA/cron dimatikan, **handler/route/template tidak diubah**) |
| Protokol | warmup untimed 3 request/jalur; 15 ronde × 20 request per engine; **alternation v8↔ze per-request** (offset rotasi per ronde); tanpa trimming; n=150/engine; latensi = `performance.now()` di sekitar `fetch` (load generator di mesin yang sama, localhost) |
| Parity gate | seluruh respons harus byte-identik: **1 hash unik untuk 300 request** (`a18c7b4a…`) — mismatch = run void. Pilot (2 ronde × 3) hash identik dengan run penuh. |
| Validator | **PASS** (`out/measurements/…-nd11-phase-e-dev_device.record.json`); arsip `reports/nd11/` + exhibit `reports/nd11/raw/` |

## 2. Hasil (in-run, satu run_id)

| Jalur | median | p95 | mean | std | cv |
|---|---:|---:|---:|---:|---:|
| `E/rekap/v8` | 4,397 ms | 6,216 ms | 4,555 ms | 0,834 ms | 18,4% |
| `E/rekap/ze` | 4,085 ms | 6,005 ms | 4,321 ms | 0,839 ms | 19,5% |

- **Speedup in-run = 1,08×** (median v8/ze); p95 ratio 1,035×.
- Estimat paired per-ronde (kontrol drift mesin): median rasio 1,048×,
  ze menang 9/15 ronde — arah konsisten, magnitudo kecil.
- Delta median v8−ze = **0,311 ms**; sisa ~4,0 ms per request = Express
  middleware + EJS render + serialisasi respons (non-parser) — konsisten
  dengan fase D (repo-layer dev: v8 0,215 ms vs ze 0,081 ms, delta
  0,134 ms) + noise.

## 3. Verdict — jawaban RQ pada boundary aplikasi

1. **Pada endpoint `/rekap` end-to-end, keunggulan parser terkompresi
   ~1,05–1,08×** — dari 2,88×/2,67× (fase D, lapisan repository) menjadi
   ≈1,08× saat seluruh jalur HTTP dibayar. Non-parser (~95% waktu request)
   mendominasi: middleware Express, render EJS, serialisasi.
2. **Temuan yang diantisipasi desain §4 terjadi**: E < D ratio — biaya
   non-parser menutupi perbaikan parser. Temuan sah dan menjawab RQ:
   manfaat lazy parsing muncul pada **jalur count/read-only berbobot
   parser** (repository/cache), bukan pada endpoint render-penuh.
3. Batas: cv ~19% (laptop, editor + Chrome pemilik aktif saat ukur —
   kondisi dinyatakan; mitigasi = alternation per-request + paired
   per-ronde); **satu run** (konfirmasi independen menyusul di server);
   store dev = korpus anonim (server = LIVE store — jangan bandingkan
   lintas site); boot WA/cron dimatikan (dinyatakan; instance identik
   kecuali engine toggle).

## 4. Deliverables

- Harness `scripts/bench/nd11_phase_e.mjs` (root) + boot gate
  `SAQ_DISABLE_WHATSAPP` (saq-report PR #5) — keduanya via PR
  (root PR #73, saq-report PR #5).
- Laporan ini + arsip record/exhibit `reports/nd11/` + sidecar registry.
- As-built tercatat di `docs/measurement/nd11-phase-e-http.md` §6;
  sinkronisasi `tasks.md`/`plans.md`/`CHANGELOG.md`.
- @cite: `10.1002_spe.3313` (provenance + pertanyaan boundary; rationale
  per-result di record).

## 5. Lanjutan

- **Server run (saq_server)**: skrip identik, store LIVE, boot apa adanya
  (`SAQ_DISABLE_WHATSAPP` tidak berlaku — WA aktif sebagai kondisi
  produksi, dinyatakan di laporan); urutan sesuai ND-11 §5.
- Opsional (keputusan pemilik): boundary lebih berat (`/rekap/asisten`,
  read+enrich penuh) untuk mengukur apakah keunggulan count-only
  bertahan saat decode per-item dominan.