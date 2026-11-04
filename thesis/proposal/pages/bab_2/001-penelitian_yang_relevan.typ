#let p(k) = cite(label(k), form: "prose")

Penelitian yang relevan ditinjau dari tiga arus utama, yaitu strategi parsing JSON,
teknik akselerasi pemindaian struktural, dan penggunaan WebAssembly pada aplikasi
produksi. Hasil penelaahan dirangkum pada @tbl-relevan.

Penelitian #p("10.1002_spe.3313") menjadi acuan utama penelitian ini. Mereka
merancang antarmuka parsing on-demand yang terlihat seperti pendekatan berbasis DOM
bagi pemrogram, tetapi secara internal hanya menggerakkan penunjuk melalui teks
masukan dan mengalirkan (streaming) struktur dokumen tanpa membentuk pohon parse.
Hasil benchmark pada prosesor komoditas terkini menunjukkan kinerja unggul
dibandingkan pendekatan konvensional, dan antarmuka tersebut telah diadopsi sistem
produksi seperti Node.js, Apache Doris, Milvus, dan Velox. Kebaruan yang sama, yaitu
pemrosesan malas, sejatinya telah dirintis pada konteks XML oleh
#p("10.1145_585058.585075") yang menunjukkan bahwa pendekatan lazy unggul secara
kinerja dibandingkan pemrosesan pohon penuh.

Pada arus akselerasi pemindaian struktural, #p("10.48550_arXiv.1902.08318")
memperkenalkan parser simdjson yang menjadi parser validasi pertama yang mampu
memproses gigabyte per detik pada satu inti prosesor dengan memanfaatkan instruksi
SIMD, sekaligus membuktikan bahwa masalah parsing yang sudah dianggap matang masih
menyimpan ruang percepatan berarti. #p("10.14778_3115404.3115416") dengan Mison
membangun indeks struktural untuk melompat langsung ke posisi field yang diminta;
#p("10.14778_3236187.3236207") dengan Sparser memfilter data mentah sebelum tahap
parsing yang mahal; #p("10.1145_3503222.3507719") dengan JSONSki memajukan cepat
substruktur yang tidak relevan terhadap kueri; sementara
#p("10.1145_3297858.3304008") dengan JPStream membuktikan bahwa menghilangkan pohon
parse dari jalur pemrosesan menekan konsumsi memori hingga 95% pada beban kerja
analitik. Ke arah validasi, #p("10.14778_3778092.3778109") menunjukkan bahwa
validasi JSON yang mengalir dapat berjalan dengan memori jauh lebih kecil dan lebih
cepat daripada algoritme luring yang menuntut dokumen utuh berada di memori. Semua
temuan tersebut mengonsolidasikan argumen bahwa pemrosesan JSON parsial pada aplikasi
dengan pola akses parsial layak menempuh jalur tanpa pohon parse.

Pada arus WebAssembly, #p("10.1145_3714465") menyusun tinjauan sistematis atas 103
karya riset runtime Wasm dan menegaskan peran Wasm sebagai lingkungan eksekusi aman,
hemat memori, dan portabel di luar peramban. #p("10.1145_3487552.3487827") menemukan
bahwa kinerja Wasm berbanding JavaScript sangat bergantung pada lingkungan eksekusi,
sehingga perbandingan kinerja wajib disertai dokumentasi lingkungan; temuan ini
mendasari kebijakan pengukuran pada penelitian ini. Pada sisi penerapan,
#p("10.1109_CLEI53233.2021.9640153") serta #p("10.1109_IcETRAN62308.2024.10645198")
menunjukkan bahwa Wasm umumnya lebih cepat daripada JavaScript dan mendekati kinerja
native pada berbagai lingkungan non-peramban dan aplikasi web berkinerja tinggi,
sementara #p("10.1145_3572848.3577436") membuktikan kelayakan Wasm sebagai format
distribusi aplikasi berkinerja tinggi. Khusus pada ekosistem Node.js, studi empiris
#p("10.1145_3744916.3764533") atas ratusan paket produksi menegaskan bahwa pola
integrasi JavaScript-Wasm telah mapan, dan studi #p("10.1109_ICT4S55073.2022.00014")
serta #p("10.1145_3593434.3593454") menyoroti dimensi energi yang perlu
diperhitungkan pada pemilihan bahasa sumber dan runtime. Biaya persilangan memori
antara Wasm dan JavaScript dikuantifikasi oleh #p("10.31649_vitce_2.2026.121"),
sedangkan variasi kinerja antar runtime Wasm di sisi server didokumentasikan oleh
#p("10.1109_ASE56229.2023.00088"). Temuan-temuan ini menegaskan bahwa integrasi
parser C++ ke Node.js melalui Wasm teruji, tetapi hasil pengukurannya sensitif
terhadap lingkungan.

Terakhir, pada arus metodologi pengukuran, #p("10.1145_2807591.2807644") menunjukkan
bahwa praktik pelaporan kinerja pada literatur komputasi kerap kekurangan ketertiban
statistik dan mengusulkan aturan minimal eksperimen yang dapat ditafsirkan, termasuk
perlunya interval kepercayaan dan kejelasan kondisi perangkat keras.
#p("10.1109_PMBS56514.2022.00011") menekankan pemanfaatan penghitung perangkat keras
yang portabel antar arsitektur untuk menghubungkan pengukuran dengan karakter
algoritme. Kedua rujukan ini menjadi dasar perancangan instrumen dan analisis data
pada Bab III.

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, left, left, left),
    table.header([*Peneliti*], [*Fokus*], [*Hasil utama*], [*Relevansi*]),
    [#p("10.1002_spe.3313")],
    [Antarmuka parsing JSON on-demand],
    [Kinerja unggul tanpa pohon parse; diadopsi Node.js, Doris, Milvus, Velox],
    [Metode inti yang diuji pada studi kasus],
    [#p("10.48550_arXiv.1902.08318")],
    [Parser SIMD (simdjson)],
    [Pemrosesan gigabyte per detik pada satu inti dengan SWAR/SIMD],
    [Dasar teknik pemindaian struktural ze_json],
    [#p("10.1145_3297858.3304008")],
    [Pemrosesan JSON tanpa pohon parse (JPStream)],
    [Penurunan konsumsi memori hingga 95% pada beban analitik],
    [Landasan hipotesis penghematan memori],
    [#p("10.1145_3503222.3507719")],
    [Fast-forward bit-paralel (JSONSki)],
    [Percepatan signifikan dengan jejak memori minimal],
    [Acuan strategi pemajuan cepat kursor],
    [#p("10.14778_3115404.3115416")],
    [Indeks struktural JSON (Mison)],
    [Lompatan langsung ke field mempercepat kueri analitik],
    [Acuan indeks malas pada object root dan array],
    [#p("10.1145_3487552.3487827")],
    [Kinerja aplikasi WebAssembly vs JavaScript],
    [Kinerja sangat bergantung lingkungan eksekusi],
    [Dasar protokol lingkungan pengukuran identik],
    [#p("10.1145_3744916.3764533")],
    [Penggunaan Wasm pada Node.js],
    [Pola integrasi JavaScript-Wasm mapan pada paket produksi],
    [Dasar kelayakan integrasi binding ke SAQ],
    [#p("10.1145_2807591.2807644")],
    [Metodologi benchmark ilmiah],
    [Aturan minimal pelaporan kinerja yang dapat ditafsirkan],
    [Dasar desain instrumen dan analisis data],
  ),
  caption: [Ringkasan penelitian yang relevan],
) <tbl-relevan>
