# Laporan Eksperimen

Laporan hasil per-task (Bahasa Indonesia), satu laporan per eksperimen/evaluasi
besar. Semua angka dalam laporan **harus** berasal dari record yang PASS
validator (`scripts/measurement-schema/validate.py`); arsip record mentah
disimpan apa adanya di `reports/nd6/` (exhibit, tidak diubah).

## Indeks

### Direktif on-demand (ND, 2026-11)
- [`ondemand-saq-evaluation.md`](ondemand-saq-evaluation.md) — **ND-7**:
  evaluasi lengkap jalur on-demand di SAQ; verdict 2.85×/3.00× (fase D,
  cache Mongo) — acceptance ≥1.5× tercapai; hipotesis H1–H5, limitasi jujur.
- [`nd6-server-phase-matrix.md`](nd6-server-phase-matrix.md) — **ND-8**:
  matriks ND-6 di server SAQ (`saq_server`, Node 26) — fase D **1.30×**
  (p95 1.46×), acceptance ≥1.5× **tidak tercapai di site ini**; dekomposisi
  komponen + kandidat perbaikan (plan doc §7).
- [`nd6/`](nd6/) — arsip record tervalidasi ND-6 (6/6 PASS, verbatim).

### Server & baseline (P5)
- [`P5-saq-server-baseline.md`](P5-saq-server-baseline.md) — baseline V8
  saq-report (situs dev; prosedur mengikuti runbook
  [`docs/development/saq-server-runbook.md`](../docs/development/saq-server-runbook.md)).
- [`P5-saq-server-runbook.md` → dipindah] — kini
  [`docs/development/saq-server-runbook.md`](../docs/development/saq-server-runbook.md).

### Fase P4 — profil & bottleneck
- [`P4-uprof-hotspots.md`](P4-uprof-hotspots.md) — hotspot uprof.
- [`P4-bottleneck-report.md`](P4-bottleneck-report.md) — analisis bottleneck
  scanner (basis keputusan ADR ze_json 0002: scanner64 SWAR rejected).

### Optimalisasi terukur (R5)
- [`R5-1-materialize-assign.md`](R5-1-materialize-assign.md)
- [`R5-2-array-count-drop.md`](R5-2-array-count-drop.md)
- [`R5-3-text-decoder-decode.md`](R5-3-text-decoder-decode.md)
- [`R5-4-dv-cache.md`](R5-4-dv-cache.md)
- [`R5-5-string-fuse.md`](R5-5-string-fuse.md)
- [`R5-6-frame-shape-tracing.md`](R5-6-frame-shape-tracing.md)
- [`R5-7-count-elements-gallop.md`](R5-7-count-elements-gallop.md)
- [`R5-8-step-kind-fused.md`](R5-8-step-kind-fused.md)
- [`R5-server-phase-matrix.md`](R5-server-phase-matrix.md) — matriks fase
  server (polanya mengikuti runbook
  [`docs/development/saq-server-runbook.md`](../docs/development/saq-server-runbook.md)).

### Lain-lain
- [`E3-lto-sandwich.md`](E3-lto-sandwich.md) — LTO sandwich.
- [`final-numbers.md`](final-numbers.md) — rekap angka final.

## Konvensi

- Laporan historis **tidak di-rewrite**; koreksi datang sebagai laporan baru
  atau catatan tautan saja (contoh: pemindahan runbook di atas).
- Provenance: setiap klaim angka menautkan record + raw exhibit; korpus
  diikat sha256 manifest; `run_id` memuat host-timestamp-git-hash.
