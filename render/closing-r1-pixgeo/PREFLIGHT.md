# R1-pixgeo preflight: jobs, time, controls, the 0x072c gate, fit vs held out, risks, corrections

Prepared 2026-11-10 from `closing2/exp-pixel.md` section 1,
`closing2/geometry/exp-geometry-round2.md` and the decisions R2-11 to R2-17.  Nothing ran on the
laptop.  Frozen: `FROZEN.sha256` (every generator, scorer, runner script, table, prediction,
staged program, template, `TOOLSRC.sha256` and the read-only imports pbdump.py, probe.py,
counters.py and the landed templates the generators read), `PREDICTIONS.sha256`.  Refreeze
(`run/freeze_r1.sh freeze`) only if the tables are regenerated, and never after the first job.

## 1. Jobs and time

| stage | jobs | conditions | what |
|---|---|---|---|
| p-c2 | 41 | 40 | Q276 C2: 18 configurations as x/y pairs, direct reads c-rd-g23 / c-rd-g25, premise pair c-rd-pa, one replicate |
| g-u1 | 21 | 21 | 17 scenes against HU1 and 2 boundary pairs; the first two are the 0x072c trial |
| g-c1 | 22 | 22 | the fine ladder: 2 controls, 15 cells at 1500, 5 at 1350 |
| g-t1 | 11 | 11 | off-target boundary |
| g-t2 | 7 | 6 | clipped polygons (one replicate) |
| g-t7 | 4 | 4 | fine grid |
| g-u2 | 9 | 9 | the count constant k |
| g-t5 | 9 | 9 | sub-pixel cull |
| g-t6 | 7 | 7 | clamp ladder |
| **total** | **131** | | plus 1 of the 16 `g-c1f` cells after C1 |

Time, from S1b's per-stage times (about 5 s a plain job; the 4096 jobs with their 4.6 MB PB dumps
and partial renders 10 to 15 s; a reset and a health triangle between stages): p-c2 4 min, g-u1 4,
g-c1 5 (22 gzips of PB dumps), g-t1 1.5, g-t2 1, g-t7 1, g-u2 2, g-t5 1.5, g-t6 1, health between
stages 2: **about 24 minutes of jobs**, plus staging with the tool rebuild about 4 minutes;
plan 35.

Not in R1 (as decided): geometry C2 (the pb:11 poke), C3, T3 and T4 rows, the three U2 spacing
cells (they depend on the k found), and the other questions of the session.

## 2. The 0x072c trial and its gate (decision R2-13 b)

`CR_DPM_GLOBAL_PAGE_STATUS` (0x072c, read-only, glossary G0828) is added to the register timeline
of the first DPM job only (u-ctl-1, then u-ctl-2a if the first was clean); the other DPM jobs add
it only if the gate passed.  `regtimeline` reads LO-HI inclusive in steps of 4, so the widened
range 0x0720-0x072c also reads 0x0728 (new in these timelines).  The repo's notes already record
0x072c reads (0x10001, 0x40004, 0x50005: `questions/vdm/Q036`), so the values are expected small.

The gate state (`~/r1-out/gate072c.state`: `untested`, `pass1`, `pass`, `fail`, with a time; a
`pass` older than 6 h counts as untested) is reset to `untested` when g-u1 starts.  After EACH
trial job the runner evaluates (shell, laptop side; `score/gate072c.py` is the same rule):

