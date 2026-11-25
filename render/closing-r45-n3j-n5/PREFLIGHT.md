# r45-n3j-n5 preflight (the lead, before staging)

- **When:** after the user's OK and the one-shot boot onto the r45-kernel module (decision F (a)):
  the W build control wj, then crumbz after no draw, tri, fill-tri, fill, fill-fill, tri-fill and
  tri-tri, each right after its plant wk-wp; quiet, no planned stop.
- **The user's OK for this session** (decisions A=a, B=a, C=a, D=b, E=c, F=a) and for its
  firmware-page writes, every dword in the README ("Firmware-page bytes per row": mark as round 44
  ran it; crumbz and landq NEW, assembled from the fork's header). Not before; and not before the
  user's OK for the one-shot boot onto the r45-kernel module.
- The user is present and has a reset ready (flagged: our firmware task, no planned stop).
- The laptop runs the r45-kernel module (fork b1089172b2e7) after the one-shot boot, srcversion
  loaded = installed = EC553F41FD8324BB6BF1764 (control SV; the kit's preflight refuses any other,
  runone.sh checks it first); `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r45j5/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- The whole session in one `run` (no --from, no --only): a Z or q stage has begin draws of its own.
- About 6 minutes on the laptop (round 44's nine-stage session took 3 min 20 s), plus staging,
  scoring and the health draw after: wj 1 row of 1 job (alarm 600 s), zn 1 row of 1 job (alarm 600
  s), wk 1 row of 1 job (alarm 600 s), zt 1 row of 1 job (alarm 600 s), wl 1 row of 1 job (alarm 600
  s), zft 1 row of 1 job (alarm 600 s), wm 1 row of 1 job (alarm 600 s), zf 1 row of 1 job (alarm
  600 s), wn 1 row of 1 job (alarm 600 s), zff 1 row of 1 job (alarm 600 s), wo 1 row of 1 job
  (alarm 600 s), ztf 1 row of 1 job (alarm 600 s), wp 1 row of 1 job (alarm 600 s), ztt 1 row of 1
  job (alarm 600 s).
- After the run (or a stop): `python3 score/score.py wj out/ATT/wj`, `python3 score/score.py zn
  out/ATT/zn`, `python3 score/score.py wk out/ATT/wk`, `python3 score/score.py zt out/ATT/zt`,
  `python3 score/score.py wl out/ATT/wl`, `python3 score/score.py zft out/ATT/zft`, `python3
  score/score.py wm out/ATT/wm`, `python3 score/score.py zf out/ATT/zf`, `python3 score/score.py wn
  out/ATT/wn`, `python3 score/score.py zff out/ATT/zff`, `python3 score/score.py wo out/ATT/wo`,
  `python3 score/score.py ztf out/ATT/ztf`, `python3 score/score.py wp out/ATT/wp`, `python3
  score/score.py ztt out/ATT/ztt`.
