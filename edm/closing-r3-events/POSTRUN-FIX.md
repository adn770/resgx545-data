# Scorer fix after the run (2026-11-11)

The round-3 scorer audit (2026-11-10) found two latent bugs in the frozen scorer
`score/score_r3.py`. Neither changes a verdict or a line on the kept data. Fixed in this published
copy only, as a disclosed post-run fix (decision D7 b, 2026-11-11), with the rule now in
resgx545's `tools/closing/scorekit.py`.

- **C6, one stopped rep made a hypothesis supported (`score_a`).** H-63 (row A1) and H-P11
  (row A6) printed `supported` as soon as any rep of the row stopped the tick, so `A1 stopped the
  tick in 1 of 3 reps: supported` with two reps that kept it. Fix: `supported` only when every
  rep stopped; reps that disagree print `ROW stopped the tick in x of n reps, kept it in y:
  mixed`. On the kept data A1 and A6 kept the tick in every rep: no line changes.
- **C5, a cannot-tell job counted for the stage line (`score_b`).** A B1 job was added to its
  row's tally before the scorer checked whether it could be read, so a job whose ring held no
  skipped entry (its job line says cannot tell) still counted for the B1 reading of the stage
  line. Fix: a job counts only once it has passed the cannot-tell exits (stop jobs and the B0
  control as before). On the kept data every B1 job had its skipped entry: no line changes.

Tests (written first, in `tests/test_scorer.py`, `test_postrun_fixes`): A1 stopped in 3 of 3
reps (supported), the audit's repro on A6 (1 of 2 reps: mixed, not supported), and B1 with no
skipped entry in any rep (not counted) or in one rep (the two that decided still read H-FREE).
Against the frozen scorer three of them fail, as they should.

**Four existing checks encoded the C6 bug and were changed**, two in `tests/test_scorer.py`
(`test_stage_a`):

- the A1 world (A1 stops in 1 of 3 reps) expected `A1 stopped the tick in 1 of 3 reps:
  supported`; it now expects `A1 stopped the tick in 1 of 3 reps, kept it in 2: mixed`;
- the A6 idle-pending world stopped only `a6` and expected `A6 stopped the tick in 1 of 2 reps:
  supported`; it now stops both `a6` and `a6-r2` and expects `A6 stopped the tick in 2 of 2
  reps: supported`;

and two in `tests/run_mock.py`, whose mock stop worlds stop one rep of the row and keep the
others:

- `t_a_stop_a6` expected `A6 stopped the tick in 1 of 2 reps: supported`; it now expects `A6
  stopped the tick in 1 of 2 reps, kept it in 1: mixed`;
- `t_a_stop_a1_signatures` expected `A1 stopped the tick in 1 of 3 reps: supported`; it now
  expects `A1 stopped the tick in 1 of 3 reps, kept it in 2: mixed`.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256` and
  `LAPTOP.sha256` too. Every file the run wrote in `out/` is byte-identical.
- `out/score-STAGE.txt` (a, b, k7) is the scorer's output as kept (see `REWORDED.md`).
  `out/score-STAGE.fixed.txt` beside each is the fixed scorer's output on the same kept stage,
  byte-identical to the kept file in 3 of 3 stages.
- `score/score_r3.as-run.py` is the scorer before the fix, byte for byte (its hash is the
  `score/score_r3.py` line of `FROZEN.pre-fix.sha256`); run on the kept stages it prints output
  byte-identical to the kept `out/score-STAGE.txt` in 3 of 3 stages.
- `FROZEN.pre-fix.sha256` is the freeze as published before this fix (after the rewording;
  `FROZEN.pre-reword.sha256` is the one the run used). `FROZEN.sha256` differs from it only in
  the line of `score/score_r3.py` and the new line of `score/score_r3.as-run.py` (the lines of
  the other files were not regenerated; `tests/test_scorer.py` and `tests/run_mock.py` are not
  in this freeze).
- `run/freeze_r3.sh verify` passes in a copy of this directory with the two resgx545 files
  pinned at 52e1f06 (`tools/fwtask/fwtask.py` and `tools/fwtask/regs.toml` changed in resgx545
  after the freeze). There the offline tests pass: sim_r3.py 53 ok, test_scorer.py 84 ok (80
  before the fix), test_guard.py 32 ok, run_mock.py 17 of 17 tests and 102 ok (as before the
  fix).

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `score/score_r3.py` | 17bfb7320078cb5d | 9fa16bbf15d66a79 | yes |
| `score/score_r3.as-run.py` | (new) | 17bfb7320078cb5d | yes |
| `tests/test_scorer.py` | 7a9b29ac464cc06f | daf3bab7adaebd88 | no |
| `tests/run_mock.py` | 1eae864be0325b8d | fbabb5673ab4829c | no |
| `FROZEN.sha256` | 0d544021e16661ba | 429d25b8270ac1c8 | (the freeze) |
