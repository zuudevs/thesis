# ADR 0004 — Korpus `saq_payload_v1`

- **Status:** Accepted
- **Tanggal:** fase P0-8 (2026-11); direkam 2026-11-12
- **Pengambil keputusan:** pemilik skripsi

## Konteks

Korpus ukuran (`synthetic_1k…1mb`) membuktikan sensitivitas ukuran tetapi
tidak mewakili **bentuk kerja** server SAQ. Komparasi yang sah terhadap
baseline V8 butuh dokumen yang strukturnya setia pada store saq-report:
root object yang membungkus array per-domain (`courses`, `assistants`,
`lecturers`, `schedules`, `reports`), `config_global` root object, dan
penulisan **pretty indent 2 persis seperti** `JsonRepository.write()` =
`JSON.stringify(data, null, 2)`. Data asli SAQ **tidak boleh dibagikan**
(plans §8).

## Keputusan

- Korpus **`saq_payload_v1`** = beban kerja SAQ *anonymized-but-
  structurally-faithful*: bentuk wrapper & array mirror `config/paths.js` +
  `repositories/index.js`; nama/telepon/email dari pool sintetis — tanpa
  data nyata.
- Generasi deterministik via `scripts/corpus/make_corpus.py` (seed 20261108);
  setiap direktori korpus membawa `MANIFEST.json` bebas-timestamp yang
  mengikat sha256 per file; `corpus.sha256` (hash manifest) dicatat di
  setiap record pengukuran.
- Provenance: `.gitattributes` `corpus/** -text` (autocrlf tidak boleh
  menyentuh byte korpus); salinan byte-exact di-commit ke repo ze_json agar
  CI self-test (dokumentasi di `ze_json/corpus/README.md`).

## Konsekuensi

- `saq_payload_v1` menjadi korpus acuan ND-5 (parity gate 26/26) dan ND-6
  (default `--corpus` harness 4 fase).
- Regenerasi hanya lewat generator; edit manual byte korpus dilarang
  (melanggar manifest).
- Limitasi: kesetiaan struktural, bukan kesetiaan statistik konten; ukuran
  store dev ≠ ukuran produksi (dicatat sebagai limitasi di laporan ND-7).
