# r16-zls

Round 16's session r16-zls (plan `closing16/plan/rank-round16.md` sections 2, 3 and 5, rows 2, 6,
7 and 9; decisions R16-1 (a), R16-3 (a), R16-6 (a), R16-8 (a) in `closing16/DECISIONS-R16.md`;
records E1059 (Q297), E1063 (Q071), E1064 (Q299) and E1066 (Q069)), built with the session kit
(resgx545 HACKING.md, "Session kit"), scaffolded by `tools/closing/new_session.py` from resgx545
b2b5288c82ed, data 62cb03b369ca. Laptop prefix `r16z`, module B60AB0B475DD1E8972419B5 (fork
2a650d74). Tool t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6..., already on the laptop), built from
resgx545 a581c06 `userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76...,
`TOOLSRC.sha256`) by `lead/build_tool10.sh`, a byte copy of the published
`data:render/closing-r10-st1/lead/build_tool10.sh` that session.toml binds as the recipe (r15-zls's
binding). No knob, no kernel change, no boot, safe class only: no `expectfault` row, `#limit 0` in
every stage, no row predicted to fault under any frozen model. Round 15's r15-zls is the direct
predecessor: its helpers are copied into gen/z16.py, whose docstring states every model.

## What runs, in order (49 jobs, about 6 minutes of jobs, about 10 with staging)

A row's name prefix is its record's: `zp2-` E1059, `zb4-` E1063, `zo-` E1064, `zw2-` E1066. The
stages group the rows by the dump their scorer reads (REQUIRED is per row), so E1064's stencil
overlap rows run in zbits4, E1063's d12 row in zovp and its 640 row in zoff.

