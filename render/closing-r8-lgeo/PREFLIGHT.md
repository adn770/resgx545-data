# r8-lgeo preflight (the lead, before staging)

1. The laptop runs the current test boot: gma500 srcversion 37EC97AB0CB37213C42FCCC loaded and
   installed (`modinfo -F srcversion gma500` and `/sys/module/gma500/srcversion`); not the R8-5
   boot. If the session slips past R8-5, it is scaffolded again with that module's srcversion (a
   freeze is never rewritten).
2. `~/sgxfive-test-rgn4` is sha256 e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a
   (the kit's stage checks it); no other tool is used. t7 is not needed.
3. `~/scratch/r8m/` does not exist or holds no attempt of this session; at least 400 MiB free on
   `~` plus about 150 MiB for the kept files (zs2's 165 `--pixels` outputs, q139's dumps).
4. Offline on the Mac, in this directory: `bash tests/run_all.sh` passes (RUN_ALL PASSED), then
   `python3 kit/session.py freeze .`, then `bash tests/run_all.sh` again (it verifies the freeze).
5. `python3 kit/session.py stage .`, then `python3 kit/session.py run .`. After a stop, the stop
   code is the runner's (kit/run_stage.sh header) or the driver's (kit/session.py header); a 24
   goes on by itself; anything else waits for the lead. No reboot, no unload, no register write.
6. Run after r8-geo and r8-ldpm or between them as the lead orders; nothing here needs the round 8
   kernel. Safe class only: no fault is expected; the first one stops the session.
