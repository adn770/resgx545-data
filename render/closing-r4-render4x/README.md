# R4-G: r4-render4x (4x render, parameter buffer, health replay): prepared, NOT run

Built 2026-11-11, offline. Nothing here touched the laptop, cachix or a git repository.
Read `PREFLIGHT.md` before running. Plan:
`/Users/jtorra/src/scratch/resgx545/closing4/render4x/exp-render4x-r4.md` (section 3),
decisions as recommended (scope a, four H cells last, o8 last in O, Q292 outcome as the plan says,
Q086's skipped families left out) plus the Q113 held-out cube row of decision R4-3 as its own
small stage after S0.

## What runs, in order

| stage | rows | what | predicted | stop limit |
|---|---|---|---|---|
| s0 | 3 | controls: 1x 1024x768, 4x 288x144, 4x 1024x768 | all pass | 1 |
| c | 3 | Q113: E726's cu-xn again, two held-out off-axis cube programs | rule holds | 1 |
| p | 6 | the 4x page need at 1280x1024 ... 3072x1280 (up to 961 pages) | all complete | 2 |
| o | 8 | overflow at 4x: o1-o3 controls, o4 o5 o6 o7 fault, o8 1x 4096x4096 | see below | 5 |
| t | 7 | Q293: four-array TE 0x40/0x80, a line and a point object, 3 controls | zero dword | 1 |
| h | 4 | health triangles after a TA write fault (four cells, held, LAST) | replay | 5 |

31 table rows: 25 plain tool jobs (s0 3, c 3, p 6, o 6, t 7) and 6 held ones (o5, o6, the four h
cells). h adds follow-up steps: a context step (h3) or a fill step (h4), then health triangles one
by one until one draws, four at most a cell (about 11 runs if the replays are as in K2). So about
42 tool runs, plus a health fill and triangle at each stage's begin and end. Fault-class events:
at most 4 in o (3D side, o4 o5 o6 o7) and 4 in h (TA write faults), with up to 8 health faults in h.
The plan's count was about 39 (S0 3, P 6, O 8, T 6, H 16); the Q113 row adds 3, t4b 1, and t5 is
dropped (below).

Order of the session: `stages.txt` = s0, c, p, o, t, h. o8 is the last row of o, stage h is last.

### Stage s0, the controls (3 jobs, safe)

| row | frozen from |
|---|---|
| s0-1x-1024x768 | E827 ctl-u-1024-n1, E828 j5: hash 0xc9e301d225fe2325, 0 wrong |
| s0-4x-288x144 | E828 j1r: hash 0x4a61860dcb4ab325, TA data 0x8000, 12 PB pages |
| s0-4x-1024x768 | E824 h8: hash 0xde0b9233c9822325, TA data 0x1e000, 193 PB pages |

A miss closes the gate of every later stage (the session is void: the lead decides). The 4x rows
also read register 0x0724 (K2's c1 held reading 0x000b000b = U4 - 1 in both halves, applied here
by inference): reported, and gating P's register line only if both 4x controls reproduce it.

### Stage c, Q113 (3 jobs, safe, `probe` fills of 64 x 32)

`cu-xn` is E726's own program (its pixels must equal E726's byte for byte: the control that can
fail). `r4g-cube-a` and `r4g-cube-b` are new programs built here with p1141's own generator code
(rebuilt E726's six axis programs byte for byte first): smp3d on TEXTYPE 2 at off-axis
directions, one coordinate constant and two ramping, the dominant axis changing inside the image,
no pixel within 0.0078 of a tie. Frozen: the face of every pixel by the dominant-axis rule
(+x, -x, +y, -y, +z, -z, a face is 256 dwords) [infer, post hoc from E726; it fits E726's 8 jobs
2048 of 2048 here]: a-faces 0/643/0/882/235/288, b-faces 903/0/235/261/0/649, together all six.
Held on 2 of 2 and the control passing: Q113 may be retired as answered (R4-3); its edges and
(s, t) stay Q284's. Deviation from "a 2-job row": the control is the third job.

### Stage p, H-PB (6 jobs, predicted safe)

U4 = 1 + ceil(2 * tiles16 / 32) scene pages, the rank's ceil(tiles32 / 8) + 4 counting the non-zero
pages of a dump (page 0 and three fixed pages). Fitted on E824's ten dumps (10 of 10, with the
TA-data layout formula); the six sizes are held out:

| size | U4 | spare of 1024 | TA data |
|---|---|---|---|
| 1280 x 1024 | 321 | 703 | 0x34000 |
| 2048 x 1536 | 769 | 255 | 0x6d000 |
| 2048 x 1920 | 961 | 63 | 0x8b000 |
| 4096 x 960 | 961 | 63 | 0x8b000 |
| 960 x 4096 | 961 | 63 | 0xbb000 |
| 3072 x 1280 | 961 | 63 | 0x84000 |

Held: every row completes with 0 wrong, non-zero scene pages = U4, TA data as the formula.
Refutes H-PB: any fault, an overflow, a different count. 4096 x 960 and 960 x 4096 are the cells a
width or height limit would fail while the page need passes.

### Stage o, H-SPM4 and Q292 (8 jobs; o6 only if o5 faults)

