# r41-n3f-h1 preflight (the lead, before staging)

- **When:** first of round 41 (decision B (a)): stage c, the control, then stage x; C failing in any
  way stops everything.
- **The user has approved this session** (decisions A-F (a), 2026-11-20); the firmware-page write
  equals an already-run row's (README), no new bytes. Not before.
- The user is present and has a reset ready (flagged: our firmware task, a planned gate failure).
- The laptop runs the r40-kernel module, srcversion 83FBFD860D4E0D4CE691F48 (loaded = installed);
  `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r41h1/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- About 10-15 minutes with staging: c 1 row of 2 jobs (alarm 600 s), x 1 row of 2 jobs (alarm 600
  s).
- After the run (or a stop): `python3 score/score.py c out/ATT/c`, `python3 score/score.py x
  out/ATT/x`.
