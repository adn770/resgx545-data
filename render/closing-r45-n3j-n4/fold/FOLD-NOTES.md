# r45-n3j-n4 fold notes (folder, 2026-11-25)

- One attempt, out/20261124-210745, on module 079DD0D13F231EEAC52FE0F (fork r42-kernel
  ec6511d5de87; no rebuild or boot before N1-N4), the fourth session of round 45, after N3
  (closing29/r45-n3j-logs/runone-N4.out, run rc 4: lff's planned stop). Session N4 of
  closing29/n3j/design.md (sections 3.1 and 3.6; decision D (b): the optional row included). Kit
  and blob: resgx545 94f9e501 (K9).
- Stage wi (row W, image mark, one job): rc 0, scored by the driver (score-wi.txt). Rescored by
  hand (fold/reproduce-wi-20261124-210745.out): the same bytes. `Q128-N3J-WI RULE: W-QUIET,
  W-SA1, W-SA13`; every control passed; every prediction held (W-FAULT failed as predicted).
- Stage lff (row LFF, image land, begin draws fill,fill, jobs as lf2): exited 4 at its one row
  (class hang), the planned end; the driver did not score it. Scored with the frozen scorer after
  the run (closing29/r45-n3j-logs/score-r45-n3j-n4-lff.txt) and again by hand
  (fold/reproduce-lff-20261124-210745.out): the same bytes. `Q128-N3J-LFF RULE: LFF-PAGE`; PLANT,
  PG, E0, T0, J1, DR and DK passed, B and J2 FAILED (read by LFF-PAGE, which names the stop).
  **LFF-SA1 FAILED** (predicted held: post sa1 is 0x04000010, not M1); **LFF-SA0 FAILED**
  (predicted held: post sa0 is 0, not 2); LFF-PAGE held as predicted; LFF-V0 and LFF-HIST failed
  as predicted.
- Readings (printed): lff's job 1 done (9 ticks), post sa0 0x00000000, sa1 0x04000010, sa2
  0x0105fbea (sa02kind TRIPLE), sa13 = pa1 = M13; job 2's K5 pre already BIF_INT_STAT 0x000d0400,
  BIF_FAULT 0x0000000f (page 0; the scorer names job 1's post sa0), post, snap9 and the stop dump
  the same; job 2 never served; the tick stopped. KC begin delta 6 (two fills, ok); the end KC
  cannot tell (the stop). HKC (printed): 0x04000010 is the word H-KC names for the second fill's
  3:4 entry at K 4 (and X's, E1174, for a triangle's 3:4 at K 4 after one fill). Kernel: lff's arm
  after the two fills "2 events seen". The kit's reset and both draws recovered it (health ok,
  closing29/r45-n3j-logs/health-r45-n3j-n4.log).
- Post sa3-sa31 and pa0-pa15 equal in wi and lff, and equal to N2's and N3's (printed).
- [post hoc, infer] Two fills before land did not leave the planted M1 that crumb3 read after two
  fills twice (FF, FF2: E1191, E1202), nor sa0 2: the triple has a triangle's shape (0, a word, a
  timer word) with a word of a slot-3 entry at K 4. The same list has now given two outcomes; with
  sa0 0 the stop faulted at page 0.
- Records: E1216 (wi), E1217 (lff).
