# r41-n3f-h4 preflight (the lead, before staging)

- **When:** last of round 41, its own session (decision F (a)): the triangle first.
- **The user has approved this session** (decisions A-F (a), 2026-11-20); the firmware-page write
  equals an already-run row's (README), no new bytes. Not before.
- The user is present and has a reset ready (flagged: our firmware task, a planned gate failure).
- The laptop runs the r40-kernel module, srcversion 83FBFD860D4E0D4CE691F48 (loaded = installed);
  `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r41h4/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- About 10 minutes with staging: t 1 row of 1 job (alarm 600 s).
- After the run (or a stop): `python3 score/score.py t out/ATT/t`.
