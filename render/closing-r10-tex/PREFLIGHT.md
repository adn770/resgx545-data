# r10-tex preflight (read before staging)

## The laptop

- Module **B60AB0B4** (`B60AB0B475DD1E8972419B5`, fork 2a650d74) loaded = installed: the runner
  refuses any other. It is the one-shot boot of 03:11; a reboot returns to stock Arch: run before
  any reboot. No debugfs knob is written by any row (session.toml `[knobs]` is empty); the only
  debugfs write is the runner's `reset 1`.
- Tool: `~/sgxfive-test-rgn4`, sha256 e6951558a93b... (resgx545 4623753, bound by source). The
  preflight checks the hash; nothing is built or staged as a tool.
- python3 3.10 or later on the laptop (the premise check imports scorekit.py).
- Free space: at least 300 MiB on ~ before each job; each probe prints 2048 pixels (about 20 KB).
  Laptop files only under `~/scratch/r10t/` and `mktemp -d ~/scratch/tmp/r10t.XXXXXX` work
  directories; nothing in /tmp.

## Jobs and expected time

48 jobs: addr3 11, cube3 16, t3b 15, srgb2 6, all safe class probes. About 4 minutes of jobs,
about 13 to 20 with staging, preflight and health. No fault, hang or reset beyond the per-job
reset is expected. First session of the sitting (seeds plan R10-10 (a): S10-tex, S10-geo,
S10-dpm, S10-zls).

## Stop rules

- any fault or hang (rc 4 / 6), a fatal kernel line (rc 3): the session stops
- a control without its 32 pixel rows: the premise stops the session (rc 25)
- the second row of a stage without its 32 pixel rows: that stage stops (rc 24), the next runs
- free space (22), a latched fault before a job (14), registers unreadable (12), a failed reset
  (13), a failed health recovery (5)

## Before staging (the lead)

1. `bash tests/run_all.sh` passes and the freeze verifies (`python3 kit/session.py verify .`).
2. The module and the tool hash above, on the laptop as it is now.
3. The reads: every rival's farthest read is inside the row's mapped scratch (tests/test_gen.py
   `test_addr3_reads_fit_the_mapping`, `test_t3b_reads_fit_the_mapping`, gen/t3.py's 16-bit
   extent); the largest is t3b-s256's H-U01 at 18063 dwords of 19 pages. The 16-bit row (T1
   format 9 on a strided texture) is the only format no earlier session ran strided [infer: a
   format read changes no address beyond the texel size].
