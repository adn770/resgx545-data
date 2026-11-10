# R2-geo preflight: jobs, time, controls, the T5 decision, the C2 poke, risks, changes

Prepared 2026-11-10 from `closing2/geometry/exp-geometry-round2.md`, `closing2/exp-events.md`
section 3, R1-events and R1-pixgeo (its `out/score-*.txt` results) and the decisions R2-5, R2-12,
R2-14, R2-15, R2-17.  Nothing ran on the laptop.  Frozen: `FROZEN.sha256` (every generator,
scorer, runner script, table, prediction, staged program, template, `TOOL.sha256`,
`TOOLSRC.sha256` and the read-only imports pbdump.py, probe.py, counters.py and the landed
templates the generators read), `PREDICTIONS.sha256`. Refreeze (`run/freeze_r2.sh freeze`) only if
the tables are regenerated, never after the first job.

## 1. Jobs and time

| stage | jobs | what |
|---|---|---|
| g-t3 | 4 | 1/w of clip-made vertices: control z-cut-p, w = 0.5x + 1.25, w = -0.5x + 1.25, no-cut |
| g-t4 | 8 | depth at w != 1: 2 controls and 6 (Z, W) pairs |
| g-t5v | 13 | Q082 T5: no-loop control, 1 and 3 iterations, then 28 .. 7040 (stops at bit 7) |
| g-c3 | 11 | C3: 2 controls at 4096x4096, a calibration, 4 proposal cells and 4 low cells at 2048x2048 |
| g-c2 | 9 | C2: 2 E625 controls and 7 pokes of pb:11, P = 0x422, LAST |
| **total** | **45** | plus `g-c3f` (8 fallback cells, a table) |

Time (R1's per-job times: about 5 s a plain job, 10 to 15 s a 4096 job with 4.6 MB PB dumps, a
reset and a health triangle between stages): g-t3 20 s, g-t4 40 s, g-t5v 80 s, g-c3 110 s, g-c2
130 s, stage start, health and copies 5 x 25 s: **about 9 minutes of jobs**, plan 15.  Staging is
a copy (no build): about 1 minute.  The tool and regtimeline are R1's; the kernel must be
linux-resgx545 (the debugfs `kpoke` file must exist for g-c2: the preflight checks it).

## 2. What is frozen (row, hypothesis, prediction, label; full list in TABLES.md)

- **g-t3** (T3).  Control z-cut-p (w = 1): the S1/S1b object (4 vertices, order, prims, depth
  words), `control`.  Held out: t3-w-pos (z = 2x + 1, w = 0.5x + 1.25: cut at x = 1/6, made w =
  4/3) and t3-w-neg (w = -0.5x + 1.25: cut at x = 0.1, w = 1.2): vertex set and order (SH in (x,
  y, z, w), zigzag), prims, window = 32 + 32 x/w, the made vertices' depth exactly 1.0, and the
  1/w words by position under two hypotheses, HI-w (made 1/w = RZ of 1/w_made: 0x3f400000, 0.75)
  and HI-rhw (the ends' 1/w interpolated: 0.8205 / 0.7847), each exact and within one ulp (S1b saw
  0x3f800001 on one made vertex). t3-nocut (z = 0, no clip): positions x/w, RZ 1/w words, depth
  0.5, `heldout`.
- **g-t4** (T4).  Controls: Z = 0, W = 3 (0x3f000000, E754) and Z = -0.5, W = 1 (0x3e800000,
  cut-p's A). Six held-out pairs (-2.1, 3), (-2.6, 3), (-5.3, 7), (-0.0027, 0.003), (-0.83, 1.1),
  (-6.1, 7): the depth word of six candidates D1 RN(Z RZ(1/W)), D2 RZ(Z/W), D3 RN(Z/W), D5 RZ(Z
  RZ(1/W)), D6 RN(RN(Z+W)/2W), D7 RN(Z RN(1/W)) (3 to 4 distinct words a pair, the six pairs
  separate every pair of candidates), the RZ / RN 1/w word, default positions.  Verdict: the
  candidate right in 6 of 6; none = words recorded.
- **g-t5v** (T5).  Every vertex's stored depth word = 0x3f200000 + N (the loop count carried into
  z): HLOOP, `control` on ctl0 / n1 / n3, `heldout` on the ladder; STATUS2 0x400 after the reset
  (all rows); bit 7: H-ITER / H-INSTR clear to 53, set from 55 (E769's pixel latch: clear at 53,
  set at 55); H-TIME monotone, point not frozen; H-NEVER none.
