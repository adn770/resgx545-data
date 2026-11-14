# r15-dpm fold notes (for the builder's fold, E1057)

- Record E1057 (pr4, Q036): `tools/records/new_record.py --session DIR`; appended corrections only;
  keep question-line edits to Q036's own clauses. Predecessor E1044 (period 1682 ns; gate error).
- Kept readings: `score/score.py pr4 KEPT/pr4`; `read.py` words `clr pulses period short`; the
  READING lines list each job's clear-run widths (ns), the pulse width is the datum.
- Only change from r14-dpm: SHORT_NS 2000 (gen/plan.py, score/read.py, run/hooks.sh awk twin).
- Decision line: R-PULSE strict, R-RARE-TOTAL 1..8, log-loss ranking (1.0 nat margin).
- If period reads over 2000 ns the stage stops at the first control (rc 24): report, no verdict.
- Vectors table `dpm/r15-dpm-pr4`, replay `refused`. Sim/sgx-pipe: no step rule expected.
- Delete `.pytest_cache` and `__pycache__` before publishing.
