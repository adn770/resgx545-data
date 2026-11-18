# r35-sa preflight (the lead, before staging)

- The laptop is booted into the test kernel with module srcversion 7CE8E38EDB97FC5EA4F6C90 loaded =
  installed (it was on stock Arch on 2026-11-18: boot it first), on the travel cable
  (`ssh -o HostKeyAlias=cedar jtorra@10.42.0.2`); `~/sgxfive-test-t30` sha256 b5ea288d... and
  `~/sgxfive-test-t10` sha256 9bedc2d6... present (the kit's preflight checks both).
- Laptop files under `~/scratch/r35s/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- Check tests/test_score.py exists and covers every frozen name (D2:
  test_every_frozen_name_has_a_world_both_ways).
- About 10 minutes: stage a 40 jobs (alarm 2400 s), stage t 23 jobs (alarm 1800 s).
- Stop rules: README.md; a stop in a goes on to t, a stop in t ends the session.
- After the run: `python3 score/score.py a out/ATT/a`, `python3 score/score.py t out/ATT/t`,
  `python3 score/score.py q129 out/ATT`, `python3 score/score.py q193 out/ATT`.
