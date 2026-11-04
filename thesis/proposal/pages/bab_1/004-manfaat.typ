Manfaat yang diharapkan dari penelitian ini terbagi menjadi dua sisi.

=== Manfaat Teoretis

#block(inset: (left: 2em))[
	+ Menyediakan bukti empiris tambahan mengenai perilaku parser JSON on-demand berbasis SWAR dan WebAssembly ketika diterapkan pada aplikasi web nyata, sebagai pelengkap pengujian pada korpus benchmark generik yang telah dilakukan literatur sebelumnya @10.1002_spe.3313 @10.1145_3487552.3487827.
	+ Menyusun metodologi evaluasi kinerja parser yang mengendalikan variabel lingkungan secara tertib, termasuk pengukuran beban prosesor harian pra-implementasi dan protokol lingkungan tertutup, yang dapat menjadi acuan bagi penelitian evaluasi kinerja sejenis.
	+ Memetakan secara eksplisit pertukaran beban antara konsumsi memori dan beban prosesor sebagai konsekuensi arsitektural strategi parsing on-demand.
]

=== Manfaat praktis

#block(inset: (left: 2em))[
	+ Bagi aplikasi pelaporan SAQ, hasil penelitian memberikan dasar pengambilan keputusan apakah lapisan pembacaan JSON sebaiknya bermigrasi ke parser on-demand untuk menekan konsumsi memori dan memperbaiki stabilitas waktu respons.
	+ Bagi pengembang aplikasi Node.js lainnya, artefak integrasi berupa binding WebAssembly dapat dimanfaatkan ulang sebagai alternatif pengganti JSON.parse bawaan runtime pada pola akses data yang parsial.
	+ Bagi laboratorium, penurunan konsumsi memori dan beban prosesor berimplikasi pada pemanfaatan sumber daya server yang lebih efisien tanpa perlu penambahan perangkat keras.
]