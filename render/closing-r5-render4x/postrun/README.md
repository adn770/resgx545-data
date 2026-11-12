# postrun/: written at the fold, after the run

Written on 2026-11-12 at the fold of r5-render4x into records (E865 to E869), with the freeze
verified (`run/freeze_k.sh verify`: files verified, against resgx545 main f0d5b39's files);
nothing in `out/` was changed.

- `verdict.txt`: `score_r.py verdict out/20261112-100112`, the verdict over the session's one
  attempt, the command the driver's last line names (`run-r5x.log`). The driver does not write it.
- `posthoc_d.py`, `posthoc_d.out`: a reading of row d's held TA-data dump made after the run
  (post hoc): how each region header the frozen scorer counts as off the rule is off, by
  macrotile and in runs, and whether anything below `td.rgn` is non-zero. Standard library; run
  from the session directory.

The frozen scorer re-run on the kept files gives output byte-identical to the kept
`score-s0.txt`, `score-t.txt`, `score-o.txt`, `score-m.txt`, `score-l.txt`, `score-x.txt` and
`score-d.txt`.

FREEZE.txt names main 7a30713 as the commit the session was frozen against. The lead later amended
that commit to f0d5b39 (the two trees differ only in doc/specs/vectors.md); 7a30713 is on no branch.
Every pin of `FROZEN.commits` is a commit on main, and each pinned file at main f0d5b39 has the
pinned hash (`tools/usse-asm/usse-asm` is untracked, a build product, checked against the file).
