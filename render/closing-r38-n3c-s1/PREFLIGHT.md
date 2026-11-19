# r38-n3c-s1 preflight (the lead, before staging)

- The user is present and has a reset ready (flagged: own runs our firmware task; tim stops the
  EDM tick by design until the stage's last reset).
- The laptop runs the r37-kernel module 77917296568EB311B89B0DA (fork 4f35fc20ffa9), loaded =
  installed; `own_arm` reads `off blob=0`; the post-boot fill and triangle are done (the firmware
  loaded) before the run.
- `~/sgxfive-test-t30` (sha256 b5ea288d...) and `~/regtimeline` (sha256 079f6359...) present.
- Laptop files under `~/scratch/r38s/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- About 15 minutes with staging: own 1 job, tim 1 job, post 2 jobs (alarms 600 s each).
- After the run (or a stop): `python3 score/score.py own out/ATT/own`, `python3 score/score.py tim
  out/ATT/tim`, `python3 score/score.py post out/ATT/post`.
