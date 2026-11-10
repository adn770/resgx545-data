# S2b: the hold experiments of S2, redesigned after S2 run 3 (prepared, NOT run)

S2b repeats events E4 and E5 with every hold ending mid-period, and with the hold classifier fixed.
S2 run 3 (`../s2/out/`, analysis drafts in `../s2/analysis/records/`) could not tell its holds
apart. The reason was the design (every n a multiple of 50000 put each exit 79 to 86 units after an
old-grid tick) together with scorer bugs, not the hardware.  S2b is a copy of S2's framework.
`../s2/` and its `out/` are not modified.  Nothing here touched the laptop and nothing is
committed.  Read `PREFLIGHT.md` first.

## Layout (as S2; see `../s2/README.md` for the parts that did not change)

- `asm/ring_hold.s`, `bins/ring_hold.blob`: the only source and blob, byte-identical to S2 run 2/3's
  (sha256 `fa0f79db...`).  It has no `pa_read` and no `pa_write`, so S2b writes no sa register.
- `tables/{e4c,e4m,e4l,e5c,e5t}.json`, `TABLES.md`; `predictions/*.tsv` (frozen)
- `score/score_s2.py`: the S2 scorer with the S2b fixes (PREFLIGHT section 2); the E1 and E2 scorers
  stay in the file, unused
- `run/`: the runner (ring_hold only, no pa task), the driver and the staging, both on the laptop's
  `~/s2b` and `~/s2b-out` (S2's `~/s2` and `~/s2-out` are left alone), the freeze, the guard
- `tests/`: `test_scorer.py` (run 3's twelve hold pages as fixtures, synthetic exits), `sim_s2.py`
  (ring_hold in sgx-sim), `run_mock.py` (17 end-to-end tests); the mock EDM follows run 3's hold
  model (PREFLIGHT section 3)

```
run/guard_s2.sh
../pixel-faults/.venv/bin/python gen/gen_s2.py && run/freeze_s2.sh freeze     # only after a change
run/stage_s2.sh                       # copy to ~/s2b and check (no build)
run/s2.sh                             # e4c [G] e4m [G] e4l [G] e5c [G] e5t
```
