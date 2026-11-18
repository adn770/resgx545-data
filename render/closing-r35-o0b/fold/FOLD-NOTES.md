# r35-o0b fold (E1147)

- One attempt, out/20261118-091726: 32 jobs of stage o on 2026-11-18 from 09:17:27, laptop at
  home (192.168.12.234, module 7CE8E38EDB97FC5EA4F6C90), rc 0, no stop, fault or lead decision.
  Every control passed (18 of 18; the 128 x 128 A' rows 4272, 4274 and 4275 of 4284 A'(x, y),
  over the frozen 98 %). fold/reproduce.out equals score-o.txt byte for byte; fold/q073-rule.out
  is the frozen rule: NARROW, (a) DECIDED (H-OFFSETS), (b) not decided.
- (a), held out on 4 of 4 h1 rows: the kept pixels read A' at (0, 0) (130 to 287), (0, 32) (36
  or 85) and (32, -16) (0 or 4), and h1a 36 EARLIER pixels; (0, -16) of E1143's h1c did not recur.
  H-SAMEPIX held on h3b only (6 pixels at (0, 0)); H-OTHER FAILED on all 4.
- (b): h2 split (h2a 0 kept, h2b 12 kept at (0, 80), an offset outside E1143's set); h3a kept
  nothing (cannot tell), h3b 6 at (0, 0). Not decided.
- Lifetime: a debugfs reset between keeps them (h4: 414 and 323 pixels, all A at (0, 0) or
  (0, 32)); the t10 fill between replaces every kept pixel with its colour (h5: 651 and 651).
- Counts (R35-2, body): h1 206, 372, 262, 188; h4 414, 323; E417's 390 to 450.
- Replay refused: cross-job state (an earlier job's o0 at a pixel), no simulator keeps it; E1147
  in SIM_UNMODELLED.toml.
