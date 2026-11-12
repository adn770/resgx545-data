# r5-render4x preflight: jobs, time, module, knobs, controls, stops, risks

Prepared 2026-11-12. Nothing ran on the laptop.

The freeze is `FROZEN.sha256` with `FROZEN.commits` and `PREDICTIONS.sha256` (`FREEZE.txt`).
`gen/rgen.py` refuses to run once frozen; a refreeze is allowed only before the first job.

## 0. Check before staging (the lead)

- The laptop is still on the rgn4 test kernel: `modinfo -F srcversion gma500_gfx` and
  `/sys/module/gma500_gfx/srcversion` both **99CD90DA26E3AFF9C450517** (`run/k.env`; the handover
  `plans/resgx545-handover-2026-11-12.md` and DECISIONS-R5 name 99CD90DA, 7.3.0-resgx545). If it
  rebooted to stock Arch: stop and ask the user (a one-shot boot of rgn4 needs their OK).
- `~/sgxfive-test-rgn4` hashes to e6951558... (`TOOL.sha256`); `run/stage_k.sh` checks it.
- No `~/r5x-*` directory exists yet from another attempt (each attempt has its own `r5x-out/ATT`).
- Order of round 5 (R5-3 a): r5-events, r5-pixel, r5-dpm, then this session last (it has faults).
- `bash tests/run_all.sh` prints `ALL TESTS: PASS`; `run/freeze_k.sh verify` passes.

## 1. Jobs and time

| stage | jobs | faults predicted (TPC-d-rgn) | limit |
|---|---|---|---|
| s0 | 3 | 0 | 1 |
| t | 9 | 0 | 1 |
| o | 11 | 0 | 1 |
| m | 5 | 1 (m3) | 4 |
| l | 5 | 2 (l4, l5) | 5 |
| x | 3 (only if m held H-TPC) | 0 | 3 |
| d | 1 held | 1 | 1 |

37 jobs, 4 predicted 3D-side faults, 10 at worst under any frozen rule. A job takes a reset (3 s),
the knob writes, the tool (it checks every pixel on the Atom: 1024x768 took 0.8 s in E828, so m4's
3.1 Mpixel about 4 s) and the gzip of its dumps (a 4.6 MB PB dump each; m4's TA data 2.2 MB). A
fault adds the kernel's recovery and the strict health pair (10 to 20 s); the held row about 5 s.
Each stage adds the begin and end health and the driver's copy and health (about 1 minute).
**About 25 minutes; plan 45.** Alarms: s0 900 s, t 600, o 1200, m 1500, l 1500, x 900, d 600;
job timeout 300 s, held 60 s.

## 2. Module, tool, knobs

- **Preflight** (`lib_k.sh`): srcversion installed = loaded = 99CD90DA26E3AFF9C450517; the debugfs
  files `reset hold_recovery regs render_param render_tadata render_pb_pages alias_skip
  render_rgn_arrays kpoke` exist (`sudo -n test -e`); hold_recovery N, render_pb_pages 0x422,
  alias_skip 0, render_rgn_arrays 0; the tool's sha256. Any failure: rc 1, nothing touched.
- **Three knobs**, each written after the row's own reset, read back numerically, put back after
  the job and at every exit (the trap writes all three):
  - `render_rgn_arrays` 1 for the TE_AA rows without `--aa4` (t6, t3, t4, t3c, t4c), else 0;
  - `render_pb_pages` 0x34 to 0xe3 for the o rows, else 0x422;
  - `hold_recovery` Y for row d only (written once, in one place), N after its held reset.
- **The only debugfs writes** are `reset 1` and those three (`tests/run_mock.sh` checks the fake
  debugfs; `run/guard_k.sh` the scripts). render_param and render_tadata are read only (row d).
  No kreg, kregnow, kicker, kpoke, no clock-gate or BIF register write, no trc_hazard, no
  firmware `str`, no /dev/mem write, no reboot, GRUB, build or module unload on the laptop.
- Kernel-log markers `resgx545 case NAME RUN` (the slice of each job) and `resgx545 r5x ...`,
  appended with `sudo -n tee -a`; every timeout with `-k`; every ssh/scp bounded (perl alarm).

## 3. Controls: how each passes and fails

| stage | control | passes | fails |
|---|---|---|---|
| s0 | the three rows | hash, diff, counts, TA data, scene pages as kept | every later gate closes (session void) |
| t | t6, t3b, t4b | t6's words and hash (E827); the baselines' heads and pixel counts (11.31) | no Q293 claim |
| o | o1, o2, o3 | complete at the need / -ENOSPC one page short (19 from 6 twins) / complete | no H-ENOSPC4 claim |
| m | m0 (and s0) | completes on a 2048 x 2048 context | m stops (rc 4), no H-TPC claim, x gated |
| m | m3 (can fail) | faults: tail room, not any larger maximum | H-TPC refuted for "more room" |
| l | s0's 1024 x 768 and row d (E845's own cell) | as kept / faults | d completing voids l and m |

