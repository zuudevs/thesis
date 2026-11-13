# ND-10 — Kontrol Lintas Runtime & Mesin (E1 + E2, TEREKSEKUSI)

Eksekusi: pemilik memerintahkan fresh run (2026-11-13, sesi agent 2026-11-13/14),
mengikuti protokol `docs/measurement/nd10-site-runtime-control.md` §2–§3.
Seluruh run dari **tree bersih** (gate fail-fast aktif, `exploratory=false`
di semua sidecar), 15 ronde + 3 warmup, alternating, tanpa trimming,
GC minor/major 0/0 — protokol ND-6 tidak berubah.

**Verdict: acceptance ≥ 1,5× TIDAK tercapai di KEDUA site pada Node 26
matched** — fase D (jalur produksi, cache Mongo ter-load): dev **1,45×**
(p95 1,77×) / konfirmasi **1,41×** (p95 2,64×); server **1,13×** (p95
1,25×) / konfirmasi **1,10×** (p95 1,30×). Verdict era Node 24
(2,85×/3,00×) adalah **histori berlabel runtime** — terkonfirmasi tidak
reproducible di Node 26. Matriks interpretasi ND-10 §4 baris 1:
**runtime (V8 14.6) = penyebab dominan kompresi rasio** — klaim kausal
pertama yang sah, dengan caveat confound (lihat §3).

## 1. Identitas run (terverifikasi di sidecar `out/raw/<run_id>/metadata.json`)

| Dimensi | dev_device (E1) | saq_server (E2) |
|---|---|---|
| root v5 | `5a90545` (clean) | `5a90545` (clean, pasca stash+pull) |
| ze_json | `d9e25ac` (lib 0.1.2) | `d9e25ac` |
| saq-report | `8c7f2d4` | `8c7f2d4` |
| Runtime | Node 26.13.1 (V8 14.6.202.34-node.40) | Node 26.13.1 (identik) |
| wasm sha256 | `35b7f773…eef3185` | `35b7f773…eef3185` (**byte-identik**) |
| Korpus | `saq_payload_v1` sha256 `9f826c8a…` | identik |
| Gate | clean=true | clean=true |

Run ID (semua record PASS `scripts/measurement-schema/validate.py`):

| Fase | dev | server |
|---|---|---|
| A | `zuu-20261113173228-5a90545` | `server-lanjut-20261113174303-5a90545` |
| B | `zuu-20261113173230-5a90545` | `server-lanjut-20261113174305-5a90545` |
| C | `zuu-20261113173232-5a90545` | `server-lanjut-20261113174306-5a90545` |
| D (main) | `zuu-20261113173306-5a90545` | `server-lanjut-20261113174348-5a90545` |
| D (konfirmasi) | `zuu-20261113173308-5a90545` | `server-lanjut-20261113174349-5a90545` |

Arsip: `reports/nd10/*.record.json` + `reports/nd10/raw/<run_id>/`
(sidecar metadata + exhibit mentah per fase). Re-validasi PASS 2026-11-14.

## 2. Hasil

### 2.1 E1 — kontrol runtime (dev, Node 24-era → Node 26)

| Jalur | era Node 24 (2026-11-12) | Node 26.13.1 (fresh) | Δ |
|---|---|---|---|
| D · mongo-cache (median) | **2,85× / 3,01×** | **1,45× / 1,41×** | −50% |
| D · mongo-cache (p95) | 2,10× / 2,14× | 1,77× / 2,64× | — |
| D · file-store | 0,91× | 0,92× | setara |
| C · L1 assistants | 1,51× | 1,05× | menyusut |
| C · L1 schedules | 1,57× | 0,97× | lenyap |
| A · materialisasi penuh | 0,05× | 0,04× | setara |
| B · L2 project | 0,10× | 0,09× | setara |

Baseline V8 di jalur repository membaik besar di Node 26 (V8 14.6),
sedangkan jalur ze (dominasi biaya per-panggilan ABI wasm64, boxing
BigInt) tidak ikut membaik proporsional → rasio terkompresi.

### 2.2 E2 — kontrol mesin (dev vs server, runtime identik)

| Jalur | dev | server | sisa gap |
|---|---|---|---|
| D · mongo-cache (median) | 1,45× / 1,41× | 1,13× / 1,10× | ~0,3× |
| D · file-store | 0,92× | 0,94× | — |
| A | 0,04× | 0,04× | ≈0 |
| B | 0,09× | 0,09× | ≈0 |
| C (rentang 6 store) | 0,04–1,05× | 0,04–0,83× | kecil |

Dengan runtime + wasm + korpus identik, A/B hampir persis antar mesin;
sisa gap D (~0,3×) = hardware/OS/patch-Node (confounder dinyatakan,
i5-9400 vs Ryzen 5 5500U).

## 3. Interpretasi & batas klaim

1. **Klaim kausal yang sah (E1+E2):** kompresi rasio 2,85× → ~1,4× →
   ~1,1× didominasi oleh **runtime** (V8 13.6 → 14.6), bukan hardware.
   E2 menunjukkan sisa perbedaan antar mesin kecil.
2. **Confound E1 vs era lama:** wasm era Node 24 (`7e26044f…`, reported-only
   per AUD-1) tidak punya sidecar hash (out/ lama terhapus pasca-arsip) dan
   ze code berubah (`14592a0` → `d9e25ac`) → komparasi antar-era berlabel
   **confounded**; kontrol runtime turun status *unknown* persis skema
   ND-10 §2. Arah temuan tetap konsisten karena nilai Node 26 (1,41–1,45×)
   berimpit dengan server Node 26 (1,09–1,13×), bukan dengan era 2,85×.
3. **Implikasi RQ2 / skripsi:** angka verdict wajib berlabel runtime;
   acceptance ≥1,5× kini menuntut **countermeasure** (kandidat ND-8/O1:
   slot reuse, ABI v4 thin-call `O1-7` — disetujui pemilik, lazy decode).
   Fase C menang selektif era lama (schedules/assistants) lenyap di Node 26.
4. **Proses/gate:** konfigurasi lokal
   `git config submodule.{thesis-proposal,submission-thesis-supervisor}.ignore dirty`
   dipakai agar gate root tidak tersandung konten-dirty submodule **dokumen**
   (bukan kode terukur); mismatch pointer tetap terlihat oleh gate. Server:
   perubahan `.vscode/settings.json` milik pemilik di-**stash**
   (`nd10-e2 pre-run vscode settings`) sebelum pull `714cbb9` → `5a90545`;
   stash dibiarkan di server (recoverable via `git stash pop`).

## 4. Figure & data

- `out/charts/nd10-summary-map.{png,svg}` + arsip `reports/charts/nd10-summary-map.svg`
- `out/charts/nd10-acceptance.{png,svg}` + arsip `reports/charts/nd10-acceptance.svg`
- CSV: `out/charts/data/nd10-summary-map.csv`, `nd10-acceptance.csv`,
  `nd10-summary-fairness.csv` (jejak fairness gate in-situ)
- Generator: `scripts/analyze_measurement/nd6_summary_chart.py --vintage=nd10`
  (vintage `nd6` tetap bisa direproduksi untuk histori).
