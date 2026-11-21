# r41-n3f-lc2 preflight (the lead, before staging)

- **When:** a rerun of H3 with control E0 fixed, its own session; land with 0xc43, the timer
  running; the highest risk.
- **The user's OK for this rerun** (H3 with E0 fixed, README); not before. The firmware-page write
  equals an already-run row's (H3's, L's), no new bytes.
- The user is present and has a reset ready (flagged: our firmware task, a planned gate failure).
- The laptop runs the r40-kernel module, srcversion 83FBFD860D4E0D4CE691F48 (loaded = installed);
  `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r41lc2/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- About 10 minutes with staging: lc 1 row of 3 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py lc out/ATT/lc`.
