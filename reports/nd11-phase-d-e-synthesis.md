# ND-11 × ND-14 — Sintesis Phase D ↔ Phase E (audit bukti + rekalkulasi, tanpa eksperimen baru)

Tanggal: 2026-11-17. Sifat: **sintesis analitis** — semua angka direkalkulasi dari
record tervalidasi + exhibit mentah yang sudah ada; **tidak ada eksperimen baru**
yang dijalankan. Script: [`scripts/analyze_measurement/nd_d_e_synthesis.py`]
(../scripts/analyze_measurement/nd_d_e_synthesis.py) — CSV di
`out/charts/data/nd-*.csv`, figur di `out/charts/nd-de-*`, provenance byte-stabil
di `out/charts/data/nd-de-synthesis-provenance.json`. Rekonkiliusi terhadap record:
semua cocok (toleransi relatif 1e-5 untuk field record yang tersimpan
`toPrecision(6..9)`, 1e-9 untuk identitas exhibit) — tidak ada nilai yang
"disetel".

## 1. Ringkasan eksekutif

| Boundary | Site | Speedup (rasio median, dalam-run) | 95% CI (bootstrap ronde) | ze menang ronde | Signifikansi |
|---|---|---|---|---|---|
| **Phase D** — lapisan repository, jalur mongo-cache | dev (`6d87bf3`) | **2,880×** | 2,572–3,045 | 15/15 | p = 6,1e-5 (sign & Wilcoxon) |
| **Phase D** — lapisan repository, jalur mongo-cache | server (`8a1324b`) | **2,665×** | 2,508–2,857 | 15/15 | p = 6,1e-5 |
| **Phase E** — HTTP `GET /rekap` end-to-end | dev run 1 (`8556513`) | 1,076× | 0,935–1,147 | 9/15 | **tidak signifikan** (CI mencakup 1,0) |
| **Phase E** — HTTP end-to-end | dev re-run (`6979e3f`) | 1,041× | 0,974–1,114 | 10/15 | **tidak signifikan** |
| **Phase E** — HTTP end-to-end | server (`530f751`) | **1,134×** | 1,084–1,175 | 15/15 | p = 6,1e-5 |

- **Acceptance fase D (≥1,5×) tercapai di KEDUA site** — 2,88× (dev) dan
  2,67× (server) pada jalur mongo-cache bytes (`readCount()`), core 0.3.2,
  wasm `9795f2e8…` byte-identik kedua site.
- **Jalur file-store ≈ parity** — dev 0,953× (ze *kalah*, 7/15 ronde), server
  0,987× (6/15). Keunggulan fase D **spesifik jalur mongo-cache** (count
  atas bytes kanonik), bukan "parsing penuh"; jalur file-store terikat I/O.
- **Kompresi speedup di boundary HTTP** (indeks deskriptif C = S_D/S_E):
  dev 2,68× (run 1) / 2,77× (re-run); server 2,35×. Di boundary HTTP sisa
  keunggulan hanya 1,04–1,13×; di dev CI mencakup 1,0 (H0 tidak tertolak),
  di server signifikan.
- Pilot `ab255f5` (2 ronde × 3 request, speedup 0,866×) adalah **smoke test
  hardening harness** — bukan bukti acceptance, dilabel eksploratori.

## 2. Lingkup, sumber bukti, dan klasifikasi

Semua record di bawah lulus validator schema
(`scripts/measurement-schema/validate.py`) — audit penuh 2026-11-17: **67/67
record arsip PASS** (nd14, nd6-era, nd11, nd13, nd9, nd10, nd12, o2-1, o2-2).
Integritas arsip: 86 file raw diarsip; vs `out/raw/` — 1 byte-identik, 63
**EOL-normalized identik** (CRLF checkout vs LF asli; bukan korupsi), 22 tanpa
pasangan `out/raw` (pull era ND-10 langsung ke arsip). Exhibit tidak diubah
apa adanya.

