# r13-isp fold notes (builder; fold/ is outside the freeze)

Built 2026-11-13 by the r13-isp builder from resgx545 05b7039, data 75d01ee20, tool t10
(a581c06, 9bedc2d6...). Records: E1022 q201, E1023 q261, E1024 far (only these numbers).

## For the fold (when resumed)

- Score: `python3 score/score.py STAGE out/ATTEMPT/STAGE out/ATTEMPT` (far with the attempt
  root prints q261's family readings beside its own).
- q201: H-SAMPLE0 18/18 with E1018 coverage would retire Q201 (R13-9: the lead confirms). Then
  sgx-pipe `iter::sample_point` can lift its refusal (Q201) with a test on the `q201` table, and
  E1018's "[infer]" on the position source becomes HW (appended correction/note only).
- q261: READING lines give the surviving G, a, g; H-REL vs H-ABS from the 128 x 128 rows. Q261
  retires only if one value of each family fits every row and the controls pass (R13-9).
  sgx-pipe `far_coverage_image` keeps the band `None` unless the fold models the clip.
- far: if every row is `job: ok` and H-CLIP holds to 2^30, Q199 retires with Q261 (plan); a
  fault/hang at the first held-out row is itself the Q199 reading (stage stopped, rc 4).
- Deviations (README.md): q201 23 jobs (x/y per job); new -y and 128 x 128 vertices (c6's far-y
  depend on the x guard); far vertices' second coordinate designed; H-PIVOT only on 64 x 64 +-x.
- Before publishing: delete `.pytest_cache` and `__pycache__`; debug/ is scratch.

## Freeze

Frozen 2026-11-13: FROZEN.sha256 dedc5a1d... (160 session files, 25 pins), PREDICTIONS.sha256
7d20451f...; `bash tests/run_all.sh` passed before and after (debug/run_all1.log, run_all2.log).

## Run and fold (2026-11-13)

One attempt, out/20261113-215416 (driver rc 0; logs fold/run-r13i.log, fold/stage-r13i.log), no
stop, every far job `job: ok`, laptop healthy after. fold/reproduce.out: the frozen scorer re-run
on the kept files is byte-identical for the three stages.

- q201 (E1022): every control PASS; H-SAMPLE0 18 of 18, E1018's coverage 18 of 18; H-CENTRE and
  H-SWAP 0 of 18, H-SPLIT 8 of 18 (the source-0 rows only). Proposed: retire Q201.
- q261 (E1023): controls PASS; H-CLIP 14 of 14, H-CLIP-ONE: G = 16 (x <= 80 on 64 x 64, from E1012's
  16..22), g = 16 (y in [-16, 80]), a in {9, 16}; 128 x 128: G = 19 only among the frozen 16..22,
  so H-REL (one G on both targets) and H-ABS FAILED. Post hoc (fold/posthoc_bounds.py, after the
  scores): integer bounds that fit every row are x <= 80 or 103 (64), 147, 160, 173 or 186 (128),
  x >= -9 or -16, y >= -16, y <= 67, 80, 81, ...; one rule, a quarter of the target past each edge
  (clip x, y within +-1.5 w), draws all 24 rows (QUARTER 24 of 24) and is c6's clip[-16, 80] on
  64 x 64 (all 48 kept rows). Proposed: narrow Q261 (the guard on other targets, post hoc).
- far (E1024): far-ctl PASS, x25n replicate held; H-CLIP 7 of 7 (G = 16, g = 16), H-EXACT-BAND
  6 of 6, H-SAT, H-WRAP, H-CULL 0 of 6, H-F32 5 of 6 (far-y28p, a band pixel). Q199 narrowed, not
  retired: no saturation, wrap or removal to 2^30 px (the far vertex reaches the format only as a
  clip vertex [infer]), but its negative sub-grid rounding (E683, Q260), the 4096 target and the
  envelope refusals sgx-pipe names Q199 for stay open.

## Fold (decisions)

- Q201 retired (answered by E1022); Q261 and Q199 narrowed and reworded. Guards: G = 16 (x <= 80),
  g = 16 (y in [-16, 80]), a in {9, 16}; 128 x 128 x <= 147 (frozen range), quarter rule post hoc.
- sgx-pipe: `isp::guard_clip_image` (64 x 64, rows of fold/rust_rows.out) and
  `iter::sample_point` returning byte 0's point.
