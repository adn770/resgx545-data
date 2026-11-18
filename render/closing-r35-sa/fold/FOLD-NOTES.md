# r35-sa fold (E1144, E1145)

- One attempt, out/20261118-085610: 63 jobs, stage a 08:56:11 (40 jobs), stage t 08:59:11 (23
  jobs) on 2026-11-18, the laptop at home (192.168.12.234), rc 0, no stop, fault or lead
  decision. fold/reproduce-a.out and fold/reproduce-t.out equal the attempt's score-a.txt and
  score-t.txt byte for byte; fold/q129-rule.out and fold/q193-rule.out are the frozen rules.
- Stage a (E1144): every control and every form control passed (c0, c1, c2). H-FOUR 21 of 21
  held out, H-UNION 2 of 2, H-ONEJOB 2 of 2; H-FIXED4 and H-SHIFT 0 of 19, H-VAR 0 of 6,
  H-UNTILWRITE 0 of 2. Q129 RULE: NARROW, clause (b) decided (H-ONEJOB), clause (a) open:
  the positions do not follow S0 + n d (S0 [0, 16, 512, 528], d 1 fitted on sa1).
- Post hoc [infer] (fold/posthoc.py, posthoc.out; formed after the run, decides nothing): every
  writer's 4 odd pixels are (x, y) = ((n & 1) + 2 (n >> 2) + {0, 16}, ((n >> 1) & 1) + {0, 8})
  for sa_n, 29 of 29 position sets (25 rows; W_157 three sets each), both replicates alike.
- Stage t (E1145): every kit control passed, but the reader form control (c, frozen as U reading
  T's marker in 2048 of 2048, E484/E593) FAILED on both rows: 2024 pixels read the marker and
  24 read 0x0000200f. So every U row is cannot tell and Q193 RULE decided no group. Not a
  decode error (the pixels agree with the o0 lines, c0/c1 passed in stage a): the frozen
  premise of the reader form did not hold on the hardware. Post hoc [infer]: every U row reads
  the last r20 writer's marker in 2023 to 2025 pixels and small values 0x0000n00f/0x0000n02f in
  23 or 24 pixels at even x in 0-14, 32-46 and even y in 0-6, 16-22, positions varying from row
  to row; after the --temps 8 writer (t4) 1388 pixels read its r4 marker 0x7e080604 and 637
  the T marker.
- Replay: refused (carried state; positions not modelled).
