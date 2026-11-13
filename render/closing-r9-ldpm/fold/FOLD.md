# r9-ldpm: the fold (2026-11-13, the builder)

Run by the lead on the laptop, attempt `out/20261113-082650` (driver log `fold/run-r9l.log`, the
lead's `closing9/logs/r9-ldpm-run.log` copied), driver rc 0: every stage ran, no stop, no fault, no
lead decision. Folded as E960 to E963. README.md and PREFLIGHT.md are the pre-run documents,
unchanged; nothing frozen was changed (`kit/session.py verify`: files verified).

- `fold/reproduce.sh`: the frozen scorer re-run on the kept stages is byte-identical to the kept
  `score-STAGE.txt` in 4 of 4 stages (`fold/reproduce.out`). No post-run scorer fix.
- `fold/misses.py` (post hoc, written after the scores were read): every row's reading beside the
  frozen tables (`fold/misses.out`), and stage w's cells read without their calibrations' gate.

## Stage w: why its cells read "controls FAILED"

Not a scorer bug: the frozen scorer did what its docstring and README said. Each w calibration is
a control whose pass needs every value frozen on it under CTL and H-STEPMODEL, the replay's steps
S2 to S7 inside the bracket the job read, as well as its need. All four needs were the replay's
(H-REPLAY 8 of 8), but all four read S6 one or two pages above the replay (4096x1024 `0x17e` for
`0x17c`, 4096x1536 `0x22b` for `0x229` and S3 `0xe1` for `0xe0`, 3584x1024 `0x14f` for `0x14d`,
2048x512 `0x6f` for `0x6e`), the same kind of one-page step miss E935 and E936 found at 2048x3072,
2560x3072 and 3072x2560. So each calibration FAILED as frozen and gated its own cell: the premise
the build chose (exact replay steps) failed, which is a result about the step replay, not a reading
error. The design choice is the builder's: gating an F9 count on S6 being exact was stricter than
the count needs, since F9's cells lie in bands 3 and 2 below S6. Read after the run, ungated, the
four cells gave every frozen prediction: F9 4 of 4 counts and 4 of 4 run peaks, E625 4 of 4, the
abort's global pages 4 of 4, d = 7/4 and d = 1 0 of 4 (`fold/misses.out`). E962 reports those as
post hoc, not as a verdict.
