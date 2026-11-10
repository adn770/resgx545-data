# S1 preflight (prepared 2026-11-09, not run)

Everything under `~/src/scratch/resgx545/closing/s1/`.  The laptop was not contacted, nothing is
committed, no landed tool was changed.  Tests that passed offline: `tests/run_mock.sh` (all 13
tables through the runner against a fake tool and a plain-directory debugfs, the stop rules, the
guard), `tests/mock_all.py` (167 of 167 commands accepted by the tool's own mock),
`tests/emit_checks.py` (four word checks), `tests/test_scorers.py` (the scorers' readers on landed
data: E704's 0x0624 sample and raise dword, the pool walk, the rhw decode, E702's histogram,
E731's gradient range, the 7680 / 1536 deviations, E722's A4 hash).

## 1. Totals and time

| stage | jobs | conditions | est. minutes |
|---|---|---|---|
| g-e1 | 22 | 21 | 3.5 |
| g-e2a | 10 | 8 | 1.5 |
| g-e2b (generated at the pause) | 12 or 14 | 12 or 14 | 2 |
| g-e3 | 35 | 31 | 4 |
| g-e4 | 7 | 4 | 1 |
| g-e8 | 8 | 6 | 1 |
| g-e8b | 6 | 6 | 1 |
| g-e5 | 14 | 6 | 2.5 |
| p-b1 | 11 | 10 | 1.5 |
| p-c | 13 | 12 | 1.5 |
| p-g | 9 | 5 | 1 |
| p-b2 | 5 | 5 | 1 |
| p-d | 7 | 7 | 1.5 |
| p-f | 20 | 10 | 3 |

Total 167 jobs before the pause table, 179 to 181 with it (131 conditions plus the 12 or 14).  The
proposals said about 124 geometry jobs and about 70 pixel jobs.  Estimate: 5 to 8 s a job (reset 3
s, the job, the kept dumps; the 11.41 batch ran 157 jobs in 13 minutes), about 25 s a stage of
preflight, health and copying: 20 to 35 minutes of laptop time without the pause, plus the
analysis of g-e2a (a few minutes) and staging (one `deploy-tool.sh` compile, one `cc` of
regtimeline).  The longest single job is `p-900-0x200` (about 16 partial renders, over a second
each).

## 2. Risks per stage (the runner stops the session on an unexpected hang or fault)

- g-e1: low, but P = 0x200 and 0x300 with 900 and 1350 vertices have never run; E630 saw scenes of
  22 to 92 partial renders and two E438 hang cases at small P.  A hang stops the stage (knob
  `stophang`); `p-900-0x200` is last.  The 4096 x 4096 dumps are about 5.6 MB each raw.
- g-e2a, g-e2b: low (1024 x 768, one partial render at most).  The tool's reference check fails by
  construction for K >= 2 (rc 1, `diff:` lines): knob `expectdiff`.
- g-e3: low.  35 small renders.  Never run on hardware: `probe --tri pixel --tri-v ... --tri-unit
  10` (the `tri` form ran in p1141), `vtx_wclip` at 1024x with a dump, the clamp pokes with a
  vertex program of w.  A removed triangle writes no object; the scorer handles that.
- g-e4: medium-low.  A flip may hang (HH) or fault (HW): both are stated hypotheses and are
  measured (knob `hypo:GROUP:2`: up to two events a flip word, then the word is skipped); a hang
  or fault anywhere else stops the stage.  The same class covers p-f's pairs (HJ, `hypo:COND:2`)
  and p-d's 64-page jobs (HX, `hypo:hx:4`).
- g-e8, g-e8b: low-medium.  `--depth` with `--geometry` has no record (E8a is its first run). The
  depth kpokes of the tool are the "written words" here; each job has its marker.
- g-e5: medium for `r-n2-a32` (a hang each time if HD holds, about 1 s each plus recovery, three
  of them, run last).  The runner treats those as expected (`expecthang`).
- p-b1, p-b2: none (safe jobs; E731's family ran 21 of 21).  New: a 1024-wide depth buffer
  (`--depth-ctl` pitch field g = 31), a 256 x 512 target.
- p-c: low-medium.  E709's ten jobs completed ("risky as declared").  The new programs write o1
  twice under complementary predicates.
- p-g: low.  Ladders may measure nothing (see 4.10).
- p-d: medium at the end: `d-L2e2-20` and `d-L2e2-16` fault by design (E722 recovered 3 of 3 at
  the first health try); `expectfault` makes the runner reset, check health and go on.  The fault
  control `d-L2e2-16` is the last job (nothing depends on it; the scratch line is the knob proof);
  only `d-ok-64` leads.
- p-f: medium at the end: `f-ctl0` (buffer 0 left out) faults twice by design (E573: 0x91000); it
  is the last job, for the same reason. `alias_skip` is written per job, read back, marked and put
  back to 0 after each job and at exit.

## 3. Ready, and what is missing

Ready: 14 tables (13 now, `g-e2b` after the pause), predictions and the freeze, 14 scorers, the
runner with the stop rules, the driver, the staging script, the guard, the tests, `OPTIONS.md`.
The freeze (`run/freeze_s1.sh freeze`) was run after the last change to a script, scorer,
generator, table or prediction; it must be run again after any change (`s1.sh` refuses to start
otherwise).

Missing, in the order they matter:

1. A decision on `debugfs reset` (item 5.1): every job is preceded by one, as in all earlier
   batches.
2. The proposal's HU1 (E2: per-macrotile stream bytes from sgx-pipe's TA model) is not computed:
   the E2 predictions are an empirical coverage proxy, an extrapolation that neither confirms nor
   refutes HU1; the scorer reports the residual, not a pass (item 4.4).  Closing Q211's formula
   needs the TA model run on the six scenes first (offline, before the run if wanted).
3. The vertex fate of E5's `r-n8-a8` (a lost vertex) is not scored automatically; it needs
   `recompute/q164_fate.py` of the verification dataset run by hand on the kept dumps.
4. The scorers are scratch (numpy, stdout).  B1's must become a landed numpy-free tool before its
   result is recorded; nothing is written back into the records or the simulator.
5. `~/regtimeline`, `~/sgxfive-test-s1` and the staged programs are built or copied by
   `stage_s1.sh`; their presence on the laptop could not be checked.  Programs are rebuilt from
   the landed templates, so the identity with the laptop's old `~/sgxprobes-stage*` copies (E702,
   E709) is by source, not by hash (the `p1139-green.bin` is byte-identical to the data repo's).
6. The laptop's kernel is unknown here: the runner's preflight refuses a driver without
   `alias_skip` (branch `resgx545`) or the other debugfs files, and checks installed = loaded. The
   working tree at `/Volumes/linux/linux-sgx` is on the old branch `sgx545`: do not read it as the
   laptop's driver.

## 4. Inconsistencies of the proposals with the source or the records

Geometry (`exp-dpm-geometry.md`):

1. E1 says 24 jobs, 20 distinct conditions "the two repeats and the control are the rest".  The
   table lists 22 jobs (1 + 2 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 12), one repeat, 21 conditions.
2. The knob clamp: the proposal cites `sgxfive_render.c:108`, `sgxfive_drv.c:141` and fork commit
   f5bd8b434ad5a.  In branch `resgx545` (the rewritten history) they are `sgx_render.c:48-53`,
   `sgxfive_drv.c:168-169` and 4c9f342a2a460.  The clamp is the same; a value below 0x23 gives
   0x422 (the whole PB), not 0x23.
3. E2 "apart": moves of (256,0), (0,192), (256,192) cannot reach new macrotiles.  The default
   triangle at 1024 x 768 has vertices (128,96), (896,240), (320,672) and covers 11 of the 16
   macrotiles; a copy moved by one macrotile pitch shares most of them (and (256,0) pushes a
   vertex to x = 1152).  The moves used here are the greedy maximum of the union (computed in
   `gen/s1geo.py`): (0,288), (-64,-240), (-768,-96) give 14, 16, 16 of 16 macrotiles, so `u-3a`
   and `u-4a` cover the same macrotiles.  `--move` cannot be combined with `--tri-v` (it moves
   only the 1/16-pixel copy; the render uses the 1/256 one), so a small triangle was not an option
   without a tool change.
4. E2 HU2 (U = covered macrotiles + c, c constant per grid) fails ON THE FIT DATA, the ten known
   points (no new data): at 1024 x 768 the four positions give U = 19, 20, 17, 12 with 9, 9, 8, 5
   macrotiles (u - m = 10, 11, 9, 7), at 4x4 sampling (8, 10, 9, 6 at 8x8).  The 3-parameter
   scratch model U = 2.209 + 0.347 m + 0.0319 t (macrotiles m, tiles t) misses the proposal's own
   criterion (all ten to within one page): the largest residual is 1.08 pages (192 x 128).
5. E2's observable: "the peak of 0x0624-0x0628's status".  0x0624 is the ZLS threshold (0x400 flat
   in E704); the page status of the landed scorer (`dpm_raise.py`) is the low half of 0x0724
   (E705: 0x13). The scorer uses 0x0724 and cross-checks with the free-list walk (head - 1: 2, 3,
   5, 5, 8, 19 on the `fr-whole` jobs).  The regtimeline lists keep 0x0624-0x0628 for the knob
   proof.
