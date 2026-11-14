# r15-tex preflight (read before staging)

## The laptop

- Module **B60AB0B4** (`B60AB0B475DD1E8972419B5`, fork 2a650d74) loaded = installed: the runner
  refuses any other. It is the one-shot boot; a reboot returns to stock Arch: run before any
  reboot. No debugfs knob is written by any row (session.toml `[knobs]` is empty); the only
  debugfs write is the runner's `reset 1`.
- Tool: `~/sgxfive-test-t10`, sha256 9bedc2d6db70... (resgx545 a581c06, bound by source), the
  only tool. The preflight checks the hash; nothing is built or staged as a tool.
- python3 3.10 or later on the laptop (the premise check imports scorekit.py).
- Free space: at least 300 MiB on ~ before each job; a fill probe prints 2048 pixels (about
  20 KB). Laptop files only under `~/scratch/r15t/` and `mktemp -d ~/scratch/tmp/r15t.XXXXXX`
  work directories; nothing in /tmp.

## Jobs and expected time

33 jobs: chain 18, ty 15, all safe class probe fills. About 3.5 minutes of jobs, about 8 with
staging, preflight and health. No fault, hang or reset beyond the per-job reset is expected.
Second session of the sitting (DECISIONS-R15.md: zls, tex, dpm, isp, tw).

## Stop rules

- any fault or hang (rc 4 / 6), a fatal kernel line (rc 3): the session stops
- a control without its pixel rows: the premise stops the session (rc 25)
- the second row of a stage without its 32 pixel rows: that stage stops (rc 24), the next runs
- free space (22), a latched fault before a job (14), registers unreadable (12), a failed reset
  (13), a failed health recovery (5)

## Before staging (the lead)

1. `bash tests/run_all.sh` passes and the freeze verifies (`python3 kit/session.py verify .`).
2. The module and the tool hash above, on the laptop as it is now.
3. New on the laptop, each placed so a fault loses the least: **smp1dreplace** (chain-1d-lw,
   -lh, -max3: the instruction never ran; chain's last three rows, so a fault there loses ty
   only: accept as safe class or cut them, then Q104's 1D clause is read as W x 1 under smp2d
   per R15-6 a, which chain-32x1-* already run); T1 format 9 (u16) in a mip chain; a 1-wide and a
   1-high level 0; a 256 x 32 chain at LODs up to 8.5 (the farthest frozen read dword 10926 of the
   16 mapped pages); types 1, 3 and 4 at 32 x 32 and types 1 and 4 in u modes 5 to 7 (E567 ran
   types 1 and 4 in its "risky" group with no fault, E1039 ran them in u mode 4 as safe class).
4. README.md "Deviations" 1 to 6 (D not on 256 x 32; the smp1d rows last; this builder's row
   forms and the bias row at 0x33; H-NAME16's map fitted before the freeze; the added forms;
   gen/chain.py as the model).
