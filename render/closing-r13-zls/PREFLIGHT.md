# r13-zls preflight (the lead, before staging)

1. Module B60AB0B475DD1E8972419B5 loaded and installed (the kit checks both); no knob is used.
2. `~/sgxfive-test-t10` is sha256 9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb
   (built by `lead/build_tool10.sh` from a581c06; the kit's stage checks it). FROZEN.commits
   carries its `built` line (recipe data:render/closing-r10-st1/lead/build_tool10.sh).
3. `~/scratch/r13z/` absent or empty; at least 300 MiB free on `~`.
4. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again (verifies the freeze).
5. Runs second in the sitting (after r13-tex, before r13-dpm); log to `closing13/logs/run-r13z.log`.
   No fault is planned: a fault stops the session (4), with recovery and strict health by the kit.
6. zbase's rd:12 values assume t10 maps the depth buffer at 0x3e001000 and the store at 0x3e015000
   (every kept depth job and the library mock do): if `hook_check` stops zbase (24) on the
   addresses, nothing ran at a wrong base but the rows before it; zbits and zfmt still run.
