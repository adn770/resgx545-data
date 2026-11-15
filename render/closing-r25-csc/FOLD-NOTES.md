# r25-csc fold notes

- Built 2026-11-15 from resgx545 7f214e5, data 40050d0ac; record E1103 (rank-round24.md 5).
- Frozen before the run: H-FILLLOAD (fit b, c; held out e, f) against H-FILLIGNORE; E1097's post
  hoc reading (a fill loads) is H-FILLLOAD and is held out by e and f (BT.601 copy, zeros poke).
- Deviation: 16 jobs, one copy per half; a and d are the controls of the state b and e start from.
- Fold: Q181 retires on either verdict with its half's controls passed; a failed control half is
  cannot tell for that half only (score.py HALF_CONTROLS). Append Q050's YUV-clause note (formats
  28 and 29 do not read black in a fill on t22, E1097; corrected E568).
- Replay: csc rows after a load are refused by sgx-sim until a kept set is modelled.
