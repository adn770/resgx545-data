# r45-n3j-n1 fold notes (folder, 2026-11-25)

- One attempt, out/20261124-210141, on module 079DD0D13F231EEAC52FE0F (fork r42-kernel
  ec6511d5de87, the one-shot boot of 2026-11-22; no rebuild or boot before N1-N4), the first
  session of round 45 (closing29/r45-n3j-logs/runone-N1.out, run rc 0). Session N1 of
  closing29/n3j/design.md (sections 3.1-3.3; the user's decisions A=a, B=a, C=a, D=b, E=c, F=a).
  Kit and blob: resgx545 94f9e501 (branch r45-n3j: K9, the command count from the kernel's
  `ccb_sent`, on main 1c8dc10e). Every stage runs emitsb_sbc43s with `form=sbc43` (sideband
  0xc43) at fw14.
- Every stage was scored by the driver (out/20261124-210141/score-*.txt) and rescored by hand
  with the frozen scorer (fold/reproduce-STAGE-20261124-210141.out): the same bytes for all
  eleven, and the same bytes as closing29/r45-n3j-logs/score-r45-n3j-n1-STAGE.txt.
- Plants wa, wb, wc, wd, we (row W, image mark, one job, T3 stops the tick, no gate, no end
  draws): every control passed; `Q128-N3J-WA/WB/WC/WD/WE RULE: W-QUIET, W-SA1, W-SA13`; every
  prediction held (W-FAULT failed as predicted). Job 1's post sa1 = M1 0x005d1000, sa13 = pa1 =
  M13 0x005d3000, K5 BIF_FAULT 0 before and after, snap9 0. KC: begin delta 10 (fill,tri), end
  delta 2 (none), each as expected.
- Reads (image crumb3, one job, no gate), each right after its plant; PLANT, DR and DK passed in
  each (the declared list at try 1, each draw exact; the `ccb_sent` count as expected):
  - ff2 (fill,fill; plant wa): post sa1 0x005d1000 = M1. `Q128-N3J-FF2 RULE: FF2-KEEP, X-QUIET`;
    every prediction held (FF2-FILL and FF2-TICK failed as predicted). KC 6.
  - t2 (tri; plant wb): post sa1 0x02400000. `Q128-N3J-T2 RULE: T2-SAME, X-QUIET`; every
    prediction held (T2-34, T2-KEEP failed as predicted). KC 8.
  - tf2 (tri,fill; plant wc): post sa1 0x02400000. `Q128-N3J-TF2 RULE: TF2-SAME, X-QUIET`; every
    prediction held (TF2-FILL, TF2-KEEP failed as predicted). KC 10.
  - tt (tri,tri; plant wd): post sa1 0x08400000. `Q128-N3J-TT RULE: TT-LAST, X-QUIET`; every
    prediction held (TT-FIRST, TT-KEEP failed as predicted). KC 14.
  - f3 (fill; plant we): post sa1 0x005d1000 = M1. `Q128-N3J-F3 RULE: F3-KEEP, X-QUIET`; every
    prediction held (F3-TICK, F3-FILL failed as predicted). KC 4.
  - f2b (fill, no plant, after f3's default end draws fill,tri, end KC 10): post sa1 0x05400000.
    `Q128-N3J-F2B RULE: F2b-QUIET, F2b-SAME`; every prediction held (F2b-TICK, F2b-FILL failed as
    predicted). KC 4.
  - The -OTHER outcomes (printed) read failed in every read.
- Every read: job 1 done, K5 BIF_FAULT 0 before and after, snap9 0. Post sa0 = V0 0x32004000, sa2
  = V2 0x32002000 (crumb3 writes both); post sa3-sa31 and pa0-pa15 equal word for word in all
  eleven stages, and equal to round 44's N1 (sa3 0x3f800000 ... sa12 3, pa0 3): only sa1 differs.
- Kernel "events seen" at each arm (printed): plants 3, ff2 2, t2 2, tf2 3, tt 4, f3 1, f2b 1.
  HKC (printed, never scored) names each list's entries: the read words are tt's second
  triangle's 3:22 at K 8 (0x08400000), t2's and tf2's first triangle's 3:22 at K 2 (0x02400000).
- Health after the session ok (closing29/r45-n3j-logs/health-r45-n3j-n1.log).
- [post hoc, infer] FF, T and TF read the same word a second time (FF2, T2, TF2); one fill after a
  plant kept M1 again (F3: now 2 of 3 crumb3 reads, F's 0x01000000 the other); an unplanted fill
  after a fill,tri end read 0x05400000 again (F2b, as F2). TT read the second triangle's word, so
  H-FIRST fails and H-TRI's prediction held.
- Records: E1201 (wa), E1202 (ff2), E1203 (wb), E1204 (t2), E1205 (wc), E1206 (tf2), E1207 (wd),
  E1208 (tt), E1209 (we), E1210 (f3), E1211 (f2b).
