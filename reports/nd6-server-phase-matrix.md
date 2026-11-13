# ND-8 — Matriks Fase A–D ND-6 di Server SAQ (`saq_server`, `714cbb9`)

Eksekusi server: pemilik, 2026-11-13 (batch 00:24–00:45 UTC), mengikuti
protokol `docs/measurement/nd6-benchmark-plan.md` §2–§6 (15 ronde, warmup 3,
alternating, tanpa trimming, GC minor/major 0/0 di semua fase). Matriks ND-6
yang di dev menghasilkan verdict 2.85×/3.00× (plan doc §10) dijalankan ulang
di site server dengan runner & korpus identik — ini eksekusi pertama matriks
ND-6 di `saq_server`.

**Verdict server: acceptance ≥1.5× TIDAK tercapai** — Fase D jalur produksi
(cache Mongo) hanya **1.30×** (p95 1.46×). Verdict dev tetap sah sebagai
bukti dalam-run; angka lintas situs adalah **narasi riset, bukan bukti**
(protokol §9). Laporan ini mendokumentasikan temuan transferabilitas RQ2.

## 1. Run yang masuk

| run_id | provenance | isi | site |
|---|---|---|---|
| `server-lanjut-20261113002437-8c7f2d4` | saq_report `8c7f2d4` | harness V8: 3 konteks × 6 korpus | saq_server |
| `server-lanjut-20261113002518-d9e25ac` | ze_json `d9e25ac` (lib 0.1.2) | harness ze-parser: open/walk/full × 6 korpus | saq_server |
| `server-lanjut-20261113004447-714cbb9` | root `714cbb9-dirty`, ze_json `d9e25ac`, saq-report `8c7f2d4` | ND-6 fase A | saq_server |
| `server-lanjut-20261113004501-714cbb9` | idem | ND-6 fase B | saq_server |
| `server-lanjut-20261113004510-714cbb9` | idem | ND-6 fase C | saq_server |
| `server-lanjut-20261113004520-714cbb9` | idem | ND-6 fase D (acceptance) | saq_server |

- Record: **10/10 PASS** validator (6 harness + 4 ND-6); raw exhibit
  `out/raw/<run_id>/`, record `out/measurements/<run_id>-*.record.json`.
- Host server: `server-lanjut`, i5-9400 @2.90 GHz, **Node v26.13.0
  (V8 14.6.202.34-node.40)** — identik dengan eksekusi P5/R5 (Node 26 sejak
  awal di server). Dev pembanding: Ryzen 5 5500U, Node v24.19.0 (V8 13.6).
- Korpus `saq_payload_v1` sha256 manifest
  `9f826c8a0afbe67deb4bde57d9fe411e4b67ad6cc218988fb3393add221d66a1` ==
  manifest dev — korpus byte-exact ✓.
- **Catatan kepatuhan**: root workspace server `dirty=true` (tercatat
  `git_commit.hash = 714cbb9-dirty`); protokol §3.9 mensyaratkan tree
  bersih — deviasi tercatat, re-run dari tree bersih direkomendasikan untuk
  run konfirmasi. Bug kosmetik harness saat eksekusi: nama file record
  meng-hardcode suffix `-dev_device` (field `site` di dalam record benar
  `saq_server`) — sudah diperbaiki (`fix(harness)`, `${SITE}`).

## 2. Fase D — acceptance (median ms/op, speedup = T_v8/T_ze)

| Jalur | v8 | ze | Speedup (median / p95) | Dev (pembanding) |
|---|---|---|---|---|
| mongo-cache (produksi) | 0.2255 | 0.1728 | **1.30× / 1.46×** | **2.85×/3.00×** (p95 2.10×/2.14×) |
| file-store (fallback) | 2.1793 | 2.2911 | 0.95× / 0.90× | 0.91× (konsisten — I/O-bound) |

**Acceptance ≥1.5× gagal di site ini.** Jalur ze tetap lebih cepat (>1×),
tetapi margin 1.30× di bawah target, dan p95 1.46× juga di bawah.

## 3. Matriks diagnostik A–C (median ms/op; speedup = v8/ze)

| Fase | Store | v8 | ze | Speedup | Dev |
|---|---|---|---|---|---|
| A `v8-parse` vs `ze-parse` | courses | 0.0068 | 0.1920 | 0.035× | 0.04× |
| | assistants | 0.0099 | 0.2611 | 0.038× | 0.05× |
| | lecturers | 0.0062 | 0.1647 | 0.038× | 0.04× |
| | schedules | 0.0652 | 1.7236 | 0.038× | 0.05× |
| | reports | 0.0506 | 1.3047 | 0.039× | 0.05× |
| | globalConfig | 0.0009 | 0.0256 | 0.035× | 0.06× |
| B `v8-selective` vs `ze-project` | courses | 0.0087 | 0.1214 | 0.072× | 0.10× |
| | assistants | 0.0118 | 0.1650 | 0.072× | 0.09× |
| | lecturers | 0.0072 | 0.1294 | 0.056× | 0.08× |
| | schedules | 0.0682 | 0.8384 | 0.081× | 0.09× |
| | reports | 0.0528 | 0.6136 | 0.086× | 0.11× |
| | globalConfig | 0.0018 | 0.0198 | 0.091× | 0.10× |
| C `v8-selective` vs `ze-l1` | courses | 0.0093 | 0.0154 | 0.60× | 0.93× |
| | assistants | 0.0123 | 0.0169 | 0.73× | **1.50×** |
| | lecturers | 0.0071 | 0.0122 | 0.58× | 0.92× |
| | schedules | 0.0699 | 0.0912 | 0.77× | **1.57×** |
| | reports | 0.0538 | 0.2698 | 0.20× | 0.26× |
| | globalConfig | 0.0018 | 0.0579 | 0.03× | 0.06× |

