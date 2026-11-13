# r9-ldpm: notes for the fold (the builder, 2026-11-13)

Kept here so that the resumed builder folds the run with what the build knew.

## Records (E960 to E963, the prompt's numbers)

- E960 (offline, Q210 and Q211, no laptop): OD-1 to OD-3 as run in `offline/`, with their freezes
  (`FREEZE-od1.sha256`, `-od2`, `-od3`, `-tables`) and OD-2's one reader fix (`OD2-FIX.md`). OD-2's
  H-NEXT1 is a FIT on 3072x3072 and 2560x2560 and SEMI on eight targets (E936 printed them); OD-3's
  H-FLUSH fitted 30 of 31 and gave 7 of 20 on E938's cells (semi-held-out), so k2 did not run. OD-1:
  E874's U equals all nine kept calibration needs, HU1 of the 500 triangles none (so HU1 is not the
  1500-vertex scene's need, and only a tally in w). Cite as
  `cited-scratch:closing9/r9-ldpm/offline/`
  or move offline/ into the published session (it is part of the freeze).
- E961 (m6b, Q210): H-NEXT1 held out at the targets where it parts from H-SPAN; replicates of E936.
- E962 (w, Q211's U clause for wide targets): E874's U at four targets wider than 2:1.
- E963 (f9b, Q211's count and Q210's band 4 raise): F9 off band 4, F9 against H-NORAISE at band 4.

## What to read after the run

- m6b: `gps_next` per cell; the dumped A_6 replicates (`--dump-render`) are for the straddling
  block b_6 = 76 and b_6 + 1 (sizes, regions, macrotiles) if H-NEXT1 holds or fails.
- w: whether every calibration's steps are E874's (H-STEPMODEL gates the cell).
- f9b: the band 4 cells' second run peak (thr0 itself = not raised, E938).

## Shared-tool gaps seen while building (report, do not fix in the fold)

- `new_session.py` writes `built_from` for every `--tool-src` tool, so the freeze's `built` line
  names a recipe for t4 whose binary was built long ago (`userspace/libsgxfive/Makefile`, the
  library's own make; the commit and source hash are R7-dpm's `TOOLSRC.sha256`).
