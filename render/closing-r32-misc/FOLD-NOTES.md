# r32-misc fold notes

- Built 2026-11-16 on branch `r32-miscinfo` (worktree closing29/misc32/wt; commits 45bbaaa
  `pre:miscinfo`, f09c011 the fake reset's boot answer, 80d9f2a the fake's CR_CACHE_CTRL; not
  merged). The session's kit is a byte copy of 80d9f2a (FROZEN.commits): the lead stages it as
  frozen, whatever main is then. A fold on a main without the branch must merge it first (or
  cite the branch commit).
- Records: E1126 (m1, snap0/snap9 and the answers), E1127 (m2, the timeline). Q111 clauses only.
- Post hoc, to state in E1126: r31-cc's kernel.log has one `SGX firmware: core ... answered after
  N us` a reset (67 of 67, 130 to 285 us) before every snap0, which read 0x0000ffff (52 of 52):
  the boot's own GETMISCINFO (`sgxfive_ident_ask`, cache control from meta word 30) is a served
  kick without INVAL_DATA. The design note (r31-cc/fold/next-miscinfo.md) said the boot leaves
  0x2 pending for the word's command; at the fork pin `sgxfive_command` clears it on the boot's
  own ask, so the word's command carries 0. E1123's "What it does not show" names this test.
- The kept kernel.log of each stage lets the fold count the answers before every row's snap0
  (held rows too, not only the controls' `kicks`), and read each word read's `us` from
  NAME.miscinfo (kitscore.miscinfo).
- Score: `python3 score/score.py m1 out/ATT/m1`, same for m2; the driver already writes
  out/ATT/score-STAGE.txt.
