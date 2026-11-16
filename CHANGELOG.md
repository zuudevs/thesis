# Changelog - Workspace Skripsi v5

Riwayat perubahan workspace thesis (root `v5`). Entri berbasis tanggal -
workspace ini bukan paket yang dirilis; versi dari artefak terkait
(`ze_json` 0.1.x, npm `@zuudevs/ze-json`) tercatat di changelog masing-masing
repo. Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 2026-11-17 - ND-11.a: audit koeksistensi + hardening harness

### Added

- `reports/nd11-coexistence-audit.md` — audit read-only (verdict **SAFE
  WITH CHANGES**) untuk menjalankan dua instance benchmark ND-11
  berdampingan dengan SAQ Production di host yang sama: 4 temuan
  berbasis source code (health-check menerima status HTTP apa pun;
  tanpa preflight port; bind 0.0.0.0 dengan endpoint mutasi +
  `express.static(ROOT)` + lazy-init WA via `POST /whatsapp/restart`;
  seed-on-empty `MongoJsonRepository.init()` menulis ke DB produksi),
  risk register file:line, runbook server, acceptance criteria.
- Harness `scripts/bench/nd11_phase_e.mjs`: preflight port wajib
  kosong sebelum spawn; health = HTTP 200 **dan** boot-marker
  `Server berjalan di http://localhost:<port>` di stdout **child
  kita** (identitas terikat proses, bukan port); abort void instan
  saat child exit; mode koeksistensi `--coexist-prod-port` → preflight
  count `json_store` (read-only) + boot-log seed guard (benchmark
  tidak boleh memicu seed ke DB produksi); metadata
  `config.coexistence` di record + exhibit; kedua child bind
  127.0.0.1.

### Changed

- `saq-report` — knob boot-level `SAQ_BIND_HOST`
  (`server.listen(PORT, env || undefined)`, env-absen = perilaku
  eksisting); pin `0a62581` (PR saq-report).
- Koreksi dokumen yang bertentangan dengan implementasi: kalimat
  "boot apa adanya" pada design doc §6 / laporan dev §5 / plans /
  tasks → arsitektur koeksistensi (produksi utuh, gate pada instance
  benchmark).

### Notes

