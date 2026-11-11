# Scorer fix after the run (2026-11-11)

The round-3 scorer audit (2026-11-10, C8) found two latent bugs in the frozen scorer
`score/score_geo.py`. Neither changes a verdict or a line on the kept data. Fixed in this
published copy only, as a disclosed post-run fix (decision D7 b, 2026-11-11), with the rule now
in resgx545's `tools/closing/scorekit.py`.

- **Containment instead of overlap (`ladder_verdict`, g-e1).** HP1 was printed `REFUTED by its
  limit` whenever the C interval of the shared step was not inside [0x2fe, 0x3de), also when the
  two overlap. Fix: refuted only when the two are disjoint; an overlap that is not inside prints
  `HP1 consistent (not decided)`. On the kept data g-e1's interval [0x35e, 0x37e) lay inside: no
  line changes.
- **A hang or a fault read as "completed as predicted" (`score_e2b`).** A boundary job's
  outcome was compared as "overflow or not", so a job that hung or faulted matched a `complete`
  prediction. Fix: only `ok` and `overflow` are outcomes; a hang or a fault makes the job void
  (`void (hang)`), and the stage line says cannot tell and names it. `score_e2b` is the fixed
  E2b scorer of the S1 analysis; this session has no g-e2b stage (`score/score_s1.py` does not
  list it), so it ran on no kept data here.

Tests (written first, in `tests/test_fixes.py`, section "post-run fixes"; S1's kept g-e2b as in
the other tests of that file): b-3a-hi made to hang in a copy of S1's `out/g-e2b` (void, not
`yes`; the stage line cannot tell, naming it), and `ladder_verdict` on a disjoint, an
overlapping and an inside step (the inside wording unchanged). Against the frozen scorer both
fail, as they should (12 of 14 fixes ok).

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256` and
  `TOOLSRC.sha256` too. Every file the run wrote in `out/` is byte-identical.
- `out/score-STAGE.txt` (g-e1, g-e3, g-e4w, g-e5, g-e8b, p-b2, p-c, p-d, p-f) is the frozen
  scorer's output as printed after the run, kept. `out/score-STAGE.fixed.txt` beside each is the
  fixed scorer's output on the same kept stage, byte-identical to the kept file in 9 of 9
  stages.
- `score/score_geo.as-run.py` is the scorer before the fix, byte for byte (its hash is the
  `score/score_geo.py` line of `FROZEN.pre-fix.sha256`); run on the kept stages it prints output
  byte-identical to the kept `out/score-STAGE.txt` in 9 of 9 stages.
- `FROZEN.pre-fix.sha256` is the freeze as published before this fix (after the rewording;
  `FROZEN.pre-reword.sha256` is the one the run used). `FROZEN.sha256` differs from it only in
  the line of `score/score_geo.py` and the new line of `score/score_geo.as-run.py` (the lines of
  the other files were not regenerated; the tests are not in this freeze).
  `run/freeze_s1.sh verify` passes.
- The offline tests kept in this directory pass on a copy of it: test_fixes.py 14 of 14,
  emit_checks.py 9 ok, mock_all.py 9 stages accepted, run_mock.sh 47 ok.

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `score/score_geo.py` | 115c81ca51059ad4 | 3b270bf584e22d93 | yes |
| `score/score_geo.as-run.py` | (new) | 115c81ca51059ad4 | yes |
| `tests/test_fixes.py` | 57faca1bd4139c32 | ca881415a839d04c | no |
| `FROZEN.sha256` | 04b65f63ce438412 | efa67cf5e1b4d2ca | (the freeze) |
