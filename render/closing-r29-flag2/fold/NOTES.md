# r29-flag2 fold notes (after the run, outside the freeze)

Attempt out/20261116-073242, driver rc 0: s0 4 of 4 references passed, h1 and h2 ran every row,
4 planned hangs (q010-h1, q010-h2, h2-b3, h2-c3), each with its kernel `job N hung, recovering`
line, each reset clean and its strict health drawing; no `SGX recovery failed` line. Scorers
reproduced byte for byte (reproduce.out).

- Q010 (E1112): the frozen rule R29-3 (a) reads "narrow only" (q010-af had no fault before it).
  The measured reading is H-RECOV-CLR's hash, not the predicted H-KEEP's: q010-p1 and q010-p2
  (each after a recovered hang) read black 0xd3522437a14b6325. q010-af, the first copy of h1, read
  black too, with no fault or hang since s0's c10-bn read BT.601: only s0's end health pair (t10
  `fill`, `tri`), h1's begin health pair and debugfs resets lie between. q010-pre, after
  q010-ld2's load and a debugfs reset alone, read BT.601 (as E1097 and E1103). [post hoc, infer]
  So the set survives a debugfs reset alone and does not survive the health pair; the recoveries
  of p1 and p2 also ran a strict health pair, so the run does not part "a hang's recovery clears
  the set" from "the health fill or triangle clears it". E1103's rows had no health job between
  them; E271's zeros after hung jobs fit either.
- Q163 (E1113): H-PREV16 held 3 of 3 held out (h2-a3 ok at c = 8 after (6,2); h2-b3 and h2-c3
  hung after (5,2) and (3,2)), the control h2-c-b passing; D-PREVADD, D-C 1 of 3, H-ALWAYS 2 of 3.
  H-PREV16 was formed after E1035 was read; these rows are its only held-out test. Q163 is not
  retired: v = 0 in block 1 below c = 4 and what the counter is stay open.
