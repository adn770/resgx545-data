# r9-z2 preflight (the lead, before staging)

1. Module B60AB0B475DD1E8972419B5 loaded and installed (the kit checks both); no knob is used.
2. `~/sgxfive-test-t9` is sha256 7a28be3952fb310170e861da0622d890a2e215cb761d6f21bc9321223e1b40ce
   (staged by the lead, built by `lead/build_tool9.sh`; the kit's stage checks it). FROZEN.commits
   carries its `built` line (recipe data:render/closing-r9-z2/lead/build_tool9.sh).
3. `~/scratch/r9z/` absent or empty; at least 300 MiB free on `~`.
4. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again (verifies the freeze).
5. Runs in the sitting after r9-x (DECISIONS-R9.md order); log to `closing9/logs/run-r9z.log`.
   No fault is planned: a fault stops the session (4), recovery and strict health by the kit.
