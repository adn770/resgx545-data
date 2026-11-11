# R4-events preflight (prepared 2026-11-11, not run)

Everything is under `~/src/scratch/resgx545/closing4/r4-events/`. It reuses the framework of
`closing3/r3k-events` (the runner core, the stop signature, the ring reader, the stage gates) and
of `closing3/r4-reruns/b-q152` (the act op, the may_stop rule, the landed `dmesg_new(marker)`
slices, the knob and firmware-running preflight, the attempt directories, the mock on the 6421c1c
API); their kept files and the published copies (`edm/closing-r3k-events`, `edm/closing-r4-q152`)
were read, not changed. The laptop, cachix and every git repo were not touched; nothing is
committed; the clean-room guard was not run; no closed source was read. The tree the session pins and builds against is the integration worktree
`closing4/lead/wt` (branch r4-fold-rule, resgx545 `5a13042`): `tools/fwtask` with `own_end` and the
lint, `tools/closing/scorekit.py`.

## 0. Preconditions the lead checks (not automated, in the order they happen)

- The laptop is on the rgn4 module, srcversion **99CD90DA26E3AFF9C450517**, loaded = installed
  (`stage_r4e.sh` checks it; any other, E817's 230E0EF5 included, is refused by the preflight of
  every stage). No reboot is needed if the previous session ended healthy (README, "Reboot").
- `~/sgxfive-test-s1b` (sha256 `46a2d063...` in `TOOL.sha256`: the health fill and triangle and
  e3p's fill) and `/home/jtorra/sgxfive-test` (the landed gate's tool) exist and are executable.
- The debugfs files `kicker`, `kick_no_bump`, `kregnow`, `hold_recovery`, `render_rgn_arrays`,
  `render_pb_pages` and the six of the landed runner exist (`stage_r4e.sh` lists them).
- The integration tree is at `RESGX545` (default `closing4/lead/wt`, 5a13042): `FROZEN.sha256` pins
  `fwtask_run.py`, `fwtask.py`, `regs.toml`, `simrun.py` and `usse-asm` of it by absolute path;
  `FROZEN.commits` names `5a13042` for each (see README, deviation 8).
- `/lib/firmware/sgx545_ukernel.fw` is not read for a `cont4` (no blob of this session has one).
- Another session of round 4 (r4-render4x, r4-pixel) runs serially before or after, never at once;
  the laptop prefix of this one is `~/r4e-` (`~/r4e-run`, `~/r4e-out`), shared with no other.

## 1. What runs

See `README.md` for the table, the order, the time and the stops. Jobs: kb2 10, kp 4, e3p 4 (18).
Rows, parameters and frozen predictions: `TABLES.md`, `predictions/*.tsv`; the single source is
`gen/r4layout.py` (`ROW_SPEC` and the constants), checked by the generator, the runner, the guard
and the scorer against each other.

### Stage kb2 (Q290)

Per job: a debugfs reset, the arm of `ring_hold` (K = 2 after the arm), the ring cleared, the
writes, the window (window 2), a `miscinfo` 1 ms later (the kernel's own command and kick; never a
bare kick), then `post_ms` 5. Q2P: `kicker =0x42` before the window. Q3P and Q4: `kick_no_bump` Y
before the window (one-shot, read back N after); after the call timed out, the signature twice, 30
ms apart (`USE0_SERV_EVENT` bit 16). Q4: the ring cleared, a second window, one ordinary `miscinfo`
1 ms after it, the kicker file read after. Frozen readings: README. The timing control (G0P): after
each G0P job the runner counts the kick entries and the ticks after the first in the page; not
exactly 1 and at least 3, it raises exit 8 (reset and gate exact) before Q2P, Q3P and Q4 run.

