# Scorer fix after the run (2026-11-10)

The frozen scorer `score/score_c3.py` printed three verdict lines that its own job lines and its
`SUMMARY` line contradict. Read from the kept job records (`out/c3/*.json`), after a reload (L)
and after a reset and a reload (R) r20 read 0 and r21 the writer's marker in 6 of 6 jobs, so
"r20 and r21 both survived" holds in 0 of 6:

- `Q158 L ...` and `Q158 R ...` printed `r20/r21 survived 3/3`. The count read `res["r"]`,
  which the job loop had overwritten with the pair of values `(r20, r21)` (a tuple, always
  true) instead of the row's result. A scorer bug.
- `H-KEEP (r20/r21 after a reload or a reset): held in all 6` and `H-ALL (...): refuted in 6 of
  6 jobs` scored the `b_r_kept` row (r20 and r21 both kept) alone, not the hypotheses: both
  hypotheses also predicted sa63 kept, which read 0 in 6 of 6, and the `SUMMARY` line lists
  both as refuted.

Fixed in this published copy only, as a disclosed post-run fix: the job loop keeps the pair under
another key, the Q158 lines print the row and r20 and r21 apart, and each hypothesis gets a line
for its r20/r21 row and one for all its i, r and sa63 rows. The `SUMMARY` line and every job
line are unchanged.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `LAPTOP.sha256` and
  `TOOL.sha256` too. `out/` is byte-identical.
- `out/score-c3.txt` is the frozen scorer's output as printed after the run, kept.
  `out/score-c3.fixed.txt` is the fixed scorer's output on the same kept `out/c3/`.
- `score/score_c3.as-run.py` is the frozen scorer, byte for byte (its hash is the
  `score/score_c3.py` line of `FROZEN.pre-fix.sha256`); run on the kept stage it prints output
  byte-identical to `out/score-c3.txt`.
- `FROZEN.pre-fix.sha256` is the freeze the run used (the lead's refreeze before the first job);
  `FROZEN.sha256` is regenerated after the fix (`run/freeze_c3.sh freeze`) and differs in the
  lines of `score/score_c3.py`, `score/score_c3.as-run.py` (new) and `tests/run_mock.py`.
- `tests/run_mock.py` matched the old wording of the two hypothesis lines in one check; that
  string was updated to the new wording. The offline tests pass on a copy of this directory
  (`tests/run_all.sh`: sim_c3.py 24 ok, test_scorer.py 58 ok, test_guard.py 30 ok, run_mock.py
  84 ok, guard clean).
- The unchanged originals stay in the scratch session directory the run used.

The lines that changed (`diff out/score-c3.txt out/score-c3.fixed.txt`):

```
< Q158 L (reload (no reset)): kept i0/i1 3/3, sa63 0/3, r20/r21 survived 3/3; p2 p3 after: 01 00 00
< Q158 R (debugfs reset and reload): kept i0/i1 3/3, sa63 0/3, r20/r21 survived 3/3; p2 p3 after: 01 00 00
> Q158 L (reload (no reset)): kept i0/i1 3/3, sa63 0/3, r20/r21 both survived 0/3 (r20 0/3, r21 3/3); p2 p3 after: 01 00 00
> Q158 R (debugfs reset and reload): kept i0/i1 3/3, sa63 0/3, r20/r21 both survived 0/3 (r20 0/3, r21 3/3); p2 p3 after: 01 00 00
< H-KEEP (r20/r21 after a reload or a reset): held in all 6
< H-ALL (r20/r21 after a reload or a reset): refuted in 6 of 6 jobs
> H-KEEP, its r20/r21 row only (both kept after a reload or a reset): held in all 6
> H-KEEP as a whole (its i, r and sa63 rows after a reload or a reset): 12 held, 6 FAILED of 18
> H-ALL, its r20/r21 row only (both kept after a reload or a reset): FAILED in 6 of 6 jobs
> H-ALL as a whole (its i, r and sa63 rows after a reload or a reset): 6 held, 12 FAILED of 18
```

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `score/score_c3.py` | b4d4cfdc41183efe | bd4856a89b8008c7 | yes |
| `score/score_c3.as-run.py` | (new) | b4d4cfdc41183efe | yes |
| `tests/run_mock.py` | 5b0a0c0c0177eeba | 20767deb3ccea5ed | yes |
| `FROZEN.sha256` | 8140fae7124e37b9 | 21f5abf785658c3b | (the freeze) |

## Second scorer fix (2026-11-11)

The round-3 scorer audit (2026-11-10, C7) found that a failed control still let some rows through.
Fixed in this published copy, as a second disclosed post-run fix (decision D7 b, 2026-11-11), with
the rule now in resgx545's `tools/closing/scorekit.py`. No line changes on the kept data: every
control passed, and every fill was read.

- **A failed control gated only some rows of its job.** When the job's markers were not read at
  the next event (`a_markers` FAILED), `b_i_kept`, `b_r_*`, `b_sa63_kept` and `b_markers` were
  cannot tell, but `b_p0p1`, `b_p2p3`, `b_pclink`, `b_sa20_sa24_zero` and every `b_SA_same` row
  were still scored. Fix: the failed control makes every row after the perturbation cannot tell.
- **The Q158 count lines counted a job whose control failed.** Fix: such a job is left out of
  the counts, and the line names it (`; 1 job with a failed control not counted (l1)`); a row
  with no job left prints `cannot tell`.
- **The r21 step of a fill was taken across a fill that was not read.** `last_fill_r21` kept the
  reading of the last fill read, so with f2 void f3's step was taken against f1. Fix: a void,
  stopped or unread fill, and a fill whose control failed, reset it; the next step is cannot
  tell (`no previous fill reading`).

Tests (written first, in `tests/test_scorer.py`, `test_postrun_c7`): the audit's repro
(`synth_c3.py`, l1's control failed: every `b_` row of l1 cannot tell, the Q158 L line counting 2
of 2 and naming l1, l2's rows still decided), f2 void (f3's step cannot tell; with every fill
read it is decided), and f2's control failed (f3's step cannot tell). Against the scorer of the
first fix four of them fail, as they should.

- `out/score-c3.fixed2.txt` is this scorer's output on the kept `out/c3/`: byte-identical to
  `out/score-c3.fixed.txt`. `out/score-c3.txt` (the frozen scorer's output) and
  `out/score-c3.fixed.txt` stay as they were.
- `FROZEN.pre-fix2.sha256` is the freeze after the first fix, byte for byte; `FROZEN.sha256` is
  regenerated after this fix (`run/freeze_c3.sh freeze`) and differs from it only in the lines of
  `score/score_c3.py` and `tests/test_scorer.py`. `run/freeze_c3.sh verify` passes.
- The offline tests pass on a copy of this directory (`tests/run_all.sh`: sim_c3.py 24 ok,
  test_scorer.py 64 ok, test_guard.py 30 ok, run_mock.py 11 of 11 tests and 84 ok, guard clean).
- The first fix's scorer is not kept as a separate file: it is `score/score_c3.py` at the
  previous commit, and its hash is the `score/score_c3.py` line of `FROZEN.pre-fix2.sha256`.

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `score/score_c3.py` | bd4856a89b8008c7 | 6e48a73485952229 | yes |
| `tests/test_scorer.py` | 9cb53cf7d4db70cc | 7103a3e64578d49c | yes |
| `FROZEN.sha256` | 21f5abf785658c3b | f0dafe335b2ef2b3 | (the freeze) |
