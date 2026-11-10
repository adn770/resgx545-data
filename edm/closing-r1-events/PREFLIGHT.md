# R1-events preflight (prepared 2026-11-10, not run)

Everything is under `~/src/scratch/resgx545/closing2/r1-events/`. The landed tree, the data and the
past session directories were read, not changed. The laptop was not contacted. Nothing is
committed. Frozen: `FROZEN.sha256` (90 files: generators, scorer, runner, scripts, tables, blob,
loop programs, predictions, `TOOL.sha256`, and what they import from the landed tree),
`PREDICTIONS.sha256` (4 files), `LAPTOP.sha256` (the files as laid out on the laptop).

Checks that pass (2026-11-10): `run/guard_r1.sh` clean; `run/freeze_r1.sh verify`;
`tests/test_scorer.py` (all scorer checks); `tests/sim_r1.py` (all sim checks);
`tests/mock_tool_check.py` (71 of 71 commands accepted by the landed tool's `--mock`);
`tests/run_mock.py` (12 tests, 0 failed: the whole session on a mock laptop, 14 guard refusals,
stop rules, scenarios).

## 1. Offline readings

- **K0 from the kernel source** (branch resgx545). The arm path is the landed `cmd_arm`: `own_arm`,
  `own_code`, `load`, `boot`, then the runner's `miscinfo()`. `sgxfive_boot` ends with
  `sgxfive_ident_ask` (sgxfive.c, one GETMISCINFO through `sgx_ccb_submit`); the runner's
  `miscinfo()` read is a second (`sgxfive_miscinfo` calls the same function). `alive`,
  `tick_rate` and `health` read `regs` and `status` (no command). `load` unloads first
  (`sgxfive_stop` sends a POWER command, but `seq_pre_kick` zeroes the kicker word at the boot).
  So the arm path makes exactly two GETMISCINFO commands: K0 = 2 and ccbctl[0] = 2 under H-KW
  (the kicker word is `(kicker + 1) % SGX_CCB_ENTRIES`, 256). It needs no other counting.
- **A free count of the arm path**: `sgxfive_ident_ask` logs one `SGX firmware: core ... answered
  after N us` line per call. The runner counts them after its own arm marker
  (`ident_after_arm`; expected 2, 2, 1, 4 for the standard, no-miscinfo and two-extra arms) and the
  scorer makes it the control of the variant: a variant that the log does not show is cannot tell.
- **K1**: `cmd_reset` makes the kernel boot (GETMISCINFO 1) and then reads miscinfo (2); the arm
  after it unloads and loads again, so K1 = 2 as K0. K0 and K1 differ only in what came before.
- **K5 arithmetic**: the arm leaves 2; 254 kicks make 256 = 0 mod 256; the four logged kicks carry
  0, 1, 2, 3 (a kick's own entry carries the value before its bump, E746); the ticks after carry
  4; ccbctl[0] is 4; the kernel log holds 2 + 254 + 4 = 260 answers.
- **Q082, the 8x8 target and the vertex program** (the landed tool's `--mock`): `probe --tri pixel
  --width 8 --height 8 FILE` runs (18 covered pixels of 64 in the mock); `probe --tri vtxuse
  vtx-stock.bin` takes a vertex program (the slot patches only the first instruction's `phas`).
  What does not follow: a vertex LOOP. The shader is placed at an offset from its code base and
  only the `phas` is patched, so an absolute `ba` would miss, and `br` takes only a number whose
  offset base the assembler README says is not established. That is T5's open item
  (T5 is not in R1).
- **Loop lengths in sgx-sim** (instructions executed, 28 programs): prologue + iterations
  x body + 1,
  o0 = 0 in all. Body 16 at 28 iterations (448) and body 4 at 110 (440) are the equal-instruction
  pair of H-INSTR; the sim has no occupancy, no latency model (that is what T3 and T4 test).
- **E431's data through the scorer's ladder logic** (`resgx545-data/platform/event-fine`,
  `event-steps`, read only): every job's own pre read is 0x400, 53 clear, 55 and 56 set in all
  three runs, bit 6 clear to 48 and set from 56 in the 48 jobs of steps of 8.
- **S2's pages through the R1 reader**: e1c's three kicks (K = 2, 3, 4, ticks after K + 1), e1j's
  tri64 (E747's nine entries in E747's order, dispatch 100%), fill and partial (slot 2 bits 21 and
  10, no bit 19). Slot 3 had 8 rungs there and has 12 here; the reader sees zeros past the old end.
- **D2's raise knob**: 0x0624 = render_pb_pages - 0x22 (S1b: 0x320 gives 0x2fe, 0x3a0 gives 0x37e,
  0x422 gives 0x400); the proposal's numbers agree. S1b's own HP1 limit (0x2fe <= C < 0x3de) would
  allow a raise at 0x3a0 as well: D3's "no raise" is the proposal's reading, labelled held out, and
  a raise in D3 reads as "the premise failed" (cannot tell for H-RAISE), never as a pass.

## 2. What I changed from the proposal, and why

1. **K5**: window 0 over kicks 1 to 254 as proposed, but the four logged kicks run in window 1
   (only
   the kicks log) and window 2 follows for 5 ms for the ticks. Window 2 over the kicks would log
   about 15 ticks besides the four kicks in slot 0's 16 rungs (a kick call takes about 3.6 ms,
   E746); the last entries would drop.
2. **K4**: window 2 for 6 ms after the kick (not 20): S2's 20 ms windows filled the ring (9 drops).
3. **T6**: its "0 iterations" row is the stock vertex program through `vtxuse` (no loop: zero
   trips), because a vertex loop cannot be built soundly yet (section 1). Its "E357's hang
   held" row is S3's
   e1-ta-read recipe: reset, hold_recovery Y (read back), `tri --fault --wait-ms 20000` in the
   background, registers 2.8 s and 1 s later (0x480 predicted), the reset with the hold still Y,
   hold_recovery N (read back). It is a fault job, last in stage t; the debugfs reset is the only
   recovery.
4. **T3 sizes and ladders**: 8x8, 32x32, 128x128, 256x256 by 53, 56, 80, 130, 220, 440 iterations
   (24 jobs); T4 on a fill (40, 50, 53, 56) and on 8x8 (20 to 56); T1 (20, 26-30, 56); T2 (50, 80,
   100, 105, 108, 110, 112, 115, 120); T0 twice at 53 and 56. 56 jobs in all (the proposal's ~60).
   `probe --tri` prints no job time: the knob proof there is o0 = 0 on covered pixels; fills also
   get "job time grows with iterations".
5. **D5 registers**: regtimeline reads 0x012c, 0x0118, 0x0624, 0x0658 and also 0x0724 (the job's
   own start of the TA, to find the job's own 0x0624 as S1b did).
6. **Stages**: d is split into d0 (D0, D1: the controls, gate) and d1 (D2-D4), so the
   4096x4096 jobs
   run only after the ring and dispatch controls held. d1 resets and arms again before each job
   (S1b's isolation); d0 arms once.
7. **Hold lengths**: none in R1 (K7 is R3), so S2b's mid-period n is not used.
8. **Entries "from the window's own CR_TIMER stamp on"**: the runner reads CR_TIMER (regs 0x0144)
   just before it opens each window and the scorers drop earlier entries; the ring is also zeroed
   before the window, and the second page read must equal the first (window-0 proof). If the regs
   file prints 0x0144 as `skip` the stamp is None and the zeroing carries the argument.

## 3. Rows, labels and controls

Fit rows are only what the past data fitted (K = 2 after an arm, E746's kick identity, E747's
order and step rule); everything else is held out, replicates are their own kind (the scorer's
tally line is `fit / held out / replicate / control`). Controls: ticks on the 25000 grid, the
GETMISCINFO answers in the log equal the arm path's calls, T0 (53 clear, 56 set, E431), the job's
own pre read of CR_EVENT_STATUS2 after its reset is 0x400, o0 = 0 on covered pixels, the fill job
time grows with iterations, D0 and D1 reproduce E747 with dispatch 100% (they open the gate), the
job's own 0x0624 equals the written knob, the knob read-back of render_pb_pages per job.
Void: no record, a class that is not a result, no page, the ring changed after the close, a pre
read that is not 0x400, no o0 = 0, a knob read back wrong, no timeline. Cannot tell: a variant not
shown, ring drops (an absence cannot be told), a kick that timed out (K5 is a result, not a stop),
a raise that did not reproduce (D2), slot 0 full, a ladder with a void point, a failed control.

## 4. Risks and limits

No kernel change, no reboot, no build on the laptop; the only writes are debugfs own_code, own_arm,
own_res, load, boot, reset, render_pb_pages and hold_recovery (an allow-list), /dev/kmsg
(`os.open(path, os.O_WRONLY | os.O_APPEND)`), and the results page. No register write, no kreg,
kpoke or clock-gate register, no trc_hazard, no firmware-task `str`, no sa write (ring_e1 has none:
the guard checks), no ldr but CR_TIMER. The kernel's debugfs reset is used between jobs (t: every
job; k: before K1; d1: before each job). The runner stops on a watchdog or a freeze (exit 3, 6).

- stage k: low (S2's e1c with more arms; 254 kicks, each a GETMISCINFO of about 0.2 ms);
- stage t: low except t6-hang, a held TA fault last in the stage (S3 did it, 2 of 2 controls);
- d0: low; d1: the 4096x4096 job with 1500 vertices at render_pb_pages 0x320, 0x3a0 and 0x422
  (S1b ran these under the stock firmware without a stop; here the closed task runs behind
  ring_e1).
- Reset at 0.2 s (the landed `cmd_reset`) is shorter than S1b's 3 s: the pre read after it is the
  guard (a register not at 0x400 stops the stage).

## 5. Time

About 8 minutes of laptop work: k about 1.5 min (15 arms, two 254-kick bursts), t about 3 min (56
jobs, a reset each, the 8-second held fault), d0 under 0.5 min, d1 about 2 min (8 jobs, a reset and
arm each, 4.6 MB PB dumps). About 15 minutes wall with staging, health, copies and scoring.

## 6. Not closed by R1

H-KW against H-HWC (needs a kernel change); the latch order of the pre-bump value; Q082's meaning
beyond which of time, instructions or iterations (T5, a vertex loop, is not here); what sets bit 19
if D2 does not raise (H-NEVER) or the ring loses it.

## Post-freeze change (2026-11-10, after stage d1's first job; predictions unchanged)

d2-0x320 was classed trigfail: the ringtool check looked for "overflowed" in tool_out, the last
4000 characters, which the timeline's samples fill. The probe's "scene overflowed" line was in the
full output (out/d1-try1/d2-0x320.tool.txt.gz), rc 3, tick advancing, health ok. r1_run.py now
records rec["overflowed"] from the whole output; refrozen, PREDICTIONS.sha256 byte-identical.
Stage d1 rerun from its start; the first try is kept in out/d1-try1.
