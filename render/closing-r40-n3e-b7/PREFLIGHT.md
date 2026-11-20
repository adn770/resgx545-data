# r40-n3e-b7 preflight (the lead, before staging)

- **When:** row B7, conditional: only if B2, B3 or B4 read RUN (H-DM falsified as needed); bits 1:0
  = 1, a new risk class (decision B (a)); a FAULT stops the ladder.
- **The user has approved this row** (ST's firmware-page write, our emit on a timer pass). Not
  before.
- The user is present and has a reset ready (flagged: own runs our firmware task).
- The laptop runs the r40-kernel module (fork 423b436e7f80) after its one-shot boot, loaded =
  installed; session.toml's srcversion is that build's (not the placeholder) and the session is
  frozen again; `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` present.
- Laptop files under `~/scratch/r40b7/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- About 2 minutes with staging: own 1 job (alarm 600 s), post 2 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py own out/ATT/own`, `python3 score/score.py post
  out/ATT/post`.
