# r21-zls fold notes (builder, 2026-11-15)

## Deviations from the plan (rank-round21 section 3)

- H-ZCOUNT's raised count is 184320, not the plan's 195584: window dwords only (the user's rule
  and the plan's own "window" regions). The plan's 195584 counted every dword below tile row 12,
  the pitch pad tile columns 32 and 33 included (11264 zero pad dwords in E1082's zs rows and in
  E1090's zq rows alike); its 118784 was already a window count. Both frozen counts are checked
  on the kept dumps (tests/test_plan.py test_zcount_on_kept).
- zregs2 (H-OFFS) is scored on zc-r25 from its first partial-render sample on (samples before it
  can be the previous job's: r20's zc-nl "before" samples), every sample with a non-zero
  0x0480-0x0488, at least one. It holds on E1088's zr rows (rd:12 0x1000, rd:13 0x341000) and
  fails against zc-geo's words (rd:13 0x311000).
- The plan's hook stop "a missing depth-store.2.bin twice in a row" is not built: the hooks only
  read the job's text (as r20), and a missing dump is the kit's kept check (REQUIRED). Premise
  and refill words stop a stage as in r20.
- norefill: zc-r25 is a control that declares `refill`, so a missing refill line is the kit's
  premise stop (25), not a hook stop (24).
- H-PRMASK's 80 % share: E1088's rows had one partial-render stretch of 7 to 15 samples with one
  rd:11 sample. r19-k0b's f0-up-h2-1 (P 0x24, the same triangle) had one stretch of 6 samples:
  one rd:11 sample there is 83 %, two would fail the frozen 80 % [infer: a risk on zl-24-nl only].
- zl, zw: H-PRMASK is scored in zl too (zl's seven rows, the plan's held-out samples), so each
  stage's headline carries it; both void unless zregs2 passes.

## For the fold

- Score: `python3 score/score.py STAGE out/ATT/STAGE out/ATT` (zl and zw read zregs2 from
  ROOT/zc).
- zl's READING lines carry the lo zero counts of store.2 and depth.2 (Q107, E1088's 65246 and
  183107) and the final's target check.
- Records: E1093 (zc, zl), E1094 (zw), E1095 (zz), E1096 spare; the E1090 correction and the Q107
  line (plan section 4) go in this fold without a number.
