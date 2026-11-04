=== Sumber dan Jenis Data

Data yang dikumpulkan dalam penelitian ini terdiri atas dua jenis. Data primer adalah hasil pengukuran kinerja yang diperoleh langsung dari benchmark terkendali pada lingkungan penelitian, meliputi latensi, throughput, konsumsi memori, dan beban prosesor harian. Data sekunder adalah data pendukung yang diperoleh dari dokumentasi teknis kedua perangkat lunak, berupa dokumentasi arsitektur aplikasi
SAQ, dokumentasi pustaka ze_json, serta literatur ilmiah yang menjadi dasar teknik dan metodologi @10.1002_spe.3313 @10.1145_2807591.2807644. Semua data disertai penanda waktu pengambilan agar konsistensinya dapat ditelusuri.

=== Korpus Uji

Korpus uji berupa fixture JSON deterministik yang bentuk dan skenarionya diturunkan
langsung dari kode sumber aplikasi SAQ, sehingga meniru struktur data nyata aplikasi
tanpa memuat data pengguna. Fixture terbagi ke dalam tiga kelompok: kelompok
persisted yang meniru berkas data master dan konfigurasi (asisten, dosen, mata
kuliah, jadwal, laporan, konfigurasi global), kelompok service-output yang meniru
keluaran layanan seperti jadwal terperkaya dan kisi kehadiran, serta kelompok
route-input yang meniru payload mentah masukan rute pengaturan. Setiap fixture
dicatat identitasnya meliputi ukuran berkas, tipe root, dan hash SHA-256, sehingga
kesamaan masukan antara run baseline dan run perlakuan dapat diverifikasi secara
eksak. Integritas korpus dijaga oleh manifes yang memetakan setiap fixture ke
kode sumber asalnya.

=== Teknik Pengumpulan Data

Data kinerja dikumpulkan melalui tiga teknik utama. Teknik pertama adalah benchmark
baseline terhadap JSON.parse bawaan runtime pada tiga mode pengukuran: mode
parse-only yang mengukur parsing murni terhadap string UTF-8 yang telah berada di
memori; mode file-read-parse yang mengukur jalur lengkap pembacaan berkas disertai
parsing dan ekstraksi root key, meniru jalur JsonRepository.read(); serta mode
json-clone yang mengukur pasangan serialisasi-parsing untuk penggandaan nilai
repository, meniru helper cloneJson(). Setiap mode dijalankan berurutan dengan
konkurensi satu, disertai fase warm-up dan kalibrasi batch, sehingga waktu warm-up,
pemuatan manifes, dan pembuatan hash tidak tercampur ke dalam waktu parsing.

Teknik kedua adalah benchmark perlakuan terhadap ze_json dengan metrik yang
setara. Pengukuran native dilakukan dengan Google Benchmark pada kode C++ yang sama
dengan yang dikompilasi ke WebAssembly, sedangkan pengukuran pada jalur integrasi
aplikasi dilakukan melalui binding JavaScript pada runtime Node.js, mengikuti alur
pemanggilan yang diilustrasikan pada @fig-integrasi-ze-json-saq. Payload yang sama ditulis ke memori
linear Wasm, kueri dieksekusi melalui find_path dan getter, lalu hasil dibaca;
pemilihan varian scanner dicatat pada metadata run. Kedua jalur pengukuran
menggunakan satuan yang sama, yaitu nanosecond dan ns/op, sehingga hasilnya dapat
dibandingkan secara langsung dengan baseline pada mode yang sama.

#figure(
  image("../../../../assets/images/integrasi-ze-json-saq.png", width: 56%),
  caption: [Arsitektur integrasi ze_json ke aplikasi SAQ],
) <fig-integrasi-ze-json-saq>

Teknik ketiga adalah pencatatan lingkungan eksekusi pada setiap run, terdiri atas
dua lapis. Lapis pertama adalah metadata run benchmark yang mencatat waktu mulai
dan selesai, label perangkat (device-label), nama host, model prosesor, rentang
frekuensi inti, jumlah inti logis, memori total dan bebas, load average, flag
runtime Node.js, versi runtime lengkap, konfigurasi benchmark, hash SHA-256 dan
ukuran tiap fixture, snapshot memori, serta event pengumpul sampah. Lapis kedua
adalah sidecar telemetry berkas pengukuran yang menyimpan metadata terpisah dengan
identitas run yang sama, sehingga setiap artefak hasil pengukuran selalu dapat
dilacak kondisi lingkungannya.

=== Pengukuran Beban Prosesor Harian

Beban prosesor harian server SAQ dikumpulkan sebelum implementasi dan berlanjut
setelah implementasi, melalui sampling pemanfaatan prosesor dan load average pada
interval tetap sepanjang hari operasional. Data ini tidak dimaksudkan sebagai
metrik latensi, melainkan sebagai gambaran perilaku beban server yang alami, yang
digunakan untuk tiga keperluan: memastikan pengukuran benchmark dilakukan pada
kondisi server yang tenang, menyediakan garis dasar untuk menilai perubahan beban
prosesor pasca-implementasi, dan mengidentifikasi anomali operasional seperti
penurunan frekuensi karena termal yang dapat mencemari hasil benchmark.

=== Protokol Lingkungan Tertutup

Seluruh benchmarking dilakukan dalam lingkungan tertutup (close environment):
baseline dan perlakuan diukur pada perangkat keras yang persis sama, yaitu server
SAQ, dengan konfigurasi perangkat lunak yang identik. Perbedaan perangkat antara
perangkat pengembang dan server tidak digunakan sebagai dasar perbandingan karena
akan menimbulkan derau (noise) dan bias lingkungan; setiap peningkatan atau
penurunan kinerja harus murni dapat diatribusikan kepada ze_json. Untuk menegakkan
syarat tersebut, perbandingan hanya sah apabila: (1) hash SHA-256 setiap fixture
identik antara kedua run; (2) versi runtime Node.js major.miner identik dan flag
runtime terdokumentasi; (3) setiap run diberi device-label yang jelas agar hasil
dari perangkat berbeda tidak pernah tercampur; (4) kondisi eksekusi sama, meliputi
urutan mode, durasi warm-up, parameter benchmark, dan keadaan server yang tenang
sebagaimana terverifikasi dari data beban prosesor harian; serta (5) statistik
yang dikutip adalah P50 beserta lebar CI95, bukan rata-rata tunggal
@10.1145_2807591.2807644.
