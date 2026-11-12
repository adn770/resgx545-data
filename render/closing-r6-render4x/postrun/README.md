# postrun/: written at the fold, after the run

Written on 2026-11-12 at the fold of r6-render4x into records (E887 to E889), with both freezes
verified (`run/freeze_k.sh verify` and `verify B`: files verified, against resgx545 main d9b2969's
files and resgx545-data main e5cdaf0a's); nothing in `out/` was changed.

- `verdict-A.txt`: `score_r.py verdict out/20261112-144822`, set A's verdict over its one attempt,
  the command the driver's last line names (`run-r6x-A.log`). The driver does not write it.
- `verdict-B.txt`: `score_b.py verdict out/20261112-153845 out/20261112-144822`, set B's, as the
  driver names it (`run-r6x-B.log`).
- `data-view.txt`: the render sessions of resgx545-data main e5cdaf0a, which the generators' twin
  scan saw at both freezes, so that `tools/closing/session_tests.sh` shows render/ as they saw it
  and not this session's kept rows.

The frozen scorers re-run on the kept files give output byte-identical to the kept
`score-s0.txt`, `score-a.txt`, `score-t.txt` (set A) and `score-s0b.txt`, `score-b.txt`,
`score-k.txt`, `score-r.txt` (set B).

Set B was frozen (15:01, `FREEZE-B.txt` 15:11) after set A ran (14:48 to 14:52) and its verdicts
were read; README-B.md discloses it. Set B's module is the linux fork's branch r6-kernel at
3f0b3e74 (srcversion 41E2F5C756F96D20F7109A4), booted one-shot at 15:37; its runner checked the
srcversion installed and loaded before the first job (`out/20261112-153845/s0b/runner.log`).
`REWORDED.md` names the two test checks reworded at the fold.
