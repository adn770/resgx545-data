# r16-usse

Round 16's session r16-usse (closing16/plan/rank-round16.md sections 2 and 3, decisions R16-1 (a)
and R16-5 (a) of closing16/DECISIONS-R16.md), built with the session kit (resgx545 HACKING.md,
"Session kit"), scaffolded by `tools/closing/new_session.py` from resgx545 b2b5288c82ed (kit/ is
that commit's blobs) and resgx545-data 62cb03b369ca. The first USSE table on the kit: client fills
as E597 and E599 ran them (`probe --temps 32 FILE`), predicted by sgx-sim's usse.rs. Generator:
gen/make.py with gen/progs.py (the programs and their predictions), gen/rule.py (the frozen
hypotheses as code), gen/sim.py and gen/pins.py (sgx-sim and usse-asm built from `git archive` of
the pinned commit into debug/target, every repository file read at the frozen commits). Records
E1061 (uadd and urpt, Q126), E1062 (utest, Q137).

## What runs

Three stages in this order, 30 jobs, laptop prefix `r16u` (files under `~/scratch/r16u/`), one
binary: `~/sgxfive-test-t10` (t10, sha256 9bedc2d6...), bound by source to resgx545 a581c06
`userspace/libsgxfive/tools/sgxfive-test.c` (sha256 23e1fa76..., `TOOLSRC.sha256`), recipe
`data:render/closing-r10-st1/lead/build_tool10.sh`. Every row names t10; the kit's library-mock
replay runs all 30 (probes of programs of ours: "program not simulated", since c12542e). Module
B60AB0B475DD1E8972419B5 (fork 2a650d74) loaded = installed; no debugfs knob is written. Safe class:
no planned fault, no expect-fault row, `#limit 0` on every stage; the programs store only to
scratch dwords 0 to 15 of the 16 default pages (no load, no other address) and write only
temporaries, i0, sa0 (E496 wrote sa0 and i0 in fills) and o0.

| stage | plan | question | jobs | what is frozen | record |
|---|---|---|---|---|---|
| uadd | uadd | Q126 | 7 | H-ZX against H-SX on #1, #127, c56, i0, sa0 | E1061 |
| utest | utest | Q137 | 20 | H-RULE against H-SETAND (a), H-AJOIN, H-ORFALSE, H-SETOR (o), H-CHAN0 (lanes) | E1062 |
| urpt | uadd's repeats | Q126 | 3 | H-ZX-ADV against H-SX, H-NOREP, H-NOADV on .xy, .xyzw | E1061 |

- **uadd** (`tables/uadd.txt`). Each program runs `iaddu32.testtaz.chan0 DST, p0, r1, SRC2` over
  eight pairs and stores each value to its own dword (dword k = pair k). r1 = 0x8000, 0x8001,
  0xabcd, 0xffff, 0x7fff (both extensions agree), 0xffff8000, 0x1234fedc, 0xffffffff. Controls that
  can fail: u-ctl-e521 (eight of E521's sixteen pairs, its kept values) and u-ctl-e498 (E498's four
  iaddu32 tests on (0, 0) and (0x8000, 0x8000), p0 into r10 as E498 did, its kept readbacks).
  Held out: source 2 #1 and #127 (u-imm1, u-imm127; the test group's immediates are 0 to 127),
  c56 (0xffffffff, the constant bank, u-c56), the destinations i0 and sa0 read back by `mov r3,
  i0` / `sa0` (u-i0, u-sa0; register r2 of 0x8000, 0x7fff0000, 1, 0xffffffff, 0x8001, 0x12345678,
  0x80000000, 0x10000).
- **utest** (`tables/utest.txt`). One form and one join a program. For each of six input pairs j:
  dword 2j holds the operation's value (written by the field-0 test `OP.testtat.chan0 r3, ...`),
  dword 2j + 1 holds 0x5A5A0000 with bit f set when the test word of field f set p0 (`p0 or r10,
  r10, r(12 + f)`, r12 + f = 1 << f), fields 0 to 15. Controls that can fail: E499's rawcond table
  (and r1, r2, the a join, fields 1 to 15, its six pairs) and E529's rawjoin-o table (the o join),
  their kept readbacks. Held out: shl, shr, asr with registers, or and rol with #7, iadd32 and
  iaddu32 sums, each with the a and the o join (14); then the lane operations iadd8 (bytes 0, 3,
  0xf1, 8: zero, positive, negative, positive) and iadd16 (halves 0 and -15; chan1 and chan3 have
  no lane) on one pair, a dword a chan field (chan0 to or02 at dwords 1 to 8), the nine fields the
  assembler names (0, 1, 2, 4, 5, 6, 8, 9, 0xa), the a join, and last the o join (the E530 family
  on lanes). A test word the assembler names is written as text, the others as `.long` (the text
  word with enc[43:36] replaced; OQ137 below).
- **urpt** (`tables/urpt.txt`), the session's last stage (`on_stop = "end"`). The write masks
  `.xy` and `.xyzw` on the test (`iaddu32.testtaz.chan0 r10.xy, p0, r1, r5`), sources r1 + k and
  r5 + k, r10 to r13 preset to markers before each instruction, uadd's eight pairs. Control that
  can fail: E521's pairs again (u-ctl-rpt, the same program as u-ctl-e521).

## Predictions and what each verdict does

Frozen before the run: `predictions/STAGE.tsv` (the dwords each model changes, `OFFSET=VALUE`;
`PREDICTIONS.sha256` at the freeze). How each was made, and checked before the freeze
(tests/test_sim.py):

- sgx-sim of the pinned commit replays every kept vector file the session leans on (E521's values,
  E498's tests, E499's rawcond and rawcond2, E529's rawjoin-o and -o2, E530's rawchan-1 to -7: 0
  mismatches, 0 unsupported), and gen/rule.py's H-RULE gives every kept raw test case of those
  tables (1152 of 1152).
- H-RULE's channel classes come from the sim's own single-condition text forms; the whole program
  with each raw field written as the field of its two parts runs on the sim to exactly H-RULE's
  bits and H-SIM's values on every a join row, both controls and or #7 with the o join. The sim
  refuses the o join on shl, shr, asr, rol, iadd32, iaddu32, iadd8 and iadd16 ("not run, E529")
  and the test's write mask: there the frozen prediction is the sim's rule carried over [infer],
  which is what those rows test.
- uadd: every row runs on the sim to H-ZX (and the controls to their kept values).

Expected, not frozen: every control passes; H-RULE on all 18 held-out utest rows; H-ZX on all five
held-out uadd rows; on urpt H-ZX-ADV is the weakest guess (the mask on a test was never run;
H-NOREP,
the mask ignored, is the live rival). Retire (R16-6 a, the lead confirms): **Q126** if H-ZX holds
on every uadd and urpt row with the controls passing (its test clause reworded as not observable
[infer], as Q276's predicate clause was; if urpt reads H-NOREP the repeat clause is answered "the
test group has no repeat: the mask is ignored"); **Q137** if H-RULE holds on every utest row with
both controls passing, the clause "whether our own backend may emit the combined words from the
assembler's text forms" being OQ137 (offline, below) plus the text words these rows run.

Offline parts done here: **OQ137** (tests/test_gen.py): usse-asm's words for `.testtoz`,
`.testnoz`, `.testnaz`, `.testpanz` and every other name, on every form and chan of the session,
equal the raw words with that field, join and chan, E529's and E530's words byte for byte (and
the session runs them as text). **OQ126** (tests/test_sim.py, gen/progs.py): the sim's predictions
per form; the assembler takes iaddu32 to r, o, i0, sa0 and g0 and immediates 0 to 127 in source 2;
it writes no `.repeat` on the test group, whose enc[47:44] is a write mask.

## Stops (kit/run_stage.sh, kit/session.py)

Any fault or hang stops the session (rc 4 / 6; none expected: E499, E529, E530 ran 1152 raw test
words with no fault, E521 and E498 their forms, E496 the i0 and sa0 destinations). A control
without its scratch dwords stops the session (rc 25). The second row of a stage without its o0
line or scratch dwords stops that stage (rc 24, run/hooks.sh); uadd and utest then go on to the
next stage, urpt (the last) ends the session. Less than 300 MiB free on ~ stops it (rc 22). Stop
budget: `#limit 0` on every stage, 0 faults and 0 hangs expected. The rows that run something no
job ran are placed last: the o join lane rows close utest, the test's write mask is urpt, the
session's last stage.

Expected time: client fills of under 10 ms (E597's 928 to 9712 us), plus the runner's reset,
snapshot and health (about 6 to 9 s a job): about 4 minutes of jobs, about 8 with staging and
preflight; stage alarms 15, 20 and 10 minutes.

## Commands

Every command is run through its interpreter, never by its mode bits:

- Python: the repo's own, `$HOME/src/resgx545/.venv/bin/python` (pytest), which the offline tests
  use unless `PY` names another. Cargo (offline) builds sgx-sim and usse-asm of the pinned commit
  into this directory's `debug/target` on first use (gen/pins.py).
- Offline: `bash tests/run_all.sh` (guard, own tests, mock of every world, verify).
- Generator: `python3 gen/make.py --check` (tables, predictions and programs current).
- Freeze: `python3 kit/session.py freeze .` once the tests pass, before the first job.
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .`
  (stop codes: kit/session.py).

Mock worlds (mock/world.py): model (every stage 0, the controls their kept tables, H-ZX, H-ZX-ADV,
H-RULE and H-SIM held), alt (the rivals H-SX, H-SETAND, H-AJOIN, H-CHAN0; every stage 0), ctlnoread
(u-ctl-e521 prints no dword: the premise stops the session, rc 25), uaddstop (two uadd rows print
no o0: uadd rc 24, the session goes on), unread (the same in utest: rc 24, urpt runs), rptstop
(both mask rows unread: urpt rc 24 ends the session, driver 24), fault (the first held-out uadd row
faults: rc 4), hang (the first held-out utest row does not return: rc 6), rpthang (the first mask
row does not return: rc 6 at the last stage).

## Deviations from the plan

1. **Jobs: 30, not 25.** utest has 20 rows, not 16: each 32-bit form runs both joins (one
   program a join: PROBE_MAX_WORDS is 256 words and a form's 16 fields over six pairs take 250),
   which the plan's "shifts (3), or/rol #7 (2)" left to one join; the plan's separate field-0
   program is folded into every program (field 0 is bit 0 of each packed dword, on every form and
   both joins). The lane rows test the nine fields the assembler names over chan0 to or02 on one
   pair (72 tests a program); the raw two-bit fields 3, 7, 0xb-0xf on lanes are not run.
2. **The repeats are a stage of their own, the session's last** (urpt, 3 jobs with E521's control
   again), not uadd's rows 8 and 9: the test group's enc[47:44] is a write mask that no job has run
   on a class 9 word and the sim refuses, so a fault there loses nothing else. The plan's ".rpt2
   and .rpt4" are `.xy` and `.xyzw`: the assembler writes no `.repeat` on the test group.
3. **No g destination** (the plan: "and g if the assembler accepts it"): it does (g0), but a
   global register written by a fill is not a register of the task; dropped from safe class.
4. **The readout packs the fields**: one bit a field (`p0 or r10, r10, rB`, a predicated bitwise
   op), where E499 and E529 read p0 one job a case through `p0 mov r10, #1`. The two controls
   replicate their tables through this readout, so a readout that does not work fails them.
5. **or #7 has no zero result** (or with 7 is never 0): its rows cover positive and negative only.
6. **Rivals added**: H-SETAND, H-AJOIN, H-ORFALSE, H-SETOR, H-CHAN0 (utest) and H-NOREP, H-NOADV
   (urpt), each told from the tested model on every row that carries it (tests/test_sim.py).

## Replay vectors (HACKING.md "Replay vectors")

| stage | vectors (fold) | replay |
|---|---|---|
| uadd | `vectors/closing/r16-usse/usse/uadd.vec.json` (format `sgx545-vectors`: each job's program words from bins/, the init of a probe fill, the kept scratch dwords) | `sgx-sim --vectors` (crates/sgx-sim/src/vectors.rs), as E597's `vectors-usse-fw37`; every row runs on the sim now |
| utest | `vectors/closing/r16-usse/usse/utest.vec.json` | the same, once the fold lifts the sim's "join o (not run, E529)" refusal for the forms that held; until then those rows are counted unsupported, never passes |
| urpt | `vectors/closing/r16-usse/usse/urpt.vec.json` | the same, once the fold models (or refuses with E1061) the test's write mask |

closing_tables.py has no kit kind for probe scratch dwords: these are sgx545-vectors (the USSE
corpus format E597 and E599 used), built from the kept files and bins/ alone (the fill
0xd0000000 | i and the base 0x3e003000 are the probe's, written in gen/progs.py). If the fold needs
a converter for kit probe outputs, it reports it to the tooling agent (shared tools are not the
fold's to change).

## Data

No file here derives from the closed firmware: everything is publishable (resgx545-data
`usse/closing-r16-usse` or the area the fold names). bins/ are our own programs (assembled by the
pinned usse-asm from the .s beside them). `debug/` (the sim and assembler build, the mocks) is not
published. **Nothing is marked for data-private.**
