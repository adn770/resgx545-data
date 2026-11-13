# r13-dpm: round 13's DPM session (Q036, 0x0748 bit 2)

Round 13, session r13-dpm of `closing13/plan/rank-round13.md` sections 2 and 3, stage pr2 (decision
R13-1 (a), safe class only: no held reset, no planned fault, no `expectfault` row, `#limit 0`).
Built offline 2026-11-13 on the session kit, scaffolded by `tools/closing/new_session.py` from
resgx545 main 05b7039 and resgx545-data 75d01ee20. Nothing here touched the laptop, cachix or a git
repository. Record number reserved for the fold: **E1032**. Built from r10-dpm (`closing10/r10-dpm`)
and r8-ldpm (copy patterns, not files).

## The question

Q036: what 0x0748 bit 2 marks. E1019 ranked, on 558 held-out jobs, R-PR (clears of bit 2 in
proportion to the partial-render count) above R-LEN (per line), R-0x100 and a constant (log-loss),
a ranking and not a pass rule. This stage reads bit 2 at controlled partial-render counts of one
scene. The same timelines read 0x0700, 0x070c, 0x0710, 0x0720 to 0x0728 and 0x072c's high half (the
global page count, CR_DPM_3D_PAGE_COUNTS' high half) as readings. Narrow: CR_DMS_CTRL, the signature
registers and the builder fault stay open; 0x071c is not in the register set (E1019's caveat stays).

## What runs

Laptop prefix `~/scratch/r13d/`, module B60AB0B475DD1E8972419B5 (fork 2a650d74, loaded). Tool t10
`~/sgxfive-test-t10` (9bedc2d6..., source resgx545 a581c06 `userspace/libsgxfive/tools/
sgxfive-test.c`, sha256 23e1fa76..., recipe `data:render/closing-r10-st1/lead/build_tool10.sh`,
replayed row by row on its library mock) under `~/regtimeline` (079f6359..., `wraps = true`) with
R5-dpm's 16 registers, as r10-dpm ran t4. Both are on the laptop; nothing is built or shipped. The
program is `bins/p1139-green.bin` (pinned blob of r9-ldpm). One stage, **pr2, 8 jobs** (about 5
minutes with the preflight, 7 to 10 s a job under regtimeline):

| rows | scene | `dbg:render_pb_pages` (thr0) | partial renders |
|---|---|---|---|
| pr2-c0-1, pr2-c0-2 (controls) | 3072x2048, 1500 vertices | 0x422 (0x400) | 0 |
| pr2-c1-1, pr2-c1-2 | same | 0x2b6 (0x294) | 1 |
| pr2-c2-1, pr2-c2-2 | same | 0x1c2 (0x1a0) | 2 |
| pr2-c4-1, pr2-c4-2 | same | 0xe2 (0xc0) | 4 |

Run order c0, c1, c2, c4, then c1, c0, c4, c2 (no row follows its own count). The counts are
r8-ldpm's kept readings of this scene (f9 and m6: 0x400 0, 0x292 to 0x296 1, 0x1a0 2, 0xc0 4), so a
count is a repeat; tests/test_plan.py replays them on the published jobs. Every row is
`expect:rc3-overflow` (a PR 0 job completes, rc 0, also an expected end).

Stops: a PR 0 row that reads a partial render (`ctl:nparts=0`, hook_check) stops the stage (rc 24);
an unread control (no knob, no 0x0748 column: a cut capture) stops the session (rc 25); any fault,
hang, -110, failed health or an rc 3 without "scene overflowed the parameter buffer" stops it
(rc 4). A PR 0 row with a bit 2 clear does not stop anything: it is the finding (below).
`min_free_mb` 300, `job_timeout` 120 s.

## Frozen before the run (`predictions/pr2.tsv`, gen/plan.py, score/score.py)

CLR = lines of a job with 0x0748 bit 2 clear (E1019's unit); PR = partial renders (stretches of
0x0658 bit 0).

| model | says | prediction |
|---|---|---|
| H-PR-STRICT | the plan's R-PR: a clear line at least once per partial render, none at 0 | CLR >= PR at the 6 rows with PR > 0; CLR 0 at both PR 0 rows |
| H-R-PR | E1019's R-PR | P(job has a clear) = 1 - exp(-0.1708 PR) |
| H-R-LEN | E1019's R-LEN | 1 - (1 - 0.00108)^N, N the job's lines |
| H-CONST | the constant | 0.439 |
| H-COUNT (tally) | the count is controlled | nparts = PR (0, 1, 2, 4) |
| H0 (tally) | E1019's STATUS2 | 0x0710 bits 31:16 = 0 at every line |

Constants are E1019's fit on r1 to r3 (`closing12/plan/c1-q036/q036_score.out`); every row is held
out of that fit. Controls that can fail: the two PR 0 rows (nparts 0 and CLR 0; a clear at PR 0
refutes R-PR's "none at 0" and gates every verdict), and the count itself (H-COUNT). Rule
(score.py): with both controls passed, the DECISION line prints the strict form's state (held only
if 6 of 6) and the ranking by E1019's per-job log-loss over the 8 rows (R-PR ranked first only if it
has the lowest and each rival is at least 1.0 nat higher; else NO RANKING).