Pola identik dengan dev pada arah besar (A: materialisasi penuh 26–28× di
bawah V8; B: L2 kalah semua ukuran SAQ), tetapi **fase C berbalik**: dua
kemenangan L1 di dev (schedules 1.57×, assistants 1.50×) hilang di server —
ze-l1 kalah di semua store.

## 4. Harness P5-style di server (in-situ, satu konteks per run)

| Konteks | Engine | ms/op (median) |
|---|---|---|
| `body-parse` (express.json) | V8 | 0.143 |
| `store-read` | V8 | 0.141 |
| `export-stringify` | V8 | 0.149 |
| `wasm-open` | ze wasm64 | 0.202 |
| `wasm-walk-full` | ze wasm64 | 1.639 |
| `wasm-parse-full` | ze wasm64 | 3.704 |

Konsisten dengan fase A (full materialize korpus 88 KB ≈ 3.7 ms ze vs
0.14 ms V8 ≈ 26×).

## 5. Dekomposisi gerakan komponen (median, dev → server)

| Komponen | Perubahan | Arti |
|---|---|---|
| v8-parse / v8-selective / v8 mongo-cache | **−30…−44%** (semua) | baseline V8 jauh membaik (searah Node 26 / V8 14.6) |
| ze-parse (A, one-shot besar) | −13…−22% | wasm path membaik di jalur materialisasi |
| ze-project (B) | −5…−29% | campur |
| **ze-l1 (C, per-panggilan ABI)** | **+39% (assistants), +41% (schedules), +6…+8% (lecturers/courses)** | jalur dominan per-panggilan ABI justru **mundur** |
| D mongo-cache ze | **+33…+35%** | idem — structural count dibayar per panggilan ABI |

**Interpretasi (narasi, bukan klaim kausal):** rasio terkompresi di semua
fase karena baseline V8 membaik lebih besar daripada jalur wasm64; pada
jalur yang didominasi biaya per-panggilan ABI (boxing u64 lintas boundary —
`ze_json/docs/architecture/wasm-abi.md`; model biaya
`docs/architecture/lazy-access-api.md` §13), jalur ze bahkan absolut
memburuk. Dua variabel berubah sekaligus (mesin + versi runtime Node 24→26),
sehingga **penyebab tunggal belum dapat diklaim** — isolasi satu variabel
(discipline one-change-per-experiment) diperlukan sebelum atribusi.

## 6. Atribusi bottleneck & kandidat (prosedur plan doc §7)

D <1.5× → matriks A–C memutuskan: pada ukuran dokumen SAQ (3.6–39 KB),
biaya **open arena + boxing ABI per panggilan** mendominasi jalur ze, dan
di site server margin tersebut relatif memburuk vs baseline V8 yang lebih
cepat. Kandidat yang sudah disediakan protokol (wajib diukur ulang — O1-11):

1. **Reuse slot / open amortization** — `readCount()` sole-owner membayar
   open penuh (structural scan + carve arena 3×src_size×8 —
   `ze_json/docs/architecture/ondemand-parser.md`) per store per request;
   reuse slot di antara request menyangkal bagian ini (perhatian: kontrak
   lifetime §4.2 `lazy-access-api.md`).
2. **ABI v4 batch / proyeksi C++-side satu-panggilan** — memotong boxing
   per field/panggilan step (hipotesis §13.3, terbuka).
3. **Lazy decode** — relevan bila decode string dominan (belum terprofilkan
   di site server).

## 7. Limitasi jujur

1. Root workspace server `dirty` (§3.9 dilanggar; tercatat di record) —
   re-run konfirmasi dari tree bersih direkomendasikan.
2. Dua variabel berubah vs dev (mesin + versi Node) — kovariasi belum
   diputus; perbandingan lintas situs = narasi riset (§9).
3. Bug penamaan file record (suffix `-dev_device`) saat batch ini — field
   `site` di dalam record tetap sahih; harness sudah diperbaiki.
4. H4/H5 (body-parse server utuh, end-to-end handler) tetap belum diuji —
   fase D tetap melalui lapisan repositori, bukan HTTP handler penuh.
5. sha256 artefakt `ze_json.wasm` sisi server tidak terekam di metadata
   batch ini (sidecar `build-wasm.ps1` ada; catat pada run berikutnya).
