# Scorer fix after the run (2026-11-11)

The round-3 scorer audit (2026-11-10) found two latent bugs in the frozen scorer
(`score/score_r3.py`, `score/sc_ring.py`, `score/sc_e3.py`). Neither changes a verdict on the kept
data; one changes the wording of the kb and e3b summary lines. Fixed in this published copy only,
as a disclosed post-run fix (decision D7 b, 2026-11-11), with the rule now in resgx545's
`tools/closing/scorekit.py`.

- **C3, a K0 headline printed with no data (`score_defaults`, `score_tool`).** The headlines
  `defaults as designed` (k0f) and `both jobs as L1 and L2 kept them` (k0t) were printed whenever
  no control row FAILED, so also when no row was read at all. Repro (the audit's `k0_nodata.py`):
  delete every job record from a copy of the kept `k0f/` or `k0t/`; the frozen scorer still
  printed the headline with every row cannot tell, and exited 0. Fix: the headline is printed only
  when at least one row decided and every control row decided; otherwise the summary starts
  `cannot tell: no row decided` or `cannot tell: N of M control rows cannot tell (JOBS)`. A FAILED
  control still prints `DEFAULTS DIFFER` / `CONTROL DIFFERS` first, as before. On the kept data
  every row of k0f and k0t decided: no line changes.
- **C9, verdict lines that did not say how little they rest on (`score_kicker`, `score_e3b`).**
  kb printed `consistent with ['H-LATCH', 'H-HWC']` from one decided held-out row (q1, with its two
  replicates) of four, a reading on which both hypotheses predict the same value. The fixed line
  adds the count of decided held-out rows, the replicates, and, when the standing hypotheses
  agree on every decided reading, that the readings do not separate them. e3b printed H-STOP3
  (and the refuted list) from one stopped job, b1, which has no replicate (b2 was not run by its
  rule); the fixed line adds `in 1 run (b1; one run, no replicate)`. A wording change: the
  verdicts, the tallies and every job line are unchanged.

Tests (written first, in `tests/test_scorer.py`, `test_postrun_fixes`): the audit's C3 repro on
copies of the kept k0f and k0t (every job record deleted; and k0t with the px record deleted), the
kept data keeping both headlines, the kept kb and e3b stages printing the new wording, and the kb
H-LATCH world (one standing hypothesis: no "do not separate").

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256`,
  `TOOLR1.sha256`, `LAPTOP-k0.sha256` and `LAPTOP-kev.sha256` too. Every file the run wrote in
  `out/` is byte-identical.
- `out/score-STAGE.txt` (11 stages: k0f, k0t, k0c, k0h, f, t, kb, e2b, e3h, e3a, e3b) is the
  frozen scorer's output as printed after the run, kept. `out/score-STAGE.fixed.txt` beside each
  is the fixed scorer's output on the same kept stage.
- `score/score_r3.as-run.py`, `score/sc_ring.as-run.py` and `score/sc_e3.as-run.py` are the
  frozen scorer's three files, byte for byte (their hashes are the lines of `score/score_r3.py`,
  `score/sc_ring.py` and `score/sc_e3.py` in `FROZEN.pre-fix.sha256`). `score_r3` imports the
  other two by module name, so the frozen scorer is run with the three as-run files under their
  frozen names (`scorelib.py` and `sc_e2b.py` did not change); so run on the kept stages it
  prints output byte-identical to the kept `out/score-STAGE.txt` in 11 of 11 stages.
- `FROZEN.pre-fix.sha256` is the freeze before the fix, byte-identical to the one the run used
  (`FROZEN.pre-reword.sha256`, see `REWORDED.md`); `FROZEN.sha256` differs from it only in the
  lines of the three scorer files and the three new as-run lines (the lines of the other files
  were not regenerated). `run/freeze_r3.sh verify` passes, and the fixed scorer ran under it. The
  offline tests pass on a copy of this directory (`tests/run_all.sh`, before and after the fix:
  guard clean, freeze verified, sim_r3.py passed, test_scorer.py 91 ok before and 99 ok after,
  test_guard.py 79 ok, run_mock.py 12 of 12 tests and 134 ok).

The lines that changed (`diff out/score-STAGE.txt out/score-STAGE.fixed.txt`; each line wrapped
here, one line in the files; the shared tail of each line is cut at `...`):

```
< SUMMARY: kb: Q0 held (ticks K = 2); consistent with ['H-LATCH', 'H-HWC'], refuted ['H-KW'];
  stops 0 []; Q290 rows: ...
> SUMMARY: kb: Q0 held (ticks K = 2); consistent with ['H-LATCH', 'H-HWC'] (1 of 4 held-out rows
  decided: q1; replicates q1-r2, q1-r3; the decided readings do not separate them), refuted
  ['H-KW']; stops 0 []; Q290 rows: ...
< SUMMARY: e3b: H-STOP3 (a skipped end-of-render handler stops the tick); stops 1 ['b1']; Q111
  rows: ...
> SUMMARY: e3b: H-STOP3 (a skipped end-of-render handler stops the tick) in 1 run (b1; one run,
  no replicate); stops 1 ['b1']; Q111 rows: ...
```

The other nine `score-STAGE.fixed.txt` files are identical to the kept ones.

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `score/score_r3.py` | 41b78851d978f246 | 1e429c9a07832ce5 | yes |
| `score/sc_ring.py` | 5326b4f12a96fcb5 | b2cf5838eaceb49a | yes |
| `score/sc_e3.py` | 386a170e028ad45e | 9b93bc0e4edb356b | yes |
| `score/score_r3.as-run.py` | (new) | 41b78851d978f246 | yes |
| `score/sc_ring.as-run.py` | (new) | 5326b4f12a96fcb5 | yes |
| `score/sc_e3.as-run.py` | (new) | 386a170e028ad45e | yes |
| `tests/test_scorer.py` | 674d647b05bcd5c3 | 6c8b744cf678ca78 | no |
| `FROZEN.sha256` | 1d6a3ad2360f639b | a462a7e3f11b44fc | (the freeze) |
