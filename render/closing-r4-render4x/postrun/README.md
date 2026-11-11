# postrun/: the frozen scorer's outputs written after the run

Written on 2026-11-11 at the fold, by the frozen `score/score_r.py` on the kept attempts, with the
freeze verified; nothing in `out/` was changed.

- `score-p.txt`: `score_r.py p out/20261111-211315/p`. Stage p stopped at its second fault
  (rc 15), and the driver scores a stage only when it ends, so the run kept no `score-p.txt`.
- `verdict.txt`: `score_r.py verdict out/20261111-211649 out/20261111-211315`, the verdict over
  both attempts, as the driver's last line names it (`run2.log`). The second attempt's own
  `score-o.txt`, `score-t.txt` and `score-h.txt` list s0's controls as NODATA because s0 ran in
  the first attempt; the verdict reads them from there.

The frozen scorer re-run on the kept files gives output byte-identical to the kept `score-s0.txt`,
`score-c.txt`, `score-o.txt`, `score-t.txt`, `score-h.txt` and the five `gate-*.txt`.
