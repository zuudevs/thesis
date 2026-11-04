Laboratorium Software Architecture and Quality (SAQ) Institut Teknologi PLN mengelola
aktivitas praktikum melalui aplikasi pelaporan otomatis berbasis web. Aplikasi tersebut
dibangun di atas runtime Node.js dengan kerangka kerja Express dan basis data MongoDB,
serta melayani pencatatan data asisten, dosen, mata kuliah, jadwal, laporan harian,
rekapitulasi, hingga pengiriman pengingat melalui WhatsApp. Hampir seluruh perpindahan
data pada aplikasi ini berlangsung dalam format JavaScript Object Notation (JSON):
dokumen pada MongoDB diserialisasi sebagai JSON, konfigurasi aplikasi tersimpan sebagai
berkas JSON, dan payload antara klien dengan server juga berbentuk JSON. Popularitas
format ini tidak terlepas dari sifatnya yang ringan, berbasis teks, dan independen
terhadap bahasa pemrograman @10.17487_RFC8259.

Di balik popularitasnya, pemrosesan JSON merupakan salah satu titik sempit (bottleneck)
kinerja yang paling umum pada aplikasi data-intensif. Sebagian besar pustaka parser JSON
mengadopsi strategi konvensional berbasis Document Object Model (DOM), yaitu mengonversi
seluruh teks masukan menjadi pohon data yang utama di memori sebelum aplikasi dapat
membaca nilainya @10.48550_arXiv.1902.08318. Pembentukan pohon penuh ini mahal: biaya
waktu dan memori dibayar untuk seluruh struktur dokumen, termasuk bagian yang tidak akan
pernah dibaca oleh aplikasi. Rangkaian penelitian menunjukkan bahwa menghilangkan pohon
parse dari jalur pemrosesan dapat menekan konsumsi memori hingga 95% pada beban kerja
analitik @10.1145_3297858.3304008, dan bahwa strategi malas (lazy) secara konsisten
mengurangi biaya pemrosesan dokumen berpohon @10.1145_585058.585075. Keberlanjutan
isu ini tampak pada arah penelitian mutakhir yang memindahkan validasi dan pembacaan
JSON ke skema mengalir (streaming) tanpa memuat dokumen utuh ke memori
@10.14778_3778092.3778109.

Kondisi serupa dijumpai pada aplikasi pelaporan SAQ. Jalur pembacaan data pada lapisan
repository memanggil JSON.parse bawaan runtime terhadap seluruh isi berkas atau dokumen
setiap kali data diakses, sedangkan jalur penyimpanan memori (deep clone) bahkan
melakukan serialisasi dan parsing ulang secara berpasangan. Padahal pola akses aplikasi
tergolong parsial: sebagian besar operasi hanya membutuhkan sebagian kecil kolom dari
suatu dokumen, misalnya daftar nama asisten untuk penyusunan jadwal, atau satu field
konfigurasi untuk pengingat harian. Biaya pembentukan DOM utuh untuk kebutuhan akses
parsial tersebut menimbulkan pemborosan dua arah, yaitu waktu prosesor untuk parsing
yang tidak perlu dan tekanan pengumpul sampah (garbage collector) atas objek sementara
yang cepat terbuang. Pada sisi aplikasi lab yang berjalan terus-menerus sebagai layanan,
pemborosan ini bermuara pada konsumsi memori yang meningkat dan waktu respons yang
tidak stabil.

Pendekatan parsing on-demand menawarkan alternatif yang relevan dengan masalah tersebut.
Antarmuka on-demand hadir bagi pemrogram seperti parser berbasis DOM biasa, tetapi
implementasinya hanya menggerakkan penunjuk melalui teks masukan dan melakukan
materialisasi nilai secara malas, yaitu hanya saat nilai benar-benar diminta
@10.1002_spe.3313. Kecepatan pendekatan ini ditopang teknik SWAR (SIMD Within A
Register) dan instruksi SIMD yang memindai struktur dokumen secara bit-paralel dalam
satu lintasan @10.48550_arXiv.1902.08318. Keluarga teknik yang sama terbukti efektif
pada berbagai konteks pemrosesan JSON, mulai dari pemilihan (projection) dan filter
yang didorong masuk ke parser @10.14778_3115404.3115416, pemfilteran data mentah
sebelum parsing @10.14778_3236187.3236207, pemajuan cepat (fast-forward) atas
substruktur yang tidak relevan terhadap kueri @10.1145_3503222.3507719, hingga
pembangunan indeks struktural @10.14778_3436905.3436926. Pendekatan on-demand juga
sudah diadopsi oleh sistem produksi seperti Node.js, Apache Doris, Milvus, dan Velox
@10.1002_spe.3313.

