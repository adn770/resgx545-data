# r14-bif preflight (the lead, before staging)

1. Module B60AB0B475DD1E8972419B5 loaded and installed (the kit checks both); debugfs vm_pte_addr
   and vm_pte_flags read 0 (the kit's knob check; the runner restores them after every row).
2. `~/sgxfive-test-t14` is sha256 aa550b94585aaf6eb5d9b7927d320ad31ea8d1e206b8c5e99e4435c7f0a83859
   (built by `lead/build_tool14.sh` from c58f9f9; `closing14/k14/TOOL14.built`; the kit's stage
   checks it). FROZEN.commits carries its `built` line (recipe
   data:render/closing-r14-bif/lead/build_tool14.sh: the fold publishes `lead/` there).
3. `~/scratch/r14b/` absent or empty; at least 300 MiB free on `~`.
4. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again (verifies the freeze).
5. Runs fifth in the sitting (after r14-isp, before r14-flag); log to `closing14/logs/run-r14b.log`.
   No fault is planned: a fault stops the session (4), with recovery and strict health by the kit.
6. The rows assume t14 maps the depth buffer at 0x3e001000 and the store at 0x3e015000 (E1029's and
   E965's kept jobs, the library mock): if `hook_check` stops the stage (24) on the addresses or on
   a missing PTE line, nothing ran with the flag elsewhere but the rows before it.
