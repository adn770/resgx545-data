# r45-n3j-n1 preflight (the lead, before staging)

- **When:** first of round 45 (decisions A (a), F (a)): five plants and the second reads after
  fill-fill, tri and tri-fill, the new tri-tri, a third read of one fill, then F2b with no plant;
  all quiet, no planned stop; no build, no boot.
- **The user's OK for this session** (decisions A=a, B=a, C=a, D=b, F=a) and for its firmware-page
  writes, every dword in the README ("Firmware-page bytes per row": mark, crumb3 and land as round
  44 ran them). Not before.
- The user is present and has a reset ready (flagged: our firmware task, no planned stop).
- The laptop runs the r42-kernel module (fork ec6511d5de87), srcversion loaded = installed =
  079DD0D13F231EEAC52FE0F; `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r45j1/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- The whole session in one `run` (no --from, no --only): a read stage has begin draws of its own.
- About 5 minutes on the laptop (round 44's two-stage sessions took about 45 s), plus staging,
  scoring and the health draw after: wa 1 row of 1 job (alarm 600 s), ff2 1 row of 1 job (alarm 600
  s), wb 1 row of 1 job (alarm 600 s), t2 1 row of 1 job (alarm 600 s), wc 1 row of 1 job (alarm 600
  s), tf2 1 row of 1 job (alarm 600 s), wd 1 row of 1 job (alarm 600 s), tt 1 row of 1 job (alarm
  600 s), we 1 row of 1 job (alarm 600 s), f3 1 row of 1 job (alarm 600 s), f2b 1 row of 1 job
  (alarm 600 s).
- After the run (or a stop): `python3 score/score.py wa out/ATT/wa`, `python3 score/score.py ff2
  out/ATT/ff2`, `python3 score/score.py wb out/ATT/wb`, `python3 score/score.py t2 out/ATT/t2`,
  `python3 score/score.py wc out/ATT/wc`, `python3 score/score.py tf2 out/ATT/tf2`, `python3
  score/score.py wd out/ATT/wd`, `python3 score/score.py tt out/ATT/tt`, `python3 score/score.py we
  out/ATT/we`, `python3 score/score.py f3 out/ATT/f3`, `python3 score/score.py f2b out/ATT/f2b`.
