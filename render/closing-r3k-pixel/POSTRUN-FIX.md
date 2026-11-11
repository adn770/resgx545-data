# Scorer fix after the run (2026-11-11)

The round-3 scorer audit (2026-11-10) found two latent bugs in the frozen scorer
`score/score_k.py`. One verdict line changes on the kept data: the Q003 line of k-bif (and of
`verdict.txt`), from `cannot tell: no held row could be read` to `none of H-W1C, H-CLR, H-RST: 4
of 4 held rows were read and match none of them` (C10, below). No other verdict changes. Fixed in
this published copy only, as a disclosed post-run fix (decision D7 b, 2026-11-11; the Q003 change
accepted by the user the same day), with the rule now in resgx545's `tools/closing/scorekit.py`.
The as-run output is kept beside the fixed output, and E826 already reads the four rows this way.

- **C2, a NODATA control let the held-out rows through (`f4_stage`).** `ctl_bad` left out a
  control that read NODATA, so the held-out rows of k-f4 kept AGREES with a control missing.
  Repro (the audit's `kf4_nodata.py`): delete the output of control `c3-64x64-k1` from a copy of
  the kept `k-f4/`; the frozen scorer still printed `8 of 8 held-out rows complete ...; controls
  {'c3-64x64-k1': 'NODATA', ...}`. Fix: any control that is not PASS (FAIL, NODATA or a row that
  did not run) makes every held-out row cannot tell, and the summary starts `cannot tell for the
  held-out rows: control c3-64x64-k1 NODATA`. On the kept data all three controls passed: no
  line changes.
- **C10, rows that were read called unread (`bif_stage`, `pb_stage`).** With every held row of
  k-bif read OTHER (a change after the writes that matches none of H-W1C, H-CLR and H-RST) the
  scorer printed `cannot tell: no held row could be read`: the rows were read. The fixed line
  says what was read and names any row that was not. In k-pb the H-OLD line said `2 of 2 jobs`
  whatever the second job read; it now counts the jobs behind each reading. k-pb did not run
  (its gate closed), so only the k-bif line changes. This is a verdict change on Q003: the frozen
  line said cannot tell, the fixed line says none of the three hypotheses fits. Both rest on the
  same four OTHER rows, and E826 states them.

Tests (written first, in `tests/test_scorers_k.py`, section "post-run fixes"): the audit's C2
repro on the f4 world, the k-bif OTHER world alone and with one row refused (NODATA), the k-bif
world with no row read (the old line stays), and the k-pb H-OLD world with one p4 job removed.

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `TOOL.sha256` and
  `TOOLSRC.sha256` too. Every file the run wrote in `out/` is byte-identical.
- `out/20261110-193547/score-STAGE.txt` (k-f4, k-pb0, k-bif) and `verdict.txt` are the frozen
  scorer's output as printed after the run, kept. `score-STAGE.fixed.txt` and
  `verdict.fixed.txt` beside them are the fixed scorer's output on the same kept stages.
- `score/score_k.as-run.py` is the frozen scorer, byte for byte (its hash is the
  `score/score_k.py` line of `FROZEN.pre-fix.sha256`); run on the kept stages it prints output
  byte-identical to the kept score files, `gate-k-pb.txt` and `verdict.txt`.
- `FROZEN.pre-fix.sha256` is the freeze the run used; `FROZEN.sha256` differs from it only in the
  line of `score/score_k.py` and the new line of `score/score_k.as-run.py` (the lines of the
  other files were not regenerated). `run/freeze_k.sh verify` fails, before and after the fix,
  only on the absolute path of the landed `sgxfive-test.c`, which changed in resgx545 after the
  freeze (the pinned file is the blob at resgx545 0675ca0); with that file pinned the offline
  tests pass on a copy of this directory (`tests/run_all.sh`: test_gen 33 ok, test_scorers_k 55
  ok, mock_all 23 accepted, run_mock 130 ok, guard clean).

The lines that changed (`diff out/20261110-193547/score-k-bif.txt
out/20261110-193547/score-k-bif.fixed.txt`; `verdict.txt` changes in its Q003 line the same way):

```
< SUMMARY: k-bif: Q003: cannot tell: no held row could be read ({'f1-ta-read': 'OTHER',
  'f1r-ta-read': 'OTHER', 'f2-ta-write': 'OTHER', 'f3-tex': 'OTHER'})
> SUMMARY: k-bif: Q003: none of H-W1C, H-CLR, H-RST: 4 of 4 held rows were read and match
  none of them ({'f1-ta-read': 'OTHER', 'f1r-ta-read': 'OTHER', 'f2-ta-write': 'OTHER',
  'f3-tex': 'OTHER'}); n0 PASS
```

(each line wrapped here; one line in the files). `score-k-f4.fixed.txt` and
`score-k-pb0.fixed.txt` are identical to the kept files.

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `score/score_k.py` | 94d6cd021a6a380c | e9d9570a6dcc6889 | yes |
| `score/score_k.as-run.py` | (new) | 94d6cd021a6a380c | yes |
| `tests/test_scorers_k.py` | fb9d6d9f13e7cc1b | 9cb8696610ba8c87 | no |
| `FROZEN.sha256` | 2ff760c33774cd3e | 872f218d08c4af42 | (the freeze) |
