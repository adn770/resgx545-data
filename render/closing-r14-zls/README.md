# r14-zls

Round 14's session r14-zls (plan `closing14/plan/rank-round14.md` sections 2, 3 and 5, rows 5 to 8;
decisions R14-1 (a), R14-7 (a), R14-9 (a), R14-10 (a) in `closing14/DECISIONS-R14.md`; records E1040
(Q243), E1041 (Q242), E1042 (Q071) and E1043 (Q120)), built with the session kit (resgx545
HACKING.md, "Session kit"), scaffolded by `tools/closing/new_session.py` from resgx545 dddadbdd001b,
data 3309b5fd9bd7. Laptop prefix `r14z`, module B60AB0B475DD1E8972419B5 (fork 2a650d74). Tool t10 =
`~/sgxfive-test-t10` (sha256 9bedc2d6..., already on the laptop), built from resgx545 a581c06
`userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76..., `TOOLSRC.sha256`) by
`lead/build_tool10.sh`, a byte copy of the published
`data:render/closing-r10-st1/lead/build_tool10.sh`
that session.toml binds as the recipe (r10-st1's binding, as r13-zls). No knob, no kernel change, no
boot, safe class only: no `expectfault` row, `#limit 0` in every stage. Round 13's r13-zls is the
direct predecessor: its forms are copied into gen/z14.py.

## What runs, in order (52 jobs, about 6 minutes of jobs, about 10 with staging)

The plan's four parts are four records; the stages group the rows by the dump their scorer reads
(the kit's REQUIRED is per row: a row without the file stops the runner, and a fixed file of a row
that a stopped stage never ran would stop the driver), so a stage may run another record's rows.
A row's name prefix is its record's: `zg-` E1040, `zo-` E1041, `zb2-` E1042, `zl-` E1043.

