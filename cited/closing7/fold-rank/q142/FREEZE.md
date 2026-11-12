# Q142 freeze (round 7 fold r7-fold-rank, 2026-11-12)

Frozen before te-m2-20-128x128 (the input) and te-m2-e0-128x128 (held out) of E504's dumps were
opened by this fold. The round 7 ranking's `closing7/rank/q142_diff.py` printed a run summary of
the held-out TA-data diff into `q142_diff.out` (its last line); the ranking says it read only the
first 6 lines of the 128 x 128 parameter diff, and this fold has not read that file past the
64 x 64 sections.

- Model: `q142_grid.py` (H-GRID and the H-HALF control, rules in its header).
- Fit: `q142_fit.py` on the nine 64 x 64 pairs of E504 (`q142_fit.out`): H-GRID 0 of 6144 TA-data
  dwords off and streams = opened blocks in 9 of 9; H-HALF off in the 6 pairs with bit 30 or 31.
- Prediction: `q142_grid.py predict <data> te-m2-20-128x128 128 128 0xe0000000 pred-e0-128`,
  then `q142_score.py <data> pred-e0-128 te-m2-e0-128x128 <self-check>`.
- Held: 0 of 6144 TA-data dwords differ and the predicted streams are exactly the 0x80-byte blocks
  the held-out parameter dump opens in [0x2000, 0x100000). Refuted: any dword or block off.
- Control that can fail: H-HALF must FAIL on the held-out job, and the 0x20000000 model must give
  the 128 x 128 input back (0 dwords off); else the headline is cannot tell.
