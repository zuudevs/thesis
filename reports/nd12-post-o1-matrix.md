# ND-12 — Matriks ND-6 pasca-O1 (countermeasure terpasang), TEREKSEKUSI

Eksekusi: 2026-11-14 (dev + server), setelah ladder R5-12 — instruksi
pemilik dalam sesi chart. Tree bersih kedua site (dev: editan `.vscode`
pemilik di-stash selama run lalu di-pop; server: stash `nd10-e2 pre-run
vscode settings` masih disimpan), gate fail-fast aktif, 15 ronde + 3
warmup, tanpa trimming, korpus `saq_payload_v1` sha256 identik.

**Identitas**: root `7fb2ae4`, ze_json `fe877f2` (**ABI v4** — O1-4+O1-5+O1-7
terpasang), wasm `c5b42b7d…` **byte-identik** kedua site (server menerima
artefak v4 via scp, sha diverifikasi), Node 26.13.1 identik.

**Verdict pasca-O1** (vs ND-10 pra-O1 di kolom Δ):

| Fase | ND-10 (pra-O1) | ND-12 (pasca-O1) | Δ rasio |
|---|---|---|---|
| A · materialisasi penuh | 0,04× / 0,04× | **0,05× / 0,06×** | +25–50% relatif |
| B · L2 project | 0,09× / 0,09× | **0,13× / 0,13×** | +40% relatif |
| C · L1 (terbaik per site) | 1,05× / 0,81× | **1,05× (dev) / 0,81× (srv)** | stabil |
| D · mongo-cache (acceptance) | 1,45× / 1,13× | **1,48× / 1,13×** | stabil |
| D · file-store | 0,92× / 0,94× | 0,81× / 0,92× | warm-cache confounder |

Run ID (10 record PASS validator): dev `zuu-20261114{022724,022727,
022730,022954,022956}-7fb2ae4`; server `server-lanjut-20261114{023810,
023812,023813,024229,024230}-7fb2ae4`. Arsip: `reports/nd12/` + sidecar
`reports/nd12/raw/`.

## Interpretasi

1. **Countermeasure O1 menutup sebagian gap fase A/B** — persis target
   R5-9/10/11 (loop O1 menyasar jalur materialisasi): A +25–50% dan
   B +40% relatif terhadap pra-O1, di KEDUA site. Server kini
   menyamai/Melebihi dev di fase A (0,06× vs 0,05×) — hardware gap di
   materialisasi menutup dengan thin-call.
2. **Fase D tak berubah (1,48×/1,13×)** — konsisten prediksi ND-9:
   jalur count tidak memanggil `valueKind`/step family yang dioptimasi;
   jalannya kini `s2-open`-bound. Acceptance ≥1,5× **belum tercapai**
   → kandidat berikutnya ada di jalur open (instrumentasi core lanjutan)
   atau ND-11 (HTTP end-to-end, konteks ekspres.json).
3. **Fase C stabil** — L1 traversal untung kecil dari kind-mirror
   (assistants 1,05× tetap satu-satunya kemenangan).
4. **Confounder dinyatakan**: window dev lebih lambat absolut (editor
   berjalan — rasio in-window yang menjadi bukti); fase D file-store dev
   kini warm page-cache (0,53 ms vs 4,09 ms pra-O1) — jangan
   dibandingkan absolut lintas vintage.
5. Chart vintage **`post-o1`** ditambahkan ke `nd6_summary_chart.py`
   (nd6/nd10 jadi histori); master `out/charts/post-o1-summary-map.` +
   `post-o1-acceptance.`, arsip SVG `reports/charts/`.

## Proses/gate

- Dev: stash `nd12 post-o1 pre-run: vscode trailing comma` (pop setelah
  run — pemilik); server: stash ND-10 masih disimpan (pemilik, recoverable).
- Semua sidecar: `gate.clean = true`, `exploratory = false`,
  `artifact.wasm_sha256 = c5b42b7d…` (kedua site).
