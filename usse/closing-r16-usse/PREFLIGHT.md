# r16-usse preflight (read before staging)

## The laptop

- Module **B60AB0B4** (`B60AB0B475DD1E8972419B5`, fork 2a650d74) loaded = installed: the runner
  refuses any other. It is the one-shot boot; a reboot returns to stock Arch: run before any
  reboot. No debugfs knob is written by any row (session.toml `[knobs]` is empty); the only
  debugfs write is the runner's `reset 1`.
- Tool: `~/sgxfive-test-t10`, sha256 9bedc2d6db70... (resgx545 a581c06, bound by source), the
  only tool. The preflight checks the hash; nothing is built or staged as a tool.
- python3 3.10 or later on the laptop (the premise check imports scorekit.py).
- Free space: at least 300 MiB on ~ before each job; a probe prints at most 13 lines. Laptop
  files only under `~/scratch/r16u/` and `mktemp -d ~/scratch/tmp/r16u.XXXXXX` work directories;
  nothing in /tmp.

## Jobs and expected time

30 jobs: uadd 7, utest 20, urpt 3, all safe class probe fills of programs of ours (30 bins, 29 to
250 words). About 4 minutes of jobs, about 8 with staging, preflight and health. No fault, hang
or reset beyond the per-job reset is expected. Second session of the sitting (DECISIONS-R16.md:
zls, usse, tex, mte, tw).

## Stop rules

- any fault or hang (rc 4 / 6), a fatal kernel line (rc 3): the session stops
- a control without its scratch dwords: the premise stops the session (rc 25)
- the second row of a stage without its o0 line or scratch dwords: that stage stops (rc 24);
  after uadd or utest the next stage runs, after urpt (the last, `on_stop = "end"`) the session
  ends
- free space (22), a latched fault before a job (14), registers unreadable (12), a failed reset
  (13), a failed health recovery (5)

## Before staging (the lead)

1. `bash tests/run_all.sh` passes and the freeze verifies (`python3 kit/session.py verify .`).
2. The module and the tool hash above, on the laptop as it is now.
3. New on the laptop, each placed so a fault loses the least: class 9 test words with the o join
   on shl, shr, asr, rol, iadd32, iaddu32 and on the lane operations with chan fields 1 to 7
   (E529 ran the o join on and, or, xor; E530 the chan fields on a 32-bit and; 1152 raw test
   words, no fault), raw two-bit fields on the shifts and sums (E499 ran them on and, or, xor,
   rol); iaddu32 into i0 and sa0 (E496 ran ima32 into both in fills); and, as the session's last
   stage (urpt), **the write mask .xy / .xyzw on a class 9 test** (enc[47:44] of a test word, never
   run; the write masks of mov, the bitwise group and frcp ran): accept as safe class or cut urpt
   (then Q126's repeat clause stays open, R16-6).
4. README.md "Deviations" 1 to 6 (30 jobs with both joins a form and field 0 in every program;
   the repeats a stage of their own; no g destination; the packed readout; or #7 without a zero
   result; the added rivals).
