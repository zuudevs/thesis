# Evaluasi Riset On-Demand JSON untuk Server SAQ — Laporan Final (Stage 7, ND-7)

> Tanggal: 2026-11-12 · Direktif: *"Scan the structure once. Access only what
> is needed."* · Target: Speedup = T_baseline/T_ze ≥ 1.5× pada workload SAQ
> asli, dibuktikan eksperimental tanpa mengubah workload/benchmark.
> Bukti: 6 record tervalidasi (`reports/nd6/*.record.json`, semuanya **PASS**
> `scripts/measurement-schema/validate.py`); exhibit raw `out/raw/<run_id>/`.
> Bahasa angka: **median** per-op; speedup = baseline/ze **dalam satu run_id**
> (AGENTS §4).

---

## 1. Verdict

**Acceptance tercapai pada jalur produksi: Speedup 2.85× (run utama) dan
3.00× (run konfirmasi independen), p95 2.10×/2.14× — di atas target 1.5×.**

Verdict ini berlaku untuk boundary yang diukur: **jalur repositori call-site
GET `/rekap`** (4× `read().length` vs 4× `readCount()`) pada mode produksi
(cache Mongo ter-load, `SAQ_JSON_ENGINE=ze` opt-in) dengan korpus data store
asli `saq_payload_v1` (provenance P0-8). Baseline tidak diubah byte-identical;
tidak ada boundary ukur yang dimanipulasi (larangan §11 dijunjung penuh:
protokol disetujui lebih dulu, kandidat diukur — bukan diklaim, O1-11).

---

## 2. Pertanyaan riset & hipotesis — status akhir

| Hipotesis (audit §7) | Eksperimen | Status | Bukti |
|---|---|---|---|
| **H1 (klon-clone)** — ganti clone per read dengan akses lazy menghapus stringify+parse penuh | Fase D (mongo-cache) | **Terverifikasi** — setelah kandidat cache-bytes: 2.85×/3.00× | `...064628/064642-bbee7bf` |
| **H2 (proyeksi terpilih)** — materialisasi subset field yang dipakai view | Fase B (L2 `project`) | **Ditolak untuk ukuran SAQ** — kalah semua (0.09–0.11×): open arena + per-call ABI ≫ parse V8 pada 3.6–39 KB | `...063949-0dcb418` |
| **H3 (skip)** — lewati field tak-dibaca tanpa decode | Fase C (L1 count-only) | **Sebagian** — count-only menang (schedules 1.57×, assistants 1.50×); decode-per-item kalah bila panggilan ABI tinggi (reports 0.26×, ~191 ABI/op). Skip granularity masih terbuka | `...063955-0dcb418` |
| **H4 (body-parse)** — `express.json()` kecil, dampak minor | — | **Belum diukur** (server penuh tidak tersedia) | — |
| **H5 (stringify/export)** — on-demand tidak membantu jalur tulis | — | **Belum diukur**; konsisten dengan desain (jalur tulis tetap V8) | — |

Premis direktif terkonfirmasi tegas di fase A: materialisasi penuh via wasm
**14–27× di bawah V8** — arah on-demand adalah satu-satunya jalur viable
(`...063944-0dcb418`).

---

## 3. Implementasi yang dievaluasi

