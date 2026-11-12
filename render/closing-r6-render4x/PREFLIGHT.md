# r6-render4x stage A preflight: jobs, time, module, knobs, files, controls, stops, risks

Prepared 2026-11-12. Nothing ran on the laptop.

The freeze is `FROZEN.sha256` with `FROZEN.commits` and `PREDICTIONS.sha256` (`FREEZE.txt`),
against resgx545 main d9b2969. `gen/rgen.py` refuses to run once frozen and `run/freeze_k.sh`
refuses to rewrite a set's freeze; a refreeze before the first job means removing the two hash
files by hand.

## 0. Check before staging (the lead)

- The laptop is still on the rgn4 test kernel: `modinfo -F srcversion gma500_gfx` and
  `/sys/module/gma500_gfx/srcversion` both **99CD90DA26E3AFF9C450517** (`run/k.env`; handover
  `plans/resgx545-handover-2026-11-12-r5.md`: "still on 7.3.0-resgx545 (rgn4, 99CD90DA)"). If it
  rebooted to stock Arch: stop and ask the user. Stage A must run before the R6-3 reboot.
- `~/sgxfive-test-rgn4` hashes to e6951558... (`TOOL.sha256`); `run/stage_k.sh` checks it.
- Order of round 6 (R6-2 a): r6-pixel, r6-dpm, r6-misc, then this session last (it has faults).
- **Laptop /tmp**: the handover says /tmp still holds r5-render4x's work directories (that runner's
  bare `mktemp -d`; this one never uses /tmp). They are the lead's to clear (`/tmp/tmp.*`); this
  runner needs only 300 MiB free on ~ (`df -h ~`). No `~/scratch/r6x` from another attempt matters:
  each attempt has its own `~/scratch/r6x/out/ATT`.
- `bash tests/run_all.sh` prints `ALL TESTS: PASS`; `run/freeze_k.sh verify` passes.

## 1. Jobs and time

| stage | jobs | faults predicted (H-TPM) | limit | alarm |
|---|---|---|---|---|
| s0 | 3 | 0 | 1 | 900 s |
| a | 13 (12 if a1 faults: a1r skipped) | 6 (a2, a3, a5, a14, h1, h2) | 8 | 2400 s |
| t | 4 | 0 | 1 | 600 s |

20 jobs, 6 predicted 3D-side faults (E845's class, health ok after 8 of 8 in r5). Under any dead
size rule (K-OR) stage a would take its 8th fault at a5 and stop with rc 15. A job: a reset (3 s),
the knob writes, the tool (pixel check on the Atom: 1024 x 1536 about 2 s), the gzip of its dumps
(a 4.6 MB PB dump each). A fault adds the recovery and the strict health pair (10 to 20 s); a held
row about 5 s. **About 15 minutes; plan 30.** Job timeout 300 s, held 60 s.

## 2. Module, tool, knobs, files

- **Preflight** (`lib_k.sh`): srcversion installed = loaded = 99CD90DA26E3AFF9C450517; the debugfs
  files `reset hold_recovery regs render_param render_tadata render_pb_pages alias_skip
  render_rgn_arrays kpoke` exist (`sudo -n test -e`); hold_recovery N, render_pb_pages 0x422,
  alias_skip 0, render_rgn_arrays 0; the tool's sha256; at least 300 MiB free on ~. Any failure:
  rc 1 (rc 21 for the space), nothing touched.
- **Knobs**, each written after the row's own reset, read back numerically, put back after the job
  and at every exit: `render_rgn_arrays` 1 for t5-t8 (TE_AA bits 31:30 without --aa4), else 0;
  `render_pb_pages` 0x422 always (no PB row in stage A); `hold_recovery` Y for h1 and h2 only (one
  place), N after the held reset.
- **The only debugfs writes** are `reset 1` and those three. render_param and render_tadata are
  read in the hold (h1, h2); kpoke is read after every job and kept (t7's `--kpoke-render 2:par:11`
  is armed by the tool itself; the next reset disarms anything left). No kreg, kregnow, kicker, no
  kpoke write of the runner's, no clock-gate or BIF register write, no trc_hazard, no firmware
  `str`, no /dev/mem write, no reboot, GRUB, build or module unload.
- **Files**: `~/scratch/r6x/run` (runner, tables, freeze), `~/scratch/r6x/stage` (two programs),
  `~/scratch/r6x/out/ATT/STAGE` (kept); work in `mktemp -d ~/scratch/tmp/r6x.XXXXXX`, each job's
  directory removed once kept, the whole one at every exit. Nothing in /tmp.
- Kernel-log markers `resgx545 case NAME RUN` and `resgx545 r6x ...` appended with
  `sudo -n tee -a`; every timeout with `-k`; every ssh/scp bounded (perl alarm).

## 3. Controls: how each passes and fails

| stage | control | passes | fails |
|---|---|---|---|
| s0 | the three rows | hash, diff, counts, TA data, scene pages as kept (r5: PASS) | every later gate closes (session void) |
| a | a4 (premise) | 1024 x 768 on 2048 x 1024 completes (entries end = `td.rgn` 0x7000) | stage a stops (rc 4); no H-TPM claim |
| a | a2, a14 (neighbours) | fault | if they complete the boot differs from r5's: the claim fails |
| t | t8 | E827's hash, words and counts (r5's t6 PASS) | no Q293 claim |

