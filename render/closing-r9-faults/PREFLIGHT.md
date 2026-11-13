# r9-faults preflight (the lead, before staging)

1. The sitting's safe sessions have run first (DECISIONS-R9: the two fault stages last). The
   laptop still runs the round 8 module: gma500 srcversion B60AB0B475DD1E8972419B5 loaded and
   installed (the kit's preflight checks both); `/sys/kernel/debug/dri/*/sgx/vm_pte_flags`,
   `vm_pte_addr`, `alias_skip` and `render_pb_pages` exist and read 0, 0, 0 and 0x422 (the
   preflight refuses knobs not at their defaults). If the module was rebuilt or the laptop
   rebooted to stock Arch, this session does not run: it is scaffolded again (a freeze is never
   rewritten).
2. `~/sgxfive-test-rgn4` is sha256 e6951558a93b4b7bc750eeae302997992d7ec6e26719bc527ba1ffc9c6fb779a
   (the kit's stage checks it); no other tool is used. Its source is bound (TOOLSRC.sha256,
   session.toml `source`): every row was replayed on its library mock, none refused.
3. `~/scratch/r9f/` does not exist or holds no attempt of this session; at least 300 MiB free on
   `~` (the kept files are a few MiB).
4. Offline on the Mac, in this directory: `bash tests/run_all.sh` passes (RUN_ALL PASSED); the
   session is frozen (`python3 kit/session.py freeze .`) and `bash tests/run_all.sh` passes again
   (it verifies the freeze).
5. `python3 kit/session.py stage .`, then `python3 kit/session.py run .` with its log outside this
   directory (`closing9/logs/run-r9f.log`). A 24 goes on by itself; anything else waits for the
   lead. No reboot, no unload, no register write. After the run (or a stop) the four knobs read
   their defaults (the exit trap restores them; check with `sudo cat` of the four files).
6. Faults are planned: isolation's three in one job (a control), 5 in xf2, 3 in tri2, bif-c9 and
   bif-c1 (controls), and up to 12 more if the rivals hold. Each is recovered by the kernel, then
   the kit's reset and strict health. A recovery that fails (`SGX recovery failed: -110`) and a
   health draw that fails stop the session (16 or 5); two -110 lines in one stage stop the stage
   (24). bif's masks leave the EDM's own buffers out of the client directory only: the EDM's own
   directory (list 15) is never touched (E573).
7. bif-c1 (buffer 0, a fault in the EDM's code heap, E573 and E745) and the 0x7dfe rows are the
   riskiest rows of the sitting; they run last. If a stop leaves the GPU not drawing after the
   kit's recovery, the lead decides (no further job, no reboot from the session).
