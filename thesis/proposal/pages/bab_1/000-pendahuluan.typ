= BAB I \ PENDAHULUAN

#set heading(
	numbering: (..nums) => {
		let parts = nums.pos()
		if parts.len() > 1 { parts.map(str).join(".") }
	}
)

#context counter(heading).update(1)

== Latar Belakang
#include "001-latar_belakang.typ"
== Rumusan Masalah
#include "002-rumusan_masalah.typ"
== Tujuan
#include "003-tujuan.typ"
== Manfaat
#include "004-manfaat.typ"
== Ruang Lingkup Masalah
#include "005-ruang_lingkup_masalah.typ"
== Keberharuan
#include "006-keberharuan.typ"
#pagebreak()