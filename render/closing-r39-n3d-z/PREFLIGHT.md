# r39-n3d-z preflight (the lead, before staging)

- **The user has approved this row** (our image in the slack of the firmware's PDS #14 page,
  as R4; our emit inside a GETMISCINFO pass). Not before.

- The user is present and has a reset ready (flagged: own runs our firmware task).
- The laptop runs the r39-kernel module (r39-kernel-f9453424bf71) after its one-shot boot,
  loaded = installed; session.toml's srcversion is that build's (not the placeholder) and the
  session is frozen again; `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- **Conditional**: only after r39-n3d-k reads K-NEVER, then the r39-kernel build and its one-shot boot.
- Laptop files under `~/scratch/r39z/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- About 2 minutes with staging: own 1 job (alarm 600 s), post 2 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py own out/ATT/own`, `python3 score/score.py post
  out/ATT/post`.
