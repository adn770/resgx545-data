# r39-n3d-k preflight (the lead, before staging)

- **The user has approved this row** (our image in the slack of the firmware's PDS #14 page,
  as R4; our emit inside a GETMISCINFO pass). Not before.

- The user is present and has a reset ready (flagged: own runs our firmware task).
- The laptop runs module 88ADCEB5AD9F055D077A99C (r38-kernel, fork e1cf9d2b43ab), loaded =
  installed; `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` sha256 b5ea288d... present.
- Now, on the module the laptop runs (88ADCEB5AD9F055D077A99C, fork e1cf9d2b43ab, r38-kernel); before any rebuild. The design's O2d precondition holds (data-private firmware/fwsim/n3d-kick/facts.txt: 0 emits in a GETMISCINFO kick pass).
- Laptop files under `~/scratch/r39k/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- About 2 minutes with staging: own 1 job (alarm 600 s), post 2 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py own out/ATT/own`, `python3 score/score.py post
  out/ATT/post`.
