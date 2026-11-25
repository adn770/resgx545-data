# r45-n3j-n2 preflight (the lead, before staging)

- **When:** after N1 (decision F (a)): wg plants M1, lf2 runs land after one fill again and ends in
  the runner's planned stop (row LF2); no build, no boot.
- **The user's OK for this session** (decisions A=a, B=a, C=a, D=b, F=a) and for its firmware-page
  writes, every dword in the README ("Firmware-page bytes per row": mark, crumb3 and land as round
  44 ran them). Not before.
- The user is present and has a reset ready (flagged: our firmware task, a planned stop).
- The laptop runs the r42-kernel module (fork ec6511d5de87), srcversion loaded = installed =
  079DD0D13F231EEAC52FE0F; `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r45j2/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- The whole session in one `run` (no --from, no --only): a read stage has begin draws of its own.
- About 1 minutes on the laptop (round 44's two-stage sessions took about 45 s), plus staging,
  scoring and the health draw after: wg 1 row of 1 job (alarm 600 s), lf2 1 row of 2 jobs (alarm 600
  s).
- After the run (or a stop): `python3 score/score.py wg out/ATT/wg`, `python3 score/score.py lf2
  out/ATT/lf2`.
