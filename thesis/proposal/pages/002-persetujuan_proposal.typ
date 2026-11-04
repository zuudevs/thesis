#let metadata = json("../metadata.json")
#import "../../utils/strfmt.typ": strfmt

#let studentInfoMatrix = (
	"Nama Mahasiswa": metadata.student.full_name,
	"NIM": metadata.student.id,
	"Program Studi": metadata.student.major,
	"Fakultas": metadata.student.faculty,
	"No. HP": metadata.student.phone,
	"Email": metadata.student.email,
)

#align(center)[
	#image(
		"../../../assets/images/itpln_logo.png",
		height: 4.5cm,
		width: 6.5cm,
		fit: "contain",
		scaling: "smooth"
	)
	#set par(leading: 0.5em)
	#heading(
		level: 1, 
		text(size: 14pt)[LEMBAR PERSETUJUAN \ PROPOSAL TUGAS AKHIR]
	) \
	#grid(
		columns: (35%, auto, auto),
		column-gutter: (1em, 0.5em),
		row-gutter: 0.5em,
		align: left,
		"Judul Proposal Tugas Akhir", ":", metadata.document.title.primary,
		"Identitas Mahasiswa", [], [],
		..studentInfoMatrix
			.pairs()
			.enumerate(start: str.to-unicode("a"))
			.map(((idx, (key, val))) => (
				strfmt(
					"{0}. {1}", 
					str.from-unicode(idx),
					key
				),
				":", val
			))
			.flatten(),
		"Jangka waktu penyelesaian tugas akhir", [], [],
		"a. Waktu mulai", ":", repeat("."),
		"b. Waktu selesai", ":", repeat("."),
		"Lokasi tempat pengambilan data", [], [],
		"a. Nama instansi", ":", "Software Architecture and Quality",
		"b. Alamat instansi", ":", strfmt(
			"{0}, {1}, {2}, {3}", 
			metadata.institute.address.streets.join(", "),
			metadata.institute.address.city,
			metadata.institute.address.province.primary,
			metadata.institute.address.zip_code,
		),
		"Nama dosen pembimbing", ":", strfmt(
			"{0}{1} {2}",
			if metadata.lecture.thesis_supervisor.prefixes == none {
				metadata.lecture.thesis_supervisor.prefixes + " "
			} else { 
				metadata.lecture.thesis_supervisor.prefixes.join(", ")
			},
			metadata.lecture.thesis_supervisor.full_name,
			metadata.lecture.thesis_supervisor.suffixes.join(", ")
		)
	)
	#grid(
		columns: 2,
		align: center,
		row-gutter: 0.25em,
		column-gutter: 4em,
		[*Disetujui*], [*#metadata.institute.address.province.secondary.at(0), #metadata.document.date*],
		[*Dosen Pembimbing*], [*#metadata.student.full_name*],
		box(height: 3em), [],
		[#repeat(".")], [#repeat(".")],
		grid.cell(colspan: 2, box(height: 1em)),
		grid.cell(colspan: 2)[*Mengetahui*],
		grid.cell(colspan: 2)[*Kepala Program Studi*],
		grid.cell(colspan: 2, box(height: 3em)),
		grid.cell(colspan: 2, line(length: 40%, stroke: (dash: "dotted")))
	)
]

#pagebreak()