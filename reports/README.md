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
- [`nd6/server-lanjut-20261111/`](nd6/server-lanjut-20261111/) + [`nd6/server-lanjut-20261113/`](nd6/server-lanjut-20261113/) —
  arsip verbatim 52 record server (36 + 16; seluruhnya PASS re-validasi
  AUD-1; batch 11-13 = exploratory — root server dirty).
- [`nd6-audit-2026-11-13.md`](nd6-audit-2026-11-13.md) — **AUD-1**: audit
  artefak & protokol ND-6; klasifikasi Verified/Reported/Unknown, kesalahan
  hitung dokumen yang dikoreksi (errata), fix harness (gate clean-tree,
  `artifact_sha256`), dan rencana eksperimen ND-9/ND-10/ND-11.
- Desain eksperimen berikutnya (belum dieksekusi):
  [`../docs/measurement/nd9-parser-cost-diagnosis.md`](../docs/measurement/nd9-parser-cost-diagnosis.md),
  [`../docs/measurement/nd10-site-runtime-control.md`](../docs/measurement/nd10-site-runtime-control.md),
  [`../docs/measurement/nd11-phase-e-http.md`](../docs/measurement/nd11-phase-e-http.md).

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
- [`R5-9-kind-mirror.md`](R5-9-kind-mirror.md) — **O1-4** (loop O1 1/3 diterima):
  kind-mirror pool step — +7,5–11,5%.
- [`R5-10-frame-decode.md`](R5-10-frame-decode.md) — **O1-5** (2/3):
  fast path decode frame — +7,5–16,5%.
- [`R5-11-thin-step.md`](R5-11-thin-step.md) — **O1-7** (3/3):
  ABI v4 thin step family — +27,4–45,1%; gate 25 ekspor; wasm v4.
- [`R5-12-o1-ladder.md`](R5-12-o1-ladder.md) — **O1-8/R5-12**: ladder kumulatif
  4 state satu window, median-of-6 — kumulatif 1,36×–1,53× monotonic.
- [`R5-13-version-registry.md`](R5-13-version-registry.md) — **R5-13**:
  dua registry versi (core/js) + bump 0.2.0 + backfill provenance
  (`reports/registry/`, 195 run: 192 git / 3 inferred / 0 unknown).
- [`R5-server-phase-matrix.md`](R5-server-phase-matrix.md) — matriks fase
  server (polanya mengikuti runbook
  [`docs/development/saq-server-runbook.md`](../docs/development/saq-server-runbook.md)).
- [`registry/`](registry/) — sidecar versi per run (backfill R5-13;
  exhibit record tidak diubah).

### Direktif ND lanjutan (2026-11-13/14)
- [`nd9-cost-diagnosis.md`](nd9-cost-diagnosis.md) — **ND-9**: dekomposisi
  biaya parser; s2-open ~88–90%, s5-boundary ≈ 0 (hipotesis boxing-ABI
  terbantahkan untuk fase D).
- [`nd10-runtime-control.md`](nd10-runtime-control.md) — **ND-10**: kontrol
  runtime Node 26 matched + wasm byte-identik; kompresi V8 14.6 = penyebab
  dominan.
- [`nd12-post-o1-matrix.md`](nd12-post-o1-matrix.md) — **ND-12**: matriks
  pasca-O1 (ABI v4); A/B naik (+25–50%/+40%), D tak berubah 1,48×/1,13×
  (s2-open-bound).

### Lain-lain
- [`E3-lto-sandwich.md`](E3-lto-sandwich.md) — LTO sandwich.
- [`final-numbers.md`](final-numbers.md) — rekap angka final.

## Konvensi

- Laporan historis **tidak di-rewrite**; koreksi datang sebagai laporan baru
  atau catatan tautan saja (contoh: pemindahan runbook di atas).
- Provenance: setiap klaim angka menautkan record + raw exhibit; korpus
  diikat sha256 manifest; `run_id` memuat host-timestamp-git-hash.
