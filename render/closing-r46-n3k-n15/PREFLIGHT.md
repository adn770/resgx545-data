# r46-n3k-n15 preflight (the lead, before staging)

- **When:** after N14 (decision J (a)): w15 plants M1, r2 is R's second read; ends in the planned
  stop.
- **The user's OK for this session** (decisions G=a, H=a, I=a, J=a, K=a) and for its firmware-page
  writes, every dword in the README ("Firmware-page bytes per row"). Not before.
- The user is present and has a reset ready (flagged: our firmware task, a planned stop).
- The laptop still runs the r46-kernel module (fork c5094783eb88) on round 46's boot, srcversion
  loaded = installed = 10BBF3BFBD51D559106589F (control SV; the kit's preflight refuses any other,
  runone.sh checks it first); `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r46k15/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- The whole session in one `run` (no --from, no --only).
- About 1 minute on the laptop, plus staging, scoring and the health draw after: w15 1 row of 1 job
  (alarm 600 s), r2 1 row of 2 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py w15 out/ATT/w15`, `python3 score/score.py r2
  out/ATT/r2`.