| Stage (dump) | Jobs | Rows | Controls (can fail) |
| --- | --- | --- | --- |
| zpass2 (depth store) | 15 | zp2-p-K and its twin zp2-t-K right after it at 0.0625, 0.1, 0.3, 0.375, 0.625, 0.5 + 2^-20; zp2-t-z125 (the 0.125 twin, held out) | zp2-c-467 (E1050's zp-c-467), zp2-c-z125 (E1050's zp-z125, the 0.125 pass) |
| zbits4 (stencil store, depth) | 14 | zb4-b0-st, -f6, -f7, -c16; zb4-20-f6, -f7; zo-s-64, zo-s-160; zb4-23-ref, -msk, -bg last | zb4-c-base (E988/E1042), zb4-c-b23 (E1042), zb4-c-f6 (E1031) |
| zovp (depth store) | 10 | zo-p-64, zo-p-160; zo-n1-7fc, -n2-7fc, -n1-ffc, -n1-7f8, -n2-7f8; zb4-20-d12 | zo-c-64 (the no-load twin of zo-p-64: E996's owner rule), zo-c-f1 (E1050's zp-f1) |
| zoff (depth, on_stop end) | 10 | zb4-20-640; zw2-w7, -w6, -w5, -w3, -s25, -w1, -s75, -w0 last | zw2-c-0125 (E987's zw-0125) |

Frozen per record (predictions/STAGE.tsv from gen/z16.py):

- **E1059 (Q297).** E1050's zpass form at seven flat depths, each pass with its no-load twin:
  H-PASS-TWIN (the store is the twin's float where it is below the load, else the load) against
  H-PASS-OWN (the depth's own float; zp-z125 refuted it at 0.125) and, at the one-float depths
  0.375, 0.625 and 0.5 + 2^-20, H-PASS-EXACT. Q297 retires (R16-6 (a), the lead confirms) if
  H-PASS-TWIN holds on all seven pairs and H-PASS-EXACT on the three one-float depths, with both
  controls passing.
- **E1063 (Q071).** Bit 0 under E988's st1, E1031's flat format 6 and F7K and E1030's bit 16
  cleared: H-B0 (the kept twin's dumps, no colour) against H-B0-NOSTORE. Bit 20 cleared on formats
  6 and 7, E1042's d12 (bit 12 with a depth load) and E1041's 640 x 480: H-INERT20 (each its kept
  twin). Bit 23 with the reference 0x80, the compare mask 0xff and the background stencil 0x5a:
  H23-FIXED against H23-REF, H23-MASK, H23-BG. Narrow unless one H23 rival holds (R16-6).
- **E1064 (Q299).** The depth load pass over overlapping tiles (64 x 32 G 0, 160 x 48 G 2, E996's
  plane over a 0.2 load): H-OVL-PASS (E996's owner, E1050's pass) against H-OVL-FIRST and
  H-OVL-SKIP; the stencil pass at the same pitches: H-OVL-PASS against H-OVL-SKIP. Kept NaN loads
  into formats 1 and 2 under never: H-NAN-SAT against H-NAN-ZERO and H-NAN-LOW. Narrow: the fault
  clause is a planned fault (section 7 of the plan).
- **E1066 (Q069).** After OQ069 (below): w = 7/16 to 0 at s 0.5 and w 0.25 at s 0.25 and 0.75:
  H-LIN [fitted] outside BEND against H-POLYCLIP, and H-LIN-S on the s rows. Narrow (OUTSEL bit 13
  and presence bits 16 to 31 need a tool change).

## Offline gate OQ069 (done before zoff froze)

gen/oq069.py (output gen/oq069.out, written by `python3 gen/make.py`) replayed E987's zw-0125 and
E981's z2-a-f0 (w 0.125 and 0.25, every dword kept) through E1056's polygon cut, sgx-pipe
`isp::depth_cut_image` (`gen/oq069rs`, its output `gen/oq069rs.out`; z16's Python cut gives the
same counts, tests/test_gen.py), and through E987's H-LIN. H-POLYCLIP covers 8192 and 16384 of the
32768 pixels both rows drew: it fails the gate on coverage. H-LIN reproduces 31856 of 32768 dwords
of each row, and the other 912 pixels are the same set in both (BEND, from x/512 + y/256 = 0.817 to
the far corner): it passes the gate on the pixels outside BEND, so zoff runs with H-LIN frozen
[fitted] there and BEND's dwords a reading. The lead may read this as the gate failing (no form
reproduces every kept dword); then zoff is dropped and the other three stages stand alone.

## Deviations from the plan

1. **49 jobs, not 48** (15, 14, 10, 10 by stage; by record E1059 15, E1063 14, E1064 11, E1066
   9): zovp has two controls of its own forms. E1051's overlap replicate is a depth-only row and
   cannot run in the depth-store stage, so zo-c-64 (the overlap pass row without the load, its
   store E996's owner rule from the kept reference, held on E996's kept zov-64x32-g0 dword for
   dword, tests/test_score.py) replaces it, and zo-c-f1 (E1050's zp-f1) controls the NaN rows.
2. **Stages grouped by dump**: zo-s-64 and zo-s-160 (E1064) run in zbits4, zb4-20-d12 in zovp and
   zb4-20-640 in zoff.
3. **zovp's pass rows use E996's plane over a 0.2 load**, not the flat 0.375: tiles sharing a
   slot load the same dwords, so a flat plane stores the same under every owner rule; E996's plane
   gives each tile its own floats and 0.2 lies inside the plane's range in every overlapped tile
   row, so H-OVL-PASS, -FIRST and -SKIP part on both rows (390 to 1344 dwords).
4. **The stencil overlap rows part H-OVL-PASS from H-OVL-SKIP only**: the bytes a shared slot
   loads are the same for every tile, so first and last store the same.
5. **H-PASS-LE is not scored**: no row's depth equals a loaded one (0.25, 0.75), so it predicts
   what H-PASS-TWIN does; E1050 refuted it at 0.75.
6. **Bit 23's rivals** are frozen as "the read bytes are not COL23 on this rival's row and are on
   the other two": the plan names no byte form for them.
7. **zoff**: H-LIN is frozen outside BEND only (OQ069); H-LIN-S ((1.6 w + 0.4 s) t, E987's two
   points written with the far and near vertex depths, [infer]) is added for the two z-scale rows,
   which the plan's H-LIN (no s) cannot predict apart.
8. **The plan's "--kpoke-render [check: the builder names the render-details dword]"**: dword 17,
   CR_ISP_BGOBJVALS (3d.md sections 5.3 and 11.3, HWRENDERDETAILS + 0x44); t10 writes 0x300 there
   (bit 8 set, so the STENCIL byte is used), the row writes 0x35a.

## Predicted outcomes (frozen in predictions/, [infer] where not)

- E1059: H-PASS-TWIN 7 of 7 [infer: E1050's zp-z125 is a plane error], H-PASS-EXACT 3 of 3 (E1054),
  H-PASS-OWN FAILED at 0.125 (E1050) and at whichever of 0.0625, 0.1, 0.3 has a twin of more than
  one float.
- E1063: H-B0 4 of 4 [infer: E997], H-INERT20 4 of 4 [infer: E1030], H23-FIXED 3 of 3 [infer: E1053
  saw the bytes whatever was loaded]: then Q071 narrows, it does not retire.
- E1064: H-OVL-PASS on all four rows [infer: E996 with E1050], H-NAN-SAT 5 of 5 [infer: E995's NaN
  above every depth, E1051's clamp].
- E1066: H-POLYCLIP FAILED on every row (OQ069); H-LIN [fitted] at w 1/16 to 7/16 is the builder's
  guess, w 0 and the s rows least sure; on the s rows H-LIN-S [infer].

## Replay vectors (HACKING.md "Replay vectors")

| Rows | Vectors table (closing_tables.py, `sgx545-tables`) | replay |
| --- | --- | --- |
| zp2- | `zpass2` (depth, the twin's store, the pass store) | sgx-pipe `zls::pass` fed the twin's plane |
| zb4- | `zbits4` (control word, test words, the kept dumps) | sgx-pipe `zls::stencil_source` (bit 23) and `zls` store (bits 0, 20); formats 6 and 7 refused (Q120) |
| zo- | `zovp` (size, pitch, fill, the kept store) | sgx-pipe `zls::pass` over overlaps and the NaN conversion (test first) |
| zw2- | `zoff` (w, s, the kept dump) | refused unless H-LIN or H-LIN-S holds; then sgx-pipe isp/mte depth with BEND refused |

The freeze pins what the replays read: `crates/sgx-pipe/src/zls.rs`, `crates/sgx-pipe/src/isp.rs`
and every kept dump the scorer compares with (session.toml `[freeze] pins`).

## Commands

Every command is run through its interpreter, never by its mode bits.

- Python: `$HOME/src/resgx545/.venv/bin/python` (tests use it unless `PY` names another).
- Generator: `python3 gen/make.py` (`--check`); OQ069's Rust replay: `cargo run --release
  --manifest-path gen/oq069rs/Cargo.toml` with `CARGO_TARGET_DIR=debug/target`.
- Offline: `bash tests/run_all.sh`; freeze `python3 kit/session.py freeze .`, then again
  `bash tests/run_all.sh`.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score: `python3 score/score.py STAGE KEPT_DIR`.

Stops: any fault or hang (4: the session stops); a control without its reading (premise, 25); a
row without `job: ok`, zb4-23-bg without its rd:17 poke line, or zb4-20-d12 with other buffer
addresses or no rd:12 poke line (`hook_check`, 24: that stage stops and the next runs; zoff's stop
ends the session, `on_stop = "end"`); free space under 300 MiB (22).

Mock worlds (`mock/world.py`): model (0 everywhere), noread (premise 25 at zpass2), rejected (the
kpoke rows `job: rejected`: zbits4 4 at zb4-23-bg), moved (the depth buffer a page higher: zovp 24
at zb4-20-d12, zoff runs), nobg (no rd:17 poke line: zbits4 24), f7fault (a format-7 fault: zbits4
4) and w0fault (the last row faults: zoff 4).

Nothing here is firmware-derived; every file may go to resgx545-data.
