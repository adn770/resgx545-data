# r42-n3g-g3 preflight (the lead, before staging)

- **When:** last of round 42, its own session (decision D (a)): landv with 0xc43, the timer running;
  the highest risk.
- **The user's OK for this session** (decisions A-F (a), 2026-11-21) and for its firmware-page
  writes, every dword in the README: **new bytes** in stage lv. Not before.
- The user is present and has a reset ready (flagged: our firmware task, a planned gate failure).
- The laptop runs the r42-kernel module (fork ec6511d5de87), booted once with the user's OK;
  srcversion loaded = installed = session.toml's (not the placeholder
  `UNBUILT-r42-kernel-ec6511d5de87`); `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r42g3/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging (refrozen
  after the srcversion is set).
- About 10-15 minutes with staging: lv 1 row of 3 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py lv out/ATT/lv`.
