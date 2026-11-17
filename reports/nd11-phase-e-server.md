# ND-11 — Phase E: HTTP `GET /rekap` end-to-end (server tereksekusi)

Eksekusi: **2026-11-17** di `saq_server` (`server-lanjut`), mode
**koeksistensi penuh** dengan SAQ Production di host yang sama — produksi
tidak disentuh (pid sama, WA/cron aktif), dua instance benchmark membaca
store LIVE yang sama. Laporan pasangan dev:
[`nd11-phase-e-dev.md`](nd11-phase-e-dev.md); hardening + runbook:
[`nd11-coexistence-audit.md`](nd11-coexistence-audit.md); desain:
[`../docs/measurement/nd11-phase-e-http.md`](../docs/measurement/nd11-phase-e-http.md).
Pertanyaan sama seperti dev: **pada boundary byte-identik aplikasi penuh
(middleware → handler 4 repo → render EJS → respons), seberapa besar sisa
keunggulan jalur ze_json?**

## 1. Identitas run

| Sifat | Nilai |
|---|---|
| run_id | `server-lanjut-20261117003513-530f751` |
| root / ze_json / saq-report | `530f751` (harness ter-hardening) / `01a143f` (core 0.3.2, js 0.3.0, abi `2026000302`) / `534d9a8` (knob `SAQ_BIND_HOST`) |
| wasm | `9795f2e8…` **byte-identik dev/server** (Get-FileHash SHA256 kedua site) |
| Runtime | Node 26.13.1 (V8 14.6) — matched dengan dev |
| Site | `saq_server` (i5-9400, 6C/6T) — tree bersih (tracked), gate fail-fast lulus |
| Store | **LIVE** — MongoDB lokal `127.0.0.1:27017/test`, koleksi `json_store` (6 storeKey, counts 1/1/1/1/1/1); URI diberikan via env sesi (`mongodb://127.0.0.1:27017/test`, non-sekret) |
| Instance | 2× `node server.js` localhost: v8 port 3100 · ze (`SAQ_JSON_ENGINE=ze`) port 3101; keduanya `SAQ_DISABLE_WHATSAPP=1` + `SAQ_BIND_HOST=127.0.0.1` |
| Produksi | pid 15640, `node server.js`, listen port 3000 — **tidak disentuh** (`--coexist-prod-port 3000`; guard aktif) |
| Protokol | warmup untimed 3 request/jalur; 15 ronde × 20 request/ronde **TOTAL** (10 v8 + 10 ze); **alternation v8↔ze per-request** (offset rotasi per ronde); tanpa trimming; n=150/engine (300 total) |
| Parity gate | **1 hash unik untuk 300 request** (`a6236b6c…`) — sama dengan hash probe db-match §2 |
| Validator | **PASS**; arsip `reports/nd11/` + exhibit + sidecar `reports/registry/` |

Catatan as-built: percobaan pertama dihentikan harness sendiri di cek
file store (file seed korpus belum ada di server — perilaku sesuai
desain). Diperbaiki dengan menyalin 6 file seed `saq_payload_v1` ke
`saq-report/` (sha256 6/6 == `MANIFEST.json`; gitignored, tree tetap
bersih). File itu **hanya provenance** — sumber data benchmark = Mongo
LIVE (lihat §2).

## 2. Provenance "store LIVE yang dibaca benchmark = store produksi"

Koeksistensi menuntut benchmark membaca DB yang sama dengan produksi
(tanpa menyentuhnya). Bukti berlapis (semua read-only):

1. **Produksi membaca mongo lokal**: 8 koneksi `ESTABLISHED` dari pid
   15640 ke `127.0.0.1:27017` (mongod pid 4760); tidak ada koneksi
   remote lain.
2. **Db = `test`**: satu-satunya db di mongod lokal yang memuat
   `json_store` (6 storeKey). `db=test` juga tempat produksi menulis
   (satu-satunya kandidat; db lain sistem/kecil).
3. **Render identik**: instance probe sementara (port 3102, bind
   loopback, WA off, `MONGO_URL=mongodb://127.0.0.1:27017/test`)
   merender `/rekap` yang **identik teks-per-teks** dengan produksi
   (832 baris sama; beda 821 byte = line-ending template LF (copy
   produksi) vs CRLF (copy benchmark) — bukan data). Hash probe =
   `a6236b6c…` = hash parity run (§1).
4. **Temuan operasional**: di server **tidak ada `.env`**; produksi
   di-start manual pemilik via console (pid dibuat 07:06, parent
   explorer.exe → cmd.exe) dengan URI di env console-nya. Harness
   menerima URI non-sekret yang setara (lokal default `test`) via env
   sesi — nilai asli milik pemilik tidak pernah dibaca/dicetak.
5. **Guard tulis**: preflight counts 6 key = 1 (semua terisi — init()
   benchmark tidak pernah seed); boot log child memuat
   "Loaded 'assistants' from MongoDB" dan **tidak** memuat seed marker;
   abort void aktif; metadata `config.coexistence` terisi di record +
   exhibit.

## 3. Hasil (in-run, satu run_id)

| Jalur | median | p95 | mean | std | cv |
|---|---:|---:|---:|---:|---:|
| `E/rekap/v8` | 5,401 ms | 6,136 ms | 5,463 ms | 0,376 ms | 6,9% |
| `E/rekap/ze` | 4,764 ms | 5,501 ms | 4,871 ms | 0,460 ms | 9,5% |

- **Speedup in-run = 1,13×** (median v8/ze); p95 ratio 1,115×.
- Estimat paired per-ronde (kontrol drift): median rasio **1,133× —
  ze menang 15/15 ronde** (semua ronde; rasio 1,04–1,20).
