# r44-n3i-n1 fold notes (folder, 2026-11-24)

- One attempt, out/20261124-005624, on module 079DD0D13F231EEAC52FE0F (fork r42-kernel
  ec6511d5de87, the one-shot boot of 2026-11-22; no rebuild or boot for round 44), the first
  session of round 44 (closing29/r44-n3i-logs/runone-N1.out, run rc 0). Session N1 of
  closing29/n3i/design.md (sections 3.1-3.3; the user's decisions A-E all (a), 2026-11-23). Kit
  and blob: resgx545 ce01a0c4 (branch r44-n3i: K8 on main 9076992b). Every stage runs
  emitsb_sbc43s with `form=sbc43` (sideband 0xc43) at fw14.
- Every stage was scored by the driver (out/20261124-005624/score-*.txt) and rescored by hand
  with the frozen scorer (fold/reproduce-STAGE-20261124-005624.out): the same bytes for all nine,
  and the same bytes as closing29/r44-n3i-logs/score-r44-n3i-n1-STAGE.txt.
- Plants wa, wb, wc, wd (row W, image mark, one job, T3 stops the tick, no gate, no end draws):
  every control passed; `Q128-N3I-WA/WB/WC/WD RULE: W-QUIET, W-SA1, W-SA13`; every prediction
  held (W-FAULT failed as predicted). Job 1's post sa1 = M1 0x005d1000, sa13 = pa1 = M13
  0x005d3000, K5 BIF_FAULT 0 before and after, snap9 0.
- Reads (image crumb3, one job, no gate), each right after its plant, PLANT passed in each, DR
  passed in each (the declared list at try 1, each draw exact):
  - ft (begin draws fill,tri): post sa1 0x04400000. `Q128-N3I-FT RULE: FT-SAME, X-QUIET`.
    FT-SAME held as predicted; X-KEEP failed as predicted; every prediction held.
  - ff (fill,fill): post sa1 0x005d1000 = M1. `Q128-N3I-FF RULE: X-KEEP, X-QUIET`. **FF-N
    FAILED** (predicted held); **X-KEEP FAILED** (predicted failed, read held); FF-LAST and FF-K
    failed as predicted; X-QUIET held.
  - t (tri): post sa1 0x02400000. `Q128-N3I-T RULE: T-K, X-QUIET`. **T-N FAILED** (predicted
    held); **T-K FAILED** (predicted failed, read held); T-LAST and X-KEEP failed as predicted.
  - tf (tri,fill): post sa1 0x02400000. `Q128-N3I-TF RULE: X-QUIET`. **TF-N FAILED** (predicted
    held); TF-LAST, TF-K, TF-TRI and X-KEEP failed as predicted; X-OTHER (printed) read held.
  - f2 (fill, no plant, after tf's default end draws fill,tri): post sa1 0x05400000.
    `Q128-N3I-F2 RULE: F2-QUIET`. **F2-N FAILED** (predicted held); F2-ACC, F2-K and F2-PRIOR
    failed as predicted; F2-OTHER (printed) read held; F2-QUIET held.
- Every read: job 1 done, K5 BIF_FAULT 0 before and after, snap9 0. Post sa0 = V0 0x32004000, sa2
  = V2 0x32002000 (crumb3 writes both), and post sa3-sa31 and pa0-pa15 equal word for word in all
  nine stages (and in N2 and N3): only sa1 differs.
- Kernel "events seen" at each read's arm (printed): ft 3, ff 2, t 2, tf 3, f2 1. tf's end health
  (`health end try 2 fill,tri`) drew at its one try ("try N" is the stage's health count, not a
  retry): F2's cannot-tell rule on tf's end health is not met.
- Health after the session ok (closing29/r44-n3i-logs/health-r44-n3i-n1.log).
- [post hoc, infer] H-N is falsified (FF-N, T-N, TF-N, F2-N all failed). FF kept M1 after two
  fills, where one fill rewrote it in E1187: a client fill does not always write attribute 1.
  T and TF read the same word: the fill after a triangle left it. What decides whether a draw
  writes attribute 1, and the top byte's meaning, are open.
- Records: E1188 (wa), E1189 (ft), E1190 (wb), E1191 (ff), E1192 (wc), E1193 (t), E1194 (wd),
  E1195 (tf), E1196 (f2).
