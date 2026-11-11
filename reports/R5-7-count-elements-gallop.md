# R5-7 — O1-8: Gallop `first_index_at_or_after` (Kuadratik `ze_count_elements` Diperbaiki)

Eksperimen lanjutan siklus O1: **poin 2** keputusan pemilik ("fix kuadratik
`ze_count_elements` via gallop"). Satu perubahan per pengukuran; perubahan
satu file C++ (`src/ondemand/document.cpp`), tanpa perubahan ABI/binding.

## 1. Bug (temuan O1-6, tetap hidup setelah O1-6)

`ze_count_elements` (`cabi.cpp:444`) mem-frames Value dengan
`frame_value(doc, token_start, 0)` — `index_cursor_ = 0` — lalu
`begin_array`/`begin_object`/`operator*` memanggil
`first_index_at_or_after` yang berjalan **linear dari index 0** ke posisi
kontainer. Agregat = O(#containers × #indexes) per pemanggilan
`count_elements`. Jalur parse (`#readArray`/`#readObject`) tidak lagi
memanggil `countElements` sejak O1-6, jadi bug hidup untuk pemanggil
API publik lain (`countElements()` wrapper + tooling).

## 2. Fix: gallop (probe eksponensial + binary dalam bracket)

`first_index_at_or_after` sekarang dua rezim dengan jawaban identik di
atas index array sorted:

- **Posisi step (hot path)**: `index_at(cursor) >= byte_pos` → kembali
  langsung — dua komparasi, sama persis dengan while lama (O(1)).
- **Re-derivasi (gap > 0)**: gallop `cursor+1, +2, +4, …` sampai melewati
  batas, lalu binary search dalam bracket — O(log distance), bukan
  O(distance).

Gap kecil (1–3, pola mayoritas pemanggil walk) tetap 1–3 komparasi; yang
berubah drastis hanya kasus jauh (cursor=0): 684.7 ms → 11.6 ms per pass
(lihat §4). Komentar Doxygen fungsi menjelaskan dua rezim + dasar
TASKS O1-8; bukan teknik paper — tanpa `@cite`.

## 3. Gerbang kebenaran

- `native-release`: ctest **6/6** PASS; `native-sanitize` (ASan/UBSan):
  ctest **6/6** PASS.
- JS: smoke PASS; differential **71 dokumen × 5 scanner mode + parser/
  tree parity vs `JSON.parse`** — semua agree.
- Wasm artifact: rebuild `wasm64-release` → sha256 **`35b7f773…`**
  (BASE = `7e26044f…`).

## 4. Bukti: probe informal + sandwich

**Probe informal `countElements`** (Bukan record; artifact-swap A/B,
synthetic_1mb — 157.195 index, 19.448 kontainer: 9.724 object + 9.724
array; enumerasi via structural index; 5 pass terukur):

| sisi | wasm | ms/pass (19.448 `countElements`) |
|---|---|---|
| BASE | `7e26044f…` | 684.7 |
| CAND | `35b7f773…` | **11.6** |

**59.2×**; counts **identik** per kontainer antar sisi (identitas jawaban
terverifikasi, bukan cuma kecepatan).

**Sandwich** 2 window dev, 6 pasang BASE↔CAND swap artifact-only, 6
korpus, **72 record PASS** validator (`out/measurements/zuu-2026111123{0426,0435,0444,0452,0501,0510,0623,0632,0641,0649,0658,0707}-*`):

| korpus | BASE MB/s | CAND MB/s | cand/base |
|---|---|---|---|
| synthetic_1k | 14.9 | 14.7 | 0.986 |
| synthetic_10k | 9.9 | 9.9 | 0.993 |
| synthetic_100k | 9.2 | 9.1 | 0.993 |
| synthetic_1mb | 9.2 | 9.2 | 0.998 |
| saq_payload_v1 | 19.8 | 19.5 | 0.984 |
| checker_batch | 7.7 | 7.7 | 0.995 |

Sebaran per-pair **0.950–1.023** (window 1: 1k 0.976–0.989, saq pair-1 =
0.965; window 2: 1k 1.001–1.002, saq pair-6 = 1.023 — melintasi 1.0 ke
dua arah); nilai base/cand saling tumpang tindih per korpus (1k: base
14.6–15.2 vs cand 14.6–15.0). Pola ini = envelope noise mesin (drift
±2% antar pasangan, konsisten dengan pengamatan O1-3/R5-4), bukan sinyal
regresi: jalur parse yang diukur tidak memanggil `ze_count_elements`
sama sekali (sejak O1-6), dan hot-path O(1)-nya tidak berubah.
**Keputusan: diterima** — fix bug wajib (O1-8), kompleksitas
diperbaiki (O(distance) → O(log distance)), tanpa regresi bermakna.

## 5. Provenance & keputusan

- ze_json PR #29 (`a6e1d5c`) merged `c1c91ce` (branch
  `perf/first-index-gallop`).
- wasm artifact working tree = `35b7f773…`; BASE tersimpan
  `%TEMP%/opencode/wasm_base.wasm` (`7e26044f…`), CAND di
  `wasm_o18_cand.wasm` (+ `wasm_cand.wasm` ditimpa dengannya — nama lama
  R5-5 yang stale).
- Probe: `r5_7_count_probe.mjs` + hasil `r5_7_probe_{base,cand}.json`
  (temp); komparator `r5_1_compare.py`, `r5_7_pairs.py`.
- Site: `dev_device`; semua perbandingan in-situ satu sesi; 72 record
  sandwich dipertahankan (exhibit kanonik).
