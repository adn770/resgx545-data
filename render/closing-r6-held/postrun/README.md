# r6-held: files written at the fold (2026-11-12), after the run

- `score-q.txt`: the frozen scorer on stage q's kept files, `score/score_h.py q
  out/20261112-154536/q`. The driver writes `out/ATT/score-q.txt` only after a stage ends, and
  stage q stopped with rc 22 (a -110 in two cells in a row, after b2's health), so no score file
  was kept for q; this is the scorer's output on the kept files, unchanged.
- `verdict.txt`: `score/score_h.py verdict out/20261112-154536`, which the driver names and does
  not write. Its s0 line is the kept `out/20261112-154536/score-s0.txt`'s, byte for byte.
- `paths-as-frozen.txt`: `gen/data/sources.lst`, and the freeze's lines of the E848 files it
  lists, keep their absolute paths in `tools/closing/session_tests.sh`: gen/hgen.py writes its
  fixed data path into the list and tests/test_gen.py checks the list against what it writes,
  and run/freeze_h.sh verify wants every listed path in the freeze (the tests read E848's kept
  files at that path, as tests/test_twin.py does).

The scorers verify the freeze before they score, and the freeze names the O3 oracle files of
`private/o3/`, which derive from the firmware and are published only in resgx545-data-private
(`cited/closing6/r6-held/private/o3/`). Run them where those files are back in place
(`tools/closing/session_tests.sh` puts them back). Part P's scorer, `p/score/score_p.py p1
p/out/a1/p1`, re-run on 2026-11-12, gave `p/out/a1/score-p1.txt` byte for byte; part H's s0 the
same.
