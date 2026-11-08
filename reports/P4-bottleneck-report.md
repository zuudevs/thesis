# P4 — Laporan Bottleneck & Checklist Optimasi (scanner struktural)

> TASKS P4-6 · template: skill `cpp-highperf-json` (bottleneck_report) ·
> Bahasa kerja Indonesia · angka: MB/s, median 5 repetisi, site `dev_device`,
> preset `native-release`, Clang 23.1.5, AMD Ryzen 5 5500U.

## 1. Konteks objek optimasi

Tahap yang diukur: **structural pre-scan** (`reference_scan` / `scanner8` /
`scanner64` SWAR / `scanner128` SSE2 / `structural_scan` dispatch) — satu-satunya
tahap `ze_json` yang sudah terimplement dan teruji (parser on-demand menyusul).
Semua korpus P0-8; satu run = satu record; perbandingan kunci dilakukan
**dalam-run** (lihat §4).

## 2. Baseline

- Baseline kanonik: `zuu-20261109042022-ca8f5f4` (6/6 PASS validator).
- Gerbang kebenaran: 18+2 test suite — diferensial reference ↔ semua varian
  (fixtures, fuzz 300×3–4 varian, korpus json_checker lengkap dengan
  pengecualian legacy RFC 8259 fail1/fail18). ctest 100% di setiap langkah.

## 3. Limitasi pengukuran (penting untuk interpretasi)

1. **Profiler khusus tidak tersedia** (uProf/VTune tak terinstal; hanya WPR/ETW)
   → analisis bottleneck bersifat static-analysis + bukti terukur
   (lower-confidence, sesuai protokol skill).
2. **Clock drift antar-sesi**: scanner8 melompat 727→934→895 MB/s antar run
   pada korpus yang sama (laptop, tanpa pinning). Konsekuensi: perbandingan
   antar-klaim hanya dilakukan **dalam satu run**; `cpu_pinning` + frekuensi
   terkunci menjadi kebutuhan P5.
3. `cpu_pinning=false` di semua record (single-thread, tidak mengubah relatif).

## 4. Eksperimen & hasil

### E1 — SWAR `scanner64` (P4-2a, run `zuu-20261109053632`)

3 jalur: FAST-A (luar string tanpa kutip), FAST-B (dalam string tanpa kutip),
SLOW (serial). Klasifikasi 6×eq SWAR.

| korpus | scanner8 | scanner64 | delta |
|---|---|---|---|
| synthetic_1k | 999 | 1300 | +30% |
| synthetic_10k | 912 | 892 | −2% |
| synthetic_100k | 953 | 781 | −18% |
| synthetic_1mb | 934 | 760 | −19% |
| saq_payload_v1 | 1410 | 1240 | −12% |
| checker_batch | 999 | 815 | −18% |

**Ditolak** — kalah 5/6 korpus.

### E2 — SSE2 `scanner128` (P4-2b, run `zuu-20261109060034`)

Struktur 3-jalur identik, klasifikasi `_mm_cmpeq_epi8` (12 ops/16 B) +
`movemask`. Tambahan temuan kebenaran: rekaman kapasitas-penuh di jalur SLOW
sempat diabaikan — diperbaiki (kini ter-cover kontrak `InsufficientBuffer`).

| korpus | scanner8 | scanner128 | delta |
|---|---|---|---|
| synthetic_1k | 1056 | **1430** | +35% |
| synthetic_10k | 941 | 834 (cv 13%) | −11% |
| synthetic_100k | 912 | 777 | −15% |
| synthetic_1mb | 895 | 716 | −20% |
| saq_payload_v1 | 1150 (cv 11%) | 956 | −17% |
| checker_batch | 951 (cv 7%) | 799 | −16% |

**Ditolak** — kalah 5/6 korpus (menang hanya pada dokumen 1 KiB).

### E3 — Fix correctness `utils/swar.hpp` (ditemukan E1)

`(v−0x01)&~v&0x80` sebagai mask per-byte bocor borrow ke lane atas (30/200k
acak). Formula pengganti `~(v | ((v&0x7F..)+0x7F..)) & 0x80..` diverifikasi
2.000.256 kasus. Ini perbaikan kebenaran, **dipertahankan** — juga berdampak
ke pemakaian SWAR lain di masa depan.

## 5. Analisis bottleneck (static analysis + bukti terukur)

1. **Kepadatan kutip menentukan jalur** (evidence: E1/E2 — korpus compact
   selalu kalah; hanya dokumen 1 KiB yang menang). JSON compact punya kutip
   tiap ~6–15 B → hampir semua blok 8/16 B mengandung kutip/backslash →
   jatuh ke jalur serial → seluruh keunggulan vektor hilang, plus overhead
   klasifikasi vektor per blok.
2. **Klasifikasi 6 kelas mahal tanpa pshufb**: SWAR 6×eq ≈ 30 ops/8 B;
   SSE2 cmpeq 12 ops/16 B — keduanya masih lebih mahal dari **satu load
   tabel L1 + 2 tes masker** per byte yang dilakukan scanner8, apalagi
   scanner8 juga mendapat prediksi cabang stabil (state machine sederhana).
3. **Serial escape chain adalah penghalang SIMD murni**: rantai
   `e(i)=bs(i−1)&~e(i−1)` (alternasi dalam run backslash) tidak punya bentuk
   tertutup shift-xor sederhana; pendekatan jalur-serial yang kita pakai
   benar tapi membatasi kecepatan di korpus quote-dense. simdjson memecahkan
   ini dengan pipeline mask penuh (prefix-xor kutip + penanganan run
   backslash) — arsitektur berbeda, bukan tambalan pada desain 3-jalur.
4. **Per-doc overhead** (batch kecil): checker_batch semua varian ±790–990
   MB/s — panggilan per dokumen kecil terlihat, tapi bukan dominan.
5. **Latensi load tabel**: scanner8 unggul karena lookup tabel L1 per byte
   berjalan searah prediksi cabang; hipotesis unroll-8 (H2) belum diuji —
   kandidat eksperimen berikutnya bila scanner8 ingin dipertajam.

## 6. Keputusan & checklist P4

- [x] E1 SWAR — diukur → **ditolak** → varian dipertahankan teruji untuk
      perbandingan skripsi; dispatch default tetap `scanner8`.
- [x] E2 SSE2 — diukur → **ditolak** → idem.
- [x] E3 fix `swar.hpp` — **diterima** (correctness).
- [x] Satu perubahan per ukur; record lama vs baru tersimpan & tervalidasi.
- [ ] Eksperimen lanjutan (di luar lingkup P4 tahap ini): pipeline simdjson-style
      penuh (prefix-xor + escape SIMD), unroll scanner8, number parser &
      UTF-8 validator (komponen belum ada → P4-3 menunggu implementasinya).
- [ ] PGO (P4-4) — **keputusan pemilik** (PLANS §7); catatan: dengan clock
      drift antar-sesi, PGO perlu pengukuran dalam-run yang ketat.
