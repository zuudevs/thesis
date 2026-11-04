Penelitian ini menggunakan metode studi kasus yang diaplikasikan pada perangkat lunak
pelaporan otomatis SAQ, dengan desain eksperimen kuantitatif berbanding (comparative
experiment) antara kondisi baseline dan kondisi perlakuan. Studi kasus dipilih karena
penelitian bertujuan menjawab pertanyaan kelayakan teknik pada satu aplikasi nyata
dengan konteks operasionalnya, sedangkan desain eksperimen dipilih karena variabel
yang diuji bersifat terukur dan terkontrol. Satu-satunya variabel yang diubah antara
kedua kondisi adalah komponen parser pada jalur pemrosesan JSON; seluruh variabel
lain dipertahankan konstan.

=== Justifikasi Kendala Teknik dan Teknik yang Diadopsi

Kendala teknik pada jalur pemrosesan JSON aplikasi SAQ saat ini, beserta teknik baru
yang diadopsi untuk menutupi setiap kendala, dirasionalkan pada @tbl-kendala.

Kendala pertama adalah pemborosan akibat pembentukan DOM utuh. Setiap pemanggilan
JSON.parse membayar biaya validasi, alokasi, dan pembentukan objek untuk seluruh
dokumen, padahal pola akses aplikasi bersifat parsial. Strategi parsing on-demand
menutup kendala ini dengan mengganti pohon parse menjadi kursor maju tunggal yang
mematerialisasi nilai hanya saat diminta @10.1002_spe.3313. Kendala kedua adalah biaya
pemindaian teks per karakter pada parser konvensional; kendala ini ditutup dengan
pemindaian struktural SWAR yang merekam posisi struktur dokumen secara bit-paralel
dalam satu lintasan @10.48550_arXiv.1902.08318. Kendala ketiga adalah kebutuhan
integrasi kode C++ yang berkinerja tinggi ke aplikasi Node.js; kendala ini ditutup
dengan kompilasi ze_json ke WebAssembly 64-bit yang diekspos melalui antarmuka biner
C dan binding JavaScript, mengikuti pola integrasi yang telah mapan pada ekosistem
Node.js @10.1145_3744916.3764533. Kendala keempat adalah biaya alokasi objek sementara
yang membebani pengumpul sampah; kendala ini ditutup dengan arena allocator yang
mengelola seluruh memori kerja parsing dalam satu blok dan mengosongkannya sekaligus
pada akhir siklus. Kendala kelima adalah pencarian field berulang pada objek lebar
yang bersifat sekuensial; kendala ini ditutup dengan indeks malas yang membangun
tabel posisi hanya setelah pola kueri berulang terdeteksi @10.14778_3115404.3115416.

#set par(justify: false)

#figure(
  table(
    columns: (11em, auto, auto),
    align: (left, left, left),
    table.header([*Kendala teknik saat ini*], [*Teknik yang diadopsi*], [*Dampak diharapkan*]),
    [Pembentukan DOM utuh untuk akses parsial @10.1002_spe.3313],
    [Parsing on-demand dengan materialisasi malas],
    [Konsumsi memori dan biaya parsing proporsional terhadap bagian yang dibaca],
    [Pemindaian teks per karakter yang lambat @10.48550_arXiv.1902.08318],
    [Pemindaian struktural SWAR satu lintasan],
    [Latensi pemindaian dan validasi menurun per byte],
    [Integrasi kode native C++ ke Node.js yang tidak langsung @10.1145_3744916.3764533],
    [Kompilasi WebAssembly 64-bit dengan antarmuka biner C],
    [Keunggulan kinerja C++ dapat dipanggil dari JavaScript dengan biaya integrasi rendah],
    [Banyak objek sementara yang membebani pengumpul sampah @10.1145_3487552.3487827],
    [Arena allocator satu blok per siklus parsing],
    [Alokasi dan pembebasan memori menjadi O(1) per siklus, tekanan pengumpul sampah menurun],
    [Pencarian field sekuensial pada objek lebar @10.14778_3115404.3115416],
    [Indeks malas root dan elemen array],
    [Akses berulang pada objek lebar berubah menjadi lompatan konstan],
  ),
  caption: [Kendala teknik, teknik yang diadopsi, dan dampak yang diharapkan],
) <tbl-kendala>

#set par(justify: true)

=== Mekanisme Parser JSON On-Demand ze_json

Mekanisme kerja ze_json secara high-level tersusun atas dua tahap yang terpisah
tegas, sebagaimana diilustrasikan pada @fig-mekanisme-ze-json. Tahap pertama adalah pemindaian
struktural: payload JSON mentah berkode UTF-8 dipindai sekali jalan oleh scanner
SWAR (varian scanner8, scanner32, atau scanner64 sesuai platform) yang sekaligus
memvalidasi struktur dan karakternya, lalu merekam posisi seluruh struktur dokumen
ke sebuah larik tape. Tahap kedua adalah akses on-demand: sebuah Session berisi
kursor maju tunggal dibangun di atas tape tersebut, dan aplikasi mengajukan kueri
berupa nama field atau path (misalnya "position.x" atau "items[0].name") melalui
fungsi find_field atau find_path. Kursor melompat langsung ke posisi nilai yang
diminta, dan nilai dibaca melalui getter bertipe (get_int, get_double, get_string,
get_bool) dengan salinan nol (zero-copy) untuk nilai string. Seluruh memori kerja
Session dikelola arena allocator sehingga dapat dikosongkan sekaligus setelah siklus
pembacaan selesai.

