# r10-dpm: notes for the fold (the builder, 2026-11-13)

## Record (E1009; tooling is adding 4-digit E-number support before folds)

- E1009 (s6rep, Q210): the 15 replicates against H-NOISE and H-BIAS, per target class and the
  frozen decision (README.md), the a0 pair as controls. Narrows Q210's "what puts E874's replay
  low at S_6" to noise or bias. Draft the method with `tools/records/new_record.py --session DIR`.

## What to read after the run

- `score-s6rep.txt`: the TARGET lines (replicates beside the replay and the kept read), the
  DECISION line. H-BIAS-SAME and H-REPLAY6 are tallies for what a bias would be.
- Whether any replicate read S_6 below the replay (none was seen in 13 kept targets: the m6b and
  w cells always read R or above).
- Compare a replicate's S_6 with the same target's partial-render cells (r9-ldpm m6b: 2304x2304
  calibration 0x1e1, cells 0x1dd): not decided by this stage.
- If NOISE: sgx-pipe's `dpm.rs` step test gets a 2-page tolerance at S_6; E874's replay stays.
  If BIAS: sim/sgx-pipe S_6 offsets per target are a candidate, one fit and one held-out target
  needed.

## Deviations from the plan

None. The plan's 17 rows: the a0 pair plus 3 x 5 replicates. Rows round-robin (the plan did not
say an order). The rivals' decision rule (4 of 5 targets) and the class definitions are the
builder's, frozen in README.md and score/score.py before the run.
