# OD-2: one reader fix after the first run (2026-11-13, the builder)

`od2_band6.py` was frozen (`FREEZE-od2.sha256`, first block) and run once: `od2_band6.out`,
`od2_band6.as-run.json`. Its docstring says the cells are read "with `next` where `left` is the
artefact of (a)"; part (a) of that same run lists the artefact: at `m6-map-c1212-0x3cf` and
`m6-c0404-0x82` every sample of the first partial render reads the abort's count (6) and the first
sample after it reads 2 (the global list trimmed between two samples). The code tested
`left > gps_abort`, which never holds there (left = gps_abort = 6), so both cells were scored as
"6 pages left" and every candidate missed them. That is the only change:

- `observed()`: `next` replaces `left` where `left == gps_abort`, `left > 2` and `next < left`
  (the two cells of part (a) in m6; part (a) shows no other m6 row where left and next differ).
- `od2_band6.as-run.py` is the frozen script byte for byte (its hash is the first block's line);
  `od2_band6.out` and `od2_band6.as-run.json` are its output, kept.
- `od2_band6.py` is the fixed script (its hash in the second block of `FREEZE-od2.sha256`, written
  before its run); `od2_band6.fixed.out` and `od2_band6.json` are its output. The candidate family,
  the fit targets, the held-out targets and the 7-of-8 rule are unchanged.

What this costs: the fix was written after the first run's table was read, and in that table the
end H-NEXT1 gives (`after[b_6 + 1]`) already equals every target's first one-page cell, the two
artefact cells aside. So the fixed verdict is not a blind one: it is a FIT on the two mapped
targets and SEMI on the eight others (E936 printed their cells), as the plan said it would be. The
held-out test of the frozen candidate is stage m6b's four new targets.
