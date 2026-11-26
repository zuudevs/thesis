# ADR 0008 — Batas Repository Workspace Skripsi

- Status: Accepted
- Tanggal: 2026-11-26
- Menggantikan: —

## Konteks

Workspace `v5` telah berkembang dari fondasi pengukuran menjadi superproject
yang memuat parser, baseline aplikasi, protokol, laporan, serta dokumen
skripsi. Proyek dan repo sebelumnya mengalami beberapa perpindahan folder sehingga
batas antara domain riset, source code, naskah, dan tooling lokal menjadi
ambigu. Selain itu, `thesis-proposal/utils` merupakan symlink absolut ke
root workspace, sehingga checkout proposal tidak portabel.

## Keputusan

1. Root `v5` menjadi **research superproject**. Isinya meliputi `docs/`,
   `scripts/`, `schemas/`, `corpus/`, `reports/`, `assets/`, dan `tools/`
   yang tracking.
2. Komponen berikut menjadi submodule dengan repo masing-masing:
   - `ze_json/` — library parser;
   - `saq-report/` — baseline aplikasi;
   - `thesis-proposal/` — sumber proposal Typst;
   - `article/` — sumber, pipeline build, dan audit naskah artikel.
3. `submission-thesis-supervisor` tidak lagi menjadi submodule aktif. Repo
   GitHub historis ditandai **archived (read-only)**, diberi tag
   `archive/2026-11-26` pada commit `015188c`, dan tidak dihapus.
4. `utils/typ` dipindahkan ke repo proposal. Repo proposal harus menyimpan
   utilitas sebagai file terlacak, bukan symlink ke path absolut workspace.
5. `tools/dashboard` dan `tools/grapher` menjadi sumber terlacak. Kredensial,
   database lokal, dependency, build output, dan incremental cache tetap
   diabaikan Git.
6. `out/` tetap menjadi lokasi hasil transient; record permanen hanya berada
   di `reports/` beserta provenance verbatim.
7. `assets/bib/cites.bib` adalah registri bibliografi riset kanonik. Snapshot
   bibliografi artikel harus berasal dari sumber kanonik tersebut dan menyimpan
   commit/hash provenance; perubahan literatur independen tidak boleh
   menggabungkan dua sumber kebenaran.
8. Kebijakan tahun pada registri kanonik adalah `year >= 2016`. Satu paper
   metodologi SC'15 (`10.1145_2807591.2807644`) diizinkan melalui exception
   key-based yang eksplisit dan tervalidasi; tahun publikasinya tidak diubah.

## Konsekuensi

### Positif

- Clone root dan setiap subproject dapat dipahami serta di-review secara
  terpisah.
- Perubahan naskah tidak mencemari pipeline pengukuran; sebaliknya,
  pointer submodule memberi provenance snapshot yang eksplisit.
- Path absolut dihilangkan dari repo proposal.
- Tooling tracked dapat direproduksi tanpa memasukkan state lokal.

### Negatif

- Submodule menambah satu tingkat checkout dan membutuhkan
  `git submodule update --init --recursive`.
- Pergantian snapshot artikel memerlukan perubahan gitlink pada root.
- Pemisahan repo berarti filter bibliografi harus dibuat secara eksplisit.

## Mitigasi dan transisi

- `submission-thesis-supervisor` diarsipkan pada upstream dan tetap dipertahankan.
- Perubahan utility proposal dibuat melalui PR pada repo proposal sebelum
  root menghapus `utils/typ`. PR `zuudevs/thesis-proposal#3` sudah merged
  pada commit `e9cee64`; root memindai commit tersebut dan menghapus helper
  symlink lama.
- Registri canonical root commit `5f2043a426e52ee5af193920bccaafcbb2dc1aab`
  berisi 68 entri/66 DOI unik. PR `zuu-inner/thesis-article#2` merged pada
  `cc0bbe2cb1996173f99fec9d235a3cf10fbda6e1`; PR #3 menambahkan normalisasi
  EOL dan merged pada `fbcf44f79b367f0eecfc6c4d1006fb7f9bc5d3e0`; PR #4
  mengatur output teks tracked dengan newline LF eksplisit dan merged pada
  `8cc881b18dfa3eb0ace446618d80052905df63d1`; PR #5 menambahkan atribut LF
  untuk laporan validasi dan merged pada
  `cb22c9cffc8489132780807d5af59e5cf3bba696`. Snapshot artikel 42 entri
  (41 DOI + satu paper URL-only) beserta provenance dan verifier 16/16 menjadi
  pointer submodule root.
- PR restrukturisasi root tidak mengubah record pengukuran historis dan tidak
  memerlukan bump versi core/JS `ze_json`.
