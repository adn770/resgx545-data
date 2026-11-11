# Scorer fix after the run (2026-11-11)

The round-3 scorer audit (2026-11-10, C8) found two latent bugs in the frozen scorer
`score/score_geo2.py`. Neither changes a verdict or a line on the kept data. Fixed in this
published copy only, as a disclosed post-run fix (decision D7 b, 2026-11-11), with the rule now
in resgx545's `tools/closing/scorekit.py`.

- **A hang or a fault read as "completed as predicted" (`score_u1`, g-u1).** A boundary job's
  outcome was compared as "overflow or not", so a job that hung or faulted matched a `complete`
  prediction; and a U job that hung or faulted stayed usable. Repro (the audit's `synth/g-u1`):
  b-2-m96-hi and u-m32 hung; the frozen scorer printed `want complete: yes` for b-2-m96-hi and
  counted both. Fix: only `ok` and `overflow` are outcomes; a hang or a fault makes the job void
  (`void (hang)`), listed and not counted. On the kept data no g-u1 job hung or faulted: no
  line changes.
- **Containment instead of overlap (`c1_verdict`, g-c1).** H-abs was printed `REFUTED by its
  range` whenever the C interval of the flip was not inside E753's range, also when the two
  overlap. Repro (the audit's `repro_overlap.py`): a flip giving C in [0x356, 0x36e) against
  [0x35e, 0x37e). Fix: refuted only when the two are disjoint; an overlap that is not inside
  prints `H-abs consistent (not decided)`. On the kept data the interval lay inside: no line
  changes.

Tests (written first, in `tests/test_scorers_r1.py`, section "post-run fixes"): the g-u1 world
with b-2-m96-hi and u-m32 hung, and c1_verdict on a disjoint, an inside and an overlapping
bracket. Against the frozen scorer three of them fail, as they should (test_scorers_r1.py 58 ok
and 3 FAIL).

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256` and
  `TOOLSRC.sha256` too. Every file the run wrote in `out/` is byte-identical.
- `out/score-STAGE.txt` (g-c1, g-c1f, g-t1, g-t2, g-t5, g-t6, g-t7, g-u1, g-u2, p-c2) is the
  frozen scorer's output as printed after the run, kept. `out/score-STAGE.fixed.txt` beside each
  is the fixed scorer's output on the same kept stage, byte-identical to the kept file in 10 of
  10 stages.
- `score/score_geo2.as-run.py` is the scorer before the fix, byte for byte (its hash is the
  `score/score_geo2.py` line of `FROZEN.pre-fix.sha256`); run on the kept stages it prints output
  byte-identical to the kept `out/score-STAGE.txt` in 10 of 10 stages.
- `FROZEN.pre-fix.sha256` is the freeze as published before this fix (after the rewording;
  `FROZEN.pre-reword.sha256` is the one the run used). `FROZEN.sha256` differs from it only in
  the line of `score/score_geo2.py` and the new line of `score/score_geo2.as-run.py` (the lines
  of the other files were not regenerated; the tests are not in this freeze).
  `run/freeze_r1.sh verify` passes.
- The offline tests pass on a copy of this directory (`tests/run_all.sh`: test_models 18 ok,
  test_gen 111 ok, test_templates 11 ok, test_gate 14 ok, test_scorers_r1 61 ok, mock_all 10
  stages, run_mock 69 ok). run_mock's two staging checks compare the landed tool source with
  `TOOLSRC.sha256`; `userspace/libsgxfive/tools/sgxfive-test.c` changed in resgx545 after the
  freeze, so they pass with the source pinned at resgx545 0675ca0 (`TOOL_SRC`) and fail on the
  live checkout. They do not run the scorer.

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `score/score_geo2.py` | ba0c40bf82f5550c | 80b9598f604934e4 | yes |
| `score/score_geo2.as-run.py` | (new) | ba0c40bf82f5550c | yes |
| `tests/test_scorers_r1.py` | c67fee605dadb858 | 1d7983f75b3c44f7 | no |
| `FROZEN.sha256` | c34d7e3494ab7dce | f042c686c660e877 | (the freeze) |
