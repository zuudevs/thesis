=== Pra-pemrosesan Data

Hasil benchmark yang terkumpul dalam format JSON terlebih dahulu dinormalisasi.
Untuk setiap fixture dan mode, waktu pengukuran per batch dikonversi menjadi
latensi per operasi (ns/op), kemudian statistik ringkas dihitung: minimum,
maksimum, rata-rata, median (P50), persentil P95 dan P99 dengan metode
nearest-rank, simpangan baku populasi atas nilai yang ternormalisasi per batch,
serta interval kepercayaan 95% atas rata-rata (CI95) menggunakan varians sampel
dan aproksimasi kuantil distribusi-t. Sampel mentah per batch turut disertakan
bersama penanda waktu relatif awal mode untuk memungkinkan pemeriksaan drift atau
throttle sepanjang run. Verifikasi awal dilakukan terhadap keabsahan data: jumlah
fixture yang terdeteksi dan valid harus konsisten dengan manifes, dan seluruh hash
SHA-256 harus cocok sebelum data layak dianalisis.

=== Analisis Perbandingan Kinerja

Analisis utama adalah perbandingan baseline terhadap perlakuan. Untuk setiap pasang
(fixture, mode), selisih absolut dan relatif dihitung atas P50 dan CI95 masing-masing
kondisi; keputusan perbandingan tidak dilakukan atas rata-rata tunggal agar hasil
dapat ditafsirkan @10.1145_2807591.2807644. Hasil selanjutnya diagregasi per
kelompok korpus (persisted, service-output, route-input) dan per mode pengukuran
untuk melihat konsistensi arah perubahan. Perbedaan dinyatakan bermakna apabila
interval kepercayaan kedua kondisi tidak saling menutupi, dan selisihnya konsisten
berarah pada mayoritas fixture. Temuan yang menyimpang dari pola, misalnya fixture
dengan payload kecil yang tidak menunjukkan keunggulan, dianalisis tersendiri untuk
menghubungkan perilakunya dengan karakter payload seperti ukuran dan kedalaman
struktur.

=== Analisis Konsumsi Memori dan Pengumpul Sampah

Analisis memori membandingkan snapshot heap, RSS, external memory, dan ArrayBuffer
sebelum dan sesudah pengukuran tiap fixture pada kedua kondisi, disertai jumlah dan
durasi event pengumpul sampah selama pengukuran. Pada kondisi perlakuan, pemakaian
arena allocator dicatat sebagai konsumsi memori kerja parsing. Hasil analisis
memori digunakan untuk menilai klaim penghematan memori strategi on-demand
@10.1002_spe.3313 @10.1145_3297858.3304008 sekaligus mengidentifikasi kasus di mana
penghematan memori tercapai tanpa mengorbankan latensi.

=== Analisis Pertukaran Beban Memori dan Prosesor

Analisis pertukaran beban menghubungkan tiga sumber data: selisih latensi dan
throughput dari benchmark, selisih konsumsi memori dari snapshot, dan perubahan
beban prosesor harian server sebelum serta sesudah implementasi. Pola yang
diantisipasi adalah penurunan konsumsi memori yang disertai perpindahan pekerjaan
ke prosesor, sebagaimana sifat arsitektural parsing on-demand @10.1002_spe.3313.
Untuk setiap kelompok korpus, rasio keuntungan memori terhadap tambahan beban
prosesor dirangkum secara deskriptif, kemudian dibandingkan dengan data beban
prosesor harian untuk menilai apakah tambahan beban tersebut berdampak nyata pada
operasional server atau tetap berada di bawah variasi beban yang alami. Analisis
ini menjadi dasar jawaban atas rumusan masalah keempat.