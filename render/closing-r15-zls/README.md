# r15-zls

Round 15's session r15-zls (plan `closing15/plan/rank-round15.md` sections 2 and 3, rows 2, 3, 7
and 8; decisions R15-1 (a), R15-6 (a), R15-7 (a), R15-8 (a) in `closing15/DECISIONS-R15.md`;
records E1050 (Q297), E1051 (Q298), E1053 (Q071) and E1054 (Q120)), built with the session kit
(resgx545 HACKING.md, "Session kit"), scaffolded by `tools/closing/new_session.py` from resgx545
158bdc5455b2, data cddc7b60b8ed. Laptop prefix `r15z`, module B60AB0B475DD1E8972419B5 (fork
2a650d74). Tool t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6..., already on the laptop), built from
resgx545 a581c06 `userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76...,
`TOOLSRC.sha256`) by `lead/build_tool10.sh`, a byte copy of the published
`data:render/closing-r10-st1/lead/build_tool10.sh` that session.toml binds as the recipe (r14-zls's
binding). No knob, no kernel change, no boot, safe class only: no `expectfault` row, `#limit 0` in
every stage, no row predicted to fault under any frozen model. Round 14's r14-zls is the direct
predecessor: its forms are copied into gen/z15.py.

## What runs, in order (52 jobs, about 6 minutes of jobs, about 10 with staging)

A row's name prefix is its record's: `zp-` E1050, `zv-` E1051, `zb3-` E1053, `zl2-` E1054. The
stages group the rows by the dump their scorer reads (REQUIRED is per row), so zp-e-st (E1050's
stencil edge row) runs in zbits3.

