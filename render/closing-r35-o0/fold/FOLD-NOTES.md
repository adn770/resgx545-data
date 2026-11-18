# r35-o0 fold (E1143)

- One attempt, out/20261118-085126: 27 jobs of stage o on 2026-11-18 from 08:51:26, laptop at
  home (192.168.12.234, test kernel, module 7CE8E38EDB97FC5EA4F6C90), rc 0, no stop, fault or
  lead decision. fold/reproduce.out equals score-o.txt byte for byte; fold/q073-rule.out is the
  frozen rule: NARROW, nothing decided.
- Controls: 13 of 16 passed. Every A' at 64 x 64 stored A'(x, y) on 1062 of 1062 pixels (10 of
  10 rows); K and c1's P passed (P kept K on 426 of 1062, E417's count). The three A' rows at 128
  x 128 FAILED: 4269, 4254 and 4283 of 4284 pixels were A'(x, y). The frozen gate put c0a-a128
  in front of every h row, so every hypothesis row is cannot tell.
- Why the A' controls failed (post hoc, fold/posthoc.out): the construction is right (every
  other pixel matches); the 15, 30 and 1 wrong pixels sit in 4 x 4 blocks (x 100-103, y 44-47
  in all three; x 52-55 and 60-63, y 28-31 in h2a-a) and 40 of the 46 values are A' of
  another triangle pixel (26 to 64 columns to the left, often another row), 6 decode to no
  pixel. A hardware reading: at 128 x 128 a few pixels of the A' job itself store another
  instance's o0 [infer: the misplacement of E081's o1-o3 and E1139's aliasing]. The builder's
  error is the gate: it froze exactness at 128 x 128, which no kept record had shown (E081 ran at
  64 x 64 only; E417's constant colours cannot show a misplaced pixel), and gated the 64 x 64
  rows on it.
- Post hoc readings (not frozen, not decided): leftover pixels of P at 64 x 64 read A' of the
  same pixel (148 of 188 in h1b, h4a, h4b; 167 of 292 h1a; 148 of 279 h1c), of the pixel 32 rows
  lower (36; 85 in h1a; h1c also 59 at 16 rows higher) and of the pixel 32 columns right and 16
  rows higher (4); h1a and h1c also 36 pixels of 0xff00ff00, K's colour from two jobs back. The
  counts differ from E417's 390 to 450. h2 (P 64 after A' 128): no leftover pixel, 2 of 2. h3 (P
  128 after A' 64): 344 (68 same pixel, 36 at 64 columns left 16 up, 240 values A' never wrote)
  and 6 (same pixel). h4 (a reset between): the same 188 as h1b (kept). h5 (the fill between):
  651 pixels of the fill's colour, none of A'.
- Rerun r35-o0b (E1147) with the post hoc offsets frozen as the fit, the A' controls gating only
  their own groups and 128 x 128 checked against its own image.
- Replay refused (no simulator models o0 at the start of a pass).
