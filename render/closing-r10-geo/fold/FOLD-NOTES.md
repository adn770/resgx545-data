# r10-geo fold notes (builder, 2026-11-13)

Outside the freeze (fold/). For the fold, when the lead resumes the builder with the run.

- Records: E1005 (pivot, Q261), E1006 (bgw, Q066), E1007 (q139c, Q139); E1008 is far2's (not
  here). 4-digit E-numbers need r10-tooling2's support before the fold lands. Draft each method with
  `tools/records/new_record.py --session DIR`.
- pivot: carry the per-triangle READING lines (the D interval) and the H-PIVOT / H-CONSTD / H-ANGLE
  summaries. If a triangle's rows do not meet (H-PIVOT FAILED), read the per-row D sets post hoc
  (a staircase: D depends on d, e.g. a quantised slope) - not frozen. sgx-pipe: `isp.rs`
  far_coverage_image keeps the band `None` unless D is pinned; then a pivot rule with a test beside
  E979_ROWS. Seeds finding 4 / E984 (offline band reading) is the prior record to cite.
- bgw: H-INERT vs H-SCALE0 per word (TALLY lines). sgx-pipe `bglayer::check` admits the values
  that held (with the rule) and keeps refusing the rest; replay via bg_layer_table.rs.
- q139c: H-LAST on the four new dumps is its first held-out test (E959 was post hoc). Untouched
  set for later: r7-rp's 21 q139 dumps were never read for the flag (only for slots, E907).
- Restate README "Deviations" 1 to 5 in the records (d range, bgw values, the two dumped words,
  no H-EVENY, order).
- Delete any `.pytest_cache` before publishing.

## After the freeze (builder, 2026-11-13)

- The scaffold's tests/run_all.sh (kit 9849dab template) runs pytest without
  `-p no:cacheprovider`, so a run leaves `.pytest_cache/` in the session root, which `verify` (and
  so `stage`) refuses as new files. The freeze is kept as is (never rewritten): run the offline
  tests as `PYTEST_ADDOPTS="-p no:cacheprovider" bash tests/run_all.sh`, or delete
  `.pytest_cache/` before `kit/session.py stage .`. Tooling item: the template should pass the flag
  (r10-x, r9-k1 and r9-lgeo added it by hand).

## Fold (builder, 2026-11-13)

- Attempt 20261113-103256, rc 0; fold/reproduce.sh: every score byte-identical, every kept file
  matches the laptop's sha256. Lead log copied to out/20261113-103256/run.log.
- Branches: resgx545 r10-fold-geo (closing10/r10-geo-fold/wt), data r10-fold-geo-data
  (closing10/r10-geo-fold/wt-data); own CARGO_TARGET_DIR closing10/r10-geo-fold/target-own.
- pivot: x24p D in (339.4, 467.4) px; x23p, x25n D > 586 (never flipped): H-CONSTD and H-ANGLE
  refuted; band stays undetermined in sgx-pipe (E1005_ROWS test), pivot table refused.
- q139c: ta::macrotile_slots (R7-BLK + flag list end) replays the q139c table; bgw: bglayer admits
  the measured finite values; bg_layer_table.rs replays r10-geo bgw.
