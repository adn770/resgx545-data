# r13-tex preflight (read before staging)

## The laptop

- Module **B60AB0B4** (`B60AB0B475DD1E8972419B5`, fork 2a650d74) loaded = installed: the runner
  refuses any other. It is the one-shot boot; a reboot returns to stock Arch: run before any
  reboot. No debugfs knob is written by any row (session.toml `[knobs]` is empty); the only
  debugfs write is the runner's `reset 1`.
- Tool: `~/sgxfive-test-t10`, sha256 9bedc2d6db70... (resgx545 a581c06, bound by source), named
  t10 and t10p in session.toml (one file, one hash; README.md "Deviations" 1). The preflight
  checks the hash; nothing is built or staged as a tool.
- python3 3.10 or later on the laptop (the premise check imports scorekit.py).
- Free space: at least 300 MiB on ~ before each job; a fill probe prints 2048 pixels (about
  20 KB), an sb12 row 4096. Laptop files only under `~/scratch/r13t/` and
  `mktemp -d ~/scratch/tmp/r13t.XXXXXX` work directories; nothing in /tmp.

## Jobs and expected time

53 jobs: srgb3 9, addr4 12, t3c 16, sb12 16, all safe class probes. About 5.5 minutes of jobs,
about 9 with staging, preflight and health. No fault, hang or reset beyond the per-job reset is
expected. First session of the sitting (DECISIONS-R13.md: tex, zls, dpm, isp, flag).

## Stop rules

- any fault or hang (rc 4 / 6), a fatal kernel line (rc 3): the session stops
- a control without its pixel rows: the premise stops the session (rc 25)
- the second row of a stage without its pixel rows (32, sb12 64): that stage stops (rc 24), the
  next runs
- free space (22), a latched fault before a job (14), registers unreadable (12), a failed reset
  (13), a failed health recovery (5)

## Before staging (the lead)

1. `bash tests/run_all.sh` passes and the freeze verifies (`python3 kit/session.py verify .`).
2. The module and the tool hash above, on the laptop as it is now.
3. Accept or refuse README.md "Deviations" 1: the 37 probe-fill rows are replayed by
   tests/test_libmock.py, not by the kit's replay (which the library mock cannot pass for any
   probe program); the kit fix is in FOLD-NOTES.md.
4. The reads: every rival's farthest read is inside the row's mapped scratch
   (tests/test_gen.py `test_addr_reads_inside_the_mapping`, `test_t3_b14_reads_inside_pages`);
   the largest is addr4-128x32-u4's H-MAX at page 12 + 5086 dwords of 32 pages. New on the laptop:
   smp2dreplace on an sRGB twiddled chain with T0 bit 9 (srgb3-tri), T3 bits 12:11 = 10
   (t3c-b10), bit 14 bilinear (t3c-b14bl), the u16 twiddled format with u mode 4
   (addr4-32x64-u4-h16), sideband bit 12 with colour 1 and a moved triangle [infer: none reads
   past its mapping].