#figure(
  image("../../../../assets/images/mekanisme-ze-json.png", width: 56%),
  caption: [Mekanisme high-level Parser JSON On-Demand ze_json],
) <fig-mekanisme-ze-json>

Berdasarkan mekanisme tersebut, keterbacaan aliran data pada penelitian ini dirangkum
sebagai berikut. Masukan berupa payload JSON mentah berkode UTF-8 beserta pernyataan
kueri berupa nama field atau path. Proses berupa pemindaian struktural satu lintasan
yang menghasilkan tape, dilanjutkan navigasi kursor on-demand hingga nilai terpilih.
Keluaran berupa nilai yang diminta saja beserta tipenya, tanpa pohon DOM lengkap.
Instrumen evaluasi yang digunakan untuk mengukur keberhasilan proses ini adalah
benchmark latensi dalam satuan nanosecond dan ns/op, throughput operasi per detik,
konsumsi memori, serta pencatatan beban prosesor harian server.

=== Alur Penelitian

Tahapan penelitian dari studi literatur hingga penyusunan kesimpulan mengikuti bagan
alir pada @fig-alur-penelitian. Setelah masalah terformulasi dan terukur, desain eksperimen
disiapkan, korpus uji dibangun, baseline diukur, perlakuan diintegrasikan dan diukur,
lalu data dianalisis. Titik keputusan pada bagan menjamin validitas data sebelum
masuk tahap analisis: bila hasil pengukuran tidak dapat direproduksi, instrumen
diperbaiki melalui kalibrasi, penyesuaian warm-up, dan penguatan pencatatan metadata
lingkungan, kemudian pengukuran diulang.

#figure(
  image("../../../../assets/images/alur-penelitian.png", width: 72%),
  caption: [Bagan alir penelitian],
) <fig-alur-penelitian>

=== Desain Perbandingan Baseline dan Perlakuan

Desain perbandingan diilustrasikan pada @fig-desain-baseline-vs-treatment. Kedua kelompuk pengukuran
mengonsumsi korpus uji yang sama persis dan berjalan pada lingkungan tertutup yang
identik. Kelompok baseline mengukur jalur aplikasi saat ini, yaitu pembacaan berkas
disertai JSON.parse bawaan runtime serta penggandaan nilai repository melalui
pasangan serialisasi-parsing. Kelompok perlakuan mengukur jalur yang sama setelah
lapisan pembacaan digantikan oleh ze_json melalui binding WebAssembly. Hasil kedua
kelompok kemudian dibandingkan per fixture dan per mode pengukuran untuk
mendapatkan selisih latensi, throughput, dan memori, yang selanjutnya ditafsirkan
sebagai pertukaran beban antara memori dan prosesor.

#figure(
  image("../../../../assets/images/desain-baseline-vs-treatment.png", width: 100%),
  caption: [Desain perbandingan baseline dan perlakuan ze_json],
) <fig-desain-baseline-vs-treatment>

=== Definisi Operasional Variabel

Variabel penelitian beserta definisi operasionalnya disajikan pada @tbl-variabel.

#set par(justify: false)

#figure(
  table(
    columns: (9em, auto, auto),
    align: (left, left, left),
    table.header([*Variabel*], [*Definisi operasional*], [*Skala dan pengukuran*]),
    [Variabel independen: jenis parser],
    [Komponen parser pada jalur pembacaan JSON, dengan dua level: baseline JSON.parse bawaan runtime dan perlakuan ze_json on-demand],
    [Nominal, kategoris],
    [Variabel dependen: latensi],
    [Waktu pemanggilan fungsi parser terhadap payload identik],
    [Rasio, nanosecond dan ns/op per batch; dirangkum dengan P50, P95, P99, dan CI95],
    [Variabel dependen: throughput],
    [Banyaknya operasi parsing yang tuntas per satuan waktu dan volume data yang diproses],
    [Rasio, operasi per detik dan MiB per detik],
    [Variabel dependen: konsumsi memori],
    [Pemakaian memori proses selama pengukuran, meliputi heap, RSS, external, dan ArrayBuffer],
    [Rasio, byte; snapshot sebelum dan sesudah tiap fixture, disertai jumlah event pengumpul sampah],
    [Variabel dependen: beban prosesor harian],
    [Pemanfaatan prosesor dan load average server SAQ pada operasional sehari-hari],
    [Rasio, persen; sampling berkala harian sebelum dan sesudah implementasi],
    [Variabel kontrol: lingkungan eksekusi],
    [Perangkat keras, sistem operasi, versi runtime Node.js, basis data, dan konfigurasi benchmark yang dijaga identik antar kondisi],
    [Kategoris; dicatat pada metadata setiap run dan diverifikasi sebelum perbandingan],
    [Variabel kontrol: korpus uji],
    [Fixture JSON deterministik yang diturunkan dari struktur data aplikasi SAQ],
    [Kategoris; integritas diverifikasi dengan hash SHA-256 tiap berkas],
  ),
  caption: [Definisi operasional variabel penelitian],
) <tbl-variabel>

#set par(justify: true)
