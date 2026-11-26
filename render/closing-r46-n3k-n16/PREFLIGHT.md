# r46-n3k-n16 preflight (the lead, before staging)

- **When:** after N15 (decision J (a)): w16 plants M1, p2 is P's second read; ends in the planned
  stop.
- **The user's OK for this session** (decisions G=a, H=a, I=a, J=a, K=a) and for its firmware-page
  writes, every dword in the README ("Firmware-page bytes per row"). Not before.
- The user is present and has a reset ready (flagged: our firmware task, a planned stop).
- The laptop still runs the r46-kernel module (fork c5094783eb88) on round 46's boot, srcversion
  loaded = installed = 10BBF3BFBD51D559106589F (control SV; the kit's preflight refuses any other,
  runone.sh checks it first); `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r46k16/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- The whole session in one `run` (no --from, no --only).
- About 1 minute on the laptop, plus staging, scoring and the health draw after: w16 1 row of 1 job
  (alarm 600 s), p2 1 row of 2 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py w16 out/ATT/w16`, `python3 score/score.py p2
  out/ATT/p2`.
