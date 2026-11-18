# r36-n3 preflight (the lead, before staging)

- The user is present and has a reset ready (flagged: own runs our firmware task); records
  E1148-E1155.
- The laptop is booted into the test kernel with module srcversion C01FB3203FDA4FEF01E4891 loaded =
  installed (fork c78059370315), `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` sha256
  b5ea288d... present (the kit's preflight checks it and the debugfs files fwtask_run.py uses:
  own_code, own_arm, own_res, load, boot, status, miscinfo, ...).
- Laptop files under `~/scratch/r36n/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- About 3 minutes with staging: own 10 jobs (alarm 900 s), post 2 jobs (alarm 600 s).
- Stop rules: README.md; any stop in own ends the session.
- After the run (or a stop): `python3 score/score.py own out/ATT/own`, `python3 score/score.py post
  out/ATT/post`.
