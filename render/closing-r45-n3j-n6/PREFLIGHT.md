# r45-n3j-n6 preflight (the lead, before staging)

- **When:** after N5 (decision F (a)): wq plants M1 (the kit's K7 keeps a session's first stage on
  the default begin draws), q runs landq with no draws and ends in the runner's planned stop (row
  Q).
- **The user's OK for this session** (decisions A=a, B=a, C=a, D=b, E=c, F=a) and for its
  firmware-page writes, every dword in the README ("Firmware-page bytes per row": mark as round 44
  ran it; crumbz and landq NEW, assembled from the fork's header). Not before; and not before the
  user's OK for the one-shot boot onto the r45-kernel module.
- The user is present and has a reset ready (flagged: our firmware task, a planned stop).
- The laptop runs the r45-kernel module (fork b1089172b2e7) after the one-shot boot, srcversion
  loaded = installed = EC553F41FD8324BB6BF1764 (control SV; the kit's preflight refuses any other,
  runone.sh checks it first); `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r45j6/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- The whole session in one `run` (no --from, no --only): a Z or q stage has begin draws of its own.
- About 1 minute on the laptop (round 44's nine-stage session took 3 min 20 s), plus staging,
  scoring and the health draw after: wq 1 row of 1 job (alarm 600 s), q 1 row of 2 jobs (alarm 600
  s).
- After the run (or a stop): `python3 score/score.py wq out/ATT/wq`, `python3 score/score.py q
  out/ATT/q`.
