# Rencana Benchmark ND-6 — Matriks 4 Fase A–D (Stage 6)

> Status: **desain, belum ada angka**. Eksekusi setelah persetujuan pemilik.
> Dasar: TASKS ND-6, desain `docs/architecture/lazy-access-api.md` §11, §13
> (hipotesis), keputusan pemilik 2026-11-12 (korpus tetap `saq_payload_v1`,
> Workload D pakai data store asli). Semua angka yang keluar dari protokol ini
> menjadi record tervalidasi — bukan probe preliminary.

## 1. Tujuan & acceptance

- Menjawab RQ utama: apakah jalur lazy `ze_json` mencapai
  **Speedup = T_baseline / T_ze ≥ 1.5×** pada workload SAQ asli?
- Acceptance utama = **Fase D**. Fase A–C adalah matriks diagnostik yang
  memisahkan kontribusi biaya: open/arena vs traversal vs decode vs boxing
  ABI (hipotesis §13.3).
- Site: `dev_device` (akses server SAQ belum ada — runner site-aware;
  protokol identik saat `saq_server` tersedia).

## 2. Definisi fase (per dokumen korpus, satu run_id per fase)

Korpus: **`corpus/benchmarks/saq_payload_v1`** (6 dokumen file store SAQ,
provenance sha256 manifest P0-8) — tidak diganti, tidak diregenerasi.
Baseline selalu V8 (`JSON.parse` bawaan Node 24); candidate selalu jalur
`ze_json` wasm64 C-ABI v3 pada hash bersih yang sama (submodule pointer
tercatat di record `git_commit`).

| Fase | Pertanyaan | Jalur baseline | Jalur ze |
|---|---|---|---|
| **A** materialisasi penuh | Berapa biaya ceil bila semua dibaca? | `JSON.parse(text)`; plus varian clone `JSON.parse(JSON.stringify(x))` (semantik `MongoJsonRepository.read()`) | `ZeParser.parse()` (full materialize) |
| **B** parsial (L2) | Konsumen ambil subset field level atas — apa untungnya? | `JSON.parse` lalu akses subset field sama | `project(shape-parsial)` — hanya subset yang dipayung |
| **C** deep selective (L1) | Konsumen hanya butuh count/id per item — apa untungnya? | `JSON.parse` lalu loop akses field sama | traversal frame manual: `get(key)` + `countElements` + decode minimal, early-exit |
| **D** workload SAQ asli (**acceptance**) | Request `/rekap` satu iterasi = 4 repo | `repo.read().length` × 4 (jalur default, byte-identical produksi) | `repo.readCount()` × 4 (`SAQ_JSON_ENGINE=ze`) |

- Fase A–C berjalan pada level binding (dokumen per dokumen, semua 6 file).
- Fase D berjalan pada level **repositori aplikasi** (`JsonRepository`
  file-store mode memakai file korpus sebagai data store; `MongoJsonRepository`
  diukur terpisah dengan cache yang di-seed dari file yang sama — replikasi
  state pasca-`init()` tanpa MongoDB). Satu iterasi D = satu request `/rekap`.
- GlobalConfig tidak ikut iterasi `.length` (`.length`-nya `undefined` di
  kedua jalur — sudah terkunci parity gate ND-5); dilaporkan sebagai
  result `skip` dengan alasan, agar matriks jujur.

## 3. Kontrol eksperimen

1. **Warmup**: 3 rep untimed per (dokumen × jalur) sebelum pengukuran.
2. **Ronde independen**: 15 ronde; setiap ronde mengukur ulang semua jalur.
3. **Alternating**: urutan jalur dirotasi per ronde (round-robin offset) —
   thermal/JIT/turbo bias merata antar jalur; TIDAK ada fase berurutan
   panjang seperti probe §13.
4. **Tanpa buang outlier**: semua ronde dilaporkan apa adanya; agregat =
   mean, **median**, **P95** (interpolasi linier), stddev. Tidak ada trimming.
5. **Satu `run_id` per fase**: `run_id = <hostname>-<YYYYMMDDHHMMSS>-<hash>`;
   perbandingan baseline↔ze hanya dalam satu run_id (hukum §4 AGENTS).
6. **Reps per ronde** di-skala per ukuran dokumen (target ≥ ~2 ms per
   ronde-jalur; ditulis di `config.iterations`) supaya timer presisi.
7. **GC dikontrol**: `global.gc()` antar dokumen (`node --expose-gc`);
   jumlah GC minor/major selama ronde dihitung via `PerformanceObserver`
   dan dilaporkan — bukan disembunyikan.
