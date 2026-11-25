# r46-n3k-n4 preflight (the lead, before staging)

- **When:** after N3: we plants M1, q2 runs landq with no draws (Q's second read) and ends in the
  planned stop.
- **The user's OK for this session** (decisions A=a, B=b, C=a, D=a, E=a, F=b) and for its
  firmware-page writes, every dword in the README ("Firmware-page bytes per row"). Not before; and
  not before the user's OK for the one-shot boot onto the r46-kernel module.
- The user is present and has a reset ready (flagged: our firmware task, a planned stop).
- The laptop runs the r46-kernel module (fork c5094783eb88) after the one-shot boot, srcversion
  loaded = installed = 10BBF3BFBD51D559106589F (control SV; the kit's preflight refuses any other,
  runone.sh checks it first); `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r46k4/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- The whole session in one `run` (no --from, no --only).
- About 1 minute on the laptop, plus staging, scoring and the health draw after: we 1 row of 1 job
  (alarm 600 s), q2 1 row of 2 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py we out/ATT/we`, `python3 score/score.py q2
  out/ATT/q2`.
