#set text(
	font: "Times New Roman",
	size: 12pt,
	lang: "id",
)

#set page(
	paper: "a4",
	margin: (
		top: 3.5cm,
		left: 4cm,
		bottom: 2cm,
		right: 3.5cm,
	),
	number-align: center,
)

#set outline(
	title: none
)

#set par(
	leading: 1em,
	spacing: 1.5em,
)

#show figure.where(kind: table): set figure.caption(position: top)

#set figure.caption(separator: " ")

#set figure(numbering: n => {
  let chap = counter(heading).get().at(0, default: 1)
  str(chap) + "." + str(n)
})

#show heading.where(level: 1): it => {
	counter(figure.where(kind: table)).update(0)
  counter(figure.where(kind: image)).update(0)
	set align(center)
	it
}

#show outline.entry.where(level: 1): it => {
	set text(size: 14pt)
	set align(left)
	show regex("\s*\n\s*"): " "
	it
}

#show outline.entry.where(level: 2): it => {
	set text(size: 12pt)
	set align(left)
	show regex("\s*\n\s*"): " "
	it
}

#include "pages/001-judul.typ"
#set page(numbering: "i")
#include "pages/002-persetujuan_proposal.typ"
#set par(justify: true)
#include "pages/003-abstrak.typ"
#align(
	center, 
	heading(
		level: 1,
		numbering: none,
		outlined: true,
		text(size: 14pt, "DAFTAR ISI")
	)
)
#v(1em)
#outline(target: heading)
#pagebreak()
#align(
	center, 
	heading(
		level: 1,
		numbering: none,
		outlined: true,
		text(size: 14pt, "DAFTAR TABEL")
	)
)
#v(1em)
#outline(target: figure.where(kind: table))
#pagebreak()
#align(
	center, 
	heading(
		level: 1,
		numbering: none,
		outlined: true,
		text(size: 14pt, "DAFTAR GAMBAR")
	)
)
#v(1em)
#outline(target: figure.where(kind: image))
#pagebreak()

#set par(
	justify: true,
	first-line-indent: (
		all: true,
		amount: 2em
	)
)
#set page(numbering: "1")
#counter(page).update(1)
#include "pages/bab_1/000-pendahuluan.typ"
#include "pages/bab_2/000-tinjauan_pustaka.typ"
#include "pages/bab_3/000-metode_penelitian.typ"
#align(
	center, 
	heading(
		level: 1,
		numbering: none,
		outlined: true,
		text(size: 14pt, "DAFTAR PUSTAKA")
	)
)
#bibliography("../../assets/bib/cites.bib", style: "apa", title: none)
#pagebreak()
#include "pages/004-riwayat_hidup.typ"