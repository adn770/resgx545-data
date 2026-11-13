# r10-zls fold notes (builder; this file is frozen, post-run notes go to fold/)

- Records: E986 (zst2, Q120) and E987 (zbgc, zbg, zw: Q101). E988-E989 stay reserved for st1.
  Draft each with `tools/records/new_record.py --session DIR`; E985 (offline decode, SEMI) is the
  frozen rule set: cite closing10/seeds/q120/frozen_rules.md (sha256 86f0701a...).
- zst2: read z2x-f0's replicate line (E978 byte for byte or not) first. H-E985 counted only on
  held-out rows (y, d, e planes, x fills); z2x-f4 is a control and its layout line is E985's fit
  set. f7: decode post hoc in fold/ from the f4/f7 pairs of every plane and fill (READING lines).
  If H-E985 fails on the d plane only, look at f4's 0xf0 against depth first (its coding).
- zbg: if zbgc's gate shut, say why from the CONTROL lines (c25's background values, the triangle
  reading) and do not score zbg. A held rival on all six -0.25 rows retires Q101's background
  clause; with H-CLAMP0 vs H-CLAMP0P the f0-b19 row decides.
- zw: the off-mask region (x/512 + y/256 > 0.5) is a reading: fit it post hoc (E981's corner
  bend at 0.81) and say whether it moves with w.
- Delete any `.pytest_cache` and `__pycache__` before publishing; lead/w10_look.py needs numpy.
- sgx-pipe (fold, test first): zls formats 3 to 6 from E985/E986 if held; the background clear
  value below 0 from E987's held rival.
