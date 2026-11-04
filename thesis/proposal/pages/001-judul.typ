#let metadata = json("../metadata.json")
#heading(
	level: 1,
	outlined: false
)[
	#upper(metadata.document.title.primary) \ 
	#upper("SOFTWARE ARCHITECTURE AND QUALITY")
]

#align(center)[
	#text(size: 14pt)[
		#upper[\ *#metadata.document.kind* \ ]
		#image(
			"../../../assets/images/itpln_logo.png",
			height: 4.5cm,
			width: 6.5cm,
			fit: "contain",
			scaling: "smooth"
		)
		Diajukan untuk Memenuhi Sebagian Persyaratan \
		Guna Memperoleh Gelar Sarjana Komputer \ \
		Disusun Oleh: \
		#upper[
			*#underline(metadata.student.full_name)* \
			*NIM: #metadata.student.id* \ \
			*PROGRAM STUDI S1 #metadata.student.major* \
			*FAKULTAS #metadata.student.faculty* \
			*#metadata.institute.full_name* \
			*#metadata.institute.address.province.secondary.at(0)*
		]
	]
]

#pagebreak()