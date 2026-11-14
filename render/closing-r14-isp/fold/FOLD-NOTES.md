# r14-isp fold notes (builder; fold/ is outside the freeze)

Built 2026-11-14 by the r14-isp builder from resgx545 dddadbd, data 3309b5fd9, tool t10 (a581c06,
9bedc2d6...). Records: E1045 wind (Q241), E1036 g14 (Q261), E1037 clipr (Q199) (only these
numbers).

## For the fold (when resumed)

- Score: `python3 score/score.py STAGE out/ATTEMPT/STAGE`.
- wind: H-CULL vs H-KILL on the reversed order (3 rows); the z rows' READING (out-of-range dwords:
  count, distinct words) carries the clause whatever model holds. Predicted: H-CULL 3 of 3, zlo
  H-CLAMP, zhi H-RAW [infer]. Q241 narrows only (bit 18, the visibility counter, the polygon
  offset's units, the pass types, the gate pairs stay open).
- g14: Q261 retires (R14-6 a, the lead confirms) if H-VP holds on all 19 held-out rows with both
  controls PASS; the clause "clip space or window pixels" is then reworded as the viewport's box
  ([infer]: for w > 0 the two are one set). The READING family lines give the 128 x 128 x bound
  (160 expected) and the 64 x 64 lower x bound (a = 16 expected).
- clipr: Q199 retires (with R14-7's text fix: drop the negative-vertex clause, E683, Q260) if
  CLIP-HU (or exactly one rival) holds on the three tie rows, the 4096 x 16 rows draw IN-E607 and
  H-VP, and the int32 rows draw H-VP. The decisive-pixel counts per row say which pixels decided.
- sgx-pipe: `isp::guard_clip_image` past 64 x 64 and through a viewport (tables `g14`, `clipr`);
  the clip vertex's rounding; Q241's refusals for bits 15 to 17 and a depth outside [0, 1] if
  decided (table `wind`).
- Deviations (README.md): wind 8 jobs, z rows under compare always; 4096 x 16 not 4096 x 128;
  y ties at x = 5000 and -1000; the negative clip tie on x = 80; g14's aimed far vertices.
- Before publishing: delete `.pytest_cache` and `__pycache__`; debug/ is scratch.

## Freeze

Frozen 2026-11-14 (146 session files, 45 pins); `bash tests/run_all.sh` passed before and after
(debug/run_all1.log, run_all2.log).

## Run and fold (2026-11-14)

One attempt, out/20261114-060059 (driver rc 0; logs fold/run-r14i.log, fold/stage-r14i.log), no
stop, every job `job: ok` (the poked viewports and both int32 ends included), laptop healthy
after. fold/reproduce.out: the frozen scorer re-run on the kept files is byte-identical for the
three stages.

- wind (E1045): controls PASS. H-KILL 3 of 3, not the predicted H-CULL: each of bits 15 to 17
  removes the reversed triangle too. H-ZCLIP 2 of 2, not the predicted H-CLAMP (zlo) and H-RAW
  (zhi): the pixels past [0, 1] are removed (1600 of 3200 drawn), the background stored there.
  Q241 narrowed and its line reworded (own clauses only).
- g14 (E1036): controls PASS; H-VP 19 of 19 as predicted, every rival FAILED (H-TGT 16 of 19, on
  the vp rows). Families: 64 x 64 lower x -16 (not -9), 128 x 128 +x 160. Q261 retired (R14-6 a,
  the lead confirmed): the clause "clip space or window pixels" answered as one set for w > 0
  [infer].
- clipr (E1037): controls PASS; CLIP-HA 3 of 3, not the predicted CLIP-HU (2 of 3: the negative
  tie went away from zero); IN-E607 2 of 2 and H-VP 3 of 3 as predicted; SAT, WRAP, CULL 0 of 2.
  Q199 retired with R14-7's text fix (the negative sub-grid clause is Q260's).
- sgx-pipe: `isp::guard_clip_image_vp` and `guard_box` (the viewport-quarter guard on every
  target), the clip vertex rounded half away from zero; fold/rust_rows.py gives the 31 rows
  (`GUARD_R14`, every one drawn pixel for pixel; r13's 21 rows and the 47 kept counts still hold).
  Rows inline in isp.rs as r13-isp's were (no vectors table). Refusals that named Q199 or Q261
  name Q240, Q260 or Q230.
