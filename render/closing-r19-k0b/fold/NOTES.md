# r19-k0b fold notes (post hoc, outside the freeze)

- Reproduction: `python3 score/score.py STAGE out/20261114-224248/STAGE out/20261114-224248` for k0,
  kg, f0 gives the kept score files byte for byte (fold/score-*.txt).
- [post hoc] H-UPD's 4 FAILED rows are f0-down-1/2's ovf2 and nparts: the final did not overflow.
  `python3 fold/timeline.py out/20261114-224248/f0` (fold/timeline.out): at both f0-down rows
  0x0624 took 0xe (N 0x30 - 0x22) at the final's kick, with 19 pages held, and the page count never
  passed 19 after it (the second triangle is the first's: it took no new page). The prediction
  rested on an assumed 5 more pages for the second triangle ([infer] in gen/plan.py); with no
  allocation after the threshold fell below the pages held, no abort was due, so f0-down does not
  test whether the kick's TA follows N. The register reading is H-UPD's on every row.
- [post hoc] H-LATE's 26 held are its predictions equal to H-UPD's (thr2 = N - 0x22 everywhere)
  plus f0-down's no-overflow; its own claim (N's thresholds loaded only at a later kick) is
  against the timeline: 0x0624 takes N - 0x22 at the final kick itself, in every f0 row, before
  that render ends (the up rows: about 900 ms after the job's start, then up to 19 or 20 pages
  with no abort). And its behavioural claim (the final follows P) fails against the knob-0 twin:
  kg's k0-geo rows (P 0x28, no final PB) overflow in the final too (ovf2 1, 2 partial renders in
  the job, 0x0624 raised to 0x26), while f0-up-1/2 (P 0x28, N 0x100, the same geometry kick by
  H-GEO0) complete the final with no partial render. The frozen H-LATE values left the up rows'
  ovf2 unpredicted (the twin was to be read), so this is post hoc. The controls read only 0x0624
  and the overflow, so they pass under both.
- H-STORE 12/12: pb:10-13 after the final hold (list + 0x10, N - 0x22, N - 0x22, PDS(N)): the EDM
  stores the command's thresholds into the PB descriptor. H-STICK 0/4: f0-back's next scene runs
  at P's 0x6 again and overflows (render 3: 1 partial render).
- Not predicted, read: f0-up's final image is exact (diff 0), not short of the triangle (E038's
  expectation).
- k0-a0's param dump here has the plain sha256 2643d77d... of r19-k0's stopped run: the same 4
  dwords at 0x12de30 to 0x12de3c read 0 again (both runs a0 third, after the same two jobs), so
  the tail is reproducible on this module; the masked control and the tadata dump match r10-dpm.
