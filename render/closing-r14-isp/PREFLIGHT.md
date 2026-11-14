# r14-isp preflight (the lead, before staging)

1. The laptop runs the test boot: gma500 srcversion B60AB0B475DD1E8972419B5 loaded and installed
   (`modinfo -F srcversion gma500` and `/sys/module/gma500/srcversion`). After the reboot to stock
   Arch this session is scaffolded again (a freeze is never rewritten).
2. `~/sgxfive-test-t10` is sha256 9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb
   (the kit's stage checks it); no other tool is used.
3. No earlier session of the sitting left a kpoke armed or a knob off its default (this session
   writes no knob and no kpoke; its only pokes are `--poke blk:N`, the state block in the tool's
   own buffer).
4. `~/scratch/r14i/` does not exist or holds no attempt of this session; at least 400 MiB free on
   `~` plus about 5 MiB for the kept files (39 outputs with every pixel, eight 80 KiB dumps; the
   three 4096 x 16 outputs are 0.7 MB each before gzip).
5. Offline on the Mac, in this directory: `bash tests/run_all.sh` passes (RUN_ALL PASSED), then
   `python3 kit/session.py freeze .`, then `bash tests/run_all.sh` again (it verifies the freeze).
6. `python3 kit/session.py stage .`, then `python3 kit/session.py run .`. After a stop, the stop
   code is the runner's (kit/run_stage.sh header) or the driver's (kit/session.py header); a 24
   after wind or g14 goes on by itself, a 24 in clipr ends the session (its `on_stop = "end"`);
   anything else waits for the lead. No reboot, no unload, no register write.
7. Order in the sitting (DECISIONS-R14.md): after r14-tex, r14-zls and r14-dpm, before r14-bif and
   r14-flag. Safe class only: no fault is expected. The two untested kinds of row come last in
   their stages: g14's three poked-viewport rows (words 6 to 9 of the state block; E903 poked
   words 6 and 7 on module 41E2F5C7 without a fault, B60AB0B4 has not run one) and clipr's int32
   ends (+-2^31 px at --tri-unit 0; E1024 drew 2^30). Each stops its stage at the first job that
   is not ok.
8. The viewport words: render.c's `sgxfive_tri_block` writes words 6 to 9 as W/2, W/2, H/2, H/2
   (offset and scale per axis, whichever comes first); every vp row pokes the four words to one
   value (32.0 or 64.0), so the order does not enter the prediction.