| Stage (dump) | Jobs | Rows | Controls (can fail) |
| --- | --- | --- | --- |
| zpass (depth store) | 12 | zp-e-dp (34 x 18), zp-19-nv, -19-ls, zp-f1, -f2 (at 0.375), zp-z0, -z125, -z75, -z1 | zp-c-id (E1029's zb-c-id), zp-c-467 (E467 on t10, 16384 drawn), zp-c-band (34 x 18 without a load) |
| zbits3 (stencil store) | 11 | zb3-b15-96, -b15-r1, -b23-96, -b23-idx, -p21-23, -p22-23; zp-e-st last | zb3-c-base, -c-set, -c-b23 (E1042's kept), zb3-c-ref1 (reference 1) |
| zflat2 (depth) | 13 | zl2-f6-0p375, -0p625, -0p9375, -0p0625; 0p1, 0p3, 0p5e20 each as f0 (reading) and f6 | zl2-c-flat (E1031), zl2-c-y6 (E986), zl2-c-f5 (E1043) |
| zovl (depth, on_stop end) | 16 | zv-ov-64-f2, -160-f2, -65-f1, -640-f1; zv-r-hi (reading); zv-i125-f1/f2, zv-im25-f1/f2; zv-b25, zv-g5, zv-g9, zv-g17 last | zv-c-ov (E996), zv-c-075 (0x00c00000), zv-c-g3 (E1041's zo-g3) |

Frozen per record (predictions/STAGE.tsv from gen/z15.py, whose docstring states every model):

- **E1050 (Q297).** The load pass over 34 x 18 edge tiles, depth (zp-e-dp) and stencil (zp-e-st):
  H-EDGE (per dword as on whole tiles: the band tested against the load, past it the loaded value)
  against H-EDGE-CLEAR (1.0 or 0 past the band) and H-EDGE-SKIP (the edge tiles take no load).
  Bit 19 with a load under never and less: H-19-RENEG against H-19-ABS. Formats 1 and 2 at 0.375:
  H-INT-PASS (the loaded dword compared as a float, E977, E1040; the floor rule stored) against
  H-INT-WORD. Triangle depths 0, 0.125, 0.75, 1 over 0.25 / 0.75 tile halves: H-PASS-Z (strict
  less, E995) against H-PASS-LE. Q297 retires (R15-6 (a), the lead confirms) if every clause's
  hypothesis (or exactly one rival) holds with the controls passing.
- **E1051 (Q298).** Overlaps in formats 2 and 1 (64 x 32 G 0, 160 x 48 G 2; 65 x 33 G 1, 640 x
  480 G 2) from kept full-pitch references by E991's floor rule: H-LATE/HDR and three rivals.
  Integer depths at the z offsets 1.25 and -0.25: H-INT-SAT, H-INT-WRAP, H-INT-SIGN. E411's
  arrangement with the buffer sized: H-E465-EXT against H-STOP16 at G 5, 9, 17; H-B25-FLOOR
  against H-B25-FF on the bit-25 row. Q298 retires if each clause's hypothesis (or one rival)
  holds; if the bit-25 row is read but no frozen form holds, Q298 narrows to it.
- **E1053 (Q071).** Bit 15 alone (96 x 32 G 2; reference flipped): H15-FAIL against H15-READFF.
  Bit 23 alone (96 x 32 G 2; the `index` fill): H23-MOD16 against H23-LOADED. Bits 21 + 23 and
  22 + 23: H-PAIR-23, H-PAIR-ZERO, H-PAIR-BASE. Narrow: bit 0, bit 20, the ISP's use stay.
- **E1054 (Q120).** FL-REC0 held out at four depths whose floats have zero low 16 bits; H-LOW16
  against H-FLATPLANE at 0.1, 0.3 and 0.5 + 2^-20, each with a format-0 twin. Narrow.

## Deviations from the plan

1. **52 jobs, not 48** (12, 11, 13, 16 against the plan's 13, 9, 13, 13 by stage; 12, 11, 13, 16
   by record with zp-e-st counted in E1050): three controls of the rows' own shape and one
   reading were added. zb3-c-ref1 (st1-b0 with the reference flipped by `--poke blk:1^=0x1`, ISP
   word 0 bits 7:0, E284) shows the flip acts before zb3-b15-r1 is read; zv-c-075 (format 1 at
   the z offset 0.75, E987's H-OFF and E977's floor rule) is the integer rows' own control;
   zv-c-g3 (E1041's zo-g3 rerun) is the sized rows' own control; zv-r-hi (format 0 at 1.25) reads
   the float the conversion meets above 1, so H-INT-SAT parts a clamp in the conversion from one
   before it [infer].
2. **zp-e-st runs in zbits3** (the stencil-store stage; zpass's rows write the depth store).
3. **Dyadic triangle depths in zpass**: 0.125 and 0.375 in place of the plan's 0.1 and 0.3, so a
   flat plane is one float at every pixel and the frozen exact store holds; zflat2's twins read
   what non-dyadic planes do.
4. **The plan's "E1040's zg-c-id"** is E1029's zb-c-id (r13-zls zbase, the identity form E1040
   used); no r14 row of that name exists.
5. **Bit 15's rival**: the plan names only H15-FAIL; H15-READFF (the test reads 0xff, alive on
   E1042's row) is the rival the reference flip parts.
6. **zpass predictions from gen/z15.py, not sgx-pipe**: a builder writes no repository file, so
   the extension of `zls::pass` (edge tiles, bit 19, the integer formats, other depths) is frozen
   here in Python (`pass_model`, checked on E977's kept z243 rows and E988's st1-e-b0); the fold
   writes it into sgx-pipe test first.

## Predicted outcomes (frozen in predictions/, [infer] where not)

- E1050: H-EDGE on both edge rows (E988's 40 x 20 post hoc), H-19-RENEG [infer: E411's bit 19
  negates what is stored], H-INT-PASS (E977, E1040), H-PASS-Z (E995).
- E1051: H-LATE/HDR on all four overlaps (E996, E1041), H-INT-SAT (E981 for -0.25; E287 for
  1.25), H-E465-EXT on G 5, 9, 17 (E991 [infer]), H-B25-FLOOR [infer: E411's base rows stored 1.0
  everywhere, so its 0xffffffff was the background's floor].
- E1053: H15-FAIL [infer], H23-MOD16 [infer: E1042's read does not follow the loaded byte's y
  bits], H-PAIR-23 [infer].
- E1054: FL-REC0 4 of 4; H-FLATPLANE at 0.5 + 2^-20 [infer: a dyadic plane is flat].

## Replay vectors (HACKING.md "Replay vectors")

| Rows | Vectors table (closing_tables.py, `sgx545-tables`) | replay |
| --- | --- | --- |
| zp- | `zpass` (size, control, fill, depth, test, the kept store) | sgx-pipe `zls::pass` (edge tiles, bit 19, formats 1 and 2, other depths; test first) |
| zv- | `zovl` (size, pitch, format, offset, the kept dump) | sgx-pipe `zls` store (16-bit and 24-bit overlaps, integer clamps) and `check_scratch_pitch` (sized pitches) |
| zb3- | `zbits3` (control word, reference, drawn count, the kept stencil store) | sgx-pipe `zls::stencil_source` (bit 23's read refused unless H23-MOD16 holds) |
| zl2- | `zflat2` | refused: sgx-pipe keeps formats 5 to 7 refused (Q120) unless the fold models a held rule |

The freeze pins what the replays read: `crates/sgx-pipe/src/zls.rs` and every kept dump the scorer
compares with (session.toml `[freeze] pins`).

## Commands

Every command is run through its interpreter, never by its mode bits.

- Python: `$HOME/src/resgx545/.venv/bin/python` (tests use it unless `PY` names another).
- Generator: `python3 gen/make.py` (`--check`).
- Dry run: `bash lead/dryrun_checks.sh` (library mock only, Mac; output in `lead/dryrun_checks.out`:
  52 rows `job: ok`, the kpoke files of zp-c-id and zv-g17).
- Offline: `bash tests/run_all.sh`; freeze `python3 kit/session.py freeze .`, then again
  `bash tests/run_all.sh`.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score: `python3 score/score.py STAGE KEPT_DIR`.

Stops: any fault or hang (4: the session stops); a control without its reading (premise, 25); a
row without `job: ok`, or a poke row with other buffer addresses or no poke line (`hook_check`,
24: zpass's zp-c-id stops zpass and the next stage runs; zovl's rd:13 rows end the session,
`on_stop = "end"`); free space under 300 MiB (22).

Mock worlds (`mock/world.py`): model (0 everywhere), noread (premise 25 at zpass), rejected (a
kpoke row `job: rejected`: 4 at zpass), moved (the depth buffer a page higher: zpass 24, zovl 24
and the session ends 24), f6fault (a format-6 fault: zflat2 4), g17fault (the last row faults:
zovl 4).

Nothing here is firmware-derived; every file may go to resgx545-data.
