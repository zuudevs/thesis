# O2-1 — String-interior fast skip di `scanner8` (DITERIMA, sandwich)

Tanggal: 2026-11-15. Kandidat pertama keluarga **O2** (optimasi scanner),
dasar: verdict ND-13 — `s2-open` mendominasi jalur count (88–90% per-op)
dengan **scan = 82–92% dari open** (`reports/nd13-open-decomposition.md`).

## 0. Hipotesis & perubahan

Loop interior string di `scanner8` membayar **load tabel `kJsonCharClass`
+ 2 masked test per byte** — padahal interior adalah mayoritas byte payload.
Perubahan (`src/ondemand/scalar.cpp`, commit `2429520`): jalur interior
kini **bebas-tabel** — 2 compare prediktable per byte (`'\\'` lalu `'"'`),
tabel hanya di jalur luar-string. Bit escape = hanya 0x5C, bit quote =
hanya 0x22 (codegen `GenerateLookups.py`), jadi compare langsung ≡ masked
test lama. Semantik error identik (dangling escape, string tak tertutup,
precedence, isi `dst` pada InsufficientBuffer); `reference_scan()` tetap
oracle tak tersentuh. Satu perubahan per pengukuran (skill
`cpp-highperf-json`); core PATCH `0.3.0 → 0.3.1` (tag `core/0.3.1`,
merge `0aacd82`, ze_json PR #44); js tetap 0.3.0.

## 1. Identitas run (sandwich back-to-back, satu window)

| Sifat | Baseline (core 0.3.0) | Kandidat (core 0.3.1) |
|---|---|---|
| run_id | `zuu-20261114200912-b699f51` | `zuu-20261114201432-1c530d0` |
| ze_json / wasm | `22e939c` / `8ec2d3cd…` (rebuild reproduksi byte-identik) | `0aacd82` / `1d8960c9…` (abi 2026000301) |
| root | `b699f51` branch (pointer `22e939c`, tree bersih) | `1c530d0` branch (pointer `0aacd82`, tree bersih) |
| korpus | `saq_payload_v1`, manifest sha identik | sama |
| protokol | 15×4 siklus, warmup 3, tanpa trimming, GC off, `--probe` ND-13 | identik |
| validator | PASS (738 parity checks) | PASS (738 parity checks) |

Dua run dieksekusi **berurutan dalam ±5 menit** (satu window) — pola
sandwich C2 untuk mengendalikan drift window (pelajaran ND-12: drift
dev ~11%). Exhibit tambahan lintas-window (kandidat, ~1 jam sebelumnya):
`zuu-20261114195727-1c530d0`.

## 2. Hasil (Σmedian per-op, 6 dokumen)

| stage | baseline | kandidat | Δ |
|---|---:|---:|---:|
| **s2-open (fused)** | 0,1829 ms | **0,0906 ms** | **−50,5%** |
| s2b-scan | 0,1729 ms | 0,0847 ms | **−51,0%** |
| s1-copy | 0,0093 ms | 0,0063 ms | (window) |
| s3-count | 0,0137 ms | 0,0101 ms | (window) |
| s2a-carve / s2c-match | 0,0018 / 0,0185 ms | 0,0013 / 0,0141 ms | (window) |

Per dokumen (sandwich):

| dokumen | bytes | fused Δ | scan Δ |
|---|---:|---:|---:|
| courses | 3.993 | −42,6% | −40,8% |
| assistants | 5.614 | −42,3% | −46,4% |
| lecturers | 3.582 | −47,6% | −49,1% |
| schedules | 39.209 | **−54,1%** | −53,4% |
| reports | 35.623 | −49,2% | −50,9% |
| globalConfig | 360 | −30,5% | −30,2% |

Konsistensi antar-pengukuran: pair lintas-window (kemarin vs hari ini)
memberi −38,7% pada fused — arah dan orde sama; sandwich (kontrol
window) menempatkan efek sebenarnya di **−50%**.

## 3. Verdict

**DITERIMA.** Gain −50,5% pada stage terpanas jalur count (s2-open),
konsisten di seluruh 6 dokumen (−30,5%..−54,1%, terbesar di payload
besar), jauh melampaui band drift window (~11%), dengan gate kebenaran
penuh (diferensial byte-identity + sanitize + wasm differential 71×5 +
738 parity checks per run). Implikasi fase D:

- Rasio D (nd6) naik otomatis dari sisi ze (denominator jalur ze
  turun ~38% per-op: s2-open 0,1773 → ~0,09 ms dari Σ ND-13 0,2019 →
  ~0,109 ms) — **re-measure matriks ND-6 pasca-O2 = langkah berikutnya**
  (pola ND-12; acceptance ≥1,5× dinilai ulang di sana).
- s2-open kini ~0,09 ms Σmedian: komposisi baru = scan ~0,085 (masih
  dominan), match ~0,014, carve ~0,001 — **kandidat O2-2 (SWAR interior
  skip) layak diukur** bila profil menunjukkan interior masih dominan.
- Kaitan ND-9/ND-10: gap hardware server-vs-dev di open (+38%) akan
  diuji ulang saat run server pasca-O2.

## 4. Batas klaim

- Bukti = perbandingan baseline↔kandidat **run berbeda** (satu kode satu
  run_id) dalam satu window, tree bersih keduanya, preset/korpus/protokol
  identik, artifact sha ter-catat di record — pola P4-2/C2/R5-9.
- Mesin: `dev_device` saja; server menyusul (saat reachable).
- `globalConfig` (360 B) −30% tapi tetap call-boundary-dominated
  (Σ sub / fused 1,96× era ND-13) — tidak diekstrapolasi ke payload
  yang lebih kecil.

## 5. Deliverables

- ze_json PR #44 (`perf/o2-1-interior-skip`: `2429520` perf + `fd8cca7`
  build fix) → merged `0aacd82`, tag `core/0.3.1`.
- Build fix ikut PR (`fd8cca7`): deklarasi cross-compile wasm dipindah ke
  toolchain file (`ZUU_WASM_TOOLCHAIN`) — preset cacheVariables hilang
  saat re-detection (invalidasi info compiler) sehingga configure wasm64
  turun jadi host build dan guard `NOT wasm` terbalik (GTest REQUIRED
  gagal). Linux runner terselamatkan gtest sistem; Windows fresh terbukti
  rusak dan kini diperbaiki.
- Arsip `reports/o2-1/` (3 record + raw), sidecar `reports/registry/`
  (3 run baru, source=record), sinkronisasi tasks/plans.
- @cite: `10.14778_3115404.3115416` (Mison staging), `10.1002_spe.3313`
  (provenance per-run).
