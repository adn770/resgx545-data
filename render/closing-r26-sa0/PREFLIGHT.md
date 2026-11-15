# r26-sa0 preflight (the lead, before staging)

- The laptop is on the travel cable (`ssh -o HostKeyAlias=cedar jtorra@10.42.0.2`), module
  srcversion
  E0CC40275493F8AEAD8180B loaded = installed, `~/sgxfive-test-t24` sha256 fd15fce4... and
  `~/sgxfive-test-t10` sha256 9bedc2d6... present (the kit's preflight checks both).
- Run after r26-vol (one sitting); laptop files under `~/scratch/r26s/`, never /tmp.
- `bash tests/run_all.sh` passes and `FROZEN.sha256` verifies on the Mac before staging.
- Stop rules: see README.md; a stop in uc ends the session (on_stop end).
