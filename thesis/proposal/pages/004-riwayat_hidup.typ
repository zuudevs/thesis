#import "../../utils/strfmt.typ": strfmt

#let metadata = json("../metadata.json")

#let personalInfo = (
	"Nama mahasiswa": metadata.student.full_name,
	"Program studi": metadata.student.major,
	"NIM": metadata.student.id,
	"Tempat, tanggal lahir": strfmt(
		"{0}, {1}", 
		metadata.student.pob.city, 
		metadata.student.pob.values().slice(1).map(it => str(it)).join(" ")
	),
	"Jenis kelamin": metadata.student.sex,
	"Agama": metadata.student.religion,
	"No HP": metadata.student.phone,
	"Email": metadata.student.email,
	"Alamat rumah": strfmt(
		"{0}, {1}, {2}, {3}", 
		metadata.student.address.streets.join(", "),
		metadata.student.address.city,
		metadata.student.address.province.primary,
		metadata.student.address.zip_code,
	),
)

#text(size: 14pt)[
	#set par(
		leading: 0.5em,
		spacing: 1em,
	)
	#align(center)[
		*DAFTAR RIWAYAT HIDUP* \ 
		#v(0.5em)
		#box(
			height: 4cm,
			width: 3cm,
			stroke: 1pt + black, 
			clip: true,
			inset: (left: 4pt),
			image(
				"../../../assets/images/me.png",
				height: auto,
				width: 4cm,
				scaling: "smooth",
				fit: "cover"
			), 
		)
		#v(1em)
	]
	#grid(
		columns: 3,
		column-gutter: (50% - 6cm),
		row-gutter: 0.5em,
		grid.cell(colspan: 3)[*Data Pribadi*],
		..personalInfo
			.pairs()
			.map(((key, val)) => (key, ":", val))
			.flatten(),
		grid.cell(colspan: 3, "Pendidikan"),
		..metadata.student.academic
			.pairs()
			.map(((key, val)) => (key, ":", val))
			.flatten()
	)
	Demikianlah daftar riwayat hidup ini dibuat dengan sebenarnya.
	#align(
		right,
		grid(
			columns: 1,
			align: left,
			row-gutter: 1em,
			strfmt("{0}, {1}", metadata.institute.address.city, metadata.document.date),
			"Mahasiswa ybs.",
			box(height: 3em),
			metadata.student.full_name
		)
	)
]

#pagebreak()