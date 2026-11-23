# r43-n3h-n2 fold notes (folder, 2026-11-23)

- One attempt, out/20261123-164448, on module 079DD0D13F231EEAC52FE0F (fork r42-kernel
  ec6511d5de87; no rebuild or boot), after session N1 (closing29/r43-n3h-logs/runone-N2.out).
  Session N2 of closing29/n3h/design.md (sections 3.3 and 3.4; decisions A-E all (a),
  2026-11-23). Kit and blob: resgx545 1f49335c (branch r43-n3h). Both stages run emitsb_sbc43s with
  `form=sbc43` (sideband 0xc43) at fw14.
- Stage w2 (row W2, row W byte for byte): rc 0, scored by the driver
  (out/20261123-164448/score-w2.txt), rescored by hand
  (fold/reproduce-w2-20261123-164448.out): the same bytes. `Q128-N3H-W2 RULE: W-QUIET, W-SA1,
  W-SA13`; every control passed; every prediction held.
- Stage f (row F, image crumb3, begin draws the fill alone; job 1 the emit, T3 stops the tick; job
  2 kick-only (K6: GETMISCINFO, no command, 50 ms, expect notdone); job 3 command 6 on a
  GETMISCINFO kick): exited 4 at its one row (class hang), the end K-STALL names; the driver did
  not score it. Rescored by hand (fold/reproduce-f-20261123-164448.out), the same bytes as
  closing29/r43-n3h-logs/score-r43-n3h-n2-f.txt. `Q128-N3H-F RULE: K-KICK, K-QUIET, K-REPLY,
  K-STALL`; PG, E0, T0, J1 and J2 passed, B and J3 FAILED (read by K-KICK and K-STALL).
- **F-FILL4 FAILED against its prediction (held).** Job 1's post sa1 0x01000000: neither M1 nor
  0x04000010 (no bits in 23:0). F-KEEP failed as predicted; F-OTHER (printed) held. Every other
  prediction held; F-GATE not reached (K-STALL).
- Readings (printed): job 1 done (10 ticks), K5 BIF 0 before and after; post sa13 = pa1 = M13
  (planted by w2), sa0 = V0, sa2 = V2, the other words as w2's. Job 2: K5 pre BIF_FAULT 0; the kick
  answered (GETMISCINFO after 200 us, 3.6 ms); K5 mid (read right after the reply) BIF_INT_STAT
  0x000d0400, BIF_FAULT 0x005d300f (list 15, page 0x005d3000 = M13 = post sa13); post the same.
  Job 3: K5 pre, mid and post 0x005d300f; the kick not answered (the kernel: "no GETMISCINFO answer
  (-110)"; the runner: [Errno 110]); cmd_after 6, dwords 224-255 0xdeadc0de. Kernel lines: f's
  arm after the one fill "1 events seen" (w2's after both draws "3 events seen").
- The tick count was 2091 at job 2's start and 2090-2091 at the stop: T3 in crumb3 stops the tick
  at job 1 (design section 3.1), so the stopped tick here is T3's, not a sign of the stall; the
  stall is read from job 3's unanswered kick and unserved command.
- Between w2's emit and f's emit ran w2's disarm and exit resets, f's begin reset, one stock fill
  and f's arm [HW, kernel.log]. The kit's reset and both draws recovered f (health ok,
  closing29/r43-n3h-logs/health-r43-n3h-n2.log).
- The scorer's JOB line "no done within 200 ms (job 2)" counts jobs from 0: the job not served is
  job 3.
- [post hoc, infer] With V (n1, E1185) keeping M1 across the same boundary without the fill, the
  one fill rewrote attribute 1, to 0x01000000, not the slot-3 event word H-EVT predicted. That the
  top byte is a count is not claimed.
- Records: E1186 (w2), E1187 (f).