6. E3: "viewport x offset 8, 64, 128, 512, 1000 pixels off" is ambiguous; used absolute offsets of
   block word 6 (E061, E182: 1000.0 = 0x447a0000).  Offsets 8 and 64 still touch a 64 x 64 target;
   HO-region's "absent at 8 px off and beyond" and HO-guard's "present at 8, 64, 128" are read
   that way (region: absent from 128 on; guard: present at 8, 64, 128, absent at 1000, 512
   unknown).
7. E3 WCLAMP: "clamp equal to a vertex's own 1/w".  E194 shows `blk:14` compared with w: a clamp
   of 1e-3 removes w = 1e-5 and below.  The three jobs put the clamp at w, one ulp above and one
   below.
8. E3 "w = 1 must equal E651's object": E651 is an offline decode, not a run.  The control
   compares decoded fields (rhw 1.0 and the vertices (8,8), (56,20), (20,56)).  The proposal's
   slot `pixpds:12` is not the one the landed tables use (`vtxuse`, default pixel program): the
   landed form is used.
9. E3 offline: the three `mte/rhw` dumps already give the stored 1/w as round-toward-zero float32
   of the exact reciprocal (9 of 9 vertices); their packed x, y are unchanged (8, 56, 20), i.e.
   that vertex program does not divide x, y.  Predictions use RZ32 with RN32 as the alternative.
