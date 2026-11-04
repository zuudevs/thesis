#let checkBox = table.cell(inset: (top: 0pt), box(width: 1.5em, height: 1.5em, fill: blue, stroke: 0.5pt))
Rencana jadwal penelitian disusun untuk jangka waktu enam bulan, terhitung November
2026 sampai April 2027, sebagaimana dirinci pada @tbl-jadwal dan divisualisasikan pada
@fig-jadwal. Target pendaftaran seminar proposal diatur pada bulan November 2026, dan
seluruh tahapan berikutnya diselaraskan dengan kalender akademik semester ganjil
2026/2027 sampai semester genap 2026/2027.
#text(size: 11pt)[
#figure(
  table(
    columns: (auto, 1.5em, 1.5em, 1.5em, 1.5em, 1.5em, 1.5em, 1.5em, 1.5em, 1.5em, 1.5em, 1.5em, 1.5em),
		rows: 1.5em,
    align: (left, center, center, center, center, center, center, center),
		stroke: 0.5pt,
    table.header(
      table.cell(rowspan: 2, align: center + horizon)[*Kegiatan*],
			table.cell(colspan: 4)[*Oktober*],
			table.cell(colspan: 4)[*November*],
			table.cell(colspan: 4)[*Desember*],
      ..range(1, 5).map(it => [*#it*]),
      ..range(1, 5).map(it => [*#it*]),
      ..range(1, 5).map(it => [*#it*]),
    ),
    [Studi literatur], checkBox, checkBox, checkBox, checkBox, [], [], [], [], [], [], [], [],
    [Pengumpulan data], [], [], [], checkBox, checkBox, [], [], [], [], [], [], [],
    [Permodelan sistem], [], [], [], [], checkBox, [], [], [], [], [], [], [],
    [Pengukuran baseline], [], [], [], [], checkBox, [], [], [], [], [], [], [],
    [Implementasi ze_json], [], [], [], [], checkBox, checkBox, checkBox, [], [], [], [], [],
    [Pengukuran ze_json], [], [], [], [], [], [], checkBox, table.cell(inset: (left: 0pt, top: 0pt), box(width: 1.5em, height: 1.5em, fill: blue, stroke: 0.5pt)), [], [], [], [],
    [Analisis hasil], [], [], [], [], [], [], [], table.cell(inset: (left: 0pt, top: 0pt), box(width: 1.5em, height: 1.5em, fill: blue, stroke: 0.5pt)), checkBox, [], [], [],
    [Penyusunan laporan], [], [], [], [], [], [], [], [], checkBox, checkBox, [], [],
    [Refinisi hasil], [], [], [], [], [], [], [], [], [], checkBox, checkBox, checkBox,
  ),
  caption: [Rencana jadwal penelitian tiga bulan],
) <tbl-jadwal>
]

#figure(
  image("../../../../assets/images/jadwal-penelitian.png", width: 100%),
  caption: [Diagram Gantt rencana jadwal penelitian],
) <fig-jadwal>