1. **Lapisan lazy ze_json** (Stage 4, ze_json PR #31 `defd452`): parser
   on-demand `ZeParser` (frame `(ts, cursor)`) — `get(key)` protokol induk,
   `countElements`, `getString` (decode V8-locked), `project(shape)` (L2),
   iterator `lazy().items()` (L1); wasm64 C-ABI v3 tanpa ekspor baru.
2. **Integrasi call-site read-only** (Stage 5, saq-report PR #3 `7930009`):
   `readCount()` pada `JsonRepository`/`MongoJsonRepository`; loader
   `repositories/zeJsonBinding.js` (`require(esm)`, Node ≥ 24); pola
   sole-owner (open → count → close → `resetHeap` sinkron, atomik event
   loop); opt-in env `SAQ_JSON_ENGINE=ze`; parity `.length` penuh termasuk
   lokasi error (TypeError call-site vs dalam-`read()` → AppError 500).
3. **Kandidat cache-bytes** (Stage 6, saq-report PR #4 `8c7f2d4`): bytes
   kanonik cache dibangun lazy **sekali per mutasi** (seed/write, invalidate
   on write) — menghapus 4×`JSON.stringify` (~88 KB) per request pada jalur
   ze. Satu perubahan per eksperimen; parity gate tetap 26/26 hijau.
4. **TIDAK diubah**: baseline V8 (`JSON.parse`, clone H1
   `JSON.parse(JSON.stringify())`), `express.json()`, workload/benchmark,
   korpus — sesuai direktif.

---

## 4. Setup pengukuran

- **Host**: dev device `zuu` (Windows, Node 24.19.0, V8 13.x, wasm64 ABI v3).
- **Korpus**: `corpus/benchmarks/saq_payload_v1` — 6 dokumen, 88.381 B,
  manifest sha256 tercatat per record (keputusan pemilik 2026-11-12: korpus
  tetap, tidak diregenerasi).
- **Protokol** (`docs/measurement/nd6-benchmark-plan.md`, disetujui pemilik):
  15 ronde independen, warmup 3 rep untimed, **alternating** (rotasi urutan
  jalur per ronde), **tanpa buang outlier**, GC diobservasi dan dilaporkan
  (0/0 semua fase), reps di-skala per ukuran dokumen, satu `run_id` per fase.
- **Metrik v2** via `extras` (schema tetap v1.0.0, PLANS §3): seconds_median,
  seconds_p95, binding_calls (ekspor ABI sisi JS), index_count,
  consumed/skipped_fields, GC minor/major.
- **Fase D** diukur pada level repositori aplikasi nyata (kode produksi
  Stage 5): file-store mode (JsonRepository) dan mongo-cache mode
  (MongoJsonRepository dengan cache di-seed dari file yang sama — replikasi
  state pasca-`init()` tanpa MongoDB; **mode produksi aktual**).

---

## 5. Hasil

### 5.1 Matriks diagnostik (A–C)

| Fase | Jalur | Median (ms/op) | Speedup | Interpretasi |
|---|---|---|---|---|
| A | v8-parse vs ze-parse | 0.002–0.096 vs 0.030–1.985 | 0.04–0.07× | materialisasi penuh wasm 14–27× lebih lambat → wajib lazy |
| A | v8-clone vs ze-parse | 0.003–0.144 | 0.02–0.07× | clone H1 juga kalah |
| B | v8-selective vs ze-project | 0.003–0.100 vs 0.028–1.055 | 0.09–0.11× | L2 tidak viable di ukuran SAQ |
| C | v8-selective vs ze-l1 | schedules 0.102/0.065 · assistants 0.018/0.012 · lecturers 0.011/0.012 · courses 0.013/0.014 · reports 0.074/0.290 · globalConfig 0.004/0.065 | **1.57× · 1.50× · 0.92× · 0.93× · 0.26× · 0.06×** | L1 menang bila ABI-per-item rendah; kalah bila tinggi |

### 5.2 Acceptance (Fase D — workload SAQ asli)

| Run | Mode | Baseline V8 (median) | ze (median) | Speedup | p95 speedup |
|---|---|---|---|---|---|
| `...064001-0dcb418` (pre-kandidat) | mongo-cache | 0.359 ms | 0.328 ms | **1.10×** | — |
| idem | file-store | 4.207 ms | 5.036 ms | **0.84×** | — |
| `...064628-bbee7bf` (**utama**) | mongo-cache | 0.365 ms | **0.128 ms** | **2.85×** | **2.10×** |
| idem | file-store | 3.927 ms | 4.321 ms | 0.91× | — |
| `...064642-bbee7bf` (konfirmasi) | mongo-cache | 0.390 ms | **0.130 ms** | **3.00×** | **2.14×** |

Eksperimen kandidat dibuktikan dua run self-contained: 1.10× → 2.85× →
3.00×; perbandingan antar run adalah narasi riset, bukan bukti.

---

## 6. Bukti korektness (bukan hanya kecepatan)

1. **Parity gate 26/26** (`scripts/check-json-lazy-parity.js`): file store
   (korpus provenance P0-8), cache Mongo (simulasi pasca-`init()`), file
   hilang, 12 edge semantik — nilai `.length` **dan** jenis & lokasi error
   identik baseline (`?? default` pada null; TypeError call-site vs
   dalam-`read()` → AppError). Tetap 26/26 pasca kandidat cache-bytes.
2. **Test binding lazy** (`ze_json/bindings/js/tests/lazy.mjs`): 43 check
   hijau (T1–T6: differential proyeksi, duplikat-key, lifetime slot, skip,
   string/number edge, parity byte-exact).
3. **Validator schema**: setiap record yang memandu analisis wajib PASS
   (`scripts/measurement-schema/validate.py`) — 6/6 PASS; record tanpa
   validator tidak pernah dipakai.
4. **Provenance**: korpus sha256 manifest, git hash (root/ze_json/saq-report,
   dirty flag dari tracked files saja), host metadata — lengkap di tiap
   record; exhibit raw menyimpan SEMUA ronde per dokumen per jalur.

---

## 7. Analisis bottleneck (sintesis)

- **Biaya tetap per iterasi ze** = open arena (~30–50 µs) + boxing BigInt
  per panggilan ABI — mendominasi di dokumen 3.6–39 KB (V8 parse lecturers
  hanya ~9 µs!). Itulah mengapa L2 (B) kalah dan L1 (C) hanya menang di
  dokumen besar dengan panggilan ABI sedikit.
- **Fase D pre-kandidat 1.10×** bukan karena parser: jalur repositori
  mem-stringify cache **setiap** `readCount()` (4× ~88 KB/request) —
  overhead JS-side. Kandidat cache-bytes menghapusnya → count murni
  (open + structural count) → 2.85×/3.00×.
- **File-store D ~4 ms I/O** (`readFileSync`, dibayar kedua jalur —
  diduga Defender real-time scan pada mesin dev) membanjiri parser; ze
  tambah open arena → 0.91×. Karakteristik host, dilaporkan apa adanya.

---

## 8. Limitasi (dilaporkan jujur)

1. **Workload D literal "server utuh" belum dijalankan**: akses server SAQ
   belum tersedia — D diukur pada boundary repositori call-site `/rekap`
   (persis kode produksi Stage 5) dengan data store asli; render EJS,
   join service, dan `express.json()` tidak termasuk boundary. Runner
   site-aware siap; protokol identik dijalankan saat akses ada.
2. **Gap fidelity korpus** (audit §4.4): `saq_payload_v1` anonim, indent-2
   seperti writer repo; distribusi field tidak identik data live — terdok
   umentasi sebagai limitasi.
3. **Angka = dev device**; tidak ada perbandingan lintas mesin (RQ2 lintas
   arsitektur ditunda).
4. **File-store fallback 0.91×** — jalur degradasi (cache belum load);
   tidak dilayangkan menang.
5. **L1 decode-per-item tidak aman** tanpa pengukuran (reports 0.26×);
   call-site baru wajib count-only dulu + ukur.
6. Hipotesis H4/H5 belum diuji (butuh server utuh).

---

## 9. Karya lanjutan

1. **Server SAQ run** (site `saq_server`): jalankan protokol identik —
   acceptance akhir pada handler penuh (termasuk H4).
2. **Perluasan call-site** (dashboard stats/enrichment) dengan disiplin
   yang sama: satu perubahan → parity gate → ukur (setelah ND-6 dulu
   menyimpulkan — call-site baru bukan pengganti bukti).
3. **ABI v4 batch-count** (satu panggilan untuk N repo): mengurangi boxing
   JS; open arena tetap per dokumen — wajib diukur dulu (O1-11).
4. **Profil open arena**: reuse slot lintas call-site (desain §4.2) bila
   call-site mulai menahan handle.
5. H3 skip-granularity dan H5 export — eksperimen terpisah sesuai
   metodologi (satu perubahan per pengukuran).

---

## 10. Provenance & reproduksibilitas

- Rencana protokol: `docs/measurement/nd6-benchmark-plan.md` (§1–9 protokol;
  §10 hasil as-built).
- Harness: `scripts/bench/nd6_bench.mjs` — `node --expose-gc
  scripts/bench/nd6_bench.mjs --phase A|B|C|D --rounds 15 --warmup 3`.
- Record arsip: `reports/nd6/zuu-2026111206{3944,3949,3955,4001}-0dcb418-*`
  (fase A/B/C/D-pre, tree `0dcb418`) dan
  `...064628/064642-bbee7bf-nd6-d-*` (D pasca-kandidat + konfirmasi,
  tree `bbee7bf`, saq-report `8c7f2d4`).
- Validator: `python scripts/measurement-schema/validate.py <record>` →
  PASS untuk keenam record.
- Analisis: `python scripts/analyze_measurement/main.py summary|compare`
  (legalitas perbandingan: kind/generator/site/host/corpus/library/preset
  harus sama — hash boleh beda).
- Desain & as-built: `docs/architecture/lazy-access-api.md` §12–14;
  audit: `docs/research/ondemand-direction-audit.md`.

---

## 11. Kata penutup

Direktif *"Scan the structure once. Access only what is needed."* terbukti
pada workload SAQ asli sebatas boundary repositori yang diukur: struktur
discan sekali (structural index ze_json), count dilakukan tanpa
materialisasi, dan string/field hanya di-decode bila benar-benar dibaca.
Speedup 2.85×/3.00× (≥ 1.5×) dicapai **tanpa mengubah** baseline, workload,
atau korpus — semua hasil berasal dari record tervalidasi yang dapat
direproduksi, dengan limitasi yang dilaporkan apa adanya.