- **clean** means all of: G1 the job ended in the normal classes (class ok: rc 0, or rc 3 with
  "scene overflowed"; no hang or fault line); G2 its kernel-log slice (after the case marker,
  before any reset) holds no line but our own markers (S1b's ok jobs all had none); G3 the
  timeline header lists 0x072c and 0x0724 and the job has at least 10 rows; G4 every 0x072c sample
  is plausible (not 0xffffffff or 0xdeadbeef, both halves at most 0x40) and at least one has a
  non-zero low half; G5 the 0x0724 low-half peak equals the control's frozen U (19, then 29): the
  extra reads did not disturb the DPM; G6 a plain 64x64 triangle drew exactly right right after
  the job without a reset.
- clean job 1: `untested` to `pass1`; clean job 2 (sampled because of `pass1`): to `pass`;
  anything else: `fail`.  Rows with the knob `s072c` (all other DPM rows of g-u1, g-c1, g-c1f,
  g-u2) list 0x072c only in state `pass`; after a `fail` the stages go on without it (the verdicts
  do not need it; D36 is then "not scored").  A hang, fault or failure in a trial job stops the
  stage (rc 4) as in every job, with the gate recorded as `fail`.
- `run/r1.sh` prints each stage's `gate072c.txt` after the copy; `score_r1.py g-u1` re-evaluates
  G1 to G5 from the kept files and prints what the runner recorded.  D36 (dword 36 against 0x072c)
  is a side table, never gating.

## 3. Controls: how each passes and fails

| stage | control | passes | fails (scorer) |
|---|---|---|---|
| p-c2 | c-e709 | 17..29 tag-5 pairs | cannot tell for the stage |
| p-c2 | c-u, c-u-r2 | tag-2 fraction >= 0.98 each (S1b 0.990) | cannot tell for the stage |
| p-c2 | c-g23r4 | rule x bit 4 (register form of S1b's immediate) | the g23 group cannot tell |
| p-c2 | c-o4-u | o4 class 5 (both o4 writes unpredicated) | the o4 group cannot tell |
| p-c2 | c-rd-pa | o0 = pa0 / pa1 decodes to the pixel's own position in >= 90% | the direct reads cannot tell |
| g-u1 | u-ctl-1, u-ctl-2a | U = 19, 29 (E705/E735 measured) | cannot tell for the stage |
| g-c1 | c-1500-0x360, -0x380 | raise, none (E753), second run reaching thr0 | cannot tell |
| g-t1 | o-x64, o-x1000 | present, none (E736/E650) | cannot tell |
| g-t2 | z-flat099, z-cut-p | E651's object, depth 0x3f7eb852; S1/S1b's cut-p object (4 items) | cannot tell |
| g-t7 | e3f-ctl | the 1/256 packing | cannot tell |
| g-u2 | k-0xa0, k-0xb0 | count 2, 1 (E625) | cannot tell |
| g-t5 | t5-ctl-sq, t5-ctl-none | S1b's e3k-ctl present (1/w 0x4479ffff), e3k-i-c1e3 none | cannot tell |
| g-t6 | t6-ctl | S1b's e3k-i-c3e5: object, 1/w 0x47023555 | cannot tell |

Knob proofs: g-u1, g-c1, g-u2 the job's own 0x0624 rows (`knob_value`, never the first sample:
S1b's bug); p-c2 the marker nibbles of the decoded words (x job marker m, y job m + 1, frozen in
`bins/c2-markers.tsv`) and the program sha256; the T stages the program sha256 (frozen) and the
echoed `--tri-v` / `--blk`.  Every tri row carries `expectdiff` (a runner check refuses a table
where one does not: S1b's missing-expectdiff stop); a multi-render tri row needs `--keep-going`.

## 4. Fit vs held out

Everything the offline work read from measured data is a FIT; what the new runs hold out is
labelled.

- HU1 (U): residual 0 on all 16 measured U (a fit, two constants from a small grid): u-ctl-1 and
  u-ctl-2a carry it as `repeat`, the other 15 scenes are held out; HU2 (macrotiles + 8) is the
  alternative and fails where it differs.  Boundary pairs: E625's rule on HU1's U, held out.
- C1: H-abs's range (C in [0x35e, 0x37e)) is E753's two controls; every cell between is held out;
  HP1 (1350 equals 1500 at the same P) is held out.  D36: 99 of 99 unraised jobs are the fit,
  raised jobs held out.
- T2: the SH + zigzag + prim + depth model fits 41 of 41 S1/S1b objects (and the two controls);
  the five new clips (and the slab in both plane orders) are held out.  T7: HF-round is S1's post
  hoc reading; the three triangles are held out.  T1's HO-region fits S1's five cells; 88.0,
  87.5, -24, -24.5, y and 88.5..104 are held out.  T5, T6: held out.
- Q276: c-k7, c-k0, c-g23 are S1b fits run again (`repeat`, tallied apart); c-k1, c-k2, c-k5, the
  g23 masks, the o4 configurations and the two direct reads are held out; c-k1-x-rep is the
  replicate.

## 5. Corrections to the proposals (found while building; each is frozen as built)

1. **U1 boundary pair.** The proposal's b-2-m96 pair P = 0x45 / 0x46 is not E625's rule for
   U = 24: P = U + 0x22 - 1 and U + 0x22 give 0x39 / 0x3a (0x45 / 0x46 would be U = 36).  b-m32
   at U = 21 is 0x36 / 0x37 as proposed.  U1 has 21 jobs (17 scenes + 4), not 22.
2. **T2 z-cut-m-slope.** The proposed prediction (3 vertices, B kept) is that of z = 2x - 1: with
   z = 4x - 1, B has z = 2 > w and is clipped at x = 0.5 too: a 4-vertex polygon, both plane
   orders frozen.
3. **T2 model.** A plane no vertex crosses is not run (a pass rotates the polygon by one; the
   S1/S1b stored order is the zigzag of one pass), and an unclipped triangle keeps its input
   order.  Both fit all measured objects (`tests/test_models.py`) and are in the generator.
4. **Q276 tolerance.** "At most 2 disagreeing of >= 400 sources" would refute S1b's own c-k0 fit
   (6 lane-0 sources at x 12..14 and 46 kept the !p1 write, of 490).  Frozen: at most max(2, 2%)
   exceptions among >= 300 decoded sources; a wrong rule misses 25 to 50%.  The g23
   configurations carry no fraction (the decoded sources are not half at x bit 4: 0.237), only
   the per-source rule.
5. **Q276 masks.** `and.testtanz` with `#0x20` or `#0x100000` does not assemble (decimal
   immediates up to 127 only): the new masks go through a register (`mov r1, #mask`), validated
   by the control c-g23r4 (mask 0x10) against S1b's immediate form c-g23 (kept as a repeat).
6. **Direct reads.** `or.skipinv.end o0, g23, #0` and the g25 twin assemble (checked); the
   program writes only o0 (any other output would overwrite o0 words), so "o0 off its pixel" is
   tested by the premise control c-rd-pa (>= 90%).  c-k4 is left out (c-k5 carries HQ-none).
7. **C1 pause.** The step-1 cell depends on the flip: all 16 candidates are frozen in `g-c1f`,
   one runs (`r1.sh --cell g-c1f f-1500-0xNNN`).  U2's three spacing cells depend on the k found:
   not prepared.
8. **0x072c.** The proposal says it is in no kept timeline; the repo's notes record reads (E358,
   E438, E443): the plausibility bound uses them.  The range also reads 0x0728.
9. **Templates and the mock.** The tool's `--mock` does not execute vertex programs (every
   variant draws the host triangle, 1098 pixels), so it checks acceptance only; behaviour is
   checked with the landed simulator (`sgx-sim --task vertex`, bit-exact z and w at the three
   vertices), the instruction-level structure (one changed instruction; second phase index) and
   the assembler.  No row needs a tool change: T2-T4 are probe programs assembled on the Mac and
   staged; the laptop rebuild only pins the tool hash (`TOOL.sha256`), as in S1b.

