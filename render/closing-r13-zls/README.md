# r13-zls

Round 13's session r13-zls (plan `closing13/plan/rank-round13.md` sections 2 and 3, rows 2, 8 and 9;
decisions R13-1 (a), R13-8 (a), R13-10 (a) in `closing13/DECISIONS-R13.md`; records E1029 (zbase,
Q243), E1030 (zbits, Q071) and E1031 (zfmt, Q120)), built with the session kit (resgx545 HACKING.md,
"Session kit"), scaffolded by `tools/closing/new_session.py` from resgx545 05b7039ee021, data
75d01ee20311. Laptop prefix `r13z`, module B60AB0B475DD1E8972419B5 (fork 2a650d74). Tool t10 =
`~/sgxfive-test-t10` (sha256 9bedc2d6..., already on the laptop), built from resgx545 a581c06
`userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76..., `TOOLSRC.sha256`) by
`lead/build_tool10.sh`, a byte copy of the published
`data:render/closing-r10-st1/lead/build_tool10.sh`
that session.toml binds as the recipe (r10-st1's binding; the copy's last line names
closing-r10-zls, kept byte for byte). No knob, no kernel change, no boot, safe class only: no
`expectfault` row, `#limit 0` in every stage.

## What runs, in order (33 jobs, about 3.5 minutes of jobs at 6 s, about 7 with staging)

| Stage | Jobs | Controls (can fail) | Frozen | Record |
| --- | --- | --- | --- | --- |
| zbase | 11 | zb-c-ctl (E977's z243-ctl, rd:12 re-poked to its own 0x1000: drawn 2048, store = E977's kept dump), zb-c-eq0 (E995's eq-m0: drawn 0, store = E995's), zb-c-id (identity), zb-c-off (load bits off, +0x1000: 1.0) | per stored dword: H-MOVED, H-ALIGN4K, H-ALIGNTILE, H-STOREBASE, H-UNMOVED | E1029 |
| zbits | 16 | zbs-base (E988's st1-b0: 1024 drawn), zbs-q071 (E989's q071-b0: 2048), zbr-ctl (E977's z242-c-f0, byte for byte) | Z (the test reads 0) and L (E997's linear store) per bit: c-BIT-k, c-PAIR-a+b, c-ALL, c-ANY, Z-SET | E1030 |
| zfmt | 6 | zf-y6-ctl (E986's z2y-f6, byte for byte; 212 changed) | F7K vs F7K-FIX; F6C vs F6RAW (E1015's c7_rule.py, pinned) | E1031 |

**zbase (Q243, the moved load base).** E977's z243 form on t10 (64 x 32, flat 0.5, control
0x0017500e) with the depth test never (`--poke blk:1=0x00000200`, E467's form: the store holds what
was loaded), the depth buffer `index` (a stored dword names its address), `--depth-store` filled
0x3e800000, `--depth-pages 20`, and `--kpoke-render 1:rd:12=0x1000+m`. t10 arms depth_arm's pokes
before the row's (sgxfive-test.c, pinned; `lead/dryrun_checks.out`: the library mock's kpoke file
holds `rd:12=0x1000`, `rd:13=0x15000`, then the row's `rd:12`), so the row's value is the load base.
Moves m: +0x1000, +0x4000, +0x10000, the store's own base (zb-mst: rd:12 = rd:13 = 0x15000, fills
swapped), +0x800, +0x40, +4 (the bases below a page last). Every row's farthest read (m + 8 KiB)
is inside the 20 pages (tests/test_gen.py). The rd:12 values assume t10's buffers at 0x3e001000
and 0x3e015000 (every kept t4/t10 depth job, and the library mock): `hook_check` stops the stage
(24) if a 20-page row prints other addresses or no rd:12 poke line. Q243 retires if H-MOVED holds
on all 7 moves and the four controls pass.

**zbits (Q071, bits 12, 16 and 20 alone and in pairs).** Stencil rows: E988's st1-b0 (bytes fill,
EQUAL against mask 0x01, `--isp2 0x040501ff`) with the control word 0x0017300e's bits cleared
alone (3) and in pairs (3), and the set half (15, 21-23, 27-31) alone (zbs-set); the reading is the
drawn count (1024: the loaded stencil, 2048: the test reads 0, E989). Ramp rows: E977's z242-c-f0
(80 x 40, G 2, 0x00171014) with the same clears; the reading is the dump, byte for byte E977's
(tiled) or E997's zb-clr-f0 (linear). Narrow: bit 0 with other controls and the bits' meaning stay
open; the clause each bit carries is decided if one c-BIT or c-PAIR model holds alone.