| Kelas | Run | Isi |
|---|---|---|
| **primary** | `zuu-20261115080840-6d87bf3` (D dev), `server-lanjut-20261116060933-8a1324b` (D server), `zuu-20261116101458-8556513` (E dev run 1), `zuu-20261117000112-6979e3f` (E dev re-run), `server-lanjut-20261117003513-530f751` (E server) | dasar semua angka sintesis |
| **supporting** | `zuu-20261115010155-3376d07` (D dev, core 0.3.1) | sensitivitas versi |
| **pilot** | `zuu-20261116235636-ab255f5` (E dev, rounds=2, request_count=3) | smoke harness hardened; bukan bukti |
| **context/mechanism** | ND-8 `server-lanjut-20261113004520-714cbb9` (server D pre-O2 1,30×); ND-9 `zuu-20261113181631-4940f1d`, `server-lanjut-20261113181730-5a90545`; ND-13 `zuu-20261114113218-f6c3f3e`, `server-lanjut-20261116060747-8a1324b` | dekomposisi mekanisme |
| arsip historis | nd6-era 2026-11-12, nd10, nd12, o2-1, o2-2 | lini masa; tidak dipakai untuk angka sintesis |

Identitas lintas run: root `f5fd124`-era branch; saq-report per run — D dev
`8c7f2d4`, D server `8c7f2d4`, E dev run 1 `501cc03`, E dev re-run & server
`534d9a8`; ze_json `01a143f` (core 0.3.2, js 0.3.0, abi 2026000302); korpus
`saq_payload_v1` manifest sha `9f826c8a…`; store dev = mirror korpus anonim
(parity body `a18c7b4a…`), server = LIVE mongo `test` (parity `a6236b6c…`).

**Unit statistik = ronde pengukuran** (15 ronde/run). 300 request Phase E BUKAN
observasi independen — alternasi per-request `(r+k)%2` di satu sesi host; hanya
15 pasangan ronde yang membawa bobot inferensial. Perbandingan lintas site
adalah **narasi riset, bukan bukti** (host, commit saq-report, dan store
berbeda).

## 3. Protokol terkunci (koreksi dokumentasi)

Dibaca dari source harness `scripts/bench/nd11_phase_e.mjs` L423–431:

- Loop request: `for r in 1..15 { for k in 0..19 { engine = (r+k)%2 ? ze : v8 } }`
  → **20 request/ronde TOTAL = 10 v8 + 10 ze**; total **150 request/engine,
  300 request**; warmup untimed 3 request/jalur; tanpa trimming.
- Parity: **1 hash body unik untuk seluruh 300 request** (dev `a18c7b4a…`,
  server `a6236b6c…`; 47.888 byte; `parity.unique_response_hashes = 1`,
  `void = false`).
- `speedup_in_run` (harness) = `median(v8)/median(ze)` — konvensi yang dipakai
  sebagai angka utama di laporan ini.
- Statistik harness: `stddev` = populasi (ddof=0), `p95` = interpolasi linear
  (kedua harness; `nd6_bench.mjs` L137–152).

**Ambiguitas field `reps_per_round`** (akar salah baca dokumentasi):
- Phase D record extras `reps_per_round = 2` → artinya **2 repetisi per engine
  per ronde** (nilai ronde = `dt/reps`, mean dari 2 iterasi).
- Phase E record extras `reps_per_round = 20` (= config `iterations`) → artinya
  **20 request per ronde TOTAL lintas dua engine** (10/engine).
Dokumentasi lama yang menulis "20 request per engine" adalah salah baca dari
field ini; **raw/record tidak diubah retroaktif** — koreksi hanya di dokumen
(lihat §11).

## 4. Rekalkulasi Phase D — lapisan repository