A control is NODATA, never a pass, with no cases.tsv row, rc 2, 124-127 or >= 128, a class that
is not a result, a missing output or dump (a READER-MISS when a dump the row asked for is absent).

## 4. Fit vs held out

- **Fit, post hoc** (E870): H-TPM's interleave and limit from E869's one dump; 26 of 26 recorded
  outcomes (an offline check on seen data; `gen/data/recorded_cells.tsv`).
- **Held out**: a1, a12, a13, a8, a9 (H-TPM complete, K-OR fault), a2, a3, a5, a14 (fault), h1, h2
  (the lost sets, frozen to the offset), t5, t6 (0xc0000000 never ran on a line or a point), t7.
- **Replicate**: a1r (only after a1 completes).
- **Exploratory**: word 0 / bit 27 / flags of the held dumps, h1 against a9, right pixels before a
  fault (plan 1.4: a3 and h2 lose offsets only from a later header on).

## 5. Stops and recovery

| rc | meaning |
|---|---|
| 1 | preflight; a frozen file, table or staged program that is not the frozen one |
| 3 | a fatal kernel message (no reset; the knob restore only) |
| 4 | an unexpected fault (s0, t, a4), hang or failure (strict health first) |
| 5 | a failed health recovery |
| 6 | a freeze (no reset; the knob restore only) |
| 7 | a forbidden knob or dbg_write |
| 8 | a staged program is missing |
| 9, 10, 11 | hold_recovery not Y / held fault latched after two resets / not N |
| 12, 13, 14 | registers unreadable / a reset failed / a fault latched before a job |
| 15 | stage a's 8th fault-class event with rows left |
| 16 | strict: the first health after a fault failed (recovery done) |
| 18 | a fault that is not E845's word (bits 15:0 0x0100, BIF_FAULT 0x10000011) or a -110 |
| 19 | a knob did not read back, or did not go back |
| 21 | less than 300 MiB free on ~ (preflight or before a job) |

Driver: 20 frozen files changed, 30-37 health after a stage, 38 no SUMMARY, 39 the attempt's
stage directory exists, 42 a knob not at its default after a stage, 142 the alarm. **After any
stop: no reboot, no module unload, no register write. The lead decides.** A refuting outcome
(a1 faulting, a set off) is a result, not a stop.

## 6. Risks

- **s0, t: low.** s0 repeats r5's passing controls; t5, t6 are r5's t3c/t4c with bit 30 also set
  (rgn:1, the 11.31 programs); t7 is E829's shape with another value at dword 11 (0xffffffff drew
  nothing and did not fault, 2 of 2).
- **a: medium, 3D side.** Six predicted faults of the class r5 took 8 of with health ok after
  every one; strict health stops the stage if a triangle fails afterwards. Two held faults (r5's d
  held cleanly). The largest context is 1040 x 1280 / 1024 x 1536 (TA data well inside 4 MiB).

## 7. Deviations

See README.md "Deviations from the plan".
