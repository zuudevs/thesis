# R5-1 — Optimasi Materialisasi JS: Fast Data-Property Assignment

Tindak lanjut prioritas #1 verdict R5 (`reports/R5-server-phase-matrix.md`
§6): fase materialisasi JS mendominasi 58–92% waktu full parse. Satu
perubahan per pengukuran (skill `cpp-highperf-json`), baseline = record R5
dev @`ab09adb`.

## 1. Profil & hipotesis

Profil CPU V8 (`--cpu-prof`) pada konteks `wasm-parse-full`, korpus
`synthetic_100k` (dev, Node 24.19):

| kelompok | item self-time teratas |
|---|---|
| JS materialisasi (~55% termasuk GC parsial) | `#readObject` 12.4%, `#frame` 6.6%, `getDouble` 4.7%, `valueKind` 3.8%, decode string (`utf8Slice`+`toString`+`fromArrayLike`) ≈ 6.4%, `#materialize` 2.8%, `#plain` 2.5% |
| C++ walk (~25%) | `Value::begin_array` **15.8%** (terpanas), `scan_string` 2.2%, `scan_number` 1.6% |
| harness (bukan parse) | `spawnSync` 6.8%, `(program)` 1.9% |

Korpus synthetic ≈ 952 object + 952 array per 100 KB → `#readObject`/`
#readArray` dipanggil ribuan kali per dokumen. Hipotesis H1 (terpilih
pertama, item JS terbesar): `Object.defineProperty` per field memakai
generic property path V8; assignment biasa pada receiver null-prototype
mengambil fast data-property path dengan semantik identik.

## 2. Perubahan & semantik

`ze_json.mjs` `#readObject`: `Object.defineProperty(obj, key, {...})` →
`obj[key] = value`.

Setara dengan `JSON.parse` (DefineOwnProperty) **karena** receiver
`Object.create(null)`:

- `__proto__` tidak menemukan setter di chain (tidak ada prototype) →
  tetap OWN data key (bukan perubahan prototype);
- duplicate key: last-wins, posisi = kemunculan pertama;
- key integer-index-like (`"3"`, `"123"`): urutan `OrdinaryOwnPropertyKeys`
  sama di kedua engine (integer indices ascending dulu).

Wasm tidak berubah (JS-only) — sha256 artifact `7e26044f…` tetap;
provenance R5 tetap valid.

## 3. Protocol sandwich

- Satu window (dev, 2026-11-11, 3 pasang bergantian): konteks
  `wasm-parse-full`, 6 korpus, flag standar harness
  (`--repeats 5 --min-time-ms 200 --warmup-ms 300`, `gc_between_repeats=false`,
  Node 24.19.0, Ryzen 5 5500U).
- BASE = binding `ab09adb` (file di-revert in-worktree); CAND = binding
  `207b2bf`. Record menandai hash HEAD (`207b2bf`) + `dirty=true` untuk
  kedua sisi (untracked artifact) → slot dipetakan dari urutan timestamp
  invokasi (preseden E3 §1): `141554`/`141617`/`141640` = BASE,
  `141606`/`141629`/`141652` = CAND.
- 36 record **validator PASS**; analyzer: per-invocation grouping
  (6 record satu invokasi berbagi timestamp), median per korpus.

**Catatan akuntansi** (provenance): dua batch attempt tercatat lalu
DIHAPUS karena run terpotong — (a) 6 record `134636–134645` (pipeline
`Select-Object -First 1` meng-kill node di korpus pertama), (b) 18 record
`134934–135034` (git `index.lock` transient → checkout BASE gagal, semua
invokasi mengukur binding candidate). Bukan bukti pengukuran sah.

## 4. Hasil (median MB/s; cand/base)

| korpus | BASE | CAND | rasio | pairs BASE | pairs CAND |
|---|---|---|---|---|---|
| synthetic_1k | 8.5 | 10.6 | **1.252** | 7.3 / 8.5 / 9.8 | 8.8 / 10.6 / 11.0 |
| synthetic_10k | 6.5 | 7.5 | 1.151 | 6.3 / 6.5 / 6.5 | 7.4 / 7.5 / 7.5 |
| synthetic_100k | 5.1 | 5.5 | 1.086 | 5.0 / 5.1 / 5.1 | 4.9 / 5.5 / 5.5 |
| synthetic_1mb | 1.6 | 1.8 | 1.132 | 1.6 / 1.6 / 1.8 | 1.8 / 1.8 / 1.9 |
| saq_payload_v1 | 13.2 | 13.5 | 1.022 | 11.1 / 13.2 / 13.6 | 13.3 / 13.5 / 15.8 |
| checker_batch | 5.4 | 6.0 | 1.109 | 3.6 / 5.4 / 5.5 | 5.0 / 6.0 / 6.1 |

Konsistensi: BASE median 8.5 MB/s @1k vs record R5 dev `131706` 8.1 MB/s —
same-hash antar-window ±5%, wajar.

## 5. Verdict & kebenaran

- **Diterima**: naik di semua korpus (1.02–1.25× median), tanpa regresi;
  gain terbesar di korpus object-dense (1k) — konsisten dengan profil
  (`#readObject` item terbesar). saq_payload_v1 marginal (1.02×) —
  store-shaped, share key/byte lebih kecil.
- Kebenaran: smoke PASS (termasuk 5 test semantik baru: dup-key, `__proto__`
  mid-doc, key numerik) + differential 71 dokumen × 5 mode + parser/tree
  parity — hijau di `207b2bf` dan head final `f82e09d`.
- ze_json PR #24 (`perf(binding-js): assign object keys via the fast
  data-property path`); commit `207b2bf` (perf) + `f82e09d` (comment fix
  menuju report ini).

## 6. Lanjutan (TASKS O1)

Urutan berikutnya berdasar sisa profil: **O1-2** TextDecoder cached
(~6.4% + copy per string), O1-3 cache DataView (4.7%), O1-4 mirror JS
`valueKind` (3.8%, wajib differential ekshaustif), O1-5 `#frame`/`#plain`
bigint trim (9.1%), O1-6 drop presize `countElements` (terpanas di C++:
`begin_array` 15.8% — dipanggil 2× per array via `count_elements`).
O1-7 (ABI v4 thin-call) menunggu keputusan pemilik.
