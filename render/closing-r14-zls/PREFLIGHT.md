# r14-zls preflight (the lead, before staging)

1. Module B60AB0B475DD1E8972419B5 loaded and installed (the kit checks both); no knob is used.
2. `~/sgxfive-test-t10` is sha256 9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb
   (built by `lead/build_tool10.sh` from a581c06; the kit's stage checks it). FROZEN.commits
   carries its `built` line (recipe data:render/closing-r10-st1/lead/build_tool10.sh).
3. `~/scratch/r14z/` absent or empty; at least 300 MiB free on `~` (the 640 x 480 rows dump 316
   pages each, about 1.3 MB raw, small gzipped).
4. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again (verifies the freeze).
5. Runs second in the sitting (after r14-tex, before r14-dpm); log to `closing14/logs/run-r14z.log`.
   No fault is planned: a fault stops the session (4), with recovery and strict health by the kit.
6. The poked bases assume t10 maps the depth buffer at 0x3e001000 (base 0x3e000000), the 20-page
   store at 0x3e015000 and E988's 18-page stencil at 0x3e013000 with its store at 0x3e025000 (every
   kept job of these forms and the library mock: `lead/dryrun_checks.out`). If `hook_check` stops a
   stage (24) on the addresses, only the rows before it ran; the next stage still runs.
7. zo-g3 (E411's G 3 store base) is zodd's last row, inside its 20 pages by E465's rule; if it
   faults anyway, the session stops there (4) with zbits2 and zflat not run: rerun them alone.
