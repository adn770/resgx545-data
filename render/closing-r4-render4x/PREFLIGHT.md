# R4-G preflight: jobs, time, module, knobs, controls, stops, risks, deviations

Prepared 2026-11-11. Nothing ran on the laptop.

The freeze is `FROZEN.sha256` with `FROZEN.commits` and `PREDICTIONS.sha256` (section 9). Refreeze
(`gen/rgen.py` after removing nothing: it refuses once frozen; `run/freeze_k.sh freeze`, then
`gen/frozen_commits.py`) only before any job, never after the first.

## 1. Jobs and time

| stage | table rows | tool runs (expected) |
|---|---|---|
| s0 | 3 | 3 |
| c | 3 | 3 |
| p | 6 | 6 |
| o | 8 (o6 only if o5 faults) | 7 or 8 |
| t | 7 | 7 |
| h | 4 cells | 4 held jobs + about 11 steps |

About 42 tool runs. The time is estimated, not measured. A job takes a reset (3 s), the knob
writes, the tool and the gzip of its dumps (a 4.6 MB parameter buffer each). The tool checks every
pixel on the laptop's Atom: E828's 1x 1024x768 took 0.8 s, so 4096x960 (3.9 Mpixel) about 4 s and
the two 16.7 Mpixel jobs (o8; o7 is 4.7 Mpixel) up to a minute. Held jobs add 4 s. A fault adds the
kernel's recovery and the health pair (10 to 20 s). Each stage adds the begin and end health
(about 10 s), the driver's copy and health (about 40 s). Staging takes about 1 minute.

**Total about 15 to 20 minutes; plan 40.** The per-stage alarm of the driver is 900 s (600 for c
and t, 1500 for p, 2400 for o, 1200 for h); the job timeout is 300 s, held jobs 60 s.

## 2. Module, tool, knobs

- **The preflight** (`lib_k.sh`) checks: `modinfo -F srcversion gma500_gfx` = loaded =
  **99CD90DA26E3AFF9C450517** (`k.env`; check it against the handover
  `plans/resgx545-handover-2026-11-11.md` before staging); the debugfs files `reset
  hold_recovery regs render_param render_tadata render_pb_pages alias_skip render_rgn_arrays kpoke`
  exist (`sudo -n test -e`); the defaults hold_recovery N, render_pb_pages 0x422, alias_skip 0,
  render_rgn_arrays 0; the tool's sha256 is e6951558.... Any failure exits with rc 1 and nothing
  is touched.
- **The tool** is `~/sgxfive-test-rgn4` (built from resgx545 r3-rgn4 4623753, source
  sha256 703cbcea..., `TOOLSRC.sha256`). `--aa4` makes a context for 4x targets; `--regs` reads
  registers through /dev/mem (a read); `--dump-render` copies render_param and render_tadata.
- **Three knobs are written**, each after the row's own reset, read back numerically, and put back
  after the job and at every exit (the exit trap writes all three, a stop or a freeze included):
  - `render_rgn_arrays` 1 (rows `rgn:1`: the t6/t3/t4 poke rows and the h cells), else 0;
  - `render_pb_pages` 0x23 to 0x422 (rows `pb:0xNN`: o1 to o6), else 0x422;
  - `hold_recovery` Y (held rows only: o5, o6, the h cells; written once, in one place), then N
    after the held reset, read back.