| row | size, mode | P | need | predicted |
|---|---|---|---|---|
| o1 | 1024x768 1x | 0x83 | 97 | completes (control) |
| o2 | 1024x768 1x | 0x82 | 97 | -ENOSPC, no fault (control) |
| o3 | 1024x768 4x | 0xe3 | 193 | completes (control) |
| o4 | 1024x768 4x | 0xe2 | 193 | fault: INT_STAT bits 15:0 0x0100, page 0x10000, SB 1 |
| o5 | 288x144 4x held | 0x23 | 12 | as o4 (dumps read in the hold) |
| o6 | o5 plus tadata_fill page 7 | 0x23 | 12 | exploratory: the fault page leaves or stays |
| o7 | 4096x1152 4x | 0x422 | 1153 | as o4 |
| o8 | 4096x4096 1x | 0x422 | 2049 | -ENOSPC, no fault (j4's control) |

`strict`: after a 3D-side fault the first health fill and triangle must draw (no reset of ours
before them), else the stage stops (rc 16). The verdict (`score_r.py verdict`) prints Q292's
narrowed form by case: o4, o5, o7 fault and o2, o8 do not (recorded as "an overflowing scene
faults at 4x; the fork has no partial renders", no kernel work now: decision 7a); -ENOSPC at 4x
too (the fault is about the size); or mixed.

### Stage t, Q293 (7 jobs, safe: rg-pb's class)

t1, t2: TE 0x40 and 0x80 with `--aa4`, mode 2 (H-SAME: dword 11 zero, format word at 12, empty
image). t3, t4: a line and a point object from the 11.31 sessions with `--cmd 1=0x40000000`
(programs rebuilt from `probes/ta/p1131-progs.toml`, equal to the ones that ran), on `rgn:1`
(the module refuses TE bits 31:30 without a forced count or `--aa4`). H-PAD: one dword inserted
right before the format word and it is zero; H-FIELD: non-zero. Controls: t6 (E827's
pb-e40-m2-64a: its words and hash), t3b and t4b (the same probes without the poke, in-session
baselines for the insertion). Deviation: the plan's t5 (two objects in one render) is dropped, the
kept E825/E829 pb-n40 dumps already show one inserted dword per object (dwords 11 and 38); t4b is
added. So 7 jobs where the plan had 6.

### Stage h, Q140 (4 held cells, last)

Each cell: `render_rgn_arrays` 1, no flag, `hold_recovery` Y, the c1-shaped job (the 4x words on a
one-array context), the fault read, a debugfs `reset`, then the cell's follow-up, then health
triangles one by one until one draws (four at most), kept with kernel-log slice and registers
(clock status) after every step.

| cell | job | follow-up | H-REPLAY predicts |
|---|---|---|---|
| h1 | 288x144 (0x20006061) | health | every failing one reads 0x20006061 |
| h2 | 640x480 (page 0x2000a) | health | every failing one names page 0x2000a |
| h3 | 288x144 | a 64x64 triangle on a 1024x768 context | no fault (page mapped) |
| h4 | 288x144 | a fill, then health | fill passes, health still faults |

h2 is the control that can fail (a health fault at 0x20006, the health context's own end,
refutes the replay). The count of replays is reported, not predicted. Any -110 is read against
the plan's 1.3 shape (requestor bit 2, a PARAMETERS page).

## Stops

- s0, c, t: the first fault, hang or unexplained failure ends the stage (rc 4).
- p: two fault-class events end it (rc 15). o: five (four are predicted). h: five.
- A health failure after a strict 3D-side fault: rc 16. A cell's fourth health triangle failing:
  rc 17, every knob restored, no further reset (the lead decides). A fatal kernel message: rc 3,
  a job that does not return: rc 6 (nothing but the knob restore).
- A knob that does not read back (render_rgn_arrays, render_pb_pages) or does not go back: rc 19;
  hold_recovery not Y: rc 9; the driver stops with rc 42 if a knob is not at its default after a
  stage. After any stop: no reboot, no module unload, no register write. The lead decides.

## Layout and commands

`gen/rgen.py` writes `tables/`, `predictions/`, `TABLES.md`, `stages.txt`, `bins/` (the staged
programs), `gen/data/` (the model fit, the source list). `gen/pbmodel.py` is the page model,
`gen/cubegen.py` the cube builder and rule, `gen/rlib.py` readers. `score/score_r.py` is the
scorer (scorekit byte for byte main's). `run/`: `run_stage.sh` and `lib_k.sh` run on the laptop;
`k.sh` the driver; `stage_k.sh` stages; `freeze_k.sh`, `guard_k.sh` the freeze and the session's
own static guard; `lib_check.sh`. `tests/`: `run_all.sh` (all offline tests, exits 0).

Laptop directories: `~/r4g-run`, `~/r4g-stage` (the five programs), `~/r4g-out` (no other
session's). Prefix `~/r4g-`.

```
export SGX_TARGET_HOST=jtorra@192.168.12.234
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
export PYTHONDONTWRITEBYTECODE=1
export PY=/Users/jtorra/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python
cd /Users/jtorra/src/scratch/resgx545/closing4/r4-render4x
bash tests/run_all.sh                 # offline: ALL TESTS: PASS
run/guard_k.sh && run/freeze_k.sh verify
SGX_DRY_RUN=1 run/stage_k.sh && SGX_DRY_RUN=1 run/k.sh
run/stage_k.sh                        # copies, compares, checks the tool hash
run/k.sh                              # the session, stage by stage (gates, scores, health)
$PY score/score_r.py verdict out/ATT  # the SUMMARY lines
```

`run/k.sh --only STAGE` (a new attempt directory) reruns one stage, `run/k.sh --from STAGE`
continues after a stop.
