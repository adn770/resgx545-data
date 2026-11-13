# c5-q210: S6 lower-end class (E1009), kept DPM runs r5..r10

Rule file `s6bias_rule.py`, sha256 ee0fe5e410b52e206b368738b6485e7c2cd10c333ea747c39045e567cffa6b95
(FREEZE.log). Scorer `s6bias_score.py` -> `s6bias_score.out` (rerun: `python -I`). Reader =
r10-dpm `score/read.py` (bracket (a, max(a, b-1)), lower end = a). R = replay S6: r10-dpm
`gen/r9_tables.json` (13 targets) plus, for 11 more targets, r8-ldpm `gen/ol7_tables.json` and
r7-dpm `sibling-src/b/q210_targets.out` (same E874 replay; the 13 agree across the sources).

## Frozen before reading kept samples
H-CLASS (R+1 at the 5 biased, R at the 8 held targets, every run), H-LOW0, H-LOWPLUS1, and a
candidate H-RULE "biased iff w/h > 2 or w < h". H-RULE is FIT on the 13 (stated from E1009's
list); its predictions for the other targets were frozen (as a formula) before they were read.

## Data
520 kept jobs with width/height and a timeline; 62 calibration runs (no partial render) and 121
cell runs (S6 read before the first partial render) have an S6 step and a replay R. Fit/known rows:
E1009's 15 + control, E962's 4, E961's 2048x2304 m6b rows. All else held out for H-CLASS.

## Results, S6 lower end d = lower - R
First pass, all workloads: H-CLASS on the 13: calibrations 37 held / 9 failed; cells 56 / 3.
All 12 exceptions are `--vtx-coords`/`--slot` jobs at 2048x2048 (v-* of r6/r7/r8: d = -154,
-225, +113): a different scene, not the replay's (E937; dpm.rs says so). [post hoc scoping]
Standard workload (1500 vertices, p1139-green, no vtx-coords):
- H-CLASS, 13 targets: calibrations 37 held / 0 failed (21 fit + 16 held-out), cells 56 / 0
  (6 E961 + 50 held-out). Held eight: 1280x1280, 1536x1536, 1792x1792, 2048x2048, 2304x1792,
  2304x2304, 2560x2048, 4096x2048: d = 0 at every run (calib 16 of 16; cells all). Five biased:
  d = +1 at every run (calib 20 of 20 incl. 15 of 15 of E1009; cells 6 of 6).
- H-LOW0: fails on every biased run (calib 27 of 53 over all targets). H-LOWPLUS1 fails 26 of 53.
- Cells never differ from calibrations at a target (d is constant per target, both kinds).
- S2/S3 lower end d2, d3: d2 = 0 everywhere except 4096x1536 (-1); d3 = +1 at 2048x2304 and
  4096x1536, +2 at 3072x2560 (cal), else 0 (2048x2048 v-runs excepted).

## Targets beyond the 13 (kept, with a replay R): they TEST H-RULE
d6lo = +1 (biased): 2048x3072 (5 cal + 7 cells), 2560x3072 (1 + 5), 3072x2560 (1 + 5).
d6lo = 0: 1024x1024 (3 + 6), 2560x2560 (2 + 15), 3072x2048 (3 + 5), 3072x3072 (cells, 18),
1024x2048 (1 cal), 2048x4096 (1 cell; E935/E915 note S3 +3 there).
H-RULE predicted: 2048x3072 B ok, 2560x3072 B ok, 1024x1024 H ok, 2560x2560 H ok, 3072x2048 H ok,
3072x3072 H ok; 3072x2560 H -> observed B (FAIL, 1 cal + 5 cells); 1024x2048 B -> observed R
(FAIL); 2048x4096 B -> observed R (FAIL, 1 cell). H-RULE: 51 of 53 calibrations and 112 of 118
cells match run-wise, but 3 of 9 beyond-13 targets fail: REFUTED as a rule (aspect alone).
No kept target with a replay R and a standard S6 step remains untested: also kept but with no
replay in any published table: 2048x1024 (E881), 4096x4096, 1024x768 (other scene); their d cannot
be read (no R). 152 jobs lack an S6 step (aborted before it, or no timeline step).
[post hoc, no rule fitted] Biased 8: 4096x1024, 4096x1536, 3584x1024, 2048x512, 2048x2304,
2048x3072, 2560x3072, 3072x2560. Not biased 13: see above. No simple w, h, pixel count, aspect or
residue of 256/512/1024 separates them (1024x1024 and 2048x3072 share residues).

## What would refute / needs
H-CLASS is refuted by one run off class on the 13 (none). Needs for a rule: a replay's block and
region counts per target (sgx-pipe `replay_1500` is private; no R for 2048x1024, 4096x4096).
Rests on E874, E915, E935-E938, E961-E963, E1009. [infer] the bias is a per-target offset of the
replay, not noise (all runs at a target agree on d, whichever session).

## Records
E1009's text stands for its five targets. An appended note is advisable: the bias also holds at
2048x3072, 2560x3072, 3072x2560 (E915/E936 read them "one above"); it is absent at 1024x2048 and
2048x4096; "wider than 2:1" does not explain it. dpm.rs's STEP_TARGETS comment is consistent.
All files here are publishable (data-derived numbers only, no firmware content).