**Builder's expectation (not a verdict)** [infer]: the strict form fails. The kept 3072x2048 jobs
(r8-ldpm: clear lines in 2 of 5 jobs at 1 PR, 0 of 1 at 2, 1 of 1 at 3, 1 of 1 at 4, 1 at 6,
0 at 7) clear about 0.2 to 0.3 per
partial render, as E1019's fit says, and a pulse can fall between ~8 us samples. A NO RANKING
decision with a small total of clear lines (about 2 to 4 over 14 partial renders) is the likely
result; the stage narrows Q036 only if the rows part the rivals. Power is low by design (8 jobs,
the plan's size); the lead may add replicates of PR 4 in a later round.
Post hoc [infer]: the builder read the kept 3072x2048 jobs' clear lines (scan of r8-ldpm's f9 and m6
timelines) before freezing, to check which count rows are reachable; the rows are new runs, but not
blind to those counts.

## Layout

- gen/plan.py (table, predictions, `--check`); score/score.py (scorekit and kitscore; `ranking`
  is the frozen rule), score/read.py (the reader; adds `clr`, `pulses`, `hi10`).
- run/hooks.sh: `rd_words` (the reading in awk; tests/test_read.py holds the twin), `hook_reading`,
  `hook_check` (a `ctl:` word off stops the stage), `hook_fault` (none).
- mock/world.py: seven worlds (model, clear0, perpr, ctloff, noread, fault, rc3other).
- tests/: test_plan.py (generator, rows, safe class, session.toml, the kept counts, the frozen
  rivals, the strict fake takes every row), test_read.py (awk twin on kept jobs), test_score.py
  (holds on r8-ldpm's kept 3072x2048 jobs as the rows, fails on a moved knob, a control with a clear
  line, and the ranking rule on synthetic reads).

## Commands

- Offline: `bash tests/run_all.sh` (guard, own tests, library mock of every row, mock of every
  world, verify).
- Freeze: `python3 kit/session.py freeze .` (never rewritten).
- Laptop: `python3 kit/session.py stage .`, then `python3 kit/session.py run .` (stop codes:
  kit/session.py), with `SGX_TARGET_HOST` set; afterwards move `~/scratch/r13d` to
  `~/scratch/archive/`.

## Replay vectors

pr2: the rows' counts, clear lines and 0x0700 to 0x0728 readings become the `sgx545-tables` table
`dpm/r13-dpm-pr2` (`tools/usse-asm/closing_tables.py`) when the fold lands it. Replay: `refused`
(register timelines: a clear-line count is a sampled reading, not a step rule). The fold reads only
the kept `out/` files and score/score.py; the pinned r8-ldpm jobs are the scorer's replays.

## Publication

No file reads a firmware image, listing or closed binary: nothing is marked for data-private.
`debug/` is scratch (delete any `.pytest_cache` and `__pycache__` before the fold publishes).
