# R5-6 — Tracing Wrong-Map `#frame` (Bukti Diagnostik, Bukan Klaim Performa)

Item **#6** rencana pemilik R5-lanjutan: "investigasi wrong-map `#frame`
dengan `--trace-deopt` (tracing terpisah dari throughput)". Laporan ini
murni **bukti** untuk hipotesis: apakah bentuk `#frame` yang beragam
(`{ok:true,done:true}` / `{ok:true,ts,cursor}` / `{ok:false,error,code}`)
menimbulkan deoptimization "Wrong map" atau IC megamorphic pada
konsumennya. **Tidak ada klaim throughput** di laporan ini.

## 1. Metode

Semua run di `dev_device`, binding main ze_json `55aa893`, wasm artifact
`7e26044f…` (build reproducible, lihat R5-5 §5), Node **v24.19.0**,
harness `scripts/node-benchmark/harness.mjs`, engine `ze-parser`,
context `wasm-parse-full`.

| run | korpus | flag | run_id (dihapus) |
|---|---|---|---|
| T1 | synthetic_1mb | `--trace-deopt --trace-deopt-verbose` | `zuu-20261111224610` |
| T2 | saq_payload_v1 | idem | `zuu-20261111224612` |
| T3 | synthetic_10k | `--log --log-ic --log-code --logfile=<tmp>` (`--repeats 2 --min-time-ms 100 --warmup-ms 200`) | `zuu-20261111225103` |
| T4 | saq_payload_v1 | idem T3 | `zuu-20261111225104` |

Catatan tooling: `--trace-ic` **tidak tersedia** di Node 24.19.0 Windows
(`bad option`); padanannya `--log-ic` + `--log --logfile=...`. Dengan
`--logfile-per-isolate` (default), nama file menjadi
`isolate-<pid>-<logfile>` di direktori logfile. Event IC berformat
`<Kind>,<addr>,<t>,<line>,<col>,<old>,<new>,<map>,<name>` — pasangan
(line,col) dipakai untuk atribusi situs: dicocokkan **persis** dengan
posisi source `bindings/js/ze_json.mjs`; event dengan state `X` (snapshot
builtin/generic, map `0x0`) dan situs yang (line,col)-nya tidak cocok
dengan source binding dikecualikan dari klaim binding.

## 2. Temuan `--trace-deopt` (T1, T2)

Hitungan alasan deopt pada seluruh isi trace:

| string | T1 (1mb) | T2 (saq) |
|---|---|---|
| `wrong map` / `wrong-map` | **0** | **0** |
| `insufficient type feedback` | 0 | 0 |
| `not a heap number` | 0 | 0 |
| `wrong instance` / `wrong-prototype` | 0 | 0 |
| `bailout` | 1 | 0 |
| `marking dependent code` | 11 | 0 |

T1 (1mb), seluruh 62 baris trace terkatalog:

1. **Tidak ada deopt eager "Wrong map"** — tidak ada satu pun, termasuk
   pada `#frame` dan seluruh konsumennya.
2. **1 lazy bailout** `#readArray` (TURBOFAN, opt id 25, 0.938 ms),
   pemicu invalidasinya: `reason: dependent allocation site tenuring
   changed` — keputusan pretenuring site alokasi berubah (umpan balik
   GC), bukan bentuk objek. Frame input menunjukkan array hasil
   `JSArray[1755]` + frame object yang sedang dibangun.
3. **10 invalidasi** `marking dependent code … reason: embedded weak
   objects cleared` pada `#materialize` (TF), `valueKind`, `arrayNext`,
   `objectNext`, `objectField`, `getString`, `getDouble`,
   `#decodeStringBytes` (Maglev), `#readArray`, `#readObject` (TF) —
   referensi weak ke objek wasm (exports/instance) yang tertanam di kode
   teroptimasi dibersihkan GC saat instance parser tua dikumpulkan.
4. **Urutan waktu**: semua event deopt muncul **setelah** baris hasil
   pengukuran dicetak (klaster pasca-pengukuran). Selama warmup + 5
   repeats yang diukur, **nol** event deopt.

T2 (saq): **nol** event deopt dari ujung ke ujung.

## 3. Temuan `--log-ic` (T3, T4)

State char (konvensi ic-processor): `0`=uninitialized, `1`=monomorphic,
`P`=polymorphic, `N`=megamorphic, `X`=generic (snapshot/builtin),
`^`=reconfigured. Dua map frame yang teramati (addr per run):
`M_step` = map frame `{ok:true, ts, cursor}` — dibuat literal baris 230
(StoreIC `.ts`/`.cursor` membawa map ini); `M_done` = map frame
`{ok:true, done:true}` — boilerplate literal baris 221 (literal
konstanta, tak ber-StoreIC, masuk lewat transisi `1→P`).

Situs keluarga frame di `ze_json.mjs` (final state, jumlah map):

