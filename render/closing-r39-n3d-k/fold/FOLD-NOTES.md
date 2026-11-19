# r39-n3d-k fold notes (folder, 2026-11-19)

- One attempt, out/20261119-152848 (the lead, user present), on the r38-kernel module
  88ADCEB5AD9F055D077A99C (fork e1cf9d2b43ab, closing29/kernel38/deliver/e1cf9d2b43ab/manifest;
  KUnit all pass), installed and loaded alike, the boot that ran r38-n3c-s4 and -s3 (kernel log
  uptime 14621 s at the arm). Row K of closing29/n3d/design.md §3.1 (session S1).
- The arm logged `own_code: 684 bytes accepted` and `own task armed: slots 0x1, ... emit image
  0x30011100 ... pds=crumb3 pdsat=fw14`; health ok, ticks advancing (217, 246, 274). The blob is
  emitsk (asm/fwtask/emitsk.s at resgx545 70e30d38): emitsb whose entry 0 emits only on a pass
  with pa1 bit 8 set, our emit word 0xfb20b00000008184 (sideband 0, `s2` 0). The image and place
  are r38-n3c-s3's (crumb3, 3 rows, control 0x01800100, offset 0x100 of the firmware's PDS #14
  page); only our bytes and the address are recorded here.
- c1-a: command 1, K0 read 6.9 ms after the command write (cmd 1, slot 1 the fill, tick 2108: the
  ticks did not emit), then one debugfs `miscinfo` read (GETMISCINFO answered after 203 us, 22
  lines, printed, not scored), then the poll: no done within 200 ms, runner rc 1 (`firmware hung:
  the tick stopped`), the kit classed it `hang`, stage rc 4; post did not run.
- The frozen scorer, run on the kept directory (fold/reproduce-own.out): every control passed (PG,
  K0, K1, T0, B) and no frozen outcome held: `N3d-K RULE: CANNOT TELL (no frozen outcome holds)`.
  The readings are K-NEVER's in every column but one: X0 0x5a5a3303, S1 and M4 the host's fill,
  state 0; T (0x0acc) 0x0101ecfd in snap9 and 0x0100b3fe in the stop dump, bit 24 set and
  counting; but Δtick from the kick 7 (15 from the command write, window 248.1 ms; 8 between the
  command write and K0), outside K-NEVER's frozen band 8-11 (the design's §3 common table, R4's
  9-11 from the command write carried over to the kick). alive false (ticks 2115 three times,
  serv_event 67657 three times).
- So the score is CANNOT TELL. The informal reading, not frozen and not scored: with our word and
  `s2` 0, an emit from a GETMISCINFO kick pass did not start the program either and the tick
  stopped as after a timer-pass emit [infer, post hoc]. The band was set before any emit had been
  timed from a kick; nothing measured says what Δtick a kick-pass NEVER would read.
- Read from the kept files (not frozen): snap0 0x0acc 0x0105e396; BIF_FAULT 0 throughout; the
  reset after the stop recovered (t30 triangle `diff: 0 of 4096`, fill `diff: 0 of 2048`); the
  lead found own_arm off afterwards.
- The SIGNATURE line is printed, not scored: USE0_SERV_EVENT bit 16 set at snap0, snap9 and the
  stop dump, count minus tick 6 in each.
- After K, row Z (r39-n3d-z) was first frozen as conditional on K-NEVER. With K CANNOT TELL, the
  user chose (2026-11-19, plan log closing29) to refreeze Z before it ran without the tick band
  (Z-NEVER reads T and S1 alone; Δtick printed): r39-n3d-z's README, "When". K stays CANNOT TELL.
- No vectors table: an owntask row is no table kind. sgx-sim refuses an emit from our own task.
- Records: E1155 (this session); E1156 is r39-n3d-z.
