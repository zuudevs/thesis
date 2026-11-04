#let metadata = json("../metadata.json")

#set par(
	leading: 0.5em
)

#align(center)[
	= ABSTRAK \ \

	#text(size: 14pt, lang: "id")[
		#upper(metadata.student.full_name). #metadata.document.title.primary. Dibimbing oleh #metadata.lecture.thesis_supervisor.full_name #metadata.lecture.thesis_supervisor.suffixes.join(", ") \
		#align(left)[
			Aplikasi pelaporan otomatis Laboratorium Software Architecture and Quality (SAQ)
			memproses hampir seluruh datanya dalam format _JSON_, baik dokumen basis data,
			berkas konfigurasi, maupun payload antarmuka. Jalur pemrosesan saat ini
			mengandalkan JSON.parse bawaan runtime JavaScript yang membentuk struktur DOM
			utuh dari setiap dokumen, padahal pola akses aplikasi bersifat parsial sehingga
			biaya waktu prosesor dan memori yang dibayar tidak proporsional terhadap
			kebutuhan. Penelitian ini bertujuan mengevaluasi kelayakan _Parser_ _JSON_
			On-Demand ze_json, yaitu _parser_ _JSON_ _on-demand_ satu lintasan berbasis C++23
			dengan pemindaian struktural _SWAR_ yang dikompilasi ke _WebAssembly_ 64-bit, pada
			aplikasi SAQ. Metode yang digunakan adalah studi kasus dengan desain
			eksperimen kuantitatif berbanding antara baseline JSON.parse dan perlakuan
			ze_json pada lingkungan tertutup dengan perangkat keras identik. Data
			dikumpulkan melalui benchmark latensi dalam satuan nanosecond dan nanosecond
			per operasi (ns/op) pada tiga mode pengukuran, yaitu parsing murni, pembacaan
			berkas disertai parsing, dan penggandaan nilai _repository_, terhadap korpus
			_fixture_ deterministik yang diturunkan dari struktur data SAQ, disertai snapshot
			memori, pencatatan event pengumpul sampah, serta pengukuran beban prosesor
			harian sebelum dan sesudah implementasi. Data dianalisis dengan statistik
			deskriptif berbasis persentil dan interval kepercayaan 95% serta uji perbandingan
			distribusi pada taraf signifikansi 5%. Hasil yang diharapkan dari penelitian
			ini adalah keputusan kelayakan penerapan ze_json beserta pemetaan pertukaran
			beban antara konsumsi memori dan beban prosesor, sehingga migrasi lapisan
			pembacaan JSON aplikasi SAQ dapat dilakukan secara terukur.
			#align(left)[
				Kata kunci: _#metadata.document.keywords.join(", ")_
			]
		]
	]
	#pagebreak()

	*ABSTRACT* \ \

	#text(size: 14pt, lang: "en")[
		#upper(metadata.student.full_name). #metadata.document.title.primary. Supervised by #metadata.lecture.thesis_supervisor.full_name #metadata.lecture.thesis_supervisor.suffixes.join(", ") \
		#align(left)[
			Almost all data handled by the automatic reporting application of the Software
			Architecture and Quality (SAQ) laboratory is exchanged in JSON format, whether
			as database documents, configuration files, or interface payloads. The current
			pipeline relies on the JavaScript runtime built-in JSON.parse, which materializes
			a full DOM for every document, even though the application accesses only a small
			fraction of each document. As a result, processor time and memory are spent
			disproportionately to actual needs. This research evaluates the feasibility of
			ze_json, an on-demand single-pass JSON parser written in C++23 with SWAR
			structural scanning compiled to 64-bit WebAssembly, applied to the SAQ
			application. The method is a case study with a controlled quantitative
			comparison between the JSON.parse baseline and the ze_json treatment on a
			closed environment with identical hardware. Data are collected through
			benchmarks of parser invocation latency in nanoseconds and nanoseconds per
			operation (ns/op) across three measurement modes, namely parse-only,
			file-read-parse, and repository value cloning, against a deterministic fixture
			corpus derived from SAQ data structures, complemented by memory snapshots,
			garbage collection events, and daily CPU load measurements before and after
			implementation. The data are analyzed with percentile-based descriptive
			statistics, 95% confidence intervals, and distribution comparison tests at a
			5% significance level. The expected outcome is a feasibility decision for
			ze_json adoption together with an explicit mapping of the memory-versus-CPU
			trade-off, so that the migration of the SAQ JSON reading layer can be carried
			out measurably.
			#align(left)[
				Keywords: _JSON parser, WebAssembly, on-demand parsing, SWAR, performance benchmark_
			]
		]
	]
]


#pagebreak()
