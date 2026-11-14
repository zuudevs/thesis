# ND-13 — Dekomposisi sub-stage `s2-open` (dev tereksekusi; server pending)

Eksekusi: lanjutan instruksi pemilik "lanjut s2-open dulu" (2026-11-14).
Menjawab pertanyaan terbuka ND-9: di dalam 0,14–0,19 ms per `ze_parser_open`
(dokumen SAQ 3,6–39 KB) — yang mana dominan: **carve** arena
(`bump_aligned(3×len×8+64)`), **scan** struktural (`structural_scan` →
scanner8), atau **match** (pass pairing LIFO)? Jawabannya menentukan arah
optimasi fase D (varian scanner? mikro-opt match? reuse arena?) — setelah
thin-call terbantahkan ND-9.

## 0. Desain (kenapa ekspor, bukan timer in-module)

wasm64 freestanding (`-nostdlib`, tanpa libc) **tidak punya clock in-module**
— timer `steady_clock` mustahil. Dekomposisi karenanya lewat **ekspor
standalone setara** yang diukur clock JS harness (protokol identik ND-9,
ditempel di harness `nd9_cost_diagnosis.mjs --probe`):

| Sub-stage | Panggilan setara | Catatan kesetaraan |
|---|---|---|
| `s2a-carve` | `ze_alloc(3*len*8 + 64)` | footprint persis yang di-carve `ze_parser_open` (cabi.cpp L224); `bump_aligned` O(1) — state bentuknya sama |
| `s2b-scan` | `ze_scanner8(src,len,dst)` | scanner yang sama persis yang di-dispatch `Document::open` (static dispatch → scanner8) |
| `s2c-match` | `ze_match_pass(...)` **(ABI v5 baru)** | loop pairing diekstrak dari `Document::open` jadi `ondemand::match_pass` — **satu sumber**: fused open memanggilnya in place, ekspor me-replay-nya |

Fused `s2-open` tetap diukur penuh sebagai **bound produksi**; tiga sub-stage
dilaporkan **berdampingan** (proxy lower-bound + satu call boundary masing-
masing), **tidak pernah force-subtract**. Semua dalam satu run_id per site —
rasio hanya dihitung dalam run.

