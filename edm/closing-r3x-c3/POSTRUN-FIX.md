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
