Sejalan dengan rumusan masalah, tujuan penelitian ini adalah:
#block(inset: (left: 2em))[
+ Mengukur dan mendokumentasikan kinerja baseline jalur pemrosesan JSON aplikasi pelaporan SAQ, mencakup latensi pemanggilan fungsi parser dalam satuan nanosecond dan ns/op, throughput, serta konsumsi memori, disertai pencatatan beban prosesor harian sebelum implementasi.
+ Merancang dan mengimplementasikan integrasi Parser JSON On-Demand ze_json berbasis SWAR dan WebAssembly 64-bit ke lapisan repository aplikasi pelaporan SAQ melalui antarmuka binding JavaScript.
+ Mengevaluasi perbandingan kinerja antara baseline dan hasil implementasi Parser JSON On-Demand ze_json secara kuantitatif pada lingkungan pengujian tertutup (close environment) dengan perangkat keras yang persis sama.
+ Menganalisis pertukaran beban antara konsumsi memori dan beban prosesor yang ditimbulkan oleh strategi parsing on-demand, sehingga diperoleh rekomendasi kelayakan penerapan pada aplikasi pelaporan SAQ.
]