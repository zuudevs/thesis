# Dashboard Monitoring Riset

Dashboard workspace untuk memantau progress pengukuran riset (skripsi v5) — parser JSON
on-demand **ze_json** (C++23 native/wasm64) vs baseline **V8 di saq-report**.
Membaca record pengukuran tervalidasi di `out/measurements/`, mengimpor ke MongoDB
lokal, lalu menyajikannya lewat pencarian, filter, chart, dan perbandingan.

> Source dashboard tracking resides in the root repository under
> `tools/dashboard/`. Local state such as `.env`, the MongoDB database, and
> dependency/build directories is excluded from Git.

## Prasyarat

- Node.js + npm
- MongoDB (`mongod`) tersedia di `PATH`

## Setup dan menjalankan

```powershell
cd tools/dashboard
Copy-Item .env.example .env

npm ci
npm ci --prefix backend
npm ci --prefix frontend

# satu perintah: mongod + backend + frontend
npm run dev
```

Ketiga package tree memiliki lockfile sendiri, sehingga `npm ci` wajib
dijalankan pada root dashboard, `backend/`, dan `frontend/`. File `.env`
adalah konfigurasi lokal dan tidak pernah di-commit.

- Backend  : http://localhost:3000 (Express 5 + Mongoose)
- Frontend : http://localhost:5173 (Vite + React + TS + MUI + ECharts, UI Bahasa Indonesia)

Alternatif CLI impor (setara tombol **Re-scan** di halaman Import):

```sh
npm run import          # scan + validasi + upsert
npm run import:prune    # + hapus run yang filenya sudah tidak ada
```

## Halaman

| Halaman | Isi |
|---|---|
| **Ringkasan** | KPI (run, result, dirty, exploratory, invalid), grafik aktivitas harian, sebaran site/kind/family |
| **Runs** | Tabel semua file record + filter lengkap + pencarian; klik → detail run |
| **Detail run** | identitas/mesin/konfigurasi verbatim, chart throughput per result, tabel results + rationale + basis paper |
| **Analisis** | 3 tab: timeline throughput (metrik bisa dipilih), panel acceptance vs ambang 1.5×, perbandingan mode scanner |
| **Compare** | pilih 2–8 result → chart + rasio speedup + guardrail |
| **Tests** | tabel result `kind=test` (ok/skip/fail) — siap dipakai saat record gtest mulai diimpor |
| **Import** | tombol Re-scan, status folder/schema/waktu impor, daftar record invalid (karantina) |

## Aturan riset yang diimplementasikan (AGENTS.md §4)

1. **Validasi schema wajib** — setiap file divalidasi terhadap
   `schemas/measurement.schema.json` (sumber kebenaran di root repo, dibaca via
   `SCHEMA_PATH`). Record gagal validasi masuk **karantina** (`InvalidRecord`),
   tidak pernah dipakai analisis.
2. **Label status run** — `dirty` dan `exploratory` selalu tampil sebagai badge
   (tabel, detail, compare, acceptance).
3. **Guardrail Compare** — perbandingan lintas **run_id**, **site**, **kind**, atau
   **korpus** DIBLOKIR; lintas **runtime/toolchain**, lintas **git hash**,
   tree dirty, dan run exploratory memberi peringatan ("narasi riset, bukan bukti").
4. **Bukti speedup = dalam satu run_id per site** — Compare memilih result
   dengan identitas `run_id + corpus_key + name`; panel acceptance hanya
   memasangkan baseline (engine `v8`) vs candidate pada `run_id + korpus` yang sama.

## Arsitektur singkat

```
tools/dashboard/
  .env                    # BACKEND_PORT, FRONTEND_PORT, MONGODB_*, MEASUREMENTS_DIR, SCHEMA_PATH
  database/               # dbpath MongoDB (mongod --dbpath database; gitignored)
  backend/
    src/models/           # Run (record verbatim + derived), Result (flatten per-result),
                          # InvalidRecord (karantina)
    src/services/         # ingest (scan→validate→upsert, kunci unik run_id+corpus),
                          # aggregate (trend/acceptance/scanner), compare (guardrail), stats
    src/routes/           # /api/runs, /api/results, /api/charts, /api/compare,
                          # /api/imports, /api/stats
    scripts/import-measurements.js  # CLI importer
  frontend/               # Vite + React + TS + MUI + ECharts (tree-shaken, proxy /api → :3000)
```

Model data: 1 dokumen `Run` per file record (record disimpan **verbatim** agar
provenance utuh) + 1 dokumen `Result` per entri `results[]` (flatten, siap
search/agregasi). Kunci unik: `(run_id, corpus_key)` — satu `run_id` bisa punya
hingga 6 file (6 korpus).

## Verifikasi

```powershell
npm test
npm run build:frontend
```

`npm test` memverifikasi schema measurement dan guardrail Compare tanpa
memerlukan MongoDB. Record yang gagal validasi dikarantina dan data import
lama dengan nama file yang sama dihapus agar tidak dapat dipakai analisis.