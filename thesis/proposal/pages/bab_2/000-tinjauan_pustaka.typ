= BAB II \ TINJAUAN PUSTAKA

#set heading(
	numbering: (..nums) => {
		let parts = nums.pos()
		if parts.len() > 1 { parts.map(str).join(".") }
	}
)

#context counter(heading).update(2)

== Penelitian yang Relevan
#include "001-penelitian_yang_relevan.typ"
== Landasan Teori
#include "002-landasan_teori.typ"
== Kerangka Pemikiran
#include "003-kerangka_pemikian.typ"
#pagebreak()