- cv 6,9%/9,5% — jauh lebih stabil dari dev (27,0%/21,8%): server
  dedicated + tanpa kontensi editor; round medians stabil
  (v8 5,08–5,85; ze 4,61–5,21), tanpa outlier besar (max 8,8 ms).
- Delta median v8−ze = **0,637 ms** → share parser-related ≈ 12% dari
  waktu request (non-parser ≈ 88%, floor ze ≈ 4,8 ms = middleware +
  EJS + serialisasi). Bandingkan dev: delta 0,162 ms ≈ 4% share.

## 4. Verdict — jawaban RQ pada boundary aplikasi (site server)

1. **Pada endpoint `/rekap` end-to-end di server, keunggulan parser
   1,13× (ze menang 15/15 ronde)** — dari fase D server 2,67×
   (lapisan repository) terkompresi ~2,4× saat seluruh jalur HTTP
   dibayar. Pola kompresi konsisten dengan dev (2,88× → 1,08×,
   ~2,7×).
2. **Share parser lebih besar di server** (≈12% vs ≈4% di dev) —
   konsisten ND-9/ND-13 (share scan/match server lebih besar); koeksistensi
   produksi yang nyaris idle (CPU produksi +0,3 s selama jendela
   monitoring) membuat sinyal bersih.
3. **Lintas-site (dev 1,04×/1,08× vs server 1,13×) = narasi riset,
   bukan bukti** — mesin + hash root + kondisi host berbeda (aturan
   AGENTS §4). Bukti = rasio in-run satu run_id per site.
4. Tidak ada gate numerik khusus Phase E (§3 desain: E < D diantisipasi);
   temuan = arah + magnitudo + komposisi biaya, bukan acceptance 1,5×
   (itu gate fase D — tercapai di kedua site).
5. Angka absolut lintas mesin (server 5,4 ms vs dev 4,1 ms) = narasi
   (hardware/OS confounder dinyatakan; runtime Node 26 matched).

## 5. Acceptance criteria (audit §5) — bukti per butir

- [x] **Production tidak restart** — pid 15640 identik di 36 snapshot
      monitoring (2 jendela × ~5 s, 07:33:56–07:37:04) dan post-check.
- [x] **WA Production authenticated/ready** — `GET /whatsapp/status`
      (read-only diagnostics): `status=ready, hasQR=false`;
      `chrome_procs=9` utuh; `.wwebjs_auth` hanya disentuh produksi
      (children WA off — boot log "📴 WhatsApp/cron boot dimatikan").
- [x] **Cron Production tidak berubah** — produksi tidak pernah
      di-spawn/di-signal; cron hanya dimatikan di child benchmark.
- [x] **Port tidak bentrok** — preflight: 3000 (produksi) vs 3100/3101
      (benchmark), lulus sebelum spawn.
- [x] **Dua instance benchmark teridentifikasi** — health = HTTP 200 +
      boot-marker child (`waitHealthy` ter-hardening; boot v8 1,89 s,
      ze 0,07 s).
- [x] **Tidak ada request ke endpoint mutasi** — protokol hanya
      `GET /rekap` (300 request; harness tidak punya jalur lain).
- [x] **Tidak ada mutasi DB tak terduga** — counts `json_store` pre =
      post = 1 semua (preflight + post-check read-only); boot log tanpa
      seed marker.
- [x] **Parity gate PASS** — 1 hash / 300 request (`a6236b6c…`).
- [x] **Validator PASS + sidecar + metadata coexistence** — record PASS;
      `reports/registry/server-lanjut-20261117003513-530f751.json`;
      `config.coexistence` + `mongo_json_store_counts` di exhibit.
- [x] **Hanya child benchmark yang dihentikan** — harness killChildren;
      pasca-run port 3100/3101 kosong (monitor), produksi tetap listen
      3000.
- [x] **Production sehat setelah eksperimen** — `/rekap` produksi 200
      pada SEMUA snapshot (termasuk saat run: `bench_listen=[3100,3101]`
      dengan `rekap=200`); RAM ≤78,5% (ambang abort 90%); WA ready.

Jendela run ≈ 10 s (07:35:13 run_id → 07:35:22 port benchmark sudah
kosong); produksi nyaris tak terdampak (CPU 5,4 → 5,7 CPU-s total).

## 6. Deliverables & kebersihan

- Harness `scripts/bench/nd11_phase_e.mjs` @ `530f751` (tanpa perubahan
  kode untuk run server — hardening sudah merged di PR #76).
- Helper server reusable di-commit: `scripts/ssh-remote/nd11/`
  (`nd11_monitor.ps1` — snapshot produksi selama run; `nd11_json_store_counts.cjs`
  — counts read-only; `nd11_seed_copy.ps1` — copy seed korpus + sha).
  Script investigasi sekali-pakai (envprobe/conn/dbmatch/bodysave) = throwaway `out/`.
- Arsip: record + exhibit `reports/nd11/` (+ sidecar `reports/registry/`).
- Server: file sementara HOME dihapus pasca-run; 6 file seed tetap di
  `saq-report/` (gitignored, provenance sha256 tercatat di record).
- @cite: `10.1002_spe.3313` (boundary + provenance; rationale per-result
  di record).

## 7. Lanjutan

- Opsional (keputusan pemilik): boundary berat `/rekap/asisten`
  (read+enrich penuh) — di server share parser ≈12% bisa naik saat
  decode per-item dominan; protokol + guard identik.
- Angka ini masuk narasi Bab 4 (E vs D per site; kompresi non-parser),
  bukan pengganti fase D.
