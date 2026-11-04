Penelitian dilaksanakan pada Program Studi S1 Teknik Informatika, Fakultas Telematika
Energi, Institut Teknologi PLN, yang beralamat di Jl. Duri Cengkareng Raya No.3,
Cengkareng, Jakarta Barat. Objek studi kasus adalah aplikasi pelaporan otomatis
Laboratorium Software Architecture and Quality (SAQ) yang berjalan pada server
laboratorium, dan seluruh perangkat pengembangan berupa repositori kode sumber
aplikasi SAQ serta pustaka Parser JSON On-Demand ze_json.

Penelitian direncanakan berlangsung selama enam bulan, terhitung sejak November 2026
sampai dengan April 2027. Tahap awal mencakup studi literatur dan penyusunan proposal
pada bulan November 2026, disusul studi kode sumber kedua perangkat lunak pada bulan
Desember 2026. Tahap instrumentasi berlangsung pada bulan Desember 2026 sampai
Januari 2027, mencakup penyiapan korpus uji dan pengukuran baseline. Tahap
implementasi integrasi ze_json beserta pengukuran perlakuan dilakukan pada bulan
Januari sampai Februari 2027, disusul tahap evaluasi dan analisis data pada bulan
Februari sampai Maret 2027. Tahap akhir berupa penyusunan laporan, revisi, dan
persiapan sidang dilaksanakan pada bulan Maret sampai April 2027. Rincian kegiatan
per bulan disajikan pada subbab Jadwal Penelitian.

Instrumen utama penelitian ini adalah perangkat keras dan perangkat lunak yang
menjadi lingkungan pengukuran. Sesuai prinsip lingkungan tertutup (close
environment), baseline dan perlakuan diukur pada perangkat keras yang persis sama,
yaitu server SAQ tempat aplikasi berjalan. Spesifikasi perangkat keras dan perangkat
lunak lingkungan pengukuran disajikan pada @tbl-hw dan @tbl-sw; nilai spesifikasi
tersebut akan dilengkapi dengan pembacaan langsung dari sistem pada saat pengukuran
dan tercatat pula secara otomatis pada metadata setiap run benchmark.

#figure(
  table(
    columns: (auto, auto),
    align: (left, left),
    table.header([*Komponen*], [*Spesifikasi*]),
    [Prosesor (server SAQ)], [○○ (jenis, jumlah inti fisik/logis, frekuensi)],
    [Memori utama (RAM)], [○○ GB, ○○ (jenis/kecepatan)],
    [Penyimpanan], [○○ (jenis, kapasitas)],
    [Kartu antarmuka jaringan], [○○],
    [Perangkat pengukur pendamping], [○○ (laptop penguji; hanya untuk penyiapan, bukan kutipan lintas perangkat)],
  ),
  caption: [Spesifikasi perangkat keras lingkungan pengukuran],
) <tbl-hw>

#figure(
  table(
    columns: (auto, auto),
    align: (left, left),
    table.header([*Komponen*], [*Versi dan ketentuan*]),
    [Sistem operasi], [○○ (edisi, versi)],
    [Runtime Node.js], [○○ (versi major.minor wajib identik antar run)],
    [Basis data], [MongoDB ○○],
    [Kompilator C++], [LLVM/clang ○○ dengan C++23],
    [Sistem build], [CMake dengan generator Ninja, dependensi via vcpkg],
    [Kerangka benchmark], [Google Benchmark (native), benchmark runner Node.js (baseline)],
    [Kerangka uji], [GoogleTest],
  ),
  caption: [Spesifikasi perangkat lunak lingkungan pengukuran],
) <tbl-sw>

Sebagai bagian dari instrumentasi, beban prosesor harian server SAQ dicatat sejak
sebelum implementasi ze_json dimulai. Pencatatan dilakukan melalui sampling
pemanfaatan prosesor dan beban rata-rata (load average) pada interval tetap setiap
hari selama periode observasi, disertai identitas waktu pengambilan. Data beban
prosesor harian ini berfungsi sebagai garis dasar perilaku server sehari-hari, sehingga
perubahan beban prosesor pasca-implementasi dapat dibedakan secara jelas antara
dampak parser dan variasi operasional yang alami.
