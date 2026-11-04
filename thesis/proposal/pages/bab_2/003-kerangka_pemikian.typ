Kerangka pemikiran penelitian ini menghubungkan masalah nyata pada aplikasi pelaporan
SAQ dengan resep solusi yang tersedia pada literatur, kemudian menutupnya dengan
metode evaluasi yang mengendalikan bias lingkungan. Alur pemikiran tersebut diilustrasikan
pada @fig-kerangka-pemikiran.

Di sisi masalah, aplikasi SAQ memproses dokumen JSON pada setiap operasi pembacaan,
penulisan, dan penggandaan data melalui JSON.parse bawaan runtime. Pola aksesnya yang
parsial membuat biaya pembentukan DOM utuh tidak proporsional terhadap kebutuhan
aplikasi. Di sisi solusi, literatur menyediakan tiga resep yang saling melengkapi:
strategi parsing on-demand yang menghilangkan pohon parse dan mematerialisasi nilai
secara malas @10.1002_spe.3313, teknik pemindaian struktural SWAR yang menekan biaya
pemindaian per byte @10.48550_arXiv.1902.08318, serta WebAssembly sebagai jembatan
integrasi kode C++ ke runtime Node.js @10.1145_3714465 @10.1145_3744916.3764533.

Pertemuan kedua sisi tersebut menemukan celah penelitian: keunggulan yang dilaporkan
literatur diukur pada korpus generik, sedangkan bukti penerapannya pada aplikasi
pelaporan nyata belum tersedia. Celah ini dirumuskan menjadi hipotesis bahwa Parser
JSON On-Demand ze_json akan menurunkan latensi dan konsumsi memori dengan pertukaran
beban prosesor yang terkendali. Hipotesis kemudian diuji melalui metode eksperimen
terkendali baseline versus perlakuan pada lingkungan tertutup, menggunakan instrumen
pengukuran nanosecond dan ns/op dengan pencatatan lingkungan yang lengkap, dan
bermuara pada kesimpulan kelayakan penerapan ze_json pada aplikasi pelaporan otomatis
SAQ.

#figure(
  image("../../../../assets/images/kerangka-pemikiran.png", width: 90%),
  caption: [Kerangka pemikiran penelitian],
) <fig-kerangka-pemikiran>
