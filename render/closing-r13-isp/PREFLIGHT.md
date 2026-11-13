# r13-isp preflight (the lead, before staging)

1. The laptop runs the test boot: gma500 srcversion B60AB0B475DD1E8972419B5 loaded and installed
   (`modinfo -F srcversion gma500` and `/sys/module/gma500/srcversion`). After the reboot to stock
   Arch this session is scaffolded again (a freeze is never rewritten).
2. `~/sgxfive-test-t10` is sha256 9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb
   (the kit's stage checks it); no other tool is used.
3. No earlier session of the sitting left a kpoke armed or a knob off its default (this session
   writes no knob and no kpoke).
4. `~/scratch/r13i/` does not exist or holds no attempt of this session; at least 300 MiB free on
   `~` plus about 15 MiB for the kept files (47 outputs with every pixel).
5. Offline on the Mac, in this directory: `bash tests/run_all.sh` passes (RUN_ALL PASSED), then
   `python3 kit/session.py freeze .`, then `bash tests/run_all.sh` again (it verifies the freeze).
6. `python3 kit/session.py stage .`, then `python3 kit/session.py run .`. After a stop, the stop
   code is the runner's (kit/run_stage.sh header) or the driver's (kit/session.py header); a 24
   goes on by itself; anything else waits for the lead. No reboot, no unload, no register write.
7. Order in the sitting (DECISIONS-R13.md): after r13-tex, r13-zls and r13-dpm, before r13-flag.
   Safe class only: no fault is expected before far; far is the last stage and stops at its first
   job that is not ok (its rows past 2^25 px are the only untested range of the safe sessions).
8. `--cmd 16=` with byte 0 other than 0x88: the fork (2a650d74, read only) copies the word into
   the render data unchecked (`sgx_render.c` line 309, `rd[SGX_RENDER_RD_MSCTL / 4] =
   c->isp_multisamplectl`; no other use outside tests) and the library mock takes it; E064 swept
   all 256 values. Were it refused, q201's 0x26 control would fail rc 3 and the session stop (4)
   before q261 (mock world cmdrefused).
