# R5-13 — Version Registry: Dua Registry Mandiri + Backfill Provenance Pengukuran

Tanggal: 2026-11-14 · Status: **TEREKSEKUSI** (PR ze_json #41, PR root: pointer + harness)
Araah: instruksi pemilik — versi ABI mengikuti versi `ze_json` core; versi
`@ze_json/bindings/js` independen; setiap perubahan wajib bump versi (semver) + tag,
kecuali perubahan trivial (komentar/docs/whitespace); ada script untuk mengisi
kekosongan registry pada hasil pengukuran agar fieldnya standar.

## 1. Latar

Sebelum R5-13, tiga angka versi hidup terpisah dan sering tidak sinkron:

| Angka | Lokasi lama | Masalah |
|---|---|---|
| Versi ABI | `ABI_VERSION = 4` hardcoded di `ze_json.mjs` + `kAbiVersion` di `cabi.hpp` | bisa berbeda dari binary yang di-load |
| Versi core | `project(VERSION)` CMakeLists + `vcpkg.json` | O1-7 menaikkan ABI 3→4 tanpa bump semver |
| Versi npm | `bindings/js/package.json` statis | record pengukuran menulis `0.0.0-unknown` (nd6/nd9 membaca `ze_json/package.json` yang tidak ada) |

## 2. Desain (diterapkan di ze_json PR #41)

**Dua registry mandiri** (komit pemilik `2948c4f`, disambungkan `ee5e000`):

1. **Core** — `project(VERSION)` di `ze_json/CMakeLists.txt` (+ `vcpkg.json`
   wajib sama, divalidasi). Nomor ABI mengikuti otomatis: generator
   `configure_file` menulis `build/generated/ze_json/core/version.hpp`
   (`ZE_JSON_VERSION` = `ZE_JSON_CORE_VERSION_NUMBER` =
   `<year><major><minor><patch>` = **2026000200** untuk 0.2.0) → `kAbiVersion`
   di `include/ze_json/abi/cabi.hpp`.
2. **bindings/js** — `ZE_JSON_JS_VERSION` di `cmake/modules/ModuleRegistry.cmake`;
   `bindings/js/package.json` **digenerate** dari `cmake/templates/package.json.in`
   berisi `version` (js semver), `coreVersion` (= `ze_abi_version()`), `coreSemver`.
   `ze_json.mjs` membaca package.json-nya sendiri → `ABI_VERSION = coreVersion`
   (fail-loud di `ZeJson.load()` tetap; sumber tunggal CMake, tanpa angka duplikat).

**Validasi dua arah** (`cmake/templates/ValidateVersion.py.in`, PRE_BUILD):
`vcpkg.json == core semver` dan `bindings/js/package.json == ZE_JSON_JS_VERSION` —
kedua cek berjalan (dulu: `exit(0)` prematur + variabel `@BINDING_DIR@` tak pernah diset).

**Bump** kali ini: core `0.1.2 → 0.2.0` (MINOR — nilai `ze_abi_version()` berubah
karena sumbernya pindah; kontrak panggilan append-only tetap), js `0.2.0`.

## 3. Kebijakan bump + tag (AGENTS.md §9 baru)

| Jenis perubahan | Registry yang dibump | Tag |
|---|---|---|
| Kode core C++ (`include/`, `src/`, cmake core, tabel lookups) | core (`CMakeLists.txt` + `vcpkg.json`) | `core/X.Y.Z` |
| `bindings/js` (`ze_json.mjs`, tests, benchmarks binding) | js (`ModuleRegistry.cmake`) | `js/X.Y.Z` |
| Keduanya | keduanya | keduanya |
| Komentar/Doxygen, docs `.md`, reformat whitespace, CI yml tanpa sentuh kode versi-able | ❌ tidak | ❌ tidak |

Semver: **MAJOR** = perubahan signature/packing/semantik ABI · **MINOR** =
ekspor/fitur additive · **PATCH** = fix/perf tanpa kontrak baru. Tag dipasang di
commit merge `main` setelah PR lulus (bukan di branch). Checklist PR wajib
menyatakan bump+tag ya/tidak + alasan.

## 4. Verifikasi (gate)

- native-release: configure ulang + build 50/50 + **ctest 6/6 PASS**.
- wasm64-release: build OK, **gate 25 ekspor** (v4 surface, additive), SIMD v128 ada.
- wasm baru: sha256 `19baac8c84ccc0cdbd965586e483526d72ea99feb24681313f1c096cae00f57f`
  (berubah dari `c5b42b7d…` karena konstanta versi kini di-bake ke binary).
- Binding: smoke PASS; differential 71 dokumen × 5 mode scanner + parity parser
  vs `JSON.parse` PASS; lazy 43 checks PASS.
- Catatan operasional: configure lama gagal memproses toolchain vcpkg karena
  **CMakeCache basi** pasca-kegagalan vcpkg (VS instance tidak ketemu) — hapus
  `CMakeCache.txt` + `CMakeFiles/` lalu configure preset ulang; `activate.ps1`
  kini punya fallback auto-detect MSVC sistem bila `.toolchains/MSVC` belum dipasang.

## 5. Schema record pengukuran

`measurement.schema.json` + field standar (opsional — record lama tetap valid):
`library.js_version` (string), `library.core_version` (string),
`library.abi_version` (integer = `ZE_JSON_CORE_VERSION_NUMBER`).
Harness terdampak: `scripts/bench/nd6_bench.mjs`, `scripts/bench/nd9_cost_diagnosis.mjs`,
`scripts/node-benchmark/harness.mjs` — kini membaca `bindings/js/package.json`
(generated), sehingga `0.0.0-unknown` tidak muncul lagi pada record baru.

## 6. Backfill histori — `scripts/measurement-schema/registry_fill.py`

Stdlib-only; scan `reports/**` + `out/measurements/**` (read-only — exhibit
verbatim tidak disentuh, aturan AGENTS §4); tulis **sidecar**
`reports/registry/<run_id>.json` per run unik:

```json
{"schema_version":"1.0.0","kind":"version_registry","run_id":"…","site":"…",
 "git_commit":{"ze_json":"…","ze_json_source":"library.version pin|run_id suffix","saq_report":"…"},
 "versions":{"js_version":"…","core_version":"…","abi_version":N,"wasm_sha256":"…"},
 "source":"record|git|inferred|unknown","source_paths":[…],"notes":[…]}
```

Prioritas resolusi (jujur, tanpa menebak):

1. **record** — field standar sudah ada (record pasca-R5-13; belum ada yang
   masuk kategori ini).
2. **git** — resolusi di repo ze_json pada commit yang di-pin
   (`ze_json@<hash>` dari `library.version`, fallback suffix `run_id` untuk
   record cmake-generated): js dari `bindings/js/package.json`, abi dari
   literal `ABI_VERSION` di `ze_json.mjs` (era lama) atau `coreVersion` package.json
   (era baru), core dari `vcpkg.json`/`CMakeLists.txt`.
3. **inferred** — dari record sendiri: `library.version` semver polos =
   `js_version` (harness lama) → `core_version` dipasangkan (kebijakan
   sinkron-manual terverifikasi di `47eb27a`/`9d1d6a2`/`26769c0`: 0.1.0/0.1.1/0.1.2
   identik); label `ABI vN` di `language_runtime` = `abi_version`; record
   **native** (`C++23 … native-release`): `js/abi` = N/A (tanpa permukaan C-ABI),
   `core_version` = semver polos.
4. **unknown** — kosong jujur (tidak ada).

**Diskriminator loaded-artifact (kasus wasm-swap):** label `ABI v3` pada
beberapa harness lama HARDCODED — ND-10/ND-12 membawa sha256 artifact v4
(`c5b42b7d…`) tapi label bilang v3. Peta `KNOWN_ARTIFACT_ABI`
(sha→abi, dari log sandwich/driver swap + gate build-wasm) jadi sumber kebenaran
terkuat: `35b7f773…→3`, `c5b42b7d…→4`, `19baac8c…→2026000200`. Bila record tak
membawa sha (nd6-era, ladder S0–S2 v3-swap di tree `fe877f2`), label dipakai.

**Hasil** (195 run unik ze_json; 79 record `saq_baseline` dilewati):

| source | run | catatan |
|---|---|---|
| git | 192 | termasuk nd6 (pin `14592a0` → 0.1.0/3), nd9 (pin `d9e25ac` → 0.1.2/3), nd10/nd12 (pin `fe877f2`/`5a90545` → 0.1.2/**4**), o1-ladder (S0–S2 label v3 menimpa git 4 — swap) |
| inferred | 3 | record native google_benchmark era pra-kontrak-ABI (3211b7d dkk.) — `abi_version` null + catatan N/A |
| unknown | 0 | — |

`wasm_sha256` = null untuk era yang tidak merekam sha (nd6 dev/server awal) —
jujur, tidak diisi tebakan.

## 7. Batas

- Sidecar menangani record yang tersimpan; run yang benar-benar hilang dari
  arsip tetap tidak terwakili (tidak direkonstruksi).
- `source_paths` menunjuk file record sumber; record di `out/` (gitignored)
  tetap tidak ter-commit — sidecar-lah yang committed.
- Nilai `abi_version` untuk record era v1/v2 mengandalkan label string
  (`ABI v1`); tidak ada binary tersisa untuk memverifikasi.
