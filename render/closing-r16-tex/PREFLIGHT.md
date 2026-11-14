# r16-tex preflight (read before staging)

## The laptop

- Module **B60AB0B4** (`B60AB0B475DD1E8972419B5`, fork 2a650d74) loaded = installed: the runner
  refuses any other. It is the one-shot boot; a reboot returns to stock Arch: run before any
  reboot. No debugfs knob is written by any row (session.toml `[knobs]` is empty); the only
  debugfs write is the runner's `reset 1`.
- Tool: `~/sgxfive-test-t10`, sha256 9bedc2d6db70... (resgx545 a581c06, bound by source), the
  only tool. The preflight checks the hash; nothing is built or staged as a tool.
- python3 3.10 or later on the laptop (the premise check imports scorekit.py).
- Free space: at least 300 MiB on ~ before each job; a fill probe prints 2048 pixels (about
  20 KB). Laptop files only under `~/scratch/r16t/` and `mktemp -d ~/scratch/tmp/r16t.XXXXXX`
  work directories; nothing in /tmp.

## Jobs and expected time

15 jobs: ty only, all safe class probe fills. About 1.5 minutes of jobs, about 5 with staging,
preflight and health. No fault, hang or reset beyond the per-job reset is expected. Third session
of round 16 (DECISIONS-R16.md: zls, usse, tex, mte, tw).

## Stop rules

- any fault or hang (rc 4 / 6), a fatal kernel line (rc 3): the session stops
- the control without its pixel rows: the premise stops the session (rc 25)
- the second held-out row without its 32 pixel rows: the stage stops (rc 24); it is the only stage
- free space (22), a latched fault before a job (14), registers unreadable (12), a failed reset
  (13), a failed health recovery (5)

## Before staging (the lead)

1. `bash tests/run_all.sh` passes and the freeze verifies (`python3 kit/session.py verify .`).
2. The module and the tool hash above, on the laptop as it is now.
3. New on the laptop: types 1 and 4 at 8 x 8, 64 x 64 and 64 x 16 (E1055 ran 16 x 16 and 32 x 32,
   E567 ran 16 x 16 as "risky", no fault), mode 5 at 8 x 8 and 64 x 64 and modes 6 and 7 at 64 x 64
   (E1055: 16 x 16, no fault). Every frozen model's farthest read is dword 4031 (the type 4
   2 W stride rival at 64 x 64) of the 32 mapped pages (32768); the unmodelled mode 5 constant is
   163 at 16 x 16 (a name, not a size-scaled one so far).
4. README.md "Deviations" 1 to 6 (15 jobs; type 3 not run; W against max not parted at 64 x 16;
   H-LIN1 not selective; the added forms; one control).
