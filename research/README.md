# research/ — Analisa & visualisasi benchmark ze_json + saq-report + ze_json_js

Tujuan: membandingkan hasil benchmark **lintas-device** (device pribadi ↔
server SAQ) dan **lintas-paket** (ze_json scanner64 C++ ↔ ze_json WASM
binding di Node ↔ JSON.parse Node) dengan aturan provenance yang sama
(docs ze_json `docs/telemetry-sidecar.md`): join key `fixture + sha256`,
run_id unik per sesi, dan agregat P50/CI95 dari repetisi terstandar.

## Korpus terpadu

Kedua paket mengukur korpus byte-sama di `$SAMPLE` (3 grup):

| Grup | Isi | Sumber |
|---|---|---|
| `JSON_checker` | pass1-3 + fail1-33 (json.org) | upstream zip |
| `commons` | 9 dataset benchmark (tiny … jeopardy 152 MB) | internal + simdjson-data |
| `saq-report` | 21 fixture generator deterministik (nested) | `saq-report/benchmark/generate-samples.js` |

- Manifest jangkar: `$RAW/ze_json/manifest.json` (sha256 semua fixture).
- ze_json mengukur semuanya via target **`corpus_benchmark`** (registrasi
  dinamis `BM_Corpus_Scanner64_<grup>_<fixture>`; korpus negatif `fail*`
  tidak diregistrasi — memang wajib ditolak parser).
- saq-report mengukur semuanya via `benchmark-json.js` (default `--input`
  = akar `$SAMPLE`; `[INVALID]` fail* tercatat skipped, bukan error; fixture
  > 64 MB di-skip untuk mode `json-clone` saja — guard OOM).
- **ze_json_js** mengukur korpus yang sama via `benchmark_ze_json_js.mjs`:
  binding WASM ze_json (`bindings/js/ze_json.mjs`, memory64) di Node yang
  sama dengan JSON.parse — **perbandingan inti skripsi**. Tiga mode:
  `json-parse` (baseline V8, proses sama), `wasm-parse` (end-to-end dari
  string JS, termasuk `TextEncoder.encodeInto`), `wasm-parse-preloaded`
  (payload sudah di memori wasm — scan saja). Region memori diukur
  per-dokumen (tape = `size/2 + 64` entri, metodologi `corpus_benchmark`);
  butuh Node ≥ 24 (WASM memory64).

## Isi folder

| Berkas | Fungsi |
|---|---|
| `audit_raw.py` | Gerbang integritas `$RAW`: nama RUN_ID, pasangan report⟷sidecar, nol error, dataset sha256 ∈ manifest, layout nested. `--prune` hapus pelanggaran (iteratif sampai stabil). |
| `run_benchmarks.ps1` / `run_benchmarks.sh` | **Runner sekali-jalan** (Windows/Linux, kontrak identik): preflight korpus (install + generate + verify + scan) → 5 export ze_json (termasuk corpus_benchmark) → saq-report benchmark → ze_json_js benchmark → audit otomatis. |
| `benchmark_ze_json_js.mjs` | Benchmark ze_json WASM binding vs JSON.parse di Node (korpus terpadu, report self-contained schema 1.1.0 di `$RAW/benchmark/ze_json_js/`). |
| `analyze_benchmarks.py` | Gabung semua report+sidecar KEEP → `out/benchmarks.csv` + `out/summary.md` (tabel per-target, rasio lintas-device, tabel lintas-paket scanner64 vs JSON.parse, dan **tabel tiga arah** C++ vs WASM vs JSON.parse per sha256). |
| `visualize.py` | 5 chart bermakna (SVG+PDF, vector untuk skripsi) dari `benchmarks.csv` → `out/`. |
| `out/` | Output (regenerate kapan pun). |

## Alur kerja standar (identik di kedua device)

```powershell
# Device pribadi (Windows)
powershell research/run_benchmarks.ps1          # full: 5 repetisi, sekali jalan
```

```bash
# Server SAQ (Linux) — cukup env + satu perintah
export SAMPLE=/path/to/sample
export RAW=/path/to/raw
./research/run_benchmarks.sh
```

Lalu di device mana pun:

```powershell
python research/analyze_benchmarks.py
python research/visualize.py
```

Flag opsional runner: `-Quick` / `--quick` (3 repetisi, sanity), `-SkipZeJson`
/ `--skip-ze-json`, `-SkipSaqReport` / `--skip-saq-report`, `-SkipZeJsonJs` /
`--skip-ze-json-js`, `-SkipCorpusPreflight` / `--skip-corpus-preflight`.

> **Durasi**: `corpus_benchmark` (33 fixture × 5 repetisi × MinTime 15 s)
> butuh ± 1 jam sendiri; full run ± 1,5 jam. Jalankan di background / tmux,
> jangan dipotong di tengah — report yang terpotong = sidecar yatim = DELETE
> di audit.

## Aturan perbandingan (thesis)

1. Hanya bandingkan run dengan **fixture sha256 identik** (korpus byte-sama)
   dan **versi library identik** — diperiksa otomatis oleh analisa.
2. Angka pembanding: **P50** (median antar-repetisi) + **CI95**; bukan angka
   mentah antar-proses (jam antar-proses bergetar 15–45%).
3. Konteks device (cpu_model, cores, OS) dari sidecar `machine.*` — dicetak
   di tabel, bukan dianggap variabel bebas.
4. Setiap device menghasilkan run-id sendiri (`<host>-<stamp>-<commit>`); dua
   sesi tidak pernah menimpa artefak satu sama lain.
5. Lintas-paket: ze_json scanner64 (C++) vs JSON.parse (V8) di fixture
   sha256 sama — rasio P50 dilaporkan per fixture, bukan agregat menyatu.
6. **Perbandingan inti skripsi** = ze_json WASM binding (`ze_json.wasm/
   end-to-end`) vs JSON.parse di runtime Node yang sama; angka ze_json C++
   dilaporkan sebagai *native ceiling* (konteks), bukan pembanding utama.
   Beda semantik output dinyatakan eksplisit: `JSON.parse` mem-materialisasi
   objek JS penuh, ze_json membangun tape (indeks struktural) tanpa
   materialisasi.

## Dependensi

Python ≥ 3.11; `matplotlib` untuk visualisasi (`pip install matplotlib`);
Node.js ≥ 18 untuk saq-report benchmark dan **Node.js ≥ 24** untuk
ze_json_js (WASM memory64; versi lebih tua: `node
--experimental-wasm-memory64`); CMake + preset `native-release` untuk
ze_json.
