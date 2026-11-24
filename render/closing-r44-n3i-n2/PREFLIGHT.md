# r44-n3i-n2 preflight (the lead, before staging)

- **When:** after N1 (decision E (a)): wl plants M1, lm runs land on that bank with no draws and
  ends in the runner's planned stop (row LM); no build, no boot.
- **The user's OK for this session** (decisions A-E (a), 2026-11-23) and for its firmware-page
  writes, every dword in the README ("Firmware-page bytes per row": mark and crumb3 as rounds 42-43
  ran them, land as rounds 40-41 ran it). Not before.
- The user is present and has a reset ready (flagged: our firmware task, a planned stop).
- The laptop runs the r42-kernel module (fork ec6511d5de87), srcversion loaded = installed =
  079DD0D13F231EEAC52FE0F; `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r44i2/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- The whole session in one `run` (no --from, no --only): a read stage has begin draws of its own.
- About 1 minutes on the laptop (round 43's two-stage sessions took about 45 s), plus staging,
  scoring and the health draw after: wl 1 row of 1 job (alarm 600 s), lm 1 row of 2 jobs (alarm 600
  s).
- After the run (or a stop): `python3 score/score.py wl out/ATT/wl`, `python3 score/score.py lm
  out/ATT/lm`.