## 6. Risks

- Reading 0x0728 / 0x072c adds registers to the timeline: a lower sampling rate (fewer rows, a
  coarser 0x0724 peak); G5 would catch a peak that moved.  The trial runs on the two jobs whose U
  is known.
- p-c2 uses new words on hardware only in its programs (a register-held mask, `or ... o0, g23`):
  same slot and shape as S1b's 40 completed p-c jobs.
- g-c1: 22 jobs at 4096x4096 with 4.6 MB PB dumps each (gzip on the laptop about 3 s each);
  rc 3 "scene overflowed" is the normal class.
- U1 non-library sizes (640x480, 1280x1024, 2048x1536) and 2048x2048: accepted by the tool's
  mock, never run on hardware.  A refusal stops the stage (rc 4).
- Stop rule: any `job hung` or fault line, or an unexplained failure, stops the stage (4); a
  watchdog, lockup or BUG stops it at once touching nothing (3); a job that does not return stops
  it (6); a failed health recovery stops it (5).  There are no hypothesis rows.
- Nothing writes a clock-gate register, trc_hazard, kreg/kpoke, /dev/mem beyond the `--regs`
  reads, boot-loader files or a kernel; the only debugfs writes are `render_pb_pages`
  (allow-listed, restored) and the kernel's own `reset`; every debugfs access goes through
  `sudo -n` (guard-checked, including `[ -e ]` and globs).  The debugfs directory is the first of
  `dri/*/sgx` (three names exist).
