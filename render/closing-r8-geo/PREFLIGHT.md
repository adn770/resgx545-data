# r8-geo preflight (read before staging)

## The laptop

- Module **37EC97AB** (fork 664fd0d0) loaded = installed: the runner refuses any other
  (`SRCV_EXPECT=37EC97AB0CB37213C42FCCC`). Any test boot with the sgxfive render node will do (the
  plan's rows need no r6/r7 knob); r8-geo writes no debugfs file but `reset 1`.
- Run r8-geo **before** the one-shot boot of the r8-k module (decision R8-5: "one one-shot boot
  after r8-geo"), and after round 7's sessions.
- Tool: `~/sgxfive-test-rgn4`, sha256 e6951558a93b... (unchanged since round 4; from resgx545
  4623753). The preflight checks the hash; nothing is built or staged as a tool. t7
  (`~/scratch/r7r/bin/sgxfive-test-t7`, f2df4f99...) is not used.
- python3 3.10 or later on the laptop (the premise check imports scorekit.py).
- Free space: at least 300 MiB on ~ before each job (`min_free_mb`). The vdm stage keeps each job's
  render memory (about 4.6 MB of parameter buffer a job, 8 jobs). Laptop files only under
  `~/scratch/r8g/` and `mktemp -d ~/scratch/tmp/r8g.XXXXXX` work directories; nothing in /tmp.

## Jobs and expected time

60 jobs: cube 19, seam 24, addr 9, vdm 8 (risky, last). About 4 minutes of jobs, about 25 with
staging, preflight and health. No fault, hang or reset beyond the per-job reset is expected.

## Stop rules

- any fault or hang (rc 4 / 6), a fatal kernel line (rc 3): the session stops
- a control without its pixel rows: the premise stops the session (rc 25)
- the second row of a stage without pixel rows: that stage stops (rc 24), the next one runs
- free space (rc 22), a latched fault before a job (14), registers unreadable (12), a failed reset
  (13), a failed health recovery (5), strict health after a vdm job (16)

## Before staging (the lead)

1. `bash tests/run_all.sh` passes and the freeze verifies (`python3 kit/session.py verify .`).
2. The module and the tool hash above, on the laptop as it is now.
3. `closing8/offline/r8-1` (the O8 R8-1 table) still hashes as gen/o8/q141_r8pred.sha256 says; if
   O8 changed its table after this freeze, this session runs the copy it froze (decide whether a
   new session directory is needed).
