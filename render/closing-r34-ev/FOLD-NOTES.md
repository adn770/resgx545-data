# r34-ev fold notes (builder)

- Built 2026-11-17 on main fd916fe (T1 kit forms), data 9a809796f. Records E1137 (Q111: e0, e1,
  e2c, e2) and E1138 (Q036: d0, d1).
- Deviations from plan 3.3/3.4: the overflow is the probe form of E1032/E1057 (t10,
  `expect:rc3-overflow`), not `tri --keep-overflow` at r32-kreg3's sizes (r32-kreg3 ran no
  overflow); the large copy
  is a 256 x 256 copy (t30's `--large-copy` is Q109's vm_large dump); no plain-triangle control
  (its bit 26 order shows in about half the jobs, E1121: a control that fails by chance); E547's
  6.1 us width bound is not frozen for bit 1 (E547's own tl-partial-r2-2 holds a 136 us bit 1).
- Calibration is per job form (score.calibrations: kitscore.calibration with the form's rows):
  the lint checks the register set only; a probe and a copy may sample at different intervals.
- At the fold: score each stage with its roots (`score.py e1 out/ATT/e1 out/ATT`), read the READ
  lines for the bit sets and widths; 0x0660's word after a probe persists through the reset (the
  next row's snap0), as r13-dpm showed.
