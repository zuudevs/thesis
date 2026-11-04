=== JavaScript Object Notation

JavaScript Object Notation (JSON) adalah format pertukaran data ringan berbasis teks
yang independen terhadap bahasa pemrograman @10.17487_RFC8259. Struktur data JSON
terdiri atas dua jenis wadah, yaitu objek yang merupakan kumpulan pasangan nama-nilai
dan larik yang merupakan kumpulan nilai berurutan, serta empat jenis nilai primitif,
yaitu string, angka, boolean, dan null. Pada aplikasi pelaporan SAQ, JSON hadir pada
hampir seluruh lapisan: dokumen MongoDB diperlakukan sebagai dokumen JSON, berkas
konfigurasi dan data master tersimpan sebagai berkas JSON, dan payload antarmuka HTTP
juga berbentuk JSON. Ubiquitas ini menjadikan biaya parsing JSON sebagai komponen
biaya yang terulang pada hampir setiap operasi aplikasi.

=== Strategi Parsing: DOM Penuh versus On-Demand

Strategi parsing konvensional berbasis DOM membaca seluruh teks masukan, memvalidasi
struktur dan karakternya, lalu membentuk pohon objek yang mewakili seluruh dokumen di
memori sebelum nilai apa pun dapat diakses. Strategi ini mudah digunakan tetapi
membebani aplikasi dengan dua biaya yang tidak selalu diperlukan: waktu pembentukan
pohon untuk bagian dokumen yang tidak dibaca dan ruang memori untuk seluruh pohon
tersebut @10.48550_arXiv.1902.08318 @10.1145_3297858.3304008.

Strategi parsing on-demand menawarkan antarmuka yang tampak serupa bagi pemrogram,
namun secara internal hanya mempertahankan penunjuk (kursor) yang bergerak maju
melalui teks masukan @10.1002_spe.3313. Nilai hanya dimaterialisasi saat diminta,
sehingga biaya parsing proporsional terhadap bagian dokumen yang benar-benar dibaca.
Untuk mendukung akses acak yang cepat, parser on-demand dapat membangun indeks malas:
pencarian field pada objek root mula-mula dilakukan secara sekuensial, dan indeks
penuh baru dibangun setelah pola kueri berulang terdeteksi @10.14778_3115404.3115416.
Akar gagasan pemrosesan malas ini telah teruji pada konteks dokumen berpohon lain,
yaitu pemrosesan XML lazy @10.1145_585058.585075.

=== SWAR dan SIMD untuk Pemindaian Struktural

SWAR (SIMD Within A Register) adalah teknik memproses beberapa unit data dalam satu
kata register secara paralel menggunakan operasi bit aritmetika-logika biasa, sedangkan
SIMD (Single Instruction, Multiple Data) adalah instruksi prosesor yang memproses
beberapa data dalam satu instruksi. Pada parsing JSON, kedua teknik dipakai untuk
memindai struktur dokumen secara bit-paralel: mengidentifikasi posisi tanda kutip,
kurung kurawal, kurung siku, dan pemisah dalam satu lintasan, sehingga posisi
struktural dapat direkam ke larik tape tanpa pengulangan teks
@10.48550_arXiv.1902.08318. Keluarga teknik ini terbukti efektif pada berbagai
variasi beban, antara lain pemfilteran data mentah sebelum parsing
@10.14778_3236187.3236207, pemajuan cepat atas substruktur yang tidak relevan
@10.1145_3503222.3507719, pembangunan indeks struktural yang dapat diparalelkan
@10.14778_3436905.3436926, serta akselerasi tugas pendukung seperti validasi UTF-8
@10.1002_spe.2920 dan parsing angka @10.1002_spe.2984.

=== WebAssembly dan Interoperabilitas dengan JavaScript

WebAssembly (Wasm) adalah format instruksi biner portabel dengan lingkungan eksekusi
terpasir yang dirancang awalnya untuk peramban, namun kini berkembang luas ke sisi
server @10.1145_3714465. Kode C++ yang dikompilasi ke Wasm dapat diekspor sebagai
fungsi dengan antarmuka biner C (C ABI) dan dipanggil langsung dari JavaScript.
Pertukaran data berlangsung melalui memori linear Wasm: sisi JavaScript menulis
payload JSON ke memori tersebut, memanggil fungsi parser, lalu membaca hasilnya
dari lokasi memori yang sama. Pola integrasi JavaScript-Wasm pada Node.js telah
mapan pada ekosistem paket produksi @10.1145_3744916.3764533, dan kinerja Wasm
secara umum berada di antara JavaScript dan kode native @10.1109_CLEI53233.2021.9640153
@10.1109_IcETRAN62308.2024.10645198. Dua sifat Wasm yang perlu diperhitungkan pada
penelitian ini adalah biaya persilangan memori antar batas runtime
@10.31649_vitce_2.2026.121 dan sensitivitas kinerja terhadap pilihan runtime serta
lingkungan eksekusi @10.1145_3487552.3487827 @10.1109_ASE56229.2023.00088.

=== Pengukuran Kinerja dan Benchmarking

Kinerja parser diukur dari latensi pemanggilan fungsi dalam satuan nanosecond dan
nanosecond per operasi (ns/op), yaitu rata-rata waktu satu operasi parsing setelah
hasil pengukuran dinormalisasi per batch. Ukuran pelengkap meliputi throughput
operasi per detik, throughput data dalam MiB per detik, serta distribusi latensi
yang dirangkum dengan persentil (median atau P50, P95, P99). Praktik pelaporan yang
baik menuntut pengulangan pengukuran yang cukup, pemaparan interval kepercayaan
(misalnya CI95), serta dokumentasi lingkungan eksekusi yang lengkap, karena selisih
angka antar lingkungan tidak dapat ditafsirkan sebagai selisih kemampuan
@10.1145_2807591.2807644. Pada pengukuran di atas runtime dengan pengumpul sampah,
faktor pendukung seperti fase warm-up, kalibrasi batch, dan pencatatan event
pengumpul sampah turut menentukan keterbacaan hasil @10.1145_3487552.3487827.

=== Pertukaran Beban Memori dan Prosesor

Perpindahan dari strategi DOM penuh ke on-demand mengubah letak beban secara
arsitektural. Pada strategi DOM, biaya parsing dibayar sekali di awal lalu hasilnya
dipertahankan di memori; pada strategi on-demand, konsumsi memori menurun karena
tidak ada pohon utuh yang dipertahankan, tetapi pekerjaan pemindaian dan navigasi
berpindah ke prosesor pada setiap akses. Pada runtime JavaScript, penurunan jumlah
objek sementara juga mengurangi tekanan pengumpul sampah, sedangkan penambahan
pemanggilan lintas batas Wasm menambah biaya tetap per kueri
@10.31649_vitce_2.2026.121. Oleh karena itu, evaluasi kelayakan parser on-demand
harus dilakukan dengan membandingkan baseline dan perlakuan pada kondisi yang
sama persis, dengan perhatian khusus pada perilaku beban prosesor jangka panjang
selain metrik latensi titik.
