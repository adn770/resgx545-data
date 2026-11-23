# r42-n3g-g2 preflight (the lead, before staging)

- **When:** after G1 (decision C (a)): stage s (row C again, after M's resets), then stage q
  (sb402); s failing as a control stops the session.
- **The user's OK for this session** (decisions A-F (a), 2026-11-21) and for its firmware-page
  writes, every dword in the README: crumb3's bytes, run since round 38. Not before.
- The user is present and has a reset ready (flagged: our firmware task, a planned gate failure).
- The laptop runs the r42-kernel module (fork ec6511d5de87), booted once with the user's OK;
  srcversion loaded = installed = session.toml's (not the placeholder
  `UNBUILT-r42-kernel-ec6511d5de87`); `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r42g2/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging (refrozen
  after the srcversion is set).
- About 20 minutes with staging: s 1 row of 2 jobs (alarm 600 s), q 1 row of 2 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py s out/ATT/s`, `python3 score/score.py q
  out/ATT/q`.