10. E3 count: "36 to 40 jobs, 30 conditions".  The table has 35 jobs (controls included), 31
    conditions; the up to six repeats of "any group whose two runs differ" are not pre-generated.
11. E4's command lacks `--copy-depth`, which E414's five-copy job has (its control "word for word"
    needs it).  E414 shows bit 24 of the TRAILING word (VDM word 4) acts (keeps three triangles,
    sets bit 15 in two primitive entries); the proposal flips bits of the header (word 2), which
    E414 never touched: different words, not a contradiction, but worth knowing before the read.
12. E8b: `--copy-depth` only ever makes the copy farther (z = c / 16), and no option reorders a
    pair; "nearer" is made with `--obj2-blk 10=` (viewport z offset of object 2).  The proposal's
    three translucent configurations (obj 2, obj 1, both) with two depths are 6 conditions, not
    the 4 it counts for 14 jobs: "on both" is dropped.  E8a combines `--geometry` with `--depth`,
    which no record does.
13. E2's U and E8's two-object scenes: the tool's own one-triangle reference check reports a diff
    and rc 1 for every multi-object scene (E627's `st-two-n`); handled by knob `expectdiff`.

Pixel (`exp-pixel-faults.md`):

14. B1 "dx > 1024" contradicts its own ramps (dx 400 to 900, and 1700): a row of the 1024-wide
    target holds about dx - y covered pixels, not 1024; with 32 rows (E731 had 128) the joint
    range will be wider than the "about 1 ulp" measured over 107 rows.  `--depth-pages` is 48 by
    tri1141's formula (the proposal says 40; at least 32 is required).  Of the 16 rules (the
    proposal's eleven plus the reciprocal-of-dx forms RD16 to RD20) one pair is not split by any
    ramp: T20 and RD20 (the proposal says every pair is split; that holds for the 16-bit forms).
15. C: with the `p1` write first and the `!p1` write second, HN ("both land, the second, tag 2,
    wins") predicts tag 2' and cannot be told from HP at K = 7.  The writes are swapped (`!p1`
    first).  The job list had x/y jobs only for k7; the scorer needs the pair for every
    configuration (13 jobs, not 9). `and.testtanz ... #0x10` does not assemble (the immediate must
    be decimal: `#16`).  E570 says o1 lands in the region BEFORE the one that ran it, so "o1 lands
    for every pixel" cannot hold for the last region: the scorer counts landings only.  E709's
    table was marked risky; the proposal says low.
16. G: a pitch of 1/4096 of a 1/64 step over 64 columns spans +-32 columns, narrower than the +-40
    columns (+-0.01 step) it wants to detect: the pitch is 1/2048.  The "step column" is undefined
    for a raw-dword output that also moves with u; u and v are constants here, and no record shows
    that the output depends on the LOD fraction at all.
17. B2: the deviation of E731's dp-ax-b2 is exactly the pixels with x + 2y >= 319 (fit on all
    9216, rows 32 on), although the plane has B = 0 (no y term); that is the control's frozen
    line.
