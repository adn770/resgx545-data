# r13-tex fold notes (2026-11-13, after the run)

Attempt `out/20261113-214825`, rc 0, no stop, fault or hang; the lead accepted README.md
"Deviations" 1 (t10p: the probe-fill rows replayed by tests/test_libmock.py, not by the kit's
library-mock replay). The frozen scorer re-run on the kept files is byte-identical
(`fold/reproduce.sh`, `fold/reproduce.out`). Logs: `fold/run-r13t.log`, `fold/stage-r13t.log`.

Records: E1025 srgb3 (Q282), E1026 addr4 (Q177), E1027 t3c (Q078), E1028 sb12 (Q046).

## Post hoc (after the scores were read; fitted, not held out)

- `fold/sb12_post.py`: sb12-rep-m0-c0 failed its control (inset 3924 of 4096 against >= 4055):
  172 to 230 pixels of every colour 0 row hold words outside E383's set, at tile-periodic
  places mostly outside the triangle (17 of 172 inside), and each colour 0 row differs from E383's
  run on 390 to 799 pixels (E383's two runs: 0 to 256). Within this session the colour 1 image is
  a function of the colour 0 image of the same mode, pixel by pixel (4056 to 4096 of 4096): the
  0x66 fields stay, the 0xff fields become 0x03 or 0x00 (mode 0: 0x006600ff -> 0x00660300). So the
  words are per-pixel classes whose layout moves between sessions and whose values follow o0.
- `fold/addr4_post.py`: the uv5 corners read c + 0, 1, 2, 3 with c = 24 at 64 x 16 and at
  16 x 64; with E565's 16 (16 x 16) and 20 (32 x 8), c = 4 log2 max(W, H) fits all four shapes,
  each frozen form two.
- `fold/srgb3_tri_post.py`: no frozen trilinear form is exact; the two levels' FTZ-OUT halves
  lerped exactly at f = 16/64 and rounded nearest, ties up, fit 4091 of 4096 halves.

## R13-9 (the lead confirms)

- Q282: not retired. FTZ-OUT held on all five held-out rows and the replicate (the y stage's
  own flush, FTZ-IN refuted on three; FTZ-T64 refuted), but the trilinear row fits no frozen form
  ("other filters" open) and bytes 2 and 3 were not run.
- Q177: not retired. H-MAX held 7 of 7 (texels on u16), mode 5 sides, above and below with M
  held out (2 of 2); every frozen corner form failed (post hoc 4 log2 M).
- Q078: not retired (needs F1). Bits 12:11 decided on the forms run: 00 level 0 (9 of 9), 01
  the LOD's level, 1x the last level T0's max level allows (3 of 3, and 10 1 of 1); bit 14
  filtered moves the footprint (H-FOOT 1 of 1). Open: bit 14 on a twiddled texture (F1).
- Q046: narrowed, no verdict (control FAILED); text fix (modes 20/27 clause dropped, E999).

## For HACKING "Known tool weaknesses" (not changed in this fold)

- resgx545-data `texture/p1141/support/texmodel.py` addresses a twiddled texture in plain Morton
  order over the whole side, not E561's 16 x 16 tiles: wrong above 16 a side (it misses E564's
  an-t3b11 at pixel 16). gen/t3.py uses gen/addr.py's tile law.
- the kit's library-mock replay (tools/closing/kit/session.py `_unexpected_end`, since 287031c)
  refuses every probe of a program of ours: libsgxfive's mock (mock.c) runs only its copy shader
  and limm fills. Wanted: count the mock's own "unknown program" fault on a probe fill as not
  modelled (argv accepted, no usage line, no `job: rejected`), as tests/test_libmock.py does.
