# Changelog — Workspace Skripsi v5

Riwayat perubahan workspace thesis (root `v5`). Entri berbasis tanggal —
workspace ini bukan paket yang dirilis; versi dari artefak terkait
(`ze_json` 0.1.x, npm `@zuudevs/ze-json`) tercatat di changelog masing-masing
repo. Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 2026-11-13 — AUD-1: audit artefak & protokol ND-6

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

- `README.md` (root), `CHANGELOG.md` (root — file ini), index README per
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
