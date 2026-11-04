Berdasarkan latar belakang yang telah diuraikan, rumusan masalah penelitian ini
adalah sebagai berikut:
#block(inset: (left: 2em))[
+ Bagaimana karakteristik kinerja baseline jalur pemrosesan JSON aplikasi pelaporan SAQ saat ini, dilihat dari latensi pemanggilan parser dalam satuan nanosecond, nanosecond per operasi (ns/op), throughput, dan konsumsi memori?
+ Bagaimana rancangan integrasi Parser JSON On-Demand ze_json berbasis SWAR dan WebAssembly ke dalam lapisan pemrosesan data aplikasi pelaporan SAQ?
+ Seberapa besar perubahan kinerja aplikasi SAQ setelah implementasi Parser JSON On-Demand ze_json dibandingkan dengan baseline, pada lingkungan pengujian tertutup dengan perangkat keras yang identik?
+ Bagaimana pola pertukaran beban (trade-off) antara konsumsi memori dan beban prosesor yang ditimbulkan oleh penerapan strategi parsing on-demand pada aplikasi pelaporan SAQ?
]