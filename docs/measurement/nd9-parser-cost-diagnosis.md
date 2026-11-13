# ND-9 — Desain Diagnosis Biaya Parser (diagnosis, BUKAN optimasi)

> Status: **harness terimplement & teruji smoke** (`scripts/bench/nd9_cost_diagnosis.mjs`,
> 2026-11-13: syntax OK, gate REFUSED exit 3, smoke exploratory `--allow-dirty`
> 25 results + 36 parity checks, record PASS validator). **Eksekusi penuh
> menunggu tree bersih** (gate fail-fast). Direktif: buktikan batas
> komponen dari source, jangan kurangi dua benchmark berbeda lalu sebut
> selisihnya komponen tanpa validasi.

## 1. Tujuan

Fase D server = 1.30× (di bawah acceptance ≥1.5×). Sebelum kandidat apa pun
(slot reuse / ABI v4 batch / lazy decode) dipertimbangkan, kontribusi biaya
per komponen jalur `readCount()` harus terukur sendiri-sendiri — satu
eksperimen diagnosis, bukan proyek optimasi.

## 2. Batas komponen (dibuktikan dari source saat ini)

| # | Komponen | Bukti source | Cara ukur | Catatan |
|---|---|---|---|---|
| 1 | Input alloc + copy JS→wasm | `bindings/js/ze_json.mjs` L159–169 (`ze_alloc` + `new Uint8Array(memory.buffer).set(bytes, ptr)`), L371–372 (`alloc(len)`, `alloc(cap*8)`) | stage: time(`alloc`+`set`) saja, tanpa open | `ze_alloc` = 1 ABI call; `set` = tulis memori langsung dari JS |
| 2 | `ze_parser_open` (arena + structural scan + bracket match) | `src/abi/cabi.cpp` L205–206; `src/ondemand/document.cpp` L234–259 (3× `arena.allocate(slot_bytes)` + `structural_scan(src, src_size, indexes, src_size)`) | stage: time(open) | **Inseparable**: scan+index di dalam satu pass `open` — pemisahan butuh instrumentasi core (di luar scope; dinyatakan keterbatasan). Arena carve = 3×`src_size*8` upper bound (`ondemand-parser.md`) |
| 3 | Traversal `countElements` | surface C-ABI `ze_parser_*` (cabi.hpp; count pada slot) — **wajib verifikasi dulu dari source**: bagaimana nested container di-skip (bracket table), kerja framing token yang masih dilakukan, iterasi semua direct children | stage: time(count) | DILARANG menyebut O(1) hanya karena satu ABI call — kerja per-child + framing harus dibaca dari implementasi sebelum klaim kompleksitas |
| 4 | Close + reset heap | `src/abi/cabi.cpp` L461–462 (`ze_parser_close`), L118–123 (`ze_reset_heap` — menutup semua slot; L91: tanpa free individual, alloc hidup sampai reset) | stage: time(close), time(reset) | `closeParser` harness juga menghitung 2 ABI call (close + reset) |
| 5 | Boundary JS/BigInt per panggilan ABI | `ze_json.mjs` (setiap ekspor di-boxing `BigInt`→u64; L160 `Number(this.#exports.ze_alloc(BigInt(...)))`) | stage: micro-loop `ze_abi_version` N kali → biaya per-panggilan floor | boxing u64 = hipotesis §13.3 `docs/architecture/lazy-access-api.md` |

## 3. Protokol

- Harness `scripts/bench/nd9_cost_diagnosis.mjs` (terimplement 2026-11-13) — korpus
  `saq_payload_v1` (tidak diganti), 15 ronde, warmup 3, CYCLES=4 bracket-samples
  per ronde dirotasi-urutan-dokumen (urutan stage fix — data dependency
  s1→s4), tanpa trimming, `--expose-gc`, GC counter, parity guard per siklus
  (countElements == jumlah child root V8; mismatch = run void), metadata
  lengkap (incl. `artifact_sha256` + gate clean-tree dari `nd6_protocol.mjs`).
- Record schema v1.0.0: tiap stage = satu `results[]` entry (engine
  `wasm64_cabi`) dengan `rationale.purpose` + `basis_papers`
  (`10.1002_spe.3313`; `10.14778_3115404.3115416` Mison untuk index count).
- **Larangan**: tidak ada perubahan core/scanner/ABI; stage diukur dari
  ekspor yang sudah ada. Selisih antar-stage TIDAK boleh disebut "biaya
  komponen X" bila stage menumpuk (mis. open termasuk scan) — dilaporkan
  sebagai batas terikat, bukan dikurangi paksa. Bracket gap antar stage
  dikecualikan dari angka stage.
- Site: `dev_device` dulu; re-run di `saq_server` untuk melihat apakah
  distribusi komponen berbeda lintas mesin (ragam varian implikasi RQ2).
- Filename record: `<run_id>-nd9-cost-<site>.record.json` (`recordFilename`
  prefix `nd9`); raw exhibit `out/raw/<run_id>/nd9_stages.json`.

## 4. Interpretasi yang sah

- Tabel kontribusi per stage (median + P95 + rasio thd total per-op).
- Menjawab: di ukuran dokumen SAQ (3.6–39 KB), berapa dominasi open-vs-
  count-vs-boundary; memberi basis KUANTITATIF untuk memprioritaskan
  kandidat §7 plan doc — keputusan tetap milik pemilik, bukan bagian
  eksperimen ini.
- Tidak menjawab: biaya di dalam `open` (scan vs carve vs match) — butuh
  instrumentasi core (hipotesis kandidat berikutnya, terpisah).

## 5. Yang tidak dilakukan

- Tidak mengubah workload/korpus/metrik demi angka; tidak mengubah core;
  tidak mengklaim optimasi dari diagnosis.
