# R5-events: laptop session r5-events of round 5 (stages h1, h2, h3)

Prepared 2026-11-12, NOT run. Nothing here touched the laptop, cachix or a git repo; nothing is
committed; the clean-room guard was not run; no closed source, no firmware image and no closed
binary was read (`closing5/r6/ukernel.hex.dis` was not
opened: R-6 is used only through what `reading-r6.md` and `s0/RESULT.md` say). Read
`PREFLIGHT.md` first.

Plan: `closing5/events/exp-events-r5.md` section 5, every decision (a) (`DECISIONS-R5.md` R5-3,
R5-4, R5-7). It runs FIRST of round 5, as a health check of the laptop. Base: round 4's
`closing4/r4-events` (published `edm/closing-r4-events`): the blob `ring_skip3p` byte for byte
(sha256 `3b35d3af...`), the runner, the scorer's readers, the mock, the driver.

## What runs (one session, laptop prefix `~/r5e-`)

| stage | `timer_clock` | jobs | what | predicted stops |
|---|---|---|---|---|
| h1 | 0 (400000) | B0, B1P x3 | R4's e3p job again: the lockup marks, the count 20, bit 18 a level, the host's clears after the stop | 3 |
| h2 | 800000, then 1600000 | per clock B0, B1P x2 (6) | the dose: 20 ticks (H-TICKS) or about 19 ms (H-TIME); no host write before the watch ends | 4 |
| h3 | 1600000 | B0, B1E x3 | the clears of bit 15 then 18 at the slot 3 entry (EDM running), one `miscinfo` after them, then a 150 ms watch | 3 |

**14 jobs, 10 predicted stops** (budgets h1 3, h2 4, h3 3: one per B1P / B1E). Order h1, h2, h3,
each gated on the previous stage's kept `stage.json`. If only one stage can run: h1.

Every job: `timer_clock` written and read back BEFORE its reset (the kernel copies it into HostCtl
dword 6 at the boot, E084), a debugfs reset and the arm, a status dump at the arm (dword 6, dwords
3 and 8), `hold_recovery` Y in B1P / B1E (N in B0), the page's skip flag, one `fill` through
`~/sgxfive-test-s1b`, the bounded wait for the slot 3 entry, (h3: the clears and the `miscinfo`),
the watch (50, 100, 150 ms by clock), the tick checked (a stop is signed at once: signature twice,
the landed dumps `stop-NAME-{status,regs}.txt` and `-own_res.json`), (h1: the clears), P3 after a
stop, a status dump after the watch, `hold_recovery` N read back, the tool collected (6 s), then
the reset, the gate and the health. Every stage ends with `clock_back`: `timer_clock` 0 written and
read back, a reset and an arm, the ring open 20 ms, its tick gap 25000 +-10 and the rate in 900 to
1100 Hz, then the reset, the gate and the health (exit 9 if the clock did not come back). The
driver's health line checks `timer_clock=0x00000000` after every stage and the session's last
lines print the knob.

Time: about 7 minutes of jobs (a stop job 30 to 35 s with its recovery, a B0 about 6 s), three
stage ends (clock back, copy, health, score: about 45 s each) and the staging: **about 15 minutes
wall**, 25 with trouble. Stage alarms (`stages.txt`): 600, 900, 700 s.

## Stops (R5-4 (a))