- **The debugfs writes of the whole session** are `reset 1` and those three: `tests/run_mock.sh`
  checks it against the fake debugfs, and `run/guard_k.sh` against the scripts. render_param and
  render_tadata are read (a held job's dump in o5/o6). No kreg, kregnow, kicker, kpoke, no
  clock-gate or BIF register write, no trc_hazard, no /dev/mem write, no reboot, GRUB, build or
  module unload on the laptop.
- **The knob's rule in the mock**: the fork refuses TE_AA bits 31:30 on a context made without
  `--aa4` unless render_rgn_arrays forces a count: every row with such a word and no `--aa4`
  carries `rgn:1` (the mock refuses it without; `tests/mock_all.py` proves it for the t6, t3, t4
  and h rows).
- **The driver** reads alias_skip, render_rgn_arrays and render_pb_pages after each stage and stops
  with rc 42 if one is not at its default.
- **The kernel-log markers** are `resgx545 case NAME RUN` (a job or a step: the slice of each is
  taken after its own marker, never by line count) and `resgx545 r4g ...` (knob writes,
  read-backs, registers, classes), appended with `tee -a`.

## 3. Controls: how each passes and fails

| stage | control | passes | fails |
|---|---|---|---|
| s0 | the three rows | every frozen quantity (hash, diff, counts, TA data, pages) | gate of every later stage closes |
| c | cu-xn | face 1 on 2048 of 2048 and E726's pixels byte for byte | no Q113 claim |
| p | s0's controls | (the gate) | no claim |
| o | o1, o2, o3 | complete / -ENOSPC without a fault / complete | Q292 cannot tell |
| t | t6, t3b, t4b | t6's words and hash; the baselines' heads and pixel counts | no Q293 claim |
| h | the job of each cell | faults at the frozen word | the cell cannot tell |

A control is NODATA, never a pass, when it has no cases.tsv row, its rc is 2, 124-127 or 128 or
more, its class is not a result, its output or a needed dump is missing, or a value is missing.
h2 carries the control that can fail for H-REPLAY: a health fault at 0x20006 (the health
context's own end) after a job at 0x2000a refutes the replay.

## 4. Fit vs held out

- **Fit (post hoc, E824's ten kept dumps)**: the page model U4 and the TA-data layout formula
  (10 of 10), the face rule on E726's eight jobs (2048 of 2048 each), the insertion before the
  format word on E728's pairs. `tests/test_gen.py` checks each.
- **Held out**: p's six sizes (four are five times larger than the largest fitted), o4 o5 o7 o8,
  the two held-out cube programs, the line and point insertion and the four-array rows, h2's page
  0x2000a as a health fault.
- **Exploratory, no prediction**: o6's either/or, the number of replays, any -110 beyond the
  shape check.
- Predicted values come from the kept records; where none has the value (sizes never run) the
  `model` column says so and the claim is [infer].

## 5. Decision rules

Frozen in `score/score_r.py` (the header gives the hypotheses). The rules are scorekit's: a
control that is not PASS gates every dependent row; replicates that disagree are mixed; the
headline states how many rows decided. `score_r.py verdict ROOT` prints one SUMMARY line each for
the session, Q113, H-PB, Q292, H-SPM4, Q293 and Q140.

## 6. Stops and recovery

Runner exit codes (`run_stage.sh` header):

| rc | meaning |
|---|---|
| 1 | preflight; a frozen file, table or staged program that is not the frozen one |
| 3 | a fatal kernel message (no reset; the knob restore only) |
| 4 | an unexpected fault, hang or failure (a reset and the health check first) |
| 5 | a failed health recovery |
| 6 | a freeze (no reset; the knob restore only) |
| 7 | a forbidden knob or dbg_write (also a pb value outside 0x23 to 0x422) |
| 8 | a staged program is missing |
| 9, 10, 11 | hold_recovery did not read back Y / a held fault still latched after two resets / did not read back N |
| 12, 13, 14 | registers unreadable / a reset failed / a fault latched before a job |
| 15 | the stage's fault-class event limit (p 2, o 5, h 5, others 1) |
| 16 | strict: the first health after a 3D-side fault failed (recovery done, stage stops) |
| 17 | a cell's fourth health triangle failed (every knob restored, no further reset) |
| 19 | a knob did not read back, or did not go back |

Driver exit codes (`k.sh`): 20 frozen files changed, 30-37 health after a stage, 38 no SUMMARY,
39 the attempt's stage directory exists, 42 a knob is not at its default after a stage, 142 the
alarm. **After any stop: no reboot, no module unload, no register write. The lead decides.** A
stop of the whole session after a held fault that does not clear (rc 10) leaves the GPU as it is.

A wrong image or a refuting outcome is a result, not a stop.

## 7. Risks

- **s0, c, t: low.** s0 repeats E827/E828/E824 jobs; c's probes are E726's class; t is rg-pb's
  class (E728: 9 of 9 empty images, no fault).
- **p: low to medium.** Four sizes use 961 of 1024 pages (63 spare). A fault or overflow there
  refutes H-PB and is recorded; two such events end the stage. The 4096-wide and 4096-high jobs
  have the largest targets and dumps (the PB dump is 4.6 MB each).
- **o: medium, 3D side.** o4, o5, o7 are predicted to fault like E828 j4 (BIF_INT_STAT 0x90100,
  health ok 3 of 3 after j4); o5 and o6 run held at a 0x23-page PB. K2's j4 left a TA-side clock
  state (0x78) that a completed render clears. The strict health stops the stage if a 3D-side
  fault leaves the next triangle failing. o8 is a 16.7 Mpixel job at 1x (j4's size).
- **h: medium to high, TA write faults, last.** Each cell is a held c1-shaped fault followed by
  up to four failing health triangles; K2 saw two replays, the rgn4 boot one; E507's run stopped
  with four failing. A fourth failure ends the session with the knobs restored and no reset.
  h3's follow-up is a 64x64 triangle on a 1024x768 context: its stray write (if the replay is real)
  lands in a mapped page of that context's DPM state; no other context is touched.
- **Nothing else is written.** No clock-gate register, trc_hazard, kreg, kregnow, kicker, BIF
  register, /dev/mem write, boot-loader file or kernel.

## 8. Deviations from the plan and the brief

1. **Stage c (Q113's held-out cube row)** is added after s0 (decision R4-3): the tool can run it
   (`probe --temps 32 --coords --pixels PROGRAM`, accepted by the mock; the programs are built
   offline with p1141's builder and verified against the published ones). Three jobs, not two:
   E726's cu-xn is the control.
2. **t5 dropped, t4b added**: the kept pb-n40 dumps (E825, E829) already show one inserted dword
   per object (dwords 11 and 38); the line and point rows need an in-session baseline each (t3b,
   t4b) because the kept baselines come from the 11.31 session on another module and tool.
3. **`--pixels` on o5/o6** is kept as the plan has it (it prints pixels only when a render fails
   without pokes; harmless); `--regs 0x0700-0x072c` is on the plain 4x rows only (a failed or held
   job prints none: the held rows read 0x0724 from the debugfs snapshot).
4. **o8's command** is the plain 1x full triangle at 4096x4096 (default TE_AA): j4's 4x words
   would be refused on a 1x context.
5. **The tool's `mock_all.py` tool** is the Mac build of 4623753 in `debug/tool4623753` made by
   `tests/build_mock_tool.sh` (the original `closing3/kernel/wt-rgn4` build no longer exists).
6. **Freeze pins**: by absolute path, from resgx545: `tools/closing/scorekit.py`,
   `tools/bringup/health.sh`, `tools/usse-asm/probe.py`, `probes/ta/p1131-progs.toml`, its
   templates and the untracked assembler build; from resgx545-data: the kept records the values
   came from (`gen/data/sources.lst`). `FROZEN.commits` pins the resgx545 commit 5a13042 (the
   files are unchanged there).
7. **A bounded wait for the log tee** as in R4-A (`TEE_GRACE`).

## 9. Freeze (2026-11-11, before any job)

See `FREEZE.txt` (written by the build: the hashes of `FROZEN.sha256`, `PREDICTIONS.sha256` and
`FROZEN.commits`).
