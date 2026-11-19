# r40-s-pass preflight (the lead, before staging)

- **The user has approved this row** (our image in the slack of the firmware's PDS #14 page,
  as R4 and Z; the emit on a timer pass, as R4). Not before.

- The user is present and has a reset ready (flagged: own runs our firmware task).
- The laptop runs the r39-kernel module (0CDFCDB73D76F39FE9E593C, fork f9453424bf71), loaded =
  installed; `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` sha256 b5ea288d... present.
- No rebuild, no boot.
- Laptop files under `~/scratch/r40sp/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- About 2 minutes with staging: own 1 job (alarm 600 s), post 2 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py own out/ATT/own`, `python3 score/score.py post
  out/ATT/post`.
