# Scorer fix after the run (2026-11-11)

The round-3 scorer audit (2026-11-10) found three latent bugs in the frozen scorers
`score/score_t.py`, `score/score_f.py` and `score/score_c3.py`. None changes a verdict or a line
on the kept data. Fixed in this published copy only, as a disclosed post-run fix (decision D7 b,
2026-11-11), with the rule now in resgx545's `tools/closing/scorekit.py`.

- **C1, a void row inside the bracket decided a size (`score_t.evaluate`, q-t).** A size whose
  allowed point was a void row still counted as decided whenever the size had a first set point,
  so a void row inside (last clear, first set] could make an exact-point hypothesis REFUTED.
  Repro (the audit's `qt_void.py`): the q-t world H-INST with the 256x256 row at its allowed
  point void; the frozen scorer printed `H-INST ... REFUTED at 256x256`. Fix: a size is decided
  only if every allowed point lies at or below the last clear point, above the first set point,
  or on a usable row. On the kept data every allowed point was a usable row: no line changes.
- **C11, a void last point read as "not set" (`score_f.f1_verdict`, q-f1).** The unexplained
  case (neither b2 nor b8n sets by its last point and b4 never sets: H-MA and H-WD both
  refuted) was taken when the last point of b2 or b8n was void in both orders. Fix: the case
  needs the last point read clear in at least one order and set in none. On the kept data the
  case was not taken: no line changes.
- **C11, a vacuous control test (`score_c3.score_p_c3`, p-c3).** The swapped-order control
  `c-o4s-u` tested `ctl.get("c-e709", (False,))[0] is not None`, which is always true, so it
  could print PASS with c-e709 failing (the 5' class test still gated it). Fix: c-e709 must
  PASS. On the kept data c-e709 passed: no line changes.

Tests (written first: `tests/test_scorers_r3.py` and `tests/test_scorers_c3.py`, sections
"post-run fixes"): the C1 repro on the q-t world, the q-f1 world NEVER with b2's last point void
in both orders (and read clear: the unexplained case stands), and the p-c3 world with c-e709
failing (and passing). Against the frozen scorers three of them fail, as they should
(test_scorers_r3.py 62 ok and 2 FAIL, test_scorers_c3.py 34 ok and 1 FAIL).

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256` and
  `TOOLSRC.sha256` too. Every file the run wrote in `out/` is byte-identical.
- `out/20261110-160415/score-STAGE.txt` (p-c3, q-f0, q-f1a, q-f1b, q-t, q-v) and
  `out/verdict.txt` are the frozen scorers' output as printed after the run, kept.
  `score-STAGE.fixed.txt` and `out/verdict.fixed.txt` beside them are the fixed scorers' output
  on the same kept stages, byte-identical to the kept files in 6 of 6 stages and the verdict.
- `score/score_t.as-run.py`, `score/score_f.as-run.py` and `score/score_c3.as-run.py` are the
  frozen scorers, byte for byte (their hashes are the lines of `score/score_t.py`,
  `score/score_f.py` and `score/score_c3.py` in `FROZEN.pre-fix.sha256`); run with them under
  their frozen names on the kept stages, the session prints output byte-identical to the kept
  score files, the gate files and `verdict.txt`.
- `FROZEN.pre-fix.sha256` is the freeze the run used; `FROZEN.sha256` differs from it only in the
  lines of the three scorer files and the three new as-run lines (the lines of the other files
  were not regenerated; the tests are not in this freeze). `run/freeze_r3.sh verify` fails,
  before and after the fix, only on the absolute path of the landed `sgxfive-test.c`, which
  changed in resgx545 after the freeze (the pinned file is the blob at resgx545 0675ca0, as in
  R3k-pixel). With that file pinned the offline tests pass on a copy of this directory
  (`tests/run_all.sh`: test_gen 79 ok, test_scorers_r3 64 ok, test_scorers_c3 35 ok, mock_all
  374 commands accepted, run_mock 101 ok, guard clean). test_loops was not run: it builds a
  scratch Rust harness (`debug/simcheck`) that is not kept, and it tests the loop programs in
  the simulator, not the scorers.
- The audit's A1 (`score_v.consistent`) is not part of this fix.

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `score/score_t.py` | caf7df860d97013e | 3e1583c5c0162363 | yes |
| `score/score_f.py` | c74cfdea4ac2f39b | 94d0a63df1dd07a1 | yes |
| `score/score_c3.py` | 8f13ac970f0c18d2 | 39be0134db791181 | yes |
| `score/score_t.as-run.py` | (new) | caf7df860d97013e | yes |
| `score/score_f.as-run.py` | (new) | c74cfdea4ac2f39b | yes |
| `score/score_c3.as-run.py` | (new) | 8f13ac970f0c18d2 | yes |
| `tests/test_scorers_r3.py` | 6a87d11131e5f6bc | 86abdd439ced4a76 | no |
| `tests/test_scorers_c3.py` | 3bc7b2e6b47ce204 | 90faf8a27d6b2957 | no |
| `FROZEN.sha256` | 8a0fa9aa17bad7f1 | 2e3ea7b93b75dfae | (the freeze) |

## A second fix: `score_v.consistent` (A1, 2026-11-11, decision R4-6 a)

The audit's A1 was left out of the fix above because, unlike C1 and C11, it changes a verdict on
the kept data. It is fixed now, as a second disclosed post-run fix, the same way.

- **A1, a prediction was tested against the bracket widened by a ladder step
  (`score_v.consistent`, q-v).** The window predicted for a ladder's first set point was
  compared with the observed bracket (last clear, first set] widened on both sides by a slack
  of the bracket's width (the largest gap between the ladder's points when an end is open), an
  open end counting as 0 or infinity. Strict overlap is the rule (`tools/closing/scorekit.py`):
  a first set point in (lo, hi] can lie in the window [flo, fhi] when flo <= hi and fhi > lo,
  an open end is None, and there is no slack. Repro (the audit's `qv_strict.py`): the b4v
  ladder, bracket (None, 1760], window 2090..2200 of HV-INSTR (N8* 1045 to 1100 doubled): the
  window lies wholly above the bracket and the frozen scorer printed `consistent`; the other
  nine windows scored the same either way.
- **Fix.** `consistent` is the two-line strict overlap; its signature is unchanged (`ns` is
  no longer used).
- **One verdict changes.** The verdict of b4v HV-INSTR goes from consistent to REFUTED. It is
  printed twice in `score-q-v.txt`, so the fixed output differs from the as-run output in two
  places and in nothing else: in the b4v ladder line `HV-INSTR 2090..2200 ok` becomes `... MISS`,
  and in the `SUMMARY:` line (and so in `verdict.txt` line 17, the Q082-V line)
  `b4v HV-INSTR consistent` becomes `b4v HV-INSTR REFUTED`. E807's claim line (corrected
  2026-11-11) already records the reading with the b4v window above its bracket: the as-run
  line was the scorer's error and not a measurement. The other nine rows, the ladders' brackets,
  the controls and the other five stages are unchanged.

Test (written first: `tests/test_scorers_r3.py`, section "A1"): `consistent` on the b4v case and
on the strict-overlap edges (the first set point may equal hi, may not equal lo; an open end is
open); the as-run copy still says consistent there; the as-run scorer on the kept q-v records
prints the kept `out/score-q-v.txt` byte for byte, the fixed scorer prints
`out/score-q-v.fixed.txt` byte for byte, and the two outputs differ in exactly those two tokens.
Before the fix three of the checks failed (the b4v case, the strict edges and the one-verdict
difference; test_scorers_r3.py 67 ok and 3 FAIL), as they should.

- `predictions/`, `PREDICTIONS.sha256`, `TOOL.sha256`, `TOOLSRC.sha256`, every file the run wrote
  and `FROZEN.pre-fix.sha256` are unchanged; `out/20261110-160415/score-q-v.txt` and
  `out/verdict.txt` stay as printed after the run, kept.
- `score/score_v.as-run.py` is the frozen scorer byte for byte (its hash is the `score/score_v.py`
  line of `FROZEN.pre-fix.sha256`). `out/20261110-160415/score-q-v.fixed.txt` and
  `out/verdict.fixed.txt` are the fixed scorer's output on the kept q-v records (the verdict
  fixed file now differs from `out/verdict.txt` in that one token; the other five stage files
  stay byte-identical to the kept ones).
- `FROZEN.sha256` differs from the earlier fixed freeze only in the `score/score_v.py` line and
  the new `score/score_v.as-run.py` line.

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `score/score_v.py` | 621336de2daf8283 | 98ef7fcfef25e47b | yes |
| `score/score_v.as-run.py` | (new) | 621336de2daf8283 | yes |
| `tests/test_scorers_r3.py` | 86abdd439ced4a76 | 931dc472f5437cec | no |
| `out/20261110-160415/score-q-v.fixed.txt` | 270c2fc5c08bdd4b | 4cb762f324806435 | no |
| `out/verdict.fixed.txt` | a6e22ca540177e30 | 8952678c8b943685 | no |
| `FROZEN.sha256` | 2e3ea7b93b75dfae | 087a1dc9624a26b0 | (the freeze) |