Dari exhibit `raw_rounds[]{doc,path,reps,rounds_ms[15]}` (nilai ronde = mean
dari `reps` iterasi) + record. Pasangan per-ronde langsung antar array
(`nd6_bench.mjs --phase D`, 15 ronde, warmup 3, alternating rounds).

### 4.1 Jalur mongo-cache (bytes kanonik — jalur acceptance)

| Run | v8 median (ms) | ze median (ms) | Speedup | 95% CI | ze menang | p (sign = Wilcoxon) |
|---|---|---|---|---|---|---|
| dev 0.3.1 (`3376d07`, supporting) | 0,27935 | 0,11645 | 2,399× | 1,960–2,906 | 15/15 | 6,1e-5 |
| dev 0.3.2 (`6d87bf3`, primary) | 0,20435 | 0,07095 | **2,880×** | 2,572–3,045 | 15/15 | 6,1e-5 |
| server 0.3.2 (`8a1324b`, primary) | 0,21470 | 0,08055 | **2,665×** | 2,508–2,857 | 15/15 | 6,1e-5 |

p95 ratio: dev 3,253×; server 2,492×. Median paired-ratio per ronde (statistik
berbeda dari rasio median — keduanya dilabel di CSV): dev 2,850×, server
2,756×. CV dev tinggi (v8 27,1%, ze 34,3%) vs server (4,3% / 7,8%) — dev
konsisten bervariasi antar-sesi (lihat §10).

### 4.2 Jalur file-store (jalur `read()` penuh — I/O-bound)

| Run | v8 median (ms) | ze median (ms) | Speedup | ze menang | p |
|---|---|---|---|---|---|
| dev 0.3.1 | 5,26545 | 5,54525 | 0,950× | 8/15 | 1,00 |
| dev 0.3.2 | 4,03250 | 4,23320 | **0,953×** | 7/15 | 0,56 |
| server | 2,14080 | 2,16870 | **0,987×** | 6/15 | 0,61 |

Ze **kalah tipis di dev** (0,95×) dan parity di server (0,99×) — CI dev
0,767–1,109, server 0,971–1,039 mencakup 1,0. Tidak ada bukti keunggulan ze
pada jalur file-store di boundary D. Klaim "2,88×" TIDAK berlaku generik untuk
seluruh lapisan repository — hanya jalur mongo-cache.

### 4.3 Sensitivitas versi & drift antar-sesi (dev)

- Core 0.3.1 → 0.3.2: mongo-cache 2,399× → 2,880× (keduanya ≥1,5×); perbaikan
  datang dari sisi v8 baseline juga turun (0,2794 → 0,2044 ms, −27%) DAN ze
  turun lebih jauh (0,1165 → 0,0710 ms, −39%) — O2-2 (`interior fast skip`)
  memangkas ze, sementara kondisi sesi dev membaikkan baseline. Laporan
  [`nd14-post-o2-matrix.md`](nd14-post-o2-matrix.md) §7 mendokumentasikan
  koreksi drift ini secara eksplisit; angka lintas sesi dev **tidak boleh
  digabung** sebagai satu populasi.

## 5. Rekalkulasi Phase E — HTTP `GET /rekap` end-to-end

Dari exhibit per-request `requests{v8,ze}[{round,seconds,body_sha256}]`
(150/engine) + record; ronde median per engine → pasangan ronde.

| Run | v8 median | ze median | delta | Speedup (rasio median) | 95% CI | v8 CV | ze CV | ze menang | p sign | p Wilcoxon |
|---|---|---|---|---|---|---|---|---|---|---|
| dev run 1 (`8556513`) | 4,3969 ms | 4,08545 ms | 0,311 ms | 1,076× | 0,935–1,147 | 18,3% | 19,4% | 9/15 | 0,607 | 0,208 |
| dev re-run (`6979e3f`) | 4,1457 ms | 3,98425 ms | 0,161 ms | 1,041× | 0,974–1,114 | 27,0% | 21,8% | 10/15 | 0,302 | 0,107 |
| server (`530f751`) | 5,40115 ms | 4,76385 ms | 0,637 ms | **1,134×** | 1,084–1,175 | 6,9% | 9,4% | 15/15 | 6,1e-5 | 6,1e-5 |

