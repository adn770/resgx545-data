# Scorer fix after the run (2026-11-11)

The round-3 scorer audit (2026-11-10) found one latent bug in the frozen scorer
`score/score_r3.py`. It changes no verdict and no line on the kept data. Fixed in this published
copy only, as a disclosed post-run fix (decision D7 b, 2026-11-11), with the rule now in
resgx545's `tools/closing/scorekit.py`.

- **C5, a cannot-tell job counted for the stage line (`score_e`).** An X1 or B3 job was added
  to its row's tally before the scorer checked whether it could be read, so a job whose job line
  says cannot tell (ACTED 0: its acted pass never came in the window; the acted pass not logged;
  the ring full) still counted for the stage's hypothesis line. Repro (the audit's): set ACTED to
  0 in x1 and x1-r2 of the H-EXIT world; the frozen scorer still printed `H-EXIT (a tick pass
  ...` from those two jobs. Fix: a job counts only once it has passed the three cannot-tell
  exits; the line then reads `B3 stopped, X1 not read`. On the kept data every X1 and B3 job
  passed them: no line changes.

Tests (written first, in `tests/test_scorer.py`, `test_postrun_fixes`): the audit's repro, and
the H-EXIT world with only x1-r2 at ACTED 0 (the X1 rep that decided still reads H-EXIT).
Against the frozen scorer the repro fails, as it should.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256` and
  `LAPTOP.sha256` too. Every file the run wrote in `out/` is byte-identical.
- `out/score-STAGE.txt` (c, d, e, h) is the frozen scorer's output as kept.
  `out/score-STAGE.fixed.txt` beside each is the fixed scorer's output on the same kept stage,
  byte-identical to the kept file in 4 of 4 stages.
- `score/score_r3.as-run.py` is the frozen scorer, byte for byte (its hash is the
  `score/score_r3.py` line of `FROZEN.pre-fix.sha256`); run on the kept stages it prints output
  byte-identical to the kept `out/score-STAGE.txt` in 4 of 4 stages.
- `FROZEN.pre-fix.sha256` is the freeze as published before this fix; `FROZEN.sha256` differs
  from it only in the line of `score/score_r3.py` and the new line of `score/score_r3.as-run.py`
  (the lines of the other files were not regenerated; `tests/test_scorer.py` is not in this
  freeze). `run/freeze_r3.sh verify` passes.
- The offline tests pass on a copy of this directory (`tests/run_all.sh`, before and after the
  fix: guard clean, freeze verified, sim_r3.py passed, test_scorer.py 127 ok before and 129 ok
  after (5 fixtures absent, as before), test_guard.py 53 ok, run_mock.py 17 of 17 tests and 127
  ok).

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `score/score_r3.py` | 726dc2badb24a37c | fe066daf6b4bce0c | yes |
| `score/score_r3.as-run.py` | (new) | 726dc2badb24a37c | yes |
| `tests/test_scorer.py` | 84e075cdfa1f51df | 0f69bdfd20570694 | no |
| `FROZEN.sha256` | 19c1c47a414d188b | 106a656d52b71b28 | (the freeze) |