Keputusan yang menyertai: bump core `0.2.0 → 0.3.0` + js `0.3.0` (ekspor
additive = MINOR, AGENTS §9), tag `core/0.3.0` + `js/0.3.0` di merge commit
`22e939c` (PR ze_json #42); `ze_abi_version()` kini `2026000300`; gate
`scripts/build-wasm.ps1` tuntut 26 ekspor (v5).

## 1. Identitas run (dev)

| Sifat | Nilai |
|---|---|
| run_id | `zuu-20261114113218-f6c3f3e` |
| root / ze_json / saq-report | `f6c3f3e` (branch `feat/nd13-open-decomposition`, tree bersih) / `22e939c` (= `core/0.3.0`+`js/0.3.0`) / `8c7f2d4` |
| wasm sha256 | `8ec2d3cd4ade29d7f143c7fb6fea2a7148043aad48ed16f8bd0762eb9c828b40` (v5) |
| library | js 0.3.0 / core 0.3.0 / abi `2026000300` |
| korpus | `saq_payload_v1` (6 dokumen, 88.381 B; manifest sha identik ND-9/ND-12) |
| protokol | 15 ronde × 4 siklus, warmup 3, tanpa trimming, GC `false` (identik ND-9), urutan dokumen dirotasi, stage order terkunci data-dependency |
| guard | parity count (V8 root children) 360× + **guard match baru**: `paired == closers di index stream` 360×; warmup 18× → **738 parity checks**, 0 gagal |
| validator | `PASS` (schema v1.0.0 tanpa perubahan — sub-stage masuk sebagai `results[]` entry) |
| record | `out/measurements/zuu-20261114113218-f6c3f3e-nd9-cost-dev_device.record.json`; arsip `reports/nd13/` + `reports/nd13/raw/` |

## 2. Hasil dev (median per-op, ms)

| dokumen | bytes | **s2-open (fused)** | s2a-carve | s2b-scan | s2c-match | Σ sub / fused |
|---|---:|---:|---:|---|---|---:|
| courses | 3.993 | 0,0084 | 0,0003 | 0,0080 | 0,0015 | 1,15× |
| assistants | 5.614 | 0,0113 | 0,0003 | 0,0109 | 0,0018 | 1,14× |
| lecturers | 3.582 | 0,0080 | 0,0003 | 0,0077 | 0,0014 | 1,16× |
| schedules | 39.209 | 0,0790 | 0,0003 | 0,0738 | 0,0078 | 1,04× |
| reports | 35.623 | 0,0692 | 0,0003 | 0,0653 | 0,0051 | 1,02× |
| globalConfig | 360 | 0,0014 | 0,0003 | 0,0016 | 0,0009 | 1,96× |

Komposisi Σ(carve+scan+match) — dalam run:

| dokumen | scan | match | carve |
|---|---:|---:|---:|
| courses | 82,4% | 15,0% | 2,6% |
| assistants | 84,1% | 14,0% | 1,9% |
| lecturers | 82,1% | 15,2% | 2,7% |
| schedules | 90,0% | 9,6% | 0,4% |
| reports | 92,4% | 7,2% | 0,4% |
| globalConfig | 58,2% | 32,7% | 9,1% |

Sanity lintas-ukuran: `s5-boundary` = **0,021 µs/call** (bigint boxing floor)
— jauh di bawah semua sub-stage; Σ sub-stage ≈ fused (1,02–1,16× di KB-scale)
menunjukkan dekomposisi konsisten dengan bound, tanpa komponen ganda besar.

## 3. Verdict (dev)

1. **Scan mendominasi `s2-open`: 82–92%** pada dokumen KB-scale; match 7–15%;
   carve ~0,3 µs flat (2–3% KB-scale, 0,4% di 35–39 KB). Kandidat optimasi
   fase D yang menyasar open **harus menyasar scanner** (varian/mikro-opt
   `scanner8`), bukan arena carve maupun pass match.
2. **Rasio match naik di dokumen kecil** (15% di 3,5–5,6 KB vs 7–10% di 35–39
   KB; 33% di 360 B) — konsisten dengan call-boundary floor + jumlah bracket
   absolut yang kecil; bukan sinyal optimasi pada ukuran SAQ dominan.
3. **globalConfig (360 B) Σ/fused = 1,96×** — harga dua call boundary
   tambahan (scan + match standalone) menyamai pekerjaannya sendiri di
   payload sangat kecil; konfirmasi bentuk ABI v4 thin-call relevan untuk
   pemanggilan per-dokumen kecil, tapi bukan jalur count SAQ (dokumen
   KB-scale).
4. Kaitan ND-9: fused `s2-open` dev kini 0,1773 ms Σ-median (vs 0,1397 ms
   ND-9 era Node 24 / wasm v3) — **narasi antar-run**, bukan bukti (runtime
   V8 14.6 + wasm v5; bukan variabel terkontrol; lihat ND-10 E1).

## 4. Batas klaim

- Proxy sub-stage = **panggilan standalone** dengan call boundary sendiri:
  lower-bound per komponen, ditempel berdampingan dengan bound fused —
  TIDAK force-subtract (metodologi ND-9 diteruskan).
- Angka ini dev_device saja; server run menyusul (bila server reachable) —
  pertanyaan spesifik ND-9 "gap +38% open di server menempel di scan atau
  match?" belum terjawab sampai run server.
- Satu run_id per site; semua rasio dalam-run (AGENTS §4/§6).
- wasm v5 sha `8ec2d3cd…` ≠ wasm ND-9/ND-12 (`19baac8c…`/`c5b42b7d…`) —
  perbandingan antar-run dinyatakan narasi, bukan bukti.

## 5. Server run (pending)

Prosedur (pola ND-12 — tanpa boot app, aman di luar Senin): push branch →
server `git switch feat/nd13-open-decomposition` → scp `ze_json.wasm` +
`.sha256` (verifikasi sha `8ec2d3cd…`) → `node scripts/bench/
nd9_cost_diagnosis.mjs --probe --rounds 15 --warmup 3 --cycles 4
--abi-calls 4096 --site saq_server` → pull record. Status: **server
unreachable saat sesi (SSH timeout 100.67.191.111, 2× dicoba)** — run
server ditunda sampai mesin reachable; deliverable dev tidak menunggu.

## 6. Gate kebenaran ze_json v5 (PR #42, merged `22e939c`)

- native-release ctest **6/6** + native-sanitize (ASan/UBSan) **6/6**
  (termasuk `ReferenceParser.MatchPassParityWithOpen`: tabel match
  standalone == tabel fused open, index-for-index + paired count, atas
  fixture adversarial + seluruh korpus json_checker).
- wasm64 differential 71 dokumen × 5 mode + smoke + lazy **PASS**;
  26 ekspor v5; `abi_version=2026000300`; CI GitHub 4/4 (ubuntu+windows ×
  debug+release).

## 7. Deliverables

- ze_json PR #42 (`feat/abi-v5-match-pass`, commit `cb1fe9c`) → merged
  `22e939c`; tag `core/0.3.0` + `js/0.3.0`.
- Root: mode `--probe` di `scripts/bench/nd9_cost_diagnosis.mjs` + gate v5
  di `scripts/build-wasm.ps1` + pointer `ze_json → 22e939c` (commit
  `f6c3f3e`), laporan ini, arsip `reports/nd13/`, sidecar
  `reports/registry/zuu-20261114113218-f6c3f3e.json` (source=record),
  sinkronisasi tasks/plans.
- @cite: `10.14778_3115404.3115416` (Mison — staging pairing pass atas
  index stream; dasar `match_pass`), `10.1002_spe.3313` (provenance
  artifact/corpus per-run).