| Stage (dump) | Jobs | Rows | Controls (can fail) |
| --- | --- | --- | --- |
| zgran (depth store) | 11 | zg-m8, -m10, -m20, -m1008, -m1020; zg-f1, zg-f2; zb2-d12 | zg-c-ctl (E977's z243-ctl), zg-c-m4, zg-c-m40 (E1029's kept stores) |
| zodd (depth) | 13 | zo-63-f0/f1/f2, zo-65-f0/f1/f2, zo-65-ov, zo-640-f0, zo-640-ov; zb2-f2-16; zo-g3 last | zo-c-ov (E996's zov-64x32-g0), zb2-c-r16 (E1030's zbr-c16 = E997's linear dump) |
| zbits2 (stencil store) | 19 | zb2-b15, -b21 ... -b31, zb2-g21-23, zb2-g27-31; zb2-p12/p16 at 96 and 64 G 2; zg-s14 last | zb2-c-base (1024 drawn), zb2-c-set (2048, every byte 0xff), zg-c-sid (rd:14 its own) |
| zflat (depth) | 9 | zl-f6-0p25, -0p75, -0p1234, -1p0, -0p0; zl-f7-idx; zl-f5-flat | zl-c-flat (E1031's zf-flat-f6), zl-c-y6 (E986's z2y-f6) |

Frozen per record (predictions/STAGE.tsv, gen/z14.py):

- **E1040 (Q243).** The granule of the depth load base (rd:12 moved +8, +16, +32, +0x1008,
  +0x1020): G8, G16, G32, G64, H-BYTE (E1029's zb-m4 refutes it; kept as a negative). Formats 1 and
  2 with rd:12 moved +0x1000 over a `bit:10` depth fill (a store filled 0.5): I-MOVED-L32,
  I-MOVED-L16, I-UNMOVED-L32, I-UNMOVED-L16, I-STOREBASE. The stencil load base: the fork's render
  details dword 14 (`depth_arm`: `rd:14 = 0x80000000 | (stencil - base)`, sgxfive-test.c line 2739;
  the plan's [check] resolved) moved +0x1000 over an `index` stencil fill: S-MOVED, S-UNMOVED,
  S-STOREBASE, read model-free (the loaded byte is the stored one XOR 0xff where the pixel drew,
  E1030's fold read, 2048 of 2048 on E1030's kept zbs-base). Q243 retires (R14-7 (a) text fix) if
  exactly one granule holds on all five granule rows, I-MOVED-L32 or -L16 on both integer rows and
  S-MOVED on zg-s14, with the controls passing.
- **E1041 (Q242).** E996's plane at 63 x 31 (G 1) and 65 x 33 (G 2): formats 1 and 2 past the target
  INT-FLOOR-EXT (E991's rule over the whole edge tile; it holds on E977's kept z242-c rows) against
  INT-ZERO-PAST and INT-EDGE-CLAMP, each from the format-0 row of its size. Overlapping stores at 65
  x
  33 G 1 (edge tiles; one macrotile, so header order is raster there) and 640 x 480 G 2 (four
  macrotiles a side: every pair of E996's four orders parts on 33 or more slots): H-LATE/HDR (E996)
  and three rivals. E411's G 3 store base (rd:13 = 0xd000, page 12) with 20 pages, the stage's last
  row: H-NEXTTILE (pages 12, 14, 16, 18) against H-STRAY (12 and 14 only). Q242 can retire if every
  frozen E996/E991 extension holds.
- **E1042 (Q071).** Each set-half bit alone under E988's stencil test: Z-ONE-k (9), Z-GRP-21-23,
  Z-GRP-27-31, Z-GROUP, Z-ANY. The linear stencil pitch: P-64, P-W, P-G at 96 x 32 and 64 x 32, both
  G 2. Bit 12 cleared with a depth load: H-DEPTH-UNCH, H-DEPTH-LIN. Bit 16 cleared on the 16-bit
  format: L16-TILED, L16-PAIR, L16-HALF, L16-DW. Narrow: bit 0, bit 20 and the ISP's use stay.
- **E1043 (Q120).** No rule of E1031's 44-dword flat block was fitted offline (gen/flat_fit.py:
  16 0x9e markers one a tile row, at gaps of 12, 10 and 2 bytes; its first 16 bytes are E1015's F6C
  group 0 for 0.5): frozen FL-HEAD (bytes 0 to 15 F6C's for v), FL-CONST (the 44 dwords do not
  depend
  on v), FL-SHAPE (44 dwords a block, the blocks alike, the 0x9e markers at E1031's places); format
  7 under the index stencil on the flat 0.5: F7I-COMMON (the 771 dwords E986's z2y-f7 and z2d-f7
  share), F7I-COUNT (784 changed, 392 a block); format 5 on it: F5-EQ-F6. The block bytes are kept
  as
  READING lines. Narrow.

Stops: any fault or hang (the session stops, 4); a control without its reading (premise, 25); a row
without `job: ok` or with other buffer addresses or no base poke line (`hook_check`, 24: the stage
stops, the next runs): zgran's rd:12 rows (depth 0x3e001000 20 pages, store 0x3e015000), zo-g3
(depth 0x3e001000 20 pages, the rd:13 line), the rd:14 rows (stencil 0x3e013000, its store
0x3e025000); free space under 300 MiB (22). No stage ends the session on its own stop.

## Deviations from the plan

1. **Stages group rows by dump, not by record** (above): zb2-d12 runs in zgran (the zbase form; its
   controls are zgran's), zb2-c-r16 and zb2-f2-16 in zodd, zg-c-sid and zg-s14 in zbits2 (E988's
   form; their controls are zbits2's). Each model's headline is gated by its own form's controls
   (score.py GATED_BY). Counts 11, 13, 19, 9 (by part 12, 11, 20, 9 against the plan's 11, 7, 20,
   9).
2. **zgran, 12 rows by part, not 11**: zg-c-sid (the stencil row with rd:14 its own, `index` fill)
   is added so the stencil row has a control of its own shape. The integer rows fill the depth
   buffer `bit:10` (the `index` fill is denormal: every integer store would be 0) and the store 0.5
   (with E1029's 0.25 the unmoved L16 rival equals the store base). The stencil rows fill `index`
   (E988's `bytes` repeats every 256 bytes: a 0x1000 move reads the same bytes; tested on E1030's
   kept zbs-base).
3. **zodd, 11 rows by part, not 7**: the integer rows need each size's format-0 reference (E991's
   rule maps the float the same pixel stores) and the overlap rows their full-pitch references, so
   E996's plane is used for both (its floats differ at every pixel) and 65 x 33 serves both; a
   640 x 480 pair is added so "four macrotiles a side" is decided (the plan's [check]: no 65 x 33
   row
   can part the header order from raster). zo-g3 keeps E411's store base (rd:13 = 0xd000), so its
   tile rows 2 and 3 land on pages 16 and 18 as in E411, inside 20 pages.
4. **zbits2's pitch rows at G 2, not 96 x 32 G 1**: at 96 x 32 G 1 the three tiles across share
   slots (E996), and the two rows (96 and 64 wide at G 2: P-64 64/64, P-W 96/64, P-G 96/96) part
   every pair of rivals.
5. **zflat**: no rule fitted (plan section 5's fallback); the frozen rivals are structural. Format 5
   and format 7 run on the flat 0.5.

## Predicted outcomes (frozen in predictions/, [infer] where not)

- E1040: one granule of 8 to 64 bytes, no preference frozen; I-MOVED-L32 on both integer rows
  [infer: E977 read the dword as a float, E1029's base]; S-MOVED [infer: rd:14 is a base register as
  rd:12 is].
- E1041: INT-FLOOR-EXT [infer: E991 past the target at an even size], H-LATE/HDR on both overlap
  rows (E996), H-NEXTTILE [infer: E991's address rule; E411's misfit is the only reason to run it].
- E1042: one Z-ONE-k, no bit preferred; P-G [infer: E997's depth rows are 32 (G + 1) dwords];
  H-DEPTH-UNCH [infer: E1030 saw bit 12 change the stencil load only]; L16-PAIR [infer].
- E1043: FL-HEAD and FL-SHAPE hold, FL-CONST fails off 0.5 [infer: the 0x3f bytes are the
  float's]; 1.0 (the background) and 0.0 are readings; F5-EQ-F6 fails [infer: format 5 carries the
  stencil, E985].

## Replay vectors (HACKING.md "Replay vectors")

| Rows | Vectors table (closing_tables.py, `sgx545-tables`) | replay |
| --- | --- | --- |
| zg- granule, integer, stencil | `zls-load-granule` (rd:12/rd:14 move, fills, the kept store's predicted dwords) | sgx-pipe `zls` load test (the base an input with the granule that held; test first) |
| zo- | `zls-odd-edge` (size, format, the kept dump) and `zls-overlap-4mt` | sgx-pipe `zls` store (integer edge tiles at odd sizes; E996's owner rule at four macrotiles) |
| zo-g3 | `zls-scratch-g3` (pages) | sgx-pipe `check_scratch_pitch` (E411's arrangement) |
| zb2- | `zls-control-bits2` (control word, drawn count, stencil pitch, the 16-bit linear dump) | sgx-pipe `zls` (`Ctl` decode: the set-half bit, the linear stencil pitch, bit 16 with format 2) |
| zl- | `zls-flat-formats` | refused: sgx-pipe keeps formats 5 to 7 refused (Q120) unless the fold models a held rule |

The freeze pins what the replays read: `crates/sgx-pipe/src/zls.rs` and every kept dump the scorer
compares with (session.toml `[freeze] pins`).

## Commands

Every command is run through its interpreter, never by its mode bits.

- Python: `$HOME/src/resgx545/.venv/bin/python` (tests use it unless `PY` names another).
- Generator: `python3 gen/make.py` (`--check`); the flat block's look: `python3 gen/flat_fit.py`.
- Dry run: `bash lead/dryrun_checks.sh` (library mock only, Mac; output in `lead/dryrun_checks.out`:
  52 rows `job: ok`, and the kpoke files show depth_arm's pokes before each row's rd:12, rd:13,
  rd:14).
- Offline: `bash tests/run_all.sh`; freeze `python3 kit/session.py freeze .`, then again
  `bash tests/run_all.sh`.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score: `python3 score/score.py STAGE KEPT_DIR`.

Mock worlds (`mock/world.py`): model (0 everywhere), noread (premise 25 at zgran), rejected (a kpoke
row `job: rejected`: 4 at zgran), moved (the depth buffer a page higher: zgran, zodd and zbits2 stop
24 at their first base-poke row, zflat 0), f7fault (a format-7 fault: zflat 4).

Nothing here is firmware-derived; every file may go to resgx545-data.
