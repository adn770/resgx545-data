# r6-held part P preflight (prepared 2026-11-12, not run)

Everything is under `~/src/scratch/resgx545/closing6/r6-held/p/`. It reuses round 5's
`closing5/r5-events` (published `edm/closing-r5-events`, E855-E857): the blob, the runner, the
stop signature, the ring reader, the scorer, the mock, the driver; their files were copied, not
changed there. The laptop, cachix and every git repo were not touched; nothing is committed; the
clean-room guard was not run. The repo the session pins is resgx545 main **d9b2969**, read only
(`FROZEN.pin`, `FROZEN.commits`: `tools/fwtask/fwtask_run.py`, `fwtask.py`, `regs.toml`,
`simrun.py`, `tools/usse-asm/usse-asm`, `tools/closing/scorekit.py` as `score/scorekit.py`, and the
records E084, E836, E837, E849, E855); the round 5 kept files the scorer replays are copies of
resgx545-data **e5cdaf0a** (`tests/fixtures/real/SOURCES.txt`).

## 0. Preconditions the lead checks (in the order they happen)

- **The new kernel**: the laptop booted one-shot into fork branch `r6-kernel` tip 3f0b3e74
  (`boot-test-kernel.sh`, the user's OK), module srcversion **41E2F5C756F96D20F7109A4**
  (gma500_gfx.ko sha256 8a32dada...576a as built), loaded = installed. `stage_p.sh` and the
  runner's preflight refuse any other (the rgn4 module 99CD90DA is refused by name).
- **Order**: part P is one stage; run it on its own, before or after part H / r6-render4x stage B
  as the lead orders, never at the same time (one laptop prefix each: P is `~/scratch/r6h/p/`).
  A held part-H fault left latched, or render_tail_room left non-zero by stage B, stops P's
  preflight (the knobs must be at their defaults).
- **Tool**: `~/sgxfive-test-s1b` (sha256 `46a2d063...`, `TOOL.sha256`: E855's tool) and
  `/home/jtorra/sgxfive-test` (the landed gate's tool) must still be on the laptop. The round 5
  handover (`plans/resgx545-handover-2026-11-12-r5.md`) lists the laptop's leftovers to clean
  (`/tmp/tmp.*`, `~/r5?-*` dirs) and does not name these tools: **check they were not removed**
  (`stage_p.sh` checks both and the hash; if s1b is gone, rebuild nothing: stop and ask).
- Debugfs files: the landed runner's (`own_code`, `own_arm`, `own_res`, `load`, `boot`, `reset`,
  `regs`, `status`, `miscinfo`), `kregnow`, `hold_recovery`, `timer_clock`, `kick_no_bump`,
  `render_rgn_arrays`, `render_pb_pages`, and the new kernel's **`peek`** and
  **`render_tail_room`** (`stage_p.sh` lists them; the runner checks again).
- **The peek** prints exactly one line `reg 0x0694 0x........` at the load step's health and at
  the runner's preflight (a read: its offset is the kernel's default 0x0694, never written). No
  line (the kernel's -ENODEV: no firmware running; -EPERM) stops the preflight (exit 1).
- The knobs read their defaults before the stage: `hold_recovery N`, `render_rgn_arrays 0`,
  `render_pb_pages 0x422`, `kick_no_bump N`, `timer_clock 0`, **`render_tail_room 0`**.
- At least **300 MiB free on ~** (the driver before the load step and the stage, the runner before
  each job: exit 21), and `~/scratch/tmp` exists (`stage_p.sh` makes it).
- `run/freeze_p.sh verify` passes on the Mac (every pin re-checked with `git show d9b2969:PATH`).

## 1. What the laptop sees

Files: the staged tree `~/scratch/r6h/p/stage/` (exactly `gen/laptop_files.py`'s list, the
landed `fwtask_run.py` and `LAPTOP.sha256`), the results `~/scratch/r6h/p/out/ATTEMPT/p1/`, one
work directory a job `~/scratch/tmp/r6hp.XXXXXX` (the tool's cwd; whatever it leaves is copied to
`out/.../NAME.work/`, then the directory is removed; all removed at any exit). Nothing in `/tmp`.
No `run/` directory is used (the runner is part of the staged tree): the round 6 layout
`~/scratch/<prefix>/{run,stage,out}` is met with `stage` and `out`.

Writes, all through the debugfs as root (`sudo -n python3 r6hp_run.py`): the landed `own_code`,
`own_arm`, `load`, `boot`, `reset`, the page (`own_res`), `hold_recovery` (Y / N),
`timer_clock` (0 only), `kregnow` with `0x0134=0x8000` and `0x0134=0x40000` only (after a B1P's
stop and its peek read). The peek is only read (`timeout -k 5 10 cat`): at each job's arm, at a
stop right after the signature registers (before the dumps, the clears and P3), after the clears,
after the recovery; B0 after the watch. No other register, no clock-gate register, no
`trc_hazard`, no `kreg`, no `kicker`; the blob carries no firmware `str`. Every kmsg marker by
`os.open(O_WRONLY | O_APPEND)`. Every ssh and scp is bounded by a perl alarm; the health tool
calls by `timeout -k 5 60`; the job's own fill is started exactly as E855 did (no wrapper: its
kick must land within the ring window) and bounded by the runner (collected after 6 s, then
killed). The landed gate (`fwtask_run.gate`) runs its tool without a timeout (landed code, as in
E855); the stage is bounded by the driver's alarm (600 s).

## 2. Stop budget and the order of a stop

Budget 2 (one per B1P). A stop: the signature twice, **the peek**, the landed dumps, the
explanation (marks + count readable), the clears and their peek, P3, the status dump,
`hold_recovery` N, the tool collected, then the reset, the gate, the health and the recovery's
peek. E855 recovered 3 of 3 such stops by one reset each (and E856, E857 more). A B0 stop, an
unexplained stop or a third stop: exit 8. Exit 5 at any recovery: stop and ask the user.

## 3. Before staging: the offline checks (done at the freeze)

`tests/run_all.sh` passed on the frozen tree (`debug/run_all.out`). The scorer was replayed on
E855's kept stops (every E855 row held, the peek rows cannot tell) and on round 4's and E823's
files. The dry run `SGX_DRY_RUN=1 run/p.sh ATTEMPT` prints the commands without the laptop.
