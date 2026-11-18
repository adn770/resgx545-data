# r37-n3b-b preflight (the lead, before staging)

- The user is present and has a reset ready (flagged: own runs our firmware task).
- The laptop runs the r37-kernel module (fork 4f35fc20ffa9) after its one-shot boot, loaded =
  installed; session.toml's srcversion is that build's (not the placeholder) and the session is
  frozen again; `own_arm` reads `off blob=0`; `~/sgxfive-test-t30` sha256 b5ea288d... present.
- Run it after r37-n3b-a, on the same boot (the user approved step B: the crumb image writes
  `tim` three times with stopped values, a planned stop of the EDM tick until the next reset).
- Laptop files under `~/scratch/r37b/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- About 2 minutes with staging: own 1 job (alarm 600 s), post 2 jobs (alarm 600 s).
- After the run (or a stop): `python3 score/score.py own out/ATT/own`, `python3 score/score.py post
  out/ATT/post`.
