# r34-q010 fold

- Run: attempt 20261116-231015 (lead, 2026-11-16 23:10-23:16, travel cable, module 7CE8E38E),
  rc 0, 32 jobs of stage c, every row class ok, no stop, fault, hang or lead decision.
  fold/lead-run.log is the lead's driver log, fold/lead-stage.log the stage log.
- Score: the frozen score/score.py reproduces score-c.txt byte for byte (fold/reproduce.out);
  `score.py q010 out/20261116-231015` prints fold/q010-rule.out: controls 15 of 15, held-out R
  rows 9 of 9, H-TRI on every row (9 of 9), H-FILL 4 FAILED, H-BOTH 2 FAILED, H-NONE 3 FAILED,
  H-IDLE 0 of 2, H-COPYNL 0 of 2: "one job hypothesis, H-TRI: RETIRE-CAPABLE".
- Readings: the R rows after t10 `tri` (t2a-rd, t2b-rd) and after the pair (t6-rd) read black
  0xd3522437a14b6325; the R rows after t10 `fill` (t1a-rd, t1b-rd), the plain copy (t3a-rd,
  t3b-rd), 60 s and 120 s idle (t4-rd, t5-rd) and no job (t0a-rd, t0b-rd) read E037's
  0xb6067a95fa98de2d. z0-ld, z0-rd read black; every L read E037's hash.
- Record E1134 (texture). Q010 narrowed on branch r34-fold-q010 to the answer with the givens
  stated; the retirement is a separate commit on branch r34-retire-q010 (not merged), for the
  user to confirm the givens ((b)'s recovered hangs, E1112, and (c), E271, not re-run).
- Sim: no frozen row is a replayed vector (README "Replay vectors": refused, cross-job state);
  sgx-sim's comment on the set a job without the load reads now cites E1134 (the triangle clears,
  the caller's batch must say so); no behaviour change.
