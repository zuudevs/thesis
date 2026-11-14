# P4-3 — Penutupan: C3 (UTF-8 SIMD pshufb) DITOLAK dengan bukti terukur

Tanggal: 2026-11-14. Status akhir task `P4-3` (tasks.md L193): **ditutup**.

## Riwayat P4-3

| Sub-item | Keputusan | Bukti |
|---|---|---|
| C1 — string-class table di `scan_string`/`decode_interior` | **DITOLAK** (2026-11-10) | sandwich back-to-back: regres seragam −12..−48%; kontrol bisection B1 ≈ baseline → penyebab loop baru, bukan kehadiran tabel |
| Sisa C1 (repairs `@cite` + fix encoding generator) | **commit terpisah** (2026-11-10) | masuk repo |
| C2 — reciprocal fast path q<0 (`kPowerOfFiveReciprocal`) | **DITERIMA** (2026-11-10) | FullWalk ladder +19,6..+33,2%; tanpa regresi; bit-exact vs oracle (150k fuzz) |
| C3 — UTF-8 SIMD pshufb | **DITOLAK** (2026-11-14, laporan ini) | bukti di bawah |

## Bukti penolakan C3

Metode: profil byte-class seluruh korpus terukur via
`scripts/corpus/ascii_profile.py` (daftar dokumen dari `MANIFEST.json`
per korpus, dengan guard byte-count manifest↔disk; stdlib-only).
Output verbatim (2026-11-14):

```
corpus              docs      bytes  nonASCII       % backslash       %
checker_batch        25       5573       102  1.830%        50  0.897%
saq_payload_v1        6      88381         0  0.000%         0  0.000%
synthetic_100k        1     102400        92  0.090%       174  0.170%
synthetic_10k         1      10240        10  0.098%        18  0.176%
synthetic_1k          1       1024         2  0.195%         6  0.586%
synthetic_1mb         1    1048576       926  0.088%      1770  0.169%
```

Interpretasi:

1. **Sumber gain C3 tidak tersedia di workload terukur.**
   `utf8_seq_advance` (`src/ondemand/string.cpp` L104) hanya menyala pada
   byte lead ≥ 0x80 — frekuensinya ≤ 0,195% byte (0,000% di
   `saq_payload_v1`, korpus utama jalur count). Validasi UTF-8 berbasis
   pshufb (block 64 B) hanya menang ketika multi-byte sequence umum;
   di korpus ini panggilan per-sekuens hampir tak pernah terjadi.
2. **C3 tidak menyentuh jalur dominan.** Validasi UTF-8 hidup di
   `scan_string` (traversal/decode), bukan di `scanner8` — sedangkan
   ND-13 (`reports/nd13-open-decomposition.md`) menetapkan s2-open =
   88–90% biaya per-op dengan **scan 82–92% dari open**. Ceiling C3
   pada jalur count dibatasi porsi s3-count (~7%) dikali panggilan
   per-sekuens yang ~nol → gain terukur ≈ 0.
3. **Pelajaran P4-2 berlaku**: varian vektor kalah dari scalar pada
   JSON compact quote-dense (klasifikasi vektor lebih mahal dari 1 load
   tabel). Tidak ada alasan mengharapkan pshufb UTF-8 menghindari pola
   yang sama pada segmen pendek.

Konsekuensi:

- P4-3 **ditutup**; C3 tidak diimplementasikan. Kandidat adopsi ulang
  hanya bila workload bergeser non-ASCII-heavy (mis. payload chat
  multibyte) — saat itu ukur ulang profil byte-class dulu (script di
  atas), jangan asumsikan.
- Arah optimasi scanner berlanjut sebagai keluarga **O2** (O2-1:
  string-interior fast skip di `scanner8`, lihat tasks.md) — menyasar
  mayoritas byte (interior string) di stage yang benar (s2-open).

## Rujukan

- `@cite 10.1002_spe.2920` — semantik validasi UTF-8 yang di-anchor
  `utf8_validate_scalar` (tetap benar; hanya ROI fast path-nya yang
  tak tersedia di korpus ini).
- `@cite 10.14778_3115404.3115416` (Mison) + ND-13 — peta biaya stage
  yang menjadi dasar prioritas.
