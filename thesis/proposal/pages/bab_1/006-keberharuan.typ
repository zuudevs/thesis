Kebaruan (novelty) penelitian ini terletak pada tiga hal berikut:
#block(inset: (left: 2em))[
	+ *Pengujian parser on-demand pada aplikasi nyata, bukan hanya korpus benchmark.* \
		Literatur yang ada mengukur keunggulan parsing on-demand dan SWAR terutama pada korpus benchmark generik atau beban kerja analitik skala besar
		@10.1002_spe.3313 
		@10.48550_arXiv.1902.08318 
		@10.1145_3503222.3507719. 
		Penelitian ini menguji teknik yang sama pada aplikasi pelaporan operasional yang memiliki pola akses parsial, payload menengah, dan tuntutan layanan berkelanjutan, sehingga menutup jarak antara bukti laboratorium dan kondisi penerapan.

	+ *Kombinasi SWAR dan WebAssembly 64-bit pada satu parser untuk runtime Node.js.* \
		Implementasi Parser JSON On-Demand ze_json memadukan pemindaian struktural bit-paralel dengan kompilasi langsung ke WebAssembly 64-bit tanpa lapisan perekat (glue) tambahan, sehingga keunggulan kinerja kode native C++ dapat dihadirkan ke dalam aplikasi JavaScript dengan biaya integrasi yang rendah @10.1145_3714465
		@10.1145_3744916.3764533.

	+ *Metodologi evaluasi yang mengendalikan bias lingkungan secara eksplisit.* \
		Perbandingan kinerja dilakukan pada lingkungan tertutup dengan perangkat keras identik, #highlight()[dilengkapi pencatatan beban prosesor harian] pra-implementasi dan metadata lingkungan pada setiap hasil pengukuran. Pendekatan ini menindaklanjuti temuan
		bahwa perbandingan kinerja lintas lingkungan kerap menghasilkan kesimpulan yang
		menyesatkan bila kondisi eksekusi tidak dikendalikan @10.1145_2807591.2807644
		@10.1145_3487552.3487827.
]