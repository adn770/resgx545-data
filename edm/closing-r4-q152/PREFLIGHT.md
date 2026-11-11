# R4b preflight (prepared 2026-11-11, reworked to blocks the same day, not run)

Everything is under `~/src/scratch/resgx545/closing3/r4-reruns/b-q152/`. It reuses the framework of
R3k-events (`resgx545-data/edm/closing-r3k-events`, the session of E817): the runner, the stop
signature, the readers, the mock EDM. The published files were read, not changed. The laptop,
cachix and every git repo were not touched; nothing is committed.

## 1. FCF: which row, how many runs, and its context

- Row FCF of stage f (`ROW_SPEC["f"]`, ACT 3 = `ACT_CFI`): the acted tick pass ends with
  `cfi.global, idf, wdf, nop.end` (no `phas`). Two jobs were frozen: `fcf` (held out) and
  `fcf-r2` (replicate), both `run_if all_kept:FB:1`.
- `out/f/stage.json`: `jobs_run` e0, fc4, fc4-r2, fb, fb-r2, **fcf**, fcf-r2, fph, fph-r2. One arm
  at the stage start, no reset between jobs. `fcf` ran once, the sixth job after the arm, class
  `stop`. `fcf-r2` was `skipped` ("a stopped row is never replicated"). After the stop: reset,
  gate, health, re-arm (`rearm1.json`), then fph and fph-r2 kept the tick. So fph is not between
  the arm and fcf: it is the first job after the stop's re-arm.
- E817's signature (`out/f/fcf.json`, two samples 40 ms apart): CR_CLKGATESTATUS 0x000ccfa0 (busy),
  USE0_SERV_EVENT 0x1149 in both (frozen, empty bit clear), EVENT_TIMER 0x0102619f then 0x0104389b
  (counting), EVENT_STATUS 0x20000000, CCB offsets 2 and 2 (read - write 0), HostCtl dword 14 0,
  4 ring entries (flags 1 and 3, ACT_SEEN 3), no entry after the acted pass, P3 not answered (a
  timeout at 505 ms, 0 new ring entries).
- The window stamps (CR_TIMER, 24.94 MHz) put E817's jobs about 0.65 s apart under one arm, and
  fph 3.4 s after fcf (the stop's recovery and re-arm included).

## 2. Jobs, order and time

Three blocks, 21 jobs (`TABLES.md`). Block N: **reset and arm**, bNe0, bNfc4, bNfc4-r2, bNfb,
bNfb-r2, fcfN (E817's sequence from its arm to fcf, job for job: kind, act, count, `pre_ms` 3,
`open_ms` 20, window 2, the same blob and arm line; `tests/test_gen_r4b.py` checks it against
E817's table); if fcfN stopped, the recovery and a re-arm; then fkN (E817's fph). No E817 job
between the arm and fcf is left out, and the block adds none: the choice is E817's exact sequence,
because its `stage.json` gives it and no record says the earlier jobs are irrelevant.

Time, from E817's own stamps (not measured here): a reset and arm about 3 s (R3k's figure), six jobs
under the arm about 4 s, a stop's recovery and re-arm about 3.5 s, fkN under 1 s: about 12 s a
block, **about 40 s for the stage** under H-REP. The session: staging about 1 minute, load step
20 s, the stage 1 minute with the end reset and gate, copy, health and score 30 s: **about 3
minutes**; plan 10. The driver's alarm on the stage is 720 s.

## 3. Hypotheses, held out, controls

- **H-REP** (FCF's stop reproduces with E817's exact signature) and **H-NOREP** (FCF keeps the
  tick), as in `README.md`. Held out: `fcf1`; replicates `fcf2`, `fcf3`. A replicate is REPRO,
  STOP-OTHER, KEPT or cannot tell (`score/score_r4b.py`, top docstring); STOP-OTHER refutes both.
  Replicates that disagree are mixed (`scorekit.combine`); the headline (`scorekit.headline`) is
  printed only when every control passed and a row decided, with the count of decided rows.
