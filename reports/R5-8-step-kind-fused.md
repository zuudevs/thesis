# R5-8 — O1-10: Batch ABI Opsi A Fused Step+Kind (Hasil Negatif)

Eksperimen **#5** rencana optimasi R5-lanjutan (item rencana pemilik:
"batch ABI Opsi A — fused step+kind"), mengeksekusi dasar R5-6: overhead
`#frame` yang tersisa = **panggilan ABI + boxing BigInt per value**
(bukan shape-deopt). Satu perubahan per pengukuran; **keputusan:
DITOLAK** — hasil netral, perubahan di-revert sebelum push (pola O1-9:
aturan "terima hanya jika menang").

## 1. Desain Opsi A

Fusi klasifikasi ke langkah iterasi: setiap export langkah yang hot
menerbitkan `classify(token_start)` frame yang dikembalikan lewat satu
out-pointer u32, sehingga walk materialisasi JS tidak lagi memanggil
`ze_value_kind` terpisah (1 panggilan ABI + 1 boxing BigInt lebih sedikit
per value materialisasi):

- `ze_container_begin_kind (slot, ts, cursor, kind_out)` — kind token
  frame balikan (array child / object key);
- `ze_array_next_kind (slot, ts, cursor, kind_out)` — kind child berikut;
- `ze_object_field_kind (slot, ts, cursor, kind_out)` — kind **value**
  frame (klasifikasi hot walk JS).

Kontrak **append-only** (ABI v4, `kAbiVersion = 4`): seluruh signature v3
dan packing tak berubah; `kind_out == 0` = tidak diminta; frame `done`/
`error` tidak menyentuh out-pointer (binding memegang nilai sebelumnya).
Binding: `readU32Cached` (pola cache-view O1-3), `#kindPtr = alloc(8)`,
`#materialize(ts, cursor, kind)` dengan fallback `valueKind` untuk kind=0
(root tetap 1× `valueKind`).

## 2. Gerbang kebenaran (semua PASS)

- `native-release` + `native-sanitize` (ASan/UBSan): ctest **6/6** PASS
  di kedua preset.
- Wasm64 rebuild: sha256 **`aaa16629…`** (BASE = `35b7f773…`).
- Smoke PASS (`abi_version=4`); differential **71 dokumen × 5 scanner
  mode + parser/tree parity vs `JSON.parse`** — semua agree.

## 3. Sandwich (swap 2 file: binding + wasm)

| sisi | binding `.mjs` | wasm |
|---|---|---|
| BASE | `fa7b7cef` (v3) | `35b7f773…` |
| CAND | `1b1f35d9` (v4) | `aaa16629…` |

**Insiden integritas (dicatat):** sandwich pertama memakai verifikasi
`Get-FileHash` — cmdlet **tidak tersedia** di environment PowerShell
device ini, sehingga kedua sisi perbandingan jadi `$null` dan verifikasi
$null==null selalu lolos tanpa memverifikasi apa pun. **36 record window
pertama dihapus** (integritas swap tak terbukti), sandwich di-rerun
dengan verifikasi `python hashlib` dua file per swap. Pada rerun,
atribusi sisi terbukti tiga lapis: (a) urutan alternasi BASE→CAND per
pasangan sesuai script, (b) verifikasi hash file per swap (script throw
bila mismatch), (c) metadata record membawa **versi ABI aktual binding**
(`ABI v3` = BASE ×3, `ABI v4` = CAND ×3).

Rerun: 2 window? — satu window 3 pasangan, 6 korpus, **36 record PASS**
validator (`out/measurements/zuu-20261111232{000,009,017,026,035,044}-*`).

## 4. Hasil: netral

| korpus | BASE MB/s | CAND MB/s | cand/base | per-pair (3 pasang) |
|---|---|---|---|---|
| synthetic_1k | 14.8 | 14.7 | 0.989 | 1.024 / 0.994 / 0.966 |
| synthetic_10k | 10.0 | 9.8 | 0.989 | 1.017 / 0.991 / 0.942 |
| synthetic_100k | 9.9 | 9.7 | 0.979 | 1.013 / 0.997 / 0.969 |
| synthetic_1mb | 9.6 | 9.6 | 1.004 | 0.958 / 1.057 / 1.004 |
| saq_payload_v1 | 20.9 | 20.7 | 0.994 | 0.998 / 0.998 / 0.994 |
| checker_batch | 8.2 | 8.4 | 1.027 | 1.022 / 1.044 / 0.958 |

Median cand/base **0.979–1.027**; per-pair **0.942–1.057** melintasi 1.0
dua arah; nilai base/cand saling tumpang tindih di semua korpus (1k:
base 14.8–14.9 vs cand 14.4–15.2). Harapan awal eksperimen (~3–6% dari
penghapusan 1 panggilan ABI + boxing per value) **tidak tercapai** —
semua perbedaan dalam envelope noise mesin (drift ±2% antar pasangan,
pola yang sama dengan O1-3/R5-4/R5-7).

## 5. Interpretasi (dasar keputusan)

- Menghapus 1 panggilan ABI + 1 boxing BigInt per value **tidak
  berdampak pada throughput end-to-end**: biaya per-panggilan wasm64
  (`BigInt(slot)` cast + trampoline) ternyata kecil dibanding pekerjaan
  materialisasi per value (alokasi objek/array JS, decode string,
  boxing double). Faktor dominan profil O1-1 = walk/re-entry struktur,
  yang tetap harus dikeluarkan oleh walk v4 (frame masih di-decode dan
  diteruskan antar langkah).
- Fusi menambah **kompleksitas permanen** — bump ABI v4, 3 export baru
  di permukaan C-ABI publik, out-pointer + state `#kindPtr` di binding,
  parameter `kind` di `#materialize`. Tanpa gain terukur, kompleksitas
  ini tidak dibayar oleh bukti (aturan "terima hanya jika menang",
  konsisten dengan O1-9).
- Opsi B (thin-call — `#frame` tanpa objek frame, kembalikan tuple tipis)
  tetap **open** di O1-7 sebagai kandidat lain; hasil O1-10 justru
  memperkuat dasarnya: overhead bukan di jumlah panggilan, tapi di
  bentuk frame yang di-boxing.

## 6. Keputusan & provenance

- **DITOLAK.** Commit kandidat `ce255cc` (branch
  `perf/step-kind-fused`) di-**revert sebelum push**: `main` ze_json
  tetap `c1c91ce`, branch lokal dihapus (commit masih reachable via
  reflog bila suatu hari workload berubah), working tree dipulihkan ke
  artifact BASE (binding `fa7b7cef` + wasm `35b7f773…`, smoke
  `abi_version=3` PASS).
- 36 record rerun **dipertahankan** sebagai exhibit (`out/measurements/
  zuu-20261111232{000,009,017,026,035,044}-ce255cc_*` + raw pasangannya);
  36 record window pertama (verifikasi rusak) dihapus bersama raw-nya.
- Artifact kandidat tersimpan di temp untuk arsip: `o10_wasm_cand.wasm`
  (`aaa16629…`), `o10_binding_cand.mjs` (`1b1f35d9`); log sandwich
  `r5_8_sandwich2.log`, script `r5_8_sandwich.ps1` (temp).
- Site: `dev_device`; semua perbandingan in-situ satu sesi; hash BASE
  `35b7f773…` → CAND `aaa16629…` (wasm64, sama kecuali cabi + binding).
