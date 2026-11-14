# r14-flag (round 14: the flagged stages, Q078 bit 14 with the reach mapped, Q139 H-EVEN)

A closing session built with the session kit (resgx545 HACKING.md, "Session kit"), scaffolded by
`tools/closing/new_session.py` from resgx545 c58f9f9c87aa (kit/ is that commit's blobs, as main
dddadbd's kit plus T14's guard rows) and resgx545-data 3309b5fd9bd7. Plan
`closing14/plan/rank-round14.md` sections 2 and 3 (F1, F2); decisions `closing14/DECISIONS-R14.md`:
R14-4 (a) t14, R14-5 (a) F1 and F2 after every safe session, no F3. **FLAGGED (outside the safe
class)**: the user OK'd exactly these planned faults: no hang, no reboot, no clock-gate write.
Built offline; nothing here touched the laptop, cachix or a git repository. Records E1047 (f1,
Q078) and E1048 (f2, Q139) are reserved for its fold (the builder folds it). Round 13's r13-flag
(E1033's fault pages) is the direct predecessor.

## What runs, in order: 11 jobs, about 5 minutes (8 at most)

Laptop: module B60AB0B475DD1E8972419B5 (fork 2a650d74) loaded = installed; no debugfs knob is
written (only `reset`; f2 reads `render_param` and `render_tadata`). Files under `~/scratch/r14f/`.

- t14 = `~/sgxfive-test-t14` (sha256 aa550b94...), bound by source to resgx545 c58f9f9
  `userspace/libsgxfive/tools/sgxfive-test.c` (sha256 9cef7a20...), recipe
  `lead/build_tool14.sh` (`data:render/closing-r14-flag/lead/build_tool14.sh` once published; the
  lead's build line: closing14/k14/TOOL14.built). f1 only (`probe --scratch-pages 256`).
- t10 = `~/sgxfive-test-t10` (sha256 9bedc2d6...), source resgx545 a581c06 (23e1fa76...), recipe
  `data:render/closing-r10-st1/lead/build_tool10.sh`. f2 and the health pair.

| # | stage | jobs | planned (#limit) | tool | what | controls |
|---|---|---|---|---|---|---|
| 1 | f1 | 5 | 3 | t14 | T3 bit 14 on a twiddled 32 x 32, 1 MiB scratch: E566's pair, u = x / 4096, u = 0 | the two bit-clear references, each before its rows |
| 2 | f2 | 6 | 4 | t10 | CR_TE_MTILE1 fx 14, 15 at 256 x 256 and 26, 27 at 768 x 640, TA dumps | the two unpoked baselines, each first in its size |

Planned rows are the `expectfault` rows that are not controls; `#limit` is their count (E946's
slip designed out), and in each stage the last planned row is the stage's last row. Predicted: no
fault at all (every frozen form of f1 reads inside the 1 MiB scratch; f2's H-COVER draws), so 11
jobs at about 6 to 15 s with their resets, plus staging and preflight (3 minutes): about 5
minutes; if all 7 planned rows fault (H-FAULTANY, H-FAULT23), about 40 s each with the reset and
strict health: about 8 minutes. Alarms: 15 minutes a stage.

### f1 (Q078, E1047): bit 14 on a twiddled texture with the reach mapped

E1033's form (E566's tx_map: scratch dword i reads 0xD0000000 | i; texture at the scratch's first
dword, T1 0x0C01F01F) with t14's `--scratch-pages 256`: E1033's fault pages (+0x21000, +0x40000)
now lie inside the scratch, so a read there names its dword. Rows: f1-ref-a (control, E566's
tw32-ctl byte for byte, its kept image), f1-tw32 (E566's tw32-t3b14, u in (1, 2); E1033's first
planned row again), f1-ref-b (control, u = x / 4096 bit clear: the tile law's column 0, E1033's
kept image), f1-small (u = x / 4096 with bit 14; E1033's held-out row again), f1-zero (held out,
never run: u = 0 on every pixel with bit 14). Frozen (gen/f1.py, predictions/f1.tsv and
predictions/f1/), the forms post hoc on E1033's two pages (fit/fit_e1033.py) [infer]:

- H-TWP4096: column s + floor(4096 frac(u)), E561's tile law with a tile-row pitch of 4096 texels;
- H-TWP4128: the same column, pitch W + 4096 = 4128;
- H-TWP4096-NS: column floor(4096 frac(u)) alone, pitch 4096 (parted from H-TWP4096 on f1-tw32
  only: where s = 0 they are one image);
- H-FAULTANY: every bit-14 row faults whatever is mapped (E1033, 2 of 2);
- H-MOVE0 (f1-zero): E1003's move is 0 at u = 0, so the bit-clear image.

Every form puts E1033's f1-small faults on page + 0x40000 (all its unmapped reads there or on the
next page) and f1-tw32's pixel (16, 0) on + 0x21000, the first pixel of the fill's second 16 x 16
tile [infer: only each job's first faulting page is kept; the first tile's pixels 11 to 15 read
lower unmapped pages, so the forms need that tile's read to fault first]. Retire Q078's twiddled
clause if one frozen form gives the image of all three planned rows (and the controls pass); the
images decode every read either way (READING lines).

### f2 (Q139, E1048): H-EVEN held out at fx 2 or 3 mod 4

r10-geo q139c's form (E1007) on t10: `tri --tri-full --pixels ... --keep-going --dump-render "$W"`,
CR_TE_MTILE1 poked with `--kpoke-render 1:ta:143=V` (never run: tests/test_gen.py). The header base
of each size is its unpoked baseline's (lib_dump.baseline_layout). Frozen (gen/f2.py):

- end: H-COVER [infer, post hoc on the 22 kept jobs at fx 2 or 3 mod 4: the 19 that faulted have
  fx below the target's width, the 3 that drew a first macrotile covering it] (ok) against
  H-FAULT23 (fault);
- slots: every target tile's header slot under H-EVEN (E950: 8 floor(fx / 2) slots a block row)
  against R7-BLK (16 floor(fx / 4)), parted on every planned row;
- flag: the one bit-7 header's slot and the image's wrong tiles under H-LASTBLOCK (E1007's
  H-FLAGSLOT) against H-HIGHSLOT (E1011's rival), parted on the two 768 x 640 rows only
  (fit/f2search.py: no word with fx covering the target parts them at 256 x 256 or 640 x 480).

A planned row that faults is cannot tell for the slot and flag models: t10's tri dumps nothing
after a failed render (deviation 1). The kit's own `score.py f2` (run by the driver) scores the
ends and the controls' images only; the slot and flag verdicts read the dumps:
`python3 score/score.py dumps f2 out/ATT/f2` (frozen with the rest; deviation 6).

## Stops

- An undeclared fault or hang (any control): the stage stops (4) and the session with it.
- Strict health after every fault (the kit): a health draw that fails at its first try stops the
  session (16), or aborts it (5) when the retry fails too.
- hook_fault (24) after every planned fault: any `SGX recovery failed` line in the row's kernel
  slice (no reboot, the user decides), a hang (none is planned), or a fault without its kernel
  `BIF fault S at A` line. In f1 that ends the session (`on_stop = "end"`), so f2 does not run.
- hook_check (24): an f1 row that read ok without its 32 pixel rows; an f2 row that read ok
  without `job: ok`, its target hash or its dump line.
- A control without its reading stops the session (25).

## The mock's worlds (mock/world.py, kit/session.py mock)

model (f1 H-TWP4096, f2 H-COVER + H-EVEN + H-LASTBLOCK: 0, 0), alt (f1-zero H-MOVE0, f2
H-HIGHSLOT: 0, 0), faultany (every planned row faults, each limit used up on its last row: 0, 0),
unplanned (f1-ref-a faults: 4), ctlnopix (f1 24, the session ends: 24), f1hang (24, ends),
recovfail (24, ends), nobifline (24, ends), ctl2fault (f2's control faults: 4), f2hang (f2 24),
nohash (f2 24), nodump (f2 24), wedge (the health fails after a -110: 16). The kit's library-mock
replay runs all 11 rows on t14's and t10's pinned sources (f1's 5 as "program not simulated").

## Replay vectors

f1: `refused` until the fold: if one form holds, f1's three images become a `tex` table for
sgx-sim's texture address (`closing_tables.py` format `sgx545-tables`), replayed by sgx-sim's
texture tests; the fold builds it from the kept files and predictions/f1/. f2: if H-EVEN holds,
the four rows' slots and wrong tiles become a table for sgx-pipe's `ta::macrotile_slots` (kind
`ta`); else `refused` (planned faults). The readers it needs (gen/q139*.py, score/lib_dump.py)
are pinned. Nothing else to pin.

## Layout

gen/make.py writes tables/, predictions/ and bins/ (gen/f1.py, gen/f2.py; gen/law.py the tile law,
gen/pins.py and gen/tex.py r10-tex's, gen/q139_fit.py, q139model.py, q139even.py r10-geo's byte
copies); score/score.py with score/lib_dump.py, pbdump_dump.py, region_tiles_dump.py (r10-geo's
byte copies); run/hooks.sh; mock/world.py; tests/ (test_gen.py, test_twin.py, test_score.py);
fit/ (the builder's searches and their outputs); lead/build_tool14.sh (t14's recipe);
PREFLIGHT.md; FOLD-NOTES.md. Publishable: everything (our own programs, tables, scorer, mock and
searches; no firmware-derived file). **Nothing is marked for data-private.** `debug/` is scratch.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Offline: `bash tests/run_all.sh` (the guard, the session's tests, the library mock, the mock of
  every world, the verify once frozen); `python3 gen/make.py --check` (the generator current).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`, its log kept
  OUTSIDE this directory (`... run . 2>&1 | tee ../logs/r14-flag-run.log`).
- Score again on a kept attempt: `python3 score/score.py STAGE out/ATT/STAGE`; f2's slots and flag:
  `python3 score/score.py dumps f2 out/ATT/f2`.

## Deviations from the plan (the lead may object before staging)

1. **F2's premise does not hold on t10**: the plan says a faulting Q139 row still yields its TA
   dump (from E944/E950), but E950's three residue dumps came from jobs that drew, and t10's `tri`
   breaks before `dump_render` after a failed render (sgxfive-test.c at a581c06; the function's
   own comment: recovery resets the TA data). So f2's four rows are words predicted to draw
   (H-COVER: fx covering the target), still `expectfault` under the user's OK; a row that faults
   reads only its end (H-FAULT23). The plan's "fx 2, 3, 6 and 7 mod 4" is read as fx 2 or 3 mod
   4 at four values (14, 15, 26, 27).
2. **The flag's rivals part only at 768 x 640**: no word with fx covering the target parts
   H-LASTBLOCK from H-HIGHSLOT at 256 x 256 or 640 x 480 (fit/f2search.py); the 256 x 256 rows
   (E950's named fx 14, 15) part H-EVEN from R7-BLK only.
3. **F2 has 6 jobs, not 5**: a 768 x 640 baseline (E959's) as a second control, for that size's
   header base.
4. **F1's rows are the plan's three with E1033's own two references**: f1-tw32 and f1-small are
   E1033's inputs again at 256 pages (`replicate`; the forms were fitted on their fault pages),
   f1-zero the held-out row. Q078 retires only if one frozen form gives all three images.
5. Kit: c58f9f9's (main dddadbd's kit, the commit that adds t14's source), as the prompt names.
6. **Kit need: REQUIRED per class.** The kit checks a stage's REQUIRED files on every kept row,
   so f2 cannot declare the dumps (a faulted row has none) and its kit scorer may not read them.
   The driver's `score.py f2` therefore prints the ends and the controls' images, and the frozen
   `score.py dumps f2 KEPT` the rest (the lead runs it after f2, or the fold does). A kit change
   (REQUIRED files of ok rows only) would fold the two; not needed for this run.
