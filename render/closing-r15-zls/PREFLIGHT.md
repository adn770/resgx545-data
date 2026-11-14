# r15-zls preflight (the lead, before staging)

1. Module B60AB0B475DD1E8972419B5 loaded and installed (the kit checks both); no knob is used.
2. `~/sgxfive-test-t10` is sha256 9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb
   (built by `lead/build_tool10.sh` from a581c06; the kit's stage checks it). FROZEN.commits
   carries its `built` line (recipe data:render/closing-r10-st1/lead/build_tool10.sh).
3. `~/scratch/r15z/` absent or empty; at least 300 MiB free on `~` (the 640 x 480 row dumps 316
   pages, about 1.3 MB raw, small gzipped; zv-g17 44 pages).
4. Offline: `bash tests/run_all.sh`, freeze, `bash tests/run_all.sh` again (verifies the freeze).
5. Runs first in the sitting (R15-1 (a): zls, tex, dpm, isp, tw); log to
   `closing15/logs/run-r15z.log`. No fault is planned: a fault stops the session (4), with
   recovery and strict health by the kit.
6. The poked rows assume t10 maps the depth buffer at 0x3e001000 (base 0x3e000000) and, for
   zp-c-id, the 20-page store at 0x3e015000 (every kept job of these forms and the library mock:
   `lead/dryrun_checks.out`). zovl's rd:13 rows (zv-c-g3, zv-b25, zv-g5, zv-g9, zv-g17) store
   from page 12 of the depth buffer; G 5, 9 and 17 reach pages 21, 27 and 39 of buffers of 24, 32
   and 44 pages, pages no job has written: they are the session's last rows, in ascending extent,
   and a stop there ends the session (`on_stop = "end"`), a fault too (4).
7. The reference flip `--poke blk:1^=0x1` (zb3-c-ref1, zb3-b15-r1) and the z-offset pokes
   `--poke blk:10=...` (zv-c-075, zv-r-hi, zv-i125-*, zv-im25-*) are job pokes of the state block,
   replayed on t10's library mock (none refused).
