# Scorer fix after the run (2026-11-11)

The round-3 scorer audit (2026-11-10, C8) found two latent bugs in the frozen scorer
`score/score_r3.py`. Neither changes a verdict or a line on the kept data. Fixed in this
published copy only, as a disclosed post-run fix (decision D7 b, 2026-11-11), with the rule now
in resgx545's `tools/closing/scorekit.py`.

- **"No raise" refuted LT whatever the cells (`score_c4`, g-c4).** With no raise in any valid
  cell the scorer printed `the flip is below the bracket (LT REFUTED)` unconditionally. LT's last
  raise is 0xd4: silent cells all above 0xd4 do not contradict it. Fix: LT is refuted only when a
  silent cell lies at or below 0xd4; otherwise the line says `cannot tell` (and `no valid cell:
  cannot tell` with no valid cell at all). The verdict moved into `c4_verdict`, with every other
  wording unchanged. On the kept data g-c4 found an exact flip (0xe2 / 0xe3): no line changes.
- **A bracket's low end taken as the exact flip (`score_c6`, g-c6).** H-target predicts a raise
  at or below g-c4's last raise and none at or above its first silent cell; the scorer predicted
  "none" for every cell above the last raise, so with a g-c4 bracket (not an exact flip) a cell
  inside the bracket was scored against a value H-target does not give. Fix: such a cell is not
  decided for H-target and is named (`... decided cells as g-c4's bracket (lo, hi); [cells]
  inside it not decided`); with every valid cell inside it the line says `cannot tell`. The
  verdict moved into `c6_verdict`. On the kept data g-c4's flip was exact, so no cell lies
  inside: no line changes.

Tests (written first, in `tests/test_scorers_r3.py`, section "post-run fixes"): `c4_verdict` on
"no raise" with every silent cell above 0xd4, with one at or below it, with no valid cell, and on
an exact flip (wording unchanged); `c6_verdict` with a raise inside g-c4's bracket, with one
decided cell, with every cell inside, and with an exact flip (wording unchanged). The two
functions are new, so against the frozen scorer the test file stops at the first of them
(51 ok before it).

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256` and
  `TOOLSRC.sha256` too. Every file the run wrote in `out/` is byte-identical.
- `out/score-STAGE.txt` (g-c4, g-c5, g-c6, g-c7, g-d36, g-da, g-db, g-dc, g-dd) is the frozen
  scorer's output as printed after the run, kept. `out/score-STAGE.fixed.txt` beside each is the
  fixed scorer's output on the same kept stage, byte-identical to the kept file in 9 of 9
  stages.
- `score/score_r3.as-run.py` is the scorer before the fix, byte for byte (its hash is the
  `score/score_r3.py` line of `FROZEN.pre-fix.sha256`); run on the kept stages it prints output
  byte-identical to the kept `out/score-STAGE.txt` in 9 of 9 stages.
- `FROZEN.pre-fix.sha256` is the freeze as published before this fix (after the rewording;
  `FROZEN.pre-reword.sha256` is the one the run used). `FROZEN.sha256` differs from it only in
  the line of `score/score_r3.py` and the new line of `score/score_r3.as-run.py` (the lines of
  the other files were not regenerated; the tests are not in this freeze).
  `run/freeze_r3.sh verify` passes.
- The offline tests pass on a copy of this directory (`tests/run_all.sh`: test_models_r3 17 ok,
  test_gen_r3 137 ok, test_templates_r3 3 ok, test_scorers_r3 59 ok, test_awk_reader 4 ok,
  mock_all 9 stages, run_mock 73 ok).

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `score/score_r3.py` | d0af9cb0ab73dee7 | da391b0625be212f | yes |
| `score/score_r3.as-run.py` | (new) | d0af9cb0ab73dee7 | yes |
| `tests/test_scorers_r3.py` | ddd3d27e97f0c267 | d069146f7480c740 | no |
| `FROZEN.sha256` | 7fabb92b4d88de3f | 7fe5f16c4b5e2ddc | (the freeze) |