A B1P / B1E stop is the predicted outcome: each is signed, recovered (reset, gate, health) and
the stage goes on, when it is **explained**: its status dump carries the lockup marks (HostCtl
dword 3 above the arm's, dword 8 bit 0) and the slot 0 ring holds the fill's kick entry (the count
is readable). The stage ends (exit 8, and the driver ends the session) on: a B0 that stops, an
unexplained stop, a stop past the budget. Exit 5 (reset or gate not exact): the lead asks the user
before anything else. Exit 3 (watchdog) or 6 (no return): nothing else touches the laptop.

## What is frozen, and what each stage predicts

`PREDICTIONS.sha256` (`predictions/*.tsv`, `case quantity value model set`; sets control and
heldout: every B1P / B1E row of round 5 is held out), `FROZEN.sha256` (every generator, scorer,
runner, script, table, blob, source, prediction, test, fixture, the landed files of the repo by
absolute path, and the cited inputs: the plan, `DECISIONS-R5.md`, R-6 and S0), `FROZEN.commits`
and `FROZEN.pin` (the repo pins: resgx545 main at the freeze), `LAPTOP.sha256` (the files as laid
out under `~/r5e-run`), `TOOL.sha256`.

The predictions start from landed text (E836, E837, E823, E353, E084, and **E849**, the offline
fold of the plan's O1-O3, which landed on main before the freeze) and from reading R-6 and the
pysgx oracle S0 (firmware-derived, data-private: cited as `cited/closing5/r6/reading-r6.md` and
`cited/closing5/r6/s0/RESULT.md`). All three R-6 predictions held: the arm is **sa9 bit 0** ("3D
running", set by the 3D kicks, cleared by the end-of-render path the skipped handler would have
run); TA3DCtl dword 57 counts ticks against HostCtl dword 5 (10), tick 10 stores a register
signature in dword 58, tick 20 compares and an equal one runs the lockup (dword 3 + 1, dword 8 |=
1, `SW_EVENT`, `CR_DPM_TASK_STATE` = 2, then a poll of `EVENT_STATUS` bit 6 under `lock #0` with no
exit). S0 ran that path in pysgx with the arm set by hand.

- **h1** [held out, 3 jobs]. Controls (every job, can fail): skip flag, slot 3 entry logged,
  `hold_recovery` back to N, the knob read back, dword 6 = 400000 and dwords 3, 8 = 0 0 in the arm
  dump (the kernel's reset rebuilds every firmware buffer: fork a2788bd8 `sgx_fw_build`), the tick
  gap 25000 +-10; B0: fill ok, tick alive, one end-of-render entry, bit 18 never, dwords 3, 8 = 0 0
  after the watch. **H-HWR** (predicted, now by the code): stop; lockups (dword 3 stop minus arm)
  1, dword 8 1, `sw_events` 1, dword 9 0, dword 57 0, dword 58 non-zero, dword 14 0, CCB 3 3,
  `EVENT_STATUS` bit 6 clear (the poll), TA3DCtl dword 28 0 [infer: the fill's 3D kick sets sa9 bit
  2, so the path skips the render context's dword 13 bit 11], P3 not answered; against H-NOMARK
  (0, 0, 0, dword 58 0). **H-TICKS**: `ticks_after_kick` 20 (ring ticks after the fill's kick +
  page dword 16). H-LEVEL (bit 18 all through the watch) against H-PULSE; **H-W** (after bit 15 bit
  18 still set, after bit 18 clear) against H-ALL and H-NONE.
- **h2** [held out, 4 jobs]. Controls per clock: knob read back (`0x000c3500`, `0x00186a00`),
  dword 6 in the arm dump (800000, 1600000), tick gap 50000 +-20 or 100000 +-40 (B0B is E084's
  rule's first measurement at 1600000; a failed B0 voids its clock's rows). **H-TICKS** 20 at both
  clocks against H-TIME 9..11 (800000) and 4..6 (1600000) (19.3 ms, E849, at 2.005 and 4.010 ms a
  tick); the H-HWR marks as h1; H-LEVEL.
- **h3** [held out, 3 jobs]. Controls: the `miscinfo` after the clears answered, its kick entry in
  the ring with a tick after it (the EDM was running at the clears). **H-STATE** (the arm is sa9
  bit 0, which no host write to `EVENT_HOST_CLEAR` touches and GETMISCINFO does not reset): stop,
  lockups 1, dword 8 1, the stop's `EVENT_STATUS` 0x20000000; against H-ACK18 (tick alive at 150 ms,
  lockups 0). H-TICKS 20 counted from the fill's kick (a stop with marks at another count is
  H-TICKS mixed, H-STATE untouched). H-LEVEL: bit 18 set before the clears; H-W on a running EDM.

A row is held, FAILED or cannot tell (scorekit, resgx545 main `tools/closing/scorekit.py` byte for
byte); a control that is not a pass makes the job's other rows cannot tell, B0's make the stage's
(h2: the clock's). Cannot tell: the fill's kick entry not in the ring (count), fewer than 3 ticks
in the ring (gap), no slot 3 entry, a watch of fewer than 5 reads. Family verdicts per stage in one
`SUMMARY:` line. What the results change (plan section 6, R5-7 (a)): Q166 retired if H-W holds 3
of 3 in h1; Q295 retired if h1 and h2 hold (R-6 names the state), else narrowed.

## Run (the lead)

```
cd ~/src/scratch/resgx545/closing5/r5-events
export PYTHONDONTWRITEBYTECODE=1
export SGX_TARGET_HOST=jtorra@192.168.12.234        # direct cable: jtorra@10.42.0.2
export SGX_TARGET_SSH_OPTS="-o HostKeyAlias=cedar"
export PY=../../closing/pixel-faults/.venv/bin/python PYTHON=$PY
run/guard_r5e.sh && run/freeze_r5e.sh verify
SGX_DRY_RUN=1 run/r5e.sh ATTEMPT                    # prints the commands
run/stage_r5e.sh                                    # copy and check on the laptop (~/r5e-run)
run/r5e.sh ATTEMPT                                  # the session; stops at the first problem
run/r5e.sh ATTEMPT --from h2                        # resume after a stage a stop rule ended (8)
score/score_r5e.py replay h1 b1p DIR NAME [BASE]    # read a kept job of any round as a job of this table
```

Results: `out/ATTEMPT/score-STAGE.txt`, `out/ATTEMPT/STAGE/` (records, stop dumps,
`clock-back.json`); on the laptop `~/r5e-out/ATTEMPT/STAGE`. An attempt is never overwritten.

## Tests (all offline)

`tests/run_all.sh` (about 6 minutes): the static guard, the freeze verify, `test_gen_r5.py`,
`test_scorer.py` (the replays: r4's b1p read as h1's b1p holds every H-HWR row and the count 20,
E823's b1 prints H-HWR FAILED and the count 0 FAILED, r4's b0 passes every control its files can
measure, a missing dump is cannot tell with its path; then worlds built from those records for
every family verdict and gate), `run_mock.py` (the whole session against a mock that answers by
what the runner wrote: the argv-twin test against a hand transcription of the plan's rows, the
worlds time_stop, ignore_clock, nomark, ack18, phas_any, sticky_marks, b0_stop, fill_fail, the
refusals, the traps, the guard's refusals).

## Layout

- `asm/ring_skip3p.s`, `bins/ring_skip3p.blob`, `bins/blobs.json`: R4's, byte for byte
- `gen/r5layout.py` (the one source: module, stages, rows, clocks, readers), `gen/r3layout.py`
  (R3k's), `gen/r3blobs.py` (R3k's: the landed assembler's front for the guard), `gen/gen_r5.py`
  (tables, predictions), `gen/laptop_files.py`; `tables/`, `predictions/`, `TABLES.md`, `stages.txt`
- `run/r5e_run.py` (laptop runner), `run/ops_h.py` (the job), `run/r3common.py`,
  `run/health_remote.sh`, `run/r5e.sh` (Mac driver), `run/stage_r5e.sh`, `run/freeze_r5e.sh`,
  `run/guard_r5e.sh`, `run/guard_blobs.py`, `run/guard_py.py`, `run/guard_names.py`
- `score/score_r5e.py`, `score/sc_h.py`, `score/r5common.py`, `score/scorelib.py` (R3k's, its
  layout import moved to r5layout), `score/scorekit.py`
- `tests/`: `run_all.sh`, `test_gen_r5.py`, `test_scorer.py` (+ `fixtures/real/`, copies of
  published r4-events e3p and r3k-events e3b files, `SOURCES.txt`), `run_mock.py` (+ `mockfw/`,
  `shims/`, `fake_tool.sh`, `fake_tool.py`)

## Publishing (the fold)

The directory is published whole. **No file here is firmware-derived**: the predictions and the
code cite R-6 and S0 by item and path, without instruction indices or listing text. R-6 and S0
themselves (`closing5/r6/reading-r6.md`, `PREDICTIONS.md`, `s0/RESULT.md`) are firmware-derived
and go to data-private: `tools/records/scratch_cites.py --publish --private` as
`cited/closing5/r6/...` (`ukernel.hex.dis`, `s0/s0_oracle.*`, `s0/pymod`, `s0/target` never to the
public data). `FROZEN.sha256` names their scratch paths by hash only.

## Deviations from the plan (each for a reason the build found)

1. **Tool**: the plan's `~/sgxfive-test-s1b` (sha256 `46a2d063...`, E836's), not the brief's
   `~/sgxfive-test-rgn4`: the B1P rows replicate E836 with its tool. Switching is one line in
   `TOOL.sha256`, `stage_r5e.sh`, `r5e.sh` and a refreeze.
2. **`CR_DPM_TASK_STATE` (0x0694) = 2 cannot be read on rgn4**: the kernel's regs file lists 0x0694
   as `skip` and never reads it (fork a2788bd8 `sgxfive_regdump.c`); `kreg` covers only registers
   the firmware never touches; no kernel change this round. The row is frozen (model `R6-DPM`,
   outside every family) and scores cannot tell with that reason.
3. **The render context's dword 13 bit 11 is not readable** (no debugfs file reads device memory
   at TA3DCtl dword 28; `render_words` shows the kernel's newest render context, not the
   firmware's pointer). Frozen instead: TA3DCtl dword 28 = 0 at the stop [infer, from b1p's 0 and
   R-6: the path writes the context only when sa9 bit 2 is clear].
4. **The arm's rate is judged per clock**: the landed `cmd_arm` asks 900 to 1100 Hz; at 800000 and
   1600000 the tick runs at 498.8 and 249.4 Hz (E084). The runner keeps the landed verdict unless
   only the default band can have failed it, and then asks +-10% of 399.0 MHz / dword 6
   (`ok_landed` is recorded). The tick check after the watch uses the same band.
5. **`tick_gap`** is the median gap of the slot 0 ring's consecutive ticks, before and after the
   fill's kick (at 1600000 the ring may hold one or two ticks before it); "fewer than 3 ticks"
   voids the gap only. `ticks_after_kick` has no minimum (E823's 0 is a count).
6. **"Explained stop"** (the runner's stop rule) = the marks and a readable count, not a count of
   20: a count other than 20 is H-TIME's or H-TICKS-mixed's outcome, not an unexplained stop.
7. **h2's B1P writes nothing after the stop either** (R4's after-watch clears are h1's rows); P3
   still follows each stop. h3's B0 has no clears and no `miscinfo`. h3's B1E reads STATUS once
   before the clears (the precondition of its H-W rows) and starts the watch after the `miscinfo`.
8. **`clock_back`** at every stage end (not only the session's): the plan's "knob 0, reset,
   `tick_gap` 25000 in a 20 ms window, health" made a step with its own exit (9).
9. **No sgx-sim test**: the blob is R4's bytes (`tests/sim_r4.py` of r4-events ran it); the guard
   still assembles the source with the landed tool and compares.
10. **Pins**: `FROZEN.commits` pins the repo files to resgx545 main at the freeze (`FROZEN.pin`),
    checked with `git show`; the replay's round 3 and 4 records are copies under
    `tests/fixtures/real/` (sources in `SOURCES.txt`).
11. **The mock's tool is a bash front** (`tests/fake_tool.sh`) so a job's fill reaches the mock EDM
    within milliseconds, as the C tool does (a Python start filled the ring with ticks before the
    kick); its argv is logged per job for the argv-twin test.
