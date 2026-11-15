# r26-vol fold notes (builder, 2026-11-15)

- Record E1105 only. Q114: retire only under H-NOVOL 19 of 19 (no cannot tell) and R26-2 a,
  naming the bound (the never-run and faulting bits stay Q300's). If a bit acts: Q114 answered
  in part (that bit is the volume candidate), narrowed; its slice layout is the next row.
- Q300: append the 19 bits under smp3d to its note either way (own clause only).
- Score: `python3 score/score.py vc out/ATT/vc` and `python3 score/score.py vb out/ATT/vb out/ATT`
  (the root gives vb's headline vc's controls).
- Vectors: `closing_tables.py texture`, replay refused (README "Replay vectors"); a sim rule
  extension (smp3d as smp2d at the bits that held) is a sim change to report, not to make here.
- t0b27, t0b30: E564 read values that are no name of the buffer; their repeats decide whether
  their pair is decided.

## Fold (2026-11-15)

- Attempt 20261115-225136, rc 0, no stop or fault: vc controls 5 of 5 (both cube images), vb
  H-NOVOL 19 of 19 decided, no cannot tell (both repeats equal their w 0 job); the frozen scorer
  reproduces the kept scores byte for byte (fold/reproduce.out). E1105; Q114 retired under
  R26-2 a (separate commit); Q300 gains the 19 bits under smp3d.
- Post hoc, not frozen: 13 of the 19 bits leave the w 0 image equal to c-w0 at 2048 pixels; T0 27,
  30 and T3 10, 18, 27, 28 change it, and none of them makes w act either.
