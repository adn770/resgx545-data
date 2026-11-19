# r39-n3d-z fold notes (folder, 2026-11-19)

- One attempt, out/20261119-153429 (the lead, user present), on the r39-kernel module
  0CDFCDB73D76F39FE9E593C (fork f9453424bf71, built on cachix by closing29/kernel39c,
  closing29/kernel39c/deliver/f9453424bf71/manifest; series check 10 of 10), installed and
  loaded alike, after its one-shot boot of 2026-11-19 (kernel log uptime 58 s at the arm). Row Z
  of closing29/n3d/design.md §3.2 (session S3).
- Frozen twice before it ran: first as conditional on r39-n3d-k reading K-NEVER, with the 8-11
  tick band; K read CANNOT TELL (Δtick 7 from the kick), and at the user's choice the session was
  refrozen without the band (Z-NEVER reads T and S1 alone, Δtick printed), the srcversion the
  built module's; the predictions of the T1..DONE rows did not change. The published FROZEN.sha256
  and PREDICTIONS.sha256 are the second freeze (README, "When").
- The arm logged `own_code: 684 bytes accepted` and `own task armed: slots 0x1, ... emit image
  0x30011100 ... pds=crumb3 pdsat=fw14 pds2=req form=fw14`; health ok, ticks advancing (218, 247,
  275). The blob is emitsk14 (asm/fwtask/emitsk14.s at resgx545 7d1aa9e5): emitsk with the emit
  word 0xfb20b10800c08184, ours with the 14-bit sideband 0x843 (the value the firmware's #12 and
  #14 emits carry, a fact of the data-private O1 read), every other field equal; `pds2=req` makes
  the kernel write 0x00020000 into the blob's `pds2` limm, so the emit's `s2` is the request
  #14's emit carries (the O2 fact). Image and place as K and r38-n3c-s3. Only our bytes, the
  facts above and the address are recorded here; no firmware byte.
- c1-a: command 1, K0 read 6.7 ms after the command write (cmd 1, slot 1 the fill, tick 2488),
  one debugfs `miscinfo` read (GETMISCINFO answered after 204 us, printed, not scored), the poll:
  done after 10.5 ms, echo 1, cmd 0; class ok, stage rc 0; the owntask gate (tick stopped) drew
  the triangle and the fill exactly; the disarm reset recovered the tick (293, 322, 349).
- The frozen scorer (the driver's score-own.txt; fold/reproduce-own.out the same bytes): every
  control passed (PG, K0, K1, T0, B), `N3d-Z RULE: Z-DONE: all ran`. X0 0x5a5a3303; T 0x005a3305
  in snap9 (crumb3's last `tim` marker; snap0 0x01023f19 running); S1 0x5a5a3304; M4 0x5a5a3302
  and the run id 1; state 2. Δtick 6 from the kick (15 from the command write, 47.7 ms window);
  alive false, as T1 stops the tick by design (crumb3's first `tim` write is a stopped 0).
- Post (fold/reproduce-post.out = score-post.txt): p1-tri and p2-fill diff 0, exact.
- The LANDING line is one exploratory row, printed, not scored: entry 1's pa0-pa3 read
  0x00000000 0x00043000 0x3727c5ac 0x01555620 and sa0-sa3 0x32004000 0x32005000 0x32002000 0,
  snap0's TA3DCtl dwords 0-3. pa0 and pa2 are not V0 and V2 [HW]; sa0-sa3 equal V0-V3, but sa0
  and sa2 hold V0 and V2 in the EDM's tasks anyway (E002, E1148), so where crumb3's two douta
  landed is not told by this row [infer].
- The SIGNATURE line is printed, not scored: USE0_SERV_EVENT bit 16 set at snap0 and snap9,
  count minus tick 5 and 7.
- What it shows: the first program our task emitted that ran, all of it, with its doutu starting
  our entry 1 to done. Against r38-n3c-s3 (M-NEVER) three things changed together: the sideband
  (0 to 0x843), `s2` (0 to 0x00020000) and the pass (the first tick pass to a GETMISCINFO kick
  pass). Which of them decides, alone or together, is open: row S (closing29/n3d/design.md §3.2)
  splits them.
- No vectors table: an owntask row is no table kind. sgx-sim still refuses an emit from our own
  task, now citing this record for the one mirrored form that ran.
- Records: E1156 (this session); E1155 is r39-n3d-k.
