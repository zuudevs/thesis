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
| Protokol | warmup untimed 3 request/jalur; 15 ronde × 20 request/ronde **TOTAL** (10 v8 + 10 ze — field record `reps_per_round=20` berarti total lintas engine, bukan per engine); **alternation v8↔ze per-request** (offset rotasi per ronde, `(r+k)%2`); tanpa trimming; n=150/engine (300 total); latensi = `performance.now()` di sekitar `fetch` (load generator di mesin yang sama, localhost) |
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

- **Server run (saq_server)**: skrip identik, store LIVE, **arsitektur
  koeksistensi** hasil audit 2026-11-17 — SAQ Production utuh di host
  yang sama (WA + cron AKTIF, tidak disentuh); dua instance benchmark
  nonaktif WA/cron + bind 127.0.0.1 (`--coexist-prod-port`); lihat
  `reports/nd11-coexistence-audit.md`.
- Opsional (keputusan pemilik): boundary lebih berat (`/rekap/asisten`,
  read+enrich penuh) untuk mengukur apakah keunggulan count-only
  bertahan saat decode per-item dominan.

## 6. Re-run pasca-hardening (2026-11-17)

Run penuh kedua di dev dengan harness ter-hardening hasil audit
ND-11.a (`reports/nd11-coexistence-audit.md`): preflight port wajib
kosong, health = HTTP 200 + boot-marker child, abort void saat
child-exit, metadata `config.coexistence`. **Protokol ukur tidak
berubah** — tujuan run: memverifikasi bahwa hardening tidak menggeser
protokol dan mengonfirmasi arah temuan §2 dengan harness yang kini
aman untuk koeksistensi dengan SAQ Production.

| Sifat | Nilai |
|---|---|
| run_id | `zuu-20261117000112-6979e3f` |
| root / ze_json / saq-report | `6979e3f` / `01a143f` (core 0.3.2, js 0.3.0, abi `2026000302` — identik run pertama) / `534d9a8` (knob `SAQ_BIND_HOST`, PR #6) |
| Mode | normal — **tanpa** `--coexist-prod-port` (di dev tidak ada SAQ Production berjalan; metadata jujur: `production_same_host=false`, write guard off) |
| Port | 3100 (v8) / 3101 (ze) — preflight wajib-kosong lulus sebelum spawn |
| Protokol | identik §1: warmup untimed 3, 15 ronde × 20 request/ronde TOTAL (10 v8 + 10 ze), alternation per-request, tanpa trimming, n=150/engine (300 total) |
| Parity gate | 1 hash unik untuk 300 request (`a18c7b4a…` — sama dengan run pertama; store identik) |
| Validator | **PASS**; arsip `reports/nd11/` + sidecar `reports/registry/zuu-20261117000112-6979e3f.json` |

| Jalur | median | p95 | mean | std | cv |
|---|---:|---:|---:|---:|---:|
| `E/rekap/v8` | 4,146 ms | 6,504 ms | 4,508 ms | 1,217 ms | 27,0% |
| `E/rekap/ze` | 3,984 ms | 5,976 ms | 4,243 ms | 0,925 ms | 21,8% |

- **Speedup in-run = 1,04×** (median v8/ze); estimat paired per-ronde:
  median rasio **1,029×**, ze menang 10/15 ronde — arah konsisten §2.
- cv lebih tinggi dari run pertama (27,0%/21,8% vs 18,4%/19,5%) — ada
  satu outlier v8 13,2 ms (laptop, background aktif); median + paired
  per-ronde menahan dampaknya, parity & protokol utuh.
- **Lintas-run (1,08× vs 1,04×) = narasi riset, bukan bukti** — hash
  root berbeda (harness berubah; aturan AGENTS §4: dilarang
  membandingkan lintas git-hash). Yang konsisten lintas run: arah
  keunggulan ze kecil (~4–8%) pada boundary HTTP penuh, non-parser
  ~95% waktu request.
- Verifikasi guard tampak di exhibit: boot log child memuat
  "📴 WhatsApp/cron boot dimatikan (SAQ_DISABLE_WHATSAPP=1)"; boot
  v8 3,78 s vs ze 0,04 s; port 3100/3101 bersih pasca-run (0
  listener — shutdown bersih).