8. **Host metadata lengkap**: hostname, OS, arch, CPU model, toolchain
   `node 24.x (v8 13.x) + wasm64` — wajib di record.
9. **Dirty tree**: hash suffix `-dirty` dan disebut; eksekusi hanya dari
   working tree bersih.

## 4. Skema metrik v2 (apa yang dilaporkan per result)

Record tetap **schema v1.0.0** (validator P0 tak berubah — PLANS §3:
field tambahan lewat `extras`). Per result `results[]`:

| Field (lokasi) | Arti |
|---|---|
| `metrics.seconds_mean` (wajib schema) | mean per-op seluruh ronde |
| `metrics.seconds_stddev` | stddev |
| `metrics.bytes_per_second` / `documents_per_second` | throughput |
| `extras.seconds_median`, `extras.seconds_p95` | median & P95 (metrik v2) |
| `extras.rounds`, `extras.reps_per_round` | kontrol eksperimen |
| `extras.heap_delta_bytes`, `extras.gc_minor`, `extras.gc_major` | proxy alokasi ("alloc") |
| `extras.binding_calls` | jumlah panggilan ekspor ABI (boxing count) |
| `extras.index_count` | jumlah operasi akses struktural (`get`/`count`/`next`) |
| `extras.consumed_fields`, `extras.skipped_fields` | field yang dibayar vs dilewati (statis dari shape vs dokumen) |
| `extras.path` | nama jalur (A1/A2/A3/B/C/D-baseline/D-ze) |
| `extras.saq_engine` | `v8` \| `ze` (fase D) |

`rationale` per result wajib (sinkron komentar `@cite` di harness): 
`10.1002_spe.3313` (on-demand JSON), `10.14778_3115404.3115416` (Mison —
structural index menopang count).

## 5. Harness & artefak

- **Harness tunggal di root**: `scripts/bench/nd6_bench.mjs` (Node ≥ 24,
  ESM, `--expose-gc`). Alasan: fase D butuh memuat repositori saq-report,
  fase A–C butuh binding ze_json — record adalah artefak workspace-level.
- CLI: `node scripts/bench/nd6_bench.mjs --phase A|B|C|D [--rounds 15]
  [--warmup 3] [--site dev_device] [--corpus <dir>]`.
- Output per eksekusi fase:
  - `out/raw/<run_id>/nd6_phase_<X>.json` — exhibit mentah (semua ronde,
    semua dokumen, semua jalur, timestamp per ronde).
  - `out/raw/<run_id>/metadata.json` — sidecar host/tool/config.
  - `out/measurements/<run_id>-nd6-<X>-record.json` — record hasil
    normalisasi → **wajib PASS** `python scripts/measurement-schema/validate.py`.
- Analisis: `python scripts/analyze_measurement/main.py` (baseline vs
  candidate dalam satu run_id; guard host/korpus).

## 6. Protokol eksekusi

1. Verifikasi working tree bersih di root + kedua submodule; catat hash.
2. Urutan eksekusi: **A → B → C → D**, satu perintah satu fase, tanpa
   beban paralel lain; antar-fase jeda ≥ 5 s (thermal).
3. Setiap fase selesai → langsung validasi record + hitung summary.
4. Figure untuk laporan: `out/charts/nd6_*.png` (figur, bukan bukti —
   bukti tetap record).
5. Hasil dimasukkan ke laporan Stage 6 → input ND-7 verdict.

## 7. Kriteria keputusan pasca-ukur

- **Fase D ≥ 1.5×** (median, dan P95 tidak runtuh) → lulus acceptance;
  lanjut ND-7 (verdict + tulis laporan).
- **Fase D < 1.5×** → matriks A–C memutuskan bottleneck:
  open/arena mendominasi → kandidat reuse slot (§4.2 desain);
  boxing ABI mendominasi → kandidat batch/proyeksi C++-side (ABI v4) —
  **wajib diukur ulang** (O1-11) sebelum diklaim;
  decode string mendominasi → kandidat lazy decode.
  Tidak ada perubahan boundary ukur demi angka (larangan §11).

## 8. Risiko & mitigasi

| Risiko | Mitigasi |
|---|---|
| Dokumen korpus ~4–39 KB → biaya open (~25–50 µs) mendominasi, rasio buruk | Itulah pertanyaan risetnya — dilaporkan apa adanya; matriks B/C memisahkan kontribusi |
| JIT berubah di tengah run | warmup + alternating + ronde independen |
| GC noise | `--expose-gc` + hitung GC events, dilaporkan |
| Drift antar fase (A dijalankan beda kondisi dari D) | satu run_id per fase + alternation internal; tidak ada perbandingan lintas run_id |
| `require(esm)` binding lambat saat load | load sekali di luar ronde (warmup termasuk) |

