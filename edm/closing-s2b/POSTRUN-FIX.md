# Scorer fix after the run (2026-11-11)

The round-3 scorer audit (2026-11-10) found two latent bugs in the frozen scorer
`score/score_s2.py`. Neither changes a verdict on the kept data; one changes the wording and the
entry counts of the e5t job lines. Fixed in this published copy only, as a disclosed post-run fix
(decision D7 b, 2026-11-11), with the rule now in resgx545's `tools/closing/scorekit.py`.

- **C4, e5t read the host's kicks as the job's events (`score_e5t`).** The held rows counted
  every ring entry of the four slots, the host's GETMISCINFO kick entries of slot 0 included,
  and called a held job QUEUED when every entry came after the exit and the first within 5000
  units of it: a window open above. The no-hold control "event entries >= 1" counted the kicks
  too, so it could not fail. Repro (the audit's `synth_e5t.py`): erase slots 1 and 3 (the job's
  events) in every e5t record of a copy of the kept `out/e5t/`; only the kick entries remain, and
  the frozen scorer still printed QUEUED three times with its control passed. Fix: the job's
  events are the entries that are not a kick and not a plain tick (`job_events`); QUEUED needs
  every one of them in [0, 5000] units after the exit (`e5t_reading`), and the control counts
  them. On the kept data each job has 3 job entries (slot 1 one, slot 3 two, 2338 to 4133 units
  after the exit) and 6 kick entries: the verdicts and the `SUMMARY` line are unchanged, the
  five job lines now give the job's count and the kicks left out.
- **C8, ALL within one tick taken for ALL (`hold_shape`).** A burst one short of the held ticks
  read ALL (`|q - floorH| <= 1`), but it is also PARTIAL(q): at H = 5 a burst of 4 is exactly
  what the cap min(H, 4) predicts. The same held in the ring-full branch (`qmin < floorH - 1`).
  Fix: q = floorH - 1 reads `ALL-or-PARTIAL(q)` (and the ring-full branch says
  ALL-or-PARTIAL for any qmin below floorH). The cap verdict reads q, not the shape, so it does
  not change; on the kept data every burst is H or the cap (H 1 to 4 and 6, 90): no line changes.

Tests (written first, in `tests/test_scorer.py`, section "post-run fixes"): the audit's C4 repro
on a copy of the kept `out/e5t/` (QUEUED kept, then gone with the control failed once slots 1 and
3 are erased), a job event 90000 units after the exit (OTHER), no job event (LOST?), a kick
entry left out of the job's events; for C8 a 5-tick hold with 4 and with 5 entries after the
exit. Two older checks asserted the old rule (`three of four at the exit: ALL` and `3 held, 2
after the exit` read ALL); they now expect `ALL-or-PARTIAL(3)` and `ALL-or-PARTIAL(2)`. Every
check of a C4 or C8 failure fails on the frozen scorer (the 5-tick hold with 5 entries reads ALL
in both).

- `predictions/` and `PREDICTIONS.sha256` are byte-identical to the run's; `LAPTOP.sha256` too.
  Every file the run wrote in `out/` is byte-identical.
- `out/score-STAGE.txt` (e4c, e4m, e4l, e5c, e5t) is the frozen scorer's output as printed after
  the run, kept. `out/score-STAGE.fixed.txt` beside each is the fixed scorer's output on the
  same kept stage (with `--gate` for the four gated stages, as `run/s2.sh` ran them).
- `score/score_s2.as-run.py` is the frozen scorer as published, the reworded one of
  `REWORDED.md`, byte for byte (its hash is the `score/score_s2.py` line of
  `FROZEN.pre-fix.sha256`); run on the kept stages it prints output byte-identical to every
  kept `out/score-STAGE.txt` (5 of 5).
- `FROZEN.pre-fix.sha256` is the freeze before this fix (the one regenerated after the
  rewording; the run's own is `FROZEN.pre-reword.sha256`); `FROZEN.sha256` differs from it only
  in the line of `score/score_s2.py` and the new line of `score/score_s2.as-run.py` (the lines of
  the other files were not regenerated). `run/freeze_s2.sh verify` fails, before and after the
  fix, only on the absolute paths of the landed `tools/fwtask/fwtask.py` and `regs.toml`, which
  changed in resgx545 after the freeze (the pinned files are the blobs at resgx545 52e1f06). With
  the landed tools pinned (and `fwtask_run.py` at 5ef4785, `health.sh` at 382b736) the offline
  tests pass on a copy of this directory beside `../s2` (closing-s2) and `../pixel-faults`:
  `tests/test_scorer.py` 63 ok, `tests/sim_s2.py` 18 ok, `tests/run_mock.py` 77 ok. Before the
  fix the same copy gave 55, 18 and 76 ok with the e4m mock check that `REWORDED.md` names as
  flaky failing once.

The lines that changed (`diff out/score-e5t.txt out/score-e5t.fixed.txt`); the other four stages
are identical:

```
< tri-nohold: 9 event entries (control: >= 1), tri 5673 us
< tri-nohold-r2: 9 event entries (control: >= 1), tri 6038 us
< tri90: tri 75230 us (no-hold median 6038), 9 entries: QUEUED (the job's events at the exit)
< tri90-r2: tri 73184 us (no-hold median 6038), 9 entries: QUEUED (the job's events at the exit)
< tri90-r3: tri 74788 us (no-hold median 6038), 9 entries: QUEUED (the job's events at the exit)
> tri-nohold: 3 job event entries (control: >= 1; 6 host kick entries not counted), tri 5673 us
> tri-nohold-r2: 3 job event entries (control: >= 1; 6 host kick entries not counted), tri 6038
  us
> tri90: tri 75230 us (no-hold median 6038), 3 job entries (6 host kick entries not counted):
  QUEUED (the job's events at the exit)
> tri90-r2: tri 73184 us (no-hold median 6038), 3 job entries (6 host kick entries not
  counted): QUEUED (the job's events at the exit)
> tri90-r3: tri 74788 us (no-hold median 6038), 3 job entries (6 host kick entries not
  counted): QUEUED (the job's events at the exit)
```

(the longer lines wrapped here; one line in the files). The `SUMMARY` line is identical.

Changed files (sha256, first 16 hex digits):

| file | before | after | in the freeze |
|---|---|---|---|
| `score/score_s2.py` | aa156a0129e05a49 | 413638b3061680b6 | yes |
| `score/score_s2.as-run.py` | (new) | aa156a0129e05a49 | yes |
| `tests/test_scorer.py` | 688a62649503a3da | 8cbc10f3b135c4f3 | no |
| `FROZEN.sha256` | 25d2911bbe5bef06 | 4475f497493bf181 | (the freeze) |