- **g-c3** (C3).  R1's C = 0x371 (raise at P = 0x373, none at 0x374; P* = 0x374).  Controls at
  4096x4096: P = 0x372 raise, 0x374 none (R1, `control`).  At 2048x2048: H-same (raise iff P - 2
  <= 0x371): 0x354 raise, 0x372 raise, 0x374 none, 0x394 none, the low cells (P = 0x162, 0x122,
  0xe2, 0xa2) raise; H-target: the (0x372, 0x374) pair on one side, a flip along the
  ladder.  The calibration job at P = 0x422 is `heldout` "no overflow".  Verdict text: flip and C
  range, bound only, or NODATA.
- **g-c2** (C2).  Controls (E625): poke 0x80 raise, 0x100 none.  Held out at 1500 vertices: V =
  0x300, 0x33e, 0x351 raise and 0x352, 0x35e, 0x3a0, 0x3de none under H-abs (the limit compares
  the threshold the TA runs: raise iff V + 0x20 <= 0x371); H-P (limit on the knob's P = 0x373):
  none everywhere; H-rel (the proposal's: raise at every V).  The first abort's status = V is the
  knob proof.

## 3. Controls: how each passes and fails

| stage | control | passes | fails (scorer) |
|---|---|---|---|
| g-t3 | z-cut-p | S1/S1b's object (set, order, prims, depth words) | cannot tell |
| g-t4 | t4-ctl-z0-w3, t4-ctl-zm05-w1 | depth 0x3f000000, 0x3e800000 | cannot tell |
| g-t5v | ctl0, n1, n3 | depth word 0x3f200000 + N on all 3 vertices, STATUS2 0x400 after the reset, bit 7 clear | cannot tell; n3 alone failing = "the backward branch did not loop": no ladder row is a reading |
| g-c3 | c3-4096-0x372 / 0x374 | raise, none (R1), second run reaching thr0 | cannot tell |
| g-c2 | k-tri-0x80 / 0x100 | raise, none (E625), first abort status = V | cannot tell |

Knob proofs read the job's own data, never a first sample: DPM rows the 0x0624 rows after the
job's start and the first partial-render status (`knob_value`, `runs`); T5 the stored depth words
and the STATUS2 files read after THIS job's reset and after THIS job; C2 the first partial
render's status equal to V (a poke that did not land is NODATA, not a miss).  Every tri row carries
`expectdiff`; a multi-render tri row needs `--keep-going` (the runner refuses both omissions).

## 4. T5 (Q082): kept, with this evidence

The R1-events preflight said a vertex loop "cannot be built soundly yet": the shader sits at an
offset from its code base, only the `phas` is patched, an absolute `ba` misses and `br`'s base is
not established.  Settled offline:

1. **Placement.** `sgxfive_tri_probe.h`: the vtxuse program is at `UV_VTX` = 0x200 bytes into its
   page, instruction 0x40 from the page start, and the host adds that index only to the first
   `phas`.  E476 (hardware): absolute indices count from a code base that is the placement rounded
   down to 512 KiB; a jump counted from the program start faults or hangs.  So `ba #label` lands
   in other code.  This also explains E770 (R1-events' loops used `ba`; the pixel program sits at
   0x100 bytes = instruction 0x20): sgx-sim stops the same `ba` loop at code index 0x40 ("a ba to
   an index before the program in its code base") and runs it at index 0.
2. **`br` is relative.** E075 (hardware, 5 forward offsets): `br #1` is the next instruction,
   offsets count from the branch itself.  The assembler takes `br -#N` (18-bit two's complement,
   ISA table), the sim runs it.  `templates/vtx_loop.s`: 8 instructions an iteration (as E769's
   body 8), `p1 br -#7`.
3. **Run in sgx-sim** (`tests/test_t5loop.py`, a scratch harness over `crates/sgx-sim` setting
   `Machine::code_index`): the 12 staged bins give z = 0.25 + 4N ulp, steps 14 + 8N, at code
   indices 0, 0x40, 0x41, 0x1040, 0x10040: placement independent.  The landed `sgx-sim` command
   line agrees.
4. **Knob proof that would have caught E770 for vertices.** The loop count goes into z (0.25 + 4N
   ulp), so the stored depth 0.5 + 0.5 z is exactly 0x3f200000 + N (checked for N to 100000): a
   vertex that did not run N iterations, or a branch that fell through (N = 1), shows in the dump;
   the scorer flags `LOOP FAILED` and voids that length for the latch.  The ladder's first loop is
   n3.
5. **What is NOT established offline: a backward `br` on the hardware** (every `br` in the data
   repo is a forward offset; E476's backward jumps are `lapc`).  The design isolates it: ctl0 and
   n1 run no backward branch; n3 is the first, before any long loop; n3 failing is a stated
   outcome (cannot tell, no ladder row read).  If the branch faults or hangs the stage stops at n3
   (rc 4) with a reset. The lead may DROP T5 at the user's word; it is the last of the three
   vertex stages and independent.

The sweep: lengths 28, 53, 55, 110, 220, 440, 880, 1760, 3520, 7040 iterations (224 to 56320
instructions a vertex).  `sweep:t5v`: after each job the runner reads STATUS2 (0x0118) from the
debugfs regs; the first with bit 7 (0x80) set ends the sweep, the rest are recorded as `skipped`.

## 5. C2 (the pb:11 poke): design, last in its session

- **Spec** (linux fork branch resgx545, `sgxfive_kpoke.h`, read-only): `pb:N=V` sets word N of the
  render context's PB descriptor, applied ONCE to the next render the kernel kicks (after it wrote
  its own words), then dropped; a boot, firmware reload or recovery reset clears whatever is
  armed.  The tool writes it (`--kpoke pb:11=0x...` for probe rows, `--kpoke-render 1:pb:11=0x...`
  for the E625 tri rows, `SGXFIVE_KPOKE` overrides the path only in tests).  `--mock` accepts both
  spellings and writes the line to the override file (tests/mock_all.py).
- **Only pb:11.**  `rcommon.write_table` (generator), `run_stage.sh` (before anything runs) and
  `guard_r2.sh` (static) refuse any `--kpoke*` value that is not exactly `pb:11=0xHEX`, any poke
  outside g-c2, any poke row without the knobs `kpoke` and `wd:S`, and any script line writing the
  debugfs `kpoke` (the scripts never write it; the tool does).  No `^=` form, no second poke.
- **A stuck job ends with the kernel's own debugfs reset.**  Every poke row has `wd:75`: a
  background subshell writes `1` to the debugfs `reset` (through `sudo -n`) 75 s after the tool
  started, if the tool is still running; it is killed when the tool returns first.  A
  watchdog-fired job is class `hang`: the stage stops (rc 4) after a reset and a health triangle.
  The tool's own timeout is wd + 40 s; a tool that still does not return (rc 124) gets the
  kernel's reset and a health triangle first, then the stage stops (rc 6).  Before every job the
  runner resets (clearing any armed poke), and the exit trap resets again, so no poke survives the
  stage.  The kernel also recovers a hung job by itself (E118, E630: "job hung, context lost");
  the watchdog is the second line.
- **Order and values.**  Controls first (E625's two); the poke ladder ascends; P = 0x422
  throughout. Risk class "risky" as E625's script; E625 ran 5 pokes without incident.

## 6. Changes from the proposal, and why

1. **C3 cells may not reach (the main change).**  `--vertices` is capped at 1500 by the tool (no
   rebuild allowed) and the scene's page need scales with the target's area: about 1300 pages at
   4096x4096 (E704: first abort at 0x400, then 0x400, 0x11c), so at 2048x2048 about a quarter,
   below thr0 = 0x352 at P*: the proposal's four cells (and its 2048x1536 fallback, smaller still)
   likely complete in one render with no first abort: NODATA.  Added: a calibration job (P = 0x422)
   that measures the need, and a low ladder (raised thresholds 0xa0 .. 0x160, run from the highest down, none below thr0 0x80
   because E630's wide scene hung in 0x40 pages) that can show a
   LOWER limit at 2048 if the second run can reach it (it cannot test a higher or equal C: bound
   only, reported as such).  The 2048x1536 fallback stays as `g-c3f` with 4096x3072 (three
   quarters of the 4096 area, closer to a scene that reaches).  `--mock` accepts 2048x2048,
   2048x1536 and 4096x3072.
2. **C recomputed from R1.**  C = 0x371 exactly (raise at P = 0x373, none at 0x374), so P* = 0x374
   and C3's cells are 0x354, 0x372, 0x374, 0x394; C2 gets the bracketing pair V = 0x351 / 0x352.
3. **C2 hypotheses restated.**  With the knob ladder known, "H-rel" (limit follows P) is already
   hard to reconcile with R1's flip, so the poke ladder separates H-abs (limit on the threshold
   the TA runs) from H-P (limit on the knob, 0x373: no poke at P = 0x422 raises; E625's 0x80 raise
   is evidence against) and keeps H-rel as the proposal had it (every V raises).  7 poked cells
   instead of 5.
4. **No 0x072c gate.**  R1's passed (gate state `pass`, 0x0720-0x072c read in every later DPM
   timeline); every DPM row lists 0x0720-0x072c.  D36 stays a side table (R1: count - 2 holds 6 of
   9 unraised jobs, 0 of 13 raised), never gating, no new prediction.
5. **T5**: the vertex loop is built (relative branch), see section 4; it carries its own knob
   proof.
6. **T3**: HI-w is the RZ of the exact reciprocal of the exact made w (the proposal's 0.75), with
   a one-ulp variant frozen beside it.  T3 and T4 reuse R1's simulator-checked templates
   unchanged.
7. **No rebuild**: R1's tool is pinned by sha256; `stage_r2.sh` checks it on the laptop.

## 7. Fit vs held out

R1's C = 0x371 and the controls are measured data; every 2048 and poke cell is held out.  The SH,
zigzag, prim and made-depth model fits 41 of 41 S1/S1b objects (and R1's T2 cells); T3's w != 1
form reduces to it at w = 1 (`tests/test_models.py`).  RZ 1/w at w = 3, 7, 0.003 is S1b's measured
fit; the made vertices' 1/w, the depth candidates (T4), the loop and the bit-7 point are held out.

## 8. Risks

- g-t5v: a long vertex program was never run on this core; a hang stops the stage (rc 4, reset,
  health). A first backward `br` is unmeasured on the hardware (section 4).
- g-c3: a low cell may need many partial renders (E630: a wide scene in 0x40 pages logged `job hung`
  after 47 to 92); a hang stops g-c3 but `run/r2.sh --only g-c2` still runs after the health
  triangle.  The 2048x2048 context was never run (the tool's mock accepts it; the kernel might refuse:
  the stage stops, rc 4).  4096 jobs write 4.6 MB PB dumps each.
- g-c2: a poke of the PB descriptor; stop on any `job hung` or fault line; the watchdog reset.
- Stop rule: any `job hung` or fault line stops the stage (4); a watchdog, lockup or BUG stops it
  at once (3); a job that does not return stops it (6); a failed health recovery stops it (5).  rc
  3 "scene overflowed" is the normal class of the DPM jobs.
- Nothing writes a clock-gate register, trc_hazard, kreg, /dev/mem beyond `--regs` reads,
  boot-loader files or a kernel; the only debugfs writes are `render_pb_pages` (allow-listed,
  restored), the kernel's own `reset`, and the tool's pb:11 poke; every debugfs access goes
  through `sudo -n`.

## 9. Known bugs of earlier batches and where they are tested

`set -f` losing dumps: run_mock counts the kept dumps of every table.  Knob proofs reading the
previous job's sample: section 3.  Debugfs without `sudo -n` (reads, `[ -e ]`, globs): guard + 4
mock refusals. Missing `--keep-going` / `expectdiff`: the runner refuses both.  Exactly one dri
directory: the first of `dri/*/sgx` is used (three names exist).  A tool message checked in a
truncated tail: the classification greps the whole output (head is only for display).  A restage
resetting a gate file: there is no gate. srcversion: the preflight compares
`/sys/module/gma500_gfx/srcversion` with `modinfo -F srcversion gma500_gfx` (a mock with a
different loaded module is refused).
