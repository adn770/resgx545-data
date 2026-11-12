# F3 post-run fix (2026-11-12)

`f3_streams.as-run.py` (sha256 in `FREEZE-f3.sha256`) took the regions from `pbdump.regions`, which
reads the region headers on the first written TA data page only (341 headers, 23 with a stream at
2048x2048), and sized an entry whose PRIM_TILES is a mask form with bit 5 set (0xa8, 0xaa, 0xac)
as 3 dwords, so it read a mask as a link and stopped at 4096x2048 (`f3_streams.as-run.out`).
`f3_streams.py` reads every header at the TA data's region offset (`dpm_words.tadata_layout`,
`mtile_grid`) and sizes those entries as 4 dwords; a link outside the dump is an error. F3 has no
verdict: its output feeds F5's constants and the burst reading, both labelled post hoc.
