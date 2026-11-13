# r13-dpm fold notes (for the builder's fold, E1032)

- Record E1032 (pr2, Q036): `tools/records/new_record.py --session DIR`; appended corrections only.
  Candidate text: counts and clear lines per row, the DECISION line (strict form, ranking), the
  readings of 0x0700 to 0x0728 and G; "narrowed" only if the rows part the rivals.
- Kept readings come from `score/score.py pr2 KEPT/pr2`; `read.py` words are `nparts clr pulses
  gmax knob`; `hi10` and the distinct values are in the READING lines.
- Vectors table: `dpm/r13-dpm-pr2`, replay `refused` (register timelines).
- Builder's expectation (README): strict form fails, no ranking at 8 jobs. If bit 2 clears at a PR 0
  row, state it as the finding against R-PR's "none at 0" (E1019's note stays, appended
  correction only).
- Post hoc: the builder looked at the kept 3072x2048 clear lines before freezing (README).
- Delete `.pytest_cache` and `__pycache__` before publishing; sim and sgx-pipe updates: none
  expected (no step rule).
