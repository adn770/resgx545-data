# r14-tex preflight (read before staging)

## The laptop

- Module **B60AB0B4** (`B60AB0B475DD1E8972419B5`, fork 2a650d74) loaded = installed: the runner
  refuses any other. It is the one-shot boot; a reboot returns to stock Arch: run before any
  reboot. No debugfs knob is written by any row (session.toml `[knobs]` is empty); the only
  debugfs write is the runner's `reset 1`.
- Tool: `~/sgxfive-test-t10`, sha256 9bedc2d6db70... (resgx545 a581c06, bound by source), the
  only tool. The preflight checks the hash; nothing is built or staged as a tool.
- python3 3.10 or later on the laptop (the premise check imports scorekit.py).
- Free space: at least 300 MiB on ~ before each job; a fill probe prints 2048 pixels (about
  20 KB). Laptop files only under `~/scratch/r14t/` and `mktemp -d ~/scratch/tmp/r14t.XXXXXX`
  work directories; nothing in /tmp.

## Jobs and expected time

27 jobs: srgb4 13, addr5 14, all safe class probe fills. About 3 minutes of jobs, about 7 with
staging, preflight and health. No fault, hang or reset beyond the per-job reset is expected.
First session of the sitting (DECISIONS-R14.md: tex, zls, dpm, isp, bif, flag).

## Stop rules

- any fault or hang (rc 4 / 6), a fatal kernel line (rc 3): the session stops
- a control without its pixel rows: the premise stops the session (rc 25)
- the second row of a stage without its 32 pixel rows: that stage stops (rc 24), the next runs
- free space (22), a latched fault before a job (14), registers unreadable (12), a failed reset
  (13), a failed health recovery (5)

## Before staging (the lead)

1. `bash tests/run_all.sh` passes and the freeze verifies (`python3 kit/session.py verify .`).
2. The module and the tool hash above, on the laptop as it is now.
3. New on the laptop, each placed so a fault loses the least: texture types 1 and 4 with u mode 4
   (addr5-ty1-u4, addr5-ty4-u4; E567 ran their mode 0 programs in its "risky" group with no
   fault and the health exact, README.md "Deviations" 4: accept them as safe class or cut the
   type rows); a 256-wide twiddled texture (addr5-256x32-uv5, the stage's last row); 128 x 128
   at page 12 (addr5-128x128-uv5: the farthest frozen read is page 12 + 17428 dwords of 32
   pages); the r11 template on bilinear sRGB (srgb4-b2x1, -ax, -ay, -axy) and smp2dreplace on an
   injected 4 x 4 sRGB chain (srgb4-tdark).
4. README.md "Deviations" 1 to 5 (TRI-G15 frozen beside the plan's TRI-RNTU; the third flush as
   two forms; the alpha forms' premise from E723's r11 jobs; the type references are E567's jobs
   and T-OFFSET is scored on them; the 256 x 32 row last).
