# ADR 0007 — Measurement schema v1 + mekanisme `extras`

- **Status:** Accepted
- **Tanggal:** schema fase P0-1/P0-2 (2026-11); mekanisme `extras` ND-6
  (2026-11-12)
- **Pengambil keputusan:** pemilik skripsi

## Konteks

Perbandingan lintas mesin/preset/hash/korpus dilarang (AGENTS §4), jadi
satu format record harus cukup untuk semua sisi (benchmark C++, gtest,
harness Node, ND-6) dan tetap bisa berkembang tanpa memecah validator.
Record tanpa `rationale` dianggap tidak lengkap. ND-6 menuntut metrik baru
(median, P95, GC, counter ABI) yang tidak ada di schema awal.

## Keputusan

- **Schema v1.0.0** (`schemas/measurement.schema.json`, JSON Schema
  draft-07): satu "measurement record" = `schema_version`, `run_id`,
  metadata host/tool/library/corpus/config, array `results`; setiap entry
  `results[]` wajib `rationale` (`purpose` + `basis_papers[]`) — validator
  stdlib-only `scripts/measurement-schema/validate.py` menolak record tanpa
  itu. `run_id = hostname-<YYYYMMDDHHMMSS>-<git-hash>` (+ `-dirty`).
- **Mekanisme `extras`** (ND-6, metrik v2): perluasan metrik (median, P95,
  `binding_calls`, `index_count`, `consumed/skipped_fields`, hitungan GC)
  hidup di field `extras` per entry — **schema tetap v1.0.0**, validator
  tidak berubah, record lama tetap sah. `binding_calls`/`index_count` =
  null di fase D (tidak terukur di level harness — jujur, bukan nol palsu).
- Pipeline: exhibit mentah di `out/raw/<run_id>/` apa adanya; record
  tervalidasi di `out/measurements/`; arsip verbatim di `reports/nd6/`.

## Konsekuensi

- Semua analisis hanya boleh memakai record PASS validator (6/6 ND-6 PASS).
- Perubahan schema di masa depan = bump minor + ADR baru (bukan edit record
  historis).
- Normalisasi google-benchmark via `scripts/measurement-schema/
  split-gbench.py` (satu corpus object per record).
