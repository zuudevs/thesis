Hipotesis penelitian dibangun atas premis bahwa metode yang berhasil dibuktikan pada
sebuah paper akan menyelesaikan masalah serupa pada studi kasus apabila kondisi
eksekusi dikendalikan dengan benar. Berdasarkan premis tersebut, hipotesis yang
diuji dalam penelitian ini adalah sebagai berikut:
#block(inset: (left: 2em))[
	*H#sub[0]* : Tidak terdapat perbedaan yang signifikan antara baseline JSON.parse bawaan runtime dan Parser JSON On-Demand ze_json terhadap latensi pemanggilan parser, throughput, dan konsumsi memori pada aplikasi pelaporan SAQ.

	*H#sub[1]* : Penerapan Parser JSON On-Demand ze_json pada aplikasi pelaporan SAQ menurunkan latensi pemanggilan parser (nanosecond dan ns/op) serta konsumsi memori secara signifikan dibandingkan baseline, dengan kenaikan beban prosesor yang terkendali, pada lingkungan pengujian tertutup dengan perangkat keras yang identik.
]
Hipotesis diuji melalui eksperimen terkendali yang dirancang pada Bab III, dengan
tingkat signifikansi 5%.