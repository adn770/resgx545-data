# r10-geo preflight (the lead, before staging)

1. The laptop runs the round 9 test boot: gma500 srcversion B60AB0B475DD1E8972419B5 loaded and
   installed (`modinfo -F srcversion gma500` and `/sys/module/gma500/srcversion`); debugfs has
   `render_bg_layer` (reads N) and `render_bg_src` (reads 0x00000000), `render_param` and
   `render_tadata` (session.toml `debugfs`: the runner refuses to start otherwise). After the
   reboot to stock Arch this session is scaffolded again (a freeze is never rewritten).
2. `~/sgxfive-test-rgn4` is sha256 e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a
   and `~/sgxfive-test-t9` is 7a28be3952fb310170e861da0622d890a2e215cb761d6f21bc9321223e1b40ce (the
   kit's stage checks both); no other tool is used (t10 and far2 are not here).
3. No earlier session of the sitting left a kpoke armed or a layer knob on (bgw writes them as row
   words; the runner restores them after every job and by its trap).
4. `~/scratch/r10g/` does not exist or holds no attempt of this session; at least 400 MiB free on
   `~` plus about 30 MiB for the kept files (q139c's 640 x 480 `--pixels` outputs and dumps).
5. Offline on the Mac, in this directory: `bash tests/run_all.sh` passes (RUN_ALL PASSED), then
   `python3 kit/session.py freeze .`, then `bash tests/run_all.sh` again (it verifies the freeze).
6. `python3 kit/session.py stage .`, then `python3 kit/session.py run .`. After a stop, the stop
   code is the runner's (kit/run_stage.sh header) or the driver's (kit/session.py header); a 24
   goes on by itself; anything else waits for the lead. No reboot, no unload, no register write.
7. Order in the sitting (DECISIONS-R10.md, R10-10 (a)): after S10-tex, before S10-dpm. Safe class
   only: no fault is expected; the first one stops the session.
