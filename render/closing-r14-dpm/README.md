# r14-dpm: round 14's DPM session (Q036, 0x0748 sampled alone)

Round 14, session r14-dpm of `closing14/plan/rank-round14.md` (row 9, decision R14-1 (a), safe class
only: no held reset, no planned fault, no `expectfault` row, `#limit 0`). Built offline 2026-11-14
on
the session kit, scaffolded by `tools/closing/new_session.py` from resgx545 main dddadbd and
resgx545-data 3309b5fd9. Nothing here touched the laptop, cachix or a git repository. Record number
reserved for the fold: **E1044**. Built from r13-dpm (`closing13/r13-dpm`, E1032; copy patterns).

## The question

Q036: what 0x0748 bit 2 marks. E1032 (r13-dpm) sampled 16 registers (a sample every 7.5 us) at 0, 1,
2 and 4 partial renders and saw one clear line in 14 partial renders (0.07 per partial render,
E1019's fit 0.17): the plan's strict form (a clear per partial render) failed, and the clear it saw
was one sample wide (8.4 us). pr3 samples **0x0748 alone**, to shorten the period. The [check] of
the plan, resolved on every kept regtimeline job (end / samples): about 0.46 us a register (16
registers 7.5 us, 14 7.5, 8 4.7, 5 4.6, 3 1.4), so one register samples about every 0.46 us, 16
times shorter [infer]. Narrow: CR_DMS_CTRL, the signature registers and the builder fault stay open.

## What runs

Laptop prefix `~/scratch/r14d/`, module B60AB0B475DD1E8972419B5 (fork 2a650d74, loaded). Tool t10
`~/sgxfive-test-t10` (9bedc2d6..., source resgx545 a581c06 `userspace/libsgxfive/tools/
sgxfive-test.c`, sha256 23e1fa76..., recipe `data:render/closing-r10-st1/lead/build_tool10.sh`,
replayed row by row on its library mock) under `~/regtimeline` (079f6359..., `wraps = true`) over
the one register 0x0748. Both are on the laptop; nothing is built or shipped. The program is
`bins/p1139-green.bin` (pinned blob of r9-ldpm). One stage, **pr3, 10 jobs** (about 7 minutes with
the preflight, 7 to 10 s a job):

| rows | scene | `dbg:render_pb_pages` (thr0) | partial renders |
|---|---|---|---|
| pr3-c0-1, pr3-c0-2 (controls) | 3072x2048, 1500 vertices | 0x422 (0x400) | 0 |
| pr3-c1-1, pr3-c1-2 | same | 0x2b6 (0x294) | 1 |
| pr3-c4-1 to pr3-c4-3 | same | 0xe2 (0xc0) | 4 |
| pr3-c7-1 to pr3-c7-3 | same | 0x82 (0x60) | 7 |

Run order 0, 1, 4, 7, 1, 0, 7, 4, 7, 4 (no row follows its own count). The counts are r8-ldpm's kept
readings of this scene (0x400 0, 0x294 1, 0xc0 4, 0x60 7); tests/test_plan.py replays them on the
published jobs. **Deviation from the plan: PR 7 replaces PR 8** (no kept reading of 8; with one
register the count cannot be read back, so a row's count is its label, and every label is a repeat
of a kept reading). The knob proof is the job's rc: 0 at PR 0 (the kit's `expect:rc3-overflow` also
accepts it), 3 with the overflow line otherwise. Every row is `expect:rc3-overflow`.

Stops: a PR 0 row whose period reads over 1000 ns (`ctl:short=1` off, hook_check) stops the stage
(rc 24: R-PULSE is not tested); an unread control (no timeline block, no 0x0748 column: a cut
capture) stops the session (rc 25); any fault, hang, -110, failed health or an rc 3 without
"scene overflowed the parameter buffer" stops it (rc 4). A PR 0 row with a bit 2 clear does not stop
anything: it is the finding. `min_free_mb` 300, `job_timeout` 120 s.

