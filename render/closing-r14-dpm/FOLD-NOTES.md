# r14-dpm fold notes (for the builder's fold, E1044)

- Record E1044 (pr3, Q036): `tools/records/new_record.py --session DIR`; appended corrections only;
  keep question-line edits to Q036's own clauses.
- Kept readings come from `score/score.py pr3 KEPT/pr3`; `read.py` words are `clr pulses period
  short`; the READING lines list each job's clear-run widths (ns), the pulse width is the new datum
  (E1032's one clear was exactly one 16-register sample wide, about 8.4 us [infer: a clear shorter
  than a sample is invisible at any period]).
- PR is the row's label (the knob), not a reading: 0x0658 is not sampled (one register, the plan's).
  The counts 0, 1, 4, 7 are r8-ldpm's kept readings of this scene (E-records of closing r8; 7 at
  thr0 0x60 is one kept job). The plan's PR 8 was replaced by PR 7: no kept 8, and a count that
  cannot be read back must be a repeat. The knob proof is the job's rc (0 at PR 0, 3 otherwise).
- The [check] on the period is resolved in gen/plan.py's docstring: end / samples of every kept
  regtimeline job: 16 registers 7.5 us, 14 7.5, 8 4.7, 5 4.6, 3 1.4 about 0.46 us a register, so one
  register is about 0.46 us; the run's `period` reading confirms or refutes it (control `short`).
- Decision line: R-PULSE strict (PULSES >= PR at all 8 rows), R-RARE-TOTAL (total pulses in 1..8,
  the
  central 95% Poisson interval of 0.109 x 35), ranking by log-loss (R-RARE first needs 1.0 nat over
  each rival). Builder's expectation [infer]: R-PULSE fails again, a handful of clears (about 4),
  the
  ranking R-RARE first on absence if no clears and NO RANKING otherwise.
- Vectors table: `dpm/r14-dpm-pr3`, replay `refused` (register timelines). Sim and sgx-pipe: no step
  rule expected.
- Delete `.pytest_cache` and `__pycache__` before publishing.

## Fold (2026-11-14): what the run showed (post hoc)

- Attempt out/20261114-052638: one job ran (pr3-c0-1, rc 0, class ok), then the stage stopped by its
  own rule (rc 24): `control pr3-c0-1 reads short=0 where the frozen value is 1`. No verdict: the
  scorer prints "cannot tell" for the other nine jobs, which never ran.
- Single-register regtimeline read fine: 118 lines, 894110 samples over 1.5045 s, period 1682 ns.
  The premise `short` (period at most 1000 ns) was frozen from a linear extrapolation (0.46 us a
  register) and was wrong: the period has a floor near 1.3 us plus about 0.4 us a register (16
  registers 7.5 us fits). One register is 4.5 times faster than r13-dpm's 16, not 16 times.
- The PR 0 control showed no clear: 0x0748 bit 2 was set in all 118 lines (values 0x6, 0x7, 0xe,
  0xf, 0x1d, 0x1f), so "none at 0" held in this one job (it would have passed the clr part).
- The frozen threshold stopped a stage that could have run at 1.7 us; whether the pulses are
  visible at 1.7 us is the question the session asked, so the stop threshold was a builder error, not
  a finding about 0x0748. A re-run needs a new session directory (a freeze is never rewritten) with
  `short` meaning at most about 2000 ns or no period gate (the period reported, not gated).