- p95 ratio: dev run 1 1,035×; dev re-run 1,088×; server 1,115×.
- **Dev: H0 (null, proposal) tidak tertolak** — CI 95% mencakup 1,0 dan ze
  hanya menang 9–10/15 ronde. Tidak sah mengklaim "ze lebih cepat pada
  endpoint penuh di dev".
- **Server: signifikan** — ze menang 15/15 ronde, CI di atas 1,0. Outlier
  request v8 hingga 8,86 ms tetap dilaporkan (tanpa trimming; figur ECDF).
- Pilot `ab255f5`: rounds=2, per_round=3, warmup=2, speedup_in_run 0,866× —
  n total 6 request; ini shakedown harness hardened-coexistence (seed-guard,
  write-guard, bind loopback). Dikeluarkan dari semua tabel primary.

## 6. Indeks kompresi C = S_D / S_E (deskriptif)

| Site | S_D (mongo-cache) | S_E (HTTP) | C |
|---|---|---|---|
| dev (E run 1) | 2,880× | 1,076× | **2,68** |
| dev (E re-run) | 2,880× | 1,041× | **2,77** |
| server | 2,665× | 1,134× | **2,35** |

C **hanya indeks deskriptif**: S_D dan S_E diukur di boundary berbeda, run
berbeda, dan commit saq-report berbeda (S_D `8c7f2d4` vs S_E `501cc03`/
`534d9a8`). Bukan share waktu parser, bukan hasil pengukuran komponen.

**Batas aritmetika lintas boundary** — penjumlahan komponen D tidak
merekonstruksi delta E. Server: keunggulan D gabungan (file+mongo, v8−ze) =
(2,1408+0,2147) − (2,1687+0,08055) = **0,106 ms**, sedangkan delta E = 0,637
ms → aritmetika D hanya "menjelaskan" ~17% delta E. Dev: D gabungan justru
ze lebih lambat 0,067 ms, sementara delta E = 0,311 ms. Handler `/rekap`
memakai campuran `read()`/`readCount()` yang berbeda dari kedua jalur D yang
diisolasi, ditambah render EJS yang konsumsinya bergantung bentuk data —
sehingga **dekomposisi aditif lintas boundary tidak valid**; C dipakai hanya
sebagai ringkasan kompresi, bukan mekanisme.

## 7. Sintesis mekanisme D → E

Rantai bukti (semua dari laporan tereksekusi dengan run_id masing-masing):

1. **ND-9** — diagnosis biaya jalur count (`readCount()`): `s2-open`
   mendominasi ~88–90% per-op; biaya boundary JS/BigInt per panggilan ABI ≈ 0
   (`zuu-20261113181631-4940f1d`, `server-lanjut-20261113181730-5a90545`).
2. **ND-13** — dekomposisi `s2-open`: **scan 73–92%** dari sub-stage; share
   `match` server 17,5–23,6% vs dev 7,2–15,2% (`f6c3f3e`/`8a1324b`).
3. **O1 + O2** (slot reuse; interior fast skip, core 0.3.1→0.3.2) →
   ND-14: fase D mongo-cache dev 2,88×, server 2,67× — **acceptance ≥1,5×
   tercapai kedua site** (sebelum O2, ND-8 server hanya 1,30×, p95 1,46×,
   `714cbb9`).
4. **Phase E**: di boundary HTTP penuh (middleware → handler → 4 repo call →
   render EJS → respons), sisa keunggulan terkompresi ke 1,04–1,13×.

