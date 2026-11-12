# R5-events preflight (prepared 2026-11-12, not run)

Everything is under `~/src/scratch/resgx545/closing5/r5-events/`. It reuses round 4's
`closing4/r4-events` (published `edm/closing-r4-events`): the blob, the runner core, the stop
signature, the ring reader, the stage gates, the mock, the driver; their kept files were read,
not changed. The laptop, cachix and every git repo were not touched; nothing is committed; the
clean-room guard was not run. The repo the session pins is resgx545 main, read only, at the
commit in `FROZEN.pin` (`tools/fwtask/fwtask_run.py`, `fwtask.py`, `regs.toml`, `simrun.py`,
`tools/usse-asm/usse-asm`, `tools/closing/scorekit.py` as `score/scorekit.py`).

## 0. Preconditions the lead checks (in the order they happen)

- This session runs FIRST of round 5 and alone (no other session at once). Laptop prefix `~/r5e-`
  (`~/r5e-run`, `~/r5e-out`), shared with no other session.
- The laptop is on the rgn4 module, srcversion **99CD90DA26E3AFF9C450517**, loaded = installed
  (`stage_r5e.sh` checks it; the runner's preflight refuses any other). No reboot: if the laptop
  was rebooted to stock Arch, the session needs the one-shot test boot, with the user's OK.
- `~/sgxfive-test-s1b` (sha256 `46a2d063...` in `TOOL.sha256`) and `/home/jtorra/sgxfive-test`
  (the landed gate's tool) exist and are executable (`stage_r5e.sh` checks both).
- The debugfs files `kregnow`, `hold_recovery`, `timer_clock`, `kick_no_bump`,
  `render_rgn_arrays`, `render_pb_pages` and the landed runner's (`own_code`, `own_arm`,
  `own_res`, `load`, `boot`, `reset`, `regs`, `status`, `miscinfo`) exist (`stage_r5e.sh` lists
  them; the runner checks again).
- The knobs read their defaults before every stage: `hold_recovery N`, `render_rgn_arrays
  0x00000000`, `render_pb_pages 0x00000422`, `kick_no_bump N`, **`timer_clock 0x00000000`**
  (the runner refuses otherwise; the driver's health line checks `timer_clock` after every stage).
- `run/freeze_r5e.sh verify` passes on the Mac (it re-checks every pin with `git show` at
  `FROZEN.pin` and the hashes of the cited plan, `DECISIONS-R5.md`, R-6 and S0).

## 1. What the laptop sees

Writes, all through the debugfs as root (`sudo -n python3 r5e_run.py`): the landed `own_code`,
`own_arm`, `load`, `boot`, `reset`, the page (`own_res`), `hold_recovery` (Y / N),
`timer_clock` (0, 800000, 1600000 only: the runner's `knob` refuses any other value, the guard
checks the code and the tables), `kregnow` with `0x0134=0x8000` and `0x0134=0x40000` only
(`CR_EVENT_HOST_CLEAR` bits 15 and 18; h1 after the stop, h3 at the slot 3 entry). No other
register, no clock-gate register, no `trc_hazard`, no `kreg`, no `kicker`; the blob carries no
firmware `str`, no `cont4`, no sa or pa write (`run/guard_blobs.py` on the assembled code). Every
kmsg marker by `os.open(O_WRONLY | O_APPEND)`. Kicks: the fill's (the tool), `miscinfo` (the
kernel's command and kick: the arm's, h3's one after the clears, P3 after a stop). Every ssh and
scp is bounded by a perl alarm; the runner's loops are bounded `for` loops.

Knobs put back: each job's `finally` (`hold_recovery` N), the runner's exit handler and a trap on
TERM, HUP and INT (`hold_recovery` N, `timer_clock` 0), the cleanup after any stop of a stage
(both, before its reset), `clock_back` at every stage end (`timer_clock` 0, read back, a reset, the
25000-unit grid checked). After an abnormal end where no reset followed the knob's put-back, the
firmware still runs at the last clock until the next reset: the next session's first reset (every
job of every round 5 session resets before it arms) boots it at 400000.

## 2. Stop budget and the order of a stop

Per stage h1 3, h2 4, h3 3 (one per B1P / B1E): 10 predicted stops. A stop: the signature twice
and the landed dumps first (before any write), then the explanation (marks + count readable),
h1's clears, P3, the status dump, `hold_recovery` N, the tool collected (6 s, killed), then
`end()`: the reset, the gate (fill and triangle through `/home/jtorra/sgxfive-test`), the health.
The kept stops of this busy signature were recovered by one debugfs reset, b1p's marked one among
them (E836: reset, gate and health exact; E849 lists the dumps): the marked kind has one recovery
on record, so h1's first B1P is the test of a second. Exit 5 at any recovery: stop and ask the user.

## 3. Before staging: the offline checks (done at the freeze)

`tests/run_all.sh` passed on the frozen tree (`debug/run_all.out`). The scorer was replayed on the
kept round 4 and E823 files (README, Tests). The dry run `SGX_DRY_RUN=1 run/r5e.sh ATTEMPT` prints
the commands without touching the laptop.
