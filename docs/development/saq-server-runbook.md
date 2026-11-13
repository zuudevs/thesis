# Runbook Benchmark Server SAQ (P5 baseline V8 + ND-6 on-demand)

Tujuan: (a) baseline V8 (`JSON.parse`/`JSON.stringify` — jalur panas
saq-report) di server produksi SAQ (`site=saq_server`) sebagai data
komparatif RQ2 (P5-2), dan (b) matriks jalur on-demand ze_json 4 fase
A–D (ND-6, Stage 6) di situs yang sama. Keduanya dieksekusi owner via
SSH. Runner sudah site-aware (AGENTS §6) — prosedur identik dengan situs
dev, tanpa mengubah harness.

## 0. Prasyarat server

| Kebutuhan | Cek |
|---|---|
| Node.js >= 24 (kontrak proyek) | `node --version` |
| git + akses GitHub `zuudevs` (repo private → deploy key/PAT) | `git ls-remote https://github.com/zuudevs/thesis.git` |
| Mesin idle saat pengukuran (tanpa build/deploy lain) | `uptime`, htop |

## 1. Clone + submodule

```sh
git clone https://github.com/zuudevs/thesis.git v5 && cd v5
git submodule update --init saq-report ze_json
```

- Korpus benchmark (42 file, ~1.2 MB, manifest sha256) ikut dari clone —
  tidak perlu transfer manual.
- `saq-report` wajib: provenance baseline (`--repo saq_report` membaca hash
  git-nya) dan objek riset.
- `ze_json` wajib: harness mengimpor `ze_json/bindings/js/ze_json.mjs`
  secara statis (dipakai engine `ze-parser`; tidak untuk engine `v8`).

## 2. Smoke (verifikasi import + host introspection)

```sh
node scripts/host-introspect.mjs
```

Harus mencetak JSON metadata host server (hostname, CPU, RAM, node/V8).
Bila gagal: cek versi Node (< 24 hanya warning, error import = rusak).

## 3. Baseline V8 saq-report (P5-2 — target utama)

```sh
node --expose-gc scripts/node-benchmark/harness.mjs \
  --corpus all --engine v8 --site saq_server --repo saq_report --repeats 5
```

- Menghasilkan 6 korpus × 3 konteks (`body-parse`, `store-read`,
  `export-stringify`) = 6 record + raw exhibit per korpus.
- `run_id = <hostname-server>-<UTCstamp>-<saq-report-hash>`;
  `site: "saq_server"`; host metadata otomatis di setiap record.
- Flag harness identik dengan situs dev (repeats 5, min-time 200 ms,
  warmup 300 ms) — komparabilitas metodologi.
- Waktu: ± 3-5 menit.

## 4. (Opsional, P5-3) ze_json wasm64 in-situ server

```sh
node --expose-gc scripts/node-benchmark/harness.mjs \
  --corpus all --engine ze-parser --site saq_server --repo ze_json --repeats 5
```

 ze_json (wasm64) vs V8 **di mesin yang sama (server)** — sisi server dari
perbandingan lintas-arsitektur. Catatan: bila `bindings/js/ze_json.wasm`
di submodule belum commit-update, rebuild dulu via `scripts/build-wasm.ps1`
(membangun + memverifikasi artefakt: build type, 21 ekspor ABI v3, SIMD,
sha256 sidecar; mode `-VerifyOnly` untuk artefakt yang sudah ada) atau
salin artefakt dari dev.

## 5. ND-6 — matriks on-demand 4 fase (Stage 6)

Protokol eksperimen: `docs/measurement/nd6-benchmark-plan.md` (disetujui
pemilik). Kontrol: warmup untimed, ronde independen, alternating (urutan
jalur dirotasi), tanpa buang outlier — semua ronde dilaporkan. Jalankan
**satu fase per eksekusi** (satu `run_id` per fase; perbandingan
baseline↔ze hanya dalam satu run_id — AGENTS §4):

