# r41-n3f-h3 preflight (the lead, before staging)

- **When:** after H1 and H2, its own session (decision D (a)): land with 0xc43, the timer running;
  the highest risk.
- **The user has approved this session** (decisions A-F (a), 2026-11-20); the firmware-page write
  equals an already-run row's (README), no new bytes. Not before.
- The user is present and has a reset ready (flagged: our firmware task, a planned gate failure).
- The laptop runs the r40-kernel module, srcversion 83FBFD860D4E0D4CE691F48 (loaded = installed);
  `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r41h3/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- About 10 minutes with staging: lc 1 row of 3 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py lc out/ATT/lc`.
