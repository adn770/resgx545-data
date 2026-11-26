# r46-n3k-n9 preflight (the lead, before staging)

- **When:** first of the addendum, on the boot N1-N4 ran on (module 10BBF3BF, sa12 = V0 since B6;
  design §11.3): w9 plants M1, lfk runs land after one fill and ends in the planned stop.
- **The user's OK for this session** (decisions G=a, H=a, I=a, J=a, K=a) and for its firmware-page
  writes, every dword in the README ("Firmware-page bytes per row"). Not before.
- The user is present and has a reset ready (flagged: our firmware task, a planned stop).
- The laptop still runs the r46-kernel module (fork c5094783eb88) on round 46's boot, srcversion
  loaded = installed = 10BBF3BFBD51D559106589F (control SV; the kit's preflight refuses any other,
  runone.sh checks it first); `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r46k9/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- The whole session in one `run` (no --from, no --only).
- About 1 minute on the laptop, plus staging, scoring and the health draw after: w9 1 row of 1 job
  (alarm 600 s), lfk 1 row of 2 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py w9 out/ATT/w9`, `python3 score/score.py lfk
  out/ATT/lfk`.
