# r34-sa0 preflight (the lead, before staging)

- The laptop is on the travel cable (`ssh -o HostKeyAlias=cedar jtorra@10.42.0.2`), module
  srcversion 7CE8E38EDB97FC5EA4F6C90 loaded = installed, `~/sgxfive-test-t30` sha256
  b5ea288d... and `~/sgxfive-test-t10` sha256 9bedc2d6... present (the kit's preflight checks
  both).
- Laptop files under `~/scratch/r34s/`, never /tmp; at least 300 MiB free on ~.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- About 18 minutes (25 at most, alarm 2700 s): 60 jobs and 380 s of idle in one stage.
- Stop rules: README.md; any stop ends the session (`on_stop = "end"`, one stage).
- After the run: `python3 score/score.py s out/ATT/s` and `python3 score/score.py q136 out/ATT`.