Why the order changed (E819 stage kb): the 16-rung ring was full 11 ms before the kick. By E816
G0's timing the call's kick entry comes 6.70 ms after its start stamp (a `regs` read costs about 7
ms in the laptop's debugfs, E823's watch), so with the writes first and the call 1 ms after the
window the write falls about 8 ms after the first entry, with about 7 ticks before it and 6 after
(round 4's note 0a: the old Q3 ring ended at the kick, 2, 1 and 0 ticks after it).

### Stage kp (Q152)

`ring_exit2` is R3k's `ring_exit.s` reduced to ACT 4 (`idf, wdf, phas #0, #0, pixel, end, parallel,
nop.end` by `own_end`) with a KIND 2 kick pass (E813's test: `pa0` 0, `pa1[23:0]` 0x100). E0 and FK
run under the stage's arm, as E830; each KP resets and arms, writes KIND, ACT and COUNT before the
window opens, opens it and sends one `miscinfo` at once, then the signature twice (30 ms apart)
before anything else. A kept KP leaves the command unread (read = write - 1) and the call times out
(504 ms: class `kick-timeout`, the tick alive); a stop is signed (signature x2, P3, the landed
dumps), reset, gated, and the row is not replicated. Budget 1; a stop of E0 or FK ends the stage.

### Stage e3p (Q166, Q111), last

`ring_skip3p` is `ring_skip3.s` without its `str #77`: slot 3's first end-of-render pass (`pa0` 0,
`pa1[23:0]` 0x10, E747) is skipped once when the host's flag is set, logged with flag 3, and ends
`idf, wdf, phas end, nop.end`. B0: flag 0, `hold_recovery` N. B1P: flag 1, `hold_recovery` Y
(restored by the job's `finally`, by the exit handler and by a trap on TERM, HUP and INT), a `fill`
through the pinned tool, a bounded wait (2 ms steps, 4 s) for the slot 3 entry in the page, then
STATUS and STATUS2 read as fast as the debugfs reads go for 50 ms (about 9 reads), the tick checked
(a stop is signed first), the host's CLEAR (`kregnow 0x0134=`) bit 15 read at 1 and 3 ms, bit 18
read at 1, 3 and 20 ms, P3 if the tick stopped, the tool collected (6 s, killed), then a reset, the
gate and the health. A stop ends the stage after that recovery (exit 8).

## 2. The runner and the driver (new against R3k's and R4b's)

- Preflight: root, the session directory `~/r4e-run`, every file against `LAPTOP.sha256` (the
  landed `fwtask_run.py` of 5a13042 among them), the table against `r4layout.ROW_SPEC` (names,
  order, every parameter; exit 7 otherwise), the blob's `blobs.json` entry (no str, no sa or pa
  write, no cont4), srcversion loaded = installed = 99CD90DA..., the debugfs files, the four knobs
  at their defaults, the firmware running (HostCtl dword 12 advancing), the pinned tool and the
  gate tool, the previous stage's kept `stage.json` (exit 0 or 8). An output directory that holds a
  stage is refused.
- Driver (`run/r4e.sh ATTEMPT [--from STAGE]`): freeze verify, the laptop's `LAPTOP.sha256`, the
  **load step** (a health fill and triangle: both `diff: 0`, the four knobs), then per stage the
  gate, the stage (one ssh bounded by a perl alarm), the copy, the health (also the next stage's
  load step), the stage's `kernel.log` (e3p tolerates the held job's hung and recovery lines: only
  BIF and page fault lines stop it), the scorer. Any stop, failed health or lost ssh ends the
  session.
- Debugfs writes, by name: `own_code`, `own_arm`, `load`, `boot`, `reset` (the landed commands);
  `kicker` only `=0x42`; `kick_no_bump` only Y; `hold_recovery` only Y (B1P) and N through `knob`;
  `kregnow` only `0x0134=` bits 15 and 18. Never CLEAR2, a BIF register, an enable, `CLKGATECTL2`,
  `kreg`, `kpoke`, a clock-gate register, `trc_hazard`. No reboot, GRUB or build.
- Stops as R3k: the signature twice 30 ms apart with HostCtl dword 14 and the CCB offsets BEFORE
  the reset, P3, the landed dumps, then reset + gate + health. A freeze (exit 6) or a watchdog line
  (exit 3) stops all laptop work.
- Kernel log: each job's slice is the lines after its own marker by the landed `dmesg_new(marker)`,
  a line judged by the landed `is_bad_log`; tool messages are searched in the whole output.

## 3. Controls that can fail, void and cannot-tell states

