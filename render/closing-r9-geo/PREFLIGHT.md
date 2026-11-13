# r9-geo preflight (read before staging)

## The laptop

- Module **B60AB0B4** (`B60AB0B475DD1E8972419B5`, fork 2a650d74) loaded = installed: the runner
  refuses any other. It is the one-shot boot of 03:11; a reboot returns to stock Arch, which has no
  sgxfive debugfs and no `render_rgn_arrays`: run before any reboot.
- The debugfs knob `render_rgn_arrays` must exist (the module's debug option; the preflight checks
  it with reset and regs) and read 0 (`0x00000000`) at the start: nothing of an earlier session
  left. seam1's rows write 1 before each job and the runner writes 0 back after it and by its trap;
  no other debugfs write but `reset 1`.
- Tool: `~/sgxfive-test-rgn4`, sha256 e6951558a93b... (from resgx545 4623753; its `--aa4` makes
  the 4x context). The preflight checks the hash; nothing is built or staged as a tool.
- python3 3.10 or later on the laptop (the premise check imports scorekit.py).
- Free space: at least 300 MiB on ~ before each job. j1r prints 41472 pixels (about 0.5 MB of
  output); nothing else is large. Laptop files only under `~/scratch/r9g/` and
  `mktemp -d ~/scratch/tmp/r9g.XXXXXX` work directories; nothing in /tmp.

## Jobs and expected time

77 jobs: seam1 24, seam4 25, cube2 17, addr2 11, all safe class. About 4 minutes of jobs, about 20
to 25 with staging, preflight and health. No fault, hang or reset beyond the per-job reset is
expected. First in the sitting (DECISIONS-R9.md: S9-geo, S9-lgeo, r9-k1, ...).

## Stop rules

- any fault or hang (rc 4 / 6), a fatal kernel line (rc 3): the session stops
- a tri job the kernel refuses (`job: rejected`): no reading, the stage stops (rc 4)
- a control without its reading: the premise stops the session (rc 25)
- the second row of a stage without pixel rows or `job: ok`: that stage stops (rc 24)
- a knob that does not read back (19), free space (22), a latched fault before a job (14),
  registers unreadable (12), a failed reset (13), a failed health recovery (5)

## Before staging (the lead)

1. `bash tests/run_all.sh` passes and the freeze verifies (`python3 kit/session.py verify .`).
2. The module and the tool hash above, on the laptop as it is now, and `render_rgn_arrays` at 0.
3. Safety of seam1's knob: one array with `--aa4` at 128 x 96 or below is E502's ground (E828's
   one-array fault was 288 x 144 without the flag, j2); the tail room is the 4x one [infer].
