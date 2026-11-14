# r15-isp preflight (the lead, before staging)

1. The laptop runs the test boot: gma500 srcversion B60AB0B475DD1E8972419B5 loaded and installed
   (`modinfo -F srcversion gma500` and `/sys/module/gma500/srcversion`). After a reboot to stock
   Arch this session is scaffolded again (a freeze is never rewritten).
2. `~/sgxfive-test-t10` is sha256 9bedc2d6db70b2691698478572e311cf2b9b54acfaf8d714ed4db47852e322eb
   (the kit's stage checks it); no other tool is used.
3. No earlier session of the sitting left a kpoke armed or a knob off its default (this session
   writes no knob and no kpoke; its only pokes are `--poke blk:1` and `blk:1^=V`, the state block
   in the tool's own buffer).
4. `~/scratch/r15i/` does not exist or holds no attempt of this session; at least 300 MiB free on
   `~` plus about 2 MiB for the kept files (11 outputs with every pixel, eight 80 KiB dumps).
5. Offline on the Mac, in this directory: `bash tests/run_all.sh` passes (RUN_ALL PASSED), then
   `python3 kit/session.py freeze .`, then `bash tests/run_all.sh` again (it verifies the freeze).
6. `python3 kit/session.py stage .`, then `python3 kit/session.py run .`. After a stop, the stop
   code is the runner's (kit/run_stage.sh header) or the driver's (kit/session.py header); a 24 in
   zcut ends the session (`on_stop = "end"`, the only stage); anything else waits for the lead. No
   reboot, no unload, no register write.
7. Order in the sitting (DECISIONS-R15.md): fourth, after r15-zls, r15-tex and r15-dpm, before
   r15-tw (last). Safe class only: no fault is expected. The rows are E1045's form (compare always,
   a depth past [0, 1]) and E065's flips of the library triangle; every vertex lies inside H-VP's
   guard of the 80 x 40 target.
8. What to read after the run: `out/ATTEMPT/score-zcut.txt` (CONTROL lines first: the three must
   PASS before a headline means anything; READING lines say where H-POLYCLIP parted from the exact
   cut and whether bits 16 and 17 leave bit 15's pixels).