- Tidak menyentuh handler/route/template/repository read-path/parity
  gate/schema record; knob `SAQ_BIND_HOST` satu kelas dengan gate
  `SAQ_DISABLE_WHATSAPP` (PR saq-report #5) — perilaku produksi tidak
  berubah.

## 2026-11-16 - Sesi server terpadu: ND-13 probe + matriks ND-14 di saq_server

### Added

- 5 record `saq_server` PASS validator + raw exhibit: probe ND-13
  (`server-lanjut-20261116060747-8a1324b`) + fase A–D ND-6
  (`…060843/060900/060915/060933-8a1324b`) — root `8a1324b`, ze_json
  `01a143f` (core 0.3.2, abi `2026000302`), wasm `9795f2e8…`
  **byte-identik** dev/server (scp + sidecar + gate
  `build-wasm.ps1 -VerifyOnly` 26 ekspor v5), Node 26.13.1, tree bersih.
  Arsip `reports/nd14/` (4 record) + `reports/nd13/` (probe) + sidecar
  `reports/registry/` (5 run).
- Addendum laporan: `reports/nd14-post-o2-matrix.md` §8 (panel server) +
  `reports/nd13-open-decomposition.md` §5 (hasil dekomposisi server).

### Changed

- Chart `post-o2` regenerated dengan panel server terisi
  (`nd6_summary_chart.py`: `RUNS_POST_O2` + label/judul/footnote; arsip
  `reports/charts/`); CSV `out/charts/data/post-o2-*.csv`.
- Sinkronisasi `docs/project/tasks.md` (ND-13, ND-14, O2-1 follow-up) +
  `docs/project/plans.md` (P8-3).

### Verdict

- **Fase D mongo-cache ≥ 1,5× DI KEDUA SITE** — dev 2,88× (p95 3,25×) ·
  server **2,67×** (p95 2,49×); file-store 0,99× (I/O-bound); fase C
  server kini menang schedules 1,50× + assistants 1,42× (era ND-12:
  kalah semua). Fase A/B tetap <1× (konsisten).
- Pertanyaan terbuka ND-9 terjawab: gap open di server menempel di
  scan **dan** match (scan 73–82% dominan; share match server
  17,5–23,6% vs dev 7–15%) → kandidat O2 pass pairing berlaku kedua site.
- Sisa terbuka: ND-11 (Phase E HTTP end-to-end) — prasyarat "server
  bersih D dulu" kini terpenuhi.

## 2026-11-16 - ND-11 Phase E (HTTP end-to-end) di dev + sinkronisasi laporan

### Added

- Harness `scripts/bench/nd11_phase_e.mjs` (root) — ukur `GET /rekap`
  **end-to-end**: 2 instance aplikasi di localhost (v8 vs
  `SAQ_JSON_ENGINE=ze`, kode+store identik, toggle engine saja),
  warmup untimed, 15 ronde × 20 request/engine dengan alternation
  per-request, tanpa trimming; parity gate byte-identical (1 hash unik
  untuk 300 request — mismatch = run void); record schema v1.0.0 +
  exhibit per-request. As-built dev di `docs/measurement/nd11-phase-e-http.md` §6.
- Boot gate `SAQ_DISABLE_WHATSAPP=1` di `saq-report` (PR saq-report #5
  → `501cc03`) — puppeteer WA + cron reminder dimatikan saat pengukuran;
  handler/route/template aplikasi tidak diubah.
- Laporan [`reports/nd11-phase-e-dev.md`](reports/nd11-phase-e-dev.md) +
  arsip record/exhibit `reports/nd11/` + sidecar `reports/registry/`.
- Sinkronisasi laporan: `reports/README.md` indeks (ND-13/ND-14/O2-1/O2-2
  + catatan tautan ND-7/ND-8), klaim "pending" di O2-1/O2-2/ND-14
  diganti pointer sesi server terpadu (PR #72).

### Changed

- Submodule `saq-report` `8c7f2d4` → `501cc03` (root PR #73).
- `chore`: ignore `dashboard/` scratch dir (PR #74) — syarat tree bersih
  untuk acceptance run.

### Verdict

- **Phase E dev: speedup in-run 1,08×** (median v8 4,397 ms vs ze 4,085
  ms; p95 1,035×; paired per-ronde 1,048×) — non-parser ~95% waktu
  request → keunggulan parser terkompresi dari 2,88×/2,67× (fase D) di
  endpoint render-penuh; parity byte-identical 300 request. Temuan
  menjawab RQ: manfaat muncul di jalur count/read-only, bukan endpoint
  penuh. Sisa: server run (store LIVE, boot apa adanya) + opsional
  boundary berat (`/rekap/asisten`).

## 2026-11-13 - AUD-1: audit artefak & protokol ND-6

Audit berbasis source + re-validasi dari file (bukan ringkasan). Tidak ada
angka benchmark baru; eksekusi ukur berikutnya menunggu tree bersih.

### Added

- Laporan [`reports/nd6-audit-2026-11-13.md`](reports/nd6-audit-2026-11-13.md):
  klasifikasi Verified/Reported/Unknown (58/58 record PASS — 52 server +
  6 dev; korpus identik lintas situs; tidak ada hash wasm terekam di
  artefak era manapun).
- Arsip verbatim `reports/nd6/server-lanjut-20261111/` (36) +
  `server-lanjut-20261113/` (16).
- Desain eksperimen: `docs/measurement/nd9-parser-cost-diagnosis.md`,
  `nd10-site-runtime-control.md`, `nd11-phase-e-http.md`.
- `scripts/bench/nd6_protocol.mjs` (+ unit test 5/5): helper protokol
  murni — filename site-aware, gate clean-tree, sha256 wasm.

### Changed

- **Errata dokumen**: hitungan record server = 52 (bukan 54) dan batch
  11-13 = 16 (bukan "10/10") — `tasks.md` (ND-7/ND-8), `reports/nd6-server-phase-matrix.md`;
  fase D = lapisan repository, bukan HTTP `/rekap` end-to-end —
  `tasks.md`, `docs/adr/0001`, `reports/ondemand-saq-evaluation.md` §8,
  `docs/measurement/nd6-benchmark-plan.md` §2, AGENTS §6; status akses
  server "belum tersedia" → tereksekusi (plans ×4, tasks, plan doc).
- `scripts/bench/nd6_bench.mjs`: gate fail-fast clean-tree (exit 3,
  teruji hidup) + `--allow-dirty` → `config.exploratory`, `artifact_sha256`
  wasm, metadata artifact/gate.
- `scripts/node-benchmark/harness.mjs`: `library.version` = identitas
  baseline (`node-builtin (saq-report@<hash>)`), bukan versi runtime.
- `schemas/measurement.schema.json`: field opsional
  `library.artifact_sha256` + `config.exploratory`.
- `scripts/ssh-remote-saq/ssh-remote.py`: rewrite CLI non-interaktif
  (run/push/pull/smoke; smoke exit 0, scp roundtrip byte-identik);
  `.env` di-gitignore.

## 2026-11-13 — ND-8: matriks ND-6 di server SAQ

Eksekusi pemilik di `site=saq_server` (Node 26/V8 14.6, korpus byte-exact);
10 record PASS validator.

### Added

- Laporan [`reports/nd6-server-phase-matrix.md`](reports/nd6-server-phase-matrix.md):
  **acceptance ≥1.5× tidak tercapai di server** — fase D produksi 1.30×
  (p95 1.46×) vs verdict dev 2.85×/3.00×; dekomposisi komponen + kandidat
  perbaikan (plan doc §7).

### Changed

- `docs/measurement/nd6-benchmark-plan.md`: seksi §11 (hasil saq_server) +
  pointer di limitasi #4 §10; ND-7 report addendum per-site; ledger **ND-8**.
- `scripts/bench/nd6_bench.mjs`: nama file record memakai `--site`
  aktual (sebelumnya hardcode `-dev_device`).

## 2026-11-12 — Overhaul arsitektur dokumentasi (PW-4)

Direktif on-demand 7 stage (ND-1…ND-7) selesai pada main `3947bcd` (verdict
2.85×/3.00×); overhaul dokumentasi menyusul.

### Changed

- **Migrasi riil** `PLANS.md` → [`docs/project/plans.md`](docs/project/plans.md),
  `TASKS.md` → [`docs/project/tasks.md`](docs/project/tasks.md) (git mv) +
  update seluruh referensi lintas-file (AGENTS, template PR, scripts,
  schemas, korpus, laporan historis).
- Audit arah on-demand dipindah menjadi snapshot historis:
  `docs/research/audit-2026-11-12.md` (isi tidak di-rewrite).
- Runbook server SAQ dipindah: `reports/P5-saq-server-runbook.md` →
  [`docs/development/saq-server-runbook.md`](docs/development/saq-server-runbook.md)
  (+ seksi baru **ND-6**: matriks 4 fase A–D di server, prasyarat fase D
  `npm install --ignore-scripts` di `saq-report/`, pola transfer record).
- `scripts/build-wasm.ps1` (verifikasi artefakt deployment): gate lazy
  (`tests/lazy.mjs`, 43 checks), mode `-VerifyOnly` (verifikasi tanpa
  rebuild), cek ekspor diperluas 9 → **21 simbol** ABI v3 penuh
  (3 core + 5 scanner + 13 parser).
- Pointer submodule `ze_json` dinaikkan ke main pasca-overhaul
  (rilis 0.1.2, publish GitHub Packages terverifikasi).

### Added

- `README.md` (root), `CHANGELOG.md`, index README per
  folder docs (`project/`, `architecture/`, `measurement/`, `research/`,
  `development/`), dan `reports/README.md` (indeks 15 laporan).
- ADR thesis: `docs/adr/` — 0001 (arah on-demand), 0004 (korpus
  `saq_payload_v1`), 0005 (slot sole-owner `readCount()`), 0006
  (kandidat cache-bytes), 0007 (schema pengukuran v1 + extras) — penomoran
  kontinu lintas-repo dengan `ze_json` (0002 scanner64 rejected, 0003 ABI v3
  slot pool milik ze_json).

## 2026-11-11 — Direktif on-demand 7 stage (ND-1…ND-7)

- ND-1 audit arah → snapshot `docs/research/audit-2026-11-12.md`.
- ND-4 lazy-access layer (L1 `lazy()`/L2 `project(shape)`) di binding —
  permukaan ABI v3 tidak berubah.
- ND-5 integrasi call-site read-only: `GET /rekap` di saq-report PR #3 —
  `readCount()` opt-in `SAQ_JSON_ENGINE=ze`, parity gate 26/26.
- ND-6 matriks benchmark 4 fase A–D (protokol disetujui pemilik; 6 record
  PASS validator) — acceptance ≥1.5× tercapai: fase D 2.85× (run utama) +
  3.00× (konfirmasi) pasca kandidat cache-bytes (saq-report PR #4).
- ND-7 laporan evaluasi: [`reports/ondemand-saq-evaluation.md`](reports/ondemand-saq-evaluation.md).

## Sebelumnya

Fase P0–P6 (fondasi pengukuran, scanner, binding, parser on-demand, dokumen
ze_json), P4 (profil & bottleneck), P5 (baseline server), E3 (LTO sandwich),
R1–R5 (optimalisasi terukur + server phase matrix) — rincian per task di
[`docs/project/tasks.md`](docs/project/tasks.md); laporan per eksperimen di
[`reports/`](reports/README.md).
