# r17-zls preflight (the lead, before staging)

1. Module B60AB0B475DD1E8972419B5 loaded and installed (the kit checks both); no knob is used.
2. `~/sgxfive-test-t10` is sha256 9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb
   (built by `lead/build_tool10.sh` from a581c06; the kit's stage checks it). FROZEN.commits
   carries its `built` line (recipe data:render/closing-r10-st1/lead/build_tool10.sh).
3. `~/scratch/r17z/` absent or empty; at least 300 MiB free on `~` (the 32-page dumps of zb20 are
   128 KiB a buffer, small gzipped).
4. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again (verifies the freeze).
5. R17-1 (a): this session runs first in the sitting, then r17-tw; log to
   `closing17/logs/run-r17z.log`. No fault is planned: a fault stops the session (4), with
   recovery and strict health by the kit.
6. First of their kind (a stop does not mean a fault): zb20's 128 x 64 pair (bit 20 cleared at a
   size never run, 32 pages), its last four rows, `on_stop = "end"`. The packed records go to
   dwords 2048 to 8192 + 700 of a 32768-dword buffer (every frozen start is inside it).
7. The 17 rows name `--depth-pages` where the target is not whole tiles and on every new zb20 row;
   `hook_check` stops the stage if the tool maps another count.
8. Deviation 1 of README.md (63 x 31 G 0 for 161 x 49 G 2) is the lead's to accept; the plan's
   161 x 49 needs one more reference job and scores against the run's own reference.
