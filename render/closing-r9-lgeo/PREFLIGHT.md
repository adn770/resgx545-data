# r9-lgeo preflight (the lead, before staging)

1. The laptop runs the round 9 test boot: gma500 srcversion B60AB0B475DD1E8972419B5 loaded and
   installed (`modinfo -F srcversion gma500` and `/sys/module/gma500/srcversion`). After the
   reboot to stock Arch this session is scaffolded again with that module's srcversion (a freeze
   is never rewritten).
2. `~/sgxfive-test-rgn4` is sha256 e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a
   (the kit's stage checks it); no other tool is used.
3. `~/scratch/r9m/` does not exist or holds no attempt of this session; at least 400 MiB free on
   `~` plus about 60 MiB for the kept files (q139b's 1280 x 720 `--pixels` outputs and dumps).
4. Offline on the Mac, in this directory: `bash tests/run_all.sh` passes (RUN_ALL PASSED), then
   `python3 kit/session.py freeze .`, then `bash tests/run_all.sh` again (it verifies the freeze).
5. `python3 kit/session.py stage .`, then `python3 kit/session.py run .`. After a stop, the stop
   code is the runner's (kit/run_stage.sh header) or the driver's (kit/session.py header); a 24
   goes on by itself; anything else waits for the lead. No reboot, no unload, no register write.
6. Order in the sitting (DECISIONS-R9.md): after S9-geo, before r9-k1. Safe class only: no fault
   is expected; the first one stops the session. zs3 is not here.
