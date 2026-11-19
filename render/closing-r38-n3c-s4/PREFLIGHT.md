# r38-n3c-s4 preflight (the lead, before staging)

- The user is present and has a reset ready (flagged: own runs our firmware task).
- The laptop runs the r38-kernel module (fork e1cf9d2b43ab) after its one-shot boot, loaded =
  installed; session.toml's srcversion is that build's (not the placeholder) and the session is
  frozen again; `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` sha256 b5ea288d... present.
- After the r38-kernel build and one-shot boot; S3 and S4 on the same boot, in either order (the design runs S4 first only after V0-NOT; R2 read V0-HOLDS).
- Laptop files under `~/scratch/r38d/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- About 2 minutes with staging: own 1 job (alarm 600 s), post 2 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py own out/ATT/own`, `python3 score/score.py post
  out/ATT/post`.