A control is NODATA, never a pass, with no cases.tsv row, rc 2, 124-127 or >= 128, a class that
is not a result, a missing output or dump (a READER-MISS when a dump the row asked for is absent).

## 4. Fit vs held out

- **Fit, post hoc**: the eleven rules against the 13 kept four-array cells (13 of 13 each,
  `gen/data/rules_fit.tsv`); the header rule on 12 kept dumps (0 off); the page model U4 on
  E824's ten dumps; the 1x full model on one dump (10 pages).
- **Held out**: m1, m2, m4 (H-TPC against every size rule), l1-l5, t3c, t4c, o6-o9.
- **Replicates** (outcome known, not counted as held out): t1-t4 (E847), o4, o5 (E846).
- **Exploratory**: x1-x3 (the variant), d (the held dumps), o10, o11 (the 1x need [model] 49).

## 5. Stops and recovery

| rc | meaning |
|---|---|
| 1 | preflight; a frozen file, table or staged program that is not the frozen one |
| 3 | a fatal kernel message (no reset; the knob restore only) |
| 4 | an unexpected fault (s0, t, o, m0), hang or failure (strict health first) |
| 5 | a failed health recovery |
| 6 | a freeze (no reset; the knob restore only) |
| 7 | a forbidden knob or dbg_write |
| 8 | a staged program is missing |
| 9, 10, 11 | hold_recovery not Y / held fault latched after two resets / not N |
| 12, 13, 14 | registers unreadable / a reset failed / a fault latched before a job |
| 15 | the stage's fault limit reached with rows left |
| 16 | strict: the first health after a fault failed (recovery done) |
| 18 | a fault that is not E845's word (bits 15:0 0x0100, BIF_FAULT 0x10000011) or a -110 |
| 19 | a knob did not read back, or did not go back |

Driver: 20 frozen files changed, 30-37 health after a stage, 38 no SUMMARY, 39 the attempt's
stage directory exists, 42 a knob not at its default after a stage, 142 the alarm. **After any
stop: no reboot, no module unload, no register write. The lead decides.** A refuting outcome is
a result, not a stop.

## 6. Risks

- **s0, t, o: low.** s0 repeats round 4's controls; t is rg-pb's and 11.31's class (E847 ran it on
  this module); o's P values are one page each side of measured needs (E846: -ENOSPC at 4x).
- **m, l, x: medium, 3D side.** Each predicted fault is E845's class (BIF_INT_STAT 0x90100, page
  0x10000), health ok after 6 of 6 such faults so far; strict health stops a stage whose next
  triangle fails. m4 uses a 4096 x 4096 context (TA data 0x223000, inside the 4 MiB slot).
- **d: medium.** One held 3D-side fault; the held dump path returned error text once (o5, no
  fault). The held recovery is the kernel's own debugfs reset with the hold still Y.

## 7. Deviations

See README.md "Deviations from the plan".
