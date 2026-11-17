# ND-11 — Audit koeksistensi benchmark dengan SAQ Production (2026-11-17)

Audit read-only atas desain "dua instance benchmark berjalan berdampingan
dengan SAQ Production di host yang sama" sebelum eksekusi server run.
Basis: source code aktual (bukan dokumentasi) — harness
`scripts/bench/nd11_phase_e.mjs` @ `fix/bench-nd11-coexist`, saq-report
`501cc03` (+ knob `0a62581`), ze_json `01a143f`, root `b6ae287` (pasca
PR #75). Metode: baca seluruh file yang benar-benar dieksekusi
(harness, `server.js`, `config/*`, `repositories/*`, `routes/*`,
`services/whatsapp/*`, `services/cronService.js`, `models/JsonStore.js`,
`package.json`, `.gitignore`, schema validator) + inventaris endpoint
mutasi. Tidak ada benchmark dijalankan selama audit; tidak ada perubahan
produksi.

## 1. Executive verdict

**SAFE WITH CHANGES** — desain koeksistensi sah (boot gate terbukti
mematikan puppeteer + cron hanya di child benchmark; `GET /rekap`
read-only murni), tetapi 4 temuan harus ditangani dulu:

1. **R1 (Critical)** — `waitHealthy` lama menerima respons HTTP **apa
   pun** (status tidak diperiksa, `nd11_phase_e.mjs` lama L166-168).
   Port bentrok dengan produksi → harness mengukur **produksi**;
   parity bisa "PASS" karena kedua port menunjuk server yang sama.
2. **R2 (Critical)** — tidak ada preflight port; default CLI 3000
   berpotensi = port produksi; `EADDRINUSE` tertelan
   `uncaughtException` yang tidak exit (`server.js` L106-109) → child
   zombie non-listening.
3. **R3 (Critical)** — `server.listen(PORT)` tanpa host = 0.0.0.0
   (`server.js` L116): instance benchmark exposed LAN dengan 20
   endpoint mutasi (7 file routes: jadwal/dosen/asisten/matakuliah/
   laporan/whatsapp/setting) yang menulis ke **DB produksi bersama**,
   plus `express.static(PATHS.ROOT)` (L69) mengekspos `.env` via HTTP,
   plus `POST /whatsapp/restart` → `restartClient()` →
   `initializeClient()` (`whatsappClient.js` L423-431) = lazy-init WA
   yang **tidak ter-coverage boot gate** (LocalAuth `dataPath`
   `.wwebjs_auth` bersama produksi, L13-14/L286-289).
4. **R4 (High)** — `MongoJsonRepository.init()` melakukan **seed +
   upsert ke `json_store`** bila storeKey kosong (L75-83): benchmark
   bisa menulis ke DB produksi bila ada koleksi kosong.

Temuan lain: R6 kematian child tidak terdeteksi instan (Medium);
R7 kontensi CPU/RAM host selama ~30 dtk run (Medium — mitigasi
prosedural); R8 snapshot divergen antara dua init → parity void
(perilaku aman, Low); R9 index init idempotent (Low); R10 dir
upload/export shared — tidak tersentuh harness (Low); R11 env
harness menang atas `.env` (dotenv v17 non-override, terverifikasi
`package.json` L21 + `server.js` L17) (Informational).

## 2. Desain yang disetujui

| Instance | Port | Engine | WhatsApp/cron | Bind |
|---|---:|---|---|---|
| SAQ Production | port produksi (di-discover, jangan diasumsikan) | produksi | AKTIF (tidak disentuh) | eksisting |
| Benchmark V8 | 3100 (contoh) | V8 baseline | nonaktif (`SAQ_DISABLE_WHATSAPP=1`) | 127.0.0.1 |
| Benchmark ze | 3101 (contoh) | `SAQ_JSON_ENGINE=ze` | nonaktif (sama) | 127.0.0.1 |

Controller = harness: spawn 2 child → preflight → health (200 + marker
child) → warmup untimed → 15 ronde × 20 request/ronde TOTAL (10 v8 + 10
ze) alternation per-request → parity byte-identical → record → kill **hanya** child.
Produksi tidak pernah dihentikan/diubah; benchmark membaca DB produksi
yang sama (LIVE store) secara read-only.

## 3. Perubahan minimum (diterapkan di PR ini)

| # | File | Perubahan | Bukti risiko |
|---|---|---|---|
| E1 | `scripts/bench/nd11_phase_e.mjs` | preflight port wajib kosong sebelum spawn; health = HTTP 200 **dan** marker `Server berjalan di http://localhost:<port>` di stdout **child kita**; child exit saat warmup/ukur = abort void instan | R1, R2, R6 |
| E2 | `scripts/bench/nd11_phase_e.mjs` | mode koeksistensi (`--coexist-prod-port`): preflight count `json_store` per storeKey (read-only, via node_modules saq-report) + boot-log seed guard → void/REFUSED | R4 |
| E3 | `saq-report/server.js` | knob `SAQ_BIND_HOST` (env-absen = perilaku eksisting); harness set `127.0.0.1` pada kedua child | R3, R5 |
| E4 | `scripts/bench/nd11_phase_e.mjs` | metadata `config.coexistence` di record (production_same_host/port/untouched, wa/cron aktif, bind host, seed guard) + exhibit | provenance |
| E5 | docs | koreksi kalimat "boot apa adanya" (design doc §6, laporan dev §5, plans/tasks) + laporan ini | dokumentasi vs source |

Tidak ada refactoring lain: handler/route/template/repository read-path/
parity gate/schema record tidak diubah. Opsional yang sengaja TIDAK
dilakukan: env `SAQ_DISABLE_SEED` (guard deteksi + preflight sudah
menutup; menghindari perubahan perilaku app tambahan).

## 4. Runbook eksekusi server (ringkas — Windows, verifikasi per langkah)

1. **Preflight produksi** (read-only): `Get-Process node`;
   `Get-NetTCPConnection -State Listen | Where-Object { $_.OwningProcess -in
   (Get-Process node).Id }` → port produksi; `curl.exe -s -o NUL -w
   "%{http_code}" http://127.0.0.1:<PORT>/rekap` = 200; inventaris **nama**
   variabel `.env` produksi (nilai tidak dicetak).
2. **Port check**: `Get-NetTCPConnection -State Listen -LocalPort 3100,3101`
   harus kosong.
3. **Environment**: tanpa mengubah `.env` produksi; pin submodule = commit
   merged; 6 file store ada di `saq-report/` (harness wajib, provenance
   sha256 per file).
4. **Start**: `node scripts/bench/nd11_phase_e.mjs --rounds 15 --per-round 20
   --warmup 3 --site saq_server --v8-port 3100 --ze-port 3101
   --coexist-prod-port <PORT_PRODUKSI>` (preflight counts + seed guard aktif
   otomatis; child bind loopback).
5. **Monitoring produksi** tiap ~5 dtk selama run (~30 dtk): CPU/WS PID
   produksi + `GET /rekap` produksi tetap 200. **Abort**: produksi bukan
   200 / CPU naik tajam / RAM host > 90% → `Stop-Process -Id <PID_CONTROLLER>`
   (exit handler harness membunuh child-nya).
6. **Validasi output**: validator PASS; exhibit `parity.void=false`; log boot
   memuat `📴 WhatsApp/cron boot dimatikan` dan TIDAK memuat
   `[MongoDB] Seed '`; `config.coexistence` terisi.
7. **Shutdown**: otomatis oleh harness; verifikasi 3100/3101 kosong +
   tidak ada chrome `*wwebjs*`.
8. **Post-run produksi**: `GET /rekap` 200; PID produksi sama (tidak restart);
   WA ready; cron tidak berubah.

## 5. Acceptance criteria

Hasil verifikasi run 2026-11-17 (`server-lanjut-20261117003513-530f751`)
— semua butir lulus dengan bukti per butir di
[`reports/nd11-phase-e-server.md`](../reports/nd11-phase-e-server.md) §5
(pid produksi 15640 utuh; WA `ready`; counts pre=post; parity 1
hash/300; validator PASS; port bersih pasca-run). Checklist asli:

- [x] Production tidak restart (PID sama pre/post)
- [x] WA Production authenticated/ready; `.wwebjs_auth` hanya disentuh produksi
- [x] Cron Production tidak berubah
- [x] Port tidak bentrok (preflight lulus)
- [x] Dua benchmark instance teridentifikasi via marker boot-log child + 200
- [x] Tidak ada request benchmark ke endpoint mutasi (hanya `GET /rekap`)
- [x] Tidak ada mutasi DB tak terduga (count `json_store` pre = post;
      boot log tanpa seed marker)
- [x] Parity gate PASS (1 hash / 300 request)
- [x] Validator record PASS + sidecar registry + metadata coexistence
- [x] Hanya child benchmark yang dihentikan
- [x] Production sehat setelah eksperimen

## 6. Batas metodologi (dinyatakan)

Ko-tenansi produksi = confounder **angka absolut** server (traffic produksi
variabel); **rasio in-run v8↔ze** (satu run_id, alternation per-request,
paired per-ronde) tetap bukti primer. dev-vs-server = narasi riset, bukan
bukti (aturan AGENTS §4). HTTP end-to-end ≠ repository-level (fase D) —
tidak saling digantikan. Store LIVE (server) ≠ korpus anonim (dev) —
dilarang membandingkan lintas site.
