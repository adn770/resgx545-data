# r44-n3i-n1 preflight (the lead, before staging)

- **When:** first of round 44 (decision E (a)): four plants and the reads after fill-tri, fill-fill,
  tri and tri-fill, then F2 with no plant; all quiet, no planned stop; no build, no boot.
- **The user's OK for this session** (decisions A-E (a), 2026-11-23) and for its firmware-page
  writes, every dword in the README ("Firmware-page bytes per row": mark and crumb3 as rounds 42-43
  ran them, land as rounds 40-41 ran it). Not before.
- The user is present and has a reset ready (flagged: our firmware task, no planned stop).
- The laptop runs the r42-kernel module (fork ec6511d5de87), srcversion loaded = installed =
  079DD0D13F231EEAC52FE0F; `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r44i1/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- The whole session in one `run` (no --from, no --only): a read stage has begin draws of its own.
- About 5 minutes on the laptop (round 43's two-stage sessions took about 45 s), plus staging,
  scoring and the health draw after: wa 1 row of 1 job (alarm 600 s), ft 1 row of 1 job (alarm 600
  s), wb 1 row of 1 job (alarm 600 s), ff 1 row of 1 job (alarm 600 s), wc 1 row of 1 job (alarm 600
  s), t 1 row of 1 job (alarm 600 s), wd 1 row of 1 job (alarm 600 s), tf 1 row of 1 job (alarm 600
  s), f2 1 row of 1 job (alarm 600 s).
- After the run (or a stop): `python3 score/score.py wa out/ATT/wa`, `python3 score/score.py ft
  out/ATT/ft`, `python3 score/score.py wb out/ATT/wb`, `python3 score/score.py ff out/ATT/ff`,
  `python3 score/score.py wc out/ATT/wc`, `python3 score/score.py t out/ATT/t`, `python3
  score/score.py wd out/ATT/wd`, `python3 score/score.py tf out/ATT/tf`, `python3 score/score.py f2
  out/ATT/f2`.
