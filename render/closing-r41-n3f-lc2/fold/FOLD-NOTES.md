# r41-n3f-lc2 fold notes (folder, 2026-11-21)

- One attempt, out/20261121-073816, on module 83FBFD860D4E0D4CE691F48 (fork r40-kernel
  423b436e7f80, no rebuild, no boot). A rerun of H3 (row LC of closing29/n3f/design.md section
  3.4) with control E0 fixed: stage lc, blob emitsb_sbc43s, arm `slots=0x1 entry=0 pds=land
  pdsat=fw14 form=sbc43`, sideband 0xc43 with the land image (the timer left running, no V0 or V2),
  three jobs: command 1 (the emit, timer pass), command 6 on the next tick pass, command 6 after
  `sleep_ms` 2000. Kit: resgx545 0cfe29a7 (r41-n3f e516a7aa plus the fake runner's posting).
- E0 now reads job 1's record (its slot and cmd_after as the runner read them when job 1 ended,
  before job 2 was posted), not the page after the row. Every other prediction and control is H3's.
- The stage stopped at its one row: job 1 done, job 2 posted and never served (the runner's "no
  done within 200 ms", class hang, rc 4, `## STOP: unexpected hang in lc1-a`); the kit's reset and
  health recovered it (closing29/r41-lc2-logs/health-r41-n3f-lc2.log). The driver did not score
  it; scored by hand with the frozen scorer (fold/reproduce-lc-20261121-073816.out).
- **Frozen verdict: `Q128-N3F-LC RULE: LC-EARLY`**, the prediction held. Controls PG, E0, T0 and
  J1 passed; B failed (BIF_FAULT 0x0000000f in snap9), read by LC-EARLY, which names the fault, as
  the frozen rule says. LC-FILL, LC-FILLOK and LC-HEAL cannot tell; LC-REBASE not reached (its
  outcome line reads FAILED, the PREDICTION line "not reached (LC-EARLY)").
- Readings [HW]: job 1 done, X0 0x5a5a3303, run id 1, cmd_after 0, 10 ticks. After job 1: snap9
  and the stop dump BIF_INT_STAT 0x000d0400, BIF_FAULT 0x0000000f (list 15, page 0); the tick
  stopped (the runner's alive check: ticks 2159 three times, not advancing); job 2 not done
  (cmd_after 6, dwords 224-255 still 0xdeadc0de); no gate ran.
- Survey, printed, not scored: the started entry's post sa0 0x32004000 -> 0x00000000, sa1
  0x32005000 -> 0x04400000, sa2 0x32002000 -> 0x01030b00 (H3: 0x0104b95b), sa3-sa10 as H3's,
  sa12-sa27 = its pa0-pa15 (sa12 = pa0 = 0x00000003, sa13 = pa1 = 0x00043000, pa12 and pa14
  0x5a5a3a18 and 0x5a5a3a1a, land's markers); pa4 (= sa16) 0x32411000 where H3 read 0x32004000.
- [infer] That the copy into sa12-sa27 happened before the early stop, and that 0x00043000 in sa13
  comes from pa1 in this run, are not read: the post words are what the started entry read, and
  round 41's fold found that the started entry's pa can hold words of earlier rows across resets
  (H4's notes: land's markers in pa12 and pa14 after H3).
- H3's kept stage under this scorer (tests/h3/, closing29/r41-lc2-logs/rescore-h3-under-lc2.txt)
  reads E0 PASS and LC-EARLY too: for information only, H3's verdict stays CANNOT TELL (E1176).
- Records: E1178.
