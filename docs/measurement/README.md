# Pengukuran

Protokol eksperimen & desain metrik.

| Dokumen | Isi |
|---|---|
| [`nd6-benchmark-plan.md`](nd6-benchmark-plan.md) | Protokol matriks benchmark 4 fase A–D (ND-6): jalur, kontrol eksperimen, metrik, acceptance ≥1.5× — disetujui pemilik; hasil di [`../../reports/ondemand-saq-evaluation.md`](../../reports/ondemand-saq-evaluation.md) |

Pendukung di luar folder ini:

- [`../../schemas/measurement.schema.json`](../../schemas/README.md) —
  schema record v1.0.0 + validator (`extras` membawa metrik v2: median, P95,
  binding_calls, index_count, GC).
- [`../../corpus/benchmarks/README.md`](../../corpus/benchmarks/README.md) —
  korpus benchmark & manifest sha256.
- [`../../scripts/bench/nd6_bench.mjs`](../../scripts/bench/nd6_bench.mjs) —
  harness 4 fase (satu run_id per fase).