**zfmt (Q120, E1015's layouts held out).** F7K at the stencil fills 0x3f and 0x1f (equal to the
template's markers) on E986's x ramp; F6C on a 48 x 32 y ramp of another origin (depths 0.375,
0.375, 0.875; its row values from zf-y48-f0, the format-0 reference, a reading row) and on a flat
0.5 (every group of every tile, v = 0x3f000000, E977/E995's stored 0.5). Narrow: format 5, format 7
under the index stencil and format 6's variable runs stay.

Stops: any fault or hang (the session stops, 4); a control without its reading (premise, 25); a
row without `job: ok` or (zbase) other buffer addresses (hook_check, 24: the stage stops, the
next runs); free space under 300 MiB (22).

## Deviations from the plan

1. **zbase: 11 jobs, not 10.** The plan's moves (+4, +0x40, +0x1000, +0x4000, +0x10000, the store's
   offset) cannot split H-ALIGN4K from H-ALIGNTILE (each rounds +4 and +0x40 to 0 and keeps the
   others): +0x800 (one tile) is added. The plan's three controls are kept and zb-c-id (the
   identity on this form, E467's reading) is a fourth: every move is read against it.
2. **zbase uses the depth test never**, not z243-ctl's less: with an `index` load every
   less-compare fails (the indices are denormals below 0.5), so the store holds the load either
   way; never is E467's form and keeps the image out of it. zb-c-ctl keeps E977's less form.
3. **zb-mst swaps the fills** (depth 0x3e800000, store `index`): with the store's own fill every
   base-following rival predicts the same constant; swapped, H-UNMOVED (the poke not reaching the
   load) is split from the rest. H-UNMOVED is a rival the plan did not name.
4. **zbits: 16 jobs, not 15**: zbr-ctl (E977's z242-c-f0 rerun) is a control of the ramp rows'
   own shape; the plan's two controls are both stencil rows.
5. **zfmt: 6 jobs, not 5**: F6C needs each row's format-0 float, so the 48 x 32 ramp has its own
   format-0 reference (zf-y48-f0, a reading row). "A plane with equal rows in another tile" is a
   flat 0.5: every row of all four tiles is one depth, known exactly (0x3f000000).

## Predicted outcomes (frozen in predictions/, [infer] where not)

- zbase: H-MOVED on all 7 moves [infer: E058's two base registers, E467's identity read at the
  index the store writes]; the rival that survives otherwise is named by the READING line's d.
- zbits: no preference is frozen between the bits; [infer] (E997) the window controls set 12, 16 and
  20 and E337's texture attachment clears 12 and 16, so a single bit for each clause is likely.
- zfmt: F7K holds at 0x3f and 0x1f (E1015: S is the fill byte), F6C on the 48 x 32 tile-0 blocks;
  the
  edge tile's rows past the target and the flat plane are the open readings.

## Replay vectors (HACKING.md "Replay vectors")

| Stage | Vectors table (closing_tables.py, `sgx545-tables`) | replay |
| --- | --- | --- |
| zbase | `zls-load-base` (rd:12 move, fills, the kept store's first 2048 dwords) | sgx-pipe `zls` load test (the load base an input; widened test first with the held rival) |
| zbits | `zls-control-bits` (control word, the drawn count or the dump's layout) | sgx-pipe `zls` (`Ctl` decode: the linear-layout bit and the zero-read bit, test first) |
| zfmt | `zls-packed-formats` (format, fill, the kept dump's predicted dwords) | refused: sgx-pipe keeps formats 5 to 7 refused (Q120) unless the fold models F7K and F6C test first |

The freeze pins what the replays read: `crates/sgx-pipe/src/zls.rs`, the kept dumps of E977, E995,
E997, E988, E989, E986 and E1015's `c7_rule.py` (session.toml `[freeze] pins`).

## Commands

- Python: `$HOME/src/resgx545/.venv/bin/python` (tests use it unless `PY` names another).
- Generator: `python3 gen/make.py` (`--check`).
- Dry run: `bash lead/dryrun_checks.sh` (library mock only, Mac; output in
  `lead/dryrun_checks.out`).
- Offline: `bash tests/run_all.sh`; freeze `python3 kit/session.py freeze .`, then again
  `bash tests/run_all.sh`.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`.
- Score: `python3 score/score.py STAGE KEPT_DIR`.

Mock worlds (`mock/world.py`): model (0 everywhere), noread (premise 25 at zbase), rejected (a
kpoke row `job: rejected`: 4 at zbase), moved (other buffer addresses: zbase 24, zbits and zfmt
0), f7fault (a format-7 fault: zfmt 4).

Nothing here is firmware-derived; every file may go to resgx545-data.
