# ND-14 — Matriks ND-6 pasca-O2 (dev tereksekusi; server pending)

Tanggal: 2026-11-15. Re-measure matriks 4 fase ND-6 di atas core **0.3.1**
(O2-1 interior fast skip, wasm `1d8960c9…`) — pola ND-12 (pasca-O1).
Pertanyaan acceptance: **rasio fase D ≥1,5× per site** (AGENTS §6).

## 1. Identitas run (dev, tree bersih)

| Fase | run_id | validator |
|---|---|---|
| A | `zuu-20261115005811-3376d07` | PASS |
| B | `zuu-20261115010151-3376d07` | PASS |
| C | `zuu-20261115010153-3376d07` | PASS |
| D | `zuu-20261115010155-3376d07` | PASS |

Semua: `site=dev_device`, 15 ronde, warmup 3, korpus `saq_payload_v1`
(manifest sha identik ND-12), root `3376d07` / ze_json `0aacd82`
(core 0.3.1, `core/0.3.1`) / saq-report `8c7f2d4`. Arsip
`reports/nd14/` + sidecar `reports/registry/` (4 run, source=record).

## 2. Fase D — **ACCEPTANCE DEV TERCAPAI**

| metrik | ND-12 (0.2-era, wasm `c5b2b7d…`) | ND-14 (0.3.1) |
|---|---:|---:|
| **mongo-cache v8/ze** | 1,48× | **2,40× ✓** |
| file-store v8/ze | 0,81× | 0,95× |
| mongo-cache-ze (absolut) | 0,1404 ms | 0,1164 ms |
| mongo-cache-v8 (absolut) | 0,2084 ms | 0,2793 ms |

- Rasio dalam-run **2,40× ≥ 1,5×** — kriteria acceptance terpenuhi di dev.
- **Koreksi drift**: v8-side drift +34% lintas window (0,2084→0,2793) sementara
  ze-side turun −17,1% (efek O2-1 yang dicari). Dengan v8 baseline ND-12:
  0,2084/0,1164 = **1,79×** — tetap ≥1,5× tanpa andil drift. ✓
- file-store tetap <1× (0,95×): jalur ze membayar kanonikalisasi + copy;
  window file-store hari ini COLD (0,526→5,265 ms v8, 10× — page cache
  hilang; angka absolut lintas-window file-store tidak sebanding).

## 3. Fase A/B/C — rasio dalam-run (sah; delta absolut lintas-window = noise)

Konfounder dinyatakan: lintas-window, SEMUA entri fase A turun 26–57%
(kedua engine — window lebih cepat) dan SEMUA entri fase B naik 22–119%
(kedua engine — window lebih lambat). Delta absolut lintas-window tidak
diinterpretasi; hanya rasio dalam-run (pola ND-12).

| fase | pasangan | ND-12 → ND-14 (per dokumen) | bacaan |
|---|---|---|---|
| A | v8-parse / ze-parse | 0,04–0,07× → 0,04–0,05× | stabil; materialisasi penuh tetap kalah — O2-1 terdilusi di jalur full-decode (scan kecil vs decode/materialisasi) |
| B | v8-selective / ze-project-selective | 0,12–0,16× → 0,08–0,13× | window noise; mekanisme L2-project tak berubah |
| C | v8-selective / ze-l1-traversal | schedules **0,90× → 1,50×**; courses 0,72→0,79; lecturers 0,79→0,85; assistants 1,05→1,03; reports 0,30→0,27; globalConfig 0,06→0,05 | campuran; schedules membaik jelas, lainnya dalam noise |
| D | mongo-cache v8/ze | 1,48× → **2,40×** | **acceptance ✓** (koreksi drift 1,79×) |

## 4. Keputusan O2-2 (histogram interior — GO terbatas)

`scripts/corpus/interior_histogram.py` (mesin state string identik
`scanner8`; guard manifest):

```
corpus              ints  intBytes  p50  p90  max  bw_p50  >=8B share
checker_batch        330      1704    1   10   83      10      61.0%
saq_payload_v1      3932     55758   11   24   83      24      91.0%
synthetic_100k      6820     42147    5    9  174       6      34.2%
synthetic_10k        671      4374    6   10  226       6      37.8%
synthetic_1k          47       660    6   11  350     350      72.3%
synthetic_1mb      69686    428978    5    9  131       6      34.0%
```

- Korpus acceptance (`saq_payload_v1`): byte-weighted p50 = **24 B**,
  91,0% byte interior hidup di run ≥8 B → **SWAR menang di mayoritas
  byte yang menentukan metrik**.
- Korpus synthetic: bw_p50 = 6 B, 34% ≥8 B → SWAR berisiko regress di
  gbench ladder (interior pendek, key-dominated).
- **Keputusan: GO terbatas** — implementasi O2-2 diukur, diterima hanya
  bila `saq_payload_v1` menang dan synthetic tidak regress melebihi
  noise (aturan "terima hanya jika menang", O1-9/C1).

## 5. Batas klaim

- Bukti rasio = dalam satu run_id per fase (AGENTS §4); delta absolut
  lintas-window dinyatakan noise (bukti konfounded, bagian §3).
- Site dev saja; server menyusul (sesi terpadu ND-13+ND-14 saat
  reachable) — acceptance server (baseline 1,13× era O1) adalah
  pertanyaan terbuka berikutnya.
- Fase D tetap lapisan repository (bukan HTTP end-to-end) — klaim
  "endpoint produksi" tetap menunggu ND-11 (Senin).

## 6. Deliverables

- 4 record tervalidasi + arsip + sidecar; sinkronisasi tasks/plans.
- Keputusan O2-2 GO terbatas (§4) tercatat di tasks.md.
- @cite: `10.1002_spe.3313` (provenance per-run), `10.14778_3115404.3115416`
  (Mison — dasar jalur on-demand yang diukur).