18. D: the frozen A4 image hash is the same for `L2e2`, `L3e3` and `st-L3e2` (9568c92a...), so a
    completion cannot tell them apart by image; 21 pages = 84 KiB equals the extent only if the
    texture starts at the scratch base (E722: base `0x3e003000`, page aligned).
19. F: "11 jobs (2 repeats each)" is 9 conditions, 20 jobs with the second DPM mask.  `alias_skip`
    exists only in branch `resgx545`; E592's `tri -n 2` is the form used.

## 5. Constraints of this session against the machinery

1. `debugfs reset` makes the kernel run its boot sequence, which writes CR_CLKGATECTL and
   CR_CLKGATECTL2 from the firmware's own metadata (`sgx_seq.c:48-49`, `sgxfive_recover`).  No S1
   script writes a clock-gate register, and none uses trc_hazard, kreg, kregnow or a firmware
   task.  The tool's `--depth` writes the ZLS words through debugfs kpoke (kernel words of the
   next job, not registers of ours); that is accepted.  Every earlier batch reset the same way.
   If the rule means "no reset", S1 cannot run as built (a recovery after a fault or hang runs the
   same path).  **Decision needed.**
2. No wait loops: `grep` finds no `while` or `until` in the runner, the library or the driver (the
   guard checks it).  There are single fixed `sleep`s after a reset (3 s) and before the health
   triangle, and each health attempt is written out one after the other.  `regtimeline` samples in a busy cycle inside
   the landed tool (read-only).  If fixed sleeps count as waiting, `RESET_WAIT=0 HEALTH_WAIT=0`
   removes them.
3. No reboot, GRUB, kernel build, install or push: `guard_s1.sh` checks the scripts and the
   tables. The only compiles on the laptop are userspace (`deploy-tool.sh`, one `cc`).
4. `tools/bringup/run-table.sh` and the campaign cannot run these tables (see `OPTIONS.md`), so
   the runner is its own; it reuses `health.sh` between stages and the established per-job shape
   of the 11.39 and 11.41 runners (a keep directory per stage, `raw.sha256`, a marker per job).
5. Markers: every job writes `resgx545 s1 knobs ...`, `readback` (for each knob written), `class`
   and the case marker `resgx545 case NAME RUN` to /dev/kmsg; the kernel-log slice after the case
   marker is kept per job (`NAME.dmesg.gz`), the stage's journal in `kernel.log`.