- **Controls**, all of the same shape as the stage's jobs (plain tick passes of `ring_exit`, the
  same times, blob and arm line), with values from E817's own kept jobs of the same shape:

| control (block N) | passes when | value from |
|---|---|---|
| bNe0 | 12 to 16 entries, on the 25000 grid, nothing acted | E817 `e0` (14 entries) |
| bNfc4, bNfc4-r2 | kept; flag 4, ACT_SEEN 6; next entry 24950..25050; read - write 0; dword 14 0 | E817 `fc4`, `fc4-r2` (+24994, +24995) |
| bNfb, bNfb-r2 | kept; flag 3, ACT_SEEN 5; the same window and marks | E817 `fb`, `fb-r2` (+24995, +24995) |
| fkN | kept; flag 3, ACT_SEEN 4; the same | E817 `fph` (+24994), its first job after the re-arm |
| armN | block N's arm resolves exit 0x1974 | E817 `arm.json` (exit_index 6516) |
| rearmN | the re-arm after a stopped fcfN resolves exit 0x1974 (no stop: none due, PASS) | E817 `rearm1.json` |

- **Gates** (`scorekit.gate`, `gated`, per block): fcfN is judged only if block N's controls and
  armN passed, and for N > 1 also fk(N-1) and rearm(N-1). A control that is not PASS (FAILED, or
  NODATA: no record, skipped, void) makes that replicate cannot tell. fk3 and rearm3 gate no
  replicate; they are reported, and with all the others they decide the headline.
  `tests/test_gen_r4b.py` checks every frozen control value against E817's kept records, and
  H-REP's values against `fcf.json`.

## 4. The runner and the driver (what is new against R3k's `r3_run.py` and `r3.sh`)

- Preflight (nothing is touched before it passes, exit 1): root; the session directory `~/r4b`;
  every file against `LAPTOP.sha256` (the landed `fwtask_run.py` of 6421c1c among them); the table
  against `r4blayout.ROW_SPEC` (names, order, acts, `run_if`, `may_stop`, `block`, `block_start`;
  exit 7 otherwise); the blob's `blobs.json` entry and the firmware digest 6a00268e... that `cont4`
  is tied to; srcversion loaded = installed = **99CD90DA26E3AFF9C450517** (E817's 230E0EF5 is
  refused); the debugfs files `own_code own_arm own_res load boot reset regs status miscinfo
  kick_no_bump hold_recovery render_rgn_arrays render_pb_pages`; the four knobs at their defaults
  (hold_recovery N, **render_rgn_arrays 0x00000000**, render_pb_pages 0x422, kick_no_bump N); the
  firmware running (HostCtl dword 12 advancing); the pinned tool and the gate tool. An output
  directory that already holds a stage is refused.
- **Load step**: after a fresh boot the firmware is loaded only by a client job (R3k's
  `attempt1-nofw`: ENODEV). The driver runs `health_remote.sh` (a fill and a triangle through
  `~/sgxfive-test-s1b`) before the stage; both must print `diff: 0` and the knobs must read their
  defaults, else it stops (31 to 36) without starting the runner.
- **Blocks**: a debugfs reset and the arm (the landed `cmd_reset`, `cmd_arm`) in the first job of
  each block only (`block_start`, kept as `bNe0.arm.json`); no reset between the jobs of a block;
  after a stopped fcfN the recovery and a re-arm (`rearm-fcfN.json`). This replaces the brief's
  "reset before each job" by the user's decision of 2026-11-11 (E817's context). The first job must
  start a block, else exit 7.
- **Kernel log by marker**: each job's log is the slice after its own kmsg marker, by the landed
  `dmesg_new(marker)` (6421c1c); a line is judged by the landed `is_bad_log`, so the reset's
  "SGX reset: after the fault clear" info line is not bad. The arm is read the same way. Markers
  are written with `os.open(O_WRONLY | O_APPEND)`.
- Tool messages are searched in the whole output (`captured`); a watchdog line in a job's slice
  is fatal (exit 3, no reset); the driver also checks the stage's whole `kernel.log`.