Interpretasi konsisten dengan data: waktu non-parser (middleware, render EJS,
serialisasi respons) mendominasi request penuh di KEDUA site; keunggulan
jalur count bytes kanonik (±0,1–0,14 ms/store-range per request, dari D)
hanya menyumbang sebagian kecil total. Di server sisa 1,13× masih terukur
signifikan karena variabilitas ronde rendah (CV 6,9–9,4%); di dev variabilitas
tinggi (CV 18–27%) membuat sisa 1,04–1,08× tidak dapat dibedakan dari nol.

## 8. Pemetaan RQ dan hipotesis (verbatim)

**Pertanyaan riset** ([`docs/project/plans.md`](../docs/project/plans.md) L15–24):

> - **RQ1** — Seberapa jauh performa `ze_json` (native + wasm64) berbeda dari baseline
>   `JSON.parse`/`JSON.stringify` V8 yang dipakai server SAQ, pada korpus kerja SAQ
>   yang riil?
> - **RQ2** — Bagaimana pengaruh **arsitektur sistem** (site: server SAQ vs device dev;
>   ISA: native x86-64 vs wasm64) terhadap hasil ukur yang setara?
> - **RQ3** — Optimasi apa yang berdampak terukur (berbasis paper) tanpa melanggar
>   kebenaran (validitas, kepatuhan JSON)?

**Hipotesis proposal** ([`thesis-proposal/pages/bab_1/007-hipotesis.typ`](../thesis-proposal/pages/bab_1/007-hipotesis.typ) L13–15, verbatim):

> **H₀** : Tidak terdapat perbedaan yang signifikan antara baseline JSON.parse bawaan runtime dan Parser JSON On-Demand ze_json terhadap latensi pemanggilan parser, throughput, dan konsumsi memori pada aplikasi pelaporan SAQ.
>
> **H₁** : Penerapan Parser JSON On-Demand ze_json pada aplikasi pelaporan SAQ menurunkan latensi pemanggilan parser (nanosecond dan ns/op) serta konsumsi memori secara signifikan dibandingkan baseline, dengan kenaikan beban prosesor yang terkendali, pada lingkungan pengujian tertutup dengan perangkat keras yang identik.

*(Catatan: proposal hanya memuat H₀/H₁; penomoran H1–H5 di
[`ondemand-saq-evaluation.md`](ondemand-saq-evaluation.md) adalah hipotesis
kerja turunan per-fase eksperimen on-demand, bukan teks proposal.)*

**Hipotesis kerja** (plans.md L26–28, verbatim):

> parser on-demand C++23/SIMD > V8 pada korpus besar dan read-only; pada payload kecil SAQ keunggulan bisa tertelan overhead boundary (wasm/ABI), bukan hilang di algoritme — ini diukur, bukan diasumsikan.

Status setelah sintesis ini:

| Item | Status | Bukti |
|---|---|---|
| RQ1 | **terjawab parsial** — keunggulan besar di jalur count bytes kanonik (D: 2,67–2,88×, kedua site, p=6,1e-5); tersisa 1,04–1,13× di HTTP end-to-end; jalur file-store parity (0,95–0,99×). wasm64 vs native belum dikontraskan di laporan ini (di luar lingkup D/E). | §4–§5 |
| RQ2 | **terjawab parsial** — hasil setara-protokol berbeda tajam antar site: D tercapai kedua site tapi magnitudo & variabilitas berbeda (dev CV 27–34% vs server 4–8%); E signifikan hanya di server. Lintas-site tetap narasi, bukan bukti kausal. | §4–§5, §10 |
| RQ3 | **didukung** — O1/O2 (slot reuse, interior fast skip) menaikkan server D dari 1,30× (ND-8) ke 2,67× (ND-14) tanpa melanggar parity/validator; arah optimasi selanjutnya konsisten dengan dekomposisi ND-13 (scan-dominan). | §7 |
| H₀ (proposal) | **tidak tertolak di boundary E dev** (CI mencakup 1,0); tertolak di D kedua site dan di E server (p=6,1e-5). Konsumsi memori & beban prosesor **belum diukur** di D/E — H₀/H₁ menyentuh tiga dimensi; dua di antaranya di luar lingkup laporan ini. | §4–§5 |
| H₁ (proposal) | **didukung parsial** — penurunan latensi signifikan pada jalur count (D); "lingkungan pengujian tertutup dengan perangkat keras yang identik" hanya terpenuhi dalam-run per site. | §4 |
| H1–H5 kerja (ND-7) | H1 verifikasi → diperkuat D 0.3.2; H2 tetap ditolak; H3 sebagian; H4/H5 tetap belum diukur (Phase E bukan uji `express.json()` body-parse). | ND-7 tabel |

