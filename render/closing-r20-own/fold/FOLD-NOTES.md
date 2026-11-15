# r20-own fold notes (builder, 2026-11-15)

- Records: E1091 (ow + owt, Q191), E1092 (owp, Q192); spare E1093/E1094 belong to the lead.
- Moves: -112,-80 replaces the plan's -128,-96 (gen/cover.py: the plan's sits on macrotile edges).
- owt's kick rule is a register reading [infer]: a register value is not the store's time.
- Score: `python3 score/score.py STAGE out/ATT/STAGE`; ow's verdict and owp-30m (owpw) decide
  whose lists; Q192 retires (R20-4 a) if owp holds on both held-out P, the repeat holds and ow plus
  owpw agree.

## After the run (attempt 20261115-080117, rc 0, no fault, no empty copy)

- Scores re-run on the kept files byte for byte (fold/reproduce-ow.txt, -owt, -owp).
- ow: H-SECOND 0 of 3 FAILED; the rival H-OWNER fit all 3: page 6's lists are the moved cover
  exactly ({0,1,2,3,4,5,6,8,9,12} twice at -112,-80; {0,1,4,5,6,7,9,10,11,13,14} at 64,64), counts
  summing to 20 and 21, the owner's peak U (0x15, 0x16, regtimeline 0x0724) less 1. ow-c passed.
- owt: cannot tell (no row decided). 0x0694 and 0x0698 read 0 in every sample of every row (no task
  write seen), and the frozen owner base, words.101 rtds:11 0x20406000, is the base 0x062c holds
  during the second context's run; the owner's TA ran under 0x20006000 (post hoc:
  fold/timeline-stretches.txt, fold/stretches.py). 0x062c never returns to 0x20006000 after the
  second context's run starts.
- owp: H-REGIME 5 of 5 (raised 0x2c zero; not raised 0x30 E1084's 10 dwords twice, 0x34 one list,
  7; owp-30m E627 lists). owpw: H-SECOND 0 of 1 FAILED, H-OWNER fit: lists {1,2,3,5,6,9}, within
  the moved cover.
- Post hoc [infer]: not raised, the closed copy's lists and the after copy's lists together are the
  owner's cover (0x30: {0,1,2,4,5,6,8,9,13} + {2,6,7,10}; 0x30 moved: {0,1,4,5,8,9,12} +
  {1,2,3,5,6,9}; 0x34: {0,1,2,4,5,6,8,9,10,13} + {7}), so the after lists are the owner's.