- Knobs: the session writes none. The only debugfs writes are the landed commands' (`own_code`,
  `own_arm`, `load`, `boot`, `reset`); `own_arm` is left off by the reset at every exit the runner
  controls (the cleanup on any Stop, the end). The driver reads the four knobs after the stage.
- Gates and verdicts from kept output only: `run_if` from the records of this run, the scorer from
  the copied stage directory.

## 5. Stop rule, and how three blocks fit R3k's rule

R3k's rule (E817's stage f, and R3-E2 a for e3b): "a stopped row is never replicated"; e3b's B1
ran once for that reason. This session exists to replicate one, so by the user's decision it
changes the rule for the FCF rows only:

- fcf1, fcf2 and fcf3 are three rows of one group, each marked `may_stop`; no control is.
- After an fcf stop: the signature twice before anything else, P3, the dumps; then the debugfs
  reset, the gate (fill and triangle) and the health (`end()`); a recovery that is not exact ends
  the stage (exit 5); then the re-arm and fkN under it, as E817's fph after its re-arm.
- Block N+1 runs only if fkN kept the tick (`run_if all_kept:FKN:1` on bN+1's first jobs), and
  starts with its own reset and arm: every replicate starts from a recovery measured to work and
  from E817's context (one arm, five jobs, then fcf).
- Budget 3 stops, one per block (the same cap as e3b's 3-stop budget). A stop of a control (any
  bN job, fkN) ends the stage at once (exit 8), after the reset and the gate.
- So the session makes at most three stops, all of the FCF group, each followed by one control
  pass and, but for the last, by a fresh block.

## 6. te_aa and render_rgn_arrays

No job of this session touches `te_aa` bits 31:30 or `render_rgn_arrays`: the stage runs no
render; its only client jobs are the health fill and triangle (load step, after the stage) and the
landed `cmd_gate`'s fill and triangle after each stop and at the end. Those are 1x jobs on
contexts without the 4x flag: libsgxfive sets `te_aa` 0x20000000 by default (`render.c`), which
the fork's KUnit lists as 1x [infer: the pinned `~/sgxfive-test-s1b` and the gate tool are older
builds; E825 and E827 show their default triangle is not a 4x job]. At the new default 0
(automatic) such a context gets one array, the old layout, and is not refused. The runner and the
driver never write `render_rgn_arrays`; both refuse to run unless it reads 0x00000000.

The module diff since E817's (fork `8fc748b0..a2788bd8`, two commits) touches render contexts
only (`sgx_render.c`, `sgxfive_ctx.c`, `sgxfive_cmd.c`, `sgxfive_debug.c`, the UAPI header); no
firmware-task, verifier or overlay file changed [read from `git diff --name-only`].

## 7. Freeze, tests, guard (dated run, 2026-11-11, Mac, offline)

Frozen before any job: `FROZEN.sha256` (28 files: source, blob, `blobs.json`, generator, layouts,
scorer, `scorekit.py`, `scorelib.py`, runner, scripts, table, predictions, `TABLES.md`,
`LAPTOP.sha256`, `TOOL.sha256`, `tests/test_gen_r4b.py`, and resgx545's `tools/fwtask/fwtask_run.py`,
`fwtask.py`, `regs.toml` by absolute path), `FROZEN.commits` (tools/records/frozen.py's finder:
fwtask.py at 7aaa017, fwtask_run.py at 6421c1c, regs.toml at 19f64df; verified by
`run/freeze_r4b.sh verify` with `git show`; unchanged by the rework, the pins are the same),
`PREDICTIONS.sha256`, `LAPTOP.sha256`.

| file | sha256 |
|---|---|
| FROZEN.sha256 | 025ec710858310cf9b6541c23db5a70a2e9337522cb7c6aa52b71340199c858e |
| PREDICTIONS.sha256 | e2b8d409e978fdb4760a65f267a522fa06d3e087a3212c68ccec36820c737489 |
| LAPTOP.sha256 | 0102abbc96bd5c72e40cb9d13d0f2771b66dd819890547593a57bb046a38102a |
| FROZEN.commits | 1724757184ed6820c8b739d1d573df7c1856910aa07cae4c51385205732acc50 |
| predictions/fr.tsv | in PREDICTIONS.sha256 (174 predictions) |