```sh
node --expose-gc scripts/bench/nd6_bench.mjs --phase A --rounds 15 --warmup 3 --site saq_server
node --expose-gc scripts/bench/nd6_bench.mjs --phase B --rounds 15 --warmup 3 --site saq_server
node --expose-gc scripts/bench/nd6_bench.mjs --phase C --rounds 15 --warmup 3 --site saq_server
node --expose-gc scripts/bench/nd6_bench.mjs --phase D --rounds 15 --warmup 3 --site saq_server
```

| Fase | Jalur yang diukur | Isolasi mekanisme |
|---|---|---|
| A | `v8-parse` (JSON.parse) · `v8-clone` (klon `MongoJsonRepository.read()` H1) · `ze-parse` (full materialize) | biaya full materialization vs baseline |
| B | `v8-selective` (JSON.parse + subset `id`) · `ze-project-selective` (L2 `project(shape)`) | L2 vs konsumen V8 identik |
| C | `v8-selective` (identik dengan B) · `ze-l1-traversal` (L1 frame walk, early-exit) | L1 vs konsumen V8 identik (biaya ABI per panggilan terlihat) |
| D | jalur repositori saq-report (`D-rekap-request`, 4 repo: courses/assistants/schedules/reports) | pembanding in-situ jalur yang benar-benar ditanggung server |

- **Prasyarat fase D**: `npm install --ignore-scripts` di `saq-report/`
  sekali (skrip mengimpor `repositories/JsonRepository.js` +
  `repositories/MongoJsonRepository.js` dari submodule). Fase A–C tidak
  butuh ini.
- Korpus default `corpus/benchmarks/saq_payload_v1` (override `--corpus`).
- Output per eksekusi: `out/raw/<run_id>/nd6_phase_<X>.json` (exhibit
  mentah, semua ronde), `out/raw/<run_id>/metadata.json`, dan record
  `out/measurements/<run_id>-nd6-<fase>-<site>.record.json`.
- Validasi wajib sebelum dipakai analisis (lihat §6).
- Waktu: ± 2–4 menit per fase (4 fase total ± 15 menit).

## 6. Transfer hasil balik ke dev

```sh
# dari dev (ganti user/host):
scp -r user@saq-server:~/v5/out/raw/<run_id> out/raw/
scp "user@saq-server:~/v5/out/measurements/<run_id>*.json" out/measurements/
```

(Gabungan pola record harness `<run_id>_*.json` dan ND-6
`<run_id>-nd6-*.json`.)

Lalu di dev: validasi + ledger.

```sh
python scripts/measurement-schema/validate.py out/measurements/<run_id>.record.json
```

## 7. Disiplin metodologi (AGENTS §4 / plans §8)

- **Jangan membandingkan angka lintas situs secara kasar** — perbandingan
  dev-vs-server adalah eksperimen P5/RQ2 yang disetujui; syaratnya korpus
  identik (sha256 manifest tercatat di record), versi Node/V8 tercatat
  (field `library`/`host`), dan laporan menyebut kedua situs + spesifikasi.
- Server harus idle; bila cv > 10% pada korpus besar, ulangi run di window
  lain dan laporkan keduanya.
- Baseline dev (`site=dev_device`) tidak digantikan — kedua situs adalah
  dua baris komparatif paralel.

## 8. Troubleshooting

| Gejala | Penanganan |
|---|---|
| `git rev-parse failed for repo 'saq_report'` | submodule belum init / tidak ada .git — ulangi langkah 1 |
| `corpus manifest not found` | clone tidak lengkap — pastikan di root `v5`, bukan subfolder |
| warning `node < 24` | upgrade Node (kontrak proyek); hasil tetap jalan tapi dicatat |
| cv tinggi (>10%) di korpus kecil (checker_batch) | normal untuk dokumen mikro; fokuskan interpretasi ke korpus ≥ 10k |
