# R5-5 — Fusi Scan String C++ (Hasil Negatif) + Gerbang Sanitize Pulih

Eksperimen **#4** dari rencana optimasi R5-lanjutan (item rencana
pemilik: "hilangkan validasi string berulang di C++";
`reports/R5-4-dv-cache.md` = eksperimen #3). Satu perubahan per
pengukuran; **keputusan: DITOLAK** — perubahan fusi di-revert sebelum
merge, build-fix gerbang yang diambil.

## 1. Temuan pass ganda (terkonfirmasi dari source)

`ze_get_string` (`cabi.cpp:375-395`) untuk string ber-escape menjalankan
**3 pass** di atas body yang sama: `get_string_span()` → `scan_string`
(verdict) → `unescape_string` → `scan_string` lagi + `decode_interior`
(count, out=null) + `decode_interior` (write). String polos: 2 scan +
memcpy.

## 2. Perubahan yang diuji

Fusi: pass-1 scan tetap (verdict wajib); saat `cap >= inner_len`,
skip pass count (probe) — decode langsung ke dst, satu pass. Invariant
provable: output decode ≤ `inner_len` (kontrak `StringParts`,
`string.hpp:13-18`). Kontrak terjaga: no-grammar-error-writes (pass-1
di depan), InsufficientBuffer dst-untouched (jalur `cap < inner_len`
tetap probe dulu). Wasm berubah: sha256 baru `b2f24a9b…`.

## 3. Gerbang yang dijalankan

- `native-release`: ctest **6/6** PASS.
- `native-sanitize`: **6/6** PASS — setelah dua perbaikan gerbang
  (lihat §5) yang sebelumnya membuat gerbang **tak pernah bisa jalan**
  di device ini: (a) `stl_asan.lib` tidak tersedia di BuildTools 14.44
  install → annotation STL dimatikan saat sanitizers on; (b)
  `sanitizer_copy_runtime` didefinisikan tapi tak pernah dipasang ke
  target → semua test mati `STATUS_DLL_NOT_FOUND` (0xc0000135).
  ze_json PR #28 (`2727fb0`) merged `55aa893`.
- JS dengan wasm baru: smoke PASS + differential 71 dokumen × 5 mode +
  parser/tree parity.
- Build wasm terbukti **reproducible**: rebuild dari source main sama
  menghasilkan sha256 `7e26044f…` byte-identik (diverifikasi 3×).

## 4. Hasil benchmark: TIDAK MENANG

Sandwich satu window (2026-11-12 UTC 22:35xx), 3 pasang
BASE(`7e26044f…`) ↔ CAND(`b2f24a9b…`), 6 korpus, 36 record PASS:

| korpus | BASE | CAND | rasio |
|---|---|---|---|
| synthetic_1k | 14.6 | 14.7 | 1.008 |
| synthetic_10k | 9.8 | 9.8 | 1.003 |
| synthetic_100k | 9.8 | 9.6 | 0.979 |
| synthetic_1mb | 9.5 | 9.3 | 0.979 |
| saq_payload_v1 | 20.4 | 20.4 | 0.998 |
| checker_batch | 8.2 | 8.1 | 0.992 |

**Atribusi**: korpus nyaris tanpa escaped string — saq 0 backslash,
checker 50, synthetic_100k 174 (≈0.17% bytes), 1mb 1770 (≈0.17%).
Pass yang dihapus (probe count untuk string ber-escape) hampir tak
pernah jalan → sumber gain tidak tersedia di korpus manapun. Selisih
-2% di 100k/1mb = **shift codegen** (layout branch baru memindah
optimalisasi), bukan sinyal manfaat/hilangnya kerja: per pasangan tak
konsisten (satu pasang CAND +1.9%), median hanya tertarik oleh
sebaran.

## 5. Keputusan & provenance

- **Ditolak**: aturan "terima hanya jika menang". Fusi didefinisikan
  ulang saat ada workload escape-heavy, atau sebagai rider pada
  eksperimen #5 (batch ABI) yang mengubah hot path yang sama.
- Commit perf `ed5351d` dihapus dari branch (belum pernah di-push);
  yang di-merge hanya build fix gerbang (PR #28, `2727fb0`, merged
  `55aa893`). wasm artifact di working tree kembali `7e26044f…`
  (rebuild verifikasi). Branch benchmark artifacts tersimpan di
  `out/measurements/zuu-2026111122{3512,3521,3530,3538,3547,3555}-*`.
- Site: `dev_device`; angka hanya dibandingkan in-situ satu window.

## 6. Tindak lanjut

- Eksperimen #5 (batch ABI, Opsi A fused export) — keputusan pemilik
  untuk bump ABI v4; #6 wrong-map `#frame` butuh bukti tracing
  terpisah.
- Korpus escape-heavy (fixture escape padat) bisa menambah sensitivitas
  evaluasi pass-string di masa depan — dijadwalkan terpisah (bukan
  bagian siklus ini).