`tests/run_all.sh`: RUN_ALL PASSED (guard clean; freeze verified; test_gen_r4b 68 ok;
test_score_r4b 41 ok; run_mock 7 tests, 110 ok). Tests written first and seen failing, kept in
`debug/`: the first build's `red-test_score_r4b.txt`, `red-run_mock.txt`, `red2-run_mock.txt`;
the block rework's `red3-test_gen_r4b.txt` (5 failures: job order, budget and reset, block starts,
E817's sequence, run_if), `red3-test_score_r4b.txt` (the worlds of the old table: no block 1),
`red3-run_mock.txt` (14 failures: the old order, resets per job, no re-arm names, the new worlds).

Mock worlds (`tests/run_mock.py`, each scored as predicted):

| world | stage | FCF replicates | verdict |
|---|---|---|---|
| default (E817's) | exit 0, 3 stops, 21 jobs | REPRO, REPRO, REPRO | H-REP held, 3 of 3 decided |
| `fcf_keep` | exit 0, 0 stops | KEPT x3 | H-NOREP held |
| `fcf_keep2` | exit 0, 2 stops | REPRO, KEPT, REPRO | mixed |
| `ctx5` (the stop needs more context than a block) | exit 0, 0 stops | KEPT x3 | H-NOREP held |
| `ctx_first` (only the stage's first arm stops) | exit 0, 1 stop | REPRO, KEPT, KEPT | mixed |
| `sig_pending` (idle clock) | exit 0, 3 stops | STOP-OTHER x3 | both refuted |
| `p3_answers` | exit 0, 3 stops | STOP-OTHER x3 | both refuted |
| `fb_stop2` (b1fb-r2 stops) | exit 8, 5 jobs | not run | controls FAILED, cannot tell |
| `fph_stop` (fk1 stops) | exit 8, 7 jobs | fcf1 REPRO | block 2 never ran |
| `fb_stop3` (b2fb stops) | exit 8, 11 jobs | fcf1 REPRO, others not run | fcf1 decided, H-REP cannot tell |
| `fatal@fcf2` | exit 3 | | no reset after the watchdog line |
| `exit0` (arm) | exit 4, 1 job | | |

Plus the preflight refusals (firmware not running, render_rgn_arrays 1, hold_recovery Y, E817's
module), a failed load step (exit 31, runner not started), an existing attempt (exit 22), and in
the default world: 7 resets (3 block starts, 3 stops, the end), one reset in each block start's
log slice and none in any other job's, arms `b1e0`, `b2e0`, `b3e0` and re-arms after fcf1, fcf2,
fcf3, no knob written. The scorer's worlds (`tests/test_score_r4b.py`) are built from E817's own
kept records, including per-block gates (a block-2 control gates fcf2 only, fk1 gates block 2,
fk3 gates none, a bad arm or re-arm gates its block).

Clean-room guard: `tools/clean-room/guard.py --tree` over a temporary git copy of every file of
this directory (130 files, debug/ included): **0 findings** (counts only, never `--show`).

## 8. Deviations and user decisions

1. **Replicates after a stop** (section 5): taken by the user, 2026-11-11 (three blocks).
2. **No reset between the jobs of a block**: taken by the user (E817's context). The brief's
   "reset before each job" holds at each block start only.
3. **fkN is E817's fph** (ACT 4, `idf, wdf, phas end, nop.end`), not FB's pass: E817's first job
   after its re-arm was fph. FB's pass is in every block (bNfb, bNfb-r2).
4. **Tools**: the health tool is R3k's `~/sgxfive-test-s1b` (46a2d063..., `TOOL.sha256`); the gate
   tool `/home/jtorra/sgxfive-test` is recorded in `env.json`, not pinned (as in R3k).
5. **No K0-style gate**: the R3k sessions gated K1 on K0's stages; here the load step and the
   preflight (knobs, firmware running) replace it. What ran before E817's arm (K0's stages, and
   the R3k stage ends' reset) is not reproduced beyond the reset each block starts with.