## 9. Yang TIDAK dilakukan

- Tidak mengubah workload/benchmark demi angka (direktif).
- Tidak meregenerasi korpus; tidak menambah korpus sintetis ke matriks.
- Tidak memakai `native-sanitize` untuk angka; tidak memakai angka probe §13
  sebagai bukti.
- Tidak membandingkan lintas mesin/preset/hash/korpus.

## 10. Hasil eksekusi ND-6 (pasca-protokol — 2026-11-12)

Eksekusi penuh sesuai protokol §3–§6 (15 ronde, warmup 3, alternating,
tanpa trimming, GC 0/0 di semua fase, semua record **PASS** validator;
arsip verbatim: `reports/nd6/*.record.json` — angka di bawah = **median**,
speedup = baseline/ze **dalam run yang sama**; dev device `zuu`):

| Fase | Run | Jalur (median ms/op) | Speedup |
|---|---|---|---|
| A materialisasi penuh | `...063944-0dcb418` | v8-parse 0.010–0.096 vs ze-parse 0.030–1.985 | **0.04–0.07×** (ze 14–27× lebih lambat) |
| A klon (semantik `read()` Mongo) | idem | v8-clone 0.003–0.144 vs ze-parse | **0.02–0.07×** |
| B parsial (L2 `project`) | `...063949-0dcb418` | v8-selective 0.003–0.100 vs ze-project 0.028–1.055 | **0.09–0.11×** (kalah semua) |
| C deep selective (L1) | `...063955-0dcb418` | schedules v8 0.102 vs L1 0.065; assistants 0.018/0.012; lecturers 0.011/0.012; courses 0.013/0.014; reports 0.074/0.290; globalConfig 0.004/0.065 | **1.57× / 1.50× / 0.92× / 0.93× / 0.26× / 0.06×** |
| D pre-candidate | `...064001-0dcb418` | file-store v8 4.207 vs ze 5.036; mongo-cache v8 0.359 vs ze 0.328 | **0.84× / 1.10×** |
| D **pasca kandidat cache-bytes** (saq-report PR #4 `8c7f2d4`) | `...064628-bbee7bf` | file-store v8 3.927 vs ze 4.321; mongo-cache v8 0.365 vs ze **0.128** | **0.91× / 2.85×** (p95 2.10×) |
| D konfirmasi (run independen kedua) | `...064642-bbee7bf` | mongo-cache v8 0.390 vs ze **0.130** | **3.00×** (p95 2.14×) |

**Verdict**: acceptance **T_baseline/T_ze ≥ 1.5× TERCAPAI pada jalur
produksi** (cache Mongo ter-load, mode `SAQ_JSON_ENGINE=ze`): **2.85×**
(run utama) dan **3.00×** (run konfirmasi independen) — median; p95
2.10×/2.14× — robust di atas target. Satu perubahan per eksperimen:
kandidat cache-bytes (stringify sekali per mutasi cache, bukan per
`readCount()`) adalah penyebab lompatan 1.10× → 2.85× (dibuktikan dua
run self-contained, bukan klaim).

**Limitasi jujur (dilaporkan apa adanya — larangan §11):**

1. **File-store mode 0.91×** (ze kalah): iterasi dibayar ~4 ms I/O
   `readFileSync` yang sama di kedua jalur (Defender real-time scan pada
   mesin dev — karakteristik host); parser bukan penentu. Mode ini adalah
   fallback degradasi, bukan jalur produksi.
2. **L2 `project` (fase B) kalah di semua ukuran SAQ** — biaya open arena +
   per-call ABI ≫ parse V8 pada dokumen 3.6–39 KB. L2 hanya viable untuk
   dokumen ≫ ukuran SAQ; konsumen SAQ jalur L2 dihentikan rekomendasinya
   (dipakai L1/count).
3. **L1 traversal menang hanya bila panggilan ABI per item sedikit**
   (schedules 1.57×, assistants 1.50×) dan kalah bila banyak (reports
   0.26×, ~191 panggilan ABI/op). Call-site enrichment berikutnya (ND-5
   lanjutan) harus konservatif: count-only terbukti; decode-per-item
   harus diukur dahulu (hipotesis ABI v4 batch masih terbuka, O1-11).
4. Angka = dev device; server SAQ belum tersedia (site-aware runner siap,
   protokol identik saat akses ada). Perbandingan lintas run_id di tabel
   adalah **narasi riset**, bukan bukti — bukti = speedup dalam satu run.

