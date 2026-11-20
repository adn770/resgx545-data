# r40-n3e-l preflight (the lead, before staging)

- **When:** row L, E1, 2nd: after B0-DONE (n3e §3.3 row L, the user's decision C (a)); L-NEVER: no
  other image in this build.
- **The user has approved this row** and the `land` image's 16 firmware-page dwords listed in the
  README (a new write). Not before.
- The user is present and has a reset ready (flagged: own runs our firmware task).
- The laptop runs the r40-kernel module (fork 423b436e7f80) after its one-shot boot, loaded =
  installed; session.toml's srcversion is that build's (not the placeholder) and the session is
  frozen again; `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r40l/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- About 2 minutes with staging: own 1 job (alarm 600 s), post 2 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py own out/ATT/own`, `python3 score/score.py post
  out/ATT/post`.
