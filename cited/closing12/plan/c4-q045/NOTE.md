# C4 / Q045 (b): rule A2 (state page sum = last TA run's peak status - 1) on closing sessions

Rule: `a2_rule.py` sha256 2f9a6503...c173 (v1 crashed on a truncated timeline row before printing
any score); `a2_rule2.py` sha256 ba89c2b0...cabe = same rule + skip truncated rows, frozen before
scoring (FREEZE.log). Run: `python -I a2_rule2.py > a2_rule2.out`. Functions copied from
`resgx545-data/vdm/verification-1141ta/recompute/dpm_raise.py` (timeline, runs, ctl, state_page).
Criterion: raised job (TA3DCtl dword 38 == 0x20) passes iff sum of 16 (dword>>16) at the state
page (0x42000 if tri width >= 4096 else 0x6000) == peaks[-1] - 1. Rivals: sum = peak; peak - 2;
pages of the last TA run (peak - status at the run's first sample). Fit rows: the 11.38 batch
(48/48, not re-scored here). Held out: closing-r5..r7-dpm, r1-pixgeo, r2-geo, r3-geo tadata dumps.

## Held-out results (a2_rule2.out)
- Raised, state page found: 91 jobs; A2 held 4, failed 87. Rivals: sum = peak 0; peak-2 3;
  last-run pages 4. Verdict by the frozen criterion: REFUTED.
- Unraised: 177 jobs; A2 0 (E627's split; rivals 0 / 2 / 3). Not part of the verdict.
- Cannot tell: r8-ldpm 40 + r9-ldpm 9 + r10-dpm 2 + r5 1 (no ctl dump), r1-r3 geo 157 (no
  timeline in the txt; r1 also 2 no txt). r8/r9/r10 dpm have no (or no scorable) tadata+ctl pair:
  the r8-r10 sessions contribute 0 raised rows. Dirs named closing-r8-dpm / r9-dpm do not exist.
- [post hoc] (`posthoc.py`, `posthoc.out`) split by whether the page at the rule's offset is all
  zero: raised zero page 62 (A2 0): the dump has no state page there (the 2048-wide closing dumps
  have an empty 0x6000, nonzero data starts at 0x12000), so the offset rule of dpm_raise.py does
  not locate it: [infer] these are "cannot tell", not refutations of the sum. Raised with a
  nonzero page: 29 jobs, A2 4, 25 miss. Differences (peak - sum) of the misses: mostly 3
  (4096-wide 1500-vertex jobs: sum 570/571 vs peak 573/574; 2048 job 78 vs 81), a few 2 and 1.
  Five raised rows (r3 c5a-*) have sum 134192:
  garbage, the page there is not a state page (a different layout).
- [infer] the A2 equation as stated is not general; it fits the 11.38 batch scenes only. The
  closing-session scenes (1500 vertices, 4096 wide) break it; peak - 3 is the common difference
  there and was not frozen (not a fitted rule, post hoc observation only).

## Refutes / would change
- Frozen: any raised job with a state page where the sum misses peak - 1: 87 do (29 with a
  nonzero page). Q045 part (b)'s clause "sum = peak - 1 (48 of 48)" needs the scope appended:
  holds on the 11.38 batch scenes, not on the closing r1-r7 1500-vertex / 4096 scenes
  (4 of 29 nonzero-page raised rows). No landed record holds the statistic (C4 survey), so no
  E-record correction, only the question text. Whether the scenes differ by multiple
  macrotile-list reuse is untested here.

## Caveats
- E900 (G6, G7) opened 183 of these state pages for another field (the global list): rows are
  held out of A2, but the files were not unread.
- Raised flag via ta3d.1 else after.buf09 (dword 38). Timeline peak = max (status & 0xffff) of
  the last TA run after the last partial render.
- Records: E625, E627, E631, E900. All files here are scripts and counts from published data;
  no firmware-derived content; publishable.