| situs (line,col) | properti | T3 (10k) | T4 (saq) |
|---|---|---|---|
| 230,28 / 230,48 | store `ts`/`cursor` (step frame) | mono `M_step` | mono `M_step` |
| 243,31 / 324,45 | store `value` (`#plain`, `getDouble`) | mono | mono |
| 252,45 / 479,18 / 258,43 / 484,20 | store `slot`/`ts` | mono | mono |
| 252,17 / 258,17 / 309,17 / 464,15 / 471,16 / 626,17 / 638,18 | load `.ok` (open/root/getDouble/count) | mono | mono |
| 695,16 (`#readObject` begin.ok), 709,18 (field.ok) | load `.ok` | mono | mono |
| 653,16 (`#readArray` begin.ok) | load `.ok` | mono | **P (2 map)** |
| 680,17 (`#readArray` next.ok), 728,17 (`#readObject` next.ok) | load `.ok` | **P (2 map)** | **P (2 map)** |
| 657,15 (`#readArray` begin.done) | load `.done` | mono | **P (2 map)** |
| 700,15 (`#readObject` begin.done) | load `.done` | mono | mono |
| 684,16 / 732,16 (next.done) | load `.done` | **P (2 map)** | **P (2 map)** |
| 677,40/50, 708,65/75, 714,45/55 | load `.ts`/`.cursor` | mono `M_step` | mono `M_step` |

Interpretasi:

- **Set situs P(2) = M_step + M_done, persis 2 map, stabil.** Situs
  loop-exit (`next.ok`/`next.done` dari `arrayNext`/`objectNext`)
  memang menerima frame done tiap kontainer habis → polymorphic-2.
  `containerBegin` hanya kembali done untuk kontainer kosong: 10k tanpa
  array kosong (mono), saq punya satu array kosong (`P(2)` di 653/657).
- **Map error-frame (`{ok:false,error,code}`, baris 225-227) tidak pernah
  dibuat** di keempat run: tidak ada StoreIC `.error`/`.code` dari situs
  literal itu dan tidak ada map error di situs konsumen mana pun (jalur
  error short-circuit via `!x.ok` sebelum properti lain disentuh).
- **Tidak ada transisi `1→N`, `P→N`, `N→N`, `^` pada satu pun situs
  keluarga frame binding.** Semua transisi situs binding = `0→1`
  (inisialisasi) dan `1→P` (tambah map kedua), lalu stabil sampai akhir
  run. Sebagai pembanding, tracing memang menangkap state `N` di
  tempat lain (`length`/`prototype`/`keys`/`types`, LoadGlobalIC
  `Number`/`process` — internals Node + harness), jadi keabsennya di
  situs frame bukan artefak alat.

## 4. Jawaban hipotesis

1. **Wrong-map deopt: tidak didukung.** `--trace-deopt` pada dua korpus
   (0 eager "Wrong map"; satu-satunya lazy bailout berpemicu tenuring GC)
   dan `--log-ic` (tidak ada situs frame yang mencapai `N` atau
   reconfigured) konsisten: keragaman bentuk `#frame` tertangani IC
   polymorphic-2 + feedback compiler, tanpa deopt.
2. **Bentuk frame praktis hanya 2** (step + done); map error-frame absen
   di korpus yang sukses. Konsumen `.ok`/`.done` polymorphic-2; `.ts`/
   `.cursor` monomorphic — tidak ada churn.
3. **Implikasi eksekusi**: overhead `#frame` yang tersisa (profil O1-1:
   walk/re-entry dominan) berasal dari **panggilan ABI + boxing BigInt**
   per langkah, bukan dari bentuk objek — dieksekusi di eksperimen #5
   (batch ABI Opsi A fused step+kind, TASKS O1-10). Item O1-5 (hoist
   BigInt decode `#frame`/`#plain`) tetap open dengan dasar profil, dan
   kini juga bebas tuduhan shape-deopt.

## 5. Keputusan & provenance

- **Keputusan**: hipotesis wrong-map `#frame` **dinyatakan tidak
  terkonfirmasi** (evidence-based); tidak ada perubahan kode dari item
  ini — tracing saja.
- Run tracing mengubah timing (instrumen di jalur yang sama), maka
  **4 record + raw exhibit T1–T4 dihapus** setelah analisis
  (`out/measurements` kembali 462; `out/raw` 90 direktori). Angka
  throughput yang tercetak pada stdout tracing tidak dipakai.
- Bukti mentah (log temp, tidak di-commit): `r5_6_trace_1mb_utf8.log`
  (62 baris terkatalog), `r5_6_trace_saq_utf8.log` (8 baris),
  `r5_6_ic_{10k,saq}.v8.log` (7.1k/7.1k baris), analyzer
  `r5_6_ic_analyze.py` + kutipan situs `r5_6_ic_sites.py` di
  `%TEMP%/opencode/`.
- Site: `dev_device`; tidak ada perbandingan lintas mesin/preset/hash.
