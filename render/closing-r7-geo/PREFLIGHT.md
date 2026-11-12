# r7-geo preflight (read before staging)

## The laptop

- Module **41E2F5C7** (fork 3f0b3e74: rgn4 + render_tail_room + peek + bif_flush) loaded = installed: the runner refuses any other
  (`SRCV_EXPECT=41E2F5C756F96D20F7109A4`).  Run r7-geo on the current boot of 41E2F5C7 (or a one-shot boot of it with the user's
  OK), **before** r7-faults' rows (DECISIONS-R7 R7-2: a wedged boot ends at the distro kernel), and before the one-shot boot of
  37EC97AB (r7-dpm's s-k): r7-geo needs nothing of 37EC97AB and was not built for it.
- Debugfs at the defaults, read only and never written but `reset 1`: hold_recovery N, render_pb_pages 0x422, alias_skip 0,
  render_rgn_arrays 0, render_tail_room 0 (checked at the start and after every stage); peek and bif_flush must exist (not used).
- Tools: `~/sgxfive-test-rgn4` sha256 e6951558... (unchanged since round 4); `~/scratch/r7g/bin/sgxfive-test` is staged by
  `run/stage_g.sh` (round 6's t6, 97df5c0e..., for zf's odd heights only).
- **python3 3.10 or later on the laptop** (new this round): a control's premise check runs `python3 sessioncheck.py premise`, which
  imports scorekit.py (`float | None` annotations).  The preflight of every stage with a control checks it (a reading must pass, a
  missing one must STOP) and prints `python3 --version`; an older python stops the stage at its preflight (rc 1) before any job.
  CHECK THIS FIRST (`ssh LAPTOP python3 --version`).
- Free space: at least 200 MB on ~ before each job, 200 MB + 8 KiB a depth page before a depth row (336 MB before each 4096 x 4096
  depth row).  Laptop files only under `~/scratch/r7g/` (run, stage, bin, out) and `mktemp -d ~/scratch/tmp/r7g.XXXXXX` work dirs
  (removed once kept); nothing in /tmp.

## Jobs and expected time

628 jobs: xf 10, tx 18, zd 102, zi 26, zf 242, zs 230.  About 60 minutes of jobs, about 75 with staging and health (per-stage
alarms in g.sh: 15, 30, 80, 80, 70, 70 minutes).  No fault, hang or reset beyond the per-job reset is expected.

## Stop rules (per stage; the driver stops on the first non-zero status)

- any fault or hang (rc 4, after strict health); a fatal kernel line (rc 3); a job that does not return (rc 6)
- an unexplained failure of a row that is not soft or a gate (rc 4)
- soft rows (zd's 4096 x 4096 depth rows, zi's probes from 1024 x 768): a failure that is no fault is recorded in void.tsv and the
  stage goes on; the second in a row stops (rc 24)
- gate rows (zf's first row of 32 x 16, 16 x 8, 64 x 33, 96 x 47): a refusal (rc 1, no diff line) skips that size (void.tsv,
  cannot tell); the stage goes on
- the second row without a `target: ... hash` line (rc 17); a depth dump not written or not kept (rc 23); a control without a
  reading it declares (rc 25); free space (rc 22); a latched fault before a job (rc 14); registers unreadable (12); a failed reset
  (13); a failed health recovery (5); strict health after tx's jobs (16)
- on the Mac: a kept file the scorer reads missing (`sessioncheck.py kept`, rc 40), no scorer SUMMARY (38), a knob not at its
  default after a stage (42)

## Before staging (the lead)

1. `bash tests/run_all.sh` → `ALL TESTS: PASS` (about 15 minutes; builds the pinned assembler into debug/asm if missing).
2. `run/guard_g.sh && run/freeze_g.sh verify`; FROZEN.commits pins the resgx545 files the freeze names by absolute path
   (main 1c64f3a: tools/closing/scorekit.py, sessioncheck.py, tools/bringup/health.sh).
3. The laptop's python3 version (above) and free space on ~.
4. `run/stage_g.sh`, then `run/g.sh`.

## Risks

- Lowest class throughout (tri, fill, map-texture probes).  The 4096 x 4096 depth rows allocate a 64 MB depth buffer and a 64 MB
  target in the tool on a 2 GB laptop (E680 ran 4096 x 4096 colour only): soft, last in zd.  E606's I0 probe never ran above
  256 x 128: soft from 1024 x 768.  Targets below one tile (32 x 16, 16 x 8) never ran: gated.
- Type 4 and 5 probes are E725/E567's risky class (no fault there): a health check after each tx job.