## Frozen before the run (`predictions/pr3.tsv`, gen/plan.py, score/score.py)

CLR = lines from the command's start on with 0x0748 bit 2 clear; PULSES = their runs (a clear
event);
period = the capture's length over its samples.

| model | says | prediction |
|---|---|---|
| R-PULSE | the plan's: a clear event per partial render once the period is short | PULSES >= PR at all 8 rows with PR > 0 (strict); CLR 0 at PR 0 |
| R-RARE | a clear is rare, Poisson whatever the period | P(job has a clear) = 1 - exp(-0.109 PR) (0.109 = geometric mean of E1032's 0.07 and E1019's 0.17); total PULSES in 1..8 (central 95% of Poisson(0.109 x 35 = 3.8)) |
| R-CONST | a constant | 0.439 |

Controls that can fail: the two PR 0 rows: CLR 0 (a clear at PR 0 refutes "none at 0" and gates
every
verdict) and `short` 1 (a period of at most 1000 ns; else R-PULSE is not tested). Rule (score.py):
with both controls passed the DECISION line prints the strict form's state (held only if 8 of 8) and
the ranking by per-job log-loss over the 10 rows (R-PULSE's p is 0.99 at PR > 0, 0.01 at PR 0;
R-RARE
RANKED FIRST only if lowest with each rival at least 1.0 nat higher; else NO RANKING).

**Builder's expectation (not a verdict)** [infer]: the strict form fails again. E1032's one clear
was
exactly one 16-register sample wide, so a clear event is short, and at 0.46 us it should still be
rare: about 4 clear events in 35 partial renders (R-RARE's mean 3.8), with none the ranking puts
R-RARE first by absence, as in E1032. If the period is not short the stage stops at the first
control. A clear shorter than one 0.46 us sample is invisible at any period.

Post hoc [infer]: the builder read the kept 3072x2048 jobs' clear runs (r8-ldpm, r13-dpm) and the
kept periods before freezing; the rows are new runs, not blind to those counts.

## Layout

- gen/plan.py (table, predictions, `--check`); score/score.py (scorekit and kitscore; `ranking` is
  the frozen rule), score/read.py (the reader: `clr`, `pulses`, `widths`, `period`, `short`).
- run/hooks.sh: `rd_words` (the reading in awk; tests/test_read.py holds the twin), `hook_reading`,
  `hook_check` (a `ctl:` word off stops the stage), `hook_fault` (none).
- mock/world.py: seven worlds (model, clear0, perpr, slow, noread, fault, rc3other); the world
  answers regtimeline itself, with a header whose samples and end set the period.
- tests/: test_plan.py (generator, rows, safe class, session.toml, the kept counts, the frozen
  rivals), test_read.py (awk twin on kept jobs and the mock's, the period), test_score.py (kept
  16-register jobs fail the short control; made fast they pass and R-PULSE fails; synthetic jobs
  hold
  the strict form; the ranking rule on synthetic reads).

## Commands

- Offline: `bash tests/run_all.sh` (guard, own tests, library mock of every row, mock of every
  world, verify).
- Freeze: `python3 kit/session.py freeze .` (never rewritten).
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .` (stop codes:
  kit/session.py), with `SGX_TARGET_HOST` set; afterwards move `~/scratch/r14d` to
  `~/scratch/archive/`.

## Replay vectors

pr3: the rows' clear runs, widths and period become the `sgx545-tables` table `dpm/r14-dpm-pr3`
(`tools/usse-asm/closing_tables.py`) when the fold lands it. Replay: `refused` (register timelines:
a clear-event count is a sampled reading, not a step rule). The fold reads only the kept `out/`
files and score/score.py; the pinned r8-ldpm and r13-dpm jobs are the scorer's replays.

## Publication

No file reads a firmware image, listing or closed binary: nothing is marked for data-private.
`debug/` is scratch (delete any `.pytest_cache` and `__pycache__` before the fold publishes).
