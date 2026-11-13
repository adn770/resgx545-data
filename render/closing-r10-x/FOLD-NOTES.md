# r10-x fold notes (builder, for the fold after the run)

- Records E995 (dcmp, Q241/Q243), E996 (zov, Q242), E997 (zbits, Q071), E998 (isp0x, Q241), E999
  (sb, Q046); win0 (Q030) needs a sixth number from the lead (DECISIONS-R10.md gave E995-E999 for
  "dcmp, zov, zbits, isp0x, win0; sb and grad only if their checks pass": with sb in, either sb or
  win0 takes the lead's next free number). Draft each method with
  `tools/records/new_record.py --session DIR`.
- dcmp: the mode rows test E282's GL order on equal depths exactly at 0.5 (the flat plane stores
  0x3f000000, E977's z243-ctl store). A count other than 0 or 2048 is a reading (a partial pass,
  e.g. the plane not exact), not a model. The value rows part H-UBITS (E977's [infer]) from
  H-ABS, H-IEEE, H-CLAMP0; a held H-UBITS settles Q243's "other compare modes against NaN" and the
  negative loads, and Q241's equal-depth clause by the mode rows.
- zov: the full-pitch control's floats name each dword's pixel (distinct by construction; the
  control fails if not). A shared slot holding neither tile's value, or a mix inside one slot, is a
  reading table (dword, the pixel its float names) before any refit. H-LATE vs H-EARLY in header
  order and raster order part only at 160 x 48 and 256 x 64 (a second macrotile column).
  Format 1 at G 0 applies O10-2's floor rule (E977) to the winning tile's floats.
- zbits: equalities with E977's kept dumps; a load row's store is frozen as E977's `depth store
  #1:` line (the scorer reads one dump a row). bit 0 rows: H-E665 drawn 0 with the dumps E977
  kept; H-INERT is its null.
- isp0x: H-NULL per row; a row that differs is a reading (the `depth #1:` line, drawn, hash).
  Bit 18 was not run (E065's fault; safe class).
- sb: H-LOW16 vs H-M7 part only at field 0; at fields 1 to 3 they tie (mode 7's field 1 is the
  low half). A third image is a reading.
- win0: H-IDENT vs H-WIN part on every configuration's x and y jobs together; H-IDFULL ties
  H-IDENT where the region model has no hole (64 x 64 under 0x60000000 and 0xa0000000). If the
  E502 controls fail, the E437 program is not E502's: no row is read.
- Kit weakness for the tooling agent (README.md deviation 6): the libmock replay runs without
  `SGXFIVE_KPOKE` and does not flag rc 1 `kpoke:` ends or a probe's `failed:` line.
- sgx-pipe/sgx-sim updates (sim in sync): only from the held models; refuse what stayed unmeasured.
- Delete `.pytest_cache` (none should exist: tests/run_all.sh runs pytest with `-p
  no:cacheprovider`) and `debug/` contents are not published.
