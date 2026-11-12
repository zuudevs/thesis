# Skripsi v5 — Workspace Komparatif Parsing JSON

Workspace skripsi: **pengukuran komparatif** jalur parsing JSON yang dipakai
server `saq-report/` (Node.js — baseline = `JSON.parse`/`JSON.stringify`
bawaan V8) terhadap **`ze_json/`** — parser JSON on-demand C++23 yang diukur
native (google-benchmark) dan via wasm64 di Node (`bindings/js`).

**Verdict terkini (ND-6/ND-7, 2026-11-12)**: jalur produksi `/rekap`
(cache Mongo, opt-in `SAQ_JSON_ENGINE=ze`) mencapai **2.85×/3.00×** baseline
V8 (acceptance ≥ 1.5× tercapai) — rincian
[`reports/ondemand-saq-evaluation.md`](reports/ondemand-saq-evaluation.md).

## Struktur

| Path | Isi |
|---|---|
| [`docs/project/`](docs/project/README.md) | Rencana skripsi + ledger tugas (sumber kebenaran rencana kerja) |
| [`docs/architecture/`](docs/architecture/README.md) | Dokumentasi arsitektur (lazy-access layer, dsb.) |
| [`docs/measurement/`](docs/measurement/README.md) | Protokol pengukuran (nd6-benchmark-plan, dsb.) |
| [`docs/research/`](docs/research/README.md) | Audit & riset arah (snapshot historis) |
| [`docs/development/`](docs/development/README.md) | Runbook operasional (server SAQ, dsb.) |
| [`docs/adr/`](docs/adr/README.md) | Architecture decision records (penomoran kontinu lintas-repo) |
| [`reports/`](reports/README.md) | Laporan hasil eksperimen per-task (15 laporan + arsip record) |
| [`schemas/`](schemas/README.md) | Measurement record schema v1 + validator |
| [`corpus/`](corpus/benchmarks/README.md) | Korpus benchmark (42 file, manifest sha256) + korpus json_checker |
| `scripts/` | Harness benchmark, validator, analyzer, codegen korpus, tooling |
| `out/` | Hasil ukur (raw exhibit + record tervalidasi) — gitignored |
| `out/rag/` | Korpus paper (~50 DOI) untuk provenance literatur |
| `ze_json/` | Submodule — library parser (sumber: [repo ze_json](https://github.com/zuudevs/ze_json)) |
| `saq-report/` | Submodule — aplikasi Node.js SAQ (baseline) |
| `assets/bib/cites.bib` | Bibliografi (entri wajib year ≥ 2016) |

## Prinsip kerja

1. **Rencana & tugas**: [`docs/project/plans.md`](docs/project/plans.md) +
   [`docs/project/tasks.md`](docs/project/tasks.md) — baca keduanya sebelum
   mengubah apa pun. Setiap sesi mulai dari `scripts/env/activate.ps1`.
2. **Provenance wajib**: setiap teknik dari paper membawa `@cite <DOI>`
   (korpus paper di `out/rag/`); setiap record pengukuran membawa field
   `rationale` dan wajib PASS
   `python scripts/measurement-schema/validate.py <record>`.
3. **Perbandingan hanya dalam satu run** (mesin, preset, git hash, korpus
   sama). Runner site-aware (`--site`) — server SAQ dijalankan dengan
   prosedur identik begitu akses tersedia (runbook:
   [`docs/development/saq-server-runbook.md`](docs/development/saq-server-runbook.md)).
4. **Git**: branch → PR → merge (tanpa push langsung `main`); Conventional
   Commits (English) + template PR.
5. **Bahasa**: dokumen & laporan Indonesia; kode, identifier, nama file,
   commit English. `ze_json/docs/` English (dokumentasi library).

## Perintah harian

```sh
# environment (wajib di sesi non-interaktif)
scripts\env\activate.ps1

# build & test ze_json (dari root workspace)
cmake --preset native-release --preset-dir ze_json ...
#   — atau lihat docs ze_json/ (dokumentasi build lengkap di sana)

# benchmark V8 vs ze-wasm64 (semua korpus)
node --expose-gc scripts/node-benchmark/harness.mjs \
  --corpus all --engine all --site dev_device --rounds 15

# matriks on-demand ND-6 (fase A–D, satu fase per eksekusi)
node --expose-gc scripts/bench/nd6_bench.mjs --phase D --rounds 15 --warmup 3

# validasi record
python scripts/measurement-schema/validate.py out/measurements/<run_id>.record.json
```

Riwayat perubahan workspace: [`CHANGELOG.md`](CHANGELOG.md).
