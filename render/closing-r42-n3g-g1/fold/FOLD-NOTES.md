# r42-n3g-g1 fold notes (folder, 2026-11-23)

- Module 079DD0D13F231EEAC52FE0F (linux fork r42-kernel ec6511d5de87, built on cachix 2026-11-21,
  closing29/kernel39c/deliver/ec6511d5de87/manifest; closing29/r42-n3g-logs/cachix-wait.log), the
  one-shot boot of 2026-11-22, installed and loaded alike. Session G1 of closing29/n3g/design.md
  (sections 3.1 and 3.2): stage c (row C, the build control, blob emitsb14s, `form=fw14`, sideband
  0x843, crumb3), then stage m (row M, blob emitsb_sbc43s, `form=sbc43`, sideband 0xc43, image
  mark), each one row of two jobs: command 1 (the emit, timer pass) and command 6 (the after-read
  of sa0-sa31 into dwords 224-255) on a GETMISCINFO kick. Kit and blobs: resgx545 c0e2dc36 (branch
  r42-n3g). The fork's KUnit suite on the Mac shim with the round's own suite, 48 of 48
  (closing29/r42-n3g-logs/shim-r42.log; r42-red 46 of 48, shim-r42-red.log; a wrong form fails,
  shim-r42-neg.log).
- **The first try did not run.** Attempt 20261122-154515: staging failed at its first step, ssh
  timing out at the `mkdir` on the laptop (out/stage.log: `STAGING FAILED: mkdir on the laptop:
  ssh exited 255: Connection timed out during banner exchange`). Nothing was staged and nothing ran
  on the laptop; no out/ directory was made for it. The second try, attempt 20261122-160857, is the
  session's one run (closing29/r42-n3g-logs/runone-G1-try2.out).
- Rescored by hand with the frozen scorer (fold/reproduce-c-*.out, fold/reproduce-m-*.out): the
  same bytes as the kept out/20261122-160857/score-c.txt and score-m.txt.
- Stage c: every control passed; `Q128-N3G-C RULE: C-GATE, C-SAME` as predicted. Job 2 done on the
  kick (GETMISCINFO answered after 200 us); its after-read equal to job 1's pre in all 32 sa; the
  gate's fill and triangle exact; BIF_FAULT 0 in snap9; K5: BIF_FAULT 0 before and after both jobs.
- Stage c, R-BOOT (printed, not scored): job 1's post odd pa are the words of the nine kept rows of
  round 40 and 41 (design section 0.1), 8 of 8: pa1 0x00043000, pa3 0x01555620, pa5 0, pa7
  0x03c3cdac, pa9 0xdc531a54, pa11 0x5d50716f, pa13 0x82e151b5, pa15 0x11b5d77a. Even pa: pa0 3,
  pa2 0x32002000, pa4 0x32411000, pa6 0x32002000, pa8 0x32004000, pa10 0x32002000, pa12 0x5a5a3a18,
  pa14 0x5a5a3a1a (land's markers from round 41). So the module change and the reboot left these
  words as they were.
- Stage m: PG, E0, T0, J1 and J2 passed; B (BIF_FAULT 0 in snap9) FAILED: snap9 read BIF_INT_STAT
  0x000d0400, BIF_FAULT 0x005d300f. The frozen rule reads B through the outcomes that name a fault
  and prints `Q128-N3G-M RULE: M-FILL, M-PA, M-REBASE, M-SA1, M-SA13; FAULT: BIF_FAULT is not 0
  after the row and no outcome names it`. Every prediction held: M-PA, M-SA13, M-SA1, M-REBASE and
  M-FILL held; M-FILL43, M-FILLM1, M-FILLOK and M-NOKICK failed. rc 16 at the gate, the planned end
  (on_gate_fail = "score").
- Stage m readings: job 1's post pa1 = M13 0x005d3000 (the only post pa that differs from stage
  c's); job 2's after-read equals job 1's post in all 32: sa1 = M1 0x005d1000, sa13 = M13, sa12-sa27
  = pa0-pa15, sa0 0x32004000 and sa2 0x32002000 kept, sa3-sa10 0x3f800000, 0x32004000, 0xbec00000,
  0x32002000, 0x3f800000, 0x32004000, 0x3f400000, 0x32002000.
- Stage m, K5 (printed): job 1 BIF_FAULT 0 before and after; job 2 BIF_FAULT 0 before (pre) and
  0x005d300f after (post). So the fault arose in job 2, the GETMISCINFO kick and command 6 served
  on the rewritten bank, not after job 1's pass.
- Stage m, the gate: the fill's kernel line `BIF fault 0xd0400 at 0x5d300f (PD 0x0) stalls job 11,
  recovering`, every pixel 0xdeadbeef; the triangle after the watchdog's recovery reset exact.
  devcd2 (detector manual) was there before the gate; devcd3 (detector bif-fault, BIF_FAULT
  0x005d300f) appeared during the fill. Since BIF_FAULT already held 0x005d300f from job 2 when
  the fill was sent, the fill's own fault reading cannot tell a fresh fault from the latched one:
  M-FILL is the page the fill stalled on, read through a fault already set.
- Health after the session's end: fill and triangle ok (closing29/r42-n3g-logs/health-r42-n3g-g1.log).
- Records: E1179 (stage c), E1180 (stage m).
