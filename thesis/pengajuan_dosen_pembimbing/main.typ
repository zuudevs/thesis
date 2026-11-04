#import "../utils/strfmt.typ": strfmt
#import "../utils/reduce.typ": reduce_name
#let metadata = json("metadata.json")

#set text(
	font: "Times New Roman",
	size: 12pt,
	lang: "id",
	spacing: 150%,
)

#set page(
	paper: "a4",
	margin: (
		top: 3.5cm,
		left: 4cm,
		bottom: 2cm,
		right: 3.5cm,
	),
)

#set par(
	leading: 0.5em,
)

#grid(
	columns: 3,
	align: start,
	column-gutter: (2em, 0.5em),
	row-gutter: 0.75em,
	"Lampiran", ":", "-",
	"Hal", ":", "Pengajuan Dosen Pembimbing",
)

Kepada Yth. \
Kepala Program Studi #metadata.student.major \
Fakultas/Sekolah #metadata.student.faculty \
#metadata.institute.full_name \

Dengan Hormat, \
Sesuai pedoman penulisan Mahasiswa #metadata.institute.full_name, dengan ini kami bersama ini disampaikan bahwa:
#block(
	inset: (left: 1em),
	align(
		center,
		grid(
			columns: 3,
			align: start,
			column-gutter: (1em, 0.25em),
			row-gutter: 0.75em,
			"Nama Mahasiswa", ":", metadata.student.full_name,
			"NIM", ":", metadata.student.id,
			"Program Studi", ":", metadata.student.major,
			"Rencana Topik Tugas Akhir", ":", metadata.document.topic.primary,
		)
	)
)

Telah memenuhi syarat untuk menyusun Tugas Akhir. untuk itu kami mengajukan calon dosen pembimbing sebagai syarat berikut:

#block(
	inset: (left: 1em),
	align(
		center,
		grid(
			columns: 3,
			align: start,
			column-gutter: (6.25em, 0.25em),
			row-gutter: 0.75em,
			..metadata
				.lecture
				.thesis_supervisor
				.enumerate(start: 1)
				.map(((idx, it)) => (
					"Nama Dosen " + str(idx),
					":",
					strfmt(
						"{0}{1} {2}",
						if it.prefixes != none { 
							it.prefixes.join(", ") 
						} else {
							""
						},
						it.full_name,
						it.suffixes.join(", ")
					)
				))
				.flatten()
		)
	)
)

Atas perhatiannya diucapkan terima kasih.
#v(6em)
#block(
	inset: (left: 0.5em),
	grid(
		columns: (35%, 32.5%, 32.5%),
		row-gutter: (0.5em),
		grid.cell(
			colspan: 3, 
			align(right)[
				Jakarta, #datetime.today().display("[day] November [year]") #h(2em)
			]
		),
		box(width: 100%, align(center, grid(
			columns: 100%,
			rows: (3.125em, auto, auto),
			[Mengetahui,\ Dosen PA],
			[#box(height: 3em)],
			[#align(left)[#strfmt(
				"{0}{1} {2}",
				if metadata.lecture.academic_advisor.prefixes != none {
					metadata.lecture.academic_advisor.prefixes.join(", ")
				} else {
					""
				},
				reduce_name(
					name: metadata.lecture.academic_advisor.full_name, 
					count: 2
				),
				metadata.lecture.academic_advisor.suffixes.join(", "),
				) \
				NIDN. #metadata.lecture.academic_advisor.id
			]]
		))),
		box(width: 100%, align(center, grid(
			rows: (3.125em, auto, auto),
			[Menyetujui,\ Dosen Pembimbing],
			[#box(height: 3em)],
			[#strfmt(
				"{0}{1} {2}", 
				if metadata.lecture.thesis_supervisor.at(0).prefixes != none {
					metadata.lecture.thesis_supervisor.prefixes.join(", ")
				} else {
					""
				}, 
				metadata.lecture.thesis_supervisor.at(0).full_name, 
				metadata.lecture.thesis_supervisor.at(0).suffixes.join(", ")
			)]
		))),
		box(width: 100%, align(center, grid(
			rows: (3.125em, auto, auto),
			[Pemohon,\ Mahasiswa],
			[#box(height: 3em)],
			[#align(left)[
				#reduce_name(
					name: metadata.student.full_name, 
					count: 2
				) \
				NIM. #metadata.student.id
			]]
		))),
	)
)