Controls (rows labelled control, `predictions/*.tsv`): kb2: G0P's eight rows (the timing control
can fail: E816's real G0 fails it, `tests/test_scorer.py`), every job's tick alive and
`kick_no_bump` N, Q2P's and Q3P's shared readings; kp: E0, FK (E830 and E817's shapes), KP's acted
pass (ACTED 1, ACT_SEEN 4, flag 3); e3p: B0 (E823's), every B1P job's skipped count, slot 3 entry
and `hold_recovery` N. A control that is not a pass gates the other rows of its job (cannot tell),
and the stage controls (G0P, E0 and FK, B0) the other rows of the stage. Cannot tell: fewer than 3
ticks after the kick (kb2), mixed K after, the ring full before the kick entry (kp), a watch under
5 reads or no slot 3 entry (e3p), a signature that cannot be read. Void: no record, a class that is
not a result, no rc, a page that is truncated or whose ring changed after the close, a pass that
was not acted as designed (KP). Void and cannot-tell rows never count as a pass; a job the stage's
stop rule did not run has no rows.

## 4. Stop budget and risks

| stage | stops expected | cap | risk |
|---|---|---|---|
| kb2 | 0 | any stop ends it | low: E819 ran the same writes 12 times; Q4's second kick after an unbumped one is new (H-PEND: it may deliver two events), last in the stage |
| kp | H-PHAS-ANY 0, H-KICK-MORE 1 | 1 (KP); a control's stop ends it | medium-low: B3's shape plus a word that kept 13 of 13 tick passes; the reset recovers (13 of 13 stops in the records) |
| e3p | H-PHAS-ANY 0, H-SLOT3-MORE 1 | its first stop ends it | medium: the only stage that skips a closed handler and holds a job (`hold_recovery` Y, 3 recoveries by design), last in the session |

Risks that cannot be proved offline: (1) the 6.7 ms call latency is one sample (E816); G0P is its
control and the stage stops if it fails; (2) the number of ticks after the kick in KP (at least 4
needed; by design about 14: the kick follows the window at once); (3) what a held fill does while
the slot 3 pass ends with the phase end (the mock invents it; the runner bounds the tool at 6 s,
kills it and resets); (4) `sgx-sim` models no hardware: its tests prove encodings, control flow and
the ring, not any result.

## 5. Offline readings the freeze starts from

The notes 0a to 0e of the plan are landed (E818 and E819 Correction sections, `hw_spec.md` 12.2 in
5a13042) and read there: 0a (the old Q3 ring ended at the kick), 0b (the last ticks of an unbumped
kick carry `0x01061a74`, E751's latched mark: H-PEND's reading), 0c (a stored timer word moves the
grid for good: not read here), 0d (the timer reloads with nobody serving it), 0e (13 stops, every
one recovered by one reset, P3 answered 0 of 8). The predictions of Q3P and Q4 are those of 0a and
0b: no kick entry within the ring, ticks after the write at `...74`, K staying 2. The real records
used as fixtures (copied from the kept stage directories of the sessions that ran them,
`tests/fixtures/real/`): E813 `b3`, E816 `g0`, E817 `e0`, `fph`, `fcf`, E819 `q2`, `q3`, E823 `b0`,
`b1`.

## 6. Dated run (2026-11-11, Mac, offline)

Frozen before any job: `FROZEN.sha256` (74 files: generators, sources, blobs, scorers,
`scorekit.py`, runner, scripts, tables, predictions, `TABLES.md`, `LAPTOP.sha256`, `TOOL.sha256`,
the tests, their mock and real-record fixtures, and `fwtask_run.py`, `fwtask.py`, `regs.toml`,
`simrun.py`, `usse-asm` of the integration tree by absolute path), `FROZEN.commits` (those 5 pins;
4 tracked ones to 5a13042, `usse-asm` untracked), `PREDICTIONS.sha256` (3 files, 232 prediction
rows), `LAPTOP.sha256` (the 16 files as laid out under `~/r4e-run`, with `run/fwtask_run.py`).

| check | result |
|---|---|
| `run/guard_r4e.sh` | clean (3 blobs, 3 tables, scripts, runner and op modules) |
| `run/freeze_r4e.sh verify` | files verified (FROZEN.sha256, PREDICTIONS.sha256, FROZEN.commits by `git show`) |
| `tests/test_gen_r4.py` | 42 checks, 0 failed (tables and predictions are the generator's; job counts; every job has a control) |
| `tests/sim_r4.py` | 46 checks, 0 failed (ring_exit2's tick and kick passes, ring_skip3p's skip-once, ring_hold; lint clean; no str) |
| `tests/test_scorer.py` | 27 checks, 0 failed (E813, E816, E817, E819, E823 real records; the engine; a shut gate) |
| `tests/run_mock.py` | 14 tests, 186 checks, 0 failed (the default session; every world: H-LATCH, H-CNT, H-HWC, H-PEND, H-NOEVENT, H-LATE, H-PHAS-ANY, H-KICK-MORE, H-SLOT3-MORE, H-LEVEL, H-PULSE, H-W, H-ALL, H-NONE; G0P without a kick entry stops the stage; a control's stop; the refusals; the trap on SIGTERM; 26 guard refusals; the landed API) |
| `tests/run_all.sh` | RUN_ALL PASSED (about 7 minutes) |

Freeze hashes (sha256, first 16 hex): `FROZEN.sha256` b30c1d8145dfff38, `PREDICTIONS.sha256`
9952faf51cb84296, `LAPTOP.sha256` c4781cc311a150b3, `FROZEN.commits` f4ec1b296b3bac97. Blobs:
ring_hold `fa0f79db...` (S2b's), ring_exit2 `ed4bd0e6...`, ring_skip3p `3b35d3af...`.
