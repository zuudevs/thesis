Agar penelitian tetap terarah dan dapat diselesaikan sesuai batas waktu, ruang
lingkup masalah dibatasi sebagai berikut:
#block(inset: (left: 2em))[
	+ Objek penelitian adalah aplikasi pelaporan otomatis Laboratorium SAQ yang dibangun di atas runtime Node.js, khususnya lapisan repository yang membaca, menulis, dan menggandakan data JSON (JsonRepository dan MongoJsonRepository).
	+ Teknik yang diadopsi adalah Parser JSON On-Demand ze_json, yaitu parser JSON on-demand satu lintasan berbasis C++23 dengan pemindaian struktural SWAR yang dikompilasi ke WebAssembly 64-bit dan diintegrasikan melalui binding JavaScript.
	+ Perbandingan kinerja dilakukan terhadap baseline JSON.parse bawaan runtime pada tiga skenario pengukuran, yaitu parsing murni, pembacaan berkas disertai parsing, dan penggandaan nilai repository, dengan korpus uji berupa fixture deterministik yang diturunkan dari struktur data aplikasi SAQ.
	+ Pengukuran dilakukan dalam satuan nanosecond dan ns/op pada lingkungan pengujian tertutup dengan perangkat keras identik, disertai pencatatan spesifikasi perangkat keras (prosesor, memori, penyimpanan), perangkat lunak (sistem operasi, versi runtime, basis data), serta beban prosesor harian sebelum implementasi.
	+ Perubahan fungsional yang berada di luar jalur pemrosesan JSON, seperti penataan ulang skema data, penggantian basis data, dan antarmuka pengguna, tidak termasuk dalam ruang lingkup penelitian ini.
]