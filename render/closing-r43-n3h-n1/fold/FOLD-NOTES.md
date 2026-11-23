# r43-n3h-n1 fold notes (folder, 2026-11-23)

- One attempt, out/20261123-164401, on module 079DD0D13F231EEAC52FE0F (fork r42-kernel
  ec6511d5de87, the one-shot boot of 2026-11-22; no rebuild or boot for round 43), the first
  session of round 43 (closing29/r43-n3h-logs/runone-N1.out). Session N1 of closing29/n3h/design.md
  (sections 3.1 and 3.2; the user's decisions A-E all (a), 2026-11-23). Kit and blob: resgx545
  1f49335c (branch r43-n3h: K6 and K7 on main 4993566e). Both stages run emitsb_sbc43s with
  `form=sbc43` (sideband 0xc43) at fw14.
- Stage w (row W, image mark: M13 0x005d3000 to attribute 13 and M1 0x005d1000 to attribute 1,
  one job, T3 stops the tick, no gate, no end draws): rc 0, scored by the driver
  (out/20261123-164401/score-w.txt). Rescored by hand with the frozen scorer
  (fold/reproduce-w-20261123-164401.out): the same bytes. `Q128-N3H-W RULE: W-QUIET, W-SA1,
  W-SA13`; every control passed; every prediction held (W-FAULT failed as predicted).
- Stage v (row V, image landv, no begin draws, job 1 the emit with the tick running, job 2 command
  6 on the next tick pass): exited 4 at its one row (class hang), the planned end; the driver did
  not score it. Rescored by hand (fold/reproduce-v-20261123-164401.out), the same bytes as
  closing29/r43-n3h-logs/score-r43-n3h-n1-v.txt. `Q128-N3H-V RULE: V-EARLY1, V-KEEP, V-V`; PG,
  E0, T0 and J1 passed, B and J2 FAILED (read by V-EARLY1, which names the stop, the frozen rule);
  every prediction held (V-OTHER, printed, failed).
- Readings (printed): w's and v's job 1 post sa equal word for word: sa1 = M1, sa13 = pa1 = M13,
  sa0 = V0, sa2 = V2, sa12-sa27 = pa0-pa15, sa3-sa10 the float and V words of rounds 41-42. v's
  job 2 K5 pre already BIF_INT_STAT 0x000d0400, BIF_FAULT 0x005d100f (list 15, page 0x005d1000 =
  M1 = job 1's post sa1), job 2 never served (cmd_after 6, dwords 224-255 0xdeadc0de), the tick
  stopped (the runner's alive check). Kernel lines: w's arm after the begin draws "3 events seen";
  v's arm with no draws "0 events seen".
- Between w's emit and v's emit ran only w's disarm reset, w's exit reset, v's begin reset with the
  register health (no draw) and v's arm (boot, GETMISCINFO, ticks) [HW, kernel.log of both
  stages]. The kit's reset and both draws recovered v (health ok, runone-N1.out; health log
  closing29/r43-n3h-logs/health-r43-n3h-n1.log).
- The scorer's JOB line "no done within 200 ms (job 1)" counts jobs from 0: the job not served is
  job 2.
- [post hoc, infer] V-EARLY1 with V-KEEP: the early stop's fault page follows the word in sa1, as
  LV's 0x04400000 was LV's sa1 (E1183). LC's page 0 (E1176, E1178: sa1 0x04400000) is not
  explained by that.
- Records: E1184 (w), E1185 (v).
