# ADR 0005 — `readCount()` repositori dengan slot parser sole-owner

- **Status:** Accepted
- **Tanggal:** ND-5 (2026-11-12); direkam 2026-11-12
- **Pengambil keputusan:** pemilik skripsi (satu call-site dulu), diimplement
  di saq-report PR #3 (`7930009`)

## Konteks

Integrasi pertama ze_json ke SAQ harus **read-only** dan tidak boleh
mengubah perilaku baseline. `GET /rekap` hanya butuh `length` dari 4 store
(courses, assistants, schedules, reports) — sementara `read()` yang ada
mem-materialize seluruh store per request (jalur panas V8). Binding wasm64
mengekspos parser on-demand pada slot pool statis 64 (ADR ze_json 0003);
integrasi butuh protokol kepemilikan slot yang jelas di sisi aplikasi.

## Keputusan

- Tambah method **`readCount()`** pada `JsonRepository`/`MongoJsonRepository`
  (baseline `read()`/`write()` **byte-identical**, tidak disentuh):
  menghitung jumlah entri store tanpa materialisasi penuh — dijalankan di
  atas **slot parser sole-owner** per store (satu parser slot tetap milik
  satu store; lifetime open → traverse → close per dokumen; kontrak D2).
- Loader `repositories/zeJsonBinding.js` (wasm64 C-ABI v3, `require(esm)`
  Node ≥ 24); opt-in env `SAQ_JSON_ENGINE=ze` — default tetap V8.
- Parity gate `scripts/check-json-lazy-parity.js` 26/26: nilai + jenis &
  lokasi error identik (TypeError call-site vs dalam-`read()` → AppError);
  semantik aplikasi terkunci (missing-key → default, null field →
  `?? default`, urutan array, error); duplicate-key terkunci di level
  binding (lazy.mjs T2).

## Konsekuensi

- Risiko regresi baseline ≈ 0 (jalur lama utuh; jalur baru opt-in).
- Perfomance awal 1.10× (fase D) — penyebabnya stringify per `readCount()`;
  diperbaiki oleh kandidat cache-bytes (ADR 0006) menjadi 2.85×/3.00×.
- Call-site lain menyusul setelah benchmark ND-6; deviasi as-built tercatat
  di `docs/architecture/lazy-access-api.md` §14.