## 9. Klaim yang didukung bukti (dan yang tidak)

| # | Klaim | Status | Bukti |
|---|---|---|---|
| 1 | Jalur `readCount()` bytes kanonik ≥1,5× di KEDUA site (core 0.3.2) | **didukung** — dev 2,880× (CI 2,57–3,05), server 2,665× (CI 2,51–2,86) | record `6d87bf3`/`8a1324b` D |
| 2 | Keunggulan berlaku untuk seluruh lapisan repository | **TIDAK didukung** — file-store 0,95×/0,99× (parity/kalah) | §4.2 |
| 3 | ze lebih cepat pada endpoint `/rekap` penuh | **didukung di server saja** (1,134×, 15/15, p=6,1e-5); di dev tidak signifikan (1,076×/1,041×, CI mencakup 1,0) | §5 |
| 4 | Kompresi speedup D→E ~2,3–2,8× (indeks deskriptif) | didukung sebagai deskriptif; bukan share parser, bukan mekanisme | §6 |
| 5 | Sisa keunggulan HTTP berasal langsung dari keunggulan jalur D (dekomposisi aditif) | **TIDAK didukung** — aritmetika lintas boundary tidak konsisten (§6); klaim kausal butuh eksperimen isolasi terpisah | §6 |

## 10. Threats to validity

1. **Satu run per sel** — semua CI/p-value mengukur variabilitas **antar-ronde
   dalam satu run**; tidak ada replikasi antar-run di server, dan dua run dev
   (E) menunjukkan sendiri bahwa antar-run dev bisa bergeser (1,076→1,041).
2. **Drift antar-sesi dev** — D dev 0.3.1 (pagi) vs 0.3.2 (siang): v8 −27%,
   ze −39% dalam ±7 jam pada host yang sama; dev high-load environment
   (laptop) membuat angka dev sensitif sesi.
3. **Lintas-site bukan eksperimen** — host (Ryzen 5 5500U vs i5-9400), commit
   saq-report, dan store (mirror anonim vs LIVE mongo) berbeda; hanya
   narasi RQ2.
4. **Korpus kecil** — 6 dokumen store (88.381 byte total; terbesar 39.209);
   parity body tunggal 47.888 byte (satu bentuk respons).
5. **Reps rendah** — Phase D 2 iterasi/ronde (nilai ronte = mean 2 sampel);
   Phase E 10 request/engine/ronde. Alternasi `(r+k)%2` merata antisipasi
   drift dalam-ronde, tapi tidak meniadakannya.
6. **Warm cache** — mongo-cache fase D = steady-state warm (seed dari korpus);
   jalur file-store menyertakan I/O nyata → dua jalur tidak setara termal.
7. **Uji non-parametrik n=15** — sign/Wilcoxon exact pada 15 pasangan
   memiliki daya terbatas; bootstrap percentile juga bias kecil pada n kecil.
8. **Coexistence** — run server E berjalan di host produksi dengan guard
   (bind loopback, WhatsApp off, write-guard, preflight counts); dev tidak
   memerlukan guard yang sama. Lingkungan tidak identik lintas site.

## 11. Koreksi dokumentasi & errata

Koreksi protokol "20 request/engine" → "20 request/ronde TOTAL (10 v8 +
10 ze); n=150/engine; 300 total" diterapkan pada:

| File | Lokasi | Koreksi |
|---|---|---|
| `reports/nd11-phase-e-dev.md` | §1 tabel protokol & §re-run | 20 request/ronde TOTAL; ambiguitas `reps_per_round` diberi catatan |
| `reports/nd11-phase-e-server.md` | §1 tabel protokol | idem |
| `reports/nd11-coexistence-audit.md` | §2 alur | idem |
| `docs/measurement/nd11-phase-e-http.md` | header status | "belum dieksekusi" → TEREKSEKUSI (dev 2026-11-16, server 2026-11-17) + taut laporan |
| `docs/measurement/nd11-phase-e-http.md` | §6 tabel sampel | "20 request/engine/ronde (n=150)" → "20 request/ronde TOTAL (10/engine); n=150/engine" |
| `docs/project/tasks.md` | ND-11 Phase E | idem |
| `reports/README.md` | indeks | tambah entri laporan sintesis ini |
| `CHANGELOG.md` | — | entri sintesis |

Tidak ada raw exhibit/record yang diubah retroaktif; koreksi hanya dokumen.

## 12. Kesimpulan audit

- 67/67 record arsip lulus validator; integritas arsip sehat (perbedaan byte
  = line-ending; 22 exhibit era ND-10 disimpan langsung di arsip).
- Rekalkulasi independen 5 run primary + 1 supporting + 6 exhibit konteks
  A/B/C: **semua nilai cocok dengan record** (tol 1e-5 record / 1e-9 exhibit).
- Script analisis deterministik: rerun menghasilkan CSV/PNG/SVG byte-identik
  (seed bootstrap 20261117, `svg.hashsalt` dipin, metadata tanggal dimatikan).
- Acceptance fase D ≥1,5× **tercapai di kedua site** pada jalur mongo-cache;
  Phase E mengkarakterisasi sisa keunggulan di boundary HTTP: signifikan di
  server (1,13×), tidak signifikan di dev — dan keunggulan tidak generik di
  lapisan repository (file-store parity).
- Untuk klaim kausal "sisa keunggulan HTTP berasal dari X", eksperimen
  isolasi terpisah diperlukan; laporan ini sengaja tidak membuat klaim
  semacam itu.

## Lampiran — artefak & reproduksi

```
python scripts/analyze_measurement/nd_d_e_synthesis.py          # -> out/charts (exit 0 = rekonsiliasi match)
python scripts/analyze_measurement/nd_d_e_synthesis.py --archive reports/charts   # salin CSV+SVG+provenance ke arsip
```

- CSV: `out/charts/data/nd-de-inventory.csv`, `nd-phase-d-stats.csv`,
  `nd-phase-d-paired.csv`, `nd-phase-e-stats.csv`, `nd-phase-e-paired.csv`,
  `nd-phase-abcd-stats.csv`, `nd-de-inference.csv`, `nd-de-compression.csv`,
  `nd-de-synthesis-provenance.json` (hash sha256 semua input).
- Figur: `out/charts/nd-de-speedup-comparison.{png,svg}`,
  `nd-de-phase-e-distribution.{png,svg}`, `nd-de-paired-rounds.{png,svg}`,
  `nd-de-compression.{png,svg}`, `fig1-architecture.mmd` (Mermaid).
  PNG (≥300 DPI) diregenerasi deterministik setiap rerun di `out/charts/`;
  arsip repo (`reports/charts/`) menyimpan **versi vektor SVG** — PNG arsip
  diabaikan `.gitignore` repo (tidak diubah untuk tugas ini).
- Metode: bootstrap ronde-berpasangan B=10.000 seed 20261117 (persentil);
  sign test eksak; Wilcoxon exact dua-arah — unit = ronde; 300 request bukan
  observasi independen.
- Indeks C deskriptif; tidak dipakai sebagai klaim kausal (§6).