Untuk menghadirkan implementasi parser berkinerja tinggi ke dalam aplikasi Node.js,
diperlukan jembatan eksekusi lintas bahasa. WebAssembly (Wasm) menyediakan format
biner ringkas dengan lingkungan eksekusi terpasir (sandboxed) yang dapat dipanggil
langsung dari JavaScript @10.1145_3714465. Studi empiris menunjukkan bahwa Wasm
secara umum berkinerja lebih cepat daripada JavaScript dan mendekati kinerja kode
native pada banyak kasus @10.1109_CLEI53233.2021.9640153 @10.1109_IcETRAN62308.2024.10645198,
termasuk pada beban kerja komputasi di sisi server @10.1145_3572848.3577436. Ekosistem
Node.js sendiri telah memuat ratusan paket yang mengintegrasikan modul Wasm ke dalam
aplikasi produksi @10.1145_3744916.3764533, sehingga pola integrasi parser Wasm pada
aplikasi server berbasis JavaScript tergolong matang dan teruji.

Meskipun demikian, adopsi parser on-demand bukan keputusan tanpa risiko. Secara
arsitektural, penghilangan DOM akan meringankan beban memori, tetapi beban komputasi
parsing yang semula terjadi satu kali lalu dihindari kini berpindah ke prosesor setiap
kali data diakses. Interaksi antara modul Wasm dan JavaScript juga menimbulkan biaya
persilangan memori (bridge crossing) yang perlu diperhitungkan @10.31649_vitce_2.2026.121,
sementara variasi kinerja antar runtime dan antar lingkungan eksekusi dapat menutupi
atau melebarkan keunggulan yang dilaporkan literatur @10.1145_3487552.3487827
@10.1109_ASE56229.2023.00088. Dengan kata lain, angka percepatan pada korpus benchmark
generik belum tentu terulang pada aplikasi nyata yang memiliki pola akses, ukuran
payload, dan lingkungan penerapan yang berbeda.

Di sinilah celah penelitian (research gap) penelitian ini berada. Rangkaian karya
terdahulu menguji parser on-demand dan SWAR terutama pada korpus benchmark sintetis
atau beban kerja analitik skala besar @10.48550_arXiv.1902.08318 @10.1145_3503222.3507719,
sedangkan bukti penerapannya pada aplikasi pelaporan operasional dengan pola akses
parsial dan payload menengah masih terbatas. Penelitian ini berangkat dari premis bahwa
metode yang terbukti berhasil pada sebuah paper akan tetap menyelesaikan masalah pada
studi kasus apabila kondisi eksekusinya dikendalikan dengan benar; premis tersebut
dinyatakan secara eksplisit sebagai hipotesis dan diuji secara empiris. Studi kasus
yang dipilih adalah aplikasi pelaporan otomatis SAQ, dengan teknik baru yang diadopsi
berupa Parser JSON On-Demand ze_json: _parser JSON_ on-demand satu lintasan berbasis
C++23 dengan pemindaian struktural SWAR yang dikompilasi ke WebAssembly 64-bit dan
diekspos ke runtime Node.js melalui antarmuka binding JavaScript.

Melalui studi kasus tersebut, penelitian ini mengevaluasi kualitas kinerja dengan
membandingkan baseline aplikasi SAQ saat ini (sebelum menggunakan ze_json) dengan hasil
setelah implementasi, pada lingkungan perangkat keras yang identik dan tertutup.
Pengukuran dilakukan dalam satuan nanosecond dan nanosecond per operasi (ns/op) atas
pemanggilan fungsi parser, disertai pencatatan beban prosesor harian sebelum
implementasi agar dampak teknis yang teramati dapat dikaitkan secara langsung dengan
perubahan parser, bukan dengan variasi lingkungan. Dengan demikian, penelitian ini
diharapkan memberikan dua kontribusi sekaligus: bukti empiris kelayakan parser
on-demand pada aplikasi pelaporan nyata, dan metodologi evaluasi yang tertib dalam
menghindari bias lingkungan.
