# r15-dpm: round 15's DPM session (Q036, pr4: 0x0748 sampled alone, period gate 2000 ns)

Round 15, session r15-dpm of `closing15/plan/rank-round15.md` (R15-3 a, DECISIONS-R15.md; safe
class only: no held reset, no planned fault, no `expectfault` row, `#limit 0`). Built offline
2026-11-14 on the session kit, scaffolded from resgx545 main 158bdc5 and resgx545-data cddc7b60b.
Nothing here touched the laptop, cachix or a git repository. Record number reserved for the
fold: **E1057**. Copied from `closing14/r14-dpm` (frozen; its fold E1044).

## The question

Q036: what 0x0748 bit 2 marks. r14-dpm's pr3 sampled the one register 0x0748 and read a period of
1682 ns (E1044); its 1000 ns `short` gate was a premise error (the floor is about 1.3 us plus 0.4
us a register [infer]), so the rows stopped at the first control. pr4 is pr3 re-run with the gate
at **2000 ns**: the only change. Rows, run order, knob values, frozen predictions and the ranking
rule are r14-dpm's (tests/test_plan.py diffs the tables and predictions against r14-dpm's after
the stage rename). Narrow: CR_DMS_CTRL, the signature registers and the builder fault stay open.

## What runs

Laptop prefix `~/scratch/r15d/`, module B60AB0B475DD1E8972419B5. Tool t10 `~/sgxfive-test-t10`
(9bedc2d6..., source a581c06, recipe `data:render/closing-r10-st1/lead/build_tool10.sh`, every row
replayed on its library mock) under `~/regtimeline` (079f6359..., `wraps = true`) over 0x0748.
Program `bins/p1139-green.bin`. One stage, **pr4, 10 jobs** (about 40 s a job with the scene, about
8 minutes with the preflight):

| rows | scene | `dbg:render_pb_pages` | partial renders |
|---|---|---|---|
| pr4-c0-1, pr4-c0-2 (controls) | 3072x2048, 1500 vertices | 0x422 | 0 |
| pr4-c1-1, pr4-c1-2 | same | 0x2b6 | 1 |
| pr4-c4-1 to pr4-c4-3 | same | 0xe2 | 4 |
| pr4-c7-1 to pr4-c7-3 | same | 0x82 | 7 |

Run order 0, 1, 4, 7, 1, 0, 7, 4, 7, 4. Every row is `expect:rc3-overflow`.

Stops (budget: the stage ends at the first): a PR 0 row whose period reads over 2000 ns stops the
stage (rc 24; R-PULSE untestable); an unread control stops the session (rc 25); any fault, hang,
-110, failed health or an rc 3 without the overflow line stops it (rc 4). A PR 0 row with a bit 2
clear is the finding, not a stop.

## Frozen predictions (`predictions/pr4.tsv`, as pr3)

R-PULSE strict (PULSES >= PR at all 8 PR > 0 rows), R-RARE (total pulses 1..8), R-CONST; ranking
by log-loss, R-RARE first needs 1.0 nat over each rival. Builder's expectation [infer]: R-PULSE
fails again, a few short clears, R-RARE first or NO RANKING; a pulse shorter than one 1.7 us sample
is invisible.

## Layout and commands

gen/plan.py, score/score.py, score/read.py, run/hooks.sh, mock/world.py (worlds: model, clear0,
perpr, slow, noread, fault, rc3other; model's period is 1682 ns), tests/. Offline `bash
tests/run_all.sh`; freeze `python3 kit/session.py freeze .`; laptop `python3 kit/session.py stage .`
then `python3 kit/session.py run .` with `SGX_TARGET_HOST` set; afterwards move `~/scratch/r15d`
to `~/scratch/archive/`.

## Replay vectors

pr4: table `dpm/r15-dpm-pr4` (`sgx545-tables`, `tools/usse-asm/closing_tables.py`) when the fold
lands it. Replay: `refused` (register timelines: a clear-event count is a sampled reading, not a
step rule). The fold reads only the kept `out/` files and score/score.py.

## Publication

No file reads a firmware image, listing or closed binary: nothing is marked for data-private.
Delete `.pytest_cache` and `__pycache__` before the fold publishes.
