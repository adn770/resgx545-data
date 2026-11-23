# r43-n3h-n1 preflight (the lead, before staging)

- **When:** first of round 43 (decision E (a)): stage w plants M1, stage v reads it with no draws
  between and ends in the runner's planned stop (V-EARLY1); no build, no boot.
- **The user's OK for this session** (decisions A-E (a), 2026-11-23) and for its firmware-page
  writes, every dword in the README ("Firmware-page bytes per row": round 42's mark, landv and
  crumb3). Not before.
- The user is present and has a reset ready (flagged: our firmware task, a planned stop).
- The laptop runs the r42-kernel module (fork ec6511d5de87), srcversion loaded = installed =
  079DD0D13F231EEAC52FE0F; `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r43h1/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- The whole session in one `run` (no --from, no --only): the second stage has no begin draws of its
  own.
- About 15-20 minutes with staging: w 1 row of 1 job (alarm 600 s), v 1 row of 2 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py w out/ATT/w`, `python3 score/score.py v
  out/ATT/v`.
